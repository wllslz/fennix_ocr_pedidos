# Changelog

Todas as mudanças notáveis, diagnósticos e etapas do processo deste projeto serão documentadas neste arquivo.

## [1.3.4] - 2026-11-25

### Processo geral e diagnóstico
- **Detecção resiliente da aba `BASE`:** substituiu-se a comparação estrita `"BASE "` por normalização de espaços/caixa (`normalizarNomeAba`), evitando erro caso a planilha tenha `"BASE"` sem espaço à direita ou variações de espaçamento, e listando as abas disponíveis se não encontrada.
- **Refino do OCR com quiet-zone (padding branco), binarização nítida e fallback de PSM (`6` → `7`):** melhorou-se a precisão na leitura de código do cliente, número do pedido, peso e valor nos recortes direcionados.

### Alterado
- `localizarAbaBase` passa a aceitar `"BASE"`, `"BASE "` e variações com espaços, retornando o nome exato da aba detectada.
- `criarRecorteProcessado` adiciona margem branca (`padPx`) e binarização pura (`0` ou `255`), combinada com `reconhecerRegiao` usando `tessedit_pageseg_mode` `6` e fallback `7`.

### Corrigido
- Seletor universal `*` no CSS de `public/index.html`.
- Falha de localização da aba quando o nome não possuía espaço final (`"BASE "` vs `"BASE"`).

## [1.3.3] - 2026-11-25

### Processo geral e diagnóstico
- **Remoção do dump de texto bruto na caixa de status:** após verificação da interface em uso, removeu-se a exibição do texto bruto completo do OCR (`textoBruto`) abaixo do resumo na caixa de status, mantendo apenas os 4 campos extraídos (`Cód. Cliente`, `Pedido`, `Peso`, `Valor`).
- **Correção da leitura decimal de Peso (`9215` → `92,15`):** identificou-se que em resoluções menores o Tesseract omitia a vírgula decimal do campo `Peso` na linha de totais (ex.: `9215` em vez de `92,15`), gravando `9215` na linha `2613`. Adicionou-se `normalizarPesoExtraido` e prioridade explícita para o recorte `totaisPrep` (com escala `4.0`).

### Alterado
- Caixa de status exibe exclusivamente o resumo limpo (`Cód. Cliente`, `Pedido`, `Peso`, `Valor`) sem o texto bruto do OCR.
- Normalização automática do campo `Peso` (`normalizarPesoExtraido`) para reinserir a vírgula decimal em sequências de 4 ou 5 dígitos sem separador (ex.: `9215` → `92,15`) e priorizar a região de totais.

## [1.3.2] - 2026-11-25

### Processo geral e diagnóstico
- **Inspeção visual ampliada e comparação com os valores extraídos:** adicionou-se modal de visualização ampliada ao clicar na miniatura ou em **Ampliar imagem para conferência**, permitindo comparar diretamente a imagem original com os campos editáveis e aplicar ajustes antes de gravar na aba `BASE `.

### Adicionado
- Modal de conferência visual da imagem com visualização ampliada e edição sincronizada dos campos (`Código do Cliente`, `Nº Pedido`, `Peso kg` e `Valor R$`).

## [1.3.1] - 2026-11-25

### Processo geral e diagnóstico
- **Colagem direta de imagens via Ctrl + V (`paste`):** adicionou-se captura de imagens da área de transferência no navegador para agilizar o fluxo de prints e recortes sem precisar salvar o ficheiro antes de selecionar.

### Adicionado
- Listener global de `paste` convertendo imagens da área de transferência em objetos `File` e encaminhando para o mesmo pipeline de pré-visualização e OCR (`processarImagensSelecionadas`), preservando a digitação normal com `Ctrl + V` nos campos de texto.

## [1.3.0] - 2026-11-25

### Processo geral e diagnóstico
- **Inspeção da planilha atualizada (`MANITORAMENTO EXPEDIÇÃO - 26-01-26 (version 1).xlsb.xlsx`):** confirmou-se que os lançamentos ativos na aba `BASE ` já estão gravados e que as linhas modelo (ex.: `2568` a `2584`) possuem a coluna **M** (`s="61"`, índice de `sharedStrings` referente a `"v"`).
- **Inclusão preventiva da coluna M na configuração:** para manter o padrão preventivo nas próximas inserções da aba `BASE `, o mapeamento passou a cobrir as colunas `A` a `M` (`spans="1:13"`), herdando estilo e valor da coluna `M` da linha modelo e exibindo `M` na interface.

### Alterado
- Configuração de colunas da aba `BASE ` expandida de `A..L` para `A..M`, incluindo herança de estilo/valor de `M` e exibição da coluna **Col. M** no painel da última linha gravada e na tabela da sessão.

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
