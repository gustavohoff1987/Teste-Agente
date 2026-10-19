"""Contratos HTTP, cálculos independentes e entradas adversariais, sem dados pessoais reais."""
import io
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, compute, read_dataset
from semantic_bridge import candidates, preflight, OPERATIONS
from data_contract import period_positions

client = TestClient(app)
M = {"territory": "Municipality", "period": "Year", "category": "Profession",
     "count": "Count", "population": "Population"}
O = {"count_unit": "pessoas", "report_indicator": "quantity", "population_denominator_confirmed": True}


def sample():
    return pd.DataFrame({"Municipality": ["Springfield", "Springfield", "River", "River"],
        "Code": ["001", "002", "003", "003"], "Year": [2023, 2023, 2023, 2024],
        "Profession": ["Nurses"] * 4, "Count": [10, 20, 30, 36],
        "Population": [1000, 4000, 5000, 6000]})


def post(path, frame, mapping=M, options=None, operation="density"):
    return client.post(path, files={"file": ("synthetic.csv", frame.to_csv(index=False).encode())},
                       data={"mapping": json.dumps(mapping), "options": json.dumps(O if options is None else options), "operation": operation})


def test_homonyms_are_resolved_by_confirmed_code_without_adding_counts_or_population():
    df = sample()
    before = preflight(df, M, O)
    assert before["multiplicity"]["affected_records"] == 2
    assert before["multiplicity"]["groups"] == 1
    assert before["capabilities"]["density"]["status"] == "needs_confirmation"
    mapping = {**M, "territory_id": "Code"}
    assert preflight(df, mapping, O)["capabilities"]["density"]["status"] == "needs_confirmation"
    opts = {**O, "confirmed_roles": ["territory_id"]}
    ready = post("/api/preflight", df, mapping, opts).json()
    assert ready["capabilities"]["density"]["status"] == "available"
    response = post("/api/analyze", df, mapping, opts)
    assert response.status_code == 200, response.text
    rows = response.json()["rows"]
    assert rows[0]["Território"] == "Springfield [001]"
    assert rows[0]["Densidade por 1.000"] == 10
    assert rows[1]["Densidade por 1.000"] == 5
    assert sum(r["Quantidade"] for r in rows) == 96
    assert response.json()["metadata"]["mapping"]["territory"] == "Municipality"


def test_exact_duplicates_need_specific_authorization_and_preserve_original():
    df = sample().iloc[[2, 2]].copy()
    original = df.copy(deep=True)
    assert post("/api/analyze", df).status_code == 422
    opts = {**O, "rows_additive_confirmed": True, "component_columns": ["Code"]}
    assert post("/api/analyze", df, options=opts).status_code == 422
    result = post("/api/analyze", df, options={**O, "duplicate_policy": "remove_exact"})
    assert result.status_code == 200, result.text
    assert result.json()["rows"][0]["Quantidade"] == 30
    assert result.json()["rows"][0]["População"] == 5000
    pd.testing.assert_frame_equal(df, original)


def test_authorized_disaggregation_keeps_population_once():
    df = sample().iloc[[2, 2]].reset_index(drop=True)
    df["Sector"] = ["Public", "Private"]
    df["Count"] = [10, 15]
    opts = {**O, "component_columns": ["Sector"]}
    # D1: escolher as colunas dos componentes aplica a premissa de soma das partes, com nota e limitação.
    implicit = post("/api/analyze", df, options=opts)
    assert implicit.status_code == 200, implicit.text
    assert "rows_additive_confirmed" in implicit.json()["metadata"]["options"]["analysis_premises"]
    assert implicit.json()["metadata"]["evaluability"]["limitacoes"] == ["SOMA_COM_POSSIVEL_DUPLA_CONTAGEM"]
    assert post("/api/analyze", df, options={**opts, "rows_additive_confirmed": False}).status_code == 422  # recusa explícita
    result = post("/api/analyze", df, options={**opts, "rows_additive_confirmed": True})
    assert result.status_code == 200, result.text
    assert result.json()["rows"] == implicit.json()["rows"]
    row = result.json()["rows"][0]
    assert (row["Quantidade"], row["População"], row["Densidade por 1.000"]) == (25, 5000, 5)
    df.loc[1, "Population"] = 6000
    assert post("/api/analyze", df, options={**opts, "rows_additive_confirmed": True}).status_code == 422


