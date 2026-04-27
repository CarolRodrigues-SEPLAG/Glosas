import sys
sys.path.append('.')

from app import parse_qrp_bytes_to_records
from pathlib import Path
import pandas as pd

file_path = Path(r'Exemplo QRP\Ruy de Barros Correia.QRP')
if file_path.exists():
    with open(file_path, 'rb') as f:
        bytes_data = f.read()
    records = parse_qrp_bytes_to_records(bytes_data, file_path.name)
    df = pd.DataFrame(records)
    print(f'Registros extraídos: {len(df)}')
    print('AIHs extraídas:')
    for record in records:
        print(f'  {record["AIH"]}')
    
    # Check for specific AIHs
    specific_aihs = ['2625105795796', '2625105795807']
    print('\nChecking for specific AIHs:')
    for aih in specific_aihs:
        found = any(r['AIH'] == aih for r in records)
        print(f'  {aih}: {"Found" if found else "Not found"}')
    
    # Check records with empty motives
    empty_motives = [r for r in records if not r['Motivo_Glosa'].strip()]
    print(f'\nRecords with empty motives: {len(empty_motives)}')
    if empty_motives:
        for r in empty_motives[:5]:  # Show first 5
            print(f'  AIH: {r["AIH"]}, Motivo: "{r["Motivo_Glosa"]}"')
    
    print(f'\nTotal records: {len(records)}')
else:
    print('Arquivo não encontrado')