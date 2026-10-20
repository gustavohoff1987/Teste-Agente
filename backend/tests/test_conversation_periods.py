"""Competências citadas por extenso ou pelo ano na proposta do intérprete, como na gramática local.

"Densidade em junho de 2024" não pode receber "o período não foi encontrado" quando a base tem 202406; um ano com
várias competências fica em escolha, e uma competência inexistente continua com a pergunta. Provedor simulado.
"""
import io
import json

import pytest
from fastapi.testclient import TestClient

import llm_bridge
from llm_context import bind_local_parameters
from main import app

client = TestClient(app)
ELIGIBILITY = {"values": {"periods": ["202301", "202306", "202401", "202406"], "categories": ["MEDICINA"]}}
SOURCE = (b"Unidade;Periodo;Categoria;Quantidade;Populacao\n"
          b"Alfa;202401;Medicos;10;3000\nAlfa;202406;Medicos;12;3000\nBeta;202406;Medicos;8;5000\n")
MAPPING = {"territory": "Unidade", "period": "Periodo", "category": "Categoria", "count": "Quantidade",
           "population": "Populacao"}


@pytest.mark.parametrize("message,period,ambiguous", [
    ("Quero a densidade de médicos em junho de 2024", "202406", []),
    ("e em março de 2024?", "202403", []),  # não existe na base: o pré-exame recusa adiante
    ("densidade em 202406", "202406", []),
    ("quantos médicos em 2023", "", ["period"]),  # janeiro e junho: a escolha fica com o usuário
    ("junho de 2023 e junho de 2024", "", ["period"]),
    ("de janeiro a junho de 2024", "2024", []),  # intervalo de meses: nada é convertido, como antes
    ("densidade em 2030", "2030", []),
])
def test_period_mentions_become_the_base_competences(message, period, ambiguous):
    proposal = {"operation": "density", "indicator": "density", "period": "", "category": "", "territory": ""}
    assert bind_local_parameters(proposal, message, ELIGIBILITY) == ambiguous
    assert proposal["period"] == period


def ask(monkeypatch, message):
    async def provider(*_args):
        return {"operation": "density", "indicator": "density", "period": "", "category": "", "territory": "",
                "intent": "ANALITICO", "topic": "none"}
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    response = client.post("/api/llm/interpret-context", files={
        "file": ("sintetica.csv", io.BytesIO(SOURCE), "text/csv")}, data={
        "message": message, "history": "[]", "mapping": json.dumps(MAPPING),
        "options": json.dumps({"count_unit": "pessoas"})})
    assert response.status_code == 200, response.text
    return response.json()


def test_month_and_year_do_not_trigger_the_missing_period_question(monkeypatch):
    body = ask(monkeypatch, "Quero a densidade de médicos em junho de 2024")
    assert body["proposal"]["period"] == "202406"
    assert body["verification"]["slots"]["period"] == "found_in_dataset"
    assert body.get("clarification", {}).get("code") != "PERIODO_NAO_CONFIRMADO"
    assert body["executed"] is False and body["verification"]["ready_to_execute"] is False


def test_a_year_with_several_competences_stays_a_choice(monkeypatch):
    body = ask(monkeypatch, "Quero a densidade de médicos em 2024")
    assert body["proposal"]["period"] == ""
    assert body.get("clarification", {}).get("code") != "PERIODO_NAO_CONFIRMADO"
    assert any("mais de um período" in blocker for blocker in body["verification"]["blockers"])


def test_a_competence_outside_the_base_still_asks(monkeypatch):
    body = ask(monkeypatch, "Quero a densidade de médicos em junho de 2030")
    assert body["verification"]["slots"]["period"] == "not_confirmed_in_dataset"
    assert body["clarification"]["code"] == "PERIODO_NAO_CONFIRMADO"
