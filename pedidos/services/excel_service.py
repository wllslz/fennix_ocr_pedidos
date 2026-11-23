import os
import shutil
import unicodedata
from copy import copy
from datetime import datetime, date
from decimal import Decimal
import openpyxl
from openpyxl.utils import get_column_letter

MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro",
}

ALIASES_CAMPOS = {
    "cliente": ["cliente", "cod cliente", "codigo cliente", "num cliente", "numero cliente"],
    "pedido": ["pedido", "num pedido", "numero pedido", "n pedido", "nro pedido"],
    "peso": ["peso", "peso total", "peso kg", "peso liquido", "peso bruto"],
    "total": ["valor", "total", "valor total", "vlr total", "valor pedido"],
    "data": ["data", "data pedido", "dt"],
    "mes": ["mes", "mês"],
    "tipo_expedicao": ["tipo de expedicao", "tipo expedicao", "expedicao"],
    "status_separacao": ["status de separacao", "status separacao", "status"],
    "responsavel": ["responsavel", "conferente"],
}


def normalizar_texto(txt) -> str:
    if txt is None:
        return ""
    s = str(txt).strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ASCII", "ignore").decode("ASCII")
    return " ".join(s.split())


def analisar_estrutura_planilha(caminho_xlsx: str) -> dict:
    wb = openpyxl.load_workbook(caminho_xlsx, data_only=False)
    abas_info = {}

    for nome_aba in wb.sheetnames:
        ws = wb[nome_aba]
        linha_cabecalho = None
        colunas = {}

        for r in range(1, min(21, ws.max_row + 1)):
            encontrados = {}
            for c in range(1, min(30, ws.max_column + 1)):
                val = ws.cell(r, c).value
                if val is not None and str(val).strip():
                    encontrados[c] = {
                        "col_idx": c,
                        "col_letter": get_column_letter(c),
                        "header_original": str(val),
                        "header_norm": normalizar_texto(val),
                        "number_format": ws.cell(r, c).number_format,
                    }
            norms = {v["header_norm"] for v in encontrados.values()}
            if any(any(k in n for k in ("pedido", "cliente", "peso", "valor", "total")) for n in norms):
                linha_cabecalho = r
                colunas = encontrados
                break

        if linha_cabecalho is None:
            continue

        mapeamento = {}
        for campo_logico, sinonimos in ALIASES_CAMPOS.items():
            for c_idx, info in colunas.items():
                if info["header_norm"] in sinonimos:
                    mapeamento[campo_logico] = info["col_letter"]
                    break

        ultima_linha_dados = linha_cabecalho
        linhas_vagas_pre_datadas = []
        col_pedido_idx = None
        col_cliente_idx = None
        for c_idx, info in colunas.items():
            if info["col_letter"] == mapeamento.get("pedido"):
                col_pedido_idx = c_idx
            if info["col_letter"] == mapeamento.get("cliente"):
                col_cliente_idx = c_idx

        limite_busca = min(ws.max_row, 50000)
        linhas_vazias_seguidas = 0
        for r in range(linha_cabecalho + 1, limite_busca + 1):
            vals = [ws.cell(r, c).value for c in colunas.keys()]
            if any(v is not None for v in vals):
                ultima_linha_dados = r
                linhas_vazias_seguidas = 0
                ped_v = ws.cell(r, col_pedido_idx).value if col_pedido_idx else None
                cli_v = ws.cell(r, col_cliente_idx).value if col_cliente_idx else None
                if ped_v is None and cli_v is None:
                    linhas_vagas_pre_datadas.append(r)
            else:
                linhas_vazias_seguidas += 1
                if linhas_vazias_seguidas > 50:
                    break

        abas_info[nome_aba] = {
            "linha_cabecalho": linha_cabecalho,
            "colunas": list(colunas.values()),
            "mapeamento": mapeamento,
            "ultima_linha_dados": ultima_linha_dados,
            "linhas_vagas_pre_datadas": linhas_vagas_pre_datadas,
            "tabelas": list(ws.tables.keys()),
        }

    aba_padrao = None
    for nome_aba, info in abas_info.items():
        m = info["mapeamento"]
        if all(k in m for k in ("cliente", "pedido", "peso", "total")):
            if nome_aba.strip().upper() == "BASE":
                aba_padrao = nome_aba
                break
            if aba_padrao is None:
                aba_padrao = nome_aba

    if aba_padrao is None and abas_info:
        aba_padrao = next(iter(abas_info.keys()))

    return {
        "abas": wb.sheetnames,
        "aba_destino": aba_padrao,
        "aba_selecionada": aba_padrao,
        "mapeamento": abas_info.get(aba_padrao, {}).get("mapeamento", {}) if aba_padrao else {},
        "linha_cabecalho": abas_info.get(aba_padrao, {}).get("linha_cabecalho") if aba_padrao else None,
        "detalhes_abas": abas_info,
        "aviso_slicer": "Planilha analisada com sucesso. Slicers visuais do Excel são removidos pelo OpenPyXL, mantendo 100% dos dados, fórmulas e formatações.",
    }


