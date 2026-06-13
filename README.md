# SAP Activate ERP Procurement Analytics

## Project Description

This project is a portfolio-oriented data analytics and SAP implementation simulation project. It combines SAP Activate project methodology, ERP procurement business processes, and SQL-based business analytics.

The project will simulate a company preparing or executing an SAP S/4HANA procurement-related implementation. Instead of building a live SAP system, the repository will create a realistic analytical environment around procurement data such as suppliers, materials, purchase orders, goods receipts, invoices, payments, and project KPIs.

## Business Problem

A fictional mid-sized company wants better visibility into its procurement process during an SAP S/4HANA implementation or improvement initiative.

The business needs to understand:

- Supplier performance and reliability
- Purchase order processing efficiency
- Delivery delays and bottlenecks
- Goods receipt and invoice matching issues
- Procurement spend distribution
- Material category performance
- Data quality and readiness risks
- Project KPI status before and after go-live

The goal is to support stakeholders such as procurement managers, SAP consultants, business analysts, project managers, key users, and finance teams with clear SQL-based analysis.

## SAP Activate Connection

The project is framed around the SAP Activate methodology:

- Discover: Identify procurement pain points and high-level business questions.
- Prepare: Define scope, stakeholders, KPIs, and planned data sources.
- Explore: Map reporting requirements, process gaps, and analytics needs.
- Realize: Build the database, SQL queries, KPI logic, and optional dashboard.
- Deploy: Prepare final reporting outputs and documentation.
- Run: Monitor procurement KPIs and continuous improvement opportunities.

The analytics work will connect technical outputs to SAP implementation phases, especially procurement process readiness, data quality, testing, and operational KPI monitoring.

## Planned Tech Stack

- SQL for analytics queries
- PostgreSQL or SQLite for the database layer
- Python for data generation and preprocessing
- pandas for synthetic dataset preparation
- Markdown for documentation
- Power BI or Tableau for an optional dashboard layer
- GitHub for project presentation

## Planned Deliverables

- Clean procurement analytics database schema
- Realistic synthetic ERP-style procurement dataset
- SQL queries for procurement KPIs
- SQL queries for SAP Activate project KPIs
- Business KPI catalog
- SAP Activate mapping documentation
- Business case documentation
- Optional dashboard or dashboard screenshots
- Final portfolio-ready README

## Current Project Status

Initial setup stage.

Completed so far:

- Project context defined in `PROJECT_CONTEXT.md`
- Initial folder structure created
- Initial README draft created

Not created yet:

- Synthetic data
- SQL database schema
- SQL analysis queries
- Dashboard files

## Next Steps

1. Define the detailed business case in `docs/business_case.md`.
2. Create the SAP Activate mapping document in `docs/sap_activate_mapping.md`.
3. Draft the KPI catalog in `docs/kpi_catalog.md`.
4. Design the procurement data model and ERD.
5. Create the SQL schema after the data model is confirmed.
6. Generate realistic synthetic ERP-style procurement data.
7. Build SQL analytics queries for procurement and project KPIs.
