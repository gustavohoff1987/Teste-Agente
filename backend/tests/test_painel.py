"""Painel integrado de bolhas (Adendo BOL-20261021 da SPEC; Docs/PAINEL_INTEGRADO.md): POST /api/painel e
POST /api/painel/referencias.

O catálogo sintético é instalado como versão governada num repositório temporário (como em test_geo_complement.py),
para valerem as premissas do perfil oficial, entre elas o referencial SIRGAS 2000 e a vírgula decimal das coordenadas.
Seis municípios e três competências, com valores fictícios:
- empate exato de densidade em 202406 (TEFE e PARINTINS, 10 por 1.000; MANACAPURU e NOVO AIRAO, 8 por 1.000);
- quantidade zero em 202006 (TEFE: base zero da variação percentual);
- MANACAPURU sem coordenadas (distância não avaliável);
- NOVO AIRAO sem registro em 202006 (sem variação, agregado parcial e conjunto com membros diferentes).
Os valores esperados vêm de contas independentes (Fraction e pyproj) e das análises existentes (/api/analyze). Os
testes com a base versionada, no fim, rodam no job dados-reais (ADT_REAL_DATA_DIR), somente em leitura.
"""
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import llm_bridge
import main
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from install_brazil_data import install
from nearest_reference import GEOD

client = TestClient(main.app)
PERIODS = ["202006", "202306", "202406"]
HEADER = ("regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
          "quantidade;população_estimada")
# código: (nome, UF, latitude e longitude com vírgula decimal, quantidades e populações por competência)
UNITS = {
    "130260": ("MANAUS", "AM", ("-3,1", "-60,0"), [40, 44, 50], [2000, 2100, 2200]),
    "130420": ("TEFE", "AM", ("-3,3", "-64,7"), [0, 5, 6], [600, 600, 600]),
    "130340": ("PARINTINS", "AM", ("-2,6", "-56,7"), [10, 11, 12], [1000, 1100, 1200]),
    "130250": ("MANACAPURU", "AM", ("", ""), [8, 8, 8], [1000, 1000, 1000]),
    "130390": ("NOVO AIRAO", "AM", ("-2,6", "-60,9"), [None, 3, 4], [None, 500, 500]),
    "150140": ("BELEM", "PA", ("-1,4", "-48,5"), [50, 52, 56], [3000, 3000, 3000]),
}
MANAUS, TEFE, PARINTINS, MANACAPURU, NOVO, BELEM = ("code:" + code for code in UNITS)
TOP = {"competencia", "competencia_inicial", "categoria", "versao_base", "chave_execucao", "referencia", "itens",
       "dominios", "notas", "limitacoes"}
UNIT = {"id", "tipo", "rotulo", "uf", "populacao", "quantidade", "densidade", "distancia_km", "inicial",
        "variacao_percentual", "avaliavel", "motivos", "referencia"}
SET = {"id", "tipo", "rotulo", "membros", "populacao", "quantidade", "densidade", "contagem", "distancia_km",
       "distancia_km_max", "inicial", "variacao_percentual", "avaliavel", "motivos", "referencia"}
DOMAINS = {"densidade", "quantidade", "populacao", "distancia_km", "variacao_densidade", "variacao_quantidade",
           "variacao_populacao"}
THREE = {"populacao", "quantidade", "densidade"}
FULL = {"competencia": "202406", "competencia_inicial": "202006", "categoria": "MEDICINA",
        "base": {"municipios": {"estados": ["13"]}},
        "conjuntos": [{"id": "c1", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]}],
        "referencia": {"membros": [BELEM], "criterio": {"atributo": "densidade", "ordem": "desc"}}}


