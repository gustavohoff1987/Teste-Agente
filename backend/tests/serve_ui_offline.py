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

if os.environ.get("ADT_SESSAO_PRAZO_DE_TESTE"):
    # Só neste servidor de teste (suíte "sessao" do run_ui_checks.py): o prazo de inatividade reduzido, para o roteiro
    # ui_sessao.py ver a expiração sem esperar 30 minutos. O produto continua com os 1.800 s fixos da SPEC (RQ-FLX-17).
    import conversation_session
    conversation_session.TIMEOUT = int(os.environ["ADT_SESSAO_PRAZO_DE_TESTE"])


async def forbidden(*args, **kwargs):
    raise llm_bridge.LLMError(503, "Transporte externo desabilitado no servidor de testes.", "indisponivel")


llm_bridge._call_gemini = forbidden
llm_bridge.generate_structured = forbidden
app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="ui-offline")
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ADT_UI_PORT", "18000")), log_level="warning")
