"""Gera a coleção do Postman e o ambiente local a partir de uma descrição única (rodar com python3)."""
import json

URL = '{{base_url}}'
JSON_H = [{'key': 'Content-Type', 'value': 'application/json'}, {'key': 'X-CSRFToken', 'value': '{{csrf}}'}]


def req(nome, metodo, rota, testes, corpo=None, desc=''):
    r = {'method': metodo, 'header': JSON_H if metodo != 'GET' else [], 'url': {'raw': URL + rota, 'host': [URL], 'path': [p for p in rota.split('?')[0].split('/') if p] + ([''] if rota.split('?')[0].endswith('/') else [])}}
    if '?' in rota:
        r['url']['query'] = [{'key': k, 'value': v} for k, v in (x.split('=') for x in rota.split('?')[1].split('&'))]
    if corpo is not None:
        r['body'] = {'mode': 'raw', 'raw': json.dumps(corpo, ensure_ascii=False, indent=2), 'options': {'raw': {'language': 'json'}}}
    return {'name': nome, 'description': desc, 'request': r, 'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': testes}}]}


def status(c):
    return [f'pm.test("Status {c}", () => pm.response.to.have.status({c}));']


pastas = [
 ('Autenticação', [
  req('Obter token CSRF', 'GET', '/auth/csrf/', status(200) + ['const j = pm.response.json();', 'pm.test("Contrato: csrfToken é texto", () => pm.expect(j.csrfToken).to.be.a("string").and.not.empty);', 'pm.collectionVariables.set("csrf", j.csrfToken);']),
  req('Login com senha errada', 'POST', '/auth/sessions/', status(401) + ['pm.test("Mensagem de erro", () => pm.expect(pm.response.json().detail).to.eql("E-mail ou senha inválidos."));'], {'email': '{{email}}', 'password': 'senha-errada'}, 'CT-002 / RF-01 (negativo)'),
  req('Login válido', 'POST', '/auth/sessions/', status(204), {'email': '{{email}}', 'password': '{{senha}}'}, 'CT-001 / RF-01 (positivo)'),
  req('Renovar token CSRF depois do login', 'GET', '/auth/csrf/', status(200) + ['pm.collectionVariables.set("csrf", pm.response.json().csrfToken);'], desc='O token CSRF muda depois do login.'),
  req('Usuário logado', 'GET', '/me/', status(200) + ['const j = pm.response.json();', 'pm.test("Contrato: id e email", () => { pm.expect(j).to.have.property("id"); pm.expect(j.email).to.eql(pm.environment.get("email") || pm.collectionVariables.get("email")); });']),
 ]),
 ('Cadastros', [
  req('Listar produtos', 'GET', '/produtos/', status(200) + ['const j = pm.response.json();', 'pm.test("Contrato: lista com id, nome e preco_venda", () => { pm.expect(j).to.be.an("array").that.is.not.empty; j.forEach(p => pm.expect(p).to.include.keys("id", "nome", "preco_venda")); });', 'const bolo = j.find(p => p.nome === "Bolo de Pote Teste"); const mousse = j.find(p => p.nome === "Mousse Teste");', 'pm.test("Produtos do seed presentes", () => { pm.expect(bolo).to.be.ok; pm.expect(mousse).to.be.ok; });', 'pm.collectionVariables.set("bolo_id", bolo.id); pm.collectionVariables.set("mousse_id", mousse.id);']),
  req('Cadastrar cliente válido', 'POST', '/clientes/', status(201) + ['const j = pm.response.json();', 'pm.test("Nome gravado", () => pm.expect(j.nome).to.eql("Cliente Postman"));', 'pm.collectionVariables.set("cliente_id", j.id);'], {'nome': 'Cliente Postman'}, 'CT-004 / RF-02 (positivo)'),
  req('Cadastrar cliente com nome vazio', 'POST', '/clientes/', status(400) + ['pm.test("Erro no campo nome", () => pm.expect(pm.response.json()).to.have.property("nome"));'], {'nome': ''}, 'CT-006 / RF-02 (negativo)'),
 ]),
 ('Vendas', [
  req('Registrar venda fiado', 'POST', '/vendas/', status(201) + ['const j = pm.response.json();', 'pm.test("Total 34,00", () => pm.expect(j.valor_total).to.eql("34.00"));', 'pm.test("Gera valor a receber ABERTO de 34,00", () => { pm.expect(j.recebivel.status).to.eql("ABERTO"); pm.expect(j.recebivel.a_receber).to.eql("34.00"); });', 'pm.collectionVariables.set("venda_id", j.id);'], {'cliente': '{{cliente_id}}', 'itens_input': [{'produto': '{{bolo_id}}', 'quantidade': 2}, {'produto': '{{mousse_id}}', 'quantidade': 1}]}, 'CT-013 / RF-04 (positivo)'),
  req('Registrar venda sem itens', 'POST', '/vendas/', status(400) + ['pm.test("Mensagem de item obrigatório", () => pm.expect(pm.response.json().itens_input[0]).to.eql("A venda precisa de ao menos um item."));'], {'cliente': '{{cliente_id}}', 'itens_input': []}, 'CT-015 / RF-04 (negativo)'),
  req('Registrar venda com quantidade negativa', 'POST', '/vendas/', status(400), {'cliente': '{{cliente_id}}', 'itens_input': [{'produto': '{{bolo_id}}', 'quantidade': -2}]}, 'CT-017 / RF-04 (negativo). Falha esperada enquanto o DEF-004 não for corrigido.'),
 ]),
 ('Recebimentos', [
  req('Registrar pagamento parcial', 'POST', '/pagamentos/', status(201) + ['const j = pm.response.json();', 'pm.test("Aloca 20,00 na venda", () => pm.expect(j.alocacoes[0].valor_aplicado).to.eql("20.00"));'], {'cliente': '{{cliente_id}}', 'valor': '20.00', 'forma_pagamento': 'PIX'}, 'CT-021 / RF-05 (positivo)'),
  req('Saldo depois do pagamento parcial', 'GET', '/recebiveis/?cliente={{cliente_id}}', status(200) + ['const r = pm.response.json()[0];', 'pm.test("Saldo 14,00 e status PARCIAL", () => { pm.expect(r.a_receber).to.eql("14.00"); pm.expect(r.status).to.eql("PARCIAL"); });'], desc='CT-021 / RF-05'),
  req('Registrar pagamento negativo', 'POST', '/pagamentos/', status(400), {'cliente': '{{cliente_id}}', 'valor': '-5.00', 'forma_pagamento': 'PIX'}, 'CT-027 / RF-05 (negativo). Falha esperada enquanto o DEF-008 não for corrigido.'),
  req('Quitar o saldo da venda', 'POST', '/vendas/{{venda_id}}/quitar/', status(201) + ['pm.test("Quita os 14,00 restantes", () => pm.expect(pm.response.json().valor).to.eql("14.00"));'], {'forma_pagamento': 'PIX'}, 'CT-022 / RF-05 (positivo)'),
  req('Quitar venda já paga', 'POST', '/vendas/{{venda_id}}/quitar/', status(400) + ['pm.test("Mensagem de venda quitada", () => pm.expect(pm.response.json().detail).to.eql("Venda já está quitada."));'], {'forma_pagamento': 'PIX'}, 'CT-028 / RF-05 (negativo)'),
 ]),
 ('Segurança', [
  req('Sair (logout)', 'DELETE', '/auth/session/', status(204), desc='CT-003 / RF-01'),
  req('Listar clientes sem login', 'GET', '/clientes/', status(401), desc='CT-031 / RNF-01'),
 ]),
]

