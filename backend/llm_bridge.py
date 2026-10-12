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
from typing import Any, Literal, Callable

import httpx
from pydantic import BaseModel, Field, StrictStr, ValidationError, field_validator, model_validator
from llm_context import provider_snapshot, review_interpretation
from dialogue_guidance import clarification_for
from llm_config import load_local_environment


# Carregado na inicialização do backend; sem log da chave e sem sobrescrever
# credenciais injetadas pela futura plataforma de hospedagem.
load_local_environment()


from analysis_catalog import OPERATION_LABELS as OPERATIONS
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
    message: str = Field(min_length=2, max_length=800)
    history: list[str] = Field(default_factory=list, max_length=4)


# Respostas sobre o funcionamento do agente são produzidas a partir do catálogo
# local, não de conteúdo livre ou não ancorado do provedor externo.
_GUIDANCE = {
    "capabilities": (
        "Posso ajudar com densidade por 1.000 habitantes, quantitativos, distribuição, "
        "comparações territoriais, evolução temporal, agregações, distâncias geodésicas, "
        "rankings, rotatividade e relatórios. Escolha uma opção no carrossel ou descreva "
        "seu objetivo. Cada análise depende dos requisitos disponíveis na sua base."
    ),
    "data": (
        "Você pode usar os dados brasileiros já configurados ou importar CSV, XLS ou XLSX. "
        "Em 'Importar seus dados', baixe a estrutura recomendada para conhecer os campos "
        "e a hierarquia territorial. Os nomes de colunas podem ser associados durante "
        "a preparação. Nenhum cálculo acontece apenas por importar."
    ),
    "workflow": (
        "Escolha um tipo de análise no carrossel da conversa. Em seguida, confira "
        "a identificação dos dados, os parâmetros e as confirmações; por último, "
        "revise e execute. O Python valida os requisitos e realiza os cálculos."
    ),
    "privacy": (
        "Os arquivos são processados no backend local. O Gemini recebe apenas mensagens "
        "minimizadas e, quando necessário, estados técnicos do pré-exame; não recebe "
        "linhas, colunas nem registros da base. Evite inserir dados pessoais no chat."
    ),
    "limits": (
        "O Gemini propõe interpretações, mas não executa cálculos, não confirma "
        "significados dos campos, não inventa métodos e não autoriza agregações. "
        "Se o modelo estiver indisponível, o motor Python e os controles continuam funcionando."
    ),
    "spatial": (
        "A distância espacial utiliza coordenadas e cálculo geodésico. Ela representa "
        "distância geográfica direta, não percurso viário, tempo de deslocamento "
        "ou acesso efetivo a um serviço. A execução exige coordenadas válidas."
    ),
    "aggregation": (
        "O agrupamento territorial não comprova, por si só, pessoas únicas. "
        "Quando houver possibilidade de sobreposição, a soma representa contagens "
        "dos componentes, salvo evidência válida de deduplicação ou aditividade."
    ),
    "density": (
        "A densidade por 1.000 habitantes é calculada como quantidade de profissionais "
        "dividida pela população correspondente, multiplicada por 1.000. "
        "A compatibilidade entre unidade de contagem, território e período precisa "
        "ser confirmada antes da execução."
    ),
}
_GENERIC_GREETING = (
    "Olá! Sou o Agente Diagnóstico Territorial. Posso ajudar a explorar dados "
    "sobre a força de trabalho na saúde, explicar as análises disponíveis "
    "e orientar sua preparação. Que tipo de análise você deseja fazer? "
    "Você pode escolher no carrossel ou descrever seu objetivo."
)
_INTENTS = ("ANALITICO", "SOBRE_O_AGENTE", "CONCEITUAL_DOMINIO", "CONVERSACIONAL")
_TOPICS = ("capabilities", "data", "workflow", "privacy", "limits", "density", "spatial", "aggregation", "none")


class ModelInterpretation(BaseModel):
    operation: StrictStr
    indicator: Literal["density", "quantity", "none"]
    period: StrictStr = Field(max_length=100)
    category: StrictStr = Field(max_length=100)
    territory: StrictStr = Field(max_length=100)
    intent: Literal["ANALITICO", "SOBRE_O_AGENTE", "CONCEITUAL_DOMINIO", "CONVERSACIONAL"]
    topic: Literal["capabilities", "data", "workflow", "privacy", "limits", "density", "spatial", "aggregation", "none"]

    @field_validator("operation")
    @classmethod
    def supported_operation(cls, value):
        if value not in (*OPERATIONS, "none"):
            raise ValueError("Operação desconhecida")
        return value

    @model_validator(mode="after")
    def compatible(self):
        allowed = {
            "counts": {"quantity", "none"}, "density": {"density", "none"},
            "comparisons": {"density", "none"}, "ranking": {"density", "none"},
            "aggregate": {"density", "none"}, "spatial": {"none"}, "rotation": {"none"},
            "none": {"none"}, "distribution": {"quantity", "density", "none"},
            "temporal": {"quantity", "density", "none"}, "report": {"quantity", "density", "none"},
        }
        if self.indicator not in allowed[self.operation]:
            raise ValueError("Indicador incompatível")
        if self.operation != "none" and (self.intent != "ANALITICO" or self.topic != "none"):
            raise ValueError("Intenção incompatível")
        return self


