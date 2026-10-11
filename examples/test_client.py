"""Smoke-test the MCP server over stdio, the same way an MCP client launches it.

Usage: python examples/test_client.py <path-to-file.mp3> [model_size]
"""
import asyncio
import json
import sys

from mcp import Client, StdioServerParameters


async def main(mp3_path: str, model_size: str) -> None:
    params = StdioServerParameters(command=sys.executable, args=["-m", "mp3_transcribe_mcp.server"])

    async def on_progress(progress: float, total: float | None, message: str | None) -> None:
        print(f"  progress {progress:g}/{total:g} {message or ''}", flush=True)

    async with Client(params) as client:
        tools = await client.list_tools()
        print("Tools:", [t.name for t in tools.tools])

        result = await client.call_tool(
            "transcribe_mp3",
            {"mp3_path": mp3_path, "model_size": model_size, "include_text": False},
            progress_callback=on_progress,
        )
        if result.is_error:
            raise SystemExit(f"Tool error: {result.content}")
        print(json.dumps(result.structured_content, indent=2))

        text = await client.call_tool("get_transcript", {"mp3_path": mp3_path})
        preview = text.content[0].text if text.content else ""
        print("Transcript preview:\n" + preview[:500])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    asyncio.run(main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "base"))
