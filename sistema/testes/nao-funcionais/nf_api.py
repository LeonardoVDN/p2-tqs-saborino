"""Testes não funcionais pela API: desempenho, segurança básica e confiabilidade.
Uso: python3 nf_api.py <pasta-de-saida>   (com o sistema no ar; só biblioteca padrão do Python)"""
import http.cookiejar, json, statistics, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path

BASE = 'http://localhost:8000/api/v1'
EMAIL, SENHA = 'tester@saborino.test', 'SenhaFicticia-P2-2026'
SAIDA = Path(sys.argv[1] if len(sys.argv) > 1 else 'resultado'); SAIDA.mkdir(parents=True, exist_ok=True)


def seed():
    subprocess.run(['docker', 'exec', 'p2tqs-saborino-api-1', 'python', '/p2/seed.py'], check=True, capture_output=True)


class Sessao:
    def __init__(self):
        self.jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
        self.ultimos_cabecalhos = {}

    def csrf(self):
        return next((c.value for c in self.jar if 'csrf' in c.name), '')

    def req(self, metodo, rota, corpo=None, com_csrf=True):
        r = urllib.request.Request(BASE + rota, data=json.dumps(corpo).encode() if corpo is not None else None, method=metodo)
        r.add_header('Content-Type', 'application/json')
        if metodo != 'GET' and com_csrf:
            r.add_header('X-CSRFToken', self.csrf())
        try:
            with self.op.open(r) as resp:
                st, txt, cab = resp.status, resp.read().decode(), resp.headers
        except urllib.error.HTTPError as e:
            st, txt, cab = e.code, e.read().decode(), e.headers
        self.ultimos_cabecalhos = cab
        try:
            return st, json.loads(txt) if txt else None
        except ValueError:
            return st, txt[:200]

    def entrar(self):
        self.req('GET', '/auth/csrf/')
        st, _ = self.req('POST', '/auth/sessions/', {'email': EMAIL, 'password': SENHA})
        assert st == 204, st


def ids(s):
    _, ps = s.req('GET', '/produtos/')
    _, cs = s.req('GET', '/clientes/')
    p = {x['nome']: x['id'] for x in ps}
    return p['Bolo de Pote Teste'], p['Mousse Teste'], next(c['id'] for c in cs if c['nome'] == 'Cliente Fictício Carla')


def gravar(nome, linhas):
    texto = '\n'.join([f'# {nome} — {datetime.now().isoformat(timespec="seconds")}'] + linhas) + '\n'
    (SAIDA / f'{nome}.txt').write_text(texto, encoding='utf-8')
    print(texto)


def nf01_desempenho_api():
    seed(); s = Sessao(); s.entrar(); b, m, c = ids(s)
    ops = {
        'Listar clientes (GET /clientes/)': lambda: s.req('GET', '/clientes/'),
        'Abrir painel (GET /relatorios/dashboard/)': lambda: s.req('GET', '/relatorios/dashboard/'),
        'Registrar venda (POST /vendas/)': lambda: s.req('POST', '/vendas/', {'cliente': c, 'itens_input': [{'produto': b, 'quantidade': 2}, {'produto': m, 'quantidade': 1}]}),
        'Registrar pagamento (POST /pagamentos/)': lambda: s.req('POST', '/pagamentos/', {'cliente': c, 'valor': '1.00', 'forma_pagamento': 'PIX'}),
    }
    linhas = ['Critério: média de até 2 s por operação (RNF-02). 30 medições por operação, uma depois da outra.']
    for nome, f in ops.items():
        t = []
        for _ in range(30):
            ini = time.perf_counter(); st, _ = f(); t.append(time.perf_counter() - ini)
            assert st < 300, (nome, st)
        t.sort()
        linhas.append(f'{nome}: média {statistics.mean(t)*1000:.1f} ms | mediana {statistics.median(t)*1000:.1f} ms | p95 {t[28]*1000:.1f} ms | máximo {t[-1]*1000:.1f} ms')
    gravar('NF-01-desempenho-api', linhas); seed()


