from __future__ import annotations

import json
import tempfile
import unittest
import wave
from pathlib import Path
from unittest.mock import patch

from asterisk_call_leg_transcription.cli import main


def write_mono(path: Path, frames: bytes) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8000)
        output.writeframes(frames)


class CliTests(unittest.TestCase):
    def test_pack_writes_labels_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left, right, output = root / "left.wav", root / "right.wav", root / "call.wav"
            write_mono(left, b"\x01\x00")
            write_mono(right, b"\x02\x00")
            with patch(
                "sys.argv",
                [
                    "asterisk-call-leg-transcription",
                    "pack",
                    "--left",
                    str(left),
                    "--right",
                    str(right),
                    "--output",
                    str(output),
                    "--left-label",
                    "customer",
                    "--right-label",
                    "operator",
                ],
            ):
                main()

            self.assertTrue(output.is_file())
            self.assertEqual(
                json.loads(output.with_suffix(".wav.labels.json").read_text()),
                {
                    "format": "16-bit stereo PCM WAV",
                    "sample_rate_hz": 8000,
                    "left": "customer",
                    "right": "operator",
                },
            )
