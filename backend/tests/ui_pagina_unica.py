"""Página única de análise (22/10/2026): a estrutura da página, sem as telas clássicas.

Percorre:
- o aceite de privacidade primeiro;
- a abertura (E0): o nome do agente, Nova sessão, Nova análise (desabilitada) e Histórico, sem Início nem Resultados; a
  fonte ("Dados do Brasil" e "Enviar meus dados"); a conversa aberta e mais larga, perguntando o que analisar; nenhum pedido
  ao motor antes dos dados;
- a base do Brasil (E1): o resumo da fonte e a porta de entrada nos estados (nunca todos os municípios de início);
- o Histórico, que guarda cada análise e reabre sem recalcular, e Nova análise, que guarda a atual e volta a E1 com os
  mesmos dados;
- o diálogo de Nova sessão, com o foco preso nele e o CSV da análise em exibição (valores do motor, em precisão integral);
- a caixa da conversa, que o mouse e o teclado movem, guarda a posição e se minimiza;
- uma planilha de outro país, com distritos e províncias e sem código IBGE, pelo painel "Colunas": papéis sugeridos e
  escolhidos, nomes das unidades e dos grupos, referencial das coordenadas (SIRGAS 2000 ou WGS 84, sem conversão) e o que a
  planilha permite;
  a área recebe o arquivo, o mapeamento e as premissas; nenhum texto da estrutura diz "município";
- uma planilha com duas abas (a escolha da aba), um formato recusado e "Cancelar", que mantém a fonte em uso;
- o celular (390 px) sem rolagem horizontal, com a conversa ancorada embaixo;
- o fim da sessão: a falha ao encerrar mantém tudo; o encerramento revoga a sessão no servidor.

Catálogo sintético do Bloco 1 ou, com ADT_BLOCK1_REAL=1, a base versionada (somente leitura). Servidor serve_ui_offline.py;
nunca chama o provedor de IA. A área de análise é da frente B2: este roteiro só usa a raiz dela (AREA em ui_support.py) e
confere pela rede o que ela pede ao motor (/api/painel). As planilhas de teste são criadas aqui, numa pasta temporária.
"""
import csv
import io
import json
import os
import re
import tempfile
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import expect, sync_playwright
from ui_support import (AREA, PRIVACIDADE, URL, accept_privacy, form_field, history_label, is_post,
                        no_horizontal_scroll, offline, options_of, uploaded_filename)

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
SEM_MUNICIPIO = re.compile("munic", re.IGNORECASE)
# Planilha de outro país: distritos agrupados em províncias, sem código IBGE, com coordenadas fixas e quatro anos.
DISTRITOS = [("Alfa", "Norte", 1000, "-10.10", "-40.20"), ("Beta", "Norte", 2500, "-10.40", "-40.60"),
             ("Gama", "Sul", 4000, "-12.00", "-42.10"), ("Delta", "Sul", 800, "-12.30", "-42.50")]
MAPEAMENTO_DOS_DISTRITOS = {"territory": "distrito", "grupo_territorial": "provincia", "period": "ano", "category": "categoria",
                            "count": "quantidade", "population": "populacao", "latitude": "latitude", "longitude": "longitude"}


def planilha_de_distritos(pasta):
    linhas = ["distrito;provincia;ano;categoria;quantidade;populacao;latitude;longitude"]
    for ano, extra in ((2021, 0), (2022, 1), (2023, 2), (2024, 3)):
        for indice, (nome, provincia, populacao, latitude, longitude) in enumerate(DISTRITOS):
            linhas.append(f"{nome};{provincia};{ano};MEDICINA;{5 + indice + extra};{populacao};{latitude};{longitude}")
    caminho = pasta / "distritos.csv"
    caminho.write_text("\n".join(linhas) + "\n", encoding="utf-8")
    return caminho


