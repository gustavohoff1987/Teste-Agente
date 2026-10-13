"""Uso explícito de catálogos externos nos testes: pasta e versão fixadas juntas."""
from brazil_data import catalog_version


def use_external_catalog(monkeypatch, folder):
    # Catálogos sintéticos não são a versão governada: o backend exige a versão fixada.
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(folder))
    monkeypatch.setenv("ADT_BRASIL_DATA_VERSION", catalog_version(folder))
