import shutil
from copy import copy
from datetime import datetime
from pathlib import Path
import openpyxl

MESES_PT = {1:"Janeiro",2:"Fevereiro",3:"Março",4:"Abril",5:"Maio",6:"Junho",7:"Julho",8:"Agosto",9:"Setembro",10:"Outubro",11:"Novembro",12:"Dezembro"}

def _aba_base(wb):
    for n in wb.sheetnames:
        if n.strip().upper() == "BASE":
            return wb[n]
    raise ValueError(f"Aba BASE nao encontrada: {wb.sheetnames}")

def _proxima_linha(ws) -> int:
    for r in range(min(ws.max_row, 50000), 1, -1):
        if ws.cell(r, 6).value is not None or ws.cell(r, 3).value is not None:
            return r + 1
    return 2

def analisar_planilha(caminho: str) -> dict:
    wb = openpyxl.load_workbook(caminho, read_only=True)
    ws = _aba_base(wb)
    ult = 1
    for idx, row in enumerate(ws.iter_rows(max_col=12, values_only=True), start=1):
        if idx > 1 and (row[5] is not None or row[2] is not None):
            ult = idx
        elif idx > ult + 200:
            break
    wb.close()
    return {"aba_alvo": ws.title, "proxima_linha": ult + 1, "total_pedidos": ult - 1}

def inserir_pedidos_na_planilha(caminho_planilha: str, pedidos: list[dict], responsavel_obs: str = "") -> dict:
    caminho = Path(caminho_planilha)
    bkp = caminho.parent.parent / "backups"
    bkp.mkdir(parents=True, exist_ok=True)
    shutil.copy2(caminho, bkp / f"{caminho.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{caminho.suffix}")
    wb = openpyxl.load_workbook(caminho)
    ws = _aba_base(wb)
    existentes = {str(ws.cell(r, 6).value).strip() for r in range(2, min(ws.max_row, 50000) + 1) if ws.cell(r, 6).value is not None}
    linha = _proxima_linha(ws)
    modelo = max(2, linha - 1)
    inseridos, duplicados = 0, []
    for p in pedidos:
        cod_ped = str(p["numero_pedido"]).strip()
        if cod_ped in existentes:
            duplicados.append(cod_ped)
            continue
        try:
            dt = datetime.strptime(p["data_pedido"], "%d/%m/%Y")
        except Exception:
            dt = datetime.now()
        for c in range(1, 13):
            o, d = ws.cell(modelo, c), ws.cell(linha, c)
            if o.has_style:
                d.font, d.fill, d.border, d.alignment, d.number_format = copy(o.font), copy(o.fill), copy(o.border), copy(o.alignment), o.number_format
        if ws.cell(linha, 1).value is None: ws.cell(linha, 1, dt)
        if ws.cell(linha, 2).value is None: ws.cell(linha, 2, MESES_PT[dt.month])
        ws.cell(linha, 3, int(p["codigo_cliente"]))
        ws.cell(linha, 4, float(p["peso_total"]))
        ws.cell(linha, 5, float(p["valor_total"]))
        ws.cell(linha, 6, int(p["numero_pedido"]))
        ws.cell(linha, 8, p.get("tipo_expedicao", "LOJA"))
        ws.cell(linha, 9, "SEPARADO")
        if responsavel_obs and ws.cell(linha, 11).value is None:
            ws.cell(linha, 11, responsavel_obs)
        existentes.add(cod_ped)
        linha += 1
        inseridos += 1
    wb.save(caminho)
    wb.close()
    return {"inseridos": inseridos, "ignorados_duplicados": duplicados, "proxima_linha_livre": linha}
