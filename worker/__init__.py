"""DubWizard Worker - Video dubbing processing worker.

This package provides the background worker for processing video dubbing jobs,
including transcription, translation, speech synthesis, and video muxing.
"""

__version__ = "1.0.0"

from worker.models import (
    TranscriptionSegment,
    TranslationSegment,
    SynthesizedSegment,
    segments_to_srt_format,
)
from worker.services import AIService, AIServiceError
from worker.tasks import JobProcessor, JobProcessingError, process_job
from worker.utils import (
    FFmpegError,
    SubtitleError,
    extract_audio,
    get_video_duration,
    get_video_metadata,
    mux_audio_video,
    generate_srt,
    save_srt,
)

__all__ = [
    # Version
    "__version__",
    # Models
    "TranscriptionSegment",
    "TranslationSegment",
    "SynthesizedSegment",
    "segments_to_srt_format",
    # Services
    "AIService",
    "AIServiceError",
    # Tasks
    "JobProcessor",
    "JobProcessingError",
    "process_job",
    # Utils
    "FFmpegError",
    "SubtitleError",
    "extract_audio",
    "get_video_duration",
    "get_video_metadata",
    "mux_audio_video",
    "generate_srt",
    "save_srt",
]
