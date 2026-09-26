"""Optional local faster-whisper adapter.

The adapter requires a local model directory. It intentionally rejects model
names so running the pipeline cannot silently download a model.
"""

from __future__ import annotations

import logging
from pathlib import Path

from .alignment import ASRSegment


logger = logging.getLogger(__name__)


class FasterWhisperTranscriber:
    """Local faster-whisper transcription adapter.

    The adapter accepts only an existing model directory. This prevents a
    pipeline run from unexpectedly downloading a model or requiring network
    access.
    """

    def __init__(self, model_path: str | Path, device: str = "cpu", compute_type: str = "int8"):
        """Load a local faster-whisper model.

        Args:
            model_path: Existing CTranslate2 faster-whisper model directory.
            device: Inference device, normally ``cpu`` or ``cuda``.
            compute_type: CTranslate2 precision, such as ``int8`` or ``float16``.

        Raises:
            FileNotFoundError: If ``model_path`` does not exist.
            RuntimeError: If the ``faster_whisper`` package is unavailable.
        """
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Local faster-whisper model not found: {model_path}. "
                "Provide a pre-downloaded local model path; no model download is performed."
            )
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper is not installed. Install it or provide a hosted ASR adapter."
            ) from exc
        self._model = WhisperModel(str(model_path), device=device, compute_type=compute_type)
        logger.info(
            "Loaded faster-whisper model: path=%s device=%s compute_type=%s",
            model_path,
            device,
            compute_type,
        )

    def transcribe(self, audio_path: str | Path) -> list[ASRSegment]:
        """Transcribe one audio file into timestamped ASR segments.

        Args:
            audio_path: WAV or other audio file supported by faster-whisper.

        Returns:
            ASR segments with start time, end time, and transcript text.
        """
        logger.info("Transcribing audio: %s", audio_path)
        segments, _ = self._model.transcribe(str(audio_path), word_timestamps=False)
        results = [
            ASRSegment(float(segment.start), float(segment.end), segment.text)
            for segment in segments
        ]
        logger.info("Transcription complete: %s ASR segments from %s", len(results), audio_path)
        return results
