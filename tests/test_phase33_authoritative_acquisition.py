"""
tests/test_phase33_authoritative_acquisition.py — Phase 33 Test Suite.

Validates:
1. Authentic Source Acquisition & Checksum Integrity (IS 1239 Part 2, IS 14846, IS 800).
2. Clause and Page Provenance Preservation in corpus.db.
3. Safe, Idempotent Document Ingestion.
4. Acquisition Blocker Recording for Unacquired Sources (e.g. IS 2062).
5. Evidence-Grounded Cross-Reference Traversal from Grounded Clauses.
6. Cycle Prevention, Depth Bounds, and Deduplication in Traversal.
7. Lifecycle Awareness for Referenced Standards (Active, Withdrawn, Superseded).
8. Contextual Relevance Filtering Against Tender Requirements.
9. Safety Gate Invariant: Graph Connectivity NEVER Substitutes for Clause Evidence.
10. Compound Requirement Evidence Isolation (Pipe Fittings + Sluice Valves).
11. Ground Truth Benchmark Bit-for-Bit Integrity.
"""

from __future__ import annotations

import os
import sqlite3
import hashlib
import pytest

from src.corpus.storage import CorpusStorage
from src.graph import StandardsGraph, TraversedReference
from src.extract import extract_from_text
from src.recommend import StandardsRecommender
from scripts.ingest_normative_standards import ingest_normative_corpus


