"""Conversa agindo no gráfico da página única (22/10/2026), pela caixa da conversa, sempre na página.

Percorre:
- perguntas antes dos dados, respondidas sem o provedor de IA (inclusive a descrição dos dados do Brasil);
- a escolha da base pela conversa ("usar dados do Brasil"), sem o provedor;
- comandos que mudam o gráfico: o campo `painel` da resposta do intérprete local vira um pedido para a área, que pede ao
  motor (/api/painel) o novo recorte: "Mostre o Amazonas", "Compare Manaus e Tefé" e "Volte aos estados";
- o contexto que vai ao intérprete saindo do gráfico: os municípios na tela, a família, o indicador e a competência;
- um esclarecimento pendente ("Compare Manaus" → "Com qual outro município?"), guardado para a mensagem seguinte;
- pedidos de apresentação (tabela, mapa) e "volte ao resultado anterior", que reabre a análise anterior do Histórico, sem
  recalcular;
- uma planilha enviada pela conversa ("enviar meus dados"), com condados e sem grupo: a orientação usa o nome das unidades,
  nunca "município", e "Compare Alfa e Beta" muda o gráfico da planilha.
Nada é calculado pela conversa.

Dois modos, pela suíte (run_ui_checks.py):
- "conversa" (servidor offline, sem transporte de IA): só os canais locais; o pedido que dependeria do provedor antes dos
  dados recebe a resposta local ou o aviso de indisponibilidade, e a página continua funcionando;
- "gemini-simulado" (ADT_FAKE_GEMINI_LOG definido): também o pedido feito antes dos dados, guardado e interpretado de novo
  quando a base fica pronta; a proposta fora do contrato, recusada com o aviso, e a recuperação na mensagem seguinte; a
  ambiguidade material com alternativas em botões (CATALOGO_LOCAL), cuja escolha muda o indicador do gráfico; e a
  conferência de que nada da base chega ao provedor simulado, com os exemplos da biblioteca conversacional mascarados.
Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; quatro competências). Nunca chama o provedor real.
"""
import json
import os
import re
import tempfile
from contextlib import nullcontext
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import (AREA, URL, accept_privacy, form_field, history_label, is_post, offline, open_chat, options_of, send,
                        uploaded_filename)

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, TEFE, PARINTINS = "code:130260", "code:130420", "code:130340"
AMAZONAS = sorted([MANAUS, TEFE, PARINTINS])
SEM_MUNICIPIO = re.compile("munic", re.IGNORECASE)
# Nada disto pode chegar ao provedor: arquivos, colunas, códigos e as chaves do contexto do gráfico.
PROTEGIDOS = ("Dados_Municipios_Brasil.csv", "Dados_Brasil.xlsx", "Dados_Estados_Brasil.csv", "cod_ibge", "população_estimada",
              "130260", "130420", "130340", "code:", "condados.csv", "territory_ids", "painel_familia")


def provider_log():
    caminho = os.getenv("ADT_FAKE_GEMINI_LOG")
    return Path(caminho).read_text(encoding="utf-8") if caminho and Path(caminho).exists() else ""


