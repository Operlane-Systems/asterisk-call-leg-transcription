from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path

from asterisk_call_leg_transcription.audio import AudioFormatError, package_tracks, split_stereo


def write_mono(path: Path, frames: bytes, rate: int = 8000) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(frames)


class PackageTracksTests(unittest.TestCase):
    def test_packages_and_pads_two_tracks_without_losing_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left_path, right_path = root / "left.wav", root / "right.wav"
            write_mono(left_path, b"\x01\x00\x02\x00")
            write_mono(right_path, b"\x03\x00")
            packaged, rate = package_tracks(left_path, right_path)

        left, right, unpacked_rate = split_stereo(packaged)
        self.assertEqual(rate, 8000)
        self.assertEqual(unpacked_rate, 8000)
        self.assertEqual(left, b"\x01\x00\x02\x00")
        self.assertEqual(right, b"\x03\x00\x00\x00")

    def test_rejects_non_mono_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stereo, mono = root / "stereo.wav", root / "mono.wav"
            with wave.open(str(stereo), "wb") as output:
                output.setnchannels(2)
                output.setsampwidth(2)
                output.setframerate(8000)
                output.writeframes(b"\0\0\0\0")
            write_mono(mono, b"\0\0")
            with self.assertRaises(AudioFormatError):
                package_tracks(stereo, mono)
