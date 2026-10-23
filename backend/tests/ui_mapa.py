"""Mapa da página única (23/10/2026), com a base versionada (somente leitura): a segunda vista do gráfico.

Confere, contra as respostas de /api/painel e de /api/painel/mapa: nos estados, o mapa desligado, com o motivo e o atalho para os
municípios (os ladrilhos dos estados não foram aprovados); os pontos do motor (sede municipal, IBGE) e o fundo com as demais
unidades; a pergunta "Como pintar o mapa?" (decisão de 23/10), a cor contínua linear por padrão (logarítmica só por escolha), os
quintis do motor com a mesma contagem por cor, a régua que esmaece sem esconder (decisão de 23/10), a seleção e a dica iguais às do
gráfico, o zoom com o mapinha do canto, o mapinha na dica do gráfico, o convite depois das Condições, as ligações ilustrativas da
análise espacial, o lado a lado em telas largas (sem legenda repetida), o Histórico que reabre a análise no mapa sem recalcular e
o celular. Nenhuma cor, classe ou contagem é criada na tela: tudo vem do motor. Servidor serve_ui_offline.py; nunca chama o
provedor de IA.
"""
import json
import os
import re
from collections import Counter
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
AM = "13"  # prefixo IBGE do Amazonas
GANCHO = """() => { const m = window.__adtMapa; if (!m) return null;
  return { pintura: m.pintura, escala: m.escala, dominio: m.dominio, contexto: m.contexto, esmaecidos: m.esmaecidos,
           brasil: m.brasil, largura: m.largura, altura: m.altura, vista: m.vista, desenhos: m.desenhos, pontos: m.pontos }; }"""


