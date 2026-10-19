"""CAP-TEN-01 (tendência, DA-15) e CAP-TMP-01 (mudança, DA-14) em aritmética exata, sem dados reais.

Casos da SPEC: AT-53 (classes e normalização pelo tempo), AT-10 (sem classificação é resultado), AT-09 (dois
períodos: mudança, não tendência), AT-69/AT-80 (agregado não comparável sem trajetória), AT-18 (não avaliáveis
separados) e a regressão do float (densidade em float criaria acelerações espúrias).
"""
import json
import random
from fractions import Fraction

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from main import app, compute
from temporal_change import change, evolution
from trend import (CLASSES, LABELS, METHOD_VERSION, TEXT_BLOCKED, classify, classify_frame, classify_speeds, density,
                   exact, stage_block, summarize, time_unit)

ANNUAL = [2018, 2019, 2020, 2021]
client = TestClient(app)


def annual(values, years=ANNUAL):
    return classify([(str(y), y, v) for y, v in zip(years, values)])


# AT-53 (L2346): séries anuais
@pytest.mark.parametrize("values,category,motive", [
    ((10, 11, 12, 14), "CRESCIMENTO_ACELERADO", None),
    ((10, 12, 14, 16), "CRESCIMENTO", None),
    ((10, 14, 16, 17), "CRESCIMENTO_DESACELERADO", None),
    ((20, 18, 15, 11), "DECLINIO_ACELERADO", None),
    ((20, 12, 8, 6), "DECLINIO_DESACELERADO", None),
    ((20, 18, 16, 14), "DECLINIO", None),
    ((10, 12, 12, 15), "CRESCIMENTO", None),           # intervalo com velocidade zero
    ((20, 18, 18, 15), "DECLINIO", None),             # idem, no declínio
    ((10, 12, 15, 17), "CRESCIMENTO", None),           # ritmo sem monotonicidade
    ((10, 12, 11, 13), "SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO"),
    ((5, 5, 5, 5), "SEM_CLASSIFICACAO", "SERIE_ESTAVEL"),
])
def test_at53_classes(values, category, motive):
    trend = annual(values)
    assert (trend.evaluability, trend.category, trend.motive) == ("AVALIAVEL", category, motive)
    assert trend.label == LABELS[category]
    assert trend.method_version == METHOD_VERSION
    assert [o.value for o in trend.observations] == [Fraction(v) for v in values]


def test_at53_three_observations_not_evaluable():
    trend = annual((10, 11, 12), ANNUAL[:3])
    assert (trend.evaluability, trend.not_evaluable, trend.category) == ("NAO_AVALIAVEL", "SERIE_INSUFICIENTE", None)
    assert trend.label == "Não avaliável: série insuficiente" and trend.intervals == ()
    assert trend.row()["Motivo da tendência"] == "3 de 4 observações necessárias"


def test_at53_elapsed_time_normalization():
    trend = annual((10, 12, 16, 18), [2018, 2019, 2021, 2022])
    assert [i.speed for i in trend.intervals] == [2, 2, 2] and trend.category == "CRESCIMENTO"
    assert [i.elapsed for i in trend.intervals] == [1, 2, 1]


def test_monthly_positions_and_exact_density():
    # Competências AAAAMM alternando 5 e 7 meses (base Brasil): a velocidade é por mês, exata.
    points = [("202301", 2023 * 12, 10), ("202306", 2023 * 12 + 5, 12), ("202401", 2024 * 12, 15), ("202406", 2024 * 12 + 5, 16)]
    trend = classify(points)
    assert [i.speed for i in trend.intervals] == [Fraction(2, 5), Fraction(3, 7), Fraction(1, 5)]
    assert trend.category == "CRESCIMENTO"   # 0,4 < 0,4286 > 0,2: sem monotonicidade
    assert density(502495, 212583750) == Fraction(502495000, 212583750)
    assert exact(0.1) == Fraction(1, 10) and exact(12.0) == 12
    assert (time_unit("yyyymm"), time_unit("date"), time_unit("numeric")) == ("mês", "dia", "unidade do período")


