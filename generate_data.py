from pathlib import Path
import json
import random

import pandas as pd
from faker import Faker


# ---------------------------------------------------------
# Configuration
# ---------------------------------------------------------

fake = Faker()
random.seed(42)
Faker.seed(42)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
QUERY_DIR = DATA_DIR / "queries"
LINEAGE_DIR = DATA_DIR / "lineage"

RAW_DIR.mkdir(parents=True, exist_ok=True)
QUERY_DIR.mkdir(parents=True, exist_ok=True)
LINEAGE_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------
# 1. Generate raw_customers.csv
# ---------------------------------------------------------

customers = []

for i in range(1, 101):
    customers.append(
        {
            "customer_id": f"CUST_{i:04d}",
            "customer_name": fake.name(),
            "email": fake.email(),
            "country": fake.country(),
        }
    )

customers_df = pd.DataFrame(customers)

customers_path = RAW_DIR / "raw_customers.csv"
customers_df.to_csv(customers_path, index=False)


# ---------------------------------------------------------
# 2. Generate stg_orders.parquet
# ---------------------------------------------------------

statuses = ["COMPLETED", "PENDING", "CANCELLED"]

orders = []

for i in range(1, 501):
    orders.append(
        {
            "order_id": f"ORD_{i:05d}",
            "customer_id": f"CUST_{random.randint(1, 100):04d}",
            "price": round(random.uniform(10, 500), 2),
            "status": random.choice(statuses),
            "order_date": fake.date_between(
                start_date="-30d",
                end_date="today"
            ),
        }
    )

orders_df = pd.DataFrame(orders)


# ---------------------------------------------------------
# Intentional DQ issues
# ---------------------------------------------------------

# Negative prices — invalid business values
orders_df.loc[10, "price"] = -25.50
orders_df.loc[75, "price"] = -47.03
orders_df.loc[210, "price"] = -12.75

# Invalid status
orders_df.loc[120, "status"] = "UNKNOWN"
orders_df.loc[350, "status"] = "INVALID"

# Missing customer IDs
orders_df.loc[180, "customer_id"] = None
orders_df.loc[420, "customer_id"] = None


orders_path = RAW_DIR / "stg_orders.parquet"
orders_df.to_parquet(orders_path, index=False)


# ---------------------------------------------------------
# 3. Generate fct_sales.sql
# ---------------------------------------------------------

fct_sales_sql = """SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.country,
    o.price,
    o.status,
    o.order_date
FROM stg_orders o
LEFT JOIN raw_customers c
    ON o.customer_id = c.customer_id;
"""

sql_path = QUERY_DIR / "fct_sales.sql"
sql_path.write_text(fct_sales_sql, encoding="utf-8")


# ---------------------------------------------------------
# 4. Generate lineage.json
# ---------------------------------------------------------

lineage = {
    "nodes": [
        {
            "name": "raw_customers",
            "type": "source",
            "path": "data/raw/raw_customers.csv",
        },
        {
            "name": "stg_orders",
            "type": "staging",
            "path": "data/raw/stg_orders.parquet",
        },
        {
            "name": "fct_sales",
            "type": "fact",
            "path": "data/queries/fct_sales.sql",
        },
    ],
    "edges": [
        {
            "source": "raw_customers",
            "target": "stg_orders",
        },
        {
            "source": "stg_orders",
            "target": "fct_sales",
        },
        {
            "source": "raw_customers",
            "target": "fct_sales",
        },
    ],
}

lineage_path = LINEAGE_DIR / "lineage.json"
lineage_path.write_text(
    json.dumps(lineage, indent=4),
    encoding="utf-8",
)


# ---------------------------------------------------------
# Completion message
# ---------------------------------------------------------

print("=" * 60)
print("ObsidianDQ Phase 1 data generation complete")
print("=" * 60)

print(f"Customers : {customers_path}")
print(f"Orders    : {orders_path}")
print(f"SQL       : {sql_path}")
print(f"Lineage   : {lineage_path}")

print()
print(f"Customers rows : {len(customers_df)}")
print(f"Orders rows    : {len(orders_df)}")
print(f"Columns        : {list(orders_df.columns)}")

print()
print("Intentional DQ issues:")
print("- 3 negative prices")
print("- 2 invalid statuses")
print("- 2 missing customer IDs")
print("=" * 60)