def planilha_de_duas_abas(pasta):
    livro = Workbook()
    livro.active.title = "Notas"
    livro.active.append(["observacao"])
    livro.active.append(["Os dados estão na aba Dados"])
    dados = livro.create_sheet("Dados")
    dados.append(["distrito", "ano", "quantidade"])
    dados.append(["Alfa", 2024, 10])
    caminho = pasta / "duas-abas.xlsx"
    livro.save(caminho)
    return caminho


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = "-real" if real else ""
    with tempfile.TemporaryDirectory(prefix="adt-pagina-unica-") as temporaria, sync_playwright() as p:
        pasta = Path(temporaria)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, llm_calls, analyze_calls, painel = [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: analyze_calls.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.on("request", lambda request: painel.append(request) if request.url.endswith("/api/painel") else None)
        area = page.get_by_test_id(AREA["raiz"])
        chat = page.get_by_test_id("painel-chat")
        fonte = page.get_by_test_id("fonte-barra")
        navigation = page.get_by_test_id("main-navigation")
        historico = page.get_by_test_id("nav-history")
        menu = page.get_by_test_id("analysis-history-menu")
        itens = menu.get_by_test_id("historico-item")

        def shot(name):
            page.wait_for_timeout(700)
            page.screenshot(path=str(OUTPUT / ("pagina-unica-" + name + suffix + ".png")), full_page=True)

        def painel_response(action, timeout=180000):
            """Executa a ação e devolve a resposta de /api/painel, as opções e o pedido (formulário) correspondentes."""
            with page.expect_response(lambda r: is_post(r, "/api/painel"), timeout=timeout) as event:
                action()
            response = event.value
            assert response.status == 200, response.text()[:2000]
            return response.json(), options_of(response.request), response.request

        def escolher_arquivo(caminho):
            fonte.get_by_test_id("fonte-trocar").click()
            expect(fonte.get_by_test_id("fonte-cancelar")).to_be_visible()
            with page.expect_file_chooser() as escolha:
                fonte.get_by_test_id("fonte-arquivo").click()
            escolha.value.set_files(str(caminho))

        page.goto(URL)
        # 1. Abertura (E0): o aceite de privacidade primeiro; depois, a estrutura sem as telas clássicas e a conversa
        # perguntando o que analisar. Nada é pedido ao motor antes dos dados.
        privacidade = page.get_by_role("dialog", name=PRIVACIDADE)
        expect(privacidade).to_be_visible()
        expect(page.get_by_test_id("fonte-brasil")).to_be_disabled()
        accept_privacy(page)
        expect(privacidade).to_have_count(0)
        expect(page.get_by_test_id("pagina-marca")).to_contain_text("Agente Diagnóstico Territorial")
        assert navigation.locator(":scope > button").all_text_contents() == ["Nova sessão", "Nova análise"]
        expect(historico).to_contain_text("Histórico")
        expect(historico).to_contain_text(history_label(0))
        for removed in ("nav-home", "nav-results", "analysis-catalog", "stage-tabs", "painel-voltar", "conversation-pane",
                        "territory-card", "investigation-overview"):
            expect(page.get_by_test_id(removed)).to_have_count(0)
        for removed in ("#preparacao-conversacional", "#resultados"):
            expect(page.locator(removed)).to_have_count(0)
        expect(page.get_by_test_id("nav-new-analysis")).to_be_disabled()
        expect(fonte.get_by_test_id("fonte-brasil")).to_have_text("Dados do Brasil")
        expect(fonte.get_by_test_id("fonte-arquivo")).to_have_text("Enviar meus dados")
        expect(page.get_by_test_id("current-source")).to_have_count(0)
        expect(area).to_be_visible()
        expect(chat).to_have_attribute("data-minimizada", "false")
        expect(chat).to_have_attribute("data-ampla", "true")
        expect(chat.get_by_test_id("painel-chat-guia")).to_contain_text(
            "O que você quer analisar? Prefere começar com os dados do Brasil ou enviar os seus?")
        expect(chat.get_by_test_id("chat-fonte-brasil")).to_be_visible()
        expect(chat.get_by_test_id("chat-fonte-arquivo")).to_be_visible()
        page.wait_for_timeout(800)
        assert not painel, "antes dos dados, a área não pede nada ao motor"
        shot("01-abertura")

        # 2. Base do Brasil (E1): o resumo da fonte no alto e os estados como porta de entrada, nunca todos os municípios.
        with page.expect_response(lambda r: is_post(r, "/api/painel"), timeout=180000) as primeiro:
            with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=180000) as inspecao:
                fonte.get_by_test_id("fonte-brasil").click()
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        assert primeiro.value.status == 200, primeiro.value.text()[:2000]
        e1, sent = primeiro.value.json(), options_of(primeiro.value.request)
        assert sent.get("nivel") == "estados", sent
        assert not sent.get("base", {}).get("municipios", {}).get("todos"), sent
        if real:
            assert len([item for item in e1["itens"] if item.get("tipo") == "estado"]) == 27, len(e1["itens"])
        periodos = "jan/2014 a jun/2024" if real else "jan/2023 a jun/2024"
        expect(page.get_by_test_id("current-source")).to_have_text("Dados do Brasil · Medicina · " + periodos)
        expect(fonte.get_by_test_id("fonte-trocar")).to_be_visible()
        expect(fonte.get_by_test_id("fonte-brasil")).to_have_count(0)
        expect(fonte.get_by_test_id("colunas-abrir")).to_have_count(0)
        expect(fonte.locator("summary", has_text="Diagnóstico técnico da fonte")).to_be_visible()
        expect(page.get_by_test_id("nav-new-analysis")).to_be_enabled()
        expect(chat).to_have_attribute("data-ampla", "false")
        expect(chat.get_by_test_id("painel-chat-guia")).to_contain_text(
            "Escolha no gráfico quais estados abrir, ou me diga quais municípios quer ver.")
        shot("02-estados")

        # 3. Histórico e Nova análise: a análise fica guardada, a nova volta a E1 com os mesmos dados, e o Histórico reabre a
        # anterior como estava, sem recalcular. Escape fecha o menu e devolve o foco.
        expect(historico).to_contain_text(history_label(1), timeout=30000)
        _, segunda, _ = painel_response(lambda: navigation.get_by_test_id("nav-new-analysis").click())
        expect(page.get_by_test_id("pagina-aviso")).to_have_text("Análise guardada no Histórico. Nova análise com os mesmos dados.")
        assert segunda.get("nivel") == "estados", segunda
        expect(page.get_by_test_id("current-source")).to_have_text("Dados do Brasil · Medicina · " + periodos)
        expect(historico).to_contain_text(history_label(2), timeout=30000)
        historico.click()
        expect(menu).to_have_attribute("open", "")
        expect(itens).to_have_count(2)
        expect(itens.first).to_have_attribute("aria-current", "true")  # a mais recente, em exibição
        expect(itens.first).to_be_disabled()
        chamadas = len(painel)
        itens.nth(1).click()
        expect(page.get_by_test_id("pagina-aviso")).to_contain_text("Análise reaberta como estava, sem recalcular")
        expect(menu).not_to_have_attribute("open", "")
        page.wait_for_timeout(1500)
        assert len(painel) == chamadas, "reabrir do Histórico não recalcula"
        historico.click()
        expect(itens.nth(1)).to_have_attribute("aria-current", "true")
        page.keyboard.press("Escape")
        expect(menu).not_to_have_attribute("open", "")
        expect(historico).to_be_focused()
        shot("03-historico")

        # 4. Nova sessão: o diálogo oferece o CSV da análise em exibição (os valores do motor, em precisão integral) e
        # Imprimir / PDF; "Continuar nesta sessão" não muda nada.
        navigation.get_by_test_id("nav-new-session").click()
        dialogo = page.get_by_test_id("new-session-confirmation")
        expect(dialogo).to_be_visible()
        expect(dialogo.get_by_test_id("session-current-analysis")).to_be_visible()
        expect(dialogo.get_by_test_id("session-print")).to_be_enabled()
        page.keyboard.press("Shift+Tab")
        assert dialogo.evaluate("el => el.contains(document.activeElement)"), "o foco fica no diálogo"
        with page.expect_download() as baixado:
            dialogo.get_by_test_id("session-export-csv").click()
        linhas = list(csv.DictReader(io.StringIO(Path(baixado.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))
        assert [linha["id"] for linha in linhas] == [item["id"] for item in e1["itens"]], linhas[:3]
        for linha, item in zip(linhas, e1["itens"]):
            if isinstance(item.get("densidade"), (int, float)) and not isinstance(item.get("densidade"), bool):
                assert float(linha["densidade"]) == item["densidade"], (linha, item)
        dialogo.get_by_test_id("cancel-new-session").click()
        expect(dialogo).to_have_count(0)
        assert len(painel) == chamadas

        # A caixa da conversa: o mouse e o teclado a movem (setas com o cabeçalho focado), a posição fica guardada, ela se
        # minimiza e volta; Home a devolve ao canto.
        handle = chat.get_by_test_id("painel-chat-handle")
        antes, cabeca = chat.bounding_box(), handle.bounding_box()
        page.mouse.move(cabeca["x"] + cabeca["width"] * 0.35, cabeca["y"] + cabeca["height"] / 2)
        page.mouse.down()
        page.mouse.move(cabeca["x"] + cabeca["width"] * 0.35 - 220, cabeca["y"] + cabeca["height"] / 2 - 160, steps=8)
        page.mouse.up()
        depois = chat.bounding_box()
        assert abs((antes["x"] - depois["x"]) - 220) <= 4 and abs((antes["y"] - depois["y"]) - 160) <= 4, (antes, depois)
        handle.focus()
        handle.press("ArrowLeft")
        handle.press("ArrowUp")
        movida = chat.bounding_box()
        assert abs((depois["x"] - movida["x"]) - 16) <= 1 and abs((depois["y"] - movida["y"]) - 16) <= 1, (depois, movida)
        page.wait_for_timeout(400)
        guardada = json.loads(page.evaluate("localStorage.getItem('adt:painel-chat:v1')"))
        assert abs(guardada["x"] - movida["x"]) <= 1 and abs(guardada["y"] - movida["y"]) <= 1, (guardada, movida)
        chat.get_by_test_id("painel-chat-minimizar").click()
        expect(chat).to_have_attribute("data-minimizada", "true")
        expect(chat.locator("#assistant-input")).to_be_hidden()
        chat.get_by_test_id("painel-chat-minimizar").click()
        expect(chat.locator("#assistant-input")).to_be_visible()
        handle.focus()
        handle.press("Home")
        page.wait_for_timeout(300)
        assert chat.bounding_box()["x"] > movida["x"], "Home devolve a caixa ao canto inferior direito"

        # 5. Planilha de outro país (distritos e províncias, sem código IBGE). A troca só vale quando ela fica pronta; o painel
        # "Colunas" sugere sem escolher em silêncio, pede o que falta, os nomes e o referencial (SIRGAS 2000 ou WGS 84).
        escolher_arquivo(planilha_de_distritos(pasta))
        colunas = fonte.get_by_test_id("colunas-painel")
        expect(colunas).to_be_visible(timeout=60000)
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil")
        unidade = colunas.get_by_test_id("colunas-territory")
        expect(unidade).to_have_value("")
        expect(unidade.locator("option").nth(1)).to_have_text("distrito (sugerida)")
        expect(unidade.locator("option").nth(2)).to_have_text("provincia (sugerida)")
        expect(colunas.get_by_test_id("colunas-territory_id")).to_have_value("")
        for papel, coluna in (("period", "ano"), ("category", "categoria"), ("count", "quantidade"), ("population", "populacao"),
                              ("latitude", "latitude"), ("longitude", "longitude")):
            expect(colunas.get_by_test_id("colunas-" + papel)).to_have_value(coluna)
        chamadas = len(painel)
        colunas.get_by_test_id("colunas-comecar").click()
        pendencias = colunas.get_by_test_id("colunas-pendencias")
        expect(pendencias).to_contain_text("Escolha a coluna da unidade territorial.")
        expect(pendencias).to_contain_text("Diga o que a quantidade conta")
        assert len(painel) == chamadas, "sem as colunas necessárias, nada é pedido ao motor"
        unidade.select_option("distrito")
        grupo = colunas.get_by_test_id("colunas-grupo_territorial")
        expect(grupo.locator("option").nth(1)).to_have_text("provincia (sugerida)", timeout=30000)
        expect(grupo).to_have_value("")
        grupo.select_option("provincia")
        expect(colunas.get_by_test_id("colunas-unidade-singular")).to_have_value("distrito")
        expect(colunas.get_by_test_id("colunas-unidade-plural")).to_have_value("distritos")
        expect(colunas.get_by_test_id("colunas-grupo-singular")).to_have_value("província")
        expect(colunas.get_by_test_id("colunas-grupo-plural")).to_have_value("províncias")
        colunas.get_by_test_id("colunas-unidade-de-contagem").select_option("pessoas")
        expect(pendencias).to_have_count(0)
        disponibilidade = colunas.get_by_test_id("colunas-disponibilidade")
        espacial = disponibilidade.get_by_test_id("colunas-disponibilidade-espacial")
        referencial = colunas.get_by_test_id("colunas-referencial")
        assert referencial.locator("option").all_text_contents() == [
            "Escolher", "SIRGAS 2000", "WGS 84", "Outro referencial", "Não sei"], referencial.locator("option").all_text_contents()
        expect(colunas.get_by_test_id("colunas-referencial-ajuda")).to_contain_text(
            "Informe o referencial em que as coordenadas foram coletadas: SIRGAS 2000 ou WGS 84. O sistema não converte um no outro.")
        referencial.select_option("outro")
        expect(espacial).to_have_attribute("data-disponivel", "false", timeout=30000)
        expect(espacial).to_contain_text("Só os referenciais SIRGAS 2000 e WGS 84 são admitidos")
        referencial.select_option("WGS84")
        expect(espacial).to_have_attribute("data-disponivel", "true", timeout=30000)
        referencial.select_option("SIRGAS2000")
        expect(espacial).to_have_attribute("data-disponivel", "true", timeout=30000)
        expect(disponibilidade.get_by_test_id("colunas-disponibilidade-distribuicao")).to_have_attribute("data-disponivel", "true")
        rotatividade = disponibilidade.get_by_test_id("colunas-disponibilidade-rotatividade")
        expect(rotatividade).to_have_attribute("data-disponivel", "false")
        expect(rotatividade).to_contain_text("Falta a coluna do identificador individual.")
        shot("04-colunas")
        _, sent, pedido = painel_response(lambda: colunas.get_by_test_id("colunas-comecar").click())
        assert uploaded_filename(pedido) == "distritos.csv", uploaded_filename(pedido)
        assert not form_field(pedido, "dataset"), "planilha enviada: vai o arquivo, não a base do Brasil"
        assert json.loads(form_field(pedido, "mapping")) == MAPEAMENTO_DOS_DISTRITOS, form_field(pedido, "mapping")
        # A coluna escolhida pela pessoa no seletor vai como papel estabelecido (confirmed_roles, D1), como no pré-exame.
        assert sent.get("premissas") == {"confirmed_roles": ["territory"], "count_unit": "pessoas", "crs": "SIRGAS2000"}, sent
        expect(colunas).to_have_count(0)
        expect(page.get_by_test_id("current-source")).to_contain_text("distritos.csv · distritos e províncias")
        expect(fonte.get_by_test_id("colunas-abrir")).to_be_visible()
        expect(fonte).not_to_contain_text(SEM_MUNICIPIO)
        guia = chat.get_by_test_id("painel-chat-guia")
        expect(guia).to_contain_text("distritos")
        expect(guia).not_to_contain_text(SEM_MUNICIPIO)
        # As análises da base do Brasil continuam no Histórico, mas só reabrem com aquela fonte.
        expect(historico).to_contain_text(history_label(3), timeout=30000)
        historico.click()
        expect(menu.get_by_test_id("historico-outra-fonte")).to_have_count(2)
        expect(itens.first).to_have_attribute("aria-current", "true")
        for indice in (1, 2):
            expect(itens.nth(indice)).to_be_disabled()
        page.keyboard.press("Escape")
        shot("05-planilha")

        # 6. Planilha com duas abas: a escolha da aba vem antes das colunas; "Cancelar" mantém a planilha em uso.
        escolher_arquivo(planilha_de_duas_abas(pasta))
        aba = fonte.get_by_test_id("fonte-aba")
        expect(aba).to_be_visible(timeout=60000)
        assert aba.locator("option").all_text_contents() == ["Selecione uma aba", "Notas", "Dados"]
        with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=60000) as inspecao:
            aba.select_option("Dados")
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        expect(fonte.get_by_test_id("colunas-painel")).to_be_visible()
        expect(fonte.get_by_test_id("colunas-territory")).to_have_value("distrito")  # reconhecida por regra, única candidata
        chamadas = len(painel)
        fonte.get_by_test_id("fonte-cancelar-preparo").click()
        expect(fonte.get_by_test_id("colunas-painel")).to_have_count(0)
        expect(page.get_by_test_id("current-source")).to_contain_text("distritos.csv")
        assert len(painel) == chamadas

        # 7. Formato recusado: a mensagem diz o que aceitar, e a planilha em uso continua.
        texto = pasta / "dados.txt"
        texto.write_text("a;b\n1;2\n", encoding="utf-8")
        escolher_arquivo(texto)
        expect(fonte.get_by_test_id("fonte-erro")).to_have_text("Formato não reconhecido. Selecione um arquivo CSV, XLS ou XLSX.")
        expect(page.get_by_test_id("current-source")).to_contain_text("distritos.csv")
        fonte.get_by_test_id("fonte-cancelar-preparo").click()
        expect(fonte.get_by_test_id("fonte-erro")).to_have_count(0)

        # 8. Celular (390 px): sem rolagem horizontal; cabeçalho, navegação e fonte à vista; a conversa ancorada embaixo.
        page.set_viewport_size({"width": 390, "height": 844})
        expect(chat).to_have_attribute("data-ancorada", "true")
        page.wait_for_timeout(500)
        no_horizontal_scroll(page, "390 px")
        for alvo in ("pagina-marca", "nav-new-session", "nav-new-analysis", "nav-history", "current-source", "fonte-trocar"):
            expect(page.get_by_test_id(alvo)).to_be_visible()
        caixa = chat.bounding_box()
        assert caixa["x"] <= 12 and caixa["x"] + caixa["width"] >= 390 - 12 and caixa["y"] + caixa["height"] >= 844 - 12, caixa
        shot("06-celular")
        page.set_viewport_size({"width": 1280, "height": 900})

        # 9. Fim da sessão. A falha ao encerrar mantém a sessão e o conteúdo; o encerramento revoga a sessão no servidor, e o
        # aceite volta, com o aviso do descarte; o Histórico e a fonte recomeçam vazios.
        token = next((pedido.headers.get("x-adt-session") for pedido in painel if pedido.headers.get("x-adt-session")), None)
        assert token, "o gráfico leva a sessão temporária"
        navigation.get_by_test_id("nav-new-session").click()
        dialogo = page.get_by_test_id("new-session-confirmation")
        page.route("**/api/session/close", lambda route: route.fulfill(status=503, body="indisponível"), times=1)
        dialogo.get_by_test_id("confirm-new-session").click()
        expect(dialogo.get_by_role("alert")).to_contain_text("Não foi possível encerrar")
        expect(page.get_by_test_id("current-source")).to_contain_text("distritos.csv")
        with page.expect_response(lambda r: r.url.endswith("/api/session/close"), timeout=60000) as fechada:
            dialogo.get_by_test_id("confirm-new-session").click()
        assert fechada.value.status == 200, fechada.value.text()[:500]
        expect(page.get_by_role("dialog", name=PRIVACIDADE)).to_be_visible(timeout=60000)
        expect(page.get_by_test_id("session-ended-notice")).to_contain_text("A sessão anterior foi encerrada")
        assert context.request.get(URL.rstrip("/") + "/api/session", headers={"X-ADT-Session": token}).status == 410
        accept_privacy(page)
        expect(historico).to_contain_text(history_label(0))
        expect(page.get_by_test_id("current-source")).to_have_count(0)
        expect(page.get_by_test_id("latest-reply")).to_have_count(0)

        assert not llm_calls, llm_calls
        assert not analyze_calls, "a página única não usa as telas clássicas de /api/analyze"
        assert not failures, failures
        browser.close()
    print("PÁGINA ÚNICA PASS: abertura, estados, Histórico e Nova análise sem recálculo, CSV da sessão, planilha de distritos "
          "e províncias pelo painel Colunas, abas, formato recusado, celular e fim da sessão" +
          (" (base versionada)." if real else " (catálogo sintético)."))


if __name__ == "__main__":
    main()
