"""Simulador de Cenários Territoriais na página única (comando V22, etapas 4 e 5; Proposta V3 do comando V23, Parte C), com a base
versionada (somente leitura).

Confere, contra as respostas de POST /api/simulador:
- a ferramenta na navegação principal ("Simulador de Cenários"), que abre no modo simples e, sem territórios, não pede nada ao
  motor em nenhum dos dois modos;
- o modo simples numa tela só (Proposta V3): o território (um dos da seleção local), até quando (com os atalhos de 1, 2 e 4 anos)
  e o que testar (só continuar como vinha, acrescentar, retirar ou chegar a uma meta); o pedido leva um território só; o
  resultado traz a frase fixa do motor, os três números, o jeito de projetar escolhido pela base, os dois "Entenda" (com os
  textos do motor) e a faixa de 8 em cada 10: conferida em 2 anos, provisória em 4 e indisponível, com o motivo, para um estado
  como unidade; a retirada acima do estoque volta para revisão; "Avançado" leva às quatro etapas, e "Modo simples" traz de volta;
- a seleção local (no modo avançado): uma cópia da seleção principal, em que acrescentar (um município e um estado como unidade)
  e tirar territórios não muda a seleção principal; "Copiar de novo a seleção principal" e "Aplicar à seleção principal", que só
  então muda a seleção principal, num passo do Desfazer;
- as quatro etapas do modo avançado: os territórios, a base histórica e o método (a janela padrão de 3 anos e o método padrão, que
  é o jeito escolhido pela base), as intervenções e a data final (qualquer mês; os atalhos são só atalhos) e os resultados, só
  depois de "Calcular os cenários";
- os resultados de RIO RUFINO (SC), de BRASILIA (DF) e do Paraná como unidade: o texto fixo de cenário vindo do motor, o gráfico
  com o observado, a base do cenário, a intervenção e a faixa (só no jeito escolhido pela base), o aviso do pico fora do ajuste,
  o estado sem faixa (com o motivo) e a persistência como referência;
- um segundo cenário; a retirada acima do estoque, devolvida para revisão; as estatísticas históricas, com a média aritmética só
  descritiva; a avaliação dos métodos (as dez faixas de porte), que desde o AJ-03 (18/11/2026) sai da tela e vai em "Exportar a
  avaliação dos métodos (JSON)", com os números do motor; a ficha metodológica (PDF), servida com a interface e aberta numa nova
  aba pelo link e pelo "Ver explicação completa" dos "Entenda"; a janela do cálculo no modo avançado; as exportações (CSV dos
  resultados e JSON do cenário) e a importação do cenário;
- da etapa 5: "Abrir no Simulador", no Detector de Sinais, que traz MANAUS (AM) com o contexto analítico, no modo simples, sem
  mudar a seleção principal; o Brasil como território, só no Simulador (o único com o método padrão provisório); as referências
  de comparação (FLORIANOPOLIS dinâmica, o Brasil fixo e um valor informado), com as curvas no gráfico, os textos do motor, "não
  alcança no horizonte simulado" e o aviso de sobreposição; o CSV das comparações; o planejamento inverso, com a meta hipotética,
  o menor inteiro por evento e o plano usado como intervenção, que recalculado alcança a meta; e a faixa pedida (5 em cada 10);
- o que só o modo avançado escolhe fica no modo avançado: a janela geral e as referências vão no pedido do modo avançado, não vão
  no do modo simples (ficam guardadas) e voltam a ir no modo avançado; o jeito de projetar escolhido lá é avisado no modo simples;
- "Simular recuperação", no Detector de Sinais: ABELARDO LUZ (SC) abre o modo simples com "Chegar a uma meta" marcado e o patamar
  anterior como meta, que a pessoa pode trocar;
- nenhuma chamada ao provedor de IA e nenhum erro na página.

Base Brasil versionada (suíte base-versionada, ADT_BLOCK1_REAL=1); servidor serve_ui_offline.py, sem o provedor de IA.
"""
import json
import math
import os
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline, options_of

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, TEFE, RIO_RUFINO, BRASILIA, PR = "code:130260", "code:130420", "code:421505", "code:530010", "41"
FLORIANOPOLIS = "code:420540"
# EIRUNEPE (AM) tem 22 médicos em jun/2024 (faixa de porte de 20 a 49); ABELARDO LUZ (SC) está abaixo do que já teve (patamar de 78,25).
EIRUNEPE, ABELARDO_LUZ = "code:130140", "code:420010"
FIXO = "Cenário hipotético, não é previsão: "
VERSAO = "SIMULADOR-CENARIOS/V3/1"
C1 = {"id": "c1", "nome": "Cenário 1", "metodo": "padrao"}
PERSISTENCIA = {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}
# Os textos da faixa de 8 em cada 10 (Proposta V3, seção C.4): o que a tela diz quando ela é provisória e o motivo de não haver
# faixa para os estados como unidade nesta base.
PROVISORIA = ("Faixa provisória: ainda não deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do "
              "esperado.")
SEM_CASOS = ("A faixa de 8 em cada 10 pede 200 casos por prazo, e esta base tem 189 em 1 ano para o porte deste território, mesmo "
             "juntando os portes vizinhos e os menores.")
MEIO_DA_FAIXA = ", o número observado ficou dentro dessa margem; ela acompanha a intervenção."


def curta(competencia):
    """A data como a tela a escreve: "jun/2024"."""
    return ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")[int(competencia[4:]) - 1] + "/" + competencia[:4]


def so_o_municipio(codigo):
    """A seleção do pedido com um município só (o território em análise do modo simples)."""
    return {"municipios": {"todos": False, "estados": [], "ids": [codigo]}}


