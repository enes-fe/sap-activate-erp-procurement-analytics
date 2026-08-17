"""Export deterministic Seed-42 datasets for the Phase 8A Power BI model."""

from __future__ import annotations

import csv
import hashlib
import io
import os
import sqlite3
import sys
import tempfile
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = REPOSITORY_ROOT / "database" / "marmara_components.db"
OUTPUT_DIRECTORY = REPOSITORY_ROOT / "dashboard" / "data"

REPORTING_DATE = "2026-03-31"
PERIOD_START = "2026-01-01"
PERIOD_END = REPORTING_DATE


class ExportValidationError(RuntimeError):
    """Raised when a dashboard dataset fails its export contract."""


@dataclass(frozen=True)
class DatasetSpec:
    filename: str
    columns: tuple[str, ...]
    grain_columns: tuple[str, ...]
    expected_row_count: int
    query: str


@dataclass(frozen=True)
class DatasetResult:
    columns: tuple[str, ...]
    rows: tuple[dict[str, Any], ...]


PROCUREMENT_COLUMNS = (
    "reporting_date",
    "po_id",
    "po_number",
    "po_item_id",
    "po_item_number",
    "po_created_date",
    "po_lifecycle_status",
    "po_item_lifecycle_status",
    "document_currency",
    "vendor_id",
    "vendor_name",
    "preferred_vendor_flag",
    "plant_id",
    "plant_name",
    "purchasing_group_id",
    "purchasing_group_name",
    "material_id",
    "material_name",
    "material_group_id",
    "material_group_name",
    "spend_category",
    "base_unit_of_measure",
    "pr_item_id",
    "direct_po_flag",
    "ordered_quantity",
    "unit_price",
    "net_value",
    "planned_delivery_date",
    "total_accepted_quantity",
    "open_quantity",
    "fulfillment_status",
    "fulfillment_date",
    "delivery_performance_status",
    "otif_eligible_flag",
    "otif_flag",
    "remaining_commitment_value",
    "backlog_due_status",
    "backlog_age_days",
)

INVOICE_MATCHING_COLUMNS = (
    "invoice_id",
    "invoice_number",
    "invoice_item_id",
    "invoice_item_number",
    "invoice_date",
    "invoice_received_date",
    "posting_date",
    "invoice_currency",
    "po_currency",
    "invoice_status",
    "blocked_flag",
    "block_reason",
    "vendor_id",
    "vendor_name",
    "po_id",
    "po_number",
    "po_item_id",
    "po_item_number",
    "material_id",
    "material_name",
    "ordered_quantity",
    "eligible_posted_accepted_quantity",
    "invoiced_quantity",
    "invoiced_amount",
    "po_unit_price",
    "invoiced_unit_price",
    "quantity_variance",
    "price_variance",
    "monetary_price_variance_impact",
    "matching_status",
    "exception_flag",
)

PAYMENT_PROGRESS_COLUMNS = (
    "invoice_id",
    "invoice_number",
    "invoice_date",
    "invoice_received_date",
    "posting_date",
    "vendor_id",
    "vendor_name",
    "invoice_currency",
    "invoice_total_amount",
    "invoice_status",
    "blocked_flag",
    "block_reason",
    "invoice_matching_status",
    "eligible_for_payment_flag",
    "successful_paid_amount",
    "outstanding_amount",
    "payment_progress_status",
    "fully_paid_flag",
    "successful_payment_count",
    "latest_successful_payment_date",
    "valid_payment_kpi_flag",
)

PROJECT_READINESS_COLUMNS = (
    "pre_go_live_task_count",
    "completed_pre_go_live_task_count",
    "pre_go_live_task_completion_rate_pct",
    "critical_pre_go_live_task_count",
    "incomplete_critical_pre_go_live_task_count",
    "blocking_critical_pre_go_live_task_count",
    "total_change_request_count",
    "open_change_request_count",
    "high_critical_open_change_request_count",
    "critical_open_change_request_count",
    "total_data_quality_issue_count",
    "non_cancelled_data_quality_issue_count",
    "cancelled_data_quality_issue_count",
    "unresolved_data_quality_issue_count",
    "unresolved_high_critical_data_quality_issue_count",
    "unresolved_critical_data_quality_issue_count",
    "resolved_data_quality_issue_count",
    "accepted_risk_data_quality_issue_count",
    "high_critical_accepted_risk_data_quality_issue_count",
    "data_quality_resolution_rate_pct",
    "data_quality_disposition_rate_pct",
    "go_live_readiness_classification",
)

