import os, json, uuid
from pathlib import Path
from django.conf import settings
from django.http import JsonResponse, FileResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_POST
from .services.excel_service import analisar_planilha, inserir_pedidos_na_planilha

def dashboard(request):
    return render(request, "pedidos/dashboard.html")

@require_POST
def upload_planilha(request):
    arq = request.FILES.get("planilha")
    if not arq or not arq.name.endswith(".xlsx"):
        return JsonResponse({"erro": "Envie um arquivo .xlsx valido."}, status=400)
    pasta = Path(settings.MEDIA_ROOT)
    pasta.mkdir(parents=True, exist_ok=True)
    file_id = f"{uuid.uuid4().hex}_{arq.name}"
    dest = pasta / file_id
    with open(dest, "wb+") as f:
        for ch in arq.chunks():
            f.write(ch)
    try:
        resumo = analisar_planilha(str(dest))
    except Exception as e:
        if dest.exists():
            dest.unlink()
        return JsonResponse({"erro": f"Planilha invalida: {e}"}, status=400)

    return JsonResponse({
        "mensagem": f"Planilha '{arq.name}' mapeada na aba '{resumo['aba_alvo']}'!",
        "file_id": file_id,
        "nome_original": arq.name,
        "resumo": resumo,
    })

@require_POST
def gravar_na_planilha(request):
    arq = request.FILES.get("planilha")
    pedidos_raw = request.POST.get("pedidos", "[]")
    responsavel = request.POST.get("responsavel", "").strip()

    if not arq:
        return JsonResponse({"erro": "Selecione a planilha .xlsx primeiro."}, status=400)

    try:
        pedidos = json.loads(pedidos_raw)
    except Exception:
        return JsonResponse({"erro": "Lista de pedidos invalida."}, status=400)

    if not pedidos:
        return JsonResponse({"erro": "Nenhum pedido na tabela para gravar."}, status=400)

    pasta = Path(settings.MEDIA_ROOT)
    pasta.mkdir(parents=True, exist_ok=True)
    temp_path = pasta / f"{uuid.uuid4().hex}_{arq.name}"

    with open(temp_path, "wb+") as f:
        for ch in arq.chunks():
            f.write(ch)

    try:
        res = inserir_pedidos_na_planilha(str(temp_path), pedidos, responsavel)
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        return JsonResponse({"erro": f"Erro ao gravar na planilha: {e}"}, status=400)

    resp = FileResponse(open(temp_path, "rb"), as_attachment=True, filename=arq.name)
    resp["X-Inseridos"] = str(res["inseridos"])
    resp["X-Duplicados"] = str(len(res["ignorados_duplicados"]))
    resp["X-Proxima-Linha"] = str(res["proxima_linha"])
    resp["Access-Control-Expose-Headers"] = "X-Inseridos, X-Duplicados, X-Proxima-Linha"
    return resp
