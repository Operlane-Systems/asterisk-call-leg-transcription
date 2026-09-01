"""OpenAI Realtime transcription adapter for call-leg μ-law audio."""

from __future__ import annotations

import asyncio
import audioop
import base64
from collections.abc import Awaitable, Callable
import json
import os

import websockets

from .live import LiveTranscript, TranscriptEvent

OPENAI_TRANSCRIPTION_URL = "wss://api.openai.com/v1/realtime?intent=transcription"
PCM_RATE = 24000


class OpenAIRealtimeTranscript(LiveTranscript):
    """One OpenAI transcription session per physical call leg.

    Asterisk `externalMedia(format=ulaw)` is decoded from 8 kHz μ-law and
    resampled to the 24 kHz PCM configuration documented for Realtime
    transcription. `on_event` receives the PBX-derived label unchanged.
    """

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str = "gpt-live-transcribe",
        on_event: Callable[[TranscriptEvent], Awaitable[None]] | None = None,
        prompt: str | None = None,
        keywords: list[str] | None = None,
        languages: list[str] | None = None,
        delay: str = "low",
    ):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model
        self.on_event = on_event or self._print_event
        self.prompt = prompt
        self.keywords = keywords
        self.languages = languages
        self.delay = delay
        self._sessions: dict[str, _LegSession] = {}

    async def start_leg(self, label: str) -> None:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required for the OpenAI Realtime adapter")
        session = _LegSession(label, self)
        await session.start()
        self._sessions[label] = session

    async def append_ulaw(self, label: str, audio: bytes) -> None:
        session = self._sessions.get(label)
        if session:
            session.append_ulaw(audio)

    async def stop_leg(self, label: str) -> None:
        session = self._sessions.pop(label, None)
        if session:
            await session.stop()

    async def _print_event(self, event: TranscriptEvent) -> None:
        if event.type == "completed":
            print(f"[{event.speaker}] {event.text}")


class _LegSession:
    def __init__(self, label: str, owner: OpenAIRealtimeTranscript):
        self.label = label
        self.owner = owner
        self.websocket = None
        self.input: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=1000)
        self.tasks: list[asyncio.Task] = []
        self.closed = False
        self._rate_state = None
        self._completed = asyncio.Event()

    async def start(self) -> None:
        self.websocket = await websockets.connect(
            OPENAI_TRANSCRIPTION_URL,
            additional_headers={"Authorization": f"Bearer {self.owner.api_key}"},
            max_size=None,
            max_queue=None,
        )
        transcription: dict[str, object] = {"model": self.owner.model, "delay": self.owner.delay}
        if self.owner.prompt:
            transcription["prompt"] = self.owner.prompt
        if self.owner.keywords:
            transcription["keywords"] = self.owner.keywords
        if self.owner.languages:
            transcription["languages"] = self.owner.languages
        await self._send(
            {
                "type": "session.update",
                "session": {
                    "type": "transcription",
                    "audio": {
                        "input": {
                            "format": {"type": "audio/pcm", "rate": PCM_RATE},
                            "transcription": transcription,
                            # gpt-live-transcribe uses explicit turn commits.  This
                            # keeps a call-leg stream model-compatible and lets the
                            # PBX lifecycle, rather than diarization or VAD guesses,
                            # determine the boundary.
                            "turn_detection": None,
                        }
                    },
                },
            }
        )
        await self._await_session_updated()
        self.tasks = [
            asyncio.create_task(self._send_loop(), name=f"openai-transmit-{self.label}"),
            asyncio.create_task(self._receive_loop(), name=f"openai-receive-{self.label}"),
        ]

    def append_ulaw(self, audio: bytes) -> None:
        if self.closed:
            return
        pcm_8k = audioop.ulaw2lin(audio, 2)
        pcm_24k, self._rate_state = audioop.ratecv(pcm_8k, 2, 1, 8000, PCM_RATE, self._rate_state)
        try:
            self.input.put_nowait(pcm_24k)
        except asyncio.QueueFull:
            pass

    async def _await_session_updated(self) -> None:
        assert self.websocket is not None
        while True:
            event = json.loads(await asyncio.wait_for(self.websocket.recv(), timeout=10))
            if event.get("type") == "error":
                raise RuntimeError(event.get("error", {}).get("message", "OpenAI Realtime startup failed"))
            if event.get("type") == "session.updated":
                return

    async def _send(self, event: dict) -> None:
        if self.websocket and not self.closed:
            await self.websocket.send(json.dumps(event))

    async def _send_loop(self) -> None:
        while True:
            pcm = await self.input.get()
            try:
                if pcm is None:
                    return
                await self._send(
                    {"type": "input_audio_buffer.append", "audio": base64.b64encode(pcm).decode("ascii")}
                )
            finally:
                self.input.task_done()

    async def _receive_loop(self) -> None:
        assert self.websocket is not None
        try:
            async for raw in self.websocket:
                event = json.loads(raw)
                kind = event.get("type")
                if kind == "conversation.item.input_audio_transcription.delta":
                    await self.owner.on_event(
                        TranscriptEvent(self.label, "delta", event.get("delta", ""), event.get("item_id"))
                    )
                elif kind == "conversation.item.input_audio_transcription.completed":
                    await self.owner.on_event(
                        TranscriptEvent(
                            self.label,
                            "completed",
                            event.get("transcript", ""),
                            event.get("item_id"),
                        )
                    )
                    self._completed.set()
        except Exception:
            if not self.closed:
                raise

    async def stop(self) -> None:
        if self.closed:
            return
        # Flush every RTP chunk first, then explicitly finish this call leg's
        # current turn.  gpt-live-transcribe does not support server VAD.
        try:
            await asyncio.wait_for(self.input.join(), timeout=5)
            await self._send({"type": "input_audio_buffer.commit"})
            await asyncio.wait_for(self._completed.wait(), timeout=10)
        except (asyncio.TimeoutError, websockets.WebSocketException):
            pass
        self.closed = True
        self.input.put_nowait(None)
        if self.websocket:
            await self.websocket.close()
        for task in self.tasks:
            task.cancel()
