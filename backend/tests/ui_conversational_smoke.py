"""Navegação conversacional: fonte, análise, confirmações inline e resultados no chat.

Requer backend e frontend locais, Chromium/Playwright e ADT_UI_URL.
Não utiliza a API Gemini nem dados pessoais.
"""
import os

from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline

CSV = (
    "municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;população_estimada\n"
    "A;001;2024;6;MEDICINA;10;1000\n"
    "B;002;2024;6;MEDICINA;20;2000\n"
).encode("utf-8")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        assistant = page.locator("#assistente")
        expect(assistant).to_be_visible()
        assert assistant.locator("#dados").count() == 1
        expect(page.locator("#analises")).to_have_count(0)
        assert page.locator("#preparacao").count() == 0

        page.locator('input[type="file"]').set_input_files({
            "name": "dados_sinteticos.csv", "mimeType": "text/csv", "buffer": CSV
        })
        expect(assistant.get_by_text("Recebi sua base", exact=False)).to_be_visible(timeout=30000)
        expect(assistant.locator("#analises")).to_be_visible()

        assistant.get_by_role("button", name="Selecionar análise: Densidade").click()
        inline = assistant.locator("#preparacao-conversacional")
        expect(inline).to_be_visible()
        field = inline.get_by_role("combobox", name="Território", exact=True)
        expect(field).to_have_value("municipio")
        # A seleção é uma expressão no parágrafo, não um formulário em largura total.
        assert field.evaluate("el => el.closest('p') !== null")
        assert field.bounding_box()["width"] < 240
        expect(inline.get_by_role("combobox", name="Identificador territorial")).to_have_value("cod_ibge")

        inline.get_by_role("combobox", name="Unidade de contagem").select_option("pessoas")
        inline.get_by_label("Confirmo que os dados selecionados correspondem à força de trabalho em saúde.").check()
        inline.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados.").check()
        inline.get_by_role("button", name="Confirmar correspondências").click()
        execute = inline.get_by_role("button", name="Executar análise")
        expect(execute).to_be_enabled(timeout=30000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            execute.click()
        assert event.value.status == 200, event.value.text()
        result = assistant.locator("#resultados")
        expect(result).to_be_visible(timeout=30000)
        assert result.locator(".data-table tbody tr").count() == 2
        assert result.evaluate("el => el.closest('#assistente') !== null")
        with page.expect_download() as download:
            result.get_by_role("button", name="CSV", exact=True).click()
        assert download.value.suggested_filename.endswith(".csv")

        # O catálogo brasileiro disponibiliza as duas fontes na mesma sessão,
        # mantendo seleção explícita de abrangência e sem concatenar registros.
        page.reload()
        assistant = page.locator("#assistente")
        assistant.get_by_role("button", name="Usar dados do Brasil").click()
        expect(assistant.get_by_text("As fontes do Brasil e dos municípios estão disponíveis.", exact=False)).to_be_visible(timeout=30000)
        assistant.get_by_role("button", name="Selecionar análise: Densidade").click()
        scope = assistant.get_by_role("combobox", name="Abrangência territorial")
        expect(scope).to_have_value("municipal")
        scope.select_option("national")
        expect(assistant.get_by_role("combobox", name="Abrangência territorial")).to_have_value("national", timeout=30000)
        scope = assistant.get_by_role("combobox", name="Abrangência territorial")
        scope.select_option("municipal")
        expect(assistant.get_by_role("combobox", name="Abrangência territorial")).to_have_value("municipal", timeout=30000)
        context.close()
        browser.close()
    print("CONVERSATIONAL UI PASS: dual Brazil sources, source in chat, inline edits, analysis and export.")


if __name__ == "__main__":
    main()
