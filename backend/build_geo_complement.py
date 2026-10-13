"""Constrói a camada geográfica complementar a partir do arquivo oficial do IBGE (uso administrativo).

Uso, na raiz do repositório, depois de baixar o arquivo oficial de Localidades do Brasil 2022:
    python backend/build_geo_complement.py --fonte <arquivo> --url <URL oficial do arquivo> \\
        --edicao "<edição>" --campo-codigo <campo> --campo-nome <campo> --campo-uf <campo> \\
        --campo-categoria <campo> --valor-sede "<valor que identifica a sede municipal>" \\
        [--camada <tabela do GeoPackage>] [--campos-extras <campo,campo>] \\
        [--campo-lat <campo> --campo-lon <campo> --referencial SIRGAS2000 \\
         --evidencia-referencial "<trecho do metadado oficial>" --codificacao <codificação>] [--gravar]

Os nomes de campos e o valor da categoria de sede devem ser conferidos no próprio arquivo; nada é
presumido. Em GeoPackage, o ponto vem da geometria e o referencial de gpkg_spatial_ref_sys
(EPSG:4674 = SIRGAS 2000); em CSV/XLSX, exige campos de latitude/longitude, referencial e evidência
textual explícitos. Cada município autorizado precisa de um único registro de sede com código (6
dígitos da base como prefixo do código de 7), nome e UF iguais; caso contrário fica como exceção,
sem escolha arbitrária. Sem --gravar, apenas exibe a camada proposta; com --gravar, valida e grava
dados/brasil/complemento_coordenadas.json.
"""
import argparse
import hashlib
import json
import math
import sqlite3
import struct
import sys
from pathlib import Path

import pandas as pd

import brazil_data
from geo_complement import AUTHORIZED, LAYER, PERIODS, PREMISE, _plain, _validate

SIRGAS2000_EPSG = 4674


def _gpkg_point(blob):
    """(longitude, latitude, srs_id) de uma geometria pontual GeoPackage (cabeçalho GP + WKB ISO)."""
    if not isinstance(blob, (bytes, memoryview)) or bytes(blob[:2]) != b"GP":
        raise ValueError("geometria GeoPackage inválida")
    blob = bytes(blob)
    flags = blob[3]
    if flags & 0x30:  # bit 4: geometria vazia; bit 5: formato estendido
        raise ValueError("geometria vazia ou em formato estendido")
    envelope = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}.get((flags >> 1) & 7)
    if envelope is None:
        raise ValueError("envelope GeoPackage inválido")
    order = "<" if flags & 1 else ">"
    srs_id = struct.unpack(order + "i", blob[4:8])[0]
    wkb = blob[8 + envelope:]
    wkb_order = "<" if wkb[0] == 1 else ">"
    kind = struct.unpack(wkb_order + "I", wkb[1:5])[0] % 1000
    if kind != 1:
        raise ValueError("a geometria não é um ponto")
    x, y = struct.unpack(wkb_order + "dd", wkb[5:21])
    return x, y, srs_id


def _read_gpkg(path, args):
    if args.campo_lat or args.campo_lon or args.referencial:
        raise ValueError("em GeoPackage o ponto vem da geometria e o referencial de gpkg_spatial_ref_sys")
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
        layer = args.camada or db.execute("SELECT table_name FROM gpkg_contents WHERE data_type='features'").fetchone()[0]
        geom, srs_id = db.execute("SELECT column_name, srs_id FROM gpkg_geometry_columns WHERE table_name=?",
                                  (layer,)).fetchone()
        srs = db.execute("SELECT organization, organization_coordsys_id FROM gpkg_spatial_ref_sys WHERE srs_id=?",
                         (srs_id,)).fetchone()
        frame = pd.read_sql_query(f'SELECT * FROM "{layer}"', db)
    if not srs or str(srs[0]).upper() != "EPSG" or srs[1] != SIRGAS2000_EPSG:
        raise ValueError("o GeoPackage não declara o referencial SIRGAS 2000 (EPSG:4674) para a camada")

    def point(blob):  # decodificado só para o registro associado; o SRS da geometria deve ser o da camada
        x, y, own = _gpkg_point(blob)
        if own != srs_id:
            raise ValueError("geometria com referencial diferente do declarado para a camada")
        return y, x

    return frame, point, geom, "SIRGAS2000", "gpkg_spatial_ref_sys: EPSG:4674 (SIRGAS 2000)"


