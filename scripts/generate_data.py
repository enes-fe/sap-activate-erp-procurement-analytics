"""Generate Phase 1 synthetic master and SAP Activate data."""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker


DEFAULT_SEED = 42
DEFAULT_DB_PATH = Path("database") / "marmara_components.db"

EXPECTED_COUNTS = {
    "vendors": 5,
    "plants": 2,
    "purchasing_groups": 3,
    "material_groups": 4,
    "materials": 12,
    "sap_activate_project_tasks": 12,
}


def repository_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return repository_root() / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the Phase 1 synthetic SQLite dataset."
    )
    parser.add_argument(
        "--db",
        default=str(DEFAULT_DB_PATH),
        help=f"SQLite database path, relative to the repo root by default ({DEFAULT_DB_PATH}).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"Deterministic random seed (default: {DEFAULT_SEED}).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete an existing database before regenerating it.",
    )
    return parser.parse_args()


def prepare_database_path(db_path: Path, reset: bool) -> None:
    if db_path.exists():
        if not reset:
            raise SystemExit(
                f"Database already exists at {db_path}. Re-run with --reset to recreate it."
            )
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def create_generators(seed: int) -> tuple[random.Random, Faker]:
    random.seed(seed)
    rng = random.Random(seed)
    fake = Faker("tr_TR")
    fake.seed_instance(seed)
    return rng, fake


def iso_date(value: date) -> str:
    return value.isoformat()


def offset_date(start: date, days: int) -> str:
    return iso_date(start + timedelta(days=days))


def generate_vendors(rng: random.Random) -> list[dict[str, object]]:
    base_date = date(2024, 10, 1)
    vendor_specs = [
        (
            "VEN-001",
            "Anadolu Metal Sanayi A.S.",
            "Turkiye",
            "raw material supplier",
            "Net 30",
            1,
            "active",
        ),
        (
            "VEN-002",
            "Ruhr Stahlhandel GmbH",
            "Germany",
            "raw material supplier",
            "Net 45",
            1,
            "active",
        ),
        (
            "VEN-003",
            "Ege Packaging A.S.",
            "Turkiye",
            "packaging supplier",
            "Net 30",
            0,
            "active",
        ),
        (
            "VEN-004",
            "Bursa Teknik Bakim Ltd.",
            "Turkiye",
            "mro supplier",
            "Net 15",
            0,
            "active",
        ),
        (
            "VEN-005",
            "Lombardia Industrial Services S.r.l.",
            "Italy",
            "service supplier",
            "Net 60",
            0,
            "pending review",
        ),
    ]

    vendors = []
    for spec in vendor_specs:
        (
            vendor_id,
            vendor_name,
            country,
            vendor_category,
            payment_terms,
            preferred_vendor_flag,
            vendor_status,
        ) = spec
        vendors.append(
            {
                "vendor_id": vendor_id,
                "vendor_name": vendor_name,
                "country": country,
                "vendor_category": vendor_category,
                "payment_terms": payment_terms,
                "preferred_vendor_flag": preferred_vendor_flag,
                "vendor_status": vendor_status,
                "created_date": offset_date(base_date, rng.randint(0, 90)),
            }
        )
    return vendors


def generate_plants() -> list[dict[str, object]]:
    return [
        {
            "plant_id": "PL-001",
            "plant_name": "Marmara Components Gebze Manufacturing Plant",
            "city": "Gebze",
            "country": "Turkiye",
            "plant_type": "manufacturing",
            "plant_status": "active",
        },
        {
            "plant_id": "PL-002",
            "plant_name": "Marmara Components Bursa Distribution Center",
            "city": "Bursa",
            "country": "Turkiye",
            "plant_type": "distribution",
            "plant_status": "active",
        },
    ]


def generate_purchasing_groups(fake: Faker) -> list[dict[str, object]]:
    return [
        {
            "purchasing_group_id": "PG-001",
            "purchasing_group_name": "Direct Materials Sourcing",
            "manager_name": fake.name(),
            "process_area": "direct materials",
            "status": "active",
        },
        {
            "purchasing_group_id": "PG-002",
            "purchasing_group_name": "Indirect Materials and Packaging",
            "manager_name": fake.name(),
            "process_area": "indirect materials",
            "status": "active",
        },
        {
            "purchasing_group_id": "PG-003",
            "purchasing_group_name": "MRO and Plant Services",
            "manager_name": fake.name(),
            "process_area": "mro",
            "status": "active",
        },
    ]


