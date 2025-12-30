"""FFmpeg helper functions for video/audio processing."""

import logging
import subprocess
import json
from pathlib import Path
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class FFmpegError(Exception):
    """Exception raised when FFmpeg operations fail."""
    pass


def _run_ffmpeg(args: list, description: str) -> subprocess.CompletedProcess:
    """
    Run FFmpeg command with error handling.

    Args:
        args: FFmpeg command arguments
        description: Description of the operation for logging

    Returns:
        CompletedProcess result

    Raises:
        FFmpegError: If FFmpeg command fails
    """
    try:
        logger.info(f"Running FFmpeg: {description}")
        logger.debug(f"FFmpeg command: {' '.join(args)}")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"FFmpeg error: {result.stderr}")
            raise FFmpegError(f"FFmpeg failed: {result.stderr}")

        return result

    except subprocess.TimeoutExpired:
        logger.error(f"FFmpeg timeout: {description}")
        raise FFmpegError(f"FFmpeg operation timed out: {description}")
    except FileNotFoundError:
        logger.error("FFmpeg not found in PATH")
        raise FFmpegError("FFmpeg is not installed or not in PATH")


def _run_ffprobe(args: list, description: str) -> str:
    """
    Run FFprobe command with error handling.

    Args:
        args: FFprobe command arguments
        description: Description of the operation for logging

    Returns:
        stdout output from FFprobe

    Raises:
        FFmpegError: If FFprobe command fails
    """
    try:
        logger.info(f"Running FFprobe: {description}")
        logger.debug(f"FFprobe command: {' '.join(args)}")

        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=60  # 1 minute timeout
        )

        if result.returncode != 0:
            logger.error(f"FFprobe error: {result.stderr}")
            raise FFmpegError(f"FFprobe failed: {result.stderr}")

        return result.stdout

    except subprocess.TimeoutExpired:
        logger.error(f"FFprobe timeout: {description}")
        raise FFmpegError(f"FFprobe operation timed out: {description}")
    except FileNotFoundError:
        logger.error("FFprobe not found in PATH")
        raise FFmpegError("FFprobe is not installed or not in PATH")


def extract_audio(
    video_path: str,
    output_path: str,
    sample_rate: int = 16000,
    channels: int = 1
) -> str:
    """
    Extract audio from video file as WAV.

    Args:
        video_path: Path to input video file
        output_path: Path for output WAV file
        sample_rate: Audio sample rate (default 16000 for Whisper)
        channels: Number of audio channels (default 1 for mono)

    Returns:
        Path to extracted audio file

    Raises:
        FFmpegError: If extraction fails
        FileNotFoundError: If input video doesn't exist
    """
    video_path = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = [
        "ffmpeg",
        "-i", str(video_path),
        "-vn",  # No video
        "-acodec", "pcm_s16le",  # PCM 16-bit little-endian
        "-ar", str(sample_rate),  # Sample rate
        "-ac", str(channels),  # Channels
        "-y",  # Overwrite output
        str(output_path)
    ]

    _run_ffmpeg(args, f"Extract audio from {video_path.name}")

    if not output_path.exists():
        raise FFmpegError(f"Audio extraction failed: output file not created")

    logger.info(f"Audio extracted to {output_path}")
    return str(output_path)


