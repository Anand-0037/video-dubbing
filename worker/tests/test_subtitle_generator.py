"""Tests for subtitle generation utilities."""

import pytest
from pathlib import Path

from worker.utils.subtitle_generator import (
    format_srt_time,
    parse_srt_time,
    generate_srt,
    save_srt,
    parse_srt,
    load_srt,
    validate_srt,
    SubtitleError,
)
from worker.models.segments import TranscriptionSegment, TranslationSegment


class TestFormatSrtTime:
    """Tests for format_srt_time function."""

    def test_format_zero(self):
        """Test formatting zero seconds."""
        assert format_srt_time(0) == "00:00:00,000"

    def test_format_seconds_only(self):
        """Test formatting seconds only."""
        assert format_srt_time(5) == "00:00:05,000"
        assert format_srt_time(59) == "00:00:59,000"

    def test_format_minutes_and_seconds(self):
        """Test formatting minutes and seconds."""
        assert format_srt_time(65) == "00:01:05,000"
        assert format_srt_time(125.5) == "00:02:05,500"

    def test_format_hours(self):
        """Test formatting hours."""
        assert format_srt_time(3661.123) == "01:01:01,123"
        assert format_srt_time(7200) == "02:00:00,000"

    def test_format_milliseconds(self):
        """Test formatting milliseconds."""
        assert format_srt_time(1.5) == "00:00:01,500"
        assert format_srt_time(1.123) == "00:00:01,123"
        assert format_srt_time(1.999) == "00:00:01,999"

    def test_format_negative(self):
        """Test formatting negative values (should clamp to 0)."""
        assert format_srt_time(-5) == "00:00:00,000"


class TestParseSrtTime:
    """Tests for parse_srt_time function."""

    def test_parse_zero(self):
        """Test parsing zero timestamp."""
        assert parse_srt_time("00:00:00,000") == 0

    def test_parse_seconds(self):
        """Test parsing seconds."""
        assert parse_srt_time("00:00:05,000") == 5
        assert parse_srt_time("00:00:59,000") == 59

    def test_parse_minutes(self):
        """Test parsing minutes."""
        assert parse_srt_time("00:01:05,000") == 65
        assert parse_srt_time("00:02:05,500") == 125.5

    def test_parse_hours(self):
        """Test parsing hours."""
        assert parse_srt_time("01:01:01,123") == 3661.123
        assert parse_srt_time("02:00:00,000") == 7200

    def test_parse_invalid_format(self):
        """Test parsing invalid format."""
        with pytest.raises(ValueError):
            parse_srt_time("invalid")

        with pytest.raises(ValueError):
            parse_srt_time("00:00:00")  # Missing milliseconds

    def test_roundtrip(self):
        """Test format -> parse roundtrip."""
        test_values = [0, 1.5, 65.123, 3661.999, 7200]
        for value in test_values:
            formatted = format_srt_time(value)
            parsed = parse_srt_time(formatted)
            assert abs(parsed - value) < 0.001


class TestGenerateSrt:
    """Tests for generate_srt function."""

    def test_generate_empty(self):
        """Test generating from empty list."""
        assert generate_srt([]) == ""

    def test_generate_single_segment(self):
        """Test generating single segment."""
        segments = [
            TranscriptionSegment(id=1, start=0, end=5, text="Hello world")
        ]

        srt = generate_srt(segments)

        assert "1\n" in srt
        assert "00:00:00,000 --> 00:00:05,000" in srt
        assert "Hello world" in srt

    def test_generate_multiple_segments(self):
        """Test generating multiple segments."""
        segments = [
            TranscriptionSegment(id=1, start=0, end=5, text="First segment"),
            TranscriptionSegment(id=2, start=5, end=10, text="Second segment"),
            TranscriptionSegment(id=3, start=10, end=15, text="Third segment"),
        ]

        srt = generate_srt(segments)

        assert "First segment" in srt
        assert "Second segment" in srt
        assert "Third segment" in srt

    def test_generate_translation_original(self):
        """Test generating from translation segments using original text."""
        segments = [
            TranslationSegment(
                id=1, start=0, end=5,
                original_text="Hello",
                translated_text="नमस्ते",
                source_language="english",
                target_language="hindi"
            )
        ]

        srt = generate_srt(segments, use_translated=False)

        assert "Hello" in srt
        assert "नमस्ते" not in srt

    def test_generate_translation_translated(self):
        """Test generating from translation segments using translated text."""
        segments = [
            TranslationSegment(
                id=1, start=0, end=5,
                original_text="Hello",
                translated_text="नमस्ते",
                source_language="english",
                target_language="hindi"
            )
        ]

        srt = generate_srt(segments, use_translated=True)

        assert "नमस्ते" in srt
        assert "Hello" not in srt

    def test_generate_skips_empty_text(self):
        """Test that empty segments are skipped."""
        segments = [
            TranscriptionSegment(id=1, start=0, end=5, text="Valid"),
            TranscriptionSegment(id=2, start=5, end=10, text=""),
            TranscriptionSegment(id=3, start=10, end=15, text="Also valid"),
        ]

        srt = generate_srt(segments)

        assert "Valid" in srt
        assert "Also valid" in srt
        # Empty segment should be skipped


