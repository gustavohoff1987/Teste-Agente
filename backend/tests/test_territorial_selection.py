import copy
import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, compute
from semantic_bridge import preflight
from territorial_selection import territory_catalog
from exploration import interpret_exploration


MAP = {"territory": "municipio", "territory_id": "codigo_identificador", "period": "periodo",
       "category": "categoria_profissional", "count": "quantidade", "population": "populacao"}
OPTIONS = {"confirmed_roles": list(MAP), "count_unit": "pessoas", "population_denominator_confirmed": True,
           "comparison_confirmed": True, "temporal_comparability_confirmed": True,
           "territory_longitudinal_confirmed": True, "temporal_indicator": "quantity"}


@pytest.fixture
def frame():
    return pd.DataFrame([
        {"municipio": name, "codigo_identificador": code, "periodo": period, "categoria_profissional": "MEDICINA",
         "quantidade": quantity + offset, "populacao": pop}
        for period, offset in [("202301", 0), ("202306", 2), ("202401", 3), ("202406", 5)]
        for name, code, quantity, pop in [("Manaus", "130260", 10, 1000), ("Tefé", "130420", 5, 2000),
                                         ("Parintins", "130340", 7, 4000), ("Fora", "X04", 1000, 10000)]
    ])


def chosen(**extra):
    return {**OPTIONS, "territory_ids": ["code:130260", "code:130420", "code:130340"], **extra}


def test_selection_precedes_density_counts_ranking_distribution(frame):
    for operation in ("density", "counts", "ranking", "distribution"):
        result = compute(frame, MAP, operation, chosen(period_filter="202406", distribution_indicator="quantity"))
        rows = result.get("detail_rows", result["rows"])
        assert len(rows) == 3
        assert all("Fora" not in str(row) for row in rows)
        assert len(result["metadata"]["universe"]["members"]) == 3
        assert result["metadata"]["universe"]["classification_scope"] == "subconjunto selecionado"
    density = compute(frame, MAP, "density", chosen(period_filter="202406"))
    assert [r["Densidade por 1.000"] for r in density["rows"]] == [15, 5, 3]


@pytest.mark.parametrize("ids", [[], "130260", ["code:missing"], ["code:130260", "code:130260"], [None]])
def test_invalid_selections_are_not_silently_ignored(frame, ids):
    with pytest.raises(ValueError):
        compute(frame, MAP, "counts", {**OPTIONS, "territory_ids": ids})


def test_no_selection_preserves_full_base_and_inputs_are_immutable(frame):
    original = frame.copy(deep=True)
    options = chosen(period_filter="202406")
    before = copy.deepcopy(options)
    selected = compute(frame, MAP, "counts", options)
    entire = compute(frame, MAP, "counts", {**OPTIONS, "period_filter": "202406"})
    assert len(selected["rows"]) == 3 and len(entire["rows"]) == 4
    pd.testing.assert_frame_equal(frame, original)
    assert options == before


def test_comparison_quantity_without_population_and_density(frame):
    two = chosen(period_filter="202406", territory_ids=["code:130260", "code:130420"])
    density = compute(frame, MAP, "comparisons", two)["rows"][0]
    assert density["Diferença A − B"] == 10
    mapping = {k: v for k, v in MAP.items() if k != "population"}
    quantity = compute(frame, mapping, "comparisons", {**two, "comparison_indicator": "quantity"})["rows"][0]
    assert quantity["Diferença A − B"] == 5
    assert quantity["Indicador"] == "Quantidade"
    assert preflight(frame, mapping, {**two, "comparison_indicator": "quantity"})["capabilities"]["comparisons"]["status"] == "available"


def test_aggregation_keeps_component_sum_distinct_from_unique_people(frame):
    opts = chosen(period_filter="202406")
    with pytest.raises(ValueError, match="populações"):
        compute(frame, MAP, "aggregate", opts)
    with pytest.raises(ValueError, match="sobreposição"):
        compute(frame, MAP, "aggregate", {**opts, "population_additive_confirmed": True})
    result = compute(frame, MAP, "aggregate", {**opts, "population_additive_confirmed": True, "component_sum_confirmed": True})
    row = result["rows"][0]
    assert row["Quantidade"] == 37 and row["População"] == 7000
    assert row["Densidade por 1.000"] == pytest.approx(37 / 7)
    assert "possível dupla contagem" in row["Tipo"]


def test_temporal_selected_periods_and_missing_endpoints(frame):
    result = compute(frame, MAP, "temporal", chosen())
    assert len(result["rows"]) == 3 and len(result["detail_rows"]) == 12
    assert all(row["Variação absoluta"] == 5 for row in result["rows"])
    assert all(row["Tendência"] == "Crescimento" for row in result["rows"])
    two = compute(frame, MAP, "temporal", chosen(period_filters=["202301", "202406"]))
    assert all("Não avaliável" in row["Tendência"] for row in two["rows"])
    partial = frame[~((frame.municipio == "Tefé") & (frame.periodo == "202301"))]
    output = compute(partial, MAP, "temporal", chosen())
    tefe = next(row for row in output["rows"] if row["Território"].startswith("Tefé"))
    assert tefe["Inicial"] is None and tefe["Variação absoluta"] is None


