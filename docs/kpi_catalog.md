# KPI Catalog

## Purpose

This KPI catalog defines the procurement and SAP Activate project KPIs for the SAP Activate ERP Procurement Analytics project. The data model is implemented for the current Phase 6 scope, but not every KPI in this catalog has been implemented as a separate SQL query file yet.

The current repository includes SQLite views and generator validation logic for item fulfillment, delivery performance, invoice three-way matching, invoice payment progress, change requests, data-quality readiness, and go-live readiness classification. Spend and dashboard-ready SQL query packages remain planned work.

## KPI Prioritization

Core KPIs are the priority analytics scope for the first complete portfolio version. Extended KPIs support deeper analysis after the core query package and documentation are stable.

### Core KPIs

- Total Procurement Spend
- Spend by Vendor
- Spend by Material Group
- Purchase Order Cycle Time
- PO Item On-Time In-Full Rate
- Average Delivery Delay
- Goods Receipt vs Invoice Mismatch Rate
- Blocked Invoice Count
- Invoice Payment Completion Rate
- Outstanding Invoice Amount by Currency
- Open Purchase Order Count and Open Quantity
- Unresolved High/Critical Data Quality Issue Count
- Data Quality Resolution Rate
- Go-Live Readiness Classification

### Extended or Supporting KPIs

- Receipt Event On-Time Rate
- Purchase Order Volume
- Requisition to Purchase Order Conversion Time
- Late Delivery Rate
- Average Invoice Processing Time
- Maverick Buying Indicator
- Supplier Reliability Score
- Purchasing Group Efficiency
- Open Change Request Count
- High/Critical Open Change Request Count
- Vendor Master Data Completeness
- Material Master Data Completeness
- Project Task Completion Rate
- Open Issues by Phase
- Change Request Count by Phase
- Test Case Pass Rate
- Defect Rate by Process Area

## Current Implementation Status

Implemented through Phase 6:

- PO Item On-Time In-Full Rate.
- Receipt Event On-Time Rate.
- Average Delivery Delay across late receipt events.
- Item fulfillment and open quantity logic.
- PO header fulfillment rollup.
- Goods Receipt vs Invoice Mismatch Rate.
- Blocked Invoice Count.
- Item-level three-way matching and invoice-level matching summary.
- Invoice Payment Completion Rate.
- Outstanding Invoice Amount by Currency.
- Successful Paid Amount by Currency as a supporting measure.
- Invoice-level current payment eligibility and payment-progress summary.
- Open Change Request Count and High/Critical Open Change Request Count.
- Change Request Count by Phase.
- Unresolved High/Critical Data Quality Issue Count.
- Data Quality Resolution Rate and supporting disposition rate.
- Go-Live Readiness Classification.

Planned:

- Separate spend query files.
- Dashboard-ready output tables or extracts.

## Primary Delivery KPI: PO Item On-Time In-Full Rate

Business question:

What percentage of due active PO items were fully fulfilled with accepted quantity on or before the planned delivery date?

Denominator:

- Active PO header.
- Active PO item.
- `planned_delivery_date` on or before the selected reporting date.

Numerator:

- Cumulative posted accepted quantity reaches ordered quantity.
- `fulfillment_date` is on or before `planned_delivery_date`.

Expected source objects:

- `purchase_orders`
- `purchase_order_items`
- `goods_receipts`
- `vw_po_item_fulfillment`
- `vw_po_item_delivery_performance`
- `vendors`

Why this is the primary supplier-reliability metric:

- It evaluates complete business fulfillment, not only physical receipt activity.
- It avoids overweighting split deliveries because each PO item contributes once.
- Rejected quantity does not count toward fulfillment.
- It connects supplier reliability to the PO item that procurement needs fulfilled.

## Secondary Delivery Diagnostic: Receipt Event On-Time Rate

Priority: Extended / supporting diagnostic.

Business question:

What percentage of posted receipt events occurred on or before the planned delivery date?

