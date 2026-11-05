"""A interface como no GitHub Pages e o serviço como no Cloud Run (suíte "conteiner" do run_ui_checks.py; 01/11/2026).

A página vem de /Teste-Agente/ (o build com ADT_BASE_DA_PAGINA) e chama o serviço noutro endereço (VITE_API_BASE_URL), com
CORS, como em https://gustavohoff1987.github.io/Teste-Agente/ e o Cloud Run. Confere:
- os recursos estáticos (scripts, estilos e a fonte embutida) sob /Teste-Agente/, sem nenhum recurso de fora e sem falhas;
- o título com o nome oficial completo e a separação imperceptível: os pedidos ao serviço respondem, inclusive os que levam
  o cabeçalho da sessão (com a pré-verificação do CORS);
- a base do Brasil, o gráfico dos estados (JSON do motor) e o CSV da análise em exibição;
- o modelo de planilha (XLSX) baixado do serviço por outro endereço;
- no serviço: a documentação da API desligada (/docs, /redoc, /openapi.json) e o CORS só para a origem da página.
Os demais recursos (envio de planilhas, mapas e relatórios) passam pelos roteiros da página única nesta mesma suíte.
Desde 04/11/2026, o caminho esperado vem de ADT_PAGINA_BASE (padrão /Teste-Agente/); na suíte "conteiner-raiz", é "/", como
em https://diagnostico-territorial.github.io/.
"""
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import expect, sync_playwright
from ui_support import API, PRIVACIDADE, URL, accept_privacy, fonte_embutida_carregada, offline

BASE = urlparse(URL).path or "/"  # /Teste-Agente/ ou /
ESPERADA = os.getenv("ADT_PAGINA_BASE", "/Teste-Agente/")
ORIGEM = "{0.scheme}://{0.netloc}".format(urlparse(URL))


