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
from catalog_support import use_external_catalog, write_state_source


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
    write_state_source(source, {("AC", "202306"): 5, ("AC", "202406"): 7})
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES.values()}
    destination = tmp_path / "resident"
    install(source, destination, governed=False)
    use_external_catalog(monkeypatch, destination)
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
    assert national["source"]["available_scopes"] == ["national", "municipal"]  # a fonte estadual não é um recorte
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


def test_multiple_periods_are_independent_and_invalid_periods_are_rejected(catalog):
    national = inspected()
    import json
    request = form(national, "counts")
    request["options"] = json.dumps({"period_filters": ["202306", "202406"]})
    result = client.post("/api/analyze", data=request)
    assert result.status_code == 200, result.text
    assert sorted((row["Período"], row["Quantidade"]) for row in result.json()["rows"]) == [
        ("202306", 10), ("202406", 15)]
    request["options"] = json.dumps({"period_filters": ["202406"]})
    result = client.post("/api/analyze", data=request)
    assert result.status_code == 200, result.text
    assert [row["Quantidade"] for row in result.json()["rows"]] == [15]
    for options in (
        {"period_filters": ["202306", "209906"]},
        {"period_filters": ["202306", "202306"]},
        {"period_filters": ["202306", "202406"], "period_filter": "202406"},
        {"period_filters": [202306]},
    ):
        request["options"] = json.dumps(options)
        assert client.post("/api/analyze", data=request).status_code == 422


GOVERNED = ["temporal_comparability_confirmed", "territory_longitudinal_confirmed", "comparison_confirmed",
            "population_additive_confirmed", "component_sum_confirmed"]


def test_official_base_resolves_comparability_premises_without_user_declarations(catalog):
    national = inspected("temporal")
    assert [item["option"] for item in national["curated_defaults"]["premises"]] == GOVERNED[:2]
    request = {**form(national, "temporal"), "options": json.dumps({"temporal_indicator": "quantity"})}
    assert client.post("/api/preflight", data=request).json()["capabilities"]["temporal"]["status"] == "available"
    body = client.post("/api/analyze", data=request).json()
    assert (body["rows"][0]["Inicial"], body["rows"][0]["Final"]) == (10, 15)
    notes = " ".join(body["notes"])
    assert "premissa governada" in notes and "verificada nos dados" in notes and "pelo usuário para esta execução" not in notes
    assert body["metadata"]["options"]["governed_premises"] == GOVERNED[:2]

    municipal = inspected("density")
    assert [item["option"] for item in municipal["curated_defaults"]["premises"]] == GOVERNED

    def run(operation, **options):
        response = client.post("/api/analyze", data={**form(municipal, operation), "options": json.dumps(options)})
        assert response.status_code == 200, response.text
        return response.json()

    temporal = run("temporal", temporal_indicator="density")
    assert [row["Inicial"] for row in temporal["rows"]] == [6.0, 4.0]  # 6/1000 e 8/2000 por mil habitantes
    assert "Comparabilidade entre territórios" in " ".join(run("comparisons", period_filter="202306")["notes"])
    assert run("ranking", period_filter="202306")["total_rows"] == 2
    total = run("aggregate", period_filter="202306")
    assert total["rows"][0]["Tipo"] == "Soma dos componentes (possível dupla contagem)"
    assert (total["rows"][0]["Quantidade"], total["rows"][0]["População"]) == (14, 3000)
    assert "possível dupla contagem" in " ".join(total["notes"])
    # Outro modo de agregação, escolhido explicitamente, continua prevalecendo.
    unique = run("aggregate", period_filter="202306", no_overlap_confirmed=True)
    assert unique["rows"][0]["Tipo"] == "Unidades distintas: pessoas"
    assert "component_sum_confirmed" not in unique["metadata"]["options"]["governed_premises"]


