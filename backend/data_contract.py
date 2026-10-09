"""Contratos estruturais compartilhados pelo exame e pelo cálculo, sem LLM.

RQ-DAD-18/29/35/36: nomes não implicam identidade, soma ou unidade.
As transformações são locais à requisição e exigem declarações explícitas.
"""
import re
from itertools import islice

import numpy as np
import pandas as pd


class ConfirmationRequired(ValueError):
    pass


def text_values(series):
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


def scoped(frame, mapping, options):
    frame = frame.copy()
    for role in ("period", "category"):
        value = options.get(role + "_filter")
        if value:
            col = mapping.get(role)
            if not col:
                raise ValueError("O filtro exige a associação da dimensão correspondente.")
            frame = frame[text_values(frame[col]) == str(value).strip()]
    if frame.empty:
        raise ValueError("Nenhum registro corresponde aos filtros selecionados.")
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
                raise ConfirmationRequired("Associe Período ou confirme que a base representa um único período.")
            if role == "category" and not (options.get("category_constant") or options.get("fts_scope_confirmed")):
                raise ConfirmationRequired("Declare a categoria ou o conjunto de trabalhadores da base.")
            data[role] = fallback
    if data.isna().any().any():
        raise ValueError("Há valores ausentes ou vazios nas dimensões associadas; corrija a base ou selecione um recorte completo.")
    id_col = mapping.get("territory_id")
    if id_col:
        if not mapping.get("territory"):
            raise ValueError("Associe também o nome da unidade territorial correspondente ao código.")
        if "territory_id" not in options.get("confirmed_roles", []):
            raise ConfirmationRequired("Confirme que o código identifica cada unidade territorial no recorte escolhido.")
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
    if code and "territory_id" in options.get("confirmed_roles", []):
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


def needs_population(mapping, options, operation):
    if operation == "distribution":
        return options.get("distribution_indicator") == "density"
    return operation in ("density", "comparisons", "ranking", "aggregate") or bool(
        operation in ("temporal", "report") and mapping.get("territory") and options.get("population_denominator_confirmed"))


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
                raise ConfirmationRequired("Há várias linhas idênticas em todas as colunas. Investigue sua origem e autorize a remoção das cópias somente se forem duplicatas de importação.")
            parts = options.get("component_columns") or []
            if not isinstance(parts, list) or any(c not in df.columns for c in parts):
                raise ValueError("As colunas que distinguem os componentes não são válidas.")
            if any(c in mapping.values() for c in parts):
                raise ValueError("Componentes devem ser dimensões adicionais, não medidas, população ou campos já associados.")
            if not parts:
                raise ConfirmationRequired("Há várias linhas por território, período e categoria. Associe um código para distinguir territórios homônimos ou indique as colunas que distinguem os componentes da contagem.")
            detail = data[KEYS].copy()
            for i, col in enumerate(parts):
                detail[f"component_{i}"] = text_values(df[col])
            if detail.isna().any().any() or detail.duplicated().any():
                raise ValueError("Os componentes indicados não distinguem todos os registros, ou têm valores ausentes. Não é seguro somar essas linhas.")
            if not options.get("rows_additive_confirmed"):
                raise ConfirmationRequired("Declare que os componentes têm a mesma unidade de contagem e são partes sem sobreposição dentro de cada território, período e categoria.")
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


