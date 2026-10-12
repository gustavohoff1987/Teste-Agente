"""Catálogo usa fontes sintéticas na CI. Não depende dos dados brasileiros."""
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import llm_bridge
from brazil_data import FILES
from install_brazil_data import install
from main import app


client = TestClient(app)


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    source = tmp_path / "original"
    source.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    book.active.append(["Brasil", 2023, 6, "MEDICINA", 10])
    book.active.append(["Brasil", 2024, 6, "MEDICINA", 15])
    book.save(source / FILES["national"])
    (source / FILES["municipal"]).write_text(
        "municipio;cod_ibge;periodo_ano;periodo_mes;categoria_profissional;quantidade;população_estimada;latitude;longitude\n"
        "A;001;2023;6;MEDICINA;6;1000;-10,1;-40,1\nB;002;2023;6;MEDICINA;8;2000;-11,1;-41,1\n"
        "A;001;2024;6;MEDICINA;10;1000;-10,1;-40,1\nB;002;2024;6;MEDICINA;12;2000;-11,1;-41,1\n", encoding="utf-8")
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES.values()}
    destination = tmp_path / "resident"
    install(source, destination)
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(destination))
    yield source, destination
    assert hashes == {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES.values()}


def inspected(operation="counts", scope="auto"):
    response = client.post("/api/inspect", data={"dataset": "brazil", "operation": operation, "scope": scope})
    assert response.status_code == 200, response.text
    return response.json()


def form(info, operation="counts", **options):
    return {"dataset": "brazil", "scope": info["source"]["scope"], "dataset_version": info["source"]["version"],
            "operation": operation, "mapping": json.dumps(info["suggested_mapping"]),
            "options": json.dumps({"count_unit": "pessoas", "confirmed_roles": ["period", "territory_id"], **options})}


def test_logical_dataset_routes_without_merging_and_accepts_municipal_counts(catalog):
    national = inspected()
    assert national["row_count"] == 2 and national["source"]["scope"] == "national"
    assert set(national["source"]["available_scopes"]) == set(FILES)
    assert national["sheets"] == []
    assert all(filename not in json.dumps(national) for filename in FILES.values())
    national_result = client.post("/api/analyze", data=form(national)).json()
    assert [row["Quantidade"] for row in national_result["rows"]] == [10, 15]
    municipal = inspected("density")
    assert municipal["source"]["scope"] == "municipal" and municipal["row_count"] == 4
    assert municipal["source"]["version"] == national["source"]["version"]
    response = client.post("/api/analyze", data=form(municipal, "density", population_denominator_confirmed=True))
    assert response.status_code == 200, response.text
    assert response.json()["rows"][0]["Território"] == "A [001]"
    assert response.json()["metadata"]["source"]["dataset"] == "brazil"
    municipal_counts = client.post("/api/analyze", data=form(municipal)).json()
    assert [row["Quantidade"] for row in municipal_counts["rows"]] == [6, 8, 10, 12]
    assert inspected("counts", "municipal")["source"]["scope"] == "municipal"
    assert client.post("/api/analyze", data=form(national, "density", population_denominator_confirmed=True)).status_code == 422


def test_curated_brazil_profiles_remove_unnecessary_user_confirmations(catalog):
    national = inspected()
    assert national["curated_defaults"]["count_unit"] == "pessoas"
    assert national["curated_defaults"]["category"] == "MEDICINA"
    request = form(national)
    request["options"] = "{}"
    result = client.post("/api/analyze", data=request)
    assert result.status_code == 200, result.text
    assert [row["Quantidade"] for row in result.json()["rows"]] == [10, 15]
    assert client.post("/api/preflight", data=request).json()["capabilities"]["counts"]["status"] == "available"
    municipal = inspected("density")
    assert municipal["curated_defaults"]["population_denominator_confirmed"] is True
    density = client.post("/api/analyze", data={
        **form(municipal, "density"), "options": "{}"})
    assert density.status_code == 200, density.text
    description = client.get("/api/brazil/description")
    assert description.status_code == 200, description.text
    assert "médicos" in description.json()["description"]
    assert "junho de 2023" in description.json()["description"]
    assert "junho de 2024" in description.json()["description"]


def test_curated_brazil_profile_never_assumes_unrelated_categories():
    import pandas as pd
    from brazil_catalog_profile import curated_profile, apply_curated_options
    frame = pd.DataFrame({"pais": ["Brasil"], "categoria_profissional": ["NÃO CLASSIFICADA"],
                          "contagem": [4], "Período (ano e mês)": ["202406"]})
    frame.attrs["source"] = {"dataset": "brazil", "scope": "national"}
    mapping = {"territory":"pais", "category":"categoria_profissional",
               "count":"contagem", "period":"Período (ano e mês)"}
    assert curated_profile(frame, mapping) is None
    assert apply_curated_options(frame, mapping, {}) == {}


def test_contextual_agent_can_read_resident_data_without_upload(catalog, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    sent = []

    async def provider(payload, model, key):
        sent.append(json.dumps(payload))
        return {"intent": "ANALITICO", "topic": "none", "operation": "counts", "indicator": "quantity", "period": "202406", "category": "", "territory": ""}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    response = client.post("/api/llm/interpret-context", data={**form(inspected()), "message": "Quantitativos em 202406"})
    assert response.status_code == 200, response.text
    assert response.json()["verification"]["slots"]["period"] == "found_in_dataset"
    assert response.json()["verification"]["capability_status"] == "available"
    assert sent and all(value not in sent[0] for value in ["Dados_Brasil", "periodo_ano", "MEDICINA", "Brasil"])


def test_missing_tampered_or_partial_catalog_fails_without_fallback(catalog):
    _, destination = catalog
    info = inspected()
    path = destination / FILES["municipal"]
    raw = path.read_bytes()
    try:
        path.write_bytes(raw + b"\n")
        assert client.post("/api/inspect", data={"dataset": "brazil", "operation": "counts"}).status_code == 422
        assert client.post("/api/analyze", data=form(info)).status_code == 422
    finally:
        path.write_bytes(raw)
    with pytest.raises(ValueError, match="nova"):
        install(catalog[0], destination)


def test_stale_version_and_unknown_sources_are_rejected(catalog):
    request = form(inspected())
    request["dataset_version"] = "stale-version"
    for endpoint in ("/api/analyze", "/api/preflight"):
        assert client.post(endpoint, data=request).status_code == 422
    for data in ({"dataset": "../secret"}, {"dataset": "brazil", "scope": "../secret"}, {}):
        assert client.post("/api/inspect", data=data).status_code == 422
    assert client.post("/api/inspect", data={"dataset": "brazil"},
                       files={"file": ("upload.csv", b"Ano;Quantidade\n2024;1")}).status_code == 422


def test_upload_remains_available_without_catalog(tmp_path, monkeypatch):
    monkeypatch.setenv("ADT_BRASIL_DATA_DIR", str(tmp_path / "missing"))
    assert client.post("/api/inspect", data={"dataset": "brazil"}).status_code == 422
    response = client.post("/api/inspect", files={"file": ("any-country.csv",
        b"country;year;category;count\nCanada;2024;nurses;20")})
    assert response.status_code == 200
    assert response.json()["source"] is None
