# KPI Catalog

## Purpose

This KPI catalog defines the procurement and SAP Activate project KPIs planned for the SAP Activate ERP Procurement Analytics project. The logic is written in plain English only. SQL will be created later after the data model is confirmed.

## KPI Prioritization

Not all KPIs have the same importance in the first portfolio version. The initial implementation should focus on a smaller set of high-value KPIs that clearly demonstrate procurement analytics, operational control, invoice matching, data readiness, and SAP Activate go-live preparation.

Core KPIs are the first KPIs that will be implemented in SQL. They represent the priority analytics scope for the first complete portfolio version.

Extended KPIs are additional KPIs that may be implemented later after the core SQL queries, data model, and portfolio explanation are stable.

### Core KPIs

- Total Procurement Spend
- Spend by Vendor
- Spend by Material Group
- Purchase Order Cycle Time
- On-Time Delivery Rate
- Average Delivery Delay
- Goods Receipt vs Invoice Mismatch Rate
- Blocked Invoice Count
- Open Purchase Order Count
- Data Migration Readiness
- Go-Live Readiness Score

All KPIs not listed above are classified as Extended KPIs for the first portfolio version.

## KPI Table

| KPI Name | Priority | Category | Business Question | Calculation Logic in Plain English | Expected Data Source Tables | Why It Matters |
| --- | --- | --- | --- | --- | --- | --- |
| Total Procurement Spend | Core | Procurement Spend | What is the total value of procurement activity? | Add the net value of all relevant purchase order items within the selected period. | `purchase_orders`, `purchase_order_items` | Shows overall procurement volume and supports budget, category, and supplier analysis. |
| Spend by Vendor | Core | Procurement Spend | Which vendors receive the highest spend? | Group purchase order item values by vendor and rank vendors by total spend. | `vendors`, `purchase_orders`, `purchase_order_items` | Identifies strategic suppliers, concentration risk, and negotiation opportunities. |
| Spend by Material Group | Core | Procurement Spend | Which material groups drive the largest procurement cost? | Group purchase order item values by material group and compare total spend across groups. | `materials`, `material_groups`, `purchase_order_items` | Helps category managers prioritize sourcing and cost control activities. |
| Purchase Order Volume | Extended | Procurement Operations | How many purchase orders are created in a selected period? | Count purchase orders created within the selected date range. | `purchase_orders` | Measures procurement workload and supports trend analysis by plant or purchasing group. |
| Purchase Order Cycle Time | Core | Procurement Efficiency | How long does it take to process a purchase order? | Measure the number of days between purchase requisition creation and purchase order creation or approval. | `purchase_requisitions`, `purchase_orders` | Reveals process delays before suppliers receive orders. |
| Requisition to Purchase Order Conversion Time | Extended | Procurement Efficiency | How quickly are approved requisitions converted into purchase orders? | Measure the number of days between requisition approval and purchase order creation. | `purchase_requisitions`, `purchase_orders` | Highlights bottlenecks in buyer workload, approval flow, or sourcing decisions. |
| On-Time Delivery Rate | Core | Supplier Performance | What percentage of supplier deliveries arrive on or before the expected delivery date? | Count goods receipts received on or before the planned delivery date and divide by total relevant goods receipts. | `purchase_orders`, `purchase_order_items`, `goods_receipts`, `vendors` | Measures supplier reliability and supports supplier performance reviews. |
| Late Delivery Rate | Extended | Supplier Performance | Which suppliers or material groups are frequently late? | Count goods receipts received after the planned delivery date and divide by total relevant goods receipts. | `purchase_orders`, `purchase_order_items`, `goods_receipts`, `vendors`, `materials` | Helps identify delivery risk that may affect production, inventory, or service levels. |
| Average Delivery Delay | Core | Supplier Performance | When deliveries are late, how many days late are they on average? | For late goods receipts, calculate the average number of days between planned delivery date and actual receipt date. | `purchase_order_items`, `goods_receipts`, `vendors` | Quantifies the severity of supplier delays rather than only the frequency. |
| Goods Receipt vs Invoice Mismatch Rate | Core | Invoice and Matching | How often do invoice records differ from goods receipt or purchase order expectations? | Count invoice items with quantity or value differences compared with goods receipt or purchase order records, then divide by total invoice items. | `purchase_order_items`, `goods_receipts`, `invoices` | Indicates manual reconciliation effort and potential control issues. |
| Blocked Invoice Count | Core | Invoice and Matching | How many invoices are blocked for payment or review? | Count invoices with a blocked, disputed, or exception status. | `invoices`, `vendors` | Shows finance workload and highlights issues delaying supplier payment. |
| Average Invoice Processing Time | Extended | Invoice and Matching | How long does it take to process supplier invoices? | Measure the number of days between invoice receipt date and invoice posting or payment release date. | `invoices`, `payments` | Helps evaluate finance process efficiency and payment readiness. |
| Open Purchase Order Count | Core | Procurement Operations | How many purchase orders remain open? | Count purchase orders or purchase order items that are not fully received, invoiced, closed, or cancelled. | `purchase_orders`, `purchase_order_items`, `goods_receipts`, `invoices` | Supports operational follow-up and prevents old commitments from remaining unmanaged. |
| Maverick Buying Indicator | Extended | Procurement Compliance | Are purchases happening outside expected procurement channels or preferred suppliers? | Flag purchases that do not reference approved vendors, expected purchasing groups, or standard material categories. | `vendors`, `materials`, `purchase_orders`, `purchase_order_items`, `purchasing_groups` | Helps identify compliance risk and opportunities to improve guided buying. |
| Supplier Reliability Score | Extended | Supplier Performance | Which suppliers are most reliable overall? | Combine delivery timeliness, mismatch frequency, blocked invoice count, and order fulfillment consistency into a weighted score. | `vendors`, `purchase_orders`, `purchase_order_items`, `goods_receipts`, `invoices` | Provides a practical supplier comparison metric for sourcing and performance reviews. |
| Purchasing Group Efficiency | Extended | Procurement Efficiency | Which purchasing groups process orders most efficiently? | Compare cycle time, open order count, and purchase order volume by purchasing group. | `purchasing_groups`, `purchase_requisitions`, `purchase_orders`, `purchase_order_items` | Helps managers understand workload, process bottlenecks, and team performance. |
| Data Quality Issue Count | Extended | Data Readiness | How many known data quality issues exist before migration or reporting? | Count open records classified as master data, transaction data, duplicate, missing value, or inconsistent reference issues. | `data_quality_issues`, `vendors`, `materials`, `purchase_orders` | Data quality affects migration, reporting accuracy, user trust, and go-live readiness. |
| Vendor Master Data Completeness | Extended | Data Readiness | Are vendor master records complete enough for SAP S/4HANA use? | Calculate the percentage of vendor records with required fields populated, such as vendor name, country, payment terms, and status. | `vendors`, `data_quality_issues` | Incomplete vendor data can cause purchasing, invoice, and payment issues. |
| Material Master Data Completeness | Extended | Data Readiness | Are material records complete enough for procurement reporting and operations? | Calculate the percentage of material records with required fields populated, such as material group, unit of measure, plant relevance, and status. | `materials`, `material_groups`, `data_quality_issues` | Clean material data supports accurate purchasing, category analysis, and reporting. |
| Project Task Completion Rate | Extended | SAP Activate Project | Is the SAP implementation progressing according to plan? | Divide completed project tasks by total planned project tasks, optionally grouped by SAP Activate phase. | `sap_activate_project_tasks` | Gives project managers a simple view of delivery progress. |
| Open Issues by Phase | Extended | SAP Activate Project | Which SAP Activate phase has the most unresolved issues? | Count open project issues or risks by assigned SAP Activate phase. | `sap_activate_project_tasks`, `change_requests`, `data_quality_issues` | Helps focus management attention on phases with unresolved blockers. |
| Change Request Count by Phase | Extended | SAP Activate Project | Where are scope or requirement changes occurring most often? | Count change requests by SAP Activate phase and status. | `change_requests`, `sap_activate_project_tasks` | Shows scope pressure and helps manage timeline, cost, and design stability. |
| Data Migration Readiness | Core | SAP Activate Project | Is procurement data ready for migration or reporting use? | Compare resolved data quality issues, required master data completeness, and migration validation status against readiness criteria. | `data_quality_issues`, `vendors`, `materials`, `purchase_orders` | Data readiness is critical for testing, cutover, reporting accuracy, and go-live confidence. |
| Test Case Pass Rate | Extended | SAP Activate Project | Are procurement processes passing validation tests? | Divide passed procurement test cases by total executed procurement test cases. | `sap_activate_project_tasks` | Indicates whether configured processes and reports are ready for deployment. |
| Defect Rate by Process Area | Extended | SAP Activate Project | Which procurement process areas have the most defects? | Count defects or failed test items by process area, such as requisition, purchase order, goods receipt, invoice, or payment. | `sap_activate_project_tasks`, `change_requests` | Helps prioritize stabilization work before go-live. |
| Go-Live Readiness Score | Core | SAP Activate Project | Is the procurement workstream ready for go-live? | Combine selected readiness indicators such as task completion, critical open issues, data readiness, test pass rate, and unresolved defects into a weighted readiness score. | `sap_activate_project_tasks`, `change_requests`, `data_quality_issues` | Provides a management-level view of whether the procurement workstream is ready to deploy. |

## Notes

- KPI logic is intentionally written in business language at this stage.
- SQL expressions, joins, and exact field names should be added only after the data model is confirmed.
- Every KPI should remain connected to a business question and an SAP implementation use case.