def test_float_rounding_does_not_fake_acceleration():
    # Quantidades 0, 1, 2, 3 e população 3: densidades 0; 333,33…; 666,66…; 1.000, velocidade constante.
    # Em float (quantity / population * 1000, data_contract.prepare) as diferenças saem 333,3333333333333,
    # 333,3333333333333 e 333,33333333333337: "Aceleração do crescimento" espúria.
    floats = [q / 3 * 1000 for q in (0, 1, 2, 3)]
    assert classify_speeds([Fraction(b) - Fraction(a) for a, b in zip(floats, floats[1:])])[0] == "CRESCIMENTO_ACELERADO"
    exact_points = [(str(y), y, density(q, 3)) for y, q in zip(ANNUAL, (0, 1, 2, 3))]
    assert classify(exact_points).category == "CRESCIMENTO"
    decimals = classify([(str(y), y, v) for y, v in zip(ANNUAL, (0.0, 0.1, 0.2, 0.3))])
    assert decimals.category == "CRESCIMENTO"  # exact(float) usa o decimal mais curto, não a expansão binária


def test_float_regression_through_the_engine():
    """Pela análise: densidade exata (quantidade × 1.000 / população), não a coluna float do motor."""
    frame = pd.DataFrame({"Municipality": ["A"] * 4, "Year": ANNUAL, "Profession": ["Nurses"] * 4,
                          "Count": [0, 1, 2, 3], "Population": [3] * 4})
    response = client.post("/api/analyze", files={"file": ("float.csv", frame.to_csv(index=False).encode())}, data={
        "operation": "temporal", "mapping": json.dumps({"territory": "Municipality", "period": "Year", "category": "Profession",
                                                        "count": "Count", "population": "Population"}),
        "options": json.dumps({"count_unit": "pessoas", "population_denominator_confirmed": True,
                               "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True,
                               "temporal_indicator": "density"})})
    assert response.status_code == 200, response.text
    body = response.json()
    row = body["rows"][0]
    assert row["Tendência"] == "Crescimento" and row["Observações da tendência"] == 4
    assert body["metadata"]["tendencia"]["contagens"]["CRESCIMENTO_ACELERADO"] == 0
    assert body["metadata"]["tendencia"]["unidades"][0]["velocidades"] == [1000 / 3] * 3
    # Base zero: direção e variação absoluta calculadas, variação percentual não avaliável.
    assert row["Variação (%)"] is None and row["Direção da mudança"] == "Aumento"
    assert row["Condição da mudança"] == "Avaliável; variação percentual não avaliável: base zero"
    assert body["metadata"]["mudanca"]["percentual_nao_avaliavel"] == {"BASE_ZERO": 1}
    assert any(note.startswith("Variação (%) não avaliável quando o valor inicial é zero") for note in body["notes"])


# AT-10 (L2256): SEM_CLASSIFICACAO é resultado, com trajetória e velocidades
def test_at10_without_class_keeps_trajectory_and_speeds():
    trend = annual((10, 12, 11, 13))
    assert trend.category == "SEM_CLASSIFICACAO" and trend.motive == "MUDANCA_DE_DIRECAO"
    assert [i.speed for i in trend.intervals] == [2, -1, 2]
    record = trend.structured()
    assert record["avaliabilidade"] == "AVALIAVEL" and record["motivo_nao_avaliavel"] is None
    assert [v["exata"] for v in record["velocidades"]] == ["2", "-1", "2"]
    assert "Não avaliável" not in trend.row()["Tendência"]  # compute não pode tratá-la como limitação
    summary = summarize([trend, annual((5, 5, 5, 5))])
    assert summary["desfecho"] == "RES-SCL" and summary["avaliaveis"] == 2
    assert summary["sem_classificacao_por_motivo"] == {"MUDANCA_DE_DIRECAO": 1, "SERIE_ESTAVEL": 1}


