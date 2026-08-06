# Audio Meeting Summarizer - Frontend

A single-page React application that lets users upload an audio recording,
watch the transcript stream in live as faster-whisper produces it, choose a
summary type, and download the results as `.txt` and `.docx`.

Built with **React 19** and **Vite 8**. No UI framework, just plain CSS
with a minimal design system defined in `App.css`.

## Features

- Wakes the backend automatically on page load (scale-to-zero friendly) and
  shows a spinner until it's ready, then enables the upload form
- Streams the transcript live via Server-Sent Events, segment by segment,
  with automatic reconnection for long files split into chunks by the backend
- Falls back to polling if the SSE connection is dropped (e.g. by a proxy
  timeout), so a result is always delivered even on flaky connections
- Five summary types selectable after transcription: Meeting, Lecture,
  User Interview / CustDev, Sales Call, and Voice Note
- Transcript language selector (auto-detect by default), populated from the
  backend at startup
- Download transcript as `.txt` and summary as `.docx`

## Requirements

- Node.js 18+
- The backend running (see `backend/README.md`)

## Setup

```bash
cd frontend
npm install
npm run dev       # starts on http://localhost:5173
```

`/api/*` requests are proxied to `http://localhost:8000` in development by
`vite.config.js`, so no CORS configuration is needed locally.

## Scripts

| Command           | Description                              |
|-------------------|------------------------------------------|
| `npm run dev`     | Start the Vite dev server with HMR       |
| `npm run build`   | Production build → `dist/`              |
| `npm run preview` | Serve the production build locally       |
| `npm run lint`    | Run oxlint                               |

## Project layout

```
src/
  api/
    client.js           All fetch() calls in one place. Components and hooks
                        never call fetch directly; they import named functions
                        from here instead. If the base URL, auth headers, or
                        error handling strategy changes, this is the only file
                        to edit.

  hooks/
    useBackendWake.js   Polls GET /api/health until the backend responds with
                        200. Returns { isWaking }, and the rest of the app
                        stays disabled until isWaking is false.

    useJob.js           All job state (jobId, stage, transcript, summary,
                        language, error), the SSE connection lifecycle, the
                        polling fallback, and the upload() / summarize()
                        actions. App.jsx calls this hook and passes the result
                        to components as props.

  components/
    WakingBanner.jsx    Spinner + message shown while the backend is cold-starting.

    UploadPanel.jsx     File picker, beam size (transcription speed/accuracy
                        trade-off), language selector, and Upload button. Owns
                        its own local state (file, beamSize, languageChoice)
                        because those are purely UI concerns that reset on each
                        new upload and don't need to live in the hook.

    TranscriptPanel.jsx Transcript text, summary type selector, Summarize button,
                        and transcript download link. Receives transcript, stage,
                        summaryTypes, isBusy, and onSummarize as props.

    SummaryPanel.jsx    Rendered Markdown summary and summary download link.

  App.jsx               Thin coordinator: calls useBackendWake and useJob, fetches
                        the language and summary-type lists at startup, and
                        composes the four components. Contains no fetch() calls
                        and no SSE logic.

  App.css               All styles. One flat file, since the app is small
                        enough that a CSS framework would add more complexity
                        than it removes.
```

## Architecture notes

### Why custom hooks?

`useJob` extracts the stateful complexity (11 state variables, SSE lifecycle,
polling fallback, two async actions) out of the component tree so components
stay focused on rendering. The hook's public API is a flat object; components
destructure what they need and ignore the rest.

### Why an `api/` layer?

Every `fetch()` call goes through `src/api/client.js`. Components import
named functions (`uploadAudio`, `fetchJob`, `openTranscriptStream`, etc.)
rather than constructing requests inline. This makes the network contract
explicit, keeps components testable without network access, and means the
backend URL or auth strategy is changed in one place.

### SSE + polling fallback

The backend streams the transcript over Server-Sent Events. For long files
the audio is split into chunks server-side; the client reconnects for each
chunk when it receives a `chunk_done` event. If the SSE connection drops at
the network level (proxy timeout, Azure ingress limit), `es.onerror` switches
to polling `GET /api/jobs/{id}` every 10 seconds so the result is still
delivered when the backend finishes.

### Scale-to-zero

`useBackendWake` fires `GET /api/health` immediately on mount. This single
request wakes the Azure Container App from 0 replicas. The upload form
stays disabled, via the `isWaking` flag passed to `UploadPanel`, until the
backend responds with 200, which means the Whisper model is fully loaded
and the backend is ready to accept uploads.

## Production build

In production the frontend is served by nginx, which proxies `/api/*` to the
backend container. The nginx config is in `nginx.conf.template`; `BACKEND_URL`
is injected at container startup via `envsubst`.

```bash
npm run build        # output in dist/
docker build -t audio-frontend .
```
