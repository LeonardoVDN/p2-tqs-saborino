"""Testes não funcionais pela interface: tempo de carregamento das telas e compatibilidade (resoluções e Safari).
Uso: python nf_interface.py <pasta-de-saida>   (com o sistema no ar; precisa do selenium)"""
import statistics, subprocess, sys, time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

URL = 'http://localhost:5173'
EMAIL, SENHA = 'tester@saborino.test', 'SenhaFicticia-P2-2026'
SAIDA = Path(sys.argv[1] if len(sys.argv) > 1 else 'resultado')  # opcional: nomes dos testes depois da pasta (nf02 nf03 nf04); SAIDA.mkdir(parents=True, exist_ok=True)


def seed():
    subprocess.run(['docker', 'exec', 'p2tqs-saborino-api-1', 'python', '/p2/seed.py'], check=True, capture_output=True)


def chrome(largura, altura):
    o = webdriver.ChromeOptions(); o.add_argument('--headless=new'); o.add_argument(f'--window-size={largura},{altura}')
    return webdriver.Chrome(options=o)


def esperar_texto(d, texto, seg=15):
    WebDriverWait(d, seg).until(EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), texto))


def botao(d, texto):
    """Rola até o botão (como o usuário faria em tela pequena) e devolve o elemento pronto para clicar."""
    el = WebDriverWait(d, 15).until(EC.presence_of_element_located((By.XPATH, f"//button[contains(normalize-space(.), '{texto}')]")))
    d.execute_script("arguments[0].scrollIntoView({block: 'center'})", el)
    return WebDriverWait(d, 15).until(EC.element_to_be_clickable(el))


def entrar(d):
    d.get(URL + '/login')
    WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.ID, 'email'))).send_keys(EMAIL)
    d.find_element(By.ID, 'password').send_keys(SENHA)
    d.find_element(By.CSS_SELECTOR, 'form button.btn-primary').click()
    esperar_texto(d, 'Vendido')


def fluxo_venda(d):
    """Login, venda fiado de 2 bolos e 1 mousse e conferência em A receber. Devolve o texto da linha."""
    entrar(d)
    d.get(URL + '/venda')
    WebDriverWait(d, 15).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder^="Buscar ou digitar"]'))).send_keys('Carla')
    botao(d, 'Cliente Fictício Carla').click()
    for nome in ['Bolo de Pote Teste', 'Bolo de Pote Teste', 'Mousse Teste']:
        botao(d, nome).click()
    botao(d, 'Fiado').click(); botao(d, 'Salvar venda').click(); esperar_texto(d, 'Venda registrada')
    d.get(URL + '/a-receber')
    WebDriverWait(d, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.data tbody tr')))
    return d.find_element(By.CSS_SELECTOR, 'table.data tbody tr').text.replace('\n', ' ')


def sobra_horizontal(d):
    return d.execute_script('return document.documentElement.scrollWidth - document.documentElement.clientWidth')


def gravar(nome, linhas):
    texto = '\n'.join([f'# {nome} — {datetime.now().isoformat(timespec="seconds")}'] + linhas) + '\n'
    (SAIDA / f'{nome}.txt').write_text(texto, encoding='utf-8'); print(texto)


def nf02_tempo_telas():
    seed(); d = chrome(1280, 1000); entrar(d)
    telas = [('Painel', '/', 'Vendido'), ('Nova venda', '/venda', 'Produtos'), ('A receber', '/a-receber', 'Total em aberto'), ('Clientes', '/clientes', 'Novo cliente'), ('Fechamento', '/fechamento', 'Resultado por competência')]
    linhas = ['Critério: cada tela fica pronta (texto principal visível) em até 2 s, em média. 5 aberturas por tela, com recarga completa da página.']
    for nome, rota, marca in telas:
        t = []
        for _ in range(5):
            ini = time.perf_counter(); d.get(URL + rota); esperar_texto(d, marca); t.append(time.perf_counter() - ini)
        linhas.append(f'{nome} ({rota}): média {statistics.mean(t):.2f} s | mínimo {min(t):.2f} s | máximo {max(t):.2f} s')
    d.quit(); gravar('NF-02-desempenho-telas', linhas); seed()


def nf03_resolucoes():
    linhas = ['Critério: o fluxo de venda funciona do início ao fim e a página não cria rolagem horizontal. Navegador: Chrome.']
    for nome, (lg, alt) in [('computador 1366x768', (1366, 768)), ('celular 390x844', (390, 844))]:
        seed(); d = chrome(lg, alt)
        try:
            linha = fluxo_venda(d)
            res = f'fluxo concluído; A receber: "{linha}"'
        except Exception as e:
            res = f'fluxo interrompido: {type(e).__name__}'
        arq = f'NF-03-{lg}x{alt}.png'; d.save_screenshot(str(SAIDA / arq))
        linhas.append(f'{nome}: {res} | rolagem horizontal da página: {sobra_horizontal(d)} px | print {arq}')
        d.quit()
    gravar('NF-03-compatibilidade-resolucoes', linhas); seed()


def nf04_safari():
    seed()
    try:
        d = webdriver.Safari()
    except Exception as e:
        gravar('NF-04-compatibilidade-safari', ['Não executado: o Safari não aceitou a automação.', f'Erro: {str(e).splitlines()[0][:300]}'])
        return
    try:
        d.set_window_size(1280, 1000)
        linha = fluxo_venda(d); res = f'fluxo concluído; A receber: "{linha}"'
    except Exception as e:
        res = f'fluxo interrompido: {type(e).__name__}: {str(e).splitlines()[0][:200] if str(e) else ""}'
    d.save_screenshot(str(SAIDA / 'NF-04-safari.png'))
    gravar('NF-04-compatibilidade-safari', ['Critério: o mesmo fluxo de venda do NF-03 funciona no Safari.', f'Safari {d.capabilities.get("browserVersion")}: {res} | print NF-04-safari.png'])
    d.quit(); seed()


if __name__ == '__main__':
    so = sys.argv[2:] or ['nf02', 'nf03', 'nf04']
    for nome, f in [('nf02', nf02_tempo_telas), ('nf03', nf03_resolucoes), ('nf04', nf04_safari)]:
        if nome in so:
            f()
