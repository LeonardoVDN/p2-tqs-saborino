"""Massa de dados FICTÍCIA do Projeto P2 (TQS 2026).

Uso (a partir de sistema/saborino/backend, com o env.teste carregado):
    python ../../ambiente/seed.py

Idempotente: apaga os dados operacionais e recria sempre o mesmo estado inicial,
para que os testes possam ser repetidos (seção 9.1, item 6 do manual).
Nenhum nome, telefone ou valor corresponde a pessoas ou negócios reais.
"""
import os
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

BACKEND = Path.cwd()
sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from accounts.models import CustomUser  # noqa: E402
from cadastros.models import Canal, Cliente, Competencia, Conta, Produto  # noqa: E402
from operacao.models import (  # noqa: E402
    Compra, ItemVenda, Pagamento, PagamentoAlocacao, ProducaoProduto, Recebivel, Venda,
)

USUARIO_EMAIL = 'tester@saborino.test'
USUARIO_SENHA = 'SenhaFicticia-P2-2026'


@transaction.atomic
def main():
    # 1) Limpeza (ordem respeita as FKs PROTECT)
    PagamentoAlocacao.objects.all().delete()
    Pagamento.objects.all().delete()
    Recebivel.objects.all().delete()
    ItemVenda.objects.all().delete()
    Venda.objects.all().delete()
    Compra.objects.all().delete()
    ProducaoProduto.objects.all().delete()
    Cliente.objects.all().delete()
    Produto.objects.all().delete()
    Conta.objects.all().delete()
    Canal.objects.all().delete()
    Competencia.objects.all().delete()

    # 2) Usuário de teste
    user, _ = CustomUser.objects.get_or_create(username='tester', defaults={'email': USUARIO_EMAIL})
    user.email = USUARIO_EMAIL
    user.is_active = True
    user.is_staff = True
    user.email_verified_at = timezone.now()
    user.set_password(USUARIO_SENHA)
    user.save()

    # 3) Cadastros
    canal_a = Canal.objects.create(nome='Canal A', ordem=1)
    canal_b = Canal.objects.create(nome='Canal B', ordem=2, aplica_dizimo=True)
    Canal.objects.create(nome='Canal C', ordem=3)

    conta_pix = Conta.objects.create(nome='Conta Teste PIX', tipo=Conta.Tipo.CONTA_CORRENTE)
    Conta.objects.create(nome='Caixa Teste', tipo=Conta.Tipo.DINHEIRO)

    bolo = Produto.objects.create(nome='Bolo de Pote Teste', categoria='BOLO_POTE', unidade='POTE',
                                  preco_venda=Decimal('12.00'), custo_estimado_unitario=Decimal('5.00'))
    mousse = Produto.objects.create(nome='Mousse Teste', categoria='MOUSSE', unidade='POTE',
                                    preco_venda=Decimal('10.00'), custo_estimado_unitario=Decimal('4.00'))
    Produto.objects.create(nome='Brownie Teste', categoria='BROWNIE', unidade='UNIDADE',
                           preco_venda=Decimal('7.50'), custo_estimado_unitario=Decimal('3.00'))

    ana = Cliente.objects.create(nome='Cliente Fictício Ana', canal=canal_a, contato='(14) 90000-0001')
    bruno = Cliente.objects.create(nome='Cliente Fictício Bruno', canal=canal_b, contato='(14) 90000-0002')
    Cliente.objects.create(nome='Cliente Fictício Carla', canal=canal_a, contato='(14) 90000-0003')

    # 4) Operação no mês de referência fixo (setembro/2026)
    dia = date(2026, 9, 10)
    venda = Venda.objects.create(cliente=ana, data_venda=dia, registrado_por=user)
    ItemVenda.objects.create(venda=venda, produto=bolo, quantidade=Decimal('2'))
    ItemVenda.objects.create(venda=venda, produto=mousse, quantidade=Decimal('1'))
    venda.recompute_total()
    receb = venda.sincronizar_recebivel()

    venda2 = Venda.objects.create(cliente=bruno, data_venda=dia, registrado_por=user)
    ItemVenda.objects.create(venda=venda2, produto=mousse, quantidade=Decimal('3'))
    venda2.recompute_total()
    venda2.sincronizar_recebivel()

    pag = Pagamento.objects.create(cliente=ana, data=dia, valor=Decimal('20.00'),
                                   conta_recebimento=conta_pix, registrado_por=user)
    PagamentoAlocacao.objects.create(pagamento=pag, recebivel=receb, valor_aplicado=Decimal('20.00'))
    receb.recompute()

    Compra.objects.create(data=dia, descricao='Leite condensado (teste)', quantidade=Decimal('4'),
                          preco_unitario=Decimal('6.50'), conta_origem=conta_pix, produto_rateio=bolo,
                          registrado_por=user)
    ProducaoProduto.objects.create(produto=bolo, competencia=Competencia.para_data(dia),
                                   quantidade_produzida=Decimal('20'), meta_producao=Decimal('30'))

    print('Seed fictício aplicado:')
    print(f'  usuário: {USUARIO_EMAIL} / senha: {USUARIO_SENHA}')
    print(f'  clientes={Cliente.objects.count()} produtos={Produto.objects.count()} '
          f'vendas={Venda.objects.count()} recebíveis={Recebivel.objects.count()} '
          f'pagamentos={Pagamento.objects.count()} compras={Compra.objects.count()}')


if __name__ == '__main__':
    main()
