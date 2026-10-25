"""Modo escuro da página única (23/10/2026): a página segue o esquema de cor do aparelho, sem botão, e a impressão é sempre clara.

Com o navegador no escuro (contexto do Playwright com color_scheme="dark"), confere pelo estilo calculado (getComputedStyle e a
luminância relativa do WCAG):
- o aviso de privacidade, a página, o cabeçalho com o banner, a abertura com as duas entradas dos dados, a janela de envio com o
  modelo de planilha e a conversa flutuante com fundo escuro e texto claro, a 4,5:1 ou mais do fundo;
- a base carregada sem seleção (as abas, a Seleção de Territórios com os níveis, a busca e o que entra na análise; desde a segunda
  rodada de 24/10/2026, Voltar e Limpar seleção no alto, o aviso da mudança coletiva e o "Voltar aos estados" preenchido), os estados (E1)
  e o Amazonas (E2), marcado na lista de territórios, com "Entenda esta análise": o fundo da área e do gráfico escuros, o título, o subtítulo, os rótulos dos eixos e o aviso (âmbar) com contraste
  de texto; as bolhas na série única do escuro (#1ba3b5), com o anel na superfície escura (#1a1a19), e o eixo no tom do escuro;
- a dica da bolha, o painel de uma função, os Detalhes e o diálogo de Nova sessão, todos escuros e legíveis;
- o mapa (botão analise-desenho-mapa): com os pontos do motor, a superfície escura no canvas, as cores do escuro no gancho de
  teste e a legenda dos 5 grupos iguais (quintis) legível, sem a pergunta "Como pintar o mapa?" (retirada em 23/10/2026); se o
  motor não entregar os pontos no catálogo sintético, confere só a área do mapa (o fundo escuro e o aviso do motor legível) e
  registra isso na saída;
- a impressão (page.emulate_media(media="print")) volta ao claro: a página, o título, a superfície e as bolhas (#008b9e); de
  volta à tela, o escuro.
Tira capturas em .local/ui-validation (escuro-*.png) para a conferência visual. Catálogo sintético do Bloco 1; servidor
serve_ui_offline.py; nunca chama o provedor de IA e não pode ter erro de página. Seletores: data-testid (e o id do aviso de
privacidade, que dá nome ao diálogo).
"""
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import URL, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
AM = "13"  # prefixo IBGE do Amazonas
BOLHAS = '[data-testid="analise-bolha"][data-visivel="true"]'
SERIE_ESCURO, SERIE_CLARO = "#1ba3b5", "#008b9e"
SUPERFICIE_ESCURO = "#1a1a19"
# Todas as bolhas à vista (e há pelo menos uma) com o preenchimento pedido.
TODAS_NA_COR = """cor => { const marcas = [...document.querySelectorAll('[data-testid=analise-bolha][data-visivel=true] circle.analise-marca')];
  return marcas.length > 0 && marcas.every(e => e.getAttribute('fill') === cor); }"""

# Cor do texto (ou do preenchimento, no SVG) e o fundo efetivo: o primeiro fundo opaco dos ancestrais, com os semitransparentes
# compostos por cima, como o navegador pinta.
CORES = """(elemento, propriedade) => {
  const ler = texto => { const m = /rgba?\\(([^)]+)\\)/.exec(texto || ''); if (!m) return null;
    const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const camadas = [];
  for (let e = elemento; e; e = e.parentElement) {
    const c = ler(getComputedStyle(e).backgroundColor);
    if (c && c[3] > 0) { camadas.push(c); if (c[3] >= 1) break; }
  }
  let fundo = [255, 255, 255];
  for (let i = camadas.length - 1; i >= 0; i--) {
    const [r, g, b, a] = camadas[i];
    fundo = [r * a + fundo[0] * (1 - a), g * a + fundo[1] * (1 - a), b * a + fundo[2] * (1 - a)];
  }
  const c = ler(getComputedStyle(elemento)[propriedade]) || [0, 0, 0, 1];
  const cor = [0, 1, 2].map(i => c[i] * c[3] + fundo[i] * (1 - c[3]));
  return { cor: cor.map(Math.round), fundo: fundo.map(Math.round) };
}"""


