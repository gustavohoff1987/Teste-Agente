"""Hospedagem simulada para os roteiros de navegador (suíte "conteiner" do run_ui_checks.py; job "conteiner" do CI).

- O serviço de análise é a imagem do contêiner, nas condições do Cloud Run: 1 CPU, 2 GiB sem swap e /tmp em memória, na porta
  ADT_CONTEINER_PORTA (18080), com o CORS só para a origem desta página. Sem chave do Gemini (a conversa usa os canais locais).
- A interface é o build do GitHub Pages (frontend/dist, feito com ADT_BASE_DA_PAGINA=/Teste-Agente/ e
  VITE_API_BASE_URL=http://127.0.0.1:18080), servido em /Teste-Agente/ noutro endereço (ADT_UI_PORT), como no Pages.

O contêiner se chama ADT_CONTEINER_NOME (adt-api-ui): os roteiros o param e o reiniciam (docker stop/start) para ver os
estados da conexão e a sessão perdida no reinício. Ao encerrar, o contêiner é removido. Exige o Docker e a imagem
ADT_CONTEINER_IMAGEM (adt:ci) já construída. Nenhuma rede externa.
"""
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
IMAGEM = os.getenv("ADT_CONTEINER_IMAGEM", "adt:ci")
NOME = os.getenv("ADT_CONTEINER_NOME", "adt-api-ui")
PORTA_API = int(os.getenv("ADT_CONTEINER_PORTA", "18080"))
PORTA_UI = int(os.getenv("ADT_UI_PORT", "18100"))
DIST = Path(os.getenv("ADT_PAGES_DIST", ROOT / "frontend" / "dist"))
LOCAL = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def docker(*args, check=True):
    return subprocess.run(["docker", *args], check=check, capture_output=True, text=True)


def subir_conteiner():
    docker("rm", "-f", NOME, check=False)
    docker("run", "-d", "--name", NOME, "--cpus=1", "--memory=2g", "--memory-swap=2g",
           "--tmpfs", "/tmp:rw,size=1g,mode=1777", "-p", f"127.0.0.1:{PORTA_API}:8080",
           "-e", "PORT=8080", "-e", f"ADT_ALLOWED_ORIGINS=http://127.0.0.1:{PORTA_UI}", "-e", "GEMINI_API_KEY=", IMAGEM)
    prazo = time.monotonic() + 280
    while time.monotonic() < prazo:
        try:
            with LOCAL.open(f"http://127.0.0.1:{PORTA_API}/api/health", timeout=3) as resposta:
                if resposta.status == 200:
                    return
        except OSError:
            time.sleep(0.5)
    print(docker("logs", "--tail", "80", NOME, check=False).stdout, flush=True)
    raise SystemExit("o contêiner não respondeu em 280 s")


def app() -> Starlette:
    if not (DIST / "index.html").is_file():
        raise SystemExit("Build ausente em " + str(DIST))
    return Starlette(routes=[Route("/", lambda _request: RedirectResponse("/Teste-Agente/")),
                             Mount("/Teste-Agente", StaticFiles(directory=DIST, html=True), name="pages")])


if __name__ == "__main__":
    subir_conteiner()
    try:
        uvicorn.run(app(), host="127.0.0.1", port=PORTA_UI, log_level="warning")
    finally:
        docker("rm", "-f", NOME, check=False)
        sys.stdout.flush()
