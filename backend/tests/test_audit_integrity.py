"""Reproduções adversariais A01–A08 da auditoria de 11/10/2026."""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from pyproj import Geod

from main import app, read_dataset

client = TestClient(app)
M = {"territory": "Municipality", "period": "Year", "category": "Profession",
     "count": "Count", "population": "Population"}
O = {"count_unit": "pessoas", "population_denominator_confirmed": True,
     "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True,
     "comparison_confirmed": True}


def post(frame, operation, options=None, mapping=None, route="analyze"):
    return client.post("/api/" + route,
        files={"file": ("audit.csv", frame.to_csv(index=False).encode())},
        data={"operation": operation, "mapping": json.dumps(mapping or M),
              "options": json.dumps({**O, **(options or {})})})


@pytest.mark.parametrize("raw", [b"Year;Count\n2024;10;999\n", b"Year,Count\n2024\n",
    b'Year,Count\n2024,"10\n'])
def test_a01_malformed_csv_is_rejected_before_inspection_or_calculation(raw):
    with pytest.raises(ValueError):
        read_dataset(raw, "audit.csv")
    for route in ("inspect", "preflight", "analyze"):
        response = client.post("/api/" + route, files={"file": ("audit.csv", raw)},
            data={"operation": "counts", "mapping": json.dumps({"period": "Year", "count": "Count"}),
                  "options": json.dumps({"count_unit": "pessoas", "category_constant": "Nurses"})})
        assert response.status_code == 422


def test_a01_quoted_delimiters_newlines_blank_lines_and_leading_zero_are_preserved():
    frame, _ = read_dataset(b'Name;Code\n"A;B\nC";001\n\n', "audit.csv")
    assert frame.to_dict("records") == [{"Name": "A;B\nC", "Code": "001"}]


def temporal_frame():
    return pd.DataFrame({"Municipality": ["A", "A"], "Year": [2023, 2024],
        "Profession": ["Nurses"] * 2, "Count": [10, 20], "Population": [1000, 4000]})


@pytest.mark.parametrize("operation", ["temporal", "report"])
def test_a02_indicator_required_and_independent_of_other_confirmations(operation):
    frame = temporal_frame()
    assert post(frame, operation).status_code == 422
    for confirmed in (False, True):
        response = post(frame, operation, {operation + "_indicator": "quantity",
            "population_denominator_confirmed": confirmed})
        assert response.status_code == 200, response.text
        body = response.json()
        if operation == "temporal":
            assert body["rows"][0]["Variação (%)"] == 100
        else:
            assert "Densidade por 1.000" not in body["rows"][0]
    density = post(frame, operation, {operation + "_indicator": "density"})
    assert density.status_code == 200, density.text
    if operation == "temporal":
        assert density.json()["rows"][0]["Variação (%)"] == -50
    assert post(frame, operation, {operation + "_indicator": "density",
        "population_denominator_confirmed": False}).status_code == 422
    frame["Population"] = "invalid"
    assert post(frame, operation, {operation + "_indicator": "quantity"}).status_code == 200


@pytest.mark.parametrize("has_global_extremes", [False, True])
def test_a03_trend_uses_four_valid_observations_without_global_extremes(has_global_extremes):
    years_a = list(range(2020, 2026)) if has_global_extremes else [2020, 2021]
    frame = pd.DataFrame({"Municipality": ["A"] * len(years_a) + ["B"] * 4,
        "Year": years_a + [2021, 2022, 2023, 2025],
        "Profession": ["Nurses"] * (len(years_a) + 4), "Count": [10] * len(years_a) + [1, 2, 3, 5]})
    response = post(frame, "temporal", {"temporal_indicator": "quantity"},
                    {k: v for k, v in M.items() if k != "population"})
    assert response.status_code == 200, response.text
    row = next(r for r in response.json()["rows"] if r["Território"] == "B")
    assert row["Variação absoluta"] is None
    assert row["Tendência"] == "Crescimento"
    assert row["Final"] == 5


def test_a05_spatial_preserves_submeter_distance_in_result():
    frame = pd.DataFrame({"Municipality": ["A", "B"], "Latitude": [0, 0], "Longitude": [0, .000001]})
    response = post(frame, "spatial", {"crs": "SIRGAS2000", "reference_territory": "A"},
        {"territory": "Municipality", "latitude": "Latitude", "longitude": "Longitude"})
    assert response.status_code == 200, response.text
    expected = Geod(ellps="GRS80").inv(0, 0, .000001, 0)[2] / 1000
    assert response.json()["rows"][1]["Distância (km)"] == expected > 0


