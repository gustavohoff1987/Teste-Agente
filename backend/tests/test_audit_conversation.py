"""A09/A10/A12/A13: propostas simuladas, sem rede ou autoridade analítica."""
import json

import pytest
from fastapi.testclient import TestClient

import llm_bridge
from dialogue_guidance import clarification_for
import main
from main import app

client = TestClient(app, raise_server_exceptions=False)
RAW = {"operation": "distribution", "indicator": "density", "period": "2024",
       "category": "Nurses", "territory": "", "intent": "ANALITICO", "topic": "none"}


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "synthetic-offline")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    calls = []
    def install(raw):
        async def fake(*args):
            calls.append(args)
            return raw
        monkeypatch.setattr(llm_bridge, "_call_gemini", fake)
    return install, calls


def context(message, **extra):
    return client.post("/api/llm/interpret-context", files={"file": ("test.csv",
        b"Municipality,Year,Profession,Count\nA,2023,Nurses,1\nB,2023,Nurses,2\nA,2024,Nurses,3\n")},
        data={"message": message, "mapping": json.dumps({"territory": "Municipality", "period": "Year",
            "category": "Profession", "count": "Count"}), "options": json.dumps({"count_unit": "pessoas",
            "distribution_indicator": "quantity", "period_filter": "2023"}), **extra})


@pytest.mark.parametrize("indicator", ["density", "quantity"])
def test_a09_review_uses_proposed_indicator_and_period_not_current_gate(provider, indicator):
    install, _ = provider
    install({**RAW, "indicator": indicator})
    result = context("Quero distribuição de Nurses em 2024")
    assert result.status_code == 200, result.text
    v = result.json()["verification"]
    assert v["current_capability_status"] == "available"
    assert v["capability_status"] == "unavailable"  # sem população OU apenas um território em 2024
    assert v["blockers"] and not v["ready_to_execute"]
    assert not result.json()["executed"]


def test_a09_pending_period_association_is_not_reported_as_missing_value(provider):
    # Cabeçalho de período sem regra de reconhecimento ("Ref") fica como escolha pendente até ser escolhido no
    # seletor; o valor existe na base. (O período AAAAMM composto passou a ser reconhecido por regra, D1.)
    install, _ = provider
    raw = (b"Municipality,Ref,Profession,Count\n"
           b"A,202406,Nurses,1\nB,202406,Nurses,2\nA,202401,Nurses,3\n")
    mapping = {"territory": "Municipality", "period": "Ref", "category": "Profession", "count": "Count"}

    def review(period):
        install({**RAW, "operation": "counts", "indicator": "quantity", "period": period, "category": ""})
        response = client.post("/api/llm/interpret-context", files={"file": ("test.csv", raw)},
            data={"message": "Quero quantitativos em " + period, "mapping": json.dumps(mapping),
                  "options": json.dumps({"count_unit": "pessoas"})})
        assert response.status_code == 200, response.text
        return response.json()["verification"]

    pending = review("202406")
    assert pending["capability_status"] == "needs_confirmation", pending
    assert any("Escolha a coluna de Período no seletor" in b for b in pending["blockers"])
    assert not any("correspondência única" in b for b in pending["blockers"])
    assert pending["slots"]["period"] == "not_confirmed_in_dataset" and not pending["ready_to_execute"]
    absent = review("209912")
    assert absent["capability_status"] == "unavailable"
    assert any("correspondência única" in b for b in absent["blockers"])


def test_a10_pending_context_allows_only_local_guidance(provider):
    install, calls = provider
    install(RAW)
    assert context("Quero distribuição", context_ready="false").status_code == 409
    greeting = context("Olá", context_ready="false")
    assert greeting.status_code == 200 and greeting.json()["origin"] == "CANAL_SISTEMICO"
    assert calls == []


@pytest.mark.parametrize("ready", [None, "true", "True"])
def test_a10_context_is_ready_unless_the_form_says_otherwise(provider, ready):
    # Sem o campo, o contexto vale como pronto em qualquer versão do FastAPI (a 0.147 lê booleano
    # ausente como falso); só "false" explícito bloqueia a proposta analítica.
    install, _ = provider
    install(RAW)
    extra = {} if ready is None else {"context_ready": ready}
    assert context("Quero distribuição", **extra).status_code == 200
    assert context("Quero distribuição", context_ready="False").status_code == 409


