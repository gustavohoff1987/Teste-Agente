"""Capturas das telas principais da página única com a base versionada, para a conferência visual (somente leitura).

Uso, de qualquer pasta do repositório, depois de "npm run build" em frontend/:
    python scripts/capturar_telas.py [--saida PASTA] [--canal chrome|chromium]

Sobe o servidor de testes (backend/tests/serve_ui_offline.py, sem transporte de IA) com a base versionada da raiz, percorre
as telas principais da página única e salva as capturas em .local/capturas/<data-hora>/, pasta ignorada pelo Git. Desde o
comando V22 (9/11/2026), as telas da Seleção de Territórios: a árvore Brasil → região → estado → município, a Região Norte
aberta, a seleção com o Pará e a Bahia como unidade ("Só o estado") e os municípios do Amazonas, com o mapa da seleção, a lista
e as três ações; a Distribuição com os dois níveis e os quintis de cada um; "Aplicar critérios de seleção"; "Agrupar territórios selecionados" por escolha livre e
por proximidade; a seleção com os conjuntos; a dica de um conjunto, com todos os membros; a Escolha dos territórios da Análise
Espacial com a base em conjuntos e territórios individuais; o foco numa base da Análise Espacial; os estados como unidade ("Só
os estados"); o Detector de Sinais Territoriais (a tabela, os detalhes, os alertas do Brasil e os parâmetros) e o Simulador de
Cenários Territoriais (os territórios, as intervenções, os resultados, a base e o método e a validação). Da etapa 5 do comando
(telas 25 a 38): os fenômenos 8 a 12 do Detector em jun/2021, quando a comparação de 2 anos é habilitada (as bolhas da distância e
da taxa, o mapa dos sinais, a série da taxa com a referência e os detalhes de cada fenômeno); "Abrir no Simulador" com as
referências de comparação, as comparações, o planejamento inverso e o Brasil como território; e "Simular recuperação", com a meta
hipotética e o resultado. Depois, o Histórico, o diálogo de Nova sessão, o painel "Colunas" de uma planilha de distritos e províncias
(criada numa pasta temporária) e a Seleção no celular. Nada vai para o provedor de IA, nenhum dado é alterado e o servidor é
encerrado no fim. Uma tela que falhar é informada no fim, sem impedir as seguintes. Saída: 0 se todas as capturas foram feitas.
"""
import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist" / "index.html"
sys.path.insert(0, str(ROOT / "backend" / "tests"))
AM, PA, BA = "13", "15", "29"
MANAUS, FLORIANOPOLIS = "code:130260", "code:420540"
# A tabela do Detector tem 50 linhas por página: as capturas dele mostram o alto da página (os filtros, o gráfico ou o mapa, as
# primeiras linhas e os detalhes abertos). A página inteira passaria do limite de altura de uma imagem do navegador.
ALTO_DO_DETECTOR = 4200


def porta_livre():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def aguardar(url, segundos=90):
    limite = time.time() + segundos
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=5) as resposta:
                if resposta.status == 200:
                    return True
        except OSError:
            time.sleep(0.5)
    return False


def build_desatualizado():
    fontes = [p for p in (ROOT / "frontend" / "src").rglob("*") if p.is_file()]
    return any(p.stat().st_mtime > DIST.stat().st_mtime for p in fontes)


