"""Comparação territorial com janela temporal: CAP-CMP-01 com CAP-TMP-01 e CAP-TEN-01 (decisão D6 do responsável
pelo produto, 19/10/2026).

Com a opção `comparison_values_period` (a competência dos valores) e a janela em `period_filters`:
- `rows`: as relações da CAP-CMP-01 só na competência dos valores, no formato de sempre (par A/B com relação e
  diferença assinada A − B; com três ou mais objetos, valores, iguais e próximo valor maior, sem diferenças de pares);
  a cardinalidade é a do conjunto pedido, não a dos objetos que restarem na competência (AT-84);
- `detail_rows`: um registro por objeto, com quantidade, população e densidade na competência dos valores e, com duas
  ou mais competências na janela, a mudança entre a competência inicial e a final (CAP-TMP-01) e a tendência
  (CAP-TEN-01) calculadas pela mesma `temporal_change.evolution` da evolução temporal. Não há variação percentual,
  razão nem diferença percentual automáticas (AT-84): a variação percentual continua na Evolução temporal;
- entre classes de tendência não há ordem nem relação: ficam lado a lado.

Sem a opção, a comparação segue exatamente o caminho anterior (relações em cada competência). Nenhum cálculo aqui
lê arquivos ou vai ao provedor de IA; o módulo só organiza o que o motor já calculou.
"""
from __future__ import annotations

import pandas as pd

from temporal_change import CONDITION_BASE_ZERO, CONDITION_EVALUABLE, evolution, evolution_notes

OPTION = "comparison_values_period"
WINDOW_COLUMNS = ("Período inicial", "Período final", "Inicial", "Final", "Variação absoluta", "Direção da mudança",
                  "Condição da mudança", "Tendência", "Motivo da tendência", "Observações da tendência")
METRIC_LABELS = {"density": "Densidade por 1.000", "quantity": "Quantidade"}
MISSING_VALUES = "Não avaliável: sem registro na competência dos valores"
NOTE_PAIRS = "Entre dois objetos: A e B em ordem de nome, relação A/B e diferença assinada A − B."
NOTE_SET = ("Entre três ou mais: valores iguais e próximo valor estritamente maior descrevem a ordem do conjunto; sem "
            "diferenças automáticas entre pares.")
NOTE_CLASSES = ("Classes de tendência lado a lado: entre territórios, só se lê se a classe é a mesma; as classes não "
                "têm ordem entre si.")


def requested_period(options: dict) -> str | None:
    """Competência dos valores pedida (None: caminho anterior, relações em cada competência)."""
    value = options.get(OPTION)
    if value is None or value == "":
        return None
    if not isinstance(value, str) or not value.strip() or len(value) > 64:
        raise ValueError("Competência dos valores inválida: escolha uma das competências da janela.")
    return value.strip()


def relation_rows(data: pd.DataFrame, metric: str, unit: str, requested: int | None = None) -> list[dict]:
    """Relações da CAP-CMP-01 por (período, categoria). `requested` é a cardinalidade do conjunto pedido (AT-84);
    sem ela, vale o número de territórios do próprio quadro (comportamento anterior)."""
    rows = []
    metric_label = METRIC_LABELS[metric]
    pair = (data.territory.nunique() if requested is None else requested) == 2
    for (period, category), group in data.groupby(["period", "category"], sort=True):
        group = group.sort_values("territory")
        common = {"Período": period, "Categoria": category, "Indicador": metric_label, "Unidade de contagem": unit}
        if pair and len(group) == 2:
            a, b = group.iloc[0], group.iloc[1]
            rows.append({**common, "Objeto A": a.territory, "Valor A": a[metric],
                         "Objeto B": b.territory, "Valor B": b[metric],
                         "Relação A/B": "IGUALDADE" if a[metric] == b[metric] else "MAIOR" if a[metric] > b[metric] else "MENOR",
                         "Diferença A − B": a[metric] - b[metric], "Condição": "Comparável"})
        else:
            values = sorted(group[metric].unique())
            following = dict(zip(values, [*values[1:], None]))
            equal_counts = group[metric].value_counts()
            for item in group.itertuples():
                value = getattr(item, metric)
                rows.append({**common, "Território": item.territory, metric_label: value,
                             "Próximo valor maior": following[value],
                             "Unidades com mesmo valor": int(equal_counts[value]),
                             "Condição": "Comparável" if len(group) > 1 else "Não avaliável: menos de dois territórios neste recorte"})
    # Períodos com cardinalidades diferentes mantêm todas as colunas no CSV.
    columns = dict.fromkeys(key for row in rows for key in row)
    return [{key: row.get(key) for key in columns} for row in rows]


