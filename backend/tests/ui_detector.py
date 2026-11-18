"""Detector de Sinais Territoriais na página única (comando V23, Proposta V3, Parte B), com a base versionada (somente leitura).

Confere, contra as respostas de POST /api/detector:
- a ferramenta na navegação principal ("Detector de Sinais"), que não pede nada ao motor sem territórios selecionados;
- a primeira tela para os municípios de Santa Catarina: a lista de cinco colunas (Território · Sinal · Alerta · Por quê · Último
  registro; desde o AJ-04, de 18/11/2026, cada sinal com nível numa linha), 50 territórios por página, com a data do registro mais
  recente à vista; o resumo dos níveis, clicável como filtro; os filtros numa linha (Até, Nível, Sinal e Buscar); a ordem pelos
  cabeçalhos; o nível sempre escrito, com o tipo de critério;
- ABELARDO LUZ (SC), com quatro sinais de dois níveis: uma linha por sinal, do mais grave ao menos grave, com o nome, o nível, o
  tipo de critério e a frase de cada um (a do principal, da lista; a dos outros, do detalhe, que a lista pede ao motor sozinha);
- o perfil da base antes da ferramenta: fechado na base do Brasil (sem pedido ao motor) e, aberto, com o "dá para / não dá para";
- os detalhes de RIO RUFINO (SC): a série observada com o registro do pico marcado, os 12 sinais (11 itens: 1 e 2 juntos) em
  quatro grupos mais Juntos, cada um com o nível, uma frase e o "Entenda" (mouse, teclado e "Ver explicação completa"), a
  explicação completa com os sete campos e o histórico de sinais;
- a janela entre competências reais: com o fim em jun/2023, o salto de RIO RUFINO ainda é "verificar registro";
- "Ajustar critérios": os limites em frases, com os campos dentro delas; trocar um valor torna a configuração exploratória, com
  aviso no alto e "Voltar ao padrão" sempre à vista;
- a ficha metodológica (PDF), servida com a interface e aberta numa nova aba pelo link e pelo "Ver explicação completa" dos
  "Entenda" (o da ferramenta e os dos cabeçalhos da lista, escritos pela página), e "Exportar o método (JSON)", com a régua da
  data, o monitoramento e as versões, os mesmos números do motor: desde o AJ-03 (18/11/2026), "Como foi calculado" saiu da tela;
  a régua usada de fato em cada nível (as faixas vizinhas, quando o porte não basta, e "sem comparações suficientes" no crítico de
  3.000 médicos para cima) continua conferida, no arquivo exportado;
- um estado como unidade na mesma seleção, com a régua própria dos estados (na exportação) e a ressalva de leitura junto da lista;
- as visões Mapa (os pontos pelo nível, com a legenda escrita) e Gráfico (a distância e a taxa, pelo nível), com a dica que nomeia o
  sinal e diz quantos outros sinais com nível o território tem;
- com a janela até jun/2021, os sinais comparados em 2 anos (8 a 10) com nível, a série da taxa com a referência e os textos do
  motor; e "Simular recuperação", que abre o Simulador de Cenários com a meta hipotética de voltar ao patamar, sem mudar a
  seleção principal;
- numa tela de celular, com toque: o "Entenda" abre pelo toque, cabe na largura e fecha com um toque fora; a lista vira cartões e
  nada passa da largura;
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import json
import math
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, linha_do_estado, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
SC, PR, RIO_RUFINO, ABELARDO_LUZ = "42", "41", "code:421505", "code:420010"
ESTADOS = ("critico", "elevado", "moderado", "sem_alerta", "sem_comparacoes", "sem_nivel")
NOMES = {"critico": "Crítico", "elevado": "Elevado", "moderado": "Moderado"}
# AJ-05 (18/11/2026): o tipo de critério na tela. O campo `criterio` do motor e as exportações continuam "por convenção" para o
# limite fixo; a tela diz "limite fixo".
NA_TELA = {"por convenção": "limite fixo", "comparado com a base": "comparado com a base"}
# AJ-04: na lista, a frase do sinal principal vem sem a contagem dos outros sinais, que têm as linhas deles.
OUTROS = re.compile(r" \(\+\d+ sina(?:l|is)\)$")
GRAVIDADE = {"critico": 3, "elevado": 2, "moderado": 1}
SINAIS = ["estrutural", "declinio", "desaceleracao", "instabilidade", "perda", "patamar", "disponibilidade", "posicao", "defasagem", "contexto",
          "coexistencia"]


def estado_do_alerta(item):
    return item["alerta"]["nivel"] or item["alerta"]["estado"]


def com_o_sinal(item, sinal):
    return any(dado["sinal"] == sinal for dado in item["alerta"]["sinais"])


def regua_exportada(calibracao):
    """A régua da data como "Exportar o método (JSON)" a leva (AJ-03): os números do motor, campo a campo, com os nomes da tela."""
    def faixas(itens, campo):
        return [{"porte": item["porte"], "comparacoes": item["comparacoes"], "niveis": {
            nivel: {"umEm": item[nivel]["um_em"], "pede": item[nivel]["pede"], "cortePct": item[nivel][campo],
                    "origem": item[nivel]["origem"] if item[nivel]["origem"] in ("vizinhas", "todas") else "porte",
                    "comparacoes": item[nivel].get("comparacoes"), "corteAtePct": item[nivel].get(campo + "_ate")}
            for nivel in ("moderado", "elevado", "critico") if item.get(nivel)}} for item in itens]
    monitoramento = calibracao["monitoramento"]
    return {"competencia": calibracao["competencia"], "intervaloMeses": calibracao["intervalo_meses"],
            "perda": faixas(calibracao["perda"], "queda_pct"), "patamar": faixas(calibracao["patamar"], "afastamento_pct"),
            "monitoramento": {"avaliadas": monitoramento["avaliadas"], "raras": monitoramento["raras"], "taxaPct": monitoramento.get("taxa_pct"),
                              "esperadoPct": monitoramento.get("esperado_pct"), "avisoDaBase": monitoramento.get("aviso_da_base") is True}}


def sinal_do_historico(passo, nomes):
    """O sinal do alerta numa data do histórico, como a tela o nomeia (AJ-03): a coluna com o nível do alerta; no empate, a
    primeira na ordem dos sinais."""
    colunas = [("ausencia" if passo.get("valor") == 0 else "estrutural", passo.get("estrutural")),
               ("declinio", (passo.get("declinio") or {}).get("classe")), ("desaceleracao", (passo.get("desaceleracao") or {}).get("classe")),
               ("instabilidade", passo.get("instabilidade")), ("perda", (passo.get("perda") or {}).get("classe")),
               ("patamar", (passo.get("patamar") or {}).get("classe"))]
    return next((nomes[chave] for chave, nivel in colunas if nivel == passo["alerta"]), None)


def curta(competencia):
    """A data como a tela a escreve: "jun/2024"."""
    return ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")[int(competencia[4:]) - 1] + "/" + competencia[:4]


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "este roteiro usa a base Brasil versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        falhas, chamadas_llm, pedidos = [], [], []
        page.on("pageerror", lambda error: falhas.append(str(error)))
        page.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: pedidos.append(request) if request.url.endswith("/api/detector") else None)
        # Os detalhes pedidos ao motor: ao abrir a linha ou, desde o AJ-04 (18/11/2026), antes, pela própria lista, para a frase de
        # cada sinal dos territórios à vista com mais de um sinal com nível (dois de cada vez).
        detalhes_pedidos = []
        page.on("response", lambda resposta: detalhes_pedidos.append((options_of(resposta.request), resposta)) if resposta.url.endswith(
            "/api/detector") and resposta.request.method == "POST" and options_of(resposta.request).get("detalhe") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        botao = area.get_by_test_id("analise-ferramenta-detector")
        detector = area.get_by_test_id("detector")

        def do_detector(acao, condicao=None, da_pagina=None):
            """A resposta de /api/detector que a ação provocou (a lista ou o perfil, nunca o detalhe de um território) e as opções do
            pedido."""
            with (da_pagina or page).expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST" and
                    not options_of(r.request).get("detalhe") and (condicao is None or condicao(options_of(r.request))), timeout=180000) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        def detalhe_pedido(codigo, condicao=None):
            """O detalhe do território que a tela pediu ao motor (ao abrir a linha ou, antes, para as frases da lista) e as opções
            do pedido: o mais recente que atende à condição."""
            for _ in range(600):
                achados = [(opcoes, resposta) for opcoes, resposta in detalhes_pedidos
                           if opcoes.get("detalhe") == codigo and (condicao is None or condicao(opcoes))]
                if achados:
                    opcoes, resposta = achados[-1]
                    assert resposta.status == 200, resposta.text()[:2000]
                    return resposta.json(), opcoes
                page.wait_for_timeout(300)
            raise AssertionError("a tela não pediu ao motor o detalhe de " + codigo)

        def das_listas(lista_de_pedidos):
            """Os pedidos da lista (sem os do detalhe de um território)."""
            return [pedido for pedido in lista_de_pedidos if not options_of(pedido).get("detalhe")]

        def baixado(botao):
            """O arquivo que o botão baixa, lido como texto."""
            with page.expect_download() as evento:
                botao.click()
            return Path(evento.value.path()).read_text(encoding="utf-8")

        def linha(codigo):
            return detector.locator('[data-testid="detector-linha"][data-id="' + codigo + '"]')

        def sinal_da_tela(detalhe, chave):
            return detalhe.locator('[data-testid="detector-fenomeno"][data-chave="' + chave + '"]')

        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. A ferramenta fica na navegação principal; sem territórios, diz isso e não pede nada ao motor.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
        expect(botao).to_be_enabled()
        expect(botao).to_have_text("Detector de Sinais")
        expect(botao).to_have_attribute("aria-pressed", "false")
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "detector")
        expect(detector).to_have_attribute("data-estado", "sem-selecao")
        expect(detector.get_by_test_id("detector-titulo")).to_have_text("Detector de Sinais Territoriais")
        expect(detector.get_by_test_id("detector-sem-selecao")).to_contain_text("Nenhum território selecionado")
        page.wait_for_timeout(500)
        assert not pedidos, "sem territórios, nada é pedido ao motor"
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "")

        # 2. Os municípios de Santa Catarina: a lista de cinco colunas (AJ-04, 18/11/2026; antes, quatro, sem "Sinal"), um grupo de
        # linhas por território, 50 territórios por página, na visão Lista.
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
            linha_do_estado(territorios, SC).get_by_test_id("analise-grupo-todos").check()
        corpo, enviado = do_detector(lambda: botao.click())
        assert enviado == {"base": {"municipios": {"todos": False, "estados": [SC], "ids": []}}}, enviado
        assert len(corpo["linhas"]) == 295 and corpo["janela"]["fim"] == "202406" and corpo["exploratorio"] is False, corpo["janela"]
        assert corpo["versao"] == "DETECTOR-SINAIS/V3/1", corpo["versao"]
        expect(detector).to_have_attribute("data-estado", "pronto")
        expect(detector.get_by_test_id("detector-data")).to_contain_text("Registro mais recente da base: jun/2024")
        expect(detector.get_by_test_id("detector-data")).to_contain_text("não a de hoje")
        tabela = detector.get_by_test_id("detector-tabela")
        expect(tabela).to_have_attribute("data-linhas", "295")
        expect(detector.get_by_test_id("detector-linha")).to_have_count(50)
        expect(detector.get_by_test_id("detector-paginas")).to_contain_text("Página 1 de 6")
        cabecalhos = tabela.locator("thead th")
        expect(cabecalhos).to_have_count(5)
        for indice, nome in enumerate(("Território", "Sinal", "Alerta", "Por quê", "Último registro")):
            expect(cabecalhos.nth(indice)).to_contain_text(nome)
        expect(detector.get_by_test_id("detector-visual")).to_have_count(0)   # a Lista é a visão padrão
        expect(detector.get_by_test_id("detector-vista-lista")).to_have_attribute("aria-pressed", "true")
        expect(detector.get_by_test_id("detector-comparacao")).to_contain_text("usam a variação de jun/2022 a jun/2024")
        expect(detector.get_by_test_id("detector-aviso-da-base")).to_have_count(0)
        assert corpo["aviso_da_base"] is None, corpo["aviso_da_base"]
        # O resumo dos níveis: um nível por território (o maior entre os sinais), com os números do motor; sem conjuntos, não há
        # "sem nível". O nível vem sempre escrito, com o tipo de critério.
        niveis = corpo["resumo"]["niveis"]
        assert sum(niveis.values()) == 295 and niveis["critico"] >= 1 and niveis["elevado"] >= 1 and niveis["moderado"] >= 1, niveis
        assert niveis == {estado: sum(1 for item in corpo["linhas"] if estado_do_alerta(item) == estado) for estado in ESTADOS}, niveis
        resumo = detector.get_by_test_id("detector-resumo")
        expect(resumo).to_have_attribute("data-territorios", "295")
        for estado in ESTADOS[:5]:
            expect(resumo.get_by_test_id("detector-resumo-" + estado)).to_have_attribute("data-quantos", str(niveis[estado]))
        expect(resumo.get_by_test_id("detector-resumo-sem_nivel")).to_have_count(0)
        expect(resumo.get_by_test_id("detector-resumo-sem_alerta")).to_have_text(str(niveis["sem_alerta"]) + " sem alerta")
        primeira = detector.get_by_test_id("detector-linha").first
        expect(tabela).to_have_attribute("data-ordem", "nivel")
        expect(primeira).to_have_attribute("data-alerta", "critico")
        do_primeiro = next(item for item in corpo["linhas"] if item["id"] == primeira.get_attribute("data-id"))
        # A linha de cima do território é a do sinal principal do alerta: o nível dele, o tipo de critério e a frase da lista, sem a
        # contagem "(+N sinais)" (os outros sinais têm as linhas deles).
        expect(primeira.get_by_test_id("detector-sinal-linha")).to_have_count(max(1, len(do_primeiro["alerta"]["sinais"])))
        de_cima = primeira.get_by_test_id("detector-sinal-linha").first
        expect(de_cima).to_have_attribute("data-sinal", do_primeiro["alerta"]["sinal"])
        expect(de_cima.get_by_test_id("detector-sinal")).not_to_have_text("")
        expect(de_cima.get_by_test_id("detector-nivel")).to_have_text("Crítico")
        expect(de_cima.get_by_test_id("detector-criterio")).to_have_text(NA_TELA[do_primeiro["alerta"]["criterio"]])
        expect(de_cima.get_by_test_id("detector-por-que")).to_have_text(OUTROS.sub("", do_primeiro["alerta"]["por_que"]))
        assert do_primeiro["alerta"]["criterio"] in ("por convenção", "comparado com a base"), do_primeiro["alerta"]
        page.screenshot(path=str(OUTPUT / "detector-01-lista-real.png"), full_page=True)
        # O resumo é clicável e funciona como o filtro "Nível".
        resumo.get_by_test_id("detector-resumo-elevado").click()
        expect(detector.get_by_test_id("detector-filtro-nivel")).to_have_value("elevado")
        expect(tabela).to_have_attribute("data-linhas", str(niveis["elevado"]))
        assert set(detector.get_by_test_id("detector-linha").evaluate_all("els => els.map(e => e.dataset.alerta)")) == {"elevado"}
        # O alerta do território é o maior nível: a linha de cima diz "Elevado"; as outras, quando há, "Elevado" ou "Moderado".
        de_cada = detector.get_by_test_id("detector-linha").evaluate_all(
            "els => els.map(e => [...e.querySelectorAll('[data-testid=detector-sinal-linha] [data-testid=detector-nivel]')].map(n => n.textContent))")
        assert all(nomes[0] == "Elevado" and set(nomes) <= {"Elevado", "Moderado"} for nomes in de_cada), de_cada
        resumo.get_by_test_id("detector-resumo-elevado").click()
        expect(detector.get_by_test_id("detector-filtro-nivel")).to_have_value("todos")
        detector.get_by_test_id("detector-filtro-nivel").select_option("sem_alerta")
        expect(tabela).to_have_attribute("data-linhas", str(niveis["sem_alerta"]))
        expect(detector.get_by_test_id("detector-linha").first.get_by_test_id("detector-alerta")).to_have_text("Sem alerta")
        expect(detector.get_by_test_id("detector-linha").first.get_by_test_id("detector-nivel")).to_have_count(0)
        detector.get_by_test_id("detector-filtro-nivel").select_option("todos")
        # A ordem pelos cabeçalhos: pelo nome e de volta ao nível (a ordem não é um índice).
        detector.get_by_test_id("detector-ordem-nome").click()
        expect(tabela).to_have_attribute("data-ordem", "nome")
        expect(detector.get_by_test_id("detector-linha").first).to_have_attribute("data-id", min(corpo["linhas"], key=lambda item: item["rotulo"])["id"])
        detector.get_by_test_id("detector-ordem-nivel").click()
        expect(detector.get_by_test_id("detector-linha").first).to_have_attribute("data-alerta", "critico")

        # 2b. O perfil da base (comando V23, seção A.3) vem antes da ferramenta. Na base do Brasil, fica fechado e só é lido quando
        # a pessoa pede; aberto, mostra o que o Agente leu dela e o resumo "dá para / não dá para", como o motor mandou.
        perfil = area.get_by_test_id("perfil-da-base")
        expect(perfil).to_have_attribute("data-estado", "fechado")
        expect(perfil.get_by_test_id("perfil-da-base-botao")).to_have_attribute("aria-expanded", "false")
        assert not [pedido for pedido in pedidos if options_of(pedido).get("perfil")], "fechado, o perfil não é pedido ao motor"
        do_perfil, _ = do_detector(lambda: perfil.get_by_test_id("perfil-da-base-botao").click(), lambda opcoes: opcoes.get("perfil") is True)
        expect(perfil).to_have_attribute("data-estado", "pronto")
        expect(perfil).to_have_attribute("data-origem", "brasil")
        expect(perfil.get_by_test_id("perfil-da-base-resumo")).to_have_text("5.570 territórios · 22 registros, de jan/2014 a jun/2024.")
        # Desde a etapa 5 do comando V23, o resumo traz também o que a retroprojeção do Simulador sustenta (8 linhas viraram 11).
        assert len(do_perfil["perfil"]["da_para"]) == 11 and do_perfil["perfil"]["da_para"][0] == "Alertas moderados desde jun/2015 (o 2º ano da base).", (
            do_perfil["perfil"]["da_para"])
        assert do_perfil["perfil"]["da_para"][8] == ("Cenários do Simulador com a forma de projetar que a base escolheu: persistência com o "
                                                     "crescimento recente do estado."), do_perfil["perfil"]["da_para"]
        expect(perfil.get_by_test_id("perfil-da-para").locator("li")).to_have_text(do_perfil["perfil"]["da_para"])
        expect(perfil.get_by_test_id("perfil-nao-da-para").locator("li")).to_have_text(
            ["Alertas críticos nos estados como unidade: eles pedem 999 comparações, e esta base chega a 270.",
             "A faixa do Simulador nos estados como unidade: ela pede 200 casos por prazo, e esta base tem 189."])
        expect(perfil.locator('[data-testid="perfil-da-base-itens"] tbody tr')).to_have_count(8)
        expect(perfil.locator('[data-testid="perfil-da-base-itens"] tr[data-chave="serie_anual"]')).to_contain_text(
            "Usa os registros de junho, o mês presente em todos os anos (11 anos, de 2014 a 2024).")
        page.screenshot(path=str(OUTPUT / "detector-01b-perfil-da-base-real.png"), full_page=False)
        perfil.get_by_test_id("perfil-da-base-botao").click()
        expect(perfil).to_have_attribute("data-estado", "fechado")
        expect(perfil.get_by_test_id("perfil-da-base-corpo")).to_have_count(0)

        # 3. O filtro "Sinal": a linha passa quando o sinal tem nível nela (não só o sinal principal do alerta).
        com_poucos = [item for item in corpo["linhas"] if com_o_sinal(item, "estrutural")]
        assert com_poucos and len(com_poucos) == corpo["resumo"]["com_nivel"]["estrutural"], "há municípios de Santa Catarina com poucos médicos em jun/2024"
        detector.get_by_test_id("detector-filtro-sinal").select_option("estrutural")
        expect(tabela).to_have_attribute("data-linhas", str(len(com_poucos)))
        assert all("estrutural" in sinais.split() for sinais in detector.get_by_test_id("detector-linha").evaluate_all("els => els.map(e => e.dataset.sinais)"))
        detector.get_by_test_id("detector-filtro-sinal").select_option("todos")

        # 3b. AJ-04 (18/11/2026): cada sinal com nível numa linha, do mais grave ao menos grave, com o nome do sinal na coluna "Sinal".
        # ABELARDO LUZ (SC) tem quatro sinais com nível em jun/2024, dois elevados e dois moderados (um deles por limite fixo): quatro
        # linhas, com o nome e o último registro uma vez para o território. A frase do principal é a da lista; a de cada outro, a do
        # detalhe do território, que a lista pede ao motor sozinha. Os quatro vêm da mesma queda, e a linha de baixo diz isso. Os
        # contadores, os filtros e as páginas continuam por território.
        do_abelardo = next(item for item in corpo["linhas"] if item["id"] == ABELARDO_LUZ)
        dele = do_abelardo["alerta"]["sinais"]
        assert len(dele) == 4 and {item["nivel"] for item in dele} == {"elevado", "moderado"}, dele
        assert [GRAVIDADE[item["nivel"]] for item in dele] == sorted((GRAVIDADE[item["nivel"]] for item in dele), reverse=True), dele
        assert dele[0]["sinal"] == do_abelardo["alerta"]["sinal"] and "por convenção" in [item["criterio"] for item in dele], do_abelardo["alerta"]
        detector.get_by_test_id("detector-busca").fill("abelardo")
        expect(tabela).to_have_attribute("data-linhas", "1")
        abelardo = linha(ABELARDO_LUZ)
        expect(abelardo).to_have_attribute("data-linhas-de-sinal", "4")
        filas = abelardo.get_by_test_id("detector-sinal-linha")
        expect(filas).to_have_count(4)
        assert filas.evaluate_all("els => els.map(e => [e.dataset.sinal, e.dataset.nivel])") == [[item["sinal"], item["nivel"]] for item in dele]
        detalhe_do_abelardo, _ = detalhe_pedido(ABELARDO_LUZ, lambda o: not o.get("parametros") and (o.get("janela") or {}).get("fim", "202406") == "202406")
        do_sinal = {item["chave"]: item for item in detalhe_do_abelardo["fenomenos"]}
        # O nome, o nível e o critério de cada linha são os do detalhe; a frase, a do motor.
        assert [(do_sinal[item["sinal"]]["nivel"], do_sinal[item["sinal"]]["criterio_do_nivel"]) for item in dele] == [
            (item["nivel"], item["criterio"]) for item in dele], dele
        # Os nomes da coluna "Sinal" são os do filtro "Sinal" e os do detalhe.
        do_filtro = detector.get_by_test_id("detector-filtro-sinal").locator("option").evaluate_all(
            "els => Object.fromEntries(els.map(e => [e.value, e.textContent]))")
        assert [do_sinal[item["sinal"]]["nome"] for item in dele] == [do_filtro[item["sinal"]] for item in dele], do_filtro
        expect(abelardo.get_by_test_id("detector-sinal")).to_have_text([do_sinal[item["sinal"]]["nome"] for item in dele])
        expect(abelardo.get_by_test_id("detector-nivel")).to_have_text([NOMES[item["nivel"]] for item in dele])
        expect(abelardo.get_by_test_id("detector-criterio")).to_have_text([NA_TELA[item["criterio"]] for item in dele])
        expect(abelardo.locator('[data-testid="detector-por-que"][data-carregando="true"]')).to_have_count(0, timeout=120000)
        expect(abelardo.get_by_test_id("detector-por-que")).to_have_text(
            [OUTROS.sub("", do_abelardo["alerta"]["por_que"])] + [do_sinal[item["sinal"]]["situacao"] for item in dele[1:]])
        assert OUTROS.sub("", do_abelardo["alerta"]["por_que"]) == do_sinal[dele[0]["sinal"]]["situacao"], do_abelardo["alerta"]["por_que"]
        # O nome e o último registro, uma vez para o território: as quatro linhas e a da mesma queda.
        expect(abelardo.locator('th[scope="rowgroup"]')).to_have_count(1)
        expect(abelardo.locator('th[scope="rowgroup"]')).to_have_attribute("rowspan", "5")
        expect(abelardo.get_by_test_id("detector-ultimo")).to_have_count(1)
        expect(abelardo.get_by_test_id("detector-ultimo")).to_have_attribute("rowspan", "5")
        assert sorted(do_abelardo["alerta"]["mesma_queda"]) == sorted(item["sinal"] for item in dele), do_abelardo["alerta"]
        expect(abelardo.get_by_test_id("detector-linha-nota")).to_contain_text("vêm da mesma queda: contam como um evento.")
        page.screenshot(path=str(OUTPUT / "detector-01c-sinais-por-linha-real.png"), full_page=False)
        detector.get_by_test_id("detector-busca").fill("")
        expect(tabela).to_have_attribute("data-linhas", "295")

        # 4. RIO RUFINO (SC), pelo nome: o pico que volta (4 → 87 → 5) é descontinuidade de registro, sem alerta de queda; os
        # detalhes trazem a série com o registro do pico marcado e os 12 sinais (11 itens) em quatro grupos, mais Juntos.
        detector.get_by_test_id("detector-busca").fill("rio rufino")
        expect(tabela).to_have_attribute("data-linhas", "1")
        rio = linha(RIO_RUFINO)
        expect(rio.get_by_test_id("detector-registro")).to_have_attribute("data-marca", "descontinuidade")
        expect(rio.get_by_test_id("detector-registro")).to_have_text("Descontinuidade de registro (pico que volta)")
        expect(rio.get_by_test_id("detector-ultimo")).to_contain_text("jun/2024 · 5 médicos")
        rio.get_by_test_id("detector-abrir").click()
        detalhe_do_motor, _ = detalhe_pedido(RIO_RUFINO, lambda o: not o.get("janela") and not o.get("parametros"))
        assert detalhe_do_motor["territorio"]["registro"]["eventos"][0]["valores"] == [4, 87, 5], detalhe_do_motor["territorio"]["registro"]
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_have_attribute("data-id", RIO_RUFINO, timeout=120000)
        do_rio = detalhe_do_motor["linha"]["alerta"]
        expect(detalhe.get_by_test_id("detector-detalhe-alerta")).to_have_attribute("data-estado", do_rio["nivel"] or do_rio["estado"])
        # AJ-03: o alto do detalhe nomeia o sinal principal do alerta (em jun/2024, "Poucos médicos", moderado, por limite fixo).
        assert (do_rio["sinal"], do_rio["nivel"], do_rio["criterio"]) == ("estrutural", "moderado", "por convenção"), do_rio
        expect(detalhe.get_by_test_id("detector-detalhe-sinal")).to_have_text("Poucos médicos")
        expect(detalhe.locator('[data-testid="detector-serie-ponto"][data-marca="pico_que_volta"]')).to_have_count(1)
        expect(detalhe.locator('[data-testid="detector-serie-ponto"][data-competencia="202306"]')).to_have_attribute("data-marca", "pico_que_volta")
        grupos = detalhe.get_by_test_id("detector-grupo")
        assert grupos.evaluate_all("els => els.map(e => e.dataset.grupo)") == ["quantos", "mudou", "comparado", "onde", "juntos"]
        assert grupos.locator("h4").all_text_contents() == ["Quantos há", "Como mudou", "Comparado com outros", "Onde fica", "Juntos"]
        assert [(item["chave"], item["sinais"]) for item in detalhe_do_motor["grupos"]] == [
            ("quantos", ["estrutural"]), ("mudou", ["declinio", "desaceleracao", "instabilidade", "perda", "patamar"]),
            ("comparado", ["disponibilidade", "posicao", "defasagem"]), ("onde", ["contexto"]), ("juntos", ["coexistencia"])]
        fenomenos = detalhe.get_by_test_id("detector-fenomeno")
        expect(fenomenos).to_have_count(11)
        assert fenomenos.evaluate_all("els => els.map(e => e.dataset.chave)") == SINAIS
        assert [item["numero"] for item in detalhe_do_motor["fenomenos"]] == ["1–2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
        # Em cada sinal: o nível (ou o que a base diz no lugar), uma frase e o "Entenda", com os textos do motor.
        for item in detalhe_do_motor["fenomenos"]:
            da_tela = sinal_da_tela(detalhe, item["chave"])
            expect(da_tela).to_have_attribute("data-nivel", item["nivel"] or "")
            expect(da_tela).to_have_attribute("data-estado", item["estado_do_nivel"])
            expect(da_tela.get_by_test_id("detector-fenomeno-situacao")).to_contain_text(item["situacao"])
            if item["nivel"]:
                expect(da_tela.get_by_test_id("detector-nivel")).to_have_text(NOMES[item["nivel"]])
                expect(da_tela.get_by_test_id("detector-fenomeno-criterio")).to_contain_text(NA_TELA[item["criterio_do_nivel"]])
            else:
                expect(da_tela.get_by_test_id("detector-nivel")).to_have_count(0)
            expect(da_tela.get_by_test_id("detector-entenda-botao")).to_have_text("Entenda")
        # O sinal 4 é rotulado como exploratório e diz que mostra uma mudança de ritmo, não o que vem depois.
        do_ritmo = next(item for item in detalhe_do_motor["fenomenos"] if item["chave"] == "desaceleracao")
        assert do_ritmo["exploratorio"] is True and "não indica o que vem depois" in do_ritmo["entenda"]["texto"], do_ritmo
        # "Entenda" com o mouse: abre ao passar por cima, com duas ou três frases e um exemplo com números, e fecha ao sair.
        da_queda = sinal_da_tela(detalhe, "perda")
        do_motor_da_queda = next(item for item in detalhe_do_motor["fenomenos"] if item["chave"] == "perda")
        entenda = da_queda.get_by_test_id("detector-entenda")
        caixa = da_queda.get_by_test_id("detector-entenda-caixa")
        expect(caixa).to_have_count(0)
        da_queda.get_by_test_id("detector-entenda-botao").hover()
        expect(entenda).to_have_attribute("data-aberto", "true")
        expect(caixa).to_be_visible()
        expect(caixa).to_contain_text(do_motor_da_queda["entenda"]["texto"])
        expect(da_queda.get_by_test_id("detector-entenda-exemplo")).to_have_text("Exemplo: " + do_motor_da_queda["entenda"]["exemplo"])
        assert "2 para 1" in do_motor_da_queda["entenda"]["exemplo"], do_motor_da_queda["entenda"]   # o exemplo do anexo (nota da seção B.2)
        page.screenshot(path=str(OUTPUT / "detector-02-entenda-real.png"), full_page=False)
        detector.get_by_test_id("detector-titulo").hover()
        expect(caixa).to_have_count(0)
        # "Entenda" pelo teclado: abre ao receber o foco, e Esc fecha; "Ver explicação completa" abre os sete campos do sinal.
        da_queda.get_by_test_id("detector-entenda-botao").focus()
        expect(caixa).to_be_visible()
        expect(da_queda.get_by_test_id("detector-entenda-botao")).to_have_attribute("aria-expanded", "true")
        page.keyboard.press("Escape")
        expect(caixa).to_have_count(0)
        expect(da_queda.get_by_test_id("detector-fenomeno-explicacao")).to_have_count(0)
        da_queda.get_by_test_id("detector-entenda-botao").press("Enter")
        expect(caixa).to_be_visible()
        page.keyboard.press("Tab")
        expect(da_queda.get_by_test_id("detector-entenda-completa")).to_be_focused()
        page.keyboard.press("Enter")
        expect(caixa).to_have_count(0)
        explicacao = da_queda.get_by_test_id("detector-fenomeno-explicacao")
        expect(explicacao).to_be_visible()
        for campo, rotulo in (("observado", "O que foi observado"), ("criterio", "Qual critério"), ("habitual", "Comparado com o comum"),
                              ("significa", "O que significa"), ("naoSignifica", "O que não significa"), ("limitacoes", "Limitações do dado"),
                              ("qualidade", "Qualidade do registro")):
            expect(explicacao.get_by_test_id("detector-campo-" + campo).locator("dt")).to_have_text(rotulo)
            expect(explicacao.get_by_test_id("detector-campo-" + campo).locator("dd")).not_to_have_text("")
        expect(explicacao.get_by_test_id("detector-campo-observado").locator("dd")).to_have_text(do_motor_da_queda["observado"])
        expect(explicacao.get_by_test_id("detector-campo-habitual").locator("dd")).to_have_text(do_motor_da_queda["habitual"])
        expect(explicacao.get_by_test_id("detector-campo-qualidade").locator("dd")).to_contain_text("pico que volta")
        da_queda.get_by_test_id("detector-fenomeno-completa").click()
        expect(explicacao).to_have_count(0)
        # AJ-05 (18/11/2026): o critério do sinal 1–2, escrito pelo motor nos sete campos, diz "Limite fixo" (antes, "Por
        # convenção"); nenhum texto à vista no Detector traz "por convenção" nem "jeito", com as explicações de dois sinais abertas.
        dos_poucos = sinal_da_tela(detalhe, "estrutural")
        do_motor_dos_poucos = next(item for item in detalhe_do_motor["fenomenos"] if item["chave"] == "estrutural")
        assert do_motor_dos_poucos["criterio"].startswith("Limite fixo, pelo número de médicos no último registro"), do_motor_dos_poucos
        assert do_motor_dos_poucos["criterio_do_nivel"] == "por convenção", "o campo do motor não muda"
        dos_poucos.get_by_test_id("detector-fenomeno-completa").click()
        expect(dos_poucos.get_by_test_id("detector-campo-criterio").locator("dd")).to_have_text(do_motor_dos_poucos["criterio"])
        da_queda.get_by_test_id("detector-fenomeno-completa").click()
        texto_a_vista = detector.inner_text().lower()
        assert "convenção" not in texto_a_vista and "jeito" not in texto_a_vista, "por convenção ou jeito à vista no Detector"
        da_queda.get_by_test_id("detector-fenomeno-completa").click()
        dos_poucos.get_by_test_id("detector-fenomeno-completa").click()
        expect(detalhe.get_by_test_id("detector-fenomeno-explicacao")).to_have_count(0)
        detalhe.get_by_test_id("detector-historico-botao").click()
        expect(detalhe.get_by_test_id("detector-historico").locator("tbody tr")).to_have_count(22)
        expect(detalhe.get_by_test_id("detector-historico").locator('tbody tr[data-competencia="202401"]')).to_contain_text(
            "descontinuidade de registro")
        # AJ-03: em cada data com alerta, o histórico diz o nível e o sinal dele (a coluna com aquele nível; no empate, a primeira
        # na ordem dos sinais), pelos números do motor.
        nomes_da_tela = {"ausencia": "Nenhum médico registrado", "estrutural": "Poucos médicos",
                         **{item["chave"]: item["nome"] for item in detalhe_do_motor["fenomenos"] if item["chave"] != "estrutural"}}
        com_alerta = [passo for passo in detalhe_do_motor["historico"] if passo["alerta"]]
        assert com_alerta, detalhe_do_motor["historico"][-3:]
        for passo in com_alerta:
            celula = detalhe.locator('[data-testid="detector-historico"] tbody tr[data-competencia="' + passo["competencia"] + '"] '
                                     '[data-testid="detector-historico-alerta"]')
            nome_do_sinal = sinal_do_historico(passo, nomes_da_tela)
            assert nome_do_sinal, passo
            expect(celula).to_contain_text(NOMES[passo["alerta"]])
            expect(celula).to_contain_text(nome_do_sinal)
        page.screenshot(path=str(OUTPUT / "detector-03-detalhe-real.png"), full_page=True)

        # 5. A janela entre competências reais ("Até"): com o fim em jun/2023, a volta ainda não foi observada — "verificar registro".
        corpo_2023, enviado = do_detector(lambda: detector.get_by_test_id("detector-janela-fim").select_option("202306"),
                                          lambda o: (o.get("janela") or {}).get("fim") == "202306")
        assert corpo_2023["janela"]["fim"] == "202306" and corpo_2023["janela"]["e_o_ultimo"] is False, corpo_2023["janela"]
        expect(detector.get_by_test_id("detector-data")).to_contain_text("situação até jun/2023")
        expect(linha(RIO_RUFINO).get_by_test_id("detector-registro")).to_have_attribute("data-marca", "verificar")
        expect(linha(RIO_RUFINO)).to_contain_text("jun/2023 · 87 médicos")
        detector.get_by_test_id("detector-janela-fim").select_option("202406")
        expect(linha(RIO_RUFINO).get_by_test_id("detector-registro")).to_have_attribute("data-marca", "descontinuidade")
        detector.get_by_test_id("detector-busca").fill("")
        expect(tabela).to_have_attribute("data-linhas", "295")

        # 6. "Ajustar critérios": os limites em frases, com os campos dentro delas. Trocar um valor torna a configuração
        # exploratória, com aviso no alto; "Voltar ao padrão" fica sempre à vista (desligado enquanto os critérios são os padrões).
        expect(detector.get_by_test_id("detector-exploratorio")).to_have_count(0)
        voltar = detector.get_by_test_id("detector-voltar-ao-padrao")
        expect(voltar).to_be_visible()
        expect(voltar).to_be_disabled()
        detector.get_by_test_id("detector-parametros-botao").click()
        criterios = detector.get_by_test_id("detector-parametros")
        assert criterios.get_by_test_id("detector-criterio").evaluate_all("els => els.map(e => e.dataset.sinal)") == SINAIS[:10]
        da_queda_em_frases = criterios.locator('[data-testid="detector-criterio"][data-sinal="perda"]')
        expect(da_queda_em_frases).to_contain_text("Alerta elevado quando a queda for de pelo menos")
        expect(da_queda_em_frases).to_contain_text("mudanças anteriores foi uma queda igual ou maior.")
        assert [criterios.get_by_test_id("detector-parametro-perda-elevado_" + campo).input_value() for campo in ("minimo", "fracao", "um_em")] == ["2", "20", "100"]
        expect(criterios.get_by_test_id("detector-janela-inicio")).to_have_value("201401")
        # AJ-05: o tipo de critério de cada sinal em palavras da tela; o sinal 7 não fica só com "comparado com a base", porque o
        # moderado dele vem de um limite fixo.
        expect(criterios.locator('[data-testid="detector-criterio"][data-sinal="estrutural"] legend')).to_contain_text("· limite fixo")
        expect(criterios.locator('[data-testid="detector-criterio"][data-sinal="patamar"] legend')).to_contain_text(
            "· limite fixo no moderado; comparado com a base no elevado e no crítico")
        assert "convenção" not in criterios.inner_text().lower() and "jeito" not in criterios.inner_text().lower()
        campo = criterios.get_by_test_id("detector-parametro-estrutural-moderado")
        expect(campo).to_have_value("5")
        expect(campo).to_have_attribute("data-trocado", "false")
        campo.fill("9")
        expect(campo).to_have_attribute("data-trocado", "true")
        expect(voltar).to_be_enabled()
        corpo_exploratorio, enviado = do_detector(lambda: criterios.get_by_test_id("detector-parametros-aplicar").click(),
                                                  lambda o: bool(o.get("parametros")))
        assert enviado["parametros"] == {"estrutural": {"moderado": 9}} and corpo_exploratorio["exploratorio"] is True, enviado
        assert "CONFIGURACAO_EXPLORATORIA" in corpo_exploratorio["limitacoes"], corpo_exploratorio["limitacoes"]
        expect(detector).to_have_attribute("data-exploratorio", "true")
        expect(detector.get_by_test_id("detector-exploratorio")).to_contain_text("Configuração exploratória.")
        assert corpo_exploratorio["resumo"]["com_nivel"]["estrutural"] > corpo["resumo"]["com_nivel"]["estrutural"]
        page.screenshot(path=str(OUTPUT / "detector-04-criterios-real.png"), full_page=True)
        # A lista do padrão vem da memória da tela; as frases dos sinais dos territórios à vista são pedidas de novo (AJ-04).
        pedidos_antes = len(das_listas(pedidos))
        voltar.click()
        expect(detector.get_by_test_id("detector-exploratorio")).to_have_count(0)
        expect(detector).to_have_attribute("data-exploratorio", "false")
        expect(criterios.get_by_test_id("detector-parametro-estrutural-moderado")).to_have_value("5")
        expect(voltar).to_be_disabled()
        page.wait_for_timeout(400)
        assert len(das_listas(pedidos)) == pedidos_antes, "o padrão já calculado vem da memória da tela"
        detector.get_by_test_id("detector-parametros-botao").click()
        expect(criterios).to_have_count(0)

        # 7. AJ-03 (18/11/2026): "Como foi calculado" saiu da tela. O link "Ficha metodológica (PDF)" e o "Ver explicação completa"
        # do "Entenda" da ferramenta levam à ficha A, servida com a interface, numa nova aba; os "Entenda" dos cabeçalhos da lista,
        # escritos pela página, levam às seções dela. A régua da data, o monitoramento e as versões vão em "Exportar o método
        # (JSON)", com os números do motor. A régua usada de fato em cada nível (revisão das capturas, 14/11/2026) continua
        # conferida: de 1.000 a 2.999 médicos, o crítico junta as faixas vizinhas e é avaliado; de 3.000 para cima, nem com elas há
        # as 999 comparações.
        expect(detector.get_by_test_id("detector-metodo")).to_have_count(0)
        expect(detector.get_by_test_id("detector-metodo-botao")).to_have_count(0)
        assert "como foi calculado" not in detector.inner_text().lower()
        ficha = detector.get_by_test_id("detector-ficha")
        expect(ficha).to_contain_text("Ficha metodológica (PDF)")
        expect(ficha).to_have_attribute("target", "_blank")
        endereco = ficha.evaluate("e => e.href")
        assert endereco.endswith("/fichas/ficha-detector.pdf"), endereco
        do_pdf = page.request.get(endereco)
        assert do_pdf.status == 200 and do_pdf.body()[:5] == b"%PDF-", (do_pdf.status, do_pdf.body()[:20])
        assert do_pdf.headers.get("content-type", "").startswith("application/pdf"), do_pdf.headers
        detector.get_by_test_id("detector-entenda-ferramenta-botao").click()
        expect(detector.get_by_test_id("detector-entenda-ferramenta-caixa")).to_contain_text(corpo["entenda"]["ferramenta"]["texto"])
        completa = detector.get_by_test_id("detector-entenda-ferramenta-completa")
        expect(completa).to_have_attribute("target", "_blank")
        assert completa.evaluate("e => e.href") == endereco + "#nameddest=o-que-e"
        page.keyboard.press("Escape")
        # Os "Entenda" dos cabeçalhos: o do alerta explica "limite fixo"; o do último registro cita a primeira linha à vista.
        de_cima = detector.get_by_test_id("detector-linha").first
        do_de_cima = next(item for item in corpo["linhas"] if item["id"] == de_cima.get_attribute("data-id"))
        for chave, secao in (("sinal", "sinais"), ("alerta", "niveis"), ("por-que", "sinais"), ("ultimo", "dados")):
            detector.get_by_test_id("detector-entenda-" + chave + "-botao").click()
            caixa_da_lista = detector.get_by_test_id("detector-entenda-" + chave + "-caixa")
            expect(caixa_da_lista).to_be_visible()
            assert "convenção" not in caixa_da_lista.inner_text().lower() and "jeito" not in caixa_da_lista.inner_text().lower()
            if chave == "alerta":
                expect(caixa_da_lista).to_contain_text("“limite fixo”, um limite igual para todos os territórios")
            if chave == "ultimo":
                expect(caixa_da_lista).to_contain_text(" em " + do_de_cima["rotulo"] + ": em " + curta(do_de_cima["ultima"]["competencia"]) +
                                                       ", a base registrou ")
            assert detector.get_by_test_id("detector-entenda-" + chave + "-completa").evaluate("e => e.href") == endereco + "#nameddest=" + secao, chave
            page.keyboard.press("Escape")
            expect(caixa_da_lista).to_have_count(0)
        # As ressalvas de leitura, junto da lista: "raro" e o que o nível não é, e a distância só como contexto.
        ressalvas = detector.get_by_test_id("detector-ressalvas")
        assert ressalvas.locator("li").evaluate_all("els => els.map(e => e.dataset.chave)") == ["raro", "distancia"]
        expect(ressalvas.locator('li[data-chave="raro"]')).to_contain_text("“Raro” quer dizer incomum nesta base, não comprovadamente pior")
        expect(ressalvas.locator('li[data-chave="distancia"]')).to_contain_text("nunca vira alerta")
        # A exportação do método: a régua da data, campo a campo, o monitoramento, os níveis e as versões, como o motor mandou.
        metodo = json.loads(baixado(detector.get_by_test_id("detector-exportar-metodo")))
        assert metodo["regua_na_data"] == regua_exportada(corpo["calibracao"]), metodo["regua_na_data"]["perda"][:1]
        assert "regua_dos_estados_na_data" not in metodo   # sem estados como unidade na seleção
        assert (metodo["versao_do_metodo"], metodo["fonte"]["versao"]) == (corpo["versao"], corpo["fonte"]["versao"]), metodo["fonte"]
        assert [(item["chave"], item["umEm"], item["pede"]) for item in metodo["niveis"]] == [
            (item["chave"], item["um_em"], item["pede"]) for item in corpo["niveis"]], metodo["niveis"]
        assert [(item["chave"], item["um_em"], item["pede"]) for item in corpo["niveis"]] == [
            ("moderado", 20, 19), ("elevado", 100, 99), ("critico", 1000, 999)], corpo["niveis"]
        assert metodo["notas"] == corpo["notas"], metodo["notas"]
        assert any(nota.startswith("Um nível por território: o maior entre os seus sinais, sem soma nem índice.") for nota in metodo["notas"]), metodo["notas"]
        do_monitoramento = corpo["calibracao"]["monitoramento"]
        assert do_monitoramento["avaliadas"] > 0 and metodo["regua_na_data"]["monitoramento"]["raras"] == do_monitoramento["raras"], do_monitoramento
        portes = [item["porte"] for item in metodo["regua_na_data"]["perda"]]
        assert portes == ["1 a 3", "4 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 a 999", "1.000 a 2.999", "3.000 a 9.999",
                          "10.000 ou mais"], portes
        for celula in corpo["calibracao"]["perda"]:
            for nivel in ("moderado", "elevado", "critico"):
                do_nivel = celula[nivel]
                if not do_nivel["avaliado"]:
                    assert do_nivel["origem"] == "vizinhas" and do_nivel["queda_pct"] is None, (celula["porte"], nivel, do_nivel)
                    continue
                assert do_nivel["origem"] in ("porte", "vizinhas"), (celula["porte"], nivel, do_nivel)   # em jun/2024, nunca todas as faixas
                if do_nivel["origem"] == "porte":
                    assert do_nivel["comparacoes"] == celula["comparacoes"], (celula["porte"], nivel, do_nivel)
        do_critico = {celula["porte"]: (celula["critico"]["avaliado"], celula["critico"]["origem"]) for celula in corpo["calibracao"]["perda"]}
        assert [porte for porte, (avaliado, _) in do_critico.items() if not avaliado] == ["3.000 a 9.999", "10.000 ou mais"], do_critico
        assert do_critico["1.000 a 2.999"] == (True, "vizinhas") and do_critico["300 a 999"] == (True, "porte"), do_critico
        # De 1 a 3 médicos, o corte do crítico é de 100%: nenhuma queda chega lá. De 10.000 para cima, o elevado vem das vizinhas.
        assert corpo["calibracao"]["perda"][0]["critico"]["queda_pct"] >= 100, corpo["calibracao"]["perda"][0]
        assert corpo["calibracao"]["perda"][9]["elevado"]["origem"] == "vizinhas", corpo["calibracao"]["perda"][9]["elevado"]
        maiores = corpo["calibracao"]["patamar"][-1]
        assert (maiores["porte"], maiores["critico"]["avaliado"], maiores["critico"]["origem"]) == ("10.000 ou mais", False, "vizinhas"), maiores
        assert metodo["regua_na_data"]["patamar"][-1]["niveis"]["critico"]["cortePct"] is None
        assert metodo["regua_na_data"]["patamar"][-1]["niveis"]["critico"]["comparacoes"] == maiores["critico"]["comparacoes"] < 999, maiores

        # 8. "Alterar a seleção" volta à Seleção de Territórios; com o Paraná como unidade, a linha dele usa a régua própria dos
        # estados (a base dos estados, pequena): os níveis que ela não sustenta ficam "sem comparações suficientes", com os números,
        # no detalhe e na exportação do método; junto da lista, a ressalva diz isso.
        detector.get_by_test_id("detector-alterar-selecao").click()
        expect(area).to_have_attribute("data-ferramenta", "")
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true")
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
            linha_do_estado(territorios, PR).get_by_test_id("analise-grupo-so-estado").click()
        corpo_misto, enviado = do_detector(lambda: botao.click(), lambda o: o.get("estados_unidade") == [PR])
        assert enviado["base"]["municipios"]["estados"] == [SC] and len(corpo_misto["linhas"]) == 296, enviado
        assert corpo_misto["calibracao_dos_estados"]["monitoramento"]["avaliadas"] == 27, corpo_misto["calibracao_dos_estados"]["monitoramento"]
        detector.get_by_test_id("detector-busca").fill("paraná")
        parana = linha("uf:" + PR)
        do_parana = next(item for item in corpo_misto["linhas"] if item["id"] == "uf:" + PR)
        expect(parana).to_have_attribute("data-tipo", "estado")
        expect(parana).to_contain_text("estado como unidade · régua própria")
        expect(parana).to_have_attribute("data-alerta", estado_do_alerta(do_parana))
        parana.get_by_test_id("detector-abrir").click()
        detalhe_do_parana, _ = detalhe_pedido("uf:" + PR, lambda o: o.get("estados_unidade") == [PR])
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_have_attribute("data-id", "uf:" + PR, timeout=120000)
        queda_do_parana = next(item for item in detalhe_do_parana["fenomenos"] if item["chave"] == "perda")
        assert queda_do_parana["sem_comparacoes"]["niveis"] == ["critico"] and queda_do_parana["sem_comparacoes"]["pede"] == 999, queda_do_parana
        expect(sinal_da_tela(detalhe, "perda").get_by_test_id("detector-fenomeno-sem-comparacoes")).to_have_text(queda_do_parana["sem_comparacoes"]["texto"])
        expect(sinal_da_tela(detalhe, "perda").get_by_test_id("detector-fenomeno-sem-comparacoes")).to_contain_text("Sem comparações suficientes para o crítico: há ")
        # O estado como unidade não tem um ponto único: a distância não se aplica.
        expect(sinal_da_tela(detalhe, "contexto")).to_have_attribute("data-estado", "contexto")
        expect(sinal_da_tela(detalhe, "contexto").get_by_test_id("detector-fenomeno-situacao")).to_contain_text("Não se aplica")
        ressalva = detector.locator('[data-testid="detector-ressalvas"] li[data-chave="grupos"]')
        expect(ressalva).to_have_text("O estado como unidade tem régua própria, com a base dos estados: é uma base pequena, e os níveis mais "
                                      "graves podem ficar sem comparações suficientes.")
        # A régua usada de fato, na exportação: nos estados de 10.000 médicos ou mais, o crítico tem as comparações da faixa com as
        # vizinhas (o número que o detalhe do estado diz: "há N, e ele pede 999"), e não só as do próprio porte.
        metodo_misto = json.loads(baixado(detector.get_by_test_id("detector-exportar-metodo")))
        assert metodo_misto["regua_dos_estados_na_data"] == regua_exportada(corpo_misto["calibracao_dos_estados"]), metodo_misto["regua_dos_estados_na_data"]
        assert metodo_misto["regua_na_data"] == regua_exportada(corpo_misto["calibracao"])
        dos_maiores = next(celula for celula in corpo_misto["calibracao_dos_estados"]["perda"] if celula["porte"] == "10.000 ou mais")
        assert dos_maiores["critico"]["origem"] == "vizinhas" and dos_maiores["critico"]["comparacoes"] > dos_maiores["comparacoes"], dos_maiores
        assert dos_maiores["critico"]["avaliado"] is False and dos_maiores["critico"]["comparacoes"] < 999, dos_maiores
        exportado = next(item for item in metodo_misto["regua_dos_estados_na_data"]["perda"] if item["porte"] == "10.000 ou mais")
        assert exportado["niveis"]["critico"] == {"umEm": 1000, "pede": 999, "cortePct": None, "origem": "vizinhas",
                                                  "comparacoes": dos_maiores["critico"]["comparacoes"], "corteAtePct": None}, exportado
        assert any(celula["critico"]["avaliado"] is False for celula in corpo_misto["calibracao_dos_estados"]["perda"]), "sem comparações suficientes no crítico"
        page.screenshot(path=str(OUTPUT / "detector-05-estado-real.png"), full_page=True)
        parana.get_by_test_id("detector-abrir").click()  # fecha os detalhes
        detector.get_by_test_id("detector-busca").fill("")

        # 9. As visões Mapa e Gráfico. Com a população do Ministério da Saúde (13/11/2026), a base inteira é um trecho só de
        # população comparável, lido dela mesma: no último registro (jun/2024), a janela de jun/2022 a jun/2024 vale.
        do_motor = corpo_misto["comparacao"]
        assert (do_motor["estado"], do_motor["de"], do_motor["ate"]) == ("comparavel", "202206", "202406"), do_motor
        assert do_motor["trechos"] == [[2014, 2024]] and do_motor["motivo"] is None, do_motor
        municipais = [item for item in corpo_misto["linhas"] if item["tipo"] == "municipio"]
        assert not any("comparacao_nao_habilitada" in (item["disponibilidade"]["estado"], item["posicao"]["estado"]) for item in municipais)
        com_ponto = set(corpo_misto["coordenadas"])

        def no_mapa(nivel, sinal=None):
            return sum(1 for item in municipais if item["id"] in com_ponto and (
                item["alerta"]["nivel"] == nivel if sinal is None else any(d["sinal"] == sinal and d["nivel"] == nivel for d in item["alerta"]["sinais"])))
        # O mapa: cada município à vista com ponto, pintado pelo nível do alerta, com a legenda escrita e as coordenadas do motor.
        detector.get_by_test_id("detector-vista-mapa").click()
        visual = detector.get_by_test_id("detector-visual")
        expect(visual).to_have_attribute("data-vista", "mapa")
        mapa = detector.get_by_test_id("detector-mapa")
        for nivel in NOMES:
            expect(mapa).to_have_attribute("data-" + nivel, str(no_mapa(nivel)))
            expect(mapa.locator('[data-testid="analise-mapa-ponto"][data-pintura="' + nivel + '"]')).to_have_count(no_mapa(nivel))
            expect(mapa.locator('[data-testid="detector-legenda-niveis"] [data-nivel="' + nivel + '"]')).to_have_text(
                NOMES[nivel] + ": " + str(no_mapa(nivel)))
        assert no_mapa("critico") >= 1 and no_mapa("moderado") > no_mapa("elevado") > 0, [no_mapa(nivel) for nivel in NOMES]
        expect(mapa.get_by_test_id("analise-mapa-nome-grupo")).to_have_text("SC")
        # Muda de propósito na revisão final do V23 (15/11/2026, opção (a) do item 4 da Pausa 2): em Santa Catarina, a base traz a
        # coordenada de dois municípios (Pescaria Brava e Balneário Rincão) fora do intervalo válido. Eles ficavam fora do mapa, com
        # a frase "Fora do mapa: 2 municípios à vista (…)"; agora ficam com a sede municipal da camada oficial do IBGE, como nas
        # análises: ninguém fica de fora, e a legenda diz quais pontos vieram da camada. Quem fica fora do mapa por não ter
        # coordenada continua conferido em `ui_planilha_ficticia.py` (a comuna sem coordenada) e nos testes do modelo.
        fora = [item for item in municipais if item["id"] not in com_ponto]
        assert fora == [] and corpo_misto["sem_coordenada"] == [], [item["rotulo"] for item in fora]
        assert corpo_misto["complemento_geografico"]["territorios_complementados"] == ["code:421265", "code:422000"], corpo_misto["complemento_geografico"]
        expect(mapa.get_by_test_id("detector-mapa-fora")).to_have_count(0)
        oficiais = mapa.get_by_test_id("detector-mapa-coordenadas-oficiais")
        expect(oficiais).to_contain_text("Em 2 municípios à vista, o ponto é o da sede municipal, da camada oficial de coordenadas do IBGE, "
                                         "porque a base traz a coordenada deles fora do intervalo válido: ")
        for rotulo in ("PESCARIA BRAVA (SC)", "BALNEARIO RINCAO (SC)"):
            expect(oficiais).to_contain_text(rotulo)
        expect(mapa.locator('[data-testid="analise-mapa-ponto"]')).to_have_count(len(municipais))   # um ponto por município da lista
        # As divisas (etapa 7 do comando V23; muda de propósito: antes, "A base não tem as divisas"): na base do Brasil, o mapa tem
        # a malha municipal do IBGE, pedida só quando ele abre. As divisas dos estados ficam sempre à vista; com os municípios de um
        # estado só à vista (Santa Catarina), as dos municípios também aparecem; a área de cada município com nível leva a cor
        # dele.
        expect(mapa).to_have_attribute("data-divisas", "carregadas", timeout=60000)
        divisas = mapa.get_by_test_id("analise-mapa-divisas")
        expect(divisas).to_have_attribute("data-bordas", "true")
        expect(divisas.get_by_test_id("analise-mapa-divisas-dos-estados")).to_have_count(1)
        com_nivel = sum(1 for item in municipais if item["alerta"]["nivel"])
        expect(divisas).to_have_attribute("data-areas-com-cor", str(com_nivel))
        expect(divisas.get_by_test_id("analise-mapa-area")).to_have_count(com_nivel)
        for nivel in NOMES:
            expect(divisas.locator('[data-testid="analise-mapa-area"][data-pintura="' + nivel + '"]')).to_have_count(
                sum(1 for item in municipais if item["alerta"]["nivel"] == nivel))
        expect(divisas.get_by_test_id("analise-mapa-areas-sem-cor")).to_have_count(1)
        expect(mapa.get_by_test_id("detector-mapa-aproximar")).to_have_count(0)   # um estado só à vista: não há em que aproximar
        expect(mapa).to_have_attribute("data-aproximado", "")
        expect(mapa.get_by_test_id("detector-mapa-divisas")).to_contain_text(
            "As divisas são as da malha municipal do IBGE: as dos estados ficam sempre à vista")
        expect(mapa.get_by_test_id("detector-mapa-divisas")).to_contain_text("as divisas dos municípios estão à vista")
        expect(mapa).not_to_contain_text("A base não tem as divisas")
        expect(mapa).to_contain_text("o estado como unidade não tem ponto")
        # AJ-04: a dica do ponto nomeia o sinal pintado (o principal do alerta), com o nível, e diz quantos outros sinais com nível
        # o território tem; a cor e o tamanho continuam pelo maior nível.
        nomes_dos_sinais = {item["chave"]: item["nome"] for item in detalhe_do_abelardo["fenomenos"]}

        def dica(item, sinal=None):
            dado = next(d for d in item["alerta"]["sinais"] if d["sinal"] == (sinal or item["alerta"]["sinal"]))
            outros = len(item["alerta"]["sinais"]) - 1
            return nomes_dos_sinais[dado["sinal"]] + " · " + dado["nivel"] + ("; mais " + str(outros) + (" sinal" if outros == 1 else " sinais") +
                                                                               " com nível" if outros else "")
        ponto_do_abelardo = mapa.locator('[data-testid="analise-mapa-ponto"][data-id="' + ABELARDO_LUZ + '"]')
        expect(ponto_do_abelardo).to_have_attribute("data-pintura", "elevado")
        expect(ponto_do_abelardo.locator("title")).to_have_text(do_abelardo["rotulo"] + " · " + dica(do_abelardo))
        assert dica(do_abelardo) == "Menos médicos por habitante · elevado; mais 3 sinais com nível", dica(do_abelardo)
        page.screenshot(path=str(OUTPUT / "detector-06-mapa-real.png"), full_page=False)
        # Com o filtro "Sinal", o mapa pinta o nível daquele sinal, e a lista fica só com as linhas em que ele tem nível.
        detector.get_by_test_id("detector-filtro-sinal").select_option("patamar")
        com_patamar = [item for item in corpo_misto["linhas"] if com_o_sinal(item, "patamar")]
        assert com_patamar and sum(no_mapa(nivel, "patamar") for nivel in NOMES) == len(com_patamar), len(com_patamar)
        expect(mapa).to_have_attribute("data-sinal", "patamar")
        expect(mapa).to_have_attribute("data-fundo", "0")
        # Com o filtro, a frase fala só de quem está à vista: sem ninguém de fora entre as linhas filtradas, ela não aparece.
        expect(mapa.get_by_test_id("detector-mapa-fora")).to_have_count(1 if any(com_o_sinal(item, "patamar") for item in fora) else 0)
        for nivel in NOMES:
            expect(mapa).to_have_attribute("data-" + nivel, str(no_mapa(nivel, "patamar")))
        expect(tabela).to_have_attribute("data-linhas", str(len(com_patamar)))
        # Com o filtro, a dica nomeia aquele sinal, com o nível dele, e os outros sinais com nível do território continuam contados.
        expect(ponto_do_abelardo).to_have_attribute("data-pintura", "moderado")
        expect(ponto_do_abelardo.locator("title")).to_have_text(do_abelardo["rotulo"] + " · " + dica(do_abelardo, "patamar"))
        assert dica(do_abelardo, "patamar") == "Abaixo do que já teve · moderado; mais 3 sinais com nível", dica(do_abelardo, "patamar")
        detector.get_by_test_id("detector-filtro-sinal").select_option("todos")
        # O gráfico: uma bolha por território com distância a mostrar (a distância até o mais próximo que atende ao critério e a
        # taxa por habitante), pintada pelo nível. A distância é só contexto.
        detector.get_by_test_id("detector-vista-grafico").click()
        expect(visual).to_have_attribute("data-vista", "grafico")
        com_distancia = [item for item in corpo_misto["linhas"] if item["contexto"]["estado"] == "contexto" and item["disponibilidade"]["taxa"] is not None]
        assert len(com_distancia) > 50, len(com_distancia)
        bolhas = detector.get_by_test_id("detector-bolhas")
        expect(bolhas).to_have_attribute("data-itens", str(len(com_distancia)))
        expect(bolhas).to_have_attribute("data-critico", str(sum(1 for item in com_distancia if item["alerta"]["nivel"] == "critico")))
        expect(bolhas.locator('[data-testid="analise-bolha"]').first).to_be_visible()
        expect(bolhas).to_contain_text("município mais próximo com 2,36 médicos por 1.000 habitantes ou mais")
        expect(bolhas).to_contain_text("nunca vira alerta")
        # AJ-04: na dica da bolha, também o sinal principal, com o nível, e quantos outros sinais com nível o território tem.
        com_varios = next(item for item in com_distancia if len(item["alerta"]["sinais"]) > 1 and item["alerta"]["sinal"] not in ("estrutural", "ausencia"))
        bolhas.locator('[data-testid="analise-bolha"][data-id="' + com_varios["id"] + '"]').focus()
        dica_da_bolha = detector.get_by_test_id("analise-dica")
        expect(dica_da_bolha).to_contain_text(com_varios["rotulo"])
        expect(dica_da_bolha).to_contain_text(dica(com_varios))
        page.screenshot(path=str(OUTPUT / "detector-07-grafico-real.png"), full_page=False)
        detector.get_by_test_id("detector-vista-lista").click()
        expect(detector.get_by_test_id("detector-visual")).to_have_count(0)

        # 10. Com a janela até jun/2021 (de jun/2019 a jun/2021, com população comparável), os sinais comparados em 2 anos têm
        # nível pela raridade na base. Os detalhes trazem a série da taxa com a da referência e os textos do motor.
        corpo_2021, enviado = do_detector(lambda: detector.get_by_test_id("detector-janela-fim").select_option("202106"),
                                          lambda o: (o.get("janela") or {}).get("fim") == "202106")
        assert (corpo_2021["comparacao"]["estado"], corpo_2021["comparacao"]["de"], corpo_2021["comparacao"]["ate"]) == ("comparavel", "201906", "202106")
        expect(detector.get_by_test_id("detector-comparacao")).to_contain_text("usam a variação de jun/2019 a jun/2021")
        com_queda = [item for item in corpo_2021["linhas"] if com_o_sinal(item, "disponibilidade")]
        assert com_queda and corpo_2021["resumo"]["com_nivel"]["disponibilidade"] == len(com_queda), "há quedas raras da taxa por habitante em Santa Catarina"
        assert all(item["disponibilidade"]["classe"] in NOMES for item in com_queda)
        detector.get_by_test_id("detector-filtro-sinal").select_option("disponibilidade")
        expect(tabela).to_have_attribute("data-linhas", str(len(com_queda)))
        alvo = com_queda[0]
        da_queda = linha(alvo["id"])
        da_queda.get_by_test_id("detector-abrir").click()
        detalhe_2021, enviado = detalhe_pedido(alvo["id"], lambda o: (o.get("janela") or {}).get("fim") == "202106")
        assert enviado["janela"] == {"fim": "202106"} or enviado["janela"].get("fim") == "202106", enviado
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_have_attribute("data-id", alvo["id"], timeout=120000)
        serie_da_taxa = detalhe.get_by_test_id("detector-serie-da-taxa")
        expect(serie_da_taxa).to_have_attribute("data-referencias", "1")
        expect(serie_da_taxa.locator('[data-testid="analise-serie-referencia"]')).to_have_count(1)
        expect(serie_da_taxa).to_contain_text(detalhe_2021["comparativo"]["referencia"]["rotulo"])
        # Os trechos de população comparável vêm do motor, lidos da própria base: com a população nova, um trecho só.
        assert detalhe_2021["comparativo"]["trechos"] == [[2014, 2024]], detalhe_2021["comparativo"]["trechos"]
        expect(serie_da_taxa).to_contain_text("a variação entre datas só é lida de 2014 a 2024, quando a população da base é comparável")
        # As datas do eixo são escritas como nos outros gráficos do Detector ("jun/2021", e não "06/2021"; revisão das capturas de
        # 15/11/2026). A última data do eixo aparece sempre.
        expect(serie_da_taxa.locator("svg").first).to_contain_text("jun/2021")
        expect(serie_da_taxa.locator("svg").first).not_to_contain_text("06/2021")
        oito = next(item for item in detalhe_2021["fenomenos"] if item["chave"] == "disponibilidade")
        assert oito["numero"] == "8" and oito["nivel"] == alvo["disponibilidade"]["classe"] and oito["criterio_do_nivel"] == "comparado com a base", oito
        assert "Comparado com a base: entre " in oito["habitual"], oito["habitual"]
        for chave in ("disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"):
            do_fenomeno = next(item for item in detalhe_2021["fenomenos"] if item["chave"] == chave)
            item = sinal_da_tela(detalhe, chave)
            expect(item.get_by_test_id("detector-fenomeno-situacao")).to_contain_text(do_fenomeno["situacao"])
            item.get_by_test_id("detector-fenomeno-completa").click()
            expect(item.get_by_test_id("detector-campo-observado").locator("dd")).to_have_text(do_fenomeno["observado"])
            expect(item.get_by_test_id("detector-campo-naoSignifica").locator("dd")).to_have_text(do_fenomeno["nao_significa"])
        # Os efeitos da mesma queda contam como um evento, e a tela diz isso.
        if detalhe_2021["linha"]["alerta"]["mesma_queda"]:
            expect(detalhe.get_by_test_id("detector-mesma-queda")).to_contain_text("vêm da mesma queda: contam como um evento.")
        page.screenshot(path=str(OUTPUT / "detector-08-comparados-2021-real.png"), full_page=False)
        da_queda.get_by_test_id("detector-abrir").click()  # fecha os detalhes
        detector.get_by_test_id("detector-filtro-sinal").select_option("todos")

        # 11. "Simular recuperação": de volta ao último registro, ABELARDO LUZ (SC) está abaixo do que já teve; o botão abre o
        # Simulador de Cenários só com ele, com a meta hipotética (e editável) de voltar ao patamar, sem mudar a seleção
        # principal. Quem está acima do patamar não tem o botão. Desde o comando V23 (Proposta V3, seção C.7; muda de propósito
        # este trecho, que conferia a etapa 3 das quatro etapas), o Simulador abre no modo simples, numa tela só, com "Chegar a
        # uma meta" já escolhido.
        principal = area.get_by_test_id("analise-aba-territorios-resumo").inner_text()
        detector.get_by_test_id("detector-janela-fim").select_option("202406")
        expect(detector.get_by_test_id("detector-comparacao")).to_contain_text("usam a variação de jun/2022 a jun/2024")
        do_abelardo = next(item for item in corpo_misto["linhas"] if item["id"] == ABELARDO_LUZ)
        assert com_o_sinal(do_abelardo, "patamar") and do_abelardo["patamar"]["diferenca_pct"] < 0, do_abelardo["patamar"]
        assert "patamar" in do_abelardo["alerta"]["mesma_queda"], do_abelardo["alerta"]
        acima = next(item for item in municipais if item["patamar"]["patamar"] is not None and (item["patamar"]["diferenca_pct"] or 0) > 0)
        detector.get_by_test_id("detector-busca").fill(acima["rotulo"].split(" (")[0])
        linha(acima["id"]).get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", acima["id"])
        expect(detector.get_by_test_id("detector-abrir-no-simulador")).to_be_visible()
        expect(detector.get_by_test_id("detector-simular-recuperacao")).to_have_count(0)
        detector.get_by_test_id("detector-busca").fill("abelardo")
        linha(ABELARDO_LUZ).get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", ABELARDO_LUZ)
        expect(detector.get_by_test_id("detector-mesma-queda")).to_contain_text("vêm da mesma queda: contam como um evento.")
        expect(detector.get_by_test_id("detector-recuperacao-apoio")).to_contain_text("meta hipotética")
        expect(detector.get_by_test_id("detector-recuperacao-apoio")).to_contain_text("não uma previsão")
        # A meta é um número inteiro, o patamar arredondado para cima, e a frase diz de onde ela vem (revisão das capturas,
        # 14/11/2026): o patamar de Abelardo Luz é de 78,25 médicos, e a meta, 79.
        patamar = do_abelardo["patamar"]["patamar"]
        meta = math.ceil(patamar - 1e-9)
        assert (patamar, meta) == (78.25, 79), patamar
        expect(detector.get_by_test_id("detector-recuperacao-apoio")).to_have_attribute("data-meta", str(meta))
        expect(detector.get_by_test_id("detector-recuperacao-apoio")).to_contain_text(
            "voltar ao patamar, 79 médicos (o patamar é de 78,25, a maior média de dois anos seguidos antes dos registros mais recentes, "
            "arredondado para cima).")
        pedidos_do_simulador = []
        page.on("request", lambda request: pedidos_do_simulador.append(request) if request.url.endswith("/api/simulador") else None)
        detector.get_by_test_id("detector-simular-recuperacao").click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        simulador = area.get_by_test_id("simulador")
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simulador.get_by_test_id("simulador-simples")).to_have_attribute("data-teste", "meta")
        expect(simulador.get_by_test_id("simulador-territorio")).to_have_value(ABELARDO_LUZ)
        aviso = simulador.get_by_test_id("simulador-do-detector")
        expect(aviso).to_have_attribute("data-recuperacao", "true")
        expect(aviso).to_contain_text("Aberto pelo Detector de Sinais: ABELARDO LUZ (SC), avaliado em jun/2024")
        expect(aviso).to_contain_text("Sinais com nível lá: ")
        expect(aviso).to_contain_text("Abaixo do que já teve (")
        expect(aviso).to_contain_text("meta hipotética que você pode trocar")
        expect(simulador.get_by_test_id("simulador-teste-meta")).to_be_checked()
        # O campo mostra a meta em uso (79); a frase ao lado diz o patamar com a precisão do Detector, que é o que vai ao motor.
        expect(simulador.get_by_test_id("simulador-teste-meta-valor")).to_have_value(str(meta))
        expect(simulador.get_by_test_id("simulador-teste-meta-origem")).to_have_text(
            "A meta veio do Detector de Sinais: o patamar anterior, de 78,25 médicos (a maior média de dois anos seguidos), arredondado "
            "para cima. É uma hipótese que você pode trocar.")
        page.wait_for_timeout(400)
        assert not pedidos_do_simulador, "nada é calculado antes de \"Calcular\""
        with page.expect_response(lambda r: r.url.endswith("/api/simulador") and r.request.method == "POST", timeout=180000) as evento:
            simulador.get_by_test_id("simulador-calcular").click()
        assert evento.value.status == 200, evento.value.text()[:2000]
        pedido, cenarios = options_of(evento.value.request), evento.value.json()["territorios"]
        assert pedido["base"] == {"municipios": {"todos": False, "estados": [], "ids": [ABELARDO_LUZ]}} and "estados_unidade" not in pedido, pedido
        assert pedido["cenarios"][0]["planejamento"] == {"meta": {"tipo": "patamar", "valor": patamar}, "em": "202506"}, pedido
        assert [item["id"] for item in cenarios] == [ABELARDO_LUZ], cenarios
        planejado = cenarios[0]["cenarios"][0]["planejamento"]
        assert planejado["estado"] == "calculado" and planejado["por_evento"] >= 1 and planejado["resultado"] >= planejado["meta"]["valor"], planejado
        assert planejado["texto"].startswith("Meta hipotética: voltar ao patamar de 79 médicos em jun/2026 (patamar de 78,25, média de 4 "
                                             "registros, arredondado para cima). ") and planejado["texto"].endswith("não um plano."), planejado["texto"]
        assert (planejado["meta"]["valor"], planejado["meta"]["patamar"], planejado["meta"]["registros"]) == (meta, patamar, 4), planejado["meta"]
        # O resultado exibido não fica abaixo da meta: "teria 79 médicos" (antes, com a meta de 78,25, o texto dizia 78).
        assert " teria " + str(max(meta, round(planejado["resultado"]))) + " médicos em jun/2026." in planejado["texto"], planejado["texto"]
        for proibida in ("recomenda", "é preciso", "deveria", "necessário prover"):
            assert proibida not in planejado["texto"].lower(), proibida
        resultado = simulador.get_by_test_id("simulador-resultado")
        expect(resultado).to_have_attribute("data-estado", "calculado", timeout=180000)
        expect(resultado.get_by_test_id("simulador-planejamento")).to_have_attribute("data-estado", "calculado")
        expect(resultado.get_by_test_id("simulador-planejamento")).to_have_attribute("data-por-evento", str(planejado["por_evento"]))
        expect(resultado.get_by_test_id("simulador-planejamento-texto")).to_have_text(planejado["texto"])
        # O gráfico mostra a meta (uma linha na altura dela), o caminho do cenário com o acréscimo e a marca na data dele.
        do_grafico = resultado.get_by_test_id("simulador-plano-no-grafico")
        expect(do_grafico).to_have_attribute("data-meta", str(meta))
        expect(do_grafico).to_have_attribute("data-estado", "calculado")
        expect(do_grafico.get_by_test_id("simulador-meta-linha")).to_have_count(1)
        expect(do_grafico.get_by_test_id("simulador-plano-curva")).to_have_count(1)
        expect(do_grafico.get_by_test_id("simulador-plano-evento")).to_have_count(planejado["eventos"])
        assert [ponto["data"] for ponto in planejado["trajetoria"]][-1] == "202606" and planejado["trajetoria"][-1]["total"] >= meta, planejado["trajetoria"]
        expect(resultado.get_by_test_id("simulador-meta-legenda")).to_contain_text(
            "meta hipotética de 79 médicos; linha contínua: o cenário com o acréscimo que alcança a meta (▼ na data do acréscimo)")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(principal)   # a seleção principal não mudou
        page.screenshot(path=str(OUTPUT / "detector-09-simular-recuperacao-real.png"), full_page=True)

        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas, falhas
        context.close()

        # 12. Numa tela de celular, com toque: o "Entenda" abre pelo toque, cabe na largura e fecha com um toque fora; a lista
        # vira cartões, um por território (AJ-04: o nome e o último registro no alto; em cada sinal, o nome dele e o alerta numa
        # linha, e o porquê abaixo) e nada passa da largura.
        celular = browser.new_context(viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        offline(celular)
        tela = celular.new_page()
        falhas_no_celular = []
        tela.on("pageerror", lambda error: falhas_no_celular.append(str(error)))
        tela.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)
        tela.goto(URL)
        tela.get_by_role("button", name="Li e concordo", exact=True).click()
        area = tela.get_by_test_id("area-de-analise")
        chat = tela.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").tap()
        area.get_by_test_id("analise-fonte-brasil").tap()
        territorios = area.get_by_test_id("analise-territorios")
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
        caixa_do_estado = linha_do_estado(territorios, SC).get_by_test_id("analise-grupo-todos")
        caixa_do_estado.scroll_into_view_if_needed()
        with tela.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
            caixa_do_estado.focus()
            caixa_do_estado.press("Space")
        botao = area.get_by_test_id("analise-ferramenta-detector")
        botao.scroll_into_view_if_needed()
        corpo_no_celular, _ = do_detector(lambda: botao.tap(), da_pagina=tela)
        detector = area.get_by_test_id("detector")
        expect(detector).to_have_attribute("data-estado", "pronto")
        assert corpo_no_celular["resumo"]["niveis"] == corpo["resumo"]["niveis"]
        # O "Entenda" da ferramenta, pelo toque.
        entenda = detector.get_by_test_id("detector-entenda-ferramenta-botao")
        entenda.scroll_into_view_if_needed()
        entenda.tap()
        caixa = detector.get_by_test_id("detector-entenda-ferramenta-caixa")
        expect(caixa).to_be_visible()
        expect(caixa).to_contain_text("Exemplo:")
        medida = caixa.bounding_box()
        assert medida["x"] >= 0 and medida["x"] + medida["width"] <= 390 + 0.5 and medida["width"] >= 300, medida
        tela.screenshot(path=str(OUTPUT / "detector-10-celular-entenda-real.png"), full_page=False)
        detector.get_by_test_id("detector-titulo").tap()   # um toque fora fecha
        expect(caixa).to_have_count(0)
        # A lista em cartões e nada passando da largura.
        primeira = detector.get_by_test_id("detector-linha").first
        primeira.scroll_into_view_if_needed()
        caixas = primeira.evaluate("""e => Object.fromEntries([...e.querySelector('tr').children].map(c => [c.dataset.rotulo, c.getBoundingClientRect()])
          .map(([rotulo, r]) => [rotulo, [Math.round(r.left), Math.round(r.top), Math.round(r.right)]]))""")
        assert caixas["Último registro"][1] > caixas["Território"][1] and caixas["Sinal"][1] > caixas["Último registro"][1], caixas
        assert caixas["Por quê"][1] > caixas["Sinal"][1], caixas
        assert abs(caixas["Alerta"][1] - caixas["Sinal"][1]) <= 4 and caixas["Alerta"][0] >= caixas["Sinal"][2] - 1, caixas
        assert all(0 <= esquerda and direita <= 390 for esquerda, _, direita in caixas.values()), caixas
        assert tela.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1, "a página passa da largura da janela"
        primeira.get_by_test_id("detector-abrir").tap()
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_be_visible(timeout=180000)
        do_sinal = detalhe.locator('[data-testid="detector-fenomeno"][data-chave="estrutural"]')
        do_sinal.get_by_test_id("detector-entenda-botao").scroll_into_view_if_needed()
        do_sinal.get_by_test_id("detector-entenda-botao").tap()
        expect(do_sinal.get_by_test_id("detector-entenda-caixa")).to_be_visible()
        medida = do_sinal.get_by_test_id("detector-entenda-caixa").bounding_box()
        assert medida["x"] >= 0 and medida["x"] + medida["width"] <= 390 + 0.5, medida
        do_sinal.get_by_test_id("detector-entenda-botao").tap()   # o segundo toque fecha
        expect(do_sinal.get_by_test_id("detector-entenda-caixa")).to_have_count(0)
        assert tela.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth") <= 1, "o detalhe passa da largura da janela"
        # A série do território é desenhada na largura que tem na tela (revisão das capturas de 15/11/2026): o desenho não é
        # encolhido, o texto dos eixos fica com 12 px de verdade, e o gráfico é mais alto que no computador (220 em vez de 170).
        serie = detalhe.get_by_test_id("detector-serie")
        serie.scroll_into_view_if_needed()
        expect(serie).not_to_have_attribute("data-largura", "640")   # a largura medida, e não a do primeiro desenho
        medidas = serie.evaluate("""e => { const svg = e.querySelector("svg"), texto = svg.querySelector("text");
          return { largura: Number(e.dataset.largura), caixa: svg.viewBox.baseVal.width, altura: svg.viewBox.baseVal.height,
                   naTela: svg.getBoundingClientRect().width, fonte: parseFloat(getComputedStyle(texto).fontSize) }; }""")
        assert 280 <= medidas["largura"] == medidas["caixa"] <= 390 and medidas["altura"] == 220, medidas
        assert abs(medidas["naTela"] - medidas["caixa"]) <= 1 and medidas["fonte"] == 12, medidas
        tela.screenshot(path=str(OUTPUT / "detector-11-celular-detalhe-real.png"), full_page=False)
        # O mapa no celular (etapa 7 do comando V23): desenhado na largura da tela, mais alto (380 em vez de 440 numa tela larga, que
        # antes encolhia para caber), com as divisas da malha; o desenho não passa da largura da janela.
        vista_mapa = detector.get_by_test_id("detector-vista-mapa")
        vista_mapa.scroll_into_view_if_needed()
        vista_mapa.tap()
        mapa_no_celular = detector.get_by_test_id("detector-mapa")
        expect(mapa_no_celular).to_have_attribute("data-divisas", "carregadas", timeout=60000)
        expect(mapa_no_celular).not_to_have_attribute("data-largura", "760")   # a largura medida, e não a do primeiro desenho
        medidas = mapa_no_celular.evaluate("""e => { const svg = e.querySelector('[data-testid="analise-mapa-conjuntos"] svg'), caixa = svg.getBoundingClientRect();
          return { largura: Number(e.dataset.largura), caixa: svg.viewBox.baseVal.width, altura: svg.viewBox.baseVal.height,
                   naTela: caixa.width, direita: caixa.right, esquerda: caixa.left }; }""")
        assert 280 <= medidas["largura"] == medidas["caixa"] <= 390 and medidas["altura"] == 380, medidas
        assert abs(medidas["naTela"] - medidas["caixa"]) <= 1 and medidas["esquerda"] >= 0 and medidas["direita"] <= 390 + 0.5, medidas
        expect(mapa_no_celular.get_by_test_id("analise-mapa-divisas-dos-estados")).to_have_count(1)
        tela.screenshot(path=str(OUTPUT / "detector-12-celular-mapa-real.png"), full_page=False)
        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas_no_celular, falhas_no_celular
        browser.close()
    print("DETECTOR PASS: ferramenta na navegação sem pedido sem seleção; lista de cinco colunas de Santa Catarina (295, 50 por página), "
          "resumo dos níveis clicável, filtros Até, Nível, Sinal e Buscar e ordem pelos cabeçalhos; ABELARDO LUZ com um sinal por linha; "
          "RIO RUFINO com o pico que volta "
          "(série, 12 sinais em quatro grupos mais Juntos, Entenda por mouse e teclado, explicação completa e histórico); janela até "
          "jun/2023 (verificar registro); critérios em frases, configuração exploratória e Voltar ao padrão pela memória; a ficha "
          "metodológica em PDF e a régua por porte na exportação do método; o Paraná como unidade com a régua dos estados; mapa e "
          "gráfico pelos níveis, com a dica do sinal; sinais "
          "comparados em jun/2021 com a série da taxa; Simular recuperação com a meta hipotética do patamar; e a tela de celular, com "
          "o Entenda pelo toque e a lista em cartões.")


if __name__ == "__main__":
    main()
