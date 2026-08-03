# Audio Meeting Summarizer — Backend

A FastAPI backend that turns an uploaded audio recording into a clean
transcript and a structured summary — delivered as a `.txt` and a `.docx`
file. The transcript streams to the client live, segment by segment, as
it's produced, instead of leaving the user staring at a loading spinner.

Transcription runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(no audio leaves your machine for that step); summarization is powered by
Google Gemini.

## Features

- Accepts audio uploads (`.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`, `.webm`,
  `.opus`, `.aac`)
- Local, offline transcription via faster-whisper
- Transcript language chosen per upload — auto-detect by default, or pick
  one explicitly (see `GET /api/languages`)
- Long files are automatically split into chunks using ffmpeg so no single
  SSE connection has to stay open for the full transcription duration
- Transcript streams to the client via Server-Sent Events (SSE) as
  faster-whisper produces each segment
- Five summary types: **Meeting**, **Lecture / Educational**,
  **User Interview / CustDev**, **Sales Call / Client Deal**, and
  **Voice Note / Stream of Consciousness** (see `GET /api/summary-types`)
- Each summary type has its own prompt and section structure, generated in
  the same language as the transcript
- Automatic retry on transient Gemini API errors
- Delivers the transcript as `.txt` and the summary as `.docx`

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) on your `PATH` (faster-whisper
  uses it to decode audio; the backend also uses it to split long files)
