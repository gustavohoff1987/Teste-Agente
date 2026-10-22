"""Referências territoriais (CAP-REF-01) e referência geograficamente mais próxima (CAP-ESP-01/02).

O conjunto de referências vem de lista explícita do usuário ou de critério determinístico simples
aplicado aos dados (densidade comparada a um valor, critério atômico de CAP-SUB-01). CFG-REF é
vazio nesta versão; nenhuma referência é escolhida por conhecimento externo.

Distância: geodésica direta pelo problema inverso de Karney (GeographicLib, via pyproj), no
elipsoide do referencial confirmado (GRS80 no SIRGAS2000; WGS 84 no WGS84, Adendo REF-20261022),
em precisão integral; arredondar é tarefa da apresentação. A busca da mais próxima é exata: a corda 3D entre os pontos nunca excede a
geodésica, então só se calculam geodésicas de referências cuja corda não supere a menor
geodésica já obtida. Mínimo e empates são decididos pelas distâncias geodésicas calculadas.
"""
import json
from decimal import Decimal, InvalidOperation
from fractions import Fraction

import numpy as np
import pandas as pd
import pyproj
from pyproj import Geod

from data_contract import ChoiceRequired, SUPPORTED_CRS, canonical_crs, numbers, scoped, source_crs_conflict, text_values
from geo_complement import overlay
from request_memo import request_value
from territorial_selection import territory_catalog, texts

# Elipsoide de cada referencial do conjunto governado (nome, semieixo maior em m, inverso do achatamento).
# Não há referencial padrão nem transformação entre referenciais (RQ-DAD-26/27).
ELLIPSOIDS = {"SIRGAS2000": ("GRS80", 6378137.0, 298.257222101),
              "WGS84": ("WGS 84", 6378137.0, 298.257223563)}
GEODS = {crs: Geod(a=a, rf=rf) for crs, (_, a, rf) in ELLIPSOIDS.items()}
_, GRS80_A, GRS80_RF = ELLIPSOIDS["SIRGAS2000"]
GEOD = GEODS["SIRGAS2000"]
METHOD = {
    "capacidades": ["CAP-REF-01", "CAP-ESP-01", "CAP-ESP-02"], "versao": "1.0",
    "algoritmo": "problema geodésico inverso de Karney (GeographicLib)",
    "implementacao": "pyproj " + pyproj.__version__ + " / PROJ " + pyproj.proj_version_str,
    "unidade": "km", "precisao": "integral; arredondamento somente na apresentação",
    "busca": "exata; corda 3D como limite inferior da geodésica, sem aproximação",
}


def method(crs):
    """Método com o referencial confirmado e o elipsoide dele."""
    name, a, rf = ELLIPSOIDS[crs]
    return {**METHOD, "referencial": crs, "elipsoide": {"nome": name, "a_m": a, "inverso_achatamento": rf}}


def ellipsoid_note(crs):
    """Início da nota do resultado: referencial, elipsoide e parâmetros, em formato brasileiro."""
    name, a, rf = ELLIPSOIDS[crs]
    return (f"Referencial geodésico {crs} (elipsoide {name}, a = " + f"{a:,.0f}".replace(",", ".") + " m, 1/f = "
            + str(rf).replace(".", ",") + "); ")


TPL_11 = ("A distância apresentada é geográfica direta. Não representa distância viária, "
          "tempo de deslocamento ou acessibilidade real.")
OPERATORS = {"<": "<", "<=": "≤", ">": ">", ">=": "≥", "=": "=", "!=": "≠"}
MOTIVES = {"AUSENTE": "SEM_INFORMACAO_ESPACIAL", "INVALIDA": "COORDENADA_INVALIDA",
           "CONFLITANTE": "COORDENADA_INVALIDA", "SEM_REGISTRO": "SEM_REGISTRO_OBSERVADO"}
CONDITION_TEXT = {"AUSENTE": "coordenadas ausentes", "INVALIDA": "coordenada não numérica ou fora do intervalo",
                  "CONFLITANTE": "coordenadas divergentes no período", "SEM_REGISTRO": "sem registro no período"}
CHUNK = 128          # alvos por bloco: limita a matriz de cordas a CHUNK × referências
FIRST_CANDIDATES = 4  # geodésicas iniciais por alvo, pelas menores cordas


def row_ids(frame, mapping):
    """Mesma identidade das seleções do Bloco 1: código quando associado, senão nome."""
    code = mapping.get("territory_id")
    return ("code:" if code else "name:") + texts(frame[code or mapping["territory"]])