@pytest.mark.parametrize("patch", [{"operation": "counts", "indicator": "density"},
    {"operation": "none", "intent": "SOBRE_O_AGENTE", "topic": []}, {"operation": []},
    {"indicator": {}}, {"category": 2}, {"period": None}, {"territory": []},
    {"intent": []}, {"topic": "invented"}, {"operation": "spatial", "indicator": "quantity"},
    {"operation": "rotation", "indicator": "density"}, {"operation": "aggregate", "indicator": "quantity"},
    {"intent": "CONVERSACIONAL"}])
def test_a12_invalid_response_is_regenerated_then_answered_by_the_reserve(provider, patch):
    # Saída fora do contrato (26/10/2026, seção 11.5): nova tentativa com a lista das violações, até 2 vezes (RQ-SIN-05);
    # persistindo, a resposta determinística de reserva, sem erro técnico, sem nada executado e sem a chave.
    install, calls = provider
    install({**RAW, **patch})
    response = client.post("/api/llm/interpret", json={"message": "Quero analisar Nurses em 2024"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["reserva"] is True and body["reply"] == main.RESERVA_DA_INTERPRETACAO and body["executed"] is False
    assert len(calls) == 3 and "VIOLACOES_DA_TENTATIVA_ANTERIOR" in " ".join(calls[1][0])
    assert "synthetic-offline" not in response.text and "HTTP" not in response.text


@pytest.mark.parametrize("field", list(RAW))
def test_a12_required_response_fields(provider, field):
    install, calls = provider
    install({k: v for k, v in RAW.items() if k != field})
    response = client.post("/api/llm/interpret", json={"message": "Quero distribuição"})
    assert response.status_code == 200 and response.json()["reserva"] is True and len(calls) == 3


def test_a13_current_period_cannot_be_overwritten_by_previous_period(provider):
    install, _ = provider
    install({**RAW, "operation": "counts", "indicator": "quantity", "period": "2023"})
    r = client.post("/api/llm/interpret", json={"message": "agora quero quantitativos em 2024",
        "history": ["Quero quantitativos de Nurses em 2023"]})
    assert r.status_code == 200, r.text
    assert r.json()["proposal"]["period"] != "2023"


def test_a13_indicator_choice_preserves_explicit_scope(provider):
    install, _ = provider
    question = "Quero distribuição de nurses em 2024 por municípios"
    proposal = {"operation": "distribution", "indicator": None, "period": "2024",
        "category": "nurses", "territory": "municípios"}
    clarification = clarification_for(question, proposal, None)
    draft = clarification["choices"][1]["draft"]
    install({**RAW, "indicator": "quantity", "category": "nurses", "territory": "municípios"})
    r = client.post("/api/llm/interpret", json={"message": draft, "history": [question]})
    assert r.status_code == 200, r.text
    for slot in ("period", "category", "territory"):
        assert r.json()["proposal"][slot] == proposal[slot]


@pytest.mark.parametrize("status,expected", [(401, 503), (403, 503), (429, 429), (500, 502), (503, 502), (504, 502)])
def test_provider_http_errors_are_controlled_without_network(monkeypatch, status, expected):
    import asyncio
    import httpx
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return httpx.Response(status, text="sensitive provider error")
    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", Client)
    with pytest.raises(llm_bridge.LLMError) as error:
        asyncio.run(llm_bridge._call_gemini(["Quero quantitativos"], "gemini-3.5-flash-lite", "synthetic"))
    assert error.value.status == expected
    assert "sensitive" not in str(error.value)
    assert "Tempo limite" not in str(error.value)  # HTTP 504 do provedor não é timeout do cliente.


@pytest.mark.parametrize("failure", ["timeout", "connection", "invalid_json", "empty_candidates"])
def test_provider_transport_and_payload_failures(monkeypatch, failure):
    import asyncio
    import httpx
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            if failure == "timeout":
                raise httpx.ReadTimeout("synthetic")
            if failure == "connection":
                raise httpx.ConnectError("synthetic")
            return httpx.Response(200, text="invalid" if failure == "invalid_json" else '{"candidates":[]}')
    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", Client)
    with pytest.raises(llm_bridge.LLMError) as error:
        asyncio.run(llm_bridge._call_gemini(["Quero quantitativos"], "gemini-3.5-flash-lite", "synthetic"))
    assert error.value.status == (503 if failure in ("timeout", "connection") else 502)
