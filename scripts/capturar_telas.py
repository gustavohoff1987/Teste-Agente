"""Capturas das telas principais da página única com a base versionada, para a conferência visual (somente leitura).

Uso, de qualquer pasta do repositório, depois de "npm run build" em frontend/:
    python scripts/capturar_telas.py [--saida PASTA] [--canal chrome|chromium]

Sobe o servidor de testes (backend/tests/serve_ui_offline.py, sem transporte de IA) com a base versionada da raiz, percorre
as telas principais da página única (22/10/2026) e salva as capturas em .local/capturas/<data-hora>/, pasta ignorada pelo Git:
a abertura, os estados com a base do Brasil, os municípios do Amazonas e a comparação pedidos pela conversa, o Histórico, o
diálogo de Nova sessão, o painel "Colunas" de uma planilha de distritos e províncias (criada numa pasta temporária) e o
celular. Nada vai para o provedor de IA, nenhum dado é alterado e o servidor é encerrado no fim. Uma tela que falhar é
informada no fim, sem impedir as seguintes. Saída: 0 se todas as capturas foram feitas.
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
    from ui_support import accept_privacy, is_post, offline, open_chat, options_of, send

    feitas, falhas = [], []
    with tempfile.TemporaryDirectory(prefix="adt-capturas-") as temporaria, sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=canal)
        context = browser.new_context(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
        offline(context)
        page = context.new_page()
        erros = []
        page.on("pageerror", lambda erro: erros.append(str(erro)))

        def tela(nome, acao):
            """Executa os passos da tela e salva a captura da página inteira."""
            try:
                acao()
                page.wait_for_timeout(900)  # transições curtas do gráfico
                caminho = saida / (nome + ".png")
                page.screenshot(path=str(caminho), full_page=True)
                feitas.append(caminho.name)
                print("   ok:", caminho.name, flush=True)
            except Exception as erro:  # noqa: BLE001 — a tela seguinte ainda é útil para a conferência
                falhas.append(f"{nome}: {str(erro).splitlines()[0]}")
                print("   FALHOU:", falhas[-1], flush=True)

        def grafico(acao, condicao=lambda opcoes: True):
            """Executa a ação e espera o gráfico com o pedido correspondente ao motor (/api/painel)."""
            with page.expect_response(lambda r: is_post(r, "/api/painel") and condicao(options_of(r.request)), timeout=180000):
                acao()

        def minimizar_conversa():
            chat = page.get_by_test_id("painel-chat")
            if chat.get_attribute("data-minimizada") == "false":
                chat.get_by_test_id("painel-chat-minimizar").click()

        def abertura():
            page.goto(url)
            accept_privacy(page)
            expect(page.get_by_test_id("painel-chat")).to_have_attribute("data-ampla", "true")

        def estados():
            grafico(lambda: page.get_by_test_id("fonte-brasil").click(), lambda opcoes: opcoes.get("nivel") == "estados")
            expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=90000)

        def amazonas():
            grafico(lambda: send(page, "Mostre o Amazonas"),
                    lambda opcoes: opcoes.get("base", {}).get("municipios", {}).get("estados") == ["13"])

        def comparacao():
            grafico(lambda: send(page, "Compare Manaus e Tefé"), lambda opcoes: bool(opcoes.get("comparar")))

        def historico():
            minimizar_conversa()
            grafico(lambda: page.get_by_test_id("nav-new-analysis").click(), lambda opcoes: opcoes.get("nivel") == "estados")
            page.get_by_test_id("nav-history").click()
            expect(page.get_by_test_id("historico-item")).to_have_count(2, timeout=30000)

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
            with page.expect_file_chooser() as escolha:
                page.get_by_test_id("fonte-arquivo").click()
            escolha.value.set_files(str(planilha))
            painel = page.get_by_test_id("colunas-painel")
            expect(painel).to_be_visible(timeout=60000)
            painel.get_by_test_id("colunas-territory").select_option("distrito")
            expect(painel.get_by_test_id("colunas-grupo_territorial").locator("option").nth(1)).to_have_text(
                "provincia (sugerida)", timeout=30000)
            painel.get_by_test_id("colunas-grupo_territorial").select_option("provincia")

        def celular():
            page.get_by_test_id("fonte-cancelar-preparo").click()
            open_chat(page)
            page.set_viewport_size({"width": 390, "height": 844})

        tela("01-abertura", abertura)
        tela("02-estados", estados)
        tela("03-amazonas-pela-conversa", amazonas)
        tela("04-comparacao-pela-conversa", comparacao)
        tela("05-historico", historico)
        tela("06-nova-sessao", nova_sessao)
        tela("07-planilha-colunas", colunas)
        tela("08-celular", celular)
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
