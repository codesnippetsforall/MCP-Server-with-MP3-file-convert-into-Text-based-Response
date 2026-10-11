"""Command-line entry point: mp3-transcribe <file.mp3> [options]."""
from __future__ import annotations

import argparse
import logging
import sys

from . import core


def main() -> None:
    parser = argparse.ArgumentParser(description="Split and transcribe a local MP3 file.")
    parser.add_argument("mp3_path", help="Path to the .mp3 file")
    parser.add_argument("--model", default=core.DEFAULT_MODEL, help="Whisper model size (default: base)")
    parser.add_argument("--language", default=core.DEFAULT_LANGUAGE, help='Language code or "auto" (default: en)')
    parser.add_argument("--segment-seconds", type=int, default=core.DEFAULT_SEGMENT_SECONDS)
    parser.add_argument("--output-dir", default=None, help="Defaults to the MP3's folder")
    parser.add_argument("--force", action="store_true", help="Re-split and re-transcribe")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    result = core.transcribe_mp3(
        args.mp3_path,
        model_size=args.model,
        language=args.language,
        segment_seconds=args.segment_seconds,
        output_dir=args.output_dir,
        force=args.force,
        on_progress=lambda done, total, msg: print(msg, file=sys.stderr, flush=True),
    )
    print(result.merged_transcript)


if __name__ == "__main__":
    main()
