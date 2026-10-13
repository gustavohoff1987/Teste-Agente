"""Bloco 2, Etapa 1: referências territoriais (CAP-REF-01) e referência mais próxima (CAP-ESP-01/02)."""
import json
import math

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main
from brazil_catalog_profile import FIELDS
from llm_bridge import OPERATIONS as LLM_OPERATIONS
from llm_context import provider_snapshot
from nearest_reference import GEOD, GRS80_A, GRS80_RF, nearest_exact, nearest_exhaustive
from prepare_block1_catalog import prepare

client = TestClient(main.app)
MAP = {"territory": "municipio", "territory_id": "codigo", "period": "periodo", "category": "categoria",
       "count": "quantidade", "population": "populacao", "latitude": "latitude", "longitude": "longitude"}
BASE = {"confirmed_roles": list(MAP), "count_unit": "pessoas", "population_denominator_confirmed": True,
        "fts_scope_confirmed": True, "object_confirmed": True, "crs": "SIRGAS2000", "period_filter": "2024",
        "category_filter": "MEDICINA"}
# nome, código, latitude, longitude, quantidade, população — coordenadas sintéticas, não oficiais.
UNITS = [("Manaus", "130260", -3.119, -60.021, 100, 10000), ("Tefe", "130420", -3.354, -64.711, 5, 10000),
         ("Parintins", "130340", -2.628, -56.736, 20, 10000), ("Santarem", "150680", -2.443, -54.708, 59, 25000),
         ("Faro", "150300", -2.168, -56.742, 30, 10000), ("Invalido", "130009", 63741, -60.0, 50, 10000),
         ("Sem coordenada", "130008", None, None, 40, 10000)]


def frame(units=UNITS, periods=("2023", "2024"), extra=()):
    rows = [{"municipio": n, "codigo": c, "periodo": period, "categoria": "MEDICINA", "quantidade": q,
             "populacao": p, "latitude": lat, "longitude": lon}
            for period in periods for n, c, lat, lon, q, p in units]
    return pd.DataFrame(rows + list(extra))


def run(df, path="/api/analyze", mapping=MAP, **options):
    return client.post(path, files={"file": ("sintetico.csv", df.to_csv(index=False).encode())},
                       data={"mapping": json.dumps(mapping), "options": json.dumps({**BASE, **options}),
                             "operation": "nearest"})


def ok(df, **options):
    response = run(df, **options)
    assert response.status_code == 200, response.text
    body = response.json()
    return body, body["metadata"]["nearest_reference"], {r["unidade"]: r for r in
                                                           body["metadata"]["nearest_reference"]["cobertura_referencias"]}


def geodesic_km(a, b):
    units = {c: (lat, lon) for _, c, lat, lon, _, _ in UNITS}
    return GEOD.inv(units[a][1], units[a][0], units[b][1], units[b][0])[2] / 1000


def vincenty(lat1, lon1, lat2, lon2, a=GRS80_A, f=1 / GRS80_RF):
    """Implementação independente (Vincenty, 1975) só para conferência; não usada pelo motor."""
    b = (1 - f) * a
    u1, u2 = math.atan((1 - f) * math.tan(math.radians(lat1))), math.atan((1 - f) * math.tan(math.radians(lat2)))
    lam = big_l = math.radians(lon2 - lon1)
    for _ in range(200):
        sin_s = math.hypot(math.cos(u2) * math.sin(lam), math.cos(u1) * math.sin(u2) - math.sin(u1) * math.cos(u2) * math.cos(lam))
        cos_s = math.sin(u1) * math.sin(u2) + math.cos(u1) * math.cos(u2) * math.cos(lam)
        sigma = math.atan2(sin_s, cos_s)
        sin_a = math.cos(u1) * math.cos(u2) * math.sin(lam) / sin_s
        cos2a = 1 - sin_a ** 2
        cos2sm = cos_s - 2 * math.sin(u1) * math.sin(u2) / cos2a
        c = f / 16 * cos2a * (4 + f * (4 - 3 * cos2a))
        previous, lam = lam, big_l + (1 - c) * f * sin_a * (sigma + c * sin_s * (cos2sm + c * cos_s * (-1 + 2 * cos2sm ** 2)))
        if abs(lam - previous) < 1e-13:
            break
    usq = cos2a * (a * a - b * b) / (b * b)
    big_a = 1 + usq / 16384 * (4096 + usq * (-768 + usq * (320 - 175 * usq)))
    big_b = usq / 1024 * (256 + usq * (-128 + usq * (74 - 47 * usq)))
    delta = big_b * sin_s * (cos2sm + big_b / 4 * (cos_s * (-1 + 2 * cos2sm ** 2) - big_b / 6 * cos2sm *
                                                  (-3 + 4 * sin_s ** 2) * (-3 + 4 * cos2sm ** 2)))
    return b * big_a * (sigma - delta)


