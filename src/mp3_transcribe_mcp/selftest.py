"""Smoke-test the MCP server over stdio, the same way an MCP client launches it.

Usage: mp3-transcribe-mcp-test <file.mp3> [--model base] [--force]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mcp import Client, StdioServerParameters


async def run(mp3_path: str, model_size: str, force: bool) -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "mp3_transcribe_mcp.server"])

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        print(f"  progress {progress:g}/{total or 0:g} {message or ''}", flush=True)

    async with Client(params) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools.tools])

        result = await client.call_tool(
            "transcribe_mp3",
            {"mp3_path": mp3_path, "model_size": model_size, "force": force, "include_text": False},
            progress_callback=on_progress,
        )
        if result.is_error:
            raise SystemExit(f"Tool error: {result.content[0].text if result.content else result}")
        print(json.dumps(result.structured_content, indent=2))

        text = await client.call_tool("get_transcript", {"mp3_path": mp3_path})
        preview = text.content[0].text if text.content else ""
        print("Transcript preview:\n" + preview[:500])


def main() -> None:
    parser = argparse.ArgumentParser(description="Test the MP3 transcribe MCP server end to end.")
    parser.add_argument("mp3_path", help="Path to the .mp3 file")
    parser.add_argument("--model", default="base", help="Whisper model size (default: base)")
    parser.add_argument("--force", action="store_true", help="Re-split and re-transcribe")
    args = parser.parse_args()
    asyncio.run(run(str(Path(args.mp3_path).resolve()), args.model, args.force))


if __name__ == "__main__":
    main()
