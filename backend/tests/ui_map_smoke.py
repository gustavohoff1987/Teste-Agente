"""Bloco 3: mapa, gráficos e tabela sincronizados na interface, com base importada sintética.

Servidor serve_ui_offline.py (qualquer catálogo); nunca chama Gemini nem serviços externos de mapa.
Confronta o modelo desenhado (gancho window.__adtMapModel, ativo só com window.__ADT_TEST__) com a
resposta da API: identidade, coordenadas, valores, estados, não avaliáveis, referências e vínculos.
Percorre seleção por busca e por clique, filtros, indicador, zoom e arrasto, gráficos, reutilização
da seleção sem execução, histórico, competências, referência mais próxima, critérios com território
não avaliável, imagem PNG, impressão, celular e operação offline.
Coordenadas fictícias; capturas em .local/ui-validation/, ignorada pelo Git.
"""
import json
import os
import tempfile
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright
from ui_support import execute_analysis, URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
# nome, código, (lat, lon) em 202401, (lat, lon) em 202406, quantidade, população — valores fictícios.
UNITS = [("ALFA", "110001", (-3.10, -60.02), (-3.10, -60.02), 10, 1000),
         ("BETA", "110002", (-3.35, -64.71), (-3.35, -64.71), 3, 2000),
         ("GAMA", "110003", (-2.63, -56.74), (-2.60, -56.70), 7, 4000),   # coordenada muda entre competências
         ("DELTA", "110004", (-2.44, -54.71), (-2.44, -54.71), 25, 1000),
         ("SANTA RITA", "110005", (-4.00, -62.00), (-4.00, -62.00), 4, 1000),  # homônimos com códigos distintos
         ("SANTA RITA", "250005", (-7.11, -34.98), (-7.11, -34.98), 9, 1000),  # outra UF
         ("EMPATE", "110007", (-3.00, -60.00), (-3.00, -60.00), 2, 1000),    # equidistante de duas referências
         ("LESTE", "110008", (-3.00, -59.00), (-3.00, -59.00), 30, 1000),
         ("OESTE", "110009", (-3.00, -61.00), (-3.00, -61.00), 30, 1000),
         ("SEM DENOMINADOR", "110010", (-5.00, -63.00), (-5.00, -63.00), 6, 1000),  # sem população em 12/2024
         ("INVALIDA", "110011", (95.0, -60.0), (95.0, -60.0), 5, 1000),      # fora do intervalo
         ("AUSENTE", "110012", (None, None), (None, None), 5, 1000)]          # sem coordenadas
EXTERNAL = []


# 12/2024 repete as coordenadas de 06/2024; a população ausente torna a densidade não avaliável nos
# critérios (a análise de densidade recusa denominador ausente, regra do Bloco 1).
WITHOUT_POPULATION = {("110010", "202412")}


def csv_text():
    lines = ["municipio;cod_ibge;periodo;categoria;quantidade;populacao;latitude;longitude"]
    for period, index in (("202401", 0), ("202406", 1), ("202412", 1)):
        for name, code, *points, quantity, population in UNITS:
            lat, lon = points[index]
            population = None if (code, period) in WITHOUT_POPULATION else population
            lines.append(";".join(str(v) if v is not None else "" for v in
                                  (name, code, period, "MEDICINA", quantity, population, lat, lon)))
    return "\n".join(lines) + "\n"


