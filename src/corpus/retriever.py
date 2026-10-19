"""
src/corpus/retriever.py — Clause-Level Retrieval & Grounding Subsystem

Retrieves clause-aware passages from the ingested standards corpus with strict
edition isolation. Provides verifiable clause grounding without modifying production
ranking weights or fabricating expert approval.
"""

from __future__ import annotations

import re
import os
import sqlite3
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional, Tuple

from src.corpus.storage import CorpusStorage
from src.corpus.chunker import ClausePassage
from src.corpus.manifest import IngestionStatus
from src.corpus.semantics import ClauseEvidenceOutcome, RequirementEvidenceSupportState


@dataclass
class ClauseEvidenceResult:
    """Structured response container for clause-level evidence retrieval."""
    outcome: str                              # Value of ClauseEvidenceOutcome
    passage_text: Optional[str] = None       # Actual text from extracted document
    clause_identifier: Optional[str] = None  # Structurally identified clause, e.g. "4.2"
    page_number: Optional[int] = None        # Page number (1-indexed)
    page_end: Optional[int] = None
    document_id: Optional[str] = None        # Internal doc ID, e.g. DOC-IS-1180-2014
    standard_number: Optional[str] = None    # Standard number
    edition_year: Optional[int] = None       # Exact edition year
    source_citation: Optional[str] = None    # Documentary citation / gazette notification
    source_url: Optional[str] = None         # Official web URL
    file_sha256: Optional[str] = None        # Raw PDF SHA-256
    passage_sha256: Optional[str] = None     # Canonical passage content hash
    extraction_quality_status: Optional[str] = None # Ingestion status, e.g. "EXTRACTED"
    has_table: bool = False
    is_grounded: bool = False                # Strictly True only when structurally verified
    requirement_evidence_support: str = RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value # Value of RequirementEvidenceSupportState
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ClauseEvidenceResult:
        valid_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)


_DEFAULT_STORAGE = object()


