"""Teste opt-in da referência mais próxima com as bases reais (ADT_REAL_DATA_DIR), só em leitura.

Os resultados da API são confrontados com recálculo independente a partir do CSV bruto:
densidade em frações exatas sobre os textos originais, coordenadas por Decimal e busca
exaustiva com pyproj. Nenhum registro é impresso; os originais são conferidos por SHA-256.
Resultados da base original sem complemento (camada versionada desconsiderada no teste) e
resultados espaciais efetivos com a camada oficial são verificados separadamente.
"""
import csv
import hashlib
import io
import json
import os
import unicodedata
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

import geo_complement
import main
from brazil_data import FILES
from install_brazil_data import install
from nearest_reference import GEOD

client = TestClient(main.app)
PERIOD = "202406"
LAYER_FILE = Path(__file__).resolve().parents[2] / "dados" / "brasil" / "complemento_coordenadas.json"


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
    text = next(p for p in paths if p.name == FILES["municipal"]).read_bytes().decode("utf-8-sig")
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


@pytest.fixture
def without_layer(monkeypatch):
    """Base original sem complemento: a camada versionada é desconsiderada somente neste teste."""
    monkeypatch.setattr(geo_complement, "LAYER", Path("dados") / "brasil" / "camada_desconsiderada_no_teste.json")


def independent(rows, period=PERIOD):
    units = {}
    for row in rows:
        if row["periodo_ano"] + row["periodo_mes"].zfill(2) != period:
            continue
        lat, lon = (Decimal(row[c].strip().replace(",", ".")) for c in ("latitude", "longitude"))
        valid = abs(lat) <= 90 and abs(lon) <= 180
        units["code:" + row["cod_ibge"].strip()] = {
            "lat": float(lat), "lon": float(lon), "valid": valid, "name": row["municipio"], "uf": row["uf"].strip(),
            "q": Fraction(Decimal(row["quantidade"].strip())), "p": Fraction(Decimal(row["população_estimada"].strip()))}
    return units


def _plain(text):
    return "".join(c for c in unicodedata.normalize("NFD", text.upper()) if not unicodedata.combining(c)).strip()


def official_layer():
    """Leitura independente da camada versionada (sem o validador do aplicativo): pontos oficiais por unidade."""
    document = json.loads(LAYER_FILE.read_text(encoding="utf-8"))
    return {"code:" + item["codigo_base"]: item for item in document["municipios"]}, document


def effective(units, layer):
    """Coordenadas efetivas esperadas: só o ponto inválido na base original de um município da camada, com nome e UF
    conferidos, recebe o ponto oficial; todos os demais pontos permanecem os originais."""
    result = {}
    for key, unit in units.items():
        item = layer.get(key)
        if item and not unit["valid"] and _plain(unit["name"]) == _plain(item["municipio"]) and unit["uf"] == item["uf"]:
            result[key] = {**unit, "lat": item["latitude"], "lon": item["longitude"], "valid": True, "complemented": True}
        else:
            result[key] = {**unit, "complemented": False}
    return result


def exhaustive_minimum(units, targets, refs, block=250):
    """Menor distância geodésica (km) de cada alvo a todas as referências e as referências empatadas nela."""
    r_lat, r_lon = np.array([units[k]["lat"] for k in refs]), np.array([units[k]["lon"] for k in refs])
    result = {}
    for start in range(0, len(targets), block):
        chunk = targets[start:start + block]
        t_lat = np.repeat([units[k]["lat"] for k in chunk], len(refs))
        t_lon = np.repeat([units[k]["lon"] for k in chunk], len(refs))
        _, _, meters = GEOD.inv(t_lon, t_lat, np.tile(r_lon, len(chunk)), np.tile(r_lat, len(chunk)))
        for key, row in zip(chunk, meters.reshape(len(chunk), len(refs))):
            best = row.min()
            result[key] = (best / 1000, sorted(refs[i] for i in np.flatnonzero(row == best)))
    return result


