-- Business question:
-- What share of valid posted/approved invoices is fully paid, how much remains
-- outstanding in each currency, and which invoices drive the balance?
--
-- Successful paid amount, outstanding amount, and payment-progress status come
-- from `vw_invoice_payment_progress`. Blocked invoices remain in the KPI
-- denominator. TRY and EUR amounts are never combined.

-- Result set 1: payment progress and amount profile by invoice currency.
WITH valid_invoices AS (
    SELECT *
    FROM vw_invoice_payment_progress
    WHERE invoice_status IN ('posted', 'approved')
        AND invoice_matching_status NOT IN ('excluded', 'invalid')
)
SELECT
    invoice_currency,
    COUNT(*) AS valid_invoice_count,
    SUM(CASE WHEN payment_progress_status = 'paid' THEN 1 ELSE 0 END)
        AS fully_paid_invoice_count,
    SUM(CASE WHEN payment_progress_status = 'partially paid' THEN 1 ELSE 0 END)
        AS partially_paid_invoice_count,
    SUM(CASE WHEN payment_progress_status = 'unpaid' THEN 1 ELSE 0 END)
        AS unpaid_invoice_count,
    SUM(CASE WHEN eligible_for_payment_flag = 1 THEN 1 ELSE 0 END)
        AS currently_payment_eligible_invoice_count,
    ROUND(SUM(invoice_total_amount), 2) AS invoice_amount,
    ROUND(SUM(successful_paid_amount), 2) AS successful_paid_amount,
    ROUND(SUM(outstanding_amount), 2) AS outstanding_amount,
    SUM(successful_payment_count) AS successful_payment_count
FROM valid_invoices
GROUP BY invoice_currency
ORDER BY invoice_currency;

-- Result set 2: invoice-level outstanding balance priority within currency.
WITH valid_invoices AS (
    SELECT *
    FROM vw_invoice_payment_progress
    WHERE invoice_status IN ('posted', 'approved')
        AND invoice_matching_status NOT IN ('excluded', 'invalid')
)
SELECT
    payment.invoice_currency,
    payment.invoice_id,
    vendor.vendor_id,
    vendor.vendor_name,
    payment.invoice_total_amount,
    payment.successful_paid_amount,
    payment.outstanding_amount,
    payment.payment_progress_status,
    payment.invoice_matching_status,
    payment.blocked_flag,
    payment.eligible_for_payment_flag,
    payment.successful_payment_count,
    payment.latest_successful_payment_date,
    ROW_NUMBER() OVER (
        PARTITION BY payment.invoice_currency
        ORDER BY payment.outstanding_amount DESC, payment.invoice_id
    ) AS currency_outstanding_rank
FROM valid_invoices AS payment
JOIN vendors AS vendor
    ON vendor.vendor_id = payment.vendor_id
ORDER BY
    payment.invoice_currency,
    currency_outstanding_rank;

-- FINAL HEADLINE: compact Seed-42 validation result.
WITH valid_invoices AS (
    SELECT *
    FROM vw_invoice_payment_progress
    WHERE invoice_status IN ('posted', 'approved')
        AND invoice_matching_status NOT IN ('excluded', 'invalid')
)
SELECT
    COUNT(*) AS valid_invoice_count,
    SUM(CASE WHEN payment_progress_status = 'paid' THEN 1 ELSE 0 END)
        AS fully_paid_invoice_count,
    ROUND(
        100.0
        * SUM(CASE WHEN payment_progress_status = 'paid' THEN 1 ELSE 0 END)
        / NULLIF(COUNT(*), 0),
        1
    ) AS completion_rate_pct,
    ROUND(
        SUM(
            CASE
                WHEN invoice_currency = 'TRY' THEN outstanding_amount
                ELSE 0
            END
        ),
        2
    ) AS try_outstanding_amount,
    ROUND(
        SUM(
            CASE
                WHEN invoice_currency = 'EUR' THEN outstanding_amount
                ELSE 0
            END
        ),
        2
    ) AS eur_outstanding_amount
FROM valid_invoices;
