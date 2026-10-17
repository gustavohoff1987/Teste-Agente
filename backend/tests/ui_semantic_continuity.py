"""Continuidade semântica e painéis com rolagem independente; provedor simulado."""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        errors, analyses, interpretations = [], [], []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.on("request", lambda request: analyses.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.on("request", lambda request: interpretations.append(request.url) if request.url.endswith("/api/llm/interpret-context") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        chat = page.locator("#assistente")
        composer = page.locator("#conversation-composer")
        history = page.get_by_role("region", name="Histórico de análises", exact=True)

        def visible_composer():
            box = composer.bounding_box()
            assert box and box["y"] >= 0 and box["y"] + box["height"] <= page.viewport_size["height"] + 2, box
            toolbar = page.locator(".analysis-toolbar").bounding_box()
            assert toolbar and toolbar["y"] >= 0 and toolbar["y"] + toolbar["height"] <= page.viewport_size["height"] + 2, toolbar
            assert page.evaluate("window.scrollY <= 2"), "Navegar no resultado deslocou a página externa."
            assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")

        def send(message, endpoint=None):
            page.locator("#assistant-input").fill(message)
            if endpoint:
                with page.expect_response(lambda response: response.url.endswith(endpoint), timeout=60000) as event:
                    page.get_by_role("button", name="Enviar mensagem", exact=True).click()
                assert event.value.status == 200, event.value.text()
                result = event.value.json()
            else:
                page.get_by_role("button", name="Enviar mensagem", exact=True).click()
                result = None
            expect(page.locator("#assistant-input")).to_be_enabled(timeout=60000)
            visible_composer()
            return result

        send("Olá")
        expect(history).to_be_visible()
        page.get_by_role("button", name="Usar dados do Brasil", exact=False).click()
        expect(page.get_by_test_id("current-source")).to_be_visible(timeout=60000)
        first_choices = send("Analise o perfil dos municipios", "/api/llm/interpret-context")
        assert first_choices["clarification"]["code"] == "AMBIGUIDADE_MATERIAL"
        with page.expect_response(lambda response: response.url.endswith("/api/exploration/interpret")) as event:
            chat.get_by_role("button", name="Densidade · Densidade por 1.000 habitantes", exact=True).click()
        assert event.value.status == 200 and not analyses
        inline = page.locator("#preparacao-conversacional")
        expect(inline).to_be_visible(timeout=60000)
        inline.get_by_label("Escolher períodos da análise", exact=True).click()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        execute = inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
        expect(execute).to_be_enabled(timeout=60000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=60000) as event:
            execute.click()
        assert event.value.status == 200
        density = event.value.json()
        expect(history).to_contain_text("1 análise nesta sessão")
        explanation = send("O que esse resultado significa?", "/api/llm/interpret-context")
        assert explanation["result_reference"]["result_id"] == density["result_id"]
        assert explanation["result_reference"]["origin"] == "BACKEND_VERIFIED_RESULT"
        assert explanation["segments"] and explanation["documentation"]
        simpler = send("Explique de maneira mais simples", "/api/llm/interpret-context")
        assert simpler["result_reference"]["result_id"] == density["result_id"]
        assert len(simpler["reply"]) < len(explanation["reply"]) and len(analyses) == 1
        left = page.get_by_test_id("conversation-pane").bounding_box()
        right = page.get_by_test_id("analysis-pane").bounding_box()
        assert left["x"] + left["width"] <= right["x"] + 2
        page.get_by_test_id("analysis-scroll").evaluate("el => el.scrollTop = el.scrollHeight")
        visible_composer()

        result = send("Coloque Manaus e Tefé lado a lado", "/api/llm/interpret-context")
        assert result["origin"] == "INTERPRETACAO_LLM"
        assert set(result["exploration"]["territory_ids"]) == {"code:130260", "code:130420"}
        assert len(analyses) == 1
        selection = page.get_by_role("region", name="Seleção territorial compartilhada", exact=True)
        expect(selection.get_by_text("2 selecionados", exact=True)).to_be_visible()

        partial = send("Agora vamos analisar comparativamente no município de Manaus", "/api/llm/interpret-context")
        assert partial["exploration"]["territory_ids"] == ["code:130260"]
        expect(chat.get_by_text("Com qual outro município", exact=False)).to_be_visible()
        send("TEFE e PARINTINS", "/api/exploration/interpret")
        expect(selection.get_by_text("3 selecionados", exact=True)).to_be_visible()
        send("Analise dois municípios também", "/api/exploration/interpret")
        expect(chat.get_by_text("Quais 2 municípios", exact=False)).to_be_visible()
        expect(selection.get_by_text("0 selecionados", exact=True)).to_be_visible()
        calls = len(interpretations)
        guidance = send("O que o agente é capaz de fazer?", "/api/exploration/interpret")
        assert "critérios combinados" in guidance["reply"] and len(interpretations) == calls
        assert "operation" not in guidance and len(analyses) == 1
        thanks = send("Muito obrigada pela ajuda!", "/api/exploration/interpret")
        assert "De nada" in thanks["reply"] and len(interpretations) == calls
        send("MANAUS e TEFE", "/api/exploration/interpret")
        expect(selection.get_by_text("2 selecionados", exact=True)).to_be_visible()
        contextual = send("E agora?", "/api/llm/interpret-context")
        assert contextual["context_reference"]["origin"] == "BACKEND_VERIFIED_STATE"
        # O catálogo sintético conserva os rótulos originais, sem acentos e em caixa alta.
        assert "MANAUS [130260]" in contextual["reply"] and "TEFE [130420]" in contextual["reply"], contextual
        assert len(analyses) == 1 and contextual["executed"] is False

        ambiguous = send("Analise o perfil dos municipios", "/api/llm/interpret-context")
        assert ambiguous["clarification"]["code"] == "AMBIGUIDADE_MATERIAL"
        calls = len(interpretations)
        with page.expect_response(lambda response: response.url.endswith("/api/exploration/interpret")) as event:
            # A escolha pertence à pergunta mais recente; as anteriores permanecem no histórico da conversa.
            chat.get_by_role("button", name="Quantitativos · Quantidade absoluta de profissionais", exact=True).last.click()
        assert event.value.status == 200 and len(interpretations) == calls
        assert len(analyses) == 1  # escolher a leitura prepara, nunca calcula
        expect(execute).to_be_enabled(timeout=60000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            execute.click()
        assert event.value.status == 200 and event.value.json()["metadata"]["operation"] == "counts"
        expect(history).to_contain_text("2 análises nesta sessão")
        history.locator("summary").click()
        history.get_by_role("button", name="Abrir análise: " + density["title"], exact=True).click()
        expect(page.get_by_test_id("result-title")).to_have_text(density["title"])
        assert len(analyses) == 2
        history.locator("summary").click()
        page.get_by_role("button", name="Ver resultado", exact=True).click()
        visible_composer()
        page.screenshot(path=str(OUTPUT / "conversa-paineis-semantica.png"), full_page=True)
        for width in (390, 768):
            page.set_viewport_size({"width": width, "height": 844})
            visible_composer()
        assert not errors, errors
        with page.expect_response(lambda response: response.url.endswith("/api/session/close")) as closed:
            page.get_by_test_id("end-session").click()
        assert closed.value.status == 200
        expect(page.get_by_role("button", name="Li e concordo", exact=True)).to_be_visible()
        browser.close()
    print("CONTINUIDADE SEMÂNTICA PASS: propostas, alternativas ancoradas, nomes pendentes, histórico, painéis e compositor visível.")


if __name__ == "__main__":
    main()
