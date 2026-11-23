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

        for r in range(1, min(25, ws.max_row + 1)):
            encontrados = {}
            for c in range(1, min(35, ws.max_column + 1)):
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
            if any(v is not None and str(v).strip() != "" for v in vals):
                ultima_linha_dados = r
                linhas_vazias_seguidas = 0
                ped_v = ws.cell(r, col_pedido_idx).value if col_pedido_idx else None
                cli_v = ws.cell(r, col_cliente_idx).value if col_cliente_idx else None
                if (ped_v is None or str(ped_v).strip() == "") and (cli_v is None or str(cli_v).strip() == ""):
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
        if any(k in m for k in ("cliente", "pedido", "peso", "total")):
            if nome_aba.strip().upper() == "BASE":
                aba_padrao = nome_aba
                break
            if aba_padrao is None:
                aba_padrao = nome_aba

    if aba_padrao is None:
        aba_padrao = wb.sheetnames[0] if wb.sheetnames else "BASE"

    return {
        "abas": wb.sheetnames,
        "aba_destino": aba_padrao,
        "aba_selecionada": aba_padrao,
        "mapeamento": abas_info.get(aba_padrao, {}).get("mapeamento", {}),
        "linha_cabecalho": abas_info.get(aba_padrao, {}).get("linha_cabecalho") or 1,
        "detalhes_abas": abas_info,
        "aviso_slicer": "Planilha analisada com sucesso.",
    }


