"""Converts a plain-text transcript into UTF-8 .txt bytes."""


def render_transcript_to_txt(text: str) -> bytes:
    """Return the transcript as UTF-8 bytes, ready to write to a .txt file."""
    return text.strip().encode("utf-8")
