import os, json
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.core.files.storage import FileSystemStorage
from .services.ai_ocr_service import extrair_dados_pedido_ia
from .services.excel_service import analisar_planilha, inserir_pedidos_na_planilha

def dashboard(request):
    nome = request.session.get("planilha_ativa_nome")
    caminho = request.session.get("planilha_ativa_path")
    resumo = analisar_planilha(caminho) if caminho and os.path.exists(caminho) else None
    return render(request, "pedidos/dashboard.html", {"planilha_ativa": nome, "resumo": resumo})

@require_POST
def upload_planilha(request):
    arq = request.FILES.get("planilha")
    if not arq or not arq.name.endswith(".xlsx"):
        return JsonResponse({"erro": "Envie um arquivo .xlsx valido."}, status=400)
    pasta = Path(settings.MEDIA_ROOT) / "planilha_ativa"
    pasta.mkdir(parents=True, exist_ok=True)
    dest = pasta / arq.name
    with open(dest, "wb+") as f:
        for ch in arq.chunks(): f.write(ch)
    resumo = analisar_planilha(str(dest))
    request.session["planilha_ativa_path"] = str(dest)
    request.session["planilha_ativa_nome"] = arq.name
    return JsonResponse({"mensagem": f"Planilha '{arq.name}' carregada!", "resumo": resumo})

@require_POST
def processar_imagens_ia(request):
    imgs = request.FILES.getlist("imagens")
    if not imgs:
        return JsonResponse({"erro": "Nenhuma imagem enviada."}, status=400)
    fs = FileSystemStorage(location=Path(settings.MEDIA_ROOT) / "temp_pedidos")
    out = []
    for img in imgs:
        salvo = fs.save(img.name, img)
        full = fs.path(salvo)
        try:
            d = extrair_dados_pedido_ia(full)
            d.update({"arquivo": img.name, "sucesso": True})
            out.append(d)
        except Exception as e:
            out.append({"arquivo": img.name, "sucesso": False, "erro": str(e)})
        finally:
            if os.path.exists(full): os.remove(full)
    return JsonResponse({"pedidos": out})

@require_POST
def gravar_na_planilha(request):
    caminho = request.session.get("planilha_ativa_path")
    if not caminho or not os.path.exists(caminho):
        return JsonResponse({"erro": "Faca o upload da planilha primeiro."}, status=400)
    body = json.loads(request.body)
    pedidos = body.get("pedidos", [])
    if not pedidos:
        return JsonResponse({"erro": "Nenhum pedido para gravar."}, status=400)
    res = inserir_pedidos_na_planilha(caminho, pedidos, body.get("responsavel", "").strip())
    return JsonResponse({"resultado": res, "resumo": analisar_planilha(caminho)})

def baixar_planilha(request):
    caminho = request.session.get("planilha_ativa_path")
    nome = request.session.get("planilha_ativa_nome", "MONITORAMENTO_EXPEDICAO.xlsx")
    if not caminho or not os.path.exists(caminho):
        return HttpResponseBadRequest("Planilha nao encontrada.")
    return FileResponse(open(caminho, "rb"), as_attachment=True, filename=nome)
