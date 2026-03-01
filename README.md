# Restaurant Margin Intelligence V1

Initial V1 backend slice for the South Africa-focused restaurant margin tool.

## What is implemented
- `POST /ingest/pos-sales/csv`
- `POST /ingest/invoices/csv`
- `POST /menu-items/recipe-lite`
- `POST /metrics/margins/recompute`
- `GET /metrics/margins`

This is intentionally an in-memory starter implementation to validate the end-to-end margin flow before database hardening.

## Run locally
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run tests
```bash
pytest -q
```
