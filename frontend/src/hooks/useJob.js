import { useRef, useState } from "react";
import {
  fetchJob,
  openTranscriptStream,
  summarizeJob,
  uploadAudio,
} from "../api/client";

export const STAGES = {
  IDLE:         "idle",
  UPLOADING:    "uploading",
  TRANSCRIBING: "transcribing",
  TRANSCRIBED:  "transcribed",
  SUMMARIZING:  "summarizing",
  DONE:         "done",
  ERROR:        "error",
};

const TYPING_CPS = 60;

export function useJob() {
  const [jobId,      setJobId]      = useState(null);
  const [stage,      setStage]      = useState(STAGES.IDLE);
  const [language,   setLanguage]   = useState(null);
  const [transcript, setTranscript] = useState("");
  const [summary,    setSummary]    = useState("");
  const [error,      setError]      = useState("");

  const esRef       = useRef(null);
  const pollRef     = useRef(null);

  const fullTextRef = useRef("");
  const queueRef    = useRef([]);
  const typingRef   = useRef(null);

  // Typing helpers

  function stopTyping() {
    if (typingRef.current) {
      clearInterval(typingRef.current);
      typingRef.current = null;
    }
  }

  function typeNextSegment() {
    if (typingRef.current || queueRef.current.length === 0) return;

    const segment   = queueRef.current.shift();
    const prefix    = fullTextRef.current ? fullTextRef.current + " " : "";
    const fullSegment = prefix + segment;
    let charIndex   = fullTextRef.current.length;

    typingRef.current = setInterval(() => {
      charIndex++;
      setTranscript(fullSegment.slice(0, charIndex));

      if (charIndex >= fullSegment.length) {
        stopTyping();
        fullTextRef.current = fullSegment;
        typeNextSegment();
      }
    }, 1000 / TYPING_CPS);
  }

  function enqueueSegment(seg) {
    queueRef.current.push(seg);
    typeNextSegment();
  }

  function resetTyping() {
    stopTyping();
    queueRef.current  = [];
    fullTextRef.current = "";
  }

  // Polling

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
          resetTyping();
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

  // Streaming

  function startStreaming(id, chunkIndex = 0) {
    setStage(STAGES.TRANSCRIBING);
    if (chunkIndex === 0) {
      resetTyping();
      setTranscript("");
    }

    const es = openTranscriptStream(id, chunkIndex);
    esRef.current = es;

    es.addEventListener("language", (e) => setLanguage(JSON.parse(e.data)));

    es.addEventListener("segment", (e) => {
      enqueueSegment(JSON.parse(e.data));
    });

    es.addEventListener("chunk_done", (e) => {
      es.close();
      startStreaming(id, parseInt(JSON.parse(e.data), 10));
    });

    es.addEventListener("done", (e) => {
      stopPolling();
      resetTyping();
      setTranscript(JSON.parse(e.data));
      setStage(STAGES.TRANSCRIBED);
      es.close();
    });

    es.addEventListener("error", (e) => {
      stopPolling();
      resetTyping();
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
    resetTyping();
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