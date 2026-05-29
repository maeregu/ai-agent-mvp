# Amharic-English Transcription Agent MVP

This is a market-test MVP for an Ethiopian audio/video transcription agent. It supports:

- audio/video upload
- background transcription job
- job status polling
- transcript display
- optional translation display
- short video clip generation for uploaded videos
- custom clip durations: 45 seconds, 2 minutes, 5 minutes, or 20 minutes
- multiple highlight clips per video
- progress/status percentage
- optional Celery + Redis worker mode for long jobs
- text download

The current code has clean adapters for transcription and translation. By default it uses local Whisper, which also requires FFmpeg. Set `TRANSCRIPTION_PROVIDER=demo` only when you want placeholder transcripts for product-flow testing.

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    database.py
    models.py
    schemas.py
    routes/
      uploads.py
      jobs.py
    services/
      transcription.py
      translation.py
      file_storage.py
      video_shortener.py
    workers/
      tasks.py
  uploads/
  outputs/
  jobs/
  chunks/
  requirements.txt
  .env.example

frontend/
  index.html
  styles.css
  app.js
```

## Run Locally

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open:

```text
frontend/index.html
```

The frontend expects the backend at:

```text
http://127.0.0.1:8000
```

## Connect Real Transcription

Option 1: install local Whisper:

```powershell
python -m pip install openai-whisper
```

You may also need FFmpeg installed and available on `PATH`.

Then run the backend with:

```powershell
$env:TRANSCRIPTION_PROVIDER="local_whisper"
$env:WHISPER_MODEL="tiny"
$env:WHISPER_THREADS="2"
uvicorn app.main:app --reload
```

For low-spec computers, keep `WHISPER_MODEL=tiny`. Larger models are slower and can make the computer feel stuck while processing.

Option 2: replace `backend/app/services/transcription.py` with an API provider such as OpenAI transcription, hosted Whisper, or an Ethiopian-language ASR provider.

## Connect Real Translation

The MVP now includes an OpenAI translation provider for Amharic ↔ English.

Set your API key before starting the backend:

```powershell
$env:OPENAI_API_KEY="your_api_key_here"
$env:TRANSLATION_PROVIDER="openai"
uvicorn app.main:app --reload
```

Or create `backend/.env`:

```text
OPENAI_API_KEY=your_real_api_key_here
TRANSLATION_PROVIDER=openai
OPENAI_TRANSLATION_MODEL=gpt-5-mini
```

Then restart the backend.

Current MVP behavior:

- If the target is English and the transcript already looks English, the app returns the transcript as the translation.
- Otherwise, the app sends the transcript to OpenAI and returns only the translated text.

You can later replace the provider with Google Translate, Lesan, or a custom model inside `backend/app/services/translation.py`.

## Long Video To Short Video

The MVP now creates a short downloadable video for uploaded video files.

Default behavior:

- uses FFmpeg
- uses Whisper timestamp segments
- asks OpenAI to choose the strongest highlight when API quota is available
- falls back to local highlight scoring when OpenAI is unavailable
- exports one or more `.mp4` clips
- supports 45 seconds, 2 minutes, 5 minutes, and 20 minutes
- shows clip download buttons after processing

Change duration in `backend/.env`:

```text
SHORT_CLIP_SECONDS=45
SHORT_CLIP_COUNT=3
HIGHLIGHT_PROVIDER=openai
OPENAI_HIGHLIGHT_MODEL=gpt-5-mini
```

If OpenAI quota/billing is not active, the app still creates a short clip using local scoring over the timestamped transcript.

## Long Job Worker Mode

For 2-3 hour videos, use Redis + Celery instead of FastAPI's local background task.

Install requirements:

```powershell
cd backend
python -m pip install -r requirements.txt
```

Start Redis. On Windows, the simplest path is usually Docker Desktop:

```powershell
docker run --name ai-agent-redis -p 6379:6379 redis:7
```

Set worker mode in `backend/.env`:

```text
USE_CELERY=true
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
TRANSCRIPTION_CHUNK_SECONDS=1200
```

Start the Celery worker in one terminal:

```powershell
cd backend
celery -A app.workers.celery_app.celery_app worker --pool=solo --loglevel=info
```

Start FastAPI in another terminal:

```powershell
cd backend
uvicorn app.main:app --reload
```

The app still works without Celery. If `USE_CELERY=false`, uploads run with FastAPI's local background task.

## Next Market Features

- user accounts
- ETB pricing and local payment/manual invoice flow
- Telegram bot
- subtitles `.srt`
- summaries for lectures and meetings
- speaker labels
- human review workflow for B2B customers

