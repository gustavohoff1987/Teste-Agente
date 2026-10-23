"""Executor único das jornadas de navegador: o mesmo comando na máquina local e no CI.

Cada roteiro roda em processo próprio, e uma falha não interrompe os seguintes. Assim, nenhum
problema fica escondido atrás de outro. No final, um resumo lista todos os resultados, e o
código de saída é 1 se algum roteiro falhou.

Uso, na raiz do repositório, depois de `npm run build` em frontend/:
    python backend/tests/run_ui_checks.py                        # todas as suítes
    python backend/tests/run_ui_checks.py --suite bloco1         # só uma suíte (pode repetir)
    python backend/tests/run_ui_checks.py --roteiro ui_pagina_unica.py    # só os roteiros indicados (pode repetir)
    python backend/tests/run_ui_checks.py --listar               # suítes e roteiros registrados

Navegador: ADT_BROWSER_CHANNEL (o padrão dos roteiros é "chrome"; sem o Google Chrome
instalado, use "chromium"). Nenhuma suíte chama o provedor real de IA. A suíte
"base-versionada" usa os arquivos da raiz conferidos pelo manifesto, somente em leitura.

Todo roteiro ui_*.py ativo em backend/tests precisa estar registrado em SUITES. A verificação
de governança do CI recusa roteiros de navegador que não rodam (.github/scripts/verificar_governanca.py).
"""
import argparse
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TESTS = ROOT / "backend" / "tests"
TIMEOUT = 20 * 60  # segundos por roteiro; os passos internos têm esperas próprias

# Página única (22/10/2026): os roteiros do fluxo clássico saíram (ver backend/tests/legado/README.md). Os nomes das suítes
# continuam os mesmos, porque o .github/workflows/ci.yml os chama.
# catalogo: "bloco1" é a fixture sintética; "repositorio" é a base versionada.
# servidor: "offline" (sem transporte de IA) ou "gemini-simulado" (só o transporte é simulado).
SUITES = {
    "conversa": {
        "descricao": "Conversa agindo no gráfico só pelos canais locais (catálogo sintético do Bloco 1, sem provedor de IA)",
        "catalogo": "bloco1", "servidor": "offline",
        "roteiros": [("ui_conversa_grafico.py", {})],
    },
    "bloco1": {
        "descricao": "Página única com catálogo sintético: abertura, estados, Histórico, Nova análise, planilha enviada, "
                     "celular, a área de análise (famílias, territórios em lista, funções e detalhes) e o modo escuro "
                     "(o navegador no escuro; a impressão clara)",
        "catalogo": "bloco1", "servidor": "offline",
        "roteiros": [("ui_pagina_unica.py", {}), ("ui_area_de_analise.py", {}), ("ui_modo_escuro.py", {})],
    },
    "gemini-simulado": {
        "descricao": "Conversa agindo no gráfico com um transporte Gemini simulado: ambiguidade em botões e nada da base ao provedor",
        "catalogo": "bloco1", "servidor": "gemini-simulado",
        "roteiros": [("ui_conversa_grafico.py", {})],
    },
    "base-versionada": {
        "descricao": "Página única com a base Brasil versionada (27 estados, 5.570 municípios, 22 competências) e o mapa, "
                     "a segunda vista do gráfico, com as coordenadas da sede municipal",
        "catalogo": "repositorio", "servidor": "offline",
        "roteiros": [("ui_pagina_unica.py", {"ADT_BLOCK1_REAL": "1"}), ("ui_area_de_analise.py", {"ADT_BLOCK1_REAL": "1"}),
                     ("ui_mapa.py", {"ADT_BLOCK1_REAL": "1"})],
    },
}
SERVERS = {"offline": "serve_ui_offline.py", "gemini-simulado": "serve_ui_fake_gemini.py"}
FIXTURES = {"bloco1": "prepare_block1_catalog.py"}
GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # 127.0.0.1 nunca passa por proxy


def registered_scripts():
    """Roteiros que o executor conhece; usado pela verificação de governança."""
    return sorted({name for suite in SUITES.values() for name, _ in suite["roteiros"]})


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def base_env():
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    env["NO_PROXY"] = env["no_proxy"] = ",".join(filter(None, ["127.0.0.1", "localhost", env.get("NO_PROXY", "")]))
    for key in ("ADT_BRASIL_DATA_DIR", "ADT_BRASIL_DATA_VERSION", "ADT_BLOCK1_REAL", "ADT_FAKE_GEMINI_LOG", "ADT_UI_URL"):
        env.pop(key, None)  # cada suíte declara explicitamente a sua origem de dados
    return env


def start_server(kind, env, log_path):
    port = free_port()
    env = dict(env, ADT_UI_PORT=str(port))
    log = open(log_path, "w", encoding="utf-8")
    process = subprocess.Popen([sys.executable, str(TESTS / SERVERS[kind])], cwd=ROOT, env=env,
                               stdout=log, stderr=subprocess.STDOUT)
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"o servidor {SERVERS[kind]} encerrou com código {process.returncode}")
        try:
            with LOCAL.open(f"http://127.0.0.1:{port}/api/health", timeout=2) as response:
                if response.status == 200:
                    return process, port, log
        except OSError:
            time.sleep(0.3)
    stop_server(process, log)
    raise RuntimeError(f"o servidor {SERVERS[kind]} não respondeu em 90 s")


