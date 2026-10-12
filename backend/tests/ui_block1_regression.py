"""Regressões atuais de importação, histórico, seleção e validade sem Gemini."""
import io
import json
import os
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline

CSV = b"territorio_analise;codigo_identificador;periodo;categoria_profissional;quantidade;populacao\nAlfa;local-a;2024;MEDICINA;10;1000\nBeta;local-b;2024;MEDICINA;20;4000\nGama;local-c;2024;MEDICINA;30;5000\n"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        errors, calculated = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("response", lambda response: calculated.append(response.json()) if response.url.endswith("/api/analyze") and response.status == 200 else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        page.locator("#assistant-input").fill("Olá")
        page.get_by_role("button", name="Enviar mensagem").click()
        page.locator('input[type="file"]').set_input_files({"name":"local.csv", "mimeType":"text/csv", "buffer":CSV})
        expect(page.get_by_text("Recebi sua base", exact=False)).to_be_visible(timeout=30000)
        page.get_by_role("button", name="Selecionar análise: Densidade", exact=True).click()
        inline = page.locator("#preparacao-conversacional")
        inline.get_by_role("combobox", name="Unidade de contagem", exact=True).select_option("pessoas")
        inline.get_by_label("Confirmo que os dados selecionados correspondem à força de trabalho em saúde.").check()
        inline.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados.").check()
        inline.get_by_role("button", name="Confirmar correspondências").click()

        def execute():
            button = inline.get_by_role("button", name="Executar análise", exact=True)
            expect(button).to_be_enabled(timeout=30000)
            with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
                button.click()
            assert event.value.status == 200, event.value.text()
            return event.value.json()

        first = execute()
        assert first["total_rows"] == 3
        selection = page.get_by_role("region", name="Seleção territorial compartilhada")
        for code in ("local-a", "local-b"):
            selection.get_by_role("searchbox").fill(code)
            selection.get_by_role("checkbox").check()
        page.get_by_role("button", name="Comparar selecionados", exact=True).click()
        inline.get_by_role("combobox", name="Indicador", exact=True).select_option("quantity")
        inline.get_by_label("As medidas, unidades e populações são comparáveis entre os territórios.").check()
        inline.get_by_role("button", name="Confirmar correspondências").click()
        pair = execute()
        assert pair["rows"][0]["Diferença A − B"] == -10
        assert pair["metadata"]["options"]["territory_ids"] == ["code:local-a", "code:local-b"]
        # Sem o identificador associado, os IDs "code:" deixam de existir: a seleção é limpa
        # em vez de manter o pré-exame recusado (422) sem explicação.
        with page.expect_response(lambda response: response.url.endswith("/api/preflight")) as checked:
            inline.get_by_role("combobox", name="Identificador territorial", exact=True).select_option("")
        expect(selection.get_by_text("0 selecionados", exact=True)).to_be_visible()
        assert checked.value.status == 200, checked.value.text()
        history = page.get_by_role("navigation", name="Histórico de resultados")
        expect(history.locator("ol > li")).to_have_count(2)
        history.get_by_role("button", name="1. Densidade de profissionais", exact=False).click()
        result = page.locator("#resultados")
        expect(result.locator(".data-table tbody tr")).to_have_count(3)
        result.get_by_text("Consultar solicitação e parâmetros", exact=True).click()
        result.get_by_role("button", name="Retomar parâmetros deste resultado").click()
        expect(selection.get_by_text("0 selecionados", exact=True)).to_be_visible()
        expect(result.get_by_test_id("result-status")).to_contain_text("válido e vigente")
        result.get_by_text("Registrar correção que invalida este resultado", exact=True).click()
        result.get_by_label("Motivo factual da invalidação").fill("Quantitativo de origem declarado incorreto pelo responsável pela base.")
        result.get_by_role("button", name="Invalidar este resultado", exact=True).click()
        expect(result.get_by_test_id("result-status")).to_contain_text("Resultado invalidado")
        expect(result.get_by_role("button", name="CSV", exact=True)).to_be_disabled()
        expect(result.get_by_role("button", name="Retomar parâmetros deste resultado")).to_be_disabled()
        with page.expect_download() as download:
            result.get_by_role("button", name="Método e parâmetros").click()
        metadata = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert metadata["validity"] == "INVALIDADO"
        assert metadata["invalidation_reason"]
        # Não reutiliza um resultado invalidado, mesmo com parâmetros iguais.
        again = execute()
        assert again["result_id"] != first["result_id"]
        expect(history.locator("ol > li")).to_have_count(3)
        assert len(calculated) == 3

        # Troca de fonte preserva o histórico. XLSX com duas abas exige escolha.
        book = Workbook()
        book.active.title = "Notas"
        book.active.append(["observacao"])
        book.active.append(["Escolher a aba Dados"])
        data = book.create_sheet("Dados")
        data.append(["territorio_analise", "periodo", "categoria_profissional", "quantidade"])
        data.append(["Outro território", "2024", "MEDICINA", 50])
        buffer = io.BytesIO(); book.save(buffer)
        # O mesmo input continua no seletor de fonte, disponibilizado pela ação do banner.
        page.locator('input[type="file"]').set_input_files({"name":"duas-abas.xlsx", "mimeType":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "buffer":buffer.getvalue()})
        expect(page.get_by_role("combobox", name="Qual aba deseja utilizar?", exact=True)).to_be_visible()
        page.get_by_role("combobox", name="Qual aba deseja utilizar?", exact=True).select_option("Dados")
        expect(inline.get_by_role("combobox", name="Território", exact=True)).to_have_value("territorio_analise", timeout=30000)
        expect(history.locator("ol > li")).to_have_count(3)
        expect(result.get_by_test_id("result-status")).to_contain_text("histórico válido")
        assert len(calculated) == 3  # Trocar fonte não executa análise.
        history.get_by_role("button", name="2. Comparação territorial", exact=False).click()
        expect(result.locator(".data-table tbody tr")).to_have_count(1)
        expect(selection.get_by_text("0 selecionados", exact=True)).to_be_visible()
        assert not errors, errors
        browser.close()
        print("BLOCK1 REGRESSION PASS: CSV/XLSX, opaque IDs, quantity comparison, history, parameter restore, invalidation and source replacement.")


if __name__ == "__main__":
    main()