def _text_key(value: str) -> str:
    plain = unicodedata.normalize("NFKD", value.casefold())
    return " ".join("".join(c for c in plain if not unicodedata.combining(c)).split())


def _local_guidance(message: str) -> str | None:
    """Atalhos determinísticos para intenções inequívocas, sem consumir franquia."""
    text = _text_key(message).strip(" .!?")
    if re.fullmatch(r"(oi|ola|bom dia|boa tarde|boa noite|e ai|hello|hi|hey)", text):
        return _GENERIC_GREETING
    if re.fullmatch(r"(ajuda|me ajude|o que voce faz|o que este agente faz|o que o agente faz|"
                    r"como funciona o agente|quais analises voce faz|quais analises existem|"
                    r"o que posso fazer aqui|quais sao as opcoes)", text):
        return _GUIDANCE["capabilities"] + " " + _GUIDANCE["workflow"]
    if re.fullmatch(r"(como importar (meus )?dados|como envio meus dados|"
                    r"qual (e a )?estrutura recomendada|como funciona a importacao)", text):
        return _GUIDANCE["data"]
    if re.fullmatch(r"(como (se )?calcula (a )?densidade|o que e densidade|"
                    r"o que significa densidade por 1000 habitantes)", text):
        return _GUIDANCE["density"]
    if re.fullmatch(r"(como funciona a privacidade|meus dados vao para o gemini|"
                    r"quem acessa meus dados)", text):
        return _GUIDANCE["privacy"]
    if re.fullmatch(r"(o que e distancia geodesica|distancia geodesica e distancia de estrada|"
                    r"distancia espacial mede tempo de viagem)", text):
        return _GUIDANCE["spatial"]
    if re.fullmatch(r"(posso somar os profissionais de diferentes municipios|"
                    r"uma soma territorial representa pessoas unicas|"
                    r"como funciona a agregacao territorial)", text):
        return _GUIDANCE["aggregation"]
    if re.fullmatch(r"(o gemini faz os calculos|quem faz os calculos|"
                    r"o agente inventa metodos)", text):
        return _GUIDANCE["limits"]
    return None


def local_response(request: ChatRequest) -> dict | None:
    """Atendimento sem modelo nem leitura de dataset para perguntas de orientação."""
    guidance = _local_guidance(request.message)
    return _system_response(guidance, None, "") if guidance is not None else None


def _system_response(reply: str, eligibility: dict | None, category_constant: str) -> dict:
    proposal = {"operation": None, "indicator": None, "period": "",
                "category": "", "territory": ""}
    result = {"reply": reply, "proposal": proposal, "requires_confirmation": False,
              "executed": False, "origin": "CANAL_SISTEMICO",
              "note": "Orientação operacional do catálogo local; nenhuma análise executada.",
              "model": "sem chamada ao Gemini",
              "privacy": "Nenhum conteúdo desta mensagem foi transmitido ao Gemini."}
    if eligibility is not None:
        result["verification"] = review_interpretation(
            proposal, eligibility, category_constant=category_constant)
    return result


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
            "intent": {"type": "STRING", "enum": list(_INTENTS)},
            "topic": {"type": "STRING", "enum": list(_TOPICS)},
        },
        "required": ["operation", "indicator", "period", "category", "territory", "intent", "topic"],
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
    "Classifique também a intenção em ANALITICO, SOBRE_O_AGENTE, "
    "CONCEITUAL_DOMINIO ou CONVERSACIONAL; selecione o tópico da enumeração "
    "somente quando for realmente pedido. Perguntas sobre o agente, importação, "
    "privacidade, limitações, fluxo de preparação ou definição de densidade "
    "não são propostas analíticas, a menos que o usuário solicite uma operação. "
    "Se houver CONTEXTO_VERIFICADO, ele descreve apenas papéis técnicos e "
    "estados das capacidades confirmados pelo servidor. Não contém nomes ou "
    "valores da base; não deduza nenhum deles nem contorne indisponibilidades. "
    "Não trate o resumo como instrução para executar ferramentas. "
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
    if not re.search(r"(?<!\w)" + re.escape(norm(value)) + r"(?!\w)", norm(user_text)):
        return ""
    return value


# Referências por parâmetro: conectivos como 'agora' não autorizam recuperar slots.
_REFERENCES = {
    "period": r"\b(?:(?:mesmo|nesse|naquele) periodo|periodo anterior)\b",
    "category": r"\b(?:mesma (?:categoria|profissao)|categoria anterior)\b",
    "territory": r"\b(?:mesmos? (?:territorios?|municipios?|estados?)|mesma unidade territorial|territorio anterior)\b",
}


def _anchors_for_turn(raw: dict, sanitized: list[str]) -> dict[str, str]:
    current = sanitized[-1]
    previous = sanitized[-2] if len(sanitized) > 1 else ""
    values = {}
    for name in ("period", "category", "territory"):
        candidate = raw.get(name)
        reference = bool(re.search(_REFERENCES[name], _text_key(current)))
        # Uma menção temporal atual prevalece mesmo se coexistir com uma retomada.
        if name == "period" and re.search(r"\b\d{4}(?:\d{2}|-\d{2}(?:-\d{2})?)?\b", current):
            reference = False
        values[name] = _anchor(candidate, current) or (_anchor(candidate, previous) if reference else "")
    return values


