import { useState } from "react";

export function HeroDescription() {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="hero">
      <p className="hero-intro">
        Turn any audio recording into a structured written summary — in
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
          <li>
            <span className="hero-step-num" aria-hidden="true">1</span>
            <div>
              <span className="hero-step-title">Upload your recording</span>
              <span className="hero-step-detail">
                Any common audio format works — .mp3, .wav, .m4a, and others.
                Long files are handled automatically, no trimming needed.
              </span>
            </div>
          </li>
          <li>
            <span className="hero-step-num" aria-hidden="true">2</span>
            <div>
              <span className="hero-step-title">Watch the transcript appear</span>
              <span className="hero-step-detail">
                Text streams in as it's ready — you can read along while the
                rest is still being processed.
              </span>
            </div>
          </li>
          <li>
            <span className="hero-step-num" aria-hidden="true">3</span>
            <div>
              <span className="hero-step-title">Get your summary</span>
              <span className="hero-step-detail">
                Choose the format that fits your content and download a
                ready-to-share .docx file.
              </span>
            </div>
          </li>
        </ol>
      )}
    </div>
  );
}
