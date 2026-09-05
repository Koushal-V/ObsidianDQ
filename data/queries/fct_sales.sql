SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.country,
    o.price,
    o.status,
    o.order_date
FROM stg_orders o
LEFT JOIN raw_customers c
    ON o.customer_id = c.cust_id;
