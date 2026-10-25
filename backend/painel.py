"""Painel integrado de bolhas: os números que a tela posiciona, filtra e desenha (Adendo BOL-20261021 da SPEC, contrato do
painel de 21/10/2026 e contrato da página única de análise de 22/10/2026; ver Docs/PAINEL_INTEGRADO.md).

Rotas POST /api/painel, POST /api/painel/referencias e POST /api/painel/mapa (main.py; o mapa lê as coordenadas
autorizadas da análise espacial, sem cálculo novo). O pedido de /api/painel tem dois formatos:
- sem `nivel` (contrato de 21/10/2026): só a base Brasil oficial (fonte municipal), com as chaves e a resposta de então;
- com `nivel` (página única, 22/10/2026): a base Brasil (municípios ou estados) ou uma planilha enviada, com tendência,
  grupos por posição, faixas, condições, ordenação, comparação, rotatividade, disponibilidade por análise, linha de
  contexto do Brasil e o registro do resultado na sessão.

Nada aqui é fórmula nova; cada número vem do motor das análises:
- quantidade, população e densidade de cada município (ou unidade da planilha): data_contract.prepare, a mesma preparação
  da análise de densidade (CAP-IND-01 e CAP-IND-02; densidade = quantidade ÷ população × 1.000, em precisão integral);
- estados: territorial_levels.state_part, a contagem estadual de médicos únicos (UF-CONTAGEM-ESTADUAL-1) e a população do
  estado, soma dos seus municípios na própria competência (UF-POP-MUNICIPIOS-1), como na abrangência por estados;
- conjunto: main._compute(..., "aggregate"), a agregação municipal (CAP-AGR-01), soma dos componentes com possível
  dupla contagem (SOMA_DOS_COMPONENTES) e agregado parcial sobre os membros com registro (AGREGADO_PARCIAL);
- distância e membro mais próximo: nearest_reference.territory_coordinates e nearest_exact (CAP-ESP-01 e CAP-ESP-02),
  geodésica no elipsoide do referencial confirmado (GRS80 no SIRGAS 2000; WGS 84 no WGS 84) até a referência ou até o
  membro mais próximo do conjunto de referência, pelo mínimo do conjunto completo, com os empates exatos (uma referência
  sem coordenada válida deixa a distância não avaliável), com a camada complementar de coordenadas como na análise
  espacial;
- variação percentual: a de temporal_change.change (CAP-TMP-01, DA-14), em aritmética exata com inteiros (_percent);
  base zero não é avaliável;
- tendência: trend.classify_frame e trend.summarize (CAP-TEN-01, DA-15), as funções da evolução temporal;
- grupos por posição: main._compute(..., "distribution") e main.distribution_cuts (CAP-DIS-02, Hyndman–Fan tipo 7),
  também os grupos que pintam o mapa (`grupos_mapa`, 23/10/2026: o mesmo cálculo, pedido junto com a análise);
- faixas do usuário e faixas de distância: combined_criteria.band_edges e bands_of (CAP-DIS-03 e CAP-ESP-03);
- condições: combined_criteria.parse_tree e evaluate (CAP-SUB-01, três estados, combinação E);
- ordenação e N primeiros: combined_criteria.ranking_of e select_top (CAP-SUB-02 e CAP-SUB-03), empates na mesma posição;
- comparação de 2 ou 3 itens: main._compute(..., "comparisons") (CAP-CMP-01);
- rotatividade: main._compute(..., "rotation") (CAP-ROT-01), só com identificador individual;
- linha de contexto do Brasil: territorial_levels.national_reference (decisão D5), sem classificar nada;
- frase-resumo (resumo_painel.py): as contagens de itens e as unidades de menor e de maior valor que ela copia
  (summary_facts).

Não avaliáveis seguem com o motivo, nunca como zero (RQ-CAP-04, RQ-REP-04). A régua da tela é filtro visual sobre os
valores devolvidos (RQ-REP-06). Na base Brasil verificada, o que não muda entre pedidos é reaproveitado pela memória da
versão (_reaproveitar). Nada deste módulo vai ao provedor de IA.
"""
from __future__ import annotations

import contextvars
import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime, timezone
from fractions import Fraction

import numpy as np
import pandas as pd

from analysis_premises import apply_premises, limitations as premise_limitations, premise_notes
from brazil_catalog_profile import FIELDS, curated_profile, source_identity
from combined_criteria import band_edges, bands_of, describe, evaluate, parse_tree, ranking_of, select_top
from comparison_window import NOTE_PAIRS, NOTE_SET
from conversation_session import fingerprint
from data_contract import (CRS_ALIASES, SUPPORTED_CRS, ChoiceRequired, canonical_crs, count_unit_label, period_positions,
                           prepare, resolve_convention, text_values)
from geo_complement import frame_identity
from nearest_reference import (CONDITION_TEXT, METHOD as DISTANCE_METHOD, MOTIVES, TPL_11, _in_period, ellipsoid_note,
                               extreme_exact, nearest_exact, row_ids, territory_coordinates)
from request_memo import per_source
from semantic_bridge import (ROLE_NAMES, ROLES, coordinate_roles, premise_reason, role_established, territories_stable,
                             verified_separator)
from temporal_change import evolution_notes, window as series_window
from territorial_levels import (MAX_IDS, METODOS, NOTE_STATE_POPULATION, NOTE_STATES, ROTATION, Abrangencia, Parts,
                                _codes_text, human_period, municipal_index, national_reference, parse as parse_scope,
                                state_part, state_source, thousands, uf_label)
from territorial_selection import REGIONS, STATES, territory_catalog, texts
from trend import METHOD_VERSION as TREND_METHOD, classify, classify_frame, stage_block, summarize, time_unit

METHOD = "PAINEL-BOLHAS-1"
OPERATION = "painel"
OFFICIAL_ONLY = ("O painel integrado usa só a base Brasil oficial (fonte municipal) nesta versão; um arquivo importado "
                 "segue pelo formato da página única, com nivel (\"municipios\").")
GOVERNED = ("O painel usa as colunas do perfil oficial da base Brasil: código IBGE, município, período, categoria, "
            "quantidade e população e, com a referência, latitude e longitude.")
NO_CRS = ("A distância do painel precisa do referencial geodésico SIRGAS 2000, premissa governada da versão oficial da "
          "base Brasil; nesta versão da base ele não está estabelecido, e nenhum referencial é presumido.")
CRS_PENDING = ("Confirme o referencial geodésico em que as coordenadas da planilha foram coletadas: a distância é "
               "calculada no SIRGAS 2000 ou no WGS 84, sem converter um no outro, e nenhum referencial é presumido.")
CRS_UNSUPPORTED = ("Referencial geodésico informado não suportado nesta versão (somente " + SUPPORTED_CRS + "). Nenhuma "
                   "transformação, aproximação ou substituição é aplicada.")
# Referenciais em que o gráfico calcula a distância (nomes canônicos de data_contract.canonical_crs, Adendo REF-20261022);
# o elipsoide de cada um vem de nearest_reference. Toda conferência de referencial passa por _referencial_suportado.
REFERENCIAIS_ACEITOS = tuple(CRS_ALIASES)
REQUIRED_ROLES = frozenset(("territory", "territory_id", "period", "category", "count", "population"))
SPATIAL_ROLES = frozenset(("latitude", "longitude"))
PANEL_KEYS = frozenset(("competencia", "competencia_inicial", "categoria", "base", "conjuntos", "referencia"))
PAGE_ONLY = frozenset(("nivel", "indicador", "faixas_distancia", "tendencia", "grupos", "grupos_mapa", "faixas",
                       "condicoes", "ordenar", "comparar", "rotatividade", "premissas", "rotulos", "estados", "serie"))
PAGE_KEYS = PANEL_KEYS | PAGE_ONLY
REFERENCE_KEYS = frozenset(("competencia", "categoria", "universo", "criterio", "premissas", "rotulos"))
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
# Página única (22/10/2026). O nível Brasil (24/10/2026): o país inteiro como uma unidade, da fonte nacional (D3 e D4).
GROUP_ROLE = "grupo_territorial"
LEVELS = ("municipios", "estados", "brasil")
BRAZIL_ID = "br"
INDICATORS = {"densidade": "density", "quantidade": "quantity"}
GROUP_TYPES = {"quartis": 4, "quintis": 5, "decis": 10}
GROUP_NAMES = {4: "quartil", 5: "quintil", 10: "decil"}
ORDER_ATTRIBUTES = {"densidade": "densidade", "quantidade": "quantidade", "populacao": "populacao",
                    "distancia_km": "distancia", "variacao": "variacao"}
CONDITION_ATTRIBUTES = {"densidade": "densidade", "quantidade": "quantidade", "populacao": "populacao",
                        "distancia_km": "distancia"}
VALUE_TEXT = {"densidade": "densidade", "quantidade": "quantidade", "populacao": "população",
              "distancia": "distância até a referência", "variacao": "variação percentual"}
MAX_CONDITIONS = 12
MAX_WINDOW = 80
# Série temporal (24/10/2026): os valores observados em cada competência de um intervalo, sem classificação.
MAX_SERIE = 600
SERIE_METHOD = "SERIE-OBSERVADA-1"
# Território de referência por elegibilidade (24/10/2026): primeiro os territórios elegíveis (a delimitação e a condição,
# CAP-REF-01 por CAP-SUB-01), depois o mais próximo (CAP-ESP-02) ou o mais distante (CAP-ESP-01 com CAP-SUB-02 e
# CAP-SUB-03) de cada território, sem ele mesmo.
ELIGIBLE_KEYS = frozenset(("relacao", "delimitacao", "condicao"))
RELATIONS = {"mais_proxima": "mais próximo", "mais_distante": "mais distante"}
DELIMITATIONS = ("todos", "mesmo_grupo", "grupos", "mesma_regiao", "regioes")
ELIGIBLE_OPERATORS = ("<", "<=", ">", ">=")
ELIGIBLE_SHAPE = ("Território de referência inválido: use {\"relacao\": \"mais_proxima\" ou \"mais_distante\", "
                  "\"delimitacao\": {\"tipo\", \"valores\"}, \"condicao\": {\"atributo\", \"operador\", \"valor\"}}.")
PREMISE_KEYS = ("confirmed_roles", "count_unit", "custom_count_unit", "crs", "number_format", "object_declaration",
                "category_constant", "duplicate_policy", "component_columns")
COUNT_UNITS = ("pessoas", "vinculos", "postos", "outro")
NUMBER_FORMATS = ("decimal_comma", "decimal_point")
EMPTY = ["territory", "period", "category", "quantity", "population", "density"]
BAND_CONVENTION = "[a, b); o último intervalo inclui o limite superior"
SCOPE_FULL = "conjunto completo de referências"
ROLE_BY_NAME = {name: role for role, name in ROLE_NAMES.items()}


# --------------------------------------------------------------------------------------------- rótulos
@dataclass(frozen=True)
class Rotulo:
    """Nome de um nível territorial no texto: singular, plural e gênero gramatical (concordância dos artigos)."""
    singular: str
    plural: str
    genero: str = "m"

    def g(self, masculino: str, feminino: str) -> str:
        return feminino if self.genero == "f" else masculino

    def n(self, count: int) -> str:
        return thousands(count) + " " + (self.singular if count == 1 else self.plural)

    @property
    def Plural(self) -> str:
        return self.plural[:1].upper() + self.plural[1:]

    @property
    def Singular(self) -> str:
        return self.singular[:1].upper() + self.singular[1:]

    def public(self) -> dict:
        return {"singular": self.singular, "plural": self.plural, "genero": self.genero}


@dataclass(frozen=True)
class Rotulos:
    unidade: Rotulo
    grupo: Rotulo

    def public(self) -> dict:
        return {"unidade": self.unidade.public(), "grupo": self.grupo.public()}


BRASIL = Rotulos(Rotulo("município", "municípios"), Rotulo("estado", "estados"))
PADRAO = Rotulos(Rotulo("unidade", "unidades", "f"), Rotulo("grupo", "grupos"))
ROTULOS_SHAPE = ("Rótulos inválidos: use {\"unidade\": {\"singular\", \"plural\"}, \"grupo\": {\"singular\", \"plural\"} ou "
                 "null}, com \"genero\" (\"m\" ou \"f\") opcional.")
FEMININE = ("a", "ade", "ção", "são", "gião")


def _genero(word: str) -> str:
    """Gênero do substantivo principal (a primeira palavra) só para a concordância dos artigos: feminino nas terminações
    -a, -ade, -ção, -são e -gião (província, unidade, região); masculino nas demais (distrito, condado, cantão)."""
    head = unicodedata.normalize("NFC", word.strip().lower()).split()[0]
    return "f" if head.endswith(FEMININE) else "m"


def _rotulo(raw, default: Rotulo) -> Rotulo:
    if raw is None:
        return default
    if not isinstance(raw, dict) or set(raw) - {"singular", "plural", "genero"} or not {"singular", "plural"} <= set(raw):
        raise ValueError(ROTULOS_SHAPE)
    words = []
    for key in ("singular", "plural"):
        value = raw[key]
        if not isinstance(value, str) or not value.strip() or len(value) > 40 or any(ord(ch) < 32 for ch in value):
            raise ValueError("Rótulo inválido (" + key + "): use um texto de até 40 caracteres.")
        words.append(value.strip())
    gender = raw.get("genero")
    if gender not in (None, "m", "f"):
        raise ValueError("Gênero do rótulo inválido: use \"m\" ou \"f\".")
    return Rotulo(words[0], words[1], gender or _genero(words[0]))


def _labels(raw, brazil: bool) -> Rotulos:
    """Rótulos da resposta: fixos na base do Brasil (município e estado); nas planilhas, os recebidos ou os padrões."""
    if brazil:
        if raw not in (None, {}):
            raise ValueError("Na base do Brasil, os rótulos são fixos (município e estado): não envie rotulos.")
        return BRASIL
    if raw is None or raw == {}:
        return PADRAO
    if not isinstance(raw, dict) or set(raw) - {"unidade", "grupo"}:
        raise ValueError(ROTULOS_SHAPE)
    return Rotulos(_rotulo(raw.get("unidade"), PADRAO.unidade), _rotulo(raw.get("grupo"), PADRAO.grupo))


# --------------------------------------------------------------------------------------------- estruturas
@dataclass
class Context:
    """O que vale para todo o pedido: fonte (base Brasil ou planilha), mapeamento, índice da versão (Brasil), catálogo
    territorial, premissas, competência, categoria e a posição temporal de cada competência."""
    frame: pd.DataFrame
    mapping: dict
    index: object
    catalog: dict
    settings: dict
    period: str
    category: str
    positions: dict
    kind: str = "brasil"
    sources: object = None
    labels: Rotulos = BRASIL
    premissas: dict = field(default_factory=dict)
    group_column: str | None = None
    groups: dict = field(default_factory=dict)
    periods: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    density: bool = True
    page: bool = False
    nivel: str = "municipios"
    indicador: str | None = None
    periods_error: str = ""

    @property
    def brazil(self) -> bool:
        return self.kind == "brasil"


@dataclass
class Measures:
    """Valores de uma competência: registros por item (code:/name:/uf:), linhas da fonte e o quadro preparado pelo motor
    (com a coluna "key", o id do item). `fingerprint`, quando há, devolve o resumo das linhas lido pela chave de execução
    (o mesmo hash_pandas_object de `rows`, guardado por versão na base Brasil)."""
    period: str
    records: dict
    rows: pd.DataFrame
    data: pd.DataFrame | None
    parts: object = None
    fingerprint: object = None

    def row_hash(self) -> bytes:
        if self.fingerprint is not None:
            return self.fingerprint()
        return pd.util.hash_pandas_object(self.rows, index=True).values.tobytes()


@dataclass
class Spatial:
    """Distâncias até a referência (mínimo do conjunto completo de CAP-ESP-02) e os membros à menor distância (empates
    exatos incluídos) para os alvos com coordenada válida."""
    settings: dict
    coords: pd.DataFrame
    references: list
    invalid: list
    values: dict
    referencial: str  # o referencial confirmado (canônico), o das premissas e da chave de execução
    nearest: dict = field(default_factory=dict)
    states: dict | None = None  # condição de cada id, lida uma vez do quadro de coordenadas
    # Território de referência por elegibilidade: o motivo da distância não avaliável de cada alvo (sem território
    # elegível, elegível sem coordenada) e a avaliação da condição (contagens e quantos são elegíveis).
    reasons: dict = field(default_factory=dict)
    eligible: dict | None = None

    def condition(self, key):
        if self.states is None:
            self.states = self.coords["condicao"].to_dict()
        return self.states.get(key, "SEM_REGISTRO")


@dataclass
class Result:
    """Estado intermediário do cálculo, lido pelas funções da página única."""
    universe: list
    sets: list
    reference: dict | None
    final: Measures
    initial: Measures | None
    spatial: Spatial | None
    items: list
    engine_rows: pd.DataFrame
    changes: dict = field(default_factory=dict)
    frames: list = field(default_factory=list)
    digests: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    limitations: list = field(default_factory=list)
    methods: dict = field(default_factory=dict)


class Pendencia(ChoiceRequired):
    """Escolha pendente que a tela pode oferecer: a chave de options.premissas e as opções aceitas."""

    def __init__(self, text: str, chave: str | None = None, opcoes=()):
        super().__init__(text)
        self.chave = chave
        self.opcoes = list(opcoes)


# --------------------------------------------------------------------------------------------- utilidades
def _num(value):
    """Número nativo para o JSON: inteiro quando o valor é inteiro; ausente, NaN e infinito viram null (nunca zero)."""
    if type(value) is float:  # o caso comum (valores do pandas), sem conversão: o mesmo resultado do caminho geral
        return (int(value) if value.is_integer() else value) if math.isfinite(value) else None
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _present(value) -> bool:
    return _num(value) is not None


def _empty3():
    return {field: None for field in FIELDS3}


def _values3(record):
    return {field: _num(record["valores"][field]) for field in FIELDS3}


def _ratio(value):
    """O valor exato de Fraction(value) como par de inteiros (numerador, denominador > 0), sem montar o Fraction:
    inteiro como está e float pela expansão binária exata (float.as_integer_ratio, a mesma de Fraction(float))."""
    kind = type(value)
    if kind is int:
        return value, 1
    if kind is float:
        return value.as_integer_ratio()
    exact = Fraction(value)
    return exact.numerator, exact.denominator


def _pair(record, field):
    """Valor exato de um registro como par de inteiros (numerador, denominador): a densidade sai da quantidade e da
    população (quantidade × 1.000 ÷ população), sem passar pelo float, como em _exact."""
    values = record["valores"]
    if field != "densidade":
        return _ratio(values[field])
    qn, qd = _ratio(values["quantidade"])
    pn, pd_ = _ratio(values["populacao"])
    return qn * 1000 * pd_, qd * pn


def _exact(record, field):
    """Valor exato (Fraction) de um registro: a densidade sai da quantidade e da população, sem passar pelo float
    (como em combined_criteria e trend). O Fraction é montado uma vez do par de inteiros (o mesmo valor de
    Fraction(quantidade) × 1.000 ÷ Fraction(população))."""
    cache = record.setdefault("exatos", {})
    if field not in cache:
        cache[field] = Fraction(*_pair(record, field))
    return cache[field]


def _label(entry):
    """Nome do município com a UF do prefixo do código IBGE (regra brasil-cod-uf-prefix-1), como "MANAUS (AM)"; nas
    planilhas, o rótulo do catálogo territorial ("NOME [código]" ou "NOME")."""
    if entry.get("state"):
        return entry["name"] + " (" + entry["state"] + ")"
    return entry["label"]


def _join(parts):
    parts = list(parts)
    return parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " e " + parts[-1]


def _short(ctx, key):
    entry = ctx.catalog[key]
    return entry["code"] or entry["name"]


def _no_record(ctx, period):
    return ("Sem registro em " + human_period(period) + " na categoria " + ctx.category +
            ": valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)")


def _no_initial(period):
    return ("Variação não avaliável: sem registro na competência inicial, " + human_period(period) +
            " (SEM_REGISTRO_OBSERVADO)")


def _data_keys(ctx, territory: pd.Series) -> pd.Series:
    """Id do item de cada linha preparada pelo motor: code:<código> quando há código territorial (o rótulo do motor é
    "NOME [código]"), senão name:<nome>, a mesma identidade de row_ids e do catálogo territorial."""
    if ctx.mapping.get("territory_id"):
        return "code:" + territory.str.extract(r"\[([^\[\]]+)\]$", expand=False)
    return "name:" + territory.astype(str)


def _dedupe(values):
    return list(dict.fromkeys(values))


# --------------------------------------------------------------------------------------------- pedido
def is_page(options) -> bool:
    """Contrato da página única (22/10/2026): o pedido traz `nivel`."""
    return isinstance(options, dict) and "nivel" in options


