"""Prompt templates used to call Gemini."""

# Maps WHISPER_LANGUAGE codes to language names Gemini can act on reliably.
# Falls back to the raw code for anything not listed.
LANGUAGE_NAMES = {
    "ru": "Russian",
    "en": "English",
    "uk": "Ukrainian",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "pt": "Portuguese",
    "it": "Italian",
    "pl": "Polish",
    "tr": "Turkish",
    "kk": "Kazakh",
}

MEETING_SUMMARY_PROMPT_TEMPLATE = """You will be given the transcript of a meeting.

Write a summary in {language}, formatted in Markdown so it can be converted
directly into a Word document. Translate every section heading into
{language} as well - do not leave them in English.

Structure the summary using these five sections, in this order:
1. Overview - a short 2-4 sentence summary of what the meeting was about.
2. Key Discussion Points - a bullet list of the main topics discussed.
3. Decisions Made - a bullet list of decisions reached. If none were made, state that clearly.
4. Action Items - a bullet list of action items, including the responsible person and deadline where mentioned. If none were mentioned, state that clearly.
5. Next Steps - a bullet list of what happens next, if mentioned. If not mentioned, state that clearly.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not invent names, dates, or decisions.

Transcript:
{text}
"""


def build_meeting_summary_prompt(text: str, language: str) -> str:
    """Build the meeting-summary prompt for the given transcript and
    WHISPER_LANGUAGE code (e.g. "ru", "en").
    """
    language_name = LANGUAGE_NAMES.get(language, language)
    return MEETING_SUMMARY_PROMPT_TEMPLATE.format(language=language_name, text=text)
