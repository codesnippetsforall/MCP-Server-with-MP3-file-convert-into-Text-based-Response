"""MCP server exposing local MP3 splitting and transcription tools (stdio)."""
from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import anyio
import anyio.from_thread
from mcp.server.mcpserver import Context, MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import __version__, core


@contextmanager
def _as_tool_error() -> Iterator[None]:
    """Surface the real cause to the client instead of a generic failure message."""
    try:
        yield
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(f"{type(exc).__name__}: {exc}") from exc


server = MCPServer(
    name="mp3-transcribe",
    version=__version__,
    instructions=(
        "Transcribes local MP3 files to text on the user's machine. "
        "Use transcribe_mp3 with an absolute path to an .mp3 file. "
        "Outputs are written next to the MP3: parts/, transcripts/ and <name>.txt."
    ),
)


@server.tool()
async def transcribe_mp3(
    mp3_path: str,
    ctx: Context,
    model_size: str = core.DEFAULT_MODEL,
    language: str = core.DEFAULT_LANGUAGE,
    segment_seconds: int = core.DEFAULT_SEGMENT_SECONDS,
    output_dir: str | None = None,
    force: bool = False,
    include_text: bool = True,
) -> dict[str, Any]:
    """Split a local MP3 into chunks, transcribe each chunk and merge into one transcript.

    Args:
        mp3_path: Absolute path to the .mp3 file on this machine.
        model_size: Whisper model: tiny, base, small, medium, large-v3 (bigger = slower, more accurate).
        language: Spoken language code such as "en", or "auto" to detect.
        segment_seconds: Length of each chunk in seconds.
        output_dir: Folder for parts/, transcripts/ and the merged .txt. Defaults to the MP3's folder.
        force: Re-split and re-transcribe even if earlier outputs exist.
        include_text: Return the merged transcript text in the response.
    """

    def progress(done: int, total: int, message: str) -> None:
        anyio.from_thread.run(ctx.report_progress, done, total, message)

    with _as_tool_error():
        result = await anyio.to_thread.run_sync(
            lambda: core.transcribe_mp3(
                mp3_path,
                model_size=model_size,
                language=language,
                segment_seconds=segment_seconds,
                output_dir=output_dir,
                force=force,
                on_progress=progress,
            )
        )
    return result.to_dict(include_text=include_text)


@server.tool()
async def split_mp3(
    mp3_path: str,
    segment_seconds: int = core.DEFAULT_SEGMENT_SECONDS,
    output_dir: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Split a local MP3 into fixed-length chunks (no re-encoding) without transcribing.

    Args:
        mp3_path: Absolute path to the .mp3 file on this machine.
        segment_seconds: Length of each chunk in seconds.
        output_dir: Folder in which parts/ is created. Defaults to the MP3's folder.
        force: Re-split even if parts already exist.
    """
    with _as_tool_error():
        parts = await anyio.to_thread.run_sync(
            lambda: core.split_mp3(mp3_path, segment_seconds, output_dir, force=force)
        )
    return {"source": mp3_path, "parts": [str(p) for p in parts]}


@server.tool()
def get_transcript(mp3_path: str, output_dir: str | None = None) -> str:
    """Return the merged transcript previously produced for a local MP3.

    Args:
        mp3_path: Absolute path to the .mp3 file that was transcribed.
        output_dir: Same output_dir used when transcribing, if any.
    """
    src = Path(mp3_path).expanduser().resolve()
    _, _, merged = core.output_paths(src, Path(output_dir).expanduser().resolve() if output_dir else None)
    if not merged.is_file():
        raise ToolError(f"No transcript found at {merged}. Run transcribe_mp3 first.")
    return merged.read_text(encoding="utf-8")


@server.tool()
def list_mp3_files(directory: str) -> list[str]:
    """List .mp3 files in a local folder (not recursive), excluding generated parts.

    Args:
        directory: Absolute path to the folder.
    """
    folder = Path(directory).expanduser().resolve()
    if not folder.is_dir():
        raise ToolError(f"Folder not found: {folder}")
    return sorted(str(p) for p in folder.glob("*.mp3") if p.is_file())


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(levelname)s %(message)s")
    server.run("stdio")


if __name__ == "__main__":
    main()
