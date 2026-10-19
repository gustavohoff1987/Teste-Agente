"""Bloco 3: contrato de apresentação (metadata.representacao) — geometria autorizada e indicadores.

Bases sintéticas geradas em tempo de teste (coordenadas fictícias). O contrato não calcula: as
coordenadas são as efetivas da competência (mesma regra das análises espaciais) e os indicadores são
colunas do próprio resultado; as linhas, os valores e a chave de execução não mudam por causa dele.
"""
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main
import representation
from geo_complement import AUTHORIZED, PERIODS, state
from nearest_reference import TPL_11
from test_geo_complement import FIXED, inspection, layer_document, repo, write_layer  # noqa: F401 (fixture)

client = TestClient(main.app)
MAP = {"territory": "municipio", "territory_id": "codigo", "period": "periodo", "category": "categoria",
       "count": "quantidade", "population": "populacao", "latitude": "latitude", "longitude": "longitude"}
BASE = {"confirmed_roles": list(MAP), "count_unit": "pessoas", "population_denominator_confirmed": True,
        "fts_scope_confirmed": True, "object_confirmed": True, "category_filter": "MEDICINA", "period_filter": "2024"}
GEO = {"crs": "SIRGAS2000"}
# nome, código, (latitude, longitude) em 2023, (latitude, longitude) em 2024, quantidade, população.
UNITS = [("Manaus", "130260", (-3.119, -60.021), (-3.119, -60.021), 100, 10000),
         ("Tefe", "130420", (-3.354, -64.711), (-3.354, -64.711), 5, 10000),
         ("Mudou", "130340", (-2.600, -56.700), (-2.628, -56.736), 20, 10000),  # coordenada muda entre competências
         ("Santarem", "150680", (-2.443, -54.708), (-2.443, -54.708), 59, 25000),
         ("Boa Vista", "140010", (2.820, -60.672), (2.820, -60.672), 30, 10000),  # homônimos com códigos distintos
         ("Boa Vista", "250215", (-7.263, -36.237), (-7.263, -36.237), 3, 10000),
         ("Invalido", "130009", (63741, -60.0), (63741, -60.0), 50, 10000),
         ("Sem coordenada", "130008", (None, None), (None, None), 40, 10000)]


def frame(units=UNITS, comma=False):
    rows = []
    for period, index in (("2023", 2), ("2024", 3)):
        for name, code, *points, quantity, population in units:
            lat, lon = points[index - 2]
            fmt = (lambda v: None if v is None else str(v).replace(".", ",")) if comma else (lambda v: v)
            rows.append({"municipio": name, "codigo": code, "periodo": period, "categoria": "MEDICINA", "quantidade": quantity,
                         "populacao": population, "latitude": fmt(lat), "longitude": fmt(lon)})
    return pd.DataFrame(rows)


def analyze(df, operation="density", mapping=MAP, separator=",", **options):
    response = client.post("/api/analyze", files={"file": ("sintetico.csv", df.to_csv(index=False, sep=separator).encode())},
                           data={"mapping": json.dumps(mapping), "options": json.dumps({**BASE, **options}), "operation": operation})
    assert response.status_code == 200, response.text
    return response.json()


def points(geometry):
    return {key: (lat, lon) for key, lat, lon in zip(geometry["ids"], geometry["lat"], geometry["lon"])}


def expected(period):
    index = 0 if period == "2023" else 1
    return {"code:" + code: pts[index] for _, code, *pts, _, _ in UNITS}


def linked_ids(body):
    """Cada linha leva a um identificador estável pela coluna e chave declaradas no contrato."""
    contract = body["metadata"]["representacao"]
    rows = body[contract["tabela"]]
    link = contract["vinculo"]
    labels = {item["label"]: item["id"] for item in body["metadata"]["universe"]["members"]}
    prefix = {"codigo": "code:", "nome": "name:"}
    return [labels[row[link["coluna"]]] if link["chave"] == "rotulo" else prefix[link["chave"]] + str(row[link["coluna"]])
            for row in rows]