@pytest.mark.parametrize("operation", ["ranking", "comparisons", "distribution", "aggregate"])
def test_a07_homonyms_use_confirmed_codes_in_every_gate(operation):
    frame = pd.DataFrame({"Municipality": ["A", "A"], "Code": ["001", "002"],
        "Year": [2024, 2024], "Profession": ["Nurses"] * 2, "Count": [10, 20], "Population": [1000, 1000]})
    options = {"confirmed_roles": ["territory_id"], "distribution_indicator": "quantity",
        "population_additive_confirmed": True, "component_sum_confirmed": True}
    mapping = {**M, "territory_id": "Code"}
    gate = post(frame, operation, options, mapping, route="preflight").json()["capabilities"][operation]
    assert gate["status"] == "available", gate
    assert post(frame, operation, options, mapping).status_code == 200
    options["confirmed_roles"] = []
    assert post(frame, operation, options, mapping).status_code == 422


@pytest.mark.parametrize("unit,label", [("pessoas", "pessoas"), ("vinculos", "vínculos"),
    ("postos", "postos"), ("outro", "horas contratadas")])
def test_a08_distribution_keeps_count_unit_in_standalone_rows(unit, label):
    frame = temporal_frame()
    frame["Municipality"] = ["A", "B"]
    frame["Year"] = 2024
    response = post(frame, "distribution", {"distribution_indicator": "quantity", "count_unit": unit,
        "custom_count_unit": "horas contratadas"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["rows"][0]["Indicador"] == "Quantidade de " + label
    assert body["detail_rows"][0]["Quantidade de " + label] == 10
    assert all(r["Unidade de contagem"] == label for r in body["detail_rows"])


@pytest.mark.parametrize("counts,relation,difference", [([10, 20], "MENOR", -10),
    ([20, 10], "MAIOR", 10), ([10, 10], "IGUALDADE", 0)])
def test_a04_two_objects_compare_values_with_explicit_signed_operands(counts, relation, difference):
    frame = temporal_frame()
    frame["Municipality"] = ["A", "B"]
    frame["Year"], frame["Population"], frame["Count"] = 2024, 1000, counts
    comparison = post(frame, "comparisons").json()["rows"]
    assert len(comparison) == 1
    assert comparison[0]["Objeto A"] == "A" and comparison[0]["Objeto B"] == "B"
    assert comparison[0]["Relação A/B"] == relation
    assert comparison[0]["Diferença A − B"] == difference
    assert "Posição" not in comparison[0]
    ranking = post(frame, "ranking").json()["rows"]
    assert len(ranking) == 2 and "Posição" in ranking[0]


def test_a04_three_objects_keep_visual_order_and_do_not_create_pairwise_differences():
    frame = pd.DataFrame({"Municipality": ["C", "A", "B"], "Year": [2024]*3,
        "Profession": ["Nurses"]*3, "Count": [30, 10, 20], "Population": [1000]*3})
    rows = post(frame, "comparisons").json()["rows"]
    assert [r["Território"] for r in rows] == ["A", "B", "C"]
    assert all("Posição" not in r and "Diferença A − B" not in r for r in rows)
    assert [r["Próximo valor maior"] for r in rows] == [20, 30, None]


@pytest.mark.parametrize("crs", ["SIRGAS2000", "SIRGAS 2000", "SIRGAS-2000", "sirgas2000"])
def test_a06_crs_aliases_are_canonical_in_result_and_metadata(crs):
    frame = pd.DataFrame({"Municipality": ["A", "B"], "Latitude": [0, 0], "Longitude": [0, 1]})
    mapping = {"territory": "Municipality", "latitude": "Latitude", "longitude": "Longitude"}
    result = post(frame, "spatial", {"crs": crs, "reference_territory": "A"}, mapping)
    assert result.status_code == 200, result.text
    assert result.json()["metadata"]["options"]["crs"] == "SIRGAS2000"
    assert post(frame, "spatial", {"crs": "WGS84", "reference_territory": "A"}, mapping).status_code == 422
