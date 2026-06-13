# SAP Activate Mapping

## Purpose

This document explains how the SAP Activate methodology connects to the SAP Activate ERP Procurement Analytics project. The project is a portfolio-oriented simulation, so the phases are used to structure business thinking, analytics requirements, deliverables, and implementation storytelling.

The goal is to show how procurement analytics can support an SAP S/4HANA implementation from early problem discovery through post-go-live monitoring.

## Phase Mapping

| SAP Activate Phase | Project Activity | Expected Analytics Contribution | Example Deliverables |
| --- | --- | --- | --- |
| Discover | Identify the procurement business problem, high-level pain points, and improvement opportunities. | Translate procurement issues into measurable business questions and candidate KPIs. | Business case, initial pain point list, high-level procurement analytics scope, stakeholder overview. |
| Prepare | Define project scope, stakeholders, planned data sources, and KPI priorities. | Establish the reporting foundation before database design and SQL development begin. | KPI catalog, stakeholder matrix, planned source table list, analytics scope definition. |
| Explore | Review current procurement process gaps and reporting needs through a fit-gap style lens. | Connect reporting requirements to process steps such as requisition, purchase order, goods receipt, invoice, and payment. | Reporting requirement notes, process gap list, KPI-to-process mapping, data quality risk list. |
| Realize | Build the analytical layer for procurement and project KPIs. | Convert agreed KPI definitions into database structures, SQL queries, and analysis outputs. | SQL schema, procurement dataset, KPI queries, analysis documentation, optional dashboard draft. |
| Deploy | Prepare final outputs for stakeholder review and go-live readiness support. | Use analytics to highlight readiness, unresolved risks, testing gaps, and priority operational reports. | Final KPI reports, readiness summary, dashboard screenshots, documentation package. |
| Run | Monitor procurement performance and continuous improvement opportunities after go-live. | Track operational KPIs, supplier performance, invoice exceptions, and project stabilization metrics. | Run-phase KPI dashboard, improvement backlog, recurring procurement performance review pack. |

## Discover

### Project Activity

The Discover phase frames the reason for the project. In this simulation, Marmara Components, a fictional mid-sized manufacturing and industrial components distribution company, has limited visibility into procurement performance and wants better control during an SAP S/4HANA procurement implementation.

Key activities include:

- Define the procurement process problem.
- Identify main stakeholders.
- Capture business pain points.
- Convert pain points into high-level analytics questions.

### Expected Analytics Contribution

Analytics helps make the business problem concrete. Instead of describing procurement issues only in general terms, the project identifies measurable areas such as supplier reliability, purchase order cycle time, invoice matching, spend concentration, and data quality readiness.

### Example Deliverables

- `docs/business_case.md`
- Initial business questions
- Draft procurement KPI themes
- Stakeholder and pain point summary

## Prepare

### Project Activity

The Prepare phase turns the initial concept into a structured project scope. For this repository, that means defining which procurement areas, stakeholder needs, and KPI categories will be included before creating any database schema or SQL queries.

Key activities include:

- Confirm the project scope.
- Define expected source tables.
- Identify procurement and project KPI categories.
- Plan documentation and analytics deliverables.

### Expected Analytics Contribution

Analytics supports scope control. It clarifies which questions will be answered and which tables will likely be needed later, such as vendors, materials, purchase requisitions, purchase orders, goods receipts, invoices, payments, project tasks, defects, and change requests.

### Example Deliverables

- `docs/kpi_catalog.md`
- Planned data source table list
- Analytics scope statement
- KPI prioritization notes

## Explore

### Project Activity

The Explore phase connects the business process to reporting requirements. In a real SAP project, this would include fit-gap workshops and process design discussions. In this portfolio project, the phase is represented by mapping procurement questions to expected analytics outputs.

Key activities include:

- Review procurement process steps.
- Identify where delays, mismatches, or data quality risks may appear.
- Connect each business question to a measurable KPI.
- Define how SAP Activate project KPIs support readiness tracking.

### Expected Analytics Contribution

Analytics contributes evidence for process design and reporting decisions. For example, if invoice mismatch rate is a key metric, the future data model must support comparison between purchase order values, goods receipts, and invoice records.

### Example Deliverables

- Procurement process analytics map
- KPI-to-process mapping
- Data quality risk assumptions
- Reporting requirement list

## Realize

### Project Activity

The Realize phase is where the analytical assets are built. For this project, future Realize work will include creating the database schema, generating realistic ERP-style synthetic data, writing SQL queries, and preparing optional dashboard outputs.

Key activities include:

- Create the procurement database schema.
- Prepare controlled synthetic procurement data.
- Write SQL analysis queries.
- Validate KPI logic against business questions.

### Expected Analytics Contribution

Analytics becomes executable in this phase. KPI definitions from the catalog are translated into SQL logic and reporting outputs. The project should keep every technical object connected to a business question.

### Example Deliverables

- Database schema
- Procurement and project KPI SQL queries
- Analysis result documentation
- Optional Power BI or Tableau dashboard draft

## Deploy

### Project Activity

The Deploy phase prepares the project outputs for final review and go-live readiness storytelling. In a real implementation, this phase would include cutover preparation, training, final testing, and readiness checks.

Key activities include:

- Summarize KPI findings.
- Review unresolved project and procurement risks.
- Prepare final documentation.
- Package portfolio outputs clearly.

### Expected Analytics Contribution

Analytics supports readiness decisions by showing whether key procurement and project indicators are acceptable. Examples include test case pass rate, defect status, data migration readiness, blocked invoice trends, and open purchase order exposure.

### Example Deliverables

- Go-live readiness analytics summary
- Final KPI report
- Dashboard screenshots if created
- Final documentation package

## Run

### Project Activity

The Run phase focuses on post-go-live monitoring and continuous improvement. After SAP S/4HANA is live, procurement analytics should help the business compare performance, monitor exceptions, and identify improvement opportunities.

Key activities include:

- Monitor recurring procurement KPIs.
- Review supplier and purchasing group performance.
- Track invoice exceptions and open items.
- Maintain a continuous improvement backlog.

### Expected Analytics Contribution

Analytics provides the operational feedback loop after go-live. It helps determine whether the implementation improved procurement visibility, process control, and decision-making.

### Example Deliverables

- Run-phase procurement KPI dashboard
- Supplier performance review pack
- Invoice exception monitoring report
- Continuous improvement action list

## Practical Project Interpretation

This repository does not need to reproduce a full enterprise SAP implementation. Instead, it uses SAP Activate as a practical structure for explaining why analytics is needed, how KPIs are selected, how source data is planned, and how SQL analysis can support procurement process improvement.

The most important connection is that each technical deliverable should support a business question and fit into a realistic SAP implementation phase.
