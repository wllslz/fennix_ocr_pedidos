import os
import re
import shutil
from datetime import datetime
from PIL import Image, ImageOps, ImageEnhance
import pytesseract

# Localiza automaticamente o executavel do Tesseract no Windows
_CAMINHOS_TESSERACT = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
]
if not shutil.which("tesseract"):
    for caminho in _CAMINHOS_TESSERACT:
        if os.path.exists(caminho):
            pytesseract.pytesseract.tesseract_cmd = caminho
            break


def _limpar_numero_br(texto_num: str) -> float:
    limpo = re.sub(r"[^\d,.]", "", texto_num.strip())
    if "," in limpo and "." in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    return float(limpo)


def extrair_dados_pedido_ia(caminho_imagem: str) -> dict:
    with Image.open(caminho_imagem) as img:
        # Amplia 2x em escala de cinza e aumenta contraste para leitura nitida de prints/WhatsApp
        gray = ImageOps.grayscale(img)
        w, h = gray.size
        resized = gray.resize((w * 2, h * 2), Image.Resampling.LANCZOS)
        enhanced = ImageEnhance.Contrast(resized).enhance(1.8)
        texto = pytesseract.image_to_string(enhanced, lang="por+eng", config="--psm 6")

    # 1. Numero do Pedido (ex: Pedido 4731000665 ou 10 digitos iniciados por 47)
    m_pedido = re.search(r"(?:Pedido|Ped\.?|N[ºo°]\s*Pedido)\s*[:#-]?\s*(\d{7,12})", texto, re.IGNORECASE)
    if not m_pedido:
        m_pedido = re.search(r"\b(47\d{8})\b", texto)
    if not m_pedido:
        raise ValueError(f"Numero do pedido nao encontrado no print. Texto lido:\n{texto[:300]}")
    numero_pedido = int(m_pedido.group(1))

    # 2. Codigo e Nome do Cliente (ex: Cliente: 14660 - S. MAIA REIS LTDA)
    m_cliente = re.search(r"Cliente\s*[:\-]?\s*(\d{2,8})\s*[-–—]\s*([^\n\r]+)", texto, re.IGNORECASE)
    if m_cliente:
        codigo_cliente = int(m_cliente.group(1))
        nome_cliente = m_cliente.group(2).strip()
    else:
        m_cod_alt = re.search(r"\b(\d{4,6})\s*[-–—]\s*([A-ZÀ-Ú0-9 .,&/-]{4,})", texto)
        if not m_cod_alt:
            raise ValueError("Codigo do cliente nao identificado no print.")
        codigo_cliente = int(m_cod_alt.group(1))
        nome_cliente = m_cod_alt.group(2).strip()

    # 3. Peso Total (ex: 20,16 Kg)
    m_peso = re.search(r"(?:Peso(?:\s*Total|\s*Bruto|\s*L[ií]q\.?)?\s*[:\-]?\s*)?(\d{1,5}[.,]\d{1,3})\s*Kg\b", texto, re.IGNORECASE)
    if not m_peso:
        raise ValueError("Peso total (Kg) nao identificado no print.")
    peso_total = _limpar_numero_br(m_peso.group(1))

    # 4. Valor Total (ex: Total: R$ 359,89 ou Valor Total 359,89)
    m_valor = re.search(
        r"(?:Valor\s*Total|Total\s*(?:do\s*Pedido|Geral|L[ií]quido)?)\s*[:\-]?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+[.,]\d{2})",
        texto,
        re.IGNORECASE,
    )
    if not m_valor:
        todos_valores = re.findall(r"(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2})", texto)
        if not todos_valores:
            raise ValueError("Valor total do pedido nao identificado no print.")
        valor_total = max(_limpar_numero_br(v) for v in todos_valores)
    else:
        valor_total = _limpar_numero_br(m_valor.group(1))

    # 5. Data do Pedido (DD/MM/AAAA)
    m_data = re.search(r"\b(\d{2}/\d{2}/20\d{2})\b", texto)
    data_pedido = m_data.group(1) if m_data else datetime.now().strftime("%d/%m/%Y")

    # 6. Tipo de Expedicao
    tipo_expedicao = "LOJA"

    return {
        "codigo_cliente": codigo_cliente,
        "nome_cliente": nome_cliente,
        "numero_pedido": numero_pedido,
        "peso_total": peso_total,
        "valor_total": valor_total,
        "data_pedido": data_pedido,
        "tipo_expedicao": tipo_expedicao,
    }
