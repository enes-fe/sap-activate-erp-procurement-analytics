# Phase 7 SQL Analytics Package

This package exposes the existing Marmara Components business logic through
standalone, recruiter-readable SQLite queries. It does not create tables or
views and does not replace any logic implemented in `database/schema.sql`.

## Run the Package

From the repository root, validate every statement and the deterministic
Seed-42 headline returned by each file:

```bash
python scripts/validate_sql_queries.py
```

To recreate the canonical database before validation:

```bash
python scripts/generate_data.py --reset
python scripts/validate_sql_queries.py
```

The runner opens `database/marmara_components.db` in read-only mode. Each SQL
file contains one or more analytical result sets followed by a compact final
headline result set. The final result is intentionally stable so the runner can
compare it with an explicit Seed-42 expectation.

## Reporting Scope

- Fixed reporting date: `2026-03-31`.
- Procurement commitment period: `2026-01-01` through `2026-03-31`.
- PO monetary measures represent purchase-order commitment value, not cash
  spend or payment activity.
- Cancelled PO headers and cancelled PO items are excluded from commitment
  analysis. Blocked POs remain visible and are reported separately.
- Item OTIF uses the existing `vw_po_item_delivery_performance` logic.
- Open quantity uses the existing `vw_po_item_fulfillment` logic.
- Invoice matching, payment progress, and readiness classifications come from
  their existing analytical views.
- TRY and EUR values are never added together. Monetary summaries group by
  currency or return separate currency columns.
- Open quantities are not added across unlike units of measure.
- Every multi-row result has a deterministic `ORDER BY`.

## Files and Business Questions

| File | Business question |
| --- | --- |
| `01_procurement_spend.sql` | Where is non-cancelled PO commitment value concentrated by currency, supplier, and material group? |
| `02_supplier_delivery_performance.sql` | Which suppliers deliver active due PO items on time and in full, and what does receipt-event timing show? |
| `03_open_po_analysis.sql` | Which active PO items remain open or partial, how overdue are they, and what commitment remains by currency? |
| `04_invoice_matching_analysis.sql` | How often does three-way matching fail, why does it fail, and which invoice value is blocked by currency? |
| `05_payment_progress_analysis.sql` | How much valid invoice value is paid or outstanding by currency, and which invoices drive the balance? |
| `06_project_readiness_analysis.sql` | What is the current go-live readiness, and which phase-level tasks, change requests, and data-quality risks need attention? |

## Expected Seed-42 Headlines

| File | Deterministic headline |
| --- | --- |
| `01_procurement_spend.sql` | 7 non-cancelled POs; 14 items; TRY 7216.64 and EUR 4269.30 commitment value. |
| `02_supplier_delivery_performance.sql` | 12 eligible active due items; 3 OTIF; 25.0% item OTIF; 50.0% receipt-event on-time rate; 2.2 average late receipt days. |
| `03_open_po_analysis.sql` | 4 active PO headers with 5 open/partial items; TRY 1118.82 and EUR 2245.80 remaining commitment. |
| `04_invoice_matching_analysis.sql` | 5 eligible items; 2 matched; 3 exceptions; 60.0% exception rate; 3 blocked invoices. |
| `05_payment_progress_analysis.sql` | 4 valid invoices; 1 fully paid; 25.0% completion; TRY 1279.00 and EUR 597.00 outstanding. |
| `06_project_readiness_analysis.sql` | 10 pre-go-live tasks; 6 completed; 3 open change requests; 2 unresolved high/critical data-quality issues; `not ready`. |