colecao = {
 'info': {'name': 'Saborino · Testes de API (P2 TQS)', 'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json',
          'description': 'Testes de integração da API do Saborino (cópia local com dados fictícios). Antes de rodar, restaure os dados com o seed (ver README do repositório). Rode as pastas em ordem: as requisições passam dados umas para as outras (cliente, produtos, venda).'},
 'event': [{'listen': 'test', 'script': {'type': 'text/javascript', 'exec': ['pm.test("Responde em até 2 s", () => pm.expect(pm.response.responseTime).to.be.below(2000));']}}],
 'variable': [{'key': k, 'value': ''} for k in ['csrf', 'bolo_id', 'mousse_id', 'cliente_id', 'venda_id']],
 'item': [{'name': n, 'item': itens} for n, itens in pastas],
}
ambiente = {'name': 'Saborino local (P2 TQS)', 'values': [
 {'key': 'base_url', 'value': 'http://localhost:8000/api/v1', 'type': 'default', 'enabled': True},
 {'key': 'email', 'value': 'tester@saborino.test', 'type': 'default', 'enabled': True},
 {'key': 'senha', 'value': 'SenhaFicticia-P2-2026', 'type': 'secret', 'enabled': True}]}
json.dump(colecao, open('saborino-api.postman_collection.json', 'w'), ensure_ascii=False, indent=2)
json.dump(ambiente, open('saborino-local.postman_environment.json', 'w'), ensure_ascii=False, indent=2)
print(sum(len(i) for _, i in pastas), 'requisições')
