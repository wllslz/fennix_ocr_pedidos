# Fennix OCR Pedidos

Aplicação web em **Django** para análise estrutural de planilhas `.xlsx`, extração de pedidos em imagens via **OCR** e exportação com **OpenPyXL**.

## Porquê e Como Foi Feito

Automatiza a conferência de comprovantes/imagens de pedidos e a identificação de colunas e abas em planilhas `.xlsx`, mantendo revisão humana antes da exportação. Utiliza `openpyxl` para inspeção e gravação de planilhas, validadores de arquivo/tamanho/*magic bytes* em `forms.py` e respostas JSON seguras em `views.py`.

## Funcionalidades e Segurança

- **Análise de estrutura `.xlsx`:** Detecta abas, linha de cabeçalho e mapeamento de colunas (`cliente`, `pedido`, `peso`, `total`, `data`, `mes`, `tipo_expedicao`, `status_separacao`, `responsavel`).
- **Processamento em lote e exportação:** Valida imagens (`JPG`, `PNG`, `WEBP`), extrai campos via OCR e gera o `.xlsx` atualizado.
- **Segurança:** Valida assinatura `PK\x03\x04` e *magic bytes* de imagem, sanitiza nomes de arquivo com `os.path.basename` e retorna `400` em JSON inválido.

```bash
python manage.py check && python manage.py runserver
