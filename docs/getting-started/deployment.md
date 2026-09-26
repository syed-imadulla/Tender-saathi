# Production Deployment Guide: Tender Saathi

This guide outlines the production deployment architecture, configuration, and verification procedures for **Tender Saathi**.

---

## 1. Architecture Topology

Tender Saathi uses a **decoupled production architecture** to preserve 100% of verified recommendation intelligence, SQLite catalogue capabilities, and large government tender PDF processing:

```
+-----------------------------------------------------------------------------------+
|                                  USER BROWSER                                     |
|  - Modern UI / Desktop / Tablet (Responsive React 18 + Vite 5 SPA)                |
+-----------------------------------------------------------------------------------+
         |                                                               |
         | 1. Static HTML/JS/CSS Assets                                  | 2. Direct API Calls (Optional: VITE_API_URL)
         v                                                               |    (bypasses Vercel 4.5MB payload limit)
+------------------------------------+                                   |
|       VERCEL (Frontend Host)       |                                   |
|  - Root: frontend/dist             |                                   |
|  - Framework: Vite / SPA           |                                   |
|  - Edge Routing / Static CDN       |                                   |
|  - vercel.json rewrite / proxy     |                                   |
|    /api/* -> Dedicated Backend     |                                   |
+------------------------------------+                                   |
                  |                                                      |
                  | (If routed via Vercel proxy)                         |
                  +------------------------+-----------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
|                     DEDICATED BACKEND SERVICE (Render / Fly / Cloud)              |
|  - Linux Container (Debian/Ubuntu base)                                           |
|  - System Packages: tesseract-ocr, poppler-utils (for PDF/scanned OCR)            |
|  - Python 3.10+ Runtime with full PyTorch, Transformers, Pandas, PyMuPDF          |
|  - Flask / WSGI Production Server                                                 |
|  - Persistent/warm in-memory report cache (_report_cache[tender_id])               |
|  - Read-only SQLite Data:                                                         |
|      * data/catalogue/bis_catalogue.db (35,208 records, 38 MB)                    |
|      * data/standards/standards.db (90 core standards, 116 KB)                    |
|  - Writable Directory: reports/generated/                                         |
|  - No 4.5 MB request body limit (handles 10MB-50MB real government tender PDFs)    |
|  - Long-running execution tolerance (no 10-15s serverless timeouts)               |
+-----------------------------------------------------------------------------------+
```

---

## 2. Why Decoupled Deployment is Essential

| Dimension | Monolithic Vercel Serverless | Decoupled Architecture |
| :--- | :--- | :--- |
| **Request Payload** | Hard 4.5 MB limit (blocks large tender PDFs) | Configurable backend upload limit, suitable for large government tender PDFs |
| **Review Session State** | Lost across cold/ephemeral lambdas | Warm process memory (`_report_cache`) |
| **ML Dependencies** | >1 GB bundle size (risks lambda failure) | Pre-warmed container with PyTorch & Transformers |
| **System Binaries** | No native `tesseract-ocr` or `poppler-utils` | Full OCR pipeline with Hindi & English models |
| **Core Invariant** | Requires weakening product intelligence | **Zero product compromises** |

---

## 3. Dedicated Backend Deployment

### A. Containerized Deployment (Recommended)
Tender Saathi includes a production-ready `Dockerfile`:
```bash
# Build the container locally or in CI
docker build -t tender-saathi-api:latest .

# Run the container
docker run -d -p 5000:5000 \
  -e PORT=5000 \
  -e CORS_ORIGINS="https://tender-saathi.vercel.app,https://*.vercel.app" \
  tender-saathi-api:latest
```

### B. Deploying to Cloud PaaS (Render, Railway, Fly.io)
1. **Render (Web Service)**:
   - Environment: `Docker`
   - Plan: Starter (1 GB - 2 GB RAM recommended for PyTorch models)
   - Health Check Path: `/api/health`
   - Environment Variables:
     - `PORT`: `5000`
     - `CORS_ORIGINS`: `https://*.vercel.app,https://your-domain.com`
