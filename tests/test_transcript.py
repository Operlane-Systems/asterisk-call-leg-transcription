from __future__ import annotations

import unittest

from asterisk_call_leg_transcription.transcript import merge_segments


class MergeSegmentsTests(unittest.TestCase):
    def test_keeps_physical_track_labels_and_sorts_by_timestamp(self) -> None:
        transcript = merge_segments(
            {
                "caller": [{"start": 2.0, "text": "I need help"}],
                "agent": [{"start": 1.0, "text": "How can I help?"}],
            }
        )
        self.assertEqual(
            transcript,
            [
                {"at_s": 1.0, "speaker": "agent", "text": "How can I help?"},
                {"at_s": 2.0, "speaker": "caller", "text": "I need help"},
            ],
        )