def period_positions(values, convention="auto"):
    labels = list(dict.fromkeys(str(v).strip() for v in values))
    if convention == "auto":
        if all(re.fullmatch(r"\d{6}", x) for x in labels):
            convention = "yyyymm"
        elif all(re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", x) for x in labels):
            convention = "date"
        else:
            convention = "numeric"
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
        raise ValueError("Referências temporais inválidas ou equivalentes. Declare a convenção e corrija períodos como meses inexistentes ou duas grafias do mesmo período.") from exc
    return dict(zip(labels, positions))


def spatial_data(frame, mapping, options):
    df = scoped(frame, mapping, options)
    # A análise espacial não exige categoria ou referência temporal.
    opts = {**options, "single_period_confirmed": True, "fts_scope_confirmed": True}
    geomapping = {r: c for r, c in mapping.items() if r in ("territory", "territory_id")}
    geo = dimensions(df, geomapping, opts)[["territory"]]
    for role, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
        if not mapping.get(role):
            raise ValueError("Associe latitude e longitude.")
        geo[role] = numbers(df[mapping[role]], role, options)
        if geo[role].isna().any() or not geo[role].between(low, high).all():
            raise ValueError("Coordenadas ausentes ou fora dos intervalos geográficos válidos.")
    if geo.groupby("territory")[["latitude", "longitude"]].nunique().gt(1).any().any():
        raise ValueError("Coordenadas conflitantes para o mesmo território. Verifique o identificador ou selecione um período consistente.")
    return geo.drop_duplicates("territory")


def rotation_data(frame, mapping, options):
    if options.get("period_filter"):
        raise ValueError("Remova o filtro de período e escolha os períodos inicial e final da coorte.")
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
    if operation == "spatial":
        geo = spatial_data(frame, mapping, options)
        if options.get("crs") not in ("SIRGAS2000", "WGS84"):
            raise ConfirmationRequired("Informe um referencial suportado: SIRGAS2000 ou WGS84.")
        if options.get("reference_territory") not in set(geo.territory):
            raise ConfirmationRequired("Selecione um território de referência existente, com seu código quando associado.")
        return geo
    if operation == "rotation":
        rotation_data(frame, mapping, options)
        if not options.get("cohort_coverage_confirmed"):
            raise ConfirmationRequired("Confirme que os dois períodos cobrem integralmente o mesmo universo de trabalhadores; ausência de registro deve representar ausência na coorte.")
        return None
    data = prepare(frame, mapping, options, operation) if prepared is None else prepared
    if operation in ("comparisons", "ranking", "distribution"):
        if not data.groupby(["period", "category"]).territory.nunique().ge(2).any():
            raise ValueError("São necessários pelo menos dois territórios no mesmo período e categoria.")
    if operation in ("comparisons", "ranking") and not options.get("comparison_confirmed"):
        raise ConfirmationRequired("Confirme que medida, unidade e definição populacional são equivalentes entre os territórios comparados.")
    if operation == "distribution":
        indicator = options.get("distribution_indicator")
        if indicator not in ("quantity", "density"):
            raise ConfirmationRequired("Escolha o indicador da distribuição: quantidade de profissionais ou densidade por 1.000 habitantes.")
        if indicator == "density" and (not mapping.get("population") or not options.get("population_denominator_confirmed")):
            raise ConfirmationRequired("Para distribuir por densidade, associe e confirme a população correspondente.")
        if data.period.nunique() > 1 and not options.get("period_filter"):
            raise ConfirmationRequired("Escolha um período para classificar territórios do mesmo momento. Os quintis não devem misturar diferentes períodos.")
        if data.category.nunique() > 1 and not options.get("category_filter"):
            raise ConfirmationRequired("Escolha uma categoria profissional para comparar unidades com o mesmo objeto de análise.")
        k = options.get("quantile_count", 5)
        if not isinstance(k, int) or isinstance(k, bool) or not 2 <= k <= 10:
            raise ValueError("O número de classes deve ser inteiro entre 2 e 10.")
    if operation == "temporal":
        positions = period_positions(data.period.unique(), options.get("period_convention", "auto"))
        if len(positions) < 2:
            raise ValueError("Evolução temporal exige pelo menos dois períodos no recorte.")
        periods = sorted(positions, key=positions.get)
        present = data.groupby(["territory", "category"]).period.agg(set)
        if not any(periods[0] in s and periods[-1] in s for s in present):
            raise ValueError("Nenhuma unidade tem observações nos dois períodos extremos selecionados.")
    if operation == "aggregate":
        if data.period.nunique() != 1 or data.category.nunique() != 1:
            raise ConfirmationRequired("Selecione um período e uma categoria para a agregação.")
        if not options.get("population_additive_confirmed"):
            raise ConfirmationRequired("Declare que as populações dos territórios são partes sem sobreposição do conjunto agregado.")
        modes = [bool(options.get("no_overlap_confirmed")), bool(options.get("component_sum_confirmed")),
                 bool(not mapping.get("count") and options.get("identity_union_confirmed"))]
        if sum(modes) > 1:
            raise ValueError("Escolha uma única forma de agregação: unidades sem sobreposição, soma dos componentes ou deduplicação da união.")
        if not (options.get("no_overlap_confirmed") or options.get("component_sum_confirmed") or (
            not mapping.get("count") and options.get("identity_union_confirmed"))):
            raise ConfirmationRequired("Informe ausência de sobreposição, autorize a soma dos componentes com possível dupla contagem ou declare identidade válida na união territorial.")
    return data
