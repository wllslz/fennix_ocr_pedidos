# Changelog

Todas as mudanças notáveis deste projeto serão documentadas neste arquivo.

## [1.1.0] - 2026-11-25

### Adicionado
- Pré-processamento de imagem no navegador via HTML5 Canvas (`upscale`, escala de cinza, ajuste de contraste e binarização leve) integrado ao Tesseract.js (`por+eng`).
- Recortes direcionados por regiões do layout do pedido (`topoDir`, `clienteEsq`, `totais` e imagem completa) com `tessedit_char_whitelist` para aumentar a precisão na leitura de campos numéricos.
- Exibição detalhada do resumo extraído (`Cód. Cliente`, `Pedido`, `Peso`, `Total`) e do texto bruto reconhecido pelo OCR na caixa de status.

### Alterado
- Extração de **Código do Cliente** (ex.: `14660`) em substituição ao nome do cliente.
- Extração do **Nº Pedido** focada em sequências numéricas após o rótulo `Pedido` / topo direito (ex.: `4731000665`), evitando capturas incorretas como trechos do cabeçalho/logo (`FENNIX`).
- Controle do botão **Baixar .xlsx atualizado**, que permanece desabilitado até que a planilha base (`.xlsx` com a aba `BASE `) seja carregada e ao menos um pedido seja adicionado na sessão.
- Configuração estática em `vercel.json` com `"framework": null`, `"buildCommand": null` e `"outputDirectory": "public"` para evitar detecção indevida do preset Django no deploy client-side.

### Corrigido
- Falhas de build na Vercel (`[DJANGO_ENTRYPOINT_NOT_FOUND]`) causadas pela detecção residual de projeto Django.
- Leitura trocada do número do pedido e ausência do código numérico do cliente em prints de pedidos da Fennix.
