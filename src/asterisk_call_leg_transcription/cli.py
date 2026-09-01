"""Command-line entry point for post-call MixMonitor packaging."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audio import write_package


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Package two Asterisk call-leg tracks as a labelled stereo WAV.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    pack = subcommands.add_parser("pack", help="package two 16-bit mono MixMonitor tracks")
    pack.add_argument("--left", required=True, type=Path, help="track written to stereo left")
    pack.add_argument("--right", required=True, type=Path, help="track written to stereo right")
    pack.add_argument("--output", required=True, type=Path, help="output stereo WAV")
    pack.add_argument("--left-label", default="caller")
    pack.add_argument("--right-label", default="agent")
    return parser


def main() -> None:
    args = _parser().parse_args()
    rate = write_package(args.left, args.right, args.output)
    labels_path = args.output.with_suffix(args.output.suffix + ".labels.json")
    labels_path.write_text(
        json.dumps(
            {
                "format": "16-bit stereo PCM WAV",
                "sample_rate_hz": rate,
                "left": args.left_label,
                "right": args.right_label,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
