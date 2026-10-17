"""Contexto mínimo do LLM, derivado de preflight executado no servidor.

Somente status de capacidades e papéis de campo são enviados ao provedor.
Listas de territórios, pessoas, categorias, períodos e metadados originais
permanecem neste backend. Nenhum valor vindo do navegador é aceito como
evidência de disponibilidade sem revalidação da base.
"""
from typing import Any
import unicodedata
import hashlib
import pandas as pd

from data_contract import text_values
from analysis_catalog import OPERATION_LABELS as OPERATIONS  # só as capacidades do contrato do LLM
from semantic_bridge import preflight
from conversation_session import fingerprint
from territorial_selection import territory_catalog


def investigation_context(frame, mapping, options, eligibility):
    """Snapshot local verificado; os valores nunca integram provider_snapshot."""
    source = fingerprint({"columns": list(frame.columns), "source": frame.attrs.get("source"),
                          "data": hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()})
    parameters = {key: value for key, value in options.items()
                  if not key.startswith(("conversation_", "exploration_"))}
    selected = []
    if options.get("territory_ids"):
        catalog = territory_catalog(frame, mapping, options)
        by_id = {item["id"]: item for item in catalog}
        if any(item not in by_id for item in options["territory_ids"]):
            raise ValueError("Seleção territorial não pertence à base.")
        selected = [{"id": item, "label": by_id[item]["label"]} for item in dict.fromkeys(options["territory_ids"])]
    return {"source": source, "signature": fingerprint({"source": source, "mapping": mapping, "options": parameters}),
            "selection": selected, "parameters": parameters,
            "operation": options.get("exploration_operation") if options.get("exploration_operation") in OPERATIONS else None,
            "capabilities": {key: value["status"] for key, value in eligibility["capabilities"].items()}}


def dialogue_projection(capture, has_result=False):
    """Somente estados/enums: nenhuma seleção, resultado, token ou hash de dados."""
    context = capture["context"]
    memory = capture["dialogue"]
    return {"has_selection": bool(context.get("selection")), "has_verified_result": bool(has_result),
            "active_operation": context.get("operation"),
            "previous_operation": memory.get("operation"), "previous_indicator": memory.get("indicator"),
            "previous_document": memory.get("document")}


def screen_reply(action, capture):
    """Descrição estruturada do estado; não inventa resultado nem aplica parâmetros."""
    context = capture["context"]
    selected = context.get("selection", [])
    lines = []
    if selected:
        lines.append("Seleção atual: " + ", ".join(item["label"] for item in selected[:12]) +
                     (" (demais territórios preservados na seleção)." if len(selected) > 12 else "."))
    else:
        lines.append("Seleção territorial: não informada.")
    parameters = context.get("parameters", {})
    periods = parameters.get("period_filters") or ([parameters["period_filter"]] if parameters.get("period_filter") else [])
    if periods:
        lines.append("Período da preparação: " + ", ".join(map(str, periods)) + ".")
    if action == "change_selection":
        lines.append("Qual município você deseja acrescentar?")
    elif action == "change_period":
        lines.append("A mudança de período prepara outro recorte; não altera um resultado já calculado. Qual período deseja usar?")
    else:
        from analysis_catalog import ENGINE_OPERATION_LABELS
        available = [ENGINE_OPERATION_LABELS[key] for key, value in context.get("capabilities", {}).items()
                     if value == "available" and key in ENGINE_OPERATION_LABELS]
        if available:
            lines.append("Possibilidades no pré-exame atual (sem execução): " + "; ".join(available) + ".")
        else:
            lines.append("Há parâmetros ou confirmações pendentes na preparação.")
    return {"reply": "\n\n".join(lines), "dialogue_action": action,
            "context_reference": {"revision": capture["revision"], "origin": "BACKEND_VERIFIED_STATE"}}


def _norm(value: str) -> str:
    simplified = "".join(
        ch for ch in unicodedata.normalize("NFKD", str(value).casefold())
        if not unicodedata.combining(ch)
    )
    return " ".join(simplified.split())


def provider_snapshot(eligibility: dict[str, Any]) -> dict[str, Any]:
    """Resumo enumerado, sem conteúdo original da base ou valores de células."""
    roles = {
        role: value["status"]
        for role, value in eligibility["field_states"].items()
        if value["status"] in ("recognized", "confirmed")
    }
    return {
        "source": "BACKEND_PREFLIGHT",
        "has_dataset": True,
        "recognized_roles": roles,
        "capabilities": {
            operation: eligibility["capabilities"][operation]["status"]
            for operation in OPERATIONS
        },
        # Sem nomes de campos, nomes territoriais, valores nem linhas.
    }


