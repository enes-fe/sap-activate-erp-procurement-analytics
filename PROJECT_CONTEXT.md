# SAP Activate ERP Procurement Analytics Project Context

## 1. Project Overview

This project is a portfolio-oriented procurement analytics simulation. It combines SAP Activate project methodology, ERP procure-to-pay process understanding, SQLite data modeling, deterministic synthetic data generation, and SQL-ready analytics.

The repository does not build or connect to a live SAP system. It creates a realistic analytical environment for Marmara Components, a fictional mid-sized manufacturing and industrial components distribution company, so the project can demonstrate both technical analytics work and SAP-oriented business thinking.

## 2. Why This Project Exists

The project is designed to demonstrate practical capability at the intersection of:

- Data analysis.
- SQL and relational modeling.
- ERP/SAP procurement processes.
- Procurement KPI design.
- IT project and SAP Activate framing.
- Business requirements and stakeholder communication.

The final portfolio should be readable to recruiters, data analysts, business analysts, SAP consultants, and project managers.

## 3. Business Scenario

Marmara Components is implementing or improving ERP procurement processes using SAP Activate as the project framing. The company wants better visibility into supplier performance, purchase order processing, delivery reliability, invoice matching, spend distribution, material category performance, process bottlenecks, data quality risk, and implementation readiness.

The analytics layer supports stakeholders such as procurement managers, buyers, finance teams, SAP consultants, business analysts, project managers, and key users.

## 4. Technical Scope

Implemented stack:

- SQLite is the current database.
- Python 3 is used for deterministic synthetic data generation.
- The generator uses Python standard library modules and Faker.
- SQL is used for the schema, constraints, views, validation-ready logic, and future analytics query files.
- Markdown is used for documentation.
- Git and GitHub are used for version control and portfolio presentation.
- Power BI or Tableau remain optional future dashboard layers.

## 5. Actual Data Model

The current SQLite schema contains these 16 persisted tables:

- `vendors`
- `plants`
- `purchasing_groups`
- `material_groups`
- `materials`
- `purchase_requisitions`
- `purchase_requisition_items`
- `purchase_orders`
- `purchase_order_items`
- `goods_receipts`
- `invoices`
- `invoice_items`
- `payments`
- `sap_activate_project_tasks`
- `change_requests`
- `data_quality_issues`

The current schema also contains three analytical views:

- `vw_po_item_fulfillment`
- `vw_po_fulfillment`
- `vw_po_item_delivery_performance`

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

The following tables currently exist for later phases but are empty: `invoices`, `invoice_items`, `payments`, `change_requests`, and `data_quality_issues`.

## 6. Important Architecture Decision

The pre-Phase 3 refactor separated several concepts that should not be compressed into a single status field:

- PO lifecycle: stored on `purchase_orders.po_lifecycle_status`.
- PO-item lifecycle: stored on `purchase_order_items.po_item_lifecycle_status`.
- Receipt workflow: stored on `goods_receipts.receipt_status`.
- Quantitative receipt facts: stored as received, accepted, and rejected quantities.
- Derived fulfillment: calculated by SQL views from posted accepted quantities.
- Future invoice progress: to be derived separately when invoice records are generated.

This keeps document lifecycle, operational receipt workflow, quantity facts, fulfillment progress, and invoice progress independently understandable. It also prevents one PO status field from representing lifecycle, delivery progress, timeliness, and invoice progress at the same time.

## 7. KPI Decision

The primary delivery-reliability KPI is `PO Item On-Time In-Full Rate`.

This KPI asks: what percentage of due active PO items were fully fulfilled with accepted quantity on or before the planned delivery date?

Supporting decisions:

- Receipt Event On-Time Rate is a secondary operational diagnostic, not the primary supplier reliability KPI.
- Accepted quantity determines fulfillment.
- Physical received quantity alone does not close a PO item.
- Rejected quantity does not close a PO item.
- Split deliveries should not overweight supplier reliability at the item level.

Current deterministic Phase 3 validation results, using reporting date `2026-03-31`:

- Eligible active due PO items: 12.
- On-time-in-full PO items: 3.
- PO Item On-Time In-Full Rate: 25.0%.
- On-time receipt events: 5.
- Late receipt events: 5.
- Receipt Event On-Time Rate: 50.0%.
- Average delay across late receipt events: 2.2 calendar days.

These are validation results for the synthetic dataset, not business targets or benchmarks.

## 8. Current Roadmap Status

| Step | Status | Notes |
| --- | --- | --- |
| Step 1: Foundation | Completed | Project scope, README, business case, KPI catalog, SAP Activate mapping, and project context exist. |
| Step 2: Data model | Completed for current scope | The executable SQLite schema contains the 16-table model and three analytical views. |
| Step 3: Synthetic data | Phase 1-3 completed | Master data, purchase requisitions, purchase orders, PR-to-PO conversion, direct PO scenarios, goods receipts, and SAP Activate project tasks are generated. Finance and project-exception tables remain for later phases. |
| Step 4: SQL analytics | Partially started | Fulfillment and delivery-performance logic exists as schema views and generator validation queries. Separate SQL analysis files are not yet created. |
| Step 5: Documentation | In progress | Current work aligns documentation with the pre-Phase 3 model refactor and Phase 3 goods receipt implementation. |
| Step 6: Dashboard | Not started / optional | Dashboard tools should wait until core SQL outputs are stable. |

Latest completed technical milestone:

```text
Phase 3 goods receipt and delivery-performance analytics
```

## 9. Current Completed Scope

Completed:

- SQLite schema.
- Deterministic Python data generator.
- Default seed `42`.
- Master data generation.
- Purchase requisition generation.
- Purchase order generation.
- PR-to-PO conversion scenarios.
- Direct PO scenarios.
- Goods receipt generation.
- PO lifecycle and fulfillment separation.
- Fulfillment views.
- PO-item delivery-performance view.
- Phase 1, Phase 2, and Phase 3 validations.
- Integrity, foreign-key, and deterministic regeneration checks.

Not yet implemented:

- Invoice data generation.
- Invoice item data generation.
- Payment data generation.
- Change request data generation.
- Data quality issue generation.
- Separate SQL analytics query files.
- Dashboard implementation.
- Final portfolio screenshots.
- SAP API or SAP Learning Hub integration.

## 10. Development Principles

- Keep the project realistic and business-oriented.
- Treat `database/schema.sql` and `scripts/generate_data.py` as technical source of truth for implemented behavior.
- Prefer simple, explicit SQL and Python over unnecessary abstraction.
- Keep synthetic data deterministic and validation-backed.
- Every technical output should connect to a business question.
- Do not claim live SAP integration, production data, or completed future phases.
- Keep documentation accurate for the current repository state.

## 11. Repository Structure

```text
sap-activate-erp-procurement-analytics/
|
|-- database/
|   |-- schema.sql
|   |-- marmara_components.db        # generated, ignored by Git
|
|-- docs/
|   |-- business_case.md
|   |-- data_model.md
|   |-- kpi_catalog.md
|   |-- sap_activate_mapping.md
|
|-- scripts/
|   |-- generate_data.py
|
|-- README.md
|-- PROJECT_CONTEXT.md
|-- .gitignore
```

Additional folders such as `sql/` or `dashboard/` may be added later when those phases are implemented.