def test_missing_members_period_category_and_ambiguous_identity(frame):
    for patch in ({"period_filter": "209906"}, {"category_filter": "ENFERMAGEM"}):
        with pytest.raises(ValueError):
            compute(frame, MAP, "counts", chosen(**patch))
    partial = frame[~((frame.municipio == "Tefé") & (frame.periodo == "202406"))]
    with pytest.raises(ValueError, match="Não avaliável"):
        compute(partial, MAP, "counts", chosen(period_filter="202406"))
    ambiguous = frame.copy()
    ambiguous.loc[ambiguous.municipio == "Tefé", "codigo_identificador"] = "130260"
    with pytest.raises(ValueError, match="ambíguo"):
        compute(ambiguous, MAP, "counts", chosen())


def test_imported_identifiers_are_opaque_and_names_work_without_ibge(frame):
    items = territory_catalog(frame, MAP, OPTIONS)
    assert any(item["id"] == "code:X04" for item in items)
    assert all(item["state"] == "" for item in items)  # Upload nunca ganha perfil Brasil.
    mapping = {k: v for k, v in MAP.items() if k != "territory_id"}
    out = compute(frame, mapping, "counts", {**OPTIONS, "territory_ids": ["name:Tefé"], "period_filter": "202406"})
    assert out["rows"][0]["Quantidade"] == 10
    ambiguous = frame.copy()
    ambiguous["UF"] = ["AM", "AM", "AM", "XX"] * 4
    ambiguous.loc[ambiguous.municipio == "Fora", "municipio"] = "Tefé"
    with pytest.raises(ValueError, match="ambígua"):
        territory_catalog(ambiguous, mapping, OPTIONS)


def test_local_interpretation_uses_verified_names_and_does_not_execute(frame):
    parsed = interpret_exploration("Compare Manaus e Tefé em junho de 2024.", frame, MAP, OPTIONS)
    assert parsed["executed"] is False
    assert set(parsed["territory_ids"]) == {"code:130260", "code:130420"}
    assert parsed["options_patch"]["period_filter"] == "202406"
    selected = interpret_exploration("Mostre a evolução dos municípios selecionados.", frame, MAP, chosen())
    assert selected["operation"] == "temporal" and len(selected["territory_ids"]) == 3
    assert "clarification" in interpret_exploration("Compare Manaus e Inexistente", frame, MAP, OPTIONS)
    assert "clarification" in interpret_exploration("Compare os selecionados", frame, MAP, OPTIONS)


def test_selection_rejects_related_territorial_levels(frame):
    frame = frame.copy()
    frame.loc[frame.municipio == "Fora", "municipio"] = "Amazonas"
    frame["territorio_superior_1"] = frame.municipio.map(lambda name: "Brasil" if name == "Amazonas" else "Amazonas")
    opts = chosen(period_filter="202406", territory_ids=["code:130260", "code:X04"])
    for operation in ("comparisons", "aggregate"):
        with pytest.raises(ValueError, match="nível superior"):
            compute(frame, MAP, operation, opts)


def test_homonyms_require_codes_in_conversational_resolution(frame):
    frame = frame.copy()
    frame.loc[frame.municipio == "Fora", "municipio"] = "Tefé"
    assert "homônimos" in interpret_exploration("Compare Manaus e Tefé", frame, MAP, OPTIONS)["clarification"]
    assert len(compute(frame, MAP, "counts", chosen(period_filter="202406"))["rows"]) == 3


def test_unrelated_hierarchy_conflict_does_not_block_valid_selection(frame):
    frame = frame.copy()
    frame["uf"] = "AM"
    frame.loc[(frame.municipio == "Fora") & (frame.periodo == "202406"), "uf"] = "PA"
    choices = territory_catalog(frame, MAP, OPTIONS)
    assert next(item for item in choices if item["id"] == "code:X04")["selection_reason"]
    assert len(compute(frame, MAP, "counts", chosen())["rows"]) == 12
    with pytest.raises(ValueError, match="ambígua"):
        compute(frame, MAP, "counts", chosen(territory_ids=["code:X04"]))


def test_short_territory_names_do_not_capture_generic_conversation(frame):
    frame = frame.copy()
    frame.loc[frame.municipio == "Manaus", "municipio"] = "A"
    assert interpret_exploration("Quero analisar a densidade", frame, MAP, OPTIONS) == {"handled": False}
    assert interpret_exploration("Compare A e Tefé", frame, MAP, OPTIONS)["operation"] == "comparisons"


def test_api_has_unique_results_and_reproducible_execution_key(frame):
    client = TestClient(app)
    source = {"file": ("controlado.csv", frame.to_csv(index=False).encode())}
    data = {"operation": "counts", "mapping": json.dumps(MAP), "options": json.dumps(chosen(period_filter="202406"))}
    first = client.post("/api/analyze", files=source, data=data)
    second = client.post("/api/analyze", files=source, data=data)
    assert first.status_code == second.status_code == 200
    a, b = first.json(), second.json()
    assert a["result_id"] != b["result_id"]
    assert a["metadata"]["execution_key"] == b["metadata"]["execution_key"]
    assert a["metadata"]["data_sha256"] and a["metadata"]["validity"] == "VALIDO"
    assert len(a["metadata"]["universe"]["members"]) == 3
    data["options"] = json.dumps(chosen(territory_ids=[]))
    assert client.post("/api/analyze", files=source, data=data).status_code == 422
