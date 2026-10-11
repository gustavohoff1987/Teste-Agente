"""Ponte semântica determinística do protótipo (SPEC v1.2.4: CFG-VOC,
RQ-DAD-05/06/13/15/28/29/36). Não extrapola reconhecimentos de pertença.
Este módulo faz EXAME HABILITADOR: não realiza diagnósticos.
"""
import re
import unicodedata
from typing import Any

import pandas as pd
from territorial_hierarchy import describe_hierarchy
from data_contract import (ConfirmationRequired, multiplicity, scoped, text_values,
                           validate_operation, period_positions, prepare, needs_population, dimensions, count_unit_label, canonical_crs)

ROLES = ("territory", "territory_id", "period", "category", "count", "population", "latitude", "longitude", "identity")
ROLE_NAMES = {
    "territory": "Território", "period": "Período", "category": "Categoria",
    "count": "Quantitativo", "population": "População", "latitude": "Latitude",
    "longitude": "Longitude", "identity": "Identificador individual",
    "territory_id": "Código identificador territorial",
}
from analysis_catalog import OPERATION_LABELS
OPERATIONS = tuple(OPERATION_LABELS)
# Baseados nos grupos de cabeçalhos da CFG-VOC §4.4.9; os complementos
# operacionais ficam explícitos e NÃO alteram a configuração normativa.
EXACT = {
    "territory": ("territorio", "unidade territorial", "municipio", "territorio analise", "territorio de analise", "cidade", "estado",
                  "provincia", "distrito", "regiao", "territory", "territorial unit",
                  "municipality", "city", "state", "province", "district", "region",
                  "cod municipio", "codigo municipio", "localidade", "pais", "country"),
    "period": ("periodo", "ano", "mes", "data", "competencia", "year", "month", "date", "period"),
    "territory_id": ("ibge", "cod ibge", "codigo ibge", "codigo territorial", "codigo identificador", "codigo identificador territorial", "territory code", "municipality code", "geocode"),
    "category": ("categoria", "categoria profissional", "categoria profisional", "profissao", "ocupacao", "cbo",
                 "category", "professional category", "profession", "occupation"),
    "count": ("quantidade", "contagem", "qtd", "n profissionais", "total profissionais",
              "count", "quantitativo", "quantidade de profissionais"),
    "population": ("populacao", "habitantes", "population", "inhabitants",
                   "populacao estimada"),
    "latitude": ("latitude", "lat", "nu latitude"),
    "longitude": ("longitude", "lon", "lng", "nu longitude"),
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
# Reconhecimento FTS_INEQUIVOCA: aliases integrais de CFG-DOM §4.3;
# categorias contextuais não são aceitas automaticamente.
FTS_GOVERNED = {
    "medico", "medica", "medicos", "medicas", "medicina", "profissional medico", "profissional medica",
    "physician", "physicians", "medical doctor", "medical doctors", "medicine",
    "enfermeiro", "enfermeira", "enfermeiros", "enfermeiras", "enfermagem",
    "nurse", "nurses", "nursing",
    "dentista", "dentistas", "cirurgiao dentista", "cirurgia dentista",
    "cirurgioes dentistas", "odontologo", "odontologa", "odontologia",
    "dentist", "dentists", "dentistry",
    "farmaceutico", "farmaceutica", "farmaceuticos", "farmaceuticas", "farmacia",
    "pharmacist", "pharmacists", "pharmacy",
    "fisioterapeuta", "fisioterapeutas", "fisioterapia", "physiotherapist", "physiotherapists",
    "physical therapist", "physical therapists", "physiotherapy", "physical therapy",
    "terapeuta ocupacional", "terapeutas ocupacionais", "terapia ocupacional",
    "occupational therapist", "occupational therapists", "occupational therapy",
    "fonoaudiologo", "fonoaudiologa", "fonoaudiologos", "fonoaudiologas", "fonoaudiologia",
    "speech therapist", "speech therapists", "speech language pathologist", "speech language pathologists",
    "speech language pathology", "speech therapy",
    "nutricionista", "nutricionistas", "nutricao", "nutritionist", "nutritionists", "nutrition",
    "biomedico", "biomedica", "biomedicos", "biomedicas", "biomedicina",
    "tecnico de enfermagem", "tecnica de enfermagem", "tecnicos de enfermagem",
    "tecnicas de enfermagem", "nursing technician", "nursing technicians",
    "auxiliar de enfermagem", "auxiliares de enfermagem", "nursing assistant", "nursing assistants",
    "tecnico em radiologia", "tecnica em radiologia", "tecnico de radiologia",
    "tecnica de radiologia", "radiology technician", "radiology technicians",
    "radiologic technologist", "radiologic technologists",
    "agente comunitario de saude", "agentes comunitarios de saude", "acs",
    "community health worker", "community health workers",
    "agente de combate as endemias", "agentes de combate as endemias", "ace",
    "endemic disease control agent", "endemic disease control agents",
    "psicologo", "psicologa", "psicologos", "psicologas", "psicologia",
    "psychologist", "psychologists", "psychology",
}
# Em cabeçalhos compostos, nomes de profissões são apenas candidatos.
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
        derived = next((item for item in frame.attrs.get("derived_fields", [])
                        if item["column"] == col), None)
        if derived:
            proposed.append({"role": derived["role"], "status": "proposed",
                             "evidence": "Período AAAAMM composto de " + " e ".join(derived["source_columns"]) + "; confirme a referência temporal"})
        for role, aliases in EXACT.items():
            if name in aliases:
                status = "proposed" if role == "territory_id" else "recognized"
                if role in ("latitude", "longitude"):
                    nums = pd.to_numeric(frame[col], errors="coerce")
                    non_null = frame[col].notna()
                    lower, upper = (-90, 90) if role == "latitude" else (-180, 180)
                    if (non_null & (nums.isna() | (nums < lower) | (nums > upper))).any():
                        status = "proposed"
                proposed.append({"role": role, "status": status,
                                 "evidence": ("Alias operacional do catálogo Brasil" if name in ("pais", "country", "cod ibge", "codigo ibge")
                                              else "Correspondência por alias governado CFG-VOC")})
        # Expressões territoriais compostas: hipótese, nunca vínculo autoritativo.
        if not proposed and name in ("regiao geografica", "regiao de saude",
                                     "unidade federativa", "uf", "geographic region",
                                     "administrative region"):
            proposed.append({"role": "territory", "status": "proposed",
                             "evidence": "Expressão geográfica candidata; confirme a unidade que deseja analisar"})
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
        elif len([m for m in matches if m["status"] == "recognized"]) == 1:
            mapping[role] = next(m["column"] for m in matches if m["status"] == "recognized")
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
    options = {} if options is None else options
    if not isinstance(mapping, dict) or not isinstance(options, dict):
        raise ValueError("Associação de campos inválida.")
    for key, value in options.items():
        if (key.endswith("_confirmed") or key == "require_object_confirmation") and not isinstance(value, bool):
            raise ValueError("Confirmações devem ser valores booleanos, não texto.")
    original_frame = frame
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
    frame = scoped(frame, mapped, options)
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

    declared_fts = bool(options.get("fts_scope_confirmed"))
    categorical_values = (frame[mapped["category"]].dropna().astype(str).unique().tolist()
                          if assigned("category") else [])
    fts_from_column = bool(categorical_values) and all(normalize(value) in FTS_GOVERNED
                                                       for value in categorical_values)
    fts_from_constant = normalize(options.get("category_constant", "")) in FTS_GOVERNED
    fts = declared_fts or fts_from_column or fts_from_constant
    period = assigned("period") or bool(options.get("single_period_confirmed"))
    measurable = bool(mapped.get("count") or mapped.get("identity"))
    count_confirmed = assigned("count") if mapped.get("count") else assigned("identity")
    count_unit = bool(options.get("count_unit")) if mapped.get("count") else bool(options.get("identity_count_confirmed"))
    if options.get("count_unit") == "outro" and not str(options.get("custom_count_unit", "")).strip():
        count_unit = False
    population = assigned("population") and bool(options.get("population_denominator_confirmed"))
    territory = assigned("territory")
    period_count = frame[mapped["period"]].dropna().nunique() if assigned("period") else 0
    territory_count = frame[mapped["territory"]].dropna().nunique() if territory else 0
    if territory and assigned("territory_id"):
        try:
            identity_mapping = {r: c for r, c in mapped.items() if r in ("territory", "territory_id")}
            territory_count = dimensions(frame, identity_mapping,
                {**options, "single_period_confirmed": True, "fts_scope_confirmed": True}).territory.nunique()
        except ValueError:
            pass  # O contrato compartilhado relata a causa específica abaixo.
    valid_units = {"pessoas", "vinculos", "postos", "outro"}
    if options.get("count_unit", "") not in ("", *valid_units):
        raise ValueError("Unidade de contagem não reconhecida.")
    cap: dict[str, dict[str, Any]] = {}
    count_invalid = False  # Valores e multiplicidade são verificados pelo contrato compartilhado.
    row_key_collision = False
    territory_missing = assigned("territory") and bool(frame[mapped["territory"]].isna().any())
    period_missing = assigned("period") and bool(frame[mapped["period"]].isna().any())
    category_missing = assigned("category") and bool(frame[mapped["category"]].isna().any())
    identity_missing = assigned("identity") and bool(frame[mapped["identity"]].isna().any())
    coordinate_invalid = False
    period_numeric = False
    if assigned("period") and period_count > 0:
        try:
            period_positions(text_values(frame[mapped["period"]]).dropna(), options.get("period_convention", "auto"))
            period_numeric = True
        except ValueError:
            pass
    all_period_count = frame[mapped["period"]].dropna().nunique() if assigned("period") else 0
    all_category_count = frame[mapped["category"]].dropna().nunique() if assigned("category") else 0

    prepared_cache = {}  # Somente nesta requisição; nenhuma base persiste no servidor.
    for op in OPERATIONS:
        missing: list[str] = []
        pending: list[str] = []
        consumed = {"territory", "territory_id"}
        if op == "spatial":
            consumed.update(("latitude", "longitude"))
        else:
            consumed.update(("period", "category"))
            consumed.add("identity" if op == "rotation" or not mapped.get("count") else "count")
            if op != "rotation" and needs_population(mapped, options, op):
                consumed.add("population")
        for role in ROLES:
            if role in consumed and mapped.get(role) and not assigned(role):
                pending.append("Confirme a associação de " + ROLE_NAMES[role] + " à coluna selecionada antes de utilizá-la nesta análise.")
        if op not in ("spatial", "rotation"):
            if not measurable:
                missing.append("Associe uma coluna de quantitativos ou de identificador individual.")
            elif not count_confirmed:
                pending.append("Confirme a função de quantitativo/identificador da coluna sugerida.")
            if measurable and not count_unit:
                pending.append("Informe a unidade de contagem e sua identidade antes da análise.")
            if count_invalid:
                missing.append("Há valores quantitativos ausentes, negativos ou não numéricos; corrija a base ou a associação.")
        if territory_missing:
            missing.append("Há valores ausentes na coluna territorial associada.")
        if period_missing and op != "spatial":
            missing.append("Há valores ausentes na coluna temporal associada.")
        if category_missing and op != "spatial":
            missing.append("Há valores ausentes na categoria associada.")
        if not fts and op != "spatial":
            pending.append("Confirme a profissão ou o conjunto de trabalhadores que será analisado e sua relação com a força de trabalho na saúde.")
        if options.get("require_object_confirmation") and not options.get("object_confirmed") and op != "spatial":
            pending.append("Confirme o objeto de análise apresentado pelo sistema.")
        if not period and op != "spatial":
            pending.append("Associe Período ou confirme que a base possui um período único.")
        if not territory and (op not in ("counts", "temporal", "report") or needs_population(mapped, options, op)):
            missing.append("Esta análise exige dimensão territorial reconhecida ou confirmada.")
        if needs_population(mapped, options, op):
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
            if options.get("period_filter"):
                missing.append("Remova o filtro de período para comparar dois ou mais períodos.")
            elif not assigned("period") or period_count < 2:
                missing.append("Evolução temporal exige ao menos dois períodos reconhecidos.")
            elif not period_numeric:
                missing.append("Referências temporais inválidas. Use anos, competências AAAAMM, datas ISO ou declare uma escala numérica inequívoca.")
            elif not bool(options.get("temporal_comparability_confirmed")):
                pending.append("Confirme a comparabilidade dos períodos e a convenção temporal.")
            if territory and not bool(options.get("territory_longitudinal_confirmed")):
                pending.append("Confirme a identidade territorial ao longo do tempo.")
        if op == "aggregate":
            if all_period_count > 1 and not options.get("period_filter"):
                pending.append("Selecione um período nos filtros para agregar sem somar anos distintos.")
            if all_category_count > 1 and not options.get("category_filter"):
                pending.append("Selecione uma categoria nos filtros antes da agregação.")
        if op == "rotation":
            if options.get("period_filter"):
                missing.append("Remova o filtro de período e escolha os períodos inicial e final da coorte.")
            if identity_missing:
                missing.append("Há identificadores pessoais ausentes; esta coorte não é avaliável.")
            if not assigned("identity"):
                missing.append("Rotatividade exige um identificador individual da mesma pessoa.")
            elif not bool(options.get("longitudinal_identity_confirmed")):
                pending.append("Confirme identidade pessoal e escopo longitudinal entre períodos.")
            if not assigned("period") or period_count < 2:
                missing.append("Rotatividade exige pelo menos dois períodos.")
            if territory and not bool(options.get("territory_longitudinal_confirmed")):
                pending.append("Confirme a comparabilidade territorial entre períodos.")
        if op == "spatial":
            # Geometria pode ser base auxiliar sem quantitativos/categorias/períodos.
            for role in ("latitude", "longitude"):
                if not assigned(role):
                    missing.append("Associe e valide " + ROLE_NAMES[role] + ".")
            if coordinate_invalid:
                missing.append("Há coordenadas ausentes, não numéricas ou fora dos intervalos válidos.")
            if not options.get("crs"):
                pending.append("Informe o referencial geodésico das coordenadas.")
            elif not canonical_crs(options.get("crs")):
                missing.append("O referencial indicado não é suportado nesta versão.")
            if not options.get("reference_territory"):
                pending.append("Selecione o território de referência.")
        if op == "aggregate" and not options.get("no_overlap_confirmed"):
            # Soma de componentes é possível com rótulo explícito; não implica pessoas únicas.
            pass
        if op == "report" and not territory:
            # Relatório de totais da base pode operar sem recorte espacial.
            pass
        if not missing:
            try:
                prepared = None
                if op not in ("spatial", "rotation"):
                    cache_key = needs_population(mapped, options, op)
                    if cache_key not in prepared_cache:
                        try:
                            prepared_cache[cache_key] = prepare(frame, mapped, options, op)
                        except (ValueError, TypeError) as exc:
                            prepared_cache[cache_key] = exc
                    prepared = prepared_cache[cache_key]
                    if isinstance(prepared, Exception):
                        raise prepared
                validate_operation(frame, mapped, options, op, prepared=prepared)
            except ConfirmationRequired as exc:
                if str(exc) not in pending:
                    pending.append(str(exc))
            except (ValueError, TypeError) as exc:
                missing.append(str(exc))
        if missing:
            status = "unavailable"
        elif pending:
            status = "needs_confirmation"
        else:
            status = "available"
        # Lista de requisitos da própria matriz; não duplicar critérios no React.
        checks: list[dict[str, str]] = []
        def met(title: str, detail: str) -> None:
            checks.append({"status": "met", "title": title, "detail": detail})
        if territory and not territory_missing and op not in ("counts", "temporal", "report"):
            met("Unidade territorial", "A unidade territorial foi associada a um campo válido.")
        if period and not period_missing and op != "spatial":
            met("Referência temporal", "Há uma referência temporal identificada para os dados.")
        if fts and op != "spatial" and (
                not options.get("require_object_confirmation") or options.get("object_confirmed")):
            met("Objeto de análise", "A profissão ou conjunto de trabalhadores está identificado.")
        if op not in ("spatial", "rotation") and measurable and count_confirmed and count_unit and (
                not count_invalid and not row_key_collision) and not missing and not pending:
            met("Quantitativo de profissionais", "A medida e a unidade de contagem estão definidas para esta estrutura.")
        if op in ("density", "comparisons", "ranking", "aggregate") and population and not missing and not pending:
            met("Dados populacionais", "O denominador correspondente foi associado e declarado.")
        if op == "distribution":
            indicator = options.get("distribution_indicator")
            if indicator in ("density", "quantity"):
                met("Indicador da distribuição", "Densidade por 1.000 habitantes" if indicator == "density"
                    else "Quantidade de " + count_unit_label(mapped, options))
            if options.get("period_filter") or all_period_count == 1:
                met("Período da distribuição", "As unidades serão classificadas em um único período.")
            if options.get("category_filter") or all_category_count == 1:
                met("Categoria profissional", "Os quintis serão calculados para uma única categoria.")
        if op == "temporal" and assigned("period") and period_count >= 2 and period_numeric and (
                options.get("temporal_comparability_confirmed")) and (
                not territory or options.get("territory_longitudinal_confirmed")):
            met("Comparabilidade temporal", "Foram declaradas condições de comparação entre os períodos.")
        if op == "spatial" and assigned("latitude") and assigned("longitude") and not coordinate_invalid and not missing:
            met("Coordenadas", "Latitude e longitude foram identificadas e verificadas.")
        if op == "spatial" and canonical_crs(options.get("crs")):
            met("Referencial geodésico", "O referencial informado é suportado pelo motor experimental.")
        if op == "rotation" and assigned("identity") and (
                options.get("longitudinal_identity_confirmed")) and not identity_missing:
            met("Identidade longitudinal", "O uso longitudinal da identidade individual foi declarado.")
        for kind, reasons in (("missing", missing), ("needs_confirmation", pending)):
            for message in reasons:
                if "indicador" in message.lower():
                    title = "Indicador da análise"
                elif "populaç" in message or "denominador" in message:
                    title = "Dados populacionais"
                elif "territori" in message.lower() or "Território" in message:
                    title = "Unidade territorial"
                elif "períod" in message.lower() or "temporal" in message.lower():
                    title = "Referência e comparabilidade temporal"
                elif "objeto de análise" in message or "profissão" in message or "força de trabalho" in message:
                    title = "Objeto de análise"
                elif "contagem" in message or "quantitativ" in message or "identificador" in message:
                    title = "Dados e medida dos profissionais"
                elif "coordenad" in message.lower() or "Latitude" in message or "Longitude" in message:
                    title = "Coordenadas geográficas"
                elif "geodésico" in message:
                    title = "Referencial geodésico"
                else:
                    title = "Condição para esta análise"
                checks.append({"status": kind, "title": title, "detail": message})
        cap[op] = {"status": status, "reasons": missing + pending, "requirements": checks}
    def values(role: str) -> list[str]:
        if role == "territory" and assigned(role) and assigned("territory_id"):
            return (text_values(original_frame[mapped[role]]) + " [" + text_values(original_frame[mapped["territory_id"]]) + "]").dropna().unique().tolist()
        return text_values(original_frame[mapped[role]]).dropna().unique().tolist() if assigned(role) else []
    return {"capabilities": cap, "field_states": field_states,
            "territorial_hierarchy": describe_hierarchy(original_frame, mapped, options.get("hierarchy_columns")),
            "multiplicity": multiplicity(frame, mapped, options),
            "values": {"territories": values("territory"), "periods": values("period"),
                       "categories": values("category")},
            "profile": {
                "row_count": len(frame), "column_count": len(frame.columns),
                "recognized_roles": sum(s["status"] in ("recognized", "confirmed") for s in field_states.values()),
            }}
