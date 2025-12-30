"""Data models for transcription and translation segments."""

from dataclasses import dataclass
from typing import List, Optional


from dubwizard_shared import TranscriptionSegment, TranslationSegment, SynthesizedSegment


def segments_to_srt_format(segments: List[TranslationSegment], use_translated: bool = True) -> List[dict]:
    """
    Convert segments to SRT-compatible format.

    Args:
        segments: List of translation segments
        use_translated: If True, use translated_text; otherwise use original_text

    Returns:
        List of dicts with id, start, end, text
    """
    return [
        {
            "id": seg.id,
            "start": seg.start,
            "end": seg.end,
            "text": seg.translated_text if use_translated else seg.original_text,
        }
        for seg in segments
    ]
