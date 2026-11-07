"""Confirmação de execução dos pedidos da conversa (05/11/2026), com a base Brasil versionada (somente leitura).

A conversa só diz que fez o que foi pedido ("Mostrei", "Ordenei") depois de a área de análise confirmar que o pedido está na
tela, com o cálculo do motor: o desfecho do pedido fica na mensagem do agente (`data-execucao`, `data-pedido` e
`data-resultado`, o resultado do motor guardado na sessão) e na área (`data-desfecho`, `data-pedido-da-conversa` e
`data-resultado`). Percorre os testes do pedido do responsável:
1. sem base, "Quero os cinco municípios do Acre com maior densidade médica": a base Brasil escolhida pelo pedido (sem o "sim"),
   os 22 municípios do Acre na área e a ordenação pela densidade, com os 5 primeiros, no painel Ordenar e nas bolhas;
2. com a base e sem territórios (Nova análise), "faça uma análise de Rondônia": os 52 municípios selecionados e a análise
   calculada;
3. a ordenação pedida na conversa (pela alternativa da direção) aparece no painel Ordenar e nas posições das bolhas;
4. operações ambíguas ("ordene pela densidade", "mostre São Paulo"): o esclarecimento em botões, sem mudar a área e sem pedir
   nada ao motor;
5. o motor lento (a resposta só sai com o cálculo; além do prazo da tela, o aviso de que a confirmação ainda não veio e, quando o
   cálculo chega, a mensagem de conclusão), o motor com falha, a recusa da área (a resposta do intérprete simulada dizendo
   "Ordenei…" com uma ordenação que a área não reconhece) e o pedido sem territórios: em nenhum caso a conversa anuncia
   execução inexistente;
6. as jornadas conversacionais de antes continuam nos outros roteiros (ui_conversa_grafico.py, ui_area_de_analise.py,
   ui_pagina_unica.py).
Servidor sem o provedor de IA: tudo pelos canais locais.
"""
import json
import os
import re
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import AREA, URL, accept_privacy, form_field, is_post, offline, open_chat, options_of, responder_uma_vez, send

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
ACRE, RONDONIA = "12", "11"
BOLHAS = '[data-testid="analise-bolha"][data-tipo="municipio"][data-visivel="true"]'
# O que a conversa só pode dizer com o desfecho "concluido" da área (desde 06/11/2026, também "Agreguei", de Agregar territórios).
AFIRMA_EXECUCAO = re.compile(r"\b(?:Mostrei|Ordenei|Selecionei|Atualizei|Apliquei|Abri|Comparei|Juntei|Agreguei|Destaquei|Troquei|"
                             r"Voltei|Desfiz)\b")
SEM_CONFIRMACAO = "O pedido foi enviado à área de análise, mas ainda não terminou."


def estados_do_pedido(request):
    return ((options_of(request).get("base") or {}).get("municipios") or {}).get("estados")


def liberar(retidas):
    """Solta os pedidos retidos ao motor, na ordem; um pedido que a página já cancelou não tem o que soltar."""
    for rota in retidas:
        try:
            rota.continue_()
        except Exception:  # noqa: BLE001 - o pedido cancelado pela página não pode seguir
            pass


