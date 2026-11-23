import os
import json
from django.conf import settings
from django.http import JsonResponse, FileResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.views.decorators.http import require_POST

from .forms import PlanilhaUploadForm, validar_imagem_pedido
from .models import PlanilhaModelo, LoteProcessamento, PedidoExtraido
from .services.image_processor import preprocessar_imagem_pedido
from .services.ocr_engine import executar_ocr
from .services.field_extractor import extrair_campos_pedido, parse_decimal_br
from .services.excel_service import (
    analisar_estrutura_planilha,
    criar_backup_planilha,
    inserir_pedidos_na_planilha,
)


def dashboard(request):
    planilha_atual = PlanilhaModelo.objects.first()
    lote_atual = LoteProcessamento.objects.first()
    pedidos_lote = lote_atual.pedidos.all() if lote_atual else []
    return render(
        request,
        "pedidos/dashboard.html",
        {
            "planilha": planilha_atual,
            "lote": lote_atual,
            "pedidos": pedidos_lote,
        },
    )


@require_POST
def upload_planilha(request):
    form = PlanilhaUploadForm(request.POST, request.FILES)
    if not form.is_valid():
        return JsonResponse({"ok": False, "erro": form.errors.as_text()}, status=400)

    arquivo = form.cleaned_data["planilha"]
    planilha_obj = PlanilhaModelo.objects.create(
        nome_original=arquivo.name,
        arquivo_original=arquivo,
    )

    try:
        estrutura = analisar_estrutura_planilha(planilha_obj.arquivo_original.path)
        aba = estrutura.get("aba_selecionada") or "BASE "
        detalhes_aba = estrutura.get("detalhes_abas", {}).get(aba, {})
        mapeamento = detalhes_aba.get("mapeamento", {})

        planilha_obj.aba_destino = aba
        planilha_obj.mapeamento_colunas = mapeamento
        planilha_obj.metadados_estrutura = estrutura
        planilha_obj.save()

        return JsonResponse({
            "ok": True,
            "planilha_id": planilha_obj.id,
            "nome": planilha_obj.nome_original,
            "aba_destino": aba,
            "mapeamento": mapeamento,
            "estrutura": estrutura,
        })
    except Exception as e:
        planilha_obj.delete()
        return JsonResponse({"ok": False, "erro": f"Erro ao ler estrutura do Excel: {e}"}, status=500)


@require_POST
def atualizar_mapeamento(request):
    payload = json.loads(request.body)
    planilha = get_object_or_404(PlanilhaModelo, id=payload.get("planilha_id"))
    planilha.aba_destino = payload.get("aba_destino", planilha.aba_destino)
    planilha.mapeamento_colunas = payload.get("mapeamento", planilha.mapeamento_colunas)
    planilha.save()
    return JsonResponse({"ok": True})


