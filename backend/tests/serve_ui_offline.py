"""Servidor local de regressão: build Vite + API, sem transporte externo de IA.

Executar na raiz: python backend/tests/serve_ui_offline.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
os.environ["GEMINI_API_KEY"] = ""  # somente neste processo; não escreve configuração
if os.environ.get("ADT_BRASIL_DATA_DIR") and not os.environ.get("ADT_BRASIL_DATA_VERSION"):
    # Servidor de teste: o catálogo indicado ao iniciá-lo é escolha explícita; sua versão é fixada.
    from brazil_data import catalog_version
    os.environ["ADT_BRASIL_DATA_VERSION"] = catalog_version(os.environ["ADT_BRASIL_DATA_DIR"])
import llm_bridge
from main import app
from fastapi.staticfiles import StaticFiles
import uvicorn


async def forbidden(*args, **kwargs):
    raise llm_bridge.LLMError(503, "Transporte externo desabilitado no servidor de testes.")


llm_bridge._call_gemini = forbidden
app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="ui-offline")
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ADT_UI_PORT", "18000")), log_level="warning")
