"""Run Phase 1-6 database validations in their established order."""

from __future__ import annotations

import sqlite3

from .validation_common import validate_expected_counts, validate_integrity_checks
from .validation_fulfillment import validate_phase3_rules
from .validation_invoice import validate_phase4_rules
from .validation_payment import validate_phase5_rules
from .validation_procurement import validate_phase2_rules
from .validation_readiness import validate_phase6_rules


def validate_database(connection: sqlite3.Connection) -> dict[str, int]:
    validate_integrity_checks(connection)
    counts = validate_expected_counts(connection)
    validate_phase2_rules(connection)
    validate_phase3_rules(connection)
    validate_phase4_rules(connection)
    validate_phase5_rules(connection)
    validate_phase6_rules(connection)
    return counts
