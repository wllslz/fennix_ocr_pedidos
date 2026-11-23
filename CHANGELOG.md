# Histórico de Versões (Changelog)

Registro cronológico desde o primeiro commit do repositório (9 commits).

## 1. 0bbefe2 (2026-11-23) - feat: sistema Django OCR de pedidos pronto para Vercel e WhatsApp
- **Autor:** Willian Lira de Souza
- **Resumo:** Implementação e ajustes na estrutura Django, leitura OCR, manipulação de planilhas .xlsx ou interface.

## 2. 62dfd77 (2026-11-23) - fix: inicializa SQLite no /tmp apos carregar apps Django na Vercel
- **Autor:** Willian Lira de Souza
- **Resumo:** Implementação e ajustes na estrutura Django, leitura OCR, manipulação de planilhas .xlsx ou interface.

## 3. 8f03c23 (2026-11-23) - fix: restaura roteamento WSGI na Vercel preservando PATH_INFO original
- **Autor:** Willian Lira de Souza
- **Resumo:** Implementação e ajustes na estrutura Django, leitura OCR, manipulação de planilhas .xlsx ou interface.

## 4. 5921e23 (2026-11-23) - fix(excel-service): corrige analise de estrutura, validacoes de entrada, seguranca e docs
- **Autor:** Willian Lira de Souza
- **Resumo:** Corrige o retorno de analisar_estrutura_planilha (aba_destino, mapeamento e linha_cabecalho), amplia a detecção de cabeçalhos, reforça validações de upload/JSON/mapeamento e ajusta formatação monetária no OpenPyXL.

## 5. 0f6d0ad (2026-11-23) - docs: aprofunda README e detalha historico completo no CHANGELOG
- **Autor:** Willian Lira de Souza
- **Resumo:** Implementação e ajustes na estrutura Django, leitura OCR, manipulação de planilhas .xlsx ou interface.

## 6. 0ac6d39 (2026-11-23) - docs(changelog): gera historico completo de commits desde o inicio do repositorio
- **Autor:** Willian Lira de Souza
- **Resumo:** Organiza o histórico completo de commits no CHANGELOG.md desde o início do repositório e atualiza o README.md.

## 7. cdbf578 (2026-11-23) - feat(ocr-lote): adiciona backoff para HTTP 429 e documenta processamento de varias imagens
- **Autor:** Willian Lira de Souza
- **Resumo:** Atualiza tratamento de requisições no OCR e documenta o fluxo de processamento de imagens.

## 8. 3009f02 (2026-11-23) - feat(ocr): requisicao unica por imagem, extracao minuciosa, botao reiniciar e docs
- **Autor:** Willian Lira de Souza
- **Resumo:** Define requisição única por imagem em ocr_engine.py, refina a extração minuciosa em field_extractor.py, adiciona destaque visual para campos vazios e botão Limpar e Reiniciar Tudo.

## 9. Entrega Atual - fix(lote-paste): reaproveita lote_id no envio sequencial e normaliza prints colados
- **Resumo:** Reaproveita o LoteProcessamento em processar_lote quando lote_id é enviado (garantindo exportação consolidada de todas as imagens processadas 1 a 1) e normaliza prints colados via Ctrl+V como File com extensão válida no dashboard.html.