def options_of(request):
    return json.loads(request.post_data.split('name="options"\r\n\r\n', 1)[1].split("\r\n--", 1)[0])


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "o roteiro do mapa usa a base versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, llm_calls, painel_calls, mapa_calls, pedidos = [], [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: painel_calls.append(request.url) if request.url.endswith("/api/painel") else None)
        page.on("request", lambda request: pedidos.append(request)
                if request.url.endswith("/api/painel") and request.method == "POST" else None)
        page.on("request", lambda request: mapa_calls.append(request) if request.url.endswith("/api/painel/mapa") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        mapa = area.get_by_test_id("mapa-analise")
        territorios = area.get_by_test_id("analise-territorios")

        def shot(name):
            page.wait_for_timeout(700)
            page.screenshot(path=str(OUTPUT / ("mapa-" + name + "-real.png")), full_page=True)

        def respond(action, timeout=180000):
            """A resposta de /api/painel e as opções do pedido feito pela ação. Só vale um pedido feito depois do início da ação: a
            resposta de um pedido anterior ainda em curso (o "Limpar" das Condições pede ao motor sem que o roteiro espere) pode
            chegar depois e não é a desta ação."""
            antes = len(pedidos)
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST"
                                      and any(r.request is pedido for pedido in pedidos[antes:]), timeout=timeout) as event:
                action()
            return event.value, options_of(event.value.request)

        def ok(action, timeout=180000):
            response, sent = respond(action, timeout)
            assert response.status == 200, response.text()[:2000]
            return response.json(), sent

        def aperta(locator):
            """Botões pelo teclado (também os aria-disabled, que mostram o motivo), como nos outros roteiros."""
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Enter")

        def marca(locator):
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Space")

        def abre(funcao):
            botao = area.get_by_test_id("analise-funcao-" + funcao)
            if botao.get_attribute("aria-expanded") != "true":
                aperta(botao)
            painel = area.get_by_test_id("analise-painel")
            expect(painel).to_have_attribute("data-painel", funcao)
            return painel

        def fecha():
            if area.get_by_test_id("analise-painel").count():
                aperta(area.get_by_test_id("analise-painel-fechar"))
                expect(area.get_by_test_id("analise-painel")).to_have_count(0)

        def gancho():
            return page.evaluate(GANCHO)

        def desenhado(pontos, pintura=None, timeout=60000):
            """Espera o mapa à vista com `pontos` pontos do resultado (e a pintura pedida) e devolve o gancho de teste."""
            expect(mapa).to_be_visible(timeout=timeout)
            expect(mapa).to_have_attribute("data-pontos", str(pontos), timeout=timeout)
            if pintura:
                expect(mapa).to_have_attribute("data-pintura", pintura, timeout=timeout)
            page.wait_for_function("([n, pintura]) => { const m = window.__adtMapa; return !!m && m.largura > 0 && "
                                   "m.pontos.length === n && (!pintura || m.pintura === pintura); }", arg=[pontos, pintura], timeout=timeout)
            return gancho()

        def com_ponto(body, dados):
            """Itens que o mapa desenha: unidades com densidade e com coordenada válida (estados e conjuntos não têm ponto)."""
            return [item for item in body["itens"] if item["tipo"] == "municipio" and item.get("densidade") is not None
                    and item["id"] in dados]

        def estavel():
            """O gancho depois de o desenho assentar. Fechar um painel devolve a largura ao desenho (com a janela larga, o painel
            ocupa uma coluna ao lado): o canvas cresce e o mapa se reenquadra logo depois. Vale quando duas leituras seguidas
            têm o mesmo tamanho, a mesma vista e o mesmo número de desenhos."""
            anterior = None
            for _ in range(40):
                atual = gancho()
                chave = atual and json.dumps([atual["largura"], atual["altura"], atual["vista"], atual["desenhos"]], sort_keys=True)
                if chave and chave == anterior:
                    return atual
                anterior = chave
                page.wait_for_timeout(250)
            raise AssertionError("o desenho do mapa não assentou")

        def alcancaveis(pontos):
            """Ids dos pontos em que o clique cai no próprio canvas (sem legenda, controle, pergunta ou conversa por cima)."""
            return set(mapa.get_by_test_id("mapa-canvas").evaluate(
                "(c, pontos) => { const caixa = c.getBoundingClientRect(); return pontos.filter(p => "
                "document.elementFromPoint(caixa.left + p.x, caixa.top + p.y) === c).map(p => p.id); }", pontos))

        def ponto_isolado(pontos, evitar=(), livres=None):
            """O ponto à vista mais longe dos vizinhos (o clique e o mouse acertam só ele), entre os `livres` quando dados."""
            candidatos = [p for p in pontos if p["naTela"] and not p["esmaecido"] and p["id"] not in evitar
                          and (livres is None or p["id"] in livres)]
            assert candidatos, "há pontos à vista no mapa"

            def folga(p):
                return min(((p["x"] - q["x"]) ** 2 + (p["y"] - q["y"]) ** 2) ** 0.5 - q["r"] - p["r"]
                           for q in pontos if q["id"] != p["id"] and q["naTela"])
            return max(candidatos, key=folga)

        def no_canvas(ponto):
            canvas = mapa.get_by_test_id("mapa-canvas")
            canvas.evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})")
            caixa = canvas.bounding_box()
            return caixa["x"] + ponto["x"], caixa["y"] + ponto["y"]

        # A caixa da conversa, se estiver aberta, fica minimizada enquanto o roteiro usa o mapa.
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. Estados (E1): o mapa desligado, com o motivo (os estados não têm um ponto) e o atalho; nada é pedido ao motor.
        estados, _ = ok(lambda: area.get_by_test_id("analise-fonte-brasil").click())
        expect(area).to_have_attribute("data-estado", "E1")
        expect(area).to_have_attribute("data-desenho", "grafico")
        botao_mapa = area.get_by_test_id("analise-desenho-mapa")
        expect(botao_mapa).to_have_attribute("aria-disabled", "true")
        aperta(botao_mapa)
        motivo = area.get_by_test_id("analise-desenho-motivo")
        expect(motivo).to_contain_text("Os estados não têm um ponto no mapa")
        expect(area).to_have_attribute("data-desenho", "grafico")
        assert not mapa_calls, "nos estados, nada é pedido ao endpoint do mapa"

        # 2. O atalho leva a todos os municípios do Brasil, já no mapa: os pontos do motor (sede municipal), o fundo, a pergunta.
        with page.expect_response(lambda r: r.url.endswith("/api/painel/mapa") and r.request.method == "POST", timeout=180000) as evento:
            brasil, sent = ok(lambda: aperta(motivo.get_by_test_id("analise-desenho-atalho")))
        assert sent["base"] == {"municipios": {"todos": True, "estados": [], "ids": []}}, sent
        resposta_mapa = evento.value
        assert resposta_mapa.status == 200, resposta_mapa.text()[:2000]
        dados_mapa = resposta_mapa.json()
        assert options_of(resposta_mapa.request) == {"competencia": brasil["competencia"], "categoria": brasil["categoria"]}, \
            options_of(resposta_mapa.request)
        assert dados_mapa["competencia"] == brasil["competencia"] and dados_mapa["referencial"] == "SIRGAS2000", dados_mapa["referencial"]
        pontos_motor = {ponto["id"]: (ponto["lat"], ponto["lon"]) for ponto in dados_mapa["pontos"]}
        assert len(pontos_motor) > 5000, len(pontos_motor)
        assert all(-34 <= lat <= 6 and -74 <= lon <= -28 for lat, lon in pontos_motor.values()), "coordenadas dentro do Brasil"
        sem_coordenada = {item["id"] for item in dados_mapa["sem_coordenada"]}
        municipios_brasil = {item["id"] for item in brasil["itens"] if item["tipo"] == "municipio"}
        assert municipios_brasil <= set(pontos_motor) | sem_coordenada, "cada município tem ponto ou motivo"
        expect(area).to_have_attribute("data-desenho", "mapa")
        expect(area.get_by_test_id("analise-vista-mapa")).to_be_visible()
        expect(area.get_by_test_id("analise-desenho-mapa")).to_have_attribute("aria-pressed", "true")
        desenhaveis = com_ponto(brasil, pontos_motor)
        estado = desenhado(len(desenhaveis), "pergunta")
        assert estado["contexto"] == len(set(pontos_motor) - {item["id"] for item in desenhaveis}), estado["contexto"]
        expect(mapa).to_have_attribute("data-escala", "nenhuma")
        expect(mapa.get_by_test_id("mapa-nota")).to_contain_text("sede do município")
        pergunta = mapa.get_by_test_id("mapa-pergunta")
        expect(pergunta).to_be_visible()
        expect(pergunta.get_by_test_id("mapa-pergunta-quintis")).to_have_attribute("data-recomendado", "true")
        for opcao in ("faixas", "continua"):
            expect(pergunta.get_by_test_id("mapa-pergunta-" + opcao)).to_be_visible()
        expect(mapa.get_by_test_id("mapa-legenda")).to_have_attribute("data-tipo", "pergunta")
        shot("01-brasil-pergunta")

        # 3. Cor contínua: estado visual (nada é pedido ao motor), linear por padrão; logarítmica só por escolha.
        calls = len(painel_calls)
        aperta(pergunta.get_by_test_id("mapa-pergunta-continua"))
        estado = desenhado(len(desenhaveis), "continua")
        expect(mapa).to_have_attribute("data-escala", "linear")
        legenda = mapa.get_by_test_id("mapa-legenda")
        expect(legenda).to_have_attribute("data-tipo", "continua")
        expect(legenda.get_by_test_id("mapa-legenda-aviso")).to_contain_text("não é classe nem limiar")
        assert estado["dominio"] == brasil["dominios"]["densidade"], (estado["dominio"], brasil["dominios"]["densidade"])
        assert len({ponto["cor"] for ponto in estado["pontos"]}) > 3, "a cor contínua varia com o valor"
        escala = area.get_by_test_id("analise-escala")
        expect(escala).to_have_value("linear")
        escala.select_option("logaritmica")
        expect(mapa).to_have_attribute("data-escala", "logaritmica")
        escala.select_option("linear")
        expect(mapa).to_have_attribute("data-escala", "linear")
        page.wait_for_timeout(300)
        assert len(painel_calls) == calls, "a cor contínua e a escala da cor não pedem nada ao motor"
        shot("02-brasil-continua")

        # 4. Amazonas pela lista: o mapa enquadra o estado, com o restante do Brasil ao fundo; os mesmos pontos (sem novo pedido).
        pedidos_mapa = len(mapa_calls)
        linha_am = territorios.locator('[data-testid="analise-grupo"][data-id="' + AM + '"]')
        am, sent = ok(lambda: aperta(linha_am.get_by_test_id("analise-grupo-ver")))
        assert sent["base"] == {"municipios": {"todos": False, "estados": [AM], "ids": []}}, sent
        desenhaveis_am = com_ponto(am, pontos_motor)
        estado = desenhado(len(desenhaveis_am), "continua")
        assert estado["contexto"] == len(set(pontos_motor) - {item["id"] for item in desenhaveis_am}), estado["contexto"]
        assert len(mapa_calls) == pedidos_mapa, "os pontos da mesma competência vêm da memória"
        ids_am = {item["id"] for item in desenhaveis_am}
        assert {ponto["id"] for ponto in estado["pontos"]} == ids_am

        # 5. Quintis do motor: o mapa pinta como o gráfico, com a mesma contagem por cor que o motor devolveu por grupo.
        quintis, sent = ok(lambda: area.get_by_test_id("analise-ajustes").get_by_test_id("analise-agrupar").select_option("quintis"))
        assert sent["grupos"] == {"tipo": "quintis"}, sent
        estado = desenhado(len(desenhaveis_am), "camada")
        expect(mapa.get_by_test_id("mapa-legenda")).to_have_attribute("data-tipo", "camada")
        por_grupo = Counter(item["grupo"]["indice"] for item in quintis["itens"] if item["id"] in ids_am and item.get("grupo"))
        por_cor = Counter(ponto["cor"] for ponto in estado["pontos"] if not ponto["vazada"])
        assert sorted(por_cor.values()) == sorted(por_grupo.values()), (por_cor, por_grupo)
        assert area.get_by_test_id("analise-legenda-cor").count() <= 1, "a legenda das cores não se repete"
        shot("03-am-quintis")
        area.get_by_test_id("analise-ajustes").get_by_test_id("analise-agrupar").select_option("nenhum")
        estado = desenhado(len(desenhaveis_am), "continua")

        # 6. Régua no mapa: esmaece o que fica fora do corte, sem esconder (decisão de 23/10); nada é recalculado.
        calls = len(painel_calls)
        regua = abre("regua").get_by_test_id("analise-regua")
        cursor = regua.get_by_test_id("analise-regua-min")
        cursor.focus()
        for _ in range(3):
            cursor.press("PageUp")
        minimo = float(cursor.get_attribute("aria-valuenow"))
        maximo = float(regua.get_by_test_id("analise-regua-max").get_attribute("aria-valuenow"))
        fora = [item for item in desenhaveis_am if not minimo <= item["densidade"] <= maximo]
        assert fora, "o corte deixa municípios de fora"
        expect(mapa).to_have_attribute("data-esmaecidos", str(len(fora)), timeout=10000)
        expect(mapa).to_have_attribute("data-pontos", str(len(desenhaveis_am)))
        estado = gancho()
        assert {ponto["id"] for ponto in estado["pontos"] if ponto["esmaecido"]} == {item["id"] for item in fora}
        assert len(painel_calls) == calls, "a régua só esmaece: nada é recalculado"
        aperta(regua.get_by_test_id("analise-regua-limpar"))
        expect(mapa).to_have_attribute("data-esmaecidos", "0", timeout=10000)
        fecha()

        # 7. Clique no ponto: marca, como na bolha; o mouse mostra a mesma dica do gráfico. O painel da régua acabou de fechar:
        # o ponto é escolhido com o desenho já assentado e entre os que o clique alcança.
        mapa.get_by_test_id("mapa-canvas").evaluate("e => e.scrollIntoView({block: 'center', behavior: 'instant'})")
        estado = estavel()
        alvo = ponto_isolado(estado["pontos"], livres=alcancaveis(estado["pontos"]))
        x, y = no_canvas(alvo)
        page.mouse.click(x, y)
        page.wait_for_function("id => (window.__adtMapa?.pontos || []).some(p => p.id === id && p.selecionado)", arg=alvo["id"], timeout=10000)
        rotulo = next(item["rotulo"] for item in am["itens"] if item["id"] == alvo["id"])
        page.mouse.move(x, y + 1)
        dica = mapa.get_by_test_id("mapa-dica")
        expect(dica).to_be_visible(timeout=5000)
        expect(dica).to_contain_text(rotulo)
        page.mouse.move(2, 2)

        # 8. Zoom: o mapinha do canto aparece; "Ver tudo" volta ao enquadramento inicial.
        aperta(mapa.get_by_test_id("mapa-ampliar"))
        aperta(mapa.get_by_test_id("mapa-ampliar"))
        page.wait_for_function("() => (window.__adtMapa?.vista?.zoom || 1) > 1.5", timeout=10000)
        expect(mapa.get_by_test_id("minimapa").first).to_be_visible()
        aperta(mapa.get_by_test_id("mapa-ver-tudo"))
        page.wait_for_function("() => Math.abs((window.__adtMapa?.vista?.zoom || 0) - 1) < 0.01", timeout=10000)
        shot("04-am-selecao")

        # 9. De volta ao gráfico: a mesma seleção; a dica da bolha mostra o mapinha ("onde fica?").
        aperta(area.get_by_test_id("analise-desenho-grafico"))
        expect(area).to_have_attribute("data-desenho", "grafico")
        bolha = area.locator('[data-testid="analise-bolha"][data-id="' + alvo["id"] + '"]')
        expect(bolha).to_have_attribute("data-selecionado", "true", timeout=10000)
        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start', behavior: 'instant'})")
        maior = max(desenhaveis_am, key=lambda item: item["populacao"] or 0)
        area.locator('[data-testid="analise-bolha"][data-id="' + maior["id"] + '"]').hover()
        dica_grafico = area.get_by_test_id("analise-dica")
        expect(dica_grafico).to_contain_text(maior["rotulo"])
        expect(dica_grafico.get_by_test_id("minimapa")).to_be_visible()
        page.mouse.move(2, 2)
        marca(area.locator('[data-testid="analise-linha"][data-id="' + alvo["id"] + '"] input[type=checkbox]'))
        expect(bolha).not_to_have_attribute("data-selecionado", "true")

        # 10. Condições no gráfico: o convite leva ao mapa, pintado como o gráfico (quem atende, quem não atende, sem dado).
        densidades = sorted(item["densidade"] for item in desenhaveis_am)
        limiar = round(densidades[len(densidades) // 2], 2)
        condicoes = abre("condicoes").get_by_test_id("analise-condicoes")
        condicoes.get_by_test_id("analise-condicao-atributo").select_option("densidade")
        condicoes.get_by_test_id("analise-condicao-operador").select_option("<")
        condicoes.get_by_test_id("analise-condicao-valor").fill(str(limiar).replace(".", ","))
        filtrado, _ = ok(lambda: aperta(condicoes.get_by_test_id("analise-condicoes-aplicar")))
        fecha()
        convite = area.get_by_test_id("analise-convite-mapa")
        expect(convite).to_have_text("Ver onde ficam no mapa")
        aperta(convite)
        expect(area).to_have_attribute("data-desenho", "mapa")
        estado = desenhado(len(desenhaveis_am), "camada")
        por_situacao = Counter(item["condicoes"]["situacao"] for item in filtrado["itens"] if item["id"] in ids_am and item.get("condicoes"))
        por_cor = Counter(ponto["cor"] for ponto in estado["pontos"] if not ponto["vazada"])
        assert sorted(por_cor.values()) == sorted(n for situacao, n in por_situacao.items() if situacao != "NAO_AVALIAVEL"), (por_cor, por_situacao)
        shot("05-am-condicoes")
        aperta(abre("condicoes").get_by_test_id("analise-condicoes").get_by_test_id("analise-condicoes-limpar"))
        fecha()
        estado = desenhado(len(desenhaveis_am), "continua")

        # 11. Análise espacial no mapa: a referência do motor e as ligações ilustrativas dos marcados (até 30).
        aperta(area.get_by_test_id("analise-familia-espacial"))
        referencia = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
        expect(referencia).to_be_visible()
        referencia.get_by_test_id("analise-ref-criterio").select_option("densidade")
        referencia.get_by_test_id("analise-ref-ordem").select_option("desc")
        with page.expect_response(lambda r: r.url.endswith("/api/painel/referencias"), timeout=120000) as lista_evento:
            aperta(referencia.get_by_test_id("analise-ref-listar"))
        lista = lista_evento.value.json()
        primeiros = [item for item in lista["candidatos"] if item["posicao"] == 1]
        if len(primeiros) == 1:
            espacial, _ = ok(lambda: aperta(referencia.get_by_test_id("analise-ref-primeiro")))
        else:
            aperta(referencia.get_by_test_id("analise-ref-primeiro"))
            marca(referencia.get_by_test_id("analise-ref-candidato").first.locator("input"))
            espacial, _ = ok(lambda: aperta(referencia.get_by_test_id("analise-ref-aplicar")))
        fecha()
        expect(area).to_have_attribute("data-desenho", "mapa")
        com_distancia = [item for item in com_ponto(espacial, pontos_motor) if item.get("distancia_km") is not None]
        assert com_distancia, "a análise espacial devolve distâncias"
        dois = [item["id"] for item in com_distancia if not item.get("referencia")][:2]
        for chave in dois:
            marca(area.locator('[data-testid="analise-linha"][data-id="' + chave + '"] input[type=checkbox]'))
        expect(mapa.get_by_test_id("mapa-ligacoes")).to_contain_text("ligação ilustrativa, não é trajeto")
        shot("06-am-espacial")

        # 12. Lado a lado (janela de 1.600 px ou mais): gráfico e mapa juntos, sem legenda repetida; ao estreitar, volta ao mapa.
        page.set_viewport_size({"width": 1700, "height": 1000})
        lado = area.get_by_test_id("analise-desenho-lado")
        expect(lado).to_be_visible()
        aperta(lado)
        expect(area).to_have_attribute("data-desenho", "lado")
        expect(area.get_by_test_id("analise-vista-grafico")).to_be_visible()
        expect(area.get_by_test_id("analise-vista-mapa")).to_be_visible()
        assert area.get_by_test_id("analise-legenda-cor").count() <= 1, "a legenda das cores não se repete no lado a lado"
        shot("07-lado-a-lado")
        page.set_viewport_size({"width": 1440, "height": 900})
        expect(area).to_have_attribute("data-desenho", "mapa")
        expect(area.get_by_test_id("analise-desenho-lado")).to_have_count(0)

        # 13. Nova análise volta aos estados (sem mapa); o Histórico reabre a análise espacial no mapa, sem recalcular.
        navegacao = page.get_by_test_id("main-navigation")
        navegacao.get_by_test_id("nav-new-analysis").click()  # os estados podem vir da memória: nem sempre há pedido novo
        expect(area).to_have_attribute("data-estado", "E1", timeout=60000)
        expect(area).to_have_attribute("data-desenho", "grafico")
        historico = page.get_by_test_id("nav-history")
        historico.click()
        itens = page.get_by_test_id("analysis-history-menu").get_by_test_id("historico-item")
        calls = len(painel_calls)
        itens.filter(has_text="distância até").first.click()
        expect(area).to_have_attribute("data-desenho", "mapa", timeout=30000)
        expect(mapa).to_be_visible()
        page.wait_for_timeout(1000)
        assert len(painel_calls) == calls, "reabrir do Histórico não recalcula"

        # 14. Celular (390 px): o mapa cabe na tela, sem rolagem horizontal; a escolha da vista continua à vista.
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        expect(area.get_by_test_id("analise-desenho")).to_be_visible()
        caixa = mapa.get_by_test_id("mapa-canvas").bounding_box()
        assert caixa and caixa["width"] <= 390, caixa
        page.screenshot(path=str(OUTPUT / "mapa-08-celular-real.png"), full_page=False)

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    print("MAPA PASS: estados sem mapa (motivo e atalho), pontos do motor e fundo, pergunta, cor contínua linear, quintis, régua que "
          "esmaece, seleção e dica, zoom e mapinha, mapinha na dica do gráfico, convite das Condições, ligações da análise espacial, "
          "lado a lado, Histórico e celular (base versionada).")


if __name__ == "__main__":
    main()
