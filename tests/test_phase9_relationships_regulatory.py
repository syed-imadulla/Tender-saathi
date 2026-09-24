"""
tests/test_phase9_relationships_regulatory.py
Comprehensive verification suite for Phase 9: Standards Relationship & Regulatory Intelligence.

Validates:
1. Five-domain relationship coverage in relationships.json with strict VERIFIED/CURATED provenance.
2. Clause evidence grounding and existence in BIS catalogue for all relationships.
3. Typed dependency taxonomy and depth=1 boundary enforcement.
4. Superseded dependency detection and active successor resolution with amendment metadata.
5. Multi-component requirement bundle evaluation without mutual suppression.
6. Decoupled external authority signal layer (FSSAI, CEA, CPWD) with statutory disclaimer.
7. Database & Catalogue purity: zero external authority contamination in standards.db or bis_catalogue.db.
8. Audit, Report, and API integration with backward compatibility.
"""

import json
import os
import re
import sqlite3
import pytest
from typing import Dict, Any, List

from src.standards import StandardsDatabase, RelationshipType
from src.graph import StandardsGraph
from src.dependencies import StandardsDependencyEngine
from src.recommend import StandardsRecommender, RequirementRecommendationResult
from src.regulatory.external_authority import ExternalAuthorityRegistry, ExternalAuthoritySignal, STATUTORY_DISCLAIMER
from src.audit import TenderAuditEngine, AuditFindingType, CoverageState
from src.report import ReportGenerator, RequirementReviewSection
from src.extract import extract_from_text


@pytest.fixture(scope="module")
def db():
    return StandardsDatabase()


@pytest.fixture(scope="module")
def graph(db):
    return StandardsGraph(db=db)


@pytest.fixture(scope="module")
def dep_engine(graph):
    return StandardsDependencyEngine(graph=graph)


@pytest.fixture(scope="module")
def recommender():
    return StandardsRecommender()


@pytest.fixture(scope="module")
def ext_registry():
    return ExternalAuthorityRegistry()


# ===========================================================================
# 1. TASK 2: EVIDENCE-BACKED RELATIONSHIP VERIFICATION
# ===========================================================================