class TestPhase33AuthoritativeAcquisition:
    """Comprehensive regression suite for Phase 33 authoritative acquisition and traversal."""

    @pytest.fixture(autouse=True)
    def setup_fixtures(self):
        self.corpus_storage = CorpusStorage()
        self.graph = StandardsGraph()
        self.recommender = StandardsRecommender()

    # -----------------------------------------------------------------------
    # 1. Authentic Source Ingestion & Checksum Integrity
    # -----------------------------------------------------------------------
    def test_authentic_source_ingestion_and_checksum_integrity(self):
        """Verify the 3 target standards are registered with authentic gazette URLs and SHA-256 hashes."""
        with sqlite3.connect("data/standards/corpus.db") as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            docs = {
                r["doc_id"]: r for r in cur.execute(
                    "SELECT doc_id, standard_number, edition_year, source_url, file_sha256, licensing_status, ingestion_status "
                    "FROM corpus_documents WHERE doc_id IN ('DOC-IS-1239-Part-2-2011', 'DOC-IS-14846-2000', 'DOC-IS-800-2007')"
                ).fetchall()
            }

        assert len(docs) == 3, f"Expected 3 target documents registered, found {len(docs)}"

        # IS 1239 (Part 2) : 2011
        doc_1239 = docs["DOC-IS-1239-Part-2-2011"]
        assert doc_1239["standard_number"] == "IS 1239 (Part 2)"
        assert doc_1239["edition_year"] == 2011
        assert doc_1239["source_url"] == "https://archive.org/details/gov.in.is.1239.2.2011"
        assert doc_1239["file_sha256"] == "f2b3d1dd35eb232b58762d1ef8161c3d3dc570f026947756b7840f33b53557ca"
        assert doc_1239["licensing_status"] == "STATUTORY_PUBLIC_GAZETTE"
        assert doc_1239["ingestion_status"] == "EXTRACTED"

        # IS 14846 : 2000
        doc_14846 = docs["DOC-IS-14846-2000"]
        assert doc_14846["standard_number"] == "IS 14846"
        assert doc_14846["edition_year"] == 2000
        assert doc_14846["source_url"] == "https://archive.org/details/gov.in.is.14846.2000"
        assert doc_14846["file_sha256"] == "8bf2d8f924d773ec6877a0124431738198019dde287d5c1122779532f1ee9d03"
        assert doc_14846["licensing_status"] == "STATUTORY_PUBLIC_GAZETTE"
        assert doc_14846["ingestion_status"] == "EXTRACTED"

        # IS 800 : 2007
        doc_800 = docs["DOC-IS-800-2007"]
        assert doc_800["standard_number"] == "IS 800"
        assert doc_800["edition_year"] == 2007
        assert doc_800["source_url"] == "https://archive.org/details/gov.in.is.800.2007"
        assert doc_800["file_sha256"] == "fdb899a1a7c7a2bd75493a998abda11b5336b637c55302601cfaff7b88fb24df"
        assert doc_800["licensing_status"] == "STATUTORY_PUBLIC_GAZETTE"
        assert doc_800["ingestion_status"] == "EXTRACTED"

    # -----------------------------------------------------------------------
    # 2. Clause and Page Provenance Preservation
    # -----------------------------------------------------------------------
    def test_clause_and_page_provenance_preservation(self):
        """Verify authentic passages have exact clause identifiers, non-empty page numbers, and verified status."""
        with sqlite3.connect("data/standards/corpus.db") as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            rows = cur.execute(
                "SELECT standard_number, clause_identifier, page_start, page_end, content_hash, verification_state, passage_text "
                "FROM corpus_passages WHERE standard_number IN ('IS 1239 (Part 2)', 'IS 14846', 'IS 800') "
                "ORDER BY standard_number, clause_identifier"
            ).fetchall()

        assert len(rows) == 13, f"Expected 13 passages across 3 target standards, found {len(rows)}"

        clauses_by_std = {}
        for r in rows:
            s = r["standard_number"]
            clauses_by_std.setdefault(s, []).append(r["clause_identifier"])
            assert r["page_start"] >= 1, "Page start must be valid positive integer"
            assert len(r["content_hash"]) == 64, "Content hash must be valid 64-char SHA-256"
            assert r["verification_state"] == "CLAUSE_IDENTIFIER_VERIFIED"
            assert len(r["passage_text"]) > 50, "Passage text must contain substantive normative extract"

        assert set(clauses_by_std["IS 1239 (Part 2)"]) == {"1.1", "4.1", "7.1", "8.1"}
        assert set(clauses_by_std["IS 14846"]) == {"1.1", "4.1", "6.1", "7.1", "10.1"}
        assert set(clauses_by_std["IS 800"]) == {"1.1", "2.2", "3.7", "10.1"}

    # -----------------------------------------------------------------------
    # 3. Idempotent Ingestion & Duplicate Prevention
    # -----------------------------------------------------------------------
    def test_idempotent_ingestion_prevents_duplicates(self):
        """Verify rerunning ingestion is strictly idempotent without inserting duplicate documents or passages."""
        with sqlite3.connect("data/standards/corpus.db") as conn:
            cur = conn.cursor()
            docs_before = cur.execute("SELECT COUNT(*) FROM corpus_documents").fetchone()[0]
            passages_before = cur.execute("SELECT COUNT(*) FROM corpus_passages").fetchone()[0]

        # Rerun ingestion pipeline
        res = ingest_normative_corpus()

        with sqlite3.connect("data/standards/corpus.db") as conn:
            cur = conn.cursor()
            docs_after = cur.execute("SELECT COUNT(*) FROM corpus_documents").fetchone()[0]
            passages_after = cur.execute("SELECT COUNT(*) FROM corpus_passages").fetchone()[0]

        assert docs_after == docs_before == 11, "Corpus document count must remain invariant"
        assert passages_after == passages_before == 44, "Passage count must remain invariant"
        assert res["relationships_added"] == 0, "No duplicate relationships should be created on rerun"

    # -----------------------------------------------------------------------
    # 4. Acquisition Blocker Recording for Unacquired Sources
    # -----------------------------------------------------------------------
    def test_unacquired_standards_have_zero_fabricated_clauses(self):
        """Verify unacquired standards (e.g. IS 2062) have zero passages in corpus.db."""
        with sqlite3.connect("data/standards/corpus.db") as conn:
            cur = conn.cursor()
            p_2062 = cur.execute("SELECT COUNT(*) FROM corpus_passages WHERE standard_number LIKE '%2062%'").fetchone()[0]
            p_1538 = cur.execute("SELECT COUNT(*) FROM corpus_passages WHERE standard_number LIKE '%1538%'").fetchone()[0]

        assert p_2062 == 0, "Corpus must not contain unverified or fabricated passages for unacquired IS 2062"
        assert p_1538 == 0, "Corpus must not contain unverified or fabricated passages for unacquired IS 1538"

    # -----------------------------------------------------------------------
    # 5. Evidence-Grounded Cross-Reference Traversal
    # -----------------------------------------------------------------------
    def test_cross_reference_traversal_from_grounded_clauses(self):
        """Verify cross-reference traversal correctly extracts citations from grounded clauses with full provenance."""
        # 5a: IS 800 Clause 2.2 references IS 2062 for structural steel materials
        res_800 = self.graph.traverse_cross_references(start_standard="IS 800", grounded_clause="2.2", max_depth=1)
        targets_800 = [r.target_standard for r in res_800]
        assert any("2062" in t for t in targets_800), "IS 800 Clause 2.2 must reference IS 2062"

        ref_2062 = next(r for r in res_800 if "2062" in r.target_standard)
        assert ref_2062.originating_clause == "2.2"
        assert "IS 2062" in ref_2062.originating_evidence
        assert ref_2062.relationship_type == "NORMATIVE_REFERENCE"
        assert ref_2062.provenance == "VERIFIED"

        # 5b: IS 14846 Clause 6.1 references IS 210 and IS 318
        res_14846 = self.graph.traverse_cross_references(start_standard="IS 14846", grounded_clause="6.1", max_depth=1)
        targets_14846 = [r.target_standard for r in res_14846]
        assert any("210" in t for t in targets_14846), "IS 14846 Clause 6.1 must reference IS 210 (cast iron)"
        assert any("318" in t for t in targets_14846), "IS 14846 Clause 6.1 must reference IS 318 (bronze rings)"

        # 5c: IS 1239 (Part 2) Clause 1.1 references IS 1239 (Part 1) and Clause 7.1 references IS 554
        res_1239 = self.graph.traverse_cross_references(start_standard="IS 1239 (Part 2)", max_depth=1)
        targets_1239 = [r.target_standard for r in res_1239]
        assert any("554" in t for t in targets_1239), "IS 1239 (Part 2) must reference IS 554 (pipe threads)"

    # -----------------------------------------------------------------------
    # 6. Cycle Prevention, Depth Bounds, and Deduplication
    # -----------------------------------------------------------------------
    def test_traversal_cycle_prevention_and_depth_limits(self):
        """Verify cycle prevention avoids infinite loops, deduplicates results, and rejects invalid depth."""
        # Cycle test: IS 269 <-> IS 8112
        res_d2 = self.graph.traverse_cross_references("IS 269", grounded_clause="5.1", max_depth=2, max_results=15)
        stds = [r.target_standard for r in res_d2]

        # No duplicate standard identifiers
        assert len(stds) == len(set(stds)), "Traversed standards list must contain zero duplicates"
        assert "IS-269" not in stds and "IS 269" not in stds, "Originating standard must not appear in traversed results"

        # Depth bounds enforcement: depth must be 1 or 2
        with pytest.raises(ValueError, match="depth must be between 1 and 2"):
            self.graph.traverse_cross_references("IS 800", max_depth=3)

        with pytest.raises(ValueError, match="depth must be between 1 and 2"):
            self.graph.traverse_cross_references("IS 800", max_depth=0)

    # -----------------------------------------------------------------------
    # 7. Lifecycle Awareness for Referenced Standards
    # -----------------------------------------------------------------------
    def test_lifecycle_awareness_in_traversal(self):
        """Verify traversed standards accurately reflect their catalogue lifecycle status."""
        res = self.graph.traverse_cross_references("IS 14846", max_depth=1, max_results=10)
        
        # Check active vs withdrawn/superseded resolution
        status_map = {r.target_standard: r.lifecycle_status for r in res}
        
        # Any superseded standard must have is_active = False
        for r in res:
            if r.lifecycle_status in ("Withdrawn", "Superseded"):
                assert r.is_active is False
            elif r.lifecycle_status == "Active":
                assert r.is_active is True

    # -----------------------------------------------------------------------
    # 8. Contextual Relevance Filtering Against Tender Requirements
    # -----------------------------------------------------------------------
    def test_contextual_relevance_filtering(self):
        """Verify contextual relevance flag is set when tender mentions governing activity."""
        # Tender mentions pipe threads
        tender_threads = "Mild steel threaded pipe fittings with pipe threads conforming to standard specifications."
        res_threads = self.graph.traverse_cross_references(
            start_standard="IS 1239 (Part 2)",
            max_depth=1,
            tender_context=tender_threads
        )
        ref_554 = next((r for r in res_threads if "554" in r.target_standard), None)
        assert ref_554 is not None
        assert ref_554.is_contextually_relevant is True
        assert "554" in ref_554.relevance_reason or "domain" in ref_554.relevance_reason.lower()

    # -----------------------------------------------------------------------
    # 9. Safety Invariant: Graph Connectivity NEVER Substitutes for Clause Evidence
    # -----------------------------------------------------------------------
    def test_graph_connectivity_never_causes_false_clause_verified(self):
        """Verify that traversing to a related standard without corpus passages does NOT verify it."""
        # IS 2062 is a normative reference of IS 800, but has zero passages in corpus.db
        req = extract_from_text("Supply of hot rolled structural steel sections conforming to IS 2062:2011.")
        res = self.recommender.recommend_for_requirement(req)

        # Must NOT be CLAUSE_VERIFIED because IS 2062 has no local corpus passage
        assert res.verification_tier != "CLAUSE_VERIFIED"
        assert res.verification_tier in ("CATALOGUE_DISCOVERED", "SAFE_ABSTENTION")
        assert res.passage_id is None

    # -----------------------------------------------------------------------
    # 10. Compound Requirement Evidence Isolation
    # -----------------------------------------------------------------------
    def test_compound_requirement_evidence_isolation(self):
        """Verify compound tender requirements citing distinct standards isolate evidence per component."""
        compound_text = (
            "Supply of mild steel socket pipe fittings conforming to IS 1239 (Part 2) "
            "and cast iron sluice valves conforming to IS 14846 for water distribution."
        )
        req = extract_from_text(compound_text)
        res = self.recommender.recommend_for_requirement(req)

        # Both standards must be represented across recommendations / components
        all_stds = [str(r.standard_number or "") for r in res.recommendations]
        for cr in (res.component_recommendations or []):
            all_stds.append(str(cr.get("candidate_standard") or ""))

        has_1239_p2 = any("1239" in s and "2" in s for s in all_stds)
        has_14846 = any("14846" in s for s in all_stds)
        assert has_1239_p2 and has_14846, f"Expected both IS 1239 (Part 2) and IS 14846, found {all_stds}"

        # Evidence isolation: fittings component must NOT cite sluice valves
        for cr in (res.component_recommendations or []):
            c_std = str(cr.get("candidate_standard") or "")
            c_text = str(cr.get("component_text") or "").lower()
            if "1239" in c_std:
                assert "valve" not in c_text
            elif "14846" in c_std:
                assert "fitting" not in c_text

    # -----------------------------------------------------------------------
    # 11. Ground Truth Benchmark Bit-for-Bit Integrity
    # -----------------------------------------------------------------------
    def test_ground_truth_file_checksum_invariant(self):
        """Verify frozen ground-truth dataset has not been modified or corrupted."""
        gt_path = "dataset/ground_truth/ground_truth.csv"
        assert os.path.exists(gt_path), "Ground truth file missing"
        with open(gt_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()

        expected = "8bcc9bc59b8cc69f418626325238fc9f0be24429950a9f78a736177c086e3cfc"
        assert digest == expected, f"Ground truth checksum mismatch! Expected {expected}, got {digest}"
