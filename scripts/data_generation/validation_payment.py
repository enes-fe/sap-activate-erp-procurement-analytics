"""Validate payment facts, eligibility, progress, and edge cases."""

from __future__ import annotations

import sqlite3

from .config import FLOAT_TOLERANCE
from .expected_results import EXPECTED_PAYMENT_DETAILS, EXPECTED_PAYMENT_PROGRESS_ROWS
from .validation_common import raise_if_rows, validation_savepoint
from .validation_invoice import insert_validation_invoice


def validate_payment_identifiers_and_rows(
    connection: sqlite3.Connection,
) -> None:
    payment_rows = connection.execute(
        """
        SELECT payment_id,
               invoice_id,
               payment_status_date,
               payment_date,
               ROUND(payment_amount, 2),
               payment_method,
               payment_status,
               clearing_reference
        FROM payments
        ORDER BY payment_id
        """
    ).fetchall()
    actual_payment_details = {
        str(payment_id): (
            str(invoice_id),
            str(payment_status_date),
            str(payment_date) if payment_date is not None else None,
            float(payment_amount),
            str(payment_method),
            str(payment_status),
            (
                str(clearing_reference)
                if clearing_reference is not None
                else None
            ),
        )
        for (
            payment_id,
            invoice_id,
            payment_status_date,
            payment_date,
            payment_amount,
            payment_method,
            payment_status,
            clearing_reference,
        ) in payment_rows
    }
    if actual_payment_details != EXPECTED_PAYMENT_DETAILS:
        raise RuntimeError(
            f"Unexpected deterministic payment rows: {actual_payment_details}"
        )


