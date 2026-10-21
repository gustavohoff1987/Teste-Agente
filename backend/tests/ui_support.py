"""Navegação compartilhada para a interface vigente; só permite URLs locais."""
import os
from urllib.parse import urlparse
from playwright.sync_api import expect

URL = os.getenv("ADT_UI_URL", "http://127.0.0.1:5173/")
assert urlparse(URL).hostname in ("127.0.0.1", "localhost", "::1")
TITLES = ["Densidade", "Quantitativos", "Distribuição", "Comparações", "Evolução temporal",
          "Agregações", "Análise espacial", "Recortes e rankings", "Rotatividade", "Relatórios",
          "Referência mais próxima", "Critérios combinados"]


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
    expect(card(page)).to_have_attribute("aria-label", "Selecionar análise: " + title)
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


def expand(toggle):
    """Abre a lista de uma caixa das configurações (período ou abrangência territorial), se estiver fechada."""
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    expect(toggle).to_have_attribute("aria-expanded", "true")


def workspace(page, stage):
    """Percorre as áreas visíveis, sem forçar interação com controles ocultos.

    A seleção territorial é um bloco da preparação: "territories" abre a preparação e expande esse bloco. Na base
    oficial, o bloco é a caixa "Abrangência territorial" das configurações, com o Brasil, os estados e os municípios."""
    names = {"territories": "1. Preparação", "preparation": "1. Preparação", "results": "2. Resultados"}
    button = page.get_by_role("button", name=names[stage], exact=True)
    button.click()
    expect(button).to_have_attribute("aria-current", "step")
    if stage == "territories":
        card = page.get_by_test_id("territory-card")
        expect(card).to_be_visible()
        toggle = card.get_by_test_id("territory-toggle")
        if toggle.count():  # fora da base oficial, no recorte nacional o bloco só informa o território único
            expand(toggle)


def municipality(region, code):
    """Base oficial: caixa de marcar de um município na abrangência territorial. Quando a lista do estado (prefixo do
    código IBGE) ainda não está à vista, escolhe o estado no seletor "Estado dos municípios"."""
    option = region.get_by_test_id("territory-option-code-" + code)
    if not option.count():
        state = region.get_by_test_id("territory-municipal-state")
        if state.count():
            state.select_option(code[:2])
    expect(option).to_have_count(1)
    return option


def municipal_group(region, prefix):
    """Base oficial: caixa "Todos os municípios" de um estado, à vista depois de escolher o estado no seletor."""
    region.get_by_test_id("territory-municipal-state").select_option(prefix)
    group = region.get_by_test_id("territory-group-check-" + prefix)
    expect(group).to_have_count(1)
    return group


def choose(inline, label, column):
    """Escolhe a coluna de um campo no seletor da preparação (D1): a sugestão aparece no topo, mas nunca é selecionada
    em silêncio; escolher a coluna estabelece o papel. Não há botão de confirmação."""
    field = inline.get_by_label(label, exact=True)
    expect(field).to_be_visible()
    field.select_option(column)
    expect(field).to_have_value(column)
    return field


def stage(page, number):
    panel = page.get_by_role("region", name="Preparação da análise")
    names = ["1. Identificar os dados", "2. Parâmetros", "3. Revisar e executar"]
    panel.get_by_role("button", name=names[number-1], exact=False).click()
    expect(panel.get_by_text(f"Etapa {number} de 3", exact=True)).to_be_visible()
