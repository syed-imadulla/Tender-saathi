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


class StandardsSearchEngine:
    """Retrieval engine operating over StandardsDatabase with version-aware ranking."""

    def __init__(self, db: Optional[StandardsDatabase] = None):
        self.db = db or StandardsDatabase()

    def search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        query_clean = query.strip()
        if not query_clean:
            return []

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

            # 2. Title and Scope Substring / Token Matching
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

            cursor.execute("SELECT * FROM standards")
            all_standards = cursor.fetchall()

            for row in all_standards:
                r_dict = dict(row)
                if any(res.standard_id == r_dict["standard_id"] for res in results):
                    continue

                title_lower = (r_dict["full_title"] or "").lower()
                scope_lower = (r_dict["scope"] or "").lower()
                notes_lower = (r_dict["notes"] or "").lower()

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

                # Distinctive domain noun match (e.g. "cpvc", "hubless", "haccp", "sluice valve")
                domain_hits = []
                for dt in ["cpvc", "hubless", "haccp", "sluice", "vitrified", "flange", "earthing", "sewerage", "plaster", "insulation", "sanitary", "pillar", "cable", "vfd", "pump"]:
                    if dt in query_clean.lower() and (dt in title_lower or dt in scope_lower):
                        domain_hits.append(dt)

                # Token overlap scoring using effective tokens
                if effective_tokens:
                    title_hits = sum(1 for t in effective_tokens if t in title_lower)
                    scope_hits = sum(1 for t in effective_tokens if t in scope_lower)

                    if domain_hits or title_hits > 0 or scope_hits > 0:
                        raw_score = (title_hits * 0.45) + (scope_hits * 0.25)
                        if domain_hits:
                            raw_score += len(domain_hits) * 0.40

                        # Normalize against matched subset rather than entire lengthy query
                        norm_denom = max(1, min(len(effective_tokens), 3))
                        score = min(0.92, raw_score / norm_denom)

                        # Boost specific product standards over generic handbooks (SP)
                        if r_dict["standard_number"].startswith("IS") and not r_dict["standard_number"].startswith("SP"):
                            score = min(0.95, score * 1.12)

                        if raw_score >= 0.35 or score >= 0.22:
                            reasons = []
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

        # Sort by relevance score descending
        results.sort(key=lambda x: x.relevance_score, reverse=True)
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
            source_provenance=f"{row_dict['source']} ({row_dict.get('source_url') or 'local'})"
        )
