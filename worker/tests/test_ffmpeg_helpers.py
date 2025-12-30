"""Tests for FFmpeg helper functions."""

import pytest
from unittest.mock import patch, MagicMock
import json
import subprocess

from worker.utils.ffmpeg_helpers import (
    extract_audio,
    get_video_duration,
    get_video_metadata,
    mux_audio_video,
    concatenate_audio_files,
    convert_audio_format,
    get_audio_duration,
    FFmpegError,
    _run_ffmpeg,
    _run_ffprobe,
)


class TestRunFFmpeg:
    """Tests for _run_ffmpeg helper."""

    @patch("subprocess.run")
    def test_run_ffmpeg_success(self, mock_run):
        """Test successful FFmpeg execution."""
        mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")

        result = _run_ffmpeg(["ffmpeg", "-version"], "test")

        assert result.returncode == 0
        mock_run.assert_called_once()

    @patch("subprocess.run")
    def test_run_ffmpeg_failure(self, mock_run):
        """Test FFmpeg execution failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error message")

        with pytest.raises(FFmpegError) as exc_info:
            _run_ffmpeg(["ffmpeg", "-invalid"], "test")

        assert "FFmpeg failed" in str(exc_info.value)

    @patch("subprocess.run")
    def test_run_ffmpeg_timeout(self, mock_run):
        """Test FFmpeg timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=300)

        with pytest.raises(FFmpegError) as exc_info:
            _run_ffmpeg(["ffmpeg", "-version"], "test")

        assert "timed out" in str(exc_info.value)

    @patch("subprocess.run")
    def test_run_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg not installed."""
        mock_run.side_effect = FileNotFoundError()

        with pytest.raises(FFmpegError) as exc_info:
            _run_ffmpeg(["ffmpeg", "-version"], "test")

        assert "not installed" in str(exc_info.value)


class TestRunFFprobe:
    """Tests for _run_ffprobe helper."""

    @patch("subprocess.run")
    def test_run_ffprobe_success(self, mock_run):
        """Test successful FFprobe execution."""
        mock_run.return_value = MagicMock(returncode=0, stdout='{"format": {}}', stderr="")

        result = _run_ffprobe(["ffprobe", "-version"], "test")

        assert result == '{"format": {}}'

    @patch("subprocess.run")
    def test_run_ffprobe_failure(self, mock_run):
        """Test FFprobe execution failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Error")

        with pytest.raises(FFmpegError):
            _run_ffprobe(["ffprobe", "-invalid"], "test")


