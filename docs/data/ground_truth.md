# Ground Truth & Evaluation Datasets Reference

This document details the human-verified ground-truth dataset and negative-control test cases used to evaluate **Tender Saathi** in [`dataset/ground_truth/`](../../dataset/ground_truth/).

---

## 1. Ground Truth Benchmark (`ground_truth.csv`)

The primary evaluation benchmark is [`dataset/ground_truth/ground_truth.csv`](../../dataset/ground_truth/ground_truth.csv). It contains **20 human-verifiable procurement requirements** extracted directly from real Central Public Procurement Portal (CPPP) government tender documents.

### Key Characteristics:
- **Total Requirements**: 20
- **Scope**: Civil construction, electrical installations, mechanical piping, pumping machinery, and water treatment.
- **Verification**: Each row has been independently audited and confirmed by human engineers against official BIS documentation.

### Field Definitions:

| Column Name | Data Type | Purpose & Description |
| :--- | :--- | :--- |
| `tender_id` | String | Unique tender ID (e.g. `T001` to `T020`) matching `dataset/tender_metadata.csv` |
| `requirement_id` | String | Unique requirement ID (e.g. `T001-R002`) |
| `requirement_text` | String | Verbatim requirement excerpt extracted from the tender PDF |
| `category` | String | Engineering category (`material`, `product_equipment`, `installation_execution`) |
| `source_page` | Integer | Page number in original government tender PDF |
| `explicit_standard` | String | Indian Standard explicitly cited by the buyer (blank if omitted) |
| `applicable_standard` | String | Official BIS code(s) confirmed by human engineers (e.g. `IS 15778 : 2007`) |
| `standard_title` | String | Official title of the applicable standard |
| `standard_status` | String | Status in official gazette (`Active`, `Superseded`, `Withdrawn`) |
| `verification_outcome`| String | `STANDARD_EXPLICIT`, `STANDARD_MISSING`, `STANDARD_WRONG_OR_OUTDATED`, `NEEDS_EXPERT_VERIFICATION` |
| `evidence_snippet` | String | Factual excerpt from the standard confirming technical applicability |
| `confidence` | String | Expected confidence tier (`High`, `Medium`, `Low`) |
| `human_verified` | Boolean | `TRUE` for all 20 benchmark requirements |

---

## 2. Negative Benchmark Controls (`src/evaluate.py`)

To evaluate the **Applicability Gate** and verify that Tender Saathi does not produce false positives on out-of-scope or unrelated requirements, the evaluator defines **5 frozen negative control cases** (`NEG-001` through `NEG-005` in [`src/evaluate.py`](../../src/evaluate.py#L367-L403)):

| ID | Description | Requirement Text | Unrelated Standards to Reject | Target Outcome |
| :--- | :--- | :--- | :--- | :--- |
| `NEG-001` | Crane rail track vs. valve standard | *"Replacement of crane rail track for RMQC crane at dock area..."* | `IS/ISO 10434`, `IS 778`, `IS 14846` | Safe Abstention / Rejection |
| `NEG-002` | Electrical cable vs. food standard | *"Supply and laying of 1.1 kV grade copper conductor armored power cables..."* | `IS 2491`, `IS 15000`, `IS 778` | Rejection of food codes |
| `NEG-003` | Water pump vs. tile standard | *"Procurement of heavy duty submersible slurry pumps for power station..."* | `IS 15622`, `IS 4457`, `IS/ISO 10434`| Rejection of ceramic codes |
| `NEG-004` | Structural steel vs. valve standard | *"Design, fabrication and erection of structural steel roof trusses..."* | `IS/ISO 10434`, `IS 778`, `IS 14846` | Rejection of valve codes |
| `NEG-005` | Gibberish / nonsense requirement | *"xyz abc 123 invalid requirement gibberish text 9999"* | `IS 15778`, `IS 778`, `IS/ISO 10434` | Safe Abstention |

---

## 3. Candidate Standards Audit Table (`candidate_standards.csv`)

[`dataset/ground_truth/candidate_standards.csv`](../../dataset/ground_truth/candidate_standards.csv) logs all 49 candidate standards evaluated during benchmark research, recording both accepted standards and formally rejected candidates with reasons for rejection (e.g. `REJECTED_DIFFERENT_MATERIAL`, `REJECTED_SUPERSEDED`, `REJECTED_DIFFERENT_DOMAIN`).
