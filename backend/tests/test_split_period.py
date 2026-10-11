"""Regressão de importação, confirmação e rastreabilidade de ano/mês."""
import io
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import llm_bridge
from dataset_normalization import compose_period
from main import app, read_dataset
from semantic_bridge import candidates


client = TestClient(app)
HEADERS = ["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"]
ROWS = [["Brasil", 2023, 12, "MEDICINA", 100], ["Brasil", 2024, 1, "MEDICINA", 120]]


def source(extension="csv", rows=None):
    rows = ROWS if rows is None else rows
    if extension == "csv":
        return "\n".join(";".join(map(str, r)) for r in [HEADERS, *rows]).encode()
    book = Workbook()
    for row in [HEADERS, *rows]:
        book.active.append(row)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


@pytest.mark.parametrize("extension", ["csv", "xlsx"])
def test_split_period_import_confirmation_filter_and_temporal(extension):
    raw = source(extension)
    files = {"file": ("base." + extension, raw)}
    info = client.post("/api/inspect", files=files).json()
    mapping = info["suggested_mapping"]
    assert mapping == {"territory": "pais", "period": "Período (ano e mês)",
                       "category": "categoria_profissional", "count": "contagem"}
    assert info["columns"][:5] == HEADERS
    assert info["periods"] == ["202312", "202401"]
    assert info["preflight"]["field_states"]["period"]["status"] == "proposed"
    assert info["derived_fields"][0]["source_columns"] == ["periodo_ano", "periodo_mes"]
    options = {"count_unit": "pessoas", "temporal_indicator": "quantity", "temporal_comparability_confirmed": True,
               "territory_longitudinal_confirmed": True}

    def analyze(operation):
        return client.post("/api/analyze", files=files, data={"operation": operation,
            "mapping": json.dumps(mapping), "options": json.dumps(options)})

    assert analyze("counts").status_code == 422
    options["confirmed_roles"] = ["period"]
    result = analyze("temporal")
    assert result.status_code == 200, result.text
    row = result.json()["rows"][0]
    assert (row["Território"], row["Período inicial"], row["Período final"]) == ("Brasil", "202312", "202401")
    assert row["Inicial"] == 100 and row["Final"] == 120 and row["Variação (%)"] == 20
    assert result.json()["metadata"]["derived_fields"] == info["derived_fields"]
    options["period_filter"] = "202401"
    filtered = analyze("counts")
    assert filtered.status_code == 200
    assert filtered.json()["total_rows"] == 1
    assert filtered.json()["rows"][0]["Quantidade"] == 120
    assert analyze("temporal").status_code == 422


@pytest.mark.parametrize("year,month", [(2024, 0), (2024, 13), (2024, 1.5), (2024, ""),
                                        (2024, "junho"), ("", 1), (2024.5, 1), ("inf", 1)])
def test_invalid_components_do_not_create_a_plausible_period(year, month):
    response = client.post("/api/inspect", files={"file": ("base.csv", source(rows=[
        ["Brasil", year, month, "MEDICINA", 10]]))})
    assert response.status_code == 422
    assert "inteiros" in response.json()["detail"]


def test_original_columns_are_unchanged_and_existing_period_is_not_overwritten():
    original = pd.DataFrame(ROWS, columns=HEADERS)
    original["Período (ano e mês)"] = ["original", "preservado"]
    original["Competência"] = ["202312", "202401"]
    snapshot = original.copy(deep=True)
    prepared = compose_period(original)
    pd.testing.assert_frame_equal(original, snapshot)
    pd.testing.assert_frame_equal(prepared[original.columns], snapshot)
    assert prepared["Período (ano e mês) 2"].tolist() == ["202312", "202401"]
    assert candidates(prepared)[0]["period"] == "Competência"


def test_incomplete_or_ambiguous_components_are_not_combined():
    frame = pd.DataFrame({"periodo_ano": [2024], "periodo_mes": [1], "Período Mês": [6]})
    assert compose_period(frame) is frame
    incomplete = frame[["periodo_ano"]]
    assert compose_period(incomplete) is incomplete


def test_new_territory_code_alias_still_requires_confirmation_and_preserves_zero():
    frame, _ = read_dataset(b"municipio;cod_ibge;periodo_ano;periodo_mes\nA;001234;2024;6", "test.csv")
    mapping, profiles = candidates(frame)
    assert mapping["territory"] == "municipio" and mapping["territory_id"] == "cod_ibge"
    assert frame.cod_ibge.iloc[0] == "001234"
    profile = next(p for p in profiles if p["name"] == "cod_ibge")
    assert profile["proposal"][0]["status"] == "proposed"


def test_contextual_agent_uses_composed_period_without_sending_source(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "test-only")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    sent = []

    async def provider(payload, model, key):
        sent.append(json.dumps(payload, ensure_ascii=False))
        return {"intent": "ANALITICO", "topic": "none", "operation": "counts", "indicator": "quantity", "period": "202401",
                "category": "", "territory": ""}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    raw = source()
    info = client.post("/api/inspect", files={"file": ("base.csv", raw)}).json()
    result = client.post("/api/llm/interpret-context", files={"file": ("base.csv", raw)}, data={
        "message": "Quero quantitativos em 202401", "mapping": json.dumps(info["suggested_mapping"]),
        "options": json.dumps({"confirmed_roles": ["period"], "count_unit": "pessoas"})})
    assert result.status_code == 200, result.text
    assert result.json()["verification"]["slots"]["period"] == "found_in_dataset"
    assert result.json()["verification"]["capability_status"] == "available"
    assert sent and all(value not in sent[0] for value in ["periodo_ano", "periodo_mes", "Brasil", "MEDICINA"])
