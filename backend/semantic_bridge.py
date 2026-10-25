"""Ponte semântica determinística do protótipo (SPEC v1.2.4: CFG-VOC,
RQ-DAD-05/06/13/15/28/29/36). Não extrapola reconhecimentos de pertença.
Este módulo faz EXAME HABILITADOR: não realiza diagnósticos.

Sem confirmações de colunas e campos (decisão D1 do responsável pelo produto, 19/10/2026): um papel
fica estabelecido por regra conclusiva (REGRA_CONFIGURADA), pelo perfil da base oficial, campo a
campo (PERFIL_GOVERNADO), ou pela escolha do usuário no seletor (ESCOLHA_DO_USUARIO, enviada em
"confirmed_roles"). Uma sugestão nunca entra no mapeamento: o seletor fica vazio e a sugestão aparece
no topo da lista. Coluna indicada sem regra e sem escolha continua bloqueada.
"""
import re
import unicodedata
from typing import Any

import numpy as np
import pandas as pd
from territorial_hierarchy import describe_hierarchy
from data_contract import (ChoiceRequired, multiplicity, scoped, text_values,
                           validate_operation, period_positions, prepare, needs_population, dimensions, count_unit_label, canonical_crs,
                           SUPPORTED_CRS, source_crs_conflict)

ROLES = ("territory", "territory_id", "period", "category", "count", "population", "latitude", "longitude", "identity")
ROLE_NAMES = {
    "territory": "Território", "period": "Período", "category": "Categoria",
    "count": "Quantitativo", "population": "População", "latitude": "Latitude",
    "longitude": "Longitude", "identity": "Identificador individual",
    "territory_id": "Código identificador territorial",
}
from analysis_catalog import ENGINE_OPERATION_LABELS
from request_memo import per_source
OPERATIONS = tuple(ENGINE_OPERATION_LABELS)
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


# Formato decimal único para coordenadas (RQ-DAD-25): números com ponto (ou inteiros), ou decimais só com vírgula.
COMMA_NUMBER = r"[-+]?\d+,\d+"
INTEGER = r"[-+]?\d+"
COORDINATE_LIMITS = {"latitude": 90, "longitude": 180}
GEOGRAPHIC_HINTS = ("regiao geografica", "regiao de saude", "unidade federativa", "uf", "geographic region",
                    "administrative region")


def coordinate_format(series: pd.Series) -> str | None:
    """Formato dos valores de uma coluna de coordenadas: "decimal_comma", "decimal_point", "integer" (sem separador)
    ou None quando há valor não numérico, não finito ou mistura de vírgula e ponto. Coluna vazia conta como "integer"."""
    values = series.dropna()
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(values, errors="coerce")
        return "decimal_point" if np.isfinite(numeric.to_numpy(dtype="float64")).all() else None
    text = values.astype(str).str.strip()
    text = text[text != ""].drop_duplicates()
    if text.empty:
        return "integer"
    comma = text.str.contains(",", regex=False)
    if comma.any():
        # Vírgula decimal: os demais valores só podem ser inteiros (ponto ou expoente misturados são ambíguos).
        if text[comma].str.fullmatch(COMMA_NUMBER).all() and text[~comma].str.fullmatch(INTEGER).all():
            return "decimal_comma"
        return None
    numeric = pd.to_numeric(text, errors="coerce")
    if numeric.isna().any() or not np.isfinite(numeric.to_numpy(dtype="float64")).all():
        return None
    return "integer" if text.str.fullmatch(INTEGER).all() else "decimal_point"


def _out_of_range(series: pd.Series, role: str, fmt: str) -> int:
    source = series.dropna().astype(str).str.strip()
    if fmt == "decimal_comma":
        source = source.str.replace(",", ".", regex=False)
    values = pd.to_numeric(source, errors="coerce")
    return int((values.abs() > COORDINATE_LIMITS[role]).sum())