def criar_backup_planilha(caminho_origem: str, pasta_backups: str) -> str:
    os.makedirs(pasta_backups, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = os.path.basename(caminho_origem)
    destino = os.path.join(pasta_backups, f"BACKUP_{ts}_{nome}")
    shutil.copy2(caminho_origem, destino)
    return destino


def _copiar_estilo_linha(ws, linha_origem: int, linha_destino: int, max_col: int):
    for c in range(1, max_col + 1):
        src = ws.cell(linha_origem, c)
        dst = ws.cell(linha_destino, c)
        if src.has_style:
            dst.font = copy(src.font)
            dst.fill = copy(src.fill)
            dst.border = copy(src.border)
            dst.alignment = copy(src.alignment)
            dst.number_format = src.number_format


def _converter_identificador(valor_str: str):
    s = str(valor_str).strip()
    if not s:
        return None
    if s.isdigit() and not (len(s) > 1 and s.startswith("0")):
        return int(s)
    return s


def inserir_pedidos_na_planilha(
    caminho_base: str,
    caminho_saida: str,
    aba_destino: str,
    mapeamento: dict,
    pedidos_aprovados: list[dict],
) -> dict:
    wb = openpyxl.load_workbook(caminho_base, data_only=False)
    if aba_destino not in wb.sheetnames:
        raise ValueError(f"Aba '{aba_destino}' não encontrada na planilha.")

    ws = wb[aba_destino]
    col_cliente = openpyxl.utils.column_index_from_string(mapeamento["cliente"])
    col_pedido = openpyxl.utils.column_index_from_string(mapeamento["pedido"])
    col_peso = openpyxl.utils.column_index_from_string(mapeamento["peso"])
    col_total = openpyxl.utils.column_index_from_string(mapeamento["total"])

    col_data = openpyxl.utils.column_index_from_string(mapeamento["data"]) if mapeamento.get("data") else None
    col_mes = openpyxl.utils.column_index_from_string(mapeamento["mes"]) if mapeamento.get("mes") else None
    col_tipo = openpyxl.utils.column_index_from_string(mapeamento["tipo_expedicao"]) if mapeamento.get("tipo_expedicao") else None
    col_status = openpyxl.utils.column_index_from_string(mapeamento["status_separacao"]) if mapeamento.get("status_separacao") else None
    col_resp = openpyxl.utils.column_index_from_string(mapeamento["responsavel"]) if mapeamento.get("responsavel") else None

    pedidos_existentes = set()
    ultima_linha_com_algo = 1
    linhas_vagas_disponiveis = []
    linhas_vazias_seguidas = 0

    for r in range(2, min(ws.max_row + 1, 50000)):
        row_vals = [ws.cell(r, c).value for c in range(1, 13)]
        if any(v is not None for v in row_vals):
            ultima_linha_com_algo = r
            linhas_vazias_seguidas = 0
            ped_val = ws.cell(r, col_pedido).value
            cli_val = ws.cell(r, col_cliente).value
            if ped_val is not None:
                pedidos_existentes.add(str(ped_val).strip())
            elif cli_val is None:
                linhas_vagas_disponiveis.append(r)
        else:
            linhas_vazias_seguidas += 1
            if linhas_vazias_seguidas > 50:
                break

    linha_modelo_estilo = max(2, ultima_linha_com_algo)
    proxima_linha_nova = ultima_linha_com_algo + 1
    hoje_dt = datetime.combine(date.today(), datetime.min.time())
    mes_atual_pt = MESES_PT[date.today().month]

    inseridos = []
    duplicados_ignorados = []

    for item in pedidos_aprovados:
        ped_str = str(item.get("numero_pedido", "")).strip()
        if not ped_str:
            continue
        if ped_str in pedidos_existentes:
            duplicados_ignorados.append(ped_str)
            continue

        if linhas_vagas_disponiveis:
            target_row = linhas_vagas_disponiveis.pop(0)
        else:
            target_row = proxima_linha_nova
            proxima_linha_nova += 1
            _copiar_estilo_linha(ws, linha_modelo_estilo, target_row, 12)
            if col_data and ws.cell(target_row, col_data).value is None:
                ws.cell(target_row, col_data).value = hoje_dt
                ws.cell(target_row, col_data).number_format = "mm-dd-yy"
            if col_mes and ws.cell(target_row, col_mes).value is None:
                ws.cell(target_row, col_mes).value = mes_atual_pt
            if col_status and ws.cell(target_row, col_status).value is None:
                ws.cell(target_row, col_status).value = "SEPARADO"

        ws.cell(target_row, col_cliente).value = _converter_identificador(item.get("numero_cliente", ""))
        ws.cell(target_row, col_pedido).value = _converter_identificador(ped_str)

        peso_val = item.get("peso_total")
        if peso_val is not None and peso_val != "":
            ws.cell(target_row, col_peso).value = float(Decimal(str(peso_val)))
            ws.cell(target_row, col_peso).number_format = "0.00"

        total_val = item.get("valor_total")
        if total_val is not None and total_val != "":
            ws.cell(target_row, col_total).value = float(Decimal(str(total_val)))
            ws.cell(target_row, col_total).number_format = r'_-"R$"\ * #,##0.00_-;\-"R$"\ * #,##0.00_-;_-"R$"\ * "-"??_-;_-@_-'

        if col_tipo and item.get("tipo_expedicao"):
            ws.cell(target_row, col_tipo).value = str(item["tipo_expedicao"]).strip().upper()
        if col_resp and item.get("responsavel"):
            ws.cell(target_row, col_resp).value = str(item["responsavel"]).strip()

        pedidos_existentes.add(ped_str)
        inseridos.append({"id": item.get("id"), "pedido": ped_str, "linha": target_row})

    ultima_final = max(ultima_linha_com_algo, proxima_linha_nova - 1)
    if "Tabela1" in ws.tables:
        ws.tables["Tabela1"].ref = f"A1:L{ultima_final}"

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    wb.save(caminho_saida)

    return {
        "inseridos": inseridos,
        "duplicados": duplicados_ignorados,
        "arquivo_saida": caminho_saida,
    }
