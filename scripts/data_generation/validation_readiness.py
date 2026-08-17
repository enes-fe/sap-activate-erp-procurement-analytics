"""Validate change requests, data quality, and project readiness."""

from __future__ import annotations

import sqlite3

from .expected_results import (
    EXPECTED_CHANGE_REQUEST_DETAILS,
    EXPECTED_CHANGE_REQUEST_PHASE_SUMMARY_ROWS,
    EXPECTED_DATA_QUALITY_ISSUE_DETAILS,
    EXPECTED_PROJECT_READINESS_ROW,
)
from .validation_common import raise_if_rows, validation_savepoint


def change_request_phase_summary_rows(
    connection: sqlite3.Connection,
) -> list[tuple[object, ...]]:
    return connection.execute(
        """
        SELECT activate_phase,
               total_request_count,
               submitted_request_count,
               under_review_request_count,
               approved_request_count,
               implemented_request_count,
               deferred_request_count,
               rejected_request_count,
               cancelled_request_count,
               open_request_count,
               high_critical_open_request_count
        FROM vw_change_request_phase_summary
        ORDER BY CASE activate_phase
            WHEN 'discover' THEN 1
            WHEN 'prepare' THEN 2
            WHEN 'explore' THEN 3
            WHEN 'realize' THEN 4
            WHEN 'deploy' THEN 5
            WHEN 'run' THEN 6
        END
        """
    ).fetchall()


def project_readiness_row(
    connection: sqlite3.Connection,
) -> tuple[object, ...] | None:
    return connection.execute(
        """
        SELECT pre_go_live_task_count,
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
        """
    ).fetchone()


def validate_change_request_rows(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT change_request_id,
               related_task_id,
               activate_phase,
               change_title,
               change_type,
               priority,
               status,
               requested_date,
               decision_date,
               business_impact
        FROM change_requests
        ORDER BY change_request_id
        """
    ).fetchall()
    actual_details = {str(row[0]): tuple(row[1:]) for row in rows}
    if actual_details != EXPECTED_CHANGE_REQUEST_DETAILS:
        raise RuntimeError(
            "Unexpected deterministic change-request rows: "
            f"{actual_details}"
        )


def validate_change_request_task_alignment(
    connection: sqlite3.Connection,
) -> None:
    violations = connection.execute(
        """
        SELECT change_request.change_request_id,
               change_request.related_task_id,
               change_request.activate_phase,
               task.activate_phase,
               change_request.requested_date,
               task.planned_start_date,
               task.planned_finish_date
        FROM change_requests AS change_request
        LEFT JOIN sap_activate_project_tasks AS task
            ON task.task_id = change_request.related_task_id
        WHERE change_request.related_task_id IS NOT NULL
            AND (
                task.task_id IS NULL
                OR change_request.activate_phase <> task.activate_phase
                OR change_request.requested_date < task.planned_start_date
                OR change_request.requested_date > task.planned_finish_date
            )
        """
    ).fetchall()
    raise_if_rows(
        violations,
        "Change request task phase/date alignment violations",
    )


def validate_data_quality_issue_rows(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT data_quality_issue_id,
               issue_description,
               related_task_id,
               affected_entity_type,
               affected_entity_id,
               issue_category,
               severity,
               issue_status,
               detected_date,
               resolved_date,
               migration_relevant_flag,
               readiness_impact_score
        FROM data_quality_issues
        ORDER BY data_quality_issue_id
        """
    ).fetchall()
    actual_details = {str(row[0]): tuple(row[1:]) for row in rows}
    if actual_details != EXPECTED_DATA_QUALITY_ISSUE_DETAILS:
        raise RuntimeError(
            "Unexpected deterministic data-quality issue rows: "
            f"{actual_details}"
        )


def validate_data_quality_task_alignment(
    connection: sqlite3.Connection,
) -> None:
    violations = connection.execute(
        """
        SELECT issue.data_quality_issue_id,
               issue.related_task_id,
               issue.detected_date,
               task.planned_start_date,
               task.planned_finish_date
        FROM data_quality_issues AS issue
        LEFT JOIN sap_activate_project_tasks AS task
            ON task.task_id = issue.related_task_id
        WHERE issue.related_task_id IS NOT NULL
            AND (
                task.task_id IS NULL
                OR issue.detected_date < task.planned_start_date
                OR issue.detected_date > task.planned_finish_date
            )
        """
    ).fetchall()
    raise_if_rows(
        violations,
        "Data-quality issue task date alignment violations",
    )


