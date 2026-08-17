"""Generate synthetic master, SAP Activate, and procurement transaction data."""

from __future__ import annotations

import argparse
from pathlib import Path

from data_generation.config import DEFAULT_DB_PATH, DEFAULT_SEED, REPOSITORY_ROOT
from data_generation.expected_results import EXPECTED_COUNTS
from data_generation.persistence import build_database, prepare_database_path


def resolve_repo_path(path_value: str | Path) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return REPOSITORY_ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate the synthetic ERP procurement SQLite dataset."
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
