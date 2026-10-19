"""Contratos estruturais compartilhados pelo exame e pelo cálculo, sem LLM.

RQ-DAD-18/29/35/36: nomes não implicam identidade, soma ou unidade.
As transformações são locais à requisição. Papéis de coluna valem por regra conclusiva, pelo perfil
oficial ou pela escolha do usuário; as antigas declarações são premissas aplicadas pelo backend
(analysis_premises.py), e um valor falso explícito na API continua recusando a premissa.
"""
import re
from itertools import islice

import numpy as np
import pandas as pd
from territorial_selection import selected_frame, selection_coverage, validate_selected_levels
from request_memo import per_request


class ChoiceRequired(ValueError):
    """Escolha pendente do usuário (coluna, parâmetro ou opção) ou premissa recusada explicitamente."""


# Nome antigo mantido por compatibilidade: vários módulos e testes o importam.
ConfirmationRequired = ChoiceRequired


def _established(frame, mapping, options, role):
    from semantic_bridge import role_established  # importação tardia: a ponte usa este contrato
    return role_established(frame, mapping, options, role)


def _premise(options, key):
    from semantic_bridge import premise_reason  # importação tardia: a ponte usa este contrato
    return premise_reason(options, key)


@per_request  # a mesma coluna é normalizada uma vez por requisição; resultado só lido
def text_values(series):
    # Coluna só de textos: cada valor distinto é normalizado uma vez e o resultado é o mesmo.
    # Com números ou outros tipos não: 130260 e 130260.0 coincidem na deduplicação, mas não como texto.
    if series.dtype == object and pd.api.types.infer_dtype(series, skipna=True) in ("string", "empty"):
        codes, uniques = pd.factorize(series, use_na_sentinel=True)
        normalized = _normalized_text(pd.Series(uniques, dtype=object))
        return pd.Series(normalized.array.take(codes, allow_fill=True), index=series.index, name=series.name)
    return _normalized_text(series)


def _normalized_text(series):
    return series.astype("string").str.strip().replace("", pd.NA)


def numbers(series, label, options):
    source = text_values(series)
    if options.get("number_format") == "decimal_comma":
        # Sem separadores de milhares: uma vírgula tem significado declarado.
        source = source.str.replace(",", ".", regex=False)
    result = pd.to_numeric(source, errors="coerce")
    if (source.notna() & (result.isna() | ~np.isfinite(result))).any():
        raise ValueError(f"Há valores não numéricos ou não finitos em {label}. Confira o formato decimal e a coluna selecionada.")
    if label in ("quantidade", "população") and result.lt(0).any():
        raise ValueError(f"Há valores negativos em {label}.")
    return result.astype(float)


@per_request  # chamadores só leem o recorte; nenhum o altera in place
def scoped(frame, mapping, options):
    frame = selected_frame(frame, mapping, options).copy()
    selected_periods = options.get("period_filters") or []
    if selected_periods:
        if (not isinstance(selected_periods, list) or
                len(selected_periods) > 80 or
                not all(isinstance(v, str) and 0 < len(v) <= 64 for v in selected_periods) or
                len(set(selected_periods)) != len(selected_periods) or
                options.get("period_filter")):
            raise ValueError("Escolha uma lista de períodos distintos sem combinar com o filtro individual.")
        col = mapping.get("period")
        if not col:
            raise ValueError("Seleção de períodos exige uma referência temporal válida.")
        available = set(text_values(frame[col]).dropna().tolist())
        if any(period not in available for period in selected_periods):
            raise ValueError("A seleção contém período não disponível na base atual.")
        frame = frame[text_values(frame[col]).isin(selected_periods)]
    for role in ("period", "category"):
        value = options.get(role + "_filter")
        if value:
            col = mapping.get(role)
            if not col:
                raise ValueError("O filtro exige a associação da dimensão correspondente.")
            frame = frame[text_values(frame[col]) == str(value).strip()]
    if frame.empty:
        raise ValueError("Nenhum registro corresponde aos filtros selecionados.")
    selection_coverage(frame, mapping, options)
    return frame


