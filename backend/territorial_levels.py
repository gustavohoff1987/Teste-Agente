"""Níveis territoriais da base Brasil oficial: Brasil, estados e municípios (decisões D3, D4 e D5 do responsável pelo
produto, 19/10/2026).

- Brasil (BR): contagem nacional de Dados_Brasil.xlsx, nunca a soma dos municípios. Densidade pela regra governada
  BR-POP-JUNHO-1 (D4): a população do ano é a soma da população estimada dos municípios na competência de junho, cada
  município uma vez, e vale para janeiro e para junho do mesmo ano. Município sem registro em junho não é estimado: a
  população soma os municípios com registro, e o valor fica avaliável com limitações (POPULACAO_NACIONAL_PARCIAL).
- Estado (UF): soma dos municípios pelo prefixo do código IBGE (regra brasil-cod-uf-prefix-1; a coluna uf da fonte não
  é usada), sempre SOMA_DOS_COMPONENTES, com possível dupla contagem e nunca comparada com o total do Brasil.
- Município (MUN): o caminho municipal atual; "Todos os municípios" e "Municípios de um estado" são expansões.

Cada nível é um universo próprio e nenhum nível é somado a outro (RQ-DAD-30). As linhas de cada universo vêm do mesmo
motor: data_contract.prepare, main._compute com o quadro já preparado e temporal_change.evolution na evolução. A taxa
nacional (D5) é referência de contexto no resultado da densidade: não classifica nem colore os municípios e não entra
em rankings, distribuições ou agregações. Nada deste módulo vai ao provedor de IA.
"""
from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

import numpy as np
import pandas as pd

from analysis_catalog import ENGINE_OPERATION_LABELS
from brazil_catalog_profile import FIELDS, curated_profile, source_identity
import comparison_window
from data_contract import (ChoiceRequired, comparison_window as comparison_window_periods, count_unit_label, numbers,
                           period_positions, prepare, resolve_convention, scoped, text_values)
from territorial_selection import STATES, territory_catalog

BR, UF, MUN = "BR", "UF", "MUN"
ORDER = (BR, UF, MUN)
LEVEL_LABELS = {BR: "Brasil (total nacional)", UF: "Estado (soma dos municípios)", MUN: "Município"}
COUNT_TYPES = {BR: "Unidades distintas: contagem nacional (não é a soma dos municípios)",
               UF: "Soma dos componentes (possível dupla contagem)", MUN: "Unidades distintas no município"}
METODOS = {"niveis": "NIVEIS-BR-UF-MUN-1", "populacao_nacional": "BR-POP-JUNHO-1", "estado": "brasil-cod-uf-prefix-1"}
# Linha da fonte municipal cuja coluna uf contradiz o prefixo do código (hoje só 251365 em 2016/6). Falso: entra como
# está, com nota de qualidade (decisão residual 1). Verdadeiro: a linha fica fora das somas (o município passa a
# ausente naquela competência, e o estado e a população do Brasil daquele ano ficam parciais).
UF_DIVERGENTE_EXCLUI = False
MAX_IDS = 10000
_CACHE: dict[tuple, "MunicipalIndex"] = {}
_LOCK = threading.Lock()

ROTATION = ("A rotatividade não está disponível nos dados do Brasil: falta um identificador da mesma pessoa entre os "
            "períodos.")
WHY_BR = {
    "distribution": "Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só.",
    "ranking": "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só.",
    "aggregate": "Não se aplica: o total do Brasil vem pronto da fonte nacional e não é somado a outros territórios.",
    "spatial": "Não se aplica: as distâncias e os critérios usam a localização de cada município.",
    "nearest": "Não se aplica: as distâncias e os critérios usam a localização de cada município.",
    "criteria": "Não se aplica: as distâncias e os critérios usam a localização de cada município.",
    "rotation": ROTATION,
}
WHY_UF = {
    "spatial": "Não se aplica: estados não têm um ponto único. Para usar os municípios de um estado, marque o grupo em "
               "Municípios.",
    "nearest": "Não se aplica: estados não têm um ponto único. Para usar os municípios de um estado, marque o grupo em "
               "Municípios.",
    "criteria": "Não se aplica: estados não têm um ponto único. Para usar os municípios de um estado, marque o grupo em "
                "Municípios.",
    "rotation": ROTATION,
}
TEXT_BLOCKS = "Marque o Brasil, estados e municípios; cada nível aparece em um bloco separado no resultado."
TEXTS = {
    "density": TEXT_BLOCKS, "counts": TEXT_BLOCKS, "temporal": TEXT_BLOCKS, "report": TEXT_BLOCKS,
    "comparisons": "Compare dois ou mais territórios. Maior, menor e diferença só entre territórios do mesmo nível; níveis "
                   "diferentes aparecem lado a lado.",
    "distribution": "A distribuição agrupa dois ou mais territórios do mesmo nível: só estados ou só municípios.",
    "ranking": "O ranking ordena dois ou mais territórios do mesmo nível: só estados ou só municípios.",
    "aggregate": "A agregação soma os municípios marcados; marcar um estado inclui todos os municípios dele. O resultado é "
                 "um valor só.",
    "spatial": "As distâncias são calculadas entre municípios, numa competência. Marque municípios ou use todos.",
    "nearest": "Marque os municípios-alvo ou use todos.",
    "criteria": "Os critérios são avaliados em cada município marcado ou em todos.",
    "rotation": ROTATION,
}
ALL_LEVELS = ["brasil", "estado", "municipio"]


def _rule(accepts, state_as, minimum, combination, default, available=True):
    return {"aceita": list(accepts), "estado_como": state_as, "minimo": minimum, "combinacao": combination,
            "padrao": default, "disponivel": available}


# Matriz de níveis por análise (base oficial). "motivos" e "texto" são preenchidos abaixo.
OPERATION_LEVELS = {
    "density": _rule(ALL_LEVELS, "objeto", 1, "blocos", "todos_municipios"),
    "counts": _rule(ALL_LEVELS, "objeto", 1, "blocos", "brasil"),
    "report": _rule(ALL_LEVELS, "objeto", 1, "blocos", "brasil"),
    "temporal": _rule(ALL_LEVELS, "objeto", 1, "blocos", "brasil"),
    "comparisons": _rule(ALL_LEVELS, "objeto", 2, "lado_a_lado", "todos_municipios"),
    "distribution": _rule(["estado", "municipio"], "objeto", 2, "mesmo_nivel", "todos_municipios"),
    "ranking": _rule(["estado", "municipio"], "objeto", 2, "mesmo_nivel", "todos_municipios"),
    "aggregate": _rule(["estado", "municipio"], "expansao", 2, "uniao", "todos_municipios"),
    "spatial": _rule(["municipio"], None, 1, "municipal", "todos_municipios"),
    "nearest": _rule(["municipio"], None, 1, "municipal", "todos_municipios"),
    "criteria": _rule(["municipio"], None, 1, "municipal", "todos_municipios"),
    "rotation": _rule([], None, 0, "municipal", None, available=False),
}
for _operation, _item in OPERATION_LEVELS.items():
    _item["texto"] = TEXTS[_operation]
    _item["motivos"] = {key: text for key, text in (("brasil", WHY_BR.get(_operation)), ("estado", WHY_UF.get(_operation)))
                        if text}
    if _operation == "rotation":
        _item["motivos"]["municipio"] = ROTATION

NOTE_LEVELS = "Brasil, estados e municípios aparecem em blocos separados; nenhum nível foi somado a outro."
NOTE_STATES = ("Estados: soma dos municípios de cada estado (código IBGE). Quem atua em mais de um município é contado em "
               "cada um; o valor não é o número de médicos diferentes do estado e não é comparado com o total do Brasil.")
NOTE_STATES_ORDER = "A dupla contagem varia entre os estados; a ordem e as classes podem refletir isso."
NOTE_JANUARY = ("Em janeiro, a população do Brasil é a de junho do mesmo ano; nos estados e municípios, é a da própria "
                "competência.")
NOTE_REFERENCE = ("Taxa nacional como referência de contexto: não classifica nem colore os municípios e não entra em "
                  "rankings, distribuições ou agregações.")
BR_UNAVAILABLE = "Brasil (total nacional) indisponível: as duas fontes precisam estar no perfil oficial da base Brasil."
OFFICIAL_ONLY = "A abrangência por Brasil e estados existe só na base Brasil oficial."
GOVERNED_COLUMNS = ("Brasil e estados exigem as colunas do perfil oficial da base Brasil (código IBGE, município, período, "
                    "categoria e quantidade; população na densidade).")
SELECTION_RULE = "Seleção territorial deve conter identificadores distintos e não pode ser vazia."
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
          "novembro", "dezembro"]
# Preposição usada no nome do grupo ("Municípios do Amazonas"): o frontend não monta gramática.
_PREPOSITIONS = {"12": "do", "27": "de", "16": "do", "13": "do", "29": "da", "23": "do", "53": "do", "32": "do",
                 "52": "de", "21": "do", "51": "de", "50": "de", "31": "de", "15": "do", "25": "da", "41": "do",
                 "26": "de", "22": "do", "33": "do", "24": "do", "43": "do", "11": "de", "14": "de", "42": "de",
                 "35": "de", "28": "de", "17": "do"}


def human_period(value: str) -> str:
    value = str(value)
    if re.fullmatch(r"\d{6}", value) and 1 <= int(value[4:]) <= 12:
        return MONTHS[int(value[4:]) - 1] + " de " + value[:4]
    return value


def thousands(value) -> str:
    return f"{int(value):,}".replace(",", ".")


def uf_label(prefix: str) -> str:
    return STATES[prefix][1] + " (" + STATES[prefix][0] + ")"


def group_label(prefix: str) -> str:
    return "Municípios " + _PREPOSITIONS.get(prefix, "de") + " " + STATES[prefix][1]


def _plural(n: int, singular: str, plural: str) -> str:
    return singular if n == 1 else plural


def _codes_text(codes, limit: int = 8) -> str:
    codes = list(codes)
    shown = ", ".join(codes[:limit])
    return shown + (" e mais " + str(len(codes) - limit) if len(codes) > limit else "")


# --------------------------------------------------------------------------------------------- índice por versão
@dataclass
class MunicipalIndex:
    """Fatos da fonte municipal oficial de uma versão: códigos, membros por estado, nomes, linhas com uf divergente
    e população nacional de junho por ano (BR-POP-JUNHO-1). Guardado por versão; nunca em attrs."""
    version: str | None
    codes: tuple
    by_uf: dict
    names: dict
    periods: tuple
    categories: tuple
    divergent: dict
    population: dict
    excluded: frozenset = field(default_factory=frozenset)


