"""Comparação com competência dos valores e janela (D6, 19/10/2026): CAP-CMP-01 com CAP-TMP-01 e CAP-TEN-01.

Bases sintéticas importadas. As relações ficam só na competência dos valores e no formato de sempre; cada território
ganha um registro com valores, mudança e tendência na janela, sem variação percentual, razão nem diferença percentual
(AT-84). Sem a opção, a comparação segue o caminho anterior (test_audit_integrity.py, A04).
"""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app
from trend import METHOD_VERSION

client = TestClient(app)
M = {"territory": "Municipality", "period": "Year", "category": "Profession", "count": "Count", "population": "Population"}
O = {"count_unit": "pessoas", "population_denominator_confirmed": True, "temporal_comparability_confirmed": True,
     "territory_longitudinal_confirmed": True, "comparison_confirmed": True}
YEARS = ["2021", "2022", "2023", "2024"]


def series(counts: dict, populations: dict | None = None):
    rows = []
    for territory, values in counts.items():
        for year, value in zip(YEARS, values):
            if value is None:
                continue
            population = (populations or {}).get(territory, 1000)
            rows.append({"Municipality": territory, "Year": int(year), "Profession": "Nurses", "Count": value,
                         "Population": population})
    return pd.DataFrame(rows)


def post(frame, options=None):
    return client.post("/api/analyze", files={"file": ("janela.csv", frame.to_csv(index=False).encode())},
                       data={"operation": "comparisons", "mapping": json.dumps(M),
                             "options": json.dumps({**O, **(options or {})})})


def ok(response):
    assert response.status_code == 200, response.text
    return response.json()


WINDOW = {"period_filters": YEARS, "comparison_values_period": "2024"}


def test_pair_relates_in_the_values_period_and_each_territory_gets_change_and_trend():
    frame = series({"A": [10, 12, 15, 20], "B": [30, 29, 31, 30]})
    body = ok(post(frame, WINDOW))
    # rows no formato atual: um par A/B, só na competência dos valores.
    assert body["rows"] == [{"Período": "2024", "Categoria": "Nurses", "Indicador": "Densidade por 1.000",
                             "Unidade de contagem": "pessoas", "Objeto A": "A", "Valor A": 20.0, "Objeto B": "B",
                             "Valor B": 30.0, "Relação A/B": "MENOR", "Diferença A − B": -10.0, "Condição": "Comparável"}]
    detail = {row["Território"]: row for row in body["detail_rows"]}
    assert list(detail["A"]) == ["Território", "Categoria", "Período", "Quantidade", "População", "Densidade por 1.000",
                                 "Unidade de contagem", "Condição", "Período inicial", "Período final", "Inicial", "Final",
                                 "Variação absoluta", "Direção da mudança", "Condição da mudança", "Tendência",
                                 "Motivo da tendência", "Observações da tendência"]
    assert (detail["A"]["Quantidade"], detail["A"]["População"], detail["A"]["Densidade por 1.000"]) == (20, 1000, 20.0)
    assert (detail["A"]["Inicial"], detail["A"]["Final"], detail["A"]["Variação absoluta"]) == (10.0, 20.0, 10.0)
    assert (detail["A"]["Direção da mudança"], detail["A"]["Tendência"]) == ("Aumento", "Aceleração do crescimento")
    assert (detail["B"]["Direção da mudança"], detail["B"]["Tendência"], detail["B"]["Motivo da tendência"]) == (
        "Sem mudança", "Sem classificação", "Mudança de direção")
    # AT-84: nenhuma variação percentual, razão ou diferença percentual automática.
    assert not any("%" in key or "razão" in key.lower() or "percentual" in key.lower()
                   for row in body["rows"] + body["detail_rows"] for key in row)
    metadata = body["metadata"]
    assert metadata["comparacao"]["competencia_valores"] == "2024"
    assert metadata["comparacao"]["janela"] == {"periodos": YEARS, "inicio": "2021", "fim": "2024", "competencias": 4}
    assert metadata["comparacao"]["grupos"] == [{"nivel": None, "unidade_contagem": "pessoas", "objetos": ["A", "B"],
                                                 "relacoes": True}]
    assert metadata["tendencia"]["contagens"]["CRESCIMENTO_ACELERADO"] == 1
    assert metadata["tendencia"]["contagens"]["SEM_CLASSIFICACAO"] == 1
    assert metadata["mudanca"]["direcoes"] == {"AUMENTO": 1, "REDUCAO": 0, "SEM_MUDANCA": 1}
    assert metadata["metodos"] == {"tendencia": METHOD_VERSION}  # entra na chave de execução
    assert [(item["label"], item["value"]) for item in body["metrics"]] == [("Territórios comparados", 2),
                                                                          ("Competências na janela", 4)]
    assert any(note.startswith("Competência dos valores: 2024.") for note in body["notes"])
    assert "Classes de tendência lado a lado: entre territórios, só se lê se a classe é a mesma; as classes não têm ordem " \
           "entre si." in body["notes"]
    assert not any(note.startswith("Variação (%)") for note in body["notes"])
    # Sem a opção: o caminho anterior (relações em cada competência), sem detail_rows nem tendência; chave diferente.
    before = ok(post(frame, {"period_filters": YEARS}))
    assert [row["Período"] for row in before["rows"]] == YEARS and "detail_rows" not in before
    assert "comparacao" not in before["metadata"] and "metodos" not in before["metadata"]
    assert before["metadata"]["execution_key"] != metadata["execution_key"]


