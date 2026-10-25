"""Conversa agindo no gráfico da página única (22/10/2026), pela caixa da conversa, sempre na página.

Percorre:
- perguntas antes dos dados, respondidas sem o provedor de IA (inclusive a descrição dos dados do Brasil);
- a escolha da base pela conversa ("usar dados do Brasil"), sem o provedor e sem seleção automática (23/10/2026): nada é
  pedido ao motor até a escolha dos territórios, e a conversa orienta a escolher na Seleção de Territórios ou pela conversa;
- comandos que mudam o gráfico: o campo `painel` da resposta do intérprete local vira um pedido para a área, que pede ao
  motor (/api/painel) o novo recorte: "todos os estados", "Mostre o Amazonas", "Compare Manaus e Tefé" e "Volte aos estados";
- a vista do desenho pela conversa (23/10/2026), na tela e sem o intérprete: com os municípios na tela, "ver no mapa" troca
  o gráfico pelo mapa (`area-de-analise` com data-desenho="mapa") e "volte ao gráfico" desfaz; "o que esse gráfico mostra?"
  responde com a frase-resumo do motor (`analise-resumo`), como veio;
- o contexto que vai ao intérprete saindo do gráfico: os municípios na tela, a família, o indicador, a competência, a vista
  e a frase-resumo (esta nunca chega ao provedor);
- um esclarecimento pendente ("Compare Manaus" → "Com qual outro município?"), guardado para a mensagem seguinte;
- pedidos de apresentação nos estados (tabela; mapa, que os estados não têm: a resposta é o motivo da área, e a vista
  continua o gráfico) e "volte ao resultado anterior", que reabre a análise anterior do Histórico, sem recalcular (a Nova
  análise recomeça sem territórios, sem pedir nada ao motor);
- uma planilha enviada pela conversa ("enviar meus dados", que abre a mesma janela de envio da área central, com o modelo de
  planilha), com condados e sem grupo: abre sem territórios escolhidos; a orientação usa o nome das unidades, nunca
  "município"; e "Compare Alfa e Beta" muda o gráfico da planilha.
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
              "130260", "130420", "130340", "code:", "condados.csv", "territory_ids", "painel_familia", "painel_vista",
              "painel_resumo", "painel_mapa_disponivel")


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
        failures, llm_calls, analyze_calls, exploracoes, painel, contextuais = [], [], [], [], [], []
        page.on("pageerror", lambda error: failures.append(str(error)))
        page.on("request", lambda request: llm_calls.append(request.url) if "/api/llm/interpret" in request.url else None)
        page.on("request", lambda request: contextuais.append(request)
                if request.url.endswith("/api/llm/interpret-context") else None)
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
        area = page.get_by_test_id(AREA["raiz"])
        expect(area).to_be_visible()
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

        # 3. A base escolhida pela conversa, como pelo botão, sem o provedor e sem seleção automática: nada é pedido ao motor
        # até a escolha dos territórios, e a conversa orienta a escolher. O pedido guardado é interpretado de novo pelo
        # intérprete local, já com a base. Depois, "todos os estados", o exemplo da orientação, põe os estados no gráfico (E1).
        chamadas_llm, chamadas_painel = len(llm_calls), len(painel)
        reinterpretacao = page.expect_request(lambda r: r.url.endswith("/api/exploration/interpret") and
                                              form_field(r, "message") == "Quero analisar a densidade",
                                              timeout=180000) if guardado else nullcontext()
        with reinterpretacao:
            with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=180000) as inspecao:
                send(page, "usar dados do Brasil")
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        assert len(llm_calls) == chamadas_llm, "a escolha da fonte pela conversa é local"
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil")
        expect(guia).to_contain_text("Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais "
                                     "quer ver, por exemplo “mostre o Pará” ou “todos os estados”.", timeout=60000)
        expect(area).to_have_attribute("data-aba", "territorios")
        page.wait_for_timeout(1000)  # a área informa o contexto do gráfico (sem territórios)
        if not guardado:
            assert len(painel) == chamadas_painel, "sem territórios escolhidos, nada é pedido ao motor"
        resposta, _, _, grafico = chat_to_chart("todos os estados", lambda o: o.get("nivel") == "estados")
        assert resposta["painel"].get("nivel") == "estados", resposta["painel"]
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

        # 5. A vista do desenho pela conversa (o mapa como segunda vista do gráfico, 23/10/2026), na tela e sem o intérprete:
        # com os municípios na tela, "ver no mapa" troca o gráfico pelo mapa, e "volte ao gráfico" desfaz; "o que esse gráfico
        # mostra?" responde com a frase-resumo do motor (analise-resumo), como veio.
        interpretacoes = len(exploracoes) + len(llm_calls)
        expect(area).to_have_attribute("data-desenho", "grafico")
        send(page, "ver no mapa")
        expect(latest).to_contain_text("Mostrei o mapa no lugar do gráfico")
        expect(area).to_have_attribute("data-desenho", "mapa", timeout=60000)
        shot("01b-mapa")
        send(page, "volte ao gráfico")
        expect(latest).to_contain_text("Voltei ao gráfico")
        expect(area).to_have_attribute("data-desenho", "grafico", timeout=60000)
        resumo = page.get_by_test_id("analise-resumo").first
        expect(resumo).to_have_text(re.compile(r"\S"), timeout=60000)
        frase = " ".join((resumo.text_content() or "").split())
        send(page, "O que esse gráfico mostra?")
        expect(latest).to_contain_text(frase)
        assert len(exploracoes) + len(llm_calls) == interpretacoes, "a vista e o resumo são respondidos na tela"

        # 6. "Compare Manaus e Tefé": o contexto leva os municípios na tela, a vista e a frase-resumo; a comparação (maior,
        # menor, diferença) vem do motor.
        resposta, conversa, _, grafico = chat_to_chart("Compare Manaus e Tefé", lambda o: bool(o.get("comparar")))
        assert sorted(conversa.get("territory_ids", [])) == AMAZONAS, conversa
        assert conversa.get("painel_vista") == "grafico" and conversa.get("painel_mapa_disponivel", True) is True, conversa
        assert frase in " ".join(str(conversa.get("painel_resumo") or "").split()), conversa
        assert resposta["painel"].get("funcao") == "comparar", resposta["painel"]
        assert set(resposta["painel"].get("selecao") or []) == {MANAUS, TEFE}, resposta["painel"]
        assert set(grafico["comparar"]) == {MANAUS, TEFE}, grafico
        page.wait_for_timeout(1000)
        shot("02-comparacao")

        # 7. Esclarecimento: a conversa pergunta o outro município e guarda a pendência para a mensagem seguinte.
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Compare Manaus")
        assert event.value.json().get("pending_operation") == "comparisons", event.value.json()
        expect(latest).to_contain_text("Com qual outro município")
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Tefé e Parintins")
        assert options_of(event.value.request).get("conversation_pending_operation") == "comparisons", options_of(event.value.request)
        page.wait_for_timeout(1500)

        # 7b. Território de referência pela conversa (decisão 4, 25/10/2026): o "menor" do pedido vira o operador da condição, com o
        # atributo citado; a relação, a delimitação e o valor de corte ficam com a pessoa, sem valor sugerido. O Desfazer do alto
        # (o "Voltar" até 25/10/2026) desfaz o pedido da conversa e devolve a análise de antes, para os passos seguintes.
        familia_antes = area.get_attribute("data-familia")
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "use como referência o município de menor densidade")
        resposta = event.value.json()
        assert (resposta.get("painel") or {}).get("referencia") == {
            "membros": [], "criterio": {"atributo": "densidade", "ordem": "asc"}}, resposta
        expect(latest).to_contain_text("com a condição Densidade “Menor que”")
        referencia = area.get_by_test_id("analise-referencia")
        expect(referencia).to_be_visible(timeout=60000)
        expect(referencia.get_by_test_id("analise-ref-da-conversa")).to_contain_text("pela menor densidade")
        expect(referencia.get_by_test_id("analise-ref-atributo")).to_have_value("densidade")
        expect(referencia.get_by_test_id("analise-ref-operador-menor")).to_have_attribute("aria-checked", "true")
        expect(referencia.get_by_test_id("analise-ref-operador-maior")).to_have_attribute("aria-checked", "false")
        expect(referencia.get_by_test_id("analise-ref-relacao-mais_proxima")).to_have_attribute("aria-checked", "false")
        expect(referencia.get_by_test_id("analise-ref-valor")).to_have_value("")
        expect(referencia.get_by_test_id("analise-ref-falta")).to_have_text(
            "Falta escolher: a relação espacial, a delimitação, o valor de corte.")
        shot("02b-referencia-pela-conversa")
        page.get_by_test_id("analise-desfazer").click()
        expect(area).to_have_attribute("data-familia", familia_antes, timeout=60000)
        page.wait_for_timeout(1500)

        # 8. Gemini simulado: ambiguidade material com alternativas em botões; a escolha muda o indicador do gráfico, e a
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

        # 9. "Volte aos estados": de volta à porta de entrada, com o indicador do gráfico no contexto. Os estados (todos) já foram
        # calculados no passo 3: a resposta vem da memória da tela, sem novo pedido ao motor; a comparação dos municípios não vai
        # junto (ela só vale para os itens que continuam na análise, 24/10/2026).
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=120000) as conversa_estados:
            send(page, "Volte aos estados")
        assert conversa_estados.value.status == 200, conversa_estados.value.text()[:2000]
        resposta, conversa = conversa_estados.value.json(), options_of(conversa_estados.value.request)
        assert resposta.get("handled") is True and resposta["painel"].get("nivel") == "estados", resposta
        assert conversa.get("exploration_indicator") == indicador, conversa
        expect(area).to_have_attribute("data-nivel", "estados")
        expect(page.locator('[data-testid="analise-bolha"][data-tipo="estado"][data-visivel="true"]').first).to_be_attached(timeout=60000)
        assert not any(options_of(pedido).get("nivel") == "estados" and options_of(pedido).get("comparar") for pedido in painel
                       if pedido.method == "POST"), "a comparação dos municípios não vai ao pedido dos estados"
        page.wait_for_timeout(1000)

        # 10. Pedidos de apresentação: respondidos na tela, sem recalcular nem chamar o intérprete. Nos estados, o mapa não
        # está disponível (os estados não têm um ponto): a resposta é o motivo informado pela área, e a vista continua o
        # gráfico.
        chamadas, interpretacoes = len(painel), len(exploracoes) + len(llm_calls)
        send(page, "agora a tabela")
        expect(latest).to_contain_text("A tabela fica em Detalhes")
        send(page, "Quero ver no mapa.")
        expect(latest).to_contain_text("Nada mudou no gráfico")
        expect(latest).not_to_contain_text("Mostrei o mapa")
        expect(area).to_have_attribute("data-desenho", "grafico")
        motivo = page.get_by_test_id("analise-desenho-motivo")
        if motivo.count() == 1 and motivo.is_visible():
            expect(latest).to_contain_text(" ".join((motivo.text_content() or "").split()))
        send(page, "Volte para o resultado anterior")
        expect(latest).to_contain_text("Ainda não há análise anterior nesta sessão")
        assert len(painel) == chamadas and len(exploracoes) + len(llm_calls) == interpretacoes

        # 11. Nova análise (sem territórios, sem pedir nada ao motor) e "volte ao resultado anterior": a conversa reabre a
        # análise anterior do Histórico, sem recalcular.
        chamadas = len(painel)
        page.get_by_test_id("nav-new-analysis").click()
        expect(guia).to_contain_text("Os dados estão prontos. Escolha os territórios", timeout=30000)
        expect(page.get_by_test_id("nav-history")).to_contain_text(history_label(1), timeout=30000)
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "a nova análise começa sem territórios e não pede nada ao motor"
        send(page, "Volte para o resultado anterior")
        expect(latest).to_contain_text("Reabri a análise anterior, sem recalcular")
        page.wait_for_timeout(1500)
        assert len(painel) == chamadas, "reabrir a análise anterior não recalcula"

        # 12. Planilha pela conversa: "enviar meus dados" abre a janela de envio; a orientação usa o nome das unidades
        # (condados), nunca "município"; e a conversa muda o gráfico da planilha.
        caminho = pasta / "condados.csv"
        caminho.write_text("condado;ano;quantidade;populacao\nAlfa;2023;10;1000\nBeta;2023;20;4000\nGama;2023;5;2500\n"
                           "Alfa;2024;12;1000\nBeta;2024;22;4100\nGama;2024;6;2500\n", encoding="utf-8")
        send(page, "enviar meus dados")
        expect(latest).to_contain_text("Abri a janela de envio")
        expect(latest).to_contain_text("confira as colunas no painel Colunas")
        janela = page.get_by_test_id("envio-de-dados")
        expect(janela).to_be_visible()
        expect(janela.get_by_test_id("envio-modelo-baixar")).to_be_visible()
        with page.expect_file_chooser() as escolha:
            janela.get_by_test_id("envio-escolher-arquivo").click()
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
        # A planilha também abre sem territórios: a orientação, sem "município", pede a escolha; com todos os condados
        # marcados na Seleção de Territórios, a área envia o arquivo ao motor.
        chamadas = len(painel)
        colunas.get_by_test_id("colunas-comecar").click()
        expect(colunas).to_have_count(0)
        expect(page.get_by_test_id("current-source")).to_contain_text("condados.csv · condados")
        expect(guia).to_contain_text("Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais "
                                     "quer ver.")
        expect(guia).not_to_contain_text(SEM_MUNICIPIO)
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "sem territórios escolhidos, nada é pedido ao motor"
        todos = area.get_by_test_id("analise-marcar-todos")
        expect(todos).to_have_text("Marcar todos os condados")
        with page.expect_response(lambda r: is_post(r, "/api/painel") and uploaded_filename(r.request) == "condados.csv",
                                  timeout=120000) as primeiro:
            todos.scroll_into_view_if_needed()
            todos.focus()
            todos.press("Enter")
        assert primeiro.value.status == 200, primeiro.value.text()[:2000]
        # Os nomes confirmados vão no pedido (24/10/2026), e a resposta fala deles: a Seleção continua com "condados", sem
        # voltar para "unidades" depois da resposta do motor.
        rotulos_pedidos = options_of(primeiro.value.request).get("rotulos") or {}
        assert (rotulos_pedidos.get("unidade") or {}).get("plural") == "condados", rotulos_pedidos
        assert primeiro.value.json()["rotulos"]["unidade"]["plural"] == "condados", primeiro.value.json()["rotulos"]
        expect(area.get_by_test_id("analise-aba-territorios-resumo")).to_have_text(re.compile(r"^Todos os condados( \(3\))?$"))
        expect(guia).to_contain_text("condados")
        expect(guia).not_to_contain_text(SEM_MUNICIPIO)
        page.wait_for_timeout(1000)
        resposta, _, pedido, grafico = chat_to_chart("Compare Alfa e Beta", lambda o: bool(o.get("comparar")))
        assert uploaded_filename(pedido) == "condados.csv", uploaded_filename(pedido)
        assert json.loads(form_field(pedido, "mapping")).get("territory") == "condado", form_field(pedido, "mapping")
        assert set(resposta["painel"].get("selecao") or []) == {"name:Alfa", "name:Beta"}, resposta["painel"]
        assert set(grafico["comparar"]) == {"name:Alfa", "name:Beta"}, grafico
        shot("03-planilha")

        # 13. Nada da base chega ao provedor simulado: nem arquivos, colunas e códigos, nem o contexto do gráfico, nem a
        # frase-resumo do motor, que a tela manda ao backend local (painel_resumo) e ele tira antes do intérprete.
        if simulado:
            registros = [json.loads(linha) for linha in provider_log().splitlines() if linha.strip()]
            assert len(registros) >= 3, registros
            payload = provider_log()
            for protegido in PROTEGIDOS:
                assert protegido not in payload, protegido
            assert contextuais, "o roteiro passa pelo intérprete contextual"
            for texto in filter(None, [frase, *(options_of(pedido).get("painel_resumo") for pedido in contextuais)]):
                assert texto not in payload, texto
            # Exemplos da biblioteca conversacional acompanham os pedidos, mascarados como as mensagens.
            exemplos = [registro["exemplos"] for registro in registros if registro.get("exemplos")]
            assert exemplos and all(bloco.startswith("EXEMPLOS_DA_BIBLIOTECA_CONVERSACIONAL") for bloco in exemplos), registros
        assert not analyze_calls, "a conversa não aciona as telas clássicas de /api/analyze"
        assert not failures, failures
        browser.close()
    print("CONVERSA NO GRÁFICO PASS: perguntas locais, fonte pela conversa sem seleção automática, todos os estados, Amazonas, "
          "mapa e gráfico, resumo, comparação, esclarecimento, estados, apresentação, análise anterior e planilha de condados" +
          (", ambiguidade e minimização (Gemini simulado)." if simulado else " (sem provedor)."))


if __name__ == "__main__":
    main()
