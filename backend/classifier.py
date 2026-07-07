"""
classifier.py — /classify endpoint logic.

Runs a BERT forward pass on the extracted resume text and returns the top-5
predicted job categories with confidence scores.
"""

import logging
from typing import List, Dict, Any

import torch
import torch.nn.functional as F

from .models_loader import get_classifier
from .file_parser import extract_text, clean_text

logger = logging.getLogger(__name__)

# Maximum tokens the BERT model accepts
MAX_TOKENS = 512


def classify_resume(filename: str, file_bytes: bytes) -> Dict[str, Any]:
    """
    Classify a resume file and return top-5 categories.

    Args:
        filename:   Original filename (for extension detection + response).
        file_bytes: Raw file bytes.

    Returns:
        Dict with keys: filename, preview, top5
    """
    tokenizer, model, label_encoder = get_classifier()

    # 1. Extract & clean text
    raw_text = extract_text(filename, file_bytes)
    text = clean_text(raw_text)

    if not text:
        return {
            "filename": filename,
            "preview": "",
            "top5": [],
            "error": "Could not extract text from file.",
        }

    # 2. Tokenize (truncate to MAX_TOKENS)
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=MAX_TOKENS,
        padding=True,
    )

    # 3. Forward pass (no gradient needed)
    with torch.no_grad():
        logits = model(**inputs).logits

    # 4. Softmax → probabilities
    probs = F.softmax(logits, dim=-1).squeeze()  # shape: (num_labels,)

    # 5. Top-5 indices
    top5_indices = torch.topk(probs, k=min(5, probs.shape[0])).indices.tolist()
    top5_scores = probs[top5_indices].tolist()

    # 6. Map indices → category labels
    top5 = []
    for rank, (idx, score) in enumerate(zip(top5_indices, top5_scores), start=1):
        if label_encoder is not None:
            try:
                category = label_encoder.inverse_transform([idx])[0]
            except Exception:
                category = str(idx)
        else:
            category = f"Category {idx}"

        top5.append(
            {
                "rank": rank,
                "category": category,
                "score": round(float(score), 4),
            }
        )

    # 7. Build preview (first 200 chars of cleaned text)
    preview = text[:200].replace("\n", " ").strip()

    logger.info(
        "Classified '%s' → top category: %s (%.3f)",
        filename,
        top5[0]["category"] if top5 else "N/A",
        top5[0]["score"] if top5 else 0.0,
    )

    return {
        "filename": filename,
        "preview": preview,
        "top5": top5,
    }
