-- Business question:
-- Which suppliers delivered active, due PO items on time and in full as of the
-- fixed reporting date, and what does receipt-event timing show operationally?
--
-- The primary KPI uses `vw_po_item_delivery_performance`, preserving the
-- existing accepted-quantity fulfillment and split-delivery logic. Receipt
-- event timing is a secondary diagnostic and must not replace item-level OTIF.

-- Result set 1: supplier-level PO-item delivery performance.
WITH parameters AS (
    SELECT '2026-03-31' AS reporting_date
),
eligible_items AS (
    SELECT
        performance.vendor_id,
        vendor.vendor_name,
        performance.po_item_id,
        performance.delivery_performance_status,
        performance.open_quantity,
        performance.planned_delivery_date,
        performance.fulfillment_date
    FROM vw_po_item_delivery_performance AS performance
    JOIN vendors AS vendor
        ON vendor.vendor_id = performance.vendor_id
    CROSS JOIN parameters AS parameter
    WHERE performance.po_lifecycle_status = 'active'
        AND performance.po_item_lifecycle_status = 'active'
        AND performance.planned_delivery_date <= parameter.reporting_date
),
supplier_metrics AS (
    SELECT
        vendor_id,
        vendor_name,
        COUNT(*) AS eligible_due_item_count,
        SUM(
            CASE
                WHEN delivery_performance_status = 'on time in full' THEN 1
                ELSE 0
            END
        ) AS otif_item_count,
        SUM(
            CASE
                WHEN delivery_performance_status = 'late in full' THEN 1
                ELSE 0
            END
        ) AS late_in_full_item_count,
        SUM(
            CASE
                WHEN delivery_performance_status = 'not fulfilled' THEN 1
                ELSE 0
            END
        ) AS not_fulfilled_item_count,
        SUM(open_quantity) AS open_quantity,
        ROUND(
            AVG(
                CASE
                    WHEN delivery_performance_status = 'late in full'
                    THEN julianday(fulfillment_date)
                        - julianday(planned_delivery_date)
                END
            ),
            1
        ) AS average_late_in_full_days
    FROM eligible_items
    GROUP BY vendor_id, vendor_name
)
SELECT
    vendor_id,
    vendor_name,
    eligible_due_item_count,
    otif_item_count,
    late_in_full_item_count,
    not_fulfilled_item_count,
    open_quantity,
    average_late_in_full_days,
    ROUND(
        100.0 * otif_item_count / NULLIF(eligible_due_item_count, 0),
        1
    ) AS supplier_otif_rate_pct,
    ROUND(
        100.0 * SUM(otif_item_count) OVER ()
        / NULLIF(SUM(eligible_due_item_count) OVER (), 0),
        1
    ) AS overall_otif_rate_pct,
    ROW_NUMBER() OVER (
        ORDER BY
            1.0 * otif_item_count / NULLIF(eligible_due_item_count, 0) DESC,
            not_fulfilled_item_count,
            vendor_id
    ) AS supplier_performance_rank
FROM supplier_metrics
ORDER BY supplier_performance_rank;

-- Result set 2: secondary receipt-event timing diagnostic by supplier.
WITH parameters AS (
    SELECT '2026-03-31' AS reporting_date
),
eligible_receipt_events AS (
    SELECT
        po.vendor_id,
        vendor.vendor_name,
        receipt.goods_receipt_id,
        receipt.receipt_date,
        poi.planned_delivery_date
    FROM goods_receipts AS receipt
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = receipt.po_item_id
    JOIN purchase_orders AS po
        ON po.po_id = poi.po_id
    JOIN vendors AS vendor
        ON vendor.vendor_id = po.vendor_id
    CROSS JOIN parameters AS parameter
    WHERE receipt.receipt_status = 'posted'
        AND po.po_lifecycle_status = 'active'
        AND poi.po_item_lifecycle_status = 'active'
        AND poi.planned_delivery_date <= parameter.reporting_date
        AND receipt.receipt_date <= parameter.reporting_date
)
SELECT
    vendor_id,
    vendor_name,
    COUNT(*) AS posted_receipt_event_count,
    SUM(
        CASE
            WHEN receipt_date <= planned_delivery_date THEN 1
            ELSE 0
        END
    ) AS on_time_receipt_event_count,
    ROUND(
        100.0
        * SUM(
            CASE
                WHEN receipt_date <= planned_delivery_date THEN 1
                ELSE 0
            END
        )
        / NULLIF(COUNT(*), 0),
        1
    ) AS receipt_event_on_time_rate_pct,
    ROUND(
        AVG(
            CASE
                WHEN receipt_date > planned_delivery_date
                THEN julianday(receipt_date) - julianday(planned_delivery_date)
            END
        ),
        1
    ) AS average_late_receipt_delay_days
FROM eligible_receipt_events
GROUP BY vendor_id, vendor_name
ORDER BY
    receipt_event_on_time_rate_pct DESC,
    vendor_id;

-- FINAL HEADLINE: compact Seed-42 validation result.
WITH parameters AS (
    SELECT '2026-03-31' AS reporting_date
),
eligible_items AS (
    SELECT performance.delivery_performance_status
    FROM vw_po_item_delivery_performance AS performance
    CROSS JOIN parameters AS parameter
    WHERE performance.po_lifecycle_status = 'active'
        AND performance.po_item_lifecycle_status = 'active'
        AND performance.planned_delivery_date <= parameter.reporting_date
),
eligible_receipt_events AS (
    SELECT
        receipt.receipt_date,
        poi.planned_delivery_date
    FROM goods_receipts AS receipt
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = receipt.po_item_id
    JOIN purchase_orders AS po
        ON po.po_id = poi.po_id
    CROSS JOIN parameters AS parameter
    WHERE receipt.receipt_status = 'posted'
        AND po.po_lifecycle_status = 'active'
        AND poi.po_item_lifecycle_status = 'active'
        AND poi.planned_delivery_date <= parameter.reporting_date
        AND receipt.receipt_date <= parameter.reporting_date
)
SELECT
    (SELECT COUNT(*) FROM eligible_items)
        AS eligible_active_due_po_items,
    (
        SELECT SUM(
            CASE
                WHEN delivery_performance_status = 'on time in full' THEN 1
                ELSE 0
            END
        )
        FROM eligible_items
    ) AS otif_item_count,
    (
        SELECT ROUND(
            100.0
            * SUM(
                CASE
                    WHEN delivery_performance_status = 'on time in full' THEN 1
                    ELSE 0
                END
            )
            / NULLIF(COUNT(*), 0),
            1
        )
        FROM eligible_items
    ) AS po_item_otif_rate_pct,
    (
        SELECT ROUND(
            100.0
            * SUM(
                CASE
                    WHEN receipt_date <= planned_delivery_date THEN 1
                    ELSE 0
                END
            )
            / NULLIF(COUNT(*), 0),
            1
        )
        FROM eligible_receipt_events
    ) AS receipt_event_on_time_rate_pct,
    (
        SELECT ROUND(
            AVG(
                CASE
                    WHEN receipt_date > planned_delivery_date
                    THEN julianday(receipt_date) - julianday(planned_delivery_date)
                END
            ),
            1
        )
        FROM eligible_receipt_events
    ) AS average_late_receipt_delay_days;
