"""Selecionar por critérios (07/11/2026, item 6 do comando de 06/11/2026; decisão 4 do responsável), com a base versionada.

Confere o aceite do comando na Seleção de Territórios, contra as respostas de /api/painel/criterios e /api/painel:
- a ferramenta "Selecionar por critérios" ao lado de Buscar e Agregar territórios; o painel começa sem valores (nada é sugerido);
- no todo, densidade abaixo de 0,5 em jun/2024: 89 municípios atendem (a prévia do motor, antes de mudar a análise);
- "Agrupar os que ficam a até 200 km uns dos outros": 6 grupos e 8 isolados; o maior com 46 municípios (PI 33, TO 11, MA 1 e BA
  1) e 1.235 km de ponta a ponta; o segundo, 24 do PA e 907 km; o mapa pequeno com os 89 pontos, 81 coloridos e 8 vazados;
- "Como seleção (89)": a trilha "Brasil › Seleção: densidade abaixo de 0,5 em jun/2024 (89)", a regra na Seleção e nos Detalhes,
  e a Distribuição com os 89;
- "Cada grupo como território agregado": 6 grupos e 8 municípios na análise;
- pela conversa (item 6.9), o pedido do comando abre o mesmo painel preenchido, com a prévia, e nada muda na análise até a
  confirmação no painel;
- nenhum texto à vista com "cluster".

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, options_of, send

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "este roteiro usa a base Brasil versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        offline(context)
        page = context.new_page()
        falhas, chamadas_llm = [], []
        page.on("pageerror", lambda error: falhas.append(str(error)))
        page.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        partes = area.get_by_test_id("analise-trilha").get_by_test_id("analise-trilha-parte")

        def aperta(locator):
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Enter")

        def marcado(locator):
            """Marca a caixa pelo teclado, só se ainda não estiver marcada."""
            locator.scroll_into_view_if_needed()
            if not locator.is_checked():
                locator.focus()
                locator.press("Space")
            expect(locator).to_be_checked()

        def previa(acao, timeout=180000):
            """A resposta de /api/painel/criterios do pedido feito pela ação."""
            with page.expect_response(lambda r: r.url.endswith("/api/painel/criterios") and r.request.method == "POST",
                                      timeout=timeout) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        # A caixa da conversa, minimizada (a conversa do passo 6 a abre de novo).
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. A ferramenta na Seleção, ao lado de Buscar e Agregar; o painel começa sem valores.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true", timeout=180000)
        ferramentas = territorios.get_by_test_id("analise-selecao-ferramentas")
        expect(ferramentas.get_by_role("button")).to_have_text(["Buscar", "Agregar territórios", "Selecionar por critérios"])
        aperta(ferramentas.get_by_test_id("analise-criterios-abrir"))
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel).to_be_visible()
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("")
        expect(painel.get_by_test_id("analise-criterios-previa")).to_be_disabled()
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()

        # 2. No todo, densidade abaixo de 0,5 em jun/2024: 89.
        expect(painel.get_by_test_id("analise-criterios-competencia")).to_have_value("202406")
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        painel.get_by_test_id("analise-criterio-valor").fill("0,5")
        corpo, pedido = previa(lambda: aperta(painel.get_by_test_id("analise-criterios-previa")))
        assert pedido["criterios"] == {"partir_de": {"tipo": "pais"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 0.5}]}, pedido
        assert corpo["atendem"] == 89 and corpo["regra"]["texto"] == "densidade abaixo de 0,5", corpo["regra"]
        expect(painel.get_by_test_id("analise-criterios-atendem")).to_contain_text(
            "89 municípios atendem aos critérios (densidade abaixo de 0,5 em jun/2024)")
        expect(painel.get_by_test_id("analise-criterios-como-selecao")).to_have_text("Como seleção (89)")
        expect(painel.get_by_test_id("analise-criterios-como-grupos")).to_have_count(0)
        # A prévia não muda a análise: nada foi selecionado ainda.
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")

        # 3. Agrupar a até 200 km: 6 grupos e 8 isolados; o maior com 46 (PI 33, TO 11, MA 1, BA 1) e 1.235 km; o segundo, 24 do
        # PA e 907 km; o mapa pequeno com os 89 pontos (81 coloridos, 8 vazados).
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        painel.get_by_test_id("analise-criterios-agrupar-km").fill("200")
        corpo, pedido = previa(lambda: aperta(painel.get_by_test_id("analise-criterios-previa")))
        assert pedido["agrupar"] == {"km": 200}, pedido
        assert (len(corpo["grupos"]), len(corpo["isolados"])) == (6, 8), (len(corpo["grupos"]), len(corpo["isolados"]))
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_have_text("6 grupos e 8 isolados.")
        grupos = painel.get_by_test_id("analise-criterios-grupo")
        expect(grupos).to_have_count(6)
        expect(grupos.nth(0)).to_contain_text("Grupo 1 · 46 municípios")
        for texto in ("PI 33", "TO 11", "MA 1", "BA 1", "1.235 km de ponta a ponta"):
            expect(grupos.nth(0)).to_contain_text(texto)
        expect(grupos.nth(1)).to_contain_text("Grupo 2 · 24 municípios · PA 24 · 907 km de ponta a ponta")
        pontos = painel.get_by_test_id("analise-criterios-mapa").get_by_test_id("analise-criterios-ponto")
        expect(pontos).to_have_count(89)
        expect(painel.locator('[data-testid="analise-criterios-ponto"][data-grupo=""]')).to_have_count(8)

        # 4. "Como seleção (89)": a trilha com a regra (sem o agrupamento), a regra na Seleção, a Distribuição com os 89 e a regra
        # nos Detalhes.
        # A análise é pedida assim que a seleção muda, ainda na Seleção: a resposta é a do clique.
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000) as evento:
            aperta(painel.get_by_test_id("analise-criterios-como-selecao"))
        assert evento.value.status == 200, evento.value.text()[:2000]
        resposta = evento.value.json()
        na_analise = {item["id"] for item in resposta["itens"] if item["tipo"] == "municipio"}
        assert na_analise == set(corpo["ids"]) and len(na_analise) == 89, len(na_analise)
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])
        expect(territorios.get_by_test_id("analise-selecao-regra")).to_contain_text(
            "Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (89)")
        expect(territorios.get_by_test_id("analise-criterios-reaplicar")).to_be_visible()
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])
        expect(area.get_by_test_id("analise-detalhes-regra")).to_contain_text(
            "Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (89)", timeout=60000)
        page.screenshot(path=str(OUTPUT / "criterios-como-selecao-real.png"), full_page=True)

        # 5. "Cada grupo como território agregado": 6 grupos e 8 municípios na análise.
        aperta(area.get_by_test_id("analise-aba-territorios"))
        aperta(territorios.get_by_test_id("analise-criterios-reaplicar"))
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("0,5")
        # Onde a regra procurou continua o mesmo (o todo), embora a seleção em uso já seja a do resultado.
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()
        expect(painel.locator("label", has=painel.get_by_test_id("analise-criterios-onde-selecao"))).to_have_text("A seleção atual")
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        painel.get_by_test_id("analise-criterios-agrupar-km").fill("200")
        previa(lambda: aperta(painel.get_by_test_id("analise-criterios-previa")))
        aperta(painel.get_by_test_id("analise-criterios-como-grupos"))
        expect(territorios.get_by_test_id("analise-selecionado-conjunto")).to_have_count(6)
        expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_contain_text("8 municípios")
        expect(territorios.get_by_test_id("analise-selecionado-conjunto").first).to_contain_text("Grupo 1 · grupo · 46 municípios")
        expect(partes.nth(1)).to_have_text(re.compile(r"^Seleção: densidade abaixo de 0,5, agrupados a até 200 km uns dos outros"))

        # 6. Pela conversa (item 6.9): o pedido do comando abre o mesmo painel preenchido, com a prévia do motor; nada muda na
        # análise até a confirmação no painel.
        chat = page.get_by_test_id("painel-chat")
        antes = area.get_by_test_id("analise-aba-territorios-resumo").inner_text()
        corpo, pedido = previa(lambda: send(page, "municípios com menos de 0,5 médico por mil habitantes a até 200 km uns dos outros"))
        assert pedido["criterios"] == {"partir_de": {"tipo": "pais"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 0.5}]}, pedido
        assert pedido["agrupar"] == {"km": 200} and corpo["atendem"] == 89 and len(corpo["grupos"]) == 6, pedido
        expect(chat.get_by_test_id("latest-reply")).to_contain_text(
            "Abri Selecionar por critérios, na Seleção, com densidade abaixo de 0,5 em todo o país, agrupando os que ficam a até "
            "200 km uns dos outros.", timeout=60000)
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true")
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("0,5")
        expect(painel.get_by_test_id("analise-criterios-agrupar")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-agrupar-km")).to_have_value("200")
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_have_text("6 grupos e 8 isolados.")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(antes)
        expect(chat.locator('[data-papel="agente"]').last).to_have_attribute("data-execucao", "concluido", timeout=60000)
        aperta(painel.get_by_test_id("analise-criterios-como-selecao"))
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])

        # 7. Nenhum "cluster" à vista.
        assert "cluster" not in page.evaluate("() => document.body.innerText").lower()
        page.screenshot(path=str(OUTPUT / "criterios-grupos-real.png"), full_page=True)
        assert not falhas, falhas
        assert not chamadas_llm, chamadas_llm
        browser.close()
    print("CRITÉRIOS PASS: Selecionar por critérios na Seleção (sem valores sugeridos), densidade abaixo de 0,5 em jun/2024 (89), "
          "6 grupos e 8 isolados a até 200 km (46 municípios e 1.235 km; 24 do PA e 907 km), o mapa pequeno, \"Como seleção (89)\" com "
          "a trilha, a regra e os Detalhes, e \"Cada grupo como território agregado\" (6 grupos e 8 municípios), o pedido pela conversa com o painel "
          "preenchido e a prévia, sem mudar a análise até a confirmação; nenhum \"cluster\" (base versionada).")


if __name__ == "__main__":
    main()