Logic:

- Count relevant posted receipt events with `receipt_date` on or before `planned_delivery_date`.
- Divide by total relevant posted receipt events.

This is useful for operational diagnostics, but it is not the primary supplier fulfillment KPI. One PO item with multiple receipts contributes multiple events, so a split delivery can influence this rate more than a single complete item delivery.

## Invoice Matching KPIs

### Three-Way Matching Exception Rate

Business question:

What percentage of invoice items fail the PO, eligible accepted goods receipt, and invoice comparison?

Denominator:

- Non-cancelled invoice items.
- Cancelled and invalid zero-item invoice headers contribute no items.

Numerator:

- Invoice items whose derived `matching_status` is not `matched`.
- Exception types include price mismatch, quantity mismatch, combined quantity-and-price mismatch, and missing goods receipt.

Eligible accepted quantity includes only `receipt_status = 'posted'` receipt quantity for the same PO item where `receipt_date <= invoice_received_date`. A later receipt does not retroactively change the matching state that existed when the invoice was received.

### Blocked Invoice Count

Business question:

How many invoice headers are blocked from payment release or further processing?

Calculation:

- Count invoice headers where `blocked_flag = 1`.
- `invoice_status` is not used as a blocking indicator.
- Exclude headers whose matching-summary status is `excluded` or `invalid`.
- The deterministic Phase 4 dataset validates that an invoice is blocked when at least one item has a matching exception.

## Payment Progress KPIs

### Invoice Payment Completion Rate

Business question:

What percentage of valid posted or approved invoices have been fully paid?

Denominator:

- Invoice status is `posted` or `approved`.
- Invoice matching status is not `excluded` or `invalid`.
- Blocked invoices remain in the denominator because this is an end-to-end invoice-closure KPI.

Numerator:

- Invoice payment progress is `paid`.

Only `payment_status = 'paid'` rows contribute to invoice payment progress. Payment-row statuses never represent invoice-level partial payment.

### Outstanding Invoice Amount by Currency

Business question:

How much valid invoice value remains unpaid in each invoice currency?

Calculation:

- Sum `outstanding_amount` from `vw_invoice_payment_progress`.
- Exclude cancelled and invalid invoices, whose outstanding amount is null.
- Group by `invoice_currency`.
- Never add different currencies together because Phase 5 does not perform FX conversion.

Successful Paid Amount by Currency is a supporting measure from the same view. It sums `successful_paid_amount` by invoice currency and includes only successful payment events.

Average Days to Payment is not a core Phase 5 KPI. A future diagnostic may measure posting-to-full-payment duration, but the current deterministic dataset contains only one fully paid invoice and does not model payment due dates.

## Phase 6 Project Readiness KPIs

### Open Change Request Count

Count requests whose status is `submitted`, `under review`, or `approved`. Approved requests remain open until implemented. Deferred, rejected, implemented, and cancelled requests are not open.

Expected result: 3.

### High/Critical Open Change Request Count

Count open requests whose priority is `high` or `critical`.

Expected result: 2.

### Unresolved High/Critical Data Quality Issue Count

Count issues whose status is `open` or `in progress` and whose severity is `high` or `critical`. Accepted risk is reported separately and is not unresolved.

Expected result: 2.

### Data Quality Resolution Rate

Divide resolved issues by all non-cancelled issues. Cancelled issues are excluded from the denominator. Accepted-risk issues remain in the denominator but not the numerator because they have not been fixed. A zero denominator returns null.

Expected result: 3 / 6 = 50.0%.

Data Quality Disposition Rate is a supporting diagnostic: resolved plus accepted-risk issues divided by non-cancelled issues. Its expected result is 4 / 6 = 66.7%. It must not be described as a resolution rate.

### Go-Live Readiness Classification

The classification uses Discover through Deploy tasks; Run tasks are outside the go-live gate.

Precedence:

1. `not ready`: a critical pre-go-live task is blocked, delayed, or cancelled; a critical change request is open; or a critical data-quality issue is open/in progress.
2. `at risk`: no not-ready condition exists, but a critical pre-go-live task is incomplete; a high-priority request is open; a high-severity issue is unresolved; or a high/critical issue is accepted risk.
3. `ready`: none of the preceding conditions exists.

Expected result: `not ready`, caused independently by blocked critical Deploy task `TASK-010` and open critical issue `DQ-004`.

## KPI Table

| KPI Name | Priority | Category | Business Question | Calculation Logic in Plain English | Expected Source Objects | Current Status |
| --- | --- | --- | --- | --- | --- | --- |
| Total Procurement Spend | Core | Procurement Spend | What is the total value of procurement activity? | Add the net value of all relevant purchase order items within the selected period. | `purchase_orders`, `purchase_order_items` | Planned query file. |
| Spend by Vendor | Core | Procurement Spend | Which vendors receive the highest spend? | Group purchase order item values by vendor and rank vendors by total spend. | `vendors`, `purchase_orders`, `purchase_order_items` | Planned query file. |
| Spend by Material Group | Core | Procurement Spend | Which material groups drive the largest procurement cost? | Group purchase order item values by material group and compare total spend across groups. | `materials`, `material_groups`, `purchase_order_items` | Planned query file. |
| Purchase Order Volume | Extended | Procurement Operations | How many purchase orders are created in a selected period? | Count purchase orders created within the selected date range. | `purchase_orders` | Planned. |
| Purchase Order Cycle Time | Core | Procurement Efficiency | How long does it take to process a purchase order? | Measure days between requisition creation or approval and purchase order creation or approval where conversion links exist. | `purchase_requisitions`, `purchase_requisition_items`, `purchase_orders`, `purchase_order_items` | Planned query file. |
| Requisition to Purchase Order Conversion Time | Extended | Procurement Efficiency | How quickly are approved requisitions converted into purchase orders? | Measure days between requisition approval and purchase order creation. | `purchase_requisitions`, `purchase_requisition_items`, `purchase_orders`, `purchase_order_items` | Planned. |
| PO Item On-Time In-Full Rate | Core | Supplier Performance | What percentage of due active PO items were fully fulfilled with accepted quantity on or before the planned delivery date? | Count due active PO items where cumulative posted accepted quantity reaches ordered quantity on or before the planned date, then divide by due active PO items. | `purchase_orders`, `purchase_order_items`, `goods_receipts`, `vw_po_item_fulfillment`, `vw_po_item_delivery_performance`, `vendors` | Implemented in Phase 3 validation logic. |
| Receipt Event On-Time Rate | Extended | Supplier Performance | What percentage of receipt events were posted on or before the planned delivery date? | Count posted receipt events on or before planned delivery date and divide by relevant posted receipt events. | `goods_receipts`, `purchase_order_items`, `purchase_orders`, `vendors` | Implemented in Phase 3 validation logic. |
| Late Delivery Rate | Extended | Supplier Performance | Which suppliers or material groups are frequently late? | Count late PO items or late receipt events and divide by the relevant denominator selected for the report. | `vw_po_item_delivery_performance`, `goods_receipts`, `purchase_order_items`, `vendors`, `materials` | Planned supplier-level reporting. |
| Average Delivery Delay | Core | Supplier Performance | When deliveries are late, how many calendar days late are they on average? | For late receipt events, calculate the average calendar-day difference between planned delivery date and receipt date. Future reports may group this by vendor. | `goods_receipts`, `purchase_order_items`, `vendors` | Implemented in Phase 3 validation logic. |
| Open Purchase Order Count | Core | Procurement Operations | How many purchase orders or PO items remain open? | Count active PO headers or items with derived open or partial fulfillment. | `vw_po_fulfillment`, `vw_po_item_fulfillment`, `purchase_orders`, `purchase_order_items` | Partially implemented through views. |
| Open PO Quantity | Core | Procurement Operations | How much ordered quantity remains unfulfilled? | Calculate `MAX(ordered quantity - effective posted accepted quantity, 0)` at item level. Rejected and under-review quantities do not close the PO item. | `vw_po_item_fulfillment` | Implemented in Phase 3 view logic. |
| Goods Receipt vs Invoice Mismatch Rate | Core | Invoice and Matching | How often do invoice records differ from goods receipt or purchase order expectations? | Count non-cancelled invoice items whose derived matching status is not matched, then divide by non-cancelled invoice items. Eligible receipt quantity uses posted accepted quantity as of invoice receipt. | `vw_invoice_item_three_way_match`, `purchase_order_items`, `goods_receipts`, `invoices`, `invoice_items` | Implemented in Phase 4 view and validation logic. |
| Blocked Invoice Count | Core | Invoice and Matching | How many eligible invoices are blocked for payment release or review? | Count invoice headers where `blocked_flag = 1` and summary status is `matched` or `exception`. Cancelled and invalid zero-item headers are excluded. | `invoices`, `vw_invoice_matching_summary`, `vendors` | Implemented in Phase 4 validation logic. |
| Invoice Payment Completion Rate | Core | Payment Progress | What percentage of valid posted or approved invoices have been fully paid? | Count invoices with derived payment progress `paid` and divide by valid posted or approved non-cancelled invoices. Blocked invoices remain in the denominator. | `invoices`, `payments`, `vw_invoice_payment_progress` | Implemented in Phase 5 view and validation logic. |
| Outstanding Invoice Amount by Currency | Core | Payment Progress | How much valid invoice value remains unpaid in each currency? | Sum derived outstanding amount for valid invoices and group by invoice currency. Never aggregate different currencies together. | `invoices`, `payments`, `vw_invoice_payment_progress` | Implemented in Phase 5 view and validation logic. |
| Average Invoice Processing Time | Extended | Invoice and Matching | How long does it take to process supplier invoices? | Measure days between invoice receipt and posting or payment release. | `invoices`, `payments` | Planned. |
| Maverick Buying Indicator | Extended | Procurement Compliance | Are purchases happening outside expected procurement channels or preferred suppliers? | Flag purchases that do not reference preferred vendors, expected purchasing groups, or standard material categories. | `vendors`, `materials`, `purchase_orders`, `purchase_order_items`, `purchasing_groups` | Planned. |
| Supplier Reliability Score | Extended | Supplier Performance | Which suppliers are most reliable overall? | Combine item OTIF, delay severity, mismatch frequency, blocked invoice count, and fulfillment consistency into a weighted score. | `vendors`, `purchase_orders`, `purchase_order_items`, `goods_receipts`, `invoices` | Planned composite metric. |
| Purchasing Group Efficiency | Extended | Procurement Efficiency | Which purchasing groups process orders most efficiently? | Compare cycle time, open order count, and purchase order volume by purchasing group. | `purchasing_groups`, `purchase_requisitions`, `purchase_orders`, `purchase_order_items` | Planned. |
| Unresolved High/Critical Data Quality Issue Count | Core | Data Readiness | How many material data risks remain unresolved? | Count open or in-progress issues whose severity is high or critical; accepted risk is reported separately. | `data_quality_issues`, `vw_project_readiness_summary` | Implemented in Phase 6 view and validation logic. |
| Data Quality Resolution Rate | Core | Data Readiness | What share of non-cancelled issues has been fixed? | Divide resolved issues by non-cancelled issues. Accepted risk remains in the denominator but not the numerator; return null for a zero denominator. | `data_quality_issues`, `vw_project_readiness_summary` | Implemented in Phase 6 view and validation logic. |
| Go-Live Readiness Classification | Core | SAP Activate Project | Is the procurement workstream ready for go-live? | Apply explicit not-ready, at-risk, and ready precedence to pre-go-live critical tasks, open high/critical requests, unresolved high/critical issues, and accepted high/critical risks. | `sap_activate_project_tasks`, `change_requests`, `data_quality_issues`, `vw_project_readiness_summary` | Implemented in Phase 6 view and validation logic. |
| Project Task Completion Rate | Extended | SAP Activate Project | Is the implementation progressing according to plan? | Divide completed project tasks by total planned project tasks, optionally grouped by SAP Activate phase. | `sap_activate_project_tasks` | Data generated; separate query file planned. |
| Open Change Request Count | Extended | SAP Activate Project | How many submitted, under-review, or approved requests remain unimplemented? | Count submitted, under-review, and approved requests. Deferred, rejected, implemented, and cancelled requests are not open. | `change_requests`, `vw_change_request_phase_summary`, `vw_project_readiness_summary` | Implemented in Phase 6 view and validation logic. |
| High/Critical Open Change Request Count | Extended | SAP Activate Project | How many open requests require elevated management attention? | Count open requests whose priority is high or critical. | `change_requests`, `vw_change_request_phase_summary`, `vw_project_readiness_summary` | Implemented in Phase 6 view and validation logic. |

