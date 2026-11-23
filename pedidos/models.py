from django.db import models


class PlanilhaModelo(models.Model):
    nome_original = models.CharField(max_length=255)
    arquivo_original = models.FileField(upload_to="planilhas_base/")
    arquivo_atualizado = models.CharField(max_length=500, blank=True, default="")
    aba_destino = models.CharField(max_length=100, default="BASE ")
    mapeamento_colunas = models.JSONField(default=dict, blank=True)
    metadados_estrutura = models.JSONField(default=dict, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.nome_original} ({self.aba_destino})"


class LoteProcessamento(models.Model):
    planilha = models.ForeignKey(PlanilhaModelo, on_delete=models.CASCADE, related_name="lotes")
    criado_em = models.DateTimeField(auto_now_add=True)
    total_imagens = models.PositiveIntegerField(default=0)
    total_identificados = models.PositiveIntegerField(default=0)
    total_pendentes = models.PositiveIntegerField(default=0)
    total_exportados = models.PositiveIntegerField(default=0)
    arquivo_exportado = models.CharField(max_length=500, blank=True, default="")
    backup_gerado = models.CharField(max_length=500, blank=True, default="")

    class Meta:
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Lote #{self.id} - {self.criado_em:%d/%m/%Y %H:%M}"


class PedidoExtraido(models.Model):
    STATUS_REC_CHOICES = [
        ("OK", "Reconhecido"),
        ("PARCIAL", "Revisão Necessária"),
        ("DUPLICADO", "Duplicado"),
        ("ERRO", "Falha na Leitura"),
    ]
    STATUS_PLAN_CHOICES = [
        ("PENDENTE", "Aguardando Confirmação"),
        ("INSERIDO", "Inserido na Planilha"),
        ("IGNORADO", "Ignorado / Duplicado"),
    ]

    lote = models.ForeignKey(LoteProcessamento, on_delete=models.CASCADE, related_name="pedidos")
    imagem = models.ImageField(upload_to="pedidos_imagens/")
    nome_imagem = models.CharField(max_length=255)

    numero_cliente = models.CharField(max_length=50, blank=True, default="")
    numero_pedido = models.CharField(max_length=50, blank=True, default="")
    peso_total = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    valor_total = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    tipo_expedicao = models.CharField(max_length=50, blank=True, default="LOJA")
    responsavel = models.CharField(max_length=100, blank=True, default="")

    status_reconhecimento = models.CharField(max_length=20, choices=STATUS_REC_CHOICES, default="PARCIAL")
    status_planilha = models.CharField(max_length=20, choices=STATUS_PLAN_CHOICES, default="PENDENTE")
    observacao_ocr = models.TextField(blank=True, default="")
    texto_ocr_bruto = models.TextField(blank=True, default="")
    linha_inserida = models.PositiveIntegerField(null=True, blank=True)
    data_processamento = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"Pedido {self.numero_pedido or 'N/D'} - Cliente {self.numero_cliente or 'N/D'}"
