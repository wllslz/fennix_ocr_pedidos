import os
import json
import shutil
import urllib.request
from PIL import Image

try:
    import pytesseract
    win_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
    ]
    win_tess = next((p for p in win_paths if os.path.exists(p)), win_paths[0])
    if os.name == "nt" and not shutil.which("tesseract") and os.path.exists(win_tess):
        pytesseract.pytesseract.tesseract_cmd = win_tess
    HAS_TESSERACT = bool(shutil.which("tesseract") or (os.name == "nt" and os.path.exists(win_tess)))
except ImportError:
    pytesseract = None
    HAS_TESSERACT = False


def _ocr_cloud_api(image_path: str) -> str:
    api_key = os.environ.get("OCR_SPACE_API_KEY", "helloworld")
    boundary = "----FennixOCRBoundary7MA4YWxkTrZu0gW"
    with open(image_path, "rb") as f:
        img_data = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="apikey"\r\n\r\n{api_key}\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="language"\r\n\r\npor\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="OCREngine"\r\n\r\n2\r\n'
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="pedido.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + img_data + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(
        "https://api.ocr.space/parse/image",
        data=body,
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": "FennixOCR/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        res = json.loads(resp.read().decode("utf-8"))

    parsed = res.get("ParsedResults") or []
    return "\n".join(item.get("ParsedText", "") for item in parsed)


def executar_ocr(imagens_prep: dict) -> dict:
    enh_path = imagens_prep["enhanced_path"]
    bin_path = imagens_prep["binary_path"]

    if HAS_TESSERACT and pytesseract is not None:
        config_tess = "--oem 3 --psm 6 -l por+eng"
        with Image.open(enh_path) as im_enh, Image.open(bin_path) as im_bin:
            texto_enh = pytesseract.image_to_string(im_enh, config=config_tess)
            texto_bin = pytesseract.image_to_string(im_bin, config=config_tess)
        return {
            "engine": "tesseract",
            "texto_completo": f"{texto_enh}\n---\n{texto_bin}",
            "texto_principal": texto_enh,
            "texto_secundario": texto_bin,
            "linhas": [],
        }

    texto_cloud = _ocr_cloud_api(enh_path)
    return {
        "engine": "ocr_cloud",
        "texto_completo": texto_cloud,
        "texto_principal": texto_cloud,
        "texto_secundario": "",
        "linhas": [],
    }
