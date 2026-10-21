"""D1 (19/10/2026): nenhuma confirmação de colunas e campos nas 12 análises, na base oficial (catálogo sintético do
Bloco 1) e numa base importada. O usuário só escolhe: a sugestão aparece no topo do seletor, que fica vazio até a
escolha; as antigas declarações são premissas aplicadas pelo backend, com nota no resultado.

Guarda também o conflito K1: nenhuma requisição de pré-exame ou de análise leva uma premissa com false explícito (o
backend a trataria como recusada), nem as chaves antigas require_object_confirmation e object_confirmed.
Servidor serve_ui_offline.py; nunca chama o provedor de IA. Dados sintéticos.
"""
import json
import os
import re

from playwright.sync_api import sync_playwright, expect
from ui_support import TITLES, URL, choose, execute_analysis, municipality, offline, select, workspace

FORBIDDEN = re.compile(r"Confirm|Declaro|Autorizo|confirmad")
OPTIONS = re.compile(r'name="options"\r\n\r\n(.*?)\r\n--', re.S)
UNITS = [("ALFA", "900001", 10, 1000, "-3,10", "-60,02"), ("BETA", "900002", 5, 2000, "-3,35", "-64,71"),
         ("GAMA", "900003", 7, 4000, "-2,63", "-56,74")]
