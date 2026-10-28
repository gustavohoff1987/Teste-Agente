"""Conversa agindo no gráfico da página única (22/10/2026), pela caixa da conversa, sempre na página.

Percorre:
- perguntas antes dos dados, respondidas sem o provedor de IA (inclusive a descrição dos dados do Brasil);
- o pedido de análise antes dos dados (26/10/2026), com ou sem o provedor: o lembrete na hora de escolher os dados, sem o
  intérprete, com os dois botões da escolha em destaque; o pedido fica guardado e segue pelo caminho completo quando a base
  fica pronta;
- a escolha da base pela conversa ("usar dados do Brasil"), sem o provedor e sem seleção automática (23/10/2026): nada é
  pedido ao motor até a escolha dos territórios, e a conversa orienta a escolher na Seleção de Territórios ou pela conversa;
- comandos que mudam o gráfico: o campo `painel` da resposta do intérprete local vira um pedido para a área, que pede ao
  motor (/api/painel) o novo recorte: "todos os estados", "Mostre o Amazonas", "Compare Manaus e Tefé" e "Volte aos estados";
- a vista do desenho pela conversa (23/10/2026), na tela e sem o intérprete: com os municípios na tela, "ver no mapa" troca
  o gráfico pelo mapa (`area-de-analise` com data-desenho="mapa") e "volte ao gráfico" desfaz; "o que esse gráfico mostra?"
  responde com a frase-resumo do motor (`analise-resumo`), como veio;
- o contexto que vai ao intérprete saindo do gráfico: os municípios na tela, a família, o indicador, a competência, a vista
  e a frase-resumo (esta nunca chega ao provedor);
- o gestor de diálogo (26/10/2026), no backend local e sem o provedor: a pergunta sobre o resultado em exibição ("Qual deles
  apresenta densidade maior?"), respondida com os valores do motor e sem recalcular; a troca de ordem da comparação; "não
  era isso que eu queria", que desfaz a última mudança da conversa; a resposta digitada a um esclarecimento ("a de
  janeiro"), que escolhe a alternativa como o clique; e "não entendi a aceleração", que abre "Entenda esta análise" da
  Tendência com a classe destacada;
- a comparação indireta (26/10/2026): "compare o de maior e o de menor densidade" abre a comparação dos extremos do gráfico,
  pelas ordens do motor, e as demais bolhas esmaecem;
- a proximidade pela conversa (28/10/2026): neste catálogo, sem a Análise Espacial, o pedido responde com o motivo, sem
  pedir nada ao motor (o cálculo e a leitura da referência mais próxima ficam no roteiro da área com a base versionada);
- um esclarecimento pendente ("Compare Manaus" → "Com qual outro município?"), guardado para a mensagem seguinte;
- pedidos de apresentação nos estados (tabela; mapa, que os estados não têm: a resposta é o motivo da área, e a vista
  continua o gráfico) e "volte ao resultado anterior", que reabre a análise anterior do Histórico, sem recalcular (a Nova
  análise recomeça sem territórios, sem pedir nada ao motor);
- uma planilha enviada pela conversa ("enviar meus dados", que abre a mesma janela de envio da área central, com o modelo de
  planilha), com condados e sem grupo: abre sem territórios escolhidos; a orientação usa o nome das unidades, nunca
  "município"; e "Compare Alfa e Beta" muda o gráfico da planilha.
Nada é calculado pela conversa.

- o histórico da conversa (26/10/2026): as mensagens da pessoa exatamente como ela escreveu e as respostas do agente, em
  ordem e sem duplicar, preservadas na navegação (vista, abas, Nova análise, planilha); a rolagem que não arrasta quem lê
  mensagens antigas; a caixa no celular; e a mensagem original na tela, mesmo quando a cópia ao provedor é triada.
Nada é calculado pela conversa.

Dois modos, pela suíte (run_ui_checks.py):
- "conversa" (servidor offline, sem transporte de IA): só os canais locais; o pedido que dependeria do provedor recebe a
  comunicação cordial de indisponibilidade no próprio histórico, sem código nem mensagem técnica, e a página continua
  funcionando;
- "gemini-simulado" (ADT_FAKE_GEMINI_LOG definido): também as perguntas de conversa, que seguem para o canal contextual e voltam redigidas pelo Gemini
  simulado e aprovadas na conferência de fidelidade; a proposta fora do contrato, que depois das tentativas previstas recebe
  a resposta de reserva; o limite de consultas e a falha temporária simulados, com o aviso certo para cada causa, os
  controles do gráfico funcionando e a recuperação; a ambiguidade material com alternativas em botões (CATALOGO_LOCAL); e a
  conferência do que chega ao provedor simulado: o resultado agregado em exibição sim; arquivos, colunas, códigos e as chaves
  internas da tela, não.
Catálogo sintético do Bloco 1 (AM: MANAUS, TEFE e PARINTINS; SP: FORA; quatro competências). Nunca chama o provedor real.
"""
import json
import os
import re
import tempfile
import time
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import (AREA, PRIVACIDADE, URL, accept_privacy, end_session, form_field, history_label, is_post, offline,
                        open_chat, options_of, send, uploaded_filename)