def dimensions(frame, mapping, options, allow_global=False):
    data = pd.DataFrame(index=frame.index)
    for role, fallback in (("territory", "Base inteira (sem dimensão territorial)"),
                           ("period", "Período declarado"),
                           ("category", options.get("category_constant") or "FTS declarada")):
        col = mapping.get(role)
        if col:
            data[role] = text_values(frame[col])
        else:
            if role == "territory" and not allow_global:
                raise ValueError("Associe a unidade territorial.")
            if role == "period" and not options.get("single_period_confirmed"):
                raise ChoiceRequired("Escolha a coluna de Período ou a opção «A base tem um único período».")
            if role == "category" and not (options.get("category_constant") or options.get("fts_scope_confirmed")):
                raise ChoiceRequired("Informe o objeto de análise: a profissão ou o conjunto de trabalhadores da força de "
                                     "trabalho em saúde.")
            data[role] = fallback
    if data.isna().any().any():
        raise ValueError("Há valores ausentes ou vazios nas dimensões associadas; corrija a base ou selecione um recorte completo.")
    id_col = mapping.get("territory_id")
    if id_col:
        if not mapping.get("territory"):
            raise ValueError("Associe também o nome da unidade territorial correspondente ao código.")
        if not _established(frame, mapping, options, "territory_id"):
            raise ChoiceRequired("Escolha a coluna do código territorial no seletor; a coluna indicada não foi escolhida "
                                 "nem reconhecida pelo perfil oficial.")
        codes = text_values(frame[id_col])
        if codes.isna().any():
            raise ValueError("Há códigos territoriais ausentes ou vazios.")
        pairs = pd.DataFrame({"code": codes, "name": data.territory})
        if pairs.groupby("code").name.nunique().gt(1).any():
            raise ValueError("O mesmo código territorial está associado a nomes diferentes. Corrija ou esclareça a correspondência antes de usar esse identificador.")
        # Nome legível e código opaco; nenhum nível, país ou dígito é inventado.
        data["territory"] = data.territory + " [" + codes + "]"
    return data


KEYS = ["territory", "period", "category"]


def multiplicity(frame, mapping, options):
    """Somente exemplos agregados de dimensões autorizadas, nunca identidades."""
    df = scoped(frame, mapping, options)
    keys = [mapping[r] for r in KEYS if mapping.get(r)]
    code = mapping.get("territory_id")
    if code and _established(frame, mapping, options, "territory_id"):
        keys = [code if c == mapping.get("territory") else c for c in keys]
    normalized = df.copy()
    for col in keys:
        normalized[col] = text_values(df[col])
    collision = normalized.duplicated(keys, keep=False) if keys else pd.Series(len(df) > 1, index=df.index)
    multiple = normalized[collision]
    examples = []
    if keys and not multiple.empty:
        grouped = multiple.groupby(keys, dropna=False)
        group_count = grouped.ngroups
        for key, group in islice(grouped, 5):
            # Não retorna valores arbitrários de outras colunas nem identificadores pessoais.
            key = key if isinstance(key, tuple) else (key,)
            examples.append({"dimensions": {c: str(v) for c, v in zip(keys, key)}, "records": len(group)})
        distinguishing = [c for c in df.columns if c not in keys and c != mapping.get("identity")
                          and grouped[c].nunique().gt(1).any()]
    else:
        group_count = int(bool(len(multiple)))
        distinguishing = []
    exact = int(df.duplicated().sum())
    return {"affected_records": int(collision.sum()), "groups": group_count,
            "exact_duplicate_excess": exact, "distinguishing_columns": distinguishing,
            "examples": examples, "key_columns": keys}


def count_unit_label(mapping, options):
    if not mapping.get("count"):
        return "pessoas distintas"
    unit = options.get("count_unit")
    return (options.get("custom_count_unit", "").strip() if unit == "outro"
            else {"pessoas": "pessoas", "vinculos": "vínculos", "postos": "postos"}.get(unit, "unidades declaradas"))


