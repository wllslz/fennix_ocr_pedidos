# Histórico de Versões (Changelog)

Registro cronológico desde o primeiro commit do repositório (10 commits).

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

## 10. Entrega Atual - fix(export-fila): gera planilha base automatica para download e exibe fila multipla visual
- **Resumo:** Garante criação automática de planilha base quando nenhum .xlsx prévio foi enviado, corrige o caminho relativo ao MEDIA_ROOT para habilitar sempre o botão Baixar Planilha Atualizada (.XLSX) e adiciona visualização e gerenciamento de múltiplas imagens na fila antes do OCR.

