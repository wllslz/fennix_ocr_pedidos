from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("upload-planilha/", views.upload_planilha, name="upload_planilha"),
    path("atualizar-mapeamento/", views.atualizar_mapeamento, name="atualizar_mapeamento"),
    path("processar-lote/", views.processar_lote, name="processar_lote"),
    path("confirmar-exportacao/", views.confirmar_exportacao, name="confirmar_exportacao"),
    path("baixar-planilha/<int:lote_id>/", views.baixar_planilha, name="baixar_planilha"),
    path("webhook/whatsapp/", views.webhook_whatsapp, name="webhook_whatsapp"),
]
