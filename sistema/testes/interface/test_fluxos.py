"""Testes de sistema pela interface do Saborino (Selenium).

Cada teste percorre um fluxo inteiro do usuário e verifica o resultado na tela.
Entre parênteses, o requisito e o caso de teste manual que o teste representa.
"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from conftest import URL

EMAIL, SENHA = 'tester@saborino.test', 'SenhaFicticia-P2-2026'


def esperar(d, segundos=10):
    return WebDriverWait(d, segundos)


def botao(d, texto):
    return esperar(d).until(EC.element_to_be_clickable((By.XPATH, f"//button[contains(normalize-space(.), '{texto}')]")))


def texto_aparece(d, texto):
    return esperar(d).until(EC.text_to_be_present_in_element((By.TAG_NAME, 'body'), texto))


def entrar(d, senha=SENHA):
    d.get(URL + '/login')
    esperar(d).until(EC.visibility_of_element_located((By.ID, 'email'))).send_keys(EMAIL)
    d.find_element(By.ID, 'password').send_keys(senha)
    d.find_element(By.CSS_SELECTOR, 'form button.btn-primary').click()


def entrar_e_esperar_painel(d):
    entrar(d)
    texto_aparece(d, 'Vendido')


def registrar_venda_fiado(d):
    """2 Bolo de Pote Teste (12,00) + 1 Mousse Teste (10,00) para a Carla."""
    d.get(URL + '/venda')
    esperar(d).until(EC.visibility_of_element_located((By.CSS_SELECTOR, 'input[placeholder^="Buscar ou digitar"]'))).send_keys('Carla')
    botao(d, 'Cliente Fictício Carla').click()
    for nome in ['Bolo de Pote Teste', 'Bolo de Pote Teste', 'Mousse Teste']:
        botao(d, nome).click()
    botao(d, 'Fiado').click()
    total = d.find_element(By.CSS_SELECTOR, '.total-row').text
    botao(d, 'Salvar venda').click()
    texto_aparece(d, 'Venda registrada')
    return total


def linhas_a_receber(d):
    d.get(URL + '/a-receber')
    esperar(d).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'table.data tbody tr')))
    return [linha.text for linha in d.find_elements(By.CSS_SELECTOR, 'table.data tbody tr')]


# RF-01 · CT-001
def test_login_valido_abre_o_painel(navegador):
    entrar(navegador)
    esperar(navegador).until(EC.url_to_be(URL + '/'))
    assert texto_aparece(navegador, 'Vendido')


# RF-01 · CT-002
def test_login_com_senha_errada_mostra_mensagem_e_fica_no_login(navegador):
    entrar(navegador, senha='senha-errada')
    assert texto_aparece(navegador, 'E-mail ou senha inválidos.')
    assert navegador.current_url.endswith('/login')


# RNF-01 · CT-032
def test_tela_interna_sem_login_leva_ao_login(navegador):
    navegador.get(URL + '/clientes')
    assert esperar(navegador).until(EC.url_contains('/login'))


# RF-04 · CT-013
def test_venda_fiado_gera_valor_a_receber_de_34(navegador):
    entrar_e_esperar_painel(navegador)
    total = registrar_venda_fiado(navegador)
    assert 'R$ 34,00' in total
    linhas = linhas_a_receber(navegador)
    assert len(linhas) == 1
    assert 'R$ 34,00' in linhas[0] and 'ABERTO' in linhas[0]


# RF-05 · CT-021
def test_pagamento_parcial_deixa_saldo_de_14_e_status_parcial(navegador):
    entrar_e_esperar_painel(navegador)
    registrar_venda_fiado(navegador)
    linhas_a_receber(navegador)
    Select(navegador.find_element(By.CSS_SELECTOR, '.card select.select:not(.comp-select)')).select_by_index(1)
    navegador.find_element(By.CSS_SELECTOR, 'input[placeholder="Valor"]').send_keys('20')
    botao(navegador, 'Registrar').click()
    texto_aparece(navegador, 'Pagamento registrado')
    esperar(navegador).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'table.data tbody'), 'PARCIAL'))
    linha = navegador.find_element(By.CSS_SELECTOR, 'table.data tbody tr').text
    assert 'R$ 14,00' in linha and 'PARCIAL' in linha


# RF-03 · CT-011 · falha enquanto o DEF-001 não for corrigido
def test_produto_com_nome_repetido_mostra_erro_na_tela(navegador):
    entrar_e_esperar_painel(navegador)
    navegador.get(URL + '/produtos')
    botao(navegador, 'Novo produto').click()
    esperar(navegador).until(EC.visibility_of_element_located((By.CSS_SELECTOR, '.grid2 input.input:not([type=number])'))).send_keys('Mousse Teste')
    navegador.find_elements(By.CSS_SELECTOR, '.grid2 input[type=number]')[0].send_keys('10')
    botao(navegador, 'Salvar').click()
    assert texto_aparece(navegador, 'já existe')
