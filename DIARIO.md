# Diário de Desenvolvimento — Fennix OCR Pedidos

- **2026-11-25 (Restauração e publicação):** Corrigido o arquivo `public/index.html` que havia sido truncado durante substituições anteriores, garantindo a presença de todas as funções (`renderUltimaLinha`, `render`, `processarImagensSelecionadas`, `adicionarNaPlanilha` e `baixarPlanilha`) e mantendo a preservação do serial numérico da coluna `A` e da estrutura XML da aba `BASE`.
- **2026-11-25 (Documentação):** Atualizados `CHANGELOG.md` e `DIARIO.md` e disparado commit, `git push` e deploy em produção com `npx vercel --prod`.
