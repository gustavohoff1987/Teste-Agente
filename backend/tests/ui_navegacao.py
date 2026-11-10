"""Navegação por níveis (06/11/2026, comando do responsável, itens 2 e 3), com a base versionada (somente leitura).

Confere, contra as respostas de /api/painel, /api/painel/lugar e /api/painel/mapa, os aceites do comando:
- o todo como referência: desde o comando V22 (decisão 3), sem o "Ver por": "Só os estados", na linha do Brasil da árvore, põe
  os 27 estados como unidade, e a caixa do Brasil marca os 5.570 municípios; "Confirmar seleção" vai à análise aberta; sem o
  Brasil como unidade de análise; a faixa fixa no alto das abas de análise com os números do Brasil (502.495 médicos, 212,6
  milhões de habitantes, 2,36 por 1.000 e a variação da densidade desde jun/2021, cerca de +19,2%), iguais aos que o motor
  devolveu; com os estados, 27 pontos; com os municípios, 5.570; a linha tracejada "Brasil 2,36" no gráfico;
- a trilha, sempre à vista e igual em todas as abas: "Brasil" no todo; "Brasil › Pará" ao tocar no Pará (144 municípios, 10.307
  médicos, 1,19 por 1.000, com o Brasil como referência: "Pará 1,19 · Brasil 2,36", e a linha do estado no gráfico);
  "Brasil › Pará › MARABA (PA)" ao tocar em Marabá, com o cartão (472 médicos, 1,64, e as barras do município, do Pará e do
  Brasil); tocar em "Brasil" volta ao todo sem o Desfazer, e um Desfazer, depois, volta a Marabá;
- a Série temporal de Marabá com as linhas de referência do Pará e do Brasil, tracejadas;
- o mapa vendo por estado: 27 bolhas, nos pontos de desenho do servidor;
- a Análise Espacial com os estados como unidade: só a mensagem "A Análise Espacial mede distâncias entre municípios." e o
  botão "Ver os municípios destes estados", que põe os municípios no lugar dos estados e abre a Escolha dos territórios;
- a conversa que navega: "Mostre o Pará" leva a trilha a "Brasil › Pará", com os números do Pará na faixa;
- a proteção (item 4.6): com o cálculo da seleção em uso retido, a aba diz "Esta análise ainda é do Pará: o cálculo da seleção
  em uso ainda não chegou.", com "Atualizar", e o desenho fica esmaecido; com a falha do cálculo, "… não deu certo.", e
  "Atualizar" pede de novo, até o resultado ser o da seleção em uso;
- pergunta não é comando (item 4, parte B): na Análise Espacial do Pará, com a referência "municípios de todo o país com
  densidade a partir de 3", "Quantos médicos tem em Marabá?" recebe 472 médicos, 1,64 por 1.000 habitantes e a distância até a
  referência mais próxima (cerca de 140 km), do motor; a tela continua no Pará, com Marabá em destaque. "Abrir MARABA (PA)" leva
  a trilha a "Brasil › Pará › MARABA (PA)", com a mesma referência em todas as abas, e só então a conversa diz "Abri MARABA (PA).",
  com o selo "conferido: está na tela". No Amapá, a Análise Espacial acompanha a seleção com a mesma referência, e a mesma
  pergunta traz os números do motor e "Ir para MARABA (PA)";
- os grupos em tela estreita (item 7): a 360 px, nos modos claro e escuro, vendo por estado, a lista na ordem do motor, do DF
  (4,41) ao MA (1,13), com a linha "Brasil 2,36", sem textos sobrepostos; nas bolhas, os nomes só dos destaques (os 3 maiores e
  os 3 menores), sem rótulos sobrepostos, e a sigla do Pará junto da bolha;
- Agrupar territórios (item 5; desde o comando V22, "Agrupar territórios selecionados", no painel direito da Seleção, só com
  os selecionados): o Juntar não aparece nas Ferramentas das análises; na Seleção do Pará, sem os modos de antes, a escolha
  livre: buscar "Parau", marcar PARAUAPEBAS (PA) e MARABA (PA), o nome "Carajás" e "Criar conjunto": a lista mostra "Pará · 142
  de 144 municípios" e "Carajás · conjunto · 2 municípios · 894 médicos · 1,52 por mil", com a ressalva da soma; no gráfico,
  Carajás fica no lugar das duas; a trilha continua "Brasil › Pará", e a busca da tabela dos Detalhes acha o grupo. O ✎ renomeia
  e muda os membros, só entre os selecionados (a MACAPA (AP), fora da seleção, não aparece na busca); o × desfaz o grupo, e os
  membros que saíram da seleção voltam (o Pará inteiro). Pela conversa, "agregue Marabá e Parauapebas como Carajás" cria o
  mesmo grupo, com a confirmação conferida (o selo "conferido: está na tela").
Nada é calculado na tela: os números vêm do motor. Servidor serve_ui_offline.py; nunca chama o provedor de IA. Tira capturas em
.local/ui-validation (navegacao-*.png).
"""
import json
import os
import re
import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_responsivo import SOBREPOSTOS
from ui_support import URL, offline, options_of, responder_uma_vez, send

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
PA, MARABA = "15", "code:150420"
PARAUAPEBAS, MACAPA = "code:150553", "code:160030"
ESTADOS = '[data-testid="analise-bolha"][data-tipo="estado"][data-visivel="true"]'
MUNICIPIOS = '[data-testid="analise-bolha"][data-tipo="municipio"][data-visivel="true"]'
TEXTOS_DA_AREA = """() => { const area = document.querySelector('[data-testid=area-de-analise]'); if (!area) return '';
  const partes = [area.innerText || ''];
  for (const e of area.querySelectorAll('[aria-label], [title]')) partes.push(e.getAttribute('aria-label') || '', e.getAttribute('title') || '');
  return partes.join('\\n'); }"""


def br(valor, casas=2):
    """O número como a conversa o escreve (resumo_painel.number): casas fixas, arredondamento meio para cima, milhar com ponto."""
    arredondado = Decimal(str(valor)).quantize(Decimal(1).scaleb(-casas), rounding=ROUND_HALF_UP)
    return format(arredondado, ",f").replace(",", "_").replace(".", ",").replace("_", ".")


def sem_acento(texto):
    """O texto sem acentos e em minúsculas, como a busca da tabela compara os nomes."""
    return unicodedata.normalize("NFD", texto).encode("ascii", "ignore").decode().lower()


