# SAP Activate ERP Procurement Analytics

## Project Description

This repository is a portfolio-oriented procurement analytics project. It combines SAP Activate project framing, procure-to-pay process understanding, SQLite data modeling, deterministic synthetic ERP data, and SQL-ready procurement analytics.

The project does not connect to a live SAP system and does not claim to reproduce SAP S/4HANA internals. It creates a realistic analytical layer around a fictional company, Marmara Components, so procurement and project stakeholders can reason about supplier performance, purchase order fulfillment, delivery reliability, invoice readiness, and SAP Activate-style implementation progress.

## Business Problem

Marmara Components, a fictional mid-sized manufacturing and industrial components distribution company, wants better visibility into procurement performance during an SAP S/4HANA improvement initiative.

The analytics layer is designed to support questions such as:

- Which vendors represent the highest procurement spend?
- Which suppliers deliver complete orders on time?
- Which purchase orders or purchase order items remain open?
- Where do delays appear between requisition, purchase order, goods receipt, invoice, and payment?
- Which implementation tasks, exceptions, or data readiness issues need management attention?

## Current Technology Stack

- SQLite for the implemented relational database.
- Python 3 for deterministic data generation.
- Python standard library modules for dates, randomness, paths, argparse, and SQLite access.
- Faker for realistic synthetic names and master-data details.
- SQL for schema objects, constraints, validation-ready views, and future query files.
- Markdown for project documentation.
- Git and GitHub for version control and portfolio presentation.
- Power BI or Tableau as optional future dashboard layers after SQL outputs are stable.

## Current Implementation Status

Completed:

- Foundation and business documentation, including the business case, KPI catalog, SAP Activate mapping, and data-model documentation.
- Executable SQLite schema in `database/schema.sql`.
- Phase 1 master data generation for vendors, plants, purchasing groups, material groups, and materials.
- Phase 2 purchase requisition and purchase order generation, including PR-to-PO conversion scenarios and direct PO scenarios.
- Pre-Phase 3 refactor separating PO lifecycle state from fulfillment state.
- Phase 3 goods receipt generation and delivery-performance analytics.
- Fulfillment views and PO-item delivery-performance view.
- Phase 4 invoice and invoice-item generation.
- Item-level three-way matching and invoice-level matching summary views.
- Intentional perfect-match, price-mismatch, quantity-mismatch, and missing-goods-receipt scenarios.
- Phase 5 payment-event generation and invoice-level payment-progress derivation.
- Intentional failed, cancelled, on-hold, split successful payment, and fully paid scenarios.
- Phase 1 through Phase 5 validations, including integrity, foreign-key, deterministic regeneration, lifecycle, fulfillment, delivery KPI, invoice arithmetic, matching, blocking, payment arithmetic, eligibility, and rollback checks.

Not yet implemented:

- Change request data generation.
- Data quality issue generation.
- Separate SQL analytics query files.
- Dashboard implementation and final portfolio screenshots.
- SAP API or SAP Learning Hub integration.

## Architecture Highlight

The current model deliberately separates related but different concepts:

- Stored PO lifecycle state, such as active, blocked, cancelled, or closed.
- Stored PO-item lifecycle state, such as active, cancelled, or closed.
- Receipt-event workflow state, such as posted, under review, or reversed.
- Quantity facts, including received, accepted, rejected, and open quantities.
- Derived fulfillment state, calculated from posted accepted receipt quantities.
- Invoice document lifecycle state.
- Independent invoice blocking state and reason.
- Derived three-way matching state, calculated from PO, invoice, and eligible posted accepted receipt quantities.
- Payment-instruction result, such as scheduled, on hold, paid, failed, or cancelled.
- Derived invoice payment progress, calculated only from successful payment amounts.

This prevents one status field from representing unrelated business meanings. Receipt fulfillment is calculated through SQL views from accepted quantity; it is not manually stored as a purchase order status.

## Implemented Analytical Views

- `vw_po_item_fulfillment`: one row per PO item with received, accepted, rejected, under-review, open quantity, and derived fulfillment status.
- `vw_po_fulfillment`: one row per PO header with item-level fulfillment rolled up into header-level fulfillment status.
- `vw_po_item_delivery_performance`: one row per PO item with fulfillment date and delivery-performance classification.
- `vw_invoice_item_three_way_match`: one row per non-cancelled invoice item with eligible accepted quantity, cumulative invoiced quantity, quantity and price variances, monetary price impact, and derived matching status.
- `vw_invoice_matching_summary`: one row per invoice header with eligible, matched, and exception item counts plus `excluded` cancelled headers and `invalid` non-cancelled zero-item headers.
- `vw_invoice_payment_progress`: one row per invoice header with current payment eligibility, successful paid amount, outstanding amount, successful payment count, latest successful payment date, and derived payment progress.

## Reproducible Generation

Generate or regenerate the SQLite dataset from the repository root:

```bash
python scripts/generate_data.py --reset
```

