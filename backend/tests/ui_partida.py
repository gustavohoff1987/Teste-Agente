"""A página que espera o servidor ligar (PA-02, 19/11/2026), com a interface como no GitHub Pages e o serviço no contêiner (suíte
"conteiner" do run_ui_checks.py; servidor serve_ui_conteiner.py, que sobe a imagem com 1 CPU e 2 GiB).

O contêiner de verdade é parado e ligado de novo (docker stop e start), e a página abre antes de ele abrir a porta. A plataforma
do Cloud Run é imitada nos pedidos à API, até o serviço responder: ela segura a verificação de saúde (como o Cloud Run segura o
pedido numa partida a frio) e recusa os demais sem resposta legível, como o "The request was aborted after waiting too long for
an available instance", sem CORS, que o navegador vê como falha de rede. Percorre:
- a abertura durante a partida: o aviso de partida; o clique em "Dados do Brasil" e uma mensagem na conversa, feitos durante a
  partida, esperam o serviço (nenhum dos dois sai antes); quando ele responde, a base carrega sem erro e sem segundo clique, e a
  mensagem sai uma vez só e recebe a resposta de sempre (o contêiner não tem a chave do Gemini);
- com o serviço no ar, uma falha de rede no gráfico (/api/painel): o pedido se repete sozinho, e o gráfico aparece sem erro;
- uma falha de rede na conversa (/api/exploration/interpret): a mensagem não é reenviada, e a conversa mostra o aviso;
- nenhuma indisponibilidade declarada e nenhum erro da página.
Nunca chama o provedor de IA.
"""
import os
import subprocess
import time
import urllib.request
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright
from ui_support import API, PRIVACIDADE, URL, accept_privacy, offline, open_chat

NOME = os.getenv("ADT_CONTEINER_NOME", "adt-api-ui")
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
INDISPONIVEL_NA_CONVERSA = "Assistente conversacional temporariamente indisponível"
CONTADOS = {"exame": "/api/inspect", "conversa sem dados": "/api/llm/interpret", "conversa local": "/api/exploration/interpret",
            "conversa com dados": "/api/llm/interpret-context", "gráfico": "/api/painel", "sessão": "/api/session"}


def docker(*args):
    subprocess.run(["docker", *args], check=True, capture_output=True, text=True, timeout=120)


def saudavel() -> bool:
    try:
        with LOCAL.open(API + "api/health", timeout=3) as resposta:
            return resposta.status == 200
    except OSError:
        return False


class Plataforma:
    """A plataforma do Cloud Run numa partida a frio, nos pedidos da página à API, até `soltar`: segura a verificação de saúde e
    recusa os demais (falha de rede no navegador). Depois de solta, nada muda nos pedidos."""

    def __init__(self, page):
        self.solta, self.seguras, self.recusadas = False, [], []
        page.route(API + "api/**", self.tratar)

    def tratar(self, rota):
        if self.solta:
            rota.fallback()
            return
        pedido = rota.request
        if pedido.method == "GET" and urlparse(pedido.url).path.endswith("/api/health"):
            self.seguras.append(rota)
            return
        self.recusadas.append(pedido.method + " " + urlparse(pedido.url).path)
        rota.abort("failed")

    def soltar(self):
        self.solta = True
        for rota in self.seguras:
            rota.fallback()
        self.seguras.clear()


def aperta(alvo):
    """Botões da área pelo teclado (a caixa da conversa pode ficar por cima), como nos outros roteiros."""
    alvo.scroll_into_view_if_needed()
    alvo.focus()
    alvo.press("Enter")