def analysis_period(frame, mapping, options):
    """Coordenadas e critério vêm de uma competência explícita; base de período único a resolve."""
    if options.get("period_filters"):
        raise ValueError("A referência mais próxima usa uma única competência; escolha um período.")
    col = mapping.get("period")
    if not col:
        if options.get("single_period_confirmed"):
            return None
        raise ChoiceRequired("Escolha a coluna de Período ou a opção «A base tem um único período».")
    available = set(text_values(frame[col]).dropna().tolist())
    chosen = str(options.get("period_filter") or "").strip()
    if chosen:
        if chosen not in available:
            raise ValueError("O período escolhido não existe na base.")
        return chosen
    if len(available) == 1:
        return next(iter(available))
    raise ChoiceRequired("Escolha o período: as coordenadas e o critério das referências são lidos "
                               "em uma única competência, pois podem mudar ao longo do tempo.")


def _in_period(frame, mapping, period):
    if period is None:
        return frame
    return frame[text_values(frame[mapping["period"]]) == period]


def territory_coordinates(frame, mapping, options):
    """Uma coordenada por território: válida e idêntica em todas as suas linhas, ou não avaliável."""
    comma = options.get("number_format") == "decimal_comma"

    def parse(col):
        raw = text_values(frame[col])
        source = raw.str.replace(",", ".", regex=False) if comma else raw
        return raw, pd.to_numeric(source, errors="coerce").astype("float64")

    raw_lat, lat = parse(mapping["latitude"])
    raw_lon, lon = parse(mapping["longitude"])
    # Sem separador de milhares, vírgula só tem significado declarado (mesma regra de numbers()).
    if not comma and (raw_lat.str.contains(",", regex=False).any() or raw_lon.str.contains(",", regex=False).any()):
        if options.get("number_format") == "decimal_point":
            raise ValueError("Há coordenadas com vírgula, incompatíveis com o ponto decimal escolhido. "
                             "Escolha a vírgula como separador decimal ou revise a base.")
        raise ChoiceRequired("Escolha o separador decimal das coordenadas (vírgula ou ponto): o formato não pôde ser "
                             "verificado nos dados.")
    # Camada complementar governada (só base Brasil): ponto inválido dos municípios autorizados substituído.
    lat, lon, applied, complement = overlay(frame, mapping, lat, lon)
    applied = np.zeros(len(frame), dtype=bool) if applied is None else applied
    missing = (raw_lat.isna() | raw_lon.isna()).to_numpy() & ~applied
    numeric = np.isfinite(lat.to_numpy()) & np.isfinite(lon.to_numpy())
    in_range = numeric & (np.abs(lat.to_numpy()) <= 90) & (np.abs(lon.to_numpy()) <= 180)
    state = np.where(missing, "AUSENTE", np.where(in_range, "VALIDA", "INVALIDA"))
    rows = pd.DataFrame({"id": row_ids(frame, mapping).to_numpy(), "lat": lat.to_numpy(),
                         "lon": lon.to_numpy(), "state": state, "applied": applied})
    counts = pd.crosstab(rows["id"], rows["state"]).reindex(columns=["VALIDA", "INVALIDA", "AUSENTE"], fill_value=0)
    valid = rows[rows.state == "VALIDA"]
    distinct = valid.groupby("id")[["lat", "lon"]].nunique().max(axis=1)
    first = valid.groupby("id")[["lat", "lon"]].first()
    result = pd.DataFrame(index=counts.index)
    result["lat"] = first["lat"]
    result["lon"] = first["lon"]
    only_valid = counts["VALIDA"].gt(0) & counts["INVALIDA"].eq(0) & counts["AUSENTE"].eq(0)
    result["condicao"] = np.where(
        only_valid & distinct.reindex(result.index).fillna(0).eq(1), "VALIDA",
        np.where(counts["VALIDA"].gt(0), "CONFLITANTE",
                 np.where(counts["INVALIDA"].gt(0), "INVALIDA", "AUSENTE")))
    result.loc[result.condicao != "VALIDA", ["lat", "lon"]] = np.nan
    result["coordenada"] = np.where(rows.groupby("id")["applied"].any().reindex(result.index, fill_value=False),
                                    "complementada", "original")
    result.attrs["complemento"] = complement
    return result


def _decimal(value):
    text = str(value).strip().replace(",", ".")
    try:
        number = Decimal(text)
    except InvalidOperation:
        number = None
    if number is None or not number.is_finite() or number < 0 or len(text) > 32:
        raise ValueError("Valor do critério inválido: informe um número não negativo de densidade por 1.000 habitantes.")
    return number


def _compare(operator, left, right):
    return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right,
            "=": left == right, "!=": left != right}[operator]


