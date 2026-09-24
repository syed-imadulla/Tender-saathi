# System Limitations & Boundary Conditions

This document transparently describes the known limitations, operational boundaries, and non-goals of **Tender Saathi**.

---

## 1. Scope & Operational Non-Goals

Tender Saathi is an AI-assisted standards recommendation and audit assistant for procurement officials and bidders. It is designed to assist technical evaluation by identifying relevant Indian Standards, detecting obsolete citations, and flagging technical ambiguities.

It is **NOT**:
1. **A Legal Certification Authority**: Tender Saathi recommendations do not constitute statutory certification or legal tender compliance guarantees.
2. **A Structural or Electrical Simulation Tool**: The system does not verify whether an engineering design physically complies with stress, load, or voltage limits.
3. **An Automated Procurement Decision Maker**: All high-risk, ambiguous, or superseded recommendations are surfaced to human reviewers for final sign-off.

---

## 2. Catalogue Boundary Limitations

### BIS Catalogue Coverage
- The system indexes **35,208 BIS catalogue records** containing titles, department codes, committee IDs, ICS codes, and status metadata.
- Deep full-text section grounding is available for prioritized core civil, electrical, mechanical, and safety standards. Standards outside this core set rely on title, abstract, keyword, and committee metadata for initial retrieval.

### Multi-Domain Regulatory Interfacing
- When tender requirements blend equipment manufacturing standards with statutory hygiene or electrical safety regulations, domain-boundary trade-offs occur.
- *Case in Point (`ADV-MUL-005`)*: In commercial kitchen specifications combining food grinding equipment with hygiene protocols, the engine surfaces mandatory statutory hygiene regulations (`FSSAI Schedule 4`) rather than purely equipment manufacturing standards (`IS 302` or `IS 2491`). The engine safely downgrades confidence to `Low` and routes the requirement to the human review queue.

---

## 3. Document Extraction & OCR Boundaries

### Scanned PDFs and Complex Layouts
- **Native Digital PDFs**: High fidelity extraction with font-size hierarchy, header/clause detection, and section preservation.
- **Scanned PDFs**: Fallback to local Tesseract OCR. Highly degraded documents, low-resolution scans (<150 DPI), skewed pages, or handwritten annotations will degrade parameter extraction accuracy.
- **Complex Multi-Column Tables**: While basic tabular specs are parsed, highly nested tables with merged cells across multiple pages may split technical parameters into fragmented requirements.

### Non-Textual Assets
- Engineering drawings, CAD diagrams, schematics, and photographic appendices are not analyzed by the text extraction pipeline.

---

## 4. Relationship Graph Traversal Bounds

### Strict Depth-1 Horizon
- To prevent unbounded transitive association drift (e.g. Rebar -> Concrete -> Cement -> Gypsum -> Mining Safety), relationship graph expansion is strictly bounded to `depth=1`.
- Traversal only occurs along verified, curated edges (`VERIFIED` provenance). Secondary or tertiary relationships must be queried independently.

---

## 5. Conservative Safety Bias (False Abstention Trade-Off)

Tender Saathi is intentionally designed with a conservative safety bias:
- **Zero Hallucination Policy**: If a requirement lacks essential engineering parameters (such as pressure ratings, operating voltage, or material grades), the system marks the state as `INCOMPLETE` or `AMBIGUOUS` and abstains from high-confidence recommendation.
- **Precision vs. Recall in Ambiguity**: The ambiguity detection recall is 100%, with a precision of 14.3%. This means the engine frequently flags borderline requirements for human review rather than risk silently recommending an incorrect standard.

---

## 6. Evaluation Limitations: Lifecycle Trap Catch Rate (60.0%)

In the 70-probe adversarial evaluation suite, the system is evaluated across 14 failure categories and 8 safety metrics:
- **7 of the 8 safety metrics** met their target thresholds.
- The **Lifecycle Trap Catch Rate** scored **60.0% (3/5)** against an aggressive 100% automated catch target.
- In 2 under-determined probes containing legacy revisions, the engine safely routed the requirements to the technical human review queue (`REVIEW_REQUIRED`) rather than asserting an automated replacement code. While safe from an operational standpoint, this conservative routing did not trigger the specific automated replacement flag expected by the test harness.