def _keys(options, allowed):
    if not isinstance(options, dict):
        raise ValueError("Parâmetros do painel inválidos: envie um objeto JSON em options.")
    unknown = sorted(str(key)[:40] for key in set(options) - allowed)
    if unknown:
        text = "Parâmetro não reconhecido no painel: " + ", ".join(unknown[:5]) + "."
        if allowed is PANEL_KEYS and set(unknown) & PAGE_ONLY:
            text += " As chaves da página única valem com nivel (\"municipios\", \"estados\" ou \"brasil\")."
        raise ValueError(text)


def _period(value, periods, missing, where="nesta versão da base"):
    if value is None or value == "":
        if len(periods) == 1:
            return periods[0]
        raise ValueError(missing)
    if not isinstance(value, str) or value.strip() not in periods:
        raise ValueError("Competência inexistente " + where + ": " + str(value)[:16] + ". Escolha uma das competências " +
                         ("da base." if where == "nesta versão da base" else "da planilha."))
    return value.strip()


def _category(value, categories, where="nesta versão da base"):
    if value is None or value == "":
        if len(categories) == 1:
            return categories[0]
        raise ValueError("Escolha a categoria profissional do painel.")
    if not isinstance(value, str) or value.strip() not in categories:
        raise ValueError("Categoria profissional inexistente " + where + ": " + str(value)[:40] + ".")
    return value.strip()


def _mapping_shape(mapping):
    if not isinstance(mapping, dict) or any(not isinstance(key, str) or not isinstance(value, (str, type(None)))
                                            for key, value in mapping.items()):
        raise ValueError("Mapeamento de colunas inválido.")


def context(sources, mapping, options, allowed, frame=None, page=False) -> Context:
    """Validações comuns às duas rotas: fonte (base oficial ou planilha), colunas, competência e categoria existentes."""
    _keys(options, allowed)
    if frame is not None:
        return _upload_context(frame, mapping, options, page)
    return _brazil_context(sources, mapping, options, page)


def _brazil_context(sources, mapping, options, page) -> Context:
    municipal = sources.frame("municipal") if sources is not None else None
    if municipal is None or source_identity(municipal) != "municipal":
        raise ValueError(OFFICIAL_ONLY)
    _mapping_shape(mapping)
    if options.get("premissas") not in (None, {}):
        raise ValueError("Na base do Brasil, as premissas vêm do perfil oficial: não envie premissas.")
    labels = _labels(options.get("rotulos"), brazil=True)
    if page and mapping.get(GROUP_ROLE):
        raise ValueError("Na base do Brasil, o grupo dos municípios é o estado, pelo prefixo do código IBGE: não envie "
                         "grupo_territorial no mapeamento.")
    # Papel sem coluna (vazio) não conta; sem mapeamento, vale o do perfil oficial, que o painel exige de todo modo.
    mapping = {key: value for key, value in mapping.items() if value} or dict(FIELDS["municipal"])
    profile = curated_profile(municipal, mapping)
    if not REQUIRED_ROLES <= set((profile or {}).get("governed_roles") or []):
        raise ValueError(GOVERNED)
    index = municipal_index(municipal)
    # As mesmas premissas da análise de densidade (perfil oficial, sem as premissas de coordenadas).
    settings = _official_settings(municipal, mapping, False)
    catalog = {item["id"]: item for item in territory_catalog(municipal, mapping, settings)}
    periods = list(index.periods)
    period = _period(options.get("competencia"), periods, "Escolha a competência do painel.")
    category = _category(options.get("categoria"), list(index.categories))
    return Context(municipal, mapping, index, catalog, settings, period, category, period_positions(periods),
                   kind="brasil", sources=sources, labels=labels, periods=periods, categories=list(index.categories),
                   page=page)


@per_source()
def _official_settings(frame, mapping, spatial):
    """As premissas do perfil oficial da base Brasil (apply_premises sem opções do pedido), com ou sem as de coordenadas.
    Na base Brasil verificada, por versão (request_memo.per_source); cada chamada recebe cópia própria."""
    return apply_premises(frame, mapping, {}, spatial=spatial)


def _premissas(raw) -> dict:
    """Escolhas da pessoa sobre a planilha (as mesmas opções de /api/analyze): papéis escolhidos, unidade de contagem,
    referencial, separador decimal, objeto de análise, cópias idênticas e componentes. As premissas da análise continuam
    aplicadas pelo backend (analysis_premises), nunca enviadas pela tela."""
    if raw is None or raw == {}:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Premissas inválidas: envie um objeto em premissas, com as chaves " + ", ".join(PREMISE_KEYS) + ".")
    unknown = sorted(str(key)[:40] for key in set(raw) - set(PREMISE_KEYS))
    if unknown:
        raise ValueError("Premissa não reconhecida no gráfico: " + ", ".join(unknown[:5]) + ". Use " +
                         ", ".join(PREMISE_KEYS) + ".")
    out = {}
    for key in PREMISE_KEYS:
        value = raw.get(key)
        if value is None or value == "" or value == []:
            continue
        if key in ("confirmed_roles", "component_columns"):
            if (not isinstance(value, list) or len(value) > 32 or len(set(value)) != len(value) or
                    any(not isinstance(item, str) or not item or len(item) > 256 for item in value)):
                raise ValueError("Premissa inválida (" + key + "): envie uma lista de textos distintos.")
            if key == "confirmed_roles" and any(item not in ROLES for item in value):
                raise ValueError("Papel não reconhecido em premissas.confirmed_roles: use " + ", ".join(ROLES) + ".")
            out[key] = list(value)
            continue
        if not isinstance(value, str) or not value.strip() or len(value) > 120:
            raise ValueError("Premissa inválida (" + key + "): use um texto de até 120 caracteres.")
        if key == "count_unit" and value not in COUNT_UNITS:
            raise ValueError("Unidade de contagem não reconhecida: use pessoas, vinculos, postos ou outro.")
        if key == "number_format" and value not in NUMBER_FORMATS:
            raise ValueError("Separador decimal não reconhecido: use decimal_comma (vírgula) ou decimal_point (ponto).")
        if key == "duplicate_policy" and value != "remove_exact":
            raise ValueError("Tratamento de cópias idênticas não reconhecido: use remove_exact.")
        out[key] = value.strip()
    return out


def _groups_of(frame, mapping, column) -> dict:
    """Valor do grupo (coluna-mãe escolhida no papel grupo_territorial) de cada unidade, pela identidade de row_ids; a
    unidade com mais de um valor na planilha fica sem grupo (não entra na escolha por grupo)."""
    pairs = pd.DataFrame({"id": row_ids(frame, mapping).to_numpy(), "grupo": texts(frame[column]).to_numpy()})
    pairs = pairs.dropna(subset=["id"]).drop_duplicates()
    out = {}
    for key, group in pairs.groupby("id", sort=False):
        values = sorted(set(group["grupo"].dropna()))
        out[key] = values[0] if len(values) == 1 else None
    return out


def _upload_context(frame, mapping, options, page) -> Context:
    """Planilha enviada (só na página única): o mapeamento de /api/inspect confirmado na tela, as escolhas da pessoa em
    options.premissas e o mesmo portão de /api/analyze (pré-exame da análise de densidade ou de quantitativos)."""
    if frame is None or frame.empty:
        raise ValueError("Planilha sem registros.")
    _mapping_shape(mapping)
    mapping = {key: value for key, value in mapping.items() if value}
    group_column = mapping.pop(GROUP_ROLE, None)
    unknown = sorted(role for role in mapping if role not in ROLES)
    if unknown:
        raise ValueError("Papel de campo desconhecido no mapeamento: " + ", ".join(unknown[:5]) + ". Use " +
                         ", ".join(ROLES) + " ou " + GROUP_ROLE + ".")
    for column in [*mapping.values(), *([group_column] if group_column else [])]:
        if column not in frame.columns:
            raise ValueError("A coluna associada não existe nesta base: " + column)
    labels = _labels(options.get("rotulos"), brazil=False)
    unit, group = labels.unidade, labels.grupo
    if group_column and group_column in (mapping.get("territory"), mapping.get("territory_id")):
        raise ValueError("A coluna d" + group.g("o", "a") + " " + group.singular + " (grupo_territorial) precisa ser "
                         "diferente da coluna de " + unit.plural + " e do código.")
    premissas = _premissas(options.get("premissas"))
    if not mapping.get("territory"):
        raise ValueError("Escolha a coluna territorial: o gráfico mostra cada " + unit.singular + " da planilha.")
    if not mapping.get("period"):
        raise ValueError("Escolha a coluna de período: o gráfico é organizado por competência.")
    engine = dict(premissas)
    if group_column:
        engine["hierarchy_columns"] = {"territorio_superior_1": group_column}
    settings = apply_premises(frame, mapping, engine, spatial=False)
    # D1: nenhum papel sem regra e sem escolha da pessoa é usado (mesma regra do pré-exame de /api/analyze).
    used = [role for role in ("territory", "territory_id", "period", "category", "count", "population")
            if mapping.get(role)]
    if not mapping.get("count") and mapping.get("identity"):
        used.append("identity")
    pending = [role for role in used if not role_established(frame, mapping, settings, role)]
    if pending:
        raise Pendencia("Escolha a coluna de " + ROLE_NAMES[pending[0]] + " no seletor: a coluna indicada não foi "
                        "reconhecida nem escolhida.", "confirmed_roles", pending)
    raw_periods = list(dict.fromkeys(text_values(frame[mapping["period"]]).dropna().tolist()))
    positions, error = {}, ""
    try:
        positions = period_positions(raw_periods)
    except ValueError as exc:
        error = str(exc)
    periods = sorted(raw_periods, key=positions.get) if positions else sorted(raw_periods)
    if mapping.get("category"):
        categories = sorted(set(text_values(frame[mapping["category"]]).dropna().tolist()))
    else:
        categories = [str(settings.get("category_constant") or "FTS declarada")]
    period = _period(options.get("competencia"), periods, "Escolha a competência do gráfico.", "nesta planilha")
    category = _category(options.get("categoria"), categories, "nesta planilha")
    density = bool(mapping.get("population"))
    gate = {**engine, "period_filter": period, **({"category_filter": category} if mapping.get("category") else {})}
    _gate(frame, mapping, apply_premises(frame, mapping, gate), "density" if density else "counts", mapping)
    catalog = {item["id"]: item for item in territory_catalog(frame, mapping, settings)}
    groups = _groups_of(frame, mapping, group_column) if group_column else {}
    return Context(frame, mapping, None, catalog, settings, period, category, positions, kind="arquivo", labels=labels,
                   premissas=premissas, group_column=group_column, groups=groups, periods=periods, categories=categories,
                   density=density, page=page, periods_error=error)


def _gate(frame, mapping, options, capability, original_mapping):
    """O portão de /api/analyze na análise de densidade (ou de quantitativos, sem população): o pré-exame da ponte
    semântica, com as mesmas mensagens. Escolha pendente vira pendência estruturada; impedimento nos dados, 422."""
    from semantic_bridge import preflight  # importação tardia, como nos demais módulos do motor
    exam = preflight(frame, mapping, options)
    item = exam["capabilities"][capability]
    if item["status"] == "available":
        return exam
    missing = [entry["detail"] for entry in item["requirements"] if entry["status"] == "missing"]
    pending = [entry["detail"] for entry in item["requirements"] if entry["status"] == "needs_confirmation"]
    if missing or not pending:
        raise ValueError("Gráfico não habilitado para a planilha: " + " ".join(_dedupe(missing + pending or item["reasons"])))
    chave, opcoes = _classify(pending[0], original_mapping)
    raise Pendencia(" ".join(_dedupe(pending)), chave, opcoes)


PENDING = (("referencial geodésico", "crs", list(REFERENCIAIS_ACEITOS)),
           ("separador decimal", "number_format", list(NUMBER_FORMATS)),
           ("unidade de contagem", "count_unit", list(COUNT_UNITS)),
           ("linhas idênticas", "duplicate_policy", ["remove_exact"]),
           ("colunas que distinguem os componentes", "component_columns", []),
           ("código territorial", "confirmed_roles", ["territory_id"]))


def _classify(text: str, mapping=None):
    """Chave de options.premissas e opções de uma escolha pendente do motor (None quando a tela não a resolve)."""
    lower = text.lower()
    match = re.search(r"Escolha a coluna de (.+?) no seletor", text)
    if match and match.group(1) in ROLE_BY_NAME:
        return "confirmed_roles", [ROLE_BY_NAME[match.group(1)]]
    if "objeto de análise" in lower or "força de trabalho" in lower:
        return ("object_declaration" if (mapping or {}).get("category") else "category_constant"), []
    for fragment, key, options in PENDING:
        if fragment in lower:
            return key, list(options)
    return None, []


def pendencia(exc) -> dict:
    """Pendência estruturada de um ChoiceRequired (422): chave, opções e o texto para a tela oferecer a escolha."""
    if isinstance(exc, Pendencia):
        return {"chave": exc.chave, "opcoes": list(exc.opcoes), "texto": str(exc)}
    chave, opcoes = _classify(str(exc))
    return {"chave": chave, "opcoes": opcoes, "texto": str(exc)}


def _ids(values, ctx, what):
    """Identificadores de itens existentes no catálogo da base (code:<código IBGE>; nas planilhas, code:<código> ou
    name:<nome>, como row_ids), distintos."""
    unit = ctx.labels.unidade
    if (not isinstance(values, list) or len(values) > MAX_IDS or
            any(not isinstance(value, str) or not value or len(value) > 512 for value in values) or
            len(set(values)) != len(values)):
        raise ValueError("Identificadores inválidos (" + what + "): " +
                         ("use códigos distintos de municípios (code:<código IBGE>)." if ctx.brazil else
                          "use identificadores distintos de " + unit.plural + " (code:<código> ou name:<nome>)."))
    unknown = [value for value in values if value not in ctx.catalog]
    if unknown:
        raise ValueError(unit.Plural + " inexistentes ou incompatíveis com a base (" + what + "): " +
                         ", ".join(unknown[:8]) + ".")
    ambiguous = [ctx.catalog[value]["label"] for value in values if ctx.catalog[value]["selection_reason"]]
    if ambiguous:
        raise ValueError("Identificação territorial ambígua entre níveis superiores: " + ", ".join(ambiguous[:8]) + ".")
    return list(values)


def _universe(raw, ctx, what, allow_empty):
    """Itens de um universo com a forma de options.abrangencia.municipios (todos, estados inteiros ou ids), na ordem do
    código (RQ-REP-03). Na base Brasil valem as regras da abrangência (territorial_levels.parse); nas planilhas, "estados"
    carrega os valores do grupo (coluna grupo_territorial) e "ids" os identificadores das unidades."""
    unit = ctx.labels.unidade
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
        raise ValueError(unit.g("Nenhum", "Nenhuma") + " " + unit.singular + " " + unit.g("marcado", "marcada") +
                         " (" + what + ").")
    if municipios.get("ids") is not None:
        _ids(municipios["ids"], ctx, what)
    if ctx.brazil:
        scope = parse_scope({"municipios": municipios}, ctx.index.by_uf)
        if scope.mun_todos:
            codes = set(ctx.index.codes)
        else:
            codes = {ctx.catalog[item]["code"] for item in scope.ids}
            for prefix in scope.mun_estados:
                codes |= set(ctx.index.by_uf.get(prefix, ()))
        return ["code:" + code for code in sorted(codes)]
    keys = _upload_scope(municipios, ctx, what)
    return sorted(keys, key=lambda key: (ctx.catalog[key]["code"], key))


def _upload_scope(municipios, ctx, what):
    unit, group = ctx.labels.unidade, ctx.labels.grupo
    invalid = "Universo inválido (" + what + "): " + SCOPE_SHAPE + "."
    if set(municipios) - {"todos", "estados", "ids"} or not isinstance(municipios.get("todos", False), bool):
        raise ValueError(invalid)
    groups = municipios.get("estados") or []
    if (not isinstance(groups, list) or len(groups) > MAX_IDS or len(set(groups)) != len(groups) or
            any(not isinstance(value, str) or not value.strip() or len(value) > 512 for value in groups)):
        raise ValueError(invalid)
    if municipios.get("todos"):
        return set(ctx.catalog)
    keys = set(municipios.get("ids") or [])
    if groups:
        if not ctx.group_column:
            raise ValueError("A planilha não tem a coluna de " + group.singular + " escolhida (papel grupo_territorial): "
                             "marque " + unit.g("os", "as") + " " + unit.plural + " pelos identificadores ou todos.")
        known = {value for value in ctx.groups.values() if value}
        unknown = [value for value in groups if value not in known]
        if unknown:
            raise ValueError(group.Plural + " inexistentes na planilha (" + what + "): " + ", ".join(unknown[:8]) + ".")
        chosen = set(groups)
        keys |= {key for key, value in ctx.groups.items()
                 if value in chosen and key in ctx.catalog and not ctx.catalog[key]["selection_reason"]}
    return keys


def _sets(raw, ctx):
    """Conjuntos agregados pedidos (CAP-AGR-01): id, rótulo e ao menos dois membros da base (podem estar fora de base)."""
    unit = ctx.labels.unidade
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
            raise ValueError("O conjunto " + key + " está sem membros: escolha pelo menos " + unit.g("dois", "duas") +
                             " " + unit.plural + ".")
        _ids(members, ctx, "membros do conjunto " + key)
        if len(members) < 2:
            raise ValueError("O conjunto " + key + " precisa de pelo menos " + unit.g("dois", "duas") + " " +
                             unit.plural + ".")
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
    if attribute != "quantidade" and not ctx.density:
        raise ValueError(_no_population(ctx))
    universe = None
    if raw.get("universo") is not None:
        universe = _universe(raw["universo"], ctx, "o universo da ordenação da referência", allow_empty=False)
    return {"atributo": attribute, "ordem": order, "universo": universe}


def _reference(raw, ctx):
    """Referência (CAP-REF-01): um município ou um conjunto de municípios escolhido pelo usuário; o critério só registra
    a origem. Desde 24/10/2026, também o território de referência por elegibilidade (_eligible_reference)."""
    unit = ctx.labels.unidade
    if raw is None or raw == {}:
        return None
    if isinstance(raw, dict) and set(raw) & ELIGIBLE_KEYS:
        return _eligible_reference(raw, ctx)
    if not isinstance(raw, dict) or set(raw) - {"membros", "criterio"}:
        raise ValueError("Referência inválida: use {\"membros\", \"criterio\"}.")
    members = raw.get("membros")
    if not isinstance(members, list) or not members:
        raise ValueError("Escolha " + unit.g("o", "a") + " " + unit.singular + " de referência ou os membros do conjunto "
                         "de referência.")
    _ids(members, ctx, "membros da referência")
    return {"membros": list(members), "criterio": _criterion(raw.get("criterio"), ctx, allow_universe=True)}


def _eligible_reference(raw, ctx):
    """Território de referência por elegibilidade (pedido do responsável, 24/10/2026): a relação espacial (o mais
    próximo ou o mais distante), a delimitação dos territórios elegíveis (a base inteira, o mesmo grupo de cada
    território, grupos escolhidos e, na base do Brasil, a mesma Grande Região ou regiões escolhidas) e a condição
    (CAP-SUB-01 atômico: densidade, quantidade ou população, com <, ≤, > ou ≥ e o valor, pela mesma árvore das
    condições). Nada tem valor padrão: os três vêm do pedido. A referência de cada território é escolhida entre os
    elegíveis, sem ele mesmo (_eligible_spatial)."""
    if not isinstance(raw, dict) or set(raw) != ELIGIBLE_KEYS:
        raise ValueError(ELIGIBLE_SHAPE)
    relation = raw["relacao"]
    if not isinstance(relation, str) or relation not in RELATIONS:
        raise ValueError("Relação espacial não reconhecida: use mais_proxima ou mais_distante.")
    return {"modo": "elegiveis", "relacao": relation, "delimitacao": _delimitation(raw["delimitacao"], ctx),
            "condicao": _eligible_condition(raw["condicao"], ctx), "membros": [], "criterio": None}


