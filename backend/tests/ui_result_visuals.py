"""Visual completo dos resultados (D7, 19/10/2026): cabeçalho, níveis, comparação, evolução, ranking, distribuição, agregação,
rotatividade e escala do mapa, sempre com os valores do motor.

Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; quatro competências, duas de junho; estados da
fonte estadual de médicos únicos) ou, com
ADT_BLOCK1_REAL=1, a base versionada (somente leitura). Confere, para cada visual, que o que a tela mostra é o que o motor
entregou (frase em partes, KPIs, procedência, relação e diferença do par, variação e classe de cada território, posição do
ranking, classe de cada ponto da distribuição, tipo de contagem da agregação, percentuais da coorte), que nada é calculado
na tela (o total da distribuição é a métrica do motor; não há segundo gráfico de contagens), que a taxa nacional fica só como
contexto (legenda, barras dos municípios e cartão) e que a escala de cor do mapa não cria classes. Larguras de 390 px sem
rolagem horizontal e impressão. Pela conversa, a aba do resultado e o resultado anterior abrem sem recalcular.
Servidor serve_ui_offline.py; nunca chama o provedor de IA.
"""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from ui_support import URL, choose, execute_analysis, expand, municipality, offline, select, workspace

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
AM = [("MANAUS", "130260"), ("TEFE", "130420"), ("PARINTINS", "130340")]
ROTATION_CSV = ("territorio;periodo;categoria;pessoa\n" + "\n".join(
    f"{name};{period};MEDICINA;{person}" for name, period, people in [
        ("ALFA", "202401", range(10)), ("ALFA", "202406", range(4, 12)), ("BETA", "202401", range(20, 25)),
        ("BETA", "202406", range(22, 30)), ("GAMA", "202401", range(40, 43))] for person in people) + "\n").encode()


def options_of(request):
    return json.loads(request.post_data.split('name="options"\r\n\r\n', 1)[1].split("\r\n--", 1)[0])


def resolve(value, path):
    for key in path:
        value = value[key]
    return value


