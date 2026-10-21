"""Painel integrado de bolhas (21/10/2026): abrir o painel com a base do Brasil, eixo único da densidade com as bolhas iguais às
da resposta do motor, a dica ao passar o mouse e ao focar, Quantidade sem novo pedido, a régua "acima de / abaixo de" filtrando
(teclado e mouse), municípios acrescentados por busca e por arrastar, conjunto agregado como bolha (soma das contagens dos
componentes), Distância com a referência por critério ("Usar o primeiro"), Crescimento com os percentuais do motor, a caixa da
conversa arrastável (mouse e teclado) com o envio de mensagem funcionando, 390 px sem rolagem horizontal e a volta à
preparação clássica.

Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; quatro competências) ou, com ADT_BLOCK1_REAL=1, a base
versionada (somente leitura). No catálogo sintético, com quatro municípios, o painel abre com todos eles; na base versionada,
com milhares, abre sem universo e sem pedido ao motor, e o roteiro escolhe o Amazonas inteiro. No catálogo sintético, instalado
como versão externa, o referencial SIRGAS 2000 não é premissa: o motor recusa a distância (422), e o roteiro confere que a tela
mostra a recusa e volta ao último painel calculado. Com a base versionada, confere o eixo da distância. Depende das rotas
/api/painel e /api/painel/referencias (backend/painel.py). Servidor serve_ui_offline.py; nunca chama o provedor de IA.
"""
import json
import os
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, TEFE, PARINTINS = "code:130260", "code:130420", "code:130340"
AM = "13"  # prefixo IBGE do Amazonas
VISIVEIS = '[data-testid="painel-bubble"][data-visivel="true"]'


def options_of(request):
    return json.loads(request.post_data.split('name="options"\r\n\r\n', 1)[1].split("\r\n--", 1)[0])


def variacao(valor):
    """A apresentação da tela (RQ-REP-05): sinal, duas casas (mais, se o valor não nulo pareceria zero) e vírgula decimal."""
    if valor is None:
        return "Não avaliável"
    numero, casas = Decimal(repr(abs(valor))), 2
    while casas < 8 and valor != 0 and numero.quantize(Decimal(1).scaleb(-casas), ROUND_HALF_UP) == 0:
        casas += 1
    texto = f"{numero.quantize(Decimal(1).scaleb(-casas), ROUND_HALF_UP):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("+" if valor > 0 else "−" if valor < 0 else "") + texto + "%"


