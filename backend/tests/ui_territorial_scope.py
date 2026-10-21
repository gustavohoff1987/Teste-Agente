"""Abrangência territorial da base oficial em lista vertical (D3) e taxa nacional de contexto (D5) na tela.

Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; populações 1.000, 2.000, 4.000 e 9.000; contagem
nacional 100, 102, 103 e 105; fonte estadual com AM 18, 22, 24 e 30 e SP 100, 102, 103 e 105) ou, com ADT_BLOCK1_REAL=1, a
base versionada (somente leitura). Confere:
- a lista com Brasil, estados (médicos únicos da fonte estadual; a soma dos estados não é o total do Brasil) e
  municípios agrupados por estado;
- a análise espacial com a escolha de uma competência e o grupo de municípios de um estado;
- a densidade com Brasil + estado + município numa única execução (níveis em blocos, nunca somados);
- a taxa nacional na legenda do mapa e como linha tracejada nas barras dos municípios, sem mudar cores nem o domínio;
- o ranking só com estados e a escolha pendente quando estados e municípios são misturados;
- "Limpar seleção", o padrão de cada análise e larguras de 390 e 768 px sem rolagem horizontal.
Servidor serve_ui_offline.py; nunca chama o provedor de IA.
"""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from ui_support import URL, execute_analysis, expand, municipality, offline, select, workspace

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
# Barras com rolagem: o número de cada barra fica inteiro fora dela (logo depois do fim) ou inteiro dentro dela (perto da
# borda direita), e, onde a linha tracejada da referência passa por ele, o número fica por cima da linha.
BAR_LABELS_CLEAR = """() => {
  const region = document.querySelector('[data-testid=scrollable-bars] [role=region]');
  const view = region.getBoundingClientRect(), problems = [];
  let checked = 0;
  for (const row of region.querySelectorAll('button')) {
    const box = row.getBoundingClientRect();
    if (box.top < view.top || box.bottom > view.bottom || box.top < 0 || box.bottom > window.innerHeight) continue;
    const name = row.getAttribute('aria-label'), label = row.querySelector('[data-testid=bar-value]');
    const text = label.getBoundingClientRect(), fill = row.querySelector('[data-testid=bar-fill]');
    const probe = document.elementFromPoint(text.right - 1, (text.top + text.bottom) / 2);
    if (!probe || !row.contains(probe)) continue;  // linha coberta por outro elemento da página (a caixa da conversa, fixa)
    if (fill) {
      const bar = fill.getBoundingClientRect();
      const outside = text.left >= bar.right - 0.5, inside = text.left >= bar.left - 0.5 && text.right <= bar.right + 0.5;
      if (!outside && !inside) problems.push(name + ': número sobre a borda da barra');
    }
    const mark = row.querySelector('[data-testid=bar-reference-mark]');
    if (mark) {
      const x = mark.getBoundingClientRect().left + 0.75;
      if (x > text.left + 0.5 && x < text.right - 0.5) {
        const top = document.elementFromPoint(x, (text.top + text.bottom) / 2);
        const color = getComputedStyle(label).backgroundColor.match(/[\\d.]+/g) || [];
        const opaque = color.length === 3 || (color.length === 4 && Number(color[3]) >= 0.8);
        if (!(top === label || label.contains(top)) || !opaque) problems.push(name + ': linha da referência sobre o número');
      }
    }
    checked += 1;
  }
  return [checked, problems];
}"""


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        context.add_init_script("window.__ADT_TEST__ = true")
        page = context.new_page()
        failures, llm_calls, inspections, conversation = [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))

        def conversation_options(request):
            """A conversa recebe só os municípios marcados, nunca a abrangência (Brasil e estados)."""
            if request.method == "POST" and request.url.endswith(("/api/exploration/interpret", "/api/llm/interpret-context")):
                conversation.append(json.loads(request.post_data.split('name="options"\r\n\r\n', 1)[1].split("\r\n--", 1)[0]))
        page.on("request", conversation_options)
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: inspections.append(request.url) if request.url.endswith("/api/inspect") else None)
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
            with page.expect_request(lambda r: r.url.endswith("/api/analyze"), timeout=120000) as sent:
                with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=120000) as event:
                    execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()
            body = event.value.json()
            options = json.loads(sent.value.post_data.split('name="options"\r\n\r\n', 1)[1].split("\r\n--", 1)[0])
            expect(board.get_by_test_id("result-title")).to_have_text(body["title"], timeout=60000)
            print("Resultado: " + body["title"] + " / " + str(body["total_rows"]) + " linhas", flush=True)
            return body, options

        def choose_period(label="junho de 2024"):
            summary = inline.get_by_test_id("period-summary")
            if summary.inner_text() != label:
                expand(inline.get_by_label("Escolher períodos da análise"))
                inline.get_by_role("button", name=label, exact=True).click()
            expect(summary).to_have_text(label)

        def open_scope():
            workspace(page, "preparation")
            expand(inline.get_by_test_id("territory-toggle"))
            expect(region).to_be_visible()

        # 1. Lista vertical: Brasil, estados (fonte estadual) e municípios por estado; padrão da análise com selo.
        select(page, "Densidade")
        settled()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Todos os municípios", timeout=90000)
        open_scope()
        expect(region.get_by_test_id("territory-badge-padrao")).to_have_count(1)
        expect(region.get_by_test_id("territory-option-todos-municipios")).not_to_be_checked()
        expect(region.get_by_test_id("territory-count")).to_have_text("0 selecionados")
        expect(region.get_by_test_id("territory-double-count-help")).to_contain_text(
            "quem atua em mais de um município do estado conta uma vez")
        expect(region.get_by_test_id("territory-double-count-help")).to_contain_text("a soma dos estados não é o total do Brasil")
        states = region.locator('[data-testid^="territory-option-uf-"]')
        expect(states).to_have_count(27 if real else 2)
        assert inspections and len(inspections) == 1, inspections
        if real:
            group = region.get_by_test_id("territory-group-check-31")
            expect(group).to_have_attribute("aria-label", "Municípios de Minas Gerais (853)")
            region.get_by_test_id("territory-group-toggle-31").click()
            expect(region.locator("#territorio-grupo-31").get_by_role("checkbox")).to_have_count(853)
            region.get_by_test_id("territory-group-toggle-31").click()
            expect(region.get_by_test_id("territory-option-uf-25")).to_be_visible()
        page.screenshot(path=str(OUTPUT / ("territorial-01-lista" + ("-real" if real else "") + ".png")), full_page=True)

        # 2. Análise espacial: uma competência; Brasil e estados não se aplicam (motivo em uma linha); o grupo de
        # municípios de um estado vale.
        select(page, "Análise espacial")
        settled()
        expect(inline.get_by_test_id("period-summary")).to_have_text("Escolher período")
        open_scope()
        expect(region.get_by_test_id("scope-info")).to_have_text(
            "As distâncias são calculadas entre municípios, numa competência. Marque municípios ou use todos.")
        expect(region.get_by_test_id("territory-option-brasil")).to_be_disabled()
        expect(region.get_by_test_id("territory-section-brasil")).to_contain_text(
            "Não se aplica: as distâncias e os critérios usam a localização de cada município.")
        expect(region.get_by_test_id("territory-section-estados")).to_contain_text("Não se aplica: estados não têm um ponto único.")
        region.get_by_test_id("territory-group-check-13").check()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Municípios do Amazonas (" + ("62" if real else "3") + ")")
        # Sem período e sem território de referência, o botão continua clicável: o clique nomeia as escolhas que faltam
        # (o referencial só fora da versão governada) e abre a lista de competências; nada é calculado.
        inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True).click()
        expect(inline.get_by_test_id("missing-choices")).to_have_text(
            "Falta escolher: Período e Território de referência." if real
            else "Falta escolher: Período, Território de referência e Referencial geodésico.")
        expect(inline.get_by_label("Escolher períodos da análise")).to_have_attribute("aria-expanded", "true")
        expand(inline.get_by_label("Escolher períodos da análise"))
        expect(inline.get_by_test_id("spatial-period-note")).to_have_text(
            "As distâncias usam as coordenadas da competência escolhida; em algumas competências, a fonte traz coordenadas "
            "diferentes para o mesmo município.")
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        if not real:  # catálogo sintético: o referencial é escolhido pelo usuário (na base oficial, é premissa governada)
            inline.get_by_label("Referencial geodésico", exact=True).select_option("SIRGAS2000")
        inline.get_by_label("Território de referência", exact=True).select_option("MANAUS [130260]")
        spatial, sent = calculate()
        assert sent["abrangencia"] == {"brasil": False, "estados": [], "municipios": {"todos": False, "estados": ["13"], "ids": []}}
        assert "territory_ids" not in sent
        assert spatial["metadata"]["periods"] == ["202406"] and spatial["metadata"]["selecao_territorial"]["rota"] == "municipal"
        assert spatial["total_rows"] == (62 if real else 3)
        assert spatial["rows"][0]["Território"] == "MANAUS [130260]" and spatial["rows"][0]["Distância (km)"] == 0.0

        # 3. Densidade com Brasil + estado + município, níveis em blocos (nunca somados), e a taxa nacional de contexto. O
        # estado vem da fonte estadual (médicos únicos), com a população dos seus municípios na competência.
        select(page, "Densidade")
        settled()
        open_scope()
        region.get_by_test_id("territory-clear").click()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Todos os municípios")
        region.get_by_test_id("territory-option-brasil").check()
        region.get_by_test_id("territory-option-uf-" + ("35" if real else "13")).check()
        municipality(region, "130260").check()
        state_name = "São Paulo" if real else "Amazonas"
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Brasil (total nacional), " + state_name + " (estado) e MANAUS (AM)")
        expect(region.get_by_test_id("territory-count")).to_have_text("3 selecionados")
        expect(region.get_by_test_id("territory-breakdown")).to_have_text("Brasil · 1 estado · 1 município")
        choose_period()
        density, sent = calculate()
        assert sent["abrangencia"] == {"brasil": True, "estados": ["35" if real else "13"],
                                       "municipios": {"todos": False, "estados": [], "ids": ["code:130260"]}}
        assert density["metadata"]["selecao_territorial"]["rota"] == "niveis"
        assert [row["Nível"] for row in density["rows"]] == ["Brasil (total nacional)", "Estado", "Município"]
        brazil, state, manaus = density["rows"]
        if real:
            assert (brazil["Quantidade"], brazil["População"]) == (502495, 212583750)
            assert (state["Quantidade"], state["População"]) == (148909, 45973194)
        else:
            assert (brazil["Quantidade"], brazil["População"], brazil["Densidade por 1.000"]) == (105, 16000, 6.5625)
            assert (state["Quantidade"], state["População"]) == (30, 7000)  # 30 médicos únicos, não 15 + 10 + 12
            assert (manaus["Quantidade"], manaus["Densidade por 1.000"]) == (15, 15.0)
        reference = density["metadata"]["referencia_nacional"]["valores"][0]
        assert reference["valor"] == brazil["Densidade por 1.000"] and reference["competencia"] == "202406"
        national = "2,36" if real else "6,56"
        expect(board.locator("#tabela-resultado tbody tr")).to_have_count(3)
        # Mapa: só municípios; a marca do Brasil fica na legenda, presa à escala, sem alterar cores nem o domínio.
        board.get_by_role("tab", name="Mapa", exact=True).click()
        expect(board.get_by_test_id("territory-map")).to_be_visible(timeout=60000)
        page.wait_for_function("window.__adtMapModel && window.__adtMapModel.resultId === '" + density["result_id"] + "'")
        model = page.evaluate("window.__adtMapModel")
        assert model["ids"] == ["code:130260"] and model["domain"] == [manaus["Densidade por 1.000"]] * 2
        assert model["reference"]["valor"] == reference["valor"] and model["reference"]["competencia"] == "202406"
        legend = board.get_by_test_id("national-reference")
        expect(legend).to_contain_text("Brasil (total nacional): " + national + " por 1.000 habitantes")
        expect(legend).to_contain_text("referência de contexto")
        expect(legend).to_contain_text("(fora da escala dos municípios)")
        page.screenshot(path=str(OUTPUT / ("territorial-02-densidade-niveis" + ("-real" if real else "") + ".png")), full_page=True)
        # Barras: os municípios com a linha tracejada "Brasil x,xx"; o estado em figura própria; nunca uma barra do Brasil.
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        municipal = board.get_by_test_id("level-panel-mun")
        expect(municipal.get_by_test_id("bars-reference-line")).to_contain_text("Brasil (total nacional): " + national + " por 1.000 habitantes")
        expect(municipal.get_by_test_id("bars-reference-line")).to_contain_text("referência de contexto")
        expect(municipal.get_by_text("Brasil " + national, exact=True)).to_be_visible()
        expect(board.get_by_test_id("level-panel-uf")).to_contain_text(" · Estados")
        expect(board.get_by_test_id("level-panel-uf")).to_contain_text(
            "Fonte estadual: médicos únicos de cada estado · a soma dos estados não é o total do Brasil.")
        assert page.evaluate("window.__adtMapModel.fills.length") == 1

        # 4. "Todos os municípios" (padrão da densidade): a taxa nacional fica dentro da escala; o domínio é o dos municípios.
        open_scope()
        region.get_by_test_id("territory-clear").click()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Todos os municípios")
        expect(region.get_by_test_id("territory-count")).to_have_text("0 selecionados")
        every, sent = calculate()
        assert sent["abrangencia"] == {"brasil": False, "estados": [], "municipios": {"todos": True, "estados": [], "ids": []}}
        assert every["metadata"]["selecao_territorial"]["rota"] == "municipal" and every["total_rows"] == (5570 if real else 4)
        board.get_by_role("tab", name="Mapa", exact=True).click()
        page.wait_for_function("window.__adtMapModel && window.__adtMapModel.resultId === '" + every["result_id"] + "'")
        model = page.evaluate("window.__adtMapModel")
        values = [row["Densidade por 1.000"] for row in every["rows"] if row["Densidade por 1.000"] is not None]
        assert model["domain"] == [min(values), max(values)]  # a referência não entra no domínio de cor
        assert model["reference"]["valor"] == every["metadata"]["referencia_nacional"]["valores"][0]["valor"]
        expect(board.get_by_test_id("national-reference")).to_contain_text(national + " por 1.000 habitantes")
        expect(board.get_by_test_id("national-reference")).not_to_contain_text("fora da escala")
        board.get_by_role("tab", name="Gráficos", exact=True).click()
        expect(board.get_by_test_id("bars-reference-line")).to_contain_text(national + " por 1.000 habitantes")
        if real:  # 5.570 municípios: barras com rolagem, com a linha tracejada da referência perto do zero
            scrollable = board.get_by_test_id("scrollable-bars")
            expect(scrollable).to_have_attribute("data-total", "5570")
            scrollable.scroll_into_view_if_needed()
            checked, problems = page.evaluate(BAR_LABELS_CLEAR)
            assert checked >= 5 and not problems, (checked, problems)

        # 5. Ranking só de estados; estados e municípios misturados ficam pendentes, com o motivo do backend.
        select(page, "Recortes e rankings")
        settled()
        open_scope()
        expect(region.get_by_test_id("territory-option-brasil")).to_be_disabled()
        expect(region.get_by_test_id("territory-section-brasil")).to_contain_text(
            "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só.")
        region.get_by_test_id("territory-option-uf-13").check()
        region.get_by_test_id("territory-option-uf-35").check()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Amazonas e São Paulo (estados)")
        choose_period()
        ranking, sent = calculate()
        assert sent["abrangencia"]["estados"] == ["13", "35"] and sent["abrangencia"]["brasil"] is False
        assert {row["Território"] for row in ranking["rows"]} == {"Amazonas (AM)", "São Paulo (SP)"}
        open_scope()
        municipality(region, "130260").check()
        message = region.get_by_test_id("territory-rule-message")
        expect(message).to_have_text("Você marcou estados e municípios. Recortes e rankings usa territórios do mesmo tipo: "
                                     "escolha qual manter.", timeout=60000)
        expect(inline.get_by_test_id("territory-pending")).to_be_visible()
        # A escolha pendente da abrangência retém o cálculo: o clique nomeia a caixa e nada é calculado.
        inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True).click()
        expect(inline.get_by_test_id("missing-choices")).to_have_text("Falta escolher: Abrangência territorial.")
        municipality(region, "130260").uncheck()
        expect(message).to_have_count(0, timeout=60000)
        expect(inline.get_by_test_id("missing-choices")).to_have_count(0, timeout=60000)
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)).to_be_enabled(timeout=60000)

        # 6. Limpar seleção: nada marcado, vale o padrão da análise.
        region.get_by_test_id("territory-clear").click()
        expect(region.get_by_test_id("territory-count")).to_have_text("0 selecionados")
        expect(region.get_by_test_id("territory-default")).to_have_text("Padrão desta análise: Todos os municípios")
        select(page, "Quantitativos")
        settled()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Brasil (total nacional)")

        # 7. Conversa: com o Brasil marcado, o pedido de municípios substitui a seleção por eles; a conversa nunca
        # recebe a abrangência.
        open_scope()
        region.get_by_test_id("territory-option-brasil").check()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Brasil (total nacional)")
        page.locator("#assistant-input").fill("Compare Manaus e Tefé.")
        page.get_by_role("button", name="Enviar mensagem", exact=True).click()
        expect(page.locator("#assistant-input")).to_be_enabled(timeout=60000)
        expect(inline.get_by_test_id("scope-summary")).to_have_text("MANAUS (AM) e TEFE (AM)", timeout=60000)
        open_scope()
        expect(region.get_by_test_id("territory-option-brasil")).not_to_be_checked()
        assert conversation and all("abrangencia" not in options for options in conversation), conversation

        # 8. Larguras de celular e tablet: a lista rola por dentro, sem rolagem horizontal da página.
        open_scope()
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            expect(region.get_by_test_id("territory-list")).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), width
            page.locator("#assistant-input").scroll_into_view_if_needed()
            expect(page.locator("#assistant-input")).to_be_in_viewport()
            page.screenshot(path=str(OUTPUT / ("territorial-03-largura-" + str(width) + ("-real" if real else "") + ".png")),
                            full_page=True)
        assert len(inspections) == 1, "trocar de análise ou de abrangência não recarrega a base"
        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    print("ABRANGÊNCIA TERRITORIAL PASS: lista vertical, espacial com competência, níveis na densidade, taxa nacional na "
          "legenda e nas barras, ranking de estados e escolha pendente" + (" (base versionada)." if real else "."))


if __name__ == "__main__":
    main()
