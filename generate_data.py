from pathlib import Path
import json
import random

import pandas as pd
from faker import Faker


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
QUERY_DIR = DATA_DIR / "queries"
LINEAGE_DIR = DATA_DIR / "lineage"


def generate_all() -> None:
    """Generate the complete deterministic demo dataset and metadata."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    QUERY_DIR.mkdir(parents=True, exist_ok=True)
    LINEAGE_DIR.mkdir(parents=True, exist_ok=True)

    fake = Faker()
    random.seed(42)
    Faker.seed(42)

    customers = [
        {
            "customer_id": f"CUST_{index:04d}",
            "customer_name": fake.name(),
            "email": fake.email(),
            "country": fake.country(),
        }
        for index in range(1, 101)
    ]
    customers_df = pd.DataFrame(customers)
    # Inject documented corruptions into raw_customers.csv
    customers_df.loc[5, "email"] = None
    customers_df.loc[15, "email"] = "invalid_email_format"
    customers_df.loc[25, "customer_id"] = None
    customers_df.to_csv(RAW_DIR / "raw_customers.csv", index=False)

    statuses = ["COMPLETED", "PENDING", "CANCELLED"]
    orders = [
        {
            "order_id": f"ORD_{index:05d}",
            "customer_id": f"CUST_{random.randint(1, 100):04d}",
            "price": round(random.uniform(10, 500), 2),
            "status": random.choice(statuses),
            "order_date": str(fake.date_between(start_date="-30d", end_date="today")),
        }
        for index in range(1, 501)
    ]
    orders_df = pd.DataFrame(orders)
    orders_df.loc[10, "price"] = -25.50
    orders_df.loc[75, "price"] = -47.03
    orders_df.loc[210, "price"] = -12.75
    orders_df.loc[120, "status"] = "UNKNOWN"
    orders_df.loc[350, "status"] = "INVALID"
    orders_df.loc[180, "customer_id"] = None
    orders_df.loc[420, "customer_id"] = None
    # Inject corrupted order_date timestamps
    orders_df.loc[150, "order_date"] = "1970-01-01"
    orders_df.loc[250, "order_date"] = None
    orders_df.to_parquet(RAW_DIR / "stg_orders.parquet", index=False)

    (QUERY_DIR / "fct_sales.sql").write_text(
        """SELECT
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
""",
        encoding="utf-8",
    )

    lineage = {
        "nodes": [
            {"name": "raw_customers", "type": "source", "path": "data/raw/raw_customers.csv"},
            {"name": "stg_orders", "type": "staging", "path": "data/raw/stg_orders.parquet"},
            {"name": "fct_sales", "type": "fact", "path": "data/queries/fct_sales.sql"},
        ],
        "edges": [
            {"source": "raw_customers", "target": "stg_orders"},
            {"source": "stg_orders", "target": "fct_sales"},
            {"source": "raw_customers", "target": "fct_sales"},
        ],
    }
    (LINEAGE_DIR / "lineage.json").write_text(json.dumps(lineage, indent=4), encoding="utf-8")


if __name__ == "__main__":
    generate_all()
