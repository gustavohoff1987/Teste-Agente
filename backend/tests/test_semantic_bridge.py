"""Regressão da ponte semântica e do gate compartilhado com o motor.

Os exemplos representam estrutura, NÃO dados reais de profissionais.
"""
import io
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from main import app
from semantic_bridge import candidates, normalize_headers, preflight


client = TestClient(app)


def user_frame():
    return pd.DataFrame({
        "0": [1, 2, 3, 4],
        "Competência": [2021, 2022, 2023, 2024],
        "Total de médicos únicos": [50, 60, 66, 72],
    })


def user_file():
    frame = user_frame()
    return (";".join(frame.columns) + "\n" + "\n".join(
        ";".join(map(str, row)) for row in frame.itertuples(index=False, name=None)
    ) + "\n").encode("utf-8")


def test_suggest_names_and_unknown_zero_header():
    # D1: só o reconhecido por regra entra no mapeamento; o padrão "Total de médicos…" fica como sugestão.
    mapping, columns = candidates(user_frame())
    assert mapping == {"period": "Competência"}
    assert columns[0]["suspicious_header"] is True
    assert columns[2]["proposal"][0]["status"] == "proposed"


def test_preflight_count_unit_does_not_follow_name_only():
    frame = user_frame()
    mapping, _ = candidates(frame)
    a = preflight(frame, mapping)
    assert a["field_states"]["period"]["status"] == "recognized"
    assert a["field_states"]["count"]["status"] == "unmapped"  # sugestão não é seleção
    assert a["capabilities"]["counts"]["status"] == "unavailable"
    assert any("Escolha a coluna de quantitativos" in r for r in a["capabilities"]["counts"]["reasons"])
    assert a["capabilities"]["density"]["status"] == "unavailable"
    assert a["capabilities"]["temporal"]["status"] == "unavailable"
    # A escolha da coluna estabelece o papel; a unidade de contagem continua uma escolha.
    chosen = {**mapping, "count": "Total de médicos únicos"}
    b = preflight(frame, chosen, {"confirmed_roles": ["count"], "category_constant": "Médicos"})
    assert b["field_states"]["count"]["status"] == "confirmed"
    assert b["capabilities"]["counts"]["status"] == "needs_confirmation"
    assert any("unidade de contagem" in r for r in b["capabilities"]["counts"]["reasons"])
    c = preflight(frame, chosen, {"confirmed_roles": ["count"], "category_constant": "Médicos", "count_unit": "pessoas"})
    assert c["capabilities"]["counts"]["status"] == "available"


def test_user_chooses_count_and_enables_count_and_temporal_without_territory():
    frame = user_frame()
    mapping, _ = candidates(frame)
    mapping["count"] = "Total de médicos únicos"  # escolha do usuário no seletor
    opts = {
        "confirmed_roles": ["count"],
        "count_unit": "pessoas",
        "category_constant": "Médicos",
        "temporal_indicator": "quantity", "temporal_comparability_confirmed": True,
    }
    matrix = preflight(frame, mapping, opts)
    assert matrix["capabilities"]["counts"]["status"] == "available"
    assert matrix["capabilities"]["temporal"]["status"] == "available"
    assert matrix["capabilities"]["density"]["status"] == "unavailable"

    data = {"file": ("base.csv", user_file())}
    response = client.post("/api/analyze", files=data, data={
        "operation": "temporal", "mapping": json.dumps(mapping),
        "options": json.dumps(opts),
    })
    assert response.status_code == 200, response.text
    assert response.json()["rows"][0]["Inicial"] == 50.0
    assert response.json()["rows"][0]["Final"] == 72.0
    assert response.json()["rows"][0]["Categoria"] == "Médicos"


def test_real_import_and_preflight_http():
    contents = user_file()
    inspected = client.post("/api/inspect", files={"file": ("base.csv", contents)})
    assert inspected.status_code == 200, inspected.text
    profile = inspected.json()
    assert "count" not in profile["suggested_mapping"]  # sugestão no topo do seletor, nunca selecionada
    assert profile["suggested_columns"]["count"] == ["Total de médicos únicos"]
    assert profile["suggested_category_constant"] == "Médicos"
    assert profile["column_profiles"][0]["name"] == "0"
    assert profile["preflight"]["capabilities"]["counts"]["status"] == "unavailable"
    response = client.post("/api/preflight", files={"file": ("base.csv", contents)}, data={
        "mapping": json.dumps({**profile["suggested_mapping"], "count": "Total de médicos únicos"}),
        "options": json.dumps({
            "confirmed_roles": ["count"], "count_unit": "pessoas",
            "category_constant": "Médicos",
        }),
    })
    assert response.status_code == 200, response.text
    assert response.json()["capabilities"]["counts"]["status"] == "available"
    assert response.json()["capabilities"]["temporal"]["status"] == "needs_confirmation"


