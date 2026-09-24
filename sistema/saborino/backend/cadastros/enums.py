from django.db import models


class FormaPagamento(models.TextChoices):
    PIX = 'PIX', 'Pix'
    DINHEIRO = 'DINHEIRO', 'Dinheiro'
    CARTAO = 'CARTAO', 'Cartão'
    OUTRO = 'OUTRO', 'Outro'
