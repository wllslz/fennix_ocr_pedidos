import os
import json
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.core.files.storage import FileSystemStorage

from .services.ai_ocr_service import extrair_dados_pedido_ia
from .services.excel_service import analisar_planilha, inserir_pedidos_na_planilha


def dashboard(request):
    planilha_ativa = request.session.get("planilha_ativa_nome")
    resumo = None
    caminho = request.session.get("planilha_ativa_path")
    if caminho and os.path.exists(caminho):
        try:
            resumo = analisar_planilha(caminho)
        except Exception:
            request.session.pop("planilha_ativa_path", None)
            request.session.pop("planilha_ativa_nome", None)
            planilha_ativa = None

    return render(request, "pedidos/dashboard.html", {
        "planilha_ativa": planilha_ativa,
        "resumo": resumo,
    })


@require_POST
def upload_planilha(request):
    arquivo = request.FILES.get("planilha")
    if not arquivo or not arquivo.name.endswith(".xlsx"):
        return JsonResponse({"erro": "Envie um arquivo .xlsx valido."}, status=400)

    pasta = Path(settings.MEDIA_ROOT) / "planilha_ativa"
    pasta.mkdir(parents=True, exist_ok=True)
    destino = pasta / arquivo.name

    with open(destino, "wb+") as f:
        for chunk in arquivo.chunks():
            f.write(chunk)

    try:
        resumo = analisar_planilha(str(destino))
    except Exception as e:
        if os.path.exists(destino):
            os.remove(destino)
        return JsonResponse({"erro": f"Arquivo .xlsx invalido ou corrompido: {e}"}, status=400)

    request.session["planilha_ativa_path"] = str(destino)
    request.session["planilha_ativa_nome"] = arquivo.name

    return JsonResponse({
        "mensagem": f"Planilha '{arquivo.name}' mapeada na aba '{resumo['aba_alvo']}'!",
        "resumo": resumo,
    })


@require_POST
def processar_imagens_ia(request):
    imagens = request.FILES.getlist("imagens")
    if not imagens:
        return JsonResponse({"erro": "Nenhuma imagem enviada."}, status=400)

    fs = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "temp_pedidos")
    resultados = []

    for img in imagens:
        nome_salvo = fs.save(img.name, img)
        caminho_completo = fs.path(nome_salvo)
        try:
            dados = extrair_dados_pedido_ia(caminho_completo)
            dados["arquivo"] = img.name
            dados["sucesso"] = True
            resultados.append(dados)
        except Exception as e:
            resultados.append({
                "arquivo": img.name,
                "sucesso": False,
                "erro": str(e),
            })
        finally:
            if os.path.exists(caminho_completo):
                os.remove(caminho_completo)

    return JsonResponse({"pedidos": resultados})


@require_POST
def gravar_na_planilha(request):
    caminho = request.session.get("planilha_ativa_path")
    if not caminho or not os.path.exists(caminho):
        return JsonResponse({"erro": "Nenhuma planilha ativa na sessao. Faca o upload primeiro."}, status=400)

    try:
        payload = json.loads(request.body)
        pedidos = payload.get("pedidos", [])
        responsavel = payload.get("responsavel", "").strip()
    except Exception:
        return JsonResponse({"erro": "Payload JSON invalido."}, status=400)

    if not pedidos:
        return JsonResponse({"erro": "Nenhum pedido para gravar."}, status=400)

    resultado = inserir_pedidos_na_planilha(
        caminho_planilha=caminho,
        pedidos=pedidos,
        responsavel_obs=responsavel,
    )
    resumo_atualizado = analisar_planilha(caminho)

    return JsonResponse({
        "resultado": resultado,
        "resumo": resumo_atualizado,
    })


def baixar_planilha(request):
    caminho = request.session.get("planilha_ativa_path")
    nome_original = request.session.get("planilha_ativa_nome", "MONITORAMENTO_EXPEDICAO.xlsx")
    if not caminho or not os.path.exists(caminho):
        return HttpResponseBadRequest("Planilha nao encontrada.")

    return FileResponse(
        open(caminho, "rb"),
        as_attachment=True,
        filename=nome_original,
    )
