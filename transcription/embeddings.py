"""Local sentence-transformers embedding generation."""

from __future__ import annotations

import logging
from collections.abc import Iterable

from .embedding_config import DEFAULT_EMBEDDING_CONFIG, EmbeddingConfig


logger = logging.getLogger(__name__)


class LocalEmbedder:
    """Generate and validate local sentence-transformers embeddings."""

    def __init__(self, config: EmbeddingConfig = DEFAULT_EMBEDDING_CONFIG):
        """Load the configured model without using a hosted embedding API."""
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is required for ingestion. Install the Stage 4 dependencies."
            ) from exc
        self.config = config
        self.model = SentenceTransformer(config.model_name)
        logger.info("Loaded embedding model: %s", config.model_name)

    def encode(self, texts: Iterable[str]) -> list[list[float]]:
        """Encode texts locally and return normalized vectors as Python lists.

        Args:
            texts: Transcript texts to encode.

        Returns:
            One vector per input text, each with the configured dimension.

        Raises:
            ValueError: If the model returns an unexpected vector dimension.
        """
        text_list = list(texts)
        if not text_list:
            return []
        vectors = self.model.encode(
            text_list,
            batch_size=self.config.batch_size,
            normalize_embeddings=self.config.normalize_embeddings,
            convert_to_numpy=True,
            show_progress_bar=True,
        )
        result = [vector.astype(float).tolist() for vector in vectors]
        dimensions = {len(vector) for vector in result}
        if dimensions != {self.config.dimension}:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.config.dimension}, got {sorted(dimensions)}"
            )
        logger.info("Generated %d embeddings with dimension %d", len(result), self.config.dimension)
        return result
