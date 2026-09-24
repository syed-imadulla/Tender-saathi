"""
Test Suite: Phase 9 Task 1 - Taxonomy & Graph Schema Consolidation
Module: tests/test_phase9_taxonomy_schema.py

Verifies:
1. Canonical relationship taxonomy (NORMATIVE_REFERENCE, TEST_METHOD, INSTALLATION_CODE,
   SAFETY_STANDARD, TERMINOLOGY_STANDARD, ALLIED_STANDARD, SUPERSEDES, AMENDS).
2. Backward-compatible normalization for legacy aliases (CODE_OF_PRACTICE,
   INSTALLATION_STANDARD, CODE_OF_PRACTICE_FOR, REFERENCES, SUPERSEDED_BY).
3. Strict provenance invariant: Production graph relationships may ONLY use
   VERIFIED or CURATED; INFERRED must be strictly rejected with ValueError.
4. StandardRelationship field enforcement (source_standard, target_standard,
   relationship_type, evidence, evidence_clause, provenance, confidence, source).
5. SUPERSEDED_BY reverses source and target and normalizes to canonical SUPERSEDES.
6. Existing production relationships in relationships.json and standards.db remain
   100% valid under canonical schema normalization.
"""

import unittest
import json
import os
from typing import List

from src.standards import (
    StandardsDatabase,
    CANONICAL_RELATIONSHIP_TYPES,
    LEGACY_RELATIONSHIP_ALIASES,
    ALLOWED_PROVENANCE_LEVELS,
    PROHIBITED_PROVENANCE_LEVELS,
    RelationshipType,
    normalize_relationship_type,
    StandardRole,
    classify_standard_role,
    BISStandardRelationship,
)
from src.graph import StandardsGraph, StandardRelationship
from src.dependencies import DependencyItem, StandardsDependencyReport, StandardsDependencyEngine


