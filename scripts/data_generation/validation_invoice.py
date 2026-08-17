"""Validate invoices, three-way matching, and invoice summaries."""

from __future__ import annotations

import sqlite3

from .config import FLOAT_TOLERANCE, ITEM_NUMBER_STEP
from .expected_results import (
    EXPECTED_INVOICE_BLOCKING,
    EXPECTED_INVOICE_HEADER_DETAILS,
    EXPECTED_INVOICE_IDS,
    EXPECTED_INVOICE_ITEM_IDS,
    EXPECTED_INVOICE_ITEM_REFERENCES,
    EXPECTED_INVOICE_MATCHING_STATUSES,
    EXPECTED_INVOICE_NUMBERS,
)
from .validation_common import (
    raise_if_rows,
    validate_item_number_sequences,
    validation_savepoint,
)


def validate_invoice_identifiers_and_references(
    connection: sqlite3.Connection,
) -> None:
    invoice_rows = connection.execute(
        """
        SELECT invoice_id,
               invoice_number,
               vendor_id,
               invoice_date,
               invoice_received_date,
               posting_date,
               invoice_currency,
               invoice_status
        FROM invoices
        ORDER BY invoice_id
        """
    ).fetchall()
    actual_invoice_ids = {str(row[0]) for row in invoice_rows}
    if actual_invoice_ids != EXPECTED_INVOICE_IDS:
        raise RuntimeError(f"Unexpected invoice IDs: {actual_invoice_ids}")

    actual_invoice_numbers = {
        str(invoice_id): str(invoice_number)
        for invoice_id, invoice_number, *_ in invoice_rows
    }
    if actual_invoice_numbers != EXPECTED_INVOICE_NUMBERS:
        raise RuntimeError(
            f"Unexpected invoice numbers: {actual_invoice_numbers}"
        )

    actual_header_details = {
        str(invoice_id): (
            str(vendor_id),
            str(invoice_date),
            str(invoice_received_date),
            str(posting_date),
            str(invoice_currency),
            str(invoice_status),
        )
        for (
            invoice_id,
            _,
            vendor_id,
            invoice_date,
            invoice_received_date,
            posting_date,
            invoice_currency,
            invoice_status,
        ) in invoice_rows
    }
    if actual_header_details != EXPECTED_INVOICE_HEADER_DETAILS:
        raise RuntimeError(
            f"Unexpected invoice header details: {actual_header_details}"
        )

    item_rows = connection.execute(
        """
        SELECT invoice_item_id, invoice_id, invoice_item_number, po_item_id
        FROM invoice_items
        ORDER BY invoice_item_id
        """
    ).fetchall()
    actual_invoice_item_ids = {str(row[0]) for row in item_rows}
    if actual_invoice_item_ids != EXPECTED_INVOICE_ITEM_IDS:
        raise RuntimeError(
            f"Unexpected invoice item IDs: {actual_invoice_item_ids}"
        )

    actual_references = {
        str(invoice_item_id): (
            str(invoice_id),
            int(invoice_item_number),
            str(po_item_id),
        )
        for invoice_item_id, invoice_id, invoice_item_number, po_item_id in item_rows
    }
    if actual_references != EXPECTED_INVOICE_ITEM_REFERENCES:
        raise RuntimeError(
            f"Unexpected invoice item references: {actual_references}"
        )


