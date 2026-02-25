-- ==============================================================================
-- CONSISTENT AI SUITE - MATERIALIZED VIEWS SETUP
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. ML INPUT MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_ml_input CASCADE;
CREATE MATERIALIZED VIEW mv_ml_input AS
SELECT 
    mp.company_name, 
    mp.state, 
    p.group_name, 
    SUM(tp.net_amt) as total_spend
FROM transactions_dsr t
JOIN transactions_dsr_products tp ON t.id = tp.dsr_id
JOIN master_party mp ON t.party_id = mp.id
JOIN master_products p ON tp.product_id = p.id
WHERE t.is_approved = 'True'
GROUP BY mp.company_name, mp.state, p.group_name;

-- ------------------------------------------------------------------------------
-- 2. MARKET BASKET MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_product_associations CASCADE;
CREATE MATERIALIZED VIEW mv_product_associations AS
SELECT 
    p1.product_name AS product_a, 
    p2.product_name AS product_b, 
    COUNT(DISTINCT t1.dsr_id) AS times_bought_together
FROM transactions_dsr_products t1
JOIN transactions_dsr_products t2 
    ON t1.dsr_id = t2.dsr_id 
    AND t1.product_id != t2.product_id
JOIN master_products p1 ON t1.product_id = p1.id
JOIN master_products p2 ON t2.product_id = p2.id
GROUP BY p1.product_name, p2.product_name
HAVING COUNT(DISTINCT t1.dsr_id) > 1
ORDER BY times_bought_together DESC;

-- ------------------------------------------------------------------------------
-- 3. AGEING STOCK MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_ageing_stock CASCADE;
CREATE MATERIALIZED VIEW mv_ageing_stock AS
SELECT 
    p.product_name, 
    SUM(s.qty) as total_stock_qty,
    MAX(CURRENT_DATE - s.created_at::date) as max_age_days
FROM master_opening_stock s
JOIN master_products p ON s.product_id = p.id
GROUP BY p.product_name;

-- ------------------------------------------------------------------------------
-- 4. DEAD STOCK LIQUIDATION LEADS MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_stock_liquidation_leads CASCADE;
CREATE MATERIALIZED VIEW mv_stock_liquidation_leads AS
SELECT 
    product_name AS dead_stock_item
FROM mv_ageing_stock
WHERE max_age_days > 90 AND total_stock_qty > 0;

