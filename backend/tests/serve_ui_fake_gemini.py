"""Servidor local de verificação: build Vite + API reais; só o transporte Gemini é simulado.

Executar na raiz, um novo processo a cada execução de ui_integration_smoke.py
(o limite local é de 20 solicitações por processo):
    python backend/tests/serve_ui_fake_gemini.py
Nenhuma rede externa. Cada payload que seria enviado ao provedor é registrado em JSONL
(ADT_FAKE_GEMINI_LOG) para conferir a minimização: sem arquivos, colunas, valores ou linhas.
"""
import asyncio
import json
import os
import re
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["GEMINI_API_KEY"] = "fake-offline-key"  # somente neste processo; a chave local não é carregada

# Qualquer conexão externa neste processo é uma falha de verificação.
_connect = socket.socket.connect


def _local_only(sock, address):
    if isinstance(address, tuple) and address[0] not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError("Rede externa proibida no servidor de verificação")
    return _connect(sock, address)


socket.socket.connect = _local_only

if os.environ.get("ADT_BRASIL_DATA_DIR") and not os.environ.get("ADT_BRASIL_DATA_VERSION"):
    # Servidor de teste: o catálogo indicado ao iniciá-lo é escolha explícita; sua versão é fixada.
    from brazil_data import catalog_version
    os.environ["ADT_BRASIL_DATA_VERSION"] = catalog_version(os.environ["ADT_BRASIL_DATA_DIR"])
import llm_bridge  # noqa: E402
from main import app  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
import uvicorn  # noqa: E402

LOG = Path(os.getenv("ADT_FAKE_GEMINI_LOG", ROOT / ".local" / "ui-validation" / "fake-gemini-calls.jsonl"))


async def fake_gemini(sanitized, model, api_key):
    """Imita um intérprete que 'carrega' contexto: devolve período/categoria de mensagens
    anteriores, para que o backend prove que só aceita valores ancorados."""
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"model": model, "messages": sanitized}, ensure_ascii=False) + "\n")
    users = [m for m in sanitized if not m.startswith("CONTEXTO_VERIFICADO_PELO_BACKEND")]
    current = users[-1].casefold()
    if "lento" in current:
        await asyncio.sleep(2.5)
    if "invalido" in current:
        return {"operation": "counts", "indicator": "density", "period": "", "category": "",
                "territory": "", "intent": "ANALITICO", "topic": "none"}
    if "perfil dos municipios" in current:
        return {"operation":"none","indicator":"none","period":"","category":"","territory":"",
                "intent":"ANALITICO","topic":"none","candidates":[
                    {"operation":"density","indicator":"density","anchor":"perfil dos municipios"},
                    {"operation":"counts","indicator":"quantity","anchor":"perfil dos municipios"}]}
    if "lado a lado" in current or "comparativ" in current:
        op, ind = "comparisons", "density"
    elif "distribui" in current:
        op, ind = "distribution", ("density" if "densidade" in current else "quantity" if "quantidade" in current else "none")
    elif "densidade" in current:
        op, ind = "density", "density"
    elif "quantitativ" in current or "quantos" in current and ("medic" in current or "médic" in current):
        op, ind = "counts", "quantity"
    else:
        op, ind = "none", "none"
    periods = [p for m in users for p in re.findall(r"\b(20\d{4}|20\d{2})\b", m)]
    category = "MEDICINA" if any("medicina" in m.casefold() for m in users) else ""
    territory = "municípios" if "munic" in current else "Brasil" if "brasil" in current else ""
    return {"operation": op, "indicator": ind, "period": periods[-1] if periods else "",
            "category": category, "territory": territory,
            "intent": "ANALITICO" if op != "none" else "CONVERSACIONAL", "topic": "none"}


llm_bridge._call_gemini = fake_gemini
app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="ui-verify")
if __name__ == "__main__":
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")  # o roteiro confere todas as chamadas desta execução
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ADT_UI_PORT", "18200")), log_level="warning")
