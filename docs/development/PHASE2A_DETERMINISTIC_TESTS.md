# Tender Saathi — Phase 2A: Deterministic, Offline Test Suite

**Status**: Verified & Active  
**Date**: October 18, 2026  
**Module**: Automated Test Infrastructure & Model Isolation  
**Test Suite Status**: **516 passed, 0 failed in 58.2s** (100% offline, zero network dependencies)

---

## 1. Executive Summary

During Phase 1, test `tests/test_p7c_evidence_chain.py::test_05` failed because an unmocked call was made to the live Groq API (`https://api.groq.com/openai/v1/chat/completions`) when analyzing `tenders/raw/eProcurement System Government of India3.pdf`. The live model non-deterministically parsed valve facets and triggered Stage 4 Competing Interpretations (`AMBIGUOUS`) instead of Stage 5 Specification Completeness (`INCOMPLETE`). Furthermore, automated test runs were making unauthenticated HTTP `HEAD` calls to Hugging Face Hub on every invocation, causing network latency and flakiness.

Phase 2A completely eliminates non-deterministic external dependencies from automated testing:
1. Created [`tests/conftest.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/tests/conftest.py) installing a session-level socket connection guard that strictly blocks any outbound non-loopback network calls and enforces `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1`.
2. Resolved `test_p7c_evidence_chain.py::test_05` with an explicit deterministic understanding fixture, verifying the `INCOMPLETE` pathway, parameter preservation, and clarification question generation.
3. Added `test_05b` verifying the distinct `AMBIGUOUS` pathway on real PDF input.
4. Added [`tests/test_offline_isolation.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/tests/test_offline_isolation.py) proving socket blocking, offline environment variables, and credential-free execution.
5. Reduced full backend test suite execution time from **221.88s (3m 41s)** down to **57.11s** (almost 4x faster) with **zero failures** across all 516 tests.

---

## 2. Test-Dependency Inventory & Isolation Strategy