-- ------------------------------------------------------------------------------
-- 5. FACT SALES INTELLIGENCE (Core Dashboard Table)
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS fact_sales_intelligence CASCADE;
CREATE MATERIALIZED VIEW fact_sales_intelligence AS
WITH max_date_cte AS (
    SELECT MAX(date) as last_recorded_date FROM transactions_dsr
),
sales_stats AS (
    SELECT 
        t.party_id,
        COUNT(DISTINCT CASE WHEN t.date >= (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN t.id END) as recent_txns,
        COUNT(DISTINCT CASE WHEN t.date < (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN t.id END) as old_txns,
        COALESCE(SUM(CASE WHEN t.date >= (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN tp.net_amt ELSE 0 END), 0) as recent_revenue,
        COALESCE(SUM(CASE WHEN t.date >= (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '180 days' AND t.date < (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN tp.net_amt ELSE 0 END), 0) as prev_revenue
    FROM transactions_dsr t
    LEFT JOIN transactions_dsr_products tp ON t.id = tp.dsr_id
    WHERE t.is_approved = 'True' 
    GROUP BY t.party_id
),
partner_products AS (
    SELECT DISTINCT t.party_id, p.product_name
    FROM transactions_dsr t
    JOIN transactions_dsr_products tp ON t.id = tp.dsr_id
    JOIN master_products p ON tp.product_id = p.id
),
pitches AS (
    SELECT 
        pp.party_id,
        pa.product_b,
        ROW_NUMBER() OVER(PARTITION BY pp.party_id ORDER BY pa.times_bought_together DESC) as rank
    FROM partner_products pp
    JOIN mv_product_associations pa ON pp.product_name = pa.product_a
    WHERE NOT EXISTS (
        SELECT 1 FROM partner_products pp2 
        WHERE pp2.party_id = pp.party_id AND pp2.product_name = pa.product_b
    )
)
SELECT 
    mp.company_name,
    CASE 
        WHEN COALESCE(ss.recent_txns, 0) = 0 AND COALESCE(ss.old_txns, 0) > 0 THEN 'Churned (Risk)'
        WHEN COALESCE(ss.old_txns, 0) = 0 AND COALESCE(ss.recent_txns, 0) > 0 THEN 'New Partner'
        WHEN COALESCE(ss.recent_txns, 0) > COALESCE(ss.old_txns, 0) THEN 'Healthy (Growing)' 
        ELSE 'Stable'
    END as health_status,
    CASE 
        WHEN ss.prev_revenue > 0 THEN 
            ROUND(((ss.recent_revenue - ss.prev_revenue) / ss.prev_revenue * 100)::numeric, 1)
        ELSE 0 
    END as revenue_variance_pct,
    COALESCE((SELECT CAST(product_b AS TEXT) FROM pitches WHERE party_id = mp.id AND rank = 1), 'N/A') as top_affinity_pitch,
    'None' as missing_categories
FROM master_party mp
LEFT JOIN sales_stats ss ON mp.id = ss.party_id;

CREATE INDEX idx_fact_party ON fact_sales_intelligence(company_name);-- ==============================================================================
-- CONSISTENT AI SUITE - MATERIALIZED VIEWS SETUP
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. ML INPUT MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_ml_input CASCADE;
CREATE MATERIALIZED VIEW mv_ml_input AS
SELECT 
    mp.company_name, 
    mp.state, 
    p.group_name, 
    SUM(tp.net_amt) as total_spend
FROM transactions_dsr t
JOIN transactions_dsr_products tp ON t.id = tp.dsr_id
JOIN master_party mp ON t.party_id = mp.id
JOIN master_products p ON tp.product_id = p.id
WHERE t.is_approved = 'True'
GROUP BY mp.company_name, mp.state, p.group_name;

-- ------------------------------------------------------------------------------
-- 2. MARKET BASKET MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_product_associations CASCADE;
CREATE MATERIALIZED VIEW mv_product_associations AS
SELECT 
    p1.product_name AS product_a, 
    p2.product_name AS product_b, 
    COUNT(DISTINCT t1.dsr_id) AS times_bought_together
FROM transactions_dsr_products t1
JOIN transactions_dsr_products t2 
    ON t1.dsr_id = t2.dsr_id 
    AND t1.product_id != t2.product_id
JOIN master_products p1 ON t1.product_id = p1.id
JOIN master_products p2 ON t2.product_id = p2.id
GROUP BY p1.product_name, p2.product_name
HAVING COUNT(DISTINCT t1.dsr_id) > 1
ORDER BY times_bought_together DESC;

-- ------------------------------------------------------------------------------
-- 3. AGEING STOCK MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_ageing_stock CASCADE;
CREATE MATERIALIZED VIEW mv_ageing_stock AS
SELECT 
    p.product_name, 
    SUM(s.qty) as total_stock_qty,
    MAX(CURRENT_DATE - s.created_at::date) as max_age_days
FROM master_opening_stock s
JOIN master_products p ON s.product_id = p.id
GROUP BY p.product_name;

-- ------------------------------------------------------------------------------
-- 4. DEAD STOCK LIQUIDATION LEADS MATERIALIZED VIEW
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS mv_stock_liquidation_leads CASCADE;
CREATE MATERIALIZED VIEW mv_stock_liquidation_leads AS
SELECT 
    product_name AS dead_stock_item
FROM mv_ageing_stock
WHERE max_age_days > 90 AND total_stock_qty > 0;

-- ------------------------------------------------------------------------------
-- 5. FACT SALES INTELLIGENCE (Core Dashboard Table)
-- ------------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS fact_sales_intelligence CASCADE;
CREATE MATERIALIZED VIEW fact_sales_intelligence AS
WITH max_date_cte AS (
    SELECT MAX(date) as last_recorded_date FROM transactions_dsr
),
sales_stats AS (
    SELECT 
        t.party_id,
        COUNT(DISTINCT CASE WHEN t.date >= (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN t.id END) as recent_txns,
        COUNT(DISTINCT CASE WHEN t.date < (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN t.id END) as old_txns,
        COALESCE(SUM(CASE WHEN t.date >= (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN tp.net_amt ELSE 0 END), 0) as recent_revenue,
        COALESCE(SUM(CASE WHEN t.date >= (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '180 days' AND t.date < (SELECT last_recorded_date FROM max_date_cte) - INTERVAL '90 days' THEN tp.net_amt ELSE 0 END), 0) as prev_revenue
    FROM transactions_dsr t
    LEFT JOIN transactions_dsr_products tp ON t.id = tp.dsr_id
    WHERE t.is_approved = 'True' 
    GROUP BY t.party_id
),
partner_products AS (
    SELECT DISTINCT t.party_id, p.product_name
    FROM transactions_dsr t
    JOIN transactions_dsr_products tp ON t.id = tp.dsr_id
    JOIN master_products p ON tp.product_id = p.id
),
pitches AS (
    SELECT 
        pp.party_id,
        pa.product_b,
        ROW_NUMBER() OVER(PARTITION BY pp.party_id ORDER BY pa.times_bought_together DESC) as rank
    FROM partner_products pp
    JOIN mv_product_associations pa ON pp.product_name = pa.product_a
    WHERE NOT EXISTS (
        SELECT 1 FROM partner_products pp2 
        WHERE pp2.party_id = pp.party_id AND pp2.product_name = pa.product_b
    )
)
SELECT 
    mp.company_name,
    CASE 
        WHEN COALESCE(ss.recent_txns, 0) = 0 AND COALESCE(ss.old_txns, 0) > 0 THEN 'Churned (Risk)'
        WHEN COALESCE(ss.old_txns, 0) = 0 AND COALESCE(ss.recent_txns, 0) > 0 THEN 'New Partner'
        WHEN COALESCE(ss.recent_txns, 0) > COALESCE(ss.old_txns, 0) THEN 'Healthy (Growing)' 
        ELSE 'Stable'
    END as health_status,
    CASE 
        WHEN ss.prev_revenue > 0 THEN 
            ROUND(((ss.recent_revenue - ss.prev_revenue) / ss.prev_revenue * 100)::numeric, 1)
        ELSE 0 
    END as revenue_variance_pct,
    COALESCE((SELECT CAST(product_b AS TEXT) FROM pitches WHERE party_id = mp.id AND rank = 1), 'N/A') as top_affinity_pitch,
    'None' as missing_categories
FROM master_party mp
LEFT JOIN sales_stats ss ON mp.id = ss.party_id;

CREATE INDEX idx_fact_party ON fact_sales_intelligence(company_name);