2. **Railway / Fly.io**:
   - Deploys automatically via root `Dockerfile`.
   - Set internal port to `5000`.

---

## 4. Vercel Frontend Deployment

### A. Environment Configuration
In your Vercel Project Settings under **Environment Variables**, add:
- `BACKEND_URL`: URL of your deployed dedicated backend service (e.g. `https://tender-saathi-api.onrender.com`).
- `VITE_API_URL` *(Optional)*: If you want browser uploads to go directly to the backend to bypass Vercel's 4.5 MB proxy limit, set `VITE_API_URL=https://tender-saathi-api.onrender.com/api`.

### B. Deployment via Vercel CLI
```bash
# 1. Preview Deployment
npx vercel

# 2. Production Deployment (only after verifying preview)
npx vercel --prod
```

### C. Automatic Build & Routing
`vercel.json` configures the build and routing:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "buildCommand": "python3 scripts/configure_vercel.py && npm --prefix frontend install && npm --prefix frontend run build",
  "outputDirectory": "frontend/dist",
  "framework": "vite",
  "rewrites": [
    {
      "source": "/((?!api(?:/|$)).*)",
      "destination": "/index.html"
    }
  ]
}
```
During build, `scripts/configure_vercel.py` automatically injects the `/api/*` rewrite rule pointing to `BACKEND_URL` if set, while strictly excluding `/api/*` from the SPA fallback.

---

## 5. End-to-End Verification Checklist (18-Point Suite)

- **Phase 11 implementation and pre-deployment verification: PASS**
- **Production deployment: NOT YET EXECUTED**

Before promoting preview to production, verify all 18 functional checks:

1. [x] **Homepage loads**: Clean UI, fonts, badges, sample cards render.
2. [x] **Static assets load**: SVGs, stylesheets, JS chunks load with HTTP 200.
3. [x] **API health endpoint**: `GET /api/health` returns `{"status":"ok","service":"TenderSaathi API"}`.
4. [x] **Text tender analysis**: Analyzing CPVC sample text produces requirements with candidate standards.
5. [x] **Sample tender buttons**: CPVC, Valve, and Superseded demo buttons execute cleanly.
6. [x] **PDF upload**: Normal tender PDF uploads and extracts text.
7. [x] **Large PDF upload**: Large documents (>5 MB) are handled safely without truncation.
8. [x] **Recommendation results render**: Cards, scores, and candidate badges render accurately.
9. [x] **Evidence & provenance**: Provenance tags (VERIFIED, CURATED, INFERRED) and evidence details render.
10. [x] **Applicability & ambiguity**: Validated gates (Direct, General, Boundary, Review Needed) display correctly.
11. [x] **Standards relationships & regulatory**: Mandatory tags, supersession alerts, and successor links display.
12. [x] **Human review queue**: Actionable candidates enter review queue.
13. [x] **Human review decisions**: Accept / Edit / Dismiss buttons update state and persist during session.
14. [x] **Report generation**: Summary metrics and audit breakdown generate on the fly.
15. [x] **Report download**: JSON and Markdown export download valid files to client.
16. [x] **OCR/scanned document path**: Handled gracefully via backend OCR layer.
17. [x] **Error handling**: Empty inputs and invalid files return user-friendly error banners without raw stack traces.
18. [x] **Browser console**: No unhandled CORS errors, CSP blocks, or failed asset requests.

---

## 6. Rollback Procedures

### Frontend Rollback
Vercel keeps immutable deployment records. To rollback instantly:
```bash
# List recent deployments
npx vercel list

# Promote prior deployment to production
npx vercel promote <DEPLOYMENT_URL_OR_ID>
```
Or use the **Vercel Dashboard $\rightarrow$ Deployments $\rightarrow$ Instant Rollback**.

### Backend Rollback
- On Docker / PaaS: Redeploy the previously tagged image or rollback via the PaaS web console.
- In Git: Revert deployment commits using standard `git revert`.
