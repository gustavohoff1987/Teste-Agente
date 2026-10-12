"""Perguntas estruturadas e discriminação de pedidos, sem autoridade do LLM.

Incremento experimental de FN-INT-01/02/03. As perguntas são produzidas pelo
canal sistêmico a partir de estados controlados; não são prosa do modelo.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

# Catálogo fechado de alternativas para pedidos explicitamente concorrentes.
from analysis_catalog import OPERATION_LABELS as _OPERATION_LABELS
_PATTERNS = {
    "density": r"densidade",
    "counts": r"quantitativos?",
    "distribution": r"distribuicao",
    "comparisons": r"comparac(?:ao|oes)",
    "temporal": r"evolucao(?: temporal)?",
    "aggregate": r"agregac(?:ao|oes)",
    "spatial": r"analise espacial",
    "ranking": r"rankings?",
    "rotation": r"rotatividade",
    "report": r"relatorios?",
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def explicit_parallel_operations(message: str) -> list[str]:
    """Detecta apenas dupla nomeação literal conectada por 'e'.

    Não interpreta expressões como 'distribuição da densidade' como
    solicitação de duas operações.
    """
    source = _normalize(message)
    for left, lp in _PATTERNS.items():
        for right, rp in _PATTERNS.items():
            if left >= right:
                continue
            lhs = rf"\b(?:{lp})\s+e\s+(?:{rp})\b"
            rhs = rf"\b(?:{rp})\s+e\s+(?:{lp})\b"
            if re.search(lhs, source):
                return [left, right]
            if re.search(rhs, source):
                return [right, left]
    return []


def _make(code: str, prompt: str, choices: list[dict[str, str]],
          reason: str) -> dict[str, Any]:
    return {"code": code, "prompt": prompt, "choices": choices,
            "reason": reason, "source": "CATALOGO_LOCAL", "answered": False}


def clarification_for(
    message: str, proposal: dict[str, Any], verification: dict | None,
) -> dict | None:
    """Uma pergunta prioritária; proposta não autorizada continua bloqueada."""
    parallel = explicit_parallel_operations(message)
    if len(parallel) == 2:
        return _make(
            "MULTIPLAS_CAPACIDADES",
            "Você mencionou duas análises. Por qual deseja começar? "
            "A outra poderá ser solicitada depois, sem execução automática.",
            [{"label": _OPERATION_LABELS[item],
              "draft": "Quero começar pela análise de " + _OPERATION_LABELS[item].lower() + "."}
             for item in parallel],
            "Há duas capacidades explicitamente nomeadas na mensagem atual.",
        )

    operation = proposal.get("operation")
    if not operation:
        return None
    if operation == "distribution" and not proposal.get("indicator"):
        scope = "".join(" " + label + " " + proposal[slot] for slot, label in
                        (("period", "no período"), ("category", "para a categoria"),
                         ("territory", "na unidade territorial")) if proposal.get(slot))
        return _make(
            "INDICADOR_DISTRIBUICAO",
            "Para a distribuição, qual indicador deseja utilizar?",
            [
                {"label": "Densidade por 1.000 habitantes",
                 "draft": "Quero a distribuição da densidade por 1.000 habitantes" + scope + "."},
                {"label": "Quantidade absoluta de profissionais",
                 "draft": "Quero a distribuição por quantidade absoluta" + scope + "."},
            ],
            "A distribuição admite indicadores diferentes; escolha explícita necessária.",
        )

    slots = (verification or {}).get("slots") or {}
    if slots.get("period") == "not_confirmed_in_dataset":
        return _make(
            "PERIODO_NAO_CONFIRMADO",
            "O período mencionado não foi confirmado na base. Deseja revisar o período na preparação?",
            [], "O pré-exame não encontrou correspondência para o período informado.",
        )
    if slots.get("category") == "not_confirmed_in_dataset":
        return _make(
            "CATEGORIA_NAO_CONFIRMADA",
            "Vamos localizar nos dados a categoria correspondente à profissão que você mencionou. Confira a opção adequada antes de calcular.",
            [], "A correspondência de categorias depende dos dados e das regras governadas.",
        )
    if slots.get("territory") == "requires_unit_confirmation":
        return _make(
            "UNIDADE_TERRITORIAL",
            "Confirme a unidade territorial na etapa de identificação dos dados.",
            [], "A menção a um nível territorial não confirma sua associação com a base.",
        )
    return None
