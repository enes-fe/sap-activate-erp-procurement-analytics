PRAGMA foreign_keys = ON;

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
    po_status TEXT NOT NULL
        CHECK (po_status IN ('open', 'partially received', 'fully received', 'invoiced', 'closed', 'blocked', 'cancelled')),
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
    po_item_status TEXT NOT NULL
        CHECK (po_item_status IN ('open', 'partially received', 'fully received', 'partially invoiced', 'fully invoiced', 'closed', 'cancelled')),
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
        CHECK (receipt_status IN ('posted', 'reversed', 'partial', 'accepted', 'rejected', 'under review')),
    CHECK (accepted_quantity + rejected_quantity <= received_quantity),
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
    invoice_total_amount REAL NOT NULL
        CHECK (invoice_total_amount >= 0),
    invoice_status TEXT NOT NULL
        CHECK (invoice_status IN ('received', 'posted', 'blocked', 'disputed', 'approved', 'paid', 'cancelled')),
    blocked_flag INTEGER NOT NULL DEFAULT 0
        CHECK (blocked_flag IN (0, 1)),
    block_reason TEXT,
    UNIQUE (vendor_id, invoice_number),
    FOREIGN KEY (vendor_id)
        REFERENCES vendors (vendor_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE invoice_items (
    invoice_item_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    po_item_id TEXT NOT NULL,
    invoiced_quantity REAL NOT NULL
        CHECK (invoiced_quantity > 0),
    invoiced_unit_price REAL NOT NULL
        CHECK (invoiced_unit_price >= 0),
    invoiced_amount REAL NOT NULL
        CHECK (invoiced_amount >= 0),
    quantity_variance REAL NOT NULL DEFAULT 0,
    price_variance REAL NOT NULL DEFAULT 0,
    matching_status TEXT NOT NULL
        CHECK (matching_status IN ('matched', 'quantity mismatch', 'price mismatch', 'missing goods receipt', 'blocked', 'under review')),
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
    payment_date TEXT
        CHECK (payment_date IS NULL OR payment_date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    payment_amount REAL NOT NULL
        CHECK (payment_amount > 0),
    payment_method TEXT NOT NULL
        CHECK (payment_method IN ('bank transfer', 'check', 'card', 'other')),
    payment_status TEXT NOT NULL
        CHECK (payment_status IN ('scheduled', 'paid', 'partially paid', 'failed', 'cancelled', 'on hold')),
    clearing_reference TEXT,
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
