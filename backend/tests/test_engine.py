import pandas as pd
import pytest
from main import compute, suggest, read_dataset


MAP = {"territory": "Territorio", "period": "Ano", "category": "Categoria",
       "count": "Quantidade", "population": "Populacao"}


@pytest.fixture
def table():
    return pd.DataFrame({
        "Territorio": ["A", "B", "A", "B"],
        "Ano": [2023, 2023, 2024, 2024],
        "Categoria": ["Médicos"] * 4,
        "Quantidade": [10, 15, 20, 25],
        "Populacao": [10000, 30000, 10000, 25000],
    })


def test_semantic_aliases():
    assert suggest(["Territorio", "Ano", "Populacao"]) == {
        "territory": "Territorio", "period": "Ano", "population": "Populacao"
    }


def test_density_per_thousand(table):
    out = compute(table, MAP, "density", {})
    items = [r for r in out["rows"] if r["Território"] == "A" and r["Período"] == "2024"]
    assert items[0]["Densidade por 1.000"] == 2.0


def test_aggregate_denominator_not_mean(table):
    out = compute(table, MAP, "aggregate", {"period_filter": "2024", "category_filter": "Médicos",
                                         "population_additive_confirmed": True, "component_sum_confirmed": True})
    assert out["rows"][0]["Densidade por 1.000"] == pytest.approx(45 / 35000 * 1000)
    assert "Soma dos componentes" in out["rows"][0]["Tipo"]


def test_no_implicit_sum_on_ambiguous_duplicates(table):
    frame = pd.concat([table, table.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="várias linhas"):
        compute(frame, MAP, "density", {})


def test_no_implicit_zero(table):
    frame = table.copy()
    frame.loc[0, "Populacao"] = 0
    with pytest.raises(ValueError, match="não positivas"):
        compute(frame, MAP, "density", {})


def test_quantile_ties_are_kept():
    frame = pd.DataFrame({"Territorio": ["A", "B", "C", "D", "E"],
                          "Ano": [2024]*5, "Categoria": ["Med"]*5,
                          "Quantidade": [3, 5, 7, 9, 11]})
    mapping = {k: v for k, v in MAP.items() if k != "population"}
    result = compute(frame, mapping, "distribution", {"quantile_count": 4})
    assert [r["Unidades"] for r in result["rows"]] == [2, 1, 1, 1]


def test_csv_semicolon():
    df, sheets = read_dataset(b"Territorio;Quantidade\nA;10\n", "base.csv")
    assert len(df) == 1
    assert list(df.columns) == ["Territorio", "Quantidade"]


def test_missing_period_requires_confirmation():
    frame = pd.DataFrame({"Territorio": ["A"], "Categoria": ["Med"],
                          "Quantidade": [10]})
    with pytest.raises(ValueError, match="Período"):
        compute(frame, {"territory": "Territorio", "category": "Categoria",
                         "count": "Quantidade"}, "counts", {})
