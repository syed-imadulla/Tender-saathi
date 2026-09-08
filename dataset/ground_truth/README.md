# Human Ground Truth Dataset (SIH26108)

This directory contains the **human-verified ground truth dataset** for our technical feasibility spike.

Ground truth is the benchmark standard of accuracy against which our proposed AI recommendation engine will be evaluated. While initial candidate requirements were automatically extracted from the tender documents, **ground truth must be validated by human engineers and domain experts**.

---

## 1. Directory Contents

- **`ground_truth.csv`**: The primary ground-truth benchmark containing the 20 selected requirements, candidate/selected standards, verification outcomes, methods, evidence references, and snippets.
- **`candidate_standards.csv`**: Full audit log of all 49 candidate standards evaluated during research, including accepted standards and formally rejected candidates (with reasons for rejection).
- **`README.md`**: This guide.

---

## 2. Column-by-Column Field Guide (`ground_truth.csv`)

| Column Name | Type | Description & Purpose |
|---|---|---|
| `tender_id` | String | Unique identifier of the tender (e.g. `T001`). Matches `dataset/tender_metadata.csv`. |
| `requirement_id` | String | Unique identifier of the requirement (e.g. `T001-R002`). Matches `dataset/tender_requirements.jsonl`. |
| `requirement_text` | String | The exact verbatim text of the procurement requirement extracted from the tender. |
| `category` | String | Technical category (e.g., `material`, `product_equipment`, `installation_execution`, `general_specification`). |
| `source_page` | Integer | The page number in the original PDF where this requirement is located. |
| `explicit_standard` | String | Any standard explicitly cited in the original tender text. Blank if the buyer did not cite any standard. |
| `applicable_standard` | String | The Bureau of Indian Standards code(s) identified for this requirement (e.g., `IS 15778 : 2007; IS 1239 (Part 1) : 2004`). |
| `standard_title` | String | Official title(s) of the applicable standard as listed in the BIS catalogue. |
| `standard_status` | String | Current status of the standard (`Active` or `Withdrawn/Superseded`). |
| **`verification_outcome`** | String | One of: `STANDARD_EXPLICIT`, `STANDARD_MISSING`, `STANDARD_WRONG_OR_OUTDATED`, `NO_CONFIRMED_STANDARD`, `NEEDS_EXPERT_VERIFICATION`. |
| **`verification_method`** | String | One of: `BIS_METADATA`, `BIS_DOCUMENT`, `BIS_CATALOGUE`, `OTHER_OFFICIAL_SOURCE`, `UNVERIFIED`. |
| `evidence_source` | String | Source of evidence (e.g., BIS Catalogue Sectional Committee, Quality Control Order). |
| `evidence_reference` | String | Specific standard clause, scope section, or regulatory reference. |
| **`evidence_snippet`** | String | Factual excerpt showing why the standard applies to this product/material. |
| `reasoning` | String | Plain-language technical justification explaining why this standard governs the requirement. |
| `confidence` | String | `High` (direct authoritative evidence / QCO), `Medium` (strong evidence), or `Low` (needs BOQ verification). |
| **`human_verified`** | Boolean | Remains `FALSE` until the human reviewer inspects the evidence and confirms the row. |
| `reviewer_notes` | String | QCO references, supersession notes, or scope boundaries. |

---

## 3. Candidate Standards Audit Table (`candidate_standards.csv`)

Tracks all candidate standards analyzed, including false positives and rejected options:
- `requirement_id`: Identifier of the requirement.
- `candidate_standard`: The standard analyzed.
- `standard_title`: Official title.
- `why_candidate`: Why it initially appeared relevant.
- `applicability`: `APPLICABLE_PRIMARY`, `APPLICABLE_SECONDARY`, `REJECTED_DIFFERENT_MATERIAL`, `REJECTED_SUPERSEDED`, `REJECTED_DIFFERENT_DOMAIN`, or `AMBIGUOUS_NEEDS_BOQ`.
- `evidence_source`: Source reference.
- `evidence_reference`: Specific scope clause or reason for rejection.
- `selected_as_ground_truth`: `TRUE` or `FALSE`.