def test_density_geometry_is_the_effective_point_of_each_territory_in_the_period():
    for period in ("2023", "2024"):
        body = analyze(frame(), period_filter=period, **GEO)
        geometry = body["metadata"]["representacao"]["geometria"]
        assert geometry["estado"] == "DISPONIVEL" and geometry["competencia"] == period and geometry["referencial"] == "SIRGAS2000"
        valid = {key: point for key, point in expected(period).items() if point[0] is not None and abs(point[0]) <= 90}
        assert points(geometry) == valid  # coordenadas da própria competência, sem arredondamento
        assert geometry["complementados"] == [] and geometry["complemento_geografico"] is None  # upload: nunca complementado
        missing = {item["id"]: (item["condicao"], item["motivo"]) for item in geometry["sem_geometria"]}
        assert missing == {"code:130009": ("INVALIDA", "COORDENADA_INVALIDA"), "code:130008": ("AUSENTE", "SEM_INFORMACAO_ESPACIAL")}
        # Sem geometria não sai do resultado analítico: as linhas e os valores continuam na tabela.
        ids = linked_ids(body)
        assert sorted(ids) == sorted("code:" + code for _, code, *_ in UNITS)
        assert set(geometry["ids"]) | set(missing) == set(ids)
    assert points(analyze(frame(), period_filter="2023", **GEO)["metadata"]["representacao"]["geometria"])["code:130340"] == (-2.6, -56.7)


def test_homonyms_with_different_codes_are_distinct_points_and_labels():
    body = analyze(frame(), **GEO)
    labels = {item["id"]: item["label"] for item in body["metadata"]["universe"]["members"]}
    geometry = points(body["metadata"]["representacao"]["geometria"])
    assert labels["code:140010"] != labels["code:250215"] and geometry["code:140010"] != geometry["code:250215"]


@pytest.mark.parametrize("change, pending", [
    ({}, "REFERENCIAL_GEODESICO"),
    ({"crs": "WGS84"}, "REFERENCIAL_NAO_SUPORTADO"),
    ({"crs": "SIRGAS2000", "period_filter": ""}, "COMPETENCIA_UNICA"),
])
def test_map_without_authorized_geometry_is_blocked_with_reason_and_table_intact(change, pending):
    reference = analyze(frame(), **GEO)
    body = analyze(frame(), **{"crs": "", **change})
    geometry = body["metadata"]["representacao"]["geometria"]
    assert geometry["estado"] == "INDISPONIVEL" and geometry["desfecho"] == "BLQ-DAD" and geometry["pendencia"] == pending
    assert geometry["motivo"] and "ids" not in geometry
    if change.get("period_filter") != "":
        assert body["rows"] == reference["rows"]  # a representação não altera o resultado analítico


def test_coordinate_format_and_roles_must_be_established():
    comma = frame(comma=True)
    # D1: a vírgula decimal das coordenadas é verificada nos dados (quantidades e populações sem vírgula).
    verified = analyze(comma, separator=";", **GEO)["metadata"]["representacao"]["geometria"]
    assert verified["estado"] == "DISPONIVEL" and points(verified)["code:130340"] == (-2.628, -56.736)
    declared = analyze(comma, separator=";", number_format="decimal_comma", **GEO)["metadata"]["representacao"]["geometria"]
    assert declared["estado"] == "DISPONIVEL" and points(declared)["code:130340"] == (-2.628, -56.736)
    # Formato misto (vírgula numa coordenada, ponto em outra): o separador não pode ser verificado e continua escolha.
    mixed = comma.copy()
    mixed.loc[0, "latitude"] = "-3.119"
    body = analyze(mixed, separator=";", **GEO)
    assert body["metadata"]["representacao"]["geometria"]["pendencia"] == "SEPARADOR_DECIMAL"
    renamed = frame().rename(columns={"latitude": "y_coord", "longitude": "x_coord"})
    mapping = {**MAP, "latitude": "y_coord", "longitude": "x_coord"}
    roles = [role for role in MAP if role not in ("latitude", "longitude")]
    body = analyze(renamed, mapping=mapping, confirmed_roles=roles, **GEO)
    assert body["metadata"]["representacao"]["geometria"]["pendencia"] == "PAPEIS_COORDENADAS"
    without = {key: value for key, value in MAP.items() if key not in ("latitude", "longitude")}
    body = analyze(frame(), mapping=without, confirmed_roles=list(without), **GEO)
    assert body["metadata"]["representacao"]["geometria"]["pendencia"] == "COORDENADAS_NAO_ASSOCIADAS"


