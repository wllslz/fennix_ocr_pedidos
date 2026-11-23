import re
from decimal import Decimal, InvalidOperation


def parse_decimal_br(valor_str: str):
    if not valor_str:
        return None
    limpo = re.sub(r"[^0-9,.]", "", valor_str.strip())
    if not limpo:
        return None
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif limpo.count(".") > 1:
        limpo = limpo.replace(".", "")
    try:
        return Decimal(limpo).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _extrair_cliente(texto: str) -> str:
    padroes = [
        r"(?i)\bCliente\b\s*[:\-]?\s*0*(\d{1,8})(?=\s*(?:[-–]|\b[A-ZÀ-Ú]{2,}|$|\n))",
        r"(?i)\bCliente\b\s*[:\-]?\s*(\d{1,8})\b",
    ]
    for pat in padroes:
        m = re.search(pat, texto)
        if m:
            m_bruto = re.search(r"(?i)\bCliente\b\s*[:\-]?\s*(\d{1,8})\b", texto)
            return m_bruto.group(1) if m_bruto else m.group(1)
    return ""


def _extrair_pedido(texto: str) -> str:
    texto_sem_data_ped = re.sub(r"(?i)Data\s+pedido\s*[:\-]?\s*[\d/]+", "", texto)

    padroes = [
        r"(?i)\bPedido\b\s*[:\-]?\s*(\d{5,14})\b",
        r"(?i)\bN[º°o]?\s*Pedido\b\s*[:\-]?\s*(\d{5,14})\b",
    ]
    for pat in padroes:
        m = re.search(pat, texto_sem_data_ped)
        if m:
            return m.group(1)
    return ""


def _extrair_peso(texto: str):
    padroes = [
        r"(?i)\bPeso\b\s*[:\-]?\s*(\d{1,3}(?:\.\d{3})*,\d{1,3}|\d+(?:[.,]\d{1,3})?)\s*(?:Kg|KG|kg)?",
    ]
    for pat in padroes:
        m = re.search(pat, texto)
        if m:
            val = parse_decimal_br(m.group(1))
            if val is not None:
                return val
    return None


def _extrair_valor_total(texto: str):
    m_bloco = re.search(
        r"(?i)(?:Peso|N\.\s*Itens|Emitente)[^\n]{0,120}\bTotal\b\s*[:\-]?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        texto,
    )
    if m_bloco:
        val = parse_decimal_br(m_bloco.group(1))
        if val is not None:
            return val

    matches = re.findall(
        r"(?i)\bTotal\b\s*[:\-]?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})",
        texto,
    )
    if matches:
        val = parse_decimal_br(matches[-1])
        if val is not None:
            return val

    return None


def extrair_campos_pedido(ocr_resultado: dict) -> dict:
    t1 = ocr_resultado.get("texto_principal", "")
    t2 = ocr_resultado.get("texto_secundario", "")
    textos_busca = [t1, t2] if t2 else [t1]

    cliente = ""
    pedido = ""
    peso = None
    total = None

    for txt in textos_busca:
        if not cliente:
            cliente = _extrair_cliente(txt)
        if not pedido:
            pedido = _extrair_pedido(txt)
        if peso is None:
            peso = _extrair_peso(txt)
        if total is None:
            total = _extrair_valor_total(txt)

    faltantes = []
    if not cliente:
        faltantes.append("Cliente")
    if not pedido:
        faltantes.append("Pedido")
    if peso is None:
        faltantes.append("Peso")
    if total is None:
        faltantes.append("Total")

    if not faltantes:
        status = "OK"
        obs = "Todos os 4 campos extraídos com sucesso."
    elif len(faltantes) < 4:
        status = "PARCIAL"
        obs = f"Conferir campo(s) não identificado(s): {', '.join(faltantes)}."
    else:
        status = "ERRO"
        obs = "Não foi possível localizar os rótulos Cliente, Pedido, Peso e Total na imagem."

    return {
        "numero_cliente": cliente,
        "numero_pedido": pedido,
        "peso_total": peso,
        "valor_total": total,
        "status_reconhecimento": status,
        "observacao_ocr": obs,
    }
