"""Estados da conexão (seção 10 do comando de implantação, 01/11/2026), com a interface como no GitHub Pages e o serviço no
contêiner (suíte "conteiner" do run_ui_checks.py; servidor serve_ui_conteiner.py, que sobe a imagem com 1 CPU e 2 GiB).

Percorre, com o serviço de verdade parado e restabelecido (docker stop, start e restart):
- A. serviço inacessível na abertura: a interface abre pelo Pages; a tentativa curta antes; o título "Serviço temporariamente
  indisponível" e o texto institucional, sem código HTTP, mensagens do provedor ou da infraestrutura;
- B. antes de declarar a indisponibilidade, o aviso de que o serviço está iniciando;
- G. o botão "Tentar novamente" (uma verificação na hora); a pausa das tentativas automáticas com a aba oculta e a verificação
  ao voltar; com o serviço de volta, a tentativa automática restabelece sozinha, com o aviso breve;
- F. erros de validação com a mensagem própria (arquivo malformado, pelo backend; arquivo acima de 15 MB, antes do envio);
- D. a conversa sem o Gemini (o contêiner não tem chave): o aviso cordial de sempre, na conversa;
- C. o serviço ocupado (resposta legível com `ocupado`): o aviso de ocupado, sem a indisponibilidade; no gráfico, a nova
  tentativa sozinha;
- E. o reinício do contêiner com a sessão aberta: a sessão se perde (sessões em memória), e a tela mostra o aviso de sessão
  expirada ou indisponível, distinto da indisponibilidade do serviço.
Nunca chama o provedor de IA.
"""
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright
from ui_support import API, CORS, PRIVACIDADE, URL, accept_privacy, offline, send

NOME = os.getenv("ADT_CONTEINER_NOME", "adt-api-ui")
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))
TITULO_A = "Serviço temporariamente indisponível"
TEXTO_A = ("O Agente Diagnóstico Territorial da Força de Trabalho na Saúde está temporariamente indisponível. Por favor, tente "
           "acessar novamente mais tarde. Agradecemos sua compreensão.")
EXPIRADA = "A sessão anterior expirou ou ficou indisponível no servidor."
TECNICO = re.compile(r"HTTP|\b[45]\d\d\b|Google|Cloud Run|Traceback|R\$|US\$|uvicorn|docker", re.IGNORECASE)
ESTADOS = ("conexao-iniciando", "conexao-indisponivel", "conexao-ocupado", "conexao-restabelecida")
# A sequência dos estados que a página mostrou, desde o carregamento (as trocas rápidas também ficam registradas).
OBSERVAR = """(() => { window.__conexao = []; const ids = %s;
  const ver = () => { for (const el of document.querySelectorAll('[data-testid]')) { const id = el.dataset.testid;
    if (ids.includes(id) && window.__conexao[window.__conexao.length - 1] !== id) window.__conexao.push(id); } };
  new MutationObserver(ver).observe(document, {subtree: true, childList: true}); })()""" % list(ESTADOS)
VISIBILIDADE = """estado => { Object.defineProperty(document, 'visibilityState', {configurable: true, get: () => estado});
  document.dispatchEvent(new Event('visibilitychange')); }"""


def docker(*args):
    subprocess.run(["docker", *args], check=True, capture_output=True, text=True, timeout=120)


def saudavel() -> bool:
    try:
        with LOCAL.open(API + "api/health", timeout=3) as resposta:
            return resposta.status == 200
    except OSError:
        return False


def esperar_saude(prazo=280):
    fim = time.monotonic() + prazo
    while time.monotonic() < fim:
        if saudavel():
            return
        time.sleep(0.5)
    raise AssertionError("o contêiner não voltou em " + str(prazo) + " s")


