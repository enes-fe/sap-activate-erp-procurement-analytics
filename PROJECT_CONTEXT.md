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

Marmara Components is implementing or improving ERP procurement processes using SAP Activate as the project framing. The company wants better visibility into supplier performance, purchase order processing, delivery reliability, invoice matching, PO commitment distribution, material category performance, process bottlenecks, data quality risk, and implementation readiness.

The analytics layer supports stakeholders such as procurement managers, buyers, finance teams, SAP consultants, business analysts, project managers, and key users.

## 4. Technical Scope

Implemented stack:

- SQLite is the current database.
- Python 3 is used for deterministic synthetic data generation.
- The generator uses Python standard library modules and Faker.
- SQL is used for the schema, constraints, analytical views, and the standalone Phase 7 analytics package.
- Markdown is used for documentation.
- Git and GitHub are used for version control and portfolio presentation.
- Power BI delivery includes six deterministic dashboard-ready CSV extracts, a completed three-page report, real page screenshots, and an optional downloadable PBIX artifact.

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

The current schema also contains eight analytical views:

- `vw_po_item_fulfillment`
- `vw_po_fulfillment`
- `vw_po_item_delivery_performance`
- `vw_invoice_item_three_way_match`
- `vw_invoice_matching_summary`
- `vw_invoice_payment_progress`
- `vw_change_request_phase_summary`
- `vw_project_readiness_summary`

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
| `change_requests` | 6 |
| `data_quality_issues` | 7 |

The Phase 6 project dataset contains six change requests and seven data-quality issues. These issue records describe legacy migration or UAT findings; the deterministic Phase 1-5 master and transaction facts remain valid and unchanged.

## 6. Important Architecture Decision

The pre-Phase 3 refactor separated several concepts that should not be compressed into a single status field:

- PO lifecycle: stored on `purchase_orders.po_lifecycle_status`.
- PO-item lifecycle: stored on `purchase_order_items.po_item_lifecycle_status`.
- Receipt workflow: stored on `goods_receipts.receipt_status`.
- Quantitative receipt facts: stored as received, accepted, and rejected quantities.
- Derived fulfillment: calculated by SQL views from posted accepted quantities.
- Invoice document lifecycle: stored on `invoices.invoice_status`.
- Invoice blocking: stored independently through `blocked_flag` and `block_reason`.
- Three-way matching: derived by SQL views from PO, invoice, and eligible posted accepted receipt quantities.
- Payment instruction or attempt result: stored on `payments.payment_status`.
- Invoice payment progress: derived from successful payment amounts through `vw_invoice_payment_progress`.
- Change-request lifecycle: stored independently on `change_requests.status`.
- Data-quality lifecycle: stored independently on `data_quality_issues.issue_status`.
- Go-live readiness: derived from explicit pre-go-live task, open change-request, and data-quality blocker rules through `vw_project_readiness_summary`.

This keeps document lifecycle, operational receipt workflow, quantity facts, fulfillment progress, invoice matching, blocking, payment-attempt result, current payment eligibility, and invoice payment progress independently understandable. In particular, a posted invoice may be blocked without overloading `invoice_status`, and `partially paid` is derived at invoice grain rather than stored as a payment-event status.

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

Current deterministic Phase 4 matching results:

- 5 invoice items: 2 matched and 3 exceptions.
- 1 price mismatch.
- 1 quantity mismatch caused by 40 invoiced units against 38 eligible accepted units.
- 1 missing-goods-receipt exception.
- Three-Way Matching Exception Rate: 60.0%.
- Blocked Invoice Count: 3.

Eligible accepted quantity includes only posted goods receipts for the same PO item with a receipt date on or before the invoice received date.

Cancelled invoices are excluded from item-level matching and matching KPI denominators. Their headers remain visible in the invoice summary as `excluded`; non-cancelled zero-item headers are classified as `invalid`.

Current deterministic Phase 5 payment results:

- 5 payment instructions or attempts.
- 2 successful payments against INV-001, totaling TRY 2,770.20.
- INV-001 is fully paid; INV-002, INV-003, and INV-004 are unpaid.
- Failed, cancelled, scheduled, and on-hold payments contribute zero to successful paid amount.
- Invoice Payment Completion Rate: 1 / 4 = 25.0%.
- Outstanding Invoice Amount: TRY 1,279.00 and EUR 597.00.
- Successful Paid Amount: TRY 2,770.20 and EUR 0.00.

Payment amount inherits invoice currency. The model does not duplicate currency on payment rows or combine different currencies in amount KPIs.

Current deterministic Phase 6 readiness results:

- 6 change requests; 3 are open and 2 are both open and high/critical priority.
- 7 data-quality issues; 6 are non-cancelled, 3 resolved, 1 accepted risk, and 2 unresolved.
- Unresolved High/Critical Data Quality Issue Count: 2.
- Data Quality Resolution Rate: 3 / 6 = 50.0%.
- Data Quality Disposition Rate: 4 / 6 = 66.7%; accepted risk is not counted as resolved.
- Go-Live Readiness Classification: `not ready`.
- Permanent hard blockers: critical blocked Deploy task `TASK-010` and critical open issue `DQ-004`.

