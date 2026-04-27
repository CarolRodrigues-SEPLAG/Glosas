import sys
import os
sys.path.append(os.path.dirname(__file__))

from app import parse_qrp_bytes_to_records

# Read the QRP file
with open("c:/Users/carolinne.silva/Desktop/GLOSAS GEMINI/Exemplo QRP/HOSPAM.QRP", "rb") as f:
    raw_bytes = f.read()

# Parse the records
records = parse_qrp_bytes_to_records(raw_bytes, "HOSPAM.QRP")

print(f"Total records extracted: {len(records)}")

if records:
    # Calculate sum of values
    total_value = sum(record['Valor_Glosa'] for record in records)
    print(f"Sum of values: R$ {total_value:,.2f}")

    # Show sample records
    print("\nSample records (first 5):")
    for i, record in enumerate(records[:5]):
        print(f"{i+1}. AIH: {record['AIH']}, Motivo: {record['Motivo_Glosa']}, Valor: R$ {record['Valor_Glosa']:,.2f}")

    # Check parentheses-based normalization
    print("\nChecking parentheses-based normalization:")
    motives_with_parens = [r for r in records if '(' in r['Motivo_Glosa'] or ')' in r['Motivo_Glosa']]
    print(f"Records with parentheses in motive: {len(motives_with_parens)}")

    # Show unique normalized motives
    unique_motives = set(r['Motivo_Glosa'] for r in records)
    print(f"\nUnique motive types: {len(unique_motives)}")
    print("Sample unique motives:")
    for motive in sorted(list(unique_motives))[:10]:
        print(f"  - {motive}")

else:
    print("No records extracted.")