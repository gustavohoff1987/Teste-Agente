"""Atos de visualização e de resultado anterior e tópicos metodológicos governados no contrato do intérprete.

O provedor é sempre simulado. "Mostre no gráfico", "volte ao resultado anterior" e perguntas sobre o método da
distribuição ou da referência mais próxima não calculam nem criam texto metodológico: os atos voltam como
dialogue_action para a interface, e as explicações são as formas PT do catálogo governado.
"""
import pytest
from fastapi.testclient import TestClient

import llm_bridge
from document_catalog import TOPICS, verify_documentation
from main import app

client = TestClient(app)
NONE = {"operation": "none", "indicator": "none", "period": "", "category": "", "territory": "",
        "intent": "CONVERSACIONAL", "topic": "none", "dialogue": "none", "social_reply": "", "candidates": []}


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")

    def install(answer):
        async def fake(*_args):
            return answer
        monkeypatch.setattr(llm_bridge, "_call_gemini", fake)
    return install


def test_contract_lists_the_new_acts_and_the_governed_topics():
    schema = llm_bridge._schema()["properties"]
    assert {"show_map", "show_chart", "show_table", "previous_result"} <= set(schema["dialogue"]["enum"])
    assert set(TOPICS) <= set(schema["topic"]["enum"]) and schema["topic"]["enum"][-1] == "none"
    assert "show_map" in llm_bridge._SYSTEM and "previous_result" in llm_bridge._SYSTEM


@pytest.mark.parametrize("dialogue", ["show_map", "show_chart", "show_table", "previous_result"])
def test_view_and_previous_result_are_dialogue_actions_without_calculation(provider, dialogue):
    provider({**NONE, "dialogue": dialogue})
    response = client.post("/api/llm/interpret", json={"message": "dá pra ver isso de outro jeito?"})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert answer["dialogue_action"] == dialogue
    assert answer["proposal"]["operation"] is None and answer["executed"] is False
    assert "recalcul" in answer["reply"]


@pytest.mark.parametrize("topic", ["distribution", "nearest"])
def test_method_questions_use_only_the_governed_forms(provider, topic):
    provider({**NONE, "intent": "CONCEITUAL_DOMINIO", "topic": topic})
    response = client.post("/api/llm/interpret", json={"message": "como esse método funciona por dentro?"})
    assert response.status_code == 200, response.text
    answer = response.json()
    assert [form["id_doc"] for form in answer["documentation"]] == list(TOPICS[topic])
    assert verify_documentation(answer["reply"], answer["documentation"])
    assert answer["proposal"]["operation"] is None and answer["executed"] is False


def test_methods_without_aligned_forms_are_not_explained_by_the_chat():
    # Tendência, mudança, comparação, contagem, ranking, critérios e rotatividade: formas com etapas não implementadas.
    assert set(TOPICS) == {"density", "spatial", "aggregation", "distribution", "nearest"}
