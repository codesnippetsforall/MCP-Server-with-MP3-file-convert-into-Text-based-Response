# MP3 Transcribe MCP Server

An MCP server that turns a **local** MP3 file into text. Everything runs on your machine:
the MP3 is split into chunks, each chunk is transcribed with [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
and the results are merged into one transcript. No cloud service, API key, or ffmpeg install needed.

## Requirements

- Python 3.10+
- Optional: [uv](https://docs.astral.sh/uv/) (lets the MCP client run the server straight from GitHub)

The Whisper model (~150 MB for `base`) is downloaded automatically on first use.

## Add to your MCP client

**Option A: with uv (no install step)**: add this to your MCP config
(Cursor: `~/.cursor/mcp.json`, Claude Desktop: `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mp3-transcribe": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/codesnippetsforall/MCP-Server-with-MP3-file-convert-into-Text-based-Response.git",
        "mp3-transcribe-mcp"
      ]
    }
  }
}
```

**Option B: with pip**

```bash
pip install git+https://github.com/codesnippetsforall/MCP-Server-with-MP3-file-convert-into-Text-based-Response.git
```

```json
{
  "mcpServers": {
    "mp3-transcribe": { "command": "mp3-transcribe-mcp" }
  }
}
```

Then ask your assistant, for example: *"Transcribe C:\Users\me\Music\meeting.mp3"*.

## Tools

| Tool | What it does |
| --- | --- |
| `transcribe_mp3` | Split, transcribe every chunk, merge, and return the transcript |
| `split_mp3` | Only split the MP3 into chunks |
| `get_transcript` | Read a transcript produced earlier |
| `list_mp3_files` | List MP3 files in a folder |

`transcribe_mp3` options: `model_size` (`tiny`, `base`, `small`, `medium`, `large-v3`), `language` (`en` or `auto`),
`segment_seconds` (default 450), `output_dir`, `force`, `include_text`.

## Output (next to the MP3 by default)

```
meeting.mp3
meeting.txt                      merged transcript
parts/meeting_part00.mp3 ...     chunks
transcripts/meeting_part00.txt   per-chunk transcripts
```

Re-running skips chunks that already have a transcript, so an interrupted run resumes. Use `force` to redo everything.

## Command line (without MCP)

```bash
mp3-transcribe path/to/meeting.mp3 --model base --language en
```

## Test the server locally

```bash
python examples/test_client.py path/to/meeting.mp3
```
