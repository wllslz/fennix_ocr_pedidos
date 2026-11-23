import os
from PIL import Image, ImageOps, ImageEnhance, ImageFilter


def preprocessar_imagem_pedido(image_path: str) -> dict:
    with Image.open(image_path) as pil_img:
        pil_img = ImageOps.exif_transpose(pil_img)
        rgb = pil_img.convert("RGB")

        w, h = rgb.size
        if w < 1600:
            scale = 1600.0 / float(w)
            rgb = rgb.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

        gray = ImageOps.grayscale(rgb)
        contrasted = ImageEnhance.Contrast(gray).enhance(1.8)
        sharpened = contrasted.filter(ImageFilter.SHARPEN)
        binary = sharpened.point(lambda p: 255 if p > 145 else 0)

        out_enh = f"{image_path}_enh.png"
        out_bin = f"{image_path}_bin.png"
        sharpened.save(out_enh, "PNG")
        binary.save(out_bin, "PNG")

    return {
        "enhanced_path": out_enh,
        "binary_path": out_bin,
    }
