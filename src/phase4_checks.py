import warnings
warnings.filterwarnings('ignore')

import os
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
import joblib

RANDOM_STATE = 42

def find_root():
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / 'data').exists() and (candidate / 'db').exists():
            return candidate
    return cwd

ROOT = find_root()
PROCESSED = ROOT / 'data' / 'processed'
MODELS = ROOT / 'models'

orders_fp = PROCESSED / 'orders_features.csv'
if not orders_fp.exists():
    raise FileNotFoundError(f"Missing {orders_fp}")

print('Using processed file:', orders_fp)
orders = pd.read_csv(orders_fp)
print('orders.shape =', orders.shape)

# Classification target
target = 'bad_review'
if target not in orders.columns:
    raise ValueError(f"Target column '{target}' not found in orders_features.csv")

# Drop rows where target is NA
df = orders.copy()
df = df[df[target].notna()].reset_index(drop=True)
print('After dropping NA target rows:', df.shape)

# Prepare indices split to check overlap
y = df[target].astype(int)
idx = df.index.values
trainval_idx, test_idx = train_test_split(idx, test_size=0.2, stratify=y, random_state=RANDOM_STATE)
train_idx, val_idx = train_test_split(trainval_idx, test_size=0.25, stratify=y[trainval_idx], random_state=RANDOM_STATE)

print('\nSplit sizes:')
print('train:', len(train_idx), 'val:', len(val_idx), 'test:', len(test_idx))

# Check overlap
overlap_train_test = set(train_idx) & set(test_idx)
overlap_train_val = set(train_idx) & set(val_idx)
print('overlap train/test:', len(overlap_train_test))
print('overlap train/val:', len(overlap_train_val))

# Label distribution
print('\nLabel distribution (proportion):')
print('train:', df.loc[train_idx, target].value_counts(normalize=True).to_dict())
print('val  :', df.loc[val_idx, target].value_counts(normalize=True).to_dict())
print('test :', df.loc[test_idx, target].value_counts(normalize=True).to_dict())

# Check suspicious columns
suspect_cols = [c for c in df.columns if ('review' in c.lower()) or ('score' in c.lower()) or ('rate' in c.lower())]
print('\nSuspect columns (review/score/rate):', suspect_cols)

# If suspect columns present, check exact matches with target
if suspect_cols:
    for c in suspect_cols:
        try:
            equal_prop = (df.loc[train_idx, c] == df.loc[train_idx, target]).mean()
            print(f"Column {c}: proportion equal to target in train = {equal_prop}")
        except Exception:
            print(f"Could not compare column {c}")

# Check duplicates by order_id or customer_unique_id
id_cols = [c for c in ['order_id','customer_unique_id','customer_id'] if c in df.columns]
for idc in id_cols:
    print(f"Unique {idc}:", df[idc].nunique(), 'rows:', len(df))

# Build feature matrix as notebook does
X = df.drop(columns=[target, 'order_id', 'customer_id', 'customer_unique_id'], errors='ignore')

# Check if any column is identical to target
numeric_cols = X.select_dtypes(include=['int64','float64']).columns.tolist()
for c in numeric_cols:
    try:
        corr = np.corrcoef(X[c].fillna(0).values, df[target].astype(int).values)[0,1]
        if np.abs(corr) > 0.9999:
            print('Column', c, 'is almost perfectly correlated with target (corr=', corr, ')')
    except Exception:
        pass

# Load best model if exists
best_model_fp = MODELS / 'churn_best.joblib'
if best_model_fp.exists():
    print('\nFound saved model:', best_model_fp)
    model = joblib.load(best_model_fp)
    # prepare train/val/test feature sets as model expects (pipeline handles preprocessing)
    X_train = X.loc[train_idx]
    X_val = X.loc[val_idx]
    X_test = X.loc[test_idx]
    y_train = df.loc[train_idx, target].astype(int)
    y_val = df.loc[val_idx, target].astype(int)
    y_test = df.loc[test_idx, target].astype(int)

    for name, (Xsub, ysub) in [('val', (X_val, y_val)), ('test', (X_test, y_test))]:
        try:
            ypred = model.predict(Xsub)
            print(f"\n{name} classification report:")
            print(classification_report(ysub, ypred))
            print('Confusion matrix:')
            print(confusion_matrix(ysub, ypred))
        except Exception as e:
            print('Could not evaluate model on', name, '—', e)
else:
    print('\nNo `churn_best.joblib` model found to evaluate.')

print('\nChecks complete.')
