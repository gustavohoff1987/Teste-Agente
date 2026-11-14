"""Detector de Sinais Territoriais na página única (comando V23, Proposta V3, Parte B), com a base versionada (somente leitura).

Confere, contra as respostas de POST /api/detector:
- a ferramenta na navegação principal ("Detector de Sinais"), que não pede nada ao motor sem territórios selecionados;
- a primeira tela para os municípios de Santa Catarina: a lista de quatro colunas (Território · Alerta · Por quê · Último
  registro), 50 por página, com a data do registro mais recente à vista; o resumo dos níveis, clicável como filtro; os filtros numa
  linha (Até, Nível, Sinal e Buscar); a ordem pelos cabeçalhos; o nível sempre escrito, com o tipo de critério;
- os detalhes de RIO RUFINO (SC): a série observada com o registro do pico marcado, os 12 sinais (11 itens: 1 e 2 juntos) em
  quatro grupos mais Juntos, cada um com o nível, uma frase e o "Entenda" (mouse, teclado e "Ver explicação completa"), a
  explicação completa com os sete campos e o histórico de sinais;
- a janela entre competências reais: com o fim em jun/2023, o salto de RIO RUFINO ainda é "verificar registro";
- "Ajustar critérios": os limites em frases, com os campos dentro delas; trocar um valor torna a configuração exploratória, com
  aviso no alto e "Voltar ao padrão" sempre à vista;
- "Como foi calculado": os três níveis e a régua da data por porte, com "sem comparações suficientes" no crítico de 1.000 para cima;
- um estado como unidade na mesma seleção, com a régua própria dos estados e "sem comparações suficientes" com os números;
- as visões Mapa (os pontos pelo nível, com a legenda escrita) e Gráfico (a distância e a taxa, pelo nível);
- com a janela até jun/2021, os sinais comparados em 2 anos (8 a 10) com nível, a série da taxa com a referência e os textos do
  motor; e "Simular recuperação", que abre o Simulador de Cenários com a meta hipotética de voltar ao patamar, sem mudar a
  seleção principal;
- numa tela de celular, com toque: o "Entenda" abre pelo toque, cabe na largura e fecha com um toque fora; a lista vira cartões e
  nada passa da largura;
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, linha_do_estado, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
SC, PR, RIO_RUFINO, ABELARDO_LUZ = "42", "41", "code:421505", "code:420010"
ESTADOS = ("critico", "elevado", "moderado", "sem_alerta", "sem_comparacoes", "sem_nivel")
NOMES = {"critico": "Crítico", "elevado": "Elevado", "moderado": "Moderado"}
SINAIS = ["estrutural", "declinio", "desaceleracao", "instabilidade", "perda", "patamar", "disponibilidade", "posicao", "defasagem", "contexto",
          "coexistencia"]


def estado_do_alerta(item):
    return item["alerta"]["nivel"] or item["alerta"]["estado"]


def com_o_sinal(item, sinal):
    return any(dado["sinal"] == sinal for dado in item["alerta"]["sinais"])


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "este roteiro usa a base Brasil versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        offline(context)
        page = context.new_page()
        falhas, chamadas_llm, pedidos = [], [], []
        page.on("pageerror", lambda error: falhas.append(str(error)))
        page.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: pedidos.append(request) if request.url.endswith("/api/detector") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        botao = area.get_by_test_id("analise-ferramenta-detector")
        detector = area.get_by_test_id("detector")

        def do_detector(acao, condicao=None, da_pagina=None):
            """A resposta de /api/detector que a ação provocou e as opções do pedido."""
            with (da_pagina or page).expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST" and (
                    condicao is None or condicao(options_of(r.request))), timeout=180000) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

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

        # 2. Os municípios de Santa Catarina: a lista de quatro colunas, uma linha por território, 50 por página, na visão Lista.
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
        expect(cabecalhos).to_have_count(4)
        for indice, nome in enumerate(("Território", "Alerta", "Por quê", "Último registro")):
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
        expect(primeira.get_by_test_id("detector-nivel")).to_have_text("Crítico")
        do_primeiro = next(item for item in corpo["linhas"] if item["id"] == primeira.get_attribute("data-id"))
        expect(primeira.get_by_test_id("detector-criterio")).to_have_text(do_primeiro["alerta"]["criterio"])
        expect(primeira.get_by_test_id("detector-por-que")).to_have_text(do_primeiro["alerta"]["por_que"])
        assert do_primeiro["alerta"]["criterio"] in ("por convenção", "comparado com a base"), do_primeiro["alerta"]
        page.screenshot(path=str(OUTPUT / "detector-01-lista-real.png"), full_page=True)
        # O resumo é clicável e funciona como o filtro "Nível".
        resumo.get_by_test_id("detector-resumo-elevado").click()
        expect(detector.get_by_test_id("detector-filtro-nivel")).to_have_value("elevado")
        expect(tabela).to_have_attribute("data-linhas", str(niveis["elevado"]))
        assert set(detector.get_by_test_id("detector-linha").evaluate_all("els => els.map(e => e.dataset.alerta)")) == {"elevado"}
        assert set(detector.get_by_test_id("detector-nivel").all_text_contents()) == {"Elevado"}
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

        # 3. O filtro "Sinal": a linha passa quando o sinal tem nível nela (não só o sinal principal do alerta).
        com_poucos = [item for item in corpo["linhas"] if com_o_sinal(item, "estrutural")]
        assert com_poucos and len(com_poucos) == corpo["resumo"]["com_nivel"]["estrutural"], "há municípios de Santa Catarina com poucos médicos em jun/2024"
        detector.get_by_test_id("detector-filtro-sinal").select_option("estrutural")
        expect(tabela).to_have_attribute("data-linhas", str(len(com_poucos)))
        assert all("estrutural" in sinais.split() for sinais in detector.get_by_test_id("detector-linha").evaluate_all("els => els.map(e => e.dataset.sinais)"))
        detector.get_by_test_id("detector-filtro-sinal").select_option("todos")

        # 4. RIO RUFINO (SC), pelo nome: o pico que volta (4 → 87 → 5) é descontinuidade de registro, sem alerta de queda; os
        # detalhes trazem a série com o registro do pico marcado e os 12 sinais (11 itens) em quatro grupos, mais Juntos.
        detector.get_by_test_id("detector-busca").fill("rio rufino")
        expect(tabela).to_have_attribute("data-linhas", "1")
        rio = linha(RIO_RUFINO)
        expect(rio.get_by_test_id("detector-registro")).to_have_attribute("data-marca", "descontinuidade")
        expect(rio.get_by_test_id("detector-registro")).to_have_text("Descontinuidade de registro (pico que volta)")
        expect(rio.get_by_test_id("detector-ultimo")).to_contain_text("jun/2024 · 5 médicos")
        detalhe_do_motor, enviado = do_detector(lambda: rio.get_by_test_id("detector-abrir").click(), lambda o: o.get("detalhe") == RIO_RUFINO)
        assert detalhe_do_motor["territorio"]["registro"]["eventos"][0]["valores"] == [4, 87, 5], detalhe_do_motor["territorio"]["registro"]
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_have_attribute("data-id", RIO_RUFINO)
        do_rio = detalhe_do_motor["linha"]["alerta"]
        expect(detalhe.get_by_test_id("detector-detalhe-alerta")).to_have_attribute("data-estado", do_rio["nivel"] or do_rio["estado"])
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
                expect(da_tela.get_by_test_id("detector-fenomeno-criterio")).to_contain_text(item["criterio_do_nivel"])
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
        detalhe.get_by_test_id("detector-historico-botao").click()
        expect(detalhe.get_by_test_id("detector-historico").locator("tbody tr")).to_have_count(22)
        expect(detalhe.get_by_test_id("detector-historico").locator('tbody tr[data-competencia="202401"]')).to_contain_text(
            "descontinuidade de registro")
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
        pedidos_antes = len(pedidos)
        voltar.click()
        expect(detector.get_by_test_id("detector-exploratorio")).to_have_count(0)
        expect(detector).to_have_attribute("data-exploratorio", "false")
        expect(criterios.get_by_test_id("detector-parametro-estrutural-moderado")).to_have_value("5")
        expect(voltar).to_be_disabled()
        page.wait_for_timeout(400)
        assert len(pedidos) == pedidos_antes, "o padrão já calculado vem da memória da tela"
        detector.get_by_test_id("detector-parametros-botao").click()
        expect(criterios).to_have_count(0)

        # 7. "Como foi calculado", aberto pelo "Ver explicação completa" do "Entenda" da ferramenta: as notas, os três níveis e a
        # régua da data por porte. A tabela mostra as comparações da própria faixa: de 1.000 médicos para cima, ela não tem as 999
        # do crítico (de 3.000 para cima, nem com as faixas vizinhas, e o crítico não é avaliado).
        expect(detector.get_by_test_id("detector-metodo")).to_have_count(0)
        detector.get_by_test_id("detector-entenda-ferramenta-botao").click()
        expect(detector.get_by_test_id("detector-entenda-ferramenta-caixa")).to_contain_text(corpo["entenda"]["ferramenta"]["texto"])
        detector.get_by_test_id("detector-entenda-ferramenta-completa").click()
        metodo = detector.get_by_test_id("detector-metodo")
        expect(metodo).to_be_visible()
        expect(metodo).to_contain_text("Um nível por território: o maior entre os seus sinais, sem soma nem índice.")
        expect(metodo.get_by_test_id("detector-niveis").locator("tbody tr")).to_have_text([
            "Moderado1 em cada 20pelo menos 19", "Elevado1 em cada 100pelo menos 99", "Crítico1 em cada 1.000pelo menos 999"])
        regua = metodo.get_by_test_id("detector-calibracao")
        assert regua.locator("tbody tr").evaluate_all("els => els.map(e => e.dataset.porte)") == [
            "1 a 3", "4 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 a 999", "1.000 a 2.999", "3.000 a 9.999", "10.000 ou mais"]
        for celula in corpo["calibracao"]["perda"]:
            da_faixa = regua.locator('tbody tr[data-porte="' + celula["porte"] + '"] td[data-nivel="critico"]')
            if celula["critico"]["queda_pct"] is None:
                expect(da_faixa).to_have_text("sem comparações suficientes ({:,} de 999)".format(celula["comparacoes"]).replace(",", "."))
            else:
                expect(da_faixa).to_contain_text("queda maior que ")
        sem_critico = [celula["porte"] for celula in corpo["calibracao"]["perda"] if celula["critico"]["queda_pct"] is None]
        assert sem_critico == ["1.000 a 2.999", "3.000 a 9.999", "10.000 ou mais"], sem_critico
        expect(metodo.get_by_test_id("detector-calibracao-estados")).to_have_count(0)   # sem estados como unidade na seleção
        detector.get_by_test_id("detector-metodo-botao").click()
        expect(metodo).to_have_count(0)

        # 8. "Alterar a seleção" volta à Seleção de Territórios; com o Paraná como unidade, a linha dele usa a régua própria dos
        # estados (a base dos estados, pequena): os níveis que ela não sustenta ficam "sem comparações suficientes", com os números.
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
        detalhe_do_parana, enviado = do_detector(lambda: parana.get_by_test_id("detector-abrir").click(), lambda o: o.get("detalhe") == "uf:" + PR)
        detalhe = detector.get_by_test_id("detector-detalhe")
        queda_do_parana = next(item for item in detalhe_do_parana["fenomenos"] if item["chave"] == "perda")
        assert queda_do_parana["sem_comparacoes"]["niveis"] == ["critico"] and queda_do_parana["sem_comparacoes"]["pede"] == 999, queda_do_parana
        expect(sinal_da_tela(detalhe, "perda").get_by_test_id("detector-fenomeno-sem-comparacoes")).to_have_text(queda_do_parana["sem_comparacoes"]["texto"])
        expect(sinal_da_tela(detalhe, "perda").get_by_test_id("detector-fenomeno-sem-comparacoes")).to_contain_text("Sem comparações suficientes para o crítico: há ")
        # O estado como unidade não tem um ponto único: a distância não se aplica.
        expect(sinal_da_tela(detalhe, "contexto")).to_have_attribute("data-estado", "contexto")
        expect(sinal_da_tela(detalhe, "contexto").get_by_test_id("detector-fenomeno-situacao")).to_contain_text("Não se aplica")
        detector.get_by_test_id("detector-metodo-botao").click()
        dos_estados = detector.get_by_test_id("detector-calibracao-estados")
        expect(dos_estados).to_contain_text("régua própria, com a base dos estados")
        expect(dos_estados.locator("tbody tr").first.locator('td[data-nivel="critico"]')).to_contain_text("sem comparações suficientes")
        page.screenshot(path=str(OUTPUT / "detector-05-estado-real.png"), full_page=True)
        detector.get_by_test_id("detector-metodo-botao").click()
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
        expect(mapa).to_contain_text("A base não tem as divisas")
        expect(mapa).to_contain_text("o estado como unidade não tem ponto")
        page.screenshot(path=str(OUTPUT / "detector-06-mapa-real.png"), full_page=False)
        # Com o filtro "Sinal", o mapa pinta o nível daquele sinal, e a lista fica só com as linhas em que ele tem nível.
        detector.get_by_test_id("detector-filtro-sinal").select_option("patamar")
        com_patamar = [item for item in corpo_misto["linhas"] if com_o_sinal(item, "patamar")]
        assert com_patamar and sum(no_mapa(nivel, "patamar") for nivel in NOMES) == len(com_patamar), len(com_patamar)
        expect(mapa).to_have_attribute("data-sinal", "patamar")
        expect(mapa).to_have_attribute("data-fundo", "0")
        for nivel in NOMES:
            expect(mapa).to_have_attribute("data-" + nivel, str(no_mapa(nivel, "patamar")))
        expect(tabela).to_have_attribute("data-linhas", str(len(com_patamar)))
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
        detalhe_2021, enviado = do_detector(lambda: da_queda.get_by_test_id("detector-abrir").click(), lambda o: o.get("detalhe") == alvo["id"])
        assert enviado["janela"] == {"fim": "202106"} or enviado["janela"].get("fim") == "202106", enviado
        detalhe = detector.get_by_test_id("detector-detalhe")
        serie_da_taxa = detalhe.get_by_test_id("detector-serie-da-taxa")
        expect(serie_da_taxa).to_have_attribute("data-referencias", "1")
        expect(serie_da_taxa.locator('[data-testid="analise-serie-referencia"]')).to_have_count(1)
        expect(serie_da_taxa).to_contain_text(detalhe_2021["comparativo"]["referencia"]["rotulo"])
        # Os trechos de população comparável vêm do motor, lidos da própria base: com a população nova, um trecho só.
        assert detalhe_2021["comparativo"]["trechos"] == [[2014, 2024]], detalhe_2021["comparativo"]["trechos"]
        expect(serie_da_taxa).to_contain_text("a variação entre datas só é lida de 2014 a 2024, quando a população da base é comparável")
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
        # principal. Quem está acima do patamar não tem o botão.
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
        pedidos_do_simulador = []
        page.on("request", lambda request: pedidos_do_simulador.append(request) if request.url.endswith("/api/simulador") else None)
        detector.get_by_test_id("detector-simular-recuperacao").click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        simulador = area.get_by_test_id("simulador")
        expect(simulador).to_have_attribute("data-etapa", "3")
        aviso = simulador.get_by_test_id("simulador-do-detector")
        expect(aviso).to_have_attribute("data-recuperacao", "true")
        expect(aviso).to_contain_text("Aberto pelo Detector de Sinais: ABELARDO LUZ (SC), avaliado em jun/2024")
        expect(aviso).to_contain_text("Sinais com nível lá: ")
        expect(aviso).to_contain_text("Abaixo do que já teve (")
        expect(aviso).to_contain_text("meta hipotética que você pode trocar")
        plano = simulador.get_by_test_id("simulador-plano")
        expect(plano).to_have_attribute("data-meta", "patamar")
        patamar = do_abelardo["patamar"]["patamar"]
        expect(plano.get_by_test_id("simulador-plano-valor")).to_have_value(str(patamar).replace(".", ","))   # a precisão do Detector
        expect(plano).to_contain_text("não um plano")
        page.wait_for_timeout(400)
        assert not pedidos_do_simulador, "nada é calculado antes de \"Calcular os cenários\""
        with page.expect_response(lambda r: r.url.endswith("/api/simulador") and r.request.method == "POST", timeout=180000) as evento:
            simulador.get_by_test_id("simulador-calcular").click()
        assert evento.value.status == 200, evento.value.text()[:2000]
        pedido, cenarios = options_of(evento.value.request), evento.value.json()["territorios"]
        assert pedido["base"] == {"municipios": {"todos": False, "estados": [], "ids": [ABELARDO_LUZ]}} and "estados_unidade" not in pedido, pedido
        assert pedido["cenarios"][0]["planejamento"] == {"meta": {"tipo": "patamar", "valor": patamar}, "em": "202506"}, pedido
        assert [item["id"] for item in cenarios] == [ABELARDO_LUZ], cenarios
        planejado = cenarios[0]["cenarios"][0]["planejamento"]
        assert planejado["estado"] == "calculado" and planejado["por_evento"] >= 1 and planejado["resultado"] >= planejado["meta"]["valor"], planejado
        assert planejado["texto"].startswith("Meta hipotética: voltar ao patamar de ") and planejado["texto"].endswith("não um plano."), planejado["texto"]
        for proibida in ("recomenda", "é preciso", "deveria", "necessário prover"):
            assert proibida not in planejado["texto"].lower(), proibida
        resultado = simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="c1"]')
        expect(resultado.get_by_test_id("simulador-planejamento")).to_have_attribute("data-estado", "calculado")
        expect(resultado.get_by_test_id("simulador-planejamento")).to_have_attribute("data-por-evento", str(planejado["por_evento"]))
        expect(resultado.get_by_test_id("simulador-planejamento-texto")).to_have_text(planejado["texto"])
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(principal)   # a seleção principal não mudou
        page.screenshot(path=str(OUTPUT / "detector-09-simular-recuperacao-real.png"), full_page=True)

        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas, falhas
        context.close()

        # 12. Numa tela de celular, com toque: o "Entenda" abre pelo toque, cabe na largura e fecha com um toque fora; a lista
        # vira cartões (o território e o alerta na primeira linha; o porquê e o último registro abaixo) e nada passa da largura.
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
        caixas = primeira.evaluate("""e => Object.fromEntries([...e.children].map(c => [c.dataset.rotulo, c.getBoundingClientRect()])
          .map(([rotulo, r]) => [rotulo, [Math.round(r.left), Math.round(r.top), Math.round(r.right)]]))""")
        assert caixas["Por quê"][1] > caixas["Território"][1] and caixas["Último registro"][1] > caixas["Por quê"][1], caixas
        assert abs(caixas["Alerta"][1] - caixas["Território"][1]) <= 4 and caixas["Alerta"][0] >= caixas["Território"][2] - 1, caixas
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
        tela.screenshot(path=str(OUTPUT / "detector-11-celular-detalhe-real.png"), full_page=False)
        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas_no_celular, falhas_no_celular
        browser.close()
    print("DETECTOR PASS: ferramenta na navegação sem pedido sem seleção; lista de quatro colunas de Santa Catarina (295, 50 por página), "
          "resumo dos níveis clicável, filtros Até, Nível, Sinal e Buscar e ordem pelos cabeçalhos; RIO RUFINO com o pico que volta "
          "(série, 12 sinais em quatro grupos mais Juntos, Entenda por mouse e teclado, explicação completa e histórico); janela até "
          "jun/2023 (verificar registro); critérios em frases, configuração exploratória e Voltar ao padrão pela memória; Como foi "
          "calculado com a régua por porte; o Paraná como unidade com a régua dos estados; mapa e gráfico pelos níveis; sinais "
          "comparados em jun/2021 com a série da taxa; Simular recuperação com a meta hipotética do patamar; e a tela de celular, com "
          "o Entenda pelo toque e a lista em cartões.")


if __name__ == "__main__":
    main()
