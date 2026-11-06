"""Mapa da página única: POST /api/painel/mapa (Docs/PAINEL_INTEGRADO.md, "Rota 3: POST /api/painel/mapa").

As coordenadas são as autorizadas que a análise espacial já usa para medir as distâncias (territory_coordinates, com a
camada complementar na base do Brasil), uma por unidade do catálogo da fonte na competência: ponto válido em `pontos` ou,
sem ele, a unidade em `sem_coordenada`, com o motivo. Os ids são os dos itens de POST /api/painel. Nada é registrado na
sessão e nada vai ao provedor de IA.

Catálogo sintético e planilha de distritos de test_painel_pagina.py (MANACAPURU sem coordenadas; NOVO AIRAO só a partir
de 2022; o distrito Serra sem coordenadas). O caso com a base versionada roda no job dados-reais (ADT_REAL_DATA_DIR),
somente em leitura.
"""
import csv
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import llm_bridge
import main
from conversation_session import sessions
from nearest_reference import GEOD, GEODS
from test_painel_pagina import (ALTO, BAIXO, BELEM, CAMPINA, DISTRICT_MAPPING, LABELS, MANACAPURU, MANAUS, NOVO,
                                PARINTINS, SERRA, TEFE, UNITS, inspection, ok, page, post, refused, upload)
from test_painel_pagina import real, repo  # noqa: F401 (fixtures)

client = TestClient(main.app)
KEYS = {"competencia", "referencial", "pontos", "sem_coordenada"}


def mapa(info, headers=None, **options):
    return post(info, path="/api/painel/mapa", headers=headers, **options)


def coordinate(code):
    lat, lon = UNITS[code][2]
    return float(lat.replace(",", ".")), float(lon.replace(",", "."))


def test_map_has_every_unit_of_the_catalog_with_the_authorized_point_or_the_reason(repo):
    info = inspection()
    body = ok(mapa(info, competencia="202406"))
    assert set(body) == KEYS
    assert (body["competencia"], body["referencial"]) == ("202406", "SIRGAS2000")
    # Na ordem do código, todas as unidades do catálogo: pontos válidos e, à parte, quem não tem coordenada.
    assert [point["id"] for point in body["pontos"]] == [MANAUS, PARINTINS, NOVO, TEFE, BELEM]
    assert body["sem_coordenada"] == [{"id": MANACAPURU, "rotulo": "MANACAPURU (AM)", "motivo": (
        "Sem coordenada válida em junho de 2024: coordenadas ausentes (SEM_INFORMACAO_ESPACIAL)")}]
    for point in body["pontos"]:
        assert set(point) == {"id", "lat", "lon"}
        assert (point["lat"], point["lon"]) == coordinate(point["id"][5:])
    # Os ids são os dos itens do gráfico.
    items = ok(page(info, base={"municipios": {"todos": True}}))["itens"]
    assert {item["id"] for item in items} == {point["id"] for point in body["pontos"]} | {MANACAPURU}
    # Coordenadas da competência: NOVO AIRAO não tem registro em 2020 e fica fora, com o motivo.
    early = ok(mapa(info, competencia="202006"))
    assert [entry["id"] for entry in early["sem_coordenada"]] == [MANACAPURU, NOVO]
    assert early["sem_coordenada"][1]["motivo"] == ("Sem coordenada válida em junho de 2020: sem registro no período "
                                                    "(SEM_REGISTRO_OBSERVADO)")


def test_map_points_are_the_coordinates_of_the_distances(repo):
    info = inspection()
    points = {point["id"]: (point["lat"], point["lon"]) for point in ok(mapa(info, competencia="202406"))["pontos"]}
    items = {item["id"]: item for item in ok(page(info, referencia={"membros": [PARINTINS]}))["itens"]}
    for key in (MANAUS, NOVO, TEFE):
        (lat_a, lon_a), (lat_b, lon_b) = points[key], points[PARINTINS]
        assert items[key]["distancia_km"] == GEOD.inv(lon_a, lat_a, lon_b, lat_b)[2] / 1000
    assert items[MANACAPURU]["distancia_km"] is None and MANACAPURU not in points