CSV = ("municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;populacao;latitude;longitude\n" +
       "".join(f"{name};{code};{year};6;MEDICINA;{count + year - 2023};{population};{lat};{lon}\n"
               for year in (2023, 2024) for name, code, count, population, lat, lon in UNITS)).encode("utf-8")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        failures, sent, llm_calls = [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)

        def record(request):
            if request.method != "POST" or not request.url.endswith(("/api/analyze", "/api/preflight")):
                return
            match = OPTIONS.search(request.post_data or "")
            assert match, "requisição sem opções: " + request.url
            sent.append(json.loads(match.group(1)))
        page.on("request", record)

        def no_refused_premises():
            """K1: nenhuma chave de premissa com false explícito; nenhuma chave antiga de confirmação do objeto."""
            assert sent, "nenhuma requisição de pré-exame ou análise foi observada"
            for options in sent:
                refused = sorted(key for key, value in options.items() if key.endswith("_confirmed") and value is False)
                assert not refused, refused
                assert "require_object_confirmation" not in options and "object_confirmed" not in options, options

        inline = page.locator("#preparacao-conversacional")
        panel = page.get_by_role("region", name="Preparação da análise")

        def settled():
            expect(inline).to_be_visible(timeout=60000)
            expect(inline.get_by_test_id("scope-loading")).to_have_count(0, timeout=60000)
            for busy in ("Preparando a análise...", "Verificando as condições da análise..."):
                expect(inline.get_by_text(busy, exact=True)).to_have_count(0, timeout=60000)

        def no_confirmation_text(label):
            text = inline.text_content() or ""
            found = sorted(set(FORBIDDEN.findall(text)))
            assert not found, (label, found)

        def visit(title, official):
            """Base importada: percorre a preparação e as três etapas das condições avançadas, sem nada para confirmar.
            Base oficial: não há condições avançadas; só as escolhas da análise retêm o cálculo, nomeadas no clique."""
            print("Análise: " + title + (" (base oficial)" if official else " (base importada)"), flush=True)
            select(page, title)
            settled()
            no_confirmation_text(title)
            expect(inline.get_by_role("button", name="Confirmar correspondências")).to_have_count(0)
            if official:
                expect(inline.locator("summary", has_text="Ver outras condições da análise")).to_have_count(0)
                expect(panel).to_have_count(0)
                expect(inline.get_by_text("Ainda faltam condições específicas", exact=False)).to_have_count(0)
                if title == "Distribuição":
                    # Falta escolher o indicador: o clique em Calcular nomeia a caixa, sem pedir confirmação.
                    inline.get_by_role("button", name="Calcular e mostrar resultado", exact=True).click()
                    expect(inline.get_by_test_id("missing-choices")).to_contain_text("Indicador")
                    no_confirmation_text(title + " / calcular")
                return
            summary = inline.locator("summary", has_text="Ajustar condições específicas ou situações excepcionais")
            if not summary.evaluate("element => element.parentElement.open"):
                summary.click()
            expect(panel).to_be_visible()
            for number, name in enumerate(("1. Identificar os dados", "2. Parâmetros", "3. Revisar e executar"), start=1):
                step = panel.get_by_role("button", name=name)
                step.click()
                expect(panel.get_by_text(f"Etapa {number} de 3", exact=True)).to_be_visible()
                expect(panel.get_by_text("Atualizando as pendências…", exact=True)).to_have_count(0, timeout=60000)
                no_confirmation_text(title + " / " + name)
                if number == 1:
                    # "pend." conta só escolhas; com os campos estabelecidos, a identificação dos dados não tem pendência.
                    assert "pend." not in (step.text_content() or ""), (title, step.text_content())
            if title == "Distribuição":
                # Falta escolher o indicador: o selo diz "Escolha pendente", nunca "Confirmação necessária".
                parameters = panel.get_by_role("button", name="2. Parâmetros")
                parameters.click()
                expect(parameters).to_contain_text("pend.")
                expect(panel.get_by_test_id("requirement-choice").first).to_contain_text("Escolha pendente")
                panel.get_by_role("button", name="3. Revisar e executar").click()
                expect(panel.get_by_text("Escolha pendente", exact=True)).to_be_visible()
            summary.click()

        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        chat = page.locator("#assistente")

        # 1. Base importada: código territorial só como sugestão; escolher a coluna estabelece o papel.
        page.locator('input[type="file"]').set_input_files({"name": "importada.csv", "mimeType": "text/csv", "buffer": CSV})
        expect(chat.get_by_text("Recebi sua base", exact=False)).to_be_visible(timeout=60000)
        chat.get_by_role("button", name="Selecionar análise: Densidade", exact=True).click()
        settled()
        code = inline.get_by_test_id("field-choice-territory_id")
        expect(code).to_have_value("")  # seletor vazio: a sugestão não é seleção
        expect(code.locator("option").nth(1)).to_have_text("cod_ibge (sugerida)")
        for role, column in (("territory", "municipio"), ("period", "Período (ano e mês)"), ("latitude", "latitude")):
            field = inline.get_by_test_id("field-choice-" + role)
            if field.count():
                expect(field).to_have_value(column)  # reconhecidos por regra já vêm escolhidos
        no_confirmation_text("Densidade (antes das escolhas)")
        choose(inline, "Identificador territorial", "cod_ibge")
        inline.get_by_role("combobox", name="Unidade de contagem", exact=True).select_option("pessoas")
        inline.get_by_label("Filtrar por período", exact=True).select_option("202406")
        execute = inline.get_by_role("button", name="Executar análise", exact=True)
        expect(execute).to_be_enabled(timeout=60000)
        with page.expect_response(lambda response: response.url.endswith("/api/analyze"), timeout=60000) as event:
            execute_analysis(page, execute)
        assert event.value.status == 200, event.value.text()
        density = event.value.json()
        assert any(note.startswith("Denominador: população da mesma linha") for note in density["notes"]), density["notes"]
        assert density["metadata"]["options"]["confirmed_roles"] == ["territory_id"]
        workspace(page, "territories")
        shared = page.get_by_role("region", name="Seleção territorial compartilhada")
        for value in ("900001", "900002"):
            shared.get_by_role("searchbox").fill(value)
            expect(shared.get_by_role("checkbox")).to_have_count(1)
            with page.expect_request(lambda request: request.url.endswith("/api/preflight"), timeout=60000):
                shared.get_by_role("checkbox").check()
        workspace(page, "preparation")
        for title in TITLES:
            visit(title, official=False)
        no_refused_premises()

        # 2. Base oficial (catálogo sintético do Bloco 1): perfil campo a campo, nenhuma caixa de declaração.
        chat.get_by_text("Trocar fonte de dados", exact=True).click()
        chat.get_by_role("button", name="Usar dados do Brasil").click()
        expect(chat.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=60000)
        settled()
        for title in TITLES:
            visit(title, official=True)
        select(page, "Densidade")
        settled()
        workspace(page, "territories")
        territory = page.get_by_test_id("territory-card")
        expect(territory).to_be_visible()
        shared = page.get_by_role("region", name="Seleção territorial compartilhada")
        option = municipality(shared, "130260")  # lista vertical: o município fica no grupo do estado
        with page.expect_request(lambda request: request.url.endswith("/api/preflight"), timeout=60000):
            option.check()
        no_refused_premises()

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
        print("SEM CONFIRMAÇÕES PASS: 12 análises nas bases importada e oficial; " + str(len(sent)) +
              " requisições sem premissa recusada nem confirmação de objeto.")


if __name__ == "__main__":
    main()