def _build_index(municipal: pd.DataFrame) -> MunicipalIndex:
    mapping = FIELDS["municipal"]
    codes = text_values(municipal[mapping["territory_id"]])
    names = text_values(municipal[mapping["territory"]])
    periods = text_values(municipal[mapping["period"]])
    categories = text_values(municipal[mapping["category"]])
    table = pd.DataFrame({"code": codes, "name": names, "period": periods})
    if table.isna().any().any():
        raise ValueError("Há códigos, nomes ou períodos ausentes na fonte municipal; os níveis não são calculados.")
    expected = sorted(set(table.code))
    by_uf: dict[str, list] = {}
    for code in expected:
        if re.fullmatch(r"\d{6,7}", code) and code[:2] in STATES:
            by_uf.setdefault(code[:2], []).append(code)
    last_names = table.drop_duplicates("code", keep="last").set_index("code")["name"].to_dict()
    divergent: dict[str, list] = {}
    if "uf" in municipal.columns:
        declared = text_values(municipal["uf"])
        prefix = table.code.str[:2].map(lambda value: STATES.get(value, ("",))[0])
        mask = declared.notna() & prefix.ne("") & declared.str.upper().ne(prefix)
        for period, group in table[mask].groupby("period"):
            divergent[str(period)] = sorted(set(group.code))
    excluded = frozenset((code, period) for period, items in divergent.items() for code in items) \
        if UF_DIVERGENTE_EXCLUI else frozenset()
    population: dict[str, dict] = {}
    if mapping.get("population") in municipal.columns:
        try:
            values = numbers(municipal[mapping["population"]], "população", {})
        except ValueError as exc:
            values = None
            error = str(exc)
        years = sorted({period[:4] for period in table.period.unique() if re.fullmatch(r"\d{6}", period)})
        for year in years:
            if values is None:
                population[year] = {"erro": error}
                continue
            june = table.assign(pop=values)[table.period == year + "06"]
            if excluded:
                june = june[[(code, year + "06") not in excluded for code in june.code]]
            population[year] = _june_population(year, june, expected, last_names, divergent.get(year + "06", []))
    return MunicipalIndex(version=(municipal.attrs.get("source") or {}).get("version"), codes=tuple(expected),
                          by_uf={key: tuple(value) for key, value in by_uf.items()}, names=last_names,
                          periods=tuple(sorted(set(table.period))),
                          categories=tuple(sorted(set(categories.dropna()))), divergent=divergent,
                          population=population, excluded=excluded)


def _june_population(year: str, june: pd.DataFrame, expected: list, names: dict, divergent: list) -> dict:
    """BR-POP-JUNHO-1 de um ano: soma da população de junho, cada município uma vez; nunca estimada."""
    base = {"ano": year, "competencia_populacao": year + "06", "previstos": len(expected), "divergentes": divergent}
    if june.empty:
        return {**base, "populacao": None, "incluidos": 0, "ausentes": [], "ausentes_detalhe": [],
                "avaliabilidade": "NAO_AVALIAVEL", "motivo": "SEM_COMPETENCIA_DE_JUNHO", "nota":
                "Brasil em " + year + ": densidade não avaliável; a fonte municipal não tem a competência de junho de " +
                year + ", e a população não é estimada."}
    if june["pop"].isna().any() or june["pop"].le(0).any():
        return {"erro": "População ausente ou não positiva em junho de " + year + " na fonte municipal; a população do "
                        "Brasil desse ano não é calculada."}
    if june.groupby("code")["pop"].nunique().gt(1).any():
        return {"erro": "Populações conflitantes no mesmo município em junho de " + year + "; a população do Brasil "
                        "desse ano não é calculada."}
    present = june.drop_duplicates("code")
    values = present["pop"]
    total = int(values.astype("int64").sum()) if values.mod(1).eq(0).all() else float(values.sum())
    missing = sorted(set(expected) - set(present.code))
    detail = [{"codigo": code, "nome": names.get(code, ""), "uf": STATES.get(code[:2], ("",))[0]} for code in missing]
    item = {**base, "populacao": total, "incluidos": int(len(present)), "ausentes": missing, "ausentes_detalhe": detail,
            "avaliabilidade": "AVALIAVEL_COM_LIMITACOES" if missing else "AVALIAVEL",
            "motivo": "POPULACAO_NACIONAL_PARCIAL" if missing else None, "nota": None}
    if missing:
        listed = "; ".join(", ".join(part for part in (d["nome"], d["uf"], d["codigo"]) if part) for d in detail[:10])
        listed += "; e mais " + str(len(detail) - 10) if len(detail) > 10 else ""
        item["nota"] = ("Em junho de " + year + ", a base municipal não tem registro de " + str(len(missing)) + " " +
                        _plural(len(missing), "município", "municípios") + " (" + listed + "); a população do Brasil "
                        "desse ano soma os " + thousands(len(present)) + " municípios com registro.")
    return item


def municipal_index(municipal: pd.DataFrame) -> MunicipalIndex:
    """Índice da fonte municipal oficial, calculado uma vez por versão (com trava, uma versão guardada)."""
    version = (municipal.attrs.get("source") or {}).get("version")
    key = (version, len(municipal), UF_DIVERGENTE_EXCLUI)
    if version:
        with _LOCK:
            if key in _CACHE:
                return _CACHE[key]
    index = _build_index(municipal)
    if version:
        with _LOCK:
            for stale in [item for item in _CACHE if item != key]:
                del _CACHE[stale]
            _CACHE[key] = index
    return index


def population_for(index: MunicipalIndex, period: str) -> dict:
    """População nacional (BR-POP-JUNHO-1) usada numa competência; erro quando o junho do ano é inconsistente."""
    period = str(period)
    if not re.fullmatch(r"\d{6}", period):
        return {"ano": None, "competencia_populacao": None, "populacao": None, "previstos": len(index.codes),
                "incluidos": 0, "ausentes": [], "ausentes_detalhe": [], "divergentes": [],
                "avaliabilidade": "NAO_AVALIAVEL", "motivo": "COMPETENCIA_SEM_ANO_E_MES",
                "nota": "Brasil em " + period + ": densidade não avaliável; a competência não está no formato AAAAMM."}
    year = period[:4]
    info = index.population.get(year)
    if info is None:
        info = _june_population(year, pd.DataFrame(columns=["code", "pop"]), list(index.codes), index.names, [])
    if "erro" in info:
        raise ValueError(info["erro"])
    return info


# --------------------------------------------------------------------------------------------- pedido
@dataclass(frozen=True)
class Abrangencia:
    brasil: bool
    estados: tuple
    mun_todos: bool
    mun_estados: tuple
    ids: tuple
    absorvidos: tuple = ()
    pedido: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def has_mun(self) -> bool:
        return self.mun_todos or bool(self.mun_estados) or bool(self.ids)

    @property
    def levels(self) -> list:
        return [level for level, present in ((BR, self.brasil), (UF, bool(self.estados)), (MUN, self.has_mun)) if present]


def _state_list(value, members: dict | None) -> tuple:
    if value is None:
        return ()
    if not isinstance(value, list) or len(value) > len(STATES):
        raise ValueError("Abrangência territorial inválida: estados devem ser uma lista de códigos de dois dígitos.")
    out = []
    for item in value:
        if not isinstance(item, str) or item not in STATES or (members is not None and not members.get(item)):
            raise ValueError("Estado não reconhecido nesta base: " + str(item)[:16] + ".")
        out.append(item)
    if len(set(out)) != len(out):
        raise ValueError(SELECTION_RULE)
    return tuple(sorted(out))


def parse(raw: Any, members: dict | None = None) -> Abrangencia:
    """Contrato options.abrangencia (Abr §6.1). Absorções explícitas, nunca silenciosas."""
    invalid = ("Abrangência territorial inválida: use {\"brasil\", \"estados\", \"municipios\": {\"todos\", \"estados\", "
               "\"ids\"}}.")
    if not isinstance(raw, dict) or set(raw) - {"brasil", "estados", "municipios"}:
        raise ValueError(invalid)
    brasil = raw.get("brasil", False)
    municipios = raw.get("municipios") or {}
    if not isinstance(brasil, bool) or not isinstance(municipios, dict) or set(municipios) - {"todos", "estados", "ids"}:
        raise ValueError(invalid)
    todos = municipios.get("todos", False)
    if not isinstance(todos, bool):
        raise ValueError(invalid)
    estados = _state_list(raw.get("estados"), members)
    groups = _state_list(municipios.get("estados"), members)
    ids = municipios.get("ids") or []
    if (not isinstance(ids, list) or len(ids) > MAX_IDS or
            any(not isinstance(item, str) or not item or len(item) > 512 for item in ids) or len(set(ids)) != len(ids)):
        raise ValueError(SELECTION_RULE)
    request = {"brasil": brasil, "estados": list(estados),
               "municipios": {"todos": todos, "estados": list(groups), "ids": sorted(ids)}}
    absorbed = []
    if todos:
        absorbed += ["mun:uf:" + item for item in groups] + sorted(ids)
        groups, ids = (), []
    else:
        inside = [item for item in ids if item.startswith("code:") and item[5:7] in groups]
        absorbed += sorted(inside)
        ids = [item for item in ids if item not in inside]
    result = Abrangencia(brasil, estados, todos, groups, tuple(sorted(ids)), tuple(absorbed), request)
    if not result.levels:
        raise ValueError("Nenhum território marcado na abrangência.")
    return result


def canonical_ids(a: Abrangencia) -> list[str]:
    return ((["br"] if a.brasil else []) + ["uf:" + item for item in a.estados] + (["mun:todos"] if a.mun_todos else []) +
            ["mun:uf:" + item for item in a.mun_estados] + list(a.ids))


def serialize(a: Abrangencia) -> dict:
    """Forma normalizada (listas ordenadas, absorções aplicadas) gravada em options.abrangencia e na chave."""
    return {"brasil": a.brasil, "estados": list(a.estados),
            "municipios": {"todos": a.mun_todos, "estados": list(a.mun_estados), "ids": list(a.ids)}}


def uses_density(operation: str, options: dict) -> bool:
    if operation in ("density", "ranking"):
        return True
    if operation == "comparisons":
        return options.get("comparison_indicator", "density") == "density"
    if operation in ("temporal", "report", "distribution"):
        return options.get(operation + "_indicator") == "density"
    return False


def _municipalities(a: Abrangencia, index: MunicipalIndex, operation: str) -> set:
    if a.mun_todos:
        return set(index.codes)
    codes = {item[5:] for item in a.ids if item.startswith("code:")} | {item for item in a.ids if not item.startswith("code:")}
    for prefix in a.mun_estados + (a.estados if operation == "aggregate" else ()):
        codes |= set(index.by_uf.get(prefix, ()))
    return codes


def plan(a: Abrangencia, operation: str, options: dict, index: MunicipalIndex) -> dict:
    """Regras da matriz (aceita, mínimo e mistura), conferidas no backend antes de qualquer cálculo."""
    rule = OPERATION_LEVELS.get(operation)
    if rule is None:
        raise ValueError("Análise não reconhecida.")
    label = ENGINE_OPERATION_LABELS.get(operation, operation)
    if not rule["disponivel"]:
        raise ValueError(ROTATION)
    if a.brasil and "brasil" not in rule["aceita"]:
        raise ValueError(rule["motivos"]["brasil"])
    if a.estados and "estado" not in rule["aceita"]:
        raise ValueError(rule["motivos"]["estado"])
    if rule["combinacao"] == "mesmo_nivel" and a.estados and a.has_mun:
        raise ChoiceRequired("Você marcou estados e municípios. " + label + " usa territórios do mesmo tipo: escolha qual "
                             "manter.")
    municipalities = _municipalities(a, index, operation)
    if operation == "aggregate":
        if len(municipalities) < 2:
            raise ChoiceRequired("A agregação precisa de pelo menos dois municípios.")
    elif rule["combinacao"] == "mesmo_nivel":
        if (len(a.estados) if a.estados else len(municipalities)) < rule["minimo"]:
            raise ChoiceRequired(label + " precisa de pelo menos dois territórios do mesmo tipo. Marque mais um.")
    elif rule["minimo"] > 1 and int(a.brasil) + len(a.estados) + len(municipalities) < rule["minimo"]:
        raise ChoiceRequired(label + " precisa de pelo menos dois territórios.")
    return rule