PROJECT_PHASE_COLUMNS = (
    "phase_sequence",
    "activate_phase",
    "task_count",
    "completed_task_count",
    "average_completion_pct",
    "incomplete_critical_task_count",
    "total_request_count",
    "open_request_count",
    "high_critical_open_request_count",
    "unresolved_dq_issue_count",
    "unresolved_high_critical_dq_issue_count",
)

PROJECT_ACTION_COLUMNS = (
    "action_source",
    "action_id",
    "activate_phase",
    "priority_or_severity",
    "action_status",
    "action_description",
    "hard_blocker_flag",
)


DATASET_SPECS = (
    DatasetSpec(
        filename="procurement_items.csv",
        columns=PROCUREMENT_COLUMNS,
        grain_columns=("po_item_id",),
        expected_row_count=14,
        query="""
            WITH parameters AS (
                SELECT
                    :reporting_date AS reporting_date,
                    :period_start AS period_start,
                    :period_end AS period_end
            )
            SELECT
                parameter.reporting_date,
                po.po_id,
                po.po_number,
                item.po_item_id,
                item.po_item_number,
                po.po_created_date,
                po.po_lifecycle_status,
                item.po_item_lifecycle_status,
                po.document_currency,
                vendor.vendor_id,
                vendor.vendor_name,
                vendor.preferred_vendor_flag,
                plant.plant_id,
                plant.plant_name,
                purchasing_group.purchasing_group_id,
                purchasing_group.purchasing_group_name,
                material.material_id,
                material.material_name,
                material_group.material_group_id,
                material_group.material_group_name,
                material_group.spend_category,
                material.base_unit_of_measure,
                item.pr_item_id,
                CASE WHEN item.pr_item_id IS NULL THEN 1 ELSE 0 END
                    AS direct_po_flag,
                item.ordered_quantity,
                item.unit_price,
                item.net_value,
                item.planned_delivery_date,
                delivery.total_accepted_quantity,
                delivery.open_quantity,
                delivery.fulfillment_status,
                delivery.fulfillment_date,
                delivery.delivery_performance_status,
                CASE
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND item.planned_delivery_date <= parameter.reporting_date
                    THEN 1
                    ELSE 0
                END AS otif_eligible_flag,
                CASE
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND item.planned_delivery_date <= parameter.reporting_date
                        AND delivery.delivery_performance_status = 'on time in full'
                    THEN 1
                    ELSE 0
                END AS otif_flag,
                CASE
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND delivery.fulfillment_status IN ('open', 'partial')
                    THEN ROUND(delivery.open_quantity * item.unit_price, 2)
                    ELSE 0
                END AS remaining_commitment_value,
                CASE
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND delivery.fulfillment_status IN ('open', 'partial')
                        AND item.planned_delivery_date < parameter.reporting_date
                    THEN 'overdue'
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND delivery.fulfillment_status IN ('open', 'partial')
                        AND item.planned_delivery_date = parameter.reporting_date
                    THEN 'due today'
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND delivery.fulfillment_status IN ('open', 'partial')
                    THEN 'not yet due'
                    ELSE NULL
                END AS backlog_due_status,
                CASE
                    WHEN po.po_lifecycle_status = 'active'
                        AND item.po_item_lifecycle_status = 'active'
                        AND delivery.fulfillment_status IN ('open', 'partial')
                    THEN CAST(
                        julianday(parameter.reporting_date)
                        - julianday(item.planned_delivery_date)
                        AS INTEGER
                    )
                    ELSE NULL
                END AS backlog_age_days
            FROM purchase_orders AS po
            JOIN purchase_order_items AS item
                ON item.po_id = po.po_id
            JOIN vw_po_item_delivery_performance AS delivery
                ON delivery.po_item_id = item.po_item_id
            JOIN vendors AS vendor
                ON vendor.vendor_id = po.vendor_id
            JOIN plants AS plant
                ON plant.plant_id = po.plant_id
            JOIN purchasing_groups AS purchasing_group
                ON purchasing_group.purchasing_group_id = po.purchasing_group_id
            JOIN materials AS material
                ON material.material_id = item.material_id
            JOIN material_groups AS material_group
                ON material_group.material_group_id = material.material_group_id
            CROSS JOIN parameters AS parameter
            WHERE po.po_created_date BETWEEN parameter.period_start
                    AND parameter.period_end
                AND po.po_lifecycle_status <> 'cancelled'
                AND item.po_item_lifecycle_status <> 'cancelled'
            ORDER BY
                po.document_currency,
                po.po_id,
                item.po_item_number,
                item.po_item_id
        """,
    ),
    DatasetSpec(
        filename="invoice_matching.csv",
        columns=INVOICE_MATCHING_COLUMNS,
        grain_columns=("invoice_item_id",),
        expected_row_count=5,
        query="""
            SELECT
                match.invoice_id,
                match.invoice_number,
                match.invoice_item_id,
                match.invoice_item_number,
                match.invoice_date,
                match.invoice_received_date,
                match.posting_date,
                match.invoice_currency,
                match.po_currency,
                match.invoice_status,
                match.blocked_flag,
                match.block_reason,
                vendor.vendor_id,
                vendor.vendor_name,
                match.po_id,
                match.po_number,
                match.po_item_id,
                match.po_item_number,
                material.material_id,
                material.material_name,
                match.ordered_quantity,
                match.eligible_posted_accepted_quantity,
                match.invoiced_quantity,
                match.invoiced_amount,
                match.po_unit_price,
                match.invoiced_unit_price,
                match.quantity_variance,
                match.price_variance,
                match.monetary_price_variance_impact,
                match.matching_status,
                CASE WHEN match.matching_status <> 'matched' THEN 1 ELSE 0 END
                    AS exception_flag
            FROM vw_invoice_item_three_way_match AS match
            JOIN vendors AS vendor
                ON vendor.vendor_id = match.vendor_id
            JOIN purchase_order_items AS item
                ON item.po_item_id = match.po_item_id
            JOIN materials AS material
                ON material.material_id = item.material_id
            ORDER BY
                match.invoice_id,
                match.invoice_item_number,
                match.invoice_item_id
        """,
    ),
    DatasetSpec(
        filename="payment_progress.csv",
        columns=PAYMENT_PROGRESS_COLUMNS,
        grain_columns=("invoice_id",),
        expected_row_count=4,
        query="""
            SELECT
                payment.invoice_id,
                invoice.invoice_number,
                invoice.invoice_date,
                invoice.invoice_received_date,
                invoice.posting_date,
                vendor.vendor_id,
                vendor.vendor_name,
                payment.invoice_currency,
                payment.invoice_total_amount,
                payment.invoice_status,
                payment.blocked_flag,
                invoice.block_reason,
                payment.invoice_matching_status,
                payment.eligible_for_payment_flag,
                payment.successful_paid_amount,
                payment.outstanding_amount,
                payment.payment_progress_status,
                CASE
                    WHEN payment.payment_progress_status = 'paid' THEN 1
                    ELSE 0
                END AS fully_paid_flag,
                payment.successful_payment_count,
                payment.latest_successful_payment_date,
                1 AS valid_payment_kpi_flag
            FROM vw_invoice_payment_progress AS payment
            JOIN invoices AS invoice
                ON invoice.invoice_id = payment.invoice_id
            JOIN vendors AS vendor
                ON vendor.vendor_id = payment.vendor_id
            WHERE payment.invoice_status IN ('posted', 'approved')
                AND payment.invoice_matching_status NOT IN ('excluded', 'invalid')
            ORDER BY payment.invoice_id
        """,
    ),
    DatasetSpec(
        filename="project_readiness.csv",
        columns=PROJECT_READINESS_COLUMNS,
        grain_columns=(),
        expected_row_count=1,
        query="""
            SELECT
                pre_go_live_task_count,
                completed_pre_go_live_task_count,
                pre_go_live_task_completion_rate_pct,
                critical_pre_go_live_task_count,
                incomplete_critical_pre_go_live_task_count,
                blocking_critical_pre_go_live_task_count,
                total_change_request_count,
                open_change_request_count,
                high_critical_open_change_request_count,
                critical_open_change_request_count,
                total_data_quality_issue_count,
                non_cancelled_data_quality_issue_count,
                cancelled_data_quality_issue_count,
                unresolved_data_quality_issue_count,
                unresolved_high_critical_data_quality_issue_count,
                unresolved_critical_data_quality_issue_count,
                resolved_data_quality_issue_count,
                accepted_risk_data_quality_issue_count,
                high_critical_accepted_risk_data_quality_issue_count,
                data_quality_resolution_rate_pct,
                data_quality_disposition_rate_pct,
                go_live_readiness_classification
            FROM vw_project_readiness_summary
        """,
    ),
    DatasetSpec(
        filename="project_phases.csv",
        columns=PROJECT_PHASE_COLUMNS,
        grain_columns=("activate_phase",),
        expected_row_count=6,
        query="""
            WITH phase_order(activate_phase, phase_sequence) AS (
                VALUES
                    ('discover', 1),
                    ('prepare', 2),
                    ('explore', 3),
                    ('realize', 4),
                    ('deploy', 5),
                    ('run', 6)
            ),
            task_metrics AS (
                SELECT
                    activate_phase,
                    COUNT(*) AS task_count,
                    SUM(
                        CASE
                            WHEN task_status = 'completed'
                                AND completion_percent = 100
                            THEN 1
                            ELSE 0
                        END
                    ) AS completed_task_count,
                    ROUND(AVG(completion_percent), 1)
                        AS average_completion_pct,
                    SUM(
                        CASE
                            WHEN critical_flag = 1
                                AND (
                                    task_status <> 'completed'
                                    OR completion_percent < 100
                                )
                            THEN 1
                            ELSE 0
                        END
                    ) AS incomplete_critical_task_count
                FROM sap_activate_project_tasks
                GROUP BY activate_phase
            ),
            dq_metrics AS (
                SELECT
                    task.activate_phase,
                    SUM(
                        CASE
                            WHEN issue.issue_status IN ('open', 'in progress')
                            THEN 1
                            ELSE 0
                        END
                    ) AS unresolved_dq_issue_count,
                    SUM(
                        CASE
                            WHEN issue.issue_status IN ('open', 'in progress')
                                AND issue.severity IN ('high', 'critical')
                            THEN 1
                            ELSE 0
                        END
                    ) AS unresolved_high_critical_dq_issue_count
                FROM data_quality_issues AS issue
                LEFT JOIN sap_activate_project_tasks AS task
                    ON task.task_id = issue.related_task_id
                GROUP BY task.activate_phase
            )
            SELECT
                phase.phase_sequence,
                phase.activate_phase,
                COALESCE(task.task_count, 0) AS task_count,
                COALESCE(task.completed_task_count, 0) AS completed_task_count,
                task.average_completion_pct,
                COALESCE(task.incomplete_critical_task_count, 0)
                    AS incomplete_critical_task_count,
                change_request.total_request_count,
                change_request.open_request_count,
                change_request.high_critical_open_request_count,
                COALESCE(dq.unresolved_dq_issue_count, 0)
                    AS unresolved_dq_issue_count,
                COALESCE(dq.unresolved_high_critical_dq_issue_count, 0)
                    AS unresolved_high_critical_dq_issue_count
            FROM phase_order AS phase
            LEFT JOIN task_metrics AS task
                ON task.activate_phase = phase.activate_phase
            JOIN vw_change_request_phase_summary AS change_request
                ON change_request.activate_phase = phase.activate_phase
            LEFT JOIN dq_metrics AS dq
                ON dq.activate_phase = phase.activate_phase
            ORDER BY phase.phase_sequence
        """,
    ),
    DatasetSpec(
        filename="project_actions.csv",
        columns=PROJECT_ACTION_COLUMNS,
        grain_columns=("action_source", "action_id"),
        expected_row_count=9,
        query="""
            WITH management_actions AS (
                SELECT
                    'critical task' AS action_source,
                    task.task_id AS action_id,
                    task.activate_phase,
                    'critical' AS priority_or_severity,
                    task.task_status AS action_status,
                    task.task_name AS action_description,
                    CASE
                        WHEN task.task_status IN ('blocked', 'delayed', 'cancelled')
                        THEN 1
                        ELSE 0
                    END AS hard_blocker_flag
                FROM sap_activate_project_tasks AS task
                WHERE task.activate_phase <> 'run'
                    AND task.critical_flag = 1
                    AND (
                        task.task_status <> 'completed'
                        OR task.completion_percent < 100
                    )

                UNION ALL

                SELECT
                    'open change request' AS action_source,
                    request.change_request_id AS action_id,
                    request.activate_phase,
                    request.priority AS priority_or_severity,
                    request.status AS action_status,
                    request.change_title AS action_description,
                    CASE WHEN request.priority = 'critical' THEN 1 ELSE 0 END
                        AS hard_blocker_flag
                FROM change_requests AS request
                WHERE request.status IN ('submitted', 'under review', 'approved')

                UNION ALL

                SELECT
                    'data quality risk' AS action_source,
                    issue.data_quality_issue_id AS action_id,
                    COALESCE(task.activate_phase, 'unassigned') AS activate_phase,
                    issue.severity AS priority_or_severity,
                    issue.issue_status AS action_status,
                    issue.issue_description AS action_description,
                    CASE
                        WHEN issue.severity = 'critical'
                            AND issue.issue_status IN ('open', 'in progress')
                        THEN 1
                        ELSE 0
                    END AS hard_blocker_flag
                FROM data_quality_issues AS issue
                LEFT JOIN sap_activate_project_tasks AS task
                    ON task.task_id = issue.related_task_id
                WHERE issue.issue_status IN (
                        'open',
                        'in progress',
                        'accepted risk'
                    )
                    AND issue.severity IN ('high', 'critical')
            )
            SELECT
                action_source,
                action_id,
                activate_phase,
                priority_or_severity,
                action_status,
                action_description,
                hard_blocker_flag
            FROM management_actions
            ORDER BY
                CASE priority_or_severity
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END,
                action_source,
                action_id
        """,
    ),
)


