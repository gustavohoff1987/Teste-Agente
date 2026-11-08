"""Seleção por critérios de ponta a ponta (07/11/2026, comando de 07/11/2026; antes, item 6 do comando de 06/11/2026), com a base
versionada.

Confere, contra as respostas de /api/painel/criterios e /api/painel, o que o comando pede na tela:
- uma ferramenta por vez: os modos "Marcar na lista" (o padrão), "Por critérios" e "Agrupar territórios", sem dois formulários
  abertos nem formulário e árvore juntos; "Por critérios" começa sem valores (nada é sugerido) e sem o botão "Ver a prévia";
- a prévia sozinha, a cada ajuste: no todo, densidade abaixo de 0,5 em jun/2024 → 89 (a linha-resumo e o mini mapa no alto); com
  o valor incompleto ("0,"), a linha de estado diz o que falta e o mini mapa fica esmaecido; agrupar a até 200 km entre si (o
  campo de km mostra o número, na largura dos outros campos) → nenhum conjunto passa de 200 km, cada um com o contorno no mini
  mapa; trocar 0,5 por 0,7 pede a prévia de novo, sem clicar;
- "Usar como seleção (89)": a trilha "Brasil › Seleção: densidade abaixo de 0,5 em jun/2024 (89)", a regra e os Detalhes;
- "Usar como seleção" nas Condições abre "Por critérios" nos marcados, com a prévia;
- "Usar cada conjunto como um território", no lugar da seleção atual: os conjuntos "Conjunto A"… na análise;
- junto com a seleção atual: no Pará, a até 100 km, os conjuntos da referência do comando (Igarapé-Miri, Limoeiro do Ajuru, Moju
  e Muaná; Bagre, Curralinho e Oeiras do Pará; Acará e Concórdia do Pará) se somam aos que já estão na análise, com as letras
  continuando da próxima livre;
- agrupar só pela distância (o Pará a até 50 km, sem critério de valor);
- pela conversa, o pedido do comando abre "Por critérios" preenchido, com a prévia, e nada muda na análise até a confirmação;
- as regiões na árvore do Brasil (marcar o Norte marca os 7 estados); com o Pará na trilha, "Por critérios" abre com ele
  pré-escolhido e com "Os marcados na lista (144)";
- "Agrupar os marcados" com cinco municípios: o mini mapa que escolhe (o ponto entra e sai, e o contorno e a extensão mudam),
  "Conjunto A", o nome editado pelo ✎ em "Na análise" e em "Ver os conjuntos no mapa", o nome repetido recusado e o contorno
  tracejado com o nome no mapa da análise;
- o exemplo do objetivo, sem passar pela lista: Norte, densidade abaixo de 0,5, a até 100 km entre si, só os conjuntos na análise,
  a Análise Espacial com a aba Base dos conjuntos e a Referência com densidade a partir de 1: cada conjunto com a menor e a maior
  distância e a referência do membro mais próximo, também nos Detalhes;
- os conjuntos nas comparações (comando de 08/11/2026): os cortes dos quintis não mudam com um conjunto que não fica no
  lugar dos membros; o Norte junto com dez municípios do Pará: a ordem por densidade e a condição "densidade abaixo de
  0,4" com os conjuntos pelo valor de cada um e as contagens por tipo; na Análise Espacial, as faixas 0; 100; 300 e a
  ordem pela distância com os conjuntos entre as unidades;
- nenhum texto à vista com "cluster".

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, options_of, send

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
PARA = "15"
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
        partes = area.get_by_test_id("analise-trilha").get_by_test_id("analise-trilha-parte")
        modos = territorios.get_by_test_id("analise-selecao-modos")

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

        # A caixa da conversa, minimizada (a conversa do passo 8 a abre de novo).
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. Uma ferramenta por vez: os três modos; "Marcar na lista" de início; "Por critérios" esconde a árvore, começa sem valores e
        #    sem "Ver a prévia".
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true", timeout=180000)
        expect(modos.get_by_role("radio")).to_have_text(["Marcar na lista", "Por critérios", "Agrupar territórios"])
        expect(modos.get_by_test_id("analise-modo-lista")).to_have_attribute("aria-checked", "true")
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible()
        aperta(modos.get_by_test_id("analise-modo-criterios"))
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel).to_be_visible()
        expect(territorios.get_by_test_id("analise-arvore")).to_be_hidden()
        expect(territorios.get_by_test_id("analise-agregar")).to_have_count(0)
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("")
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()
        expect(page.get_by_test_id("analise-criterios-previa")).to_have_count(0)
        expect(painel.get_by_test_id("analise-criterios-estado")).to_have_text("Falta o valor do critério 1.")

        # 2. A prévia sozinha: no todo, densidade abaixo de 0,5 em jun/2024 → 89.
        expect(painel.get_by_test_id("analise-criterios-competencia")).to_have_value("202406")
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"))
        assert pedido["criterios"] == {"partir_de": {"tipo": "pais"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 0.5}]}, pedido
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

        # 3. Agrupar a até 200 km entre si: o campo de km vazio, na largura dos outros; nenhum conjunto passa de 200 km; o contorno de
        #    cada um no mini mapa; trocar 0,5 por 0,7 pede a prévia de novo, sem clicar.
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        km = painel.get_by_test_id("analise-criterios-agrupar-km")
        expect(km).to_have_value("")
        expect(painel.get_by_test_id("analise-criterios-estado")).to_have_text("Falta a distância do agrupamento.")
        corpo, pedido = previa(lambda: km.fill("200"))
        assert pedido["agrupar"] == {"km": 200}, pedido
        expect(km).to_have_value("200")
        assert km.bounding_box()["width"] > 60, km.bounding_box()
        grupos = corpo["grupos"]
        assert grupos and all(grupo["extensao_km"] <= 200 for grupo in grupos), [grupo["extensao_km"] for grupo in grupos]
        assert grupos[0]["rotulo"] == "Conjunto A", grupos[0]["rotulo"]
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text(str(len(grupos)) + " conjunto")
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text(str(len(corpo["isolados"]) + len(corpo["sem_posicao"] or [])) +
                                                                                 " sem conjunto")
        expect(painel.get_by_test_id("analise-mapa-contorno")).to_have_count(len(grupos))
        aperta(painel.get_by_test_id("analise-criterios-ver-conjuntos"))
        expect(painel.get_by_test_id("analise-criterios-grupo")).to_have_count(len(grupos))
        expect(painel.get_by_test_id("analise-criterios-grupo-nome").first).to_have_value("Conjunto A")
        corpo07, _ = previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,7"),
                            condicao=lambda o: (o["criterios"]["filtros"] or [{}])[0].get("valor") == 0.7)
        assert corpo07["atendem"] > 89, corpo07["atendem"]
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text(str(corpo07["atendem"]) + " atendem")
        previa(lambda: painel.get_by_test_id("analise-criterio-valor").fill("0,5"),
               condicao=lambda o: (o["criterios"]["filtros"] or [{}])[0].get("valor") == 0.5)
        page.screenshot(path=str(OUTPUT / "criterios-mini-mapa-real.png"), full_page=True)

        # 4. "Usar como seleção (89)", sem o agrupamento: a trilha com a regra, a regra na Seleção e nos Detalhes; o modo volta à lista.
        previa(lambda: marcado(painel.get_by_test_id("analise-criterios-nao-agrupar")), condicao=lambda o: not o.get("agrupar"))
        expect(painel.get_by_test_id("analise-criterios-como-selecao")).to_have_text("Usar como seleção (89)", timeout=60000)
        resposta, _ = analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-selecao")))
        na_analise = {item["id"] for item in resposta["itens"] if item["tipo"] == "municipio"}
        assert len(na_analise) == 89, len(na_analise)
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)
        expect(modos.get_by_test_id("analise-modo-lista")).to_have_attribute("aria-checked", "true")
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])
        expect(territorios.get_by_test_id("analise-selecao-regra")).to_contain_text(
            "Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (89)")
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area.get_by_test_id("analise-detalhes-regra")).to_contain_text(
            "Seleção por critérios: densidade abaixo de 0,5 em jun/2024 (89)", timeout=60000)

        # 5. "Usar como seleção" nas Condições: abre "Por critérios" nos marcados, com a prévia; Cancelar volta à lista.
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
        expect(modos.get_by_test_id("analise-modo-criterios")).to_have_attribute("aria-checked", "true")
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterios-onde-marcados")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("1")
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])

        # 6. "Reaplicar" e "Usar cada conjunto como um território", no lugar da seleção atual: os conjuntos "Conjunto A"… na análise.
        aperta(territorios.get_by_test_id("analise-criterios-reaplicar"))
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("0,5")
        expect(painel.get_by_test_id("analise-criterios-onde-todo")).to_be_checked()
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        corpo, _ = previa(lambda: painel.get_by_test_id("analise-criterios-agrupar-km").fill("200"))
        n_conjuntos = len(corpo["grupos"])
        assert 0 < n_conjuntos <= 50, n_conjuntos
        expect(painel.get_by_test_id("analise-criterios-no-lugar")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-sem-conjunto")).to_be_checked()
        resposta, enviado = analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-grupos")))
        assert [c["rotulo"] for c in enviado["conjuntos"]][:2] == ["Conjunto A", "Conjunto B"], enviado["conjuntos"][:2]
        expect(territorios.get_by_test_id("analise-selecionado-conjunto")).to_have_count(n_conjuntos)
        expect(territorios.get_by_test_id("analise-selecionado-conjunto").first).to_contain_text("Conjunto A · conjunto ·")
        expect(partes.nth(1)).to_have_text(re.compile(r"^Seleção: densidade abaixo de 0,5, agrupados a até 200 km entre si"))

        # 7. Junto com a seleção atual: no Pará, a até 100 km, os conjuntos da referência do comando se somam aos de antes, e as letras
        #    continuam da próxima livre. Depois, agrupar só pela distância: o Pará a até 50 km, sem critério de valor.
        aperta(modos.get_by_test_id("analise-modo-criterios"))
        painel = territorios.get_by_test_id("analise-criterios")
        marcado(painel.get_by_test_id("analise-criterios-onde-estados"))
        marcado(painel.locator('[data-testid="analise-criterios-onde-estado"][data-id="' + PARA + '"]'))
        painel.get_by_test_id("analise-criterio-valor").fill("0,5")
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterios-agrupar-km").fill("100"),
                               condicao=lambda o: (o.get("agrupar") or {}).get("km") == 100)
        assert pedido["criterios"]["partir_de"] == {"tipo": "ufs", "ufs": [PARA]}, pedido
        do_para = [sorted(grupo["membros"]) for grupo in corpo["grupos"]]
        for esperado in CONJUNTOS_DO_COMANDO:
            assert esperado in do_para, (esperado, do_para)
        marcado(painel.get_by_test_id("analise-criterios-junto"))
        resposta, enviado = analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-grupos")))
        nomes = [c["rotulo"] for c in enviado["conjuntos"]]
        assert len(nomes) == n_conjuntos + len(corpo["grupos"]) and len(set(nomes)) == len(nomes), nomes
        assert nomes[n_conjuntos] not in nomes[:n_conjuntos], nomes
        expect(territorios.get_by_test_id("analise-selecionado-conjunto")).to_have_count(len(nomes))
        aperta(modos.get_by_test_id("analise-modo-criterios"))
        painel = territorios.get_by_test_id("analise-criterios")
        marcado(painel.get_by_test_id("analise-criterios-onde-estados"))
        marcado(painel.locator('[data-testid="analise-criterios-onde-estado"][data-id="' + PARA + '"]'))
        painel.get_by_test_id("analise-criterio-valor").fill("")
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterios-agrupar-km").fill("50"),
                               condicao=lambda o: (o.get("agrupar") or {}).get("km") == 50 and not o["criterios"]["filtros"])
        assert corpo["atendem"] == 144 and corpo["grupos"], (corpo["atendem"], len(corpo["grupos"] or []))
        expect(painel.get_by_test_id("analise-mapa-contorno")).to_have_count(len(corpo["grupos"]))
        page.screenshot(path=str(OUTPUT / "criterios-para-50km-real.png"), full_page=True)
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)

        # 8. Pela conversa: o pedido do comando abre "Por critérios" preenchido, com a prévia; nada muda até a confirmação.
        antes = area.get_by_test_id("analise-aba-territorios-resumo").inner_text()
        corpo, pedido = previa(lambda: send(page, "municípios com menos de 0,5 médico por mil habitantes a até 200 km uns dos outros"))
        assert pedido["criterios"] == {"partir_de": {"tipo": "pais"},
                                       "filtros": [{"indicador": "densidade", "operador": "<", "valor": 0.5}]}, pedido
        assert pedido["agrupar"] == {"km": 200} and corpo["atendem"] == 89, pedido
        expect(chat.get_by_test_id("latest-reply")).to_contain_text(
            "Abri “Por critérios”, na Seleção, com densidade abaixo de 0,5 em todo o país, agrupando os que ficam a até 200 km "
            "entre si.", timeout=60000)
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true")
        expect(modos.get_by_test_id("analise-modo-criterios")).to_have_attribute("aria-checked", "true")
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterio-valor")).to_have_value("0,5")
        expect(painel.get_by_test_id("analise-criterios-agrupar")).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-agrupar-km")).to_have_value("200")
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text("89 atendem")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(antes)
        expect(chat.locator('[data-papel="agente"]').last).to_have_attribute("data-execucao", "concluido", timeout=60000)
        # A mesma definição do passo 5 (os 89, com a condição aplicada): a tela reaproveita a resposta guardada, sem novo pedido ao
        # motor (a memória das respostas da área), e por isso o roteiro não espera um pedido aqui.
        aperta(painel.get_by_test_id("analise-criterios-como-selecao"))
        expect(partes).to_have_text(["Brasil", "Seleção: densidade abaixo de 0,5 em jun/2024 (89)"])
        expect(modos.get_by_test_id("analise-modo-lista")).to_have_attribute("aria-checked", "true")

        if chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        def desmarcado(locator):
            """Desmarca a caixa pelo teclado, só se estiver marcada."""
            locator.scroll_into_view_if_needed()
            if locator.is_checked():
                locator.focus()
                locator.press("Space")
            expect(locator).not_to_be_checked()

        # 9. As regiões na árvore do Brasil (item 3): Brasil › região › estado › município; marcar a região marca todos os estados
        #    dela. Depois, o Pará inteiro na lista: em "Por critérios", o lugar em uso vem pré-escolhido (item 2.3), e os marcados
        #    aparecem com quantos são (item 2.1).
        aperta(area.get_by_test_id("analise-limpar-selecao"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        regioes = territorios.get_by_test_id("analise-regioes").get_by_test_id("analise-regiao")
        expect(regioes).to_have_count(5)
        expect(regioes.locator(".analise-regiao-linha .analise-grupo-nome")).to_have_text(
            ["Norte", "Nordeste", "Sudeste", "Sul", "Centro-Oeste"])
        norte = territorios.locator('[data-testid="analise-regiao"][data-id="1"]')
        expect(norte.get_by_test_id("analise-regiao-contagem")).to_have_text("7 estados · 450 municípios")
        expect(norte.get_by_test_id("analise-grupo")).to_have_count(7)
        analise(lambda: marcado(norte.get_by_test_id("analise-regiao-todos")))
        expect(norte).to_have_attribute("data-situacao", "inteiro")
        expect(norte.locator('[data-testid="analise-grupo"][data-situacao="inteiro"]')).to_have_count(7)
        expect(territorios.get_by_test_id("analise-selecao-aviso")).to_contain_text("Todos os municípios da Região Norte marcados.")
        desmarcado(norte.get_by_test_id("analise-regiao-todos"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        linha_pa = territorios.locator('[data-testid="analise-grupo"][data-id="' + PARA + '"]')
        analise(lambda: marcado(linha_pa.get_by_test_id("analise-grupo-todos")))
        expect(partes).to_have_text(["Brasil", "Pará"])
        aperta(modos.get_by_test_id("analise-modo-criterios"))
        painel = territorios.get_by_test_id("analise-criterios")
        expect(painel.get_by_test_id("analise-criterios-onde-estados")).to_be_checked()
        expect(painel.locator('[data-testid="analise-criterios-onde-estado"][data-id="' + PARA + '"]')).to_be_checked()
        expect(painel.get_by_test_id("analise-criterios-onde-marcados")).to_be_enabled()
        expect(painel.get_by_text("Os marcados na lista (144)", exact=True)).to_be_visible()
        expect(painel.get_by_test_id("analise-criterios-ir-lista")).to_have_count(0)
        aperta(painel.get_by_test_id("analise-criterios-cancelar"))
        expect(territorios.get_by_test_id("analise-criterios")).to_have_count(0)

        # 10. "Agrupar os marcados" (item 9.2): cinco municípios marcados na lista → "Agrupar territórios" com eles → o mini mapa que
        #     escolhe (item 7.8: tocar num ponto cinza põe; num cheio, tira; o contorno e a extensão mudam) → "Criar conjunto"
        #     ("Conjunto A", item 8.2) → o nome editado pelo ✎ vale em "Na análise" e no mini mapa dos conjuntos (itens 8.3 e 7.9);
        #     dois conjuntos não ficam com o mesmo nome; no mapa da análise, o contorno tracejado com o nome (item 7.10).
        aperta(area.get_by_test_id("analise-limpar-selecao"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        if linha_pa.get_attribute("data-aberto") != "true":
            aperta(linha_pa.get_by_test_id("analise-grupo-ver"))
        expect(linha_pa).to_have_attribute("data-aberto", "true")
        unidades_pa = linha_pa.get_by_test_id("analise-unidade")
        for indice in range(4):
            marcado(unidades_pa.nth(indice).locator("input"))
        analise(lambda: marcado(unidades_pa.nth(4).locator("input")),
                condicao=lambda o: len(((o.get("base") or {}).get("municipios") or {}).get("ids") or []) == 5)
        agrupar_marcados = territorios.get_by_test_id("analise-agrupar-marcados")
        expect(agrupar_marcados).to_have_text("Agrupar os marcados (5)")
        aperta(agrupar_marcados)
        expect(modos.get_by_test_id("analise-modo-agrupar")).to_have_attribute("aria-checked", "true")
        expect(territorios.get_by_test_id("analise-modo-lista-conteudo")).to_be_hidden()
        agregar = territorios.get_by_test_id("analise-agregar")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(5)
        expect(agregar.get_by_test_id("analise-agregar-nome")).to_have_value("Conjunto A")
        resumo = agregar.get_by_test_id("analise-agregar-resumo")
        expect(resumo).to_have_text(re.compile(r"^5 municípios · [\d.]+ km de ponta a ponta$"), timeout=180000)
        km_antes = resumo.inner_text().split(" · ")[1]
        mini = agregar.get_by_test_id("analise-mapa-conjuntos")
        expect(mini).to_be_visible(timeout=180000)
        contorno = agregar.get_by_test_id("analise-mapa-contorno")
        expect(contorno).to_have_count(1)
        contorno_antes = contorno.get_attribute("d")
        # O ponto cinza mais longe do centro dos escolhidos fica fora do contorno: ao entrar, o contorno muda.
        longe = mini.evaluate("""fig => {
          const pontos = [...fig.querySelectorAll('[data-testid=analise-mapa-ponto]')].map(c => ({id: c.dataset.id, papel: c.dataset.papel,
            x: Number(c.getAttribute('cx')), y: Number(c.getAttribute('cy'))}));
          const membros = pontos.filter(p => p.papel === 'membro');
          const cx = membros.reduce((s, p) => s + p.x, 0) / membros.length, cy = membros.reduce((s, p) => s + p.y, 0) / membros.length;
          const fundo = pontos.filter(p => p.papel === 'fundo');
          fundo.sort((a, b) => Math.hypot(b.x - cx, b.y - cy) - Math.hypot(a.x - cx, a.y - cy));
          return fundo.length ? fundo[0].id : null; }""")
        assert longe, "o mini mapa mostra, em cinza, os demais municípios do Pará"
        ponto = agregar.locator('[data-testid="analise-mapa-ponto"][data-id="' + longe + '"]')
        ponto.dispatch_event("click")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(6)
        expect(ponto).to_have_attribute("data-papel", "membro")
        expect(resumo).to_have_text(re.compile(r"^6 municípios · [\d.]+ km de ponta a ponta · .+ entrou no conjunto\.$"), timeout=180000)
        assert resumo.inner_text().split(" · ")[1] != km_antes, (km_antes, resumo.inner_text())
        assert contorno.get_attribute("d") != contorno_antes, "o contorno muda com o ponto novo"
        ponto.dispatch_event("click")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(5)
        expect(ponto).to_have_attribute("data-papel", "fundo")
        expect(resumo).to_contain_text("saiu do conjunto.")
        _, enviado = analise(lambda: aperta(agregar.get_by_test_id("analise-agregar-criar")),
                             condicao=lambda o: bool(o.get("conjuntos")))
        assert [c["rotulo"] for c in enviado["conjuntos"]] == ["Conjunto A"] and len(enviado["conjuntos"][0]["membros"]) == 5, \
            enviado["conjuntos"]
        expect(modos.get_by_test_id("analise-modo-lista")).to_have_attribute("aria-checked", "true")
        expect(territorios.get_by_test_id("analise-agregar")).to_have_count(0)
        texto_do_conjunto = territorios.get_by_test_id("analise-selecionado-conjunto-texto")
        expect(texto_do_conjunto).to_contain_text("Conjunto A · conjunto · 5 municípios", timeout=60000)
        aperta(territorios.get_by_test_id("analise-selecionado-conjunto-editar"))
        agregar = territorios.get_by_test_id("analise-agregar")
        expect(agregar.get_by_test_id("analise-agregar-criar")).to_have_text("Salvar conjunto")
        agregar.get_by_test_id("analise-agregar-nome").fill("Paraenses do A")
        aperta(agregar.get_by_test_id("analise-agregar-criar"))
        expect(texto_do_conjunto).to_contain_text("Paraenses do A · conjunto · 5 municípios", timeout=60000)
        ver_no_mapa = territorios.get_by_test_id("analise-ver-conjuntos-no-mapa")
        expect(ver_no_mapa).to_be_visible(timeout=180000)
        aperta(ver_no_mapa)
        expect(territorios.get_by_test_id("analise-selecionados").get_by_test_id("analise-mapa-contorno")).to_have_attribute(
            "data-nome", "Paraenses do A")
        aperta(ver_no_mapa)
        aperta(modos.get_by_test_id("analise-modo-agrupar"))
        agregar = territorios.get_by_test_id("analise-agregar")
        expect(agregar.get_by_test_id("analise-agregar-nome")).to_have_value("Conjunto A")
        agregar.get_by_test_id("analise-agregar-nome").fill("paraenses do a")
        expect(agregar.get_by_test_id("analise-agregar-nome-repetido")).to_have_text("Já existe um conjunto com esse nome na análise.")
        expect(agregar.get_by_test_id("analise-agregar-criar")).to_be_disabled()
        aperta(agregar.get_by_test_id("analise-agregar-cancelar"))
        expect(territorios.get_by_test_id("analise-agregar")).to_have_count(0)
        expect(modos.get_by_test_id("analise-modo-lista")).to_have_attribute("aria-checked", "true")
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        aperta(area.get_by_test_id("analise-desenho-mapa"))
        expect(area.get_by_test_id("mapa-analise").get_by_test_id("mapa-simbolos")).to_contain_text(
            "contorno tracejado com o nome", timeout=180000)
        page.screenshot(path=str(OUTPUT / "criterios-contorno-no-mapa-real.png"), full_page=True)
        aperta(area.get_by_test_id("analise-desenho-grafico"))
        aperta(area.get_by_test_id("analise-aba-territorios"))

        # 11. O exemplo do objetivo, sem passar pela lista: Por critérios → Norte → densidade abaixo de 0,5 → agrupar a até 100 km
        #     entre si → só os conjuntos na análise (sem os sem conjunto, item 5.3; no lugar da seleção atual, as letras recomeçam) →
        #     Análise Espacial (a aba Base com os conjuntos, item 6.4) → Referência com densidade a partir de 1 → cada conjunto com a
        #     menor e a maior distância e a referência do membro mais próximo (itens 6.2 e 6.6).
        aperta(modos.get_by_test_id("analise-modo-criterios"))
        painel = territorios.get_by_test_id("analise-criterios")
        marcado(painel.get_by_test_id("analise-criterios-onde-regioes"))
        expect(painel.get_by_test_id("analise-criterios-estado")).to_have_text("Escolha ao menos uma região.")
        marcado(painel.locator('[data-testid="analise-criterios-onde-regiao"][data-id="1"]'))
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        painel.get_by_test_id("analise-criterio-valor").fill("0,5")
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        corpo, pedido = previa(lambda: painel.get_by_test_id("analise-criterios-agrupar-km").fill("100"),
                               condicao=lambda o: (o.get("agrupar") or {}).get("km") == 100)
        assert pedido["criterios"]["partir_de"]["tipo"] == "ufs" and sorted(pedido["criterios"]["partir_de"]["ufs"]) == [
            "11", "12", "13", "14", "15", "16", "17"], pedido["criterios"]
        grupos_norte = corpo["grupos"]
        assert grupos_norte and len(grupos_norte) <= 50 and all(g["extensao_km"] <= 100 for g in grupos_norte), \
            [g["extensao_km"] for g in grupos_norte]
        sem_conjunto = len(corpo["isolados"]) + len(corpo["sem_posicao"] or [])
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text(
            str(corpo["atendem"]) + " atendem · " + str(len(grupos_norte)) + " conjunto")
        expect(painel.get_by_test_id("analise-criterios-resumo")).to_contain_text(str(sem_conjunto) + " sem conjunto")
        expect(painel.get_by_test_id("analise-criterios-no-lugar")).to_be_checked()
        desmarcado(painel.get_by_test_id("analise-criterios-sem-conjunto"))
        resposta, enviado = analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-grupos")),
                                    condicao=lambda o: len(o.get("conjuntos") or []) == len(grupos_norte))
        assert [c["rotulo"] for c in enviado["conjuntos"]][:2] == ["Conjunto A", "Conjunto B"][:len(grupos_norte)], enviado["conjuntos"]
        assert all(item["tipo"] == "conjunto" for item in resposta["itens"]), [item["tipo"] for item in resposta["itens"]]
        expect(territorios.get_by_test_id("analise-selecionado-conjunto")).to_have_count(len(grupos_norte))
        aperta(area.get_by_test_id("analise-familia-espacial"))
        janela = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
        expect(janela).to_be_visible(timeout=60000)
        expect(janela.get_by_test_id("territorios-base-selecao-texto")).to_have_text("A base são os conjuntos da seleção em uso.",
                                                                                     timeout=180000)
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
        assert len(conjuntos_espaciais) == len(grupos_norte) == len(espacial["itens"]), [item["tipo"] for item in espacial["itens"]]
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

        # 12. Os conjuntos nas comparações (comando de 08/11/2026). Primeiro, os quintis: com dez municípios do Pará marcados, criar um
        #     conjunto deles que não fica no lugar dos membros não muda os cortes dos quintis do mapa (só as unidades entram). Depois,
        #     o Norte a até 100 km, "Usar cada conjunto como um território" junto com os dez: ordenar por densidade põe os conjuntos
        #     entre os municípios, cada um no lugar do seu valor; "densidade abaixo de 0,4" inclui ou deixa fora cada conjunto pelo
        #     valor, e a contagem separa municípios e conjuntos; na Análise Espacial, com as faixas 0; 100; 300, cada conjunto fica na
        #     faixa da sua menor distância, e ordenar pela distância o põe entre as unidades.
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
        aperta(area.get_by_test_id("analise-limpar-selecao"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        if linha_pa.get_attribute("data-aberto") != "true":
            aperta(linha_pa.get_by_test_id("analise-grupo-ver"))
        unidades_pa = linha_pa.get_by_test_id("analise-unidade")
        for indice in range(9):
            marcado(unidades_pa.nth(indice).locator("input"))
        antes, _ = analise(lambda: marcado(unidades_pa.nth(9).locator("input")),
                           condicao=lambda o: len(((o.get("base") or {}).get("municipios") or {}).get("ids") or []) == 10)
        assert antes["grupos_mapa"] and antes["grupos_mapa"]["universo"] == 10, antes.get("grupos_mapa")
        aperta(territorios.get_by_test_id("analise-agrupar-marcados"))
        agregar = territorios.get_by_test_id("analise-agregar")
        desmarcado(agregar.get_by_test_id("analise-agregar-substitui"))
        com_conjunto, enviado = analise(lambda: aperta(agregar.get_by_test_id("analise-agregar-criar")),
                                        condicao=lambda o: bool(o.get("conjuntos")))
        assert len(enviado["base"]["municipios"]["ids"]) == 10, enviado["base"]  # os membros continuam na análise
        assert com_conjunto["grupos_mapa"]["cortes"] == antes["grupos_mapa"]["cortes"], (com_conjunto["grupos_mapa"], antes["grupos_mapa"])
        assert com_conjunto["grupos_mapa"]["universo"] == 10
        assert all(item["grupo_mapa"] is None for item in com_conjunto["itens"] if item["tipo"] == "conjunto")
        aperta(territorios.get_by_role("button", name="Desfazer o conjunto Conjunto A", exact=True))
        expect(territorios.get_by_test_id("analise-selecionado-conjunto")).to_have_count(0)
        # O Norte a até 100 km, junto com os dez do Pará.
        aperta(modos.get_by_test_id("analise-modo-criterios"))
        painel = territorios.get_by_test_id("analise-criterios")
        marcado(painel.get_by_test_id("analise-criterios-onde-regioes"))
        marcado(painel.locator('[data-testid="analise-criterios-onde-regiao"][data-id="1"]'))
        painel.get_by_test_id("analise-criterio-atributo").select_option("densidade")
        painel.get_by_test_id("analise-criterio-operador").select_option("<")
        painel.get_by_test_id("analise-criterio-valor").fill("0,5")
        marcado(painel.get_by_test_id("analise-criterios-agrupar"))
        corpo, _ = previa(lambda: painel.get_by_test_id("analise-criterios-agrupar-km").fill("100"),
                          condicao=lambda o: (o.get("agrupar") or {}).get("km") == 100)
        n_norte = len(corpo["grupos"])
        marcado(painel.get_by_test_id("analise-criterios-junto"))
        junto, _ = analise(lambda: aperta(painel.get_by_test_id("analise-criterios-como-grupos")),
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
        # Na Análise Espacial (a Escolha dos territórios do passo 11), as faixas 0; 100; 300 e a ordem pela distância.
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

        # 13. Nenhum "cluster" à vista.
        assert "cluster" not in page.evaluate("() => document.body.innerText").lower()
        page.screenshot(path=str(OUTPUT / "criterios-conjuntos-real.png"), full_page=True)
        assert not falhas, falhas
        assert not chamadas_llm, chamadas_llm
        browser.close()
    print("CRITÉRIOS PASS: os modos da Seleção (uma ferramenta por vez), a prévia sozinha (densidade abaixo de 0,5 em jun/2024: 89; "
          "o valor incompleto esmaecido; 0,7 sem clicar), os conjuntos todos a até 200 km entre si com os contornos no mini mapa, "
          "\"Usar como seleção (89)\" com a trilha, a regra e os Detalhes, as Condições nos marcados, \"Usar cada conjunto como um "
          "território\" no lugar e junto (o Pará a até 100 km: os conjuntos da referência do comando, com as letras continuando), "
          "o Pará só pela distância (50 km), o pedido pela conversa sem mudar a análise até a confirmação, as regiões na árvore, o "
          "lugar em uso pré-escolhido, \"Agrupar os marcados\" com o mini mapa que escolhe, os nomes únicos, o contorno no mapa e o "
          "exemplo do objetivo (o Norte a até 100 km até a Análise Espacial, com a distância e a referência de cada conjunto); "
          "os conjuntos nas comparações (quintis sem mudança, a ordem, a condição e as faixas de distância com os conjuntos "
          "pelo valor de cada um); nenhum \"cluster\" (base versionada).")


if __name__ == "__main__":
    main()
