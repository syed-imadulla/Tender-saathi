# Phase 13 Context — Expert Ground-Truth Adjudication & Evaluation Calibration

## 1. Executive Intent & Phase Boundary

**Phase Goal**: Establish an auditable, reviewer-ready adjudication workflow for Tender Saathi's ground-truth benchmark, generate review packets for all active benchmark cases ($N=20$) and staged candidate cases ($N=20$), document a standardized adjudication rubric, and enforce strict governance gating preventing unverified machine predictions from masquerading as expert-verified truth.

**Strict Phase Boundary**:
- **Human-Review Frontier**: Software tools, review packet generators, consensus validation, and governance gates are fully implemented in this phase.
- **Stopping Rule**: Execution halts strictly at the human-review boundary. Zero rows in `ground_truth.csv` or `candidates_staging.csv` may be marked `human_verified: TRUE` without real domain experts completing the review packets.

---

## 2. Locked Decisions & Core Conventions

### D-01: Canonical Vocabulary for Adjudication Decisions
Reviewers must adjudicate each requirement into one of five mutually exclusive canonical decisions:
1. `RECOMMEND`: The specification is sufficiently complete to recommend one or more definitive Indian Standards (BIS).
2. `ABSTAIN_UNDER_SPECIFIED`: The requirement is incomplete or vague (missing critical engineering parameters like pressure rating, pipe size, voltage grade, or material chemistry) such that selecting a standard would be speculative.
3. `ABSTAIN_AMBIGUOUS`: The specification describes multiple valid interpretations that map to mutually exclusive standards without clarifying context.
4. `ABSTAIN_CONFLICTING`: The requirement contains internally contradictory specifications (e.g. demanding "PVC pipe as per IS 1239 steel tube specification").
5. `REJECT_INELIGIBLE`: The requirement is outside the scope of Indian Standards procurement (e.g. proprietary software licenses, commercial catering services without BIS relevance, synthetic distractors).

### D-02: Reviewer Roles & Minimum Qualifications
To satisfy `GATE-01` in `docs/data/GROUND_TRUTH_GOVERNANCE.md`, an adjudicator must hold a recognized technical procurement or standards qualification:
- `CPWD_EXECUTIVE_ENGINEER` / `CPWD_ASSISTANT_ENGINEER` (Central Public Works Department)
- `BIS_STANDARDS_OFFICER` / `BIS_SCIENTIST` (Bureau of Indian Standards)
- `MES_MILITARY_ENGINEER` (Military Engineer Services)
- `RAILWAY_SENIOR_SECTION_ENGINEER` (Indian Railways / RDSO)
- `PUBLIC_PROCUREMENT_SPECIALIST` (Certified GeM / DGS&D procurement consultant)

### D-03: Two-Party Consensus Protocol
For a candidate case to transition from `MACHINE_PREDICTED` or `UNVERIFIED_BASELINE` to `EXPERT_VERIFIED`:
1. Two independent qualified reviewers must review the case packet.
2. If both agree on `expected_decision` and applicable standard(s), the case is certified.
3. If a disagreement occurs (e.g. Reviewer A says `RECOMMEND` with IS 458, Reviewer B says `ABSTAIN_UNDER_SPECIFIED`), the packet is escalated to a Senior Adjudicator with both rationales documented.

### D-04: Non-Fabrication Guarantee
No reviewer identities, credentials, timestamps, or verdicts will be generated or mocked. The system delivers 40 review packets in `reports/adjudication_packets/` ready for domain expert distribution.

---

## 3. Plan Decomposition for Phase 13

1. **Plan 13-01: Reviewer Packet Generator & Rubric Specification**
   - Formalize `docs/data/ADJUDICATION_RUBRIC.md` detailing decision rules, mandatory clause evidence, and conflict handling.
   - Build `scripts/generate_adjudication_packets.py` generating structured markdown packets for each tender case.
   - Output 40 reviewer packets: 20 baseline cases (`dataset/ground_truth/ground_truth.csv`) and 20 candidate cases (`dataset/ground_truth/candidates_staging.csv`).

2. **Plan 13-02: Adjudication Ingestion & Consensus Validation Tool**
   - Build `scripts/ingest_adjudication.py` CLI to parse completed reviewer response forms.
   - Enforce schema validation (valid reviewer role, ISO-8601 timestamp, non-empty clause reference, detailed rationale).
   - Enforce two-party consensus logic and detect adjudication conflicts.
   - Provide safe dry-run promotion staging without overwriting active ground truth unless fully validated.

3. **Plan 13-03: Verification, Full-Suite Regression & Expert Handoff**
   - Add unit tests in `tests/test_adjudication_workflow.py` validating packet generation, schema enforcement, and consensus rules.
   - Run the full offline test suite (`pytest tests/`) ensuring 100% pass rate.
   - Re-run `scripts/evaluate_milestone12.py` verifying evaluation report accurately reports 0 expert-verified cases and stratifies baseline metrics.
   - Formally document the Expert Handoff Dossier and halt at the human-review boundary.