@dataclass
class Route:
    kind: str                   # "municipal", "nacional" ou "niveis"
    abrangencia: Abrangencia
    frame: pd.DataFrame
    mapping: dict
    options: dict               # opções do pedido para a rota (sem "abrangencia" na rota de níveis)
    selecao: dict


def resolve(sources, mapping: dict, operation: str, requested: dict, scope: str) -> Route:
    """Valida o pedido com abrangência e escolhe a rota (Abr §6.2): só municípios (ou estados na agregação) seguem o
    caminho municipal; só o Brasil sem densidade, o caminho nacional; o resto, os níveis."""
    if sources is None:
        raise ValueError(OFFICIAL_ONLY)
    if "territory_ids" in requested:
        raise ValueError("Use a abrangência territorial ou a lista de territórios, não as duas.")
    if scope == "national":
        raise ValueError("Com a abrangência territorial, o recorte é resolvido pela análise; envie scope=auto.")
    if not isinstance(mapping, dict):
        raise ValueError("Parâmetros de análise inválidos.")
    municipal = sources.frame("municipal")
    if municipal is None or source_identity(municipal) != "municipal":
        raise ValueError(OFFICIAL_ONLY)
    index = municipal_index(municipal)
    a = parse(requested.get("abrangencia"), index.by_uf)
    plan(a, operation, requested, index)
    base = {key: value for key, value in requested.items() if key != "abrangencia"}
    density = uses_density(operation, requested)
    needs_governed = bool(a.brasil or a.estados or a.mun_estados)
    if needs_governed:
        profile = curated_profile(municipal, mapping)
        roles = set((profile or {}).get("governed_roles") or [])
        required = {"territory", "territory_id", "period", "category", "count"} | ({"population"} if density else set())
        if not required <= roles:
            raise ValueError(GOVERNED_COLUMNS)
    selecao = {"pedido": a.pedido, "ids_canonicos": canonical_ids(a), "absorvidos": list(a.absorvidos)}
    only_municipal = not a.brasil and (not a.estados or operation == "aggregate")
    if only_municipal:
        options, coverage, absorbed = expand_municipal(a, index, municipal, mapping, base, operation)
        selecao.update(rota="municipal", expansoes=coverage)
        selecao["absorvidos"] = list(dict.fromkeys(selecao["absorvidos"] + absorbed))
        return Route("municipal", a, municipal, mapping, {**options, "abrangencia": serialize(a)}, selecao)
    if a.brasil and not a.estados and not a.has_mun and (
            operation == "counts" or (operation in ("temporal", "report") and not density)):
        national = sources.frame("national")
        if national is None or source_identity(national) != "national":
            raise ValueError(BR_UNAVAILABLE)
        selecao["rota"] = "nacional"
        return Route("nacional", a, national, dict(FIELDS["national"]), {**base, "abrangencia": serialize(a)}, selecao)
    selecao["rota"] = "niveis"
    return Route("niveis", a, municipal, mapping, base, selecao)


def _present_by_period(frame: pd.DataFrame, mapping: dict) -> dict:
    codes = text_values(frame[mapping["territory_id"]])
    periods = text_values(frame[mapping["period"]]) if mapping.get("period") else pd.Series("", index=frame.index)
    return {str(period): set(group) for period, group in codes.groupby(periods)}


def expand_municipal(a: Abrangencia, index: MunicipalIndex, municipal: pd.DataFrame, mapping: dict, options: dict,
                     operation: str):
    """Expansões ("Todos os municípios", grupos por estado e, na agregação, estados) nos municípios presentes depois
    dos filtros de período e categoria. Escolhas diretas continuam estritas (selected_frame/selection_coverage)."""
    if not mapping.get("territory_id"):
        raise ValueError(GOVERNED_COLUMNS)
    groups = list(a.mun_estados)
    absorbed = []
    ids = list(a.ids)
    if operation == "aggregate" and a.estados:
        absorbed += ["mun:uf:" + item for item in groups if item in a.estados]
        inside = [item for item in ids if item.startswith("code:") and item[5:7] in a.estados]
        absorbed += inside
        ids = [item for item in ids if item not in inside]
        groups = sorted(set(groups) | set(a.estados))
    filtered = scoped(municipal, mapping, options)
    present = _present_by_period(filtered, mapping)
    every = set().union(*present.values()) if present else set()
    coverage = []

    def describe(identifier, members, label):
        members = set(members)
        included = {period: len(members & codes) for period, codes in sorted(present.items())}
        missing = {period: sorted(members - codes) for period, codes in sorted(present.items()) if members - codes}
        coverage.append({"id": identifier, "rotulo": label, "previstos": len(members),
                         "incluidos_por_competencia": included, "ausentes_por_competencia": missing})

    if a.mun_todos:
        describe("mun:todos", index.codes, "Todos os municípios")
        return dict(options), coverage, absorbed
    expanded = []
    for prefix in groups:
        members = index.by_uf.get(prefix, ())
        is_state = operation == "aggregate" and prefix in a.estados
        describe(("uf:" if is_state else "mun:uf:") + prefix, members, uf_label(prefix) if is_state else group_label(prefix))
        expanded += [code for code in members if code in every]
    derived = list(ids) + ["code:" + code for code in sorted(set(expanded)) if "code:" + code not in ids]
    if not derived:
        raise ValueError("Não avaliável: nenhum município da seleção tem registro no recorte escolhido.")
    return {**options, "territory_ids": derived}, coverage, absorbed


def coverage_notes(selecao: dict, operation: str) -> list[str]:
    """Notas de cobertura das expansões (rota municipal)."""
    notes = []
    for item in selecao.get("expansoes") or []:
        missing = item["ausentes_por_competencia"]
        total = item["previstos"]
        if item["id"] == "mun:todos":
            included = list(item["incluidos_por_competencia"].values())
            if operation == "aggregate" and len(included) == 1:
                notes.append("Soma dos " + thousands(included[0]) + " municípios (possível dupla contagem); não é o total do "
                             "Brasil, que vem da contagem nacional.")
            if missing:
                for period, codes in missing.items():
                    notes.append("Todos os municípios em " + human_period(period) + ": " +
                                 thousands(item["incluidos_por_competencia"][period]) + " de " + thousands(total) +
                                 " municípios com registro; sem registro: " + _codes_text(codes) + ".")
            else:
                notes.append("Todos os municípios: os " + thousands(total) + " municípios previstos nesta versão da base "
                             "têm registro no recorte escolhido.")
            continue
        for period, codes in missing.items():
            included = item["incluidos_por_competencia"][period]
            if item["id"].startswith("uf:"):
                notes.append(item["rotulo"] + " em " + human_period(period) + ": soma parcial, " + str(included) + " de " +
                             str(total) + " municípios; sem registro: " + _codes_text(codes) +
                             ". O valor não representa o estado inteiro.")
            else:
                notes.append(item["rotulo"] + " em " + human_period(period) + ": " + str(included) + " de " + str(total) +
                             " municípios com registro; sem registro: " + _codes_text(codes) + ".")
    return notes


def route_limitations(selecao: dict, operation: str) -> list[str]:
    if operation == "aggregate" and any(item["id"].startswith("uf:") and item["ausentes_por_competencia"]
                                        for item in selecao.get("expansoes") or []):
        return ["AGREGADO_PARCIAL"]
    return []


# --------------------------------------------------------------------------------------------- partes
def _requested_periods(options: dict):
    if options.get("period_filters"):
        return list(options["period_filters"])
    if options.get("period_filter"):
        return [str(options["period_filter"]).strip()]
    return None


def _without_periods(options: dict) -> dict:
    return {key: value for key, value in options.items()
            if key not in ("period_filters", "period_filter", "territory_ids", "abrangencia")}


def _check_periods(periods):
    if periods is None:
        return
    if len(periods) > 80 or not all(isinstance(v, str) and 0 < len(v) <= 64 for v in periods) or \
            len(set(periods)) != len(periods):
        raise ValueError("Escolha uma lista de períodos distintos sem combinar com o filtro individual.")


@dataclass
class Parts:
    data: dict = field(default_factory=dict)          # nível → quadro (territory, period, category, quantity, ...)
    missing_periods: dict = field(default_factory=dict)  # nível → competências pedidas ausentes na fonte
    periods: dict = field(default_factory=dict)       # nível → competências usadas
    support: list = field(default_factory=list)       # suporte_agregado (UF × competência × categoria)
    population: list = field(default_factory=list)    # populacao_nacional (Brasil × competência)
    divergent: dict = field(default_factory=dict)     # competência → códigos com uf divergente usados
    mun_frame: pd.DataFrame | None = None             # recorte municipal preparado (para a geometria e o portão)
    mun_options: dict = field(default_factory=dict)
    catalog: dict = field(default_factory=dict)


EMPTY = ["territory", "period", "category", "quantity", "population", "density"]


def brazil_part(sources, options: dict, density: bool, index: MunicipalIndex, parts: Parts) -> pd.DataFrame:
    """Brasil: contagem nacional (nunca a soma dos municípios) e, na densidade, população BR-POP-JUNHO-1."""
    from analysis_premises import apply_premises  # importação tardia: o módulo de premissas usa o contrato de dados
    national = sources.frame("national")
    municipal = sources.frame("municipal")
    if national is None or source_identity(national) != "national" or source_identity(municipal) != "municipal":
        raise ValueError(BR_UNAVAILABLE)
    mapping = dict(FIELDS["national"])
    available = sorted(set(text_values(national[mapping["period"]]).dropna()))
    requested = _requested_periods(options)
    use = [period for period in requested if period in available] if requested is not None else available
    parts.missing_periods[BR] = [period for period in (requested or []) if period not in available]
    parts.periods[BR] = use
    if not use:
        return pd.DataFrame(columns=EMPTY)
    base = {key: options[key] for key in ("category_filter",) if options.get(key)}
    if requested is not None:
        base["period_filters"] = use
    settings = apply_premises(national, mapping, base, spatial=False)
    data = prepare(national, mapping, settings, "counts")[["territory", "period", "category", "quantity"]].copy()
    data["population"] = np.nan
    data["density"] = np.nan
    data["population_period"] = None
    data["condition"] = "Avaliável"
    data["coverage"] = None
    if density:
        populations, conditions, coverages, densities, sources_period = [], [], [], [], []
        for period, quantity in zip(data.period, data.quantity):
            info = population_for(index, period)
            parts.population.append({"competencia": str(period), **{key: info.get(key) for key in (
                "competencia_populacao", "populacao", "previstos", "incluidos", "ausentes", "avaliabilidade", "motivo",
                "nota")}})
            for code in info.get("divergentes") or []:
                parts.divergent.setdefault(info["competencia_populacao"], set()).add(code)
            value = info.get("populacao")
            populations.append(float(value) if value is not None else np.nan)
            sources_period.append(info.get("competencia_populacao"))
            if value is None:
                densities.append(np.nan)
                conditions.append("Não avaliável: a fonte municipal não tem a competência de junho de " + str(info["ano"]) +
                                  "; a população do Brasil não é estimada (" + info["motivo"] + ")"
                                  if info["motivo"] == "SEM_COMPETENCIA_DE_JUNHO" else
                                  "Não avaliável: competência fora do formato AAAAMM (" + info["motivo"] + ")")
                coverages.append(None)
                continue
            exact = Fraction(int(quantity)) * 1000 / Fraction(value) if float(quantity).is_integer() and \
                isinstance(value, int) else None
            densities.append(float(exact) if exact is not None else float(quantity) / float(value) * 1000)
            coverages.append("População: " + thousands(info["incluidos"]) + " de " + thousands(info["previstos"]) +
                             " municípios em " + human_period(info["competencia_populacao"]) +
                             ("; sem registro: " + _codes_text(info["ausentes"]) if info["ausentes"] else ""))
            conditions.append("Avaliável com limitações: população nacional parcial (POPULACAO_NACIONAL_PARCIAL)"
                              if info["avaliabilidade"] == "AVALIAVEL_COM_LIMITACOES" else "Avaliável")
        data["population"] = populations
        data["density"] = densities
        data["population_period"] = sources_period
        data["condition"] = conditions
        data["coverage"] = coverages
    return data.assign(level=BR, unit="br")


