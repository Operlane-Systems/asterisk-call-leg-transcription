"""Attach real-time, labelled transcription to already-known Stasis call legs.

Run on the Asterisk host (or change the external-media host handling for a
remote RTP gateway). The process remains attached until Ctrl-C, then cleans up
only the helper channels and bridges it created.
"""

from __future__ import annotations

import argparse
import asyncio
import os

from asterisk_call_leg_transcription.ari import ARIClient, ARISettings
from asterisk_call_leg_transcription.live import CallLegPipeline
from asterisk_call_leg_transcription.openai_realtime import OpenAIRealtimeTranscript


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--caller-channel", required=True)
    parser.add_argument("--agent-channel", required=True)
    return parser.parse_args()


async def run() -> None:
    args = arguments()
    ari = ARIClient(
        ARISettings(
            url=os.environ.get("ARI_URL", "http://127.0.0.1:8088/ari"),
            username=os.environ["ARI_USER"],
            password=os.environ["ARI_PASS"],
            app_name=os.environ.get("ARI_APP", "call-leg-transcription"),
        )
    )
    pipeline = CallLegPipeline(ari, OpenAIRealtimeTranscript())
    await pipeline.start({"caller": args.caller_channel, "agent": args.agent_channel})
    print("Live transcription attached. Press Ctrl-C to stop.")
    try:
        await asyncio.Event().wait()
    finally:
        await pipeline.stop()


if __name__ == "__main__":
    asyncio.run(run())
