# SAP Activate Mapping

## Purpose

This document explains how SAP Activate methodology frames the SAP Activate ERP Procurement Analytics project. The repository is a portfolio-oriented analytics simulation, not an SAP Activate implementation tool and not a live SAP production deployment.

The goal is to show how procurement analytics requirements, data modeling, synthetic data, KPI logic, and documentation can be organized around a realistic SAP S/4HANA project story.

## Phase Mapping

| SAP Activate Phase | Project Activity | Analytics Contribution | Current Status |
| --- | --- | --- | --- |
| Discover | Identify the procurement business problem, pain points, and improvement opportunities. | Translate business pain points into measurable questions and candidate KPIs. | Business case complete. |
| Prepare | Define scope, stakeholders, planned sources, and KPI priorities. | Establish reporting scope before implementation. | Scope and KPI catalog established. |
| Explore | Review procurement process gaps and reporting requirements. | Connect reporting needs to process steps such as requisition, PO, goods receipt, invoice, and payment. | Process, data model, and KPI requirements documented. |
| Realize | Build the analytical layer iteratively. | Convert agreed requirements into schema, deterministic data, views, standalone queries, and validation logic. | Deterministic data and analytical views are implemented through Phase 6; the standalone SQL package is implemented in Phase 7. |
| Deploy | Prepare final reporting outputs for review and readiness storytelling. | Use the implemented readiness classification and validated SQL outputs for portfolio packaging. | Readiness analytics and SQL packaging are implemented; optional dashboard and presentation work remain. |
| Run | Monitor procurement performance and continuous improvement opportunities. | Track recurring procurement KPIs, supplier performance, and exception diagnostics. | Conceptual / future analytics use. |

## Discover

The Discover phase frames the reason for the project. In this simulation, Marmara Components has limited visibility into procurement performance and wants better control during an SAP S/4HANA procurement improvement initiative.

Completed artifacts:

- `docs/business_case.md`
- Initial stakeholder and pain-point framing.
- Practical procurement analytics themes, including supplier reliability, spend visibility, open orders, invoice matching, and readiness risk.

## Prepare

The Prepare phase turns the idea into a controlled analytics scope. For this repository, that means defining stakeholders, planned source objects, KPI priorities, and project documentation before expanding implementation.

Completed artifacts:

- `docs/kpi_catalog.md`
- Current project scope and technical context.
- Planned source table list, later replaced by the implemented 16-table SQLite model.
- KPI prioritization into core and extended/supporting measures.

## Explore

The Explore phase connects procurement processes to reporting requirements. In a real SAP project, this would happen through fit-gap workshops and design validation. In this portfolio project, it is represented by mapping business questions to source objects, grains, statuses, and KPI definitions.

Completed artifacts:

- `docs/data_model.md`
- Process-to-data model explanation.
- KPI-to-source mapping.
- Documentation of lifecycle, fulfillment, receipt workflow, invoice matching, payment progress, and project-readiness decisions.

## Explore-to-Realize Design Decision

Supplier reliability reporting required an item-level on-time-in-full KPI. That requirement exposed a modeling issue: receipt workflow, quantity facts, PO lifecycle, PO-item lifecycle, and fulfillment progress cannot be represented cleanly by one stored status field.

Before Phase 3 goods receipt data was added, the model was refactored to separate:

- Stored PO lifecycle.
- Stored PO-item lifecycle.
- Receipt workflow status.
- Received, accepted, and rejected quantity facts.
- Derived fulfillment status.
- Future derived invoice progress.

This is a practical example of Explore requirements influencing Realize implementation before extending the dataset.

## Realize

The Realize phase is where the analytical assets become executable. The repository has now implemented:

- Executable SQLite schema.
- Deterministic master data.
- Purchase requisition scenarios.
- Purchase order scenarios.
- PR-to-PO conversion and direct PO scenarios.
- Goods receipt scenarios.
- Lifecycle and fulfillment architecture.
- `vw_po_item_fulfillment`.
- `vw_po_fulfillment`.
- `vw_po_item_delivery_performance`.
- Invoice and invoice-item matching scenarios.
- `vw_invoice_item_three_way_match`.
- `vw_invoice_matching_summary`.
- Payment instructions, attempts, and invoice payment-progress scenarios.
- `vw_invoice_payment_progress`.
- Six deterministic change requests and seven deterministic data-quality issues.
- `vw_change_request_phase_summary`.
- `vw_project_readiness_summary`.
- Phase 1 through Phase 6 validation and deterministic regeneration checks.
- Six standalone Phase 7 SQL analysis files.
- Read-only analytics runner with explicit Seed-42 headline validation.

This represents iterative realization of the analytical layer through project-readiness analytics and a recruiter-readable SQL package. Optional dashboards, final screenshots, and presentation work remain future-oriented.

## Deploy

The Deploy phase remains partly future-oriented for this repository. Phase 6 supplies readiness analytics, and Phase 7 packages the implemented logic as validated standalone SQL outputs. Dashboard and presentation work remain future-oriented.

Implemented Deploy-oriented outputs include:

- Final SQL query package.
- Documentation alignment and deterministic SQL validation.
- Presentation of the implemented readiness reporting and its transparent blocker logic.
- Clear explanation of what is synthetic, what is implemented, and what is planned.

Remaining optional Deploy outputs include:

- Dashboard screenshots if a dashboard is built.
- Final recruiter-facing presentation assets.

This project should not claim a live SAP production deployment.

## Run

The Run phase is also future-oriented. It represents the kind of recurring analytics that procurement and project teams could monitor after implementation.

Future Run use cases include:

- Recurring item-level OTIF monitoring.
- Receipt-event delay diagnostics.
- Supplier performance monitoring.
- Open quantity and open PO follow-up.
- Invoice exception monitoring.
- Continuous improvement tracking based on recurring KPI reviews.

## Project Progress Summary

| SAP Activate Phase | Current Repository Status |
| --- | --- |
| Discover | Business case complete. |
| Prepare | Scope and KPI catalog established. |
| Explore | Process/data model and KPI requirements documented. |
| Realize | Deterministic analytical scope and standalone Phase 7 SQL package are implemented. |
| Deploy | Readiness analytics and SQL output packaging are implemented; optional dashboard and presentation work remain. |
| Run | Conceptual / future analytics use. |

## Practical Interpretation

This repository uses SAP Activate as a practical structure for portfolio storytelling. Each technical artifact should support a business question and fit into a realistic SAP implementation phase, while remaining honest about current implementation boundaries.
