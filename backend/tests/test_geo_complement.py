"""Camada geográfica complementar: validação, aplicação restrita e rastreável, identidade e isolamento.

Fixture sintética gerada em tempo de teste (coordenadas fictícias, não oficiais): os seis municípios
autorizados com ponto inválido nas 22 competências, municípios válidos e um inválido não autorizado.
"""
import copy
import hashlib
import json

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from pyproj import Geod

import brazil_data
import main
from brazil_catalog_profile import FIELDS
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from geo_complement import AUTHORIZED, LAYER, PERIODS, PREMISE, state

client = TestClient(main.app)
GEOD = Geod(ellps="GRS80")
# Pontos fictícios para os seis autorizados (latitude, longitude) e o padrão inválido da fonte original.
FIXED = {"170100": (-6.4, -48.1), "421265": (-28.4, -48.9), "422000": (-28.8, -49.2),
         "500490": (-20.1, -54.4), "430367": (-28.8, -51.1), "350050": (-22.5, -46.6)}
INVALID = {"170100": ("-63741", "-48,07976461"), "421265": ("-283844", "-488664"), "422000": ("-28831", "-49,23611111"),
           "500490": ("-20102", "-54,44068395"), "430367": ("-287993", "-51,095664"), "350050": ("-224716", "-466321")}
OTHERS = [("ALFA", "TO", "170001", "-7,1", "-48,2"), ("BETA", "SC", "420001", "-27,6", "-48,6"),
          ("GAMA", "SP", "350001", "-23,5", "-46,6"), ("DELTA", "MS", "500001", "-20,4", "-54,6"),
          ("FORA", "RS", "999999", "-999", "-51,0")]  # inválido e não autorizado: nunca complementado
TRACE = "Coordenada complementada (camada oficial)"
HEADER = ("regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
          "quantidade;população_estimada")


def municipal_text(valid_ananas_in=None, extra_period=None, names=None):
    lines = [HEADER]
    for period in PERIODS + ((extra_period,) if extra_period else ()):
        year, month = period[:4], str(int(period[4:]))
        for code, (name, uf) in AUTHORIZED.items():
            lat, lon = ("-6,3", "-48,0") if (code == "170100" and period == valid_ananas_in) else INVALID[code]
            lines.append(f"R;{uf};{(names or {}).get(code, name)};{code};{lat};{lon};MEDICINA;{year};{month};3;1000")
        for name, uf, code, lat, lon in OTHERS:
            lines.append(f"R;{uf};{name};{code};{lat};{lon};MEDICINA;{year};{month};4;1000")
    return "\n".join(lines) + "\n"


def layer_document(root, **changes):
    data = {"schema_version": 1, "identificador": "fixture-sintetica-de-teste", "versao": "1",
            "aplica_se_a": {"arquivo": FILES["municipal"],
                            "sha256": hashlib.sha256((root / FILES["municipal"]).read_bytes()).hexdigest()},
            "escopo_temporal": {"competencias": list(PERIODS)},
            "premissa": {"tipo": PREMISE, "origem": "decisao_metodologica_do_usuario", "descricao": "teste"},
            "fonte": {"produto": "FIXTURE SINTÉTICA DE TESTE (não oficial)", "edicao": "teste",
                      "url": "https://geoftp.ibge.gov.br/organizacao_do_territorio/teste", "ponto": "sede municipal",
                      "referencial": "SIRGAS 2000", "evidencia_referencial": "metadado sintético de teste",
                      "sha256_arquivo": "0" * 64},
            "municipios": [{"codigo_base": code, "codigo_ibge": code + "0", "municipio": AUTHORIZED[code][0],
                            "uf": AUTHORIZED[code][1], "latitude": lat, "longitude": lon} for code, (lat, lon) in FIXED.items()]}
    for key, value in changes.items():
        data[key] = value
    return data


