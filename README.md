# Fennix OCR Pedidos

Sistema web em **Django** para leitura de comprovantes de pedidos via OCR, mapeamento de planilhas `.xlsx` com **OpenPyXL**, conferência manual e exportação consolidada.

## Contexto e Objetivo

Na rotina de expedição, comprovantes e telas de pedidos chegam em formato de imagem (fotos e capturas de tela). O sistema resolve três problemas operacionais:

1. **Transcrição manual:** Substitui a digitação repetitiva de `Cliente`, `Pedido`, `Peso (Kg)` e `Total (R$)` por leitura automática com revisão antes da gravação.
2. **Diferenças entre planilhas:** Inspeciona abas e cabeçalhos dinamicamente em arquivos `.xlsx` em vez de depender de colunas fixas.
3. **Controle de requisições:** Executa apenas uma requisição de OCR por imagem, processando uma imagem por vez para evitar sobrecarga e facilitar a conferência item a item.

## Funcionalidades Principais

- **Análise estrutural de planilhas (`.xlsx`):** Valida extensão, tamanho (até 25 MB) e assinatura `PK\x03\x04`, identifica a linha de cabeçalho, sugere a aba de destino (priorizando `BASE`) e mapeia as colunas (`cliente`, `pedido`, `peso`, `total`, `data`, `mes`, `tipo_expedicao`, `status_separacao` e `responsavel`).
- **Mapeamento ajustável:** Permite revisar e salvar a aba de destino e as letras das colunas antes da exportação.
- **Leitura OCR individual e verificação minuciosa:** Processa uma imagem por vez com requisição única, extrai os campos principais (incluindo valores totais com quebra de linha ou formatos decimais variados) e destaca visualmente em vermelho qualquer campo vazio que exija revisão.
- **Conferência, reinício rápido e exportação:** Permite editar valores na tabela, limpar todos os dados da tela pelo botão **Limpar e Reiniciar Tudo** e gerar a planilha `.xlsx` atualizada com os pedidos aprovados.

## Estrutura do Projeto

```text
fennix_ocr_pedidos/
├── fennix_ocr_pedidos/          # Configurações principais do projeto Django
├── pedidos/
│   ├── models.py                # PlanilhaModelo, LoteProcessamento e PedidoExtraido
│   ├── forms.py                 # Validação de planilhas .xlsx e imagens
│   ├── views.py                 # Rotas de upload, mapeamento, OCR e exportação
│   └── services/
│       ├── image_processor.py   # Tratamento prévio das imagens
│       ├── ocr_engine.py        # Execução via Tesseract local ou API OCR (requisição única)
│       ├── field_extractor.py   # Extração e validação de Cliente, Pedido, Peso e Total
│       └── excel_service.py     # Inspeção e gravação em planilhas com OpenPyXL
├── templates/pedidos/
│   └── dashboard.html           # Painel operacional de conferência
├── CHANGELOG.md                 # Histórico completo de commits do repositório
└── README.md

## Validações e Segurança

- **Verificação de arquivos:** Checagem de extensão, limite de tamanho e assinatura binária (magic bytes) para arquivos .xlsx, JPG, PNG e WEBP.
- **Proteção de caminhos e parâmetros:** Sanitização de nomes de arquivos com os.path.basename e validação de letras de coluna com regex ^[A-Z]{1,3}$.
- **Tratamento de respostas HTTP:** Validação de JSON no backend (HTTP 400 para payload inválido) e leitura segura de respostas no frontend (lerJsonSeguro).

## Execução Local

1. Clone o repositório e acesse a pasta fennix_ocr_pedidos.
2. Crie e ative o ambiente virtual Python (venv).
3. Instale as dependências com pip install -r requirements.txt.
4. Execute python manage.py migrate e inicie com python manage.py runserver.

O histórico completo de versões está registrado em CHANGELOG.md.
