"""CAP-TMP-01 (mudança entre dois períodos, DA-14) e evolução temporal com CAP-TEN-01, em aritmética exata.

`change` não qualifica aceleração nem afirma tendência (L1765: "Proibido: afirmar tendência").
`evolution` reúne, por território e categoria, a mudança entre a primeira e a última competência da
janela e a tendência de `trend.py`. É a função que a evolução temporal usa e que os níveis territoriais
e a comparação com janela reutilizam: quem chama informa a incomparabilidade de agregados pela
entrada (`incomparable`), nunca reescrevendo linhas depois do cálculo.

Inicial, Final e as variações continuam em float, com a mesma aritmética de antes (a tabela, o CSV e
os testes de igualdade exata não mudam). A direção da mudança e a tendência usam os valores exatos:
a densidade é recalculada como quantidade × 1.000 / população, sem passar pelo float.
"""
from __future__ import annotations

from fractions import Fraction

import numpy as np

from trend import (MIN_OBSERVATIONS, METHOD_VERSION, TEXT_MINIMUM, classify_frame, exact, stage_block, summarize,
                   time_unit, time_unit_plural)

DIRECTIONS = {"AUMENTO": "Aumento", "REDUCAO": "Redução", "SEM_MUDANCA": "Sem mudança"}
ANNUAL_MONTH = "06"  # série anual da base Brasil: junho, o mês da população estimada
CONDITION_EVALUABLE = "Avaliável"
CONDITION_BASE_ZERO = "Avaliável; variação percentual não avaliável: base zero"
CONDITION_MISSING = "Não avaliável: observação ausente em um dos extremos"
COLUMNS = ("Território", "Categoria", "Período inicial", "Período final", "Inicial", "Final", "Variação absoluta",
           "Variação (%)", "Direção da mudança", "Condição da mudança", "Tendência", "Motivo da tendência",
           "Observações da tendência")


def change(v1, v2) -> dict:
    """Variação absoluta, percentual (NAO_AVALIAVEL por BASE_ZERO quando v1 = 0) e direção exata."""
    a, b = exact(v1), exact(v2)
    absolute = b - a
    direction = "AUMENTO" if b > a else "REDUCAO" if b < a else "SEM_MUDANCA"
    percent: Fraction | None = absolute / a * 100 if a != 0 else None
    return {"variacao_absoluta": absolute, "variacao_percentual": percent, "direcao": direction,
            "rotulo_direcao": DIRECTIONS[direction],
            "motivo_percentual": None if percent is not None else "BASE_ZERO"}


def _number(value: float):
    return int(value) if float(value).is_integer() else float(value)


def window(periods: list[str], positions: dict, convention: str | None) -> dict:
    """Janela da série: competências, intervalos entre vizinhas e disponibilidade da série anual de junho."""
    steps = [positions[b] - positions[a] for a, b in zip(periods, periods[1:])]
    distinct = sorted({_number(step) for step in steps})
    monthly = convention == "yyyymm"
    months = {period[4:] for period in periods} if monthly else set()
    annual = next(iter(months)) if monthly and len(months) == 1 and distinct == [12] else None
    june = [period for period in periods if monthly and period[4:] == ANNUAL_MONTH]
    return {"periodos": list(periods), "inicio": periods[0], "fim": periods[-1], "intervalos": distinct,
            "intervalo_constante": len(distinct) <= 1, "serie_anual": annual,
            "serie_anual_disponivel": len(june) >= MIN_OBSERVATIONS and annual != ANNUAL_MONTH,
            "competencias_serie_anual": june if len(june) >= MIN_OBSERVATIONS and annual != ANNUAL_MONTH else []}


