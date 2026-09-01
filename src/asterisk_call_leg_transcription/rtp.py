"""RTP receive path for one Asterisk externalMedia channel."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import struct

RTP_HEADER_BYTES = 12
ULAW_RATE = 8000


def rtp_payload(packet: bytes) -> bytes | None:
    """Extract RTP payload while respecting CSRC, extension, and padding fields."""

    if len(packet) < RTP_HEADER_BYTES or packet[0] >> 6 != 2:
        return None
    csrc_count = packet[0] & 0x0F
    header_size = RTP_HEADER_BYTES + csrc_count * 4
    if packet[0] & 0x10:
        if len(packet) < header_size + 4:
            return None
        extension_words = struct.unpack("!H", packet[header_size + 2 : header_size + 4])[0]
        header_size += 4 + extension_words * 4
    if len(packet) <= header_size:
        return None
    padding = packet[-1] if packet[0] & 0x20 else 0
    if padding > len(packet) - header_size:
        return None
    return packet[header_size : len(packet) - padding if padding else None]


class _RTPProtocol(asyncio.DatagramProtocol):
    def __init__(self, on_packet: Callable[[bytes], None]):
        self._on_packet = on_packet

    def datagram_received(self, data: bytes, addr) -> None:
        payload = rtp_payload(data)
        if payload:
            self._on_packet(payload)


class RTPReceiveGateway:
    """Bound UDP endpoint that delivers μ-law RTP payloads without blocking I/O.

    The sink is intentionally isolated behind a bounded queue. A slow provider
    must not block Asterisk's RTP receive loop; stale packets are dropped and
    counted rather than growing memory without limit.
    """

    def __init__(self, on_ulaw: Callable[[bytes], Awaitable[None]], *, queue_size: int = 500):
        self._on_ulaw = on_ulaw
        self._queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=queue_size)
        self._transport: asyncio.DatagramTransport | None = None
        self._worker: asyncio.Task | None = None
        self.local_port: int | None = None
        self.dropped_packets = 0

    async def bind(self) -> int:
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _RTPProtocol(self._received), local_addr=("127.0.0.1", 0)
        )
        self._transport = transport
        self.local_port = transport.get_extra_info("sockname")[1]
        self._worker = asyncio.create_task(self._run(), name=f"rtp-receive-{self.local_port}")
        return self.local_port

    def _received(self, ulaw: bytes) -> None:
        try:
            self._queue.put_nowait(ulaw)
        except asyncio.QueueFull:
            self.dropped_packets += 1

    async def _run(self) -> None:
        while True:
            ulaw = await self._queue.get()
            if ulaw is None:
                return
            await self._on_ulaw(ulaw)

    async def close(self) -> None:
        if self._transport:
            self._transport.close()
            self._transport = None
        if self._worker:
            try:
                self._queue.put_nowait(None)
            except asyncio.QueueFull:
                # Prefer a clean shutdown over one stale RTP packet when the
                # provider has stopped consuming audio.
                self._queue.get_nowait()
                self._queue.put_nowait(None)
            await self._worker
            self._worker = None