def _read_table(path, args):
    if not (args.referencial and args.evidencia_referencial and args.campo_lat and args.campo_lon):
        raise ValueError("CSV/XLSX exige campos de latitude/longitude, referencial e evidência textual do metadado oficial")
    if path.suffix.lower() in (".xlsx", ".xls"):
        frame = pd.read_excel(path, dtype=str)
    else:
        try:
            frame = pd.read_csv(path, dtype=str, sep=None, engine="python", encoding=args.codificacao)
        except UnicodeDecodeError as exc:
            raise ValueError("codificação do arquivo diferente de " + args.codificacao + "; informe --codificacao") from exc

    def point(row):
        return tuple(float(str(row[field]).strip().replace(",", ".")) for field in (args.campo_lat, args.campo_lon))

    return frame, point, None, args.referencial, args.evidencia_referencial


def build(args):
    path = Path(args.fonte)
    raw = path.read_bytes()
    frame, point, geom, reference, evidence = (_read_gpkg if path.suffix.lower() == ".gpkg" else _read_table)(path, args)
    extras = [field for field in (args.campos_extras or "").split(",") if field.strip()]
    keys = [args.campo_codigo, args.campo_nome, args.campo_uf, args.campo_categoria] + extras
    missing = [field for field in keys if field not in frame.columns]
    if missing:
        raise ValueError("campos inexistentes no arquivo: " + ", ".join(missing))
    codes = frame[args.campo_codigo].astype(str).str.strip()
    names = frame[args.campo_nome].map(_plain)
    ufs = frame[args.campo_uf].astype(str).str.strip()
    seats = frame[args.campo_categoria].astype(str).str.strip() == args.valor_sede
    records, exceptions = [], []
    for code, (name, uf) in AUTHORIZED.items():
        match = frame[codes.str.fullmatch(code + r"\d") & (names == name) & (ufs == uf) & seats]
        if len(match) != 1:
            exceptions.append({"codigo_base": code, "municipio": name, "uf": uf,
                               "motivo": "nenhum registro de sede" if match.empty else "mais de um registro de sede (ambíguo)"})
            continue
        row = match.iloc[0]
        try:
            lat, lon = point(row[geom] if geom else row)
            if not (math.isfinite(lat) and math.isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180):
                raise ValueError("coordenada fora do intervalo geográfico")
        except (ValueError, TypeError) as exc:
            exceptions.append({"codigo_base": code, "municipio": name, "uf": uf,
                               "motivo": "registro de sede sem ponto válido: " + str(exc)})
            continue
        records.append({"codigo_base": code, "codigo_ibge": codes[match.index[0]], "municipio": name, "uf": uf,
                        "latitude": lat, "longitude": lon, "ponto": "sede municipal",
                        "registro_oficial": {field: str(row[field]) for field in keys}})
    layer = {
        "schema_version": 1, "identificador": "complemento-coordenadas-ibge-localidades-2022", "versao": args.versao,
        "finalidade": "Coordenadas oficiais de sede municipal para municípios com ponto inválido na fonte original.",
        "aplica_se_a": {"arquivo": brazil_data.FILES["municipal"],
                        "sha256": brazil_data.governed_manifest()["sha256"]["municipal"]},
        "escopo_temporal": {"competencias": list(PERIODS)},
        "premissa": {"tipo": PREMISE, "origem": "decisao_metodologica_do_usuario",
                     "descricao": "Uma coordenada fixa por município para as 22 competências de 2014 a 2024; premissa "
                                  "metodológica do usuário, sem comprovação independente de estabilidade histórica."},
        "fonte": {"produto": "IBGE — Censo Demográfico 2022 — Localidades do Brasil", "url": args.url, "edicao": args.edicao,
                  "arquivo": path.name, "sha256_arquivo": hashlib.sha256(raw).hexdigest(), "referencial": reference,
                  "evidencia_referencial": evidence,
                  "ponto": "sede municipal (" + args.campo_categoria + " = " + args.valor_sede + ")"},
        "municipios": records, "excecoes": exceptions}
    _validate(layer)  # mesmas regras aplicadas pelo backend a cada leitura
    return layer


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ("fonte", "url", "edicao", "campo-codigo", "campo-nome", "campo-uf", "campo-categoria", "valor-sede"):
        parser.add_argument("--" + name, required=True)
    for name in ("campo-lat", "campo-lon", "camada", "referencial", "evidencia-referencial", "campos-extras"):
        parser.add_argument("--" + name)
    parser.add_argument("--codificacao", default="utf-8-sig")
    parser.add_argument("--versao", default="1")
    parser.add_argument("--gravar", action="store_true")
    args = parser.parse_args(argv)
    layer = build(args)
    text = json.dumps(layer, ensure_ascii=False, indent=2) + "\n"
    if args.gravar:
        target = brazil_data.REPO_ROOT / LAYER
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        print("Camada gravada em " + LAYER.as_posix() + "; revise as exceções e registre no Git.", file=sys.stderr)
    else:
        print(text)
    return layer


if __name__ == "__main__":
    main()
