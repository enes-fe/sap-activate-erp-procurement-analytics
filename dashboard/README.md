# Phase 8A Dashboard Data Layer

This directory contains the deterministic CSV import layer for a three-page
Power BI report. The report, PBIX file, and screenshots are intentionally not
included in Phase 8A; they will be created manually after the data model and
visuals are reviewed in Power BI Desktop.

## Refresh the Data

From the repository root:

```powershell
python scripts/generate_data.py --reset
python scripts/validate_sql_queries.py
python scripts/export_dashboard_data.py
```

The export script opens `database/marmara_components.db` with SQLite URI
`mode=ro`, enables `PRAGMA query_only = ON`, validates all six dataset
contracts, and then atomically replaces the files in `dashboard/data/`.

The fixed reporting date is `2026-03-31`. Purchase-order commitment scope is
Q1 2026 and excludes cancelled PO headers and items, matching the Phase 7 SQL
analytics package.

## Exported Datasets

| File | Grain | Seed-42 Rows | Purpose |
| --- | --- | ---: | --- |
| `procurement_items.csv` | One non-cancelled Q1 PO item | 14 | PO commitment, supplier OTIF, fulfillment, and open-item backlog. |
| `invoice_matching.csv` | One eligible invoice item | 5 | Three-way matching status and item-level exception diagnosis. |
| `payment_progress.csv` | One valid posted/approved invoice | 4 | Invoice-level blocking, payment progress, and outstanding balance. |
| `project_readiness.csv` | One project summary | 1 | Existing project-level go-live readiness result and supporting KPIs. |
| `project_phases.csv` | One SAP Activate phase | 6 | Phase task, change-request, and DQ workload. |
| `project_actions.csv` | One management-action record | 9 | Critical task, open CR, and high/critical DQ drill-down. |

`invoice_matching.csv` deliberately excludes `invoice_total_amount`. Header
amounts belong to `payment_progress.csv`; repeating them at invoice-item grain
would create a double-counting risk.

All monetary fields remain attached to `document_currency`,
`invoice_currency`, or `po_currency`. Do not create an unfiltered monetary
total that adds TRY and EUR.

## Power BI Import and Types

Import all six files from `dashboard/data/` as separate text/CSV sources. Use
the filenames without the `.csv` suffix as table names.

Recommended types:

- IDs, names, statuses, descriptions, currencies, units, and flags' labels:
  Text, except numeric flags.
- `*_date` and `reporting_date`: Date.
- `*_flag`, counts, sequence, item numbers, and `backlog_age_days`: Whole
  number.
- Quantities, unit prices, amounts, and percentages: Decimal number.

The CSVs use UTF-8, LF line endings, fixed column order, and explicit row
ordering. Empty database nulls are exported as empty CSV fields.

## Data Model

### Page 1

`procurement_items` is self-contained and requires no relationship.

### Page 2

Create exactly this relationship:

```text
payment_progress[invoice_id]  1  ->  *  invoice_matching[invoice_id]
```

- Cardinality: one-to-many.
- Cross-filter direction: single, from `payment_progress` to
  `invoice_matching`.
- Do not enable bidirectional filtering.
- Header/payment slicers such as invoice currency, vendor, block state, and
  payment progress should use `payment_progress` fields.
- Item-level matching visuals may use `invoice_matching` fields.

### Page 3

Create a one-to-many, single-direction relationship from
`project_phases[activate_phase]` to `project_actions[activate_phase]`.
`project_readiness` should remain disconnected so phase filtering cannot alter
the project-level readiness classification.

## Required DAX Measures

Only these three ratio measures are required. Existing SQL/view KPI columns
should be used directly for all other cards and visuals.

```DAX
PO Item OTIF % =
DIVIDE(
    SUM(procurement_items[otif_flag]),
    SUM(procurement_items[otif_eligible_flag])
)
```

```DAX
Three-Way Matching Exception % =
DIVIDE(
    SUM(invoice_matching[exception_flag]),
    COUNTROWS(invoice_matching)
)
```

```DAX
Invoice Payment Completion % =
DIVIDE(
    SUM(payment_progress[fully_paid_flag]),
    SUM(payment_progress[valid_payment_kpi_flag])
)
```

Format the three measures as percentages with one decimal place.

## Page 1 - Procurement Overview

Business purpose: show where PO commitment is concentrated, how suppliers
perform on item-level OTIF, and which active PO items remain open or overdue.

Dataset: `procurement_items` only.

KPI cards:

- TRY PO Commitment: sum `net_value`, visual filter
  `document_currency = TRY`; expected `7,216.64`.
- EUR PO Commitment: sum `net_value`, visual filter
  `document_currency = EUR`; expected `4,269.30`.
- PO Item OTIF: `PO Item OTIF %`; expected `25.0%` (`3 / 12`).
- Open/Partial PO Items: count `po_item_id`, visual filter
  `fulfillment_status` is `open` or `partial`; expected `5`.

Keep the TRY and EUR cards explicitly currency-specific. If a currency slicer
is added, disable its interaction with these fixed cards when necessary so a
TRY selection does not blank the EUR card, or vice versa.

Recommended visuals:

