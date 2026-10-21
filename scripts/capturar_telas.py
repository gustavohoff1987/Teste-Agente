"""Capturas das telas principais com a base versionada, para a conferência visual (somente leitura).

Uso, de qualquer pasta do repositório, depois de "npm run build" em frontend/:
    python scripts/capturar_telas.py [--saida PASTA] [--canal chrome|chromium]

Sobe o servidor de testes (backend/tests/serve_ui_offline.py, sem transporte de IA) com a base versionada
da raiz, percorre as telas principais e salva as capturas em .local/capturas/<data-hora>/, pasta ignorada
pelo Git. Nada vai para o provedor de IA, nenhum dado é alterado e o servidor é encerrado no fim. Só nas
capturas, a caixa de mensagem deixa de ficar presa ao rodapé, para não cobrir o conteúdo. Uma tela que
falhar é informada no fim, sem impedir as seguintes. Saída: 0 se todas as capturas foram feitas.
"""
import argparse
import os
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "frontend" / "dist" / "index.html"
sys.path.insert(0, str(ROOT / "backend" / "tests"))
DOCA_SOLTA = ".conversation-dock { position: static !important; }"


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
    from ui_support import execute_analysis, expand, offline, select, workspace

    feitas, falhas = [], []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, channel=canal)
        context = browser.new_context(viewport={"width": 1366, "height": 900}, reduced_motion="reduce")
        offline(context)
        page = context.new_page()
        erros = []
        page.on("pageerror", lambda erro: erros.append(str(erro)))
        preparacao = page.locator("#preparacao-conversacional")
        resultados = page.locator("#resultados")

        def tela(nome, acao):
            """Executa os passos da tela e salva a captura da página inteira."""
            try:
                acao()
                page.wait_for_timeout(700)  # animações curtas de gráficos e mapa
                caminho = saida / (nome + ".png")
                page.screenshot(path=str(caminho), full_page=True)
                feitas.append(caminho.name)
                print("   ok:", caminho.name, flush=True)
            except Exception as erro:  # noqa: BLE001 — a tela seguinte ainda é útil para a conferência
                falhas.append(f"{nome}: {str(erro).splitlines()[0]}")
                print("   FALHOU:", falhas[-1], flush=True)

        def escolher_periodo(rotulo):
            expand(preparacao.get_by_label("Escolher períodos da análise"))
            preparacao.get_by_role("button", name=rotulo, exact=True).click()

        def inicio():
            page.goto(url)
            page.add_style_tag(content=DOCA_SOLTA)
            page.get_by_role("button", name="Li e concordo", exact=True).click()

        def densidade():
            page.get_by_role("button", name="Usar dados do Brasil").click()
            expect(page.get_by_test_id("current-source")).to_contain_text("Dados do Brasil", timeout=90000)
            select(page, "Densidade")
            expect(preparacao.get_by_test_id("scope-summary")).to_have_text("Todos os municípios", timeout=90000)
            escolher_periodo("junho de 2024")
            expect(preparacao.get_by_test_id("analysis-summary")).to_be_visible(timeout=90000)

        def resultado_mapa():
            botao = preparacao.get_by_role("button", name="Calcular e mostrar resultado", exact=True)
            expect(botao).to_be_enabled(timeout=90000)
            execute_analysis(page, botao)
            expect(resultados.get_by_test_id("result-title")).to_be_visible(timeout=90000)
            resultados.get_by_role("tab", name="Mapa", exact=True).click()

        def aba(nome):
            return lambda: resultados.get_by_role("tab", name=nome, exact=True).click()

        def celular():
            page.set_viewport_size({"width": 390, "height": 844})

        def evolucao():
            page.set_viewport_size({"width": 1366, "height": 900})
            workspace(page, "preparation")
            select(page, "Evolução temporal")
            expect(preparacao.get_by_test_id("scope-summary")).to_have_text("Brasil (total nacional)", timeout=90000)
            expect(preparacao.get_by_test_id("scope-loading")).to_have_count(0, timeout=90000)
            expand(preparacao.get_by_label("Escolher períodos da análise"))

        def abrangencia():
            preparacao.get_by_test_id("period-done").click()
            expand(preparacao.get_by_test_id("territory-toggle"))
            # Lista vertical da abrangência (Brasil, estados e municípios), com o grupo do Amazonas aberto.
            lista = page.get_by_role("region", name="Seleção territorial compartilhada")
            expect(lista.get_by_test_id("territory-option-todos-municipios")).to_be_enabled(timeout=90000)
            grupo = lista.get_by_test_id("territory-group-toggle-13")
            if grupo.count() and grupo.get_attribute("aria-expanded") != "true":
                grupo.click()

        def distancias():
            select(page, "Análise espacial")
            expect(preparacao.get_by_test_id("analysis-summary")).to_be_visible(timeout=90000)
            expect(preparacao.get_by_test_id("scope-loading")).to_have_count(0, timeout=90000)

        def escolhas_faltantes():
            # Base oficial: sem condições avançadas; o clique em "Calcular" nomeia as escolhas que faltam.
            preparacao.get_by_role("button", name="Calcular e mostrar resultado", exact=True).click()
            expect(preparacao.get_by_test_id("missing-choices")).to_be_visible(timeout=90000)

        tela("01-inicio", inicio)
        tela("02-densidade-preparacao", densidade)
        tela("03-densidade-resultado-mapa", resultado_mapa)
        tela("04-densidade-resultado-graficos", aba("Gráficos"))
        tela("05-densidade-resultado-tabela", aba("Tabela"))
        tela("06-densidade-resultado-celular", celular)
        tela("07-evolucao-escolha-de-periodos", evolucao)
        tela("07b-evolucao-abrangencia-territorial", abrangencia)
        tela("08-analise-espacial-preparacao", distancias)
        tela("09-escolhas-faltantes", escolhas_faltantes)
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