def validate_data_quality_entity_references(
    connection: sqlite3.Connection,
) -> None:
    entity_sources = {
        "vendor": ("vendors", "vendor_id"),
        "material": ("materials", "material_id"),
        "purchase order": ("purchase_orders", "po_id"),
        "invoice": ("invoices", "invoice_id"),
        "project task": ("sap_activate_project_tasks", "task_id"),
    }
    rows = connection.execute(
        """
        SELECT data_quality_issue_id,
               affected_entity_type,
               affected_entity_id
        FROM data_quality_issues
        WHERE affected_entity_id IS NOT NULL
        """
    ).fetchall()
    violations = []
    for issue_id, entity_type, entity_id in rows:
        table_name, id_column = entity_sources[str(entity_type)]
        exists = connection.execute(
            f"SELECT 1 FROM {table_name} WHERE {id_column} = ?",
            (entity_id,),
        ).fetchone()
        if exists is None:
            violations.append((issue_id, entity_type, entity_id))
    if violations:
        raise RuntimeError(
            "Data-quality affected entity reference violations: "
            f"{violations}"
        )


def validate_phase1_to_phase5_source_facts_unchanged(
    connection: sqlite3.Connection,
) -> None:
    source_facts = {
        "VEN-002": connection.execute(
            "SELECT vendor_status FROM vendors WHERE vendor_id = 'VEN-002'"
        ).fetchone(),
        "VEN-005": connection.execute(
            "SELECT vendor_status FROM vendors WHERE vendor_id = 'VEN-005'"
        ).fetchone(),
        "MAT-004": connection.execute(
            """
            SELECT material_status, standard_price
            FROM materials
            WHERE material_id = 'MAT-004'
            """
        ).fetchone(),
        "MAT-008": connection.execute(
            """
            SELECT material_status, standard_price
            FROM materials
            WHERE material_id = 'MAT-008'
            """
        ).fetchone(),
        "MAT-009": connection.execute(
            """
            SELECT material_status, standard_price
            FROM materials
            WHERE material_id = 'MAT-009'
            """
        ).fetchone(),
        "PO-005": connection.execute(
            """
            SELECT po_lifecycle_status, po_approval_date
            FROM purchase_orders
            WHERE po_id = 'PO-005'
            """
        ).fetchone(),
        "INV-004": connection.execute(
            """
            SELECT invoice_status, blocked_flag
            FROM invoices
            WHERE invoice_id = 'INV-004'
            """
        ).fetchone(),
    }
    expected_source_facts = {
        "VEN-002": ("active",),
        "VEN-005": ("pending review",),
        "MAT-004": ("active", 1.2),
        "MAT-008": ("active", 185.0),
        "MAT-009": ("active", 420.0),
        "PO-005": ("blocked", None),
        "INV-004": ("posted", 1),
    }
    if source_facts != expected_source_facts:
        raise RuntimeError(
            "Phase 6 changed referenced Phase 1-5 source facts: "
            f"{source_facts}"
        )


def validate_change_request_phase_summary(
    connection: sqlite3.Connection,
) -> None:
    rows = change_request_phase_summary_rows(connection)
    if rows != EXPECTED_CHANGE_REQUEST_PHASE_SUMMARY_ROWS:
        raise RuntimeError(
            "Unexpected change-request phase summary rows: "
            f"{rows}"
        )


def validate_project_readiness_summary(
    connection: sqlite3.Connection,
) -> None:
    row = project_readiness_row(connection)
    if row != EXPECTED_PROJECT_READINESS_ROW:
        raise RuntimeError(
            f"Unexpected project readiness summary row: {row}"
        )