def test_geodesic_method_is_grs80_and_agrees_with_independent_vincenty():
    assert (GEOD.a, GEOD.f) == (6378137.0, 1 / 298.257222101)
    reference = main.Geod(ellps="GRS80")
    assert (GEOD.a, GEOD.f) == (reference.a, reference.f)
    rng = np.random.default_rng(11)
    for lat1, lon1, lat2, lon2 in rng.uniform([-34, -74, -34, -74], [5, -35, 5, -35], size=(200, 4)):
        karney = GEOD.inv(lon1, lat1, lon2, lat2)[2]
        assert abs(karney - vincenty(lat1, lon1, lat2, lon2)) < 1e-3  # metros
    # Meio meridiano do GRS80 (polo a polo), valor de referência do elipsoide.
    assert abs(GEOD.inv(0, 90, 0, -90)[2] - 20003931.4586) < 1e-3


def ring(rng):
    """Referências a 1.000 km + centímetros, em azimutes aleatórios: a ordem das cordas varia com o azimute
    (dezenas de metros) e não coincide com a ordem geodésica — só a busca completa acha a mais próxima."""
    azimuths = rng.uniform(-180, 180, 64)
    distances = 1_000_000 + rng.permutation(64) * 0.01
    lon, lat, _ = GEOD.fwd(np.full(64, -50.0), np.full(64, -10.0), azimuths, distances)
    return np.array([-10.0]), np.array([-50.0]), lat, lon


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_exact_search_equals_exhaustive_search(seed):
    rng = np.random.default_rng(seed)
    scenarios = [
        (rng.uniform(-33.7, 5.2, 150), rng.uniform(-73.9, -34.8, 150), rng.uniform(-33.7, 5.2, 400), rng.uniform(-73.9, -34.8, 400)),
        (rng.uniform(-90, 90, 80), rng.uniform(-180, 180, 80), rng.uniform(-90, 90, 300), rng.uniform(-180, 180, 300)),
        # Polos, linha de data, quase antípodas e pontos coincidentes.
        (np.array([90, -90, 0, 0, 10, -45, 0]), np.array([0, 0, 179.9999, -179.9999, 20, 60, 0]),
         np.array([-90, 90, 0, 0.1, -10, 45, 0, 0]), np.array([0, 0, -179.9999, 179.95, -160, -120, 0, 0])),
        # Empates exatos: referências simétricas no equador.
        (np.zeros(5), np.array([0, 10, 20, 30, 40.0]), np.zeros(10), np.concatenate([np.arange(0, 50, 10) - 1.5, np.arange(0, 50, 10) + 1.5])),
        # Seis referências coincidentes: empate de seis, além das quatro geodésicas iniciais.
        (np.array([-10.0]), np.array([-50.0]), np.full(6, -11.0), np.full(6, -50.0)),
        ring(rng),
    ]
    for t_lat, t_lon, r_lat, r_lon in scenarios:
        best, ties, evaluated = nearest_exact(t_lat, t_lon, r_lat, r_lon)
        expected_best, expected_ties = nearest_exhaustive(t_lat, t_lon, r_lat, r_lon)
        assert np.array_equal(best, expected_best)
        assert [sorted(x) for x in ties] == [sorted(x) for x in expected_ties]
        assert evaluated <= len(t_lat) * len(r_lat)
    assert all(len(x) == 2 for x in nearest_exact(*scenarios[3])[1])
    assert len(nearest_exact(*scenarios[4])[1][0]) == 6