def _slot_status(value: str, possibilities: list[str]) -> str:
    if not value:
        return "not_requested"
    # Não converter uma expressão semântica em outra; equivalências exigem
    # reconhecimento governado, inexistente integralmente no protótipo.
    return ("found_in_dataset" if _norm(value) in {_norm(item) for item in possibilities}
            else "not_confirmed_in_dataset")


def review_interpretation(proposal: dict, eligibility: dict[str, Any],
                          category_constant: str = "", *, frame=None, mapping=None, options=None) -> dict:
    """Revisão do resultado LLM com evidência produzida por código."""
    operation = proposal.get("operation")
    gate = eligibility["capabilities"].get(operation) if operation else None
    capability_status = gate["status"] if gate else "not_selected"
    current_status = capability_status
    values = eligibility["values"]
    # Categoria constante já confirmada pelo usuário não exige coluna de
    # categoria própria. Não inventar equivalências ou categorias adicionais.
    categories = [*values["categories"], *([category_constant] if category_constant else [])]
    slots = {
        "period": _slot_status(proposal.get("period", ""), values["periods"]),
        "category": _slot_status(proposal.get("category", ""), categories),
    }
    territorial = proposal.get("territory", "")
    # 'Municípios' é um nível territorial pedido, não um nome da base;
    # não presumir que o nível está autorizado pelo cabeçalho da coluna.
    if territorial:
        slots["territory"] = "requires_unit_confirmation"
    else:
        slots["territory"] = "not_requested"

    blockers = []
    if operation and frame is not None:
        # Cópia provisória: nenhuma seleção ou confirmação é aplicada à sessão.
        proposed = dict(options or {})
        if operation in ("distribution", "temporal", "report"):
            proposed[operation + "_indicator"] = proposal.get("indicator") or ""
        for role, choices in (("period", values["periods"]), ("category", categories)):
            candidate = proposal.get(role)
            if not candidate:
                continue
            column = (mapping or {}).get(role)
            if column and column in frame.columns:
                # Associação ainda pendente não significa valor ausente: o pré-exame
                # da proposta relata a confirmação exigida para esse papel.
                choices = text_values(frame[column]).dropna().unique().tolist()
            matches = [value for value in choices if _norm(value) == _norm(candidate)]
            if len(matches) != 1:
                capability_status = "unavailable"
                blockers.append("O recorte proposto não tem correspondência única na base.")
                break
            if (mapping or {}).get(role):
                proposed[role + "_filter"] = matches[0]
        else:
            try:
                proposed_gate = preflight(frame, mapping, proposed)["capabilities"][operation]
                capability_status = proposed_gate["status"]
                blockers.extend(proposed_gate["reasons"])
            except (ValueError, TypeError):
                capability_status = "unavailable"
                blockers.append("Não foi possível validar o recorte proposto.")
    elif operation:
        capability_status = "needs_confirmation"
        blockers.append("A proposta exige novo pré-exame com seus próprios parâmetros.")
    if operation is None:
        blockers.append("Escolha uma das capacidades de diagnóstico territorial.")
    if capability_status == "unavailable":
        blockers.append("A capacidade ainda não atende às condições da matriz de aplicabilidade.")
    elif capability_status == "needs_confirmation":
        blockers.append("Existem confirmações ou parâmetros pendentes para essa capacidade.")
    if proposal.get("operation") == "distribution" and not proposal.get("indicator"):
        blockers.append("A distribuição exige escolher densidade ou quantidade de profissionais.")
    if slots["period"] == "not_confirmed_in_dataset":
        blockers.append("O período mencionado não foi confirmado entre os valores da base.")
    if slots["category"] == "not_confirmed_in_dataset":
        blockers.append("A categoria mencionada não foi confirmada entre os valores da base.")
    if slots["territory"] == "requires_unit_confirmation":
        blockers.append("Confirme a unidade territorial nos controles da base.")
    return {
        "source": "BACKEND_PREFLIGHT",
        "capability_status": capability_status,
        "current_capability_status": current_status,
        "configuration_reviewed": "proposal" if frame is not None else "current_only",
        "slots": slots,
        "blockers": blockers,
        "ready_to_execute": False,
        "next_action": "confirm_in_interface",
    }