def generate_material_groups() -> list[dict[str, object]]:
    return [
        {
            "material_group_id": "MG-001",
            "material_group_name": "Metals and Raw Materials",
            "category_owner": "Direct Materials Lead",
            "spend_category": "Direct Materials",
            "status": "active",
        },
        {
            "material_group_id": "MG-002",
            "material_group_name": "Packaging Materials",
            "category_owner": "Packaging Lead",
            "spend_category": "Indirect Materials",
            "status": "active",
        },
        {
            "material_group_id": "MG-003",
            "material_group_name": "MRO Spare Parts",
            "category_owner": "Maintenance Lead",
            "spend_category": "MRO",
            "status": "active",
        },
        {
            "material_group_id": "MG-004",
            "material_group_name": "Plant Consumables and Services",
            "category_owner": "Operations Lead",
            "spend_category": "Services and Consumables",
            "status": "active",
        },
    ]


def generate_materials() -> list[dict[str, object]]:
    material_specs = [
        ("MAT-001", "MG-001", "Cold Rolled Steel Coil", "KG", "raw material", 1.15),
        ("MAT-002", "MG-001", "Aluminum Extrusion Bar", "KG", "raw material", 3.85),
        ("MAT-003", "MG-001", "Copper Busbar", "KG", "raw material", 8.75),
        ("MAT-004", "MG-002", "Corrugated Export Carton", "EA", "packaging", 1.2),
        ("MAT-005", "MG-002", "Stretch Film Roll", "EA", "packaging", 18.5),
        ("MAT-006", "MG-002", "Wooden Export Pallet", "EA", "packaging", 14.75),
        ("MAT-007", "MG-003", "Hydraulic Seal Kit", "EA", "spare part", 42.0),
        ("MAT-008", "MG-003", "CNC Spindle Bearing", "EA", "spare part", 185.0),
        ("MAT-009", "MG-003", "Conveyor Motor Assembly", "EA", "spare part", 420.0),
        ("MAT-010", "MG-004", "Cutting Fluid Concentrate", "L", "consumable", 4.9),
        ("MAT-011", "MG-004", "Industrial Safety Gloves", "EA", "consumable", 6.5),
        ("MAT-012", "MG-004", "Preventive Maintenance Service", "HR", "service", 55.0),
    ]
    return [
        {
            "material_id": material_id,
            "material_group_id": material_group_id,
            "material_name": material_name,
            "base_unit_of_measure": unit,
            "material_type": material_type,
            "standard_price": standard_price,
            "material_status": "active",
        }
        for (
            material_id,
            material_group_id,
            material_name,
            unit,
            material_type,
            standard_price,
        ) in material_specs
    ]


