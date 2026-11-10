"""Configuração dos testes de interface: navegador, dados restaurados e prints."""
import os
import subprocess
from pathlib import Path

import pytest
from selenium import webdriver

URL = os.environ.get('SABORINO_URL', 'http://localhost:5173')
SAIDA = Path(os.environ.get('SAIDA', Path(__file__).parent / 'resultado'))


def restaurar_dados():
    subprocess.run(['docker', 'exec', 'p2tqs-saborino-api-1', 'python', '/p2/seed.py'], check=True, capture_output=True)


@pytest.fixture
def navegador(request):
    restaurar_dados()
    opcoes = webdriver.ChromeOptions()
    if os.environ.get('MOSTRAR_NAVEGADOR') != '1':
        opcoes.add_argument('--headless=new')
    opcoes.add_argument('--window-size=1280,1000')
    driver = webdriver.Chrome(options=opcoes)
    yield driver
    SAIDA.mkdir(parents=True, exist_ok=True)
    falhou = getattr(request.node, 'rep_call', None) and request.node.rep_call.failed
    driver.save_screenshot(str(SAIDA / f'{request.node.name}{"-FALHOU" if falhou else ""}.png'))
    driver.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    resultado = yield
    rep = resultado.get_result()
    if rep.when == 'call':
        item.rep_call = rep
