import sys
import os
from pathlib import Path
import re

sys.path.append(os.path.dirname(__file__))
from app import parse_qrp_bytes_to_records
import pandas as pd

qrp_path = Path('Exemplo QRP') / 'Ruy de Barros Correia.QRP'
txt_path = Path('Exemplos TXT') / 'Ruy de Barros Correia.txt'

with qrp_path.open('rb') as f:
    raw_bytes = f.read()

records = parse_qrp_bytes_to_records(raw_bytes, qrp_path.name)
df = pd.DataFrame(records)
df_unique = df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')

print('Parser results:')
print(f'Total records after deduplication: {len(df_unique)}')
print(f'Sum of values: R$ {df_unique["Valor_Glosa"].sum():,.2f}')


def parse_txt_records(path):
    text = Path(path).read_text(encoding='cp1252', errors='replace')
    lines = [line.rstrip() for line in text.splitlines()]
    records = []
    current = None
    pattern = re.compile(r'^(\d{13})#\s*\d{2}#\s*\d{8,10}#\s*\d{2}/\d{2}/\d{4}#\s*(.*)$')

    for line in lines:
        if not line.strip():
            continue
        match = pattern.match(line)
        if match:
            if current is not None:
                records.append(current)
            current = {'AIH': match.group(1), 'text_lines': [match.group(2).strip()]}
            continue
        if current is not None:
            current['text_lines'].append(line.strip())

    if current is not None:
        records.append(current)

    expected = []
    currency_pattern = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}')
    for rec in records:
        text = ' '.join(rec['text_lines'])
        currency_matches = currency_pattern.findall(text)
        if not currency_matches:
            continue
        valor = float(currency_matches[-1].replace('.', '').replace(',', '.'))
        expected.append({'AIH': rec['AIH'], 'Valor': valor, 'Mensagem': text})
    return expected

expected_records = parse_txt_records(txt_path)
print() 
print('Expected from TXT:')
print(f'Total records: {len(expected_records)}')
print(f'Sum of values: R$ {sum(r["Valor"] for r in expected_records):,.2f}')

parser_aihs = set(df_unique['AIH'])
expected_aihs = set(r['AIH'] for r in expected_records)
missing_in_parser = expected_aihs - parser_aihs
extra_in_parser = parser_aihs - expected_aihs

print() 
print('Comparison:')
print(f'AIHs missing in parser: {len(missing_in_parser)}')
print(f'AIHs extra in parser: {len(extra_in_parser)}')
if missing_in_parser:
    print('Missing AIHs:', sorted(list(missing_in_parser))[:10], '...' if len(missing_in_parser) > 10 else '')
if extra_in_parser:
    print('Extra AIHs:', sorted(list(extra_in_parser))[:10], '...' if len(extra_in_parser) > 10 else '')

matched_records = 0
matched_value = 0.0
for exp in expected_records:
    parser_match = df_unique[(df_unique['AIH'] == exp['AIH']) & (df_unique['Valor_Glosa'] == exp['Valor'])]
    if not parser_match.empty:
        matched_records += 1
        matched_value += exp['Valor']

accuracy_records = matched_records / len(expected_records) * 100 if expected_records else 0.0
accuracy_value = matched_value / sum(r['Valor'] for r in expected_records) * 100 if expected_records else 0.0

print() 
print('Accuracy:')
print(f'Records accuracy: {accuracy_records:.1f}% ({matched_records}/{len(expected_records)})')
print(f'Value accuracy: {accuracy_value:.1f}% (R$ {matched_value:,.2f} / R$ {sum(r["Valor"] for r in expected_records):,.2f})')