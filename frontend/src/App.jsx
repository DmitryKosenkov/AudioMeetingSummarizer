import { useRef, useState } from "react";
import "./App.css";


const API_BASE = "/api";

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
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState(STAGES.IDLE);
  const [language, setLanguage] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");
  const eventSourceRef = useRef(null);

  function reset() {
    eventSourceRef.current?.close();
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

  function startStreaming(id) {
    setStage(STAGES.TRANSCRIBING);
    setTranscript("");

    const es = new EventSource(`${API_BASE}/jobs/${id}/stream`);
    eventSourceRef.current = es;

    es.addEventListener("language", (e) => setLanguage(JSON.parse(e.data)));

    es.addEventListener("segment", (e) => {
      const segment = JSON.parse(e.data);
      setTranscript((prev) => (prev ? `${prev} ${segment}` : segment));
    });

    es.addEventListener("done", (e) => {
      setTranscript(JSON.parse(e.data));
      setStage(STAGES.TRANSCRIBED);
      es.close();
    });

    es.addEventListener("error", (e) => {
      setError(JSON.parse(e.data) || "Transcription failed.");
      setStage(STAGES.ERROR);
      es.close();
    });

    // Fires on network-level errors too (e.g. connection dropped)
    es.onerror = () => {
      if (stage !== STAGES.TRANSCRIBED) {
        setError((prev) => prev || "Connection to server lost during streaming.");
      }
      es.close();
    };
  }

  async function handleSummarize() {
    if (!jobId) return;
    setError("");
    setStage(STAGES.SUMMARIZING);

    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}/summarize`, {
        method: "POST",
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
        <button onClick={handleUpload} disabled={!file || isBusy}>
          {stage === STAGES.UPLOADING ? "Uploading..." : "Upload & Transcribe"}
        </button>
      </div>

      {error && <p className="error">{error}</p>}

      {jobId && <p className="meta">Job ID: {jobId}</p>}
      {language && <p className="meta">Detected language: {language}</p>}

      {stage === STAGES.TRANSCRIBING && <p className="status">Transcribing...</p>}

      {transcript && (
        <div className="panel">
          <h2>Transcript</h2>
          <p className="text-block">{transcript}</p>

          {stage === STAGES.TRANSCRIBED && (
            <button onClick={handleSummarize} disabled={isBusy}>
              Summarize
            </button>
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
          <p className="text-block">{summary}</p>
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
