SELECT
  o.order_id,
  o.customer_id,
  c.customer_name,
  c.country,
  o.price,
  o.status,
  o.order_date
FROM stg_orders AS o
LEFT JOIN raw_customers AS c
  ON o.customer_id = c.customer_id;
