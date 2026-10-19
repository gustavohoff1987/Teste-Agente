"""Construtor da camada geográfica complementar: associação única da sede, referencial comprovado e recusas.

Arquivos sintéticos no formato de uma base de localidades (nomes de campos e coordenadas fictícios,
não oficiais), gerados em tempo de teste; nenhum arquivo oficial é lido e nada é gravado no repositório.
"""
import hashlib
import json
import sqlite3
import struct
from argparse import Namespace

import pytest
from openpyxl import Workbook

import brazil_data
import build_geo_complement as builder
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from geo_complement import AUTHORIZED, LAYER, state

ACCENTED = {"170100": "Ananás", "421265": "Pescaria Brava", "422000": "Balneário Rincão", "500490": "Jaraguari",
            "430367": "Campestre da Serra", "350050": "Águas de Lindóia"}
POINTS = {"170100": (-6.4, -48.1), "421265": (-28.4, -48.9), "422000": (-28.8, -49.2),
          "500490": (-20.1, -54.4), "430367": (-28.8, -51.1), "350050": (-22.5, -46.6)}
HEADER = ["CD_MUN", "NM_MUN", "SIGLA_UF", "NM_CATEGORIA", "NM_LOCALIDADE", "LAT", "LONG"]
URL = "https://geoftp.ibge.gov.br/organizacao_do_territorio/teste/localidades_sinteticas"


def records(skip=(), duplicate=(), wrong_uf=(), blank=()):
    rows = []
    for code, name in ACCENTED.items():
        lat, lon = POINTS[code]
        uf = AUTHORIZED[code][1]
        if code not in skip:
            rows.append([code + "0", name, "GO" if code in wrong_uf else uf, "CIDADE", name,
                         "" if code in blank else lat, "" if code in blank else lon])
        if code in duplicate:
            rows.append([code + "0", name, uf, "CIDADE", name + " (2)", lat + 0.01, lon])
        rows.append([code + "0", name, uf, "VILA", "Vila de " + name, lat + 0.2, lon + 0.2])  # não é sede
        rows.append([code + "00", name, uf, "CIDADE", name, lat + 0.3, lon])  # código de 8 dígitos: nunca associado
    rows.append(["1721000", "Palmas", "TO", "CIDADE", "Palmas", -10.2, -48.3])  # não autorizado
    return rows


def write_csv(path, rows, decimal=","):
    def cell(value):
        return str(value).replace(".", decimal) if isinstance(value, float) else str(value)
    path.write_text("\n".join(";".join(cell(v) for v in row) for row in [HEADER] + rows) + "\n", encoding="utf-8")
    return path


def gp_point(lon, lat, srs_id, envelope=False):
    flags = 0b1 | (0b10 if envelope else 0)  # little-endian; envelope XY opcional
    header = b"GP" + bytes([0, flags]) + struct.pack("<i", srs_id)
    if envelope:
        header += struct.pack("<4d", lon, lon, lat, lat)
    return header + struct.pack("<BIdd", 1, 1, lon, lat)


