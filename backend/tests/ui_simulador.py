"""Simulador de Cenários Territoriais na página única (comando V22, etapa 4), com a base versionada (somente leitura).

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
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import json
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, RIO_RUFINO, BRASILIA, PR = "code:130260", "code:421505", "code:530010", "41"
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
        territorios.get_by_test_id("analise-busca").fill("")
        principal = resumo.inner_text()
        botao.click()
        # A cópia ainda não foi alterada no Simulador: ela acompanha a seleção principal.
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "2")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "true")
        expect(local(MANAUS)).to_contain_text("MANAUS (AM)")
        expect(local(RIO_RUFINO)).to_contain_text("RIO RUFINO (SC)")

        # 3. Acrescentar e tirar territórios só no Simulador: a seleção principal não muda, e a seleção local deixa de acompanhá-la.
        acrescentar("brasilia", BRASILIA)
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "false")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_contain_text("só do Simulador")
        acrescentar("parana", "uf:" + PR)
        expect(local("uf:" + PR)).to_contain_text("Paraná (PR) (estado)")
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
        assert cenario["final"]["faixa"] and cenario["final"]["faixa"]["anos"] == 3 and cenario["final"]["faixa"]["validada"] is False, cenario["final"]
        expect(simulador.get_by_test_id("simulador-foco")).to_have_value(RIO_RUFINO)
        resultado = simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="c1"]')
        expect(resultado).to_have_attribute("data-metodo", "M0d")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("RIO RUFINO (SC) teria")
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("Base: registros até jun/2024.")
        expect(resultado).to_contain_text("método provisório")
        expect(resultado.get_by_test_id("simulador-contas")).to_contain_text(" + 3 da intervenção = ")
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

        assert not chamadas_llm, "o Simulador calcula sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("SIMULADOR PASS: ferramenta na navegação sem pedido antes de Calcular, seleção local (cópia, acréscimo de BRASILIA e do Paraná "
          "como unidade, retirada de MANAUS e recusa de CURITIBA) sem mudar a seleção principal, janela e método padrão, data final em "
          "qualquer mês, cenário com acréscimo (texto fixo do motor, gráfico com observado, base, evento e faixa; pico fora do ajuste em "
          "RIO RUFINO), Paraná sem faixa, estatísticas descritivas, modo avançado com dois cenários, retirada acima do estoque, validação "
          "dos métodos, exportações CSV e JSON, importação do cenário, cópia de novo e Aplicar à seleção principal com Desfazer.")


if __name__ == "__main__":
    main()