def municipal_part(sources, mapping: dict, options: dict, operation: str, a: Abrangencia, index: MunicipalIndex,
                   parts: Parts):
    """Uma única preparação para os municípios marcados e os membros dos estados marcados (mesmas linhas do caminho
    municipal, porque a preparação é local a cada território); depois, MUN e UF separados."""
    municipal = sources.frame("municipal")
    requested = _requested_periods(options)
    available = set(index.periods)
    use = [period for period in requested if period in available] if requested is not None else sorted(available)
    missing = [period for period in (requested or []) if period not in available]
    for level in (UF, MUN):
        parts.missing_periods[level] = missing
        parts.periods[level] = use
    direct = [item for item in a.ids]
    catalog = {item["id"]: item for item in territory_catalog(municipal, mapping, options)}
    parts.catalog = catalog
    unknown = [item for item in direct if item not in catalog]
    if unknown:
        raise ValueError("Municípios/territórios inexistentes ou incompatíveis com a base: " + ", ".join(unknown[:8]))
    ambiguous = [catalog[item]["label"] for item in direct if catalog[item]["selection_reason"]]
    if ambiguous:
        raise ValueError("Identificação territorial ambígua entre níveis superiores: " + ", ".join(ambiguous[:8]))
    wanted = None if a.mun_todos else (
        {catalog[item]["code"] for item in direct} | {code for prefix in a.mun_estados for code in index.by_uf.get(prefix, ())})
    states = set(a.estados)
    codes = text_values(municipal[mapping["territory_id"]])
    periods = text_values(municipal[mapping["period"]])
    mask = pd.Series(True, index=municipal.index)
    if wanted is not None:
        mask &= codes.isin(wanted) | codes.str[:2].isin(states)
    if requested is not None:
        mask &= periods.isin(use)
    if index.excluded:
        mask &= ~pd.Series([(code, period) in index.excluded for code, period in zip(codes, periods)], index=municipal.index)
    settings = _without_periods(options)
    frame = municipal if bool(mask.all()) else municipal.loc[mask]
    parts.mun_options = settings
    parts.mun_frame = frame
    if frame.empty or not use:
        data = pd.DataFrame(columns=EMPTY + ["code"])
    else:
        data = prepare(frame, mapping, settings, operation).copy()
        data["code"] = data.territory.str.extract(r"\[([^\[\]]+)\]$", expand=False)
    if a.has_mun:
        chosen = data if a.mun_todos else data[data.code.isin(wanted)]
        present = set(chosen.code)
        absent = [item for item in direct if catalog[item]["code"] not in present]
        if absent and use:
            raise ValueError("Não avaliável: seleção sem registros na categoria/período solicitado: " + ", ".join(sorted(absent)))
        rows = chosen.copy()
        rows["population_period"] = None
        rows["condition"] = "Avaliável"
        rows["coverage"] = None
        parts.data[MUN] = rows.assign(level=MUN, unit="code:" + rows.code)
        for period, items in index.divergent.items():
            used = present & set(items)
            if used and period in set(rows.period):
                parts.divergent.setdefault(period, set()).update(used)
    if a.estados:
        parts.data[UF] = uf_part(data, a, index, use, parts)
    return data


def uf_part(data: pd.DataFrame, a: Abrangencia, index: MunicipalIndex, periods: list, parts: Parts) -> pd.DataFrame:
    """Estados: Σ quantidade e Σ população dos membros presentes em cada competência (mesmo suporte do numerador)."""
    members = data[data.code.str[:2].isin(a.estados)].assign(uf=lambda d: d.code.str[:2])
    keys = ["uf", "period", "category"]
    sums = members.groupby(keys, sort=True)[["quantity", "population"]].sum(min_count=1)
    present = members.groupby(keys, sort=True)["code"].agg(lambda s: frozenset(s))
    categories = sorted(set(data.category)) or list(index.categories)
    out = []
    for prefix in a.estados:
        expected = set(index.by_uf.get(prefix, ()))
        for period in periods:
            for category in categories:
                key = (prefix, period, category)
                codes = present.get(key, frozenset())
                missing = sorted(expected - set(codes))
                quantity = sums["quantity"].get(key, np.nan) if key in sums.index else np.nan
                population = sums["population"].get(key, np.nan) if key in sums.index else np.nan
                coverage = (thousands(len(codes)) + " de " + thousands(len(expected)) + " municípios" +
                            ("; sem registro: " + _codes_text(missing) if missing else ""))
                if not codes:
                    condition = "Não avaliável: nenhum município do estado com registro nesta competência"
                elif missing:
                    condition = "Avaliável com limitações: soma parcial (AGREGADO_PARCIAL)"
                else:
                    condition = "Avaliável"
                parts.support.append({"estado": prefix, "rotulo": uf_label(prefix), "competencia": period,
                                      "categoria": category, "previstos": len(expected), "incluidos": len(codes),
                                      "ausentes": missing, "tipo": "SOMA_DOS_COMPONENTES", "fundamento": "CAP-AGR-01",
                                      "regra": METODOS["estado"]})
                for code in index.divergent.get(period, []):
                    if code in codes:
                        parts.divergent.setdefault(period, set()).add(code)
                density = quantity / population * 1000 if pd.notna(quantity) and pd.notna(population) and population > 0 \
                    else np.nan
                out.append({"territory": uf_label(prefix), "period": period, "category": category, "quantity": quantity,
                            "population": population, "density": density, "population_period": None,
                            "condition": condition, "coverage": coverage, "level": UF, "unit": "uf:" + prefix,
                            "uf": prefix, "members": codes, "expected": len(expected), "missing": missing})
    return pd.DataFrame(out, columns=EMPTY + ["population_period", "condition", "coverage", "level", "unit", "uf",
                                              "members", "expected", "missing"])


def build_parts(sources, mapping: dict, operation: str, options: dict, a: Abrangencia, index: MunicipalIndex) -> Parts:
    parts = Parts()
    _check_periods(_requested_periods(options))
    density = uses_density(operation, options)
    if a.brasil:
        parts.data[BR] = brazil_part(sources, options, density, index, parts)
    if a.has_mun or a.estados:
        municipal_part(sources, mapping, options, operation, a, index, parts)
    return parts


# --------------------------------------------------------------------------------------------- linhas
def _number(value):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return None
    if pd.isna(value):
        return None
    value = float(value)
    return int(value) if value.is_integer() else value


def _ordered(frame: pd.DataFrame, level: str) -> pd.DataFrame:
    if frame is None or frame.empty:
        return frame
    if level == UF:
        return frame.sort_values(["uf", "period", "category"], kind="stable")
    return frame


def _missing_rows(parts: Parts, a: Abrangencia, categories: list) -> list[dict]:
    """Competência pedida sem registro na fonte de um nível: linha não avaliável, nunca erro nem zero."""
    out = []
    objects = {BR: [("Brasil", "br")] if a.brasil else [],
               UF: [(uf_label(prefix), "uf:" + prefix) for prefix in a.estados],
               MUN: [(parts.catalog[item]["label"], item) for item in a.ids if item in parts.catalog]}
    source = {BR: "nacional", UF: "municipal", MUN: "municipal"}
    for level in ORDER:
        for period in parts.missing_periods.get(level) or []:
            for label, unit in objects[level]:
                for category in categories:
                    out.append({"level": level, "unit": unit, "territory": label, "period": period, "category": category,
                                "quantity": np.nan, "population": np.nan, "density": np.nan, "population_period": None,
                                "coverage": None, "condition": "Não avaliável: sem registro nesta competência na fonte " +
                                source[level]})
    return out


def _value_rows(parts: Parts, a: Abrangencia, density: bool, unit: str, categories: list) -> list[dict]:
    rows = []
    frames = [(level, _ordered(parts.data.get(level), level)) for level in ORDER if parts.data.get(level) is not None]
    missing = _missing_rows(parts, a, categories)
    for level, frame in frames:
        records = frame.to_dict("records") + [item for item in missing if item["level"] == level]
        for item in records:
            row = {"Nível": LEVEL_LABELS[level], "Território": item["territory"], "Período": item["period"],
                   "Categoria": item["category"], "Quantidade": _number(item["quantity"])}
            if density:
                row["População"] = _number(item["population"])
                row["Densidade por 1.000"] = None if pd.isna(item["density"]) else float(item["density"])
            row["Tipo de contagem"] = (COUNT_TYPES[level] if level != MUN else "Unidades distintas: " + unit)
            row["Cobertura"] = item.get("coverage")
            if density:
                row["Competência da população"] = item.get("population_period")
            row["Condição"] = item.get("condition") or "Avaliável"
            rows.append(row)
    return rows


def _harmonize(rows: list[dict], first=("Nível",)) -> list[dict]:
    columns = dict.fromkeys([*first, *(key for row in rows for key in row)])
    return [{key: row.get(key) for key in columns} for row in rows]


def _notes(parts: Parts, a: Abrangencia, operation: str, density: bool, levels_present: list) -> list[str]:
    notes = []
    if BR in levels_present and density:
        years = sorted({item["competencia_populacao"][:4] for item in parts.population if item.get("competencia_populacao")})
        # Municípios efetivamente somados (não os previstos): com um ano parcial na série (2015 na base atual), o
        # número varia entre os anos, e a nota não afirma um total que algum ano não tem.
        counts = sorted({item["incluidos"] for item in parts.population if item.get("populacao") is not None})
        if len(years) == 1:
            info = next(item for item in parts.population if (item.get("competencia_populacao") or "")[:4] == years[0])
            population = ("soma das populações estimadas dos " + thousands(info["incluidos"] or info["previstos"]) +
                          " municípios em junho de " + years[0] + ", usada também em janeiro de " + years[0])
        else:
            population = ("soma das populações estimadas dos " + (thousands(counts[0]) + " municípios" if len(counts) == 1
                                                                 else "municípios com registro") +
                          " em junho de cada ano, usada também em janeiro do mesmo ano")
        notes.append("Brasil (total nacional): contagem nacional de médicos da base Brasil, não a soma dos municípios. "
                     "População: " + population + " (regra BR-POP-JUNHO-1). Densidade = contagem ÷ população × 1.000.")
        for note in dict.fromkeys(item["nota"] for item in parts.population if item.get("nota")):
            notes.append(note)
        if len(levels_present) > 1 and any(not str(item["competencia"]).endswith("06") for item in parts.population):
            notes.append(NOTE_JANUARY)
    if UF in levels_present:
        notes.append(NOTE_STATES)
        if operation in ("ranking", "distribution"):
            notes.append(NOTE_STATES_ORDER)
        if operation != "temporal":
            for item in parts.support:
                if item["ausentes"] and item["incluidos"]:
                    notes.append(item["rotulo"] + " em " + human_period(item["competencia"]) + ": soma parcial, " +
                                 str(item["incluidos"]) + " de " + str(item["previstos"]) + " municípios; sem registro: " +
                                 _codes_text(item["ausentes"]) + ". O valor não representa o estado inteiro.")
    if len(levels_present) > 1:
        notes.append(NOTE_LEVELS)
    for period, codes in sorted(parts.divergent.items()):
        notes.append("Em " + human_period(period) + ", " + str(len(codes)) + " registro(s) da fonte municipal trazem na "
                     "coluna uf um estado diferente do indicado pelo código IBGE (" + _codes_text(sorted(codes)) +
                     "); o estado segue o código, e os valores entram como estão na fonte.")
    return list(dict.fromkeys(notes))


