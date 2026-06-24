"""Reproducible ETL: load CSVs from data/raw into SQLite.

Usage:
    python -m src.etl --db-path db/retailsense.db --raw-dir data/raw

The script reads the standard Olist CSVs (if present), cleans column names,
parses common date columns, and writes tables into the SQLite database using
transactions and chunked writes for large files.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
from typing import Dict, Iterable, List, Optional

import pandas as pd


CSV_TABLE_MAP: Dict[str, str] = {
    'olist_customers_dataset.csv': 'customers',
    'olist_geolocation_dataset.csv': 'geolocation',
    'olist_order_items_dataset.csv': 'order_items',
    'olist_order_payments_dataset.csv': 'payments',
    'olist_order_reviews_dataset.csv': 'reviews',
    'olist_orders_dataset.csv': 'orders',
    'olist_products_dataset.csv': 'products',
    'olist_sellers_dataset.csv': 'sellers',
    'product_category_name_translation.csv': 'category_translation',
}


def find_csv_files(raw_dir: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for fname, table in CSV_TABLE_MAP.items():
        path = os.path.join(raw_dir, fname)
        if os.path.exists(path):
            out[path] = table
    return out


def _clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize column names: strip
    df = df.rename(columns=lambda c: c.strip())
    return df


def _guess_parse_dates(columns: Iterable[str]) -> List[str]:
    date_tokens = ['date', 'timestamp', 'time']
    cols = []
    for c in columns:
        lc = c.lower()
        if any(tok in lc for tok in date_tokens):
            cols.append(c)
    return cols


def load_csv_to_sqlite(
    csv_path: str,
    table_name: str,
    conn: sqlite3.Connection,
    chunksize: Optional[int] = 100_000,
    if_exists: str = 'replace',
):
    """Load a CSV into sqlite using pandas chunked to_sql."""
    print(f'Loading {os.path.basename(csv_path)} -> {table_name} (chunksize={chunksize})')

    # detect parse_dates by column names (sample)
    sample = pd.read_csv(csv_path, nrows=100)
    parse_dates = _guess_parse_dates(sample.columns)

    reader = pd.read_csv(csv_path, chunksize=chunksize, parse_dates=parse_dates, low_memory=False)

    first = True
    for chunk in reader:
        chunk = _clean_column_names(chunk)
        chunk = chunk.replace({'': pd.NA})
        chunk.to_sql(
            name=table_name,
            con=conn,
            if_exists=('replace' if first and if_exists == 'replace' else 'append'),
            index=False,
        )
        first = False


def create_indices(conn: sqlite3.Connection):
    cur = conn.cursor()
    idx_cmds = [
        "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);",
        "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);",
        "CREATE INDEX IF NOT EXISTS idx_products_id ON products(product_id);",
        "CREATE INDEX IF NOT EXISTS idx_customers_id ON customers(customer_id);",
    ]
    for sql in idx_cmds:
        try:
            cur.execute(sql)
        except Exception:
            pass
    conn.commit()


def etl(db_path: str, raw_dir: str, tables: Optional[List[str]] = None, chunksize: int = 100_000, drop_existing: bool = False):
    os.makedirs(os.path.dirname(db_path) or '.', exist_ok=True)
    conn = sqlite3.connect(db_path)
    try:
        conn.execute('PRAGMA journal_mode = WAL;')
        conn.execute('PRAGMA synchronous = NORMAL;')

        csv_map = find_csv_files(raw_dir)
        if not csv_map:
            raise FileNotFoundError(f'No CSV files found in {raw_dir} matching known patterns')

        if tables:
            wanted = set(tables)
            csv_map = {p: t for p, t in csv_map.items() if t in wanted}

        for csv_path, table_name in csv_map.items():
            if drop_existing:
                conn.execute(f'DROP TABLE IF EXISTS {table_name};')
                conn.commit()
            load_csv_to_sqlite(csv_path, table_name, conn, chunksize=chunksize, if_exists='replace')

        create_indices(conn)
    finally:
        conn.close()


def parse_args():
    p = argparse.ArgumentParser(description='ETL: CSV -> SQLite (reproducible)')
    p.add_argument('--db-path', default=os.path.join('db', 'retailsense.db'), help='SQLite DB path')
    p.add_argument('--raw-dir', default=os.path.join('data', 'raw'), help='Directory containing raw CSV files')
    p.add_argument('--tables', nargs='+', help='Optional list of table names to load (e.g. orders customers)')
    p.add_argument('--chunksize', type=int, default=100_000, help='Pandas read_csv chunksize')
    p.add_argument('--drop-existing', action='store_true', help='Drop existing tables before loading')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()
    print('ETL starting', args)
    etl(db_path=args.db_path, raw_dir=args.raw_dir, tables=args.tables, chunksize=args.chunksize, drop_existing=args.drop_existing)
    print('ETL finished')