def _number(value):
    if value is None or pd.isna(value):
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def value_columns(record: dict | None, metric: str, density_columns: bool) -> dict:
    """Quantidade, população e densidade na competência dos valores (lacuna quando o objeto não tem registro)."""
    record = record or {}
    out = {"Quantidade": _number(record.get("quantity"))}
    if density_columns:
        out["População"] = _number(record.get("population"))
        density = record.get("density")
        out["Densidade por 1.000"] = None if density is None or pd.isna(density) else float(density)
    return out


def window_columns(evolved: dict | None) -> dict:
    """Mudança e tendência do objeto na janela, sem a variação percentual (AT-84). Base zero só afeta o percentual,
    ausente da comparação: a condição da mudança fica "Avaliável". Extremo sem valor (densidade sem população) é
    lacuna (None), nunca NaN."""
    if evolved is None:
        return {column: None for column in WINDOW_COLUMNS}
    out = {column: None if isinstance(evolved.get(column), float) and pd.isna(evolved.get(column)) else evolved.get(column)
           for column in WINDOW_COLUMNS}
    if out["Condição da mudança"] == CONDITION_BASE_ZERO:
        out["Condição da mudança"] = CONDITION_EVALUABLE
    return out


def evolve(data: pd.DataFrame, metric: str, positions: dict, convention: str | None, value_unit: str,
           incomparable: dict | None = None, change_incomparable: dict | None = None):
    """Mudança e tendência por (território, categoria) na janela: a mesma evolution da evolução temporal."""
    rows, _, tendencia, mudanca, breaks = evolution(data, metric, positions, convention=convention,
                                                    incomparable=incomparable, change_incomparable=change_incomparable,
                                                    value_unit=value_unit)
    by_key = {(row["Território"], row["Categoria"]): row for row in rows}
    return by_key, tendencia, mudanca, breaks


def notes(period: str, ordered: list, tendencia: dict | None, mudanca: dict | None, convention: str | None,
          relations: list[str]) -> list[str]:
    """Notas da comparação com competência dos valores (PT-BR); `relations` são as notas das relações usadas."""
    out = ["Competência dos valores: " + str(period) + ". As relações da comparação (CAP-CMP-01) usam só esta "
           "competência; os valores de outras competências não entram nelas.", *relations]
    if len(ordered) >= 2:
        out.append("Janela de " + str(ordered[0]) + " a " + str(ordered[-1]) + " (" + str(len(ordered)) + " competências): "
                   "por território, mudança entre a competência inicial e a final (CAP-TMP-01) e tendência (CAP-TEN-01); "
                   "sem variação percentual, razão ou diferença percentual automáticas (AT-84).")
        out += [note for note in evolution_notes(tendencia, mudanca, convention) if not note.startswith("Variação (%)")]
        out.append(NOTE_CLASSES)
    return out


def window_meta(period: str, ordered: list, metric: str) -> dict:
    return {"capacidade": "CAP-CMP-01", "competencia_valores": period, "indicador": metric,
            "janela": {"periodos": list(ordered), "inicio": ordered[0] if ordered else None,
                       "fim": ordered[-1] if ordered else None, "competencias": len(ordered)},
            "mudanca_e_tendencia": len(ordered) >= 2, "grupos": [], "sem_relacao": []}
