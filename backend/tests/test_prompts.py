import re

from app.services.prompts import build_meeting_summary_prompt


def test_known_language_code_is_expanded_to_a_name():
    prompt = build_meeting_summary_prompt("some transcript", "ru")
    assert "Russian" in prompt
    # the raw code shouldn't leak into the instructions as its own word
    # (can't just check "ru" not in prompt - "Structure" contains "ru")
    instructions = prompt.split("Transcript:")[0]
    assert not re.search(r"\bru\b", instructions)


def test_unknown_language_code_falls_back_to_the_raw_code():
    prompt = build_meeting_summary_prompt("some transcript", "xx")
    assert "xx" in prompt


def test_transcript_text_is_included_verbatim():
    prompt = build_meeting_summary_prompt("Alice: let's ship it.", "en")
    assert "Alice: let's ship it." in prompt
