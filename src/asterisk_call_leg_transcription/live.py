"""Production-shaped lifecycle for one Snoop + externalMedia pipeline per call leg."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
import inspect
import uuid

from .ari import ARIClient
from .rtp import RTPReceiveGateway


@dataclass(frozen=True)
class TranscriptEvent:
    speaker: str
    type: str  # "delta" or "completed"
    text: str
    item_id: str | None = None


class LiveTranscript:
    """The tiny contract a real-time transcription provider must satisfy."""

    async def start_leg(self, label: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def append_ulaw(self, label: str, audio: bytes) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def stop_leg(self, label: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


@dataclass
class _LegResources:
    label: str
    snoop_id: str
    media_id: str
    bridge_id: str
    gateway: RTPReceiveGateway
    media_channel_id: str | None = None
    sink_started: bool = False


class CallLegPipeline:
    """Attach a dedicated real-time transcription path to every supplied leg.

    The retry around Snoop bridge attachment is intentional: ARI returns from
    the Snoop request before the helper channel is always ready to join a bridge.
    Every partial-start path uses the same teardown routine.
    """

    def __init__(
        self,
        ari: ARIClient,
        transcript: LiveTranscript,
        *,
        prefix: str = "call-leg",
        rtp_bind_host: str = "127.0.0.1",
        external_media_host: str = "127.0.0.1",
        snoop_ready_retries: int = 15,
        snoop_ready_delay_s: float = 0.1,
    ):
        self.ari = ari
        self.transcript = transcript
        self.prefix = prefix
        self.rtp_bind_host = rtp_bind_host
        self.external_media_host = external_media_host
        self.snoop_ready_retries = snoop_ready_retries
        self.snoop_ready_delay_s = snoop_ready_delay_s
        self._resources: list[_LegResources] = []

    async def start(self, legs: Mapping[str, str]) -> None:
        """Start all labelled legs, or clean up every started resource on failure."""

        if not legs:
            raise ValueError("at least one labelled call leg is required")
        try:
            for label, channel_id in legs.items():
                self._resources.append(await self._start_leg(label, channel_id))
        except Exception:
            await self.stop()
            raise

    async def _start_leg(self, label: str, target_channel_id: str) -> _LegResources:
        token = uuid.uuid4().hex[:12]
        safe_label = "".join(char if char.isalnum() or char in "-_" else "-" for char in label)
        resource = _LegResources(
            label=label,
            snoop_id=f"{self.prefix}-snoop-{safe_label}-{token}",
            media_id=f"{self.prefix}-media-{safe_label}-{token}",
            bridge_id=f"{self.prefix}-bridge-{safe_label}-{token}",
            gateway=RTPReceiveGateway(
                lambda audio: self.transcript.append_ulaw(label, audio), bind_host=self.rtp_bind_host
            ),
        )
        try:
            port = await resource.gateway.bind()
            await asyncio.to_thread(self.ari.snoop, target_channel_id, snoop_id=resource.snoop_id)
            media = await asyncio.to_thread(
                self.ari.external_media,
                channel_id=resource.media_id,
                host=f"{self.external_media_host}:{port}",
            )
            resource.media_channel_id = media["id"]
            await asyncio.to_thread(self.ari.create_bridge, resource.bridge_id)
            for attempt in range(self.snoop_ready_retries):
                try:
                    await asyncio.to_thread(self.ari.add_to_bridge, resource.bridge_id, resource.snoop_id)
                    break
                except Exception:
                    if attempt == self.snoop_ready_retries - 1:
                        raise
                    await asyncio.sleep(self.snoop_ready_delay_s)
            await asyncio.to_thread(
                self.ari.add_to_bridge, resource.bridge_id, resource.media_channel_id
            )
            await self.transcript.start_leg(label)
            resource.sink_started = True
            return resource
        except Exception:
            await self._stop_resource(resource)
            raise

    async def stop(self) -> None:
        """Release provider, RTP endpoint, ARI media, Snoop, and bridge in order."""

        resources, self._resources = self._resources, []
        for resource in reversed(resources):
            await self._stop_resource(resource)

    async def _stop_resource(self, resource: _LegResources) -> None:
        if resource.sink_started:
            try:
                await self.transcript.stop_leg(resource.label)
            except Exception:
                pass
        try:
            await resource.gateway.close()
        except Exception:
            pass
        if resource.media_channel_id:
            await self._quiet(self.ari.remove_from_bridge, resource.bridge_id, resource.media_channel_id)
            await self._quiet(self.ari.hangup, resource.media_channel_id)
        await self._quiet(self.ari.hangup, resource.snoop_id)
        await self._quiet(self.ari.destroy_bridge, resource.bridge_id)

    async def _quiet(self, operation: Callable[..., object], *args: object) -> None:
        try:
            result = await asyncio.to_thread(operation, *args)
            if inspect.isawaitable(result):
                await result
        except Exception:
            pass
