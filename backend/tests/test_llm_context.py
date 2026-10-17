"""Contrato da interpretação contextual: a base não cruza a fronteira do Gemini."""
import io
import json

from fastapi.testclient import TestClient
import pytest

import llm_bridge
from main import app


client = TestClient(app)
MAPPING = {
    "territory": "Unidade", "period": "Periodo",
    "category": "Categoria", "count": "Quantidade", "population": "Populacao",
}
OPTIONS = {
    "confirmed_roles": ["territory", "period", "category", "count", "population"],
    "fts_scope_confirmed": True, "object_confirmed": True,
    "require_object_confirmation": True, "population_denominator_confirmed": True,
    "count_unit": "pessoas",
    "distribution_indicator": "density",
    "period_filter": "202406", "category_filter": "Medicos",
}


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")


def _dataset() -> bytes:
    # Texto e identificadores artificiais servem apenas para provar que
    # valores da base não atravessam o contexto externo do LLM.
    return (
        "Unidade;Periodo;Categoria;Quantidade;Populacao;Identificador_privado\n"
        "Vila Protegida;202406;Medicos;10;10000;11122233344\n"
        "Outra Localidade;202406;Medicos;20;10000;55566677788\n"
    ).encode()


def _form(message="Quero distribuicao da densidade de medicos por municipios em 202406",
          mapping=None, options=None) -> dict:
    return {
        "files": {"file": ("exclusivo_privado.csv", io.BytesIO(_dataset()), "text/csv")},
        "data": {
            "message": message, "history": "[]",
            "mapping": json.dumps(MAPPING if mapping is None else mapping),
            "options": json.dumps(OPTIONS if options is None else options),
        },
    }


def test_verified_context_does_not_send_base_values_or_labels(monkeypatch):
    sent = []

    async def provider(payload, model, key):
        sent.extend(payload)
        assert model == "gemini-3.5-flash-lite"
        assert key == "test-only-not-real"
        return {
            "intent": "ANALITICO", "topic": "none", "operation": "distribution", "indicator": "density",
            "period": "202406", "category": "medicos", "territory": "municipios",
        }

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    result = client.post("/api/llm/interpret-context", **_form())
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["executed"] is False
    assert body["requires_confirmation"] is True
    assert body["verification"]["source"] == "BACKEND_PREFLIGHT"
    assert body["verification"]["ready_to_execute"] is False
    assert body["verification"]["slots"]["period"] == "found_in_dataset"
    assert body["verification"]["slots"]["category"] == "found_in_dataset"
    assert body["verification"]["slots"]["territory"] == "requires_unit_confirmation"
    assert body["verification"]["capability_status"] in (
        "available", "needs_confirmation", "unavailable",
    )
    assert sent[0].startswith("CONTEXTO_VERIFICADO_PELO_BACKEND:")
    content = " ".join(sent)
    for forbidden in (
        "Vila Protegida", "Outra Localidade", "11122233344",
        "55566677788", "Identificador_privado", "exclusivo_privado.csv",
    ):
        assert forbidden not in content
    assert "Medicos" not in sent[0]  # categoria textual fica apenas no backend
    assert "202406" not in sent[0]
    assert "Unidade" not in sent[0]
    assert "recognized_roles" in sent[0]
    assert "capabilities" in sent[0]
    # Período e categoria são recuperados localmente, sem enviar seus valores ao modelo.
    assert "202406" not in content
    assert "medicos" not in content.lower()


