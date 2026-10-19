"""Premissas das análises, aplicadas pelo backend sem confirmação do usuário.

Decisão D1 do responsável pelo produto (19/10/2026): nenhuma confirmação de colunas e campos, em
nenhum nível, nas bases oficial e importada. As antigas declarações ("Confirmo…", "Declaro…",
"Autorizo…") passam a premissas com origem, nota em "Método e limitações" e limitação quando cabível.

Camada única, chamada nos mesmos pontos em que o perfil da base oficial era aplicado:
1. o perfil da base oficial, campo a campo (brazil_catalog_profile.apply_curated_options);
2. as premissas genéricas cuja chave está AUSENTE nas opções e que não vêm do perfil, quando se aplicam
   ao caso (papéis estabelecidos) e, se houver verificação, depois de verificadas nos dados.

Valor explícito da API prevalece: uma premissa enviada como false continua recusada (R3), e a
análise fica bloqueada com o motivo. "analysis_premises" só é gravada quando houver itens (R5).
"""
from __future__ import annotations

from typing import Any

from brazil_catalog_profile import AGGREGATION_MODES, apply_curated_options, premise_notes as profile_notes
from data_contract import needs_population

# Chaves de controle calculadas pelo servidor: nunca aceitas do navegador.
BOOKKEEPING = ("governed_roles", "governed_premises", "analysis_premises")
COUNT_OPERATIONS = ("density", "counts", "distribution", "comparisons", "temporal", "aggregate", "ranking", "report")
ALL_BUT_SPATIAL = (*COUNT_OPERATIONS, "rotation", "nearest", "criteria")

# Premissa → origem, análises em que a nota aparece e nota do resultado.
GENERIC = {
    "population_denominator_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": "population",
        "note": "Denominador: população da mesma linha, no mesmo território e período de cada quantidade (CAP-IND-02); "
                "populações conflitantes continuam bloqueando a análise."},
    "temporal_comparability_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": ("temporal",),
        "note": "Comparabilidade temporal: mesma coluna e unidade em todos os períodos; a base não declara mudança de "
                "definição (premissa da análise)."},
    "territory_longitudinal_confirmed": {
        "origin": "VERIFICADA_NOS_DADOS", "operations": ("temporal", "rotation"),
        "note": "Identidade territorial: verificada nos dados; cada código mantém o mesmo nome em todas as competências.",
        "note_by_name": "Identidade territorial: pelo nome do território, sem código territorial escolhido."},
    "comparison_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": ("comparisons", "ranking"),
        "note": "Comparabilidade entre territórios: mesma coluna de medida, unidade e população para todos os "
                "territórios (premissa da análise)."},
    "population_additive_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": ("aggregate",),
        "note": "Agregação: populações somadas como partes disjuntas do conjunto (premissa da análise); territórios de "
                "níveis relacionados continuam recusados."},
    "component_sum_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": ("aggregate",),
        "note": "Agregação: total como soma dos componentes, com possível dupla contagem (premissa da análise); para "
                "outro total, escolha pessoas distintas pelo identificador individual, quando a base o tiver."},
    "rows_additive_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": COUNT_OPERATIONS,
        "note": "Componentes da contagem somados nas colunas escolhidas como partes da mesma unidade; população "
                "territorial utilizada uma vez (premissa da análise)."},
    "identity_count_confirmed": {
        "origin": "ESCOLHA_DO_USUARIO", "operations": COUNT_OPERATIONS,
        "note": "Contagem: pessoas distintas pelo identificador individual associado."},
    "longitudinal_identity_confirmed": {
        "origin": "ESCOLHA_DO_USUARIO", "operations": ("rotation",),
        "note": "Identidade longitudinal: a mesma pessoa é acompanhada pelo identificador individual associado "
                "(CAP-ROT-01; RQ-DAD-35)."},
    "cohort_coverage_confirmed": {
        "origin": "PREMISSA_DA_ANALISE", "operations": ("rotation",),
        "note": "Coorte: a ausência de registro de uma pessoa no período final conta como saída; unidade sem registro "
                "em um dos períodos fica não avaliável (SEM_REGISTRO_OBSERVADO; CAP-ROT-01)."},
    "fts_scope_confirmed": {
        "origin": "DECLARADA_PELO_USUARIO", "operations": ALL_BUT_SPATIAL,
        "note": "Objeto de análise informado por você; pertença à força de trabalho em saúde não reconhecida pelo "
                "catálogo (CFG-DOM)."},
    # Mesma opção (fts_scope_confirmed), quando o objeto é reconhecido pelo catálogo: registra a origem e mantém o
    # rótulo "profissionais" das bases importadas, antes obtido pela caixa de declaração.
    "fts_scope_recognized": {
        "origin": "REGRA_CONFIGURADA", "operations": ALL_BUT_SPATIAL, "option": "fts_scope_confirmed",
        "note": "Objeto de análise: categorias reconhecidas pelo catálogo da força de trabalho em saúde (CFG-DOM)."},
    "number_format": {
        "origin": "VERIFICADA_NOS_DADOS", "operations": ("spatial", "nearest", "criteria"), "value": "decimal_comma",
        "note": "Separador decimal das coordenadas: vírgula, verificada nos dados; quantidades e populações não têm "
                "vírgula."},
}
LIMITATION = "SOMA_COM_POSSIVEL_DUPLA_CONTAGEM"


