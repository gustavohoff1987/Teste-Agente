"""Reaproveitamento das fontes Brasil: integridade, versões, isolamento e limites."""
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import pytest
from fastapi.testclient import TestClient

import main
import request_memo
from brazil_catalog_profile import FIELDS
from brazil_data import FILES, load_brazil
from prepare_block1_catalog import prepare
from catalog_support import use_external_catalog


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    folder = tmp_path / "catalogo"
    prepare(folder)
    use_external_catalog(monkeypatch, folder)
    monkeypatch.delenv("ADT_BRASIL_CACHE_MAX_MB", raising=False)
    main._BRAZIL_FRAMES.clear()
    yield folder
    main._BRAZIL_FRAMES.clear()


def pristine(scope="municipal"):
    raw, name, _ = load_brazil(scope)
    return main.read_dataset(raw, name)[0]


def analyze(client, version, **options):
    response = client.post("/api/analyze", data={
        "dataset": "brazil", "scope": "municipal", "dataset_version": version, "operation": "density",
        "mapping": json.dumps(FIELDS["municipal"]), "options": json.dumps({"period_filter": "202406", **options})})
    body = response.json()
    if response.status_code == 200:
        body.pop("result_id")
        body["metadata"].pop("created_at")
    return response.status_code, body


def test_each_request_receives_its_own_copy(catalog):
    raw, name, source = load_brazil("municipal")
    first = main._brazil_frame(raw, name, source)
    first.iloc[0, 0] = "ALTERADO"
    first.attrs["source"]["label"] = "alterado"
    first.attrs["derived_fields"].clear()  # attrs precisam ser copiados em profundidade
    raw, name, fresh = load_brazil("municipal")
    second = main._brazil_frame(raw, name, fresh)
    assert second is not first
    pd.testing.assert_frame_equal(second, pristine())
    assert second.attrs["source"]["label"] == "Dados do Brasil"
    assert second.attrs["derived_fields"] == pristine().attrs["derived_fields"] != []
    assert len(main._BRAZIL_FRAMES) == 1 and "source" not in next(iter(main._BRAZIL_FRAMES.values())).attrs


def test_integrity_is_verified_on_every_request(catalog):
    client = TestClient(main.app)
    version = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()["source"]["version"]
    assert analyze(client, version)[0] == 200
    path = catalog / FILES["municipal"]
    path.write_bytes(path.read_bytes().replace(b"MANAUS;130260;2024;6;MEDICINA;15", b"MANAUS;130260;2024;6;MEDICINA;99"))
    status, body = analyze(client, version)
    assert status == 422 and "integridade" in body["detail"]
    path.unlink()
    assert analyze(client, version)[0] == 422


def test_new_version_never_reuses_previous_content(catalog, tmp_path, monkeypatch):
    client = TestClient(main.app)
    first = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    _, before = analyze(client, first["source"]["version"])
    # Nova instalação com outro conteúdo: outra versão, outra interpretação.
    source = tmp_path / "fonte"
    source.mkdir()
    (source / FILES["national"]).write_bytes((catalog / FILES["national"]).read_bytes())
    (source / FILES["state"]).write_bytes((catalog / FILES["state"]).read_bytes())
    (source / FILES["municipal"]).write_text((catalog / FILES["municipal"]).read_text(encoding="utf-8").replace(
        "MANAUS;130260;2024;6;MEDICINA;15", "MANAUS;130260;2024;6;MEDICINA;40"), encoding="utf-8")
    from install_brazil_data import install
    install(source, tmp_path / "nova", governed=False)
    use_external_catalog(monkeypatch, tmp_path / "nova")
    second = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    assert second["source"]["version"] != first["source"]["version"]
    assert analyze(client, first["source"]["version"])[0] == 422  # versão antiga recusada como antes
    _, after = analyze(client, second["source"]["version"])
    manaus = lambda body: next(r for r in body["rows"] if r["Território"].startswith("MANAUS"))
    assert manaus(before)["Quantidade"] == 15 and manaus(after)["Quantidade"] == 40
    assert [key for key in main._BRAZIL_FRAMES if key[0] == FILES["municipal"]] == [
        (FILES["municipal"], second["source"]["version"])]