def luminancia(rgb):
    def canal(c):
        c = c / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (canal(c) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a, b):
    claro, escuro = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (claro + 0.05) / (escuro + 0.05)


def hexa(rgb):
    return "#" + "".join(f"{round(c):02x}" for c in rgb[:3])


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 900}, color_scheme="dark")
        offline(context)
        page = context.new_page()
        failures, llm_calls, painel_calls = [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: painel_calls.append(request.url) if request.url.endswith("/api/painel") else None)
        notas = []

        def shot(nome, pagina_inteira=True):
            page.wait_for_timeout(700)  # transições do gráfico
            page.screenshot(path=str(OUTPUT / ("escuro-" + nome + ".png")), full_page=pagina_inteira)

        def cores(locator, propriedade="color"):
            return locator.evaluate(CORES, propriedade)

        def escuro(locator, rotulo):
            """O fundo efetivo do elemento é escuro (luminância relativa baixa) e devolve o fundo."""
            fundo = cores(locator)["fundo"]
            assert luminancia(fundo) < 0.05, (rotulo, "fundo claro no modo escuro", hexa(fundo))
            return fundo

        def legivel(locator, rotulo, propriedade="color", minimo=4.5):
            """Texto com contraste de pelo menos `minimo` (4,5:1, texto normal) com o fundo efetivo."""
            medida = cores(locator, propriedade)
            razao = contraste(medida["cor"], medida["fundo"])
            assert razao >= minimo, (rotulo, hexa(medida["cor"]), "sobre", hexa(medida["fundo"]), round(razao, 2))
            return medida

        def aperta(locator):
            locator.scroll_into_view_if_needed()
            locator.focus()
            locator.press("Enter")

        def respond(action, timeout=180000):
            with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.request.method == "POST", timeout=timeout) as event:
                action()
            response = event.value
            assert response.status == 200, response.text()[:2000]
            return response.json()

        def preenchimentos():
            return area.locator(BOLHAS + " circle.analise-marca").evaluate_all("els => els.map(e => e.getAttribute('fill'))")

        # 1. O aviso de privacidade, antes de tudo: o diálogo escuro, a declaração e o botão legíveis; a página toda no escuro.
        page.goto(URL)
        declaracao = page.locator("#privacy-declaration")
        expect(declaracao).to_be_visible(timeout=60000)
        assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == "dark", "controles nativos no escuro"
        assert page.evaluate("matchMedia('(prefers-color-scheme: dark)').matches"), "o contexto do navegador está no escuro"
        escuro(declaracao, "aviso de privacidade")
        legivel(declaracao, "declaração de privacidade")
        aceitar = page.get_by_role("button", name="Li e concordo", exact=True)
        legivel(aceitar, "botão Li e concordo")
        shot("01-privacidade", pagina_inteira=False)
        aceitar.click()

        # 2. A abertura (E0): a página, o cabeçalho com o banner, as entradas dos dados na área central, as abas com a
        # apresentação e a conversa flutuante, escuros e legíveis. Antes dos dados, não há barra da fonte no alto.
        area = page.get_by_test_id("area-de-analise")
        expect(area).to_be_visible(timeout=60000)
        expect(area).to_have_attribute("data-estado", "E0")
        fundo_pagina = cores(page.locator("body"))["fundo"]
        assert luminancia(fundo_pagina) < 0.02, ("página", hexa(fundo_pagina))
        assert luminancia(cores(page.locator("html"))["fundo"]) < 0.02
        legivel(page.get_by_test_id("pagina-marca"), "nome do agente")
        banner = page.get_by_test_id("pagina-banner")
        expect(banner).to_be_visible()
        legivel(banner.locator("h1"), "título do banner")
        expect(page.get_by_test_id("fonte-barra")).to_have_count(0)
        escuro(area, "área de análise")
        legivel(area.get_by_test_id("analise-titulo"), "título da área")
        legivel(area.get_by_test_id("analise-abertura-chamada"), "chamada da abertura")
        legivel(area.get_by_test_id("analise-fonte-brasil"), "botão primário (Usar dados do Brasil)")
        legivel(area.get_by_test_id("analise-fonte-arquivo"), "botão secundário (Enviar meus dados)")
        # A janela de envio, com o modelo de planilha, escura e legível.
        aperta(area.get_by_test_id("analise-fonte-arquivo"))
        janela = page.get_by_test_id("envio-de-dados")
        expect(janela).to_be_visible()
        escuro(janela, "janela de envio")
        legivel(janela.locator("p").first, "texto da janela de envio")
        legivel(janela.get_by_test_id("envio-escolher-arquivo"), "Escolher o arquivo")
        legivel(janela.get_by_test_id("envio-modelo-baixar"), "link do modelo de planilha")
        janela.get_by_test_id("envio-cancelar").click()
        expect(janela).to_have_count(0)
        chat = page.get_by_test_id("painel-chat")
        expect(chat).to_be_visible()
        escuro(chat, "conversa flutuante")
        guia = page.get_by_test_id("painel-chat-guia").locator("p").first
        legivel(guia, "texto da conversa")
        legivel(chat.get_by_test_id("chat-fonte-brasil"), "Usar dados do Brasil, na conversa")
        legivel(chat.locator("#assistant-input"), "campo da mensagem")
        shot("02-abertura")
        if chat.get_attribute("data-minimizada") != "true":
            chat.get_by_test_id("painel-chat-minimizar").click()

        # 3. A base carregada sem seleção: o aviso e a lista de territórios, escuros e legíveis. Os estados (E1), escolhidos na
        # Seleção de Territórios: o gráfico escuro; as bolhas na série única do escuro; o mapa desligado mostra o motivo (âmbar).
        area.get_by_test_id("analise-fonte-brasil").click()
        territorios = area.get_by_test_id("analise-territorios")
        expect(territorios).to_be_visible(timeout=120000)
        legivel(page.get_by_test_id("nav-new-session"), "Nova sessão")
        legivel(area.get_by_test_id("analise-aba-territorios"), "aba da Seleção de Territórios")
        escuro(area.get_by_test_id("analise-aba-painel"), "painel da aba")
        legivel(area.get_by_test_id("analise-apresentacao").locator("p").first, "orientação da Seleção")
        escuro(territorios, "lista de territórios")
        legivel(territorios.get_by_test_id("analise-nivel-municipios"), "nível escolhido (Municípios)")
        legivel(territorios.get_by_test_id("analise-nivel-estados"), "nível Estados")
        legivel(territorios.get_by_test_id("analise-busca"), "busca no alto")
        escuro(territorios.get_by_test_id("analise-selecionados"), "o que entra na análise")
        legivel(territorios.get_by_test_id("analise-selecionados-resumo"), "resumo do que entra na análise")
        aperta(territorios.get_by_test_id("analise-nivel-estados"))
        legivel(territorios.get_by_test_id("analise-marcar-todos"), "Marcar todos os estados")
        estados = respond(lambda: aperta(territorios.get_by_test_id("analise-marcar-todos")))
        # Voltar e Limpar seleção (24/10/2026, segunda rodada): no alto da área, com fundo escuro e os nomes legíveis; o aviso da
        # mudança coletiva ("Para desfazer, use Voltar, no alto.") junto do que está marcado, também legível.
        controles = area.get_by_test_id("analise-controles-globais")
        escuro(controles, "Voltar e Limpar seleção, no alto")
        legivel(controles.get_by_test_id("analise-voltar"), "Voltar")
        legivel(controles.get_by_test_id("analise-limpar-selecao"), "Limpar seleção (vassoura)")
        legivel(territorios.get_by_test_id("analise-selecao-aviso"), "aviso da mudança coletiva, com o caminho do Voltar")
        legivel(territorios.get_by_test_id("analise-ver-analise"), "Ver a análise")
        aperta(territorios.get_by_test_id("analise-ver-analise"))
        expect(area).to_have_attribute("data-estado", "E1")
        assert estados["itens"], "o motor devolveu os estados"
        grafico = area.get_by_test_id("analise-grafico")
        expect(area.locator(BOLHAS).first).to_be_visible(timeout=30000)
        escuro(grafico, "gráfico")
        assert set(preenchimentos()) == {SERIE_ESCURO}, preenchimentos()
        aperta(area.get_by_test_id("analise-desenho-mapa"))
        motivo = area.get_by_test_id("analise-desenho-motivo")
        expect(motivo).to_be_visible()
        escuro(motivo, "motivo do mapa desligado")
        legivel(motivo, "motivo do mapa desligado (âmbar)")
        shot("03-estados")

        # 4. O Amazonas marcado na lista de territórios (E2): fundo da área e do gráfico escuros, textos legíveis, a paleta do escuro.
        aperta(area.get_by_test_id("analise-aba-territorios"))
        aperta(territorios.get_by_test_id("analise-nivel-municipios"))
        linha_am = territorios.locator('[data-testid="analise-grupo"][data-id="' + AM + '"]')
        expect(linha_am).to_contain_text("Amazonas")
        escuro(territorios, "lista de territórios")
        legivel(linha_am.get_by_test_id("analise-grupo-ver"), "Ver os municípios (link de ação)")
        # "Voltar aos estados" (24/10/2026, segunda rodada): o botão preenchido da lista do estado, legível no escuro; ele só fecha
        # a lista.
        aperta(linha_am.get_by_test_id("analise-grupo-ver"))
        legivel(territorios.get_by_test_id("analise-grupo-voltar"), "Voltar aos estados (preenchido)")
        escuro(territorios.get_by_test_id("analise-selecionados"), "o que entra na análise, à direita")
        aperta(territorios.get_by_test_id("analise-grupo-voltar"))
        expect(linha_am.get_by_test_id("analise-grupo-todos")).to_be_visible()
        caixa_am = linha_am.get_by_test_id("analise-grupo-todos")

        def marca_am():
            caixa_am.scroll_into_view_if_needed()
            caixa_am.focus()
            caixa_am.press("Space")
        am = respond(marca_am)
        aperta(territorios.get_by_test_id("analise-ver-analise"))
        expect(area).to_have_attribute("data-estado", "E2")
        assert all(item["tipo"] == "municipio" for item in am["itens"])
        com_valor = sorted(item["id"] for item in am["itens"] if item.get("densidade") is not None)
        page.wait_for_function("ids => JSON.stringify([...document.querySelectorAll('[data-testid=analise-bolha][data-visivel=true]')]"
                               ".map(e => e.dataset.id).sort()) === JSON.stringify(ids)", arg=com_valor, timeout=30000)
        fundo_area = escuro(area, "área de análise")
        fundo_grafico = escuro(grafico, "superfície do gráfico")
        assert hexa(fundo_grafico) == SUPERFICIE_ESCURO, ("superfície do gráfico", hexa(fundo_grafico))
        assert luminancia(fundo_area) < luminancia(fundo_grafico), "o gráfico um pouco acima do cartão da área"
        titulo = legivel(area.get_by_test_id("analise-titulo"), "título")
        assert luminancia(titulo["cor"]) > 0.6, ("o texto principal é claro", hexa(titulo["cor"]))
        legivel(area.get_by_test_id("analise-subtitulo"), "subtítulo")
        if (area.get_by_test_id("analise-resumo").text_content() or "").strip():
            legivel(area.get_by_test_id("analise-resumo"), "frase-resumo do motor")
        # Os ajustes ficam na aba da análise (a troca de aba, sem trocar de análise, não pede nada ao motor).
        aperta(area.get_by_test_id("analise-familia-distribuicao"))
        expect(area).to_have_attribute("data-aba", "distribuicao")
        legivel(area.get_by_test_id("analise-entenda-botao"), "Entenda esta análise")
        legivel(area.get_by_test_id("analise-selecao-resumo"), "resumo da seleção, na aba da análise")
        legivel(area.get_by_test_id("analise-ajustes").get_by_test_id("analise-indicador-densidade"), "indicador escolhido (preenchido)")
        legivel(area.get_by_test_id("analise-ajustes").get_by_test_id("analise-indicador-quantidade"), "indicador não escolhido")
        legivel(area.get_by_test_id("analise-arranjo-nota"), "nota do arranjo, na legenda")
        eixo_y = area.get_by_test_id("analise-eixo-y")
        legivel(eixo_y.locator("text").first, "marca do eixo", propriedade="fill")
        assert eixo_y.locator("line").first.get_attribute("stroke") == "#383835", "eixo no tom do escuro"
        marcas = area.locator(BOLHAS + " circle.analise-marca")
        assert marcas.count() == len(com_valor) and set(preenchimentos()) == {SERIE_ESCURO}, preenchimentos()
        assert set(marcas.evaluate_all("els => els.map(e => e.getAttribute('stroke'))")) == {SUPERFICIE_ESCURO}, "anel na superfície escura"
        # A família indisponível (rotatividade, na base do Brasil) mostra o motivo, em âmbar, legível.
        aperta(area.get_by_test_id("analise-familia-rotatividade"))
        motivo_familia = area.get_by_test_id("analise-familia-motivo")
        expect(motivo_familia).to_be_visible()
        legivel(motivo_familia, "motivo da família indisponível (âmbar)")
        legivel(motivo_familia.get_by_test_id("analise-enviar-dados"), "Enviar meus dados, no motivo")
        expect(area).to_have_attribute("data-familia", "distribuicao")
        shot("04-amazonas")

        # 5. A dica da bolha (elevada sobre o gráfico), o painel de uma função e os Detalhes.
        maior = max((item for item in am["itens"] if item["id"] in com_valor), key=lambda item: item.get("populacao") or 0)
        grafico.evaluate("e => e.scrollIntoView({block: 'start', behavior: 'instant'})")
        area.locator('[data-testid="analise-bolha"][data-id="' + maior["id"] + '"]').hover()
        dica = area.get_by_test_id("analise-dica")
        expect(dica).to_contain_text(maior["rotulo"])
        fundo_dica = escuro(dica, "dica")
        assert luminancia(fundo_dica) > luminancia(fundo_grafico), "a dica um pouco acima da superfície do gráfico"
        legivel(dica.locator("strong").first, "título da dica")
        shot("05-dica", pagina_inteira=False)
        page.mouse.move(2, 2)
        aperta(area.get_by_test_id("analise-funcao-regua"))
        painel = area.get_by_test_id("analise-painel")
        expect(painel).to_have_attribute("data-painel", "regua")
        escuro(painel, "painel da função")
        assert luminancia(cores(painel)["fundo"]) > luminancia(fundo_area), "o painel um pouco acima do cartão da área"
        legivel(page.locator("#analise-painel-titulo"), "título do painel")
        legivel(painel.get_by_test_id("analise-regua-texto"), "texto da régua")
        shot("06-painel")
        aperta(painel.get_by_test_id("analise-painel-fechar"))
        expect(area.get_by_test_id("analise-painel")).to_have_count(0)
        detalhes = area.get_by_test_id("analise-detalhes")
        escuro(detalhes, "Detalhes")
        legivel(detalhes.get_by_test_id("analise-detalhes-tabela"), "aba dos Detalhes")
        legivel(detalhes.get_by_test_id("analise-linha").first.locator("td").nth(1), "linha da tabela")

        # 6. O mapa: com os pontos do motor, a superfície escura no canvas e as cores do escuro; sem eles, a área do mapa.
        calls = len(painel_calls)
        aperta(area.get_by_test_id("analise-desenho-mapa"))
        expect(area).to_have_attribute("data-desenho", "mapa")
        vista_mapa = area.get_by_test_id("analise-vista-mapa")
        expect(vista_mapa).to_be_visible()
        mapa, erro_mapa = area.get_by_test_id("mapa-analise"), area.get_by_test_id("analise-mapa-erro")
        expect(mapa.or_(erro_mapa)).to_be_visible(timeout=60000)
        expect(page.get_by_test_id("transicao-vistas")).to_have_count(0, timeout=10000)
        escuro(vista_mapa, "área do mapa")
        if mapa.is_visible():
            expect(mapa).to_have_attribute("data-esquema", "escuro")
            page.wait_for_function("() => { const m = window.__adtMapa; return !!m && m.largura > 0; }", timeout=60000)
            gancho = page.evaluate("() => { const m = window.__adtMapa; return { esquema: m.esquema, superficie: m.superficie, "
                                   "pintura: m.pintura, pontos: m.pontos.map(p => ({ cor: p.cor, vazada: p.vazada, esmaecido: p.esmaecido })) }; }")
            assert gancho["esquema"] == "escuro" and gancho["superficie"] == SUPERFICIE_ESCURO, gancho
            if gancho["pintura"] == "camada":  # sem os quintis do motor: a cor única do escuro
                assert all(ponto["cor"] == SERIE_ESCURO for ponto in gancho["pontos"] if not ponto["vazada"]), gancho["pontos"]
            canvas = mapa.get_by_test_id("mapa-canvas")
            pixel = canvas.evaluate("c => [...c.getContext('2d').getImageData(1, 1, 1, 1).data]")
            assert hexa(pixel) == SUPERFICIE_ESCURO, ("canvas na superfície escura", pixel)
            escuro(canvas, "quadro do mapa")
            legivel(mapa.get_by_test_id("mapa-nota"), "nota do mapa")
            expect(mapa.get_by_test_id("mapa-pergunta")).to_have_count(0)
            if gancho["pintura"] == "quintis":
                legivel(mapa.get_by_test_id("mapa-legenda-quintis"), "legenda dos quintis do mapa")
                legivel(mapa.get_by_test_id("mapa-quintil").first, "item da legenda dos quintis")
            legivel(mapa.get_by_test_id("mapa-ampliar"), "controle do mapa", minimo=3)
            notas.append("mapa com os pontos do motor (" + str(len(gancho["pontos"])) + " pontos), conferido no escuro")
        else:
            escuro(erro_mapa, "aviso do mapa")
            legivel(erro_mapa.locator("p").first, "aviso do motor sobre o mapa (rosa)")
            legivel(erro_mapa.get_by_test_id("analise-mapa-tentar"), "Tentar novamente, no aviso do mapa")
            notas.append("o motor não entregou os pontos do mapa no catálogo sintético; conferida só a área do mapa: "
                         + (erro_mapa.text_content() or "").strip()[:160])
        shot("07-mapa")
        assert len(painel_calls) == calls, "trocar a vista não pede nada novo ao gráfico"
        aperta(area.get_by_test_id("analise-desenho-grafico"))
        expect(area).to_have_attribute("data-desenho", "grafico")
        expect(page.get_by_test_id("transicao-vistas")).to_have_count(0, timeout=10000)

        # 7. O diálogo de Nova sessão: escuro, com o texto e os botões legíveis; "Continuar nesta sessão" fecha.
        page.get_by_test_id("nav-new-session").click()
        dialogo = page.get_by_test_id("new-session-confirmation")
        expect(dialogo).to_be_visible()
        escuro(dialogo, "diálogo de Nova sessão")
        legivel(dialogo.locator("p").first, "texto do diálogo")
        legivel(dialogo.get_by_test_id("cancel-new-session"), "botão do diálogo")
        shot("08-dialogo", pagina_inteira=False)
        dialogo.get_by_test_id("cancel-new-session").click()
        expect(dialogo).to_have_count(0)

        # 8. A impressão é sempre clara: a página, o título, a superfície do gráfico e as bolhas na série do claro.
        page.emulate_media(media="print")
        page.wait_for_function(TODAS_NA_COR, arg=SERIE_CLARO, timeout=10000)
        assert page.evaluate("getComputedStyle(document.documentElement).colorScheme") == "light"
        assert luminancia(cores(page.locator("html"))["fundo"]) > 0.9, "a página impressa é clara"
        fundo_impresso = cores(grafico)["fundo"]
        assert luminancia(fundo_impresso) > 0.9, ("superfície impressa", hexa(fundo_impresso))
        titulo_impresso = legivel(area.get_by_test_id("analise-titulo"), "título na impressão")
        assert luminancia(titulo_impresso["cor"]) < 0.1, ("título escuro sobre o claro", hexa(titulo_impresso["cor"]))
        assert set(area.locator(BOLHAS + " circle.analise-marca").evaluate_all("els => els.map(e => e.getAttribute('stroke'))")) == {"#fcfcfb"}
        shot("09-impressao")
        page.emulate_media(media="screen")
        page.wait_for_function(TODAS_NA_COR, arg=SERIE_ESCURO, timeout=10000)
        escuro(grafico, "de volta à tela")

        assert not llm_calls, llm_calls
        assert not failures, failures
        browser.close()
    for nota in notas:
        print("Nota:", nota)
    print("MODO ESCURO PASS: aviso de privacidade, página, conversa, estados, Amazonas, dica, painel, Detalhes, mapa, diálogo e "
          "impressão clara (catálogo sintético).")


if __name__ == "__main__":
    main()
