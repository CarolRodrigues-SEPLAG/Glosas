from pathlib import Path
import pandas as pd
import re

# Simplified test
file_path = Path(r'Exemplo QRP\HOSPAM.QRP')
if file_path.exists():
    with open(file_path, 'rb') as f:
        bytes_data = f.read()
    print(f'File size: {len(bytes_data)} bytes')
    text = bytes_data.decode('utf-16le', errors='ignore')
    print(f'Decoded text length: {len(text)}')
    # Count AIH patterns
    ai_regex = re.compile(r'\b\d{13,14}\b')
    aihs = ai_regex.findall(text)
    print(f'AIHs found: {len(aihs)}')
    # Count currency
    currency_regex = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}')
    values = currency_regex.findall(text)
    print(f'Values found: {len(values)}')
else:
    print('Arquivo não encontrado')