def test_real_criterion_reference_set_and_partial_coverage(real, without_layer):
    """Base original sem complemento: referências e alvos com coordenada inválida permanecem não avaliáveis."""
    rows, inspection = real
    body = analyze(inspection, reference_mode="criterion", reference_criterion={"operator": ">=", "value": "2,36"})
    structured = body["metadata"]["nearest_reference"]
    assert structured["complemento_geografico"]["estado"] == "ausente"
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
    # Base oficial: sem declaração, o referencial e o separador decimal são premissas internas, com o mesmo resultado.
    internal = analyze(inspection, reference_mode="list", reference_ids=refs, crs="", number_format="")
    assert internal["rows"] == body["rows"]
    assert internal["metadata"]["nearest_reference"]["cobertura_referencias"] == structured["cobertura_referencias"]
    assert internal["metadata"]["options"]["governed_premises"][-2:] == ["crs", "number_format"]
    assert any(note.startswith("Referencial geodésico: SIRGAS 2000, premissa governada") for note in internal["notes"])
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


def test_real_combined_criteria_density_and_distance_june_2024(real, without_layer):
    """Densidade < 2,36 E distância > 155 km (valores do pedido do usuário, não normativos), referências ≥ 2,36.

    Base original sem complemento: há referências sem coordenada válida."""
    rows, inspection = real
    units = independent(rows)
    tree = {"logic": "and", "operands": [{"attribute": "densidade", "operator": "<", "value": "2,36"},
                                         {"attribute": "distancia", "operator": ">", "value": "155"}]}
    refs = {"reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "2,36"}}
    strict = analyze(inspection, operation="criteria", criteria=tree, **refs)["metadata"]["criterios"]
    low = {key for key, u in units.items() if u["q"] * 1000 < Fraction(Decimal("2.36")) * u["p"]}
    invalid_refs = {key for key in units if key not in low and not units[key]["valid"]}
    results = {item["elemento"]: item for item in strict["avaliacoes"]}
    assert len(results) == len(units) and strict["contagens"]["universo"] == len(units)
    if invalid_refs:  # sem aceitação explícita, a distância não é afirmada para nenhum alvo
        assert strict["contagens"]["ATENDE"] == 0
        assert {k for k, item in results.items() if item["estado"] == "NAO_ATENDE"} == set(units) - low
        assert {k for k, item in results.items() if item["estado"] == "NAO_AVALIAVEL"} == low
        assert strict["referencias"]["aceitacoes_disponiveis"]["cobertura_parcial"] == sum(u["valid"] for u in units.values())
    partial = analyze(inspection, operation="criteria", criteria=tree, distance_scope="evaluable_references",
                      **refs)["metadata"]["criterios"]
    results = {item["elemento"]: item for item in partial["avaliacoes"]}
    valid_refs = sorted(key for key in units if key not in low and units[key]["valid"])
    r_lat, r_lon = np.array([units[k]["lat"] for k in valid_refs]), np.array([units[k]["lon"] for k in valid_refs])
    for key in sorted(low)[::40]:
        item = results[key]
        if not units[key]["valid"]:
            assert item["estado"] == "NAO_AVALIAVEL" and item["nos"]["c2"]["motivos"] == ["COORDENADA_INVALIDA"]
            continue
        _, _, meters = GEOD.inv(np.full(len(valid_refs), units[key]["lon"]), np.full(len(valid_refs), units[key]["lat"]), r_lon, r_lat)
        distance = meters.min() / 1000
        assert item["nos"]["c2"]["valor"] == distance
        assert item["estado"] == ("ATENDE" if Fraction(distance) > 155 else "NAO_ATENDE")
    assert "COBERTURA_PARCIAL" in {l["tipo"] for l in partial["limitacoes"]}
    assert partial["contagens"]["ATENDE"] > 0 and partial["desfecho"] == "RES-LIM"


@pytest.fixture(scope="module")
def june_with_layer(real):
    """Junho de 2024 com a camada oficial: coordenadas efetivas esperadas, referências ≥ 2,36 e mínimo exaustivo."""
    rows, inspection = real
    raw = independent(rows)
    layer, _ = official_layer()
    units = effective(raw, layer)
    threshold = Fraction(Decimal("2.36"))
    refs = sorted(key for key, u in units.items() if u["q"] * 1000 >= threshold * u["p"])
    low = {key for key, u in units.items() if u["q"] * 1000 < threshold * u["p"]}
    return raw, units, layer, refs, low, exhaustive_minimum(units, sorted(units), refs)


def test_real_criterion_reference_set_with_the_official_layer(real, june_with_layer):
    """Com a camada oficial, as quatro referências sem coordenada válida na base original passam a participar e todos os
    alvos têm o mínimo do conjunto completo, igual à busca exaustiva independente sobre as coordenadas efetivas."""
    _, inspection = real
    raw, units, layer, refs, _, minimum = june_with_layer
    body = analyze(inspection, reference_mode="criterion", reference_criterion={"operator": ">=", "value": "2,36"})
    structured = body["metadata"]["nearest_reference"]
    members = {item["id"]: item for item in structured["conjunto_referencias"]["membros"]}
    assert set(members) == set(refs)  # a pertença ao conjunto não depende das coordenadas
    complemented_refs = {key for key in refs if not raw[key]["valid"]}  # base original: sem coordenada válida
    assert len(complemented_refs) == 4 and complemented_refs < set(layer)
    assert all(item["condicao_espacial"] == "VALIDA" for item in members.values())
    assert structured["referencias_nao_avaliaveis"] == []
    assert structured["conjunto_referencias"]["n_coordenadas_avaliaveis"] == len(refs)
    coverage = structured["cobertura"]
    assert coverage["n_universo"] == coverage["n_minimo_completo"] == len(units) == structured["universo_alvos"]["n_coordenadas_avaliaveis"]
    assert coverage["n_somente_entre_avaliaveis"] == 0 and coverage["n_nao_avaliaveis_por_motivo"] == {}
    assert "COBERTURA_PARCIAL" not in {item["tipo"] for item in structured["limitacoes"]}
    records = {item["unidade"]: item for item in structured["cobertura_referencias"]}
    assert set(records) == set(units)
    for key, (distance, nearest) in minimum.items():
        record = records[key]["minimo_completo"]
        assert record["avaliabilidade"] == "AVALIAVEL" and record["distancia_km"] == distance
        assert sorted(record["referencias"]) == nearest
        assert records[key]["coordenada"] == ("complementada" if units[key]["complemented"] else "original")
    # Referências complementadas efetivamente usadas como as mais próximas de algum alvo.
    assert {ref for _, nearest in minimum.values() for ref in nearest} & complemented_refs == complemented_refs
    geo = structured["complemento_geografico"]
    assert geo["estado"] == "valido" and geo["sha256"] == hashlib.sha256(LAYER_FILE.read_bytes()).hexdigest()
    assert geo["versao"] == "1" and geo["premissa"] == "COORDENADA_FIXA_2014_2024"
    source = json.loads(LAYER_FILE.read_text(encoding="utf-8"))["fonte"]  # proveniência registrada no resultado
    assert geo["proveniencia"] == {key: source[key] for key in ("produto", "edicao", "arquivo", "sha256_arquivo", "referencial",
                                                                "epsg", "ponto", "verificacao")}
    assert "Não houve autenticação independente" in geo["proveniencia"]["verificacao"]
    assert sorted(geo["municipios_complementados"]) == sorted(key[5:] for key in layer) and geo["linhas_complementadas"] == 6
    traced = {item["id"]: (item["latitude"], item["longitude"]) for item in geo["territorios_complementados"]}
    assert traced == {key: (item["latitude"], item["longitude"]) for key, item in layer.items()}
    assert body["metadata"]["complemento_geografico"]["sha256"] == geo["sha256"]


def test_real_layer_applies_only_to_the_six_invalid_points_in_the_22_periods(real):
    """Base original: em cada competência, só os seis municípios da camada têm ponto inválido. Com a camada, esses
    132 registros recebem o ponto oficial e os demais municípios usam o ponto original da própria competência."""
    rows, inspection = real
    layer, document = official_layer()
    periods = document["escopo_temporal"]["competencias"]
    assert periods == sorted({row["periodo_ano"] + row["periodo_mes"].zfill(2) for row in rows}) and len(periods) == 22
    refs = sorted(layer)  # os seis como referências: ponto complementado nos dois lados da distância
    total = 0
    for period in periods:
        raw = independent(rows, period)
        assert {key for key, unit in raw.items() if not unit["valid"]} == set(layer)
        units = effective(raw, layer)
        assert sum(unit["complemented"] for unit in units.values()) == 6
        structured = analyze(inspection, reference_mode="list", reference_ids=refs, period_filter=period)["metadata"]["nearest_reference"]
        geo = structured["complemento_geografico"]
        assert geo["estado"] == "valido" and sorted(geo["municipios_complementados"]) == sorted(key[5:] for key in layer)
        total += geo["linhas_complementadas"]
        records = {item["unidade"]: item for item in structured["cobertura_referencias"]}
        assert set(records) == set(units) and structured["cobertura"]["n_minimo_completo"] == len(units)
        for key, (distance, nearest) in exhaustive_minimum(units, sorted(units), refs).items():
            record = records[key]
            assert record["condicao_espacial"] == "VALIDA"
            assert record["coordenada"] == ("complementada" if units[key]["complemented"] else "original")
            assert record["minimo_completo"]["distancia_km"] == distance and sorted(record["minimo_completo"]["referencias"]) == nearest
    assert total == 132


def test_real_combined_criteria_with_the_official_layer(real, june_with_layer):
    """Mesmo pedido com a camada oficial: todas as referências avaliáveis, distância afirmada pelo mínimo do conjunto
    completo sem aceitação de cobertura parcial; estados iguais ao recálculo exaustivo independente."""
    _, inspection = real
    _, units, _, refs, low, minimum = june_with_layer
    tree = {"logic": "and", "operands": [{"attribute": "densidade", "operator": "<", "value": "2,36"},
                                         {"attribute": "distancia", "operator": ">", "value": "155"}]}
    options = {"reference_mode": "criterion", "reference_criterion": {"operator": ">=", "value": "2,36"}}
    strict = analyze(inspection, operation="criteria", criteria=tree, **options)["metadata"]["criterios"]
    expected = {key: "ATENDE" if key in low and Fraction(minimum[key][0]) > 155 else "NAO_ATENDE" for key in units}
    results = {item["elemento"]: item for item in strict["avaliacoes"]}
    assert {key: item["estado"] for key, item in results.items()} == expected
    assert all(results[key]["nos"]["c2"]["valor"] == minimum[key][0] for key in units)
    counts = strict["contagens"]
    assert counts["universo"] == len(units) and counts["NAO_AVALIAVEL"] == 0
    assert counts["ATENDE"] == sum(state == "ATENDE" for state in expected.values()) > 0
    assert counts["NAO_ATENDE"] == len(units) - counts["ATENDE"]
    kinds = {item["tipo"] for item in strict["limitacoes"]}
    assert "COBERTURA_PARCIAL" not in kinds and "UNIDADES_NAO_AVALIAVEIS" not in kinds
    assert strict["desfecho"] == "RES-LIM" and "DISTANCIA_GEODESICA_DIRETA" in kinds  # limitação sempre registrada
    assert strict["referencias"]["referencias_nao_avaliaveis"] == [] and strict["referencias"]["aceitacoes_disponiveis"]["cobertura_parcial"] == 0
    assert strict["referencias"]["complemento_geografico"]["estado"] == "valido"
    # Aceitar a cobertura parcial não altera nada quando todas as referências são avaliáveis.
    partial = analyze(inspection, operation="criteria", criteria=tree, distance_scope="evaluable_references",
                      **options)["metadata"]["criterios"]
    assert {item["elemento"]: item["estado"] for item in partial["avaliacoes"]} == expected
    # Referencial e separador decimal internos da base oficial: as mesmas avaliações sem declaração do usuário.
    internal = analyze(inspection, operation="criteria", criteria=tree, crs="", number_format="", **options)
    assert internal["metadata"]["criterios"]["avaliacoes"] == strict["avaliacoes"]
