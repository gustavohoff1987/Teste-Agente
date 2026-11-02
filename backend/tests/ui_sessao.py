"""Sessão temporária pelo navegador (RQ-FLX-17, TPL-09; hospedagem de 01/11/2026, seção 9 do comando de implantação).

O servidor de teste reduz o prazo de inatividade para ADT_SESSAO_PRAZO_DE_TESTE (45 s, suíte "sessao" do run_ui_checks.py);
o produto continua com os 1.800 s fixos. Percorre:
1. a consulta automática da sessão (a cada 30 s) não renova o prazo: no servidor, ele só diminui;
2. a interação do catálogo (um clique num controle, NAVEGACAO_CONTROLE_EFETIVO) renova o prazo;
3. sem interação, a sessão expira no prazo, apesar das consultas; a tela recarrega com o aviso de sessão expirada ou
   indisponível (estado E), nunca com o de serviço indisponível (estado A);
4. o encerramento explícito (Nova sessão) é imediato: o token deixa de valer na hora;
5. a aba congelada, como um aparelho em repouso ou um navegador móvel em segundo plano: nenhuma consulta sai, a sessão expira
   no servidor e, ao voltar, a tela informa a perda (a consulta não mantém a sessão nem a instância).
Catálogo sintético do Bloco 1; nunca chama o provedor de IA.
"""
import os
import time

from playwright.sync_api import expect, sync_playwright
from ui_support import API, PRIVACIDADE, URL, accept_privacy, end_session, offline

PRAZO = int(os.getenv("ADT_SESSAO_PRAZO_DE_TESTE", "45"))
assert 35 <= PRAZO <= 120, "o roteiro precisa do prazo reduzido do servidor de teste (entre 35 e 120 s)"
EXPIRADA = "A sessão anterior expirou ou ficou indisponível no servidor."


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        falhas, consultas, tokens = [], [], []
        page.on("pageerror", lambda erro: falhas.append(str(erro)))

        def registrar(pedido):
            if pedido.method == "GET" and pedido.url.endswith("/api/session"):
                consultas.append(time.monotonic())
            token = pedido.headers.get("x-adt-session")
            if token and token not in tokens:
                tokens.append(token)
        page.on("request", registrar)

        def no_servidor(token):
            """(status, prazo restante) da sessão, consultado à parte: a consulta não renova o prazo."""
            resposta = context.request.get(API + "api/session", headers={"X-ADT-Session": token})
            return resposta.status, resposta.json().get("expires_in") if resposta.status == 200 else None

        def nova_sessao_com_os_dados():
            """Aceite e a primeira interação (a escolha dos dados do Brasil), que cria a sessão no servidor."""
            accept_privacy(page)
            tokens.clear()
            with page.expect_response(lambda r: r.url.endswith("/api/session/interact"), timeout=60000) as interacao:
                page.get_by_test_id("analise-fonte-brasil").click()
            assert interacao.value.status == 200, interacao.value.text()[:300]
            expect(page.get_by_test_id("current-source")).to_be_visible(timeout=60000)
            assert tokens, "a interação leva a sessão temporária"
            return tokens[0]

        page.goto(URL)
        token = nova_sessao_com_os_dados()
        status, inicio = no_servidor(token)
        assert status == 200 and inicio > PRAZO - 10, (status, inicio)

        # 1. Consulta sem renovação: a consulta automática sai, e o prazo no servidor só diminui.
        antes = len(consultas)
        page.wait_for_timeout(33000)
        assert len(consultas) > antes, "a tela consulta a sessão a cada 30 s"
        status, depois = no_servidor(token)
        assert status == 200 and depois <= inicio - 30, ("a consulta não renova o prazo", inicio, depois)

        # 2. Interação com renovação: um clique num controle do catálogo devolve o prazo inteiro.
        with page.expect_response(lambda r: r.url.endswith("/api/session/interact"), timeout=30000) as renovacao:
            page.get_by_test_id("pagina-marca").click()
        assert renovacao.value.status == 200
        status, renovado = no_servidor(token)
        assert status == 200 and renovado >= PRAZO - 3, ("a interação renova o prazo", renovado)

        # 3. Expiração sem interação, apesar das consultas: o aviso de sessão expirada (E), não o de serviço indisponível (A).
        inicio_da_espera = time.monotonic()
        expect(page.get_by_test_id("session-ended-notice")).to_contain_text(EXPIRADA, timeout=(PRAZO + 45) * 1000)
        decorrido = time.monotonic() - inicio_da_espera
        assert decorrido >= PRAZO - 5, ("a sessão não expira antes do prazo", decorrido)
        assert no_servidor(token)[0] == 410
        expect(page.get_by_role("dialog", name=PRIVACIDADE)).to_be_visible()
        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)

        # 4. Encerramento explícito: imediato, e o token deixa de valer na hora.
        token = nova_sessao_com_os_dados()
        expect(page.get_by_test_id("nav-new-session")).to_be_visible(timeout=60000)
        end_session(page)
        expect(page.get_by_test_id("session-ended-notice")).to_contain_text("A sessão anterior foi encerrada", timeout=60000)
        assert no_servidor(token)[0] == 410

        # 5. Aba congelada (aparelho em repouso): nenhuma consulta sai; a sessão expira no servidor; ao voltar, a tela avisa.
        token = nova_sessao_com_os_dados()
        cdp = context.new_cdp_session(page)
        cdp.send("Page.setWebLifecycleState", {"state": "frozen"})
        congeladas = len(consultas)
        time.sleep(PRAZO + 8)
        assert len(consultas) == congeladas, "a aba congelada não consulta a sessão"
        assert no_servidor(token)[0] == 410, "sem interação, a sessão expira no servidor mesmo com a aba aberta"
        cdp.send("Page.setWebLifecycleState", {"state": "active"})
        expect(page.get_by_test_id("session-ended-notice")).to_contain_text(EXPIRADA, timeout=60000)
        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)

        assert not falhas, falhas
        browser.close()
    print(f"SESSÃO PASS (prazo de teste {PRAZO} s): consulta sem renovação, interação com renovação, expiração sem interação "
          "com o aviso de sessão expirada, encerramento imediato e aba congelada sem consultas.")


if __name__ == "__main__":
    main()
