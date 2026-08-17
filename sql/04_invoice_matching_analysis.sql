-- Business question:
-- How often do eligible invoice items fail three-way matching, which exception
-- types cause the failure, and how much invoice value is blocked by currency?
--
-- Matching status and eligible accepted quantity come from the existing
-- matching views. This file reports those results without rebuilding the
-- receipt-at-invoice-date or cumulative-invoice business logic.

-- Result set 1: blocked invoice count and value by invoice currency.
SELECT
    matching.invoice_currency,
    COUNT(*) AS blocked_invoice_count,
    ROUND(SUM(matching.invoice_total_amount), 2) AS blocked_invoice_amount
FROM vw_invoice_matching_summary AS matching
WHERE matching.blocked_flag = 1
    AND matching.invoice_matching_status IN ('matched', 'exception')
GROUP BY matching.invoice_currency
ORDER BY matching.invoice_currency;

-- Result set 2: item-level exception diagnosis.
SELECT
    match.invoice_currency,
    match.invoice_id,
    match.invoice_number,
    match.invoice_item_id,
    vendor.vendor_id,
    vendor.vendor_name,
    match.po_number,
    match.po_item_id,
    material.material_name,
    match.invoiced_quantity,
    match.eligible_posted_accepted_quantity,
    match.quantity_variance,
    match.po_unit_price,
    match.invoiced_unit_price,
    match.price_variance,
    match.monetary_price_variance_impact,
    match.matching_status,
    match.block_reason
FROM vw_invoice_item_three_way_match AS match
JOIN vendors AS vendor
    ON vendor.vendor_id = match.vendor_id
JOIN purchase_order_items AS poi
    ON poi.po_item_id = match.po_item_id
JOIN materials AS material
    ON material.material_id = poi.material_id
WHERE match.matching_status <> 'matched'
ORDER BY
    CASE match.matching_status
        WHEN 'missing goods receipt' THEN 1
        WHEN 'quantity mismatch' THEN 2
        WHEN 'price mismatch' THEN 3
        ELSE 4
    END,
    match.invoice_id,
    match.invoice_item_id;

-- FINAL HEADLINE: compact Seed-42 validation result.
WITH item_metrics AS (
    SELECT
        COUNT(*) AS eligible_invoice_item_count,
        SUM(CASE WHEN matching_status = 'matched' THEN 1 ELSE 0 END)
            AS matched_item_count,
        SUM(CASE WHEN matching_status <> 'matched' THEN 1 ELSE 0 END)
            AS exception_item_count
    FROM vw_invoice_item_three_way_match
),
header_metrics AS (
    SELECT
        SUM(
            CASE
                WHEN blocked_flag = 1
                    AND invoice_matching_status IN ('matched', 'exception')
                THEN 1
                ELSE 0
            END
        ) AS blocked_invoice_count
    FROM vw_invoice_matching_summary
)
SELECT
    item.eligible_invoice_item_count AS eligible_invoice_item_count,
    item.matched_item_count,
    item.exception_item_count,
    ROUND(
        100.0 * item.exception_item_count
        / NULLIF(item.eligible_invoice_item_count, 0),
        1
    ) AS exception_rate_pct,
    header.blocked_invoice_count
FROM item_metrics AS item
CROSS JOIN header_metrics AS header;