@require_POST
def processar_lote(request):
    planilha_id = request.POST.get("planilha_id")
    planilha = PlanilhaModelo.objects.filter(id=planilha_id).first() if planilha_id else PlanilhaModelo.objects.first()
    if not planilha:
        return JsonResponse({"ok": False, "erro": "Carregue a planilha Excel modelo antes de enviar imagens."}, status=400)

    imagens = request.FILES.getlist("imagens")
    if not imagens:
        return JsonResponse({"ok": False, "erro": "Nenhuma imagem foi selecionada."}, status=400)

    tipo_exp_padrao = request.POST.get("tipo_expedicao", "LOJA").strip().upper()
    resp_padrao = request.POST.get("responsavel", "").strip()

    lote = LoteProcessamento.objects.create(
        planilha=planilha,
        total_imagens=len(imagens),
    )

    pedidos_vistos_lote = set()
    resultados_json = []
    identificados = 0
    pendentes = 0

    for img_file in imagens:
        try:
            validar_imagem_pedido(img_file)
        except Exception as val_err:
            rec = PedidoExtraido.objects.create(
                lote=lote,
                nome_imagem=img_file.name,
                status_reconhecimento="ERRO",
                status_planilha="IGNORADO",
                observacao_ocr=str(val_err),
            )
            pendentes += 1
            resultados_json.append(_serializar_pedido(rec))
            continue

        rec = PedidoExtraido.objects.create(
            lote=lote,
            imagem=img_file,
            nome_imagem=img_file.name,
            tipo_expedicao=tipo_exp_padrao,
            responsavel=resp_padrao,
        )

        try:
            prep = preprocessar_imagem_pedido(rec.imagem.path)
            ocr_res = executar_ocr(prep)
            extraido = extrair_campos_pedido(ocr_res)

            rec.numero_cliente = extraido["numero_cliente"]
            rec.numero_pedido = extraido["numero_pedido"]
            rec.peso_total = extraido["peso_total"]
            rec.valor_total = extraido["valor_total"]
            rec.texto_ocr_bruto = ocr_res.get("texto_principal", "")

            if rec.numero_pedido and rec.numero_pedido in pedidos_vistos_lote:
                rec.status_reconhecimento = "DUPLICADO"
                rec.status_planilha = "IGNORADO"
                rec.observacao_ocr = f"Pedido {rec.numero_pedido} duplicado neste lote."
                pendentes += 1
            else:
                if rec.numero_pedido:
                    pedidos_vistos_lote.add(rec.numero_pedido)
                rec.status_reconhecimento = extraido["status_reconhecimento"]
                rec.observacao_ocr = extraido["observacao_ocr"]
                if rec.status_reconhecimento == "OK":
                    identificados += 1
                else:
                    pendentes += 1

            rec.save()
        except Exception as ocr_err:
            rec.status_reconhecimento = "ERRO"
            rec.observacao_ocr = f"Erro no processamento OCR: {ocr_err}"
            rec.save()
            pendentes += 1

        resultados_json.append(_serializar_pedido(rec))

    lote.total_identificados = identificados
    lote.total_pendentes = pendentes
    lote.save()

    return JsonResponse({
        "ok": True,
        "lote_id": lote.id,
        "resumo": {
            "total_imagens": lote.total_imagens,
            "total_identificados": lote.total_identificados,
            "total_pendentes": lote.total_pendentes,
        },
        "pedidos": resultados_json,
    })


@require_POST
def confirmar_exportacao(request):
    payload = json.loads(request.body)
    lote = get_object_or_404(LoteProcessamento, id=payload.get("lote_id"))
    planilha = lote.planilha
    registros_revisados = payload.get("registros", [])

    mapeamento = planilha.mapeamento_colunas or {}
    faltando_col = [c for c in ("cliente", "pedido", "peso", "total") if not mapeamento.get(c)]
    if faltando_col:
        return JsonResponse(
            {"ok": False, "erro": f"Mapeamento de colunas incompleto: {', '.join(faltando_col)}"},
            status=400,
        )

    caminho_origem = planilha.arquivo_original.path
    backup_path = criar_backup_planilha(caminho_origem, os.path.join(settings.MEDIA_ROOT, "backups"))

    aprovados = []
    for item in registros_revisados:
        if not item.get("aprovar", True):
            continue
        rec = PedidoExtraido.objects.filter(id=item.get("id"), lote=lote).first()
        if not rec:
            continue

        rec.numero_cliente = str(item.get("numero_cliente", "")).strip()
        rec.numero_pedido = str(item.get("numero_pedido", "")).strip()
        rec.peso_total = parse_decimal_br(str(item.get("peso_total", "")))
        rec.valor_total = parse_decimal_br(str(item.get("valor_total", "")))
        rec.tipo_expedicao = str(item.get("tipo_expedicao", rec.tipo_expedicao)).strip().upper()
        rec.responsavel = str(item.get("responsavel", rec.responsavel)).strip()
        rec.save()

        aprovados.append({
            "id": rec.id,
            "numero_cliente": rec.numero_cliente,
            "numero_pedido": rec.numero_pedido,
            "peso_total": rec.peso_total,
            "valor_total": rec.valor_total,
            "tipo_expedicao": rec.tipo_expedicao,
            "responsavel": rec.responsavel,
        })

    nome_saida = f"ATUALIZADO_LOTE_{lote.id}_{planilha.nome_original}"
    caminho_saida = os.path.join(settings.MEDIA_ROOT, "exportados", nome_saida)

    resultado = inserir_pedidos_na_planilha(
        caminho_base=caminho_origem,
        caminho_saida=caminho_saida,
        aba_destino=planilha.aba_destino,
        mapeamento=mapeamento,
        pedidos_aprovados=aprovados,
    )

    for ins in resultado["inseridos"]:
        PedidoExtraido.objects.filter(id=ins["id"]).update(
            status_planilha="INSERIDO",
            linha_inserida=ins["linha"],
        )

    for dup_ped in resultado["duplicados"]:
        PedidoExtraido.objects.filter(lote=lote, numero_pedido=dup_ped).update(
            status_reconhecimento="DUPLICADO",
            status_planilha="IGNORADO",
            observacao_ocr=f"Pedido {dup_ped} já existia na planilha Excel (duplicidade evitada).",
        )

    lote.total_exportados = len(resultado["inseridos"])
    lote.arquivo_exportado = caminho_saida
    lote.backup_gerado = backup_path
    lote.save()

    return JsonResponse({
        "ok": True,
        "inseridos": len(resultado["inseridos"]),
        "duplicados": resultado["duplicados"],
        "download_url": f"/baixar-planilha/{lote.id}/",
    })


