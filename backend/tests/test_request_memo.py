"""Memorização restrita à requisição: mesmos resultados, sem vazamento entre requisições."""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main
import request_memo
from data_contract import scoped
from territorial_selection import territory_catalog

MAP = {"territory": "municipio", "territory_id": "codigo", "period": "periodo",
       "category": "categoria", "count": "quantidade", "population": "populacao"}
OPTIONS = {"confirmed_roles": list(MAP)}


def frame(offset=0):
    return pd.DataFrame([{"municipio": name, "codigo": code, "periodo": "2024", "categoria": "MEDICINA",
                          "quantidade": str(q + offset), "populacao": "1000"}
                         for name, code, q in [("Alfa", "a1", 10), ("Beta", "b2", 20), ("Gama", "c3", 30)]])


def test_outside_a_request_nothing_is_memoized():
    data = frame()
    assert territory_catalog(data, MAP, OPTIONS) is not territory_catalog(data, MAP, OPTIONS)


def test_inside_a_request_same_inputs_share_one_result():
    data = frame()
    token = request_memo._MEMO.set({})
    try:
        first = territory_catalog(data, MAP, OPTIONS)
        assert territory_catalog(data, MAP, OPTIONS) is first
        # Outro quadro com o mesmo conteúdo, ou outras opções, não reaproveita a entrada.
        assert territory_catalog(frame(), MAP, OPTIONS) is not first
        assert territory_catalog(data, MAP, {**OPTIONS, "hierarchy_columns": {}}) is not first
        selected = {**OPTIONS, "territory_ids": ["code:a1"]}
        assert scoped(data, MAP, selected) is scoped(data, MAP, selected)
        assert len(scoped(data, MAP, {**OPTIONS, "territory_ids": ["code:a1", "code:b2"]})) == 2
        assert scoped(data, MAP, selected) is not data  # o recorte continua sendo um quadro próprio
        for _ in range(2):  # exceções não são memorizadas: a mesma recusa se repete
            with pytest.raises(ValueError, match="não pode ser vazia"):
                scoped(data, MAP, {**OPTIONS, "territory_ids": []})
    finally:
        request_memo._MEMO.reset(token)
    assert request_memo._MEMO.get() is None


def test_requests_never_reuse_each_others_results():
    client = TestClient(main.app)
    options = {**OPTIONS, "count_unit": "pessoas", "fts_scope_confirmed": True,
               "population_denominator_confirmed": True, "territory_ids": ["code:a1", "code:b2"]}

    def density(data):
        response = client.post("/api/analyze", files={"file": ("base.csv", data.to_csv(index=False).encode())},
                               data={"operation": "density", "mapping": json.dumps(MAP), "options": json.dumps(options)})
        assert response.status_code == 200, response.text
        return [row["Quantidade"] for row in response.json()["rows"]]

    assert density(frame()) == [10, 20]
    assert density(frame(offset=5)) == [15, 25]
    assert request_memo._MEMO.get() is None


def test_middleware_memoizes_within_one_http_request(monkeypatch):
    import territorial_selection
    invocations, computations = [], []
    memoized, profile = territorial_selection.territory_catalog, territorial_selection.curated_profile
    monkeypatch.setattr(territorial_selection, "territory_catalog",
                        lambda *a, **k: invocations.append(1) or memoized(*a, **k))
    monkeypatch.setattr(territorial_selection, "curated_profile",
                        lambda *a, **k: computations.append(1) or profile(*a, **k))  # uma por cálculo efetivo
    options = {**OPTIONS, "count_unit": "pessoas", "fts_scope_confirmed": True,
               "population_denominator_confirmed": True, "territory_ids": ["code:a1", "code:b2"]}
    response = TestClient(main.app).post("/api/analyze", files={"file": ("base.csv", frame().to_csv(index=False).encode())},
                                         data={"operation": "density", "mapping": json.dumps(MAP), "options": json.dumps(options)})
    assert response.status_code == 200, response.text
    assert len(invocations) > 5 and len(computations) < len(invocations) / 2
