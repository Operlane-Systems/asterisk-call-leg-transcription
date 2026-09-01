from __future__ import annotations

import struct
import unittest

from asterisk_call_leg_transcription.rtp import rtp_payload


class RTPPayloadTests(unittest.TestCase):
    def test_extracts_payload_after_csrc_extension_and_padding(self) -> None:
        header = bytes([0xB1, 0]) + struct.pack("!HII", 1, 2, 3) + b"CSRC"
        extension = struct.pack("!HH", 0x1000, 1) + b"EXT!"
        packet = header + extension + b"audio" + b"\x02\x02"
        self.assertEqual(rtp_payload(packet), b"audio")

    def test_rejects_non_rtp_packets(self) -> None:
        self.assertIsNone(rtp_payload(b"not rtp"))
