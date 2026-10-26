"""Cobertura offline dos incrementos conversacionais FN-INT-01/02/03/META.

O modelo é simulado. Não há consumo de quota externa.
"""
import io

from fastapi.testclient import TestClient
import pytest

import llm_bridge
from dialogue_guidance import clarification_for, explicit_parallel_operations
from main import app


client = TestClient(app)


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "placeholder-for-tests")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")


def test_parallel_operations_are_not_confused_with_an_indicator():
    assert set(explicit_parallel_operations("Quero densidade e quantitativos")) == {
        "density", "counts"}
    assert explicit_parallel_operations("Quero distribuição da densidade de médicos") == []
    assert explicit_parallel_operations("Quero comparar a densidade ao longo do tempo") == []


def test_parallel_request_demands_user_decision_and_cannot_execute(monkeypatch):
    async def provider(_messages, _model, _key):
        return {"operation": "density", "indicator": "density",
                "period": "", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    result = client.post("/api/llm/interpret",
                         json={"message": "Quero densidade e quantitativos"})
    assert result.status_code == 200, result.text
    payload = result.json()
    assert payload["proposal"]["operation"] is None
    assert payload["clarification"]["code"] == "MULTIPLAS_CAPACIDADES"
    assert {choice["label"] for choice in payload["clarification"]["choices"]} == {
        "Densidade", "Quantitativos"}
    assert payload["clarification"]["source"] == "CATALOGO_LOCAL"
    assert payload["executed"] is False
    assert payload["requires_confirmation"] is True


def test_indicator_ambiguity_uses_only_closed_choices(monkeypatch):
    async def provider(_messages, _model, _key):
        return {"operation": "distribution", "indicator": "none",
                "period": "", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none",
                "suggested_value": "100000"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    result = client.post("/api/llm/interpret",
                         json={"message": "Quero a distribuição por município"})
    assert result.status_code == 200, result.text
    payload = result.json()
    question = payload["clarification"]
    assert question["code"] == "INDICADOR_DISTRIBUICAO"
    assert len(question["choices"]) == 2
    assert all("draft" in choice for choice in question["choices"])
    assert "100000" not in result.text
    assert payload["proposal"]["indicator"] is None
    assert payload["executed"] is False


def test_unknown_period_is_not_confirmed_via_clarification():
    proposal = {"operation": "density", "indicator": "density",
                "period": "203001", "category": "", "territory": ""}
    verification = {"slots": {"period": "not_confirmed_in_dataset",
                               "category": "not_requested",
                               "territory": "not_requested"}}
    question = clarification_for("Quero densidade em 203001", proposal, verification)
    assert question["code"] == "PERIODO_NAO_CONFIRMADO"
    assert question["choices"] == []
    assert "revisar o período" in question["prompt"]


def test_unmatched_profession_is_a_guided_choice_not_a_user_error():
    proposal = {"operation": "counts", "indicator": "quantity",
                "period": "", "category": "médicos", "territory": ""}
    verification = {"slots": {"period": "not_requested",
                               "category": "not_confirmed_in_dataset",
                               "territory": "not_requested"}}
    question = clarification_for("Quero saber quantos médicos existem no Brasil",
                                 proposal, verification)
    assert question["code"] == "CATEGORIA_NAO_CONFIRMADA"
    assert "localizar nos dados" in question["prompt"]
    assert "não foi confirmada" not in question["prompt"]
    assert question["choices"] == []


def test_local_meta_topics_are_redacted_by_gemini_from_the_catalog_and_greeting_stays_local(monkeypatch):
    # Desde 26/10/2026 (Frentes III e V): com o provedor disponível, a orientação do catálogo é redigida pelo Gemini a
    # partir do texto do catálogo e conferida (paráfrase fiel aparece); a saudação continua com o texto fixo, sem chamada.
    async def unexpected(*_args):
        raise AssertionError("A orientação do catálogo não passa pelo intérprete.")
    redigidas = []

    async def redige(sistema, mensagens, esquema, max_tokens=1200):
        redigidas.append(mensagens)
        pergunta = mensagens[-1]
        if "agregação" in pergunta:
            return {"resposta": "Na agregação, o conjunto soma as contagens dos componentes; por isso a mesma pessoa pode "
                                "entrar mais de uma vez (possível dupla contagem), e o total não é de pessoas únicas."}
        return {"resposta": "É a distância em linha reta entre as coordenadas, em km, calculada no elipsoide. Não é a "
                            "distância por estrada nem o tempo de deslocamento."}
    monkeypatch.setattr(llm_bridge, "_call_gemini", unexpected)
    monkeypatch.setattr(llm_bridge, "generate_structured", redige)
    for message, expected in (
        ("Como funciona a agregação territorial?", "dupla contagem"),
        ("O que é distância geodésica?", "linha reta"),
        ("Olá", "tipo de análise"),
    ):
        result = client.post("/api/llm/interpret", json={"message": message})
        assert result.status_code == 200, result.text
        payload = result.json()
        assert expected.lower() in payload["reply"].lower()
        assert payload["origin"] == "CANAL_SISTEMICO"
        assert payload["executed"] is False
        assert ("redacao" in payload) is (message != "Olá")
    assert len(redigidas) == 2
    # O texto do catálogo vai como resposta verificada (a referência e a reserva da paráfrase).
    assert "RESPOSTA_VERIFICADA" not in redigidas[0][0] and "resposta_verificada_do_sistema" in redigidas[0][0]


def test_local_meta_topics_without_the_provider_use_the_catalog_without_calls(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    async def unexpected(*_args, **_kwargs):
        raise AssertionError("Sem o provedor, nada é chamado.")
    monkeypatch.setattr(llm_bridge, "_call_gemini", unexpected)
    monkeypatch.setattr(llm_bridge, "generate_structured", unexpected)
    for message, expected in (("Como funciona a agregação territorial?", "sobreposição"),
                              ("O que é distância geodésica?", "direta")):
        payload = client.post("/api/llm/interpret", json={"message": message}).json()
        assert expected in payload["reply"].lower() and payload["origin"] == "CANAL_SISTEMICO" and "redacao" not in payload
    assert client.get("/api/llm/status").json()["requests_used_today"] == 0


def test_contextual_period_question_uses_python_preflight(monkeypatch):
    async def provider(_messages, _model, _key):
        return {"operation": "density", "indicator": "density",
                "period": "203001", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    source = (b"Unidade;Periodo;Categoria;Quantidade;Populacao\n"
              b"Teste;202406;Medicos;10;3000\n")
    result = client.post("/api/llm/interpret-context", files={
        "file": ("sintetica.csv", io.BytesIO(source), "text/csv")
    }, data={
        "message": "Quero densidade em 203001",
        "history": "[]",
        "mapping": '{"territory":"Unidade","period":"Periodo","category":"Categoria","count":"Quantidade","population":"Populacao"}',
        "options": '{"confirmed_roles":["territory","period","category","count","population"],"count_unit":"pessoas","fts_scope_confirmed":true,"object_confirmed":true,"population_denominator_confirmed":true}',
    })
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["verification"]["source"] == "BACKEND_PREFLIGHT"
    assert body["clarification"]["code"] == "PERIODO_NAO_CONFIRMADO"
    assert body["verification"]["ready_to_execute"] is False


def test_previous_period_requires_explicit_conversational_reference(monkeypatch):
    async def provider(_messages, _model, _key):
        return {"operation": "density", "indicator": "density",
                "period": "202406", "category": "medicos", "territory": "",
                "intent": "ANALITICO", "topic": "none"}
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    earlier = "Quero densidade de medicos em 202406"
    following = client.post("/api/llm/interpret", json={
        "message": "E nesse mesmo período?", "history": [earlier]})
    assert following.status_code == 200, following.text
    assert following.json()["proposal"]["period"] == "202406"
    assert following.json()["proposal"]["category"] == ""  # retomada explícita somente do período
    independent = client.post("/api/llm/interpret", json={
        "message": "Quero outro relatório", "history": [earlier]})
    assert independent.status_code == 200, independent.text
    assert independent.json()["proposal"]["period"] == ""
    assert independent.json()["proposal"]["category"] == ""


def test_model_can_return_competing_anchored_interpretations_without_choosing(monkeypatch):
    async def provider(*_args):
        return {"operation":"none","indicator":"none","period":"","category":"","territory":"",
                "intent":"ANALITICO","topic":"none","candidates":[
                    {"operation":"density","indicator":"density","anchor":"perfil dos municipios"},
                    {"operation":"counts","indicator":"quantity","anchor":"perfil dos municipios"}]}
    monkeypatch.setattr(llm_bridge,"_call_gemini",provider)
    response = client.post("/api/llm/interpret",json={"message":"Analise o perfil dos municipios"})
    assert response.status_code == 200, response.text
    body=response.json()
    assert body["proposal"]["operation"] is None and body["executed"] is False
    assert body["clarification"]["code"] == "AMBIGUIDADE_MATERIAL"
    assert {c["operation"] for c in body["clarification"]["choices"]} == {"density","counts"}
    assert len(body["interpretations"]) == 2


def test_unanchored_interpretation_alternatives_are_rejected(monkeypatch):
    async def provider(*_args):
        return {"operation":"none","indicator":"none","period":"","category":"","territory":"",
                "intent":"ANALITICO","topic":"none","candidates":[
                    {"operation":"density","indicator":"density","anchor":"pedido inexistente"}]}
    monkeypatch.setattr(llm_bridge,"_call_gemini",provider)
    result = client.post("/api/llm/interpret",json={"message":"Analise o perfil dos municipios"})
    # Alternativa sem âncora no pedido é violação do contrato: regenerações e, persistindo, a reserva (nada é proposto).
    assert result.status_code == 200 and result.json()["reserva"] is True
    assert result.json()["proposal"]["operation"] is None and result.json()["executed"] is False
