# MP3 Transcribe MCP Server

An MCP server that turns a **local** MP3 file into text. Everything runs on your machine:
the MP3 is split into chunks, each chunk is transcribed with [faster-whisper](https://github.com/SYSTRAN/faster-whisper),
and the results are merged into one transcript. No cloud service, API key, ffmpeg, or build/deploy step needed.

## How it works

Your MCP client (Cursor, Claude Desktop, ...) starts this server on your machine with `uvx`, which fetches the
Python code straight from this GitHub repository. When you ask the assistant to transcribe a file, it calls the
`transcribe_mp3` tool:

1. **Split** (`core.split_mp3`): the MP3 is cut into fixed-length chunks (default 450 s) with PyAV, without re-encoding.
2. **Transcribe** (`core.transcribe_mp3`): each chunk is transcribed by Whisper on the CPU, with silence skipped.
3. **Merge**: the per-chunk texts are joined, with a header for each part, into one `.txt` file. The text is also
   returned to the assistant so you can ask questions about it.

| File | Role |
| --- | --- |
| `src/mp3_transcribe_mcp/core.py` | Split, transcribe and merge logic |
| `src/mp3_transcribe_mcp/server.py` | MCP server (stdio) exposing the tools |
| `src/mp3_transcribe_mcp/cli.py` | Same logic as a command-line tool |
| `src/mp3_transcribe_mcp/selftest.py` | Test client that runs the MCP server end to end |
| `pyproject.toml` | Dependencies and the `mp3-transcribe-mcp`, `mp3-transcribe` and `mp3-transcribe-mcp-test` commands |

## Setup (Option A: uvx, recommended)

**1. Install uv** (one time):

```powershell
# Windows
winget install --id astral-sh.uv -e
```

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

uv installs Python automatically if needed. [Git](https://git-scm.com/downloads) must also be installed, because
uvx fetches the code from GitHub. On Windows, **restart Cursor or Claude Desktop** after installing so it
picks up the new PATH.

**2. Warm the cache** (optional, recommended). The first start downloads about 200 MB of dependencies, which can
exceed the MCP client's startup timeout. Run this once in a terminal:

```bash
uvx --from git+https://github.com/codesnippetsforall/MCP-Server-with-MP3-file-convert-into-Text-based-Response.git mp3-transcribe --help
```

**3. Add the server to your MCP config**: Cursor uses `~/.cursor/mcp.json` (Windows: `%USERPROFILE%\.cursor\mcp.json`),
and Claude Desktop uses `claude_desktop_config.json`:

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

If the client reports that `uvx` is not found, put the full path to `uvx` in `command`
(find it with `where uvx` on Windows or `which uvx` on macOS/Linux).

**4. Check it is connected.** In Cursor, open **Settings → Tools & MCP**: `mp3-transcribe` should show a green status
and 4 tools. Every start pulls the latest code from this repository.

## Setup (Option B: pip)

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

If you installed into a virtual environment, use the full path to `mp3-transcribe-mcp` (inside the venv's
`Scripts\` or `bin/` folder) as `command`. Update later with `pip install --upgrade git+https://...`.

## Usage

Ask your assistant in chat, for example:

- *"Transcribe C:\Users\me\Music\meeting.mp3"*
- *"List the MP3 files in C:\Users\me\Music and transcribe the newest one"*
- *"Transcribe meeting.mp3 with the small model and auto-detect the language"*

The Whisper model (~150 MB for `base`) is downloaded on first use. With `base` on a CPU, a 30-minute recording
takes about 5 minutes.

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
uvx --from git+https://github.com/codesnippetsforall/MCP-Server-with-MP3-file-convert-into-Text-based-Response.git mp3-transcribe path/to/meeting.mp3
```

Options: `--model`, `--language`, `--segment-seconds`, `--output-dir`, `--force`.

## Test the MCP server from a terminal

Run from any folder; no clone needed:

```bash
uvx --from git+https://github.com/codesnippetsforall/MCP-Server-with-MP3-file-convert-into-Text-based-Response.git mp3-transcribe-mcp-test path/to/meeting.mp3
```

The test client starts the server over stdio (as an MCP client does), lists the tools, transcribes the file
with progress output, and prints the result. Options: `--model`, `--force`.
