import Markdown from "react-markdown";
import { downloadUrl } from "../api/client";

export function SummaryPanel({ jobId, summary }) {
  return (
    <div className="panel">
      <h2>Summary</h2>
      <div className="markdown-body">
        <Markdown>{summary}</Markdown>
      </div>
      <a className="button-link" href={downloadUrl(jobId, "docx")}>
        Download summary (.docx)
      </a>
    </div>
  );
}