def test_explicit_list_with_references_in_other_state_and_target_also_reference():
    body, structured, units = ok(frame(), reference_mode="list", reference_ids=["code:130260", "code:150300"])
    assert structured["conjunto_referencias"]["forma"] == "LISTA_EXPLICITA"
    assert structured["conjunto_referencias"]["origem"] == "MANIFESTACAO_USUARIO"
    parintins = units["code:130340"]
    assert parintins["minimo_completo"]["avaliabilidade"] == "AVALIAVEL"
    assert parintins["minimo_completo"]["referencias"] == ["code:150300"]  # Faro (PA), outro estado
    assert parintins["minimo_completo"]["distancia_km"] == geodesic_km("130340", "150300")
    assert parintins["minimo_completo"]["alcance"] == "conjunto completo de referências"
    manaus = units["code:130260"]
    assert manaus["alvo_e_referencia"] is True and manaus["minimo_completo"]["distancia_km"] == 0.0
    assert any("também integram o conjunto de referências" in note for note in body["notes"])
    assert {l["tipo"] for l in structured["limitacoes"]} >= {"DISTANCIA_GEODESICA_DIRETA", "UNIDADES_NAO_AVALIAVEIS"}
    assert any("geográfica direta" in note for note in body["notes"])
    assert structured["desfecho"] == "RES-LIM"


def test_invalid_reference_gives_partial_minimum_never_presented_as_complete():
    body, structured, units = ok(frame(), reference_mode="list", reference_ids=["code:130260", "code:130009"])
    tefe = units["code:130420"]
    assert tefe["minimo_completo"] == {"avaliabilidade": "NAO_AVALIAVEL", "motivo": "DEPENDENCIA_NAO_AVALIAVEL", "referencias": []}
    assert tefe["minimo_avaliaveis"]["referencias"] == ["code:130260"]
    assert tefe["minimo_avaliaveis"]["alcance"] == "entre as referências avaliáveis"
    assert tefe["referencias_autorizadas"] == 2 and tefe["referencias_avaliaveis"] == 1
    assert structured["referencias_nao_avaliaveis"] == [{"id": "code:130009", "territorio": "Invalido [130009]",
                                                         "condicao": "INVALIDA", "motivo": "COORDENADA_INVALIDA"}]
    assert "COBERTURA_PARCIAL" in {l["tipo"] for l in structured["limitacoes"]}
    row = next(r for r in body["rows"] if r["Código do alvo"] == "130420")
    assert row["Alcance"] == "Entre as referências avaliáveis" and "Cobertura parcial" in row["Condição"]
    assert row["Distância (km)"] == geodesic_km("130420", "130260")


def test_targets_without_valid_coordinates_stay_in_universe():
    body, structured, units = ok(frame(), reference_mode="list", reference_ids=["code:130260"])
    assert len(body["rows"]) == len(UNITS)
    assert units["code:130009"]["minimo_avaliaveis"]["avaliabilidade"] == "NAO_AVALIAVEL"
    assert units["code:130009"]["referencias_nao_avaliaveis_com_motivo"][0]["motivo"] == "COORDENADA_INVALIDA"
    assert units["code:130008"]["referencias_nao_avaliaveis_com_motivo"][0]["motivo"] == "SEM_INFORMACAO_ESPACIAL"
    assert structured["cobertura"]["n_nao_avaliaveis_por_motivo"] == {"COORDENADA_INVALIDA": 1, "SEM_INFORMACAO_ESPACIAL": 1}
    assert all(r["Distância (km)"] is None for r in body["rows"] if r["Código do alvo"] in ("130009", "130008"))


def test_conflicting_coordinates_in_the_period_are_not_evaluable():
    conflict = {"municipio": "Manaus", "codigo": "130260", "periodo": "2024", "categoria": "ENFERMAGEM",
                "quantidade": 1, "populacao": 10000, "latitude": -3.5, "longitude": -60.5}
    body, structured, units = ok(frame(extra=[conflict]), reference_mode="list", reference_ids=["code:130260", "code:150300"])
    assert structured["referencias_nao_avaliaveis"][0]["condicao"] == "CONFLITANTE"
    assert units["code:130260"]["minimo_avaliaveis"]["avaliabilidade"] == "NAO_AVALIAVEL"
    assert units["code:130340"]["minimo_completo"]["avaliabilidade"] == "NAO_AVALIAVEL"
    assert units["code:130340"]["minimo_avaliaveis"]["referencias"] == ["code:150300"]


