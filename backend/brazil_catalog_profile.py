"""Padrões governados para as duas fontes da base pública Brasil.

Essas associações só são aplicadas à base instalada e íntegra, com estrutura
esperada. Elas não autorizam deduplicação entre municípios ou entre períodos.
Para bases importadas pelo usuário, permanece a confirmação guiada.

Na base oficial, as premissas de comparabilidade que o usuário confirmava são internas
(decisão do responsável pelo produto em 18/10/2026). Cada uma vale por regra governada deste
perfil ou somente depois de verificada nos dados; o resultado registra a origem de cada uma.
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
# conferência em _territories_stable; sem ela, a confirmação volta a ser pedida ao usuário.
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
}
# Outro modo de agregação escolhido explicitamente prevalece sobre a soma dos componentes.
AGGREGATION_MODES = ("no_overlap_confirmed", "identity_union_confirmed")
# Verificação por versão da base: a versão (SHA-256 das fontes) fixa o conteúdo conferido.
_STABILITY: dict[tuple, bool] = {}


def _territories_stable(frame, expected: dict[str, str]) -> bool:
    """Cada território mantém um único nome em todas as competências (municipal: por código IBGE)."""
    version = (frame.attrs.get("source") or {}).get("version")
    key = (tuple(expected.items()), version, len(frame))
    if version and key in _STABILITY:
        return _STABILITY[key]
    name_col, code_col = expected["territory"], expected.get("territory_id")
    if not code_col:  # recorte nacional: um único território
        stable = frame[name_col].dropna().astype(str).str.strip().nunique() == 1
    else:
        pairs = distinct_raw(frame, [name_col, code_col])
        codes = pairs[code_col].astype(str).str.strip()
        stable = not pairs.empty and not pairs.isna().any().any() and \
            int(pairs[name_col].astype(str).str.strip().groupby(codes).nunique().max()) == 1
    if version:
        _STABILITY[key] = stable
    return stable


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
    stable = _territories_stable(frame, expected)
    premises = [{"option": key, "label": item["label"], "origin": item["origin"], "operations": list(item["operations"])}
                for key, item in PREMISES.items()
                if scope in item["scopes"] and (item["origin"] != "VERIFICADA_NOS_DADOS" or stable)]
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


def apply_curated_options(frame, mapping, options):
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
        if item["option"] == "component_sum_confirmed" and any(result.get(mode) for mode in AGGREGATION_MODES):
            continue
        result[item["option"]] = True
        applied.append(item["option"])
    result["governed_premises"] = applied
    return result


def premise_notes(options, operation) -> list[str]:
    """Notas do resultado para as premissas internas aplicadas a esta análise."""
    applied = options.get("governed_premises") or []
    return [item["note"] for key, item in PREMISES.items() if key in applied and operation in item["operations"]]
