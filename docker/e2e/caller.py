"""Internal E2E caller. The runbook treats it as a generic SIP test client."""

from __future__ import annotations

import audioop
import io
import os
import socket
import time
import wave

import requests
from pyVoIP.VoIP import CallState, VoIPPhone

FRAME_SAMPLES = 160


def local_ip(remote_host: str) -> str:
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect((remote_host, 5060))
        return probe.getsockname()[0]
    finally:
        probe.close()


def synthesize(text: str, api_key: str) -> bytes:
    response = requests.post(
        "https://api.openai.com/v1/audio/speech",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "gpt-4o-mini-tts", "voice": "alloy", "input": text, "response_format": "wav"},
        timeout=90,
    )
    response.raise_for_status()
    with wave.open(io.BytesIO(response.content), "rb") as input_wav:
        if input_wav.getnchannels() != 1 or input_wav.getsampwidth() != 2:
            raise RuntimeError("OpenAI TTS response was not mono 16-bit WAV")
        pcm = input_wav.readframes(input_wav.getnframes())
        rate = input_wav.getframerate()
    if rate != 8000:
        pcm, _ = audioop.ratecv(pcm, 2, 1, rate, 8000, None)
    return audioop.lin2ulaw(pcm, 2)


def send_ulaw(call, ulaw: bytes) -> None:
    linear = audioop.ulaw2lin(ulaw, 1)
    call.write_audio(audioop.bias(linear, 1, 128))


def main() -> None:
    host = os.environ["SIP_HOST"]
    # Prepare speech before the call begins.  A generic SIP client should
    # transmit media as soon as the far end answers; delaying this work until
    # after answer lets its real-time media buffer advance through silence.
    audio = synthesize(os.environ["EXPECTED_TRANSCRIPT"], os.environ["OPENAI_API_KEY"])
    print(f"Generated {len(audio)} μ-law bytes; max RMS {audioop.rms(audioop.ulaw2lin(audio, 2), 2)}", flush=True)
    phone = VoIPPhone(
        host,
        int(os.environ.get("SIP_PORT", "5060")),
        os.environ.get("SIP_USERNAME", "lab-client"),
        os.environ["SIP_PASSWORD"],
        myIP=local_ip(host),
        sipPort=5060,
        rtpPortLow=10000,
        rtpPortHigh=10100,
    )
    phone.start()
    try:
        time.sleep(3)
        call = phone.call(os.environ.get("SIP_EXTENSION", "7000"))
        deadline = time.monotonic() + 30
        while call.state not in {CallState.ANSWERED, CallState.ENDED} and time.monotonic() < deadline:
            time.sleep(0.1)
        if call.state != CallState.ANSWERED:
            raise RuntimeError(f"call was not answered: {call.state}")
        silence = b"\xff" * FRAME_SAMPLES
        for offset in range(0, len(audio), FRAME_SAMPLES):
            send_ulaw(call, audio[offset : offset + FRAME_SAMPLES].ljust(FRAME_SAMPLES, b"\xff"))
            time.sleep(0.02)
        for _ in range(150):
            send_ulaw(call, silence)
            time.sleep(0.02)
        call.hangup()
        print("SIP call completed", flush=True)
    finally:
        phone.stop()


if __name__ == "__main__":
    main()