def test_gate_prevents_unconfirmed_calculation():
    mapping, _ = candidates(user_frame())
    result = client.post("/api/analyze", files={"file": ("base.csv", user_file())}, data={
        "operation": "counts", "mapping": json.dumps(mapping), "options": "{}",
    })
    assert result.status_code == 422
    assert "não habilitada" in result.json()["detail"]


def test_non_health_category_not_assumed_from_semantic_similarity():
    frame = pd.DataFrame({"Categoria": ["Médico veterinário"], "Quantidade": [2], "Ano": [2024]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas"})
    assert gate["capabilities"]["counts"]["status"] == "needs_confirmation"
    assert any("força de trabalho" in item for item in gate["capabilities"]["counts"]["reasons"])


def test_empty_non_health_category_requires_fts_declaration():
    frame = pd.DataFrame({"Categoria": ["Eletricistas"], "Quantidade": [2], "Ano": [2024]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas"})
    assert gate["capabilities"]["counts"]["status"] == "needs_confirmation"


def test_numeric_zero_header_has_same_key_during_inspect_and_analysis():
    df = pd.DataFrame({0: ["X", "Y"], "Competência": [2023, 2024], "Quantidade": [4, 5]})
    normalized = normalize_headers(df)
    assert list(normalized.columns) == ["0", "Competência", "Quantidade"]
    mapping, _ = candidates(normalized)
    mapping["territory"] = "0"
    gate = preflight(normalized, mapping, {
        "confirmed_roles": ["territory"], "count_unit": "vinculos",
        "fts_scope_confirmed": True,
    })
    assert gate["field_states"]["territory"]["status"] == "confirmed"
    assert gate["capabilities"]["counts"]["status"] == "available"


def test_cannot_map_same_column_as_two_roles():
    frame = user_frame()
    with pytest.raises(ValueError, match="mesma coluna"):
        preflight(frame, {"territory": "Competência", "period": "Competência"})


def test_temporal_not_available_with_single_period():
    frame = pd.DataFrame({"Ano": [2024], "Categoria": ["Médicos"], "Quantidade": [5]})
    mapping, _ = candidates(frame)
    gate = preflight(frame, mapping, {"count_unit": "pessoas",
                                      "temporal_indicator": "quantity", "temporal_comparability_confirmed": True})
    assert gate["capabilities"]["temporal"]["status"] == "unavailable"


def test_xlsx_numeric_header_is_normalized():
    wb = Workbook()
    ws = wb.active
    ws.append([0, "Competência", "Total de médicos únicos"])
    ws.append([1, 2024, 5])
    buffer = io.BytesIO()
    wb.save(buffer)
    response = client.post("/api/inspect", files={"file": ("teste.xlsx", buffer.getvalue())})
    assert response.status_code == 200, response.text
    assert response.json()["columns"][0] == "0"


def test_out_of_range_coordinate_does_not_demote_the_column():
    # RQ-DAD-25: valor fora do intervalo não rebaixa a coluna; o elemento é que fica inválido. Na análise espacial, só
    # aquele território fica não avaliável; como referência, ele impede a análise com um motivo claro.
    frame = pd.DataFrame({"Território": ["A", "B"], "Latitude": [110, -3.1], "Longitude": [-48.0, -60.0]})
    mapping, profiles = candidates(frame)
    assert mapping["latitude"] == "Latitude"
    assert "fora do intervalo" in profiles[1]["proposal"][0]["evidence"]
    matrix = preflight(frame, mapping, {"crs": "SIRGAS2000", "reference_territory": "A"})
    assert matrix["field_states"]["latitude"]["status"] == "recognized"
    assert matrix["capabilities"]["spatial"]["status"] == "unavailable"
    assert any("referência não tem coordenada válida" in r for r in matrix["capabilities"]["spatial"]["reasons"])
    assert preflight(frame, mapping, {"crs": "SIRGAS2000", "reference_territory": "B"})["capabilities"]["spatial"]["status"] == "available"


def test_report_without_population_is_quantitative_not_density():
    frame = user_frame()
    mapping, _ = candidates(frame)
    mapping["count"] = "Total de médicos únicos"  # escolha do usuário
    opts = {"confirmed_roles": ["count"], "count_unit": "pessoas", "category_constant": "Médicos", "report_indicator": "quantity"}
    response = client.post("/api/analyze", files={"file": ("base.csv", user_file())}, data={
        "mapping": json.dumps(mapping), "options": json.dumps(opts), "operation": "report",
    })
    assert response.status_code == 200, response.text
    row = response.json()["rows"][0]
    assert "Densidade por 1.000" not in row


def test_geographic_region_is_a_suggestion_until_chosen():
    frame = pd.DataFrame({
        "Região Geográfica": ["Norte", "Sul"],
        "Competência": [2024, 2024],
        "Total de médicos únicos": [10, 20],
    })
    mapping, profile = candidates(frame)
    assert mapping == {"period": "Competência"}  # região e padrão de contagem ficam como sugestões
    assert profile[0]["proposal"][0] == {"role": "territory", "status": "proposed",
        "evidence": "Expressão geográfica sugerida; escolha a coluna para usá-la como unidade territorial"}
    # Indicada só pela API, sem escolha: continua bloqueada (sugestão não é seleção).
    indicated = {**mapping, "territory": "Região Geográfica", "count": "Total de médicos únicos"}
    gate = preflight(frame, indicated)
    assert gate["field_states"]["territory"]["status"] == "proposed"
    assert gate["capabilities"]["density"]["status"] != "available"
    assert any("Escolha a coluna de Território no seletor" in r for r in gate["capabilities"]["density"]["reasons"])
    chosen = preflight(frame, indicated, {"confirmed_roles": ["territory"]})
    assert chosen["field_states"]["territory"]["status"] == "confirmed"


def test_informed_object_establishes_the_object_without_confirmation():
    frame = pd.DataFrame({
        "Região Geográfica": ["Norte", "Sul"],
        "Competência": [2024, 2024],
        "Quantidade": [10, 20],
        "População": [10000, 20000],
    })
    mapping, _ = candidates(frame)
    mapping["territory"] = "Região Geográfica"  # escolha do usuário
    opts = {
        "confirmed_roles": ["territory"],
        "count_unit": "pessoas",
        "population_denominator_confirmed": True,
    }
    first = preflight(frame, mapping, opts)
    assert first["object"] == {"status": "ausente", "origin": None}
    assert first["capabilities"]["density"]["status"] == "needs_confirmation"
    assert any("Informe o objeto de análise" in r for r in first["capabilities"]["density"]["reasons"])
    assert any(r["status"] == "needs_confirmation" and r["title"] == "Objeto de análise" and r["kind"] == "escolha"
               for r in first["capabilities"]["density"]["requirements"])
    # O texto informado é o objeto: nenhuma confirmação; as chaves antigas da API são ignoradas pelo motor.
    for informed in ({"category_constant": "Médicos"},
                     {"category_constant": "Médicos", "require_object_confirmation": True, "object_confirmed": False}):
        ready = preflight(frame, mapping, {**opts, **informed})
        assert ready["object"]["status"] == "reconhecido"
        assert ready["capabilities"]["density"]["status"] == "available"
        assert ready["capabilities"]["density"]["reasons"] == []
        assert all(item["status"] == "met" for item in ready["capabilities"]["density"]["requirements"])
    # Objeto fora do catálogo: informado por você, com nota de premissa no resultado.
    other = preflight(frame, mapping, {**opts, "category_constant": "Agentes de vigilância"})
    assert other["object"] == {"status": "informado", "origin": "DECLARADA_PELO_USUARIO"}
    assert other["capabilities"]["density"]["status"] == "available"
    body = client.post("/api/analyze", files={"file": ("base.csv", frame.to_csv(index=False).encode())}, data={
        "operation": "density", "mapping": json.dumps(mapping),
        "options": json.dumps({**opts, "category_constant": "Agentes de vigilância"})})
    assert body.status_code == 200, body.text
    assert "fts_scope_confirmed" in body.json()["metadata"]["options"]["analysis_premises"]
    assert any("pertença à força de trabalho em saúde não reconhecida" in note for note in body.json()["notes"])
    # Recusa explícita da premissa continua bloqueando (valor explícito prevalece).
    refused = preflight(frame, mapping, {**opts, "category_constant": "Agentes de vigilância", "fts_scope_confirmed": False})
    assert refused["capabilities"]["density"]["status"] == "needs_confirmation"
    assert any("foi recusada" in r for r in refused["capabilities"]["density"]["reasons"])


def test_population_absence_is_visible_as_red_checklist_requirement():
    frame = pd.DataFrame({
        "Região Geográfica": ["Norte", "Sul"],
        "Competência": [2024, 2024],
        "Quantidade": [10, 20],
    })
    mapping, _ = candidates(frame)
    mapping["territory"] = "Região Geográfica"  # escolha do usuário (a região é só sugestão)
    opts = {
        "confirmed_roles": ["territory"],
        "count_unit": "pessoas",
        "category_constant": "Médicos",
        "require_object_confirmation": True,
        "object_confirmed": True,
    }
    gate = preflight(frame, mapping, opts)["capabilities"]["density"]
    assert gate["status"] == "unavailable"
    assert any(item["status"] == "missing" and item["title"] == "Dados populacionais"
               for item in gate["requirements"])
    assert any(item["status"] == "met" and item["title"] == "Unidade territorial"
               for item in gate["requirements"])
