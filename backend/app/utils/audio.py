import logging
import math
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


_SPLIT_THRESHOLD_SECONDS = 600  # 10 min

_CHUNK_SECONDS = 600


def probe_duration(audio_path: str) -> float | None:
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError, OSError):
        logger.warning("ffprobe failed for %s — duration unknown", audio_path)
        return None


def split_audio(
    audio_path: str,
    chunk_seconds: int = _CHUNK_SECONDS,
    threshold_seconds: int = _SPLIT_THRESHOLD_SECONDS,
) -> list[str]:
    duration = probe_duration(audio_path)
    if duration is None or duration <= threshold_seconds:
        return [audio_path]

    ext = os.path.splitext(audio_path)[1] or ".mp3"
    n_chunks = math.ceil(duration / chunk_seconds)
    logger.info(
        "Audio duration %.0fs — splitting into %d chunks of %ds each",
        duration,
        n_chunks,
        chunk_seconds,
    )

    chunk_paths: list[str] = []
    try:
        for i in range(n_chunks):
            start = i * chunk_seconds
            # Use a named temp file so faster-whisper can re-read it by path.
            fd, chunk_path = tempfile.mkstemp(suffix=f"_chunk{i}{ext}")
            os.close(fd)
            chunk_paths.append(chunk_path)

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",                        # overwrite if exists
                    "-ss", str(start),
                    "-t", str(chunk_seconds),
                    "-i", audio_path,
                    "-c", "copy",                # no re-encode — fast
                    chunk_path,
                ],
                capture_output=True,
                check=True,
            )
            logger.info("Wrote chunk %d/%d → %s", i + 1, n_chunks, chunk_path)
    except subprocess.CalledProcessError as exc:
        logger.exception("ffmpeg failed while splitting %s", audio_path)
        for path in chunk_paths:
            _safe_unlink(path)
        raise RuntimeError("Audio splitting failed") from exc

    return chunk_paths


def merge_audio_files(paths: list[str]) -> str:
    if len(paths) == 1:
        return paths[0]

    fd, merged_path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    try:
        cmd = ["ffmpeg", "-y"]
        for p in paths:
            cmd += ["-i", p]

        n = len(paths)
        filter_inputs = "".join(f"[{i}:a]" for i in range(n))
        filter_complex = f"{filter_inputs}concat=n={n}:v=0:a=1[out]"

        cmd += [
            "-filter_complex", filter_complex,
            "-map", "[out]",
            "-ar", "16000",   # 16 kHz — matches Whisper's native sample rate
            "-ac", "1",       # mono
            merged_path,
        ]

        subprocess.run(cmd, capture_output=True, check=True)
        logger.info("Merged %d files into %s", len(paths), merged_path)
        return merged_path
    except subprocess.CalledProcessError as exc:
        _safe_unlink(merged_path)
        raise RuntimeError("Audio merge failed") from exc


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass