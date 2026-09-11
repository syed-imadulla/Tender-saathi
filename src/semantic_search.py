"""
Module: src/semantic_search.py
Purpose: Dense semantic embedding retrieval engine using sentence-transformers (all-MiniLM-L6-v2).

Features:
- Lightweight CPU-friendly model (all-MiniLM-L6-v2, ~90MB)
- Singleton model loader (loaded once in memory)
- Pre-computed, cached L2-normalized document embeddings for fast dot-product cosine similarity
- Graceful degradation: returns empty hit list if model/dependencies are unavailable
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
import os
import json
import logging
import numpy as np

from src.standards import StandardsDatabase

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data Model
# ---------------------------------------------------------------------------

@dataclass
class SemanticHit:
    standard_id: str
    standard_number: str
    full_title: str
    similarity_score: float               # Cosine similarity in [0, 1]
    raw_record: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_id": self.standard_id,
            "standard_number": self.standard_number,
            "full_title": self.full_title,
            "similarity_score": round(self.similarity_score, 4)
        }


# ---------------------------------------------------------------------------
# Singleton Model Holder
# ---------------------------------------------------------------------------

_MODEL_INSTANCE = None
_MODEL_LOAD_ATTEMPTED = False


def get_embedding_model(model_name: str = "all-MiniLM-L6-v2"):
    """Loads the sentence-transformer model once and caches in memory."""
    global _MODEL_INSTANCE, _MODEL_LOAD_ATTEMPTED
    if _MODEL_INSTANCE is not None:
        return _MODEL_INSTANCE

    if _MODEL_LOAD_ATTEMPTED:
        return None

    _MODEL_LOAD_ATTEMPTED = True
    try:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading SentenceTransformer model '{model_name}'...")
        _MODEL_INSTANCE = SentenceTransformer(model_name)
        return _MODEL_INSTANCE
    except Exception as e:
        logger.warning(f"Semantic model unavailable: {e}. Falling back to BM25/Deterministic.")
        return None


# ---------------------------------------------------------------------------
# Semantic Search Engine
# ---------------------------------------------------------------------------

class SemanticSearchEngine:
    """Semantic vector search operating over standard titles, scopes, and notes."""

    def __init__(
        self,
        db: Optional[StandardsDatabase] = None,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: str = "data/standards"
    ):
        self.db = db or StandardsDatabase()
        self.model_name = model_name
        # If cache_dir was left default, align with the DB directory
        if cache_dir == "data/standards" and self.db.db_path != "data/standards/standards.db":
            self.cache_dir = os.path.dirname(os.path.abspath(self.db.db_path))
        else:
            self.cache_dir = cache_dir

        self.model = get_embedding_model(model_name)
        self.is_available = self.model is not None

        self.doc_ids: List[str] = []
        self.doc_records: Dict[str, Dict[str, Any]] = {}
        self.doc_embeddings: Optional[np.ndarray] = None

        if self.is_available:
            self._build_or_load_index()

    def _build_or_load_index(self):
        """Loads embeddings from cache or incrementally computes and saves them."""
        import hashlib
        npy_path = os.path.join(self.cache_dir, "semantic_embeddings.npy")
        meta_path = os.path.join(self.cache_dir, "semantic_doc_ids.json")
        hash_path = os.path.join(self.cache_dir, "semantic_doc_hashes.json")

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standards")
            rows = [dict(r) for r in cursor.fetchall()]

        self.doc_records = {r["standard_id"]: r for r in rows}
        current_ids = [r["standard_id"] for r in rows]

        # Compute document representation strings and hashes
        doc_strings = {}
        current_hashes = {}
        for r in rows:
            sid = r["standard_id"]
            std_num = r.get("standard_number") or ""
            title = r.get("full_title") or ""
            scope = r.get("scope") or ""
            notes = r.get("notes") or ""
            tc = r.get("technical_committee") or ""
            doc_str = f"{std_num} : {title}. Scope: {scope}. Notes: {notes}. Committee: {tc}"
            doc_strings[sid] = doc_str
            current_hashes[sid] = hashlib.sha256(doc_str.encode('utf-8')).hexdigest()[:16]

        # Check if cache is fully up-to-date
        if (
            os.path.exists(npy_path) and
            os.path.exists(meta_path) and
            os.path.exists(hash_path)
        ):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    cached_ids = json.load(f)
                with open(hash_path, "r", encoding="utf-8") as f:
                    cached_hashes = json.load(f)

                if cached_ids == current_ids and cached_hashes == current_hashes:
                    self.doc_ids = cached_ids
                    self.doc_embeddings = np.load(npy_path)
                    return
            except Exception:
                pass

        # Perform incremental update
        self._compute_and_cache_incremental(rows, doc_strings, current_hashes, npy_path, meta_path, hash_path)

    def _compute_and_cache_incremental(
        self,
        rows: List[Dict[str, Any]],
        doc_strings: Dict[str, str],
        current_hashes: Dict[str, str],
        npy_path: str,
        meta_path: str,
        hash_path: str
    ):
        """Incrementally computes embeddings, reusing unchanged cached vectors."""
        if not rows or self.model is None:
            return

        cached_ids = []
        cached_hashes = {}
        cached_embeddings = None

        if os.path.exists(npy_path) and os.path.exists(meta_path) and os.path.exists(hash_path):
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    cached_ids = json.load(f)
                with open(hash_path, "r", encoding="utf-8") as f:
                    cached_hashes = json.load(f)
                cached_embeddings = np.load(npy_path)
            except Exception:
                cached_ids = []
                cached_hashes = {}
                cached_embeddings = None

        cached_id_to_idx = {cid: idx for idx, cid in enumerate(cached_ids)} if cached_embeddings is not None else {}

        new_doc_ids = [r["standard_id"] for r in rows]
        new_matrix = np.zeros((len(rows), 384), dtype=np.float32)  # all-MiniLM-L6-v2 dimension = 384

        to_encode_indices = []
        to_encode_texts = []

        for idx, sid in enumerate(new_doc_ids):
            # Check if unchanged standard exists in cache
            if (
                sid in cached_id_to_idx and
                sid in cached_hashes and
                cached_hashes[sid] == current_hashes.get(sid) and
                cached_embeddings is not None and
                cached_id_to_idx[sid] < len(cached_embeddings)
            ):
                # REUSE existing embedding
                new_matrix[idx] = cached_embeddings[cached_id_to_idx[sid]]
            else:
                # NEW or UPDATED standard
                to_encode_indices.append(idx)
                to_encode_texts.append(doc_strings.get(sid, ""))

        if to_encode_texts:
            logger.info(f"Incrementally encoding {len(to_encode_texts)} new/updated standards...")
            encoded = self.model.encode(to_encode_texts, convert_to_numpy=True, show_progress_bar=False)
            norms = np.linalg.norm(encoded, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            normalized_encoded = encoded / norms

            for pos, matrix_idx in enumerate(to_encode_indices):
                new_matrix[matrix_idx] = normalized_encoded[pos]

        self.doc_ids = new_doc_ids
        self.doc_embeddings = new_matrix

        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            np.save(npy_path, self.doc_embeddings)
            with open(meta_path, "w", encoding="utf-8") as f:
                json.dump(self.doc_ids, f)
            with open(hash_path, "w", encoding="utf-8") as f:
                json.dump(current_hashes, f)
        except Exception as e:
            logger.warning(f"Could not cache semantic embeddings: {e}")

    def search(self, query: str, top_k: int = 10) -> List[SemanticHit]:
        """Encodes query and returns top_k SemanticHit results by cosine similarity."""
        if not self.is_available or self.doc_embeddings is None or not query.strip():
            return []

        try:
            query_emb = self.model.encode([query.strip()], convert_to_numpy=True, show_progress_bar=False)[0]
            norm = np.linalg.norm(query_emb)
            if norm > 0:
                query_emb = query_emb / norm

            # Dot product with normalized document embeddings gives exact cosine similarities
            sims = np.dot(self.doc_embeddings, query_emb)
            # Clip negative similarities to 0
            sims = np.clip(sims, 0.0, 1.0)

            # Top k indices
            top_indices = np.argsort(sims)[::-1][:top_k]
            hits: List[SemanticHit] = []

            for idx in top_indices:
                score = float(sims[idx])
                if score <= 0.05:
                    continue
                doc_id = self.doc_ids[idx]
                rec = self.doc_records.get(doc_id, {})
                hits.append(SemanticHit(
                    standard_id=doc_id,
                    standard_number=rec.get("standard_number", ""),
                    full_title=rec.get("full_title", ""),
                    similarity_score=score,
                    raw_record=rec
                ))

            return hits
        except Exception as e:
            logger.warning(f"Semantic search failed for query '{query}': {e}")
            return []
