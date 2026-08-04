
const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`${options.method ?? "GET"} ${path} failed (${res.status})`);
  return res.json();
}

// Bootstrap

export function fetchHealth() {
  return fetch(`${BASE}/health`);   // raw Response — caller checks res.ok
}

export function fetchLanguages() {
  return request("/languages");
}

export function fetchSummaryTypes() {
  return request("/summary-types");
}

// Jobs

export function uploadAudio(file, { beamSize, language }) {
  const form = new FormData();
  form.append("file", file);
  form.append("beam_size", beamSize);
  form.append("language", language);
  return request("/jobs", { method: "POST", body: form });
}

export function fetchJob(jobId) {
  return request(`/jobs/${jobId}`);
}

export function summarizeJob(jobId, summaryType) {
  return request(`/jobs/${jobId}/summarize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ summary_type: summaryType }),
  });
}

export function openTranscriptStream(jobId, chunkIndex) {
  return new EventSource(`${BASE}/jobs/${jobId}/stream?chunk=${chunkIndex}`);
}

export function downloadUrl(jobId, format) {
  return `${BASE}/jobs/${jobId}/download/${format}`;
}
