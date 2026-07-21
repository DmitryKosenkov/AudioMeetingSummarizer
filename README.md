# Audio Meeting Summarizer

A FastAPI backend that turns an uploaded meeting recording into a clean
transcript and a structured summary — delivered as a `.txt` and a `.docx`
file. The transcript streams to the client live, segment by segment, as
it's produced, instead of leaving the user staring at a loading spinner.

Transcription runs locally via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
(no audio leaves your machine for that step); summarization is powered by
Google Gemini.

## Features

- Accepts audio uploads (`.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`, `.webm`,
  `.opus`, `.aac`)
- Local, offline transcription
- Transcript streams to the client via Server-Sent Events (SSE) as
  faster-whisper produces each segment
- Structured meeting summary (Overview, Key Discussion Points, Decisions
  Made, Action Items, Next Steps), generated in the same language as the
  transcript
- Automatic retry on transient Gemini API errors
- Delivers the transcript as `.txt` and the summary as `.docx`

## Requirements

- Python 3.10+
- [ffmpeg](https://ffmpeg.org/download.html) on your `PATH` (faster-whisper
  uses it to decode audio)
- A [Gemini API key](https://aistudio.google.com/apikey)

## Setup

```bash
git clone https://github.com/<your-username>/audio-meeting-summarizer.git
cd audio-meeting-summarizer
pip install -r requirements.txt
cp .env.example .env   # fill in GEMINI_API_KEY
python main.py
```

On first run, faster-whisper downloads the transcription model (a few
hundred MB to ~1.5 GB, depending on `WHISPER_MODEL_SIZE`) — this only
happens once. Interactive API docs: `http://localhost:8000/docs`.

## API

| Method | Path                                | Description                                       |
|--------|--------------------------------------|------------------------------------------------------|
| POST   | `/api/jobs`                         | Upload an audio file, returns a `job_id`               |
| GET    | `/api/jobs/{job_id}`                | Get current job status/transcript/summary              |
| GET    | `/api/jobs/{job_id}/stream`         | SSE stream of transcript segments                       |
| POST   | `/api/jobs/{job_id}/summarize`      | Generate the summary from the finished transcript        |
| GET    | `/api/jobs/{job_id}/download/txt`   | Download the transcript                                  |
| GET    | `/api/jobs/{job_id}/download/docx`  | Download the summary                                     |

```bash
job_id=$(curl -s -X POST -F "file=@some_audio.mp3" http://localhost:8000/api/jobs | python3 -c "import sys,json; print(json.load(sys.stdin)['job_id'])")
curl -N http://localhost:8000/api/jobs/$job_id/stream
curl -X POST http://localhost:8000/api/jobs/$job_id/summarize
```

## Configuration

Read from environment variables (see `.env.example`):

| Variable                    | Default                 | Description                             |
|------------------------------|--------------------------|-------------------------------------------|
| `GEMINI_API_KEY`            | -                        | Gemini API key                            |
| `WHISPER_MODEL_SIZE`        | `large-v3-turbo`         | faster-whisper model size                 |
| `WHISPER_LANGUAGE`          | `ru`                     | Language for transcription and summary    |
| `GEMINI_MODEL`              | `gemini-3.1-flash-lite`  | Gemini model used for summarization       |
| `GEMINI_MAX_ATTEMPTS`       | `3`                      | Retry attempts on transient errors        |
| `GEMINI_RETRY_DELAY_SECONDS`| `5`                      | Base delay between retries                |
| `DOWNLOADS_DIR`             | `downloads`              | Local directory for uploaded audio        |

## Project layout

```
main.py                        entry point - run with `python main.py`

app/
  main.py                     FastAPI app, CORS, lifespan (builds transcriber/summarizer once)

  api/
    deps.py                    shared transcriber/summarizer access via Depends()
    routes/
      jobs.py                    upload / stream / summarize / download endpoints

  core/
    config.py                  settings, loaded from .env
    logging_config.py

  models/
    job.py                      Job record, JobStatus enum, in-memory job store

  schemas/
    job.py                      Pydantic response models

  services/
    transcriber.py              Transcriber interface + WhisperTranscriber
    summarizer.py                Summarizer interface + GeminiSummarizer
    prompts.py                    Gemini prompt template
    pipeline.py                  async wrapper around summarizer.summarize()

  exporters/
    docx_export/                 Markdown -> Word converter
      converter.py
      __main__.py                   CLI: python -m app.exporters.docx_export input.md output.docx
    txt_export/                   transcript -> .txt converter
      converter.py
      __main__.py                   CLI: python -m app.exporters.txt_export input.txt output.txt

  utils/
    streaming.py                 runs a blocking generator on a background thread for SSE
    sse.py                       Server-Sent Events message formatting
```

## Architecture

`Transcriber` and `Summarizer` are abstract interfaces (Strategy pattern);
`WhisperTranscriber` and `GeminiSummarizer` are the current implementations.
Swapping either means adding a class in `app/services/` and updating
`app/main.py`'s lifespan, where they're built once and stashed on
`app.state`.

`faster-whisper`'s `.transcribe()` decodes audio incrementally and returns a
generator, so `WhisperTranscriber.transcribe_stream()` yields each segment
as soon as it's ready. The `/stream` route runs that blocking generator on
a background thread (`app/utils/streaming.py`) and relays segments to the
client over SSE, so the transcript fills in live instead of a spinner.

Job state (`JobStatus` in `app/models/job.py`: `QUEUED` → `TRANSCRIBING` →
`TRANSCRIBED` → `SUMMARIZING` → `DONE`/`ERROR`) lives in an in-memory
store — fine for a single-process deployment; swapping in Redis later
wouldn't require touching the routes.

The Gemini prompt (`app/services/prompts.py`) asks for a structured
Markdown summary — Overview, Key Discussion Points, Decisions Made, Action
Items, Next Steps — generated in whatever language `WHISPER_LANGUAGE` is
set to, via a code-to-name lookup so Gemini gets an unambiguous
instruction like "Russian" rather than the raw code `ru`.

`docx_export` and `txt_export` convert those results into real files: real
headings/bullets/bold for the summary, plain UTF-8 for the transcript.
Both live under `app/exporters/`, kept as separate subpackages so
importing `txt_export` never requires `python-docx`. Neither imports from
`app.api`, so both work as standalone tools:

```bash
python -m app.exporters.docx_export input.md output.docx
python -m app.exporters.txt_export input.txt output.txt
```

```python
from app.exporters.docx_export import render_markdown_summary_to_docx
from app.exporters.txt_export import render_transcript_to_txt
```

## License

[MIT](LICENSE)
