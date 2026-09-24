# Configuration Guide

This document describes the configuration options, environment variables, database locations, and runtime operational modes of **Tender Saathi**.

---

## 1. Environment Variables

Tender Saathi follows a zero-required-configuration philosophy for local execution. All core functionality (document extraction, BM25 retrieval, semantic search, reranking, contradiction detection, and report generation) runs offline without third-party API dependencies.

If advanced features (such as LLM-assisted clause synthesis) are desired, create a `.env` file in the project root:

```ini
# Optional: Groq API key for LLM-assisted clause explanations and summaries
GROQ_API_KEY=gsk_...

# Optional: HuggingFace Token (avoids unauthenticated rate limits if re-downloading embeddings)
HF_TOKEN=hf_...

# Server configuration (default: 5000)
FLASK_PORT=5000
FLASK_DEBUG=false

# Security & CORS (default: http://localhost:5173)
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend Configuration (`frontend/.env`)
```ini
# API Gateway Target
VITE_API_URL=http://localhost:5000
```

---

## 2. Operating Modes: Offline vs. Cloud AI

| Feature | Offline Mode (Default) | Cloud AI Mode (`GROQ_API_KEY` set) |
| :--- | :--- | :--- |
| **Requirements Extraction** | Rule-based regex & NLP clause segmenter | Rule-based extraction + LLM entity refinement |
| **Standards Recommendation** | Pure-Python BM25 + NumPy embeddings + cross-encoder | Pure-Python BM25 + NumPy embeddings + cross-encoder |
| **Ambiguity & Guardrails** | Deterministic contradiction gates & operating condition rules | Deterministic contradiction gates & operating condition rules |
| **Report Generation** | Structured deterministic template engine | Structured deterministic template engine + synthesized narrative |
| **Network Dependency** | **Zero (Air-gapped capable)** | Outbound HTTPS to Groq API |

> [!IMPORTANT]
> The core safety, applicability, and recommendation decisions are **never delegated to an external generative LLM**. All recommendation candidates must strictly resolve to verified records in the local SQLite database.

---

## 3. Database Locations & File Structure

The system relies on local SQLite databases located in the repository:

- **Full BIS Catalogue**: [`data/catalogue/bis_catalogue.db`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/data/catalogue/bis_catalogue.db)
  - Contains 35,208 BIS standards with titles, status, ICS codes, and committee mappings.
- **Curated Standards Database**: [`data/standards/standards.db`](file:///home/syed-imadulla/Desktop/sih26108-feasibility/data/standards/standards.db)
  - Contains 90 prioritized core standards and 72 verified relationship graph edges.
- **Tender Repositories**:
  - `data/tenders/`: Reference tender PDFs.
  - `tenders/raw/`: Raw input tender PDFs for end-to-end evaluation.

---

## 4. Cache & Report Directories

- `.cache/`: Local model weights cache (e.g. `minilm_l6_v2` embeddings).
- `reports/generated/`: Session-based tender audit JSON and Markdown reports.
- `reports/feasibility/`: Milestone benchmark outputs.
- `reports/adversarial/`: 70-probe adversarial evaluation reports.
