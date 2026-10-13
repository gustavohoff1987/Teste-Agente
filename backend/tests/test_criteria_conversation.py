"""Comandos conversacionais dos critérios combinados: estruturam o pedido, nunca calculam nem escolhem."""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main
from criteria_conversation import criteria_command

client = TestClient(main.app)
CRITERIA = {"exploration_operation": "criteria"}
DENSITY = {"attribute": "densidade", "operator": "<", "value": "2", "unit": "por_1000_habitantes"}


def interpret(message, **options):
    """Pelo endpoint, com uma base importada mínima (a gramática dos critérios não lê dados)."""
    df = pd.DataFrame({"municipio": ["A", "B"], "periodo": ["2024", "2024"], "quantidade": [1, 2], "populacao": [10, 20]})
    response = client.post("/api/exploration/interpret", files={"file": ("x.csv", df.to_csv(index=False).encode())},
                           data={"message": message, "mapping": json.dumps({"territory": "municipio"}),
                                 "options": json.dumps(options)})
    assert response.status_code == 200, response.text
    return response.json()


def test_the_five_requested_commands_follow_the_conversational_state():
    first = interpret("Mostre os municípios com menos de 2 médicos por mil habitantes.")
    assert first["operation"] == "criteria" and first["criteria_patch"] == {"mode": "replace", "leaf": DENSITY}
    assert "“menos de” → <" in first["reply"] and "Nada foi calculado" in first["reply"] and first["executed"] is False
    second = interpret("Agora considere também distância superior a 150 km.", criteria=DENSITY, **CRITERIA)
    assert second["criteria_patch"] == {"mode": "and", "leaf": {"attribute": "distancia", "operator": ">", "value": "150", "unit": "km"}}
    assert "nenhuma referência foi escolhida pelo sistema" in second["reply"]
    third = interpret("Ordene esses municípios pela distância.", **CRITERIA)
    assert "decrescente" in third["clarification"] and third["criteria_pending_ranking"] == "distancia"
    answer = interpret("Decrescente.", criteria_pending_ranking="distancia", **CRITERIA)
    assert answer["criteria_patch"] == {"ranking": {"attribute": "distancia", "direction": "desc"}}
    fourth = interpret("Mostre os 20 primeiros.", ranking={"attribute": "distancia", "direction": "desc"}, **CRITERIA)
    assert fourth["criteria_patch"] == {"top_n": 20, "exact_n": False} and "EMPATE_NO_CORTE" in fourth["reply"]
    fifth = interpret("Compare esse conjunto com o anterior.", **CRITERIA)
    assert fifth["criteria_patch"] == {"compare": "previous"}


@pytest.mark.parametrize("phrase,operator", [
    ("abaixo de", "<"), ("menos de", "<"), ("inferior a", "<"), ("menor que", "<"), ("até", "<="), ("no máximo", "<="),
    ("acima de", ">"), ("mais de", ">"), ("superior a", ">"), ("maior que", ">"), ("a partir de", ">="), ("no mínimo", ">="),
    ("maior ou igual a", ">="), ("menor ou igual a", "<="), ("igual a", "="), ("diferente de", "!=")])
def test_operator_vocabulary_is_explicit_and_complete(phrase, operator):
    proposal = criteria_command(f"municípios com densidade {phrase} 2,36", {})
    assert proposal["criteria_patch"]["leaf"] == {"attribute": "densidade", "operator": operator, "value": "2.36"}
    assert "→" in proposal["reply"] and "único contexto da densidade" in proposal["reply"]


@pytest.mark.parametrize("message,leaf", [
    ("municípios com mais de 50 mil habitantes", {"attribute": "populacao", "operator": ">", "value": "50000", "unit": "habitantes"}),
    ("densidade inferior a 236 por 100 mil habitantes", {"attribute": "densidade", "operator": "<", "value": "236",
                                                          "unit": "por_100000_habitantes"}),
    ("municípios com distância maior que 155", {"attribute": "distancia", "operator": ">", "value": "155"}),
    ("municípios a mais de 800 metros", {"attribute": "distancia", "operator": ">", "value": "800", "unit": "m"}),
    ("quantidade de médicos menor que 3", {"attribute": "quantidade", "operator": "<", "value": "3"}),
])
def test_units_and_indicators_are_taken_only_from_the_request(message, leaf):
    assert criteria_command(message, {})["criteria_patch"]["leaf"] == leaf


@pytest.mark.parametrize("message,options,fragment", [
    ("municípios com menos de 2 médicos", {}, "quantidade de profissionais ou a densidade"),
    ("densidade abaixo de 2.360", {}, "sem separador de milhar"),
    ("densidade abaixo de 2 e distância acima de 100 km", {}, "uma condição por mensagem"),
    ("municípios com mais de 3", {}, "Não identifiquei o indicador"),
    ("Mostre os 20 primeiros.", CRITERIA, "por qual atributo ordenar"),
    ("Ordene pela densidade", CRITERIA, "crescente"),
])
def test_material_ambiguity_becomes_a_question(message, options, fragment):
    proposal = criteria_command(message, options)
    assert proposal["handled"] and "criteria_patch" not in proposal and fragment in proposal["clarification"]


def test_other_channels_keep_their_commands():
    assert criteria_command("Compare Manaus e Tefé", {}) is None  # comparação do Bloco 1
    assert criteria_command("Mostre a evolução de 2014 até 2024", {}) is None
    assert criteria_command("Calcule a referência mais próxima de Manaus", {}) is None
    assert criteria_command("Ordene esses municípios pela distância.", {}) is None  # fora do contexto de critérios
    assert criteria_command("Compare esse conjunto com o anterior.", {}) is None
    assert interpret("Compare A e B")["operation"] == "comparisons"


def test_successive_and_alternative_conditions_and_first_condition_without_previous():
    previous = {"criteria": DENSITY}
    assert criteria_command("agora também população acima de 10000", previous)["criteria_patch"]["mode"] == "and"
    assert criteria_command("ou com distância acima de 300 km", previous)["criteria_patch"]["mode"] == "or"
    assert criteria_command("agora também população acima de 10000", {})["criteria_patch"]["mode"] == "replace"
    assert criteria_command("Mostre os 10 mais distantes", CRITERIA)["criteria_patch"] == {
        "top_n": 10, "exact_n": False, "ranking": {"attribute": "distancia", "direction": "desc"}}
    exact = criteria_command("exatamente os 5 primeiros", {**CRITERIA, "ranking": {"attribute": "densidade", "direction": "asc"}})
    assert exact["criteria_patch"] == {"top_n": 5, "exact_n": True}


def test_the_llm_contract_does_not_receive_the_criteria_capability():
    from llm_bridge import OPERATIONS as LLM_OPERATIONS
    assert "criteria" not in LLM_OPERATIONS and "nearest" not in LLM_OPERATIONS