def main():
    assert os.getenv("ADT_BLOCK1_REAL") == "1", "este roteiro usa a base Brasil versionada (suíte base-versionada)"
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        offline(context)
        page = context.new_page()
        falhas, contextuais, painel = [], [], []
        page.on("pageerror", lambda error: falhas.append(str(error)))
        page.on("request", lambda r: contextuais.append(r.url) if r.url.endswith("/api/llm/interpret-context") else None)
        page.on("request", lambda r: painel.append(r) if r.url.endswith("/api/painel") and r.method == "POST" else None)

        def shot(nome):
            page.wait_for_timeout(500)
            page.screenshot(path=str(OUTPUT / ("execucao-conversa-" + nome + ".png")), full_page=True)

        page.goto(URL)
        accept_privacy(page)
        area = page.get_by_test_id(AREA["raiz"])
        expect(area).to_be_visible()
        chat = open_chat(page)
        historico = chat.get_by_test_id("chat-historico")
        latest = chat.get_by_test_id("latest-reply")
        processando = chat.get_by_test_id("chat-processando")

        def do_agente():
            return historico.locator('[data-papel="agente"]')

        def enviar_sem_esperar(mensagem):
            open_chat(page).locator("#assistant-input").fill(mensagem)
            chat.get_by_role("button", name="Enviar mensagem", exact=True).click()

        def associada(mensagem):
            """A associação verificável: o resultado do motor da mensagem é o que a área mostra, e o pedido da mensagem é o último
            que a área confirmou."""
            resultado = mensagem.get_attribute("data-resultado") or ""
            assert resultado and resultado == area.get_attribute("data-resultado"), (resultado, area.get_attribute("data-resultado"))
            assert mensagem.get_attribute("data-pedido") == area.get_attribute("data-pedido-da-conversa"), (
                mensagem.get_attribute("data-pedido"), area.get_attribute("data-pedido-da-conversa"))

        def ordem_na_tela(resposta, limite):
            """O painel Ordenar e as bolhas mostram as posições do motor: a lista até o corte (com os empates) e cada bolha com a
            posição dela."""
            posicionados = [item for item in resposta["itens"] if (item.get("ordem") or {}).get("posicao") is not None]
            no_corte = [item for item in posicionados if limite is None or item["ordem"]["posicao"] <= limite]
            gaveta = area.get_by_test_id("analise-painel")
            expect(gaveta).to_have_attribute("data-painel", "ordenar", timeout=30000)
            lista = gaveta.get_by_test_id("analise-ordenar-lista").locator("li")
            expect(lista).to_have_count(len(no_corte) if limite is not None else min(20, len(posicionados)), timeout=30000)
            posicoes = [int(valor) for valor in lista.evaluate_all("els => els.map(e => e.dataset.posicao)")]
            assert posicoes == sorted(posicoes) and posicoes[0] == 1, posicoes
            primeiro = lista.first.get_attribute("data-id")
            assert any(item["id"] == primeiro and item["ordem"]["posicao"] == 1 for item in posicionados), primeiro
            bolhas = dict(area.locator(BOLHAS).evaluate_all("els => els.map(e => [e.dataset.id, e.dataset.posicao ?? null])"))
            for item in posicionados:
                if item["id"] in bolhas:
                    assert bolhas[item["id"]] == str(item["ordem"]["posicao"]), (item["id"], bolhas[item["id"]], item["ordem"])
            return gaveta

        # 1. Sem base: o pedido cita o Acre, e a base Brasil é escolhida pelo pedido, sem o "sim"; quando ela fica pronta, o pedido
        # guardado segue pela gramática local: os municípios do Acre e a ordenação pela densidade, com os 5 primeiros. A resposta
        # que diz o que foi feito só aparece com o desfecho "concluido" da área.
        pedido = "Quero os cinco municípios do Acre com maior densidade médica"
        with page.expect_response(lambda r: is_post(r, "/api/painel") and estados_do_pedido(r.request) == [ACRE],
                                  timeout=180000) as grafico:
            with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret") and
                                      form_field(r.request, "message") == pedido, timeout=180000) as interpretacao:
                with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=180000) as inspecao:
                    with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as escolha:
                        enviar_sem_esperar(pedido)
        corpo = escolha.value.json()
        assert corpo.get("aguarda_base") is True and corpo.get("fonte_escolhida") == "brasil", corpo
        assert "fonte_sugerida" not in corpo and not corpo.get("painel"), corpo
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        comando = interpretacao.value.json()
        assert comando.get("handled") is True and (comando.get("painel") or {}).get("ordenar") == {
            "atributo": "densidade", "ordem": "desc", "primeiros": 5}, comando
        enviado = options_of(grafico.value.request)
        assert enviado.get("ordenar") == {"atributo": "densidade", "ordem": "desc", "primeiros": 5}, enviado
        assert grafico.value.status == 200, grafico.value.text()[:2000]
        acre = grafico.value.json()
        assert len([item for item in acre["itens"] if item["tipo"] == "municipio"]) == 22, len(acre["itens"])
        expect(historico).to_contain_text("Para analisar o Acre, vou usar os dados do Brasil. Estou preparando os dados e, em "
                                          "seguida, sigo com o seu pedido.")
        expect(historico).not_to_contain_text("posso usar os dados do Brasil")
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=60000)
        confirmada = do_agente().last
        expect(confirmada).to_have_attribute("data-execucao", "concluido", timeout=60000)
        # O começo da frase depende de a área já ter informado o contexto ("Mostrei a densidade nos…" ou "Mostrei os valores nos…").
        expect(latest).to_contain_text("Com os dados prontos, sigo com o seu pedido. Mostrei ")
        expect(latest).to_contain_text(" nos 22 municípios do Acre. Ordenei os municípios pela densidade, do maior para o menor, e "
                                       "destaquei os 5 primeiros")
        expect(area).to_have_attribute("data-desfecho", "concluido")
        expect(area).to_have_attribute("data-nivel", "municipios")
        expect(area).to_have_attribute("data-familia", "distribuicao")
        expect(area).to_have_attribute("data-aba", "distribuicao")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_contain_text("Acre")
        associada(confirmada)
        gaveta = ordem_na_tela(acre, 5)
        expect(gaveta.get_by_test_id("analise-ordenar-atributo")).to_have_value("densidade")
        expect(gaveta.get_by_test_id("analise-ordenar-ordem")).to_have_value("desc")
        expect(gaveta.get_by_test_id("analise-ordenar-primeiros")).to_have_value("5")
        shot("01-acre-sem-base")

        # 4. Operações ambíguas: o esclarecimento em botões, sem mudar a área e sem pedir nada ao motor; nenhuma mensagem diz que
        # algo foi feito.
        chamadas, resultado = len(painel), area.get_attribute("data-resultado")
        alternativas = chat.get_by_role("group", name="Alternativas de esclarecimento")
        for ambigua, pergunta, alternativa in (
                ("ordene pela quantidade", "do maior para o menor ou do menor para o maior", "Do menor para o maior"),
                ("mostre São Paulo", "identifica um estado e também um município", "SAO PAULO (SP)")):
            with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
                send(page, ambigua)
            resposta = event.value.json()
            assert resposta.get("choices") and not resposta.get("painel"), resposta
            expect(latest).to_contain_text(pergunta)
            expect(alternativas.get_by_role("button", name=alternativa, exact=True)).to_be_visible()
            assert do_agente().last.get_attribute("data-execucao") is None
            assert not AFIRMA_EXECUCAO.search(latest.text_content() or ""), latest.text_content()
        page.wait_for_timeout(800)
        assert len(painel) == chamadas and area.get_attribute("data-resultado") == resultado, "a ambiguidade não muda a área"
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_contain_text("Acre")
        shot("02-ambiguidade")

        # 3. A ordenação pedida na conversa, pela alternativa da direção: o painel Ordenar e as bolhas com as posições do motor.
        send(page, "ordene pela quantidade")
        with page.expect_response(lambda r: is_post(r, "/api/painel") and (options_of(r.request).get("ordenar") or {}).get(
                "atributo") == "quantidade", timeout=120000) as grafico:
            alternativas.get_by_role("button", name="Do menor para o maior", exact=True).click()
        assert options_of(grafico.value.request)["ordenar"]["ordem"] == "asc", options_of(grafico.value.request)
        confirmada = do_agente().last
        expect(confirmada).to_have_attribute("data-execucao", "concluido", timeout=60000)
        expect(latest).to_contain_text("Ordenei")
        associada(confirmada)
        gaveta = ordem_na_tela(grafico.value.json(), (grafico.value.json().get("ordenacao") or {}).get("primeiros"))
        expect(gaveta.get_by_test_id("analise-ordenar-atributo")).to_have_value("quantidade")
        expect(gaveta.get_by_test_id("analise-ordenar-ordem")).to_have_value("asc")
        shot("03-ordenacao-pela-conversa")

        # 5a. O motor lento, dentro do prazo da tela: enquanto o cálculo não chega, a conversa mostra que está aplicando o pedido
        # e nenhuma resposta nova aparece; com o cálculo, a resposta e o desfecho "concluido". (Uma ordenação nova sempre vai ao
        # motor; a troca só do indicador, com a ordenação em uso, não pede nada novo e não serviria aqui.)
        retidas = []
        page.route("**/api/painel", lambda route: retidas.append(route))
        mensagens_antes = do_agente().count()
        enviar_sem_esperar("os 3 municípios com maior quantidade")
        for _ in range(150):
            if retidas:
                break
            page.wait_for_timeout(100)
        assert retidas, "o pedido ao motor não saiu"
        expect(processando).to_have_attribute("data-fase", "aplicando", timeout=30000)
        expect(processando).to_contain_text("Aplicando o pedido na área de análise")
        page.wait_for_timeout(2500)
        assert do_agente().count() == mensagens_antes, "sem o cálculo, nenhuma resposta nova"
        liberar(retidas)
        page.unroute("**/api/painel")
        confirmada = do_agente().nth(mensagens_antes)
        expect(confirmada).to_have_attribute("data-execucao", "concluido", timeout=60000)
        expect(confirmada).to_contain_text("Ordenei os municípios pela quantidade, do maior para o menor, e destaquei os 3 primeiros")
        expect(processando).to_have_count(0, timeout=30000)
        associada(confirmada)

        # 5b. O motor com falha: a resposta diz que o pedido não foi concluído, com o motivo, sem dizer que foi feito.
        falha = "Falha simulada do serviço de análise neste teste."
        responder_uma_vez(page, "**/api/painel", status=500, body=json.dumps({"detail": falha}), content_type="application/json")
        send(page, "os 3 municípios com menor densidade")
        expect(do_agente().last).to_have_attribute("data-execucao", "falhou", timeout=60000)
        expect(latest).to_contain_text("O pedido não foi concluído: " + falha + " O gráfico não foi atualizado.")
        assert not AFIRMA_EXECUCAO.search(latest.text_content() or ""), latest.text_content()
        expect(area).to_have_attribute("data-desfecho", "falhou")
        shot("04-falha-do-motor")

        # 5c. A recusa da área: o intérprete (simulado aqui) diz "Ordenei…", mas a área não reconhece a ordenação; a resposta diz
        # que o pedido não pôde ser aplicado, e nada é pedido ao motor.
        responder_uma_vez(page, "**/api/exploration/interpret", status=200, content_type="application/json", body=json.dumps({
            "handled": True, "executed": False, "reply": "Ordenei os municípios pela densidade, do maior para o menor.",
            "painel": {"ordenar": {"atributo": "inexistente", "ordem": "desc", "primeiros": None}}}))
        chamadas = len(painel)
        send(page, "ordene os municípios pela densidade, do maior para o menor")
        expect(do_agente().last).to_have_attribute("data-execucao", "recusado", timeout=60000)
        expect(latest).to_contain_text("O pedido não pôde ser aplicado: A ordenação pedida não foi reconhecida. Nada mudou na área de "
                                       "análise.")
        expect(latest).not_to_contain_text("Ordenei")
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "a recusa não pede nada ao motor"

        # 5d. O motor lento além do prazo da tela (20 s): a resposta diz que a confirmação ainda não veio, sem dizer que foi feito,
        # e a conversa volta a aceitar mensagens; quando o cálculo chega, uma mensagem nova diz que o pedido foi concluído.
        retidas = []
        page.route("**/api/painel", lambda route: retidas.append(route))
        mensagens_antes = do_agente().count()
        enviar_sem_esperar("os 10 municípios com maior população")
        provisoria = do_agente().nth(mensagens_antes)
        expect(provisoria).to_have_attribute("data-execucao", "aguardando", timeout=45000)
        expect(provisoria).to_contain_text(SEM_CONFIRMACAO)
        assert not AFIRMA_EXECUCAO.search(provisoria.text_content() or ""), provisoria.text_content()
        expect(chat.locator("#assistant-input")).to_be_enabled(timeout=10000)
        assert retidas, "o pedido ao motor saiu e ficou retido"
        liberar(retidas)
        page.unroute("**/api/painel")
        tardia = do_agente().nth(mensagens_antes + 1)
        expect(tardia).to_have_attribute("data-execucao", "concluido", timeout=60000)
        expect(tardia).to_contain_text("Pronto, o pedido anterior foi concluído. ")
        assert tardia.get_attribute("data-pedido") == provisoria.get_attribute("data-pedido"), "a mesma execução, confirmada depois"
        associada(tardia)
        shot("05-confirmacao-depois-do-prazo")

        # 2. Com a base e sem territórios (Nova análise): "faça uma análise de Rondônia" seleciona os 52 municípios e calcula a
        # análise; a resposta só com o desfecho "concluido".
        page.get_by_test_id("nav-new-analysis").click()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado", timeout=30000)
        expect(area).to_have_attribute("data-aba", "territorios")
        with page.expect_response(lambda r: is_post(r, "/api/painel") and estados_do_pedido(r.request) == [RONDONIA],
                                  timeout=120000) as grafico:
            send(page, "faça uma análise de Rondônia")
        assert grafico.value.status == 200, grafico.value.text()[:2000]
        rondonia = grafico.value.json()
        assert len([item for item in rondonia["itens"] if item["tipo"] == "municipio"]) == 52, len(rondonia["itens"])
        confirmada = do_agente().last
        expect(confirmada).to_have_attribute("data-execucao", "concluido", timeout=60000)
        expect(latest).to_contain_text("Mostrei ")
        expect(latest).to_contain_text(" nos 52 municípios de Rondônia.")
        expect(area).to_have_attribute("data-aba", "distribuicao")
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_contain_text("Rondônia")
        expect(area.locator(BOLHAS)).to_have_count(len([item for item in rondonia["itens"] if item["tipo"] == "municipio" and
                                                         item.get("densidade") is not None]), timeout=30000)
        associada(confirmada)
        shot("06-rondonia-sem-territorios")

        # 5e. O pedido sem territórios (o defeito relatado): com a base pronta e nada selecionado, a ordenação pedida não é dada
        # como feita; a resposta diz que faltam os territórios, e nada é pedido ao motor.
        page.get_by_test_id("nav-new-analysis").click()
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text("Nenhum território selecionado", timeout=30000)
        chamadas = len(painel)
        send(page, "ordene os municípios pela densidade, do maior para o menor")
        expect(do_agente().last).to_have_attribute("data-execucao", "pendente", timeout=60000)
        expect(latest).to_contain_text("O pedido não foi concluído: ainda não há territórios escolhidos, e nada foi calculado.")
        expect(latest).not_to_contain_text("Ordenei")
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "sem territórios, nada é pedido ao motor"
        expect(area).to_have_attribute("data-desfecho", "pendente")
        shot("07-sem-territorios")

        assert not contextuais, "tudo pelos canais locais: " + str(contextuais)
        assert not falhas, falhas
        browser.close()
    print("EXECUÇÃO PELA CONVERSA PASS: base Brasil escolhida pelo pedido com o Acre e os 5 primeiros na tela, Rondônia sem "
          "territórios selecionada e calculada, ordenação pela conversa no painel Ordenar e nas bolhas, ambiguidades em botões "
          "sem mudar a área, motor lento (antes e depois do prazo), falha do motor, recusa da área e pedido sem territórios sem "
          "anunciar execução inexistente, com a associação entre a mensagem e o resultado da área.")


if __name__ == "__main__":
    main()