def main():
    with tempfile.TemporaryDirectory(prefix="adt-conexao-") as temporaria, sync_playwright() as p:
        pasta = Path(temporaria)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        offline(context)
        page = context.new_page()
        page.add_init_script(OBSERVAR)
        falhas, saude = [], []
        page.on("pageerror", lambda erro: falhas.append(str(erro)))
        page.on("request", lambda pedido: saude.append(time.monotonic()) if pedido.url.endswith("/api/health") else None)
        estados = lambda: page.evaluate("window.__conexao || []")  # noqa: E731

        def esperar_verificacao(antes, prazo=8.0):
            fim = time.monotonic() + prazo
            while len(saude) <= antes and time.monotonic() < fim:
                page.wait_for_timeout(200)
            return len(saude) > antes

        # A e B. O serviço parado na abertura: a interface abre, avisa que o serviço está iniciando, tenta de novo e só então
        # mostra a indisponibilidade, com o texto institucional.
        docker("stop", "-t", "10", NOME)
        page.goto(URL)
        expect(page).to_have_title("Agente Diagnóstico Territorial da Força de Trabalho na Saúde")
        dialogo = page.get_by_role("dialog", name=PRIVACIDADE)
        expect(dialogo).to_be_visible()
        indisponivel = dialogo.get_by_test_id("conexao-indisponivel")
        expect(indisponivel).to_be_visible(timeout=30000)
        assert estados()[:2] == ["conexao-iniciando", "conexao-indisponivel"], estados()
        assert len(saude) >= 2, "a tentativa curta antes de declarar a indisponibilidade"
        expect(indisponivel.get_by_role("heading")).to_have_text(TITULO_A)
        expect(indisponivel.get_by_test_id("conexao-texto")).to_have_text(TEXTO_A)
        expect(indisponivel).not_to_contain_text(TECNICO)
        expect(page.get_by_test_id("pagina-banner")).to_be_attached()  # a página do Pages abriu inteira

        # G. O botão verifica na hora; com a aba oculta, as tentativas automáticas esperam; ao voltar, a verificação sai.
        antes = len(saude)
        indisponivel.get_by_test_id("conexao-tentar").click()
        assert esperar_verificacao(antes), "o botão verifica na hora"
        expect(indisponivel).to_be_visible()
        page.evaluate(VISIBILIDADE, "hidden")
        expect(indisponivel.get_by_test_id("conexao-nota")).to_contain_text("quando esta aba voltar a ficar à vista")
        oculta = len(saude)
        page.wait_for_timeout(12000)
        assert len(saude) == oculta, "nenhuma tentativa automática com a aba oculta"
        page.evaluate(VISIBILIDADE, "visible")
        assert esperar_verificacao(oculta, 4), "a tentativa vencida sai quando a aba volta"

        # G. O serviço volta: a tentativa automática restabelece sozinha, com o aviso breve.
        docker("start", NOME)
        esperar_saude()
        expect(indisponivel).to_have_count(0, timeout=150000)
        assert "conexao-restabelecida" in estados(), estados()
        accept_privacy(page)

        # F. Erros de validação: a mensagem própria, nunca a de indisponibilidade.
        fonte = page.get_by_test_id("fonte-barra")
        area = page.get_by_test_id("area-de-analise")

        def aperta(alvo):
            """Botões da área pelo teclado (a caixa da conversa pode ficar por cima), como nos outros roteiros."""
            alvo.scroll_into_view_if_needed()
            alvo.focus()
            alvo.press("Enter")

        def enviar(caminho):
            aperta(area.get_by_test_id("analise-fonte-arquivo"))
            janela = page.get_by_test_id("envio-de-dados")
            with page.expect_file_chooser() as escolha:
                janela.get_by_test_id("envio-escolher-arquivo").click()
            escolha.value.set_files(str(caminho))
        quebrado = pasta / "quebrado.xlsx"
        quebrado.write_bytes(b"isto nao e uma planilha")
        enviar(quebrado)
        expect(fonte.get_by_test_id("fonte-erro")).to_contain_text("Não foi possível interpretar este arquivo Excel", timeout=60000)
        expect(fonte.get_by_test_id("fonte-erro")).not_to_contain_text(TECNICO)
        grande = pasta / "grande.csv"
        with grande.open("wb") as arquivo:
            arquivo.truncate(15_000_001)
        enviar(grande)
        expect(fonte.get_by_test_id("fonte-erro")).to_have_text(
            "Arquivo acima de 15 MB, o limite desta versão; a planilha não foi processada.")
        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)
        fonte.get_by_test_id("fonte-cancelar-preparo").click()
        expect(fonte.get_by_test_id("fonte-erro")).to_have_count(0)

        # D. A conversa sem o Gemini: o aviso cordial de sempre, na conversa, sem a indisponibilidade do serviço.
        chat = page.get_by_test_id("painel-chat")
        with page.expect_response(lambda r: r.url.endswith("/api/llm/interpret"), timeout=60000) as conversa:
            send(page, "Me conte uma curiosidade")
        assert conversa.value.status == 200 and "indisponibilidade" in conversa.value.json()
        aviso = chat.get_by_test_id("chat-historico").locator('[data-papel="aviso"]').last
        expect(aviso).to_contain_text("Assistente conversacional temporariamente indisponível")
        expect(chat).not_to_contain_text(TECNICO)
        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)

        # C. Ocupado: a resposta legível do serviço no limite mostra o aviso de ocupado, sem a indisponibilidade.
        texto_ocupado = "O serviço está ocupado neste teste. Aguarde alguns segundos e tente novamente."
        corpo = '{"detail": "%s", "ocupado": true, "tente_em": 1}' % texto_ocupado
        page.route("**/api/inspect", lambda rota: rota.fulfill(status=503, body=corpo, content_type="application/json",
                                                               headers=CORS), times=1)
        aperta(area.get_by_test_id("analise-fonte-brasil"))
        expect(page.get_by_test_id("conexao-ocupado")).to_have_text(texto_ocupado, timeout=30000)
        expect(fonte.get_by_test_id("fonte-erro")).to_have_text(texto_ocupado)
        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)
        fonte.get_by_test_id("fonte-cancelar-preparo").click()
        aperta(area.get_by_test_id("analise-fonte-brasil"))  # a pessoa tenta de novo: a base carrega e o aviso sai
        expect(page.get_by_test_id("current-source")).to_be_visible(timeout=120000)
        expect(page.get_by_test_id("conexao-ocupado")).to_have_count(0)
        # No gráfico, a nova tentativa sai sozinha, depois do tempo que o serviço indica.
        page.route("**/api/painel", lambda rota: rota.fulfill(status=503, body=corpo, content_type="application/json",
                                                              headers=CORS), times=1)
        aperta(area.get_by_test_id("analise-nivel-estados"))
        with page.expect_response(lambda r: r.url.endswith("/api/painel") and r.status == 200, timeout=120000):
            aperta(area.get_by_test_id("analise-marcar-todos"))
        expect(area.get_by_test_id("analise-erro")).to_have_count(0, timeout=30000)
        expect(page.get_by_test_id("conexao-ocupado")).to_have_count(0, timeout=30000)

        # E. Reinício do contêiner com a sessão aberta: a sessão se perde (sessões em memória). Na consulta seguinte (a cada
        # 30 s), a tela recarrega com o aviso de sessão expirada ou indisponível, distinto da indisponibilidade do serviço, e
        # uma sessão nova começa normalmente.
        docker("restart", "-t", "10", NOME)
        esperar_saude()
        expect(page.get_by_test_id("session-ended-notice")).to_contain_text(EXPIRADA, timeout=75000)
        dialogo = page.get_by_role("dialog", name=PRIVACIDADE)
        expect(dialogo.get_by_test_id("conexao-indisponivel")).to_have_count(0, timeout=30000)
        accept_privacy(page)
        with page.expect_response(lambda r: r.url.endswith("/api/session/interact"), timeout=60000) as interacao:
            aperta(area.get_by_test_id("analise-fonte-brasil"))
        assert interacao.value.status == 200, "a sessão nova começa normalmente"
        expect(page.get_by_test_id("current-source")).to_be_visible(timeout=120000)
        assert not falhas, falhas
        browser.close()
    print("CONEXÃO PASS: indisponível na abertura com a tentativa curta e o aviso de partida, botão, pausa com a aba oculta, "
          "restabelecimento automático, erros de validação, conversa sem o Gemini, ocupado (com a nova tentativa do gráfico) "
          "e a sessão perdida no reinício do contêiner, com o aviso próprio.")


if __name__ == "__main__":
    main()
