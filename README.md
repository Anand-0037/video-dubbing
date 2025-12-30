# DubWizard

AI-powered video dubbing application that converts English videos to Hindi with natural-sounding speech synthesis.

## Screenshots

| Upload | Processing | Results |
|--------|------------|---------|
| ![Upload](docs/screenshots/upload-page.png) | ![Processing](docs/screenshots/processing-page.png) | ![Results](docs/screenshots/result-page.png) |

> Screenshots will be added before submission. See `docs/screenshots/` folder.

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- FFmpeg (installed and in PATH)
- Docker & Docker Compose (optional)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd video-dubbing

# Backend setup
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Worker setup
cd ../../worker
pip install -r requirements.txt

# Frontend setup
cd ../apps/web
npm install
```

### Running Locally

```bash
# Terminal 1: Start API server
cd apps/api
uvicorn app.main:app --reload --port 8000

# Terminal 2: Start worker
cd worker
python worker.py

# Terminal 3: Start frontend
cd apps/web
npm run dev
```

Open http://localhost:3000 in your browser.

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for Whisper transcription | Yes |
| `ELEVENLABS_API_KEY` | ElevenLabs API key for TTS | Yes |
| `AWS_ACCESS_KEY_ID` | AWS credentials for S3 | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS credentials for S3 | Yes |
| `AWS_REGION` | AWS region (e.g., us-east-1) | Yes |
| `S3_BUCKET_NAME` | S3 bucket for video storage | Yes |
| `DATABASE_URL` | SQLite database path | No (default: ./dubwizard.db) |

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   FastAPI   │────▶│   Worker    │
│   (React)   │     │   Backend   │     │  (Python)   │
└─────────────┘     └─────────────┘     └─────────────┘
                           │                   │
                           ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐
                    │   SQLite    │     │  S3 Bucket  │
                    │  (Jobs DB)  │     │  (Videos)   │
                    └─────────────┘     └─────────────┘
                                               │
                           ┌───────────────────┼───────────────────┐
                           ▼                   ▼                   ▼
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │   Whisper   │     │   GPT-4     │     │ ElevenLabs  │
                    │ (Transcribe)│     │ (Translate) │     │   (TTS)     │
                    └─────────────┘     └─────────────┘     └─────────────┘
```

### Components

- **Frontend (React)**: Upload UI, progress tracking, download results
- **Backend (FastAPI)**: REST API, job management, presigned URLs
- **Worker**: Video processing pipeline (FFmpeg + AI services)
- **S3**: Video and subtitle file storage
- **SQLite**: Job state persistence

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/jobs` | Create job and get presigned upload URL |
| GET | `/api/v1/jobs/{job_id}` | Get job status and progress |
| POST | `/api/v1/jobs/{job_id}/enqueue` | Start job processing |
| GET | `/api/v1/jobs/{job_id}/download` | Get presigned download URLs |
| DELETE | `/api/v1/jobs/{job_id}` | Delete a job |
| GET | `/api/v1/health` | Health check |

## Demo Steps

1. **Upload Video** (5 seconds)
   - Select an MP4 video (max 60 seconds, max 100MB)
   - Choose voice style (Adam or Bella)
   - Click "Start Dubbing"

2. **Processing** (2-5 minutes depending on video length)
   - Watch progress through stages:
     - Transcribing (Whisper)
     - Translating (GPT-4)
     - Synthesizing (ElevenLabs)
     - Processing Video (FFmpeg)

3. **Download Results**
   - Dubbed video (MP4 with Hindi audio)
   - English subtitles (SRT)
   - Hindi subtitles (SRT)

### Sample Video Requirements

- Format: MP4
- Duration: 30-60 seconds recommended
- Audio: Clear English speech
- Size: Under 100MB

## Example Requests

```bash
# Create a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "demo.mp4",
    "file_size": 5000000,
    "content_type": "video/mp4",
    "target_language": "hindi",
    "voice_id": "pNInz6obpgDQGcFmaJgB"
  }'

# Get job status
curl http://localhost:8000/api/v1/jobs/job_abc123

# Enqueue job after upload
curl -X POST http://localhost:8000/api/v1/jobs/job_abc123/enqueue

# Get download URLs
curl http://localhost:8000/api/v1/jobs/job_abc123/download
```

## Known Limitations

- **Video Duration**: Maximum 60 seconds (hackathon MVP constraint)
- **Input Language**: English only
- **Output Language**: Hindi only
- **File Format**: MP4 only
- **File Size**: Maximum 100MB
- **Concurrent Jobs**: Single worker processes one job at a time

### Future Improvements

- Support for longer videos (chunked processing)
- Additional languages (Spanish, French, German, etc.)
- Multiple voice options per language
- Real-time progress via WebSocket
- Batch processing support

## Project Structure

```
video-dubbing/
├── apps/
│   ├── api/                 # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/      # API routes
│   │   │   ├── core/        # Config, logging
│   │   │   ├── db/          # Database setup
│   │   │   ├── models/      # SQLAlchemy models
│   │   │   ├── schemas/     # Pydantic schemas
│   │   │   └── services/    # Business logic
│   │   └── tests/
│   └── web/                 # React frontend
│       └── src/
│           ├── components/  # UI components
│           ├── hooks/       # Custom hooks
│           ├── services/    # API client
│           ├── store/       # Zustand state
│           └── types/       # TypeScript types
├── worker/                  # Background worker
│   ├── services/            # AI integrations
│   ├── tasks/               # Job processing
│   └── utils/               # FFmpeg, subtitles
├── infra/                   # Docker configs
└── .kiro/
    ├── hooks/               # Kiro automation hooks
    ├── specs/               # Feature specifications
    └── steering/            # Project guidelines
```

## License

MIT

---

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and start all services
cd infra
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

Services will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Development with Docker

```bash
cd infra
docker-compose -f docker-compose.dev.yml up --build
```

This enables hot reload for faster development.

### Manual Run (Without Docker)

If you prefer not to use Docker:

```bash
# Terminal 1: Backend
cd apps/api
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Worker
cd worker
source ../apps/api/venv/bin/activate  # or create separate venv
python worker.py

# Terminal 3: Frontend
cd apps/web
npm run dev
```

## Troubleshooting

### Common Issues

**FFmpeg not found**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

**S3 Access Denied**
- Check AWS credentials in `.env`
- Verify bucket name and region
- Ensure bucket CORS is configured (see `docs/S3_SETUP.md`)

**API Key Errors**
- Verify OpenAI API key has Whisper access
- Verify ElevenLabs API key is valid
- Check API usage limits

**Video Processing Fails**
- Ensure video is MP4 format
- Check video duration is under 60 seconds
- Verify audio track exists in video

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `make test`
5. Submit a pull request

## License

MIT
