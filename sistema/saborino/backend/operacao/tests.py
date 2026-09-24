from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from cadastros.models import Canal, Cliente, Competencia, Conta, Produto
from operacao import services
from operacao.models import ItemVenda, Pagamento, Recebivel, Venda
from operacao.reports import build_dashboard

User = get_user_model()


class BaseData(TestCase):
    def setUp(self):
        self.canal, _ = Canal.objects.get_or_create(nome='Canal B', defaults={'slug': 'canal-b', 'aplica_dizimo': True})
        self.conta, _ = Conta.objects.get_or_create(nome='Caixa', defaults={'tipo': 'DINHEIRO'})
        self.p1 = Produto.objects.create(nome='Bolo de Pote', preco_venda=Decimal('7.00'), custo_estimado_unitario=Decimal('3.00'))
        self.p2 = Produto.objects.create(nome='Pudim', preco_venda=Decimal('6.00'), custo_estimado_unitario=Decimal('2.50'))
        self.cli = Cliente.objects.create(nome='Cliente Teste', canal=self.canal)

    def nova_venda(self, produto, qtd, dia=10, mes=8):
        v = Venda.objects.create(cliente=self.cli, data_venda=date(2026, mes, dia))
        ItemVenda(venda=v, produto=produto, quantidade=Decimal(qtd)).save()
        v.recompute_total()
        v.sincronizar_recebivel()
        return v


class ModeloRegrasTest(BaseData):
    def test_competencia_derivada_da_data(self):
        v = self.nova_venda(self.p1, 3, dia=10, mes=8)
        self.assertEqual(v.competencia.ano, 2026)
        self.assertEqual(v.competencia.mes, 8)
        self.assertEqual(v.competencia.rotulo, 'Agosto/2026')

    def test_canal_herdado_do_cliente(self):
        v = self.nova_venda(self.p1, 1)
        self.assertEqual(v.canal, self.canal)

    def test_item_snapshot_preco_e_custo(self):
        v = self.nova_venda(self.p1, 2)
        item = v.itens.first()
        self.assertEqual(item.preco_unitario, Decimal('7.00'))
        self.assertEqual(item.custo_unitario, Decimal('3.00'))  # snapshot analítico
        self.assertEqual(item.subtotal, Decimal('14.00'))
        self.assertEqual(v.valor_total, Decimal('14.00'))

    def test_snapshot_nao_muda_com_preco_futuro(self):
        v = self.nova_venda(self.p1, 2)
        self.p1.preco_venda = Decimal('9.00')
        self.p1.save()
        v.itens.first().refresh_from_db()
        self.assertEqual(v.itens.first().preco_unitario, Decimal('7.00'))

    def test_valores_sao_decimais(self):
        v = self.nova_venda(self.p1, 3)
        self.assertIsInstance(v.valor_total, Decimal)
        self.assertIsInstance(v.recebivel.a_receber, Decimal)

    def test_recebivel_status_aberto(self):
        v = self.nova_venda(self.p1, 3)
        self.assertEqual(v.recebivel.status, Recebivel.Status.ABERTO)
        self.assertEqual(v.recebivel.a_receber, Decimal('21.00'))

    def test_pagamento_parcial_status(self):
        v = self.nova_venda(self.p1, 3)  # 21
        services.registrar_pagamento(cliente=self.cli, valor=Decimal('10.00'), forma_pagamento='PIX',
                                     alocacoes=[{'recebivel': v.recebivel, 'valor': Decimal('10.00')}])
        v.recebivel.refresh_from_db()
        self.assertEqual(v.recebivel.status, Recebivel.Status.PARCIAL)
        self.assertEqual(v.recebivel.a_receber, Decimal('11.00'))

    def test_pagamento_consolidado_aloca_mais_antigo_primeiro(self):
        v1 = self.nova_venda(self.p1, 3, dia=10)  # 21, mais antiga
        v2 = self.nova_venda(self.p2, 2, dia=12)  # 12, mais nova
        services.registrar_pagamento(cliente=self.cli, valor=Decimal('25.00'), forma_pagamento='PIX')
        v1.recebivel.refresh_from_db()
        v2.recebivel.refresh_from_db()
        self.assertEqual(v1.recebivel.status, Recebivel.Status.PAGO)       # quitou os 21
        self.assertEqual(v2.recebivel.valor_pago, Decimal('4.00'))          # sobrou 4 para a nova
        self.assertEqual(v2.recebivel.a_receber, Decimal('8.00'))

    def test_quitar_venda(self):
        v = self.nova_venda(self.p1, 3)
        services.quitar_venda(venda=v, forma_pagamento='DINHEIRO', conta_recebimento=self.conta)
        v.recebivel.refresh_from_db()
        self.assertEqual(v.recebivel.status, Recebivel.Status.PAGO)
        self.assertEqual(v.recebivel.a_receber, Decimal('0.00'))

    def test_quitar_venda_ja_paga_retorna_none(self):
        v = self.nova_venda(self.p1, 1)
        services.quitar_venda(venda=v, forma_pagamento='PIX')
        self.assertIsNone(services.quitar_venda(venda=v, forma_pagamento='PIX'))

    def test_dashboard_agrega(self):
        v1 = self.nova_venda(self.p1, 3)  # 21
        self.nova_venda(self.p2, 2)       # 12
        services.quitar_venda(venda=v1, forma_pagamento='PIX')
        d = build_dashboard(v1.competencia)
        self.assertEqual(d['vendido'], Decimal('33.00'))
        self.assertEqual(d['recebido'], Decimal('21.00'))
        self.assertEqual(d['a_receber'], Decimal('12.00'))
        self.assertEqual(d['potes_vendidos'], Decimal('5.000'))
        self.assertEqual(d['num_vendas'], 2)


class ApiTest(BaseData):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username='op', password='x', is_active=True)
        self.client = APIClient()

    def test_exige_autenticacao(self):
        resp = self.client.get('/api/v1/vendas/')
        self.assertIn(resp.status_code, (401, 403))

    def test_cria_venda_aninhada_e_gera_recebivel(self):
        self.client.force_authenticate(self.user)
        payload = {
            'cliente': self.cli.id,
            'itens_input': [{'produto': self.p1.id, 'quantidade': '3'}],
        }
        resp = self.client.post('/api/v1/vendas/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(str(resp.data['valor_total']), '21.00')
        self.assertEqual(resp.data['recebivel']['status'], 'ABERTO')

    def test_venda_pagar_agora_vem_paga(self):
        self.client.force_authenticate(self.user)
        payload = {
            'cliente': self.cli.id,
            'itens_input': [{'produto': self.p1.id, 'quantidade': '2'}],
            'pagar_agora': True, 'forma_pagamento': 'PIX',
        }
        resp = self.client.post('/api/v1/vendas/', payload, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.data['recebivel']['status'], 'PAGO')
        self.assertEqual(str(resp.data['recebivel']['a_receber']), '0.00')

    def test_registrar_pagamento_endpoint(self):
        self.client.force_authenticate(self.user)
        v = self.nova_venda(self.p1, 3)
        resp = self.client.post('/api/v1/pagamentos/', {
            'cliente': self.cli.id, 'valor': '21.00', 'forma_pagamento': 'PIX',
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.content)
        v.recebivel.refresh_from_db()
        self.assertEqual(v.recebivel.status, 'PAGO')

    def test_venda_sem_itens_falha(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post('/api/v1/vendas/', {'cliente': self.cli.id, 'itens_input': []}, format='json')
        self.assertEqual(resp.status_code, 400)
