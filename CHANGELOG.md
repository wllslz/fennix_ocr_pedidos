# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

O formato é baseado em Keep a Changelog ([https://keepachangelog.com/pt-BR/1.1.0/](https://keepachangelog.com/pt-BR/1.1.0/)),
e este projeto adere ao Versionamento Semântico ([https://semver.org/lang/pt-BR/](https://semver.org/lang/pt-BR/)).

## [1.0.0] - 2026-11-23

### Adicionado
- **Arquitetura 100% Client-Side:** Processamento completo de imagens e planilhas executado localmente no navegador via Tesseract.js (idioma por) e SheetJS (xlsx).
- **Worker OCR Reutilizável & Normalização de Contraste:** Instância única de worker para lotes e normalização de fundo cinza sombreado no Canvas, preservando a leitura do campo Peso (Kg) em prints comprimidos do WhatsApp.
- **Exportação Integrada à Aba BASE:** Injeção automática dos novos pedidos validados diretamente na aba BASE da planilha .xlsx carregada pelo usuário.
- **Revisão Interativa e Segurança DOM:** Tabela editável renderizada via document.createElement e textContent para conferência manual antes do download, com prevenção de duplicidade por lote e planilha.

### Alterado
- **Infraestrutura de Deploy:** Migração de backend Python/Django serverless para entrega estática via CDN na Vercel (outputDirectory: public), eliminando erros de tamanho máximo de payload (413 Payload Too Large) e cold start.
- **Consolidação de Código:** Unificação dos templates HTML duplicados em um único ponto de entrada (public/index.html).

### Removido
- Cópias redundantes do template HTML na raiz e subdiretórios templates/.
