import { useRef, useState } from "react";
import {
  fetchJob,
  openTranscriptStream,
  summarizeJob,
  uploadAudio,
} from "../api/client";

export const STAGES = {
  IDLE:        "idle",
  UPLOADING:   "uploading",
  TRANSCRIBING:"transcribing",
  TRANSCRIBED: "transcribed",
  SUMMARIZING: "summarizing",
  DONE:        "done",
  ERROR:       "error",
};


export function useJob() {
  const [jobId, setJobId] = useState(null);
  const [stage, setStage] = useState(STAGES.IDLE);
  const [language, setLanguage] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [summary, setSummary] = useState("");
  const [error, setError] = useState("");

  const esRef = useRef(null);
  const pollRef = useRef(null);

  // Helpers

  function stopPolling() {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }

  function startPolling(id) {
    stopPolling();
    pollRef.current = setInterval(async () => {
      try {
        const data = await fetchJob(id);
        if (data.status === "transcribed" || data.status === "done") {
          stopPolling();
          setTranscript(data.transcript ?? "");
          if (data.detected_language) setLanguage(data.detected_language);
          setStage(STAGES.TRANSCRIBED);
        } else if (data.status === "error") {
          stopPolling();
          setError(data.error ?? "Transcription failed.");
          setStage(STAGES.ERROR);
        }
      } catch {
      }
    }, 10_000);
  }

  function startStreaming(id, chunkIndex = 0) {
    setStage(STAGES.TRANSCRIBING);
    if (chunkIndex === 0) setTranscript("");

    const es = openTranscriptStream(id, chunkIndex);
    esRef.current = es;

    es.addEventListener("language", (e) => setLanguage(JSON.parse(e.data)));

    es.addEventListener("segment", (e) => {
      const seg = JSON.parse(e.data);
      setTranscript((prev) => (prev ? `${prev} ${seg}` : seg));
    });

    es.addEventListener("chunk_done", (e) => {
      es.close();
      startStreaming(id, parseInt(JSON.parse(e.data), 10));
    });

    es.addEventListener("done", (e) => {
      stopPolling();
      setTranscript(JSON.parse(e.data));
      setStage(STAGES.TRANSCRIBED);
      es.close();
    });

    es.addEventListener("error", (e) => {
      stopPolling();
      setError(JSON.parse(e.data) ?? "Transcription failed.");
      setStage(STAGES.ERROR);
      es.close();
    });

    es.onerror = () => {
      es.close();
      startPolling(id);
    };
  }

  // API

  function reset() {
    esRef.current?.close();
    stopPolling();
    setJobId(null);
    setStage(STAGES.IDLE);
    setLanguage(null);
    setTranscript("");
    setSummary("");
    setError("");
  }

  async function upload(file, options) {
    setError("");
    setStage(STAGES.UPLOADING);
    try {
      const data = await uploadAudio(file, options);
      setJobId(data.job_id);
      startStreaming(data.job_id);
    } catch (err) {
      setError(err.message);
      setStage(STAGES.ERROR);
    }
  }

  async function summarize(summaryType) {
    if (!jobId) return;
    setError("");
    setStage(STAGES.SUMMARIZING);
    try {
      const data = await summarizeJob(jobId, summaryType);
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

  return {
    jobId, stage, language, transcript, summary, error, isBusy,
    upload, summarize, reset,
  };
}
