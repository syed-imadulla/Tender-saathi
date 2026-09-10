"""
Module: src/reranker.py
Purpose: Cross-Encoder second-stage reranking for TenderSaathi.

Uses:
  cross-encoder/ms-marco-MiniLM-L-6-v2

Architecture:
  First-stage retrieval (BM25 + Bi-Encoder + Deterministic) produces a candidate pool (~10 candidates).
  Cross-Encoder performs joint token-level cross-attention over (query, candidate_standard_text).
  Raw logits are normalized into [0, 1] using standard sigmoid:
    score = 1 / (1 + exp(-logit))

HONEST MODEL TRANSPARENCY:
  ms-marco-MiniLM-L-6-v2 is a general-domain English passage ranking model pre-trained on MS MARCO.
  It is NOT specifically fine-tuned on Bureau of Indian Standards (BIS) technical specifications.
  Its role is strictly to assess deep semantic cross-attention between requirement queries and
  standard titles/scopes to re-order the retrieved candidate pool.
"""

import os
import math
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass


_RERANKER_INSTANCE = None


def sigmoid(x: float) -> float:
    """Calculates standard logistic sigmoid: score = 1 / (1 + exp(-logit))."""
    try:
        # Clip to prevent overflow
        if x > 20.0:
            return 1.0
        elif x < -20.0:
            return 0.0
        return 1.0 / (1.0 + math.exp(-x))
    except Exception:
        return 0.5


@dataclass
class RerankedCandidate:
    standard_id: str
    standard_number: str
    original_score: float
    reranker_score: float
    final_score: float
    reason: str


class CrossEncoderReranker:
    """
    Second-stage neural reranker using a CrossEncoder.
    Lazily loads the model and caches the instance.
    Gracefully falls back to original scores if the model is absent or dependencies fail.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None
        self._is_loaded = False
        self._load_failed = False

    def load_model(self):
        """Loads the sentence_transformers CrossEncoder lazily."""
        if self._is_loaded or self._load_failed:
            return self._model

        try:
            from sentence_transformers import CrossEncoder
            self._model = CrossEncoder(self.model_name)
            self._is_loaded = True
        except Exception as e:
            self._load_failed = True
            self._model = None
        return self._model

    @property
    def is_available(self) -> bool:
        """Returns True if the underlying model is successfully loaded."""
        if not self._is_loaded and not self._load_failed:
            self.load_model()
        return self._is_loaded and self._model is not None

    def build_candidate_text(self, record: Dict[str, Any]) -> str:
        """
        Constructs rich passage representation from standard metadata:
        standard number, title, scope, technical committee, notes.
        """
        parts = []
        std_num = record.get("standard_number") or record.get("standard_id") or ""
        if std_num:
            parts.append(f"Standard: {std_num}")

        title = record.get("full_title") or record.get("title") or ""
        if title:
            parts.append(f"Title: {title}")

        scope = record.get("scope") or record.get("scope_summary") or ""
        if scope:
            parts.append(f"Scope: {scope}")

        comm = record.get("technical_committee") or ""
        if comm:
            parts.append(f"Committee: {comm}")

        notes = record.get("notes") or ""
        if notes:
            parts.append(f"Notes: {notes}")

        return " | ".join(parts)

    def score_pairs(self, query: str, candidate_texts: List[str]) -> List[float]:
        """
        Computes normalized sigmoid scores [0, 1] for each (query, candidate_text) pair.
        """
        if not candidate_texts:
            return []

        model = self.load_model()
        if model is None:
            # Neutral fallback
            return [0.5] * len(candidate_texts)

        pairs = [[query, text] for text in candidate_texts]
        try:
            raw_logits = model.predict(pairs)
            # raw_logits can be a numpy array or list
            scores = []
            for logit in raw_logits:
                val = float(logit)
                scores.append(round(sigmoid(val), 4))
            return scores
        except Exception:
            return [0.5] * len(candidate_texts)

    def rerank_candidates(
        self,
        query: str,
        candidates: List[Any],
        w_rerank: float = 0.25,
        top_k: int = 5
    ) -> List[Any]:
        """
        Reranks candidates by combining initial hybrid score with CrossEncoder score.
        Preserves exact authoritative standard citations (score >= 0.98 or explicitly pinned).
        """
        if not candidates:
            return []

        # If model is unavailable or only 1 candidate, return as-is
        if not self.is_available or len(candidates) <= 1:
            for c in candidates:
                if getattr(c, "reranker_score", None) is None:
                    setattr(c, "reranker_score", getattr(c, "hybrid_score", getattr(c, "relevance_score", 0.5)))
                if getattr(c, "final_score", None) is None:
                    setattr(c, "final_score", getattr(c, "hybrid_score", getattr(c, "relevance_score", 0.5)))
            return candidates[:top_k]

        candidate_texts = []
        for c in candidates:
            rec = getattr(c, "raw_record", None)
            if rec is None:
                # Fallback if SearchResult or dict
                rec = {
                    "standard_number": getattr(c, "standard_number", ""),
                    "full_title": getattr(c, "full_title", ""),
                    "scope": getattr(c, "scope_summary", getattr(c, "scope", ""))
                }
            candidate_texts.append(self.build_candidate_text(rec))

        rerank_scores = self.score_pairs(query, candidate_texts)

        for i, c in enumerate(candidates):
            r_score = rerank_scores[i]
            orig_score = getattr(c, "hybrid_score", getattr(c, "relevance_score", 0.5))

            # Exact match safety: preserve exact cited standard priority
            reasons = getattr(c, "reasons", [])
            if isinstance(reasons, str):
                reasons = [reasons]
            is_exact = any("Authoritative replacement" in r or "Standard number match on identifier" in r for r in reasons)
            if is_exact or orig_score >= 0.98:
                final = orig_score
            else:
                final = round((1.0 - w_rerank) * orig_score + w_rerank * r_score, 4)

            setattr(c, "reranker_score", r_score)
            setattr(c, "final_score", final)

        # Sort by final_score descending
        candidates.sort(key=lambda x: getattr(x, "final_score", 0.0), reverse=True)
        return candidates[:top_k]


def get_reranker_instance(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2") -> CrossEncoderReranker:
    """Returns singleton instance of CrossEncoderReranker."""
    global _RERANKER_INSTANCE
    if _RERANKER_INSTANCE is None:
        _RERANKER_INSTANCE = CrossEncoderReranker(model_name=model_name)
    return _RERANKER_INSTANCE
