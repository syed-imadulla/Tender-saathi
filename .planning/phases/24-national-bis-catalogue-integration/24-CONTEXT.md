# Phase 24 Context: National BIS Catalogue Integration

## Background & Intent
Phase 24 (Phase 1 of the BIS Coverage Roadmap) resolves the architectural disconnect between the national bulk catalogue (`data/catalogue/bis_catalogue.db`, 35,208 records) and the tender recommendation engine. Previously, `src/validate.py` validated cited standards solely against `data/standards/standards.db` (90 records), resulting in valid Indian Standards (such as `IS 8112`, `IS 1489`, `IS 10000`, `IS 10245`) being falsely flagged as `NONEXISTENT_CITATION`.

## Locked Decisions
1. **Primary Citation Authority:**
   - Resolve explicit standard citations against `data/catalogue/bis_catalogue.db` (`catalogue_standards` table).
   - If a standard is also present in `data/standards/standards.db`, its rich scope text, technical notes, and verified relationships take precedence for candidate evaluation.
2. **Four-Tier Lifecycle & Recognition Status:**
   - `FOUND_ACTIVE`: Published active standard in the national catalogue.
   - `FOUND_WITHDRAWN_OR_SUPERSEDED`: Withdrawn or superseded standard in the national catalogue.
   - `FOUND_STATUS_UNKNOWN`: Present in the national catalogue, but lifecycle status is unclassified.
   - `NOT_FOUND`: Standard is absent from both the national catalogue and the curated dataset.
3. **Ambiguity & Edition Handling:**
   - Where a tender query cites a base standard number matching multiple historical editions (e.g. `IS 2712 : 1998` Withdrawn vs `IS 2712 : 2024`), prefer the latest active/non-withdrawn edition while attaching an explicit `EDITION_AMBIGUITY_REVIEW` notice listing all known editions.
   - Robust identifier normalization handling parentheses, spaces, and `-Part-` tokens (e.g. `IS 7098 (Part 1)`, `IS-7098-(Part-1)-1988`, `IS/IEC 61439-3`).
4. **Catalogue-Only Candidate Presentation:**
   - Surface valid catalogue-only citations as a validated candidate (`VALIDATED_NATIONAL_CITATION`) with official metadata (Standard Number, Official Title, Publication Year, Technical Committee, Department, Status, Source URL).
   - Strictly mark evidence as `UNINDEXED_IN_SEMANTIC_CORPUS` and applicability as `PENDING_TECHNICAL_EVALUATION`.
   - Never fabricate clause text, test thresholds, or relationships.
5. **Safety Invariants:**
   - Zero modifications to recommendation thresholds or ranking weights for existing curated standards.
   - The frozen benchmark ground truth (`dataset/ground_truth/ground_truth.csv`, SHA-256 `8bcc9bc5...`) must remain bit-for-bit identical.