def stop_server(process, log):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    log.close()


def tail(path, lines=60):
    try:
        return "\n".join(Path(path).read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def run_suite(name, workdir, only=None):
    suite = SUITES[name]
    roteiros = [item for item in suite["roteiros"] if not only or item[0] in only]
    env = base_env()
    results = []
    if suite["catalogo"] in FIXTURES:
        catalog = workdir / ("catalogo-" + name)
        prepared = subprocess.run([sys.executable, str(TESTS / FIXTURES[suite["catalogo"]]), str(catalog)],
                                  cwd=ROOT, env=env).returncode
        if prepared != 0:
            message = f"catálogo de teste não foi preparado ({FIXTURES[suite['catalogo']]}, código {prepared})"
            print(message, flush=True)
            return [(name, script, "falhou", 0.0, message) for script, _ in roteiros]
        env["ADT_BRASIL_DATA_DIR"] = str(catalog)
    if suite["servidor"] == "gemini-simulado":
        env["ADT_FAKE_GEMINI_LOG"] = str(workdir / ("gemini-simulado-" + name + ".jsonl"))
    server_log = workdir / ("servidor-" + name + ".log")
    try:
        process, port, log = start_server(suite["servidor"], env, server_log)
    except (RuntimeError, OSError) as exc:
        message = "servidor não iniciou: " + str(exc)
        print(message + "\n" + tail(server_log), flush=True)
        return [(name, script, "falhou", 0.0, message) for script, _ in roteiros]
    try:
        for script, extra in roteiros:
            label = script + (" (" + ", ".join(f"{k}={v}" for k, v in extra.items()) + ")" if extra else "")
            print(f"::group::{name} · {label}" if GITHUB else f"\n===== {name} · {label}", flush=True)
            started = time.monotonic()
            try:
                code = subprocess.run([sys.executable, str(TESTS / script)], cwd=ROOT, timeout=TIMEOUT,
                                      env=dict(env, ADT_UI_URL=f"http://127.0.0.1:{port}/", **extra)).returncode
                status, detail = ("passou", "") if code == 0 else ("falhou", f"código de saída {code}")
            except subprocess.TimeoutExpired:
                status, detail = "falhou", f"tempo esgotado ({TIMEOUT} s)"
            elapsed = time.monotonic() - started
            if GITHUB:
                print("::endgroup::", flush=True)
            if status != "passou":
                print(f"--- últimas linhas do servidor ({SERVERS[suite['servidor']]}):\n" + tail(server_log), flush=True)
                if GITHUB:
                    print(f"::error title=Jornada de navegador falhou::{name} · {label}: {detail}", flush=True)
            results.append((name, label, status, elapsed, detail))
    finally:
        stop_server(process, log)
    return results


def report(results):
    lines = ["| Suíte | Roteiro | Resultado | Tempo |", "|---|---|---|---|"]
    for suite, label, status, elapsed, detail in results:
        mark = "✅ passou" if status == "passou" else "❌ " + (detail or status)
        lines.append(f"| {suite} | `{label}` | {mark} | {elapsed:.0f} s |")
    failed = sum(1 for item in results if item[2] != "passou")
    title = (f"**{failed} de {len(results)} roteiros falharam.**" if failed
             else f"**Todos os {len(results)} roteiros passaram.**")
    print("\nResumo das jornadas de navegador\n" + "\n".join(lines) + "\n" + title, flush=True)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write("### Jornadas de navegador\n\n" + "\n".join(lines) + "\n\n" + title + "\n")
    return failed


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--suite", action="append", choices=sorted(SUITES), help="suíte a executar (repetível)")
    parser.add_argument("--roteiro", action="append",
                        help="roteiro a executar, nas suítes em que está registrado (repetível)")
    parser.add_argument("--listar", action="store_true", help="mostra suítes e roteiros registrados")
    args = parser.parse_args()
    registrados = {script for suite in SUITES.values() for script, _ in suite["roteiros"]}
    if set(args.roteiro or []) - registrados:
        parser.error("roteiro não registrado: " + ", ".join(sorted(set(args.roteiro) - registrados)))
    if args.listar:
        for name, suite in SUITES.items():
            print(f"{name}: {suite['descricao']}")
            for script, extra in suite["roteiros"]:
                print("   ", script, extra or "")
        return 0
    if not (ROOT / "frontend" / "dist" / "index.html").is_file():
        print("Build ausente: rode `npm ci && npm run build` em frontend/ antes das jornadas.", file=sys.stderr)
        return 2
    results = []
    with tempfile.TemporaryDirectory(prefix="adt-ui-") as folder:
        for name in args.suite or list(SUITES):
            if not args.roteiro or any(script in args.roteiro for script, _ in SUITES[name]["roteiros"]):
                results.extend(run_suite(name, Path(folder), args.roteiro))
    return 1 if report(results) else 0


if __name__ == "__main__":
    sys.exit(main())