def display(period):
    return period[4:] + "/" + period[:4]


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = "-real" if real else ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        context.add_init_script("window.__ADT_TEST__ = true")
        page = context.new_page()
        failures, llm_calls = [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        analyze_calls = []
        page.on("request", lambda request: analyze_calls.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        page.get_by_role("button", name="Usar dados do Brasil").click()
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=90000)
        inline = page.locator("#preparacao-conversacional")
        board = page.locator("#resultados")
        region = page.get_by_role("region", name="Seleção territorial compartilhada")

        def settled():
            expect(inline.get_by_test_id("scope-loading")).to_have_count(0, timeout=90000)
            for busy in ("Preparando a análise...", "Verificando as condições da análise..."):
                expect(inline.get_by_text(busy, exact=True)).to_have_count(0, timeout=90000)

        def calculate():
            button = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
            expect(button).to_be_enabled(timeout=90000)
            with page.expect_request(lambda r: r.url.endswith("/api/analyze"), timeout=180000) as sent:
                with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=180000) as event:
                    execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()[:2000]
            body = event.value.json()
            expect(board.get_by_test_id("result-title")).to_have_text(body["title"], timeout=60000)
            print("Resultado: " + body["title"] + " / " + str(body["total_rows"]) + " linhas", flush=True)
            return body, options_of(sent.value)

        def choose_period(label="junho de 2024"):
            summary = inline.get_by_test_id("period-summary")
            if summary.inner_text() != label:
                expand(inline.get_by_label("Escolher períodos da análise"))
                if inline.get_by_role("button", name="Escolher apenas um", exact=True).count():
                    inline.get_by_role("button", name="Escolher apenas um", exact=True).click()
                inline.get_by_role("button", name=label, exact=True).click()
            expect(summary).to_have_text(label)

        def open_scope(clear=True):
            workspace(page, "preparation")
            expand(inline.get_by_test_id("territory-toggle"))
            expect(region).to_be_visible()
            if clear and region.get_by_test_id("territory-clear").is_enabled():
                region.get_by_test_id("territory-clear").click()

        def shot(name):
            page.wait_for_timeout(1600)  # animação do Recharts
            page.screenshot(path=str(OUTPUT / ("visuais-" + name + suffix + ".png")), full_page=True)

        def check_header(body):
            """Frase do motor em partes (competência como mês/ano, milhar), KPIs e procedência; sem a grade antiga."""
            resumo = body["metadata"]["representacao"]["resumo"]
            header = board.get_by_test_id("result-header")
            expect(header).to_be_visible()
            summary = header.get_by_test_id("result-summary")
            for part in resumo["partes"]:
                if "caminho" not in part:
                    expect(summary).to_contain_text(part["texto"].strip())
            for period in body["metadata"]["periods"]:
                if any(part.get("caminho", [None])[0] == "metadata" and part["texto"] == period for part in resumo["partes"]):
                    expect(summary).to_contain_text(display(period))
            expect(header.get_by_test_id("result-kpi")).to_have_count(len(resumo["indicadores"]))
            provenance = header.get_by_test_id("result-provenance")
            expect(provenance).to_contain_text("Chave de execução: " + body["metadata"]["execution_key"][:12])
            for item in resumo["procedencia"]:
                expect(provenance).to_contain_text(item["rotulo"])
            expect(board.get_by_test_id("result-metrics")).to_have_count(0)
            assert "acima" not in summary.inner_text() and "abaixo" not in summary.inner_text()
            return resumo

        # 1. Comparação (primeira escolha da sessão): padrão na série anual de junho, com os valores em junho de 2024; níveis lado a lado e halteres.
        select(page, "Comparações")
        settled()
        # Sem período escolhido, a janela padrão é a série anual de junho e os valores ficam em junho de 2024.
        expect(inline.get_by_test_id("period-summary")).to_contain_text("série anual de junho: " + ("11" if real else "2") + " competências",
                                                                       timeout=90000)
        expect(inline.get_by_test_id("comparison-values-period")).to_contain_text("junho de 2024")
        open_scope()
        region.get_by_test_id("territory-option-brasil").check()
        region.get_by_test_id("territory-option-uf-13").check()
        region.get_by_test_id("territory-option-uf-35").check()
        for code in ("130260", "130420"):
            municipality(region, code).check()
        compared, sent = calculate()
        assert sent["comparison_values_period"] == "202406"
        assert sent["period_filters"] == [period for period in sorted(sent["period_filters"]) if period.endswith("06")]
        meta = compared["metadata"]["comparacao"]
        assert meta["competencia_valores"] == "202406" and meta["mudanca_e_tendencia"] is True
        check_header(compared)
        panel = board.get_by_test_id("comparison-panel")
        expect(panel.get_by_test_id("comparison-values-caption")).to_contain_text("06/2024")
        side = panel.get_by_test_id("comparison-side-by-side")
        for level in ("br", "uf", "mun"):
            expect(side.get_by_test_id("comparison-group-" + level)).to_be_visible()
        expect(side.get_by_test_id("comparison-object")).to_have_count(len(compared["detail_rows"]))
        expect(side.get_by_test_id("comparison-group-br")).not_to_contain_text("Relação A/B")
        expect(side.get_by_test_id("comparison-group-uf").get_by_test_id("uf-warning")).to_contain_text(
            "a soma dos estados não é o total do Brasil")
        pairs = [row for row in compared["rows"] if row.get("Objeto A")]
        assert len(pairs) == 2
        relations = side.get_by_test_id("comparison-pair-relation")
        expect(relations).to_have_count(2)
        for chip, row in zip(relations.all(), pairs):
            expect(chip).to_contain_text(row["Objeto A"])
            expect(chip).to_contain_text("Diferença A − B")
        dumbbell = panel.get_by_test_id("comparison-dumbbell")
        rows = dumbbell.get_by_test_id("dumbbell-row")
        expect(rows).to_have_count(len(compared["detail_rows"]))
        trends = {row["Território"]: row["Tendência"] for row in compared["detail_rows"]}
        for territory, label in trends.items():
            badge = dumbbell.locator('[data-testid="dumbbell-row"][data-territory="' + territory + '"]').get_by_test_id("trend-badge")
            expect(badge).to_have_text(label)  # selo igual ao row["Tendência"] do motor
        assert not any("%" in key or "Razão" in key for row in compared["detail_rows"] for key in row)
        cards = board.get_by_test_id("comparison-territory-row")
        expect(cards).to_have_count(sum(2 if row.get("Objeto A") else 1 for row in compared["rows"]))
        expect(board.get_by_test_id("comparison-card-extra").first).to_contain_text("Na competência dos valores")
        representation = compared["metadata"]["representacao"]
        assert representation["tabela"] == "detail_rows"  # indicadores e mapa pelos objetos, numa competência
        if real:  # na base oficial, o par/conjunto tem mapa (antes: "Mapa indisponível"); no sintético falta o referencial
            assert representation["geometria"]["estado"] == "DISPONIVEL" and representation["geometria"]["competencia"] == "202406"
            board.get_by_role("tab", name="Mapa", exact=True).click()
            expect(board.get_by_test_id("territory-map")).to_be_visible(timeout=60000)
        shot("03-comparacao")

        # 2. Densidade com Brasil, um estado e um município: cabeçalho, níveis em blocos e taxa nacional de contexto.
        select(page, "Densidade")
        settled()
        open_scope()
        region.get_by_test_id("territory-option-brasil").check()
        region.get_by_test_id("territory-option-uf-13").check()
        municipality(region, "130260").check()
        choose_period()
        density, _ = calculate()
        resumo = check_header(density)
        expect(board.get_by_test_id("result-summary")).to_contain_text("06/2024")
        expect(board.get_by_test_id("result-summary")).to_contain_text("por 1.000 habitantes")
        assert density["description"].startswith("Densidade de ")
        brazil_kpi = board.locator('[data-testid="result-kpi"][data-nivel="BR"]')
        expect(brazil_kpi).to_have_count(1)
        national = density["metadata"]["referencia_nacional"]
        series = [item for item in national["serie"] if item["categoria"] == density["metadata"]["categories"][0]]
        expect(brazil_kpi.get_by_test_id("kpi-sparkline")).to_have_attribute("data-points", str(len(series)))
        # Métricas por nível (do motor): nada de "Unidades avaliáveis" contando só municípios.
        assert not any(item["label"] == "Unidades avaliáveis" for item in density["metrics"])
        expect(board.get_by_text("Unidades avaliáveis", exact=True)).to_have_count(0)
        highlights = board.get_by_test_id("result-highlights")
        expect(highlights.locator("article")).to_have_count(3)
        expect(highlights.locator('article[data-level="UF"]')).to_contain_text("médicos únicos de cada estado")
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        levels = board.get_by_test_id("levels-panel")
        expect(levels.get_by_test_id("level-panel-br")).to_contain_text("Brasil (total nacional)")
        expect(levels.get_by_test_id("level-panel-uf").get_by_test_id("uf-warning")).to_contain_text(
            "Fonte estadual: médicos únicos de cada estado")
        expect(levels.get_by_test_id("level-panel-uf")).not_to_contain_text("pessoas únicas")
        expect(levels.get_by_test_id("level-panel-uf").get_by_test_id("bars-reference-line")).to_have_count(0)
        expect(levels.get_by_test_id("level-panel-mun").get_by_test_id("bars-reference-line")).to_contain_text("referência de contexto")
        shot("01-densidade-niveis")
        # Situação do resultado com acentos (antes "avaliavel com limitacoes").
        overview = page.get_by_test_id("investigation-overview")
        if overview.count():
            expect(overview).not_to_contain_text("avaliavel com limitacoes")
        assert density["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"
        # Conversa sobre o resultado apresentado: a aba pedida e o resultado anterior abrem sem recalcular e sem o provedor.
        prompt = page.locator("#assistant-input")

        def say(message, reply):
            prompt.fill(message)
            page.get_by_role("button", name="Enviar mensagem").click()
            expect(page.get_by_test_id("latest-reply")).to_contain_text(reply, timeout=30000)

        calculated = len(analyze_calls)
        say("agora a tabela, por favor", "Resultado aberto na aba Tabela")
        expect(board.get_by_role("tab", name="Tabela", exact=True)).to_have_attribute("aria-selected", "true")
        say("mostra isso num gráfico", "Resultado aberto na aba Gráficos")
        expect(board.get_by_role("tab", name="Gráficos", exact=True)).to_have_attribute("aria-selected", "true")
        say("volta pro resultado anterior", "Resultado anterior reaberto, sem recalcular")
        expect(board.get_by_test_id("result-title")).to_have_text(compared["title"])
        assert len(analyze_calls) == calculated, analyze_calls

        # 3. Todos os municípios: escala de cor logarítmica (padrão) e linear, sempre contínuas, com os extremos marcados.
        if not real:  # catálogo sintético: o referencial das coordenadas é escolhido pelo usuário (na base oficial, é premissa)
            select(page, "Análise espacial")
            settled()
            inline.get_by_label("Referencial geodésico", exact=True).select_option("SIRGAS2000")
            select(page, "Densidade")
            settled()
            choose_period()
        open_scope()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Todos os municípios")
        every, _ = calculate()
        check_header(every)
        board.get_by_role("tab", name="Mapa", exact=True).click()
        page.wait_for_function("window.__adtMapModel && window.__adtMapModel.resultId === '" + every["result_id"] + "'")
        model = page.evaluate("window.__adtMapModel")
        values = {row["Território"]: row["Densidade por 1.000"] for row in every["rows"]}
        valid = [value for value in values.values() if value is not None]
        assert model["domain"] == [min(valid), max(valid)] and model["scale"] == "logaritmica"
        by_id = {"code:" + name.rsplit("[", 1)[1].rstrip("]"): value for name, value in values.items()}
        for fill, key in zip(model["fills"], model["ids"]):
            assert (fill is None) == (by_id[key] is None), key  # não avaliável: anel vazado, nunca uma cor da escala
        legend = board.get_by_role("complementary", name="Legenda do mapa")
        expect(legend.get_by_test_id("legend-scale")).to_have_attribute("data-scale", "logaritmica")
        expect(legend.get_by_test_id("legend-extreme")).to_have_count(2)
        expect(legend).to_contain_text("não é classe nem limiar")
        logarithmic = model["fills"]
        legend.get_by_text("Linear", exact=True).click()
        page.wait_for_function("window.__adtMapModel.scale === 'linear'")
        model = page.evaluate("window.__adtMapModel")
        assert model["domain"] == [min(valid), max(valid)]
        assert [fill is None for fill in model["fills"]] == [fill is None for fill in logarithmic]
        expect(legend.get_by_test_id("legend-scale")).to_have_attribute("data-scale", "linear")
        legend.get_by_text("Logarítmica", exact=True).click()
        page.wait_for_function("window.__adtMapModel.scale === 'logaritmica'")
        shot("02-mapa-escala")

        # 4. Evolução temporal: pequenos múltiplos na mesma escala e halteres do primeiro ao último período.
        select(page, "Evolução temporal")
        settled()
        open_scope()
        region.get_by_test_id("territory-group-check-13").check()
        temporal, _ = calculate()
        check_header(temporal)
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        multiples = board.get_by_test_id("trend-small-multiples")
        expect(multiples).to_have_count(1)
        expect(multiples.get_by_test_id("trend-small-multiple")).to_have_count(min(12, temporal["total_rows"]))
        if real:
            nav = board.get_by_role("navigation", name="Páginas dos pequenos múltiplos", exact=True)
            domain = multiples.get_attribute("data-domain")
            nav.get_by_role("button", name="Próximos", exact=True).click()
            expect(nav).to_contain_text("Territórios 13 a 24 de 62")
            assert multiples.get_attribute("data-domain") == domain  # mesma escala em todas as páginas
        dumbbells = board.get_by_test_id("temporal-dumbbells")
        expect(dumbbells).to_have_attribute("data-total", str(temporal["total_rows"]))
        first = temporal["rows"][0]
        row = dumbbells.locator('[data-testid="dumbbell-row"][data-territory="' + first["Território"] + '"]')
        expect(row.get_by_test_id("trend-badge")).to_have_text(first["Tendência"])
        expect(board.get_by_test_id("trend-counts")).to_be_visible()
        shot("04-evolucao")

        # 5. Ranking em pirulito: a posição é a do motor, na ordem do resultado.
        select(page, "Recortes e rankings")
        settled()
        open_scope()
        region.get_by_test_id("territory-group-check-13").check()
        choose_period()
        ranking, _ = calculate()
        check_header(ranking)
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        lollipop = board.get_by_test_id("ranking-lollipop")
        expect(lollipop).to_have_attribute("data-total", str(ranking["total_rows"]))
        shown = lollipop.get_by_test_id("lollipop-row")
        expect(shown.first).to_contain_text("Posição " + str(ranking["rows"][0]["Posição"]))
        expect(shown.first).to_contain_text(ranking["rows"][0]["Território"])
        assert shown.first.get_attribute("data-rank") == str(ranking["rows"][0]["Posição"])
        shot("05-ranking")

        # 6. Distribuição: total do motor (sem soma na tela), um só gráfico de contagens e a faixa por território.
        select(page, "Distribuição")
        settled()
        open_scope()
        inline.get_by_role("combobox", name="Indicador", exact=True).select_option("density")
        choose_period()
        distribution, _ = calculate()
        check_header(distribution)
        total = next(item["value"] for item in distribution["metrics"] if item["label"] == "Unidades classificadas")
        expect(board.get_by_test_id("distribution-total")).to_contain_text(f"{total:,}".replace(",", "."))
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        expect(board.get_by_role("figure", name="Territórios por grupo da distribuição", exact=True)).to_be_visible()
        expect(board.get_by_text("Quantas unidades pertencem a cada quintil?", exact=True)).to_have_count(1)
        column = distribution["rows"][0]["Indicador"]
        strip = board.get_by_test_id("distribution-strip")
        expect(strip).to_have_attribute("data-total", str(sum(row[column] is not None for row in distribution["detail_rows"])))
        shot("06-distribuicao")

        # 7. Agregação: cartão com o tipo de contagem do motor, fora dos destaques.
        select(page, "Agregações")
        settled()
        open_scope()
        for _, code in AM:
            municipality(region, code).check()
        choose_period()
        aggregate, _ = calculate()
        check_header(aggregate)
        card = board.get_by_test_id("aggregate-card")
        expect(card.get_by_test_id("aggregate-type")).to_have_text(aggregate["rows"][0]["Tipo"])
        expect(card).to_contain_text("possível dupla contagem")
        expect(board.get_by_test_id("result-highlights")).to_have_count(0)
        shot("07-agregacao")

        # 8. Quantitativos do Brasil: KPI com a última competência da linha nacional e o minigráfico.
        select(page, "Quantitativos")
        settled()
        open_scope()
        region.get_by_test_id("territory-option-brasil").check()
        expand(inline.get_by_label("Escolher períodos da análise"))
        if inline.get_by_role("button", name="Selecionar vários períodos", exact=True).count():
            inline.get_by_role("button", name="Selecionar vários períodos", exact=True).click()
        inline.get_by_role("button", name="Todos os períodos disponíveis", exact=True).click()
        counts, _ = calculate()
        resumo = check_header(counts)
        kpi = board.get_by_test_id("result-kpi").first
        last = max(row["Período"] for row in counts["rows"])
        expect(kpi).to_contain_text("Brasil (total nacional) em " + display(last))
        expect(kpi.get_by_test_id("kpi-sparkline")).to_have_attribute("data-points", str(counts["total_rows"]))

        # 9. Larguras de celular e impressão: sem rolagem horizontal; cabeçalho e visuais impressos, controles não.
        workspace(page, "results")
        history = page.get_by_test_id("analysis-history-menu")  # a comparação (primeira análise), o painel mais largo
        history.locator("summary").click()
        history.get_by_role("button", name="Abrir análise: " + compared["title"], exact=True).first.click()
        expect(board.get_by_test_id("result-title")).to_have_text(compared["title"])
        expect(board.get_by_test_id("comparison-panel")).to_be_visible()
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), width
            page.screenshot(path=str(OUTPUT / ("visuais-08-largura-" + str(width) + suffix + ".png")), full_page=True)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.emulate_media(media="print")
        expect(board.get_by_test_id("result-header")).to_be_visible()
        expect(board.get_by_role("radiogroup", name="Filtro visual dos territórios")).to_be_hidden()
        page.emulate_media(media="screen")

        # 10. Rotatividade (base importada com identificador): barras da coorte com os percentuais do motor.
        imported = context.new_page()
        imported.on("pageerror", lambda error: failures.append(str(error)))
        imported.goto(URL)
        imported.get_by_role("button", name="Li e concordo", exact=True).click()
        imported.get_by_label("Importar arquivo de dados").set_input_files({"name": "coorte.csv", "mimeType": "text/csv",
                                                                             "buffer": ROTATION_CSV})
        expect(imported.get_by_test_id("current-source")).to_contain_text("coorte.csv", timeout=60000)
        select(imported, "Rotatividade")
        preparation = imported.locator("#preparacao-conversacional")
        choose(preparation, "Identificador individual", "pessoa")
        execute = preparation.get_by_role("button", name="Executar análise", exact=True)
        expect(execute).to_be_enabled(timeout=60000)
        with imported.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=60000) as event:
            execute_analysis(imported, execute)
        assert event.value.status == 200, event.value.text()[:2000]
        rotation = event.value.json()
        bars = imported.locator("#resultados").get_by_test_id("rotation-cohort-bars")
        expect(bars.get_by_test_id("cohort-bar")).to_have_count(len(rotation["rows"]))
        for row in rotation["rows"]:
            bar = bars.locator('[data-testid="cohort-bar"][data-territory="' + row["Território"] + '"]')
            if row["Permanência (%)"] is None:
                expect(bar).to_contain_text("Não avaliável")
            else:
                expect(bar).to_contain_text(f"{row['Permanência (%)']:.2f}".replace(".", ",") + "%")
        imported.screenshot(path=str(OUTPUT / ("visuais-09-rotatividade" + suffix + ".png")), full_page=True)
        imported.close()

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    print("VISUAIS DOS RESULTADOS PASS: cabeçalho, níveis, comparação, evolução, ranking, distribuição, agregação, rotatividade e "
          "escala do mapa" + (" (base versionada)." if real else "."))


if __name__ == "__main__":
    main()
