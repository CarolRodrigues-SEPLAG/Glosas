import streamlit as st
import pandas as pd
import re
import io
import unicodedata
from pathlib import Path

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
    # Removido: text = re.sub(r'\([^)]*\)', ' ', text)  # Agora mantemos os códigos entre parênteses
    text = re.sub(r'\b\d{2}/\d{2}/\d{4}\b', ' ', text)
    text = re.sub(r'\b\d{1,3}(?:\.\d{3})*,\d{2}\b', ' ', text)
    text = re.sub(r'\b\d+\b', ' ', text)
    lixos = ['SISTEMA', 'DATASUS', 'SECRETARIA', 'ESTADUAL', 'HOSPITALARES',
             'DEFINITIVO', 'MENSAGEM DE ERRO', 'VALOR PRÉVIA', 'MUNICÍPIO',
             'RECIFE', 'LINHA', 'LOTE', 'COMPETÊNCIA', 'PÁGINA', 'GESTOR',
             'VALOR', 'PRÉVIA', 'PRINCIPAL', 'ALTA', 'SIHD', 'ARIAL', 'FONTE']
    for lx in lixos:
        text = re.compile(r'\b' + lx + r'\b', re.IGNORECASE).sub(' ', text)
    text = re.sub(r'\([^)]*\)', lambda m: m.group(0) if 'DOC:' in m.group(0).upper() else m.group(0), text)
    text = re.sub(r'\(\s*DOC\s*\)', ' ', text, flags=re.IGNORECASE)
    text = re.sub(r'\(\s*\)', ' ', text)
    text = re.sub(r'[^A-Za-zÇÃÕÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙçãõáéíóúâêîôûàèìòù\s\-\/\.()]+', ' ', text)  # Adicionado () para manter parênteses
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+[A-Za-zÇÃÕÁÉÍÓÚÂÊÎÔÛÀÈÌÒÙçãõáéíóúâêîôûàèìòù]$', '', text)
    text = re.sub(r'[\s\-\./,;:]+$', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'\s+OU\s*$', '', text, flags=re.IGNORECASE)
    return text


def normalize_motivo(text):
    t = text.upper()

    def accentless(value):
        normalized = unicodedata.normalize('NFD', value)
        return ''.join(ch for ch in normalized if unicodedata.category(ch) != 'Mn')

    t_ascii = re.sub(r'[^A-Z0-9 ]+', ' ', accentless(t))
    t_ascii = re.sub(r'\s+', ' ', t_ascii).strip()

    # Extrair códigos entre parênteses para usar como marcadores
    paren_codes = re.findall(r'\(([^)]+)\)', text.upper())
    paren_text = ' '.join(paren_codes)

    # Regras baseadas em códigos entre parênteses
    if 'DESACORDO COM CF-88' in paren_text or 'PROF COM MAIS 2 VINC PUBL' in paren_text:
        return 'PROFISSIONAL COM MAIS DE 2 VINC. PÚBLICOS (DESACORDO COM CF-88) OU PROFISSIONAL COM CH MAIOR QUE 168h POR SEMANA'

    if 'DOC:' in paren_text or 'DOCUMENTO' in paren_text:
        return 'PROFISSIONAL VINCULADO NÃO CADASTRADO'

    # Regras existentes
    if 'PROFISSIONAL AUTONOMO' in t_ascii or 'PROFISSIONAL AUTO NOMO' in t_ascii:
        return 'PROFISSIONAL AUTÔNOMO NÃO CADASTRADO NO HOSPITAL COM CBO INFORMADO'

    if 'PROFISSIONAL VINCULADO' in t_ascii and 'NAO CADASTRADO' in t_ascii:
        return 'PROFISSIONAL VINCULADO NÃO CADASTRADO'

    if 'PROFISSIONAL NAO VINCULADO AO CNES' in t_ascii:
        return 'PROFISSIONAL NÃO VINCULADO AO CNES COM O CBO INFORMADO'

    if 'AIH BLOQUEADA EM OUTRO PROCESSAMENTO' in t_ascii:
        return 'AIH BLOQUEADA EM OUTRO PROCESSAMENTO'

    if 'AIH APROVADA EM OUTRO PROCESSAMENTO' in t_ascii:
        return 'AIH APROVADA EM OUTRO PROCESSAMENTO'

    if 'DESACORDO COM CF' in t_ascii or 'CF-' in t_ascii or 'PROF COM MAIS' in t_ascii and 'VINC' in t_ascii and 'PUBL' in t_ascii:
        return 'PROFISSIONAL COM MAIS DE 2 VINC. PÚBLICOS (DESACORDO COM CF-88) OU PROFISSIONAL COM CH MAIOR QUE 168h POR SEMANA'

    if 'DUPL INTERNA O C INTERSERC O DE PERIODOS' in t_ascii or 'DUPL INTERNACAO C INTERSERCAO DE PERIODOS' in t_ascii:
        return 'AIH BLOQUEADA POR DUPL.INTERNAÇÃO C/INTERSERCÃO DE PERÍODOS'

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
        return 'HOSPITAL NÃO POSSUI LEITOS DE UTI II PEDIATRICA'

    if 'DIARIA DE SAUDE MENTAL EXIGE LANCAMENTO DE PROCED DE SAUDE MENTAL' in t_ascii:
        return 'DIÁRIA DE SAÚDE MENTAL EXIGE LANÇAMENTO DE PROCED. DE SAÚDE MENTAL'

    if 'QUANTIDADE INVALIDA' in t_ascii:
        return 'QUANTIDADE INVÁLIDA'

    if 'TOTAL DE DIARIAS SUPERIOR AO PERIODO DE INTERNACAO NA INFORMADA' in t_ascii:
        return 'TOTAL DE DIÁRIAS SUPERIOR AO PERÍODO DE INTERNAÇÃO NA INFORMADA'

    return text


