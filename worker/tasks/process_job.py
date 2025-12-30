"""Job processing pipeline for video dubbing."""

import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Optional, Callable, List

from dubwizard_shared import JobStatus, TranscriptionSegment, TranslationSegment, SynthesizedSegment, JobService, S3Service, shared_settings as settings
from worker.services.ai_service import AIService, AIServiceError
from worker.utils.ffmpeg_helpers import (
    extract_audio,
    get_video_duration,
    get_audio_duration,
    mux_audio_video,
    concatenate_audio_files,
    convert_audio_format,
    FFmpegError,
)
from worker.utils.subtitle_generator import save_srt, SubtitleError

logger = logging.getLogger(__name__)


class JobProcessingError(Exception):
    """Exception raised when job processing fails."""
    pass


class JobProcessor:
    """Processor for video dubbing jobs."""

    # Maximum video duration in seconds
    MAX_VIDEO_DURATION = settings.MAX_VIDEO_DURATION_SECONDS

    def __init__(
        self,
        s3_service,
        job_service,
        ai_service: Optional[AIService] = None,
    ):
        """
        Initialize job processor.

        Args:
            s3_service: S3 service for file operations
            job_service: Job service for database operations
            ai_service: AI service for transcription/translation/TTS (optional, created if not provided)
        """
        self.s3_service = s3_service
        self.job_service = job_service
        self.ai_service = ai_service or AIService()

    def process_job(
        self,
        job_id: str,
        progress_callback: Optional[Callable[[JobStatus, int], None]] = None,
    ) -> bool:
        """
        Process a dubbing job through the complete pipeline.

        Pipeline steps:
        1. Download video from S3
        2. Validate video duration (<= 60s)
        3. Extract audio to WAV using FFmpeg
        4. Transcribe audio with Whisper (with timestamps)
        5. Translate transcript to target language
        6. Generate TTS audio via ElevenLabs
        7. Create timing-adjusted dubbed audio
        8. Mux dubbed audio into video using FFmpeg
        9. Generate SRT subtitle files
        10. Upload outputs to S3
        11. Mark job as completed

        Args:
            job_id: Job ID to process
            progress_callback: Optional callback for progress updates (status, progress)

        Returns:
            True if successful, False otherwise

        Raises:
            JobProcessingError: If processing fails
        """
        start_time = time.time()
        logger.info(f"[{job_id}] Starting job processing")

        # Get job from database
        job = self.job_service.get_job(job_id)
        if not job:
            raise JobProcessingError(f"Job not found: {job_id}")

        logger.info(f"[{job_id}] Job config: source={job.source_language}, target={job.target_language}, voice={job.voice_id}")

        # Create temporary directory for processing
        temp_dir = tempfile.mkdtemp(prefix=f"dubwizard_{job_id}_")
        logger.info(f"[{job_id}] Created temp directory: {temp_dir}")

        try:
            # Update progress helper
            def update_progress(status: JobStatus, progress: int):
                self.job_service.update_job_status(job_id, status, progress)
                if progress_callback:
                    progress_callback(status, progress)
                elapsed = time.time() - start_time
                logger.info(f"[{job_id}] {status} ({progress}%) - elapsed: {elapsed:.1f}s")

            # Step 1: Download video from S3
            update_progress(JobStatus.PROCESSING, 0)
            video_path = self._download_video(job_id, job.input_s3_key, temp_dir)

            # Step 2: Validate video duration
            duration = get_video_duration(video_path)
            logger.info(f"[{job_id}] Video duration: {duration:.2f}s")

            if duration > self.MAX_VIDEO_DURATION:
                raise JobProcessingError(
                    f"Video too long: {duration:.1f}s exceeds maximum of {self.MAX_VIDEO_DURATION}s. "
                    f"Please upload a video that is {self.MAX_VIDEO_DURATION} seconds or shorter."
                )

            # Update video duration in database
            self.job_service.update_video_duration(job_id, duration)
            update_progress(JobStatus.TRANSCRIBING, 5)

            # Step 3: Extract audio to WAV (16kHz mono for Whisper)
            audio_path = Path(temp_dir) / "audio.wav"
            logger.info(f"[{job_id}] Extracting audio...")
            extract_audio(video_path, str(audio_path), sample_rate=16000, channels=1)
            update_progress(JobStatus.TRANSCRIBING, 10)

            # Step 4: Transcribe audio with Whisper
            logger.info(f"[{job_id}] Transcribing audio with Whisper...")
            transcription_segments = self.ai_service.transcribe_audio(
                str(audio_path),
                language="en",
            )

            if not transcription_segments:
                raise JobProcessingError(
                    "No speech detected in video. Please ensure the video contains audible speech."
                )

            logger.info(f"[{job_id}] Transcribed {len(transcription_segments)} segments")
            update_progress(JobStatus.TRANSLATING, 25)

            # Step 5: Translate segments
            logger.info(f"[{job_id}] Translating to {job.target_language}...")
            translation_segments = self.ai_service.translate_segments(
                transcription_segments,
                source_language=job.source_language,
                target_language=job.target_language,
            )
            logger.info(f"[{job_id}] Translated {len(translation_segments)} segments")
            update_progress(JobStatus.SYNTHESIZING, 50)

            # Step 6: Synthesize speech with ElevenLabs
            synth_dir = Path(temp_dir) / "synth"
            logger.info(f"[{job_id}] Synthesizing speech with voice {job.voice_id}...")
            synthesized_segments = self.ai_service.synthesize_segments(
                translation_segments,
                voice_id=job.voice_id,
                output_dir=str(synth_dir),
            )
            logger.info(f"[{job_id}] Synthesized {len(synthesized_segments)} audio segments")
            update_progress(JobStatus.PROCESSING_VIDEO, 70)

            # Step 7: Create timing-adjusted dubbed audio
            logger.info(f"[{job_id}] Creating dubbed audio track...")
            dubbed_audio_path = self._create_dubbed_audio(
                job_id, synthesized_segments, duration, temp_dir
            )
            update_progress(JobStatus.PROCESSING_VIDEO, 80)

            # Step 8: Generate subtitle files
            logger.info(f"[{job_id}] Generating subtitle files...")
            source_srt_path = Path(temp_dir) / "source.srt"
            target_srt_path = Path(temp_dir) / "target.srt"

            save_srt(translation_segments, str(source_srt_path), use_translated=False)
            save_srt(translation_segments, str(target_srt_path), use_translated=True)
            update_progress(JobStatus.PROCESSING_VIDEO, 85)

            # Step 9: Mux audio into video
            logger.info(f"[{job_id}] Muxing dubbed audio into video...")
            output_video_path = Path(temp_dir) / "dubbed_video.mp4"
            mux_audio_video(
                video_path,
                str(dubbed_audio_path),
                str(output_video_path),
            )
            update_progress(JobStatus.PROCESSING_VIDEO, 90)

            # Step 10: Upload outputs to S3
            logger.info(f"[{job_id}] Uploading outputs to S3...")
            output_video_key = f"outputs/{job_id}_dubbed.mp4"
            source_subtitle_key = f"subtitles/{job_id}_source.srt"
            target_subtitle_key = f"subtitles/{job_id}_target.srt"

            self.s3_service.upload_file_with_retry(str(output_video_path), output_video_key)
            self.s3_service.upload_file_with_retry(str(source_srt_path), source_subtitle_key)
            self.s3_service.upload_file_with_retry(str(target_srt_path), target_subtitle_key)
            update_progress(JobStatus.PROCESSING_VIDEO, 95)

            # Step 11: Mark job as completed
            self.job_service.complete_job(
                job_id,
                output_video_key=output_video_key,
                source_subtitle_key=source_subtitle_key,
                target_subtitle_key=target_subtitle_key,
            )
            update_progress(JobStatus.DONE, 100)

            total_time = time.time() - start_time
            logger.info(f"[{job_id}] Job completed successfully in {total_time:.1f}s")
            return True

        except FFmpegError as e:
            error_msg = f"Video processing error: {str(e)}"
            logger.error(f"[{job_id}] {error_msg}")
            self.job_service.fail_job(job_id, error_msg)
            raise JobProcessingError(error_msg) from e

        except AIServiceError as e:
            error_msg = f"AI service error: {str(e)}"
            logger.error(f"[{job_id}] {error_msg}")
            self.job_service.fail_job(job_id, error_msg)
            raise JobProcessingError(error_msg) from e

        except SubtitleError as e:
            error_msg = f"Subtitle generation error: {str(e)}"
            logger.error(f"[{job_id}] {error_msg}")
            self.job_service.fail_job(job_id, error_msg)
            raise JobProcessingError(error_msg) from e

        except JobProcessingError:
            # Re-raise without wrapping
            raise

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"[{job_id}] {error_msg}", exc_info=True)
            self.job_service.fail_job(job_id, error_msg)
            raise JobProcessingError(error_msg) from e

        finally:
            # Clean up temporary directory
            self._cleanup_temp_dir(job_id, temp_dir)

    def _download_video(self, job_id: str, s3_key: str, temp_dir: str) -> str:
        """
        Download video from S3 to temporary directory.

        Args:
            job_id: Job ID for logging
            s3_key: S3 key of the video
            temp_dir: Temporary directory path

        Returns:
            Path to downloaded video file

        Raises:
            JobProcessingError: If download fails
        """
        video_path = Path(temp_dir) / "input.mp4"

        logger.info(f"[{job_id}] Downloading video from S3: {s3_key}")

        try:
            self.s3_service.download_file_with_retry(s3_key, str(video_path))
        except Exception as e:
            raise JobProcessingError(
                f"Failed to download video from S3: {str(e)}. "
                "Please ensure the video was uploaded successfully."
            ) from e

        if not video_path.exists():
            raise JobProcessingError(
                f"Video file not found after download. "
                "Please try uploading the video again."
            )

        file_size = video_path.stat().st_size / (1024 * 1024)  # MB
        logger.info(f"[{job_id}] Video downloaded: {file_size:.2f} MB")
        return str(video_path)

    def _create_dubbed_audio(
        self,
        job_id: str,
        synthesized_segments: List[SynthesizedSegment],
        video_duration: float,
        temp_dir: str,
    ) -> str:
        """
        Create a single dubbed audio track from synthesized segments.

        This method concatenates all synthesized audio segments into a single
        audio file that matches the video duration.

        Args:
            job_id: Job ID for logging
            synthesized_segments: List of synthesized audio segments
            video_duration: Original video duration in seconds
            temp_dir: Temporary directory path

        Returns:
            Path to the dubbed audio file
        """
        if not synthesized_segments:
            raise JobProcessingError("No audio segments to concatenate")

        # Get all audio file paths
        audio_files = [seg.audio_path for seg in synthesized_segments]

        # Log segment info
        total_synth_duration = sum(seg.actual_duration for seg in synthesized_segments)
        logger.info(
            f"[{job_id}] Concatenating {len(audio_files)} segments "
            f"(total synth duration: {total_synth_duration:.2f}s, video duration: {video_duration:.2f}s)"
        )

        # Concatenate all audio segments
        dubbed_audio_path = Path(temp_dir) / "dubbed_audio.mp3"
        concatenate_audio_files(audio_files, str(dubbed_audio_path))

        # Verify the output
        actual_duration = get_audio_duration(str(dubbed_audio_path))
        logger.info(f"[{job_id}] Dubbed audio created: {actual_duration:.2f}s")

        return str(dubbed_audio_path)

    def _cleanup_temp_dir(self, job_id: str, temp_dir: str):
        """
        Clean up temporary directory.

        Args:
            job_id: Job ID for logging
            temp_dir: Path to temporary directory
        """
        try:
            if os.path.exists(temp_dir):
                # Count files before cleanup
                file_count = sum(1 for _ in Path(temp_dir).rglob("*") if _.is_file())

                shutil.rmtree(temp_dir)
                logger.info(f"[{job_id}] Cleaned up temp directory ({file_count} files)")
        except Exception as e:
            logger.warning(f"[{job_id}] Failed to clean up temp directory: {e}")


def process_job(
    job_id: str,
    s3_service,
    job_service,
    ai_service: Optional[AIService] = None,
    progress_callback: Optional[Callable[[JobStatus, int], None]] = None,
) -> bool:
    """
    Convenience function to process a job.

    Args:
        job_id: Job ID to process
        s3_service: S3 service instance
        job_service: Job service instance
        ai_service: Optional AI service instance
        progress_callback: Optional progress callback

    Returns:
        True if successful
    """
    processor = JobProcessor(
        s3_service=s3_service,
        job_service=job_service,
        ai_service=ai_service,
    )
    return processor.process_job(job_id, progress_callback)
