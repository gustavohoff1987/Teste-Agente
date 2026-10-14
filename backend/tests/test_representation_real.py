"""Teste opt-in (ADT_REAL_DATA_DIR) do contrato de apresentação com a base Brasil real, só em leitura.

A geometria de cada competência é confrontada com uma leitura independente do CSV bruto (Decimal) e
da camada versionada: os seis municípios com ponto inválido na fonte recebem o ponto oficial; os
demais, o ponto original da própria competência. Nenhum registro é impresso.
"""
import hashlib

from test_nearest_real_data import LAYER_FILE, analyze, effective, independent, official_layer, real  # noqa: F401 (fixture)


def located(geometry):
    return {key: (lat, lon) for key, lat, lon in zip(geometry["ids"], geometry["lat"], geometry["lon"])}


def test_real_geometry_matches_the_effective_points_in_the_22_periods(real):  # noqa: F811
    rows, inspection = real
    layer, document = official_layer()
    for period in document["escopo_temporal"]["competencias"]:
        units = effective(independent(rows, period), layer)
        body = analyze(inspection, operation="density", period_filter=period)
        geometry = body["metadata"]["representacao"]["geometria"]
        assert geometry["estado"] == "DISPONIVEL" and geometry["competencia"] == period and geometry["sem_geometria"] == []
        assert located(geometry) == {key: (unit["lat"], unit["lon"]) for key, unit in units.items()}
        assert sorted(geometry["complementados"]) == sorted(layer) and len(geometry["ids"]) == len(units)
        identity = geometry["complemento_geografico"]
        assert identity["estado"] == "valido" and identity["sha256"] == hashlib.sha256(LAYER_FILE.read_bytes()).hexdigest()


def test_real_criteria_scenario_links_every_row_state_and_reference_to_a_point(real):  # noqa: F811
    _, inspection = real
    tree = {"logic": "and", "operands": [{"attribute": "densidade", "operator": "<", "value": "2,36"},
                                         {"attribute": "distancia", "operator": ">", "value": "155"}]}
    body = analyze(inspection, operation="criteria", criteria=tree, reference_mode="criterion",
                   reference_criterion={"operator": ">=", "value": "2,36"})
    contract = body["metadata"]["representacao"]
    points = located(contract["geometria"])
    states = {"code:" + row["Código"]: row["Resultado"] for row in body["rows"]}
    assert len(points) == len(states) == 5570 and set(states) == set(points)
    assert sum(state == "ATENDE" for state in states.values()) == body["metadata"]["criterios"]["contagens"]["ATENDE"]
    references = {item["id"] for item in body["metadata"]["criterios"]["referencias"]["membros"]}
    assert references <= set(points)
    for item in body["metadata"]["criterios"]["avaliacoes"][::50]:
        assert set(item["nos"]["c2"]["referencias"] or []) <= references
