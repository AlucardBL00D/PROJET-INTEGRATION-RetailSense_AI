import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = Path(__file__).parent / "retailsense.db"

CSV_MAP = {
    "clients": "../data/raw/olist_customers_dataset.csv",
    "geolocation": "../data/raw/olist_geolocation_dataset.csv",
    "order_items": "../data/raw/olist_order_items_dataset.csv",
    "payments": "../data/raw/olist_order_payments_dataset.csv",
    "reviews": "../data/raw/olist_order_reviews_dataset.csv",
    "orders": "../data/raw/olist_orders_dataset.csv",
    "products": "../data/raw/olist_products_dataset.csv",
    "sellers": "../data/raw/olist_sellers_dataset.csv",
    "category_translation": "../data/raw/product_category_name_translation.csv"
}

CREATE_TABLES = {
    "clients": (
        "CREATE TABLE IF NOT EXISTS clients ("
        "customer_id TEXT PRIMARY KEY,"
        "customer_unique_id TEXT,"
        "customer_zip_code_prefix TEXT,"
        "customer_city TEXT,"
        "customer_state TEXT"
        ")"
    ),
    "geolocation": (
        "CREATE TABLE IF NOT EXISTS geolocation ("
        "geolocation_zip_code_prefix TEXT PRIMARY KEY,"
        "geolocation_lat REAL,"
        "geolocation_lng REAL,"
        "geolocation_city TEXT,"
        "geolocation_state TEXT"
        ")"
    ),
    "sellers": (
        "CREATE TABLE IF NOT EXISTS sellers ("
        "seller_id TEXT PRIMARY KEY,"
        "seller_zip_code_prefix TEXT,"
        "seller_city TEXT,"
        "seller_state TEXT"
        ")"
    ),
    "products": (
        "CREATE TABLE IF NOT EXISTS products ("
        "product_id TEXT PRIMARY KEY,"
        "product_category_name TEXT,"
        "product_name_lenght INTEGER,"
        "product_description_lenght INTEGER,"
        "product_photos_qty INTEGER,"
        "product_weight_g REAL,"
        "product_length_cm REAL,"
        "product_height_cm REAL,"
        "product_width_cm REAL,"
        "FOREIGN KEY (product_category_name) REFERENCES category_translation(product_category_name)"
        ")"
    ),
    "category_translation": (
        "CREATE TABLE IF NOT EXISTS category_translation ("
        "product_category_name TEXT PRIMARY KEY,"
        "product_category_name_english TEXT"
        ")"
    ),
    "orders": (
        "CREATE TABLE IF NOT EXISTS orders ("
        "order_id TEXT PRIMARY KEY,"
        "customer_id TEXT,"
        "order_status TEXT,"
        "order_purchase_timestamp TEXT,"
        "order_approved_at TEXT,"
        "order_delivered_carrier_date TEXT,"
        "order_delivered_customer_date TEXT,"
        "order_estimated_delivery_date TEXT,"
        "FOREIGN KEY (customer_id) REFERENCES clients(customer_id)"
        ")"
    ),
    "order_items": (
        "CREATE TABLE IF NOT EXISTS order_items ("
        "order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "order_id TEXT,"
        "order_item_sequence INTEGER,"
        "product_id TEXT,"
        "seller_id TEXT,"
        "shipping_limit_date TEXT,"
        "price REAL,"
        "freight_value REAL,"
        "FOREIGN KEY (order_id) REFERENCES orders(order_id),"
        "FOREIGN KEY (product_id) REFERENCES products(product_id),"
        "FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)"
        ")"
    ),
    "payments": (
        "CREATE TABLE IF NOT EXISTS payments ("
        "payment_id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "order_id TEXT,"
        "payment_sequential INTEGER,"
        "payment_type TEXT,"
        "payment_installments INTEGER,"
        "payment_value REAL,"
        "FOREIGN KEY (order_id) REFERENCES orders(order_id)"
        ")"
    ),
    "reviews": (
        "CREATE TABLE IF NOT EXISTS reviews ("
        "review_id TEXT PRIMARY KEY,"
        "order_id TEXT,"
        "review_score INTEGER,"
        "review_comment_title TEXT,"
        "review_comment_message TEXT,"
        "review_creation_date TEXT,"
        "review_answer_timestamp TEXT,"
        "FOREIGN KEY (order_id) REFERENCES orders(order_id)"
        ")"
    )
}


def create_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    for name, ddl in CREATE_TABLES.items():
        cursor.execute(ddl)

    conn.commit()
    conn.close()


def import_csvs():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Order matters: load tables with FK constraints after their parent tables
    import_order = [
        "geolocation",
        "category_translation",
        "clients",
        "sellers",
        "products",
        "orders",
        "order_items",
        "payments",
        "reviews"
    ]

    for table in import_order:
        if table not in CSV_MAP:
            continue
            
        path = CSV_MAP[table]
        p = Path(__file__).parent / Path(path)
        if not p.exists():
            print(f"CSV for {table} not found at {p}")
            continue
        
        df = pd.read_csv(p, low_memory=False)
        
        # Import all data as-is, pandas will create columns matching the CSV
        try:
            df.to_sql(table, conn, if_exists="replace", index=False)
            print(f"✓ Imported {table} ({len(df)} rows) with columns: {list(df.columns)}")
        except Exception as e:
            print(f"✗ Error importing {table}: {e}")
            conn.rollback()
            continue

    conn.commit()
    conn.close()


if __name__ == "__main__":
    create_db()
    import_csvs()
    print("DB initialized and CSVs imported.")
