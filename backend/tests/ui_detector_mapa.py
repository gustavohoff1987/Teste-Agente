"""O mapa do Detector de Sinais com as divisas, com municípios de dois estados à vista (etapa 7 do comando V23), na base
versionada (somente leitura).

Confere, contra a resposta de POST /api/detector, com os municípios de Santa Catarina e de Roraima selecionados:
- a malha municipal do IBGE só é pedida quando o mapa abre, e uma vez só (voltar à lista e abrir o mapa de novo não a pede outra vez);
- com dois estados à vista, as divisas dos estados aparecem e as dos municípios não; a área de cada município com nível leva a cor
  dele, e todos os pontos cabem no desenho;
- "Aproximar o mapa em" oferece os estados dos territórios à vista. Aproximado em Santa Catarina, o mapa enquadra o estado (os
  pontos de Roraima saem do desenho), mostra as divisas dos municípios dele e não corta nada antes do desenho: as áreas com nível
  dos dois estados continuam nele. O mesmo com Roraima;
- de volta a "todos os territórios à vista", as divisas dos municípios saem;
- com a busca deixando um estado só à vista, as divisas dos municípios aparecem sem aproximar, e a escolha some (o estado escolhido
  antes deixa de valer quando sai da vista);
- com o Brasil inteiro (revisão final do comando V23, 15/11/2026): os 5.570 municípios têm ponto — os seis em que a base traz a
  coordenada fora do intervalo válido, com a sede municipal da camada oficial do IBGE, ditos na legenda —, e as siglas dos 27
  estados aparecem sem se sobrepor (a de Goiás e a do Distrito Federal ficavam uma sobre a outra);
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, linha_do_estado, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
SC, RR = "42", "14"
ARQUIVO_DA_MALHA = "/malha/municipios-ibge-qualidade-minima.json"
# Quantos pontos de um estado (pelo prefixo do código) ficam dentro do desenho.
DENTRO_DO_DESENHO = """(mapa, prefixo) => {
  const svg = mapa.querySelector('[data-testid="analise-mapa-conjuntos"] svg'), largura = svg.viewBox.baseVal.width, altura = svg.viewBox.baseVal.height;
  return [...svg.querySelectorAll('[data-testid="analise-mapa-ponto"]')].filter(ponto => ponto.dataset.id.startsWith('code:' + prefixo)).filter(ponto => {
    const x = Number(ponto.getAttribute('cx')), y = Number(ponto.getAttribute('cy'));
    return x >= 0 && x <= largura && y >= 0 && y <= altura;
  }).length;
}"""


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "este roteiro usa a base Brasil versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 1000})
        offline(context)
        page = context.new_page()
        falhas, chamadas_llm, da_malha = [], [], []
        page.on("pageerror", lambda error: falhas.append(str(error)))
        page.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: da_malha.append(request.url) if request.url.endswith(ARQUIVO_DA_MALHA) else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        detector = area.get_by_test_id("detector")
        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. Os municípios de Santa Catarina e de Roraima, no Detector. Até o mapa abrir, a malha não é pedida.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
        for estado in (SC, RR):
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
                linha_do_estado(territorios, estado).get_by_test_id("analise-grupo-todos").check()
        with page.expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST", timeout=180000) as evento:
            area.get_by_test_id("analise-ferramenta-detector").click()
        assert evento.value.status == 200, evento.value.text()[:2000]
        corpo, enviado = evento.value.json(), options_of(evento.value.request)
        assert sorted(enviado["base"]["municipios"]["estados"]) == [RR, SC] and not enviado["base"]["municipios"]["ids"], enviado
        expect(detector).to_have_attribute("data-estado", "pronto")
        municipais = [item for item in corpo["linhas"] if item["tipo"] == "municipio"]
        assert len(municipais) == len(corpo["linhas"]) == 310, len(corpo["linhas"])

        def do_estado(prefixo):
            return [item for item in municipais if item["id"].startswith("code:" + prefixo)]
        com_ponto = set(corpo["coordenadas"])
        pontos = {prefixo: sum(1 for item in do_estado(prefixo) if item["id"] in com_ponto) for prefixo in (SC, RR)}
        com_nivel = {prefixo: sum(1 for item in do_estado(prefixo) if item["alerta"]["nivel"]) for prefixo in (SC, RR)}
        # Muda de propósito na revisão final do V23: os dois municípios de Santa Catarina em que a base traz a coordenada fora do
        # intervalo válido ficam com a sede municipal da camada oficial do IBGE — 295 pontos (antes, 293).
        assert (len(do_estado(SC)), len(do_estado(RR)), pontos) == (295, 15, {SC: 295, RR: 15}), pontos
        assert corpo["sem_coordenada"] == [] and corpo["complemento_geografico"]["territorios_complementados"] == ["code:421265", "code:422000"]
        assert com_nivel[SC] > com_nivel[RR] >= 1, com_nivel
        todas_com_nivel = str(com_nivel[SC] + com_nivel[RR])
        page.wait_for_timeout(500)
        assert not da_malha, "a malha só é pedida quando o mapa abre"

        # 2. O mapa: dois estados à vista. As divisas dos estados aparecem; as dos municípios, não.
        detector.get_by_test_id("detector-vista-mapa").click()
        mapa = detector.get_by_test_id("detector-mapa")
        expect(mapa).to_have_attribute("data-divisas", "carregadas", timeout=60000)
        divisas = mapa.get_by_test_id("analise-mapa-divisas")
        legenda = mapa.get_by_test_id("detector-mapa-divisas")
        escolha = mapa.get_by_test_id("detector-mapa-aproximar")

        def confere(aproximado, bordas, dentro):
            """O estado em que o mapa está aproximado, as divisas dos municípios e os pontos de cada estado dentro do desenho."""
            expect(mapa).to_have_attribute("data-aproximado", aproximado)
            expect(divisas).to_have_attribute("data-bordas", "true" if bordas else "false")
            expect(divisas.get_by_test_id("analise-mapa-areas-sem-cor")).to_have_count(1 if bordas else 0)
            expect(divisas.get_by_test_id("analise-mapa-divisas-dos-estados")).to_have_count(1)
            # Nada é cortado antes do desenho: as áreas com nível dos dois estados continuam nele, aproximado ou não.
            expect(divisas).to_have_attribute("data-areas-com-cor", todas_com_nivel)
            expect(divisas.get_by_test_id("analise-mapa-area")).to_have_count(int(todas_com_nivel))
            expect(mapa.locator('[data-testid="analise-mapa-ponto"]')).to_have_count(pontos[SC] + pontos[RR])
            assert {prefixo: mapa.evaluate(DENTRO_DO_DESENHO, prefixo) for prefixo in (SC, RR)} == dentro, (aproximado, dentro)
            if bordas:
                expect(legenda).to_contain_text("as divisas dos municípios estão à vista")
            else:
                expect(legenda).not_to_contain_text("as divisas dos municípios estão à vista")

        expect(escolha.locator("option")).to_have_text(["todos os territórios à vista", "RR", "SC"])
        expect(escolha).to_have_value("")
        expect(legenda).to_contain_text("As divisas são as da malha municipal do IBGE: as dos estados ficam sempre à vista")
        confere("", False, {SC: pontos[SC], RR: pontos[RR]})
        page.screenshot(path=str(OUTPUT / "detector-mapa-01-dois-estados-real.png"), full_page=False)

        # 3. Aproximado em Santa Catarina: o mapa enquadra o estado, com as divisas dos municípios dele; Roraima sai do desenho.
        escolha.select_option(SC)
        confere(SC, True, {SC: pontos[SC], RR: 0})
        page.screenshot(path=str(OUTPUT / "detector-mapa-02-aproximado-real.png"), full_page=False)
        # Aproximado em Roraima: o contrário.
        escolha.select_option(RR)
        confere(RR, True, {SC: 0, RR: pontos[RR]})
        # De volta a todos os territórios à vista: as divisas dos municípios saem.
        escolha.select_option("")
        confere("", False, {SC: pontos[SC], RR: pontos[RR]})

        # 4. Com um estado só à vista (a busca deixa só Roraima), as divisas dos municípios aparecem sem aproximar, e a escolha
        # some. O estado escolhido antes (Santa Catarina) deixa de valer quando sai da vista.
        escolha.select_option(SC)
        expect(mapa).to_have_attribute("data-aproximado", SC)
        detector.get_by_test_id("detector-busca").fill("(rr)")
        expect(mapa.locator('[data-testid="analise-mapa-ponto"]')).to_have_count(pontos[RR])
        expect(escolha).to_have_count(0)
        expect(mapa).to_have_attribute("data-aproximado", "")
        expect(divisas).to_have_attribute("data-bordas", "true")
        expect(divisas).to_have_attribute("data-areas-com-cor", str(com_nivel[RR]))
        expect(divisas.get_by_test_id("analise-mapa-areas-sem-cor")).to_have_count(1)
        assert mapa.evaluate(DENTRO_DO_DESENHO, RR) == pontos[RR]
        expect(legenda).to_contain_text("as divisas dos municípios estão à vista")
        detector.get_by_test_id("detector-busca").fill("")
        expect(mapa.locator('[data-testid="analise-mapa-ponto"]')).to_have_count(pontos[SC] + pontos[RR])

        # 5. A malha foi pedida uma vez só: voltar à lista e abrir o mapa de novo não a pede outra vez.
        detector.get_by_test_id("detector-vista-lista").click()
        expect(detector.get_by_test_id("detector-mapa")).to_have_count(0)
        detector.get_by_test_id("detector-vista-mapa").click()
        expect(detector.get_by_test_id("detector-mapa")).to_have_attribute("data-divisas", "carregadas", timeout=60000)
        assert len(da_malha) == 1, da_malha

        # 6. O Brasil inteiro (revisão final do V23, 15/11/2026). Os 5.570 municípios têm ponto: os seis em que a base traz a
        # coordenada fora do intervalo válido ficam com a sede municipal da camada oficial do IBGE, e a legenda diz quais são. As
        # siglas dos 27 estados aparecem sem se sobrepor: a que cobriria outra se afasta (antes, a de Goiás e a do Distrito Federal
        # ficavam uma sobre a outra, e as que cobririam outra, pela largura estimada, não apareciam).
        area.get_by_test_id("analise-aba-territorios").click()
        expect(area).to_have_attribute("data-ferramenta", "")
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
            territorios.get_by_test_id("analise-raiz-caixa").check()
        with page.expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST", timeout=240000) as do_brasil:
            area.get_by_test_id("analise-ferramenta-detector").click()
        assert do_brasil.value.status == 200
        expect(detector).to_have_attribute("data-estado", "pronto", timeout=240000)
        expect(detector.get_by_test_id("detector-tabela")).to_have_attribute("data-linhas", "5570")
        detector.get_by_test_id("detector-vista-mapa").click()
        mapa = detector.get_by_test_id("detector-mapa")
        expect(mapa).to_have_attribute("data-divisas", "carregadas", timeout=60000)
        expect(mapa.locator('[data-testid="analise-mapa-ponto"]')).to_have_count(5570, timeout=120000)
        expect(mapa.get_by_test_id("detector-mapa-fora")).to_have_count(0)
        oficiais = mapa.get_by_test_id("detector-mapa-coordenadas-oficiais")
        expect(oficiais).to_contain_text("Em 6 municípios à vista, o ponto é o da sede municipal, da camada oficial de coordenadas do IBGE, "
                                         "porque a base traz a coordenada deles fora do intervalo válido: ")
        for rotulo in ("ANANAS (TO)", "AGUAS DE LINDOIA (SP)", "PESCARIA BRAVA (SC)", "BALNEARIO RINCAO (SC)", "CAMPESTRE DA SERRA (RS)",
                       "JARAGUARI (MS)"):
            expect(oficiais).to_contain_text(rotulo)
        siglas = mapa.locator('[data-testid="analise-mapa-nome-grupo"]').evaluate_all(
            "nomes => nomes.map(nome => { const caixa = nome.getBBox(); "
            "return [nome.textContent, caixa.x, caixa.y, caixa.x + caixa.width, caixa.y + caixa.height, nome.dataset.deslocado]; })")
        assert sorted(sigla[0] for sigla in siglas) == sorted(
            "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split()), [sigla[0] for sigla in siglas]
        cruzam = [(a[0], b[0]) for posicao, a in enumerate(siglas) for b in siglas[posicao + 1:]
                  if a[1] < b[3] and a[3] > b[1] and a[2] < b[4] and a[4] > b[2]]
        assert not cruzam, cruzam
        deslocada = {sigla[0]: sigla[5] for sigla in siglas}
        assert (deslocada["GO"], deslocada["DF"]) == ("false", "true"), deslocada   # Goiás no centro dos pontos dele; o DF, ao lado
        page.screenshot(path=str(OUTPUT / "detector-mapa-03-brasil-real.png"), full_page=False)
        assert len(da_malha) == 1, da_malha      # a malha continua a mesma: nenhum pedido novo
        assert not chamadas_llm, "o Detector calcula sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("DETECTOR MAPA PASS: Santa Catarina e Roraima à vista, com as divisas dos estados e as áreas pelo nível; \"Aproximar o mapa em\" "
          "enquadra o estado com as divisas dos municípios, sem cortar as áreas com nível; um estado só à vista mostra as divisas dos "
          "municípios sem aproximar; a malha é pedida uma vez, quando o mapa abre; o Brasil inteiro com os 5.570 pontos (seis com a "
          "coordenada da camada oficial) e as siglas dos 27 estados sem sobreposição.")


if __name__ == "__main__":
    main()