def main():
    assert BASE == ESPERADA, f"a suíte serve a página como no GitHub Pages ({ESPERADA}): {BASE}"
    assert urlparse(API).netloc != urlparse(URL).netloc, "o serviço fica noutro endereço"
    with tempfile.TemporaryDirectory(prefix="adt-hospedagem-") as temporaria, sync_playwright() as p:
        pasta = Path(temporaria)
        browser = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL", "chrome"))
        context = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
        offline(context)
        page = context.new_page()
        falhas, respostas, recusados = [], [], []
        page.on("pageerror", lambda erro: falhas.append(str(erro)))
        page.on("response", lambda resposta: None if resposta.url.endswith("/favicon.ico") else
                respostas.append((resposta.url, resposta.status)))
        # Pedidos abortados pela própria página (um gráfico substituído, o download que encerra a navegação) não são falhas.
        page.on("requestfailed", lambda pedido: None if "ERR_ABORTED" in (pedido.failure or "") else
                recusados.append((pedido.url, pedido.failure)))
        page.goto(URL)
        expect(page).to_have_title("Agente Diagnóstico Territorial da Força de Trabalho na Saúde")
        expect(page.get_by_role("dialog", name=PRIVACIDADE)).to_be_visible()

        # Recursos estáticos: todos sob o caminho da página, servidos sem erro; a fonte embutida carregou.
        estaticos = [(url, status) for url, status in respostas if url.startswith(ORIGEM)]
        assert estaticos and all(urlparse(url).path.startswith(BASE) for url, _ in estaticos), estaticos
        assert all(status < 400 for _, status in estaticos), estaticos
        assert any(re.search(r"/assets/.+\.js$", url) for url, _ in estaticos), "o script do build"
        assert any(re.search(r"/assets/.+\.css$", url) for url, _ in estaticos), "a folha de estilos do build"
        assert page.evaluate("[...document.scripts].every(s => !s.src || new URL(s.src).pathname.startsWith('%s'))" % BASE)
        assert fonte_embutida_carregada(page), "a Inter embutida, servida pelo próprio Pages"
        assert all(urlparse(url).hostname in ("127.0.0.1", "localhost") for url, _ in respostas), "nenhum recurso de fora"

        # O serviço noutro endereço: a saúde respondeu na abertura, sem aviso de conexão.
        assert any(url == API + "api/health" and status == 200 for url, status in respostas), respostas[-10:]
        expect(page.get_by_test_id("conexao-indisponivel")).to_have_count(0)
        accept_privacy(page)

        # A base do Brasil e o gráfico dos estados, pelo serviço noutro endereço (com a sessão: pré-verificação do CORS).
        area = page.get_by_test_id("area-de-analise")

        def aperta(alvo):
            alvo.scroll_into_view_if_needed()
            alvo.focus()
            alvo.press("Enter")
        with page.expect_response(lambda r: r.url == API + "api/inspect", timeout=120000) as inspecao:
            aperta(area.get_by_test_id("analise-fonte-brasil"))
        assert inspecao.value.status == 200 and inspecao.value.json()["catalog"]["integridade"] == "verificada"
        expect(page.get_by_test_id("current-source")).to_be_visible(timeout=60000)
        # Os estados como unidades (05/11/2026, a seleção unificada): sem nada marcado, a unidade Estados marca todos e pede o gráfico.
        with page.expect_response(lambda r: r.url == API + "api/painel", timeout=120000) as painel:
            aperta(area.get_by_test_id("analise-nivel-estados"))
        assert painel.value.status == 200, painel.value.text()[:500]
        assert painel.value.request.headers.get("x-adt-session"), "o gráfico leva a sessão, com a pré-verificação"
        assert len([item for item in painel.value.json()["itens"] if item.get("tipo") == "estado"]) == 27
        assert painel.value.headers.get("access-control-allow-origin") == ORIGEM

        # O CSV da análise em exibição (feito na própria página) e o modelo de planilha, baixado do serviço.
        page.get_by_test_id("nav-new-session").click()
        dialogo = page.get_by_test_id("new-session-confirmation")
        with page.expect_download() as baixado:
            dialogo.get_by_test_id("session-export-csv").click()
        csv = (pasta / "analise.csv")
        baixado.value.save_as(csv)
        assert csv.read_bytes().startswith(b"\xef\xbb\xbf") and b";" in csv.read_bytes()[:200]
        dialogo.get_by_test_id("cancel-new-session").click()
        aperta(page.get_by_test_id("fonte-barra").get_by_test_id("fonte-trocar"))
        aperta(area.get_by_test_id("analise-troca-fonte").get_by_test_id("analise-fonte-arquivo"))
        janela = page.get_by_test_id("envio-de-dados")
        modelo = janela.get_by_test_id("envio-modelo-baixar")
        assert modelo.get_attribute("href") == API + "api/modelo/estrutura-recomendada"
        with page.expect_download() as baixado:
            modelo.click()
        assert baixado.value.suggested_filename == "modelo_territorial_recomendado.xlsx"
        planilha = pasta / "modelo.xlsx"
        baixado.value.save_as(planilha)
        assert planilha.read_bytes()[:2] == b"PK"
        janela.get_by_test_id("envio-cancelar").click()

        # No serviço: a documentação da API desligada e o CORS só para a origem da página.
        for caminho in ("docs", "redoc", "openapi.json"):
            assert context.request.get(API + caminho).status == 404, caminho
        estranha = context.request.get(API + "api/health", headers={"Origin": "https://exemplo.invalid"})
        assert estranha.status == 200 and "access-control-allow-origin" not in estranha.headers
        propria = context.request.get(API + "api/health", headers={"Origin": ORIGEM})
        assert propria.headers.get("access-control-allow-origin") == ORIGEM

        assert not recusados, recusados
        assert not falhas, falhas
        browser.close()
    print(f"HOSPEDAGEM PASS: recursos sob {BASE}, fonte embutida, nome oficial no título, serviço noutro endereço com "
          "CORS (base, gráfico com a sessão, CSV e o modelo XLSX), documentação da API desligada e CORS só da origem da página.")


if __name__ == "__main__":
    main()
