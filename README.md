# Fennix OCR Pedidos

Extrator automatizado de dados de pedidos a partir de capturas de tela (WhatsApp / ERP) com exportação direta para planilha Excel operacional (.xlsx), operando **100% client-side** (sem armazenamento de arquivos em servidor).

**Aplicação em Produção:** [https://fennixocrpedidos-nine.vercel.app](https://fennixocrpedidos-nine.vercel.app)

## Arquitetura & Diferenciais

- **Processamento Local (Stateless):** Todo o reconhecimento óptico de caracteres (OCR) e a manipulação da planilha ocorrem diretamente no navegador do usuário via WebAssembly/JavaScript.
- **Zero Limite de Upload:** Contorna limites de payload de funções serverless (4.5 MB na Vercel) e elimina latência de cold start.
- **Privacidade Operacional:** Nenhuma imagem de pedido ou planilha financeira trafega ou fica retida em servidores externos.
- **Integridade da Planilha Base:** Lê a planilha .xlsx existente do usuário, localiza a aba BASE (preservando o espaço nominal), anexa os novos registros validados e gera o arquivo atualizado para download imediato.

## Stack Tecnológica

| Camada | Tecnologia | Finalidade |
| :--- | :--- | :--- |
| **Interface** | HTML5, CSS3, JavaScript (ES6+) | Upload em lote, revisão editável e feedback de progresso |
| **Motor OCR** | Tesseract.js (por) | Reconhecimento de texto em português direto no navegador |
| **Planilhas** | SheetJS (xlsx) | Leitura, injeção de linhas na aba BASE e exportação .xlsx |
| **Hospedagem** | Vercel Static CDN | Deploy contínuo via GitHub (outputDirectory: public) |

## Mapeamento de Colunas na Aba BASE

| Coluna | Cabeçalho | Origem no Pedido |
| :--- | :--- | :--- |
| **A** | Data | Data do pedido (DD/MM/AAAA) |
| **B** | Mês | Mês por extenso em português |
| **C** | CLIENTE | Código numérico do cliente (ex.: 14660) |
| **D** | PESO | Peso total em Kg (ex.: 20.16) |
| **E** | VALOR | Valor total do pedido (ex.: 359.89) |
| **F** | Pedido | Número do pedido (ex.: 4731000665) |
| **H** | TIPO DE EXPEDIÇÃO | LOJA (padrão) |
| **I** | STATUS DE SEPARAÇÃO | SEPARADO |
| **K** | OBS | Nome do conferente informado na tela |

## Estrutura do Projeto

- public/index.html — Aplicação completa (UI, Worker OCR, Parser Regex e Exportador XLSX)
- vercel.json — Configuração de roteamento estático na Vercel
- CHANGELOG.md — Histórico de versões e evolução arquitetural
- README.md — Documentação técnica do projeto

## Execução Local

Sirva a pasta public/ com qualquer servidor HTTP local:

    python -m http.server 8000 --directory public

Acesse http://localhost:8000 no navegador.

## Autor

Desenvolvido por **Willian Lira de Souza** ([https://github.com/wllslz](https://github.com/wllslz)).