def municipal_text():
    lines = [HEADER]
    for i, period in enumerate(PERIODS):
        for code, (name, uf, (lat, lon), counts, populations) in UNITS.items():
            if counts[i] is None:
                continue
            lines.append(";".join(["NORTE", uf, name, code, lat, lon, "MEDICINA", period[:4], str(int(period[4:])),
                                   str(counts[i]), str(populations[i])]))
    return "\n".join(lines) + "\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Repositório temporário com o catálogo sintético como versão governada (manifesto próprio)."""
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for period in PERIODS:
        book.active.append(["Brasil", int(period[:4]), int(period[4:]), "MEDICINA", 1000])
    book.save(root / FILES["national"])
    (root / FILES["municipal"]).write_text(municipal_text(), encoding="utf-8")
    write_state_source(root, {("AM", period): 100 for period in PERIODS})
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
    assert response.status_code == 200, response.text[:2000]
    return response.json()


def post(info, path="/api/painel", headers=None, **options):
    return client.post(path, headers=headers or {}, data={
        "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options)})


def analyze(info, operation, abrangencia=None, **options):
    if abrangencia is not None:
        options["abrangencia"] = abrangencia
    return client.post("/api/analyze", data={
        "dataset": "brazil", "scope": "auto" if abrangencia is not None else "municipal",
        "dataset_version": info["source"]["version"], "operation": operation,
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options)})


def nearest_units(info, references, period="202406"):
    """Análise da referência mais próxima (compute_nearest) com a lista explícita de referências."""
    body = ok(analyze(info, "nearest", period_filter=period, reference_mode="list", reference_ids=references,
                      crs="SIRGAS2000", number_format="decimal_comma", category_filter="MEDICINA"))
    return {record["unidade"]: record for record in body["metadata"]["nearest_reference"]["cobertura_referencias"]}


def ok(response):
    assert response.status_code == 200, response.text[:2000]
    return response.json()


def refused(response, text):
    assert response.status_code == 422, response.text[:2000]
    assert text in response.json()["detail"], response.json()["detail"]


def by_id(body):
    return {item["id"]: item for item in body["itens"]}


def km(a, b):
    """Geodésica independente (pyproj, GRS80) entre dois municípios do catálogo sintético, em km."""
    (lat_a, lon_a), (lat_b, lon_b) = (tuple(float(v.replace(",", ".")) for v in UNITS[key[5:]][2]) for key in (a, b))
    return GEOD.inv(lon_a, lat_a, lon_b, lat_b)[2] / 1000


def density(key, period):
    i = PERIODS.index(period)
    return UNITS[key[5:]][3][i] / UNITS[key[5:]][4][i] * 1000


def percent(before, after):
    return float((Fraction(after) - Fraction(before)) / Fraction(before) * 100)


def test_response_has_exactly_the_contract_keys(repo):
    info = inspection()
    body = ok(post(info, **FULL))
    assert set(body) == TOP
    assert (body["competencia"], body["competencia_inicial"], body["categoria"]) == ("202406", "202006", "MEDICINA")
    assert body["versao_base"] == info["source"]["version"] and len(body["chave_execucao"]) == 64
    units = [item for item in body["itens"] if item["tipo"] == "municipio"]
    sets = [item for item in body["itens"] if item["tipo"] == "conjunto"]
    # Municípios base do AM e a referência (BELEM, fora da base) na ordem do código IBGE; o conjunto vem depois.
    assert [item["id"] for item in units] == [MANACAPURU, MANAUS, PARINTINS, NOVO, TEFE, BELEM]
    assert [item["id"] for item in sets] == ["c1"] and body["itens"][-1]["id"] == "c1"
    assert all(set(item) == UNIT for item in units) and all(set(item) == SET for item in sets)
    for item in body["itens"]:
        assert set(item["inicial"]) == THREE == set(item["variacao_percentual"])
        assert set(item["avaliavel"]) == {"densidade", "distancia", "variacao"}
        assert all(isinstance(text, str) for text in item["motivos"]) and isinstance(item["referencia"], bool)
    assert set(body["dominios"]) == DOMAINS
    assert all(value is None or (len(value) == 2 and value[0] <= value[1]) for value in body["dominios"].values())
    assert set(body["referencia"]) == {"tipo", "membros", "origem"}
    assert body["referencia"]["membros"] == [{"id": BELEM, "rotulo": "BELEM (PA)"}]
    assert all(isinstance(text, str) for text in body["notas"] + body["limitacoes"])
    json.dumps(body, allow_nan=False)
    # A chave de execução é reproduzível e muda com o pedido.
    assert ok(post(info, **FULL))["chave_execucao"] == body["chave_execucao"]
    assert ok(post(info, **{**FULL, "competencia_inicial": "202306"}))["chave_execucao"] != body["chave_execucao"]
    # Sem referência e sem competência inicial: as mesmas chaves, com null onde nada foi pedido.
    plain = ok(post(info, competencia="202406", base={"municipios": {"ids": [MANAUS]}}))
    assert set(plain) == TOP and plain["referencia"] is None and plain["competencia_inicial"] is None
    [item] = plain["itens"]
    assert set(item) == UNIT and item["distancia_km"] is None and item["referencia"] is False
    assert item["avaliavel"] == {"densidade": True, "distancia": None, "variacao": None} and item["motivos"] == []
    assert item["inicial"] == dict.fromkeys(THREE) == item["variacao_percentual"]
    assert plain["dominios"]["distancia_km"] is None and plain["dominios"]["variacao_densidade"] is None
    assert plain["dominios"]["densidade"] == [density(MANAUS, "202406")] * 2


def test_values_are_the_density_analysis_values_of_the_same_competencia(repo):
    info = inspection()
    ids = [MANAUS, TEFE, PARINTINS, BELEM]
    body = ok(post(info, competencia="202406", base={"municipios": {"ids": ids}}))
    analysis = ok(analyze(info, "density", {"municipios": {"ids": ids}}, period_filter="202406"))
    rows = {row["Território"]: row for row in analysis["rows"]}
    assert len(rows) == len(body["itens"]) == 4
    for item in body["itens"]:
        code = item["id"][5:]
        row = rows[UNITS[code][0] + " [" + code + "]"]
        assert (item["populacao"], item["quantidade"], item["densidade"]) == (
            row["População"], row["Quantidade"], row["Densidade por 1.000"])
        assert item["densidade"] == density(item["id"], "202406")
        assert (item["rotulo"], item["uf"]) == (UNITS[code][0] + " (" + UNITS[code][1] + ")", UNITS[code][1])
        assert item["avaliavel"]["densidade"] is True and item["motivos"] == []
    assert any("Densidade = quantitativo / população × 1.000" in note for note in body["notas"])


def test_all_municipalities_keep_the_ones_without_record_apart(repo):
    info = inspection()
    body = ok(post(info, competencia="202006", base={"municipios": {"todos": True}}))
    items = by_id(body)
    assert list(items) == sorted("code:" + code for code in UNITS)
    novo = items[NOVO]
    assert (novo["populacao"], novo["quantidade"], novo["densidade"]) == (None, None, None)
    assert novo["avaliavel"]["densidade"] is False
    assert any("SEM_REGISTRO_OBSERVADO" in text for text in novo["motivos"])
    assert "UNIDADES_NAO_AVALIAVEIS" in body["limitacoes"]
    assert any(note.startswith("Municípios base (junho de 2020): 5 de 6 com registro") for note in body["notas"])
    # O ausente não vira zero: o mínimo é o zero observado de TEFE, e o máximo, MANAUS.
    assert body["dominios"]["densidade"] == [0, density(MANAUS, "202006")]


def test_a_set_is_one_bubble_with_the_aggregation_values(repo):
    info = inspection()
    members = [MANAUS, PARINTINS]
    body = ok(post(info, competencia="202406",
                   conjuntos=[{"id": "c1", "rotulo": "Manaus e Parintins", "membros": members}]))
    [item] = body["itens"]
    assert (item["id"], item["tipo"], item["rotulo"], item["membros"]) == ("c1", "conjunto", "Manaus e Parintins", members)
    assert item["contagem"] == "SOMA_DOS_COMPONENTES" and item["referencia"] is False
    assert (item["quantidade"], item["populacao"]) == (50 + 12, 2200 + 1200)
    [row] = ok(analyze(info, "aggregate", {"municipios": {"ids": members}}, period_filter="202406"))["rows"]
    assert row["Tipo"] == "Soma dos componentes (possível dupla contagem)"
    assert (item["quantidade"], item["populacao"], item["densidade"]) == (
        row["Quantidade"], row["População"], row["Densidade por 1.000"])
    assert item["densidade"] == 62 / 3400 * 1000
    assert item["avaliavel"] == {"densidade": True, "distancia": None, "variacao": None} and item["motivos"] == []
    assert "SOMA_COM_POSSIVEL_DUPLA_CONTAGEM" in body["limitacoes"]
    assert any("possível dupla contagem" in note for note in body["notas"])
    # Membro sem registro na competência: agregado parcial sobre os demais, nunca zero no lugar dele (CAP-AGR-01).
    partial = ok(post(info, competencia="202006",
                      conjuntos=[{"id": "c2", "rotulo": "Tefé e Novo Airão", "membros": [TEFE, NOVO]}]))
    [item] = partial["itens"]
    assert (item["quantidade"], item["populacao"], item["densidade"]) == (0, 600, 0)
    assert any("(AGREGADO_PARCIAL)" in text and "NOVO AIRAO (AM)" in text for text in item["motivos"])
    assert "AGREGADO_PARCIAL" in partial["limitacoes"]


def test_distance_to_a_reference_municipality_and_to_the_nearest_member_of_a_reference_set(repo):
    info = inspection()
    base = {"municipios": {"ids": [MANAUS, TEFE, MANACAPURU]}}
    single = ok(post(info, competencia="202406", base=base, referencia={"membros": [BELEM]}))
    items = by_id(single)
    assert list(items) == [MANACAPURU, MANAUS, TEFE, BELEM]
    assert items[MANAUS]["distancia_km"] == km(MANAUS, BELEM) and items[TEFE]["distancia_km"] == km(TEFE, BELEM)
    assert items[BELEM]["distancia_km"] == 0 and items[BELEM]["referencia"] is True
    assert items[MANAUS]["referencia"] is False and items[MANAUS]["avaliavel"]["distancia"] is True
    gap = items[MANACAPURU]
    assert gap["distancia_km"] is None and gap["avaliavel"]["distancia"] is False and gap["densidade"] == 8
    assert any("SEM_INFORMACAO_ESPACIAL" in text for text in gap["motivos"])
    assert single["referencia"]["tipo"] == "municipio" and "DISTANCIA_GEODESICA_DIRETA" in single["limitacoes"]
    assert any("geográfica direta" in note for note in single["notas"])
    assert single["dominios"]["distancia_km"] == [0, km(TEFE, BELEM)]
    nearest = nearest_units(info, [BELEM])
    for key in (MANAUS, TEFE):
        assert items[key]["distancia_km"] == nearest[key]["minimo_completo"]["distancia_km"]
    # Conjunto de referência: distância até o membro mais próximo (mínimo do conjunto completo, CAP-ESP-02).
    pair = ok(post(info, competencia="202406", base=base, referencia={"membros": [BELEM, PARINTINS]}))
    items = by_id(pair)
    assert pair["referencia"]["tipo"] == "conjunto"
    assert items[MANAUS]["distancia_km"] == min(km(MANAUS, BELEM), km(MANAUS, PARINTINS)) == km(MANAUS, PARINTINS)
    assert items[PARINTINS]["referencia"] is True and items[PARINTINS]["distancia_km"] == 0
    nearest = nearest_units(info, [BELEM, PARINTINS])
    for key in (MANAUS, TEFE):
        assert items[key]["distancia_km"] == nearest[key]["minimo_completo"]["distancia_km"]
    # Referência sem coordenada: o mínimo do conjunto completo não é avaliável para ninguém (como em compute_nearest).
    broken = ok(post(info, competencia="202406", base=base, referencia={"membros": [BELEM, MANACAPURU]}))
    assert all(item["distancia_km"] is None and item["avaliavel"]["distancia"] is False for item in broken["itens"])
    assert any("DEPENDENCIA_NAO_AVALIAVEL" in text for text in by_id(broken)[MANAUS]["motivos"])
    assert broken["dominios"]["distancia_km"] is None and "DISTANCIA_GEODESICA_DIRETA" not in broken["limitacoes"]
    assert nearest_units(info, [BELEM, MANACAPURU])[MANAUS]["minimo_completo"]["avaliabilidade"] == "NAO_AVALIAVEL"


def test_a_set_gets_the_nearest_and_the_farthest_member_distance(repo):
    info = inspection()
    body = ok(post(info, competencia="202406", referencia={"membros": [BELEM]},
                   conjuntos=[{"id": "c1", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]},
                              {"id": "c3", "rotulo": "Manaus e Manacapuru", "membros": [MANAUS, MANACAPURU]}]))
    items = by_id(body)
    assert list(items) == [BELEM, "c1", "c3"]  # a referência entra como item, com distância zero
    c1, c3 = items["c1"], items["c3"]
    assert (c1["distancia_km"], c1["distancia_km_max"]) == (km(PARINTINS, BELEM), km(MANAUS, BELEM))
    assert c1["avaliavel"]["distancia"] is True
    assert c3["distancia_km"] is None and c3["distancia_km_max"] is None and c3["avaliavel"]["distancia"] is False
    assert any("MANACAPURU (AM)" in text and "DEPENDENCIA_NAO_AVALIAVEL" in text for text in c3["motivos"])
    assert (c3["quantidade"], c3["populacao"]) == (8 + 50, 1000 + 2200)  # os valores do conjunto continuam avaliáveis
    assert body["dominios"]["distancia_km"] == [0, km(MANAUS, BELEM)]
    # O conjunto com os mesmos membros da referência é a bolha da referência.
    both = ok(post(info, competencia="202406", referencia={"membros": [MANAUS, PARINTINS]},
                   conjuntos=[{"id": "ref", "rotulo": "Referência", "membros": [PARINTINS, MANAUS]}]))
    reference = by_id(both)["ref"]
    assert reference["referencia"] is True and reference["distancia_km"] == 0 == reference["distancia_km_max"]


