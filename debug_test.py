import sys
import os

print("Current directory:", os.getcwd())
print("Files in directory:", os.listdir('.'))

qrp_path = r"Exemplo QRP\Ruy de Barros Correia.QRP"
print("QRP path:", qrp_path)
print("QRP exists:", os.path.exists(qrp_path))

if os.path.exists(qrp_path):
    with open(qrp_path, 'rb') as f:
        raw_bytes = f.read()
    print("File size:", len(raw_bytes))
    print("First 100 bytes:", raw_bytes[:100])
else:
    print("File not found")