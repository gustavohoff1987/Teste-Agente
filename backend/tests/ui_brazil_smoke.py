"""Base Brasil real na interface: catálogo, recortes, CSV e retorno ao upload.

Requer servidores locais e instalação privada da base. Não chama o Gemini.
"""
import csv
import io
import json
import os
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / ".local" / "ui-validation"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    expected = pd.read_excel(Path(os.environ["ADT_REAL_DATA_DIR"]) / "Dados_Brasil.xlsx")
    with sync_playwright() as p:
        expect.set_options(timeout=60000)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        context.route("**/api/llm/status", lambda route: route.fulfill(json={"configured": True}))
        context.route("**/api/llm/interpret*", lambda route: route.fulfill(json={
            "reply": "Confira os requisitos para a análise solicitada.", "proposal": {
                "operation": "counts", "indicator": "quantity", "period": "", "category": "", "territory": ""},
            "verification": {"source": "BACKEND_PREFLIGHT", "capability_status": "available",
                "slots": {}, "blockers": [], "ready_to_execute": False, "next_action": "confirm_in_interface"},
            "executed": False, "origin": "INTERPRETACAO_LLM", "requires_confirmation": True}))
        page = context.new_page()
        page.set_default_timeout(60000)
        errors, requests = [], []
        page.on("pageerror", lambda exc: (errors.append(str(exc)), print("PAGE ERROR", exc, flush=True)))
        page.on("request", lambda req: requests.append(req) if req.method == "POST" else None)
        page.goto("http://localhost:5173/")
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        page.get_by_role("button", name="Usar dados do Brasil", exact=True).click()
        expect(page.get_by_text("Dados do Brasil carregados", exact=True)).to_be_visible()
        print("Brazil catalog loaded", flush=True)
        assert "Dados_Brasil.xlsx" not in page.inner_text("body")
        assert "Dados_Municipios_Brasil.csv" not in page.inner_text("body")
        card = page.locator("#analises .analysis-card")
        card.press("Home")
        print("Carousel Home", flush=True)
        card.press("ArrowRight")
        print("Carousel counts", flush=True)
        expect(page.locator("#analysis-card-status")).to_have_text("Selecione para conferir o recorte")
        card.click()
        print("Requested national scope", flush=True)
        territory = page.get_by_label("Unidade territorial de análise", exact=True)
        period = page.get_by_label("Unidade temporal de análise", exact=True)
        try:
            expect(territory).to_have_value("pais", timeout=15000)
        except Exception:
            print("Source switch failed:", page.locator("#associacoes select").evaluate_all("nodes => nodes.map(n => n.value)"), flush=True)
            print("Alerts:", page.get_by_role("alert").all_text_contents(), flush=True)
            page.screenshot(path=str(OUTPUT / "brazil-failure.png"))
            raise
        print("National scope selected", flush=True)
        execute = page.get_by_role("button", name="Executar análise", exact=True)
        expect(execute).to_be_disabled()
        assert not any(req.url.endswith("/api/analyze") for req in requests)
        period.select_option("Período (ano e mês)")
        page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        page.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        expect(execute).to_be_enabled()
        print("National counts enabled", flush=True)
        page.screenshot(path=str(OUTPUT / "brazil-national-desktop.png"))
        prompt = page.get_by_role("textbox", name="Descreva sua análise ou faça uma pergunta")
        prompt.fill("Quantitativos do Brasil")
        page.get_by_role("button", name="Enviar mensagem").click()
        expect(page.get_by_role("log")).to_contain_text("Confira os requisitos")
        chat = next(req for req in reversed(requests) if req.url.endswith("/api/llm/interpret-context"))
        assert 'name="dataset"' in chat.post_data and 'name="file"' not in chat.post_data
        with page.expect_response(lambda r: r.url.endswith("/api/analyze")) as event:
            execute.click()
        result = event.value.json()
        assert event.value.status == 200 and result["total_rows"] == len(expected) == 22
        assert result["metadata"]["source"]["scope"] == "national"
        values = {f"{int(row.periodo_ano):04d}{int(row.periodo_mes):02d}": int(row.contagem)
                  for row in expected.itertuples()}
        with page.expect_download() as event:
            page.get_by_role("button", name="CSV", exact=True).click()
        rows = list(csv.DictReader(io.StringIO(Path(event.value.path()).read_text(encoding="utf-8-sig")), delimiter=";"))
        assert len(rows) == 22
        assert all(row["Território"] == "Brasil" and float(row["Quantidade"]) == values[row["Período"]] for row in rows)
        print("National CSV verified", flush=True)
        page.get_by_role("button", name="Início", exact=True).click()
        card.press("Home")
        card.click()
        expect(territory).to_have_value("municipio")
        print("Municipal scope selected", flush=True)
        expect(page.get_by_role("log")).not_to_contain_text("Confira os requisitos")
        expect(execute).to_be_disabled()
        # Mudança de granularidade não herda confirmações do total nacional.
        expect(page.get_by_label("O que o quantitativo representa?", exact=True)).to_have_value("")
        period.select_option("Período (ano e mês)")
        page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        page.get_by_text("Identificação territorial · código associado", exact=True).click()
        page.get_by_role("button", name="Confirmar identificador territorial", exact=True).click()
        page.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        page.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True).check()
        page.locator('select[aria-label="Filtrar por período"]:visible').select_option("202406")
        expect(execute).to_be_enabled()
        with page.expect_response(lambda r: r.url.endswith("/api/analyze")) as event:
            execute.click()
        density = event.value.json()
        assert event.value.status == 200 and density["total_rows"] == 5570
        assert density["metadata"]["source"]["scope"] == "municipal"
        assert all(row["Período"] == "202406" for row in density["rows"])
        for req in requests:
            if req.url.endswith(("/api/analyze", "/api/inspect", "/api/preflight")):
                assert 'name="dataset"' in req.post_data and 'name="file"' not in req.post_data
        page.get_by_role("button", name="Início", exact=True).click()
        # Seleção explícita prevalece sobre o padrão da análise.
        page.get_by_label("Abrangência da análise").select_option("municipal")
        expect(territory).to_have_value("municipio")
        card.press("ArrowRight")
        card.click()
        expect(territory).to_have_value("municipio")
        # O upload internacional continua acessível e não herda a base Brasil.
        page.locator('input[type="file"]').set_input_files({"name": "international.csv", "mimeType": "text/csv",
            "buffer": b"country;year;category;count\nCanada;2024;nurses;20\n"})
        expect(territory).to_have_value("country")
        expect(page.get_by_label("Abrangência da análise")).to_have_count(0)
        expect(page.get_by_text("international.csv carregado", exact=True)).to_be_visible()
        card.press("Home")
        card.press("ArrowRight")
        card.click()
        page.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        page.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        expect(execute).to_be_enabled()
        with page.expect_response(lambda r: r.url.endswith("/api/analyze")) as event:
            execute.click()
        uploaded = event.value.json()
        assert event.value.status == 200 and uploaded["rows"][0]["Quantidade"] == 20
        assert uploaded["rows"][0]["Território"] == "Canada"
        assert "source" not in uploaded["metadata"]
        page.get_by_role("button", name="Início", exact=True).click()
        page.get_by_role("button", name="Usar dados do Brasil", exact=True).click()
        expect(territory).to_have_value("municipio")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        page.locator("#dados").scroll_into_view_if_needed()
        page.screenshot(path=str(OUTPUT / "brazil-mobile.png"))
        assert not errors, errors
        (OUTPUT / "brazil-evidence.json").write_text(json.dumps({
            "status": "PASS", "national_export_rows": 22, "municipal_density_rows": 5570,
            "resident_requests_without_file_upload": True, "international_upload": True,
            "scope_resets_confirmations": True, "page_errors": errors}, indent=2), encoding="utf-8")
        browser.close()
    print("BRAZIL UI PASS: logical catalog, national CSV, municipal density, scope reset, contextual chat, international upload, mobile.")


if __name__ == "__main__":
    main()
