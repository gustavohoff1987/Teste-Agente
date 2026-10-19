"""Uso explícito de catálogos externos nos testes: pasta e versão fixadas juntas; fonte estadual sintética."""
from pathlib import Path

from brazil_data import FILES, catalog_version

STATE_HEADER = "uf;periodo_ano;periodo_mes;categoria_profissional;contagem"


def use_external_catalog(monkeypatch, folder):
    # Catálogos sintéticos não são a versão governada: o backend exige a versão fixada.
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(folder))
    monkeypatch.setenv("ADT_BRASIL_DATA_VERSION", catalog_version(folder))


def write_state_source(folder, counts):
    """Fonte estadual sintética no formato de Dados_Estados_Brasil.csv (médicos únicos por UF e competência, CRLF):
    {(sigla da UF, "AAAAMM"): contagem}. Não representa quantitativos reais."""
    lines = [STATE_HEADER] + [";".join((uf, period[:4], str(int(period[4:])), "MEDICINA", str(count)))
                              for (uf, period), count in counts.items()]
    (Path(folder) / FILES["state"]).write_bytes(("\r\n".join(lines) + "\r\n").encode("utf-8"))