def test_ties_preserve_every_reference():
    units = [("Alvo", "900001", 0.0, 0.0, 1, 100), ("Oeste", "900002", 0.0, -1.5, 1, 100),
             ("Leste", "900003", 0.0, 1.5, 1, 100)]
    body, _, by_unit = ok(frame(units), reference_mode="list", reference_ids=["code:900002", "code:900003"])
    assert sorted(by_unit["code:900001"]["minimo_completo"]["referencias"]) == ["code:900002", "code:900003"]
    row = next(r for r in body["rows"] if r["Código do alvo"] == "900001")
    assert row["Empate"] == "Sim (2 referências)" and row["Código da referência"] in ("900003; 900002", "900002; 900003")


def test_density_criterion_is_exact_at_the_boundary():
    # Santarém: 59 / 25.000 × 1.000 = 2,36 exatamente; em ponto flutuante, 2,3600000000000003.
    assert 59 / 25000 * 1000 > 2.36
    _, at_least, _ = ok(frame(), reference_mode="criterion", reference_criterion={"operator": ">=", "value": "2,36"})
    _, above, _ = ok(frame(), reference_mode="criterion", reference_criterion={"operator": ">", "value": "2.36"})
    _, equal, _ = ok(frame(), reference_mode="criterion", reference_criterion={"operator": "=", "value": "2.36"})
    members = lambda s: {m["id"] for m in s["conjunto_referencias"]["membros"]}
    assert "code:150680" in members(at_least) and "code:150680" not in members(above)
    assert members(equal) == {"code:150680"}
    criterion = at_least["conjunto_referencias"]["criterio"]
    assert (criterion["simbolo"], criterion["valor"], criterion["periodo"], criterion["categoria"]) == ("≥", "2.36", "2024", "MEDICINA")
    values = {item["id"]: item["densidade_por_1000"] for item in at_least["conjunto_referencias"]["avaliacao_criterio"]["valores_atende"]}
    assert values["code:130260"] == 100 / 10000 * 1000


def test_criterion_candidates_without_denominator_are_listed_not_assumed():
    units = [*UNITS[:5], ("Sem populacao", "130007", -3.0, -59.0, 10, None), ("Populacao zero", "130006", -3.1, -59.1, 10, 0)]
    body, structured, _ = ok(frame(units), reference_mode="criterion", reference_criterion={"operator": ">=", "value": "1"})
    evaluation = structured["conjunto_referencias"]["avaliacao_criterio"]
    assert {(i["id"], i["motivo"]) for i in evaluation["NAO_AVALIAVEL"]} == {
        ("code:130007", "DENOMINADOR_AUSENTE"), ("code:130006", "DENOMINADOR_ZERO")}
    member_ids = {m["id"] for m in structured["conjunto_referencias"]["membros"]}
    assert not member_ids & {"code:130007", "code:130006"}
    assert any(l["dados_estruturados"].get("escopo") == "candidatos à referência" for l in structured["limitacoes"]
               if l["tipo"] == "UNIDADES_NAO_AVALIAVEIS")


def test_empty_reference_set_preserves_targets_without_distances():
    body, structured, units = ok(frame(), reference_mode="criterion", reference_criterion={"operator": ">=", "value": "1000"})
    assert structured["conjunto_referencias"]["n"] == 0 and structured["desfecho"] == "BLQ-DEP"
    assert len(units) == len(UNITS)
    for record in units.values():
        assert record["minimo_completo"]["detalhe"] == "CONJUNTO_REFERENCIAS_VAZIO"
        assert record["minimo_avaliaveis"]["detalhe"] == "CONJUNTO_REFERENCIAS_VAZIO"
    assert all(r["Distância (km)"] is None for r in body["rows"])
    assert body["title"].endswith("sem resultado analítico")
    assert "DISTANCIA_GEODESICA_DIRETA" not in {l["tipo"] for l in structured["limitacoes"]}


def test_references_all_without_coordinates_produce_no_analytical_result():
    _, structured, units = ok(frame(), reference_mode="list", reference_ids=["code:130009", "code:130008"])
    assert structured["desfecho"] == "BLQ-DAD"
    assert all(r["minimo_avaliaveis"]["avaliabilidade"] == "NAO_AVALIAVEL" for r in units.values())


