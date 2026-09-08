# SIH26108 Feasibility Spike: Tender Dataset & Standards Extraction

**Problem Statement (SIH 2026)**: *“AI-Powered Recommendation Engine for Identifying Applicable Indian Standards for Procurement Specifications.”*

This repository contains the **Technical Feasibility Spike** dataset, analysis pipeline, and evidence collection tools for our SIH project.

---

## 1. What This Dataset Is

When government and public sector organizations publish procurement tenders, they specify products, materials, and testing parameters (for example: *GI pipe*, *CPVC pipe*, *Underground power cables*, *Process water pumps*). 

Often, the explicit **Indian Standard (IS) numbers are omitted** or buried in annexures, creating compliance ambiguity.

This dataset collects **20 real Government of India eProcurement / CPPP tender documents** and provides an automated, reproducible pipeline to:
1. Inventory and extract text without modifying original files.
2. Extract candidate technical requirements (labeled as candidates pending human verification).
3. Detect any cited Indian Standards (`IS`, `SP`, `BIS`).
4. Prepare human-ground-truth review files to validate recommendation logic.

---

## 2. Directory Structure

```text
sih26108-feasibility/
│
├── tenders/
│   ├── raw/                  <-- Put your downloaded tender PDFs here
│   ├── processed/            <-- Track processed states
│   └── failed/               <-- Log any corrupted/unreadable PDFs
│
├── dataset/
│   ├── tender_metadata.csv      <-- Inventory table with 15 columns
│   ├── tender_requirements.jsonl <-- Candidate requirements (1 per line)
│   ├── standard_mentions.jsonl   <-- Extracted Indian Standard mentions
│   ├── tender_review.csv        <-- Human validation review table
│   └── extraction_results/      <-- Structured JSON per tender (T001.json...)
│
├── scripts/
│   ├── ingest_tenders.py        <-- Master repeatable ingestion command
│   ├── extract_text.py          <-- PDF text & section layout parser
│   ├── extract_requirements.py  <-- Candidate requirement extractor
│   ├── extract_standards.py     <-- Regex pattern matcher for IS/SP/BIS
│   └── generate_dataset.py      <-- Dataset & feasibility report builder
│
├── reports/
│   ├── feasibility/
│   │   ├── extraction_report.md <-- Full quality & extraction metrics report
│   │   ├── T001_manual_review.md <-- Plumbing / Toilet renovation review
│   │   ├── T004_manual_review.md <-- Electrical power cabling review
│   │   ├── T007_manual_review.md <-- Food outlet / Catering review
│   │   ├── T014_manual_review.md <-- Heavy mechanical process pump review
│   │   └── T020_manual_review.md <-- CPVC vs GI water supply review
│   └── tender_analysis/
│
├── data/
│   ├── standards/
│   │   └── standards.xlsx       <-- 54 audited Bureau of Indian Standards
│   └── tenders/                 <-- Backup archive of source tender PDFs
│
└── README.md
```

---

## 3. How to Run the Pipeline

### Step 1: Place Your Tender PDFs
Drop any new or existing tender PDFs into the folder:
```bash
tenders/raw/
```
*(Your original files will never be modified or overwritten)*.

### Step 2: Run the Ingestion Pipeline
In your terminal, execute:
```bash
python3 scripts/ingest_tenders.py
```
Or to run the dataset generator directly:
```bash
python3 scripts/generate_dataset.py
```

If you have PDFs in another folder, you can safely import them without duplicates:
```bash
python3 scripts/ingest_tenders.py --import-from /path/to/my_downloads
```

---

## 4. What Each Dataset File Means

| File Path | What It Contains | How to Use It |
|---|---|---|
| `dataset/tender_metadata.csv` | Master inventory with tender ID, filename, file size, page count, OCR status, department, organization, title, and product category. | Open in Excel/Calc to view all tenders at a glance. |
| `dataset/tender_requirements.jsonl` | One JSON record per extracted requirement (`T001-R001`, etc.), clearly tagged as `status: "candidate"` and `human_verified: false`. | Use for downstream NLP parsing and evaluation. |
| `dataset/standard_mentions.jsonl` | One JSON record per detected Indian Standard mention, page number, context snippet, and source. | Tracks cited standards across documents. |
| `dataset/tender_review.csv` | A spreadsheet designed specifically for human reviewers with verification columns (`Human Verified`, `Expected/Applicable Standard`, `Verification Evidence`, `Reviewer Notes`). | Reviewers mark ground truth in this file. |
| `dataset/extraction_results/T001.json` | Complete page-by-page text, character counts, detected sections, and parsed key-value metadata for tender `T001`. | Deep inspection of raw extracted text per tender. |
| `reports/feasibility/extraction_report.md` | Executive quality audit summarizing pages, requirements, OCR checks, and the 5 analytical categories (A, B, C, D, E). | Read for overall feasibility findings. |

---

## 5. How to Inspect Extraction Results

1. **Quick Overview**: Open `reports/feasibility/extraction_report.md` to see the total number of tenders, pages, and requirements.
2. **Reviewing Ground Truth**: Open `dataset/tender_review.csv` in your spreadsheet editor (e.g. LibreOffice Calc, Excel, or Google Sheets).
3. **Manual Validation Candidates**: Read through the 5 domain review files in `reports/feasibility/`:
   - `reports/feasibility/T001_manual_review.md` (Sanitary & Plumbing)
   - `reports/feasibility/T004_manual_review.md` (Electrical Power Distribution)
   - `reports/feasibility/T007_manual_review.md` (Food & Services)
   - `reports/feasibility/T014_manual_review.md` (Heavy Mechanical Equipment)
   - `reports/feasibility/T020_manual_review.md` (Water Supply Piping)

---

## 6. How to Add Another Tender

1. Copy your new PDF into `tenders/raw/`:
   ```bash
   cp my_new_tender.pdf tenders/raw/
   ```
2. Re-run the ingestion command:
   ```bash
   python3 scripts/ingest_tenders.py
   ```
3. The script automatically discovers the new PDF, assigns the next sequential ID (e.g. `T021`), extracts text and requirements, and updates all datasets without losing existing data.
