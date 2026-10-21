"""Continuidade da conversa: territórios já escolhidos e "últimos N anos" (AT-34, RQ-GOV-23), sem cálculo."""
from datetime import datetime, timezone
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import exploration
from exploration import current_year, interpret_exploration
from main import app

MAP = {"territory": "municipio", "territory_id": "codigo_identificador", "period": "periodo",
       "category": "categoria_profissional", "count": "quantidade", "population": "populacao"}
OPTIONS = {"confirmed_roles": list(MAP), "count_unit": "pessoas", "population_denominator_confirmed": True,
           "comparison_confirmed": True, "temporal_comparability_confirmed": True,
           "territory_longitudinal_confirmed": True, "temporal_indicator": "quantity"}
# Base semestral de 2014 a 2024, como a base oficial (janeiro e junho).
PERIODS = [str(year) + month for year in range(2014, 2025) for month in ("01", "06")]
UNITS = [("Manaus", "130260"), ("Tefé", "130420"), ("Parintins", "130340"), ("Fora", "X04")]
SELECTED = ["code:130260", "code:130420", "code:130340"]
KEPT = "Mantive os 3 territórios já escolhidos na conversa: Manaus [130260], Tefé [130420] e Parintins [130340]. "


def build(periods=PERIODS):
    return pd.DataFrame([{"municipio": name, "codigo_identificador": code, "periodo": period,
                          "categoria_profissional": "MEDICINA", "quantidade": 10, "populacao": 1000}
                         for period in periods for name, code in UNITS])


@pytest.fixture
def frame():
    return build()


def followup(frame, message, **extra):
    return interpret_exploration(message, frame, MAP, {**OPTIONS, "territory_ids": SELECTED,
                                                       "exploration_operation": "comparisons", **extra})


def years(first, last):
    return [period for period in PERIODS if first <= int(period[:4]) <= last]


def test_last_years_with_divergent_anchors_offers_both_readings_and_keeps_the_territories(frame):
    body = followup(frame, "quero fazer a comparação dos últimos 5 anos", conversation_today="2026-10-21")
    assert body["handled"] is True and body["executed"] is False and body["operation"] == "comparisons"
    assert body["territory_ids"] == SELECTED  # os municípios da conversa continuam; nada é perguntado sobre eles
    assert "period_filter" not in body["options_patch"] and "period_filters" not in body["options_patch"]
    assert body["ambiguity"] == "AMB-04" and "pending_operation" not in body
    assert body["clarification"] == (KEPT + "“Últimos 5 anos” pode ser contado de duas formas: até o último período da "
                                     "base (de 2020 a 2024) ou até hoje (de 2022 a 2026; a base vai até 2024, então "
                                     "ficariam de 2022 a 2024). Qual você prefere? Nada foi calculado.")
    assert [(choice["label"], choice["draft"], choice["send"]) for choice in body["choices"]] == [
        ("De 2020 a 2024: até o último período da base", "Comparação de 2020 a 2024", True),
        ("De 2022 a 2024: até hoje, com os anos que a base tem", "Comparação de 2022 a 2024", True)]
    # Cada alternativa é um pedido comum, com os anos explícitos: o período entra e os territórios continuam.
    for choice, (first, last) in zip(body["choices"], [(2020, 2024), (2022, 2024)]):
        chosen = followup(frame, choice["draft"])
        assert chosen["territory_ids"] == SELECTED and "clarification" not in chosen
        assert chosen["options_patch"]["period_filters"] == years(first, last)
        assert chosen["reply"].startswith(KEPT)


def test_last_years_with_coinciding_anchors_applies_the_period_and_says_which(frame):
    body = followup(frame, "Compare os últimos 3 anos", conversation_today="2024-11-05")
    assert body["territory_ids"] == SELECTED and "clarification" not in body and "choices" not in body
    assert body["options_patch"]["period_filters"] == years(2022, 2024)
    assert body["reply"] == (KEPT + "“Últimos 3 anos”: de 2022 a 2024 (até o último período da base, que é também o "
                             "ano atual). Confira os parâmetros e as condições metodológicas e execute a análise na "
                             "preparação.")
    single = followup(frame, "Compare o último ano", conversation_today="2024-02-10")
    assert single["options_patch"]["period_filters"] == years(2024, 2024)
    assert "“Último ano”: 2024" in single["reply"]