def test_map_requests_are_strict_read_only_and_never_reach_the_provider(repo, monkeypatch):
    calls = []

    async def forbidden(*args):
        calls.append(args)
        raise AssertionError("O mapa não chama o provedor de IA.")

    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    info = inspection()
    token = client.post("/api/session").json()["token"]
    headers = {"X-ADT-Session": token}
    try:
        assert ok(mapa(info, headers=headers, competencia="202406", categoria="MEDICINA"))["pontos"]
        assert sessions.sessions[token].results == {}  # nada registrado na sessão
    finally:
        client.post("/api/session/close", headers=headers)
    assert calls == []
    refused(mapa(info, competencia="202406", nivel="municipios"), "Parâmetro não reconhecido no painel: nivel")
    refused(mapa(info, competencia="209912"), "Competência inexistente")
    refused(mapa(info), "Escolha a competência do painel")
    refused(mapa(info, competencia="202406", premissas={"crs": "WGS84"}), "as premissas vêm do perfil oficial")
    refused(mapa(info, competencia="202406", rotulos=LABELS), "rótulos são fixos")


def test_map_state_draw_points_are_the_mean_of_the_valid_seats(repo):
    """Vendo por estado (06/11/2026, item 3.2 do comando; divergência aprovada da RQ-REP-07, só para a bolha no centro): com
    `grupos`, o ponto de desenho de cada estado é a média das latitudes e a das longitudes das sedes válidas dos seus municípios na
    competência, com o método e a nota; as sedes não mudam, e sem `grupos` a resposta é a de sempre. Numa planilha, recusado."""
    info = inspection()
    body = ok(mapa(info, competencia="202406", grupos=True))
    assert set(body) == KEYS | {"grupos", "metodo_grupos", "nota_grupos"}
    assert body["metodo_grupos"] == "CENTRO-DE-DESENHO-1" and "só para desenhar" in body["nota_grupos"]
    seats = [coordinate(key[5:]) for key in (MANAUS, PARINTINS, NOVO, TEFE)]  # MANACAPURU sem coordenada fica de fora
    expected = {"uf:13": (sum(lat for lat, _ in seats) / 4, sum(lon for _, lon in seats) / 4, 4),
                "uf:15": (*coordinate(BELEM[5:]), 1)}
    assert [(grupo["id"], grupo["rotulo"]) for grupo in body["grupos"]] == [("uf:13", "Amazonas (AM)"), ("uf:15", "Pará (PA)")]
    for grupo in body["grupos"]:
        lat, lon, units = expected[grupo["id"]]
        assert (grupo["lat"], grupo["lon"], grupo["unidades"]) == (pytest.approx(lat), pytest.approx(lon), units)
    plain = ok(mapa(info, competencia="202406"))
    assert set(plain) == KEYS and plain["pontos"] == body["pontos"]
    assert set(ok(mapa(info, competencia="202406", grupos=False))) == KEYS
    refused(mapa(info, competencia="202406", grupos="sim"), "Grupos do mapa inválidos")
    refused(upload({"competencia": "2024", "rotulos": LABELS, "premissas": {"count_unit": "pessoas", "crs": "SIRGAS2000"},
                    "grupos": True}, path="/api/painel/mapa"), "existem só na base do Brasil")