def falhar_uma_vez(page, rota_da_api: str) -> dict:
    """O próximo POST da rota falha por rede uma vez (a conexão cai); os demais seguem."""
    estado = {"falhas": 0}

    def tratar(rota):
        if rota.request.method == "POST" and not estado["falhas"]:
            estado["falhas"] += 1
            rota.abort("failed")
        else:
            rota.fallback()
    page.route(API + rota_da_api.lstrip("/"), tratar)
    estado["desfazer"] = lambda: page.unroute(API + rota_da_api.lstrip("/"), tratar)
    return estado


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        falhas, enviados = [], {chave: 0 for chave in CONTADOS}
        page.on("pageerror", lambda erro: falhas.append(str(erro)))

        def contar(pedido):
            caminho = urlparse(pedido.url).path
            for chave, rota in CONTADOS.items():
                if pedido.method == "POST" and caminho.endswith(rota):
                    enviados[chave] += 1
        page.on("request", contar)
        plataforma = Plataforma(page)

        # A partida a frio: o contêiner para e liga de novo, e a página abre antes de ele abrir a porta.
        docker("stop", "-t", "10", NOME)
        docker("start", NOME)
        ligado_em = time.monotonic()
        page.goto(URL)
        expect(page).to_have_title("Agente Diagnóstico Territorial da Força de Trabalho na Saúde")
        dialogo = page.get_by_role("dialog", name=PRIVACIDADE)
        expect(dialogo.get_by_test_id("conexao-iniciando")).to_be_visible(timeout=20000)   # o aviso de partida
        accept_privacy(page)
        chat = open_chat(page)
        chat.locator("#assistant-input").fill("Me conte uma curiosidade")
        chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
        area = page.get_by_test_id("area-de-analise")
        aperta(area.get_by_test_id("analise-fonte-brasil"))   # "Dados do Brasil", uma vez, durante a partida
        page.wait_for_timeout(3000)
        expect(page.get_by_test_id("conexao-iniciando")).to_be_visible()
        assert enviados["exame"] == enviados["conversa sem dados"] == enviados["sessão"] == 0, \
            ("na partida, os pedidos esperam o serviço antes de sair", enviados, plataforma.recusadas)
        expect(page.get_by_test_id("fonte-erro")).to_have_count(0)

        # O serviço abre a porta: a plataforma solta a verificação, e os pedidos que esperavam saem, uma vez cada.
        while not saudavel():
            assert time.monotonic() - ligado_em < 240, "o contêiner não ficou saudável em 240 s"
            page.wait_for_timeout(500)
        partida_s = time.monotonic() - ligado_em
        plataforma.soltar()
        expect(page.get_by_test_id("current-source")).to_be_visible(timeout=120000)
        expect(page.get_by_test_id("fonte-erro")).to_have_count(0)
        expect(page.get_by_test_id("conexao-iniciando")).to_have_count(0, timeout=30000)
        historico = chat.get_by_test_id("chat-historico")
        expect(historico.locator('[data-papel="aviso"]').last).to_contain_text(INDISPONIVEL_NA_CONVERSA, timeout=90000)
        assert enviados["conversa sem dados"] == 1, ("a mensagem da partida saiu uma vez só", enviados)
        assert enviados["exame"] >= 1 and enviados["sessão"] >= 1, enviados
        assert not any(rota.endswith(("/api/inspect", "/api/llm/interpret")) for rota in plataforma.recusadas), plataforma.recusadas

        # Com o serviço no ar, a conexão cai no pedido do gráfico: ele se repete sozinho, e o gráfico aparece sem erro.
        grafico = falhar_uma_vez(page, "/api/painel")
        antes = enviados["gráfico"]
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.status == 200, timeout=120000):
            aperta(area.get_by_test_id("analise-raiz-so-estados"))   # "Só os estados", na linha do Brasil, pede o gráfico
        expect(area.get_by_test_id("analise-erro")).to_have_count(0, timeout=30000)
        assert grafico["falhas"] == 1 and enviados["gráfico"] - antes >= 2, ("a falha e a repetição", grafico, enviados)
        grafico["desfazer"]()

        # A conexão cai na conversa: a mensagem não é reenviada, e a conversa mostra o aviso.
        conversa = falhar_uma_vez(page, "/api/exploration/interpret")
        local, contextual = enviados["conversa local"], enviados["conversa com dados"]
        mensagens = historico.get_by_test_id("chat-mensagem").count()
        chat.locator("#assistant-input").fill("Quantos médicos há no Amazonas?")
        chat.get_by_role("button", name="Enviar mensagem", exact=True).click()
        expect(chat.locator("#assistant-input")).to_be_enabled(timeout=60000)
        expect(historico.get_by_test_id("chat-mensagem")).to_have_count(mensagens + 2, timeout=30000)   # a pergunta e o aviso
        page.wait_for_timeout(6000)
        assert conversa["falhas"] == 1 and enviados["conversa local"] - local == 1, ("sem reenvio da conversa", enviados)
        assert enviados["conversa com dados"] == contextual, enviados
        conversa["desfazer"]()

        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)
        assert not falhas, falhas
        browser.close()
    print(f"PARTIDA PASS: a página abriu durante a partida (o contêiner respondeu {partida_s:.1f} s depois de ligado), com o aviso "
          f"de partida; \"Dados do Brasil\" e a mensagem esperaram o serviço e concluíram sem erro, sem segundo clique e com a "
          f"mensagem enviada uma vez; a falha de rede no gráfico se repetiu sozinha; a da conversa não foi reenviada. Recusados "
          f"pela plataforma imitada: {plataforma.recusadas or 'nenhum'}.")


if __name__ == "__main__":
    main()
