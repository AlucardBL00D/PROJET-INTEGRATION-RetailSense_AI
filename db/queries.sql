-- Aggregation queries for RetailSense_AI

-- 1) Revenue (chiffre d'affaires) par client
SELECT
  customer_id,
  SUM(order_total) AS revenue,
  COUNT(DISTINCT order_id) AS n_orders
FROM orders
GROUP BY customer_id
ORDER BY revenue DESC;

-- 2) Revenue par produit
SELECT
  oi.product_id,
  COALESCE(p.product_name, '') AS product_name,
  SUM(oi.price) AS revenue,
  COUNT(DISTINCT oi.order_id) AS n_orders
FROM order_items oi
LEFT JOIN products p USING(product_id)
GROUP BY oi.product_id, p.product_name
ORDER BY revenue DESC;

-- 3) Revenue par mois
SELECT
  STRFTIME('%Y-%m', order_purchase_timestamp) AS year_month,
  SUM(order_total) AS revenue,
  COUNT(DISTINCT order_id) AS n_orders
FROM orders
GROUP BY year_month
ORDER BY year_month;

-- 4) Nombre de commandes global
SELECT COUNT(DISTINCT order_id) AS total_orders FROM orders;

-- 5) Dernier achat par client
SELECT customer_id, MAX(order_purchase_timestamp) AS last_purchase FROM orders GROUP BY customer_id;

-- 6) Diagnostics / intégrité
-- a) orphan order_items
SELECT oi.order_id FROM order_items oi LEFT JOIN orders o ON oi.order_id = o.order_id WHERE o.order_id IS NULL LIMIT 20;

-- b) duplicate order_items groups
SELECT order_id, product_id, COUNT(*) as cnt FROM order_items GROUP BY order_id, product_id HAVING cnt > 1 LIMIT 20;

-- c) null counts in orders
SELECT
  SUM(CASE WHEN order_id IS NULL THEN 1 ELSE 0 END) AS null_order_id,
  SUM(CASE WHEN customer_id IS NULL THEN 1 ELSE 0 END) AS null_customer_id,
  SUM(CASE WHEN order_purchase_timestamp IS NULL THEN 1 ELSE 0 END) AS null_purchase_ts
FROM orders;

-- 7) Index recommendations (run once)
-- CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
-- CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts ON orders(order_purchase_timestamp);
-- CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
-- CREATE INDEX IF NOT EXISTS idx_products_id ON products(product_id);

-- 8) Revenue cumulé par client (cumulative revenue by customer)
SELECT
  customer_id,
  SUM(order_total) OVER (PARTITION BY customer_id ORDER BY STRFTIME('%Y-%m', order_purchase_timestamp)) AS cumulative_revenue
FROM orders
ORDER BY customer_id, STRFTIME('%Y-%m', order_purchase_timestamp);

-- 9) Taux de croissance du chiffre d'affaires par mois (month-over-month revenue growth)
SELECT
  year_month,
  SUM(revenue) AS monthly_revenue,
  LAG(SUM(revenue)) OVER (ORDER BY year_month) AS previous_month_revenue,
  (SUM(revenue) - LAG(SUM(revenue)) OVER (ORDER BY year_month)) / NULLIF(LAG(SUM(revenue)) OVER (ORDER BY year_month), 0) AS revenue_growth_rate
FROM (
  SELECT
    STRFTIME('%Y-%m', order_purchase_timestamp) AS year_month,
    order_total AS revenue
  FROM orders
)
GROUP BY year_month
ORDER BY year_month;

-- 10) Diagnostic des produits sans vente (products with no sales)
SELECT p.product_id, p.product_name
FROM products p
LEFT JOIN order_items oi ON p.product_id = oi.product_id
LEFT JOIN orders o ON oi.order_id = o.order_id
WHERE o.order_id IS NULL
LIMIT 20;