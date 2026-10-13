"""Universos explícitos, locais à requisição. Não deduz aditividade ou pessoas únicas."""
import re

import pandas as pd

from brazil_catalog_profile import curated_profile
from territorial_hierarchy import describe_hierarchy, distinct_raw
from request_memo import per_request


# Regra governada apenas para a fonte municipal Brasil. Códigos de seis dígitos
# preservados tal como fornecidos (sem inventar o dígito verificador).
# Fonte: https://www.ibge.gov.br/explica/codigos-dos-municipios.php
STATES = {
    "11": ("RO", "Rondônia"), "12": ("AC", "Acre"), "13": ("AM", "Amazonas"),
    "14": ("RR", "Roraima"), "15": ("PA", "Pará"), "16": ("AP", "Amapá"),
    "17": ("TO", "Tocantins"), "21": ("MA", "Maranhão"), "22": ("PI", "Piauí"),
    "23": ("CE", "Ceará"), "24": ("RN", "Rio Grande do Norte"), "25": ("PB", "Paraíba"),
    "26": ("PE", "Pernambuco"), "27": ("AL", "Alagoas"), "28": ("SE", "Sergipe"),
    "29": ("BA", "Bahia"), "31": ("MG", "Minas Gerais"), "32": ("ES", "Espírito Santo"),
    "33": ("RJ", "Rio de Janeiro"), "35": ("SP", "São Paulo"), "41": ("PR", "Paraná"),
    "42": ("SC", "Santa Catarina"), "43": ("RS", "Rio Grande do Sul"),
    "50": ("MS", "Mato Grosso do Sul"), "51": ("MT", "Mato Grosso"),
    "52": ("GO", "Goiás"), "53": ("DF", "Distrito Federal"),
}


@per_request
def texts(series):
    return series.astype("string").str.strip().replace("", pd.NA)


@per_request
def territory_catalog(frame, mapping, options):
    name_col, code_col = mapping.get("territory"), mapping.get("territory_id")
    if not name_col or name_col not in frame:
        raise ValueError("Seleção territorial exige uma coluna de territórios associada.")
    if code_col and "territory_id" not in options.get("confirmed_roles", []):
        raise ValueError("Confirme o identificador territorial antes de selecionar unidades.")
    columns = [name_col] + ([code_col] if code_col else [])
    # Os níveis dependem só dos nomes das colunas; as relações são conferidas nos pares abaixo.
    hierarchy = describe_hierarchy(frame.head(0), mapping, options.get("hierarchy_columns"))
    parents = [level["column"] for level in hierarchy["levels"] if level["role"] != "territorio_analise"]
    # Deduplicar antes de normalizar (quando o resultado não muda) evita converter cada registro.
    pairs = distinct_raw(frame, list(dict.fromkeys(columns + parents))).copy()
    for col in pairs:
        pairs[col] = texts(pairs[col])
    pairs = pairs.drop_duplicates()
    if pairs[columns].isna().any().any():
        raise ValueError("Há nomes ou identificadores territoriais ausentes; esclareça a identidade antes da seleção.")
    key_col = code_col or name_col
    if pairs.groupby(key_col)[name_col].nunique().gt(1).any():
        raise ValueError("Identificador territorial ambíguo: o mesmo código identifica nomes diferentes.")
    conflicts = set()
    if parents:
        divergences = pairs.groupby(key_col)[parents].nunique().gt(1).any(axis=1)
        conflicts = set(divergences[divergences].index)
        if conflicts and not code_col:
            raise ValueError("Identificação territorial ambígua entre níveis superiores. Associe um código inequívoco ou corrija a hierarquia.")
    profile = curated_profile(frame, mapping)
    brazil = bool(profile and profile["scope"] == "municipal")
    items = []
    # Registros simples: iterrows copiaria frame.attrs a cada unidade territorial.
    for row in pairs.drop_duplicates(key_col).to_dict("records"):
        code = str(row[code_col]) if code_col else ""
        name = str(row[name_col])
        state = STATES.get(code[:2]) if brazil and re.fullmatch(r"\d{6,7}", code) else None
        conflict = str(row[key_col]) in conflicts
        if conflict:
            state = None
        label = name + (" [" + code + "]" if code else "")
        items.append({"id": ("code:" + code if code else "name:" + name),
                      "name": name, "code": code, "label": label,
                      "parents": [str(row[c]) for c in parents if pd.notna(row[c])],
                      "selection_reason": "Relações territoriais divergentes na fonte; esclareça a hierarquia desta unidade." if conflict else "",
                      "state": state[0] if state else "", "state_name": state[1] if state else ""})
    return sorted(items, key=lambda item: (item["name"], item["id"]))


def selected_frame(frame, mapping, options):
    """Omissão preserva a API antiga; lista vazia explícita nunca significa todos."""
    if "territory_ids" not in options:
        return frame
    ids = options["territory_ids"]
    if (not isinstance(ids, list) or not ids or len(ids) > 10000 or
            any(not isinstance(v, str) or not v or len(v) > 512 for v in ids) or
            len(ids) != len(set(ids))):
        raise ValueError("Seleção territorial deve conter identificadores distintos e não pode ser vazia.")
    catalog = territory_catalog(frame, mapping, options)
    known = {item["id"] for item in catalog}
    unknown = [value for value in ids if value not in known]
    if unknown:
        raise ValueError("Municípios/territórios inexistentes ou incompatíveis com a base: " + ", ".join(unknown[:8]))
    ambiguous = [item["label"] for item in catalog if item["id"] in ids and item["selection_reason"]]
    if ambiguous:
        raise ValueError("Identificação territorial ambígua entre níveis superiores: " + ", ".join(ambiguous[:8]))
    code = mapping.get("territory_id")
    keys = ("code:" if code else "name:") + texts(frame[code or mapping["territory"]])
    return frame.loc[keys.isin(ids)].copy()


def selection_coverage(frame, mapping, options):
    """Não deixa desaparecer silenciosamente um membro após filtros de categoria/tempo."""
    if "territory_ids" not in options:
        return
    present = {item["id"] for item in territory_catalog(frame, mapping, options)}
    missing = set(options["territory_ids"]) - present
    if missing:
        raise ValueError("Não avaliável: seleção sem registros na categoria/período solicitado: " + ", ".join(sorted(missing)))


def universe_metadata(frame, mapping, options):
    if not mapping.get("territory"):
        return {"kind": "global", "members": [], "classification_scope": "base sem dimensão territorial"}
    try:
        members = territory_catalog(frame, mapping, options)
    except ValueError:
        if "territory_ids" in options:
            raise
        return {"kind": "observed", "members": [], "classification_scope": "universo observado; identidade não confirmada"}
    return {"kind": "selection" if "territory_ids" in options else "observed", "members": members,
            "classification_scope": "subconjunto selecionado" if "territory_ids" in options else "universo observado",
            "state_rule": "brasil-cod-uf-prefix-1" if any(x["state"] for x in members) else None}


def validate_selected_levels(frame, mapping, options):
    if "territory_ids" not in options:
        return
    members = territory_catalog(frame, mapping, options)
    names = {item["name"] for item in members}
    if any(names.intersection(item["parents"]) for item in members):
        raise ValueError("Unidades territoriais não comparáveis: a seleção contém território e nível superior relacionado. Separe os níveis antes de comparar ou agregar.")