- A [Gemini API key](https://aistudio.google.com/apikey)

## Setup

```bash
git clone https://github.com/<your-username>/audio-meeting-summarizer.git
cd audio-meeting-summarizer/backend
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY
python main.py
```

On first run, faster-whisper downloads the transcription model (a few
hundred MB to ~1.5 GB, depending on `WHISPER_MODEL_SIZE`) — this only
happens once. Interactive API docs: `http://localhost:8000/docs`.

## API

| Method | Path                               | Description                                                                                      |
|--------|------------------------------------|--------------------------------------------------------------------------------------------------|
| GET    | `/api/languages`                   | List selectable transcript languages, plus the `"auto"` auto-detect default                      |
| GET    | `/api/summary-types`               | List selectable summary types, plus the default (`"meeting"`)                                    |
| POST   | `/api/jobs`                        | Upload an audio file; optionally pass `language` (code from `/api/languages`, default `"auto"`) and `beam_size` (1–5, default `2`). Returns `job_id`. |
| GET    | `/api/jobs/{job_id}`               | Get current job status, transcript, and summary                                                  |
| GET    | `/api/jobs/{job_id}/stream`        | SSE stream: detected/used language, then transcript segments. Accepts `?chunk=N` for multi-chunk long files. |
| POST   | `/api/jobs/{job_id}/summarize`     | Generate the summary. Optionally pass `{"summary_type": "lecture"}` in the JSON body (defaults to `"meeting"`). |
| GET    | `/api/jobs/{job_id}/download/txt`  | Download the transcript as `.txt`                                                                |
| GET    | `/api/jobs/{job_id}/download/docx` | Download the summary as `.docx`                                                                  |

### Quick example

```bash
# Upload
job_id=$(curl -s -X POST -F "file=@recording.mp3" -F "language=ru" \
  http://localhost:8000/api/jobs \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")

# Stream transcript
curl -N http://localhost:8000/api/jobs/$job_id/stream

# Summarize (choose a type)
curl -s -X POST http://localhost:8000/api/jobs/$job_id/summarize \
  -H "Content-Type: application/json" \
  -d '{"summary_type": "meeting"}'
```

## Configuration

Read from environment variables (see `.env.example`):

| Variable                     | Default                 | Description                                      |
|------------------------------|-------------------------|--------------------------------------------------|
| `GEMINI_API_KEY`             | —                       | **Required.** Gemini API key                     |
| `WHISPER_MODEL_SIZE`         | `small`                 | faster-whisper model size                        |
| `GEMINI_MODEL`               | `gemini-3.1-flash-lite` | Gemini model used for summarization              |
| `GEMINI_MAX_ATTEMPTS`        | `3`                     | Retry attempts on transient Gemini errors        |
| `GEMINI_RETRY_DELAY_SECONDS` | `5`                     | Base delay (seconds) between retries             |
| `DOWNLOADS_DIR`              | `downloads`             | Local directory where uploaded audio is saved    |

## Project layout

```
main.py                          entry point — run with `python main.py`

app/
  main.py                        FastAPI app, CORS, lifespan (builds transcriber/summarizer once)

  api/
    deps.py                      shared transcriber/summarizer access via Depends()
    routes/
      jobs.py                    upload / stream / summarize / download endpoints
      languages.py               GET /api/languages and GET /api/summary-types

  core/
    config.py                    settings, loaded from .env
    logging_config.py

  models/
    job.py                       Job dataclass, JobStatus enum, in-memory job store

  schemas/
    job.py                       Pydantic response models

  services/
    transcriber.py               Transcriber interface + WhisperTranscriber
    summarizer.py                Summarizer interface + GeminiSummarizer
    prompts.py                   SummaryType enum, all prompt templates, build_summary_prompt()
    pipeline.py                  async wrapper around summarizer.summarize()

  exporters/
    docx_export/                 Markdown → Word converter
      converter.py
      __main__.py                CLI: python -m app.exporters.docx_export input.md output.docx
    txt_export/                  transcript → .txt converter
      converter.py
      __main__.py                CLI: python -m app.exporters.txt_export input.txt output.txt

  utils/
    audio.py                     ffprobe duration probe + ffmpeg audio splitter for long files
    streaming.py                 runs a blocking generator on a background thread for SSE,
                                 emitting keepalive comments while waiting for the first chunk
    sse.py                       Server-Sent Events message formatting
```

## Architecture

### Transcription

`Transcriber` and `Summarizer` are abstract interfaces (Strategy pattern);
`WhisperTranscriber` and `GeminiSummarizer` are the current implementations.
Swapping either means adding a class in `app/services/` and updating the
lifespan in `app/main.py`, where they're built once and stashed on `app.state`.

faster-whisper's `.transcribe()` returns a lazy generator, so
`WhisperTranscriber.transcribe_stream()` yields each segment as soon as it's
ready. The `/stream` route runs that blocking generator on a background thread
(`app/utils/streaming.py`) and relays segments to the client over SSE, so the
transcript fills in live.

The transcript language is chosen per upload — not baked into the server config.
`None` means auto-detect; an explicit code (e.g. `"ru"`) pins the language and
skips detection, which is slightly faster. After the first chunk, the detected
language is locked onto the job so subsequent chunks use it directly.

### Long file handling

Files longer than 10 minutes are split into 10-minute chunks by ffmpeg at
upload time (`app/utils/audio.py`). The `/stream` endpoint processes one chunk
per SSE connection, selected by `?chunk=N`. When a chunk finishes, it emits a
`chunk_done` event with the next index; the frontend reconnects immediately.
This keeps each SSE connection short enough to survive cloud ingress timeouts
(Azure Container Apps, etc.) even for hour-long recordings.

### Summarization

`POST /api/jobs/{id}/summarize` accepts an optional `summary_type` in its JSON
body (defaults to `"meeting"`). Five types are supported, each with its own
prompt template and section structure in `app/services/prompts.py`:

| Type         | Sections                                                                 |
|--------------|--------------------------------------------------------------------------|
| `meeting`    | Overview · Key Discussion Points · Decisions Made · Action Items · Next Steps |
| `lecture`    | Core Topic & Goal · Key Concepts & Definitions · Detailed Takeaways · Review Questions |
| `custdev`    | Respondent Profile & Context · User Pain Points & Needs · Feedback on Product/Solution · Notable Quotes |
| `sales`      | Deal Overview · Client Needs & Pain Points · Objections & Concerns · Next Steps & Agreed Action Items |
| `voice_note` | Main Thought · Structured Breakdown · Extracted Tasks & Ideas            |

All summaries are generated in the same language as the transcript. A
`LANGUAGE_NAMES` dict (`prompts.py`) maps Whisper language codes to full names
so Gemini receives an unambiguous instruction (e.g. `"Russian"` rather than `"ru"`).

### Job lifecycle

```
QUEUED → TRANSCRIBING → TRANSCRIBED → SUMMARIZING → DONE
                                                   ↘ ERROR
```

Job state lives in an in-memory dict — correct for a single-replica deployment.
Swapping in Redis would only touch `app/models/job.py`.

### Exporters

`docx_export` and `txt_export` convert results into real files — proper
headings, bullets, and bold for the summary; plain UTF-8 for the transcript.
Both live under `app/exporters/` as separate subpackages (importing `txt_export`
never requires `python-docx`) and work as standalone CLI tools:

```bash
python -m app.exporters.docx_export input.md output.docx
python -m app.exporters.txt_export  input.txt output.txt
```

## License

[MIT](LICENSE)

## CI/CD

Every push and pull request against `main` runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml):
lint (`ruff`) then the test suite (`pytest`, in [`tests/`](tests/)) against a
`TestClient`, with the real Whisper/Gemini dependencies swapped for fakes via
FastAPI's `dependency_overrides` — no model download or API key needed to run CI.

**Workflow:** feature branches (`feature/xyz`) → PR into `main` → CI must pass
→ squash-merge → auto-deploy. `main` is protected: PRs required, CI must pass,
branch must be up to date before merging.

Run the same checks locally before pushing:

```bash
pip install -r requirements-dev.txt
ruff check .
pytest -v
```