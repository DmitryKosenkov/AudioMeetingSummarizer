import { useState } from "react";
import { STAGES } from "../hooks/useJob";

const AUTO_DETECT = "auto";

const BEAM_OPTIONS = [
  { value: 1, label: "Maximum speed",    hint: "beam size 1" },
  { value: 2, label: "Balanced",         hint: "beam size 2" },
  { value: 5, label: "Maximum accuracy", hint: "beam size 5" },
];

export function UploadPanel({ languages, onUpload, disabled, stage }) {
  const [file,           setFile]           = useState(null);
  const [beamSize,       setBeamSize]       = useState(2);
  const [languageChoice, setLanguageChoice] = useState(AUTO_DETECT);

  function handleFileChange(e) {
    setFile(e.target.files[0] ?? null);
  }

  function handleUpload() {
    if (!file) return;
    onUpload(file, { beamSize, language: languageChoice });
  }

  return (
    <div className="panel">
      <input type="file" accept="audio/*" onChange={handleFileChange} />

      <div className="beam-selector">
        <span className="beam-label">Transcription mode</span>
        <div className="beam-options">
          {BEAM_OPTIONS.map(({ value, label, hint }) => (
            <button
              key={value}
              className={`beam-option${beamSize === value ? " beam-option--active" : ""}`}
              onClick={() => setBeamSize(value)}
              disabled={disabled}
              title={hint}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="language-selector">
        <label className="language-label" htmlFor="language-select">
          Transcript language
        </label>
        <select
          id="language-select"
          value={languageChoice}
          onChange={(e) => setLanguageChoice(e.target.value)}
          disabled={disabled}
        >
          <option value={AUTO_DETECT}>Auto-detect</option>
          {languages.map(({ code, name }) => (
            <option key={code} value={code}>{name}</option>
          ))}
        </select>
      </div>

      <button onClick={handleUpload} disabled={!file || disabled}>
        {stage === STAGES.UPLOADING ? "Uploading…" : "Upload & Transcribe"}
      </button>
    </div>
  );
}