def _limitations(parts: Parts, levels_present: list, density: bool) -> list[str]:
    found = []
    if len(levels_present) > 1:
        found.append("NIVEIS_TERRITORIAIS_DIFERENTES")
    if BR in levels_present and density:
        found.append("DENOMINADOR_ALTERNATIVO")
        if any(item.get("motivo") == "POPULACAO_NACIONAL_PARCIAL" for item in parts.population):
            found.append("POPULACAO_NACIONAL_PARCIAL")
    if UF in levels_present:
        found.append("SOMA_COM_POSSIVEL_DUPLA_CONTAGEM")
        if any(item["ausentes"] for item in parts.support):
            found.append("AGREGADO_PARCIAL")
    return found


# --------------------------------------------------------------------------------------------- orquestrador
def _members(parts: Parts, a: Abrangencia, rows_units: set) -> list[dict]:
    members = []
    if a.brasil:
        members.append({"id": "br", "name": "Brasil", "code": "", "label": LEVEL_LABELS[BR], "parents": [],
                        "selection_reason": "", "state": "", "state_name": "", "nivel": BR})
    for prefix in a.estados:
        members.append({"id": "uf:" + prefix, "name": STATES[prefix][1], "code": prefix, "label": uf_label(prefix),
                        "parents": [], "selection_reason": "", "state": STATES[prefix][0], "state_name": STATES[prefix][1],
                        "nivel": UF})
    for unit in sorted(rows_units):
        item = parts.catalog.get(unit)
        if item:
            members.append({**item, "nivel": MUN})
    return members


def _panels(levels_present: list, density: bool, labels: dict) -> list[dict]:
    """Painéis da série por tipo de contagem: na quantidade, um por nível; na densidade, municípios (com o Brasil como
    referência tracejada) e estados (soma dos componentes) separados."""
    if density:
        panels = []
        if MUN in levels_present or BR in levels_present:
            names = [LEVEL_LABELS[level] for level in (MUN, BR) if level in levels_present]
            panels.append({"id": "U", "rotulo": "Densidade · " + (" e ".join(
                "Municípios" if name == LEVEL_LABELS[MUN] else name for name in names)),
                "niveis": [level for level in (MUN, BR) if level in levels_present],
                "tipo_contagem": "UNIDADES_DISTINTAS", "territorios": labels.get(MUN, []) + labels.get(BR, []),
                "referencia": "Brasil" if BR in levels_present and MUN in levels_present else None})
        if UF in levels_present:
            panels.append({"id": "S", "rotulo": "Densidade · Estados (soma dos municípios)", "niveis": [UF],
                           "tipo_contagem": "SOMA_DOS_COMPONENTES", "territorios": labels.get(UF, []), "referencia": None})
        return panels
    names = {BR: "Quantidade · Brasil (total nacional)", UF: "Quantidade · Estados (soma dos municípios)",
             MUN: "Quantidade · Municípios"}
    return [{"id": level, "rotulo": names[level], "niveis": [level],
             "tipo_contagem": "SOMA_DOS_COMPONENTES" if level == UF else "UNIDADES_DISTINTAS",
             "territorios": labels.get(level, []), "referencia": None} for level in levels_present]


def _support_of(parts: Parts):
    """(rótulo do estado, categoria) → {competência: membros presentes}."""
    out: dict = {}
    frame = parts.data.get(UF)
    if frame is None or frame.empty:
        return out
    for item in frame.to_dict("records"):
        if item["members"]:
            out.setdefault((item["territory"], item["category"]), {})[item["period"]] = item["members"]
    return out


LEVEL_PLURAL = {BR: "Brasil (total nacional)", UF: "Estados (soma dos municípios)", MUN: "Municípios"}


def _levels_phrase(levels_present: list) -> str:
    names = [{BR: "Brasil (total nacional)", UF: "estados (soma dos municípios)", MUN: "municípios"}[level]
             for level in levels_present]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " e " + names[-1]


def _level_metrics(rows: list[dict], column: str) -> list[dict]:
    """Registros avaliáveis e não avaliáveis de cada nível (o valor da coluna existe ou é lacuna); "nivel" indica o
    bloco. Os números de níveis diferentes nunca são somados."""
    out = []
    for level in ORDER:
        mine = [row for row in rows if row.get("Nível") == LEVEL_LABELS[level]]
        if not mine:
            continue
        valid = sum(row.get(column) is not None for row in mine)
        out.append({"label": LEVEL_PLURAL[level] + ": registros avaliáveis", "value": valid, "nivel": level})
        out.append({"label": LEVEL_PLURAL[level] + ": registros não avaliáveis", "value": len(mine) - valid, "nivel": level})
    return out


def _window_support(parts: Parts, positions: dict):
    """Estados cujo suporte (municípios presentes) muda na janela: tendência com INCOMPARABILIDADE, informada na
    entrada de evolution (nunca reescrita depois), e mudança não avaliada quando os extremos diferem."""
    ordered = sorted(positions, key=positions.get)
    incomparable, unchangeable, breaks_periods = {}, {}, {}
    for key, by_period in _support_of(parts).items():
        window = {period: members for period, members in by_period.items() if period in positions}
        if not window:
            continue
        union = frozenset().union(*window.values())
        varying = {period: sorted(union - members) for period, members in window.items() if members != union}
        if varying:
            incomparable[key] = "Membros efetivos diferentes entre competências (" + "; ".join(
                period + ": " + _codes_text(codes, 3) + " ausente" + ("s" if len(codes) > 1 else "")
                for period, codes in sorted(varying.items(), key=lambda item: positions[item[0]])) + ")"
            breaks_periods[key] = sorted(varying, key=positions.get)
        first, last = window.get(ordered[0]), window.get(ordered[-1])
        if first is not None and last is not None and first != last:
            unchangeable[key] = "municípios incluídos diferentes nos extremos"
    return incomparable, unchangeable, breaks_periods


def _support_notes(breaks_periods: dict, unchangeable: dict) -> list[str]:
    notes = []
    for key, periods in breaks_periods.items():
        both = key in unchangeable
        notes.append(("A mudança e a tendência de " if both else "A tendência de ") + key[0] + (
            " não foram avaliadas" if both else " não foi avaliada") + ": o número de municípios incluídos muda em " +
            ", ".join(human_period(period) for period in periods) + ". Escolha um intervalo sem essas competências "
            "para avaliá-" + ("las." if both else "la."))
    return notes


def _window_frame(parts: Parts, levels_present: list, density: bool) -> pd.DataFrame:
    """Valores de todos os níveis na janela, para evolution: observação ausente fica fora (nunca zero)."""
    frames = [parts.data[level][EMPTY].assign(level=level) for level in levels_present
              if parts.data[level] is not None and not parts.data[level].empty]
    if not frames:
        raise ValueError("Nenhum registro corresponde aos filtros selecionados.")
    data = pd.concat(frames, ignore_index=True)
    data = data[data.quantity.notna()]
    if density:
        data = data.assign(density=data.density.where(data.population.notna()))
    return data


