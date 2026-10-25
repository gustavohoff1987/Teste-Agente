"""Área de análise da página única (22/10/2026): abertura antes dos dados (E0, só a identificação e as duas entradas, sem abas,
desde 24/10/2026), a base do Brasil sem seleção automática e a Seleção de Territórios por níveis (24/10/2026: o Brasil como
unidade, os estados um a um ou todos, os municípios navegados por estado e cumulativos, a busca no alto, "Marcar todos" e
"Desmarcar todos"), os estados em bolhas e a bolha que abre os municípios de um estado, o eixo vertical do indicador com o arranjo
horizontal, a dica no mouse e no foco, Quantidade (com os quintis do mapa no pedido, a troca pede ao motor; a volta vem da
memória da tela), a régua que só esconde, grupos por posição, a análise espacial com o Território de referência, a tendência, a
rotatividade com o motivo, Condições, Ordenar, Comparar, Juntar, Limpar filtros, Exportar (CSV em precisão integral), os
Detalhes e o celular (abas roláveis e o botão Ferramentas).

Desde 23/10/2026 (pedido integrado): uma linha de abas com a Seleção de Territórios primeiro e as quatro análises com os nomes
padronizados (Análise de Distribuição, Análise Espacial, Análise de Tendência e Análise de Rotatividade); a lista de territórios
fica no painel da Seleção (`analise-aba-painel`), e os ajustes de cada análise, no painel da aba dela, com o resumo da seleção e
"Alterar a seleção". Desde 24/10/2026, a Seleção é só seleção (o título, a frase-resumo, o desenho e os Detalhes ficam nas
análises), e cada análise começa por "Entenda esta análise" (`analise-entenda`), aberta na primeira visita e recolhível.

Desde 24/10/2026 (segunda rodada, os 12 ajustes de interface): o nome da plataforma na abertura ("Diagnóstico Territorial da
Força de Trabalho na Saúde"); no alto da área, fixos ao rolar e lado a lado, Desfazer (`analise-desfazer`, até 25/10/2026
"Voltar", com a seta curva do desfazer desde então; um desfazer sequencial
de toda a interação, como o Ctrl+Z: a seleção, as abas, os ajustes, os filtros e a vista; desligado, com o motivo em palavras,
quando não há o que desfazer) e Limpar seleção (`analise-limpar-selecao`, a vassoura: tira os territórios do nível em uso sem
apagar os dados nem a escolha dos outros níveis; desligado no nível Brasil, com o motivo); "Voltar aos estados" maior e preenchido, distinto do Desfazer do alto; a Seleção em duas áreas (à esquerda, a busca e a
lista; à direita, o que entra na análise, estado a estado, com o × de cada município e de cada estado); as abas das análises só
com o nome; o Território de referência da análise espacial num fluxo só (a relação, a delimitação, o atributo, o operador e o
valor de corte, sem valores padrão; primeiro os elegíveis, depois o mais próximo ou o mais distante, nunca o próprio território;
a mensagem quando nenhum território fica com referência); Comparar e Juntar sem os cartões de valores, com a orientação e os
escolhidos; na tendência, "Entenda esta análise" recolhido, o período Anual (ou o único ritmo da base) e o Gráfico ao abrir, os
ajustes no alto, o desenho em destaque e a explicação à direita, com a divisória ajustável (mouse e teclado, com limites); a
coluna "Tendência" (sem "Classe (do motor)") e nenhum "motor" nos textos da área; as visões Tendência, Trajetória (com os
períodos do meio no caminho) e Série temporal (toda a série da base ou o intervalo escolhido), trocadas sem refazer a seleção.

Desde 23/10/2026: os ajustes dentro de cada análise (`analise-ajustes`, o painel colado na aba escolhida, com só o que vale para
ela e o mesmo indicador em todas), a escala na barra junto do desenho (fora dos ajustes, e só quando se aplica), a escolha da vista
do desenho (`analise-desenho`: o gráfico é a inicial; nos estados, o mapa desligado, com o motivo e o atalho), o convite ao mapa
depois das Condições e na análise espacial e a frase-resumo do motor (`analise-resumo`), com a competência da resposta. O mapa
em si (pontos, pintura, transição, lado a lado) é conferido no roteiro do mapa.

Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; quatro competências; fonte estadual sintética; todas as
sedes no mesmo ponto) ou, com ADT_BLOCK1_REAL=1, a base versionada (somente leitura), que acrescenta o modo leve com todos os
municípios do Brasil. O roteiro assume que a estrutura da página abre a área de análise (`area-de-analise`) depois do aceite de
privacidade e usa os botões de fonte da própria área em E0. Cada bolha desenhada é conferida com a resposta de /api/painel: todo
número vem do motor. A disponibilidade da análise espacial também vem do motor: no catálogo sintético, instalado como versão
externa, o referencial (SIRGAS 2000 ou WGS 84) pode não ser premissa, e o roteiro segue o que o motor disser (a aba desabilitada
com o motivo; a recusa, com as opções da pendência que o motor mandar, e a volta ao último gráfico calculado; ou o eixo da
distância). Servidor serve_ui_offline.py; nunca chama o provedor de IA.
"""
import csv
import io
import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, TEFE, PARINTINS = "code:130260", "code:130420", "code:130340"
AM = "13"  # prefixo IBGE do Amazonas
BOLHAS = '[data-testid="analise-bolha"][data-visivel="true"]'
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro",
         "dezembro")
DESFAZER_VAZIO = "Nada para desfazer ainda"
# Estilo calculado e caixa de um elemento, para comparar o destaque de dois botões.
ESTILO = """e => { const s = getComputedStyle(e), c = e.getBoundingClientRect();
  return {fundo: s.backgroundColor, cor: s.color, altura: c.height, fonte: parseFloat(s.fontSize), peso: Number(s.fontWeight)}; }"""
# O texto da área (o que está à vista e o que os leitores de tela leem) e os title/aria-label dos controles.
TEXTOS_DA_AREA = """e => e.innerText + '\\n' + [...e.querySelectorAll('[title],[aria-label]')]
  .map(x => (x.getAttribute('title') || '') + ' ' + (x.getAttribute('aria-label') || '')).join('\\n')"""


def formas_da_competencia(competencia):
    """A competência AAAAMM como a frase-resumo do motor pode escrevê-la: por extenso, mm/aaaa, mês abreviado ou como veio."""
    formas = [competencia]
    if re.fullmatch(r"\d{6}", competencia) and 1 <= int(competencia[4:]) <= 12:
        mes, ano = MESES[int(competencia[4:]) - 1], competencia[:4]
        formas += [mes + " de " + ano, competencia[4:] + "/" + ano, mes[:3] + "/" + ano]
    return formas


def mm_aaaa(competencia):
    return competencia[4:] + "/" + competencia[:4] if re.fullmatch(r"\d{6}", competencia) else competencia


def options_of(request):
    return json.loads(request.post_data.split('name="options"\r\n\r\n', 1)[1].split("\r\n--", 1)[0])


def esperados(body, indicador="densidade", corte=None, distancia=False):
    """Bolhas que a tela deve desenhar: itens com o indicador avaliável (e a distância, quando à vista); a régua só tira as
    unidades fora do corte (conjuntos e referência ficam)."""
    ids = []
    for item in body["itens"]:
        valor = item.get(indicador)
        if valor is None or (distancia and item.get("distancia_km") is None):
            continue
        if corte and item["tipo"] != "conjunto" and not item.get("referencia") and not corte[0] <= valor <= corte[1]:
            continue
        ids.append(item["id"])
    return sorted(ids)