def test_requested_cardinality_prevails_in_the_values_period():
    # AT-84: três territórios pedidos; só dois têm registro em 2024. Nenhuma diferença de par é criada.
    frame = series({"A": [1, 2, 3, 4], "B": [2, 3, 4, 5], "C": [3, 4, 5, None]})
    body = ok(post(frame, WINDOW))
    assert all("Diferença A − B" not in row and "Relação A/B" not in row for row in body["rows"])
    assert [(row["Território"], row["Próximo valor maior"]) for row in body["rows"]] == [("A", 5.0), ("B", None)]
    c = {row["Território"]: row for row in body["detail_rows"]}["C"]
    assert c["Condição"] == "Não avaliável: sem registro na competência dos valores" and c["Quantidade"] is None
    assert c["Direção da mudança"] is None and c["Condição da mudança"] == "Não avaliável: observação ausente em um dos extremos"
    assert c["Tendência"] == "Não avaliável: série insuficiente"
    assert body["metadata"]["comparacao"]["sem_relacao"] == [
        {"objeto": "C", "motivo": "Não avaliável: sem registro na competência dos valores"}]
    assert body["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"


def test_quantity_comparison_and_base_zero_keep_only_what_the_indicator_has():
    frame = series({"A": [0, 1, 2, 3], "B": [5, 5, 5, 5]})
    body = ok(post(frame, {**WINDOW, "comparison_indicator": "quantity"}))
    a = {row["Território"]: row for row in body["detail_rows"]}["A"]
    assert "População" not in a and "Densidade por 1.000" not in a  # quantidade: sem população nem densidade
    assert (a["Quantidade"], a["Variação absoluta"], a["Direção da mudança"]) == (3, 3.0, "Aumento")
    assert a["Condição da mudança"] == "Avaliável"  # base zero só afeta o percentual, ausente da comparação
    assert body["rows"][0]["Indicador"] == "Quantidade" and body["rows"][0]["Relação A/B"] == "MENOR"


def test_the_window_needs_the_temporal_premises_and_the_values_period_inside_it():
    frame = series({"A": [10, 12, 15, 20], "B": [30, 29, 31, 30]})
    refused = post(frame, {**WINDOW, "temporal_comparability_confirmed": False})
    assert refused.status_code == 422 and "comparabilidade temporal" in refused.json()["detail"]
    outside = post(frame, {"period_filters": YEARS[:2], "comparison_values_period": "2024"})
    assert outside.status_code == 422
    assert "A competência dos valores precisa estar entre os períodos escolhidos" in outside.json()["detail"]
    invalid = post(frame, {"comparison_values_period": ["2024"]})
    assert invalid.status_code == 422 and "Competência dos valores inválida" in invalid.json()["detail"]
    # Uma competência só: valores lado a lado, sem janela e sem as premissas temporais.
    single = ok(post(frame, {"period_filter": "2024", "comparison_values_period": "2024",
                             "temporal_comparability_confirmed": False}))
    assert "tendencia" not in single["metadata"] and single["metadata"]["comparacao"]["mudanca_e_tendencia"] is False
    assert "Tendência" not in single["detail_rows"][0] and single["detail_rows"][0]["Densidade por 1.000"] == 20.0


@pytest.mark.parametrize("values,relation", [((10, 20), "MENOR"), ((10, 10), "IGUALDADE")])
def test_preflight_reports_the_window_like_the_analysis(values, relation):
    frame = series({"A": [1, 1, 1, values[0]], "B": [1, 1, 1, values[1]]})
    response = client.post("/api/preflight", files={"file": ("janela.csv", frame.to_csv(index=False).encode())},
                           data={"mapping": json.dumps(M), "options": json.dumps({**O, **WINDOW})})
    assert response.status_code == 200 and response.json()["capabilities"]["comparisons"]["status"] == "available"
    assert ok(post(frame, WINDOW))["rows"][0]["Relação A/B"] == relation
