# Milestone 10: Standards Dependency & Coverage Analysis Report

## Executive Summary

- **Tenders Analyzed**: 20 real CPPP tenders
- **Requirements Evaluated**: 72
- **Direct Standards Recommended**: 68
- **Standards Dependencies Identified**: 215
  - Normative References: 176
  - Testing Standards: 6
  - Installation Standards: 9
  - Allied / Related Standards: 24
- **Potential Standards Gaps**: 17
- **Verified Missing Standards**: 0
- **Items Flagged for Human Review**: 237
- **False-Positive Dependency Findings**: 0 (governed by deterministic graph & evidence level)

## Tender Breakdown

| Tender ID | Reqs | Direct Stds | Dependencies | Potential Gaps | Verified Gaps | Review Items | Cited in Tender |
|-----------|------|-------------|--------------|----------------|---------------|--------------|-----------------|
| T001 | 5 | 5 | 7 | 2 | 0 | 6 | 0 |
| T002 | 4 | 4 | 75 | 0 | 0 | 78 | 0 |
| T003 | 4 | 3 | 3 | 0 | 0 | 4 | 0 |
| T004 | 6 | 6 | 2 | 0 | 0 | 6 | 0 |
| T005 | 4 | 4 | 0 | 0 | 0 | 3 | 0 |
| T006 | 5 | 4 | 7 | 1 | 0 | 7 | 0 |
| T007 | 4 | 3 | 2 | 0 | 0 | 6 | 0 |
| T008 | 4 | 4 | 75 | 0 | 0 | 78 | 0 |
| T009 | 2 | 2 | 2 | 0 | 0 | 2 | 0 |
| T010 | 2 | 2 | 14 | 2 | 0 | 14 | 0 |
| T011 | 2 | 2 | 0 | 0 | 0 | 2 | 0 |
| T012 | 6 | 6 | 0 | 0 | 0 | 3 | 0 |
| T013 | 6 | 6 | 6 | 0 | 0 | 10 | 0 |
| T014 | 3 | 3 | 4 | 2 | 0 | 5 | 0 |
| T015 | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| T016 | 2 | 2 | 1 | 0 | 0 | 2 | 0 |
| T017 | 3 | 3 | 6 | 4 | 0 | 4 | 0 |
| T018 | 2 | 2 | 1 | 0 | 0 | 2 | 0 |
| T019 | 2 | 2 | 1 | 0 | 0 | 1 | 0 |
| T020 | 4 | 3 | 9 | 6 | 0 | 4 | 0 |

## Methodological Guardrails

1. **Zero Hallucinated Standards**: Dependencies originate solely from verified BIS normative references, codes of practice, or curated standards relationships (`relationships.json` + `standards.db`).
2. **Separation of Relatedness vs. Applicability**: A referenced standard is flagged as a potential dependency for human review, never automatically declared legally mandatory.
3. **Separation of Specification Gaps vs. Standards Gaps**: Parameter omissions (e.g. pressure class, schedule) are strictly classified as `SPECIFICATION_GAP`, distinct from `STANDARD_GAP`.
