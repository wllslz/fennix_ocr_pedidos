# Changelog

Todas as mudanças notáveis, diagnósticos e etapas do processo deste projeto serão documentadas neste arquivo.

## [1.2.1] - 2026-11-25

### Processo geral e diagnóstico
- **Exibição da linha exata na interface:** após identificar que o arquivo enviado anteriormente gravou o registro na linha `1048505` (fora da sequência ativa da aba `BASE `), adicionou-se na interface o destaque visual **Linha preenchida na aba BASE** com o número da linha e o detalhamento das células (`A`, `B`, `C`, `D`, `E`, `F` e `I`), além da coluna **Linha BASE** na tabela da sessão e no log de status.

### Adicionado
- Bloco **Linha preenchida na aba BASE** na interface exibindo o número da linha gravada e cada célula preenchida (`A` a `F` e `I`).

## [1.2.0] - 2026-11-25

### Processo geral e diagnóstico
- **Inspeção da planilha gerada (`MANITORAMENTO EXPEDIÇÃO - 26-01-26 (version 1).xlsb_atualizado.xlsx`) e do print da aba `BASE `:** identificou-se que a aba `BASE ` contém linhas formatadas vazias até a linha `1.048.504`, fazendo com que a soma simples `+ 1` sobre a última tag `<row>` enviasse os lançamentos para a linha `1048505` em vez da próxima linha ativa logo abaixo do último pedido preenchido (ex.: linha `2583` após a linha `2582`).
- **Mapeamento das colunas da aba `BASE ` (`A` a `L`):** confirmou-se que a aba `BASE ` utiliza estrutura específica (`A`: Data serial/estilo `56`, `B`: Mês via `sharedStrings`/`57`, `C`: Cliente/`57`, `D`: Peso/`58`, `E`: Valor/`59`, `F`: Pedido/`60`, `G`–`L`: colunas operacionais com `SEPARADO` e estilos preservados), distinta da aba `LOJA` e da aba oculta `BASE 2`.
- **Verificação do fluxo de download:** assegurou-se que o botão **Baixar .xlsx atualizado** permaneça bloqueado até que o arquivo `.xlsx` seja carregado e ao menos um pedido seja adicionado na sessão, mantendo todas as abas (`LOJA`, `BASE `, `BASE 2`) intactas no arquivo final.

### Alterado
- Inserção na aba `BASE ` direcionada à próxima linha após a última linha com conteúdo real (`encontrarProximaLinhaAtiva`), evitando o salto até `1048505`.
- Preenchimento das células nas colunas `A` a `L` herdando os estilos e referências de `sharedStrings` (como mês e `SEPARADO`) da linha modelo da aba `BASE `.
- Exibição da coluna **Linha BASE** na tabela de pedidos adicionados na sessão e mensagens de status detalhadas na adição e no download.

### Corrigido
- Lançamento de pedidos fora da sequência ativa da aba `BASE ` (linha `1048505` em vez da linha imediatamente abaixo dos últimos registros).
- Despadronização de colunas e tipos numéricos/strings ao gravar novos registros na aba `BASE `.

## [1.1.0] - 2026-11-25

### Processo geral e diagnóstico
- **Diagnóstico da leitura OCR no print do pedido:** verificou-se que o OCR de imagem inteira capturava `"NIX"` (do cabeçalho/logo `FENNIX`) no campo de pedido e não isolava o código numérico do cliente (`14660`) nem o número completo do pedido (`4731000665`).
- **Diagnóstico de build na Vercel:** identificou-se o erro `[DJANGO_ENTRYPOINT_NOT_FOUND]` quando a Vercel tentava aplicar preset Django após a migração para aplicação estática client-side em `public/index.html`.

### Adicionado
- Pré-processamento de imagem no navegador via HTML5 Canvas (`upscale`, escala de cinza, ajuste de contraste e binarização leve) integrado ao Tesseract.js (`por+eng`).
- Recortes direcionados (`topoDir`, `clienteEsq`, `totais` e imagem completa) com `tessedit_char_whitelist` para leitura de campos numéricos e identificadores.
- Exibição do resumo extraído (`Cód. Cliente`, `Pedido`, `Peso`, `Valor`) e do texto bruto do OCR na caixa de status.

### Alterado
- Extração de **Código do Cliente** (ex.: `14660`) e **Nº Pedido** numérico (ex.: `4731000665`) a partir dos rótulos e regiões do documento.
- Bloqueio do botão **Baixar .xlsx atualizado** até o carregamento da planilha base e a adição de pelo menos um pedido.
- Configuração de `vercel.json` com `"framework": null`, `"buildCommand": null` e `"outputDirectory": "public"`.

### Corrigido
- Falha de deploy na Vercel por detecção de projeto Django sem entrypoint Python.
- Captura incorreta de `"NIX"` como número do pedido e ausência do código numérico do cliente.
