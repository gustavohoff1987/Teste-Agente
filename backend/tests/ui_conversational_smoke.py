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
        assert assistant.locator("#dados").count() == 0
        expect(page.locator("#analises")).to_have_count(0)
        expect(assistant.get_by_text("Olá! Sou o Agente Diagnóstico Territorial.")).to_be_visible()
        assistant.locator("#assistant-input").fill("Olá")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.locator("#dados")).to_be_visible()
        assert page.locator("#preparacao").count() == 0

        # Perguntas antes da escolha da fonte recebem conteúdo, sem repetir a apresentação.
        for question, fragment in (
            ("O que é possível fazer nessa página?", "critérios combinados"),
            ("O que o agente é capaz de fazer?", "mapas quando há localização disponível"),
            ("Como se calcula a densidade?", "D(u, p, c) = Q(u, p, c) / P(u, p′)"),
            ("Muito obrigada pela ajuda!", "De nada!"),
        ):
            assistant.locator("#assistant-input").fill(question)
            with page.expect_response(lambda response: response.url.endswith("/api/llm/interpret")) as response:
                assistant.get_by_role("button", name="Enviar mensagem", exact=True).click()
            assert response.value.status == 200
            expect(assistant.get_by_text(fragment, exact=False).last).to_be_visible()
            expect(assistant.locator("#preparacao-conversacional")).to_have_count(0)
        expect(assistant.get_by_text("Olá! Para começar, prefere usar os dados do Brasil", exact=False)).to_have_count(1)

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
        expect(result.get_by_role("navigation", name="Histórico de resultados")).to_have_count(0)
        for removed in ("Período AAAAMM composto em memória", "Identificação territorial:",
                        "Registrar correção que invalida este resultado"):
            expect(result.get_by_text(removed, exact=False)).to_have_count(0)
        with page.expect_download() as download:
            result.get_by_role("button", name="CSV", exact=True).click()
        assert download.value.suggested_filename.endswith(".csv")

        # O catálogo brasileiro disponibiliza as duas fontes na mesma sessão,
        # mantendo seleção explícita de abrangência e sem concatenar registros.
        page.reload()
        assistant = page.locator("#assistente")
        assistant.locator("#assistant-input").fill("Olá")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.locator("#dados")).to_be_visible()
        assistant.get_by_role("button", name="Usar dados do Brasil").click()
        expect(assistant.get_by_text("Os dados do Brasil já estão disponíveis.", exact=False)).to_be_visible(timeout=30000)
        assistant.get_by_role("button", name="Selecionar análise: Densidade").click()
        inline = assistant.locator("#preparacao-conversacional")
        inline.get_by_text("Alterar a abrangência territorial").click()
        scope = inline.get_by_role("combobox", name="Abrangência territorial")
        expect(scope).to_have_value("municipal")
        scope.select_option("national")
        inline = assistant.locator("#preparacao-conversacional")
        inline.get_by_text("Alterar a abrangência territorial").click()
        expect(inline.get_by_role("combobox", name="Abrangência territorial")).to_have_value("national", timeout=30000)
        scope = inline.get_by_role("combobox", name="Abrangência territorial")
        scope.select_option("municipal")
        inline = assistant.locator("#preparacao-conversacional")
        inline.get_by_text("Alterar a abrangência territorial").click()
        expect(inline.get_by_role("combobox", name="Abrangência territorial")).to_have_value("municipal", timeout=30000)
        # O pedido inicial não carrega dados nem exige escolha antecipada.
        # A intenção deve sobreviver à escolha da fonte e seguir até o cálculo.
        page.reload()
        assistant = page.locator("#assistente")
        expect(assistant.locator("#dados")).to_have_count(0)
        def mock_interpret(route):
            route.fulfill(status=200, content_type="application/json", body=__import__("json").dumps({
                "origin": "INTERPRETACAO_LLM", "executed": False,
                "requires_confirmation": True, "model": "mock", "privacy": "teste",
                "note": "", "reply": "A categoria mencionada não foi confirmada na base. Confira seu nome.",
                "proposal": {"operation": "counts", "indicator": "quantity",
                             "period": "", "category": "médicos", "territory": "Brasil"},
                "verification": {"source": "BACKEND_PREFLIGHT",
                                 "capability_status": "unavailable",
                                 "slots": {"period":"not_requested",
                                           "category":"not_confirmed_in_dataset",
                                           "territory":"requires_unit_confirmation"},
                                 "blockers": ["A categoria mencionada não foi confirmada."],
                                 "ready_to_execute": False, "next_action": "confirm_in_interface"},
                "clarification": {"code": "CATEGORIA_NAO_CONFIRMADA",
                                  "prompt": "A categoria mencionada não foi confirmada na base.",
                                  "reason": "Correspondência não reconhecida",
                                  "source": "CATALOGO_LOCAL",
                                  "choices": [], "answered": False}
            }, ensure_ascii=False))
        page.route("**/api/llm/interpret", mock_interpret)
        assistant.locator("#assistant-input").fill("Quero saber quantos médicos existem no Brasil")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.get_by_text("Entendi. Podemos fazer essa análise de quantitativos.", exact=False)).to_be_visible(timeout=30000)
        expect(assistant.locator("#dados")).to_be_visible()
        assert assistant.locator("#preparacao-conversacional").count() == 0
        assistant.locator("#assistant-input").fill("certo, quantos tem?")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.get_by_text("Para continuar, escolha os dados", exact=False)).to_be_visible()
        assistant.get_by_role("button", name="Usar dados do Brasil").click()
        expect(assistant.locator("#preparacao-conversacional")).to_be_visible(timeout=30000)
        assert assistant.get_by_text("A categoria mencionada não foi confirmada", exact=False).count() == 0
        inline = assistant.locator("#preparacao-conversacional")
        expect(inline).to_be_visible(timeout=30000)
        expect(inline.get_by_text("categoria MEDICINA", exact=False)).to_be_visible()
        assert inline.get_by_role("combobox", name="Categoria profissional").count() == 0
        assert inline.get_by_role("combobox", name="Unidade de contagem").count() == 0
        assert inline.get_by_role("button", name="Confirmar correspondências").count() == 0
        expect(inline.get_by_text("Qual período você deseja analisar?")).to_be_visible()
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_disabled()
        inline.get_by_label("Escolher períodos da análise").click()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_enabled(timeout=30000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            inline.get_by_role("button", name="Calcular e mostrar resultado").click()
        assert event.value.status == 200, event.value.text()
        assert assistant.locator("#resultados .data-table tbody tr").count() == 1
        # A seleção cumulativa mostra competências separadas, sem somar pessoas
        # de períodos diferentes em um único quantitativo.
        inline.get_by_role("button", name="Selecionar vários períodos").click()
        try:
            expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_enabled(timeout=30000)
        except AssertionError:
            print("MULTIPERIOD-UI-DIAGNOSTIC:", inline.inner_text()[:2000], flush=True)
            raise
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            inline.get_by_role("button", name="Calcular e mostrar resultado").click()
        assert event.value.status == 200, event.value.text()
        expect(assistant.locator("#resultados .data-table tbody tr")).to_have_count(2)
        # A descrição da base é acessível sem escolher uma fonte.
        page.reload()
        assistant = page.locator("#assistente")
        assistant.locator("#assistant-input").fill("O que tem nos dados do Brasil?")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.get_by_text("junho de 2023", exact=False)).to_be_visible(timeout=30000)
        expect(assistant.locator("#dados")).to_be_visible()
        context.close()
        browser.close()
    print("CONVERSATIONAL UI PASS: greeting, deferred source selection, resumed intent, inline edits, dual Brazil sources, export.")


if __name__ == "__main__":
    main()
