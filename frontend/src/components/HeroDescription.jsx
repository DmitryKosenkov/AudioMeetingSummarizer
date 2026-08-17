import { useState } from "react";

const STEPS = [
  {
    title: "Upload your recording",
    detail: (
      <>
        Supported formats: <strong>.mp3, .wav, .m4a, .ogg, .flac, .webm,
        .opus, .aac</strong>. Any file size works, including recordings
        that are an hour long or more.
      </>
    ),
  },
  {
    title: "Choose a transcription mode",
    detail: (
      <>
        <strong>Balanced</strong> works well for most recordings and is
        selected by default. Choose <strong>Maximum speed</strong> if you
        need results quickly and the audio is clear. Choose{" "}
        <strong>Maximum accuracy</strong> for noisy recordings or heavy
        accents.
      </>
    ),
  },
  {
    title: "Set the transcript language",
    detail: (
      <>
        Leave it on <strong>Auto-detect</strong> if you are not sure.
        Selecting the language manually can improve accuracy. Supported
        languages: English, Russian, Ukrainian, Spanish, French, German,
        Portuguese, Italian, Polish, Turkish, and Kazakh.
      </>
    ),
  },
  {
    title: "Watch the transcript appear",
    detail: (
      <>
        Text appears segment by segment as it is processed. You can start
        reading right away without waiting for the full file to finish.
      </>
    ),
  },
  {
    title: "Choose a summary type",
    detail: (
      <>
        Pick the format that matches your recording:
        <ul className="hero-step-list">
          <li><strong>Meeting:</strong> overview, key points, decisions, action items, next steps.</li>
          <li><strong>Lecture:</strong> core topic, key concepts and definitions, takeaways, review questions.</li>
          <li><strong>Interview:</strong> participants, main themes, key statements, notable quotes.</li>
          <li><strong>Voice Note:</strong> core idea, structured breakdown, tasks and follow-ups.</li>
          <li><strong>General:</strong> works for anything that does not fit the types above.</li>
        </ul>
      </>
    ),
  },
  {
    title: "Download the results",
    detail: (
      <>
        Save the summary as a <strong>.docx</strong> file or the full
        transcript as a <strong>.txt</strong> file. Both are written in
        the same language as the recording.
      </>
    ),
  },
];

export function HeroDescription() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="hero">
      <p className="hero-intro">
        Turn any audio recording into a structured written summary in
        minutes, in your language.
      </p>
      <p className="hero-sub">
        Works for meetings, lectures, interviews, sales calls, voice notes,
        and more. Upload once, get a transcript and a formatted summary you
        can download and share.
      </p>

      <button
        className="hero-toggle"
        onClick={() => setExpanded((e) => !e)}
        aria-expanded={expanded}
      >
        {expanded ? "Hide instructions" : "How does it work?"}
      </button>

      {expanded && (
        <ol className="hero-steps">
          {STEPS.map(({ title, detail }, i) => (
            <li key={i}>
              <span className="hero-step-num" aria-hidden="true">{i + 1}</span>
              <div>
                <span className="hero-step-title">{title}</span>
                <span className="hero-step-detail">{detail}</span>
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