| Module / Component | External Dependency | Test Files Affected | Root Cause / Risk | Phase 2A Isolation Strategy |
|---|---|---|---|---|
| **AI Requirement Parser** ([`src/ai_understanding.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/ai_understanding.py)) | Groq API (`api.groq.com`), OpenRouter | `test_p7c_evidence_chain.py`, `test_milestone8_ai.py`, `test_p7b_api_ui_contract.py`, `test_p7d_adversarial_safety.py`, `test_p7e_failure_and_edge_states.py` | If `GROQ_API_KEY` exists in `.env` or shell env, unmocked calls hit external servers; output token drift causes test flakiness. | Outbound socket blocking in `conftest.py`; explicit deterministic JSON fixtures for understanding tests; graceful deterministic fallback verification. |
| **Multilingual Normalizer** ([`src/multilingual/normalizer.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/multilingual/normalizer.py)) | Groq API for non-fastpath translation | `test_multilingual.py` | Unmocked multilingual text translation. | Already initialized with `enabled=False` (offline deterministic regex/lexicon); guarded by network blocker in `conftest.py`. |
| **SentenceTransformer & CrossEncoder** ([`src/search.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/search.py), [`src/rerank.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/rerank.py)) | Hugging Face Hub (`huggingface.co`) | All retrieval, recommendation, and API integration tests | SentenceTransformer sends unauthenticated `HEAD` requests to verify model cache updates, causing warnings and network latency. | Enforced `HF_HUB_OFFLINE="1"` and `TRANSFORMERS_OFFLINE="1"` in `conftest.py`. Models load instantly from local disk cache with zero HTTP traffic. |
| **BIS Client** ([`src/catalogue/bis_client.py`](file:///home/syed-imadulla/Desktop/Tender_Saathi/src/catalogue/bis_client.py)) | BIS Portal (`services.bis.gov.in`) | `test_bis_acquisition.py` | Scraping / catalogue updates. | Already isolated with `mock_session = MagicMock()`. Guaranteed by network blocker. |

---

## 3. Implementation Details

### A. Centralized Test Configuration (`tests/conftest.py`)
- Sets `HF_HUB_OFFLINE = "1"` and `TRANSFORMERS_OFFLINE = "1"` before any imports.
- Installs `_guarded_socket_connect`:
  ```python
  def _guarded_socket_connect(self, address):
      host = address[0] if isinstance(address, tuple) and len(address) > 0 else str(address)
      if host in ("127.0.0.1", "localhost", "::1", "0.0.0.0"):
          return _ORIG_SOCKET_CONNECT(self, address)
      raise RuntimeError(
          f"External network connection to {address} was blocked. "
          "Automated tests must run deterministically offline without external API dependencies."
      )
  ```
- Autouse fixture `reset_test_state`: Calls `AIRequirementParser.clear_cache()` before and after every test to eliminate test crosstalk.
- Reusable fixture `mock_groq_understanding`: Helper factory to mock `_call_llm_api` with custom or default facets.

### B. Correction of `tests/test_p7c_evidence_chain.py::test_05`
- Isolated the pump maintenance scenario in `eProcurement System Government of India3.pdf` using an explicit deterministic understanding response.
- Preserved all substantive safety assertions:
  - `self.assertEqual(r0["ambiguity_state"], "INCOMPLETE")`
  - `self.assertTrue(r0["human_review_required"])`
  - `self.assertIsNone(r0["candidate_standard"])`
  - `self.assertTrue(len(r0.get("missing_parameters", [])) > 0)`
  - `self.assertIn("Pump Mechanism / Type", r0["missing_parameters"])`
  - `self.assertTrue(bool(r0.get("suggested_clarification_question")))`
- Added companion test `test_05b_ambiguous_competing_candidates_pdf` explicitly testing that when ambiguous multi-candidate scope (e.g., unspecified valve replacement) is provided on real PDF input, the engine safely flags `AMBIGUOUS`, sets `candidate_standard = None`, and preserves competing candidate pairs (`IS 14846` vs `IS/ISO 10434`).

### C. Self-Contained Unit Tests in `tests/test_milestone8_ai.py`
- Updated `test_28` and `test_29` to explicitly configure `recommender.ai_parser.enabled = True` and `recommender.ai_parser._api_key = "mock_groq_key"`. This ensures these unit tests pass even when no environment variables or `.env` files are present.

### D. Dedicated Verification Suite (`tests/test_offline_isolation.py`)
- Added 4 regression tests verifying:
  1. Socket connect to external IP addresses raises `RuntimeError`.
  2. Offline Hugging Face environment variables are active.
  3. Deterministic LLM response parsing functions without credentials.
  4. Missing credentials trigger graceful deterministic fallback.

---

## 4. Actual Before-and-After Test Results

### Before Phase 2A (Live Groq Calls & HF Hub Online)
```
Full Test Suite: pytest -q
Results: 510 passed, 1 failed in 221.88s (3m 41s)
Failure: tests/test_p7c_evidence_chain.py::TestPriority7CEvidenceChain::test_05_incomplete_clarification_preserved
Root Cause: AssertionError: 'AMBIGUOUS' != 'INCOMPLETE' due to live Groq API output variability.
```

### After Phase 2A (Deterministic Offline Execution)

| Test Command | Scope | Result | Execution Time | Offline Confirmed |
|---|---|---|---|---|
| `pytest tests/test_offline_isolation.py` | Network guard & offline isolation checks | **4 / 4 Passed** | 0.41s | Yes (socket blocked) |
| `pytest tests/test_p7c_evidence_chain.py` | Evidence chain & PDF ambiguity tests | **16 / 16 Passed** | 6.50s | Yes (socket blocked) |
| `pytest tests/test_milestone8_ai.py` | AI understanding unit tests | **29 / 29 Passed** | 6.88s | Yes (socket blocked) |
| `pytest tests/test_p7b_api_ui_contract.py tests/test_p7d_adversarial_safety.py tests/test_p7e_failure_and_edge_states.py` | API contract, adversarial, and failure states | **50 / 50 Passed** | 9.20s | Yes (socket blocked) |
| `pytest -q` (Full Suite) | Complete backend integration & regression suite | **516 / 516 Passed** | 58.21s | Yes (socket blocked) |
| `npx -y vitest run` | Frontend filter regression tests | **4 / 4 Passed** | 0.42s | Yes |
| `npm run build` | Frontend TypeScript compile & Vite bundle | **Passed (0 errors)** | 0.97s | Yes |

---

## 5. Protection of Evaluation & Architecture Integrity

- **Zero Changes to Production Recommendation Logic**: No modifications were made to candidate ranking, semantic similarity weights, cross-encoder scores, or the 10-stage decision safety pipeline in `src/recommend.py`.
- **Zero Changes to Thresholds**: `abs_delta <= 0.20` and `relative_ratio >= 0.70` in `src/ambiguity.py` were preserved without modification.
- **Evaluation Integrity**: No entries in `dataset/ground_truth/ground_truth.csv` were altered or falsely marked as `human_verified`.
- **Security**: No secrets or private tokens are stored in fixtures or committed to the repository.

---

## 6. Single Highest-Priority Next Step

**Phase 2B: Benchmark Transparency & Expert Verification**:
Expand and formally adjudicate the ground truth evaluation dataset (`dataset/ground_truth/ground_truth.csv`) with domain expert sign-off, setting `human_verified: TRUE` on verified rows, and expanding beyond 20 cases to cover multi-sector procurement tenders (CPWD, MES, Railway, GeM).
