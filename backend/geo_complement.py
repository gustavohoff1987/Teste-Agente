"""Camada geográfica complementar da base Brasil (Bloco 2, Etapa 2).

Coordenadas oficiais de sede municipal para os seis municípios autorizados cuja coordenada na
fonte original é inválida, sob a premissa metodológica do usuário de uma coordenada fixa nas 22
competências de janeiro e junho de 2014 a 2024. A camada é um arquivo versionado
(dados/brasil/complemento_coordenadas.json) validado a cada leitura; os arquivos originais não
são alterados: a substituição ocorre ao ler coordenadas, só para a versão governada da fonte
municipal, só nas competências autorizadas e só onde o ponto original é inválido. O ponto é
substituído inteiro (latitude e longitude), para não combinar conceitos geográficos diferentes.
Bases importadas nunca recebem o complemento.
"""
import hashlib
import json
import math
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from data_contract import canonical_crs, text_values
from request_memo import request_value

LAYER = Path("dados") / "brasil" / "complemento_coordenadas.json"
PREMISE = "COORDENADA_FIXA_2014_2024"
PERIODS = tuple(f"{year}{month:02d}" for year in range(2014, 2025) for month in (1, 6))
# Decisão humana registrada: somente estes municípios, validados na base (nome, UF e código).
AUTHORIZED = {"170100": ("ANANAS", "TO"), "421265": ("PESCARIA BRAVA", "SC"), "422000": ("BALNEARIO RINCAO", "SC"),
              "500490": ("JARAGUARI", "MS"), "430367": ("CAMPESTRE DA SERRA", "RS"), "350050": ("AGUAS DE LINDOIA", "SP")}
SHA256 = re.compile(r"[0-9a-f]{64}")
# Proveniência registrada nos resultados espaciais (inclui a declaração de verificação da fonte).
PROVENANCE = ("produto", "edicao", "arquivo", "sha256_arquivo", "referencial", "epsg", "ponto", "verificacao")


def _plain(text):
    return "".join(c for c in unicodedata.normalize("NFD", str(text).upper()) if not unicodedata.combining(c)).strip()


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _validate(data):
    _require(isinstance(data, dict) and data.get("schema_version") == 1, "esquema não suportado")
    for key in ("identificador", "versao"):
        _require(isinstance(data.get(key), str) and data[key].strip(), "campo ausente: " + key)
    target = data.get("aplica_se_a") or {}
    _require(target.get("arquivo") == "Dados_Municipios_Brasil.csv" and SHA256.fullmatch(str(target.get("sha256", ""))),
             "versão da fonte municipal não identificada")
    _require(list((data.get("escopo_temporal") or {}).get("competencias") or []) == list(PERIODS),
             "escopo temporal diferente das 22 competências autorizadas (2014–2024)")
    premise = data.get("premissa") or {}
    _require(premise.get("tipo") == PREMISE and premise.get("origem") == "decisao_metodologica_do_usuario",
             "premissa de coordenada fixa não identificada")
    source = data.get("fonte") or {}
    for key in ("produto", "url", "edicao", "ponto", "referencial", "evidencia_referencial"):
        _require(isinstance(source.get(key), str) and source[key].strip(), "fonte sem " + key)
    _require(source["url"].startswith("https://") and ".ibge.gov.br/" in source["url"], "fonte fora do IBGE")
    _require(canonical_crs(source["referencial"]) == "SIRGAS2000", "referencial da fonte não suportado ou não declarado")
    _require(SHA256.fullmatch(str(source.get("sha256_arquivo", ""))), "SHA-256 do arquivo oficial ausente")
    records, seen = {}, set()
    for item in data.get("municipios") or []:
        code = str(item.get("codigo_base", ""))
        _require(code in AUTHORIZED and code not in seen, "município não autorizado ou repetido: " + code)
        seen.add(code)
        name, uf = AUTHORIZED[code]
        _require(_plain(item.get("municipio", "")) == name and item.get("uf") == uf, "nome ou UF divergente: " + code)
        official = str(item.get("codigo_ibge", ""))
        _require(re.fullmatch(r"\d{7}", official) and official.startswith(code), "código oficial incompatível: " + code)
        lat, lon = item.get("latitude"), item.get("longitude")
        _require(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in (lat, lon))
                 and abs(lat) <= 90 and abs(lon) <= 180, "coordenada inválida no complemento: " + code)
        records[code] = {"codigo_ibge": official, "municipio": name, "uf": uf, "latitude": float(lat), "longitude": float(lon)}
    _require(records, "nenhum município no complemento")
    return records


def state(root=None):
    """Estado da camada versionada: ausente, inválida (com motivo) ou válida (com identidade e registros).

    Lido uma vez por requisição: identidade, sobreposição e metadados usam a mesma versão."""
    return request_value(("geo_complement.state", str(root)), lambda: _state(root))


