# PROJECT_CONTEXT.md

# SAP Activate ERP Procurement Analytics Project

## 1. Project Overview

This project is a portfolio-oriented data analytics and SAP implementation simulation project.

The main idea is to combine three areas:

1. SAP Activate project methodology
2. ERP procurement business processes
3. SQL-based business analytics

The project simulates a company that is preparing or executing an SAP S/4HANA procurement-related implementation. Instead of building a real SAP system, this project creates a realistic analytical environment around procurement, purchasing, suppliers, materials, purchase orders, goods receipts, invoices, and project KPIs.

The goal is to show both technical data analytics ability and business understanding of ERP/SAP projects.

## 2. Why This Project Exists

The project is designed to demonstrate that I can work at the intersection of:

* Data analysis
* SQL
* ERP/SAP business processes
* Procurement analytics
* IT project management
* SAP Activate methodology
* Business requirements and KPI thinking

This is not just a random SQL project. It should look like a realistic junior data analyst / business analyst / SAP-oriented portfolio project.

The final output should help explain how procurement data can be analyzed during or after an SAP S/4HANA implementation project.

## 3. Business Scenario

A fictional mid-sized company is implementing or improving its ERP procurement processes using SAP Activate.

The company wants to understand:

* Supplier performance
* Purchase order processing efficiency
* Delivery reliability
* Invoice and goods receipt matching issues
* Procurement spend distribution
* Material category performance
* Process bottlenecks
* Data quality issues
* Project readiness and KPI monitoring

The analytics layer will support project stakeholders such as:

* Procurement managers
* SAP consultants
* Business analysts
* Project managers
* Key users
* Finance and controlling teams

## 4. SAP Activate Framing

The project should be framed around the SAP Activate methodology.

SAP Activate phases to consider:

1. Discover
2. Prepare
3. Explore
4. Realize
5. Deploy
6. Run

The project does not need to fully implement all phases technically. However, the documentation and project storytelling should connect the analytics work to these phases.

Example interpretation:

* Discover: Identify business problem and high-level procurement pain points.
* Prepare: Define project scope, stakeholders, KPIs, and data sources.
* Explore: Analyze fit-gap, process requirements, and reporting needs.
* Realize: Build database, SQL queries, KPIs, and dashboards.
* Deploy: Prepare final reporting outputs and documentation.
* Run: Monitor procurement KPIs and continuous improvement opportunities.

## 5. Main Project Objective

Build a procurement analytics database and reporting layer that answers business questions through SQL and structured analysis.

The project should include:

* A clean database schema
* Realistic synthetic ERP-style procurement data
* SQL analysis queries
* Business KPI definitions
* SAP Activate-inspired documentation
* Optional dashboard layer
* Final README and portfolio explanation

## 6. Technical Scope

Preferred technology stack:

* SQL
* PostgreSQL or SQLite
* Python for data generation and preprocessing
* pandas for synthetic dataset preparation
* Power BI or Tableau optionally for dashboarding
* Markdown documentation
* GitHub for portfolio presentation

The project should remain realistic but manageable for one student.

## 7. Planned Data Model

Possible tables:

* vendors
* materials
* material_groups
* purchase_requisitions
* purchase_orders
* purchase_order_items
* goods_receipts
* invoices
* payments
* plants
* purchasing_groups
* users or buyers
* sap_activate_project_tasks
* change_requests
* data_quality_issues

The data model should support procurement analytics and project management analytics together.

## 8. Possible KPIs

Procurement KPIs:

* Total procurement spend
* Spend by vendor
* Spend by material group
* Purchase order cycle time
* Purchase requisition to purchase order conversion time
* On-time delivery rate
* Late delivery rate
* Goods receipt vs invoice mismatch rate
* Average invoice processing time
* Top vendors by volume and spend
* Maverick buying indicators
* Open purchase orders
* Blocked invoices
* Supplier reliability score

SAP Activate / project KPIs:

* Project task completion rate
* Open issues by phase
* Change request count by phase
* Data migration readiness
* Test case pass rate
* Defect rate by process area
* Go-live readiness score

## 9. Business Questions

The project should answer questions like:

* Which vendors create the highest spend?
* Which suppliers are frequently late?
* Which material groups have the highest procurement volume?
* Where do invoice mismatches occur most often?
* Which purchasing groups process orders most efficiently?
* Are there bottlenecks between requisition, order, goods receipt, and invoice?
* Which SAP Activate phase has the most project issues?
* What risks should be monitored before go-live?
* What procurement KPIs should be monitored during the Run phase?

## 10. Development Principles

When working on this repository:

* Keep the project realistic and business-oriented.
* Prefer simple but clean architecture over unnecessary complexity.
* Document every important decision.
* Use clear folder structure.
* Do not over-engineer.
* SQL queries should be readable and explained.
* Synthetic data should look realistic enough for portfolio use.
* Every technical output should connect to a business question.
* The project should be understandable to recruiters, SAP consultants, data analysts, and business analysts.

## 11. Expected Folder Structure

Possible structure:

```text
sap-activate-erp-procurement-analytics/
│
├── data/
│   ├── raw/
│   ├── processed/
│
├── database/
│   ├── schema.sql
│   ├── seed_data.sql
│
├── notebooks/
│   ├── data_generation.ipynb
│
├── scripts/
│   ├── generate_data.py
│
├── sql/
│   ├── 01_procurement_spend_analysis.sql
│   ├── 02_supplier_performance.sql
│   ├── 03_cycle_time_analysis.sql
│   ├── 04_invoice_matching_analysis.sql
│   ├── 05_project_kpi_analysis.sql
│
├── docs/
│   ├── business_case.md
│   ├── sap_activate_mapping.md
│   ├── kpi_catalog.md
│
├── dashboard/
│
├── PROJECT_CONTEXT.md
├── README.md
└── requirements.txt
```

## 12. First Roadmap

### Step 1: Project Foundation

* Create PROJECT_CONTEXT.md
* Create README.md draft
* Define business case
* Define folder structure

### Step 2: Data Model

* Design procurement ERD
* Create SQL schema
* Define primary and foreign keys
* Define realistic ERP-style fields

### Step 3: Synthetic Data

* Generate realistic vendor, material, PO, GR, invoice, and project task data
* Add controlled problems such as late deliveries, invoice mismatches, and open change requests

### Step 4: SQL Analytics

* Write SQL queries for procurement KPIs
* Write SQL queries for SAP Activate project KPIs
* Explain business interpretation of each query

### Step 5: Documentation

* Create business case document
* Create SAP Activate mapping
* Create KPI catalog
* Create final README

### Step 6: Dashboard Optional

* Build Power BI or Tableau dashboard if time allows
* Include screenshots in README

## 13. Current Status

The project is at the initial setup stage.

The immediate next task is to create this PROJECT_CONTEXT.md file and then build the first project structure.
