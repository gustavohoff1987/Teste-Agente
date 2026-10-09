"""Regressão da ponte semântica e do gate compartilhado com o motor.

Os exemplos representam estrutura, NÃO dados reais de profissionais.
"""
import io
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from main import app
from semantic_bridge import candidates, normalize_headers, preflight


client = TestClient(app)


def user_frame():
    return pd.DataFrame({
        "0": [1, 2, 3, 4],
        "Competência": [2021, 2022, 2023, 2024],
        "Total de médicos únicos": [50, 60, 66, 72],
    })


def user_file():
    frame = user_frame()
    return (";".join(frame.columns) + "\n" + "\n".join(
        ";".join(map(str, row)) for row in frame.itertuples(index=False, name=None)
    ) + "\n").encode("utf-8")


def test_suggest_names_and_unknown_zero_header():
    mapping, columns = candidates(user_frame())
    assert mapping == {"period": "Competência", "count": "Total de médicos únicos"}
    assert columns[0]["suspicious_header"] is True
    assert columns[2]["proposal"][0]["status"] == "proposed"


def test_preflight_count_unit_does_not_follow_name_only():
    frame = user_frame()
    mapping, _ = candidates(frame)
    a = preflight(frame, mapping)
    assert a["field_states"]["period"]["status"] == "recognized"
    assert a["field_states"]["count"]["status"] == "proposed"
    assert a["capabilities"]["counts"]["status"] == "needs_confirmation"
    assert a["capabilities"]["density"]["status"] == "unavailable"
    assert a["capabilities"]["temporal"]["status"] == "needs_confirmation"


def test_user_confirms_and_enables_count_and_temporal_without_territory():
    frame = user_frame()
    mapping, _ = candidates(frame)
    opts = {
        "confirmed_roles": ["count"],
        "count_unit": "pessoas",
        "category_constant": "Médicos",
        "temporal_comparability_confirmed": True,
    }
    matrix = preflight(frame, mapping, opts)
    assert matrix["capabilities"]["counts"]["status"] == "available"
    assert matrix["capabilities"]["temporal"]["status"] == "available"
    assert matrix["capabilities"]["density"]["status"] == "unavailable"

    data = {"file": ("base.csv", user_file())}
    response = client.post("/api/analyze", files=data, data={
        "operation": "temporal", "mapping": json.dumps(mapping),
        "options": json.dumps(opts),
    })
    assert response.status_code == 200, response.text
    assert response.json()["rows"][0]["Inicial"] == 50.0
    assert response.json()["rows"][0]["Final"] == 72.0
    assert response.json()["rows"][0]["Categoria"] == "Médicos"


def test_real_import_and_preflight_http():
    contents = user_file()
    inspected = client.post("/api/inspect", files={"file": ("base.csv", contents)})
    assert inspected.status_code == 200, inspected.text
    profile = inspected.json()
    assert profile["suggested_mapping"]["count"] == "Total de médicos únicos"
    assert profile["suggested_category_constant"] == "Médicos"
    assert profile["column_profiles"][0]["name"] == "0"
    assert profile["preflight"]["capabilities"]["counts"]["status"] == "needs_confirmation"
    response = client.post("/api/preflight", files={"file": ("base.csv", contents)}, data={
        "mapping": json.dumps(profile["suggested_mapping"]),
        "options": json.dumps({
            "confirmed_roles": ["count"], "count_unit": "pessoas",
            "category_constant": "Médicos",
        }),
    })
    assert response.status_code == 200, response.text
    assert response.json()["capabilities"]["counts"]["status"] == "available"
    assert response.json()["capabilities"]["temporal"]["status"] == "needs_confirmation"


def test_gate_prevents_unconfirmed_calculation():
    mapping, _ = candidates(user_frame())
    result = client.post("/api/analyze", files={"file": ("base.csv", user_file())}, data={
        "operation": "counts", "mapping": json.dumps(mapping), "options": "{}",
    })
    assert result.status_code == 422
    assert "não habilitada" in result.json()["detail"]


def test_non_health_category_not_assumed_from_semantic_similarity():
    frame = pd.DataFrame({"Categoria": ["Médico veterinário"], "Quantidade": [2], "Ano": [2024]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas"})
    assert gate["capabilities"]["counts"]["status"] == "needs_confirmation"
    assert any("força de trabalho" in item for item in gate["capabilities"]["counts"]["reasons"])


def test_empty_non_health_category_requires_fts_declaration():
    frame = pd.DataFrame({"Categoria": ["Eletricistas"], "Quantidade": [2], "Ano": [2024]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas"})
    assert gate["capabilities"]["counts"]["status"] == "needs_confirmation"


def test_numeric_zero_header_has_same_key_during_inspect_and_analysis():
    df = pd.DataFrame({0: ["X", "Y"], "Competência": [2023, 2024], "Quantidade": [4, 5]})
    normalized = normalize_headers(df)
    assert list(normalized.columns) == ["0", "Competência", "Quantidade"]
    mapping, _ = candidates(normalized)
    mapping["territory"] = "0"
    gate = preflight(normalized, mapping, {
        "confirmed_roles": ["territory"], "count_unit": "vinculos",
        "fts_scope_confirmed": True,
    })
    assert gate["field_states"]["territory"]["status"] == "confirmed"
    assert gate["capabilities"]["counts"]["status"] == "available"


def test_cannot_map_same_column_as_two_roles():
    frame = user_frame()
    with pytest.raises(ValueError, match="mesma coluna"):
        preflight(frame, {"territory": "Competência", "period": "Competência"})


def test_temporal_not_available_with_single_period():
    frame = pd.DataFrame({"Ano": [2024], "Categoria": ["Médicos"], "Quantidade": [5]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas",
                                      "temporal_comparability_confirmed": True})
    assert gate["capabilities"]["temporal"]["status"] == "unavailable"


def test_xlsx_numeric_header_is_normalized():
    wb = Workbook()
    ws = wb.active
    ws.append([0, "Competência", "Total de médicos únicos"])
    ws.append([1, 2024, 5])
    buffer = io.BytesIO()
    wb.save(buffer)
    response = client.post("/api/inspect", files={"file": ("teste.xlsx", buffer.getvalue())})
    assert response.status_code == 200, response.text
    assert response.json()["columns"][0] == "0"


def test_unsupported_coordinate_values_require_confirmation():
    frame = pd.DataFrame({"Território": ["A"], "Latitude": [110], "Longitude": [-48.0]})
    mapping, _ = candidates(frame)
    matrix = preflight(frame, mapping, {"crs": "SIRGAS2000", "reference_territory": "A"})
    assert matrix["field_states"]["latitude"]["status"] == "proposed"
    assert matrix["capabilities"]["spatial"]["status"] == "unavailable"


def test_report_without_population_is_quantitative_not_density():
    frame = user_frame()
    mapping, _ = candidates(frame)
    opts = {"confirmed_roles": ["count"], "count_unit": "pessoas", "category_constant": "Médicos"}
    response = client.post("/api/analyze", files={"file": ("base.csv", user_file())}, data={
        "mapping": json.dumps(mapping), "options": json.dumps(opts), "operation": "report",
    })
    assert response.status_code == 200, response.text
    row = response.json()["rows"][0]
    assert "Densidade por 1.000" not in row