def get_video_duration(video_path: str) -> float:
    """
    Get video duration in seconds.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds

    Raises:
        FFmpegError: If duration cannot be determined
        FileNotFoundError: If video doesn't exist
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    args = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]

    output = _run_ffprobe(args, f"Get duration of {video_path.name}")

    try:
        data = json.loads(output)
        duration = float(data["format"]["duration"])
        logger.info(f"Video duration: {duration:.2f} seconds")
        return duration
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise FFmpegError(f"Failed to parse video duration: {e}")


def get_video_metadata(video_path: str) -> Dict:
    """
    Get video metadata including resolution, fps, and codec.

    Args:
        video_path: Path to video file

    Returns:
        Dictionary with video metadata:
        - width: Video width in pixels
        - height: Video height in pixels
        - fps: Frames per second
        - duration: Duration in seconds
        - video_codec: Video codec name
        - audio_codec: Audio codec name (if present)

    Raises:
        FFmpegError: If metadata cannot be determined
        FileNotFoundError: If video doesn't exist
    """
    video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    args = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,codec_name",
        "-show_entries", "format=duration",
        "-of", "json",
        str(video_path)
    ]

    output = _run_ffprobe(args, f"Get metadata of {video_path.name}")

    try:
        data = json.loads(output)

        metadata = {
            "duration": float(data.get("format", {}).get("duration", 0)),
        }

        if data.get("streams"):
            stream = data["streams"][0]
            metadata["width"] = stream.get("width")
            metadata["height"] = stream.get("height")
            metadata["video_codec"] = stream.get("codec_name")

            # Parse frame rate (e.g., "30/1" or "30000/1001")
            fps_str = stream.get("r_frame_rate", "0/1")
            if "/" in fps_str:
                num, den = fps_str.split("/")
                metadata["fps"] = float(num) / float(den) if float(den) != 0 else 0
            else:
                metadata["fps"] = float(fps_str)

        # Get audio codec
        audio_args = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "json",
            str(video_path)
        ]

        audio_output = _run_ffprobe(audio_args, f"Get audio codec of {video_path.name}")
        audio_data = json.loads(audio_output)

        if audio_data.get("streams"):
            metadata["audio_codec"] = audio_data["streams"][0].get("codec_name")

        logger.info(f"Video metadata: {metadata}")
        return metadata

    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise FFmpegError(f"Failed to parse video metadata: {e}")


def mux_audio_video(
    video_path: str,
    audio_path: str,
    output_path: str,
    keep_original_audio: bool = False
) -> str:
    """
    Replace or add audio track to video.

    Args:
        video_path: Path to input video file
        audio_path: Path to new audio file
        output_path: Path for output video file
        keep_original_audio: If True, mix with original audio; if False, replace

    Returns:
        Path to output video file

    Raises:
        FFmpegError: If muxing fails
        FileNotFoundError: If input files don't exist
    """
    video_path = Path(video_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if keep_original_audio:
        # Mix original and new audio
        args = [
            "ffmpeg",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-y",
            str(output_path)
        ]
    else:
        # Replace audio completely
        args = [
            "ffmpeg",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v",  # Video from first input
            "-map", "1:a",  # Audio from second input
            "-c:v", "copy",  # Copy video codec
            "-c:a", "aac",  # Encode audio as AAC
            "-shortest",  # Match shortest stream duration
            "-y",
            str(output_path)
        ]

    _run_ffmpeg(args, f"Mux audio into {video_path.name}")

    if not output_path.exists():
        raise FFmpegError(f"Audio muxing failed: output file not created")

    logger.info(f"Video with new audio saved to {output_path}")
    return str(output_path)


def concatenate_audio_files(
    audio_files: list,
    output_path: str,
    format: str = "mp3"
) -> str:
    """
    Concatenate multiple audio files into one.

    Args:
        audio_files: List of paths to audio files
        output_path: Path for output audio file
        format: Output format (mp3, wav, etc.)

    Returns:
        Path to concatenated audio file

    Raises:
        FFmpegError: If concatenation fails
        ValueError: If audio_files is empty
    """
    if not audio_files:
        raise ValueError("No audio files provided for concatenation")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Verify all input files exist
    for audio_file in audio_files:
        if not Path(audio_file).exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file}")

    # Create concat file list
    concat_file = output_path.parent / "concat_list.txt"
    with open(concat_file, "w") as f:
        for audio_file in audio_files:
            # Escape single quotes in file paths
            escaped_path = str(Path(audio_file).absolute()).replace("'", "'\\''")
            f.write(f"file '{escaped_path}'\n")

    try:
        args = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:a", "libmp3lame" if format == "mp3" else "pcm_s16le",
            "-y",
            str(output_path)
        ]

        _run_ffmpeg(args, f"Concatenate {len(audio_files)} audio files")

        if not output_path.exists():
            raise FFmpegError(f"Audio concatenation failed: output file not created")

        logger.info(f"Concatenated audio saved to {output_path}")
        return str(output_path)

    finally:
        # Clean up concat file
        if concat_file.exists():
            concat_file.unlink()


def convert_audio_format(
    input_path: str,
    output_path: str,
    sample_rate: Optional[int] = None,
    channels: Optional[int] = None
) -> str:
    """
    Convert audio file to different format.

    Args:
        input_path: Path to input audio file
        output_path: Path for output audio file (format determined by extension)
        sample_rate: Optional sample rate for output
        channels: Optional number of channels for output

    Returns:
        Path to converted audio file

    Raises:
        FFmpegError: If conversion fails
        FileNotFoundError: If input file doesn't exist
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Audio file not found: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    args = ["ffmpeg", "-i", str(input_path)]

    if sample_rate:
        args.extend(["-ar", str(sample_rate)])
    if channels:
        args.extend(["-ac", str(channels)])

    args.extend(["-y", str(output_path)])

    _run_ffmpeg(args, f"Convert {input_path.name} to {output_path.suffix}")

    if not output_path.exists():
        raise FFmpegError(f"Audio conversion failed: output file not created")

    logger.info(f"Audio converted to {output_path}")
    return str(output_path)


def get_audio_duration(audio_path: str) -> float:
    """
    Get audio file duration in seconds.

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds

    Raises:
        FFmpegError: If duration cannot be determined
        FileNotFoundError: If audio file doesn't exist
    """
    audio_path = Path(audio_path)

    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    args = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json",
        str(audio_path)
    ]

    output = _run_ffprobe(args, f"Get duration of {audio_path.name}")

    try:
        data = json.loads(output)
        duration = float(data["format"]["duration"])
        logger.info(f"Audio duration: {duration:.2f} seconds")
        return duration
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        raise FFmpegError(f"Failed to parse audio duration: {e}")
