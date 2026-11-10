"""Detector de Sinais Territoriais na página única (comando V22, etapa 3), com a base versionada (somente leitura).

Confere, contra as respostas de POST /api/detector:
- a ferramenta na navegação principal ("Detector de Sinais"), que não pede nada ao motor sem territórios selecionados;
- a tabela da situação mais recente da janela para os municípios de Santa Catarina (uma linha por território, 50 por página),
  com a data do registro mais recente à vista;
- os filtros por fenômeno e pelo nome, e os detalhes de RIO RUFINO (SC): a série observada com o registro do pico marcado, os
  seis fenômenos com os sete campos (o que foi observado, qual critério, quanto difere do habitual, o que significa, o que não
  significa, limitações do dado e qualidade do registro) e o histórico de sinais;
- a janela entre competências reais: com o fim em jun/2023, o salto de RIO RUFINO ainda é "verificar registro";
- os parâmetros personalizados, marcados como exploratórios, com "Voltar aos padrões";
- um estado como unidade na mesma seleção: os fatos, "sem classificação neste nível";
- "Alterar a seleção", que volta à Seleção de Territórios; nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, linha_do_estado, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
SC, PR, RIO_RUFINO = "42", "41", "code:421505"


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
                                                         "Qualidade do registro", "Última observação"])
        expect(tabela.locator("caption")).to_contain_text("limites provisórios")
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
        # trazem a série com o registro do pico marcado, os seis fenômenos com os sete campos e o histórico de sinais.
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
        expect(fenomenos).to_have_count(6)
        assert fenomenos.evaluate_all("els => els.map(e => e.dataset.chave)") == [
            "estrutural", "declinio", "perda", "patamar", "desaceleracao", "instabilidade"]
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

        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("DETECTOR PASS: ferramenta na navegação sem pedido sem seleção, tabela de Santa Catarina (295, 50 por página), filtro por "
          "fenômeno, RIO RUFINO com o pico que volta (série, seis fenômenos com sete campos e histórico), janela até jun/2023 "
          "(verificar registro), parâmetros exploratórios com volta aos padrões pela memória, Como foi calculado e o Paraná como "
          "unidade sem intensidade.")


if __name__ == "__main__":
    main()
