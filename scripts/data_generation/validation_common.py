"""Small domain-independent validation helpers."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from .config import ITEM_NUMBER_STEP
from .expected_results import EXPECTED_COUNTS


def raise_if_rows(rows: list[tuple[object, ...]], message: str) -> None:
    if rows:
        raise RuntimeError(f"{message}: {rows}")


@contextmanager
def validation_savepoint(
    connection: sqlite3.Connection,
    savepoint_name: str,
) -> Iterator[None]:
    connection.execute(f"SAVEPOINT {savepoint_name}")
    try:
        yield
    finally:
        connection.execute(f"ROLLBACK TO {savepoint_name}")
        connection.execute(f"RELEASE {savepoint_name}")


def validate_integrity_checks(connection: sqlite3.Connection) -> None:
    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity_result is None or integrity_result[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")

    foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_violations:
        raise RuntimeError(f"SQLite foreign key check failed: {foreign_key_violations}")


def validate_expected_counts(connection: sqlite3.Connection) -> dict[str, int]:
    counts = {
        table_name: connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"
        ).fetchone()[0]
        for table_name in EXPECTED_COUNTS
    }
    mismatches = {
        table_name: (EXPECTED_COUNTS[table_name], actual_count)
        for table_name, actual_count in counts.items()
        if actual_count != EXPECTED_COUNTS[table_name]
    }
    if mismatches:
        raise RuntimeError(f"Unexpected table counts: {mismatches}")
    return counts


def validate_item_number_sequences(
    connection: sqlite3.Connection,
    table_name: str,
    parent_column: str,
    item_number_column: str,
) -> None:
    duplicate_rows = connection.execute(
        f"""
        SELECT {parent_column}, {item_number_column}, COUNT(*) AS duplicate_count
        FROM {table_name}
        GROUP BY {parent_column}, {item_number_column}
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    raise_if_rows(duplicate_rows, f"Duplicate item numbers in {table_name}")

    sequence_rows = connection.execute(
        f"""
        SELECT {parent_column}, GROUP_CONCAT({item_number_column}, ',') AS item_numbers
        FROM (
            SELECT {parent_column}, {item_number_column}
            FROM {table_name}
            ORDER BY {parent_column}, {item_number_column}
        )
        GROUP BY {parent_column}
        """
    ).fetchall()
    violations = []
    for parent_id, item_numbers in sequence_rows:
        actual_numbers = [int(value) for value in str(item_numbers).split(",")]
        expected_numbers = list(
            range(
                ITEM_NUMBER_STEP,
                ITEM_NUMBER_STEP * (len(actual_numbers) + 1),
                ITEM_NUMBER_STEP,
            )
        )
        if actual_numbers != expected_numbers:
            violations.append((parent_id, actual_numbers, expected_numbers))
    if violations:
        raise RuntimeError(f"Invalid item number sequence in {table_name}: {violations}")