def write_layer(root, data):
    (root / LAYER).parent.mkdir(parents=True, exist_ok=True)
    (root / LAYER).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def repo(tmp_path, monkeypatch, request):
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    book.active.append(["Brasil", 2024, 6, "MEDICINA", 100])
    book.save(root / FILES["national"])
    (root / FILES["municipal"]).write_text(municipal_text(**getattr(request, "param", {})), encoding="utf-8")
    (root / GOVERNED_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (root / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(root)), encoding="utf-8")
    monkeypatch.setattr(brazil_data, "REPO_ROOT", root)
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    main._BRAZIL_FRAMES.clear()
    originals = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES.values()}
    yield root
    assert originals == {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES.values()}
    main._BRAZIL_FRAMES.clear()


def inspection():
    response = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"})
    assert response.status_code == 200, response.text
    return response.json()


def options(**extra):
    return {"confirmed_roles": list(FIELDS["municipal"]), "count_unit": "pessoas", "population_denominator_confirmed": True,
            "fts_scope_confirmed": True, "object_confirmed": True, "number_format": "decimal_comma", "crs": "SIRGAS2000",
            "category_filter": "MEDICINA", **extra}


def analyze(operation, info=None, geo_version="", **extra):
    info = info or inspection()
    data = {"dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"], "operation": operation,
            "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options(**extra))}
    if geo_version:
        data["geo_version"] = geo_version
    return client.post("/api/analyze", data=data)


def nearest(period, refs, **extra):
    response = analyze("nearest", period_filter=period, reference_mode="list", reference_ids=refs, **extra)
    assert response.status_code == 200, response.text
    body = response.json()
    return body, {r["unidade"]: r for r in body["metadata"]["nearest_reference"]["cobertura_referencias"]}


def km(a, b):
    return GEOD.inv(a[1], a[0], b[1], b[0])[2] / 1000


def test_absent_layer_keeps_invalid_points_not_evaluable(repo):
    assert state()["estado"] == "ausente"
    body, units = nearest("202406", ["code:170001"])
    assert all(units["code:" + code]["condicao_espacial"] == "INVALIDA" for code in AUTHORIZED)
    geo = body["metadata"]["nearest_reference"]["complemento_geografico"]
    assert geo["estado"] == "ausente" and geo["territorios_complementados"] == []
    assert any("Camada geográfica complementar ausente" in note for note in body["notes"])
    assert body["metadata"]["complemento_geografico"]["estado"] == "ausente"


def test_valid_layer_applies_the_fixed_point_to_the_six_units_in_all_22_periods(repo):
    write_layer(repo, layer_document(repo))
    current = state()
    assert current["estado"] == "valido" and current["excecoes"] == []
    refs = ["code:170001", "code:420001", "code:350001", "code:500001"]
    for period in PERIODS:
        body, units = nearest(period, refs)
        for code, point in FIXED.items():
            record = units["code:" + code]
            assert record["condicao_espacial"] == "VALIDA" and record["coordenada"] == "complementada", (period, code)
            expected = min(km(point, (float(lat.replace(",", ".")), float(lon.replace(",", "."))))
                           for _, _, c, lat, lon in OTHERS if "code:" + c in refs)
            assert record["minimo_completo"]["distancia_km"] == expected  # mesmo método, valor idêntico
        # Demais municípios preservados: válidos seguem originais; o inválido não autorizado continua inválido.
        assert units["code:999999"]["condicao_espacial"] == "INVALIDA" and units["code:999999"]["coordenada"] == "original"
        assert all(units["code:" + c]["coordenada"] == "original" for _, _, c, _, _ in OTHERS)
        geo = body["metadata"]["nearest_reference"]["complemento_geografico"]
        assert sorted(geo["municipios_complementados"]) == sorted(AUTHORIZED) and geo["linhas_complementadas"] == 6


def test_complemented_distances_equal_an_independent_geodesic(repo):
    write_layer(repo, layer_document(repo))
    body, units = nearest("201401", ["code:170100", "code:350050"])  # duas referências complementadas
    for code, point in FIXED.items():
        expected = min(km(point, FIXED["170100"]), km(point, FIXED["350050"]))
        assert units["code:" + code]["minimo_completo"]["distancia_km"] == expected
    alfa = units["code:170001"]["minimo_completo"]
    assert alfa["distancia_km"] == min(km((-7.1, -48.2), FIXED["170100"]), km((-7.1, -48.2), FIXED["350050"]))
    traced = {item["id"]: item for item in body["metadata"]["nearest_reference"]["complemento_geografico"]["territorios_complementados"]}
    assert (traced["code:170100"]["latitude"], traced["code:170100"]["longitude"]) == FIXED["170100"]


