PRAGMA foreign_keys = ON;

DROP VIEW IF EXISTS vw_invoice_payment_progress;
DROP VIEW IF EXISTS vw_invoice_matching_summary;
DROP VIEW IF EXISTS vw_invoice_item_three_way_match;
DROP VIEW IF EXISTS vw_po_item_delivery_performance;
DROP VIEW IF EXISTS vw_po_fulfillment;
DROP VIEW IF EXISTS vw_po_item_fulfillment;

DROP TABLE IF EXISTS data_quality_issues;
DROP TABLE IF EXISTS change_requests;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS invoice_items;
DROP TABLE IF EXISTS invoices;
DROP TABLE IF EXISTS goods_receipts;
DROP TABLE IF EXISTS purchase_order_items;
DROP TABLE IF EXISTS purchase_orders;
DROP TABLE IF EXISTS purchase_requisition_items;
DROP TABLE IF EXISTS purchase_requisitions;
DROP TABLE IF EXISTS materials;
DROP TABLE IF EXISTS material_groups;
DROP TABLE IF EXISTS purchasing_groups;
DROP TABLE IF EXISTS plants;
DROP TABLE IF EXISTS vendors;
DROP TABLE IF EXISTS sap_activate_project_tasks;

CREATE TABLE vendors (
    vendor_id TEXT PRIMARY KEY,
    vendor_name TEXT NOT NULL,
    country TEXT NOT NULL,
    vendor_category TEXT NOT NULL,
    payment_terms TEXT NOT NULL,
    preferred_vendor_flag INTEGER NOT NULL DEFAULT 0
        CHECK (preferred_vendor_flag IN (0, 1)),
    vendor_status TEXT NOT NULL
        CHECK (vendor_status IN ('active', 'inactive', 'blocked', 'pending review')),
    created_date TEXT NOT NULL
        CHECK (created_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]')
);

CREATE TABLE plants (
    plant_id TEXT PRIMARY KEY,
    plant_name TEXT NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    plant_type TEXT NOT NULL
        CHECK (plant_type IN ('manufacturing', 'distribution', 'service', 'office')),
    plant_status TEXT NOT NULL
        CHECK (plant_status IN ('active', 'inactive', 'planned'))
);

