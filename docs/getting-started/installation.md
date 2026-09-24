# Installation Guide

This guide provides step-by-step instructions to set up the development and evaluation environment for **Tender Saathi**.

---

## 1. Prerequisites

Ensure your system meets the following prerequisites:

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows WSL2.
- **Python**: Version `3.10` or higher (`python3 --version`).
- **Node.js**: Version `18.x` or higher (`node --version`).
- **npm**: Version `9.x` or higher (`npm --version`).
- **System Packages (Optional for OCR / PDF parsing)**:
  ```bash
  # Debian / Ubuntu
  sudo apt-get update
  sudo apt-get install -y tesseract-ocr poppler-utils
  ```

> [!NOTE]
> Tender Saathi's core recommendation engine is pure-Python and NumPy-based. Heavy ML frameworks like PyTorch or GPU drivers are **not required** for default offline execution.

---

## 2. Python Environment Setup

1. **Clone the repository and enter the directory**:
   ```bash
   git clone <repo-url> sih26108-feasibility
   cd sih26108-feasibility
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

---

## 3. Frontend Setup

The user interface is built with React and Vite:

1. **Navigate to the frontend directory**:
   ```bash
   cd frontend
   ```

2. **Install npm dependencies**:
   ```bash
   npm install
   ```

3. **Return to the repository root**:
   ```bash
   cd ..
   ```

---

## 4. Verification

Verify that your installation is complete and all test suites pass:

```bash
python3 -m pytest -q
```

Expected output:
```text
503 passed in ...s
```

All 503 unit, integration, and safety tests should pass cleanly.