def _proposals(frame: pd.DataFrame, col: str, roles: tuple[str, ...] = ROLES) -> list[dict[str, Any]]:
    """Propostas de papel para uma coluna; "recognized" só por regra conclusiva."""
    name = normalize(col)
    proposed = []
    derived = next((item for item in frame.attrs.get("derived_fields", []) if item["column"] == col), None)
    if derived and derived["role"] in roles:
        # Composição determinística e validada na importação (dataset_normalization.compose_period). Uma coluna de
        # período já existente e reconhecida pelo nome prevalece: a composição fica como sugestão.
        existing = [other for other in frame.columns if other != col and normalize(other) in EXACT[derived["role"]]]
        proposed.append({"role": derived["role"], "status": "proposed" if existing else "recognized",
                         "evidence": "Composição AAAAMM de " + " × 100 + ".join(derived["source_columns"]) +
                                     ", valores validados" + ("; a base já tem outra coluna de período" if existing else "")})
    for role, aliases in EXACT.items():
        if role not in roles or name not in aliases:
            continue
        status = "recognized"
        evidence = ("Alias operacional do catálogo Brasil" if name in ("pais", "country", "cod ibge", "codigo ibge")
                    else "Correspondência por alias governado CFG-VOC")
        if role == "territory_id":
            # Nome do campo e repetição de códigos não bastam para estabelecer o código (SPEC L1327).
            status, evidence = "proposed", "Sugestão: escolha a coluna do código para usá-la"
        elif role in COORDINATE_LIMITS:
            fmt = coordinate_format(frame[col])
            if fmt is None:
                status = "proposed"
                evidence = "Nome de coordenada, mas os valores não estão num formato decimal único; escolha a coluna para usá-la"
            else:
                invalid = _out_of_range(frame[col], role, fmt)
                evidence += "; valores numéricos em graus decimais" + (
                    f"; {invalid} valor(es) fora do intervalo ficam não avaliáveis por elemento" if invalid else "")
        proposed.append({"role": role, "status": status, "evidence": evidence})
    # Expressões territoriais compostas: hipótese, nunca vínculo autoritativo.
    if not proposed and "territory" in roles and name in GEOGRAPHIC_HINTS:
        proposed.append({"role": "territory", "status": "proposed",
                         "evidence": "Expressão geográfica sugerida; escolha a coluna para usá-la como unidade territorial"})
    if not proposed and "count" in roles and COUNT_PATTERN.fullmatch(name):
        nums = pd.to_numeric(frame[col], errors="coerce")
        if (frame[col].notna() & nums.isna()).any():
            reason = "Cabeçalho sugere contagem, mas contém valores não numéricos"
        else:
            reason = "Padrão lexical de medida quantitativa; escolha a coluna e a unidade de contagem para usá-la"
        proposed.append({"role": "count", "status": "proposed", "evidence": reason})
    return proposed


@per_source()  # perfis das colunas da base Brasil: os mesmos em toda requisição da versão
def candidates(frame: pd.DataFrame) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Mapeamento só com o reconhecido por regra conclusiva; sugestões ficam nos perfis das colunas."""
    mapping: dict[str, str] = {}
    columns: list[dict[str, Any]] = []
    suggestions: dict[str, list[dict[str, str]]] = {role: [] for role in ROLES}
    for raw in frame.columns:
        col = str(raw)
        name = normalize(col)
        proposed = _proposals(frame, col)
        for item in proposed:
            suggestions[item["role"]].append({**item, "column": col})
        is_numeric = pd.api.types.is_numeric_dtype(frame[col])
        columns.append({
            "name": col,
            "type": "numérico" if is_numeric else "texto/misto",
            "missing": int(frame[col].isna().sum()),
            "proposal": proposed,
            "suspicious_header": bool(name.isdigit() or name.startswith("unnamed")),
        })
    # Ambiguidade entre candidatos permanece em aberto: não escolhemos por ordem.
    # Uma sugestão (proposta) nunca entra no mapeamento: o seletor fica vazio (D1).
    for role, matches in suggestions.items():
        recognized = [m for m in matches if m["status"] == "recognized"]
        if len(recognized) == 1:
            mapping[role] = recognized[0]["column"]
    return mapping, columns


def suggested_columns(profiles: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Colunas sugeridas por papel (reconhecidas ou propostas), para o topo de cada seletor."""
    result: dict[str, list[str]] = {}
    for profile in profiles:
        for item in profile["proposal"]:
            result.setdefault(item["role"], [])
            if profile["name"] not in result[item["role"]]:
                result[item["role"]].append(profile["name"])
    return result


def role_recognized(frame: pd.DataFrame, mapping: dict[str, str], role: str) -> bool:
    """Regra conclusiva para a coluna associada ao papel (mesma regra de candidates())."""
    column = mapping.get(role)
    if not isinstance(column, str) or not column or column not in frame.columns:
        return False
    profiles = _proposals(frame, column, (role,))
    return len(profiles) == 1 and profiles[0]["status"] == "recognized"


