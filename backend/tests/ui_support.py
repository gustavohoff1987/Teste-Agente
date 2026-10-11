"""Navegação compartilhada para a interface vigente; só permite URLs locais."""
import os
from urllib.parse import urlparse
from playwright.sync_api import expect

URL = os.getenv("ADT_UI_URL", "http://127.0.0.1:5173/")
assert urlparse(URL).hostname in ("127.0.0.1", "localhost", "::1")
TITLES = ["Densidade", "Quantitativos", "Distribuição", "Comparações", "Evolução temporal",
          "Agregações", "Análise espacial", "Recortes e rankings", "Rotatividade", "Relatórios"]


def offline(context):
    context.route("**/*", lambda route: route.continue_() if urlparse(route.request.url).hostname
                  in ("127.0.0.1", "localhost", "::1") else route.abort())


def card(page):
    return page.get_by_role("group", name="Carrossel de tipos de análise").locator('button[aria-pressed]')


def select(page, title):
    card(page).press("Home")
    for _ in range(TITLES.index(title)):
        page.get_by_role("button", name="Próxima análise", exact=True).click()
    card(page).click()


def stage(page, number):
    panel = page.get_by_role("region", name="Preparação da análise")
    names = ["1. Identificar os dados", "2. Parâmetros e confirmações", "3. Revisar e executar"]
    panel.get_by_role("button", name=names[number-1], exact=False).click()
    expect(panel.get_by_text(f"Etapa {number} de 3", exact=True)).to_be_visible()
