from dataclasses import dataclass
from typing import List, Optional

@dataclass
class TranscriptionSegment:
    """Represents a transcribed segment with timing information."""
    id: int
    start: float  # Start time in seconds
    end: float    # End time in seconds
    text: str     # Transcribed text

    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end - self.start

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TranscriptionSegment":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            start=data["start"],
            end=data["end"],
            text=data["text"],
        )

@dataclass
class TranslationSegment:
    """Represents a translated segment with timing information."""
    id: int
    start: float           # Start time in seconds
    end: float             # End time in seconds
    original_text: str     # Original text
    translated_text: str   # Translated text
    source_language: str   # Source language code
    target_language: str   # Target language code

    @property
    def duration(self) -> float:
        """Get segment duration in seconds."""
        return self.end - self.start

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "original_text": self.original_text,
            "translated_text": self.translated_text,
            "source_language": self.source_language,
            "target_language": self.target_language,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TranslationSegment":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            start=data["start"],
            end=data["end"],
            original_text=data["original_text"],
            translated_text=data["translated_text"],
            source_language=data["source_language"],
            target_language=data["target_language"],
        )

@dataclass
class SynthesizedSegment:
    """Represents a synthesized audio segment."""
    id: int
    start: float           # Target start time in seconds
    end: float             # Target end time in seconds
    text: str              # Text that was synthesized
    audio_path: str        # Path to audio file
    actual_duration: float # Actual duration of synthesized audio

    @property
    def target_duration(self) -> float:
        """Get target duration in seconds."""
        return self.end - self.start

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "audio_path": self.audio_path,
            "actual_duration": self.actual_duration,
        }