def validate_historical_payment_facts(
    connection: sqlite3.Connection,
) -> None:
    status_date_violations = connection.execute(
        """
        SELECT payment.payment_id,
               payment.payment_status_date,
               invoice.invoice_received_date
        FROM payments AS payment
        JOIN invoices AS invoice
            ON invoice.invoice_id = payment.invoice_id
        WHERE payment.payment_status_date < invoice.invoice_received_date
        """
    ).fetchall()
    raise_if_rows(
        status_date_violations,
        "Payment status date precedes invoice receipt",
    )

    successful_date_violations = connection.execute(
        """
        SELECT payment.payment_id,
               payment.payment_date,
               invoice.posting_date
        FROM payments AS payment
        JOIN invoices AS invoice
            ON invoice.invoice_id = payment.invoice_id
        WHERE payment.payment_status = 'paid'
            AND (
                invoice.posting_date IS NULL
                OR payment.payment_date < invoice.posting_date
            )
        """
    ).fetchall()
    raise_if_rows(
        successful_date_violations,
        "Successful payment precedes invoice posting",
    )

    single_payment_violations = connection.execute(
        f"""
        SELECT payment.payment_id,
               payment.payment_amount,
               invoice.invoice_total_amount
        FROM payments AS payment
        JOIN invoices AS invoice
            ON invoice.invoice_id = payment.invoice_id
        WHERE payment.payment_status = 'paid'
            AND (
                payment.payment_amount - invoice.invoice_total_amount
            ) > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(
        single_payment_violations,
        "Successful payment exceeds invoice total",
    )

    cumulative_payment_violations = connection.execute(
        f"""
        SELECT payment.invoice_id,
               ROUND(SUM(payment.payment_amount), 2)
                   AS successful_paid_amount,
               invoice.invoice_total_amount
        FROM payments AS payment
        JOIN invoices AS invoice
            ON invoice.invoice_id = payment.invoice_id
        WHERE payment.payment_status = 'paid'
        GROUP BY payment.invoice_id, invoice.invoice_total_amount
        HAVING (
            ROUND(SUM(payment.payment_amount), 2)
            - ROUND(invoice.invoice_total_amount, 2)
        ) > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(
        cumulative_payment_violations,
        "Cumulative successful payment exceeds invoice total",
    )


def validate_new_successful_payment_eligibility(
    connection: sqlite3.Connection,
    payment_ids: tuple[str, ...],
) -> None:
    if not payment_ids:
        return
    if len(payment_ids) != len(set(payment_ids)):
        raise RuntimeError(
            f"Duplicate new-payment candidate IDs: {payment_ids}"
        )

    placeholders = ", ".join("?" for _ in payment_ids)
    candidate_rows = connection.execute(
        f"""
        SELECT payment.payment_id,
               payment.invoice_id,
               payment.payment_status_date,
               payment.payment_date,
               payment.payment_amount,
               payment.payment_status,
               invoice.invoice_total_amount,
               invoice.invoice_status,
               invoice.blocked_flag,
               matching.invoice_matching_status
        FROM payments AS payment
        JOIN invoices AS invoice
            ON invoice.invoice_id = payment.invoice_id
        LEFT JOIN vw_invoice_matching_summary AS matching
            ON matching.invoice_id = invoice.invoice_id
        WHERE payment.payment_id IN ({placeholders})
        ORDER BY
            payment.invoice_id,
            payment.payment_status_date,
            payment.payment_date,
            payment.payment_id
        """,
        payment_ids,
    ).fetchall()
    actual_candidate_ids = {str(row[0]) for row in candidate_rows}
    missing_candidate_ids = set(payment_ids) - actual_candidate_ids
    if missing_candidate_ids:
        raise RuntimeError(
            "Missing new-payment candidate rows: "
            f"{sorted(missing_candidate_ids)}"
        )

    prior_successful_amounts = {
        str(invoice_id): float(successful_paid_amount)
        for invoice_id, successful_paid_amount in connection.execute(
            f"""
            SELECT invoice_id,
                   ROUND(SUM(payment_amount), 2)
            FROM payments
            WHERE payment_status = 'paid'
                AND payment_id NOT IN ({placeholders})
            GROUP BY invoice_id
            """,
            payment_ids,
        ).fetchall()
    }
    running_successful_amounts = dict(prior_successful_amounts)
    violations = []
    for (
        payment_id,
        invoice_id,
        _,
        _,
        payment_amount,
        payment_status,
        invoice_total_amount,
        invoice_status,
        blocked_flag,
        invoice_matching_status,
    ) in candidate_rows:
        invoice_key = str(invoice_id)
        candidate_amount = float(payment_amount)
        invoice_total = float(invoice_total_amount)
        successful_before_candidate = running_successful_amounts.get(
            invoice_key,
            0.0,
        )
        outstanding_before_candidate = round(
            invoice_total - successful_before_candidate,
            2,
        )
        reasons = []
        if payment_status != "paid":
            reasons.append("candidate status is not paid")
        if invoice_status not in ("posted", "approved"):
            reasons.append("invoice lifecycle is not posted or approved")
        if int(blocked_flag) != 0:
            reasons.append("invoice is currently blocked")
        if invoice_matching_status != "matched":
            reasons.append("invoice is not currently matched")
        if outstanding_before_candidate <= FLOAT_TOLERANCE:
            reasons.append("invoice has no positive outstanding balance")
        if (
            candidate_amount - outstanding_before_candidate
            > FLOAT_TOLERANCE
        ):
            reasons.append("candidate creates cumulative overpayment")
        if reasons:
            violations.append(
                (
                    str(payment_id),
                    invoice_key,
                    round(successful_before_candidate, 2),
                    outstanding_before_candidate,
                    reasons,
                )
            )
        if payment_status == "paid":
            running_successful_amounts[invoice_key] = round(
                successful_before_candidate + candidate_amount,
                2,
            )

    if violations:
        raise RuntimeError(
            "New successful payment candidate eligibility violations: "
            f"{violations}"
        )


def validate_payment_progress_view(connection: sqlite3.Connection) -> None:
    progress_rows = connection.execute(
        """
        SELECT invoice_id,
               invoice_currency,
               ROUND(invoice_total_amount, 2),
               invoice_status,
               blocked_flag,
               invoice_matching_status,
               eligible_for_payment_flag,
               ROUND(successful_paid_amount, 2),
               ROUND(outstanding_amount, 2),
               successful_payment_count,
               latest_successful_payment_date,
               payment_progress_status
        FROM vw_invoice_payment_progress
        ORDER BY invoice_id
        """
    ).fetchall()
    if progress_rows != EXPECTED_PAYMENT_PROGRESS_ROWS:
        raise RuntimeError(
            f"Unexpected invoice payment progress rows: {progress_rows}"
        )

    successful_rollup_violations = connection.execute(
        f"""
        WITH expected_successful_amounts AS (
            SELECT
                invoice.invoice_id,
                ROUND(
                    COALESCE(
                        SUM(
                            CASE
                                WHEN payment.payment_status = 'paid'
                                THEN payment.payment_amount
                                ELSE 0
                            END
                        ),
                        0
                    ),
                    2
                ) AS expected_successful_paid_amount
            FROM invoices AS invoice
            LEFT JOIN payments AS payment
                ON payment.invoice_id = invoice.invoice_id
            GROUP BY invoice.invoice_id
        )
        SELECT progress.invoice_id,
               progress.successful_paid_amount,
               expected.expected_successful_paid_amount
        FROM vw_invoice_payment_progress AS progress
        JOIN expected_successful_amounts AS expected
            ON expected.invoice_id = progress.invoice_id
        WHERE ABS(
            progress.successful_paid_amount
            - expected.expected_successful_paid_amount
        ) > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(
        successful_rollup_violations,
        "Non-successful payments affected successful paid amount",
    )

    completion_result = connection.execute(
        """
        SELECT
            SUM(
                CASE
                    WHEN payment_progress_status = 'paid' THEN 1
                    ELSE 0
                END
            ) AS fully_paid_invoice_count,
            COUNT(*) AS eligible_denominator,
            ROUND(
                100.0 * SUM(
                    CASE
                        WHEN payment_progress_status = 'paid' THEN 1
                        ELSE 0
                    END
                ) / COUNT(*),
                1
            ) AS completion_rate
        FROM vw_invoice_payment_progress
        WHERE invoice_status IN ('posted', 'approved')
            AND invoice_matching_status NOT IN ('excluded', 'invalid')
        """
    ).fetchone()
    if completion_result != (1, 4, 25.0):
        raise RuntimeError(
            "Unexpected Invoice Payment Completion Rate: "
            f"{completion_result}"
        )

    outstanding_by_currency = connection.execute(
        """
        SELECT invoice_currency,
               ROUND(SUM(outstanding_amount), 2)
        FROM vw_invoice_payment_progress
        WHERE outstanding_amount IS NOT NULL
        GROUP BY invoice_currency
        ORDER BY invoice_currency
        """
    ).fetchall()
    if outstanding_by_currency != [("EUR", 597.0), ("TRY", 1279.0)]:
        raise RuntimeError(
            "Unexpected outstanding invoice amount by currency: "
            f"{outstanding_by_currency}"
        )

    successful_paid_by_currency = connection.execute(
        """
        SELECT invoice_currency,
               ROUND(SUM(successful_paid_amount), 2)
        FROM vw_invoice_payment_progress
        GROUP BY invoice_currency
        ORDER BY invoice_currency
        """
    ).fetchall()
    if successful_paid_by_currency != [("EUR", 0.0), ("TRY", 2770.2)]:
        raise RuntimeError(
            "Unexpected successful paid amount by currency: "
            f"{successful_paid_by_currency}"
        )


def insert_validation_payment(
    connection: sqlite3.Connection,
    payment_id: str,
    invoice_id: str,
    payment_status_date: str,
    payment_date: str | None,
    payment_amount: float,
    payment_status: str,
    clearing_reference: str | None,
) -> None:
    connection.execute(
        """
        INSERT INTO payments (
            payment_id,
            invoice_id,
            payment_status_date,
            payment_date,
            payment_amount,
            payment_method,
            payment_status,
            clearing_reference
        )
        VALUES (?, ?, ?, ?, ?, 'bank transfer', ?, ?)
        """,
        (
            payment_id,
            invoice_id,
            payment_status_date,
            payment_date,
            payment_amount,
            payment_status,
            clearing_reference,
        ),
    )


def expect_payment_schema_rejection(
    connection: sqlite3.Connection,
    description: str,
    payment_values: tuple[
        str,
        str,
        str,
        str | None,
        float,
        str,
        str | None,
    ],
) -> None:
    try:
        insert_validation_payment(connection, *payment_values)
    except sqlite3.IntegrityError:
        return
    raise RuntimeError(
        f"Payment schema accepted invalid row: {description}"
    )


def expect_historical_payment_validation_failure(
    connection: sqlite3.Connection,
    expected_message: str,
) -> None:
    try:
        validate_historical_payment_facts(connection)
    except RuntimeError as error:
        if expected_message in str(error):
            return
        raise RuntimeError(
            "Historical payment validation failed for an unexpected reason: "
            f"{error}"
        ) from error
    raise RuntimeError(
        "Historical payment validation did not detect expected violation: "
        f"{expected_message}"
    )


def expect_new_payment_candidate_rejection(
    connection: sqlite3.Connection,
    payment_ids: tuple[str, ...],
    expected_message: str,
) -> None:
    try:
        validate_new_successful_payment_eligibility(
            connection,
            payment_ids,
        )
    except RuntimeError as error:
        if expected_message in str(error):
            return
        raise RuntimeError(
            "New-payment candidate validation failed for an unexpected "
            f"reason: {error}"
        ) from error
    raise RuntimeError(
        "New-payment candidate validation did not detect expected "
        f"violation: {expected_message}"
    )


def payment_progress_result(
    connection: sqlite3.Connection,
    invoice_id: str,
) -> tuple[object, ...] | None:
    return connection.execute(
        """
        SELECT eligible_for_payment_flag,
               ROUND(successful_paid_amount, 2),
               ROUND(outstanding_amount, 2),
               successful_payment_count,
               latest_successful_payment_date,
               payment_progress_status
        FROM vw_invoice_payment_progress
        WHERE invoice_id = ?
        """,
        (invoice_id,),
    ).fetchone()


def validate_payment_adversarial_cases(
    connection: sqlite3.Connection,
) -> None:
    with validation_savepoint(connection, "payment_progress_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-PROGRESS",
            "POI-007",
            "2026-03-03",
            120.0,
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-SCHEDULED",
            "INV-VAL-PAY-PROGRESS",
            "2026-03-04",
            None,
            585.60,
            "scheduled",
            None,
        )
        validate_historical_payment_facts(connection)
        unpaid_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-PROGRESS",
        )
        if unpaid_result != (1, 0.0, 585.6, 0, None, "unpaid"):
            raise RuntimeError(
                "Scheduled-payment exclusion validation failed: "
                f"{unpaid_result}"
            )

        insert_validation_payment(
            connection,
            "PAY-VAL-PARTIAL-1",
            "INV-VAL-PAY-PROGRESS",
            "2026-03-10",
            "2026-03-10",
            200.00,
            "paid",
            "CLR-VAL-PARTIAL-1",
        )
        validate_new_successful_payment_eligibility(
            connection,
            ("PAY-VAL-PARTIAL-1",),
        )
        validate_historical_payment_facts(connection)
        partial_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-PROGRESS",
        )
        if partial_result != (
            1,
            200.0,
            385.6,
            1,
            "2026-03-10",
            "partially paid",
        ):
            raise RuntimeError(
                f"Partial-payment validation failed: {partial_result}"
            )

        insert_validation_payment(
            connection,
            "PAY-VAL-PARTIAL-2",
            "INV-VAL-PAY-PROGRESS",
            "2026-03-15",
            "2026-03-15",
            385.60,
            "paid",
            "CLR-VAL-PARTIAL-2",
        )
        validate_new_successful_payment_eligibility(
            connection,
            ("PAY-VAL-PARTIAL-1", "PAY-VAL-PARTIAL-2"),
        )
        validate_historical_payment_facts(connection)
        paid_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-PROGRESS",
        )
        if paid_result != (
            0,
            585.6,
            0.0,
            2,
            "2026-03-15",
            "paid",
        ):
            raise RuntimeError(
                f"Multiple-payment accumulation validation failed: {paid_result}"
            )

        insert_validation_payment(
            connection,
            "PAY-VAL-OVERPAYMENT",
            "INV-VAL-PAY-PROGRESS",
            "2026-03-16",
            "2026-03-16",
            0.01,
            "paid",
            "CLR-VAL-OVERPAYMENT",
        )
        expect_new_payment_candidate_rejection(
            connection,
            ("PAY-VAL-OVERPAYMENT",),
            "invoice has no positive outstanding balance",
        )
        expect_historical_payment_validation_failure(
            connection,
            "Cumulative successful payment exceeds invoice total",
        )

    with validation_savepoint(connection, "blocked_payment_validation"):
        insert_validation_payment(
            connection,
            "PAY-VAL-BLOCKED",
            "INV-002",
            "2026-03-05",
            "2026-03-05",
            10.00,
            "paid",
            "CLR-VAL-BLOCKED",
        )
        expect_new_payment_candidate_rejection(
            connection,
            ("PAY-VAL-BLOCKED",),
            "invoice is currently blocked",
        )
        validate_historical_payment_facts(connection)

    with validation_savepoint(connection, "cancelled_payment_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-CANCELLED",
            "POI-007",
            "2026-03-03",
            120.0,
            invoice_status="cancelled",
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-CANCELLED-INVOICE",
            "INV-VAL-PAY-CANCELLED",
            "2026-03-05",
            "2026-03-05",
            100.00,
            "paid",
            "CLR-VAL-CANCELLED-INVOICE",
        )
        cancelled_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-CANCELLED",
        )
        if cancelled_result != (
            0,
            100.0,
            None,
            1,
            "2026-03-05",
            None,
        ):
            raise RuntimeError(
                "Cancelled-invoice payment-progress validation failed: "
                f"{cancelled_result}"
            )
        expect_new_payment_candidate_rejection(
            connection,
            ("PAY-VAL-CANCELLED-INVOICE",),
            "invoice lifecycle is not posted or approved",
        )
        validate_historical_payment_facts(connection)

    with validation_savepoint(connection, "invalid_payment_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-INVALID",
            "POI-007",
            "2026-03-03",
            None,
        )
        connection.execute(
            """
            UPDATE invoices
            SET invoice_total_amount = 100
            WHERE invoice_id = 'INV-VAL-PAY-INVALID'
            """
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-INVALID-INVOICE",
            "INV-VAL-PAY-INVALID",
            "2026-03-05",
            "2026-03-05",
            100.00,
            "paid",
            "CLR-VAL-INVALID-INVOICE",
        )
        invalid_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-INVALID",
        )
        if invalid_result != (
            0,
            100.0,
            None,
            1,
            "2026-03-05",
            None,
        ):
            raise RuntimeError(
                "Invalid-invoice payment-progress validation failed: "
                f"{invalid_result}"
            )
        expect_new_payment_candidate_rejection(
            connection,
            ("PAY-VAL-INVALID-INVOICE",),
            "invoice is not currently matched",
        )
        validate_historical_payment_facts(connection)

    with validation_savepoint(connection, "payment_schema_validation"):
        expect_payment_schema_rejection(
            connection,
            "paid row without payment_date",
            (
                "PAY-VAL-NO-DATE",
                "INV-001",
                "2026-03-22",
                None,
                1.00,
                "paid",
                "CLR-VAL-NO-DATE",
            ),
        )
        expect_payment_schema_rejection(
            connection,
            "paid row without clearing_reference",
            (
                "PAY-VAL-NO-REFERENCE",
                "INV-001",
                "2026-03-22",
                "2026-03-22",
                1.00,
                "paid",
                None,
            ),
        )
        expect_payment_schema_rejection(
            connection,
            "non-paid row with payment_date",
            (
                "PAY-VAL-FAILED-DATE",
                "INV-001",
                "2026-03-22",
                "2026-03-22",
                1.00,
                "failed",
                None,
            ),
        )
        expect_payment_schema_rejection(
            connection,
            "non-paid row with clearing_reference",
            (
                "PAY-VAL-FAILED-REFERENCE",
                "INV-001",
                "2026-03-22",
                None,
                1.00,
                "failed",
                "CLR-VAL-FAILED",
            ),
        )
        expect_payment_schema_rejection(
            connection,
            "duplicate successful clearing reference",
            (
                "PAY-VAL-DUPLICATE-REFERENCE",
                "INV-001",
                "2026-03-22",
                "2026-03-22",
                1.00,
                "paid",
                "CLR-2026-000001",
            ),
        )

    with validation_savepoint(connection, "status_date_validation"):
        insert_validation_payment(
            connection,
            "PAY-VAL-EARLY-STATUS",
            "INV-001",
            "2026-02-28",
            None,
            10.00,
            "failed",
            None,
        )
        expect_historical_payment_validation_failure(
            connection,
            "Payment status date precedes invoice receipt",
        )

    with validation_savepoint(connection, "payment_date_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-EARLY",
            "POI-007",
            "2026-03-03",
            120.0,
        )
        connection.execute(
            """
            UPDATE invoices
            SET posting_date = '2026-03-05'
            WHERE invoice_id = 'INV-VAL-PAY-EARLY'
            """
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-EARLY-PAYMENT",
            "INV-VAL-PAY-EARLY",
            "2026-03-04",
            "2026-03-04",
            100.00,
            "paid",
            "CLR-VAL-EARLY-PAYMENT",
        )
        expect_historical_payment_validation_failure(
            connection,
            "Successful payment precedes invoice posting",
        )

    with validation_savepoint(connection, "single_payment_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-SINGLE",
            "POI-007",
            "2026-03-03",
            120.0,
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-SINGLE-OVER",
            "INV-VAL-PAY-SINGLE",
            "2026-03-05",
            "2026-03-05",
            585.61,
            "paid",
            "CLR-VAL-SINGLE-OVER",
        )
        expect_historical_payment_validation_failure(
            connection,
            "Successful payment exceeds invoice total",
        )

    with validation_savepoint(connection, "historical_payment_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-HISTORY",
            "POI-007",
            "2026-03-03",
            120.0,
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-HISTORY",
            "INV-VAL-PAY-HISTORY",
            "2026-03-05",
            "2026-03-05",
            585.60,
            "paid",
            "CLR-VAL-HISTORY",
        )
        validate_new_successful_payment_eligibility(
            connection,
            ("PAY-VAL-HISTORY",),
        )
        validate_historical_payment_facts(connection)
        connection.execute(
            """
            UPDATE invoices
            SET blocked_flag = 1,
                block_reason = 'temporary post-payment validation hold'
            WHERE invoice_id = 'INV-VAL-PAY-HISTORY'
            """
        )
        historical_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-HISTORY",
        )
        if historical_result != (
            0,
            585.6,
            0.0,
            1,
            "2026-03-05",
            "paid",
        ):
            raise RuntimeError(
                "Historical successful payment was not preserved: "
                f"{historical_result}"
            )
        validate_historical_payment_facts(connection)

    with validation_savepoint(
        connection,
        "historical_cancelled_payment_validation",
    ):
        insert_validation_invoice(
            connection,
            "INV-VAL-PAY-HIST-CANCEL",
            "POI-007",
            "2026-03-03",
            120.0,
        )
        insert_validation_payment(
            connection,
            "PAY-VAL-HIST-CANCEL",
            "INV-VAL-PAY-HIST-CANCEL",
            "2026-03-05",
            "2026-03-05",
            585.60,
            "paid",
            "CLR-VAL-HIST-CANCEL",
        )
        validate_new_successful_payment_eligibility(
            connection,
            ("PAY-VAL-HIST-CANCEL",),
        )
        validate_historical_payment_facts(connection)
        connection.execute(
            """
            UPDATE invoices
            SET invoice_status = 'cancelled'
            WHERE invoice_id = 'INV-VAL-PAY-HIST-CANCEL'
            """
        )
        cancelled_historical_result = payment_progress_result(
            connection,
            "INV-VAL-PAY-HIST-CANCEL",
        )
        if cancelled_historical_result != (
            0,
            585.6,
            None,
            1,
            "2026-03-05",
            None,
        ):
            raise RuntimeError(
                "Cancelled invoice lost historical successful payment "
                f"facts: {cancelled_historical_result}"
            )
        validate_historical_payment_facts(connection)

    final_counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM invoices),
            (SELECT COUNT(*) FROM invoice_items),
            (SELECT COUNT(*) FROM payments)
        """
    ).fetchone()
    temporary_row_count = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM invoices
             WHERE invoice_id LIKE 'INV-VAL-PAY-%')
            + (SELECT COUNT(*) FROM invoice_items
               WHERE invoice_item_id LIKE 'INVI-VAL-PAY-%')
            + (SELECT COUNT(*) FROM payments
               WHERE payment_id LIKE 'PAY-VAL-%')
        """
    ).fetchone()[0]
    if final_counts != (4, 5, 5) or temporary_row_count != 0:
        raise RuntimeError(
            "Adversarial payment validations changed the final dataset: "
            f"counts={final_counts}, temporary_rows={temporary_row_count}"
        )

    validate_historical_payment_facts(connection)
    validate_payment_progress_view(connection)


def validate_phase5_rules(connection: sqlite3.Connection) -> None:
    validate_payment_identifiers_and_rows(connection)
    validate_new_successful_payment_eligibility(
        connection,
        ("PAY-003", "PAY-004"),
    )
    validate_historical_payment_facts(connection)
    validate_payment_progress_view(connection)
    validate_payment_adversarial_cases(connection)
