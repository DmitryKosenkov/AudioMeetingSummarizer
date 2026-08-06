"""Prompt templates used to call Gemini."""

from enum import Enum

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
    INTERVIEW  = "interview"
    VOICE_NOTE = "voice_note"
    GENERAL    = "general"


SUMMARY_TYPE_LABELS: dict[SummaryType, str] = {
    SummaryType.MEETING:    "Meeting",
    SummaryType.LECTURE:    "Lecture / Educational",
    SummaryType.INTERVIEW:  "Interview",
    SummaryType.VOICE_NOTE: "Voice Note",
    SummaryType.GENERAL:    "General",
}


# ---------------------------------------------------------------------------
# Prompt templates  (one per summary type)
# ---------------------------------------------------------------------------

_MEETING_PROMPT = """You will be given the transcript of a meeting.

Write a summary in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these five sections, in this order:
1. Overview - a short 2-4 sentence summary of what the meeting was about and who participated, if identifiable.
2. Key Discussion Points - a bullet list of the main topics discussed.
3. Decisions Made - a bullet list of decisions reached. If none were made, state that clearly.
4. Action Items - a bullet list of action items, including the responsible person and deadline where mentioned. If none were mentioned, state that clearly.
5. Next Steps - a bullet list of what happens next, if mentioned. If not mentioned, state that clearly.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not invent names, dates, or decisions.

Transcript:
{text}
"""

_LECTURE_PROMPT = """You will be given the transcript of an educational lecture, lesson, tutorial, or presentation.

Write a structured study note in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these four sections, in this order:
1. Core Topic & Goal - 2-3 sentences explaining the main subject and what the listener is meant to learn or take away.
2. Key Concepts & Definitions - a list of important terms, definitions, formulas, or concepts introduced, using bold text for each term (e.g., - **Term**: Definition).
3. Detailed Takeaways - a bulleted breakdown of the main arguments, methods, steps, or ideas covered in order.
4. Review Questions - 3-5 self-test questions based strictly on the content to help the listener check their understanding.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not invent facts, theories, or terminology.

Transcript:
{text}
"""

_INTERVIEW_PROMPT = """You will be given the transcript of an interview. This may be a job interview, podcast, journalistic interview, user research call, sales call, or any other question-and-answer dialogue between two or more people.

Write an interview summary in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these four sections, in this order:
1. Participants & Context - briefly describe who is speaking and what the interview is about, based only on what is stated or clearly implied in the transcript.
2. Main Themes & Topics - a bullet list of the key subjects covered, in the order they arose.
3. Key Statements & Insights - the most important answers, opinions, facts, or revelations from the interviewee. Use bullet points, and attribute each point to the speaker if identifiable.
4. Notable Quotes - 2-4 direct or closely paraphrased quotes that best capture the interviewee's voice, stance, or a pivotal moment in the conversation.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Only include information present in the transcript - do not assume context, roles, or opinions not expressed.

Transcript:
{text}
"""

_VOICE_NOTE_PROMPT = """You will be given the transcript of an unstructured personal voice note, memo, or stream-of-consciousness recording made by a single speaker.

Write a clear, structured digest in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these three sections, in this order:
1. Core Idea - a 1-2 sentence statement of the central thought, question, or topic the speaker was exploring.
2. Breakdown - reorganize the speaker's thoughts into logical bullet points or named sub-topics, preserving their intent while removing filler words and repetition.
3. Tasks & Ideas to Follow Up - a bullet list of any actionable items, reminders, decisions pending, or creative ideas mentioned. If none are present, state that clearly.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Preserve the speaker's original meaning and intent exactly - do not reinterpret, editorialize, or add information.

Transcript:
{text}
"""

_GENERAL_PROMPT = """You will be given an audio transcript. It may be a conversation, a monologue, a discussion, a recording, or any other type of spoken content.

Write a concise, structured summary in {language}, formatted in Markdown. Translate every section heading into {language} as well - do not leave them in English.

Structure the summary using these three sections, in this order:
1. What This Is About - 2-3 sentences describing the type of content, the speaker(s) if identifiable, and the overall subject.
2. Key Points - a bullet list of the most important information, ideas, or events covered, in the order they appear.
3. Action Items & Conclusions - any decisions made, tasks mentioned, or conclusions reached. If none are present, state that clearly.

Use "#" for the main title, "##" for section headings, and "-" for bullet points.
Make no assumptions about the context or purpose of the recording - only summarize what is explicitly present in the transcript.

Transcript:
{text}
"""

_PROMPT_BY_TYPE: dict[SummaryType, str] = {
    SummaryType.MEETING:    _MEETING_PROMPT,
    SummaryType.LECTURE:    _LECTURE_PROMPT,
    SummaryType.INTERVIEW:  _INTERVIEW_PROMPT,
    SummaryType.VOICE_NOTE: _VOICE_NOTE_PROMPT,
    SummaryType.GENERAL:    _GENERAL_PROMPT,
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
