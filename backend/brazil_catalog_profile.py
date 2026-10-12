"""Padrões governados para as duas fontes da base pública Brasil.

Essas associações só são aplicadas à base instalada e íntegra, com estrutura
esperada. Elas não autorizam deduplicação entre municípios ou entre períodos.
Para bases importadas pelo usuário, permanece a confirmação guiada.
"""
from __future__ import annotations

from typing import Any

from brazil_data import FILES


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
    return {
        "mapping": dict(expected),
        "category": categories[0],
        "count_unit": "pessoas",
        "confirmed_roles": list(expected),
        "fts_scope_confirmed": True,
        "object_confirmed": True,
        "population_denominator_confirmed": scope == "municipal",
        "scope": scope,
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
    return result