def test_summary_counts_come_from_engine():
    trends = [annual(v) for v in ((10, 11, 12, 14), (10, 12, 14, 16), (20, 12, 8, 6), (10, 12, 11, 13))]
    trends.append(annual((1, 2, 3), ANNUAL[:3]))
    summary = summarize(trends)
    assert list(summary["contagens"]) == list(CLASSES)
    assert summary["contagens"]["CRESCIMENTO_ACELERADO"] == 1 and summary["familias"] == {
        "CRESCIMENTO": 2, "DECLINIO": 1, "NENHUMA": 1}
    # AT-18: não avaliáveis à parte, por motivo, fora das classes.
    assert summary["nao_avaliaveis_por_motivo"] == {"SERIE_INSUFICIENTE": 1, "INCOMPARABILIDADE": 0}
    assert (summary["avaliaveis"], summary["nao_avaliaveis"], summary["unidades_total"]) == (4, 1, 5)
    assert summary["desfecho"] == "RES-LIM"
    assert summarize(trends[:2])["desfecho"] == "RES-VAL"


# AT-09 (L2254): dois períodos → mudança, não tendência
def test_at09_two_periods_change_and_stage_block():
    block = stage_block(2)
    assert block["desfecho"] == "BLQ-MET" and block["motivo"] == "SERIE_INSUFICIENTE"
    assert block["texto"] == TEXT_BLOCKED.format(quantidade=2)
    assert stage_block(4) is None
    assert change(0, 5) == {"variacao_absoluta": 5, "variacao_percentual": None, "direcao": "AUMENTO",
                            "rotulo_direcao": "Aumento", "motivo_percentual": "BASE_ZERO"}
    assert change(0, 0)["direcao"] == "SEM_MUDANCA" and change(0, 0)["motivo_percentual"] == "BASE_ZERO"
    gone = change(5, 0)
    assert (gone["direcao"], gone["variacao_absoluta"], gone["variacao_percentual"]) == ("REDUCAO", -5, -100)
    assert summarize([annual((1, 2), ANNUAL[:2])], block=block)["desfecho"] == "BLQ-MET"


