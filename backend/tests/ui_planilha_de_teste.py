"""Os nomes da base nas duas ferramentas, com a planilha de teste (revisão final do comando V23, 15/11/2026).

A planilha de teste (`planilha_das_ferramentas.csv`: 20 distritos fictícios, registros de janeiro e de julho, de 2014 a 2023, sem
grupo de cima, sem população e sem coordenadas) é enviada com os trabalhadores "Enfermeiros". O roteiro percorre o Detector de
Sinais (a lista e o perfil, o "Entenda" da ferramenta, "Ajustar critérios", "Como foi calculado", o detalhe de um distrito com o
"Entenda" e a explicação completa de cada sinal e o histórico) e o Simulador de Cenários (o modo simples com os quatro testes e
os "Entenda", e as quatro etapas do modo avançado, com referências, dois cenários, uma intervenção, os resultados, as
estatísticas e a validação), guardando todos os textos à vista em cada parada (e os que os leitores de tela leem).

Confere que **nenhum texto traz "junho" nem "médicos"** — as palavras que a base do Brasil põe nesses lugares ("taxas de junho a
junho", "médicos acrescentados", "Com 22 médicos…") —, nem as outras palavras próprias da base do Brasil (município, UF, IBGE,
Brasil, estado), e que, nesses mesmos lugares, a tela diz os nomes da planilha: "julho" e "enfermeiros".

Servidor serve_ui_offline.py, sem o provedor de IA; a planilha é o arquivo de teste do repositório (somente leitura).
"""
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_planilha_ficticia import DO_BRASIL, TEXTOS
from ui_support import URL, accept_privacy, is_post, offline

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
PLANILHA = Path(__file__).resolve().parent / "planilha_das_ferramentas.csv"
# O que a base do Brasil diz e esta planilha não tem: o mês da série anual dela é julho, e os trabalhadores são enfermeiros.
DA_BASE_DO_BRASIL = re.compile(r"junho|\bjun/|m[ée]dic", re.IGNORECASE)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
        offline(context)
        page = context.new_page()
        falhas, chamadas_llm, vistos = [], [], {}
        page.on("pageerror", lambda erro: falhas.append(str(erro)))
        page.on("request", lambda pedido: chamadas_llm.append(pedido.url) if "/api/llm/interpret" in pedido.url else None)
        area = page.get_by_test_id("area-de-analise")
        detector, simulador = area.get_by_test_id("detector"), area.get_by_test_id("simulador")

        def guarda(nome):
            """Os textos à vista (e os atributos lidos por leitores de tela) nesta parada, para a varredura do fim."""
            page.wait_for_timeout(350)
            vistos[nome] = page.evaluate(TEXTOS)

        def aperta(testid, raiz=None):
            botao = (raiz or page).get_by_test_id(testid).first
            botao.scroll_into_view_if_needed()
            botao.click()

        def calcula(botao="simulador-calcular"):
            with page.expect_response(lambda r: is_post(r, "/api/simulador"), timeout=240000) as evento:
                aperta(botao, simulador)
            assert evento.value.status == 200, evento.value.text()[:2000]
            expect(simulador).to_have_attribute("data-estado", "pronto", timeout=240000)

        def minimiza_a_conversa():
            chat = page.get_by_test_id("painel-chat")
            if chat.count() and chat.get_by_test_id("painel-chat-minimizar").count() and chat.get_attribute("data-minimizada") != "true":
                chat.get_by_test_id("painel-chat-minimizar").click()

        # 1. A planilha de teste, enviada com os nomes dela: distritos, a Solária e "Enfermeiros".
        page.goto(URL)
        accept_privacy(page)
        minimiza_a_conversa()
        area.get_by_test_id("analise-fonte-arquivo").click()
        janela = page.get_by_test_id("envio-de-dados")
        expect(janela).to_be_visible()
        with page.expect_file_chooser() as escolha:
            janela.get_by_test_id("envio-escolher-arquivo").click()
        escolha.value.set_files(str(PLANILHA))
        colunas = page.get_by_test_id("colunas-painel")
        expect(colunas).to_be_visible(timeout=90000)
        for papel, coluna in (("territory", "distrito"), ("period", "periodo"), ("count", "profissionais")):
            colunas.get_by_test_id("colunas-" + papel).select_option(coluna)
        for campo, valor in (("unidade-singular", "distrito"), ("unidade-plural", "distritos")):
            colunas.get_by_test_id("colunas-" + campo).fill(valor)
        colunas.get_by_test_id("colunas-todo-nome").fill("Solária")
        colunas.get_by_test_id("colunas-todo-artigo").select_option("a")
        colunas.get_by_test_id("colunas-unidade-de-contagem").select_option("pessoas")
        # O exemplo do campo dos trabalhadores não traz uma palavra da base do Brasil (antes, "Por exemplo: médicos").
        expect(colunas.get_by_test_id("colunas-objeto")).to_have_attribute("placeholder", "Por exemplo: enfermeiros")
        colunas.get_by_test_id("colunas-objeto").fill("Enfermeiros")
        guarda("colunas")
        colunas.get_by_test_id("colunas-comecar").click()
        expect(colunas).to_have_count(0, timeout=90000)
        expect(area.get_by_test_id("analise-aba-territorios")).to_be_visible(timeout=90000)
        minimiza_a_conversa()
        area.get_by_test_id("analise-marcar-todos").click()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_contain_text("20", timeout=120000)
        guarda("seleção")

        # 2. O Detector: a lista, o perfil da base (aberto: é uma base nova), o "Entenda", os critérios e o método.
        with page.expect_response(lambda r: is_post(r, "/api/detector"), timeout=180000):
            area.get_by_test_id("analise-ferramenta-detector").click()
        expect(detector).to_have_attribute("data-estado", "pronto", timeout=240000)
        expect(area.get_by_test_id("perfil-da-base")).to_have_attribute("data-estado", "pronto", timeout=240000)
        expect(detector.get_by_test_id("detector-linha")).to_have_count(20)
        expect(detector.get_by_test_id("detector-data")).to_contain_text("Registro mais recente da base: jul/2023.")
        guarda("detector: lista e perfil")
        aperta("detector-entenda-ferramenta-botao", detector)
        expect(detector.get_by_test_id("detector-entenda-ferramenta-caixa")).to_contain_text("enfermeiros")
        guarda("detector: entenda da ferramenta")
        page.keyboard.press("Escape")
        aperta("detector-parametros-botao", detector)
        guarda("detector: ajustar critérios")
        aperta("detector-metodo-botao", detector)
        guarda("detector: como foi calculado")

        # 3. O detalhe de um distrito: cada sinal, com o "Entenda" e a explicação completa; e o histórico de sinais.
        detector.locator('[data-testid="detector-linha"][data-id="name:Distrito 13"]').get_by_test_id("detector-abrir").click()
        detalhe = detector.get_by_test_id("detector-detalhe")
        expect(detalhe).to_be_visible(timeout=120000)
        sinais = detalhe.get_by_test_id("detector-fenomeno")
        expect(sinais).to_have_count(11)
        expect(detalhe.locator('[data-testid="detector-fenomeno"][data-chave="estrutural"]')).to_contain_text("enfermeiros")
        guarda("detector: detalhe")
        for posicao in range(11):
            sinal = sinais.nth(posicao)
            chave = sinal.get_attribute("data-chave")
            sinal.get_by_test_id("detector-entenda-botao").scroll_into_view_if_needed()
            sinal.get_by_test_id("detector-entenda-botao").click()
            expect(sinal.get_by_test_id("detector-entenda-caixa")).to_be_visible()
            guarda("detector: entenda do sinal " + chave)
            sinal.get_by_test_id("detector-entenda-botao").click()
            sinal.get_by_test_id("detector-fenomeno-completa").click()
            guarda("detector: explicação completa do sinal " + chave)
            sinal.get_by_test_id("detector-fenomeno-completa").click()
        aperta("detector-historico-botao", detalhe)
        expect(detalhe.get_by_test_id("detector-historico")).to_be_visible()
        guarda("detector: histórico de sinais")

        # 4. O Simulador, no modo simples: antes de calcular, os "Entenda" e os quatro testes.
        detalhe.get_by_test_id("detector-abrir-no-simulador").click()
        expect(simulador.get_by_test_id("simulador-simples")).to_be_visible(timeout=60000)
        guarda("simulador: simples, antes de calcular")
        aperta("simulador-entenda-ferramenta-botao", simulador)
        # Onde a base do Brasil diz "Com 22 médicos no último registro…", a planilha diz os trabalhadores dela.
        expect(simulador.get_by_test_id("simulador-entenda-ferramenta-caixa")).to_contain_text("Com 22 enfermeiros no último registro")
        guarda("simulador: entenda geral")
        page.keyboard.press("Escape")
        calcula()
        expect(simulador.get_by_test_id("simulador-resultado")).to_be_visible()
        guarda("simulador: continuar como vinha")
        for chave in ("jeito", "faixa"):
            aperta("simulador-entenda-" + chave + "-botao", simulador)
            expect(simulador.get_by_test_id("simulador-entenda-" + chave + "-caixa")).to_be_visible()
            guarda("simulador: entenda do " + chave)
            page.keyboard.press("Escape")
        aperta("simulador-validacao-botao", simulador)
        guarda("simulador: como os métodos se saíram no passado")
        simulador.get_by_test_id("simulador-teste-acrescentar").check()
        simulador.get_by_test_id("simulador-teste-quantidade").fill("3")
        expect(simulador.get_by_test_id("simulador-frase-do-teste")).to_contain_text("enfermeiros")
        guarda("simulador: acrescentar, antes de calcular")
        calcula()
        guarda("simulador: acrescentar")
        simulador.get_by_test_id("simulador-teste-retirar").check()
        simulador.get_by_test_id("simulador-teste-quantidade").fill("2")
        calcula()
        guarda("simulador: retirar")
        simulador.get_by_test_id("simulador-teste-meta").check()
        simulador.get_by_test_id("simulador-teste-meta-valor").fill("40")
        calcula()
        expect(simulador.get_by_test_id("simulador-planejamento")).to_be_visible()
        guarda("simulador: chegar a uma meta")

        # 5. O modo avançado, etapa por etapa.
        simulador.get_by_test_id("simulador-modo-avancado").click()
        simulador.get_by_test_id("simulador-etapa-1").click()
        expect(simulador.get_by_test_id("simulador-territorios")).to_be_visible()
        simulador.get_by_test_id("simulador-busca").fill("distrito 1")
        guarda("simulador avançado: etapa 1, com a busca")
        simulador.get_by_test_id("simulador-busca").fill("")
        simulador.get_by_test_id("simulador-referencia-brasil").click()          # o todo da planilha: a Solária
        simulador.get_by_test_id("simulador-referencia-valor-nova").click()
        simulador.get_by_test_id("simulador-referencia-valor").fill("30")
        expect(simulador.get_by_test_id("simulador-frase-da-comparacao")).to_be_visible()
        guarda("simulador avançado: etapa 1, com referências")
        simulador.get_by_test_id("simulador-etapa-2").click()
        expect(simulador.get_by_test_id("simulador-frase-da-janela")).to_be_visible()
        simulador.get_by_test_id("simulador-cenario-novo").click()
        expect(simulador.get_by_test_id("simulador-cenario")).to_have_count(2)
        guarda("simulador avançado: etapa 2, com dois cenários")
        simulador.get_by_test_id("simulador-etapa-3").click()
        simulador.get_by_test_id("simulador-intervencao-nova").first.click()
        simulador.get_by_test_id("simulador-intervencao-quantidade").first.fill("2")
        # Onde a base do Brasil diz "Dos médicos acrescentados, a cada ano permanecem…".
        expect(simulador.get_by_test_id("simulador-frase-da-permanencia").first).to_contain_text("Dos enfermeiros acrescentados, a cada ano permanecem")
        guarda("simulador avançado: etapa 3, com uma intervenção")
        calcula()
        expect(simulador.get_by_test_id("simulador-resultados")).to_be_visible(timeout=240000)
        guarda("simulador avançado: etapa 4, os resultados")
        simulador.get_by_test_id("simulador-etapa-2").click()
        # Onde a base do Brasil diz "Taxas de junho a junho", a planilha diz o mês da série anual dela.
        expect(simulador.get_by_test_id("simulador-base")).to_contain_text("Taxas de julho a julho")
        guarda("simulador avançado: etapa 2, as estatísticas")
        simulador.get_by_test_id("simulador-etapa-4").click()
        aperta("simulador-validacao-botao", simulador)
        guarda("simulador avançado: a validação")
        page.screenshot(path=str(OUTPUT / "planilha-de-teste-01-avancado.png"), full_page=False)

        # 6. A varredura: em nenhuma das paradas há "junho" nem "médicos", nem as outras palavras próprias da base do Brasil; e os
        # nomes da planilha estão em todas elas.
        assert len(vistos) == 47, sorted(vistos)
        for nome, texto in vistos.items():
            achados = sorted({texto[max(0, m.start() - 60):m.end() + 40].replace("\n", " ") for m in DA_BASE_DO_BRASIL.finditer(texto)})
            assert not achados, (nome, achados[:5])
            if nome == "colunas":
                continue   # a tela de entrada ainda oferece "Usar dados do Brasil" e dá "município" como exemplo de unidade de uma linha
            do_brasil = sorted({texto[max(0, m.start() - 60):m.end() + 40].replace("\n", " ") for m in DO_BRASIL.finditer(texto)})
            assert not do_brasil, (nome, do_brasil[:5])
        fora_do_envio = {nome: texto for nome, texto in vistos.items() if nome != "colunas"}
        assert all("Solária" in texto for texto in fora_do_envio.values()), [nome for nome, texto in fora_do_envio.items() if "Solária" not in texto]
        das_ferramentas = {nome: texto for nome, texto in vistos.items() if nome.startswith(("detector", "simulador"))}
        assert all("enfermeiro" in texto for texto in das_ferramentas.values()), [nome for nome, texto in das_ferramentas.items()
                                                                                 if "enfermeiro" not in texto]
        assert any("de julho a julho" in texto for texto in das_ferramentas.values())
        assert not chamadas_llm, "as ferramentas calculam sem o provedor de IA"
        assert not falhas, falhas
        browser.close()
    print("PLANILHA DE TESTE PASS: com a planilha de julho e de enfermeiros, 47 paradas no Detector e no Simulador (modo simples, as "
          "quatro etapas do avançado e os \"Entenda\") sem \"junho\", \"médicos\" nem as outras palavras da base do Brasil; nos mesmos "
          "lugares, \"julho\" e \"enfermeiros\".")


if __name__ == "__main__":
    main()