def test_uploaded_map_uses_the_spreadsheet_coordinates_in_the_confirmed_reference(repo):
    options = {"competencia": "2024", "rotulos": LABELS, "premissas": {"count_unit": "pessoas", "crs": "SIRGAS2000"}}
    body = ok(upload(options, path="/api/painel/mapa"))
    assert body["referencial"] == "SIRGAS2000"
    assert body["pontos"] == [{"id": ALTO, "lat": -3.1, "lon": -60.0}, {"id": BAIXO, "lat": -3.5, "lon": -61.0},
                              {"id": CAMPINA, "lat": -8.0, "lon": -55.0}]
    assert body["sem_coordenada"] == [{"id": SERRA, "rotulo": "Serra", "motivo": (
        "Sem coordenada válida em 2024: coordenadas ausentes (SEM_INFORMACAO_ESPACIAL)")}]
    # WGS 84 aceito (Adendo REF-20261022), cada um no seu referencial, sem converter as coordenadas.
    wgs84 = ok(upload({**options, "premissas": {"count_unit": "pessoas", "crs": "WGS 84"}}, path="/api/painel/mapa"))
    assert wgs84["referencial"] == "WGS84" and wgs84["pontos"] == body["pontos"]
    distances = {item["id"]: item["distancia_km"] for item in ok(upload(
        {"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "rotulos": LABELS,
         "premissas": {"count_unit": "pessoas", "crs": "WGS84"}, "base": {"municipios": {"todos": True}},
         "referencia": {"membros": [ALTO]}}))["itens"]}
    lon_a, lat_a = -61.0, -3.5
    assert distances[BAIXO] == GEODS["WGS84"].inv(lon_a, lat_a, -60.0, -3.1)[2] / 1000
    # Sem o referencial: a mesma pendência da análise espacial; referencial fora dos aceitos: recusado, sem presumir.
    pending = refused(upload({**options, "premissas": {"count_unit": "pessoas"}}, path="/api/painel/mapa"),
                      "Confirme o referencial geodésico")
    assert pending["pendencia"]["chave"] == "crs" and pending["pendencia"]["opcoes"] == ["SIRGAS2000", "WGS84"]
    refused(upload({**options, "premissas": {"count_unit": "pessoas", "crs": "SAD69"}}, path="/api/painel/mapa"),
            "Referencial geodésico informado não suportado")


def test_uploaded_map_without_coordinate_columns_is_refused_with_the_reason(repo):
    mapping = {key: value for key, value in DISTRICT_MAPPING.items() if key not in ("latitude", "longitude")}
    refused(upload({"competencia": "2024", "premissas": {"count_unit": "pessoas"}}, mapping=mapping,
                   path="/api/painel/mapa"),
            "A planilha não tem colunas de latitude e longitude associadas: o mapa precisa delas.")


# --------------------------------------------------------------------------------------------- base versionada
def test_real_map_covers_the_municipalities_of_the_competence_inside_brazil(real):
    body = ok(mapa(real, competencia="202406"))
    folder = Path(os.environ["ADT_BRASIL_DATA_DIR"])
    with open(folder / "Dados_Municipios_Brasil.csv", encoding="utf-8-sig", newline="") as handle:
        expected = {"code:" + row["cod_ibge"].strip() for row in csv.DictReader(handle, delimiter=";")
                    if row["periodo_ano"].strip() == "2024" and row["periodo_mes"].strip() == "6"}
    ids = [point["id"] for point in body["pontos"]] + [entry["id"] for entry in body["sem_coordenada"]]
    assert len(ids) == len(set(ids)) and set(ids) == expected and len(expected) == 5570
    assert body["referencial"] == "SIRGAS2000"
    # O Brasil com as ilhas oceânicas: a sede de Fernando de Noronha (PE) fica a 32,4° W, a leste do continente (34,8° W).
    fora = [point for point in body["pontos"] if not (-34 <= point["lat"] <= 6 and -74 <= point["lon"] <= -28)]
    assert not fora, fora[:5]
    points = {point["id"]: (point["lat"], point["lon"]) for point in body["pontos"]}
    assert points["code:130260"] == (-3.134691491, -60.02333518)  # MANAUS, sede municipal da fonte
    assert points["code:260545"] == (-3.852021401, -32.43518633)  # FERNANDO DE NORONHA, ilha oceânica, como na fonte
    assert points["code:170100"] == (-6.374096, -48.07024)  # ANANAS, pela camada complementar governada
    items = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406",
                    base={"municipios": {"todos": True}}))["itens"]
    assert {item["id"] for item in items} == set(ids)
    # Os 27 estados no ponto de desenho (06/11/2026): a média das sedes válidas de cada um, dentro do Brasil.
    grupos = ok(mapa(real, competencia="202406", grupos=True))["grupos"]
    assert len(grupos) == 27 and sum(grupo["unidades"] for grupo in grupos) == len(body["pontos"])
    para = next(grupo for grupo in grupos if grupo["id"] == "uf:15")
    seats = [point for point in body["pontos"] if point["id"].startswith("code:15")]
    assert para["unidades"] == len(seats) == 144
    assert para["lat"] == pytest.approx(sum(point["lat"] for point in seats) / 144)
    assert para["lon"] == pytest.approx(sum(point["lon"] for point in seats) / 144)