## Current Deterministic Dataset Example

The current synthetic dataset validates these Phase 3 delivery-performance results using reporting date `2026-03-31`:

- PO Item On-Time In-Full Rate: 3 / 12 = 25.0%.
- Receipt Event On-Time Rate: 5 / 10 = 50.0%.
- Average late-event delay: 2.2 calendar days.

These values validate the deterministic synthetic scenario. They are not target benchmarks for a real procurement organization.

The Phase 4 deterministic invoice dataset validates:

- Matched invoice items: 2.
- Matching exception items: 3.
- Three-Way Matching Exception Rate: 3 / 5 = 60.0%.
- Price mismatch items: 1.
- Quantity mismatch items: 1.
- Missing-goods-receipt items: 1.
- Blocked Invoice Count: 3.

The Phase 5 deterministic payment dataset validates:

- Payment instructions or attempts: 5.
- Successful payments: 2, both against INV-001.
- Successful paid amount: TRY 2,770.20 and EUR 0.00.
- Invoice Payment Completion Rate: 1 / 4 = 25.0%.
- Outstanding Invoice Amount: TRY 1,279.00 and EUR 597.00.
- Failed, cancelled, scheduled, and on-hold payments contribute zero to successful paid amount.

The Phase 6 deterministic project-readiness dataset validates:

