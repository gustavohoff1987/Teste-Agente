"""Testes offline da primeira iteração Gemini: nenhuma chamada externa real."""
import pytest
from fastapi.testclient import TestClient

import llm_bridge
from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_local_limits(monkeypatch):
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ADT_GEMINI_MODEL", raising=False)


def test_without_key_is_degraded_and_keeps_analytical_engine_available():
    status = client.get("/api/llm/status")
    assert status.status_code == 200
    assert status.json()["configured"] is False
    assert status.json()["executes_analyses"] is False
    response = client.post("/api/llm/interpret", json={"message": "Densidade de médicos"})
    assert response.status_code == 503
    assert client.get("/api/health").status_code == 200


def test_interpretation_is_structured_sanitized_and_does_not_execute(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-private-key")
    captured = {}

    async def fake_model(sent, model, api_key):
        captured.update(sent=sent, model=model, api_key=api_key)
        return {"operation": "distribution", "indicator": "density",
                "period": "202406", "category": "médicos", "territory": "municípios"}

    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    question = "Quero distribuição da densidade de médicos por municípios em 202406"
    response = client.post("/api/llm/interpret", json={"message": question})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["executed"] is False
    assert body["origin"] == "INTERPRETACAO_LLM"
    assert body["proposal"]["operation"] == "distribution"
    assert body["proposal"]["indicator"] == "density"
    assert body["proposal"]["period"] == "202406"
    assert body["proposal"]["category"] == "médicos"
    assert captured["model"] == "gemini-2.5-flash-lite"
    assert captured["api_key"] == "test-private-key"
    assert "test-private-key" not in response.text
    assert "file" not in captured
    assert client.get("/api/llm/status").json()["requests_used_today"] == 1


def test_redaction_occurs_before_external_call(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    seen = []

    async def fake_model(sent, _model, _key):
        seen.extend(sent)
        return {"operation": "density", "indicator": "density",
                "period": "2024", "category": "médicos", "territory": ""}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    response = client.post("/api/llm/interpret", json={
        "message": "Quero densidade de médicos em 2024. CPF: 123.456.789-09, João Silva, joao@example.com."
    })
    assert response.status_code == 200, response.text
    joined = " ".join(seen)
    for forbidden in ("123.456.789-09", "João", "Silva", "joao@example.com"):
        assert forbidden not in joined
    assert "PROTEGID" in joined


def test_discard_model_invented_entities_and_unknown_schema(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    async def fake_model(_sent, _model, _key):
        return {"operation": "density", "indicator": "density",
                "period": "2035", "category": "Neurocirurgiões", "territory": "Fortaleza"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    response = client.post("/api/llm/interpret", json={"message": "Quero analisar médicos em 2024"})
    assert response.status_code == 200
    assert response.json()["proposal"]["period"] == ""
    assert response.json()["proposal"]["category"] == ""
    assert response.json()["proposal"]["territory"] == ""

    async def bad_model(_sent, _model, _key):
        return {"operation": "invented_operation", "indicator": "density"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", bad_model)
    invalid = client.post("/api/llm/interpret", json={"message": "Quero analisar médicos em 2024"})
    assert invalid.status_code == 502


def test_unknown_model_is_blocked_before_api(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    monkeypatch.setenv("ADT_GEMINI_MODEL", "model-billing-unknown")
    response = client.post("/api/llm/interpret", json={"message": "Comparar médicos"})
    assert response.status_code == 503
    assert "secret" not in response.text


def test_local_limit_applies_without_network_call(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    from datetime import date
    monkeypatch.setattr(llm_bridge, "_counter_day", date.today().isoformat())
    monkeypatch.setattr(llm_bridge, "_counter", llm_bridge.MAX_REQUESTS_PER_DAY)
    response = client.post("/api/llm/interpret", json={"message": "Analisar distribuição"})
    assert response.status_code == 429


def test_request_body_limits():
    response = client.post("/api/llm/interpret", json={"message": "a" * 801})
    assert response.status_code == 422


def test_history_is_limited_and_only_user_text_is_sent(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "secret")
    seen = []

    async def fake_model(sent, _model, _key):
        seen.extend(sent)
        return {"operation": "none", "indicator": "none",
                "period": "", "category": "", "territory": ""}
    monkeypatch.setattr(llm_bridge, "_call_gemini", fake_model)
    response = client.post("/api/llm/interpret",
                           json={"message": "E quanto à distribuição?", "history": [
                               "Quero analisar médicos", "Em municípios"]})
    assert response.status_code == 200
    assert len(seen) == 3
    assert response.json()["proposal"]["operation"] is None
    excessive = client.post("/api/llm/interpret",
                            json={"message": "E quanto à distribuição?", "history": ["Pergunta"] * 5})
    assert excessive.status_code == 422


def test_http_transport_uses_json_schema_header_and_no_dataset(monkeypatch):
    import asyncio
    import httpx
    captured = {}

    class FakeHTTPClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs["timeout"]

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, headers, json):
            captured.update(url=url, headers=headers, body=json)
            return httpx.Response(200, json={"candidates": [{"content": {"parts": [{
                "text": '{"operation":"distribution","indicator":"density","period":"2024",'
                        '"category":"médicos","territory":"municípios"}'
            }]}}]})

    monkeypatch.setattr(llm_bridge.httpx, "AsyncClient", FakeHTTPClient)
    response = asyncio.run(llm_bridge._call_gemini(
        ["Quero distribuição da densidade de médicos em municípios em 2024"],
        "gemini-2.5-flash-lite", "test-secret"))
    assert response["operation"] == "distribution"
    assert captured["url"].startswith("https://generativelanguage.googleapis.com/")
    assert captured["headers"]["x-goog-api-key"] == "test-secret"
    assert captured["timeout"] <= 30
    assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseSchema" in captured["body"]["generationConfig"]
    assert all(k not in captured["body"] for k in ("file", "mapping", "rows", "data"))
    assert "test-secret" not in str(captured["body"])
