"""Jornada Bloco 1 com catálogo Brasil real ou fixture explicitamente configurada.

Servidor serve_ui_offline.py; nunca chama Gemini. ADT_BLOCK1_REAL=1 valida
62 municípios amazonenses e 22 competências. Nenhum registro é salvo no teste.
"""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, results, llm_calls = [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
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
                button.click()
            assert event.value.status == 200, event.value.text()
            result = event.value.json()
            results.append(result)
            print("Resultado: " + result["title"] + " / " + str(result["total_rows"]) + " linhas", flush=True)
            expect(page.get_by_role("navigation", name="Histórico de resultados").locator("ol > li")).to_have_count(len(results))
            return result

        send("Olá")
        chat.get_by_role("button", name="Usar dados do Brasil").click()
        expect(chat.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=60000)
        send("Mostre a densidade médica dos municípios do Amazonas em junho de 2024.")
        expect(page.get_by_role("region", name="Seleção territorial compartilhada").get_by_text("62 selecionados" if real else "3 selecionados", exact=True)).to_be_visible(timeout=60000)
        initial = calculate()
        assert initial["metadata"]["operation"] == "density"
        assert initial["total_rows"] == (62 if real else 3)
        assert {row["Período"] for row in initial["rows"]} == {"202406"}
        assert all(row["Densidade por 1.000"] == row["Quantidade"] / row["População"] * 1000 for row in initial["rows"])
        original = json.dumps(initial, sort_keys=True)
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
        inline.get_by_label("As medidas, unidades e populações são comparáveis entre os territórios.").check()
        compared = calculate()
        assert compared["total_rows"] == 3
        assert compared["metadata"]["options"]["territory_ids"] == ["code:130260", "code:130420", "code:130340"]
        send("Mostre a evolução dos municípios selecionados.")
        inline.get_by_label("Confirmo que os quantitativos e os períodos são comparáveis.").check()
        inline.get_by_label("Os territórios correspondem às mesmas unidades ao longo do tempo.").check()
        temporal = calculate()
        assert temporal["total_rows"] == 3
        assert len(temporal["detail_rows"]) == (66 if real else 12)
        previous = page.get_by_role("navigation", name="Histórico de resultados")
        previous.get_by_role("button", name="1. Densidade de profissionais", exact=False).click()
        expect(page.locator("#resultados .data-table tbody tr")).to_have_count(62 if real else 3)
        page.locator("#resultados").get_by_text("Consultar solicitação e parâmetros", exact=True).click()
        expect(page.locator("#resultados").get_by_text("Solicitação: Mostre a densidade médica dos municípios do Amazonas em junho de 2024.", exact=True)).to_be_visible()
        with page.expect_download() as download:
            page.locator("#resultados").get_by_role("button", name="Método e parâmetros", exact=True).click()
        exported = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert exported["result_id"] == initial["result_id"] and exported["currency"] == "NAO_VIGENTE"
        assert json.dumps(initial, sort_keys=True) == original

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
        assert "possível dupla contagem" in aggregate["rows"][0]["Tipo"]
        # Repetição exata recupera o resultado sem nova requisição/cálculo.
        inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True).click()
        expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible()
        expect(previous.locator("ol > li")).to_have_count(4)

        # Teclado/toque e dimensões móveis preservam a navegação e as ações.
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            page.get_by_role("button", name="Abrir menu", exact=True).click()
            page.get_by_role("button", name="Fechar menu", exact=True).click()
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
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
        print("Bloco 1: 10 etapas executadas; 4 resultados reais do motor; histórico, reutilização, exportação e responsividade aprovados; catálogo=" + ("Brasil real" if real else "sintético controlado"))
        browser.close()


if __name__ == "__main__":
    main()
