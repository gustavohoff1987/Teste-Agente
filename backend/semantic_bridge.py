"""Ponte semântica determinística do protótipo (SPEC v1.2.4: CFG-VOC,
RQ-DAD-05/06/13/15/28/29/36). Não extrapola reconhecimentos de pertença.
Este módulo faz EXAME HABILITADOR: não realiza diagnósticos.
"""
import re
import unicodedata
from typing import Any

import pandas as pd

ROLES = ("territory", "period", "category", "count", "population", "latitude", "longitude", "identity")
ROLE_NAMES = {
    "territory": "Território", "period": "Período", "category": "Categoria",
    "count": "Quantitativo", "population": "População", "latitude": "Latitude",
    "longitude": "Longitude", "identity": "Identificador individual",
}
OPERATIONS = ("density", "counts", "distribution", "comparisons", "temporal",
              "aggregate", "spatial", "ranking", "rotation", "report")
# Baseados nos grupos de cabeçalhos da CFG-VOC §4.4.9; os complementos
# operacionais ficam explícitos e NÃO alteram a configuração normativa.
EXACT = {
    "territory": ("territorio", "unidade territorial", "municipio", "cidade", "estado",
                  "provincia", "distrito", "regiao", "territory", "territorial unit",
                  "municipality", "city", "state", "province", "district", "region",
                  "cod municipio", "codigo municipio", "localidade"),
    "period": ("periodo", "ano", "mes", "data", "competencia", "year", "month", "date", "period"),
    "category": ("categoria", "categoria profissional", "profissao", "ocupacao", "cbo",
                 "category", "professional category", "profession", "occupation"),
    "count": ("quantidade", "contagem", "qtd", "n profissionais", "total profissionais",
              "count", "quantitativo", "quantidade de profissionais"),
    "population": ("populacao", "habitantes", "population", "inhabitants",
                   "populacao estimada"),
    "latitude": ("latitude", "lat"),
    "longitude": ("longitude", "lon", "lng"),
    "identity": ("identificador individual", "id pessoa", "id profissional",
                 "id trabalhador", "identity"),
}
# Exemplos inscritos como propostas, nunca AUTORIZADO_POR_CONFIGURACAO.
# Extrair fragmento de expressão só produz candidato; não declara pertença
# ou identidade de contagem (RQ-CFG-10; RQ-DAD-18).
COUNT_PATTERN = re.compile(
    r"^(?:total|numero|n|quantidade|qtd|contagem)\s+(?:de\s+)?"
    r"(?:profissionais?|medic[oa]s?|enfermeir[oa]s?|trabalhadores?|vinculos?|postos?)"
    r"(?:\s+(?:unicos?|distintos?|ativos?))?$"
)
CATEGORIES = {
    "medicos": "Médicos", "medicas": "Médicas",
    "enfermeiros": "Enfermeiros", "enfermeiras": "Enfermeiras",
    "dentistas": "Dentistas", "farmaceuticos": "Farmacêuticos",
    "fisioterapeutas": "Fisioterapeutas", "psicologos": "Psicólogos",
    "nutricionistas": "Nutricionistas",
}