def density_criterion(frame, mapping, options, period, operator, threshold):
    """CAP-SUB-01 atômico sobre densidade (CAP-IND-02), por candidato e em aritmética exata."""
    if not mapping.get("population"):
        raise ValueError("O critério de densidade exige uma coluna de população associada.")
    if not mapping.get("count"):
        raise ValueError("O critério de densidade desta etapa usa coluna de quantitativos; contagem por "
                         "identificador individual não está habilitada para definir referências.")
    from semantic_bridge import premise_reason, role_established  # mesma regra do pré-exame; evita ciclo
    if not all(role_established(frame, mapping, options, role) for role in ("count", "population")):
        raise ChoiceRequired("Escolha as colunas de quantitativo e de população usadas no critério.")
    if not options.get("count_unit"):
        raise ChoiceRequired("Escolha a unidade de contagem dos quantitativos usados no critério.")
    if not options.get("population_denominator_confirmed"):
        raise ChoiceRequired(premise_reason(options, "population_denominator_confirmed"))
    rows = _in_period(frame, mapping, period)
    category = None
    if mapping.get("category"):
        available = set(text_values(rows[mapping["category"]]).dropna().tolist())
        category = str(options.get("category_filter") or "").strip()
        if not category:
            if len(available) != 1:
                raise ChoiceRequired("Escolha a categoria profissional do critério de densidade.")
            category = next(iter(available))
        if category not in available:
            raise ValueError("A categoria escolhida não existe no período do critério.")
        rows = rows[text_values(rows[mapping["category"]]) == category]
    elif not (options.get("category_constant") or options.get("fts_scope_confirmed")):
        raise ChoiceRequired("Informe o objeto de análise: a profissão ou o conjunto de trabalhadores da força de "
                             "trabalho em saúde.")
    if rows.empty:
        raise ValueError("Não há registros no período e na categoria do critério.")
    ids = row_ids(rows, mapping)
    if ids.duplicated().any():
        raise ValueError("Há territórios homônimos ou várias linhas por território no período e na categoria do "
                         "critério. Associe o código territorial para distinguir homônimos ou resolva as multiplicidades "
                         "na análise de densidade antes de definir referências.")
    quantity = numbers(rows[mapping["count"]], "quantidade", options)
    population = numbers(rows[mapping["population"]], "população", options)
    if options.get("count_unit") in ("pessoas", "vinculos", "postos") and quantity.dropna().mod(1).ne(0).any():
        raise ValueError("Contagens de pessoas, vínculos e postos devem ser inteiras; confira a unidade e o formato numérico.")
    evaluations = []
    for key, q, p in zip(ids.tolist(), quantity.tolist(), population.tolist()):
        item = {"id": key, "quantidade": None if pd.isna(q) else q, "populacao": None if pd.isna(p) else p,
                "densidade_por_1000": None, "condicao": "NAO_AVALIAVEL", "motivo": None}
        if pd.isna(q):
            item["motivo"] = "DADO_AUSENTE"
        elif pd.isna(p):
            item["motivo"] = "DENOMINADOR_AUSENTE"
        elif p == 0:
            item["motivo"] = "DENOMINADOR_ZERO"
        else:
            # q/p × 1.000 comparado a v sem arredondar: q × 1.000 contra v × p, em frações exatas.
            item["densidade_por_1000"] = q / p * 1000
            meets = _compare(operator, Fraction(q) * 1000, Fraction(threshold) * Fraction(p))
            item["condicao"] = "ATENDE" if meets else "NAO_ATENDE"
        evaluations.append(item)
    return category, evaluations


def reference_set(frame, mapping, options, period):
    """CAP-REF-01: forma, origem e membros do conjunto, preservando candidatos não avaliáveis."""
    mode = options.get("reference_mode")
    if mode not in ("list", "criterion"):
        raise ChoiceRequired("Escolha como definir as referências: lista de territórios ou critério de densidade.")
    if mode == "list":
        ids = options.get("reference_ids")
        if not ids:
            raise ChoiceRequired("Selecione ao menos um território de referência.")
        if (not isinstance(ids, list) or len(ids) > 10000 or len(ids) != len(set(ids)) or
                any(not isinstance(v, str) or not v or len(v) > 512 for v in ids)):
            raise ValueError("A lista de referências deve conter identificadores distintos.")
    else:
        criterion = options.get("reference_criterion") or {}
        operator, value = criterion.get("operator"), criterion.get("value")
        if operator not in OPERATORS or value in (None, ""):
            raise ChoiceRequired("Defina o operador e o valor do critério de densidade das referências.")
        threshold = _decimal(value)
    catalog = {item["id"]: item for item in territory_catalog(frame, mapping, options)}
    if mode == "list":
        unknown = [v for v in ids if v not in catalog]
        if unknown:
            raise ValueError("Referências inexistentes ou incompatíveis com a base: " + ", ".join(unknown[:8]))
        ambiguous = [catalog[v]["label"] for v in ids if catalog[v]["selection_reason"]]
        if ambiguous:
            raise ValueError("Identificação territorial ambígua entre níveis superiores: " + ", ".join(ambiguous[:8]))
        return {"forma": "LISTA_EXPLICITA", "origem": "MANIFESTACAO_USUARIO", "criterio": None,
                "universo_candidatos": {"definicao": "lista explícita do usuário", "n": len(ids)},
                "membros": list(ids), "avaliacao_criterio": None, "catalogo": catalog}
    category, evaluations = density_criterion(frame, mapping, options, period, operator, threshold)
    members = [item["id"] for item in evaluations if item["condicao"] == "ATENDE"]
    criterion = {"indicador": "DENSIDADE", "operador": operator, "simbolo": OPERATORS[operator],
                 "valor": str(threshold), "escala": "por 1.000 habitantes",
                 "contexto": "valor sem unidade interpretado no único contexto da densidade (por 1.000 habitantes)",
                 "periodo": period, "categoria": category,
                 "comparacao": "exata: quantidade × 1.000 contra valor × população"}
    return {"forma": "CRITERIO", "origem": "CRITERIO_AUTORIZADO_APLICADO_AOS_DADOS", "criterio": criterion,
            "universo_candidatos": {"definicao": "territórios da base no período e na categoria do critério",
                                    "n": len(evaluations)},
            "membros": sorted(members, key=lambda key: (catalog[key]["name"], key)),
            "avaliacao_criterio": evaluations, "catalogo": catalog}


