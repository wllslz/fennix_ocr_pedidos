import os
import json
import base64
import tempfile
import urllib.request
from decimal import Decimal
from django.http import JsonResponse, FileResponse, HttpResponse
from django.shortcuts import render
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import PlanilhaModelo, LoteProcessamento, PedidoExtraido
from .forms import PlanilhaUploadForm, validar_imagem_pedido
from .services.excel_service import analisar_estrutura_planilha, inserir_pedidos_na_planilha
from .services.image_processor import preprocessar_imagem_pedido
from .services.ocr_engine import executar_ocr
from .services.field_extractor import extrair_campos_pedido, parse_decimal_br


def _obter_ou_criar_planilha_padrao(planilha_id=None):
    planilha = PlanilhaModelo.objects.filter(id=planilha_id).first() if planilha_id else PlanilhaModelo.objects.first()
    if not planilha:
        planilha = PlanilhaModelo.objects.create(
            nome_original="MANITORAMENTO_EXPEDICAO_BASE.xlsx",
            aba_destino="BASE ",
            mapeamento_colunas={
                "cliente": "C",
                "pedido": "F",
                "peso": "D",
                "total": "E",
                "data": "A",
                "mes": "B",
                "tipo_expedicao": "H",
                "status_separacao": "I",
                "responsavel": "L",
            },
        )
    return planilha


def dashboard(request):
    planilha = PlanilhaModelo.objects.first()
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
        arquivo_modelo=arquivo,
    )
    info = analisar_estrutura_planilha(planilha.arquivo_modelo.path)
    planilha.aba_destino = info["aba_destino"]
    planilha.mapeamento_colunas = info["mapeamento"]
    planilha.save()

    return JsonResponse({
        "ok": True,
        "planilha_id": planilha.id,
        "nome": planilha.nome_original,
        "abas": info["abas"],
        "aba_destino": info["aba_destino"],
        "mapeamento": info["mapeamento"],
    })


@require_POST
def atualizar_mapeamento(request):
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido."}, status=400)
    planilha = _obter_ou_criar_planilha_padrao(data.get("planilha_id"))
    planilha.aba_destino = data.get("aba_destino", planilha.aba_destino)
    planilha.mapeamento_colunas = data.get("mapeamento", planilha.mapeamento_colunas)
    planilha.save()
    return JsonResponse({"ok": True})


@require_POST
def processar_lote(request):
    planilha = _obter_ou_criar_planilha_padrao(request.POST.get("planilha_id"))
    arquivos = request.FILES.getlist("imagens")
    if not arquivos:
        return JsonResponse({"ok": False, "erro": "Envie ao menos uma imagem de pedido."}, status=400)

    tipo_expedicao = request.POST.get("tipo_expedicao", "LOJA").strip().upper()
    responsavel = request.POST.get("responsavel", "").strip()

    lote = LoteProcessamento.objects.create(
        planilha=planilha,
        total_imagens=len(arquivos),
    )

    resultados = []
    identificados = 0
    pendentes = 0

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
    if not lote or not lote.planilha.arquivo_modelo:
        return JsonResponse({"ok": False, "erro": "Use a exportação direta com a planilha selecionada."}, status=400)

    registros = data.get("registros", [])
    aprovados = []
    for item in registros:
        rec = PedidoExtraido.objects.filter(id=item.get("id"), lote=lote).first()
        if not rec:
            continue
        rec.numero_cliente = str(item.get("numero_cliente", "")).strip()
        rec.numero_pedido = str(item.get("numero_pedido", "")).strip()
        rec.peso_total = parse_decimal_br(str(item.get("peso_total", "")))
        rec.valor_total = parse_decimal_br(str(item.get("valor_total", "")))
        rec.tipo_expedicao = str(item.get("tipo_expedicao", "LOJA")).strip().upper()
        rec.responsavel = str(item.get("responsavel", "")).strip()
        rec.aprovado_usuario = bool(item.get("aprovar", True))
        rec.save()
        if rec.aprovado_usuario:
            aprovados.append({
                "id": rec.id,
                "numero_cliente": rec.numero_cliente,
                "numero_pedido": rec.numero_pedido,
                "peso_total": rec.peso_total,
                "valor_total": rec.valor_total,
                "tipo_expedicao": rec.tipo_expedicao,
                "responsavel": rec.responsavel,
            })

    nome_saida = f"ATUALIZADO_{os.path.basename(lote.planilha.nome_original or "planilha.xlsx")}"
    caminho_saida = os.path.join(os.path.dirname(lote.planilha.arquivo_modelo.path), f"lote_{lote.id}_{nome_saida}")
    resultado = inserir_pedidos_na_planilha(
        caminho_base=lote.planilha.arquivo_modelo.path,
        caminho_saida=caminho_saida,
        aba_destino=lote.planilha.aba_destino,
        mapeamento=lote.planilha.mapeamento_colunas,
        pedidos_aprovados=aprovados,
    )
    lote.arquivo_exportado.name = os.path.relpath(caminho_saida, os.path.join(os.path.dirname(lote.planilha.arquivo_modelo.path), ".."))
    lote.status = "EXPORTADO"
    lote.save()

    return JsonResponse({
        "ok": True,
        "inseridos": len(resultado["inseridos"]),
        "duplicados": resultado["duplicados"],
        "download_url": f"/baixar-planilha/{lote.id}/",
    })


def baixar_planilha(request, lote_id):
    lote = LoteProcessamento.objects.filter(id=lote_id).first()
    if not lote or not lote.arquivo_exportado:
        return JsonResponse({"ok": False, "erro": "Arquivo não encontrado."}, status=404)
    return FileResponse(
        open(lote.arquivo_exportado.path, "rb"),
        as_attachment=True,
        filename=f"ATUALIZADO_{lote.planilha.nome_original}",
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