def normalize(text: Any) -> str:
    value = unicodedata.normalize("NFKD", str(text).strip().lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_headers(frame: pd.DataFrame) -> pd.DataFrame:
    """Iguala os nomes lidos na inspeção e na execução, inclusive 0 numérico.

    Cabeçalhos vazios/duplicados não são silenciosamente recuperados.
    """
    names = [str(col).strip() for col in frame.columns]
    if len(names) != len(set(names)):
        raise ValueError("Há cabeçalhos duplicados após normalização. Renomeie as colunas para identificá-las sem ambiguidade.")
    frame = frame.copy()
    frame.columns = names
    return frame


def candidates(frame: pd.DataFrame) -> tuple[dict[str, str], list[dict[str, Any]]]:
    mapping: dict[str, str] = {}
    columns: list[dict[str, Any]] = []
    suggestions: dict[str, list[dict[str, str]]] = {role: [] for role in ROLES}
    for raw in frame.columns:
        col = str(raw)
        name = normalize(col)
        proposed = []
        for role, aliases in EXACT.items():
            if name in aliases:
                status = "recognized"
                if role in ("latitude", "longitude"):
                    nums = pd.to_numeric(frame[col], errors="coerce")
                    non_null = frame[col].notna()
                    lower, upper = (-90, 90) if role == "latitude" else (-180, 180)
                    if (non_null & (nums.isna() | (nums < lower) | (nums > upper))).any():
                        status = "proposed"
                proposed.append({"role": role, "status": status,
                                 "evidence": "Correspondência por alias governado CFG-VOC"})
        if not proposed and COUNT_PATTERN.fullmatch(name):
            nums = pd.to_numeric(frame[col], errors="coerce")
            if (frame[col].notna() & nums.isna()).any():
                reason = "Cabeçalho sugere contagem, mas contém valores não numéricos"
            else:
                reason = "Padrão lexical de medida quantitativa; unidade e alcance precisam ser declarados"
            proposed.append({"role": "count", "status": "proposed", "evidence": reason})
        for item in proposed:
            suggestions[item["role"]].append({**item, "column": col})
        non_null = frame[col].dropna()
        is_numeric = pd.api.types.is_numeric_dtype(frame[col])
        columns.append({
            "name": col,
            "type": "numérico" if is_numeric else "texto/misto",
            "missing": int(frame[col].isna().sum()),
            "proposal": proposed,
            "suspicious_header": bool(name.isdigit() or name.startswith("unnamed")),
        })
    # Ambiguidade entre candidatos permanece em aberto: não escolhemos por ordem.
    for role, matches in suggestions.items():
        if len(matches) == 1:
            mapping[role] = matches[0]["column"]
    return mapping, columns


def category_from_count_header(column: str) -> str:
    """Sugestão apenas, para o usuário declarar dimensão constante."""
    name = normalize(column)
    if not COUNT_PATTERN.fullmatch(name):
        return ""
    words = name.split()
    hits = [title for token, title in CATEGORIES.items() if token in words]
    return hits[0] if len(hits) == 1 else ""


def preflight(frame: pd.DataFrame, mapping: dict[str, str],
              options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Matriz potencial de aplicabilidade por contrato, sem cálculo substantivo."""
    options = options or {}
    if not isinstance(mapping, dict) or not isinstance(options, dict):
        raise ValueError("Associação de campos inválida.")
    mapped: dict[str, str] = {}
    for role, col in mapping.items():
        if role not in ROLES or not isinstance(col, str):
            raise ValueError("Papel de campo desconhecido na associação.")
        if col:
            if col not in frame.columns:
                raise ValueError("A coluna associada não existe nesta base: " + col)
            mapped[role] = col
    if len(mapped.values()) != len(set(mapped.values())):
        raise ValueError("A mesma coluna não pode representar simultaneamente dois papéis diferentes.")
    _, descriptions = candidates(frame)
    desc = {item["name"]: item for item in descriptions}
    confirmations = options.get("confirmed_roles") or []
    if not isinstance(confirmations, list) or any(x not in ROLES for x in confirmations):
        raise ValueError("Confirmações de campos inválidas.")
    field_states: dict[str, dict] = {}
    for role in ROLES:
        col = mapped.get(role)
        if not col:
            field_states[role] = {"status": "unmapped", "column": "", "message": "Campo não associado"}
            continue
        profiles = [p for p in desc[col]["proposal"] if p["role"] == role]
        automatic = len(profiles) == 1 and profiles[0]["status"] == "recognized"
        state = "confirmed" if role in confirmations else ("recognized" if automatic else "proposed")
        field_states[role] = {
            "status": state, "column": col,
            "message": ("Associado por você" if state == "confirmed"
                        else "Reconhecido por regra configurada" if state == "recognized"
                        else "Confirme a função desta coluna"),
            "evidence": profiles[0]["evidence"] if profiles else "Associação manual",
        }

    def assigned(role: str) -> bool:
        return field_states[role]["status"] in ("recognized", "confirmed")

    def add_reason(reasons: list[str], message: str, needs: bool = False) -> str:
        reasons.append(message)
        return "needs_confirmation" if needs else "unavailable"

    fts = bool(options.get("fts_scope_confirmed")) or assigned("category")
    period = assigned("period") or bool(options.get("single_period_confirmed"))
    measurable = assigned("count") or assigned("identity")
    count_unit = bool(options.get("count_unit")) if assigned("count") else bool(options.get("identity_count_confirmed"))
    population = assigned("population") and bool(options.get("population_denominator_confirmed"))
    territory = assigned("territory")
    period_count = frame[mapped["period"]].dropna().nunique() if assigned("period") else 0
    territory_count = frame[mapped["territory"]].dropna().nunique() if territory else 0
    valid_units = {"pessoas", "vinculos", "postos", "outro"}
    if options.get("count_unit", "") not in ("", *valid_units):
        raise ValueError("Unidade de contagem não reconhecida.")
    if options.get("category_constant") and not options.get("fts_scope_confirmed"):
        fts = False  # texto livre não estabelece pertinência
    cap: dict[str, dict[str, Any]] = {}
    for op in OPERATIONS:
        missing: list[str] = []
        pending: list[str] = []
        if not measurable:
            missing.append("Associe uma coluna de quantitativos ou de identificador individual.")
        elif not count_unit:
            pending.append("Informe a unidade de contagem e sua identidade antes da análise.")
        if not fts:
            pending.append("Estabeleça a categoria profissional ou declare o domínio FTS desta base.")
        if not period:
            pending.append("Associe Período ou confirme que a base possui um período único.")
        if not territory and op not in ("counts", "temporal", "report"):
            missing.append("Esta análise exige dimensão territorial reconhecida ou confirmada.")
        if op in ("density", "comparisons", "ranking", "aggregate"):
            if not assigned("population"):
                missing.append("Associe a coluna de população correspondente.")
            elif not population:
                pending.append("Confirme a definição e o alinhamento do denominador populacional.")
        if op == "report" and assigned("population") and not population:
            # Relatório de quantitativos sem interpretar denominador não confirmado.
            pass
        if op in ("comparisons", "ranking", "aggregate", "distribution") and territory and territory_count < 2:
            missing.append("São necessários pelo menos dois territórios para esta operação.")
        if op == "distribution" and territory and territory_count >= 2:
            pass
        if op == "temporal":
            if not assigned("period") or period_count < 2:
                missing.append("Evolução temporal exige ao menos dois períodos reconhecidos.")
            elif not bool(options.get("temporal_comparability_confirmed")):
                pending.append("Confirme a comparabilidade dos períodos e a convenção temporal.")
            if territory and not bool(options.get("territory_longitudinal_confirmed")):
                pending.append("Confirme a identidade territorial ao longo do tempo.")
        if op == "rotation":
            if not assigned("identity"):
                missing.append("Rotatividade exige um identificador individual da mesma pessoa.")
            elif not bool(options.get("longitudinal_identity_confirmed")):
                pending.append("Confirme identidade pessoal e escopo longitudinal entre períodos.")
            if not assigned("period") or period_count < 2:
                missing.append("Rotatividade exige pelo menos dois períodos.")
            if territory and not bool(options.get("territory_longitudinal_confirmed")):
                pending.append("Confirme a comparabilidade territorial entre períodos.")
        if op == "spatial":
            # Não depende de quantitativos, mas exige geometria e escopo.
            missing = [x for x in missing if not x.startswith("Associe uma coluna de quantitativos")]
            pending = [x for x in pending if not x.startswith("Informe a unidade de contagem")]
            for role in ("latitude", "longitude"):
                if not assigned(role):
                    missing.append("Associe e valide " + ROLE_NAMES[role] + ".")
            if not options.get("crs"):
                pending.append("Informe o referencial geodésico das coordenadas.")
            elif options.get("crs") != "SIRGAS2000":
                missing.append("O referencial indicado não é suportado nesta versão.")
            if not options.get("reference_territory"):
                pending.append("Selecione o território de referência.")
        if op == "aggregate" and not options.get("no_overlap_confirmed"):
            # Soma de componentes é possível com rótulo explícito; não implica pessoas únicas.
            pass
        if op == "report" and not territory:
            # Relatório de totais da base pode operar sem recorte espacial.
            pass
        if missing:
            status = "unavailable"
        elif pending:
            status = "needs_confirmation"
        else:
            status = "available"
        cap[op] = {"status": status, "reasons": missing + pending}
    return {"capabilities": cap, "field_states": field_states, "profile": {
        "row_count": len(frame), "column_count": len(frame.columns),
        "recognized_roles": sum(s["status"] in ("recognized", "confirmed") for s in field_states.values()),
    }}
