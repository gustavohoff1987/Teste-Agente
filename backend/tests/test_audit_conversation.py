"""A09/A10/A12/A13: propostas simuladas, sem rede ou autoridade analítica."""
import json

import pytest
from fastapi.testclient import TestClient

import llm_bridge
from dialogue_guidance import clarification_for
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


def test_a10_pending_context_allows_only_local_guidance(provider):
    install, calls = provider
    install(RAW)
    assert context("Quero distribuição", context_ready="false").status_code == 409
    greeting = context("Olá", context_ready="false")
    assert greeting.status_code == 200 and greeting.json()["origin"] == "CANAL_SISTEMICO"
    assert calls == []


@pytest.mark.parametrize("patch", [{"operation": "counts", "indicator": "density"},
    {"operation": "none", "intent": "SOBRE_O_AGENTE", "topic": []}, {"operation": []},
    {"indicator": {}}, {"category": 2}, {"period": None}, {"territory": []},
    {"intent": []}, {"topic": "invented"}, {"operation": "spatial", "indicator": "quantity"},
    {"operation": "rotation", "indicator": "density"}, {"operation": "aggregate", "indicator": "quantity"},
    {"intent": "CONVERSACIONAL"}])
def test_a12_invalid_response_is_a_controlled_error(provider, patch):
    install, _ = provider
    install({**RAW, **patch})
    response = client.post("/api/llm/interpret", json={"message": "Quero analisar Nurses em 2024"})
    assert response.status_code == 502, response.text
    assert "synthetic-offline" not in response.text


@pytest.mark.parametrize("field", list(RAW))
def test_a12_required_response_fields(provider, field):
    install, _ = provider
    install({k: v for k, v in RAW.items() if k != field})
    assert client.post("/api/llm/interpret", json={"message": "Quero distribuição"}).status_code == 502


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


@pytest.mark.parametrize("status,expected", [(401, 503), (403, 503), (429, 429), (500, 502)])
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
