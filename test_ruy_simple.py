import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import parse_qrp_bytes_to_records
import pandas as pd

# Load the QRP file
qrp_path = "Exemplo QRP/Ruy de Barros Correia.QRP"

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

# Motive distribution
print("\nMotive distribution (top 10):")
motive_counts = df_unique['Motivo_Glosa'].value_counts().head(10)
for motive, count in motive_counts.items():
    print(f"{count:3d} - {motive}")

# Also show consolidated by motive
print("\nConsolidated by motive (top 10 by value):")
df_consolidado = df_unique.groupby('Motivo_Glosa', as_index=False)['Valor_Glosa'].sum()
df_consolidado = df_consolidado.sort_values(by='Valor_Glosa', ascending=False).head(10)
for _, row in df_consolidado.iterrows():
    print(f"R$ {row['Valor_Glosa']:,.2f} - {row['Motivo_Glosa']}")