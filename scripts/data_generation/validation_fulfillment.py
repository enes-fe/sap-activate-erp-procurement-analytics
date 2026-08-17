"""Validate goods receipt, fulfillment, delivery, and OTIF behavior."""

from __future__ import annotations

import sqlite3

from .config import FLOAT_TOLERANCE, ITEM_NUMBER_STEP, REPORTING_DATE
from .expected_results import (
    EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES,
    EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES,
    EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES,
    EXPECTED_GOODS_RECEIPT_IDS,
    EXPECTED_ITEM_FULFILLMENT_REFERENCES,
    EXPECTED_LATE_RECEIPT_DELAYS,
    EXPECTED_ON_TIME_RECEIPT_IDS,
    EXPECTED_OTIF_REFERENCES,
    EXPECTED_PO_FULFILLMENT_STATUSES,
    EXPECTED_RECEIPT_NUMBERS,
)
from .validation_common import raise_if_rows


def po_item_reference_set(
    rows: list[tuple[object, ...]],
) -> set[tuple[str, int]]:
    return {(str(po_id), int(po_item_number)) for po_id, po_item_number, *_ in rows}


def validate_goods_receipt_identifiers(connection: sqlite3.Connection) -> None:
    row_count, id_count, receipt_number_count = connection.execute(
        """
        SELECT COUNT(*),
               COUNT(DISTINCT goods_receipt_id),
               COUNT(DISTINCT receipt_number)
        FROM goods_receipts
        """
    ).fetchone()
    if row_count != 10:
        raise RuntimeError(f"Expected 10 goods receipt rows, found {row_count}")
    if id_count != row_count:
        raise RuntimeError("Goods receipt IDs are not unique")
    if receipt_number_count != row_count:
        raise RuntimeError("Goods receipt numbers are not unique")

    actual_ids = {
        str(goods_receipt_id)
        for (goods_receipt_id,) in connection.execute(
            "SELECT goods_receipt_id FROM goods_receipts"
        ).fetchall()
    }
    if actual_ids != EXPECTED_GOODS_RECEIPT_IDS:
        raise RuntimeError(f"Unexpected goods receipt ID set: {actual_ids}")

    actual_receipt_numbers = {
        str(receipt_number)
        for (receipt_number,) in connection.execute(
            "SELECT receipt_number FROM goods_receipts"
        ).fetchall()
    }
    if actual_receipt_numbers != EXPECTED_RECEIPT_NUMBERS:
        raise RuntimeError(
            f"Unexpected goods receipt number set: {actual_receipt_numbers}"
        )

    invalid_reference_rows = connection.execute(
        """
        SELECT gr.goods_receipt_id, gr.po_item_id
        FROM goods_receipts AS gr
        LEFT JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        WHERE poi.po_item_id IS NULL
        """
    ).fetchall()
    raise_if_rows(invalid_reference_rows, "Goods receipts with invalid PO item links")


def validate_goods_receipt_quantities(connection: sqlite3.Connection) -> None:
    invalid_quantity_rows = connection.execute(
        f"""
        SELECT goods_receipt_id,
               received_quantity,
               accepted_quantity,
               rejected_quantity,
               receipt_status
        FROM goods_receipts
        WHERE received_quantity <= 0
            OR accepted_quantity < 0
            OR rejected_quantity < 0
            OR ABS(received_quantity - accepted_quantity - rejected_quantity)
                > {FLOAT_TOLERANCE}
            OR receipt_status <> 'posted'
        """
    ).fetchall()
    raise_if_rows(invalid_quantity_rows, "Invalid goods receipt quantity rows")

    totals = connection.execute(
        """
        SELECT COALESCE(SUM(received_quantity), 0),
               COALESCE(SUM(accepted_quantity), 0),
               COALESCE(SUM(rejected_quantity), 0),
               COALESCE(
                   SUM(
                       CASE
                           WHEN receipt_status = 'under review' THEN received_quantity
                           ELSE 0
                       END
                   ),
                   0
               )
        FROM goods_receipts
        """
    ).fetchone()
    expected_totals = (3043.0, 3041.0, 2.0, 0.0)
    if any(
        abs(float(actual) - expected) > FLOAT_TOLERANCE
        for actual, expected in zip(totals, expected_totals)
    ):
        raise RuntimeError(
            "Unexpected goods receipt aggregate quantities: "
            f"actual={totals}, expected={expected_totals}"
        )