def insert_validation_change_request(
    connection: sqlite3.Connection,
    row: tuple[object, ...],
) -> None:
    connection.execute(
        """
        INSERT INTO change_requests (
            change_request_id,
            related_task_id,
            activate_phase,
            change_title,
            change_type,
            priority,
            status,
            requested_date,
            decision_date,
            business_impact
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def insert_validation_data_quality_issue(
    connection: sqlite3.Connection,
    row: tuple[object, ...],
) -> None:
    connection.execute(
        """
        INSERT INTO data_quality_issues (
            data_quality_issue_id,
            issue_description,
            related_task_id,
            affected_entity_type,
            affected_entity_id,
            issue_category,
            severity,
            issue_status,
            detected_date,
            resolved_date,
            migration_relevant_flag,
            readiness_impact_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def expect_change_request_schema_rejection(
    connection: sqlite3.Connection,
    label: str,
    row: tuple[object, ...],
) -> None:
    try:
        insert_validation_change_request(connection, row)
    except sqlite3.IntegrityError:
        return
    raise RuntimeError(
        f"Change-request schema accepted invalid scenario: {label}"
    )


def expect_data_quality_schema_rejection(
    connection: sqlite3.Connection,
    label: str,
    row: tuple[object, ...],
) -> None:
    try:
        insert_validation_data_quality_issue(connection, row)
    except sqlite3.IntegrityError:
        return
    raise RuntimeError(
        f"Data-quality schema accepted invalid scenario: {label}"
    )


def phase6_state_snapshot(
    connection: sqlite3.Connection,
) -> tuple[object, ...]:
    counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM change_requests),
            (SELECT COUNT(*) FROM data_quality_issues)
        """
    ).fetchone()
    return (
        counts,
        tuple(change_request_phase_summary_rows(connection)),
        project_readiness_row(connection),
    )


def validate_phase6_adversarial_cases(
    connection: sqlite3.Connection,
) -> None:
    baseline_snapshot = phase6_state_snapshot(connection)

    with validation_savepoint(connection, "change_request_schema_validation"):
        expect_change_request_schema_rejection(
            connection,
            "decision date precedes requested date",
            (
                "CR-VAL-CHRONOLOGY",
                None,
                "realize",
                "Invalid chronology validation request",
                "scope",
                "medium",
                "approved",
                "2026-04-10",
                "2026-04-09",
                "Temporary adversarial validation row.",
            ),
        )
        expect_change_request_schema_rejection(
            connection,
            "implemented request without decision date",
            (
                "CR-VAL-NO-DECISION",
                None,
                "realize",
                "Missing decision validation request",
                "reporting",
                "medium",
                "implemented",
                "2026-04-10",
                None,
                "Temporary adversarial validation row.",
            ),
        )
        expect_change_request_schema_rejection(
            connection,
            "invalid related task foreign key",
            (
                "CR-VAL-TASK-FK",
                "TASK-999",
                "realize",
                "Invalid task validation request",
                "data",
                "medium",
                "under review",
                "2026-04-10",
                None,
                "Temporary adversarial validation row.",
            ),
        )

    with validation_savepoint(connection, "change_request_phase_validation"):
        insert_validation_change_request(
            connection,
            (
                "CR-VAL-PHASE",
                "TASK-007",
                "explore",
                "Task phase mismatch validation request",
                "data",
                "medium",
                "under review",
                "2026-03-25",
                None,
                "Temporary adversarial validation row.",
            ),
        )
        try:
            validate_change_request_task_alignment(connection)
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "Change-request phase mismatch was not rejected by Python validation"
            )

    with validation_savepoint(connection, "data_quality_schema_validation"):
        expect_data_quality_schema_rejection(
            connection,
            "resolved issue without resolved date",
            (
                "DQ-VAL-NO-RESOLVED-DATE",
                "Temporary adversarial validation row.",
                None,
                "vendor",
                "VEN-001",
                "missing value",
                "medium",
                "resolved",
                "2026-04-01",
                None,
                1,
                2.0,
            ),
        )
        expect_data_quality_schema_rejection(
            connection,
            "open issue with resolved date",
            (
                "DQ-VAL-OPEN-RESOLVED-DATE",
                "Temporary adversarial validation row.",
                None,
                "vendor",
                "VEN-001",
                "missing value",
                "medium",
                "open",
                "2026-04-01",
                "2026-04-02",
                1,
                2.0,
            ),
        )
        expect_data_quality_schema_rejection(
            connection,
            "resolved date precedes detected date",
            (
                "DQ-VAL-CHRONOLOGY",
                "Temporary adversarial validation row.",
                None,
                "vendor",
                "VEN-001",
                "missing value",
                "medium",
                "resolved",
                "2026-04-02",
                "2026-04-01",
                1,
                2.0,
            ),
        )

    with validation_savepoint(connection, "data_quality_entity_validation"):
        insert_validation_data_quality_issue(
            connection,
            (
                "DQ-VAL-ENTITY",
                "Temporary adversarial validation row.",
                None,
                "vendor",
                "VEN-999",
                "invalid reference",
                "high",
                "open",
                "2026-04-01",
                None,
                1,
                3.0,
            ),
        )
        try:
            validate_data_quality_entity_references(connection)
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "Invalid affected entity was not rejected by Python validation"
            )

    with validation_savepoint(connection, "cancelled_denominator_validation"):
        insert_validation_data_quality_issue(
            connection,
            (
                "DQ-VAL-CANCELLED",
                "Temporary cancelled denominator validation row.",
                None,
                "vendor",
                "VEN-001",
                "missing value",
                "critical",
                "cancelled",
                "2026-04-01",
                None,
                1,
                4.0,
            ),
        )
        cancelled_result = connection.execute(
            """
            SELECT total_data_quality_issue_count,
                   non_cancelled_data_quality_issue_count,
                   cancelled_data_quality_issue_count,
                   data_quality_resolution_rate_pct,
                   data_quality_disposition_rate_pct,
                   go_live_readiness_classification
            FROM vw_project_readiness_summary
            """
        ).fetchone()
        if cancelled_result != (8, 6, 2, 50.0, 66.7, "not ready"):
            raise RuntimeError(
                "Cancelled issue changed the readiness denominator or result: "
                f"{cancelled_result}"
            )

    with validation_savepoint(connection, "critical_readiness_validation"):
        connection.execute(
            """
            UPDATE sap_activate_project_tasks
            SET task_status = 'in progress'
            WHERE task_id = 'TASK-010'
            """
        )
        connection.execute(
            """
            UPDATE data_quality_issues
            SET issue_status = 'resolved',
                resolved_date = '2026-05-05'
            WHERE data_quality_issue_id = 'DQ-004'
            """
        )
        baseline_classification = connection.execute(
            """
            SELECT go_live_readiness_classification
            FROM vw_project_readiness_summary
            """
        ).fetchone()[0]
        if baseline_classification != "at risk":
            raise RuntimeError(
                "Temporary readiness baseline was not at risk: "
                f"{baseline_classification}"
            )

        insert_validation_data_quality_issue(
            connection,
            (
                "DQ-VAL-CRITICAL",
                "Temporary critical readiness validation row.",
                "TASK-009",
                "invoice",
                "INV-004",
                "invalid reference",
                "critical",
                "open",
                "2026-05-02",
                None,
                0,
                4.0,
            ),
        )
        critical_classification = connection.execute(
            """
            SELECT go_live_readiness_classification
            FROM vw_project_readiness_summary
            """
        ).fetchone()[0]
        if critical_classification != "not ready":
            raise RuntimeError(
                "Critical unresolved issue did not change readiness to not ready: "
                f"{critical_classification}"
            )

        connection.execute(
            """
            UPDATE data_quality_issues
            SET issue_status = 'resolved',
                resolved_date = '2026-05-03'
            WHERE data_quality_issue_id = 'DQ-VAL-CRITICAL'
            """
        )
        restored_classification = connection.execute(
            """
            SELECT go_live_readiness_classification
            FROM vw_project_readiness_summary
            """
        ).fetchone()[0]
        if restored_classification != "at risk":
            raise RuntimeError(
                "Resolving the critical issue did not restore at-risk readiness: "
                f"{restored_classification}"
            )

    final_snapshot = phase6_state_snapshot(connection)
    temporary_row_count = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM change_requests
             WHERE change_request_id LIKE 'CR-VAL-%')
            + (SELECT COUNT(*) FROM data_quality_issues
               WHERE data_quality_issue_id LIKE 'DQ-VAL-%')
        """
    ).fetchone()[0]
    if final_snapshot != baseline_snapshot or temporary_row_count != 0:
        raise RuntimeError(
            "Adversarial Phase 6 validations changed the final dataset: "
            f"snapshot={final_snapshot}, temporary_rows={temporary_row_count}"
        )


def validate_phase6_rules(connection: sqlite3.Connection) -> None:
    validate_change_request_rows(connection)
    validate_change_request_task_alignment(connection)
    validate_data_quality_issue_rows(connection)
    validate_data_quality_task_alignment(connection)
    validate_data_quality_entity_references(connection)
    validate_phase1_to_phase5_source_facts_unchanged(connection)
    validate_change_request_phase_summary(connection)
    validate_project_readiness_summary(connection)
    validate_phase6_adversarial_cases(connection)
    validate_change_request_phase_summary(connection)
    validate_project_readiness_summary(connection)
