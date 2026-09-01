from __future__ import annotations

import asyncio
import unittest

from asterisk_call_leg_transcription.live import CallLegPipeline, LiveTranscript


class FakeARI:
    def __init__(self, fail_snoop_attach: bool = False):
        self.calls: list[tuple] = []
        self.fail_snoop_attach = fail_snoop_attach

    def snoop(self, channel_id, *, snoop_id, spy="in"):
        self.calls.append(("snoop", channel_id, snoop_id, spy))
        return {"id": snoop_id}

    def external_media(self, *, channel_id, host):
        self.calls.append(("external_media", channel_id, host))
        return {"id": channel_id}

    def create_bridge(self, bridge_id):
        self.calls.append(("create_bridge", bridge_id))

    def add_to_bridge(self, bridge_id, channel_id):
        self.calls.append(("add_to_bridge", bridge_id, channel_id))
        if self.fail_snoop_attach and "snoop" in channel_id:
            raise RuntimeError("snoop not ready")

    def remove_from_bridge(self, bridge_id, channel_id):
        self.calls.append(("remove_from_bridge", bridge_id, channel_id))

    def hangup(self, channel_id):
        self.calls.append(("hangup", channel_id))

    def destroy_bridge(self, bridge_id):
        self.calls.append(("destroy_bridge", bridge_id))


class FakeTranscript(LiveTranscript):
    def __init__(self):
        self.started: list[str] = []
        self.stopped: list[str] = []

    async def start_leg(self, label: str) -> None:
        self.started.append(label)

    async def append_ulaw(self, label: str, audio: bytes) -> None:
        pass

    async def stop_leg(self, label: str) -> None:
        self.stopped.append(label)


class CallLegPipelineTests(unittest.TestCase):
    def test_starts_one_snoop_and_media_path_per_label_then_cleans_up(self) -> None:
        async def scenario():
            ari, transcript = FakeARI(), FakeTranscript()
            pipeline = CallLegPipeline(ari, transcript)
            await pipeline.start({"caller": "caller-1", "agent": "agent-2"})
            await pipeline.stop()
            return ari, transcript

        ari, transcript = asyncio.run(scenario())
        self.assertEqual(transcript.started, ["caller", "agent"])
        self.assertEqual(transcript.stopped, ["agent", "caller"])
        self.assertEqual(sum(call[0] == "snoop" for call in ari.calls), 2)
        self.assertEqual(sum(call[0] == "external_media" for call in ari.calls), 2)
        self.assertEqual(sum(call[0] == "hangup" for call in ari.calls), 4)

    def test_failure_uses_same_cleanup_path_for_partial_leg(self) -> None:
        async def scenario():
            ari, transcript = FakeARI(fail_snoop_attach=True), FakeTranscript()
            pipeline = CallLegPipeline(ari, transcript, snoop_ready_retries=1)
            with self.assertRaisesRegex(RuntimeError, "snoop not ready"):
                await pipeline.start({"caller": "caller-1"})
            return ari, transcript

        ari, transcript = asyncio.run(scenario())
        self.assertEqual(transcript.started, [])
        self.assertTrue(any(call[0] == "hangup" and "snoop" in call[1] for call in ari.calls))
        self.assertTrue(any(call[0] == "destroy_bridge" for call in ari.calls))
