import json
from pathlib import Path

def find_root():
    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / 'data').exists() and (candidate / 'db').exists():
            return candidate
    return cwd

ROOT = find_root()

notebook_path = ROOT / 'notebooks'/ 'Phase_4_Machine_learning.ipynb'
nb = json.loads(notebook_path.read_text(encoding='utf-8'))
updated = False
for cell in nb['cells']:
    if cell['cell_type'] != 'code':
        continue
    source = ''.join(cell['source'])
    if '# 4.1 Segmentation RFM — elbow + silhouette, KMeans et DBSCAN' in source and 'rfm_std.select_dtypes' in source:
        new_source = []
        for line in cell['source']:
            if line.strip() == 'X = None':
                new_source.append("if rfm_std is not None:\n")
            elif line.strip() == '# use numeric columns only':
                continue
            elif line.strip() == 'X = rfm_std.select_dtypes(include=[np.number]).values':
                new_source.append("\tX = rfm_std[['recency','frequency','monetary']].astype(float).values\n")
            else:
                new_source.append(line)
        cell['source'] = new_source
        updated = True
    if '# 4.2 Classification (churn)' in source and 'feature_cols' not in source:
        new_source = []
        for line in cell['source']:
            if line.startswith('# drop identifiers'):
                new_source.append(line)
                new_source.append("# use only the guide-prescribed classification features\n")
                new_source.append("feature_cols = [\n")
                new_source.append("\t'total_price', 'total_freight', 'total_weight', 'n_items',\n")
                new_source.append("\t'max_installments', 'payment_value', 'delivery_days', 'delay_days',\n")
                new_source.append("\t'purchase_month', 'purchase_dow', 'main_category', 'payment_type',\n")
                new_source.append("\t'customer_state'\n")
                new_source.append("]\n")
                new_source.append("missing = [c for c in feature_cols if c not in df.columns]\n")
                new_source.append("assert not missing, f\"Missing expected feature columns: {missing}\"\n")
                new_source.append("X = df[feature_cols].copy()\n")
                new_source.append("y = df[target]\n\n")
            elif line.startswith("X = df.drop(columns=[target, 'order_id', 'customer_id', 'customer_unique_id']"):
                continue
            elif line.startswith('y = df[target]'):
                continue
            else:
                new_source.append(line)
        cell['source'] = new_source
        updated = True
    if '# 4.3 Régression (delivery_days)' in source and 'feature_cols_reg' not in source:
        new_source = []
        for line in cell['source']:
            if line.startswith('X = df_reg.drop(columns=[target, '):
                new_source.append("# use only the guide-prescribed regression features (exclude delay_days / late)\n")
                new_source.append("feature_cols_reg = [\n")
                new_source.append("\t'total_price', 'total_freight', 'total_weight', 'n_items',\n")
                new_source.append("\t'payment_value', 'purchase_month', 'main_category', 'customer_state'\n")
                new_source.append("]\n")
                new_source.append("missing_reg = [c for c in feature_cols_reg if c not in df_reg.columns]\n")
                new_source.append("assert not missing_reg, f\"Missing expected regression feature columns: {missing_reg}\"\n")
                new_source.append("X = df_reg[feature_cols_reg].copy()\n")
            else:
                new_source.append(line)
        cell['source'] = new_source
        updated = True

if not updated:
    raise RuntimeError('No notebook changes were applied')
notebook_path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding='utf-8')
print('Notebook patched successfully')