@pytest.mark.parametrize("value", ["WGS84", "EPSG:4674", "SIRGAS 2000 UTM", "SIRGAS-2000/geo", "4674"])
def test_unsupported_reference_systems_are_never_transformed(value):
    response = run(frame(), reference_mode="list", reference_ids=["code:130260"], crs=value)
    assert response.status_code == 422 and "não suportado" in response.json()["detail"]


@pytest.mark.parametrize("value", [" sirgas 2000 ", "SIRGAS_2000", "Sirgas-2000", "SIRGAS2000"])
def test_governed_aliases_are_canonicalized(value):
    body, structured, _ = ok(frame(), reference_mode="list", reference_ids=["code:130260"], crs=value)
    assert body["metadata"]["options"]["crs"] == "SIRGAS2000" and structured["metodo"]["referencial"] == "SIRGAS2000"


def test_reference_system_is_never_presumed():
    response = run(frame(), reference_mode="list", reference_ids=["code:130260"], crs="")
    assert response.status_code == 422 and "nenhum referencial é presumido" in response.json()["detail"]


def test_period_must_be_explicit_and_existing_and_coordinates_come_from_it():
    moved = [("Manaus", "130260", -3.5, -60.5, 100, 10000), *UNITS[1:]]
    df = pd.concat([frame(moved, periods=("2023",)), frame(periods=("2024",))])
    assert run(df, reference_mode="list", reference_ids=["code:130260"], period_filter="").status_code == 422
    missing_period = run(df, reference_mode="list", reference_ids=["code:130260"], period_filter="2019")
    assert missing_period.status_code == 422  # recusado já pelo filtro de período comum às análises
    assert "Nenhum registro corresponde aos filtros" in missing_period.json()["detail"]
    assert run(df, reference_mode="list", reference_ids=["code:130260"], period_filter="",
               period_filters=["2023", "2024"]).status_code == 422
    _, _, units_2023 = ok(df, reference_mode="list", reference_ids=["code:130260"], period_filter="2023")
    _, _, units_2024 = ok(df, reference_mode="list", reference_ids=["code:130260"], period_filter="2024")
    tefe_2023 = units_2023["code:130420"]["minimo_completo"]["distancia_km"]
    tefe_2024 = units_2024["code:130420"]["minimo_completo"]["distancia_km"]
    assert tefe_2024 == geodesic_km("130420", "130260") and tefe_2023 != tefe_2024


def test_category_and_period_compatibility_of_the_criterion():
    response = run(frame(), reference_mode="criterion", reference_criterion={"operator": ">=", "value": "1"},
                   category_filter="ENFERMAGEM")
    assert response.status_code == 422
    two = frame(extra=[{"municipio": "Manaus", "codigo": "130260", "periodo": "2024", "categoria": "ENFERMAGEM",
                        "quantidade": 1, "populacao": 10000, "latitude": -3.119, "longitude": -60.021}])
    response = run(two, reference_mode="criterion", reference_criterion={"operator": ">=", "value": "1"}, category_filter="")
    assert response.status_code == 422 and "categoria" in response.json()["detail"]


def test_decimal_comma_requires_declaration():
    df = frame()
    for column in ("latitude", "longitude"):
        df[column] = df[column].map(lambda v: None if pd.isna(v) else str(v).replace(".", ","))
    response = run(df, reference_mode="list", reference_ids=["code:130260"])
    assert response.status_code == 422 and "separador decimal" in response.json()["detail"]
    _, _, units = ok(df, reference_mode="list", reference_ids=["code:130260"], number_format="decimal_comma")
    assert units["code:130420"]["minimo_completo"]["distancia_km"] == geodesic_km("130420", "130260")


def test_unknown_ambiguous_and_homonym_references_require_clarification():
    assert "inexistentes" in run(frame(), reference_mode="list", reference_ids=["code:999999"]).json()["detail"]
    homonyms = [*UNITS[:5], ("Santa Cruz", "150655", -2.3, -55.0, 1, 100), ("Santa Cruz", "130003", -3.3, -61.0, 1, 100)]
    _, structured, _ = ok(frame(homonyms), reference_mode="list", reference_ids=["code:150655", "code:130003"])
    assert {m["territorio"] for m in structured["conjunto_referencias"]["membros"]} == {"Santa Cruz [150655]", "Santa Cruz [130003]"}
    without_code = {k: v for k, v in MAP.items() if k != "territory_id"}
    response = run(frame(homonyms), mapping=without_code, reference_mode="list", reference_ids=["name:Santa Cruz"],
                   confirmed_roles=list(without_code))
    assert response.status_code == 422 and "homônimos" in response.json()["detail"]
    clash = frame(extra=[{"municipio": "Outro nome", "codigo": "130260", "periodo": "2024", "categoria": "MEDICINA",
                          "quantidade": 1, "populacao": 1, "latitude": -3.1, "longitude": -60.0}])
    assert run(clash, reference_mode="list", reference_ids=["code:130260"]).status_code == 422