def test_operations_without_map_explain_why_and_series_stay_available():
    temporal = analyze(frame(), "temporal", period_filter="", temporal_indicator="density", temporal_comparability_confirmed=True,
                       territory_longitudinal_confirmed=True, territory_ids=["code:130260", "code:130420"], **GEO)
    contract = temporal["metadata"]["representacao"]
    assert contract["geometria"]["estado"] == "NAO_APLICAVEL" and "gráfico de linhas" in contract["geometria"]["motivo"]
    assert contract["serie"] == {"tabela": "detail_rows", "periodo": "Período", "territorio": "Território", "categoria": "Categoria",
                                 "valor": "Densidade por 1.000", "unidade": "por 1.000 habitantes", "tipo": "CONTINUO"}
    several = analyze(frame(), period_filter="", territory_ids=["code:130260"], **GEO)["metadata"]["representacao"]
    assert several["serie"]["tabela"] == "rows" and several["geometria"]["pendencia"] == "COMPETENCIA_UNICA"
    single = analyze(frame(), **GEO)["metadata"]["representacao"]
    assert single["serie"] is None  # uma competência não forma série
    aggregate = analyze(frame(), "aggregate", population_additive_confirmed=True, component_sum_confirmed=True,
                        territory_ids=["code:130260", "code:130420"], **GEO)["metadata"]["representacao"]
    assert aggregate["geometria"]["estado"] == "NAO_APLICAVEL"


def test_indicators_are_columns_of_the_result_with_units_and_capability_classes():
    density = analyze(frame(), **GEO)
    by_column = {item["coluna"]: item for item in density["metadata"]["representacao"]["indicadores"]}
    assert by_column["Densidade por 1.000"]["unidade"] == "por 1.000 habitantes" and by_column["Densidade por 1.000"]["tipo"] == "CONTINUO"
    assert by_column["Quantidade"] == {"coluna": "Quantidade", "rotulo": "Quantitativo", "tipo": "CONTAGEM", "unidade": "profissionais",
                                       "origem": "CAP-IND-01"}
    assert set(by_column) <= set(density["rows"][0])
    distribution = analyze(frame(), "distribution", distribution_indicator="density", quantile_count=5, **GEO)
    contract = distribution["metadata"]["representacao"]
    classes = next(item for item in contract["indicadores"] if item["coluna"] == "Quintil")
    assert contract["tabela"] == "detail_rows" and classes["tipo"] == "CLASSE" and classes["origem"] == "CAP-DIS-02"
    assert classes["classes"] == sorted({row["Quintil"] for row in distribution["detail_rows"] if row["Quintil"]})
    spatial = analyze(frame(), "spatial", reference_territory="Manaus [130260]", territory_ids=["code:130260", "code:130420"], **GEO)
    distance = spatial["metadata"]["representacao"]["indicadores"]
    assert distance == [{"coluna": "Distância (km)", "rotulo": "Distância ao território de referência", "tipo": "CONTINUO",
                         "unidade": "km", "origem": "CAP-ESP-01", "nota": TPL_11}]
    assert TPL_11 in spatial["metadata"]["representacao"]["notas"]


def test_nearest_geometry_covers_targets_and_references_including_other_states_and_invalid_ones():
    body = analyze(frame(), "nearest", reference_mode="list", reference_ids=["code:130260", "code:150680", "code:130009"],
                   territory_ids=["code:130260", "code:130420", "code:130340"], **GEO)
    structured = body["metadata"]["nearest_reference"]
    geometry = body["metadata"]["representacao"]["geometria"]
    located = points(geometry)
    assert "code:150680" in located  # referência de outra UF, fora do universo-alvo
    assert {item["id"]: item["condicao"] for item in geometry["sem_geometria"]} == {"code:130009": "INVALIDA"}
    assert geometry["ids"].count("code:130260") == 1  # alvo também referência: um único ponto
    for record in structured["cobertura_referencias"]:  # cada vínculo do resultado tem ponto no mapa
        assert record["unidade"] in located
        for scope in ("minimo_completo", "minimo_avaliaveis"):
            assert set(record[scope]["referencias"]) <= set(located)
    manaus = next(r for r in structured["cobertura_referencias"] if r["unidade"] == "code:130260")
    assert manaus["alvo_e_referencia"] and manaus["minimo_avaliaveis"]["distancia_km"] == 0
    assert manaus["minimo_completo"]["avaliabilidade"] == "NAO_AVALIAVEL"  # cobertura parcial nunca vira completa
    assert body["metadata"]["representacao"]["vinculo"] == {"coluna": "Código do alvo", "chave": "codigo"}
    assert set(linked_ids(body)) <= set(located)


