# Business Case

## Fictional Company Scenario

Marmara Components is a fictional mid-sized manufacturing and industrial components distribution company with operations across several regional plants. The company purchases raw materials, maintenance supplies, packaging materials, and indirect services from a broad vendor base.

As the business has grown, procurement activities have become harder to monitor consistently. Purchasing teams use different local practices, finance teams need better invoice visibility, and project stakeholders want to understand whether procurement processes are ready for an SAP S/4HANA implementation.

The company is preparing a procurement-focused SAP S/4HANA implementation using the SAP Activate methodology. The project does not represent a live SAP system. It is a portfolio-ready analytics simulation that shows how procurement data and project KPIs can support business decisions during an ERP transformation.

## Procurement Process Problem

The current procurement process has limited end-to-end visibility from purchase requisition to purchase order, goods receipt, invoice verification, and payment. Procurement managers can see individual transactions, but they do not have a clear analytical view of process performance, supplier reliability, spend patterns, invoice exceptions, or project readiness.

This creates a practical challenge during the SAP implementation. If process issues and data quality risks are not visible early, the project may carry existing inefficiencies into the new ERP environment. The organization needs clear KPIs and business questions before building SQL analysis, reports, and dashboards.

## Stakeholders

| Stakeholder | Role in the Project | Analytics Need |
| --- | --- | --- |
| Procurement managers | Own purchasing performance and supplier relationships | Spend visibility, supplier reliability, cycle time, open orders |
| Buyers and purchasing groups | Execute daily procurement activities | Order processing efficiency, bottlenecks, overdue items |
| Finance and controlling teams | Manage invoice verification, payments, and spend control | Invoice mismatches, blocked invoices, payment readiness, spend categories |
| SAP consultants | Configure and support SAP S/4HANA procurement processes | Fit-gap evidence, KPI definitions, process readiness indicators |
| Business analysts | Translate business needs into reporting requirements | Clear business questions, data sources, KPI logic |
| Project managers | Monitor implementation progress and risks | Phase status, task completion, defects, change requests, go-live readiness |
| Key users | Validate future-state processes and reports | User acceptance feedback, test results, practical reporting needs |

## Business Pain Points

- Limited visibility into total procurement spend by vendor, material group, plant, and purchasing group.
- Unclear supplier delivery performance and late delivery patterns.
- Difficulty identifying bottlenecks between requisition creation, purchase order approval, goods receipt, invoice receipt, and payment.
- Invoice and goods receipt mismatches that create manual work for finance and procurement teams.
- Open purchase orders and blocked invoices that are not consistently monitored.
- Inconsistent master data quality for vendors, materials, purchasing groups, and process ownership.
- Lack of structured project KPIs to connect SAP Activate activities with procurement readiness.
- Risk that process issues are discovered too late during testing, deployment, or early Run phase support.

## Why Procurement Analytics Is Needed During SAP S/4HANA Implementation

Procurement analytics helps the implementation team move from assumptions to evidence. During SAP Activate, business process design, data readiness, configuration validation, testing, and go-live preparation all depend on clear information about current and expected procurement performance.

Analytics is especially useful because procurement touches multiple business areas. A purchase order delay can affect production planning, goods receipt accuracy, invoice processing, supplier relationships, and working capital. By defining KPIs early, the project team can evaluate whether the future SAP process improves visibility, control, and operational performance.

For this project, procurement analytics supports:

- Discovering pain points and priority business questions.
- Defining KPI requirements before data modeling and SQL development.
- Mapping process gaps during Explore workshops.
- Building measurable outputs during Realize.
- Supporting test and go-live readiness during Deploy.
- Monitoring continuous improvement after go-live during Run.

## Business Questions

This project is designed to answer practical procurement and SAP implementation questions such as:

- Which vendors represent the highest procurement spend?
- Which suppliers are most frequently late or unreliable?
- Which material groups drive the largest purchase volume?
- Which plants or purchasing groups have the longest purchase order cycle times?
- Where do invoice mismatches occur most often?
- Which purchase orders remain open beyond the expected processing window?
- Which procurement activities create the most manual follow-up work?
- What master data quality issues could affect SAP S/4HANA readiness?
- Which SAP Activate phase has the highest number of open issues or change requests?
- Are testing, data migration, and user readiness indicators strong enough for go-live?
- Which procurement KPIs should continue to be monitored after go-live?

## Expected Business Value

The expected value of this analytics project is not only technical reporting. The main value is connecting procurement process understanding with SAP implementation decision-making.

A clear procurement analytics layer can help the company:

- Prioritize process improvements before go-live.
- Align stakeholders around measurable KPIs.
- Improve supplier performance management.
- Reduce invoice exception handling effort.
- Support cleaner master data and transaction data.
- Improve transparency for project managers and business owners.
- Demonstrate how SQL-based analysis can support real ERP transformation work.
