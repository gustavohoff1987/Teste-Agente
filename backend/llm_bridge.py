"""Etapa experimental de interpretação conversacional; nenhuma execução analítica pelo LLM.

A SPEC v1.2.4 é referência de fronteiras: propostas sem autoridade factual,
minimização pré-LLM, resposta estruturada validada e confirmação pelo usuário.
Não implementa o agente normativo completo descrito na SPEC.
"""
import json
import os
import re
import threading
import unicodedata
from datetime import date
from typing import Any

import httpx
from pydantic import BaseModel, Field


OPERATIONS = {
    "density": "Densidade",
    "counts": "Quantitativos",
    "distribution": "Distribuição",
    "comparisons": "Comparações",
    "temporal": "Evolução temporal",
    "aggregate": "Agregações",
    "spatial": "Análise espacial",
    "ranking": "Recortes e rankings",
    "rotation": "Rotatividade",
    "report": "Relatórios",
}
INDICATORS = {"density": "Densidade por 1.000 habitantes",
              "quantity": "Quantidade absoluta de profissionais"}
# Nesta iteração, permitir apenas o modelo cuja chamada real foi comprovada
# no Python local em 10/10/2026. A seleção não garante faturamento gratuito.
ALLOWED_MODELS = {"gemini-3.5-flash-lite"}
MODEL_DEFAULT = "gemini-3.5-flash-lite"
MAX_REQUESTS_PER_DAY = 20  # guarda local, não é controle de faturamento da Google
_lock = threading.Lock()
_counter_day = ""
_counter = 0

# Campos pessoais e nomes próprios são ocultados antes da chamada externa.
# Trata-se de proteção conservadora do protótipo, não da triagem integral da SPEC.
_PRIVATE = re.compile(
    r"(?i)(?:https?://\S+|[\w.+-]+@[\w.-]+\.[a-z]{2,}"
    r"|\+?\d[\d().\s-]{7,}\d|\b\d{7,}\b"
    r"|\b(?:cpf|cns|rg|telefone|celular|e-mail|email|matrícula|nome completo)"
    r"\s*[:=]\s*[^,.;\n]{1,60})"
)
_NOMINAL = re.compile(r"(?<!\w)[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+"
                      r"(?:\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇ][a-záéíóúâêôãõç]+){0,3}")
_KEEP = {"Quero", "Preciso", "Gostaria", "Compare", "Comparar", "Analise", "Analisar",
         "Mostre", "Mostrar", "Qual", "Quais", "Onde", "Quando", "Como", "Entre",
         "Município", "Municípios", "Estado", "Estados", "Região", "Regiões",
         "Densidade", "Distribuição", "Evolução", "Quantitativos", "Médicos",
         "Médicas", "Enfermeiros", "Enfermeiras", "Brasil", "Saúde", "Profissionais",
         "FTS", "Ranking", "Período", "Categoria", "Quintis", "Quintil", "O", "A",
         "De", "Em", "No", "Na", "Por"}


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=800)
    history: list[str] = Field(default_factory=list, max_length=4)


class LLMError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


def _configured_model() -> str:
    model = os.getenv("ADT_GEMINI_MODEL", MODEL_DEFAULT).strip()
    if model not in ALLOWED_MODELS:
        raise LLMError(503, "Modelo não autorizado nesta integração experimental.")
    return model


def _enabled() -> bool:
    return bool(os.getenv("GEMINI_API_KEY", "").strip())


def status() -> dict[str, Any]:
    try:
        model = _configured_model()
    except LLMError:
        model = "configuração inválida"
    with _lock:
        day = date.today().isoformat()
        used = _counter if day == _counter_day else 0
    return {"configured": _enabled(), "model": model,
            "requests_used_today": used, "local_daily_limit": MAX_REQUESTS_PER_DAY,
            "provider_quota_verified": False, "executes_analyses": False}


def _reserve_request() -> None:
    global _counter, _counter_day
    with _lock:
        today = date.today().isoformat()
        if _counter_day != today:
            _counter_day, _counter = today, 0
        if _counter >= MAX_REQUESTS_PER_DAY:
            raise LLMError(429, "Limite local diário de solicitações ao LLM atingido.")
        _counter += 1


def _sanitize(text: str) -> str:
    # Não há upload, nome de arquivo, cabeçalho ou linha de base neste endpoint.
    # Mesmo entradas conversacionais passam por minimização antes de sair do backend.
    filtered = _PRIVATE.sub("[IDENTIFICADOR_PROTEGIDO]", text)
    filtered = _NOMINAL.sub(
        lambda match: match.group(0) if match.group(0) in _KEEP
        else "[ENTIDADE_PROTEGIDA]", filtered)
    return filtered.strip()


def _schema() -> dict:
    return {
        "type": "OBJECT",
        "properties": {
            "operation": {"type": "STRING", "enum": [*OPERATIONS, "none"]},
            "indicator": {"type": "STRING", "enum": [*INDICATORS, "none"]},
            "period": {"type": "STRING"},
            "category": {"type": "STRING"},
            "territory": {"type": "STRING"},
        },
        "required": ["operation", "indicator", "period", "category", "territory"],
    }


