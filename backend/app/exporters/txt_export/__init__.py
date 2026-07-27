"""Standalone transcript-to-.txt converter, usable independently of the bot:

    from app.exporters.txt_export import render_transcript_to_txt
    txt_bytes = render_transcript_to_txt(transcript_text)

Or from the command line:

    python -m app.exporters.txt_export input.txt output.txt
"""
from app.exporters.txt_export.converter import render_transcript_to_txt

__all__ = ["render_transcript_to_txt"]