- Change requests: 6 total, 3 open, and 2 high/critical open.
- Data-quality issues: 7 total, 6 non-cancelled, 3 resolved, 1 accepted risk, and 2 unresolved.
- Unresolved High/Critical Data Quality Issue Count: 2.
- Data Quality Resolution Rate: 3 / 6 = 50.0%.
- Data Quality Disposition Rate: 4 / 6 = 66.7%.
- Go-Live Readiness Classification: `not ready`.
- Permanent hard blockers: `TASK-010` and `DQ-004`.

## Notes

- KPI definitions should stay connected to business questions and SAP implementation use cases.
- The current delivery-performance implementation uses accepted quantity, not physical received quantity, to determine fulfillment.
- Invoice matching assumes invoice and PO quantities use the material base unit of measure. Unit-of-measure conversion, tax, freight, and business matching tolerances are outside Phase 4.
- Generated invoice unit prices use no more than two decimal places. Price comparison uses two-decimal monetary values. Quantity comparisons use floating-point tolerance only.
- Payment amount inherits invoice currency. The model does not store a duplicate payment currency or perform FX conversion.
- Payment progress is derived from successful payment events and is not stored on invoices or individual payment rows.
- Change-request status, data-quality issue status, and task status remain separate concepts.
- Accepted risk is not resolved. It contributes to the supporting disposition rate and to at-risk readiness when severity is high or critical.
- Future SQL query files should use the current schema and views as source objects rather than duplicating fulfillment, matching, payment-progress, or readiness logic.