def nearest_inputs(frame, mapping, options):
    """Insumos memorizados por requisição: pré-exame e cálculo (inclusive de critérios) usam os mesmos."""
    key = ("nearest_inputs", id(frame), json.dumps([{role: col for role, col in mapping.items() if col},
                                                     {**options, "crs": canonical_crs(options.get("crs")) or options.get("crs")}],
                                                    sort_keys=True, default=str))
    return request_value(key, lambda: _nearest_inputs(frame, mapping, options), anchor=frame)


def _nearest_inputs(frame, mapping, options):
    """Validações e insumos sem distâncias; verificações baratas antes das que percorrem a base."""
    crs = options.get("crs")
    if not canonical_crs(crs):
        if crs:
            raise ValueError("Referencial geodésico informado não suportado nesta versão (somente " + SUPPORTED_CRS + "). "
                             "Nenhuma transformação, aproximação ou substituição é aplicada.")
        raise ChoiceRequired("Escolha o referencial geodésico das coordenadas; nenhum referencial é presumido.")
    conflict = source_crs_conflict(frame, canonical_crs(crs))
    if conflict:
        raise ValueError(conflict)
    for role, label in (("territory", "o território"), ("latitude", "a latitude"), ("longitude", "a longitude")):
        if not mapping.get(role):
            raise ValueError("Associe " + label + " para calcular a referência mais próxima.")
    if not _coordinate_roles_established(frame, mapping, options):
        raise ChoiceRequired("Escolha as colunas de latitude e longitude (graus decimais).")
    period = analysis_period(frame, mapping, options)
    references = reference_set(frame, mapping, options, period)
    target_options = {**options, "period_filter": period} if period else options
    targets = scoped(frame, mapping, target_options)
    target_ids = sorted(set(row_ids(targets, mapping).tolist()),
                        key=lambda key: (references["catalogo"][key]["name"], key))
    geometry = _in_period(frame, mapping, period)
    _reject_homonyms(geometry, mapping, target_ids + (references["membros"] if references["forma"] == "LISTA_EXPLICITA" else []))
    coordinates = territory_coordinates(geometry, mapping, options)
    return {"period": period, "references": references, "targets": target_ids, "coordinates": coordinates}


def _reject_homonyms(frame, mapping, ids):
    """Sem código, um nome repetido na mesma categoria e período identifica mais de uma unidade."""
    if mapping.get("territory_id") or frame.empty:
        return
    keys = [mapping["territory"]] + ([mapping["category"]] if mapping.get("category") else [])
    names = pd.DataFrame({column: texts(frame[column]) for column in keys})
    repeated = set("name:" + names[names.duplicated(keys, keep=False)][mapping["territory"]].dropna())
    ambiguous = sorted(repeated.intersection(ids))
    if ambiguous:
        raise ValueError("Territórios homônimos sem código: " + ", ".join(key[5:] for key in ambiguous[:8])
                         + ". Associe o identificador territorial para distinguir as unidades.")


def _coordinate_roles_established(frame, mapping, options):
    """RQ-DAD-25: escolha do usuário, perfil oficial ou regra (nome do CFG-VOC e valores num formato decimal único).
    Valor fora do intervalo não rebaixa a coluna: o elemento fica não avaliável (COORDENADA_INVALIDA)."""
    from semantic_bridge import coordinate_roles  # mesma regra de candidates(); importação local evita ciclo
    return coordinate_roles(frame, mapping, options) == {"latitude", "longitude"}


