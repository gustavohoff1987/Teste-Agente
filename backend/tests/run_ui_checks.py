"""Executor único das jornadas de navegador: o mesmo comando na máquina local e no CI.

Cada roteiro roda em processo próprio, e uma falha não interrompe os seguintes. Assim, nenhum
problema fica escondido atrás de outro. No final, um resumo lista todos os resultados, e o
código de saída é 1 se algum roteiro falhou.

Uso, na raiz do repositório, depois de `npm run build` em frontend/:
    python backend/tests/run_ui_checks.py                        # todas as suítes
    python backend/tests/run_ui_checks.py --suite bloco1         # só uma suíte (pode repetir)
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

# catalogo: "bloco1" e "duas-fontes" são fixtures sintéticas; "repositorio" é a base versionada.
# servidor: "offline" (sem transporte de IA) ou "gemini-simulado" (só o transporte é simulado).
SUITES = {
    "conversa": {
        "descricao": "Jornada conversacional com catálogo sintético de duas fontes",
        "catalogo": "duas-fontes", "servidor": "offline",
        "roteiros": [("ui_conversational_smoke.py", {})],
    },
    "bloco1": {
        "descricao": "Bloco 1 a 3 com catálogo sintético: seleção, regressão, referência, critérios, mapas, visibilidade",
        "catalogo": "bloco1", "servidor": "offline",
        "roteiros": [("ui_block1_smoke.py", {}), ("ui_block1_regression.py", {}), ("ui_nearest_smoke.py", {}),
                     ("ui_criteria_smoke.py", {}), ("ui_map_smoke.py", {}), ("ui_visibility_diagnostic.py", {}),
                     ("ui_investigation.py", {}), ("ui_integrated_workspace.py", {})],
    },
    "gemini-simulado": {
        "descricao": "Interpretação por um transporte Gemini simulado (sem chamadas ao provedor)",
        "catalogo": "bloco1", "servidor": "gemini-simulado",
        "roteiros": [("ui_block1_integration.py", {}), ("ui_semantic_continuity.py", {})],
    },
    "base-versionada": {
        "descricao": "Jornada do Bloco 1 com a base Brasil versionada (62 municípios do AM, 22 competências)",
        "catalogo": "repositorio", "servidor": "offline",
        "roteiros": [("ui_block1_smoke.py", {"ADT_BLOCK1_REAL": "1"}), ("ui_investigation.py", {"ADT_BLOCK1_REAL": "1"})],
    },
}
SERVERS = {"offline": "serve_ui_offline.py", "gemini-simulado": "serve_ui_fake_gemini.py"}
FIXTURES = {"bloco1": "prepare_block1_catalog.py", "duas-fontes": "prepare_ui_brazil_catalog.py"}
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


def run_suite(name, workdir):
    suite = SUITES[name]
    env = base_env()
    results = []
    if suite["catalogo"] in FIXTURES:
        catalog = workdir / ("catalogo-" + name)
        prepared = subprocess.run([sys.executable, str(TESTS / FIXTURES[suite["catalogo"]]), str(catalog)],
                                  cwd=ROOT, env=env).returncode
        if prepared != 0:
            message = f"catálogo de teste não foi preparado ({FIXTURES[suite['catalogo']]}, código {prepared})"
            print(message, flush=True)
            return [(name, script, "falhou", 0.0, message) for script, _ in suite["roteiros"]]
        env["ADT_BRASIL_DATA_DIR"] = str(catalog)
    if suite["servidor"] == "gemini-simulado":
        env["ADT_FAKE_GEMINI_LOG"] = str(workdir / ("gemini-simulado-" + name + ".jsonl"))
    server_log = workdir / ("servidor-" + name + ".log")
    try:
        process, port, log = start_server(suite["servidor"], env, server_log)
    except (RuntimeError, OSError) as exc:
        message = "servidor não iniciou: " + str(exc)
        print(message + "\n" + tail(server_log), flush=True)
        return [(name, script, "falhou", 0.0, message) for script, _ in suite["roteiros"]]
    try:
        for script, extra in suite["roteiros"]:
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
    parser.add_argument("--listar", action="store_true", help="mostra suítes e roteiros registrados")
    args = parser.parse_args()
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
            results.extend(run_suite(name, Path(folder)))
    return 1 if report(results) else 0


if __name__ == "__main__":
    sys.exit(main())