class ClauseRetriever:
    """
    Subsystem for querying and verifying clause-level passages from CorpusStorage.
    Preserves exact standard number, edition, page range, and content hashes.
    """

    def __init__(self, storage: Any = _DEFAULT_STORAGE):
        if storage is _DEFAULT_STORAGE:
            self.storage = CorpusStorage()
        else:
            self.storage = storage

    @staticmethod
    def extract_clause_hint(text: str) -> Optional[str]:
        """
        Extracts explicit structural clause citations from requirement text.
        Does NOT guess or infer clause numbers from loose semantic keywords.
        """
        if not text:
            return None

        # Matches: "Clause 4.2", "Section 12.1", "Cl. 3.1"
        match_num = re.search(r'\b(?:Clause|Section|Cl\.)\s*([0-9]+(?:\.[0-9]+)*)\b', text, re.IGNORECASE)
        if match_num:
            return match_num.group(1).strip()

        # Matches: "Table 1", "Table 2.1"
        match_table = re.search(r'\bTable\s+([0-9]+(?:\.[0-9]+)*)\b', text, re.IGNORECASE)
        if match_table:
            return f"Table {match_table.group(1).strip()}"

        # Matches named sections: "Foreword", "Scope"
        match_named = re.search(r'\b(Foreword|Scope)\b', text, re.IGNORECASE)
        if match_named:
            return match_named.group(1).title()

        return None

    @staticmethod
    def evaluate_requirement_support(
        requirement_text: str,
        passage_text: Optional[str],
        clause_identifier: Optional[str] = None,
        is_compound: bool = False,
        compound_components: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Deterministically evaluates whether the retrieved passage supports the requirement.
        Returns a value of RequirementEvidenceSupportState:
          - FULLY_SUPPORTED
          - PARTIALLY_SUPPORTED
          - UNSUPPORTED
          - CONFLICTING
          - UNVERIFIED_COVERAGE
        """
        if not passage_text or not passage_text.strip():
            return RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value

        req_clean = (requirement_text or "").lower()
        pas_clean = passage_text.lower()

        # 1. Contradiction / Conflict Detection:
        # Operating environment conflicts (outdoor vs indoor)
        if "outdoor" in req_clean and any(p in pas_clean for p in ["indoor only", "strictly for indoor", "indoor use only", "not suitable for outdoor"]):
            return RequirementEvidenceSupportState.CONFLICTING.value
        if "indoor" in req_clean and any(p in pas_clean for p in ["outdoor only", "strictly for outdoor", "outdoor use only"]):
            return RequirementEvidenceSupportState.CONFLICTING.value

        # Negation and Exclusion Conflicts (e.g. "without X" vs "mandatory X", "shall not contain X" vs "shall contain X")
        req_negations = re.findall(r'\b(?:without|excluding|shall not have|shall not contain|prohibited)\s+([a-z0-9_-]+)', req_clean)
        for neg_term in req_negations:
            if re.search(rf'\b(?:shall have|shall include|mandatory|requires)\s+{re.escape(neg_term)}\b', pas_clean):
                return RequirementEvidenceSupportState.CONFLICTING.value

        pas_negations = re.findall(r'\b(?:without|excluding|shall not have|shall not contain|prohibited)\s+([a-z0-9_-]+)', pas_clean)
        for neg_term in pas_negations:
            if re.search(rf'\b(?:shall have|shall include|mandatory|requires|with)\s+{re.escape(neg_term)}\b', req_clean):
                return RequirementEvidenceSupportState.CONFLICTING.value

        # Phase conflicts (single phase vs three phase)
        if ("3-phase" in req_clean or "three phase" in req_clean or "3 phase" in req_clean) and any(p in pas_clean for p in ["strictly single phase", "single phase only"]):
            return RequirementEvidenceSupportState.CONFLICTING.value
        if ("single phase" in req_clean or "1-phase" in req_clean) and any(p in pas_clean for p in ["strictly three phase", "three phase only"]):
            return RequirementEvidenceSupportState.CONFLICTING.value

        # Capacity / Rating limit conflicts with Normalized Unit Conversions:
        # Normalization scale to base unit:
        # Power/Losses: W -> 1.0, kW -> 1000.0, MW -> 1e6
        # Voltage: V -> 1.0, kV -> 1000.0
        # Apparent Power: VA -> 1.0, kVA -> 1000.0, MVA -> 1e6
        # Current: A -> 1.0, mA -> 0.001
        unit_scale = {
            "w": ("power", 1.0), "kw": ("power", 1000.0), "mw": ("power", 1e6),
            "v": ("voltage", 1.0), "kv": ("voltage", 1000.0),
            "va": ("apparent_power", 1.0), "kva": ("apparent_power", 1000.0), "mva": ("apparent_power", 1e6),
            "a": ("current", 1.0), "amp": ("current", 1.0), "amps": ("current", 1.0)
        }

        # Check for inequality direction indicators in requirement
        # E.g. "at least 100 kVA", "minimum 50 kV" vs "shall not exceed 475 W", "maximum 50 kW"
        req_ratings = re.findall(r'(\b(?:at least|minimum|min|shall be at least)\s+)?(\d+(?:\.\d+)?)\s*(kva|mva|kv|kw|mw|amp|amps|a\b|w\b|v\b)', req_clean)
        for direction, val_str, unit in req_ratings:
            if unit not in unit_scale:
                continue
            dim, factor = unit_scale[unit]
            req_base_val = float(val_str) * factor
            is_min_req = bool(direction and direction.strip())

            # Find all passage statements in the same physical dimension
            for p_unit, (p_dim, p_factor) in unit_scale.items():
                if p_dim != dim:
                    continue

                # 1. Passage restricts maximum ceiling (e.g., "max 500 W", "shall not exceed 500 W")
                max_matches = re.findall(rf'(?:maximum|max|up to|not exceeding|shall not exceed|within)\s*(\d+(?:\.\d+)?)\s*{p_unit}\b', pas_clean)
                for m_str in max_matches:
                    pas_max_val = float(m_str) * p_factor
                    # If requirement is a minimum specification ("at least X") and passage ceiling is lower -> Conflict!
                    # E.g., Requirement demands at least 100 kW, but standard specifies max permissible 50 kW.
                    if is_min_req and req_base_val > pas_max_val:
                        return RequirementEvidenceSupportState.CONFLICTING.value
                    # If requirement is a ceiling and exceeds standard's strict ceiling -> Conflict!
                    elif not is_min_req and req_base_val > pas_max_val:
                        return RequirementEvidenceSupportState.CONFLICTING.value

                # 2. Passage restricts minimum floor (e.g., "minimum 10 kV", "above 10 kV")
                min_matches = re.findall(rf'(?:minimum|min|exceeding|above|at least)\s*(\d+(?:\.\d+)?)\s*{p_unit}\b', pas_clean)
                for m_str in min_matches:
                    pas_min_val = float(m_str) * p_factor
                    if req_base_val < pas_min_val:
                        return RequirementEvidenceSupportState.CONFLICTING.value

        # Tolerance and Range Check
        # E.g., requirement demands "+/- 2%" but passage specifies "+/- 5%"
        req_tols = re.findall(r'(?:±|\+/-|within)\s*(\d+(?:\.\d+)?)\s*(?:percent|%)', req_clean)
        pas_tols = re.findall(r'(?:±|\+/-|within)\s*(\d+(?:\.\d+)?)\s*(?:percent|%)', pas_clean)
        if req_tols and pas_tols:
            req_tol = float(req_tols[0])
            pas_tol = float(pas_tols[0])
            # If tender demands tighter tolerance than standard allows (e.g. req 2% vs std 5%)
            if req_tol < pas_tol and "tolerance" in req_clean:
                return RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value

        # 2. Irrelevance Detection:
        stop_words = {
            "shall", "with", "from", "that", "this", "standard", "conforming", "clause", "section",
            "table", "supply", "installation", "tender", "specification", "requirements", "item",
            "procurement", "work", "works", "required", "provisional", "active", "under", "outdoor", "indoor"
        }
        req_words = {
            w for w in re.findall(r'[a-z]{4,}', req_clean)
            if w not in stop_words
        }

        if req_words:
            overlap = {w for w in req_words if w in pas_clean}
            if len(overlap) == 0:
                return RequirementEvidenceSupportState.UNSUPPORTED.value

        # 3. Compound Requirement Coverage:
        if is_compound and compound_components and len(compound_components) > 1:
            covered_components = 0
            for c in compound_components:
                if isinstance(c, dict):
                    c_ev = c.get("clause_evidence") or {}
                    if c_ev.get("outcome") == ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value and (
                        c_ev.get("is_grounded") or c_ev.get("requirement_evidence_support") == RequirementEvidenceSupportState.FULLY_SUPPORTED.value
                    ):
                        covered_components += 1
                elif isinstance(c, str):
                    # Check if the single passage text covers key words of this sub-component
                    sub_words = {w for w in re.findall(r'[a-z]{4,}', c.lower()) if w not in stop_words}
                    if sub_words and len({w for w in sub_words if w in pas_clean}) >= 1:
                        covered_components += 1
            if covered_components == 0:
                return RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value
            elif covered_components < len(compound_components):
                return RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value

        # 4. Conservative Technical Parameter Verification:
        # If the requirement specifies numeric technical parameters (e.g. 11 kV, 475 W, 100 kVA),
        # but the passage does NOT mention any parameter in that physical dimension,
        # we cannot conservatively declare FULLY_SUPPORTED based on loose words alone!
        if req_ratings:
            req_dims = {unit_scale[u][0] for _, _, u in req_ratings if u in unit_scale}
            pas_ratings = re.findall(r'(\d+(?:\.\d+)?)\s*(kva|mva|kv|kw|mw|amp|amps|a\b|w\b|v\b)', pas_clean)
            pas_dims = {unit_scale[u][0] for _, u in pas_ratings if u in unit_scale}
            
            # If requirement specifies ratings that are completely absent from passage:
            missing_dims = req_dims - pas_dims
            if missing_dims:
                # E.g. tender specifies exact losses in Watts, but passage only talks about insulation in kV
                return RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value

        # 5. Steel Strength Grade Verification (e.g. Fe 415, Fe 500, Fe 500D vs unsupported Fe 750)
        req_fe_grades = re.findall(r'\bfe\s*[-_]?\s*(\d{3,4})([a-z]*)\b', req_clean)
        if req_fe_grades:
            pas_fe_grades = re.findall(r'\bfe\s*[-_]?\s*(\d{3,4})([a-z]*)\b', pas_clean)
            if pas_fe_grades:
                pas_fe_nums = {g[0] for g in pas_fe_grades}
                for fe_num, fe_suffix in req_fe_grades:
                    if fe_num not in pas_fe_nums:
                        return RequirementEvidenceSupportState.UNSUPPORTED.value
            else:
                # Requirement specified an exact steel grade, but this passage only covers generic scope without grades
                return RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value

        # 6. Concrete Grade Verification (e.g. M25, M30 vs unsupported M100)
        req_m_grades = re.findall(r'\bm\s*(\d{2,3})\b', req_clean)
        if req_m_grades:
            pas_m_grades = re.findall(r'\bm\s*(\d{2,3})\b', pas_clean)
            if pas_m_grades:
                pas_m_nums = set(pas_m_grades)
                for m_num in req_m_grades:
                    if m_num not in pas_m_nums:
                        return RequirementEvidenceSupportState.UNSUPPORTED.value
            else:
                return RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value

        # 7. Dimensional Parameter Bounds Verification (e.g. pipe outside diameter / nominal size)
        req_sizes = re.findall(r'\b(?:dn\s*(\d+)|(?:dia(?:meter)?\s*(?:of\s*)?)?(\d+)\s*mm\b)', req_clean)
        valid_req_sizes = []
        for dn_val, mm_val in req_sizes:
            v_str = dn_val or mm_val
            if v_str:
                val = float(v_str)
                if 10 <= val <= 20000 and val not in [1995, 2000, 2004, 2008, 2011, 2013, 2015, 2016, 2020, 2021, 2022, 2023, 2024, 2025]:
                    valid_req_sizes.append(val)

        if valid_req_sizes:
            ceiling_match = re.search(r'\bup\s+to\s+(?:and\s+including\s+)?(\d+)\s*mm\b', pas_clean)
            range_match = re.search(r'\b(?:dn\s*)?(\d+)\s*(?:mm\s*)?to\s*(?:dn\s*)?(\d+)\s*mm\b', pas_clean)
            pas_sizes = re.findall(r'\b(?:dn\s*(\d+)|\b(\d+)\s*mm\b)', pas_clean)
            pas_valid_sizes = [float(d or m) for d, m in pas_sizes if (d or m)]
            
            if ceiling_match:
                max_ceiling = float(ceiling_match.group(1))
                for val in valid_req_sizes:
                    if val > max_ceiling:
                        return RequirementEvidenceSupportState.UNSUPPORTED.value

            if range_match:
                min_size = float(range_match.group(1))
                max_size = float(range_match.group(2))
                for val in valid_req_sizes:
                    if val > max_size or val < min_size:
                        return RequirementEvidenceSupportState.UNSUPPORTED.value
            elif pas_valid_sizes and not ceiling_match:
                for val in valid_req_sizes:
                    if val not in pas_valid_sizes:
                        return RequirementEvidenceSupportState.UNSUPPORTED.value
            elif not ceiling_match:
                # Requirement specified an exact diameter/size, but this passage only covers generic scope without dimensions
                return RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value

        return RequirementEvidenceSupportState.FULLY_SUPPORTED.value

    def retrieve_clause_evidence(
        self,
        standard_number: str,
        edition_year: Optional[int] = None,
        clause_identifier: Optional[str] = None,
        query_text: Optional[str] = None,
        requirement_text: Optional[str] = None,
        is_compound: bool = False,
        compound_components: Optional[List[Dict[str, Any]]] = None
    ) -> ClauseEvidenceResult:
        """
        Integrates clause retrieval with strict eligibility, boundary, and requirement-support checks.
        """
        if not standard_number:
            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value,
                message="Standard number must be specified for clause retrieval."
            )

        # 1. Check Corpus Storage Availability
        if self.storage is None:
            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value,
                standard_number=standard_number,
                edition_year=edition_year,
                message="Corpus storage subsystem is not configured."
            )

        # Normalize edition year and base standard number if year is in string (e.g. "IS 1180 (Part 1) : 2014")
        if edition_year is None:
            year_match = re.search(r':\s*(\d{4})\b', standard_number)
            if year_match:
                edition_year = int(year_match.group(1))
        base_standard_number = re.sub(r'\s*:\s*\d{4}\b', '', standard_number).strip()

        try:
            # Check if database file exists and is queryable
            if not os.path.exists(self.storage.db_path):
                return ClauseEvidenceResult(
                    outcome=ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value,
                    standard_number=standard_number,
                    edition_year=edition_year,
                    message=f"Corpus database file '{self.storage.db_path}' does not exist."
                )

            # Test connection
            with self.storage._get_connection() as conn:
                conn.execute("SELECT 1 FROM corpus_documents LIMIT 1;")
        except (sqlite3.OperationalError, sqlite3.DatabaseError) as err:
            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CORPUS_NOT_AVAILABLE.value,
                standard_number=standard_number,
                edition_year=edition_year,
                message=f"Corpus database unavailable: {str(err)}"
            )
        except Exception as err:
            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CORPUS_LOOKUP_ERROR.value,
                standard_number=standard_number,
                edition_year=edition_year,
                message=f"Corpus connection error: {str(err)}"
            )

        # 2. Check Document Registration & Eligibility
        try:
            all_docs = self.storage.get_documents_by_standard(standard_number, edition_year=edition_year)
            if not all_docs and base_standard_number != standard_number:
                all_docs = self.storage.get_documents_by_standard(base_standard_number, edition_year=edition_year)

            if not all_docs:
                return ClauseEvidenceResult(
                    outcome=ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value,
                    standard_number=standard_number,
                    edition_year=edition_year,
                    message=f"No full-text corpus document registered for standard '{standard_number}'" +
                            (f" (Edition {edition_year})" if edition_year else "") + "."
                )

            # Filter for successful extraction
            extracted_docs = [d for d in all_docs if d.get("ingestion_status") == IngestionStatus.EXTRACTED.value]
            if not extracted_docs:
                first_doc = all_docs[0]
                status = first_doc.get("ingestion_status")
                return ClauseEvidenceResult(
                    outcome=ClauseEvidenceOutcome.CORPUS_DOCUMENT_NOT_ELIGIBLE.value,
                    document_id=first_doc.get("doc_id"),
                    standard_number=standard_number,
                    edition_year=first_doc.get("edition_year"),
                    file_sha256=first_doc.get("file_sha256"),
                    extraction_quality_status=status,
                    message=f"Corpus document '{first_doc.get('doc_id')}' is ineligible for clause evidence (ingestion status: {status})."
                )

            # Select exact eligible document
            doc = extracted_docs[0]
            doc_id = doc["doc_id"]
            doc_sha = doc.get("file_sha256")
            doc_year = doc.get("edition_year")
            doc_citation = doc.get("source_citation")
            doc_url = doc.get("source_url")

        except Exception as err:
            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CORPUS_LOOKUP_ERROR.value,
                standard_number=standard_number,
                edition_year=edition_year,
                message=f"Error evaluating document eligibility: {str(err)}"
            )

        # 3. Resolve Target Clause
        target_clause = clause_identifier or (self.extract_clause_hint(query_text) if query_text else None)

        try:
            # Case A: Specific Clause Identifier Requested
            if target_clause:
                passages = self.storage.get_passages_by_standard(
                    standard_number=doc.get("standard_number", standard_number),
                    edition_year=doc_year,
                    clause_id=target_clause
                )
                matching = [p for p in passages if p.doc_id == doc_id]
                if matching:
                    p = matching[0]
                    support_state = self.evaluate_requirement_support(
                        requirement_text=requirement_text or query_text or "",
                        passage_text=p.passage_text,
                        clause_identifier=p.clause_identifier,
                        is_compound=is_compound,
                        compound_components=compound_components
                    )
                    is_grounded = p.clause_identifier != "CLAUSE_UNKNOWN"
                    return ClauseEvidenceResult(
                        outcome=ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value,
                        passage_text=p.passage_text,
                        clause_identifier=p.clause_identifier,
                        page_number=p.page_start,
                        page_end=p.page_end,
                        document_id=doc_id,
                        standard_number=p.standard_number,
                        edition_year=p.edition_year,
                        source_citation=doc_citation,
                        source_url=doc_url,
                        file_sha256=doc_sha,
                        passage_sha256=p.content_hash,
                        extraction_quality_status=doc.get("ingestion_status"),
                        has_table=p.has_table,
                        is_grounded=is_grounded,
                        requirement_evidence_support=support_state,
                        message=f"Authentic passage for Clause {p.clause_identifier} grounded in document {doc_id}."
                        if is_grounded else "Passage from unknown clause section; grounding cannot be verified."
                    )
                else:
                    return ClauseEvidenceResult(
                        outcome=ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value,
                        clause_identifier=target_clause,
                        document_id=doc_id,
                        standard_number=standard_number,
                        edition_year=doc_year,
                        file_sha256=doc_sha,
                        extraction_quality_status=doc.get("ingestion_status"),
                        is_grounded=False,
                        requirement_evidence_support=RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value,
                        message=f"Clause '{target_clause}' not found in eligible document '{doc_id}'."
                    )

            # Case B: No Explicit Clause Identifier (Lexical Search Support)
            if query_text and query_text.strip():
                passages = self.search_clauses(
                    query=query_text,
                    standard_number=doc.get("standard_number", standard_number),
                    edition_year=doc_year,
                    top_k=4
                )
                matching = [p for p in passages if p.doc_id == doc_id]
                if matching:
                    eval_results = []
                    for cand_p in matching:
                        s_state = self.evaluate_requirement_support(
                            requirement_text=requirement_text or query_text or "",
                            passage_text=cand_p.passage_text,
                            clause_identifier=cand_p.clause_identifier,
                            is_compound=is_compound,
                            compound_components=compound_components
                        )
                        eval_results.append((cand_p, s_state))

                    if any(s == RequirementEvidenceSupportState.CONFLICTING.value for _, s in eval_results):
                        support_state = RequirementEvidenceSupportState.CONFLICTING.value
                        p = next((cp for cp, s in eval_results if s == RequirementEvidenceSupportState.CONFLICTING.value), matching[0])
                    else:
                        order = {
                            RequirementEvidenceSupportState.FULLY_SUPPORTED.value: 0,
                            RequirementEvidenceSupportState.PARTIALLY_SUPPORTED.value: 1,
                            RequirementEvidenceSupportState.UNSUPPORTED.value: 2,
                            RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value: 3
                        }
                        eval_results.sort(key=lambda x: order.get(x[1], 4))
                        p, support_state = eval_results[0]

                    is_grounded = p.clause_identifier != "CLAUSE_UNKNOWN"
                    msg = (
                        f"Authentic passage for Clause {p.clause_identifier} grounded in document {doc_id}."
                        if is_grounded
                        else "Passage from unknown clause section; grounding cannot be verified."
                    )
                    return ClauseEvidenceResult(
                        outcome=ClauseEvidenceOutcome.CLAUSE_EVIDENCE_FOUND.value,
                        passage_text=p.passage_text,
                        clause_identifier=p.clause_identifier,
                        page_number=p.page_start,
                        page_end=p.page_end,
                        document_id=doc_id,
                        standard_number=p.standard_number,
                        edition_year=p.edition_year,
                        source_citation=doc_citation,
                        source_url=doc_url,
                        file_sha256=doc_sha,
                        passage_sha256=p.content_hash,
                        extraction_quality_status=doc.get("ingestion_status"),
                        has_table=p.has_table,
                        is_grounded=is_grounded,
                        requirement_evidence_support=support_state,
                        message=msg
                    )

            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CLAUSE_EVIDENCE_NOT_FOUND.value,
                document_id=doc_id,
                standard_number=standard_number,
                edition_year=doc_year,
                file_sha256=doc_sha,
                extraction_quality_status=doc.get("ingestion_status"),
                is_grounded=False,
                requirement_evidence_support=RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value,
                message="No clause citation requested and no relevant passage located via search."
            )

        except Exception as err:
            return ClauseEvidenceResult(
                outcome=ClauseEvidenceOutcome.CORPUS_LOOKUP_ERROR.value,
                standard_number=standard_number,
                edition_year=edition_year,
                document_id=doc_id if 'doc_id' in locals() else None,
                is_grounded=False,
                requirement_evidence_support=RequirementEvidenceSupportState.UNVERIFIED_COVERAGE.value,
                message=f"Error executing clause search in corpus: {str(err)}"
            )

    def get_clause(
        self,
        standard_number: str,
        clause_identifier: str,
        edition_year: Optional[int] = None
    ) -> Optional[ClausePassage]:
        """
        Retrieves a specific clause passage for a standard and optional edition.
        Does not infer or hallucinate non-matching clauses.
        """
        passages = self.storage.get_passages_by_standard(
            standard_number=standard_number,
            edition_year=edition_year,
            clause_id=clause_identifier
        )
        return passages[0] if passages else None

    def search_clauses(
        self,
        query: str,
        standard_number: Optional[str] = None,
        edition_year: Optional[int] = None,
        top_k: int = 5
    ) -> List[ClausePassage]:
        """
        Performs lexical keyword matching over stored passages.
        Strictly enforces edition isolation when edition_year is specified.
        """
        # If standard is specified, retrieve candidate passages for that standard
        if standard_number:
            candidates = self.storage.get_passages_by_standard(
                standard_number=standard_number,
                edition_year=edition_year
            )
        else:
            with self.storage._get_connection() as conn:
                cursor = conn.cursor()
                rows = cursor.execute("SELECT passage_id FROM corpus_passages").fetchall()
                candidates = [self.storage.get_passage_by_id(r["passage_id"]) for r in rows]
                candidates = [c for c in candidates if c is not None]

        if not candidates or not query.strip():
            return candidates[:top_k]

        query_tokens = set(re.findall(r'\b[a-zA-Z0-9_-]+\b', query.lower()))
        if not query_tokens:
            return candidates[:top_k]

        scored: List[Tuple[float, ClausePassage]] = []
        for passage in candidates:
            passage_tokens = set(re.findall(r'\b[a-zA-Z0-9_-]+\b', passage.passage_text.lower()))
            if not passage_tokens:
                continue

            overlap = len(query_tokens.intersection(passage_tokens))
            union = len(query_tokens.union(passage_tokens))
            score = (overlap / union) if union > 0 else 0.0

            if passage.clause_identifier.lower() in query.lower():
                score += 0.5

            if overlap > 0:
                scored.append((score, passage))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def verify_clause_grounding(
        self,
        standard_number: str,
        clause_identifier: str,
        expected_content_hash: Optional[str] = None,
        edition_year: Optional[int] = None
    ) -> Tuple[bool, Optional[ClausePassage], Optional[str]]:
        """
        Deterministically verifies if a clause citation is grounded in the corpus.
        Returns:
            (is_grounded, matched_passage, failure_reason)
        """
        passage = self.get_clause(
            standard_number=standard_number,
            clause_identifier=clause_identifier,
            edition_year=edition_year
        )

        if not passage:
            return False, None, f"Clause '{clause_identifier}' not found in ingested corpus for standard '{standard_number}'"

        if expected_content_hash:
            if passage.content_hash != expected_content_hash:
                return False, passage, f"Content hash mismatch for clause '{clause_identifier}': expected '{expected_content_hash}', got '{passage.content_hash}'"

        return True, passage, None
