"""Build and persist the generated SQLite dataset."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .config import REPOSITORY_ROOT
from .generators import generate_dataset
from .validation import validate_database


def prepare_database_path(db_path: Path, reset: bool) -> None:
    if db_path.exists():
        if not reset:
            raise SystemExit(
                f"Database already exists at {db_path}. Re-run with --reset to recreate it."
            )
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def apply_schema(connection: sqlite3.Connection, schema_path: Path) -> None:
    schema_sql = schema_path.read_text(encoding="utf-8")
    connection.executescript(schema_sql)
    connection.execute("PRAGMA foreign_keys = ON")


def insert_rows(
    connection: sqlite3.Connection, table_name: str, rows: list[dict[str, object]]
) -> None:
    if not rows:
        return

    columns = tuple(rows[0].keys())
    placeholders = ", ".join(f":{column}" for column in columns)
    column_list = ", ".join(columns)
    sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
    connection.executemany(sql, rows)


def insert_dataset(
    connection: sqlite3.Connection, dataset: dict[str, list[dict[str, object]]]
) -> None:
    insertion_order = [
        "vendors",
        "plants",
        "purchasing_groups",
        "material_groups",
        "materials",
        "purchase_requisitions",
        "purchase_requisition_items",
        "purchase_orders",
        "purchase_order_items",
        "goods_receipts",
        "invoices",
        "invoice_items",
        "payments",
        "sap_activate_project_tasks",
        "change_requests",
        "data_quality_issues",
    ]
    for table_name in insertion_order:
        insert_rows(connection, table_name, dataset[table_name])


def build_database(db_path: Path, seed: int) -> dict[str, int]:
    schema_path = REPOSITORY_ROOT / "database" / "schema.sql"
    dataset = generate_dataset(seed)
    connection = sqlite3.connect(db_path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        apply_schema(connection, schema_path)
        connection.execute("BEGIN")
        insert_dataset(connection, dataset)
        counts = validate_database(connection)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    return counts