def _listed(options: dict[str, Any], key: str) -> set[str]:
    value = options.get(key) or []
    return set(value) if isinstance(value, list) else set()


def role_established(frame: pd.DataFrame, mapping: dict[str, str], options: dict[str, Any] | None, role: str) -> bool:
    """O papel tem coluna associada e foi escolhido pelo usuário, é do perfil oficial ou é reconhecido por regra."""
    options = options or {}
    column = (mapping or {}).get(role)
    if role not in ROLES or not isinstance(column, str) or not column or column not in frame.columns:
        return False
    return role in _listed(options, "confirmed_roles") or role in _listed(options, "governed_roles") or \
        role_recognized(frame, mapping, role)


def established_roles(frame: pd.DataFrame, mapping: dict[str, str], options: dict[str, Any] | None) -> set[str]:
    """Papéis estabelecidos por regra conclusiva, pelo perfil da base oficial ou pela escolha do usuário.

    A escolha continua a chegar em "confirmed_roles" (contrato da API) e o perfil, em "governed_roles"."""
    return {role for role in (mapping or {}) if role_established(frame, mapping, options, role)}


def coordinate_roles(frame: pd.DataFrame, mapping: dict[str, str], options: dict[str, Any] | None) -> set[str]:
    """Papéis de coordenada estabelecidos (escolha, perfil oficial ou nome do CFG-VOC com formato decimal único).
    Valor fora do intervalo não rebaixa a coluna: o elemento fica não avaliável (RQ-DAD-25)."""
    roles = {role: mapping.get(role) for role in COORDINATE_LIMITS if mapping.get(role)}
    return established_roles(frame, roles, options)


def verified_separator(frame: pd.DataFrame, mapping: dict[str, str]) -> str | None:
    """Separador decimal das coordenadas verificado nos dados: "decimal_comma" quando as coordenadas usam vírgula e
    quantidades e populações não têm vírgula; "decimal_point" quando usam ponto ou só inteiros; None se misto."""
    formats = set()
    for role in COORDINATE_LIMITS:
        column = mapping.get(role)
        if not column or column not in frame.columns:
            return None
        formats.add(coordinate_format(frame[column]))
    if None in formats:
        return None
    separators = formats - {"integer"}
    if len(separators) > 1:
        return None
    if "decimal_comma" in separators:
        for role in ("count", "population"):
            column = mapping.get(role)
            if column and column in frame.columns and \
                    frame[column].dropna().astype(str).str.contains(",", regex=False).any():
                return None
        return "decimal_comma"
    return "decimal_point"


def territories_stable(frame: pd.DataFrame, mapping: dict[str, str], options: dict[str, Any] | None) -> bool:
    """Identidade territorial ao longo do tempo verificada nos dados: com código estabelecido, cada código mantém um
    único nome em todas as competências; sem código, a identidade é a do próprio nome."""
    name_col, code_col = mapping.get("territory"), mapping.get("territory_id")
    if not name_col or name_col not in frame.columns:
        return False
    if not code_col or not role_established(frame, mapping, options, "territory_id"):
        return True
    pairs = frame[[name_col, code_col]].dropna().astype(str).apply(lambda col: col.str.strip()).drop_duplicates()
    return not pairs.empty and int(pairs.groupby(code_col)[name_col].nunique().max()) == 1


def category_from_count_header(column: str) -> str:
    """Sugestão apenas, para o usuário declarar dimensão constante."""
    name = normalize(column)
    if not COUNT_PATTERN.fullmatch(name):
        return ""
    words = name.split()
    hits = [title for token, title in CATEGORIES.items() if token in words]
    return hits[0] if len(hits) == 1 else ""