def compute_levels(sources, route: Route, operation: str, options: dict) -> dict:
    """Resultado da rota de níveis: cada universo calculado separadamente pelo mesmo motor e apresentado em blocos."""
    import main as engine  # importação tardia: main usa este módulo
    from analysis_premises import apply_premises
    from temporal_change import evolution, evolution_notes
    a = route.abrangencia
    municipal = sources.frame("municipal")
    mapping = route.mapping
    index = municipal_index(municipal)
    density = uses_density(operation, options)
    if operation in ("temporal", "report") and options.get(operation + "_indicator") not in ("quantity", "density"):
        raise ChoiceRequired("Escolha o indicador desta análise: quantidade ou densidade por 1.000 habitantes.")
    if operation == "comparisons" and options.get("comparison_indicator", "density") not in ("quantity", "density"):
        raise ValueError("Indicador de comparação inválido: escolha quantidade ou densidade.")
    parts = build_parts(sources, mapping, operation, options, a, index)
    unit = count_unit_label(mapping, options)
    categories = sorted({str(c) for frame in parts.data.values() if frame is not None for c in frame.category}) or (
        [options["category_filter"]] if options.get("category_filter") else list(index.categories))
    levels_present = [level for level in ORDER if level in parts.data]
    metric = "density" if density else "quantity"
    breaks_periods: dict = {}
    if operation in ("counts", "density", "report"):
        rows = _value_rows(parts, a, density, unit, categories)
        # Métricas e descrição por nível (K12/K13): cada nível conta os próprios registros; nada é somado entre níveis.
        metrics = _level_metrics(rows, "Densidade por 1.000" if density else "Quantidade")
        blocks = " por nível territorial (" + _levels_phrase(levels_present) + "), em blocos separados; nenhum nível é " \
                 "somado a outro."
        if operation == "counts" or (operation == "report" and not density):
            result = engine._result("Quantitativos absolutos" if operation == "counts" else "Relatório de quantitativos",
                                    "Quantitativos de " + unit + blocks, rows, metrics,
                                    None if operation == "counts" else
                                    ["Indicador escolhido: quantidade. Nenhuma densidade foi calculada."])
        else:
            result = engine._result("Relatório analítico" if operation == "report" else "Densidade de profissionais",
                                    "Densidade de " + unit + " por 1.000 habitantes" + blocks, rows, metrics,
                                    ["Densidade = quantitativo / população × 1.000.",
                                     "Valores ausentes e denominadores nulos não são transformados em zero.",
                                     "Para exportar um relatório, utilize o recurso de impressão/PDF do navegador."])
    elif operation == "temporal":
        data = _window_frame(parts, levels_present, density)
        convention = resolve_convention(data.period.unique(), options.get("period_convention", "auto"))
        positions = period_positions(data.period.unique(), convention)
        if len(positions) < 2:
            raise ValueError("Evolução temporal exige pelo menos dois períodos no recorte.")
        incomparable, unchangeable, breaks_periods = _window_support(parts, positions)
        rows, detail_rows, tendencia, mudanca, breaks = evolution(
            data, metric, positions, convention=convention, incomparable=incomparable, change_incomparable=unchangeable,
            value_unit="por 1.000 habitantes" if density else unit)
        level_of = {(row["territory"]): row["level"] for row in data[["territory", "level"]].drop_duplicates().to_dict("records")}
        order = {label: (ORDER.index(level), label) for label, level in level_of.items()}
        uf_order = {uf_label(prefix): i for i, prefix in enumerate(a.estados)}
        rows.sort(key=lambda row: (order[row["Território"]][0], uf_order.get(row["Território"], 0)))
        for row in rows:
            level = level_of[row["Território"]]
            row["Tipo de contagem"] = COUNT_TYPES[level] if level != MUN else "Unidades distintas: " + unit
        rows = [{"Nível": LEVEL_LABELS[level_of[row["Território"]]], **row} for row in rows]
        detail_rows = [{"Nível": LEVEL_LABELS[level_of[row["Território"]]], **row} for row in detail_rows]
        for item in breaks:
            key = (item["territorio"], item["categoria"])
            item["nivel"] = level_of.get(item["territorio"])
            item["periodos"] = breaks_periods.get(key, [])
        notes = ["Cada competência é independente; não se somam pessoas de períodos diferentes.",
                 *evolution_notes(tendencia, mudanca, convention), *_support_notes(breaks_periods, unchangeable)]
        result = engine._result("Evolução temporal", "Variação de " + ("densidade por 1.000 habitantes" if density else
                                "quantitativos") + " entre períodos; tendência (CAP-TEN-01) somente com quatro ou mais "
                                "observações válidas.", rows, engine.temporal_metrics(rows, mudanca), notes=notes)
        result["detail_rows"] = detail_rows
        result["_tendencia"] = {"tendencia": tendencia, "mudanca": mudanca, "quebras": breaks}
    elif operation == "comparisons":
        result = _comparisons(engine, parts, a, municipal, mapping, options, metric, unit, categories)
    elif operation in ("ranking", "distribution"):
        result = _ordering(engine, parts, municipal, mapping, operation, options)
    else:
        raise ValueError("Análise não disponível na rota de níveis.")
    levels_notes = _notes(parts, a, operation, density, levels_present)
    result["notes"] = [*result["notes"], *levels_notes]
    labels = {level: list(dict.fromkeys(parts.data[level].territory)) for level in levels_present
              if parts.data[level] is not None}
    mun_units = set(parts.data[MUN].unit) if MUN in parts.data and parts.data[MUN] is not None else set()
    universe = {"kind": "selection", "members": _members(parts, a, mun_units),
                "classification_scope": "estados selecionados (soma dos municípios)" if operation in ("ranking", "distribution")
                else "universos separados por nível", "state_rule": METODOS["estado"]}
    periods = sorted({str(row["Período"]) for row in (result.get("detail_rows") or result["rows"]) if row.get("Período")} |
                     {period for level in levels_present for period in (parts.periods.get(level) or [])})
    source = {**(municipal.attrs.get("source") or {}), "scope": "niveis", "fontes_usadas":
              (["national"] if BR in levels_present else []) + (["municipal"] if {UF, MUN} & set(levels_present) else [])}
    levels_info = {"limitacoes": _limitations(parts, levels_present, density), "source": source,
                   "niveis": {"coluna": "Nível", "ordem": [LEVEL_LABELS[level] for level in levels_present],
                              "tipos": {LEVEL_LABELS[level]: COUNT_TYPES[level] for level in levels_present},
                              "mapa": LEVEL_LABELS[MUN]},
                   "paineis": _panels(levels_present, density, labels)}
    settings = {**options, "abrangencia": serialize(a)}
    finished = engine._finish(result, parts.mun_frame if parts.mun_frame is not None else municipal, mapping, operation,
                              settings, universe=universe, periods=periods, categories=categories, levels=levels_info)
    metadata = finished["metadata"]
    metadata["selecao_territorial"] = {**route.selecao, "expansoes": _expansions(parts, a, index)}
    if parts.support:
        metadata["suporte_agregado"] = parts.support
    if parts.population:
        metadata["populacao_nacional"] = parts.population
    methods = dict(metadata.get("metodos") or {})
    methods["niveis"] = METODOS["niveis"]
    if BR in levels_present and density:
        methods["populacao_nacional"] = METODOS["populacao_nacional"]
    if UF in levels_present:
        methods["estado"] = METODOS["estado"]
    metadata["metodos"] = methods
    if MUN in levels_present and operation in ("density", "report") and density:
        attach_reference(finished, sources, finished["metadata"]["periods"], categories)
    return finished


def _expansions(parts: Parts, a: Abrangencia, index: MunicipalIndex) -> list[dict]:
    frame = parts.data.get(MUN)
    if frame is None or frame.empty or not (a.mun_todos or a.mun_estados):
        return []
    present = {str(period): set(group) for period, group in frame.code.groupby(frame.period)}
    out = []
    targets = [("mun:todos", "Todos os municípios", index.codes)] if a.mun_todos else [
        ("mun:uf:" + prefix, group_label(prefix), index.by_uf.get(prefix, ())) for prefix in a.mun_estados]
    for identifier, label, members in targets:
        members = set(members)
        out.append({"id": identifier, "rotulo": label, "previstos": len(members),
                    "incluidos_por_competencia": {period: len(members & codes) for period, codes in sorted(present.items())},
                    "ausentes_por_competencia": {period: sorted(members - codes) for period, codes in sorted(present.items())
                                                 if members - codes}})
    return out


def _isolated_row(common: dict, label: str, metric_label: str, value, condition: str) -> dict:
    return {**common, "Território": label, metric_label: value, "Condição": condition}


SIDE_BY_SIDE = {
    BR: "Lado a lado: o Brasil é outro nível e não entra em maior, menor nem diferença com estados ou municípios.",
    UF: "Lado a lado: único estado; a soma dos municípios não é comparada com municípios nem com o Brasil.",
    MUN: "Lado a lado: único município; não é comparado com outros níveis.",
}


def _objects(parts: Parts, a: Abrangencia, level: str) -> list[str]:
    """Objetos pedidos de um nível (cardinalidade do pedido, AT-84)."""
    if level == BR:
        return ["Brasil"]
    if level == UF:
        return [uf_label(prefix) for prefix in a.estados]
    frame = parts.data.get(level)
    return list(dict.fromkeys(frame.territory)) if frame is not None else []


def _comparisons(engine, parts: Parts, a: Abrangencia, municipal, mapping, options, metric, unit, categories) -> dict:
    """Relações (maior, menor, igual e diferença) só dentro do mesmo nível; o Brasil e objetos isolados lado a lado."""
    period = comparison_window.requested_period(options)
    if period is not None:
        return _comparisons_window(engine, parts, a, mapping, options, metric, unit, categories, period)
    metric_label = "Densidade por 1.000" if metric == "density" else "Quantidade"
    out_rows, out_notes = [], []
    for level in ORDER:
        frame = parts.data.get(level)
        if frame is None:
            continue
        objects = list(dict.fromkeys(frame.territory))
        complete = frame
        partial = frame.iloc[0:0]
        if level == UF:
            complete = frame[frame.condition == "Avaliável"]
            partial = frame[frame.condition != "Avaliável"]
        if level == UF:
            objects = [uf_label(prefix) for prefix in a.estados]
        if level == MUN:
            objects = list(dict.fromkeys(frame.territory))
        related = level != BR and len(objects) >= 2 and \
            complete.groupby(["period", "category"]).territory.nunique().ge(2).any()
        if related:
            data = complete[EMPTY].reset_index(drop=True)
            computed = engine._compute(municipal, mapping, "comparisons", parts.mun_options, prepared=data)
            out_rows += [{"Nível": LEVEL_LABELS[level], **row} for row in computed["rows"]]
            out_notes += computed["notes"]
            singles = frame.iloc[0:0]
        else:
            singles = complete
        for item in singles.to_dict("records"):
            common = {"Período": item["period"], "Categoria": item["category"],
                      "Indicador": metric_label, "Unidade de contagem": unit}
            value = item[metric]
            condition = SIDE_BY_SIDE[level] if level == BR or len(objects) == 1 else \
                "Não avaliável: menos de dois territórios do mesmo nível avaliáveis nesta competência"
            if level == BR and item.get("condition", "Avaliável") != "Avaliável":
                condition = SIDE_BY_SIDE[BR] + " " + item["condition"] + "."
            out_rows.append({"Nível": LEVEL_LABELS[level], **_isolated_row(
                common, item["territory"], metric_label, None if pd.isna(value) else float(value), condition)})
        for item in partial.to_dict("records"):
            common = {"Período": item["period"], "Categoria": item["category"],
                      "Indicador": metric_label, "Unidade de contagem": unit}
            out_rows.append({"Nível": LEVEL_LABELS[level], **_isolated_row(
                common, item["territory"], metric_label, None,
                "Não avaliável: agregado parcial (" + item["coverage"] + ")" if item["members"] else item["condition"])})
    for item in _missing_rows(parts, a, categories):
        out_rows.append({"Nível": LEVEL_LABELS[item["level"]], "Período": item["period"], "Categoria": item["category"],
                         "Indicador": metric_label, "Unidade de contagem": unit, "Território": item["territory"],
                         metric_label: None, "Condição": item["condition"]})
    notes = list(dict.fromkeys(out_notes or [
        "Entre dois objetos: A e B em ordem de nome, relação A/B e diferença assinada A − B.",
        "Entre três ou mais: valores iguais e próximo valor estritamente maior descrevem a ordem do conjunto; sem "
        "diferenças automáticas entre pares."]))
    notes.append(NOTE_SAME_LEVEL)
    objects = sum(len(_objects(parts, a, level)) for level in ORDER if parts.data.get(level) is not None)
    return engine._result("Comparação territorial", "Valores e relações comparativas por período e categoria, sem "
                          "posições de ranking.", _harmonize(out_rows),
                          [{"label": "Territórios comparados", "value": objects}], notes=notes)


NOTE_SAME_LEVEL = "Relações só entre territórios do mesmo nível; Brasil, estados e municípios não são comparados entre si."


