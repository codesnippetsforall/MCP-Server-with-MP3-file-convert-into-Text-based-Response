"""Split an MP3 into parts, transcribe each part and merge into one transcript."""
from __future__ import annotations

import logging
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

import av

log = logging.getLogger("mp3_transcribe_mcp")

DEFAULT_SEGMENT_SECONDS = 450
DEFAULT_MODEL = "base"
DEFAULT_LANGUAGE = "en"

ProgressFn = Callable[[int, int, str], None]

_models: dict[str, object] = {}
_models_lock = threading.Lock()


@dataclass
class PartResult:
    audio: str
    transcript: str
    segments: int
    reused: bool


@dataclass
class TranscribeResult:
    source: str
    merged_transcript: str
    parts: list[PartResult] = field(default_factory=list)
    text: str = ""

    def to_dict(self, include_text: bool = True) -> dict:
        data = asdict(self)
        if not include_text:
            data.pop("text")
        return data


def safe_stem(mp3_path: Path) -> str:
    return re.sub(r"[^\w.-]+", "_", mp3_path.stem).strip("_") or "audio"


def output_paths(mp3_path: Path, output_dir: Path | None = None) -> tuple[Path, Path, Path]:
    """Return (parts_dir, transcripts_dir, merged_txt) for an MP3."""
    base = output_dir or mp3_path.parent
    return base / "parts", base / "transcripts", base / f"{mp3_path.stem}.txt"


def _resolve_mp3(mp3_path: str | Path) -> Path:
    path = Path(mp3_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"MP3 file not found: {path}")
    return path


def existing_parts(mp3_path: Path, parts_dir: Path) -> list[Path]:
    return sorted(parts_dir.glob(f"{safe_stem(mp3_path)}_part*.mp3"))


def split_mp3(
    mp3_path: str | Path,
    segment_seconds: int = DEFAULT_SEGMENT_SECONDS,
    output_dir: str | Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Split an MP3 into fixed-length parts without re-encoding.

    Existing parts are reused unless ``force`` is set.
    """
    if segment_seconds <= 0:
        raise ValueError("segment_seconds must be positive")
    src = _resolve_mp3(mp3_path)
    parts_dir, _, _ = output_paths(src, Path(output_dir) if output_dir else None)
    parts_dir.mkdir(parents=True, exist_ok=True)

    current = existing_parts(src, parts_dir)
    if current and not force:
        log.info("Reusing %d existing parts in %s", len(current), parts_dir)
        return current
    for old in current:
        old.unlink()

    stem = safe_stem(src)
    written: list[Path] = []
    with av.open(str(src)) as inp:
        if not inp.streams.audio:
            raise ValueError(f"No audio stream in {src}")
        in_stream = inp.streams.audio[0]
        time_base = in_stream.time_base
        out = out_stream = None
        index = -1
        offset = 0
        for packet in inp.demux(in_stream):
            if packet.pts is None:
                continue
            part = int(float(packet.pts * time_base) // segment_seconds)
            if part != index:
                if out is not None:
                    out.close()
                index = part
                path = parts_dir / f"{stem}_part{index:02d}.mp3"
                out = av.open(str(path), "w", format="mp3")
                out_stream = out.add_stream_from_template(in_stream)
                offset = packet.pts
                written.append(path)
            packet.pts -= offset
            if packet.dts is not None:
                packet.dts -= offset
            packet.stream = out_stream
            out.mux(packet)
        if out is not None:
            out.close()

    log.info("Split %s into %d parts", src.name, len(written))
    return written


def _get_model(model_size: str):
    with _models_lock:
        if model_size not in _models:
            from faster_whisper import WhisperModel

            log.info("Loading Whisper model '%s' (CPU int8)...", model_size)
            _models[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
        return _models[model_size]


def transcribe_mp3(
    mp3_path: str | Path,
    model_size: str = DEFAULT_MODEL,
    language: str | None = DEFAULT_LANGUAGE,
    segment_seconds: int = DEFAULT_SEGMENT_SECONDS,
    output_dir: str | Path | None = None,
    force: bool = False,
    on_progress: ProgressFn | None = None,
) -> TranscribeResult:
    """Split, transcribe every part and write the merged transcript.

    Parts that already have a transcript are skipped unless ``force`` is set,
    so an interrupted run can be resumed.
    """
    src = _resolve_mp3(mp3_path)
    out_base = Path(output_dir).expanduser().resolve() if output_dir else None
    _, transcripts_dir, merged_path = output_paths(src, out_base)
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    lang = None if not language or language.lower() == "auto" else language

    parts = split_mp3(src, segment_seconds, out_base, force=force)
    total = len(parts)
    result = TranscribeResult(source=str(src), merged_transcript=str(merged_path))
    bodies: list[str] = []

    for i, audio in enumerate(parts, start=1):
        part_txt = transcripts_dir / f"{audio.stem}.txt"
        if on_progress:
            on_progress(i - 1, total, f"Transcribing part {i}/{total}: {audio.name}")

        if part_txt.exists() and not force:
            body = part_txt.read_text(encoding="utf-8").strip()
            count = len(body.splitlines()) if body else 0
            reused = True
        else:
            model = _get_model(model_size)
            segments, _ = model.transcribe(str(audio), language=lang, vad_filter=True)
            lines = [s.text.strip() for s in segments if s.text.strip()]
            body = "\n".join(lines)
            part_txt.write_text(body + ("\n" if body else ""), encoding="utf-8")
            count = len(lines)
            reused = False

        log.info("[%d/%d] %s: %d segments%s", i, total, audio.name, count, " (reused)" if reused else "")
        result.parts.append(PartResult(str(audio), str(part_txt), count, reused))
        bodies.append(f"===== PART {i:02d} / {total:02d} ({audio.name}) =====\n{body}")

    result.text = "\n\n".join(bodies) + "\n"
    merged_path.write_text(result.text, encoding="utf-8")
    if on_progress:
        on_progress(total, total, f"Merged transcript written to {merged_path}")
    return result