ORIGIN_MESSAGES = {
    "PERFIL_GOVERNADO": "Reconhecido pelo perfil da base oficial",
    "REGRA_CONFIGURADA": "Reconhecido por regra configurada",
    "ESCOLHA_DO_USUARIO": "Escolhido por você",
}
# Rótulos das premissas da análise (aplicadas pelo backend, sem confirmação; ver analysis_premises.py).
PREMISE_LABELS = {
    "population_denominator_confirmed": "do denominador populacional (população da mesma linha, território e período)",
    "temporal_comparability_confirmed": "de comparabilidade temporal (mesma coluna e unidade em todos os períodos)",
    "territory_longitudinal_confirmed": "de identidade territorial ao longo do tempo",
    "comparison_confirmed": "de comparabilidade entre territórios (mesma medida, unidade e população)",
    "population_additive_confirmed": "de populações somadas como partes disjuntas",
    "component_sum_confirmed": "de soma dos componentes",
    "rows_additive_confirmed": "de soma das partes da contagem",
    "identity_count_confirmed": "de contagem de pessoas distintas pelo identificador individual associado",
    "longitudinal_identity_confirmed": "de identidade longitudinal pelo identificador individual associado",
    "cohort_coverage_confirmed": "de cobertura da coorte nos dois períodos",
    "fts_scope_confirmed": "de pertença do objeto informado à força de trabalho em saúde",
}


def premise_reason(options: dict[str, Any], key: str) -> str:
    """Texto neutro de premissa não aplicada; por R3, recusa só acontece com valor falso explícito na API."""
    label = PREMISE_LABELS.get(key, key)
    if options.get(key) is False:
        return "A premissa " + label + " foi recusada nas opções desta solicitação."
    return "A premissa " + label + " não está aplicada nesta solicitação."


CHOICE_PREFIXES = ("Escolha", "Informe", "Selecione", "Remova", "Defina", "Associe", "A premissa")
STEP_ZERO = re.compile(r"coluna (?:de |do |da )?(?:território|territorial|código|período|categoria)|coluna territorial|"
                       r"objeto de análise|código territorial|único período")


def requirement_meta(status: str, message: str) -> dict[str, Any]:
    """Classificação do requisito para a interface (R4): escolha do usuário ou impedimento nos dados, e etapa."""
    kind = "escolha" if status == "needs_confirmation" or message.startswith(CHOICE_PREFIXES) else "dados"
    return {"kind": kind, "step": 0 if STEP_ZERO.search(message.lower()) else 1}


def _coordinate_layer():
    """Identidade da camada de coordenadas lida pela análise espacial: compõe a chave do pré-exame memorizado."""
    from geo_complement import state  # importação tardia: o módulo usa o contrato de dados
    current = state()
    return current.get("sha256") or current.get("estado")


