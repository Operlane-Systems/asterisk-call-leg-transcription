"""WAV helpers for packaging and separating physical Asterisk call-leg audio."""

from __future__ import annotations

import io
import wave
from pathlib import Path


class AudioFormatError(ValueError):
    """Raised when a supplied recording cannot be safely packaged."""


def _read_mono_pcm(path: Path) -> tuple[bytes, int, int]:
    with wave.open(str(path), "rb") as recording:
        channels = recording.getnchannels()
        sample_width = recording.getsampwidth()
        rate = recording.getframerate()
        frames = recording.readframes(recording.getnframes())
    if channels != 1 or sample_width != 2:
        raise AudioFormatError(
            f"{path} must be a 16-bit mono WAV; got {channels} channels and {sample_width * 8}-bit samples"
        )
    return frames, rate, sample_width


def package_tracks(left_path: Path, right_path: Path) -> tuple[bytes, int]:
    """Return a padded, 16-bit stereo WAV from two aligned mono WAV recordings.

    `MixMonitor`'s r()/t() files can differ slightly in duration. Padding the
    shorter track with silence preserves each track's timing relative to call
    start rather than shifting its transcript.
    """

    left, left_rate, sample_width = _read_mono_pcm(left_path)
    right, right_rate, right_width = _read_mono_pcm(right_path)
    if left_rate != right_rate or sample_width != right_width:
        raise AudioFormatError(
            f"Track formats differ: left={left_rate}Hz/{sample_width * 8}-bit, "
            f"right={right_rate}Hz/{right_width * 8}-bit"
        )

    size = max(len(left), len(right))
    left += b"\0" * (size - len(left))
    right += b"\0" * (size - len(right))
    frames = bytearray(size * 2)
    for offset in range(0, size, sample_width):
        target = offset * 2
        frames[target : target + sample_width] = left[offset : offset + sample_width]
        frames[target + sample_width : target + 2 * sample_width] = right[offset : offset + sample_width]

    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(sample_width)
        output.setframerate(left_rate)
        output.writeframes(bytes(frames))
    return buffer.getvalue(), left_rate


def write_package(left_path: Path, right_path: Path, output_path: Path) -> int:
    """Package MixMonitor tracks and write a stereo WAV. Returns its sample rate."""

    wav_bytes, rate = package_tracks(left_path, right_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(wav_bytes)
    return rate


def split_stereo(wav_bytes: bytes) -> tuple[bytes, bytes, int]:
    """Return (left_pcm, right_pcm, rate) from a 16-bit stereo WAV."""

    with wave.open(io.BytesIO(wav_bytes), "rb") as recording:
        channels = recording.getnchannels()
        sample_width = recording.getsampwidth()
        rate = recording.getframerate()
        frames = recording.readframes(recording.getnframes())
    if channels != 2 or sample_width != 2:
        raise AudioFormatError("expected a 16-bit stereo WAV")
    left = b"".join(frames[index : index + 2] for index in range(0, len(frames), 4))
    right = b"".join(frames[index + 2 : index + 4] for index in range(0, len(frames), 4))
    return left, right, rate
