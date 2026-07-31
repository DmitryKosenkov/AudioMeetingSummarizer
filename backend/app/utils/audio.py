"""Audio utilities — currently just file splitting via ffmpeg.

We split long files into fixed-length chunks before transcription so that
each chunk finishes quickly enough to keep the SSE connection alive on
Azure Container Apps (which recycles long-running connections).

ffmpeg is already installed in the backend Docker image, so no extra Python
dependency is needed.
"""
import logging
import math
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)

# Audio longer than this gets split.  Under this threshold we transcribe
# the whole file in one shot.
_SPLIT_THRESHOLD_SECONDS = 600  # 10 min

# How long each split chunk should be.  Shorter → more chunks but each
# finishes faster.  At ~1× real-time on the small Whisper model (CPU),
# a 10-minute chunk takes roughly 10 minutes to transcribe — comfortably
# under a 30-minute connection limit.
_CHUNK_SECONDS = 600  # 10 min


def probe_duration(audio_path: str) -> float | None:
    """Return the duration of *audio_path* in seconds, or None on error."""
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
    """Split *audio_path* into fixed-length chunks if it is longer than
    *threshold_seconds*.

    Returns a list of file paths.  If the file is short enough, the list
    contains only the original path and no splitting is done.  If splitting
    is performed, the returned paths are new temporary files that the caller
    is responsible for deleting.
    """
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
        # Clean up any chunks already written and re-raise so the job fails
        # cleanly rather than silently transcribing a partial file.
        for path in chunk_paths:
            _safe_unlink(path)
        raise RuntimeError("Audio splitting failed") from exc

    return chunk_paths


def _safe_unlink(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass
