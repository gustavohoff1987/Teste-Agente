"""Simulador de Cenários Territoriais na página única (comando V22, etapas 4 e 5), com a base versionada (somente leitura).

Confere, contra as respostas de POST /api/simulador:
- a ferramenta na navegação principal ("Simulador de Cenários"), que sem territórios não pede nada ao motor;
- a seleção local: uma cópia da seleção principal, em que acrescentar (um município e um estado como unidade) e tirar
  territórios não muda a seleção principal; "Copiar de novo a seleção principal" e "Aplicar à seleção principal", que só então
  muda a seleção principal, num passo do Desfazer;
- as quatro etapas: os territórios, a base histórica e o método (a janela padrão de 3 anos e o método padrão provisório), as
  intervenções e a data final (qualquer mês; os atalhos são só atalhos) e os resultados, só depois de "Calcular os cenários";
- os resultados de RIO RUFINO (SC), de BRASILIA (DF) e do Paraná como unidade: o texto fixo de cenário vindo do motor, o gráfico
  com o observado, a base do cenário, a intervenção e a faixa de 80% (só no método padrão dos municípios), o aviso do pico fora
  do ajuste, o estado sem faixa e a persistência como referência;
- o modo avançado, com um segundo cenário; a retirada acima do estoque, devolvida para revisão; as estatísticas históricas, com
  a média aritmética só descritiva; a validação dos métodos; as exportações (CSV dos resultados e JSON do cenário) e a
  importação do cenário;
- da etapa 5: "Abrir no Simulador", no Detector de Sinais, que traz MANAUS (AM) com o contexto analítico sem mudar a seleção
  principal; o Brasil como território, só no Simulador; as referências de comparação (FLORIANOPOLIS dinâmica, o Brasil fixo e um
  valor informado), com as curvas no gráfico, os textos do motor, "não alcança no horizonte simulado" e o aviso de sobreposição;
  o CSV das comparações; e o planejamento inverso, com a meta hipotética, o menor inteiro por evento e o plano usado como
  intervenção, que recalculado alcança a meta;
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, TEFE, RIO_RUFINO, BRASILIA, PR = "code:130260", "code:130420", "code:421505", "code:530010", "41"
FLORIANOPOLIS = "code:420540"
FIXO = "Cenário hipotético, não é previsão: "


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
        page.on("request", lambda request: pedidos.append(request) if request.url.endswith("/api/simulador") else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        botao = area.get_by_test_id("analise-ferramenta-simulador")
        simulador = area.get_by_test_id("simulador")
        resumo = area.get_by_test_id("analise-aba-territorios-resumo")

        def do_simulador(acao):
            """A resposta de /api/simulador que a ação provocou e as opções do pedido."""
            with page.expect_response(lambda r: r.url.endswith("/api/simulador") and r.request.method == "POST", timeout=180000) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        def local(codigo):
            return simulador.locator('[data-testid="simulador-local"][data-id="' + codigo + '"]')

        def marcar_na_arvore(nome, codigo):
            territorios.get_by_test_id("analise-busca").fill(nome)
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=180000):
                territorios.locator('[data-testid="analise-busca-item"][data-id="' + codigo + '"] input').check()

        def acrescentar(nome, alvo):
            simulador.get_by_test_id("simulador-busca").fill(nome)
            simulador.locator('[data-testid="simulador-acrescentar"][data-id="' + alvo + '"]').click()

        def do_territorio(corpo, codigo):
            return next(item for item in corpo["territorios"] if item["id"] == codigo)

        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. A ferramenta fica na navegação principal; sem territórios, a cópia local é vazia e nada é pedido ao motor.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
        expect(botao).to_be_enabled()
        expect(botao).to_have_text("Simulador de Cenários")
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        expect(simulador.get_by_test_id("simulador-titulo")).to_have_text("Simulador de Cenários Territoriais")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "0")
        expect(simulador.get_by_test_id("simulador-data")).to_contain_text("O registro mais recente da base é jun/2024")
        expect(simulador.get_by_test_id("simulador-data")).to_contain_text("simulado, nunca observado")
        expect(simulador.get_by_test_id("simulador-distancia")).to_contain_text("(há ")  # a distância entre o último registro e hoje
        expect(simulador.get_by_test_id("simulador-avancar-1")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-calcular-direto")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-etapa-4")).to_be_disabled()
        page.wait_for_timeout(400)
        assert not pedidos, "sem territórios e sem o comando de calcular, nada é pedido ao motor"
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "")

        # 2. A seleção principal: MANAUS (AM) e RIO RUFINO (SC). O Simulador abre com a cópia dela.
        marcar_na_arvore("manaus", MANAUS)
        marcar_na_arvore("rio rufino", RIO_RUFINO)
        # A busca pelo nome anterior continua achando o município (13/11/2026): "Parati" acha PARATY (RJ), com o nome atual.
        territorios.get_by_test_id("analise-busca").fill("Parati")
        expect(territorios.locator('[data-testid="analise-busca-item"][data-id="code:330380"]')).to_contain_text("PARATY")
        territorios.get_by_test_id("analise-busca").fill("")
        principal = resumo.inner_text()
        botao.click()
        # A cópia ainda não foi alterada no Simulador: ela acompanha a seleção principal.
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "2")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "true")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_have_count(0)
        expect(local(MANAUS)).to_contain_text("MANAUS (AM)")
        expect(local(RIO_RUFINO)).to_contain_text("RIO RUFINO (SC)")

        # 3. Acrescentar e tirar territórios só no Simulador: a seleção principal não muda, e a seleção local deixa de acompanhá-la.
        acrescentar("brasilia", BRASILIA)
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "false")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_contain_text("só do Simulador")
        # Perto de "Copiar de novo a seleção principal", a tela diz que a cópia deixou de acompanhar a seleção principal.
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_contain_text("deixou de acompanhar a seleção principal")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_contain_text("Copiar de novo a seleção principal")
        acrescentar("parana", "uf:" + PR)
        expect(local("uf:" + PR)).to_contain_text("Paraná (estado)")
        local(MANAUS).get_by_role("button").click()
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "3")
        expect(local(MANAUS)).to_have_count(0)
        # O estado inteiro e os municípios dele não entram juntos: com o Paraná como unidade, CURITIBA (PR) é recusada, com o motivo.
        acrescentar("curitiba", "code:410690")
        expect(simulador.get_by_test_id("simulador-aviso-local")).to_contain_text("O estado deste município está na seleção como unidade")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "3")
        simulador.get_by_test_id("simulador-busca").fill("")
        expect(resumo).to_have_text(principal)
        assert not pedidos, "montar a seleção local não pede nada ao motor"

        # 4. A base histórica e o método: a janela padrão (3 anos até o último registro) e o método padrão provisório.
        simulador.get_by_test_id("simulador-avancar-1").click()
        expect(simulador).to_have_attribute("data-etapa", "2")
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("202106")
        expect(simulador.get_by_test_id("simulador-janela-fim")).to_have_value("202406")
        expect(simulador.get_by_test_id("simulador-metodo")).to_have_value("padrao")
        assert simulador.get_by_test_id("simulador-metodo").locator("option").evaluate_all("els => els.map(e => e.value)") == [
            "padrao", "M0", "M1", "M2", "M3", "manual"], "a média aritmética não é um método"
        expect(simulador.get_by_test_id("simulador-base")).to_contain_text("5 e 7 meses entre um e outro")
        expect(simulador.get_by_test_id("simulador-estatisticas-depois")).to_contain_text("aparecem aqui depois de calcular")
        # Os atalhos da janela são só atalhos: a série completa e a volta à janela padrão.
        simulador.get_by_test_id("simulador-janela-completa").click()
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("201401")
        simulador.get_by_test_id("simulador-janela-padrao").click()
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("202106")

        # 5. As intervenções e a data final: os atalhos são só atalhos; qualquer mês depois do último registro vale.
        simulador.get_by_test_id("simulador-avancar-2").click()
        horizonte = simulador.get_by_test_id("simulador-horizonte")
        expect(horizonte).to_have_value("2026-06")
        simulador.get_by_test_id("simulador-atalho-4").click()
        expect(horizonte).to_have_value("2028-06")
        expect(simulador.get_by_test_id("simulador-atalho-4")).to_have_attribute("aria-pressed", "true")
        horizonte.fill("2027-03")
        expect(simulador.get_by_test_id("simulador-atalho-4")).to_have_attribute("aria-pressed", "false")
        # A intervenção vale para cada território do cenário (cada um recebe a quantidade inteira), e a tela diz isso.
        expect(simulador.get_by_test_id("simulador-por-territorio")).to_contain_text("Cada intervenção vale para cada território do cenário, não para o total")
        expect(simulador.get_by_test_id("simulador-por-territorio")).to_contain_text("com 3 territórios na seleção do Simulador")
        simulador.get_by_test_id("simulador-intervencao-nova").click()
        expect(simulador.get_by_test_id("simulador-intervencao-em")).to_have_value("2025-06")
        expect(simulador.get_by_test_id("simulador-intervencao-permanencia")).to_have_value("100")
        simulador.get_by_test_id("simulador-intervencao-quantidade").fill("")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe quantos médicos entram ou saem em cada intervenção.")
        simulador.get_by_test_id("simulador-intervencao-quantidade").fill("3")
        assert not pedidos, "nada é calculado antes de \"Calcular os cenários\""

        # 6. "Calcular os cenários": o pedido leva a seleção local, a data final, o cenário e a persistência como referência.
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
        assert enviado == {
            "base": {"municipios": {"todos": False, "estados": [], "ids": [RIO_RUFINO, BRASILIA]}}, "estados_unidade": [PR], "horizonte": "202703",
            "cenarios": [{"id": "c1", "nome": "Cenário 1", "metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 3, "em": "202506"}]},
                         {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == [RIO_RUFINO, BRASILIA, "uf:" + PR], corpo["territorios"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(simulador).to_have_attribute("data-etapa", "4")
        expect(simulador.get_by_test_id("simulador-linha")).to_have_count(3)
        rufino = do_territorio(corpo, RIO_RUFINO)
        cenario, referencia = rufino["cenarios"]
        assert cenario["metodo"]["usado"] == "M0d" and cenario["final"]["intervencao"] == 3 and cenario["texto"].startswith(FIXO), cenario
        assert "acréscimo de 3 médicos em cada território do cenário, em jun/2025, com permanência total (hipótese)" in cenario["texto"], cenario["texto"]
        assert all(item["cenarios"][0]["final"]["intervencao"] == 3 for item in corpo["territorios"]), "cada território recebe os 3 médicos"
        assert cenario["final"]["faixa"] and cenario["final"]["faixa"]["anos"] == 3 and cenario["final"]["faixa"]["validada"] is False, cenario["final"]
        expect(simulador.get_by_test_id("simulador-foco")).to_have_value(RIO_RUFINO)
        resultado = simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="c1"]')
        expect(resultado).to_have_attribute("data-metodo", "M0d")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("RIO RUFINO (SC) teria")
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("Base: registros até jun/2024.")
        expect(resultado).to_contain_text("método provisório")
        expect(resultado.get_by_test_id("simulador-contas")).to_contain_text("Na data final, neste território: base do cenário de ")
        expect(resultado.get_by_test_id("simulador-contas")).to_contain_text(" + 3 da intervenção = ")
        expect(simulador.get_by_test_id("simulador-tabela").locator("caption")).to_contain_text("Cada intervenção vale para cada território")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 80% em mar/2027: de ")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Limite provisório")
        # O registro de jun/2023 (4 → 87 → 5) é um pico que volta: fica fora da base do cenário, com o aviso.
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="PICO_FORA_DO_AJUSTE"]')).to_contain_text("jun/2023")
        expect(simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="m0"] [data-testid="simulador-texto"]')).to_have_text(
            referencia["texto"])
        # O gráfico: o observado (22 registros reais), a base de cada cenário, os eventos da intervenção e a faixa de 80%.
        grafico = simulador.get_by_test_id("simulador-grafico")
        expect(grafico.get_by_test_id("simulador-observado")).to_have_count(22)
        expect(grafico.get_by_test_id("simulador-curva")).to_have_count(2)
        expect(grafico.locator('[data-testid="simulador-curva"][data-cenario="c1"]')).to_have_attribute("data-metodo", "M0d")
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(1)
        expect(grafico.get_by_test_id("simulador-faixa")).to_have_count(1)
        expect(grafico).to_contain_text("observado (registros reais)")
        expect(grafico).to_contain_text("Fonte: base do Brasil (medicina), registros de janeiro e junho até jun/2024.")
        expect(simulador.get_by_test_id("simulador-versoes")).to_contain_text("Método " + corpo["versao"])
        expect(simulador.get_by_test_id("simulador-versoes")).to_contain_text("último registro da base: jun/2024")
        expect(grafico.locator("svg").first).to_contain_text("simulado (hipótese)")
        linha = simulador.locator('[data-testid="simulador-linha"][data-id="' + RIO_RUFINO + '"]')
        expect(linha.locator('[data-testid="simulador-final"][data-cenario="c1"]')).to_contain_text("último valor com o crescimento do estado")
        expect(linha.locator('[data-testid="simulador-final"][data-cenario="m0"]')).to_contain_text("último valor mantido")
        page.screenshot(path=str(OUTPUT / "simulador-01-resultados-real.png"), full_page=True)

        # 7. O Paraná como unidade: o padrão provisório do nível (a taxa composta de 3 anos), sem faixa.
        simulador.get_by_test_id("simulador-foco").select_option("uf:" + PR)
        expect(resultado).to_have_attribute("data-metodo", "M1")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(do_territorio(corpo, "uf:" + PR)["cenarios"][0]["texto"])
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 80%: indisponível")
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="PADRAO_PROVISORIO_DO_NIVEL"]')).to_have_count(1)
        expect(grafico.get_by_test_id("simulador-faixa")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-resultados")).to_contain_text("médicos únicos no estado")

        # 8. As estatísticas históricas, só descritivas: a média aritmética aparece, e nenhum método a usa.
        simulador.get_by_test_id("simulador-foco").select_option(BRASILIA)
        simulador.get_by_test_id("simulador-etapa-2").click()
        estatisticas = simulador.get_by_test_id("simulador-estatisticas")
        expect(estatisticas).to_contain_text("Estatísticas históricas de BRASILIA (DF) (só descrição do passado)")
        expect(estatisticas.get_by_test_id("simulador-media-aritmetica")).not_to_have_text("—")
        expect(estatisticas).to_contain_text("por isso não é usada para projetar")

        # 9. O modo avançado: um segundo cenário, com a taxa composta da janela. Mudar as escolhas deixa o cálculo desatualizado.
        simulador.get_by_test_id("simulador-modo-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        simulador.get_by_test_id("simulador-cenario-novo").click()
        expect(simulador.get_by_test_id("simulador-cenario")).to_have_count(2)
        simulador.get_by_test_id("simulador-metodo").nth(1).select_option("M1")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        # A retirada impossível: 50 médicos de RIO RUFINO (5 em jun/2024) passam do estoque; o cenário volta para revisão.
        simulador.get_by_test_id("simulador-etapa-3").click()
        primeiro = simulador.get_by_test_id("simulador-intervencoes").first
        primeiro.get_by_test_id("simulador-intervencao-tipo").select_option("retirada")
        primeiro.get_by_test_id("simulador-intervencao-quantidade").fill("50")
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
        assert [item["id"] for item in enviado["cenarios"]] == ["c1", "c2", "m0"] and enviado["cenarios"][1]["metodo"] == "M1", enviado
        assert enviado["cenarios"][0]["intervencoes"] == [{"tipo": "retirada", "quantidade": 50, "em": "202506"}], enviado
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(simulador.get_by_test_id("simulador-tabela").locator("thead th")).to_have_text(
            ["Território", "Último registro usável", "Cenário 1", "Cenário 2", "Persistência (referência)"])
        impossivel = simulador.locator('[data-testid="simulador-linha"][data-id="' + RIO_RUFINO + '"] [data-testid="simulador-final"][data-cenario="c1"]')
        expect(impossivel).to_have_attribute("data-estado", "retirada_acima_do_estoque")
        expect(impossivel).to_have_text("retirada acima do estoque: rever")
        possivel = simulador.locator('[data-testid="simulador-linha"][data-id="' + BRASILIA + '"] [data-testid="simulador-final"][data-cenario="c1"]')
        expect(possivel).to_have_attribute("data-estado", "calculado")
        simulador.get_by_test_id("simulador-foco").select_option(RIO_RUFINO)
        expect(resultado).to_have_attribute("data-estado", "retirada_acima_do_estoque")
        expect(resultado.get_by_test_id("simulador-motivo")).to_contain_text("Nenhum estoque negativo é aceito")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_count(0)
        expect(grafico.locator('[data-testid="simulador-curva"][data-cenario="c2"]')).to_have_attribute("data-metodo", "M1")
        page.screenshot(path=str(OUTPUT / "simulador-02-avancado-real.png"), full_page=True)

        # 10. "Como os métodos se saíram no passado": as faixas e os erros da retroprojeção, por porte.
        simulador.get_by_test_id("simulador-validacao-botao").click()
        faixas = simulador.get_by_test_id("simulador-faixas")
        expect(faixas.locator("tbody tr")).to_have_count(6)
        expect(faixas.locator("tbody tr").first.locator("td").first).to_contain_text("−26% a +48%")
        expect(simulador.get_by_test_id("simulador-erros").locator("tbody tr")).to_have_count(6)
        expect(simulador.get_by_test_id("simulador-erros").locator("tbody tr").first.locator("td").first).to_have_text("0,87")
        expect(simulador.get_by_test_id("simulador-validacao")).to_contain_text("não são previsão")

        # 11. As exportações: o CSV dos resultados e o JSON do cenário (com a versão do método e da base).
        with page.expect_download() as baixado:
            simulador.get_by_test_id("simulador-exportar-csv").click()
        assert baixado.value.suggested_filename == "cenarios_202703.csv", baixado.value.suggested_filename
        csv = Path(baixado.value.path()).read_text(encoding="utf-8-sig")
        assert csv.startswith("Identificador;Território;Tipo;Unidade de contagem;Cenário;") and "retirada_acima_do_estoque" in csv, csv[:300]
        assert RIO_RUFINO + ";RIO RUFINO (SC);municipio;" in csv and ";cenário hipotético;" in csv, csv[:600]
        with page.expect_download() as baixado:
            simulador.get_by_test_id("simulador-exportar-cenario").click()
        assert baixado.value.suggested_filename == "cenario_do_simulador.json"
        arquivo = OUTPUT / "simulador-cenario-exportado.json"
        baixado.value.save_as(str(arquivo))
        exportado = json.loads(arquivo.read_text(encoding="utf-8"))
        assert exportado["formato"] == "ADT-CENARIO/1" and exportado["versao_do_metodo"] == corpo["versao"], exportado
        assert exportado["base"]["versao"] and exportado["base"]["ultimo_registro"] == "202406", exportado["base"]
        assert exportado["selecao_local"] == {"municipios": [RIO_RUFINO, BRASILIA], "estados": [PR], "conjuntos": []}, exportado["selecao_local"]
        assert [item["id"] for item in exportado["cenarios"]] == ["c1", "c2"] and exportado["horizonte"] == "202703", exportado

        # 11b. Um cenário importado com um conjunto (MANAUS e TEFE): na tabela, o conjunto é a "soma das projeções dos membros", e a
        # faixa dele é rotulada como aproximação (a dos municípios com o porte da soma).
        com_conjunto = OUTPUT / "simulador-cenario-com-conjunto.json"
        com_conjunto.write_text(json.dumps({**exportado, "selecao_local": {**exportado["selecao_local"], "conjuntos": [
            {"id": "g1", "rotulo": "Manaus e Tefé", "membros": [MANAUS, TEFE], "versao": 1}]}}, ensure_ascii=False), encoding="utf-8")
        simulador.get_by_test_id("simulador-etapa-1").click()
        simulador.get_by_test_id("simulador-arquivo").set_input_files(str(com_conjunto))
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "4")
        expect(local("g1")).to_contain_text("Manaus e Tefé (conjunto de 2)")
        simulador.get_by_test_id("simulador-composicao-botao").click()
        expect(simulador.get_by_test_id("simulador-composicao")).to_contain_text("Manaus e Tefé (versão 1): MANAUS (AM), TEFE (AM).")
        corpo_g, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
        assert enviado["conjuntos"] == [{"id": "g1", "rotulo": "Manaus e Tefé", "membros": [MANAUS, TEFE], "versao": 1}], enviado
        do_conjunto = do_territorio(corpo_g, "g1")
        assert do_conjunto["cenarios"][0]["metodo"]["soma"] == "soma das projeções dos membros", do_conjunto["cenarios"][0]["metodo"]
        assert do_conjunto["cenarios"][0]["faixa"]["rotulo"].startswith("aproximação"), do_conjunto["cenarios"][0]["faixa"]
        linha_g = simulador.locator('[data-testid="simulador-linha"][data-id="g1"]')
        usado = '[data-testid="simulador-final"][data-cenario="{}"] [data-testid="simulador-metodo-usado"]'
        expect(linha_g.locator(usado.format("c1"))).to_have_text("soma das projeções dos membros (cada um com o crescimento do seu estado)")
        expect(linha_g.locator(usado.format("c2"))).to_have_text("soma das contagens dos componentes · taxa composta da janela")
        expect(linha_g.locator(usado.format("m0"))).to_have_text("soma das projeções dos membros (cada um no último valor)")
        expect(linha_g.locator('[data-testid="simulador-final"][data-cenario="c1"]')).to_contain_text(", aproximação)")
        simulador.get_by_test_id("simulador-foco").select_option("g1")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(do_conjunto["cenarios"][0]["texto"])
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("Manaus e Tefé (soma das projeções dos membros) teria")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 80% (aproximação) em mar/2027: de ")
        expect(grafico).to_contain_text("banda: faixa de 80% (aproximação)")
        expect(simulador.get_by_test_id("simulador-resultados")).to_contain_text("soma das contagens dos componentes")
        page.screenshot(path=str(OUTPUT / "simulador-03-conjunto-real.png"), full_page=True)

        # 12. "Copiar de novo a seleção principal" refaz a cópia; importar o cenário exportado traz a seleção local e os cenários de volta.
        simulador.get_by_test_id("simulador-etapa-1").click()
        simulador.get_by_test_id("simulador-copiar-principal").click()
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "2")
        expect(local(MANAUS)).to_have_count(1)
        simulador.get_by_test_id("simulador-arquivo").set_input_files(str(arquivo))
        expect(simulador.get_by_test_id("simulador-aviso-local")).to_contain_text("Cenário importado: confira e calcule.")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(simulador).to_have_attribute("data-modo", "avancado")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "3")
        expect(local("uf:" + PR)).to_have_count(1)
        expect(local(MANAUS)).to_have_count(0)
        expect(resumo).to_have_text(principal)

        # 13. "Aplicar à seleção principal": só agora a seleção principal muda, num passo do Desfazer.
        simulador.get_by_test_id("simulador-aplicar-principal").click()
        expect(simulador.get_by_test_id("simulador-aviso-local")).to_have_text("A seleção do Simulador foi aplicada à seleção principal.")
        expect(resumo).not_to_have_text(principal)
        expect(resumo).to_contain_text("Paraná")
        area.get_by_test_id("analise-desfazer").click()
        expect(resumo).to_have_text(principal)
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "3")  # o Desfazer não mexe na seleção local

        # 14. "Abrir no Simulador" (etapa 5): do Detector de Sinais, MANAUS (AM) vai ao Simulador com o contexto analítico (o
        # território, a data avaliada e os sinais à vista). A seleção local fica só com ele e não acompanha a seleção principal,
        # que não muda. Manaus está acima do patamar anterior: não há "Simular recuperação" para ele.
        area.get_by_test_id("analise-ferramenta-detector").click()
        detector = area.get_by_test_id("detector")
        expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
        with page.expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST", timeout=180000):
            detector.locator('[data-testid="detector-linha"][data-id="' + MANAUS + '"]').get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", MANAUS)
        expect(detector.get_by_test_id("detector-simular-recuperacao")).to_have_count(0)
        detector.get_by_test_id("detector-abrir-no-simulador").click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        expect(simulador).to_have_attribute("data-etapa", "1")
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        aviso = simulador.get_by_test_id("simulador-do-detector")
        expect(aviso).to_have_attribute("data-recuperacao", "false")
        expect(aviso).to_contain_text("Aberto pelo Detector de Sinais: MANAUS (AM), avaliado em jun/2024")
        expect(aviso).to_contain_text("Sem sinais à vista lá.")
        expect(aviso).to_contain_text("o que vem depois do último registro é cenário hipotético")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "1")
        expect(local(MANAUS)).to_have_count(1)
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "false")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_contain_text("veio do Detector de Sinais")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_contain_text("não acompanha a seleção principal")
        expect(resumo).to_have_text(principal)

        # 15. O Brasil como território, só no Simulador (a contagem nacional), e as referências de comparação: FLORIANOPOLIS (SC),
        # dinâmica; o Brasil, fixo; e um valor informado. Elas podem ficar fora da seleção do Simulador e não mudam a principal.
        acrescentar("brasil", "br")
        expect(local("br")).to_contain_text("Brasil (contagem nacional)")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "2")
        simulador.get_by_test_id("simulador-busca").fill("")
        referencias = simulador.get_by_test_id("simulador-referencias")
        expect(referencias).to_have_attribute("data-total", "0")
        expect(simulador.get_by_test_id("simulador-metrica")).to_have_count(0)

        def da_lista(alvo):
            return simulador.locator('[data-testid="simulador-referencia-item"][data-alvo="' + alvo + '"]')
        simulador.get_by_test_id("simulador-referencia-busca").fill("florian")
        simulador.locator('[data-testid="simulador-referencia-acrescentar"][data-id="' + FLORIANOPOLIS + '"]').click()
        expect(da_lista(FLORIANOPOLIS)).to_have_attribute("data-tipo", "fixa")
        da_lista(FLORIANOPOLIS).get_by_test_id("simulador-referencia-tipo").select_option("dinamica")
        expect(da_lista(FLORIANOPOLIS)).to_have_attribute("data-tipo", "dinamica")
        simulador.get_by_test_id("simulador-referencia-brasil").click()
        simulador.get_by_test_id("simulador-referencia-brasil").click()
        expect(simulador.get_by_test_id("simulador-referencia-aviso")).to_have_text("Esta referência já está na lista.")
        simulador.get_by_test_id("simulador-referencia-valor-nova").click()
        expect(simulador.get_by_test_id("simulador-calcular-direto")).to_be_disabled()   # falta o valor da referência
        simulador.get_by_test_id("simulador-referencia-valor").fill("6.500")
        expect(referencias).to_have_attribute("data-total", "3")
        expect(simulador.get_by_test_id("simulador-metrica")).to_have_value("quantidade")
        expect(simulador.get_by_test_id("simulador-metrica-apoio")).to_contain_text("não é comparar a suficiência do atendimento")
        expect(resumo).to_have_text(principal)
        simulador.get_by_test_id("simulador-etapa-3").click()
        simulador.get_by_test_id("simulador-atalho-4").click()
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
        assert enviado == {
            "base": {"municipios": {"todos": False, "estados": [], "ids": [MANAUS]}}, "brasil": True, "horizonte": "202806",
            "cenarios": [{"id": "c1", "nome": "Cenário 1", "metodo": "padrao"}, {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}],
            "referencias": [{"id": "r1", "tipo": "dinamica", "territorio": FLORIANOPOLIS}, {"id": "r2", "tipo": "fixa", "territorio": "br"},
                            {"id": "r3", "tipo": "valor", "valor": 6500, "rotulo": "Valor informado por você"}]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == [MANAUS, "br"], corpo["territorios"]
        assert corpo["comparacao"] == {"metrica": "quantidade", "hipotese_de_populacao": None}, corpo["comparacao"]
        de_manaus = do_territorio(corpo, MANAUS)["cenarios"][0]
        comparacoes = {item["id"]: item for item in de_manaus["comparacoes"]}
        # Sem cruzamento no horizonte: "não alcança no horizonte simulado", sem data inventada.
        assert all(item["alcance"] == {"estado": "nao_alcanca", "data": None} for item in comparacoes.values()), comparacoes
        expect(simulador.get_by_test_id("simulador-foco")).to_have_value(MANAUS)

        def da_comparacao(chave):
            return resultado.locator('[data-testid="simulador-comparacao"][data-ref="' + chave + '"]')
        expect(resultado.get_by_test_id("simulador-comparacao")).to_have_count(3)
        for chave in ("r1", "r2", "r3"):
            expect(da_comparacao(chave)).to_have_attribute("data-alcance", "nao_alcanca")
            expect(da_comparacao(chave)).to_contain_text(comparacoes[chave]["texto"])
        expect(da_comparacao("r1")).to_contain_text("Não alcança no horizonte simulado (até jun/2028).")
        expect(da_comparacao("r2").get_by_test_id("simulador-comparacao-aviso").first).to_have_text(
            "A referência (Brasil) contém o território: a comparação não é independente.")
        expect(resultado.get_by_test_id("simulador-hipotetico")).to_have_count(0)   # com milhares de médicos, a escala não tem o que dizer
        # No gráfico, as curvas das referências que cabem na escala; a do Brasil fica na legenda, fora da escala.
        expect(grafico.get_by_test_id("simulador-referencia")).to_have_count(2)
        expect(grafico.locator('[data-testid="simulador-referencia-legenda"][data-ref="r1"]')).to_contain_text(
            "R1: referência FLORIANOPOLIS (SC) (dinâmica: ")
        do_brasil_na_legenda = grafico.locator('[data-testid="simulador-referencia-legenda"][data-ref="r2"]')
        expect(do_brasil_na_legenda).to_have_attribute("data-na-escala", "false")
        expect(do_brasil_na_legenda).to_contain_text("fora da escala deste gráfico (502.495 médicos na data final)")
        expect(simulador.get_by_test_id("simulador-referencias-do-calculo")).to_contain_text("comparadas por quantidade de médicos")
        page.screenshot(path=str(OUTPUT / "simulador-04-referencias-real.png"), full_page=True)
        # O Brasil no gráfico: o padrão provisório do nível (a taxa composta de 3 anos na contagem nacional), sem faixa.
        simulador.get_by_test_id("simulador-foco").select_option("br")
        do_brasil = do_territorio(corpo, "br")["cenarios"][0]
        assert do_brasil["metodo"]["usado"] == "M1" and do_brasil["final"]["faixa"] is None and "hipotetico" not in do_brasil, do_brasil["metodo"]
        expect(resultado).to_have_attribute("data-metodo", "M1")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(do_brasil["texto"])
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="PADRAO_PROVISORIO_DO_NIVEL"]')).to_contain_text(
            "Para o Brasil, o método padrão é provisório")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 80%: indisponível")
        expect(simulador.get_by_test_id("simulador-resultados")).to_contain_text("médicos únicos no Brasil (fonte nacional)")
        expect(da_comparacao("r2")).to_contain_text("A referência é o próprio território.")
        with page.expect_download() as baixado:
            simulador.get_by_test_id("simulador-exportar-comparacoes").click()
        assert baixado.value.suggested_filename == "comparacoes_202806.csv", baixado.value.suggested_filename
        csv = Path(baixado.value.path()).read_text(encoding="utf-8-sig")
        assert csv.startswith("Identificador;Território;Cenário;Referência;Tipo da referência;O que é a referência;Métrica;Data;"), csv[:300]
        assert "não alcança no horizonte simulado" in csv and "já está no nível da referência ou acima na origem" in csv, csv[:900]

        # 16. O planejamento inverso: a meta hipotética de alcançar a referência (FLORIANOPOLIS), com um acréscimo por ano. O motor
        # devolve o menor número inteiro de médicos por evento; o cenário só o recebe por comando ("Usar como intervenção deste
        # cenário") e, recalculado, alcança a meta.
        simulador.get_by_test_id("simulador-etapa-1").click()
        local("br").get_by_role("button").click()
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "1")
        simulador.get_by_test_id("simulador-etapa-3").click()
        simulador.get_by_test_id("simulador-plano-novo").click()
        plano = simulador.get_by_test_id("simulador-plano")
        expect(plano).to_have_attribute("data-meta", "valor")
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe a meta do planejamento inverso, em médicos.")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        plano.get_by_test_id("simulador-plano-meta").select_option("referencia")
        expect(plano.get_by_test_id("simulador-plano-referencia")).to_have_value("r1")
        expect(plano.get_by_test_id("simulador-plano-em")).to_have_value("2025-06")
        plano.get_by_test_id("simulador-plano-periodica").check()
        expect(plano.get_by_test_id("simulador-plano-ate")).to_have_value("2027-06")
        plano.get_by_test_id("simulador-plano-ate").fill("2028-06")
        expect(plano).to_contain_text("não um plano")
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
        assert "brasil" not in enviado and enviado["cenarios"][0] == {"id": "c1", "nome": "Cenário 1", "metodo": "padrao", "planejamento": {
            "meta": {"tipo": "referencia", "referencia": "r1"}, "em": "202506", "ate": "202806", "a_cada_meses": 12}}, enviado
        de_manaus = do_territorio(corpo, MANAUS)["cenarios"][0]
        planejado = de_manaus["planejamento"]
        assert (planejado["estado"], planejado["eventos"], planejado["por_evento"], planejado["total"]) == ("calculado", 4, 387, 1548), planejado
        assert planejado["texto"].startswith("Meta hipotética: alcançar a referência FLORIANOPOLIS (SC)") and planejado["texto"].endswith(
            "É uma conta condicional às hipóteses do cenário, não um plano."), planejado["texto"]
        for proibida in ("recomenda", "é preciso", "deveria", "necessário prover"):
            assert proibida not in planejado["texto"].lower(), proibida
        assert de_manaus["final"]["intervencao"] == 0, "o acréscimo planejado só entra no cenário por comando"
        bloco = resultado.get_by_test_id("simulador-planejamento")
        expect(bloco).to_have_attribute("data-estado", "calculado")
        expect(bloco).to_have_attribute("data-por-evento", "387")
        expect(bloco).to_have_attribute("data-eventos", "4")
        expect(bloco.get_by_test_id("simulador-planejamento-texto")).to_have_text(planejado["texto"])
        expect(bloco).to_contain_text("conta condicional")
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(0)
        page.screenshot(path=str(OUTPUT / "simulador-05-planejamento-real.png"), full_page=True)
        bloco.get_by_test_id("simulador-planejamento-usar").click()
        expect(simulador).to_have_attribute("data-etapa", "3")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        expect(simulador.get_by_test_id("simulador-plano")).to_have_attribute("data-ativo", "false")
        expect(simulador.get_by_test_id("simulador-intervencao")).to_have_count(1)
        expect(simulador.get_by_test_id("simulador-intervencao-quantidade")).to_have_value("387")
        expect(simulador.get_by_test_id("simulador-intervencao-periodica")).to_be_checked()
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
        assert enviado["cenarios"][0] == {"id": "c1", "nome": "Cenário 1", "metodo": "padrao", "intervencoes": [
            {"tipo": "acrescimo", "quantidade": 387, "em": "202506", "ate": "202806", "a_cada_meses": 12}]}, enviado
        aplicado = do_territorio(corpo, MANAUS)["cenarios"][0]
        assert abs(aplicado["final"]["total"] - planejado["resultado"]) < 1e-6 and aplicado["final"]["total"] >= planejado["meta"]["valor"], aplicado["final"]
        da_meta = next(item for item in aplicado["comparacoes"] if item["id"] == "r1")
        assert da_meta["alcance"] == {"estado": "alcanca", "data": "202806"}, da_meta["alcance"]
        expect(da_comparacao("r1")).to_have_attribute("data-alcance", "alcanca")
        expect(da_comparacao("r1")).to_contain_text("No cenário, alcança a referência em jun/2028")
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(4)
        expect(resultado.get_by_test_id("simulador-planejamento")).to_have_count(0)
        expect(resumo).to_have_text(principal)

        assert not chamadas_llm, "o Simulador calcula sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("SIMULADOR PASS: ferramenta na navegação sem pedido antes de Calcular, seleção local (cópia, acréscimo de BRASILIA e do Paraná "
          "como unidade, retirada de MANAUS e recusa de CURITIBA) sem mudar a seleção principal, janela e método padrão, data final em "
          "qualquer mês, cenário com acréscimo (texto fixo do motor, gráfico com observado, base, evento e faixa; pico fora do ajuste em "
          "RIO RUFINO), Paraná sem faixa, estatísticas descritivas, modo avançado com dois cenários, retirada acima do estoque, validação "
          "dos métodos, exportações CSV e JSON, importação do cenário, cópia de novo e Aplicar à seleção principal com Desfazer; "
          "Abrir no Simulador com o contexto do Detector, o Brasil como território, três referências (curvas, textos, não alcança no "
          "horizonte e sobreposição), CSV das comparações e planejamento inverso (387 médicos em 4 eventos), usado como intervenção.")


if __name__ == "__main__":
    main()