def test_relative_period_alone_continues_the_active_analysis(frame):
    body = followup(frame, "E nos últimos dois anos?", conversation_today="2024-03-01", exploration_operation="temporal")
    assert body["operation"] == "temporal" and body["territory_ids"] == SELECTED
    assert body["options_patch"]["period_filters"] == years(2023, 2024)
    # Com as leituras em aberto, os períodos atuais da evolução não são trocados por "todos".
    pending = followup(frame, "E nos últimos dois anos?", conversation_today="2026-10-21", exploration_operation="temporal")
    assert pending["operation"] == "temporal" and pending["ambiguity"] == "AMB-04"
    assert "period_filters" not in pending["options_patch"] and "period_filter" not in pending["options_patch"]
    # Sem análise ativa, a frase não vira análise por conta própria.
    assert interpret_exploration("E nos últimos dois anos?", frame, MAP,
                                 {**OPTIONS, "territory_ids": SELECTED}) == {"handled": False}


def test_last_years_without_the_number_asks_how_many(frame):
    body = followup(frame, "Compare os últimos anos", conversation_today="2026-10-21")
    assert body["territory_ids"] == SELECTED and "choices" not in body and "ambiguity" not in body
    assert body["clarification"] == KEPT + "Quantos anos você quer considerar? Diga, por exemplo, “últimos 5 anos” ou “de 2020 a 2024”."
    assert "period_filters" not in body["options_patch"]


def test_turn_of_the_year_without_the_local_date_is_a_material_ambiguity(frame, monkeypatch):
    assert current_year({}, now=datetime(2026, 12, 31, 23, tzinfo=timezone.utc)) is None
    assert current_year({}, now=datetime(2027, 1, 1, 2, tzinfo=timezone.utc)) is None
    assert current_year({}, now=datetime(2026, 6, 1, tzinfo=timezone.utc)) == 2026
    assert current_year({"conversation_today": "2027-01-01"}, now=datetime(2026, 12, 31, 23, tzinfo=timezone.utc)) == 2027
    assert current_year({"conversation_today": "ontem"}, now=datetime(2026, 6, 1, tzinfo=timezone.utc)) == 2026
    monkeypatch.setattr(exploration, "current_year", lambda options, now=None: None)
    body = followup(frame, "Compare os últimos 5 anos")
    assert body["ambiguity"] == "AMBIGUIDADE_MATERIAL" and "choices" not in body
    assert "period_filters" not in body["options_patch"] and body["territory_ids"] == SELECTED
    assert body["clarification"].endswith("Diga os anos do período, por exemplo, “de 2020 a 2024”.")


def test_reading_without_years_in_the_base_is_explained_and_not_offered():
    old = build([period for period in PERIODS if period < "2016"])
    body = interpret_exploration("Compare os últimos 2 anos", old, MAP,
                                 {**OPTIONS, "territory_ids": SELECTED, "conversation_today": "2026-10-21"})
    assert [choice["draft"] for choice in body["choices"]] == ["Comparação de 2014 a 2015"]
    assert "até hoje (de 2025 a 2026; a base não tem competências nesse intervalo)" in body["clarification"]


def test_common_verbs_do_not_hide_a_complete_request(frame):
    body = followup(frame, "Quero fazer a comparação entre 2020 e 2024")
    assert "clarification" not in body and body["territory_ids"] == SELECTED
    assert body["options_patch"]["period_filters"] == years(2020, 2024)
    # Nomes citados continuam valendo no lugar dos já escolhidos, sem a frase de territórios mantidos.
    named = followup(frame, "Quero fazer a comparação de Manaus e Tefé")
    assert named["territory_ids"] == ["code:130260", "code:130420"] and not named["reply"].startswith("Mantive")


def test_relative_followup_through_the_api_keeps_the_selection_and_does_not_calculate():
    raw = ("municipio;codigo_identificador;periodo;categoria_profissional;quantidade;populacao\n" + "".join(
        name + ";" + code + ";" + period + ";MEDICINA;10;1000\n" for period in PERIODS for name, code in UNITS)).encode()
    client = TestClient(app)
    response = client.post("/api/exploration/interpret", files={"file": ("base.csv", raw)}, data={
        "message": "E nos últimos 5 anos?", "mapping": json.dumps(MAP),
        "options": json.dumps({**OPTIONS, "territory_ids": SELECTED, "exploration_operation": "comparisons",
                               "conversation_today": "2026-10-21"})})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["handled"] is True and body["executed"] is False and body["territory_ids"] == SELECTED
    assert body["ambiguity"] == "AMB-04" and len(body["choices"]) == 2
