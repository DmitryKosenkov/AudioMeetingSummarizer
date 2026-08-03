"""Prompt templates used to call Gemini."""

from enum import Enum

# Maps Whisper language codes to language names Gemini can act on reliably.
# Falls back to the raw code for anything not listed. Also doubles as the
# set of languages the frontend lets the user pick from - see
# GET /api/languages in app/api/routes/jobs.py.
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


# ---------------------------------------------------------------------------
# Summary types
# ---------------------------------------------------------------------------

class SummaryType(str, Enum):
    MEETING    = "meeting"
    LECTURE    = "lecture"
    CUSTDEV    = "custdev"
    SALES      = "sales"
    VOICE_NOTE = "voice_note"


SUMMARY_TYPE_LABELS: dict[SummaryType, str] = {
    SummaryType.MEETING:    "Meeting",
    SummaryType.LECTURE:    "Lecture / Educational",
    SummaryType.CUSTDEV:    "User Interview / CustDev",
    SummaryType.SALES:      "Sales Call / Client Deal",
    SummaryType.VOICE_NOTE: "Voice Note / Stream of Consciousness",
}


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

_MEETING_PROMPT = """You will be given the transcript of a meeting.

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

_LECTURE_PROMPT = """You will be given the transcript of an educational lecture or lesson.

Write a structured study note in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these four sections, in this order:
1. Core Topic & Goal - 2-3 sentences explaining the main topic and what the lecture teaches.
2. Key Concepts & Definitions - a list of important terms, definitions, formulas, or concepts explained, using bold text for the terms (e.g., - **Term**: Definition).
3. Detailed Takeaways - a bulleted list breaking down the main arguments, theories, or steps taught in the lecture.
4. Review Questions - 3-5 self-test questions based strictly on the lecture content to help the student test their understanding.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not invent facts, theories, or terminology.

Transcript:
{text}
"""

_CUSTDEV_PROMPT = """You will be given the transcript of a user interview or customer research call (CustDev).

Write a customer research report in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these four sections, in this order:
1. Respondent Profile & Context - brief details about who the user is, their background, or current workflow mentioned in the call.
2. User Pain Points & Needs - a bullet list of specific problems, frustrations, or desires expressed by the user.
3. Feedback on Product/Solution - what the user likes, dislikes, or finds confusing about the current product or proposed ideas.
4. Notable Quotes - 2-4 verbatim or closely paraphrased impactful quotes from the user that capture their true emotions or thoughts.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not assume or invent user feedback.

Transcript:
{text}
"""

_SALES_PROMPT = """You will be given the transcript of a sales call or client discussion.

Write a commercial deal summary in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these four sections, in this order:
1. Deal Overview - 2-3 sentences summarizing the client's profile, what product/service was discussed, and the overall status of the deal.
2. Client Needs & Pain Points - a bullet list of the client's current challenges, requirements, and budget or timeline constraints mentioned.
3. Objections & Concerns - any hesitations, pricing concerns, or questions raised by the client. If none, state that clearly.
4. Next Steps & Agreed Action Items - next steps, follow-up calls, or deliverables required, including responsible parties and deadlines if mentioned.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not invent prices, commitments, or client needs.

Transcript:
{text}
"""

_VOICE_NOTE_PROMPT = """You will be given the transcript of an unstructured personal voice note or stream of consciousness recording.

Write a clear, structured digest in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these three sections, in this order:
1. Main Thought - a 1-2 sentence core message or thesis of what the speaker was thinking about.
2. Structured Breakdown - organize the thoughts, observations, or stories into logical bullet points or sub-topics.
3. Extracted Tasks & Ideas - a list of any actionable tasks, personal reminders, or potential creative ideas mentioned in the audio. If none, state that clearly.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Clean up filler words and repetitions while strictly preserving the original intent and ideas.

Transcript:
{text}
"""

_PROMPT_BY_TYPE: dict[SummaryType, str] = {
    SummaryType.MEETING:    _MEETING_PROMPT,
    SummaryType.LECTURE:    _LECTURE_PROMPT,
    SummaryType.CUSTDEV:    _CUSTDEV_PROMPT,
    SummaryType.SALES:      _SALES_PROMPT,
    SummaryType.VOICE_NOTE: _VOICE_NOTE_PROMPT,
}


# ---------------------------------------------------------------------------
# Public builder
# ---------------------------------------------------------------------------

def build_summary_prompt(
    text: str,
    language: str,
    summary_type: SummaryType = SummaryType.MEETING,
) -> str:
    language_name = LANGUAGE_NAMES.get(language, language)
    template = _PROMPT_BY_TYPE[summary_type]
    return template.format(language=language_name, text=text)


def build_meeting_summary_prompt(text: str, language: str) -> str:
    return build_summary_prompt(text, language, SummaryType.MEETING)
