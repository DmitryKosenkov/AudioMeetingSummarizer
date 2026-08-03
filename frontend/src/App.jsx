import Markdown from "react-markdown";
import { useEffect, useRef, useState } from "react";
import "./App.css";

const API_BASE = "/api";

const AUTO_DETECT = "auto";

const STAGES = {
  IDLE: "idle",
  UPLOADING: "uploading",
  TRANSCRIBING: "transcribing",
  TRANSCRIBED: "transcribed",
  SUMMARIZING: "summarizing",
  DONE: "done",
  ERROR: "error",
};

export default function App() {
  const [file, setFile] = useState(null);
  const [beamSize, setBeamSize] = useState(2);
  const [availableLanguages, setAvailableLanguages] = useState([]);
  const [languageChoice, setLanguageChoice] = useState(AUTO_DETECT);
  const [summaryTypes, setSummaryTypes] = useState([]);
  const [summaryTypeChoice, setSummaryTypeChoice] = useState("meeting");
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState(STAGES.IDLE);
  const [language, setLanguage] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const eventSourceRef = useRef(null);

  useEffect(() => {
    fetch(`${API_BASE}/languages`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("failed"))))
      .then((data) => setAvailableLanguages(data.languages))
      .catch(() => {});

    fetch(`${API_BASE}/summary-types`)
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error("failed"))))
      .then((data) => {
        setSummaryTypes(data.types);
        setSummaryTypeChoice(data.default);
      })
      .catch(() => {});
  }, []);

  function reset() {
    eventSourceRef.current?.close();
    stopPolling();
    setJobId(null);
    setStage(STAGES.IDLE);
    setLanguage(null);
    setTranscript("");
    setSummary("");
    setError("");
  }

  function handleFileChange(e) {
    reset();
    setFile(e.target.files[0] || null);
  }

  async function handleUpload() {
    if (!file) return;
    setError("");
    setStage(STAGES.UPLOADING);

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("beam_size", beamSize);
      formData.append("language", languageChoice);

      const res = await fetch(`${API_BASE}/jobs`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) throw new Error(`Upload failed (${res.status})`);

      const data = await res.json();
      setJobId(data.job_id);
      startStreaming(data.job_id);
    } catch (err) {
      setError(err.message);
      setStage(STAGES.ERROR);
    }
  }

  const pollTimerRef = useRef(null);

  function stopPolling() {
    if (pollTimerRef.current) {
      clearInterval(pollTimerRef.current);
      pollTimerRef.current = null;
    }
  }

  function startPolling(id) {
    stopPolling();
    pollTimerRef.current = setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/jobs/${id}`);
        if (!res.ok) return;
        const data = await res.json();

        if (data.status === "transcribed" || data.status === "done") {
          stopPolling();
          setTranscript(data.transcript || "");
          if (data.detected_language) setLanguage(data.detected_language);
          setStage(STAGES.TRANSCRIBED);
        } else if (data.status === "error") {
          stopPolling();
          setError(data.error || "Transcription failed.");
          setStage(STAGES.ERROR);
        }
      } catch {
      }
    }, 10_000);
  }

  function startStreaming(id, chunkIndex = 0) {
    setStage(STAGES.TRANSCRIBING);
    if (chunkIndex === 0) setTranscript("");

    const es = new EventSource(`${API_BASE}/jobs/${id}/stream?chunk=${chunkIndex}`);
    eventSourceRef.current = es;

    es.addEventListener("language", (e) => setLanguage(JSON.parse(e.data)));

    es.addEventListener("segment", (e) => {
      const segment = JSON.parse(e.data);
      setTranscript((prev) => (prev ? `${prev} ${segment}` : segment));
    });

    es.addEventListener("chunk_done", (e) => {
      es.close();
      const nextChunk = parseInt(JSON.parse(e.data), 10);
      startStreaming(id, nextChunk);
    });

    es.addEventListener("done", (e) => {
      stopPolling();
      setTranscript(JSON.parse(e.data));
      setStage(STAGES.TRANSCRIBED);
      es.close();
    });

    es.addEventListener("error", (e) => {
      stopPolling();
      setError(JSON.parse(e.data) || "Transcription failed.");
      setStage(STAGES.ERROR);
      es.close();
    });

    es.onerror = () => {
      es.close();
      startPolling(id);
    };
  }

  async function handleSummarize() {
    if (!jobId) return;
    setError("");
    setStage(STAGES.SUMMARIZING);

    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/summarize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ summary_type: summaryTypeChoice }),
      });
      if (!res.ok) throw new Error(`Summarization failed (${res.status})`);

      const data = await res.json();
      setSummary(data.summary);
      setStage(STAGES.DONE);
    } catch (err) {
      setError(err.message);
      setStage(STAGES.ERROR);
    }
  }

  const isBusy =
    stage === STAGES.UPLOADING ||
    stage === STAGES.TRANSCRIBING ||
    stage === STAGES.SUMMARIZING;

  return (
    <div className="container">
      <h1>Audio Meeting Summarizer</h1>

      <div className="panel">
        <input type="file" accept="audio/*" onChange={handleFileChange} />
        <div className="beam-selector">
          <span className="beam-label">Transcription mode</span>
          <div className="beam-options">
            {[
              { value: 1, label: "Maximum speed",    hint: "beam size 1" },
              { value: 2, label: "Balanced",         hint: "beam size 2" },
              { value: 5, label: "Maximum accuracy", hint: "beam size 5" },
            ].map(({ value, label, hint }) => (
              <button
                key={value}
                className={`beam-option${beamSize === value ? " beam-option--active" : ""}`}
                onClick={() => setBeamSize(value)}
                disabled={isBusy}
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
            disabled={isBusy}
          >
            <option value={AUTO_DETECT}>Auto-detect</option>
            {availableLanguages.map(({ code, name }) => (
              <option key={code} value={code}>
                {name}
              </option>
            ))}
          </select>
        </div>
        <button onClick={handleUpload} disabled={!file || isBusy}>
          {stage === STAGES.UPLOADING ? "Uploading..." : "Upload & Transcribe"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {jobId && <p className="meta">Job ID: {jobId}</p>}
      {language && languageChoice === AUTO_DETECT && (
        <p className="meta">Detected language: {language}</p>
      )}

      {stage === STAGES.TRANSCRIBING && <p className="status">Transcribing...</p>}

      {transcript && (
        <div className="panel">
          <h2>Transcript</h2>
          <p className="text-block">{transcript}</p>

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
              </div>
              <button onClick={handleSummarize} disabled={isBusy}>
                Summarize
              </button>
            </>
          )}

          <a
            className="button-link"
            href={`${API_BASE}/jobs/${jobId}/download/txt`}
          >
            Download transcript (.txt)
          </a>
        </div>
      )}

      {stage === STAGES.SUMMARIZING && <p className="status">Summarizing...</p>}

      {summary && (
        <div className="panel">
          <h2>Summary</h2>
          <div className="markdown-body"><Markdown>{summary}</Markdown></div>
          <a
            className="button-link"
            href={`${API_BASE}/jobs/${jobId}/download/docx`}
          >
            Download summary (.docx)
          </a>
        </div>
      )}
    </div>
  );
}