CREATE TABLE purchasing_groups (
    purchasing_group_id TEXT PRIMARY KEY,
    purchasing_group_name TEXT NOT NULL,
    manager_name TEXT,
    process_area TEXT NOT NULL
        CHECK (process_area IN ('direct materials', 'indirect materials', 'services', 'mro')),
    status TEXT NOT NULL
        CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE material_groups (
    material_group_id TEXT PRIMARY KEY,
    material_group_name TEXT NOT NULL,
    category_owner TEXT,
    spend_category TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (status IN ('active', 'inactive'))
);

CREATE TABLE materials (
    material_id TEXT PRIMARY KEY,
    material_group_id TEXT NOT NULL,
    material_name TEXT NOT NULL,
    base_unit_of_measure TEXT NOT NULL,
    material_type TEXT NOT NULL
        CHECK (material_type IN ('raw material', 'spare part', 'packaging', 'service', 'consumable')),
    standard_price REAL
        CHECK (standard_price IS NULL OR standard_price >= 0),
    material_status TEXT NOT NULL
        CHECK (material_status IN ('active', 'inactive', 'blocked', 'under review')),
    FOREIGN KEY (material_group_id)
        REFERENCES material_groups (material_group_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE purchase_requisitions (
    pr_id TEXT PRIMARY KEY,
    plant_id TEXT NOT NULL,
    requester_name TEXT NOT NULL,
    requisition_date TEXT NOT NULL
        CHECK (requisition_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    approval_date TEXT
        CHECK (approval_date IS NULL OR approval_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    pr_status TEXT NOT NULL
        CHECK (pr_status IN ('draft', 'submitted', 'approved', 'rejected', 'converted', 'cancelled')),
    business_reason TEXT,
    FOREIGN KEY (plant_id)
        REFERENCES plants (plant_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE purchase_requisition_items (
    pr_item_id TEXT PRIMARY KEY,
    pr_id TEXT NOT NULL,
    pr_item_number INTEGER NOT NULL
        CHECK (pr_item_number > 0),
    material_id TEXT NOT NULL,
    requested_quantity REAL NOT NULL
        CHECK (requested_quantity > 0),
    requested_unit_price REAL NOT NULL
        CHECK (requested_unit_price >= 0),
    requested_delivery_date TEXT NOT NULL
        CHECK (requested_delivery_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    pr_item_status TEXT NOT NULL
        CHECK (pr_item_status IN ('open', 'approved', 'converted', 'rejected', 'cancelled', 'partially converted')),
    UNIQUE (pr_id, pr_item_number),
    FOREIGN KEY (pr_id)
        REFERENCES purchase_requisitions (pr_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (material_id)
        REFERENCES materials (material_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE purchase_orders (
    po_id TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    plant_id TEXT NOT NULL,
    purchasing_group_id TEXT NOT NULL,
    po_number TEXT NOT NULL UNIQUE,
    po_created_date TEXT NOT NULL
        CHECK (po_created_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    po_approval_date TEXT
        CHECK (po_approval_date IS NULL OR po_approval_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    document_currency TEXT NOT NULL
        CHECK (length(document_currency) = 3),
    po_lifecycle_status TEXT NOT NULL
        CHECK (po_lifecycle_status IN ('active', 'blocked', 'cancelled', 'closed')),
    FOREIGN KEY (vendor_id)
        REFERENCES vendors (vendor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (plant_id)
        REFERENCES plants (plant_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (purchasing_group_id)
        REFERENCES purchasing_groups (purchasing_group_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE purchase_order_items (
    po_item_id TEXT PRIMARY KEY,
    po_id TEXT NOT NULL,
    material_id TEXT NOT NULL,
    pr_item_id TEXT,
    po_item_number INTEGER NOT NULL
        CHECK (po_item_number > 0),
    ordered_quantity REAL NOT NULL
        CHECK (ordered_quantity > 0),
    unit_price REAL NOT NULL
        CHECK (unit_price >= 0),
    net_value REAL NOT NULL
        CHECK (net_value >= 0),
    planned_delivery_date TEXT NOT NULL
        CHECK (planned_delivery_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    po_item_lifecycle_status TEXT NOT NULL
        CHECK (po_item_lifecycle_status IN ('active', 'cancelled', 'closed')),
    UNIQUE (po_id, po_item_number),
    FOREIGN KEY (po_id)
        REFERENCES purchase_orders (po_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (material_id)
        REFERENCES materials (material_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (pr_item_id)
        REFERENCES purchase_requisition_items (pr_item_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE TABLE goods_receipts (
    goods_receipt_id TEXT PRIMARY KEY,
    po_item_id TEXT NOT NULL,
    receipt_number TEXT NOT NULL UNIQUE,
    receipt_date TEXT NOT NULL
        CHECK (receipt_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    received_quantity REAL NOT NULL
        CHECK (received_quantity > 0),
    accepted_quantity REAL NOT NULL DEFAULT 0
        CHECK (accepted_quantity >= 0),
    rejected_quantity REAL NOT NULL DEFAULT 0
        CHECK (rejected_quantity >= 0),
    receipt_status TEXT NOT NULL
        CHECK (receipt_status IN ('posted', 'under review', 'reversed')),
    CHECK (
        (
            receipt_status IN ('posted', 'reversed')
            AND ABS(received_quantity - accepted_quantity - rejected_quantity) < 0.000001
        )
        OR (
            receipt_status = 'under review'
            AND accepted_quantity = 0
            AND rejected_quantity = 0
        )
    ),
    FOREIGN KEY (po_item_id)
        REFERENCES purchase_order_items (po_item_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE invoices (
    invoice_id TEXT PRIMARY KEY,
    vendor_id TEXT NOT NULL,
    invoice_number TEXT NOT NULL,
    invoice_date TEXT NOT NULL
        CHECK (invoice_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    invoice_received_date TEXT NOT NULL
        CHECK (invoice_received_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    posting_date TEXT
        CHECK (posting_date IS NULL OR posting_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    invoice_currency TEXT NOT NULL
        CHECK (length(invoice_currency) = 3),
    invoice_total_amount REAL NOT NULL
        CHECK (invoice_total_amount >= 0),
    invoice_status TEXT NOT NULL
        CHECK (invoice_status IN ('received', 'posted', 'approved', 'disputed', 'cancelled')),
    blocked_flag INTEGER NOT NULL DEFAULT 0
        CHECK (blocked_flag IN (0, 1)),
    block_reason TEXT,
    CHECK (invoice_received_date >= invoice_date),
    CHECK (posting_date IS NULL OR posting_date >= invoice_received_date),
    CHECK (
        (blocked_flag = 0 AND block_reason IS NULL)
        OR (
            blocked_flag = 1
            AND block_reason IS NOT NULL
            AND length(trim(block_reason)) > 0
        )
    ),
    UNIQUE (vendor_id, invoice_number),
    FOREIGN KEY (vendor_id)
        REFERENCES vendors (vendor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE invoice_items (
    invoice_item_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    invoice_item_number INTEGER NOT NULL
        CHECK (invoice_item_number > 0),
    po_item_id TEXT NOT NULL,
    invoiced_quantity REAL NOT NULL
        CHECK (invoiced_quantity > 0),
    invoiced_unit_price REAL NOT NULL
        CHECK (invoiced_unit_price >= 0),
    invoiced_amount REAL NOT NULL
        CHECK (invoiced_amount >= 0),
    CHECK (
        ABS(
            invoiced_amount
            - ROUND(invoiced_quantity * invoiced_unit_price, 2)
        ) < 0.000001
    ),
    UNIQUE (invoice_id, invoice_item_number),
    FOREIGN KEY (invoice_id)
        REFERENCES invoices (invoice_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (po_item_id)
        REFERENCES purchase_order_items (po_item_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE payments (
    payment_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    payment_status_date TEXT NOT NULL
        CHECK (payment_status_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    payment_date TEXT
        CHECK (payment_date IS NULL OR payment_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    payment_amount REAL NOT NULL
        CHECK (payment_amount > 0),
    payment_method TEXT NOT NULL
        CHECK (payment_method IN ('bank transfer', 'check', 'card', 'other')),
    payment_status TEXT NOT NULL
        CHECK (payment_status IN ('scheduled', 'paid', 'failed', 'cancelled', 'on hold')),
    clearing_reference TEXT UNIQUE,
    CHECK (
        ABS(payment_amount - ROUND(payment_amount, 2)) < 0.000001
    ),
    CHECK (
        (
            payment_status = 'paid'
            AND payment_date IS NOT NULL
            AND payment_status_date = payment_date
            AND clearing_reference IS NOT NULL
            AND length(trim(clearing_reference)) > 0
        )
        OR (
            payment_status <> 'paid'
            AND payment_date IS NULL
            AND clearing_reference IS NULL
        )
    ),
    FOREIGN KEY (invoice_id)
        REFERENCES invoices (invoice_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE sap_activate_project_tasks (
    task_id TEXT PRIMARY KEY,
    activate_phase TEXT NOT NULL
        CHECK (activate_phase IN ('discover', 'prepare', 'explore', 'realize', 'deploy', 'run')),
    workstream TEXT NOT NULL,
    task_name TEXT NOT NULL,
    task_owner TEXT,
    planned_start_date TEXT NOT NULL
        CHECK (planned_start_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    planned_finish_date TEXT NOT NULL
        CHECK (planned_finish_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    actual_finish_date TEXT
        CHECK (actual_finish_date IS NULL OR actual_finish_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    task_status TEXT NOT NULL
        CHECK (task_status IN ('not started', 'in progress', 'blocked', 'completed', 'delayed', 'cancelled')),
    readiness_weight REAL NOT NULL DEFAULT 1.0
        CHECK (readiness_weight >= 0),
    completion_percent REAL NOT NULL DEFAULT 0
        CHECK (completion_percent >= 0 AND completion_percent <= 100),
    critical_flag INTEGER NOT NULL DEFAULT 0
        CHECK (critical_flag IN (0, 1))
);

CREATE TABLE change_requests (
    change_request_id TEXT PRIMARY KEY,
    related_task_id TEXT,
    activate_phase TEXT NOT NULL
        CHECK (activate_phase IN ('discover', 'prepare', 'explore', 'realize', 'deploy', 'run')),
    change_title TEXT NOT NULL,
    change_type TEXT NOT NULL
        CHECK (change_type IN ('scope', 'requirement', 'process', 'data', 'reporting', 'integration', 'training')),
    priority TEXT NOT NULL
        CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status TEXT NOT NULL
        CHECK (status IN ('submitted', 'under review', 'approved', 'rejected', 'deferred', 'implemented', 'cancelled')),
    requested_date TEXT NOT NULL
        CHECK (requested_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    decision_date TEXT
        CHECK (decision_date IS NULL OR decision_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    business_impact TEXT,
    FOREIGN KEY (related_task_id)
        REFERENCES sap_activate_project_tasks (task_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE TABLE data_quality_issues (
    data_quality_issue_id TEXT PRIMARY KEY,
    related_task_id TEXT,
    affected_entity_type TEXT NOT NULL,
    affected_entity_id TEXT,
    issue_category TEXT NOT NULL
        CHECK (issue_category IN ('missing value', 'duplicate', 'invalid reference', 'inconsistent status', 'pricing issue', 'migration mapping issue')),
    severity TEXT NOT NULL
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    issue_status TEXT NOT NULL
        CHECK (issue_status IN ('open', 'in progress', 'resolved', 'accepted risk', 'cancelled')),
    detected_date TEXT NOT NULL
        CHECK (detected_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    resolved_date TEXT
        CHECK (resolved_date IS NULL OR resolved_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    migration_relevant_flag INTEGER NOT NULL DEFAULT 1
        CHECK (migration_relevant_flag IN (0, 1)),
    readiness_impact_score REAL NOT NULL DEFAULT 0
        CHECK (readiness_impact_score >= 0),
    FOREIGN KEY (related_task_id)
        REFERENCES sap_activate_project_tasks (task_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL
);

CREATE VIEW vw_po_item_fulfillment AS
WITH receipt_totals AS (
    SELECT
        po_item_id,
        SUM(
            CASE
                WHEN receipt_status <> 'reversed' THEN received_quantity
                ELSE 0
            END
        ) AS total_received_quantity,
        SUM(
            CASE
                WHEN receipt_status = 'posted' THEN accepted_quantity
                ELSE 0
            END
        ) AS total_accepted_quantity,
        SUM(
            CASE
                WHEN receipt_status = 'posted' THEN rejected_quantity
                ELSE 0
            END
        ) AS total_rejected_quantity,
        SUM(
            CASE
                WHEN receipt_status = 'under review' THEN received_quantity
                ELSE 0
            END
        ) AS total_under_review_quantity
    FROM goods_receipts
    GROUP BY po_item_id
),
item_totals AS (
    SELECT
        poi.po_item_id,
        po.po_id,
        poi.po_item_number,
        po.po_lifecycle_status,
        poi.po_item_lifecycle_status,
        poi.ordered_quantity,
        COALESCE(rt.total_received_quantity, 0) AS total_received_quantity,
        COALESCE(rt.total_accepted_quantity, 0) AS total_accepted_quantity,
        COALESCE(rt.total_rejected_quantity, 0) AS total_rejected_quantity,
        COALESCE(rt.total_under_review_quantity, 0) AS total_under_review_quantity
    FROM purchase_order_items AS poi
    JOIN purchase_orders AS po
        ON po.po_id = poi.po_id
    LEFT JOIN receipt_totals AS rt
        ON rt.po_item_id = poi.po_item_id
)
SELECT
    po_item_id,
    po_id,
    po_item_number,
    po_lifecycle_status,
    po_item_lifecycle_status,
    ordered_quantity,
    total_received_quantity,
    total_accepted_quantity,
    total_rejected_quantity,
    total_under_review_quantity,
    MAX(ordered_quantity - total_accepted_quantity, 0) AS open_quantity,
    CASE
        WHEN po_lifecycle_status <> 'active'
            OR po_item_lifecycle_status <> 'active'
        THEN NULL
        WHEN total_accepted_quantity = 0 THEN 'open'
        WHEN total_accepted_quantity < ordered_quantity THEN 'partial'
        ELSE 'complete'
    END AS fulfillment_status
FROM item_totals;

CREATE VIEW vw_po_item_delivery_performance AS
WITH posted_receipt_progress AS (
    SELECT
        gr.po_item_id,
        gr.receipt_date,
        gr.receipt_number,
        gr.goods_receipt_id,
        SUM(gr.accepted_quantity) OVER (
            PARTITION BY gr.po_item_id
            ORDER BY gr.receipt_date, gr.receipt_number, gr.goods_receipt_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_accepted_quantity
    FROM goods_receipts AS gr
    WHERE gr.receipt_status = 'posted'
),
fulfillment_dates AS (
    SELECT
        progress.po_item_id,
        MIN(progress.receipt_date) AS fulfillment_date
    FROM posted_receipt_progress AS progress
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = progress.po_item_id
    WHERE progress.cumulative_accepted_quantity >= poi.ordered_quantity
    GROUP BY progress.po_item_id
)
SELECT
    item.po_item_id,
    item.po_id,
    po.po_number,
    po.vendor_id,
    item.po_item_number,
    item.po_lifecycle_status,
    item.po_item_lifecycle_status,
    poi.planned_delivery_date,
    item.ordered_quantity,
    item.total_accepted_quantity,
    item.open_quantity,
    item.fulfillment_status,
    dates.fulfillment_date,
    CASE
        WHEN item.po_lifecycle_status <> 'active'
            OR item.po_item_lifecycle_status <> 'active'
        THEN NULL
        WHEN dates.fulfillment_date IS NULL THEN 'not fulfilled'
        WHEN dates.fulfillment_date <= poi.planned_delivery_date THEN 'on time in full'
        ELSE 'late in full'
    END AS delivery_performance_status
FROM vw_po_item_fulfillment AS item
JOIN purchase_order_items AS poi
    ON poi.po_item_id = item.po_item_id
JOIN purchase_orders AS po
    ON po.po_id = item.po_id
LEFT JOIN fulfillment_dates AS dates
    ON dates.po_item_id = item.po_item_id;

CREATE VIEW vw_po_fulfillment AS
WITH item_counts AS (
    SELECT
        po.po_id,
        po.po_number,
        po.po_lifecycle_status,
        SUM(
            CASE
                WHEN item.po_item_lifecycle_status = 'active' THEN 1
                ELSE 0
            END
        ) AS active_item_count,
        SUM(
            CASE
                WHEN item.po_item_lifecycle_status = 'active'
                    AND item.fulfillment_status = 'open'
                THEN 1
                ELSE 0
            END
        ) AS open_item_count,
        SUM(
            CASE
                WHEN item.po_item_lifecycle_status = 'active'
                    AND item.fulfillment_status = 'partial'
                THEN 1
                ELSE 0
            END
        ) AS partial_item_count,
        SUM(
            CASE
                WHEN item.po_item_lifecycle_status = 'active'
                    AND item.fulfillment_status = 'complete'
                THEN 1
                ELSE 0
            END
        ) AS complete_item_count
    FROM purchase_orders AS po
    LEFT JOIN vw_po_item_fulfillment AS item
        ON item.po_id = po.po_id
    GROUP BY po.po_id, po.po_number, po.po_lifecycle_status
)
SELECT
    po_id,
    po_number,
    po_lifecycle_status,
    active_item_count,
    open_item_count,
    partial_item_count,
    complete_item_count,
    CASE
        WHEN po_lifecycle_status IN ('blocked', 'cancelled') THEN NULL
        WHEN po_lifecycle_status <> 'active' THEN NULL
        WHEN active_item_count = 0 THEN NULL
        WHEN open_item_count = active_item_count THEN 'open'
        WHEN complete_item_count = active_item_count THEN 'complete'
        WHEN partial_item_count + complete_item_count > 0 THEN 'partial'
        ELSE NULL
    END AS fulfillment_status
FROM item_counts;

CREATE VIEW vw_invoice_item_three_way_match AS
WITH invoice_line_base AS (
    SELECT
        ii.invoice_item_id,
        ii.invoice_id,
        ii.invoice_item_number,
        invoice.vendor_id,
        invoice.invoice_number,
        invoice.invoice_date,
        invoice.invoice_received_date,
        invoice.posting_date,
        invoice.invoice_currency,
        invoice.invoice_total_amount,
        invoice.invoice_status,
        invoice.blocked_flag,
        invoice.block_reason,
        ii.po_item_id,
        poi.po_id,
        po.po_number,
        po.vendor_id AS po_vendor_id,
        po.document_currency AS po_currency,
        po.po_lifecycle_status,
        poi.po_item_number,
        poi.po_item_lifecycle_status,
        poi.ordered_quantity,
        poi.unit_price AS po_unit_price,
        ii.invoiced_quantity,
        ii.invoiced_unit_price,
        ii.invoiced_amount,
        COALESCE(
            (
                SELECT SUM(gr.accepted_quantity)
                FROM goods_receipts AS gr
                WHERE gr.po_item_id = ii.po_item_id
                    AND gr.receipt_status = 'posted'
                    AND gr.receipt_date <= invoice.invoice_received_date
            ),
            0
        ) AS eligible_posted_accepted_quantity
    FROM invoice_items AS ii
    JOIN invoices AS invoice
        ON invoice.invoice_id = ii.invoice_id
    JOIN purchase_order_items AS poi
        ON poi.po_item_id = ii.po_item_id
    JOIN purchase_orders AS po
        ON po.po_id = poi.po_id
    WHERE invoice.invoice_status <> 'cancelled'
),
cumulative_invoice_quantities AS (
    SELECT
        line.*,
        SUM(line.invoiced_quantity) OVER (
            PARTITION BY line.po_item_id
            ORDER BY
                line.invoice_received_date,
                line.invoice_id,
                line.invoice_item_number,
                line.invoice_item_id
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS cumulative_non_cancelled_invoiced_quantity
    FROM invoice_line_base AS line
),
variance_values AS (
    SELECT
        cumulative.*,
        (
            cumulative.cumulative_non_cancelled_invoiced_quantity
            - cumulative.eligible_posted_accepted_quantity
        ) AS quantity_variance,
        ROUND(
            cumulative.invoiced_unit_price - cumulative.po_unit_price,
            2
        ) AS price_variance
    FROM cumulative_invoice_quantities AS cumulative
)
SELECT
    variance.*,
    ROUND(
        variance.price_variance * variance.invoiced_quantity,
        2
    ) AS monetary_price_variance_impact,
    CASE
        WHEN variance.eligible_posted_accepted_quantity <= 0.000001
        THEN 'missing goods receipt'
        WHEN (
            variance.cumulative_non_cancelled_invoiced_quantity
                - variance.eligible_posted_accepted_quantity > 0.000001
            OR variance.cumulative_non_cancelled_invoiced_quantity
                - variance.ordered_quantity > 0.000001
        )
            AND ABS(variance.price_variance) > 0
        THEN 'quantity and price mismatch'
        WHEN variance.cumulative_non_cancelled_invoiced_quantity
                - variance.eligible_posted_accepted_quantity > 0.000001
            OR variance.cumulative_non_cancelled_invoiced_quantity
                - variance.ordered_quantity > 0.000001
        THEN 'quantity mismatch'
        WHEN ABS(variance.price_variance) > 0
        THEN 'price mismatch'
        ELSE 'matched'
    END AS matching_status
FROM variance_values AS variance;

CREATE VIEW vw_invoice_matching_summary AS
WITH invoice_item_counts AS (
    SELECT
        invoice.invoice_id,
        invoice.vendor_id,
        invoice.invoice_date,
        invoice.invoice_currency,
        invoice.invoice_total_amount,
        invoice.invoice_status,
        invoice.blocked_flag,
        COUNT(match.invoice_item_id) AS total_item_count,
        SUM(
            CASE
                WHEN match.matching_status = 'matched' THEN 1
                ELSE 0
            END
        ) AS matched_item_count,
        SUM(
            CASE
                WHEN match.invoice_item_id IS NOT NULL
                    AND match.matching_status <> 'matched'
                THEN 1
                ELSE 0
            END
        ) AS exception_item_count
    FROM invoices AS invoice
    LEFT JOIN vw_invoice_item_three_way_match AS match
        ON match.invoice_id = invoice.invoice_id
    GROUP BY
        invoice.invoice_id,
        invoice.vendor_id,
        invoice.invoice_date,
        invoice.invoice_currency,
        invoice.invoice_total_amount,
        invoice.invoice_status,
        invoice.blocked_flag
)
SELECT
    invoice_id,
    vendor_id,
    invoice_date,
    invoice_currency,
    invoice_total_amount,
    invoice_status,
    blocked_flag,
    total_item_count,
    matched_item_count,
    exception_item_count,
    CASE
        WHEN invoice_status = 'cancelled' THEN 'excluded'
        WHEN total_item_count = 0 THEN 'invalid'
        WHEN exception_item_count = 0 THEN 'matched'
        ELSE 'exception'
    END AS invoice_matching_status
FROM invoice_item_counts;

CREATE VIEW vw_invoice_payment_progress AS
WITH successful_payment_totals AS (
    SELECT
        payment.invoice_id,
        ROUND(
            SUM(
                CASE
                    WHEN payment.payment_status = 'paid'
                    THEN payment.payment_amount
                    ELSE 0
                END
            ),
            2
        ) AS successful_paid_amount,
        SUM(
            CASE
                WHEN payment.payment_status = 'paid' THEN 1
                ELSE 0
            END
        ) AS successful_payment_count,
        MAX(
            CASE
                WHEN payment.payment_status = 'paid'
                THEN payment.payment_date
                ELSE NULL
            END
        ) AS latest_successful_payment_date
    FROM payments AS payment
    GROUP BY payment.invoice_id
),
invoice_payment_base AS (
    SELECT
        invoice.invoice_id,
        invoice.vendor_id,
        invoice.invoice_currency,
        invoice.invoice_total_amount,
        invoice.invoice_status,
        invoice.blocked_flag,
        matching.invoice_matching_status,
        CASE
            WHEN invoice.invoice_status IN ('posted', 'approved')
                AND invoice.blocked_flag = 0
                AND matching.invoice_matching_status = 'matched'
                AND ROUND(
                    invoice.invoice_total_amount
                    - COALESCE(payment.successful_paid_amount, 0),
                    2
                ) > 0.000001
            THEN 1
            ELSE 0
        END AS eligible_for_payment_flag,
        COALESCE(payment.successful_paid_amount, 0)
            AS successful_paid_amount,
        COALESCE(payment.successful_payment_count, 0)
            AS successful_payment_count,
        payment.latest_successful_payment_date
    FROM invoices AS invoice
    JOIN vw_invoice_matching_summary AS matching
        ON matching.invoice_id = invoice.invoice_id
    LEFT JOIN successful_payment_totals AS payment
        ON payment.invoice_id = invoice.invoice_id
)
SELECT
    invoice_id,
    vendor_id,
    invoice_currency,
    invoice_total_amount,
    invoice_status,
    blocked_flag,
    invoice_matching_status,
    eligible_for_payment_flag,
    successful_paid_amount,
    CASE
        WHEN invoice_matching_status IN ('excluded', 'invalid') THEN NULL
        ELSE ROUND(
            MAX(invoice_total_amount - successful_paid_amount, 0),
            2
        )
    END AS outstanding_amount,
    successful_payment_count,
    latest_successful_payment_date,
    CASE
        WHEN invoice_matching_status IN ('excluded', 'invalid') THEN NULL
        WHEN successful_paid_amount <= 0.000001 THEN 'unpaid'
        WHEN successful_paid_amount < invoice_total_amount - 0.000001
        THEN 'partially paid'
        ELSE 'paid'
    END AS payment_progress_status
FROM invoice_payment_base;
