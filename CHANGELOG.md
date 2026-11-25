# Changelog

Todas as mudanças relevantes deste projeto são documentadas neste arquivo.

## [0.3.0] - 2026-11-25
- Restauração integral de `public/index.html` com fechamento completo de `renderUltimaLinha()`, `render()`, `processarImagensSelecionadas()`, `adicionarNaPlanilha()` e `baixarPlanilha()`.
- Gravação na próxima linha ativa da aba `BASE` (colunas `A` a `M`) preservando o serial numérico da coluna `A`, estilos, `sharedStrings` e demais abas (`LOJA`, `BASE 2`).
- Suporte a upload múltiplo, colagem via `Ctrl + V`, modal de conferência visual ampliada com `Esc` e normalização decimal brasileira.

## [0.2.0] - Fluxo de conferência, colagem e gravação na aba BASE
- Suporte a colagem rápida de imagens via `Ctrl + V` fora de campos de texto.
- Modal de conferência visual ampliada com sincronização direta dos campos (`Cliente`, `Pedido`, `Peso`, `Valor R$`) e fechamento por `Esc`.
- Painel de inspeção da última linha gravada na aba `BASE` (células `A`..`M`) e tabela consolidada dos pedidos adicionados na sessão.

## [0.1.0] - Estrutura inicial
- Estrutura base em `public/index.html` com leitura de `.xlsx` via `JSZip`, OCR via `Tesseract.js` (`por`), formulário de edição/conferência e download do `.xlsx` atualizado.