def _ecef(lat, lon, crs):
    _, a, rf = ELLIPSOIDS[crs]
    f = 1 / rf
    e2 = f * (2 - f)
    phi, lam = np.radians(lat), np.radians(lon)
    sin_phi = np.sin(phi)
    n = a / np.sqrt(1 - e2 * sin_phi * sin_phi)
    return np.column_stack([n * np.cos(phi) * np.cos(lam), n * np.cos(phi) * np.sin(lam), n * (1 - e2) * sin_phi])


def nearest_exact(t_lat, t_lon, r_lat, r_lon, *, crs):
    """Para cada alvo: menor geodésica (m), no elipsoide do referencial crs, e índices de todas as referências com
    esse valor exato.

    Corda ≤ geodésica para qualquer par; logo uma referência com corda maior que a menor geodésica
    calculada não pode ser a mais próxima nem empatar. A margem (1e-12 relativa + 1 µm) só amplia o
    conjunto de geodésicas calculadas contra erros de ponto flutuante na corda; não decide nada.
    """
    t_lat, t_lon = np.asarray(t_lat, float), np.asarray(t_lon, float)
    r_lat, r_lon = np.asarray(r_lat, float), np.asarray(r_lon, float)
    count, total = len(t_lat), len(r_lat)
    best = np.full(count, np.nan)
    ties: list[list[int]] = [[] for _ in range(count)]
    evaluated = 0
    if not count or not total:
        return best, ties, evaluated
    geod = GEODS[crs]
    rx = _ecef(r_lat, r_lon, crs)
    tx = _ecef(t_lat, t_lon, crs)
    for start in range(0, count, CHUNK):
        stop = min(count, start + CHUNK)
        diff = tx[start:stop, None, :] - rx[None, :, :]
        chord = np.sqrt(np.einsum("ijk,ijk->ij", diff, diff))
        size = stop - start
        distance = np.full((size, total), np.inf)
        done = np.zeros((size, total), dtype=bool)
        k = min(FIRST_CANDIDATES, total)
        rows = np.repeat(np.arange(size), k)
        cols = np.argpartition(chord, k - 1, axis=1)[:, :k].ravel()
        while len(rows):
            _, _, meters = geod.inv(t_lon[start + rows], t_lat[start + rows], r_lon[cols], r_lat[cols])
            distance[rows, cols] = meters
            done[rows, cols] = True
            evaluated += len(rows)
            limit = np.min(distance, axis=1)
            pending = (chord <= (limit * (1 + 1e-12) + 1e-6)[:, None]) & ~done
            rows, cols = np.nonzero(pending)
        for i in range(size):
            row = distance[i]
            best[start + i] = row.min()
            ties[start + i] = np.flatnonzero(row == best[start + i]).tolist()
    return best, ties, evaluated


def nearest_exhaustive(t_lat, t_lon, r_lat, r_lon, *, crs):
    """Referência de teste: todas as geodésicas, mesmo critério de mínimo e empate."""
    best, ties = [], []
    for lat, lon in zip(t_lat, t_lon):
        _, _, meters = GEODS[crs].inv(np.full(len(r_lat), lon), np.full(len(r_lat), lat), np.asarray(r_lon), np.asarray(r_lat))
        best.append(meters.min() if len(meters) else np.nan)
        ties.append(np.flatnonzero(meters == meters.min()).tolist() if len(meters) else [])
    return np.array(best), ties


def _not_evaluable(detail=None, scope=None):
    value = {"avaliabilidade": "NAO_AVALIAVEL", "motivo": "DEPENDENCIA_NAO_AVALIAVEL", "referencias": []}
    if detail:
        value["detalhe"] = detail
    return {**value, "alcance": scope} if scope else value


