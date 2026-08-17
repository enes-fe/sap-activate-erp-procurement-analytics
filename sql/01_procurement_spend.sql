-- Business question:
-- Where is non-cancelled purchase-order commitment value concentrated during
-- the reporting period, and which suppliers and material groups drive it?
--
-- Monetary interpretation:
-- `net_value` is PO commitment value. It is not cash spend or payment activity.
-- TRY and EUR are always grouped or returned in separate columns.
-- Cancelled headers/items are excluded; blocked PO commitment remains visible.

-- Result set 1: currency-level PO commitment profile.
WITH parameters AS (
    SELECT
        '2026-01-01' AS period_start,
        '2026-03-31' AS period_end
),
scoped_po_items AS (
    SELECT
        po.po_id,
        po.document_currency,
        po.po_lifecycle_status,
        poi.po_item_id,
        poi.pr_item_id,
        poi.net_value,
        vendor.preferred_vendor_flag
    FROM purchase_orders AS po
    JOIN purchase_order_items AS poi
        ON poi.po_id = po.po_id
    JOIN vendors AS vendor
        ON vendor.vendor_id = po.vendor_id
    CROSS JOIN parameters AS parameter
    WHERE po.po_created_date BETWEEN parameter.period_start AND parameter.period_end
        AND po.po_lifecycle_status <> 'cancelled'
        AND poi.po_item_lifecycle_status <> 'cancelled'
)
SELECT
    document_currency,
    COUNT(DISTINCT po_id) AS po_count,
    COUNT(*) AS po_item_count,
    ROUND(SUM(net_value), 2) AS po_commitment_value,
    ROUND(
        SUM(
            CASE
                WHEN po_lifecycle_status = 'blocked' THEN net_value
                ELSE 0
            END
        ),
        2
    ) AS blocked_po_commitment_value,
    ROUND(
        SUM(
            CASE
                WHEN preferred_vendor_flag = 1 THEN net_value
                ELSE 0
            END
        ),
        2
    ) AS preferred_vendor_commitment_value,
    ROUND(
        SUM(
            CASE
                WHEN pr_item_id IS NULL THEN net_value
                ELSE 0
            END
        ),
        2
    ) AS direct_po_commitment_value
FROM scoped_po_items
GROUP BY document_currency
ORDER BY document_currency;

-- Result set 2: supplier concentration and rank within each currency.
WITH parameters AS (
    SELECT
        '2026-01-01' AS period_start,
        '2026-03-31' AS period_end
),
supplier_commitment AS (
    SELECT
        po.document_currency,
        vendor.vendor_id,
        vendor.vendor_name,
        vendor.preferred_vendor_flag,
        COUNT(DISTINCT po.po_id) AS po_count,
        COUNT(*) AS po_item_count,
        ROUND(SUM(poi.net_value), 2) AS po_commitment_value
    FROM purchase_orders AS po
    JOIN purchase_order_items AS poi
        ON poi.po_id = po.po_id
    JOIN vendors AS vendor
        ON vendor.vendor_id = po.vendor_id
    CROSS JOIN parameters AS parameter
    WHERE po.po_created_date BETWEEN parameter.period_start AND parameter.period_end
        AND po.po_lifecycle_status <> 'cancelled'
        AND poi.po_item_lifecycle_status <> 'cancelled'
    GROUP BY
        po.document_currency,
        vendor.vendor_id,
        vendor.vendor_name,
        vendor.preferred_vendor_flag
)
SELECT
    document_currency,
    vendor_id,
    vendor_name,
    preferred_vendor_flag,
    po_count,
    po_item_count,
    po_commitment_value,
    ROUND(
        100.0 * po_commitment_value
        / NULLIF(
            SUM(po_commitment_value) OVER (
                PARTITION BY document_currency
            ),
            0
        ),
        1
    ) AS currency_commitment_share_pct,
    DENSE_RANK() OVER (
        PARTITION BY document_currency
        ORDER BY po_commitment_value DESC
    ) AS currency_commitment_rank
FROM supplier_commitment
ORDER BY
    document_currency,
    currency_commitment_rank,
    vendor_id;

-- Result set 3: material-group commitment drivers within each currency.
WITH parameters AS (
    SELECT
        '2026-01-01' AS period_start,
        '2026-03-31' AS period_end
),
material_group_commitment AS (
    SELECT
        po.document_currency,
        material_group.material_group_id,
        material_group.material_group_name,
        material_group.spend_category,
        COUNT(DISTINCT po.po_id) AS po_count,
        COUNT(*) AS po_item_count,
        ROUND(SUM(poi.net_value), 2) AS po_commitment_value
    FROM purchase_orders AS po
    JOIN purchase_order_items AS poi
        ON poi.po_id = po.po_id
    JOIN materials AS material
        ON material.material_id = poi.material_id
    JOIN material_groups AS material_group
        ON material_group.material_group_id = material.material_group_id
    CROSS JOIN parameters AS parameter
    WHERE po.po_created_date BETWEEN parameter.period_start AND parameter.period_end
        AND po.po_lifecycle_status <> 'cancelled'
        AND poi.po_item_lifecycle_status <> 'cancelled'
    GROUP BY
        po.document_currency,
        material_group.material_group_id,
        material_group.material_group_name,
        material_group.spend_category
)
SELECT
    document_currency,
    material_group_id,
    material_group_name,
    spend_category,
    po_count,
    po_item_count,
    po_commitment_value,
    ROUND(
        100.0 * po_commitment_value
        / NULLIF(
            SUM(po_commitment_value) OVER (
                PARTITION BY document_currency
            ),
            0
        ),
        1
    ) AS currency_commitment_share_pct,
    DENSE_RANK() OVER (
        PARTITION BY document_currency
        ORDER BY po_commitment_value DESC
    ) AS currency_commitment_rank
FROM material_group_commitment
ORDER BY
    document_currency,
    currency_commitment_rank,
    material_group_id;

-- FINAL HEADLINE: compact Seed-42 validation result.
-- Currency values remain separate and are never added together.
WITH parameters AS (
    SELECT
        '2026-01-01' AS period_start,
        '2026-03-31' AS period_end
),
scoped_po_items AS (
    SELECT
        po.po_id,
        po.document_currency,
        poi.po_item_id,
        poi.net_value
    FROM purchase_orders AS po
    JOIN purchase_order_items AS poi
        ON poi.po_id = po.po_id
    CROSS JOIN parameters AS parameter
    WHERE po.po_created_date BETWEEN parameter.period_start AND parameter.period_end
        AND po.po_lifecycle_status <> 'cancelled'
        AND poi.po_item_lifecycle_status <> 'cancelled'
)
SELECT
    COUNT(DISTINCT po_id) AS non_cancelled_po_count,
    COUNT(*) AS non_cancelled_po_item_count,
    ROUND(
        SUM(CASE WHEN document_currency = 'TRY' THEN net_value ELSE 0 END),
        2
    ) AS try_commitment_value,
    ROUND(
        SUM(CASE WHEN document_currency = 'EUR' THEN net_value ELSE 0 END),
        2
    ) AS eur_commitment_value
FROM scoped_po_items;
