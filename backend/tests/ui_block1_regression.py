"""Regressões atuais de importação, apresentação, seleção e retomada sem Gemini."""
import io
import json
import os
from pathlib import Path

from openpyxl import Workbook
from playwright.sync_api import sync_playwright, expect
from ui_support import workspace, execute_analysis, URL, offline

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
                execute_analysis(page, button)
            assert event.value.status == 200, event.value.text()
            return event.value.json()

        first = execute()
        assert first["total_rows"] == 3
        page.get_by_role("button", name="1. Territórios").click()
        selection = page.get_by_role("region", name="Seleção territorial compartilhada")
        for code in ("local-a", "local-b"):
            selection.get_by_role("searchbox").fill(code)
            selection.get_by_role("checkbox").check()
        page.get_by_role("button", name="Comparar selecionados", exact=True).click()
        page.get_by_role("button", name="2. Preparação").click()
        inline.get_by_role("combobox", name="Indicador", exact=True).select_option("quantity")
        # Arquivo importado: a declaração explícita de comparabilidade continua necessária.
        inline.get_by_label("As medidas, unidades e populações são comparáveis entre os territórios.").check()
        inline.get_by_role("button", name="Confirmar correspondências").click()
        pair = execute()
        assert pair["rows"][0]["Diferença A − B"] == -10
        assert pair["metadata"]["options"]["territory_ids"] == ["code:local-a", "code:local-b"]
        # Sem o identificador associado, os IDs "code:" deixam de existir: a seleção é limpa
        # em vez de manter o pré-exame recusado (422) sem explicação.
        workspace(page, "preparation")
        with page.expect_response(lambda response: response.url.endswith("/api/preflight")) as checked:
            inline.get_by_role("combobox", name="Identificador territorial", exact=True).select_option("")
        workspace(page, "territories")
        expect(selection.get_by_text("0 selecionados", exact=True)).to_be_visible()
        assert checked.value.status == 200, checked.value.text()
        workspace(page, "results")
        result = page.locator("#resultados")
        expect(page.get_by_role("navigation", name="Histórico de resultados")).to_have_count(0)
        expect(result.get_by_test_id("comparison-territory-row")).to_have_count(2)
        result.get_by_role("button", name="Retomar parâmetros deste resultado").click()
        workspace(page, "territories")
        expect(selection.get_by_text("2 selecionados", exact=True)).to_be_visible()
        workspace(page, "results")
        expect(result.get_by_test_id("result-status")).to_contain_text("válido e vigente")
        expect(result.get_by_text("Registrar correção que invalida este resultado", exact=True)).to_have_count(0)
        expect(result.get_by_role("button", name="CSV", exact=True)).to_be_enabled()
        with page.expect_download() as download:
            result.get_by_text("Opções técnicas avançadas", exact=True).click()
            result.get_by_role("button", name="Baixar registro técnico (JSON)").click()
        metadata = json.loads(Path(download.value.path()).read_text(encoding="utf-8"))
        assert metadata["validity"] == "VALIDO" and metadata["result_id"] == pair["result_id"]
        assert not metadata["invalidation_reason"]
        # Retomar os parâmetros do resultado atual reaproveita o cálculo existente.
        workspace(page, "preparation")
        button = inline.get_by_role("button", name="Executar análise", exact=True)
        expect(button).to_be_enabled(timeout=30000)
        execute_analysis(page, button)
        expect(page.get_by_text("Resultado existente recuperado, sem recalcular.", exact=True)).to_be_visible()
        assert len(calculated) == 2

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
        workspace(page, "results")
        expect(result.get_by_test_id("result-status")).to_contain_text("histórico válido")
        assert len(calculated) == 2  # Trocar fonte não executa análise.
        expect(result.get_by_test_id("comparison-territory-row")).to_have_count(2)
        workspace(page, "territories")
        expect(selection.get_by_text("0 selecionados", exact=True)).to_be_visible()
        assert not errors, errors
        browser.close()
        print("BLOCK1 REGRESSION PASS: CSV/XLSX, opaque IDs, quantity comparison, result presentation, parameter restore and source replacement.")


if __name__ == "__main__":
    main()
