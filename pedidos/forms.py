import os
from django import forms
from django.core.exceptions import ValidationError

ALLOWED_EXCEL_EXT = {".xlsx"}
ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ""}
MAX_EXCEL_SIZE = 25 * 1024 * 1024
MAX_IMAGE_SIZE = 15 * 1024 * 1024


def validar_planilha_excel(arquivo):
    ext = os.path.splitext(arquivo.name)[1].lower()
    if ext not in ALLOWED_EXCEL_EXT:
        raise ValidationError("Formato inválido. Envie uma planilha .xlsx.")
    if arquivo.size > MAX_EXCEL_SIZE:
        raise ValidationError("A planilha excede o limite de 25 MB.")
    cabecalho = arquivo.read(4)
    arquivo.seek(0)
    if cabecalho != b"PK\x03\x04":
        raise ValidationError("Arquivo Excel inválido ou corrompido.")


def validar_imagem_pedido(arquivo):
    ext = os.path.splitext(arquivo.name)[1].lower()
    if ext not in ALLOWED_IMAGE_EXT:
        raise ValidationError(f"Arquivo '{arquivo.name}' ignorado: use JPG, PNG ou WEBP do WhatsApp.")
    if arquivo.size > MAX_IMAGE_SIZE:
        raise ValidationError(f"Imagem '{arquivo.name}' excede o limite de 15 MB.")
    cabecalho = arquivo.read(12)
    arquivo.seek(0)
    is_jpg = cabecalho.startswith(b"\xff\xd8\xff")
    is_png = cabecalho.startswith(b"\x89PNG\r\n\x1a\n")
    is_webp = cabecalho.startswith(b"RIFF") and cabecalho[8:12] == b"WEBP"
    if not (is_jpg or is_png or is_webp):
        raise ValidationError(f"Arquivo '{arquivo.name}' não é uma imagem válida.")
    if not os.path.splitext(arquivo.name)[1]:
        arquivo.name = f"{arquivo.name or 'whatsapp_pedido'}.jpg"


class PlanilhaUploadForm(forms.Form):
    planilha = forms.FileField(validators=[validar_planilha_excel])
