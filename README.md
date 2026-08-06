# Audio Meeting Summarizer

Upload a meeting recording, watch it get transcribed live (faster-whisper),
then generate an AI summary (Gemini). Transcript and summary are both
downloadable when they're ready.

## Architecture

```
.
├── backend/            FastAPI service (transcription + summarization API)
│   ├── app/
│   │   ├── api/routes/jobs.py     REST + SSE endpoints
│   │   ├── services/              Whisper transcriber, Gemini summarizer
│   │   ├── models/job.py          In-memory job store
│   │   └── main.py                App factory, CORS, lifespan
│   ├── main.py                    Entry point (uvicorn)
│   └── Dockerfile
│
├── frontend/            React + Vite SPA
│   ├── src/
│   │   ├── App.jsx                Upload -> stream -> summarize -> download
│   │   └── main.jsx
│   ├── vite.config.js             Dev proxy: /api -> localhost:8000
│   ├── nginx.conf                 Prod proxy: /api -> backend container
│   └── Dockerfile
│
└── docker-compose.yml    Runs both services together
```


The frontend never talks to a hardcoded backend host. In dev, Vite proxies
`/api/*` to the FastAPI server. In prod (Docker), nginx does the same thing,
proxying to the `backend` service on the Docker network. This keeps
everything same-origin from the browser's point of view, so no CORS
configuration is needed at runtime.

**Request flow:** upload audio (`POST /api/jobs`) → live transcript over
Server-Sent Events (`GET /api/jobs/{id}/stream`) → summarize
(`POST /api/jobs/{id}/summarize`) → download transcript/summary
(`GET /api/jobs/{id}/download/txt|docx`).

## Option A: run locally (two terminals)

**Backend**
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # add your GEMINI_API_KEY
python main.py
```
Runs on `http://localhost:8000`.

**Frontend**
```bash
cd frontend
npm install
npm run dev
```
Runs on `http://localhost:5173` and proxies API calls to the backend above.

## Option B: run with Docker Compose

```bash
cp backend/.env.example backend/.env   # add your GEMINI_API_KEY
docker compose up --build
```
Frontend (served by nginx, proxying to the backend container) is available
at `http://localhost:8080`. The backend isn't exposed to the host directly;
the frontend container is the only entry point, which mirrors how this
would sit behind a single reverse proxy in production.
