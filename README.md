# Fennix OCR Pedidos

Aplicação web estática (client-side) para extrair dados de prints de pedidos via OCR no navegador e inserir novas linhas na aba **`BASE `** de planilhas `.xlsx`, preservando a estrutura XML, estilos e dimensões originais do arquivo.

## Funcionalidades
- **OCR no navegador com Tesseract.js + Canvas:** aplica ampliação, escala de cinza, contraste e binarização leve, além de recortes direcionados para campos numéricos.
- **Extração focada em dados operacionais:**
  - **Código do Cliente** (ex.: `14660`)
  - **Nº Pedido** (ex.: `4731000665`)
  - **Peso (kg)** (ex.: `20,16`)
  - **Total (R$)** (ex.: `359,89`)
- **Edição segura de `.xlsx` via JSZip + XML:** localiza a aba `BASE ` por `xl/workbook.xml` e `xl/_rels/workbook.xml.rels`, anexa novas linhas em `<sheetData>`, atualiza `<dimension>` e preserva estilos (`s="..."`).
- **Bloqueio de download até inclusão de itens:** o botão **Baixar .xlsx atualizado** só é habilitado após carregar a planilha base e adicionar pelo menos um pedido.

## Como usar
1. Abra a aplicação em produção na Vercel ou sirva a pasta `public/` localmente.
2. Selecione a planilha base `.xlsx` contendo a aba `BASE `.
3. Selecione uma ou mais imagens de pedidos para executar o OCR e revisar os campos preenchidos.
4. Clique em **Adicionar à BASE** para registrar o pedido na sessão e atualizar a planilha em memória.
5. Clique em **Baixar .xlsx atualizado** para salvar o arquivo gerado.

## Deploy e infraestrutura
- **Repositório:** `https://github.com/wllslz/fennix_ocr_pedidos.git`
- **Produção (Vercel):** `https://fennixocrpedidos-nine.vercel.app`
- **Configuração (`vercel.json`):** serve `public/index.html` como site estático com `"framework": null`, `"buildCommand": null` e `"outputDirectory": "public"`.