MONEY_COLUMNS = {
    "unit_price",
    "net_value",
    "remaining_commitment_value",
    "invoiced_amount",
    "po_unit_price",
    "invoiced_unit_price",
    "price_variance",
    "monetary_price_variance_impact",
    "invoice_total_amount",
    "successful_paid_amount",
    "outstanding_amount",
}

PERCENT_COLUMNS = {
    "pre_go_live_task_completion_rate_pct",
    "data_quality_resolution_rate_pct",
    "data_quality_disposition_rate_pct",
    "average_completion_pct",
}


def fail(message: str) -> None:
    raise ExportValidationError(message)


def decimal_value(value: Any) -> Decimal:
    if value is None:
        fail("unexpected null numeric value")
    return Decimal(str(value))


def grouped_decimal_sum(
    rows: tuple[dict[str, Any], ...],
    group_column: str,
    value_column: str,
) -> dict[str, Decimal]:
    totals: dict[str, Decimal] = {}
    for row in rows:
        group = str(row[group_column])
        totals[group] = totals.get(group, Decimal("0")) + decimal_value(
            row[value_column]
        )
    return totals


def expect_equal(label: str, actual: Any, expected: Any) -> None:
    if actual != expected:
        fail(f"{label}: expected {expected!r}, got {actual!r}")


