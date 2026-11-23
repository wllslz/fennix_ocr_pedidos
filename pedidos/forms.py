import os
from django import forms
from django.core.exceptions import ValidationError

ALLOWED_EXCEL_EXT = {".xlsx"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ""}
MAX_EXCEL_SIZE = 25 * 1024 * 1024
MAX_IMAGE_SIZE = 15 * 1024 * 1024


def validar_planilha_excel(arquivo):
    nome_seguro = os.path.basename(arquivo.name or "")
    ext = os.path.splitext(nome_seguro)[1].lower()
    if ext not in ALLOWED_EXCEL_EXT:
        raise ValidationError("Formato inválido. Envie uma planilha .xlsx.")
    if not arquivo.size or arquivo.size > MAX_EXCEL_SIZE:
        raise ValidationError("A planilha está vazia ou excede o limite de 25 MB.")
    cabecalho = arquivo.read(4)
    arquivo.seek(0)
    if cabecalho != b"PK\x03\x04":
        raise ValidationError("Arquivo Excel inválido ou corrompido.")


def validar_imagem_pedido(arquivo):
    nome_seguro = os.path.basename(arquivo.name or "")
    ext = os.path.splitext(nome_seguro)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValidationError(f"Arquivo '{nome_seguro}' ignorado: use JPG, PNG ou WEBP do WhatsApp.")
    if not arquivo.size or arquivo.size > MAX_IMAGE_SIZE:
        raise ValidationError(f"Imagem '{nome_seguro}' está vazia ou excede o limite de 15 MB.")
    cabecalho = arquivo.read(12)
    arquivo.seek(0)
    is_jpg = cabecalho.startswith(b"\xff\xd8\xff")
    is_png = cabecalho.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = cabecalho.startswith(b"RIFF") and cabecalho[8:12] == b"WEBP"
    if not (is_jpg or is_png or is_webp):
        raise ValidationError(f"Arquivo '{nome_seguro}' não é uma imagem válida.")
    if not os.path.splitext(nome_seguro)[1]:
        arquivo.name = f"{nome_seguro or 'whatsapp_pedido'}.jpg"


class PlanilhaUploadForm(forms.Form):
    planilha = forms.FileField(validators=[validar_planilha_excel])
