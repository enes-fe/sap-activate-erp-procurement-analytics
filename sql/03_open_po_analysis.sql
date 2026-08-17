-- Business question:
-- Which active PO items remain open or partially fulfilled as of 2026-03-31,
-- how overdue are they, and what PO commitment value remains?
--
-- `open_quantity` comes from `vw_po_item_fulfillment`, so rejected and
-- under-review quantities do not close a PO item. Quantities are summarized by
-- base unit of measure. TRY and EUR remaining commitments stay separate.

-- Result set 1: open/partial backlog by currency and unit of measure.
WITH parameters AS (
    SELECT '2026-03-31' AS reporting_date
),
open_po_items AS (
    SELECT
        po.document_currency,
        fulfillment.po_id,
        fulfillment.po_item_id,
        fulfillment.fulfillment_status,
        fulfillment.open_quantity,
        material.base_unit_of_measure,
        poi.unit_price,
        poi.planned_delivery_date,
        ROUND(fulfillment.open_quantity * poi.unit_price, 2)
            AS remaining_commitment_value,
        parameter.reporting_date
    FROM vw_po_item_fulfillment AS fulfillment
    JOIN purchase_orders AS po
        ON po.po_id = fulfillment.po_id
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = fulfillment.po_item_id
    JOIN materials AS material
        ON material.material_id = poi.material_id
    CROSS JOIN parameters AS parameter
    WHERE po.po_lifecycle_status = 'active'
        AND poi.po_item_lifecycle_status = 'active'
        AND fulfillment.fulfillment_status IN ('open', 'partial')
)
SELECT
    document_currency,
    base_unit_of_measure,
    COUNT(DISTINCT po_id) AS active_po_header_count,
    COUNT(*) AS open_partial_item_count,
    SUM(CASE WHEN fulfillment_status = 'open' THEN 1 ELSE 0 END)
        AS open_item_count,
    SUM(CASE WHEN fulfillment_status = 'partial' THEN 1 ELSE 0 END)
        AS partial_item_count,
    SUM(open_quantity) AS open_quantity,
    ROUND(SUM(remaining_commitment_value), 2)
        AS remaining_commitment_value,
    SUM(
        CASE
            WHEN planned_delivery_date < reporting_date THEN 1
            ELSE 0
        END
    ) AS overdue_item_count
FROM open_po_items
GROUP BY document_currency, base_unit_of_measure
ORDER BY document_currency, base_unit_of_measure;

-- Result set 2: item-level backlog ordered by commitment within currency.
WITH parameters AS (
    SELECT '2026-03-31' AS reporting_date
),
open_po_items AS (
    SELECT
        po.document_currency,
        po.po_id,
        po.po_number,
        vendor.vendor_id,
        vendor.vendor_name,
        fulfillment.po_item_id,
        fulfillment.po_item_number,
        material.material_name,
        material.base_unit_of_measure,
        fulfillment.fulfillment_status,
        fulfillment.ordered_quantity,
        fulfillment.total_accepted_quantity,
        fulfillment.open_quantity,
        poi.unit_price,
        ROUND(fulfillment.open_quantity * poi.unit_price, 2)
            AS remaining_commitment_value,
        poi.planned_delivery_date,
        CAST(
            julianday(parameter.reporting_date)
            - julianday(poi.planned_delivery_date)
            AS INTEGER
        ) AS days_from_planned_date
    FROM vw_po_item_fulfillment AS fulfillment
    JOIN purchase_orders AS po
        ON po.po_id = fulfillment.po_id
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = fulfillment.po_item_id
    JOIN vendors AS vendor
        ON vendor.vendor_id = po.vendor_id
    JOIN materials AS material
        ON material.material_id = poi.material_id
    CROSS JOIN parameters AS parameter
    WHERE po.po_lifecycle_status = 'active'
        AND poi.po_item_lifecycle_status = 'active'
        AND fulfillment.fulfillment_status IN ('open', 'partial')
)
SELECT
    document_currency,
    po_id,
    po_number,
    vendor_id,
    vendor_name,
    po_item_id,
    po_item_number,
    material_name,
    base_unit_of_measure,
    fulfillment_status,
    ordered_quantity,
    total_accepted_quantity,
    open_quantity,
    unit_price,
    remaining_commitment_value,
    planned_delivery_date,
    days_from_planned_date,
    CASE
        WHEN days_from_planned_date > 0 THEN 'overdue'
        WHEN days_from_planned_date = 0 THEN 'due today'
        ELSE 'not yet due'
    END AS due_status,
    ROW_NUMBER() OVER (
        PARTITION BY document_currency
        ORDER BY remaining_commitment_value DESC, po_item_id
    ) AS currency_backlog_rank
FROM open_po_items
ORDER BY document_currency, currency_backlog_rank;

-- FINAL HEADLINE: compact Seed-42 validation result.
-- Remaining commitment values are returned in separate currency columns.
WITH open_po_items AS (
    SELECT
        po.document_currency,
        fulfillment.po_id,
        fulfillment.po_item_id,
        ROUND(fulfillment.open_quantity * poi.unit_price, 2)
            AS remaining_commitment_value
    FROM vw_po_item_fulfillment AS fulfillment
    JOIN purchase_orders AS po
        ON po.po_id = fulfillment.po_id
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = fulfillment.po_item_id
    WHERE po.po_lifecycle_status = 'active'
        AND poi.po_item_lifecycle_status = 'active'
        AND fulfillment.fulfillment_status IN ('open', 'partial')
)
SELECT
    COUNT(DISTINCT po_id) AS active_po_headers_with_open_partial_items,
    COUNT(*) AS open_partial_item_count,
    ROUND(
        SUM(
            CASE
                WHEN document_currency = 'TRY'
                THEN remaining_commitment_value
                ELSE 0
            END
        ),
        2
    ) AS try_remaining_commitment,
    ROUND(
        SUM(
            CASE
                WHEN document_currency = 'EUR'
                THEN remaining_commitment_value
                ELSE 0
            END
        ),
        2
    ) AS eur_remaining_commitment
FROM open_po_items;