def _state(root=None):
    from brazil_data import REPO_ROOT
    path = Path(root or REPO_ROOT) / LAYER
    if not path.is_file():
        return {"estado": "ausente", "arquivo": LAYER.as_posix(),
                "motivo": "camada versionada inexistente: coordenadas oficiais ainda não incorporadas"}
    raw = path.read_bytes()
    identity = {"arquivo": LAYER.as_posix(), "sha256": hashlib.sha256(raw).hexdigest()}
    try:
        data = json.loads(raw.decode("utf-8"))
        records = _validate(data)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError, AttributeError) as exc:
        return {**identity, "estado": "invalido", "motivo": str(exc) or "arquivo ilegível"}
    missing = sorted(set(AUTHORIZED) - set(records))
    return {**identity, "estado": "valido", "identificador": data["identificador"], "versao": data["versao"],
            "aplica_se_a": data["aplica_se_a"]["sha256"], "fonte": data["fonte"], "premissa": data["premissa"],
            "escopo_temporal": list(PERIODS), "registros": records, "excecoes": missing}


def identity(current):
    """Resumo que entra nas chaves de execução e nos metadados das análises espaciais, com a proveniência oficial."""
    summary = {key: current.get(key) for key in ("estado", "arquivo", "sha256", "identificador", "versao", "motivo")
               if current.get(key) is not None}
    if current.get("fonte"):
        summary["proveniencia"] = {key: current["fonte"][key] for key in PROVENANCE if current["fonte"].get(key) is not None}
    return summary


def frame_identity(frame):
    """Identidade da camada para esta base Brasil municipal: incompatível se a camada se refere a outra versão."""
    current = state()
    info = identity(current)
    municipal = ((frame.attrs.get("catalog") or {}).get("sha256") or {}).get("municipal")
    if current["estado"] == "valido" and municipal != current["aplica_se_a"]:
        return {**info, "estado": "incompativel", "motivo": "a camada se refere a outra versão da fonte municipal"}
    return info


def overlay(frame, mapping, lat, lon):
    """Coordenadas efetivas: substitui o ponto inválido dos municípios autorizados, se a camada se aplicar.

    lat e lon são numéricos (NaN quando ausentes ou não numéricos), alinhados ao frame. Devolve
    (lat, lon, máscara das linhas complementadas ou None, registro do complemento).
    """
    source = frame.attrs.get("source") or {}
    if source.get("dataset") != "brazil" or source.get("scope") != "municipal":
        return lat, lon, None, None  # uploads e recorte nacional: nunca complementados
    current = state()
    info = frame_identity(frame)
    if info["estado"] != "valido":
        return lat, lon, None, info
    code_col, period_col, name_col = mapping.get("territory_id"), mapping.get("period"), mapping.get("territory")
    if not code_col or not period_col:
        return lat, lon, None, {**info, "estado": "nao_aplicada", "motivo": "código territorial ou período não associados"}
    codes = text_values(frame[code_col]).fillna("")
    periods = text_values(frame[period_col]).fillna("")
    lat_values, lon_values = np.asarray(lat, dtype=float).copy(), np.asarray(lon, dtype=float).copy()
    valid = np.isfinite(lat_values) & np.isfinite(lon_values) & (np.abs(lat_values) <= 90) & (np.abs(lon_values) <= 180)
    records = current["registros"]
    applied = np.zeros(len(frame), dtype=bool)
    # Candidatas: ponto inválido de município da camada em competência autorizada; só elas têm o nome normalizado.
    candidates = np.flatnonzero(codes.isin(list(records)).to_numpy() & periods.isin(PERIODS).to_numpy() & ~valid)
    candidate_codes = codes.to_numpy()[candidates]
    names = text_values(frame[name_col].iloc[candidates]).fillna("").map(_plain).to_numpy() if name_col else None
    for code, record in records.items():
        match = candidate_codes == code
        if names is not None:
            match &= names == record["municipio"]  # nome conferido na própria base
        rows = candidates[match]
        lat_values[rows], lon_values[rows] = record["latitude"], record["longitude"]
        applied[rows] = True
    complemented = sorted(set(codes[applied])) if applied.any() else []
    as_series = isinstance(lat, pd.Series)
    return (pd.Series(lat_values, index=lat.index) if as_series else lat_values,
            pd.Series(lon_values, index=lon.index) if as_series else lon_values,
            applied, {**info, "municipios_complementados": complemented, "linhas_complementadas": int(applied.sum()),
                      "excecoes": current["excecoes"], "premissa": current["premissa"]["tipo"],
                      "escopo_temporal": [PERIODS[0], PERIODS[-1]]})
