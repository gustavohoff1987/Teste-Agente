"""CAP-TEN-01 — Tendência (DA-15), em aritmética exata, sem LLM e sem imputação.

Contrato: recebe as observações válidas de cada unidade (competência, posição temporal numérica e
valor do indicador) já preparadas pelo motor. Não lê arquivos, não escolhe janela nem decide a
composição de agregados: quem chama informa a incomparabilidade (CAP-AGR-01, F-05b) quando houver.
Períodos ausentes continuam ausentes; o tempo transcorrido entre observações entra na velocidade.

Dois caminhos com o mesmo resultado:
- `classify`: uma unidade, com `Fraction` (casos pequenos, testes e comparações);
- `classify_frame`: todas as unidades de um quadro, com valores como pares de inteiros (numerador,
  denominador > 0) e comparações por produto cruzado, sem mdc. A equivalência com `classify` é
  conferida em `tests/test_trend.py`.
A densidade em float (quantidade / população × 1.000) não entra na classificação: o arredondamento
binário separaria velocidades exatamente iguais e criaria acelerações espúrias.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import cached_property
from decimal import Decimal
from fractions import Fraction
from typing import Iterable, Sequence

METHOD_VERSION = "CAP-TEN-01/DA-15/1"
MIN_OBSERVATIONS = 4

# Ordem do enum CategoriaTendencia (SPEC L415). É a ordem da legenda e das contagens, não um ranking.
CLASSES = ("CRESCIMENTO", "CRESCIMENTO_ACELERADO", "CRESCIMENTO_DESACELERADO",
           "DECLINIO", "DECLINIO_ACELERADO", "DECLINIO_DESACELERADO", "SEM_CLASSIFICACAO")
LABELS = {  # rótulos de apresentação DA-15; os do declínio com "de" (divergência aprovada pelo responsável em 24/10/2026)
    "CRESCIMENTO": "Crescimento",
    "CRESCIMENTO_ACELERADO": "Aceleração do crescimento",
    "CRESCIMENTO_DESACELERADO": "Desaceleração do crescimento",
    "DECLINIO": "Declínio",
    "DECLINIO_ACELERADO": "Aceleração de declínio",
    "DECLINIO_DESACELERADO": "Desaceleração de declínio",
    "SEM_CLASSIFICACAO": "Sem classificação",
}
FAMILIES = ("CRESCIMENTO", "DECLINIO", "NENHUMA")
FAMILY = {**{c: "CRESCIMENTO" for c in CLASSES[:3]}, **{c: "DECLINIO" for c in CLASSES[3:6]},
          "SEM_CLASSIFICACAO": "NENHUMA"}
FAMILY_LABELS = {"CRESCIMENTO": "Família do crescimento", "DECLINIO": "Família do declínio",
                 "NENHUMA": "Sem classificação"}
MOTIVES = ("MUDANCA_DE_DIRECAO", "SERIE_ESTAVEL")  # MotivoSemClassificacao (L390)
MOTIVE_LABELS = {"MUDANCA_DE_DIRECAO": "Mudança de direção", "SERIE_ESTAVEL": "Série estável"}
NOT_EVALUABLE = ("SERIE_INSUFICIENTE", "INCOMPARABILIDADE")  # subconjunto de MotivoNaoAvaliavel (L388)
NOT_EVALUABLE_LABELS = {"SERIE_INSUFICIENTE": "Não avaliável: série insuficiente",
                        "INCOMPARABILIDADE": "Não avaliável: série não comparável"}
# Textos do catálogo (Docs/CFG_DOC_CATALOG.yaml, DOC:CAP-TEN-01.precondicoes), sem paráfrase.
TEXT_MINIMUM = "A análise de tendência exige quatro observações válidas."
TEXT_BLOCKED = "Não foi possível analisar a tendência porque há apenas {quantidade} observações válidas."
# Unidade da posição temporal (data_contract.period_positions): singular e plural.
TIME_UNITS = {"yyyymm": ("mês", "meses"), "date": ("dia", "dias"),
              "numeric": ("unidade do período", "unidades do período")}


def exact(value) -> Fraction:
    """Valor do motor como racional exato.

    Inteiros, Fraction e Decimal passam sem perda. Um float vira o menor decimal que o representa
    (repr), não a expansão binária: 0.1 → 1/10, 12.0 → 12. Booleanos, NaN e infinitos são recusados.
    """
    if isinstance(value, bool):
        raise TypeError("Valor lógico não é observação do indicador.")
    if isinstance(value, (int, Fraction, Decimal)):
        return Fraction(value)
    if hasattr(value, "item") and not isinstance(value, float):  # escalares numpy
        return exact(value.item())
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Observação não finita.")
    return Fraction(repr(number))


def pair(value) -> tuple[int, int]:
    """O mesmo valor de `exact`, como (numerador, denominador > 0), sem mdc para inteiros."""
    if isinstance(value, float) and value.is_integer():
        return int(value), 1
    if isinstance(value, int) and not isinstance(value, bool):
        return value, 1
    number = exact(value)
    return number.numerator, number.denominator


def density(quantity, population, scale: int = 1000) -> Fraction:
    """CAP-IND-02 em precisão integral: quantidade / população × escala."""
    pop = exact(population)
    if pop <= 0:
        raise ValueError("Denominador populacional não positivo.")
    return exact(quantity) * scale / pop


def time_unit(convention: str | None) -> str:
    """Unidade das velocidades: "mês" (AAAAMM), "dia" (data) ou "unidade do período" (numérico)."""
    return TIME_UNITS.get(convention or "numeric", TIME_UNITS["numeric"])[0]


def time_unit_plural(convention: str | None) -> str:
    return TIME_UNITS.get(convention or "numeric", TIME_UNITS["numeric"])[1]


@dataclass(frozen=True)
class Observation:
    period: str
    position: Fraction
    value: Fraction


@dataclass(frozen=True)
class Interval:
    start: str
    end: str
    elapsed: Fraction   # t_(i+1) − t_i na unidade da posição temporal (mês para AAAAMM)
    change: Fraction    # y_(i+1) − y_i
    speed: Fraction     # v_i = change / elapsed


@dataclass(frozen=True, eq=False)
class Trend:
    """Tendência de uma unidade. Guarda posições e valores como pares exatos (n, d > 0); observações e
    intervalos em `Fraction` são montados só quando pedidos (o caminho em massa não paga por eles)."""
    evaluability: str                 # "AVALIAVEL" | "NAO_AVALIAVEL"
    category: str | None              # CategoriaTendencia, só quando avaliável
    motive: str | None                # MotivoSemClassificacao, só com SEM_CLASSIFICACAO
    not_evaluable: str | None         # SERIE_INSUFICIENTE | INCOMPARABILIDADE
    detail: str | None                # componente divergente (INCOMPARABILIDADE), texto PT-BR
    periods: tuple[str, ...]          # competências das observações válidas, em ordem temporal
    times: tuple[tuple[int, int], ...]
    values: tuple[tuple[int, int], ...]
    method_version: str = METHOD_VERSION

    @cached_property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(Observation(p, Fraction(*t), Fraction(*v)) for p, t, v in zip(self.periods, self.times, self.values))

    @cached_property
    def intervals(self) -> tuple[Interval, ...]:
        # INCOMPARABILIDADE não entrega velocidades (AT-69/AT-80); série insuficiente não as tem.
        return intervals(self.observations) if self.evaluability == "AVALIAVEL" else ()

    def value_at(self, period: str) -> Fraction | None:
        for name, value in zip(self.periods, self.values):
            if name == period:
                return Fraction(*value)
        return None

    def __eq__(self, other):
        if not isinstance(other, Trend):
            return NotImplemented
        fields = ("evaluability", "category", "motive", "not_evaluable", "detail", "observations", "intervals",
                  "method_version")
        return all(getattr(self, name) == getattr(other, name) for name in fields)

    __hash__ = None

    @property
    def label(self) -> str:
        return LABELS[self.category] if self.category else NOT_EVALUABLE_LABELS[self.not_evaluable]

    @property
    def family(self) -> str | None:
        return FAMILY[self.category] if self.category else None

    @property
    def motive_label(self) -> str | None:
        if self.motive:
            return MOTIVE_LABELS[self.motive]
        if self.not_evaluable == "SERIE_INSUFICIENTE":
            return f"{len(self.periods)} de {MIN_OBSERVATIONS} observações necessárias"
        return self.detail

    def row(self) -> dict:
        """Colunas escalares da linha do resultado (seguras para o CSV)."""
        return {"Tendência": self.label, "Motivo da tendência": self.motive_label,
                "Observações da tendência": len(self.periods)}

    def speeds(self) -> list[float]:
        """Velocidades exatas entregues em float: divisão inteira com arredondamento correto, como float(Fraction)."""
        if self.evaluability != "AVALIAVEL":
            return []
        out = []
        for (tn1, td1), (tn2, td2), (n1, d1), (n2, d2) in zip(self.times, self.times[1:], self.values, self.values[1:]):
            out.append(((n2 * d1 - n1 * d2) * (td1 * td2)) / ((d1 * d2) * (tn2 * td1 - tn1 * td2)))
        return out

    def structured(self) -> dict:
        """Registro estruturado JSON-seguro; frações exatas como 'p/q'."""
        return {"avaliabilidade": self.evaluability, "classe": self.category, "rotulo": self.label,
                "direcao": self.family, "motivo_sem_classificacao": self.motive,
                "motivo_nao_avaliavel": self.not_evaluable, "detalhe": self.detail,
                "observacoes": [{"periodo": o.period, "valor": float(o.value), "exato": str(o.value)}
                                for o in self.observations],
                "velocidades": [{"de": i.start, "ate": i.end, "tempo": float(i.elapsed),
                                 "variacao": float(i.change), "velocidade": float(i.speed),
                                 "exata": str(i.speed)} for i in self.intervals],
                "versao_metodo": self.method_version}


def _from_fractions(evaluability, category, motive, not_evaluable, detail, obs, steps) -> Trend:
    """Trend do caminho `classify`: observações e intervalos já calculados com Fraction ficam guardados."""
    trend = Trend(evaluability, category, motive, not_evaluable, detail, tuple(o.period for o in obs),
                  tuple((o.position.numerator, o.position.denominator) for o in obs),
                  tuple((o.value.numerator, o.value.denominator) for o in obs))
    trend.__dict__["observations"] = tuple(obs)
    trend.__dict__["intervals"] = tuple(steps)
    return trend


def intervals(observations: Sequence[Observation]) -> tuple[Interval, ...]:
    out = []
    for a, b in zip(observations, observations[1:]):
        elapsed = b.position - a.position
        if elapsed <= 0:
            raise ValueError("Posições temporais repetidas ou fora de ordem.")
        change = b.value - a.value
        out.append(Interval(a.period, b.period, elapsed, change, change / elapsed))
    return tuple(out)


def classify_speeds(speeds: Sequence[Fraction]) -> tuple[str, str | None]:
    """Passos 4 a 6 de CAP-TEN-01 (DA-15). Recebe três ou mais velocidades exatas."""
    if all(v == 0 for v in speeds):
        return "SEM_CLASSIFICACAO", "SERIE_ESTAVEL"
    if any(v > 0 for v in speeds) and any(v < 0 for v in speeds):
        return "SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO"
    base = "CRESCIMENTO" if all(v >= 0 for v in speeds) else "DECLINIO"
    if any(v == 0 for v in speeds):
        return base, None  # intervalo com velocidade zero impede a qualificação
    magnitudes = [abs(v) for v in speeds]
    steps = list(zip(magnitudes, magnitudes[1:]))
    if all(b >= a for a, b in steps) and any(b > a for a, b in steps):
        return base + "_ACELERADO", None
    if all(b <= a for a, b in steps) and any(b < a for a, b in steps):
        return base + "_DESACELERADO", None
    return base, None  # constantes ou sem monotonicidade


def classify_pairs(speeds: Sequence[tuple[int, int]]) -> tuple[str, str | None]:
    """O mesmo que `classify_speeds`, com velocidades (n, d), d > 0, comparadas por produto cruzado."""
    signs = [(n > 0) - (n < 0) for n, _ in speeds]
    if not any(signs):
        return "SEM_CLASSIFICACAO", "SERIE_ESTAVEL"
    if 1 in signs and -1 in signs:
        return "SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO"
    base = "CRESCIMENTO" if -1 not in signs else "DECLINIO"
    if 0 in signs:
        return base, None
    up = down = False
    for (a, b), (c, d) in zip(speeds, speeds[1:]):
        x, y = abs(a) * d, abs(c) * b      # |a/b| contra |c/d|
        if y > x:
            up = True
        elif y < x:
            down = True
        if up and down:
            return base, None
    if up:
        return base + "_ACELERADO", None
    if down:
        return base + "_DESACELERADO", None
    return base, None


def classify(points: Iterable[tuple[str, object, object]], *, incomparability: str | None = None) -> Trend:
    """Classifica uma unidade a partir de (competência, posição temporal, valor) válidos.

    `incomparability` é o texto do componente divergente (ex.: membros efetivos diferentes); com ele,
    a unidade é NAO_AVALIAVEL (INCOMPARABILIDADE) e nenhuma velocidade é entregue (AT-69/AT-80).
    """
    obs = sorted((Observation(str(p), exact(t), exact(y)) for p, t, y in points), key=lambda o: o.position)
    if len({o.position for o in obs}) != len(obs):
        raise ValueError("Posições temporais repetidas na mesma unidade.")
    if incomparability:
        return _from_fractions("NAO_AVALIAVEL", None, None, "INCOMPARABILIDADE", incomparability, obs, ())
    if len(obs) < MIN_OBSERVATIONS:
        return _from_fractions("NAO_AVALIAVEL", None, None, "SERIE_INSUFICIENTE", None, obs, ())
    steps = intervals(obs)
    category, motive = classify_speeds([s.speed for s in steps])
    return _from_fractions("AVALIAVEL", category, motive, None, None, obs, steps)


def _trend_from_pairs(periods, times, values, incomparability) -> Trend:
    """Trend de uma unidade já ordenada; `times` e `values` são pares (n, d > 0). Sem Fraction."""
    periods, times, values = tuple(periods), tuple(times), tuple(values)
    if incomparability:
        return Trend("NAO_AVALIAVEL", None, None, "INCOMPARABILIDADE", incomparability, periods, times, values)
    if len(periods) < MIN_OBSERVATIONS:
        return Trend("NAO_AVALIAVEL", None, None, "SERIE_INSUFICIENTE", None, periods, times, values)
    speeds = []
    for (tn1, td1), (tn2, td2), (n1, d1), (n2, d2) in zip(times, times[1:], values, values[1:]):
        dt_n, dt_d = tn2 * td1 - tn1 * td2, td1 * td2
        if dt_n <= 0:
            raise ValueError("Posições temporais repetidas ou fora de ordem.")
        speeds.append(((n2 * d1 - n1 * d2) * dt_d, (d1 * d2) * dt_n))   # (Δy/Δt), denominador positivo
    category, motive = classify_pairs(speeds)
    return Trend("AVALIAVEL", category, motive, None, None, periods, times, values)


def _missing(value) -> bool:
    if value is None:
        return True
    try:
        return bool(value != value)   # NaN
    except TypeError:                 # pandas.NA
        return True


def classify_frame(data, *, value_cols: Sequence[str], positions: dict, keys: Sequence[str] = ("territory", "category"),
                   incomparability: dict | None = None, scale: int = 1000) -> list[tuple[tuple, Trend]]:
    """Classifica todas as unidades de um quadro (caminho em massa, equivalente a `classify`).

    `value_cols` = ("quantity",) usa a quantidade; ("quantity", "population") usa a densidade exata
    quantidade × escala / população. Linha com valor ausente (NaN) é observação ausente, nunca zero.
    `positions` mapeia cada competência à posição temporal numérica (distintas entre si).
    `incomparability` mapeia a chave da unidade ao texto do componente divergente. A saída segue a
    ordem das chaves (como `groupby(..., sort=True)`).
    """
    incomparability = incomparability or {}
    columns = [data[name].to_numpy(dtype=object).tolist() for name in (*keys, "period", *value_cols)]
    width = len(keys)
    time_pairs = {str(period): pair(position) for period, position in positions.items()}
    order = {str(period): position for period, position in positions.items()}
    density_mode = len(value_cols) > 1
    units: dict[tuple, list] = {}
    for record in zip(*columns):
        key, period, measures = record[:width], str(record[width]), record[width + 1:]
        if any(_missing(value) for value in measures):   # NaN ou ausente: observação ausente, não zero
            continue
        if density_mode:
            qn, qd = pair(measures[0])
            pn, pd_ = pair(measures[1])
            if pn <= 0:
                raise ValueError("Denominador populacional não positivo.")
            value = (scale * qn * pd_, qd * pn)
        else:
            value = pair(measures[0])
        units.setdefault(key, []).append((order[period], period, value))
    out = []
    for key in sorted(units, key=lambda item: tuple(str(part) for part in item)):
        series = sorted(units[key], key=lambda item: item[0])
        if len({item[0] for item in series}) != len(series):
            raise ValueError("Posições temporais repetidas na mesma unidade.")
        out.append((key, _trend_from_pairs([item[1] for item in series], [time_pairs[item[1]] for item in series],
                                           [item[2] for item in series], incomparability.get(key))))
    return out


def stage_block(distinct_periods: int) -> dict | None:
    """Pré-condição da etapa (L1769): menos de quatro competências distintas → BLQ-MET (SERIE_INSUFICIENTE)."""
    if distinct_periods >= MIN_OBSERVATIONS:
        return None
    return {"desfecho": "BLQ-MET", "motivo": "SERIE_INSUFICIENTE", "periodos_distintos": distinct_periods,
            "texto": TEXT_BLOCKED.format(quantidade=distinct_periods), "texto_minimo": TEXT_MINIMUM}


def summarize(trends: Iterable[Trend], *, block: dict | None = None) -> dict:
    """Contagens do motor por classe, motivo e família; desfecho da etapa (RQ-CAP-08, L1921)."""
    trends = list(trends)
    counts = dict.fromkeys(CLASSES, 0)
    motives = dict.fromkeys(MOTIVES, 0)
    missing = dict.fromkeys(NOT_EVALUABLE, 0)
    for item in trends:
        if item.category:
            counts[item.category] += 1
            if item.motive:
                motives[item.motive] += 1
        else:
            missing[item.not_evaluable] += 1
    families = {f: sum(n for c, n in counts.items() if FAMILY[c] == f) for f in FAMILIES}
    evaluable = sum(counts.values())
    classified = evaluable - counts["SEM_CLASSIFICACAO"]
    if block or not evaluable:
        outcome = "BLQ-MET"  # causa normativa preservada: série insuficiente ou incomparabilidade
    elif not classified:
        outcome = "RES-SCL"  # método executado sem classe; não é falta de dados
    elif sum(missing.values()):
        outcome = "RES-LIM"
    else:
        outcome = "RES-VAL"
    return {"capacidade": "CAP-TEN-01", "versao_metodo": METHOD_VERSION, "desfecho": outcome, "bloqueio": block,
            "unidades_total": len(trends), "avaliaveis": evaluable, "nao_avaliaveis": sum(missing.values()),
            "contagens": counts, "sem_classificacao_por_motivo": motives, "nao_avaliaveis_por_motivo": missing,
            "familias": families,
            "classes": [{"codigo": c, "rotulo": LABELS[c], "familia": FAMILY[c]} for c in CLASSES],
            "rotulos_familia": FAMILY_LABELS, "rotulos_nao_avaliavel": NOT_EVALUABLE_LABELS,
            "rotulos_motivo": MOTIVE_LABELS}
