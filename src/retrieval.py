"""
Module: src/retrieval.py
Purpose: Hybrid retrieval engine combining BM25 lexical, semantic vector embeddings,
and deterministic rule-based retrieval with multi-attribute component fusion.

Ablation modes supported:
- 'hybrid' (default: BM25 + Semantic + Deterministic fusion)
- 'deterministic' (rule-based / lexical heuristic alone)
- 'bm25' (Okapi BM25 alone)
- 'semantic' (sentence-transformers embeddings alone)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
import os
import re

from src.standards import StandardsDatabase
from src.search import StandardsSearchEngine, SearchResult
from src.bm25_search import BM25SearchEngine, BM25Hit
from src.semantic_search import SemanticSearchEngine, SemanticHit
from src.decompose import RequirementComponent, decompose_requirement
from src.reranker import CrossEncoderReranker, get_reranker_instance


@dataclass
class HybridCandidate:
    """Internal candidate representation tracking sub-scores and attribution."""
    standard_id: str
    standard_number: str
    full_title: str
    status: str
    raw_record: Dict[str, Any]
    det_score: float = 0.0
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    hybrid_score: float = 0.0
    reranker_score: Optional[float] = None
    final_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    matched_components: List[str] = field(default_factory=list)


class HybridRetrievalEngine:
    """
    Coordinates multi-modal hybrid retrieval across:
    1. Okapi BM25
    2. Dense semantic embeddings (all-MiniLM-L6-v2)
    3. Deterministic / domain guardrails
    4. Optional Cross-Encoder neural reranking (cross-encoder/ms-marco-MiniLM-L-6-v2)
    """

    def __init__(
        self,
        db: Optional[StandardsDatabase] = None,
        w_bm25: float = 0.40,
        w_semantic: float = 0.35,
        w_deterministic: float = 0.25,
        w_rerank: float = 0.25,
        default_mode: str = "hybrid",
        reranker: Optional[CrossEncoderReranker] = None
    ):
        self.db = db or StandardsDatabase()
        self.w_bm25 = w_bm25
        self.w_semantic = w_semantic
        self.w_deterministic = w_deterministic
        self.w_rerank = w_rerank
        self.default_mode = default_mode
        self.reranker = reranker or get_reranker_instance()

        # Initialize component engines
        self.det_engine = StandardsSearchEngine(self.db)
        self.bm25_engine = BM25SearchEngine(self.db)
        self.semantic_engine = SemanticSearchEngine(self.db)

    def search(
        self,
        query: str,
        top_k: int = 5,
        components: Optional[List[RequirementComponent]] = None,
        mode: Optional[str] = None
    ) -> List[SearchResult]:
        """
        Executes search under the specified retrieval mode:
        'hybrid', 'hybrid+rerank', 'deterministic', 'bm25', or 'semantic'.
        """
        query_clean = query.strip()
        if not query_clean:
            return []

        active_mode = mode or self.default_mode

        # Resolve components if not provided
        if components is None:
            decomp = decompose_requirement(query_clean)
            components = decomp.components

        # 1. Deterministic search results
        det_results = self.det_engine.search(query_clean, top_k=top_k * 2, components=components)

        # Mode: purely deterministic
        if active_mode == "deterministic":
            return det_results[:top_k]

        # 2. BM25 search results (primary query + components)
        bm25_hits = self.bm25_engine.search(query_clean, top_k=top_k * 2)

        # Mode: purely BM25
        if active_mode == "bm25":
            return self._convert_bm25_to_search_results(bm25_hits, top_k=top_k)

        # 3. Semantic search results (primary query)
        sem_hits = self.semantic_engine.search(query_clean, top_k=top_k * 2)

        # Mode: purely semantic
        if active_mode == "semantic":
            return self._convert_semantic_to_search_results(sem_hits, top_k=top_k)

        # 4. Hybrid / Hybrid+Rerank Mode: Candidate Union, Score Fusion, and optional Reranking
        return self._fuse_hybrid_results(
            query=query_clean,
            components=components or [],
            det_results=det_results,
            bm25_hits=bm25_hits,
            sem_hits=sem_hits,
            top_k=top_k,
            mode=active_mode
        )

    def _fuse_hybrid_results(
        self,
        query: str,
        components: List[RequirementComponent],
        det_results: List[SearchResult],
        bm25_hits: List[BM25Hit],
        sem_hits: List[SemanticHit],
        top_k: int,
        mode: str = "hybrid"
    ) -> List[SearchResult]:
        """Merges candidates from all 3 engines with multi-component fusion."""
        candidate_map: Dict[str, HybridCandidate] = {}

        # Component searches to enrich candidate pool for compound requirements
        comp_bm25_hits: Dict[str, List[BM25Hit]] = {}
        for c in components:
            if c.component_type in ["control", "electrical", "product", "equipment", "material"]:
                comp_hits = self.bm25_engine.search(c.text, top_k=3)
                comp_bm25_hits[c.text] = comp_hits

        # Collect candidate pool from Deterministic
        for r in det_results:
            std_id = r.standard_id
            rec = self.db.get_standard(std_id) or {}
            candidate_map[std_id] = HybridCandidate(
                standard_id=std_id,
                standard_number=r.standard_number,
                full_title=r.full_title,
                status=r.status,
                raw_record=rec,
                det_score=r.relevance_score,
                reasons=[f"Deterministic: {r.relevance_reason}"]
            )

        # Collect / merge from BM25
        for h in bm25_hits:
            std_id = h.standard_id
            matched_terms_str = ", ".join(h.matched_terms[:4])
            bm_reason = f"BM25 match (norm: {h.normalized_score:.2f}, terms: [{matched_terms_str}])"
            if std_id in candidate_map:
                cand = candidate_map[std_id]
                cand.bm25_score = h.normalized_score
                cand.reasons.append(bm_reason)
            else:
                rec = h.raw_record or self.db.get_standard(std_id) or {}
                candidate_map[std_id] = HybridCandidate(
                    standard_id=std_id,
                    standard_number=h.standard_number,
                    full_title=h.full_title,
                    status=rec.get("status", "Active"),
                    raw_record=rec,
                    bm25_score=h.normalized_score,
                    reasons=[bm_reason]
                )

        # Collect / merge from Component BM25
        for comp_text, hits in comp_bm25_hits.items():
            for h in hits:
                std_id = h.standard_id
                if std_id in candidate_map:
                    cand = candidate_map[std_id]
                    if cand.bm25_score < h.normalized_score:
                        cand.bm25_score = max(cand.bm25_score, h.normalized_score * 0.90)
                    cand.matched_components.append(comp_text)
                    cand.reasons.append(f"Component BM25 matched '{comp_text}'")

        # Collect / merge from Semantic
        for s in sem_hits:
            std_id = s.standard_id
            sem_reason = f"Semantic similarity: {s.similarity_score:.3f}"
            if std_id in candidate_map:
                cand = candidate_map[std_id]
                cand.semantic_score = s.similarity_score
                cand.reasons.append(sem_reason)
            else:
                rec = s.raw_record or self.db.get_standard(std_id) or {}
                candidate_map[std_id] = HybridCandidate(
                    standard_id=std_id,
                    standard_number=s.standard_number,
                    full_title=s.full_title,
                    status=rec.get("status", "Active"),
                    raw_record=rec,
                    semantic_score=s.similarity_score,
                    reasons=[sem_reason]
                )

        # Domain constraint check: identify medium voltage / industrial / control requirements
        has_industrial_or_mv = any(
            c.extracted_attributes.get("level") == "medium_or_high_voltage" or
            c.extracted_attributes.get("is_process") or
            c.component_type == "control"
            for c in components
        )

        # Compute fused hybrid score
        scored_candidates: List[HybridCandidate] = []
        for cand in candidate_map.values():
            t_low = (cand.full_title or "").lower()
            s_low = (cand.raw_record.get("scope") or "").lower()

            # Domain conflict guardrail: filter agricultural irrigation pump codes for industrial/MV requirements
            is_agri = "agriculture" in t_low or "agricultural" in t_low
            if is_agri and has_industrial_or_mv:
                continue

            # Check if this standard was an exact standard number or authoritative supersedence
            is_authoritative_match = False
            for r in cand.reasons:
                if "Authoritative replacement" in r or "Standard number match on identifier" in r:
                    is_authoritative_match = True
                    break

            if is_authoritative_match:
                cand.hybrid_score = cand.det_score or 0.98
            else:
                # Weighted hybrid formula
                # Normalize component contributions
                w_total = self.w_bm25 + self.w_semantic + self.w_deterministic
                base_hybrid = (
                    (self.w_bm25 * cand.bm25_score) +
                    (self.w_semantic * cand.semantic_score) +
                    (self.w_deterministic * cand.det_score)
                ) / (w_total if w_total > 0 else 1.0)

                # Component coherence boost
                unique_comp_matches = len(set(cand.matched_components))
                if unique_comp_matches >= 2:
                    base_hybrid = min(0.98, base_hybrid * 1.15)

                cand.hybrid_score = round(min(0.98, base_hybrid), 3)

            # Keep candidate if score exceeds minimum threshold
            if cand.hybrid_score >= 0.20 or cand.det_score >= 0.35:
                cand.final_score = cand.hybrid_score
                scored_candidates.append(cand)

        # Sort by initial hybrid score descending
        scored_candidates.sort(
            key=lambda x: (
                x.hybrid_score,
                len(x.matched_components),
                len(x.reasons)
            ),
            reverse=True
        )

        # Stage 2: Cross-Encoder Neural Reranking if active mode is hybrid+rerank
        if mode == "hybrid+rerank" and self.reranker and scored_candidates:
            pool_size = max(top_k * 2, 10)
            candidate_pool = scored_candidates[:pool_size]
            candidate_texts = [
                self.reranker.build_candidate_text(cand.raw_record)
                for cand in candidate_pool
            ]
            rerank_scores = self.reranker.score_pairs(query, candidate_texts)

            for idx, cand in enumerate(candidate_pool):
                r_score = rerank_scores[idx]
                cand.reranker_score = r_score
                cand.reasons.append(f"CrossEncoder: {r_score:.3f}")

                # Exact match safety: preserve exact cited standard priority
                is_authoritative = any(
                    "Authoritative replacement" in r or "Standard number match on identifier" in r
                    for r in cand.reasons
                )
                if is_authoritative or cand.hybrid_score >= 0.98:
                    cand.final_score = cand.hybrid_score
                else:
                    cand.final_score = round(
                        (1.0 - self.w_rerank) * cand.hybrid_score + self.w_rerank * r_score,
                        4
                    )

            # Re-sort candidates by final_score descending
            scored_candidates.sort(
                key=lambda x: (
                    x.final_score,
                    len(x.matched_components),
                    len(x.reasons)
                ),
                reverse=True
            )

        # Convert to SearchResult objects
        search_results: List[SearchResult] = []
        for cand in scored_candidates[:top_k]:
            rec = cand.raw_record
            formatted = self.det_engine._format_result(
                row_dict=rec,
                score=cand.final_score,
                reason="; ".join(cand.reasons)
            )
            formatted.bm25_score = cand.bm25_score
            formatted.semantic_score = cand.semantic_score
            formatted.deterministic_score = cand.det_score
            formatted.reranker_score = cand.reranker_score
            formatted.final_score = cand.final_score
            search_results.append(formatted)

        return search_results

    def _convert_bm25_to_search_results(self, hits: List[BM25Hit], top_k: int) -> List[SearchResult]:
        results = []
        for h in hits[:top_k]:
            rec = h.raw_record or self.db.get_standard(h.standard_id) or {}
            reason = f"BM25 lexical match (score: {h.score:.2f}, matched: {', '.join(h.matched_terms[:3])})"
            res = self.det_engine._format_result(rec, score=h.normalized_score, reason=reason)
            res.bm25_score = h.normalized_score
            res.final_score = h.normalized_score
            results.append(res)
        return results

    def _convert_semantic_to_search_results(self, hits: List[SemanticHit], top_k: int) -> List[SearchResult]:
        results = []
        for s in hits[:top_k]:
            rec = s.raw_record or self.db.get_standard(s.standard_id) or {}
            reason = f"Semantic embedding similarity: {s.similarity_score:.4f}"
            res = self.det_engine._format_result(rec, score=s.similarity_score, reason=reason)
            res.semantic_score = s.similarity_score
            res.final_score = s.similarity_score
            results.append(res)
        return results