The generator uses default seed `42`, so the current synthetic dataset is deterministic. It recreates `database/marmara_components.db`, applies the SQLite schema, inserts the synthetic data, and runs integrity, foreign-key, scenario, fulfillment, delivery-performance, invoice, three-way matching, payment-progress, and adversarial rollback checks.

## Current Deterministic Dataset Snapshot

Current generated row counts:

| Object | Rows |
| --- | ---: |
| `vendors` | 5 |
| `plants` | 2 |
| `purchasing_groups` | 3 |
| `material_groups` | 4 |
| `materials` | 12 |
| `purchase_requisitions` | 10 |
| `purchase_requisition_items` | 18 |
| `purchase_orders` | 8 |
| `purchase_order_items` | 15 |
| `goods_receipts` | 10 |
| `invoices` | 4 |
| `invoice_items` | 5 |
| `payments` | 5 |
| `sap_activate_project_tasks` | 12 |

The later-phase exception tables currently exist but are empty: `change_requests` and `data_quality_issues`.

Goods receipt facts in the current deterministic synthetic dataset:

- Total received quantity: 3043.
- Total accepted quantity: 3041.
- Total rejected quantity: 2.
- All current Phase 3 receipt events are posted.
- One PO item has multiple receipt events.
- Blocked and cancelled purchase orders have no receipts.

Current delivery KPI validation results, using reporting date `2026-03-31`:

- 12 eligible active due PO items.
- 3 on-time-in-full PO items.
- PO Item On-Time In-Full Rate: 25.0%.
- 5 on-time receipt events and 5 late receipt events.
- Receipt Event On-Time Rate: 50.0%.
- Average delay across late receipt events: 2.2 calendar days.

These values validate the current deterministic synthetic scenario. They are not universal procurement benchmarks.

Current Phase 4 invoice matching results:

- 4 invoice headers and 5 invoice items.
- 2 matched invoice items.
- 1 price mismatch.
- 1 quantity mismatch caused by 40 invoiced units against 38 posted accepted units.
- 1 missing-goods-receipt exception against an active PO item.
- Three-Way Matching Exception Rate: 3 / 5 = 60.0%.
- Blocked Invoice Count: 3.

Eligible receipt quantity is calculated as posted accepted quantity for the same PO item with `receipt_date` on or before `invoice_received_date`. Later receipts do not retroactively change the match state at invoice receipt.

Cancelled invoices are excluded at the item matching view, so they do not affect cumulative invoiced quantity or invoice-matching KPIs. Their headers remain visible in the summary with status `excluded`. A non-cancelled invoice with no items remains visible with status `invalid` and is not treated as matched or as an exception.

Phase 4 assumes invoice and PO quantities use the material base unit of measure. It does not implement unit-of-measure conversion, tax, freight, or business matching tolerances beyond numeric floating-point handling. Generated invoice unit prices are limited to two decimal places so Python and SQLite monetary rounding remain deterministic for the implemented dataset.

Current Phase 5 payment-progress results:

- 5 payment instructions or attempts.
- 2 successful payments against INV-001, totaling TRY 2,770.20.
- Failed, cancelled, and on-hold payment amounts do not contribute to successful paid amount.
- INV-001 is fully paid through two successful payment events.
- INV-002, INV-003, and INV-004 remain unpaid; all three remain blocked by their Phase 4 matching exceptions.
- Invoice Payment Completion Rate: 1 / 4 = 25.0%.
- Outstanding Invoice Amount: TRY 1,279.00 and EUR 597.00.
- Successful Paid Amount: TRY 2,770.20 and EUR 0.00.

Payment rows represent payment instructions or attempts, not invoice-level payment progress. The `payments.payment_status` field therefore does not contain `partially paid`; the `unpaid`, `partially paid`, and `paid` invoice states are derived in `vw_invoice_payment_progress`. Current payment eligibility means that a new successful payment can be accepted now, so a fully paid invoice with no outstanding balance is not eligible. Historical successful payments remain visible if an invoice is blocked or cancelled later; current header state is not used to reconstruct historical eligibility because state history is outside Phase 5. `payment_amount` inherits `invoices.invoice_currency`; Phase 5 does not store a duplicate payment currency or perform FX conversion.

PO Item On-Time In-Full Rate is the primary supplier-performance KPI because it evaluates complete business fulfillment at the PO-item grain and avoids overweighting split deliveries. Receipt Event On-Time Rate is useful as a secondary operational diagnostic because one PO item with multiple receipt events can contribute multiple events.

## SAP Activate Connection

The repository uses SAP Activate as a practical project-storytelling structure:

- Discover: define procurement pain points and business questions.
- Prepare: define scope, stakeholders, KPI priorities, and planned data sources.
- Explore: map reporting requirements to procurement process and data requirements.
- Realize: implement schema, deterministic data, analytical views, and validation logic.
- Deploy: future packaging of SQL query outputs, documentation review, dashboard screenshots, and readiness reporting.
- Run: future recurring monitoring of procurement KPIs and process improvement opportunities.

## Next Steps

1. Change request and data-quality issue generation.
2. Separate SQL analytics query files.
3. Optional dashboard and final portfolio presentation.
