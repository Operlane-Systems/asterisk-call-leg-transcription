"""Container entry point: attach one labelled OpenAI transcription pipeline per Stasis call."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

from asterisk_call_leg_transcription.ari import ARIClient, ARISettings
from asterisk_call_leg_transcription.live import CallLegPipeline, TranscriptEvent
from asterisk_call_leg_transcription.openai_realtime import OpenAIRealtimeTranscript


async def main() -> None:
    path = Path(os.environ.get("TRANSCRIPT_PATH", "/artifacts/transcript.jsonl"))
    path.parent.mkdir(parents=True, exist_ok=True)

    async def on_event(event: TranscriptEvent) -> None:
        record = {"speaker": event.speaker, "type": event.type, "text": event.text, "item_id": event.item_id}
        with path.open("a", encoding="utf-8") as output:
            output.write(json.dumps(record) + "\n")
        print(json.dumps(record), flush=True)

    ari = ARIClient(
        ARISettings(
            url=os.environ["ARI_URL"],
            username=os.environ["ARI_USER"],
            password=os.environ["ARI_PASS"],
            app_name=os.environ["ARI_APP"],
        )
    )
    transcript = OpenAIRealtimeTranscript(on_event=on_event)
    active: dict[str, CallLegPipeline] = {}
    async for event in ari.events():
        channel = event.get("channel", {})
        channel_id = channel.get("id")
        if event.get("type") == "StasisStart":
            if not channel_id or channel_id in active or channel.get("name", "").startswith(("Snoop/", "UnicastRTP/")):
                continue
            pipeline = CallLegPipeline(
                ari,
                transcript,
                prefix="e2e",
                rtp_bind_host=os.environ.get("RTP_BIND_HOST", "127.0.0.1"),
                external_media_host=os.environ.get("RTP_ADVERTISE_HOST", "127.0.0.1"),
            )
            try:
                await pipeline.start({"caller": channel_id})
            except Exception as exc:
                print(f"pipeline start failed for {channel_id}: {exc}", flush=True)
                await pipeline.stop()
                continue
            active[channel_id] = pipeline
        elif event.get("type") == "StasisEnd" and channel_id in active:
            await active.pop(channel_id).stop()


if __name__ == "__main__":
    asyncio.run(main())
