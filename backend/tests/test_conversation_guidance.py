"""Intenções conversacionais e meta: respostas seguras não acionam análises."""
import llm_bridge
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_greeting_without_key_is_immediate_and_does_not_spend_quota(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    before = client.get("/api/llm/status").json()["requests_used_today"]
    response = client.post("/api/llm/interpret", json={"message": "Olá"})
    assert response.status_code == 200
    body = response.json()
    assert body["origin"] == "CANAL_SISTEMICO"
    assert "Que tipo de análise" in body["reply"]
    assert body["proposal"]["operation"] is None
    assert body["executed"] is False
    assert body["requires_confirmation"] is False
    assert client.get("/api/llm/status").json()["requests_used_today"] == before


def test_help_and_conceptual_density_use_governed_local_descriptions(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    for query, fragment in (
        ("o que você faz?", "Densidade"),
        ("como importar meus dados", "estrutura recomendada"),
        ("como se calcula a densidade?", "multiplicada por 1.000"),
        ("Meus dados vão para o Gemini?", "não recebe"),
    ):
        response = client.post("/api/llm/interpret", json={"message": query})
        assert response.status_code == 200, (query, response.text)
        assert fragment.lower() in response.json()["reply"].lower()
        assert response.json()["origin"] == "CANAL_SISTEMICO"


def test_llm_meta_topic_is_validated_against_local_catalog(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")
    async def provider(_sanitized, _model, _key):
        return {"operation": "none", "indicator": "none", "period": "",
                "category": "", "territory": "", "intent": "SOBRE_O_AGENTE",
                "topic": "workflow", "free_text": "Nunca executamos checagens"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    response = client.post("/api/llm/interpret", json={"message": "Explique o processo de preparação de análise"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["origin"] == "INTERPRETACAO_LLM"
    assert "três etapas" not in body["reply"] or "preparação" in body["reply"].lower()
    assert "Python" in body["reply"]
    assert "Nunca executamos checagens" not in body["reply"]
    assert body["proposal"]["operation"] is None


def test_guidance_with_dataset_is_not_forced_to_read_dataset(monkeypatch):
    import main

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("O dataset não deve ser carregado para uma saudação.")

    monkeypatch.setattr(main, "_request_dataset", forbidden)
    result = client.post("/api/llm/interpret-context", data={
        "dataset": "brazil", "message": "olá", "history": "[]",
        "mapping": "{}", "options": "{}",
    })
    assert result.status_code == 200, result.text
    assert result.json()["origin"] == "CANAL_SISTEMICO"
    assert result.json()["executed"] is False