def nf05_seguranca():
    seed(); linhas = []
    anon = Sessao(); anon.req('GET', '/auth/csrf/')
    linhas.append('## a) Rotas de dados sem login (esperado: 401 ou 403 em todas)')
    for metodo, rota, corpo in [('GET', '/clientes/', None), ('POST', '/clientes/', {'nome': 'X'}), ('GET', '/produtos/', None), ('POST', '/produtos/', {'nome': 'X', 'preco_venda': '1.00'}),
                                ('GET', '/vendas/', None), ('POST', '/vendas/', {'cliente': 1, 'itens_input': []}), ('GET', '/pagamentos/', None), ('POST', '/pagamentos/', {'cliente': 1, 'valor': '1.00'}),
                                ('GET', '/recebiveis/', None), ('GET', '/relatorios/dashboard/', None), ('GET', '/relatorios/fechamento/', None), ('GET', '/me/', None)]:
        st, _ = anon.req(metodo, rota, corpo)
        linhas.append(f'{metodo} {rota} -> {st}')
    linhas.append('\n## b) Cookie de sessão depois do login')
    s = Sessao(); s.req('GET', '/auth/csrf/'); s.req('POST', '/auth/sessions/', {'email': EMAIL, 'password': SENHA})
    for c in s.ultimos_cabecalhos.get_all('Set-Cookie') or []:
        nome = c.split('=')[0]
        atributos = [a.strip().split('=')[0] for a in c.split(';')[1:]]
        linhas.append(f'{nome}: atributos {", ".join(atributos)}')
    linhas.append('\n## c) Requisição de escrita com sessão válida, mas sem o token CSRF (esperado: 403)')
    st, corpo = s.req('POST', '/clientes/', {'nome': 'Sem CSRF'}, com_csrf=False)
    linhas.append(f'POST /clientes/ sem X-CSRFToken -> {st} {json.dumps(corpo, ensure_ascii=False)[:150]}')
    st2, _ = s.req('POST', '/clientes/', {'nome': 'Com CSRF'})
    linhas.append(f'POST /clientes/ com X-CSRFToken -> {st2} (controle)')
    linhas.append('\n## d) Mensagem de login não revela se o e-mail existe (esperado: mesma resposta)')
    a = Sessao(); a.req('GET', '/auth/csrf/')
    r1 = a.req('POST', '/auth/sessions/', {'email': EMAIL, 'password': 'senha-errada'})
    r2 = a.req('POST', '/auth/sessions/', {'email': 'nao-existe@saborino.test', 'password': 'senha-errada'})
    linhas.append(f'e-mail existente com senha errada -> {r1[0]} {r1[1]}')
    linhas.append(f'e-mail inexistente -> {r2[0]} {r2[1]}')
    gravar('NF-05-seguranca-basica', linhas); seed()


def nf06_reinicio():
    seed(); s = Sessao(); s.entrar(); b, m, c = ids(s)
    st, v = s.req('POST', '/vendas/', {'cliente': c, 'itens_input': [{'produto': b, 'quantidade': 2}, {'produto': m, 'quantidade': 1}]})
    s.req('POST', '/pagamentos/', {'cliente': c, 'valor': '20.00', 'forma_pagamento': 'PIX'})
    _, antes = s.req('GET', f'/vendas/{v["id"]}/')
    linhas = ['Critério: depois de reiniciar o banco e a API, o sistema volta a responder em até 60 s e a venda e o pagamento continuam iguais.',
              f'Antes: venda #{v["id"]} total {antes["valor_total"]}, a receber {antes["recebivel"]["a_receber"]}, status {antes["recebivel"]["status"]}']
    ini = time.perf_counter()
    subprocess.run(['docker', 'restart', 'p2tqs-saborino-db-1', 'p2tqs-saborino-api-1'], check=True, capture_output=True)
    while True:
        try:
            with urllib.request.urlopen(BASE + '/auth/csrf/', timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            pass
        if time.perf_counter() - ini > 120:
            break
        time.sleep(0.5)
    volta = time.perf_counter() - ini
    linhas.append(f'Reinício de db e api: API voltou a responder {volta:.1f} s depois do comando docker restart')
    s2 = Sessao(); s2.entrar(); _, depois = s2.req('GET', f'/vendas/{v["id"]}/')
    linhas.append(f'Depois: venda #{v["id"]} total {depois["valor_total"]}, a receber {depois["recebivel"]["a_receber"]}, status {depois["recebivel"]["status"]}')
    st_antiga, _ = s.req('GET', '/me/')
    linhas.append(f'Sessão aberta antes do reinício continua válida: GET /me/ -> {st_antiga}')
    gravar('NF-06-confiabilidade-reinicio', linhas); seed()


def nf07_repeticao():
    seed(); s = Sessao(); s.entrar(); b, m, c = ids(s)
    totais, status = [], []
    for _ in range(20):
        st, v = s.req('POST', '/vendas/', {'cliente': c, 'itens_input': [{'produto': b, 'quantidade': 2}, {'produto': m, 'quantidade': 1}]})
        status.append(st); totais.append(v.get('valor_total') if isinstance(v, dict) else None)
    _, rs = s.req('GET', f'/recebiveis/?cliente={c}')
    soma = sum(float(r['a_receber']) for r in rs)
    gravar('NF-07-confiabilidade-repeticao', ['Critério: 20 vendas iguais seguidas, todas aceitas (201), com o mesmo total de 34,00, e a soma a receber igual a 20 × 34,00 = 680,00.',
           f'Status: {sorted(set(status))} ({status.count(201)} de 20 com 201)', f'Totais distintos: {sorted(set(totais))}',
           f'Valores a receber da cliente: {len(rs)} registros, soma {soma:.2f}'])
    seed()


if __name__ == '__main__':
    for f in [nf01_desempenho_api, nf05_seguranca, nf06_reinicio, nf07_repeticao]:
        f()