def test_nearest_with_empty_reference_set_keeps_target_points():
    body = analyze(frame(), "nearest", reference_mode="criterion", reference_criterion={"operator": ">=", "value": "999"}, **GEO)
    assert body["metadata"]["nearest_reference"]["conjunto_referencias"]["n"] == 0
    geometry = body["metadata"]["representacao"]["geometria"]
    assert geometry["estado"] == "DISPONIVEL" and len(geometry["ids"]) == 6


def test_criteria_states_and_values_link_by_code():
    tree = {"logic": "and", "operands": [{"attribute": "densidade", "operator": "<", "value": "5"},
                                         {"attribute": "distancia", "operator": ">", "value": "100"}]}
    body = analyze(frame(), "criteria", criteria=tree, reference_mode="list", reference_ids=["code:130260"], **GEO)
    contract = body["metadata"]["representacao"]
    assert contract["vinculo"] == {"coluna": "Código", "chave": "codigo"}
    kinds = {item["coluna"]: item for item in contract["indicadores"]}
    assert kinds["Resultado"]["classes"] == ["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"]
    assert kinds["c2 · distância à referência mais próxima (km)"]["unidade"] == "km"
    states = {"code:" + row["Código"]: row["Resultado"] for row in body["rows"]}
    assert states == {item["elemento"]: item["estado"] for item in body["metadata"]["criterios"]["avaliacoes"]}
    geometry = contract["geometria"]
    assert set(states) == set(geometry["ids"]) | {item["id"] for item in geometry["sem_geometria"]}


def test_representation_never_changes_rows_or_execution_key(monkeypatch):
    first, second = analyze(frame(), **GEO), analyze(frame(), **GEO)
    assert first["metadata"]["execution_key"] == second["metadata"]["execution_key"]

    def broken(*args, **kwargs):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(representation, "payload", broken)
    failed = analyze(frame(), **GEO)
    assert failed["metadata"]["representacao"]["geometria"]["estado"] == "INDISPONIVEL"
    assert failed["rows"] == first["rows"] and failed["metadata"]["execution_key"] == first["metadata"]["execution_key"]


def brazil(operation="density", info=None, **extra):
    info = info or inspection()
    options = {"confirmed_roles": list(info["curated_defaults"]["confirmed_roles"]), "count_unit": "pessoas",
               "population_denominator_confirmed": True, "fts_scope_confirmed": True, "object_confirmed": True,
               "category_filter": "MEDICINA", "number_format": "decimal_comma", "crs": "SIRGAS2000", **extra}
    response = client.post("/api/analyze", data={"dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
                                                 "operation": operation, "mapping": json.dumps(info["suggested_mapping"]),
                                                 "options": json.dumps(options)})
    assert response.status_code == 200, response.text
    return response.json()


def test_brazil_automatic_map_is_contextual_and_does_not_change_calculations(repo, monkeypatch):
    """A premissa só desenha a versão íntegra governada; nem opções nem execução mudam."""
    automatic = brazil(period_filter="202406", crs="", number_format="")
    geometry = automatic["metadata"]["representacao"]["geometria"]
    assert geometry["estado"] == "DISPONIVEL" and geometry["ids"]
    assert geometry["referencial"] == "SIRGAS2000"
    assert "datum não declarado" in geometry["configuracao_apresentacao"]["premissa"]
    assert automatic["metadata"]["options"]["crs"] == ""
    assert automatic["metadata"]["options"]["number_format"] == ""
    explicit = brazil(period_filter="202406")
    assert points(geometry) == points(explicit["metadata"]["representacao"]["geometria"])
    assert automatic["rows"] == explicit["rows"]
    monkeypatch.setattr(representation, "curated_profile", lambda *_: None)
    blocked = brazil(period_filter="202406", crs="", number_format="")
    assert blocked["metadata"]["representacao"]["geometria"]["pendencia"] == "REFERENCIAL_GEODESICO"
    assert blocked["rows"] == automatic["rows"]
    assert blocked["metadata"]["execution_key"] == automatic["metadata"]["execution_key"]