def _display_sidebar_logo():
    logo = Path('assets/combinado.png')
    if logo.exists():
        st.sidebar.image(str(logo), width=220)


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
    for _, seg in segments:
        if 'HOSPITAL' in seg.upper() or 'CNES' in seg.upper():
            match = re.search(r'CNES\s*[:\-]?\s*\d+\s*-\s*([^\n\r]+)', seg, re.IGNORECASE)
            if match:
                hospital_name = match.group(1).strip()
                break
            match = re.search(r'\b\d{7}\s*-\s*(HOSPITAL.*)', seg, re.IGNORECASE)
            if match:
                hospital_name = match.group(1).strip()
                break

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

    for index, (_, seg) in enumerate(segments):
        aih_match = ai_regex.search(seg)
        if not aih_match:
            continue

        raw_aih = aih_match.group(1)
        aih = extract_clean_aih(raw_aih)
        if not aih:
            continue

        record_segments = []
        for _, next_seg in segments[index + 1:]:
            if ai_regex.search(next_seg):
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

        records.append({
            'Arquivo': filename,
            'Hospital': hospital_name,
            'AIH': aih,
            'Motivo_Glosa': motivo_text,
            'Valor_Glosa': valor
        })

    return records

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
                
                # Remover duplicatas por AIH + Valor (mesma glosa repetida)
                df_unique = df.drop_duplicates(subset=['Hospital', 'AIH', 'Valor_Glosa'], keep='first')
                
                # CONSOLIDAÇÃO: Agrupar por Hospital e Motivo
                df_consolidado = df_unique.groupby(['Hospital', 'Motivo_Glosa'], as_index=False)['Valor_Glosa'].sum()
                df_consolidado = df_consolidado[df_consolidado['Valor_Glosa'] > 0]
                df_consolidado = df_consolidado.sort_values(by=['Hospital', 'Valor_Glosa'], ascending=[True, False])
                
                # Formatação Financeira PT-BR
                df_consolidado['Valor Formatado'] = df_consolidado['Valor_Glosa'].apply(
                    lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                )
                
                st.success("Tabela gerada com sucesso! Sem códigos e com acentuação corrigida.")
                
                # Métricas em destaque na tela
                col1, col2 = st.columns(2)
                with col1:
                    st.info(f"**Total de Ocorrências Válidas:** {len(df_unique)}")
                    st.caption(f"Duplicadas por Hospital+AIH+Valor removidas (mesma glosa com motivo levemente diferente).")
                with col2:
                    total = df_consolidado['Valor_Glosa'].sum()
                    st.warning(f"**Soma Total Consolidada:** R$ {total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'))
                
                st.dataframe(df_consolidado[['Hospital', 'Motivo_Glosa', 'Valor Formatado']], use_container_width=True)
                
                # Geração do arquivo Excel
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df_consolidado[['Hospital', 'Motivo_Glosa', 'Valor_Glosa']].to_excel(writer, index=False, sheet_name='Consolidado')
                    df_unique[['Arquivo', 'Hospital', 'AIH', 'Motivo_Glosa', 'Valor_Glosa']].to_excel(
                        writer, index=False, sheet_name='Detalhamento das AIHs')
                
                processed_data = output.getvalue()
                
                st.download_button(
                    label="📥 Baixar Planilha Consolidada (.xlsx)",
                    data=processed_data,
                    file_name="Relatorio_Glosas_Consolidado.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )


if __name__ == '__main__':
    run_streamlit_app()