def test_reference_sets_and_minima_per_period_become_complete_with_the_layer(repo):
    criterion = {"reference_mode": "criterion", "reference_criterion": {"operator": "<=", "value": "3"}}
    for period in ("201401", "201906", "202406"):
        before = analyze("nearest", period_filter=period, **criterion).json()["metadata"]["nearest_reference"]
        assert before["conjunto_referencias"]["n"] == 6 and before["cobertura"]["n_minimo_completo"] == 0
    write_layer(repo, layer_document(repo))
    for period in ("201401", "201906", "202406"):
        after = analyze("nearest", period_filter=period, **criterion).json()["metadata"]["nearest_reference"]
        assert {m["id"] for m in after["conjunto_referencias"]["membros"]} == {"code:" + c for c in AUTHORIZED}
        assert after["referencias_nao_avaliaveis"] == []
        assert after["cobertura"]["n_minimo_completo"] == len(AUTHORIZED) + len(OTHERS) - 1  # só FORA segue inválido


@pytest.mark.parametrize("damage", ["json", "esquema", "nao_autorizado", "nome", "codigo_oficial", "intervalo",
                                    "referencial", "evidencia_crs", "sha_fonte", "escopo", "premissa", "fonte_externa"])
def test_invalid_layer_is_never_applied(repo, damage):
    data = layer_document(repo)
    item = data["municipios"][0]
    if damage == "json":
        (repo / LAYER).parent.mkdir(parents=True, exist_ok=True)
        (repo / LAYER).write_text("{", encoding="utf-8")
    else:
        if damage == "esquema":
            data["schema_version"] = 2
        elif damage == "nao_autorizado":
            data["municipios"].append({**copy.deepcopy(item), "codigo_base": "999999", "codigo_ibge": "9999990"})
        elif damage == "nome":
            item["municipio"] = "OUTRO NOME"
        elif damage == "codigo_oficial":
            item["codigo_ibge"] = "1234567"
        elif damage == "intervalo":
            item["latitude"] = -95.0
        elif damage == "referencial":
            data["fonte"]["referencial"] = "WGS84"
        elif damage == "evidencia_crs":
            del data["fonte"]["evidencia_referencial"]  # referencial declarado sem evidência da fonte
        elif damage == "sha_fonte":
            del data["fonte"]["sha256_arquivo"]
        elif damage == "escopo":
            data["escopo_temporal"]["competencias"] = list(PERIODS[:-1])
        elif damage == "premissa":
            data["premissa"]["tipo"] = "INTERPOLACAO"
        else:
            data["fonte"]["url"] = "https://exemplo.com/coordenadas.csv"
        write_layer(repo, data)
    assert state()["estado"] == "invalido"
    body, units = nearest("202406", ["code:170001"])
    assert all(units["code:" + code]["condicao_espacial"] == "INVALIDA" for code in AUTHORIZED)
    assert body["metadata"]["complemento_geografico"]["estado"] == "invalido"


def test_layer_for_another_version_of_the_municipal_source_is_not_applied(repo):
    before, _ = nearest("202406", ["code:170001"])
    data = layer_document(repo)
    data["aplica_se_a"]["sha256"] = "f" * 64
    write_layer(repo, data)
    body, units = nearest("202406", ["code:170001"])
    assert units["code:170100"]["condicao_espacial"] == "INVALIDA"
    assert body["metadata"]["nearest_reference"]["complemento_geografico"]["estado"] == "incompativel"
    # Metadados, preparação e chave de execução coerentes com a camada não aplicada a esta versão da fonte.
    assert body["metadata"]["complemento_geografico"]["estado"] == "incompativel"
    assert inspection()["catalog"]["complemento_geografico"]["estado"] == "incompativel"
    assert body["metadata"]["execution_key"] == before["metadata"]["execution_key"]
    assert body["rows"] == before["rows"]