def _comparisons_window(engine, parts: Parts, a: Abrangencia, mapping, options, metric, unit, categories, period) -> dict:
    """Comparação com competência dos valores e janela (D6): relações só na competência dos valores e só dentro do mesmo
    nível; o Brasil lado a lado, sem relação; estado e município nunca relacionados. Um registro por objeto com valores,
    mudança e tendência na janela (a tendência do estado com suporte variável fica não comparável, pela entrada)."""
    density = metric == "density"
    metric_label = comparison_window.METRIC_LABELS[metric]
    levels_present = [level for level in ORDER if parts.data.get(level) is not None]
    requested = _requested_periods(options)
    available = sorted({str(p) for level in levels_present for p in parts.data[level].period})
    ordered, positions = comparison_window_periods(requested if requested is not None else available, mapping, options)
    convention = resolve_convention(list(positions), options.get("period_convention", "auto"))
    evolved, tendencia, mudanca, breaks, unchangeable, breaks_periods = {}, None, None, [], {}, {}
    if len(ordered) >= 2:
        data = _window_frame(parts, levels_present, density)
        data = data[data.period.isin(list(positions))]
        incomparable, unchangeable, breaks_periods = _window_support(parts, positions)
        evolved, tendencia, mudanca, breaks = comparison_window.evolve(
            data, metric, positions, convention, "por 1.000 habitantes" if density else unit, incomparable, unchangeable)
        levels_of = {row["territory"]: row["level"] for row in data[["territory", "level"]].drop_duplicates().to_dict("records")}
        for item in breaks:
            item["nivel"] = levels_of.get(item["territorio"])
            item["periodos"] = breaks_periods.get((item["territorio"], item["categoria"]), [])
    missing = [item for item in _missing_rows(parts, a, categories) if item["period"] == period]
    rows, detail, groups, unrelated, relation_notes = [], [], [], [], []
    for level in levels_present:
        frame = parts.data[level]
        values = frame[frame.period == period]
        objects = _objects(parts, a, level)
        complete, partial = values, values.iloc[0:0]
        if level == UF:
            complete, partial = values[values.condition == "Avaliável"], values[values.condition != "Avaliável"]
        related = level != BR and len(objects) >= 2 and not complete.empty and \
            complete.groupby(["period", "category"]).territory.nunique().ge(2).any()
        if related:
            computed = comparison_window.relation_rows(complete[EMPTY].reset_index(drop=True), metric, unit,
                                                       requested=len(objects))
            rows += [{"Nível": LEVEL_LABELS[level], **row} for row in computed]
            relation_notes.append(comparison_window.NOTE_PAIRS if len(objects) == 2 else comparison_window.NOTE_SET)
        for item in ([] if related else complete.to_dict("records")):
            condition = SIDE_BY_SIDE[level] if level == BR or len(objects) == 1 else \
                "Não avaliável: menos de dois territórios do mesmo nível avaliáveis nesta competência"
            if level == BR and item.get("condition", "Avaliável") != "Avaliável":
                condition = SIDE_BY_SIDE[BR] + " " + item["condition"] + "."
            value = item[metric]
            rows.append({"Nível": LEVEL_LABELS[level], **_isolated_row(
                {"Período": item["period"], "Categoria": item["category"], "Indicador": metric_label,
                 "Unidade de contagem": unit}, item["territory"], metric_label, None if pd.isna(value) else float(value),
                condition)})
            unrelated.append({"objeto": item["territory"], "nivel": level, "motivo": condition})
        for item in partial.to_dict("records"):
            condition = "Não avaliável: agregado parcial (" + item["coverage"] + ")" if item["members"] else item["condition"]
            rows.append({"Nível": LEVEL_LABELS[level], **_isolated_row(
                {"Período": item["period"], "Categoria": item["category"], "Indicador": metric_label,
                 "Unidade de contagem": unit}, item["territory"], metric_label, None, condition)})
            unrelated.append({"objeto": item["territory"], "nivel": level, "motivo": condition})
        groups.append({"nivel": level, "rotulo": LEVEL_LABELS[level],
                       "tipo_contagem": COUNT_TYPES[level] if level != MUN else "Unidades distintas: " + unit,
                       "objetos": objects, "relacoes": bool(related)})
        records = {(item["territory"], item["category"]): item for item in values.to_dict("records")}
        gaps = {(item["territory"], item["category"]): item for item in missing if item["level"] == level}
        keys = list(dict.fromkeys([*zip(frame.territory, frame.category), *gaps]))
        if level == MUN and "code" in frame:  # ordem padrão pelo código territorial (RQ-REP-03)
            codes = dict(zip(frame.territory, frame.code))
            keys.sort(key=lambda key: (str(codes.get(key[0], "")), str(key[1])))
        for key in keys:
            record = records.get(key)
            row = {"Nível": LEVEL_LABELS[level], "Território": key[0], "Categoria": key[1], "Período": period,
                   **comparison_window.value_columns(record, metric, density),
                   "Tipo de contagem": COUNT_TYPES[level] if level != MUN else "Unidades distintas: " + unit,
                   "Cobertura": (record or {}).get("coverage")}
            if density and level == BR:
                row["Competência da população"] = (record or {}).get("population_period")
            row["Condição"] = (record.get("condition") or "Avaliável") if record is not None else \
                gaps[key]["condition"] if key in gaps else comparison_window.MISSING_VALUES
            if record is None and key not in gaps:
                unrelated.append({"objeto": key[0], "nivel": level, "motivo": comparison_window.MISSING_VALUES})
            if len(ordered) >= 2:
                row.update(comparison_window.window_columns(evolved.get(key)))
            detail.append(row)
    for item in missing:
        rows.append({"Nível": LEVEL_LABELS[item["level"]], "Período": item["period"], "Categoria": item["category"],
                     "Indicador": metric_label, "Unidade de contagem": unit, "Território": item["territory"],
                     metric_label: None, "Condição": item["condition"]})
        unrelated.append({"objeto": item["territory"], "nivel": item["level"], "motivo": item["condition"]})
    comparacao = comparison_window.window_meta(period, ordered, metric)
    comparacao.update(grupos=groups, sem_relacao=unrelated)
    notes = [*comparison_window.notes(period, ordered, tendencia, mudanca, convention,
                                      list(dict.fromkeys(relation_notes))),
             *_support_notes(breaks_periods, unchangeable), NOTE_SAME_LEVEL]
    objects = sum(len(group["objetos"]) for group in groups)
    result = engine._result("Comparação territorial", "Valores e relações comparativas na competência " + str(period) +
                            (", com mudança e tendência de cada território na janela" if len(ordered) >= 2 else "") +
                            "; relações só dentro do mesmo nível, sem posições de ranking.", _harmonize(rows),
                            [{"label": "Territórios comparados", "value": objects},
                             {"label": "Competências na janela", "value": len(ordered)}], notes=notes)
    result["detail_rows"] = _harmonize(detail)
    result["_comparacao"] = comparacao
    if tendencia is not None:
        result["_tendencia"] = {"tendencia": tendencia, "mudanca": mudanca, "quebras": breaks}
    return result


def _ordering(engine, parts: Parts, municipal, mapping, operation, options) -> dict:
    """Ranking e distribuição de estados: universo próprio; estado parcial fora da ordem e listado à parte (AT-18)."""
    frame = parts.data.get(UF)
    if frame is None or frame.empty:
        raise ValueError("Nenhum registro corresponde aos filtros selecionados.")
    complete = frame[frame.condition == "Avaliável"]
    partial = frame[frame.condition != "Avaliável"]
    counts = complete.groupby(["period", "category"]).territory.nunique()
    if counts.empty or not counts.ge(2).any():
        periods = sorted(set(frame.period))
        listed = ", ".join(sorted(set(partial.territory))) or "nenhum estado parcial"
        raise ValueError("Menos de dois estados avaliáveis em " + ", ".join(human_period(p) for p in periods) +
                         ": " + listed + ".")
    data = complete[EMPTY].reset_index(drop=True)
    computed = engine._compute(municipal, mapping, operation, parts.mun_options, prepared=data)
    tipo = COUNT_TYPES[UF]
    if operation == "ranking":
        rows = [{"Nível": LEVEL_LABELS[UF], **row, "Tipo de contagem": tipo} for row in computed["rows"]]
        for item in partial.to_dict("records"):
            rows.append({"Nível": LEVEL_LABELS[UF], "Posição": None, "Território": item["territory"],
                         "Período": item["period"], "Categoria": item["category"], "Densidade por 1.000": None,
                         "Condição": "Não avaliável: agregado parcial (" + item["coverage"] + ")" if item["members"]
                         else item["condition"], "Tipo de contagem": tipo})
        computed["rows"] = _harmonize(rows)
        computed["metrics"] = engine.ranking_metrics(computed["rows"])  # estados parciais contam como não avaliáveis
    else:
        computed["detail_rows"] = [{"Nível": LEVEL_LABELS[UF], **row, "Tipo de contagem": tipo}
                                   for row in computed["detail_rows"]]
        computed["metrics"].append({"label": "Estados fora da distribuição", "value": len(partial)})
        for item in partial.to_dict("records"):
            computed["notes"].append("Fora da distribuição: " + item["territory"] + " em " + human_period(item["period"]) +
                                     " (" + ("agregado parcial, " + item["coverage"] if item["members"] else
                                             item["condition"]) + ").")
    return computed


# --------------------------------------------------------------------------------------------- taxa nacional (D5)
def national_reference(sources, periods: list, categories: list) -> dict:
    """Taxa nacional de contexto (D5) para as competências e categorias do resultado; nunca derruba a análise."""
    try:
        municipal = sources.frame("municipal")
        national = sources.frame("national")
        if national is None or municipal is None or source_identity(national) != "national" or \
                source_identity(municipal) != "municipal":
            raise ValueError(BR_UNAVAILABLE)
        index = municipal_index(municipal)
        from analysis_premises import apply_premises
        mapping = dict(FIELDS["national"])
        settings = apply_premises(national, mapping, {}, spatial=False)
        data = prepare(national, mapping, settings, "counts")
        counts = {(str(p), str(c)): q for p, c, q in zip(data.period, data.category, data.quantity)}

        def entry(period, category):
            quantity = counts.get((str(period), str(category)))
            item = {"competencia": str(period), "categoria": category, "numerador": _number(quantity),
                    "denominador": None, "competencia_populacao": None, "valor": None,
                    "avaliabilidade": "NAO_AVALIAVEL", "motivo": None, "ausentes": []}
            if quantity is None:
                item["motivo"] = "SEM_REGISTRO_NA_FONTE_NACIONAL"
                return item
            info = population_for(index, period)
            item.update(denominador=info.get("populacao"), competencia_populacao=info.get("competencia_populacao"),
                        avaliabilidade=info["avaliabilidade"], motivo=info.get("motivo"),
                        ausentes=list(info.get("ausentes") or []))
            if info.get("nota") and info["avaliabilidade"] != "AVALIAVEL":
                item["nota"] = info["nota"]
            if info.get("populacao"):
                value = info["populacao"]
                item["valor"] = float(Fraction(int(quantity)) * 1000 / Fraction(value)) if \
                    float(quantity).is_integer() and isinstance(value, int) else float(quantity) / float(value) * 1000
            return item

        values = [entry(period, category) for period in periods for category in categories]
        # Série nacional de todas as competências da fonte nacional (cartão de contexto com minigráfico): os mesmos
        # valores por competência, sem ligar competências não avaliáveis (lacuna) e sem entrar em nenhum cálculo.
        def safe(period, category):
            try:
                return entry(period, category)
            except ValueError:  # um ano inconsistente fora do resultado não derruba a referência das competências pedidas
                return {"competencia": str(period), "categoria": category, "valor": None,
                        "avaliabilidade": "NAO_AVALIAVEL", "motivo": "POPULACAO_NACIONAL_INCONSISTENTE"}

        national_periods = sorted({str(p) for p in data.period})
        serie = [{key: item.get(key) for key in ("competencia", "categoria", "valor", "avaliabilidade", "motivo",
                                                  "competencia_populacao")}
                 for item in (safe(period, category) for period in national_periods for category in categories)]
        return {"rotulo": LEVEL_LABELS[BR], "papel": "REFERENCIA_DE_CONTEXTO", "unidade": "por 1.000 habitantes",
                "regra_populacao": METODOS["populacao_nacional"], "tipo_contagem": "UNIDADES_DISTINTAS",
                "fontes": {"numerador": "Dados_Brasil.xlsx · contagem",
                           "denominador": "Dados_Municipios_Brasil.csv · população_estimada (junho)"},
                "versao_base": index.version, "limitacoes": ["NIVEIS_TERRITORIAIS_DIFERENTES", "DENOMINADOR_ALTERNATIVO"],
                "valores": values, "serie": serie, "nota": NOTE_REFERENCE}
    except Exception as exc:  # noqa: BLE001 — a referência de contexto nunca invalida a análise
        import logging
        logging.getLogger(__name__).warning("Taxa nacional de referência indisponível: %s", exc)
        return {"estado": "INDISPONIVEL", "motivo": str(exc) or "Falha ao calcular a taxa nacional de referência."}


