# Restaurant Margin Intelligence Platform (South Africa) — V1 Implementation Plan

## 1. Goal and Scope
Build V1 of a SaaS platform that helps restaurants protect gross margin by combining:
- POS sales data (Lightspeed, TABLE by Yoco, CSV fallback)
- Supplier invoice costs (PDF/image/CSV/email ingest)
- Recipe-lite mapping for top-selling items

V1 focus: **fast onboarding + actionable margin decisions**, not full accounting/AP replacement.

---

## 2. V1 Outcomes (What success looks like)
Within 14 days of onboarding, each restaurant should receive:
1. Current margin view for top-selling menu items.
2. Supplier price volatility alerts on key ingredients.
3. Weekly recommendation pack:
   - items to reprice
   - items to run as specials
   - items/promos to pause
4. A measurable estimate of recovered margin in ZAR.

---

## 3. Product Principles
1. **Progressive data maturity**: deliver value even with imperfect data.
2. **Decision layer first**: POS remains system of record for transactions.
3. **Concierge onboarding** for first customers to reduce setup friction.
4. **South Africa-first operations**: ZAR currency defaults and local supplier realities.

---

## 4. V1 Functional Requirements

### 4.1 Organization & Location Management
- Multi-tenant architecture (organization, locations).
- User roles: owner, manager, analyst (minimal RBAC).

### 4.2 Data Ingestion
#### A) POS Sales Import
- CSV upload endpoint for item-level daily sales.
- Required fields:
  - date
  - location
  - pos_item_id
  - pos_item_name
  - quantity_sold
  - gross_sales_zar
- Optional fields:
  - category
  - discounts
  - tax

#### B) Supplier Invoice Ingestion
- Upload PDF/image/CSV invoices.
- OCR + parser pipeline to extract line items:
  - supplier_name
  - invoice_date
  - raw_description
  - quantity
  - uom
  - line_total
  - unit_price (if present)
- Confidence scoring for extracted lines.
- Manual review UI/API for low-confidence lines.

### 4.3 Catalog & Mapping
- Canonical ingredient catalog per organization.
- Supplier SKU mapping table:
  - one canonical ingredient can map to many supplier descriptions.
- Unit normalization service (kg/g/L/ml/each).

### 4.4 Menu Item Modeling (Recipe-lite)
- Import menu items from POS feed.
- Recipe-lite builder for top menu items:
  - ingredient
  - quantity per serving
  - yield factor/waste factor (optional)
- Versioned recipe records (effective dates).

### 4.5 Margin Engine
- Compute latest ingredient cost from recent invoices.
- Compute estimated COGS per menu item.
- Compute gross margin per item:
  - gross_margin = selling_price - cogs
  - gross_margin_pct = gross_margin / selling_price
- Store historical daily snapshots for trend analysis.

### 4.6 Alerts & Recommendations
- Volatility alert when ingredient unit price changes above threshold (e.g., ±8% week-over-week).
- Margin risk alert when item margin drops below target.
- Recommendation generator (rules-based V1):
  1. Reprice candidate list.
  2. Special candidate list (high margin + available stock/cost stability).
  3. Promo pause list (low margin items under discount pressure).

### 4.7 Dashboards
- Top 20 item margin table.
- Ingredient volatility chart.
- Recommendation feed with expected margin impact.

---

## 5. Non-Functional Requirements
- Security: tenant isolation, encrypted secrets, audit trail for critical edits.
- Reliability: retryable ingest jobs and idempotent imports.
- Performance: process a 1,000-line invoice within target SLA (<3 minutes parse + review availability).
- Observability: structured logs + job metrics + parser confidence metrics.

---

## 6. Proposed Tech Stack (Pragmatic V1)
- Backend API: TypeScript (NestJS or Express) or Python (FastAPI).
- Workers: queue-based ingestion (BullMQ/Celery).
- Database: PostgreSQL.
- Cache/queue: Redis.
- File storage: S3-compatible bucket.
- OCR: pluggable provider (start with one provider + abstraction).
- Frontend: React/Next.js dashboard (or internal admin for early pilot).

---

## 7. Data Model (Core Tables)

### Tenant & Identity
- organizations
- locations
- users
- memberships

### POS and Menu
- pos_items
- pos_sales_daily
- menu_items (canonical)
- menu_item_mappings (pos_item_id -> menu_item_id)

### Supplier & Cost
- suppliers
- invoices
- invoice_lines_raw
- invoice_lines_normalized
- ingredients
- supplier_sku_mappings
- ingredient_cost_history

### Recipe & Margin
- recipes
- recipe_ingredients
- item_margin_snapshots
- alert_events
- recommendations

---

## 8. API Surface (V1)
1. `POST /ingest/pos-sales/csv`
2. `POST /ingest/invoices/upload`
3. `GET /ingest/invoices/:id/lines`
4. `POST /ingest/invoices/:id/confirm-lines`
5. `GET /menu-items`
6. `POST /menu-items/:id/recipe-lite`
7. `GET /metrics/margins?location_id=&date_range=`
8. `GET /alerts`
9. `GET /recommendations/weekly`

