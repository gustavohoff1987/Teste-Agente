"""Painel integrado de bolhas: os números que a tela posiciona, filtra e desenha (Adendo BOL-20261021 da SPEC e
contrato do painel de 21/10/2026; ver Docs/PAINEL_INTEGRADO.md).

Rotas POST /api/painel e POST /api/painel/referencias (main.py), só sobre a base Brasil oficial (fonte municipal),
numa competência e numa categoria. Nada aqui é fórmula nova; cada número vem do motor das análises:
- quantidade, população e densidade de cada município: data_contract.prepare, a mesma preparação da análise de
  densidade (CAP-IND-01 e CAP-IND-02; densidade = quantidade ÷ população × 1.000, em precisão integral);
- conjunto: main._compute(..., "aggregate"), a agregação municipal (CAP-AGR-01), soma dos componentes com possível
  dupla contagem (SOMA_DOS_COMPONENTES) e agregado parcial sobre os membros com registro (AGREGADO_PARCIAL);
- distância: nearest_reference.territory_coordinates e nearest_exact (CAP-ESP-01 e CAP-ESP-02), geodésica no GRS80
  (SIRGAS 2000) até a referência ou até o membro mais próximo do conjunto de referência, pelo mínimo do conjunto
  completo (uma referência sem coordenada válida deixa a distância não avaliável), com a camada complementar de
  coordenadas como na análise espacial;
- variação percentual: temporal_change.change (CAP-TMP-01, DA-14), em aritmética exata; base zero não é avaliável;
- ordem das referências candidatas: combined_criteria.ranking_of (CAP-SUB-02), empates na mesma posição (1, 2, 2, 4).

Não avaliáveis seguem com o motivo, nunca como zero (RQ-CAP-04, RQ-REP-04). A régua da tela é filtro visual sobre os
valores devolvidos (RQ-REP-06). Nada deste módulo vai ao provedor de IA.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from fractions import Fraction

import pandas as pd

from analysis_premises import apply_premises, limitations as premise_limitations, premise_notes
from brazil_catalog_profile import FIELDS, curated_profile, source_identity
from combined_criteria import ranking_of
from data_contract import ChoiceRequired, canonical_crs, count_unit_label, period_positions, prepare, text_values
from geo_complement import frame_identity
from nearest_reference import (CONDITION_TEXT, METHOD as DISTANCE_METHOD, MOTIVES, REFERENCIAL, TPL_11, _in_period,
                               nearest_exact, territory_coordinates)
from semantic_bridge import premise_reason
from temporal_change import change
from territorial_levels import MAX_IDS, _codes_text, human_period, municipal_index, parse as parse_scope, thousands
from territorial_selection import territory_catalog

METHOD = "PAINEL-BOLHAS-1"
OPERATION = "painel"
OFFICIAL_ONLY = ("O painel integrado usa só a base Brasil oficial (fonte municipal) nesta versão; um arquivo importado "
                 "segue pelas análises da preparação.")
GOVERNED = ("O painel usa as colunas do perfil oficial da base Brasil: código IBGE, município, período, categoria, "
            "quantidade e população e, com a referência, latitude e longitude.")
NO_CRS = ("A distância do painel precisa do referencial geodésico SIRGAS 2000, premissa governada da versão oficial da "
          "base Brasil; nesta versão da base ele não está estabelecido, e nenhum referencial é presumido.")
REQUIRED_ROLES = frozenset(("territory", "territory_id", "period", "category", "count", "population"))
SPATIAL_ROLES = frozenset(("latitude", "longitude"))
PANEL_KEYS = frozenset(("competencia", "competencia_inicial", "categoria", "base", "conjuntos", "referencia"))
REFERENCE_KEYS = frozenset(("competencia", "categoria", "universo", "criterio"))
ATTRIBUTES = {"densidade": "densidade", "quantidade": "quantidade", "populacao": "população"}
ORDERS = {"desc": "maior para menor", "asc": "menor para maior"}
FIELDS3 = ("populacao", "quantidade", "densidade")
LABELS3 = {"populacao": "população", "quantidade": "quantidade", "densidade": "densidade"}
DOMAINS = ("densidade", "quantidade", "populacao", "distancia_km", "variacao_densidade", "variacao_quantidade",
           "variacao_populacao")
SET_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
MAX_SETS = 50
MAX_LABEL = 120
SCOPE_SHAPE = "use {\"municipios\": {\"todos\", \"estados\", \"ids\"}}"
CRITERION_SHAPE = ("Critério inválido: use {\"atributo\": \"densidade\", \"quantidade\" ou \"populacao\", \"ordem\": "
                   "\"desc\" ou \"asc\"}.")


@dataclass
class Context:
    """O que vale para todo o pedido: fonte municipal, mapeamento, índice da versão, catálogo territorial, premissas
    (perfil oficial), competência, categoria e a posição temporal de cada competência."""
    municipal: pd.DataFrame
    mapping: dict
    index: object
    catalog: dict
    settings: dict
    period: str
    category: str
    positions: dict


@dataclass
class Measures:
    """Valores de uma competência: registros por código IBGE, linhas da fonte e o quadro preparado pelo motor."""
    period: str
    records: dict
    rows: pd.DataFrame
    data: pd.DataFrame | None


@dataclass
class Spatial:
    """Distâncias até a referência (mínimo do conjunto completo de CAP-ESP-02) para os alvos com coordenada válida."""
    settings: dict
    coords: pd.DataFrame
    references: list
    invalid: list
    values: dict

    def condition(self, key):
        return self.coords.at[key, "condicao"] if key in self.coords.index else "SEM_REGISTRO"


# --------------------------------------------------------------------------------------------- utilidades
def _num(value):
    """Número nativo para o JSON: inteiro quando o valor é inteiro; ausente, NaN e infinito viram null (nunca zero)."""
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _empty3():
    return {field: None for field in FIELDS3}


def _values3(record):
    return {field: _num(record["valores"][field]) for field in FIELDS3}


def _exact(record, field):
    """Valor exato (Fraction) de um registro: a densidade sai da quantidade e da população, sem passar pelo float
    (como em combined_criteria e trend)."""
    cache = record.setdefault("exatos", {})
    if field not in cache:
        values = record["valores"]
        cache[field] = (Fraction(values["quantidade"]) * 1000 / Fraction(values["populacao"]) if field == "densidade"
                        else Fraction(values[field]))
    return cache[field]


def _label(entry):
    """Nome do município com a UF do prefixo do código IBGE (regra brasil-cod-uf-prefix-1), como "MANAUS (AM)"."""
    if entry.get("state"):
        return entry["name"] + " (" + entry["state"] + ")"
    return entry["label"]


def _join(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " e " + parts[-1]


def _count(n):
    return thousands(n) + (" município" if n == 1 else " municípios")


def _no_record(ctx, period):
    return ("Sem registro em " + human_period(period) + " na categoria " + ctx.category +
            ": valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)")


def _no_initial(period):
    return ("Variação não avaliável: sem registro na competência inicial, " + human_period(period) +
            " (SEM_REGISTRO_OBSERVADO)")


# --------------------------------------------------------------------------------------------- pedido
def _keys(options, allowed):
    if not isinstance(options, dict):
        raise ValueError("Parâmetros do painel inválidos: envie um objeto JSON em options.")
    unknown = sorted(str(key)[:40] for key in set(options) - allowed)
    if unknown:
        raise ValueError("Parâmetro não reconhecido no painel: " + ", ".join(unknown[:5]) + ".")


def _period(value, periods, missing):
    if value is None or value == "":
        if len(periods) == 1:
            return periods[0]
        raise ValueError(missing)
    if not isinstance(value, str) or value.strip() not in periods:
        raise ValueError("Competência inexistente nesta versão da base: " + str(value)[:16] +
                         ". Escolha uma das competências da base.")
    return value.strip()


def _category(value, categories):
    if value is None or value == "":
        if len(categories) == 1:
            return categories[0]
        raise ValueError("Escolha a categoria profissional do painel.")
    if not isinstance(value, str) or value.strip() not in categories:
        raise ValueError("Categoria profissional inexistente nesta versão da base: " + str(value)[:40] + ".")
    return value.strip()


def context(sources, mapping, options, allowed) -> Context:
    """Validações comuns às duas rotas: base oficial, colunas do perfil, competência e categoria existentes."""
    _keys(options, allowed)
    municipal = sources.frame("municipal") if sources is not None else None
    if municipal is None or source_identity(municipal) != "municipal":
        raise ValueError(OFFICIAL_ONLY)
    if not isinstance(mapping, dict) or any(not isinstance(key, str) or not isinstance(value, (str, type(None)))
                                            for key, value in mapping.items()):
        raise ValueError("Mapeamento de colunas inválido.")
    # Papel sem coluna (vazio) não conta; sem mapeamento, vale o do perfil oficial, que o painel exige de todo modo.
    mapping = {key: value for key, value in mapping.items() if value} or dict(FIELDS["municipal"])
    profile = curated_profile(municipal, mapping)
    if not REQUIRED_ROLES <= set((profile or {}).get("governed_roles") or []):
        raise ValueError(GOVERNED)
    index = municipal_index(municipal)
    # As mesmas premissas da análise de densidade (perfil oficial, sem as premissas de coordenadas).
    settings = apply_premises(municipal, mapping, {}, spatial=False)
    catalog = {item["id"]: item for item in territory_catalog(municipal, mapping, settings)}
    periods = list(index.periods)
    period = _period(options.get("competencia"), periods, "Escolha a competência do painel.")
    category = _category(options.get("categoria"), list(index.categories))
    return Context(municipal, mapping, index, catalog, settings, period, category, period_positions(periods))


def _ids(values, ctx, what):
    """Identificadores de municípios existentes no catálogo da base (code:<código IBGE>), distintos."""
    if (not isinstance(values, list) or len(values) > MAX_IDS or
            any(not isinstance(value, str) or not value or len(value) > 512 for value in values) or
            len(set(values)) != len(values)):
        raise ValueError("Identificadores inválidos (" + what + "): use códigos distintos de municípios "
                         "(code:<código IBGE>).")
    unknown = [value for value in values if value not in ctx.catalog]
    if unknown:
        raise ValueError("Municípios inexistentes ou incompatíveis com a base (" + what + "): " +
                         ", ".join(unknown[:8]) + ".")
    ambiguous = [ctx.catalog[value]["label"] for value in values if ctx.catalog[value]["selection_reason"]]
    if ambiguous:
        raise ValueError("Identificação territorial ambígua entre níveis superiores: " + ", ".join(ambiguous[:8]) + ".")
    return list(values)


def _universe(raw, ctx, what, allow_empty):
    """Municípios de um universo com a forma de options.abrangencia.municipios (todos, estados inteiros ou ids), na
    ordem do código IBGE (RQ-REP-03). As regras da abrangência (territorial_levels.parse) valem aqui."""
    if raw is None or raw == {}:
        if allow_empty:
            return []
        raise ValueError("Escolha " + what + ".")
    if not isinstance(raw, dict) or set(raw) - {"municipios"} or not isinstance(raw.get("municipios"), dict):
        raise ValueError("Universo inválido (" + what + "): " + SCOPE_SHAPE + ".")
    municipios = raw["municipios"]
    if municipios.get("todos", False) is False and not municipios.get("estados") and not municipios.get("ids"):
        if allow_empty:
            return []
        raise ValueError("Nenhum município marcado (" + what + ").")
    if municipios.get("ids") is not None:
        _ids(municipios["ids"], ctx, what)
    scope = parse_scope({"municipios": municipios}, ctx.index.by_uf)
    if scope.mun_todos:
        codes = set(ctx.index.codes)
    else:
        codes = {ctx.catalog[item]["code"] for item in scope.ids}
        for prefix in scope.mun_estados:
            codes |= set(ctx.index.by_uf.get(prefix, ()))
    return ["code:" + code for code in sorted(codes)]


def _sets(raw, ctx):
    """Conjuntos agregados pedidos (CAP-AGR-01): id, rótulo e ao menos dois membros da base (podem estar fora de base)."""
    if raw is None or raw == []:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_SETS:
        raise ValueError("Conjuntos inválidos: envie uma lista de até " + str(MAX_SETS) + " conjuntos.")
    out, seen = [], set()
    for item in raw:
        if not isinstance(item, dict) or set(item) - {"id", "rotulo", "membros"}:
            raise ValueError("Conjunto inválido: use {\"id\", \"rotulo\", \"membros\"}.")
        key, label, members = item.get("id"), item.get("rotulo"), item.get("membros")
        if not isinstance(key, str) or not SET_ID.fullmatch(key) or key in seen:
            raise ValueError("Identificador de conjunto inválido ou repetido: use até 64 letras, números, _ ou -.")
        if not isinstance(label, str) or not label.strip() or len(label) > MAX_LABEL:
            raise ValueError("Rótulo do conjunto " + key + " inválido: use um texto de até " + str(MAX_LABEL) +
                             " caracteres.")
        if not isinstance(members, list) or not members:
            raise ValueError("O conjunto " + key + " está sem membros: escolha pelo menos dois municípios.")
        _ids(members, ctx, "membros do conjunto " + key)
        if len(members) < 2:
            raise ValueError("O conjunto " + key + " precisa de pelo menos dois municípios.")
        seen.add(key)
        out.append({"id": key, "rotulo": label.strip(), "membros": list(members)})
    return out


def _criterion(raw, ctx, allow_universe):
    """Critério de ordenação (CAP-SUB-02): atributo autorizado e direção, sempre escolhida pelo usuário."""
    if raw is None or raw == {}:
        return None
    allowed = {"atributo", "ordem"} | ({"universo"} if allow_universe else set())
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError(CRITERION_SHAPE)
    attribute, order = raw.get("atributo"), raw.get("ordem")
    if not isinstance(attribute, str) or attribute not in ATTRIBUTES:
        raise ValueError("Atributo do critério não reconhecido: use densidade, quantidade ou populacao.")
    if not isinstance(order, str) or order not in ORDERS:
        raise ChoiceRequired("Escolha a ordem do critério: desc (maior para menor) ou asc (menor para maior).")
    universe = None
    if raw.get("universo") is not None:
        universe = _universe(raw["universo"], ctx, "o universo da ordenação da referência", allow_empty=False)
    return {"atributo": attribute, "ordem": order, "universo": universe}


def _reference(raw, ctx):
    """Referência (CAP-REF-01): um município ou um conjunto de municípios escolhido pelo usuário; o critério só registra
    a origem."""
    if raw is None or raw == {}:
        return None
    if not isinstance(raw, dict) or set(raw) - {"membros", "criterio"}:
        raise ValueError("Referência inválida: use {\"membros\", \"criterio\"}.")
    members = raw.get("membros")
    if not isinstance(members, list) or not members:
        raise ValueError("Escolha o município de referência ou os membros do conjunto de referência.")
    _ids(members, ctx, "membros da referência")
    return {"membros": list(members), "criterio": _criterion(raw.get("criterio"), ctx, allow_universe=True)}


# --------------------------------------------------------------------------------------------- valores do motor
def _measures(ctx, period) -> Measures:
    """Quantidade, população e densidade de cada município na competência e na categoria: a preparação da análise de
    densidade (data_contract.prepare) sobre as linhas da competência; cada linha é local ao município."""
    frame, mapping = ctx.municipal, ctx.mapping
    mask = (text_values(frame[mapping["period"]]).isin([period]) &
            text_values(frame[mapping["category"]]).isin([ctx.category]))
    rows = frame.loc[mask.to_numpy(dtype=bool)]
    if rows.empty:
        return Measures(period, {}, rows, None)
    data = prepare(rows, mapping, ctx.settings, "density").copy()
    data["code"] = data["territory"].str.extract(r"\[([^\[\]]+)\]$", expand=False)
    records = {}
    for code, quantity, population, density in zip(data["code"].tolist(), data["quantity"].tolist(),
                                                   data["population"].tolist(), data["density"].tolist()):
        records[str(code)] = {"valores": {"populacao": population, "quantidade": quantity, "densidade": density}}
    return Measures(period, records, rows, data)


def _aggregate(ctx, measures, codes):
    """CAP-AGR-01 pelo motor da agregação municipal (main._compute, operação aggregate), sobre os membros com registro na
    competência: soma das quantidades, soma das populações (cada município uma vez) e densidade do conjunto."""
    import main as engine  # importação tardia: main usa este módulo
    data = measures.data
    chosen = data[data["code"].isin(codes)][["territory", "period", "category", "quantity", "population", "density"]]
    row = engine._compute(measures.rows, ctx.mapping, "aggregate", ctx.settings,
                          prepared=chosen.reset_index(drop=True))["rows"][0]
    return {"valores": {"populacao": row["População"], "quantidade": row["Quantidade"],
                        "densidade": row["Densidade por 1.000"]}, "tipo": row["Tipo"]}


def _ranking(ctx, measures, members, criterion):
    """CAP-SUB-02 (combined_criteria.ranking_of): valores exatos, empates na mesma posição (1, 2, 2, 4) e não
    avaliáveis à parte, sem posição."""
    attribute = criterion["atributo"]
    values, names = {}, {}
    for key in members:
        entry = ctx.catalog[key]
        names[key] = {"name": entry["name"]}
        record = measures.records.get(entry["code"])
        if record is None:
            values[key] = {"avaliavel": False, "motivos": [_no_record(ctx, measures.period)]}
        else:
            values[key] = {"avaliavel": True, "valor": record["valores"][attribute], "exato": _exact(record, attribute)}
    ordered, positions, not_evaluable = ranking_of(values, members, names, criterion["ordem"])
    return ordered, positions, not_evaluable, values


def _spatial(ctx, references, targets) -> Spatial:
    """Coordenadas da competência e distância de cada alvo até a referência mais próxima do conjunto completo de
    referências (nearest_exact, como em compute_nearest). Com alguma referência sem coordenada válida, nenhuma
    distância é avaliável (DEPENDENCIA_NAO_AVALIAVEL), sem substituição pelo mínimo entre as avaliáveis."""
    settings = apply_premises(ctx.municipal, ctx.mapping, {}, spatial=True)
    if not SPATIAL_ROLES <= set(settings.get("governed_roles") or []):
        raise ValueError(GOVERNED)
    if canonical_crs(settings.get("crs")) != REFERENCIAL:
        raise ChoiceRequired(NO_CRS)
    geometry = _in_period(ctx.municipal, ctx.mapping, ctx.period)
    coords = territory_coordinates(geometry, ctx.mapping, settings)
    spatial = Spatial(settings, coords, list(references), [], {})
    spatial.invalid = [(key, spatial.condition(key)) for key in references if spatial.condition(key) != "VALIDA"]
    valid = [key for key in dict.fromkeys(targets) if spatial.condition(key) == "VALIDA"]
    if not spatial.invalid and valid:
        best, _, _ = nearest_exact(coords.loc[valid, "lat"], coords.loc[valid, "lon"],
                                   coords.loc[list(references), "lat"], coords.loc[list(references), "lon"])
        spatial.values = {key: float(best[i]) / 1000 for i, key in enumerate(valid)}
    return spatial


def _reference_gap(ctx, spatial):
    names = [_label(ctx.catalog[key]) + " (" + MOTIVES[state] + ")" for key, state in spatial.invalid[:5]]
    more = " e mais " + str(len(spatial.invalid) - 5) if len(spatial.invalid) > 5 else ""
    return ("Distância não avaliável em " + human_period(ctx.period) + ": sem coordenada válida " +
            ("na referência " if len(spatial.invalid) == 1 else "nas referências ") + _join(names) + more +
            " (DEPENDENCIA_NAO_AVALIAVEL)")


def _distance_reason(ctx, spatial, key):
    """Motivo da distância não avaliável de um município (None quando a falta de registro já é o motivo do item)."""
    state = spatial.condition(key)
    if state == "SEM_REGISTRO":
        return None
    if state != "VALIDA":
        return ("Distância não avaliável em " + human_period(ctx.period) + ": " + CONDITION_TEXT[state] + " (" +
                MOTIVES[state] + ")")
    return _reference_gap(ctx, spatial) if spatial.invalid else None


def _percentages(before, after):
    """CAP-TMP-01 campo a campo: temporal_change.change sobre os valores exatos; base zero fica nula, com o motivo."""
    variation, zero = {}, []
    for field in FIELDS3:
        percent = change(_exact(before, field), _exact(after, field))["variacao_percentual"]
        variation[field] = None if percent is None else _num(float(percent))
        if percent is None:
            zero.append(field)
    if not zero:
        return variation, True, []
    return variation, False, ["Variação percentual " + _join(["da " + LABELS3[field] for field in zero]) +
                              " não avaliável: valor inicial zero (BASE_ZERO)"]


# --------------------------------------------------------------------------------------------- itens
def _unit_item(ctx, key, final, initial, spatial, reference_ids):
    entry = ctx.catalog[key]
    record = final.records.get(entry["code"])
    motives = [] if record is not None else [_no_record(ctx, final.period)]
    values = record["valores"] if record is not None else {}
    item = {"id": key, "tipo": "municipio", "rotulo": _label(entry), "uf": entry.get("state") or None,
            "populacao": _num(values.get("populacao")), "quantidade": _num(values.get("quantidade")),
            "densidade": _num(values.get("densidade")), "distancia_km": None}
    distance_ok = None
    if spatial is not None:
        value = spatial.values.get(key)
        item["distancia_km"] = _num(value)
        distance_ok = value is not None
        reason = None if distance_ok else _distance_reason(ctx, spatial, key)
        if reason:
            motives.append(reason)
    inicial, variation, variation_ok = _empty3(), _empty3(), None
    if initial is not None:
        variation_ok = False
        before = initial.records.get(entry["code"])
        if before is not None:
            inicial = _values3(before)
        if record is not None and before is None:
            motives.append(_no_initial(initial.period))
        elif record is not None:
            variation, variation_ok, why = _percentages(before, record)
            motives += why
    item.update({"inicial": inicial, "variacao_percentual": variation,
                 "avaliavel": {"densidade": item["densidade"] is not None, "distancia": distance_ok,
                               "variacao": variation_ok},
                 "motivos": motives, "referencia": key in reference_ids})
    return item


def _set_item(ctx, spec, final, initial, spatial, reference):
    members = spec["membros"]
    codes = {key: ctx.catalog[key]["code"] for key in members}
    present = [key for key in members if codes[key] in final.records]
    motives, record = [], None
    if present:
        record = _aggregate(ctx, final, [codes[key] for key in present])
        if len(present) < len(members):
            outside = [_label(ctx.catalog[key]) for key in members if key not in present]
            motives.append("Agregado parcial em " + human_period(final.period) + ": " + str(len(present)) + " de " +
                           str(len(members)) + " municípios com registro; fora: " + ", ".join(outside[:8]) +
                           (" e mais " + str(len(outside) - 8) if len(outside) > 8 else "") +
                           "; o valor não representa o conjunto completo (AGREGADO_PARCIAL)")
    else:
        motives.append("Nenhum membro do conjunto tem registro em " + human_period(final.period) + " na categoria " +
                       ctx.category + " (SEM_REGISTRO_OBSERVADO)")
    values = record["valores"] if record is not None else {}
    item = {"id": spec["id"], "tipo": "conjunto", "rotulo": spec["rotulo"], "membros": list(members),
            "populacao": _num(values.get("populacao")), "quantidade": _num(values.get("quantidade")),
            "densidade": _num(values.get("densidade")), "contagem": "SOMA_DOS_COMPONENTES",
            "distancia_km": None, "distancia_km_max": None}
    distance_ok = None
    if spatial is not None:
        distance_ok = False
        found = [spatial.values.get(key) for key in present]
        if present and all(value is not None for value in found):
            # Membro mais próximo e membro mais distante da referência, no mesmo suporte dos valores do conjunto.
            item["distancia_km"], item["distancia_km_max"] = _num(min(found)), _num(max(found))
            distance_ok = True
        elif present:
            missing = [_label(ctx.catalog[key]) for key in present if spatial.values.get(key) is None]
            motives.append(_reference_gap(ctx, spatial) if spatial.invalid else
                           "Distância não avaliável em " + human_period(ctx.period) + ": sem coordenada válida em " +
                           _join(missing[:5]) + (" e mais " + str(len(missing) - 5) if len(missing) > 5 else "") +
                           " (DEPENDENCIA_NAO_AVALIAVEL)")
    inicial, variation, variation_ok = _empty3(), _empty3(), None
    if initial is not None:
        variation_ok = False
        before = [key for key in members if codes[key] in initial.records]
        record0 = _aggregate(ctx, initial, [codes[key] for key in before]) if before else None
        if record0 is not None:
            inicial = _values3(record0)
        if record is None:
            pass  # o motivo da falta de registro na competência já está no item
        elif record0 is None:
            motives.append(_no_initial(initial.period))
        elif set(before) != set(present):
            # CAP-AGR-01 e CAP-TMP-01: os membros efetivos precisam ser os mesmos nas duas competências.
            motives.append("Variação não avaliável: os membros com registro mudam entre " + human_period(initial.period) +
                           " (" + str(len(before)) + ") e " + human_period(final.period) + " (" + str(len(present)) +
                           "); cada valor vale isoladamente (INCOMPARABILIDADE)")
        else:
            variation, variation_ok, why = _percentages(record0, record)
            motives += why
    item.update({"inicial": inicial, "variacao_percentual": variation,
                 "avaliavel": {"densidade": item["densidade"] is not None, "distancia": distance_ok,
                               "variacao": variation_ok},
                 "motivos": motives,
                 "referencia": reference is not None and set(members) == set(reference["membros"])})
    return item


def _domains(items):
    """Mínimo e máximo dos valores avaliáveis devolvidos (inclusive os da competência inicial e a distância do membro
    mais distante dos conjuntos); null quando não há valor avaliável."""
    def span(values):
        present = [value for value in values if value is not None]
        return [min(present), max(present)] if present else None
    domains = {field: span([item[field] for item in items] + [item["inicial"][field] for item in items])
               for field in FIELDS3}
    domains["distancia_km"] = span([item["distancia_km"] for item in items] +
                                   [item.get("distancia_km_max") for item in items])
    for field in FIELDS3:
        domains["variacao_" + field] = span([item["variacao_percentual"][field] for item in items])
    return {key: domains[key] for key in DOMAINS}


def _origin(ctx, reference, base, final):
    """Forma de definição e origem da referência (CAP-REF-01). Com critério, a posição é recalculada pelo motor
    (CAP-SUB-02) no universo informado ou, sem ele, entre os municípios base."""
    members = reference["membros"]
    single = len(members) == 1
    tail = "" if single else "; a distância vai até o membro mais próximo (mínimo do conjunto completo, CAP-ESP-02)"
    criterion = reference["criterio"]
    if criterion is None:
        return ("Escolhida por você (lista explícita); nenhuma referência foi escolhida pelo sistema" if single else
                "Conjunto de " + str(len(members)) + " municípios escolhido por você (lista explícita)") + tail
    head = (("Escolhida" if single else "Conjunto escolhido") + " pelo critério " + ATTRIBUTES[criterion["atributo"]] +
            " (" + ORDERS[criterion["ordem"]] + ")")
    universe = criterion["universo"]
    scope = "no universo da ordenação (" + _count(len(universe or [])) + ")"
    if universe is None:
        universe, scope = base, "entre os municípios base (" + _count(len(base)) + ")"
    if not universe:
        return head + ", em " + human_period(ctx.period) + tail
    _, positions, _, _ = _ranking(ctx, final, universe, criterion)
    places = [positions.get(key) for key in members]
    if single:
        where = (str(places[0]) + "ª posição " if places[0] else "fora da ordenação ") + scope
    else:
        where = "posições " + _join([str(place) if place else "fora da ordenação" for place in places]) + " " + scope
    return head + ", " + where + " em " + human_period(ctx.period) + tail


# --------------------------------------------------------------------------------------------- notas e chave
def _notes(ctx, base, sets, items, final, initial, spatial, reference):
    unit = count_unit_label(ctx.mapping, ctx.settings)
    notes = [*premise_notes(ctx.settings, "density", ctx.mapping),
             "Valores de " + ctx.category + " em " + human_period(ctx.period) + " pela mesma preparação da análise de "
             "densidade. Densidade = quantitativo / população × 1.000 (por 1.000 habitantes, em precisão integral; o "
             "arredondamento é só da apresentação).",
             "Valores ausentes e denominadores nulos não são transformados em zero; itens não avaliáveis seguem com o "
             "motivo.",
             "Unidade de contagem: " + unit + ". Não há conversão entre pessoas, vínculos e postos.",
             "Identificação territorial: código IBGE do perfil da base oficial; a UF segue o prefixo do código "
             "(regra brasil-cod-uf-prefix-1)."]
    for label, measures in (("Municípios base", final), ("Municípios base na competência inicial", initial)):
        if not base or measures is None:
            continue
        missing = [ctx.catalog[key]["code"] for key in base if ctx.catalog[key]["code"] not in measures.records]
        text = (label + " (" + human_period(measures.period) + "): " + thousands(len(base) - len(missing)) + " de " +
                thousands(len(base)) + " com registro")
        notes.append(text + ("; sem registro (não avaliáveis): " + _codes_text(missing) if missing else "") + ".")
    if sets:
        notes.append("Conjuntos (CAP-AGR-01): soma das contagens dos componentes, com possível dupla contagem; quem atua "
                     "em mais de um município é contado em cada um, e o total não é o número de profissionais "
                     "distintos. Densidade do conjunto = soma dos quantitativos / soma das populações × 1.000, cada "
                     "população municipal uma vez. Membro sem registro na competência fica fora (agregado parcial, "
                     "AGREGADO_PARCIAL).")
        notes += premise_notes(ctx.settings, "aggregate", ctx.mapping)
    if spatial is not None:
        if spatial.values:
            notes.append(TPL_11)
        notes.append("Referencial geodésico " + REFERENCIAL + " (elipsoide GRS80, a = 6.378.137 m, 1/f = "
                     "298,257222101); distância pelo problema geodésico inverso de Karney, em quilômetros e sem "
                     "arredondamento no cálculo.")
        notes.append("Coordenadas da competência " + ctx.period + "; coordenadas de outras competências não são "
                     "tratadas como equivalentes.")
        members = reference["membros"]
        notes.append("Referência: " + _join([_label(ctx.catalog[key]) for key in members[:8]]) +
                     (" e mais " + str(len(members) - 8) if len(members) > 8 else "") +
                     ("" if len(members) == 1 else "; a distância de cada item vai até o membro mais próximo (mínimo "
                      "do conjunto completo, CAP-ESP-02)") + ". A condição de referência não tem caráter normativo.")
        if spatial.invalid:
            notes.append(str(len(spatial.invalid)) + " referência(s) sem coordenada válida: " + "; ".join(
                _label(ctx.catalog[key]) + " (" + MOTIVES[state] + ")" for key, state in spatial.invalid[:10]) +
                ". A distância até a referência (mínimo do conjunto completo) fica não avaliável para todos os itens; "
                "nenhuma distância parcial é apresentada no lugar dela.")
        complement = spatial.coords.attrs.get("complemento")
        if complement is not None:
            if complement.get("municipios_complementados"):
                notes.append("Coordenadas de " + str(len(complement["municipios_complementados"])) + " município(s) com "
                             "ponto inválido na fonte original vêm da camada geográfica complementar versionada (" +
                             str(complement.get("identificador")) + ", versão " + str(complement.get("versao")) +
                             "), sob a premissa do usuário de coordenada fixa de 2014 a 2024; os arquivos originais não "
                             "foram alterados.")
            elif complement.get("estado") != "valido":
                notes.append("Camada geográfica complementar " + str(complement.get("estado")) + ": " +
                             str(complement.get("motivo")) + ". Municípios com coordenada inválida na fonte original "
                             "permanecem não avaliáveis.")
        notes += premise_notes(spatial.settings, "nearest", ctx.mapping)
    if initial is not None:
        notes.append("Variação percentual (CAP-TMP-01) entre " + human_period(initial.period) + " e " +
                     human_period(ctx.period) + ": (valor final − valor inicial) / valor inicial × 100, em aritmética "
                     "exata, para população, quantidade e densidade; não indica tendência. Com valor inicial zero, a "
                     "variação percentual não é avaliável (BASE_ZERO); conjunto com membros diferentes entre as "
                     "competências não tem variação (INCOMPARABILIDADE).")
        notes += premise_notes(ctx.settings, "temporal", ctx.mapping)
    used = {ctx.catalog[key]["code"] for key in base} | {ctx.catalog[key]["code"] for spec in sets for key in spec["membros"]}
    if reference is not None:
        used |= {ctx.catalog[key]["code"] for key in reference["membros"]}
    for measures in (final, initial):
        if measures is None:
            continue
        codes = sorted(used & set(ctx.index.divergent.get(measures.period, [])))
        if codes:
            notes.append("Em " + human_period(measures.period) + ", " + str(len(codes)) + " registro(s) da fonte municipal "
                         "trazem na coluna uf um estado diferente do indicado pelo código IBGE (" + _codes_text(codes) +
                         "); o estado segue o código, e os valores entram como estão na fonte.")
    return list(dict.fromkeys(notes))


def _limitations(ctx, sets, items, spatial):
    found = []
    if sets:
        found += ["SOMA_COM_POSSIVEL_DUPLA_CONTAGEM", *premise_limitations(ctx.settings, "aggregate")]
    if any("(AGREGADO_PARCIAL)" in text for item in items for text in item["motivos"]):
        found.append("AGREGADO_PARCIAL")
    if spatial is not None and spatial.values:
        found.append("DISTANCIA_GEODESICA_DIRETA")
    if any(flag is False for item in items for flag in item["avaliavel"].values()):
        found.append("UNIDADES_NAO_AVALIAVEIS")
    return list(dict.fromkeys(found))


def _execution_key(ctx, final, initial, normalized, spatial):
    """Chave reproduzível, como em /api/analyze: dados usados, fonte (versão verificada), mapeamento, pedido
    normalizado, premissas, operação e métodos (com a camada de coordenadas válida, quando há distância)."""
    digest = hashlib.sha256()
    for measures in (final, initial):
        if measures is not None and not measures.rows.empty:
            digest.update(pd.util.hash_pandas_object(measures.rows, index=True).values.tobytes())
    signature = {"data": digest.hexdigest(), "source": ctx.municipal.attrs.get("source"), "mapping": ctx.mapping,
                 "options": normalized, "operation": OPERATION, "method": METHOD,
                 "premissas": sorted(set(ctx.settings.get("governed_premises") or []) |
                                     set(ctx.settings.get("analysis_premises") or []))}
    if initial is not None:
        signature["variacao"] = "CAP-TMP-01/DA-14"
    if spatial is not None:
        signature["distancia"] = {"metodo": DISTANCE_METHOD["versao"], "referencial": REFERENCIAL,
                                  "premissas": sorted(spatial.settings.get("governed_premises") or [])}
        geo = frame_identity(ctx.municipal)
        if geo.get("estado") == "valido":
            signature["geo_complement"] = geo
    return hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


# --------------------------------------------------------------------------------------------- rotas
def compute(sources, mapping, options) -> dict:
    """POST /api/painel: municípios base, conjuntos e referência numa competência, com a variação desde a competência
    inicial quando pedida."""
    ctx = context(sources, mapping, options, PANEL_KEYS)
    initial_period = None
    if options.get("competencia_inicial") not in (None, ""):
        initial_period = _period(options["competencia_inicial"], list(ctx.index.periods), "")
        if ctx.positions[initial_period] >= ctx.positions[ctx.period]:
            raise ValueError("A competência inicial (" + initial_period + ") precisa ser anterior à competência do "
                             "painel (" + ctx.period + ").")
        for key in ("temporal_comparability_confirmed", "territory_longitudinal_confirmed"):
            if not ctx.settings.get(key):
                raise ChoiceRequired(premise_reason(ctx.settings, key))
    base = _universe(options.get("base"), ctx, "os municípios base", allow_empty=True)
    sets = _sets(options.get("conjuntos"), ctx)
    if not base and not sets:
        raise ValueError("Escolha os municípios base ou um conjunto para o painel.")
    reference = _reference(options.get("referencia"), ctx)
    final = _measures(ctx, ctx.period)
    initial = _measures(ctx, initial_period) if initial_period else None
    reference_ids = reference["membros"] if reference is not None else []
    # Os membros da referência entram como itens (distância zero); a ordem padrão é a do código IBGE (RQ-REP-03).
    units = sorted(set(base) | set(reference_ids), key=lambda key: (ctx.catalog[key]["code"], key))
    spatial = None
    if reference is not None:
        spatial = _spatial(ctx, reference_ids, units + [key for spec in sets for key in spec["membros"]])
    items = [_unit_item(ctx, key, final, initial, spatial, set(reference_ids)) for key in units]
    items += [_set_item(ctx, spec, final, initial, spatial, reference) for spec in sets]
    block = None
    if reference is not None:
        block = {"tipo": "municipio" if len(reference_ids) == 1 else "conjunto",
                 "membros": [{"id": key, "rotulo": _label(ctx.catalog[key])} for key in reference_ids],
                 "origem": _origin(ctx, reference, base, final)}
    normalized = {"competencia": ctx.period, "competencia_inicial": initial_period, "categoria": ctx.category,
                  "base": base, "conjuntos": [{**spec, "membros": sorted(spec["membros"])} for spec in sets],
                  "referencia": None if reference is None else {
                      "membros": sorted(reference_ids),
                      "criterio": None if reference["criterio"] is None else {
                          key: value for key, value in reference["criterio"].items()}}}
    return {"competencia": ctx.period, "competencia_inicial": initial_period, "categoria": ctx.category,
            "versao_base": (ctx.municipal.attrs.get("source") or {}).get("version"),
            "chave_execucao": _execution_key(ctx, final, initial, normalized, spatial),
            "referencia": block, "itens": items, "dominios": _domains(items),
            "notas": _notes(ctx, base, sets, items, final, initial, spatial, reference),
            "limitacoes": _limitations(ctx, sets, items, spatial)}


def references(sources, mapping, options) -> dict:
    """POST /api/painel/referencias: candidatos do universo na ordem do critério (CAP-SUB-02), com empates na mesma
    posição e não avaliáveis à parte. "Usar o primeiro" é a seleção por posição (CAP-SUB-03), feita na tela."""
    ctx = context(sources, mapping, options, REFERENCE_KEYS)
    universe = _universe(options.get("universo"), ctx, "o universo das referências", allow_empty=False)
    criterion = _criterion(options.get("criterio"), ctx, allow_universe=False)
    if criterion is None:
        raise ValueError("Escolha o critério das referências: atributo (densidade, quantidade ou populacao) e ordem.")
    final = _measures(ctx, ctx.period)
    ordered, positions, not_evaluable, values = _ranking(ctx, final, universe, criterion)

    def unit(key):
        entry = ctx.catalog[key]
        return {"id": key, "rotulo": _label(entry), "uf": entry.get("state") or None}

    return {"criterio": {"atributo": criterion["atributo"], "ordem": criterion["ordem"]},
            "competencia": ctx.period, "categoria": ctx.category,
            "candidatos": [{**unit(key), "valor": _num(values[key]["valor"]), "posicao": positions[key]}
                           for key in ordered],
            "nao_avaliaveis": [{**unit(key), "motivos": list(values[key]["motivos"])} for key in not_evaluable]}
