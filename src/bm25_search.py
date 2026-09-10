"""
Module: src/bm25_search.py
Purpose: True Okapi BM25 retrieval engine over the BIS Standards catalogue.

Implements standard Okapi BM25:
- Term frequency (TF)
- Inverse document frequency (IDF) with Robertson-Spärck Jones formulation
- Document length normalization (k1, b)
- Zero external dependencies (pure Python / standard library)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
import math
import re
from src.standards import StandardsDatabase


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class BM25Hit:
    standard_id: str
    standard_number: str
    full_title: str
    score: float                          # Raw BM25 score
    normalized_score: float               # Scaled to [0, 1]
    matched_terms: List[str] = field(default_factory=list)
    doc_length: int = 0
    raw_record: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "standard_id": self.standard_id,
            "standard_number": self.standard_number,
            "full_title": self.full_title,
            "score": round(self.score, 4),
            "normalized_score": round(self.normalized_score, 4),
            "matched_terms": self.matched_terms
        }


# ---------------------------------------------------------------------------
# BM25 Tokenizer
# ---------------------------------------------------------------------------

BM25_STOP_WORDS: Set[str] = {
    'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
    'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'were', 'will',
    'with', 'under', 'over', 'into', 'or', 'all', 'any', 'both', 'each', 'few',
    'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
    'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don',
    'should', 'now', 'etc', 'incl', 'including', 'work', 'works'
}


def tokenize(text: str) -> List[str]:
    """Tokenizes text into lowercase alphanumeric tokens, filtering stopwords."""
    if not text:
        return []
    tokens = [t.lower() for t in re.split(r'[^a-zA-Z0-9]+', text) if len(t) >= 2]
    return [t for t in tokens if t not in BM25_STOP_WORDS]


# ---------------------------------------------------------------------------
# Okapi BM25 Index
# ---------------------------------------------------------------------------

class BM25Index:
    """In-memory Okapi BM25 index built from SQLite standards records."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_ids: List[str] = []
        self.doc_records: Dict[str, Dict[str, Any]] = {}
        self.doc_lengths: Dict[str, int] = {}
        self.doc_term_freqs: Dict[str, Dict[str, int]] = {}
        self.doc_frequencies: Dict[str, int] = {}
        self.avg_doc_length: float = 0.0
        self.total_docs: int = 0
        self.idf_cache: Dict[str, float] = {}

    def build_from_db(self, db: StandardsDatabase):
        """Indexes all standards from the SQLite database."""
        self.doc_ids.clear()
        self.doc_records.clear()
        self.doc_lengths.clear()
        self.doc_term_freqs.clear()
        self.doc_frequencies.clear()
        self.idf_cache.clear()

        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM standards")
            rows = [dict(r) for r in cursor.fetchall()]

        self.total_docs = len(rows)
        total_len = 0

        for r in rows:
            doc_id = r["standard_id"]
            self.doc_ids.append(doc_id)
            self.doc_records[doc_id] = r

            # Combine indexed fields: standard_number (weighted by repetition), title, scope, notes, committee
            std_num = r.get("standard_number") or ""
            title = r.get("full_title") or ""
            scope = r.get("scope") or ""
            notes = r.get("notes") or ""
            tc = r.get("technical_committee") or ""

            # Repeat standard number & title to give them natural field weighting
            doc_content = f"{std_num} {std_num} {title} {title} {scope} {notes} {tc}"
            tokens = tokenize(doc_content)
            doc_len = len(tokens)
            self.doc_lengths[doc_id] = doc_len
            total_len += doc_len

            tf: Dict[str, int] = {}
            for t in tokens:
                tf[t] = tf.get(t, 0) + 1
            self.doc_term_freqs[doc_id] = tf

            # Document frequency
            for term in set(tokens):
                self.doc_frequencies[term] = self.doc_frequencies.get(term, 0) + 1

        self.avg_doc_length = (total_len / self.total_docs) if self.total_docs > 0 else 1.0

        # Precompute IDF for all indexed terms
        for term, df in self.doc_frequencies.items():
            self.idf_cache[term] = self._calculate_idf(df)

    def _calculate_idf(self, df: int) -> float:
        """Standard Robertson-Spärck Jones IDF with smoothing."""
        return math.log(1.0 + (self.total_docs - df + 0.5) / (df + 0.5))

    def get_idf(self, term: str) -> float:
        if term in self.idf_cache:
            return self.idf_cache[term]
        df = self.doc_frequencies.get(term, 0)
        idf = self._calculate_idf(df)
        self.idf_cache[term] = idf
        return idf

    def score(self, query: str) -> List[Tuple[str, float, List[str]]]:
        """
        Calculates Okapi BM25 score for query against all indexed documents.
        Returns list of tuples (doc_id, raw_bm25_score, matched_terms).
        """
        query_tokens = tokenize(query)
        if not query_tokens or self.total_docs == 0:
            return []

        scored_docs: List[Tuple[str, float, List[str]]] = []

        for doc_id in self.doc_ids:
            doc_len = self.doc_lengths.get(doc_id, 0)
            tf_dict = self.doc_term_freqs.get(doc_id, {})
            score = 0.0
            matched: List[str] = []

            for q_term in query_tokens:
                if q_term in tf_dict:
                    matched.append(q_term)
                    tf = tf_dict[q_term]
                    idf = self.get_idf(q_term)
                    # Okapi BM25 formula
                    numerator = tf * (self.k1 + 1.0)
                    denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                    score += idf * (numerator / denominator)

            if score > 0.0:
                scored_docs.append((doc_id, score, matched))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        return scored_docs


# ---------------------------------------------------------------------------
# BM25 Search Engine
# ---------------------------------------------------------------------------

class BM25SearchEngine:
    """High-level BM25 search interface with score normalization and candidate filtering."""

    def __init__(self, db: Optional[StandardsDatabase] = None, k1: float = 1.5, b: float = 0.75):
        self.db = db or StandardsDatabase()
        self.index = BM25Index(k1=k1, b=b)
        self.index.build_from_db(self.db)

    def search(self, query: str, top_k: int = 10) -> List[BM25Hit]:
        """Searches BM25 index and returns top_k BM25Hit objects."""
        raw_results = self.index.score(query)
        if not raw_results:
            return []

        max_score = raw_results[0][1] if raw_results else 1.0
        hits: List[BM25Hit] = []

        for doc_id, score, matched in raw_results[:top_k]:
            rec = self.index.doc_records.get(doc_id, {})
            # Min-max normalization against top score
            norm_score = (score / max_score) if max_score > 0 else 0.0
            hits.append(BM25Hit(
                standard_id=doc_id,
                standard_number=rec.get("standard_number", ""),
                full_title=rec.get("full_title", ""),
                score=score,
                normalized_score=min(1.0, norm_score),
                matched_terms=matched,
                doc_length=self.index.doc_lengths.get(doc_id, 0),
                raw_record=rec
            ))

        return hits