def write_gpkg(path, rows, layer_srs=4674, srs_table=((4674, "EPSG", 4674),), geometry_srs=None):
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE gpkg_spatial_ref_sys (srs_name TEXT, srs_id INTEGER PRIMARY KEY, organization TEXT, "
                   "organization_coordsys_id INTEGER, definition TEXT, description TEXT)")
        db.executemany("INSERT INTO gpkg_spatial_ref_sys VALUES ('teste', ?, ?, ?, 'teste', NULL)", srs_table)
        db.execute("CREATE TABLE gpkg_contents (table_name TEXT PRIMARY KEY, data_type TEXT, identifier TEXT, srs_id INTEGER)")
        db.execute("INSERT INTO gpkg_contents VALUES ('localidades', 'features', 'localidades', ?)", (layer_srs,))
        db.execute("CREATE TABLE gpkg_geometry_columns (table_name TEXT, column_name TEXT, geometry_type_name TEXT, "
                   "srs_id INTEGER, z TINYINT, m TINYINT)")
        db.execute("INSERT INTO gpkg_geometry_columns VALUES ('localidades', 'geom', 'POINT', ?, 0, 0)", (layer_srs,))
        db.execute("CREATE TABLE localidades (fid INTEGER PRIMARY KEY, geom BLOB, CD_MUN TEXT, NM_MUN TEXT, SIGLA_UF TEXT, "
                   "NM_CATEGORIA TEXT, NM_LOCALIDADE TEXT)")
        for index, (code, name, uf, category, place, lat, lon) in enumerate(rows):
            srs = geometry_srs(code) if geometry_srs else layer_srs
            db.execute("INSERT INTO localidades VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (index + 1, gp_point(lon, lat, srs, envelope=index % 2 == 0), code, name, uf, category, place))
    return path


def arguments(source, **changes):
    values = {"fonte": str(source), "url": URL, "edicao": "teste", "campo_codigo": "CD_MUN", "campo_nome": "NM_MUN",
              "campo_uf": "SIGLA_UF", "campo_categoria": "NM_CATEGORIA", "valor_sede": "CIDADE", "camada": None,
              "campos_extras": "NM_LOCALIDADE", "campo_lat": None, "campo_lon": None, "referencial": None,
              "evidencia_referencial": None, "codificacao": "utf-8-sig", "versao": "1", "gravar": False}
    if not str(source).endswith(".gpkg"):
        values.update(campo_lat="LAT", campo_lon="LONG", referencial="SIRGAS 2000",
                      evidencia_referencial="metadado sintético: Sistema de referência SIRGAS 2000")
    values.update(changes)
    return Namespace(**values)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "contagem"])
    book.save(root / FILES["national"])
    (root / FILES["municipal"]).write_text("municipal sintético\n", encoding="utf-8")
    (root / FILES["state"]).write_text("estadual sintético\n", encoding="utf-8")
    (root / GOVERNED_MANIFEST).parent.mkdir(parents=True)
    (root / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(root)), encoding="utf-8")
    monkeypatch.setattr(brazil_data, "REPO_ROOT", root)
    return root


def by_code(layer):
    return {item["codigo_base"]: item for item in layer["municipios"]}


def test_csv_with_unique_seats_produces_a_valid_traceable_layer(repo, tmp_path):
    source = write_csv(tmp_path / "localidades.csv", records())
    layer = builder.build(arguments(source))
    items = by_code(layer)
    assert sorted(items) == sorted(AUTHORIZED) and layer["excecoes"] == []
    for code, (lat, lon) in POINTS.items():
        assert (items[code]["latitude"], items[code]["longitude"]) == (lat, lon)  # sede, não a vila nem o código longo
        assert items[code]["codigo_ibge"] == code + "0"
        assert items[code]["registro_oficial"]["NM_LOCALIDADE"] == ACCENTED[code]
    assert layer["fonte"]["sha256_arquivo"] == hashlib.sha256(source.read_bytes()).hexdigest()
    assert layer["fonte"]["referencial"] == "SIRGAS 2000" and "SIRGAS 2000" in layer["fonte"]["evidencia_referencial"]
    assert layer["aplica_se_a"]["sha256"] == brazil_data.governed_manifest()["sha256"]["municipal"]


def test_ambiguous_missing_or_divergent_seats_become_exceptions_without_arbitrary_choice(repo, tmp_path):
    source = write_csv(tmp_path / "localidades.csv",
                       records(skip=("421265",), duplicate=("422000",), wrong_uf=("500490",), blank=("430367",)))
    layer = builder.build(arguments(source))
    reasons = {item["codigo_base"]: item["motivo"] for item in layer["excecoes"]}
    assert reasons == {"421265": "nenhum registro de sede", "422000": "mais de um registro de sede (ambíguo)",
                       "500490": "nenhum registro de sede",
                       "430367": reasons["430367"]}
    assert reasons["430367"].startswith("registro de sede sem ponto válido")
    assert sorted(by_code(layer)) == ["170100", "350050"]


def test_csv_without_crs_evidence_or_with_another_crs_is_refused(repo, tmp_path):
    source = write_csv(tmp_path / "localidades.csv", records())
    with pytest.raises(ValueError, match="evidência textual"):
        builder.build(arguments(source, evidencia_referencial=None))
    with pytest.raises(ValueError, match="referencial da fonte"):
        builder.build(arguments(source, referencial="WGS84"))
    with pytest.raises(ValueError, match="fonte fora do IBGE"):
        builder.build(arguments(source, url="https://exemplo.com/localidades.csv"))
    with pytest.raises(ValueError, match="campos inexistentes"):
        builder.build(arguments(source, campo_categoria="TIPO"))


