# Fennix OCR Pedidos — Extração de Pedidos por OCR, Análise de Planilhas e Exportação

Aplicação web em **Django** para a rotina de expedição e monitoramento de pedidos, unindo leitura de comprovantes/imagens via **OCR**, inspeção e mapeamento estrutural de planilhas `.xlsx`, conferência humana e gravação consolidada com **OpenPyXL**.

## Porquê o Sistema Foi Criado

Na rotina de expedição e acompanhamento de pedidos, comprovantes, capturas de tela e resumos chegam frequentemente como imagem (fotos e prints enviados no WhatsApp). Fazer a transcrição manual para a planilha e conferir onde cada informação entra gera gargalos recorrentes:

- **Retrabalho e erro de digitação:** Digitar manualmente número de cliente, número de pedido, peso e valor total de vários pedidos em sequência consome tempo e favorece trocas de dígitos ou separadores decimais.
- **Variação de estrutura entre planilhas:** Planilhas `.xlsx` nem sempre têm o cabeçalho na linha 1 ou mantêm as colunas nas mesmas letras; depender de posições fixas sem analisar a estrutura pode inserir dados em colunas ou abas incorretas.
- **Conferência humana antes da gravação:** A automação acelera a leitura, mas o conferente precisa revisar, corrigir e aprovar os registros antes de alterar ou exportar a planilha.

## Como Foi Construído e Decisões de Engenharia

- **Backend Django (`pedidos/`):** Organizado com modelos (`PlanilhaModelo`, `LoteProcessamento`, `PedidoExtraido`), formulários e validadores (`forms.py`), views HTTP/AJAX (`views.py`) e painel operacional (`templates/pedidos/dashboard.html`).
- **Inspeção e gravação com OpenPyXL (`pedidos/services/excel_service.py`):** Carrega o arquivo `.xlsx`, normaliza cabeçalhos removendo acentos e espaços extras (`normalizar_texto`), pontua linhas candidatas a cabeçalho, associa sinônimos (`ALIASES_CAMPOS`) às letras de coluna (`get_column_letter`), localiza linhas ocupadas ou vagas pré-datadas e insere os pedidos aprovados criando backup prévio.
- **Pipeline de imagem e OCR (`image_processor.py`, `ocr_engine.py`, `field_extractor.py`):** Pré-processa a imagem recebida, executa o reconhecimento óptico de caracteres e extrai/padroniza números e valores no padrão brasileiro (`parse_decimal_br`).

## O Que o Aplicativo Faz

1. **Upload e análise estrutural de planilhas (`.xlsx`):** Valida extensão, tamanho e assinatura `PK\x03\x04`, varre abas, detecta linha de cabeçalho e mapeia colunas (`cliente`, `pedido`, `peso`, `total`, `data`, `mes`, `tipo_expedicao`, `status_separacao`, `responsavel`), priorizando a aba `BASE` quando disponível.
2. **Ajuste de mapeamento:** Permite revisar e atualizar a aba de destino e as letras das colunas no painel.
3. **Processamento em lote de imagens:** Valida imagens (`JPG`, `PNG`, `WEBP`), executa OCR por item e classifica o status (`OK`, pendente ou `ERRO`) com texto bruto e observações.
4. **Revisão e exportação da planilha:** Permite editar campos, aprovar registros e gerar a planilha `.xlsx` atualizada.

## Arquitetura, Segurança e Execução

- **Fluxo:** `dashboard.html` -> `POST /upload-planilha/` (`analisar_estrutura_planilha`) -> `POST /atualizar-mapeamento/` -> `POST /processar-lote/` (`OCR` + `field_extractor`) -> `POST /confirmar-exportacao/` (`inserir_pedidos_na_planilha`).
- **Segurança:** Validação de extensão, tamanho e *magic bytes*, sanitização de nomes com `os.path.basename`, validação de letras de coluna (`^[A-Z]{1,3}$`) e respostas JSON seguras (`400` em JSON inválido e `lerJsonSeguro` no frontend).
- **Histórico completo:** Veja [`CHANGELOG.md`](./CHANGELOG.md) com todos os commits desde o início do repositório.

```bash
cd fennix_ocr_pedidos
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