def test_brazil_map_configuration_does_not_override_explicit_crs_or_external_version(repo, monkeypatch):
    unsupported = brazil(period_filter="202406", crs="WGS84")
    assert unsupported["metadata"]["representacao"]["geometria"]["pendencia"] == "REFERENCIAL_NAO_SUPORTADO"
    import hashlib
    import brazil_data
    external = repo.parent / "externa"
    external.mkdir()
    for key, filename in brazil_data.FILES.items():
        content = (repo / filename).read_bytes() + (b"\n" if key == "municipal" else b"")
        (external / filename).write_bytes(content)
    hashes = {key: hashlib.sha256((external / filename).read_bytes()).hexdigest() for key, filename in brazil_data.FILES.items()}
    (external / "manifest.json").write_text(json.dumps({"schema_version": 1, "sha256": hashes}), encoding="utf-8")
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(external))
    monkeypatch.setenv("ADT_BRASIL_DATA_VERSION", brazil_data.version_of(hashes))
    main._BRAZIL_FRAMES.clear()
    external = brazil(period_filter="202406", crs="", number_format="")
    assert external["metadata"]["representacao"]["geometria"]["pendencia"] == "REFERENCIAL_GEODESICO"


def test_complemented_points_use_the_layer_in_the_22_periods_with_its_identity(repo):  # noqa: F811
    before = brazil(period_filter="202406")["metadata"]["representacao"]["geometria"]
    # Camada ausente: os seis autorizados e o inválido não autorizado (999999) ficam sem geometria.
    assert {item["id"] for item in before["sem_geometria"]} == {"code:" + code for code in AUTHORIZED} | {"code:999999"}
    write_layer(repo, layer_document(repo))
    info = inspection()
    for period in PERIODS:
        geometry = brazil(info=info, period_filter=period)["metadata"]["representacao"]["geometria"]
        assert sorted(geometry["complementados"]) == sorted("code:" + code for code in AUTHORIZED)
        located = points(geometry)
        assert {code: located["code:" + code] for code in AUTHORIZED} == FIXED
        assert geometry["sem_geometria"] == [{"id": "code:999999", "condicao": "INVALIDA", "motivo": "COORDENADA_INVALIDA",
                                              "texto": "coordenada não numérica ou fora do intervalo"}]
        identity = geometry["complemento_geografico"]
        assert identity["estado"] == "valido" and identity["sha256"] == state()["sha256"] and identity["versao"] == "1"
        assert identity["premissa"] == "COORDENADA_FIXA_2014_2024" and identity["proveniencia"]["referencial"] == "SIRGAS 2000"
    contract = brazil(info=info, period_filter="202406")["metadata"]["representacao"]
    assert any("camada geográfica complementar" in note for note in contract["notas"])



@pytest.mark.parametrize("classes,label", [(4, "quartil"), (5, "quintil"), (10, "decil")])
def test_distribution_group_positions_from_backend_with_ties(classes, label):
    """O motor calcula duas posições; filtros da UI não refazem o cálculo."""
    data = [(*item[:4], 3 if item[4] == 5 else item[4], item[5]) for item in UNITS]
    body = analyze(frame(data), operation="distribution", distribution_indicator="quantity", quantile_count=classes)
    rows = body["detail_rows"]
    position = "Posição no " + label
    assert len(body["rows"]) == classes and len(rows) == len(data)
    assert sum(row["Unidades"] for row in body["rows"]) == len(data)
    assert all(position in row and "Posição geral" in row for row in rows)
    first = [row for row in rows if row["Quantidade"] == 3.0]
    assert len(first) == 2 and all(row["Posição geral"] == 1 for row in first)
    assert all(row[position] == min(r[position] for r in rows if r["Quintil"] == row["Quintil"])
               for row in first)
    assert sorted({row["Posição geral"] for row in rows}) == [1, 3, 4, 5, 6, 7, 8]
    assert all(row["Quintil"].endswith(label) for row in rows)
