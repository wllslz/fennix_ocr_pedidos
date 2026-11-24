from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/upload-planilha/", views.upload_planilha, name="upload_planilha"),
    path("api/processar-imagens/", views.processar_imagens_ia, name="processar_imagens_ia"),
    path("api/gravar-planilha/", views.gravar_na_planilha, name="gravar_na_planilha"),
    path("baixar-planilha/", views.baixar_planilha, name="baixar_planilha"),
]