def generate_sap_activate_project_tasks() -> list[dict[str, object]]:
    task_specs = [
        (
            "TASK-001",
            "discover",
            "Procurement",
            "Procurement baseline assessment",
            "Procurement Lead",
            "2026-01-06",
            "2026-01-17",
            "2026-01-16",
            "completed",
            1.2,
            100,
            1,
        ),
        (
            "TASK-002",
            "discover",
            "Reporting",
            "KPI and stakeholder alignment",
            "Reporting Lead",
            "2026-01-13",
            "2026-01-24",
            "2026-01-24",
            "completed",
            0.8,
            100,
            0,
        ),
        (
            "TASK-003",
            "prepare",
            "Data Migration",
            "Data migration strategy and ownership",
            "Data Migration Lead",
            "2026-01-27",
            "2026-02-07",
            "2026-02-07",
            "completed",
            1.3,
            100,
            1,
        ),
        (
            "TASK-004",
            "prepare",
            "Procurement",
            "Procurement project plan and resourcing",
            "Solution Architect",
            "2026-02-03",
            "2026-02-14",
            "2026-02-14",
            "completed",
            0.9,
            100,
            0,
        ),
        (
            "TASK-005",
            "explore",
            "Procurement",
            "Purchase-to-pay fit-gap workshops",
            "Solution Architect",
            "2026-02-17",
            "2026-03-07",
            "2026-03-08",
            "completed",
            1.4,
            100,
            1,
        ),
        (
            "TASK-006",
            "explore",
            "Reporting",
            "Reporting requirements and KPI definitions",
            "Reporting Lead",
            "2026-02-24",
            "2026-03-14",
            "2026-03-14",
            "completed",
            1.0,
            100,
            0,
        ),
        (
            "TASK-007",
            "realize",
            "Data Migration",
            "Vendor and material master data build",
            "Data Migration Lead",
            "2026-03-17",
            "2026-04-18",
            None,
            "in progress",
            1.5,
            78,
            1,
        ),
        (
            "TASK-008",
            "realize",
            "Reporting",
            "Procurement analytics prototype validation",
            "Reporting Lead",
            "2026-04-01",
            "2026-04-25",
            None,
            "delayed",
            0.9,
            62,
            0,
        ),
        (
            "TASK-009",
            "deploy",
            "Testing",
            "User acceptance testing for procurement",
            "Test Manager",
            "2026-04-28",
            "2026-05-16",
            None,
            "in progress",
            1.4,
            45,
            1,
        ),
        (
            "TASK-010",
            "deploy",
            "Training",
            "Key user training and job aids",
            "Training Lead",
            "2026-05-05",
            "2026-05-23",
            None,
            "blocked",
            1.1,
            25,
            1,
        ),
        (
            "TASK-011",
            "run",
            "Cutover",
            "Cutover readiness checkpoint",
            "Cutover Manager",
            "2026-05-26",
            "2026-06-06",
            None,
            "delayed",
            1.5,
            35,
            1,
        ),
        (
            "TASK-012",
            "run",
            "Reporting",
            "Hypercare reporting backlog setup",
            "Reporting Lead",
            "2026-06-09",
            "2026-06-27",
            None,
            "not started",
            0.7,
            0,
            0,
        ),
    ]

    return [
        {
            "task_id": task_id,
            "activate_phase": activate_phase,
            "workstream": workstream,
            "task_name": task_name,
            "task_owner": task_owner,
            "planned_start_date": planned_start_date,
            "planned_finish_date": planned_finish_date,
            "actual_finish_date": actual_finish_date,
            "task_status": task_status,
            "readiness_weight": readiness_weight,
            "completion_percent": completion_percent,
            "critical_flag": critical_flag,
        }
        for (
            task_id,
            activate_phase,
            workstream,
            task_name,
            task_owner,
            planned_start_date,
            planned_finish_date,
            actual_finish_date,
            task_status,
            readiness_weight,
            completion_percent,
            critical_flag,
        ) in task_specs
    ]


def generate_dataset(seed: int) -> dict[str, list[dict[str, object]]]:
    rng, fake = create_generators(seed)
    return {
        "vendors": generate_vendors(rng),
        "plants": generate_plants(),
        "purchasing_groups": generate_purchasing_groups(fake),
        "material_groups": generate_material_groups(),
        "materials": generate_materials(),
        "sap_activate_project_tasks": generate_sap_activate_project_tasks(),
    }


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
        "sap_activate_project_tasks",
    ]
    for table_name in insertion_order:
        insert_rows(connection, table_name, dataset[table_name])


def validate_database(connection: sqlite3.Connection) -> dict[str, int]:
    integrity_result = connection.execute("PRAGMA integrity_check").fetchone()
    if integrity_result is None or integrity_result[0] != "ok":
        raise RuntimeError(f"SQLite integrity check failed: {integrity_result}")

    foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_violations:
        raise RuntimeError(f"SQLite foreign key check failed: {foreign_key_violations}")

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


def build_database(db_path: Path, seed: int) -> dict[str, int]:
    schema_path = repository_root() / "database" / "schema.sql"
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


def print_success_summary(db_path: Path, seed: int, counts: dict[str, int]) -> None:
    print(f"Generated database: {db_path}")
    print(f"Seed: {seed}")
    print("Row counts:")
    for table_name in EXPECTED_COUNTS:
        print(f"  {table_name}: {counts[table_name]}")


def main() -> None:
    args = parse_args()
    db_path = resolve_repo_path(args.db)
    prepare_database_path(db_path, args.reset)
    counts = build_database(db_path, args.seed)
    print_success_summary(db_path, args.seed, counts)


if __name__ == "__main__":
    main()
