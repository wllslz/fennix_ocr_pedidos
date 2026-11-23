import os
import json
import base64
import urllib.request
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import render
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import PlanilhaModelo, LoteProcessamento, PedidoExtraido
from .forms import PlanilhaUploadForm, validar_imagem_pedido
from .services.excel_service import (
    analisar_estrutura_planilha,
    criar_backup_planilha,
    inserir_pedidos_na_planilha,
)
from .services.image_processor import preprocessar_imagem_pedido
from .services.ocr_engine import executar_ocr
from .services.field_extractor import extrair_campos_pedido, parse_decimal_br


def _obter_ou_criar_planilha_padrao(planilha_id=None):
    planilha = PlanilhaModelo.objects.filter(id=planilha_id).first() if planilha_id else PlanilhaModelo.objects.order_by('-id').first()
    mapeamento_oficial = {
        "data": "A",
        "mes": "B",
        "cliente": "C",
        "peso": "D",
        "total": "E",
        "pedido": "F",
        "tipo_expedicao": "H",
        "status_separacao": "I",
        "responsavel": "L",
    }
    rel_padrao = "planilhas_base/MANITORAMENTO_EXPEDICAO_PADRAO.xlsx"
    abs_padrao = os.path.join(settings.MEDIA_ROOT, rel_padrao)

    if not planilha:
        planilha = PlanilhaModelo(
            nome_original="MANITORAMENTO EXPEDIÇÃO - 26-01-26 (version 1).xlsb.xlsx",
            aba_destino="BASE ",
            mapeamento_colunas=mapeamento_oficial,
        )
        if os.path.exists(abs_padrao):
            planilha.arquivo_original.name = rel_padrao
        planilha.save()
    elif (not planilha.arquivo_original or not os.path.exists(planilha.arquivo_original.path)) and os.path.exists(abs_padrao):
        planilha.nome_original = "MANITORAMENTO EXPEDIÇÃO - 26-01-26 (version 1).xlsb.xlsx"
        planilha.aba_destino = "BASE "
        planilha.mapeamento_colunas = mapeamento_oficial
        planilha.arquivo_original.name = rel_padrao
        planilha.save()
    return planilha


def dashboard(request):
    planilha = PlanilhaModelo.objects.order_by('-id').first() or _obter_ou_criar_planilha_padrao()
    lote = LoteProcessamento.objects.filter(planilha=planilha).first() if planilha else None
    pedidos = lote.pedidos.all() if lote else []
    return render(
        request,
        "pedidos/dashboard.html",
        {
            "planilha": planilha,
            "lote": lote,
            "pedidos": pedidos,
        },
    )


@require_POST
def upload_planilha(request):
    form = PlanilhaUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        erros = "; ".join(sum(form.errors.values(), []))
        return JsonResponse({"ok": False, "erro": erros}, status=400)

    arquivo = form.cleaned_data["planilha"]
    planilha = PlanilhaModelo.objects.create(
        nome_original=arquivo.name,
        arquivo_original=arquivo,
    )
    try:
        info = analisar_estrutura_planilha(planilha.arquivo_original.path)
        planilha.aba_destino = info["aba_destino"]
        planilha.mapeamento_colunas = info["mapeamento"]
        planilha.metadados_estrutura = info
        planilha.save()

        m = info["mapeamento"] or {}
        resumo_cols = (
            f"Cliente: {m.get('cliente') or '-'} | "
            f"Pedido: {m.get('pedido') or '-'} | "
            f"Peso: {m.get('peso') or '-'} | "
            f"Total: {m.get('total') or '-'}"
        )
        return JsonResponse({
            "ok": True,
            "planilha_id": planilha.id,
            "nome": planilha.nome_original,
            "abas": info["abas"],
            "aba_destino": info["aba_destino"],
            "linha_cabecalho": info.get("linha_cabecalho"),
            "mapeamento": m,
            "ultima_linha_dados": info.get("ultima_linha_dados"),
        "mensagem": f"Planilha '{planilha.nome_original}' carregada! Aba '{info['aba_destino']}', última linha preenchida: {info.get('ultima_linha_dados') or 1}. Colunas -> {resumo_cols}",
        })
    except Exception as e:
        planilha.delete()
        return JsonResponse({"ok": False, "erro": f"Erro ao analisar planilha: {e}"}, status=500)