def main():
    simulado = bool(os.getenv("ADT_FAKE_GEMINI_LOG"))
    OUTPUT.mkdir(parents=True, exist_ok=True)
    suffix = "-simulado" if simulado else ""
    with tempfile.TemporaryDirectory(prefix="adt-conversa-grafico-") as temporaria, sync_playwright() as p:
        pasta = Path(temporaria)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        failures, llm_calls, analyze_calls, exploracoes, painel = [], [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: analyze_calls.append(request.url) if request.url.endswith("/api/analyze") else None)
        page.on("request", lambda request: exploracoes.append(request) if request.url.endswith("/api/exploration/interpret") else None)
        page.on("request", lambda request: painel.append(request) if request.url.endswith("/api/painel") else None)

        def shot(name):
            page.wait_for_timeout(600)
            page.screenshot(path=str(OUTPUT / ("conversa-grafico-" + name + suffix + ".png")), full_page=True)

        def chat_to_chart(message, pedido_do_grafico, timeout=120000):
            """Mensagem que muda o gráfico: a resposta do intérprete local traz o campo `painel`, e a área pede ao motor o
            recorte correspondente (o pedido de /api/painel que satisfaz pedido_do_grafico)."""
            with page.expect_response(lambda r: is_post(r, "/api/painel") and pedido_do_grafico(options_of(r.request)),
                                      timeout=timeout) as grafico:
                with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=timeout) as conversa:
                    send(page, message)
            assert conversa.value.status == 200, conversa.value.text()[:2000]
            resposta = conversa.value.json()
            assert resposta.get("handled") is True and resposta.get("painel"), resposta
            return resposta, options_of(conversa.value.request), conversa.value.request, options_of(grafico.value.request)

        page.goto(URL)
        accept_privacy(page)
        expect(page.get_by_test_id(AREA["raiz"])).to_be_visible()
        chat = open_chat(page)
        guia = chat.get_by_test_id("painel-chat-guia")
        latest = chat.get_by_test_id("latest-reply")
        expect(guia).to_contain_text("O que você quer analisar?")

        # 1. Antes dos dados: perguntas respondidas pelo catálogo local, sem o provedor de IA.
        antes = provider_log()
        for pergunta, trecho in (("Como se calcula a densidade?", "D(u, p, c) = Q(u, p, c) / P(u, p′)"),
                                 ("Muito obrigada pela ajuda!", "De nada")):
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
                send(page, pergunta)
            assert event.value.status == 200, event.value.text()[:2000]
            expect(latest).to_contain_text(trecho)
        with page.expect_response(lambda r: r.url.endswith("/api/brazil/description"), timeout=60000) as event:
            send(page, "O que tem nos dados do Brasil?")
        assert event.value.status == 200, event.value.text()[:2000]
        expect(latest).to_contain_text("Os dados do Brasil disponíveis nesta plataforma")
        expect(page.get_by_test_id("current-source")).to_have_count(0)  # a descrição não escolhe a fonte
        assert provider_log() == antes, "as respostas locais não chamam o provedor"

        # 2. Pedido antes dos dados. Com o provedor simulado, ele fica guardado até a base ficar pronta; sem provedor, a
        # conversa responde localmente ou avisa da indisponibilidade, e a página continua funcionando.
        with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
            send(page, "Quero analisar a densidade")
        guardado = event.value.status == 200
        if simulado:
            assert guardado, event.value.text()[:2000]
        else:
            assert event.value.status in (200, 503), event.value.text()[:2000]
        if guardado:
            expect(latest).to_contain_text("Para começar, prefere usar os dados do Brasil ou enviar os seus?")
            send(page, "certo, quantos tem?")
            expect(latest).to_contain_text("Para continuar, escolha os dados")
        else:
            expect(chat.get_by_role("alert")).to_contain_text("Gemini não configurado")

        # 3. A base escolhida pela conversa, como pelo botão, sem o provedor: os estados (E1). O pedido guardado é interpretado
        # de novo pelo intérprete local, já com a base.
        chamadas_llm = len(llm_calls)
        reinterpretacao = page.expect_request(lambda r: r.url.endswith("/api/exploration/interpret") and
                                              form_field(r, "message") == "Quero analisar a densidade",
                                              timeout=180000) if guardado else nullcontext()
        with reinterpretacao:
            with page.expect_response(lambda r: is_post(r, "/api/painel"), timeout=180000) as primeiro:
                with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=180000) as inspecao:
                    send(page, "usar dados do Brasil")
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        assert options_of(primeiro.value.request).get("nivel") == "estados", options_of(primeiro.value.request)
        assert len(llm_calls) == chamadas_llm, "a escolha da fonte pela conversa é local"
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil")
        expect(guia).to_contain_text("Escolha no gráfico quais estados abrir, ou me diga quais municípios quer ver.")
        page.wait_for_timeout(1000)  # a área informa o contexto do gráfico (E1)

        # 4. "Mostre o Amazonas": o campo painel vira um pedido, e a área pede ao motor os municípios do estado. O contexto
        # da mensagem é o do gráfico: nos estados, nenhum município na tela.
        resposta, conversa, _, grafico = chat_to_chart(
            "Mostre o Amazonas", lambda o: o.get("base", {}).get("municipios", {}).get("estados") == ["13"])
        assert (resposta["painel"].get("municipios") or {}).get("estados") == ["13"], resposta["painel"]
        assert conversa.get("painel_familia") == "distribuicao" and conversa.get("exploration_operation") == "density", conversa
        assert "territory_ids" not in conversa, conversa
        assert conversa.get("period_filter") == "202406", conversa
        assert grafico.get("nivel") == "municipios", grafico
        page.wait_for_timeout(1000)
        shot("01-amazonas")

        # 5. "Compare Manaus e Tefé": o contexto leva os municípios na tela; a comparação (maior, menor, diferença) vem do motor.
        resposta, conversa, _, grafico = chat_to_chart("Compare Manaus e Tefé", lambda o: bool(o.get("comparar")))
        assert sorted(conversa.get("territory_ids", [])) == AMAZONAS, conversa
        assert resposta["painel"].get("funcao") == "comparar", resposta["painel"]
        assert set(resposta["painel"].get("selecao") or []) == {MANAUS, TEFE}, resposta["painel"]
        assert set(grafico["comparar"]) == {MANAUS, TEFE}, grafico
        page.wait_for_timeout(1000)
        shot("02-comparacao")

        # 6. Esclarecimento: a conversa pergunta o outro município e guarda a pendência para a mensagem seguinte.
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Compare Manaus")
        assert event.value.json().get("pending_operation") == "comparisons", event.value.json()
        expect(latest).to_contain_text("Com qual outro município")
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Tefé e Parintins")
        assert options_of(event.value.request).get("conversation_pending_operation") == "comparisons", options_of(event.value.request)
        page.wait_for_timeout(1500)

        # 7. Gemini simulado: ambiguidade material com alternativas em botões; a escolha muda o indicador do gráfico, e a
        # mensagem seguinte leva o novo indicador no contexto.
        indicador = "density"
        if simulado:
            # Uma proposta do provedor fora do contrato é recusada (502) com o aviso, nada muda no gráfico, e a mensagem
            # seguinte funciona.
            chamadas = len(painel)
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "Mostre algo invalido")
            assert event.value.status == 502, event.value.text()[:2000]
            assert "fake-offline-key" not in event.value.text()
            expect(chat.get_by_role("alert")).to_contain_text("fora do contrato")
            assert len(painel) == chamadas
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "Analise o perfil dos municipios")
            assert event.value.status == 200, event.value.text()[:2000]
            expect(chat.get_by_role("alert")).to_have_count(0)
            assert event.value.json()["clarification"]["code"] == "AMBIGUIDADE_MATERIAL", event.value.json()
            alternativas = chat.get_by_role("group", name="Alternativas de esclarecimento")
            botao = alternativas.get_by_role("button", name="Quantitativos · Quantidade absoluta de profissionais", exact=True)
            expect(botao).to_be_visible()
            with page.expect_request(lambda r: r.url.endswith("/api/exploration/interpret"), timeout=60000) as escolha:
                botao.click()
            assert options_of(escolha.value).get("conversation_operation_choice") == "counts", options_of(escolha.value)
            expect(chat.get_by_role("group", name="Alternativas de esclarecimento")).to_have_count(0, timeout=60000)
            page.wait_for_timeout(1000)
            indicador = "quantity"

        # 8. "Volte aos estados": de volta à porta de entrada, com o indicador do gráfico no contexto.
        resposta, conversa, _, _ = chat_to_chart("Volte aos estados", lambda o: o.get("nivel") == "estados")
        assert resposta["painel"].get("nivel") == "estados", resposta["painel"]
        assert conversa.get("exploration_indicator") == indicador, conversa
        page.wait_for_timeout(1000)

        # 9. Pedidos de apresentação: respondidos na tela, sem recalcular nem chamar o intérprete.
        chamadas, interpretacoes = len(painel), len(exploracoes) + len(llm_calls)
        send(page, "agora a tabela")
        expect(latest).to_contain_text("A tabela fica em Detalhes")
        send(page, "Quero ver no mapa.")
        expect(latest).to_contain_text("o mapa não faz parte dela")
        send(page, "Volte para o resultado anterior")
        expect(latest).to_contain_text("Ainda não há análise anterior nesta sessão")
        assert len(painel) == chamadas and len(exploracoes) + len(llm_calls) == interpretacoes

        # 10. Nova análise e "volte ao resultado anterior": a conversa reabre a análise anterior do Histórico, sem recalcular.
        with page.expect_response(lambda r: is_post(r, "/api/painel") and options_of(r.request).get("nivel") == "estados",
                                  timeout=180000):
            page.get_by_test_id("nav-new-analysis").click()
        expect(page.get_by_test_id("nav-history")).to_contain_text(history_label(2), timeout=30000)
        page.wait_for_timeout(800)
        chamadas = len(painel)
        send(page, "Volte para o resultado anterior")
        expect(latest).to_contain_text("Reabri a análise anterior, sem recalcular")
        page.wait_for_timeout(1500)
        assert len(painel) == chamadas, "reabrir a análise anterior não recalcula"

        # 11. Planilha pela conversa: "enviar meus dados" abre a escolha do arquivo; a orientação usa o nome das unidades
        # (condados), nunca "município"; e a conversa muda o gráfico da planilha.
        caminho = pasta / "condados.csv"
        caminho.write_text("condado;ano;quantidade;populacao\nAlfa;2023;10;1000\nBeta;2023;20;4000\nGama;2023;5;2500\n"
                           "Alfa;2024;12;1000\nBeta;2024;22;4100\nGama;2024;6;2500\n", encoding="utf-8")
        with page.expect_file_chooser() as escolha:
            send(page, "enviar meus dados")
        expect(latest).to_contain_text("confira as colunas no painel Colunas")
        with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=60000) as inspecao:
            escolha.value.set_files(str(caminho))
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        colunas = page.get_by_test_id("colunas-painel")
        expect(colunas).to_be_visible()
        unidade = colunas.get_by_test_id("colunas-territory")
        expect(unidade).to_have_value("")  # "condado" não é nome conhecido: a pessoa escolhe
        unidade.select_option("condado")
        expect(colunas.get_by_test_id("colunas-unidade-plural")).to_have_value("condados")
        colunas.get_by_test_id("colunas-unidade-de-contagem").select_option("pessoas")
        # Sem coluna de categoria, a pessoa diz quem são os trabalhadores contados (o objeto da análise).
        colunas.get_by_test_id("colunas-objeto").fill("médicos")
        with page.expect_response(lambda r: is_post(r, "/api/painel") and uploaded_filename(r.request) == "condados.csv",
                                  timeout=120000) as primeiro:
            colunas.get_by_test_id("colunas-comecar").click()
        assert primeiro.value.status == 200, primeiro.value.text()[:2000]
        expect(page.get_by_test_id("current-source")).to_contain_text("condados.csv · condados")
        expect(guia).to_contain_text("condados")
        expect(guia).not_to_contain_text(SEM_MUNICIPIO)
        page.wait_for_timeout(1000)
        resposta, _, pedido, grafico = chat_to_chart("Compare Alfa e Beta", lambda o: bool(o.get("comparar")))
        assert uploaded_filename(pedido) == "condados.csv", uploaded_filename(pedido)
        assert json.loads(form_field(pedido, "mapping")).get("territory") == "condado", form_field(pedido, "mapping")
        assert set(resposta["painel"].get("selecao") or []) == {"name:Alfa", "name:Beta"}, resposta["painel"]
        assert set(grafico["comparar"]) == {"name:Alfa", "name:Beta"}, grafico
        shot("03-planilha")

        # 12. Nada da base chega ao provedor simulado: nem arquivos, colunas e códigos, nem o contexto do gráfico.
        if simulado:
            registros = [json.loads(linha) for linha in provider_log().splitlines() if linha.strip()]
            assert len(registros) >= 3, registros
            payload = provider_log()
            for protegido in PROTEGIDOS:
                assert protegido not in payload, protegido
            # Exemplos da biblioteca conversacional acompanham os pedidos, mascarados como as mensagens.
            exemplos = [registro["exemplos"] for registro in registros if registro.get("exemplos")]
            assert exemplos and all(bloco.startswith("EXEMPLOS_DA_BIBLIOTECA_CONVERSACIONAL") for bloco in exemplos), registros
        assert not analyze_calls, "a conversa não aciona as telas clássicas de /api/analyze"
        assert not failures, failures
        browser.close()
    print("CONVERSA NO GRÁFICO PASS: perguntas locais, fonte pela conversa, Amazonas, comparação, esclarecimento, estados, "
          "apresentação, análise anterior e planilha de condados" + (", ambiguidade e minimização (Gemini simulado)."
                                                                      if simulado else " (sem provedor)."))


if __name__ == "__main__":
    main()
