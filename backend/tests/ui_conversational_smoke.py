"""Navegação conversacional: fonte, análise, confirmações inline e resultados no chat.

Requer backend e frontend locais, Chromium/Playwright e ADT_UI_URL.
Não utiliza a API Gemini nem dados pessoais.
"""
import os

from playwright.sync_api import sync_playwright, expect
from ui_support import workspace, execute_analysis, URL, offline, select, expand, choose

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
        expect(assistant.locator("#dados")).to_be_visible()
        expect(page.locator("#analises")).to_have_count(0)
        expect(assistant.get_by_text("Olá! Conte o que deseja analisar", exact=False)).to_be_visible()
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
        # A apresentação inicial não é mais repetida no histórico visual; a conversa continua em memória.
        expect(assistant.locator("#assistant-input")).to_be_visible()

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
        # D1: o código territorial vem como sugestão no topo do seletor, que fica vazio até a escolha; escolher estabelece
        # o papel. Não há caixas "Confirmo…" nem o botão "Confirmar correspondências".
        code = inline.get_by_role("combobox", name="Identificador territorial")
        expect(code).to_have_value("")
        expect(code.locator("option").nth(1)).to_have_text("cod_ibge (sugerida)")
        choose(inline, "Identificador territorial", "cod_ibge")
        inline.get_by_role("combobox", name="Unidade de contagem").select_option("pessoas")
        assert inline.get_by_role("button", name="Confirmar correspondências").count() == 0
        assert inline.get_by_text("Confirmo", exact=False).count() == 0
        execute = inline.get_by_role("button", name="Executar análise")
        expect(execute).to_be_enabled(timeout=30000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            execute_analysis(page, execute)
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
        # Densidade só existe no recorte municipal: a caixa da abrangência territorial informa isso, sem escolha
        # que levaria a um bloqueio.
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Todos os municípios", timeout=30000)
        expand(inline.get_by_test_id("territory-toggle"))
        expect(inline.get_by_test_id("scope-info")).to_contain_text("somente a fonte municipal")
        expect(inline.get_by_role("radio", name="Brasil (total nacional)", exact=True)).to_have_count(0)
        # Quantitativos existem nas duas fontes: a escolha é explícita e a troca não volta à escolha da fonte.
        select(page, "Quantitativos")
        expect(inline.get_by_test_id("scope-summary")).to_have_text("Brasil (total nacional)", timeout=30000)
        expand(inline.get_by_test_id("territory-toggle"))
        national = inline.get_by_role("radio", name="Brasil (total nacional)", exact=True)
        municipal = inline.get_by_role("radio", name="Municípios", exact=True)
        expect(national).to_be_checked(timeout=30000)
        expect(national).to_be_enabled(timeout=30000)
        municipal.check()
        expect(municipal).to_be_checked(timeout=30000)
        expect(assistant.get_by_role("button", name="Usar dados do Brasil")).to_have_count(0)
        expect(municipal).to_be_enabled(timeout=30000)
        national.check()
        expect(national).to_be_checked(timeout=30000)
        expect(national).to_be_enabled(timeout=30000)
        # Na mesma caixa, a lista de municípios aparece também com o total nacional escolhido: marcar um município
        # leva a análise ao recorte municipal, já com ele selecionado.
        municipalities = inline.get_by_role("region", name="Seleção territorial compartilhada")
        municipalities.get_by_role("searchbox").fill("002")
        expect(municipalities.get_by_role("checkbox")).to_have_count(1, timeout=30000)
        municipalities.get_by_role("checkbox").check()
        expect(inline.get_by_test_id("scope-summary")).to_have_text("B", timeout=30000)
        expect(municipal).to_be_checked(timeout=30000)
        expect(municipal).to_be_enabled(timeout=30000)
        expect(municipalities.get_by_text("1 selecionados", exact=True)).to_be_visible()
        button = inline.get_by_role("button", name="Calcular e mostrar resultado")
        expect(button).to_be_enabled(timeout=30000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            execute_analysis(page, button)
        assert event.value.status == 200, event.value.text()
        chosen = event.value.json()
        assert chosen["metadata"]["source"]["scope"] == "municipal"
        assert chosen["metadata"]["options"]["territory_ids"] == ["code:002"]
        assert [row["Quantidade"] for row in chosen["rows"]] == [20]
        # O pedido inicial não carrega dados nem exige escolha antecipada.
        # A intenção deve sobreviver à escolha da fonte e seguir até o cálculo.
        page.reload()
        assistant = page.locator("#assistente")
        expect(assistant.locator("#dados")).to_be_visible()
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
                                           "territory":"set_in_scope"},
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
        expect(assistant.get_by_test_id("latest-reply")).to_contain_text("Entendi. Podemos fazer essa análise de quantitativos.", timeout=30000)
        expect(assistant.locator("#dados")).to_be_visible()
        assert assistant.locator("#preparacao-conversacional").count() == 0
        assistant.locator("#assistant-input").fill("certo, quantos tem?")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.get_by_test_id("latest-reply")).to_contain_text("Para continuar, escolha os dados")
        assistant.get_by_role("button", name="Usar dados do Brasil").click()
        expect(assistant.locator("#preparacao-conversacional")).to_be_visible(timeout=30000)
        assert assistant.get_by_text("A categoria mencionada não foi confirmada", exact=False).count() == 0
        inline = assistant.locator("#preparacao-conversacional")
        expect(inline).to_be_visible(timeout=30000)
        # Base oficial: configurações em caixas seletoras, sem associação de campos; o período ainda não escolhido
        # fica pendente e bloqueia o cálculo.
        expect(inline.get_by_role("heading", name="Configurações", exact=True)).to_be_visible()
        assert inline.get_by_role("combobox", name="Categoria profissional").count() == 0
        assert inline.get_by_role("combobox", name="Unidade de contagem").count() == 0
        assert inline.get_by_role("button", name="Confirmar correspondências").count() == 0
        expect(inline.get_by_test_id("period-summary")).to_have_text("Escolher período")
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_disabled()
        inline.get_by_label("Escolher períodos da análise").click()
        expect(inline.get_by_text("Qual período você deseja analisar?")).to_be_visible()
        inline.get_by_role("button", name="junho de 2024", exact=True).click()
        expect(inline.get_by_test_id("analysis-summary")).to_contain_text("MEDICINA")
        expect(inline.get_by_test_id("period-summary")).to_have_text("junho de 2024")
        expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_enabled(timeout=30000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            execute_analysis(page, inline.get_by_role("button", name="Calcular e mostrar resultado"))
        assert event.value.status == 200, event.value.text()
        expect(assistant.locator("#resultados .data-table tbody tr")).to_have_count(1, timeout=30000)
        expect(assistant.get_by_test_id("result-highlights")).to_contain_text("junho de 2024")
        # A seleção cumulativa mostra competências separadas, sem somar pessoas
        # de períodos diferentes em um único quantitativo.
        workspace(page, "preparation")
        inline.get_by_label("Escolher períodos da análise").click()
        inline.get_by_role("button", name="Selecionar vários períodos").click()
        inline.get_by_role("button", name="Todos os períodos disponíveis", exact=True).click()
        inline.get_by_test_id("period-done").click()
        try:
            expect(inline.get_by_role("button", name="Calcular e mostrar resultado")).to_be_enabled(timeout=30000)
        except AssertionError:
            print("MULTIPERIOD-UI-DIAGNOSTIC:", inline.inner_text()[:2000], flush=True)
            raise
        with page.expect_response(lambda response: response.url.endswith("/api/analyze")) as event:
            execute_analysis(page, inline.get_by_role("button", name="Calcular e mostrar resultado"))
        assert event.value.status == 200, event.value.text()
        expect(assistant.locator("#resultados .data-table tbody tr")).to_have_count(2)
        # A descrição da base é acessível sem escolher uma fonte.
        page.reload()
        assistant = page.locator("#assistente")
        assistant.locator("#assistant-input").fill("O que tem nos dados do Brasil?")
        assistant.get_by_role("button", name="Enviar mensagem").click()
        expect(assistant.get_by_test_id("latest-reply")).to_contain_text("junho de 2023", timeout=30000)
        expect(assistant.locator("#dados")).to_be_visible()
        context.close()
        browser.close()
    print("CONVERSATIONAL UI PASS: greeting, deferred source selection, resumed intent, inline edits, dual Brazil sources, export.")


if __name__ == "__main__":
    main()