def _delimitation(raw, ctx):
    """Universo dos elegíveis (CAP-UNI-01 com os níveis que a fonte tem): na base do Brasil, os estados (prefixo do
    código IBGE) e as Grandes Regiões (o primeiro dígito do código, a regra já usada na conversa e conferida com a coluna
    regiao_geografica); numa planilha, o grupo da coluna-mãe, quando há. Nenhum nível é presumido."""
    group = ctx.labels.grupo
    shape = ("Delimitação inválida: use {\"tipo\": \"todos\", \"mesmo_grupo\", \"grupos\", \"mesma_regiao\" ou \"regioes\", "
             "\"valores\": [...]}.")
    if not isinstance(raw, dict) or not isinstance(raw.get("tipo"), str) or set(raw) - {"tipo", "valores"}:
        raise ValueError(shape)
    kind, values = raw["tipo"], raw.get("valores")
    if kind not in DELIMITATIONS:
        raise ValueError(shape)
    if kind in ("mesma_regiao", "regioes") and not ctx.brazil:
        raise ValueError("As regiões (Norte, Nordeste, Sudeste, Sul e Centro-Oeste) existem só na base do Brasil: nesta "
                         "planilha, delimite " + ("pel" + group.g("o", "a") + " " + group.singular + " ou " if
                                                  ctx.group_column else "") + "pela planilha inteira.")
    if kind in ("mesmo_grupo", "grupos") and not ctx.brazil and not ctx.group_column:
        raise ValueError("A planilha não tem a coluna de " + group.singular + " (papel grupo_territorial): delimite pela "
                         "planilha inteira.")
    if kind in ("grupos", "regioes"):
        if (not isinstance(values, list) or not values or len(values) > MAX_IDS or len(set(values)) != len(values) or
                any(not isinstance(value, str) or not value.strip() for value in values)):
            raise ValueError("Escolha " + ("as regiões" if kind == "regioes" else group.g("os ", "as ") + group.plural) +
                             " da delimitação, sem repetir.")
        known = (set(REGIONS.values()) if kind == "regioes" else set(STATES) if ctx.brazil else
                 {value for value in ctx.groups.values() if value})
        unknown = [value for value in values if value not in known]
        if unknown:
            raise ValueError(("Regiões" if kind == "regioes" else group.Plural) + " inexistentes na delimitação: " +
                             ", ".join(value[:40] for value in unknown[:5]) + ".")
        values = sorted(values)
    elif values not in (None, []):
        raise ValueError("A delimitação " + kind + " não leva valores: eles valem só com grupos ou regioes.")
    else:
        values = []
    return {"tipo": kind, "valores": values, "texto": _delimitation_text(ctx, kind, values)}


def _delimitation_text(ctx, kind, values):
    """"da Região Norte", "do mesmo estado de cada município", "dos estados escolhidos (Acre e Amazonas)": o universo dos
    elegíveis em palavras, com os rótulos da fonte."""
    unit, group = ctx.labels.unidade, ctx.labels.grupo
    if kind == "todos":
        return "de todo o Brasil" if ctx.brazil else "de toda a planilha"
    if kind == "mesmo_grupo":
        return group.g("do mesmo ", "da mesma ") + group.singular + " de cada " + unit.singular
    if kind == "mesma_regiao":
        return "da mesma região de cada " + unit.singular
    if kind == "regioes":
        return "da Região " + values[0] if len(values) == 1 else "das regiões " + _join(values)
    names = [STATES[value][1] if ctx.brazil else value for value in values]
    if len(names) == 1:
        return group.g("do ", "da ") + group.singular + " " + group.g("escolhido", "escolhida") + " (" + names[0] + ")"
    return group.g("dos ", "das ") + group.plural + " " + group.g("escolhidos", "escolhidas") + " (" + _join(names) + ")"


def _eligible_condition(raw, ctx):
    """A condição dos elegíveis (CAP-SUB-01 atômico, pela árvore dos critérios combinados): o mesmo operador, o mesmo
    valor exato e o mesmo texto das Condições ("densidade > 2,36 por 1.000 habitantes")."""
    if not isinstance(raw, dict) or set(raw) != {"atributo", "operador", "valor"}:
        raise ValueError("Condição do território de referência inválida: use {\"atributo\", \"operador\", \"valor\"}.")
    attribute = raw["atributo"]
    if not isinstance(attribute, str) or attribute not in ATTRIBUTES:
        raise ValueError("Atributo da condição do território de referência não reconhecido: use densidade, quantidade ou "
                         "populacao.")
    if attribute in ("densidade", "populacao") and not ctx.density:
        raise ValueError(_no_population(ctx))
    if raw["operador"] not in ELIGIBLE_OPERATORS:
        raise ValueError("Operador da condição do território de referência não reconhecido: use <, <=, > ou >=.")
    leaf = {"id": "c1", "attribute": attribute, "operator": raw["operador"], "value": raw["valor"]}
    nodes, leaves, root = parse_tree(leaf, {"count_unit": ctx.settings.get("count_unit")})
    return {"atributo": attribute, "operador": raw["operador"], "valor": raw["valor"], "texto": nodes[leaves[0]]["condicao"],
            "nodes": nodes, "leaves": leaves, "root": root}


def _condition_value(condition):
    """O valor da condição como texto decimal canônico (o da árvore: sem arredondar), para a chave e a resposta."""
    return condition["nodes"][condition["leaves"][0]]["parametros"]["valor"]


def _eligible_normalized(reference):
    condition, delimitation = reference["condicao"], reference["delimitacao"]
    return {"modo": "elegiveis", "relacao": reference["relacao"],
            "delimitacao": {"tipo": delimitation["tipo"], "valores": list(delimitation["valores"])},
            "condicao": {"atributo": condition["atributo"], "operador": condition["operador"],
                         "valor": _condition_value(condition)}}


def _no_population(ctx):
    return ("A planilha não tem coluna de população associada: a densidade e a população não são calculadas. Use o "
            "indicador quantidade.")


def _temporal_premises(ctx):
    """Premissas temporais da evolução (comparabilidade e identidade territorial ao longo do tempo), como na mudança."""
    if ctx.periods_error:
        raise ValueError(ctx.periods_error)
    for key in ("temporal_comparability_confirmed", "territory_longitudinal_confirmed"):
        if not ctx.settings.get(key):
            if (not ctx.brazil and key == "territory_longitudinal_confirmed" and
                    not territories_stable(ctx.frame, ctx.mapping, ctx.settings)):
                raise ValueError("Identidade territorial ao longo do tempo não verificada: há códigos com nomes diferentes "
                                 "entre períodos.")
            raise ChoiceRequired(premise_reason(ctx.settings, key))


def _initial_period(ctx, options):
    if options.get("competencia_inicial") in (None, ""):
        return None
    if ctx.periods_error:
        raise ValueError(ctx.periods_error)
    initial = _period(options["competencia_inicial"], list(ctx.periods), "",
                      "nesta versão da base" if ctx.brazil else "nesta planilha")
    if ctx.positions[initial] >= ctx.positions[ctx.period]:
        raise ValueError("A competência inicial (" + initial + ") precisa ser anterior à competência do "
                         "painel (" + ctx.period + ").")
    _temporal_premises(ctx)
    return initial


# --------------------------------------------------------------------------------------------- valores do motor
@per_source()
def _row_positions(frame, mapping):
    """Posições das linhas da fonte por (competência, categoria), com os textos normalizados (text_values), como no
    filtro de _rows; sem coluna de categoria, a categoria é "". Na base Brasil verificada, guardado por versão
    (request_memo.per_source): o filtro de cada pedido não percorre de novo as 122 mil linhas."""
    period = text_values(frame[mapping["period"]]).to_numpy(dtype=object)
    category = (text_values(frame[mapping["category"]]).to_numpy(dtype=object) if mapping.get("category") else
                np.full(len(frame), "", dtype=object))
    keys = pd.DataFrame({"periodo": period, "categoria": category})
    return {key: positions for key, positions in keys.groupby(["periodo", "categoria"], sort=False, dropna=True)
            .indices.items()}


def _rows(frame, mapping, periods, category):
    """Linhas da fonte nas competências e na categoria pedidas, na ordem da fonte (as mesmas de um filtro por máscara)."""
    groups = _row_positions(frame, mapping)
    category = category if mapping.get("category") else ""
    parts = [groups[(period, category)] for period in dict.fromkeys(periods) if (period, category) in groups]
    positions = np.sort(np.concatenate(parts)) if parts else np.array([], dtype=np.int64)
    return frame.iloc[positions]


@per_source()
def _prepared(frame, mapping, settings, period, category, operation):
    """data_contract.prepare sobre as linhas da competência, com o id de cada item; na base Brasil verificada, guardado
    por versão (request_memo.per_source), como o índice municipal e o catálogo territorial."""
    data = prepare(_rows(frame, mapping, [period], category), mapping, settings, operation).copy()
    codes = data["territory"].str.extract(r"\[([^\[\]]+)\]$", expand=False)
    data["key"] = "code:" + codes if mapping.get("territory_id") else "name:" + data["territory"].astype(str)
    return data


def _measures(ctx, period) -> Measures:
    """Quantidade, população e densidade de cada item na competência e na categoria: a preparação da análise de
    densidade (ou de quantitativos, sem população) sobre as linhas da competência; cada linha é local ao território."""
    rows = _rows(ctx.frame, ctx.mapping, [period], ctx.category)
    if rows.empty:
        return Measures(period, {}, rows, None)
    data = _prepared(ctx.frame, ctx.mapping, ctx.settings, period, ctx.category, "density" if ctx.density else "counts")
    records = {key: {"valores": {"populacao": population, "quantidade": quantity, "densidade": density}}
               for key, quantity, population, density in zip(data["key"].tolist(), data["quantity"].tolist(),
                                                             data["population"].tolist(), data["density"].tolist())}
    return Measures(period, records, rows, data,
                    fingerprint=lambda: _rows_hash(ctx.frame, ctx.mapping, period, ctx.category))


@per_source()
def _rows_hash(frame, mapping, period, category) -> bytes:
    """Resumo das linhas da competência e da categoria (hash_pandas_object de _rows, o mesmo que a chave de execução lê
    de Measures.rows); na base Brasil verificada, guardado por versão (request_memo.per_source)."""
    return pd.util.hash_pandas_object(_rows(frame, mapping, [period], category), index=True).values.tobytes()


def _aggregate(ctx, measures, keys):
    """CAP-AGR-01 pelo motor da agregação municipal (main._compute, operação aggregate), sobre os membros com registro na
    competência: soma das quantidades, soma das populações (cada município uma vez) e densidade do conjunto."""
    import main as engine  # importação tardia: main usa este módulo
    data = measures.data
    chosen = data[data["key"].isin(keys)][EMPTY]
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
        record = measures.records.get(key)
        if record is None or not _present(record["valores"][attribute]):
            values[key] = {"avaliavel": False, "motivos": [_no_record(ctx, measures.period)]}
        else:
            values[key] = {"avaliavel": True, "valor": record["valores"][attribute], "exato": _exact(record, attribute)}
    ordered, positions, not_evaluable = _ranked(values, members, names, criterion["ordem"])
    return ordered, positions, not_evaluable, values


def _ranked(values, members, names, order):
    """combined_criteria.ranking_of (CAP-SUB-02) com os avaliáveis entregues já na ordem dela: valor exato, nome e id,
    com o float do valor à frente na chave (monótono no valor exato, decide quase todas as comparações sem Fraction; em
    float igual, decide o valor exato). A ordem, as posições e os não avaliáveis são os mesmos de ranking_of sobre
    `members`; ela só confere a sequência, sem refazer milhares de comparações entre frações."""
    sign = -1 if order == "desc" else 1
    evaluable = [key for key in members if values[key]["avaliavel"]]
    evaluable.sort(key=lambda key: (sign * float(values[key]["exato"]), sign * values[key]["exato"], names[key]["name"],
                                    key))
    return ranking_of(values, evaluable + [key for key in members if not values[key]["avaliavel"]], names, order)


def _upload_spatial_settings(ctx):
    """Planilha: latitude e longitude escolhidas ou reconhecidas, o referencial confirmado pela pessoa (SIRGAS 2000 ou
    WGS 84, nenhum presumido) e o separador decimal verificado nos dados ou escolhido."""
    unit = ctx.labels.unidade
    settings = apply_premises(ctx.frame, ctx.mapping, {**ctx.premissas, **(
        {"hierarchy_columns": {"territorio_superior_1": ctx.group_column}} if ctx.group_column else {})}, spatial=True)
    if not (ctx.mapping.get("latitude") and ctx.mapping.get("longitude")):
        raise ValueError("A distância exige latitude e longitude associadas na planilha (graus decimais) para cada " +
                         unit.singular + ".")
    roles = coordinate_roles(ctx.frame, ctx.mapping, settings)
    if roles != {"latitude", "longitude"}:
        missing = sorted(SPATIAL_ROLES - roles)
        raise Pendencia("Escolha as colunas de latitude e longitude (graus decimais).", "confirmed_roles", missing)
    crs = ctx.premissas.get("crs")
    if not crs:
        raise Pendencia(CRS_PENDING, "crs", list(REFERENCIAIS_ACEITOS))
    referencial = _referencial_suportado(crs)
    if referencial is None:
        raise ValueError(CRS_UNSUPPORTED)
    settings["crs"] = referencial
    return settings


def _spatial_settings(ctx):
    """Premissas das coordenadas, as mesmas da análise espacial: na base Brasil, o perfil oficial (papéis de latitude e
    longitude e o referencial SIRGAS 2000 governados); na planilha, as colunas escolhidas ou reconhecidas, o referencial
    confirmado pela pessoa (sem ele, a pendência crs) e o separador decimal verificado nos dados ou escolhido."""
    if ctx.brazil:
        settings = _official_settings(ctx.frame, ctx.mapping, True)
        if not SPATIAL_ROLES <= set(settings.get("governed_roles") or []):
            raise ValueError(GOVERNED)
        if _referencial_suportado(settings.get("crs")) is None:
            raise Pendencia(NO_CRS)
        return settings
    return _upload_spatial_settings(ctx)


def _referencial_suportado(crs) -> str | None:
    """Nome canônico do referencial (data_contract.canonical_crs, só apelidos enumerados) quando o gráfico calcula a
    distância nele; None para os demais, sem presumir, transformar nem aproximar."""
    referencial = canonical_crs(crs)
    return referencial if referencial in REFERENCIAIS_ACEITOS else None


def _coordinate_layer():
    """Identidade da camada complementar de coordenadas lida por territory_coordinates (entra na chave da memória)."""
    from geo_complement import state  # importação tardia, como em semantic_bridge
    current = state()
    return current.get("sha256") or current.get("estado")


@per_source(extra=_coordinate_layer)
def _coordinates(frame, mapping, settings, period):
    """nearest_reference.territory_coordinates sobre as linhas da competência; na base Brasil verificada, guardado por
    versão da base e da camada complementar (as coordenadas não dependem do pedido)."""
    return territory_coordinates(_in_period(frame, mapping, period), mapping, settings)


_CALCULO = contextvars.ContextVar("painel_calculo")


@per_source(extra=_coordinate_layer)
def _reaproveitado(frame, analise, entradas):
    """Resultado de uma análise da página única sobre a base Brasil verificada, guardado por versão da base e da camada
    de coordenadas (request_memo.per_source). `entradas` reúne tudo de que o cálculo depende além da versão; o cálculo
    vem de _reaproveitar."""
    return _CALCULO.get()()


def _ids_key(ids):
    """Lista de ids na chave da memória (universo, itens, alvos: milhares de municípios): o SHA-256 dos ids, na ordem."""
    return hashlib.sha256("\x1f".join(ids).encode()).hexdigest()


def _reaproveitar(ctx, analise, entradas, calcular):
    """Reaproveita entre pedidos o que não mudou: quando só a ordenação muda, as distâncias, as condições, os grupos e as
    faixas vêm do pedido anterior, sem recalcular. A chave é a da memória da versão (U8 em Docs/OTIMIZACAO_LATENCIA.md,
    só sobre a cópia íntegra marcada): versão verificada, camada de coordenadas, nível, mapeamento, competência,
    categoria e as `entradas` da análise (universo, referência, definição). `calcular` devolve só valores serializáveis;
    cada pedido recebe cópia própria. Nas planilhas, nada fica guardado: calcula a cada pedido."""
    if not ctx.brazil:
        return calcular()
    token = _CALCULO.set(calcular)
    try:
        return _reaproveitado(ctx.frame, analise, {"nivel": ctx.nivel, "mapeamento": ctx.mapping, "competencia": ctx.period,
                                                    "categoria": ctx.category, **entradas})
    finally:
        _CALCULO.reset(token)


def _spatial(ctx, references, targets) -> Spatial:
    """Coordenadas da competência e distância de cada alvo até a referência mais próxima do conjunto completo de
    referências (nearest_exact, como em compute_nearest), com os membros empatados à menor distância. Com alguma
    referência sem coordenada válida, nenhuma distância é avaliável (DEPENDENCIA_NAO_AVALIAVEL), sem substituição pelo
    mínimo entre as avaliáveis."""
    settings = _spatial_settings(ctx)
    coords = _coordinates(ctx.frame, ctx.mapping, settings, ctx.period)
    spatial = Spatial(settings, coords, list(references), [], {}, referencial=_referencial_suportado(settings.get("crs")))
    spatial.invalid = [(key, spatial.condition(key)) for key in references if spatial.condition(key) != "VALIDA"]
    valid = [key for key in dict.fromkeys(targets) if spatial.condition(key) == "VALIDA"]
    if not spatial.invalid and valid:
        members = list(references)

        def calcular():
            best, ties, _ = nearest_exact(coords.loc[valid, "lat"], coords.loc[valid, "lon"],
                                          coords.loc[members, "lat"], coords.loc[members, "lon"], crs=spatial.referencial)
            return ({key: float(best[i]) / 1000 for i, key in enumerate(valid)},
                    {key: [members[j] for j in ties[i]] for i, key in enumerate(valid)})

        spatial.values, spatial.nearest = _reaproveitar(ctx, "distancias", {"referencias": members,
                                                                            "alvos": _ids_key(valid)}, calcular)
    return spatial


def _group_key(ctx, key):
    """Grupo de uma unidade na delimitação: o estado (prefixo do código IBGE) na base do Brasil; numa planilha, o valor
    da coluna-mãe (sem ela, nenhum)."""
    if ctx.brazil:
        return ctx.catalog[key]["code"][:2] or None
    return (ctx.groups.get(key) or None) if ctx.group_column else None


def _region_key(ctx, key):
    """Grande Região da unidade na base do Brasil, pelo primeiro dígito do código IBGE (a regra da conversa, conferida com
    a coluna regiao_geografica da base versionada em test_levels_real_data.py)."""
    return REGIONS.get(ctx.catalog[key]["code"][:1]) if ctx.brazil else None


def _eligibility(ctx, final, condition, keys):
    """CAP-SUB-01 atômico em cada unidade da base, pela mesma avaliação das Condições (combined_criteria.evaluate, valores
    exatos, três estados): ATENDE, NAO_ATENDE ou NAO_AVALIAVEL (sem registro ou sem o valor; nunca elegível)."""
    table = {condition["atributo"]: _record_values(final, condition["atributo"], keys)}
    inputs = {"nodes": condition["nodes"], "root": condition["root"], "leaves": condition["leaves"], "targets": list(keys),
              "catalog": {}}
    return {record["elemento"]: record["estado"] for record in evaluate(None, None, None, inputs, _Evaluator(table))}