def canonical_crs(value):
    """CFG-MET D24: somente aliases enumerados, sem inferir EPSG ou separadores."""
    if isinstance(value, str) and value.strip().upper() in (
            "SIRGAS2000", "SIRGAS 2000", "SIRGAS-2000", "SIRGAS_2000"):
        return "SIRGAS2000"
    return None


def needs_population(mapping, options, operation):
    if operation == "comparisons":
        return options.get("comparison_indicator", "density") == "density"
    if operation in ("distribution", "temporal", "report"):
        return options.get(operation + "_indicator") == "density"
    return operation in ("density", "comparisons", "ranking", "aggregate")


def prepare(frame, mapping, options, operation):
    df = scoped(frame, mapping, options)
    if options.get("duplicate_policy") == "remove_exact":
        # Autorização específica: igualdade em TODAS as colunas, não apenas dimensões.
        df = df.loc[~df.duplicated()].copy()
    data = dimensions(df, mapping, options, operation in ("counts", "temporal", "report"))
    count, identity = mapping.get("count"), mapping.get("identity")
    if count:
        data["quantity"] = numbers(df[count], "quantidade", options)
        if data.quantity.isna().any():
            raise ValueError("Há quantitativos ausentes; nenhum valor será preenchido automaticamente.")
        if options.get("count_unit") in ("pessoas", "vinculos", "postos") and data.quantity.mod(1).ne(0).any():
            raise ValueError("Contagens de pessoas, vínculos e postos devem ser inteiras; confira a unidade e o formato numérico.")
        if data.duplicated(KEYS).any():
            if df.duplicated().any():
                raise ChoiceRequired("Há várias linhas idênticas em todas as colunas. Em «Linhas idênticas», escolha remover as cópias nesta análise ou corrija a base.")
            parts = options.get("component_columns") or []
            if not isinstance(parts, list) or any(c not in df.columns for c in parts):
                raise ValueError("As colunas que distinguem os componentes não são válidas.")
            if any(c in mapping.values() for c in parts):
                raise ValueError("Componentes devem ser dimensões adicionais, não medidas, população ou campos já associados.")
            if not parts:
                raise ChoiceRequired("Há várias linhas por território, período e categoria. Escolha a coluna do código territorial (homônimos) ou as colunas que distinguem os componentes.")
            detail = data[KEYS].copy()
            for i, col in enumerate(parts):
                detail[f"component_{i}"] = text_values(df[col])
            if detail.isna().any().any() or detail.duplicated().any():
                raise ValueError("Os componentes indicados não distinguem todos os registros, ou têm valores ausentes. Não é seguro somar essas linhas.")
            if not options.get("rows_additive_confirmed"):
                raise ChoiceRequired(_premise(options, "rows_additive_confirmed"))
            data = data.groupby(KEYS, as_index=False).quantity.sum()
    elif identity:
        values = text_values(df[identity])
        if values.isna().any():
            raise ValueError("Há identificadores individuais ausentes ou vazios; a contagem distinta está impedida.")
        data["private_identity"] = values
        data = data.groupby(KEYS, as_index=False).private_identity.nunique().rename(columns={"private_identity": "quantity"})
    else:
        raise ValueError("Associe Quantidade ou um identificador individual autorizado.")
    use_population = needs_population(mapping, options, operation)
    data["population"] = np.nan
    if use_population:
        col = mapping.get("population")
        if not col:
            raise ValueError("Associe a coluna de população correspondente.")
        population = dimensions(df, mapping, options, operation in ("temporal", "report"))[["territory", "period"]]
        population["population"] = numbers(df[col], "população", options)
        if population.population.isna().any() or population.population.le(0).any():
            raise ValueError("Há populações ausentes ou não positivas. Corrija o denominador ou selecione um recorte com população válida.")
        if population.groupby(["territory", "period"]).population.nunique().gt(1).any():
            raise ValueError("Populações conflitantes no mesmo território e período. Confira homônimos, o código territorial e o denominador; populações não serão somadas nem escolhidas arbitrariamente.")
        population = population.drop_duplicates(["territory", "period"])
        data = data.drop(columns="population").merge(population, on=["territory", "period"], validate="many_to_one")
    data["density"] = data.quantity / data.population * 1000
    if not np.isfinite(data.quantity).all() or (use_population and not np.isfinite(data.density).all()):
        raise ValueError("O cálculo excede a faixa numérica suportada; reveja a escala e os valores informados.")
    return data