---

## 9. Implementation Phases

### Phase 1 (Week 1–2): Foundation
- Repo scaffold, auth, multi-tenant core.
- Database schema migrations.
- POS CSV ingest + validation.

### Phase 2 (Week 3–4): Invoice Cost Pipeline
- Invoice file upload.
- OCR extraction + raw line storage.
- Normalization + manual correction endpoint.

### Phase 3 (Week 5–6): Recipe-lite + Margin Engine
- Recipe-lite creation for top items.
- Cost history + margin calculations.
- Snapshot job and trend endpoints.

### Phase 4 (Week 7–8): Alerts + Recommendation Feed
- Volatility and margin threshold rules.
- Weekly recommendation generator.
- Initial dashboard views.

### Phase 5 (Week 9–10): Pilot Hardening
- Onboarding tooling.
- Error handling and observability.
- Pilot reporting and ROI summaries.

---

## 10. Onboarding Playbook (V1)
For each new restaurant:
1. Import last 8–12 weeks POS sales.
2. Upload recent supplier invoices (same period if possible).
3. Map top 30 selling items.
4. Build recipe-lite for top 20 items first.
5. Set item/category target margin thresholds.
6. Deliver first weekly recommendation pack.

---

## 11. Risks and Mitigations
1. **Low-quality invoice data**
   - Mitigation: confidence scoring + human review queue.
2. **Missing recipe data**
   - Mitigation: recipe-lite + default benchmarks + gradual refinement.
3. **No direct POS integration**
   - Mitigation: CSV/email report pipeline in V1.
4. **Trust in recommendations**
   - Mitigation: transparent “why this suggestion” explanations with numbers.

---

## 12. Metrics to Track (Product + Business)
### Product KPIs
- Time-to-first-insight (days).
- % of sales covered by mapped recipe-lite items.
- Invoice parse accuracy.
- Weekly active managers.

### Business KPIs
- Estimated margin recovered per location (ZAR/month).
- Gross revenue retention/churn.
- Setup-to-subscription conversion rate.

---

## 13. Out of Scope for V1
- Full accounts payable and payment workflows.
- Automatic write-back to all POS vendors.
- Advanced ML pricing elasticity models.
- Full inventory management replacement.

---

## 14. Definition of Done for V1
V1 is complete when a pilot customer can:
1. Ingest POS and invoice data.
2. Map top items to recipe-lite costs.
3. View margin and volatility dashboards.
4. Receive actionable weekly recommendations with estimated impact.

---

## 15. Where We Start (First Build Slice)

Do **not** start with the dashboard. Start with the first end-to-end data slice that produces one trustworthy number.

### First objective
Get to: **"Upload POS CSV + upload supplier invoice CSV/PDF -> compute margin for top 10 menu items."**

### Why this first
- Without clean ingestion and mapping, a dashboard is just empty UI.
- Margin computation validates the core business value before UI polish.
- This de-risks integrations and data quality early.

### Build order (recommended)
1. **Data contracts and schema**
   - Finalize input schemas for POS sales and invoice lines.
   - Create DB migrations for core tables:
     - `pos_items`, `pos_sales_daily`, `ingredients`, `invoices`, `invoice_lines_normalized`, `menu_items`, `recipes`, `recipe_ingredients`, `item_margin_snapshots`.
2. **POS ingestion endpoint**
   - Implement `POST /ingest/pos-sales/csv` with validation + idempotency key.
3. **Invoice ingestion (CSV first, then OCR/PDF)**
   - Implement `POST /ingest/invoices/upload`.
   - Support CSV parser first for speed and deterministic testing.
   - Add OCR/PDF pipeline after CSV path is reliable.
4. **Mapping + normalization service**
   - Map supplier descriptions to canonical ingredients.
   - Normalize units and compute unit cost.
5. **Recipe-lite capture**
   - Add endpoint to create recipe-lite for top items.
6. **Margin calculation job**
   - Nightly or on-demand job to calculate per-item COGS and margin snapshots.
7. **Minimal read API + simple internal view**
   - Implement `GET /metrics/margins`.
   - If needed, use a bare internal table page before full dashboard visuals.

### First milestone acceptance criteria (M1)
- Can ingest 30 days of POS sales via CSV.
- Can ingest at least 3 supplier invoices (CSV or parsed PDF) and normalize line costs.
- Can define recipe-lite for top 10 selling items.
- Can produce margin % for those items with timestamped snapshots.
- Can return results through `GET /metrics/margins`.

### Team split for week 1
- **Backend engineer A**: POS ingest + schema + validations.
- **Backend engineer B**: invoice ingest + normalization.
- **Product/ops**: onboarding template and mapping dictionary for first pilot restaurant.
- **Frontend engineer**: very thin internal margin table (no full dashboard yet).

### Dashboard timing
Build the polished dashboard **after M1** when data is stable. Before that, prioritize correctness, traceability, and explainability of margin numbers.