OUTPUT = Path(__file__).resolve().parents[2] / ".local" / "ui-validation"
MANAUS, TEFE, PARINTINS = "code:130260", "code:130420", "code:130340"
AMAZONAS = sorted([MANAUS, TEFE, PARINTINS])
SEM_MUNICIPIO = re.compile("munic", re.IGNORECASE)
# Nada disto pode chegar ao provedor: arquivos, colunas, códigos, as chaves do contexto do gráfico e a memória crua da conversa
# (a tela a manda ao backend local, que monta o cartão triado). A memória é conferida pela chave JSON, como apareceria escapada
# dentro de uma mensagem do registro: a palavra solta "anteriores" é legítima no cabeçalho fixo dos exemplos da biblioteca
# ("Mensagens anteriores:"). Desde 26/10/2026, o resultado agregado em exibição (territórios, valores, frase-resumo) pode ir.
PROTEGIDOS = ("Dados_Municipios_Brasil.csv", "Dados_Brasil.xlsx", "Dados_Estados_Brasil.csv", "cod_ibge", "população_estimada",
              "130260", "130420", "130340", "code:", "condados.csv", "territory_ids", "painel_familia", "painel_vista",
              "painel_resumo", "painel_mapa_disponivel", "painel_motivo_sem_mapa", "painel_consulta", '\\"anteriores\\"',
              '\\"pendente\\"', "displayed_result_id")


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

        def chat_reply(message, timeout=60000):
            """Mensagem respondida pelo intérprete local (gestor de diálogo ou gramática): a resposta e o pedido."""
            with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=timeout) as conversa:
                send(page, message)
            assert conversa.value.status == 200, conversa.value.text()[:2000]
            resposta = conversa.value.json()
            assert resposta.get("handled") is True, resposta
            return resposta, conversa.value.request

        def pergunta_de_conversa(message, timeout=90000):
            """Pergunta de conversa (o resultado, um conceito): sem provedor, o gestor responde no intérprete local; com o
            Gemini (simulado), ela segue para o canal contextual e volta redigida e aprovada na conferência de fidelidade."""
            rota = "/api/llm/interpret-context" if simulado else "/api/exploration/interpret"
            with page.expect_response(lambda r: is_post(r, rota), timeout=timeout) as event:
                send(page, message)
            assert event.value.status == 200, event.value.text()[:2000]
            corpo = event.value.json()
            if simulado:
                assert (corpo.get("redacao") or {}).get("origem") == "GEMINI_VALIDADO", corpo
            else:
                assert corpo.get("handled") is True, corpo
            return corpo, event.value.request

        def mensagens(papel=None):
            """O histórico como a pessoa o vê: o texto de cada mensagem, em ordem, sem o rótulo para leitores de tela."""
            seletor = '[data-testid="chat-mensagem"]' + ('[data-papel="' + papel + '"]' if papel else "")
            return [re.sub(r"^(?:Você|Agente): ", "", " ".join((t or "").split()))
                    for t in historico.locator(seletor).all_text_contents()]

        page.goto(URL)
        accept_privacy(page)
        area = page.get_by_test_id(AREA["raiz"])
        expect(area).to_be_visible()
        chat = open_chat(page)
        guia = chat.get_by_test_id("painel-chat-guia")
        latest = chat.get_by_test_id("latest-reply")
        historico = chat.get_by_test_id("chat-historico")
        enviadas = []  # o que a pessoa escreveu, na ordem, para conferir o histórico no fim
        expect(guia).to_contain_text("O que você quer analisar?")

        # 1. Antes dos dados: perguntas respondidas pelo catálogo local, sem o intérprete. Com o Gemini (simulado), a
        # explicação do método é redigida a partir do texto do catálogo e conferida; o agradecimento continua local.
        def interpretacoes_no_registro():
            return sum(1 for linha in provider_log().splitlines() if linha.strip() and '"redacao": true' not in linha)
        antes = interpretacoes_no_registro()
        for pergunta, trecho in (("Como se calcula a densidade?", "D(u, p, c) = Q(u, p, c) / P(u, p′)"),
                                 ("Muito obrigada pela ajuda!", "De nada")):
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
                send(page, pergunta)
            enviadas.append(pergunta)
            assert event.value.status == 200, event.value.text()[:2000]
            expect(latest).to_contain_text(trecho)
            if simulado and pergunta.startswith("Como"):
                assert event.value.json()["redacao"]["origem"] == "GEMINI_VALIDADO", event.value.json()
                expect(latest).to_contain_text("Em outras palavras")
        # A mensagem aparece na hora, exatamente como foi escrita, e a resposta fica abaixo dela.
        expect(historico.locator('[data-papel="usuario"]').last).to_have_text(re.compile("Muito obrigada pela ajuda!$"))
        with page.expect_response(lambda r: r.url.endswith("/api/brazil/description"), timeout=60000) as event:
            send(page, "O que tem nos dados do Brasil?")
        enviadas.append("O que tem nos dados do Brasil?")
        assert event.value.status == 200, event.value.text()[:2000]
        expect(latest).to_contain_text("Os dados do Brasil disponíveis nesta plataforma")
        expect(page.get_by_test_id("current-source")).to_have_count(0)  # a descrição não escolhe a fonte
        assert interpretacoes_no_registro() == antes, "as respostas locais não chamam o intérprete"

        # 2. Pedido de análise antes dos dados (26/10/2026): com ou sem o provedor, a conversa lembra na hora de escolher os
        # dados, sem chamar o intérprete, destaca os dois botões da escolha e guarda o pedido até a base ficar pronta. Sem o
        # provedor, uma conversa livre recebe o aviso cordial de indisponibilidade, e a página continua funcionando. Desde
        # 28/10/2026, um pedido que cita um estado do Brasil recebe na hora a oferta dos dados do Brasil, com o botão dela na
        # resposta e só o botão "Usar dados do Brasil" do alto em destaque; a mensagem seguinte esquece a oferta.
        antes = interpretacoes_no_registro()
        with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
            send(page, "quero analisar o Amazonas")
        enviadas.append("quero analisar o Amazonas")
        assert event.value.status == 200, event.value.text()[:2000]
        assert event.value.json().get("aguarda_base") is True and event.value.json().get("fonte_sugerida") == "brasil", \
            event.value.json()
        assert interpretacoes_no_registro() == antes, "a oferta dos dados do Brasil não chama o intérprete"
        expect(latest).to_contain_text("Para analisar o Amazonas, posso usar os dados do Brasil: escolha “Usar dados do Brasil” "
                                       "ou responda “sim”.")
        escolha_dos_dados = chat.get_by_role("group", name="Escolha dos dados na conversa")
        alternativas = chat.get_by_role("group", name="Alternativas de esclarecimento")
        expect(escolha_dos_dados).to_have_attribute("data-lembrete", "brasil")
        expect(alternativas.get_by_role("button", name="Usar dados do Brasil", exact=True)).to_be_visible()
        with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
            send(page, "Quero analisar a densidade")
        enviadas.append("Quero analisar a densidade")
        assert event.value.status == 200, event.value.text()[:2000]
        assert json.loads(event.value.request.post_data or "{}").get("lembrar_base") is True, event.value.request.post_data
        assert event.value.json().get("aguarda_base") is True, event.value.json()
        assert interpretacoes_no_registro() == antes, "o lembrete da escolha dos dados não chama o intérprete"
        expect(latest).to_contain_text("Para fazer essa análise, primeiro escolha os dados: use os dados do Brasil ou envie os seus")
        expect(escolha_dos_dados).to_have_attribute("data-lembrete", "true")
        expect(alternativas).to_have_count(0)
        # Cada mensagem fica no histórico com a hora no balão (sem entrar no texto da mensagem).
        expect(historico.locator('[data-papel="usuario"]').last).to_have_attribute("data-hora", re.compile(r"^\d{2}:\d{2}$"))
        send(page, "certo, quantos tem?")
        enviadas.append("certo, quantos tem?")
        expect(latest).to_contain_text("Para continuar, escolha os dados")
        if not simulado:
            # Sem o provedor: o aviso cordial como resposta, no histórico, sem código nem mensagem técnica; a pergunta fica.
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
                send(page, "Me conte uma curiosidade")
            enviadas.append("Me conte uma curiosidade")
            assert event.value.status == 200 and "indisponibilidade" in event.value.json(), event.value.json()
            aviso = historico.locator('[data-papel="aviso"]').last
            expect(aviso).to_contain_text("Assistente conversacional temporariamente indisponível")
            expect(aviso).to_contain_text("O recurso de conversa não está disponível neste momento.")
            expect(historico.locator('[data-papel="usuario"]').last).to_have_text(re.compile("Me conte uma curiosidade$"))
            expect(chat.get_by_role("alert")).to_have_count(0)
            expect(chat).not_to_contain_text(re.compile(r"HTTP|\b50[0-9]\b|GEMINI_API_KEY|Gemini não configurado"))
            expect(chat.get_by_test_id("chat-estado-do-servico")).to_contain_text("Os botões, os controles")

        # 3. A base escolhida pela conversa, como pelo botão, sem o provedor e sem seleção automática: nada é pedido ao motor
        # até a escolha dos territórios, e a conversa orienta a escolher. O pedido guardado segue pelo caminho completo,
        # primeiro o intérprete local, já com a base (com ou sem o provedor). Depois, "todos os estados", o exemplo da
        # orientação, põe os estados no gráfico (E1).
        chamadas_llm, chamadas_painel = len(llm_calls), len(painel)
        with page.expect_request(lambda r: r.url.endswith("/api/exploration/interpret") and
                                 form_field(r, "message") == "Quero analisar a densidade", timeout=180000):
            with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=180000) as inspecao:
                send(page, "usar dados do Brasil")
        assert inspecao.value.status == 200, inspecao.value.text()[:2000]
        assert len(llm_calls) == chamadas_llm, "a escolha da fonte pela conversa é local"
        expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil")
        # Com o pedido guardado, a escolha diz que ele segue (28/10/2026), em vez de mandar escolher os territórios.
        expect(historico).to_contain_text("Dados do Brasil escolhidos. Vou prepará-los e, em seguida, sigo com o seu pedido.")
        expect(guia).to_contain_text("Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais "
                                     "quer ver: o nome de um estado ou de municípios, ou “todos os estados”.", timeout=60000)
        expect(latest).to_contain_text("Com os dados prontos, sigo com o seu pedido.", timeout=60000)
        expect(area).to_have_attribute("data-aba", "territorios")
        page.wait_for_timeout(1000)  # a área informa o contexto do gráfico (sem territórios)
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

        # 6b. Gestor de diálogo (26/10/2026), no backend local e sem o provedor: a pergunta sobre o resultado em exibição é
        # respondida com os valores do motor (a tela manda a memória da conversa e o resultado em exibição), sem recalcular;
        # a troca de ordem muda a comparação; "não era isso que eu queria" desfaz a última mudança feita pela conversa.
        chamadas = len(painel)
        corpo, pedido = pergunta_de_conversa("Qual deles apresenta densidade maior?")
        assert not corpo.get("painel"), corpo
        assert form_field(pedido, "displayed_result_id"), "a tela manda o resultado em exibição"
        assert "anteriores" in json.loads(form_field(pedido, "conversa") or "{}"), "a tela manda a memória"
        if simulado:
            turnos = json.loads(form_field(pedido, "turnos") or "[]")
            assert turnos and turnos[-1] == {"papel": "agente", "texto": turnos[-1]["texto"]} and len(turnos) <= 8, turnos
        expect(latest).to_contain_text("A maior densidade")
        expect(latest).to_contain_text("MANAUS (AM)")
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "a pergunta sobre o resultado não recalcula"
        resposta, conversa, pedido, grafico = chat_to_chart("troca o primeiro pelo segundo",
                                                            lambda o: o.get("comparar") == [TEFE, MANAUS])
        assert resposta["painel"].get("selecao") == [TEFE, MANAUS], resposta["painel"]
        expect(latest).to_contain_text("Troquei a ordem")
        # A comparação de antes já foi calculada: a área a mostra da memória da tela, sem novo pedido ao motor.
        resposta, pedido = chat_reply("não era isso que eu queria")
        assert resposta.get("desfazer") == 1 and (resposta.get("painel") or {}).get("selecao") == [MANAUS, TEFE], resposta
        anteriores = json.loads(form_field(pedido, "conversa"))["anteriores"]
        assert anteriores and anteriores[-1]["pedido"].get("selecao") == [MANAUS, TEFE], anteriores
        expect(latest).to_contain_text("Desfiz a última mudança")
        page.wait_for_timeout(1000)

        # 6b2. Comparação indireta (26/10/2026): "compare o de maior e o de menor densidade" identifica os extremos do gráfico
        # pelas ordens do motor e abre a comparação, sem pedir os nomes; no gráfico de bolhas, só os comparados ficam
        # inteiros, e as demais bolhas da seleção esmaecem.
        valores = dict(area.locator('[data-testid="analise-bolha"][data-tipo="municipio"]').evaluate_all(
            "els => els.map(e => [e.dataset.id, Number(e.dataset.valor)])"))
        maior, menor = max(valores, key=valores.get), min(valores, key=valores.get)
        assert len(valores) == 3 and {maior, menor} != {MANAUS, TEFE}, valores  # uma comparação nova, não a que já está aberta
        resposta, _, _, grafico = chat_to_chart("compare o de maior e o de menor densidade",
                                                lambda o: set(o.get("comparar") or []) == {maior, menor})
        assert resposta["painel"].get("selecao") == [maior, menor], resposta["painel"]
        expect(latest).to_contain_text("Abri a comparação lado a lado com o de maior e o de menor densidade")
        fora = area.locator('[data-testid="analise-bolha"][data-destaque="false"]')
        expect(fora).to_have_count(1, timeout=30000)
        expect(area.locator('[data-testid="analise-bolha"][data-destaque="true"]')).to_have_count(2)
        assert fora.evaluate_all("els => els.map(e => e.hasAttribute('aria-describedby') ? '0.25' : e.style.opacity)") == [
            "0.25"], "fora da comparação, a bolha esmaece (a ativa, sob o mouse, fica inteira enquanto está ativa)"
        assert area.locator('[data-testid="analise-bolha"][data-destaque="true"]').evaluate_all(
            "els => els.map(e => e.style.opacity)") == ["1", "1"]
        shot("02a-comparacao-pelos-extremos")

        # 6c. Resposta digitada a um esclarecimento: "em 2024" tem duas competências no catálogo; as alternativas aparecem em
        # botões, e a resposta escrita ("a de janeiro") escolhe uma delas, como o clique. "Não era isso" volta à de antes.
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Compare Manaus e Tefé em 2024")
        assert event.value.json().get("choices"), event.value.json()
        alternativas = chat.get_by_role("group", name="Alternativas de esclarecimento")
        expect(alternativas).to_be_visible()
        resposta, conversa, pedido, grafico = chat_to_chart("a de janeiro", lambda o: o.get("competencia") == "202401")
        assert json.loads(form_field(pedido, "conversa")).get("pendente", {}).get("alternativas"), "a pendência vai junto"
        assert grafico.get("comparar") and set(grafico["comparar"]) == {MANAUS, TEFE}, grafico
        expect(latest).to_contain_text("Entendi:")
        expect(chat.get_by_role("group", name="Alternativas de esclarecimento")).to_have_count(0)
        resposta, _ = chat_reply("não era isso que eu queria")
        assert (resposta.get("painel") or {}).get("competencia") == "202406" and resposta.get("desfazer") == 1, resposta
        expect(latest).to_contain_text("Desfiz a última mudança")
        page.wait_for_timeout(1000)

        # 6d. Explicação pela conversa na Tendência: "não entendi a aceleração" responde com as classes e os valores do motor
        # e abre "Entenda esta análise" da aba com a classe destacada, sem recalcular. O Desfazer do alto volta à
        # Distribuição para os passos seguintes.
        with page.expect_response(lambda r: is_post(r, "/api/painel") and "tendencia" in options_of(r.request),
                                  timeout=120000) as event:
            aba = area.get_by_test_id("analise-familia-tendencia")  # pelo teclado: a caixa da conversa pode estar por cima
            aba.scroll_into_view_if_needed()
            aba.focus()
            aba.press("Enter")
        assert event.value.status == 200, event.value.text()[:2000]
        expect(area).to_have_attribute("data-familia", "tendencia")
        entenda = area.get_by_test_id("analise-entenda")
        expect(entenda).not_to_have_attribute("open", "")
        page.wait_for_timeout(1000)  # a área informa o novo resultado em exibição
        chamadas = len(painel)
        corpo, _ = pergunta_de_conversa("Não entendi a aceleração.")
        acoes = corpo.get("acoes") or []
        assert acoes and acoes[0].get("tipo") == "explicar" and acoes[0].get("aba") == "tendencia", corpo
        expect(latest).to_contain_text("ganhou ritmo")  # a regra da classe em palavras (ficha autorizada)
        expect(latest).to_contain_text("Entenda esta análise")
        expect(entenda).to_have_attribute("open", "")
        expect(entenda.get_by_test_id("analise-apresentacao-destaque").first).to_be_visible()
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "a explicação não recalcula"
        shot("02c-explicacao-pela-conversa")
        desfazer = page.get_by_test_id("analise-desfazer")
        desfazer.focus()
        desfazer.press("Enter")
        expect(area).to_have_attribute("data-familia", "distribuicao", timeout=60000)
        page.wait_for_timeout(1500)

        # 7. Esclarecimento: a conversa pergunta o outro município e guarda a pendência para a mensagem seguinte.
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Compare Manaus")
        assert event.value.json().get("pending_operation") == "comparisons", event.value.json()
        expect(latest).to_contain_text("Com qual outro município")
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "Tefé e Parintins")
        assert options_of(event.value.request).get("conversation_pending_operation") == "comparisons", options_of(event.value.request)
        page.wait_for_timeout(1500)

        # 7b. Referência pela conversa (decisão 4, 25/10/2026; na Escolha dos territórios desde 27/10/2026): o "menor" do pedido
        # vira, na aba Referência, um filtro do atributo citado com o operador "abaixo de"; o valor fica com a pessoa, sem valor
        # sugerido, e a janela mostra a pendência, com "Calcular" desligado. O Desfazer do alto (o "Voltar" até 25/10/2026) desfaz
        # o pedido da conversa e devolve a análise de antes, para os passos seguintes.
        familia_antes = area.get_attribute("data-familia")
        with page.expect_response(lambda r: is_post(r, "/api/exploration/interpret"), timeout=60000) as event:
            send(page, "use como referência o município de menor densidade")
        resposta = event.value.json()
        assert (resposta.get("painel") or {}).get("referencia") == {
            "membros": [], "criterio": {"atributo": "densidade", "ordem": "asc"}}, resposta
        expect(latest).to_contain_text("com o filtro Densidade “abaixo de” na Referência")
        janela = area.get_by_test_id("analise-referencia")
        expect(janela).to_be_visible(timeout=60000)
        expect(janela.get_by_test_id("territorios-aba-referencia")).to_have_attribute("aria-selected", "true")
        filtro = janela.get_by_test_id("territorios-referencia-filtro")
        expect(filtro).to_have_count(1)
        expect(filtro.get_by_test_id("territorios-referencia-filtro-indicador")).to_have_value("densidade")
        expect(filtro.get_by_test_id("territorios-referencia-filtro-operador")).to_have_value("<")
        expect(filtro.get_by_test_id("territorios-referencia-filtro-valor")).to_have_value("")
        expect(janela.get_by_test_id("territorios-frase-referencia")).to_have_text("referência incompleta")
        expect(janela.get_by_test_id("territorios-estado")).to_have_text("Referência incompleta: preencha o valor do filtro.")
        expect(janela.get_by_test_id("territorios-calcular")).to_be_disabled()
        shot("02b-referencia-pela-conversa")
        page.get_by_test_id("analise-desfazer").click()
        expect(area).to_have_attribute("data-familia", familia_antes, timeout=60000)
        page.wait_for_timeout(1500)

        # 7c. Proximidade pela conversa (28/10/2026, pedido do responsável): neste catálogo sintético, a Análise Espacial não
        # existe (sem o referencial geodésico governado); o pedido de proximidade, com o extremo do gráfico ou com um nome,
        # responde com o motivo que o motor informou no resultado em exibição, sem prometer a análise e sem pedir nada ao motor.
        # O cálculo, a leitura da referência mais próxima e a troca do recorte são conferidos em ui_area_de_analise.py, com a
        # base versionada.
        chamadas = len(painel)
        for pedido_de_proximidade in ("o de menor densidade e o mais próximo dele com densidade acima de 0",
                                      "qual o município mais próximo de Manaus com densidade acima de 0?"):
            resposta, _ = chat_reply(pedido_de_proximidade)
            assert not resposta.get("painel") and (resposta.get("dialogo") or {}).get("ato") == "proximidade", resposta
            expect(latest).to_contain_text("A Análise Espacial não está disponível nesta base: ")
            expect(latest).to_contain_text("Nada mudou no gráfico.")
        page.wait_for_timeout(800)
        assert len(painel) == chamadas, "sem a Análise Espacial, nada é pedido ao motor"
        expect(area).to_have_attribute("data-familia", familia_antes)

        # 8. Gemini simulado: ambiguidade material com alternativas em botões; a escolha muda o indicador do gráfico, e a
        # mensagem seguinte leva o novo indicador no contexto.
        indicador = "density"
        if simulado:
            # Uma proposta do provedor fora do contrato: nova tentativa com as violações, até 2 vezes; persistindo, a resposta
            # de reserva, sem erro técnico, e nada muda no gráfico. A mensagem seguinte funciona.
            chamadas, registros = len(painel), interpretacoes_no_registro()
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "Mostre algo invalido")
            assert event.value.status == 200 and event.value.json().get("reserva") is True, event.value.text()[:2000]
            assert "fake-offline-key" not in event.value.text()
            expect(latest).to_contain_text("Não consegui interpretar este pedido com segurança")
            expect(chat.get_by_role("alert")).to_have_count(0)
            assert interpretacoes_no_registro() - registros == 3, "a primeira tentativa e só 2 regenerações"
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

            # 8b. Limite de consultas e falha temporária simulados (sem chamada real): o aviso certo para cada causa, como
            # resposta no histórico; durante a espera informada pelo provedor, nada é chamado de novo; os controles do gráfico
            # e os pedidos diretos continuam; passada a espera, a conversa volta sozinha, sem recarregar a página.
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "simule limite de consultas agora")
            assert event.value.json()["indisponibilidade"]["tipo"] == "cota", event.value.json()
            aviso = historico.locator('[data-papel="aviso"]').last
            expect(aviso).to_contain_text("Assistente conversacional temporariamente indisponível")
            expect(aviso).to_contain_text("O limite de consultas ao assistente conversacional foi atingido neste momento.")
            expect(historico.locator('[data-papel="usuario"]').last).to_have_text(re.compile("simule limite de consultas agora$"))
            expect(chat).not_to_contain_text(re.compile(r"HTTP|429|RESOURCE_EXHAUSTED|[Qq]uota|rate limit"))
            registros = len(provider_log().splitlines())
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "e o que mais dá para fazer com isso?")
            assert event.value.json()["indisponibilidade"]["tipo"] == "cota", event.value.json()
            assert len(provider_log().splitlines()) == registros, "durante a espera, nenhuma chamada ao provedor"
            resposta, _ = chat_reply("Compare Manaus e Tefé")  # o comando direto do gráfico continua, sem o provedor
            assert resposta.get("painel") and len(provider_log().splitlines()) == registros, resposta
            page.wait_for_timeout(3500)  # a espera informada pelo provedor (3 s) passou
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "e o que mais dá para fazer com isso?")
            assert "indisponibilidade" not in event.value.json(), event.value.json()
            assert len(provider_log().splitlines()) > registros, "a conversa voltou a chamar o provedor"
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000) as event:
                send(page, "simule queda do serviço")
            assert event.value.json()["indisponibilidade"]["tipo"] == "indisponivel", event.value.json()
            expect(historico.locator('[data-papel="aviso"]').last).to_contain_text(
                "O recurso de conversa não está disponível neste momento.")
            expect(historico.locator('[data-papel="aviso"]').last).not_to_contain_text("limite")
            enviadas.extend(["simule limite de consultas agora", "e o que mais dá para fazer com isso?",
                             "Compare Manaus e Tefé", "e o que mais dá para fazer com isso?", "simule queda do serviço"])
            page.wait_for_timeout(3500)

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

        # 12b. O histórico da conversa, como a pessoa o vê: tudo o que ela escreveu, exatamente como escreveu, em ordem, sem
        # duplicar, depois da vista, das abas, da Nova análise e da troca de fonte; a mensagem original fica na tela mesmo
        # quando a cópia ao provedor é triada; a rolagem não arrasta quem lê o começo; a caixa funciona no celular.
        original = "Meu CPF é 123.456.789-09; a Maria Quitéria pode ver isso?"
        send(page, original)  # espera a resposta (o campo volta a aceitar texto)
        expect(historico.locator('[data-papel="usuario"]').last).to_have_text(re.compile(re.escape(original) + "$"))
        expect(historico.locator('[data-testid="chat-mensagem"]').last).not_to_have_attribute("data-papel", "usuario")
        usuario = mensagens("usuario")
        for texto in ("Como se calcula a densidade?", "Mostre o Amazonas", "Compare Manaus e Tefé em 2024", "a de janeiro",
                      "Não entendi a aceleração.", "Compare Alfa e Beta", original):
            assert usuario.count(texto) >= 1, (texto, usuario)
        posicoes = [usuario.index(texto) for texto in ("Como se calcula a densidade?", "Mostre o Amazonas",
                                                       "Compare Manaus e Tefé em 2024", "a de janeiro", "Compare Alfa e Beta")]
        assert posicoes == sorted(posicoes), usuario
        assert usuario.count("Mostre o Amazonas") == 1 and usuario.count("a de janeiro") == 1, usuario
        todas = mensagens()
        pergunta = todas.index("Compare Manaus e Tefé em 2024")
        assert todas[pergunta + 2] == "a de janeiro" and "Em 2024" in todas[pergunta + 1], todas[pergunta:pergunta + 4]
        if simulado:
            assert "123.456.789-09" not in provider_log() and "Maria Quitéria" not in provider_log()
        historico.evaluate("el => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')); }")
        page.wait_for_timeout(300)
        topo = historico.evaluate("el => el.scrollTop")
        send(page, "ver no mapa")  # quem envia vai ao fim, para ver a resposta
        page.wait_for_timeout(300)
        assert historico.evaluate("el => el.scrollHeight - el.scrollTop - el.clientHeight") <= 48 and topo == 0
        if simulado:
            # Lendo o começo enquanto a resposta chega: a resposta não puxa a pessoa para o fim; o botão leva até ela.
            chat.locator("#assistant-input").fill("explique de forma lenta o que estou vendo")
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret-context"), timeout=90000):
                chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
                page.wait_for_timeout(400)
                historico.evaluate("el => { el.scrollTop = 0; el.dispatchEvent(new Event('scroll')); }")
            page.wait_for_timeout(500)
            assert historico.evaluate("el => el.scrollTop") < 40, "a resposta não forçou a rolagem"
            ir = chat.get_by_test_id("chat-ir-ao-fim")
            expect(ir).to_be_visible()
            ir.click()
            expect(ir).to_have_count(0)
        # A captura de página inteira não guarda a rolagem interna da caixa: a da caixa mostra o histórico como está na tela.
        page.get_by_test_id("painel-chat").screenshot(path=str(OUTPUT / ("conversa-grafico-05-historico-caixa" + suffix +
                                                                          ".png")))
        page.set_viewport_size({"width": 390, "height": 844})
        expect(historico).to_be_visible()
        caixa = page.get_by_test_id("painel-chat").bounding_box()
        assert caixa and caixa["x"] >= 0 and caixa["x"] + caixa["width"] <= 390 + 1, caixa
        expect(historico.locator('[data-papel="usuario"]').last).to_be_visible()
        shot("04-historico-celular")
        page.get_by_test_id("painel-chat").screenshot(path=str(OUTPUT / ("conversa-grafico-06-historico-celular-caixa" +
                                                                          suffix + ".png")))
        page.set_viewport_size({"width": 1280, "height": 900})

        # 13. O que chega ao provedor simulado: o resultado agregado em exibição sim (Frente IV); arquivos, colunas, códigos,
        # as chaves internas da tela e a memória crua da conversa, não.
        if simulado:
            registros = [json.loads(linha) for linha in provider_log().splitlines() if linha.strip()]
            assert len(registros) >= 3, registros
            payload = provider_log()
            for protegido in PROTEGIDOS:
                assert protegido not in payload, protegido
            assert contextuais, "o roteiro passa pelo intérprete contextual"
            assert "resultado_em_exibicao" in payload and "MANAUS (AM)" in payload, "o cartão leva o resultado em exibição"
            # Exemplos da biblioteca conversacional acompanham os pedidos, mascarados como as mensagens.
            exemplos = [registro["exemplos"] for registro in registros if registro.get("exemplos")]
            assert exemplos and all(bloco.startswith("EXEMPLOS_DA_BIBLIOTECA_CONVERSACIONAL") for bloco in exemplos), registros
        # 14. Começo sem base numa sessão nova (28/10/2026): o pedido que cita um estado do Brasil recebe a oferta dos dados do
        # Brasil, sem o intérprete; "sim" (na primeira sessão) e o botão "Usar dados do Brasil" da resposta (na segunda)
        # escolhem os dados do Brasil, como o botão do alto, e o pedido guardado segue quando a base fica pronta: os
        # municípios do Amazonas no gráfico.
        for aceite in ("sim", "botao"):
            end_session(page)
            expect(page.get_by_role("dialog", name=PRIVACIDADE)).to_be_visible(timeout=60000)
            accept_privacy(page)
            expect(page.get_by_test_id("current-source")).to_have_count(0)
            antes = interpretacoes_no_registro()
            with page.expect_response(lambda r: is_post(r, "/api/llm/interpret"), timeout=60000) as event:
                send(page, "quero analisar o Amazonas")
            assert event.value.json().get("fonte_sugerida") == "brasil", event.value.json()
            assert interpretacoes_no_registro() == antes, "a oferta dos dados do Brasil não chama o intérprete"
            expect(latest).to_contain_text("Para analisar o Amazonas, posso usar os dados do Brasil")
            expect(chat.get_by_role("group", name="Escolha dos dados na conversa")).to_have_attribute("data-lembrete", "brasil")
            with page.expect_response(lambda r: is_post(r, "/api/painel") and (
                    options_of(r.request).get("base") or {}).get("municipios", {}).get("estados") == ["13"],
                    timeout=180000) as grafico:
                with page.expect_response(lambda r: is_post(r, "/api/inspect"), timeout=180000) as inspecao:
                    if aceite == "sim":
                        send(page, "sim")
                    else:
                        chat.get_by_role("group", name="Alternativas de esclarecimento").get_by_role(
                            "button", name="Usar dados do Brasil", exact=True).click()
            assert inspecao.value.status == 200 and grafico.value.status == 200, (inspecao.value.status, grafico.value.status)
            expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil")
            expect(historico).to_contain_text("Dados do Brasil escolhidos. Vou prepará-los e, em seguida, sigo com o seu pedido.")
            expect(latest).to_contain_text("Com os dados prontos, sigo com o seu pedido.", timeout=60000)
            expect(area.locator('[data-testid="analise-bolha"][data-tipo="municipio"]')).to_have_count(3, timeout=60000)
        shot("06-comeco-sem-base-oferta")

        assert not analyze_calls, "a conversa não aciona as telas clássicas de /api/analyze"
        assert not failures, failures
        browser.close()
    print("CONVERSA NO GRÁFICO PASS: perguntas locais, fonte pela conversa sem seleção automática, todos os estados, Amazonas, "
          "mapa e gráfico, resumo, comparação, gestor de diálogo (pergunta sobre o resultado, troca, desfazer, resposta digitada e "
          "Entenda pela conversa), esclarecimento, estados, apresentação, análise anterior, planilha de condados e histórico "
          "visível (ordem, sem duplicar, navegação, original na tela, rolagem e celular), oferta dos dados do Brasil antes da "
          "escolha (\"sim\" e o botão da resposta)" +
          (", redação conferida, reserva de contrato, limite e queda simulados com recuperação, ambiguidade e triagem "
           "(Gemini simulado)." if simulado else ", aviso cordial sem o provedor."))


if __name__ == "__main__":
    main()
