"""Tests for app/api/routes/jobs.py - the upload -> stream -> summarize ->
download pipeline.
"""
import json


def parse_sse(body: str) -> list[tuple[str, object]]:
    """Turn raw `event: X\\ndata: Y\\n\\n` text into [(event, decoded_data), ...]."""
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.splitlines()
        event = next(line.removeprefix("event: ") for line in lines if line.startswith("event: "))
        data_line = next(line.removeprefix("data: ") for line in lines if line.startswith("data: "))
        events.append((event, json.loads(data_line)))
    return events


# --- upload --------------------------------------------------------------


def test_upload_rejects_unsupported_extension(client):
    response = client.post(
        "/api/jobs", files={"file": ("virus.exe", b"not audio", "application/octet-stream")}
    )
    assert response.status_code == 400


def test_upload_creates_queued_job(client):
    response = client.post(
        "/api/jobs", files={"file": ("meeting.mp3", b"fake audio bytes", "audio/mpeg")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["job_id"]


# --- stream ----------------------------------------------------------------


def test_stream_emits_language_then_segments_then_done(client, uploaded_job_id):
    response = client.get(f"/api/jobs/{uploaded_job_id}/stream")
    assert response.status_code == 200

    events = parse_sse(response.text)
    kinds = [kind for kind, _ in events]

    assert kinds[0] == "language"
    assert kinds[-1] == "done"
    assert kinds.count("segment") == 2  # FakeTranscriber's default 2 segments

    language_event = events[0]
    assert language_event[1] == "en"

    done_event = events[-1]
    assert done_event[1] == "Hello. This is a test."


def test_stream_stores_transcript_and_language_on_job(client, uploaded_job_id):
    client.get(f"/api/jobs/{uploaded_job_id}/stream")

    status = client.get(f"/api/jobs/{uploaded_job_id}").json()
    assert status["status"] == "transcribed"
    assert status["transcript"] == "Hello. This is a test."
    assert status["detected_language"] == "en"


def test_stream_rejects_a_job_that_is_already_streaming_or_done(client, uploaded_job_id):
    client.get(f"/api/jobs/{uploaded_job_id}/stream")  # completes, job -> transcribed

    second_attempt = client.get(f"/api/jobs/{uploaded_job_id}/stream")
    assert second_attempt.status_code == 409


def test_stream_reports_transcriber_failure(client, fake_transcriber, uploaded_job_id):
    fake_transcriber.raise_error = True

    response = client.get(f"/api/jobs/{uploaded_job_id}/stream")
    events = parse_sse(response.text)

    assert events[-1][0] == "error"

    status = client.get(f"/api/jobs/{uploaded_job_id}").json()
    assert status["status"] == "error"
    assert status["error"]


def test_stream_reports_no_speech_as_an_error(client, fake_transcriber, uploaded_job_id):
    fake_transcriber.segments = []  # no speech recognized

    response = client.get(f"/api/jobs/{uploaded_job_id}/stream")
    events = parse_sse(response.text)

    assert events[-1][0] == "error"
    assert "No speech" in events[-1][1]


def test_stream_404s_for_unknown_job(client):
    response = client.get("/api/jobs/does-not-exist/stream")
    assert response.status_code == 404


# --- summarize ---------------------------------------------------------------


def test_summarize_requires_a_finished_transcript(client, uploaded_job_id):
    response = client.post(f"/api/jobs/{uploaded_job_id}/summarize")
    assert response.status_code == 409


def test_summarize_uses_the_detected_language(client, fake_summarizer, uploaded_job_id):
    client.get(f"/api/jobs/{uploaded_job_id}/stream")  # -> transcribed, language "en"

    response = client.post(f"/api/jobs/{uploaded_job_id}/summarize")
    assert response.status_code == 200
    assert response.json()["summary"] == fake_summarizer.summary_text

    text, language = fake_summarizer.last_call
    assert text == "Hello. This is a test."
    assert language == "en"


def test_summarize_uses_whatever_language_was_detected(client, fake_transcriber, fake_summarizer, uploaded_job_id):
    fake_transcriber.language = "ru"

    client.get(f"/api/jobs/{uploaded_job_id}/stream")
    client.post(f"/api/jobs/{uploaded_job_id}/summarize")

    _, language = fake_summarizer.last_call
    assert language == "ru"


# --- downloads -----------------------------------------------------------------


def test_download_txt_before_transcript_ready(client, uploaded_job_id):
    response = client.get(f"/api/jobs/{uploaded_job_id}/download/txt")
    assert response.status_code == 409


def test_download_docx_before_summary_ready(client, uploaded_job_id):
    response = client.get(f"/api/jobs/{uploaded_job_id}/download/docx")
    assert response.status_code == 409


def test_full_pipeline_downloads_succeed(client, uploaded_job_id):
    client.get(f"/api/jobs/{uploaded_job_id}/stream")
    client.post(f"/api/jobs/{uploaded_job_id}/summarize")

    txt_response = client.get(f"/api/jobs/{uploaded_job_id}/download/txt")
    assert txt_response.status_code == 200
    assert txt_response.content == b"Hello. This is a test."

    docx_response = client.get(f"/api/jobs/{uploaded_job_id}/download/docx")
    assert docx_response.status_code == 200
    assert docx_response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument"
    )
