"""Teste opt-in da referência mais próxima com as bases reais (ADT_REAL_DATA_DIR), só em leitura.

Os resultados da API são confrontados com recálculo independente a partir do CSV bruto:
densidade em frações exatas sobre os textos originais, coordenadas por Decimal e busca
exaustiva com pyproj. Nenhum registro é impresso; os originais são conferidos por SHA-256.
"""
import csv
import hashlib
import io
import json
import os
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import main
from install_brazil_data import install
from nearest_reference import GEOD

client = TestClient(main.app)
PERIOD = "202406"


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    catalog = tmp_path_factory.mktemp("real") / "catalogo"
    install(Path(folder), catalog)
    previous = os.environ.get("ADT_BRASIL_DATA_DIR")
    os.environ["ADT_BRASIL_DATA_DIR"] = str(catalog)
    main._BRAZIL_FRAMES.clear()
    text = next(p for p in paths if p.suffix.lower() == ".csv").read_bytes().decode("utf-8-sig")
    first = text.splitlines()[0]
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";" if first.count(";") > first.count(",") else ","))
    inspection = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    yield rows, inspection
    main._BRAZIL_FRAMES.clear()
    if previous is None:
        os.environ.pop("ADT_BRASIL_DATA_DIR", None)
    else:
        os.environ["ADT_BRASIL_DATA_DIR"] = previous
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def analyze(inspection, operation="nearest", **options):
    curated = inspection["curated_defaults"]
    settings = {"confirmed_roles": curated["confirmed_roles"], "count_unit": curated["count_unit"],
                "fts_scope_confirmed": True, "object_confirmed": True, "population_denominator_confirmed": True,
                "category_filter": curated["category"], "period_filter": PERIOD, "number_format": "decimal_comma",
                "crs": "SIRGAS2000", **options}
    response = client.post("/api/analyze", data={
        "dataset": "brazil", "scope": "municipal", "dataset_version": inspection["source"]["version"],
        "mapping": json.dumps(inspection["suggested_mapping"]), "operation": operation, "options": json.dumps(settings)})
    assert response.status_code == 200, response.status_code
    return response.json()


def independent(rows, period=PERIOD):
    units = {}
    for row in rows:
        if row["periodo_ano"] + row["periodo_mes"].zfill(2) != period:
            continue
        lat, lon = (Decimal(row[c].strip().replace(",", ".")) for c in ("latitude", "longitude"))
        valid = abs(lat) <= 90 and abs(lon) <= 180
        units["code:" + row["cod_ibge"].strip()] = {
            "lat": float(lat), "lon": float(lon), "valid": valid,
            "q": Fraction(Decimal(row["quantidade"].strip())), "p": Fraction(Decimal(row["população_estimada"].strip()))}
    return units


def test_real_criterion_reference_set_and_partial_coverage(real):
    rows, inspection = real
    body = analyze(inspection, reference_mode="criterion", reference_criterion={"operator": ">=", "value": "2,36"})
    structured = body["metadata"]["nearest_reference"]
    units = independent(rows)
    expected_refs = {key for key, u in units.items() if u["q"] * 1000 >= Fraction(Decimal("2.36")) * u["p"]}
    assert {m["id"] for m in structured["conjunto_referencias"]["membros"]} == expected_refs
    invalid_refs = {key for key in expected_refs if not units[key]["valid"]}
    assert {item["id"] for item in structured["referencias_nao_avaliaveis"]} == invalid_refs
    invalid_targets = {key for key, u in units.items() if not u["valid"]}
    assert len(invalid_targets) == 6 and structured["cobertura"]["n_universo"] == len(units)
    assert structured["cobertura"]["n_nao_avaliaveis_por_motivo"] == {"COORDENADA_INVALIDA": 6}
    coverage = {r["unidade"]: r for r in structured["cobertura_referencias"]}
    assert all(coverage[key]["minimo_avaliaveis"]["avaliabilidade"] == "NAO_AVALIAVEL" for key in invalid_targets)
    if invalid_refs:  # alguma referência sem coordenada válida: nenhum mínimo do conjunto completo
        assert structured["cobertura"]["n_minimo_completo"] == 0
        assert "COBERTURA_PARCIAL" in {l["tipo"] for l in structured["limitacoes"]}
    valid_refs = sorted(key for key in expected_refs if units[key]["valid"])
    r_lat = np.array([units[k]["lat"] for k in valid_refs])
    r_lon = np.array([units[k]["lon"] for k in valid_refs])
    sample = sorted(key for key in units if units[key]["valid"])[::25]
    for key in sample:
        _, _, meters = GEOD.inv(np.full(len(valid_refs), units[key]["lon"]), np.full(len(valid_refs), units[key]["lat"]), r_lon, r_lat)
        nearest = sorted(valid_refs[i] for i in np.flatnonzero(meters == meters.min()))
        record = coverage[key]["minimo_avaliaveis"]
        assert sorted(record["referencias"]) == nearest and record["distancia_km"] == meters.min() / 1000
        assert record["alcance"] == "entre as referências avaliáveis"
    # Densidades do critério iguais às da análise de densidade do Bloco 1 no mesmo recorte.
    density = analyze(inspection, operation="density")
    by_label = {r["Território"]: r["Densidade por 1.000"] for r in density["rows"]}
    labels = {item["id"]: item["territorio"] for item in structured["conjunto_referencias"]["membros"]}
    for item in structured["conjunto_referencias"]["avaliacao_criterio"]["valores_atende"][:300]:
        assert item["densidade_por_1000"] == by_label[labels[item["id"]]]


def test_real_explicit_list_uses_the_period_geometry(real):
    rows, inspection = real
    refs = ["code:130260", "code:130420", "code:130340"]
    body = analyze(inspection, reference_mode="list", reference_ids=refs)
    structured = body["metadata"]["nearest_reference"]
    units = independent(rows)
    coverage = {r["unidade"]: r for r in structured["cobertura_referencias"]}
    r_lat = np.array([units[k]["lat"] for k in refs])
    r_lon = np.array([units[k]["lon"] for k in refs])
    for key in sorted(k for k in units if units[k]["valid"])[::50]:
        _, _, meters = GEOD.inv(np.full(3, units[key]["lon"]), np.full(3, units[key]["lat"]), r_lon, r_lat)
        record = coverage[key]["minimo_completo"]
        assert record["avaliabilidade"] == "AVALIAVEL" and record["distancia_km"] == meters.min() / 1000
    # Municípios cujas coordenadas mudam entre competências: cada período usa a sua geometria.
    early = independent(rows, "201401")
    moved = sorted(k for k in units if early.get(k) and units[k]["valid"] and early[k]["valid"]
                   and (units[k]["lat"], units[k]["lon"]) != (early[k]["lat"], early[k]["lon"]))
    assert moved, "esperava-se ao menos um município com coordenadas diferentes entre competências"
    other = analyze(inspection, reference_mode="list", reference_ids=refs, period_filter="201401")
    earlier = {r["unidade"]: r for r in other["metadata"]["nearest_reference"]["cobertura_referencias"]}
    e_lat = np.array([early[k]["lat"] for k in refs])
    e_lon = np.array([early[k]["lon"] for k in refs])
    for key in moved[:5]:
        _, _, meters = GEOD.inv(np.full(3, early[key]["lon"]), np.full(3, early[key]["lat"]), e_lon, e_lat)
        assert earlier[key]["minimo_completo"]["distancia_km"] == meters.min() / 1000
