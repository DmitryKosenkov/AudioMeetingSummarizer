import { useEffect, useRef, useState } from "react";
import { downloadUrl } from "../api/client";
import { STAGES } from "../hooks/useJob";

export function TranscriptPanel({
  jobId,
  transcript,
  stage,
  summaryTypes,
  isBusy,
  onSummarize,
}) {
  const [summaryTypeChoice, setSummaryTypeChoice] = useState(
    summaryTypes[0]?.value ?? "meeting"
  );

  const selectedType = summaryTypes.find((t) => t.value === summaryTypeChoice);

  const textBlockRef = useRef(null);
  useEffect(() => {
    if (textBlockRef.current) {
      const el = textBlockRef.current;
      el.scrollTop = el.scrollHeight;
    }
  }, [transcript]);

  return (
    <div className="panel">
      <h2>Transcript</h2>
      <p className="text-block" ref={textBlockRef}>{transcript}</p>

      {stage === STAGES.TRANSCRIBED && (
        <>
          <div className="language-selector">
            <label className="language-label" htmlFor="summary-type-select">
              Summary type
            </label>
            <select
              id="summary-type-select"
              value={summaryTypeChoice}
              onChange={(e) => setSummaryTypeChoice(e.target.value)}
              disabled={isBusy}
            >
              {summaryTypes.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            {selectedType?.description && (
              <p className="summary-type-description">{selectedType.description}</p>
            )}
          </div>

          <button onClick={() => onSummarize(summaryTypeChoice)} disabled={isBusy}>
            Summarize
          </button>
        </>
      )}

      <a className="button-link" href={downloadUrl(jobId, "txt")}>
        Download transcript (.txt)
      </a>
    </div>
  );
}