def test_percentage_change_uses_exact_arithmetic_and_keeps_base_zero_apart(repo):
    info = inspection()
    body = ok(post(info, competencia="202406", competencia_inicial="202006",
                   base={"municipios": {"ids": [MANAUS, TEFE, NOVO]}},
                   conjuntos=[{"id": "c1", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]},
                              {"id": "c2", "rotulo": "Tefé e Novo Airão", "membros": [TEFE, NOVO]}]))
    items = by_id(body)
    manaus = items[MANAUS]
    assert manaus["inicial"] == {"populacao": 2000, "quantidade": 40, "densidade": 20}
    assert manaus["variacao_percentual"] == {"populacao": percent(2000, 2200), "quantidade": percent(40, 50),
                                             "densidade": percent(Fraction(40 * 1000, 2000), Fraction(50 * 1000, 2200))}
    assert manaus["variacao_percentual"]["densidade"] == float(Fraction(150, 11))
    assert manaus["avaliavel"]["variacao"] is True and manaus["motivos"] == []
    # Base zero (CAP-TMP-01, DA-14): percentual não avaliável, com o motivo; a população segue avaliável.
    tefe = items[TEFE]
    assert tefe["inicial"] == {"populacao": 600, "quantidade": 0, "densidade": 0}
    assert tefe["variacao_percentual"] == {"populacao": 0, "quantidade": None, "densidade": None}
    assert tefe["avaliavel"]["variacao"] is False and tefe["avaliavel"]["densidade"] is True
    assert any("BASE_ZERO" in text for text in tefe["motivos"])
    novo = items[NOVO]
    assert novo["inicial"] == dict.fromkeys(THREE) == novo["variacao_percentual"] and novo["densidade"] == 8
    assert novo["avaliavel"]["variacao"] is False
    assert any("SEM_REGISTRO_OBSERVADO" in text for text in novo["motivos"])
    c1 = items["c1"]
    assert c1["inicial"] == {"populacao": 3000, "quantidade": 50, "densidade": 50 / 3000 * 1000}
    assert c1["variacao_percentual"] == {"populacao": percent(3000, 3400), "quantidade": percent(50, 62),
                                         "densidade": percent(Fraction(50 * 1000, 3000), Fraction(62 * 1000, 3400))}
    assert c1["variacao_percentual"]["densidade"] == float(Fraction(160, 17))
    # Membros efetivos diferentes entre as competências: sem variação (INCOMPARABILIDADE); cada valor vale isolado.
    c2 = items["c2"]
    assert c2["variacao_percentual"] == dict.fromkeys(THREE) and c2["avaliavel"]["variacao"] is False
    assert c2["inicial"] == {"populacao": 600, "quantidade": 0, "densidade": 0}
    assert (c2["quantidade"], c2["populacao"]) == (6 + 4, 600 + 500)
    assert any("(INCOMPARABILIDADE)" in text for text in c2["motivos"])
    assert body["dominios"]["variacao_densidade"] == [float(Fraction(160, 17)), float(Fraction(150, 11))]
    assert any("CAP-TMP-01" in note for note in body["notas"])