def test_territorial_identity_premise_requires_evidence_and_imports_use_analysis_premises():
    import pandas as pd
    from brazil_catalog_profile import FIELDS, apply_curated_options, curated_profile, premise_notes
    names = ["A", "A", "B", "B"]
    frame = pd.DataFrame({"municipio": names, "cod_ibge": ["001", "001", "002", "002"],
                          "Período (ano e mês)": ["202306", "202406"] * 2, "categoria_profissional": ["MEDICINA"] * 4,
                          "quantidade": ["6", "10", "8", "12"], "população_estimada": ["1000"] * 2 + ["2000"] * 2,
                          "latitude": ["-10,1"] * 4, "longitude": ["-40,1"] * 4})
    frame.attrs["source"] = {"dataset": "brazil", "scope": "municipal"}
    mapping = dict(FIELDS["municipal"])
    assert apply_curated_options(frame, mapping, {})["governed_premises"] == GOVERNED
    # O mesmo código com dois nomes: a identidade territorial não é afirmada e volta a ser pedida ao usuário.
    renamed = frame.assign(municipio=["A", "A antigo", "B", "B"])
    renamed.attrs["source"] = frame.attrs["source"]
    options = apply_curated_options(renamed, mapping, {})
    assert "territory_longitudinal_confirmed" not in options and "territory_longitudinal_confirmed" not in options["governed_premises"]
    assert [item["option"] for item in curated_profile(renamed, mapping)["premises"]] == [GOVERNED[0], *GOVERNED[2:]]
    assert premise_notes(options, "temporal") == [premise_notes({"governed_premises": GOVERNED}, "temporal")[0]]
    # Arquivo importado com a mesma estrutura: nenhuma premissa do perfil oficial.
    imported = frame.copy()
    imported.attrs = {}
    assert apply_curated_options(imported, mapping, {"temporal_indicator": "quantity"}) == {"temporal_indicator": "quantity"}
    assert premise_notes({"temporal_comparability_confirmed": True}, "temporal") == []
    # D1: na importação, as antigas declarações viram premissas da análise, aplicadas pelos papéis estabelecidos
    # (o código e o período deste quadro sintético são escolhas do usuário), com origem e nota no resultado.
    from analysis_premises import GENERIC, apply_premises, premise_notes as analysis_notes
    chosen = {"temporal_indicator": "quantity", "confirmed_roles": ["territory_id", "period"]}
    applied = apply_premises(imported, mapping, chosen)
    assert applied["analysis_premises"] == [
        "population_denominator_confirmed", "temporal_comparability_confirmed", "territory_longitudinal_confirmed",
        "comparison_confirmed", "population_additive_confirmed", "component_sum_confirmed", "fts_scope_recognized",
        "number_format"]
    assert applied["fts_scope_confirmed"] is True  # MEDICINA reconhecida pelo catálogo da FTS
    assert applied["number_format"] == "decimal_comma"  # vírgula verificada nos dados
    assert not {"governed_roles", "governed_premises"} & set(applied)
    assert GENERIC["territory_longitudinal_confirmed"]["note"] in analysis_notes(applied, "temporal", mapping)
    # Sem distância, o separador não é aplicado; valor explícito (inclusive false) prevalece.
    assert "number_format" not in apply_premises(imported, mapping, chosen, spatial=False)
    refused = apply_premises(imported, mapping, {**chosen, "comparison_confirmed": False})
    assert refused["comparison_confirmed"] is False and "comparison_confirmed" not in refused["analysis_premises"]
    # A verificação nos dados falha com o mesmo código e dois nomes: a premissa de identidade não é aplicada.
    renamed_import = renamed.copy()
    renamed_import.attrs = {}
    assert "territory_longitudinal_confirmed" not in apply_premises(renamed_import, mapping, chosen)
    # Campos do navegador que só o servidor calcula nunca são aceitos.
    assert "governed_roles" not in apply_premises(imported, mapping, {**chosen, "governed_roles": ["count"]})


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
    # A fonte estadual só é lida pela abrangência territorial; não é um recorte do pedido.
    for data in ({"dataset": "../secret"}, {"dataset": "brazil", "scope": "../secret"}, {"dataset": "brazil", "scope": "state"}, {}):
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
