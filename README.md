# Cloud-Based Pension Portability and Employment Transition Platform
## AI-Based Pension Fund Risk and Sustainability Dashboard

A working prototype demonstrating three objectives:

1. **Secure consolidation** of a member's pension contribution history across
   authorised participating institutions.
2. **Standard APIs** for exchanging approved pension information.
3. **Evaluation** of interoperability, security, accuracy, and transaction performance.

---

## Quick Start

    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    python -m pip install -r requirements.txt
    python seed.py
    uvicorn app.main:app --reload

Then open http://localhost:8000 and log in with:

    Member ID: M001
    Password:  demo1234

---

## Demo Script

1. Click **Login**.
2. Grant consent for `INS-A`, then **Consolidate contributions**.
3. Repeat for `INS-B` and `INS-C`.
4. Request a transfer from `INS-A` to `INS-B`.
5. Click **Refresh scores** on the AI dashboard.
6. Scroll to the **Audit Trail** to see the hash-chained log.

---

## Objective Mapping

| Objective | Implementation | Tests |
|---|---|---|
| O1 – Secure consolidation | `app/aggregation.py`, consent gate, JWT auth, audit ledger | `test_security.py`, `test_accuracy.py` |
| O2 – Standard APIs | Versioned REST at `/api/v1/*`, `openapi.yaml`, Pydantic schemas | `test_interoperability.py` |
| O3 – Evaluation | `tests/` suite measuring all four dimensions | All |

Run the evaluation suite:

    python -m pytest -v

Expected: **10 passed**.

---

## Architecture

- **FastAPI** backend, **SQLite** storage, **JWT** auth.
- **Consent-gated aggregation** across three mock institutions.
- **Rule-based AI scorer** (`app/risk.py`) with the same interface a real
  ML model would use, producing explainable top factors.
- **Hash-chained audit ledger** for tamper-evident logging.

---

## Evaluation Summary

| Dimension | Metric | Target | Result |
|---|---|---|---|
| Interoperability | Schema conformance | 100% | PASSED |
| Security | Auth required, cross-member blocked, consent enforced, revocation honored | 100% | PASSED |
| Accuracy | Duplicate rejection, total reconciliation | 100% / ±0.001 | PASSED |
| Performance | p95 latency | ≤ 300 ms | PASSED |

All 10 tests pass in ~15 s. See `openapi.yaml` for the published API contract.
