import pandas as pd
from pathlib import Path

# Check orders_features.csv
df = pd.read_csv('data/processed/orders_features.csv')
print(f'Shape: {df.shape}')
print(f'Columns: {list(df.columns)[:10]}')
print(f'Missing customer_id: {df["customer_id"].isna().sum()}')
print(f'Missing main_category: {df["main_category"].isna().sum() if "main_category" in df.columns else "Column missing"}')

# Try to load GNN weights
gnn_path = Path('models/gnn_native_recommender.weights.h5')
print(f'\nGNN weights exist: {gnn_path.exists()}')

# Check daily_orders for demand RNN
daily_path = Path('models/daily_orders.csv')
print(f'Daily orders exist: {daily_path.exists()}')
if daily_path.exists():
    daily = pd.read_csv(daily_path)
    print(f'Daily orders shape: {daily.shape}')
    print(f'Columns: {list(daily.columns)}')
