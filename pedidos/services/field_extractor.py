import re
from decimal import Decimal, InvalidOperation


def parse_decimal_br(valor_str: str):
    if not valor_str:
        return None
    limpo = re.sub(r"[^0-9,.]", "", valor_str.strip())
    if not limpo:
        return None
    if "," in limpo and "." in limpo:
        if limpo.rfind(",") > limpo.rfind("."):
            limpo = limpo.replace(".", "").replace(",", ".")
        else:
            limpo = limpo.replace(",", "")
    elif "," in limpo:
        limpo = limpo.replace(",", ".")
    elif limpo.count(".") > 1:
        limpo = limpo.replace(".", "")
    try:
        return Decimal(limpo).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _extrair_cliente(texto: str) -> str:
    m_bruto = re.search(r"(?i)\bCliente\b\s*[:\-]?\s*0*(\d{1,8})\b", texto)
    if m_bruto:
        return m_bruto.group(1)
    m_linha = re.search(r"(?i)\bCliente\b[^\n]{0,30}\n\s*0*(\d{1,8})\b", texto)
    if m_linha:
        return m_linha.group(1)
    return ""


def _extrair_pedido(texto: str) -> str:
    texto_sem_data_ped = re.sub(r"(?i)Data\s+pedido\s*[:\-]?\s*[\d/]+", "", texto)
    padroes = [
        r"(?i)\bPedido\b\s*[:\-]?\s*(\d{5,14})\b",
        r"(?i)\bN[º°o]?\s*Pedido\b\s*[:\-]?\s*(\d{5,14})\b",
        r"(?i)\bPedido\b[^\n]{0,25}\n\s*(\d{5,14})\b",
    ]
    for pat in padroes:
        m = re.search(pat, texto_sem_data_ped)
        if m:
            return m.group(1)
    return ""


def _extrair_peso(texto: str):
    padroes = [
        r"(?i)\bPeso\b\s*[:\-]?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{1,3}|\d+(?:[.,]\d{1,3})?)\s*(?:Kg|KG|kg)?",
        r"(?i)\bPeso\b[^\n]{0,25}\n\s*(\d{1,3}(?:\.\d{3})*,\d{1,3}|\d+(?:[.,]\d{1,3})?)\s*(?:Kg|KG|kg)?",
    ]
    for pat in padroes:
        m = re.search(pat, texto)
        if m:
            val = parse_decimal_br(m.group(1))
            if val is not None:
                return val
    return None


def _extrair_valor_total(texto: str):
    texto_sem_peso = re.sub(r"(?i)\bPeso\b\s*[:\-]?\s*[\d.,]+\s*(?:Kg|KG|kg)?", "", texto)

    padroes_diretos = [
        r"(?i)(?:Valor\s+Total|Total\s+Geral|Total)\b\s*[:\-]?\s*(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})",
        r"(?i)(?:Valor\s+Total|Total\s+Geral|Total)\b[^\n]{0,40}\n[^\d]{0,15}(?:R\$\s*)?(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})",
        r"(?i)R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2}|\d+\.\d{2})",
    ]
    for pat in padroes_diretos:
        matches = re.findall(pat, texto_sem_peso)
        if matches:
            for cand in reversed(matches):
                val = parse_decimal_br(cand)
                if val is not None and val > Decimal("0.00"):
                    return val

    linhas = [ln.strip() for ln in texto_sem_peso.splitlines() if ln.strip()]
    for ln in reversed(linhas):
        if re.search(r"(?i)\b(data|hora|pedido|cliente|itens|peso)\b", ln) and not re.search(r"(?i)\btotal\b", ln):
            continue
        m_num = re.findall(r"(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})", ln)
        if m_num:
            val = parse_decimal_br(m_num[-1])
            if val is not None and val > Decimal("0.00"):
                return val

    return None


def extrair_campos_pedido(ocr_resultado: dict) -> dict:
    t1 = ocr_resultado.get("texto_principal", "")
    t2 = ocr_resultado.get("texto_secundario", "")
    textos_busca = [t for t in [t1, t2] if t]

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
        obs = "Todos os 4 campos extraídos e conferidos."
    elif len(faltantes) < 4:
        status = "PARCIAL"
        obs = f"Conferir campo(s) ausente(s): {', '.join(faltantes)}."
    else:
        status = "ERRO"
        obs = "Nenhum campo principal (Cliente, Pedido, Peso ou Total) identificado."

    return {
        "numero_cliente": cliente,
        "numero_pedido": pedido,
        "peso_total": peso,
        "valor_total": total,
        "status_reconhecimento": status,
        "observacao_ocr": obs,
    }