def baixar_planilha(request, lote_id):
    lote = get_object_or_404(LoteProcessamento, id=lote_id)
    if not lote.arquivo_exportado or not os.path.exists(lote.arquivo_exportado):
        raise Http404("Planilha exportada não encontrada.")
    return FileResponse(
        open(lote.arquivo_exportado, "rb"),
        as_attachment=True,
        filename=os.path.basename(lote.arquivo_exportado),
    )


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


import base64
import urllib.request
from django.core.files.base import ContentFile
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def webhook_whatsapp(request):
    """
    Recebe imagens encaminhadas diretamente pelo WhatsApp (Evolution API / WPPConnect / Cloud API)
    e processa via OpenCV + Tesseract OCR automaticamente.
    """
    if request.method == "GET":
        # Verificação oficial do Webhook da Meta Cloud API
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == "fennix_ocr_2026":
            from django.http import HttpResponse
            return HttpResponse(challenge, content_type="text/plain")
        return JsonResponse({"ok": True, "status": "Webhook WhatsApp Fennix ativo"})

    if request.method != "POST":
        return JsonResponse({"ok": False, "erro": "Método não permitido"}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"ok": False, "erro": "JSON inválido"}, status=400)

    img_bytes = None
    nome_arquivo = f"whatsapp_fwd_{int(os.times()[4]*1000)}.jpg"

    # Formato 1: Evolution API / Baileys (envia base64 da imagem encaminhada)
    data_obj = payload.get("data", {})
    msg_obj = data_obj.get("message", {}) if isinstance(data_obj, dict) else {}
    b64_str = (
        payload.get("base64")
        or data_obj.get("base64")
        or msg_obj.get("base64")
    )
    if b64_str:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        img_bytes = base64.b64decode(b64_str)

    # Formato 2: URL direta da mídia (Evolution / Z-API / Twilio)
    media_url = payload.get("mediaUrl") or payload.get("image_url")
    if not img_bytes and media_url:
        req = urllib.request.Request(media_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            img_bytes = resp.read()

    if not img_bytes:
        return JsonResponse({"ok": True, "ignorado": "Mensagem sem imagem anexada"})

    planilha = PlanilhaModelo.objects.first()
    if not planilha:
        return JsonResponse({"ok": False, "erro": "Nenhuma planilha-base carregada no painel web."}, status=400)

    lote = LoteProcessamento.objects.filter(planilha=planilha).first()
    if not lote:
        lote = LoteProcessamento.objects.create(planilha=planilha, total_imagens=0)

    rec = PedidoExtraido.objects.create(
        lote=lote,
        nome_imagem=nome_arquivo,
        tipo_expedicao="LOJA",
    )
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

        resposta_bot = (
            f"Pedido lido ({rec.status_reconhecimento}):\n"
            f"• Cliente: {rec.numero_cliente or 'N/D'}\n"
            f"• Pedido: {rec.numero_pedido or 'N/D'}\n"
            f"• Peso: {rec.peso_total or 'N/D'} kg\n"
            f"• Total: R$ {rec.valor_total or 'N/D'}"
        )
        return JsonResponse({
            "ok": True,
            "pedido_id": rec.id,
            "cliente": rec.numero_cliente,
            "pedido": rec.numero_pedido,
            "peso": str(rec.peso_total or ""),
            "total": str(rec.valor_total or ""),
            "status": rec.status_reconhecimento,
            "mensagem_resposta": resposta_bot,
        })
    except Exception as e:
        rec.status_reconhecimento = "ERRO"
        rec.observacao_ocr = f"[Via WhatsApp] Erro OCR: {e}"
        rec.save()
        return JsonResponse({"ok": False, "erro": str(e)}, status=500)
