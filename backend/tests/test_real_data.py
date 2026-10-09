"""Teste opt-in: lê os originais sem persistir ou versionar seus registros.

ADT_REAL_DATA_DIR indica a pasta de validação. O usuário declarou Contagem
como profissionais distintos no recorte, sem aditividade entre recortes.
"""
import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, read_dataset
from semantic_bridge import candidates, preflight

client = TestClient(app)


@pytest.fixture(scope="module")
def real_sources():
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    yield paths
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_real_municipal_density_and_all_rows_against_independent_arithmetic(real_sources):
    path = next(p for p in real_sources if p.suffix.lower() == ".csv")
    raw = path.read_bytes()
    frame, _ = read_dataset(raw, path.name)
    mapping, _ = candidates(frame)
    assert mapping["territory"] == "municipio"
    assert mapping["territory_id"] == "ibge"
    assert mapping["category"] == "categoria_profisional"
    names_only = {k:v for k,v in mapping.items() if k != "territory_id"}
    # Não inferir unidade de contagem nem substituir confirmação por nome de cabeçalho.
    initial = preflight(frame, names_only)
    assert initial["capabilities"]["density"]["status"] != "available"
    profile = initial["multiplicity"]
    assert profile["exact_duplicate_excess"] == 0
    assert profile["affected_records"] == 11528 and profile["groups"] == 5324
    # Definição expressa do usuário; não autoriza somar municípios ou períodos.
    options = {"confirmed_roles": ["territory_id"], "count_unit": "pessoas",
        "population_denominator_confirmed": True}
    data = {"mapping": json.dumps(mapping), "options": json.dumps(options)}
    response = client.post("/api/preflight", files={"file": (path.name, raw)}, data=data)
    assert response.status_code == 200, response.text
    ready = response.json()
    assert ready["multiplicity"]["affected_records"] == 0
    assert ready["capabilities"]["density"]["status"] == "available"
    assert ready["capabilities"]["rotation"]["status"] == "unavailable"
    assert ready["capabilities"]["aggregate"]["status"] != "available"
    result = client.post("/api/analyze", files={"file": (path.name, raw)}, data={**data, "operation": "density"})
    assert result.status_code == 200, result.text[:1000]
    actual = pd.DataFrame(result.json()["rows"])
    assert len(actual) == len(frame) == 122534
    assert actual.Território.nunique() == 5570
    expected = pd.DataFrame({"Território": frame.municipio + " [" + frame.ibge + "]",
        "Período": frame[mapping["period"]], "Categoria": frame[mapping["category"]],
        "q": pd.to_numeric(frame.Contagem), "p": pd.to_numeric(frame[mapping["population"]])})
    joined = actual.merge(expected, on=["Território", "Período", "Categoria"], validate="one_to_one")
    np.testing.assert_array_equal(joined.Quantidade, joined.q)
    np.testing.assert_array_equal(joined.População, joined.p)
    np.testing.assert_allclose(joined["Densidade por 1.000"], joined.q * 1000 / joined.p, rtol=1e-13)


def test_real_national_excel_recognition_counts_and_temporal(real_sources):
    path = next(p for p in real_sources if p.suffix.lower() == ".xlsx")
    raw = path.read_bytes()
    response = client.post("/api/inspect", files={"file": (path.name, raw)})
    assert response.status_code == 200, response.text
    info = response.json()
    assert info["row_count"] == 22
    assert info["suggested_category_constant"] == "Médicos"
    mapping = info["suggested_mapping"]
    options = {"confirmed_roles": ["count"], "category_constant": "Médicos", "count_unit": "pessoas",
               "temporal_comparability_confirmed": True}
    frame, _ = read_dataset(raw, path.name)
    for op in ("counts", "temporal", "report"):
        response = client.post("/api/analyze", files={"file": (path.name, raw)}, data={
            "mapping": json.dumps(mapping), "options": json.dumps(options), "operation": op})
        assert response.status_code == 200, response.text
        if op == "temporal":
            ordered = frame.sort_values(mapping["period"])
            a, b = float(ordered.iloc[0][mapping["count"]]), float(ordered.iloc[-1][mapping["count"]])
            row = response.json()["rows"][0]
            assert row["Inicial"] == a and row["Final"] == b
            assert row["Variação (%)"] == pytest.approx((b-a)/a*100)