_SYSTEM = (
    "Você é um intérprete preliminar de pedidos de diagnóstico territorial da "
    "força de trabalho em saúde. Não possui dados, resultados, memória de base ou "
    "permissão para executar ferramentas. Proponha NO MÁXIMO uma capacidade da "
    "enumeração do esquema. Retorne JSON válido conforme o esquema. "
    "Identifique período, território ou categoria apenas se estiverem "
    "literalmente explícitos nas mensagens sanitizadas; não fabrique, agregue "
    "ou estabeleça que uma categoria pertence à FTS. "
    "Use 'none' quando não houver solicitação analítica clara. "
    "Não faça afirmações factuais, metodológicas, estatísticas ou normativas. "
    "Indicador 'density' significa densidade por 1.000 habitantes e 'quantity' "
    "significa quantidade absoluta. Uma análise de distribuição pode usar "
    "qualquer dos dois; não presuma qual sem manifestação explícita."
)


async def _call_gemini(sanitized: list[str], model: str, api_key: str) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": _SYSTEM}]},
        "contents": [{"role": "user", "parts": [{"text": entry}]} for entry in sanitized],
        "generationConfig": {
            "temperature": 0, "maxOutputTokens": 600,
            "responseMimeType": "application/json", "responseSchema": _schema(),
        },
    }
    try:
        async with httpx.AsyncClient(timeout=22.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=body,
            )
    except (httpx.TimeoutException, httpx.RequestError) as exc:
        raise LLMError(503, "Não foi possível alcançar a API Gemini. Tente novamente.") from exc
    if response.status_code == 429:
        raise LLMError(429, "Cota ou limite de requisições da API Gemini atingido.")
    if response.status_code in (401, 403):
        raise LLMError(503, "Chave ou acesso ao Gemini não autorizado. Confira a configuração local.")
    if response.status_code != 200:
        raise LLMError(502, "A API Gemini não concluiu a solicitação (HTTP "
                       + str(response.status_code) + ").")
    try:
        data = response.json()
        parts = data["candidates"][0]["content"]["parts"]
        content = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
        return json.loads(content)
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise LLMError(502, "A API não retornou uma interpretação estruturada válida.") from exc


def _anchor(value: Any, user_text: str) -> str:
    if not isinstance(value, str) or not value or len(value) > 100:
        return ""
    if "[" in value or "]" in value:
        return ""
    def norm(v: str) -> str:
        return "".join(x for x in unicodedata.normalize("NFKD", v.casefold())
                       if not unicodedata.combining(x))
    if not re.search(r"(?<!\\w)" + re.escape(norm(value)) + r"(?!\\w)", norm(user_text)):
        return ""
    return value


def _validate(raw: Any, sanitized: list[str]) -> dict:
    if not isinstance(raw, dict):
        raise LLMError(502, "O Gemini retornou dados fora do contrato de interpretação.")
    operation = raw.get("operation")
    indicator = raw.get("indicator")
    if operation not in (*OPERATIONS, "none") or indicator not in (*INDICATORS, "none"):
        raise LLMError(502, "O Gemini propôs uma operação ou indicador desconhecido.")
    # Apenas os valores textuais explicitamente presentes nas mensagens sanitizadas
    # podem voltar como candidatos. Não representam seleção ou autorização.
    source = " ".join(sanitized)
    anchors = {key: _anchor(raw.get(key), source) for key in ("period", "category", "territory")}
    if operation == "none":
        indicator = "none"
    if operation in ("density", "comparisons", "ranking") and indicator == "quantity":
        raise LLMError(502, "O indicador sugerido não é compatível com a operação.")
    proposal = {"operation": None if operation == "none" else operation,
                "indicator": None if indicator == "none" else indicator,
                **anchors}
    if operation == "distribution" and indicator == "none":
        followup = "Qual indicador deseja utilizar: densidade por 1.000 habitantes ou quantidade absoluta?"
    elif operation == "none":
        followup = "Qual análise deseja realizar sobre a força de trabalho na saúde?"
    else:
        followup = "Confira a proposta e confirme as dimensões na configuração da análise antes de executar."
    summary = ("Sugestão preliminar: " + OPERATIONS[operation] + "."
               if operation in OPERATIONS else "Não identifiquei uma análise inequívoca.")
    if indicator in INDICATORS:
        summary += " Indicador sugerido: " + INDICATORS[indicator] + "."
    # Nenhum texto livre produzido pelo LLM é mostrado como explicação metodológica.
    return {"reply": summary + " " + followup,
            "proposal": proposal, "requires_confirmation": True,
            "executed": False, "origin": "INTERPRETACAO_LLM",
            "note": "Proposta não verificada contra a base: nenhuma análise foi executada."}


async def interpret(request: ChatRequest) -> dict:
    if not _enabled():
        raise LLMError(503, "Gemini não configurado. Defina GEMINI_API_KEY no backend.")
    model = _configured_model()
    messages = [*request.history, request.message]
    if any(not isinstance(x, str) or not 3 <= len(x) <= 800 for x in messages):
        raise LLMError(422, "Histórico de conversa inválido.")
    sanitized = [_sanitize(m) for m in messages]
    if not any(re.search(r"[a-zá-ú]{3}", x, re.I) for x in sanitized):
        raise LLMError(422, "Solicitação sem conteúdo analítico após proteção de identificadores.")
    _reserve_request()
    raw = await _call_gemini(sanitized, model, os.environ["GEMINI_API_KEY"].strip())
    return {**_validate(raw, sanitized), "model": model, "privacy": "Nenhum arquivo ou registro da base foi enviado."}
