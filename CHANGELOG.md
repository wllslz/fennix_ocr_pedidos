# Histórico de Versões (Changelog)

Registro cronológico desde o primeiro commit do repositório (13 commits).

## 1. 0bbefe2 (2026-11-23) - feat: sistema Django OCR de pedidos pronto para Vercel e WhatsApp
- **Autor:** Willian Lira de Souza

## 2. 62dfd77 (2026-11-23) - fix: inicializa SQLite no /tmp apos carregar apps Django na Vercel
- **Autor:** Willian Lira de Souza

## 3. 8f03c23 (2026-11-23) - fix: restaura roteamento WSGI na Vercel preservando PATH_INFO original
- **Autor:** Willian Lira de Souza

## 4. 5921e23 (2026-11-23) - fix(excel-service): corrige analise de estrutura, validacoes de entrada, seguranca e docs
- **Autor:** Willian Lira de Souza

## 5. 0f6d0ad (2026-11-23) - docs: aprofunda README e detalha historico completo no CHANGELOG
- **Autor:** Willian Lira de Souza

## 6. 0ac6d39 (2026-11-23) - docs(changelog): gera historico completo de commits desde o inicio do repositorio
- **Autor:** Willian Lira de Souza

## 7. cdbf578 (2026-11-23) - feat(ocr-lote): adiciona backoff para HTTP 429 e documenta processamento de varias imagens
- **Autor:** Willian Lira de Souza

## 8. 3009f02 (2026-11-23) - feat(ocr): requisicao unica por imagem, extracao minuciosa, botao reiniciar e docs
- **Autor:** Willian Lira de Souza

## 9. e0af703 (2026-11-23) - fix(lote-paste): reaproveita lote_id no envio sequencial e normaliza prints colados
- **Autor:** Willian Lira

## 10. dd7e848 (2026-11-23) - fix(export-fila): gera planilha base automatica para download e exibe fila multipla visual
- **Autor:** Willian Lira

## 11. a54d1df (2026-11-23) - feat(planilha-feedback): adiciona retorno visual ao analisar e atualizar estrutura da planilha
- **Autor:** Willian Lira

## 12. 12d164b (2026-11-23) - fix(excel-preenchimento): garante gravacao na planilha, preserva mapeamento real e exibe retorno visual da estrutura
- **Autor:** Willian Lira

## 13. Entrega Atual - fix(models-sync): alinha campos arquivo_original, arquivo_exportado e status_planilha nas views
- **Resumo:** Corrige AttributeError em upload_planilha, confirmar_exportacao e baixar_planilha substituindo arquivo_modelo por arquivo_original, tratando arquivo_exportado como CharField e atualizando status_planilha/linha_inserida conforme pedidos/models.py.