def test_at09_through_the_engine_keeps_change_and_blocks_trend():
    frame = pd.DataFrame({"Municipality": ["A", "A", "B", "B", "C", "C"], "Year": [2023, 2024] * 3,
                          "Profession": ["Nurses"] * 6, "Count": [0, 5, 0, 0, 5, 0]})
    result = compute(frame, {"territory": "Municipality", "period": "Year", "category": "Profession", "count": "Count"},
                     "temporal", {"count_unit": "pessoas", "temporal_indicator": "quantity",
                                  "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True})
    rows = {row["Território"]: row for row in result["rows"]}
    assert [rows[k]["Direção da mudança"] for k in "ABC"] == ["Aumento", "Sem mudança", "Redução"]
    assert [rows[k]["Variação absoluta"] for k in "ABC"] == [5, 0, -5]
    assert [rows[k]["Variação (%)"] for k in "ABC"] == [None, None, -100]
    assert all(row["Tendência"] == "Não avaliável: série insuficiente" for row in result["rows"])
    assert all(row["Motivo da tendência"] == "2 de 4 observações necessárias" for row in result["rows"])
    tendencia = result["metadata"]["tendencia"]
    assert tendencia["desfecho"] == "BLQ-MET" and tendencia["bloqueio"]["periodos_distintos"] == 2
    assert result["metadata"]["mudanca"]["direcoes"] == {"AUMENTO": 1, "REDUCAO": 1, "SEM_MUDANCA": 1}
    assert any(note.startswith(TEXT_BLOCKED.format(quantidade=2) + " A análise de tendência exige quatro observações")
               for note in result["notes"])


def test_at10_through_the_engine_is_without_class_not_missing_data():
    frame = pd.DataFrame({"Municipality": ["A"] * 4 + ["B"] * 4, "Year": ANNUAL * 2, "Profession": ["Nurses"] * 8,
                          "Count": [10, 12, 11, 13, 5, 5, 5, 5]})
    result = compute(frame, {"territory": "Municipality", "period": "Year", "category": "Profession", "count": "Count"},
                     "temporal", {"count_unit": "pessoas", "temporal_indicator": "quantity",
                                  "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True})
    rows = {row["Território"]: row for row in result["rows"]}
    assert (rows["A"]["Tendência"], rows["A"]["Motivo da tendência"]) == ("Sem classificação", "Mudança de direção")
    assert (rows["B"]["Tendência"], rows["B"]["Motivo da tendência"]) == ("Sem classificação", "Série estável")
    tendencia = result["metadata"]["tendencia"]
    assert tendencia["desfecho"] == "RES-SCL" and tendencia["unidade_tempo"] == "unidade do período"
    assert tendencia["unidades"][0] == {"territorio": "A", "categoria": "Nurses", "velocidades": [2, -1, 2], "ausentes": []}
    # Sem classificação não é limitação de dados: a avaliabilidade do resultado continua plena.
    assert result["metadata"]["evaluability"]["status"] == "AVALIAVEL"
    assert result["metadata"]["metodos"] == {"tendencia": METHOD_VERSION}


# AT-69 (L2380) e AT-80 (L2404): agregado com suporte ou tipo de contagem divergente
def test_at69_at80_incomparable_aggregate_has_no_trajectory():
    trend = classify([("2020", 2020, 10), ("2021", 2021, 30), ("2022", 2022, 40), ("2023", 2023, 50)],
                     incomparability="Membros efetivos diferentes: 2020 sem M2")
    assert (trend.evaluability, trend.not_evaluable, trend.category) == ("NAO_AVALIAVEL", "INCOMPARABILIDADE", None)
    assert trend.intervals == () and len(trend.observations) == 4   # valores isolados preservados
    assert trend.row() == {"Tendência": "Não avaliável: série não comparável",
                           "Motivo da tendência": "Membros efetivos diferentes: 2020 sem M2",
                           "Observações da tendência": 4}
    assert summarize([trend])["desfecho"] == "BLQ-MET"


def test_evolution_receives_incomparability_and_reports_breaks():
    data = pd.DataFrame({"territory": ["UF"] * 4 + ["M"] * 4, "category": ["MEDICINA"] * 8, "period": ["2020", "2021", "2022", "2023"] * 2,
                         "quantity": [10.0, 30, 40, 50, 1, 2, 3, 4], "population": [float("nan")] * 8})
    data["density"] = float("nan")
    positions = {str(y): float(y) for y in range(2020, 2024)}
    rows, detail, meta, moved, breaks = evolution(data, "quantity", positions, convention="numeric",
                                                  incomparable={("UF", "MEDICINA"): "Membros efetivos diferentes"})
    assert [row["Tendência"] for row in rows] == ["Crescimento", "Não avaliável: série não comparável"]
    assert breaks == [{"territorio": "UF", "categoria": "MEDICINA"}]
    assert meta["unidades"][1]["velocidades"] == [] and meta["desfecho"] == "RES-LIM"
    assert meta["nao_avaliaveis_por_motivo"]["INCOMPARABILIDADE"] == 1
    assert len(detail) == 8 and list(detail[0]) == ["Território", "Período", "Categoria", "Quantidade"]
    # A mudança entre os extremos continua avaliável: a incomparabilidade é da trajetória.
    assert rows[1]["Direção da mudança"] == "Aumento" and moved["direcoes"]["AUMENTO"] == 2


def test_repeated_positions_are_rejected():
    with pytest.raises(ValueError):
        classify([("a", 1, 1), ("b", 1, 2), ("c", 2, 3), ("d", 3, 4)])
    assert classify_speeds([Fraction(1), Fraction(1), Fraction(1)]) == ("CRESCIMENTO", None)


def test_window_metadata_and_missing_observations():
    frame = pd.DataFrame({"Municipality": ["A"] * 4 + ["B"] * 3, "Year": ["202301", "202306", "202401", "202406",
                                                                          "202301", "202401", "202406"],
                          "Profession": ["Nurses"] * 7, "Count": [1, 2, 3, 4, 2, 2, 3]})
    result = compute(frame, {"territory": "Municipality", "period": "Year", "category": "Profession", "count": "Count"},
                     "temporal", {"count_unit": "pessoas", "temporal_indicator": "quantity",
                                  "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True})
    tendencia = result["metadata"]["tendencia"]
    janela = tendencia["janela"]
    assert janela["periodos"] == ["202301", "202306", "202401", "202406"] and janela["intervalos"] == [5, 7]
    assert janela["intervalo_constante"] is False and janela["serie_anual"] is None
    assert janela["serie_anual_disponivel"] is False   # só duas competências de junho
    assert tendencia["unidade_tempo"] == "mês" and tendencia["unidade_valor"] == "pessoas"
    b = next(unit for unit in tendencia["unidades"] if unit["territorio"] == "B")
    assert b["ausentes"] == ["202306"] and b["velocidades"] == []   # três observações: série insuficiente
    assert any(note.startswith("As competências desta série estão separadas por 5 e 7 meses") for note in result["notes"])
    assert result["rows"][1]["Observações da tendência"] == 3
    # Coluna na ordem do contrato da evolução temporal.
    assert list(result["rows"][0]) == ["Território", "Categoria", "Período inicial", "Período final", "Inicial", "Final",
                                       "Variação absoluta", "Variação (%)", "Direção da mudança", "Condição da mudança",
                                       "Tendência", "Motivo da tendência", "Observações da tendência"]


def test_annual_june_series_is_flagged():
    periods = [f"{year}{month}" for year in range(2014, 2019) for month in ("01", "06")]
    frame = pd.DataFrame({"Municipality": ["A"] * len(periods), "Year": periods, "Profession": ["Nurses"] * len(periods),
                          "Count": list(range(1, len(periods) + 1))})
    mapping = {"territory": "Municipality", "period": "Year", "category": "Profession", "count": "Count"}
    options = {"count_unit": "pessoas", "temporal_indicator": "quantity",
               "temporal_comparability_confirmed": True, "territory_longitudinal_confirmed": True}
    janela = compute(frame, mapping, "temporal", options)["metadata"]["tendencia"]["janela"]
    assert janela["serie_anual_disponivel"] is True
    assert janela["competencias_serie_anual"] == [p for p in periods if p.endswith("06")]
    june = compute(frame, mapping, "temporal", {**options, "period_filters": janela["competencias_serie_anual"]})
    janela = june["metadata"]["tendencia"]["janela"]
    assert (janela["serie_anual"], janela["intervalos"], janela["serie_anual_disponivel"]) == ("06", [12], False)
    assert june["rows"][0]["Tendência"] == "Crescimento"


def _reference(data, value_cols, positions):
    """Classificação de referência: `classify` (Fraction) por unidade."""
    out = []
    for key, group in data.groupby(["territory", "category"], sort=True):
        points = [(p, positions[p], q if len(value_cols) == 1 else density(q, pop))
                  for p, q, pop in zip(group.period, group.quantity, group.population) if q == q and (len(value_cols) == 1 or pop == pop)]
        out.append((key, classify(points)))
    return out


@pytest.mark.parametrize("seed", range(6))
def test_classify_frame_equals_classify_on_random_series(seed):
    rng = random.Random(seed)
    periods = [f"{year}{month}" for year in range(2014, 2020) for month in ("01", "06")]
    positions = {p: float(int(p[:4]) * 12 + int(p[4:]) - 1) for p in periods}
    records = []
    for unit in range(60):
        base = rng.randint(0, 50)
        population = rng.choice([3, 7, 1000, 14292, 10318])
        for period in periods:
            if rng.random() < 0.15:
                continue  # competência ausente: não imputada
            step = rng.choice([0, 0, 1, 1, 2, -1, 3])
            base = max(0, base + step)
            if rng.random() < 0.2:
                population = rng.choice([3, 7, 1000, 14292, 10318])
            quantity = float(base) if rng.random() < 0.9 else base + 0.5
            records.append({"territory": f"T{unit:02d}", "category": "MEDICINA", "period": period,
                            "quantity": quantity, "population": float(population)})
    data = pd.DataFrame(records)
    for value_cols in (("quantity",), ("quantity", "population")):
        fast = classify_frame(data, value_cols=value_cols, positions=positions)
        reference = _reference(data, value_cols, positions)
        assert [key for key, _ in fast] == [key for key, _ in reference]
        for (_, a), (_, b) in zip(fast, reference):
            assert a == b   # mesma classe, motivo, observações e velocidades exatas
            assert a.speeds() == [float(item.speed) for item in b.intervals]   # float com arredondamento correto