def capturar(url, saida, canal):
    from playwright.sync_api import expect, sync_playwright
    from ui_support import abrir_regiao, accept_privacy, is_post, offline, options_of

    feitas, falhas = [], []
    with tempfile.TemporaryDirectory(prefix="adt-capturas-") as temporaria, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=canal)
        context = browser.new_context(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
        offline(context)
        page = context.new_page()
        erros = []
        page.on("pageerror", lambda erro: erros.append(str(erro)))
        area = page.get_by_test_id("area-de-analise")
        territorios = area.get_by_test_id("analise-territorios")
        respostas = {}

        def tela(nome, acao, manter_rolagem=False, altura_maxima=None):
            """Executa os passos da tela e salva a captura da página inteira. Antes, volta ao topo: a barra fixa (Desfazer e Limpar
            seleção) fica no lugar dela, em vez de aparecer no meio da página. `manter_rolagem` fica para a tela que depende do
            ponteiro parado sobre um elemento (a dica). Com `altura_maxima`, a captura para nessa altura (o alto da página)."""
            try:
                acao()
                if not manter_rolagem:
                    page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(900)  # transições curtas do gráfico
                caminho = saida / (nome + ".png")
                altura = page.evaluate("document.documentElement.scrollHeight")
                if altura_maxima and altura > altura_maxima:
                    page.screenshot(path=str(caminho), full_page=True,
                                    clip={"x": 0, "y": 0, "width": page.viewport_size["width"], "height": altura_maxima})
                else:
                    page.screenshot(path=str(caminho), full_page=True)
                feitas.append(caminho.name)
                print("   ok:", caminho.name, flush=True)
            except Exception as erro:  # noqa: BLE001 — a tela seguinte ainda é útil para a conferência
                falhas.append(f"{nome}: {str(erro).splitlines()[0]}")
                print("   FALHOU:", falhas[-1], flush=True)

        def grafico(acao, condicao=lambda opcoes: True, chave=None):
            """Executa a ação e espera o gráfico com o pedido correspondente ao motor (/api/painel); guarda a resposta."""
            with page.expect_response(lambda r: is_post(r, "/api/painel") and condicao(options_of(r.request)), timeout=180000) as evento:
                acao()
            if chave:
                respostas[chave] = evento.value.json()

        def minimizar_conversa():
            chat = page.get_by_test_id("painel-chat")
            if chat.count() and chat.get_attribute("data-minimizada") == "false":
                chat.get_by_test_id("painel-chat-minimizar").click()

        def linha_do_estado(prefixo):
            abrir_regiao(territorios, prefixo[0])
            return territorios.locator('[data-testid="analise-grupo"][data-id="' + prefixo + '"]')

        def abertura():
            page.goto(url)
            accept_privacy(page)
            expect(page.get_by_test_id("painel-chat")).to_have_attribute("data-ampla", "true")

        def arvore():
            minimizar_conversa()
            area.get_by_test_id("analise-fonte-brasil").click()
            expect(territorios.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
            expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=90000)

        def regiao_norte():
            abrir_regiao(territorios, "1")

        def selecao_mista():
            para = linha_do_estado(PA)
            grafico(lambda: para.get_by_test_id("analise-grupo-so-estado").click())
            bahia = linha_do_estado(BA)
            grafico(lambda: bahia.get_by_test_id("analise-grupo-so-estado").click())
            amazonas = linha_do_estado(AM)
            grafico(lambda: amazonas.get_by_test_id("analise-grupo-todos").check(), chave="mista")
            para.get_by_test_id("analise-grupo-ver").click()  # os municípios do Pará, esmaecidos e bloqueados
            expect(territorios.get_by_test_id("analise-mapa-selecao").locator("svg").first).to_be_visible(timeout=120000)

        def distribuicao_mista():
            territorios.get_by_test_id("analise-confirmar-selecao").click()
            expect(area).to_have_attribute("data-aba", "distribuicao")
            expect(area.locator('[data-testid="analise-bolha"][data-tipo="estado"][data-visivel="true"]')).to_have_count(2, timeout=60000)
            # Os quintis de cada nível, com a legenda de cada um (a dos estados à parte).
            grafico(lambda: area.get_by_test_id("analise-ajustes").get_by_test_id("analise-agrupar").select_option("quintis"),
                    lambda o: bool(o.get("grupos")))
            expect(area.get_by_test_id("analise-legenda-nivel-estados").first).to_be_visible(timeout=60000)

        def criterios():
            area.get_by_test_id("analise-aba-territorios").click()
            territorios.get_by_test_id("analise-aplicar-criterios").click()
            expect(territorios.get_by_test_id("analise-criterios")).to_be_visible()

        def agrupar_livre():
            territorios.get_by_test_id("analise-criterios-cancelar").click()
            territorios.get_by_test_id("analise-agrupar-selecionados").click()
            expect(territorios.get_by_test_id("analise-agrupamento")).to_have_attribute("data-modo", "livre")

        def agrupar_proximidade():
            territorios.get_by_test_id("analise-agrupar-proximidade").click()
            territorios.get_by_test_id("analise-agrupar-km").fill("60")
            expect(territorios.get_by_test_id("analise-agrupar-conjunto").first).to_be_visible(timeout=120000)

        def selecao_com_conjuntos():
            grafico(lambda: territorios.get_by_test_id("analise-agrupar-usar").click(), lambda o: bool(o.get("conjuntos")), chave="conjuntos")
            expect(territorios.get_by_test_id("analise-selecionado-conjunto").first).to_be_visible(timeout=60000)

        def dica_do_conjunto():
            territorios.get_by_test_id("analise-confirmar-selecao").click()
            bolha = area.locator('[data-testid="analise-bolha"][data-tipo="conjunto"][data-visivel="true"]').first
            expect(bolha).to_be_visible(timeout=60000)
            bolha.hover()
            expect(area.locator(".analise-dica").first).to_be_visible(timeout=10000)

        def espacial_escolha():
            page.mouse.move(5, 5)
            area.get_by_test_id("analise-familia-espacial").click()
            janela = area.get_by_test_id("analise-painel").get_by_test_id("analise-referencia")
            expect(janela).to_be_visible(timeout=60000)
            janela.get_by_test_id("territorios-aba-referencia").click()
            janela.get_by_test_id("territorios-referencia-mais-densidade").click()
            filtro = janela.get_by_test_id("territorios-referencia-filtro").first
            filtro.get_by_test_id("territorios-referencia-filtro-operador").select_option(">=")
            filtro.get_by_test_id("territorios-referencia-filtro-valor").fill("3")
            expect(janela.get_by_test_id("territorios-calcular")).to_be_enabled(timeout=60000)
            grafico(lambda: janela.get_by_test_id("territorios-calcular").click(), lambda o: bool(o.get("consulta")), chave="espacial")
            janela.get_by_test_id("territorios-aba-base").click()

        def espacial_foco():
            area.get_by_test_id("analise-painel-fechar").click()
            itens = respostas.get("espacial", {}).get("itens", [])
            base = next(item["id"] for item in itens if item.get("distancia_km") is not None)
            bolha = area.locator('[data-testid="analise-bolha"][data-id="' + base + '"]')
            bolha.scroll_into_view_if_needed()
            bolha.click()
            expect(area.get_by_test_id("analise-foco-espacial")).to_be_visible(timeout=30000)

        def detector_tabela():
            # O Detector de Sinais Territoriais com a seleção mista em uso (municípios, conjuntos e estados como unidade).
            area.get_by_test_id("analise-ferramenta-detector").click()
            detector = area.get_by_test_id("detector")
            expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
            expect(detector.get_by_test_id("detector-linha").first).to_be_visible()

        def detector_detalhe():
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-abrir").first.click()
            expect(detector.get_by_test_id("detector-detalhe")).to_be_visible(timeout=60000)
            detector.get_by_test_id("detector-historico-botao").click()
            expect(detector.get_by_test_id("detector-historico")).to_be_visible()

        def detector_brasil():
            # Todos os municípios do Brasil: os territórios com nível em "Queda recente" no último registro, com os detalhes do primeiro.
            area.get_by_test_id("analise-limpar-selecao").click()
            area.get_by_test_id("analise-aba-territorios").click()
            grafico(lambda: territorios.get_by_test_id("analise-raiz-caixa").check())
            area.get_by_test_id("analise-ferramenta-detector").click()
            detector = area.get_by_test_id("detector")
            expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
            detector.get_by_test_id("detector-filtro-sinal").select_option("perda")
            detector.get_by_test_id("detector-abrir").first.click()
            expect(detector.get_by_test_id("detector-detalhe")).to_be_visible(timeout=60000)

        def detector_parametros():
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-abrir").first.click()  # fecha os detalhes
            detector.get_by_test_id("detector-metodo-botao").click()
            detector.get_by_test_id("detector-parametros-botao").click()
            detector.get_by_test_id("detector-parametro-perda-elevado_um_em").fill("50")
            detector.get_by_test_id("detector-parametros-aplicar").click()
            expect(detector.get_by_test_id("detector-exploratorio")).to_be_visible(timeout=180000)

        def simulador_territorios():
            # O Simulador de Cenários com a cópia local da seleção mista; um município acrescentado só no Simulador.
            area.get_by_test_id("analise-ferramenta-simulador").click()
            simulador = area.get_by_test_id("simulador")
            expect(simulador.get_by_test_id("simulador-local").first).to_be_visible(timeout=60000)
            simulador.get_by_test_id("simulador-composicao-botao").click()
            simulador.get_by_test_id("simulador-busca").fill("rio rufino")
            expect(simulador.get_by_test_id("simulador-acrescentar").first).to_be_visible()

        def simulador_intervencoes():
            simulador = area.get_by_test_id("simulador")
            simulador.locator('[data-testid="simulador-acrescentar"][data-id="code:421505"]').click()
            simulador.get_by_test_id("simulador-busca").fill("")
            simulador.get_by_test_id("simulador-etapa-3").click()
            simulador.get_by_test_id("simulador-atalho-4").click()
            simulador.get_by_test_id("simulador-intervencao-nova").click()
            simulador.get_by_test_id("simulador-intervencao-quantidade").fill("5")

        def simulador_resultados():
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-calcular").click()
            expect(simulador).to_have_attribute("data-estado", "pronto", timeout=180000)
            expect(simulador.get_by_test_id("simulador-grafico")).to_be_visible()

        def simulador_base_e_metodo():
            # O modo avançado, com um segundo cenário (a taxa composta da janela), e as estatísticas históricas, só descritivas.
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-modo-avancado").click()
            simulador.get_by_test_id("simulador-etapa-2").click()
            simulador.get_by_test_id("simulador-cenario-novo").click()
            simulador.get_by_test_id("simulador-metodo").nth(1).select_option("M1")
            expect(simulador.get_by_test_id("simulador-estatisticas")).to_be_visible()

        def simulador_validacao():
            # Dois cenários e a referência, com um estado como unidade no gráfico (sem faixa) e a validação dos métodos aberta.
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-calcular-direto").click()
            expect(simulador).to_have_attribute("data-estado", "pronto", timeout=180000)
            simulador.get_by_test_id("simulador-foco").select_option("uf:" + PA)
            simulador.get_by_test_id("simulador-validacao-botao").click()
            expect(simulador.get_by_test_id("simulador-faixas")).to_be_visible()

        def do_detector(acao):
            """Executa a ação e espera a resposta do Detector (/api/detector) e a tela pronta."""
            with page.expect_response(lambda r: is_post(r, "/api/detector"), timeout=180000):
                acao()
            expect(area.get_by_test_id("detector")).to_have_attribute("data-estado", "pronto", timeout=180000)

        def fenomeno(chave):
            """Abre, nos detalhes do território, a explicação completa do sinal pedido."""
            item = area.get_by_test_id("detector").locator('[data-testid="detector-fenomeno"][data-chave="' + chave + '"]')
            botao = item.get_by_test_id("detector-fenomeno-completa")
            if botao.get_attribute("aria-expanded") != "true":
                botao.click()
            expect(item.locator("dl")).to_be_visible()

        def detector_bolhas():
            # Etapa 5: em jun/2021 a comparação de 2 anos é habilitada (jun/2019 a jun/2021). Os municípios com queda da taxa por
            # habitante (fenômeno 8), nas bolhas: a distância até quem atende ao critério (fenômeno 11) e a taxa.
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-abrir").first.click()  # fecha os detalhes
            do_detector(lambda: detector.get_by_test_id("detector-janela-fim").select_option("202106"))
            detector.get_by_test_id("detector-filtro-sinal").select_option("disponibilidade")
            detector.get_by_test_id("detector-vista-grafico").click()
            expect(detector.get_by_test_id("detector-bolhas")).to_be_visible(timeout=60000)

        def detector_mapa():
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-vista-mapa").click()
            expect(detector.get_by_test_id("detector-mapa")).to_be_visible(timeout=60000)

        def detector_taxa():
            # Os detalhes de um território com o sinal: a série da taxa com a referência (tracejada) e o fenômeno 8.
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-vista-lista").click()
            detector.get_by_test_id("detector-abrir").first.click()
            expect(detector.get_by_test_id("detector-serie-da-taxa")).to_be_visible(timeout=60000)
            fenomeno("disponibilidade")

        def detector_combinados():
            # Os sinais combinados (fenômeno 12): o primeiro território com uma combinação, com o texto do fenômeno aberto.
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-abrir").first.click()  # fecha os detalhes
            detector.get_by_test_id("detector-filtro-sinal").select_option("juntos")
            detector.get_by_test_id("detector-abrir").first.click()
            expect(detector.get_by_test_id("detector-detalhe")).to_be_visible(timeout=60000)
            fenomeno("coexistencia")

        def abrir_no_simulador():
            # "Abrir no Simulador": Manaus, no último registro, vai ao Simulador com o contexto do Detector; lá, três referências
            # (Florianópolis, dinâmica; o Brasil, fixo; e um valor informado).
            detector = area.get_by_test_id("detector")
            detector.get_by_test_id("detector-abrir").first.click()  # fecha os detalhes
            do_detector(lambda: detector.get_by_test_id("detector-janela-fim").select_option("202406"))
            detector.get_by_test_id("detector-filtro-sinal").select_option("todos")
            detector.get_by_test_id("detector-busca").fill("manaus")
            detector.locator('[data-testid="detector-linha"][data-id="' + MANAUS + '"]').get_by_test_id("detector-abrir").click()
            expect(detector.get_by_test_id("detector-detalhe")).to_be_visible(timeout=60000)
            detector.get_by_test_id("detector-abrir-no-simulador").click()
            simulador = area.get_by_test_id("simulador")
            expect(simulador.get_by_test_id("simulador-do-detector")).to_be_visible(timeout=60000)
            simulador.get_by_test_id("simulador-referencia-busca").fill("florian")
            simulador.locator('[data-testid="simulador-referencia-acrescentar"][data-id="' + FLORIANOPOLIS + '"]').click()
            simulador.locator('[data-testid="simulador-referencia-item"][data-alvo="' + FLORIANOPOLIS + '"]').get_by_test_id(
                "simulador-referencia-tipo").select_option("dinamica")
            simulador.get_by_test_id("simulador-referencia-brasil").click()
            simulador.get_by_test_id("simulador-referencia-valor-nova").click()
            simulador.get_by_test_id("simulador-referencia-valor").fill("6500")
            expect(simulador.get_by_test_id("simulador-referencias")).to_have_attribute("data-total", "3")

        def do_simulador(acao):
            with page.expect_response(lambda r: is_post(r, "/api/simulador"), timeout=180000):
                acao()
            expect(area.get_by_test_id("simulador")).to_have_attribute("data-estado", "pronto", timeout=180000)

        def simulador_comparacoes():
            # As comparações: as curvas das referências no gráfico (a do Brasil, fora da escala) e os textos de cada uma.
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-etapa-3").click()
            simulador.get_by_test_id("simulador-atalho-4").click()
            do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
            expect(simulador.get_by_test_id("simulador-comparacao").first).to_be_visible()

        def simulador_planejamento():
            # O planejamento inverso: a meta hipotética de alcançar a referência (Florianópolis), com um acréscimo por ano.
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-etapa-1").click()   # o Brasil sai: o planejamento fica só com Manaus
            simulador.locator('[data-testid="simulador-local"][data-id="br"]').get_by_role("button").click()
            simulador.get_by_test_id("simulador-etapa-3").click()
            simulador.get_by_test_id("simulador-plano-novo").click()
            simulador.get_by_test_id("simulador-plano-meta").select_option("referencia")
            simulador.get_by_test_id("simulador-plano-periodica").check()
            simulador.get_by_test_id("simulador-plano-ate").fill("2028-06")
            expect(simulador.get_by_test_id("simulador-plano")).to_have_attribute("data-meta", "referencia")

        def simulador_planejamento_resultado():
            simulador = area.get_by_test_id("simulador")
            do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
            expect(simulador.get_by_test_id("simulador-planejamento-texto").first).to_be_visible()

        def simulador_plano_como_intervencao():
            # "Usar como intervenção deste cenário": o acréscimo calculado entra nas intervenções, e o cenário recalculado alcança a meta.
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-planejamento-usar").click()
            expect(simulador.get_by_test_id("simulador-intervencao")).to_have_count(1)
            do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
            expect(simulador.get_by_test_id("simulador-evento").first).to_be_visible()

        def simulador_brasil():
            # O Brasil como território, só no Simulador: a contagem nacional, com o padrão provisório (taxa composta de 3 anos), sem faixa.
            simulador = area.get_by_test_id("simulador")
            simulador.get_by_test_id("simulador-etapa-1").click()
            simulador.get_by_test_id("simulador-busca").fill("brasil")
            simulador.locator('[data-testid="simulador-acrescentar"][data-id="br"]').click()
            simulador.get_by_test_id("simulador-busca").fill("")
            do_simulador(lambda: simulador.get_by_test_id("simulador-calcular-direto").click())
            simulador.get_by_test_id("simulador-foco").select_option("br")
            expect(simulador.get_by_test_id("simulador-grafico")).to_be_visible()

        def simular_recuperacao():
            # "Simular recuperação": do Detector, um município abaixo do patamar anterior vai ao Simulador com a meta hipotética
            # (e editável) de voltar ao patamar; o Simulador abre na etapa em que a meta está à vista.
            area.get_by_test_id("analise-ferramenta-detector").click()
            detector = area.get_by_test_id("detector")
            expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
            detector.get_by_test_id("detector-filtro-sinal").select_option("patamar")
            detector.get_by_test_id("detector-abrir").first.click()
            expect(detector.get_by_test_id("detector-simular-recuperacao")).to_be_visible(timeout=60000)
            detector.get_by_test_id("detector-simular-recuperacao").click()
            simulador = area.get_by_test_id("simulador")
            expect(simulador).to_have_attribute("data-etapa", "3", timeout=60000)
            expect(simulador.get_by_test_id("simulador-plano")).to_have_attribute("data-meta", "patamar")

        def simular_recuperacao_resultado():
            simulador = area.get_by_test_id("simulador")
            do_simulador(lambda: simulador.get_by_test_id("simulador-calcular").click())
            expect(simulador.get_by_test_id("simulador-planejamento").first).to_be_visible()
            expect(simulador.get_by_test_id("simulador-hipotetico").first).to_be_visible()   # poucos médicos: a hipótese derivada

        def detector_de_volta():
            # De volta ao Detector, para a tela dos parâmetros (a ferramenta reabre com os padrões).
            area.get_by_test_id("analise-ferramenta-detector").click()
            detector = area.get_by_test_id("detector")
            expect(detector).to_have_attribute("data-estado", "pronto", timeout=180000)
            detector.get_by_test_id("detector-vista-lista").click()
            detector.get_by_test_id("detector-abrir").first.click()
            expect(detector.get_by_test_id("detector-detalhe")).to_be_visible(timeout=60000)

        def estados_como_unidade():
            if area.get_attribute("data-ferramenta"):
                area.get_by_test_id("analise-ferramenta-" + area.get_attribute("data-ferramenta")).click()
            area.get_by_test_id("analise-limpar-selecao").click()
            area.get_by_test_id("analise-aba-territorios").click()
            grafico(lambda: territorios.get_by_test_id("analise-raiz-so-estados").click(), lambda o: o.get("nivel") == "estados")
            area.get_by_test_id("analise-familia-distribuicao").click()
            expect(area.locator('[data-testid="analise-bolha"][data-tipo="estado"][data-visivel="true"]')).to_have_count(27, timeout=60000)

        def historico():
            page.get_by_test_id("nav-new-analysis").click()
            expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado", timeout=30000)
            page.get_by_test_id("nav-history").click()
            expect(page.get_by_test_id("historico-item").first).to_be_visible(timeout=30000)

        def nova_sessao():
            page.keyboard.press("Escape")
            page.get_by_test_id("nav-new-session").click()
            expect(page.get_by_test_id("new-session-confirmation")).to_be_visible()

        def colunas():
            page.get_by_test_id("cancel-new-session").click()
            planilha = Path(temporaria) / "distritos.csv"
            planilha.write_text("distrito;provincia;ano;categoria;quantidade;populacao;latitude;longitude\n"
                                "Alfa;Norte;2023;MEDICINA;10;1000;-10.1;-40.2\nBeta;Sul;2023;MEDICINA;20;2500;-12.0;-42.1\n"
                                "Alfa;Norte;2024;MEDICINA;11;1000;-10.1;-40.2\nBeta;Sul;2024;MEDICINA;22;2500;-12.0;-42.1\n",
                                encoding="utf-8")
            page.get_by_test_id("fonte-trocar").click()
            area.get_by_test_id("analise-troca-fonte").get_by_test_id("analise-fonte-arquivo").click()
            janela = page.get_by_test_id("envio-de-dados")
            expect(janela).to_be_visible()
            with page.expect_file_chooser() as escolha:
                janela.get_by_test_id("envio-escolher-arquivo").click()
            escolha.value.set_files(str(planilha))
            painel = page.get_by_test_id("colunas-painel")
            expect(painel).to_be_visible(timeout=60000)
            painel.get_by_test_id("colunas-territory").select_option("distrito")
            expect(painel.get_by_test_id("colunas-grupo_territorial").locator("option").nth(1)).to_have_text(
                "provincia (sugerida)", timeout=30000)
            painel.get_by_test_id("colunas-grupo_territorial").select_option("provincia")

        def celular():
            pequeno = browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce", has_touch=True, is_mobile=True)
            offline(pequeno)
            celular_page = pequeno.new_page()
            celular_page.on("pageerror", lambda erro: erros.append(str(erro)))
            celular_page.goto(url)
            accept_privacy(celular_page)
            chat = celular_page.get_by_test_id("painel-chat")
            if chat.count() and chat.get_attribute("data-minimizada") == "false":
                chat.get_by_test_id("painel-chat-minimizar").click()
            celular_page.get_by_test_id("analise-fonte-brasil").click()
            selecao = celular_page.get_by_test_id("analise-territorios")
            expect(selecao.get_by_test_id("analise-arvore")).to_be_visible(timeout=180000)
            abrir_regiao(selecao, "1")
            linha = selecao.locator('[data-testid="analise-grupo"][data-id="' + PA + '"]')
            with celular_page.expect_response(lambda r: is_post(r, "/api/painel"), timeout=180000):
                linha.get_by_test_id("analise-grupo-so-estado").click()
            celular_page.wait_for_timeout(900)
            celular_page.screenshot(path=str(saida / "15-celular-selecao.png"), full_page=True)
            pequeno.close()

        tela("01-abertura", abertura)
        tela("02-selecao-arvore", arvore)
        tela("03-selecao-regiao-norte", regiao_norte)
        tela("04-selecao-para-unidade-e-amazonas", selecao_mista)
        tela("05-distribuicao-dois-niveis", distribuicao_mista)
        tela("06-aplicar-criterios", criterios)
        tela("07-agrupar-escolha-livre", agrupar_livre)
        tela("08-agrupar-proximidade", agrupar_proximidade)
        tela("09-selecao-com-conjuntos", selecao_com_conjuntos)
        tela("10-dica-do-conjunto", dica_do_conjunto, manter_rolagem=True)
        tela("11-espacial-escolha-dos-territorios", espacial_escolha)
        tela("12-espacial-foco", espacial_foco)
        tela("16-detector-selecao-mista", detector_tabela, altura_maxima=ALTO_DO_DETECTOR)
        tela("17-detector-detalhe", detector_detalhe, altura_maxima=ALTO_DO_DETECTOR)
        tela("20-simulador-territorios", simulador_territorios)
        tela("21-simulador-intervencoes", simulador_intervencoes)
        tela("22-simulador-resultados", simulador_resultados)
        tela("23-simulador-base-e-metodo", simulador_base_e_metodo)
        tela("24-simulador-validacao", simulador_validacao)
        tela("13-estados-como-unidade", estados_como_unidade)
        tela("18-detector-brasil-alertas", detector_brasil, altura_maxima=ALTO_DO_DETECTOR)
        tela("25-detector-bolhas-distancia-e-taxa", detector_bolhas, altura_maxima=ALTO_DO_DETECTOR)
        tela("26-detector-mapa-dos-sinais", detector_mapa, altura_maxima=ALTO_DO_DETECTOR)
        tela("27-detector-taxa-e-fenomeno-8", detector_taxa, altura_maxima=ALTO_DO_DETECTOR)
        tela("28-detector-fenomeno-9-posicao", lambda: fenomeno("posicao"), altura_maxima=ALTO_DO_DETECTOR)
        tela("29-detector-fenomeno-10-defasagem", lambda: fenomeno("defasagem"), altura_maxima=ALTO_DO_DETECTOR)
        tela("30-detector-fenomeno-11-contexto", lambda: fenomeno("contexto"), altura_maxima=ALTO_DO_DETECTOR)
        tela("31-detector-fenomeno-12-sinais-combinados", detector_combinados, altura_maxima=ALTO_DO_DETECTOR)
        tela("32-abrir-no-simulador-e-referencias", abrir_no_simulador)
        tela("33-simulador-comparacoes", simulador_comparacoes)
        tela("34-simulador-brasil", simulador_brasil)
        tela("35-simulador-planejamento-inverso", simulador_planejamento)
        tela("36-simulador-planejamento-resultado", simulador_planejamento_resultado)
        tela("37-simulador-plano-como-intervencao", simulador_plano_como_intervencao)
        tela("38-simular-recuperacao-meta", simular_recuperacao)
        tela("39-simular-recuperacao-resultado", simular_recuperacao_resultado)
        detector_de_volta()
        tela("19-detector-parametros", detector_parametros, altura_maxima=ALTO_DO_DETECTOR)
        tela("14-historico", historico)
        tela("14b-nova-sessao", nova_sessao)
        tela("14c-planilha-colunas", colunas)
        try:
            celular()
            feitas.append("15-celular-selecao.png")
            print("   ok: 15-celular-selecao.png", flush=True)
        except Exception as erro:  # noqa: BLE001
            falhas.append(f"15-celular-selecao: {str(erro).splitlines()[0]}")
            print("   FALHOU:", falhas[-1], flush=True)
        browser.close()
    if erros:
        falhas.append("erros de JavaScript na página: " + "; ".join(erros[:3]))
    return feitas, falhas


def main():
    parser = argparse.ArgumentParser(description="Capturas das telas principais para a conferência visual.")
    parser.add_argument("--saida", type=Path, help="pasta das capturas (padrão: .local/capturas/<data-hora>)")
    parser.add_argument("--canal", choices=("chrome", "chromium"),
                        default=os.environ.get("ADT_BROWSER_CHANNEL") or "chrome", help="navegador (padrão: chrome)")
    args = parser.parse_args()
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8", errors="replace")  # saída redirecionada no Windows usaria cp1252
    if not DIST.exists():
        sys.exit("Build ausente: rode antes (cd frontend && npm run build).")
    if build_desatualizado():
        print("Aviso: há arquivos em frontend/src mais novos que o build; as capturas podem não refletir a última mudança.")
    saida = args.saida or ROOT / ".local" / "capturas" / datetime.now().strftime("%Y%m%d-%H%M%S")
    saida.mkdir(parents=True, exist_ok=True)
    porta = porta_livre()
    url = f"http://127.0.0.1:{porta}/"
    # Base versionada da raiz (versão governada): sem catálogo externo fixado.
    env = {chave: valor for chave, valor in os.environ.items() if chave not in ("ADT_BRASIL_DATA_DIR", "ADT_BRASIL_DATA_VERSION")}
    env.update({"ADT_UI_PORT": str(porta), "PYTHONUTF8": "1"})
    with open(saida / "servidor.log", "wb") as log:
        servidor = subprocess.Popen([sys.executable, str(ROOT / "backend" / "tests" / "serve_ui_offline.py")],
                                    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            if not aguardar(url):
                sys.exit("O servidor de testes não respondeu; veja " + str(saida / "servidor.log"))
            print(f"Capturas em {saida} (servidor em {url}, navegador {args.canal})", flush=True)
            feitas, falhas = capturar(url, saida, args.canal)
        finally:
            servidor.terminate()
            try:
                servidor.wait(timeout=15)
            except subprocess.TimeoutExpired:
                servidor.kill()
    print(f"\n{len(feitas)} captura(s) em {saida}")
    for falha in falhas:
        print("Falha:", falha)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
