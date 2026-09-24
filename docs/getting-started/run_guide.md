# Run & Execution Guide

This guide covers running **Tender Saathi** locally, executing CLI demos, launching the web UI, and running test/evaluation suites.

---

## 1. Running the Web Application

The system consists of a Flask REST backend and a Vite + React frontend.

### Step 1: Start the Backend REST API
In your terminal, activate your virtual environment and start the Flask server:

```bash
source venv/bin/activate
python3 -u api/server.py
```

The API will start at `http://127.0.0.1:5000`. You can test it by visiting `http://127.0.0.1:5000/api/health`.

### Step 2: Start the Frontend UI
In a second terminal window, navigate to the `frontend/` directory and run:

```bash
cd frontend
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 2. Running CLI Demonstrations

Tender Saathi includes standalone command-line scripts to demonstrate core intelligence without opening the browser:

### 1. Interactive Demonstration (`demo.py`)
Runs an end-to-end demonstration showcasing requirement extraction, hybrid retrieval, supersedence detection, and human review routing:

```bash
python3 demo.py
```

### 2. End-to-End Validation (`validate_e2e.py`)
Validates the extraction and recommendation pipeline against real tender PDFs:

```bash
python3 validate_e2e.py
```

---

## 3. Running Test Suites

Run the full pytest suite (503 unit, integration, and safety tests):

```bash
python3 -m pytest -q
```

To run a specific test category:
```bash
# Test API and UI contract
python3 -m pytest tests/test_p7b_api_ui_contract.py -q

# Test Evidence Chain and Citation Verification
python3 -m pytest tests/test_p7c_evidence_chain.py -q

# Test Relationship Graph and Regulatory Intelligence
python3 -m pytest tests/test_phase9_relationships_regulatory.py -q
```

---

## 4. Running Benchmark & Safety Evaluations

### Benchmark Evaluation (20-Row Standard Dataset + 5 Negative Controls)
```bash
python3 -m src.evaluate
```
Produces:
- Mode ablation comparison table.
- Negative control rejection rate.
- Reports at `reports/feasibility/milestone2_evaluation_report.md`.

### Adversarial Evaluation (70-Probe Stress Suite)
```bash
python3 -m src.eval_adversarial
```
Produces:
- 8-dimensional multi-metric report.
- 14 category breakdowns.
- Markdown report at `reports/adversarial/adversarial_evaluation_report.md`.