def test_uploads_never_receive_the_governed_complement(repo):
    write_layer(repo, layer_document(repo))
    mapping = {"territory": "municipio", "territory_id": "cod_ibge", "period": "periodo", "category": "categoria_profissional",
               "count": "quantidade", "population": "população_estimada", "latitude": "latitude", "longitude": "longitude"}
    text = municipal_text().replace("periodo_ano;periodo_mes", "periodo;mes")
    upload = client.post("/api/analyze", files={"file": ("importada.csv", text.encode("utf-8"))}, data={
        "operation": "nearest", "mapping": json.dumps(mapping),
        "options": json.dumps(options(confirmed_roles=list(mapping), period_filter="2024", reference_mode="list",
                                      reference_ids=["code:170001"]))})
    assert upload.status_code == 200, upload.text
    units = {r["unidade"]: r for r in upload.json()["metadata"]["nearest_reference"]["cobertura_referencias"]}
    assert units["code:170100"]["condicao_espacial"] != "VALIDA" and units["code:170100"]["coordenada"] == "original"
    assert "complemento_geografico" not in upload.json()["metadata"]
    assert "complemento_geografico" not in upload.json()["metadata"]["nearest_reference"]
    assert all(TRACE not in row for row in upload.json()["rows"])


def test_exported_rows_and_metadata_trace_the_complemented_points(repo):
    body, _ = nearest("202406", ["code:170001"])
    assert all(TRACE not in row for row in body["rows"])  # camada ausente: linhas exportadas inalteradas
    write_layer(repo, layer_document(repo))
    body, _ = nearest("202406", ["code:170100"])  # a própria referência tem ponto complementado
    rows = {row["Código do alvo"]: row for row in body["rows"]}
    assert rows["170100"][TRACE] == rows["350050"][TRACE] == "Alvo e referência"
    assert rows["170001"][TRACE] == "Referência" and rows["999999"][TRACE] == "Não"
    geo = body["metadata"]["complemento_geografico"]
    assert geo["estado"] == "valido" and geo["sha256"] == state()["sha256"] and geo["versao"] == "1"
    assert geo["proveniencia"]["referencial"] == "SIRGAS 2000" and geo["proveniencia"]["ponto"] == "sede municipal"
    traced = body["metadata"]["nearest_reference"]["complemento_geografico"]
    assert traced["premissa"] == PREMISE and traced["escopo_temporal"] == ["201401", "202406"]


def test_non_spatial_identity_is_unchanged_and_spatial_identity_follows_the_layer(repo):
    density_before = analyze("density", period_filter="202406").json()
    nearest_before = analyze("nearest", period_filter="202406", reference_mode="list", reference_ids=["code:170001"]).json()
    write_layer(repo, layer_document(repo))
    density_after = analyze("density", period_filter="202406").json()
    nearest_after = analyze("nearest", period_filter="202406", reference_mode="list", reference_ids=["code:170001"]).json()
    assert density_after["rows"] == density_before["rows"]
    assert density_after["metadata"]["execution_key"] == density_before["metadata"]["execution_key"]
    assert density_after["metadata"]["data_sha256"] == density_before["metadata"]["data_sha256"]
    assert "complemento_geografico" not in density_after["metadata"]
    assert nearest_after["metadata"]["execution_key"] != nearest_before["metadata"]["execution_key"]
    write_layer(repo, layer_document(repo, versao="2"))
    nearest_v2 = analyze("nearest", period_filter="202406", reference_mode="list", reference_ids=["code:170001"]).json()
    assert nearest_v2["metadata"]["execution_key"] != nearest_after["metadata"]["execution_key"]