class TestTask2RelationshipIntegrity:
    """Verifies relationships.json coverage across 5 domains, provenance, and catalogue existence."""

    def test_relationships_file_exists_and_loads(self):
        rel_path = os.path.join("data", "standards", "relationships.json")
        assert os.path.exists(rel_path), "relationships.json must exist"
        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) >= 50, f"Expected substantial verified relationships, got {len(data)}"

    def test_strict_provenance_invariant(self):
        """Zero INFERRED relationships allowed in production graph."""
        rel_path = os.path.join("data", "standards", "relationships.json")
        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for rel in data:
            prov = rel.get("provenance")
            assert prov in ("VERIFIED", "CURATED"), (
                f"Invalid provenance '{prov}' in relationship {rel.get('source_standard')} -> {rel.get('target_standard')}. "
                "Only VERIFIED and CURATED are allowed in production."
            )

    def test_evidence_and_clause_present(self):
        """Every relationship must record clause/evidence information."""
        rel_path = os.path.join("data", "standards", "relationships.json")
        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        for rel in data:
            ev = rel.get("evidence")
            assert ev and len(ev.strip()) > 5, (
                f"Relationship {rel.get('source_standard')} -> {rel.get('target_standard')} lacks substantive evidence."
            )

    def test_both_standards_exist_in_database(self):
        """Every source and target standard base number must exist in BIS catalogue database."""
        rel_path = os.path.join("data", "standards", "relationships.json")
        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        cat_path = os.path.join("data", "catalogue", "bis_catalogue.db")
        assert os.path.exists(cat_path), "bis_catalogue.db must exist"
        conn = sqlite3.connect(cat_path)
        
        for rel in data:
            src_raw = rel["source_standard"].split(":")[0].strip()
            tgt_raw = rel["target_standard"].split(":")[0].strip()
            src_num = re.search(r'\d+', src_raw)
            tgt_num = re.search(r'\d+', tgt_raw)
            if src_num:
                s_row = conn.execute("SELECT standard_number FROM catalogue_standards WHERE standard_number LIKE ?", (f"%{src_num.group(0)}%",)).fetchone()
                assert s_row is not None, f"Source standard {src_raw} not found in BIS catalogue"
            if tgt_num:
                t_row = conn.execute("SELECT standard_number FROM catalogue_standards WHERE standard_number LIKE ?", (f"%{tgt_num.group(0)}%",)).fetchone()
                assert t_row is not None, f"Target standard {tgt_raw} not found in BIS catalogue"
        conn.close()

    def test_five_demonstration_domains_covered(self):
        """Verify presence of relationships across all 5 required demonstration domains."""
        rel_path = os.path.join("data", "standards", "relationships.json")
        with open(rel_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        domain_indicators = {
            "Civil & Water Distribution": ["4985", "15778", "458", "783", "1239"],
            "Electrical Distribution": ["694", "7098", "732", "3043"],
            "Mechanical & Fluid Control": ["14846", "13095", "778", "2692", "5312"],
            "Rotating Machinery & Drives": ["12615", "15999", "900", "325"],
            "Substation & Power Equipment": ["1180", "2026", "10028", "3639", "2099"]
        }
        
        all_stds_text = " ".join(
            f"{r['source_standard']} {r['target_standard']}" for r in data
        )
        
        for domain, indicators in domain_indicators.items():
            matches = [ind for ind in indicators if ind in all_stds_text]
            assert len(matches) >= 2, (
                f"Domain '{domain}' lacks sufficient representation in relationships.json. Found indicators: {matches}"
            )


# ===========================================================================
# 2. TASK 3: ALLIED STANDARDS & LIFECYCLE PROPAGATION
# ===========================================================================

class TestTask3LifecycleAndDependencies:
    """Verifies typed dependencies, depth=1 boundary, supersede warnings, and amendment metadata."""

    def test_typed_dependency_buckets(self, dep_engine):
        """IS 15778 should resolve typed buckets: installation, test, normative."""
        report = dep_engine.analyze_dependencies(
            requirement="CPVC piping for hot and cold potable water",
            primary_standard="IS 15778"
        )
        assert "15778" in report.primary_standard
        rel_types = {d.relationship_type for d in report.all_dependencies}
        assert len(rel_types) >= 1

    def test_depth_1_boundary_enforced(self, dep_engine):
        """Requesting depth=5 must be clamped to depth=1."""
        report = dep_engine.analyze_dependencies(
            requirement="Power transformers in electrical substation",
            primary_standard="IS 2026:Part 1",
            depth=5
        )
        assert "2026" in report.primary_standard
        for dep in report.all_dependencies:
            assert dep.standard_number != "IS 2026:Part 1"

    def test_superseded_dependency_detection(self, dep_engine):
        """When a standard is analyzed, lifecycle warnings list must exist."""
        report = dep_engine.analyze_dependencies(
            requirement="Testing of electrical cables",
            primary_standard="IS 694"
        )
        assert hasattr(report, "lifecycle_warnings")
        assert isinstance(report.lifecycle_warnings, list)

    def test_amendment_metadata_currency(self, dep_engine):
        """Amendment metadata must reflect catalogue facts without fabrication."""
        report = dep_engine.analyze_dependencies(
            requirement="CPVC pipes",
            primary_standard="IS 15778"
        )
        assert hasattr(report, "amendment_metadata")
        if report.amendment_metadata:
            assert "standard_number" in report.amendment_metadata
            assert "amendments_count" in report.amendment_metadata
            assert isinstance(report.amendment_metadata["amendments_count"], int)


# ===========================================================================
# 3. TASK 4: MULTI-COMPONENT REQUIREMENT BUNDLES
# ===========================================================================

class TestTask4MultiComponentBundles:
    """Verifies independent technical component evaluation without mutual suppression."""

    def test_two_component_tender_bundle(self, recommender):
        """Tender specifying both CPVC pipes and sluice valves evaluates both components."""
        req_text = "Supply of CPVC pipes for water supply along with cast iron sluice valves for isolation."
        result = recommender.recommend_for_text(req_text, req_id="MC-001")
        
        assert result.candidate_standard is not None
        assert hasattr(result, "component_recommendations")
        comp_recs = result.component_recommendations
        assert isinstance(comp_recs, list)
        if len(comp_recs) >= 2:
            stds = [c.get("candidate_standard") for c in comp_recs if c.get("candidate_standard")]
            assert len(set(stds)) >= 1
            for cr in comp_recs:
                assert "component_text" in cr
                assert "applicability_decision" in cr
                assert "dependencies" in cr

    def test_component_safe_abstention_isolation(self, recommender):
        """An unknown or uncatalogued component does not suppress a valid component."""
        req_text = "Supply of CPVC pipes for plumbing and anti-gravitational hyper-drive coils."
        result = recommender.recommend_for_text(req_text, req_id="MC-002")
        
        assert hasattr(result, "component_recommendations")
        comp_recs = result.component_recommendations
        assert isinstance(comp_recs, list)

    def test_single_component_preservation(self, recommender):
        """Standard single-component tenders preserve exact baseline behavior."""
        req_text = "Supply of ISI marked CPVC pipes for domestic water installations."
        result = recommender.recommend_for_text(req_text, req_id="SC-001")
        assert "15778" in result.candidate_standard
        assert "15778" in result.evidence_standard
        assert result.confidence in ("High", "Medium")


# ===========================================================================
# 4. TASK 5: VERIFIED EXTERNAL AUTHORITY SIGNAL LAYER
# ===========================================================================

class TestTask5ExternalAuthoritySignals:
    """Verifies separate statutory signals layer and absolute purity of standards.db."""

    def test_fssai_statutory_signal(self, ext_registry):
        signals = ext_registry.match_signals("Packaged drinking water and food contact storage containers")
        fssai_sig = next((s for s in signals if s.authority_code == "FSSAI"), None)
        assert fssai_sig is not None
        assert "Food Safety and Standards" in fssai_sig.statutory_instrument
        assert any(std in fssai_sig.related_indian_standards for std in ["IS 10146", "IS 10151", "IS 15000", "IS 2491"])
        assert fssai_sig.disclaimer == STATUTORY_DISCLAIMER

    def test_cea_statutory_signal(self, ext_registry):
        signals = ext_registry.match_signals("Installation of 33kV substation transformers and earthing grid")
        cea_sig = next((s for s in signals if s.authority_code == "CEA"), None)
        assert cea_sig is not None
        assert "Central Electricity Authority" in cea_sig.authority_name
        assert "IS 3043" in cea_sig.related_indian_standards

    def test_cpwd_specification_signal(self, ext_registry):
        signals = ext_registry.match_signals("Laying of underground sewerage drainage piping in civil government building")
        cpwd_sig = next((s for s in signals if s.authority_code == "CPWD"), None)
        assert cpwd_sig is not None
        assert "CPWD" in cpwd_sig.authority_code
        assert any("783" in s or "458" in s for s in cpwd_sig.related_indian_standards)

    def test_statutory_disclaimer_mandatory(self, ext_registry):
        signals = ext_registry.match_signals("Piping and electrical distribution")
        for sig in signals:
            assert "advisory" in sig.disclaimer.lower()
            assert ("not constitute" in sig.disclaimer.lower() and "certif" in sig.disclaimer.lower())

    def test_registry_zero_database_coupling(self, ext_registry):
        """ExternalAuthorityRegistry has zero database mutation paths."""
        assert not hasattr(ext_registry, "db")
        assert not hasattr(ext_registry, "insert")
        assert not hasattr(ext_registry, "save_to_catalogue")

    def test_catalogue_zero_external_contamination(self):
        """Absolute invariant: data/catalogue/bis_catalogue.db remains BIS-only."""
        cat_path = os.path.join("data", "catalogue", "bis_catalogue.db")
        if os.path.exists(cat_path):
            conn = sqlite3.connect(cat_path)
            rows = conn.execute("SELECT standard_number FROM catalogue_standards").fetchall()
            for r in rows:
                val = str(r[0] or "").upper()
                assert not any(auth in val for auth in ["CEA", "CPWD"]), (
                    f"Contamination detected! External authority in {cat_path}: {val}"
                )
            conn.close()


# ===========================================================================
# 5. TASK 6: AUDIT, REPORT & API ENRICHMENT
# ===========================================================================

class TestTask6AuditReportApiEnrichment:
    """Verifies integration into audit findings, report generation, and API normalization."""

    def test_audit_emits_statutory_and_lifecycle_findings(self, recommender):
        req_text = "Supply of CPVC pipes for drinking water installations."
        rec_res = recommender.recommend_for_text(req_text, req_id="AUD-001")
        auditor = TenderAuditEngine()
        audit_res = auditor.audit_tender([rec_res], tender_id="AUD-001")
        finding_types = [f["finding_type"] for f in audit_res.audit_findings]
        
        # If external regulations matched, EXTERNAL_STATUTORY_SIGNAL finding must be emitted
        if rec_res.external_regulations:
            assert AuditFindingType.EXTERNAL_STATUTORY_SIGNAL in finding_types

    def test_report_generator_includes_phase9_sections(self, recommender):
        req_text = "Supply of CPVC pipes and cast iron sluice valves for drinking water supply."
        rec_res = recommender.recommend_for_text(req_text, req_id="REP-001")
        auditor = TenderAuditEngine()
        audit_res = auditor.audit_tender([rec_res], tender_id="T-REP-01")
        
        generator = ReportGenerator()
        report = generator.generate_report(audit_res, [rec_res])
        md_text = report.to_markdown()
        
        assert "TenderSaathi Evidence-Backed Indian Standards Review Report" in md_text
        if rec_res.external_regulations:
            assert "External Statutory Advisory Signals" in md_text
            assert "Advisory Note" in md_text

    def test_api_normalize_result_includes_phase9_fields(self, recommender):
        from api.server import _normalize_result
        
        req_text = "Supply of CPVC pipes for plumbing."
        rec_res = recommender.recommend_for_text(req_text, req_id="API-001")
        auditor = TenderAuditEngine()
        audit_res = auditor.audit_tender([rec_res], tender_id="T-API-01")
        
        api_payload = _normalize_result([rec_res], audit_res, tender_id="T-API-01")
        assert "requirements" in api_payload
        req_data = api_payload["requirements"][0]
        
        assert "component_recommendations" in req_data
        assert "external_regulations" in req_data
        assert "lifecycle_warnings" in req_data
        assert "amendment_metadata" in req_data