def test_uploads_are_never_kept(catalog):
    client = TestClient(main.app)
    csv = b"territorio_analise;periodo;categoria_profissional;quantidade\nAlfa;2024;MEDICINA;10\n"
    assert client.post("/api/inspect", files={"file": ("local.csv", csv, "text/csv")}).status_code == 200
    assert not main._BRAZIL_FRAMES


def test_responses_are_identical_with_and_without_reuse(catalog, monkeypatch):
    client = TestClient(main.app)
    version = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()["source"]["version"]
    selection = {"territory_ids": ["code:130260", "code:130420", "code:130340"]}
    reused = [analyze(client, version), analyze(client, version, **selection)]
    assert main._BRAZIL_FRAMES
    monkeypatch.setenv("ADT_BRASIL_CACHE_MAX_MB", "0")
    main._BRAZIL_FRAMES.clear()
    direct = [analyze(client, version), analyze(client, version, **selection)]
    assert not main._BRAZIL_FRAMES
    assert reused == direct


def test_concurrent_requests_share_nothing_mutable(catalog):
    raw, name, source = load_brazil("municipal")
    expected = pristine()

    def worker(index):
        frame = main._brazil_frame(raw, name, source)
        pd.testing.assert_frame_equal(frame, expected)
        frame.iloc[index % len(frame), 0] = "X" + str(index)  # mutação local à requisição
        return frame.attrs["source"]["version"]

    with ThreadPoolExecutor(max_workers=8) as pool:
        assert set(pool.map(worker, range(64))) == {source["version"]}
    pd.testing.assert_frame_equal(main._brazil_frame(raw, name, source), expected)


INSPECT = {"dataset": "brazil", "scope": "auto", "operation": "", "sheet": ""}


def test_derived_results_are_reused_only_for_the_same_verified_version(catalog, monkeypatch):
    import semantic_bridge
    computed, original = [], semantic_bridge._proposals
    monkeypatch.setattr(semantic_bridge, "_proposals", lambda *a, **k: computed.append(1) or original(*a, **k))
    client = TestClient(main.app)
    first = client.post("/api/inspect", data=INSPECT)
    assert first.status_code == 200, first.text
    count = len(computed)
    assert count  # perfis das colunas calculados na primeira inspeção
    assert client.post("/api/inspect", data=INSPECT).json() == first.json() and len(computed) == count
    monkeypatch.setenv("ADT_BRASIL_CACHE_MAX_MB", "0")  # sem reaproveitamento, tudo é calculado de novo
    main._BRAZIL_FRAMES.clear()
    assert client.post("/api/inspect", data=INSPECT).json() == first.json() and len(computed) > count


def test_uploads_never_enter_the_shared_memory(catalog):
    client = TestClient(main.app)
    csv = b"territorio_analise;periodo;categoria_profissional;quantidade\nAlfa;2024;MEDICINA;10\n"
    for _ in range(2):
        assert client.post("/api/inspect", files={"file": ("local.csv", csv, "text/csv")}).status_code == 200
    assert not request_memo._SHARED


def test_warm_up_prepares_the_first_inspection_without_changing_it(catalog, monkeypatch):
    expected = TestClient(main.app).post("/api/inspect", data=INSPECT).json()
    request_memo.clear_shared()
    main._BRAZIL_FRAMES.clear()
    monkeypatch.setenv("ADT_AQUECIMENTO", "1")
    try:
        with TestClient(main.app) as client:  # a partida do servidor dispara o aquecimento em segundo plano
            body = client.post("/api/inspect", data=INSPECT).json()  # espera o aquecimento em curso
            assert main._WARM_DONE.is_set()
        assert body == expected and request_memo._SHARED
        called = []
        monkeypatch.setattr(main, "_warm_up", lambda: called.append(1))
        monkeypatch.setenv("ADT_AQUECIMENTO", "0")
        with TestClient(main.app):
            pass
        assert called == []
    finally:
        main._WARM_DONE.set()
