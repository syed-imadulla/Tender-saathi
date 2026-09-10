"""
Module: src/search.py
Purpose: Version-aware multi-modal search and retrieval engine for BIS Standards.

Supports:
1. Exact standard number (e.g. 'IS 15000', 'IS 778')
2. Partial standard number (e.g. '14846', '10434')
3. Standard title (e.g. 'Sluice Valve', 'Precast Concrete Pipes')
4. Natural-language requirement & technical keywords (e.g. 'food hygiene', 'laying concrete pipes')

Implements strict version-aware role labelling:
- CURRENT_ACTIVE
- OLDER_VERSION
- REPLACED_OR_SUPERSEDED
- REFERENCE_ONLY
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import re
from src.standards import StandardsDatabase


@dataclass
class SearchResult:
    standard_id: str
    standard_number: str
    year: Optional[int]
    full_title: str
    status: str
    version_role: str                   # CURRENT_ACTIVE, REPLACED_OR_SUPERSEDED, WITHDRAWN, REFERENCE_ONLY
    relevance_score: float
    relevance_reason: str
    scope_summary: str
    referenced_standards: List[str] = field(default_factory=list)
    explicit_relationships: List[Dict[str, str]] = field(default_factory=list)
    verification_status: str = "VERIFIED"
    source_provenance: str = ""
    # Milestone 8 Score Transparency & AI Attribution fields:
    bm25_score: float = 0.0
    semantic_score: float = 0.0
    deterministic_score: float = 0.0
    reranker_score: Optional[float] = None
    final_score: float = 0.0
    ai_provider: Optional[str] = None
    ai_model: Optional[str] = None



class StandardsSearchEngine:
    """Retrieval engine operating over StandardsDatabase with version-aware ranking."""

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()

    def search(self, query: str, top_k: int = 5, components: Optional[List[Any]] = None) -> List[SearchResult]:
        query_clean = query.strip()
        if not query_clean:
            return []

        # Resolve components if not passed
        if components is None:
            try:
                from src.decompose import decompose_requirement
                components = decompose_requirement(query_clean).components
            except Exception:
                components = []

        results = []
        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Exact or Partial Standard Number Check (e.g. "IS 15000", "14846", "IS/ISO 10434")
            std_num_match = re.search(r'\b(?:IS\s*(?:/|\s*)?(?:ISO|IEC)?\s*)?(\d{3,5})\b', query_clean, re.IGNORECASE)
            exact_number = std_num_match.group(1) if std_num_match else None

            # Also check if query targets a standard that was superseded (e.g., "IS 10611")
            cursor.execute("""
            SELECT s.*, r.relationship_type, r.evidence as rel_evidence, r.target_standard
            FROM standards s
            JOIN standard_relationships r ON s.standard_id = r.source_standard_id
            WHERE r.relationship_type = 'SUPERSEDES' AND r.target_standard LIKE ?
            """, (f"%{query_clean}%",))
            superseding_rows = cursor.fetchall()

            for row in superseding_rows:
                r_dict = dict(row)
                results.append(self._format_result(
                    r_dict,
                    score=1.0,
                    reason=f"Authoritative replacement: {r_dict['original_standard_identifier']} explicitly supersedes {query_clean} ({r_dict['rel_evidence']})"
                ))

            # Exact standard match
            if exact_number:
                cursor.execute("""
                SELECT * FROM standards
                WHERE standard_number LIKE ? OR standard_id LIKE ? OR original_standard_identifier LIKE ?
                """, (f"%{exact_number}%", f"%{exact_number}%", f"%{exact_number}%"))
                rows = cursor.fetchall()
                for row in rows:
                    r_dict = dict(row)
                    if not any(res.standard_id == r_dict["standard_id"] for res in results):
                        results.append(self._format_result(
                            r_dict,
                            score=0.98,
                            reason=f"Standard number match on identifier containing '{exact_number}'"
                        ))

            # 2. Title, Scope, and Decomposed Component Matching
            STOP_WORDS = {
                'repair', 'maint', 'maintenance', 'annual', 'contract', 'work', 'works',
                'supply', 'supplies', 'execution', 'providing', 'fixing', 'replacement',
                'replacing', 'rate', 'basis', 'incl', 'including', 'near', 'from', 'with',
                'under', 'over', 'into', 'lieu', 'rusted', 'damaged', 'defective', 'new',
                'newly', 'campus', 'building', 'office', 'department', 'school', 'institute',
                'item', 'items', 'etc', 'and', 'the', 'for', 'dismantling', 'shifting',
                'reinstallation', 'upgradation', 'all', 'opening', 'conversion'
            }

            raw_tokens = [t.lower() for t in re.split(r'[\s,\-/:]+', query_clean) if len(t) > 2]
            sig_tokens = [t for t in raw_tokens if t not in STOP_WORDS]
            effective_tokens = sig_tokens or raw_tokens

            # Detect domain constraints from decomposed components
            has_industrial_or_mv = False
            if components:
                for c in components:
                    attrs = getattr(c, "extracted_attributes", {}) or {}
                    c_type = getattr(c, "component_type", "")
                    if attrs.get("level") == "medium_or_high_voltage" or attrs.get("is_process") or c_type in ["control"]:
                        has_industrial_or_mv = True
                        break

            cursor.execute("SELECT * FROM standards")
            all_standards = cursor.fetchall()

            for row in all_standards:
                r_dict = dict(row)
                if any(res.standard_id == r_dict["standard_id"] for res in results):
                    continue

                title_lower = (r_dict["full_title"] or "").lower()
                scope_lower = (r_dict["scope"] or "").lower()
                notes_lower = (r_dict["notes"] or "").lower()
                std_num = r_dict["standard_number"]

                # Domain conflict filter: exclude agricultural irrigation pump standards when
                # requirement specifies medium voltage (3.3 kV), VFD drives, or industrial process pumps
                is_agri = "agriculture" in title_lower or "agricultural" in title_lower
                if is_agri and has_industrial_or_mv:
                    continue

                # Exact phrase in title or scope
                if query_clean.lower() in title_lower:
                    results.append(self._format_result(
                        r_dict,
                        score=0.95,
                        reason=f"Exact query phrase match in standard title: '{query_clean}'"
                    ))
                    continue

                if query_clean.lower() in scope_lower:
                    results.append(self._format_result(
                        r_dict,
                        score=0.90,
                        reason=f"Exact query phrase match in scope description: '{query_clean}'"
                    ))
                    continue

                # Component-level evaluation
                comp_score = 0.0
                comp_reasons = []
                matched_components = 0

                if components:
                    for c in components:
                        c_text = getattr(c, "text", "").lower()
                        c_type = getattr(c, "component_type", "")
                        c_attrs = getattr(c, "extracted_attributes", {}) or {}
                        std_focus = c_attrs.get("standard_focus")

                        # Check standard focus match (e.g. IS/IEC 61800, IS/IEC 61439, IS/IEC 60034-1)
                        if std_focus and std_focus in std_num:
                            comp_score += 0.55
                            matched_components += 1
                            comp_reasons.append(f"Component '{c.text}' ({c_type}) matches standard series {std_focus}")

                        # Check component text in title or scope/notes
                        if len(c_text) > 2:
                            if c_text in title_lower:
                                comp_score += 0.35
                                matched_components += 1
                                comp_reasons.append(f"Component '{c.text}' in title")
                            elif c_text in scope_lower or c_text in notes_lower:
                                comp_score += 0.25
                                matched_components += 1
                                comp_reasons.append(f"Component '{c.text}' in scope/notes")

                # Distinctive domain noun match (e.g. "cpvc", "hubless", "haccp", "sluice valve")
                domain_hits = []
                for dt in ["cpvc", "hubless", "haccp", "sluice", "vitrified", "flange", "earthing", "sewerage", "plaster", "insulation", "sanitary", "pillar", "cable", "vfd", "pump"]:
                    if dt in query_clean.lower() and (dt in title_lower or dt in scope_lower):
                        domain_hits.append(dt)

                # Token overlap scoring using effective tokens
                title_hits = sum(1 for t in effective_tokens if t in title_lower) if effective_tokens else 0
                scope_hits = sum(1 for t in effective_tokens if t in scope_lower) if effective_tokens else 0

                if domain_hits or title_hits > 0 or scope_hits > 0 or comp_score > 0:
                    raw_score = (title_hits * 0.45) + (scope_hits * 0.25)
                    if domain_hits:
                        raw_score += len(domain_hits) * 0.40

                    # Incorporate component score
                    raw_score += comp_score

                    # Normalize against matched subset rather than entire lengthy query
                    norm_denom = max(1, min(len(effective_tokens), 3))
                    score = min(0.95, raw_score / norm_denom)

                    # Multi-component coherence boost
                    if matched_components >= 2:
                        score = min(0.96, score * 1.15)

                    # Boost specific product standards over generic handbooks (SP)
                    if r_dict["standard_number"].startswith("IS") and not r_dict["standard_number"].startswith("SP"):
                        score = min(0.96, score * 1.12)

                    if raw_score >= 0.35 or score >= 0.22 or comp_score >= 0.40:
                        reasons = []
                        if comp_reasons:
                            reasons.extend(comp_reasons)
                        if domain_hits:
                            reasons.append(f"Domain keyword match: {', '.join(domain_hits)}")
                        if title_hits:
                            reasons.append(f"{title_hits} title keyword matches")
                        if scope_hits:
                            reasons.append(f"{scope_hits} scope keyword matches")

                        results.append(self._format_result(
                            r_dict,
                            score=round(score, 3),
                            reason="; ".join(reasons)
                        ))

        # Sort by relevance score descending with component/title hit tie-breaker
        results.sort(
            key=lambda x: (
                x.relevance_score,
                x.relevance_reason.count("title"),
                x.relevance_reason.count("Component")
            ),
            reverse=True
        )
        return results[:top_k]

    def _format_result(self, row_dict: Dict[str, Any], score: float, reason: str) -> SearchResult:
        std_id = row_dict["standard_id"]
        status = row_dict["status"]

        # Determine version role based on status and explicit evidence
        if status.lower() == "active":
            version_role = "CURRENT_ACTIVE"
        elif "superseded" in status.lower():
            version_role = "REPLACED_OR_SUPERSEDED"
        elif "withdrawn" in status.lower():
            version_role = "WITHDRAWN"
        else:
            version_role = "CURRENT_ACTIVE"

        # Fetch child references and relationships
        refs = self.db.get_references(std_id)
        ref_names = [f"{r['referenced_standard_number']}{' (' + str(r['referenced_year']) + ')' if r['referenced_year'] else ''}" for r in refs]

        rels = self.db.get_relationships(std_id)
        rel_list = [{"target": r["target_standard"], "type": r["relationship_type"], "evidence": r["evidence"]} for r in rels]

        scope = row_dict.get("scope") or ""
        scope_summary = (scope[:220] + "...") if len(scope) > 220 else scope

        return SearchResult(
            standard_id=std_id,
            standard_number=row_dict["standard_number"],
            year=row_dict.get("year"),
            full_title=row_dict["full_title"],
            status=status,
            version_role=version_role,
            relevance_score=score,
            relevance_reason=reason,
            scope_summary=scope_summary,
            referenced_standards=ref_names[:10], # Top 10 references
            explicit_relationships=rel_list,
            verification_status=row_dict["verification_status"],
            source_provenance=f"{row_dict['source']} ({row_dict.get('source_url') or 'local'})",
            deterministic_score=score,
            final_score=score
        )
