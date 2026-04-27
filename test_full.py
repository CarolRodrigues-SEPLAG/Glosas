import sys
sys.path.append('.')

from app import parse_qrp_bytes_to_records
from pathlib import Path
import pandas as pd

file_path = Path(r'Exemplo QRP\HOSPAM.QRP')
if file_path.exists():
    with open(file_path, 'rb') as f:
        bytes_data = f.read()
    records = parse_qrp_bytes_to_records(bytes_data, file_path.name)
    df = pd.DataFrame(records)
    print(f'Registros brutos: {len(df)}')
    total_bruto = df['Valor_Glosa'].sum()
    print(f'Total bruto: R$ {total_bruto:,.2f}')
    df_unique = df.drop_duplicates(keep='first')
    print(f'Registros únicos: {len(df_unique)}')
    total_unique = df_unique['Valor_Glosa'].sum()
    print(f'Total único: R$ {total_unique:,.2f}')
    df_consolidado = df_unique.groupby(['Hospital', 'Motivo_Glosa'], as_index=False)['Valor_Glosa'].sum()
    total_consolidado = df_consolidado['Valor_Glosa'].sum()
    print(f'Total consolidado: R$ {total_consolidado:,.2f}')
else:
    print('Arquivo não encontrado')