def execute_dataset(
    connection: sqlite3.Connection,
    spec: DatasetSpec,
) -> DatasetResult:
    cursor = connection.execute(
        spec.query,
        {
            "reporting_date": REPORTING_DATE,
            "period_start": PERIOD_START,
            "period_end": PERIOD_END,
        },
    )
    actual_columns = tuple(column[0] for column in cursor.description or ())
    expect_equal(f"{spec.filename} columns", actual_columns, spec.columns)

    rows = tuple(dict(row) for row in cursor.fetchall())
    if not rows:
        fail(f"{spec.filename}: dataset is empty")
    expect_equal(
        f"{spec.filename} row count",
        len(rows),
        spec.expected_row_count,
    )

    if spec.grain_columns:
        seen: set[tuple[Any, ...]] = set()
        for row_number, row in enumerate(rows, start=1):
            grain = tuple(row[column] for column in spec.grain_columns)
            if any(value is None or value == "" for value in grain):
                fail(
                    f"{spec.filename} row {row_number}: null or blank grain {grain}"
                )
            if grain in seen:
                fail(f"{spec.filename}: duplicate grain {grain}")
            seen.add(grain)

    return DatasetResult(columns=actual_columns, rows=rows)


def validate_currency_rows(
    filename: str,
    result: DatasetResult,
    currency_column: str,
    monetary_columns: tuple[str, ...],
) -> None:
    for row_number, row in enumerate(result.rows, start=1):
        currency = row[currency_column]
        if currency not in {"TRY", "EUR"}:
            fail(
                f"{filename} row {row_number}: invalid or missing currency "
                f"{currency!r}"
            )
        for monetary_column in monetary_columns:
            if row[monetary_column] is None:
                fail(
                    f"{filename} row {row_number}: {monetary_column} is null "
                    f"without a valid currency amount"
                )