def inteiro_da_tela(valor):
    """O número inteiro como a tela o escreve: arredondado (metade para cima) e com o ponto de milhar."""
    return f"{math.floor(valor + 0.5):,}".replace(",", ".")


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
        # O modo simples (Proposta V3): a tela única, o território em análise, "O que testar" e o resultado.
        simples = simulador.get_by_test_id("simulador-simples")
        territorio = simulador.get_by_test_id("simulador-territorio")
        o_que_testar = simulador.get_by_test_id("simulador-o-que-testar")
        resultado_simples = simulador.get_by_test_id("simulador-resultado")

        def do_simulador(acao):
            """A resposta de /api/simulador que a ação provocou e as opções do pedido."""
            with page.expect_response(lambda r: r.url.endswith("/api/simulador") and r.request.method == "POST", timeout=180000) as evento:
                acao()
            assert evento.value.status == 200, evento.value.text()[:2000]
            return evento.value.json(), options_of(evento.value.request)

        def calcular():
            """O botão "Calcular" (no modo simples) ou "Calcular os cenários" (na etapa 3 do modo avançado): só um dos dois está na tela."""
            return do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())

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

        def teste(chave):
            """A opção de "O que testar": continuar, acrescentar, retirar ou meta."""
            return simulador.get_by_test_id("simulador-teste-" + chave)

        def tres_numeros(rotulos, valores):
            """Os três números do resultado do modo simples: os rótulos e os valores, na ordem."""
            quadro = resultado_simples.get_by_test_id("simulador-tres-numeros")
            expect(quadro.locator("dt")).to_have_text(rotulos)
            expect(quadro.locator("dd")).to_have_text(valores)

        def entenda(nome, sobre, do_motor):
            """Abre o "Entenda" do resultado pelo clique: o texto e o exemplo são os do motor."""
            simulador.get_by_test_id("simulador-entenda-" + nome + "-botao").click()
            expect(simulador.get_by_test_id("simulador-entenda-" + nome)).to_have_attribute("data-aberto", "true")
            expect(simulador.get_by_test_id("simulador-entenda-" + nome + "-botao")).to_have_attribute("aria-label", "Entenda: " + sobre)
            expect(simulador.get_by_test_id("simulador-entenda-" + nome + "-caixa")).to_contain_text(do_motor["texto"])
            expect(simulador.get_by_test_id("simulador-entenda-" + nome + "-exemplo")).to_have_text("Exemplo: " + do_motor["exemplo"])

        def fechar_o_entenda(nome):
            """Fecha o "Entenda" com Esc, para a caixa não ficar por cima do que vem depois."""
            page.keyboard.press("Escape")
            expect(simulador.get_by_test_id("simulador-entenda-" + nome + "-caixa")).to_have_count(0)

        def da_avaliacao():
            """A avaliação dos métodos exportada (AJ-03): o nome do arquivo e o conteúdo."""
            with page.expect_download() as evento:
                simulador.get_by_test_id("simulador-exportar-avaliacao").click()
            return evento.value.suggested_filename, json.loads(Path(evento.value.path()).read_text(encoding="utf-8"))

        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. A ferramenta fica na navegação principal e abre no modo simples (Proposta V3). Sem territórios, a cópia local é vazia e
        # nada é pedido ao motor, nem no modo simples nem nas quatro etapas do modo avançado.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
        expect(botao).to_be_enabled()
        expect(botao).to_have_text("Simulador de Cenários")
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        expect(simulador.get_by_test_id("simulador-titulo")).to_have_text("Simulador de Cenários Territoriais")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simples).to_be_visible()
        # O "(Entenda)" geral fica no título, como no Detector de Sinais, e abre pelo clique (etapa 7 do comando V23): três frases
        # simples e um exemplo. Um "Voltar ao padrão" só, sempre à vista, fica desligado enquanto as premissas são as do padrão.
        entenda("ferramenta", "Simulador de Cenários", {
            "texto": "Mostra para onde o território iria se continuasse como vinha, e o efeito das mudanças que você quer testar. O “como vinha” "
                     "e a margem de erro vêm da própria base: o Agente refaz no passado a projeção que teria feito e confere com o que "
                     "aconteceu depois. Todo resultado é um cenário hipotético, nunca uma previsão.",
            "exemplo": "Com 22 médicos no último registro, “continuar como vinha” pode levar a 25 dois anos depois; com 5 acrescentados, a 30. "
                       "Os números deste exemplo são ilustrativos."})
        fechar_o_entenda("ferramenta")
        voltar_ao_padrao = simulador.get_by_test_id("simulador-voltar-ao-padrao")
        expect(voltar_ao_padrao).to_have_text("Voltar ao padrão")
        expect(voltar_ao_padrao).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-modo-simples")).to_have_attribute("aria-pressed", "true")
        expect(simulador.get_by_test_id("simulador-modo-avancado")).to_have_text("Avançado")
        expect(simulador.get_by_test_id("simulador-data")).to_contain_text("O registro mais recente da base é jun/2024")
        expect(simulador.get_by_test_id("simulador-data")).to_contain_text("simulado, nunca observado")
        expect(simulador.get_by_test_id("simulador-distancia")).to_contain_text("(há ")  # a distância entre o último registro e hoje
        expect(territorio).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-sem-territorio")).to_contain_text("Nenhum território na seleção do Simulador")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Escolha pelo menos um território para o Simulador.")
        # As quatro etapas ficam no modo avançado: no modo simples, nem os passos nem a seleção local aparecem.
        expect(simulador.get_by_test_id("simulador-etapa-1")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-territorios")).to_have_count(0)
        simulador.get_by_test_id("simulador-modo-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        expect(simples).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "0")
        expect(simulador.get_by_test_id("simulador-avancar-1")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-calcular-direto")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-etapa-4")).to_be_disabled()
        simulador.get_by_test_id("simulador-modo-simples").click()
        expect(simulador).to_have_attribute("data-modo", "simples")
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

        # 3. O modo simples numa tela só (Proposta V3, seções C.2 e C.7): o território é um dos da seleção local (a cópia da seleção
        # principal), "O que testar" tem quatro opções, e os atalhos da data final são de 1, 2 e 4 anos. Nada é pedido antes de
        # "Calcular".
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(simples).to_have_attribute("data-teste", "continuar")
        expect(territorio.locator("option")).to_have_text(["MANAUS (AM)", "RIO RUFINO (SC)"])
        assert territorio.locator("option").evaluate_all("els => els.map(e => e.value)") == [MANAUS, RIO_RUFINO]
        expect(territorio).to_have_value(MANAUS)
        expect(o_que_testar.locator("legend")).to_have_text("O que testar")
        expect(o_que_testar.locator("label")).to_have_text(["Só continuar como vinha", "Acrescentar", "Retirar", "Chegar a uma meta"])
        expect(teste("continuar")).to_be_checked()
        horizonte = simulador.get_by_test_id("simulador-horizonte")
        expect(horizonte).to_have_value("2026-06")
        expect(simulador.get_by_test_id("simulador-atalho-2")).to_have_attribute("aria-pressed", "true")
        expect(simulador.get_by_test_id("simulador-atalho-1")).to_have_text("1 ano")
        expect(simulador.get_by_test_id("simulador-atalho-4")).to_have_text("4 anos")
        expect(simulador.get_by_test_id("simulador-atalho-10")).to_have_count(0)   # o atalho de 10 anos é só do modo avançado
        for anos, data in ((1, "2025-06"), (4, "2028-06"), (2, "2026-06")):
            simulador.get_by_test_id("simulador-atalho-" + str(anos)).click()
            expect(horizonte).to_have_value(data)
            expect(simulador.get_by_test_id("simulador-atalho-" + str(anos))).to_have_attribute("aria-pressed", "true")
        expect(simulador.get_by_test_id("simulador-atalho-4")).to_have_attribute("aria-pressed", "false")
        expect(simulador.get_by_test_id("simulador-calcular")).to_have_text("Calcular")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_enabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_count(0)
        expect(resultado_simples).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-etapa-1")).to_have_count(0)
        assert not pedidos, "nada é calculado antes de \"Calcular\""

        # 3a. "Calcular", com dois territórios na seleção local: o pedido leva só o território em análise (MANAUS), o cenário com o
        # jeito escolhido pela base ("padrao") e a persistência como referência. Entre os municípios de 3.000 a 9.999 médicos, a
        # faixa junta os portes vizinhos, e a tela diz isso.
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(MANAUS), "horizonte": "202606", "cenarios": [C1, PERSISTENCIA]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == [MANAUS], corpo["territorios"]
        assert corpo["versao"] == VERSAO, corpo["versao"]
        assert corpo["limitacoes"] == ["CENARIO_HIPOTETICO", "PADRAO_ESCOLHIDO_PELA_BASE", "FAIXA_SO_DO_METODO_PADRAO"], corpo["limitacoes"]
        assert corpo["faixa"] == {"em_10": 8, "opcoes": [5, 8, 9], "padrao": 8}, corpo["faixa"]
        de_manaus = corpo["territorios"][0]["cenarios"][0]
        assert de_manaus["faixa"]["como"] == "vizinhas" and de_manaus["final"]["faixa"]["estado"] == "conferida", de_manaus["faixa"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples).to_have_attribute("data-estado", "calculado")
        expect(resultado_simples).to_have_attribute("data-metodo", "M0d")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(de_manaus["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Diferença"], ["4.730", "5.335", "+605 médicos"])
        expect(resultado_simples.get_by_test_id("simulador-faixa-texto")).to_have_text(
            "Faixa de 8 em cada 10 em jun/2026: de 4.896,4 a 6.063,0 médicos. No passado da base, em 8 de cada 10 casos de territórios do "
            "mesmo porte e dos portes vizinhos" + MEIO_DA_FAIXA + " Conferida com o que veio depois.")
        expect(resultado_simples.get_by_test_id("simulador-hipotetico")).to_have_count(0)   # com milhares de médicos, a escala não tem o que dizer

        # 3b. "Avançado" leva às quatro etapas, e "Modo simples" traz de volta. Na etapa 1, a seleção local é a cópia da seleção
        # principal, que ela acompanha até ser alterada no Simulador. EIRUNEPE (AM) e o Paraná como unidade entram só no Simulador:
        # a cópia deixa de acompanhar a seleção principal, que não muda, e montar a seleção local não pede nada ao motor.
        simulador.get_by_test_id("simulador-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        expect(simulador.get_by_test_id("simulador-modo-avancado")).to_have_attribute("aria-pressed", "true")
        expect(simples).to_have_count(0)
        for numero in (1, 2, 3, 4):
            expect(simulador.get_by_test_id("simulador-etapa-" + str(numero))).to_have_count(1)
        simulador.get_by_test_id("simulador-etapa-1").click()
        expect(simulador).to_have_attribute("data-etapa", "1")
        expect(simulador.get_by_test_id("simulador-territorios")).to_be_visible()
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "2")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "true")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_have_count(0)
        expect(local(MANAUS)).to_contain_text("MANAUS (AM)")
        expect(local(RIO_RUFINO)).to_contain_text("RIO RUFINO (SC)")
        acrescentar("eirunepe", EIRUNEPE)
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "false")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_contain_text("deixou de acompanhar a seleção principal")
        acrescentar("parana", "uf:" + PR)
        expect(local("uf:" + PR)).to_contain_text("Paraná (estado)")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "4")
        simulador.get_by_test_id("simulador-busca").fill("")
        expect(resumo).to_have_text(principal)
        simulador.get_by_test_id("simulador-modo-simples").click()
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simples).to_be_visible()
        expect(simulador.get_by_test_id("simulador-territorios")).to_have_count(0)
        # A lista do território segue a seleção local: os municípios, depois o estado como unidade. Sem escolha, vale o primeiro
        # (EIRUNEPE), e o resultado de MANAUS fica à vista, marcado como anterior às escolhas de agora.
        expect(territorio.locator("option")).to_have_text(["EIRUNEPE (AM)", "MANAUS (AM)", "RIO RUFINO (SC)", "Paraná (estado)"])
        assert territorio.locator("option").evaluate_all("els => els.map(e => e.value)") == [EIRUNEPE, MANAUS, RIO_RUFINO, "uf:" + PR]
        expect(territorio).to_have_value(EIRUNEPE)
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        expect(resultado_simples.get_by_test_id("simulador-desatualizado")).to_contain_text("As escolhas mudaram depois deste cálculo.")
        assert len(pedidos) == 1, "só o cálculo de MANAUS foi pedido até aqui"

        # 3c. "Só continuar como vinha", EIRUNEPE (AM), 2 anos: 22 médicos em jun/2024 (faixa de porte de 20 a 49). O pedido leva um
        # território só; o jeito de projetar é o que a base escolheu (M0d); a faixa de 8 em cada 10 é conferida com o que veio
        # depois; a frase fixa, os três números e os dois "Entenda" são os do motor.
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(EIRUNEPE), "horizonte": "202606", "cenarios": [C1, PERSISTENCIA]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == [EIRUNEPE], corpo["territorios"]
        cenario = corpo["territorios"][0]["cenarios"][0]
        assert cenario["metodo"] == {"pedido": "padrao", "usado": "M0d", "rotulo": "persistência com o crescimento recente do estado", "padrao": True,
                                     "provisorio": False, "voltou_ao_m0": False, "soma": None, "escolhido_pela_base": "M0d",
                                     "e_o_escolhido": True}, cenario["metodo"]
        assert cenario["parametros"]["n0"] == 22 and cenario["faixa"]["porte"] == "20 a 49", (cenario["parametros"], cenario["faixa"])
        assert (cenario["faixa"]["estado"], cenario["faixa"]["em_10"], cenario["faixa"]["conferencia"], cenario["faixa"]["como"],
                cenario["faixa"]["ate_anos"]) == ("disponivel", 8, "conferida", "propria", 4), cenario["faixa"]
        assert cenario["final"]["faixa"]["anos"] == 2 and cenario["final"]["faixa"]["estado"] == "conferida", cenario["final"]
        assert [aviso["codigo"] for aviso in cenario["avisos"]] == ["HORIZONTE_CAUTELA"], cenario["avisos"]
        assert cenario["texto"].startswith(FIXO) and "sem intervenção, EIRUNEPE (AM) teria 25 médicos em jun/2026." in cenario["texto"], cenario["texto"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples.get_by_test_id("simulador-desatualizado")).to_have_count(0)
        expect(resultado_simples).to_have_attribute("data-estado", "calculado")
        expect(resultado_simples).to_have_attribute("data-metodo", "M0d")
        expect(resultado_simples).to_have_attribute("data-faixa", "disponivel")
        expect(resultado_simples).to_have_attribute("data-conferencia", "conferida")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_contain_text("Base: registros até jun/2024.")
        assert [inteiro_da_tela(cenario["parametros"]["n0"]), inteiro_da_tela(cenario["final"]["total"])] == ["22", "25"], cenario["final"]
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Diferença"], ["22", "25", "+3 médicos"])
        # AJ-05 (18/11/2026): "forma de projetar", no feminino ("escolhida pela base"); antes, "Jeito de projetar … (escolhido pela base)".
        expect(resultado_simples).to_contain_text("Forma de projetar: persistência com o crescimento recente do estado (escolhida pela base)")
        expect(resultado_simples.get_by_test_id("simulador-faixa-estado")).to_have_text("Faixa de 8 em cada 10: conferida")
        expect(resultado_simples.get_by_test_id("simulador-faixa-texto")).to_have_text(
            "Faixa de 8 em cada 10 em jun/2026: de 19,0 a 33,2 médicos. No passado da base, em 8 de cada 10 casos de territórios do "
            "mesmo porte" + MEIO_DA_FAIXA + " Conferida com o que veio depois.")
        expect(resultado_simples.locator('[data-testid="simulador-avisos"] li')).to_have_count(1)
        expect(resultado_simples.locator('[data-testid="simulador-avisos"] li[data-codigo="HORIZONTE_CAUTELA"]')).to_have_text(cenario["avisos"][0]["texto"])
        expect(resultado_simples.get_by_test_id("simulador-hipotetico")).to_have_count(0)
        expect(resultado_simples.get_by_test_id("simulador-planejamento")).to_have_count(0)
        expect(resultado_simples).to_contain_text("Contagem: médicos registrados no município")
        # O gráfico: o observado (22 registros reais), a base do cenário e a da persistência, e a faixa, sem intervenção.
        grafico = simulador.get_by_test_id("simulador-grafico")
        expect(grafico.get_by_test_id("simulador-observado")).to_have_count(22)
        expect(grafico.get_by_test_id("simulador-curva")).to_have_count(2)
        expect(grafico.locator('[data-testid="simulador-curva"][data-cenario="c1"]')).to_have_attribute("data-metodo", "M0d")
        expect(grafico.get_by_test_id("simulador-faixa")).to_have_count(1)
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(0)
        expect(grafico).to_contain_text("banda: faixa de 8 em cada 10")
        expect(grafico.get_by_test_id("simulador-grafico-fonte")).to_have_text(
            "Fonte: base do Brasil (medicina), registros de janeiro e junho até jun/2024.")
        # AJ-03 (18/11/2026): a linha das versões saiu da tela (as versões vão nas exportações). No alto, o link da ficha
        # metodológica (PDF), servida com a interface, numa nova aba.
        assert corpo["versao"] == VERSAO, corpo["versao"]
        expect(simulador.get_by_test_id("simulador-versoes")).to_have_count(0)
        ficha = simulador.get_by_test_id("simulador-ficha")
        expect(ficha).to_contain_text("Ficha metodológica (PDF)")
        expect(ficha).to_have_attribute("target", "_blank")
        endereco_da_ficha = ficha.evaluate("e => e.href")
        assert endereco_da_ficha.endswith("/fichas/ficha-simulador.pdf"), endereco_da_ficha
        do_pdf = page.request.get(endereco_da_ficha)
        assert do_pdf.status == 200 and do_pdf.body()[:5] == b"%PDF-", (do_pdf.status, do_pdf.body()[:20])
        assert do_pdf.headers.get("content-type", "").startswith("application/pdf"), do_pdf.headers
        # O gráfico é desenhado na largura que tem na tela (revisão das capturas de 15/11/2026: no celular, o desenho era encolhido,
        # e o texto dos eixos ficava pequeno demais). No computador, até 860 px; numa tela de celular, na largura dela, mais alto
        # (340 em vez de 300), com o texto em 12 px de verdade e sem passar da largura da janela.
        def medidas_do_grafico():
            return grafico.evaluate("""e => { const svg = e.querySelector("svg"), texto = svg.querySelector("text");
              return { largura: Number(e.dataset.largura), caixa: svg.viewBox.baseVal.width, altura: svg.viewBox.baseVal.height,
                       naTela: svg.getBoundingClientRect().width, fonte: parseFloat(getComputedStyle(texto).fontSize) }; }""")
        expect(grafico).not_to_have_attribute("data-largura", "760")   # a largura medida, e não a do primeiro desenho
        no_computador = medidas_do_grafico()
        assert 560 <= no_computador["largura"] == no_computador["caixa"] <= 860 and no_computador["altura"] == 300, no_computador
        assert abs(no_computador["naTela"] - no_computador["caixa"]) <= 1 and no_computador["fonte"] == 12, no_computador
        page.set_viewport_size({"width": 390, "height": 844})
        expect(grafico).not_to_have_attribute("data-largura", str(no_computador["largura"]))
        no_celular = medidas_do_grafico()
        assert 280 <= no_celular["largura"] == no_celular["caixa"] <= 390 and no_celular["altura"] == 340, no_celular
        assert abs(no_celular["naTela"] - no_celular["caixa"]) <= 1 and no_celular["fonte"] == 12, no_celular
        grafico.scroll_into_view_if_needed()
        caixa_do_grafico = grafico.bounding_box()
        assert caixa_do_grafico["x"] >= 0 and caixa_do_grafico["x"] + caixa_do_grafico["width"] <= 390 + 0.5, caixa_do_grafico
        page.screenshot(path=str(OUTPUT / "simulador-00a-simples-celular-real.png"), full_page=False)
        page.set_viewport_size({"width": 1440, "height": 1000})
        expect(grafico).to_have_attribute("data-largura", str(no_computador["largura"]))
        # Os dois "Entenda" abrem pelo clique, com o texto e o exemplo do motor.
        assert cenario["entenda"]["jeito"] == {
            "texto": "O cenário parte do último registro usado (jun/2024) e soma o crescimento recente do estado: +6,21% ao ano nos 3 anos "
                     "anteriores. Usamos esta forma porque, nesta base, ela errou menos que simplesmente manter o último valor, quando "
                     "refeita no passado.",
            "exemplo": "De 22 médicos em jun/2024, a base do cenário vai a 23,4 um ano depois, sem contar intervenções."}, cenario["entenda"]
        assert cenario["entenda"]["faixa"] == {
            "texto": "Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte. Em 8 de cada 10 vezes, o valor "
                     "real ficou dentro desta faixa. Não é garantia: o passado testado (2017–2024) pode não se repetir.",
            "exemplo": "Entre 19 e 33 médicos na data final."}, cenario["entenda"]
        entenda("jeito", "A forma de projetar", cenario["entenda"]["jeito"])
        fechar_o_entenda("jeito")
        entenda("faixa", "A faixa de 8 em cada 10", cenario["entenda"]["faixa"])
        page.screenshot(path=str(OUTPUT / "simulador-00-simples-real.png"), full_page=True)
        # AJ-03 (18/11/2026): "Como os métodos se saíram no passado" saiu da tela. O "Ver explicação completa" de cada "Entenda" leva
        # à seção da ficha metodológica (PDF), numa nova aba; a forma que a base escolheu para cada nível, com a frase do motor e o
        # erro de cada forma comparado com manter o último valor, vai em "Exportar a avaliação dos métodos (JSON)", como o motor
        # mandou.
        completa = simulador.get_by_test_id("simulador-entenda-faixa-completa")
        expect(completa).to_have_attribute("target", "_blank")
        assert completa.evaluate("e => e.href") == endereco_da_ficha + "#nameddest=faixa"
        fechar_o_entenda("faixa")
        for nome, secao in (("jeito", "forma-escolhida"), ("ferramenta", "o-que-e")):
            simulador.get_by_test_id("simulador-entenda-" + nome + "-botao").click()
            expect(simulador.get_by_test_id("simulador-entenda-" + nome + "-caixa")).to_be_visible()
            assert simulador.get_by_test_id("simulador-entenda-" + nome + "-completa").evaluate("e => e.href") == endereco_da_ficha + "#nameddest=" + secao, nome
            fechar_o_entenda(nome)
        expect(simulador.get_by_test_id("simulador-validacao")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-validacao-botao")).to_have_count(0)
        escolhas = corpo["retroprojecao"]["niveis"]
        assert escolhas["municipios"]["escolha"]["texto"] == (
            "Para os municípios, a base escolheu a persistência com o crescimento recente do estado: na retroprojeção, ela errou 29% menos "
            "que manter o último valor, e menos em 22 de 22 combinações de origem e prazo."), escolhas["municipios"]["escolha"]
        assert (escolhas["municipios"]["escolha"]["metodo"], escolhas["estados"]["escolha"]["metodo"]) == ("M0d", "M1"), escolhas
        do_m0d = next(item for item in escolhas["municipios"]["escolha"]["candidatos"] if item["metodo"] == "M0d")
        assert (round(do_m0d["frente_ao_m0"], 3), do_m0d["menos_erro_em"], do_m0d["combinacoes"]) == (0.714, 22, 22), do_m0d
        nome_da_avaliacao, avaliacao = da_avaliacao()
        assert nome_da_avaliacao == "simulador_avaliacao_dos_metodos_202406.json", nome_da_avaliacao
        assert avaliacao["retroprojecao"] == corpo["retroprojecao"], "a avaliação exportada leva os números do motor, sem leitura"
        assert (avaliacao["versao_do_metodo"], avaliacao["fonte"]["versao"], avaliacao["ultimo_registro"]) == (
            corpo["versao"], corpo["fonte"]["versao"], "202406"), (avaliacao["versao_do_metodo"], avaliacao["fonte"])
        assert avaliacao["limitacoes"] == corpo["limitacoes"] and "não é uma análise do território escolhido" in avaliacao["conteudo"], avaliacao["conteudo"]
        texto_da_avaliacao = json.dumps(avaliacao, ensure_ascii=False)
        assert escolhas["municipios"]["escolha"]["texto"] in texto_da_avaliacao and escolhas["estados"]["escolha"]["texto"] in texto_da_avaliacao

        # 3d. Com 4 anos, a faixa é provisória: ainda não deu para conferi-la com o que veio depois. Nesta base, as faixas de 1 e
        # 2 anos são conferidas, e as de 3 e 4 anos, provisórias.
        simulador.get_by_test_id("simulador-atalho-4").click()
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(EIRUNEPE), "horizonte": "202806", "cenarios": [C1, PERSISTENCIA]}, enviado
        cenario = corpo["territorios"][0]["cenarios"][0]
        assert cenario["final"]["faixa"]["anos"] == 4 and cenario["final"]["faixa"]["estado"] == "provisoria" and \
            cenario["final"]["faixa"]["validada"] is False and cenario["faixa"]["conferencia"] == "provisoria", cenario["final"]
        assert {ponto["faixa"]["anos"]: ponto["faixa"]["estado"] for ponto in cenario["trajetoria"]} == {
            1: "conferida", 2: "conferida", 3: "provisoria", 4: "provisoria"}, cenario["trajetoria"]
        da_faixa = next(aviso for aviso in cenario["avisos"] if aviso["codigo"] == "FAIXA_PROVISORIA")
        assert da_faixa["texto"] == ("Faixa provisória: ainda não deu para conferi-la com dados que vieram depois (poucas origens ou poucos "
                                     "casos de teste)."), da_faixa
        assert cenario["entenda"]["faixa"]["texto"].endswith(" " + PROVISORIA), cenario["entenda"]["faixa"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples).to_have_attribute("data-conferencia", "provisoria")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2028", "Diferença"], ["22", "28", "+6 médicos"])
        expect(resultado_simples.get_by_test_id("simulador-faixa-estado")).to_have_text("Faixa de 8 em cada 10: provisória")
        expect(resultado_simples.get_by_test_id("simulador-faixa-texto")).to_have_text(
            "Faixa de 8 em cada 10 em jun/2028: de 20,9 a 43,2 médicos. No passado da base, em 8 de cada 10 casos de territórios do "
            "mesmo porte" + MEIO_DA_FAIXA + " " + PROVISORIA)
        expect(resultado_simples.locator('[data-testid="simulador-avisos"] li[data-codigo="FAIXA_PROVISORIA"]')).to_have_text(da_faixa["texto"])

        # 3e. "Acrescentar 5 em jan/2025": sem a quantidade, nada é pedido; com ela, o resultado e a frase mudam, o gráfico ganha o
        # evento, e a faixa acompanha a intervenção.
        simulador.get_by_test_id("simulador-atalho-2").click()
        teste("acrescentar").check()
        expect(simples).to_have_attribute("data-teste", "acrescentar")
        quantidade, em = simulador.get_by_test_id("simulador-teste-quantidade"), simulador.get_by_test_id("simulador-teste-em")
        expect(quantidade).to_have_value("1")
        expect(em).to_have_value("2025-06")
        expect(o_que_testar).to_contain_text("É uma hipótese sua: o crescimento histórico não é aplicado a quem entra.")
        # O nome concorda com o número digitado: "Acrescentar 1 médico", "5 médicos" (revisão das capturas de 15/11/2026).
        frase_do_teste = simulador.get_by_test_id("simulador-frase-do-teste")
        expect(frase_do_teste).to_contain_text("médico em")
        expect(frase_do_teste).not_to_contain_text("médicos")
        quantidade.fill("")
        expect(frase_do_teste).to_contain_text("médicos em")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe quantos entram ou saem em cada intervenção.")
        quantidade.fill("5")
        expect(frase_do_teste).to_contain_text("médicos em")
        em.fill("2025-01")
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_count(0)
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(EIRUNEPE), "horizonte": "202606", "cenarios": [
            {**C1, "intervencoes": [{"tipo": "acrescimo", "quantidade": 5, "em": "202501"}]}, PERSISTENCIA]}, enviado
        cenario = corpo["territorios"][0]["cenarios"][0]
        assert cenario["final"]["intervencao"] == 5 and cenario["final"]["faixa"]["estado"] == "conferida", cenario["final"]
        assert "acréscimo de 5 médicos em jan/2025, com permanência total (hipótese), EIRUNEPE (AM) teria 30 médicos em jun/2026." in cenario["texto"], cenario["texto"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Diferença"], ["22", "30", "+8 médicos"])
        expect(resultado_simples.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 8 em cada 10 em jun/2026: de 24,0 a 38,2 médicos.")
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(1)
        expect(grafico).to_contain_text("linha contínua: com a intervenção")

        # 3f. "Retirar": a quantidade e a data digitadas ficam ao trocar de opção. Retirar 50 de quem tem 22 passa do estoque: o
        # cenário volta para revisão, sem número inventado.
        teste("retirar").check()
        expect(simples).to_have_attribute("data-teste", "retirar")
        expect(quantidade).to_have_value("5")
        expect(em).to_have_value("2025-01")
        quantidade.fill("50")
        corpo, enviado = calcular()
        assert enviado["cenarios"] == [{**C1, "intervencoes": [{"tipo": "retirada", "quantidade": 50, "em": "202501"}]}, PERSISTENCIA], enviado
        cenario = corpo["territorios"][0]["cenarios"][0]
        assert cenario["estado"] == "retirada_acima_do_estoque" and "final" not in cenario, cenario
        expect(resultado_simples).to_have_attribute("data-estado", "retirada_acima_do_estoque")
        expect(resultado_simples.get_by_test_id("simulador-motivo")).to_have_text("Retirada acima do estoque: " + cenario["motivo"])
        expect(resultado_simples.get_by_test_id("simulador-motivo")).to_contain_text("Nenhum estoque negativo é aceito")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_count(0)
        expect(resultado_simples.get_by_test_id("simulador-tres-numeros")).to_have_count(0)
        expect(grafico.get_by_test_id("simulador-curva")).to_have_count(1)   # só a persistência de referência

        # 3g. "Chegar a uma meta": a data digitada fica; sem a meta, nada é pedido. Com 40 médicos como meta, o motor devolve o
        # menor acréscimo inteiro (16), e o terceiro número passa a dizer quanto seria preciso acrescentar. A meta é uma hipótese
        # da pessoa: o acréscimo não entra no cenário.
        teste("meta").check()
        expect(simples).to_have_attribute("data-teste", "meta")
        valor_da_meta = simulador.get_by_test_id("simulador-teste-meta-valor")   # o campo do valor; "simulador-teste-meta" é a opção
        expect(valor_da_meta).to_have_value("")
        expect(em).to_have_value("2025-01")
        expect(simulador.get_by_test_id("simulador-teste-quantidade")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe a meta: um número acima de zero.")
        expect(o_que_testar).to_contain_text("A meta é uma hipótese sua. O Agente calcula quantos faltariam, com o menor número inteiro.")
        valor_da_meta.fill("40")
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(EIRUNEPE), "horizonte": "202606", "cenarios": [
            {**C1, "planejamento": {"meta": {"tipo": "valor", "valor": 40}, "em": "202501"}}, PERSISTENCIA]}, enviado
        cenario = corpo["territorios"][0]["cenarios"][0]
        planejado = cenario["planejamento"]
        assert (planejado["estado"], planejado["eventos"], planejado["por_evento"], planejado["total"]) == ("calculado", 1, 16, 16), planejado
        assert planejado["texto"].startswith("Meta hipotética: 40 médicos em jun/2026. Menor acréscimo inteiro que alcança a meta, nas hipóteses "
                                             "deste cenário: 16 médicos em jan/2025.") and planejado["texto"].endswith(
            "É uma conta condicional às hipóteses do cenário, não um plano."), planejado["texto"]
        for proibida in ("recomenda", "é preciso", "deveria", "necessário prover"):
            assert proibida not in planejado["texto"].lower(), proibida
        assert cenario["final"]["intervencao"] == 0, "o acréscimo da meta não entra no cenário"
        expect(simulador).to_have_attribute("data-estado", "pronto")
        bloco = resultado_simples.get_by_test_id("simulador-planejamento")
        expect(bloco).to_have_attribute("data-estado", "calculado")
        expect(bloco).to_have_attribute("data-por-evento", "16")
        expect(bloco).to_have_attribute("data-eventos", "1")
        expect(bloco.get_by_test_id("simulador-planejamento-texto")).to_have_text(planejado["texto"])
        expect(bloco).to_contain_text("Chegar à meta")
        expect(bloco).to_contain_text("conta condicional")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Para chegar à meta"], ["22", "25", "precisaria acrescentar 16"])
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(0)
        # O gráfico mostra a meta (uma linha na altura dela), o caminho do cenário com o acréscimo e a marca na data do acréscimo
        # (revisão das capturas, 14/11/2026: antes, o desenho não mostrava o caminho até a meta).
        do_plano = grafico.get_by_test_id("simulador-plano-no-grafico")
        expect(do_plano).to_have_attribute("data-meta", "40")
        expect(do_plano).to_have_attribute("data-estado", "calculado")
        expect(do_plano.get_by_test_id("simulador-meta-linha")).to_have_count(1)
        expect(do_plano.get_by_test_id("simulador-plano-curva")).to_have_count(1)
        expect(do_plano.get_by_test_id("simulador-plano-evento")).to_have_count(1)
        caminho = planejado["trajetoria"]
        assert caminho[-1]["data"] == "202606" and abs(caminho[-1]["total"] - planejado["resultado"]) < 1e-9 and caminho[-1]["total"] >= 40, caminho
        assert [ponto["intervencao"] for ponto in caminho if ponto["data"] >= "202501"] == [16.0] * len([p for p in caminho if p["data"] >= "202501"]), caminho
        expect(grafico.get_by_test_id("simulador-meta-legenda")).to_have_text(
            "meta hipotética de 40 médicos; linha contínua: o cenário com o acréscimo que alcança a meta (▼ na data do acréscimo)")
        page.screenshot(path=str(OUTPUT / "simulador-00b-simples-meta-real.png"), full_page=True)

        # 3g-2. Trocar o território tira a meta: ela era do território de antes (revisão das capturas, 14/11/2026: o Pará ficava
        # com a meta do município anterior, e o resultado dizia "nada a acrescentar"). O campo fica em branco, à espera de outra;
        # a data do acréscimo continua, nada é pedido, e voltar ao território de antes não traz a meta de volta. O resultado de
        # antes também sai da tela, porque era do outro território (revisão das capturas de 15/11/2026: ele ficava à vista, com o
        # aviso "As escolhas mudaram depois deste cálculo").
        antes_da_troca = len(pedidos)
        expect(resultado_simples).to_have_count(1)
        territorio.select_option("uf:" + PR)
        expect(valor_da_meta).to_have_value("")
        expect(simples).to_have_attribute("data-teste", "meta")
        expect(em).to_have_value("2025-01")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe a meta: um número acima de zero.")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(resultado_simples).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-desatualizado")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-grafico")).to_have_count(0)
        territorio.select_option(EIRUNEPE)
        expect(valor_da_meta).to_have_value("")
        expect(resultado_simples).to_have_count(0)   # voltar ao território de antes não traz o resultado dele de volta
        page.wait_for_timeout(300)
        assert len(pedidos) == antes_da_troca, "trocar o território não pede nada ao motor"

        # 3h. Um estado como unidade (o Paraná): o jeito escolhido pela base para o nível é a taxa composta (M1), e a faixa é
        # indisponível, com o motivo do motor: a base não tem casos bastantes de estados.
        teste("continuar").check()
        expect(simples).to_have_attribute("data-teste", "continuar")
        expect(simulador.get_by_test_id("simulador-teste-meta-valor")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-teste-em")).to_have_count(0)
        territorio.select_option("uf:" + PR)
        corpo, enviado = calcular()
        assert enviado == {"estados_unidade": [PR], "horizonte": "202606", "cenarios": [C1, PERSISTENCIA]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == ["uf:" + PR], corpo["territorios"]
        cenario = corpo["territorios"][0]["cenarios"][0]
        assert (cenario["metodo"]["usado"], cenario["metodo"]["escolhido_pela_base"], cenario["metodo"]["e_o_escolhido"],
                cenario["metodo"]["provisorio"]) == ("M1", "M1", True, False), cenario["metodo"]
        assert cenario["faixa"] == {"estado": "indisponivel", "motivo": SEM_CASOS, "rotulo": None, "em_10": 8} and cenario["final"]["faixa"] is None, cenario["faixa"]
        assert cenario["entenda"]["faixa"]["texto"] == SEM_CASOS, cenario["entenda"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples).to_have_attribute("data-metodo", "M1")
        expect(resultado_simples).to_have_attribute("data-faixa", "indisponivel")
        expect(resultado_simples).to_have_attribute("data-conferencia", "")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Diferença"], ["32.785", "37.486", "+4.701 médicos"])
        expect(resultado_simples).to_contain_text("Forma de projetar: taxa composta da janela (escolhida pela base)")
        expect(resultado_simples.get_by_test_id("simulador-faixa-estado")).to_have_text("Faixa de 8 em cada 10: indisponível")
        expect(resultado_simples.get_by_test_id("simulador-faixa-texto")).to_have_text("Faixa de 8 em cada 10: indisponível. " + SEM_CASOS)
        expect(resultado_simples.locator('[data-testid="simulador-avisos"] li[data-codigo="PADRAO_PROVISORIO_DO_NIVEL"]')).to_have_count(0)
        expect(grafico.get_by_test_id("simulador-faixa")).to_have_count(0)
        expect(resultado_simples).to_contain_text("Contagem: médicos únicos no estado (fonte estadual).")
        entenda("faixa", "A faixa de 8 em cada 10", cenario["entenda"]["faixa"])
        fechar_o_entenda("faixa")
        pedidos_do_simples = len(pedidos)
        assert pedidos_do_simples == 7, "um pedido por \"Calcular\" no modo simples"

        # 3i. Sair e voltar não perde o modo, o território nem o que testar (a configuração fica guardada na área); o resultado, que
        # é da tela, não fica. As quatro etapas continuam no modo avançado, com a mesma seleção local.
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "")
        botao.click()
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(territorio).to_have_value("uf:" + PR)
        expect(teste("continuar")).to_be_checked()
        expect(horizonte).to_have_value("2026-06")
        expect(resultado_simples).to_have_count(0)
        simulador.get_by_test_id("simulador-modo-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        expect(simulador).to_have_attribute("data-etapa", "1")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "4")
        expect(local(EIRUNEPE)).to_contain_text("EIRUNEPE (AM)")
        # "Copiar de novo a seleção principal" desfaz o que foi acrescentado só no Simulador, e a cópia volta a acompanhá-la.
        simulador.get_by_test_id("simulador-copiar-principal").click()
        expect(simulador.get_by_test_id("simulador-aviso-local")).to_have_text("Seleção principal copiada de novo.")
        expect(local(EIRUNEPE)).to_have_count(0)
        expect(local("uf:" + PR)).to_have_count(0)

        # 4. No modo avançado, a seleção local é a cópia da seleção principal, que ela acompanha enquanto não for alterada no Simulador.
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "2")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "true")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_have_count(0)
        expect(local(MANAUS)).to_contain_text("MANAUS (AM)")
        expect(local(RIO_RUFINO)).to_contain_text("RIO RUFINO (SC)")

        # 5. Acrescentar e tirar territórios só no Simulador: a seleção principal não muda, e a seleção local deixa de acompanhá-la.
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
        assert len(pedidos) == pedidos_do_simples, "montar a seleção local não pede nada ao motor"

        # 6. A base histórica e o método: a janela padrão (3 anos até o último registro) e o método padrão, que desde a V3 é o jeito
        # de projetar escolhido pela própria base; o M0d e o M0g também podem ser escolhidos à mão.
        simulador.get_by_test_id("simulador-avancar-1").click()
        expect(simulador).to_have_attribute("data-etapa", "2")
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("202106")
        expect(simulador.get_by_test_id("simulador-janela-fim")).to_have_value("202406")
        expect(simulador.get_by_test_id("simulador-metodo")).to_have_value("padrao")
        assert simulador.get_by_test_id("simulador-metodo").locator("option").evaluate_all("els => els.map(e => e.value)") == [
            "padrao", "M0", "M0d", "M0g", "M1", "M2", "M3", "manual"], "a média aritmética não é um método"
        expect(simulador.get_by_test_id("simulador-metodo").locator("option").first).to_have_text("Continuar como vinha (a forma escolhida pela base)")
        expect(simulador.get_by_test_id("simulador-base")).to_contain_text("5 e 7 meses entre um e outro")
        expect(simulador.get_by_test_id("simulador-estatisticas-depois")).to_contain_text("aparecem aqui depois de calcular")
        # As premissas em frases, com os campos dentro delas (Proposta V3, seção C.5; etapa 7 do comando V23): a janela diz quanto
        # tempo antes da origem o crescimento é medido, e cada cenário, o jeito de projetar e a janela dele.
        da_janela = simulador.get_by_test_id("simulador-frase-da-janela")
        expect(da_janela).to_contain_text("Janela histórica: o crescimento é medido em")
        expect(da_janela).to_contain_text(", a origem do cenário.")
        expect(da_janela).to_have_attribute("data-padrao", "true")
        expect(simulador.get_by_test_id("simulador-janela-inicio").locator("option:checked")).to_have_text("3 anos (desde jun/2021)")
        expect(simulador.get_by_test_id("simulador-janela-fim").locator("option:checked")).to_have_text("jun/2024")
        expect(simulador.get_by_test_id("simulador-frase-do-jeito")).to_contain_text("Forma de projetar:")
        expect(simulador.get_by_test_id("simulador-cenario-janela-inicio").locator("option").first).to_have_text("a janela geral")
        # Os atalhos da janela são só atalhos. A volta à janela padrão é pelo "Voltar ao padrão" único (antes, havia um atalho
        # "Janela padrão (3 anos)" aqui): ele liga quando uma premissa sai do padrão e desliga depois de usado.
        expect(simulador.get_by_test_id("simulador-janela-padrao")).to_have_count(0)
        expect(voltar_ao_padrao).to_be_disabled()
        simulador.get_by_test_id("simulador-janela-completa").click()
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("201401")
        expect(simulador.get_by_test_id("simulador-janela-inicio").locator("option:checked")).to_have_text("10 anos e 5 meses (desde jan/2014)")
        expect(da_janela).to_have_attribute("data-padrao", "false")
        expect(voltar_ao_padrao).to_be_enabled()
        voltar_ao_padrao.click()
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("202106")
        expect(da_janela).to_have_attribute("data-padrao", "true")
        expect(voltar_ao_padrao).to_be_disabled()
        # Escolher na lista a janela igual à da base também é o padrão: "Voltar ao padrão" continua desligado.
        simulador.get_by_test_id("simulador-janela-inicio").select_option("201906")
        expect(voltar_ao_padrao).to_be_enabled()
        simulador.get_by_test_id("simulador-janela-inicio").select_option("202106")
        expect(da_janela).to_have_attribute("data-padrao", "true")
        expect(voltar_ao_padrao).to_be_disabled()

        # 7. As intervenções e a data final: os atalhos são só atalhos; qualquer mês depois do último registro vale. A faixa pedida
        # é a de 8 em cada 10, e pode ser a de 5 ou a de 9.
        simulador.get_by_test_id("simulador-avancar-2").click()
        expect(horizonte).to_have_value("2026-06")
        simulador.get_by_test_id("simulador-atalho-4").click()
        expect(horizonte).to_have_value("2028-06")
        expect(simulador.get_by_test_id("simulador-atalho-4")).to_have_attribute("aria-pressed", "true")
        horizonte.fill("2027-03")
        expect(simulador.get_by_test_id("simulador-atalho-4")).to_have_attribute("aria-pressed", "false")
        expect(simulador.get_by_test_id("simulador-faixa-em-10")).to_have_value("8")
        expect(simulador.get_by_test_id("simulador-faixa-em-10").locator("option")).to_have_text(["5", "8", "9"])
        # A intervenção vale para cada território do cenário (cada um recebe a quantidade inteira), e a tela diz isso.
        expect(simulador.get_by_test_id("simulador-por-territorio")).to_contain_text("Cada intervenção vale para cada território do cenário, não para o total")
        expect(simulador.get_by_test_id("simulador-por-territorio")).to_contain_text("com 3 territórios na seleção do Simulador")
        simulador.get_by_test_id("simulador-intervencao-nova").click()
        expect(simulador.get_by_test_id("simulador-intervencao-em")).to_have_value("2025-06")
        expect(simulador.get_by_test_id("simulador-intervencao-permanencia")).to_have_value("100")
        # A permanência em frase, com o campo dentro dela; trocá-la liga o "Voltar ao padrão", que a devolve aos 100%.
        expect(simulador.get_by_test_id("simulador-frase-da-permanencia")).to_contain_text("Dos médicos acrescentados, a cada ano permanecem")
        simulador.get_by_test_id("simulador-intervencao-permanencia").fill("90")
        expect(voltar_ao_padrao).to_be_enabled()
        voltar_ao_padrao.click()
        expect(simulador.get_by_test_id("simulador-intervencao-permanencia")).to_have_value("100")
        expect(voltar_ao_padrao).to_be_disabled()
        simulador.get_by_test_id("simulador-intervencao-quantidade").fill("")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe quantos entram ou saem em cada intervenção.")
        simulador.get_by_test_id("simulador-intervencao-quantidade").fill("3")
        assert len(pedidos) == pedidos_do_simples, "nada é calculado antes de \"Calcular os cenários\""

        # 8. "Calcular os cenários": o pedido leva a seleção local inteira, a data final, o cenário e a persistência como referência.
        expect(simulador.get_by_test_id("simulador-calcular")).to_have_text("Calcular os cenários")
        corpo, enviado = calcular()
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
        # O método padrão é o que a base escolheu para os municípios: na V3, ele deixou de ser provisório.
        assert (cenario["metodo"]["escolhido_pela_base"], cenario["metodo"]["e_o_escolhido"], cenario["metodo"]["provisorio"]) == ("M0d", True, False), cenario["metodo"]
        assert "acréscimo de 3 médicos em cada território do cenário, em jun/2025, com permanência total (hipótese)" in cenario["texto"], cenario["texto"]
        assert all(item["cenarios"][0]["final"]["intervencao"] == 3 for item in corpo["territorios"]), "cada território recebe os 3 médicos"
        assert cenario["final"]["faixa"] and cenario["final"]["faixa"]["anos"] == 3 and cenario["final"]["faixa"]["validada"] is False, cenario["final"]
        assert cenario["final"]["faixa"]["estado"] == "provisoria" and cenario["faixa"]["em_10"] == 8, cenario["final"]
        expect(simulador.get_by_test_id("simulador-foco")).to_have_value(RIO_RUFINO)
        resultado = simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="c1"]')
        expect(resultado).to_have_attribute("data-metodo", "M0d")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("RIO RUFINO (SC) teria")
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("Base: registros até jun/2024.")
        expect(resultado).not_to_contain_text("método provisório")   # a marca ficou só para o Brasil como território (bloco 17)
        expect(resultado.get_by_test_id("simulador-contas")).to_contain_text("Na data final, neste território: base do cenário de ")
        expect(resultado.get_by_test_id("simulador-contas")).to_contain_text(" + 3 da intervenção = ")
        expect(simulador.get_by_test_id("simulador-tabela").locator("caption")).to_contain_text("Cada intervenção vale para cada território")
        expect(simulador.get_by_test_id("simulador-tabela").locator("caption")).to_contain_text("entre parênteses, a faixa de 8 em cada 10, quando há")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 8 em cada 10 em mar/2027: de ")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text(PROVISORIA)
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="FAIXA_PROVISORIA"]')).to_have_count(1)
        # O registro de jun/2023 (4 → 87 → 5) é um pico que volta: fica fora da base do cenário, com o aviso.
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="PICO_FORA_DO_AJUSTE"]')).to_contain_text("jun/2023")
        # Com 9 médicos no cenário, o painel da hipótese aparece, com o mesmo título do modo simples ("Poucos médicos, no cenário").
        assert cenario["hipotetico"]["inteiro"] == 9 and cenario["hipotetico"]["classe"] is None, cenario["hipotetico"]
        expect(resultado.get_by_test_id("simulador-hipotetico")).to_contain_text("Poucos médicos, no cenário")
        expect(resultado.get_by_test_id("simulador-hipotetico")).not_to_contain_text("Dependência de poucos médicos")
        expect(simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="m0"] [data-testid="simulador-texto"]')).to_have_text(
            referencia["texto"])
        # AJ-05 (18/11/2026): a persistência, como referência, não é a forma escolhida pela base: a faixa dela fica indisponível, e o
        # motivo, escrito pelo motor, diz "forma de projetar" (antes, "jeito"). Nenhum texto à vista no Simulador traz "jeito" nem
        # "por convenção".
        assert referencia["faixa"]["motivo"] == (
            "A faixa de 8 em cada 10 só existe para a forma de projetar e a janela que a própria base escolheu (persistência com o "
            "crescimento recente do estado, com os 3 anos até a origem). Com outra forma ou outra janela, não há faixa."), referencia["faixa"]
        expect(simulador.locator('[data-testid="simulador-cenario-resultado"][data-id="m0"] [data-testid="simulador-faixa-texto"]')).to_have_text(
            "Faixa de 8 em cada 10: indisponível. " + referencia["faixa"]["motivo"])
        texto_a_vista = simulador.inner_text().lower()
        assert "jeito" not in texto_a_vista and "convenção" not in texto_a_vista, "jeito ou convenção à vista no Simulador"
        # O gráfico: o observado (22 registros reais), a base de cada cenário, os eventos da intervenção e a faixa de 8 em cada 10.
        expect(grafico.get_by_test_id("simulador-observado")).to_have_count(22)
        expect(grafico.get_by_test_id("simulador-curva")).to_have_count(2)
        expect(grafico.locator('[data-testid="simulador-curva"][data-cenario="c1"]')).to_have_attribute("data-metodo", "M0d")
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(1)
        expect(grafico.get_by_test_id("simulador-faixa")).to_have_count(1)
        expect(grafico).to_contain_text("observado (registros reais)")
        expect(grafico).to_contain_text("banda: faixa de 8 em cada 10")
        expect(grafico).to_contain_text("Fonte: base do Brasil (medicina), registros de janeiro e junho até jun/2024.")
        # AJ-03: no lugar da linha das versões, a janela deste cálculo, como o motor a mandou.
        expect(simulador.get_by_test_id("simulador-versoes")).to_have_count(0)
        janela = corpo["janela"]
        assert (janela["inicio"], janela["fim"], janela["padrao"]) == ("202106", "202406", True), janela
        expect(simulador.get_by_test_id("simulador-janela-do-calculo")).to_have_text(
            "Janela deste cálculo: de " + curta(janela["inicio"]) + " a " + curta(janela["fim"]) + (" (a janela padrão)" if janela["padrao"] else "") +
            ". Cada cenário parte do último registro usável do território nessa janela.")
        expect(grafico.locator("svg").first).to_contain_text("simulado (hipótese)")
        linha = simulador.locator('[data-testid="simulador-linha"][data-id="' + RIO_RUFINO + '"]')
        expect(linha.locator('[data-testid="simulador-final"][data-cenario="c1"]')).to_contain_text("último valor com o crescimento do estado")
        expect(linha.locator('[data-testid="simulador-final"][data-cenario="m0"]')).to_contain_text("último valor mantido")
        page.screenshot(path=str(OUTPUT / "simulador-01-resultados-real.png"), full_page=True)

        # 9. O Paraná como unidade: o jeito que a base escolheu para os estados (a taxa composta de 3 anos), que na V3 não é mais
        # provisório, e sem faixa, com o motivo do motor.
        simulador.get_by_test_id("simulador-foco").select_option("uf:" + PR)
        do_parana = do_territorio(corpo, "uf:" + PR)["cenarios"][0]
        assert (do_parana["metodo"]["usado"], do_parana["metodo"]["escolhido_pela_base"], do_parana["metodo"]["provisorio"]) == ("M1", "M1", False), do_parana["metodo"]
        assert do_parana["faixa"]["motivo"] == SEM_CASOS and do_parana["final"]["faixa"] is None, do_parana["faixa"]
        expect(resultado).to_have_attribute("data-metodo", "M1")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(do_parana["texto"])
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_have_text("Faixa de 8 em cada 10: indisponível. " + SEM_CASOS)
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="PADRAO_PROVISORIO_DO_NIVEL"]')).to_have_count(0)
        expect(resultado).not_to_contain_text("método provisório")
        expect(grafico.get_by_test_id("simulador-faixa")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-resultados")).to_contain_text("médicos únicos no estado")

        # 10. As estatísticas históricas, só descritivas: a média aritmética aparece, e nenhum método a usa.
        simulador.get_by_test_id("simulador-foco").select_option(BRASILIA)
        simulador.get_by_test_id("simulador-etapa-2").click()
        estatisticas = simulador.get_by_test_id("simulador-estatisticas")
        expect(estatisticas).to_contain_text("Estatísticas históricas de BRASILIA (DF) (só descrição do passado)")
        expect(estatisticas.get_by_test_id("simulador-media-aritmetica")).not_to_have_text("—")
        expect(estatisticas).to_contain_text("por isso não é usada para projetar")

        # 11. Um segundo cenário (só no modo avançado), com a taxa composta da janela. Mudar as escolhas deixa o cálculo desatualizado.
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
        corpo, enviado = calcular()
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

        # 12. A avaliação dos métodos (AJ-03, 18/11/2026: na exportação, não mais na tela): as faixas de 8 em cada 10 e os erros da
        # retroprojeção, pelas dez faixas de porte da régua comum (de "1 a 3" a "10.000 ou mais"), com a conferência de cada faixa,
        # os mesmos números do motor que a tela mostrava até então.
        nome_da_avaliacao, avaliacao = da_avaliacao()
        assert nome_da_avaliacao == "simulador_avaliacao_dos_metodos_202406.json", nome_da_avaliacao
        assert avaliacao["retroprojecao"] == corpo["retroprojecao"], "a avaliação exportada leva os números do motor, sem leitura"
        assert avaliacao["janela"]["inicio"] == corpo["janela"]["inicio"] and avaliacao["janela"]["fim"] == corpo["janela"]["fim"], avaliacao["janela"]
        # As faixas e a tabela de erros que a tela mostrava são as do nível dos municípios, no alto da retroprojeção.
        retro = avaliacao["retroprojecao"]
        das_faixas = [item for item in retro["faixas"] if item.get("em_10", 8) == 8]
        portes = list(dict.fromkeys(item["porte"] for item in das_faixas))
        assert portes == ["1 a 3", "4 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 a 999", "1.000 a 2.999", "3.000 a 9.999",
                          "10.000 ou mais"], portes
        um_ano = next(item for item in das_faixas if item["porte"] == "1 a 3" and item["anos"] == 1)
        assert (round(um_ano["inferior_pct"]), round(um_ano["superior_pct"]), um_ano["estado"], um_ano["origens"], um_ano["casos"]) == (
            -9, 87, "conferida", 7, 4039), um_ano
        quatro_anos = next(item for item in das_faixas if item["porte"] == "1 a 3" and item["anos"] == 4)
        assert (quatro_anos["estado"], quatro_anos["origens"], quatro_anos["casos"]) == ("provisoria", 4, 2715), quatro_anos
        # A tabela de erros traz os métodos que a retroprojeção da base tem: na do Brasil, cinco, com o crescimento da base toda (M0g).
        da_tabela = {(item["metodo"], item["porte"], item["anos"]): item for item in retro["tabela"]}
        assert {metodo for metodo, _, _ in da_tabela} >= {"M0d", "M0g", "M1", "M2", "M3"}, sorted({metodo for metodo, _, _ in da_tabela})
        frente = [da_tabela[(metodo, "1 a 3", 4)]["frente_ao_m0"] for metodo in ("M0d", "M0g", "M1", "M2", "M3")]
        assert all(abs(valor - esperado) < 0.005 for valor, esperado in zip(frente, (0.90, 0.90, 1.29, 1.16, 1.26))), frente
        expect(simulador.get_by_test_id("simulador-faixas")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-erros")).to_have_count(0)

        # 13. As exportações: o CSV dos resultados e o JSON do cenário (com a versão do método e da base).
        with page.expect_download() as baixado:
            simulador.get_by_test_id("simulador-exportar-csv").click()
        assert baixado.value.suggested_filename == "cenarios_202703.csv", baixado.value.suggested_filename
        csv = Path(baixado.value.path()).read_text(encoding="utf-8-sig")
        assert csv.startswith("Identificador;Território;Tipo;Unidade de contagem;Cenário;") and "retirada_acima_do_estoque" in csv, csv[:300]
        assert ";Faixa de 80%: inferior;Faixa de 80%: superior;" in csv.splitlines()[0], csv[:600]   # 8 em cada 10
        assert RIO_RUFINO + ";RIO RUFINO (SC);municipio;" in csv and ";cenário hipotético;" in csv, csv[:600]
        with page.expect_download() as baixado:
            simulador.get_by_test_id("simulador-exportar-cenario").click()
        assert baixado.value.suggested_filename == "cenario_do_simulador.json"
        arquivo = OUTPUT / "simulador-cenario-exportado.json"
        baixado.value.save_as(str(arquivo))
        exportado = json.loads(arquivo.read_text(encoding="utf-8"))
        assert exportado["formato"] == "ADT-CENARIO/1" and exportado["versao_do_metodo"] == corpo["versao"] == VERSAO, exportado
        assert exportado["base"]["versao"] and exportado["base"]["ultimo_registro"] == "202406", exportado["base"]
        assert exportado["selecao_local"] == {"municipios": [RIO_RUFINO, BRASILIA], "estados": [PR], "conjuntos": []}, exportado["selecao_local"]
        assert [item["id"] for item in exportado["cenarios"]] == ["c1", "c2"] and exportado["horizonte"] == "202703", exportado
        assert exportado["modo"] == "avancado", exportado["modo"]

        # 13b. Um cenário importado com um conjunto (MANAUS e TEFE): na tabela, o conjunto é a "soma das projeções dos membros", e a
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
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 8 em cada 10 (aproximação) em mar/2027: de ")
        expect(grafico).to_contain_text("banda: faixa de 8 em cada 10 (aproximação)")
        expect(simulador.get_by_test_id("simulador-resultados")).to_contain_text("soma das contagens dos componentes")
        page.screenshot(path=str(OUTPUT / "simulador-03-conjunto-real.png"), full_page=True)

        # 14. "Copiar de novo a seleção principal" refaz a cópia; importar o cenário exportado traz a seleção local e os cenários de volta.
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

        # 15. "Aplicar à seleção principal": só agora a seleção principal muda, num passo do Desfazer.
        simulador.get_by_test_id("simulador-aplicar-principal").click()
        expect(simulador.get_by_test_id("simulador-aviso-local")).to_have_text("A seleção do Simulador foi aplicada à seleção principal.")
        expect(resumo).not_to_have_text(principal)
        expect(resumo).to_contain_text("Paraná")
        area.get_by_test_id("analise-desfazer").click()
        expect(resumo).to_have_text(principal)
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "3")  # o Desfazer não mexe na seleção local

        # 16. "Abrir no Simulador" (etapa 5): do Detector de Sinais, MANAUS (AM) vai ao Simulador com o contexto analítico (o
        # território, a data avaliada e os sinais com nível). O Simulador abre no modo simples, com "Só continuar como vinha"; a
        # seleção local fica só com ele e não acompanha a seleção principal, que não muda. Manaus está acima do patamar: não há
        # "Simular recuperação" para ele. Em jun/2024, Manaus tem um sinal com nível (comando V23): perdeu 4,7 pontos de percentil em
        # 2 anos, raro entre os municípios de 3.000 a 9.999 médicos.
        area.get_by_test_id("analise-ferramenta-detector").click()
        detector = area.get_by_test_id("detector")
        expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
        # O detalhe pedido ao abrir a linha (desde o AJ-04, a lista pede sozinha o detalhe dos territórios à vista com mais de um
        # sinal com nível; Manaus tem um).
        with page.expect_response(lambda r: r.url.endswith("/api/detector") and r.request.method == "POST" and
                                  options_of(r.request).get("detalhe") == MANAUS, timeout=180000):
            detector.locator('[data-testid="detector-linha"][data-id="' + MANAUS + '"]').get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", MANAUS)
        expect(detector.get_by_test_id("detector-simular-recuperacao")).to_have_count(0)
        detector.get_by_test_id("detector-abrir-no-simulador").click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(simples).to_have_attribute("data-teste", "continuar")
        expect(territorio.locator("option")).to_have_text(["MANAUS (AM)"])
        expect(territorio).to_have_value(MANAUS)
        aviso = simulador.get_by_test_id("simulador-do-detector")
        expect(aviso).to_have_attribute("data-recuperacao", "false")
        expect(aviso).to_contain_text("Aberto pelo Detector de Sinais: MANAUS (AM), avaliado em jun/2024")
        expect(aviso).to_contain_text("Sinais com nível lá: Perda de posição (moderado).")
        expect(aviso).to_contain_text("o que vem depois do último registro é cenário hipotético")
        expect(aviso).not_to_contain_text("Simular recuperação")
        # A seleção local, as referências e o planejamento inverso com calendário ficam no modo avançado.
        simulador.get_by_test_id("simulador-modo-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        expect(simulador).to_have_attribute("data-etapa", "1")
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "1")
        expect(local(MANAUS)).to_have_count(1)
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_have_attribute("data-acompanha", "false")
        expect(simulador.get_by_test_id("simulador-origem-da-selecao")).to_contain_text("veio do Detector de Sinais")
        expect(simulador.get_by_test_id("simulador-nao-acompanha")).to_contain_text("não acompanha a seleção principal")
        expect(resumo).to_have_text(principal)

        # 17. O Brasil como território, só no Simulador (a contagem nacional), e as referências de comparação: FLORIANOPOLIS (SC),
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
        # A comparação em frase (Proposta V3, seção C.5): pela diferença (o padrão), pela razão ou pela taxa por 1.000 habitantes.
        expect(simulador.get_by_test_id("simulador-frase-da-comparacao")).to_contain_text("Comparar cada cenário com as referências por")
        expect(simulador.get_by_test_id("simulador-metrica")).to_have_value("diferenca")
        expect(simulador.get_by_test_id("simulador-metrica").locator("option")).to_have_text(
            ["diferença (em médicos)", "razão (quantas vezes o valor da referência)", "taxa por 1.000 habitantes"])
        expect(simulador.get_by_test_id("simulador-populacao")).to_have_count(0)
        expect(simulador.get_by_test_id("simulador-metrica-apoio")).to_contain_text("não é comparar a suficiência do atendimento")
        expect(resumo).to_have_text(principal)
        simulador.get_by_test_id("simulador-etapa-3").click()
        simulador.get_by_test_id("simulador-atalho-4").click()
        corpo, enviado = calcular()
        assert enviado == {
            "base": {"municipios": {"todos": False, "estados": [], "ids": [MANAUS]}}, "brasil": True, "horizonte": "202806",
            "cenarios": [{"id": "c1", "nome": "Cenário 1", "metodo": "padrao"}, {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}],
            "referencias": [{"id": "r1", "tipo": "dinamica", "territorio": FLORIANOPOLIS}, {"id": "r2", "tipo": "fixa", "territorio": "br"},
                            {"id": "r3", "tipo": "valor", "valor": 6500, "rotulo": "Valor informado por você"}]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == [MANAUS, "br"], corpo["territorios"]
        assert corpo["comparacao"] == {"metrica": "quantidade", "forma": "diferenca", "populacao_pct_ao_ano": None,
                                       "hipotese_de_populacao": None}, corpo["comparacao"]
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
        expect(resultado).not_to_contain_text("método provisório")
        # No gráfico, as curvas das referências que cabem na escala; a do Brasil fica na legenda, fora da escala.
        expect(grafico.get_by_test_id("simulador-referencia")).to_have_count(2)
        expect(grafico.locator('[data-testid="simulador-referencia-legenda"][data-ref="r1"]')).to_contain_text(
            "R1: referência FLORIANOPOLIS (SC) (dinâmica: ")
        do_brasil_na_legenda = grafico.locator('[data-testid="simulador-referencia-legenda"][data-ref="r2"]')
        expect(do_brasil_na_legenda).to_have_attribute("data-na-escala", "false")
        expect(do_brasil_na_legenda).to_contain_text("fora da escala deste gráfico (502.495 médicos na data final)")
        expect(simulador.get_by_test_id("simulador-referencias-do-calculo")).to_contain_text("comparadas por quantidade de médicos")
        page.screenshot(path=str(OUTPUT / "simulador-04-referencias-real.png"), full_page=True)
        # O Brasil no gráfico: uma série só não tem retroprojeção própria, e vale o jeito escolhido para os estados (a taxa composta de
        # 3 anos na contagem nacional). É o único território em que o método padrão continua provisório; não há faixa.
        simulador.get_by_test_id("simulador-foco").select_option("br")
        do_brasil = do_territorio(corpo, "br")["cenarios"][0]
        assert do_brasil["metodo"]["usado"] == "M1" and do_brasil["final"]["faixa"] is None and "hipotetico" not in do_brasil, do_brasil["metodo"]
        assert do_brasil["metodo"]["provisorio"] is True, do_brasil["metodo"]
        expect(resultado).to_have_attribute("data-metodo", "M1")
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(do_brasil["texto"])
        expect(resultado).to_contain_text("método provisório")
        expect(resultado.locator('[data-testid="simulador-avisos"] li[data-codigo="PADRAO_PROVISORIO_DO_NIVEL"]')).to_contain_text(
            "Para o Brasil, o método padrão é provisório: uma série só não tem retroprojeção própria")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_have_text(
            "Faixa de 8 em cada 10: indisponível. Não há faixa para o Brasil: uma série só não tem retroprojeção própria.")
        expect(simulador.get_by_test_id("simulador-resultados")).to_contain_text("médicos únicos no Brasil (fonte nacional)")
        expect(da_comparacao("r2")).to_contain_text("A referência é o próprio território.")
        with page.expect_download() as baixado:
            simulador.get_by_test_id("simulador-exportar-comparacoes").click()
        assert baixado.value.suggested_filename == "comparacoes_202806.csv", baixado.value.suggested_filename
        csv = Path(baixado.value.path()).read_text(encoding="utf-8-sig")
        assert csv.startswith("Identificador;Território;Cenário;Referência;Tipo da referência;O que é a referência;Métrica;Data;"), csv[:300]
        assert "não alcança no horizonte simulado" in csv and "já está no nível da referência ou acima na origem" in csv, csv[:900]

        # 17a. A comparação pela razão e pela taxa, com a população crescendo (Proposta V3, seção C.5; etapa 7 do comando V23). Pela
        # razão, a frase de cada comparação diz quantas vezes o valor da referência o território teria; os números são os mesmos.
        com_referencias = enviado
        simulador.get_by_test_id("simulador-foco").select_option(MANAUS)
        simulador.get_by_test_id("simulador-etapa-1").click()
        simulador.get_by_test_id("simulador-metrica").select_option("razao")
        expect(voltar_ao_padrao).to_be_enabled()
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
        assert enviado == {**com_referencias, "comparacao": {"forma": "razao"}}, enviado
        assert (corpo["comparacao"]["metrica"], corpo["comparacao"]["forma"]) == ("quantidade", "razao"), corpo["comparacao"]
        pela_razao = {item["id"]: item for item in do_territorio(corpo, MANAUS)["cenarios"][0]["comparacoes"]}
        assert all(item["forma"] == "razao" and " vezes o valor da referência" in item["texto"] for item in pela_razao.values()), pela_razao
        assert all(pela_razao[chave]["pontos"] == comparacoes[chave]["pontos"] for chave in ("r1", "r2", "r3")), "os números não mudam com a forma"
        for chave in ("r1", "r2", "r3"):
            expect(da_comparacao(chave)).to_contain_text(pela_razao[chave]["texto"])
        # Pela taxa: a população é a do último registro ou cresce x% ao ano depois dele, uma hipótese da pessoa. Sem a taxa de
        # crescimento, nada é pedido; com ela, o pedido a leva, e a resposta, a tela e cada frase dizem a hipótese.
        simulador.get_by_test_id("simulador-etapa-1").click()
        simulador.get_by_test_id("simulador-metrica").select_option("taxa")
        populacao = simulador.get_by_test_id("simulador-populacao")
        expect(populacao).to_have_value("constante")
        expect(populacao.locator("option")).to_have_text(["igual à do último registro (jun/2024)", "crescendo"])
        expect(simulador.get_by_test_id("simulador-populacao-pct")).to_have_count(0)
        populacao.select_option("crescendo")
        expect(simulador.get_by_test_id("simulador-populacao-pct")).to_have_value("")
        expect(simulador.get_by_test_id("simulador-calcular-direto")).to_be_disabled()
        simulador.get_by_test_id("simulador-populacao-pct").fill("25")
        expect(simulador.get_by_test_id("simulador-calcular-direto")).to_be_disabled()
        simulador.get_by_test_id("simulador-populacao-pct").fill("1,5")
        expect(simulador.get_by_test_id("simulador-metrica-apoio")).to_contain_text("Hipótese sua: a população cresce essa taxa ao ano depois do último registro (jun/2024)")
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
        assert enviado == {**com_referencias, "comparacao": {"metrica": "taxa", "populacao_pct_ao_ano": 1.5}}, enviado
        assert corpo["comparacao"] == {
            "metrica": "taxa", "forma": "diferenca", "populacao_pct_ao_ano": 1.5,
            "hipotese_de_populacao": "crescendo 1,5% ao ano depois de jun/2024 (hipótese sua), a mesma taxa em todos os territórios; até essa "
                                     "data, a população de jun/2024"}, corpo["comparacao"]
        por_taxa = {item["id"]: item for item in do_territorio(corpo, MANAUS)["cenarios"][0]["comparacoes"]}
        assert all(item["estado"] == "calculada" and item["metrica"] == "taxa" for item in por_taxa.values()), por_taxa
        assert por_taxa["r1"]["texto"].endswith("Hipótese sua: população crescendo 1,5% ao ano depois de jun/2024, a mesma taxa no território e na "
                                                "referência."), por_taxa["r1"]["texto"]
        assert por_taxa["r3"]["texto"].endswith("Hipótese sua: população crescendo 1,5% ao ano depois de jun/2024; o valor informado não muda."), (
            por_taxa["r3"]["texto"])
        # A população cresce só depois do último registro: na origem, a taxa é a do registro; 4 anos depois, a de Manaus é a do
        # cenário dividida por 1,015⁴.
        do_cenario = do_territorio(corpo, MANAUS)["cenarios"][0]
        populacao_de_manaus = 1000 * do_cenario["parametros"]["n0"] / por_taxa["r1"]["inicial"]["territorio"]
        assert abs(por_taxa["r1"]["final"]["territorio"] - 1000 * do_cenario["final"]["total"] / (populacao_de_manaus * 1.015 ** 4)) < 1e-6, por_taxa["r1"]["final"]
        for chave in ("r1", "r2", "r3"):
            expect(da_comparacao(chave)).to_contain_text(por_taxa[chave]["texto"])
        expect(simulador.get_by_test_id("simulador-referencias-do-calculo")).to_contain_text(
            "comparadas por taxa por 1.000 habitantes (hipótese: população crescendo 1,5% ao ano depois de jun/2024 (hipótese sua)")
        page.screenshot(path=str(OUTPUT / "simulador-04b-comparacao-por-taxa-real.png"), full_page=True)
        # "Voltar ao padrão" desfaz a comparação por taxa e a hipótese de população de uma vez: o pedido volta a ser o de antes.
        voltar_ao_padrao.click()
        expect(voltar_ao_padrao).to_be_disabled()
        simulador.get_by_test_id("simulador-etapa-1").click()
        expect(simulador.get_by_test_id("simulador-metrica")).to_have_value("diferenca")
        expect(simulador.get_by_test_id("simulador-populacao")).to_have_count(0)
        expect(referencias).to_have_attribute("data-total", "3")   # as referências não são premissas: ficam
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
        assert enviado == com_referencias, enviado

        # 17b. O que só o modo avançado escolhe fica no modo avançado (ajuste de 14/11/2026). Com uma janela geral (os últimos 5 anos)
        # e as três referências, o pedido do modo avançado leva as duas coisas. No modo simples, o pedido leva só o território em
        # análise, a data final e o cenário: a janela e as referências ficam guardadas, e a resposta vem com a janela padrão e sem
        # comparações. De volta ao modo avançado, elas são pedidas de novo. O jeito de projetar escolhido no modo avançado também
        # não passa despercebido: o modo simples avisa, e o "Voltar ao padrão" único desfaz a escolha (etapa 7 do comando V23).
        simulador.get_by_test_id("simulador-etapa-2").click()
        simulador.get_by_test_id("simulador-janela-5-anos").click()
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("201906")
        expect(simulador.get_by_test_id("simulador-janela-fim")).to_have_value("202406")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
        com_a_janela = {**com_referencias, "janela": {"inicio": "201906", "fim": "202406"}}
        assert enviado == com_a_janela, enviado
        assert corpo["janela"] == {"inicio": "201906", "fim": "202406", "registros": 11, "anos": 5.0, "padrao": False}, corpo["janela"]
        assert [item["id"] for item in corpo["referencias"]] == ["r1", "r2", "r3"], corpo["referencias"]
        simulador.get_by_test_id("simulador-foco").select_option(MANAUS)
        expect(resultado.get_by_test_id("simulador-texto")).to_have_text(do_territorio(corpo, MANAUS)["cenarios"][0]["texto"])
        expect(resultado.get_by_test_id("simulador-texto")).to_contain_text("janela de jun/2019 a jun/2024")
        expect(resultado.get_by_test_id("simulador-comparacao")).to_have_count(3)
        simulador.get_by_test_id("simulador-modo-simples").click()
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(territorio.locator("option")).to_have_text(["MANAUS (AM)", "Brasil"])
        expect(territorio).to_have_value(MANAUS)
        expect(simples).to_have_attribute("data-teste", "continuar")
        do_avancado = simulador.get_by_test_id("simulador-metodo-do-avancado")
        expect(do_avancado).to_have_count(0)
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(MANAUS), "horizonte": "202806", "cenarios": [C1, PERSISTENCIA]}, enviado
        assert not {"janela", "referencias", "comparacao", "brasil"} & set(enviado), enviado
        assert corpo["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7, "anos": 3.0, "padrao": True}, corpo["janela"]
        assert corpo["referencias"] == [] and [item["id"] for item in corpo["territorios"]] == [MANAUS], corpo["referencias"]
        do_simples = corpo["territorios"][0]["cenarios"][0]
        assert "comparacoes" not in do_simples and do_simples["metodo"]["usado"] == "M0d", do_simples["metodo"]
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples).to_have_attribute("data-metodo", "M0d")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(do_simples["texto"])
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_contain_text("janela de jun/2021 a jun/2024")
        expect(grafico.get_by_test_id("simulador-referencia")).to_have_count(0)
        expect(grafico.get_by_test_id("simulador-referencia-legenda")).to_have_count(0)
        # De volta ao modo avançado: a janela geral e as referências continuam lá, e o pedido volta a levá-las.
        simulador.get_by_test_id("simulador-modo-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")   # o cálculo à vista é o do modo simples
        simulador.get_by_test_id("simulador-etapa-2").click()
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("201906")
        expect(simulador.get_by_test_id("simulador-metodo")).to_have_value("padrao")
        simulador.get_by_test_id("simulador-etapa-1").click()
        expect(referencias).to_have_attribute("data-total", "3")
        corpo, enviado = do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
        assert enviado == com_a_janela, enviado
        assert [item["id"] for item in corpo["referencias"]] == ["r1", "r2", "r3"] and corpo["janela"]["padrao"] is False, corpo["janela"]
        expect(resultado.get_by_test_id("simulador-comparacao")).to_have_count(3)
        # Um jeito de projetar escolhido à mão no modo avançado (a taxa composta), sem calcular: o modo simples avisa, e o "Voltar ao
        # padrão" único, no alto, desfaz essa escolha e a janela de 5 anos de uma vez — a janela padrão de volta, para os blocos
        # seguintes.
        simulador.get_by_test_id("simulador-etapa-2").click()
        simulador.get_by_test_id("simulador-metodo").select_option("M1")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        simulador.get_by_test_id("simulador-modo-simples").click()
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(do_avancado).to_contain_text(
            "Este cenário usa uma forma de projetar escolhida no modo avançado (taxa composta da janela), e não a que a base escolheu.")
        expect(do_avancado).to_contain_text("“Voltar ao padrão”, no alto, desfaz essa escolha.")
        expect(do_avancado.get_by_role("button")).to_have_count(0)
        expect(voltar_ao_padrao).to_be_enabled()
        voltar_ao_padrao.click()
        expect(do_avancado).to_have_count(0)
        expect(voltar_ao_padrao).to_be_disabled()
        simulador.get_by_test_id("simulador-modo-avancado").click()
        expect(simulador).to_have_attribute("data-modo", "avancado")
        simulador.get_by_test_id("simulador-etapa-2").click()
        expect(simulador.get_by_test_id("simulador-metodo")).to_have_value("padrao")
        expect(simulador.get_by_test_id("simulador-janela-inicio")).to_have_value("202106")
        expect(simulador.get_by_test_id("simulador-frase-da-janela")).to_have_attribute("data-padrao", "true")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")

        # 18. O planejamento inverso: a meta hipotética de alcançar a referência (FLORIANOPOLIS), com um acréscimo por ano. O motor
        # devolve o menor número inteiro de médicos por evento; o cenário só o recebe por comando ("Usar como intervenção deste
        # cenário") e, recalculado, alcança a meta.
        simulador.get_by_test_id("simulador-etapa-1").click()
        local("br").get_by_role("button").click()
        expect(simulador.get_by_test_id("simulador-locais")).to_have_attribute("data-total", "1")
        simulador.get_by_test_id("simulador-etapa-3").click()
        simulador.get_by_test_id("simulador-plano-novo").click()
        plano = simulador.get_by_test_id("simulador-plano")
        expect(plano).to_have_attribute("data-meta", "valor")
        expect(simulador.get_by_test_id("simulador-pendencia")).to_have_text("Informe a meta: um número acima de zero.")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_disabled()
        plano.get_by_test_id("simulador-plano-meta").select_option("referencia")
        expect(plano.get_by_test_id("simulador-plano-referencia")).to_have_value("r1")
        expect(plano.get_by_test_id("simulador-plano-em")).to_have_value("2025-06")
        plano.get_by_test_id("simulador-plano-periodica").check()
        expect(plano.get_by_test_id("simulador-plano-ate")).to_have_value("2027-06")
        plano.get_by_test_id("simulador-plano-ate").fill("2028-06")
        expect(plano).to_contain_text("não um plano")
        corpo, enviado = calcular()
        assert "brasil" not in enviado and enviado["cenarios"][0] == {"id": "c1", "nome": "Cenário 1", "metodo": "padrao", "planejamento": {
            "meta": {"tipo": "referencia", "referencia": "r1"}, "em": "202506", "ate": "202806", "a_cada_meses": 12}}, enviado
        assert "janela" not in enviado and len(enviado["referencias"]) == 3, enviado   # a janela padrão de volta; as referências continuam
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
        corpo, enviado = calcular()
        assert enviado["cenarios"][0] == {"id": "c1", "nome": "Cenário 1", "metodo": "padrao", "intervencoes": [
            {"tipo": "acrescimo", "quantidade": 387, "em": "202506", "ate": "202806", "a_cada_meses": 12}]}, enviado
        assert "faixa" not in enviado, "a faixa de 8 em cada 10 é a padrão: o pedido não a leva"
        aplicado = do_territorio(corpo, MANAUS)["cenarios"][0]
        assert abs(aplicado["final"]["total"] - planejado["resultado"]) < 1e-6 and aplicado["final"]["total"] >= planejado["meta"]["valor"], aplicado["final"]
        da_meta = next(item for item in aplicado["comparacoes"] if item["id"] == "r1")
        assert da_meta["alcance"] == {"estado": "alcanca", "data": "202806"}, da_meta["alcance"]
        expect(da_comparacao("r1")).to_have_attribute("data-alcance", "alcanca")
        expect(da_comparacao("r1")).to_contain_text("No cenário, alcança a referência em jun/2028")
        expect(grafico.get_by_test_id("simulador-evento")).to_have_count(4)
        expect(resultado.get_by_test_id("simulador-planejamento")).to_have_count(0)
        expect(resumo).to_have_text(principal)

        # 18b. A faixa pedida (etapa 3 do modo avançado): com 5 em cada 10, o pedido leva `faixa: 5`, e o resultado, a legenda do
        # gráfico e a tabela passam a dizer "5 em cada 10" (a faixa é mais estreita que a de 8 em cada 10). De volta a 8 em cada 10,
        # que é a padrão, o pedido não leva a faixa.
        do_pedido_anterior, dos_8 = enviado, aplicado["final"]["faixa"]
        simulador.get_by_test_id("simulador-etapa-3").click()
        simulador.get_by_test_id("simulador-faixa-em-10").select_option("5")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        corpo, enviado = calcular()
        assert enviado == {**do_pedido_anterior, "faixa": 5}, enviado
        assert corpo["faixa"] == {"em_10": 5, "opcoes": [5, 8, 9], "padrao": 8} and corpo["retroprojecao"]["em_10"] == 5, corpo["faixa"]
        dos_5 = do_territorio(corpo, MANAUS)["cenarios"][0]
        assert dos_5["faixa"]["em_10"] == 5 and dos_5["final"]["total"] == aplicado["final"]["total"], dos_5["faixa"]
        assert dos_8["inferior"] < dos_5["final"]["faixa"]["inferior"] < dos_5["final"]["faixa"]["superior"] < dos_8["superior"], (dos_5["final"], dos_8)
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 5 em cada 10 em jun/2028: de ")
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("em 5 de cada 10 casos de territórios do mesmo porte,")
        expect(grafico).to_contain_text("banda: faixa de 5 em cada 10")
        expect(simulador.get_by_test_id("simulador-tabela").locator("caption")).to_contain_text("entre parênteses, a faixa de 5 em cada 10, quando há")
        simulador.get_by_test_id("simulador-etapa-3").click()
        expect(simulador.get_by_test_id("simulador-faixa-em-10")).to_have_value("5")
        simulador.get_by_test_id("simulador-faixa-em-10").select_option("8")
        corpo, enviado = calcular()
        assert enviado == do_pedido_anterior, enviado
        expect(resultado.get_by_test_id("simulador-faixa-texto")).to_contain_text("Faixa de 8 em cada 10 em jun/2028: de ")
        expect(grafico).to_contain_text("banda: faixa de 8 em cada 10")

        # 19. "Simular recuperação" (Proposta V3): ABELARDO LUZ (SC) está abaixo do que já teve (54 médicos em jun/2024, para um
        # patamar de 78,25). O Detector abre o Simulador no modo simples, só com ele, com "Chegar a uma meta" marcado e o patamar
        # como meta hipotética, que a pessoa pode trocar; o aviso diz que a meta está em "O que testar". Nada é pedido antes de
        # "Calcular", e a seleção principal não muda.
        botao.click()
        expect(area).to_have_attribute("data-ferramenta", "")
        marcar_na_arvore("abelardo", ABELARDO_LUZ)
        territorios.get_by_test_id("analise-busca").fill("")
        com_abelardo = resumo.inner_text()
        assert com_abelardo != principal, com_abelardo
        area.get_by_test_id("analise-ferramenta-detector").click()
        expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
        # ABELARDO LUZ tem quatro sinais com nível: desde o AJ-04, a lista já pode ter pedido o detalhe dele (para as frases dos
        # sinais), e abrir a linha só o mostra.
        detector.locator('[data-testid="detector-linha"][data-id="' + ABELARDO_LUZ + '"]').get_by_test_id("detector-abrir").click()
        expect(detector.get_by_test_id("detector-detalhe")).to_have_attribute("data-id", ABELARDO_LUZ, timeout=180000)
        expect(detector.get_by_test_id("detector-recuperacao-apoio")).to_contain_text("meta hipotética")
        antes_da_recuperacao = len(pedidos)
        detector.get_by_test_id("detector-simular-recuperacao").click()
        expect(area).to_have_attribute("data-ferramenta", "simulador")
        expect(simulador).to_have_attribute("data-modo", "simples")
        expect(simulador).to_have_attribute("data-estado", "configurando")
        expect(aviso).to_have_attribute("data-recuperacao", "true")
        expect(aviso).to_contain_text("Aberto pelo Detector de Sinais: ABELARDO LUZ (SC), avaliado em jun/2024")
        expect(aviso).to_contain_text("Abaixo do que já teve (")
        expect(aviso).to_contain_text(
            "“Simular recuperação” trouxe, como meta hipotética que você pode trocar, a volta ao patamar anterior (em “O que testar”).")
        expect(simples).to_have_attribute("data-teste", "meta")
        expect(teste("meta")).to_be_checked()
        expect(territorio.locator("option")).to_have_text(["ABELARDO LUZ (SC)"])
        expect(territorio).to_have_value(ABELARDO_LUZ)
        # O campo mostra a meta em uso: 79, o patamar (78,25, uma média) arredondado para cima, para o resultado não parecer
        # abaixo da meta; a frase ao lado diz de onde ela veio (revisão das capturas, 14/11/2026). O pedido leva o patamar com a
        # precisão do Detector.
        expect(valor_da_meta).to_have_value("79")
        expect(simulador.get_by_test_id("simulador-teste-em")).to_have_value("2025-06")
        expect(simulador.get_by_test_id("simulador-teste-meta-origem")).to_have_text(
            "A meta veio do Detector de Sinais: o patamar anterior, de 78,25 médicos (a maior média de dois anos seguidos), arredondado "
            "para cima. É uma hipótese que você pode trocar.")
        expect(simulador.get_by_test_id("simulador-calcular")).to_be_enabled()
        page.wait_for_timeout(400)
        assert len(pedidos) == antes_da_recuperacao, "nada é calculado antes de \"Calcular\""
        corpo, enviado = calcular()
        assert enviado == {"base": so_o_municipio(ABELARDO_LUZ), "horizonte": "202606", "cenarios": [
            {"id": "c1", "nome": "Recuperação do patamar", "metodo": "padrao", "planejamento": {"meta": {"tipo": "patamar", "valor": 78.25}, "em": "202506"}},
            PERSISTENCIA]}, enviado
        assert [item["id"] for item in corpo["territorios"]] == [ABELARDO_LUZ], corpo["territorios"]
        cenario = corpo["territorios"][0]["cenarios"][0]
        planejado = cenario["planejamento"]
        # Com a meta de 79 (e não de 78,25), o menor acréscimo inteiro é de 14 médicos (antes, 13): o território teria 79.
        assert (planejado["estado"], planejado["eventos"], planejado["por_evento"]) == ("calculado", 1, 14), planejado
        assert (planejado["meta"]["valor"], planejado["meta"]["patamar"], planejado["meta"]["registros"]) == (79, 78.25, 4), planejado["meta"]
        assert planejado["resultado"] >= planejado["meta"]["valor"], planejado
        assert planejado["texto"].startswith("Meta hipotética: voltar ao patamar de 79 médicos em jun/2026 (patamar de 78,25, média de 4 "
                                             "registros, arredondado para cima). ") and planejado["texto"].endswith("não um plano."), planejado["texto"]
        assert "ABELARDO LUZ (SC) teria 79 médicos em jun/2026." in planejado["texto"], planejado["texto"]
        for proibida in ("recomenda", "é preciso", "deveria", "necessário prover"):
            assert proibida not in planejado["texto"].lower(), proibida
        expect(simulador).to_have_attribute("data-estado", "pronto")
        expect(resultado_simples).to_have_attribute("data-estado", "calculado")
        expect(resultado_simples.get_by_test_id("simulador-texto")).to_have_text(cenario["texto"])
        bloco = resultado_simples.get_by_test_id("simulador-planejamento")
        expect(bloco).to_have_attribute("data-estado", "calculado")
        expect(bloco).to_have_attribute("data-por-evento", "14")
        expect(bloco.get_by_test_id("simulador-planejamento-texto")).to_have_text(planejado["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Para chegar à meta"], ["54", "65", "precisaria acrescentar 14"])
        # No gráfico: a meta de 79, o caminho com o acréscimo de 14 em jun/2025 e a marca nessa data.
        do_plano = grafico.get_by_test_id("simulador-plano-no-grafico")
        expect(do_plano).to_have_attribute("data-meta", "79")
        expect(do_plano.get_by_test_id("simulador-meta-linha")).to_have_count(1)
        expect(do_plano.get_by_test_id("simulador-plano-curva")).to_have_count(1)
        expect(do_plano.get_by_test_id("simulador-plano-evento")).to_have_count(1)
        assert [(ponto["data"], ponto["intervencao"]) for ponto in planejado["trajetoria"]] == [
            ("202501", 0.0), ("202506", 14.0), ("202601", 14.0), ("202606", 14.0)], planejado["trajetoria"]
        expect(grafico.get_by_test_id("simulador-meta-legenda")).to_have_text(
            "meta hipotética de 79 médicos; linha contínua: o cenário com o acréscimo que alcança a meta (▼ na data do acréscimo)")
        page.screenshot(path=str(OUTPUT / "simulador-06-recuperacao-real.png"), full_page=True)
        # A meta é editável: digitar outra troca o patamar por um número da pessoa. Com 60 médicos (menos do que o cenário já
        # dá), o motor diz que ela é alcançada sem acréscimo; o gráfico mostra só a linha da meta.
        valor_da_meta.fill("60")
        expect(simulador).to_have_attribute("data-estado", "desatualizado")
        expect(simulador.get_by_test_id("simulador-teste-meta-origem")).to_have_text("A meta é uma hipótese sua.")
        corpo, enviado = calcular()
        assert enviado["cenarios"][0]["planejamento"] == {"meta": {"tipo": "valor", "valor": 60}, "em": "202506"}, enviado
        planejado = corpo["territorios"][0]["cenarios"][0]["planejamento"]
        assert planejado["estado"] == "ja_alcancada" and planejado["texto"] == (
            "Meta hipotética: 60 médicos em jun/2026. No cenário, o território já teria 65,3 médicos em jun/2026: a meta é alcançada sem "
            "acréscimo."), planejado
        expect(bloco).to_have_attribute("data-estado", "ja_alcancada")
        expect(bloco.get_by_test_id("simulador-planejamento-texto")).to_have_text(planejado["texto"])
        tres_numeros(["No último registro (jun/2024)", "Em jun/2026", "Para chegar à meta"], ["54", "65", "nada a acrescentar"])
        expect(do_plano).to_have_attribute("data-estado", "ja_alcancada")
        expect(do_plano).to_have_attribute("data-meta", "60")
        expect(do_plano.get_by_test_id("simulador-meta-linha")).to_have_count(1)
        expect(do_plano.get_by_test_id("simulador-plano-curva")).to_have_count(0)
        expect(grafico.get_by_test_id("simulador-meta-legenda")).to_have_text("meta hipotética de 60 médicos; o cenário já chega a ela, sem acréscimo")
        expect(resumo).to_have_text(com_abelardo)

        assert not chamadas_llm, "o Simulador calcula sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("SIMULADOR PASS: ferramenta na navegação, aberta no modo simples, sem pedido antes de Calcular; modo simples numa tela só (um "
          "território no pedido, frase fixa, três números, jeito escolhido pela base, os dois Entenda, faixa de 8 em cada 10 conferida em "
          "2 anos e provisória em 4, acréscimo, retirada acima do estoque, meta com 16 médicos, Paraná sem faixa com o motivo, Avançado e "
          "volta); seleção local (cópia, acréscimo de BRASILIA e do Paraná como unidade, retirada de MANAUS e recusa de CURITIBA) sem mudar "
          "a seleção principal, janela e método padrão, data final em qualquer mês, cenário com acréscimo (texto fixo do motor, gráfico com "
          "observado, base, evento e faixa; pico fora do ajuste em RIO RUFINO), estatísticas descritivas, dois cenários, retirada acima do "
          "estoque, validação dos métodos (dez faixas de porte), exportações CSV e JSON, importação do cenário, cópia de novo e Aplicar à "
          "seleção principal com Desfazer; Abrir no Simulador com o contexto do Detector, o Brasil como território (método provisório), "
          "três referências (curvas, textos, não alcança no horizonte e sobreposição), CSV das comparações, planejamento inverso (387 "
          "médicos em 4 eventos) usado como intervenção, faixa de 5 em cada 10, janela geral e referências só no pedido do modo avançado "
          "(o modo simples não as leva) e Simular recuperação (ABELARDO LUZ, meta editável).")


if __name__ == "__main__":
    main()