def test_nonexistent_period_is_not_treated_as_verified(monkeypatch):
    async def provider(payload, model, key):
        return {"intent": "ANALITICO", "topic": "none", "operation": "distribution", "indicator": "density",
                "period": "203001", "category": "medicos", "territory": ""}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    r = client.post("/api/llm/interpret-context",
                    **_form(message="Quero distribuicao de densidade de medicos em 203001"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["verification"]["slots"]["period"] == "not_confirmed_in_dataset"
    assert any("período" in value for value in body["verification"]["blockers"])
    assert body["verification"]["ready_to_execute"] is False


def test_model_cannot_invent_a_field_value_which_user_never_named(monkeypatch):
    async def provider(payload, model, key):
        return {"intent": "ANALITICO", "topic": "none", "operation": "distribution", "indicator": "density",
                "period": "202406", "category": "Enfermeiros", "territory": "Vila Protegida"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    r = client.post("/api/llm/interpret-context",
                    **_form(message="Quero distribuicao de densidade em municipios"))
    assert r.status_code == 200, r.text
    proposal = r.json()["proposal"]
    assert proposal["period"] == ""
    assert proposal["category"] == ""
    assert proposal["territory"] == ""


def test_invalid_mapping_blocks_provider_call(monkeypatch):
    calls = []

    async def provider(payload, model, key):
        calls.append(True)
        return {}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    bad = dict(MAPPING, territory="ColunaQueNaoExiste")
    r = client.post("/api/llm/interpret-context", **_form(mapping=bad))
    assert r.status_code == 422
    assert calls == []


def test_context_endpoint_rejects_invalid_history_before_llm(monkeypatch):
    calls = []

    async def provider(payload, model, key):
        calls.append(True)
        return {}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    form = _form()
    form["data"]["history"] = json.dumps(["a"] * 5)
    r = client.post("/api/llm/interpret-context", **form)
    assert r.status_code == 422
    assert calls == []


def test_context_request_blocks_non_analytic_upload_without_provider(monkeypatch):
    calls = []
    async def provider(payload, model, key):
        calls.append(True)
        return {}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    r = client.post("/api/llm/interpret-context", files={
        "file": ("privado.txt", b"Pessoa: Ana", "text/plain"),
    }, data={"message": "Quero analisar medicos", "history": "[]"})
    assert r.status_code == 422
    assert calls == []


def test_confirmed_category_constant_is_checked_without_category_column():
    from llm_context import review_interpretation
    eligibility = {
        "capabilities": {"distribution": {"status": "needs_confirmation"}},
        "values": {"periods": [], "categories": [], "territories": []},
    }
    proposal = {"operation": "distribution", "indicator": "density",
                "period": "", "category": "medicos", "territory": ""}
    without = review_interpretation(proposal, eligibility)
    with_confirmation = review_interpretation(proposal, eligibility,
                                             category_constant="Médicos")
    assert without["slots"]["category"] == "not_confirmed_in_dataset"
    assert with_confirmation["slots"]["category"] == "found_in_dataset"
    assert with_confirmation["ready_to_execute"] is False


def test_semantic_proposal_becomes_verified_local_territory_selection(monkeypatch):
    import pandas as pd
    import main
    data = pd.DataFrame({"municipio":["Manaus","Tefé","Outro"],"codigo":["m1","m2","m3"],
        "periodo":["202406"]*3,"categoria":["MEDICINA"]*3,"quantidade":[3,4,5],"populacao":[1000]*3})
    fields={"territory":"municipio","territory_id":"codigo","period":"periodo","category":"categoria","count":"quantidade","population":"populacao"}
    options={"confirmed_roles":list(fields),"count_unit":"pessoas","fts_scope_confirmed":True,
             "object_confirmed":True,"population_denominator_confirmed":True,"period_filter":"202406","category_filter":"MEDICINA"}
    sent=[]
    async def provider(messages,*_args):
        sent.extend(messages)
        return {"operation":"comparisons","indicator":"density","period":"","category":"","territory":"",
                "intent":"ANALITICO","topic":"none"}
    monkeypatch.setattr(llm_bridge,"_call_gemini",provider)
    result=client.post("/api/llm/interpret-context",files={"file":("privado.csv",data.to_csv(index=False).encode())},
        data={"message":"Coloque Manaus e Tefé lado a lado","mapping":json.dumps(fields),"options":json.dumps(options)})
    assert result.status_code == 200, result.text
    body=result.json()
    assert body["origin"] == "INTERPRETACAO_LLM" and body["executed"] is False
    assert set(body["exploration"]["territory_ids"]) == {"code:m1","code:m2"}
    assert body["exploration"]["options_patch"]["comparison_indicator"] == "density"
    for secret in ("Manaus","Tefé","privado.csv","populacao","m1","m2"):
        assert secret not in " ".join(sent)
