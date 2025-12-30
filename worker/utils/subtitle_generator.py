"""Subtitle generation utilities for SRT format."""

import logging
from pathlib import Path
from typing import List, Tuple, Union

from worker.models.segments import TranscriptionSegment, TranslationSegment

logger = logging.getLogger(__name__)


class SubtitleError(Exception):
    """Exception raised when subtitle operations fail."""
    pass


def format_srt_time(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string

    Examples:
        >>> format_srt_time(0)
        '00:00:00,000'
        >>> format_srt_time(65.5)
        '00:01:05,500'
        >>> format_srt_time(3661.123)
        '01:01:01,123'
    """
    if seconds < 0:
        seconds = 0

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def parse_srt_time(timestamp: str) -> float:
    """
    Parse SRT timestamp to seconds.

    Args:
        timestamp: SRT timestamp (HH:MM:SS,mmm)

    Returns:
        Time in seconds

    Raises:
        ValueError: If timestamp format is invalid
    """
    try:
        time_part, millis_part = timestamp.split(",")
        hours, minutes, seconds = time_part.split(":")

        total_seconds = (
            int(hours) * 3600 +
            int(minutes) * 60 +
            int(seconds) +
            int(millis_part) / 1000
        )

        return total_seconds
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid SRT timestamp format: {timestamp}") from e


def generate_srt(
    segments: List[Union[TranscriptionSegment, TranslationSegment]],
    use_translated: bool = False,
) -> str:
    """
    Generate SRT subtitle content from segments.

    Args:
        segments: List of transcription or translation segments
        use_translated: If True and segments are TranslationSegment, use translated_text

    Returns:
        SRT formatted string

    Raises:
        SubtitleError: If segment data is invalid
    """
    if not segments:
        return ""

    srt_lines = []

    for i, seg in enumerate(segments, start=1):
        # Validate segment
        if seg.start < 0 or seg.end < 0:
            raise SubtitleError(f"Invalid segment timing: start={seg.start}, end={seg.end}")
        if seg.end < seg.start:
            logger.warning(f"Segment {i} has end time before start time, swapping")
            seg.start, seg.end = seg.end, seg.start

        # Get text based on segment type
        if isinstance(seg, TranslationSegment) and use_translated:
            text = seg.translated_text
        elif isinstance(seg, TranslationSegment):
            text = seg.original_text
        else:
            text = seg.text

        # Skip empty segments
        if not text or not text.strip():
            logger.warning(f"Skipping empty segment {i}")
            continue

        # Format SRT entry
        start_time = format_srt_time(seg.start)
        end_time = format_srt_time(seg.end)

        srt_entry = f"{i}\n{start_time} --> {end_time}\n{text.strip()}\n"
        srt_lines.append(srt_entry)

    return "\n".join(srt_lines)


def save_srt(
    segments: List[Union[TranscriptionSegment, TranslationSegment]],
    output_path: str,
    use_translated: bool = False,
    encoding: str = "utf-8",
) -> str:
    """
    Generate and save SRT subtitle file.

    Args:
        segments: List of transcription or translation segments
        output_path: Path to save SRT file
        use_translated: If True and segments are TranslationSegment, use translated_text
        encoding: File encoding (default UTF-8)

    Returns:
        Path to saved file

    Raises:
        SubtitleError: If generation or saving fails
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    srt_content = generate_srt(segments, use_translated)

    try:
        with open(output_path, "w", encoding=encoding) as f:
            f.write(srt_content)

        logger.info(f"Saved SRT file to {output_path}")
        return str(output_path)

    except IOError as e:
        raise SubtitleError(f"Failed to save SRT file: {e}")


def parse_srt(srt_content: str) -> List[dict]:
    """
    Parse SRT content into segment dictionaries.

    Args:
        srt_content: SRT formatted string

    Returns:
        List of dicts with id, start, end, text

    Raises:
        SubtitleError: If SRT format is invalid
    """
    segments = []

    # Split into blocks (separated by blank lines)
    blocks = srt_content.strip().split("\n\n")

    for block in blocks:
        if not block.strip():
            continue

        lines = block.strip().split("\n")

        if len(lines) < 3:
            logger.warning(f"Skipping malformed SRT block: {block[:50]}...")
            continue

        try:
            # Parse segment ID
            seg_id = int(lines[0].strip())

            # Parse timestamps
            timestamp_line = lines[1].strip()
            if " --> " not in timestamp_line:
                raise SubtitleError(f"Invalid timestamp line: {timestamp_line}")

            start_str, end_str = timestamp_line.split(" --> ")
            start = parse_srt_time(start_str.strip())
            end = parse_srt_time(end_str.strip())

            # Parse text (may span multiple lines)
            text = "\n".join(lines[2:]).strip()

            segments.append({
                "id": seg_id,
                "start": start,
                "end": end,
                "text": text,
            })

        except (ValueError, IndexError) as e:
            logger.warning(f"Failed to parse SRT block: {e}")
            continue

    return segments


def load_srt(file_path: str, encoding: str = "utf-8") -> List[dict]:
    """
    Load and parse SRT file.

    Args:
        file_path: Path to SRT file
        encoding: File encoding (default UTF-8)

    Returns:
        List of segment dictionaries

    Raises:
        FileNotFoundError: If file doesn't exist
        SubtitleError: If parsing fails
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"SRT file not found: {file_path}")

    try:
        with open(file_path, "r", encoding=encoding) as f:
            content = f.read()

        return parse_srt(content)

    except IOError as e:
        raise SubtitleError(f"Failed to read SRT file: {e}")


def validate_srt(srt_content: str) -> Tuple[bool, List[str]]:
    """
    Validate SRT content format.

    Args:
        srt_content: SRT formatted string

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not srt_content or not srt_content.strip():
        return False, ["Empty SRT content"]

    blocks = srt_content.strip().split("\n\n")

    prev_end = 0

    for i, block in enumerate(blocks, start=1):
        if not block.strip():
            continue

        lines = block.strip().split("\n")

        # Check minimum lines
        if len(lines) < 3:
            errors.append(f"Block {i}: Insufficient lines (need at least 3)")
            continue

        # Check segment ID
        try:
            seg_id = int(lines[0].strip())
            if seg_id != i:
                errors.append(f"Block {i}: Segment ID mismatch (expected {i}, got {seg_id})")
        except ValueError:
            errors.append(f"Block {i}: Invalid segment ID '{lines[0]}'")

        # Check timestamp format
        timestamp_line = lines[1].strip()
        if " --> " not in timestamp_line:
            errors.append(f"Block {i}: Missing ' --> ' in timestamp")
            continue

        try:
            start_str, end_str = timestamp_line.split(" --> ")
            start = parse_srt_time(start_str.strip())
            end = parse_srt_time(end_str.strip())

            if end <= start:
                errors.append(f"Block {i}: End time ({end}) <= start time ({start})")

            if start < prev_end:
                errors.append(f"Block {i}: Overlapping with previous segment")

            prev_end = end

        except ValueError as e:
            errors.append(f"Block {i}: Invalid timestamp format - {e}")

        # Check text content
        text = "\n".join(lines[2:]).strip()
        if not text:
            errors.append(f"Block {i}: Empty text content")

    return len(errors) == 0, errors