def reference_drawing(reference: dict) -> list[dict]:
    """O que o frontend desenha (legenda, barras): só os valores já calculados no backend."""
    if not reference or reference.get("estado") == "INDISPONIVEL":
        return []
    return [{"rotulo": reference["rotulo"], "papel": reference["papel"], "unidade": reference["unidade"],
             "nota": reference["nota"], "valores": [{key: item.get(key) for key in (
                 "competencia", "categoria", "valor", "avaliabilidade", "competencia_populacao")}
                 for item in reference["valores"]], "serie": list(reference.get("serie") or [])}]


def attach_reference(result: dict, sources, periods: list, categories: list) -> dict:
    """D5: metadata.referencia_nacional e representacao.referencias; metodos.populacao_nacional quando calculada."""
    reference = national_reference(sources, periods, categories)
    metadata = result["metadata"]
    metadata["referencia_nacional"] = reference
    representation = metadata.get("representacao")
    if isinstance(representation, dict):
        representation["referencias"] = reference_drawing(reference)
    if reference.get("estado") != "INDISPONIVEL":
        metadata["metodos"] = {**(metadata.get("metodos") or {}), "populacao_nacional": METODOS["populacao_nacional"]}
    return reference


def wants_reference(operation: str, options: dict, frame) -> bool:
    """Densidade e relatório com densidade de um resultado com municípios da base oficial."""
    if not (operation == "density" or (operation == "report" and options.get("report_indicator") == "density")):
        return False
    return source_identity(frame) == "municipal"


# --------------------------------------------------------------------------------------------- inspeção e pré-exame
def inspect_block(sources, mapping: dict) -> dict | None:
    """Bloco "niveis" do /api/inspect da base oficial: estados, Brasil e regras por análise (Abr §6.4)."""
    municipal = sources.frame("municipal")
    national = sources.frame("national")
    if municipal is None or source_identity(municipal) != "municipal":
        return None
    index = municipal_index(municipal)
    brasil = {"disponivel": national is not None and source_identity(national) == "national", "motivo": "",
              "periodos": [], "densidade_nao_avaliavel": [], "densidade_com_limitacoes": []}
    if not brasil["disponivel"]:
        brasil["motivo"] = BR_UNAVAILABLE
    else:
        nm = FIELDS["national"]
        brasil["periodos"] = sorted(set(text_values(national[nm["period"]]).dropna()))
        for period in brasil["periodos"]:
            try:
                info = population_for(index, period)
            except ValueError as exc:
                brasil["densidade_nao_avaliavel"].append({"competencia": period, "motivo": "ERRO", "texto": str(exc)})
                continue
            item = {"competencia": period, "motivo": info.get("motivo"), "ausentes": info.get("ausentes") or [],
                    "texto": info.get("nota")}
            if info["avaliabilidade"] == "NAO_AVALIAVEL":
                brasil["densidade_nao_avaliavel"].append(item)
            elif info["avaliabilidade"] == "AVALIAVEL_COM_LIMITACOES":
                brasil["densidade_com_limitacoes"].append(item)
    states = [{"prefixo": prefix, "sigla": STATES[prefix][0], "nome": STATES[prefix][1],
               "rotulo": uf_label(prefix), "rotulo_grupo": group_label(prefix), "municipios": len(codes)}
              for prefix, codes in sorted(index.by_uf.items())]
    operations = {}
    for operation, rule in OPERATION_LEVELS.items():
        item = {key: (list(value) if isinstance(value, list) else dict(value) if isinstance(value, dict) else value)
                for key, value in rule.items()}
        if not brasil["disponivel"] and "brasil" in item["aceita"]:
            item["aceita"] = [level for level in item["aceita"] if level != "brasil"]
            item["motivos"]["brasil"] = BR_UNAVAILABLE
        if not states and "estado" in item["aceita"]:
            item["aceita"] = [level for level in item["aceita"] if level != "estado"]
            item["motivos"]["estado"] = "Nenhum estado identificado pelos códigos desta base."
        operations[operation] = item
    return {"regra_estado": METODOS["estado"], "regra_populacao_nacional": METODOS["populacao_nacional"],
            "brasil": brasil, "estados": states, "municipios": {"total": len(index.codes)}, "operacoes": operations}


_RANK = {"available": 0, "needs_confirmation": 1, "unavailable": 2}


def level_preflight(base: dict, sources, mapping: dict, options: dict, a: Abrangencia, index: MunicipalIndex) -> dict:
    """Pré-exame com abrangência na rota de níveis: o esquema atual (da fonte municipal) mais
    capabilities[op].niveis = {brasil, estados, municipios}; o estado é o pior das partes aplicáveis."""
    from analysis_premises import apply_premises
    from semantic_bridge import preflight
    national = sources.frame("national")
    national_caps = None
    if a.brasil:
        if national is not None and source_identity(national) == "national":
            nm = dict(FIELDS["national"])
            national_caps = preflight(national, nm, apply_premises(national, nm, {
                key: options[key] for key in ("category_filter",) if options.get(key)}, spatial=False))["capabilities"]
    original = {operation: {"status": item["status"], "reasons": list(item["reasons"])}
                for operation, item in base["capabilities"].items()}
    for operation, capability in base["capabilities"].items():
        rule = OPERATION_LEVELS.get(operation)
        if rule is None:
            continue
        municipal_capability = original.get(gate_operation(operation, options), original[operation])
        levels = {}
        if a.brasil:
            if "brasil" not in rule["aceita"]:
                levels["brasil"] = {"status": "unavailable", "reasons": [rule["motivos"].get("brasil", ROTATION)]}
            elif national_caps is None:
                levels["brasil"] = {"status": "unavailable", "reasons": [BR_UNAVAILABLE]}
            else:
                item = national_caps["counts"]
                reasons = list(item["reasons"])
                status = item["status"]
                if uses_density(operation, options):
                    usable = []
                    for period in (_requested_periods(options) or index.periods):
                        try:
                            usable.append(population_for(index, period)["populacao"] is not None)
                        except ValueError as exc:
                            reasons.append(str(exc))
                    if not any(usable):
                        status = "unavailable"
                        reasons.append("População nacional (BR-POP-JUNHO-1) indisponível nas competências escolhidas.")
                levels["brasil"] = {"status": status, "reasons": reasons}
        if a.estados:
            levels["estados"] = ({"status": "unavailable", "reasons": [rule["motivos"].get("estado", ROTATION)]}
                                 if "estado" not in rule["aceita"] else dict(municipal_capability))
        if a.has_mun:
            levels["municipios"] = ({"status": "unavailable", "reasons": [ROTATION]} if not rule["disponivel"] else
                                    dict(original[operation]))
        reasons = []
        try:
            plan(a, operation, options, index)
        except ChoiceRequired as exc:  # mistura de níveis ou mínimo: escolha pendente na abrangência
            levels["selecao"] = {"status": "needs_confirmation", "reasons": [str(exc)]}
        except ValueError as exc:  # nível fora da análise: o motivo já está na parte correspondente
            if not any(str(exc) in item["reasons"] for item in levels.values()):
                levels["selecao"] = {"status": "unavailable", "reasons": [str(exc)]}
        prefixes = {"brasil": "Brasil: ", "estados": "Estados: ", "municipios": "Municípios: ", "selecao": ""}
        worst = "available"
        for key, item in levels.items():
            if _RANK[item["status"]] > _RANK[worst]:
                worst = item["status"]
            reasons += [prefixes[key] + reason for reason in item["reasons"]]
        capability["status"] = worst
        capability["reasons"] = list(dict.fromkeys(reasons))
        capability["niveis"] = levels
    base["abrangencia"] = serialize(a)
    return base


def pending_preflight(sources, mapping: dict, operation: str, options: dict, message: str) -> dict:
    """Pré-exame com uma escolha pendente na abrangência (mistura de níveis ou mínimo de territórios): o esquema da fonte
    municipal inteira, com a análise pedida em "escolha pendente" e o motivo, em vez de recusar o pré-exame. O cálculo
    continua recusado em /api/analyze (plan), com o mesmo texto."""
    from analysis_premises import apply_premises
    from semantic_bridge import preflight
    municipal = sources.frame("municipal")
    settings = {key: value for key, value in options.items() if key not in ("abrangencia", "territory_ids")}
    base = preflight(municipal, mapping, apply_premises(municipal, mapping, settings))
    capability = base["capabilities"].get(operation)
    if capability is not None:
        capability["status"] = "needs_confirmation"
        capability["reasons"] = [message]
        capability["niveis"] = {"selecao": {"status": "needs_confirmation", "reasons": [message]}}
    base["abrangencia_pendente"] = message
    return base


def gate_operation(operation: str, options: dict) -> str:
    """Capacidade municipal que habilita uma parte da rota de níveis. Na comparação, a matriz municipal exigiria dois
    municípios; com níveis lado a lado, vale a capacidade do próprio indicador (relações conferidas no cálculo)."""
    if operation == "comparisons":
        return "density" if uses_density(operation, options) else "counts"
    return operation


def gate(sources, route: Route, operation: str, settings: dict, index: MunicipalIndex) -> dict:
    """Portão da rota de níveis em /api/analyze: o pré-exame das partes envolvidas, sobre o recorte dos membros."""
    from analysis_premises import apply_premises
    from semantic_bridge import preflight
    a = route.abrangencia
    eligibility = None
    reasons, status = [], "available"
    if a.has_mun or a.estados:
        municipal = sources.frame("municipal")
        requested = _requested_periods(settings)
        part = _without_periods(settings)
        usable = sorted(index.periods) if requested is None else [p for p in requested if p in set(index.periods)]
        if requested is not None and usable:
            part["period_filters"] = usable
        frame = municipal
        if not a.mun_todos:
            codes = text_values(municipal[route.mapping["territory_id"]])
            wanted = {item[5:] for item in a.ids if item.startswith("code:")} | \
                {code for prefix in a.mun_estados + a.estados for code in index.by_uf.get(prefix, ())}
            frame = municipal.loc[codes.isin(wanted)]
        if usable and not frame.empty:
            eligibility = preflight(frame, route.mapping, part)
            capability = eligibility["capabilities"].get(gate_operation(operation, settings))
            if capability is None:
                raise ValueError("Análise desconhecida.")
            status, reasons = capability["status"], ["Municípios e estados: " + r for r in capability["reasons"]]
    if a.brasil:
        national = sources.frame("national")
        if national is None or source_identity(national) != "national":
            raise ValueError(BR_UNAVAILABLE)
        nm = dict(FIELDS["national"])
        national_caps = preflight(national, nm, apply_premises(national, nm, {
            key: settings[key] for key in ("category_filter",) if settings.get(key)}, spatial=False))["capabilities"]
        item = national_caps["counts"]
        if _RANK[item["status"]] > _RANK[status]:
            status = item["status"]
        reasons += ["Brasil: " + reason for reason in item["reasons"]]
        if eligibility is None:
            eligibility = {"capabilities": {op: {"status": value["status"]} for op, value in national_caps.items()}}
    if status != "available":
        raise ValueError("Análise não habilitada para a configuração atual: " + " ".join(reasons))
    return eligibility or {"capabilities": {operation: {"status": "available"}}}