def resolve_convention(values, convention="auto"):
    """Convenção temporal efetiva: a informada ou, em "auto", a reconhecida nos rótulos (AAAAMM, data ou numérica)."""
    if convention != "auto":
        return convention
    labels = list(dict.fromkeys(str(v).strip() for v in values))
    if all(re.fullmatch(r"\d{6}", x) for x in labels):
        return "yyyymm"
    if all(re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", x) for x in labels):
        return "date"
    return "numeric"


def period_positions(values, convention="auto"):
    labels = list(dict.fromkeys(str(v).strip() for v in values))
    convention = resolve_convention(labels, convention)
    try:
        if convention == "yyyymm":
            dates = pd.to_datetime(labels, format="%Y%m", errors="raise")
            positions = [float(d.year * 12 + d.month - 1) for d in dates]
        elif convention == "date":
            dates = pd.to_datetime(labels, format="ISO8601", errors="raise")
            positions = [float(d.toordinal()) for d in dates]
        elif convention == "numeric":
            positions = [float(v) for v in labels]
        else:
            raise ValueError()
        if not all(np.isfinite(x) for x in positions) or len(set(positions)) != len(labels):
            raise ValueError()
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Referências temporais inválidas ou equivalentes. Escolha a convenção e corrija períodos como meses inexistentes ou duas grafias do mesmo período.") from exc
    return dict(zip(labels, positions))


def spatial_data(frame, mapping, options):
    """Uma coordenada por território do recorte (RQ-DAD-25: validade por elemento).

    Coordenada ausente, não numérica ou fora dos intervalos geográficos deixa só aquele território não avaliável
    (colunas "valida" e "condicao"); os demais seguem. Coordenadas válidas diferentes para o mesmo território (por
    exemplo, em competências diferentes) continuam impedindo a análise: a escolha de uma competência resolve."""
    df = scoped(frame, mapping, options)
    # A análise espacial não exige categoria ou referência temporal.
    opts = {**options, "single_period_confirmed": True, "fts_scope_confirmed": True}
    geomapping = {r: c for r, c in mapping.items() if r in ("territory", "territory_id")}
    geo = dimensions(df, geomapping, opts)[["territory"]]
    comma = options.get("number_format") == "decimal_comma"
    raw = {}
    for role in ("latitude", "longitude"):
        if not mapping.get(role):
            raise ValueError("Associe latitude e longitude.")
        raw[role] = text_values(df[mapping[role]])
        if not comma and raw[role].str.contains(",", regex=False).any():
            # Formato da coluna, não de um elemento: a vírgula só tem significado declarado (mesma regra de numbers()).
            raise ValueError(f"Há valores não numéricos ou não finitos em {role}. Confira o formato decimal e a coluna selecionada.")
        source = raw[role].str.replace(",", ".", regex=False) if comma else raw[role]
        geo[role] = pd.to_numeric(source, errors="coerce").astype(float)
    # Camada complementar governada (só base Brasil): ponto inválido dos municípios autorizados substituído.
    from geo_complement import overlay  # importação tardia: o módulo usa este contrato
    geo["latitude"], geo["longitude"], applied, complement = overlay(df, mapping, geo["latitude"], geo["longitude"])
    applied = pd.Series(applied if applied is not None else False, index=geo.index, dtype=bool)
    missing = (raw["latitude"].isna() | raw["longitude"].isna()) & ~applied
    finite = np.isfinite(geo["latitude"]) & np.isfinite(geo["longitude"])
    in_range = finite & geo["latitude"].between(-90, 90) & geo["longitude"].between(-180, 180)
    geo["condicao"] = np.where(missing, "AUSENTE", np.where(in_range, "VALIDA", "INVALIDA"))
    valid = geo[geo.condicao == "VALIDA"]
    if valid.groupby("territory")[["latitude", "longitude"]].nunique().gt(1).any().any():
        period = mapping.get("period")
        if period and text_values(df[period]).nunique() > 1:
            raise ChoiceRequired("Coordenadas conflitantes para o mesmo território entre competências. Escolha uma competência "
                                 "no período da análise.")
        raise ValueError("Coordenadas conflitantes para o mesmo território na mesma competência. Verifique o identificador "
                         "territorial.")
    # O território é avaliável só quando todas as suas linhas trazem a coordenada válida.
    state = geo.groupby("territory")["condicao"].agg(lambda values: "VALIDA" if (values == "VALIDA").all()
                                                     else "AUSENTE" if (values == "AUSENTE").all() else "INVALIDA")
    geo["complementada"] = applied.to_numpy()
    result = geo.sort_values("condicao", key=lambda col: col.ne("VALIDA")).drop_duplicates("territory").copy()
    result["condicao"] = result.territory.map(state)
    result["valida"] = result.condicao.eq("VALIDA")
    result.loc[~result.valida, ["latitude", "longitude"]] = np.nan
    result = result.sort_index()
    result.attrs["complemento"] = complement
    return result


def rotation_data(frame, mapping, options):
    if options.get("period_filter") or options.get("period_filters"):
        raise ValueError("Remova os filtros de período e escolha os períodos inicial e final da coorte.")
    df = scoped(frame, mapping, options)
    data = dimensions(df, mapping, options)
    person = mapping.get("identity")
    if not person:
        raise ValueError("Rotatividade exige identificador individual autorizado.")
    data["person"] = text_values(df[person])
    if data.person.isna().any():
        raise ValueError("Há identificadores individuais ausentes ou vazios; a coorte está impedida.")
    positions = period_positions(data.period.unique(), options.get("period_convention", "auto"))
    periods = sorted(positions, key=positions.get)
    if len(periods) < 2:
        raise ValueError("Rotatividade exige pelo menos dois períodos.")
    first, last = options.get("initial_period") or periods[0], options.get("final_period") or periods[-1]
    if first not in positions or last not in positions or positions[first] >= positions[last]:
        raise ValueError("Escolha períodos inicial e final existentes, com o final posterior ao inicial.")
    return data, first, last


def validate_operation(frame, mapping, options, operation, prepared=None):
    if operation in ("comparisons", "ranking", "distribution", "aggregate"):
        validate_selected_levels(scoped(frame, mapping, options), mapping, options)
    if operation == "comparisons" and options.get("comparison_indicator", "density") not in ("quantity", "density"):
        raise ValueError("Indicador de comparação inválido: escolha quantidade ou densidade.")
    if operation in ("distribution", "temporal", "report"):
        if options.get(operation + "_indicator") not in ("quantity", "density"):
            raise ChoiceRequired("Escolha o indicador desta análise: quantidade ou densidade por 1.000 habitantes.")
        if needs_population(mapping, options, operation) and not options.get("population_denominator_confirmed"):
            raise ChoiceRequired(_premise(options, "population_denominator_confirmed"))
    if operation == "spatial":
        geo = spatial_data(frame, mapping, options)
        if not canonical_crs(options.get("crs")):
            raise ChoiceRequired("Escolha um referencial suportado: SIRGAS2000.")
        if options.get("reference_territory") not in set(geo.territory):
            raise ChoiceRequired("Selecione um território de referência existente, com seu código quando associado.")
        if not geo.loc[geo.territory == options["reference_territory"], "valida"].iloc[0]:
            raise ValueError("O território de referência não tem coordenada válida na competência escolhida. Escolha outro "
                             "território de referência.")
        return geo
    if operation == "nearest":
        from nearest_reference import nearest_inputs  # importação tardia: o módulo usa este contrato
        return nearest_inputs(frame, mapping, options)
    if operation == "criteria":
        from combined_criteria import criteria_inputs  # importação tardia: o módulo usa este contrato
        return criteria_inputs(frame, mapping, options)
    if operation == "rotation":
        rotation_data(frame, mapping, options)
        if not options.get("cohort_coverage_confirmed"):
            raise ChoiceRequired(_premise(options, "cohort_coverage_confirmed"))
        return None
    data = prepare(frame, mapping, options, operation) if prepared is None else prepared
    if operation in ("comparisons", "ranking", "distribution"):
        if not data.groupby(["period", "category"]).territory.nunique().ge(2).any():
            raise ValueError("São necessários pelo menos dois territórios no mesmo período e categoria.")
    if operation in ("comparisons", "ranking") and not options.get("comparison_confirmed"):
        raise ChoiceRequired(_premise(options, "comparison_confirmed"))
    if operation == "distribution":
        indicator = options.get("distribution_indicator")
        if indicator not in ("quantity", "density"):
            raise ChoiceRequired("Escolha o indicador da distribuição: quantidade de profissionais ou densidade por 1.000 habitantes.")
        if indicator == "density" and not mapping.get("population"):
            raise ChoiceRequired("Para distribuir por densidade, escolha a coluna de população correspondente.")
        if indicator == "density" and not options.get("population_denominator_confirmed"):
            raise ChoiceRequired(_premise(options, "population_denominator_confirmed"))
        if data.period.nunique() > 1 and not options.get("period_filter"):
            raise ChoiceRequired("Escolha um período para classificar territórios do mesmo momento. Os quintis não devem misturar diferentes períodos.")
        if data.category.nunique() > 1 and not options.get("category_filter"):
            raise ChoiceRequired("Escolha uma categoria profissional para comparar unidades com o mesmo objeto de análise.")
        k = options.get("quantile_count", 5)
        if not isinstance(k, int) or isinstance(k, bool) or not 2 <= k <= 10:
            raise ValueError("O número de classes deve ser inteiro entre 2 e 10.")
    if operation == "temporal":
        positions = period_positions(data.period.unique(), options.get("period_convention", "auto"))
        if len(positions) < 2:
            raise ValueError("Evolução temporal exige pelo menos dois períodos no recorte.")
        periods = sorted(positions, key=positions.get)
        present = data.groupby(["territory", "category"]).period.agg(set)
        if not any((periods[0] in s and periods[-1] in s) or len(s) >= 4 for s in present):
            raise ValueError("Nenhuma unidade tem os dois extremos para mudança ou quatro observações para tendência.")
    if operation == "aggregate":
        if data.period.nunique() != 1 or data.category.nunique() != 1:
            raise ChoiceRequired("Selecione um período e uma categoria para a agregação.")
        if not options.get("population_additive_confirmed"):
            raise ChoiceRequired(_premise(options, "population_additive_confirmed"))
        modes = [bool(options.get("no_overlap_confirmed")), bool(options.get("component_sum_confirmed")),
                 bool(not mapping.get("count") and options.get("identity_union_confirmed"))]
        if sum(modes) > 1:
            raise ValueError("Escolha uma única forma de agregação: unidades sem sobreposição, soma dos componentes ou deduplicação da união.")
        if not (options.get("no_overlap_confirmed") or options.get("component_sum_confirmed") or (
            not mapping.get("count") and options.get("identity_union_confirmed"))):
            raise ChoiceRequired("Escolha o total da agregação: soma dos componentes (possível dupla contagem), unidades sem "
                                 "sobreposição ou pessoas distintas pelo identificador. " + _premise(options, "component_sum_confirmed"))
    return data
