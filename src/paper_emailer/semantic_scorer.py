from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

from .models import SourceItem

_MODEL_NAME = "BAAI/bge-small-en-v1.5"

# Anchor sentences that define "relevant to sustainable / energy-efficient AI".
# Cosine similarity against these anchors is averaged to produce the final score.
_ANCHORS = [
    "reducing energy consumption of AI model training and inference",
    "carbon footprint and environmental impact of large language models",
    "green computing and sustainable artificial intelligence",
    "energy efficient deep learning and neural network optimization",
    "measuring power consumption and electricity use of machine learning workloads",
    "model compression quantization and distillation to reduce compute costs",
    "water usage and resource efficiency of AI datacenters",
    "responsible and environmentally sustainable machine learning practices",
]

_MIN_SIMILARITY = 0.75

_model = None
_anchor_embeddings = None


def semantic_score(item: SourceItem) -> float:
    """Return max cosine similarity of the item against sustainability anchors (0–1)."""
    model, anchor_embs = _get_model_and_anchors()
    text = f"{item.title}. {item.summary or ''}".strip()
    import numpy as np
    paper_emb = next(model.embed([text]))
    sims = anchor_embs @ paper_emb
    return float(sims.max())


def is_relevant(item: SourceItem, threshold: float = _MIN_SIMILARITY) -> bool:
    return semantic_score(item) >= threshold


def _get_model_and_anchors():
    global _model, _anchor_embeddings
    if _model is None:
        logging.info("loading embedding model %s", _MODEL_NAME)
        from fastembed import TextEmbedding
        import numpy as np
        _model = TextEmbedding(_MODEL_NAME)
        _anchor_embeddings = np.array(list(_model.embed(_ANCHORS)))
        logging.info("embedding model ready")
    return _model, _anchor_embeddings