def criar_backup_planilha(caminho_origem: str, pasta_backups: str) -> str:
    os.makedirs(pasta_backups, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = os.path.basename(caminho_origem)
    destino = os.path.join(pasta_backups, f"BACKUP_{ts}_{nome}")
    shutil.copy2(caminho_origem, destino)
    return destino


def _copiar_estilo_linha(ws, linha_origem: int, linha_destino: int, max_col: int):
    if linha_origem < 1:
        return
    if linha_origem in ws.row_dimensions and ws.row_dimensions[linha_origem].height:
        ws.row_dimensions[linha_destino].height = ws.row_dimensions[linha_origem].height
    for c in range(1, max_col + 1):
        src = ws.cell(linha_origem, c)
        dst = ws.cell(linha_destino, c)
        if src.has_style:
            dst.font = copy(src.font)
            dst.fill = copy(src.fill)
            dst.border = copy(src.border)
            dst.alignment = copy(src.alignment)
            dst.number_format = src.number_format
            dst.protection = copy(src.protection)


def _converter_identificador(valor_str: str):
    s = str(valor_str).strip()
    if not s:
        return None
    if s.isdigit() and not (len(s) > 1 and s.startswith("0")):
        return int(s)
    return s


def _col_idx_seguro(letra: str):
    s = str(letra or "").strip().upper()
    if not s:
        return None
    try:
        return openpyxl.utils.column_index_from_string(s)
    except Exception:
        return None


def inserir_pedidos_na_planilha(
    caminho_base: str,
    caminho_saida: str,
    aba_destino: str,
    mapeamento: dict,
    pedidos_aprovados: list[dict],
) -> dict:
    info_estrutura = analisar_estrutura_planilha(caminho_base)
    wb = openpyxl.load_workbook(caminho_base, data_only=False)

    aba_real = aba_destino if aba_destino in wb.sheetnames else None
    if not aba_real:
        for sname in wb.sheetnames:
            if sname.strip().lower() == str(aba_destino or "").strip().lower():
                aba_real = sname
                break
    if not aba_real:
        aba_real = info_estrutura.get("aba_destino") or wb.sheetnames[0]

    ws = wb[aba_real]
    detalhes_aba = info_estrutura.get("detalhes_abas", {}).get(aba_real, {})
    linha_cabecalho = detalhes_aba.get("linha_cabecalho") or 1

    map_efetivo = dict(detalhes_aba.get("mapeamento") or {})
    for k, v in (mapeamento or {}).items():
        if v and str(v).strip():
            map_efetivo[k] = str(v).strip().upper()

    col_cliente = _col_idx_seguro(map_efetivo.get("cliente"))
    col_pedido = _col_idx_seguro(map_efetivo.get("pedido"))
    col_peso = _col_idx_seguro(map_efetivo.get("peso"))
    col_total = _col_idx_seguro(map_efetivo.get("total"))

    col_data = _col_idx_seguro(map_efetivo.get("data"))
    col_mes = _col_idx_seguro(map_efetivo.get("mes"))
    col_tipo = _col_idx_seguro(map_efetivo.get("tipo_expedicao"))
    col_status = _col_idx_seguro(map_efetivo.get("status_separacao"))
    col_resp = _col_idx_seguro(map_efetivo.get("responsavel"))

    cols_monitoradas = [
        c for c in (col_cliente, col_pedido, col_peso, col_total)
        if c is not None
    ] or [
        c for c in (col_data, col_mes, col_tipo, col_status, col_resp)
        if c is not None
    ]
    if not cols_monitoradas:
        cols_monitoradas = list(range(1, min(13, ws.max_column + 1)))

    pedidos_existentes = set()
    ultima_linha_com_dados = linha_cabecalho
    limite_real = min(ws.max_row, 50000)

    # Varre todas as linhas até o fim real da aba para encontrar a última linha preenchida
    for r in range(linha_cabecalho + 1, limite_real + 1):
        row_vals = [ws.cell(r, c).value for c in cols_monitoradas]
        if any(v is not None and str(v).strip() != "" for v in row_vals):
            ultima_linha_com_dados = r
            ped_val = ws.cell(r, col_pedido).value if col_pedido else None
            if ped_val is not None and str(ped_val).strip() != "":
                pedidos_existentes.add(str(ped_val).strip())

    linha_modelo_estilo = ultima_linha_com_dados if ultima_linha_com_dados > linha_cabecalho else 0
    proxima_linha_nova = ultima_linha_com_dados + 1
    max_col_estilo = max([ws.max_column] + cols_monitoradas)
    hoje_dt = datetime.combine(date.today(), datetime.min.time())
    mes_atual_pt = MESES_PT[date.today().month]

    inseridos = []
    duplicados_ignorados = []

    for item in pedidos_aprovados:
        ped_str = str(item.get("numero_pedido") or "").strip()
        cli_str = str(item.get("numero_cliente") or "").strip()
        peso_val = item.get("peso_total")
        total_val = item.get("valor_total")

        tem_algum_dado = any([
            ped_str,
            cli_str,
            peso_val not in (None, ""),
            total_val not in (None, ""),
        ])
        if not tem_algum_dado:
            continue

        if ped_str and ped_str in pedidos_existentes:
            duplicados_ignorados.append(ped_str)
            continue

        # Sempre preenche estritamente a partir da última linha preenchida
        target_row = proxima_linha_nova
        proxima_linha_nova += 1
        if linha_modelo_estilo > linha_cabecalho:
            _copiar_estilo_linha(ws, linha_modelo_estilo, target_row, max_col_estilo)

        if col_data and (ws.cell(target_row, col_data).value is None or str(ws.cell(target_row, col_data).value).strip() == ""):
            ws.cell(target_row, col_data).value = hoje_dt
            ws.cell(target_row, col_data).number_format = "dd/mm/yyyy"
        if col_mes and (ws.cell(target_row, col_mes).value is None or str(ws.cell(target_row, col_mes).value).strip() == ""):
            ws.cell(target_row, col_mes).value = mes_atual_pt
        if col_status and (ws.cell(target_row, col_status).value is None or str(ws.cell(target_row, col_status).value).strip() == ""):
            ws.cell(target_row, col_status).value = "SEPARADO"

        if col_cliente and cli_str:
            ws.cell(target_row, col_cliente).value = _converter_identificador(cli_str)
        if col_pedido and ped_str:
            ws.cell(target_row, col_pedido).value = _converter_identificador(ped_str)

        if col_peso and peso_val is not None and str(peso_val).strip() != "":
            ws.cell(target_row, col_peso).value = float(Decimal(str(peso_val)))
            ws.cell(target_row, col_peso).number_format = "0.00"

        if col_total and total_val is not None and str(total_val).strip() != "":
            ws.cell(target_row, col_total).value = float(Decimal(str(total_val)))
            ws.cell(target_row, col_total).number_format = r'_-"R$"\ * #,##0.00_-;\-"R$"\ * #,##0.00_-;_-"R$"\ * "-"??_-;_-@_-'

        if col_tipo and item.get("tipo_expedicao"):
            ws.cell(target_row, col_tipo).value = str(item["tipo_expedicao"]).strip().upper()
        if col_resp and item.get("responsavel"):
            ws.cell(target_row, col_resp).value = str(item["responsavel"]).strip()

        if ped_str:
            pedidos_existentes.add(ped_str)
        inseridos.append({"id": item.get("id"), "pedido": ped_str or "-", "linha": target_row})

    ultima_final = max(ultima_linha_com_dados, proxima_linha_nova - 1)
    if "Tabela1" in ws.tables:
        ws.tables["Tabela1"].ref = f"A{linha_cabecalho}:L{ultima_final}"

    os.makedirs(os.path.dirname(caminho_saida), exist_ok=True)
    wb.save(caminho_saida)

    return {
        "inseridos": inseridos,
        "duplicados": duplicados_ignorados,
        "arquivo_saida": caminho_saida,
        "aba_utilizada": aba_real,
        "mapeamento_utilizado": map_efetivo,
    }
