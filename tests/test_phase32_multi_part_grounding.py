"""Tests for Phase 32: Multi-Part Standard Grounding & Physical Source Acquisition Readiness.

Validates the 7 representative end-to-end fixtures required by Phase 32:
1. Exact single-part standard reference (IS 1239 Part 1).
2. Ambiguous bare multi-part citation with no discriminating keywords (IS 1239).
3. Product-directed multi-part resolution (tubes -> Part 1, fittings -> Part 2).
4. Compound requirement citing multiple distinct standards without evidence blending.
5. Catalogue-only standard with no usable normative passages (IS 1239 Part 2).
6. Withdrawn/superseded standard citation (IS 2062:2011).
7. Out-of-scope ceiling parameter verification (IS 1239 Part 1 with 400 mm bore).
"""

from __future__ import annotations

import sqlite3
import pytest
from src.extract import extract_from_text
from src.recommend import StandardsRecommender


class TestPhase32MultiPartGrounding:
    """Deterministic regression test suite for multi-part standard grounding and safety invariants."""

    @pytest.fixture(autouse=True)
    def setup_recommender(self):
        self.recommender = StandardsRecommender()

    def test_fixture_1_exact_single_part_grounding(self):
        """Fixture 1: Exact single-part reference resolves to canonical part and verifies when supported."""
        text = "Mild steel tubes conforming to IS 1239 (Part 1) with nominal bore 50 mm medium grade."
        req = extract_from_text(text)

        res = self.recommender.recommend_for_requirement(req)

        # Must preserve exact canonical standard number with part
        assert "IS 1239 (Part 1)" in res.candidate_standard
        assert res.status == "Active"
        assert res.verification_tier == "CLAUSE_VERIFIED"
        assert not res.human_review_required
        assert res.clause_number == "1.1"
        assert res.passage_id is not None

    def test_fixture_2_ambiguous_bare_multipart_citation(self):
        """Fixture 2: Ambiguous bare multi-part citation without discriminating context flags review."""
        text = "Supplied structural and piping material conforming to IS 1239 strictly as per tender specs."
        req = extract_from_text(text)

        res = self.recommender.recommend_for_requirement(req)

        # Must flag human review required and not arbitrarily claim CLAUSE_VERIFIED
        assert res.verification_tier in ("SAFE_ABSTENTION", "CATALOGUE_DISCOVERED")
        assert res.human_review_required is True
        assert "AMBIGUOUS_MULTI_PART_CITATION" in res.reason or "Multiple distinct parts exist" in res.reason

    def test_fixture_3_product_directed_multipart_resolution(self):
        """Fixture 3: Product keywords disambiguate bare multi-part standard mentions."""
        # 3a: Tubes -> Part 1
        tube_text = "Mild steel tubes conforming to IS 1239 with nominal bore 25 mm."
        tube_req = extract_from_text(tube_text)
        tube_res = self.recommender.recommend_for_requirement(tube_req)
        assert "IS 1239 (Part 1)" in tube_res.candidate_standard

        # 3b: Pipe fittings -> Part 2
        fittings_text = "Mild steel pipe fittings and wrought steel elbows conforming to IS 1239."
        fittings_req = extract_from_text(fittings_text)
        fittings_res = self.recommender.recommend_for_requirement(fittings_req)
        assert "IS 1239 (Part 2)" in fittings_res.candidate_standard

    def test_fixture_4_compound_requirement_isolation(self):
        """Fixture 4: Compound requirement citing multiple standards isolates evidence per component."""
        text = (
            "Piping work requires mild steel tubes conforming to IS 1239 (Part 1) "
            "and cast iron sluice valves conforming to IS 14846."
        )
        req = extract_from_text(text)
        res = self.recommender.recommend_for_requirement(req)

        # Both standards must be represented in recommendations or component recommendations
        rec_standards = [r.standard_number for r in res.recommendations]
        comp_standards = [c.get("candidate_standard", "") for c in (res.component_recommendations or [])]
        all_stds = rec_standards + comp_standards

        has_is1239 = any("1239" in s for s in all_stds)
        has_is14846 = any("14846" in s for s in all_stds)
        assert has_is1239 and has_is14846

        # Evidence isolation: tubes standard must not point to sluice valves
        for cr in (res.component_recommendations or []):
            c_std = cr.get("candidate_standard", "")
            c_text = cr.get("component_text", "").lower()
            if "1239" in c_std:
                assert "valve" not in c_text
            elif "14846" in c_std:
                assert "tube" not in c_text and "pipe" not in c_text

    def test_fixture_5_catalogue_only_standard_never_clause_verified(self):
        """Fixture 5: A standard known only through catalogue metadata (IS 1239 Part 2) cannot be CLAUSE_VERIFIED."""
        text = "Mild steel pipe fittings conforming to IS 1239 (Part 2) : 1992."
        req = extract_from_text(text)
        res = self.recommender.recommend_for_requirement(req)

        assert "IS 1239 (Part 2)" in res.candidate_standard
        assert res.verification_tier == "CATALOGUE_DISCOVERED"
        assert res.verification_tier != "CLAUSE_VERIFIED"
        assert res.passage_id is None
        assert res.clause_number is None

    def test_fixture_6_withdrawn_superseded_citation_safety(self):
        """Fixture 6: Withdrawn standard citation (IS 2062:2011) generates explicit warning and review required."""
        text = "Structural steel sections conforming to IS 2062:2011."
        req = extract_from_text(text)
        res = self.recommender.recommend_for_requirement(req)

        assert res.verification_tier == "SAFE_ABSTENTION"
        assert res.human_review_required is True
        assert "WITHDRAWN" in res.reason

    def test_fixture_7_out_of_scope_ceiling_parameter(self):
        """Fixture 7: Parameter exceeding standard scope ceiling (e.g. 400 mm for IS 1239 Part 1) is not verified."""
        text = "Mild steel tubes conforming to IS 1239 (Part 1) with nominal bore 400 mm."
        req = extract_from_text(text)
        res = self.recommender.recommend_for_requirement(req)

        # Scope of IS 1239 (Part 1) is up to and including 150 mm nominal bore
        assert res.verification_tier != "CLAUSE_VERIFIED"
        assert res.verification_tier in ("SAFE_ABSTENTION", "CATALOGUE_DISCOVERED")


class TestSourceAcquisitionReadiness:
    """Verifies physical source acquisition audit rules and blockers."""

    def test_no_synthetic_clauses_for_unacquired_sources(self):
        """Confirms that unacquired sources (e.g. IS 2062) have zero unverified passages in corpus,
        and acquired sources (IS 1239 Part 2) only contain verified authentic passages."""
        conn = sqlite3.connect("data/standards/corpus.db")
        cursor = conn.cursor()

        # Check for any passages asserting unacquired IS 2062
        cursor.execute("SELECT COUNT(*) FROM corpus_passages WHERE standard_number LIKE '%2062%'")
        is2062_count = cursor.fetchone()[0]
        assert is2062_count == 0, "Corpus must not contain fabricated passages for unacquired IS 2062"

        # Check that IS 1239 Part 2 passages acquired in Phase 33 are strictly authentic CLAUSE_IDENTIFIER_VERIFIED
        cursor.execute("SELECT COUNT(*) FROM corpus_passages WHERE standard_number LIKE '%1239%Part 2%' AND verification_state != 'CLAUSE_IDENTIFIER_VERIFIED'")
        unverified_part2 = cursor.fetchone()[0]
        assert unverified_part2 == 0, "All IS 1239 Part 2 passages must have authentic CLAUSE_IDENTIFIER_VERIFIED provenance"
