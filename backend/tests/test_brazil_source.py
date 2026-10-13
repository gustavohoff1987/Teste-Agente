"""Origem governada da base Brasil: arquivos versionados na raiz, manifesto e pastas externas explícitas."""
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import main
from brazil_data import FILES, GOVERNED_MANIFEST, catalog_version, governed_manifest, load_brazil, manifest_from_repository
from install_brazil_data import install

client = TestClient(main.app)
MUNICIPAL = ("municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;população_estimada;latitude;longitude\n"
             "ALFA;100001;2024;6;MEDICINA;{q};1000;-10,5;-50,5\nBETA;100002;2024;6;MEDICINA;7;2000;-11,5;-51,5\n")


def write_sources(folder, q=5):
    folder.mkdir(parents=True, exist_ok=True)
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    book.active.append(["Brasil", 2024, 6, "MEDICINA", 100])
    book.save(folder / FILES["national"])
    (folder / FILES["municipal"]).write_text(MUNICIPAL.format(q=q), encoding="utf-8")


def write_manifest(root):
    (root / GOVERNED_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (root / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(root)), encoding="utf-8")


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Raiz de repositório sintética com fontes versionadas e manifesto governado."""
    root = tmp_path / "repositorio"
    write_sources(root)
    write_manifest(root)
    monkeypatch.setattr(brazil_data, "REPO_ROOT", root)
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    main._BRAZIL_FRAMES.clear()
    yield root
    main._BRAZIL_FRAMES.clear()


def inspect_municipal():
    return client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"})


def density(version):
    return client.post("/api/analyze", data={
        "dataset": "brazil", "scope": "municipal", "dataset_version": version, "operation": "density",
        "mapping": json.dumps(inspect_municipal().json()["suggested_mapping"]),
        "options": json.dumps({"confirmed_roles": ["territory", "territory_id", "period", "category", "count", "population"],
                               "count_unit": "pessoas", "population_denominator_confirmed": True, "fts_scope_confirmed": True,
                               "object_confirmed": True, "period_filter": "202406"})})


def test_real_repository_files_are_the_default_source(monkeypatch):
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    raw, name, source, integrity = load_brazil("municipal", details=True)
    root = Path(brazil_data.__file__).resolve().parents[1]
    assert integrity["modo"] == "repositorio" and integrity["integridade"] == "verificada"
    assert Path(integrity["origem"]["municipal"]) == root / FILES["municipal"]
    assert raw == (root / FILES["municipal"]).read_bytes()  # os próprios bytes versionados
    assert source["version"] == governed_manifest(root)["versao"] == integrity["versao"]


def test_versioned_sources_work_without_any_local_installation(repo):
    assert not (repo / ".local").exists()
    response = inspect_municipal()
    assert response.status_code == 200, response.text
    version = response.json()["source"]["version"]
    assert version == governed_manifest(repo)["versao"]
    body = density(version).json()
    assert {r["Território"].split(" [")[0]: r["Quantidade"] for r in body["rows"]} == {"ALFA": 5, "BETA": 7}


def test_old_local_copy_is_never_used(repo):
    old = repo / ".local" / "datasets" / "brasil"
    write_sources(repo / "antiga", q=99)
    install(repo / "antiga", old, governed=False)
    version = inspect_municipal().json()["source"]["version"]
    assert version == governed_manifest(repo)["versao"] != catalog_version(old)
    alfa = next(r for r in density(version).json()["rows"] if r["Território"].startswith("ALFA"))
    assert alfa["Quantidade"] == 5  # conteúdo da raiz, nunca o da cópia antiga


def test_changed_original_is_refused_without_fallback(repo):
    path = repo / FILES["municipal"]
    path.write_text(MUNICIPAL.format(q=6), encoding="utf-8")
    response = inspect_municipal()
    assert response.status_code == 422 and "difere do manifesto" in response.json()["detail"]
    assert client.get("/api/brazil/source").json()["integridade"] == "recusada"


@pytest.mark.parametrize("damage", ["ausente", "desatualizado", "json", "esquema", "versao", "sha256", "caminho"])
def test_missing_outdated_or_invalid_manifest_is_refused(repo, damage):
    manifest = repo / GOVERNED_MANIFEST
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if damage == "ausente":
        manifest.unlink()
    elif damage == "desatualizado":
        write_sources(repo, q=8)  # fontes novas sem manifesto atualizado
    elif damage == "json":
        manifest.write_text("{", encoding="utf-8")
    elif damage == "esquema":
        manifest.write_text(json.dumps({**data, "schema_version": 2}), encoding="utf-8")
    elif damage == "versao":
        manifest.write_text(json.dumps({**data, "versao": "0" * 64}), encoding="utf-8")
    elif damage == "sha256":
        data["arquivos"]["national"]["sha256"] = "x" * 64
        manifest.write_text(json.dumps(data), encoding="utf-8")
    else:
        data["arquivos"]["municipal"]["caminho"] = "../" + FILES["municipal"]
        manifest.write_text(json.dumps(data), encoding="utf-8")
    response = inspect_municipal()
    assert response.status_code == 422 and "integridade" in response.json()["detail"]
    diagnostic = client.get("/api/brazil/source").json()
    assert diagnostic["integridade"] == "recusada" and diagnostic["modo"] == "repositorio"


def test_inspected_and_analyzed_versions_must_match_after_a_governed_update(repo):
    before = inspect_municipal().json()["source"]["version"]
    write_sources(repo, q=11)
    write_manifest(repo)  # atualização governada: novas fontes e novo manifesto
    after = inspect_municipal().json()["source"]["version"]
    assert after != before
    stale = density(before)
    assert stale.status_code == 422 and "atualizada" in stale.json()["detail"]
    alfa = next(r for r in density(after).json()["rows"] if r["Território"].startswith("ALFA"))
    assert alfa["Quantidade"] == 11
    assert [k for k in main._BRAZIL_FRAMES if k[0] == FILES["municipal"]] == [(FILES["municipal"], after)]


def test_restart_reads_the_same_governed_source(monkeypatch):
    env = {k: v for k, v in os.environ.items() if k not in ("ADT_BRASIL_DATA_DIR", "ADT_BRASIL_DATA_VERSION")}
    backend = Path(main.__file__).resolve().parent
    output = subprocess.run([sys.executable, str(backend / "brazil_data.py"), "diagnostico"], cwd=backend, env=env,
                            capture_output=True, text=True, check=True).stdout
    diagnostic = json.loads(output)
    assert diagnostic["modo"] == "repositorio" and diagnostic["integridade"] == "verificada"
    assert diagnostic["versao"] == governed_manifest(backend.parent)["versao"]
    # Mesmo processo, caches esvaziados como em um reinício: mesma origem e versão.
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    main._BRAZIL_FRAMES.clear()
    assert load_brazil("national")[2]["version"] == diagnostic["versao"]


def test_external_directory_needs_the_governed_version_or_an_explicit_pin(repo, tmp_path, monkeypatch):
    governed_copy = tmp_path / "copia_governada"
    install(repo, governed_copy)  # padrão: somente a versão governada
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(governed_copy))
    assert inspect_municipal().json()["source"]["version"] == governed_manifest(repo)["versao"]
    assert client.get("/api/brazil/source").json()["modo"] == "externo"
    write_sources(tmp_path / "outra", q=3)
    with pytest.raises(ValueError, match="versão governada"):
        install(tmp_path / "outra", tmp_path / "nao_governada")
    install(tmp_path / "outra", tmp_path / "nao_governada", governed=False)
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(tmp_path / "nao_governada"))
    refused = inspect_municipal()
    assert refused.status_code == 422 and "ADT_BRASIL_DATA_VERSION" in refused.json()["detail"]
    monkeypatch.setenv("ADT_BRASIL_DATA_VERSION", "f" * 64)
    assert inspect_municipal().status_code == 422  # fixação divergente também é recusada
    monkeypatch.setenv("ADT_BRASIL_DATA_VERSION", catalog_version(tmp_path / "nao_governada"))
    accepted = inspect_municipal()
    assert accepted.status_code == 200 and accepted.json()["source"]["version"] != governed_manifest(repo)["versao"]
    diagnostic = client.get("/api/brazil/source").json()
    assert diagnostic["versao_fixada"] == diagnostic["versao"] != diagnostic["versao_governada"]


def test_uploads_never_depend_on_the_brazil_catalog(repo):
    (repo / GOVERNED_MANIFEST).unlink()
    assert inspect_municipal().status_code == 422
    upload = client.post("/api/inspect", files={"file": ("pais.csv", b"country;year;category;count\nCanada;2024;nurses;20")})
    assert upload.status_code == 200 and upload.json()["source"] is None


def test_diagnostic_shows_origin_identity_and_integrity_without_content(repo):
    body = client.get("/api/brazil/source").json()
    assert body["modo"] == "repositorio" and body["integridade"] == "verificada"
    assert body["origem"]["municipal"] == str(repo / FILES["municipal"])
    assert body["sha256"]["municipal"] == hashlib.sha256((repo / FILES["municipal"]).read_bytes()).hexdigest()
    assert body["versao"] == body["versao_governada"] and body["versao_fixada"] is None
    text = json.dumps(body, ensure_ascii=False)
    assert "ALFA" not in text and "MEDICINA" not in text