class TestSaveSrt:
    """Tests for save_srt function."""

    def test_save_srt_file(self, tmp_path):
        """Test saving SRT file."""
        segments = [
            TranscriptionSegment(id=1, start=0, end=5, text="Test content")
        ]

        output_path = tmp_path / "test.srt"
        result = save_srt(segments, str(output_path))

        assert result == str(output_path)
        assert output_path.exists()

        content = output_path.read_text()
        assert "Test content" in content

    def test_save_creates_directory(self, tmp_path):
        """Test that save creates parent directories."""
        segments = [
            TranscriptionSegment(id=1, start=0, end=5, text="Test")
        ]

        output_path = tmp_path / "subdir" / "nested" / "test.srt"
        save_srt(segments, str(output_path))

        assert output_path.exists()


class TestParseSrt:
    """Tests for parse_srt function."""

    def test_parse_single_segment(self):
        """Test parsing single segment."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
Hello world"""

        segments = parse_srt(srt_content)

        assert len(segments) == 1
        assert segments[0]["id"] == 1
        assert segments[0]["start"] == 0
        assert segments[0]["end"] == 5
        assert segments[0]["text"] == "Hello world"

    def test_parse_multiple_segments(self):
        """Test parsing multiple segments."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
First

2
00:00:05,000 --> 00:00:10,000
Second"""

        segments = parse_srt(srt_content)

        assert len(segments) == 2
        assert segments[0]["text"] == "First"
        assert segments[1]["text"] == "Second"

    def test_parse_multiline_text(self):
        """Test parsing multiline text."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
Line one
Line two"""

        segments = parse_srt(srt_content)

        assert segments[0]["text"] == "Line one\nLine two"

    def test_parse_empty(self):
        """Test parsing empty content."""
        assert parse_srt("") == []
        assert parse_srt("   ") == []


class TestLoadSrt:
    """Tests for load_srt function."""

    def test_load_file(self, tmp_path):
        """Test loading SRT file."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
Test content"""

        srt_file = tmp_path / "test.srt"
        srt_file.write_text(srt_content)

        segments = load_srt(str(srt_file))

        assert len(segments) == 1
        assert segments[0]["text"] == "Test content"

    def test_load_nonexistent(self, tmp_path):
        """Test loading non-existent file."""
        with pytest.raises(FileNotFoundError):
            load_srt(str(tmp_path / "nonexistent.srt"))


class TestValidateSrt:
    """Tests for validate_srt function."""

    def test_validate_valid_srt(self):
        """Test validating valid SRT."""
        srt_content = """1
00:00:00,000 --> 00:00:05,000
First segment

2
00:00:05,000 --> 00:00:10,000
Second segment"""

        is_valid, errors = validate_srt(srt_content)

        assert is_valid
        assert len(errors) == 0

    def test_validate_empty(self):
        """Test validating empty content."""
        is_valid, errors = validate_srt("")

        assert not is_valid
        assert "Empty SRT content" in errors[0]

    def test_validate_overlapping(self):
        """Test detecting overlapping segments."""
        srt_content = """1
00:00:00,000 --> 00:00:10,000
First

2
00:00:05,000 --> 00:00:15,000
Second (overlaps)"""

        is_valid, errors = validate_srt(srt_content)

        assert not is_valid
        assert any("Overlapping" in e for e in errors)

    def test_validate_end_before_start(self):
        """Test detecting end time before start time."""
        srt_content = """1
00:00:10,000 --> 00:00:05,000
Invalid timing"""

        is_valid, errors = validate_srt(srt_content)

        assert not is_valid
        assert any("End time" in e for e in errors)