def _eligible_spatial(ctx, reference, final, targets) -> Spatial:
    """Território de referência por elegibilidade (24/10/2026). Primeiro os elegíveis: as unidades da delimitação que
    atendem à condição na competência. Depois, para cada alvo com coordenada válida e sem ele mesmo entre os elegíveis, a
    referência mais próxima (CAP-ESP-02, mínimo do conjunto completo) ou a mais distante (as distâncias de CAP-ESP-01
    ordenadas pela CAP-SUB-02, com a 1ª posição pela CAP-SUB-03), com todos os empates exatos (extreme_exact, só
    geodésicas de Karney decidem). Como no conjunto de referência: um elegível sem coordenada válida deixa a distância
    do alvo não avaliável (DEPENDENCIA_NAO_AVALIAVEL), sem trocar pelo extremo entre os demais; sem elegível, também, com
    o motivo (CONJUNTO_REFERENCIAS_VAZIO), nunca distância zero."""
    settings = _spatial_settings(ctx)
    coords = _coordinates(ctx.frame, ctx.mapping, settings, ctx.period)
    spatial = Spatial(settings, coords, [], [], {}, referencial=_referencial_suportado(settings.get("crs")))
    condition, delimitation = reference["condicao"], reference["delimitacao"]
    farthest = reference["relacao"] == "mais_distante"
    valid = [key for key in dict.fromkeys(targets) if spatial.condition(key) == "VALIDA"]
    kind, chosen = delimitation["tipo"], set(delimitation["valores"])

    def pool_of(key):
        if kind == "mesmo_grupo":
            return "g", _group_key(ctx, key)
        if kind == "mesma_regiao":
            return "r", _region_key(ctx, key)
        return "*", None

    def calcular():
        universe = sorted((key for key, entry in ctx.catalog.items() if not entry["selection_reason"]),
                          key=lambda key: (ctx.catalog[key]["code"], key))
        states = _eligibility(ctx, final, condition, universe)
        eligible = [key for key in universe if states[key] == "ATENDE"]

        def members_of(pool):
            side, value = pool
            if side == "g":
                return [key for key in eligible if value is not None and _group_key(ctx, key) == value]
            if side == "r":
                return [key for key in eligible if value is not None and _region_key(ctx, key) == value]
            if kind == "grupos":
                return [key for key in eligible if _group_key(ctx, key) in chosen]
            if kind == "regioes":
                return [key for key in eligible if _region_key(ctx, key) in chosen]
            return eligible

        pools = {}
        for key in valid:
            pools.setdefault(pool_of(key), []).append(key)
        values, nearest, reasons = {}, {}, {}
        for pool, alvos in pools.items():
            members = members_of(pool)
            invalid = [(key, spatial.condition(key)) for key in members if spatial.condition(key) != "VALIDA"]
            if invalid:
                text = _eligible_gap(ctx, invalid)
                for key in alvos:
                    reasons[key] = text
                continue
            index = {key: i for i, key in enumerate(members)}
            best, ties, _ = extreme_exact(coords.loc[alvos, "lat"], coords.loc[alvos, "lon"],
                                          coords.loc[members, "lat"], coords.loc[members, "lon"], crs=spatial.referencial,
                                          farthest=farthest, skip=[index.get(key, -1) for key in alvos])
            for i, key in enumerate(alvos):
                if ties[i]:
                    values[key] = float(best[i]) / 1000
                    nearest[key] = [members[j] for j in ties[i]]
                else:
                    reasons[key] = _no_eligible(ctx, reference, pool)
        counts = {state: sum(value == state for value in states.values()) for state in ("ATENDE", "NAO_ATENDE",
                                                                                         "NAO_AVALIAVEL")}
        return {"valores": values, "referencias": nearest, "motivos": reasons,
                "elegiveis": {"universo": len(universe), "atende": counts["ATENDE"], "nao_atende": counts["NAO_ATENDE"],
                              "nao_avaliaveis": counts["NAO_AVALIAVEL"]}}

    entradas = {"relacao": reference["relacao"], "delimitacao": [kind, sorted(chosen)],
                "condicao": [condition["atributo"], condition["operador"], _condition_value(condition)],
                "alvos": _ids_key(valid)}
    out = _reaproveitar(ctx, "distancias_elegiveis", entradas, calcular)
    spatial.values, spatial.nearest, spatial.reasons = out["valores"], out["referencias"], out["motivos"]
    spatial.eligible = out["elegiveis"]
    return spatial


def _eligible_gap(ctx, invalid):
    names = [_label(ctx.catalog[key]) + " (" + MOTIVES[state] + ")" for key, state in invalid[:5]]
    more = " e mais " + str(len(invalid) - 5) if len(invalid) > 5 else ""
    return ("Distância não avaliável em " + human_period(ctx.period) + ": sem coordenada válida " +
            ("no território elegível " if len(invalid) == 1 else "nos territórios elegíveis ") + _join(names) + more +
            "; a referência não é escolhida entre os demais (DEPENDENCIA_NAO_AVALIAVEL)")


def _no_eligible(ctx, reference, pool):
    """Sem território de referência para o alvo: nenhuma outra unidade da delimitação atende à condição (ou, na planilha,
    a unidade não tem o grupo da coluna-mãe)."""
    unit, group = ctx.labels.unidade, ctx.labels.grupo
    side, value = pool
    if side in ("g", "r") and value is None:
        return ("Sem território de referência: " + unit.g("este ", "esta ") + unit.singular + " não tem " +
                group.singular + " na fonte (DEPENDENCIA_NAO_AVALIAVEL)")
    where = (group.g("do ", "da ") + group.singular + " " + (STATES[value][1] if ctx.brazil else value) if side == "g" else
             "da Região " + value if side == "r" else reference["delimitacao"]["texto"])
    return ("Sem território de referência: nenhum" + unit.g("", "a") + " outr" + unit.g("o", "a") + " " + unit.singular +
            " " + where + " atende à condição " + reference["condicao"]["texto"] + " em " + human_period(ctx.period) +
            " (DEPENDENCIA_NAO_AVALIAVEL, CONJUNTO_REFERENCIAS_VAZIO)")


def _eligible_origin(ctx, reference, spatial):
    """Forma de definição e origem do território de referência (CAP-REF-01): a relação, os elegíveis, a condição e
    quantas unidades da base a atendem na competência."""
    unit = ctx.labels.unidade
    counts = spatial.eligible or {}
    relation = (unit.g("mais próximo", "mais próxima") if reference["relacao"] == "mais_proxima" else "mais distante")
    return ("Para cada " + unit.singular + ", " + unit.g("o", "a") + " " + unit.singular + " " + relation + " entre " +
            unit.g("os", "as") + " " + unit.plural + " " + reference["delimitacao"]["texto"] + " com " +
            reference["condicao"]["texto"] + " em " + human_period(ctx.period) + " (" + thousands(counts.get("atende", 0)) +
            " de " + unit.n(counts.get("universo", 0)) + " da base atendem à condição); " + unit.g("o próprio", "a própria") +
            " " + unit.singular + " não é a sua referência. A condição é escolha do usuário e não tem caráter normativo")


def _eligible_block(ctx, reference, spatial, items, final):
    """`referencia` da resposta no modo por elegibilidade: a definição, as contagens da condição e os territórios que
    ficaram como referência de algum item (na ordem do código), com a UF, a população, a quantidade e a densidade de cada
    um na competência, lidas das mesmas medidas dos itens (25/10/2026: a tela mostra a referência do território base)."""
    used = sorted({key for item in items if item["tipo"] == "municipio" for key in spatial.nearest.get(item["id"], [])},
                  key=lambda key: (ctx.catalog[key]["code"], key))

    def member(key):
        entry, record = ctx.catalog[key], final.records.get(key)
        values = record["valores"] if record is not None else {}
        return {"id": key, "rotulo": _label(entry), "uf": entry.get("state") or None,
                "populacao": _num(values.get("populacao")), "quantidade": _num(values.get("quantidade")),
                "densidade": _num(values.get("densidade"))}
    condition, delimitation = reference["condicao"], reference["delimitacao"]
    return {"tipo": "elegiveis", "relacao": reference["relacao"],
            "delimitacao": {"tipo": delimitation["tipo"], "valores": list(delimitation["valores"]),
                            "texto": delimitation["texto"]},
            "condicao": {"atributo": condition["atributo"], "operador": condition["operador"],
                         "valor": _condition_value(condition), "texto": condition["texto"]},
            "elegiveis": dict(spatial.eligible or {}),
            "membros": [member(key) for key in used],
            "origem": _eligible_origin(ctx, reference, spatial)}


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
    if key in spatial.reasons:
        return spatial.reasons[key]
    return _reference_gap(ctx, spatial) if spatial.invalid else None


def _percent(before, after):
    """Variação percentual de CAP-TMP-01 (temporal_change.change: (v2 − v1) ÷ v1 × 100, em aritmética exata) entre dois
    valores exatos dados como pares de inteiros (n, d > 0): o par (numerador, denominador) da mesma fração, ou None com
    valor inicial zero (BASE_ZERO). Em inteiros, sem um Fraction por operação: Fraction(*par) é o valor de change, e
    numerador ÷ denominador é o float dele (divisão inteira com arredondamento correto, como float(Fraction))."""
    an, ad = before
    bn, bd = after
    if an == 0:
        return None
    return (bn * ad - an * bd) * 100, bd * an


def _percentages(ctx, before, after, fields=FIELDS3):
    """CAP-TMP-01 campo a campo: a variação de temporal_change.change sobre os valores exatos (_percent); base zero fica
    nula, com o motivo; campo sem valor numa das competências (população estadual incompleta) fica nulo, com o motivo.
    Devolve também as variações exatas, como pares (numerador, denominador) lidos pela ordenação (_values)."""
    variation, exact, zero, missing = {}, {}, [], []
    for field in FIELDS3:
        variation[field], exact[field] = None, None
        if field not in fields:
            continue
        if not _present(before["valores"][field]) or not _present(after["valores"][field]):
            missing.append(field)
            continue
        percent = _percent(_pair(before, field), _pair(after, field))
        exact[field] = percent
        variation[field] = None if percent is None else _num(percent[0] / percent[1])
        if percent is None:
            zero.append(field)
    motives = []
    if zero:
        motives.append("Variação percentual " + _join(["da " + LABELS3[field] for field in zero]) +
                       " não avaliável: valor inicial zero (BASE_ZERO)")
    if missing:
        motives.append("Variação percentual " + _join(["da " + LABELS3[field] for field in missing]) +
                       " não avaliável: sem valor em uma das competências (DADO_AUSENTE)")
    return variation, not zero and not missing, motives, exact


# --------------------------------------------------------------------------------------------- itens
def _unit_item(ctx, key, final, initial, spatial, reference_ids, changes=None):
    entry = ctx.catalog[key]
    record = final.records.get(key)
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
        before = initial.records.get(key)
        if before is not None:
            inicial = _values3(before)
        if record is not None and before is None:
            motives.append(_no_initial(initial.period))
        elif record is not None:
            variation, variation_ok, why, exact = _percentages(ctx, before, record,
                                                              FIELDS3 if ctx.density else ("quantidade",))
            motives += why
            if changes is not None:
                changes[key] = exact
    item.update({"inicial": inicial, "variacao_percentual": variation,
                 "avaliavel": {"densidade": item["densidade"] is not None, "distancia": distance_ok,
                               "variacao": variation_ok},
                 "motivos": motives, "referencia": key in reference_ids})
    return item


def _set_item(ctx, spec, final, initial, spatial, reference, changes=None):
    unit = ctx.labels.unidade
    members = spec["membros"]
    present = [key for key in members if key in final.records]
    motives, record = [], None
    if present:
        record = _aggregate(ctx, final, present)
        if len(present) < len(members):
            outside = [_label(ctx.catalog[key]) for key in members if key not in present]
            motives.append("Agregado parcial em " + human_period(final.period) + ": " + str(len(present)) + " de " +
                           str(len(members)) + " " + unit.plural + " com registro; fora: " + ", ".join(outside[:8]) +
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
    if spatial is not None and reference is not None and reference.get("modo") == "elegiveis":
        # Cada membro tem o seu território de referência: o conjunto não tem um ponto nem uma referência únicos.
        distance_ok = False
        motives.append("Distância não se aplica ao conjunto: com o território de referência escolhido para cada " +
                       unit.singular + ", cada membro tem a sua referência, e o conjunto não tem um ponto único")
    elif spatial is not None:
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
        before = [key for key in members if key in initial.records]
        record0 = _aggregate(ctx, initial, before) if before else None
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
            variation, variation_ok, why, exact = _percentages(ctx, record0, record)
            motives += why
            if changes is not None:
                changes[spec["id"]] = exact
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
    unit = ctx.labels.unidade
    members = reference["membros"]
    single = len(members) == 1
    tail = "" if single else "; a distância vai até o membro mais próximo (mínimo do conjunto completo, CAP-ESP-02)"
    criterion = reference["criterio"]
    if criterion is None:
        return ("Escolhida por você (lista explícita); nenhuma referência foi escolhida pelo sistema" if single else
                "Conjunto de " + str(len(members)) + " " + unit.plural + " escolhido por você (lista explícita)") + tail
    head = (("Escolhida" if single else "Conjunto escolhido") + " pelo critério " + ATTRIBUTES[criterion["atributo"]] +
            " (" + ORDERS[criterion["ordem"]] + ")")
    universe = criterion["universo"]
    scope = "no universo da ordenação (" + unit.n(len(universe or [])) + ")"
    if universe is None:
        universe, scope = base, "entre " + unit.g("os", "as") + " " + unit.plural + " base (" + unit.n(len(base)) + ")"
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
def _identity_note(ctx):
    if ctx.brazil:
        return ("Identificação territorial: código IBGE do perfil da base oficial; a UF segue o prefixo do código "
                "(regra brasil-cod-uf-prefix-1).")
    if ctx.mapping.get("territory_id"):
        return ("Identificação territorial: código e nome da planilha (code:<código>); códigos não foram confrontados "
                "com cadastro externo.")
    return ("Identificação territorial: nome da planilha (name:<nome>), sem código; nomes repetidos não são "
            "distinguidos.")


def _notes(ctx, base, sets, items, final, initial, spatial, reference):
    unit = count_unit_label(ctx.mapping, ctx.settings)
    lab = ctx.labels.unidade
    if ctx.density:
        values_note = ("Valores de " + ctx.category + " em " + human_period(ctx.period) + " pela mesma preparação da "
                       "análise de densidade. Densidade = quantitativo / população × 1.000 (por 1.000 habitantes, em "
                       "precisão integral; o arredondamento é só da apresentação).")
    else:
        values_note = ("Valores de " + ctx.category + " em " + human_period(ctx.period) + " pela mesma preparação da "
                       "análise de quantitativos. Sem coluna de população associada, a densidade e a população não são "
                       "calculadas.")
    notes = [*premise_notes(ctx.settings, "density" if ctx.density else "counts", ctx.mapping), values_note,
             "Valores ausentes e denominadores nulos não são transformados em zero; itens não avaliáveis seguem com o "
             "motivo.",
             "Unidade de contagem: " + unit + ". Não há conversão entre pessoas, vínculos e postos.",
             _identity_note(ctx)]
    for label, measures in ((lab.Plural + " base", final), (lab.Plural + " base na competência inicial", initial)):
        if not base or measures is None:
            continue
        missing = [_short(ctx, key) for key in base if key not in measures.records]
        text = (label + " (" + human_period(measures.period) + "): " + thousands(len(base) - len(missing)) + " de " +
                thousands(len(base)) + " com registro")
        notes.append(text + ("; sem registro (não avaliáveis): " + _codes_text(missing) if missing else "") + ".")
    if sets:
        notes.append("Conjuntos (CAP-AGR-01): soma das contagens dos componentes, com possível dupla contagem; quem atua "
                     "em mais de " + lab.g("um", "uma") + " " + lab.singular + " é contado em cada " +
                     lab.g("um", "uma") + ", e o total não é o número de profissionais distintos. Densidade do conjunto = "
                     "soma dos quantitativos / soma das populações × 1.000, cada população " +
                     ("municipal" if ctx.brazil else "de " + lab.singular) + " uma vez. Membro sem registro na "
                     "competência fica fora (agregado parcial, AGREGADO_PARCIAL).")
        notes += premise_notes(ctx.settings, "aggregate", ctx.mapping)
    if spatial is not None:
        if spatial.values:
            notes.append(TPL_11)
        notes.append(ellipsoid_note(spatial.referencial) + "distância pelo problema geodésico inverso de Karney, em "
                     "quilômetros e sem arredondamento no cálculo.")
        notes.append("Coordenadas da competência " + ctx.period + "; coordenadas de outras competências não são "
                     "tratadas como equivalentes.")
        members = reference["membros"]
        if reference.get("modo") == "elegiveis":
            notes.append("Território de referência: " + _eligible_origin(ctx, reference, spatial) + ".")
            notes.append("Primeiro os elegíveis (CAP-REF-01 pela condição, CAP-SUB-01); depois, para cada " + lab.singular +
                         ", " + ("a menor distância entre eles (CAP-ESP-02, mínimo do conjunto completo)" if
                                 reference["relacao"] == "mais_proxima" else
                                 "a maior distância entre eles (as distâncias de CAP-ESP-01 em ordem decrescente, "
                                 "CAP-SUB-02, e a 1ª posição, CAP-SUB-03)") + ", com todos os empates exatos. Um elegível "
                         "sem coordenada válida deixa a distância não avaliável, sem trocar pelo extremo entre os demais; "
                         "sem elegível, não há distância (nunca zero).")
        else:
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
                     "exata, para " + ("população, quantidade e densidade" if ctx.density else "a quantidade") +
                     "; não indica tendência. Com valor inicial zero, a variação percentual não é avaliável (BASE_ZERO); "
                     "conjunto com membros diferentes entre as competências não tem variação (INCOMPARABILIDADE).")
        notes += premise_notes(ctx.settings, "temporal", ctx.mapping)
    if ctx.brazil:
        used = {ctx.catalog[key]["code"] for key in base} | {ctx.catalog[key]["code"] for spec in sets
                                                             for key in spec["membros"]}
        if reference is not None:
            used |= {ctx.catalog[key]["code"] for key in reference["membros"]}
        for measures in (final, initial):
            if measures is None:
                continue
            codes = sorted(used & set(ctx.index.divergent.get(measures.period, [])))
            if codes:
                notes.append("Em " + human_period(measures.period) + ", " + str(len(codes)) + " registro(s) da fonte "
                             "municipal trazem na coluna uf um estado diferente do indicado pelo código IBGE (" +
                             _codes_text(codes) + "); o estado segue o código, e os valores entram como estão na fonte.")
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