def test_reference_candidates_follow_the_engine_order_with_shared_positions(repo):
    info = inspection()
    ids = [MANACAPURU, TEFE, MANAUS, PARINTINS]
    body = ok(post(info, "/api/painel/referencias", competencia="202406", categoria="MEDICINA",
                   universo={"municipios": {"ids": ids}}, criterio={"atributo": "densidade", "ordem": "desc"}))
    assert set(body) == {"criterio", "competencia", "categoria", "candidatos", "nao_avaliaveis"}
    assert (body["criterio"], body["competencia"]) == ({"atributo": "densidade", "ordem": "desc"}, "202406")
    assert all(set(item) == {"id", "rotulo", "uf", "valor", "posicao"} for item in body["candidatos"])
    # CAP-SUB-02: empates na mesma posição (1, 2, 2, 4), sem desempate artificial.
    assert [(item["id"], item["posicao"]) for item in body["candidatos"]] == [
        (MANAUS, 1), (PARINTINS, 2), (TEFE, 2), (MANACAPURU, 4)]
    assert [item["valor"] for item in body["candidatos"]] == [density(MANAUS, "202406"), 10, 10, 8]
    assert body["candidatos"][0]["rotulo"] == "MANAUS (AM)" and body["nao_avaliaveis"] == []
    asc = ok(post(info, "/api/painel/referencias", competencia="202406", universo={"municipios": {"ids": ids}},
                  criterio={"atributo": "densidade", "ordem": "asc"}))
    assert [(item["id"], item["posicao"]) for item in asc["candidatos"]] == [
        (MANACAPURU, 1), (PARINTINS, 2), (TEFE, 2), (MANAUS, 4)]
    state = ok(post(info, "/api/painel/referencias", competencia="202406", universo={"municipios": {"estados": ["13"]}},
                    criterio={"atributo": "densidade", "ordem": "desc"}))
    assert [item["posicao"] for item in state["candidatos"]] == [1, 2, 2, 4, 4]
    assert BELEM not in {item["id"] for item in state["candidatos"]}
    # Não avaliáveis numa lista separada, sem posição.
    early = ok(post(info, "/api/painel/referencias", competencia="202006", universo={"municipios": {"estados": ["13"]}},
                    criterio={"atributo": "quantidade", "ordem": "desc"}))
    assert [(item["id"], item["posicao"]) for item in early["candidatos"]] == [
        (MANAUS, 1), (PARINTINS, 2), (MANACAPURU, 3), (TEFE, 4)]
    [gap] = early["nao_avaliaveis"]
    assert set(gap) == {"id", "rotulo", "uf", "motivos"} and gap["id"] == NOVO
    assert any("SEM_REGISTRO_OBSERVADO" in text for text in gap["motivos"])
    # A origem da referência registra a posição recalculada pelo motor (CAP-REF-01 e CAP-SUB-02).
    chosen = ok(post(info, competencia="202406", base={"municipios": {"estados": ["13"]}},
                     referencia={"membros": [MANAUS], "criterio": {"atributo": "densidade", "ordem": "desc"}}))
    assert chosen["referencia"]["origem"].startswith("Escolhida pelo critério densidade (maior para menor), 1ª posição")
    tied = ok(post(info, competencia="202406", base={"municipios": {"ids": [MANAUS]}},
                   referencia={"membros": [TEFE], "criterio": {"atributo": "densidade", "ordem": "desc",
                                                               "universo": {"municipios": {"ids": ids}}}}))
    assert "2ª posição no universo da ordenação (4 municípios)" in tied["referencia"]["origem"]
    listed = ok(post(info, competencia="202406", base={"municipios": {"ids": [MANAUS]}}, referencia={"membros": [TEFE]}))
    assert listed["referencia"]["origem"].startswith("Escolhida por você (lista explícita)")


