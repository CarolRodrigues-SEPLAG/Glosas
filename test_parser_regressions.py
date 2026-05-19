from pathlib import Path

import pandas as pd

from app import (
    normalize_motivo,
    officialize_motivo,
    parse_qrp_bytes_to_records,
    drop_duplicate_glosa_records,
)


def parse_unique(path):
    records = parse_qrp_bytes_to_records(path.read_bytes(), path.name)
    df = pd.DataFrame(records)
    return df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')


def test_normalize_reviewed_motivos():
    cases = {
        'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO (DOC )': 'PROFISSIONAL AUTONOMO NAO CADASTRADO',
        'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL': 'PROFISSIONAL AUTONOMO NAO CADASTRADO NO HOSPITAL',
        'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL COM CBO INFORMADO': 'PROFISSIONAL AUTONOMO NAO CADASTRADO NO HOSPITAL',
        'NÚMERO DA AIH FORA DE FAIXA': 'NUMERO DA AIH FORA DE FAIXA',
        'DÍGITO VERIFICADOR AIH ANTERIOR INVÁLIDO': 'DIGITO VERIFICADOR AIH ANTERIOR INVALIDO',
        'AIH BLOQUEADA POR DUPL.REINTERNAÇÃO MESMO CID DIAS': 'AIH BLOQUEADA POR DUPL.REINTERNACAO, MESMO CID< 3 DIAS',
        'AIH BLOQUEADA POR A PEDIDO/ÓBITO/TRANSFERÊNCIA/EVASÃO C/ DIA P/PROCED. C/MP DIAS ATEND': 'AIH BLOQUEADA POR ALTA A PEDIDO/OBITO/TRANSFERENCIA/EVASAO C/ 1 DIA',
        'LANÇAMENTO OBRIGATÓRIO DE OPM. VERIFIQUE COMPATIBILIDADE NO SIGTAP': 'LANCAMENTO OBRIGATORIO DE OPM',
        'AIH REJEITADA NA IMPORTAÇÃO. VERIFIQUE PROTOCOLO': 'AIH REJEITADA NA IMPORTACAO',
        'TOTAL DE DIÁRIAS SUPERIOR AO PERÍODO DE INTERNAÇÃO NA INFORMADA': 'TOTAL DE DIARIAS SUPERIOR AO PERIODO DE INTERNACAO NA COMPETENCIA',
        'AIH BLOQUEADA POR PERMANÊNCIA A MENOR INJUSTIFICADAD': 'AIH BLOQUEADA POR PERMANENCIA A MENOR INJUSTIFICADA',
    }
    for raw, expected in cases.items():
        motivo, recognized = officialize_motivo(normalize_motivo(raw))
        assert recognized
        assert motivo == expected


def test_aih_inside_motivo_does_not_split_record():
    path = Path('glosas - 2026.03 (JAN)/Arquivos QRP/OSS Nossa Senhora das Gracas.QRP')
    df = parse_unique(path)
    row = df[df['AIH'].eq('2625107095920')]
    assert len(row) == 1
    assert row.iloc[0]['Motivo_Glosa'] == 'NUMERO DA AIH FORA DE FAIXA'
    assert row.iloc[0]['Valor_Glosa'] == 1942.04


def test_eduardo_campos_reviewed_profissional_value_is_separate():
    path = Path('glosas - 2026.04 (FEV)/Arquivos QRP/OSS Eduardo Campos.QRP')
    df = parse_unique(path)
    row = df[df['Valor_Glosa'].eq(41.38)]
    assert len(row) == 1
    assert row.iloc[0]['Motivo_Glosa'] == 'PROFISSIONAL AUTONOMO NAO CADASTRADO NO HOSPITAL'


def test_eduardo_campos_reviewed_execucao_value_is_alta_a_pedido():
    path = Path('glosas - 2026.04 (FEV)/Arquivos QRP/OSS Eduardo Campos.QRP')
    df = parse_unique(path)
    rows = df[df['Motivo_Glosa'].eq('AIH BLOQUEADA POR ALTA A PEDIDO/OBITO/TRANSFERENCIA/EVASAO C/ 1 DIA')]
    assert round(rows['Valor_Glosa'].sum(), 2) == 1370.83
    assert 'DE EXECUÇÃO INVÁLIDA ( )' not in set(df['Motivo_Glosa'])


def test_eduardo_campos_exemplo_competencia_execucao_consolidacao():
    path = Path('Exemplo QRP/OSS Eduardo Campos.QRP')
    if path.exists():
        records = parse_qrp_bytes_to_records(path.read_bytes(), path.name)
        df = pd.DataFrame(records).drop_duplicates(subset=['Hospital', 'AIH', 'Motivo_Glosa', 'Valor_Glosa'], keep='first')
        
        # Verificar que COMPETENCIA DE EXECUCAO INVALIDA com 1171.50 foi mapeado para ALTA A PEDIDO
        competencia_rows = df[df['Motivo_Glosa'].eq('COMPETENCIA DE EXECUCAO INVALIDA')]
        assert len(competencia_rows) == 0, "COMPETÊNCIA DE EXECUÇÃO INVÁLIDA deve ter sido consolidada"
        
        # Verificar que o valor 1171.50 aparece sob ALTA A PEDIDO
        alta_rows = df[df['Valor_Glosa'].eq(1171.50)]
        assert len(alta_rows) > 0
        assert any('ALTA A PEDIDO' in m for m in alta_rows['Motivo_Glosa'])


def test_preserva_motivos_distintos_para_mesmo_aih_valor():
    arquivo_paths = [
        'glosas - 2026.04 (FEV)/Arquivos QRP/6 Restauracao.QRP',
        'glosas - 2026.04 (FEV)/Arquivos QRP/OSS Eduardo Campos.QRP',
        'glosas - 2026.04 (FEV)/Arquivos QRP/DGAR Geral de Areias.QRP',
    ]
    for arquivo in arquivo_paths:
        df = pd.DataFrame(parse_qrp_bytes_to_records(Path(arquivo).read_bytes(), Path(arquivo).name))
        df_correct = drop_duplicate_glosa_records(df)
        df_wrong = df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')
        assert len(df_correct) >= len(df_wrong)
        assert len(df_correct) != len(df_wrong)
