"""Área de análise da página única (22/10/2026): abertura antes dos dados (E0), a base do Brasil sem seleção automática e os
estados em bolhas escolhidos na Seleção de Territórios (E1), a escolha de territórios em lista (ver os municípios de um estado,
marcar e desmarcar, marcar e desmarcar todos, voltar aos estados pela trilha), o eixo vertical do indicador com o arranjo
horizontal, a dica no mouse e no foco, Quantidade (com os quintis do mapa no pedido, a troca pede ao motor; a volta vem da
memória da tela), a régua que só esconde, grupos por posição, a análise espacial com a referência por critério, a tendência
(Classes, Mudança e Séries, com a janela escolhida pela pessoa, as classes explicadas e o motivo das sem classificação), a
rotatividade com o motivo, Condições, Ordenar, Comparar, Juntar, Exportar (CSV em precisão integral), os Detalhes e o celular
(abas roláveis e o botão Ferramentas).

Desde 23/10/2026 (pedido integrado): uma linha de abas com a Seleção de Territórios primeiro e as quatro análises com os nomes
padronizados (Análise de Distribuição, Análise Espacial, Análise de Tendência e Análise de Rotatividade); cada aba abre, mesmo
sem poder ser executada, com a apresentação do que faz (`analise-apresentacao`); a lista de territórios fica no painel da
Seleção (`analise-aba-painel`), e os ajustes de cada análise, no painel da aba dela, com o resumo da seleção e "Alterar a
seleção".

Desde 23/10/2026: os ajustes dentro de cada análise (`analise-ajustes`, o painel colado na aba escolhida, com só o que vale para
ela e o mesmo indicador em todas), a escala na barra junto do desenho (fora dos ajustes, e só quando se aplica), a escolha da vista
do desenho (`analise-desenho`: o gráfico é a inicial; nos estados, o mapa desligado, com o motivo e o atalho), o convite ao mapa
depois das Condições e na análise espacial e a frase-resumo do motor (`analise-resumo`), com a competência da resposta. O mapa
em si (pontos, pintura, transição, lado a lado) é conferido no roteiro do mapa.

Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; quatro competências; fonte estadual sintética) ou, com
ADT_BLOCK1_REAL=1, a base versionada (somente leitura), que acrescenta o modo leve com todos os municípios do Brasil. O roteiro
assume que a estrutura da página abre a área de análise (`area-de-analise`) depois do aceite de privacidade e usa os botões de
fonte da própria área em E0. Cada bolha desenhada é conferida com a resposta de /api/painel: todo número vem do motor. A
disponibilidade da análise espacial também vem do motor: no catálogo sintético, instalado como versão externa, o referencial
(SIRGAS 2000 ou WGS 84) pode não ser premissa, e o roteiro segue o que o motor disser (a aba desabilitada com o motivo; a recusa,
com as opções da pendência que o motor mandar, e a volta ao último gráfico calculado; ou o eixo da distância). Servidor
serve_ui_offline.py; nunca chama o provedor de IA.
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


def formas_da_competencia(competencia):
    """A competência AAAAMM como a frase-resumo do motor pode escrevê-la: por extenso, mm/aaaa, mês abreviado ou como veio."""
    formas = [competencia]
    if re.fullmatch(r"\d{6}", competencia) and 1 <= int(competencia[4:]) <= 12:
        mes, ano = MESES[int(competencia[4:]) - 1], competencia[:4]
        formas += [mes + " de " + ano, competencia[4:] + "/" + ano, mes[:3] + "/" + ano]
    return formas


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


def main():
    real = os.getenv("ADT_BLOCK1_REAL") == "1"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = "-real" if real else ""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        failures, llm_calls, painel_calls, pedidos = [], [], [], []
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

        def shot(name):
            page.wait_for_timeout(700)  # transições do gráfico
            page.screenshot(path=str(OUTPUT / ("area-" + name + suffix + ".png")), full_page=True)

        def respond(action, timeout=180000):
            """Executa a ação e devolve a resposta de /api/painel e as opções do mesmo pedido. Só vale um pedido feito depois do
            início da ação: a resposta de um pedido anterior ainda em curso (o "Limpar" das Condições pede ao motor sem que o
            roteiro espere) pode chegar depois e não é a desta ação. A tela só pede 150 ms depois da mudança (e só quando a
            resposta não está na memória dela, que guarda as seis últimas); por isso, antes da ação, o cálculo que a ação anterior
            tenha disparado termina ("Atualizando o gráfico no motor…" sai), para esse pedido não sair já dentro desta ação."""
            page.wait_for_timeout(200)
            expect(area.get_by_test_id("analise-atualizando")).to_have_count(0, timeout=timeout)
            antes = len(pedidos)
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST"
                                      and any(r.request is pedido for pedido in pedidos[antes:]), timeout=timeout) as event:
                action()
            response = event.value
            return response, options_of(response.request)

        def ok(action, timeout=180000):
            response, sent = respond(action, timeout)
            assert response.status == 200, response.text()[:2000]
            return response.json(), sent

        def drawn(ids, timeout=30000):
            page.wait_for_function("ids => JSON.stringify([...document.querySelectorAll('[data-testid=analise-bolha][data-visivel=true]')]"
                                   ".map(e => e.dataset.id).sort()) === JSON.stringify(ids)", arg=sorted(ids), timeout=timeout)

        def bubbles():
            return {item["id"]: item for item in area.locator(BOLHAS).evaluate_all(
                "els => els.map(e => ({id: e.dataset.id, tipo: e.dataset.tipo, valor: e.dataset.valor, populacao: e.dataset.populacao, "
                "distancia: e.dataset.distancia ?? null, variacao: e.dataset.variacao ?? null, classe: e.dataset.classe ?? null, "
                "grupo: e.dataset.grupo ?? null, condicao: e.dataset.condicao ?? null, posicao: e.dataset.posicao ?? null}))")}

        def aperta(locator):
            """Botões e caixas pelo teclado: além de conferir o acesso sem mouse, evita a caixa da conversa por cima."""
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

        def confere_valores(body, indicador="densidade"):
            desenhadas = bubbles()
            for item in body["itens"]:
                if item["id"] in desenhadas:
                    bolha = desenhadas[item["id"]]
                    assert float(bolha["valor"]) == item[indicador] and bolha["tipo"] == item["tipo"], (bolha, item)
                    assert bolha["populacao"] == "" if item.get("populacao") is None else float(bolha["populacao"]) == item["populacao"], (bolha, item)
                elif item.get(indicador) is None:
                    expect(area.locator('[data-testid="analise-nao-avaliavel"][data-id="' + item["id"] + '"]')).to_have_count(1)

        # 1. E0: antes dos dados, a moldura limpa, sem números nem bolhas; a família escolhida vira intenção.
        expect(area).to_be_visible(timeout=60000)
        expect(area).to_have_attribute("data-estado", "E0")
        expect(area.get_by_test_id("analise-abertura")).to_contain_text("Escolha os dados para começar")
        expect(area.get_by_test_id("analise-titulo")).to_have_text("Diagnóstico territorial da força de trabalho em saúde")
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-detalhes")).to_have_count(0)
        # Uma linha de abas: a Seleção de Territórios primeiro e as quatro análises com os nomes padronizados.
        linha_de_abas = area.get_by_role("tablist", name="Seleção de territórios e análises")
        ordem = linha_de_abas.get_by_role("tab").evaluate_all("els => els.map(e => e.dataset.testid)")
        assert ordem == ["analise-aba-territorios", "analise-familia-distribuicao", "analise-familia-espacial",
                         "analise-familia-tendencia", "analise-familia-rotatividade"], ordem
        for testid, nome in (("analise-aba-territorios", "Seleção de Territórios"), ("analise-familia-distribuicao", "Análise de Distribuição"),
                             ("analise-familia-espacial", "Análise Espacial"), ("analise-familia-tendencia", "Análise de Tendência"),
                             ("analise-familia-rotatividade", "Análise de Rotatividade")):
            expect(area.get_by_test_id(testid)).to_contain_text(nome)
        # Na mesma linha: uma linha horizontal atravessa as cinco abas (as alturas podem variar com o texto de apoio), da
        # esquerda para a direita, na ordem acima.
        caixas = [area.get_by_test_id(testid).bounding_box() for testid in ordem]
        assert max(caixa["y"] for caixa in caixas) < min(caixa["y"] + caixa["height"] for caixa in caixas), ("as cinco abas na mesma linha", caixas)
        assert [caixa["x"] for caixa in caixas] == sorted(caixa["x"] for caixa in caixas), ("da esquerda para a direita", caixas)
        apresentacao = area.get_by_test_id("analise-apresentacao")
        expect(area).to_have_attribute("data-aba", "territorios")
        expect(apresentacao).to_contain_text("Selecione os territórios que deseja incluir em suas análises.")
        expect(apresentacao).to_contain_text("Depois de escolher os dados, a lista de territórios aparece aqui.")
        area.get_by_test_id("analise-familia-tendencia").click()
        expect(area.get_by_test_id("analise-intencao")).to_contain_text("Você escolheu Análise de Tendência. Agora escolha os dados.")
        # Toda aba abre com a apresentação do que ela faz, mesmo antes dos dados; a da tendência explica cada classe.
        expect(apresentacao).to_have_attribute("data-aba", "tendencia")
        termos = apresentacao.get_by_test_id("analise-apresentacao-classes").locator("dt").all_inner_texts()
        assert termos == ["Crescimento", "Aceleração do crescimento", "Desaceleração do crescimento", "Declínio",
                          "Aceleração do declínio", "Desaceleração do declínio", "Sem classificação", "Não avaliável"], termos
        expect(apresentacao).to_contain_text("Basta um trecho na direção contrária")
        expect(apresentacao).not_to_contain_text(re.compile(r"MUDANCA_DE_DIRECAO|SERIE_ESTAVEL|SEM_CLASSIFICACAO"))
        area.get_by_test_id("analise-familia-distribuicao").click()
        expect(area.get_by_test_id("analise-intencao")).to_contain_text("Análise de Distribuição")
        expect(apresentacao).to_have_attribute("data-aba", "distribuicao")
        assert not painel_calls, "antes dos dados, nada é pedido ao motor"
        # A caixa da conversa (estrutura da página), se estiver aberta, fica minimizada enquanto o roteiro usa o gráfico.
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 2. E1: Dados do Brasil pela própria área, sem seleção automática: nada é pedido ao motor; a área avisa que os dados
        # estão prontos e abre a Seleção de Territórios, com a lista à vista, sem digitar. Depois, os estados em bolhas, sem
        # municípios; a instrução de clicar num estado; o eixo vertical do indicador; a linha de contexto do Brasil.
        area.get_by_test_id("analise-fonte-brasil").click()
        vazio = area.get_by_test_id("analise-vazio")
        expect(vazio).to_contain_text("Os dados do Brasil foram carregados e estão prontos para a análise.", timeout=120000)
        expect(vazio).to_contain_text("Selecione os territórios que deseja analisar.")
        expect(area).to_have_attribute("data-estado", "E1")
        expect(area).to_have_attribute("data-aba", "territorios")
        expect(territorios).to_be_visible()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado")
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-resumo")).to_have_text("")  # a região da frase fica, vazia
        page.wait_for_timeout(800)
        assert not painel_calls, "sem territórios escolhidos, nada é pedido ao motor"
        # A aba de uma análise sem territórios: a apresentação, os ajustes e o convite a selecionar; a referência e a janela só
        # depois da seleção.
        aperta(area.get_by_test_id("analise-familia-espacial"))
        expect(apresentacao).to_have_attribute("data-aba", "espacial")
        expect(apresentacao).to_contain_text("não representa um trajeto por estradas")
        expect(area.get_by_test_id("analise-painel")).to_have_count(0)
        expect(area.get_by_test_id("analise-selecao-alterar")).to_have_text("Selecionar os territórios")
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        aperta(area.get_by_test_id("analise-selecao-alterar"))
        expect(area).to_have_attribute("data-aba", "territorios")
        page.wait_for_timeout(400)
        assert not painel_calls, "abrir as abas sem territórios não pede nada ao motor"
        estados, sent = ok(lambda: aperta(territorios.get_by_test_id("analise-territorios-estados")))
        # nivel e indicador vão em todo pedido (sem nivel, o motor responde no formato de 21/10).
        assert sent.get("nivel") == "estados" and set(sent) == {"competencia", "categoria", "nivel", "indicador"}, sent
        assert sent.get("indicador") == "densidade", sent
        expect(area).to_have_attribute("data-estado", "E1")
        itens_estado = [item for item in estados["itens"] if item["tipo"] == "estado"]
        assert itens_estado and all(item["tipo"] == "estado" for item in estados["itens"]), "estados e municípios nunca juntos"
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
        expect(territorios).to_be_visible()
        expect(territorios.get_by_test_id("analise-territorios-estados")).to_contain_text("Todos os estados")
        expect(territorios.get_by_test_id("analise-territorios-estados")).to_have_attribute("aria-pressed", "true")
        expect(territorios.get_by_test_id("analise-territorios-todos")).to_contain_text("Todos os municípios do Brasil")
        linha_am = territorios.locator('[data-testid="analise-grupo"][data-id="' + AM + '"]')
        expect(linha_am).to_contain_text("Amazonas")
        expect(linha_am.get_by_test_id("analise-grupo-ver")).to_have_text(re.compile(r"Ver os \d+ municípios"))
        expect(linha_am.get_by_test_id("analise-grupo-todos")).to_have_attribute("aria-label", "Todos os municípios do Amazonas")
        expect(area.get_by_test_id("analise-trilha")).to_contain_text("Brasil")
        # A rotatividade não se executa com a base do Brasil, mas a aba abre (sem aria-disabled), com o motivo dentro dela.
        expect(area.get_by_test_id("analise-familia-rotatividade")).to_have_attribute("data-disponivel", "false")
        expect(area.get_by_test_id("analise-familia-rotatividade")).not_to_have_attribute("aria-disabled", "true")
        # Ajustes dentro da análise (23/10/2026): o painel da aba escolhida começa pela apresentação e mostra só o que vale para
        # ela; nos estados (E1), o indicador, a competência e os grupos e faixas. A escala sai dos ajustes: fica na barra junto do
        # desenho. A troca para a aba da análise já escolhida não pede nada ao motor.
        calls = len(painel_calls)
        aba_analise("distribuicao")
        painel_da_aba = area.get_by_test_id("analise-aba-painel")
        expect(painel_da_aba).to_have_attribute("role", "tabpanel")
        expect(painel_da_aba).to_have_attribute("data-aba", "distribuicao")
        expect(area.get_by_test_id("analise-familia-distribuicao")).to_have_attribute("aria-controls", "analise-aba-painel")
        expect(painel_da_aba.get_by_test_id("analise-apresentacao")).to_contain_text("Cada bolha é um município")
        expect(painel_da_aba.get_by_test_id("analise-selecao-alterar")).to_have_text("Alterar a seleção")
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
        shot("01-estados")

        # 3. Enter na bolha do estado abre os municípios dele (E2): a lista do estado aparece, marcada; a trilha leva de volta. Com
        # o mapa disponível e sem cor própria da análise, o pedido leva os 5 grupos iguais (quintis) do mapa; o gráfico não muda.
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
        expect(area.get_by_test_id("analise-trilha-atual")).to_have_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        aba_selecao()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        expect(linha_am).to_have_attribute("data-aberto", "true")
        lista_am = linha_am.get_by_test_id("analise-grupo-unidades")
        unidades_am = lista_am.get_by_test_id("analise-unidade")
        total_am = unidades_am.count()
        assert total_am == len(am["itens"]), (total_am, len(am["itens"]))
        assert all(caixa.is_checked() for caixa in lista_am.locator("input[type=checkbox]").all())
        # Dica no mouse (a maior bolha) e no foco (outra bolha).
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

        # 4. Marcar e desmarcar na lista: tirar PARINTINS pede os demais; "Desmarcar todos" esvazia sem pedir nada; "Marcar todos"
        # volta ao estado inteiro; a trilha diz quantos.
        _, sent = ok(lambda: marca(lista_am.locator('[data-testid="analise-unidade"][data-id="' + PARINTINS + '"] input')))
        restantes = {item.get_attribute("data-id") for item in unidades_am.all()} - {PARINTINS}
        assert sent["base"]["municipios"]["estados"] == [] and set(sent["base"]["municipios"]["ids"]) == restantes, sent
        expect(area.get_by_test_id("analise-trilha")).to_contain_text("Amazonas")
        expect(area.get_by_test_id("analise-trilha-atual")).to_have_text(str(len(restantes)) + " municípios")
        expect(area.locator('[data-testid="analise-bolha"][data-id="' + PARINTINS + '"]')).to_have_count(0)
        calls = len(painel_calls)
        aperta(lista_am.get_by_test_id("analise-unidades-desmarcar-todos"))
        expect(area.get_by_test_id("analise-vazio")).to_contain_text("Selecione os territórios que deseja analisar.")
        # Sem seleção, nenhum resultado anterior fica à vista: nem bolhas, nem a frase-resumo.
        expect(area.locator('[data-testid="analise-bolha"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-resumo")).to_have_text("")  # a região da frase fica, vazia
        expect(area.get_by_test_id("analise-trilha-atual")).to_have_text("Nenhum município marcado")
        assert all(not caixa.is_checked() for caixa in lista_am.locator("input[type=checkbox]").all())
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "sem unidades marcadas, nada é pedido ao motor"
        # A busca é só um complemento: pelo código, marca um município sem abrir lista nenhuma.
        busca = territorios.get_by_test_id("analise-busca")
        busca.fill("130420")
        _, sent = ok(lambda: marca(territorios.locator('[data-testid="analise-busca-item"][data-id="' + TEFE + '"] input')))
        assert sent["base"] == {"municipios": {"todos": False, "estados": [], "ids": [TEFE]}}, sent
        drawn([TEFE])
        expect(area.get_by_test_id("analise-trilha-atual")).to_have_text("1 município")
        busca.fill("")
        aperta(lista_am.get_by_test_id("analise-unidades-marcar-todos"))
        drawn(ids_am)
        expect(area.get_by_test_id("analise-trilha-atual")).to_have_text(re.compile(r"Amazonas \(\d+ municípios\)"))
        shot("03-lista")

        # 5. De volta aos estados pela trilha ("Brasil") e de novo ao Amazonas pela lista ("Ver os N municípios").
        aperta(area.locator('[data-testid="analise-trilha-item"][data-acao="estados"]'))
        drawn(esperados(estados))
        expect(area).to_have_attribute("data-estado", "E1")
        expect(area.get_by_test_id("analise-instrucao")).to_be_visible()
        aperta(linha_am.get_by_test_id("analise-grupo-ver"))
        drawn(ids_am)
        expect(linha_am).to_have_attribute("data-aberto", "true")

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

        # 7. Régua: "acima de" pelo teclado; aparecem só as unidades do corte, nada é recalculado.
        regua = abre("regua").get_by_test_id("analise-regua")
        dominio = am["dominios"]["densidade"]
        assert [float(regua.get_attribute("data-dominio-min")), float(regua.get_attribute("data-dominio-max"))] == dominio
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

        # 9. Análise espacial. A disponibilidade vem do motor (`disponibilidade.espacial`). Disponível: a referência por critério,
        # na ordem do motor; "Usar o primeiro" (com empate, a escolha); X = distância. Indisponível (por exemplo, quando o
        # referencial, SIRGAS 2000 ou WGS 84, não é premissa da fonte): a aba fica desabilitada, com o motivo do motor, e nada é
        # pedido.
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
        else:
            aperta(area.get_by_test_id("analise-familia-espacial"))
            # Os ajustes da análise espacial: o mesmo indicador, a competência e a referência (resumo e o botão do painel).
            expect(ajustes).to_have_attribute("data-familia", "espacial")
            expect(ajustes.get_by_test_id("analise-indicador-densidade")).to_have_attribute("aria-checked", "true")
            expect(ajustes.get_by_test_id("analise-referencia-resumo")).to_have_text("nenhuma ainda")
            expect(ajustes.get_by_test_id("analise-referencia-escolher")).to_be_visible()
            for ausente in ("analise-agrupar", "analise-janela-escolher", "analise-visao-classes", "analise-escala"):
                expect(ajustes.get_by_test_id(ausente)).to_have_count(0)
            referencia = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
            expect(referencia).to_be_visible()
            expect(referencia.get_by_test_id("analise-nota-tpl11")).to_contain_text("linha reta")
            referencia.get_by_test_id("analise-ref-criterio").select_option("densidade")
            referencia.get_by_test_id("analise-ref-ordem").select_option("desc")
            with page.expect_response(lambda r: r.url.endswith("/api/painel/referencias"), timeout=120000) as event:
                aperta(referencia.get_by_test_id("analise-ref-listar"))
            assert event.value.status == 200, event.value.text()[:2000]
            lista = event.value.json()
            candidatos = referencia.get_by_test_id("analise-ref-candidato")
            expect(candidatos).to_have_count(len(lista["candidatos"]))
            for row, candidato in zip(candidatos.all()[:5], lista["candidatos"][:5]):
                expect(row).to_have_attribute("data-id", candidato["id"])
                expect(row).to_contain_text(str(candidato["posicao"]) + "º")
            primeiros = [item for item in lista["candidatos"] if item["posicao"] == 1]
            if len(primeiros) == 1:
                response, sent = respond(lambda: aperta(referencia.get_by_test_id("analise-ref-primeiro")))
            else:
                aperta(referencia.get_by_test_id("analise-ref-primeiro"))
                expect(referencia.get_by_test_id("analise-ref-empate")).to_be_visible()
                expect(candidatos).to_have_count(len(primeiros))
                marca(candidatos.first.locator("input"))
                response, sent = respond(lambda: aperta(referencia.get_by_test_id("analise-ref-aplicar")))
            assert sent["referencia"] == {"membros": [primeiros[0]["id"]], "criterio": {"atributo": "densidade", "ordem": "desc",
                                                                                         "universo": universo_am}}, sent
            if real:
                assert response.status == 200, response.text()[:2000]
            if response.status == 200:
                espacial = response.json()
                expect(eixo_x).to_have_attribute("data-eixo", "distancia")
                expect(eixo_y).to_have_attribute("data-eixo", "densidade")
                drawn(esperados(espacial, distancia=True))
                desenhadas = bubbles()
                for item in espacial["itens"]:
                    if item["id"] in desenhadas:
                        assert float(desenhadas[item["id"]]["distancia"]) == item["distancia_km"], (desenhadas[item["id"]], item)
                expect(area.get_by_test_id("analise-nota-distancia")).to_contain_text("linha reta")
                expect(area.get_by_test_id("analise-titulo")).to_contain_text("e distância até")
                # Na análise espacial, o convite ao mapa ("onde ficam?"), com a vista no gráfico.
                expect(area.get_by_test_id("analise-convite-mapa")).to_have_text("Ver onde ficam no mapa")
                expect(area).to_have_attribute("data-desenho", "grafico")
                shot("06-espacial")
            else:
                # O motor recusou a distância (catálogo sintético, versão externa). Quando ele oferece a escolha da premissa, a
                # tela mostra as opções que ele mandou (sem lista fixa) e pede de novo com a escolhida; depois, a volta ao
                # último gráfico calculado, sem recalcular.
                assert response.status == 422, response.text()[:2000]
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
                        expect(eixo_x).to_have_attribute("data-eixo", "distancia")
                if area.get_by_test_id("analise-erro").count():
                    calls = len(painel_calls)
                    aperta(area.get_by_test_id("analise-voltar-calculado"))
                    expect(area.get_by_test_id("analise-erro")).to_have_count(0)
                    expect(eixo_x).to_have_count(0)
                    drawn(ids_am)
                    page.wait_for_timeout(400)
                    assert len(painel_calls) == calls, "voltar ao último gráfico não recalcula"
            fecha()

        # 10. Tendência: a janela é escolha da pessoa (sem janela padrão); Classes com a contagem por classe do motor acima do
        # gráfico; Mudança com os percentuais do motor; Séries com as linhas das unidades escolhidas.
        calls = len(painel_calls)
        aperta(area.get_by_test_id("analise-familia-tendencia"))
        expect(area.get_by_test_id("analise-painel")).to_have_attribute("data-painel", "janela")
        expect(area.get_by_test_id("analise-aviso-familia")).to_contain_text("Escolha a janela da tendência")
        # Os ajustes da tendência: o mesmo indicador (a troca de aba o mantém), a janela (resumo e o botão do painel) e a visão,
        # sem competência nem grupos e faixas.
        expect(ajustes).to_have_attribute("data-familia", "tendencia")
        expect(ajustes.get_by_test_id("analise-indicador-densidade")).to_have_attribute("aria-checked", "true")
        for controle in ("analise-janela-texto", "analise-janela-escolher", "analise-visao-classes", "analise-visao-mudanca",
                         "analise-visao-series"):
            expect(ajustes.get_by_test_id(controle)).to_be_visible()
        for ausente in ("analise-competencia", "analise-agrupar", "analise-referencia-escolher", "analise-escala"):
            expect(ajustes.get_by_test_id(ausente)).to_have_count(0)
        page.wait_for_timeout(400)
        atalho = "ultimos4junhos" if real else "todas"
        tendencia, sent = ok(lambda: aperta(area.get_by_test_id("analise-janela").get_by_test_id("analise-janela-atalho-" + atalho)))
        janela = sent["tendencia"]["competencias"]
        assert len(janela) >= 4 and sent["competencia_inicial"] == janela[0] and sent["competencia"] == janela[-1], sent
        assert sent.get("indicador") == "densidade" and "referencia" not in sent, sent
        fecha()
        drawn(esperados(tendencia))
        expect(area.get_by_test_id("analise-titulo")).to_contain_text("Tendência da densidade de médicos")
        desenhadas = bubbles()
        for item in tendencia["itens"]:
            if item["id"] in desenhadas and item.get("tendencia") is not None:
                classe = item["tendencia"].get("classe") if item["tendencia"].get("avaliavel", True) else None
                assert desenhadas[item["id"]]["classe"] == (classe or "NAO_AVALIAVEL"), (desenhadas[item["id"]], item)
        if (tendencia.get("tendencia") or {}).get("contagens"):
            for codigo, valor in tendencia["tendencia"]["contagens"].items():
                classe = area.locator('[data-testid="analise-contagem-classe"][data-classe="' + codigo + '"]')
                if classe.count():
                    expect(classe).to_have_attribute("data-contagem", str(valor))
        expect(area.get_by_test_id("analise-legenda-cor")).to_have_attribute("data-camada", "classes")
        # As classes explicadas na aba, e o motivo das unidades sem classificação em palavras, pelas contagens do motor, sem os
        # códigos internos; a dica de uma bolha sem classificação diz por quê.
        expect(area.get_by_test_id("analise-apresentacao")).to_have_attribute("data-aba", "tendencia")
        expect(area.get_by_test_id("analise-apresentacao-classes")).to_contain_text("Aceleração do crescimento")
        topo_tendencia = tendencia.get("tendencia") or {}
        sem_classe = (topo_tendencia.get("contagens") or {}).get("SEM_CLASSIFICACAO") or 0
        nota_sem = area.get_by_test_id("analise-nota-sem-classificacao")
        if sem_classe:
            por_motivo = topo_tendencia.get("sem_classificacao_por_motivo") or {}
            if por_motivo.get("MUDANCA_DE_DIRECAO"):
                expect(nota_sem).to_contain_text(re.compile(re.escape(milhar(por_motivo["MUDANCA_DE_DIRECAO"])) +
                                                            r" (municípios|município) por mudança de direção"))
            if por_motivo.get("SERIE_ESTAVEL"):
                expect(nota_sem).to_contain_text(re.compile(re.escape(milhar(por_motivo["SERIE_ESTAVEL"])) +
                                                            r" (municípios|município) por série estável"))
            expect(nota_sem).not_to_contain_text(re.compile(r"MUDANCA_DE_DIRECAO|SERIE_ESTAVEL"))
            sem_direcao = next((item for item in tendencia["itens"] if item["id"] in desenhadas and
                                (item.get("tendencia") or {}).get("motivo") == "MUDANCA_DE_DIRECAO"), None)
            if sem_direcao:
                # A dica no foco (a mesma do mouse), sem depender de onde a bolha está.
                area.locator('[data-testid="analise-bolha"][data-id="' + sem_direcao["id"] + '"]').focus()
                dica = area.get_by_test_id("analise-dica")
                expect(dica).to_contain_text("o indicador subiu em alguns trechos e caiu em outros (mudança de direção)")
                expect(dica).not_to_contain_text("MUDANCA_DE_DIRECAO")
                page.keyboard.press("Escape")
        else:
            expect(nota_sem).to_have_count(0)
        shot("07-classes")
        calls = len(painel_calls)
        area.get_by_test_id("analise-visao-mudanca").click()
        expect(area.get_by_test_id("analise-legenda-cor")).to_have_attribute("data-camada", "variacao")
        desenhadas = bubbles()
        for item in tendencia["itens"]:
            valor = (item.get("variacao_percentual") or {}).get("densidade")
            if item["id"] in desenhadas:
                assert (desenhadas[item["id"]]["variacao"] is None) == (valor is None), (desenhadas[item["id"]], item)
                if valor is not None:
                    assert float(desenhadas[item["id"]]["variacao"]) == valor
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
        shot("08-mudanca")
        area.get_by_test_id("analise-visao-series").click()
        expect(area.get_by_test_id("analise-series-vazio")).to_be_visible()
        # Em Séries, a escala não se aplica, e o mapa fica desligado, com o motivo no title (a visão Séries é só do gráfico).
        expect(area.get_by_test_id("analise-escala")).to_have_count(0)
        expect(area.get_by_test_id("analise-desenho-mapa")).to_have_attribute("aria-disabled", "true")
        expect(area.get_by_test_id("analise-desenho-mapa")).to_have_attribute("title", re.compile("Na visão Séries"))
        expect(area).to_have_attribute("data-desenho", "grafico")
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        tabela = area.get_by_test_id("analise-tabela")
        for chave in (MANAUS, TEFE):
            marca(tabela.locator('[data-testid="analise-linha"][data-id="' + chave + '"] input[type=checkbox]'))
        series = area.get_by_test_id("analise-series")
        expect(series.get_by_test_id("analise-serie")).to_have_count(2)
        expect(series.get_by_test_id("analise-velocidades")).to_be_visible()
        page.wait_for_timeout(400)
        assert len(painel_calls) == calls, "trocar a visão da tendência não pede nada ao motor"
        shot("09-series")
        area.get_by_test_id("analise-visao-classes").click()

        # 11. Rotatividade com a base do Brasil: a aba abre para a apresentação, com o motivo de não se executar e "Enviar meus
        # dados"; o desenho continua com a tendência, e nada é pedido ao motor.
        calls = len(painel_calls)
        aperta(area.get_by_test_id("analise-familia-rotatividade"))
        expect(area).to_have_attribute("data-aba", "rotatividade")
        expect(area.get_by_test_id("analise-apresentacao")).to_contain_text("A base do Brasil tem contagens de profissionais")
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

        area.get_by_test_id("analise-grafico").evaluate("e => e.scrollIntoView({block: 'start'})")
        for chave in (MANAUS, TEFE):
            bolha = area.locator('[data-testid="analise-bolha"][data-id="' + chave + '"]')
            if bolha.get_attribute("data-selecionado") != "true":
                bolha.focus()
                bolha.press("Enter")
            expect(bolha).to_have_attribute("data-selecionado", "true")
        comparar = abre("comparar").get_by_test_id("analise-comparar")
        expect(comparar.get_by_test_id("analise-comparar-item")).to_have_count(2)
        comparado, sent = ok(lambda: aperta(comparar.get_by_test_id("analise-comparar-calcular")))
        assert sorted(sent["comparar"]) == sorted([MANAUS, TEFE]), sent
        if comparado.get("comparacao"):
            expect(comparar.get_by_test_id("analise-comparacao")).to_be_visible()
            expect(comparar.get_by_test_id("analise-comparacao-linha").first).to_be_visible()
        fecha()
        juntar = abre("juntar").get_by_test_id("analise-juntar")
        juntar.get_by_test_id("analise-juntar-nome").fill("Capital e Tefé")
        junto, sent = ok(lambda: aperta(juntar.get_by_test_id("analise-juntar-criar")))
        assert sent["conjuntos"] == [{"id": "c1", "rotulo": "Capital e Tefé", "membros": [MANAUS, TEFE]}], sent
        conjunto = next(item for item in junto["itens"] if item["id"] == "c1")
        assert conjunto["tipo"] == "conjunto" and conjunto["contagem"] == "SOMA_DOS_COMPONENTES"
        drawn(esperados(junto))
        expect(area.locator('[data-testid="analise-bolha"][data-id="c1"]')).to_have_attribute("data-tipo", "conjunto")
        expect(area.get_by_test_id("analise-simbolos")).to_contain_text("possível dupla contagem")
        fecha()
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        expect(area.locator('[data-testid="analise-linha"][data-id="c1"]')).to_contain_text("soma das contagens dos componentes")
        aperta(area.get_by_test_id("analise-detalhes-metodo"))
        expect(area.locator('[data-limitacao="SOMA_COM_POSSIVEL_DUPLA_CONTAGEM"]')).to_contain_text("possível dupla contagem")
        shot("10-funcoes")

        # 13. Exportar: CSV com todos os itens, em precisão integral, com a avaliabilidade e o motivo; Detalhes com a tabela e os
        # não avaliáveis.
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

        # 14. Base versionada: todos os municípios do Brasil no modo leve, sem escala logarítmica automática; tabela em páginas;
        # régua que só esconde; dica no mouse.
        if real:
            aba_selecao()
            brasil, sent = ok(lambda: aperta(territorios.get_by_test_id("analise-territorios-todos")))
            assert sent["base"] == {"municipios": {"todos": True, "estados": [], "ids": []}}, sent
            plotaveis = [item for item in brasil["itens"] if item["densidade"] is not None]
            assert len(brasil["itens"]) > 5000, len(brasil["itens"])
            chart = area.get_by_test_id("analise-grafico")
            expect(chart).to_have_attribute("data-modo", "leve", timeout=30000)
            expect(chart).to_have_attribute("data-desenhadas", str(len(plotaveis)), timeout=30000)
            expect(eixo_y).to_have_attribute("data-escala", "linear")
            expect(area.get_by_test_id("analise-arranjo-nota")).to_contain_text("faixa limitada")
            expect(area.get_by_test_id("analise-trilha-atual")).to_contain_text("Todos os municípios")
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

        # 15. Celular (390 px): sem rolagem horizontal; as famílias em abas roláveis; as funções num botão "Ferramentas"; o painel
        # sobe da base da tela.
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
        page.set_viewport_size({"width": 1440, "height": 900})

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    print("ÁREA DE ANÁLISE PASS: abertura com as cinco abas, base sem seleção automática, estados pela Seleção de Territórios, "
          "territórios em lista, eixo do indicador, quintis do mapa no pedido, régua, grupos, espacial, tendência com as classes "
          "explicadas, rotatividade com o motivo, funções, exportação e celular" +
          (" (base versionada)." if real else " (catálogo sintético)."))


if __name__ == "__main__":
    main()
