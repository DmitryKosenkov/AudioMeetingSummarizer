
const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    let message;
    try {
      const body = await res.json();
      message = body.detail ?? `Request failed (${res.status})`;
    } catch {
      message = `Request failed (${res.status})`;
    }
    throw new Error(message);
  }
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

export function uploadAudio(files, { beamSize, language }) {
  const form = new FormData();
  for (const file of files) {
    form.append("files", file);
  }
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