@pytest.mark.parametrize("column,value", [("Count", float("inf")), ("Count", -1), ("Count", 1.5), ("Count", None),
    ("Municipality", " "), ("Year", ""), ("Profession", ""), ("Population", 0), ("Population", -1), ("Population", "inf")])
def test_invalid_inputs_never_pass_preflight_then_fail_at_execution(column, value):
    df = sample().iloc[[2, 3]].copy()
    df[column] = df[column].astype(object)
    df.iloc[0, df.columns.get_loc(column)] = value
    gate = post("/api/preflight", df)
    assert gate.status_code == 200, gate.text
    assert gate.json()["capabilities"]["density"]["status"] != "available"
    assert post("/api/analyze", df).status_code == 422


def test_unused_population_does_not_block_counts_or_unconfirmed_distribution():
    df = sample().iloc[:3].copy()
    df["Municipality"] = ["A", "B", "C"]
    df["Population"] = [None, "wrong", -1]
    opts = {"count_unit": "vinculos", "report_indicator": "quantity"}
    for op in ("counts", "distribution", "report"):
        settings = {**opts, "distribution_indicator": "quantity"} if op == "distribution" else opts
        response = post("/api/analyze", df, options=settings, operation=op)
        assert response.status_code == 200, response.text
    assert post("/api/analyze", df, options=opts).status_code == 422


def test_filter_is_applied_before_validating_unselected_rows():
    df = sample().iloc[[2, 3]].copy()
    df.iloc[0, df.columns.get_loc("Population")] = 0
    assert post("/api/analyze", df, options={**O, "period_filter": "2024"}).status_code == 200
    assert post("/api/analyze", df, options={**O, "period_filter": "1900"}).status_code == 422


def test_comparisons_and_distribution_do_not_pool_periods_or_break_ties():
    df = pd.DataFrame({"Municipality": ["A", "B", "C"] * 2, "Year": [2023]*3+[2024]*3,
        "Profession": ["Nurses"]*6, "Count": [2, 4, 4, 30, 20, 10], "Population": [1000]*6})
    opts = {**O, "comparison_confirmed": True, "quantile_count": 2}
    for operation in ("ranking",):
        rows = post("/api/analyze", df, options=opts, operation=operation).json()["rows"]
        assert [r["Posição"] for r in rows] == [1, 1, 3, 1, 2, 3]
    assert post("/api/analyze", df, options={**opts, "distribution_indicator": "density"},
                operation="distribution").status_code == 422
    for year, expected in (("2023", [3, 0]), ("2024", [2, 1])):
        outcome = post("/api/analyze", df,
                       options={**opts, "distribution_indicator": "density", "period_filter": year},
                       operation="distribution")
        assert outcome.status_code == 200, outcome.text
        rows = outcome.json()["rows"]
        assert [r["Unidades"] for r in rows] == expected
        assert {r["Período"] for r in rows} == {year}
        assert all("Limite superior" not in r for r in rows)
        assert len(outcome.json()["detail_rows"]) == 3
        assert all("Densidade por 1.000 habitantes" in r for r in outcome.json()["detail_rows"])