def validate_headlines(results: dict[str, DatasetResult]) -> None:
    procurement = results["procurement_items.csv"].rows
    validate_currency_rows(
        "procurement_items.csv",
        results["procurement_items.csv"],
        "document_currency",
        ("unit_price", "net_value", "remaining_commitment_value"),
    )
    expect_equal(
        "procurement commitment by currency",
        grouped_decimal_sum(procurement, "document_currency", "net_value"),
        {"EUR": Decimal("4269.30"), "TRY": Decimal("7216.64")},
    )
    expect_equal(
        "OTIF-eligible PO item count",
        sum(int(row["otif_eligible_flag"]) for row in procurement),
        12,
    )
    expect_equal(
        "OTIF PO item count",
        sum(int(row["otif_flag"]) for row in procurement),
        3,
    )
    backlog = tuple(
        row
        for row in procurement
        if row["fulfillment_status"] in {"open", "partial"}
        and row["po_lifecycle_status"] == "active"
        and row["po_item_lifecycle_status"] == "active"
    )
    expect_equal("open/partial backlog item count", len(backlog), 5)
    expect_equal(
        "remaining commitment by currency",
        grouped_decimal_sum(
            backlog,
            "document_currency",
            "remaining_commitment_value",
        ),
        {"EUR": Decimal("2245.80"), "TRY": Decimal("1118.82")},
    )

    matching = results["invoice_matching.csv"].rows
    validate_currency_rows(
        "invoice_matching.csv",
        results["invoice_matching.csv"],
        "invoice_currency",
        (
            "invoiced_amount",
            "po_unit_price",
            "invoiced_unit_price",
            "price_variance",
            "monetary_price_variance_impact",
        ),
    )
    exception_count = sum(int(row["exception_flag"]) for row in matching)
    expect_equal("matching exception item count", exception_count, 3)
    exception_rate = (
        Decimal(exception_count) * Decimal("100") / Decimal(len(matching))
    ).quantize(Decimal("0.1"))
    expect_equal("matching exception rate", exception_rate, Decimal("60.0"))

    payment = results["payment_progress.csv"].rows
    validate_currency_rows(
        "payment_progress.csv",
        results["payment_progress.csv"],
        "invoice_currency",
        (
            "invoice_total_amount",
            "successful_paid_amount",
            "outstanding_amount",
        ),
    )
    valid_invoice_count = sum(
        int(row["valid_payment_kpi_flag"]) for row in payment
    )
    fully_paid_count = sum(int(row["fully_paid_flag"]) for row in payment)
    expect_equal("valid payment KPI invoice count", valid_invoice_count, 4)
    expect_equal("fully paid invoice count", fully_paid_count, 1)
    completion_rate = (
        Decimal(fully_paid_count)
        * Decimal("100")
        / Decimal(valid_invoice_count)
    ).quantize(Decimal("0.1"))
    expect_equal("invoice payment completion rate", completion_rate, Decimal("25.0"))
    expect_equal(
        "outstanding amount by currency",
        grouped_decimal_sum(payment, "invoice_currency", "outstanding_amount"),
        {"EUR": Decimal("597.00"), "TRY": Decimal("1279.00")},
    )

    readiness_rows = results["project_readiness.csv"].rows
    expect_equal("project readiness row count", len(readiness_rows), 1)
    readiness = readiness_rows[0]
    expect_equal(
        "go-live readiness classification",
        readiness["go_live_readiness_classification"],
        "not ready",
    )

    phases = results["project_phases.csv"].rows
    expect_equal(
        "SAP Activate phase sequence",
        tuple(
            (row["phase_sequence"], row["activate_phase"])
            for row in phases
        ),
        (
            (1, "discover"),
            (2, "prepare"),
            (3, "explore"),
            (4, "realize"),
            (5, "deploy"),
            (6, "run"),
        ),
    )

    actions = results["project_actions.csv"].rows
    hard_blocker_count = sum(int(row["hard_blocker_flag"]) for row in actions)
    expect_equal("management action count", len(actions), 9)
    expect_equal("management hard blocker count", hard_blocker_count, 2)
    gate_hard_blocker_count = (
        int(readiness["blocking_critical_pre_go_live_task_count"])
        + int(readiness["critical_open_change_request_count"])
        + int(readiness["unresolved_critical_data_quality_issue_count"])
    )
    expect_equal(
        "hard blocker presentation mapping reconciliation",
        hard_blocker_count,
        gate_hard_blocker_count,
    )


