"""Teste opt-in: lê os originais sem persistir ou versionar seus registros.

ADT_REAL_DATA_DIR indica a pasta de validação. O usuário declarou a contagem
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
from install_brazil_data import install

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
    assert mapping["territory_id"] == "cod_ibge"
    assert mapping["category"] == "categoria_profissional"
    assert mapping["period"] == "Período (ano e mês)"
    names_only = {k:v for k,v in mapping.items() if k != "territory_id"}
    # Não inferir unidade de contagem nem substituir confirmação por nome de cabeçalho.
    initial = preflight(frame, names_only)
    assert initial["capabilities"]["density"]["status"] != "available"
    profile = initial["multiplicity"]
    assert profile["exact_duplicate_excess"] == 0
    assert profile["affected_records"] == 11528 and profile["groups"] == 5324
    # Definição expressa do usuário; não autoriza somar municípios ou períodos.
    options = {"confirmed_roles": ["territory_id", "period"], "count_unit": "pessoas",
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
    expected = pd.DataFrame({"Território": frame.municipio + " [" + frame.cod_ibge + "]",
        "Período": frame.periodo_ano + frame.periodo_mes.str.zfill(2), "Categoria": frame[mapping["category"]],
        "q": pd.to_numeric(frame.quantidade), "p": pd.to_numeric(frame[mapping["population"]])})
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
    assert info["suggested_category_constant"] == ""
    mapping = info["suggested_mapping"]
    assert mapping["territory"] == "pais" and mapping["category"] == "categoria_profissional"
    options = {"confirmed_roles": ["period"], "count_unit": "pessoas",
               "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True}
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
            assert row["Território"] == "Brasil"


@pytest.fixture(scope="module")
def real_catalog(real_sources, tmp_path_factory):
    folder = tmp_path_factory.mktemp("real-catalog") / "brasil"
    install(real_sources[0].parent, folder)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(folder))
        info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
        source = next(p for p in real_sources if p.suffix.lower() == ".csv")
        # Leitura independente do adaptador usado pelo aplicativo.
        original = pd.read_csv(source, sep=";", encoding="utf-8-sig", dtype=str)
        expected = pd.DataFrame({"Território": original.municipio + " [" + original.cod_ibge + "]",
            "Período": original.periodo_ano + original.periodo_mes.str.zfill(2),
            "Categoria": original.categoria_profissional, "Quantidade": pd.to_numeric(original.quantidade),
            "População": pd.to_numeric(original["população_estimada"])})
        expected["Densidade por 1.000"] = expected.Quantidade * 1000 / expected["População"]
        yield info, original, expected


def resident(info, operation, **extra):
    options = {"confirmed_roles": ["period", "territory_id"], "count_unit": "pessoas",
               "population_denominator_confirmed": True, **extra}
    return client.post("/api/analyze", data={"dataset": "brazil", "scope": info["source"]["scope"],
        "dataset_version": info["source"]["version"], "operation": operation,
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options)})


def resident_result(info, operation, **options):
    response = resident(info, operation, **options)
    assert response.status_code == 200, response.text[:1500]
    body = response.json()
    assert body["metadata"]["source"]["dataset"] == "brazil"
    assert body["metadata"]["derived_fields"] == info["derived_fields"]
    return body


@pytest.mark.parametrize("operation", ["counts", "report", "comparisons", "ranking"])
def test_real_resident_records_and_ranking(real_catalog, operation):
    info, _, expected = real_catalog
    result = resident_result(info, operation, comparison_confirmed=True)
    actual = pd.DataFrame(result["rows"])
    expected = expected.copy()
    expected["Posição"] = expected.groupby(["Período", "Categoria"])["Densidade por 1.000"].rank(method="min", ascending=False)
    joined = actual.merge(expected, on=["Território", "Período", "Categoria"], validate="one_to_one", suffixes=("_a", "_e"))
    assert len(actual) == len(joined) == len(expected)
    columns = (["Posição", "Densidade por 1.000"] if operation in ("comparisons", "ranking") else
               ["Quantidade"] if operation == "counts" else ["Quantidade", "População", "Densidade por 1.000"])
    for column in columns:
        np.testing.assert_allclose(joined[column + "_a"], joined[column + "_e"], rtol=1e-13)


@pytest.mark.parametrize("indicator", ["density", "quantity"])
def test_real_resident_distribution(real_catalog, indicator):
    info, _, expected = real_catalog
    result = resident_result(info, "distribution", period_filter="202406", distribution_indicator=indicator)
    expected = expected.query('Período == "202406"')
    column = "Densidade por 1.000" if indicator == "density" else "Quantidade"
    ordered = sorted(expected[column].tolist())
    cuts = []
    for j in range(1, 5):
        position = (len(ordered) - 1) * j / 5
        lower = int(position)
        cuts.append(ordered[lower] + (ordered[lower + 1] - ordered[lower]) * (position - lower))
    classes = {row.Território: 1 + sum(row[column] > cut for cut in cuts) for _, row in expected.iterrows()}
    assert len(result["detail_rows"]) == len(expected)
    for row in result["detail_rows"]:
        assert row["Quintil"] == f'{classes[row["Território"]]}º quintil'
    for j, row in enumerate(result["rows"], 1):
        assert row["Unidades"] == sum(value == j for value in classes.values())
    assert resident(info, "distribution", distribution_indicator=indicator).status_code == 422


@pytest.mark.parametrize("denominator", [True, False])
def test_real_resident_temporal(real_catalog, denominator):
    info, _, expected = real_catalog
    result = resident_result(info, "temporal", population_denominator_confirmed=denominator,
        temporal_comparability_confirmed=True, territory_longitudinal_confirmed=True)
    column = "Densidade por 1.000" if denominator else "Quantidade"
    first = expected.query('Período == "201401"').set_index("Território")[column].to_dict()
    last = expected.query('Período == "202406"').set_index("Território")[column].to_dict()
    assert len(result["rows"]) == expected.Território.nunique()
    for row in result["rows"]:
        a, b = first.get(row["Território"]), last.get(row["Território"])
        if a is None or b is None:
            assert row["Inicial"] is None and row["Final"] is None
        else:
            assert row["Inicial"] == pytest.approx(a) and row["Final"] == pytest.approx(b)
            assert row["Variação absoluta"] == pytest.approx(b - a)
            assert row["Variação (%)"] == (pytest.approx((b - a) / a * 100) if a else None)


def test_real_resident_aggregation_is_not_national_unique_count(real_catalog):
    info, _, expected = real_catalog
    assert resident(info, "aggregate", period_filter="202406", population_additive_confirmed=True).status_code == 422
    result = resident_result(info, "aggregate", period_filter="202406",
        population_additive_confirmed=True, component_sum_confirmed=True)
    selected = expected.query('Período == "202406"')
    row = result["rows"][0]
    assert "possível dupla contagem" in row["Tipo"]
    assert row["Quantidade"] == selected.Quantidade.sum()
    assert row["População"] == selected["População"].sum()
    assert row["Densidade por 1.000"] == pytest.approx(selected.Quantidade.sum() * 1000 / selected["População"].sum())
    national = client.post("/api/inspect", data={"dataset": "brazil", "operation": "counts"}).json()
    national_result = resident_result(national, "counts", population_denominator_confirmed=False, period_filter="202406")
    assert national_result["total_rows"] == 1
    assert national_result["rows"][0]["Território"] == "Brasil"
    assert national_result["rows"][0]["Quantidade"] < row["Quantidade"]


def test_real_resident_spatial_comma_and_coordinate_changes(real_catalog):
    info, original, expected = real_catalog
    expected = expected.query('Período == "202406"').copy()
    original = original.loc[expected.index]
    reference = expected.Território.iloc[0]
    options = {"confirmed_roles": ["period", "territory_id", "latitude", "longitude"],
               "number_format": "decimal_comma", "crs": "SIRGAS2000", "reference_territory": reference}
    assert resident(info, "spatial", **options).status_code == 422
    assert resident(info, "spatial", **{**options, "number_format": "decimal_point"}, period_filter="202406").status_code == 422
    response = resident(info, "spatial", **options, period_filter="202406")
    assert response.status_code == 422
    assert "intervalos geográficos" in response.json()["detail"]
    parsed = original[["latitude", "longitude"]].apply(lambda col: col.str.replace(",", ".", regex=False).astype(float))
    valid = parsed.latitude.between(-90, 90) & parsed.longitude.between(-180, 180)
    assert (~valid).sum() == 6
    # Subconjunto de teste explícito, nunca exclusão automática no catálogo.
    # Permite confrontar a função de distância sem alterar as fontes.
    original = original.loc[valid]
    expected = expected.loc[valid]
    reference = expected.Território.iloc[0]
    options["reference_territory"] = reference
    response = client.post("/api/analyze", files={"file": ("spatial-test-subset.csv", original.to_csv(index=False, sep=";").encode())},
        data={"operation": "spatial", "mapping": json.dumps(info["suggested_mapping"]),
              "options": json.dumps({**options, "period_filter": "202406"})})
    assert response.status_code == 200, response.text[:1500]
    result = response.json()
    coords = np.deg2rad(original[["latitude", "longitude"]].apply(lambda col: col.str.replace(",", ".", regex=False).astype(float)).to_numpy())
    lat, lon = coords[:, 0], coords[:, 1]
    hav = np.sin((lat - lat[0]) / 2) ** 2 + np.cos(lat[0]) * np.cos(lat) * np.sin((lon - lon[0]) / 2) ** 2
    expected["distance"] = 6371.0088 * 2 * np.arcsin(np.sqrt(np.clip(hav, 0, 1)))
    actual = pd.DataFrame(result["rows"]).merge(expected[["Território", "distance"]], on="Território", validate="one_to_one")
    assert len(actual) == len(expected)
    # Haversine independente; tolerância cobre diferença para o elipsoide.
    np.testing.assert_allclose(actual["Distância (km)"], actual.distance, rtol=0.006, atol=0.002)
    assert result["rows"][0] == {"Território": reference, "Distância (km)": 0.0}


@pytest.mark.parametrize("operation", ["density", "distribution", "comparisons", "ranking", "aggregate", "spatial", "rotation"])
def test_real_resident_national_missing_inputs_blocked(real_catalog, operation):
    info = client.post("/api/inspect", data={"dataset": "brazil", "scope": "national"}).json()
    response = resident(info, operation, period_filter="202406", distribution_indicator="quantity")
    assert response.status_code == 422
    assert "não habilitada" in response.json()["detail"]


def test_real_resident_rotation_requires_individual_data(real_catalog):
    response = resident(real_catalog[0], "rotation", longitudinal_identity_confirmed=True,
        territory_longitudinal_confirmed=True, cohort_coverage_confirmed=True)
    assert response.status_code == 422
    assert "identificador individual" in response.json()["detail"].lower()