def _execution_key(ctx, final, initial, normalized, spatial, extra=None, frames=(), digests=()):
    """Chave reproduzível, como em /api/analyze: dados usados, fonte (versão verificada ou arquivo enviado), mapeamento,
    pedido normalizado, premissas, operação e métodos (com a camada de coordenadas válida, quando há distância)."""
    digest = hashlib.sha256()
    for measures in (final, initial):
        if measures is not None and not measures.rows.empty:
            digest.update(measures.row_hash())
    for frame in frames:
        if frame is not None and not frame.empty:
            digest.update(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    for value in digests:
        digest.update(value.encode())
    signature = {"data": digest.hexdigest(), "source": ctx.frame.attrs.get("source"), "mapping": ctx.mapping,
                 "options": normalized, "operation": OPERATION, "method": METHOD,
                 "premissas": sorted(set(ctx.settings.get("governed_premises") or []) |
                                     set(ctx.settings.get("analysis_premises") or []))}
    if not ctx.brazil:
        signature["input_file"] = ctx.frame.attrs.get("input_file")
        signature["grupo_territorial"] = ctx.group_column
    if initial is not None:
        signature["variacao"] = "CAP-TMP-01/DA-14"
    if spatial is not None:
        signature["distancia"] = {"metodo": DISTANCE_METHOD["versao"], "referencial": spatial.referencial,
                                  "premissas": sorted(spatial.settings.get("governed_premises") or [])}
        geo = frame_identity(ctx.frame)
        if geo.get("estado") == "valido":
            signature["geo_complement"] = geo
    if extra:
        signature["pagina"] = extra
    return hashlib.sha256(json.dumps(signature, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


# --------------------------------------------------------------------------------------------- página única: pedido
def _page_spec(ctx, options) -> dict:
    """Validação das chaves da página única antes de qualquer cálculo (falha cedo, com a mensagem em português)."""
    unit = ctx.labels.unidade
    nivel = options.get("nivel")
    if nivel not in LEVELS:
        raise ValueError("Nível do gráfico inválido: use \"municipios\", \"estados\" ou \"brasil\".")
    if nivel == "estados" and not ctx.brazil:
        raise ValueError("O nível estados existe só na base do Brasil, com a fonte estadual de médicos únicos; nas "
                         "planilhas, o gráfico mostra " + unit.g("os", "as") + " " + unit.plural + ".")
    if nivel == "brasil" and not ctx.brazil:
        raise ValueError("O nível Brasil existe só na base do Brasil, com a contagem da fonte nacional; nas planilhas, o "
                         "gráfico mostra " + unit.g("os", "as") + " " + unit.plural + ".")
    if nivel != "estados" and options.get("estados") is not None:
        raise ValueError("A lista estados vale só no nível estados: nos municípios, os estados inteiros vão em "
                         "base.estados.")
    indicador = options.get("indicador")
    if indicador not in INDICATORS:
        raise ValueError("Escolha o indicador do gráfico: \"densidade\" ou \"quantidade\".")
    if indicador == "densidade" and not ctx.density:
        raise ValueError(_no_population(ctx))
    ctx.nivel, ctx.indicador = nivel, indicador
    spec = {"nivel": nivel, "indicador": indicador, "tendencia": _window(ctx, options.get("tendencia")),
            "serie": _series_window(ctx, options.get("serie")),
            "grupos": _group_type(options.get("grupos")),
            "grupos_mapa": _group_type(options.get("grupos_mapa"), "grupos_mapa"),
            "faixas": _limits(options.get("faixas"), "faixas"),
            "faixas_distancia": _limits(options.get("faixas_distancia"), "faixas_distancia"),
            "condicoes": _conditions_spec(ctx, options.get("condicoes")), "ordenar": _order_spec(ctx, options.get("ordenar")),
            "comparar": _compare_spec(options.get("comparar")),
            "rotatividade": _rotation_spec(ctx, options.get("rotatividade"))}
    return spec


def _window(ctx, raw):
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {"competencias"}:
        raise ValueError("Tendência inválida: use {\"competencias\": [...]}, a janela escolhida.")
    values = raw["competencias"]
    if (not isinstance(values, list) or not 2 <= len(values) <= MAX_WINDOW or len(set(values)) != len(values) or
            any(not isinstance(value, str) for value in values)):
        raise ValueError("Janela da tendência inválida: envie de 2 a " + str(MAX_WINDOW) + " competências distintas em "
                         "tendencia.competencias.")
    unknown = [value for value in values if value not in ctx.periods]
    if unknown:
        raise ValueError("Competência inexistente na janela da tendência: " + ", ".join(str(v)[:16] for v in unknown[:5]) +
                         ".")
    _temporal_premises(ctx)
    return sorted(values, key=ctx.positions.get)


def _series_window(ctx, raw):
    """Intervalo da série temporal (24/10/2026): de 2 a MAX_SERIE competências distintas da base, em ordem cronológica,
    com as mesmas premissas temporais da mudança e da tendência (os valores de competências diferentes lado a lado)."""
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {"competencias"}:
        raise ValueError("Série temporal inválida: use {\"competencias\": [...]}, as competências do intervalo.")
    values = raw["competencias"]
    if (not isinstance(values, list) or not 2 <= len(values) <= MAX_SERIE or len(set(values)) != len(values) or
            any(not isinstance(value, str) for value in values)):
        raise ValueError("Intervalo da série temporal inválido: envie de 2 a " + str(MAX_SERIE) + " competências distintas "
                         "em serie.competencias.")
    unknown = [value for value in values if value not in ctx.periods]
    if unknown:
        raise ValueError("Competência inexistente na série temporal: " + ", ".join(str(v)[:16] for v in unknown[:5]) + ".")
    _temporal_premises(ctx)
    return sorted(values, key=ctx.positions.get)


def _group_type(raw, chave="grupos"):
    """Número de grupos por posição (CAP-DIS-02) pedido em `grupos` ou em `grupos_mapa` (os grupos que pintam o mapa),
    com a mesma validação; a mensagem de `grupos_mapa` diz o nome da chave."""
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {"tipo"} or raw["tipo"] not in GROUP_TYPES:
        raise ValueError("Grupos por posição inválidos" + ("" if chave == "grupos" else " (" + chave + ")") +
                         ": use {\"tipo\": \"quartis\", \"quintis\" ou \"decis\"}.")
    return GROUP_TYPES[raw["tipo"]]


def _limits(raw, key):
    if raw is None:
        return None
    if not isinstance(raw, list):
        raise ValueError("Faixas inválidas (" + key + "): envie a lista crescente dos limites, como [0, 1, 2, 5].")
    return band_edges(raw)


def _conditions_spec(ctx, raw):
    """CAP-SUB-01: condições estruturadas (atributo, operador, valor) combinadas por E, pela árvore dos critérios
    combinados (combined_criteria.parse_tree), com os mesmos operadores, valores e mensagens."""
    if raw is None:
        return None
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_CONDITIONS:
        raise ValueError("Condições inválidas: envie de 1 a " + str(MAX_CONDITIONS) + " condições {\"atributo\", "
                         "\"operador\", \"valor\"}.")
    leaves, definition = [], []
    for i, item in enumerate(raw, start=1):
        if not isinstance(item, dict) or set(item) != {"atributo", "operador", "valor"}:
            raise ValueError("Condição inválida: use {\"atributo\", \"operador\", \"valor\"}.")
        attribute = CONDITION_ATTRIBUTES.get(item["atributo"]) if isinstance(item["atributo"], str) else None
        if attribute is None:
            raise ValueError("Atributo da condição não reconhecido: use densidade, quantidade, populacao ou distancia_km.")
        if attribute in ("densidade", "populacao") and not ctx.density:
            raise ValueError(_no_population(ctx))
        leaves.append({"id": "c" + str(i), "attribute": attribute, "operator": item["operador"], "value": item["valor"]})
        definition.append({"atributo": item["atributo"], "operador": item["operador"], "valor": item["valor"]})
    tree = leaves[0] if len(leaves) == 1 else {"id": "e", "logic": "and", "operands": leaves}
    nodes, order, root = parse_tree(tree, {"count_unit": ctx.settings.get("count_unit")})
    for entry, own in zip(definition, order):
        entry["texto"] = nodes[own]["condicao"]
    return {"nodes": nodes, "leaves": order, "root": root, "definicao": definition}


def _order_spec(ctx, raw):
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) - {"atributo", "ordem", "primeiros"} or not {"atributo", "ordem"} <= set(raw):
        raise ValueError("Ordenação inválida: use {\"atributo\", \"ordem\", \"primeiros\"}.")
    attribute, order, first = raw["atributo"], raw["ordem"], raw.get("primeiros")
    if not isinstance(attribute, str) or attribute not in ORDER_ATTRIBUTES:
        raise ValueError("Atributo da ordenação não reconhecido: use densidade, quantidade, populacao, distancia_km ou "
                         "variacao.")
    if order not in ORDERS:
        raise ValueError("Ordem inválida: use desc (maior para menor) ou asc (menor para maior).")
    if attribute in ("densidade", "populacao") and not ctx.density:
        raise ValueError(_no_population(ctx))
    if first is not None and (isinstance(first, bool) or not isinstance(first, int) or not 1 <= first <= MAX_IDS):
        raise ValueError("N primeiros inválido: use um inteiro entre 1 e " + thousands(MAX_IDS) + ".")
    return {"atributo": attribute, "ordem": order, "primeiros": first}


def _compare_spec(raw):
    if raw is None:
        return None
    if (not isinstance(raw, list) or not 2 <= len(raw) <= 3 or len(set(raw)) != len(raw) or
            any(not isinstance(value, str) or not value for value in raw)):
        raise ValueError("Comparação inválida: escolha de 2 a 3 itens distintos do gráfico (ids).")
    return list(raw)


def _rotation_spec(ctx, raw):
    if raw is None:
        return None
    if ctx.brazil:
        raise ValueError(ROTATION + " Envie uma planilha com identificador individual para a rotatividade.")
    if not isinstance(raw, dict) or set(raw) != {"inicial", "final"}:
        raise ValueError("Rotatividade inválida: use {\"inicial\", \"final\"}, duas competências da planilha.")
    for key in ("inicial", "final"):
        if raw[key] not in ctx.periods:
            raise ValueError("Competência inexistente na rotatividade (" + key + "): " + str(raw[key])[:16] + ".")
    return raw["inicial"], raw["final"]


def _page_requirements(ctx, spec, reference, initial_period):
    """Combinações que dependem de outras escolhas do pedido."""
    if spec["faixas_distancia"] is not None and reference is None:
        raise ValueError("As faixas de distância (CAP-ESP-03) exigem a referência: escolha a análise espacial.")
    if spec["ordenar"] and spec["ordenar"]["atributo"] == "distancia_km" and reference is None:
        raise ValueError("A ordenação pela distância exige a referência: escolha a análise espacial.")
    if spec["ordenar"] and spec["ordenar"]["atributo"] == "variacao" and initial_period is None:
        raise ValueError("A ordenação pela variação exige a competência inicial (visão Trajetória).")
    if spec["condicoes"] and reference is None and any(
            spec["condicoes"]["nodes"][own]["atributo"] == "distancia" for own in spec["condicoes"]["leaves"]):
        raise ValueError("A condição de distância exige a referência: escolha a análise espacial.")


# --------------------------------------------------------------------------------------------- página única: cálculos
def _names(ctx, keys):
    out = {}
    for key in keys:
        if key.startswith("uf:"):
            out[key] = {"name": STATES[key[3:]][1]}
        else:
            out[key] = {"name": ctx.catalog[key]["name"]}
    return out


def _record_values(final, attribute, keys):
    """Densidade, quantidade ou população por item, no formato dos critérios combinados, lidas das medidas da
    competência (sem registro ou sem o valor: não avaliável, com o motivo)."""
    out = {}
    for key in keys:
        record = final.records.get(key)
        if record is None:
            out[key] = {"avaliavel": False, "motivos": ["SEM_REGISTRO_OBSERVADO"]}
        elif not _present(record["valores"][attribute]):
            out[key] = {"avaliavel": False,
                        "motivos": ["DENOMINADOR_AUSENTE" if attribute in ("densidade", "populacao") else "DADO_AUSENTE"]}
        else:
            out[key] = {"avaliavel": True, "valor": record["valores"][attribute], "exato": _exact(record, attribute)}
    return out


def _values(ctx, res, attribute, keys):
    """Valores por item no formato dos critérios combinados ({avaliavel, valor, exato, motivos}), lidos das medidas já
    calculadas pelo motor: densidade, quantidade, população, distância até a referência (com os membros mais próximos)
    e variação percentual do indicador."""
    if attribute not in ("distancia", "variacao"):
        return _record_values(res.final, attribute, keys)
    out = {}
    field_of = INDICATORS_FIELD.get(ctx.indicador)
    by_item = {item["id"]: item for item in res.items} if attribute == "variacao" else {}
    for key in keys:
        if attribute == "distancia":
            spatial = res.spatial
            value = spatial.values.get(key) if spatial is not None else None
            if value is None:
                state = spatial.condition(key) if spatial is not None else "SEM_REGISTRO"
                motive = MOTIVES.get(state, "DEPENDENCIA_NAO_AVALIAVEL") if state != "VALIDA" else "DEPENDENCIA_NAO_AVALIAVEL"
                out[key] = {"avaliavel": False, "motivos": [motive]}
            else:
                out[key] = {"avaliavel": True, "valor": value, "exato": Fraction(value),
                            "referencias": list(spatial.nearest.get(key) or []), "alcance": SCOPE_FULL}
            continue
        if attribute == "variacao":
            percent = (res.changes.get(key) or {}).get(field_of)
            exact = None if percent is None else Fraction(*percent)
            if exact is None:
                start = by_item[key]["inicial"].get(field_of) if key in by_item else None
                motive = ("SEM_REGISTRO_OBSERVADO" if key not in res.changes else
                          "BASE_ZERO" if start == 0 else "DADO_AUSENTE")
                out[key] = {"avaliavel": False, "motivos": [motive]}
            else:
                out[key] = {"avaliavel": True, "valor": float(exact), "exato": exact}
    return out


INDICATORS_FIELD = {"densidade": "densidade", "quantidade": "quantidade"}


class _Evaluator:
    """Fornece aos critérios combinados (combined_criteria.evaluate) os valores já calculados pelo painel."""

    def __init__(self, table):
        self.table = table

    def category(self, requested):
        return None

    def values(self, attribute, category=None):
        return self.table[attribute]


def _apply(res, by_id, field_name, out, notas=True):
    """Leva aos itens o que uma análise calculou (_reaproveitar): o campo de cada item do universo (null nos demais
    itens), as notas e as limitações, na mesma ordem do cálculo; devolve o bloco do topo. Com `notas` falso (os grupos
    do mapa), só o campo e o bloco: as notas e as limitações da resposta ficam como estão."""
    for item in res.items:
        item[field_name] = None
    for key, value in out["itens"].items():
        by_id[key][field_name] = value
    if notas:
        res.notes += out["notas"]
        res.limitations += out["limitacoes"]
    return out["topo"]


def _reference_members(res):
    """A referência na chave da memória: os membros escolhidos ou, por elegibilidade, a definição inteira (duas
    definições diferentes nunca dividem distâncias, condições, ordem ou faixas)."""
    if res.reference is None:
        return None
    if res.reference.get("modo") == "elegiveis":
        return _eligible_normalized(res.reference)
    return list(res.reference["membros"])


def _conditions(ctx, res, spec, by_id):
    nodes, leaves, root, definition = spec["nodes"], spec["leaves"], spec["root"], spec["definicao"]

    def calcular():
        attributes = {nodes[own]["atributo"] for own in leaves}
        table = {attribute: _values(ctx, res, attribute, res.universe) for attribute in attributes}
        inputs = {"nodes": nodes, "root": root, "leaves": leaves, "targets": list(res.universe), "catalog": {}}
        evaluations = evaluate(None, None, None, inputs, _Evaluator(table))
        counts = dict.fromkeys(("ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"), 0)
        per_item = {}
        for record in evaluations:
            counts[record["estado"]] += 1
            # Uma entrada por condição, na ordem de condicoes.definicao: estado, valor do item e motivos (sem repetir a
            # definição em cada item).
            detail = [{"estado": record["nos"][own]["estado"], "valor": _num(record["nos"][own].get("valor")),
                       "motivos": list(record["nos"][own].get("motivos") or [])} for own in leaves]
            per_item[record["elemento"]] = {"situacao": record["estado"], "por_condicao": detail}
        text = describe(nodes, root)
        notes = ["Condições definidas pelo usuário (CAP-SUB-01, combinação E): " + text + ". Os valores são escolhas do "
                 "usuário e não constituem critério legal, sanitário ou científico universal.",
                 "Três estados por item e por condição: NAO_AVALIAVEL nunca é tratado como NAO_ATENDE; o resultado não "
                 "depende da ordem das condições."]
        top = {"contagens": counts, "universo": len(res.universe), "combinacao": "E", "descricao": text,
               "definicao": [{key: entry[key] for key in ("atributo", "operador", "valor", "texto")}
                             for entry in definition]}
        return {"topo": top, "itens": per_item, "notas": notes,
                "limitacoes": ["UNIDADES_NAO_AVALIAVEIS"] if counts["NAO_AVALIAVEL"] else []}

    entradas = {"universo": _ids_key(res.universe), "referencia": _reference_members(res),
                "condicoes": [[entry["atributo"], entry["operador"], entry["valor"]] for entry in definition]}
    return _apply(res, by_id, "condicoes", _reaproveitar(ctx, "condicoes", entradas, calcular))


def _ordering(ctx, res, spec, by_id):
    attribute = ORDER_ATTRIBUTES[spec["atributo"]]

    def calcular():
        values = _values(ctx, res, attribute, res.universe)
        ordered, positions, not_evaluable = _ranked(values, list(res.universe), _names(ctx, res.universe), spec["ordem"])
        top, tied = None, False
        if spec["primeiros"] is not None:
            top, _ = select_top(ordered, positions, spec["primeiros"], False)
            tied = len(top) > spec["primeiros"]
        chosen = set(top or [])
        per_item = {key: {"posicao": positions.get(key), "selecionado": None if top is None else key in chosen}
                    for key in res.universe}
        notes = ["Ordenação por " + VALUE_TEXT[attribute] + (" (" + ctx.indicador + ")" if attribute == "variacao"
                                                             else "") +
                 " (" + ORDERS[spec["ordem"]] + "; CAP-SUB-02): valores iguais compartilham posição (1, 2, 2, 4) e não "
                 "avaliáveis ficam fora da ordenação."]
        if tied:
            notes.append("Seleção dos " + str(spec["primeiros"]) + " primeiros com empate no corte (CAP-SUB-03): " +
                         str(len(top)) + " itens selecionados (EMPATE_NO_CORTE).")
        topo = {"atributo": spec["atributo"], "ordem": spec["ordem"], "primeiros": spec["primeiros"],
                "universo": len(res.universe), "ordenados": len(ordered), "nao_avaliaveis": len(not_evaluable),
                "selecionados": None if top is None else len(top), "empates_no_corte": tied,
                "ids_selecionados": None if top is None else list(top)}
        return {"topo": topo, "itens": per_item, "notas": notes, "limitacoes": ["EMPATE_NO_CORTE"] if tied else []}

    entradas = {"universo": _ids_key(res.universe), "ordenar": [spec["atributo"], spec["ordem"], spec["primeiros"]],
                "indicador": ctx.indicador, "referencia": _reference_members(res),
                "competencia_inicial": res.initial.period if res.initial is not None else None}
    return _apply(res, by_id, "ordem", _reaproveitar(ctx, "ordenacao", entradas, calcular))


def _bands(ctx, res, limits, attribute, key_name, capability, by_id):
    def calcular():
        values = _values(ctx, res, attribute, res.universe)
        labels, membership, counts, outside, not_evaluable = bands_of(values, list(res.universe), limits)
        outside, missing = set(outside), set(not_evaluable)
        per_item = {}
        for key in res.universe:
            if key in membership:  # índice ordinal (1 = primeira faixa), como nos grupos por posição
                per_item[key] = {"indice": membership[key] + 1, "rotulo": labels[membership[key]]}
            elif key in outside:
                per_item[key] = "fora"
        notes = ["Faixas (" + capability + ") de " + VALUE_TEXT[attribute] + " com limites escolhidos pelo usuário: "
                 "intervalos [a, b) e o último fechado; nenhum limite é criado pelo sistema."]
        topo = {"atributo": "distancia_km" if attribute == "distancia" else attribute, "capacidade": capability,
                "limites": [format(value, "f") for value in limits], "convencao": BAND_CONVENTION, "rotulos": labels,
                "contagens": counts, "fora": len(outside), "nao_avaliaveis": len(missing), "universo": len(res.universe)}
        return {"topo": topo, "itens": per_item, "notas": notes, "limitacoes": []}

    entradas = {"universo": _ids_key(res.universe), "atributo": attribute,
                "limites": [format(value, "f") for value in limits],
                "referencia": _reference_members(res) if attribute == "distancia" else None}
    return _apply(res, by_id, key_name, _reaproveitar(ctx, key_name, entradas, calcular))


def _rows_frame(ctx, res, keys):
    """Quadro do motor (territory, period, category, quantity, population, density) dos itens pedidos, com rótulos
    únicos; devolve também o id de cada rótulo."""
    rows, key_of, seen = [], {}, set()
    by_id = {item["id"]: item for item in res.items}
    for key in keys:
        item = by_id[key]
        name = item["rotulo"]
        if item["tipo"] == "conjunto" or name in seen:
            name = name + " [" + key + "]"
        seen.add(name)
        key_of[name] = key
        rows.append({"territory": name, "period": ctx.period, "category": ctx.category,
                     "quantity": item["quantidade"], "population": item["populacao"], "density": item["densidade"]})
    frame = pd.DataFrame(rows, columns=EMPTY)
    for column in ("quantity", "population", "density"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype(float)
    return frame, key_of


def _groups(ctx, res, k, by_id, campo="grupo"):
    """CAP-DIS-02 pelo motor da distribuição (main._compute, operação distribution) entre os itens do universo com valor
    do indicador; os pontos de corte são os mesmos de main.distribution_cuts (Hyndman–Fan tipo 7).

    `campo` é o campo por item: "grupo" (options.grupos) ou "grupo_mapa" (options.grupos_mapa, os grupos que pintam o
    mapa, 23/10/2026). Os dois são o mesmo cálculo, com as mesmas regras de empate e de não avaliáveis, e leem a mesma
    memória (_reaproveitar(ctx, "grupos", ...)): com as mesmas entradas, um vem do outro, sem recalcular. Os do mapa não
    acrescentam notas nem limitações (o gráfico, a frase-resumo, a tabela e o CSV não mudam com eles) e, com menos de
    duas unidades com valor, ficam nulos em vez de recusar o pedido: a tela os pede junto com toda análise."""
    import main as engine  # importação tardia: main usa este módulo
    unit = ctx.labels.unidade if ctx.nivel == "municipios" else ctx.labels.grupo
    metric = INDICATORS[ctx.indicador]
    evaluable = [key for key in res.universe if by_id[key][ctx.indicador] is not None]
    mapa = campo == "grupo_mapa"
    if len(evaluable) < 2:
        if mapa:
            for item in res.items:
                item[campo] = None
            return None
        raise ValueError("Os grupos por posição (CAP-DIS-02) exigem pelo menos " + unit.g("dois", "duas") + " " +
                         unit.plural + " com " + ctx.indicador + " em " + human_period(ctx.period) + ".")

    def calcular():
        data, key_of = _rows_frame(ctx, res, evaluable)
        options = {**ctx.settings, "distribution_indicator": metric, "quantile_count": k}
        computed = engine._compute(res.engine_rows, ctx.mapping, "distribution", options, prepared=data)
        labels = [str(i) + "º " + GROUP_NAMES[k] for i in range(1, k + 1)]
        index_of = {label: i for i, label in enumerate(labels, start=1)}
        per_item = {key_of[row["Território"]]: {"indice": index_of[row["Quintil"]], "rotulo": row["Quintil"]}
                    for row in computed["detail_rows"]}
        notes = [note for note in computed["notes"] if note.startswith(("Distribuição com pontos", "Posições crescentes"))]
        notes.append("Grupos por posição (CAP-DIS-02) entre " + unit.g("os", "as") + " " + unit.n(len(evaluable)) +
                     " do universo com " + ctx.indicador + " em " + human_period(ctx.period) + "; os não avaliáveis ficam "
                     "fora dos grupos, e as classes não têm caráter normativo.")
        topo = {"tipo": {4: "quartis", 5: "quintis", 10: "decis"}[k], "k": k, "atributo": ctx.indicador,
                "cortes": [_num(value) for value in engine.distribution_cuts(data[metric], k)], "rotulos": labels,
                "contagens": [int(row["Unidades"]) for row in computed["rows"]], "universo": len(res.universe),
                "classificados": len(evaluable), "nao_avaliaveis": len(res.universe) - len(evaluable)}
        return {"topo": topo, "itens": per_item, "notas": notes, "limitacoes": []}

    entradas = {"universo": _ids_key(res.universe), "indicador": ctx.indicador, "k": k}
    return _apply(res, by_id, campo, _reaproveitar(ctx, "grupos", entradas, calcular), notas=not mapa)


def _comparison(ctx, res, ids, by_id):
    """CAP-CMP-01 pelo motor (main._compute, operação comparisons) sobre os 2 ou 3 itens com valor do indicador: maior,
    menor e, entre dois itens, a relação e a diferença assinada A − B; entre três, a ordem (próximo valor maior), sem
    diferenças automáticas entre pares (AT-84)."""
    import main as engine  # importação tardia: main usa este módulo
    unknown = [value for value in ids if value not in by_id]
    if unknown:
        raise ValueError("Itens da comparação fora do gráfico: " + ", ".join(unknown[:3]) + ".")
    sets = {value: set(by_id[value]["membros"]) for value in ids if by_id[value]["tipo"] == "conjunto"}
    for value in ids:
        for other, members in sets.items():
            if other != value and (value in members or (value in sets and sets[value] & members)):
                raise ValueError("Itens relacionados não são comparados: " + by_id[other]["rotulo"] + " tem membros em "
                                 "comum com " + by_id[value]["rotulo"] + ". Escolha itens sem membros em comum.")
    metric = INDICATORS[ctx.indicador]
    field_name = ctx.indicador
    evaluable = [value for value in ids if by_id[value][field_name] is not None]
    itens = [{"id": value, "rotulo": by_id[value]["rotulo"], "tipo": by_id[value]["tipo"],
              "valor": by_id[value][field_name], "avaliavel": by_id[value][field_name] is not None,
              "motivos": list(by_id[value]["motivos"])} for value in ids]
    out = {"indicador": ctx.indicador, "itens": itens, "maior": [], "menor": [], "diferencas": [], "relacoes": [],
           "notas": []}
    if len(evaluable) < 2:
        out["notas"].append("Comparação não avaliável: menos de dois itens com " + field_name + " em " +
                            human_period(ctx.period) + ".")
        return out
    data, key_of = _rows_frame(ctx, res, evaluable)
    options = {**ctx.settings, "comparison_indicator": metric}
    computed = engine._compute(res.engine_rows, ctx.mapping, "comparisons", options, prepared=data)
    rows = computed["rows"]
    if len(evaluable) == 2:
        [row] = rows
        a, b = key_of[row["Objeto A"]], key_of[row["Objeto B"]]
        relation = row["Relação A/B"]
        out["maior"] = [a] if relation == "MAIOR" else [b] if relation == "MENOR" else [a, b]
        out["menor"] = [b] if relation == "MAIOR" else [a] if relation == "MENOR" else [a, b]
        out["diferencas"] = [{"a": a, "b": b, "relacao": relation, "diferenca": _num(row["Diferença A − B"])}]
    else:
        label = "Densidade por 1.000" if metric == "density" else "Quantidade"
        lowest = min(row[label] for row in rows)
        for row in rows:
            key = key_of[row["Território"]]
            out["relacoes"].append({"id": key, "valor": _num(row[label]),
                                    "proximo_valor_maior": _num(row["Próximo valor maior"]),
                                    "mesmo_valor": int(row["Unidades com mesmo valor"])})
            if row["Próximo valor maior"] is None:
                out["maior"].append(key)
            if row[label] == lowest:
                out["menor"].append(key)
    # A nota da forma usada (par ou conjunto de três), entre as notas do motor.
    other = NOTE_SET if len(evaluable) == 2 else NOTE_PAIRS
    out["notas"] = [note for note in computed["notes"] if note != other]
    return out


def _rotation(ctx, res, spec, by_id):
    """CAP-ROT-01 pelo motor (main._compute, operação rotation): coorte inicial de pessoas distintas pelo identificador
    individual, permanência e saída no período final; os identificadores nunca são devolvidos."""
    import main as engine  # importação tardia: main usa este módulo
    if not ctx.mapping.get("identity"):
        raise ValueError("A rotatividade (CAP-ROT-01) exige um identificador individual da mesma pessoa entre os "
                         "períodos; associe essa coluna na planilha.")
    if not role_established(ctx.frame, ctx.mapping, ctx.settings, "identity"):
        raise Pendencia("Escolha a coluna de " + ROLE_NAMES["identity"] + " no seletor: a coluna indicada não foi "
                        "reconhecida nem escolhida.", "confirmed_roles", ["identity"])
    for key in ("longitudinal_identity_confirmed", "territory_longitudinal_confirmed"):
        if not ctx.settings.get(key):
            raise ChoiceRequired(premise_reason(ctx.settings, key))
    first, last = spec
    options = {**ctx.settings, "initial_period": first, "final_period": last,
               **({"category_filter": ctx.category} if ctx.mapping.get("category") else {})}
    computed = engine._compute(ctx.frame, ctx.mapping, "rotation", options)
    rows = [row for row in computed["rows"] if not ctx.mapping.get("category") or row["Categoria"] == ctx.category]
    keys = _data_keys(ctx, pd.Series([row["Território"] for row in rows], dtype=object)).tolist() if rows else []
    found = dict(zip(keys, rows))
    evaluable = 0
    for item in res.items:
        if item["tipo"] != "municipio":
            item["rotatividade"] = None
            continue
        row = found.get(item["id"])
        if row is None:
            item["rotatividade"] = {"inicial": first, "final": last, "coorte_inicial": None, "permanencia": None,
                                    "saida": None, "permanencia_percentual": None, "saida_percentual": None,
                                    "avaliavel": False, "motivo": "Sem registro em " + human_period(first) + " nem em " +
                                    human_period(last) + " (SEM_REGISTRO_OBSERVADO)"}
            continue
        ok = row["Condição"] == "Avaliável"
        evaluable += item["id"] in res.universe and ok
        item["rotatividade"] = {"inicial": row["Período inicial"], "final": row["Período final"],
                                "coorte_inicial": _num(row["Coorte inicial"]), "permanencia": _num(row["Permanecem"]),
                                "saida": _num(row["Saíram"]), "permanencia_percentual": _num(row["Permanência (%)"]),
                                "saida_percentual": _num(row["Rotatividade (%)"]), "avaliavel": ok,
                                "motivo": None if ok else row["Condição"]}
    res.notes += list(computed["notes"]) + premise_notes(ctx.settings, "rotation", ctx.mapping)
    res.frames.append(ctx.frame)
    return {"inicial": first, "final": last, "universo": len(res.universe), "avaliaveis": int(evaluable),
            "nao_avaliaveis": len(res.universe) - int(evaluable)}


SERIES_COLUMNS = ["territory", "period", "category", "quantity", "population", "density"]


def _trend_series(frame, metric, positions, incomparability=None) -> dict:
    """trend.classify_frame (a função da evolução temporal) sobre o quadro (territory = id do item): por item, a
    tendência, as velocidades exatas entregues em float e os valores observados do indicador na janela. Observação sem
    valor (densidade sem população) fica ausente, nunca zero."""
    value_cols = ("quantity", "population") if metric == "density" else ("quantity",)
    usable, observed = _observed_values(frame, metric)
    num = _num
    return {key[0]: (trend, [num(speed) for speed in trend.speeds()], observed.get(key[0], {}))
            for key, trend in classify_frame(usable, value_cols=value_cols, positions=positions,
                                             incomparability=incomparability)}


def _observed_values(frame, metric):
    """As linhas com valor do indicador (quantidade; na densidade, também a população) e o valor observado de cada item
    em cada competência. Competência sem valor fica de fora, nunca zero."""
    usable = frame[frame["quantity"].notna()]
    if metric == "density":
        usable = usable[usable["population"].notna()]
    observed = {}
    num = _num
    for key, period, value in zip(usable["territory"].tolist(), usable["period"].tolist(), usable[metric].tolist()):
        observed.setdefault(key, {})[str(period)] = num(value)
    return usable, observed


@per_source()
def _unit_series(frame, mapping, settings, window, category, operation, metric, positions, keys):
    """CAP-TEN-01 dos municípios (ou das unidades da planilha) na janela: data_contract.prepare numa só passagem pelas
    linhas da janela e dos itens pedidos (`keys`; None = todos), como o recorte territorial da evolução temporal, e
    _trend_series. Na base Brasil verificada, guardado por versão, janela e itens (request_memo.per_source). Devolve também
    o resumo das linhas usadas, para a chave de execução."""
    rows = _rows(frame, mapping, window, category)
    if keys is not None:
        wanted = set(keys)
        rows = rows.loc[row_ids(rows, mapping).isin(wanted).to_numpy(dtype=bool)]
    digest = hashlib.sha256(pd.util.hash_pandas_object(rows, index=True).values.tobytes()).hexdigest()
    if rows.empty:
        return {}, digest
    data = prepare(rows, mapping, settings, operation)
    codes = data["territory"].str.extract(r"\[([^\[\]]+)\]$", expand=False)
    data = data.assign(territory=("code:" + codes) if mapping.get("territory_id") else ("name:" + data["territory"]))
    return _trend_series(data[SERIES_COLUMNS], metric, positions), digest


def _set_series(ctx, res, window):
    """Conjuntos na janela: a agregação municipal (main._compute, operação aggregate) em cada competência, sobre os
    membros com registro; com membros diferentes entre as competências, a tendência não é avaliável
    (INCOMPARABILIDADE pela entrada, CAP-AGR-01 e F-05b). Devolve também as linhas usadas, para a chave de execução."""
    import main as engine  # importação tardia: main usa este módulo
    mapping = ctx.mapping
    members = {key for spec in res.sets for key in spec["membros"]}
    rows = _rows(ctx.frame, mapping, window, ctx.category)
    rows = rows.loc[row_ids(rows, mapping).isin(members).to_numpy(dtype=bool)]
    if rows.empty:
        return pd.DataFrame(columns=SERIES_COLUMNS), {}, rows
    data = prepare(rows, mapping, ctx.settings, "density" if ctx.density else "counts").copy()
    data["key"] = _data_keys(ctx, data["territory"])
    periods = text_values(rows[mapping["period"]])
    out, incomparability = [], {}
    for spec in res.sets:
        support, values = {}, []
        for period in window:
            present = data[(data["period"] == period) & data["key"].isin(spec["membros"])]
            if present.empty:
                continue
            support[period] = sorted(present["key"])
            row = engine._compute(rows.loc[(periods == period).to_numpy(dtype=bool)], mapping, "aggregate", ctx.settings,
                                  prepared=present[EMPTY].reset_index(drop=True))["rows"][0]
            values.append({"territory": spec["id"], "period": period, "category": ctx.category,
                           "quantity": row["Quantidade"], "population": row["População"],
                           "density": row["Densidade por 1.000"]})
        if len({tuple(keys) for keys in support.values()}) > 1:
            incomparability[(spec["id"], ctx.category)] = (
                "os membros com registro mudam na janela (" + ", ".join(
                    human_period(period) + ": " + str(len(keys)) for period, keys in support.items()) + ")")
        out += values
    return pd.DataFrame(out, columns=SERIES_COLUMNS), incomparability, rows


def _state_series(ctx, res, window):
    """Estados na janela pela abrangência da base Brasil (territorial_levels.state_part): contagem estadual e, na
    densidade, a população do estado em cada competência (lacuna quando incompleta). Devolve também o quadro da fonte
    estadual, para a chave de execução."""
    estados = tuple(key[3:] for key in res.universe)
    data = state_part(ctx.sources, {"period_filters": list(window), "category_filter": ctx.category}, True,
                      Abrangencia(False, estados, False, (), ()), ctx.index, Parts())
    if data.empty:
        return pd.DataFrame(columns=SERIES_COLUMNS), data
    return data.assign(territory="uf:" + data["uf"].astype(str))[SERIES_COLUMNS], data


def _trend_block(ctx, res, window):
    """O cálculo de _trend: a tendência de cada item, o resumo do motor no universo, o domínio das observações, as notas e
    o que entra na chave de execução (quadros e resumos das linhas usadas)."""
    positions = {period: ctx.positions[period] for period in window}
    convention = resolve_convention(list(ctx.periods))
    metric = INDICATORS[ctx.indicador]
    frames, digests = [], []
    if ctx.nivel == "estados":
        frame, data = _state_series(ctx, res, window)
        frames.append(data)
        series = _trend_series(frame, metric, positions)
    elif ctx.nivel == "brasil":
        frame = _brazil_series(ctx, window)
        frames.append(frame)
        series = _trend_series(frame, metric, positions)
    else:
        units = [item["id"] for item in res.items if item["tipo"] == "municipio"]
        keys = None if len(units) == len(ctx.catalog) else sorted(units)
        series, digest = _unit_series(ctx.frame, ctx.mapping, ctx.settings, list(window), ctx.category,
                                      "density" if ctx.density else "counts", metric, positions, keys)
        digests.append(digest)
        if res.sets:
            frame, incomparability, rows = _set_series(ctx, res, window)
            frames.append(rows)
            series = {**series, **_trend_series(frame, metric, positions, incomparability)}
    empty = classify([])
    values, per_item = [], {}
    for item in res.items:
        trend, speeds, observed = series.get(item["id"], (empty, [], {}))
        points = [{"competencia": period, "valor": observed.get(period)} for period in trend.periods]
        values += [point["valor"] for point in points if point["valor"] is not None]
        per_item[item["id"]] = {"classe": trend.category, "familia": trend.family, "rotulo": trend.label,
                                "motivo": trend.motive or trend.not_evaluable, "motivo_texto": trend.motive_label,
                                "avaliavel": trend.evaluability == "AVALIAVEL", "observacoes": points,
                                "velocidades": speeds}
    trends = {key: value[0] for key, value in series.items()}
    block = stage_block(len(window))
    summary = summarize([trends.get(key, empty) for key in res.universe], block=block)
    summary.update({"indicador": ctx.indicador, "unidade_valor": "por 1.000 habitantes" if metric == "density" else
                    count_unit_label(ctx.mapping, ctx.settings), "unidade_tempo": time_unit(convention),
                    "janela": series_window(list(window), positions, convention), "universo": len(res.universe)})
    notes = evolution_notes(summary, {"percentual_nao_avaliavel": {"BASE_ZERO": 0}}, convention)
    notes.append("Classes de tendência (CAP-TEN-01) na janela de " + human_period(window[0]) + " a " +
                 human_period(window[-1]) + " (" + str(len(window)) + " competências): a cor da bolha segue a família "
                 "da classe (crescimento, declínio ou sem classificação); não avaliável fica à parte, com o motivo.")
    notes += premise_notes(ctx.settings, "temporal", ctx.mapping)
    return {"topo": summary, "itens": per_item, "dominio": [min(values), max(values)] if values else None,
            "notas": notes, "quadros": frames, "resumos": digests}


def _trend(ctx, res, window, by_id):
    """CAP-TEN-01 por item na janela escolhida (trend.classify_frame, como na evolução temporal) e as contagens do motor
    por classe no universo (trend.summarize), com o bloqueio de menos de quatro competências (stage_block). No nível
    municípios, reaproveitada entre pedidos enquanto a janela, o indicador, os itens e o universo não mudam
    (_reaproveitar)."""
    if ctx.nivel in ("estados", "brasil"):
        out = _trend_block(ctx, res, window)
    else:
        entradas = {"janela": list(window), "indicador": ctx.indicador, "itens": _ids_key(item["id"] for item in res.items),
                    "conjuntos": [[spec["id"], list(spec["membros"])] for spec in res.sets],
                    "universo": _ids_key(res.universe)}
        out = _reaproveitar(ctx, "tendencia", entradas, lambda: _trend_block(ctx, res, window))
    for item in res.items:
        item["tendencia"] = out["itens"][item["id"]]
    res.frames += out["quadros"]
    res.digests += out["resumos"]
    res.notes += out["notas"]
    res.methods["tendencia"] = TREND_METHOD
    return out["topo"], out["dominio"]


@per_source()
def _unit_observed(frame, mapping, settings, window, category, operation, metric, keys):
    """Os valores observados dos municípios (ou das unidades da planilha) em cada competência do intervalo, pela mesma
    preparação da tendência (data_contract.prepare numa só passagem pelas linhas do intervalo e dos itens pedidos), sem
    classificar nada. Na base Brasil verificada, guardado por versão, intervalo e itens (request_memo.per_source). Devolve
    também o resumo das linhas usadas, para a chave de execução."""
    rows = _rows(frame, mapping, window, category)
    if keys is not None:
        wanted = set(keys)
        rows = rows.loc[row_ids(rows, mapping).isin(wanted).to_numpy(dtype=bool)]
    digest = hashlib.sha256(pd.util.hash_pandas_object(rows, index=True).values.tobytes()).hexdigest()
    if rows.empty:
        return {}, digest
    data = prepare(rows, mapping, settings, operation)
    codes = data["territory"].str.extract(r"\[([^\[\]]+)\]$", expand=False)
    data = data.assign(territory=("code:" + codes) if mapping.get("territory_id") else ("name:" + data["territory"]))
    return _observed_values(data[SERIES_COLUMNS], metric)[1], digest


def _series(ctx, res, window, by_id):
    """Série temporal (24/10/2026, pedido do responsável): o valor observado do indicador de cada item em cada
    competência do intervalo escolhido (a extensão inteira da base ou parte dela), pelas mesmas funções da tendência
    (municípios, conjuntos, estados e o Brasil), sem classificação (CAP-TEN-01 não é chamada), sem linha ajustada e sem
    preencher lacunas: competência sem valor fica null. Conjunto com membros diferentes no intervalo fica com
    `comparavel` falso e o motivo (CAP-AGR-01, F-05b): os valores valem isoladamente, e a tela não os liga (RQ-REP-15)."""
    metric = INDICATORS[ctx.indicador]
    unit = ctx.labels.unidade
    frames, digests, observed, incomparable = [], [], {}, {}
    if ctx.nivel == "estados":
        frame, data = _state_series(ctx, res, window)
        frames.append(data)
        observed = _observed_values(frame, metric)[1]
    elif ctx.nivel == "brasil":
        frame = _brazil_series(ctx, window)
        frames.append(frame)
        observed = _observed_values(frame, metric)[1]
    else:
        units = [item["id"] for item in res.items if item["tipo"] == "municipio"]
        keys = None if len(units) == len(ctx.catalog) else sorted(units)
        observed, digest = _unit_observed(ctx.frame, ctx.mapping, ctx.settings, list(window), ctx.category,
                                          "density" if ctx.density else "counts", metric, keys)
        observed = dict(observed)
        digests.append(digest)
        if res.sets:
            frame, incomparable, rows = _set_series(ctx, res, window)
            frames.append(rows)
            observed.update(_observed_values(frame, metric)[1])
    values, with_value = [], 0
    for item in res.items:
        seen = observed.get(item["id"], {})
        points = [{"competencia": period, "valor": seen.get(period)} for period in window]
        present = [point["valor"] for point in points if point["valor"] is not None]
        values += present
        with_value += bool(present)
        reason = incomparable.get((item["id"], ctx.category))
        item["serie"] = {"observacoes": points, "comparavel": reason is None,
                         "motivo": None if reason is None else
                         "Série não comparável: " + reason + "; cada valor vale isoladamente e os pontos não são ligados "
                         "(INCOMPARABILIDADE)"}
    notes = ["Série temporal de " + human_period(window[0]) + " a " + human_period(window[-1]) + " (" +
             thousands(len(window)) + " competências): o valor observado d" + ("a densidade" if metric == "density" else
                                                                           "a quantidade") +
             " em cada competência, pela mesma preparação da análise; sem classificação, sem linha ajustada e sem "
             "preencher lacunas (competência sem valor fica sem ponto)."]
    if incomparable:
        notes.append("Conjuntos com membros diferentes entre as competências: os valores valem isoladamente e não são "
                     "ligados por linha (CAP-AGR-01; RQ-REP-15).")
    notes += premise_notes(ctx.settings, "temporal", ctx.mapping)
    res.frames += frames
    res.digests += digests
    res.notes += notes
    res.methods["serie"] = SERIE_METHOD
    top = {"janela": {"inicio": window[0], "fim": window[-1], "competencias": list(window)},
           "competencias": len(window), "indicador": ctx.indicador,
           "unidade_valor": "por 1.000 habitantes" if metric == "density" else count_unit_label(ctx.mapping, ctx.settings),
           "itens_com_valor": with_value, "itens": len(res.items),
           "rotulo_itens": unit.plural if ctx.nivel == "municipios" else (ctx.labels.grupo.plural if ctx.nivel == "estados"
                                                                          else "Brasil")}
    return top, ([min(values), max(values)] if values else None)


def _nearest_of(ctx, spatial, item):
    if spatial is None or item["tipo"] != "municipio":
        return None
    members = spatial.nearest.get(item["id"])
    if not members:
        return None
    return {"id": members[0], "rotulo": _label(ctx.catalog[members[0]]),
            "empate": [{"id": key, "rotulo": _label(ctx.catalog[key])} for key in members] if len(members) > 1 else []}


def _group_of(ctx, item):
    if item["tipo"] != "municipio":
        return None
    if ctx.brazil:
        code = ctx.catalog[item["id"]]["code"]
        return code[:2] if code[:2] in STATES else None
    return ctx.groups.get(item["id"]) if ctx.group_column else None


def _availability(ctx) -> dict:
    """O que a fonte permite, com o motivo (sem calcular nada): distribuição, densidade, espacial, tendência,
    rotatividade, estados e bolhas de grupo."""
    unit, group = ctx.labels.unidade, ctx.labels.grupo

    def entry(ok, reason="", pending=None):
        return {"disponivel": bool(ok), "motivo": reason, "pendencia": pending}

    out = {"distribuicao": entry(True), "densidade": entry(ctx.density, "" if ctx.density else _no_population(ctx))}
    if ctx.nivel == "estados":
        out["espacial"] = entry(False, _sem_ponto_unico(ctx.labels))
    elif ctx.nivel == "brasil":
        out["espacial"] = entry(False, BRAZIL_NO_POINT)
    elif ctx.brazil:
        settings = _official_settings(ctx.frame, ctx.mapping, True)
        if not SPATIAL_ROLES <= set(settings.get("governed_roles") or []):
            out["espacial"] = entry(False, GOVERNED)
        elif _referencial_suportado(settings.get("crs")) is None:
            out["espacial"] = entry(False, NO_CRS)
        else:
            out["espacial"] = entry(True)
    else:
        out["espacial"] = _upload_spatial_availability(ctx, entry)
    if ctx.periods_error:
        out["tendencia"] = entry(False, ctx.periods_error)
    elif len(ctx.periods) < 2:
        out["tendencia"] = entry(False, "Uma só competência: a mudança (CAP-TMP-01) e a tendência (CAP-TEN-01) exigem duas "
                                        "ou mais.")
    else:
        try:
            _temporal_premises(ctx)
            out["tendencia"] = entry(True, "" if len(ctx.periods) >= 4 else
                                     "Com " + str(len(ctx.periods)) + " competências, só a mudança (CAP-TMP-01) é "
                                     "avaliável; a tendência (CAP-TEN-01) exige quatro.")
        except ValueError as exc:
            out["tendencia"] = entry(False, str(exc))
    if ctx.brazil:
        out["rotatividade"] = entry(False, ROTATION)
    elif not ctx.mapping.get("identity"):
        out["rotatividade"] = entry(False, "A rotatividade (CAP-ROT-01) exige um identificador individual da mesma pessoa "
                                           "entre os períodos; a planilha não tem essa coluna associada.")
    elif not role_established(ctx.frame, ctx.mapping, ctx.settings, "identity"):
        out["rotatividade"] = entry(False, "Escolha a coluna de " + ROLE_NAMES["identity"] + " no seletor.",
                                    {"chave": "confirmed_roles", "opcoes": ["identity"],
                                     "texto": "Escolha a coluna de " + ROLE_NAMES["identity"] + " no seletor."})
    elif len(ctx.periods) < 2:
        out["rotatividade"] = entry(False, "Rotatividade exige pelo menos dois períodos.")
    else:
        missing = [key for key in ("longitudinal_identity_confirmed", "territory_longitudinal_confirmed",
                                   "cohort_coverage_confirmed") if not ctx.settings.get(key)]
        out["rotatividade"] = entry(not missing, premise_reason(ctx.settings, missing[0]) if missing else "")
    if ctx.brazil:
        state, _, reason = state_source(ctx.sources)
        out["estados"] = entry(state is not None, reason if state is None else "")
        out["grupos"] = dict(out["estados"])
    else:
        out["estados"] = entry(False, "O nível estados existe só na base do Brasil, com a fonte estadual de médicos únicos.")
        out["grupos"] = entry(False, "Sem um valor próprio de cada " + group.singular + " na planilha, não há bolha de " +
                              group.singular + ": somar " + unit.g("os", "as") + " " + unit.plural + " seria uma agregação "
                              "(CAP-AGR-01), com possível dupla contagem. " + group.g("O", "A") + " " + group.singular +
                              " serve para navegar e escolher " + unit.g("os", "as") + " " + unit.plural + ".")
    return out


def _sem_ponto_unico(rotulos: Rotulos) -> str:
    """Por que a distância não se aplica no nível de cima (os estados, na base do Brasil): o grupo não tem um ponto
    único. Pelos rótulos da fonte, com o gênero de cada um: "No nível dos estados, a distância não se aplica: os estados
    não têm um ponto único. Abra os municípios de um estado …"; numa estrutura de distritos e províncias, "No nível das
    províncias, … Abra os distritos de uma província …"."""
    unit, group = rotulos.unidade, rotulos.grupo
    return ("No nível d" + group.g("os", "as") + " " + group.plural + ", a distância não se aplica: " +
            group.g("os", "as") + " " + group.plural + " não têm um ponto único. Abra " + unit.g("os", "as") + " " +
            unit.plural + " de " + group.g("um", "uma") + " " + group.singular + " para usar a análise espacial.")


def _upload_spatial_availability(ctx, entry):
    unit = ctx.labels.unidade
    if not (ctx.mapping.get("latitude") and ctx.mapping.get("longitude")):
        return entry(False, "A planilha não tem latitude e longitude associadas: a distância (CAP-ESP-01) não é calculada "
                            "para " + unit.g("os", "as") + " " + unit.plural + ".")
    settings = apply_premises(ctx.frame, ctx.mapping, dict(ctx.premissas), spatial=True)
    roles = coordinate_roles(ctx.frame, ctx.mapping, settings)
    if roles != {"latitude", "longitude"}:
        missing = sorted(SPATIAL_ROLES - roles)
        text = "Escolha as colunas de latitude e longitude (graus decimais)."
        return entry(False, text, {"chave": "confirmed_roles", "opcoes": missing, "texto": text})
    crs = ctx.premissas.get("crs")
    if not crs:
        return entry(False, CRS_PENDING, {"chave": "crs", "opcoes": list(REFERENCIAIS_ACEITOS), "texto": CRS_PENDING})
    if _referencial_suportado(crs) is None:
        return entry(False, CRS_UNSUPPORTED)
    if not settings.get("number_format") and verified_separator(ctx.frame, ctx.mapping) is None:
        text = "Escolha o separador decimal das coordenadas (vírgula ou ponto): o formato não pôde ser verificado nos dados."
        return entry(False, text, {"chave": "number_format", "opcoes": list(NUMBER_FORMATS), "texto": text})
    return entry(True)


def _context_line(ctx) -> dict:
    """Linha de contexto do Brasil (decisão D5 de 19/10/2026): a taxa nacional na competência, sem classificar nada;
    reaproveitada entre pedidos da mesma competência e categoria (_reaproveitar). No nível Brasil, o próprio item é o
    total nacional: sem a linha."""
    if not ctx.brazil or ctx.nivel == "brasil":
        return {"brasil": None}
    return _reaproveitar(ctx, "contexto", {}, lambda: _national_line(ctx))


def _national_line(ctx) -> dict:
    reference = national_reference(ctx.sources, [ctx.period], [ctx.category])
    base = {"rotulo": "Brasil (total nacional)", "competencia": ctx.period, "densidade": None, "quantidade": None,
            "populacao": None, "competencia_populacao": None, "avaliabilidade": "NAO_AVALIAVEL", "motivo": None,
            "nota": NOTE_CONTEXT, "regra_populacao": None}
    if reference.get("estado") == "INDISPONIVEL":
        return {"brasil": {**base, "motivo": reference.get("motivo")}}
    value = reference["valores"][0]
    return {"brasil": {**base, "rotulo": reference["rotulo"], "densidade": _num(value["valor"]),
                       "quantidade": _num(value["numerador"]), "populacao": _num(value["denominador"]),
                       "competencia_populacao": value["competencia_populacao"],
                       "avaliabilidade": value["avaliabilidade"], "motivo": value["motivo"],
                       "regra_populacao": reference["regra_populacao"]}}


NOTE_CONTEXT = ("Brasil (total nacional) como linha de contexto: contagem da fonte nacional e população pela regra "
                "BR-POP-JUNHO-1; não classifica nem colore os itens do gráfico.")


def _page_extras(ctx, spec, body, res):
    """Campos da página única: por item, só quando pedidos; no topo, sempre nivel, indicador, rotulos, disponibilidade e
    contexto (a sessão é preenchida pela rota)."""
    items = body["itens"]
    by_id = {item["id"]: item for item in items}
    for item in items:
        item["grupo_territorial"] = _group_of(ctx, item)
    if res.reference is not None:
        # Por elegibilidade (24/10/2026), o território de referência de cada item (o mais próximo ou o mais distante dos
        # elegíveis, com os empates) vai em referencia_do_item; com membros escolhidos, o membro mais próximo, como antes.
        por_item = res.reference.get("modo") == "elegiveis"
        for item in items:
            item["referencia_mais_proxima"] = None if por_item else _nearest_of(ctx, res.spatial, item)
            if por_item:
                item["referencia_do_item"] = _nearest_of(ctx, res.spatial, item)
    body.update({"nivel": ctx.nivel, "indicador": ctx.indicador, "rotulos": ctx.labels.public(),
                 "disponibilidade": _availability(ctx), "contexto": _context_line(ctx)})
    if spec["tendencia"] is not None:
        body["tendencia"], span = _trend(ctx, res, spec["tendencia"], by_id)
        body["dominios"]["tendencia"] = list(span) if span else None
    if spec["serie"] is not None:
        body["serie"], span = _series(ctx, res, spec["serie"], by_id)
        body["dominios"]["serie"] = list(span) if span else None
    if spec["grupos"] is not None:
        body["grupos"] = _groups(ctx, res, spec["grupos"], by_id)
    if spec["grupos_mapa"] is not None:  # os grupos que pintam o mapa: à parte de `grupos`, sem notas nem frase
        body["grupos_mapa"] = _groups(ctx, res, spec["grupos_mapa"], by_id, "grupo_mapa")
    if spec["faixas"] is not None:
        body["faixas"] = _bands(ctx, res, spec["faixas"], ctx.indicador, "faixa", "CAP-DIS-03", by_id)
    if spec["faixas_distancia"] is not None:
        body["faixas_distancia"] = _bands(ctx, res, spec["faixas_distancia"], "distancia", "faixa_distancia", "CAP-ESP-03",
                                          by_id)
    if spec["condicoes"] is not None:
        body["condicoes"] = _conditions(ctx, res, spec["condicoes"], by_id)
    if spec["ordenar"] is not None:
        body["ordenacao"] = _ordering(ctx, res, spec["ordenar"], by_id)
    if spec["comparar"] is not None:
        body["comparacao"] = _comparison(ctx, res, spec["comparar"], by_id)
        res.notes += body["comparacao"]["notas"]
    if spec["rotatividade"] is not None:
        body["rotatividade"] = _rotation(ctx, res, spec["rotatividade"], by_id)
    if ctx.brazil and ctx.nivel != "brasil":
        res.notes.append(NOTE_CONTEXT)
    body["notas"] = _dedupe(body["notas"] + res.notes)
    body["limitacoes"] = _dedupe(body["limitacoes"] + res.limitations)


def _page_normalized(ctx, spec, normalized):
    page = {key: spec[key] for key in ("nivel", "indicador", "tendencia", "grupos", "ordenar", "comparar")}
    if spec["grupos_mapa"] is not None:  # só com o pedido: sem ele, a chave de execução é a de antes
        page["grupos_mapa"] = spec["grupos_mapa"]
    if spec["serie"] is not None:  # idem (24/10/2026)
        page["serie"] = spec["serie"]
    page["faixas"] = None if spec["faixas"] is None else [format(value, "f") for value in spec["faixas"]]
    page["faixas_distancia"] = (None if spec["faixas_distancia"] is None else
                                [format(value, "f") for value in spec["faixas_distancia"]])
    page["condicoes"] = None if spec["condicoes"] is None else [
        {key: str(entry[key]) for key in ("atributo", "operador", "valor")} for entry in spec["condicoes"]["definicao"]]
    page["rotatividade"] = None if spec["rotatividade"] is None else list(spec["rotatividade"])
    page["premissas"] = ctx.premissas
    page["rotulos"] = ctx.labels.public()
    return {**normalized, "pagina": page}


# --------------------------------------------------------------------------------------------- estados (página única)
STATE_REFUSALS = {
    "base": "No nível estados, os estados escolhidos vão em estados (sem a lista, todos os da fonte estadual): base vale "
            "só para municípios.",
    "conjuntos": "Conjuntos de estados não estão disponíveis no gráfico; marque municípios para formar conjuntos.",
    "referencia": "Não se aplica: estados não têm um ponto único. Para usar a distância, mostre os municípios.",
    "faixas_distancia": "Não se aplica: estados não têm um ponto único; as faixas de distância valem para municípios.",
}


def _state_choice(raw, keys):
    """Estados escolhidos no nível estados (24/10/2026): os prefixos IBGE (ou os ids "uf:") em `estados`, na ordem do
    código; sem a lista, todos os estados da fonte estadual, como antes."""
    if raw is None:
        return keys
    if (not isinstance(raw, list) or not raw or len(raw) > len(keys) or len(set(raw)) != len(raw) or
            any(not isinstance(value, str) for value in raw)):
        raise ValueError("Estados inválidos: envie em estados a lista dos estados escolhidos, por exemplo [\"29\", \"42\"], "
                         "sem repetir.")
    wanted = {value if value.startswith("uf:") else "uf:" + value for value in raw}
    unknown = sorted(wanted - set(keys))
    if unknown:
        raise ValueError("Estado sem registro na fonte estadual: " + ", ".join(key[3:][:8] for key in unknown[:5]) + ".")
    return [key for key in keys if key in wanted]


def _state_measures(ctx, period, keys) -> Measures:
    """Estados pela abrangência da base Brasil (territorial_levels.state_part): contagem estadual de médicos únicos e,
    na densidade, a população do estado (soma dos seus municípios na própria competência, só com todos registrados)."""
    parts = Parts()
    estados = tuple(key[3:] for key in keys)
    data = state_part(ctx.sources, {"period_filter": period, "category_filter": ctx.category}, True,
                      Abrangencia(False, estados, False, (), ()), ctx.index, parts)
    coverage = {"uf:" + item["estado"]: item for item in parts.state_population}
    records = {}
    for row in data.to_dict("records"):
        key = "uf:" + str(row["uf"])
        records[key] = {"valores": {"populacao": None if pd.isna(row["population"]) else row["population"],
                                    "quantidade": None if pd.isna(row["quantity"]) else row["quantity"],
                                    "densidade": None if pd.isna(row["density"]) else row["density"]},
                        "condicao": row["condition"], "populacao_estadual": coverage.get(key)}
    prepared = data.assign(key="uf:" + data["uf"].astype(str)) if not data.empty else data
    return Measures(period, records, data, prepared, parts)


def _state_item(ctx, key, final, initial, changes):
    prefix = key[3:]
    record = final.records.get(key)
    values = record["valores"] if record is not None else {}
    item = {"id": key, "tipo": "estado", "rotulo": uf_label(prefix), "uf": STATES[prefix][0],
            "populacao": _num(values.get("populacao")), "quantidade": _num(values.get("quantidade")),
            "densidade": _num(values.get("densidade")), "distancia_km": None}
    motives = []
    if item["quantidade"] is None:
        motives.append("Sem registro em " + human_period(final.period) + " na fonte estadual (categoria " + ctx.category +
                       "): valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)")
    elif item["densidade"] is None:
        info = record.get("populacao_estadual") or {}
        missing = list(info.get("ausentes") or [])
        motives.append("Densidade não avaliável em " + human_period(final.period) + ": população estadual incompleta, " +
                       thousands(info.get("incluidos") or 0) + " de " + thousands(info.get("previstos") or 0) +
                       " municípios com registro na fonte municipal" +
                       (" (sem registro: " + _codes_text(missing) + ")" if missing else "") +
                       "; a população não é estimada (DENOMINADOR_AUSENTE)")
    inicial, variation, variation_ok = _empty3(), _empty3(), None
    if initial is not None:
        variation_ok = False
        before = initial.records.get(key)
        if before is not None:
            inicial = _values3(before)
        if item["quantidade"] is not None and (before is None or not _present(before["valores"]["quantidade"])):
            motives.append(_no_initial(initial.period))
        elif item["quantidade"] is not None:
            variation, variation_ok, why, exact = _percentages(ctx, before, record)
            motives += why
            changes[key] = exact
    item.update({"inicial": inicial, "variacao_percentual": variation,
                 "avaliavel": {"densidade": item["densidade"] is not None, "distancia": None, "variacao": variation_ok},
                 "motivos": motives, "referencia": False})
    return item


def _state_notes(ctx, final, initial):
    unit = count_unit_label(ctx.mapping, ctx.settings)
    notes = [NOTE_STATES, NOTE_STATE_POPULATION,
             "Valores de " + ctx.category + " em " + human_period(ctx.period) + ": contagem estadual de médicos únicos "
             "(regra UF-CONTAGEM-ESTADUAL-1) e população do estado (regra UF-POP-MUNICIPIOS-1). Densidade = contagem / "
             "população × 1.000, em precisão integral.",
             "Valores ausentes e denominadores nulos não são transformados em zero; itens não avaliáveis seguem com o "
             "motivo.",
             "Unidade de contagem: " + unit + ". Não há conversão entre pessoas, vínculos e postos.",
             "Estados e municípios não aparecem juntos no mesmo gráfico nem são somados entre si."]
    for measures in (final, initial):
        if measures is None:
            continue
        for item in measures.parts.state_population:
            if item["populacao"] is None:
                notes.append(item["rotulo"] + " em " + human_period(item["competencia"]) + ": população estadual "
                             "incompleta, " + thousands(item["incluidos"]) + " de " + thousands(item["previstos"]) +
                             " municípios com registro na fonte municipal; a população não é estimada e a densidade do "
                             "estado não é avaliada.")
        notes += measures.parts.sources_apart
    if initial is not None:
        notes.append("Variação percentual (CAP-TMP-01) entre " + human_period(initial.period) + " e " +
                     human_period(ctx.period) + ": (valor final − valor inicial) / valor inicial × 100, em aritmética "
                     "exata; não indica tendência. Com valor inicial zero, a variação percentual não é avaliável "
                     "(BASE_ZERO).")
        notes += premise_notes(ctx.settings, "temporal", ctx.mapping)
    return _dedupe(notes)


def _engine_rows(ctx):
    """Linhas municipais da competência e da categoria: o quadro que main._compute recebe nas operações sobre valores já
    preparados (distribuição e comparação de estados), sem copiar a base inteira."""
    return _rows(ctx.frame, ctx.mapping, [ctx.period], ctx.category)


def _compute_states(ctx, options, spec) -> dict:
    """Nível estados da base Brasil: os estados da fonte estadual como itens (tipo "estado"), na ordem do código."""
    for key, text in STATE_REFUSALS.items():
        if options.get(key) not in (None, [], {}):
            raise ValueError(text)
    if spec["rotatividade"] is not None:
        raise ValueError(ROTATION)
    if spec["condicoes"] and any(spec["condicoes"]["nodes"][own]["atributo"] == "distancia"
                                 for own in spec["condicoes"]["leaves"]):
        raise ValueError(STATE_REFUSALS["referencia"])
    if spec["ordenar"] and spec["ordenar"]["atributo"] == "distancia_km":
        raise ValueError(STATE_REFUSALS["referencia"])
    initial_period = _initial_period(ctx, options)
    if spec["ordenar"] and spec["ordenar"]["atributo"] == "variacao" and initial_period is None:
        raise ValueError("A ordenação pela variação exige a competência inicial (visão Trajetória).")
    state, prefixes, reason = state_source(ctx.sources)
    if state is None:
        raise ValueError(reason)
    keys = _state_choice(options.get("estados"), ["uf:" + prefix for prefix in sorted(prefixes & set(ctx.index.by_uf))])
    final = _state_measures(ctx, ctx.period, keys)
    initial = _state_measures(ctx, initial_period, keys) if initial_period else None
    changes = {}
    items = [_state_item(ctx, key, final, initial, changes) for key in keys]
    res = Result(keys, [], None, final, initial, None, items, _engine_rows(ctx), changes=changes)
    res.methods.update({"estado": METODOS["estado"], "populacao_estadual": METODOS["populacao_estadual"]})
    limitations = ["UNIDADES_NAO_AVALIAVEIS"] if any(
        flag is False for item in items for flag in item["avaliavel"].values()) else []
    body = {"competencia": ctx.period, "competencia_inicial": initial_period, "categoria": ctx.category,
            "versao_base": (ctx.frame.attrs.get("source") or {}).get("version"), "chave_execucao": None,
            "referencia": None, "itens": items, "dominios": _domains(items), "notas": _state_notes(ctx, final, initial),
            "limitacoes": limitations}
    _page_extras(ctx, spec, body, res)
    normalized = _page_normalized(ctx, spec, {"competencia": ctx.period, "competencia_inicial": initial_period,
                                              "categoria": ctx.category, "estados": keys})
    body["chave_execucao"] = _execution_key(ctx, final, initial, normalized, None, res.methods, res.frames, res.digests)
    return body


# --------------------------------------------------------------------------------------------- Brasil (página única)
BRAZIL_NO_POINT = ("Não se aplica: as distâncias usam a localização de cada município, e o Brasil não tem um ponto "
                   "único.")
# A matriz da decisão D3: com o Brasil, valem os valores (densidade e quantidade) e a evolução no tempo; o que agrupa,
# ordena, filtra ou compara vários territórios não se aplica, porque o Brasil é um só.
BRAZIL_REFUSALS = {
    "base": "No nível Brasil, a unidade é o país inteiro: base vale só para municípios.",
    "conjuntos": "Não se aplica: o total do Brasil vem pronto da fonte nacional e não é somado a outros territórios.",
    "referencia": BRAZIL_NO_POINT,
    "faixas_distancia": BRAZIL_NO_POINT,
}
BRAZIL_SINGLE = {
    "grupos": "Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só.",
    "grupos_mapa": "Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só.",
    "faixas": "Não se aplica: as faixas agrupam vários territórios, e o Brasil é um só.",
    "condicoes": "Não se aplica: as condições separam vários territórios, e o Brasil é um só.",
    "ordenar": "Não se aplica: a ordenação ordena vários territórios, e o Brasil é um só.",
    "comparar": "Não se aplica: a comparação põe vários territórios lado a lado, e o Brasil é um só.",
}
NOTE_BRAZIL = ("Brasil (total nacional): contagem da fonte nacional e população pela soma da população estimada dos "
               "municípios em junho do ano (regra BR-POP-JUNHO-1). Densidade = contagem / população × 1.000, em precisão "
               "integral. O total do Brasil não é a soma dos estados nem dos municípios e não aparece com eles no mesmo "
               "gráfico.")


def _brazil_values(ctx, periods):
    """Valores do Brasil nas competências (territorial_levels.national_reference, a mesma conta da linha de contexto):
    contagem da fonte nacional, população BR-POP-JUNHO-1 e densidade, com a avaliabilidade e o motivo de cada uma."""
    reference = national_reference(ctx.sources, list(periods), [ctx.category])
    if reference.get("estado") == "INDISPONIVEL":
        raise ValueError("O total do Brasil não está disponível nesta base: " + str(reference.get("motivo") or "") +
                         ". As demais análises continuam com os estados e os municípios.")
    return {entry["competencia"]: entry for entry in reference["valores"]}


def _brazil_measures(ctx, period) -> Measures:
    entry = _brazil_values(ctx, [period])[str(period)]
    record = {"valores": {"populacao": entry["denominador"], "quantidade": entry["numerador"], "densidade": entry["valor"]},
              "motivo": entry.get("motivo"), "nota": entry.get("nota")}
    rows = pd.DataFrame([{"period": str(period), "category": ctx.category, "quantity": entry["numerador"],
                          "population": entry["denominador"], "density": entry["valor"]}])
    return Measures(str(period), {BRAZIL_ID: record}, rows, None)


def _brazil_series(ctx, window):
    """O Brasil na janela da tendência: os valores nacionais de cada competência, no quadro de _trend_series (lacuna
    quando falta a contagem ou a população, nunca zero)."""
    values = _brazil_values(ctx, window)
    rows = [{"territory": BRAZIL_ID, "period": str(period), "category": ctx.category,
             "quantity": values[str(period)]["numerador"], "population": values[str(period)]["denominador"],
             "density": values[str(period)]["valor"]} for period in window]
    return pd.DataFrame(rows, columns=SERIES_COLUMNS)


def _brazil_item(ctx, final, initial, changes):
    record = final.records[BRAZIL_ID]
    values = record["valores"]
    item = {"id": BRAZIL_ID, "tipo": "brasil", "rotulo": "Brasil", "uf": None,
            "populacao": _num(values["populacao"]), "quantidade": _num(values["quantidade"]),
            "densidade": _num(values["densidade"]), "distancia_km": None}
    motives = []
    if item["quantidade"] is None:
        motives.append("Sem registro em " + human_period(final.period) + " na fonte nacional (categoria " + ctx.category +
                       "): valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)")
    elif item["densidade"] is None:
        motives.append("Densidade não avaliável em " + human_period(final.period) + ": " +
                       (record.get("nota") or "sem a população nacional de junho do ano (regra BR-POP-JUNHO-1)") +
                       " (" + str(record.get("motivo") or "DENOMINADOR_AUSENTE") + ")")
    inicial, variation, variation_ok = _empty3(), _empty3(), None
    if initial is not None:
        variation_ok = False
        before = initial.records[BRAZIL_ID]
        inicial = _values3(before)
        if item["quantidade"] is not None and not _present(before["valores"]["quantidade"]):
            motives.append(_no_initial(initial.period))
        elif item["quantidade"] is not None:
            variation, variation_ok, why, exact = _percentages(ctx, before, record)
            motives += why
            changes[BRAZIL_ID] = exact
    item.update({"inicial": inicial, "variacao_percentual": variation,
                 "avaliavel": {"densidade": item["densidade"] is not None, "distancia": None, "variacao": variation_ok},
                 "motivos": motives, "referencia": False})
    return item


def _compute_brazil(ctx, options, spec) -> dict:
    """Nível Brasil da base Brasil (24/10/2026): o país inteiro como uma unidade (decisões D3 e D4), com a contagem da
    fonte nacional e a população pela regra BR-POP-JUNHO-1; a mudança e a tendência sobre os mesmos valores nacionais.
    O que agrupa, ordena, filtra ou compara vários territórios não se aplica (matriz da D3)."""
    for key, text in BRAZIL_REFUSALS.items():
        if options.get(key) not in (None, [], {}):
            raise ValueError(text)
    for key, text in BRAZIL_SINGLE.items():
        if spec[key]:
            raise ValueError(text)
    if spec["rotatividade"] is not None:
        raise ValueError(ROTATION)
    initial_period = _initial_period(ctx, options)
    final = _brazil_measures(ctx, ctx.period)
    initial = _brazil_measures(ctx, initial_period) if initial_period else None
    changes = {}
    items = [_brazil_item(ctx, final, initial, changes)]
    res = Result([BRAZIL_ID], [], None, final, initial, None, items, _engine_rows(ctx), changes=changes)
    res.methods.update({"populacao_nacional": METODOS["populacao_nacional"]})
    limitations = ["UNIDADES_NAO_AVALIAVEIS"] if any(
        flag is False for item in items for flag in item["avaliavel"].values()) else []
    notes = [NOTE_BRAZIL, "Valores ausentes e denominadores nulos não são transformados em zero; itens não avaliáveis "
                          "seguem com o motivo."]
    if initial is not None:
        notes.append("Variação percentual (CAP-TMP-01) entre " + human_period(initial.period) + " e " +
                     human_period(ctx.period) + ": (valor final − valor inicial) / valor inicial × 100, em aritmética "
                     "exata; não indica tendência. Com valor inicial zero, a variação percentual não é avaliável "
                     "(BASE_ZERO).")
        notes += premise_notes(ctx.settings, "temporal", ctx.mapping)
    body = {"competencia": ctx.period, "competencia_inicial": initial_period, "categoria": ctx.category,
            "versao_base": (ctx.frame.attrs.get("source") or {}).get("version"), "chave_execucao": None,
            "referencia": None, "itens": items, "dominios": _domains(items), "notas": _dedupe(notes),
            "limitacoes": limitations}
    _page_extras(ctx, spec, body, res)
    normalized = _page_normalized(ctx, spec, {"competencia": ctx.period, "competencia_inicial": initial_period,
                                              "categoria": ctx.category, "brasil": BRAZIL_ID})
    body["chave_execucao"] = _execution_key(ctx, final, initial, normalized, None, res.methods, res.frames, res.digests)
    return body


# --------------------------------------------------------------------------------------------- rotas
def compute(sources, mapping, options, frame=None) -> dict:
    """POST /api/painel: municípios base (ou unidades da planilha, ou estados), conjuntos e referência numa competência,
    com a variação desde a competência inicial e, na página única, as análises pedidas."""
    page = is_page(options)
    if frame is not None and not page:
        raise ValueError(OFFICIAL_ONLY)
    ctx = context(sources, mapping, options, PAGE_KEYS if page else PANEL_KEYS, frame=frame, page=page)
    spec = _page_spec(ctx, options) if page else None
    if page and ctx.nivel == "estados":
        return _compute_states(ctx, options, spec)
    if page and ctx.nivel == "brasil":
        return _compute_brazil(ctx, options, spec)
    unit = ctx.labels.unidade
    initial_period = _initial_period(ctx, options)
    base = _universe(options.get("base"), ctx, unit.g("os", "as") + " " + unit.plural + " base", allow_empty=True)
    sets = _sets(options.get("conjuntos"), ctx)
    if not base and not sets:
        raise ValueError("Escolha " + unit.g("os", "as") + " " + unit.plural + " base ou um conjunto para o painel.")
    reference = _reference(options.get("referencia"), ctx)
    # Território de referência por elegibilidade (24/10/2026): só na página única; a referência de cada item é escolhida
    # entre os elegíveis, e eles não entram como itens (a seleção da pessoa continua a mesma).
    eligible_mode = reference is not None and reference.get("modo") == "elegiveis"
    if eligible_mode and not page:
        raise ValueError("O território de referência por elegibilidade vale só no formato da página única (com nivel).")
    if page:
        _page_requirements(ctx, spec, reference, initial_period)
    final = _measures(ctx, ctx.period)
    initial = _measures(ctx, initial_period) if initial_period else None
    reference_ids = reference["membros"] if reference is not None else []
    # Os membros da referência entram como itens (distância zero); a ordem padrão é a do código IBGE (RQ-REP-03).
    units = sorted(set(base) | set(reference_ids), key=lambda key: (ctx.catalog[key]["code"], key))
    spatial = None
    if eligible_mode:
        spatial = _eligible_spatial(ctx, reference, final, units)
    elif reference is not None:
        spatial = _spatial(ctx, reference_ids, units + [key for spec_ in sets for key in spec_["membros"]])
    changes = {}
    items = [_unit_item(ctx, key, final, initial, spatial, set(reference_ids), changes) for key in units]
    items += [_set_item(ctx, spec_, final, initial, spatial, reference, changes) for spec_ in sets]
    block = None
    if eligible_mode:
        block = _eligible_block(ctx, reference, spatial, items, final)
    elif reference is not None:
        block = {"tipo": "municipio" if len(reference_ids) == 1 else "conjunto",
                 "membros": [{"id": key, "rotulo": _label(ctx.catalog[key])} for key in reference_ids],
                 "origem": _origin(ctx, reference, base, final)}
    normalized = {"competencia": ctx.period, "competencia_inicial": initial_period, "categoria": ctx.category,
                  "base": base, "conjuntos": [{**spec_, "membros": sorted(spec_["membros"])} for spec_ in sets],
                  "referencia": None if reference is None else _eligible_normalized(reference) if eligible_mode else {
                      "membros": sorted(reference_ids),
                      "criterio": None if reference["criterio"] is None else {
                          key: value for key, value in reference["criterio"].items()}}}
    body = {"competencia": ctx.period, "competencia_inicial": initial_period, "categoria": ctx.category,
            "versao_base": (ctx.frame.attrs.get("source") or {}).get("version") if ctx.brazil else
            (ctx.frame.attrs.get("input_file") or {}).get("sha256"),
            "chave_execucao": None, "referencia": block, "itens": items, "dominios": _domains(items),
            "notas": _notes(ctx, base, sets, items, final, initial, spatial, reference),
            "limitacoes": _limitations(ctx, sets, items, spatial)}
    if not page:
        body["chave_execucao"] = _execution_key(ctx, final, initial, normalized, spatial)
        return body
    res = Result(base, sets, reference, final, initial, spatial, items, final.rows, changes=changes)
    _page_extras(ctx, spec, body, res)
    body["chave_execucao"] = _execution_key(ctx, final, initial, _page_normalized(ctx, spec, normalized), spatial,
                                            res.methods or {"pagina": "PAGINA-UNICA-1"}, res.frames, res.digests)
    return body


def references(sources, mapping, options, frame=None) -> dict:
    """POST /api/painel/referencias: candidatos do universo na ordem do critério (CAP-SUB-02), com empates na mesma
    posição e não avaliáveis à parte. "Usar o primeiro" é a seleção por posição (CAP-SUB-03), feita na tela."""
    ctx = context(sources, mapping, options, REFERENCE_KEYS, frame=frame, page=frame is not None)
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


# --------------------------------------------------------------------------------------------- mapa (página única)
MAP_KEYS = frozenset(("competencia", "categoria", "premissas", "rotulos"))
NO_COORDINATES = "A planilha não tem colunas de latitude e longitude associadas: o mapa precisa delas."


def mapa(sources, mapping, options, frame=None) -> dict:
    """POST /api/painel/mapa: as coordenadas autorizadas de todas as unidades do catálogo da fonte, na competência, as
    mesmas que a análise espacial usa para medir as distâncias (nearest_reference.territory_coordinates, pela memória da
    versão em _coordinates): na base Brasil, a sede municipal do perfil oficial em SIRGAS 2000, com a camada complementar
    governada; na planilha, as colunas de latitude e longitude no referencial confirmado pela pessoa (premissas.crs;
    sem ele, a mesma pendência da análise espacial). Cada unidade vai em `pontos` ({id, lat, lon}, graus decimais) ou,
    sem coordenada válida na competência, em `sem_coordenada` ({id, rotulo, motivo}, o motivo com o código, como nas
    distâncias). Os ids são os dos itens de POST /api/painel, na ordem do código. Estados não têm ponto (só unidades).
    Nada é calculado além da leitura das coordenadas, nada é registrado na sessão e nada vai ao provedor de IA."""
    ctx = context(sources, mapping, options, MAP_KEYS, frame=frame, page=True)
    if not ctx.brazil and not (ctx.mapping.get("latitude") and ctx.mapping.get("longitude")):
        raise ValueError(NO_COORDINATES)
    settings = _spatial_settings(ctx)
    coords = _coordinates(ctx.frame, ctx.mapping, settings, ctx.period)
    spatial = Spatial(settings, coords, [], [], {}, referencial=_referencial_suportado(settings.get("crs")))
    latitudes, longitudes = coords["lat"].to_dict(), coords["lon"].to_dict()
    points, missing = [], []
    for key in sorted(ctx.catalog, key=lambda key: (ctx.catalog[key]["code"], key)):
        state = spatial.condition(key)
        if state == "VALIDA":
            points.append({"id": key, "lat": float(latitudes[key]), "lon": float(longitudes[key])})
        else:
            missing.append({"id": key, "rotulo": _label(ctx.catalog[key]),
                            "motivo": "Sem coordenada válida em " + human_period(ctx.period) + ": " +
                                      CONDITION_TEXT[state] + " (" + MOTIVES[state] + ")"})
    return {"competencia": ctx.period, "referencial": spatial.referencial, "pontos": points, "sem_coordenada": missing}


# --------------------------------------------------------------------------------------------- frase-resumo (página única)
def summary_facts(body) -> dict:
    """Contagens e extremos que a frase-resumo copia (resumo_painel.py), contados aqui, no motor, sobre os itens da própria
    resposta: o compositor só copia caminhos, sem comparar valores. `contagens`: unidades (municípios, unidades da
    planilha ou estados) e conjuntos no gráfico; unidades sem valor do indicador; com a referência, unidades (fora da
    referência) sem distância; com a competência inicial, unidades sem variação avaliável; com a rotatividade, unidades
    com e sem permanência avaliável. `extremos`: as posições em `itens` da unidade de menor e da de maior valor (nos
    empates, a primeira na ordem dos itens), por indicador, distância, variação e permanência."""
    items = body["itens"]
    indicator = body["indicador"]
    units = [index for index, item in enumerate(items) if item["tipo"] in ("municipio", "estado", "brasil")]
    counts = {"unidades": len(units), "conjuntos": sum(item["tipo"] == "conjunto" for item in items),
              "sem_valor": sum(items[index][indicator] is None for index in units)}
    extremes = {"indicador": _extremes(items, units, lambda item: item[indicator])}
    if body.get("referencia") is not None:
        targets = [index for index in units if not items[index]["referencia"]]
        counts["sem_distancia"] = sum(items[index]["distancia_km"] is None for index in targets)
        extremes["distancia"] = _extremes(items, targets, lambda item: item["distancia_km"])
    if body.get("competencia_inicial"):
        counts["sem_variacao"] = sum(items[index]["variacao_percentual"][indicator] is None for index in units)
        extremes["variacao"] = _extremes(items, units, lambda item: item["variacao_percentual"][indicator])
    if body.get("rotatividade") is not None:
        def permanence(item):
            rotation = item.get("rotatividade") or {}
            return rotation.get("permanencia_percentual") if rotation.get("avaliavel") else None
        counts["com_permanencia"] = sum(permanence(items[index]) is not None for index in units)
        counts["sem_permanencia"] = len(units) - counts["com_permanencia"]
        extremes["permanencia"] = _extremes(items, units, permanence)
    # Para a frase individual e as amplitudes (24/10/2026): o item único (um território, sem conjuntos), se os extremos
    # têm o mesmo valor, e, no item único, a direção da mudança (CAP-TMP-01: aumento, redução ou sem mudança) ou o motivo
    # da variação não avaliável. Tudo contado aqui, no motor; o compositor só escolhe o modelo e copia os caminhos.
    values = {"indicador": lambda item: item[indicator], "distancia": lambda item: item["distancia_km"],
              "variacao": lambda item: item["variacao_percentual"][indicator],
              "permanencia": lambda item: (item.get("rotatividade") or {}).get("permanencia_percentual")}
    equal = {key: pair is not None and values[key](items[pair[0]]) == values[key](items[pair[1]])
             for key, pair in extremes.items()}
    single = units[0] if len(units) == 1 and not counts["conjuntos"] else None
    out = {"contagens": counts, "extremos": extremes, "iguais": equal, "unico": single}
    if single is not None and body.get("competencia_inicial"):
        change = items[single]["variacao_percentual"][indicator]
        out["direcao"] = (None if change is None else "AUMENTO" if change > 0 else "REDUCAO" if change < 0 else
                          "SEM_MUDANCA")
        out["motivo_variacao"] = (None if change is not None else "BASE_ZERO" if items[single]["inicial"][indicator] == 0
                                  else "DADO_AUSENTE")
    return out


def _extremes(items, indices, value_of):
    present = [(value_of(items[index]), index) for index in indices if value_of(items[index]) is not None]
    if not present:
        return None
    return [min(present)[1], max(present, key=lambda pair: (pair[0], -pair[1]))[1]]


# --------------------------------------------------------------------------------------------- sessão
@per_source()
def _source_fingerprint(frame) -> str:
    """A mesma identidade da fonte de llm_context.investigation_context (colunas, origem, arquivo e dados), para a
    conversa reconhecer que o resultado do gráfico é da base que ela lê; na base Brasil, guardada por versão."""
    return fingerprint({"columns": list(frame.columns), "source": frame.attrs.get("source"),
                        "input_file": frame.attrs.get("input_file"),
                        "data": hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes()).hexdigest()})


def session_record(body, result_id) -> dict:
    """Resultado do gráfico como a sessão o guarda: a resposta inteira, com result_id e os metadados que a leitura da
    conversa confere (validade, operação, chave de execução)."""
    return {**body, "result_id": result_id,
            "metadata": {"operation": OPERATION, "method_version": METHOD, "validity": "VALIDO",
                         "execution_key": body["chave_execucao"], "created_at": datetime.now(timezone.utc).isoformat()}}


def session_context(frame, mapping, options, body) -> dict:
    """Contexto próprio do resultado do gráfico na sessão; não substitui o contexto da conversa (sessions.capture)."""
    source = _source_fingerprint(frame)
    return {"source": source, "signature": fingerprint({"source": source, "mapping": mapping, "options": options}),
            "selection": [], "parameters": options, "operation": None, "capabilities": {}, "origem": "painel",
            "painel": {"nivel": body.get("nivel"), "indicador": body.get("indicador"), "competencia": body["competencia"],
                       "competencia_inicial": body["competencia_inicial"], "categoria": body["categoria"],
                       "itens": len(body["itens"])}}