def test_invalid_requests_are_refused_in_portuguese(repo):
    info = inspection()
    base = {"municipios": {"ids": [MANAUS]}}
    stale = {**info, "source": {**info["source"], "version": "0" * 64}}
    refused(post(stale, competencia="202406", base=base), "atualizada")
    refused(post(info, competencia="209912", base=base), "Competência inexistente")
    refused(post(info, competencia="202006", competencia_inicial="202406", base=base), "anterior")
    refused(post(info, competencia="202406", competencia_inicial="202406", base=base), "anterior")
    refused(post(info, competencia="202406", competencia_inicial="201901", base=base), "Competência inexistente")
    refused(post(info, competencia="202406", categoria="ENFERMAGEM", base=base), "Categoria profissional inexistente")
    refused(post(info, competencia="202406", base={"municipios": {"ids": ["code:999999"]}}), "inexistentes")
    refused(post(info, competencia="202406", base=base, referencia={"membros": ["code:999999"]}), "inexistentes")
    refused(post(info, competencia="202406", conjuntos=[{"id": "c1", "rotulo": "Vazio", "membros": []}]),
            "sem membros")
    refused(post(info, competencia="202406", conjuntos=[{"id": "c1", "rotulo": "Um só", "membros": [MANAUS]}]),
            "pelo menos dois")
    refused(post(info, competencia="202406", conjuntos=[{"id": "c1", "rotulo": "x", "membros": [MANAUS, "code:999999"]}]),
            "inexistentes")
    refused(post(info, competencia="202406"), "Escolha os municípios base")
    refused(post(info, competencia="202406", base=base, indicador="densidade"), "não reconhecido")
    refused(post(info, "/api/painel/referencias", competencia="202406", universo=base,
                 criterio={"atributo": "renda", "ordem": "desc"}), "Atributo do critério")
    refused(post(info, "/api/painel/referencias", competencia="202406", universo=base), "Escolha o critério")
    upload = client.post("/api/painel", files={"file": ("base.csv", b"municipio;quantidade\nA;1\n")},
                         data={"options": json.dumps({"competencia": "202406"})})
    refused(upload, "base Brasil oficial")


