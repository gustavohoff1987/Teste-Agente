"""Intenções conversacionais e meta: respostas seguras não acionam análises."""
import llm_bridge
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@pytest.mark.parametrize("query,fragment", [
    ("O que é possível fazer nessa página?", "densidade"),
    ("O que o agente é capaz de fazer?", "critérios combinados"),
    ("Olá, o que posso fazer aqui?", "gráficos"),
    ("Quais são as suas funcionalidades?", "referência mais próxima"),
    ("Muito obrigada pela ajuda!", "De nada"),
])
def test_pre_source_questions_and_thanks_are_answered_without_provider_or_analysis(monkeypatch, query, fragment):
    async def forbidden(*_args):
        raise AssertionError("Orientação local não deve acionar o provedor.")
    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    before = client.get("/api/llm/status").json()["requests_used_today"]
    response = client.post("/api/llm/interpret", json={"message": query})
    assert response.status_code == 200, response.text
    body = response.json()
    assert fragment.lower() in body["reply"].lower()
    assert body["proposal"]["operation"] is None and body["executed"] is False
    assert body["origin"] == "CANAL_SISTEMICO"
    assert client.get("/api/llm/status").json()["requests_used_today"] == before


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


@pytest.mark.parametrize("query,fragment", [
    ("O que o agente é capaz de fazer?", "critérios combinados"),
    ("Muito obrigada pela ajuda!", "De nada"),
])
def test_pending_municipality_question_does_not_swallow_guidance(monkeypatch, query, fragment):
    import main

    async def forbidden(*_args, **_kwargs):
        raise AssertionError("Orientação não deve ler a base nem consumir o provedor.")

    monkeypatch.setattr(main, "_request_dataset", forbidden)
    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    result = client.post("/api/exploration/interpret", data={
        "dataset":"brazil", "message":query, "mapping":"{}",
        "options":'{"conversation_pending_operation":"comparisons","conversation_requested_count":2}',
    })
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["handled"] is True and fragment.lower() in body["reply"].lower()
    assert body["executed"] is False and "operation" not in body and "territory_ids" not in body
