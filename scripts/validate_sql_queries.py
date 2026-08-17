from __future__ import annotations

import math
import sqlite3
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = REPOSITORY_ROOT / "database" / "marmara_components.db"
SQL_DIRECTORY = REPOSITORY_ROOT / "sql"

ExpectedHeadline = tuple[tuple[str, ...], tuple[Any, ...]]

EXPECTED_HEADLINES: dict[str, ExpectedHeadline] = {
    "01_procurement_spend.sql": (
        (
            "non_cancelled_po_count",
            "non_cancelled_po_item_count",
            "try_commitment_value",
            "eur_commitment_value",
        ),
        (7, 14, 7216.64, 4269.30),
    ),
    "02_supplier_delivery_performance.sql": (
        (
            "eligible_active_due_po_items",
            "otif_item_count",
            "po_item_otif_rate_pct",
            "receipt_event_on_time_rate_pct",
            "average_late_receipt_delay_days",
        ),
        (12, 3, 25.0, 50.0, 2.2),
    ),
    "03_open_po_analysis.sql": (
        (
            "active_po_headers_with_open_partial_items",
            "open_partial_item_count",
            "try_remaining_commitment",
            "eur_remaining_commitment",
        ),
        (4, 5, 1118.82, 2245.80),
    ),
    "04_invoice_matching_analysis.sql": (
        (
            "eligible_invoice_item_count",
            "matched_item_count",
            "exception_item_count",
            "exception_rate_pct",
            "blocked_invoice_count",
        ),
        (5, 2, 3, 60.0, 3),
    ),
    "05_payment_progress_analysis.sql": (
        (
            "valid_invoice_count",
            "fully_paid_invoice_count",
            "completion_rate_pct",
            "try_outstanding_amount",
            "eur_outstanding_amount",
        ),
        (4, 1, 25.0, 1279.00, 597.00),
    ),
    "06_project_readiness_analysis.sql": (
        (
            "pre_go_live_task_count",
            "completed_pre_go_live_task_count",
            "open_change_request_count",
            "unresolved_high_critical_dq_issue_count",
            "go_live_readiness_classification",
        ),
        (10, 6, 3, 2, "not ready"),
    ),
}


def fail(message: str) -> None:
    print(f"FAIL {message}", file=sys.stderr)
    raise SystemExit(1)


def split_complete_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    buffer: list[str] = []

    for line in sql_text.splitlines(keepends=True):
        buffer.append(line)
        candidate = "".join(buffer)
        if sqlite3.complete_statement(candidate):
            if candidate.strip():
                statements.append(candidate.strip())
            buffer = []

    remaining = "".join(buffer)
    if remaining.strip():
        raise ValueError("file ends with an incomplete SQLite statement")

    if not statements:
        raise ValueError("file contains no complete SQLite statements")

    return statements


def execute_sql_file(
    connection: sqlite3.Connection,
    sql_path: Path,
) -> list[tuple[tuple[str, ...], list[tuple[Any, ...]]]]:
    statements = split_complete_statements(sql_path.read_text(encoding="utf-8"))
    result_sets: list[tuple[tuple[str, ...], list[tuple[Any, ...]]]] = []

    for statement_number, statement in enumerate(statements, start=1):
        try:
            cursor = connection.execute(statement)
            if cursor.description is None:
                fail(
                    f"{sql_path.name} statement {statement_number} "
                    "did not produce a result set"
                )
            columns = tuple(column[0] for column in cursor.description)
            rows = [tuple(row) for row in cursor.fetchall()]
        except sqlite3.Error as error:
            fail(
                f"{sql_path.name} statement {statement_number} SQL error: "
                f"{error}"
            )
        result_sets.append((columns, rows))

    return result_sets


def values_match(actual: Any, expected: Any) -> bool:
    if (
        isinstance(actual, (int, float))
        and not isinstance(actual, bool)
        and isinstance(expected, (int, float))
        and not isinstance(expected, bool)
    ):
        return math.isclose(
            float(actual),
            float(expected),
            rel_tol=0.0,
            abs_tol=1e-9,
        )
    return actual == expected


def validate_final_headline(
    sql_path: Path,
    result_sets: list[tuple[tuple[str, ...], list[tuple[Any, ...]]]],
) -> None:
    expected_columns, expected_row = EXPECTED_HEADLINES[sql_path.name]
    actual_columns, actual_rows = result_sets[-1]

    if actual_columns != expected_columns:
        fail(
            f"{sql_path.name} final columns mismatch: "
            f"expected {expected_columns}, got {actual_columns}"
        )

    if len(actual_rows) != 1:
        fail(
            f"{sql_path.name} final result must contain exactly one row; "
            f"got {len(actual_rows)}"
        )

    actual_row = actual_rows[0]
    if len(actual_row) != len(expected_row) or any(
        not values_match(actual, expected)
        for actual, expected in zip(actual_row, expected_row)
    ):
        fail(
            f"{sql_path.name} headline mismatch: "
            f"expected {expected_row}, got {actual_row}"
        )


def main() -> None:
    if not DATABASE_PATH.is_file():
        fail(f"database not found: {DATABASE_PATH}")
    if not SQL_DIRECTORY.is_dir():
        fail(f"SQL directory not found: {SQL_DIRECTORY}")

    sql_paths = sorted(SQL_DIRECTORY.glob("[0-9][0-9]_*.sql"))
    discovered_names = [path.name for path in sql_paths]
    expected_names = list(EXPECTED_HEADLINES)
    if discovered_names != expected_names:
        fail(
            "analytics file set mismatch: "
            f"expected {expected_names}, got {discovered_names}"
        )

    database_uri = f"{DATABASE_PATH.resolve().as_uri()}?mode=ro"
    try:
        connection = sqlite3.connect(database_uri, uri=True)
    except sqlite3.Error as error:
        fail(f"could not open database read-only: {error}")

    try:
        connection.execute("PRAGMA query_only = ON")
        for sql_path in sql_paths:
            try:
                result_sets = execute_sql_file(connection, sql_path)
            except (OSError, UnicodeError, ValueError) as error:
                fail(f"{sql_path.name}: {error}")
            validate_final_headline(sql_path, result_sets)
            print(
                f"PASS {sql_path.name} "
                f"({len(result_sets)} statements, headline matched)"
            )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
