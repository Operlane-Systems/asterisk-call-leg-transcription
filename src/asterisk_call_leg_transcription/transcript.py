"""Provider-neutral helpers for merging transcripts from physical audio tracks."""

from __future__ import annotations

from collections.abc import Iterable


def merge_segments(
    tracks: dict[str, Iterable[dict]], *, timestamp_key: str = "start", text_key: str = "text"
) -> list[dict]:
    """Merge timestamped transcription segments while retaining assigned labels.

    `tracks` maps the reliable PBX-derived speaker label to that leg's segments.
    It deliberately does not attempt speaker diarization.
    """

    turns: list[dict] = []
    for speaker, segments in tracks.items():
        for segment in segments:
            text = str(segment.get(text_key, "")).strip()
            if not text:
                continue
            turns.append(
                {
                    "at_s": round(float(segment.get(timestamp_key, 0)), 3),
                    "speaker": speaker,
                    "text": text,
                }
            )
    return sorted(turns, key=lambda turn: turn["at_s"])