def evolution(data, metric: str, positions: dict, *, convention: str | None = None, incomparable: dict | None = None,
              value_unit: str | None = None, scale: int = 1000):
    """Mudança (CAP-TMP-01) e tendência (CAP-TEN-01) por (território, categoria) na janela `positions`.

    `data` traz as colunas territory, period, category, quantity, population e density do motor
    (`validate_operation`). Valor ausente (NaN) é observação ausente, nunca zero. `incomparable`
    mapeia (território, categoria) ao texto do componente divergente (agregados com suporte variável).

    Devolve (rows, detail_rows, meta_tendencia, meta_mudanca, quebras); `quebras` lista as unidades sem
    trajetória (INCOMPARABILIDADE), que a representação desenha só como pontos.
    """
    periods = sorted(positions, key=positions.get)
    if len(periods) < 2:
        raise ValueError("Mudança temporal exige ao menos dois períodos.")
    block = stage_block(len(periods))
    value_cols = ("quantity", "population") if metric == "density" else ("quantity",)
    trends = classify_frame(data, value_cols=value_cols, positions=positions, incomparability=incomparable, scale=scale)
    floats = {(ter, cat, str(per)): value for ter, cat, per, value in
              zip(*(data[name].to_numpy(dtype=object).tolist() for name in ("territory", "category", "period", metric)))}
    first, last = periods[0], periods[-1]
    rows, units, breaks = [], [], []
    directions = dict.fromkeys(DIRECTIONS, 0)
    missing_endpoints = base_zero = 0
    for (ter, cat), trend in trends:
        observed = set(trend.periods)
        a, b = floats.get((ter, cat, first)), floats.get((ter, cat, last))
        endpoints = first in observed and last in observed
        row = {"Território": ter, "Categoria": cat, "Período inicial": first, "Período final": last,
               "Inicial": float(a) if a is not None else None, "Final": float(b) if b is not None else None,
               "Variação absoluta": float(b - a) if endpoints else None,
               "Variação (%)": float((b - a) / a * 100) if endpoints and a != 0 else None}
        if endpoints:
            moved = change(trend.value_at(first), trend.value_at(last))
            directions[moved["direcao"]] += 1
            row["Direção da mudança"] = moved["rotulo_direcao"]
            row["Condição da mudança"] = CONDITION_BASE_ZERO if moved["motivo_percentual"] else CONDITION_EVALUABLE
            base_zero += bool(moved["motivo_percentual"])
        else:
            missing_endpoints += 1
            row["Direção da mudança"] = None
            row["Condição da mudança"] = CONDITION_MISSING
        row.update(trend.row())
        rows.append(row)
        units.append({"territorio": ter, "categoria": cat, "velocidades": trend.speeds(),
                      "ausentes": [period for period in periods if period not in observed]})
        if trend.not_evaluable == "INCOMPARABILIDADE":
            breaks.append({"territorio": ter, "categoria": cat})
    detail = data[["territory", "period", "category", metric]].rename(columns={
        "territory": "Território", "period": "Período", "category": "Categoria",
        "quantity": "Quantidade", "density": "Densidade por 1.000"})
    detail_rows = detail.replace({np.nan: None}).to_dict(orient="records")
    convention_unit = time_unit(convention)
    meta_trend = {**summarize([trend for _, trend in trends], block=block),
                  "indicador": metric, "unidade_valor": value_unit, "unidade_tempo": convention_unit,
                  "janela": window(periods, positions, convention), "unidades": units}
    meta_change = {"capacidade": "CAP-TMP-01", "periodo_inicial": first, "periodo_final": last,
                   "direcoes": directions, "nao_avaliaveis": {"SEM_REGISTRO_OBSERVADO": missing_endpoints},
                   "percentual_nao_avaliavel": {"BASE_ZERO": base_zero}}
    return rows, detail_rows, meta_trend, meta_change, breaks


def evolution_notes(meta_trend: dict, meta_change: dict, convention: str | None = None) -> list[str]:
    """Notas do resultado (PT-BR) sobre o método da tendência, o bloqueio, os intervalos e a base zero."""
    unit, plural = time_unit(convention), time_unit_plural(convention)
    notes = ["Tendência (CAP-TEN-01, DA-15, versão " + METHOD_VERSION + "): velocidade = variação absoluta por " + unit +
             " entre observações consecutivas, em aritmética exata, sem imputação de competências ausentes. "
             "Sem classificação é resultado do método, não falta de dados."]
    block = meta_trend.get("bloqueio")
    if block:
        notes.append(block["texto"] + " " + TEXT_MINIMUM + " A mudança entre o primeiro e o último período continua disponível.")
    steps = meta_trend["janela"]["intervalos"]
    if len(steps) > 1:
        shown = [str(step).replace(".", ",") for step in steps]
        notes.append("As competências desta série estão separadas por " + ", ".join(shown[:-1]) + " e " + shown[-1] + " " +
                     plural + "; as velocidades consideram o tempo transcorrido entre elas.")
    if meta_change["percentual_nao_avaliavel"]["BASE_ZERO"]:
        notes.append("Variação (%) não avaliável quando o valor inicial é zero (base zero); direção e variação absoluta "
                     "continuam calculadas.")
    return notes
