from pathlib import Path

import pandas as pd

from app import normalize_motivo, parse_qrp_bytes_to_records


def parse_unique(path):
    records = parse_qrp_bytes_to_records(path.read_bytes(), path.name)
    df = pd.DataFrame(records)
    return df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')


def test_normalize_reviewed_motivos():
    cases = {
        'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO (DOC )': 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO',
        'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL': 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL',
        'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL COM CBO INFORMADO': 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL',
        'NÚMERO DA AIH FORA DE FAIXA': 'NÚMERO DA AIH FORA DE FAIXA',
        'DÍGITO VERIFICADOR AIH ANTERIOR INVÁLIDO': 'DÍGITO VERIFICADOR AIH ANTERIOR INVÁLIDO',
        'AIH BLOQUEADA POR DUPL.REINTERNAÇÃO MESMO CID DIAS': 'AIH BLOQUEADA POR DUPL.REINTERNAÇÃO, MESMO CID< 3 DIAS',
        'AIH BLOQUEADA POR A PEDIDO/ÓBITO/TRANSFERÊNCIA/EVASÃO C/ DIA P/PROCED. C/MP DIAS ATEND': 'AIH BLOQUEADA POR ALTA A PEDIDO/ÓBITO/TRANSFERÊNCIA/EVASÃO C/ 1 DIA',
        'LANÇAMENTO OBRIGATÓRIO DE OPM. VERIFIQUE COMPATIBILIDADE NO SIGTAP': 'LANÇAMENTO OBRIGATÓRIO DE OPM',
        'AIH REJEITADA NA IMPORTAÇÃO. VERIFIQUE PROTOCOLO': 'AIH REJEITADA NA IMPORTAÇÃO',
        'TOTAL DE DIÁRIAS SUPERIOR AO PERÍODO DE INTERNAÇÃO NA INFORMADA': 'TOTAL DE DIÁRIAS SUPERIOR AO PERÍODO DE INTERNAÇÃO NA COMPETÊNCIA',
        'AIH BLOQUEADA POR PERMANÊNCIA A MENOR INJUSTIFICADAD': 'AIH BLOQUEADA POR PERMANÊNCIA A MENOR INJUSTIFICADA',
    }
    for raw, expected in cases.items():
        assert normalize_motivo(raw) == expected


def test_aih_inside_motivo_does_not_split_record():
    path = Path('glosas - 2026.03 (JAN)/Arquivos QRP/OSS Nossa Senhora das Gracas.QRP')
    df = parse_unique(path)
    row = df[df['AIH'].eq('2625107095920')]
    assert len(row) == 1
    assert row.iloc[0]['Motivo_Glosa'] == 'NÚMERO DA AIH FORA DE FAIXA'
    assert row.iloc[0]['Valor_Glosa'] == 1942.04


def test_eduardo_campos_reviewed_profissional_value_is_separate():
    path = Path('glosas - 2026.04 (FEV)/Arquivos QRP/OSS Eduardo Campos.QRP')
    df = parse_unique(path)
    row = df[df['Valor_Glosa'].eq(41.38)]
    assert len(row) == 1
    assert row.iloc[0]['Motivo_Glosa'] == 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL'


def test_eduardo_campos_reviewed_execucao_value_is_alta_a_pedido():
    path = Path('glosas - 2026.04 (FEV)/Arquivos QRP/OSS Eduardo Campos.QRP')
    df = parse_unique(path)
    rows = df[df['Motivo_Glosa'].eq('AIH BLOQUEADA POR ALTA A PEDIDO/ÓBITO/TRANSFERÊNCIA/EVASÃO C/ 1 DIA')]
    assert round(rows['Valor_Glosa'].sum(), 2) == 1370.83
    assert 'DE EXECUÇÃO INVÁLIDA ( )' not in set(df['Motivo_Glosa'])
