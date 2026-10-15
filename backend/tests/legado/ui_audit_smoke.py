"""Casos de navegador A02/A05/A08/A10; transporte do servidor explicitamente offline."""
import csv
import io
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline, select, stage

OUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        page.set_default_timeout(30000)
        expect.set_options(timeout=30000)
        errors, requests = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: requests.append(request.url))
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()

        def upload(name, content):
            page.locator('input[type="file"]').set_input_files({"name": name, "mimeType": "text/csv", "buffer": content})
            expect(page.get_by_text(name + " carregado", exact=True)).to_be_visible()

        def execute():
            stage(page, 3)
            button = page.get_by_role("button", name="Executar análise", exact=True)
            expect(button).to_be_enabled()
            with page.expect_response(lambda r: r.url.endswith("/api/analyze")) as event:
                button.click()
            assert event.value.status == 200, event.value.text()
            body = event.value.json()
            page.get_by_role("button", name="Voltar à análise", exact=True).click()
            return body

        upload("temporal.csv", b"Municipality,Year,Profession,Count,Population\nA,2023,Nurses,10,1000\nA,2024,Nurses,20,4000\n")
        select(page, "Evolução temporal")
        page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        stage(page, 2)
        page.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        page.get_by_label("Confirmo que os períodos e os quantitativos são comparáveis", exact=True).check()
        page.get_by_label("Confirmo que os territórios mantêm identidade comparável ao longo dos períodos", exact=True).check()
        stage(page, 3)
        expect(page.get_by_role("button", name="Executar análise", exact=True)).to_be_disabled()
        stage(page, 2)
        page.get_by_label("Indicador da evolução temporal", exact=True).select_option("quantity")
        assert execute()["rows"][0]["Variação (%)"] == 100
        select(page, "Densidade")
        stage(page, 2)
        page.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True).check()
        select(page, "Evolução temporal")
        stage(page, 2)
        expect(page.get_by_label("Indicador da evolução temporal", exact=True)).to_have_value("quantity")
        assert execute()["rows"][0]["Variação (%)"] == 100
        stage(page, 2)
        page.get_by_label("Indicador da evolução temporal", exact=True).select_option("density")
        assert execute()["rows"][0]["Variação (%)"] == -50
        select(page, "Relatórios")
        stage(page, 3)
        expect(page.get_by_role("button", name="Executar análise", exact=True)).to_be_disabled()
        stage(page, 2)
        page.get_by_label("Indicador do relatório", exact=True).select_option("quantity")
        assert "Densidade por 1.000" not in execute()["rows"][0]
        print("PASS A02 explicit indicators and navigation independence", flush=True)

        # Falha do exame mantém o endpoint contextual. Saudação local continua disponível.
        stage(page, 2)
        page.route("**/api/preflight", lambda route: route.fulfill(status=503, json={"detail": "Falha simulada"}))
        page.get_by_label("Filtrar por período", exact=True).select_option("2024")
        expect(page.get_by_role("button", name="Verificar novamente")).to_be_visible()
        prompt = page.get_by_role("textbox", name="Descreva sua análise ou faça uma pergunta")
        prompt.fill("Quero quantitativos em 2024")
        with page.expect_response(lambda r: r.url.endswith("/api/llm/interpret-context")) as event:
            page.get_by_role("button", name="Enviar mensagem").click()
        assert event.value.status == 409
        expect(page.get_by_role("alert").filter(has_text="Aguarde ou repita")).to_be_visible()
        prompt.fill("Olá")
        page.get_by_role("button", name="Enviar mensagem").click()
        expect(page.get_by_role("log")).to_contain_text("Que tipo de análise")
        assert not any(url.endswith("/api/llm/interpret") for url in requests)
        page.unroute("**/api/preflight")
        page.get_by_role("button", name="Verificar novamente").click()
        print("PASS A10 contextual failure and local guidance", flush=True)

        upload("spatial.csv", b"Municipality,Latitude,Longitude\nA,0,0\nB,0,0.000001\n")
        select(page, "Análise espacial")
        stage(page, 2)
        page.get_by_role("button", name="Confirmar as colunas de latitude e longitude selecionadas").click()
        page.get_by_label("Referencial geodésico informado para a base").select_option("SIRGAS2000")
        page.get_by_label("Território de referência", exact=True).select_option("A")
        stage(page, 3)
        button = page.get_by_role("button", name="Executar análise", exact=True)
        expect(button).to_be_enabled()
        with page.expect_response(lambda r: r.url.endswith("/api/analyze")) as event:
            button.click()
        distance = event.value.json()["rows"][1]["Distância (km)"]
        with page.expect_download() as event:
            page.get_by_role("button", name="CSV", exact=True).click()
        rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))
        assert float(rows[1]["Distância (km)"]) == distance > 0
        page.get_by_role("button", name="Voltar à análise", exact=True).click()
        print("PASS A05 full precision CSV", flush=True)

        upload("units.csv", b"Municipality,Year,Profession,Count\nA,2024,Nurses,10\nB,2024,Nurses,20\n")
        select(page, "Distribuição")
        page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        stage(page, 2)
        page.get_by_label("O que o quantitativo representa?", exact=True).select_option("vinculos")
        page.get_by_label("Indicador da distribuição", exact=True).select_option("quantity")
        execute()
        page.get_by_role("button", name="Resultados", exact=True).click()
        with page.expect_download() as event:
            page.get_by_role("button", name="Exportar territórios (CSV)", exact=True).click()
        rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))
        assert len(rows) == 2 and "Quantidade de vínculos" in rows[0]
        assert all(row["Unidade de contagem"] == "vínculos" for row in rows)
        assert not errors, errors
        page.screenshot(path=str(OUT / "audit-distribution.png"))
        browser.close()
    (OUT / "audit-evidence.json").write_text(json.dumps({"status": "PASS", "page_errors": errors,
        "temporal_quantity_percent": 100, "temporal_density_percent": -50,
        "spatial_csv_km": distance, "count_unit_csv": "vínculos", "context_failure_status": 409}, indent=2), encoding="utf-8")
    print("AUDIT UI PASS: A02/A05/A08/A10, real calculations and exports, no external calls.")


if __name__ == "__main__":
    main()
