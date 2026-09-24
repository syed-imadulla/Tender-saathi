# REST API Reference

The **Tender Saathi** backend exposes a lightweight Flask REST API (`api/server.py`) that acts as an adapter over the core intelligence pipeline.

**Base URL**: `http://localhost:5000` (or configured `FLASK_PORT`)

---

## 1. System & Capability Endpoints

### 1.1 Health Check
Check backend operational status.

- **Route**: `GET /api/health`
- **Response**: `200 OK`
```json
{
  "status": "ok",
  "version": "2.0.0",
  "engine": "StandardsRecommender",
  "ocr_available": true
}
```

### 1.2 System Capabilities
Inspect active system engines, database counts, and OCR status.

- **Route**: `GET /api/capabilities`
- **Response**: `200 OK`
```json
{
  "status": "ok",
  "offline_mode": true,
  "standards_count": 35208,
  "curated_standards_count": 90,
  "relationships_count": 72,
  "ocr_available": true,
  "ocr_engine": "tesseract",
  "llm_available": false
}
```

---

## 2. Ingestion & Analysis Endpoints

### 2.1 Analyze Raw Text
Analyze tender specification clauses submitted as plain text.

- **Route**: `POST /api/analyze/text`
- **Content-Type**: `application/json`
- **Request Body**:
```json
{
  "text": "Supply and installation of CPVC pipes conforming to IS 15778.",
  "tender_id": "optional-custom-id"
}
```
- **Response**: `200 OK` (Normalized Analysis Result object)

### 2.2 Analyze Tender PDF
Upload and analyze a native or scanned tender PDF document.

- **Route**: `POST /api/analyze/pdf`
- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: PDF file blob (required)
- **Response**: `200 OK` (Normalized Analysis Result object)
- **Errors**: `400 Bad Request` if file missing or non-PDF.

### 2.3 Analyze Scanned Specification Image
Upload a single image (PNG/JPEG) of a tender page or clause for OCR processing.

- **Route**: `POST /api/analyze/image`
- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: Image file blob (required)
- **Response**: `200 OK` (Normalized Analysis Result object)

### 2.4 Analyze Pre-packaged Sample
Quickly run analysis on pre-configured demonstration scenarios without uploading files.

- **Route**: `GET /api/analyze/sample/<demo>`
- **Parameters**: `demo` in `["cpvc", "valve", "superseded"]`
- **Response**: `200 OK` (Normalized Analysis Result object)

---

## 3. Normalized Analysis Response Structure

Endpoints `2.1` through `2.4` return a consistent, normalized response:

```json
{
  "tender_id": "ts-7a2e8f19-b5c4",
  "source_name": "cpvc_tender.pdf",
  "metadata": {
    "total_requirements": 4,
    "compliant_count": 3,
    "review_required_count": 1,
    "obsolete_count": 0,
    "compliance_score": 75.0
  },
  "requirements": [
    {
      "requirement_id": "REQ-001",
      "text": "CPVC pipes for domestic water supply...",
      "candidate_standard": "IS 15778 : 2007",
      "title": "Chlorinated Polyvinyl Chloride (CPVC) Pipes...",
      "relevance_score": 0.942,
      "confidence": "High",
      "decision_state": "RECOMMENDED",
      "ambiguity_state": "CLEAR",
      "evidence_quote": "Clause 4.1 specifies CPVC pipe requirements...",
      "evidence_standard": "IS 15778 : 2007",
      "human_review_required": false,
      "review_reason": "",
      "related_standards": [
        {
          "standard": "IS 2879",
          "relationship_type": "TEST_METHOD",
          "relationship_description": "Methods of test for CPVC pipes"
        }
      ]
    }
  ],
  "review_queue": []
}
```

---

## 4. Human Review & Audit Trail Endpoints

### 4.1 Submit Human Review Decisions
Submit human reviewer decisions (`ACCEPT`, `EDIT`, `DISMISS`) for items in the review queue. Automatically updates cached Markdown/JSON audit reports.

- **Route**: `POST /api/tender/<tender_id>/review`
- **Content-Type**: `application/json`
- **Request Body**:
```json
{
  "decisions": [
    {
      "requirement_id": "REQ-002",
      "decision": "ACCEPT",
      "reviewer_note": "Verified by Chief Mechanical Engineer"
    },
    {
      "requirement_id": "REQ-003",
      "decision": "EDIT",
      "reviewer_standard": "IS 1538 : 1993",
      "reviewer_note": "Updated to ductile iron specification"
    }
  ]
}
```
- **Response**: `200 OK`
```json
{
  "status": "ok",
  "tender_id": "ts-7a2e8f19-b5c4",
  "progress": {
    "total_review_items": 2,
    "reviewed_count": 2,
    "pending_count": 0,
    "accepted_count": 1,
    "edited_count": 1,
    "dismissed_count": 0,
    "review_status": "REVIEW_COMPLETE"
  }
}
```

### 4.2 Get Human Review Status
Fetch current reviewer decisions and review completion progress.

- **Route**: `GET /api/tender/<tender_id>/review`
- **Response**: `200 OK` with `decisions` array and `progress` object.

---

## 5. Report Download Endpoints

### 5.1 Download Session Report (JSON)
- **Route**: `GET /api/report/<tender_id>/json`
- **Response**: `200 OK` (Downloads `ts-<tender_id>-audit.json`)

### 5.2 Download Session Report (Markdown)
- **Route**: `GET /api/report/<tender_id>/markdown`
- **Response**: `200 OK` (Downloads `ts-<tender_id>-audit.md`)

### 5.3 Download Latest Active Report (JSON)
- **Route**: `GET /api/report/json`
- **Response**: `200 OK` (Returns the most recently analyzed tender session JSON)

### 5.4 Download Latest Active Report (Markdown)
- **Route**: `GET /api/report/markdown`
- **Response**: `200 OK` (Returns the most recently analyzed tender session Markdown)