def esperados(body, indicador="densidade", corte=None, distancia=False):
    """Bolhas que a tela deve desenhar: itens com o indicador avaliável (e a distância, quando à vista); a régua só tira os
    municípios base fora do corte (conjuntos e referência ficam)."""
    ids = []
    for item in body["itens"]:
        valor = item[indicador]
        if valor is None or (distancia and item["distancia_km"] is None):
            continue
        if corte and item["tipo"] == "municipio" and not item["referencia"] and not corte[0] <= valor <= corte[1]:
            continue
        ids.append(item["id"])
    return sorted(ids)


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = "-real" if real else ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        failures, llm_calls, painel_calls = [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: painel_calls.append(request.url) if request.url.endswith("/api/painel") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        page.get_by_role("button", name="Usar dados do Brasil").click()
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=90000)
        painel = page.get_by_test_id("painel-integrado")
        axis_x, axis_y = painel.get_by_test_id("painel-axis-x"), painel.get_by_test_id("painel-axis-y")

        def shot(name):
            page.wait_for_timeout(900)  # transições do painel
            page.screenshot(path=str(OUTPUT / ("painel-" + name + suffix + ".png")), full_page=True)

        def respond(action, timeout=180000):
            """Executa a ação e devolve a resposta de /api/painel e as opções do mesmo pedido."""
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=timeout) as event:
                action()
            response = event.value
            return response, options_of(response.request)

        def ok(action):
            response, sent = respond(action)
            assert response.status == 200, response.text()[:2000]
            return response.json(), sent

        def drawn(ids):
            page.wait_for_function("ids => JSON.stringify([...document.querySelectorAll('[data-testid=painel-bubble][data-visivel=true]')]"
                                   ".map(e => e.dataset.id).sort()) === JSON.stringify(ids)", arg=ids, timeout=30000)

        def bubbles():
            return {item["id"]: item for item in painel.locator(VISIVEIS).evaluate_all(
                "els => els.map(e => ({id: e.dataset.id, tipo: e.dataset.tipo, valor: e.dataset.valor, populacao: e.dataset.populacao, "
                "distancia: e.dataset.distancia ?? null, variacao: e.dataset.variacao ?? null, referencia: e.dataset.referencia ?? null}))")}

        # 1. Abrir o painel: botão junto da fonte atual e na navegação principal. Sem escolha na abrangência clássica, o universo
        # inicial é o de todos os municípios numa base pequena; com milhares (base versionada), o painel espera a escolha.
        expect(page.get_by_test_id("main-navigation").locator(':scope > button')).to_have_count(5)
        expect(page.get_by_test_id("nav-painel")).to_have_text("Painel integrado")
        base = painel.get_by_test_id("painel-base")
        if real:
            page.get_by_test_id("open-painel").click()
            expect(painel.get_by_test_id("painel-vazio")).to_be_visible()
            page.wait_for_timeout(600)
            assert not painel_calls, "universo vazio: nenhum pedido ao motor"
            universo = {"municipios": {"todos": False, "estados": [AM], "ids": []}}
            body, sent = ok(lambda: base.get_by_test_id("painel-base-estado").select_option(AM))
            expect(base.locator('[data-testid="painel-base-chip"][data-id="uf:' + AM + '"]')).to_be_visible()
        else:
            universo = {"municipios": {"todos": True, "estados": [], "ids": []}}
            body, sent = ok(lambda: page.get_by_test_id("open-painel").click())
        expect(painel).to_be_visible()
        expect(page.get_by_test_id("nav-painel")).to_have_attribute("aria-current", "page")
        assert sent["base"] == universo, sent
        assert set(sent) == {"competencia", "categoria", "base"}, sent  # opções estritas do contrato, nada além
        assert body["competencia"] == sent["competencia"] and body["competencia_inicial"] is None
        expect(painel.get_by_test_id("painel-competencia")).to_have_value(sent["competencia"])
        # A caixa da conversa fica minimizada enquanto o roteiro usa o gráfico (no canto, aberta, ela cobriria bolhas e a
        # régua); o passo 9 a abre de novo.
        chat = page.get_by_test_id("painel-chat")
        chat.get_by_test_id("painel-chat-minimizar").click()
        expect(chat).to_have_attribute("data-minimizada", "true")
        expect(chat.locator("#assistant-input")).to_be_hidden()

        # 2. Densidade: eixo único, bolhas iguais às da resposta (valor, tipo e população do motor) e a altura como arranjo.
        expect(axis_x).to_have_attribute("data-eixo", "densidade")
        expect(axis_y).to_have_count(0)
        expect(painel.get_by_test_id("painel-arranjo-nota")).to_contain_text("arranjo visual")
        ids = esperados(body)
        drawn(ids)
        desenhadas = bubbles()
        for item in body["itens"]:
            if item["id"] in ids:
                bolha = desenhadas[item["id"]]
                assert float(bolha["valor"]) == item["densidade"] and bolha["tipo"] == item["tipo"], (bolha, item)
                assert bolha["populacao"] == ("" if item["populacao"] is None else str(item["populacao"])) or \
                    float(bolha["populacao"]) == item["populacao"], (bolha, item)
            else:
                expect(painel.locator('[data-testid="painel-nao-avaliavel"][data-id="' + item["id"] + '"]')).to_have_count(1)
        expect(painel.get_by_test_id("painel-size-legend").get_by_test_id("painel-size-item")).to_have_count(3)
        expect(painel.get_by_test_id("painel-table").get_by_test_id("painel-row")).to_have_count(len(ids))
        # Dica ao passar o mouse (a maior bolha) e ao focar (outra bolha), com o gráfico no alto da janela.
        painel.get_by_test_id("painel-chart").evaluate("e => e.scrollIntoView({block: 'start'})")
        maior = max((item for item in body["itens"] if item["id"] in ids), key=lambda item: item["populacao"] or 0)
        painel.locator('[data-testid="painel-bubble"][data-id="' + maior["id"] + '"]').hover()
        dica = painel.get_by_test_id("painel-tooltip")
        expect(dica).to_be_visible()
        expect(dica).to_contain_text(maior["rotulo"])
        expect(dica).to_contain_text("por 1.000 habitantes")
        page.mouse.move(2, 2)  # o mouse sai do gráfico: a dica some, e a seguinte vem só do foco
        expect(dica).to_have_count(0)
        outra = next(item for item in body["itens"] if item["id"] in ids and item["id"] != maior["id"])
        painel.locator('[data-testid="painel-bubble"][data-id="' + outra["id"] + '"]').focus()
        expect(dica).to_be_visible()
        expect(dica).to_contain_text(outra["rotulo"])
        shot("01-densidade")

        # 3. Quantidade só troca o eixo: nenhum pedido novo ao motor.
        calls = len(painel_calls)
        painel.get_by_test_id("painel-indicador-quantidade").click()
        expect(axis_x).to_have_attribute("data-eixo", "quantidade")
        drawn(esperados(body, "quantidade"))
        painel.get_by_test_id("painel-indicador-densidade").click()
        expect(axis_x).to_have_attribute("data-eixo", "densidade")
        drawn(ids)
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "trocar o indicador não pede nada ao motor"

        # 4. Régua: "acima de" pelo teclado e "abaixo de" pelo mouse; aparecem só os municípios do corte (limites incluídos).
        ruler = painel.get_by_test_id("painel-ruler")
        dominio = body["dominios"]["densidade"]
        assert [float(ruler.get_attribute("data-dominio-min")), float(ruler.get_attribute("data-dominio-max"))] == dominio
        lower, upper = ruler.get_by_test_id("painel-ruler-min"), ruler.get_by_test_id("painel-ruler-max")
        lower.focus()
        for _ in range(3):
            lower.press("PageUp")
        minimo, maximo = float(lower.get_attribute("aria-valuenow")), float(upper.get_attribute("aria-valuenow"))
        assert dominio[0] < minimo <= maximo == dominio[1], (minimo, maximo, dominio)
        expect(ruler).to_have_attribute("data-ativo", "true")
        drawn(esperados(body, corte=(minimo, maximo)))
        ruler.evaluate("e => e.scrollIntoView({block: 'start'})")  # o arrasto usa coordenadas da janela
        box = upper.bounding_box()
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        page.mouse.move(box["x"] + box["width"] / 2 - 30, box["y"] + box["height"] / 2, steps=6)
        page.mouse.up()
        maximo = float(upper.get_attribute("aria-valuenow"))
        assert minimo <= maximo < dominio[1], (minimo, maximo)
        drawn(esperados(body, corte=(minimo, maximo)))
        assert len(painel_calls) == calls, "a régua é filtro visual: nada é recalculado"
        shot("02-regua")
        ruler.get_by_test_id("painel-ruler-limpar").click()
        drawn(ids)

        # 5. Municípios base: o universo vazio não pede nada; busca e clique acrescentam; arrastar para o gráfico acumula.
        calls = len(painel_calls)
        if real:
            base.locator('[data-testid="painel-base-chip"][data-id="uf:' + AM + '"]').get_by_role("button").click()
        else:
            base.get_by_test_id("painel-base-todos").uncheck()
        expect(painel.get_by_test_id("painel-vazio")).to_be_visible()
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "universo vazio: nenhum pedido ao motor"
        base.get_by_test_id("painel-busca").fill("130420")
        body, sent = ok(lambda: base.locator('[data-testid="painel-lista-item"][data-id="' + TEFE + '"]').get_by_role("button").click())
        assert sent["base"] == {"municipios": {"todos": False, "estados": [], "ids": [TEFE]}}, sent
        drawn(esperados(body))
        base.get_by_test_id("painel-busca").fill("130260")
        origem = base.locator('[data-testid="painel-lista-item"][data-id="' + MANAUS + '"]')
        transferencia = page.evaluate_handle("() => new DataTransfer()")
        origem.dispatch_event("dragstart", {"dataTransfer": transferencia})
        body, sent = ok(lambda: painel.get_by_test_id("painel-chart").dispatch_event("drop", {"dataTransfer": transferencia}))
        assert sent["base"]["municipios"]["ids"] == [TEFE, MANAUS], sent
        drawn(esperados(body))
        # De volta ao universo do início: "Todos" (ou o estado inteiro) absorve os municípios acrescentados.
        if real:
            body, sent = ok(lambda: base.get_by_test_id("painel-base-estado").select_option(AM))
        else:
            body, sent = ok(lambda: base.get_by_test_id("painel-base-todos").check())
        assert sent["base"] == universo, sent
        expect(base.locator('[data-testid="painel-base-chip"][data-id="' + TEFE + '"]')).to_have_count(0)
        drawn(esperados(body))

        # 6. Comparar / Conjuntos: dois municípios destacados lado a lado e agregados numa bolha (soma das contagens dos componentes).
        table = painel.get_by_test_id("painel-table")
        for key in (TEFE, PARINTINS):
            table.locator('[data-testid="painel-row"][data-id="' + key + '"] input[type=checkbox]').check()
        painel.get_by_test_id("painel-acao-comparar").click()
        compare = painel.get_by_test_id("painel-compare")
        expect(compare.get_by_test_id("painel-comparacao-item")).to_have_count(2)
        compare.get_by_test_id("painel-nome-conjunto").fill("Interior")
        body, sent = ok(lambda: compare.get_by_test_id("painel-agregar").click())
        assert sent["conjuntos"] == [{"id": "c1", "rotulo": "Interior", "membros": [TEFE, PARINTINS]}], sent
        itens = {item["id"]: item for item in body["itens"]}
        conjunto = itens["c1"]
        assert conjunto["tipo"] == "conjunto" and conjunto["contagem"] == "SOMA_DOS_COMPONENTES"
        assert conjunto["populacao"] == itens[TEFE]["populacao"] + itens[PARINTINS]["populacao"]  # soma das populações (motor)
        drawn(esperados(body))
        bolha = painel.locator('[data-testid="painel-bubble"][data-id="c1"]')
        expect(bolha).to_have_attribute("data-tipo", "conjunto")
        assert float(bolha.get_attribute("data-populacao")) == conjunto["populacao"]
        expect(table.locator('[data-testid="painel-row"][data-id="c1"]')).to_contain_text("soma das contagens dos componentes")
        expect(painel.get_by_test_id("painel-simbolos")).to_contain_text("possível dupla contagem")
        expect(painel.locator('[data-limitacao="SOMA_COM_POSSIVEL_DUPLA_CONTAGEM"]')).to_contain_text("possível dupla contagem")
        shot("03-conjunto")

        # 7. Distância: referência por critério, na ordem do motor; "Usar o primeiro" (com empate, a escolha entre os empatados).
        painel.get_by_test_id("painel-acao-distancia").click()
        reference = painel.get_by_test_id("painel-reference")
        reference.get_by_test_id("painel-criterio").select_option("densidade")
        reference.get_by_test_id("painel-ordem").select_option("desc")
        with page.expect_response(lambda r: r.url.endswith("/api/painel/referencias"), timeout=120000) as event:
            reference.get_by_test_id("painel-listar-candidatos").click()
        assert event.value.status == 200, event.value.text()[:2000]
        lista, pedido = event.value.json(), options_of(event.value.request)
        assert pedido["criterio"] == {"atributo": "densidade", "ordem": "desc"}, pedido
        assert pedido["universo"] == universo, pedido  # entre os municípios base, o padrão da gaveta
        rows = reference.get_by_test_id("painel-candidato")
        expect(rows).to_have_count(len(lista["candidatos"]))
        for row, candidato in zip(rows.all()[:5], lista["candidatos"][:5]):
            expect(row).to_have_attribute("data-id", candidato["id"])
            expect(row).to_contain_text(str(candidato["posicao"]) + "º")
        primeiros = [item for item in lista["candidatos"] if item["posicao"] == 1]
        if len(primeiros) == 1:
            response, sent = respond(lambda: reference.get_by_test_id("painel-usar-primeiro").click())
        else:
            reference.get_by_test_id("painel-usar-primeiro").click()
            expect(reference.get_by_test_id("painel-empate")).to_be_visible()
            expect(rows).to_have_count(len(primeiros))
            rows.first.locator("input").check()
            response, sent = respond(lambda: reference.get_by_test_id("painel-aplicar-referencia").click())
        assert sent["referencia"] == {"membros": [primeiros[0]["id"]], "criterio": {
            "atributo": "densidade", "ordem": "desc", "universo": universo}}, sent
        if real:
            assert response.status == 200, response.text()[:2000]
            body = response.json()
            expect(axis_x).to_have_attribute("data-eixo", "distancia")
            expect(axis_y).to_have_attribute("data-eixo", "densidade")
            ids = esperados(body, distancia=True)
            drawn(ids)
            desenhadas = bubbles()
            for item in body["itens"]:
                if item["id"] in ids:
                    assert float(desenhadas[item["id"]]["distancia"]) == item["distancia_km"], (desenhadas[item["id"]], item)
                    assert (desenhadas[item["id"]]["referencia"] == "true") == item["referencia"]
            assert body["referencia"]["membros"][0]["id"] == primeiros[0]["id"]
            expect(reference.get_by_test_id("painel-referencia-ativa")).to_contain_text(body["referencia"]["origem"][:40])
            shot("04-distancia")
        else:
            # Versão externa do catálogo: sem o referencial SIRGAS 2000 como premissa, o motor recusa a distância, e a tela
            # mostra a recusa e volta ao último painel calculado sem novo pedido.
            assert response.status == 422, response.text()[:2000]
            erro = painel.get_by_test_id("painel-erro")
            expect(erro).to_contain_text(response.json()["detail"][:60])
            calls = len(painel_calls)
            erro.get_by_test_id("painel-desfazer").click()
            expect(erro).to_have_count(0)
            expect(axis_x).to_have_attribute("data-eixo", "densidade")
            expect(reference.get_by_test_id("painel-referencia-ativa")).to_have_count(0)
            drawn(esperados(body))
            page.wait_for_timeout(400)
            assert len(painel_calls) == calls

        # 8. Crescimento: competência inicial anterior, variação percentual do motor em cada bolha e na tabela.
        painel.get_by_test_id("painel-acao-crescimento").click()
        growth = painel.get_by_test_id("painel-growth")
        escolha = growth.get_by_test_id("painel-competencia-inicial")
        opcoes = escolha.locator("option").evaluate_all("els => els.map(e => e.value)")
        assert opcoes and all(opcao < body["competencia"] for opcao in opcoes), opcoes  # só as anteriores
        inicial = "202306" if "202306" in opcoes else opcoes[-1]
        escolha.select_option(inicial)
        body, sent = ok(lambda: growth.get_by_test_id("painel-mostrar-crescimento").click())
        assert sent["competencia_inicial"] == inicial and body["competencia_inicial"] == inicial, sent
        assert ("referencia" in sent) == real  # a distância continua junto, quando aplicada
        expect(growth.get_by_test_id("painel-growth-legend")).to_be_visible()
        ids = esperados(body, distancia=real)
        drawn(ids)
        desenhadas = bubbles()
        for item in body["itens"]:
            if item["id"] not in ids:
                continue
            valor = item["variacao_percentual"]["densidade"]
            if valor is None:
                assert desenhadas[item["id"]]["variacao"] is None
                expect(painel.locator('[data-testid="painel-nao-avaliavel"][data-aspecto="variacao"][data-id="' + item["id"] + '"]')).to_have_count(1)
            else:
                assert float(desenhadas[item["id"]]["variacao"]) == valor, (desenhadas[item["id"]], item)
                celula = table.locator('[data-testid="painel-row"][data-id="' + item["id"] + '"] td[data-variacao]')
                if real:
                    expect(celula).to_contain_text("%")
                else:
                    expect(celula).to_contain_text(variacao(valor))
        if any(body["itens"][i]["variacao_percentual"]["densidade"] not in (None, 0) for i in range(len(body["itens"]))
               if body["itens"][i]["id"] in ids):
            expect(painel.get_by_test_id("painel-rastro").first).to_be_attached()
        sem_variacao = [key for key in ids if next(item for item in body["itens"] if item["id"] == key)["variacao_percentual"]["densidade"] is None]
        growth.get_by_test_id("painel-vista-inicial").click()
        expect(growth.get_by_test_id("painel-vista-inicial")).to_have_attribute("aria-pressed", "true")
        expect(painel.locator('[data-testid="painel-bubble"][data-visivel="false"]')).to_have_count(len(sem_variacao))
        growth.get_by_test_id("painel-reproduzir").click()
        expect(growth.get_by_test_id("painel-vista-final")).to_have_attribute("aria-pressed", "true", timeout=10000)
        drawn(ids)
        shot("05-crescimento")

        # 9. Conversa em caixa arrastável: mesmos ids do chat; mouse e teclado movem a caixa; enviar mensagem continua.
        expect(chat).to_be_visible()
        chat.get_by_test_id("painel-chat-minimizar").click()  # minimizada no passo 1
        expect(chat).to_have_attribute("data-minimizada", "false")
        expect(chat.locator("#assistant-input")).to_be_visible()
        expect(page.locator("#assistente")).to_have_attribute("data-testid", "painel-chat")
        expect(page.get_by_test_id("conversation-pane")).to_be_hidden()
        handle = chat.get_by_test_id("painel-chat-handle")
        antes, cabeca = chat.bounding_box(), handle.bounding_box()
        page.mouse.move(cabeca["x"] + cabeca["width"] * 0.35, cabeca["y"] + cabeca["height"] / 2)
        page.mouse.down()
        page.mouse.move(cabeca["x"] + cabeca["width"] * 0.35 - 220, cabeca["y"] + cabeca["height"] / 2 - 160, steps=8)
        page.mouse.up()
        depois = chat.bounding_box()
        assert abs((antes["x"] - depois["x"]) - 220) <= 4 and abs((antes["y"] - depois["y"]) - 160) <= 4, (antes, depois)
        handle.focus()
        handle.press("ArrowLeft")
        handle.press("ArrowUp")
        movida = chat.bounding_box()
        assert abs((depois["x"] - movida["x"]) - 16) <= 1 and abs((depois["y"] - movida["y"]) - 16) <= 1, (depois, movida)
        page.wait_for_timeout(400)
        guardada = json.loads(page.evaluate("localStorage.getItem('adt:painel-chat:v1')"))
        assert abs(guardada["x"] - movida["x"]) <= 1 and abs(guardada["y"] - movida["y"]) <= 1, (guardada, movida)
        chat.locator("#assistant-input").fill("O que tem nos dados do Brasil?")
        chat.get_by_role("button", name="Enviar mensagem").click()
        expect(chat.get_by_test_id("latest-reply")).to_contain_text("Os dados do Brasil disponíveis nesta plataforma", timeout=30000)
        chat.get_by_test_id("painel-chat-minimizar").click()
        expect(chat.locator("#assistant-input")).to_be_hidden()
        chat.get_by_test_id("painel-chat-minimizar").click()
        expect(chat.locator("#assistant-input")).to_be_visible()
        shot("06-conversa")

        # 10. Celular (390 px): sem rolagem horizontal; a conversa fica ancorada embaixo.
        page.set_viewport_size({"width": 390, "height": 844})
        expect(chat).to_have_attribute("data-ancorada", "true")
        page.wait_for_timeout(500)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        caixa = chat.bounding_box()
        assert caixa["x"] <= 12 and caixa["x"] + caixa["width"] >= 390 - 12 and caixa["y"] + caixa["height"] >= 844 - 12, caixa
        page.screenshot(path=str(OUTPUT / ("painel-07-celular" + suffix + ".png")), full_page=True)
        page.set_viewport_size({"width": 1280, "height": 900})

        # 11. Voltar à preparação clássica: o chat volta ao lugar de sempre, com a mesma conversa; reabrir não recalcula; as
        # análises sem lugar no painel abrem a preparação clássica delas.
        painel.get_by_test_id("painel-voltar").click()
        expect(painel).to_be_hidden()
        expect(page.get_by_test_id("conversation-dock")).to_be_visible()
        expect(page.locator("#assistente")).to_have_attribute("aria-label", "Assistente de análise territorial")
        expect(page.get_by_test_id("latest-reply")).to_contain_text("Os dados do Brasil disponíveis nesta plataforma")
        expect(page.get_by_test_id("analysis-catalog")).to_be_visible()
        calls = len(painel_calls)
        page.get_by_test_id("nav-painel").click()
        expect(painel).to_be_visible()
        expect(painel.locator('[data-testid="painel-bubble"][data-id="c1"]')).to_have_count(1)
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "reabrir o painel não recalcula"
        painel.get_by_test_id("painel-classica-distribution").click()
        expect(painel).to_be_hidden()
        expect(page.locator("#preparacao-conversacional")).to_be_visible(timeout=90000)

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    print("PAINEL INTEGRADO PASS: eixo único, régua, municípios acrescentados, conjunto, distância, crescimento e conversa "
          "arrastável" + (" (base versionada)." if real else " (catálogo sintético)."))


if __name__ == "__main__":
    main()
