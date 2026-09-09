import { useRef, useState } from "react";
import { STAGES } from "../hooks/useJob";

const AUTO_DETECT = "auto";

const BEAM_OPTIONS = [
  { value: 1, label: "Maximum speed",    hint: "beam size 1" },
  { value: 2, label: "Balanced",         hint: "beam size 2" },
  { value: 5, label: "Maximum accuracy", hint: "beam size 5" },
];

const ACCEPT = ".mp3,.wav,.m4a,.ogg,.flac,.webm,.aac";

export function UploadPanel({ languages, onUpload, disabled, stage }) {
  const [files,          setFiles]          = useState([]);
  const [beamSize,       setBeamSize]       = useState(2);
  const [languageChoice, setLanguageChoice] = useState(AUTO_DETECT);
  const [dragging,       setDragging]       = useState(false);

  const inputRef = useRef(null);

  function applyFiles(incoming) {
    if (!incoming || incoming.length === 0) return;
    // Merge with existing selection, deduplicating by name.
    setFiles((prev) => {
      const existing = new Set(prev.map((f) => f.name));
      const added = Array.from(incoming).filter((f) => !existing.has(f.name));
      return [...prev, ...added];
    });
  }

  function removeFile(name) {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  }

  function handleFileChange(e) {
    applyFiles(e.target.files);
    // Reset so the same file can be re-added after removal.
    e.target.value = "";
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
    applyFiles(e.dataTransfer.files);
  }

  function handleUpload() {
    if (files.length === 0) return;
    onUpload(files, { beamSize, language: languageChoice });
  }

  const isUploading = stage === STAGES.UPLOADING;
  const hasFiles = files.length > 0;

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
        aria-label="Upload audio files"
        onKeyDown={(e) => e.key === "Enter" && !disabled && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          onChange={handleFileChange}
          style={{ display: "none" }}
        />
        <img src="/folder.svg" alt="" className="drop-zone-icon" />
        {hasFiles ? (
          <p className="drop-zone-primary">
            {files.length === 1 ? "1 file selected" : `${files.length} files selected`}
          </p>
        ) : (
          <>
            <p className="drop-zone-primary">Drop your audio files here</p>
            <p className="drop-zone-secondary">
              or click to browse &middot; mp3, wav, m4a, ogg, flac, webm, opus, aac
            </p>
          </>
        )}
        {hasFiles && (
          <p className="drop-zone-secondary">Click to add more</p>
        )}
      </div>

      {/* File list */}
      {hasFiles && (
        <ul className="file-list">
          {files.map((f) => (
            <li key={f.name} className="file-list-item">
              <span className="file-list-name">{f.name}</span>
              <button
                className="file-list-remove"
                onClick={(e) => { e.stopPropagation(); removeFile(f.name); }}
                disabled={disabled}
                aria-label={`Remove ${f.name}`}
              >
                &times;
              </button>
            </li>
          ))}
        </ul>
      )}

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

      <button onClick={handleUpload} disabled={!hasFiles || disabled}>
        {isUploading ? "Uploading…" : "Upload & Transcribe"}
      </button>
    </div>
  );
}
