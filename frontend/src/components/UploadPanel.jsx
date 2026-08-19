import { useRef, useState } from "react";
import { STAGES } from "../hooks/useJob";

const AUTO_DETECT = "auto";

const BEAM_OPTIONS = [
  { value: 1, label: "Maximum speed",    hint: "beam size 1" },
  { value: 2, label: "Balanced",         hint: "beam size 2" },
  { value: 5, label: "Maximum accuracy", hint: "beam size 5" },
];

const ACCEPT = ".mp3,.wav,.m4a,.ogg,.flac,.webm,.opus,.aac";

export function UploadPanel({ languages, onUpload, disabled, stage }) {
  const [file,           setFile]           = useState(null);
  const [beamSize,       setBeamSize]       = useState(2);
  const [languageChoice, setLanguageChoice] = useState(AUTO_DETECT);
  const [dragging,       setDragging]       = useState(false);

  const inputRef = useRef(null);

  function applyFile(f) {
    if (f) setFile(f);
  }

  function handleFileChange(e) {
    applyFile(e.target.files[0] ?? null);
  }

  function handleDragOver(e) {
    e.preventDefault();
    if (!disabled) setDragging(true);
  }

  function handleDragLeave(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    applyFile(e.dataTransfer.files[0] ?? null);
  }

  function handleUpload() {
    if (!file) return;
    onUpload(file, { beamSize, language: languageChoice });
  }

  const isUploading = stage === STAGES.UPLOADING;

  return (
    <div className="panel">

      {/* Drop zone */}
      <div
        className={`drop-zone${dragging ? " drop-zone--active" : ""}${disabled ? " drop-zone--disabled" : ""}`}
        onClick={() => !disabled && inputRef.current?.click()}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        role="button"
        tabIndex={disabled ? -1 : 0}
        aria-label="Upload audio file"
        onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        <img src="/folder.svg" alt="" className="drop-zone-icon" />
        {file ? (
          <p className="drop-zone-filename">{file.name}</p>
        ) : (
          <>
            <p className="drop-zone-primary">Drop your audio file here</p>
            <p className="drop-zone-secondary">
              or click to browse &middot; mp3, wav, m4a, ogg, flac, webm, opus, aac
            </p>
          </>
        )}
      </div>

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
        {isUploading ? "Uploading…" : "Upload & Transcribe"}
      </button>
    </div>
  );
}
