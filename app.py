import streamlit as st
import pandas as pd
import re
import io
import unicodedata
from pathlib import Path
from functools import lru_cache

def clean_qrp_text(raw_bytes):
    """
    PASSO 1: Converte o binário do QRP para texto legível.
    """
    text = raw_bytes.decode('utf-16le', errors='replace')
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = text.replace('\xa0', ' ')
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def clean_motivo_text(text):
    # Referências a portarias fazem parte do motivo, ao contrário dos códigos
    # de procedimentos/competências entre parênteses.
    references = []

    def protect_reference(match):
        token = 'REFERENCIANORMATIVA' + ('Z' * (len(references) + 1))
        references.append((token, match.group(0)))
        return token

    text = re.sub(r'\bPT\s+\d+\s+DE\s+\d{2}/\d{2}/(?:\d{4}|\d{2})\b',
                  protect_reference, text, flags=re.IGNORECASE)
    # Retira também uma letra residual do QRP imediatamente após o código.
    text = re.sub(r'\(\s*\d[\d\s/.,-]*\)[A-Za-z]?(?![A-Za-z])', ' ', text)
    # Removido: text = re.sub(r'\([^)]*\)', ' ', text)  # Agora mantemos os códigos entre parênteses
    text = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', ' ', text)
    text = re.sub(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', ' ', text)
    text = re.sub(r'\b\d+\b', ' ', text)
    lixos = ['SISTEMA', 'DATASUS', 'SECRETARIA', 'ESTADUAL', 'HOSPITALARES',
             'DEFINITIVO', 'MENSAGEM DE ERRO', 'VALOR PRÉVIA', 'MUNICÍPIO',
             'RECIFE', 'LINHA', 'LOTE', 'COMPETÊNCIA', 'PÁGINA', 'GESTOR',
             'VALOR', 'PRÉVIA', 'ALTA', 'SIHD', 'ARIAL', 'FONTE']
    for lx in lixos:
        text = re.compile(r'\b' + lx + r'\b', re.IGNORECASE).sub(' ', text)
    text = re.sub(r'\([^)]*\)', lambda m: m.group(0) if 'DOC:' in m.group(0).upper() else m.group(0), text)
    text = re.sub(r'\(\s*DOC\s*\)', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\(\s*\)', ' ', text)
    text = re.sub(r'\([\s/.,-]*\)[A-Za-z]?(?![A-Za-z])', ' ', text)
    text = re.sub(r'[^A-Za-zÇÃÕÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙçãõáéíóúâêîôûàèìòù\s\-\/\.()]+', ' ', text)  # Adicionado () para manter parênteses
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+[A-Za-zÇÃÕÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙçãõáéíóúâêîôûàèìòù]$', '', text)
    text = re.sub(r'[\s\-\./,;:]+$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+OU\s*$', '', text, flags=re.IGNORECASE)
    for token, reference in references:
        text = text.replace(token, reference)
    return text


def remove_accents(value):
    normalized = unicodedata.normalize('NFD', value)
    return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')


def motivo_key(text):
    text = remove_accents(str(text).upper())
    text = re.sub(r'[^A-Z0-9]+', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


# Variável global para rastrear a modificação do arquivo de motivos
_motivos_file_mtime = None
_motivos_cache = None

def load_official_motivos():
    global _motivos_file_mtime, _motivos_cache
    
    path = Path('motivos_oficiais.xlsx')
    if not path.exists():
        return {}

    # Verificar se o arquivo foi modificado
    try:
        current_mtime = path.stat().st_mtime
    except OSError:
        return _motivos_cache or {}
    
    # Se o arquivo não foi modificado, retornar o cache
    if _motivos_file_mtime == current_mtime and _motivos_cache is not None:
        return _motivos_cache

    # Arquivo foi modificado ou é a primeira vez que carrega
    df = pd.read_excel(path, header=None)
    motivos = []
    for value in df.to_numpy().ravel():
        if pd.isna(value):
            continue
        motivo = str(value).strip()
        if not motivo:
            continue
        if motivo_key(motivo) == 'MOTIVOS DA REJEICAO':
            continue
        motivos.append(motivo.upper())

    result = {motivo_key(motivo): motivo for motivo in motivos}
    
    # Atualizar o cache global
    _motivos_file_mtime = current_mtime
    _motivos_cache = result
    
    return result


def officialize_motivo(motivo):
    official_by_key = load_official_motivos()
    if not official_by_key:
        return motivo, True

    official = official_by_key.get(motivo_key(motivo))
    if official:
        return official, True

    return motivo, False


DEDUP_MOTIVO_EXCEPTIONS = {}

DEDUP_PREFERRED_MOTIVOS = {
    (
        motivo_key('HOSPITAL DA RESTAURACAO'),
        '2626101049110',
        457.98,
    ): 'AIH BLOQUEADA POR PERIODOS DE INTERNACAO SOBREPOSTOS NO MOVIMENTO',
    (
        motivo_key('HOSPITAL GERAL DE AREIAS'),
        '2626100302958',
        439.69,
    ): 'AIH BLOQUEADA POR PERIODOS DE INTERNACAO SOBREPOSTOS NO MOVIMENTO',
}


def dedup_motivo_exception_key(row):
    exception_motivos = DEDUP_MOTIVO_EXCEPTIONS.get(motivo_key(row['Hospital']), set())
    motivo = row['Motivo_Glosa']
    return motivo if motivo in exception_motivos else ''


def dedup_preference_priority(row):
    preferred = DEDUP_PREFERRED_MOTIVOS.get((
        motivo_key(row['Hospital']),
        row['AIH'],
        round(float(row['Valor_Glosa']), 2),
    ))
    if preferred and row['Motivo_Glosa'] == preferred:
        return 0
    return 1


def drop_duplicate_glosa_records(df):
    """Remove glosas duplicadas pelo mesmo hospital, AIH e valor, mantendo o primeiro motivo."""
    df_with_key = df.copy()
    df_with_key['_Original_Order'] = range(len(df_with_key))
    df_with_key['_Motivo_Dedup'] = df_with_key.apply(dedup_motivo_exception_key, axis=1)
    df_with_key['_Dedup_Priority'] = df_with_key.apply(dedup_preference_priority, axis=1)
    df_with_key = df_with_key.sort_values(
        by=['_Dedup_Priority', '_Original_Order'],
        kind='mergesort'
    )
    df_unique = df_with_key.drop_duplicates(
        subset=['Hospital', *[c for c in ['CNES', 'Competência'] if c in df_with_key],
                'AIH', 'Valor_Glosa', '_Motivo_Dedup'],
        keep='first'
    )
    df_unique = df_unique.sort_values(by='_Original_Order', kind='mergesort')
    return df_unique.drop(columns=['_Motivo_Dedup', '_Dedup_Priority', '_Original_Order'])



def highlight_new_motivos(row):
    if row.get('Status') == 'Novo':
        return ['background-color: #fff3cd; color: #5f4100'] * len(row)
    return [''] * len(row)


def normalize_motivo(text):
    t = text.upper()

    def accentless(value):
        return remove_accents(value)

    t_ascii = re.sub(r'[^A-Z0-9 ]+', ' ', accentless(t))
    t_ascii = re.sub(r'\s+', ' ', t_ascii).strip()

    # Extrair códigos entre parênteses para usar como marcadores
    paren_codes = re.findall(r'\(([^)]+)\)', text.upper())
    paren_text = ' '.join(paren_codes)

    # Regras baseadas em códigos entre parênteses
    if 'DESACORDO COM CF-88' in paren_text or 'PROF COM MAIS 2 VINC PUBL' in paren_text:
        return 'PROFISSIONAL COM MAIS DE 2 VINC. PÚBLICOS (DESACORDO COM CF-88) OU PROFISSIONAL COM CH MAIOR QUE 168H POR SEMANA (PROF COM MAIS 168 H  SEMANAIS)'

    if 'DOC:' in paren_text or 'DOCUMENTO' in paren_text:
        return 'PROFISSIONAL VINCULADO NÃO CADASTRADO'

    # Regras existentes
    if 'PROFISSIONAL AUTONOMO' in t_ascii or 'PROFISSIONAL AUTO NOMO' in t_ascii or 'PROFISISONAL AUTONOMO' in t_ascii:
        if 'NO HOSPITAL COM CBO INFORMADO' in t_ascii:
            return 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL'
        if 'NO HOSPITAL' in t_ascii:
            return 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL'
        return 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO'

    if 'PROFISSIONAL VINCULADO' in t_ascii and 'NAO CADASTRADO' in t_ascii:
        return 'PROFISSIONAL VINCULADO NÃO CADASTRADO'

    if 'PROFISSIONAL NAO VINCULADO AO CNES' in t_ascii:
        return 'PROFISSIONAL NÃO VINCULADO AO CNES COM O CBO INFORMADO'

    if 'AIH BLOQUEADA EM OUTRO PROCESSAMENTO' in t_ascii:
        return 'AIH BLOQUEADA EM OUTRO PROCESSAMENTO'

    if 'AIH APROVADA EM OUTRO PROCESSAMENTO' in t_ascii:
        return 'AIH APROVADA EM OUTRO PROCESSAMENTO'

    if 'NUMERO DA AIH FORA DE FAIXA' in t_ascii:
        return 'NÚMERO DA AIH FORA DE FAIXA'

    if 'DIGITO VERIFICADOR AIH ANTERIOR INVALIDO' in t_ascii:
        return 'DÍGITO VERIFICADOR AIH ANTERIOR INVÁLIDO'

    if 'AIH REJEITADA NA IMPORTACAO' in t_ascii:
        return 'AIH REJEITADA NA IMPORTAÇÃO'

    if 'COMPETENCIA DE EXECUCAO INVALIDA' in t_ascii or 'DE EXECUCAO INVALIDA' in t_ascii:
        return 'COMPETÊNCIA DE EXECUÇÃO INVÁLIDA'

    if 'AIH REAPRESENTADA C DATA DE INT OU SAIDA DIFERENTE DA PRIMEIRA' in t_ascii:
        return 'AIH REAPRESENTADA C/ DATA DE INT OU SAIDA DIFERENTE DA PRIMEIRA'

    if 'DESACORDO COM CF' in t_ascii or 'CF-' in t_ascii or 'PROF COM MAIS' in t_ascii and 'VINC' in t_ascii and 'PUBL' in t_ascii:
        return 'PROFISSIONAL COM MAIS DE 2 VINC. PÚBLICOS (DESACORDO COM CF-88) OU PROFISSIONAL COM CH MAIOR QUE 168H POR SEMANA (PROF COM MAIS 168 H  SEMANAIS)'

    if 'DUPL INTERNA O C INTERSERC O DE PERIODOS' in t_ascii or 'DUPL INTERNACAO C INTERSERCAO DE PERIODOS' in t_ascii:
        return 'AIH BLOQUEADA POR DUPL.INTERNAÇÃO C/INTERSERCÃO DE PERÍODOS'

    if 'DUPL REINTERNACAO MESMO CID' in t_ascii:
        return 'AIH BLOQUEADA POR DUPL.REINTERNAÇÃO, MESMO CID< 3 DIAS'

    if 'AIH BLOQUEADA POR ALTA A PEDIDO' in t_ascii or 'AIH BLOQUEADA POR A PEDIDO' in t_ascii:
        return 'AIH BLOQUEADA POR ALTA A PEDIDO/ÓBITO/TRANSFERÊNCIA/EVASÃO C/ 1 DIA'

    # Alguns QRP acrescentam uma letra de controle ao final da descrição.
    # Regra restrita a este motivo para não unir motivos apenas semelhantes.
    if re.fullmatch(r'AIH BLOQUEADA POR PERMANENCIA A MENOR INJUSTIFICADA[A-Z]?', t_ascii):
        return 'AIH BLOQUEADA POR PERMANÊNCIA A MENOR INJUSTIFICADA'

    if 'PERIODOS DE INTERNA O SOBREPOSTOS NO MOVIMENTO' in t_ascii:
        return 'AIH BLOQUEADA POR PERÍODOS DE INTERNAÇÃO SOBREPOSTOS NO MOVIMENTO'

    if 'SOLICITACAO DE LIBERACAO' in t_ascii:
        return 'AIH BLOQUEADA POR SOLICITAÇÃO DE LIBERAÇÃO'

    if 'DIARIAS SUPERIOR A CAPACIDADE INSTALADA' in t_ascii and 'UTI' not in t_ascii:
        return 'QUANTIDADE DE DIÁRIAS SUPERIOR A CAPACIDADE INSTALADA'

    if 'DIARIAS DE UTI SUPERIOR A CAPACIDADE INSTALADA' in t_ascii:
        return 'QUANTIDADE DE DIÁRIAS DE UTI SUPERIOR A CAPACIDADE INSTALADA'

    if 'PROCEDIMENTO REALIZADO EXIGE HABILITACAO' in t_ascii:
        return 'PROCEDIMENTO REALIZADO EXIGE HABILITAÇÃO'

    if 'PROCEDIMENTO REALIZADO INCOMPATIVEL COM PROCEDIMENTO' in t_ascii:
        return 'PROCEDIMENTO REALIZADO INCOMPATÍVEL COM PROCEDIMENTO'

    if 'QUANTIDADE SUPERIOR A PERMITIDA' in t_ascii:
        return 'QUANTIDADE SUPERIOR À PERMITIDA'

    if 'QTD SUPERIOR AO MAXIMO PERMITIDO' in t_ascii:
        return 'QTD SUPERIOR AO MÁXIMO PERMITIDO'

    if 'HOSPITAL NAO POSSUI O SERVICO CLASSIFICACAO EXIGIDOS' in t_ascii:
        return 'HOSPITAL NÃO POSSUI O SERVICO/CLASSIFICACAO EXIGIDOS'

    if 'HOSPITAL NAO POSSUI LEITOS DE UTI II PEDIATRICA' in t_ascii:
        return 'HOSPITAL NÃO POSSUI LEITOS DE UTI II PEDIÁTRICA'

    if 'DIARIA DE SAUDE MENTAL EXIGE LANCAMENTO DE PROCED DE SAUDE MENTAL' in t_ascii:
        return 'DIÁRIA DE SAÚDE MENTAL EXIGE LANÇAMENTO DE PROCED. DE SAÚDE MENTAL'

    if 'QUANTIDADE INVALIDA' in t_ascii:
        return 'QUANTIDADE INVÁLIDA'

    if 'AIH BLOQUEADA POR DUPLICIDADER' in t_ascii:
        return 'AIH BLOQUEADA POR DUPLICIDADE'

    if 'AIH CANCELADA POR DUPL PROCED JA INCLUIDOS EM OUTRA AIH NESTE PROCESSAMENTO' in t_ascii:
        return 'AIH CANCELADA POR DUPL PROCE. JA INCLUIDAS EM OUTRO AIH NESTE PROCESSAMENTO'

    if 'DATA DA INTERNACAO DA AIH DIFERENTE DA AIH' in t_ascii:
        return 'DATA DA INTERNACAO DA AIH 5 DIFERENTE DA 1'

    if 'DIAGNOSTICO DA AIH DIFERENTE DA AIH' in t_ascii or 'DIAGNOSTICO PRINCIPAL DA AIH DIFERENTE DA AIH' in t_ascii:
        return 'DIAGNOSTICO PRINCIPAL DA AIH 5 DIFERENTE DA AIH1'

    if 'IMPLANTE DE CATETER COM CMPT EXECUCAO POSTERIOR A CMPT DE EXECUCAO DA HEMODIALISE' in t_ascii:
        return 'IMPLANTE DE CATETER COM CMPT EXECUCAO POSTERIOR A CMPT DE EXECUCAO DE HEMODIALISE'

    if 'QUANTIDADE DE APLICACOES SUPERIOR AO PERIODO DE INTERNACAO' in t_ascii:
        return 'QUANTIDADE DE APLICACOES SUPERIOR AO PERIODO DE INTERNACAO (PERIODO INTERN: 1 DIA(S))'

    if 'TERCEIRO NAO POSSUI SERVICO CLASSIFICACAO EXIGIDO' in t_ascii:
        return 'TERCEIRO NAO POSSUI O SERVICO/CLASSIFICACAO EXIGIDOS'

    if 'PROCEDIMENTO REALIZADO INCOMPATIVEL COM CIRURGIA RELACIONADA' in t_ascii:
        return 'PROCEDIMENTO REALIZADO INCOMPATIVEL COM CIRURGIA REALIZADA'

    if 'LANCAMENTO OBRIGATORIO DE OPM' in t_ascii:
        return 'LANÇAMENTO OBRIGATÓRIO DE OPM'

    if 'TOTAL DE DIARIAS SUPERIOR AO PERIODO DE INTERNACAO NA INFORMADA' in t_ascii:
        return 'TOTAL DE DIÁRIAS SUPERIOR AO PERÍODO DE INTERNAÇÃO NA COMPETÊNCIA'

    return text


def apply_review_overrides(motivo, filename, valor):
    filename_ascii = unicodedata.normalize('NFD', filename.upper())
    filename_ascii = ''.join(ch for ch in filename_ascii if unicodedata.category(ch) != 'Mn')

    if (
        'EDUARDO CAMPOS' in filename_ascii
        and abs(valor - 41.38) < 0.001
        and motivo == 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL'
    ):
        return 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL'

    return motivo


def _display_sidebar_logo():
    logo = Path('assets/combinado.png')
    if logo.exists():
        cols = st.sidebar.columns([0.5, 3, 0.5])
        cols[1].image(str(logo), width='stretch')
        st.sidebar.markdown('---')


def _display_header():
    st.title('🏥 Consolidador de Arquivos .QRP (Glosas)')
    st.markdown('O sistema converte os arquivos `.qrp` para texto mantendo a acentuação, limpa os códigos dos motivos, exclui duplicatas exatas e consolida os valores por Hospital.')


def get_valid_credentials():
    try:
        credentials = st.secrets.get('credentials')
        if credentials:
            return credentials
    except Exception:
        pass

    # Fallback para desenvolvimento local. Troque por valores reais antes de publicar.
    return {
        'ngr-ses': 'VPNses#'
    }


def check_credentials(username, password):
    valid_users = get_valid_credentials()
    return username in valid_users and password == valid_users[username]


def login():
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.sidebar.header('Acesso restrito')
    username = st.sidebar.text_input('Usuário', key='login_username')
    password = st.sidebar.text_input('Senha', type='password', key='login_password')
    if st.sidebar.button('Entrar'):
        if check_credentials(username, password):
            st.session_state.authenticated = True
            st.session_state.user = username
            if hasattr(st, 'rerun'):
                st.rerun()
            else:
                st.experimental_rerun()
        else:
            st.sidebar.error('Usuário ou senha incorretos.')

    st.sidebar.caption('Somente usuários autorizados podem acessar este app.')
    return False


def extract_utf16le_segments(raw_bytes, min_chars=1):  # Reduced min_chars
    allowed = set(range(32, 256)) | {9, 10, 13}  # Expanded to include more characters
    segments = []
    i = 0
    while i + 1 < len(raw_bytes):
        code = raw_bytes[i] | (raw_bytes[i + 1] << 8)
        if code in allowed:
            start = i
            chars = []
            while i + 1 < len(raw_bytes) and ((raw_bytes[i] | (raw_bytes[i + 1] << 8)) in allowed):
                chars.append(chr(raw_bytes[i] | (raw_bytes[i + 1] << 8)))
                i += 2
            if len(chars) >= min_chars:
                segments.append((start, ''.join(chars).strip()))
        else:
            i += 2
    return segments


def parse_qrp_bytes_to_records(raw_bytes, filename):
    records = []
    segments = extract_utf16le_segments(raw_bytes, min_chars=4)
    if not segments:
        return records

    hospital_name = "HOSPITAL DESCONHECIDO"
    cnes = ''
    competencia = ''
    hospital_regex = re.compile(
        r'(?:\bCNES\s*[:\-]?\s*)(\d{7})\s*-\s*([^\n\r]+)', re.IGNORECASE)
    hospital_fallback = re.compile(r'\b(\d{7})\s*-\s*(HOSPITAL.*)', re.IGNORECASE)
    competencia_regex = re.compile(r'\bCOMPETENCIA\s*[:\-]?\s*(0?[1-9]|1[0-2])/(\d{4})\b')

    ai_regex = re.compile(r'(?<!\d)(\d{13,14})(?!\d)')
    currency_regex = re.compile(r'\d{1,3}(?:\.\d{3})*,\d{2}')

    def extract_clean_aih(raw_aih):
        aih = re.sub(r'[^0-9]+$', '', raw_aih)
        if len(aih) == 14 and aih[-2] == aih[-1]:
            return aih[:13]
        return aih[:13] if len(aih) >= 13 else None

    def is_procedure_code(text):
        return bool(re.fullmatch(r'\d{8,10}', text.strip()))

    def is_date_segment(text):
        return bool(re.fullmatch(r'\d{2}/\d{2}/\d{4}', text.strip()))

    def aih_at_segment_start(text):
        return ai_regex.match(text.strip())

    for index, (_, seg) in enumerate(segments):
        hospital_match = hospital_regex.search(seg) or hospital_fallback.search(seg)
        if hospital_match:
            cnes, hospital_name = hospital_match.groups()
            hospital_name = hospital_name.strip()
        competencia_match = competencia_regex.search(remove_accents(seg.upper()))
        if competencia_match:
            month, year = competencia_match.groups()
            competencia = f'{int(month):02d}/{year}'
        aih_match = aih_at_segment_start(seg)
        if not aih_match:
            continue

        raw_aih = aih_match.group(1)
        aih = extract_clean_aih(raw_aih)
        if not aih:
            continue

        record_segments = []
        for _, next_seg in segments[index + 1:]:
            if aih_at_segment_start(next_seg):
                break
            record_segments.append(next_seg.strip())

        if not record_segments:
            continue

        currency_matches = [(i, m) for i, s in enumerate(record_segments) for m in [currency_regex.search(s)] if m]
        if not currency_matches:
            continue

        last_idx, last_match = max(currency_matches, key=lambda x: x[0])
        potential_value = last_match.group(0)
        try:
            valor = float(potential_value.replace('.', '').replace(',', '.'))
            # Allow zero and positive values (zero-value glosas are valid)
        except ValueError:
            continue

        motive_segments = record_segments[:last_idx]
        if motive_segments and is_procedure_code(motive_segments[0]):
            motive_segments = motive_segments[1:]
        while motive_segments and is_date_segment(motive_segments[-1]):
            motive_segments.pop()

        motivo_text = ' '.join(motive_segments).strip()
        if not motivo_text:
            continue

        motivo_text = clean_motivo_text(motivo_text)
        motivo_text = normalize_motivo(motivo_text)
        motivo_text = apply_review_overrides(motivo_text, filename, valor)
        motivo_text, motivo_reconhecido = officialize_motivo(motivo_text)

        records.append({
            'Arquivo': filename,
            'Hospital': hospital_name,
            'CNES': cnes,
            'Competência': competencia,
            'AIH': aih,
            'Motivo_Glosa': motivo_text,
            'Valor_Glosa': valor,
            'Motivo_Reconhecido': motivo_reconhecido
        })

    return records


def consolidate_records(df_unique):
    consolidated = df_unique.groupby(
        ['Hospital', 'CNES', 'Competência', 'Motivo_Glosa'], as_index=False, dropna=False
    ).agg(Valor_Glosa=('Valor_Glosa', 'sum'),
          Motivo_Reconhecido=('Motivo_Reconhecido', 'all'))
    consolidated = consolidated[consolidated['Valor_Glosa'] > 0].copy()
    consolidated = consolidated.sort_values(by=['Hospital', 'Valor_Glosa'], ascending=[True, False])
    consolidated['Status'] = consolidated['Motivo_Reconhecido'].map({True: 'Oficial', False: 'Novo'})
    return consolidated


def export_records_excel(df_consolidado, df_unique):
    output = io.BytesIO()
    details = ['Arquivo', 'Hospital', 'CNES', 'Competência', 'AIH', 'Motivo_Glosa', 'Valor_Glosa']
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_consolidado[['Hospital', 'CNES', 'Competência', 'Motivo_Glosa', 'Status', 'Valor_Glosa']].to_excel(
            writer, index=False, sheet_name='Consolidado')
        df_unique[details].to_excel(writer, index=False, sheet_name='Detalhamento das AIHs')
        review = df_unique[df_unique['Motivo_Reconhecido'] == False]
        if not review.empty:
            review[details].to_excel(writer, index=False, sheet_name='Motivos para Revisão')
    return output.getvalue()

def run_streamlit_app():
    st.set_page_config(page_title="Consolidador de Glosas", page_icon="🏥", layout="wide")

    _display_sidebar_logo()

    if not login():
        return

    st.sidebar.success(f"Autenticado como {st.session_state.user}")

    if st.sidebar.button('Sair'):
        st.session_state.authenticated = False
        st.session_state.user = None
        if hasattr(st, 'rerun'):
            st.rerun()
        else:
            st.experimental_rerun()

    _display_header()
    st.markdown('###')

    uploaded_files = st.file_uploader("Arraste os arquivos .qrp aqui", type=['qrp'], accept_multiple_files=True)

    if uploaded_files:
        if st.button("Processar Arquivos", type="primary"):
            all_records = []
            
            with st.spinner('Convertendo o relatório para texto puro e extraindo os dados...'):
                for file in uploaded_files:
                    bytes_data = file.read()
                    records = parse_qrp_bytes_to_records(bytes_data, file.name)
                    all_records.extend(records)
            
            if not all_records:
                st.error("Nenhum dado válido encontrado. Certifique-se de que os arquivos contêm AIHs.")
            else:
                df = pd.DataFrame(all_records)
                
                # Remover duplicatas por Hospital+AIH+Valor, mantendo o primeiro motivo encontrado.
                df_unique = drop_duplicate_glosa_records(df)
                df_motivos_revisao = df_unique[df_unique['Motivo_Reconhecido'] == False]

                df_consolidado = consolidate_records(df_unique)
                if df_unique[['CNES', 'Competência']].eq('').any().any():
                    st.warning('Alguns registros estão sem CNES ou competência no cabeçalho do QRP. Esses campos ficaram em branco; confira os arquivos de origem.')

                # Formatação financeira PT-BR
                df_consolidado['Valor Formatado'] = df_consolidado['Valor_Glosa'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                )

                st.success("Tabela gerada com sucesso! Sem códigos e com acentuação corrigida.")
                if not df_motivos_revisao.empty:
                    st.warning(f"{len(df_motivos_revisao)} ocorrência(s) com motivo novo, fora da lista oficial. Elas aparecem destacadas na tabela e também na aba 'Motivos para Revisão' do Excel.")
                
                # Métricas em destaque na tela
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Total de Ocorrências Válidas:** {len(df_unique)}")
                    st.caption("Duplicatas por Hospital+CNES+Competência+AIH+Valor removidas, mantendo o primeiro motivo. Pares validados pela equipe são separados quando aplicável.")
                with col2:
                    total = df_consolidado['Valor_Glosa'].sum()
                    st.warning(f"**Soma Total Consolidada:** R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                
                df_visualizacao = df_consolidado[['Hospital', 'CNES', 'Competência', 'Motivo_Glosa', 'Status', 'Valor Formatado']]
                st.dataframe(
                    df_visualizacao.style.apply(highlight_new_motivos, axis=1),
                    use_container_width=True
                )
                
                # Geração do arquivo Excel
                processed_data = export_records_excel(df_consolidado, df_unique)
                
                st.download_button(
                    label="📥 Baixar Planilha Consolidada (.xlsx)",
                    data=processed_data,
                    file_name="Relatorio_Glosas_Consolidado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


if __name__ == '__main__':
    run_streamlit_app()