def validate_invoice_amounts_and_chronology(
    connection: sqlite3.Connection,
) -> None:
    invalid_item_amounts = connection.execute(
        f"""
        SELECT invoice_item_id,
               invoiced_quantity,
               invoiced_unit_price,
               invoiced_amount
        FROM invoice_items
        WHERE ABS(
            invoiced_amount
            - ROUND(invoiced_quantity * invoiced_unit_price, 2)
        ) > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(invalid_item_amounts, "Invalid invoice item amount arithmetic")

    invalid_header_totals = connection.execute(
        f"""
        SELECT invoice.invoice_id,
               invoice.invoice_total_amount,
               ROUND(COALESCE(SUM(item.invoiced_amount), 0), 2) AS item_total
        FROM invoices AS invoice
        LEFT JOIN invoice_items AS item
            ON item.invoice_id = invoice.invoice_id
        GROUP BY invoice.invoice_id, invoice.invoice_total_amount
        HAVING ABS(
            invoice.invoice_total_amount
            - ROUND(COALESCE(SUM(item.invoiced_amount), 0), 2)
        ) > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(invalid_header_totals, "Invalid invoice header total arithmetic")

    zero_item_headers = connection.execute(
        """
        SELECT invoice.invoice_id
        FROM invoices AS invoice
        LEFT JOIN invoice_items AS item
            ON item.invoice_id = invoice.invoice_id
        GROUP BY invoice.invoice_id
        HAVING COUNT(item.invoice_item_id) = 0
        """
    ).fetchall()
    raise_if_rows(zero_item_headers, "Invoices with no items")

    invalid_dates = connection.execute(
        """
        SELECT invoice_id,
               invoice_date,
               invoice_received_date,
               posting_date
        FROM invoices
        WHERE invoice_received_date < invoice_date
            OR (
                posting_date IS NOT NULL
                AND posting_date < invoice_received_date
            )
        """
    ).fetchall()
    raise_if_rows(invalid_dates, "Invalid invoice date chronology")


def validate_invoice_po_consistency(connection: sqlite3.Connection) -> None:
    vendor_or_currency_violations = connection.execute(
        """
        SELECT invoice.invoice_id,
               invoice.vendor_id,
               po.vendor_id,
               invoice.invoice_currency,
               po.document_currency
        FROM invoice_items AS item
        JOIN invoices AS invoice
            ON invoice.invoice_id = item.invoice_id
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = item.po_item_id
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE invoice.vendor_id <> po.vendor_id
            OR invoice.invoice_currency <> po.document_currency
        """
    ).fetchall()
    raise_if_rows(
        vendor_or_currency_violations,
        "Invoice vendor or currency does not match purchase order",
    )

    lifecycle_violations = connection.execute(
        """
        SELECT invoice.invoice_id,
               po.po_id,
               po.po_lifecycle_status,
               poi.po_item_id,
               poi.po_item_lifecycle_status
        FROM invoice_items AS item
        JOIN invoices AS invoice
            ON invoice.invoice_id = item.invoice_id
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = item.po_item_id
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE po.po_lifecycle_status <> 'active'
            OR poi.po_item_lifecycle_status <> 'active'
        """
    ).fetchall()
    raise_if_rows(lifecycle_violations, "Invoice references non-active PO data")

    overordered_rows = connection.execute(
        f"""
        SELECT item.invoice_item_id,
               item.invoiced_quantity,
               poi.ordered_quantity
        FROM invoice_items AS item
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = item.po_item_id
        WHERE item.invoiced_quantity - poi.ordered_quantity > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(overordered_rows, "Invoice quantity exceeds ordered quantity")


def validate_invoice_item_matching(connection: sqlite3.Connection) -> None:
    eligible_invoice_item_count = connection.execute(
        """
        SELECT COUNT(*)
        FROM invoice_items AS item
        JOIN invoices AS invoice
            ON invoice.invoice_id = item.invoice_id
        WHERE invoice.invoice_status <> 'cancelled'
        """
    ).fetchone()[0]
    matching_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_invoice_item_three_way_match"
    ).fetchone()[0]
    if (
        matching_view_count != eligible_invoice_item_count
        or matching_view_count != 5
    ):
        raise RuntimeError(
            "Unexpected vw_invoice_item_three_way_match row count: "
            f"view={matching_view_count}, "
            f"eligible_items={eligible_invoice_item_count}"
        )

    cutoff_violations = connection.execute(
        f"""
        WITH expected_receipt_quantities AS (
            SELECT
                match.invoice_item_id,
                match.eligible_posted_accepted_quantity,
                COALESCE(SUM(gr.accepted_quantity), 0)
                    AS expected_eligible_quantity
            FROM vw_invoice_item_three_way_match AS match
            LEFT JOIN goods_receipts AS gr
                ON gr.po_item_id = match.po_item_id
                AND gr.receipt_status = 'posted'
                AND gr.receipt_date <= match.invoice_received_date
            GROUP BY
                match.invoice_item_id,
                match.eligible_posted_accepted_quantity
        )
        SELECT invoice_item_id,
               eligible_posted_accepted_quantity,
               expected_eligible_quantity
        FROM expected_receipt_quantities
        WHERE ABS(
            eligible_posted_accepted_quantity - expected_eligible_quantity
        ) > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(
        cutoff_violations,
        "Eligible accepted quantity ignores invoice-received-date cutoff",
    )

    with validation_savepoint(connection, "invoice_cutoff_validation"):
        connection.execute(
            """
            INSERT INTO goods_receipts (
                goods_receipt_id,
                po_item_id,
                receipt_number,
                receipt_date,
                received_quantity,
                accepted_quantity,
                rejected_quantity,
                receipt_status
            )
            VALUES (
                'GR-CUTOFF-TEST',
                'POI-014',
                '5999999999',
                '2026-03-10',
                150,
                150,
                0,
                'posted'
            )
            """
        )
        cutoff_test_result = connection.execute(
            """
            SELECT eligible_posted_accepted_quantity, matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = 'INVI-005'
            """
        ).fetchone()
        if cutoff_test_result != (0, "missing goods receipt"):
            raise RuntimeError(
                "A later goods receipt retroactively changed invoice matching: "
                f"{cutoff_test_result}"
            )

    expected_quantities = {
        "INVI-001": (1000.0, 1000.0, 0.0),
        "INVI-002": (420.0, 420.0, 0.0),
        "INVI-003": (12.0, 12.0, 0.0),
        "INVI-004": (38.0, 40.0, 2.0),
        "INVI-005": (0.0, 150.0, 150.0),
    }
    matching_rows = connection.execute(
        """
        SELECT match.invoice_item_id,
               match.eligible_posted_accepted_quantity,
               match.cumulative_non_cancelled_invoiced_quantity,
               match.quantity_variance,
               match.price_variance,
               match.monetary_price_variance_impact,
               match.matching_status,
               item.invoiced_quantity,
               item.invoiced_unit_price,
               poi.unit_price
        FROM vw_invoice_item_three_way_match AS match
        JOIN invoice_items AS item
            ON item.invoice_item_id = match.invoice_item_id
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = item.po_item_id
        ORDER BY match.invoice_item_id
        """
    ).fetchall()
    actual_statuses = {}
    for (
        invoice_item_id,
        eligible_quantity,
        cumulative_invoiced_quantity,
        quantity_variance,
        price_variance,
        monetary_price_variance_impact,
        matching_status,
        invoiced_quantity,
        invoiced_unit_price,
        po_unit_price,
    ) in matching_rows:
        item_id = str(invoice_item_id)
        actual_statuses[item_id] = str(matching_status)
        expected_eligible, expected_cumulative, expected_variance = (
            expected_quantities[item_id]
        )
        quantity_values = (
            (float(eligible_quantity), expected_eligible),
            (float(cumulative_invoiced_quantity), expected_cumulative),
            (float(quantity_variance), expected_variance),
        )
        if any(
            abs(actual_value - expected_value) > FLOAT_TOLERANCE
            for actual_value, expected_value in quantity_values
        ):
            raise RuntimeError(
                f"Unexpected invoice matching quantities for {item_id}: "
                f"eligible={eligible_quantity}, "
                f"cumulative={cumulative_invoiced_quantity}, "
                f"variance={quantity_variance}"
            )

        expected_price_variance, expected_impact = connection.execute(
            """
            SELECT
                ROUND(? - ?, 2),
                ROUND(ROUND(? - ?, 2) * ?, 2)
            """,
            (
                invoiced_unit_price,
                po_unit_price,
                invoiced_unit_price,
                po_unit_price,
                invoiced_quantity,
            ),
        ).fetchone()
        price_values = (
            (float(price_variance), float(expected_price_variance)),
            (float(monetary_price_variance_impact), float(expected_impact)),
        )
        if any(
            abs(actual_value - expected_value) > FLOAT_TOLERANCE
            for actual_value, expected_value in price_values
        ):
            raise RuntimeError(
                f"Unexpected price matching values for {item_id}: "
                f"price_variance={price_variance}, "
                f"impact={monetary_price_variance_impact}"
            )

    if actual_statuses != EXPECTED_INVOICE_MATCHING_STATUSES:
        raise RuntimeError(
            f"Unexpected invoice matching statuses: {actual_statuses}"
        )

    price_scenario = connection.execute(
        """
        SELECT quantity_variance,
               price_variance,
               invoiced_unit_price,
               matching_status
        FROM vw_invoice_item_three_way_match
        WHERE invoice_item_id = 'INVI-003'
        """
    ).fetchone()
    if (
        price_scenario is None
        or abs(float(price_scenario[0])) > FLOAT_TOLERANCE
        or abs(float(price_scenario[1]) - 2.12) > FLOAT_TOLERANCE
        or abs(float(price_scenario[2]) - 44.55) > FLOAT_TOLERANCE
        or price_scenario[3] != "price mismatch"
    ):
        raise RuntimeError(f"Unexpected price mismatch scenario: {price_scenario}")

    quantity_scenario = connection.execute(
        """
        SELECT match.quantity_variance,
               match.price_variance,
               match.matching_status,
               SUM(gr.received_quantity) AS received_quantity,
               SUM(gr.accepted_quantity) AS accepted_quantity
        FROM vw_invoice_item_three_way_match AS match
        JOIN goods_receipts AS gr
            ON gr.po_item_id = match.po_item_id
            AND gr.receipt_status = 'posted'
            AND gr.receipt_date <= match.invoice_received_date
        WHERE match.invoice_item_id = 'INVI-004'
        GROUP BY match.invoice_item_id,
                 match.quantity_variance,
                 match.price_variance,
                 match.matching_status
        """
    ).fetchone()
    expected_quantity_scenario = (2.0, 0.0, "quantity mismatch", 40.0, 38.0)
    if quantity_scenario != expected_quantity_scenario:
        raise RuntimeError(
            f"Unexpected quantity mismatch scenario: {quantity_scenario}"
        )

    missing_receipt_scenario = connection.execute(
        """
        SELECT eligible_posted_accepted_quantity,
               price_variance,
               matching_status
        FROM vw_invoice_item_three_way_match
        WHERE invoice_item_id = 'INVI-005'
        """
    ).fetchone()
    expected_missing_receipt = (0, 0.0, "missing goods receipt")
    if missing_receipt_scenario != expected_missing_receipt:
        raise RuntimeError(
            "Unexpected missing-goods-receipt scenario: "
            f"{missing_receipt_scenario}"
        )


def insert_validation_invoice(
    connection: sqlite3.Connection,
    invoice_id: str,
    po_item_id: str,
    invoice_received_date: str,
    invoiced_quantity: float | None,
    *,
    unit_price_adjustment: float = 0.0,
    invoice_status: str = "posted",
    blocked_flag: int = 0,
    block_reason: str | None = None,
) -> str | None:
    vendor_id, invoice_currency, po_unit_price = connection.execute(
        """
        SELECT po.vendor_id, po.document_currency, poi.unit_price
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE poi.po_item_id = ?
        """,
        (po_item_id,),
    ).fetchone()

    invoice_item_id = (
        f"INVI-{invoice_id.removeprefix('INV-')}"
        if invoiced_quantity is not None
        else None
    )
    invoiced_unit_price = round(
        float(po_unit_price) + unit_price_adjustment,
        2,
    )
    invoiced_amount = (
        connection.execute(
            "SELECT ROUND(? * ?, 2)",
            (invoiced_quantity, invoiced_unit_price),
        ).fetchone()[0]
        if invoiced_quantity is not None
        else 0.0
    )
    connection.execute(
        """
        INSERT INTO invoices (
            invoice_id,
            vendor_id,
            invoice_number,
            invoice_date,
            invoice_received_date,
            posting_date,
            invoice_currency,
            invoice_total_amount,
            invoice_status,
            blocked_flag,
            block_reason
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            invoice_id,
            vendor_id,
            f"VAL-{invoice_id}",
            invoice_received_date,
            invoice_received_date,
            invoice_received_date,
            invoice_currency,
            invoiced_amount,
            invoice_status,
            blocked_flag,
            block_reason,
        ),
    )
    if invoice_item_id is not None:
        connection.execute(
            """
            INSERT INTO invoice_items (
                invoice_item_id,
                invoice_id,
                invoice_item_number,
                po_item_id,
                invoiced_quantity,
                invoiced_unit_price,
                invoiced_amount
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                invoice_item_id,
                invoice_id,
                ITEM_NUMBER_STEP,
                po_item_id,
                invoiced_quantity,
                invoiced_unit_price,
                invoiced_amount,
            ),
        )
    return invoice_item_id


def validate_invoice_matching_adversarial_cases(
    connection: sqlite3.Connection,
) -> None:
    with validation_savepoint(connection, "multiple_invoice_validation"):
        first_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-CUM-1",
            "POI-007",
            "2026-03-03",
            70.0,
        )
        second_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-CUM-2",
            "POI-007",
            "2026-03-04",
            50.0,
        )
        cumulative_rows = connection.execute(
            """
            SELECT invoice_item_id,
                   cumulative_non_cancelled_invoiced_quantity,
                   quantity_variance,
                   matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id IN (?, ?)
            ORDER BY invoice_received_date,
                     invoice_id,
                     invoice_item_number,
                     invoice_item_id
            """,
            (first_item_id, second_item_id),
        ).fetchall()
        expected_cumulative_rows = [
            (first_item_id, 70.0, -50.0, "matched"),
            (second_item_id, 120.0, 0.0, "matched"),
        ]
        if cumulative_rows != expected_cumulative_rows:
            raise RuntimeError(
                "Cumulative multi-invoice validation failed: "
                f"{cumulative_rows}"
            )

    with validation_savepoint(connection, "cancelled_invoice_validation"):
        cancelled_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-CANCELLED",
            "POI-007",
            "2026-03-03",
            90.0,
            invoice_status="cancelled",
            blocked_flag=1,
            block_reason="cancelled invoice excluded",
        )
        active_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-AFTER-CANCEL",
            "POI-007",
            "2026-03-04",
            120.0,
        )
        cancelled_view_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = ?
            """,
            (cancelled_item_id,),
        ).fetchone()[0]
        active_result = connection.execute(
            """
            SELECT cumulative_non_cancelled_invoiced_quantity,
                   matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = ?
            """,
            (active_item_id,),
        ).fetchone()
        cancelled_summary = connection.execute(
            """
            SELECT total_item_count,
                   matched_item_count,
                   exception_item_count,
                   invoice_matching_status
            FROM vw_invoice_matching_summary
            WHERE invoice_id = 'INV-VAL-CANCELLED'
            """
        ).fetchone()
        eligible_test_item_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM vw_invoice_item_three_way_match
            WHERE invoice_id IN (
                'INV-VAL-CANCELLED',
                'INV-VAL-AFTER-CANCEL'
            )
            """
        ).fetchone()[0]
        eligible_blocked_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM vw_invoice_matching_summary
            WHERE invoice_id IN (
                'INV-VAL-CANCELLED',
                'INV-VAL-AFTER-CANCEL'
            )
                AND blocked_flag = 1
                AND invoice_matching_status IN ('matched', 'exception')
            """
        ).fetchone()[0]
        if (
            cancelled_view_count != 0
            or active_result != (120.0, "matched")
            or cancelled_summary != (0, 0, 0, "excluded")
            or eligible_test_item_count != 1
            or eligible_blocked_count != 0
        ):
            raise RuntimeError(
                "Cancelled-invoice exclusion validation failed: "
                f"cancelled_view_count={cancelled_view_count}, "
                f"active_result={active_result}, "
                f"summary={cancelled_summary}, "
                f"eligible_items={eligible_test_item_count}, "
                f"eligible_blocked={eligible_blocked_count}"
            )

    with validation_savepoint(connection, "ordered_quantity_validation"):
        connection.execute(
            """
            INSERT INTO goods_receipts (
                goods_receipt_id,
                po_item_id,
                receipt_number,
                receipt_date,
                received_quantity,
                accepted_quantity,
                rejected_quantity,
                receipt_status
            )
            VALUES (
                'GR-VAL-OVER-RECEIPT',
                'POI-007',
                '5999999998',
                '2026-03-03',
                20,
                20,
                0,
                'posted'
            )
            """
        )
        overordered_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-OVER-ORDER",
            "POI-007",
            "2026-03-04",
            130.0,
            blocked_flag=1,
            block_reason="quantity mismatch",
        )
        overordered_result = connection.execute(
            """
            SELECT eligible_posted_accepted_quantity,
                   cumulative_non_cancelled_invoiced_quantity,
                   ordered_quantity,
                   quantity_variance,
                   matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = ?
            """,
            (overordered_item_id,),
        ).fetchone()
        if overordered_result != (
            140.0,
            130.0,
            120.0,
            -10.0,
            "quantity mismatch",
        ):
            raise RuntimeError(
                "Ordered-quantity ceiling validation failed: "
                f"{overordered_result}"
            )

    with validation_savepoint(connection, "combined_mismatch_validation"):
        combined_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-COMBINED",
            "POI-007",
            "2026-03-03",
            130.0,
            unit_price_adjustment=1.0,
            blocked_flag=1,
            block_reason="quantity and price mismatch",
        )
        combined_status = connection.execute(
            """
            SELECT matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = ?
            """,
            (combined_item_id,),
        ).fetchone()
        if combined_status != ("quantity and price mismatch",):
            raise RuntimeError(
                "Combined mismatch validation failed: "
                f"{combined_status}"
            )

    with validation_savepoint(connection, "missing_receipt_validation"):
        missing_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-MISSING",
            "POI-006",
            "2026-03-03",
            1.0,
            unit_price_adjustment=1.0,
            blocked_flag=1,
            block_reason="missing goods receipt",
        )
        missing_result = connection.execute(
            """
            SELECT eligible_posted_accepted_quantity,
                   price_variance,
                   matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = ?
            """,
            (missing_item_id,),
        ).fetchone()
        if missing_result != (0, 1.0, "missing goods receipt"):
            raise RuntimeError(
                "Missing-receipt precedence validation failed: "
                f"{missing_result}"
            )

    with validation_savepoint(connection, "negative_variance_validation"):
        negative_item_id = insert_validation_invoice(
            connection,
            "INV-VAL-NEGATIVE",
            "POI-003",
            "2026-02-27",
            400.0,
        )
        negative_result = connection.execute(
            """
            SELECT quantity_variance, matching_status
            FROM vw_invoice_item_three_way_match
            WHERE invoice_item_id = ?
            """,
            (negative_item_id,),
        ).fetchone()
        if negative_result != (-100.0, "matched"):
            raise RuntimeError(
                "Negative quantity variance validation failed: "
                f"{negative_result}"
            )

    with validation_savepoint(connection, "zero_item_invoice_validation"):
        insert_validation_invoice(
            connection,
            "INV-VAL-ZERO",
            "POI-007",
            "2026-03-03",
            None,
        )
        zero_item_summary = connection.execute(
            """
            SELECT total_item_count,
                   matched_item_count,
                   exception_item_count,
                   invoice_matching_status
            FROM vw_invoice_matching_summary
            WHERE invoice_id = 'INV-VAL-ZERO'
            """
        ).fetchone()
        if zero_item_summary != (0, 0, 0, "invalid"):
            raise RuntimeError(
                "Zero-item invoice validation failed: "
                f"{zero_item_summary}"
            )

    final_counts = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM invoices),
            (SELECT COUNT(*) FROM invoice_items)
        """
    ).fetchone()
    temporary_row_count = connection.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM invoices
             WHERE invoice_id LIKE 'INV-VAL-%')
            + (SELECT COUNT(*) FROM invoice_items
               WHERE invoice_item_id LIKE 'INVI-VAL-%')
            + (SELECT COUNT(*) FROM goods_receipts
               WHERE goods_receipt_id LIKE 'GR-VAL-%')
        """
    ).fetchone()[0]
    if final_counts != (4, 5) or temporary_row_count != 0:
        raise RuntimeError(
            "Adversarial invoice validations changed the final dataset: "
            f"counts={final_counts}, temporary_rows={temporary_row_count}"
        )


def validate_invoice_matching_summary(connection: sqlite3.Connection) -> None:
    summary_rows = connection.execute(
        """
        SELECT invoice_id,
               total_item_count,
               matched_item_count,
               exception_item_count,
               invoice_matching_status
        FROM vw_invoice_matching_summary
        ORDER BY invoice_id
        """
    ).fetchall()
    expected_summary_rows = [
        ("INV-001", 2, 2, 0, "matched"),
        ("INV-002", 1, 0, 1, "exception"),
        ("INV-003", 1, 0, 1, "exception"),
        ("INV-004", 1, 0, 1, "exception"),
    ]
    if summary_rows != expected_summary_rows:
        raise RuntimeError(
            f"Unexpected invoice matching summary rows: {summary_rows}"
        )

    actual_blocking = {
        str(invoice_id): (int(blocked_flag), block_reason)
        for invoice_id, blocked_flag, block_reason in connection.execute(
            """
            SELECT invoice_id, blocked_flag, block_reason
            FROM invoices
            ORDER BY invoice_id
            """
        ).fetchall()
    }
    if actual_blocking != EXPECTED_INVOICE_BLOCKING:
        raise RuntimeError(f"Unexpected invoice blocking map: {actual_blocking}")

    blocking_violations = connection.execute(
        """
        SELECT summary.invoice_id,
               summary.exception_item_count,
               summary.invoice_matching_status,
               invoice.blocked_flag,
               invoice.block_reason
        FROM vw_invoice_matching_summary AS summary
        JOIN invoices AS invoice
            ON invoice.invoice_id = summary.invoice_id
        WHERE (
            summary.invoice_matching_status = 'matched'
            AND (
                invoice.blocked_flag <> 0
                OR invoice.block_reason IS NOT NULL
            )
        )
        OR (
            summary.invoice_matching_status = 'exception'
            AND (
                invoice.blocked_flag <> 1
                OR invoice.block_reason IS NULL
                OR length(trim(invoice.block_reason)) = 0
            )
        )
        """
    ).fetchall()
    raise_if_rows(
        blocking_violations,
        "Invoice blocking does not agree with matching results",
    )


def validate_phase4_rules(connection: sqlite3.Connection) -> None:
    validate_item_number_sequences(
        connection,
        "invoice_items",
        "invoice_id",
        "invoice_item_number",
    )
    validate_invoice_identifiers_and_references(connection)
    validate_invoice_amounts_and_chronology(connection)
    validate_invoice_po_consistency(connection)
    validate_invoice_item_matching(connection)
    validate_invoice_matching_summary(connection)
    validate_invoice_matching_adversarial_cases(connection)
