"""UI → API → transporte Gemini simulado; nenhum acesso ao provedor real.

Requer um processo novo de serve_ui_fake_gemini.py e ADT_FAKE_GEMINI_LOG.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from ui_support import URL, offline


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width":1280,"height":900})
        offline(context)
        page = context.new_page()
        errors, analyses = [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: analyses.append(request) if request.url.endswith("/api/analyze") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        prompt = page.locator("#assistant-input")

        def send(message, endpoint, status=200):
            prompt.fill(message)
            with page.expect_response(lambda response: response.url.endswith(endpoint), timeout=30000) as event:
                page.get_by_role("button", name="Enviar mensagem").click()
            assert event.value.status == status, event.value.text()
            expect(prompt).to_be_enabled(timeout=30000)
            return event.value

        first = send("Quero analisar a densidade", "/api/llm/interpret").json()
        assert first["executed"] is False and first["proposal"]["operation"] == "density"
        page.get_by_role("button", name="Usar dados do Brasil").click()
        inline = page.locator("#preparacao-conversacional")
        expect(inline.get_by_text("Os dados já estão preparados", exact=False)).to_be_visible(timeout=30000)
        if inline.get_by_label("Escolher períodos da análise").count():
            inline.get_by_label("Escolher períodos da análise").click()
            # A escolha do período dispara novo pré-exame; o contexto só é enviado como pronto depois
            # da resposta (context_ready). Sem esperar, o botão pode ser lido habilitado nos ~10 ms antes
            # de o pré-exame começar e a mensagem sair durante ele (409 "Aguarde ou repita a validação").
            with page.expect_response(lambda response: response.url.endswith("/api/preflight") and
                                      b'"period_filter":"202406"' in (response.request.post_data_buffer or b""), timeout=30000):
                inline.get_by_role("button", name="junho de 2024", exact=True).click()
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_enabled(timeout=30000)
        contextual = send("Quero analisar a densidade dos municípios", "/api/llm/interpret-context").json()
        assert contextual["verification"]["source"] == "BACKEND_PREFLIGHT"
        assert contextual["executed"] is False
        assert not analyses
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as response:
            inline.get_by_role("button", name="Calcular e mostrar resultado").click()
        assert response.value.status == 200
        expect(page.locator("#resultados").get_by_test_id("result-title")).to_have_text("Densidade de profissionais")
        # O provedor falso produz uma combinação inválida; o backend a rejeita como
        # resposta a montante fora do contrato (502, mesmo contrato do cenário A12).
        invalid = send("Quero quantitativos invalido", "/api/llm/interpret-context", 502)
        assert "fake-offline-key" not in invalid.text() and len(analyses) == 1
        expect(page.get_by_role("alert").filter(has_text="fora do contrato")).to_be_visible()
        send("Quero analisar a densidade", "/api/llm/interpret-context")
        expect(page.get_by_role("alert")).to_have_count(0)
        assert len(analyses) == 1
        payload = Path(os.environ["ADT_FAKE_GEMINI_LOG"]).read_text(encoding="utf-8")
        records = [json.loads(line) for line in payload.splitlines() if line.strip()]
        assert len(records) >= 4
        for protected in ("Dados_Municipios_Brasil.csv", "Dados_Brasil.xlsx", "cod_ibge", "população_estimada"):
            assert protected not in payload
        assert not errors, errors
        browser.close()
        print("BLOCK1 INTEGRATION PASS: preliminary/contextual interpretation, deterministic calculation, rejected invalid proposal, recovery and minimized fake-provider payload.")


if __name__ == "__main__":
    main()
