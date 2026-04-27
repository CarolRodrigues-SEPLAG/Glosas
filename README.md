# Consolidador de Glosas .QRP

Esta aplicação web permite carregar arquivos .qrp (relatórios de glosas do SUS), processa os dados e gera uma planilha consolidada com nome do hospital, motivo de glosa (sem códigos) e valor total.

## Funcionalidades

- Upload de múltiplos arquivos .qrp
- Extração automática de dados: hospital, AIH, motivo de glosa, valor
- Limpeza dos motivos (remove códigos entre parênteses)
- Remoção de duplicatas (mesmo AIH e valor)
- Consolidação por hospital e motivo
- Download da planilha Excel

## Como executar

1. Instale as dependências:
   ```
   pip install -r requirements.txt
   ```

2. Execute a aplicação:
   ```
   streamlit run app.py
   ```

3. Abra o navegador no endereço indicado (geralmente http://localhost:8501)

## Uso

1. Arraste os arquivos .qrp para a área de upload
2. Clique em "Processar Arquivos"
3. Visualize a tabela consolidada
4. Baixe a planilha Excel com os dados consolidados