def test_analysis_prepared_with_another_layer_version_is_refused(repo):
    info = inspection()
    token = info["catalog"]["complemento_geografico"]["token"]
    assert token == "ausente"
    write_layer(repo, layer_document(repo))
    stale = analyze("nearest", info=info, geo_version=token, period_filter="202406", reference_mode="list",
                    reference_ids=["code:170001"])
    assert stale.status_code == 422 and "camada geográfica complementar mudou" in stale.json()["detail"]
    fresh = inspection()
    current = fresh["catalog"]["complemento_geografico"]["token"]
    assert current == state()["sha256"]
    assert analyze("nearest", info=fresh, geo_version=current, period_filter="202406", reference_mode="list",
                   reference_ids=["code:170001"]).status_code == 200
    # Análises não espaciais não dependem da camada e não são recusadas por ela.
    assert analyze("density", info=info, geo_version=token, period_filter="202406").status_code == 200


def test_existing_spatial_analysis_uses_the_layer_with_traceability(repo):
    selection = {"period_filter": "202406", "reference_territory": "ALFA [170001]",
                 "territory_ids": ["code:" + c for c in AUTHORIZED] + ["code:170001"]}
    before = analyze("spatial", **selection)
    assert before.status_code == 422  # pontos inválidos impedem a análise espacial desse recorte
    write_layer(repo, layer_document(repo))
    response = analyze("spatial", **selection)
    assert response.status_code == 200, response.text
    body = response.json()
    rows = {r["Território"]: r for r in body["rows"]}
    column = "Coordenada complementada (camada oficial)"
    assert all(row[column] == "Território" for name, row in rows.items() if not name.startswith("ALFA"))
    assert next(row for name, row in rows.items() if name.startswith("ALFA"))[column] == "Não"
    ananas = next(row for name, row in rows.items() if name.startswith("ANANAS"))
    assert ananas["Distância (km)"] == pytest.approx(km((-7.1, -48.2), FIXED["170100"]), abs=1e-9)  # ordem inversa no motor espacial
    assert any("camada geográfica complementar" in note for note in body["notes"])
    assert body["metadata"]["complemento_geografico"]["estado"] == "valido"
    provenance = body["metadata"]["complemento_geografico"]["proveniencia"]  # registrada no próprio resultado
    assert provenance["produto"].startswith("FIXTURE SINTÉTICA") and provenance["sha256_arquivo"] == "0" * 64


@pytest.mark.parametrize("repo", [{"names": {"170100": "OUTRO MUNICIPIO", "350050": "Águas de Lindóia"}}], indirect=True)
def test_point_is_complemented_only_when_the_name_in_the_base_matches(repo):
    write_layer(repo, layer_document(repo))
    for period in ("201401", "202406"):
        body, units = nearest(period, ["code:170001"])
        assert units["code:170100"]["condicao_espacial"] == "INVALIDA" and units["code:170100"]["coordenada"] == "original"
        # Caixa e acentos não distinguem o nome conferido.
        assert units["code:350050"]["condicao_espacial"] == "VALIDA" and units["code:350050"]["coordenada"] == "complementada"
        geo = body["metadata"]["nearest_reference"]["complemento_geografico"]
        assert sorted(geo["municipios_complementados"]) == sorted(set(AUTHORIZED) - {"170100"}) and geo["linhas_complementadas"] == 5


@pytest.mark.parametrize("repo", [{"valid_ananas_in": "201401", "extra_period": "202312"}], indirect=True)
def test_valid_original_points_and_periods_outside_the_scope_are_never_complemented(repo):
    write_layer(repo, layer_document(repo))
    _, units = nearest("201401", ["code:170001"])
    assert units["code:170100"]["coordenada"] == "original"  # ponto original válido preservado
    assert units["code:170100"]["minimo_completo"]["distancia_km"] == km((-6.3, -48.0), (-7.1, -48.2))
    assert units["code:350050"]["coordenada"] == "complementada"
    _, outside = nearest("202312", ["code:170001"])
    assert all(outside["code:" + code]["condicao_espacial"] == "INVALIDA" for code in AUTHORIZED)  # fora das 22 competências