1. Supplier commitment horizontal bar: `vendor_name` on the axis, sum
   `net_value` as value, and `document_currency` as small multiples. Do not use
   a stacked grand total across currencies.
2. Supplier OTIF horizontal bar: `vendor_name` on the axis and
   `PO Item OTIF %` as value.
3. Open backlog table: `document_currency`, `po_number`, `po_item_number`,
   `vendor_name`, `material_name`, `fulfillment_status`, `open_quantity`,
   `base_unit_of_measure`, `remaining_commitment_value`,
   `planned_delivery_date`, `backlog_due_status`, and `backlog_age_days`.
   Filter to open/partial fulfillment.

Suggested slicers: `document_currency`, `vendor_name`, `plant_name`, and
`material_group_name`.

Seed-42 backlog check: five open/partial items, TRY remaining commitment
`1,118.82`, and EUR remaining commitment `2,245.80`.

## Page 2 - Invoice & Payment

Business purpose: show matching exceptions, invoice blocking reasons, payment
completion, and currency-specific outstanding exposure.

Datasets: `payment_progress` and `invoice_matching`, using the required
single-direction relationship described above.

KPI cards:

- Three-Way Matching Exception Rate: expected `60.0%` (`3 / 5`).
- Blocked Invoice Count: count `invoice_id` filtered to `blocked_flag = 1`;
  expected `3`.
- Invoice Payment Completion: expected `25.0%` (`1 / 4`).
- TRY Outstanding: sum `outstanding_amount`, visual filter
  `invoice_currency = TRY`; expected `1,279.00`.
- EUR Outstanding: sum `outstanding_amount`, visual filter
  `invoice_currency = EUR`; expected `597.00`.

Recommended visuals:

1. Matching exception reasons bar: `matching_status` on the axis, count
   `invoice_item_id` as value, filtered to `exception_flag = 1`.
2. Outstanding amount column chart: `invoice_currency` on the axis and sum
   `outstanding_amount` as value. Do not display a cross-currency grand total.
3. Payment progress 100% stacked bar: `payment_progress_status` as category
   and distinct count `invoice_id` as value.
4. Invoice attention table: `invoice_number`, `vendor_name`,
   `invoice_currency`, `invoice_total_amount`, `invoice_matching_status`,
   `blocked_flag`, `block_reason`, `payment_progress_status`,
   `outstanding_amount`, and `latest_successful_payment_date`.

Header/payment slicers: `payment_progress[invoice_currency]`,
`payment_progress[vendor_name]`, and
`payment_progress[payment_progress_status]`. A matching-status slicer may use
`invoice_matching[matching_status]` when it is intended only for item-level
matching visuals.

## Page 3 - SAP Project Readiness

Business purpose: communicate the existing go-live gate result, phase-level
delivery workload, and the records that need management attention.

Datasets: `project_readiness`, `project_phases`, and `project_actions`.

KPI cards:

- Go-Live Readiness: `not ready`.
- Pre-Go-Live Task Completion: `60.0%` (`6 / 10`).
- Open Change Requests: `3`.
- Unresolved High/Critical DQ Issues: `2`.
- Blocking Critical Tasks: `1`.

Recommended visuals:

1. Pre-go-live completion gauge: value
   `pre_go_live_task_completion_rate_pct`, target `100`.
2. Open CR by phase clustered columns: `activate_phase` on the axis, with
   `open_request_count` and `high_critical_open_request_count` as values. Sort
   by `phase_sequence`.
3. Phase delivery progress bar: `activate_phase` on the axis and
   `average_completion_pct` as value.
4. High/critical DQ attention stacked bar: filter `action_source = data quality
   risk`; use `priority_or_severity` on the axis, `action_status` as legend,
   and count `action_id` as value. Accepted risk remains separate from the
   unresolved DQ KPI.
5. Management action table: `hard_blocker_flag`, `action_source`, `action_id`,
   `activate_phase`, `priority_or_severity`, `action_status`, and
   `action_description`. Use conditional formatting for hard blockers.

Suggested slicers: `activate_phase`, `action_source`, and
`priority_or_severity`.

Seed-42 contains nine management actions and two hard blockers: `TASK-010`
and `DQ-004`. `hard_blocker_flag` is a record-level presentation mapping of the
existing readiness gates; it is not an alternative readiness classification.

## Screenshots and PBIX

`dashboard/screenshots/` is intentionally empty during Phase 8A. After the
Power BI report is manually built and reviewed, export one real 16:9 PNG for
each page using these filenames:

- `procurement_overview.png`
- `invoice_payment.png`
- `project_readiness.png`

Do not add placeholder images. A PBIX may be considered later after file size,
portable data-source configuration, and credential safety are reviewed.

## Validation

Run the complete Phase 8A validation sequence from the repository root:

```powershell
python scripts/generate_data.py --reset
python scripts/validate_sql_queries.py
python scripts/export_dashboard_data.py
python -m py_compile scripts/export_dashboard_data.py
git diff --check
python scripts/export_dashboard_data.py
git diff --exit-code -- dashboard/data
```

The final two commands prove that a repeat export produces no changes to the
committed dashboard CSV snapshot.