def two(value):
    """RQ-REP-05, calculado fora da interface: duas casas, arredondamento convencional, vírgula decimal."""
    text = str(Decimal(repr(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    integer, decimals = text.split(".")
    return f"{int(integer):,}".replace(",", ".") + "," + decimals


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p, tempfile.TemporaryDirectory(prefix="adt-map-ui-") as folder:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        context.on("request", lambda request: EXTERNAL.append(request.url)
                   if urlparse(request.url).hostname not in ("127.0.0.1", "localhost", "::1") else None)
        context.add_init_script("window.__ADT_TEST__ = true")
        page = context.new_page()
        failures, analyses = [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: analyses.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        chat = page.locator("#assistente")
        board = page.locator("#resultados")
        chat.locator("#assistant-input").fill("Olá")
        chat.get_by_role("button", name="Enviar mensagem").click()
        source = Path(folder) / "base_mapa_ficticia.csv"
        source.write_text(csv_text(), encoding="utf-8")
        page.get_by_label("Importar arquivo de dados").set_input_files(str(source))
        expect(chat.get_by_text("Recebi sua base", exact=False)).to_be_visible(timeout=60000)
        chat.get_by_role("button", name="Selecionar análise: Densidade").click()
        inline = chat.locator("#preparacao-conversacional")
        inline.get_by_role("combobox", name="Unidade de contagem").select_option("pessoas")
        inline.get_by_label("Filtrar por período").select_option("202406")
        inline.get_by_label("Confirmo que os dados selecionados correspondem à força de trabalho em saúde.").check()
        inline.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados.").check()
        inline.get_by_role("button", name="Confirmar correspondências").click()

        def execute():
            button = inline.get_by_role("button", name="Executar análise", exact=True)
            expect(button).to_be_enabled(timeout=60000)
            before = len(analyses)
            with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=120000) as event:
                execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()[:500]
            page.wait_for_timeout(300)
            assert len(analyses) == before + 1
            return event.value.json()

        def model():
            return page.evaluate("window.__adtMapModel")

        def send(message, expected):
            chat.locator("#assistant-input").fill(message)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
            expect(chat.locator("#assistant-input")).to_be_enabled(timeout=60000)
            expect(chat.get_by_text(expected, exact=False).last).to_be_visible()

        def confirm():
            """Mudanças de recorte pedem nova confirmação das correspondências antes da execução."""
            for text in ("Confirmo que os dados selecionados correspondem à força de trabalho em saúde.",
                         "Confirmo que a população corresponde aos territórios e períodos analisados."):
                if inline.get_by_label(text).count():
                    inline.get_by_label(text).check()
            button = inline.get_by_role("button", name="Confirmar correspondências", exact=True)
            if button.count():
                button.click()

        # 1. Sem referencial declarado o mapa fica indisponível com motivo (BLQ-DAD); a tabela continua.
        first = execute()
        assert first["metadata"]["representacao"]["geometria"]["pendencia"] == "REFERENCIAL_GEODESICO"
        expect(board.locator(".data-table tbody tr")).to_have_count(len(UNITS))
        tab = board.get_by_role("tab", name="Mapa (indisponível)")
        expect(tab).to_be_visible()  # o motivo fica a um clique, sem esconder tabela e gráficos
        tab.click()
        expect(board.get_by_text("Mapa indisponível para este resultado", exact=True)).to_be_visible()
        expect(board.get_by_label("Referencial geodésico para o mapa")).to_have_count(0)
        calls = len(analyses)
        page.get_by_role("button", name="2. Preparação").click()
        inline.get_by_text("Ver outras condições da análise", exact=True).click()
        inline.get_by_label("Referencial das coordenadas importadas", exact=True).select_option("SIRGAS2000")
        inline.get_by_label("Separador decimal das coordenadas importadas", exact=True).select_option("decimal_point")
        confirm()
        assert len(analyses) == calls  # configurar a origem não executa análise

        # 2. Com geometria autorizada: modelo desenhado idêntico ao resultado do motor.
        density = execute()
        geometry = density["metadata"]["representacao"]["geometria"]
        assert geometry["estado"] == "DISPONIVEL" and geometry["competencia"] == "202406"
        canvas = board.get_by_test_id("territory-map")
        expect(canvas).to_be_visible()
        page.wait_for_function("window.__adtMapModel && window.__adtMapModel.ids && window.__adtMapModel.resultId === '" +
                               density["result_id"] + "'")
        drawn = model()
        assert drawn["ids"] == geometry["ids"] and drawn["lat"] == geometry["lat"] and drawn["lon"] == geometry["lon"]
        values = {"code:" + row["Território"].split("[")[1].rstrip("]"): row["Densidade por 1.000"] for row in density["rows"]}
        for key, fill in zip(drawn["ids"], drawn["fills"]):
            assert (fill is None) == (values[key] is None), key  # não avaliável: anel vazado, nunca zero
        assert set(drawn["ids"]) == {"code:" + u[1] for u in UNITS} - {"code:110011", "code:110012"}
        assert {item["id"] for item in geometry["sem_geometria"]} == {"code:110011", "code:110012"}
        located = dict(zip(drawn["ids"], zip(drawn["lat"], drawn["lon"])))
        assert located["code:110003"] == (-2.6, -56.7)  # coordenada da competência do resultado
        valid = [value for value in values.values() if value is not None]
        legend = board.get_by_role("complementary", name="Legenda do mapa")
        expect(legend).to_contain_text(two(min(valid)))
        expect(legend).to_contain_text(two(max(valid)))
        expect(board.get_by_text("Sem coordenada válida na competência (2)", exact=False)).to_be_visible()
        page.screenshot(path=str(OUTPUT / "map-01-densidade.png"), full_page=True)

        # 3. Seleção por teclado (busca), por clique e com Shift; detalhes e tabela sincronizados.
        search = board.get_by_label("Buscar território (nome ou código)")
        search.fill("250005")
        search.press("ArrowDown")
        search.press("Enter")
        page.wait_for_function("window.__adtMapModel.selected.length === 1")
        assert model()["selected"] == ["code:250005"]  # homônimo distinguido pelo código
        selection = board.get_by_role("region", name="Territórios selecionados")
        expect(selection).to_contain_text("SANTA RITA [250005]")
        expect(selection).to_contain_text(two(values["code:250005"]))
        row = board.locator(".data-table tbody tr", has_text="SANTA RITA [250005]")
        expect(row).to_have_attribute("aria-selected", "true")
        expect(board.locator(".data-table tbody tr", has_text="SANTA RITA [110005]")).to_have_attribute("aria-selected", "false")

        def click_point(key, modifiers=None):
            canvas.scroll_into_view_if_needed()
            x, y = page.evaluate(f"window.__adtMapLocate('{key}')")
            box = canvas.bounding_box()
            assert 0 <= x <= box["width"] and 0 <= y <= box["height"], (key, x, y, box)
            page.mouse.move(box["x"] + x, box["y"] + y)
            if modifiers:
                page.keyboard.down("Shift")
            page.mouse.click(box["x"] + x, box["y"] + y)
            if modifiers:
                page.keyboard.up("Shift")

        # A busca centraliza e aproxima o território encontrado; a extensão completa volta à visão inicial.
        assert page.evaluate("window.__adtMapStats.slice(-1)[0].zoom") >= 6
        board.get_by_role("button", name="Ver a extensão completa").click()
        page.wait_for_function("Math.abs(window.__adtMapStats.slice(-1)[0].zoom - 1) < 1e-9")
        click_point("code:110004")
        page.wait_for_function("window.__adtMapModel.selected[0] === 'code:110004'")
        click_point("code:110001", modifiers=True)
        page.wait_for_function("window.__adtMapModel.selected.length === 2")
        assert model()["selected"] == ["code:110004", "code:110001"]
        expect(board.locator(".data-table tbody tr[aria-selected='true']")).to_have_count(2)
        # Seleção pela tabela (teclado) acrescenta à seleção visual.
        board.locator(".data-table tbody tr", has_text="BETA [110002]").press("Enter")
        page.wait_for_function("window.__adtMapModel.selected.length === 3")

        # 4. Filtro visual compartilhado: “Minha seleção” limita mapa e tabela, sem nova análise; “Ver na tabela”
        # leva do detalhe à tabela com o mesmo recorte.
        calls = len(analyses)
        filters = board.get_by_role("radiogroup", name="Filtro visual dos territórios")
        filters.get_by_text("Minha seleção (3)", exact=True).click()
        page.wait_for_function("window.__adtMapModel.passes.filter(Boolean).length === 3")
        expect(board.locator(".data-table tbody tr")).to_have_count(3)
        filters.get_by_text("Todos", exact=True).click()
        expect(board.locator(".data-table tbody tr")).to_have_count(len(UNITS))
        selection.get_by_role("button", name="Ver na tabela", exact=True).click()
        expect(filters.get_by_role("radio", name="Minha seleção (3)")).to_be_checked()
        expect(board.locator(".data-table tbody tr")).to_have_count(3)
        expect(page.locator("#tabela-resultado")).to_be_in_viewport()
        filters.get_by_text("Todos", exact=True).click()
        expect(board.locator(".data-table tbody tr")).to_have_count(len(UNITS))

        # 5. Indicador representado: troca a cor sem mudar valores; zoom, arrasto e extensão completa.
        board.get_by_label("Indicador representado").select_option("Quantidade")
        page.wait_for_function("window.__adtMapModel.indicator === 'Quantidade'")
        board.get_by_role("button", name="Ampliar o mapa").click()
        page.wait_for_function("window.__adtMapStats.slice(-1)[0].zoom > 1.5")
        canvas.scroll_into_view_if_needed()
        box = canvas.bounding_box()
        center_before = page.evaluate("window.__adtMapStats.slice(-1)[0].cx")
        page.mouse.move(box["x"] + 200, box["y"] + 200)
        page.mouse.down()
        page.mouse.move(box["x"] + 320, box["y"] + 260, steps=6)
        page.mouse.up()
        page.wait_for_timeout(100)
        assert page.evaluate("window.__adtMapStats.slice(-1)[0].cx") != center_before
        canvas.focus()
        page.keyboard.press("+")
        page.wait_for_function("window.__adtMapStats.slice(-1)[0].zoom > 2")
        board.get_by_role("button", name="Ver a extensão completa").click()
        page.wait_for_function("Math.abs(window.__adtMapStats.slice(-1)[0].zoom - 1) < 1e-9")
        assert len(analyses) == calls  # zoom, filtro e indicador não geram requisições de análise

        # 6. Gráficos: barras dos territórios selecionados (valores do motor), sem posições.
        board.get_by_role("tab", name="Gráficos").click()
        expect(board.get_by_label("Indicador das barras")).to_have_value("Quantidade")  # indicador compartilhado com o mapa
        bars = board.get_by_role("figure", name="Quantitativo (profissionais) · territórios selecionados")
        expect(bars).to_be_visible()
        for label in ("DELTA [110004]", "ALFA [110001]", "BETA [110002]"):
            expect(bars).to_contain_text(label)
        board.get_by_label("Ordem das barras").select_option("valor")
        expect(board.get_by_text("Ordenação apenas visual: não constitui posição de ranking nem resultado.", exact=True)).to_be_visible()
        expect(board.get_by_role("button", name="Imagem dos gráficos (PNG)", exact=True)).to_have_count(0)
        board.get_by_role("tab", name="Mapa", exact=True).click()
        expect(board.get_by_role("button", name="Imagem do mapa (PNG)", exact=True)).to_have_count(0)
        expect(board.get_by_role("button", name="Imprimir / PDF", exact=True)).to_be_enabled()
        with page.expect_download() as download:
            board.get_by_text("Opções técnicas avançadas", exact=True).click()
            board.get_by_role("button", name="Baixar registro técnico (JSON)", exact=True).click()
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert exported["representacao"]["geometria"] == geometry

        # 7. Reutilização da seleção: só prepara a próxima análise; nada é executado.
        calls = len(analyses)
        board.get_by_role("button", name="Usar seleção na próxima análise").click()
        expect(page.get_by_text("Seleção visual levada à preparação: 3 território(s)", exact=False)).to_be_visible()
        assert len(analyses) == calls
        shared = page.get_by_role("region", name="Seleção territorial compartilhada")
        expect(shared.get_by_text("3 selecionados", exact=True)).to_be_visible()
        shared.get_by_role("button", name="Limpar seleção", exact=True).click()  # de volta ao universo completo
        expect(shared.get_by_text("0 selecionados", exact=True)).to_be_visible()

        # 8. Outra competência do mesmo pedido: navegação entre resultados existentes, cada um com a sua geometria.
        inline.get_by_label("Filtrar por período").select_option("202401")
        confirm()
        previous = execute()
        assert previous["metadata"]["representacao"]["geometria"]["competencia"] == "202401"
        page.wait_for_function("window.__adtMapModel.resultId === '" + previous["result_id"] + "'")
        moved = dict(zip(model()["ids"], zip(model()["lat"], model()["lon"])))["code:110003"]
        assert moved == (-2.63, -56.74)
        periods = board.get_by_role("navigation", name="Competências deste pedido")
        expect(periods.get_by_role("button")).to_have_count(2)
        periods.get_by_role("button", name="06/2024").click()
        page.wait_for_function("window.__adtMapModel.resultId === '" + density["result_id"] + "'")
        expect(board.get_by_text("Você está consultando uma análise anterior", exact=False)).to_be_visible()

        # 9. A troca de competência preserva os dados e a geometria do resultado selecionado.
        assert model()["resultId"] == density["result_id"]
        assert model()["lat"] == density["metadata"]["representacao"]["geometria"]["lat"]

        # 10. Referência mais próxima: referências de outra UF e inválida, empate e cobertura parcial no mapa.
        send("Calcule a referência mais próxima.", "Preparei a análise de referência mais próxima")
        setup = inline.get_by_role("group", name="Definição das referências")
        inline.get_by_label("Referencial geodésico").select_option("SIRGAS2000")
        setup.get_by_label("Lista de municípios por nome ou código").check()
        chosen = inline.get_by_role("region", name="Seleção de referências")
        for code in ("110008", "110009", "250005", "110011"):
            chosen.get_by_role("searchbox").fill(code)
            expect(chosen.get_by_role("checkbox")).to_have_count(1)
            chosen.get_by_role("checkbox").check()
        inline.get_by_label("Filtrar por período").select_option("202406")
        confirm()
        nearest = execute()
        structured = nearest["metadata"]["nearest_reference"]
        page.wait_for_function("window.__adtMapModel.resultId === '" + nearest["result_id"] + "'")
        drawn = model()
        assert set(drawn["references"]) == {item["id"] for item in structured["conjunto_referencias"]["membros"]}
        assert "code:110011" not in drawn["ids"]  # referência sem coordenada válida fica fora do mapa
        search = board.get_by_label("Buscar território (nome ou código)")
        search.fill("110007")
        search.press("Enter")
        page.wait_for_function("window.__adtMapModel.connections.length === 1")
        record = next(item for item in structured["cobertura_referencias"] if item["unidade"] == "code:110007")
        scope = record["minimo_completo"] if record["minimo_completo"]["avaliabilidade"] == "AVALIAVEL" else record["minimo_avaliaveis"]
        assert sorted(model()["connections"][0]["to"]) == sorted(scope["referencias"]) and len(scope["referencias"]) == 2  # empate
        selection = board.get_by_role("region", name="Territórios selecionados")
        expect(selection).to_contain_text(two(scope["distancia_km"]) + " km")
        expect(selection).to_contain_text("empate: todas apresentadas")
        # Referência inválida na lista: o motor informa o mínimo entre as avaliáveis sem aceitação do usuário.
        expect(selection).to_contain_text("cobertura parcial: o mínimo do conjunto completo não é avaliável para este alvo")
        expect(selection).not_to_contain_text("aceita explicitamente")
        page.screenshot(path=str(OUTPUT / "map-02-referencia.png"), full_page=True)

        # 11. Critérios: estado do motor por território; não avaliável em anel vazado (nunca zero) e filtro
        # compartilhado entre mapa e tabela.
        send("Mostre os municípios com menos de 2 médicos por mil habitantes.", "“menos de” → <")
        inline.get_by_label("Filtrar por período").select_option("202412")
        inline.get_by_label("Unidade de contagem").select_option("pessoas")
        confirm()
        criteria = execute()
        evaluations = {item["elemento"]: item["estado"] for item in criteria["metadata"]["criterios"]["avaliacoes"]}
        assert evaluations["code:110010"] == "NAO_AVALIAVEL"
        page.wait_for_function("window.__adtMapModel.resultId === '" + criteria["result_id"] + "'")
        drawn = model()
        assert drawn["indicator"] == "Resultado"
        for key, fill in zip(drawn["ids"], drawn["fills"]):
            assert (fill is None) == (evaluations[key] == "NAO_AVALIAVEL"), key
        expect(board.get_by_role("complementary", name="Legenda do mapa")).to_contain_text("Não avaliável")
        meets = sum(evaluations[key] == "ATENDE" for key in drawn["ids"])
        page.wait_for_function(f"window.__adtMapModel.passes.filter(Boolean).length === {meets}")  # filtro inicial: Atendem
        results = board.get_by_role("region", name="Territórios classificados")
        counts = criteria["metadata"]["criterios"]["contagens"]
        results.get_by_text(f"Não avaliáveis ({counts['NAO_AVALIAVEL']})", exact=True).click()
        page.wait_for_function("window.__adtMapModel.passes.filter(Boolean).length === 1")
        expect(results.locator(".data-table tbody tr")).to_have_count(counts["NAO_AVALIAVEL"])

        # 12. Impressão: o mapa entra no documento; os controles não.
        page.emulate_media(media="print")
        assert canvas.is_visible() and not board.get_by_role("button", name="Ampliar o mapa").is_visible()
        page.emulate_media(media="screen")

        # 13. Celular e redimensionamento: sem rolagem horizontal; o mapa acompanha a largura.
        # Após sair da impressão, aguardar o desenho na largura de tela antes de medir.
        page.wait_for_function("Math.abs(window.__adtMapStats.slice(-1)[0].w - document.querySelector('[data-testid=territory-map]').getBoundingClientRect().width) < 2")
        desktop = page.evaluate("window.__adtMapStats.slice(-1)[0].w")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(400)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        assert page.evaluate("window.__adtMapStats.slice(-1)[0].w") < min(390, desktop)
        page.screenshot(path=str(OUTPUT / "map-03-celular.png"), full_page=True)
        page.set_viewport_size({"width": 1280, "height": 900})
        page.wait_for_timeout(400)
        restored = page.evaluate("window.__adtMapStats.slice(-1)[0].w")
        assert abs(restored - desktop) <= 16, (desktop, restored)  # tolerância: barra de rolagem vertical
        assert not failures, failures
        assert not EXTERNAL, EXTERNAL  # nenhum recurso externo (mapa sem serviço de terceiros)
        browser.close()
    print("Jornada do mapa e das visualizações: OK")


if __name__ == "__main__":
    main()
