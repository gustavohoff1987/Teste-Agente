"""Padrões governados para as duas fontes da base pública Brasil.

Essas associações só são aplicadas à base instalada e íntegra, com estrutura
esperada. Elas não autorizam deduplicação entre municípios ou entre períodos.
Para bases importadas pelo usuário, permanece a confirmação guiada.

Na base oficial, as premissas de comparabilidade que o usuário confirmava são internas
(decisão do responsável pelo produto em 18/10/2026), assim como o referencial geodésico e o
separador decimal das coordenadas nas análises de distância da versão governada. Cada uma vale
por regra governada deste perfil ou somente depois de verificada nos dados; o resultado registra
a origem de cada uma.
"""
from __future__ import annotations

from typing import Any

from brazil_data import FILES
from territorial_hierarchy import distinct_raw


FIELDS = {
    "national": {
        "territory": "pais", "period": "Período (ano e mês)",
        "category": "categoria_profissional", "count": "contagem",
    },
    "municipal": {
        "territory": "municipio", "territory_id": "cod_ibge",
        "period": "Período (ano e mês)", "category": "categoria_profissional",
        "count": "quantidade", "population": "população_estimada",
        "latitude": "latitude", "longitude": "longitude",
    },
}
TRUSTED_CATEGORY = "MEDICINA"

# Premissas internas da base oficial (opção do motor → rótulo, origem, recortes, análises e nota).
# PERFIL_GOVERNADO: regra declarada deste perfil. VERIFICADA_NOS_DADOS: só vale depois da
# conferência em CHECKS; sem ela, a confirmação volta a ser pedida ao usuário. "value" é o valor
# da opção (padrão: True); "governed_version" restringe a premissa à versão governada da base.
PREMISES = {
    "temporal_comparability_confirmed": {
        "label": "Comparabilidade temporal", "origin": "PERFIL_GOVERNADO",
        "scopes": ("national", "municipal"), "operations": ("temporal",),
        "note": "Comparabilidade temporal: premissa governada da base Brasil oficial (mesma fonte, categoria MEDICINA e "
                "unidade pessoas por território e competência em todas as competências); não foi declarada pelo usuário."},
    "territory_longitudinal_confirmed": {
        "label": "Identidade territorial ao longo do tempo", "origin": "VERIFICADA_NOS_DADOS",
        "scopes": ("national", "municipal"), "operations": ("temporal",),
        "note": "Identidade territorial: verificada nos dados; cada território mantém o mesmo identificador e o mesmo nome "
                "em todas as competências. Observações ausentes continuam não avaliáveis."},
    "comparison_confirmed": {
        "label": "Comparabilidade entre municípios", "origin": "PERFIL_GOVERNADO",
        "scopes": ("municipal",), "operations": ("comparisons", "ranking"),
        "note": "Comparabilidade entre territórios: premissa governada da base Brasil oficial (mesma medida, unidade e "
                "população estimada para todos os municípios em cada competência)."},
    "population_additive_confirmed": {
        "label": "Populações municipais sem sobreposição", "origin": "PERFIL_GOVERNADO",
        "scopes": ("municipal",), "operations": ("aggregate",),
        "note": "Agregação: os municípios são partes disjuntas do território nacional e cada população municipal entra uma "
                "única vez (premissa governada da base Brasil oficial)."},
    "component_sum_confirmed": {
        "label": "Total como soma dos componentes", "origin": "PERFIL_GOVERNADO",
        "scopes": ("municipal",), "operations": ("aggregate",),
        "note": "Agregação: a base não identifica pessoas entre municípios; o total é a soma dos componentes, com possível "
                "dupla contagem (premissa governada da base Brasil oficial)."},
    "crs": {
        "label": "Referencial geodésico SIRGAS 2000", "origin": "PERFIL_GOVERNADO", "value": "SIRGAS2000",
        "scopes": ("municipal",), "operations": ("spatial", "nearest", "criteria"), "governed_version": True,
        "note": "Referencial geodésico: SIRGAS 2000, premissa governada da base Brasil oficial (decisão do responsável pelo "
                "produto); a fonte original não declara o referencial, e nenhuma transformação é aplicada."},
    "number_format": {
        "label": "Vírgula como separador decimal das coordenadas", "origin": "VERIFICADA_NOS_DADOS",
        "value": "decimal_comma", "scopes": ("municipal",), "operations": ("spatial", "nearest", "criteria"),
        "governed_version": True,
        "note": "Separador decimal das coordenadas: vírgula, verificada nos dados; as coordenadas preenchidas usam vírgula "
                "decimal ou são inteiras, e quantidades e populações não têm vírgula."},
}
# Premissas das análises de distância: aplicadas só quando a análise usa coordenadas.
SPATIAL_PREMISES = ("crs", "number_format")
# Outro modo de agregação escolhido explicitamente prevalece sobre a soma dos componentes.
AGGREGATION_MODES = ("no_overlap_confirmed", "identity_union_confirmed")
# Verificação por versão da base: a versão (SHA-256 das fontes) fixa o conteúdo conferido.
_VERIFIED: dict[tuple, bool] = {}
_COMMA_DECIMAL = r"-?\d+(?:,\d+)?"