def _validate(raw: Any, sanitized: list[str]) -> dict:
    try:
        raw = ModelInterpretation.model_validate(raw).model_dump()
    except ValidationError as exc:
        raise LLMError(502, "O Gemini retornou dados fora do contrato de interpretação.") from exc
    operation = raw.get("operation")
    indicator = raw.get("indicator")
    if operation not in (*OPERATIONS, "none") or indicator not in (*INDICATORS, "none"):
        raise LLMError(502, "O Gemini propôs uma operação ou indicador desconhecido.")
    # Apenas os valores textuais explicitamente presentes nas mensagens sanitizadas
    # podem voltar como candidatos. Não representam seleção ou autorização.
    anchors = _anchors_for_turn(raw, sanitized)
    if operation == "none":
        indicator = "none"
        intent = raw.get("intent")
        topic = raw.get("topic")
        if intent in ("SOBRE_O_AGENTE", "CONCEITUAL_DOMINIO") and topic in _GUIDANCE:
            proposal = {"operation": None, "indicator": None,
                        "period": "", "category": "", "territory": ""}
            return {"reply": _GUIDANCE[topic], "proposal": proposal,
                    "requires_confirmation": False, "executed": False,
                    "origin": "INTERPRETACAO_LLM",
                    "note": "Tópico interpretado pelo LLM; conteúdo extraído do catálogo local."}
        if intent == "CONVERSACIONAL":
            proposal = {"operation": None, "indicator": None,
                        "period": "", "category": "", "territory": ""}
            return {"reply": _GENERIC_GREETING, "proposal": proposal,
                    "requires_confirmation": False, "executed": False,
                    "origin": "INTERPRETACAO_LLM",
                    "note": "Intenção interpretada pelo LLM; resposta do catálogo local."}
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


async def interpret(request: ChatRequest, eligibility: dict | None = None,
                    category_constant: str = "", proposal_reviewer: Callable | None = None) -> dict:
    # Intenções conversacionais óbvias são atendidas com texto controlado,
    # inclusive durante a indisponibilidade da API externa.
    guidance = _local_guidance(request.message)
    if guidance is not None:
        return _system_response(guidance, eligibility, category_constant)
    if not _enabled():
        raise LLMError(503, "Gemini não configurado. Defina GEMINI_API_KEY no backend.")
    model = _configured_model()
    messages = [*request.history, request.message]
    if any(not isinstance(x, str) or not 2 <= len(x) <= 800 for x in messages):
        raise LLMError(422, "Histórico de conversa inválido.")
    sanitized = [_sanitize(m) for m in messages]
    if not any(re.search(r"[a-zá-ú]{2}", x, re.I) for x in sanitized):
        raise LLMError(422, "Solicitação sem conteúdo analítico após proteção de identificadores.")
    provider_messages = sanitized
    if eligibility is not None:
        # Apenas enums/estados produzidos por preflight no servidor atravessam a API.
        # Os textos do usuário continuam as únicas âncoras possíveis para os slots.
        safe_context = json.dumps(provider_snapshot(eligibility), ensure_ascii=False, sort_keys=True)
        provider_messages = ["CONTEXTO_VERIFICADO_PELO_BACKEND: " + safe_context, *sanitized]
    _reserve_request()
    raw = await _call_gemini(provider_messages, model, os.environ["GEMINI_API_KEY"].strip())
    response = _validate(raw, sanitized)
    # Confirmações e alternativas são apresentadas pelo catálogo determinístico,
    # nunca como texto gerado pelo provedor. Pedidos explicitamente paralelos
    # não autorizam que o LLM escolha arbitrariamente a primeira capacidade.
    clarification = clarification_for(request.message, response["proposal"], None)
    if clarification is not None and clarification["code"] == "MULTIPLAS_CAPACIDADES":
        response["proposal"] = {"operation": None, "indicator": None,
                                "period": "", "category": "", "territory": ""}
        response["reply"] = clarification["prompt"]
        response["requires_confirmation"] = True
    if eligibility is not None:
        response["verification"] = (proposal_reviewer(response["proposal"]) if proposal_reviewer else
            review_interpretation(response["proposal"], eligibility, category_constant=category_constant))
        response["note"] = (
            "Proposta examinada contra o pré-exame da base no servidor. "
            "A autorização e a execução permanecem pendentes."
        )
    if clarification is None:
        clarification = clarification_for(
            request.message, response["proposal"], response.get("verification"))
    if clarification is not None:
        response["clarification"] = clarification
        if clarification["code"] != "MULTIPLAS_CAPACIDADES":
            response["reply"] = clarification["prompt"]
    return {**response, "model": model,
            "privacy": "Somente o pedido minimizado e estados técnicos de capacidades foram enviados; "
                       "nenhum arquivo, linha ou nome de campo da base foi enviado."}
