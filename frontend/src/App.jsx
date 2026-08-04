import { useEffect, useState } from "react";
import { fetchLanguages, fetchSummaryTypes } from "./api/client";
import { WakingBanner }    from "./components/WakingBanner";
import { UploadPanel }     from "./components/UploadPanel";
import { TranscriptPanel } from "./components/TranscriptPanel";
import { SummaryPanel }    from "./components/SummaryPanel";
import { useBackendWake }  from "./hooks/useBackendWake";
import { useJob, STAGES }  from "./hooks/useJob";
import "./App.css";

export default function App() {
  const { isWaking } = useBackendWake();
  const job= useJob();
  const [languages,    setLanguages] = useState([]);
  const [summaryTypes, setSummaryTypes] = useState([]);

  useEffect(() => {
    fetchLanguages()
      .then((data) => setLanguages(data.languages))
      .catch(() => {});

    fetchSummaryTypes()
      .then((data) => setSummaryTypes(data.types))
      .catch(() => {});
  }, []);

  return (
    <div className="container">
      <h1>Audio Meeting Summarizer</h1>

      {isWaking && <WakingBanner />}

      <UploadPanel
        languages={languages}
        onUpload={job.upload}
        disabled={isWaking || job.isBusy}
        stage={job.stage}
      />

      {job.error && <p className="error">{job.error}</p>}

      {job.jobId && <p className="meta">Job ID: {job.jobId}</p>}
      {job.language && <p className="meta">Detected language: {job.language}</p>}

      {job.stage === STAGES.TRANSCRIBING && (
        <p className="status">Transcribing…</p>
      )}

      {job.transcript && (
        <TranscriptPanel
          jobId={job.jobId}
          transcript={job.transcript}
          stage={job.stage}
          summaryTypes={summaryTypes}
          isBusy={job.isBusy}
          onSummarize={job.summarize}
        />
      )}

      {job.stage === STAGES.SUMMARIZING && (
        <p className="status">Summarizing…</p>
      )}

      {job.summary && (
        <SummaryPanel jobId={job.jobId} summary={job.summary} />
      )}
    </div>
  );
}