def referencias_do_item(item):
    """Os territórios de referência de um item na resposta (o primeiro e os empatados)."""
    ref = item.get("referencia_do_item")
    if not ref:
        return []
    return [ref["id"]] + [e["id"] for e in ref.get("empate") or [] if e["id"] != ref["id"]]


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = "-real" if real else ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, llm_calls, painel_calls, pedidos, notas = [], [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: painel_calls.append(request.url) if request.url.endswith("/api/painel") else None)
        page.on("request", lambda request: pedidos.append(request)
                if request.url.endswith("/api/painel") and request.method == "POST" else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        eixo_y, eixo_x = area.get_by_test_id("analise-eixo-y"), area.get_by_test_id("analise-eixo-x")
        territorios = area.get_by_test_id("analise-territorios")
        controles = area.get_by_test_id("analise-controles-globais")
        desfazer = controles.get_by_test_id("analise-desfazer")
        limpar = controles.get_by_test_id("analise-limpar-selecao")
        aviso = area.get_by_test_id("analise-aviso")

        def shot(name):
            page.wait_for_timeout(700)  # transições do gráfico
            page.screenshot(path=str(OUTPUT / ("area-" + name + suffix + ".png")), full_page=True)

        def respond(action, timeout=180000, condicao=None):
            """Executa a ação e devolve a resposta de /api/painel e as opções do mesmo pedido. Só vale um pedido feito depois do
            início da ação (e, com `condicao`, o primeiro cujas opções a atendem): a resposta de um pedido anterior ainda em curso
            (o "Limpar" das Condições pede ao motor sem que o roteiro espere) pode chegar depois e não é a desta ação. A tela só
            pede 150 ms depois da mudança (e só quando a resposta não está na memória dela, que guarda as seis últimas); por isso,
            antes da ação, o cálculo que a ação anterior tenha disparado termina ("Atualizando o gráfico…" sai), para esse pedido
            não sair já dentro desta ação."""
            page.wait_for_timeout(200)
            expect(area.get_by_test_id("analise-atualizando")).to_have_count(0, timeout=timeout)
            antes = len(pedidos)
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST"
                                      and any(r.request is pedido for pedido in pedidos[antes:])
                                      and (condicao is None or condicao(options_of(r.request))), timeout=timeout) as event:
                action()
            response = event.value
            return response, options_of(response.request)

        def ok(action, timeout=180000, condicao=None):
            response, sent = respond(action, timeout, condicao)
            assert response.status == 200, response.text()[:2000]
            return response.json(), sent

        def drawn(ids, timeout=30000):
            page.wait_for_function("ids => JSON.stringify([...document.querySelectorAll('[data-testid=analise-bolha][data-visivel=true]')]"
                                   ".map(e => e.dataset.id).sort()) === JSON.stringify(ids)", arg=sorted(ids), timeout=timeout)

        def bubbles():
            return {item["id"]: item for item in area.locator(BOLHAS).evaluate_all(
                "els => els.map(e => ({id: e.dataset.id, tipo: e.dataset.tipo, valor: e.dataset.valor, populacao: e.dataset.populacao, "
                "distancia: e.dataset.distancia ?? null, variacao: e.dataset.variacao ?? null, classe: e.dataset.classe ?? null, "
                "grupo: e.dataset.grupo ?? null, condicao: e.dataset.condicao ?? null, posicao: e.dataset.posicao ?? null, "
                "trajeto: [...e.querySelectorAll('[data-testid=analise-trajeto-ponto]')].map(t => t.dataset.competencia)}))")}

        def aperta(locator):
            """Botões e caixas pelo teclado: além de conferir o acesso sem mouse, evita a caixa da conversa por cima. Um botão
            desligado (disabled) não recebe o foco, e o Enter iria para o controle focado antes: o roteiro para com o motivo."""
            locator.scroll_into_view_if_needed()
            assert not locator.evaluate("e => !!e.disabled"), "o botão está desligado: o Enter iria para outro controle"
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

        def aba_selecao():
            """A Seleção de Territórios: a lista dos territórios fica no painel dela (23/10/2026)."""
            if area.get_attribute("data-aba") != "territorios":
                aperta(area.get_by_test_id("analise-aba-territorios"))
            expect(area).to_have_attribute("data-aba", "territorios")
            expect(territorios).to_be_visible()

        def aba_analise(familia):
            """A aba de uma análise já escolhida (sem trocar de análise): os ajustes ficam no painel dela."""
            if area.get_attribute("data-aba") != familia:
                aperta(area.get_by_test_id("analise-familia-" + familia))
            expect(area).to_have_attribute("data-aba", familia)

        def milhar(numero):
            return f"{numero:,}".replace(",", ".")

        def sem_bastidor(onde):
            """Requisito 11 (24/10/2026): nenhum texto da área, à vista, lido pelos leitores de tela ou nos title, fala do "motor"."""
            achados = re.findall(r"[^\n]{0,50}\bmotor\b[^\n]{0,50}", area.evaluate(TEXTOS_DA_AREA), flags=re.IGNORECASE)
            assert not achados, (onde, achados[:5])

        def confere_valores(body, indicador="densidade"):
            desenhadas = bubbles()
            for item in body["itens"]:
                if item["id"] in desenhadas:
                    bolha = desenhadas[item["id"]]
                    assert float(bolha["valor"]) == item[indicador] and bolha["tipo"] == item["tipo"], (bolha, item)
                    assert bolha["populacao"] == "" if item.get("populacao") is None else float(bolha["populacao"]) == item["populacao"], (bolha, item)
                elif item.get(indicador) is None:
                    expect(area.locator('[data-testid="analise-nao-avaliavel"][data-id="' + item["id"] + '"]')).to_have_count(1)

        # 1. E0 (24/10/2026): antes dos dados, só a identificação (o nome da plataforma), a chamada e as duas entradas; sem abas,
        # sem números nem bolhas, e sem os controles do alto (Desfazer e Limpar seleção só existem com os dados prontos).
        expect(area).to_be_visible(timeout=60000)
        expect(area).to_have_attribute("data-estado", "E0")
        expect(area.get_by_test_id("analise-abertura")).to_contain_text("Escolha seus dados para começar")
        expect(area.get_by_test_id("analise-titulo")).to_have_text("Diagnóstico Territorial da Força de Trabalho na Saúde")
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-detalhes")).to_have_count(0)
        expect(area.get_by_role("tablist")).to_have_count(0)
        expect(area.get_by_test_id("analise-apresentacao")).to_have_count(0)
        expect(controles).to_have_count(0)
        assert not painel_calls, "antes dos dados, nada é pedido ao motor"
        # A caixa da conversa (estrutura da página), se estiver aberta, fica minimizada enquanto o roteiro usa o gráfico.
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 2. E1: os dados do Brasil pela própria área, sem seleção automática: nada é pedido ao motor; a área abre a Seleção de
        # Territórios, com os três níveis (Brasil, Estados e Municípios), a busca no alto e a lista dos estados à vista. A Seleção
        # é só seleção: o título, a frase-resumo, o desenho e os Detalhes ficam nas análises.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true", timeout=120000)
        expect(area).to_have_attribute("data-estado", "E1")
        expect(area).to_have_attribute("data-aba", "territorios")
        expect(territorios).to_be_visible()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        expect(area.get_by_test_id("analise-resultados")).to_be_hidden()
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-resumo")).to_have_text("")  # a região da frase fica, vazia
        # Desfazer e Limpar seleção (24/10/2026, segunda rodada; o Desfazer era "Voltar" até 25/10/2026): no alto da área, lado a
        # lado, com os nomes exatos e os ícones (a seta curva do desfazer e a vassoura). Sem nada para desfazer nem territórios
        # marcados, os dois ficam desligados, com o motivo em palavras; o Limpar seleção da Seleção saiu (um só, o do alto).
        expect(controles).to_be_visible()
        expect(controles).to_have_attribute("role", "toolbar")
        expect(desfazer).to_have_text("Desfazer")
        expect(limpar).to_have_text("Limpar seleção")
        expect(desfazer.locator("svg")).to_have_count(1)
        expect(limpar.locator("svg")).to_have_count(1)
        expect(desfazer).to_be_disabled()
        expect(desfazer).to_have_attribute("title", DESFAZER_VAZIO)
        expect(desfazer).to_have_attribute("aria-label", DESFAZER_VAZIO)
        expect(limpar).to_be_disabled()
        expect(limpar).to_have_attribute("title", "Nenhum território selecionado.")
        expect(area.get_by_test_id("analise-limpar-selecao")).to_have_count(1)
        expect(area.get_by_test_id("analise-desfazer")).to_have_count(1)  # um só: o do alto (o da Seleção saiu em 24/10/2026)
        expect(territorios.get_by_test_id("analise-desfazer")).to_have_count(0)
        expect(desfazer.locator("svg.lucide-undo")).to_have_count(1)  # a seta curva do desfazer (25/10/2026), não a seta de voltar
        caixa_desfazer, caixa_limpar = desfazer.bounding_box(), limpar.bounding_box()
        assert caixa_desfazer["x"] + caixa_desfazer["width"] <= caixa_limpar["x"] and abs(caixa_desfazer["y"] - caixa_limpar["y"]) < 4, \
            ("Desfazer e Limpar seleção lado a lado, o Desfazer primeiro", caixa_desfazer, caixa_limpar)
        assert caixa_desfazer["y"] < territorios.bounding_box()["y"], "os controles no alto da área"
        # Uma linha de abas: a Seleção de Territórios primeiro e as quatro análises com os nomes padronizados, só os nomes (os
        # textos de apoio das análises saíram em 24/10/2026).
        linha_de_abas = area.get_by_role("tablist", name="Seleção de territórios e análises")
        ordem = linha_de_abas.get_by_role("tab").evaluate_all("els => els.map(e => e.dataset.testid)")
        assert ordem == ["analise-aba-territorios", "analise-familia-distribuicao", "analise-familia-espacial",
                         "analise-familia-tendencia", "analise-familia-rotatividade"], ordem
        expect(area.get_by_test_id("analise-aba-territorios")).to_contain_text("Seleção de Territórios")
        for testid, nome in (("analise-familia-distribuicao", "Análise de Distribuição"), ("analise-familia-espacial", "Análise Espacial"),
                             ("analise-familia-tendencia", "Análise de Tendência"), ("analise-familia-rotatividade", "Análise de Rotatividade")):
            expect(area.get_by_test_id(testid)).to_have_text(nome)
        for apoio in ("Indicador de cada território", "Distância até uma referência", "Mudança e tendência no tempo",
                      "Só com os dados enviados"):
            expect(linha_de_abas).not_to_contain_text(apoio)
        # Na mesma linha: uma linha horizontal atravessa as cinco abas (as alturas podem variar com o texto de apoio), da
        # esquerda para a direita, na ordem acima.
        caixas = [area.get_by_test_id(testid).bounding_box() for testid in ordem]
        assert max(caixa["y"] for caixa in caixas) < min(caixa["y"] + caixa["height"] for caixa in caixas), ("as cinco abas na mesma linha", caixas)
        assert [caixa["x"] for caixa in caixas] == sorted(caixa["x"] for caixa in caixas), ("da esquerda para a direita", caixas)
        # A orientação curta da Seleção, sempre à vista, sem instruções técnicas; a busca no alto, acima da lista.
        apresentacao = area.get_by_test_id("analise-apresentacao")
        expect(apresentacao).to_have_text("Escolha os territórios que entram nas análises. A seleção vale para todas elas e pode ser mudada a "
                                          "qualquer momento.")
        for tecnico in ("modo leve", "Mais lento", "em bolhas", "com a linha do Brasil", "A caixa marca"):
            expect(territorios).not_to_contain_text(tecnico)
        busca = territorios.get_by_test_id("analise-busca")
        expect(busca).to_be_visible()
        expect(busca).to_have_attribute("placeholder", "Buscar município ou estado")
        assert busca.bounding_box()["y"] < territorios.get_by_test_id("analise-grupo").first.bounding_box()["y"], "a busca no alto da Seleção"
        # Duas áreas lado a lado (24/10/2026, segunda rodada): à esquerda, a busca no alto e a lista; à direita, sempre à vista, o
        # que entra na análise (vazio, com a orientação). Cada uma com cerca de metade da largura.
        lista_esquerda = territorios.get_by_test_id("analise-territorios-lista")
        direita = territorios.get_by_test_id("analise-selecionados")
        caixa_e, caixa_d, largura_sel = lista_esquerda.bounding_box(), direita.bounding_box(), territorios.bounding_box()["width"]
        assert caixa_e["x"] + caixa_e["width"] <= caixa_d["x"] + 1, ("a lista à esquerda, o que está marcado à direita", caixa_e, caixa_d)
        assert abs(caixa_e["y"] - caixa_d["y"]) < 8, ("as duas áreas começam na mesma altura", caixa_e, caixa_d)
        assert min(caixa_e["width"], caixa_d["width"]) >= 0.4 * largura_sel, ("cada área com cerca de metade", caixa_e, caixa_d, largura_sel)
        expect(lista_esquerda.get_by_test_id("analise-busca")).to_be_visible()
        expect(direita.get_by_test_id("analise-selecionados-itens")).to_contain_text("Nenhum município marcado ainda")
        for nivel, rotulo in (("brasil", "Brasil"), ("estados", "Estados"), ("municipios", "Municípios")):
            expect(territorios.get_by_test_id("analise-nivel-" + nivel)).to_contain_text(rotulo)
        expect(territorios.get_by_test_id("analise-nivel-municipios")).to_have_attribute("aria-checked", "true")
        sem_bastidor("Seleção de Territórios")
        page.wait_for_timeout(800)
        assert not painel_calls, "sem territórios escolhidos, nada é pedido ao motor"
        # A aba de uma análise sem territórios: "Entenda esta análise" aberta na primeira visita, os ajustes e o convite a
        # selecionar; a referência e a janela só depois da seleção.
        aperta(area.get_by_test_id("analise-familia-espacial"))
        entenda = area.get_by_test_id("analise-entenda")
        expect(entenda).to_have_attribute("data-aba", "espacial")
        expect(entenda).to_have_attribute("open", "")
        expect(apresentacao).to_have_attribute("data-aba", "espacial")
        expect(apresentacao).to_contain_text("não é um trajeto por estradas")
        expect(apresentacao).to_contain_text("O próprio município nunca é a sua referência.")
        expect(apresentacao).to_be_visible()
        expect(area.get_by_test_id("analise-vazio")).to_contain_text("Os dados do Brasil foram carregados e estão prontos para a análise.")
        expect(area.get_by_test_id("analise-painel")).to_have_count(0)
        expect(area.get_by_test_id("analise-selecao-alterar")).to_have_text("Selecionar os territórios")
        # A explicação se recolhe e se reabre; na visita seguinte da aba, começa recolhida (os resultados ficam no alto).
        aperta(entenda.get_by_test_id("analise-entenda-botao"))
        expect(entenda).not_to_have_attribute("open", "")
        expect(apresentacao).to_be_hidden()
        aperta(entenda.get_by_test_id("analise-entenda-botao"))
        expect(entenda).to_have_attribute("open", "")
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area.get_by_test_id("analise-entenda")).to_have_attribute("open", "")  # primeira visita da distribuição
        aperta(area.get_by_test_id("analise-familia-espacial"))
        expect(area.get_by_test_id("analise-entenda")).to_have_attribute("open", "")  # a pessoa a deixou aberta
        aperta(area.get_by_test_id("analise-entenda-botao"))
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        aperta(area.get_by_test_id("analise-familia-espacial"))
        expect(area.get_by_test_id("analise-entenda")).not_to_have_attribute("open", "")  # recolhida, como a pessoa deixou
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        aperta(area.get_by_test_id("analise-selecao-alterar"))
        expect(area).to_have_attribute("data-aba", "territorios")
        # Cada troca de aba é um passo do Desfazer (24/10/2026, segunda rodada): ele diz o que desfaz e devolve a aba anterior, um
        # passo por vez, como o Ctrl+Z; sem mais passos, volta ao estado inicial e desliga, com o motivo. Nada é pedido ao motor.
        expect(desfazer).to_be_enabled()
        expect(desfazer).to_have_attribute("title", "Desfazer: abrir a Seleção de Territórios")
        aperta(desfazer)
        expect(area).to_have_attribute("data-aba", "distribuicao")
        expect(aviso).to_have_text("Desfeito: abrir a Seleção de Territórios.")
        expect(desfazer).to_have_attribute("title", "Desfazer: abrir a Análise de Distribuição")
        aperta(desfazer)
        expect(area).to_have_attribute("data-aba", "espacial")
        for _ in range(20):
            if desfazer.is_disabled():
                break
            aperta(desfazer)
            page.wait_for_timeout(60)
        expect(desfazer).to_be_disabled()
        expect(desfazer).to_have_attribute("title", DESFAZER_VAZIO)
        expect(area).to_have_attribute("data-aba", "territorios")
        page.wait_for_timeout(400)
        assert not painel_calls, "abrir as abas sem territórios (e desfazer) não pede nada ao motor"
        # Os estados como unidades: o nível Estados (cada nível guarda a sua escolha) e "Marcar todos os estados".
        aperta(territorios.get_by_test_id("analise-nivel-estados"))
        expect(territorios.get_by_test_id("analise-nivel-estados")).to_have_attribute("aria-checked", "true")
        expect(busca).to_have_attribute("placeholder", "Buscar estado")
        estados, sent = ok(lambda: aperta(territorios.get_by_test_id("analise-marcar-todos")))
        # nivel e indicador vão em todo pedido (sem nivel, o motor responde no formato de 21/10); com todos, sem a lista.
        assert sent.get("nivel") == "estados" and set(sent) == {"competencia", "categoria", "nivel", "indicador"}, sent
        assert sent.get("indicador") == "densidade", sent
        expect(territorios.get_by_test_id("analise-marcar-todos")).to_have_text(re.compile(r"Marcar todos os estados \(\d+\)"))
        expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text(re.compile(r"Todos os estados \(\d+\)"))
        expect(territorios.locator('[data-testid="analise-estado"][data-id="' + AM + '"] input')).to_be_checked()
        # Marcar muitos de uma vez fica dito junto do que está marcado, com o caminho para desfazer (o Desfazer do alto).
        expect(territorios.get_by_test_id("analise-selecao-aviso")).to_have_text("Todos os estados marcados. Para desfazer, use o botão Desfazer, no alto.")
        expect(desfazer).to_have_attribute("title", "Desfazer: todos os estados marcados")
        expect(limpar).to_be_enabled()
        expect(limpar).to_have_attribute("title", "Tira os territórios em análise; os dados carregados continuam.")
        expect(area).to_have_attribute("data-estado", "E1")
        itens_estado = [item for item in estados["itens"] if item["tipo"] == "estado"]
        assert itens_estado and all(item["tipo"] == "estado" for item in estados["itens"]), "estados e municípios nunca juntos"
        aperta(territorios.get_by_test_id("analise-ver-analise"))
        expect(area).to_have_attribute("data-aba", "distribuicao")
        expect(area.get_by_test_id("analise-resultados")).to_be_visible()
        drawn(esperados(estados))
        confere_valores(estados)
        expect(eixo_y).to_have_attribute("data-eixo", "densidade")
        expect(eixo_y).to_have_attribute("data-escala", "linear")
        expect(eixo_x).to_have_count(0)
        expect(area.get_by_test_id("analise-arranjo-nota")).to_contain_text("posição horizontal é só arranjo")
        expect(area.get_by_test_id("analise-instrucao")).to_contain_text("Clique num estado para ver os municípios dele")
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("nos estados")
        expect(area.get_by_test_id("analise-subtitulo")).to_have_text("Cada bolha é um estado. O tamanho mostra a população.")
        if ((estados.get("contexto") or {}).get("brasil") or {}).get("densidade") is not None:
            expect(area.get_by_test_id("analise-contexto-brasil")).to_have_count(1)
        # O Desfazer do alto desfaz passo a passo: agora, a última ação foi abrir a análise.
        expect(desfazer).to_have_attribute("title", "Desfazer: abrir a Análise de Distribuição")
        # A rotatividade não se executa com a base do Brasil, mas a aba abre (sem aria-disabled), com o motivo dentro dela.
        expect(area.get_by_test_id("analise-familia-rotatividade")).to_have_attribute("data-disponivel", "false")
        expect(area.get_by_test_id("analise-familia-rotatividade")).not_to_have_attribute("aria-disabled", "true")
        # Ajustes dentro da análise (23/10/2026): o painel da aba escolhida começa por "Entenda esta análise" e mostra só o que
        # vale para ela; nos estados (E1), o indicador, a competência e os grupos e faixas. A escala sai dos ajustes: fica na barra
        # junto do desenho. A troca para a aba da análise já escolhida não pede nada ao motor.
        calls = len(painel_calls)
        aba_analise("distribuicao")
        painel_da_aba = area.get_by_test_id("analise-aba-painel")
        expect(painel_da_aba).to_have_attribute("role", "tabpanel")
        expect(painel_da_aba).to_have_attribute("data-aba", "distribuicao")
        expect(area.get_by_test_id("analise-familia-distribuicao")).to_have_attribute("aria-controls", "analise-aba-painel")
        expect(painel_da_aba.get_by_test_id("analise-apresentacao")).to_contain_text("Cada bolha é um território")
        expect(painel_da_aba.get_by_test_id("analise-selecao-alterar")).to_have_text("Alterar a seleção")
        expect(painel_da_aba.get_by_test_id("analise-selecao-resumo")).to_contain_text(re.compile(r"Todos os estados \(\d+\)"))
        ajustes = area.get_by_test_id("analise-ajustes")
        expect(ajustes).to_have_attribute("data-familia", "distribuicao")
        page.wait_for_timeout(300)
        assert len(painel_calls) == calls, "trocar de aba sem trocar de análise não pede nada ao motor"
        for controle in ("analise-indicador-densidade", "analise-indicador-quantidade", "analise-competencia", "analise-agrupar"):
            expect(ajustes.get_by_test_id(controle)).to_be_visible()
        expect(ajustes.get_by_test_id("analise-indicador-densidade")).to_have_attribute("aria-checked", "true")
        for ausente in ("analise-referencia-escolher", "analise-janela-escolher", "analise-visao-classes", "analise-rot-inicial",
                        "analise-escala"):
            expect(ajustes.get_by_test_id(ausente)).to_have_count(0)
        barra = area.get_by_test_id("analise-barra-desenho")
        expect(barra.get_by_test_id("analise-escala")).to_be_visible()
        expect(barra.get_by_test_id("analise-escala")).to_have_value("linear")
        # A vista do desenho: o gráfico é a inicial. Nos estados, o mapa fica desligado (os estados não têm um ponto), com o motivo
        # e o atalho para os municípios no mapa; o lado a lado só aparece com a janela de 1.600 px ou mais.
        expect(area).to_have_attribute("data-desenho", "grafico")
        desenho = barra.get_by_test_id("analise-desenho")
        expect(desenho.get_by_test_id("analise-desenho-grafico")).to_have_attribute("aria-pressed", "true")
        mapa_botao = desenho.get_by_test_id("analise-desenho-mapa")
        expect(mapa_botao).to_have_attribute("aria-disabled", "true")
        expect(desenho.get_by_test_id("analise-desenho-lado")).to_have_count(0)
        calls = len(painel_calls)
        aperta(mapa_botao)
        motivo_mapa = area.get_by_test_id("analise-desenho-motivo")
        expect(motivo_mapa).to_contain_text("Os estados não têm um ponto no mapa")
        expect(motivo_mapa.get_by_test_id("analise-desenho-atalho")).to_have_text("Ver os municípios no mapa")
        expect(area).to_have_attribute("data-desenho", "grafico")
        expect(area.get_by_test_id("analise-mapa-carregando")).to_have_count(0)
        page.wait_for_timeout(300)
        assert len(painel_calls) == calls, "o mapa desligado não pede nada ao motor"
        # A bolha do estado sob o mouse e em foco mostra a ação "Ver os municípios".
        amazonas = next(item for item in itens_estado if "Amazonas" in item["rotulo"])
        bolha_am = area.locator('[data-testid="analise-bolha"][data-id="' + amazonas["id"] + '"]')
        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start'})")
        bolha_am.hover()
        dica = area.get_by_test_id("analise-dica")
        expect(dica).to_contain_text("Amazonas")
        expect(dica.get_by_test_id("analise-dica-acao")).to_contain_text(re.compile(r"Ver os \d+ municípios"))
        page.mouse.move(2, 2)
        expect(dica).to_have_count(0)
        bolha_am.focus()
        expect(dica.get_by_test_id("analise-dica-acao")).to_be_visible()
        sem_bastidor("Análise de Distribuição nos estados")
        shot("01-estados")

        # 3. Enter na bolha do estado abre os municípios dele (E2). O Desfazer do alto (24/10/2026, segunda rodada, no lugar do
        # "Voltar aos estados" que aparecia só depois dessa navegação) diz o que desfaz e devolve os estados, como estavam. Com o
        # mapa disponível e sem cor própria da análise, o pedido leva os 5 grupos iguais (quintis) do mapa.
        am, sent = ok(lambda: bolha_am.press("Enter"))
        sent_am = sent
        universo_am = {"municipios": {"todos": False, "estados": [AM], "ids": []}}
        assert sent["base"] == universo_am and sent.get("nivel") == "municipios", sent
        assert sent.get("grupos_mapa") == {"tipo": "quintis"} and "grupos" not in sent, sent
        expect(area).to_have_attribute("data-estado", "E2")
        assert all(item["tipo"] == "municipio" for item in am["itens"]), "estados e municípios nunca no mesmo eixo"
        ids_am = esperados(am)
        drawn(ids_am)
        confere_valores(am)
        expect(eixo_y).to_have_attribute("data-eixo", "densidade")
        expect(eixo_x).to_have_count(0)
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("Densidade de médicos nos municípios do Amazonas · ")
        expect(area.get_by_test_id("analise-subtitulo")).to_have_text("Cada bolha é um município. O tamanho mostra a população.")
        # Frase-resumo do motor, logo abaixo do subtítulo: o texto da resposta, como veio, com a competência dela.
        resumo_motor = am.get("resumo")
        texto_resumo = (resumo_motor.get("texto") if isinstance(resumo_motor, dict) else resumo_motor) or ""
        assert texto_resumo.strip(), ("o motor entrega a frase-resumo da distribuição", resumo_motor)
        frase = area.get_by_test_id("analise-resumo")
        expect(frase).to_be_visible()
        expect(frase).to_have_attribute("aria-live", "polite")
        expect(frase).to_have_text(texto_resumo.strip())
        expect(frase).to_contain_text(re.compile("|".join(re.escape(forma) for forma in formas_da_competencia(am["competencia"]))))
        # Com os municípios à vista, o mapa fica disponível, e o motivo dos estados sai.
        expect(area.get_by_test_id("analise-desenho-mapa")).not_to_have_attribute("aria-disabled", "true")
        expect(area.get_by_test_id("analise-desenho-motivo")).to_have_count(0)
        expect(area).to_have_attribute("data-desenho", "grafico")
        expect(area.get_by_test_id("analise-selecao-resumo")).to_contain_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        expect(aviso).to_contain_text("Para voltar aos estados, use Desfazer, no alto.")
        expect(desfazer).to_have_text("Desfazer")
        expect(desfazer).to_have_attribute("title", "Desfazer: abrir os municípios de Amazonas")
        # Desfazer devolve os estados, como estavam (sem pedir de novo: a resposta está na memória da tela); a bolha abre de novo.
        calls = len(painel_calls)
        aperta(desfazer)
        drawn(esperados(estados))
        expect(area).to_have_attribute("data-estado", "E1")
        expect(desfazer).to_have_attribute("title", "Desfazer: abrir a Análise de Distribuição")
        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start'})")
        bolha_am.focus()
        bolha_am.press("Enter")
        drawn(ids_am)
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "desfazer e abrir de novo vêm da memória da tela"
        # A Seleção mostra o estado aberto, com os municípios marcados, no nível Municípios; os estados continuam guardados.
        aba_selecao()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        expect(territorios.get_by_test_id("analise-nivel-municipios")).to_have_attribute("aria-checked", "true")
        expect(territorios.get_by_test_id("analise-nivel-estados")).to_contain_text(re.compile(r"(\d+) de \1 marcados"))
        linha_am = territorios.locator('[data-testid="analise-grupo"][data-id="' + AM + '"]')
        expect(linha_am).to_have_attribute("data-aberto", "true")
        lista_am = linha_am.get_by_test_id("analise-grupo-unidades")
        unidades_am = lista_am.get_by_test_id("analise-unidade")
        total_am = unidades_am.count()
        assert total_am == len(am["itens"]), (total_am, len(am["itens"]))
        assert all(caixa.is_checked() for caixa in lista_am.locator("input[type=checkbox]").all())
        # À direita, o estado inteiro numa linha ("todos os N"), sem a lista dos municípios.
        grupo_am_direita = territorios.locator('[data-testid="analise-selecionado"][data-grupo="' + AM + '"]')
        expect(grupo_am_direita).to_contain_text("Amazonas")
        expect(grupo_am_direita).to_contain_text("todos os " + str(total_am))
        expect(grupo_am_direita.get_by_test_id("analise-selecionado-unidade")).to_have_count(0)
        # Dica no mouse (a maior bolha) e no foco (outra bolha), na aba da análise.
        aba_analise("distribuicao")
        com_valor = [item for item in am["itens"] if item["id"] in ids_am]
        maior = max(com_valor, key=lambda item: item["populacao"] or 0)
        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start'})")
        area.locator('[data-testid="analise-bolha"][data-id="' + maior["id"] + '"]').hover()
        expect(dica).to_contain_text(maior["rotulo"])
        expect(dica).to_contain_text("por 1.000 habitantes")
        page.mouse.move(2, 2)
        outra = next(item for item in com_valor if item["id"] != maior["id"])
        area.locator('[data-testid="analise-bolha"][data-id="' + outra["id"] + '"]').focus()
        expect(dica).to_contain_text(outra["rotulo"])
        shot("02-amazonas")

        # 4. Marcar e desmarcar na lista do estado aberto: tirar PARINTINS pede os demais; "Desmarcar os municípios do Amazonas"
        # esvazia sem pedir nada e o Desfazer desfaz; "Marcar todos os municípios do Amazonas" volta ao estado inteiro; o resumo diz
        # quais (com um ou dois, os nomes).
        aba_selecao()
        grupo_voltar = territorios.get_by_test_id("analise-grupo-voltar")
        expect(grupo_voltar).to_have_text("Voltar aos estados")
        # "Voltar aos estados" (24/10/2026, segunda rodada): maior e preenchido, como os botões de destaque, e distinto do Desfazer do
        # alto (outro lugar, outro nome e outra cor); só fecha a lista do estado.
        estilo_grupo, estilo_global = grupo_voltar.evaluate(ESTILO), desfazer.evaluate(ESTILO)
        assert estilo_grupo["fundo"] not in ("rgba(0, 0, 0, 0)", "transparent"), ("preenchido", estilo_grupo)
        assert estilo_grupo["fundo"] != estilo_global["fundo"], ("distinto do Desfazer do alto", estilo_grupo, estilo_global)
        assert estilo_grupo["altura"] >= 38 and estilo_grupo["fonte"] >= 13 and estilo_grupo["peso"] >= 600, ("evidente", estilo_grupo)
        assert grupo_voltar.bounding_box()["y"] > desfazer.bounding_box()["y"] + 20, "na lista do estado, abaixo do Desfazer do alto"
        _, sent = ok(lambda: marca(lista_am.locator('[data-testid="analise-unidade"][data-id="' + PARINTINS + '"] input')))
        restantes = {item.get_attribute("data-id") for item in unidades_am.all()} - {PARINTINS}
        assert sent["base"]["municipios"]["estados"] == [] and set(sent["base"]["municipios"]["ids"]) == restantes, sent
        nomes_am = {item["id"]: item["rotulo"] for item in am["itens"]}
        texto_restantes = (" e ".join(sorted(nomes_am[i] for i in restantes)) if len(restantes) <= 2
                           else str(len(restantes)) + " municípios do Amazonas")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(texto_restantes)
        expect(area.locator('[data-testid="analise-bolha"][data-id="' + PARINTINS + '"]')).to_have_count(0)
        # O passo de um município só começa pelo verbo: o nome dele fica como é no texto do Desfazer.
        expect(desfazer).to_have_attribute("title", "Desfazer: desmarcar " + nomes_am[PARINTINS])
        # À direita, em tempo real: o estado com "N de M" e cada município marcado, com o × dele.
        expect(grupo_am_direita).to_contain_text(str(len(restantes)) + " de " + str(total_am))
        expect(grupo_am_direita.get_by_test_id("analise-selecionado-unidade")).to_have_count(len(restantes))
        expect(grupo_am_direita.locator('[data-testid="analise-selecionado-unidade"][data-id="' + PARINTINS + '"]')).to_have_count(0)
        calls = len(painel_calls)
        aperta(lista_am.get_by_test_id("analise-desmarcar-todos"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        # Sem seleção, nenhum resultado anterior fica à vista: nem bolhas, nem a frase-resumo.
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-resumo")).to_have_text("")  # a região da frase fica, vazia
        assert all(not caixa.is_checked() for caixa in lista_am.locator("input[type=checkbox]").all())
        expect(territorios.get_by_test_id("analise-selecao-aviso")).to_have_text(
            "Municípios do Amazonas desmarcados. Para desfazer, use o botão Desfazer, no alto.")
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "sem unidades marcadas, nada é pedido ao motor"
        aperta(desfazer)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(texto_restantes)
        expect(territorios.get_by_test_id("analise-selecao-aviso")).to_have_count(0)
        expect(aviso).to_have_text("Desfeito: municípios do Amazonas desmarcados.")
        aperta(lista_am.get_by_test_id("analise-desmarcar-todos"))
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        # A busca, no alto: pelo código, marca um município sem abrir lista nenhuma; o resumo diz qual, e a lista da direita mostra
        # o estado com ele.
        busca.fill("130420")
        _, sent = ok(lambda: marca(territorios.locator('[data-testid="analise-busca-item"][data-id="' + TEFE + '"] input')))
        assert sent["base"] == {"municipios": {"todos": False, "estados": [], "ids": [TEFE]}}, sent
        drawn([TEFE])
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(nomes_am[TEFE])
        expect(grupo_am_direita).to_contain_text("1 de " + str(total_am))
        expect(grupo_am_direita.get_by_test_id("analise-selecionado-unidade")).to_have_count(1)
        expect(grupo_am_direita.get_by_test_id("analise-selecionado-unidade")).to_have_attribute("data-id", TEFE)
        busca.fill("")
        aperta(lista_am.get_by_test_id("analise-marcar-todos"))
        drawn(ids_am)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        shot("03-lista")

        # 5. A seleção cumulativa entre estados (o defeito de 24/10/2026: abrir outro estado trocava a seleção pelo estado aberto):
        # um município do Amazonas e um de São Paulo ficam marcados juntos; abrir a lista de outro estado não muda nada.
        aperta(lista_am.get_by_test_id("analise-desmarcar-todos"))
        _, sent = ok(lambda: marca(lista_am.locator('[data-testid="analise-unidade"][data-id="' + MANAUS + '"] input')))
        assert sent["base"]["municipios"] == {"todos": False, "estados": [], "ids": [MANAUS]}, sent
        aperta(territorios.get_by_test_id("analise-grupo-voltar"))
        linha_sp = territorios.locator('[data-testid="analise-grupo"][data-id="35"]')
        calls = len(painel_calls)
        aperta(linha_sp.get_by_test_id("analise-grupo-ver"))
        lista_sp = territorios.locator('[data-testid="analise-grupo"][data-id="35"]').get_by_test_id("analise-grupo-unidades")
        expect(lista_sp).to_be_visible()
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "abrir a lista de outro estado não muda a seleção nem pede nada ao motor"
        primeira_sp = lista_sp.get_by_test_id("analise-unidade").first
        id_sp = primeira_sp.get_attribute("data-id")
        _, sent = ok(lambda: marca(primeira_sp.locator("input")))
        # Os dois juntos: MANAUS e o de São Paulo (que vira o estado inteiro quando é o último que faltava, como no catálogo
        # sintético, em que São Paulo tem um só).
        base_sp = sent["base"]["municipios"]
        assert MANAUS in base_sp["ids"] and (id_sp in base_sp["ids"] or base_sp["estados"] == ["35"]) and not base_sp["todos"], sent
        selecionados = territorios.get_by_test_id("analise-selecionado")
        expect(selecionados).to_have_count(2)
        expect(territorios.locator('[data-testid="analise-selecionado"][data-grupo="' + AM + '"]')).to_contain_text("Amazonas")
        expect(territorios.locator('[data-testid="analise-selecionado"][data-grupo="35"]')).to_contain_text("São Paulo")
        # Voltar aos estados (da lista) e abrir o Amazonas de novo não desfaz nada.
        aperta(territorios.get_by_test_id("analise-grupo-voltar"))
        aperta(linha_am.get_by_test_id("analise-grupo-ver"))
        expect(lista_am.locator('[data-testid="analise-unidade"][data-id="' + MANAUS + '"] input')).to_be_checked()
        # Na lista da direita (24/10/2026, segunda rodada): o × de MANAUS tira só ela; o Desfazer a devolve. O × do estado tira o
        # estado inteiro; o Desfazer também o devolve.
        tirar_manaus = territorios.locator('[data-testid="analise-selecionado-unidade"][data-id="' + MANAUS + '"]').get_by_role("button")
        expect(tirar_manaus).to_have_attribute("aria-label", "Tirar " + nomes_am[MANAUS])
        _, sent = ok(lambda: aperta(tirar_manaus))
        assert MANAUS not in sent["base"]["municipios"]["ids"] and (id_sp in sent["base"]["municipios"]["ids"] or
                                                                    sent["base"]["municipios"]["estados"] == ["35"]), sent
        expect(selecionados).to_have_count(1)
        expect(lista_am.locator('[data-testid="analise-unidade"][data-id="' + MANAUS + '"] input')).not_to_be_checked()
        expect(desfazer).to_have_attribute("title", "Desfazer: tirar " + nomes_am[MANAUS])
        aperta(desfazer)
        expect(selecionados).to_have_count(2)
        expect(lista_am.locator('[data-testid="analise-unidade"][data-id="' + MANAUS + '"] input')).to_be_checked()
        # Tirar o estado inteiro dá a mesma escolha de antes (só São Paulo): a resposta vem da memória da tela.
        tirar_am = territorios.locator('[data-testid="analise-selecionado"][data-grupo="' + AM + '"]').get_by_test_id(
            "analise-selecionado-tirar-grupo")
        expect(tirar_am).to_have_attribute("aria-label", "Tirar municípios do Amazonas")
        aperta(tirar_am)
        expect(selecionados).to_have_count(1)
        expect(territorios.locator('[data-testid="analise-selecionado"][data-grupo="' + AM + '"]')).to_have_count(0)
        expect(lista_am.locator('[data-testid="analise-unidade"][data-id="' + MANAUS + '"] input')).not_to_be_checked()
        aperta(desfazer)
        expect(selecionados).to_have_count(2)
        shot("03b-cumulativa")
        # Cada nível guarda a sua escolha: os estados voltam como estavam, e os municípios também.
        aperta(territorios.get_by_test_id("analise-nivel-estados"))
        expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text(re.compile(r"Todos os estados \(\d+\)"))
        drawn(esperados(estados))
        aperta(territorios.get_by_test_id("analise-nivel-municipios"))
        expect(selecionados).to_have_count(2)
        # Limpar seleção (a vassoura do alto, 24/10/2026): tira só os territórios do nível em uso (aqui, os municípios; decisão 5,
        # 25/10/2026), sem apagar os dados carregados (a lista do estado aberto continua, com os municípios, e a fonte também) nem a
        # escolha guardada dos estados; o Desfazer devolve tudo. Depois, de novo o Limpar e o Amazonas inteiro, para os passos
        # seguintes.
        fonte_antes = page.get_by_test_id("current-source").inner_text()
        aperta(limpar)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        expect(territorios.get_by_test_id("analise-selecao-aviso")).to_have_text("Seleção limpa. Para desfazer, use o botão Desfazer, no alto.")
        expect(aviso).to_have_text("Seleção limpa: nenhum território na análise. A base de dados continua carregada. Para desfazer, use o botão Desfazer.")
        expect(territorios.get_by_test_id("analise-nivel-estados")).to_contain_text(re.compile(r"(\d+) de \1 marcados"))
        expect(linha_am).to_have_attribute("data-aberto", "true")
        expect(unidades_am).to_have_count(total_am)
        expect(page.get_by_test_id("current-source")).to_have_text(fonte_antes)
        expect(limpar).to_be_disabled()
        expect(desfazer).to_have_attribute("title", "Desfazer: limpar seleção")
        aperta(desfazer)
        expect(selecionados).to_have_count(2)
        expect(territorios.get_by_test_id("analise-nivel-estados")).to_contain_text(re.compile(r"(\d+) de \1 marcados"))
        aperta(limpar)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        aperta(lista_am.get_by_test_id("analise-marcar-todos"))
        drawn(ids_am)

        # 6. Quantidade troca o eixo, sem escala logarítmica automática. Com os quintis do mapa no pedido (eles seguem o
        # indicador), a troca pede ao motor o mesmo universo com a quantidade; o gráfico continua sem grupos. A volta à densidade
        # vem da memória da tela, sem novo pedido. A frase-resumo é sempre a do cálculo à vista.
        aba_analise("distribuicao")
        quantidade, sent = ok(lambda: area.get_by_test_id("analise-indicador-quantidade").click())
        assert sent.get("indicador") == "quantidade" and sent["base"] == universo_am, sent
        assert sent.get("grupos_mapa") == {"tipo": "quintis"} and "grupos" not in sent, sent
        expect(eixo_y).to_have_attribute("data-eixo", "quantidade")
        drawn(esperados(quantidade, "quantidade"))
        confere_valores(quantidade, "quantidade")
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("Quantidade de médicos")
        expect(ajustes.get_by_test_id("analise-indicador-quantidade")).to_have_attribute("aria-checked", "true")
        resumo_q = quantidade.get("resumo")
        texto_q = ((resumo_q.get("texto") if isinstance(resumo_q, dict) else resumo_q) or "").strip()
        if texto_q:
            expect(frase).to_have_text(texto_q)
        calls = len(painel_calls)
        area.get_by_test_id("analise-indicador-densidade").click()
        expect(eixo_y).to_have_attribute("data-eixo", "densidade")
        expect(eixo_y).to_have_attribute("data-escala", "linear")
        drawn(ids_am)
        expect(frase).to_have_text(texto_resumo.strip())
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "a volta à densidade vem da memória da tela, sem novo pedido"

        # 7. Régua: "acima de" pelo teclado; aparecem só as unidades do corte, nada é recalculado. O arraste é um passo só do
        # Desfazer, que devolve a régua de antes.
        regua = abre("regua").get_by_test_id("analise-regua")
        dominio = am["dominios"]["densidade"]
        assert [float(regua.get_attribute("data-dominio-min")), float(regua.get_attribute("data-dominio-max"))] == dominio
        # Ao rolar, o painel da função fica preso abaixo de Desfazer e Limpar seleção: o título e o × à vista, sem nada por cima.
        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start', behavior: 'instant'})")
        page.wait_for_timeout(200)
        titulo_painel = area.get_by_test_id("analise-painel").locator("#analise-painel-titulo")
        caixa_titulo, caixa_controles = titulo_painel.bounding_box(), controles.bounding_box()
        assert caixa_titulo["y"] >= caixa_controles["y"] + caixa_controles["height"] - 1, \
            ("o título do painel abaixo dos controles do alto", caixa_titulo, caixa_controles)
        assert titulo_painel.evaluate("e => { const c = e.getBoundingClientRect(); "
                                      "const alvo = document.elementFromPoint(c.left + c.width / 2, c.top + c.height / 2); "
                                      "return !!alvo && e.contains(alvo); }"), "nada por cima do título do painel"
        minimo_cursor = regua.get_by_test_id("analise-regua-min")
        minimo_cursor.focus()
        for _ in range(3):
            minimo_cursor.press("PageUp")
        minimo, maximo = float(minimo_cursor.get_attribute("aria-valuenow")), float(regua.get_by_test_id("analise-regua-max").get_attribute("aria-valuenow"))
        assert dominio[0] < minimo <= maximo == dominio[1], (minimo, maximo, dominio)
        drawn(esperados(am, corte=(minimo, maximo)))
        maximo_cursor = regua.get_by_test_id("analise-regua-max")
        maximo_cursor.scroll_into_view_if_needed()
        caixa = maximo_cursor.bounding_box()
        page.mouse.move(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
        page.mouse.down()
        page.mouse.move(caixa["x"] + caixa["width"] / 2 - 30, caixa["y"] + caixa["height"] / 2, steps=6)
        page.mouse.up()
        maximo = float(maximo_cursor.get_attribute("aria-valuenow"))
        assert minimo <= maximo < dominio[1], (minimo, maximo)
        drawn(esperados(am, corte=(minimo, maximo)))
        expect(area.get_by_test_id("analise-corte-regua")).to_have_count(2)
        assert len(painel_calls) == calls, "a régua só esconde: nada é recalculado"
        shot("04-regua")
        # O ajuste da régua é um passo do Desfazer (o arraste contínuo, um passo só): Desfazer desfaz o arraste do limite superior.
        expect(desfazer).to_have_attribute("title", "Desfazer: ajustar a régua")
        aperta(desfazer)
        page.wait_for_function("v => Number(document.querySelector('[data-testid=analise-regua]').dataset.maximo) === v",
                               arg=dominio[1], timeout=5000)
        assert len(painel_calls) == calls, "o Desfazer da régua também não recalcula"
        if regua.get_by_test_id("analise-regua-limpar").is_enabled():
            aperta(regua.get_by_test_id("analise-regua-limpar"))
        drawn(ids_am)
        fecha()

        # 8. Distribuição com grupos por posição (CAP-DIS-02): o grupo de cada bolha e as contagens da legenda vêm do motor.
        grupos, sent = ok(lambda: area.get_by_test_id("analise-agrupar").select_option("quartis"))
        assert sent["grupos"] == {"tipo": "quartis"} and sent.get("indicador") == "densidade", sent
        drawn(esperados(grupos))
        desenhadas = bubbles()
        for item in grupos["itens"]:
            if item["id"] in desenhadas and item.get("grupo"):
                assert desenhadas[item["id"]]["grupo"] == str(item["grupo"]["indice"]), (desenhadas[item["id"]], item)
        legenda = area.get_by_test_id("analise-legenda-cor")
        expect(legenda).to_have_attribute("data-camada", "grupos")
        contagens = grupos["grupos"]["contagens"]
        valores = list(contagens.values()) if isinstance(contagens, dict) else contagens
        for indice, valor in enumerate(valores, start=1):
            expect(legenda.locator('[data-testid="analise-legenda-cor-item"][data-chave="' + str(indice) + '"]')).to_have_attribute("data-contagem", str(valor))
        shot("05-quartis")
        area.get_by_test_id("analise-agrupar").select_option("nenhum")
        drawn(ids_am)

        # 9. Análise espacial. A disponibilidade vem do motor (`disponibilidade.espacial`). Disponível: o Território de referência
        # (24/10/2026, segunda rodada, no lugar da referência por critério, pelo nome ou por um conjunto), num fluxo só e sem
        # valores padrão: a relação, a delimitação, o atributo, o operador e o valor de corte; primeiro os elegíveis (a delimitação
        # e a condição), depois o mais próximo ou o mais distante de cada município, nunca ele mesmo; X = distância. Indisponível
        # (por exemplo, quando o referencial, SIRGAS 2000 ou WGS 84, não é premissa da fonte): a aba fica desabilitada, com o motivo
        # do motor, e nada é pedido.
        espacial_motor = (am.get("disponibilidade") or {}).get("espacial") or {}
        if espacial_motor.get("disponivel") is False:
            assert not real, ("a base do Brasil tem as coordenadas: a análise espacial fica disponível", espacial_motor)
            calls = len(painel_calls)
            expect(area.get_by_test_id("analise-familia-espacial")).to_have_attribute("data-disponivel", "false")
            aperta(area.get_by_test_id("analise-familia-espacial"))
            # A aba abre com a apresentação e o motivo do motor; o desenho continua com a análise anterior.
            expect(area).to_have_attribute("data-aba", "espacial")
            expect(area.get_by_test_id("analise-apresentacao")).to_have_attribute("data-aba", "espacial")
            expect(area.get_by_test_id("analise-familia-motivo")).to_contain_text(str(espacial_motor.get("motivo") or "")[:60])
            expect(area.get_by_test_id("analise-familia-motivo")).to_contain_text("O desenho abaixo continua com a Análise de Distribuição.")
            expect(area.get_by_test_id("analise-ajustes")).to_have_count(0)
            expect(area).to_have_attribute("data-familia", "distribuicao")
            page.wait_for_timeout(400)
            assert len(painel_calls) == calls, "a família indisponível não pede nada ao motor"
            notas.append("análise espacial indisponível no motor neste catálogo: conferidos a aba e o motivo, sem o Território de "
                         "referência")
        else:
            aperta(area.get_by_test_id("analise-familia-espacial"))
            # Os ajustes da análise espacial: o mesmo indicador, a competência e o Território de referência (o resumo e o botão).
            expect(ajustes).to_have_attribute("data-familia", "espacial")
            expect(ajustes.get_by_test_id("analise-indicador-densidade")).to_have_attribute("aria-checked", "true")
            expect(ajustes.get_by_test_id("analise-referencia-resumo")).to_have_text("nenhum ainda")
            expect(ajustes.get_by_test_id("analise-referencia-escolher")).to_have_text("Definir o território de referência")
            for ausente in ("analise-agrupar", "analise-janela-escolher", "analise-visao-classes", "analise-escala"):
                expect(ajustes.get_by_test_id(ausente)).to_have_count(0)
            # Com os municípios na análise, o painel abre sozinho, com o título "Território de referência" (sem "Referência da
            # distância") e a escolha passo a passo.
            painel_ref = area.get_by_test_id("analise-painel")
            expect(painel_ref).to_have_attribute("data-painel", "referencia")
            expect(painel_ref.locator("#analise-painel-titulo")).to_have_text("Território de referência")
            expect(area).not_to_contain_text("Referência da distância")
            referencia = painel_ref.get_by_test_id("analise-referencia")
            expect(referencia).to_be_visible()
            expect(referencia.get_by_test_id("analise-nota-tpl11")).to_contain_text("linha reta")
            expect(referencia).to_contain_text("O próprio município nunca é a sua referência.")
            for antigo in ("analise-ref-criterio", "analise-ref-ordem", "analise-ref-listar", "analise-ref-candidatos", "analise-ref-primeiro",
                           "analise-ref-busca"):
                expect(referencia.get_by_test_id(antigo)).to_have_count(0)
            # Nenhum valor padrão: nada escolhido, o pedido não sai, e a tela diz o que falta.
            relacao_proxima = referencia.get_by_test_id("analise-ref-relacao-mais_proxima")
            relacao_distante = referencia.get_by_test_id("analise-ref-relacao-mais_distante")
            expect(relacao_proxima).to_have_text("Mais próximo")
            expect(relacao_distante).to_have_text("Mais distante")
            for botao in (relacao_proxima, relacao_distante, referencia.get_by_test_id("analise-ref-operador-maior"),
                          referencia.get_by_test_id("analise-ref-operador-menor")):
                expect(botao).to_have_attribute("aria-checked", "false")
            expect(referencia.get_by_test_id("analise-ref-operador-maior")).to_have_text("Maior que")
            expect(referencia.get_by_test_id("analise-ref-operador-menor")).to_have_text("Menor que")
            delimitacao = referencia.get_by_test_id("analise-ref-delimitacao")
            atributo = referencia.get_by_test_id("analise-ref-atributo")
            valor_corte = referencia.get_by_test_id("analise-ref-valor")
            expect(delimitacao).to_have_value("")
            expect(atributo).to_have_value("")
            expect(valor_corte).to_be_disabled()  # sem o atributo, o valor de corte espera (a unidade depende dele)
            expect(referencia.get_by_test_id("analise-ref-falta")).to_have_text(
                "Falta escolher: a relação espacial, a delimitação, o atributo da condição, o operador, o valor de corte.")
            aplicar_ref = referencia.get_by_test_id("analise-ref-aplicar")
            expect(aplicar_ref).to_be_disabled()
            # A delimitação segue os níveis que a fonte tem: na base do Brasil, o estado, os estados escolhidos, a região, as
            # regiões escolhidas e o país inteiro.
            opcoes = delimitacao.locator("option").evaluate_all("els => els.map(e => [e.value, e.textContent])")
            assert opcoes == [["", "Escolha"], ["mesmo_grupo", "No mesmo estado de cada município"], ["grupos", "Estados escolhidos"],
                              ["mesma_regiao", "Na mesma região de cada município"], ["regioes", "Regiões escolhidas"],
                              ["todos", "No Brasil inteiro"]], opcoes
            delimitacao.select_option("regioes")
            expect(referencia.get_by_test_id("analise-ref-valor-opcao")).to_have_count(5)  # as cinco Grandes Regiões
            expect(referencia.get_by_test_id("analise-ref-falta")).to_contain_text("as regiões")
            # O valor de corte com a unidade e a validação do atributo: a população, um inteiro de habitantes.
            atributo.select_option("populacao")
            expect(valor_corte).to_be_enabled()
            expect(referencia).to_contain_text("Valor de corte (habitantes)")
            valor_corte.fill("2,5")
            expect(valor_corte).to_have_attribute("aria-invalid", "true")
            expect(referencia).to_contain_text("Use um número inteiro não negativo.")
            # A condição: população maior que a mediana dos municípios do Amazonas, no mesmo estado de cada município. Os elegíveis
            # saem desta resposta (a dos municípios do Amazonas): quem atende à condição.
            populacoes = sorted(int(round(item["populacao"])) for item in am["itens"] if item.get("populacao") is not None)
            limiar = populacoes[len(populacoes) // 2]
            elegiveis = {item["id"] for item in am["itens"] if item.get("populacao") is not None and item["populacao"] > limiar}
            assert elegiveis, "algum município do Amazonas atende à condição"
            delimitacao.select_option("mesmo_grupo")
            valor_corte.fill(milhar(limiar))  # com o ponto de milhar, como a pessoa escreve
            aperta(referencia.get_by_test_id("analise-ref-operador-maior"))
            aperta(relacao_proxima)
            expect(relacao_proxima).to_have_attribute("aria-checked", "true")
            expect(valor_corte).not_to_have_attribute("aria-invalid", "true")
            expect(referencia.get_by_test_id("analise-ref-previa")).to_have_text(
                "Para cada município, o município mais próximo entre os municípios do mesmo estado de cada município com população "
                "maior que " + milhar(limiar) + " habitantes.")
            expect(aplicar_ref).to_be_enabled()
            calls = len(painel_calls)
            response, sent = respond(lambda: aperta(aplicar_ref))
            assert sent["referencia"] == {"relacao": "mais_proxima", "delimitacao": {"tipo": "mesmo_grupo"},
                                          "condicao": {"atributo": "populacao", "operador": ">", "valor": limiar}}, sent
            assert sent["base"] == universo_am, ("a seleção continua a mesma", sent)
            if real:
                assert response.status == 200, response.text()[:2000]
            if response.status == 422:
                # O motor recusou a distância (catálogo sintético, versão externa). Quando ele oferece a escolha da premissa, a
                # tela mostra as opções que ele mandou (sem lista fixa) e pede de novo com a escolhida.
                erro = area.get_by_test_id("analise-erro")
                corpo = response.json()
                expect(erro).to_contain_text(str(corpo["detail"])[:60])
                pendencia = corpo.get("pendencia")
                if pendencia and pendencia.get("opcoes"):
                    opcoes = erro.get_by_test_id("analise-pendencia-opcao")
                    expect(opcoes).to_have_count(len(pendencia["opcoes"]))
                    for botao, opcao in zip(opcoes.all(), pendencia["opcoes"]):
                        valor = opcao if isinstance(opcao, str) else (opcao.get("valor") or opcao.get("id"))
                        expect(botao).to_have_attribute("data-valor", str(valor))
                    escolhida = opcoes.first.get_attribute("data-valor")
                    response, sent = respond(lambda: aperta(opcoes.first))
                    assert sent.get("premissas", {}).get(pendencia["chave"]) == escolhida, sent
            if response.status == 200:
                proxima = response.json()
                referencia_resposta = proxima["referencia"]
                assert referencia_resposta["tipo"] == "elegiveis" and referencia_resposta["relacao"] == "mais_proxima", referencia_resposta
                assert referencia_resposta["delimitacao"]["texto"] == "do mesmo estado de cada município", referencia_resposta
                assert referencia_resposta["elegiveis"]["atende"] >= len(elegiveis), referencia_resposta
                expect(eixo_x).to_have_attribute("data-eixo", "distancia")
                expect(eixo_y).to_have_attribute("data-eixo", "densidade")
                drawn(esperados(proxima, distancia=True))
                desenhadas = bubbles()
                for item in proxima["itens"]:
                    refs = referencias_do_item(item)
                    # Primeiro os elegíveis: a referência de cada município atende à condição, no mesmo estado, e nunca é ele.
                    assert set(refs) <= elegiveis and item["id"] not in refs, (item["id"], refs, sorted(elegiveis))
                    if refs:
                        assert item.get("distancia_km") is not None, item
                    else:
                        # Sem referência (sem coordenada válida ou sem outro elegível): o motivo, nunca distância zero.
                        assert item.get("distancia_km") is None and item.get("motivos"), item
                    if not elegiveis - {item["id"]}:
                        # Só o próprio município atende à condição no estado: sem referência, com o motivo.
                        assert not refs and any("Sem território de referência" in motivo for motivo in item.get("motivos") or []), item
                    if item["id"] in desenhadas:
                        assert float(desenhadas[item["id"]]["distancia"]) == item["distancia_km"], (desenhadas[item["id"]], item)
                assert any(referencias_do_item(item) for item in proxima["itens"]), "algum município do Amazonas tem referência"
                expect(area.get_by_test_id("analise-nota-distancia")).to_contain_text("linha reta")
                expect(area.get_by_test_id("analise-titulo")).to_contain_text("e distância até o território de referência")
                expect(area.get_by_test_id("analise-ref-sem-resultado")).to_have_count(0)
                # O resumo nos ajustes diz a relação, a delimitação e a condição, com os textos do motor.
                expect(ajustes.get_by_test_id("analise-referencia-resumo")).to_have_text(
                    "Mais próximo · do mesmo estado de cada município · " + referencia_resposta["condicao"]["texto"])
                expect(ajustes.get_by_test_id("analise-referencia-escolher")).to_have_text("Mudar")
                # A dica da bolha diz qual é o território de referência dela.
                com_ref = next(item for item in proxima["itens"] if item["id"] in desenhadas and referencias_do_item(item))
                fecha()
                area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start', behavior: 'instant'})")
                area.locator('[data-testid="analise-bolha"][data-id="' + com_ref["id"] + '"]').focus()
                expect(dica).to_contain_text("Território de referência (o mais próximo")
                expect(dica).to_contain_text(com_ref["referencia_do_item"]["rotulo"])
                page.evaluate("document.activeElement && document.activeElement.blur()")
                # Na análise espacial, o convite ao mapa ("onde ficam?"), com a vista no gráfico.
                expect(area.get_by_test_id("analise-convite-mapa")).to_have_text("Ver onde ficam no mapa")
                expect(area).to_have_attribute("data-desenho", "grafico")
                sem_bastidor("Análise Espacial")
                shot("06-espacial")
                # Reconfigurar sem recomeçar: o painel volta com a escolha em uso; trocar só a relação pede de novo, com a mesma
                # seleção, e o mais distante fica a pelo menos a distância do mais próximo.
                aperta(ajustes.get_by_test_id("analise-referencia-escolher"))
                referencia = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
                expect(referencia.get_by_test_id("analise-ref-relacao-mais_proxima")).to_have_attribute("aria-checked", "true")
                expect(referencia.get_by_test_id("analise-ref-delimitacao")).to_have_value("mesmo_grupo")
                expect(referencia.get_by_test_id("analise-ref-atributo")).to_have_value("populacao")
                expect(referencia.get_by_test_id("analise-ref-ativa")).to_contain_text("Em uso:")
                aperta(referencia.get_by_test_id("analise-ref-relacao-mais_distante"))
                distante, sent = ok(lambda: aperta(referencia.get_by_test_id("analise-ref-aplicar")))
                assert sent["referencia"]["relacao"] == "mais_distante" and sent["base"] == universo_am, sent
                assert distante["referencia"]["relacao"] == "mais_distante", distante["referencia"]
                perto = {item["id"]: item.get("distancia_km") for item in proxima["itens"]}
                for item in distante["itens"]:
                    refs = referencias_do_item(item)
                    assert set(refs) <= elegiveis and item["id"] not in refs, (item["id"], refs)
                    if item.get("distancia_km") is not None and perto.get(item["id"]) is not None:
                        assert item["distancia_km"] >= perto[item["id"]], (item["id"], item["distancia_km"], perto[item["id"]])
                drawn(esperados(distante, distancia=True))
                expect(ajustes.get_by_test_id("analise-referencia-resumo")).to_contain_text("Mais distante · ")
                # Sem elegíveis: ninguém da base atende à condição; nenhuma distância vira zero, e a mensagem diz o que aconteceu e
                # o que fazer. O Desfazer devolve a definição anterior.
                referencia.get_by_test_id("analise-ref-valor").fill(milhar(10 ** 9))
                nenhum, sent = ok(lambda: aperta(referencia.get_by_test_id("analise-ref-aplicar")))
                assert sent["referencia"]["condicao"]["valor"] == 10 ** 9, sent
                assert nenhum["referencia"]["elegiveis"]["atende"] == 0, nenhum["referencia"]
                assert all(item.get("distancia_km") is None and not referencias_do_item(item) for item in nenhum["itens"]), nenhum["itens"]
                sem_resultado = area.get_by_test_id("analise-ref-sem-resultado")
                expect(sem_resultado).to_contain_text("Nenhum município da base atende à condição " +
                                                      nenhum["referencia"]["condicao"]["texto"] + ": não há território de referência.")
                expect(area.locator(BOLHAS)).to_have_count(0)
                fecha()
                aperta(sem_resultado.get_by_test_id("analise-ref-sem-resultado-mudar"))
                expect(area.get_by_test_id("analise-painel")).to_have_attribute("data-painel", "referencia")
                fecha()
                expect(desfazer).to_have_attribute("title", "Desfazer: aplicar o território de referência")
                aperta(desfazer)
                drawn(esperados(distante, distancia=True))
                expect(area.get_by_test_id("analise-ref-sem-resultado")).to_have_count(0)
                notas.append("Território de referência conferido no navegador: mais próximo, mais distante, sem elegíveis e o "
                             "Desfazer" + (" (depois da premissa escolhida na pendência do motor)" if sent.get("premissas") else ""))
            else:
                notas.append("o motor recusou a distância neste catálogo (código " + str(response.status) + "): conferidos o "
                             "pedido do Território de referência, a recusa e a volta ao último gráfico calculado")
                if area.get_by_test_id("analise-erro").count():
                    calls = len(painel_calls)
                    aperta(area.get_by_test_id("analise-voltar-calculado"))
                    expect(area.get_by_test_id("analise-erro")).to_have_count(0)
                    expect(eixo_x).to_have_count(0)
                    drawn(ids_am)
                    page.wait_for_timeout(400)
                    assert len(painel_calls) == calls, "voltar ao último gráfico não recalcula"
            fecha()

        # 10. Tendência (24/10/2026): abre com "Entenda esta análise" recolhido, o Período anual (ou, sem ele, o único ritmo da
        # base, RQ-GOV-14) e o Gráfico, mesmo com o mapa à vista antes (o mapa continua como alternativa); os ajustes no alto, o
        # desenho em destaque e a explicação à direita, com a divisória ajustável. As visões: Tendência (o quadro de setas, no
        # lugar das bolhas, com a contagem por classe do motor ao lado), Trajetória (os percentuais do motor, com os períodos do
        # meio no caminho) e Série temporal (toda a série da base ou o intervalo escolhido).
        if area.get_by_test_id("analise-desenho-mapa").get_attribute("aria-disabled") != "true":
            aperta(area.get_by_test_id("analise-desenho-mapa"))
            expect(area).to_have_attribute("data-desenho", "mapa")
        tendencia, sent = ok(lambda: aperta(area.get_by_test_id("analise-familia-tendencia")), condicao=lambda o: "tendencia" in o)
        janela = sent["tendencia"]["competencias"]
        esperada = ["202106", "202206", "202306", "202406"] if real else ["202301", "202306", "202401", "202406"]
        assert janela == esperada and sent["competencia_inicial"] == janela[0] and sent["competencia"] == janela[-1], sent
        assert sent.get("indicador") == "densidade" and "referencia" not in sent and sent["base"] == universo_am, sent
        expect(area).to_have_attribute("data-desenho", "grafico")
        expect(area.get_by_test_id("analise-desenho-grafico")).to_have_attribute("aria-pressed", "true")
        expect(area.get_by_test_id("analise-desenho-mapa")).not_to_have_attribute("aria-disabled", "true")
        entenda = area.get_by_test_id("analise-entenda")
        expect(entenda).to_have_attribute("data-aba", "tendencia")
        expect(entenda).not_to_have_attribute("open", "")
        expect(area.get_by_test_id("analise-apresentacao")).to_be_hidden()
        expect(area.get_by_test_id("analise-aviso-familia")).to_have_count(0)  # o período já vem escolhido
        expect(area.get_by_test_id("analise-painel")).to_have_count(0)  # nenhuma gaveta abre: o período fica nos ajustes
        # Os ajustes da tendência: o mesmo indicador (a troca de aba o mantém), o Período e a visão, sem competência nem grupos e faixas.
        expect(ajustes).to_have_attribute("data-familia", "tendencia")
        expect(ajustes.get_by_test_id("analise-indicador-densidade")).to_have_attribute("aria-checked", "true")
        for controle in ("analise-periodo-anual", "analise-periodo-semestral", "analise-periodo-texto", "analise-visao-classes",
                         "analise-visao-mudanca", "analise-visao-series"):
            expect(ajustes.get_by_test_id(controle)).to_be_visible()
        for ausente in ("analise-competencia", "analise-agrupar", "analise-referencia-escolher", "analise-escala", "analise-janela-escolher",
                        "analise-serie-intervalo"):
            expect(ajustes.get_by_test_id(ausente)).to_have_count(0)
        # O ritmo à vista: na base versionada, o anual (os dois existem); no catálogo sintético (01/2023, 06/2023, 01/2024 e
        # 06/2024), o anual fica desligado, com o motivo, e o semestral, o único da base, vem escolhido.
        ritmo = "anual" if real else "semestral"
        expect(ajustes.get_by_test_id("analise-periodo-" + ritmo)).to_have_attribute("aria-checked", "true")
        expect(ajustes.get_by_test_id("analise-periodo-texto")).to_have_text(
            "Últimos 4 períodos " + ("anuais" if real else "semestrais") + ": " + ", ".join(mm_aaaa(c) for c in janela[:-1]) + " e " +
            mm_aaaa(janela[-1]) + ".")
        if real:
            expect(ajustes.get_by_test_id("analise-periodo-semestral")).to_have_attribute("aria-checked", "false")
            # Trocar pelo semestral pede os últimos 4 períodos semestrais; o Desfazer devolve o anual (da memória da tela).
            _, sent_semestral = ok(lambda: aperta(ajustes.get_by_test_id("analise-periodo-semestral")))
            assert sent_semestral["tendencia"]["competencias"] == ["202301", "202306", "202401", "202406"], sent_semestral
            expect(desfazer).to_have_attribute("title", "Desfazer: trocar o período para semestral")
            aperta(desfazer)
            expect(ajustes.get_by_test_id("analise-periodo-anual")).to_have_attribute("aria-checked", "true")
        else:
            expect(ajustes.get_by_test_id("analise-periodo-anual")).to_be_disabled()
            expect(ajustes.get_by_test_id("analise-periodo-motivo-anual")).to_contain_text("não tem 4 períodos anuais seguidos")
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("Tendência da densidade de médicos")
        # As visões com os nomes de 24/10/2026, nesta ordem; a Tendência escolhida.
        nomes_visoes = ajustes.get_by_role("group", name="Visão da tendência").get_by_role("button").all_text_contents()
        assert nomes_visoes == ["Tendência", "Trajetória", "Série temporal"], nomes_visoes
        expect(ajustes.get_by_test_id("analise-visao-classes")).to_have_attribute("aria-pressed", "true")
        # Tendência: o quadro de setas, uma linha por unidade com o indicador, no lugar das bolhas. A classe de cada linha é a do
        # motor, e cada seta segue o sinal de uma velocidade do motor (alta, queda ou pausa); as linhas vêm agrupadas pela classe,
        # na ordem da SPEC, 50 por página. A coluna da classe se chama "Tendência".
        quadro = area.get_by_test_id("analise-setas")
        expect(quadro).to_be_visible()
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(quadro.locator(".analise-setas-cabecalho > span").last).to_have_text("Tendência")
        expect(area).not_to_contain_text("Classe (do motor)")
        com_valor = esperados(tendencia)
        linhas = quadro.get_by_test_id("analise-seta-linha")
        expect(linhas).to_have_count(min(len(com_valor), 50))
        lidas = linhas.evaluate_all("els => els.map(e => ({id: e.dataset.id, classe: e.dataset.classe, selecionado: e.dataset.selecionado, "
                                    "sinais: [...e.querySelectorAll('[data-testid=analise-seta]')].map(s => s.dataset.sinal), "
                                    "pontos: e.querySelectorAll('[data-testid=analise-seta-ponto]').length}))")
        desenhadas = {linha["id"]: linha for linha in lidas}
        por_id = {item["id"]: item for item in tendencia["itens"]}
        for linha in lidas:
            t = por_id[linha["id"]].get("tendencia") or {}
            classe = t.get("classe") if t.get("avaliavel", True) else None
            assert linha["classe"] == (classe or "NAO_AVALIAVEL"), (linha, t)
            # As velocidades do motor vêm em números (ou objetos com o valor); as observações, em objetos com a competência e o valor.
            velocidades = [v if isinstance(v, (int, float)) else (v or {}).get("valor") for v in (t.get("velocidades") or [])]
            sinais = ["alta" if v > 0 else "queda" if v < 0 else "pausa" for v in velocidades if v is not None]
            assert linha["sinais"] == sinais, (linha, t)
            observacoes = t.get("observacoes") if isinstance(t.get("observacoes"), list) else []
            assert linha["pontos"] == sum(1 for obs in observacoes if obs.get("valor") is not None), (linha, t)
        ordem = ["CRESCIMENTO", "CRESCIMENTO_ACELERADO", "CRESCIMENTO_DESACELERADO", "DECLINIO", "DECLINIO_ACELERADO",
                 "DECLINIO_DESACELERADO", "SEM_CLASSIFICACAO", "NAO_AVALIAVEL"]
        sequencia = [ordem.index(linha["classe"]) for linha in lidas]
        assert sequencia == sorted(sequencia), ("as linhas agrupadas pela classe, na ordem da SPEC", sequencia)
        if len(com_valor) > 50:
            expect(quadro.get_by_test_id("analise-setas-paginas")).to_contain_text("Linhas 1 a 50 de " + milhar(len(com_valor)))
        # O layout da tendência: os ajustes no alto; abaixo, o desenho em destaque e, à direita, a explicação (como ler, a
        # frase-resumo, as contagens por classe, a legenda e as velocidades), separados pela divisória.
        lateral = area.get_by_test_id("analise-tendencia-lateral")
        explicacao = lateral.get_by_test_id("analise-explicacao")
        divisoria = area.get_by_test_id("analise-divisoria")
        expect(explicacao).to_be_visible()
        expect(explicacao).to_contain_text("Como ler")
        expect(explicacao.get_by_test_id("analise-subtitulo")).to_have_text(
            "Cada linha é um município: as setas mostram a alta, a queda ou a pausa de um período para o seguinte.")
        expect(explicacao.get_by_test_id("analise-resumo")).to_have_count(1)
        expect(explicacao.get_by_test_id("analise-setas-legenda")).to_contain_text("Alta")
        expect(explicacao.get_by_test_id("analise-legenda-cor")).to_have_attribute("data-camada", "classes")
        caixa_ajustes, caixa_quadro = ajustes.bounding_box(), quadro.bounding_box()
        caixa_lateral, caixa_divisoria = lateral.bounding_box(), divisoria.bounding_box()
        assert caixa_ajustes["y"] + caixa_ajustes["height"] <= caixa_quadro["y"] + 1, ("os ajustes acima do desenho", caixa_ajustes, caixa_quadro)
        assert caixa_quadro["x"] + caixa_quadro["width"] <= caixa_divisoria["x"] + 1 <= caixa_lateral["x"] + 2, \
            ("o desenho, a divisória e a explicação, da esquerda para a direita", caixa_quadro, caixa_divisoria, caixa_lateral)
        assert caixa_quadro["width"] > caixa_lateral["width"], ("o desenho em destaque", caixa_quadro, caixa_lateral)
        # A divisória: separador vertical com o valor em px; as setas, Home e End mudam a largura da explicação, dentro dos
        # limites (240 px e a metade da área, até 620 px); o arraste com o mouse também.
        expect(divisoria).to_have_attribute("role", "separator")
        expect(divisoria).to_have_attribute("aria-orientation", "vertical")
        expect(divisoria).to_have_attribute("aria-valuemin", "240")
        expect(divisoria).to_have_attribute("aria-valuenow", "340")
        limite = int(divisoria.get_attribute("aria-valuemax"))
        assert 240 < limite <= 620, limite
        assert abs(caixa_lateral["width"] - 340) <= 2, caixa_lateral
        divisoria.focus()
        divisoria.press("ArrowLeft")
        expect(divisoria).to_have_attribute("aria-valuenow", "364")
        page.wait_for_function("w => Math.abs(document.querySelector('[data-testid=analise-tendencia-lateral]').getBoundingClientRect().width - w) <= 2",
                               arg=364, timeout=5000)
        divisoria.press("End")
        expect(divisoria).to_have_attribute("aria-valuenow", str(limite))
        divisoria.press("ArrowLeft")
        expect(divisoria).to_have_attribute("aria-valuenow", str(limite))  # não passa da metade da área
        divisoria.press("Home")
        expect(divisoria).to_have_attribute("aria-valuenow", "240")
        divisoria.press("ArrowRight")
        expect(divisoria).to_have_attribute("aria-valuenow", "240")  # nem fica menor que 240 px
        divisoria.scroll_into_view_if_needed()
        caixa_divisoria, caixa_lateral = divisoria.bounding_box(), lateral.bounding_box()
        direita_da_area = caixa_lateral["x"] + caixa_lateral["width"]
        meio_y = caixa_divisoria["y"] + min(caixa_divisoria["height"] / 2, 60)
        page.mouse.move(caixa_divisoria["x"] + caixa_divisoria["width"] / 2, meio_y)
        page.mouse.down()
        page.mouse.move(direita_da_area - 420, meio_y, steps=8)
        page.mouse.up()
        largura_arrastada = int(divisoria.get_attribute("aria-valuenow"))
        assert abs(largura_arrastada - min(420, limite)) <= 3, (largura_arrastada, limite)
        divisoria.focus()
        for _ in range(6):
            divisoria.press("ArrowRight")  # de volta perto da largura inicial
        # Abaixo de 1.024 px, a explicação desce para baixo do desenho, sem divisória nem rolagem horizontal.
        page.set_viewport_size({"width": 900, "height": 900})
        page.wait_for_timeout(400)
        expect(divisoria).to_be_hidden()
        assert lateral.bounding_box()["y"] >= quadro.bounding_box()["y"] + quadro.bounding_box()["height"] - 1, "a explicação abaixo do desenho"
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2"), "sem rolagem horizontal"
        page.set_viewport_size({"width": 1440, "height": 900})
        page.wait_for_timeout(400)
        if (tendencia.get("tendencia") or {}).get("contagens"):
            for codigo, valor in tendencia["tendencia"]["contagens"].items():
                classe = area.locator('[data-testid="analise-contagem-classe"][data-classe="' + codigo + '"]')
                if classe.count():
                    expect(classe).to_have_attribute("data-contagem", str(valor))
        # A contagem também filtra o quadro, sem pedir nada ao motor; de novo, volta tudo.
        calls = len(painel_calls)
        filtro = next(((codigo, valor) for codigo, valor in (tendencia.get("tendencia") or {}).get("contagens", {}).items() if valor), None)
        if filtro and area.locator('[data-testid="analise-contagem-classe"][data-classe="' + filtro[0] + '"]').count():
            botao = area.locator('[data-testid="analise-contagem-classe"][data-classe="' + filtro[0] + '"]')
            aperta(botao)
            expect(linhas).to_have_count(min(filtro[1], 50))
            assert set(linhas.evaluate_all("els => els.map(e => e.dataset.classe)")) == {filtro[0]}
            aperta(botao)
            expect(linhas).to_have_count(min(len(com_valor), 50))
        # Clicar numa linha escolhe a unidade (Série temporal e Comparar), e as velocidades dela aparecem na explicação, ao lado;
        # de novo, desfaz.
        primeira = linhas.first
        aperta(primeira)
        expect(primeira).to_have_attribute("aria-pressed", "true")
        expect(explicacao.get_by_test_id("analise-velocidades")).to_have_attribute("data-id", lidas[0]["id"])
        aperta(primeira)
        expect(primeira).to_have_attribute("aria-pressed", "false")
        expect(explicacao.get_by_test_id("analise-velocidades")).to_have_count(0)
        expect(explicacao).to_contain_text("Clique numa linha do quadro para ver as velocidades dela aqui.")
        page.wait_for_timeout(300)
        assert len(painel_calls) == calls, "o filtro da classe e a escolha de uma linha não pedem nada ao motor"
        # A dica no mouse: os períodos da linha com o valor de cada um.
        quadro.evaluate("e => e.scrollIntoView({block: 'start', behavior: 'instant'})")
        primeira.hover()
        dica_setas = quadro.get_by_test_id("analise-seta-dica")
        expect(dica_setas).to_be_visible()
        observacoes = (por_id[lidas[0]["id"]].get("tendencia") or {}).get("observacoes")
        expect(dica_setas.locator("li")).to_have_count(len(observacoes) if isinstance(observacoes, list) else 0)
        page.mouse.move(2, 2)
        expect(dica_setas).to_have_count(0)
        # As classes explicadas em "Entenda esta análise" (recolhido; abre e se recolhe de novo), e o motivo das unidades sem
        # classificação em palavras, pelas contagens do motor, sem os códigos internos; a dica de uma linha sem classificação diz
        # por quê.
        aperta(entenda.get_by_test_id("analise-entenda-botao"))
        expect(entenda).to_have_attribute("open", "")
        expect(area.get_by_test_id("analise-apresentacao")).to_have_attribute("data-aba", "tendencia")
        expect(area.get_by_test_id("analise-apresentacao-classes")).to_be_visible()
        expect(area.get_by_test_id("analise-apresentacao-classes")).to_contain_text("Aceleração do crescimento")
        expect(area.get_by_test_id("analise-apresentacao")).to_contain_text("A visão Trajetória mostra a variação entre o primeiro e o último período")
        aperta(entenda.get_by_test_id("analise-entenda-botao"))
        expect(entenda).not_to_have_attribute("open", "")
        topo_tendencia = tendencia.get("tendencia") or {}
        sem_classe = (topo_tendencia.get("contagens") or {}).get("SEM_CLASSIFICACAO") or 0
        nota_sem = area.get_by_test_id("analise-nota-sem-classificacao")
        if sem_classe:
            por_motivo = topo_tendencia.get("sem_classificacao_por_motivo") or {}
            if por_motivo.get("MUDANCA_DE_DIRECAO"):
                expect(nota_sem).to_contain_text(re.compile(re.escape(milhar(por_motivo["MUDANCA_DE_DIRECAO"])) +
                                                            r" (municípios mudaram|município mudou) de direção"))
            if por_motivo.get("SERIE_ESTAVEL"):
                expect(nota_sem).to_contain_text(re.compile(re.escape(milhar(por_motivo["SERIE_ESTAVEL"])) +
                                                            r" (municípios ficaram iguais|município ficou igual) em todos os períodos"))
            expect(nota_sem).not_to_contain_text(re.compile(r"MUDANCA_DE_DIRECAO|SERIE_ESTAVEL"))
            sem_direcao = next((item for item in tendencia["itens"] if item["id"] in desenhadas and
                                (item.get("tendencia") or {}).get("motivo") == "MUDANCA_DE_DIRECAO"), None)
            if sem_direcao:
                # A dica no foco (a mesma do mouse); Escape fecha. O foco sai antes da linha escolhida, que pode ser a primeira.
                linha = quadro.locator('[data-testid="analise-seta-linha"][data-id="' + sem_direcao["id"] + '"]')
                page.evaluate("document.activeElement && document.activeElement.blur()")
                linha.focus()
                expect(dica_setas).to_contain_text("o indicador subiu num período e caiu em outro (mudou de direção)")
                expect(dica_setas).not_to_contain_text("MUDANCA_DE_DIRECAO")
                linha.press("Escape")
                expect(dica_setas).to_have_count(0)
        else:
            expect(nota_sem).to_have_count(0)
        # A tabela dos Detalhes chama a coluna da classe de "Tendência".
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        expect(area.get_by_test_id("analise-tabela").locator("thead")).to_contain_text("Tendência")
        expect(area.get_by_test_id("analise-tabela").locator("thead")).not_to_contain_text("Classe de tendência")
        sem_bastidor("Análise de Tendência, visão Tendência")
        shot("07-classes")
        # Trajetória (a antiga visão Mudança): a mesma resposta (nada é pedido), as bolhas com a variação do motor e, no caminho do
        # rastro, os períodos do meio, como o motor os observou (o que não tem valor fica sem ponto). O Desfazer devolve a visão.
        calls = len(painel_calls)
        area.get_by_test_id("analise-visao-mudanca").click()
        expect(area.get_by_test_id("analise-legenda-cor")).to_have_attribute("data-camada", "variacao")
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("Trajetória da densidade de médicos")
        expect(desfazer).to_have_attribute("title", "Desfazer: trocar a visão para Trajetória")
        aperta(desfazer)
        expect(ajustes.get_by_test_id("analise-visao-classes")).to_have_attribute("aria-pressed", "true")
        expect(quadro).to_be_visible()
        area.get_by_test_id("analise-visao-mudanca").click()
        expect(area.get_by_test_id("analise-legenda-cor")).to_have_attribute("data-camada", "variacao")
        drawn(esperados(tendencia))
        desenhadas = bubbles()
        for item in tendencia["itens"]:
            valor = (item.get("variacao_percentual") or {}).get("densidade")
            if item["id"] in desenhadas:
                assert (desenhadas[item["id"]]["variacao"] is None) == (valor is None), (desenhadas[item["id"]], item)
                if valor is not None:
                    assert float(desenhadas[item["id"]]["variacao"]) == valor
                observacoes = (item.get("tendencia") or {}).get("observacoes") or []
                meio = [obs["competencia"] for obs in observacoes[1:-1] if obs.get("valor") is not None]
                com_rastro = valor is not None and (item.get("inicial") or {}).get("densidade") is not None
                assert desenhadas[item["id"]]["trajeto"] == (meio if com_rastro else []), (desenhadas[item["id"]], item)
        if any((item.get("variacao_percentual") or {}).get("densidade") not in (None, 0) for item in tendencia["itens"]):
            expect(area.get_by_test_id("analise-rastro").first).to_be_attached()
        sem_variacao = [item["id"] for item in tendencia["itens"] if item["id"] in desenhadas and
                        (item.get("variacao_percentual") or {}).get("densidade") is None]
        area.get_by_test_id("analise-vista-inicial").click()
        expect(area.get_by_test_id("analise-vista-inicial")).to_have_attribute("aria-pressed", "true")
        expect(area.locator('[data-testid="analise-bolha"][data-visivel="false"]')).to_have_count(len(sem_variacao))
        area.get_by_test_id("analise-reproduzir").click()
        expect(area.get_by_test_id("analise-vista-final")).to_have_attribute("aria-pressed", "true", timeout=10000)
        drawn(esperados(tendencia))
        page.wait_for_timeout(300)
        assert len(painel_calls) == calls, "entre a Tendência e a Trajetória, a troca de visão não pede nada ao motor"
        shot("08-trajetoria")
        # Série temporal: pede os valores de toda a série da base (lida dos dados, do primeiro ao último período), com a mesma
        # seleção (sem refazê-la), sem a tendência nem a variação; o Período dá lugar ao intervalo da série.
        serie, sent = ok(lambda: area.get_by_test_id("analise-visao-series").click(), condicao=lambda o: "serie" in o)
        todas = sent["serie"]["competencias"]
        assert len(todas) >= 4 and todas == sorted(todas) and sent["competencia"] == todas[-1], sent
        assert "tendencia" not in sent and "competencia_inicial" not in sent and sent["base"] == universo_am, sent
        assert serie["serie"]["janela"]["competencias"] == todas, serie["serie"]
        if real:
            assert todas[0] == "201401" and todas[-1] == "202406" and len(todas) == 22, todas
        else:
            assert todas == ["202301", "202306", "202401", "202406"], todas
        expect(ajustes.get_by_test_id("analise-periodo-anual")).to_have_count(0)
        intervalo = ajustes.get_by_test_id("analise-serie-intervalo")
        expect(intervalo.get_by_test_id("analise-serie-inicio")).to_have_value(todas[0])
        expect(intervalo.get_by_test_id("analise-serie-fim")).to_have_value(todas[-1])
        expect(intervalo.get_by_test_id("analise-serie-toda")).to_be_disabled()
        expect(intervalo.get_by_test_id("analise-serie-texto")).to_have_text(
            "Toda a série da base: " + mm_aaaa(todas[0]) + " a " + mm_aaaa(todas[-1]) + " (" + str(len(todas)) + " competências).")
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("Série temporal da densidade de médicos")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        # Na Série temporal, a escala e a régua não se aplicam, e o mapa fica desligado, com o motivo no title (só do gráfico).
        expect(area.get_by_test_id("analise-escala")).to_have_count(0)
        expect(area.get_by_test_id("analise-funcao-regua")).to_be_disabled()
        expect(area.get_by_test_id("analise-desenho-mapa")).to_have_attribute("aria-disabled", "true")
        expect(area.get_by_test_id("analise-desenho-mapa")).to_have_attribute("title", re.compile("Na visão Série temporal"))
        expect(area).to_have_attribute("data-desenho", "grafico")
        expect(explicacao.get_by_test_id("analise-serie-legenda")).to_contain_text("Não há classificação nem linha ajustada")
        series = area.get_by_test_id("analise-series")
        com_serie = [item for item in serie["itens"] if item.get("serie")]
        if len(com_serie) > 12:
            expect(area.get_by_test_id("analise-series-vazio")).to_be_visible()
        else:
            expect(series.get_by_test_id("analise-serie")).to_have_count(len(com_serie))
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        tabela = area.get_by_test_id("analise-tabela")
        for chave in (MANAUS, TEFE):
            marca(tabela.locator('[data-testid="analise-linha"][data-id="' + chave + '"] input[type=checkbox]'))
        expect(series.get_by_test_id("analise-serie")).to_have_count(2)
        por_id_serie = {item["id"]: item for item in serie["itens"]}
        for chave in (MANAUS, TEFE):
            linha_serie = series.locator('[data-testid="analise-serie"][data-id="' + chave + '"]')
            observadas = [obs for obs in por_id_serie[chave]["serie"]["observacoes"] if obs.get("valor") is not None]
            expect(linha_serie).to_have_attribute("data-pontos", str(len(observadas)))
            expect(linha_serie).to_have_attribute("data-comparavel", "true")
            pontos = linha_serie.get_by_test_id("analise-serie-ponto").evaluate_all(
                "els => els.map(e => [e.dataset.competencia, Number(e.dataset.valor)])")
            assert pontos == [[obs["competencia"], obs["valor"]] for obs in observadas], (chave, pontos)
        # O intervalo escolhido pede só as competências dele; "Toda a série" volta à extensão inteira (da memória da tela).
        inicio_escolhido = todas[len(todas) // 2]
        parte, sent = ok(lambda: intervalo.get_by_test_id("analise-serie-inicio").select_option(inicio_escolhido))
        assert sent["serie"]["competencias"] == todas[len(todas) // 2:] and sent["base"] == universo_am, sent
        expect(intervalo.get_by_test_id("analise-serie-texto")).to_have_text(
            "Intervalo escolhido: " + mm_aaaa(inicio_escolhido) + " a " + mm_aaaa(todas[-1]) + " (" +
            str(len(todas) - len(todas) // 2) + " competências).")
        expect(intervalo.get_by_test_id("analise-serie-toda")).to_be_enabled()
        expect(series).to_have_attribute("data-competencias", str(len(todas) - len(todas) // 2))
        aperta(area.get_by_test_id("analise-detalhes-metodo"))
        expect(area.get_by_test_id("analise-metodo-serie")).to_contain_text(
            "Série temporal: " + mm_aaaa(inicio_escolhido) + " a " + mm_aaaa(todas[-1]) + " (" + str(len(todas) - len(todas) // 2) +
            " competências)")
        aperta(intervalo.get_by_test_id("analise-serie-toda"))
        expect(intervalo.get_by_test_id("analise-serie-texto")).to_contain_text("Toda a série da base")
        expect(series).to_have_attribute("data-competencias", str(len(todas)))
        sem_bastidor("Análise de Tendência, visão Série temporal")
        shot("09-serie-temporal")
        area.get_by_test_id("analise-visao-classes").click()
        expect(quadro).to_be_visible()

        # 11. Rotatividade com a base do Brasil: a aba abre para a apresentação, com o motivo de não se executar e "Enviar meus
        # dados"; o desenho continua com a tendência, e nada é pedido ao motor.
        calls = len(painel_calls)
        aperta(area.get_by_test_id("analise-familia-rotatividade"))
        expect(area).to_have_attribute("data-aba", "rotatividade")
        expect(area.get_by_test_id("analise-apresentacao")).to_contain_text("Os dados do Brasil têm contagens de profissionais")
        expect(area.get_by_test_id("analise-familia-motivo")).to_be_visible()
        expect(area.get_by_test_id("analise-familia-motivo")).to_contain_text("O desenho abaixo continua com a Análise de Tendência.")
        expect(area.get_by_test_id("analise-enviar-dados")).to_be_visible()
        expect(area.get_by_test_id("analise-ajustes")).to_have_count(0)
        expect(area).to_have_attribute("data-familia", "tendencia")
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "a análise que não se executa com estes dados não pede nada ao motor"

        # 12. Funções na distribuição: Condições, Ordenar, Comparar e Juntar, com os números do motor.
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        drawn(ids_am)
        densidades = sorted(item["densidade"] for item in am["itens"] if item["densidade"] is not None)
        limiar = round(densidades[len(densidades) // 2], 2)
        condicoes = abre("condicoes").get_by_test_id("analise-condicoes")
        condicoes.get_by_test_id("analise-condicao-atributo").select_option("densidade")
        condicoes.get_by_test_id("analise-condicao-operador").select_option("<")
        condicoes.get_by_test_id("analise-condicao-valor").fill(str(limiar).replace(".", ","))
        resultado, sent = ok(lambda: aperta(condicoes.get_by_test_id("analise-condicoes-aplicar")))
        assert sent["condicoes"] == [{"atributo": "densidade", "operador": "<", "valor": limiar}], sent
        # Com as Condições aplicadas, o convite ao mapa: achar onde ficam os que atendem.
        expect(area.get_by_test_id("analise-convite-mapa")).to_have_text("Ver onde ficam no mapa")
        for situacao, valor in (resultado.get("condicoes") or {}).get("contagens", {}).items():
            expect(condicoes.locator('[data-testid="analise-condicoes-contagem"][data-situacao="' + situacao + '"]')).to_have_attribute("data-contagem", str(valor))
        desenhadas = bubbles()
        atendem = []
        for item in resultado["itens"]:
            if item["id"] in desenhadas and item.get("condicoes"):
                assert desenhadas[item["id"]]["condicao"] == item["condicoes"]["situacao"], (desenhadas[item["id"]], item)
                if item["condicoes"]["situacao"] == "ATENDE":
                    atendem.append(item["id"])
        calls = len(painel_calls)
        marca(condicoes.get_by_test_id("analise-condicoes-so-atende"))
        drawn(atendem)
        assert len(painel_calls) == calls, "mostrar só quem atende é filtro visual"
        aperta(condicoes.get_by_test_id("analise-condicoes-limpar"))
        drawn(ids_am)
        fecha()

        ordenar = abre("ordenar").get_by_test_id("analise-ordenar")
        ordenar.get_by_test_id("analise-ordenar-atributo").select_option("densidade")
        ordenar.get_by_test_id("analise-ordenar-ordem").select_option("desc")
        ordenar.get_by_test_id("analise-ordenar-primeiros").fill("2")
        ordem, sent = ok(lambda: aperta(ordenar.get_by_test_id("analise-ordenar-aplicar")))
        assert sent["ordenar"] == {"atributo": "densidade", "ordem": "desc", "primeiros": 2}, sent
        posicionados = [item for item in ordem["itens"] if (item.get("ordem") or {}).get("posicao") is not None]
        no_corte = [item for item in posicionados if item["ordem"]["posicao"] <= 2]
        # A lista do painel aparece com a resposta desenhada; só então as bolhas são lidas.
        expect(ordenar.get_by_test_id("analise-ordenar-lista").locator("li")).to_have_count(len(no_corte))
        desenhadas = bubbles()
        for item in posicionados:
            if item["id"] in desenhadas:
                assert desenhadas[item["id"]]["posicao"] == str(item["ordem"]["posicao"]), (desenhadas[item["id"]], item)
        aperta(ordenar.get_by_test_id("analise-ordenar-limpar"))
        drawn(ids_am)
        fecha()
        # Limpar filtros (o ícone do filtro riscado, 24/10/2026): tira a ordenação e os itens marcados, sem mexer nos territórios
        # nem nos ajustes. O Desfazer do alto devolve os filtros (no lugar do "Desfazer a limpeza" ao lado do botão, que saiu com o
        # Desfazer sequencial).
        ordem, sent = ok(lambda: aperta(abre("ordenar").get_by_test_id("analise-ordenar-aplicar")))
        fecha()
        limpar_filtros = area.get_by_test_id("analise-limpar-filtros")
        expect(limpar_filtros).to_be_visible()
        expect(limpar_filtros).to_have_text("Limpar filtros")
        expect(area.get_by_test_id("analise-desfazer-filtros")).to_have_count(0)
        resumo_antes = area.get_by_test_id("analise-aba-territorios-resumo").inner_text()
        aperta(limpar_filtros)
        expect(limpar_filtros).to_have_count(0)
        drawn(ids_am)
        expect(area.locator(BOLHAS + '[data-posicao="1"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(resumo_antes)
        expect(desfazer).to_have_attribute("title", "Desfazer: limpar filtros")
        aperta(desfazer)
        expect(area.locator(BOLHAS + '[data-posicao="1"]')).to_have_count(1)
        aperta(area.get_by_test_id("analise-limpar-filtros"))
        expect(area.locator(BOLHAS + '[data-posicao="1"]')).to_have_count(0)
        # O Desfazer é sequencial: Limpar seleção e Desfazer devolvem os territórios sem os filtros (limpos antes); o passo seguinte do
        # Desfazer devolve os filtros, com a mesma escolha de territórios que valia com eles (a comparação antiga nunca vai ao motor
        # fora do gráfico, o defeito que a revisão de 24/10/2026 achou).
        aperta(limpar)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        expect(area.get_by_test_id("analise-vazio")).to_be_visible()
        aperta(desfazer)
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(resumo_antes)
        drawn(ids_am)
        expect(area.locator(BOLHAS + '[data-posicao="1"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-limpar-filtros")).to_have_count(0)
        aperta(desfazer)
        expect(area.locator(BOLHAS + '[data-posicao="1"]')).to_have_count(1)
        aperta(area.get_by_test_id("analise-limpar-filtros"))
        expect(area.locator(BOLHAS + '[data-posicao="1"]')).to_have_count(0)

        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start'})")
        for chave in (MANAUS, TEFE):
            bolha = area.locator('[data-testid="analise-bolha"][data-id="' + chave + '"]')
            if bolha.get_attribute("data-selecionado") != "true":
                bolha.focus()
                bolha.press("Enter")
            expect(bolha).to_have_attribute("data-selecionado", "true")
        # Marcar não esmaece as demais (25/10/2026): as marcadas ganham o anel e o nome, e nenhuma bolha à vista perde a cor.
        opacidades = area.locator(BOLHAS).evaluate_all("els => els.map(e => [e.dataset.selecionado === 'true', e.style.opacity])")
        assert sum(marcada for marcada, _ in opacidades) == 2 and len(opacidades) > 2, opacidades
        assert all(opacidade == "1" for _, opacidade in opacidades), ("marcar não esmaece as outras bolhas", opacidades)
        # Comparar (24/10/2026): o título do painel, a orientação objetiva e os escolhidos, sem os cartões com os valores (os
        # valores estão no gráfico, na dica e na tabela); o resultado da comparação continua.
        comparar = abre("comparar").get_by_test_id("analise-comparar")
        expect(area.get_by_test_id("analise-painel").locator("#analise-painel-titulo")).to_have_text("Comparar")
        expect(comparar.get_by_test_id("analise-comparar-orientacao")).to_contain_text("Escolha dois ou três itens")
        expect(comparar.get_by_test_id("analise-comparar-item")).to_have_count(2)
        expect(comparar.locator("article, dl")).to_have_count(0)
        comparado, sent = ok(lambda: aperta(comparar.get_by_test_id("analise-comparar-calcular")))
        assert sorted(sent["comparar"]) == sorted([MANAUS, TEFE]), sent
        if comparado.get("comparacao"):
            expect(comparar.get_by_test_id("analise-comparacao")).to_be_visible()
            expect(comparar.get_by_test_id("analise-comparacao-linha").first).to_be_visible()
        fecha()
        # Juntar: a mesma forma, com os escolhidos em etiquetas, cada uma com o ×.
        juntar = abre("juntar").get_by_test_id("analise-juntar")
        expect(area.get_by_test_id("analise-painel").locator("#analise-painel-titulo")).to_have_text("Juntar")
        expect(juntar.get_by_test_id("analise-juntar-orientacao")).to_contain_text("Escolha dois ou mais municípios")
        expect(juntar.get_by_test_id("analise-juntar-item")).to_have_count(2)
        expect(juntar.locator("article, dl")).to_have_count(0)
        juntar.get_by_test_id("analise-juntar-nome").fill("Capital e Tefé")
        junto, sent = ok(lambda: aperta(juntar.get_by_test_id("analise-juntar-criar")))
        assert sent["conjuntos"] == [{"id": "c1", "rotulo": "Capital e Tefé", "membros": [MANAUS, TEFE]}], sent
        conjunto = next(item for item in junto["itens"] if item["id"] == "c1")
        assert conjunto["tipo"] == "conjunto" and conjunto["contagem"] == "SOMA_DOS_COMPONENTES"
        drawn(esperados(junto))
        expect(area.locator('[data-testid="analise-bolha"][data-id="c1"]')).to_have_attribute("data-tipo", "conjunto")
        expect(area.get_by_test_id("analise-simbolos")).to_contain_text("possível dupla contagem")
        fecha()
        # O conjunto aparece na lista da direita da Seleção, com o × que o desfaz.
        aba_selecao()
        expect(territorios.locator('[data-testid="analise-selecionado-conjunto"][data-id="c1"]')).to_contain_text("Capital e Tefé")
        aba_analise("distribuicao")
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        expect(area.locator('[data-testid="analise-linha"][data-id="c1"]')).to_contain_text("soma das contagens dos componentes")
        aperta(area.get_by_test_id("analise-detalhes-metodo"))
        expect(area.locator('[data-limitacao="SOMA_COM_POSSIVEL_DUPLA_CONTAGEM"]')).to_contain_text("possível dupla contagem")
        shot("10-funcoes")

        # 13. Exportar: CSV com todos os itens, em precisão integral, com a avaliabilidade e o motivo; Detalhes com a tabela e os
        # não avaliáveis. Lá embaixo, nos Detalhes, Desfazer e Limpar seleção continuam no alto da tela, sem rolar de volta.
        exportar = abre("exportar").get_by_test_id("analise-exportar")
        with page.expect_download() as baixado:
            aperta(exportar.get_by_test_id("analise-exportar-csv"))
        texto = Path(baixado.value.path()).read_text(encoding="utf-8-sig")
        linhas = list(csv.DictReader(io.StringIO(texto), delimiter=";"))
        assert len(linhas) == len(junto["itens"]), (len(linhas), len(junto["itens"]))
        por_id = {linha["Identificador"]: linha for linha in linhas}
        for item in junto["itens"]:
            linha = por_id[item["id"]]
            valor = item.get("densidade")
            assert (linha["Densidade por 1.000 habitantes"] == "") if valor is None else float(linha["Densidade por 1.000 habitantes"]) == valor, (linha, item)
            assert linha["Avaliável"] in ("sim", "não") and "Motivos" in linha
        fecha()
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        expect(area.get_by_test_id("analise-tabela").get_by_test_id("analise-linha")).to_have_count(len(esperados(junto)))
        aperta(area.get_by_test_id("analise-detalhes-nao-avaliaveis"))
        expect(area.get_by_test_id("analise-nao-avaliaveis")).to_be_visible()
        area.get_by_test_id("analise-detalhes").evaluate("e => e.scrollIntoView({block: 'end', behavior: 'instant'})")
        page.wait_for_timeout(300)
        assert area.get_by_test_id("analise-titulo").bounding_box()["y"] < 0, "a página rolou até os Detalhes"
        caixa_controles = controles.bounding_box()
        assert -2 <= caixa_controles["y"] <= 6, ("Desfazer e Limpar seleção fixos no alto ao rolar", caixa_controles)
        expect(desfazer).to_be_visible()
        expect(limpar).to_be_visible()
        expect(desfazer).to_be_in_viewport()
        expect(limpar).to_be_in_viewport()
        page.evaluate("window.scrollTo({top: 0, behavior: 'instant'})")

        # 14. Base versionada: todos os municípios do Brasil no modo leve, sem escala logarítmica automática; tabela em páginas;
        # régua que só esconde; dica no mouse.
        if real:
            aba_selecao()
            if territorios.get_by_test_id("analise-grupo-voltar").count():
                aperta(territorios.get_by_test_id("analise-grupo-voltar"))
            marcar_brasil = territorios.get_by_test_id("analise-marcar-todos")
            expect(marcar_brasil).to_have_text("Marcar todos os municípios do Brasil (5.570)")
            brasil, sent = ok(lambda: aperta(marcar_brasil))
            assert sent["base"] == {"municipios": {"todos": True, "estados": [], "ids": []}}, sent
            # A seleção de todos os municípios se desfaz de uma vez (Limpar seleção e Desfazer), sem desmarcar um a um.
            expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text("Todos os municípios (5.570)")
            aperta(limpar)
            expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text("Nenhum município marcado")
            aperta(desfazer)
            expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text("Todos os municípios (5.570)")
            aba_analise("distribuicao")
            plotaveis = [item for item in brasil["itens"] if item["densidade"] is not None]
            assert len(brasil["itens"]) > 5000, len(brasil["itens"])
            chart = area.get_by_test_id("analise-grafico")
            expect(chart).to_have_attribute("data-modo", "leve", timeout=30000)
            expect(chart).to_have_attribute("data-desenhadas", str(len(plotaveis)), timeout=30000)
            expect(eixo_y).to_have_attribute("data-escala", "linear")
            expect(area.get_by_test_id("analise-arranjo-nota")).to_contain_text("faixa limitada")
            expect(area.get_by_test_id("analise-selecao-resumo")).to_contain_text("Todos os municípios (5.570)")
            # Os Detalhes ficaram em "Não avaliáveis" no passo 13: a tabela volta à vista para as páginas.
            aperta(area.get_by_test_id("analise-detalhes-tabela"))
            paginas = area.get_by_test_id("analise-paginas")
            expect(area.get_by_test_id("analise-tabela").get_by_test_id("analise-linha")).to_have_count(100)
            expect(paginas).to_contain_text("Linhas 1 a 100 de " + f"{len(plotaveis):,}".replace(",", "."))
            aperta(paginas.get_by_test_id("analise-pagina-proxima"))
            expect(paginas).to_contain_text("Linhas 101 a 200")
            calls = len(painel_calls)
            regua = abre("regua").get_by_test_id("analise-regua")
            cursor = regua.get_by_test_id("analise-regua-min")
            cursor.focus()
            for _ in range(3):
                cursor.press("PageUp")
            expect(chart).not_to_have_attribute("data-desenhadas", str(len(plotaveis)), timeout=10000)
            assert len(painel_calls) == calls, "a régua só esconde: nada é recalculado"
            aperta(regua.get_by_test_id("analise-regua-limpar"))
            expect(chart).to_have_attribute("data-desenhadas", str(len(plotaveis)), timeout=10000)
            fecha()
            # A página rola suave (scroll-behavior: smooth): a rolagem instantânea garante que a posição lida abaixo seja a da
            # bolha já parada, e não a do meio da rolagem.
            chart.evaluate("e => e.scrollIntoView({block: 'start', behavior: 'instant'})")
            alvo = area.locator('[data-testid="analise-camada-leve"] [data-testid="analise-bolha"][data-visivel="true"]').nth(len(plotaveis) // 2)
            caixa = alvo.bounding_box()
            page.mouse.move(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
            expect(area.get_by_test_id("analise-dica")).to_be_visible(timeout=5000)
            page.mouse.move(2, 2)
            shot("11-brasil-leve")

        # 15. O Brasil como unidade (24/10/2026): o país inteiro, com o total nacional, e não a seleção de todos os municípios; só o
        # nível vai ao motor, e as funções que valem para vários territórios ficam desligadas, com o motivo. Depois, os estados
        # escolhidos um a um: o pedido leva só eles.
        aba_selecao()
        brasil_unidade, sent = ok(lambda: aperta(territorios.get_by_test_id("analise-nivel-brasil")))
        assert set(sent) == {"competencia", "categoria", "nivel", "indicador"} and sent["nivel"] == "brasil", sent
        [item_brasil] = brasil_unidade["itens"]
        assert item_brasil["id"] == "br" and item_brasil["tipo"] == "brasil", item_brasil
        expect(territorios.get_by_test_id("analise-territorios-brasil")).to_contain_text("Não é a soma dos estados nem a seleção de todos")
        expect(territorios.get_by_test_id("analise-busca")).to_have_count(0)
        expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text("Brasil (total nacional)")
        # Limpar seleção no nível Brasil (decisão 5, 25/10/2026): o país é a própria unidade, e o botão fica desligado, com o motivo.
        expect(limpar).to_be_disabled()
        expect(limpar).to_have_attribute("title", "No nível Brasil, o país inteiro é a unidade em análise: não há seleção para limpar.")
        aperta(territorios.get_by_test_id("analise-ver-analise"))
        drawn(["br"])
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("no Brasil")
        expect(area.get_by_test_id("analise-resumo")).to_contain_text("Brasil, em ")
        expect(area.get_by_test_id("analise-resumo")).not_to_contain_text("vai de")
        for funcao in ("regua", "condicoes", "ordenar", "comparar", "juntar"):
            expect(area.get_by_test_id("analise-funcao-" + funcao)).to_be_disabled()
        expect(area.get_by_test_id("analise-funcao-exportar")).to_be_enabled()
        expect(area.get_by_test_id("analise-agrupar")).to_have_count(0)
        expect(area.get_by_test_id("analise-desenho-mapa")).to_have_attribute("aria-disabled", "true")
        aba_selecao()
        aperta(territorios.get_by_test_id("analise-nivel-estados"))
        if territorios.get_by_test_id("analise-desmarcar-todos").is_enabled():
            aperta(territorios.get_by_test_id("analise-desmarcar-todos"))
        expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text("Nenhum estado marcado")
        _, sent = ok(lambda: marca(territorios.locator('[data-testid="analise-estado"][data-id="' + AM + '"] input')))
        assert sent.get("nivel") == "estados" and sent.get("estados") == [AM], sent
        expect(territorios.get_by_test_id("analise-selecionados-resumo")).to_have_text("Amazonas")
        expect(desfazer).to_have_attribute("title", "Desfazer: marcar Amazonas")
        aba_analise("distribuicao")
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("no Amazonas")
        aba_selecao()
        aperta(territorios.get_by_test_id("analise-nivel-municipios"))
        drawn(esperados(brasil) if real else esperados(junto))  # a escolha dos municípios (e o conjunto) continua guardada
        shot("13-niveis")

        # 16. Celular (390 px): sem rolagem horizontal; as famílias em abas roláveis; as funções num botão "Ferramentas"; o painel
        # sobe da base da tela; Desfazer e Limpar seleção à vista, dentro da largura; na Seleção, as duas áreas uma sobre a outra (o
        # que entra na análise primeiro).
        aba_analise("distribuicao")
        page.set_viewport_size({"width": 390, "height": 844})
        page.wait_for_timeout(500)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        familias = area.get_by_role("tablist", name="Seleção de territórios e análises")
        assert familias.evaluate("e => getComputedStyle(e).overflowX") in ("auto", "scroll")
        # O painel dos ajustes ocupa a largura, logo abaixo das abas; a escolha da vista continua à vista, fora das Ferramentas.
        caixa_ajustes = area.get_by_test_id("analise-ajustes").bounding_box()
        assert caixa_ajustes and caixa_ajustes["width"] >= 390 - 80, caixa_ajustes
        expect(area.get_by_test_id("analise-desenho")).to_be_visible()
        for botao in (desfazer, limpar):
            expect(botao).to_be_visible()
            caixa_botao = botao.bounding_box()
            assert caixa_botao["x"] >= 0 and caixa_botao["x"] + caixa_botao["width"] <= 390, caixa_botao
        ferramentas = area.get_by_test_id("analise-ferramentas")
        expect(ferramentas).to_be_visible()
        expect(area.get_by_test_id("analise-funcao-regua")).to_be_hidden()
        aperta(ferramentas)
        expect(ferramentas).to_have_attribute("aria-expanded", "true")
        expect(area.get_by_test_id("analise-funcao-regua")).to_be_visible()
        aperta(area.get_by_test_id("analise-funcao-exportar"))
        painel = area.get_by_test_id("analise-painel")
        expect(painel).to_be_visible()
        assert painel.evaluate("e => getComputedStyle(e).position") == "fixed"
        caixa = painel.bounding_box()
        assert caixa["y"] + caixa["height"] >= 844 - 16, caixa
        page.screenshot(path=str(OUTPUT / ("area-12-celular" + suffix + ".png")), full_page=False)
        aperta(painel.get_by_test_id("analise-painel-fechar"))
        expect(area.get_by_test_id("analise-painel")).to_have_count(0)
        aba_selecao()
        caixa_d, caixa_e, caixa_t = direita.bounding_box(), lista_esquerda.bounding_box(), territorios.bounding_box()
        assert caixa_d["y"] + caixa_d["height"] <= caixa_e["y"] + 1, ("no celular, o que entra na análise acima da lista", caixa_d, caixa_e)
        assert abs(caixa_d["x"] - caixa_e["x"]) < 2 and abs(caixa_d["width"] - caixa_e["width"]) < 2 and \
            caixa_d["width"] >= 0.85 * caixa_t["width"], ("uma coluna só, com a largura do painel", caixa_d, caixa_e, caixa_t)
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 2")
        page.set_viewport_size({"width": 1440, "height": 900})

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    for nota in notas:
        print("Nota: " + nota)
    print("ÁREA DE ANÁLISE PASS: abertura com o nome da plataforma, sem abas, base sem seleção automática, Desfazer sequencial e Limpar "
          "seleção no alto (fixos ao rolar), Seleção por níveis em duas áreas com o × de cada território, seleção cumulativa entre "
          "estados, Voltar aos estados em destaque, abas só com os nomes, Entenda esta análise, eixo do indicador, quintis do mapa no "
          "pedido, régua, grupos, análise espacial (o Território de referência por elegibilidade quando o motor a oferece, ou o "
          "motivo: veja as notas), tendência com o Período anual e o Gráfico ao abrir, a explicação ao lado com a "
          "divisória, as visões Tendência, Trajetória e Série temporal, rotatividade com o motivo, funções (Comparar e Juntar sem "
          "cartões), exportação, nenhum \"motor\" nos textos e celular" +
          (" (base versionada)." if real else " (catálogo sintético)."))


if __name__ == "__main__":
    main()
