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
from ui_support import workspace, execute_analysis, URL, offline

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
        page.get_by_role("button", name="1. Preparação").click()
        expect(page.get_by_role("region", name="Seleção territorial compartilhada").get_by_text("62 selecionados" if real else "3 selecionados", exact=True)).to_be_visible(timeout=60000)
        page.get_by_role("button", name="1. Preparação").click()
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
        page.get_by_role("button", name="1. Preparação").click()
        selection = page.get_by_role("region", name="Seleção territorial compartilhada")
        selection.get_by_role("button", name="Limpar seleção", exact=True).click()
        for name, code in [("MANAUS", "130260"), ("TEFE", "130420"), ("PARINTINS", "130340")]:
            selection.get_by_role("searchbox").fill(code)
            choice = selection.get_by_role("checkbox")
            expect(choice).to_have_count(1)
            choice.check()
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        send("Compare os selecionados.")
        inline = page.locator("#preparacao-conversacional")
        expect(inline.get_by_label("As medidas, unidades e populações são comparáveis entre os territórios.")).to_have_count(0)
        compared = calculate()
        assert compared["total_rows"] == 3
        expect(page.get_by_test_id("comparison-territory-row")).to_have_count(3)
        # Cada território da comparação deve ocupar um registro visual próprio.
        assert compared["metadata"]["options"]["territory_ids"] == ["code:130260", "code:130420", "code:130340"]
        # Mesmos valores da densidade inicial: a seleção não altera o cálculo de cada membro.
        assert {row["Período"] for row in compared["rows"]} == {"202406"}
        assert all(row["Densidade por 1.000"] == density[row["Território"]] for row in compared["rows"])
        shot("block1-02-comparacao.png")
        send("Mostre a evolução dos municípios selecionados.")
        inline.get_by_label("Confirmo que os quantitativos e os períodos são comparáveis.").check()
        inline.get_by_label("Os territórios correspondem às mesmas unidades ao longo do tempo.").check()
        temporal = calculate()
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
        expect(board.get_by_text("Solicitação: Mostre a evolução dos municípios selecionados.", exact=True)).to_be_visible()
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
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)).to_be_disabled()
        inline.get_by_label("As populações são partes sem sobreposição do conjunto agregado.").check()
        inline.get_by_label("Caso contrário, autorizo somar componentes, mesmo com possível dupla contagem.").check()
        aggregate = calculate()
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
            expect(page.get_by_test_id("main-navigation").locator(':scope > button')).to_have_count(4)
            expect(page.get_by_test_id("analysis-history-menu").locator('summary')).to_be_visible()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
            shot(f"block1-07-largura-{width}.png")
        workspace(page, "territories")
        search = selection.get_by_role("searchbox")
        search.focus()
        expect(search).to_be_focused()
        search.fill("130420")
        checkbox = selection.get_by_role("checkbox")
        checkbox.focus()
        checkbox.press("Space")
        expect(selection.get_by_text("2 selecionados", exact=True)).to_be_visible()
        checkbox.press("Space")
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        assert not llm_calls, llm_calls
        assert not failures, failures
        print("Bloco 1: 10 etapas executadas; 4 resultados reais do motor; retomada sem recálculo; CSV/JSON conferidos contra o motor; "
              "apresentação, reutilização e responsividade aprovadas; catálogo=" + ("Brasil real" if real else "sintético controlado"))
        browser.close()


if __name__ == "__main__":
    main()
