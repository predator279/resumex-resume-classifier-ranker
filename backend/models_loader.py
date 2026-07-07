"""
models_loader.py — Singleton loader for BERT classifier and MiniLM sentence transformer.
Models are downloaded from HuggingFace once at container startup and held in memory.
"""

import logging
from functools import lru_cache
from typing import Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from sentence_transformers import SentenceTransformer
from huggingface_hub import hf_hub_download
import pickle
import os

logger = logging.getLogger(__name__)

CLASSIFIER_MODEL_NAME = "predator279/resume-classifier-model"
MINILM_MODEL_NAME = "all-MiniLM-L6-v2"


class ModelsState:
    """Holds all loaded models as a singleton."""

    def __init__(self):
        self.classifier_tokenizer = None
        self.classifier_model = None
        self.label_encoder = None
        self.sentence_transformer = None
        self.loaded: bool = False


_state = ModelsState()


def load_all_models() -> None:
    """
    Download and load all models into memory.
    Called once at FastAPI startup. Safe to call multiple times (idempotent).
    """
    global _state

    if _state.loaded:
        logger.info("Models already loaded — skipping.")
        return

    logger.info("=== Loading BERT resume classifier from HuggingFace ===")
    _state.classifier_tokenizer = AutoTokenizer.from_pretrained(CLASSIFIER_MODEL_NAME)
    _state.classifier_model = AutoModelForSequenceClassification.from_pretrained(
        CLASSIFIER_MODEL_NAME
    )
    _state.classifier_model.eval()

    # Load label encoder (pickle file stored alongside the model on HuggingFace)
    logger.info("Loading label encoder …")
    try:
        label_encoder_path = hf_hub_download(
            repo_id=CLASSIFIER_MODEL_NAME,
            filename="label_encoder.pkl",
        )
        with open(label_encoder_path, "rb") as f:
            _state.label_encoder = pickle.load(f)
        logger.info("Label encoder loaded from HuggingFace repo.")
    except Exception as e:
        logger.warning(
            "label_encoder.pkl not found in repo (%s). Using numeric labels.", e
        )
        _state.label_encoder = None

    logger.info("=== Loading MiniLM sentence transformer ===")
    _state.sentence_transformer = SentenceTransformer(MINILM_MODEL_NAME)

    _state.loaded = True
    logger.info("✅ All models loaded successfully.")


def get_classifier():
    """Return (tokenizer, model, label_encoder). Raises if not yet loaded."""
    if not _state.loaded:
        raise RuntimeError("Models not loaded. Call load_all_models() first.")
    return _state.classifier_tokenizer, _state.classifier_model, _state.label_encoder


def get_sentence_transformer() -> SentenceTransformer:
    """Return the MiniLM sentence transformer. Raises if not yet loaded."""
    if not _state.loaded:
        raise RuntimeError("Models not loaded. Call load_all_models() first.")
    return _state.sentence_transformer


def models_are_loaded() -> bool:
    return _state.loaded