def validate_goods_receipt_chronology(connection: sqlite3.Connection) -> None:
    chronology_rows = connection.execute(
        """
        SELECT gr.goods_receipt_id,
               po.po_id,
               gr.receipt_date,
               po.po_created_date,
               po.po_approval_date
        FROM goods_receipts AS gr
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE po.po_approval_date IS NULL
            OR gr.receipt_date < po.po_created_date
            OR gr.receipt_date < po.po_approval_date
        """
    ).fetchall()
    raise_if_rows(chronology_rows, "Goods receipt chronology violations")


def validate_goods_receipt_lifecycle_eligibility(
    connection: sqlite3.Connection,
) -> None:
    ineligible_rows = connection.execute(
        """
        SELECT gr.goods_receipt_id,
               po.po_id,
               po.po_lifecycle_status,
               poi.po_item_number,
               poi.po_item_lifecycle_status
        FROM goods_receipts AS gr
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        WHERE po.po_lifecycle_status IN ('blocked', 'cancelled', 'closed')
            OR poi.po_item_lifecycle_status IN ('cancelled', 'closed')
        """
    ).fetchall()
    raise_if_rows(ineligible_rows, "Goods receipt lifecycle eligibility violations")


def validate_goods_receipt_scenarios(connection: sqlite3.Connection) -> None:
    expected_rows = [
        ("GR-001", "5000001001", "PO-001", 10, "2026-02-21", 1000.0, 1000.0, 0.0, "posted"),
        ("GR-002", "5000001002", "PO-001", 20, "2026-02-24", 200.0, 200.0, 0.0, "posted"),
        ("GR-003", "5000001003", "PO-001", 20, "2026-02-27", 220.0, 220.0, 0.0, "posted"),
        ("GR-004", "5000001004", "PO-002", 10, "2026-02-26", 500.0, 500.0, 0.0, "posted"),
        ("GR-005", "5000001005", "PO-002", 20, "2026-02-28", 40.0, 38.0, 2.0, "posted"),
        ("GR-006", "5000001006", "PO-003", 10, "2026-02-26", 12.0, 12.0, 0.0, "posted"),
        ("GR-007", "5000001007", "PO-003", 30, "2026-03-02", 120.0, 120.0, 0.0, "posted"),
        ("GR-008", "5000001008", "PO-004", 10, "2026-03-05", 650.0, 650.0, 0.0, "posted"),
        ("GR-009", "5000001009", "PO-004", 30, "2026-03-06", 300.0, 300.0, 0.0, "posted"),
        ("GR-010", "5000001010", "PO-006", 10, "2026-03-09", 1.0, 1.0, 0.0, "posted"),
    ]
    actual_rows = [
        (
            str(goods_receipt_id),
            str(receipt_number),
            str(po_id),
            int(po_item_number),
            str(receipt_date),
            float(received_quantity),
            float(accepted_quantity),
            float(rejected_quantity),
            str(receipt_status),
        )
        for (
            goods_receipt_id,
            receipt_number,
            po_id,
            po_item_number,
            receipt_date,
            received_quantity,
            accepted_quantity,
            rejected_quantity,
            receipt_status,
        ) in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   gr.receipt_number,
                   po.po_id,
                   poi.po_item_number,
                   gr.receipt_date,
                   gr.received_quantity,
                   gr.accepted_quantity,
                   gr.rejected_quantity,
                   gr.receipt_status
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    if actual_rows != expected_rows:
        raise RuntimeError(
            "Unexpected goods receipt scenario rows: "
            f"actual={actual_rows}, expected={expected_rows}"
        )

    receipt_references = po_item_reference_set(
        connection.execute(
            """
            SELECT DISTINCT po.po_id, poi.po_item_number
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            """
        ).fetchall()
    )
    forbidden_references = (
        EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES
        | EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES
        | EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES
    )
    unexpected_receipt_references = receipt_references & forbidden_references
    if unexpected_receipt_references:
        raise RuntimeError(
            "No-receipt scenario references have receipts: "
            f"{unexpected_receipt_references}"
        )

    active_no_receipt_rows = po_item_reference_set(
        connection.execute(
            """
            SELECT po.po_id, poi.po_item_number
            FROM purchase_order_items AS poi
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            LEFT JOIN goods_receipts AS gr
                ON gr.po_item_id = poi.po_item_id
            WHERE po.po_lifecycle_status = 'active'
                AND poi.po_item_lifecycle_status = 'active'
            GROUP BY po.po_id, poi.po_item_number
            HAVING COUNT(gr.goods_receipt_id) = 0
            """
        ).fetchall()
    )
    if active_no_receipt_rows != EXPECTED_ACTIVE_NO_RECEIPT_REFERENCES:
        raise RuntimeError(
            "Unexpected active open items with no receipt: "
            f"{active_no_receipt_rows}"
        )

    rejected_rows = [
        (str(goods_receipt_id), str(po_id), int(po_item_number), float(rejected_quantity))
        for goods_receipt_id, po_id, po_item_number, rejected_quantity in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   po.po_id,
                   poi.po_item_number,
                   gr.rejected_quantity
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            WHERE gr.rejected_quantity > 0
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    if rejected_rows != [("GR-005", "PO-002", 20, 2.0)]:
        raise RuntimeError(f"Unexpected rejected-quantity scenarios: {rejected_rows}")

    direct_receipt_rows = [
        (str(goods_receipt_id), str(po_id), int(po_item_number))
        for goods_receipt_id, po_id, po_item_number in connection.execute(
            """
            SELECT gr.goods_receipt_id, po.po_id, poi.po_item_number
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            WHERE poi.pr_item_id IS NULL
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    if direct_receipt_rows != [("GR-010", "PO-006", 10)]:
        raise RuntimeError(f"Unexpected direct-PO receipt rows: {direct_receipt_rows}")

    multiple_receipt_rows = [
        (str(po_id), int(po_item_number), int(receipt_count))
        for po_id, po_item_number, receipt_count in connection.execute(
            """
            SELECT po.po_id,
                   poi.po_item_number,
                   COUNT(gr.goods_receipt_id) AS receipt_count
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            JOIN purchase_orders AS po
                ON po.po_id = poi.po_id
            GROUP BY po.po_id, poi.po_item_number
            HAVING COUNT(gr.goods_receipt_id) > 1
            ORDER BY po.po_id, poi.po_item_number
            """
        ).fetchall()
    ]
    if multiple_receipt_rows != [("PO-001", 20, 2)]:
        raise RuntimeError(
            f"Unexpected multiple goods receipt scenarios: {multiple_receipt_rows}"
        )


def validate_cumulative_receipt_quantities(connection: sqlite3.Connection) -> None:
    overaccepted_rows = connection.execute(
        f"""
        SELECT po.po_id,
               poi.po_item_number,
               poi.ordered_quantity,
               COALESCE(SUM(gr.accepted_quantity), 0) AS total_accepted_quantity
        FROM purchase_order_items AS poi
        JOIN purchase_orders AS po
            ON po.po_id = poi.po_id
        LEFT JOIN goods_receipts AS gr
            ON gr.po_item_id = poi.po_item_id
            AND gr.receipt_status = 'posted'
        GROUP BY po.po_id, poi.po_item_number, poi.ordered_quantity
        HAVING total_accepted_quantity - poi.ordered_quantity > {FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(overaccepted_rows, "PO items with accepted overdelivery")

    negative_open_rows = connection.execute(
        f"""
        SELECT po_id, po_item_number, ordered_quantity, total_accepted_quantity, open_quantity
        FROM vw_po_item_fulfillment
        WHERE open_quantity < -{FLOAT_TOLERANCE}
        """
    ).fetchall()
    raise_if_rows(negative_open_rows, "PO items with negative open quantity")

    rejected_completion_rows = connection.execute(
        """
        SELECT po_id,
               po_item_number,
               ordered_quantity,
               total_received_quantity,
               total_accepted_quantity,
               total_rejected_quantity,
               open_quantity,
               fulfillment_status
        FROM vw_po_item_fulfillment
        WHERE total_rejected_quantity > 0
            AND fulfillment_status = 'complete'
        """
    ).fetchall()
    raise_if_rows(
        rejected_completion_rows,
        "Rejected quantities incorrectly contribute to fulfillment",
    )


def fulfillment_references(
    connection: sqlite3.Connection, status: str | None
) -> set[tuple[str, int]]:
    if status is None:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_fulfillment
            WHERE fulfillment_status IS NULL
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_fulfillment
            WHERE fulfillment_status = ?
            """,
            (status,),
        ).fetchall()
    return po_item_reference_set(rows)


def validate_fulfillment_views(connection: sqlite3.Connection) -> None:
    po_item_count = connection.execute(
        "SELECT COUNT(*) FROM purchase_order_items"
    ).fetchone()[0]
    po_item_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_po_item_fulfillment"
    ).fetchone()[0]
    if po_item_view_count != po_item_count or po_item_view_count != 15:
        raise RuntimeError(
            "Unexpected vw_po_item_fulfillment row count: "
            f"view={po_item_view_count}, purchase_order_items={po_item_count}"
        )

    item_status_counts = {
        fulfillment_status: row_count
        for fulfillment_status, row_count in connection.execute(
            """
            SELECT fulfillment_status, COUNT(*)
            FROM vw_po_item_fulfillment
            GROUP BY fulfillment_status
            """
        ).fetchall()
    }
    expected_item_status_counts = {None: 3, "complete": 7, "partial": 2, "open": 3}
    if item_status_counts != expected_item_status_counts:
        raise RuntimeError(
            "Unexpected vw_po_item_fulfillment status counts: "
            f"{item_status_counts}"
        )

    for status, expected_references in EXPECTED_ITEM_FULFILLMENT_REFERENCES.items():
        actual_references = fulfillment_references(connection, status)
        if actual_references != expected_references:
            raise RuntimeError(
                f"Unexpected item fulfillment references for {status}: "
                f"{actual_references}"
            )

    po_002_item_20 = connection.execute(
        """
        SELECT ordered_quantity,
               total_received_quantity,
               total_accepted_quantity,
               total_rejected_quantity,
               total_under_review_quantity,
               open_quantity,
               fulfillment_status
        FROM vw_po_item_fulfillment
        WHERE po_id = 'PO-002'
            AND po_item_number = 20
        """
    ).fetchone()
    expected_po_002_item_20 = (40.0, 40.0, 38.0, 2.0, 0.0, 2.0, "partial")
    if po_002_item_20 != expected_po_002_item_20:
        raise RuntimeError(
            "Unexpected PO-002 item 20 fulfillment row: "
            f"{po_002_item_20}"
        )

    po_001_item_20 = connection.execute(
        """
        SELECT ordered_quantity,
               total_received_quantity,
               total_accepted_quantity,
               total_rejected_quantity,
               open_quantity,
               fulfillment_status
        FROM vw_po_item_fulfillment
        WHERE po_id = 'PO-001'
            AND po_item_number = 20
        """
    ).fetchone()
    expected_po_001_item_20 = (420.0, 420.0, 420.0, 0.0, 0.0, "complete")
    if po_001_item_20 != expected_po_001_item_20:
        raise RuntimeError(
            "Unexpected PO-001 item 20 fulfillment row: "
            f"{po_001_item_20}"
        )

    po_count = connection.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0]
    po_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_po_fulfillment"
    ).fetchone()[0]
    if po_view_count != po_count or po_view_count != 8:
        raise RuntimeError(
            "Unexpected vw_po_fulfillment row count: "
            f"view={po_view_count}, purchase_orders={po_count}"
        )

    po_statuses = {
        str(po_id): fulfillment_status
        for po_id, fulfillment_status in connection.execute(
            """
            SELECT po_id, fulfillment_status
            FROM vw_po_fulfillment
            ORDER BY po_id
            """
        ).fetchall()
    }
    if po_statuses != EXPECTED_PO_FULFILLMENT_STATUSES:
        raise RuntimeError(f"Unexpected PO fulfillment statuses: {po_statuses}")

    po_status_counts = {
        fulfillment_status: row_count
        for fulfillment_status, row_count in connection.execute(
            """
            SELECT fulfillment_status, COUNT(*)
            FROM vw_po_fulfillment
            GROUP BY fulfillment_status
            """
        ).fetchall()
    }
    expected_po_status_counts = {None: 2, "complete": 2, "partial": 3, "open": 1}
    if po_status_counts != expected_po_status_counts:
        raise RuntimeError(
            "Unexpected vw_po_fulfillment status counts: "
            f"{po_status_counts}"
        )


def delivery_performance_references(
    connection: sqlite3.Connection, status: str | None
) -> set[tuple[str, int]]:
    if status is None:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_delivery_performance
            WHERE delivery_performance_status IS NULL
            """
        ).fetchall()
    else:
        rows = connection.execute(
            """
            SELECT po_id, po_item_number
            FROM vw_po_item_delivery_performance
            WHERE delivery_performance_status = ?
            """,
            (status,),
        ).fetchall()
    return po_item_reference_set(rows)


def validate_delivery_performance(connection: sqlite3.Connection) -> None:
    po_item_count = connection.execute(
        "SELECT COUNT(*) FROM purchase_order_items"
    ).fetchone()[0]
    delivery_view_count = connection.execute(
        "SELECT COUNT(*) FROM vw_po_item_delivery_performance"
    ).fetchone()[0]
    if delivery_view_count != po_item_count or delivery_view_count != 15:
        raise RuntimeError(
            "Unexpected vw_po_item_delivery_performance row count: "
            f"view={delivery_view_count}, purchase_order_items={po_item_count}"
        )

    expected_delivery_references = {
        "on time in full": EXPECTED_OTIF_REFERENCES,
        "late in full": {
            ("PO-001", 2 * ITEM_NUMBER_STEP),
            ("PO-003", 3 * ITEM_NUMBER_STEP),
            ("PO-004", ITEM_NUMBER_STEP),
            ("PO-006", ITEM_NUMBER_STEP),
        },
        "not fulfilled": {
            ("PO-002", ITEM_NUMBER_STEP),
            ("PO-002", 2 * ITEM_NUMBER_STEP),
            ("PO-003", 2 * ITEM_NUMBER_STEP),
            ("PO-004", 2 * ITEM_NUMBER_STEP),
            ("PO-007", ITEM_NUMBER_STEP),
        },
        None: EXPECTED_BLOCKED_NO_RECEIPT_REFERENCES
        | EXPECTED_CANCELLED_NO_RECEIPT_REFERENCES,
    }
    for status, expected_references in expected_delivery_references.items():
        actual_references = delivery_performance_references(connection, status)
        if actual_references != expected_references:
            raise RuntimeError(
                f"Unexpected delivery performance references for {status}: "
                f"{actual_references}"
            )

    eligible_rows = [
        (str(po_id), int(po_item_number), delivery_performance_status)
        for po_id, po_item_number, delivery_performance_status in connection.execute(
            """
            SELECT po_id, po_item_number, delivery_performance_status
            FROM vw_po_item_delivery_performance
            WHERE po_lifecycle_status = 'active'
                AND po_item_lifecycle_status = 'active'
                AND planned_delivery_date <= ?
            ORDER BY po_id, po_item_number
            """,
            (REPORTING_DATE,),
        ).fetchall()
    ]
    otif_references = {
        (po_id, po_item_number)
        for po_id, po_item_number, status in eligible_rows
        if status == "on time in full"
    }
    denominator = len(eligible_rows)
    numerator = len(otif_references)
    otif_rate = numerator / denominator * 100 if denominator else 0.0
    if denominator != 12:
        raise RuntimeError(f"Unexpected OTIF denominator: {denominator}")
    if numerator != 3 or otif_references != EXPECTED_OTIF_REFERENCES:
        raise RuntimeError(
            "Unexpected OTIF numerator references: "
            f"count={numerator}, references={otif_references}"
        )
    if abs(otif_rate - 25.0) > FLOAT_TOLERANCE:
        raise RuntimeError(f"Unexpected OTIF rate: {otif_rate}")

    event_rows = [
        (str(goods_receipt_id), bool(on_time_flag))
        for goods_receipt_id, on_time_flag in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   gr.receipt_date <= poi.planned_delivery_date AS on_time_flag
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    ]
    on_time_events = {
        goods_receipt_id for goods_receipt_id, on_time_flag in event_rows if on_time_flag
    }
    late_events = {
        goods_receipt_id for goods_receipt_id, on_time_flag in event_rows if not on_time_flag
    }
    event_rate = len(on_time_events) / len(event_rows) * 100 if event_rows else 0.0
    if on_time_events != EXPECTED_ON_TIME_RECEIPT_IDS:
        raise RuntimeError(f"Unexpected on-time receipt events: {on_time_events}")
    if late_events != set(EXPECTED_LATE_RECEIPT_DELAYS):
        raise RuntimeError(f"Unexpected late receipt events: {late_events}")
    if len(event_rows) != 10 or len(on_time_events) != 5 or len(late_events) != 5:
        raise RuntimeError(
            "Unexpected receipt-event timing counts: "
            f"total={len(event_rows)}, on_time={len(on_time_events)}, "
            f"late={len(late_events)}"
        )
    if abs(event_rate - 50.0) > FLOAT_TOLERANCE:
        raise RuntimeError(f"Unexpected receipt-event on-time rate: {event_rate}")

    late_delay_rows = {
        str(goods_receipt_id): int(delay_days)
        for goods_receipt_id, delay_days in connection.execute(
            """
            SELECT gr.goods_receipt_id,
                   CAST(
                       julianday(gr.receipt_date) - julianday(poi.planned_delivery_date)
                       AS INTEGER
                   ) AS delay_days
            FROM goods_receipts AS gr
            JOIN purchase_order_items AS poi
                ON poi.po_item_id = gr.po_item_id
            WHERE gr.receipt_date > poi.planned_delivery_date
            ORDER BY gr.goods_receipt_id
            """
        ).fetchall()
    }
    if late_delay_rows != EXPECTED_LATE_RECEIPT_DELAYS:
        raise RuntimeError(f"Unexpected late receipt delays: {late_delay_rows}")

    average_delay = connection.execute(
        """
        SELECT AVG(julianday(gr.receipt_date) - julianday(poi.planned_delivery_date))
        FROM goods_receipts AS gr
        JOIN purchase_order_items AS poi
            ON poi.po_item_id = gr.po_item_id
        WHERE gr.receipt_date > poi.planned_delivery_date
        """
    ).fetchone()[0]
    if abs(float(average_delay) - 2.2) > FLOAT_TOLERANCE:
        raise RuntimeError(f"Unexpected average late receipt delay: {average_delay}")


def validate_phase3_rules(connection: sqlite3.Connection) -> None:
    validate_goods_receipt_identifiers(connection)
    validate_goods_receipt_quantities(connection)
    validate_goods_receipt_chronology(connection)
    validate_goods_receipt_lifecycle_eligibility(connection)
    validate_goods_receipt_scenarios(connection)
    validate_cumulative_receipt_quantities(connection)
    validate_fulfillment_views(connection)
    validate_delivery_performance(connection)
