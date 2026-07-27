FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /dockerapp

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG WHISPER_MODEL_SIZE=small
RUN python3 -c "\
from faster_whisper import WhisperModel; \
WhisperModel('${WHISPER_MODEL_SIZE}', device='cpu', compute_type='int8')"

COPY . .

EXPOSE 8000

CMD ["python", "-m", "main"]