def _object_recognized(frame, mapping, options, category_established) -> bool:
    from semantic_bridge import FTS_GOVERNED, normalize
    column = mapping.get("category")
    if category_established and column and column in frame.columns:
        values = frame[column].dropna().astype(str).unique().tolist()
        if values and all(normalize(value) in FTS_GOVERNED for value in values):
            return True
    return normalize(options.get("category_constant", "")) in FTS_GOVERNED


def apply_premises(frame, mapping, options, spatial=True) -> dict[str, Any]:
    """Opções com o perfil oficial e as premissas genéricas aplicadas (sem sobrescrever valor explícito)."""
    if not isinstance(options, dict):
        return options
    result = apply_curated_options(frame, mapping, {key: value for key, value in options.items() if key not in BOOKKEEPING},
                                   spatial=spatial)
    if not isinstance(mapping, dict) or not isinstance(result.get("confirmed_roles") or [], list) or \
            any(not isinstance(column, str) for column in mapping.values()):
        return result  # o contrato principal valida e relata o erro
    from semantic_bridge import established_roles, territories_stable, verified_separator
    roles = established_roles(frame, mapping, result)
    governed = set(result.get("governed_premises") or [])
    applied: list[str] = []

    def apply(key, value=True):
        if key in result or key in governed:
            return  # valor explícito (inclusive false) ou premissa do perfil prevalecem
        result[key] = value
        applied.append(key)

    if "population" in roles:
        apply("population_denominator_confirmed")
    if "period" in roles:
        apply("temporal_comparability_confirmed")
    if "territory" in roles:
        if "period" in roles and "territory_longitudinal_confirmed" not in result and \
                territories_stable(frame, mapping, result):
            apply("territory_longitudinal_confirmed")
        apply("comparison_confirmed")
        if "population" in roles:
            apply("population_additive_confirmed")
        if not any(result.get(mode) for mode in AGGREGATION_MODES):
            apply("component_sum_confirmed")
    parts = result.get("component_columns")
    if isinstance(parts, list) and parts:
        apply("rows_additive_confirmed")
    if "identity" in roles:
        if not mapping.get("count"):
            apply("identity_count_confirmed")
        apply("longitudinal_identity_confirmed")
        apply("cohort_coverage_confirmed")
    informed = str(result.get("object_declaration") or result.get("category_constant") or "").strip()
    recognized = _object_recognized(frame, mapping, result, "category" in roles) if "category" in roles or informed else False
    if informed and not recognized:
        apply("fts_scope_confirmed")
    elif recognized and "fts_scope_confirmed" not in result:
        result["fts_scope_confirmed"] = True
        applied.append("fts_scope_recognized")
    if spatial and {"latitude", "longitude"} <= roles and "number_format" not in result and \
            verified_separator(frame, mapping) == "decimal_comma":
        apply("number_format", GENERIC["number_format"]["value"])
    if applied:
        result["analysis_premises"] = applied
    return result


def _shown(key: str, options: dict, operation: str) -> bool:
    scope = GENERIC[key]["operations"]
    if scope == "population":
        if operation == "nearest":
            return options.get("reference_mode") == "criterion"
        if operation == "criteria":
            from combined_criteria import needs as criteria_needs
            return criteria_needs(options)["population"]
        return needs_population({}, options, operation)
    return operation in scope


def premise_notes(options, operation, mapping=None) -> list[str]:
    """Notas do resultado: premissas do perfil oficial e, em seguida, as premissas genéricas desta análise."""
    notes = profile_notes(options, operation)
    for key in options.get("analysis_premises") or []:
        if key not in GENERIC or not _shown(key, options, operation):
            continue
        item = GENERIC[key]
        by_name = key == "territory_longitudinal_confirmed" and not (mapping or {}).get("territory_id")
        notes.append(item["note_by_name"] if by_name else item["note"])
    return notes


def limitations(options, operation) -> list[str]:
    """Códigos de limitação das premissas aplicadas (SPEC: soma dos componentes sem deduplicação)."""
    applied = {*(options.get("governed_premises") or []), *(options.get("analysis_premises") or [])}
    found = []
    if operation == "aggregate" and "component_sum_confirmed" in applied and options.get("component_sum_confirmed"):
        found.append(LIMITATION)
    if operation in COUNT_OPERATIONS and "rows_additive_confirmed" in applied and options.get("count_unit") == "pessoas":
        found.append(LIMITATION)
    return list(dict.fromkeys(found))