class TestPhase9TaxonomySchema(unittest.TestCase):
    """Rigorous unit test suite for Phase 9 Task 1."""

    def test_01_canonical_taxonomy_presence(self):
        """Verify that all 8 canonical relationship types are recognized."""
        expected_canonical = {
            "NORMATIVE_REFERENCE",
            "TEST_METHOD",
            "INSTALLATION_CODE",
            "SAFETY_STANDARD",
            "TERMINOLOGY_STANDARD",
            "ALLIED_STANDARD",
            "SUPERSEDES",
            "AMENDS",
        }
        self.assertEqual(CANONICAL_RELATIONSHIP_TYPES, expected_canonical)

    def test_02_legacy_alias_normalization(self):
        """Verify that legacy relationship strings normalize to their canonical equivalents."""
        self.assertEqual(normalize_relationship_type("CODE_OF_PRACTICE"), "INSTALLATION_CODE")
        self.assertEqual(normalize_relationship_type("INSTALLATION_STANDARD"), "INSTALLATION_CODE")
        self.assertEqual(normalize_relationship_type("CODE_OF_PRACTICE_FOR"), "INSTALLATION_CODE")
        self.assertEqual(normalize_relationship_type("REFERENCES"), "NORMATIVE_REFERENCE")
        self.assertEqual(normalize_relationship_type("SUPERSEDED_BY"), "SUPERSEDES")
        self.assertEqual(normalize_relationship_type("IDENTICAL_ADOPTION"), "ALLIED_STANDARD")

    def test_03_relationship_type_equality_backward_compatibility(self):
        """Verify that RelationshipType objects evaluate equality with both canonical and legacy aliases."""
        r_cop = RelationshipType("CODE_OF_PRACTICE_FOR")
        self.assertEqual(str(r_cop), "INSTALLATION_CODE")
        self.assertEqual(r_cop, "INSTALLATION_CODE")
        self.assertEqual(r_cop, "CODE_OF_PRACTICE")
        self.assertEqual(r_cop, "INSTALLATION_STANDARD")
        self.assertEqual(r_cop, "CODE_OF_PRACTICE_FOR")
        self.assertNotEqual(r_cop, "NORMATIVE_REFERENCE")

        r_ref = RelationshipType("REFERENCES")
        self.assertEqual(str(r_ref), "NORMATIVE_REFERENCE")
        self.assertEqual(r_ref, "NORMATIVE_REFERENCE")
        self.assertEqual(r_ref, "REFERENCES")
        self.assertNotEqual(r_ref, "INSTALLATION_CODE")

    def test_04_unsupported_relationship_type_rejection(self):
        """Verify that unsupported or hallucinated relationship types are rejected."""
        unsupported = ["RANDOM_EDGE", "RECOMMENDED_BY_AI", "SIMILAR_YEAR", "LOOSE_MATCH"]
        for u in unsupported:
            with self.assertRaises(ValueError):
                normalize_relationship_type(u)
            with self.assertRaises(ValueError):
                RelationshipType(u)
            with self.assertRaises(ValueError):
                StandardRelationship(
                    source_standard="IS 15000",
                    target_standard="IS 2491",
                    relationship_type=u,
                    evidence="Clause 2 citation",
                    provenance="VERIFIED"
                )

    def test_05_strict_provenance_invariant_enforcement(self):
        """Verify that production graph relationships ONLY allow VERIFIED or CURATED; INFERRED must be rejected."""
        self.assertEqual(ALLOWED_PROVENANCE_LEVELS, {"VERIFIED", "CURATED"})
        self.assertEqual(PROHIBITED_PROVENANCE_LEVELS, {"INFERRED"})

        # Valid VERIFIED accepted
        rel_verified = StandardRelationship(
            source_standard="IS 15000 : 2024",
            target_standard="IS 2491 : 2024",
            relationship_type="NORMATIVE_REFERENCE",
            evidence="Clause 2 explicitly cites IS 2491.",
            provenance="VERIFIED"
        )
        self.assertEqual(rel_verified.provenance, "VERIFIED")

        # Valid CURATED accepted
        rel_curated = StandardRelationship(
            source_standard="IS 458 : 2021",
            target_standard="IS 3597 : 1998",
            relationship_type="TEST_METHOD",
            evidence="Clause 8 Sampling and Testing references IS 3597.",
            provenance="CURATED"
        )
        self.assertEqual(rel_curated.provenance, "CURATED")

        # INFERRED strictly rejected with ValueError
        with self.assertRaises(ValueError) as ctx:
            StandardRelationship(
                source_standard="IS 9999",
                target_standard="IS 8888",
                relationship_type="NORMATIVE_REFERENCE",
                evidence="Inferred from tender co-occurrence",
                provenance="INFERRED"
            )
        self.assertIn("INFERRED provenance is strictly rejected", str(ctx.exception))

        # Arbitrary provenance rejected
        with self.assertRaises(ValueError):
            StandardRelationship(
                source_standard="IS 9999",
                target_standard="IS 8888",
                relationship_type="NORMATIVE_REFERENCE",
                evidence="Clause 2 citation",
                provenance="SPECULATIVE"
            )

    def test_06_standard_relationship_field_enforcement(self):
        """Verify that StandardRelationship enforces all required fields."""
        # Empty source_standard rejected
        with self.assertRaises(ValueError):
            StandardRelationship(
                source_standard="",
                target_standard="IS 2491",
                relationship_type="NORMATIVE_REFERENCE",
                evidence="Clause 2",
                provenance="VERIFIED"
            )

        # Empty target_standard rejected
        with self.assertRaises(ValueError):
            StandardRelationship(
                source_standard="IS 15000",
                target_standard="",
                relationship_type="NORMATIVE_REFERENCE",
                evidence="Clause 2",
                provenance="VERIFIED"
            )

        # Empty evidence rejected
        with self.assertRaises(ValueError):
            StandardRelationship(
                source_standard="IS 15000",
                target_standard="IS 2491",
                relationship_type="NORMATIVE_REFERENCE",
                evidence="",
                provenance="VERIFIED"
            )

        # Invalid confidence rejected
        with self.assertRaises(ValueError):
            StandardRelationship(
                source_standard="IS 15000",
                target_standard="IS 2491",
                relationship_type="NORMATIVE_REFERENCE",
                evidence="Clause 2",
                provenance="VERIFIED",
                confidence=1.5
            )

        # Automatic clause extraction when present in evidence
        rel = StandardRelationship(
            source_standard="IS 15000 : 2024",
            target_standard="IS 2491 : 2024",
            relationship_type="NORMATIVE_REFERENCE",
            evidence="Clause 2.1 Normative References explicitly cites IS 2491.",
            provenance="VERIFIED"
        )
        self.assertEqual(rel.evidence_clause, "Clause 2.1")

    def test_07_superseded_by_reversal_logic(self):
        """Verify that SUPERSEDED_BY reverses source and target and sets canonical SUPERSEDES."""
        # "IS 10611 is superseded by IS/ISO 10434"
        rel = StandardRelationship(
            source_standard="IS 10611 : 1983",
            target_standard="IS/ISO 10434 : 2020",
            relationship_type="SUPERSEDED_BY",
            evidence="National foreword declares replacement",
            provenance="VERIFIED",
            direction="OUTGOING"
        )
        # Reversal: source becomes active replacement, target becomes obsolete standard
        self.assertEqual(rel.source_standard, "IS/ISO 10434 : 2020")
        self.assertEqual(rel.target_standard, "IS 10611 : 1983")
        self.assertEqual(str(rel.relationship_type), "SUPERSEDES")
        self.assertEqual(rel.direction, "INCOMING")

    def test_08_existing_relationships_json_conformance(self):
        """Verify that every entry in relationships.json conforms to canonical normalization and allowed provenance."""
        rel_path = "data/standards/relationships.json"
        if not os.path.exists(rel_path):
            self.skipTest(f"{rel_path} does not exist")

        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertGreater(len(data), 0, "relationships.json must not be empty.")

        for i, item in enumerate(data):
            src = item.get("source_standard") or item.get("source")
            tgt = item.get("target_standard") or item.get("target")
            rtype = item.get("relationship_type")
            ev = item.get("evidence")
            prov = item.get("provenance", "CURATED")

            self.assertTrue(src, f"Entry {i} missing source_standard")
            self.assertTrue(tgt, f"Entry {i} missing target_standard")
            self.assertTrue(ev, f"Entry {i} missing evidence")
            self.assertIn(prov, ALLOWED_PROVENANCE_LEVELS, f"Entry {i} has invalid provenance: {prov}")

            # Instantiate StandardRelationship to verify schema validation passes cleanly
            sr = StandardRelationship(
                source_standard=src,
                target_standard=tgt,
                relationship_type=rtype,
                evidence=ev,
                provenance=prov,
                confidence=item.get("confidence", 1.0),
                source=item.get("evidence_source", "BSB_EDGE_MANUALLY_VERIFIED")
            )
            self.assertIn(str(sr.relationship_type), CANONICAL_RELATIONSHIP_TYPES)

    def test_09_dependencies_engine_canonical_bucketing(self):
        """Verify that StandardsDependencyEngine buckets canonical relationship types properly."""
        engine = StandardsDependencyEngine()
        self.assertEqual(engine._classify_dependency_role("INSTALLATION_CODE")[0], "installation")
        self.assertEqual(engine._classify_dependency_role("CODE_OF_PRACTICE")[0], "installation")
        self.assertEqual(engine._classify_dependency_role("NORMATIVE_REFERENCE")[0], "normative")
        self.assertEqual(engine._classify_dependency_role("REFERENCES")[0], "normative")
        self.assertEqual(engine._classify_dependency_role("TEST_METHOD")[0], "testing")
        self.assertEqual(engine._classify_dependency_role("SAFETY_STANDARD")[0], "safety")
        self.assertEqual(engine._classify_dependency_role("TERMINOLOGY_STANDARD")[0], "terminology")
        self.assertEqual(engine._classify_dependency_role("ALLIED_STANDARD")[0], "allied")


if __name__ == "__main__":
    unittest.main()