def format_cell(column: str, value: Any) -> str:
    if value is None:
        return ""
    if column in MONEY_COLUMNS:
        return f"{float(value):.2f}"
    if column in PERCENT_COLUMNS:
        return f"{float(value):.1f}"
    if isinstance(value, float):
        return format(value, ".15g")
    return str(value)


def render_csv(result: DatasetResult) -> bytes:
    stream = io.StringIO()
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(result.columns)
    for row in result.rows:
        writer.writerow(
            format_cell(column, row[column]) for column in result.columns
        )
    return stream.getvalue().encode("utf-8")


def validate_export_file_set() -> None:
    expected_names = {spec.filename for spec in DATASET_SPECS}
    actual_names = {path.name for path in OUTPUT_DIRECTORY.glob("*.csv")}
    expect_equal("dashboard CSV file set", actual_names, expected_names)
    for filename in sorted(expected_names):
        path = OUTPUT_DIRECTORY / filename
        if path.stat().st_size == 0:
            fail(f"{filename}: exported file is empty")


def write_exports_atomically(results: dict[str, DatasetResult]) -> dict[str, str]:
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    expected_names = {spec.filename for spec in DATASET_SPECS}
    unexpected_names = {
        path.name for path in OUTPUT_DIRECTORY.glob("*.csv")
    } - expected_names
    if unexpected_names:
        fail(
            "unexpected CSV files already exist in dashboard/data: "
            + ", ".join(sorted(unexpected_names))
        )

    rendered = {
        filename: render_csv(result) for filename, result in results.items()
    }
    hashes = {
        filename: hashlib.sha256(content).hexdigest()
        for filename, content in rendered.items()
    }

    with tempfile.TemporaryDirectory(
        prefix=".dashboard-export-",
        dir=OUTPUT_DIRECTORY.parent,
    ) as temporary_directory:
        staging_directory = Path(temporary_directory)
        for filename, content in rendered.items():
            staging_path = staging_directory / filename
            staging_path.write_bytes(content)
            if staging_path.stat().st_size == 0:
                fail(f"{filename}: staged export is empty")

        for filename in sorted(rendered):
            os.replace(
                staging_directory / filename,
                OUTPUT_DIRECTORY / filename,
            )

    validate_export_file_set()
    return hashes


def open_database_read_only() -> sqlite3.Connection:
    if not DATABASE_PATH.is_file():
        fail(f"database not found: {DATABASE_PATH}")
    database_uri = f"{DATABASE_PATH.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    query_only = connection.execute("PRAGMA query_only").fetchone()[0]
    expect_equal("SQLite query_only pragma", query_only, 1)
    return connection


def main() -> None:
    connection: sqlite3.Connection | None = None
    try:
        connection = open_database_read_only()
        results = {
            spec.filename: execute_dataset(connection, spec)
            for spec in DATASET_SPECS
        }
        validate_headlines(results)
        hashes = write_exports_atomically(results)
    except (ExportValidationError, OSError, sqlite3.Error) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error
    finally:
        if connection is not None:
            connection.close()

    for spec in DATASET_SPECS:
        print(
            f"PASS {spec.filename}: "
            f"{len(results[spec.filename].rows)} rows, "
            f"sha256={hashes[spec.filename]}"
        )
    print("PASS Seed-42 dashboard headline reconciliation")
    print("PASS exactly six non-empty dashboard CSV files exported")


if __name__ == "__main__":
    main()