def test_combined_criteria_with_distance_follow_the_layer_and_uf_uses_the_governed_rule(repo):
    tree = {"logic": "and", "operands": [{"attribute": "uf", "operator": "=", "value": "SC"},
                                         {"attribute": "distancia", "operator": ">", "value": "100"}]}
    spatial = {"period_filter": "202406", "criteria": tree, "reference_mode": "list", "reference_ids": ["code:420001"]}
    density = {"period_filter": "202406", "criteria": {"attribute": "densidade", "operator": "<", "value": "4"}}
    before, density_before = analyze("criteria", **spatial).json(), analyze("criteria", **density).json()
    result = {item["elemento"]: item for item in before["metadata"]["criterios"]["avaliacoes"]}
    assert result["code:421265"]["estado"] == result["code:422000"]["estado"] == "NAO_AVALIAVEL"  # SC, ponto inválido
    assert result["code:350050"]["estado"] == "NAO_ATENDE"  # SP: a UF decide, mesmo sem coordenada
    write_layer(repo, layer_document(repo))
    after, density_after = analyze("criteria", **spatial).json(), analyze("criteria", **density).json()
    result = {item["elemento"]: item for item in after["metadata"]["criterios"]["avaliacoes"]}
    beta = (-27.6, -48.6)
    for code in ("421265", "422000"):
        distance = km(FIXED[code], beta)
        assert result["code:" + code]["nos"]["c2"]["valor"] == distance
        assert result["code:" + code]["estado"] == ("ATENDE" if distance > 100 else "NAO_ATENDE")
    assert after["metadata"]["complemento_geografico"]["estado"] == "valido"
    assert after["metadata"]["criterios"]["referencias"]["complemento_geografico"]["linhas_complementadas"] == 6
    assert after["metadata"]["execution_key"] != before["metadata"]["execution_key"]
    assert density_after["metadata"]["execution_key"] == density_before["metadata"]["execution_key"]
    assert "complemento_geografico" not in density_after["metadata"]


