import json

with open('notebooks/Phase_5_Deep_Learning.ipynb', encoding='utf-8') as f:
    nb = json.load(f)
    print("=== Extracting preprocessing code ===\n")
    for i, cell in enumerate(nb['cells']):
        code = ''.join(cell.get('source', []))
        
        # Extract create_sequences functions
        if 'def create_sequences' in code:
            print(f"Cell {i}: create_sequences")
            print(code)
            print("\n" + "="*80 + "\n")
        
        # Extract tokenizer setup
        if 'keras.preprocessing.text.Tokenizer' in code:
            print(f"Cell {i}: Tokenizer setup")
            print(code)
            print("\n" + "="*80 + "\n")