def test_targets_and_references_are_independent_sets():
    _, structured, units = ok(frame(), reference_mode="list", reference_ids=["code:130260", "code:150300"],
                              territory_ids=["code:130420"])
    assert list(units) == ["code:130420"]
    assert structured["universo_alvos"]["definicao"] == "subconjunto selecionado"
    assert units["code:130420"]["minimo_completo"]["referencias"] == ["code:130260"]


def test_preflight_capability_states_follow_the_contract():
    df = frame()
    states = {label: run(df, path="/api/preflight", **{"reference_mode": "list", "reference_ids": ["code:130260"], **extra})
              .json()["capabilities"]["nearest"] for label, extra in
              (("sem modo", {"reference_mode": ""}), ("sem referencial", {"crs": ""}),
               ("não suportado", {"crs": "WGS84"}), ("completo", {}))}
    assert states["sem modo"]["status"] == "needs_confirmation"
    assert states["sem referencial"]["status"] == "needs_confirmation"
    assert states["não suportado"]["status"] == "unavailable"
    assert states["completo"]["status"] == "available"
    assert any(r["title"] == "Referências territoriais" for r in states["sem modo"]["requirements"])


def test_llm_interpretation_contract_is_not_widened():
    assert "nearest" not in LLM_OPERATIONS
    eligibility = run(frame(), path="/api/preflight", reference_mode="list", reference_ids=["code:130260"]).json()
    assert eligibility["capabilities"]["nearest"]["status"] == "available"
    context = provider_snapshot(eligibility)
    assert "nearest" not in context["capabilities"] and "density" in context["capabilities"]


def test_result_is_deterministic():
    first = ok(frame(), reference_mode="criterion", reference_criterion={"operator": ">=", "value": "2.36"})
    second = ok(frame(), reference_mode="criterion", reference_criterion={"operator": ">=", "value": "2.36"})
    assert first[0]["rows"] == second[0]["rows"] and first[1] == second[1]


@pytest.fixture
def brazil_catalog(tmp_path, monkeypatch):
    folder = tmp_path / "catalogo"
    prepare(folder)
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(folder))
    main._BRAZIL_FRAMES.clear()
    yield folder
    main._BRAZIL_FRAMES.clear()


def test_brazil_source_version_change_after_preparation_is_refused(brazil_catalog):
    inspection = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    options = {**BASE, "confirmed_roles": list(FIELDS["municipal"]), "period_filter": "202406",
               "reference_mode": "list", "reference_ids": ["code:130260"]}
    request = {"dataset": "brazil", "scope": "municipal", "operation": "nearest",
               "mapping": json.dumps(FIELDS["municipal"]), "options": json.dumps(options)}
    current = client.post("/api/analyze", data={**request, "dataset_version": inspection["source"]["version"]})
    assert current.status_code == 200, current.text
    # Catálogo sintético: todas as unidades no mesmo ponto, logo distância zero e empates explícitos.
    assert current.json()["metadata"]["nearest_reference"]["cobertura"]["n_minimo_completo"] == 4
    stale = client.post("/api/analyze", data={**request, "dataset_version": "0" * 64})
    assert stale.status_code in (409, 422)


def test_engine_only_capability_keeps_the_existing_source_descriptor(brazil_catalog):
    # A origem compõe a chave de execução: a nova capacidade não altera a chave das análises existentes.
    from analysis_catalog import OPERATION_LABELS
    inspection = client.post("/api/inspect", data={"dataset": "brazil", "scope": "auto", "operation": "nearest"}).json()
    assert inspection["source"]["scope"] == "municipal"
    assert set(inspection["source"]["default_scopes"]) == set(OPERATION_LABELS)