def test_governed_version_resolves_crs_and_decimal_separator_only_in_distance_analyses(repo, monkeypatch):
    """Versão governada: SIRGAS 2000 (regra do perfil) e vírgula decimal (verificada nos dados) sem declaração do usuário."""
    import llm_bridge

    def forbidden(*args, **kwargs):
        raise AssertionError("Nenhuma chamada ao provedor de IA neste teste")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    write_layer(repo, layer_document(repo))
    info = inspection()
    origins = {item["option"]: item["origin"] for item in info["curated_defaults"]["premises"]}
    assert (origins["crs"], origins["number_format"]) == ("PERFIL_GOVERNADO", "VERIFICADA_NOS_DADOS")
    internal = {"crs": "", "number_format": ""}
    tree = {"logic": "and", "operands": [{"attribute": "uf", "operator": "=", "value": "SC"},
                                         {"attribute": "distancia", "operator": ">", "value": "100"}]}
    runs = {"spatial": {"reference_territory": "ALFA [170001]", "territory_ids": ["code:" + c for c in AUTHORIZED] + ["code:170001"]},
            "nearest": {"reference_mode": "list", "reference_ids": ["code:170001"]},
            "criteria": {"criteria": tree, "reference_mode": "list", "reference_ids": ["code:420001"]}}
    for operation, selection in runs.items():
        gate = client.post("/api/preflight", data={"dataset": "brazil", "scope": "municipal", "operation": operation,
                                                  "dataset_version": info["source"]["version"],
                                                  "mapping": json.dumps(info["suggested_mapping"]),
                                                  "options": json.dumps(options(period_filter="202406", **selection, **internal))})
        capability = gate.json()["capabilities"][operation]
        assert capability["status"] == "available", capability["reasons"]
        assert {"status": "met", "title": "Referencial geodésico",
                "detail": "SIRGAS 2000, premissa governada da base Brasil oficial."} in capability["requirements"]
        declared = analyze(operation, info=info, period_filter="202406", **selection)
        governed = analyze(operation, info=info, period_filter="202406", **selection, **internal)
        assert declared.status_code == governed.status_code == 200, governed.text
        declared, governed = declared.json(), governed.json()
        assert governed["rows"] == declared["rows"]
        used = governed["metadata"]["options"]
        assert (used["crs"], used["number_format"]) == ("SIRGAS2000", "decimal_comma")
        assert used["governed_premises"][-2:] == ["crs", "number_format"]
        assert not {"crs", "number_format"} & set(declared["metadata"]["options"]["governed_premises"])  # informados
        notes = " ".join(governed["notes"])
        assert "Referencial geodésico: SIRGAS 2000, premissa governada" in notes
        assert "Separador decimal das coordenadas: vírgula, verificada nos dados" in notes
        assert "Referencial geodésico: SIRGAS 2000" not in " ".join(declared["notes"])
        geometry = governed["metadata"]["representacao"]["geometria"]
        assert geometry["estado"] == "DISPONIVEL" and geometry["configuracao_apresentacao"] is None
        assert geometry["premissa_referencial"].startswith("SIRGAS 2000, premissa governada")
        assert declared["metadata"]["representacao"]["geometria"]["premissa_referencial"] is None
    # Sem distância, nenhuma das duas opções entra no cálculo; o mapa continua só de apresentação.
    density = analyze("density", info=info, period_filter="202406", **internal).json()
    assert (density["metadata"]["options"]["crs"], density["metadata"]["options"]["number_format"]) == ("", "")
    assert not {"crs", "number_format"} & set(density["metadata"]["options"]["governed_premises"])
    geometry = density["metadata"]["representacao"]["geometria"]
    assert geometry["configuracao_apresentacao"]["origem"] == "configuracao_contextual_base_brasil"
    assert geometry["premissa_referencial"] is None
    # O contexto da conversa mantém todas as premissas: o resultado sem distância continua na mesma preparação.
    headers = {"X-ADT-Session": client.post("/api/session").json()["token"]}
    context = {"dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
               "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options(period_filter="202406", **internal))}
    result = client.post("/api/analyze", headers=headers, data={**context, "operation": "density"}).json()
    reply = client.post("/api/llm/interpret-context", headers=headers,
                        data={**context, "message": "O que esse resultado significa?", "displayed_result_id": result["result_id"]})
    assert reply.status_code == 200, reply.text
    assert reply.json()["result_reference"]["same_preparation"] is True
    # O que o usuário informa explicitamente prevalece, inclusive quando é incompatível ou não suportado.
    assert analyze("nearest", info=info, period_filter="202406", **runs["nearest"], number_format="decimal_point").status_code == 422
    assert analyze("nearest", info=info, period_filter="202406", **runs["nearest"], crs="WGS84").status_code == 422


def test_decimal_separator_premise_requires_evidence_and_only_reaches_the_governed_version():
    import pandas as pd
    from brazil_catalog_profile import curated_profile
    mapping = dict(FIELDS["municipal"])
    frame = pd.DataFrame({"municipio": ["A", "A"], "cod_ibge": ["001", "001"], "Período (ano e mês)": ["202306", "202406"],
                          "categoria_profissional": ["MEDICINA"] * 2, "quantidade": ["6", "10"],
                          "população_estimada": ["1000", "1000"], "latitude": ["-10,1", "-10"], "longitude": ["-40,1", "-40"]})
    governed = {"integridade": "verificada", "versao": "v1", "versao_governada": "v1"}

    def premises(changes=None, catalog=governed):
        data = frame.assign(**(changes or {}))
        data.attrs = {"source": {"dataset": "brazil", "scope": "municipal"}, "catalog": catalog}
        return [item["option"] for item in curated_profile(data, mapping)["premises"]]

    assert premises()[-2:] == ["crs", "number_format"]
    # Ponto decimal, outra notação, nenhuma vírgula ou vírgula em quantidades: o separador volta a ser pedido.
    for changes in ({"latitude": ["-10.1", "-10"]}, {"longitude": ["-40,1", "4e1"]}, {"quantidade": ["6,0", "10"]},
                    {"latitude": ["-10", "-10"], "longitude": ["-40", "-40"]}):
        assert premises(changes)[-1] == "crs", changes
    # Versão externa fixada ou integridade não verificada: nenhuma das duas premissas.
    for catalog in ({**governed, "versao_governada": "v0"}, {**governed, "integridade": "divergente"}, {}):
        assert not {"crs", "number_format"} & set(premises(catalog=catalog))
