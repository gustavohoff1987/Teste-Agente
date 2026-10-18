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
    choices = page.get_by_role("group", name="Carrossel de tipos de análise")
    if not choices.is_visible():
        page.get_by_text("Escolher outra análise", exact=True).click()
    card(page).press("Home")
    for _ in range(TITLES.index(title)):
        page.get_by_role("button", name="Próxima análise", exact=True).click()
    card(page).click()


def execute_analysis(page, button, double=False):
    """Mantém a intenção das jornadas progressivas, escolhendo composição explicitamente."""
    button.dblclick() if double else button.click()
    dialog = page.get_by_test_id("new-analysis-confirmation")
    if dialog.is_visible():
        expect(dialog).to_contain_text("preservando os resultados e parâmetros")
        dialog.get_by_test_id("append-diagnostic").click()


def end_session(page):
    page.get_by_test_id("nav-new-session").click()
    expect(page.get_by_test_id("new-session-confirmation")).to_be_visible()
    page.get_by_test_id("confirm-new-session").click()


def stage(page, number):
    panel = page.get_by_role("region", name="Preparação da análise")
    names = ["1. Identificar os dados", "2. Parâmetros e confirmações", "3. Revisar e executar"]
    panel.get_by_role("button", name=names[number-1], exact=False).click()
    expect(panel.get_by_text(f"Etapa {number} de 3", exact=True)).to_be_visible()