## 8. Current Roadmap Status

| Step | Status | Notes |
| --- | --- | --- |
| Step 1: Foundation | Completed | Project scope, README, business case, KPI catalog, SAP Activate mapping, and project context exist. |
| Step 2: Data model | Completed for current scope | The executable SQLite schema contains the 16-table model and eight analytical views. |
| Step 3: Synthetic data | Phase 1-6 completed | Master, procurement, invoice, payment, SAP Activate task, change-request, and data-quality issue data are generated. |
| Step 4: SQL analytics | Completed for current scope | Six standalone analyses expose PO commitment, delivery, open-PO, invoice, payment, and readiness logic; every file has a deterministic Seed-42 headline validated by a read-only runner. |
| Step 5: Documentation | Completed through Phase 8 | Repository documentation describes the SQL package, reporting rules, dashboard data model, expected headlines, validation workflow, and completed portfolio presentation. |
| Step 6: Dashboard | Completed | Six deterministic Power BI-ready CSV extracts, the three-page Power BI report, an optional downloadable PBIX, and real screenshots are included. |

Latest completed technical milestone:

```text
Phase 8 completed Power BI dashboard and recruiter-facing portfolio presentation
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
- Invoice and invoice-item generation.
- Perfect-match, price-mismatch, quantity-mismatch, and missing-goods-receipt scenarios.
- PO lifecycle and fulfillment separation.
- Fulfillment views.
- PO-item delivery-performance view.
- Item-level three-way matching view.
- Invoice-level matching summary view.
- Deterministic payment instruction and attempt generation.
- Invoice-level payment-progress view.
- Deterministic change-request and data-quality issue generation.
- Activate-phase change-request summary view.
- Project-level readiness summary and transparent readiness classification.
- Six recruiter-readable standalone SQL analysis files.
- Read-only SQL runner with explicit Seed-42 headline expectations.
- Read-only dashboard export script with atomic CSV replacement.
- Six deterministic Power BI-ready CSV datasets with validated grains and currency-safe monetary fields.
- Power BI relationship, visual, slicer, and minimal-DAX guidance.
- Completed three-page Power BI dashboard for procurement, invoice/payment, and SAP project-readiness reporting.
- Three real dashboard page screenshots and an optional downloadable PBIX artifact.
- Current payment-eligibility derivation.
- Independent invoice lifecycle and blocking state.
- Independent payment-event result and invoice payment-progress state.
- Phase 1 through Phase 6 validations.
- Integrity, foreign-key, and deterministic regeneration checks.

Not yet implemented:

- SAP API or SAP Learning Hub integration.

Phase 4 matching assumes invoice and PO quantities use the material base unit of measure. Unit-of-measure conversion, tax, freight, and business matching tolerances are not modeled. Generated invoice unit prices use no more than two decimal places. Price equality uses two-decimal monetary comparison, while quantity comparisons use numeric floating-point tolerance.

Phase 5 treats each payment row as one payment instruction or attempt in its current or final state. Only `paid` rows contribute to successful paid amount. Payment progress is derived as `unpaid`, `partially paid`, or `paid` at invoice grain. Current payment eligibility means a new successful payment can be accepted now and therefore also requires positive outstanding balance. Historical payment-fact validation is separate from new-payment candidate eligibility: later blocking or cancellation does not invalidate an existing successful payment, and current header state is not used to reconstruct historical eligibility because state history is not modeled. Cross-table and cumulative payment rules are enforced by deterministic Python validations, while local row invariants remain schema constraints. No database triggers are used.

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
|   |-- validate_sql_queries.py
|   |-- export_dashboard_data.py
|
|-- sql/
|   |-- README.md
|   |-- 01_procurement_spend.sql
|   |-- 02_supplier_delivery_performance.sql
|   |-- 03_open_po_analysis.sql
|   |-- 04_invoice_matching_analysis.sql
|   |-- 05_payment_progress_analysis.sql
|   |-- 06_project_readiness_analysis.sql
|
|-- dashboard/
|   |-- README.md
|   |-- sap_activate_procurement_analytics.pbix
|   |-- data/
|   |   |-- procurement_items.csv
|   |   |-- invoice_matching.csv
|   |   |-- payment_progress.csv
|   |   |-- project_readiness.csv
|   |   |-- project_phases.csv
|   |   |-- project_actions.csv
|   |-- screenshots/
|   |   |-- procurement_overview.png
|   |   |-- invoice_payment.png
|   |   |-- sap_project_readiness.png
|
|-- README.md
|-- PROJECT_CONTEXT.md
|-- .gitattributes
|-- .gitignore
```