def test_the_panel_never_calls_the_ai_provider(repo, monkeypatch):
    calls = []

    async def forbidden(*args):
        calls.append(args)
        raise AssertionError("O painel não chama o provedor de IA.")

    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    before = client.get("/api/llm/status").json()["requests_used_today"]
    info = inspection()
    token = client.post("/api/session").json()["token"]
    try:
        ok(post(info, headers={"X-ADT-Session": token}, **{**FULL, "base": {"municipios": {"todos": True}}}))
        ok(post(info, "/api/painel/referencias", competencia="202406", universo={"municipios": {"todos": True}},
                criterio={"atributo": "populacao", "ordem": "desc"}))
        assert client.get("/api/session", headers={"X-ADT-Session": token}).status_code == 200
    finally:
        client.post("/api/session/close", headers={"X-ADT-Session": token})
    assert calls == [] and client.get("/api/llm/status").json()["requests_used_today"] == before


# --------------------------------------------------------------------------------------------- base versionada
AM3 = ["code:130260", "code:130420", "code:130340"]


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    catalog = tmp_path_factory.mktemp("painel-real") / "brasil"
    install(Path(folder), catalog)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(catalog))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        main._BRAZIL_FRAMES.clear()
        yield inspection()
        main._BRAZIL_FRAMES.clear()
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_real_panel_values_match_the_engine_analyses_for_three_am_municipalities(real):
    body = ok(post(real, competencia="202406", competencia_inicial="202306", base={"municipios": {"ids": AM3}},
                   conjuntos=[{"id": "am3", "rotulo": "Manaus, Tefé e Parintins", "membros": AM3}],
                   referencia={"membros": [AM3[0]]}))
    items = by_id(body)
    analysis = ok(analyze(real, "density", {"municipios": {"ids": AM3}}, period_filter="202406"))
    rows = {row["Território"].rsplit(" [", 1)[1].rstrip("]"): row for row in analysis["rows"]}
    for key, value in zip(AM3, (2.0748, 0.8704, 1.1574)):
        item, row = items[key], rows[key[5:]]
        assert (item["populacao"], item["quantidade"], item["densidade"]) == (
            row["População"], row["Quantidade"], row["Densidade por 1.000"])
        assert round(item["densidade"], 4) == value
        assert item["avaliavel"] == {"densidade": True, "distancia": True, "variacao": True}
    [row] = ok(analyze(real, "aggregate", {"municipios": {"ids": AM3}}, period_filter="202406"))["rows"]
    group = items["am3"]
    assert (group["quantidade"], group["populacao"], group["densidade"]) == (
        row["Quantidade"], row["População"], row["Densidade por 1.000"])
    nearest = ok(analyze(real, "nearest", period_filter="202406", reference_mode="list", reference_ids=[AM3[0]],
                         crs="SIRGAS2000", number_format="decimal_comma", category_filter="MEDICINA"))
    records = {record["unidade"]: record for record in nearest["metadata"]["nearest_reference"]["cobertura_referencias"]}
    for key in AM3[1:]:
        assert items[key]["distancia_km"] == records[key]["minimo_completo"]["distancia_km"]
    assert items[AM3[0]]["distancia_km"] == 0 and items[AM3[0]]["referencia"] is True


def test_real_panel_with_all_municipalities(real):
    folder = Path(os.environ["ADT_REAL_DATA_DIR"])
    codes = pd.read_csv(folder / FILES["municipal"], sep=";", encoding="utf-8-sig", dtype=str,
                        usecols=["cod_ibge"])["cod_ibge"].str.strip().unique()
    body = ok(post(real, competencia="202406", competencia_inicial="202306", base={"municipios": {"todos": True}},
                   referencia={"membros": [AM3[0]], "criterio": {"atributo": "densidade", "ordem": "desc"}}))
    units = [item for item in body["itens"] if item["tipo"] == "municipio"]
    assert [item["id"] for item in units] == sorted("code:" + code for code in codes)
    assert all(set(item) == UNIT for item in units)
    low, high = body["dominios"]["densidade"]
    assert low <= round(by_id(body)[AM3[0]]["densidade"], 4) == 2.0748 <= high
    assert body["referencia"]["origem"].startswith("Escolhida pelo critério densidade (maior para menor), ")
    json.dumps(body, allow_nan=False)
