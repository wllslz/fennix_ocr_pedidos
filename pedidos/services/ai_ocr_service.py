import os, json
from PIL import Image
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

class PedidoExtraidoSchema(BaseModel):
    codigo_cliente: int = Field(description="Codigo numerico do cliente antes do hifen (ex: 14660).")
    nome_cliente: str = Field(description="Razao social ou nome fantasia do cliente.")
    numero_pedido: int = Field(description="Numero inteiro do pedido (ex: 4731000665).")
    peso_total: float = Field(description="Peso total em Kg com ponto decimal (ex: 20.16).")
    valor_total: float = Field(description="Valor total com ponto decimal (ex: 359.89).")
    data_pedido: str = Field(description="Data do pedido no formato DD/MM/AAAA.")
    tipo_expedicao: str = Field(description="Retornar 'LOJA' quando constar RETIRADA ou loja.")

def extrair_dados_pedido_ia(caminho_imagem: str) -> dict:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY nao configurada no .env.")
    client = genai.Client(api_key=api_key)
    prompt = "Extraia codigo_cliente (apenas digitos antes do traco), nome_cliente, numero_pedido, peso_total, valor_total, data_pedido e tipo_expedicao deste espelho de pedido FENNIX BRASIL."
    resp = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[Image.open(caminho_imagem), prompt],
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=PedidoExtraidoSchema, temperature=0.0),
    )
    return json.loads(resp.text)