class TestExtractAudio:
    """Tests for extract_audio function."""

    def test_extract_audio_file_not_found(self, tmp_path):
        """Test extraction with non-existent video."""
        with pytest.raises(FileNotFoundError):
            extract_audio(
                str(tmp_path / "nonexistent.mp4"),
                str(tmp_path / "output.wav")
            )

    @patch("worker.utils.ffmpeg_helpers._run_ffmpeg")
    def test_extract_audio_success(self, mock_ffmpeg, tmp_path):
        """Test successful audio extraction."""
        # Create dummy input file
        video_path = tmp_path / "input.mp4"
        video_path.touch()

        output_path = tmp_path / "output.wav"

        # Mock FFmpeg to create output file
        def create_output(*args, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        mock_ffmpeg.side_effect = create_output

        result = extract_audio(str(video_path), str(output_path))

        assert result == str(output_path)
        mock_ffmpeg.assert_called_once()

    @patch("worker.utils.ffmpeg_helpers._run_ffmpeg")
    def test_extract_audio_custom_params(self, mock_ffmpeg, tmp_path):
        """Test audio extraction with custom parameters."""
        video_path = tmp_path / "input.mp4"
        video_path.touch()
        output_path = tmp_path / "output.wav"

        def create_output(*args, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        mock_ffmpeg.side_effect = create_output

        extract_audio(
            str(video_path),
            str(output_path),
            sample_rate=44100,
            channels=2
        )

        # Verify FFmpeg was called with correct args
        call_args = mock_ffmpeg.call_args[0][0]
        assert "-ar" in call_args
        assert "44100" in call_args
        assert "-ac" in call_args
        assert "2" in call_args


class TestGetVideoDuration:
    """Tests for get_video_duration function."""

    def test_get_duration_file_not_found(self, tmp_path):
        """Test duration with non-existent video."""
        with pytest.raises(FileNotFoundError):
            get_video_duration(str(tmp_path / "nonexistent.mp4"))

    @patch("worker.utils.ffmpeg_helpers._run_ffprobe")
    def test_get_duration_success(self, mock_ffprobe, tmp_path):
        """Test successful duration retrieval."""
        video_path = tmp_path / "input.mp4"
        video_path.touch()

        mock_ffprobe.return_value = json.dumps({
            "format": {"duration": "45.5"}
        })

        duration = get_video_duration(str(video_path))

        assert duration == 45.5

    @patch("worker.utils.ffmpeg_helpers._run_ffprobe")
    def test_get_duration_invalid_json(self, mock_ffprobe, tmp_path):
        """Test duration with invalid JSON response."""
        video_path = tmp_path / "input.mp4"
        video_path.touch()

        mock_ffprobe.return_value = "invalid json"

        with pytest.raises(FFmpegError):
            get_video_duration(str(video_path))


class TestGetVideoMetadata:
    """Tests for get_video_metadata function."""

    def test_get_metadata_file_not_found(self, tmp_path):
        """Test metadata with non-existent video."""
        with pytest.raises(FileNotFoundError):
            get_video_metadata(str(tmp_path / "nonexistent.mp4"))

    @patch("worker.utils.ffmpeg_helpers._run_ffprobe")
    def test_get_metadata_success(self, mock_ffprobe, tmp_path):
        """Test successful metadata retrieval."""
        video_path = tmp_path / "input.mp4"
        video_path.touch()

        # First call for video metadata
        video_response = json.dumps({
            "format": {"duration": "45.5"},
            "streams": [{
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
                "codec_name": "h264"
            }]
        })

        # Second call for audio metadata
        audio_response = json.dumps({
            "streams": [{"codec_name": "aac"}]
        })

        mock_ffprobe.side_effect = [video_response, audio_response]

        metadata = get_video_metadata(str(video_path))

        assert metadata["width"] == 1920
        assert metadata["height"] == 1080
        assert metadata["fps"] == 30.0
        assert metadata["video_codec"] == "h264"
        assert metadata["audio_codec"] == "aac"
        assert metadata["duration"] == 45.5


class TestMuxAudioVideo:
    """Tests for mux_audio_video function."""

    def test_mux_video_not_found(self, tmp_path):
        """Test muxing with non-existent video."""
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()

        with pytest.raises(FileNotFoundError):
            mux_audio_video(
                str(tmp_path / "nonexistent.mp4"),
                str(audio_path),
                str(tmp_path / "output.mp4")
            )

    def test_mux_audio_not_found(self, tmp_path):
        """Test muxing with non-existent audio."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()

        with pytest.raises(FileNotFoundError):
            mux_audio_video(
                str(video_path),
                str(tmp_path / "nonexistent.wav"),
                str(tmp_path / "output.mp4")
            )

    @patch("worker.utils.ffmpeg_helpers._run_ffmpeg")
    def test_mux_success(self, mock_ffmpeg, tmp_path):
        """Test successful audio muxing."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        output_path = tmp_path / "output.mp4"

        def create_output(*args, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        mock_ffmpeg.side_effect = create_output

        result = mux_audio_video(
            str(video_path),
            str(audio_path),
            str(output_path)
        )

        assert result == str(output_path)

    @patch("worker.utils.ffmpeg_helpers._run_ffmpeg")
    def test_mux_keep_original_audio(self, mock_ffmpeg, tmp_path):
        """Test muxing while keeping original audio."""
        video_path = tmp_path / "video.mp4"
        video_path.touch()
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()
        output_path = tmp_path / "output.mp4"

        def create_output(*args, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        mock_ffmpeg.side_effect = create_output

        mux_audio_video(
            str(video_path),
            str(audio_path),
            str(output_path),
            keep_original_audio=True
        )

        # Verify amix filter was used
        call_args = mock_ffmpeg.call_args[0][0]
        assert "amix" in str(call_args)


class TestConcatenateAudioFiles:
    """Tests for concatenate_audio_files function."""

    def test_concatenate_empty_list(self, tmp_path):
        """Test concatenation with empty file list."""
        with pytest.raises(ValueError):
            concatenate_audio_files([], str(tmp_path / "output.mp3"))

    def test_concatenate_file_not_found(self, tmp_path):
        """Test concatenation with non-existent file."""
        with pytest.raises(FileNotFoundError):
            concatenate_audio_files(
                [str(tmp_path / "nonexistent.mp3")],
                str(tmp_path / "output.mp3")
            )

    @patch("worker.utils.ffmpeg_helpers._run_ffmpeg")
    def test_concatenate_success(self, mock_ffmpeg, tmp_path):
        """Test successful audio concatenation."""
        # Create dummy input files
        audio1 = tmp_path / "audio1.mp3"
        audio1.touch()
        audio2 = tmp_path / "audio2.mp3"
        audio2.touch()
        output_path = tmp_path / "output.mp3"

        def create_output(*args, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        mock_ffmpeg.side_effect = create_output

        result = concatenate_audio_files(
            [str(audio1), str(audio2)],
            str(output_path)
        )

        assert result == str(output_path)


class TestConvertAudioFormat:
    """Tests for convert_audio_format function."""

    def test_convert_file_not_found(self, tmp_path):
        """Test conversion with non-existent file."""
        with pytest.raises(FileNotFoundError):
            convert_audio_format(
                str(tmp_path / "nonexistent.wav"),
                str(tmp_path / "output.mp3")
            )

    @patch("worker.utils.ffmpeg_helpers._run_ffmpeg")
    def test_convert_success(self, mock_ffmpeg, tmp_path):
        """Test successful audio conversion."""
        input_path = tmp_path / "input.wav"
        input_path.touch()
        output_path = tmp_path / "output.mp3"

        def create_output(*args, **kwargs):
            output_path.touch()
            return MagicMock(returncode=0)

        mock_ffmpeg.side_effect = create_output

        result = convert_audio_format(str(input_path), str(output_path))

        assert result == str(output_path)


class TestGetAudioDuration:
    """Tests for get_audio_duration function."""

    def test_get_audio_duration_file_not_found(self, tmp_path):
        """Test duration with non-existent audio."""
        with pytest.raises(FileNotFoundError):
            get_audio_duration(str(tmp_path / "nonexistent.wav"))

    @patch("worker.utils.ffmpeg_helpers._run_ffprobe")
    def test_get_audio_duration_success(self, mock_ffprobe, tmp_path):
        """Test successful audio duration retrieval."""
        audio_path = tmp_path / "audio.wav"
        audio_path.touch()

        mock_ffprobe.return_value = json.dumps({
            "format": {"duration": "30.5"}
        })

        duration = get_audio_duration(str(audio_path))

        assert duration == 30.5
