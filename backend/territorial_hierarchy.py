"""Reconhecimento determinístico dos níveis territoriais, sem inferir aditividade.

A hierarquia descreve a estrutura declarada pelas colunas. Não comprova limites
administrativos externos e não autoriza agregação de profissionais ou população.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


def _key(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).strip().lower())
    plain = "".join(c for c in normalized if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", plain).split())


# A correspondência usa exclusivamente nomes completos, nunca similaridade semântica.
LEVEL_ALIASES = {
    "territorio_analise": {
        "territorio analise", "territorio de analise", "municipio", "municipality",
        "cidade", "city", "distrito", "district",
    },
    "territorio_superior_1": {
        "territorio superior 1", "uf", "unidade federativa", "estado",
        "state", "provincia", "province", "departamento", "department",
    },
    "territorio_superior_2": {
        "territorio superior 2", "regiao geografica", "geographic region",
        "macrorregiao", "macroregiao",
    },
}


def describe_hierarchy(frame: pd.DataFrame, mapping: dict[str, str]) -> dict[str, Any]:
    """Descreve níveis e relações observadas; não altera o DataFrame.

    Quando uma coluna pode representar papéis diferentes, a associação do
    território de análise escolhida pelo usuário prevalece. Níveis superiores
    ambíguos não são selecionados silenciosamente.
    """
    analysis = mapping.get("territory", "")
    if analysis not in frame.columns:
        return {"status": "not_identified", "levels": [], "relations": [],
                "warnings": ["Associe a coluna do território de análise."]}
    levels: list[dict[str, str]] = [
        {"role": "territorio_analise", "column": analysis,
         "label": "Território de análise"}
    ]
    warnings: list[str] = []
    parents: dict[str, str] = {}
    for role in ("territorio_superior_1", "territorio_superior_2"):
        matches = [str(col) for col in frame.columns
                   if col != analysis and _key(col) in LEVEL_ALIASES[role]]
        if len(matches) == 1:
            parents[role] = matches[0]
            levels.append({"role": role, "column": matches[0],
                           "label": ("Território superior 1" if role.endswith("1")
                                     else "Território superior 2")})
        elif len(matches) > 1:
            warnings.append("Há mais de uma candidata a " + role
                            + "; a hierarquia desse nível exige esclarecimento.")
    if "territorio_superior_2" in parents and "territorio_superior_1" not in parents:
        warnings.append("Não é possível estabelecer a relação entre os níveis superiores sem o nível 1.")

    # A relação declarada na planilha exige conferir os registros, não apenas os cabeçalhos.
    relations: list[dict[str, Any]] = []
    identifier = mapping.get("territory_id")
    if identifier not in frame.columns or identifier == analysis:
        identifier = None
    pairs = [
        (analysis, parents.get("territorio_superior_1"), "analise_para_superior_1"),
        (parents.get("territorio_superior_1"), parents.get("territorio_superior_2"),
         "superior_1_para_superior_2"),
    ]
    for child, parent, name in pairs:
        if not child or not parent:
            continue
        cols = [child, parent]
        if child == analysis and identifier:
            cols.insert(0, identifier)
        values = frame[cols].astype("string").apply(lambda s: s.str.strip().replace("", pd.NA))
        complete = values.notna().all(axis=1)
        if not complete.all():
            warnings.append("Há relações territoriais incompletas entre "
                            + child + " e " + parent + ".")
        combinations = values.loc[complete].drop_duplicates()
        group_keys = [identifier, child] if child == analysis and identifier else [child]
        conflicting = int(combinations.groupby(group_keys, dropna=False)[parent].nunique().gt(1).sum())
        if conflicting:
            warnings.append("Foram encontradas relações divergentes entre "
                            + child + " e " + parent + "; revise a identificação territorial.")
        relations.append({
            "relation": name, "child_column": child, "parent_column": parent,
            "distinct_links": int(len(combinations)),
            "conflicting_units": conflicting,
        })
    return {
        "status": ("detected" if parents and not warnings else
                   "review_needed" if warnings else "single_level"),
        "levels": levels,
        "relations": relations,
        "warnings": warnings,
        "aggregation_authorized": False,
    }
