"""Servidor local de verificação: build Vite + API reais; só o transporte Gemini é simulado.

Executar na raiz, um novo processo a cada execução do roteiro (não há teto local de chamadas desde 26/10/2026):
    python backend/tests/serve_ui_fake_gemini.py
Nenhuma rede externa. Cada payload que seria enviado ao provedor (mensagens, exemplos da biblioteca conversacional e as
entradas da redação da resposta) é registrado em JSONL (ADT_FAKE_GEMINI_LOG) para conferir a triagem: sem arquivos,
colunas, códigos, identificadores ou linhas; com o resultado agregado em exibição (autorização de 26/10/2026).
A redação simulada devolve a resposta verificada do sistema com outra abertura ("Em outras palavras: "), que passa pela
conferência de fidelidade como um texto real. Gatilhos de teste na mensagem: "lento" (atraso), "invalido" (saída fora do
contrato), "simule limite" (429 do provedor, com espera curta informada por ele) e "simule queda" (falha temporária).
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


def _registrar(registro):
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(registro, ensure_ascii=False) + "\n")


def _simulacao(current):
    """Limite e falha temporária simulados como o provedor os sinaliza: o backend põe a espera e não repete sozinho."""
    if "simule limite" in current:
        llm_bridge._esperar("cota", 3, "minuto")  # o RetryInfo do provedor diria 3 s
        raise llm_bridge.LLMError(429, "Cota ou limite de requisições da API Gemini atingido.", "cota")
    if "simule queda" in current:
        llm_bridge._esperar("indisponivel", 3, "provedor")
        raise llm_bridge.LLMError(502, "A API Gemini não concluiu a solicitação.", "indisponivel")


async def fake_gemini(sanitized, model, api_key):
    """Imita um intérprete que 'carrega' contexto: devolve período/categoria de mensagens
    anteriores, para que o backend prove que só aceita valores ancorados."""
    # Os exemplos da biblioteca conversacional entram na instrução de sistema do pedido real.
    _registrar({"model": model, "messages": sanitized, "exemplos": llm_bridge._EXAMPLES.get()})
    users = [m for m in sanitized if not m.startswith(("CONTEXTO_VERIFICADO_PELO_BACKEND", "CONTEXTO_DA_CONVERSA",
                                                      "CONTINUIDADE_VERIFICADA", "VIOLACOES_DA_TENTATIVA"))]
    current = users[-1].casefold()
    _simulacao(current)
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


async def fake_redacao(sistema, mensagens, esquema, max_tokens=1200):
    """Redação simulada: a resposta verificada do sistema, que vem no cartão, com outra abertura."""
    _registrar({"redacao": True, "messages": mensagens})
    contexto = next((m for m in mensagens if m.startswith("CONTEXTO_DA_CONVERSA: ")), "")
    cartao = json.loads(contexto[len("CONTEXTO_DA_CONVERSA: "):]) if contexto else {}
    _simulacao(mensagens[-1].casefold())
    if "lent" in mensagens[-1].casefold():
        await asyncio.sleep(2.5)
    verificada = cartao.get("resposta_verificada_do_sistema") or ""
    return {"resposta": ("Em outras palavras: " + verificada) if verificada else ""}


llm_bridge._call_gemini = fake_gemini
llm_bridge.generate_structured = fake_redacao
app.mount("/", StaticFiles(directory=ROOT / "frontend" / "dist", html=True), name="ui-verify")
if __name__ == "__main__":
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")  # o roteiro confere todas as chamadas desta execução
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("ADT_UI_PORT", "18200")), log_level="warning")