def test_territories_in_different_periods_are_not_a_comparison_universe():
    df = sample().iloc[[2, 3]].copy()
    df["Municipality"] = ["A", "B"]
    for op in ("comparisons", "ranking", "distribution", "temporal"):
        assert post("/api/analyze", df, options={**O, "comparison_confirmed": True,
            "temporal_indicator": "quantity", "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True}, operation=op).status_code == 422


def test_calendar_positions_and_incomplete_temporal_series():
    assert period_positions(["202312", "202401"])["202401"] - period_positions(["202312", "202401"])["202312"] == 1
    for values in (["202313", "202401"], ["1", "1.0"], ["inf", "2"]):
        with pytest.raises(ValueError):
            period_positions(values)
    df = pd.DataFrame({"Municipality": ["A"]*4+["B"], "Year": ["2023-12", "2024-01", "2024-02", "2024-03", "2024-01"],
        "Profession": ["Nurses"]*5, "Count": [10, 12, 15, 16, 8]})
    opts = {"count_unit": "pessoas", "temporal_indicator": "quantity", "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True}
    response = post("/api/analyze", df, {k:v for k,v in M.items() if k != "population"}, opts, "temporal")
    assert response.status_code == 200, response.text
    rows = response.json()["rows"]
    assert rows[0]["Tendência"] == "Crescimento"
    assert rows[0]["Variação (%)"] == 60
    assert rows[1]["Variação (%)"] is None


def individual():
    return pd.DataFrame({"Municipality": ["A", "A", "B", "A", "B"], "Year": [2,2,2,10,10],
        "Profession": ["Nurses"]*5, "Identity": ["person-x", "person-x", "person-x", "person-y", "person-x"], "Population": [1000]*5})


def test_individual_union_is_deduplicated_and_cohort_is_private():
    df = individual()
    mapping = {**M, "identity": "Identity"}; del mapping["count"]
    opts = {**O, "identity_count_confirmed": True, "identity_union_confirmed": True,
        "population_additive_confirmed": True, "period_filter": "2"}
    result = post("/api/analyze", df, mapping, opts, "aggregate")
    assert result.status_code == 200, result.text
    assert result.json()["rows"][0]["Quantidade"] == 1
    assert result.json()["rows"][0]["População"] == 2000
    rotation_opts = {"longitudinal_identity_confirmed": True, "territory_longitudinal_confirmed": True, "cohort_coverage_confirmed": True}
    result = post("/api/analyze", df, mapping, rotation_opts, "rotation")
    assert result.status_code == 200, result.text
    assert "person-x" not in result.text and "person-y" not in result.text
    rows = result.json()["rows"]
    assert [r["Rotatividade (%)"] for r in rows] == [100, 0]
    assert all(r["Rotatividade (%)"] + r["Permanência (%)"] == 100 for r in rows)
    assert all(r["Período inicial"] == "2" and r["Período final"] == "10" for r in rows)
    for bad in ({"period_filter": "2"}, {"initial_period": "10", "final_period": "2"}, {"cohort_coverage_confirmed": False}):
        assert post("/api/analyze", df, mapping, {**rotation_opts, **bad}, "rotation").status_code == 422


@pytest.mark.parametrize("crs", ["SIRGAS_2000", "SIRGAS2000"])
def test_spatial_decimal_comma_sirgas_and_coordinate_conflict(crs):
    df = pd.DataFrame({"Municipality": ["A", "B"], "Latitude": ["0,0", "0,0"], "Longitude": ["0,0", "1,0"]})
    mapping = {"territory": "Municipality", "latitude": "Latitude", "longitude": "Longitude"}
    opts = {"number_format": "decimal_comma", "confirmed_roles": ["latitude", "longitude"], "crs": crs, "reference_territory": "A"}
    result = post("/api/analyze", df, mapping, opts, "spatial")
    assert result.status_code == 200, result.text
    assert result.json()["rows"][1]["Distância (km)"] == pytest.approx(111.319, abs=.001)
    df.loc[1, "Municipality"] = "A"
    assert post("/api/preflight", df, mapping, opts).json()["capabilities"]["spatial"]["status"] == "unavailable"


def test_export_payload_keeps_every_result_and_method_metadata():
    df = pd.DataFrame({"Municipality": [f"T{i}" for i in range(180)], "Year": [2024]*180,
        "Profession": ["Nurses"]*180, "Count": range(180), "Population": [1000]*180})
    result = post("/api/analyze", df).json()
    assert len(result["rows"]) == result["total_rows"] == 180
    assert result["metadata"]["operation"] == "density"
    assert len(result["metadata"]["data_sha256"]) == 64


@pytest.mark.parametrize("opts", [{"population_denominator_confirmed": "false"}, {"quantile_count": 2.5}, {"quantile_count": 1}])
def test_malformed_options_do_not_enable_operation(opts):
    df = sample().iloc[:3].copy(); df["Municipality"] = ["A", "B", "C"]
    assert post("/api/analyze", df, options={**O, **opts}, operation="distribution").status_code == 422


def test_import_preserves_codes_and_rejects_duplicate_headers():
    df, _ = read_dataset(b"Municipality,Code,Count\nA,001,3\n", "a.csv")
    assert df.loc[0, "Code"] == "001"
    with pytest.raises(ValueError, match="duplicados"):
        read_dataset(b"Count,Count\n2,3\n", "a.csv")
    buffer = io.BytesIO()
    pd.DataFrame([[2, 3]], columns=["Count", "Count"]).to_excel(buffer, index=False)
    with pytest.raises(ValueError, match="duplicados"):
        read_dataset(buffer.getvalue(), "a.xlsx")


def test_all_ten_operations_have_successful_http_execution():
    df = pd.DataFrame({"Municipality": ["A", "B"]*4, "Year": [2021,2021,2022,2022,2023,2023,2024,2024],
        "Profession": ["Nurses"]*8, "Count": [10,20,12,22,13,24,16,30], "Population": [1000,2000]*4,
        "Latitude": [0,1]*4, "Longitude": [0,1]*4, "Identity": ["synthetic-a", "synthetic-b"]*4})
    mapping = {**M, "latitude": "Latitude", "longitude": "Longitude", "identity": "Identity"}
    opts = {**O, "comparison_confirmed": True, "temporal_indicator": "quantity", "temporal_comparability_confirmed": True,
        "territory_longitudinal_confirmed": True, "longitudinal_identity_confirmed": True,
        "cohort_coverage_confirmed": True, "crs": "SIRGAS2000", "reference_territory": "A",
        "population_additive_confirmed": True, "component_sum_confirmed": True}
    for op in OPERATIONS:
        settings = {**opts, **({"period_filter": "2024", "distribution_indicator": "density"} if op == "distribution" else
                             {"period_filter": "2024"} if op == "aggregate" else
                             {"period_filter": "2024", "reference_mode": "list", "reference_ids": ["name:A"]}
                             if op == "nearest" else
                             {"period_filter": "2024", "criteria": {"attribute": "densidade", "operator": ">=", "value": "15"}}
                             if op == "criteria" else {})}
        gate = post("/api/preflight", df, mapping, settings).json()["capabilities"][op]
        assert gate["status"] == "available", (op, gate)
        result = post("/api/analyze", df, mapping, settings, op)
        assert result.status_code == 200, (op, result.text)
        assert result.json()["total_rows"] > 0


@pytest.mark.parametrize("role", ["territory", "period", "category", "population", "count"])
def test_global_declarations_do_not_authorize_unconfirmed_field_mapping(role):
    df = sample().iloc[[2, 3]].rename(columns={M[role]: "Unrecognized field"})
    mapping = {**M, role: "Unrecognized field"}
    options = {**O, "fts_scope_confirmed": True, "single_period_confirmed": True}
    gate = post("/api/preflight", df, mapping, options).json()["capabilities"]["density"]
    assert gate["status"] != "available"
    assert post("/api/analyze", df, mapping, options).status_code == 422
    options["confirmed_roles"] = [role]
    assert post("/api/analyze", df, mapping, options).status_code == 200


def test_distribution_requires_explicit_indicator_and_selects_valid_universe():
    frame = pd.DataFrame({
        "Municipality": ["A", "B", "C"] * 2,
        "Year": [2023] * 3 + [2024] * 3,
        "Profession": ["Nurses"] * 6,
        "Count": [1, 3, 5, 2, 4, 6],
        "Population": [1000, 2000, 3000] * 2,
    })
    missing = post("/api/preflight", frame, options=O).json()["capabilities"]["distribution"]
    assert missing["status"] == "needs_confirmation"
    assert "indicador" in " ".join(missing["reasons"])
    for indicator in ("quantity", "density"):
        options = {**O, "distribution_indicator": indicator, "period_filter": "2024"}
        response = post("/api/analyze", frame, options=options, operation="distribution")
        assert response.status_code == 200, response.text
        body = response.json()
        assert sum(item["Unidades"] for item in body["rows"]) == 3
        assert len(body["detail_rows"]) == 3
        assert {r["Período"] for r in body["detail_rows"]} == {"2024"}
        assert all("Quintil" in r for r in body["detail_rows"])
        assert all("Limite superior" not in r for r in body["rows"])


def test_distribution_quantity_never_reads_population_unless_density_selected():
    frame = pd.DataFrame({
        "Municipality": ["A", "B", "C"],
        "Year": [2024] * 3,
        "Profession": ["Nurses"] * 3,
        "Count": [2, 4, 8],
        "Population": [0, -5, "invalid"],
    })
    quantity = post("/api/analyze", frame,
                    options={"count_unit": "pessoas", "distribution_indicator": "quantity"},
                    operation="distribution")
    assert quantity.status_code == 200, quantity.text
    assert [r["Quantidade de pessoas"] for r in quantity.json()["detail_rows"]] == [2, 4, 8]
    density = post("/api/analyze", frame,
                   options={**O, "distribution_indicator": "density"}, operation="distribution")
    assert density.status_code == 422
