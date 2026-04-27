import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import parse_qrp_bytes_to_records
import pandas as pd

# Load the QRP file
qrp_path = r"Exemplo QRP\Ruy de Barros Correia.QRP"

with open(qrp_path, 'rb') as f:
    raw_bytes = f.read()

# Parse the records
records = parse_qrp_bytes_to_records(raw_bytes, "Ruy de Barros Correia.QRP")

# Create DataFrame
df = pd.DataFrame(records)

# Remove duplicates as in the app
df_unique = df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')

print(f"Total records after deduplication: {len(df_unique)}")
print(f"Sum of values: R$ {df_unique['Valor_Glosa'].sum():,.2f}")

# Check for empty motives
empty_motives = df_unique['Motivo_Glosa'].isna() | (df_unique['Motivo_Glosa'] == '')
print(f"Records with empty motives: {empty_motives.sum()}")

# Check for garbled motives (containing 'K L d' which seems like parsing error)
garbled_motives = df_unique['Motivo_Glosa'].str.contains('K L d', na=False)
print(f"Records with garbled motives (containing 'K L d'): {garbled_motives.sum()}")

# Motive distribution (top 10)
print("\nMotive distribution (top 10):")
motive_counts = df_unique['Motivo_Glosa'].value_counts().head(10)
for motive, count in motive_counts.items():
    print(f"{count:3d} - {motive}")

# Show some examples of garbled motives
print("\nExamples of garbled motives:")
garbled_examples = df_unique[garbled_motives]['Motivo_Glosa'].head(5)
for example in garbled_examples:
    print(f"  {example}")

# Check for multi-line motives (containing document numbers)
doc_motives = df_unique['Motivo_Glosa'].str.contains(r'\d{10,}', na=False)
print(f"\nRecords with document numbers in motives: {doc_motives.sum()}")

# Show examples
print("\nExamples of motives with document numbers:")
doc_examples = df_unique[doc_motives]['Motivo_Glosa'].head(3)
for example in doc_examples:
    print(f"  {example}")