def compute_nearest(frame, mapping, options):
    """Resultado completo: tabela por alvo e conteúdo estruturado de CAP-REF-01/CAP-ESP-02."""
    inputs = nearest_inputs(frame, mapping, options)
    refs, coords, period = inputs["references"], inputs["coordinates"], inputs["period"]
    catalog = refs["catalogo"]
    crs = canonical_crs(options["crs"])  # conferido em nearest_inputs

    def condition(key):
        return coords.at[key, "condicao"] if key in coords.index else "SEM_REGISTRO"

    def origin(key):
        return coords.at[key, "coordenada"] if key in coords.index else "original"

    ref_ids, targets = refs["membros"], inputs["targets"]
    ref_state = {key: condition(key) for key in ref_ids}
    valid_refs = [key for key in ref_ids if ref_state[key] == "VALIDA"]
    invalid_refs = [{"id": key, "territorio": catalog[key]["label"], "condicao": ref_state[key],
                     "motivo": MOTIVES[ref_state[key]]} for key in ref_ids if ref_state[key] != "VALIDA"]
    target_state = {key: condition(key) for key in targets}
    valid_targets = [key for key in targets if target_state[key] == "VALIDA"]
    best, ties, evaluated = nearest_exact(coords.loc[valid_targets, "lat"], coords.loc[valid_targets, "lon"],
                                          coords.loc[valid_refs, "lat"], coords.loc[valid_refs, "lon"], crs=crs)
    position = {key: i for i, key in enumerate(valid_targets)}
    members = set(ref_ids)
    scope_partial, scope_full = "entre as referências avaliáveis", "conjunto completo de referências"
    # Coluna de rastreabilidade só quando a camada complementar foi usada em algum alvo ou referência.
    traced = any(origin(key) == "complementada" for key in set(targets) | members)
    coverage, rows = [], []
    for key in targets:
        record = {"unidade": key, "condicao_espacial": target_state[key], "coordenada": origin(key),
                  "referencias_autorizadas": len(ref_ids), "referencias_avaliaveis": 0,
                  "referencias_nao_avaliaveis_com_motivo": [], "alvo_e_referencia": key in members}
        if not ref_ids:
            record["minimo_completo"] = _not_evaluable("CONJUNTO_REFERENCIAS_VAZIO")
            record["minimo_avaliaveis"] = _not_evaluable("CONJUNTO_REFERENCIAS_VAZIO", scope_partial)
            condition_text = "Não avaliável: conjunto de referências vazio (DEPENDENCIA_NAO_AVALIAVEL, CONJUNTO_REFERENCIAS_VAZIO)"
        elif target_state[key] != "VALIDA":
            motive = MOTIVES[target_state[key]]
            record["referencias_nao_avaliaveis_com_motivo"] = [{"referencias": "todas", "motivo": motive,
                                                                "origem": "coordenada do alvo"}]
            record["minimo_completo"] = _not_evaluable()
            record["minimo_avaliaveis"] = _not_evaluable(None, scope_partial)
            condition_text = "Não avaliável: " + motive + " (" + CONDITION_TEXT[target_state[key]] + " no alvo)"
        else:
            record["referencias_avaliaveis"] = len(valid_refs)
            # Com o alvo avaliável, os motivos vêm só das referências e são os mesmos para todos os alvos:
            # o registro aponta a lista do resultado em vez de repeti-la 5.570 vezes.
            if invalid_refs:
                record["referencias_nao_avaliaveis_com_motivo"] = [{"referencias": "referencias_nao_avaliaveis",
                                                                    "n": len(invalid_refs), "origem": "coordenada da referência"}]
            if not valid_refs:
                record["minimo_completo"] = _not_evaluable()
                record["minimo_avaliaveis"] = _not_evaluable(None, scope_partial)
                condition_text = "Não avaliável: nenhuma referência com coordenadas avaliáveis (DEPENDENCIA_NAO_AVALIAVEL)"
            else:
                i = position[key]
                found = {"avaliabilidade": "AVALIAVEL", "referencias": [valid_refs[j] for j in ties[i]],
                         "distancia_km": best[i] / 1000}
                record["minimo_avaliaveis"] = {**found, "alcance": scope_partial}
                if invalid_refs:
                    record["minimo_completo"] = _not_evaluable()
                    condition_text = "Cobertura parcial: mínimo completo não avaliável (DEPENDENCIA_NAO_AVALIAVEL)"
                else:
                    record["minimo_completo"] = {**found, "alcance": scope_full}
                    condition_text = "Avaliável"
        full, partial = record["minimo_completo"], record["minimo_avaliaveis"]
        shown = full if full["avaliabilidade"] == "AVALIAVEL" else partial if partial["avaliabilidade"] == "AVALIAVEL" else None
        nearest = shown["referencias"] if shown else []
        row = {
            "Território-alvo": catalog[key]["name"], "Código do alvo": catalog[key]["code"] or None,
            "Referência mais próxima": "; ".join(catalog[r]["name"] for r in nearest) or None,
            "Código da referência": "; ".join(catalog[r]["code"] for r in nearest if catalog[r]["code"]) or None,
            "Distância (km)": shown["distancia_km"] if shown else None,
            "Alcance": ("Conjunto completo de referências" if shown is full else
                        "Entre as referências avaliáveis" if shown else "Não avaliável"),
            "Referências avaliáveis": f"{record['referencias_avaliaveis']} de {len(ref_ids)}",
            "Empate": f"Sim ({len(nearest)} referências)" if len(nearest) > 1 else "Não",
            "Alvo também é referência": "Sim" if record["alvo_e_referencia"] else "Não"}
        if traced:
            sides = [side for side, used in (("alvo", record["coordenada"] == "complementada"),
                                             ("referência", any(origin(r) == "complementada" for r in nearest))) if used]
            row["Coordenada complementada (camada oficial)"] = " e ".join(sides).capitalize() if sides else "Não"
        row["Condição"] = condition_text
        rows.append(row)
        coverage.append(record)
    complete = sum(r["minimo_completo"]["avaliabilidade"] == "AVALIAVEL" for r in coverage)
    partial_only = sum(r["minimo_completo"]["avaliabilidade"] != "AVALIAVEL" and
                       r["minimo_avaliaveis"]["avaliabilidade"] == "AVALIAVEL" for r in coverage)
    without = len(coverage) - complete - partial_only
    by_motive = {}
    for record in coverage:
        if record["minimo_avaliaveis"]["avaliabilidade"] != "AVALIAVEL":
            cause = (record["minimo_avaliaveis"].get("detalhe") or
                     (MOTIVES[record["condicao_espacial"]] if record["condicao_espacial"] != "VALIDA" else "DEPENDENCIA_NAO_AVALIAVEL"))
            by_motive[cause] = by_motive.get(cause, 0) + 1
    limitations = []
    if complete or partial_only:
        limitations.append({"tipo": "DISTANCIA_GEODESICA_DIRETA", "categoria": "ANALITICA", "texto": TPL_11})
    if partial_only:
        limitations.append({"tipo": "COBERTURA_PARCIAL", "categoria": "ANALITICA",
                            "dados_estruturados": {"referencias_nao_avaliaveis": invalid_refs},
                            "elementos_afetados": partial_only})
    if without:
        limitations.append({"tipo": "UNIDADES_NAO_AVALIAVEIS", "categoria": "ANALITICA",
                            "dados_estruturados": by_motive, "elementos_afetados": without})
    evaluation = refs["avaliacao_criterio"]
    criterion_summary = None
    if evaluation is not None:
        criterion_summary = {
            "ATENDE": len(ref_ids),
            "NAO_ATENDE": sum(item["condicao"] == "NAO_ATENDE" for item in evaluation),
            "NAO_AVALIAVEL": [{"id": item["id"], "territorio": catalog[item["id"]]["label"], "motivo": item["motivo"]}
                              for item in evaluation if item["condicao"] == "NAO_AVALIAVEL"],
            "valores_atende": [{"id": item["id"], "densidade_por_1000": item["densidade_por_1000"],
                                "quantidade": item["quantidade"], "populacao": item["populacao"]}
                               for item in evaluation if item["condicao"] == "ATENDE"]}
        if criterion_summary["NAO_AVALIAVEL"]:
            limitations.append({"tipo": "UNIDADES_NAO_AVALIAVEIS", "categoria": "ANALITICA",
                                "dados_estruturados": {"escopo": "candidatos à referência",
                                                       "candidatos": criterion_summary["NAO_AVALIAVEL"]},
                                "elementos_afetados": len(criterion_summary["NAO_AVALIAVEL"])})
    if complete or partial_only:
        outcome = "RES-LIM"  # RQ-CAP-08 (d): a limitação DISTANCIA_GEODESICA_DIRETA é analítica (RQ-RES-06)
    else:
        outcome = "BLQ-DEP" if not ref_ids else "BLQ-DAD"
    tie_count = sum(len(r["minimo_avaliaveis"]["referencias"]) > 1 for r in coverage)
    notes = []
    if complete or partial_only:
        notes.append(TPL_11)
    notes.append(ellipsoid_note(crs) + "distância pelo problema geodésico inverso de Karney, em quilômetros e sem "
                 "arredondamento no cálculo.")
    if period is not None:
        notes.append("Coordenadas e critério da competência " + period + "; coordenadas de outras competências não são "
                     "tratadas como equivalentes.")
    if refs["forma"] == "LISTA_EXPLICITA":
        notes.append(f"Referências: lista explícita do usuário ({len(ref_ids)} territórios); nenhuma referência foi escolhida pelo sistema.")
    else:
        c = refs["criterio"]
        notes.append(f"Referências: territórios com densidade {c['simbolo']} {c['valor'].replace('.', ',')} por 1.000 habitantes"
                     + (f" na categoria {c['categoria']}" if c["categoria"] else "")
                     + (f" em {c['periodo']}" if c["periodo"] else "")
                     + f" (critério do usuário aplicado aos dados, comparação exata). Atendem: {criterion_summary['ATENDE']}; "
                       f"não atendem: {criterion_summary['NAO_ATENDE']}; não avaliáveis: {len(criterion_summary['NAO_AVALIAVEL'])}."
                     + " A condição de referência não tem caráter normativo.")
        if criterion_summary["NAO_AVALIAVEL"]:
            notes.append("Candidatos não avaliáveis pelo critério não integram nem são excluídos do conjunto por presunção: "
                         "ficam listados à parte com seus motivos.")
    if invalid_refs:
        notes.append(f"{len(invalid_refs)} referência(s) sem coordenadas avaliáveis: "
                     + "; ".join(item["territorio"] + " (" + item["motivo"] + ")" for item in invalid_refs[:10])
                     + ". O mínimo do conjunto completo fica não avaliável e é exibida a mais próxima entre as referências avaliáveis.")
    invalid_targets = len(targets) - len(valid_targets)
    if invalid_targets:
        notes.append(f"{invalid_targets} alvo(s) sem coordenadas avaliáveis permanecem no universo como não avaliáveis.")
    coincident = sum(r["alvo_e_referencia"] for r in coverage)
    if coincident:
        notes.append(f"{coincident} alvo(s) também integram o conjunto de referências: a distância até si mesmos é zero e "
                     "está registrada; nenhuma exclusão automática foi aplicada.")
    if tie_count:
        notes.append(f"{tie_count} alvo(s) com empate exato na menor distância: todas as referências empatadas são apresentadas.")
    if not ref_ids:
        notes.append("Conjunto de referências vazio: nenhuma distância foi calculada e o universo-alvo foi preservado "
                     "(DEPENDENCIA_NAO_AVALIAVEL, detalhe CONJUNTO_REFERENCIAS_VAZIO).")
    complement = coords.attrs.get("complemento")
    if complement is not None:
        if complement.get("municipios_complementados"):
            notes.append("Coordenadas de " + str(len(complement["municipios_complementados"])) + " município(s) com ponto inválido na "
                         "fonte original vêm da camada geográfica complementar versionada (" + str(complement.get("identificador")) +
                         ", versão " + str(complement.get("versao")) + "), sob a premissa do usuário de coordenada fixa de 2014 a "
                         "2024; os arquivos originais não foram alterados.")
        elif complement.get("estado") != "valido":
            notes.append("Camada geográfica complementar " + str(complement.get("estado")) + ": " + str(complement.get("motivo")) +
                         ". Municípios com coordenada inválida na fonte original permanecem não avaliáveis.")
    title = "Referência mais próxima" + ("" if complete or partial_only else " — sem resultado analítico")
    description = ("Para cada território-alvo, a referência autorizada geograficamente mais próxima, com cobertura das "
                   "referências. " + TPL_11)
    metrics = [{"label": "Territórios-alvo", "value": len(targets)},
               {"label": "Referências autorizadas", "value": len(ref_ids)},
               {"label": "Mínimo do conjunto completo", "value": complete},
               {"label": "Somente entre as referências avaliáveis", "value": partial_only},
               {"label": "Não avaliáveis", "value": without}]
    structured = {
        "metodo": method(crs), "periodo_geometria": period,
        "universo_alvos": {"definicao": "subconjunto selecionado" if "territory_ids" in options else "universo observado no período",
                           "n": len(targets), "n_coordenadas_avaliaveis": len(valid_targets)},
        "conjunto_referencias": {
            "forma": refs["forma"], "origem": refs["origem"], "criterio": refs["criterio"],
            "universo_candidatos": refs["universo_candidatos"], "n": len(ref_ids),
            "n_coordenadas_avaliaveis": len(valid_refs),
            "membros": [{"id": key, "territorio": catalog[key]["label"], "condicao_espacial": ref_state[key],
                         "motivo": MOTIVES.get(ref_state[key])} for key in ref_ids],
            "avaliacao_criterio": criterion_summary},
        "referencias_nao_avaliaveis": invalid_refs,
        "cobertura_referencias": coverage,
        "cobertura": {"n_universo": len(targets), "n_minimo_completo": complete,
                      "n_somente_entre_avaliaveis": partial_only, "n_nao_avaliaveis_por_motivo": by_motive},
        "limitacoes": limitations, "desfecho": outcome,
        "geodesicas_calculadas": evaluated, "pares_avaliaveis": len(valid_targets) * len(valid_refs)}
    complement = coords.attrs.get("complemento")
    if complement is not None:  # base Brasil: identidade da camada e coordenadas efetivamente usadas
        used = sorted(set(targets) | set(ref_ids))
        structured["complemento_geografico"] = {**complement, "territorios_complementados": [
            {"id": key, "territorio": catalog[key]["label"], "latitude": coords.at[key, "lat"], "longitude": coords.at[key, "lon"]}
            for key in used if origin(key) == "complementada"]}
    evaluability = ("AVALIAVEL" if complete == len(targets) and not limitations[1:] else
                    "AVALIAVEL_COM_LIMITACOES" if complete or partial_only else "NAO_AVALIAVEL")
    return {"title": title, "description": description, "rows": rows, "metrics": metrics, "notes": notes,
            "structured": _plain(structured), "evaluability": evaluability}


def _plain(value):
    """Tipos JSON nativos; NaN e infinitos nunca viram número."""
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    return value
