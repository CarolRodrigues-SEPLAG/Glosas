import sys
sys.path.append('.')
from app import parse_qrp_bytes_to_records
import pandas as pd

with open(r'Exemplo QRP\Ruy de Barros Correia.QRP', 'rb') as f:
    raw_bytes = f.read()

records = parse_qrp_bytes_to_records(raw_bytes, 'Ruy de Barros Correia.QRP')
df = pd.DataFrame(records)
df_unique = df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')

# Check specific AIHs from TXT
target_aihs = ['2625105795796', '2625105795807']
for aih in target_aihs:
    record = df_unique[df_unique['AIH'] == aih]
    if not record.empty:
        print(f'AIH {aih} found: Motive: {record["Motivo_Glosa"].iloc[0]}')
    else:
        print(f'AIH {aih} not found in parsed records')

print(f'\nTotal records: {len(df_unique)}')
print(f'Total unique AIHs: {df_unique["AIH"].nunique()}')