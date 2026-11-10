"""Seleção por critérios e agrupamento de ponta a ponta, com a base versionada. Desde o comando V22 (9/11/2026, seções 2 a 5),
os critérios e o agrupamento são ações do painel direito da Seleção ("Aplicar critérios de seleção" e "Agrupar territórios
selecionados"), com a árvore sempre à vista; antes (comando de 07/11/2026), eram modos da coluna da esquerda, e o agrupamento por
proximidade era o passo 3 dos critérios.

Confere, contra as respostas de /api/painel/criterios e /api/painel, o que os comandos pedem na tela:
- sem as abas de modo; a árvore Brasil › região › estado › município com as regiões recolhidas (Norte, Nordeste, Centro-Oeste,
  Sudeste, Sul) e as três ações à direita; "Aplicar critérios de seleção" abre no painel direito, sem valores (nada é sugerido),
  procurando no país todo, com as competências em ordem de data e sem o passo de agrupar;
- a prévia sozinha, a cada ajuste: no todo, densidade abaixo de 0,5 em jun/2024 → 89; com o valor incompleto ("0,"), a linha de
  estado diz o que falta e o mini mapa fica esmaecido; trocar 0,5 por 0,7 pede a prévia de novo, sem clicar;
- "Usar como seleção (89)": a trilha "Brasil › Seleção: densidade abaixo de 0,5 em jun/2024 (89)", a regra e os Detalhes;
- "Usar como seleção" nas Condições abre os critérios nos marcados, com a prévia;
- "Agrupar territórios selecionados", por proximidade (a até 200 km entre si): só os selecionados entram, nenhum conjunto passa de
  200 km, cada um com o contorno no mini mapa, e os sem conjunto continuam selecionados individualmente (a pergunta sobre levá-los
  saiu); no Pará (densidade abaixo de 0,5), a até 100 km, os conjuntos da referência do comando de 07/11/2026 (Igarapé-Miri,
  Limoeiro do Ajuru, Moju e Muaná; Bagre, Curralinho e Oeiras do Pará; Acará e Concórdia do Pará);
- junto com a seleção atual, os municípios que já estão num conjunto ficam de fora, e a tela diz quantos e por quê;
- agrupar só pela distância (o Pará inteiro, a até 50 km);
- pela conversa, o pedido do comando abre os critérios preenchidos, com a prévia; nada muda até "Usar como seleção", e então o
  agrupamento por proximidade abre com a distância pedida;
- as regiões recolhidas na árvore (abrir não marca; marcar o Norte marca os 7 estados, sem aviso coletivo); com o Pará na trilha,
  os critérios abrem no país todo, com "Os marcados na lista (144)";
- "Só o estado" (decisão 3): o Pará como uma bolha, com a fonte estadual, e os municípios dele bloqueados; com municípios do
  Amazonas, a seleção mista (estados_unidade) e a trilha "Brasil › Seleção"; "Só os estados" do Norte;
- por escolha livre, só com os selecionados: o mini mapa que escolhe (o ponto entra e sai, e o contorno e a extensão mudam),
  "Conjunto A", o nome editado pelo ✎ no mapa da seleção, o nome repetido recusado e o contorno tracejado com o nome no mapa da
  análise;
- o exemplo do objetivo: o Norte com densidade abaixo de 0,5, agrupado a até 100 km, na Análise Espacial: a base com "N conjuntos e M
  territórios individuais" e a Referência com densidade a partir de 1, cada conjunto com a menor e a maior distância e a referência
  do membro mais próximo, também nos Detalhes;
- os conjuntos nas comparações (comando de 08/11/2026): os cortes dos quintis não mudam com um conjunto que não fica no lugar dos
  membros; a ordem por densidade, a condição "densidade abaixo de 0,4" e, na Análise Espacial, as faixas 0; 100; 300 e a ordem
  pela distância, com os conjuntos pelo valor de cada um;
- nenhum texto à vista com "cluster".

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, abrir_regiao, linha_do_estado, offline, options_of, send

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
PARA, AMAZONAS = "15", "13"
CODIGOS = lambda *codigos: sorted("code:" + codigo for codigo in codigos)  # noqa: E731
CONJUNTOS_DO_COMANDO = [CODIGOS("150330", "150400", "150470", "150490"), CODIGOS("150110", "150280", "150520"), CODIGOS("150020", "150275")]


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
        direita = territorios.get_by_test_id("analise-selecionados")
        partes = area.get_by_test_id("analise-trilha").get_by_test_id("analise-trilha-parte")

        def aperta(locator):
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Enter")

        def marcado(locator):
            """Marca a caixa (ou o botão de opção) pelo teclado, só se ainda não estiver marcada."""
            locator.scroll_into_view_if_needed()
            if not locator.is_checked():
                locator.focus()
                locator.press("Space")
            expect(locator).to_be_checked()

        def desmarcado(locator):
            """Desmarca a caixa pelo teclado, só se estiver marcada."""
            locator.scroll_into_view_if_needed()
            if locator.is_checked():
                locator.focus()
                locator.press("Space")
            expect(locator).not_to_be_checked()

        def previa(acao, condicao=None, timeout=180000):
            """A resposta de /api/painel/criterios que a ação provocou (a prévia sai sozinha, a cada ajuste)."""
            with page.expect_response(lambda r: r.url.endswith("/api/painel/criterios") and r.request.method == "POST" and (
                    condicao is None or condicao(options_of(r.request))), timeout=timeout) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        def analise(acao, condicao=None):
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST" and (
                    condicao is None or condicao(options_of(r.request))), timeout=180000) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        def criterios():
            """"Aplicar critérios de seleção", no painel direito; a árvore continua à vista."""
            aperta(direita.get_by_test_id("analise-aplicar-criterios"))
            painel = territorios.get_by_test_id("analise-criterios")
            expect(painel).to_be_visible()
            expect(territorios.get_by_test_id("analise-arvore")).to_be_visible()
            return painel

        def agrupar(modo="livre"):
            """"Agrupar territórios selecionados", na modalidade pedida."""
            aperta(direita.get_by_test_id("analise-agrupar-selecionados"))
            janela = territorios.get_by_test_id("analise-agrupamento")
            expect(janela).to_be_visible()
            if janela.get_attribute("data-modo") != modo:
                aperta(janela.get_by_test_id("analise-agrupar-" + modo))
            expect(janela).to_have_attribute("data-modo", modo)
            return janela

        def limpar():
            aperta(area.get_by_test_id("analise-limpar-selecao"))
            expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")

        # A caixa da conversa, minimizada (a conversa do passo 8 a abre de novo).
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. Sem as abas de modo: a árvore e as três ações; os critérios abrem no painel direito, sem valores, no país todo, com as
        #    competências em ordem de data e sem o passo de agrupar.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true", timeout=180000)
        expect(territorios.get_by_test_id("analise-selecao-modos")).to_have_count(0)
        regioes = territorios.get_by_test_id("analise-regioes").get_by_test_id("analise-regiao")
        expect(regioes).to_have_count(5)
        expect(regioes.locator(":scope > .analise-no-linha .analise-no-nome")).to_have_text(["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"])
        expect(territorios.get_by_test_id("analise-raiz-universo")).to_have_text("5.570 municípios | 27 UFs")
        expect(direita.get_by_test_id("analise-confirmar-selecao")).to_be_disabled()
        expect(direita.get_by_test_id("analise-agrupar-selecionados")).to_be_disabled()
        painel = criterios()
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("")
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-agrupar")).to_have_count(0)
        expect(page.get_by_test_id("analise-criterios-previa")).to_have_count(0)
        expect(painel.get_by_test_id("analise-criterios-estado")).to_have_text("Falta o valor do critério 1.")
        competencias = painel.get_by_test_id("analise-criterios-competencia").locator("option").evaluate_all(
            "opcoes => opcoes.map(o => o.value)")
        assert competencias == sorted(competencias) and len(competencias) == 22, competencias
        assert competencias.index("201801") < competencias.index("201806") < competencias.index("201901"), competencias
        assert competencias[-5:] == ["202206", "202301", "202306", "202401", "202406"], competencias

        # 2. A prévia sozinha: no todo, densidade abaixo de 0,5 em jun/2024 → 89.
        expect(painel.get_by_test_id("analise-criterios-competencia")).to_have_value("202406")
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"))
        assert pedido["criterios"] == {"partir_de": {"tipo": "pais"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 0.5}]}, pedido
        assert "agrupar" not in pedido, pedido
        assert corpo["atendem"] == 89 and corpo["regra"]["texto"] == "densidade abaixo de 0,5", corpo["regra"]
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_have_text("89 atendem")
        expect(painel.get_by_test_id("analise-criterios-estado")).to_contain_text(
            "89 municípios atendem aos critérios (densidade abaixo de 0,5 em jun/2024)")
        expect(painel.get_by_test_id("analise-criterios-como-selecao")).to_have_text("Usar como seleção (89)")
        expect(painel.get_by_test_id("analise-criterios-como-grupos")).to_have_count(0)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        # O valor incompleto: a linha de estado diz o que falta, e o mini mapa mantém o último resultado, esmaecido.
        painel.get_by_test_id("analise-criterio-valor").fill("0,")
        expect(painel.get_by_test_id("analise-criterios-estado")).to_have_text("Falta o valor do critério 1.")
        expect(painel.get_by_test_id("analise-mapa-conjuntos")).to_have_attribute("data-esmaecido", "true")
        previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"))

        # 3. Trocar 0,5 por 0,7 pede a prévia de novo, sem clicar.
        corpo07, _ = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,7"),
                            condicao=lambda o: (o["criterios"]["filtros"] or [{}])[0].get("valor") == 0.7)
        assert corpo07["atendem"] > 89, corpo07["atendem"]
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text(str(corpo07["atendem"]) + " atendem")
        previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"),
               condicao=lambda o: (o["criterios"]["filtros"] or [{}])[0].get("valor") == 0.5)
        page.screenshot(path=str(OUTPUT / "criterios-mini-mapa-real.png"), full_page=True)

        # 4. "Usar como seleção (89)": a trilha com a regra, a regra na Seleção e nos Detalhes; o painel direito volta à lista.
        expect(painel.get_by_test_id("analise-criterios-como-selecao")).to_have_text("Usar como seleção (89)", timeout=60000)
        resposta, _ = analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-selecao")))
        na_analise = {item["id"] for item in resposta["itens"] if item["tipo"] == "municipio"}
        assert len(na_analise) == 89, len(na_analise)
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)
        expect(direita.get_by_test_id("analise-mapa-selecao")).to_be_visible()
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])
        expect(territorios.get_by_test_id("analise-selecao-regra")).to_contain_text(
            "Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (89)")
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area.get_by_test_id("analise-detalhes-regra")).to_contain_text(
            "Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (89)", timeout=60000)

        # 5. "Usar como seleção" nas Condições: abre os critérios nos marcados, com a prévia; Cancelar volta à lista.
        aperta(area.get_by_test_id("analise-funcao-condicoes"))
        condicoes = area.get_by_test_id("analise-condicoes")
        condicoes.get_by_test_id("analise-condicao-atributo").select_option("densidade")
        condicoes.get_by_test_id("analise-condicao-operador").select_option("<")
        condicoes.get_by_test_id("analise-condicao-valor").fill("1")
        aperta(condicoes.get_by_test_id("analise-condicoes-aplicar"))
        corpo_condicoes, pedido = previa(lambda: aperta(condicoes.get_by_test_id("analise-condicoes-usar-como-selecao")))
        assert pedido["criterios"] == {"partir_de": {"tipo": "selecao"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 1}]}, pedido
        assert len(pedido["base"]["municipios"]["ids"]) == 89 and corpo_condicoes["atendem"] == 89, pedido.get("base")
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true")
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterios-onde-marcados")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("1")
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])

        # 6. "Reaplicar em outra competência" reabre a regra; depois, agrupar por proximidade os 89 selecionados, a até 200 km entre si:
        #    só eles entram, nenhum conjunto passa de 200 km, e os sem conjunto continuam selecionados, cada um individualmente.
        aperta(territorios.get_by_test_id("analise-criterios-reaplicar"))
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("0,5")
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        janela = agrupar("proximidade")
        expect(janela.get_by_test_id("analise-agrupar-km")).to_have_value("")
        corpo, pedido = previa(lambda: janela.get_by_test_id("analise-agrupar-km").fill("200"),
                               condicao=lambda o: (o.get("agrupar") or {}).get("km") == 200)
        assert pedido["criterios"] == {"partir_de": {"tipo": "selecao"}, "filtros": []}, pedido
        assert len(pedido["base"]["municipios"]["ids"]) == 89, pedido["base"]
        grupos = corpo["grupos"]
        assert grupos and all(grupo["extensao_km"] <= 200 for grupo in grupos), [grupo["extensao_km"] for grupo in grupos]
        assert {key for grupo in grupos for key in grupo["membros"]} <= na_analise, "só os selecionados entram nos conjuntos"
        expect(janela.get_by_test_id("analise-mapa-contorno")).to_have_count(len(grupos))
        expect(janela.get_by_test_id("analise-agrupar-conjunto")).to_have_count(len(grupos))
        expect(janela.get_by_test_id("analise-agrupar-conjunto-nome").first).to_have_value("Conjunto A")
        expect(janela.get_by_test_id("analise-agrupar-estado")).to_contain_text("sem conjunto (continu")
        expect(territorios.get_by_test_id("analise-criterios-sem-conjunto")).to_have_count(0)
        membros = sum(len(grupo["membros"]) for grupo in grupos)
        resposta, enviado = analise(lambda: aperta(janela.get_by_test_id("analise-agrupar-usar")),
                                    condicao=lambda o: len(o.get("conjuntos") or []) == len(grupos))
        n_conjuntos = len(grupos)
        assert [c["rotulo"] for c in enviado["conjuntos"]][:2] == ["Conjunto A", "Conjunto B"][:n_conjuntos], enviado["conjuntos"][:2]
        assert sum(item["tipo"] == "municipio" for item in resposta["itens"]) == 89 - membros, "os sem conjunto continuam individuais"
        expect(direita.get_by_test_id("analise-selecionado-conjunto")).to_have_count(n_conjuntos)
        expect(direita.get_by_test_id("analise-selecionado-conjunto").first).to_contain_text("Conjunto A · conjunto ·")
        expect(partes).to_have_text(["Brasil", "Seleção"])

        # 7. O Pará com densidade abaixo de 0,5, no lugar da seleção atual (os conjuntos de antes saem, com o aviso no rodapé), e o
        #    agrupamento a até 100 km: os conjuntos da referência do comando de 07/11/2026, com as letras recomeçando em A. Junto com a
        #    seleção atual, os municípios que já estão num conjunto ficam de fora, com quantos e por quê. Depois, só pela distância: o
        #    Pará inteiro a até 50 km.
        painel = criterios()
        marcado(painel.get_by_test_id("analise-criterios-onde-estados"))
        marcado(painel.locator('[data-testid="analise-criterios-onde-estado"][data-id="' + PARA + '"]'))
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"),
                               condicao=lambda o: o["criterios"]["partir_de"] == {"tipo": "ufs", "ufs": [PARA]})
        expect(painel.get_by_test_id("analise-criterios-no-lugar")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-uso-texto")).to_contain_text("saem também " + str(n_conjuntos) + " conjunto")
        do_para = set(corpo["ids"])
        analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-selecao")),
                condicao=lambda o: not o.get("conjuntos"))
        janela = agrupar("proximidade")
        corpo, pedido = previa(lambda: janela.get_by_test_id("analise-agrupar-km").fill("100"),
                               condicao=lambda o: (o.get("agrupar") or {}).get("km") == 100)
        assert set(pedido["base"]["municipios"]["ids"]) == do_para, pedido["base"]
        do_para_grupos = [sorted(grupo["membros"]) for grupo in corpo["grupos"]]
        for esperado in CONJUNTOS_DO_COMANDO:
            assert esperado in do_para_grupos, (esperado, do_para_grupos)
        _, enviado = analise(lambda: aperta(janela.get_by_test_id("analise-agrupar-usar")),
                             condicao=lambda o: len(o.get("conjuntos") or []) == len(corpo["grupos"]))
        nomes = [c["rotulo"] for c in enviado["conjuntos"]]
        assert nomes[0] == "Conjunto A" and len(set(nomes)) == len(nomes), nomes
        membros_do_para = {key for grupo in corpo["grupos"] for key in grupo["membros"]}
        painel = criterios()
        marcado(painel.get_by_test_id("analise-criterios-onde-estados"))
        marcado(painel.locator('[data-testid="analise-criterios-onde-estado"][data-id="' + PARA + '"]'))
        corpo07, _ = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,7"),
                            condicao=lambda o: (o["criterios"]["filtros"] or [{}])[0].get("valor") == 0.7)
        marcado(painel.get_by_test_id("analise-criterios-junto"))
        fora = len(set(corpo07["ids"]) & membros_do_para)
        assert fora, "o resultado junto inclui municípios que já estão num conjunto"
        expect(painel.get_by_test_id("analise-criterios-uso-texto")).to_contain_text(
            "Ficam de fora " + str(fora) + (" município que já está" if fora == 1 else " municípios que já estão") + " num conjunto da seleção")
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        limpar()
        linha_pa = linha_do_estado(territorios, PARA)
        analise(lambda: marcado(linha_pa.get_by_test_id("analise-grupo-todos")))
        janela = agrupar("proximidade")
        corpo, pedido = previa(lambda: janela.get_by_test_id("analise-agrupar-km").fill("50"),
                               condicao=lambda o: (o.get("agrupar") or {}).get("km") == 50 and not o["criterios"]["filtros"])
        assert corpo["atendem"] == 144 and corpo["grupos"], (corpo["atendem"], len(corpo["grupos"] or []))
        expect(janela.get_by_test_id("analise-mapa-contorno")).to_have_count(len(corpo["grupos"]))
        page.screenshot(path=str(OUTPUT / "criterios-para-50km-real.png"), full_page=True)
        aperta(janela.get_by_test_id("analise-agrupar-cancelar"))
        expect(territorios.get_by_test_id("analise-agrupamento")).to_have_count(0)

        # 8. Pela conversa: o pedido do comando abre os critérios preenchidos, com a prévia; nada muda até "Usar como seleção", e
        #    então o agrupamento por proximidade abre com a distância pedida.
        antes = area.get_by_test_id("analise-aba-territorios-resumo").inner_text()
        corpo, pedido = previa(lambda: send(page, "municípios com menos de 0,5 médico por mil habitantes a até 200 km uns dos outros"))
        assert pedido["criterios"] == {"partir_de": {"tipo": "pais"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 0.5}]}, pedido
        assert corpo["atendem"] == 89, corpo["atendem"]
        expect(chat.get_by_test_id("latest-reply")).to_contain_text(
            "Abri “Aplicar critérios de seleção”, na Seleção, com densidade abaixo de 0,5 em todo o país, agrupando os que ficam a "
            "até 200 km entre si.", timeout=60000)
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true")
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("0,5")
        expect(painel.get_by_test_id("analise-criterios-agrupar-depois")).to_contain_text("a até 200 km")
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text("89 atendem")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(antes)
        expect(chat.locator('[data-papel="agente"]').last).to_have_attribute("data-execucao", "concluido", timeout=60000)
        _, pedido = previa(lambda: aperta(painel.get_by_test_id("analise-criterios-como-selecao")),
                           condicao=lambda o: (o.get("agrupar") or {}).get("km") == 200)
        assert len(pedido["base"]["municipios"]["ids"]) == 89, pedido["base"]
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])
        janela = territorios.get_by_test_id("analise-agrupamento")
        expect(janela).to_have_attribute("data-modo", "proximidade")
        expect(janela.get_by_test_id("analise-agrupar-km")).to_have_value("200")
        aperta(janela.get_by_test_id("analise-agrupar-cancelar"))

        if chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 9. As regiões recolhidas: abrir não marca; marcar o Norte marca os 7 estados, sem aviso coletivo (o Desfazer, no alto, desfaz).
        #    Depois, o Pará inteiro: os critérios abrem no país todo (decisão 5), com "Os marcados na lista (144)".
        limpar()
        norte = territorios.locator('[data-testid="analise-regiao"][data-id="1"]')
        if linha_pa.get_attribute("data-aberto") == "true":
            aperta(linha_pa.get_by_test_id("analise-grupo-voltar"))
        if norte.get_attribute("data-aberta") == "true":  # fechar não muda a seleção
            aperta(norte.get_by_test_id("analise-regiao-ver"))
        expect(norte).to_have_attribute("data-aberta", "false")
        expect(norte.get_by_test_id("analise-grupo")).to_have_count(0)
        expect(norte.get_by_test_id("analise-regiao-contagem")).to_have_text("7 UFs · 450 municípios")
        abrir_regiao(territorios, "1")
        expect(norte.get_by_test_id("analise-grupo")).to_have_count(7)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        analise(lambda: marcado(norte.get_by_test_id("analise-regiao-todos")))
        expect(norte).to_have_attribute("data-situacao", "inteiro")
        expect(norte.locator('[data-testid="analise-grupo"][data-situacao="inteiro"]')).to_have_count(7)
        expect(territorios.get_by_test_id("analise-selecao-aviso")).to_have_count(0)
        desmarcado(norte.get_by_test_id("analise-regiao-todos"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        linha_pa = linha_do_estado(territorios, PARA)
        # O Pará inteiro já foi calculado no passo 7: a tela usa a memória, sem novo pedido ao motor.
        marcado(linha_pa.get_by_test_id("analise-grupo-todos"))
        expect(linha_pa).to_have_attribute("data-situacao", "inteiro")
        expect(partes).to_have_text(["Brasil", "Pará"])
        painel = criterios()
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-onde-marcados")).to_be_enabled()
        expect(painel.get_by_text("Os marcados na lista (144)", exact=True)).to_be_visible()
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)

        # 10. "Só o estado" (decisão 3): o Pará como uma bolha, com a fonte estadual; os municípios dele saem e ficam bloqueados. Com os
        #     municípios do Amazonas, a seleção mista (estados_unidade). Desativar libera os municípios, sem marcar nenhum; "Só os
        #     estados" do Norte põe os 7 como unidade.
        resposta, enviado = analise(lambda: aperta(linha_pa.get_by_test_id("analise-grupo-so-estado")),
                                    condicao=lambda o: o.get("nivel") == "estados")
        assert enviado.get("estados") == [PARA] and "base" not in enviado, enviado
        assert [item["tipo"] for item in resposta["itens"]] == ["estado"], resposta["itens"]
        expect(linha_pa).to_have_attribute("data-unidade", "true")
        expect(linha_pa.get_by_test_id("analise-grupo-so-estado")).to_have_attribute("aria-pressed", "true")
        expect(direita.get_by_test_id("analise-selecionado-estado")).to_contain_text("Pará (estado)")
        if linha_pa.get_attribute("data-aberto") != "true":
            aperta(linha_pa.get_by_test_id("analise-grupo-ver"))
        expect(linha_pa.get_by_test_id("analise-unidade").first.locator("input")).to_be_disabled()
        linha_am = linha_do_estado(territorios, AMAZONAS)
        misto, enviado = analise(lambda: marcado(linha_am.get_by_test_id("analise-grupo-todos")),
                                 condicao=lambda o: bool(o.get("estados_unidade")))
        assert enviado["nivel"] == "municipios" and enviado["estados_unidade"] == [PARA], enviado
        assert misto["niveis"] == ["municipios", "estados"], misto.get("niveis")
        assert sum(item["tipo"] == "estado" for item in misto["itens"]) == 1 and \
            sum(item["tipo"] == "municipio" for item in misto["itens"]) == 62, [item["tipo"] for item in misto["itens"]]
        expect(partes).to_have_text(["Brasil", "Seleção"])
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Amazonas (62 municípios) e Pará (estado)")
        aperta(linha_pa.get_by_test_id("analise-grupo-so-estado"))
        expect(linha_pa).to_have_attribute("data-unidade", "false")
        expect(linha_pa.get_by_test_id("analise-grupo-todos")).not_to_be_checked()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Amazonas (62 municípios)")
        limpar()
        _, enviado = analise(lambda: aperta(norte.get_by_test_id("analise-regiao-so-estados")),
                             condicao=lambda o: o.get("nivel") == "estados")
        assert sorted(enviado["estados"]) == ["11", "12", "13", "14", "15", "16", "17"], enviado
        expect(norte.locator('[data-testid="analise-grupo"][data-unidade="true"]')).to_have_count(7)

        # 11. Por escolha livre, só com os selecionados: cinco municípios do Pará; o mini mapa que escolhe (tocar num ponto cinza põe;
        #     num cheio, tira; o contorno e a extensão mudam), "Conjunto A", o nome editado pelo ✎ (no mapa da seleção), o nome
        #     repetido recusado e o contorno tracejado com o nome no mapa da análise.
        limpar()
        linha_pa = linha_do_estado(territorios, PARA)
        if linha_pa.get_attribute("data-aberto") != "true":
            aperta(linha_pa.get_by_test_id("analise-grupo-ver"))
        unidades_pa = linha_pa.get_by_test_id("analise-unidade")
        for indice in range(4):
            marcado(unidades_pa.nth(indice).locator("input"))
        analise(lambda: marcado(unidades_pa.nth(4).locator("input")),
                condicao=lambda o: len(((o.get("base") or {}).get("municipios") or {}).get("ids") or []) == 5)
        janela = agrupar("livre")
        agregar = janela.get_by_test_id("analise-agregar")
        agregar.get_by_test_id("analise-agregar-grupo").select_option(PARA)
        lista = agregar.get_by_test_id("analise-agregar-unidade")
        expect(lista).to_have_count(5)  # só os selecionados
        for indice in range(4):
            marcado(lista.nth(indice).locator("input"))
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(4)
        expect(agregar.get_by_test_id("analise-agregar-nome")).to_have_value("Conjunto A")
        resumo = agregar.get_by_test_id("analise-agregar-resumo")
        expect(resumo).to_have_text(re.compile(r"^4 municípios · [\d.]+ km de ponta a ponta"), timeout=180000)
        km_antes = resumo.inner_text().split(" · ")[1]
        mini = agregar.get_by_test_id("analise-mapa-conjuntos")
        contorno = agregar.get_by_test_id("analise-mapa-contorno")
        expect(contorno).to_have_count(1)
        contorno_antes = contorno.get_attribute("d")
        cinza = mini.locator('[data-testid="analise-mapa-ponto"][data-papel="fundo"]')
        expect(cinza).to_have_count(1)  # o quinto selecionado, em cinza
        ponto = mini.locator('[data-testid="analise-mapa-ponto"][data-id="' + cinza.get_attribute("data-id") + '"]')
        ponto.dispatch_event("click")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(5)
        expect(ponto).to_have_attribute("data-papel", "membro")
        expect(resumo).to_have_text(re.compile(r"^5 municípios · [\d.]+ km de ponta a ponta · .+ entrou no conjunto\.$"), timeout=180000)
        assert resumo.inner_text().split(" · ")[1] != km_antes or contorno.get_attribute("d") != contorno_antes, "o conjunto mudou"
        ponto.dispatch_event("click")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(4)
        expect(resumo).to_contain_text("saiu do conjunto.")
        ponto.dispatch_event("click")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(5)
        _, enviado = analise(lambda: aperta(agregar.get_by_test_id("analise-agregar-criar")),
                             condicao=lambda o: bool(o.get("conjuntos")))
        assert [c["rotulo"] for c in enviado["conjuntos"]] == ["Conjunto A"] and len(enviado["conjuntos"][0]["membros"]) == 5, \
            enviado["conjuntos"]
        expect(territorios.get_by_test_id("analise-agrupamento")).to_have_count(0)
        texto_do_conjunto = direita.get_by_test_id("analise-selecionado-conjunto-texto")
        expect(texto_do_conjunto).to_contain_text("Conjunto A · conjunto · 5 municípios", timeout=60000)
        aperta(direita.get_by_test_id("analise-selecionado-conjunto-editar"))
        agregar = territorios.get_by_test_id("analise-agrupamento").get_by_test_id("analise-agregar")
        expect(agregar.get_by_test_id("analise-agregar-criar")).to_have_text("Salvar conjunto")
        agregar.get_by_test_id("analise-agregar-nome").fill("Paraenses do A")
        aperta(agregar.get_by_test_id("analise-agregar-criar"))
        expect(texto_do_conjunto).to_contain_text("Paraenses do A · conjunto · 5 municípios", timeout=60000)
        expect(direita.get_by_test_id("analise-mapa-selecao").locator('[data-testid="analise-mapa-contorno"][data-nome="Paraenses do A"]')
               ).to_have_count(1, timeout=180000)
        # Mais dois selecionados, para formar outro conjunto: o nome repetido é recusado.
        for indice in range(5, 7):
            marcado(unidades_pa.nth(indice).locator("input"))
        janela = agrupar("livre")
        agregar = janela.get_by_test_id("analise-agregar")
        expect(agregar.get_by_test_id("analise-agregar-nome")).to_have_value("Conjunto A")
        agregar.get_by_test_id("analise-agregar-nome").fill("paraenses do a")
        expect(agregar.get_by_test_id("analise-agregar-nome-repetido")).to_have_text("Já existe um conjunto com esse nome na análise.")
        expect(agregar.get_by_test_id("analise-agregar-criar")).to_be_disabled()
        aperta(agregar.get_by_test_id("analise-agregar-cancelar"))
        expect(territorios.get_by_test_id("analise-agrupamento")).to_have_count(0)
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        aperta(area.get_by_test_id("analise-desenho-mapa"))
        expect(area.get_by_test_id("mapa-analise").get_by_test_id("mapa-simbolos")).to_contain_text(
            "contorno tracejado com o nome", timeout=180000)
        page.screenshot(path=str(OUTPUT / "criterios-contorno-no-mapa-real.png"), full_page=True)
        aperta(area.get_by_test_id("analise-desenho-grafico"))
        aperta(area.get_by_test_id("analise-aba-territorios"))

        # 12. O exemplo do objetivo: o Norte com densidade abaixo de 0,5, agrupado a até 100 km entre si, na Análise Espacial: a aba Base
        #     com "N conjuntos e M territórios individuais" (nunca "0 municípios") e a Referência com densidade a partir de 1: cada
        #     conjunto com a menor e a maior distância e a referência do membro mais próximo, também nos Detalhes.
        painel = criterios()
        marcado(painel.get_by_test_id("analise-criterios-onde-regioes"))
        expect(painel.get_by_test_id("analise-criterios-estado")).to_have_text("Escolha ao menos uma região.")
        marcado(painel.locator('[data-testid="analise-criterios-onde-regiao"][data-id="1"]'))
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"),
                               condicao=lambda o: o["criterios"]["partir_de"].get("tipo") == "ufs")
        assert sorted(pedido["criterios"]["partir_de"]["ufs"]) == ["11", "12", "13", "14", "15", "16", "17"], pedido["criterios"]
        atendem_norte = corpo["atendem"]
        analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-selecao")), condicao=lambda o: not o.get("conjuntos"))
        janela = agrupar("proximidade")
        corpo, _ = previa(lambda: janela.get_by_test_id("analise-agrupar-km").fill("100"),
                          condicao=lambda o: (o.get("agrupar") or {}).get("km") == 100)
        grupos_norte = corpo["grupos"]
        assert grupos_norte and len(grupos_norte) <= 50 and all(g["extensao_km"] <= 100 for g in grupos_norte), \
            [g["extensao_km"] for g in grupos_norte]
        individuais = atendem_norte - sum(len(g["membros"]) for g in grupos_norte)
        analise(lambda: aperta(janela.get_by_test_id("analise-agrupar-usar")),
                condicao=lambda o: len(o.get("conjuntos") or []) == len(grupos_norte))
        expect(direita.get_by_test_id("analise-selecionado-conjunto")).to_have_count(len(grupos_norte))
        aperta(area.get_by_test_id("analise-familia-espacial"))
        janela = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
        expect(janela).to_be_visible(timeout=60000)
        esperado = str(len(grupos_norte)) + (" conjunto" if len(grupos_norte) == 1 else " conjuntos") + (
            " e " + str(individuais) + (" território individual" if individuais == 1 else " territórios individuais") if individuais else "")
        expect(janela.get_by_test_id("territorios-status-base")).to_have_text(esperado, timeout=180000)
        expect(janela.get_by_test_id("territorios-base-conjuntos")).to_contain_text("Conjunto A (")
        aperta(janela.get_by_test_id("territorios-aba-referencia"))
        aperta(janela.get_by_test_id("territorios-referencia-mais-densidade"))
        filtro = janela.get_by_test_id("territorios-referencia-filtro").first
        filtro.get_by_test_id("territorios-referencia-filtro-operador").select_option(">=")
        filtro.get_by_test_id("territorios-referencia-filtro-valor").fill("1")
        expect(janela.get_by_test_id("territorios-calcular")).to_be_enabled(timeout=60000)
        espacial, enviado = analise(lambda: aperta(janela.get_by_test_id("territorios-calcular")),
                                    condicao=lambda o: bool(o.get("consulta")))
        assert enviado["consulta"]["referencia"]["filtros"] == [{"indicador": "densidade", "operador": ">=", "valor": 1}], enviado
        conjuntos_espaciais = [item for item in espacial["itens"] if item["tipo"] == "conjunto"]
        assert len(conjuntos_espaciais) == len(grupos_norte), [item["tipo"] for item in espacial["itens"]]
        for item in conjuntos_espaciais:
            referencia = item.get("referencia_do_item") or {}
            assert item["distancia_km"] is not None and item["distancia_km_max"] is not None and \
                item["distancia_km_max"] >= item["distancia_km"], item
            assert referencia.get("id") and (referencia.get("membro") or {}).get("id") in item["membros"], (item["rotulo"], referencia)
        fecha_painel = area.get_by_test_id("analise-painel-fechar")
        if fecha_painel.count():
            aperta(fecha_painel)
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        primeiro = conjuntos_espaciais[0]
        linha = area.get_by_test_id("analise-tabela").locator('[data-testid="analise-linha"][data-id="' + primeiro["id"] + '"]')
        expect(linha).to_contain_text(primeiro["referencia_do_item"]["rotulo"], timeout=60000)
        expect(linha).to_contain_text(" a ")
        page.screenshot(path=str(OUTPUT / "criterios-norte-espacial-real.png"), full_page=True)

        # 13. Os conjuntos nas comparações (comando de 08/11/2026). Primeiro, os quintis: com dez municípios do Pará marcados, um conjunto
        #     deles que não fica no lugar dos membros não muda os cortes dos quintis do mapa (só as unidades entram). Depois, o Norte com
        #     densidade abaixo de 0,5 junto com os dez, agrupado a até 100 km: ordenar por densidade põe os conjuntos entre os municípios,
        #     cada um no lugar do seu valor; "densidade abaixo de 0,4" inclui ou deixa fora cada conjunto pelo valor, e a contagem separa
        #     municípios e conjuntos; na Análise Espacial, com as faixas 0; 100; 300, cada conjunto fica na faixa da sua menor
        #     distância, e ordenar pela distância o põe entre as unidades.
        def abre(funcao):
            botao = area.get_by_test_id("analise-funcao-" + funcao)
            if botao.get_attribute("aria-expanded") != "true":
                aperta(botao)
            painel_da_funcao = area.get_by_test_id("analise-painel")
            expect(painel_da_funcao).to_have_attribute("data-painel", funcao)
            return painel_da_funcao

        def entre_as_unidades(resposta, atributo):
            """A ordem do motor pelo valor de cada item (unidade ou conjunto), sem desempate artificial, e algum conjunto com
            unidades antes e depois dele."""
            valor = (lambda item: item["distancia_km"]) if atributo == "distancia_km" else (lambda item: item[atributo])
            ordem = sorted((item["ordem"]["posicao"], valor(item), item["tipo"]) for item in resposta["itens"]
                           if item.get("ordem") and item["ordem"]["posicao"] is not None)
            assert all(a[1] <= b[1] for a, b in zip(ordem, ordem[1:])), ordem[:12]
            tipos = [tipo for _, _, tipo in ordem]
            conjuntos = [i for i, tipo in enumerate(tipos) if tipo == "conjunto"]
            assert conjuntos and any("municipio" in tipos[:i] and "municipio" in tipos[i + 1:] for i in conjuntos), tipos
            return ordem

        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        limpar_filtros = area.get_by_test_id("analise-limpar-filtros")
        if limpar_filtros.count() and limpar_filtros.is_visible():
            aperta(limpar_filtros)
        aperta(area.get_by_test_id("analise-aba-territorios"))
        limpar()
        linha_pa = linha_do_estado(territorios, PARA)
        if linha_pa.get_attribute("data-aberto") != "true":
            aperta(linha_pa.get_by_test_id("analise-grupo-ver"))
        unidades_pa = linha_pa.get_by_test_id("analise-unidade")
        for indice in range(9):
            marcado(unidades_pa.nth(indice).locator("input"))
        antes, _ = analise(lambda: marcado(unidades_pa.nth(9).locator("input")),
                           condicao=lambda o: len(((o.get("base") or {}).get("municipios") or {}).get("ids") or []) == 10)
        assert antes["grupos_mapa"] and antes["grupos_mapa"]["universo"] == 10, antes.get("grupos_mapa")
        janela = agrupar("livre")
        agregar = janela.get_by_test_id("analise-agregar")
        agregar.get_by_test_id("analise-agregar-grupo").select_option(PARA)
        lista = agregar.get_by_test_id("analise-agregar-unidade")
        expect(lista).to_have_count(10)
        for indice in range(10):
            marcado(lista.nth(indice).locator("input"))
        desmarcado(agregar.get_by_test_id("analise-agregar-substitui"))
        com_conjunto, enviado = analise(lambda: aperta(agregar.get_by_test_id("analise-agregar-criar")),
                                        condicao=lambda o: bool(o.get("conjuntos")))
        assert len(enviado["base"]["municipios"]["ids"]) == 10, enviado["base"]  # os membros continuam na análise
        assert com_conjunto["grupos_mapa"]["cortes"] == antes["grupos_mapa"]["cortes"], (com_conjunto["grupos_mapa"], antes["grupos_mapa"])
        assert com_conjunto["grupos_mapa"]["universo"] == 10
        assert all(item["grupo_mapa"] is None for item in com_conjunto["itens"] if item["tipo"] == "conjunto")
        aperta(direita.get_by_role("button", name="Desfazer o conjunto Conjunto A", exact=True))
        expect(direita.get_by_test_id("analise-selecionado-conjunto")).to_have_count(0)
        # O Norte com densidade abaixo de 0,5, junto com os dez do Pará, agrupado a até 100 km.
        painel = criterios()
        marcado(painel.get_by_test_id("analise-criterios-onde-regioes"))
        marcado(painel.locator('[data-testid="analise-criterios-onde-regiao"][data-id="1"]'))
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"),
               condicao=lambda o: o["criterios"]["partir_de"].get("tipo") == "ufs")
        marcado(painel.get_by_test_id("analise-criterios-junto"))
        analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-selecao")),
                condicao=lambda o: len(((o.get("base") or {}).get("municipios") or {}).get("ids") or []) > 10)
        janela = agrupar("proximidade")
        corpo, _ = previa(lambda: janela.get_by_test_id("analise-agrupar-km").fill("100"),
                          condicao=lambda o: (o.get("agrupar") or {}).get("km") == 100)
        n_norte = len(corpo["grupos"])
        junto, _ = analise(lambda: aperta(janela.get_by_test_id("analise-agrupar-usar")),
                           condicao=lambda o: len(o.get("conjuntos") or []) == n_norte)
        assert sum(item["tipo"] == "municipio" for item in junto["itens"]) > 0
        # Ordenar por densidade, da menor para a maior: os conjuntos entre os municípios, cada um no lugar do seu valor.
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        ordenar = abre("ordenar")
        ordenar.get_by_test_id("analise-ordenar-atributo").select_option("densidade")
        ordenar.get_by_test_id("analise-ordenar-ordem").select_option("asc")
        ordenada, _ = analise(lambda: aperta(ordenar.get_by_test_id("analise-ordenar-aplicar")),
                              condicao=lambda o: (o.get("ordenar") or {}).get("atributo") == "densidade")
        entre_as_unidades(ordenada, "densidade")
        assert ordenada["ordenacao"]["por_tipo"]["conjuntos"]["ordenados"] == n_norte, ordenada["ordenacao"]["por_tipo"]
        expect(ordenar.locator('[data-testid="analise-ordenar-lista"] li[data-tipo="conjunto"]').first).to_contain_text("conjunto",
                                                                                                                    timeout=60000)
        expect(ordenar.get_by_test_id("analise-ordenar-por-tipo")).to_contain_text(" conjunto")
        # "Densidade abaixo de 0,4": cada conjunto pelo valor dele; a contagem separa municípios e conjuntos.
        condicoes = abre("condicoes")
        condicoes.get_by_test_id("analise-condicao-atributo").first.select_option("densidade")
        condicoes.get_by_test_id("analise-condicao-operador").first.select_option("<")
        condicoes.get_by_test_id("analise-condicao-valor").first.fill("0,4")
        filtrada, _ = analise(lambda: aperta(condicoes.get_by_test_id("analise-condicoes-aplicar")),
                              condicao=lambda o: any(str(c.get("valor")) in ("0.4", "0,4") for c in o.get("condicoes") or []))
        for item in filtrada["itens"]:
            if item["tipo"] == "conjunto":
                assert item["condicoes"]["situacao"] == ("ATENDE" if item["densidade"] < 0.4 else "NAO_ATENDE"), item
        por_tipo = filtrada["condicoes"]["por_tipo"]
        assert por_tipo["conjuntos"]["universo"] == n_norte and sum(por_tipo["conjuntos"]["contagens"].values()) == n_norte
        atende = condicoes.locator('[data-testid="analise-condicoes-contagem"][data-situacao="ATENDE"]')
        expect(atende).to_have_attribute("data-conjuntos", str(por_tipo["conjuntos"]["contagens"]["ATENDE"]))
        if por_tipo["conjuntos"]["contagens"]["ATENDE"]:
            expect(atende.get_by_test_id("analise-condicoes-por-tipo")).to_contain_text("conjunto")
        page.screenshot(path=str(OUTPUT / "conjuntos-nas-comparacoes-real.png"), full_page=True)
        # Na Análise Espacial (a Escolha dos territórios do passo 12), as faixas 0; 100; 300 e a ordem pela distância.
        aperta(area.get_by_test_id("analise-familia-espacial"))
        painel_aberto = area.get_by_test_id("analise-painel")
        if not painel_aberto.count() or painel_aberto.get_attribute("data-painel") != "referencia":
            aperta(area.get_by_test_id("analise-referencia-escolher"))
        janela = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
        expect(janela).to_be_visible(timeout=60000)
        aperta(janela.get_by_test_id("territorios-aba-referencia"))
        janela.get_by_test_id("analise-faixas-distancia").fill("0; 100; 300")
        espacial, _ = analise(lambda: aperta(janela.get_by_test_id("analise-faixas-distancia-aplicar")),
                              condicao=lambda o: o.get("faixas_distancia") == [0, 100, 300] and bool(o.get("consulta")))
        conjuntos_espaciais = [item for item in espacial["itens"] if item["tipo"] == "conjunto"]
        assert len(conjuntos_espaciais) == n_norte, len(conjuntos_espaciais)
        for item in conjuntos_espaciais:
            distancia = item["distancia_km"]
            faixa = item["faixa_distancia"]
            esperada = None if distancia is None else "0 a <100" if distancia < 100 else "100 a 300" if distancia <= 300 else "fora"
            assert (faixa if faixa in (None, "fora") else faixa["rotulo"]) == esperada, (item["rotulo"], distancia, faixa)
        assert espacial["faixas_distancia"]["por_tipo"]["conjuntos"]["universo"] == n_norte
        ordenar = abre("ordenar")
        ordenar.get_by_test_id("analise-ordenar-atributo").select_option("distancia_km")
        ordenar.get_by_test_id("analise-ordenar-ordem").select_option("asc")
        pela_distancia, _ = analise(lambda: aperta(ordenar.get_by_test_id("analise-ordenar-aplicar")),
                                    condicao=lambda o: (o.get("ordenar") or {}).get("atributo") == "distancia_km")
        entre_as_unidades(pela_distancia, "distancia_km")
        page.screenshot(path=str(OUTPUT / "conjuntos-pela-distancia-real.png"), full_page=True)

        # 14. Nenhum "cluster" à vista.
        assert "cluster" not in page.evaluate("() => document.body.innerText").lower()
        page.screenshot(path=str(OUTPUT / "criterios-conjuntos-real.png"), full_page=True)
        assert not falhas, falhas
        assert not chamadas_llm, chamadas_llm
        browser.close()
    print("CRITÉRIOS PASS: sem as abas de modo (a árvore com as regiões recolhidas e as três ações), os critérios no painel direito "
          "(no país todo, sem valores, competências em ordem de data, sem o passo de agrupar), a prévia sozinha (densidade abaixo de "
          "0,5 em jun/2024: 89; o valor incompleto esmaecido; 0,7 sem clicar), \"Usar como seleção (89)\" com a trilha, a regra e os "
          "Detalhes, as Condições nos marcados, o agrupamento por proximidade só com os selecionados (a até 200 km; o Pará a até "
          "100 km com os conjuntos da referência; os sem conjunto continuam individuais), junto com a seleção (os que já estão num "
          "conjunto ficam de fora, com o aviso), o Pará só pela distância (50 km), o pedido pela conversa com o agrupamento depois, "
          "\"Só o estado\" (o Pará como unidade, a seleção mista) e \"Só os estados\" do Norte, a escolha livre com o mini mapa que "
          "escolhe, os nomes únicos e o contorno no mapa, o exemplo do objetivo na Análise Espacial (\"N conjuntos e M territórios "
          "individuais\") e os conjuntos nas comparações; nenhum \"cluster\" (base versionada).")


if __name__ == "__main__":
    main()
