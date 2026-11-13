"""Detector de Sinais Territoriais na página única (comando V22, etapas 3 e 5), com a base versionada (somente leitura).

Confere, contra as respostas de POST /api/detector:
- a ferramenta na navegação principal ("Detector de Sinais"), que não pede nada ao motor sem territórios selecionados;
- a tabela da situação mais recente da janela para os municípios de Santa Catarina (uma linha por território, 50 por página),
  com a data do registro mais recente à vista;
- os filtros por fenômeno e pelo nome, e os detalhes de RIO RUFINO (SC): a série observada com o registro do pico marcado, os
  12 fenômenos (11 itens: 1 e 2 juntos) com os sete campos (o que foi observado, qual critério, quanto difere do habitual, o que
  significa, o que não significa, limitações do dado e qualidade do registro) e o histórico de sinais;
- a janela entre competências reais: com o fim em jun/2023, o salto de RIO RUFINO ainda é "verificar registro";
- os parâmetros personalizados, marcados como exploratórios, com "Voltar aos padrões";
- um estado como unidade na mesma seleção: os fatos, "sem classificação neste nível";
- "Alterar a seleção", que volta à Seleção de Territórios;
- os fenômenos 8 a 12 (etapa 5): em jun/2024, a comparação de 2 anos com a população comparável da base; as bolhas da distância e
  da taxa e o mapa dos sinais, com os valores e as coordenadas do motor; com a janela até jun/2021, os sinais observados (sem
  intensidade), a série da taxa com a referência e os textos do motor; e "Simular recuperação", que abre o Simulador de Cenários
  com a meta hipotética de voltar ao patamar anterior, sem mudar a seleção principal;
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, linha_do_estado, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
SC, PR, RIO_RUFINO, ABELARDO_LUZ = "42", "41", "code:421505", "code:420010"


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

        def do_detector(acao, condicao=None):
            """A resposta de /api/detector que a ação provocou e as opções do pedido."""
            with page.expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST" and (
                    condicao is None or condicao(options_of(r.request))), timeout=180000) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        def linha(codigo):
            return detector.locator('[data-testid="detector-linha"][data-id="' + codigo + '"]')

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

        # 2. Os municípios de Santa Catarina: a tabela da situação mais recente, uma linha por território, 50 por página.
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
            linha_do_estado(territorios, SC).get_by_test_id("analise-grupo-todos").check()
        corpo, enviado = do_detector(lambda: botao.click())
        assert enviado == {"base": {"municipios": {"todos": False, "estados": [SC], "ids": []}}}, enviado
        assert len(corpo["linhas"]) == 295 and corpo["janela"]["fim"] == "202406" and corpo["exploratorio"] is False, corpo["janela"]
        expect(detector).to_have_attribute("data-estado", "pronto")
        expect(detector.get_by_test_id("detector-data")).to_contain_text("Registro mais recente da base: jun/2024")
        expect(detector.get_by_test_id("detector-data")).to_contain_text("não a de hoje")
        tabela = detector.get_by_test_id("detector-tabela")
        expect(tabela).to_have_attribute("data-linhas", "295")
        expect(detector.get_by_test_id("detector-linha")).to_have_count(50)
        expect(detector.get_by_test_id("detector-paginas")).to_contain_text("Página 1 de 6")
        expect(tabela.locator("thead th")).to_have_text(["Território", "Condição estrutural", "Trajetória", "Ritmo e instabilidade",
                                                         "Comparação relativa",
                                                         "Contexto geográfico município mais próximo com 2,36 médicos por 1.000 habitantes ou mais",
                                                         "Sinais combinados",
                                                         "Qualidade do registro", "Última observação"])
        expect(tabela.locator("caption")).to_contain_text("limites provisórios")
        # O critério do contexto geográfico aparece no cabeçalho e na célula (revisão da etapa 5, 13/11/2026).
        expect(detector.get_by_test_id("detector-criterio-do-contexto")).to_have_text("município mais próximo com 2,36 médicos por 1.000 habitantes ou mais")
        expect(tabela).to_contain_text("dos municípios abaixo de 2,36 médicos por 1.000 habitantes")
        expect(detector.get_by_test_id("detector-resumo")).to_contain_text("295 territórios")
        page.screenshot(path=str(OUTPUT / "detector-01-tabela-real.png"), full_page=True)

        # 3. O filtro por fenômeno usa os sinais do motor; cada linha filtrada tem a intensidade por extenso.
        com_escala = [item for item in corpo["linhas"] if "estrutural" in item["sinais"]]
        assert com_escala, "há municípios de Santa Catarina com poucos médicos em jun/2024"
        detector.get_by_test_id("detector-filtro-fenomeno").select_option("estrutural")
        expect(tabela).to_have_attribute("data-linhas", str(len(com_escala)))
        primeira = detector.get_by_test_id("detector-linha").first
        expect(primeira).not_to_have_attribute("data-estrutural", "")
        expect(primeira.get_by_test_id("detector-intensidade").first).to_have_text(["Crítica", "Alta", "Atenção"][
            ["critica", "alta", "atencao"].index(primeira.get_attribute("data-estrutural"))])
        detector.get_by_test_id("detector-filtro-fenomeno").select_option("todos")

        # 4. RIO RUFINO (SC), pelo nome: o pico que volta (4 → 87 → 5) é descontinuidade de registro, sem alerta; os detalhes
        # trazem a série com o registro do pico marcado, os 12 fenômenos (11 itens) com os sete campos e o histórico de sinais.
        detector.get_by_test_id("detector-busca").fill("rio rufino")
        expect(tabela).to_have_attribute("data-linhas", "1")
        rio = linha(RIO_RUFINO)
        expect(rio.get_by_test_id("detector-registro")).to_have_attribute("data-marca", "descontinuidade")
        expect(rio.get_by_test_id("detector-registro")).to_have_text("Descontinuidade de registro (pico que volta)")
        detalhe_do_motor, enviado = do_detector(lambda: rio.get_by_test_id("detector-abrir").click(), lambda o: o.get("detalhe") == RIO_RUFINO)
        assert detalhe_do_motor["territorio"]["registro"]["eventos"][0]["valores"] == [4, 87, 5], detalhe_do_motor["territorio"]["registro"]
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_have_attribute("data-id", RIO_RUFINO)
        expect(detalhe.locator('[data-testid="detector-serie-ponto"][data-marca="pico_que_volta"]')).to_have_count(1)
        expect(detalhe.locator('[data-testid="detector-serie-ponto"][data-competencia="202306"]')).to_have_attribute("data-marca", "pico_que_volta")
        fenomenos = detalhe.get_by_test_id("detector-fenomeno")
        expect(fenomenos).to_have_count(11)
        assert fenomenos.evaluate_all("els => els.map(e => e.dataset.chave)") == [
            "estrutural", "declinio", "perda", "patamar", "desaceleracao", "instabilidade", "disponibilidade", "posicao", "defasagem",
            "contexto", "coexistencia"]
        assert [item["numero"] for item in detalhe_do_motor["fenomenos"]] == ["1–2", "3", "6", "7", "4", "5", "8", "9", "10", "11", "12"]
        # O fenômeno 4 diz em palavras quando não se aplica (em vez de "Sem desaceleração do crescimento (declínio)").
        situacao_4 = next(item for item in detalhe_do_motor["fenomenos"] if item["chave"] == "desaceleracao")["situacao"]
        assert situacao_4.startswith(("Sem desaceleração: ", "Não se aplica: ", "Desaceleração do crescimento", "Não avaliável")), situacao_4
        expect(detalhe.locator('[data-testid="detector-fenomeno"][data-chave="desaceleracao"]')).to_contain_text(situacao_4)
        perda = detalhe.locator('[data-testid="detector-fenomeno"][data-chave="perda"]')
        if perda.locator(".ferramenta-fenomeno-cabeca").get_attribute("aria-expanded") != "true":
            perda.locator(".ferramenta-fenomeno-cabeca").click()
        for campo, rotulo in (("observado", "O que foi observado"), ("criterio", "Qual critério"), ("habitual", "Quanto difere do habitual"),
                              ("significa", "O que significa"), ("naoSignifica", "O que não significa"), ("limitacoes", "Limitações do dado"),
                              ("qualidade", "Qualidade do registro")):
            expect(perda.get_by_test_id("detector-campo-" + campo).locator("dt")).to_have_text(rotulo)
            expect(perda.get_by_test_id("detector-campo-" + campo).locator("dd")).not_to_have_text("")
        texto_da_perda = next(item for item in detalhe_do_motor["fenomenos"] if item["chave"] == "perda")
        expect(perda.get_by_test_id("detector-campo-observado").locator("dd")).to_have_text(texto_da_perda["observado"])
        expect(perda.get_by_test_id("detector-campo-qualidade").locator("dd")).to_contain_text("pico que volta")
        detalhe.get_by_test_id("detector-historico-botao").click()
        expect(detalhe.get_by_test_id("detector-historico").locator("tbody tr")).to_have_count(22)
        expect(detalhe.get_by_test_id("detector-historico").locator('tbody tr[data-competencia="202401"]')).to_contain_text(
            "descontinuidade de registro")
        page.screenshot(path=str(OUTPUT / "detector-02-detalhe-real.png"), full_page=True)

        # 5. A janela entre competências reais: com o fim em jun/2023, a volta ainda não foi observada — "verificar registro".
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

        # 6. Parâmetros personalizados: exploratórios, nunca no lugar dos padrões em silêncio.
        expect(detector.get_by_test_id("detector-exploratorio")).to_have_count(0)
        detector.get_by_test_id("detector-parametros-botao").click()
        campo = detector.get_by_test_id("detector-parametro-estrutural-atencao")
        expect(campo).to_have_value("5")
        campo.fill("9")
        corpo_exploratorio, enviado = do_detector(lambda: detector.get_by_test_id("detector-parametros-aplicar").click(),
                                                  lambda o: bool(o.get("parametros")))
        assert enviado["parametros"] == {"estrutural": {"atencao": 9}} and corpo_exploratorio["exploratorio"] is True, enviado
        expect(detector).to_have_attribute("data-exploratorio", "true")
        expect(detector.get_by_test_id("detector-exploratorio")).to_contain_text("Configuração personalizada — exploratória.")
        assert corpo_exploratorio["resumo"]["sinais"]["estrutural"] > corpo["resumo"]["sinais"]["estrutural"]
        pedidos_antes = len(pedidos)
        detector.get_by_test_id("detector-padroes").click()
        expect(detector.get_by_test_id("detector-exploratorio")).to_have_count(0)
        expect(detector).to_have_attribute("data-exploratorio", "false")
        page.wait_for_timeout(400)
        assert len(pedidos) == pedidos_antes, "os padrões já calculados vêm da memória da tela"

        # 7. "Como foi calculado": as notas e a comparação da data, por porte.
        detector.get_by_test_id("detector-metodo-botao").click()
        metodo = detector.get_by_test_id("detector-metodo")
        expect(metodo).to_contain_text("Fato observado, raridade e sinal são coisas diferentes")
        expect(metodo.get_by_test_id("detector-calibracao").locator("tbody tr")).to_have_count(7)

        # 8. "Alterar a seleção" volta à Seleção de Territórios; com o Paraná como unidade, a linha dele traz os fatos, sem
        # intensidade (a comparação com territórios parecidos existe só para municípios).
        detector.get_by_test_id("detector-alterar-selecao").click()
        expect(area).to_have_attribute("data-ferramenta", "")
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true")
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
            linha_do_estado(territorios, PR).get_by_test_id("analise-grupo-so-estado").click()
        corpo_misto, enviado = do_detector(lambda: botao.click(), lambda o: o.get("estados_unidade") == [PR])
        assert enviado["base"]["municipios"]["estados"] == [SC] and len(corpo_misto["linhas"]) == 296, enviado
        detector.get_by_test_id("detector-busca").fill("paraná")
        parana = linha("uf:" + PR)
        expect(parana).to_have_attribute("data-tipo", "estado")
        expect(parana).to_contain_text("estado como unidade · fonte estadual")
        expect(parana.get_by_test_id("detector-estrutural")).to_contain_text("sem classificação neste nível")
        expect(parana.get_by_test_id("detector-intensidade")).to_have_count(0)
        # O estado como unidade não tem um ponto único: o contexto geográfico não se aplica; a taxa e a posição entre os estados, sim.
        expect(parana.get_by_test_id("detector-contexto")).to_contain_text("Não se aplica")
        expect(parana.get_by_test_id("detector-posicao")).to_contain_text("Percentil ")
        detector.get_by_test_id("detector-busca").fill("")

        # 9. Fenômenos 8 a 12 (etapa 5). Com a população do Ministério da Saúde (comando V23, 13/11/2026), a base inteira é um
        # trecho só de população comparável, lido dela mesma: no último registro (jun/2024), a janela de jun/2022 a jun/2024 vale.
        do_motor = corpo_misto["comparacao"]
        assert (do_motor["estado"], do_motor["de"], do_motor["ate"]) == ("comparavel", "202206", "202406"), do_motor
        assert do_motor["trechos"] == [[2014, 2024]] and do_motor["motivo"] is None, do_motor
        municipais = [item for item in corpo_misto["linhas"] if item["tipo"] == "municipio"]
        assert not any("comparacao_nao_habilitada" in (item["disponibilidade"]["estado"], item["posicao"]["estado"]) for item in municipais)
        assert all(item["disponibilidade"]["taxa"] is not None and item["posicao"]["percentil"] is not None for item in municipais)
        comparacao = detector.get_by_test_id("detector-comparacao")
        expect(comparacao).to_have_attribute("data-estado", "comparavel")
        expect(comparacao).to_contain_text("variação de jun/2022 a jun/2024, em 2 anos, com população comparável")
        expect(comparacao).to_contain_text("municípios do país atendem ao critério")
        primeira = detector.get_by_test_id("detector-linha").first
        expect(primeira.get_by_test_id("detector-disponibilidade")).to_contain_text("por 1.000 hab.")
        # As bolhas do Agente: uma por território com distância a mostrar (a distância até o município mais próximo que atende ao
        # critério e a taxa por habitante); só contexto, sem intensidade.
        visual = detector.get_by_test_id("detector-visual")
        expect(visual).to_have_attribute("data-vista", "bolhas")
        com_distancia = [item for item in corpo_misto["linhas"] if item["contexto"]["estado"] == "contexto" and item["disponibilidade"]["taxa"] is not None]
        assert len(com_distancia) > 50, len(com_distancia)
        bolhas = detector.get_by_test_id("detector-bolhas")
        expect(bolhas).to_have_attribute("data-itens", str(len(com_distancia)))
        expect(bolhas.locator('[data-testid="analise-bolha"]').first).to_be_visible()
        expect(bolhas).to_contain_text("não é distância por estrada, acesso nem isolamento, e não tem intensidade")
        page.screenshot(path=str(OUTPUT / "detector-03-bolhas-real.png"), full_page=False)
        # O mapa dos sinais: em destaque, os municípios com o fenômeno do filtro (sem filtro, os sinais combinados), só com as
        # coordenadas que o motor mandou; o filtro deixa à vista só as linhas com o fenômeno.
        com_ponto = set(corpo_misto["coordenadas"])
        def no_mapa(sinal):
            return sum(1 for item in municipais if sinal in item["sinais"] and item["id"] in com_ponto)
        assert no_mapa("combinados") > 0 and no_mapa("patamar") > 0, (no_mapa("combinados"), no_mapa("patamar"))
        detector.get_by_test_id("detector-vista-mapa").click()
        mapa = detector.get_by_test_id("detector-mapa")
        expect(mapa).to_have_attribute("data-sinal", "combinados")
        expect(mapa).to_have_attribute("data-destaque", str(no_mapa("combinados")))
        detector.get_by_test_id("detector-filtro-fenomeno").select_option("patamar")
        expect(mapa).to_have_attribute("data-sinal", "patamar")
        expect(mapa).to_have_attribute("data-destaque", str(no_mapa("patamar")))
        expect(mapa).to_have_attribute("data-fundo", "0")
        expect(mapa.locator('[data-testid="analise-mapa-ponto"]').first).to_be_visible()
        expect(mapa).to_contain_text("estados como unidade não têm ponto")
        page.screenshot(path=str(OUTPUT / "detector-04-mapa-real.png"), full_page=False)
        detector.get_by_test_id("detector-filtro-fenomeno").select_option("todos")
        detector.get_by_test_id("detector-vista-tabela").click()
        expect(visual).to_have_attribute("data-vista", "tabela")
        expect(detector.get_by_test_id("detector-bolhas")).to_have_count(0)

        # 10. Com a janela até jun/2021 (de jun/2019 a jun/2021, com população comparável), os sinais observados aparecem: limites
        # provisórios, sem intensidade. Os detalhes trazem a série da taxa com a da referência e os textos do motor.
        corpo_2021, enviado = do_detector(lambda: detector.get_by_test_id("detector-janela-fim").select_option("202106"),
                                          lambda o: (o.get("janela") or {}).get("fim") == "202106")
        assert (corpo_2021["comparacao"]["estado"], corpo_2021["comparacao"]["de"], corpo_2021["comparacao"]["ate"]) == ("comparavel", "201906", "202106")
        expect(comparacao).to_have_attribute("data-estado", "comparavel")
        expect(comparacao).to_contain_text("variação de jun/2019 a jun/2021, em 2 anos, com população comparável")
        com_queda = [item for item in corpo_2021["linhas"] if "disponibilidade" in item["sinais"]]
        assert com_queda and corpo_2021["resumo"]["sinais"]["disponibilidade"] == len(com_queda), "há quedas da taxa por habitante em Santa Catarina"
        assert all(item["dimensoes"]["comparacao"] is None and item["dimensoes"]["contexto"] is None for item in corpo_2021["linhas"])
        detector.get_by_test_id("detector-filtro-fenomeno").select_option("disponibilidade")
        expect(tabela).to_have_attribute("data-linhas", str(len(com_queda)))
        expect(tabela.locator("caption")).to_contain_text("são sinais observados em 2 anos, com limites provisórios e sem intensidade")
        alvo = com_queda[0]
        da_queda = linha(alvo["id"])
        expect(da_queda.get_by_test_id("detector-disponibilidade")).to_contain_text("% em 2 anos)")
        expect(da_queda.get_by_test_id("detector-disponibilidade")).to_contain_text(
            "sinal muito forte" if alvo["disponibilidade"]["sinal"] == "muito_forte" else "sinal forte")
        expect(da_queda.get_by_test_id("detector-disponibilidade").get_by_test_id("detector-intensidade")).to_have_count(0)
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
        for chave in ("disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"):
            do_fenomeno = next(item for item in detalhe_2021["fenomenos"] if item["chave"] == chave)
            item = detalhe.locator('[data-testid="detector-fenomeno"][data-chave="' + chave + '"]')
            expect(item.get_by_test_id("detector-fenomeno-situacao")).to_have_text(do_fenomeno["situacao"])
            if item.locator(".ferramenta-fenomeno-cabeca").get_attribute("aria-expanded") != "true":
                item.locator(".ferramenta-fenomeno-cabeca").click()
            expect(item.get_by_test_id("detector-campo-observado").locator("dd")).to_have_text(do_fenomeno["observado"])
            expect(item.get_by_test_id("detector-campo-naoSignifica").locator("dd")).to_have_text(do_fenomeno["nao_significa"])
        oito = next(item for item in detalhe_2021["fenomenos"] if item["chave"] == "disponibilidade")
        assert oito["numero"] == "8" and oito["situacao"].endswith(("sinal observado forte", "sinal observado muito forte")), oito["situacao"]
        assert "Sem classificação de intensidade" in oito["habitual"], oito["habitual"]
        page.screenshot(path=str(OUTPUT / "detector-05-comparacao-2021-real.png"), full_page=False)
        da_queda.get_by_test_id("detector-abrir").click()  # fecha os detalhes
        detector.get_by_test_id("detector-filtro-fenomeno").select_option("todos")

        # 11. "Simular recuperação" (decisão D-B): de volta ao último registro, ABELARDO LUZ (SC) está abaixo do patamar anterior; o
        # botão abre o Simulador de Cenários só com ele, com a meta hipotética (e editável) de voltar ao patamar, sem mudar a
        # seleção principal. Quem está acima do patamar não tem o botão.
        principal = area.get_by_test_id("analise-aba-territorios-resumo").inner_text()
        detector.get_by_test_id("detector-janela-fim").select_option("202406")
        expect(comparacao).to_have_attribute("data-estado", "comparavel")
        expect(comparacao).to_contain_text("variação de jun/2022 a jun/2024")
        do_abelardo = next(item for item in corpo_misto["linhas"] if item["id"] == ABELARDO_LUZ)
        assert "patamar" in do_abelardo["sinais"] and do_abelardo["patamar"]["diferenca_pct"] < 0, do_abelardo["patamar"]
        acima = next(item for item in municipais if item["patamar"]["patamar"] is not None and (item["patamar"]["diferenca_pct"] or 0) > 0)
        detector.get_by_test_id("detector-busca").fill(acima["rotulo"].split(" (")[0])
        linha(acima["id"]).get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", acima["id"])
        expect(detector.get_by_test_id("detector-abrir-no-simulador")).to_be_visible()
        expect(detector.get_by_test_id("detector-simular-recuperacao")).to_have_count(0)
        detector.get_by_test_id("detector-busca").fill("abelardo")
        linha(ABELARDO_LUZ).get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", ABELARDO_LUZ)
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
        expect(aviso).to_contain_text("Abaixo do patamar anterior")
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
        page.screenshot(path=str(OUTPUT / "detector-06-simular-recuperacao-real.png"), full_page=True)

        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("DETECTOR PASS: ferramenta na navegação sem pedido sem seleção, tabela de Santa Catarina (295, 50 por página), filtro por "
          "fenômeno, RIO RUFINO com o pico que volta (série, seis fenômenos com sete campos e histórico), janela até jun/2023 "
          "(verificar registro), parâmetros exploratórios com volta aos padrões pela memória, Como foi calculado, o Paraná como "
          "unidade sem intensidade, fenômenos 8 a 12 (comparação de 2 anos em jun/2024, bolhas, mapa, sinais observados e série "
          "da taxa em jun/2021) e Simular recuperação com a meta hipotética do patamar.")


if __name__ == "__main__":
    main()