@require_POST
def atualizar_mapeamento(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido."}, status=400)

    planilha = _obter_ou_criar_planilha_padrao(data.get("planilha_id"))
    nova_aba = str(data.get("aba_destino") or planilha.aba_destino or "BASE").strip()
    novo_map = dict(planilha.mapeamento_colunas or {})
    for k, v in (data.get("mapeamento") or {}).items():
        if v is not None and str(v).strip():
            novo_map[k] = str(v).strip().upper()

    planilha.aba_destino = nova_aba
    planilha.mapeamento_colunas = novo_map
    planilha.save()

    resumo_cols = (
        f"Cliente: {novo_map.get('cliente') or '-'} | "
        f"Pedido: {novo_map.get('pedido') or '-'} | "
        f"Peso: {novo_map.get('peso') or '-'} | "
        f"Total: {novo_map.get('total') or '-'}"
    )
    return JsonResponse({
        "ok": True,
        "planilha_id": planilha.id,
        "aba_destino": planilha.aba_destino,
        "mapeamento": planilha.mapeamento_colunas,
        "mensagem": f"Estrutura atualizada na aba '{planilha.aba_destino}'. Colunas -> {resumo_cols}",
    })


@require_POST
def processar_lote(request):
    if "planilha" in request.FILES:
        form_pl = PlanilhaUploadForm(request.POST, request.FILES)
        if not form_pl.is_valid():
            erros = "; ".join(sum(form_pl.errors.values(), []))
            return JsonResponse({"ok": False, "erro": erros}, status=400)
        arq_pl = form_pl.cleaned_data["planilha"]
        planilha = PlanilhaModelo.objects.create(
            nome_original=arq_pl.name,
            arquivo_original=arq_pl,
        )
        info = analisar_estrutura_planilha(planilha.arquivo_original.path)
        planilha.aba_destino = info["aba_destino"]
        planilha.mapeamento_colunas = info["mapeamento"]
        planilha.metadados_estrutura = info
        planilha.save()
    else:
        planilha = _obter_ou_criar_planilha_padrao(request.POST.get("planilha_id"))
    arquivos = request.FILES.getlist("imagens")
    if not arquivos:
        return JsonResponse({"ok": False, "erro": "Envie ao menos uma imagem de pedido."}, status=400)

    tipo_expedicao = request.POST.get("tipo_expedicao", "LOJA").strip().upper()
    responsavel = request.POST.get("responsavel", "").strip()

    lote_id_req = request.POST.get("lote_id")
    lote = LoteProcessamento.objects.filter(id=lote_id_req).first() if lote_id_req else None
    if lote:
        if planilha and lote.planilha_id != planilha.id:
            lote.planilha = planilha
        lote.total_imagens = (lote.total_imagens or 0) + len(arquivos)
        lote.save()
    else:
        lote = LoteProcessamento.objects.create(
            planilha=planilha,
            total_imagens=len(arquivos),
        )

    resultados = []
    identificados = lote.total_identificados or 0
    pendentes = lote.total_pendentes or 0

    for arq in arquivos:
        try:
            validar_imagem_pedido(arq)
        except Exception as e:
            rec = PedidoExtraido.objects.create(
                lote=lote,
                nome_imagem=arq.name,
                tipo_expedicao=tipo_expedicao,
                responsavel=responsavel,
                status_reconhecimento="ERRO",
                observacao_ocr=str(e),
            )
            pendentes += 1
            resultados.append(_serializar_pedido(rec))
            continue

        rec = PedidoExtraido.objects.create(
            lote=lote,
            nome_imagem=arq.name,
            imagem=arq,
            tipo_expedicao=tipo_expedicao,
            responsavel=responsavel,
        )
        try:
            prep = preprocessar_imagem_pedido(rec.imagem.path)
            ocr_res = executar_ocr(prep)
            extraido = extrair_campos_pedido(ocr_res)

            rec.numero_cliente = extraido["numero_cliente"]
            rec.numero_pedido = extraido["numero_pedido"]
            rec.peso_total = extraido["peso_total"]
            rec.valor_total = extraido["valor_total"]
            rec.status_reconhecimento = extraido["status_reconhecimento"]
            rec.observacao_ocr = extraido["observacao_ocr"]
            rec.texto_ocr_bruto = ocr_res.get("texto_principal", "")
            rec.save()

            if rec.status_reconhecimento == "OK":
                identificados += 1
            else:
                pendentes += 1
        except Exception as e:
            rec.status_reconhecimento = "ERRO"
            rec.observacao_ocr = f"Erro no OCR: {e}"
            rec.save()
            pendentes += 1

        resultados.append(_serializar_pedido(rec))

    lote.total_identificados = identificados
    lote.total_pendentes = pendentes
    lote.save()

    return JsonResponse({
        "ok": True,
        "planilha_id": planilha.id,
        "lote_id": lote.id,
        "resumo": {
            "total_imagens": lote.total_imagens,
            "total_identificados": identificados,
            "total_pendentes": pendentes,
        },
        "pedidos": resultados,
    })


@require_POST
def confirmar_exportacao(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido."}, status=400)

    lote = LoteProcessamento.objects.filter(id=data.get("lote_id")).first()
    if not lote:
        return JsonResponse({"ok": False, "erro": "Lote não encontrado. Processe ao menos uma imagem antes."}, status=400)

    if not lote.planilha:
        lote.planilha = _obter_ou_criar_planilha_padrao(None)
        lote.save()

    if not lote.planilha.arquivo_original or not os.path.exists(lote.planilha.arquivo_original.path):
        import openpyxl
        dir_planilhas = os.path.join(settings.MEDIA_ROOT, "planilhas_base")
        os.makedirs(dir_planilhas, exist_ok=True)
        nome_base = f"BASE_FENNIX_{lote.planilha.id}.xlsx"
        caminho_gerado = os.path.join(dir_planilhas, nome_base)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BASE"
        ws.append([
            "Data", "Mês", "Cliente", "Pedido", "Peso", "Total",
            "Observação", "Tipo Expedição", "Status Separação",
            "Conferente", "Nota", "Responsável",
        ])
        wb.save(caminho_gerado)
        lote.planilha.nome_original = nome_base
        lote.planilha.aba_destino = "BASE"
        lote.planilha.mapeamento_colunas = {
            "data": "A",
            "mes": "B",
            "cliente": "C",
            "pedido": "D",
            "peso": "E",
            "total": "F",
            "tipo_expedicao": "H",
            "status_separacao": "I",
            "responsavel": "L",
        }
        lote.planilha.arquivo_original.name = os.path.relpath(caminho_gerado, settings.MEDIA_ROOT).replace("\\", "/")
        lote.planilha.save()

    registros = data.get("registros", [])
    aprovados = []
    for item in registros:
        rec = PedidoExtraido.objects.filter(id=item.get("id"), lote=lote).first()
        if not rec:
            continue
        aprovar = bool(item.get("aprovar", True))
        rec.numero_cliente = str(item.get("numero_cliente", "")).strip()
        rec.numero_pedido = str(item.get("numero_pedido", "")).strip()
        rec.peso_total = parse_decimal_br(str(item.get("peso_total", "")))
        rec.valor_total = parse_decimal_br(str(item.get("valor_total", "")))
        rec.tipo_expedicao = str(item.get("tipo_expedicao", "LOJA")).strip().upper()
        if "responsavel" in item and item.get("responsavel") is not None:
            rec.responsavel = str(item.get("responsavel", "")).strip()
        if not aprovar:
            rec.status_planilha = "IGNORADO"
        rec.save()

        if aprovar:
            aprovados.append({
                "id": rec.id,
                "numero_cliente": rec.numero_cliente,
                "numero_pedido": rec.numero_pedido,
                "peso_total": rec.peso_total,
                "valor_total": rec.valor_total,
                "tipo_expedicao": rec.tipo_expedicao,
                "responsavel": rec.responsavel,
            })

    if not aprovados:
        return JsonResponse({"ok": False, "erro": "Marque ao menos um pedido na tabela antes de preencher a planilha."}, status=400)

    try:
        caminho_origem = lote.planilha.arquivo_original.path
        backup_path = criar_backup_planilha(caminho_origem, os.path.join(settings.MEDIA_ROOT, "backups"))

        # Grava diretamente na propria planilha enviada, preservando nome, estrutura e dados anteriores
        caminho_saida = caminho_origem

        resultado = inserir_pedidos_na_planilha(
            caminho_base=caminho_origem,
            caminho_saida=caminho_saida,
            aba_destino=lote.planilha.aba_destino,
            mapeamento=lote.planilha.mapeamento_colunas,
            pedidos_aprovados=aprovados,
        )
    except Exception as e:
        return JsonResponse({"ok": False, "erro": f"Erro ao gravar na planilha Excel: {e}"}, status=500)

    for ins in resultado["inseridos"]:
        PedidoExtraido.objects.filter(id=ins["id"]).update(
            status_planilha="INSERIDO",
            linha_inserida=ins["linha"],
        )

    for dup_ped in resultado["duplicados"]:
        PedidoExtraido.objects.filter(lote=lote, numero_pedido=dup_ped).update(
            status_reconhecimento="DUPLICADO",
            status_planilha="IGNORADO",
            observacao_ocr=f"Pedido {dup_ped} já existia na planilha Excel.",
        )

    lote.total_exportados = len(resultado["inseridos"])
    lote.arquivo_exportado = caminho_saida
    lote.backup_gerado = backup_path
    lote.save()

    lote.planilha.arquivo_atualizado = caminho_saida
    lote.planilha.save()

    linhas_gravadas = [str(x["linha"]) for x in resultado["inseridos"]]
    return JsonResponse({
        "ok": True,
        "inseridos": len(resultado["inseridos"]),
        "linhas": linhas_gravadas,
        "aba_utilizada": resultado.get("aba_utilizada"),
        "duplicados": resultado["duplicados"],
        "download_url": f"/baixar-planilha/{lote.id}/",
    })


def baixar_planilha(request, lote_id):
    lote = LoteProcessamento.objects.filter(id=lote_id).first()
    if not lote:
        return JsonResponse({"ok": False, "erro": "Lote não encontrado."}, status=404)
    caminho = ""
    if lote.planilha and lote.planilha.arquivo_original:
        caminho = lote.planilha.arquivo_original.path
    elif lote.arquivo_exportado:
        caminho = str(lote.arquivo_exportado)
        if not os.path.exists(caminho):
            caminho = os.path.join(settings.MEDIA_ROOT, caminho)
    if not caminho or not os.path.exists(caminho):
        return JsonResponse({"ok": False, "erro": "Planilha não localizada no disco."}, status=404)
    nome_dl = os.path.basename(lote.planilha.nome_original or os.path.basename(caminho))
    return FileResponse(
        open(caminho, "rb"),
        as_attachment=True,
        filename=nome_dl,
    )


@csrf_exempt
def webhook_whatsapp(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == os.environ.get("WHATSAPP_VERIFY_TOKEN", "fennix_ocr_2026"):
            return HttpResponse(challenge, content_type="text/plain")
        return JsonResponse({"ok": True, "status": "Webhook WhatsApp Fennix ativo"})

    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido"}, status=400)

    img_bytes = None
    nome_arquivo = f"whatsapp_fwd_{int(os.times()[4] * 1000)}.jpg"
    data_obj = payload.get("data", {}) if isinstance(payload.get("data"), dict) else {}
    msg_obj = data_obj.get("message", {}) if isinstance(data_obj.get("message"), dict) else {}
    b64_str = payload.get("base64") or data_obj.get("base64") or msg_obj.get("base64")
    if b64_str:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)

    media_url = payload.get("mediaUrl") or payload.get("image_url")
    if not img_bytes and media_url:
        req = urllib.request.Request(media_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_bytes = resp.read()

    if not img_bytes:
        return JsonResponse({"ok": True, "ignorado": "Mensagem sem imagem anexada"})

    planilha = _obter_ou_criar_planilha_padrao()
    lote = LoteProcessamento.objects.filter(planilha=planilha).first() or LoteProcessamento.objects.create(planilha=planilha)
    rec = PedidoExtraido.objects.create(lote=lote, nome_imagem=nome_arquivo, tipo_expedicao="LOJA")
    rec.imagem.save(nome_arquivo, ContentFile(img_bytes), save=True)

    try:
        prep = preprocessar_imagem_pedido(rec.imagem.path)
        ocr_res = executar_ocr(prep)
        extraido = extrair_campos_pedido(ocr_res)

        rec.numero_cliente = extraido["numero_cliente"]
        rec.numero_pedido = extraido["numero_pedido"]
        rec.peso_total = extraido["peso_total"]
        rec.valor_total = extraido["valor_total"]
        rec.status_reconhecimento = extraido["status_reconhecimento"]
        rec.observacao_ocr = f"[Via WhatsApp] {extraido['observacao_ocr']}"
        rec.texto_ocr_bruto = ocr_res.get("texto_principal", "")
        rec.save()

        lote.total_imagens += 1
        if rec.status_reconhecimento == "OK":
            lote.total_identificados += 1
        else:
            lote.total_pendentes += 1
        lote.save()

        return JsonResponse({
            "ok": True,
            "pedido_id": rec.id,
            "cliente": rec.numero_cliente,
            "pedido": rec.numero_pedido,
            "peso": str(rec.peso_total or ""),
            "total": str(rec.valor_total or ""),
            "status": rec.status_reconhecimento,
        })
    except Exception as e:
        rec.status_reconhecimento = "ERRO"
        rec.observacao_ocr = f"[Via WhatsApp] Erro OCR: {e}"
        rec.save()
        return JsonResponse({"ok": False, "erro": str(e)}, status=500)


def _serializar_pedido(rec: PedidoExtraido) -> dict:
    return {
        "id": rec.id,
        "nome_imagem": rec.nome_imagem,
        "imagem_url": rec.imagem.url if rec.imagem else "",
        "numero_cliente": rec.numero_cliente,
        "numero_pedido": rec.numero_pedido,
        "peso_total": f"{rec.peso_total:.2f}".replace(".", ",") if rec.peso_total is not None else "",
        "valor_total": f"{rec.valor_total:.2f}".replace(".", ",") if rec.valor_total is not None else "",
        "tipo_expedicao": rec.tipo_expedicao,
        "responsavel": rec.responsavel,
        "status_reconhecimento": rec.status_reconhecimento,
        "status_planilha": rec.status_planilha,
        "observacao_ocr": rec.observacao_ocr,
    }
