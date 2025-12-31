"""AI service integrations for transcription, translation, and TTS."""

import logging
import os
import time
import json
import requests
from pathlib import Path
from typing import List, Optional, Tuple
from openai import OpenAI

from dubwizard_shared import (
    TranscriptionSegment,
    TranslationSegment,
    SynthesizedSegment,
    shared_settings as settings,
)

logger = logging.getLogger(__name__)


class AIServiceError(Exception):
    """Exception raised when AI service operations fail."""
    pass


class AIService:
    """Service for AI-powered transcription, translation, and TTS."""

    # Retry configuration
    MAX_RETRIES = 2
    RETRY_DELAYS = [1, 2]  # Exponential backoff delays in seconds

    def __init__(
        self,
        openai_api_key: Optional[str] = None,
        elevenlabs_api_key: Optional[str] = None,
    ):
        """
        Initialize AI service with API keys.

        Args:
            openai_api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            elevenlabs_api_key: ElevenLabs API key (defaults to ELEVENLABS_API_KEY env var)
        """
        self.openai_api_key = openai_api_key or settings.OPENAI_API_KEY
        self.groq_api_key = settings.GROQ_API_KEY
        self.elevenlabs_api_key = elevenlabs_api_key or settings.ELEVENLABS_API_KEY

        # Check for mock keys
        self.mock_mode = (
            settings.USE_MOCK_AI or
            "mock" in (self.openai_api_key or "").lower() or
            "mock" in (self.elevenlabs_api_key or "").lower()
        )

        if not self.mock_mode:
            # Initialize OpenAI Client (fallback or primary if no Groq)
            self.openai_client = None
            if self.openai_api_key:
                self.openai_client = OpenAI(api_key=self.openai_api_key)

            # Initialize Groq Client
            self.groq_client = None
            if self.groq_api_key:
                try:
                    self.groq_client = OpenAI(
                        base_url="https://api.groq.com/openai/v1",
                        api_key=self.groq_api_key
                    )
                    logger.info("Initialized Groq client")
                except Exception as e:
                    logger.warning(f"Failed to initialize Groq client: {e}")

            if not self.openai_client and not self.groq_client:
                 raise AIServiceError("No AI Provider API keys provided (OpenAI or Groq)")

            if not self.elevenlabs_api_key:
                 raise AIServiceError("ElevenLabs API key not provided")
        else:
            logger.info("AIService running in MOCK MODE")
            self.openai_client = None
            self.groq_client = None

        # ElevenLabs API configuration
        self.elevenlabs_base_url = "https://api.elevenlabs.io/v1"
        self.elevenlabs_model = "eleven_multilingual_v2"


    def _retry_with_backoff(self, func, description: str, *args, **kwargs):
        """
        Execute function with retry logic and exponential backoff.

        Args:
            func: Function to execute
            description: Description for logging
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            AIServiceError: If all retries fail
        """
        last_error = None

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_DELAYS[attempt]
                    logger.warning(
                        f"{description} failed (attempt {attempt + 1}/{self.MAX_RETRIES + 1}): {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"{description} failed after {self.MAX_RETRIES + 1} attempts: {e}")

        raise AIServiceError(f"{description} failed: {last_error}")

    def transcribe_audio(
        self,
        audio_path: str,
        language: str = "en",
    ) -> List[TranscriptionSegment]:
        """
        Transcribe audio using Groq Whisper (preferred) or OpenAI Whisper API.

        Args:
            audio_path: Path to audio file (WAV, MP3, etc.)
            language: Language code (default "en" for English)

        Returns:
            List of TranscriptionSegment with timestamps

        Raises:
            AIServiceError: If transcription fails
            FileNotFoundError: If audio file doesn't exist
        """
        if self.mock_mode:
            logger.info("MOCK MODE: Returning dummy transcription")
            return [
                TranscriptionSegment(id=1, start=0.0, end=2.0, text="Hello world."),
                TranscriptionSegment(id=2, start=2.5, end=4.5, text="This is a test video."),
                TranscriptionSegment(id=3, start=5.0, end=7.0, text="For debugging purposes."),
            ]

        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing audio: {audio_path.name}")

        def _transcribe():
            with open(audio_path, "rb") as audio_file:
                # Prefer Groq
                if self.groq_client:
                    logger.info("Using Groq for transcription...")
                    return self.groq_client.audio.transcriptions.create(
                        model="whisper-large-v3",
                        file=audio_file,
                        language=language,
                        response_format="verbose_json",
                    )
                elif self.openai_client:
                    logger.info("Using OpenAI for transcription...")
                    return self.openai_client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio_file,
                        language=language,
                        response_format="verbose_json",
                    )
                else:
                    raise AIServiceError("No AI client available")

        response = self._retry_with_backoff(_transcribe, "Whisper transcription")

        # Parse response into segments
        segments = []
        for i, seg in enumerate(response.segments):
            segment = TranscriptionSegment(
                id=i + 1,
                start=seg['start'],
                end=seg['end'],
                text=seg['text'].strip(),
            )
            segments.append(segment)

        logger.info(f"Transcribed {len(segments)} segments")
        return segments

    def translate_segments(
        self,
        segments: List[TranscriptionSegment],
        source_language: str = "english",
        target_language: str = "hindi",
    ) -> List[TranslationSegment]:
        """
        Translate transcription segments using Groq (Llama3) or GPT-4.

        Args:
            segments: List of transcription segments
            source_language: Source language name
            target_language: Target language name

        Returns:
            List of TranslationSegment with translations

        Raises:
            AIServiceError: If translation fails
        """
        if not segments:
            return []

        logger.info(f"Translating {len(segments)} segments from {source_language} to {target_language}")

        if self.mock_mode:
            logger.info("MOCK MODE: Returning dummy translation")
            translation_segments = []
            for seg in segments:
                translation_segment = TranslationSegment(
                    id=seg.id,
                    start=seg.start,
                    end=seg.end,
                    original_text=seg.text,
                    translated_text=f"Translated: {seg.text}",
                    source_language=source_language,
                    target_language=target_language,
                )
                translation_segments.append(translation_segment)
            return translation_segments

        # Prepare batch translation prompt
        texts = [seg.text for seg in segments]
        texts_json = json.dumps(texts, ensure_ascii=False)

        prompt = f"""Translate the following {source_language} text segments to {target_language}.
Return ONLY a JSON array of translated strings in the same order.
IMPORTANT: You MUST return exactly {len(segments)} translated strings. Do not merge or split sentences.
Do not add any explanation or formatting.

Input texts ({len(segments)} segments):
{texts_json}

Output (JSON array of {len(segments)} strings):"""

        def _translate():
            if self.groq_client:
                logger.info("Using Groq (Llama 3.3) for translation...")
                response = self.groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a professional translator. Translate from {source_language} to {target_language}. "
                                       "Preserve the meaning and tone. Return only valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
                return response.choices[0].message.content
            elif self.openai_client:
                logger.info("Using OpenAI (GPT-4) for translation...")
                response = self.openai_client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": f"You are a professional translator. Translate from {source_language} to {target_language}. "
                                       "Preserve the meaning and tone. Return only valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=4096,
                )
                return response.choices[0].message.content
            else:
                 raise AIServiceError("No AI client available")

        response_text = self._retry_with_backoff(_translate, "Translation")

        # Parse translated texts
        try:
            # Clean up response (remove markdown code blocks if present)
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
            response_text = response_text.strip()

            translated_texts = json.loads(response_text)

            if len(translated_texts) != len(segments):
                raise AIServiceError(
                    f"Translation count mismatch: expected {len(segments)}, got {len(translated_texts)}"
                )
        except json.JSONDecodeError as e:
            raise AIServiceError(f"Failed to parse translation response: {e}")

        # Create translation segments
        translation_segments = []
        for seg, translated in zip(segments, translated_texts):
            translation_segment = TranslationSegment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                original_text=seg.text,
                translated_text=translated,
                source_language=source_language,
                target_language=target_language,
            )
            translation_segments.append(translation_segment)

        logger.info(f"Translated {len(translation_segments)} segments")
        return translation_segments

    def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        output_path: str,
    ) -> Tuple[str, float]:
        """
        Synthesize speech using ElevenLabs API.

        Args:
            text: Text to synthesize
            voice_id: ElevenLabs voice ID
            output_path: Path to save audio file

        Returns:
            Tuple of (output_path, duration_seconds)

        Raises:
            AIServiceError: If synthesis fails
        """
        logger.debug(f"Synthesizing speech: {text[:50]}...")

        if self.mock_mode:
            logger.info(f"MOCK MODE: Synthesizing dummy speech for '{text[:20]}...'")
            # Generate silent audio using ffmpeg
            import subprocess
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                "-t", "2", "-q:a", "9", "-acodec", "libmp3lame", str(output_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return str(output_path), 2.0

        logger.debug(f"Synthesizing speech: {text[:50]}...")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        def _synthesize():
            url = f"{self.elevenlabs_base_url}/text-to-speech/{voice_id}"

            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": self.elevenlabs_api_key,
            }

            data = {
                "text": text,
                "model_id": self.elevenlabs_model,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                }
            }

            response = requests.post(url, json=data, headers=headers, timeout=60)

            if response.status_code != 200:
                raise AIServiceError(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )

            return response.content

        audio_content = self._retry_with_backoff(_synthesize, "ElevenLabs TTS")

        # Save audio file
        with open(output_path, "wb") as f:
            f.write(audio_content)

        # Get audio duration using ffprobe
        from worker.utils.ffmpeg_helpers import get_audio_duration
        duration = get_audio_duration(str(output_path))

        logger.debug(f"Synthesized audio saved to {output_path} ({duration:.2f}s)")
        return str(output_path), duration

    def synthesize_segments(
        self,
        segments: List[TranslationSegment],
        voice_id: str,
        output_dir: str,
    ) -> List[SynthesizedSegment]:
        """
        Synthesize speech for all translation segments.

        Args:
            segments: List of translation segments
            voice_id: ElevenLabs voice ID
            output_dir: Directory to save audio files

        Returns:
            List of SynthesizedSegment with audio paths

        Raises:
            AIServiceError: If synthesis fails
        """
        if not segments:
            return []

        logger.info(f"Synthesizing {len(segments)} segments with voice {voice_id}")

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        synthesized_segments = []

        for seg in segments:
            output_path = output_dir / f"segment_{seg.id:04d}.mp3"

            audio_path, duration = self.synthesize_speech(
                text=seg.translated_text,
                voice_id=voice_id,
                output_path=str(output_path),
            )

            synthesized_segment = SynthesizedSegment(
                id=seg.id,
                start=seg.start,
                end=seg.end,
                text=seg.translated_text,
                audio_path=audio_path,
                actual_duration=duration,
            )
            synthesized_segments.append(synthesized_segment)

        logger.info(f"Synthesized {len(synthesized_segments)} audio segments")
        return synthesized_segments

    def get_available_voices(self) -> List[dict]:
        """
        Get list of available ElevenLabs voices.

        Returns:
            List of voice dictionaries with id, name, description

        Raises:
            AIServiceError: If API call fails
        """
        url = f"{self.elevenlabs_base_url}/voices"

        headers = {
            "Accept": "application/json",
            "xi-api-key": self.elevenlabs_api_key,
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)

            if response.status_code != 200:
                raise AIServiceError(
                    f"ElevenLabs API error: {response.status_code} - {response.text}"
                )

            data = response.json()
            voices = [
                {
                    "id": voice["voice_id"],
                    "name": voice["name"],
                    "description": voice.get("description", ""),
                    "labels": voice.get("labels", {}),
                }
                for voice in data.get("voices", [])
            ]

            logger.info(f"Retrieved {len(voices)} available voices")
            return voices

        except requests.RequestException as e:
            raise AIServiceError(f"Failed to get voices: {e}")
