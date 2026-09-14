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
import logging

logger = logging.getLogger("tendersaathi.retrieval")

from src.standards import StandardsDatabase
from src.catalogue.provider import get_default_catalogue_provider, assert_authoritative_bis_catalogue
from src.search import StandardsSearchEngine, SearchResult
from src.bm25_search import BM25SearchEngine, BM25Hit
from src.semantic_search import SemanticSearchEngine, SemanticHit
from src.decompose import RequirementComponent, decompose_requirement
from src.reranker import CrossEncoderReranker, get_reranker_instance
from src.terminology import TechnicalTerminologyNormalizer

# Production Sizing Constants (Empirically Selected)
DEFAULT_FIRST_STAGE_K = 150
DEFAULT_RERANK_POOL_SIZE = 30
DEFAULT_TOP_K = 5


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
    det_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
    sem_rank: Optional[int] = None
    hybrid_score: float = 0.0
    reranker_score: Optional[float] = None
    final_score: float = 0.0
    reasons: List[str] = field(default_factory=list)
    matched_components: List[str] = field(default_factory=list)


class HybridRetrievalEngine:
    """
    Coordinates multi-modal hybrid retrieval across:
    1. Okapi BM25 with deterministic technical terminology expansion
    2. Dense semantic embeddings (all-MiniLM-L6-v2)
    3. Deterministic / domain guardrails & exact citation resolution
    4. Cross-Encoder neural reranking (cross-encoder/ms-marco-MiniLM-L-6-v2)
    5. Reciprocal Rank Fusion (RRF) production fusion
    """

    def __init__(
        self,
        db: Optional[StandardsDatabase] = None,
        w_bm25: float = 0.40,
        w_semantic: float = 0.35,
        w_deterministic: float = 0.25,
        w_rerank: float = 0.25,
        default_mode: str = "hybrid",
        reranker: Optional[CrossEncoderReranker] = None,
        fusion_strategy: str = "rrf",
        rrf_k: int = 60
    ):
        self.db = db or get_default_catalogue_provider()
        # Verify and assert authoritative BIS catalogue
        assert_authoritative_bis_catalogue(self.db)

        self.w_bm25 = w_bm25
        self.w_semantic = w_semantic
        self.w_deterministic = w_deterministic
        self.w_rerank = w_rerank
        self.default_mode = default_mode
        self.reranker = reranker or get_reranker_instance()
        self.fusion_strategy = fusion_strategy
        self.rrf_k = rrf_k

        # Initialize component engines
        from src.citation_resolver import ExactCitationResolver
        self.citation_resolver = ExactCitationResolver(self.db)
        self.det_engine = StandardsSearchEngine(self.db)
        self.bm25_engine = BM25SearchEngine(self.db)
        self.semantic_engine = SemanticSearchEngine(self.db)
        self.terminology_normalizer = TechnicalTerminologyNormalizer()

    def search(
        self,
        query: str,
        top_k: int = DEFAULT_TOP_K,
        components: Optional[List[RequirementComponent]] = None,
        mode: Optional[str] = None,
        fusion_strategy: Optional[str] = None,
        first_stage_k: Optional[int] = None,
        rerank_pool_size: Optional[int] = None
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

        # Expand first-stage recall pool to ensure candidates are not dropped before fusion
        stage_k = first_stage_k or DEFAULT_FIRST_STAGE_K

        # 1. Deterministic search results
        det_results = self.det_engine.search(query_clean, top_k=stage_k, components=components)

        # Dual-path architecture: Resolve explicit citations first
        resolved_citations = self.citation_resolver.resolve_from_text(query_clean)
        exact_citation_results: List[SearchResult] = []
        resolved_std_ids = set()
        for rc in resolved_citations:
            resolved_std_ids.add(rc.canonical_id)
            status_val = rc.status or "UNKNOWN"
            if status_val.lower() == "active":
                version_role = "CURRENT_ACTIVE"
            elif "superseded" in status_val.lower():
                version_role = "REPLACED_OR_SUPERSEDED"
            elif "withdrawn" in status_val.lower():
                version_role = "WITHDRAWN"
            else:
                version_role = "CURRENT_ACTIVE"

            exact_citation_results.append(SearchResult(
                standard_id=rc.canonical_id,
                standard_number=rc.standard_number,
                year=rc.year,
                full_title=rc.title,
                status=status_val,
                version_role=version_role,
                relevance_score=1.0,
                relevance_reason=f"Authoritative BIS Citation ({rc.precedence}): {rc.raw_citation}",
                scope_summary=rc.raw_record.get("scope") or "",
                source_provenance=f"{rc.source} ({rc.source_url or 'authoritative_catalogue'})",
                deterministic_score=1.0,
                final_score=1.0
            ))

        # Mode: purely deterministic
        if active_mode == "deterministic":
            merged = exact_citation_results + [r for r in det_results if r.standard_id not in resolved_std_ids]
            return merged[:top_k]

        # Expand query deterministically to bridge technical terminology mismatch
        expanded_query = self.terminology_normalizer.build_expanded_query(query_clean)

        # 2. BM25 search results (expanded query)
        bm25_hits = self.bm25_engine.search(expanded_query, top_k=stage_k)

        # Mode: purely BM25
        if active_mode == "bm25":
            bm25_converted = self._convert_bm25_to_search_results(bm25_hits, top_k=top_k)
            merged = exact_citation_results + [r for r in bm25_converted if r.standard_id not in resolved_std_ids]
            return merged[:top_k]

        # 3. Semantic search results (expanded query)
        sem_hits = self.semantic_engine.search(expanded_query, top_k=stage_k)

        # Mode: purely semantic
        if active_mode == "semantic":
            sem_converted = self._convert_semantic_to_search_results(sem_hits, top_k=top_k)
            merged = exact_citation_results + [r for r in sem_converted if r.standard_id not in resolved_std_ids]
            return merged[:top_k]

        # 4. Hybrid / Hybrid+Rerank Mode: Candidate Union, Score Fusion, and optional Reranking
        strategy = fusion_strategy or self.fusion_strategy
        hybrid_res = self._fuse_hybrid_results(
            query=query_clean,
            components=components or [],
            det_results=det_results,
            bm25_hits=bm25_hits,
            sem_hits=sem_hits,
            top_k=top_k,
            mode=active_mode,
            fusion_strategy=strategy,
            rerank_pool_size=rerank_pool_size
        )
        if exact_citation_results:
            merged = exact_citation_results + [r for r in hybrid_res if r.standard_id not in resolved_std_ids]
            return merged[:top_k]
        return hybrid_res

    def _fuse_hybrid_results(
        self,
        query: str,
        components: List[RequirementComponent],
        det_results: List[SearchResult],
        bm25_hits: List[BM25Hit],
        sem_hits: List[SemanticHit],
        top_k: int,
        mode: str = "hybrid",
        fusion_strategy: str = "rrf",
        rerank_pool_size: Optional[int] = None
    ) -> List[SearchResult]:
        """Merges candidates from all 3 engines with multi-component fusion."""
        candidate_map: Dict[str, HybridCandidate] = {}

        # Component searches to enrich candidate pool for compound requirements
        comp_bm25_hits: Dict[str, List[BM25Hit]] = {}
        for c in components:
            if c.component_type in ["control", "electrical", "product", "equipment", "material"]:
                comp_hits = self.bm25_engine.search(c.text, top_k=3)
                comp_bm25_hits[c.text] = comp_hits

        # Collect candidate pool from Deterministic with 1-based rank
        for idx, r in enumerate(det_results):
            std_id = r.standard_id
            rec = self.db.get_standard(std_id) or {}
            candidate_map[std_id] = HybridCandidate(
                standard_id=std_id,
                standard_number=r.standard_number,
                full_title=r.full_title,
                status=r.status,
                raw_record=rec,
                det_score=r.relevance_score,
                det_rank=idx + 1,
                reasons=[f"Deterministic: {r.relevance_reason}"]
            )

        # Collect / merge from BM25 with 1-based rank
        for idx, h in enumerate(bm25_hits):
            std_id = h.standard_id
            matched_terms_str = ", ".join(h.matched_terms[:4])
            bm_reason = f"BM25 match (norm: {h.normalized_score:.2f}, terms: [{matched_terms_str}])"
            if std_id in candidate_map:
                cand = candidate_map[std_id]
                cand.bm25_score = h.normalized_score
                cand.bm25_rank = idx + 1
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
                    bm25_rank=idx + 1,
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

        # Collect / merge from Semantic with 1-based rank
        for idx, s in enumerate(sem_hits):
            std_id = s.standard_id
            sem_reason = f"Semantic similarity: {s.similarity_score:.3f}"
            if std_id in candidate_map:
                cand = candidate_map[std_id]
                cand.semantic_score = s.similarity_score
                cand.sem_rank = idx + 1
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
                    sem_rank=idx + 1,
                    reasons=[sem_reason]
                )

        # Domain constraint check: identify medium voltage / industrial / control requirements
        has_industrial_or_mv = any(
            c.extracted_attributes.get("level") == "medium_or_high_voltage" or
            c.extracted_attributes.get("is_process") or
            c.component_type == "control"
            for c in components
        )

        # Compute fused hybrid score based on selected fusion_strategy
        scored_candidates: List[HybridCandidate] = []
        for cand in candidate_map.values():
            t_low = (cand.full_title or "").lower()

            # Domain conflict guardrail: filter agricultural irrigation pump codes for industrial/MV requirements
            is_agri = "agriculture" in t_low or "agricultural" in t_low
            if is_agri and has_industrial_or_mv:
                continue

            # Check if this standard was an exact standard number or authoritative supersedence
            is_authoritative_match = False
            for r in cand.reasons:
                if "Authoritative replacement" in r or "Standard number match on identifier" in r or "Authoritative BIS Citation" in r:
                    is_authoritative_match = True
                    break

            if is_authoritative_match:
                cand.hybrid_score = cand.det_score or 0.98
            elif fusion_strategy == "rrf":
                # Strategy B: Reciprocal Rank Fusion
                k_rrf = self.rrf_k or 60
                rrf_score = 0.0
                if cand.det_rank is not None:
                    rrf_score += 1.0 / (k_rrf + cand.det_rank)
                if cand.bm25_rank is not None:
                    rrf_score += 1.0 / (k_rrf + cand.bm25_rank)
                if cand.sem_rank is not None:
                    rrf_score += 1.0 / (k_rrf + cand.sem_rank)

                # Component coherence bonus
                unique_comp_matches = len(set(cand.matched_components))
                if unique_comp_matches >= 2:
                    rrf_score *= 1.10

                MAX_RRF = 3.0 / (k_rrf + 1)
                normalized_rrf = min(0.98, rrf_score / MAX_RRF)
                cand.hybrid_score = round(normalized_rrf, 4)
            elif fusion_strategy == "candidate_preserving":
                # Strategy C: Candidate-Preserving Union / CombMAX with consensus boost
                # 1. Base CombMAX score across retrievers
                comb_max = max(cand.bm25_score, cand.semantic_score, cand.det_score)

                # 2. Rank preservation anchor: reward high ranks from ANY engine
                retriever_ranks = [r for r in [cand.det_rank, cand.bm25_rank, cand.sem_rank] if r is not None]
                best_rank = min(retriever_ranks) if retriever_ranks else 100
                rank_anchor = 1.0 / (1.0 + 0.02 * (best_rank - 1))

                # 3. Consensus boost across multiple retrievers
                num_engines = len(retriever_ranks)
                consensus_boost = 1.0 + (0.10 * (num_engines - 1))

                # 4. Component coherence boost
                unique_comp_matches = len(set(cand.matched_components))
                comp_boost = 1.10 if unique_comp_matches >= 2 else 1.0

                fused_score = comb_max * rank_anchor * consensus_boost * comp_boost
                cand.hybrid_score = round(min(0.98, fused_score), 4)
            else:
                # Strategy A: Baseline Weighted Fusion
                w_total = self.w_bm25 + self.w_semantic + self.w_deterministic
                base_hybrid = (
                    (self.w_bm25 * cand.bm25_score) +
                    (self.w_semantic * cand.semantic_score) +
                    (self.w_deterministic * cand.det_score)
                ) / (w_total if w_total > 0 else 1.0)

                unique_comp_matches = len(set(cand.matched_components))
                if unique_comp_matches >= 2:
                    base_hybrid = min(0.98, base_hybrid * 1.15)

                cand.hybrid_score = round(min(0.98, base_hybrid), 4)

            # Assign preliminary final_score equal to hybrid_score
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
            # Empirically calibrated candidate pool size (30) for cross-encoder reranking
            pool_size = rerank_pool_size or DEFAULT_RERANK_POOL_SIZE
            candidate_pool = scored_candidates[:pool_size]
            remaining_candidates = scored_candidates[pool_size:]

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
                    "Authoritative replacement" in r or "Standard number match on identifier" in r or "Authoritative BIS Citation" in r
                    for r in cand.reasons
                )
                if is_authoritative or cand.hybrid_score >= 0.98:
                    cand.final_score = cand.hybrid_score
                else:
                    cand.final_score = round(
                        (1.0 - self.w_rerank) * cand.hybrid_score + self.w_rerank * r_score,
                        4
                    )

            # Re-sort candidate_pool by final_score descending
            candidate_pool.sort(
                key=lambda x: (
                    x.final_score,
                    len(x.matched_components),
                    len(x.reasons)
                ),
                reverse=True
            )
            # Reassemble scored_candidates: reranked pool first, remaining after
            scored_candidates = candidate_pool + remaining_candidates

        # General Environmental & Domain Scoping:
        # Specialized marine, aircraft, solar PV, and PCB standards should not pollute terrestrial procurement
        q_low = query.lower()
        is_marine_q = any(w in q_low for w in ['ship', 'marine', 'vessel', 'boat', 'naval', 'dock', 'harbour', 'shipyard', 'offshore'])
        is_aero_q = any(w in q_low for w in ['aircraft', 'aviation', 'aerospace', 'aeroplane', 'avionics'])
        is_solar_q = any(w in q_low for w in ['solar', 'photovoltaic', 'pv '])
        is_pcb_q = any(w in q_low for w in ['printed circuit', 'pcb', 'printed wiring board'])

        is_cable_q = bool(re.search(r'\b(?:cables?|power\s+cable|electric\s+cable|underground\s+cable)\b', q_low))
        is_underground_q = bool(re.search(r'\b(?:underground|buried)\b', q_low))

        filtered_candidates = []
        for cand in scored_candidates:
            t_low = (cand.full_title or "").lower() + " " + (cand.raw_record.get("scope") or "").lower()
            if not is_marine_q and any(w in t_low for w in ['shipbuilding', 'in ships', 'for ships', 'shipboard equipment', 'marine purposes', 'for marine']):
                continue
            if not is_aero_q and any(w in t_low for w in ['for aircraft', 'in aircraft', 'aerospace application', 'for aerospace']):
                continue
            if not is_solar_q and any(w in t_low for w in ['solar photovoltaic', 'photovoltaic systems', 'photovoltaic']):
                continue
            if not is_pcb_q and any(w in t_low for w in ['printed wiring boards', 'printed circuit boards']):
                continue
            if is_cable_q:
                # Converter valves / VSC equipment vs electric cables
                if any(w in t_low for w in ['converter valves', 'voltage sourced converters', 'vsc valves', 'thyristor valves']) and not any(w in t_low for w in ['cable', 'cables']):
                    continue
                # Cable ducts / pipes vs electric cables
                if 'pipes (ducts) and fittings for underground' in t_low and not any(w in q_low for w in ['pipe', 'duct']):
                    continue
                # Overhead lines vs underground cables
                if is_underground_q and any(w in t_low for w in ['overhead lines', 'overhead power lines', 'overhead transmission']):
                    continue
            filtered_candidates.append(cand)

        # Prioritize primary product specifications and installation codes over subordinate test methods / storage handling
        from src.standards import classify_standard_role
        is_work_or_repair = bool(re.search(r'\b(?:work|repair|repairing|installation|laying|maintenance|fixing)\b', q_low))
        is_insulation_or_plaster = bool(re.search(r'\b(?:insulation|plaster|plastering)\b', q_low))
        is_prod_query = any(re.search(rf'\b{w}\b', q_low) for w in [
            "cable", "cables", "pipe", "pipes", "piping", "valve", "valves",
            "pump", "pumps", "motor", "motors", "switchgear", "controlgear", "panel", "panels",
            "transformer", "transformers", "cement", "tile", "tiles", "tube", "tubes",
            "wire", "wires", "conductor", "conductors", "flange", "flanges", "fitting", "fittings"
        ])

        def retrieval_candidate_priority(cand: HybridCandidate) -> Tuple[int, float]:
            t_cand = (cand.full_title or "").lower()
            role = classify_standard_role(cand.standard_number, cand.full_title, cand.raw_record.get("scope"))

            # Primary engineering standards: Product specifications, installation codes, and engineering design codes
            if role == "TEST_METHOD":
                role_rank = 3
            elif role == "ALLIED":
                role_rank = 2
            elif (is_work_or_repair or is_insulation_or_plaster) and "storage and handling" in t_cand:
                role_rank = 2
            elif role in ["PRIMARY_PRODUCT", "INSTALLATION", "CODE_OF_PRACTICE"]:
                role_rank = 0
            else:
                role_rank = 1

            # Lexical specificity bonus within primary standards:
            # Reward exact technical noun phrases matching the requirement
            spec_bonus = 0
            if "distribution boards" in q_low and "distribution boards" in t_cand:
                spec_bonus -= 1
            if "fittings" in q_low and "sanitary" not in q_low:
                if any(w in t_cand for w in ["pipe fittings", "steel fittings", "tube fittings"]):
                    spec_bonus -= 1
            if "flange" in q_low and "pipe flanges" in t_cand:
                spec_bonus -= 1

            return (role_rank + spec_bonus, -cand.final_score)

        top_slice = filtered_candidates[:15]
        rest_slice = filtered_candidates[15:]
        top_slice.sort(key=retrieval_candidate_priority)
        scored_candidates = top_slice + rest_slice

        # Convert to SearchResult objects
        search_results: List[SearchResult] = []
        for rank_idx, cand in enumerate(scored_candidates[:top_k], 1):
            rec = cand.raw_record
            formatted = self.det_engine._format_result(
                row_dict=rec,
                score=cand.final_score,
                reason="; ".join(cand.reasons)
            )
            # Assert candidate identity is preserved
            assert formatted.standard_id == cand.standard_id, f"Candidate identity mismatch: {formatted.standard_id} != {cand.standard_id}"
            formatted.bm25_score = cand.bm25_score
            formatted.semantic_score = cand.semantic_score
            formatted.deterministic_score = cand.det_score
            formatted.reranker_score = cand.reranker_score
            formatted.final_score = cand.final_score
            formatted.source_rank_det = cand.det_rank
            formatted.source_rank_bm25 = cand.bm25_rank
            formatted.source_rank_semantic = cand.sem_rank
            formatted.fusion_score = cand.hybrid_score
            formatted.final_rank = rank_idx
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

