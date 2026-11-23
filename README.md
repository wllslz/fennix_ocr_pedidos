# Fennix OCR Pedidos — Extração de Pedidos por OCR, Análise de Planilhas e Exportação

Aplicação web em **Django** para a rotina de expedição e monitoramento de pedidos, combinando leitura automatizada de comprovantes/imagens via **OCR**, análise estrutural de planilhas `.xlsx` com **OpenPyXL**, revisão humana e exportação consolidada.

## Porquê o Sistema Foi Criado

Na rotina operacional de expedição e acompanhamento de pedidos, comprovantes, telas de pedido e resumos chegam frequentemente por imagem (fotos ou prints enviados pelo WhatsApp). Transcrever esses dados manualmente para a planilha e conferir onde cada informação deve entrar traz gargalos práticos:

- **Retrabalho e erro humano:** Digitar manualmente número de cliente, número de pedido, peso e valor total de vários pedidos em sequência toma tempo e favorece trocas de dígitos ou separadores decimais.
- **Variação de estrutura entre planilhas:** Planilhas `.xlsx` nem sempre têm cabeçalho na linha 1 ou mantêm as colunas sempre nas mesmas letras; depender de posições fixas sem analisar a estrutura pode inserir dados em colunas ou abas erradas.
- **Conferência humana antes da gravação:** A leitura por OCR agiliza o preenchimento, mas o conferente precisa revisar, corrigir se necessário e aprovar os registros antes de alterar ou exportar a planilha.

## Como Foi Construído e Decisões de Engenharia

- **Backend Django (`pedidos/`):** Estruturado com modelos (`PlanilhaModelo`, `LoteProcessamento`, `PedidoExtraido`), formulários e validadores (`forms.py`), views HTTP/AJAX (`views.py`) e painel web (`templates/pedidos/dashboard.html`).
- **Análise e escrita com OpenPyXL (`pedidos/services/excel_service.py`):** Carrega o arquivo `.xlsx`, normaliza cabeçalhos removendo acentos e espaços (`normalizar_texto`), pontua linhas candidatas a cabeçalho, mapeia sinônimos (`ALIASES_CAMPOS`) para letras de coluna (`get_column_letter`), identifica linhas ocupadas ou vagas pré-datadas, gera backup antes da gravação e insere os pedidos aprovados.
- **Pipeline de imagem, OCR e extração (`image_processor.py`, `ocr_engine.py`, `field_extractor.py`):** Pré-processa a imagem recebida, executa o OCR e extrai/padroniza números e valores decimais no formato brasileiro (`parse_decimal_br`).

## O Que o Aplicativo Faz

1. **Upload e análise estrutural de planilhas (`.xlsx`):** Valida extensão, tamanho e assinatura `PK\x03\x04`, varre abas, identifica a linha do cabeçalho e mapeia colunas (`cliente`, `pedido`, `peso`, `total`, `data`, `mes`, `tipo_expedicao`, `status_separacao`, `responsavel`), priorizando a aba `BASE` quando disponível.
2. **Ajuste de mapeamento:** Permite conferir e atualizar a aba de destino e as letras das colunas no painel.
3. **Processamento em lote de imagens:** Valida imagens (`JPG`, `PNG`, `WEBP`), executa OCR por item e classifica o status (`OK`, pendente ou `ERRO`) com texto bruto e observações.
4. **Revisão e exportação da planilha:** Permite editar campos extraídos, aprovar registros e gerar a planilha `.xlsx` atualizada.

## Arquitetura, Segurança e Execução

- **Fluxo:** `dashboard.html` -> `POST /upload-planilha/` (`analisar_estrutura_planilha`) -> `POST /atualizar-mapeamento/` -> `POST /processar-lote/` (`OCR` + `field_extractor`) -> `POST /confirmar-exportacao/` (`inserir_pedidos_na_planilha`).
- **Segurança:** Validação de extensão, tamanho e *magic bytes*, sanitização de nomes de arquivo com `os.path.basename`, validação de letras de coluna (`^[A-Z]{1,3}$`) e respostas JSON seguras (`400` em JSON inválido e `lerJsonSeguro` no frontend).
- **Histórico completo:** Veja [`CHANGELOG.md`](./CHANGELOG.md) com todos os commits desde o início do repositório.

```bash
cd fennix_ocr_pedidos
python -m venv venv
source venv/Scripts/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver

## Processamento em Lote e Resiliência a Rate Limit (HTTP 429)

- **Múltiplas imagens por lote:** Permite selecionar, colar (`Ctrl + V`) ou arrastar várias imagens de uma vez para a fila (`filaArquivosWhatsApp`) e enviá-las juntas em um único lote para `/processar-lote/`.
- **Retentativa com espera (*backoff*):** Em `_ocr_cloud_api` (`pedidos/services/ocr_engine.py`), quando a API externa retorna `HTTP 429` (*Too Many Requests*) ou instabilidade temporária, o sistema aguarda (`Retry-After` ou espera progressiva) e tenta novamente automaticamente antes de registrar falha.