def test_xlsx_source_is_read_with_the_same_rules(repo, tmp_path):
    book = Workbook()
    for row in [HEADER] + records():
        book.active.append(row)
    book.save(tmp_path / "localidades.xlsx")
    layer = builder.build(arguments(tmp_path / "localidades.xlsx"))
    assert {code: (i["latitude"], i["longitude"]) for code, i in by_code(layer).items()} == POINTS


def test_gpkg_point_comes_from_the_geometry_in_sirgas2000(repo, tmp_path):
    source = write_gpkg(tmp_path / "localidades.gpkg", records())
    layer = builder.build(arguments(source))
    assert {code: (i["latitude"], i["longitude"]) for code, i in by_code(layer).items()} == POINTS
    assert layer["fonte"]["evidencia_referencial"].startswith("gpkg_spatial_ref_sys: EPSG:4674")
    with pytest.raises(ValueError, match="geometria"):
        builder.build(arguments(source, campo_lat="LAT", campo_lon="LONG"))  # atributos não substituem a geometria


@pytest.mark.parametrize("variant", ["wgs84", "sem_srs", "geometria_divergente"])
def test_gpkg_without_proven_sirgas2000_is_refused_or_kept_as_exception(repo, tmp_path, variant):
    path = tmp_path / "localidades.gpkg"
    if variant == "wgs84":
        write_gpkg(path, records(), layer_srs=4326, srs_table=((4326, "EPSG", 4326),))
        with pytest.raises(ValueError, match="SIRGAS 2000"):
            builder.build(arguments(path))
    elif variant == "sem_srs":
        write_gpkg(path, records(), layer_srs=9999)
        with pytest.raises(ValueError, match="SIRGAS 2000"):
            builder.build(arguments(path))
    else:
        write_gpkg(path, records(), srs_table=((4674, "EPSG", 4674), (4326, "EPSG", 4326)),
                   geometry_srs=lambda code: 4326 if code == "1701000" else 4674)
        layer = builder.build(arguments(path))
        reasons = {item["codigo_base"]: item["motivo"] for item in layer["excecoes"]}
        assert list(reasons) == ["170100"] and "referencial diferente" in reasons["170100"]


def test_gpkg_point_decoder_rejects_non_points_and_empty_geometries():
    assert builder._gpkg_point(gp_point(-48.1, -6.4, 4674, envelope=True)) == (-48.1, -6.4, 4674)
    line = b"GP" + bytes([0, 1]) + struct.pack("<i", 4674) + struct.pack("<BI", 1, 2) + struct.pack("<I4d", 2, 0, 0, 1, 1)
    with pytest.raises(ValueError, match="não é um ponto"):
        builder._gpkg_point(line)
    with pytest.raises(ValueError, match="vazia"):
        builder._gpkg_point(b"GP" + bytes([0, 0b10001]) + struct.pack("<i", 4674) + struct.pack("<BIdd", 1, 1, 0, 0))
    with pytest.raises(ValueError, match="inválida"):
        builder._gpkg_point(b"XX")


def test_cli_writes_the_layer_only_with_explicit_flag_and_backend_accepts_it(repo, tmp_path):
    source = write_csv(tmp_path / "localidades.csv", records())
    argv = ["--fonte", str(source), "--url", URL, "--edicao", "teste", "--campo-codigo", "CD_MUN", "--campo-nome", "NM_MUN",
            "--campo-uf", "SIGLA_UF", "--campo-categoria", "NM_CATEGORIA", "--valor-sede", "CIDADE",
            "--campo-lat", "LAT", "--campo-lon", "LONG", "--referencial", "SIRGAS2000",
            "--evidencia-referencial", "metadado sintético: SIRGAS 2000"]
    builder.main(argv)
    assert not (repo / LAYER).exists() and state(repo)["estado"] == "ausente"
    builder.main(argv + ["--gravar"])
    current = state(repo)
    assert current["estado"] == "valido" and current["excecoes"] == []
    assert current["aplica_se_a"] == brazil_data.governed_manifest()["sha256"]["municipal"]
    assert {code: (r["latitude"], r["longitude"]) for code, r in current["registros"].items()} == POINTS
