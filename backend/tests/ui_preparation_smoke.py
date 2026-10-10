"""Fluxos afetados pelo painel de preparação; servidores locais e catálogo instalado.

python backend/tests/ui_preparation_smoke.py
Não chama o provedor de IA nem modifica as fontes brasileiras.
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

OUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel="chrome")
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        context.route("**/api/llm/status", lambda route: route.fulfill(json={"configured": False}))
        context.route("**/api/llm/interpret*", lambda route: route.abort())
        page = context.new_page()
        page.set_default_timeout(30000)
        expect.set_options(timeout=30000)
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto("http://127.0.0.1:5173/")
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        page.get_by_role("button", name="Usar dados do Brasil", exact=True).click()
        expect(page.get_by_text("Dados do Brasil carregados", exact=True)).to_be_visible()
        choices = page.get_by_role("complementary", name="Seleção de análises")
        expect(choices.get_by_role("button")).to_have_count(10)
        panel = page.get_by_role("region", name="Preparação da análise")

        def select(name):
            page.get_by_role("button", name="Selecionar análise: " + name, exact=True).click()
            expect(panel.get_by_role("heading", name=name, exact=True)).to_be_visible()

        def stage(n):
            panel.get_by_role("button", name=["1. Identificar os dados", "2. Parâmetros e confirmações", "3. Revisar e executar"][n-1], exact=False).click()
            expect(panel.get_by_text(f"Etapa {n} de 3", exact=True)).to_be_visible()

        def execute():
            button = panel.get_by_role("button", name="Executar análise", exact=True)
            expect(button).to_be_enabled()
            with page.expect_response(lambda r: r.url.endswith("/api/analyze"), timeout=60000) as event:
                button.click()
            assert event.value.status == 200, event.value.text()[:500]
            return event.value.json()

        select("Densidade")
        expect(choices.get_by_role("button", name="Selecionar análise: Densidade", exact=True)).to_have_attribute("aria-pressed", "true")
        expect(panel.get_by_role("button", name="Confirmar identificador territorial", exact=True)).to_be_visible()
        panel.get_by_role("button", name="Confirmar associação", exact=True).click()
        panel.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        stage(3)
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_disabled()
        expect(panel.locator("strong").filter(has_text="Identificador territorial")).to_have_count(1)
        panel.get_by_role("button", name="Resolver na etapa 1", exact=True).click()
        panel.get_by_role("button", name="Confirmar identificador territorial", exact=True).click()
        expect(panel.get_by_text("Código confirmado", exact=True)).to_be_visible()
        stage(2)
        panel.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        panel.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True).check()
        panel.get_by_label("Filtrar por período", exact=True).select_option("202406")
        stage(1)
        expect(panel.get_by_text("Código confirmado", exact=True)).to_be_visible()
        expect(panel.get_by_text("Objeto confirmado", exact=True)).to_be_visible()
        stage(2)
        expect(panel.get_by_label("O que o quantitativo representa?", exact=True)).to_have_value("pessoas")
        expect(panel.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True)).to_be_checked()
        stage(3)
        density = execute()
        assert density["total_rows"] == 5570
        assert density["metadata"]["source"]["scope"] == "municipal"
        assert "territory_id" in density["metadata"]["options"]["confirmed_roles"]
        expect(page.get_by_role("button", name="CSV", exact=True)).to_be_enabled()
        page.get_by_role("button", name="Voltar à análise", exact=True).click()
        print("PASS density, steps, code confirmation and execution", flush=True)

        select("Quantitativos")
        expect(panel.get_by_label("Unidade territorial de análise", exact=True)).to_have_value("pais")
        expect(panel.get_by_text("Objeto confirmado", exact=True)).to_be_visible()
        expect(panel.get_by_role("button", name="Confirmar associação", exact=True)).to_have_count(0)
        expect(panel.get_by_text("A abrangência mudou.", exact=False)).to_be_visible()
        stage(2)
        expect(panel.get_by_label("O que o quantitativo representa?", exact=True)).to_have_value("")
        panel.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        panel.get_by_label("Filtrar por período", exact=True).select_option("")
        stage(3)
        national = execute()
        assert national["total_rows"] == 22 and national["metadata"]["source"]["scope"] == "national"
        page.get_by_role("button", name="Voltar à análise", exact=True).click()
        select("Densidade")
        expect(panel.get_by_text("Preparação deste recorte restaurada:", exact=False)).to_be_visible()
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_enabled()
        stage(1)
        expect(panel.get_by_text("Código confirmado", exact=True)).to_be_visible()
        stage(2)
        expect(panel.get_by_label("Filtrar por período", exact=True)).to_have_value("202406")
        expect(panel.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True)).to_be_checked()
        print("PASS national counts, shared meanings and municipal restoration", flush=True)

        # Selecionar um recorte incompatível informa o dado ausente e dá acesso à origem.
        stage(1)
        panel.get_by_label("Abrangência da análise").select_option("national")
        expect(panel.get_by_label("Unidade territorial de análise", exact=True)).to_have_value("pais")
        stage(3)
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_disabled()
        expect(panel.get_by_text("Associe a coluna de população correspondente.", exact=True)).to_be_visible()
        stage(1)
        panel.get_by_label("Abrangência da análise").select_option("auto")
        expect(panel.get_by_label("Unidade territorial de análise", exact=True)).to_have_value("municipio")

        select("Distribuição")
        stage(2)
        panel.get_by_label("Indicador da distribuição", exact=True).select_option("density")
        pop = panel.get_by_label("Confirmo que a população corresponde aos territórios e períodos analisados", exact=True)
        expect(pop).to_be_visible()
        pop.uncheck()
        stage(3)
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_disabled()
        expect(panel.get_by_role("button", name="Resolver na etapa 2", exact=True)).to_have_count(1)
        panel.get_by_role("button", name="Resolver na etapa 2", exact=True).click()
        pop.check()
        stage(3)
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_enabled()
        print("PASS distribution population action and legitimate blocking", flush=True)

        # Erro de revalidação não reutiliza uma habilitação anterior.
        stage(2)
        page.route("**/api/preflight", lambda route: route.fulfill(status=503, json={"detail": "Falha simulada"}))
        panel.get_by_label("Filtrar por período", exact=True).select_option("202401")
        expect(panel.get_by_role("button", name="Verificar novamente")).to_be_visible()
        stage(3)
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_disabled()
        page.unroute("**/api/preflight")
        panel.get_by_role("button", name="Verificar novamente").click()
        expect(panel.get_by_role("button", name="Executar análise", exact=True)).to_be_enabled()

        stage(1)
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / "preparation-desktop.png"))
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 2")
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(OUT / "preparation-mobile.png"))

        # Upload continua independente do catálogo e não herda suas confirmações.
        page.locator('input[type="file"]').set_input_files({"name": "international.csv", "mimeType": "text/csv",
            "buffer": b"country;year;category;count\nCanada;2024;nurses;20\n"})
        select("Quantitativos")
        expect(panel.get_by_label("Unidade territorial de análise", exact=True)).to_have_value("country")
        panel.get_by_role("button", name="Confirmar objeto de análise", exact=True).click()
        stage(2)
        expect(panel.get_by_label("O que o quantitativo representa?", exact=True)).to_have_value("")
        panel.get_by_label("O que o quantitativo representa?", exact=True).select_option("pessoas")
        stage(3)
        uploaded = execute()
        assert uploaded["rows"][0]["Quantidade"] == 20 and "source" not in uploaded["metadata"]
        assert not errors, errors
        browser.close()
    (OUT / "preparation-evidence.json").write_text(json.dumps({"status": "PASS", "page_errors": errors,
        "density_rows": 5570, "national_rows": 22, "international_upload": True,
        "scope_preservation": True, "distribution_population_confirmation": True}, indent=2), encoding="utf-8")
    print("PREPARATION PASS: focused local flows, desktop/mobile, no provider calls.")


if __name__ == "__main__":
    main()
