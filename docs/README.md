# Tender Saathi Documentation Index

Welcome to the technical documentation for **Tender Saathi**, an evidence-backed Indian Standards recommendation and technical specification audit engine designed for Indian public procurement (SIH Problem Statement SIH26108).

> **Core Operational Philosophy**: *AI interprets. Rules validate. Evidence supports. Humans decide.*

---

## Documentation Structure

```text
docs/
├── README.md                      # This documentation index
├── architecture/                  # Deep technical design and module specifications
│   ├── overview.md                # 10-stage end-to-end review pipeline
│   ├── modules.md                 # Detailed source module reference (src/ & api/)
│   └── relationship_graph.md      # Standards graph, taxonomy, provenance & depth=1 boundary
├── getting-started/               # Developer setup and operational guides
│   ├── installation.md            # Environment setup (Python virtualenv, Node.js, system deps)
│   ├── configuration.md           # Configuration options, offline mode & environment variables
│   └── run_guide.md               # Starting backend API, frontend UI, tests & benchmarks
├── api/                           # API specifications
│   └── rest_api.md                # Complete REST API reference (12 active endpoints)
├── data/                          # Standards data and catalogue architecture
│   ├── catalogue.md               # Normalized BIS catalogue (35,208 records in bis_catalogue.db)
│   ├── relationships.md           # 72 verified relationships across 5 demonstration domains
│   └── ground_truth.md            # 20-row human-verified ground-truth dataset & candidate logs
├── safety/                        # Trust boundaries, invariants & deterministic guardrails
│   ├── principles.md              # 4 operational principles & 2 core invariants
│   ├── guardrails.md              # Operating condition gates, contradiction filters & injection defense
│   └── statutory_boundaries.md    # External authority layer (FSSAI, CEA, CPWD) & statutory disclaimers
├── evaluation/                    # Verification methodology, results & honest limitations
│   ├── benchmark.md               # 20-row benchmark evaluation (90.0% Top-1, 100% negative rejection)
│   ├── adversarial_suite.md       # 70-probe adversarial evaluation across 14 failure categories (98.57%)
│   └── limitations.md             # Transparent disclosure of ADV-MUL-005 & accepted boundaries
└── archive/                       # Historical milestone audits and presentation decks
    ├── audits/                    # Priority 6–8 audits and freeze validation reports
    └── presentation/              # SIH presentation pitch deck and workflow diagrams
```

---

## Quick Navigation by Role

### For Evaluators & Hackathon Judges
- **Executive Overview**: [`../README.md`](../README.md)
- **Architecture Pipeline**: [`architecture/overview.md`](architecture/overview.md)
- **Safety Principles & Trust Invariants**: [`safety/principles.md`](safety/principles.md)
- **Ground-Truth Benchmark Results**: [`evaluation/benchmark.md`](evaluation/benchmark.md)
- **Adversarial Safety Evaluation (69/70)**: [`evaluation/adversarial_suite.md`](evaluation/adversarial_suite.md)
- **Honest Accepted Limitations**: [`evaluation/limitations.md`](evaluation/limitations.md)

### For Developers & Engineers
- **Step-by-Step Installation**: [`getting-started/installation.md`](getting-started/installation.md)
- **Running the Stack Locally**: [`getting-started/run_guide.md`](getting-started/run_guide.md)
- **Module Architecture Reference**: [`architecture/modules.md`](architecture/modules.md)
- **REST API Specification**: [`api/rest_api.md`](api/rest_api.md)
- **Standards Graph & Taxonomy**: [`architecture/relationship_graph.md`](architecture/relationship_graph.md)

### For Data & Domain Specialists
- **BIS Catalogue Architecture (35,208 records)**: [`data/catalogue.md`](data/catalogue.md)
- **Verified Standards Relationships (72 records)**: [`data/relationships.md`](data/relationships.md)
- **Benchmark Ground Truth Field Guide**: [`data/ground_truth.md`](data/ground_truth.md)
- **Statutory Regulatory Layer (FSSAI, CEA, CPWD)**: [`safety/statutory_boundaries.md`](safety/statutory_boundaries.md)

---

## Verified Baseline Facts (Commit `6a65754`)

| Dimension | Verified Fact | Source of Truth |
| :--- | :--- | :--- |
| **Product Name** | `Tender Saathi` | Canonical repository policy |
| **BIS Catalogue** | 35,208 records | `data/catalogue/bis_catalogue.db` (`standards` table) |
| **Working Standards** | 90 core standards | `data/standards/standards.db` (`standards` table) |
| **Benchmark Size** | 20 requirements | `dataset/ground_truth/ground_truth.csv` |
| **Top-1 Accuracy** | 18 / 20 (90.0%) | `src/evaluate.py` output |
| **Top-3 Recall** | 18 / 20 (90.0%) | `src/evaluate.py` output |
| **MRR** | 0.900 | `src/evaluate.py` output |
| **Negative Rejection** | 5 / 5 (100.0%) | `NEG-001` through `NEG-005` in `src/evaluate.py` |
| **Adversarial Suite** | 70 probes (14 categories × 5) | `dataset/adversarial/adversarial_evaluation_suite.json` |
| **Adversarial Score** | 69 / 70 passed (98.57%) | `src/eval_adversarial.py` output |
| **Accepted Limitation** | `ADV-MUL-005` | Seed catalogue boundary in `standards.db` |
| **Automated Tests** | 503 passed (0 failed) | `pytest tests/` |
| **Verified Relationships** | 72 verified relationships | `data/standards/relationships.json` |
| **Demonstration Domains** | 5 domains | Civil, Electrical, Mechanical, Process, Petroleum |
| **Relationship Taxonomy** | 8 canonical types | `CANONICAL_RELATIONSHIP_TYPES` in `src/standards.py` |
| **External Authorities** | FSSAI, CEA, CPWD | `src/regulatory/external_authority.py` |
| **Lexical Engine** | Pure-Python Okapi BM25 | `src/bm25_search.py` (zero external dependencies) |
| **REST Endpoints** | 12 active endpoints | `api/server.py` |
