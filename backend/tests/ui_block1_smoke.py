"""Jornada Bloco 1 com catálogo Brasil real ou fixture explicitamente configurada.

Servidor serve_ui_offline.py; nunca chama Gemini. ADT_BLOCK1_REAL=1 valida
62 municípios amazonenses e 22 competências. Nenhum registro é salvo no teste;
capturas de tela ficam em .local/ui-validation/, ignorada pelo Git.
"""
import csv
import io
import json
import os
import re
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from ui_support import workspace, execute_analysis, select, URL, offline, municipality

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"


def exported_rows(download):
    return list(csv.DictReader(io.StringIO(Path(download.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))


def assert_same_rows(exported, rows):
    """CSV baixado no navegador × linhas devolvidas pelo motor, em precisão integral."""
    assert len(exported) == len(rows)
    for line, row in zip(exported, rows):
        assert list(line) == list(row)
        for key, value in row.items():
            if value is None:
                assert line[key] == "", (key, line[key])
            elif isinstance(value, (int, float)):
                assert float(line[key]) == value, (key, line[key], value)
            else:
                assert line[key] == str(value), (key, line[key], value)


def check_trend(board, result):
    """Selos da tabela com o código da classe de cada linha (rótulo → código pela metadata) e contagens do motor."""
    tendencia = result["metadata"]["tendencia"]
    code = {item["rotulo"]: item["codigo"] for item in tendencia["classes"]}
    code.update({label: "NAO_AVALIAVEL" for label in tendencia["rotulos_nao_avaliavel"].values()})
    badges = board.locator("#tabela-resultado").get_by_test_id("trend-badge")
    expect(badges).to_have_count(len(result["rows"]))
    assert badges.evaluate_all("items => items.map(item => item.dataset.class)") == [code[row["Tendência"]] for row in result["rows"]]
    assert badges.all_inner_texts() == [row["Tendência"] for row in result["rows"]]
    # Motivo da tendência: com a classe atribuída o motor não dá motivo (vazio no CSV); a tabela diz "Não se aplica", e não
    # "Não avaliável", que contradiria o selo da mesma linha.
    table = board.locator("#tabela-resultado table")
    headers = [text.strip() for text in table.locator("thead tr").first.locator("th").all_inner_texts()]
    column = headers.index("Motivo da tendência")
    motives = table.locator("tbody tr").evaluate_all(f"rows => rows.map(row => row.cells[{column}].innerText.trim())")
    assert motives == [row["Motivo da tendência"] or "Não se aplica" for row in result["rows"]], motives
    board.get_by_role("tab", name="Gráficos", exact=True).click()
    counts = board.get_by_test_id("trend-counts")
    expect(counts).to_be_visible()
    shown = dict(counts.get_by_test_id("trend-count").evaluate_all(
        "items => items.map(item => [item.dataset.key, Number(item.dataset.value)])"))
    assert shown == {**{key: value for key, value in tendencia["contagens"].items() if key != "SEM_CLASSIFICACAO"},
                     **{"SEM_CLASSIFICACAO:" + key: value for key, value in tendencia["sem_classificacao_por_motivo"].items()},
                     **{"NAO_AVALIAVEL:" + key: value for key, value in tendencia["nao_avaliaveis_por_motivo"].items()}}, shown


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, results, llm_calls, analyses = [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: analyses.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        chat = page.locator("#assistente")

        def send(message):
            print("Pedido: " + message, flush=True)
            chat.locator("#assistant-input").fill(message)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
            expect(chat.locator("#assistant-input")).to_be_enabled(timeout=60000)

        def calculate():
            button = page.locator("#preparacao-conversacional").get_by_role("button", name="Calcular e mostrar resultado", exact=True)
            expect(button).to_be_enabled(timeout=60000)
            with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=60000) as event:
                execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()
            result = event.value.json()
            results.append(result)
            print("Resultado: " + result["title"] + " / " + str(result["total_rows"]) + " linhas", flush=True)
            # Identificador estável: o nome do tipo de análise pode repetir o título (ex.: "Evolução temporal").
            expect(page.locator("#resultados").get_by_test_id("result-title")).to_have_text(result["title"])
            return result

        def shot(name):
            """Captura após a animação de 1,5 s do Recharts, para registrar o estado final."""
            page.wait_for_timeout(1600)
            page.screenshot(path=str(OUTPUT / name), full_page=True)

        def reveal(summary):
            """Os detalhes permanecem montados entre resultados; só abre se estiver fechado."""
            details = page.locator("#resultados details", has=page.locator("summary", has_text=summary))
            if not details.evaluate("element => element.open"):
                details.locator("summary").click()

        send("Olá")
        chat.get_by_role("button", name="Usar dados do Brasil").click()
        expect(chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=60000)
        send("Mostre a densidade médica dos municípios do Amazonas em junho de 2024.")
        workspace(page, "territories")
        expect(page.get_by_role("region", name="Seleção territorial compartilhada").get_by_text("62 selecionados" if real else "3 selecionados", exact=True)).to_be_visible(timeout=60000)
        workspace(page, "preparation")
        initial = calculate()
        assert initial["metadata"]["operation"] == "density"
        assert initial["total_rows"] == (62 if real else 3)
        assert {row["Período"] for row in initial["rows"]} == {"202406"}
        assert all(row["Densidade por 1.000"] == row["Quantidade"] / row["População"] * 1000 for row in initial["rows"])
        assert initial["metadata"]["universe"]["kind"] == "selection"
        assert {item["state"] for item in initial["metadata"]["universe"]["members"]} == {"AM"}
        # O resultado é apresentado dentro da conversa, com a tabela do motor.
        expect(chat.locator("#resultados .data-table tbody tr")).to_have_count(62 if real else 3)
        if real:
            geometry = initial["metadata"]["representacao"]["geometria"]
            assert geometry["estado"] == "DISPONIVEL" and len(geometry["ids"]) == 62
            assert geometry["configuracao_apresentacao"]["origem"] == "configuracao_contextual_base_brasil"
            board = chat.locator("#resultados")
            expect(board.get_by_test_id("territory-map")).to_be_visible()
            expect(board.get_by_label("Referencial geodésico para o mapa")).to_have_count(0)
            board.get_by_role("tab", name="Gráficos", exact=True).click()
            expect(board.get_by_test_id("scrollable-bars")).to_have_attribute("data-total", "62")
        shot("block1-01-densidade-amazonas.png")
        density = {row["Território"]: row["Densidade por 1.000"] for row in initial["rows"]}
        workspace(page, "territories")
        selection = page.get_by_role("region", name="Seleção territorial compartilhada")
        selection.get_by_role("button", name="Limpar seleção", exact=True).click()
        # Lista vertical da base oficial: os municípios ficam no grupo do estado (aberto pelo botão do grupo).
        for name, code in [("MANAUS", "130260"), ("TEFE", "130420"), ("PARINTINS", "130340")]:
            municipality(selection, code).check()
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        send("Compare os selecionados.")
        inline = page.locator("#preparacao-conversacional")
        expect(inline.get_by_label("As medidas, unidades e populações são comparáveis entre os territórios.")).to_have_count(0)
        compared = calculate()
        assert compared["total_rows"] == 3
        expect(page.get_by_test_id("comparison-territory-row")).to_have_count(3)
        # Cada território da comparação deve ocupar um registro visual próprio. A base oficial envia a abrangência
        # territorial: os municípios marcados seguem a rota municipal, na ordem do código (o contrato normaliza a ordem).
        assert compared["metadata"]["options"]["territory_ids"] == ["code:130260", "code:130340", "code:130420"]
        assert compared["metadata"]["options"]["abrangencia"]["municipios"]["ids"] == ["code:130260", "code:130340", "code:130420"]
        assert compared["metadata"]["selecao_territorial"]["rota"] == "municipal"
        # Mesmos valores da densidade inicial: a seleção não altera o cálculo de cada membro.
        assert {row["Período"] for row in compared["rows"]} == {"202406"}
        assert all(row["Densidade por 1.000"] == density[row["Território"]] for row in compared["rows"])
        shot("block1-02-comparacao.png")
        send("Mostre a evolução dos municípios selecionados.")
        # Base oficial: comparabilidade temporal e identidade territorial são premissas internas, sem caixas.
        expect(inline.get_by_label("Confirmo que os quantitativos e os períodos são comparáveis.")).to_have_count(0)
        expect(inline.get_by_label("Os territórios correspondem às mesmas unidades ao longo do tempo.")).to_have_count(0)
        temporal = calculate()
        assert temporal["metadata"]["options"]["governed_premises"][:2] == ["temporal_comparability_confirmed", "territory_longitudinal_confirmed"]
        assert not any("pelo usuário para esta execução" in note for note in temporal["notes"])
        assert temporal["total_rows"] == 3
        assert len(temporal["detail_rows"]) == (66 if real else 12)
        # Cada competência permanece separada; extremos e variação vêm da própria série.
        detail = temporal["detail_rows"]
        assert len({(row["Território"], row["Período"]) for row in detail}) == len(detail)
        value = "Densidade por 1.000" if temporal["metadata"]["indicator"] == "density" else "Quantidade"
        for row in temporal["rows"]:
            series = sorted((item["Período"], item[value]) for item in detail if item["Território"] == row["Território"])
            assert (row["Período inicial"], row["Inicial"]) == series[0] and (row["Período final"], row["Final"]) == series[-1]
            assert row["Variação absoluta"] == row["Final"] - row["Inicial"]
            if value == "Densidade por 1.000":
                assert dict(series)["202406"] == density[row["Território"]]
        shot("block1-03-evolucao.png")
        board = page.locator("#resultados")
        expect(board.locator("#tabela-resultado .data-table tbody tr")).to_have_count(3)
        # Até três registros: cartões de destaque com os valores do motor; competências legíveis na tabela.
        highlights = board.get_by_test_id("result-highlights")
        expect(highlights.locator("article")).to_have_count(3)
        for row in temporal["rows"]:
            expect(highlights).to_contain_text(row["Território"])
        start = temporal["rows"][0]["Período inicial"]
        expect(board.locator("#tabela-resultado .data-table tbody tr").first).to_contain_text(start[4:] + "/" + start[:4])
        expect(board.get_by_text("Solicitação: Mostre a evolução dos municípios selecionados.", exact=True)).to_be_visible()
        # Tendência do motor (CAP-TEN-01): selos com o código da classe de cada linha e contagens iguais às do motor.
        tendencia = temporal["metadata"]["tendencia"]
        check_trend(board, temporal)
        expect(highlights.get_by_test_id("trend-badge")).to_have_count(3)
        expect(highlights.get_by_test_id("trend-velocities")).to_have_count(3)
        assert highlights.get_by_test_id("trend-velocities").evaluate_all("items => items.map(item => item.dataset.count)") == [
            str(len(unit["velocidades"])) for unit in tendencia["unidades"]]
        # Série completa (janeiro e junho alternados): na base real, os três municípios do AM saem sem classificação (RES-SCL)
        # e o resultado oferece a série anual de junho; no catálogo sintético (só duas competências de junho), não.
        assert tendencia["desfecho"] == ("RES-SCL" if real else "RES-VAL")
        stage = board.get_by_test_id("trend-stage-note")
        if real:
            expect(stage).to_have_attribute("data-outcome", "RES-SCL")
        else:
            expect(stage).to_have_count(0)
        expect(board.get_by_test_id("trend-annual-june")).to_have_count(1 if real else 0)
        expect(board.get_by_test_id("trend-family-filter")).to_be_visible()
        with page.expect_download() as download:
            board.get_by_text("Opções técnicas avançadas", exact=True).click()
            board.get_by_role("button", name="Baixar registro técnico (JSON)", exact=True).click()
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert exported["result_id"] == temporal["result_id"] and exported["currency"] == "VIGENTE"
        assert exported["execution_key"] == temporal["metadata"]["execution_key"]
        # O CSV do resultado atual coincide com a resposta original do motor.
        with page.expect_download() as download:
            board.get_by_role("button", name="CSV", exact=True).click()
        assert_same_rows(exported_rows(download), temporal["rows"])
        shot("block1-04-resultado.png")
        # A tabela substitui o checklist duplicado: a seleção só chega à preparação por ação explícita.
        table_rows = board.locator("#tabela-resultado tbody tr")
        table_rows.nth(0).click()
        table_rows.nth(1).click()
        board.get_by_role("button", name="Usar seleção na próxima análise", exact=True).click()
        expect(selection.get_by_text("2 selecionados", exact=True)).to_be_visible()
        workspace(page, "results")
        table_rows.nth(2).click()
        board.get_by_role("button", name="Usar seleção na próxima análise", exact=True).click()
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        expect(table_rows).to_have_count(3)

        send("Agregue os municípios selecionados.")
        inline.get_by_label("Escolher períodos da análise").click()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        # Populações disjuntas e soma dos componentes são premissas internas da base oficial, sem caixas.
        for label in ("As populações são partes sem sobreposição do conjunto agregado.",
                      "As contagens representam unidades sem sobreposição entre territórios.",
                      "Caso contrário, autorizo somar componentes, mesmo com possível dupla contagem."):
            expect(inline.get_by_label(label)).to_have_count(0)
        aggregate = calculate()
        assert any("possível dupla contagem" in note for note in aggregate["notes"])
        selected_rows = [row for row in initial["rows"] if any(code in row["Território"] for code in ("130260", "130420", "130340"))]
        assert aggregate["rows"][0]["Quantidade"] == sum(row["Quantidade"] for row in selected_rows)
        assert aggregate["rows"][0]["População"] == sum(row["População"] for row in selected_rows)
        assert aggregate["rows"][0]["Densidade por 1.000"] == aggregate["rows"][0]["Quantidade"] / aggregate["rows"][0]["População"] * 1000
        assert "possível dupla contagem" in aggregate["rows"][0]["Tipo"] and "Unidades distintas" not in aggregate["rows"][0]["Tipo"]
        assert aggregate["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"
        with page.expect_download() as download:
            board.get_by_role("button", name="CSV", exact=True).click()
        assert_same_rows(exported_rows(download), aggregate["rows"])
        shot("block1-05-agregacao.png")
        # Repetição exata recupera o resultado sem nova requisição/cálculo.
        workspace(page, "preparation")
        execute_analysis(page, inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True))
        expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible()
        assert len(analyses) == 4

        # "Análises anteriores": acessível ao usuário, sem recalcular nem restaurar
        # parâmetros de forma implícita. Também mantém o resultado atual na lista.
        previous = page.get_by_role("region", name="Histórico de análises")
        expect(previous.get_by_test_id("analysis-history-menu")).to_be_visible()
        expect(previous).to_be_visible()
        expect(previous.get_by_text("4 análises nesta sessão", exact=True)).to_be_visible()
        previous.locator("summary").click()
        expect(previous.get_by_role("button", name="Abrir análise: Agregação territorial")).to_be_disabled()
        calls = len(analyses)
        previous.get_by_role("button", name="Abrir análise: Densidade de profissionais").click()
        expect(board.get_by_test_id("result-title")).to_have_text(initial["title"])
        expect(board.locator("#tabela-resultado .data-table tbody tr")).to_have_count(62 if real else 3)
        assert len(analyses) == calls, "reabrir análise anterior não pode gerar nova chamada"
        previous.locator("summary").click()
        expect(previous.get_by_role("button", name="Abrir análise: Densidade de profissionais")).to_be_disabled()
        previous.get_by_role("button", name="Abrir análise: Agregação territorial").click()
        expect(board.get_by_test_id("result-title")).to_have_text(aggregate["title"])
        expect(board.locator("#tabela-resultado .data-table tbody tr")).to_have_count(1)
        assert len(analyses) == calls
        # O menu deve recolher ao clicar fora; a confirmação de nova análise
        # deve permitir cancelamento sem descartar o resultado nem o histórico.
        previous.locator("summary").click()
        expect(previous.get_by_test_id("analysis-history-menu")).to_have_attribute("open", "")
        board.get_by_test_id("result-title").click()
        expect(previous.get_by_test_id("analysis-history-menu")).not_to_have_attribute("open", "")
        page.get_by_role("navigation", name="Navegação principal").get_by_test_id("nav-new-analysis").click()
        confirmation = page.get_by_test_id("new-analysis-confirmation")
        expect(confirmation).to_be_visible()
        expect(confirmation).to_contain_text("Histórico desta sessão")
        page.get_by_test_id("cancel-new-analysis").click()
        expect(confirmation).not_to_be_visible()
        expect(board.get_by_test_id("result-title")).to_have_text(aggregate["title"])
        assert len(analyses) == calls, "cancelar nova análise não deve executar cálculo"
        shot("block1-06-analises-anteriores.png")

        # Retomada dos parâmetros do resultado atual; o cálculo idêntico é reaproveitado.
        board.get_by_role("button", name="Retomar parâmetros deste resultado", exact=True).click()
        expect(page.get_by_text("Parâmetros e seleção restaurados", exact=False)).to_be_visible()
        workspace(page, "territories")
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        workspace(page, "preparation")
        calls = len(analyses)
        button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
        expect(button).to_be_enabled(timeout=60000)
        execute_analysis(page, button)
        expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible()
        expect(board.get_by_test_id("result-status")).to_contain_text("válido e vigente")
        expect(board.get_by_test_id("result-title")).to_have_text(aggregate["title"])
        assert len(analyses) == calls, "a retomada exata não deve recalcular"
        shot("block1-06-retomada.png")

        # Teclado/toque e dimensões móveis preservam a navegação e as ações.
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            expect(page.get_by_test_id("main-navigation")).to_be_visible()
            # Quatro botões e o Histórico: o gráfico de bolhas é a página principal ("Início"), sem botão próprio (22/10/2026).
            expect(page.get_by_test_id("main-navigation").locator(':scope > button')).to_have_count(4)
            expect(page.get_by_test_id("nav-painel")).to_have_count(0)
            expect(page.get_by_test_id("analysis-history-menu").locator('summary')).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            shot(f"block1-07-largura-{width}.png")
        workspace(page, "territories")
        # Teclado: o seletor nativo "Estado dos municípios" mostra a lista do estado, e a Espaço marca e desmarca a caixa
        # nativa do município.
        state = selection.get_by_test_id("territory-municipal-state")
        state.focus()
        expect(state).to_be_focused()
        state.select_option("13")
        checkbox = municipality(selection, "130420")
        checkbox.focus()
        checkbox.press("Space")
        expect(selection.get_by_text("2 selecionados", exact=True)).to_be_visible()
        checkbox.press("Space")
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()

        # Distâncias na base oficial: o referencial (SIRGAS 2000) e o separador decimal são premissas internas.
        # No catálogo sintético (versão externa fixada), o referencial continua sendo pedido ao usuário.
        page.set_viewport_size({"width": 1280, "height": 900})
        workspace(page, "preparation")
        select(page, "Análise espacial")
        reference = inline.get_by_label("Território de referência", exact=True)
        expect(reference).to_be_visible(timeout=60000)
        expect(inline.get_by_label("Referencial geodésico", exact=True)).to_have_count(0 if real else 1)
        # Uma competência por vez (a da agregação continua escolhida): as distâncias usam as coordenadas dela.
        expect(inline.get_by_test_id("period-summary")).to_have_text("junho de 2024")
        inline.get_by_label("Escolher períodos da análise").click()
        expect(inline.get_by_test_id("spatial-period-note")).to_contain_text("coordenadas da competência escolhida")
        inline.get_by_test_id("period-done").click()
        if real:
            expect(inline.get_by_test_id("crs-summary")).to_have_text("SIRGAS 2000 (premissa da base oficial)")
            reference.select_option(label=next(member["label"] for member in initial["metadata"]["universe"]["members"]
                                               if member["id"] == "code:130260"))
            spatial = calculate()
            assert spatial["metadata"]["periods"] == ["202406"]
            assert spatial["metadata"]["operation"] == "spatial" and spatial["total_rows"] == 3
            assert spatial["metadata"]["options"]["governed_premises"][-2:] == ["crs", "number_format"]
            assert any(note.startswith("Referencial geodésico: SIRGAS 2000, premissa governada") for note in spatial["notes"])
            board.get_by_role("tab", name="Mapa", exact=True).click()
            expect(board.get_by_text("Referencial SIRGAS 2000: premissa da base oficial", exact=False)).to_be_visible()
            shot("block1-08-distancias-base-oficial.png")

        def no_advanced_conditions():
            """Base oficial: a preparação não tem condições avançadas nem pede nada sobre a estrutura da base."""
            expect(inline.get_by_text("Preparando a análise...", exact=True)).to_have_count(0, timeout=60000)
            expect(inline.locator("summary", has_text="Ver outras condições da análise")).to_have_count(0)
            expect(page.get_by_role("region", name="Preparação da análise")).to_have_count(0)
            expect(inline.get_by_text("Ainda faltam condições específicas", exact=False)).to_have_count(0)
            expect(page.get_by_role("heading", name="Conferir a estrutura dos dados", exact=True)).to_have_count(0)

        # Sem condições avançadas na base oficial: premissas internas não voltam como caixas, seletores nem painel.
        workspace(page, "preparation")
        no_advanced_conditions()
        expect(page.get_by_test_id("governed-number-format")).to_have_count(0)
        expect(page.get_by_text("Referencial geodésico informado para a base")).to_have_count(0)
        select(page, "Agregações")
        no_advanced_conditions()
        for label in ("Declaro que as populações territoriais são partes sem sobreposição do conjunto agregado.",
                      "Autorizo a soma das contagens dos componentes, ciente de que pode contar a mesma unidade mais de uma vez; "
                      "o total não será apresentado como pessoas únicas."):
            expect(page.get_by_label(label, exact=True)).to_have_count(0)

        # Atalho "Série anual (junho)" na caixa Período da evolução temporal: só escolhe as competências de junho.
        workspace(page, "preparation")
        select(page, "Evolução temporal")
        inline.get_by_label("Escolher períodos da análise").click()
        shortcut = inline.get_by_test_id("period-annual-june")
        expect(shortcut).to_have_attribute("aria-pressed", "false")
        shortcut.click()
        expect(shortcut).to_have_attribute("aria-pressed", "true")
        expect(inline.get_by_test_id("period-range-summary")).to_contain_text("série anual de junho")
        annual = calculate()
        june = sorted(period for period in tendencia["janela"]["periodos"] if period.endswith("06"))
        assert sorted(annual["metadata"]["options"]["period_filters"]) == june
        assert annual["total_rows"] == 3 and len(annual["detail_rows"]) == (33 if real else 6)
        check_trend(board, annual)
        if real:
            assert annual["metadata"]["tendencia"]["janela"]["serie_anual"] == "06"
            assert annual["metadata"]["tendencia"]["janela"]["intervalos"] == [12]
        else:
            # Duas competências de junho: a mudança continua, e a tendência fica bloqueada na etapa (BLQ-MET).
            assert annual["metadata"]["tendencia"]["desfecho"] == "BLQ-MET"
            expect(board.get_by_test_id("trend-stage-note")).to_have_attribute("data-outcome", "BLQ-MET")
            badges = board.locator("#tabela-resultado").get_by_test_id("trend-badge")
            assert badges.evaluate_all("items => items.map(item => item.dataset.class)") == ["NAO_AVALIAVEL"] * 3
        shot("block1-09-serie-anual-junho.png")
        assert not llm_calls, llm_calls
        assert not failures, failures
        print("Bloco 1: 12 etapas executadas; " + str(len(results)) + " resultados reais do motor; retomada sem recálculo; "
              "CSV/JSON conferidos contra o motor; origem do referencial das distâncias conferida; tendência e série anual conferidas; "
              "apresentação, reutilização e responsividade aprovadas; catálogo=" + ("Brasil real" if real else "sintético controlado"))
        browser.close()


if __name__ == "__main__":
    main()
