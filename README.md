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
- Phase 1, Phase 2, and Phase 3 validations, including integrity, foreign-key, deterministic regeneration, lifecycle, fulfillment, and delivery KPI checks.

Not yet implemented:

- Invoice and invoice-item data generation.
- Payment data generation.
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
- Future invoice progress, which will be derived separately when invoice data is implemented.

This prevents one status field from representing unrelated business meanings. Receipt fulfillment is calculated through SQL views from accepted quantity; it is not manually stored as a purchase order status.

## Implemented Analytical Views

- `vw_po_item_fulfillment`: one row per PO item with received, accepted, rejected, under-review, open quantity, and derived fulfillment status.
- `vw_po_fulfillment`: one row per PO header with item-level fulfillment rolled up into header-level fulfillment status.
- `vw_po_item_delivery_performance`: one row per PO item with fulfillment date and delivery-performance classification.

## Reproducible Generation

Generate or regenerate the SQLite dataset from the repository root:

```bash
python scripts/generate_data.py --reset
```

The generator uses default seed `42`, so the current synthetic dataset is deterministic. It recreates `database/marmara_components.db`, applies the SQLite schema, inserts the synthetic data, and runs integrity, foreign-key, scenario, fulfillment, and delivery-performance checks.

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
| `sap_activate_project_tasks` | 12 |

The downstream finance and exception tables currently exist but are empty: `invoices`, `invoice_items`, `payments`, `change_requests`, and `data_quality_issues`.

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

1. Phase 4 invoice and invoice-item generation.
2. Three-way matching and invoice exception analytics.
3. Payment generation.
4. Change request and data-quality issue generation.
5. Separate SQL analytics query files.
6. Optional dashboard and final portfolio presentation.