def js(valor):
    """O número como o navegador o escreve num atributo (String(n)): os inteiros sem o ".0"."""
    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))
    return str(valor)


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "este roteiro usa a base Brasil versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        offline(context)
        page = context.new_page()
        falhas, chamadas_llm, pedidos, lugares = [], [], [], []
        page.on("pageerror", lambda error: falhas.append(str(error)))
        page.on("request", lambda request: chamadas_llm.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: pedidos.append(request)
                if request.url.endswith("/api/painel") and request.method == "POST" else None)
        page.on("request", lambda request: lugares.append(request)
                if request.url.endswith("/api/painel/lugar") and request.method == "POST" else None)
        page.goto(URL)
        page.get_by_role("button", name="Li e concordo", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        trilha = area.get_by_test_id("analise-trilha")
        partes = trilha.get_by_test_id("analise-trilha-parte")
        atual = trilha.locator('[aria-current="location"]')
        faixa = area.get_by_test_id("analise-faixa")
        desfazer = area.get_by_test_id("analise-controles-globais").get_by_test_id("analise-desfazer")
        aviso = area.get_by_test_id("analise-aviso")

        def shot(nome):
            page.wait_for_timeout(700)  # transições do gráfico
            page.screenshot(path=str(OUTPUT / ("navegacao-" + nome + "-real.png")), full_page=True)

        def aperta(locator):
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Enter")

        def marca(locator):
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Space")

        def ok(acao, timeout=180000, condicao=None):
            """A resposta de /api/painel do primeiro pedido feito depois do início da ação (e que atende `condicao`) e as opções."""
            page.wait_for_timeout(200)
            expect(area.get_by_test_id("analise-atualizando")).to_have_count(0, timeout=timeout)
            antes = len(pedidos)
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST"
                                      and any(r.request is pedido for pedido in pedidos[antes:])
                                      and (condicao is None or condicao(options_of(r.request))), timeout=timeout) as evento:
                acao()
            resposta = evento.value
            assert resposta.status == 200, resposta.text()[:2000]
            return resposta.json(), options_of(resposta.request)

        def numeros_do_lugar(acao, condicao, timeout=180000):
            """A resposta de /api/painel/lugar (os números da faixa) do primeiro pedido que atende `condicao`, feito depois da ação."""
            antes = len(lugares)
            with page.expect_response(lambda r: r.url.endswith("/api/painel/lugar") and r.request.method == "POST"
                                      and any(r.request is pedido for pedido in lugares[antes:])
                                      and condicao(options_of(r.request)), timeout=timeout) as evento:
                acao()
            resposta = evento.value
            assert resposta.status == 200, resposta.text()[:2000]
            return resposta.json(), options_of(resposta.request)

        def numero(chave):
            return faixa.locator('[data-testid="analise-faixa-numero"][data-chave="' + chave + '"]')

        def confere_numeros(nivel):
            """Os números da faixa são os do motor, sem conta na tela."""
            for chave, campo in (("profissionais", "quantidade"), ("populacao", "populacao"), ("densidade", "densidade")):
                expect(numero(chave)).to_have_attribute("data-valor", js(nivel[campo]), timeout=60000)

        def fecha():
            if area.get_by_test_id("analise-painel").count():
                aperta(area.get_by_test_id("analise-painel-fechar"))
                expect(area.get_by_test_id("analise-painel")).to_have_count(0)

        def trilha_igual_nas_abas(esperado):
            """A trilha aparece uma vez só e com as mesmas partes na Seleção e em todas as abas de análise (a Análise Espacial
            abre a Escolha dos territórios sozinha: ela fecha antes da aba seguinte)."""
            for aba in ("analise-aba-territorios", "analise-familia-distribuicao", "analise-familia-espacial",
                        "analise-familia-tendencia"):
                aperta(area.get_by_test_id(aba))
                expect(area.get_by_test_id("analise-trilha")).to_have_count(1)
                expect(partes).to_have_text(esperado)
                fecha()
            aperta(area.get_by_test_id("analise-familia-distribuicao"))
            expect(area).to_have_attribute("data-aba", "distribuicao")

        def sem_bastidor(onde):
            achados = re.findall(r"[^\n]{0,50}\bmotor\b[^\n]{0,50}", area.evaluate(TEXTOS_DA_AREA), flags=re.IGNORECASE)
            assert not achados, (onde, achados[:5])

        chat = page.get_by_test_id("painel-chat")
        if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. A base do Brasil, sem nada escolhido. Desde o comando V22 (decisão 3; muda de propósito este trecho, que conferia o Ver
        # por de 06/11/2026), sem o Ver por: "Só os estados" na linha do Brasil põe os estados como unidade. A trilha começa no
        # Brasil, ainda sem lugar atual.
        area.get_by_test_id("analise-fonte-brasil").click()
        expect(area.get_by_test_id("analise-aba-territorios")).to_have_attribute("aria-selected", "true", timeout=180000)
        expect(territorios.get_by_test_id("analise-nivel")).to_have_count(0)
        expect(territorios).not_to_contain_text("Ver por")
        expect(territorios).not_to_contain_text("Cada ponto da análise é")
        so_estados = territorios.get_by_test_id("analise-raiz-so-estados")
        expect(so_estados).to_have_text("Só os estados")
        expect(partes).to_have_text(["Brasil"])
        expect(atual).to_have_count(0)

        # 2. O todo: "Só os estados" põe todos os estados como unidade; a faixa traz os números do Brasil, prontos no motor (a fonte
        # nacional), na competência da análise, com a variação da densidade desde o primeiro dos últimos 4 junhos.
        estados_e_opcoes = []
        corpo, opcoes_lugar = numeros_do_lugar(
            lambda: estados_e_opcoes.append(ok(lambda: aperta(so_estados))),
            lambda o: "grupo" not in o)
        estados, sent = estados_e_opcoes[0]
        lugar_todo = corpo["todo"]
        assert sent.get("nivel") == "estados" and "estados" not in sent, sent
        assert sent["competencia"] == "202406", sent
        assert opcoes_lugar == {"competencia": sent["competencia"], "categoria": sent["categoria"], "desde": "202106"}, opcoes_lugar
        assert (lugar_todo["quantidade"], lugar_todo["populacao"]) == (502495, 212583750), lugar_todo
        assert round(lugar_todo["densidade"], 2) == 2.36, lugar_todo["densidade"]
        variacao = lugar_todo["variacao_percentual"]["densidade"]
        assert 19.15 <= variacao < 19.25, variacao
        itens_estado = [item for item in estados["itens"] if item["tipo"] == "estado"]
        assert len(itens_estado) == 27 == len(estados["itens"]), len(estados["itens"])
        aperta(territorios.get_by_test_id("analise-confirmar-selecao"))  # decisão 4: vai à análise aberta
        expect(area).to_have_attribute("data-aba", "distribuicao")
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=60000)
        expect(partes).to_have_text(["Brasil"])
        expect(atual).to_have_text("Brasil")
        expect(faixa).to_have_attribute("data-lugar", "todo")
        confere_numeros(lugar_todo)
        expect(numero("profissionais")).to_contain_text("502.495")
        expect(numero("populacao")).to_contain_text("212,6 milhões")
        expect(numero("populacao")).to_contain_text("212.583.750 habitantes")
        expect(numero("densidade")).to_contain_text("2,36")
        expect(numero("variacao")).to_have_attribute("data-desde", "202106")
        expect(numero("variacao")).to_have_attribute("data-valor", js(variacao))
        expect(numero("variacao")).to_contain_text("Desde jun/2021")
        expect(numero("variacao")).to_contain_text(re.compile(r"\+19,\d+%"))
        expect(faixa.locator('[data-testid^="analise-ver-por"]')).to_have_count(0)
        # A linha do todo no gráfico: tracejada, com o nome e o valor do motor.
        linha_brasil = area.get_by_test_id("analise-contexto-brasil")
        expect(linha_brasil).to_have_attribute("data-rotulo", "Brasil 2,36")
        assert linha_brasil.locator("line").get_attribute("stroke-dasharray"), "a linha do todo é tracejada"
        expect(area).not_to_contain_text("O Brasil, como unidade")
        sem_bastidor("o todo")
        shot("01-todo")

        # 3. O mapa vendo por estado: 27 bolhas, nos pontos de desenho que o servidor calcula; de volta ao gráfico.
        with page.expect_response(lambda r: r.url.endswith("/api/painel/mapa") and r.request.method == "POST", timeout=180000) as evento:
            aperta(area.get_by_test_id("analise-desenho-mapa"))
        assert evento.value.status == 200, evento.value.text()[:2000]
        assert options_of(evento.value.request).get("grupos") is True, options_of(evento.value.request)
        assert len(evento.value.json()["grupos"]) == 27
        mapa = area.get_by_test_id("mapa-analise")
        expect(mapa).to_have_attribute("data-pontos", "27", timeout=60000)
        shot("02-mapa-estados")
        aperta(area.get_by_test_id("analise-desenho-grafico"))
        expect(area).to_have_attribute("data-desenho", "grafico")

        # 4. Os 5.570 municípios do Brasil: na Seleção, desligar "Só os estados" e marcar a caixa do Brasil (desde o comando V22, ela
        # marca os municípios); a faixa continua a do Brasil (os mesmos números, sem novo pedido). "Só os estados" de novo: os 27, da
        # memória da tela.
        lugares_antes = len(lugares)
        aperta(area.get_by_test_id("analise-aba-territorios"))
        aperta(so_estados)
        expect(so_estados).to_have_attribute("aria-pressed", "false")
        brasil, sent = ok(lambda: marca(territorios.get_by_test_id("analise-raiz-caixa")))
        assert sent["base"] == {"municipios": {"todos": True, "estados": [], "ids": []}} and sent["nivel"] == "municipios", sent
        assert len([item for item in brasil["itens"] if item["tipo"] == "municipio"]) == 5570, len(brasil["itens"])
        expect(partes).to_have_text(["Brasil"])
        aperta(territorios.get_by_test_id("analise-confirmar-selecao"))
        expect(faixa).to_have_attribute("data-lugar", "todo")
        confere_numeros(lugar_todo)
        aperta(area.get_by_test_id("analise-aba-territorios"))
        aperta(so_estados)
        expect(so_estados).to_have_attribute("aria-pressed", "true")
        aperta(territorios.get_by_test_id("analise-confirmar-selecao"))
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=60000)
        page.wait_for_timeout(500)
        assert len(lugares) == lugares_antes, "os números do Brasil não mudam com o nível dos pontos"

        # 5. Tocar no Pará: os 144 municípios dele; a trilha "Brasil › Pará"; a faixa com os números do Pará (a contagem estadual
        # de médicos únicos, pronta na fonte) e o Brasil como referência; no gráfico, a linha do Pará junto da do Brasil. Voltar é
        # pela trilha.
        bolha_pa = area.locator('[data-testid="analise-bolha"][data-id="uf:' + PA + '"]')
        para_e_opcoes = []
        corpo, opcoes_lugar = numeros_do_lugar(
            lambda: para_e_opcoes.append(ok(lambda: aperta(bolha_pa))), lambda o: o.get("grupo") == PA)
        para, sent = para_e_opcoes[0]
        assert sent["base"] == {"municipios": {"todos": False, "estados": [PA], "ids": []}}, sent
        assert len(para["itens"]) == 144 and all(item["tipo"] == "municipio" for item in para["itens"]), len(para["itens"])
        lugar_pa = corpo["grupo"]
        assert (lugar_pa["quantidade"], round(lugar_pa["densidade"], 2)) == (10307, 1.19), lugar_pa
        assert corpo["todo"]["densidade"] == lugar_todo["densidade"], "o Brasil é o mesmo"
        expect(partes).to_have_text(["Brasil", "Pará"])
        expect(atual).to_have_text("Pará")
        expect(aviso).to_contain_text("Para voltar, toque em Brasil na trilha, no alto.")
        expect(faixa).to_have_attribute("data-lugar", "grupo")
        expect(faixa).to_have_attribute("data-grupo", PA)
        confere_numeros(lugar_pa)
        expect(numero("profissionais")).to_contain_text("10.307")
        expect(faixa.get_by_test_id("analise-faixa-referencia")).to_contain_text("Pará 1,19 · Brasil 2,36")
        expect(faixa.get_by_test_id("analise-ver-por")).to_have_count(0)  # uma opção só: o município
        expect(area.locator(MUNICIPIOS)).to_have_count(len([item for item in para["itens"] if item["densidade"] is not None]),
                                                       timeout=60000)
        linha_pa = area.get_by_test_id("analise-linha-grupo")
        expect(linha_pa).to_have_attribute("data-rotulo", "Pará 1,19")
        expect(linha_pa).to_have_attribute("data-valor", js(lugar_pa["densidade"]))
        expect(linha_brasil).to_have_attribute("data-rotulo", "Brasil 2,36")
        sem_bastidor("o Pará")
        shot("03-para")

        # 6. Tocar em Marabá: o lugar dela, "Brasil › Pará › MARABA (PA)", com o cartão no alto (os valores do motor e as barras
        # da densidade do município, do Pará e do Brasil); com um território só, o cartão fica no lugar do gráfico.
        bolha_maraba = area.locator('[data-testid="analise-bolha"][data-id="' + MARABA + '"]')
        expect(bolha_maraba).to_have_count(1)
        maraba, sent = ok(lambda: aperta(bolha_maraba))
        assert sent["base"] == {"municipios": {"todos": False, "estados": [], "ids": [MARABA]}}, sent
        [item_maraba] = maraba["itens"]
        assert item_maraba["quantidade"] == 472 and round(item_maraba["densidade"], 2) == 1.64, item_maraba
        expect(partes).to_have_text(["Brasil", "Pará", "MARABA (PA)"])
        expect(atual).to_have_text("MARABA (PA)")
        expect(faixa).to_have_attribute("data-lugar", "unidade")
        cartao = faixa.get_by_test_id("analise-cartao")
        expect(cartao).to_have_attribute("data-id", MARABA, timeout=60000)
        expect(cartao.get_by_test_id("analise-cartao-quantidade")).to_have_attribute("data-valor", "472")
        expect(cartao.get_by_test_id("analise-cartao-quantidade")).to_contain_text("472")
        barras = cartao.get_by_test_id("analise-cartao-barra")
        expect(barras).to_have_count(3, timeout=60000)
        for chave, valor in (("unidade", item_maraba["densidade"]), ("grupo", lugar_pa["densidade"]), ("todo", lugar_todo["densidade"])):
            expect(cartao.locator('[data-testid="analise-cartao-barra"][data-chave="' + chave + '"]')).to_have_attribute("data-valor", js(valor))
        expect(cartao).to_contain_text("1,64")
        expect(area.get_by_test_id("analise-cartao-no-lugar")).to_be_visible()
        expect(desfazer).to_have_attribute("title", "Desfazer: abrir MARABA (PA)")
        sem_bastidor("Marabá")
        shot("04-maraba")

        # 7. A trilha é igual em todas as abas; a Série temporal de Marabá traz as linhas de referência do Pará e do Brasil,
        # tracejadas (os valores de cada competência, do motor).
        trilha_igual_nas_abas(["Brasil", "Pará", "MARABA (PA)"])
        aperta(area.get_by_test_id("analise-familia-tendencia"))
        expect(area).to_have_attribute("data-aba", "tendencia")
        ok(lambda: aperta(area.get_by_test_id("analise-visao-series")), condicao=lambda o: bool(o.get("serie")))
        referencias = area.get_by_test_id("analise-serie-referencia")
        expect(referencias).to_have_count(2, timeout=60000)
        assert sorted(referencias.evaluate_all("els => els.map(e => e.dataset.id)")) == ["br", "uf:" + PA]
        expect(area.get_by_test_id("analise-serie")).to_have_count(1)
        nomes = area.locator('[data-testid="analise-serie-referencia"] text').evaluate_all("els => els.map(e => e.textContent)")
        assert sorted(nomes) == ["Brasil", "Pará"], nomes
        tracos = area.locator('[data-testid="analise-serie-referencia"] path').evaluate_all(
            "els => els.map(e => e.getAttribute('stroke-dasharray'))")
        assert tracos and all(tracos), ("as linhas de referência são tracejadas", tracos)
        shot("05-maraba-serie")
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area).to_have_attribute("data-aba", "distribuicao")

        # 8. Tocar em "Brasil" na trilha volta ao todo, vendo por estado, sem o Desfazer; um Desfazer, em seguida, volta a Marabá.
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="todo"]'))
        expect(partes).to_have_text(["Brasil"])
        expect(atual).to_have_text("Brasil")
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=60000)
        expect(faixa).to_have_attribute("data-lugar", "todo")
        expect(desfazer).to_have_attribute("title", "Desfazer: ir para Brasil na trilha")
        aperta(desfazer)
        expect(partes).to_have_text(["Brasil", "Pará", "MARABA (PA)"])
        expect(faixa.get_by_test_id("analise-cartao")).to_have_attribute("data-id", MARABA, timeout=60000)
        # O Pará, pela trilha: os 144 municípios de novo.
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="grupo"]'))
        expect(partes).to_have_text(["Brasil", "Pará"])
        expect(faixa).to_have_attribute("data-lugar", "grupo")
        expect(area.locator(MUNICIPIOS).first).to_be_visible(timeout=60000)
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="todo"]'))
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=60000)

        # 9. A Análise Espacial com só estados como unidade: só a mensagem e o botão; sem gráfico, ajustes nem a Escolha dos
        # territórios. O botão põe os municípios desses estados no lugar deles e abre a Escolha dos territórios.
        aperta(area.get_by_test_id("analise-familia-espacial"))
        expect(area).to_have_attribute("data-aba", "espacial")
        espacial = area.get_by_test_id("analise-espacial-grupos")
        expect(espacial).to_contain_text("A Análise Espacial mede distâncias entre municípios.")
        botao = espacial.get_by_test_id("analise-espacial-ver-unidades")
        expect(botao).to_have_text("Ver os municípios destes estados")
        expect(area.get_by_test_id("analise-resultados")).to_be_hidden()
        expect(area.get_by_test_id("analise-ajustes")).to_have_count(0)
        expect(area.get_by_test_id("analise-painel")).to_have_count(0)
        expect(faixa).to_have_attribute("data-lugar", "todo")
        shot("06-espacial-estados")
        aperta(botao)
        expect(area.get_by_test_id("analise-painel")).to_have_attribute("data-painel", "referencia", timeout=30000)
        expect(faixa).to_have_attribute("data-lugar", "todo")
        expect(area.get_by_test_id("analise-espacial-grupos")).to_have_count(0)
        fecha()
        aperta(area.get_by_test_id("analise-familia-distribuicao"))

        # 10. A conversa navega: "Mostre o Pará" leva a trilha a "Brasil › Pará", com os números do Pará na faixa (os mesmos do
        # passo 5; a resposta e os números podem vir da memória da tela).
        send(page, "Mostre o Pará")
        expect(page.get_by_test_id("painel-chat").get_by_test_id("latest-reply")).to_contain_text("144 municípios do Pará",
                                                                                                    timeout=120000)
        expect(partes).to_have_text(["Brasil", "Pará"], timeout=60000)
        expect(faixa).to_have_attribute("data-grupo", PA)
        confere_numeros(lugar_pa)
        shot("07-conversa-para")

        # 11. A proteção (item 4.6): o resultado à vista é de outra seleção enquanto o cálculo da seleção em uso não chega. Com o
        # pedido retido, a aba diz de que lugar ele é, com "Atualizar", e o desenho fica esmaecido; com o cálculo, tudo volta ao
        # normal.
        desatualizada = area.get_by_test_id("analise-desatualizada")
        quadro = area.get_by_test_id("analise-quadro")
        expect(area.get_by_test_id("analise-atualizando")).to_have_count(0, timeout=180000)
        expect(desatualizada).to_have_count(0)
        outro = next(item for item in para["itens"] if item["id"] != MARABA and item["densidade"] is not None)
        retidas = []
        page.route("**/api/painel", lambda route: retidas.append(route))
        aperta(area.locator('[data-testid="analise-bolha"][data-id="' + outro["id"] + '"]'))
        expect(partes).to_have_text(["Brasil", "Pará", outro["rotulo"]])
        expect(desatualizada).to_have_text(re.compile(r"^Esta análise ainda é do Pará: o cálculo da seleção em uso ainda não "
                                                      r"chegou\.\s*Atualizar$"), timeout=30000)
        expect(desatualizada).to_have_attribute("role", "status")
        expect(desatualizada.get_by_test_id("analise-atualizar")).to_have_text("Atualizar")
        expect(quadro).to_have_attribute("data-desatualizada", "true")
        assert retidas, "o pedido da seleção em uso saiu e ficou retido"
        shot("08-protecao-pendente")
        for rota in retidas:
            try:
                rota.continue_()
            except Exception:  # noqa: BLE001 - o pedido que a página já cancelou não tem o que soltar
                pass
        page.unroute("**/api/painel")
        expect(desatualizada).to_have_count(0, timeout=120000)
        expect(quadro).not_to_have_attribute("data-desatualizada", "true")
        expect(faixa.get_by_test_id("analise-cartao")).to_have_attribute("data-id", outro["id"], timeout=60000)
        expect(area.get_by_test_id("analise-cartao-no-lugar")).to_be_visible()

        # Com a falha do cálculo: "… não deu certo.", e "Atualizar" pede de novo; o resultado passa a ser o da seleção em uso.
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="todo"]'))
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=180000)
        expect(area.get_by_test_id("analise-atualizando")).to_have_count(0, timeout=180000)
        expect(desatualizada).to_have_count(0)
        falha = "Falha simulada do serviço de análise neste teste."
        falhou = responder_uma_vez(page, "**/api/painel", status=500, body=json.dumps({"detail": falha}),
                                   content_type="application/json")
        aperta(area.locator('[data-testid="analise-bolha"][data-id="uf:16"]'))
        expect(partes).to_have_text(["Brasil", "Amapá"])
        expect(desatualizada).to_have_text(re.compile(r"^Esta análise ainda é do Brasil: o cálculo da seleção em uso não deu "
                                                      r"certo\.\s*Atualizar$"), timeout=60000)
        expect(desatualizada).to_have_attribute("role", "alert")
        expect(quadro).to_have_attribute("data-desatualizada", "true")
        assert falhou, "o pedido da seleção em uso recebeu a falha simulada"
        shot("09-protecao-falha")
        amapa, sent = ok(lambda: aperta(desatualizada.get_by_test_id("analise-atualizar")))
        assert sent["base"] == {"municipios": {"todos": False, "estados": ["16"], "ids": []}}, sent
        assert amapa["itens"] and all(item["tipo"] == "municipio" for item in amapa["itens"]), len(amapa["itens"])
        expect(desatualizada).to_have_count(0, timeout=60000)
        expect(quadro).not_to_have_attribute("data-desatualizada", "true")
        expect(faixa).to_have_attribute("data-grupo", "16", timeout=60000)

        # 12. Pergunta não é comando (item 4 do comando, parte B). Na Análise Espacial do Pará, com a referência "municípios de
        # todo o país com densidade a partir de 3" escolhida na janela, "Quantos médicos tem em Marabá?" recebe os números do
        # motor e o destaque de Marabá, sem mudar a tela; "Abrir MARABA (PA)" leva a trilha a Marabá, com a mesma referência.
        page.unroute("**/api/painel")
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="todo"]'))
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=180000)
        aperta(area.locator('[data-testid="analise-bolha"][data-id="uf:' + PA + '"]'))
        expect(partes).to_have_text(["Brasil", "Pará"])
        expect(area.locator(MUNICIPIOS).first).to_be_visible(timeout=180000)
        aperta(area.get_by_test_id("analise-familia-espacial"))
        janela = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
        expect(janela).to_be_visible(timeout=30000)
        aperta(janela.get_by_test_id("territorios-aba-referencia"))
        aperta(janela.get_by_test_id("territorios-referencia-mais-densidade"))
        filtro = janela.get_by_test_id("territorios-referencia-filtro").first
        filtro.get_by_test_id("territorios-referencia-filtro-operador").select_option(">=")
        filtro.get_by_test_id("territorios-referencia-filtro-valor").fill("3")
        expect(janela.get_by_test_id("territorios-calcular")).to_be_enabled(timeout=60000)
        espacial_pa, sent = ok(lambda: aperta(janela.get_by_test_id("territorios-calcular")),
                               condicao=lambda o: bool(o.get("consulta")))
        referencia = sent["consulta"]["referencia"]
        assert sent["base"] == {"municipios": {"todos": False, "estados": [PA], "ids": []}}, sent
        assert sent["consulta"]["base"]["partir_de"]["tipo"] == "selecao_previa", sent["consulta"]
        assert referencia["partir_de"]["tipo"] == "pais" and referencia["filtros"] == [
            {"indicador": "densidade", "operador": ">=", "valor": 3}], referencia
        assert len(espacial_pa["itens"]) == 144, len(espacial_pa["itens"])
        fecha()
        [maraba_pa] = [item for item in espacial_pa["itens"] if item["id"] == MARABA]
        km = maraba_pa["distancia_km"]
        assert abs(km - 140) < 1.5, ("o aceite do comando: cerca de 140 km", km)
        chat = page.get_by_test_id("painel-chat")
        resposta_chat = chat.get_by_test_id("latest-reply")
        pedidos_antes = len(pedidos)
        send(page, "Quantos médicos tem em Marabá?")
        expect(resposta_chat).to_contain_text("MARABA (PA): 472 médicos em junho de 2024 (1,64 por 1.000 habitantes), a " + br(km) +
                                              " km em linha reta da referência mais próxima", timeout=120000)
        expect(resposta_chat).to_contain_text("Destaquei no gráfico.")
        expect(partes).to_have_text(["Brasil", "Pará"])
        expect(area).to_have_attribute("data-aba", "espacial")
        expect(area.locator('[data-testid="analise-bolha"][data-id="' + MARABA + '"]')).to_have_attribute("data-realce", "true")
        assert len(pedidos) == pedidos_antes, "a pergunta não muda a análise nem pede nada ao motor da área"
        alternativas = chat.get_by_role("group", name="Alternativas de esclarecimento")
        expect(alternativas.get_by_role("button")).to_have_text(["Abrir MARABA (PA)", "Adicionar à seleção"])
        shot("10-pergunta-maraba")
        aberto, sent = ok(lambda: alternativas.get_by_role("button", name="Abrir MARABA (PA)", exact=True).click(),
                          condicao=lambda o: bool(o.get("consulta")))
        assert sent["base"] == {"municipios": {"todos": False, "estados": [], "ids": [MARABA]}}, sent
        assert sent["consulta"]["referencia"] == referencia, "a referência escolhida continua"
        expect(partes).to_have_text(["Brasil", "Pará", "MARABA (PA)"])
        expect(resposta_chat).to_contain_text("Abri MARABA (PA).", timeout=60000)
        expect(resposta_chat.get_by_test_id("chat-conferido")).to_have_text("conferido: está na tela")
        expect(chat.locator('[data-papel="agente"]').last).to_have_attribute("data-execucao", "concluido")
        [maraba_so] = aberto["itens"]
        expect(faixa.get_by_test_id("analise-cartao-distancia")).to_have_attribute("data-valor", js(maraba_so["distancia_km"]),
                                                                                   timeout=60000)
        trilha_igual_nas_abas(["Brasil", "Pará", "MARABA (PA)"])
        shot("11-abri-maraba")

        # A seleção no Amapá: a Análise Espacial acompanha, com a mesma referência; a mesma pergunta, fora da análise em uso,
        # traz os números do motor (calculados à parte) e "Ir para MARABA (PA)".
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="todo"]'))
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=180000)
        aperta(area.locator('[data-testid="analise-bolha"][data-id="uf:16"]'))
        expect(partes).to_have_text(["Brasil", "Amapá"])
        amapa, sent = ok(lambda: aperta(area.get_by_test_id("analise-familia-espacial")), condicao=lambda o: bool(o.get("consulta")))
        assert sent["base"] == {"municipios": {"todos": False, "estados": ["16"], "ids": []}}, sent
        assert sent["consulta"]["referencia"] == referencia, "a Análise Espacial acompanha a seleção, com a mesma referência"
        assert amapa["itens"] and all(item["id"].startswith("code:16") for item in amapa["itens"]), amapa["itens"][:2]
        fecha()
        pedidos_antes = len(pedidos)
        send(page, "Quantos médicos tem em Marabá?")
        expect(resposta_chat).to_contain_text("MARABA (PA): 472 médicos em junho de 2024 (1,64 por 1.000 habitantes)",
                                              timeout=120000)
        expect(resposta_chat).to_contain_text("Não está na análise em uso.")
        expect(alternativas.get_by_role("button")).to_have_text(["Ir para MARABA (PA)", "Adicionar à seleção"])
        expect(partes).to_have_text(["Brasil", "Amapá"])
        assert len(pedidos) == pedidos_antes, "a pergunta não muda a análise"
        shot("12-maraba-fora-do-amapa")

        # 13. Os grupos em tela estreita (item 7 do comando): a 360 px, nos modos claro e escuro, vendo por estado, a lista na ordem
        # do motor, do DF (4,41) ao MA (1,13), com a linha "Brasil 2,36"; nas bolhas, os nomes só dos 3 maiores e dos 3 menores,
        # sem rótulos sobrepostos, e a sigla do Pará junto da bolha (ou ligada a ela pela linha guia).
        for esquema in ("light", "dark"):
            estreito = browser.new_context(viewport={"width": 360, "height": 800}, color_scheme=esquema, has_touch=True,
                                           is_mobile=True)
            offline(estreito)
            celular = estreito.new_page()
            celular.on("pageerror", lambda error: falhas.append(str(error)))
            celular.goto(URL)
            celular.get_by_role("button", name="Li e concordo", exact=True).click()
            area_c = celular.get_by_test_id("area-de-analise")
            chat_c = celular.get_by_test_id("painel-chat")
            if chat_c.count() and chat_c.get_by_test_id("painel-chat-minimizar").count() and \
                    chat_c.get_attribute("data-minimizada") != "true":
                chat_c.get_by_test_id("painel-chat-minimizar").click()
            area_c.get_by_test_id("analise-fonte-brasil").click()
            territorios_c = area_c.get_by_test_id("analise-territorios")
            expect(territorios_c).to_be_visible(timeout=180000)
            with celular.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST",
                                         timeout=180000) as evento:
                botao = territorios_c.get_by_test_id("analise-raiz-so-estados")
                botao.scroll_into_view_if_needed()
                botao.focus()
                botao.press("Enter")
            assert evento.value.status == 200, evento.value.text()[:1500]
            ordem_motor = evento.value.json()["ordem_do_indicador"]["itens"]
            ordem_c = [entrada["id"] for entrada in ordem_motor]
            posicoes = {entrada["id"]: entrada["posicao"] for entrada in ordem_motor}
            territorios_c.get_by_test_id("analise-confirmar-selecao").click()
            lista = area_c.get_by_test_id("analise-lista-grupos")
            expect(lista).to_be_visible(timeout=60000)
            expect(area_c.get_by_test_id("analise-grupos-lista")).to_have_attribute("aria-pressed", "true")
            linhas = lista.get_by_test_id("analise-lista-grupo")
            expect(linhas).to_have_count(27)
            assert linhas.evaluate_all("els => els.map(e => e.dataset.id)") == ordem_c, "a ordem é a do motor"
            expect(linhas.first).to_have_attribute("data-id", "uf:53")
            expect(linhas.first).to_contain_text("DF")
            expect(linhas.first).to_contain_text("4,41")
            expect(linhas.last).to_have_attribute("data-id", "uf:21")
            expect(linhas.last).to_contain_text("MA")
            expect(linhas.last).to_contain_text("1,13")
            expect(lista.get_by_test_id("analise-lista-todo")).to_have_text("Brasil 2,36")
            assert not lista.evaluate(SOBREPOSTOS), (esquema, "textos sobrepostos na lista", lista.evaluate(SOBREPOSTOS)[:5])
            assert celular.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), (esquema, "rolagem horizontal")
            assert all(caixa["height"] >= 39.5 for caixa in linhas.evaluate_all(
                "els => els.map(e => e.getBoundingClientRect().toJSON())")), (esquema, "alvo de toque menor que 40 px")
            celular.screenshot(path=str(OUTPUT / ("navegacao-13-lista-" + esquema + "-real.png")), full_page=True)
            # As bolhas, por escolha: os nomes só dos destaques, sem sobreposição; o Pará junto da bolha.
            area_c.get_by_test_id("analise-grupos-bolhas").click()
            expect(area_c.locator(ESTADOS)).to_have_count(27, timeout=60000)
            celular.wait_for_timeout(800)  # transições do gráfico
            avaliaveis = [i for i in ordem_c if posicoes[i] is not None]
            corte = posicoes[avaliaveis[-3]]
            destaques = {i for i in avaliaveis if posicoes[i] <= 3 or posicoes[i] >= corte}
            rotulados = area_c.locator("g.analise-rotulos .analise-rotulo-grupo")
            assert set(rotulados.evaluate_all("els => els.map(e => e.dataset.id)")) == destaques, (esquema, "só os destaques")
            assert not area_c.locator("g.analise-rotulos").evaluate(SOBREPOSTOS), (esquema, "rótulos sobrepostos")
            assert "uf:" + PA in destaques, ("o Pará entre os 3 menores", sorted(destaques))
            perto = celular.evaluate("""(id) => {
              const b = document.querySelector('[data-testid=analise-bolha][data-id="' + id + '"]').getBoundingClientRect();
              const g = document.querySelector('g.analise-rotulos .analise-rotulo-grupo[data-id="' + id + '"]');
              const t = g.querySelector('text').getBoundingClientRect();
              const dx = Math.max(0, t.left - b.right, b.left - t.right), dy = Math.max(0, t.top - b.bottom, b.top - t.bottom);
              return {distancia: Math.hypot(dx, dy), guia: !!g.querySelector('[data-testid=analise-rotulo-guia]')}; }""",
                                    "uf:" + PA)
            assert perto["distancia"] <= 12 or perto["guia"], (esquema, "a sigla do Pará longe da bolha, sem linha guia", perto)
            celular.screenshot(path=str(OUTPUT / ("navegacao-14-bolhas-" + esquema + "-real.png")), full_page=True)
            estreito.close()

        # 14. Agregar territórios (item 5 do comando). O Juntar saiu das Ferramentas das análises; na Seleção do Pará, o painel
        # Agregar territórios junta PARAUAPEBAS (PA) e MARABA (PA) como "Carajás", no lugar dos membros, com os números do motor.
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area).to_have_attribute("data-aba", "distribuicao")
        aperta(trilha.locator('[data-testid="analise-trilha-parte"][data-chave="todo"]'))
        expect(area.locator(ESTADOS)).to_have_count(27, timeout=180000)
        # O Pará inteiro já foi calculado (passo 5): a tela pode reaproveitar a resposta guardada, sem novo pedido.
        aperta(area.locator('[data-testid="analise-bolha"][data-id="uf:' + PA + '"]'))
        expect(partes).to_have_text(["Brasil", "Pará"])
        expect(area.locator(MUNICIPIOS)).to_have_count(len([item for item in para["itens"] if item["densidade"] is not None]),
                                                       timeout=180000)
        expect(area.get_by_test_id("analise-funcao-comparar")).to_be_visible()
        expect(area.get_by_test_id("analise-funcao-juntar")).to_have_count(0)
        ids_pa = {item["id"] for item in para["itens"]}
        assert len(ids_pa) == 144 and {PARAUAPEBAS, MARABA} <= ids_pa, len(ids_pa)
        aperta(area.get_by_test_id("analise-aba-territorios"))
        expect(area).to_have_attribute("data-aba", "territorios")
        # Desde o comando V22 (seções 3 e 5; muda de propósito esta conferência, que via os modos da coluna da esquerda): sem os
        # modos; "Agrupar territórios selecionados", no painel direito, por escolha livre, só com os selecionados (o Pará inteiro).
        expect(territorios.get_by_test_id("analise-selecao-modos")).to_have_count(0)
        aperta(territorios.get_by_test_id("analise-agrupar-selecionados"))
        expect(territorios.get_by_test_id("analise-agrupamento")).to_have_attribute("data-modo", "livre")
        agregar = territorios.get_by_test_id("analise-agregar")
        expect(territorios.get_by_test_id("analise-arvore")).to_be_visible()
        expect(agregar.get_by_test_id("analise-agregar-nome")).to_have_value("Conjunto A")
        expect(agregar.get_by_test_id("analise-agregar-substitui")).to_be_checked()
        busca_grupo = agregar.get_by_test_id("analise-agregar-busca")
        busca_grupo.fill("Parau")
        resultado = agregar.locator('[data-testid="analise-agregar-resultado"][data-id="' + PARAUAPEBAS + '"]')
        expect(resultado).to_have_text("PARAUAPEBAS (PA) · Pará")
        marca(resultado.locator("input"))
        busca_grupo.fill("Marabá")
        marca(agregar.locator('[data-testid="analise-agregar-resultado"][data-id="' + MARABA + '"] input'))
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_text(["PARAUAPEBAS (PA)", "MARABA (PA)"])
        agregar.get_by_test_id("analise-agregar-nome").fill("Carajás")
        carajas, sent = ok(lambda: aperta(agregar.get_by_test_id("analise-agregar-criar")))
        assert sent["conjuntos"] == [{"id": "c1", "rotulo": "Carajás", "membros": [PARAUAPEBAS, MARABA]}], sent["conjuntos"]
        base = sent["base"]["municipios"]
        assert not base["todos"] and base["estados"] == [] and set(base["ids"]) == ids_pa - {PARAUAPEBAS, MARABA}, base
        [grupo] = [item for item in carajas["itens"] if item["id"] == "c1"]
        assert grupo["tipo"] == "conjunto" and grupo["contagem"] == "SOMA_DOS_COMPONENTES", grupo
        assert (grupo["quantidade"], round(grupo["densidade"], 2)) == (894, 1.52), ("o aceite: 894 médicos e 1,52 por mil", grupo)
        assert len(carajas["itens"]) == 143 and not {PARAUAPEBAS, MARABA} & {item["id"] for item in carajas["itens"]}, \
            "o grupo fica no lugar das duas"
        expect(agregar).to_have_count(0)
        expect(territorios.locator('[data-testid="analise-selecionado"][data-grupo="' + PA + '"]')).to_contain_text(
            "Pará · 142 de 144 municípios")
        texto_do_grupo = territorios.get_by_test_id("analise-selecionado-conjunto-texto")
        expect(texto_do_grupo).to_have_text("Carajás · conjunto · 2 municípios · 894 médicos · 1,52 por mil", timeout=60000)
        expect(territorios.get_by_test_id("analise-selecionado-ressalva")).to_have_text(re.compile(
            r"^O total corresponde à soma dos quantitativos .* podem ser contabilizados mais de uma vez\.$"))
        expect(partes).to_have_text(["Brasil", "Pará"])
        shot("15-agregar-carajas")
        # No gráfico, Carajás no lugar das duas; a busca da tabela dos Detalhes filtra as linhas pelo nome: "Carajás" acha o grupo e
        # os municípios do Pará com o nome (CANAA DOS CARAJAS e ELDORADO DOS CARAJAS), as linhas avaliáveis da resposta do motor.
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area.locator('[data-testid="analise-bolha"][data-id="c1"]')).to_have_attribute("data-tipo", "conjunto", timeout=60000)
        for membro in (PARAUAPEBAS, MARABA):
            expect(area.locator('[data-testid="analise-bolha"][data-id="' + membro + '"]')).to_have_count(0)
        expect(area.get_by_test_id("analise-funcao-juntar")).to_have_count(0)
        aperta(area.get_by_test_id("analise-detalhes-tabela"))
        busca_tabela = area.get_by_test_id("analise-tabela-busca")
        busca_tabela.fill("Carajás")
        com_o_nome = sorted(item["id"] for item in carajas["itens"]
                            if "carajas" in sem_acento(item["rotulo"]) and item["densidade"] is not None)
        assert "c1" in com_o_nome, com_o_nome
        linhas_achadas = area.get_by_test_id("analise-tabela").get_by_test_id("analise-linha")
        expect(linhas_achadas).to_have_count(len(com_o_nome))
        assert sorted(linhas_achadas.evaluate_all("els => els.map(e => e.dataset.id)")) == com_o_nome
        expect(area.locator('[data-testid="analise-linha"][data-id="c1"]')).to_contain_text("soma das contagens dos componentes")
        busca_tabela.fill("Parauapebas")
        expect(area.get_by_test_id("analise-tabela-sem-resultado")).to_be_visible()
        busca_tabela.fill("")
        shot("16-carajas-no-grafico")
        # O ✎: o nome e os membros, só entre os selecionados (comando V22, seção 5: agrupar não traz territórios de fora; a Macapá,
        # fora da seleção, não é candidata). Um terceiro município do Pará entra e sai da seleção individual; a versão da composição
        # sobe, e o id fica.
        aperta(area.get_by_test_id("analise-aba-territorios"))
        aperta(territorios.get_by_test_id("analise-selecionado-conjunto-editar"))
        expect(agregar.get_by_test_id("analise-agregar-nome")).to_have_value("Carajás")
        expect(agregar.get_by_test_id("analise-agregar-membro")).to_have_count(2)
        agregar.get_by_test_id("analise-agregar-busca").fill("Macapa")
        expect(agregar.locator('[data-testid="analise-agregar-resultado"][data-id="' + MACAPA + '"]')).to_have_count(0)
        expect(agregar.get_by_test_id("analise-agregar-resultado")).to_have_count(0)
        agregar.get_by_test_id("analise-agregar-busca").fill("")
        agregar.get_by_test_id("analise-agregar-grupo").select_option(PA)
        terceiro = agregar.locator('[data-testid="analise-agregar-unidade"]:not([data-id="' + PARAUAPEBAS + '"]):not([data-id="' + MARABA + '"])').first
        id_terceiro = terceiro.get_attribute("data-id")
        marca(terceiro.locator("input"))
        agregar.get_by_test_id("analise-agregar-nome").fill("Carajás e vizinho")
        expect(agregar.get_by_test_id("analise-agregar-criar")).to_have_text("Salvar conjunto")
        editado, sent = ok(lambda: aperta(agregar.get_by_test_id("analise-agregar-criar")))
        assert sent["conjuntos"] == [{"id": "c1", "rotulo": "Carajás e vizinho", "membros": [PARAUAPEBAS, MARABA, id_terceiro]}], sent
        assert set(sent["base"]["municipios"]["ids"]) == ids_pa - {PARAUAPEBAS, MARABA, id_terceiro}, "o terceiro sai da seleção individual"
        expect(partes).to_have_text(["Brasil", "Pará"])
        expect(texto_do_grupo).to_contain_text("Carajás e vizinho · conjunto · 3 municípios")
        # O ×: o grupo se desfaz, e os membros que saíram da seleção voltam (o Pará inteiro). A escolha volta a ser a do Pará
        # inteiro, já calculada: a tela pode reaproveitar a resposta guardada, sem novo pedido.
        aperta(territorios.get_by_role("button", name="Desfazer o conjunto Carajás e vizinho", exact=True))
        expect(territorios.get_by_test_id("analise-selecionado-conjunto")).to_have_count(0)
        expect(territorios.locator('[data-testid="analise-selecionado"][data-grupo="' + PA + '"]')).to_contain_text(
            "Pará · todos os 144")
        expect(partes).to_have_text(["Brasil", "Pará"])
        # Pela conversa, o mesmo grupo, com a confirmação conferida (item 4): a resposta só se dá por concluída com o resultado em
        # tela.
        chat = page.get_by_test_id("painel-chat")
        resposta_chat = chat.get_by_test_id("latest-reply")
        pelo_chat, sent = ok(lambda: send(page, "agregue Marabá e Parauapebas como Carajás"),
                             condicao=lambda o: bool(o.get("conjuntos")))
        assert [(c["id"], c["rotulo"], sorted(c["membros"])) for c in sent["conjuntos"]] == [
            ("c1", "Carajás", sorted([MARABA, PARAUAPEBAS]))], sent["conjuntos"]
        assert set(sent["base"]["municipios"]["ids"]) == ids_pa - {PARAUAPEBAS, MARABA}, "os membros saem da seleção"
        [grupo_chat] = [item for item in pelo_chat["itens"] if item["id"] == "c1"]
        assert (grupo_chat["quantidade"], round(grupo_chat["densidade"], 2)) == (894, 1.52), grupo_chat
        expect(resposta_chat).to_contain_text("Agrupei MARABA (PA) e PARAUAPEBAS (PA) como Carajás", timeout=60000)
        expect(resposta_chat).to_contain_text("no lugar deles: a bolha soma as contagens dos componentes")
        expect(resposta_chat.get_by_test_id("chat-conferido")).to_have_text("conferido: está na tela", timeout=60000)
        expect(chat.locator('[data-papel="agente"]').last).to_have_attribute("data-execucao", "concluido")
        expect(partes).to_have_text(["Brasil", "Pará"])
        # O pedido feito com a Seleção à vista leva à análise em uso: no gráfico, Carajás no lugar das duas; de volta à Seleção, a
        # mesma linha do grupo em "Na análise".
        expect(area).to_have_attribute("data-aba", "distribuicao")
        expect(area.locator('[data-testid="analise-bolha"][data-id="c1"]')).to_have_attribute("data-tipo", "conjunto", timeout=60000)
        for membro in (PARAUAPEBAS, MARABA):
            expect(area.locator('[data-testid="analise-bolha"][data-id="' + membro + '"]')).to_have_count(0)
        shot("17-carajas-pela-conversa")
        aperta(area.get_by_test_id("analise-aba-territorios"))
        expect(texto_do_grupo).to_have_text("Carajás · conjunto · 2 municípios · 894 médicos · 1,52 por mil", timeout=60000)

        assert not falhas, falhas
        assert not chamadas_llm, chamadas_llm
        browser.close()
    print("NAVEGACAO PASS: o todo como referência (502.495 médicos, 212,6 milhões, 2,36), Só os estados (27) e a caixa do Brasil "
          "(5.570 municípios), trilha Brasil › Pará › MARABA (PA), cartão (472, 1,64), volta pela trilha, Série com as referências, mapa dos "
          "estados (27), Análise Espacial por estado, a conversa que move a trilha (Mostre o Pará) e a proteção (Esta análise ainda é "
          "do Pará, com Atualizar), a pergunta que não é comando (Marabá: 472, 1,64, cerca de 140 km; Abrir e Ir para), os estados "
          "em tela estreita (a lista na ordem do motor, do DF ao MA, e nas bolhas só os destaques) e Agregar territórios (Carajás: "
          "Pará · 142 de 144, 894 médicos, 1,52 por mil; editar, desfazer e pela conversa).")


if __name__ == "__main__":
    main()