@per_source(extra=_coordinate_layer)  # base Brasil: mesma versão, mesmo pedido, mesmo pré-exame
def preflight(frame: pd.DataFrame, mapping: dict[str, str],
              options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Matriz potencial de aplicabilidade por contrato, sem cálculo substantivo."""
    options = {} if options is None else options
    if not isinstance(mapping, dict) or not isinstance(options, dict):
        raise ValueError("Associação de campos inválida.")
    for key, value in options.items():
        if (key.endswith("_confirmed") or key == "require_object_confirmation") and not isinstance(value, bool):
            raise ValueError("Premissas e escolhas devem ser valores booleanos, não texto.")
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
        raise ValueError("Escolhas de campos inválidas.")
    governed_roles = _listed(options, "governed_roles")
    field_states: dict[str, dict] = {}
    for role in ROLES:
        col = mapped.get(role)
        if not col:
            field_states[role] = {"status": "unmapped", "column": "", "message": "Campo não associado"}
            continue
        profiles = [p for p in desc[col]["proposal"] if p["role"] == role]
        automatic = len(profiles) == 1 and profiles[0]["status"] == "recognized"
        origin = ("PERFIL_GOVERNADO" if role in governed_roles else "ESCOLHA_DO_USUARIO" if role in confirmations
                  else "REGRA_CONFIGURADA" if automatic else None)
        state = "confirmed" if origin == "ESCOLHA_DO_USUARIO" else "recognized" if origin else "proposed"
        field_states[role] = {
            "status": state, "column": col, "origin": origin or "SUGESTAO_NAO_ESCOLHIDA",
            "message": ORIGIN_MESSAGES[origin] if origin else "Sugestão não escolhida: escolha a coluna no seletor",
            "evidence": profiles[0]["evidence"] if profiles else "Coluna indicada sem regra de reconhecimento",
        }

    def assigned(role: str) -> bool:
        return field_states[role]["status"] in ("recognized", "confirmed")

    declared_fts = bool(options.get("fts_scope_confirmed"))
    categorical_values = (frame[mapped["category"]].dropna().astype(str).unique().tolist()
                          if assigned("category") else [])
    fts_from_column = bool(categorical_values) and all(normalize(value) in FTS_GOVERNED
                                                       for value in categorical_values)
    fts_from_constant = normalize(options.get("category_constant", "")) in FTS_GOVERNED
    informed = str(options.get("object_declaration") or options.get("category_constant") or "").strip()
    # O objeto de análise é o texto informado pelo usuário; sem confirmação (D1). Recusa explícita da premissa prevalece.
    informed_object = bool(informed) and options.get("fts_scope_confirmed") is not False
    fts = declared_fts or fts_from_column or fts_from_constant or informed_object
    object_state = ({"status": "reconhecido", "origin": "PERFIL_GOVERNADO"} if "category" in governed_roles and declared_fts
                    else {"status": "reconhecido", "origin": "REGRA_CONFIGURADA"} if fts_from_column or fts_from_constant
                    else {"status": "informado", "origin": "DECLARADA_PELO_USUARIO"} if informed_object or declared_fts
                    else {"status": "ausente", "origin": None})
    period = assigned("period") or bool(options.get("single_period_confirmed"))
    measurable = bool(mapped.get("count") or mapped.get("identity"))
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
                {**options, "single_period_confirmed": True, "fts_scope_confirmed": True,
                 "confirmed_roles": [*confirmations, "territory_id"]}).territory.nunique()
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
    longitudinal_unverified = None  # verificação da identidade territorial, só quando a premissa não foi aplicada

    def longitudinal_reason() -> tuple[str, str]:
        nonlocal longitudinal_unverified
        if options.get("territory_longitudinal_confirmed") is False:
            return "pending", premise_reason(options, "territory_longitudinal_confirmed")
        if longitudinal_unverified is None:
            longitudinal_unverified = not territories_stable(frame, mapped, options)
        if longitudinal_unverified:
            return "missing", ("Identidade territorial ao longo do tempo não verificada: há códigos com nomes diferentes "
                               "entre períodos.")
        return "pending", premise_reason(options, "territory_longitudinal_confirmed")

    prepared_cache = {}  # Somente nesta requisição; nenhuma base persiste no servidor.
    for op in OPERATIONS:
        missing: list[str] = []
        pending: list[str] = []
        consumed = {"territory", "territory_id"}
        # Referência mais próxima por critério de densidade consome também as dimensões do critério.
        criterion = op == "nearest" and options.get("reference_mode") == "criterion"
        if op == "criteria":  # papéis exigidos pelas condições, ordenações e referências efetivamente definidas
            from combined_criteria import needs as criteria_needs  # importação tardia: o módulo usa esta ponte
            uses = criteria_needs(options)
            criterion = uses["count"]
            consumed.update(("period", "category"))
            consumed.update(role for role, used in (("latitude", uses["spatial"]), ("longitude", uses["spatial"]),
                                                    ("count", uses["count"]), ("population", uses["population"])) if used)
        elif op in ("spatial", "nearest"):
            consumed.update(("latitude", "longitude"))
            if criterion:
                consumed.update(("period", "category", "count", "population"))
        else:
            consumed.update(("period", "category"))
            consumed.add("identity" if op == "rotation" or not mapped.get("count") else "count")
            if op != "rotation" and needs_population(mapped, options, op):
                consumed.add("population")
        for role in ROLES:
            if role in consumed and mapped.get(role) and not assigned(role):
                pending.append("Escolha a coluna de " + ROLE_NAMES[role] + " no seletor: a coluna indicada não foi "
                               "reconhecida nem escolhida.")
        if op not in ("spatial", "rotation", "nearest", "criteria") or criterion:
            if not measurable:
                missing.append("Escolha a coluna de quantitativos (ou o identificador individual).")
            if measurable and not count_unit:
                pending.append("Escolha a unidade de contagem: pessoas, vínculos, postos ou outra." if mapped.get("count")
                               else premise_reason(options, "identity_count_confirmed"))
            if count_invalid:
                missing.append("Há valores quantitativos ausentes, negativos ou não numéricos; corrija a base ou a associação.")
        if territory_missing:
            missing.append("Há valores ausentes na coluna territorial associada.")
        if period_missing and op != "spatial":
            missing.append("Há valores ausentes na coluna temporal associada.")
        if category_missing and (op not in ("spatial", "nearest", "criteria") or criterion):
            missing.append("Há valores ausentes na categoria associada.")
        if not fts and (op not in ("spatial", "nearest", "criteria") or criterion):
            pending.append(premise_reason(options, "fts_scope_confirmed") if informed else
                           "Informe o objeto de análise: a profissão ou o conjunto de trabalhadores da força de trabalho em saúde.")
        if not period and op != "spatial":
            pending.append("Escolha a coluna de Período ou a opção «A base tem um único período».")
        if not territory and (op not in ("counts", "temporal", "report") or needs_population(mapped, options, op)):
            missing.append("Escolha a coluna territorial: esta análise compara territórios.")
        if needs_population(mapped, options, op):
            if not assigned("population"):
                missing.append("Escolha a coluna de população correspondente.")
            elif not population:
                pending.append(premise_reason(options, "population_denominator_confirmed"))
        if op in ("comparisons", "ranking", "aggregate", "distribution") and territory and territory_count < 2:
            missing.append("São necessários pelo menos dois territórios para esta operação.")
        if op == "temporal":
            if options.get("period_filter"):
                missing.append("Remova o filtro de período para comparar dois ou mais períodos.")
            elif not assigned("period") or period_count < 2:
                missing.append("Evolução temporal exige ao menos dois períodos reconhecidos.")
            elif not period_numeric:
                missing.append("Referências temporais inválidas. Use anos, competências AAAAMM, datas ISO ou escolha uma escala numérica inequívoca.")
            elif not bool(options.get("temporal_comparability_confirmed")):
                pending.append(premise_reason(options, "temporal_comparability_confirmed"))
            if territory and not bool(options.get("territory_longitudinal_confirmed")):
                kind, message = longitudinal_reason()
                (missing if kind == "missing" else pending).append(message)
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
                pending.append(premise_reason(options, "longitudinal_identity_confirmed"))
            if not assigned("period") or period_count < 2:
                missing.append("Rotatividade exige pelo menos dois períodos.")
            if territory and not bool(options.get("territory_longitudinal_confirmed")):
                kind, message = longitudinal_reason()
                (missing if kind == "missing" else pending).append(message)
        if op == "spatial":
            # Geometria pode ser base auxiliar sem quantitativos/categorias/períodos.
            for role in ("latitude", "longitude"):
                if not assigned(role):
                    missing.append("Escolha a coluna de " + ROLE_NAMES[role] + " (graus decimais).")
            if coordinate_invalid:
                missing.append("Há coordenadas ausentes, não numéricas ou fora dos intervalos válidos.")
            if not options.get("crs"):
                pending.append("Escolha o referencial geodésico das coordenadas; nenhum referencial é presumido.")
            elif not canonical_crs(options.get("crs")):
                missing.append("O referencial indicado não é suportado nesta versão (somente " + SUPPORTED_CRS + ").")
            elif source_crs_conflict(frame, canonical_crs(options["crs"])):
                missing.append(source_crs_conflict(frame, canonical_crs(options["crs"])))
            if not options.get("reference_territory"):
                pending.append("Selecione o território de referência.")
        if op == "nearest" or (op == "criteria" and uses["spatial"]):
            # Referencial, período e referências são verificados por nearest_inputs (validate_operation).
            for role in ("latitude", "longitude"):
                if not assigned(role):
                    missing.append("Escolha a coluna de " + ROLE_NAMES[role] + " (graus decimais).")
        if not missing:
            try:
                prepared = None
                if op not in ("spatial", "rotation", "nearest", "criteria"):
                    cache_key = needs_population(mapped, options, op)
                    if cache_key not in prepared_cache:
                        try:
                            prepared_cache[cache_key] = prepare(frame, mapped, options, op)
                        except (ValueError, TypeError) as exc:
                            prepared_cache[cache_key] = exc
                    prepared = prepared_cache[cache_key]
                    if isinstance(prepared, Exception):
                        raise prepared
                # Referências independem do recorte dos alvos: "nearest" e "criteria" veem a base inteira.
                validate_operation(original_frame if op in ("nearest", "criteria") else frame, mapped, options, op, prepared=prepared)
            except ChoiceRequired as exc:
                if str(exc) not in pending:
                    pending.append(str(exc))
            except (ValueError, TypeError) as exc:
                missing.append(str(exc))
        if missing:
            status = "unavailable"
        elif pending:
            status = "needs_confirmation"  # valor do contrato: "escolha pendente"
        else:
            status = "available"
        # Lista de requisitos da própria matriz; não duplicar critérios no React.
        checks: list[dict[str, Any]] = []
        def met(title: str, detail: str) -> None:
            checks.append({"status": "met", "title": title, "detail": detail})
        if territory and not territory_missing and op not in ("counts", "temporal", "report"):
            met("Unidade territorial", "A unidade territorial foi associada a um campo válido.")
        if period and not period_missing and op != "spatial":
            met("Referência temporal", "Há uma referência temporal identificada para os dados.")
        if fts and op != "spatial":
            met("Objeto de análise", "A profissão ou conjunto de trabalhadores está identificado.")
        if op not in ("spatial", "rotation") and measurable and assigned("count" if mapped.get("count") else "identity") and \
                count_unit and not count_invalid and not row_key_collision and not missing and not pending:
            met("Quantitativo de profissionais", "A medida e a unidade de contagem estão definidas para esta estrutura.")
        if op in ("density", "comparisons", "ranking", "aggregate") and population and not missing and not pending:
            met("Dados populacionais", "A coluna de população foi estabelecida e o denominador está alinhado por território e período.")
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
            met("Comparabilidade temporal", "Premissas de comparação entre os períodos aplicadas (ver “Método e limitações”).")
        if (op in ("spatial", "nearest") or (op == "criteria" and uses["spatial"])) and assigned("latitude") and assigned("longitude") and not coordinate_invalid and not missing:
            met("Coordenadas", "Latitude e longitude foram identificadas e verificadas.")
        if (op in ("spatial", "nearest") or (op == "criteria" and uses["spatial"])) and canonical_crs(options.get("crs")):
            met("Referencial geodésico", "SIRGAS 2000, premissa governada da base Brasil oficial." if "crs" in (
                options.get("governed_premises") or []) else "O referencial informado é suportado nesta versão.")
        if op == "rotation" and assigned("identity") and (
                options.get("longitudinal_identity_confirmed")) and not identity_missing:
            met("Identidade longitudinal", "O identificador individual associado acompanha a mesma pessoa entre os períodos.")
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
                elif "objeto de análise" in message or "objeto informado" in message or "profissão" in message or "força de trabalho" in message:
                    title = "Objeto de análise"
                elif "contagem" in message or "quantitativ" in message or "identificador" in message:
                    title = "Dados e medida dos profissionais"
                elif "coordenad" in message.lower() or "Latitude" in message or "Longitude" in message:
                    title = "Coordenadas geográficas"
                elif "geodésico" in message:
                    title = "Referencial geodésico"
                elif op in ("nearest", "criteria") and "referênc" in message.lower():
                    title = "Referências territoriais"
                else:
                    title = "Condição para esta análise"
                checks.append({"status": kind, "title": title, "detail": message, **requirement_meta(kind, message)})
        cap[op] = {"status": status, "reasons": missing + pending, "requirements": checks}
    def values(role: str) -> list[str]:
        if role == "territory" and assigned(role) and assigned("territory_id"):
            return (text_values(original_frame[mapped[role]]) + " [" + text_values(original_frame[mapped["territory_id"]]) + "]").dropna().unique().tolist()
        return text_values(original_frame[mapped[role]]).dropna().unique().tolist() if assigned(role) else []
    from territorial_selection import territory_catalog
    try:
        territory_choices = territory_catalog(original_frame, mapped, options)
        selection_reason = ""
    except ValueError as exc:
        territory_choices, selection_reason = [], str(exc)
    premises = [key for key in [*(options.get("governed_premises") or []), *(options.get("analysis_premises") or [])]
                if isinstance(key, str)]
    # Separador decimal das coordenadas verificado nos dados (null: formato misto, a escolha continua com o usuário);
    # vazio quando não se aplica ou quando as coordenadas são do perfil oficial.
    coordinate_separator = ""
    if assigned("latitude") and assigned("longitude") and not {"latitude", "longitude"} <= governed_roles:
        coordinate_separator = verified_separator(original_frame, mapped)
    return {"capabilities": cap, "field_states": field_states,
            "object": object_state, "premises": premises, "coordinate_separator": coordinate_separator,
            "territory_choices": territory_choices, "selection_reason": selection_reason,
            "territorial_hierarchy": describe_hierarchy(original_frame, mapped, options.get("hierarchy_columns")),
            "multiplicity": multiplicity(frame, mapped, options),
            "values": {"territories": values("territory"), "periods": values("period"),
                       "categories": values("category")},
            "profile": {
                "row_count": len(frame), "column_count": len(frame.columns),
                "recognized_roles": sum(s["status"] in ("recognized", "confirmed") for s in field_states.values()),
            }}