def _territories_stable(frame, expected: dict[str, str]) -> bool:
    """Cada território mantém um único nome em todas as competências (municipal: por código IBGE)."""
    name_col, code_col = expected["territory"], expected.get("territory_id")
    if not code_col:  # recorte nacional: um único território
        return frame[name_col].dropna().astype(str).str.strip().nunique() == 1
    pairs = distinct_raw(frame, [name_col, code_col])
    codes = pairs[code_col].astype(str).str.strip()
    return not pairs.empty and not pairs.isna().any().any() and \
        int(pairs[name_col].astype(str).str.strip().groupby(codes).nunique().max()) == 1


def _decimal_comma(frame, expected: dict[str, str]) -> bool:
    """Coordenadas preenchidas com vírgula decimal ou inteiras (ao menos uma com vírgula); quantidades e
    populações sem vírgula, para que o separador declarado não mude a leitura delas."""
    def values(role):
        return frame[expected[role]].dropna().drop_duplicates().astype(str).str.strip()
    coordinates = [values(role) for role in ("latitude", "longitude")]
    return all(item.str.fullmatch(_COMMA_DECIMAL).all() for item in coordinates) and \
        any(item.str.contains(",", regex=False).any() for item in coordinates) and \
        not any(values(role).str.contains(",", regex=False).any() for role in ("count", "population"))


CHECKS = {"territory_longitudinal_confirmed": _territories_stable, "number_format": _decimal_comma}


def _verified(key: str, frame, expected: dict[str, str]) -> bool:
    version = (frame.attrs.get("source") or {}).get("version")
    cache = (key, tuple(expected.items()), version, len(frame))
    if version and cache in _VERIFIED:
        return _VERIFIED[cache]
    result = bool(CHECKS[key](frame, expected))
    if version:
        _VERIFIED[cache] = result
    return result


def governed_version(frame) -> bool:
    """Base instalada íntegra e na versão do manifesto governado (não uma versão externa fixada)."""
    catalog = frame.attrs.get("catalog") or {}
    return bool(catalog.get("integridade") == "verificada" and catalog.get("versao") and
                catalog.get("versao") == catalog.get("versao_governada"))


def curated_profile(frame, mapping: dict[str, str]) -> dict[str, Any] | None:
    source = frame.attrs.get("source")
    if not isinstance(source, dict) or source.get("dataset") != "brazil":
        return None
    scope = source.get("scope")
    expected = FIELDS.get(scope)
    if not expected or scope not in FILES:
        return None
    # Os dois arquivos precisam ter colunas corretas e mapeamento canônico.
    if any(column not in frame.columns or mapping.get(role) != column
           for role, column in expected.items()):
        return None
    categories = frame[expected["category"]].dropna().astype(str).str.strip().unique().tolist()
    # Nunca declarar FTS ou uma profissão sem evidência concreta da base.
    if len(categories) != 1 or categories[0].upper() != TRUSTED_CATEGORY:
        return None
    governed = governed_version(frame)
    premises = [{"option": key, "label": item["label"], "origin": item["origin"], "operations": list(item["operations"])}
                for key, item in PREMISES.items()
                if scope in item["scopes"] and (governed or not item.get("governed_version")) and
                (item["origin"] != "VERIFICADA_NOS_DADOS" or _verified(key, frame, expected))]
    return {
        "mapping": dict(expected),
        "category": categories[0],
        "count_unit": "pessoas",
        "confirmed_roles": list(expected),
        "fts_scope_confirmed": True,
        "object_confirmed": True,
        "population_denominator_confirmed": scope == "municipal",
        "scope": scope,
        "premises": premises,
    }


def apply_curated_options(frame, mapping, options, spatial=True):
    """Aplica o perfil governado. spatial=False (cálculo sem distância) omite o referencial e o separador decimal."""
    result = dict(options)
    profile = curated_profile(frame, mapping)
    if not profile:
        return result
    confirmed = result.get("confirmed_roles") or []
    if not isinstance(confirmed, list):
        return result  # contrato principal valida o erro de tipo
    result.update({
        "count_unit": profile["count_unit"],
        "confirmed_roles": list(dict.fromkeys([*confirmed, *profile["confirmed_roles"]])),
        "fts_scope_confirmed": True,
        "object_confirmed": True,
        "population_denominator_confirmed": profile["population_denominator_confirmed"],
    })
    applied = []
    for item in profile["premises"]:
        key = item["option"]
        if key == "component_sum_confirmed" and any(result.get(mode) for mode in AGGREGATION_MODES):
            continue
        if key in SPATIAL_PREMISES and (not spatial or result.get(key)):
            continue  # cálculo sem distância, ou valor informado explicitamente: prevalece o informado
        result[key] = PREMISES[key].get("value", True)
        applied.append(key)
    result["governed_premises"] = applied
    return result


def premise_notes(options, operation) -> list[str]:
    """Notas do resultado para as premissas internas aplicadas a esta análise."""
    applied = options.get("governed_premises") or []
    return [item["note"] for key, item in PREMISES.items() if key in applied and operation in item["operations"]]
