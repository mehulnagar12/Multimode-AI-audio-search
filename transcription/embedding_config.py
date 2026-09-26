"""Central configuration for local transcript embeddings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EmbeddingConfig:
    """Embedding model and vector-generation settings."""

    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    dimension: int = 384
    normalize_embeddings: bool = True
    batch_size: int = 32


DEFAULT_EMBEDDING_CONFIG = EmbeddingConfig()
"""Default lightweight retrieval configuration used by ingestion."""
