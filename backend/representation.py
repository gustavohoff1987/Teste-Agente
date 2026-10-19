"""Contrato de apresentação do Bloco 3 (CAP-REP-01 a CAP-REP-04; Parte 13 da SPEC v1.2.4).

Sem operação analítica (INV-11, RQ-REP-09). O contrato declara, para cada resultado, quais colunas
do próprio resultado são representáveis — rótulo, unidade e natureza: valor contínuo, contagem,
posição, classe ou estado produzidos por capacidade (RQ-REP-02) — e entrega a geometria autorizada:
as coordenadas efetivas de cada território na competência do resultado, lidas pela mesma regra das
análises espaciais (referencial suportado, papéis de latitude e longitude estabelecidos, separador
decimal escolhido ou verificado nos dados e camada geográfica complementar governada). Sem geometria autorizada, o mapa
recebe BLQ-DAD com o motivo (RQ-REP-07); tabela e gráficos continuam disponíveis.

Nos resultados com níveis territoriais (territorial_levels.py), o contrato declara os níveis ("niveis"), os painéis da
série por tipo de contagem ("serie.paineis") e só desenha municípios no mapa: Brasil e estados são agregados sem ponto.
A taxa nacional de referência (D5) chega pronta em "referencias"; o frontend não calcula, não classifica e não colore
os municípios em relação a ela.
"""
import re

from brazil_catalog_profile import curated_profile, governed_version
from combined_criteria import needs as criteria_needs
from data_contract import ChoiceRequired, canonical_crs, count_unit_label, scoped
from nearest_reference import (CONDITION_TEXT, MOTIVES, TPL_11, _coordinate_roles_established, _in_period,
                               nearest_inputs, territory_coordinates)
from temporal_change import DIRECTIONS
from trend import CLASSES, LABELS, NOT_EVALUABLE_LABELS

VERSION = 1
DENSITY_UNIT = "por 1.000 habitantes"
WITHOUT_MAP = {
    "aggregate": "a agregação produz um único conjunto, sem valor por território",
    "rotation": "a rotatividade descreve coortes entre duas competências, sem valor por território numa competência",
    "temporal": "a evolução temporal reúne várias competências, e as coordenadas podem mudar entre elas; "
                "use o gráfico de linhas",
}
STATES = ["ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL"]
REACH = ["Conjunto completo de referências", "Entre as referências avaliáveis", "Não avaliável"]
CRITERIA_VALUE = re.compile(r"(c\d+) · (.+) \((.+)\)")


def payload(frame, mapping, operation, options, result, nearest=None, criteria=None, breaks=None, levels=None):
    """Contrato compacto anexado aos metadados do resultado (metadata.representacao).

    `breaks` lista as unidades sem trajetória (tendência NAO_AVALIAVEL por INCOMPARABILIDADE): a série
    as desenha só como pontos, sem linha entre competências (RQ-REP-15, AT-69). `levels` (rota de níveis)
    traz a coluna e a ordem dos níveis e os painéis da série."""
    rows, detail = result.get("rows") or [], result.get("detail_rows") or []
    # Distribuição e comparação com competência dos valores: um registro por território em detail_rows (indicadores e
    # mapa); a tabela principal da comparação continua sendo `rows`, com as relações.
    table = "detail_rows" if operation in ("distribution", "comparisons") and detail else "rows"
    data = detail if table == "detail_rows" else rows
    indicators = _indicators(operation, data, mapping, options, criteria)
    geometry = _geometry(frame, mapping, operation, options, result, nearest, criteria)
    notes = []
    if geometry["estado"] == "DISPONIVEL":
        complement = geometry.get("complemento_geografico") or {}
        if geometry["complementados"]:
            notes.append(f"Coordenadas de {len(geometry['complementados'])} território(s) com ponto inválido na fonte original "
                         f"vêm da camada geográfica complementar versionada ({complement.get('identificador')}, versão "
                         f"{complement.get('versao')}), sob a premissa do usuário de coordenada fixa de 2014 a 2024.")
        if geometry["sem_geometria"]:
            notes.append(f"{len(geometry['sem_geometria'])} território(s) sem coordenada válida na competência permanecem no "
                         "resultado e na tabela, fora do mapa.")
    if any(item.get("unidade") == "km" for item in indicators):
        notes.append(TPL_11)
    series = _series(operation, rows, detail, mapping, options, breaks)
    out = {"versao": VERSION, "tabela": table, "vinculo": _link(operation, mapping), "indicadores": indicators,
           "serie": series, "geometria": geometry, "notas": notes}
    if levels:
        out["niveis"] = levels.get("niveis")
        if series is not None:
            series["paineis"] = levels.get("paineis") or []
    return out


def _link(operation, mapping):
    """Coluna da tabela que identifica o território e como ela leva ao identificador estável."""
    coded = bool(mapping.get("territory_id"))
    if operation == "nearest":
        return {"coluna": "Código do alvo", "chave": "codigo"} if coded else {"coluna": "Território-alvo", "chave": "nome"}
    if operation == "criteria":
        return {"coluna": "Código", "chave": "codigo"} if coded else {"coluna": "Território", "chave": "nome"}
    return {"coluna": "Território", "chave": "rotulo"}


def _indicators(operation, data, mapping, options, criteria):
    keys = list(data[0]) if data else []
    out = []

    def add(column, label, kind, unit=None, origin=None, classes=None, note=None):
        if column in keys:
            item = {"coluna": column, "rotulo": label, "tipo": kind, "unidade": unit, "origem": origin,
                    "classes": classes, "nota": note}
            out.append({key: value for key, value in item.items() if value is not None})

    count_unit = count_unit_label(mapping, options)
    if count_unit == "pessoas" and options.get("fts_scope_confirmed") is True:
        count_unit = "profissionais"
    if operation == "criteria":
        add("Resultado", "Resultado dos critérios", "ESTADO", origin="CAP-SUB-01", classes=STATES)
        add("Posição", "Posição na ordenação", "POSICAO", origin="CAP-SUB-02")
        for column in keys:
            match = CRITERIA_VALUE.fullmatch(column)
            if match:
                unit = match.group(3)
                add(column, match.group(1) + " · " + match.group(2), "CONTINUO", unit, "CAP-SUB-01",
                    note=TPL_11 if unit in ("km", "m") else None)
        bands = (criteria or {}).get("faixas")
        column = next((key for key in keys if key.startswith("Faixa · ")), None)
        if bands and column:
            add(column, column, "CLASSE", origin=bands.get("capacidade"),
                classes=[item["faixa"] for item in bands["faixas"]] + ["Fora das faixas", "Não avaliável"])
    elif operation == "nearest":
        add("Distância (km)", "Distância à referência mais próxima", "CONTINUO", "km", "CAP-ESP-02", note=TPL_11)
        add("Alcance", "Alcance da distância", "ESTADO", origin="CAP-ESP-02", classes=REACH)
    elif operation == "spatial":
        add("Distância (km)", "Distância ao território de referência", "CONTINUO", "km", "CAP-ESP-01", note=TPL_11)
    elif operation == "temporal":
        # Classes e estados produzidos pelo motor (CAP-TEN-01 e CAP-TMP-01); o mapa continua não aplicável.
        unit = DENSITY_UNIT if options.get("temporal_indicator") == "density" else count_unit
        add("Tendência", "Tendência", "CLASSE", origin="CAP-TEN-01",
            classes=[LABELS[code] for code in CLASSES] + list(NOT_EVALUABLE_LABELS.values()))
        add("Direção da mudança", "Direção da mudança", "ESTADO", origin="CAP-TMP-01", classes=list(DIRECTIONS.values()))
        add("Variação absoluta", "Variação absoluta", "CONTINUO", unit, "CAP-TMP-01")
        add("Variação (%)", "Variação percentual", "CONTINUO", "%", "CAP-TMP-01")
    elif operation == "distribution":
        classes = sorted({str(row["Quintil"]) for row in data if row.get("Quintil")},
                         key=lambda text: (int(re.match(r"\d+", text).group()) if re.match(r"\d+", text) else 99, text))
        add("Quintil", "Classe da distribuição", "CLASSE", origin="CAP-DIS-02", classes=classes)
        add("Densidade por 1.000 habitantes", "Densidade", "CONTINUO", DENSITY_UNIT, "CAP-IND-02")
        add("Quantidade", "Quantitativo", "CONTAGEM", count_unit, "CAP-IND-01")
        add("População", "População", "CONTAGEM", "habitantes")
    elif operation not in WITHOUT_MAP:
        add("Posição", "Posição", "POSICAO", origin="CAP-SUB-02")
        add("Densidade por 1.000", "Densidade", "CONTINUO", DENSITY_UNIT, "CAP-IND-02")
        add("Quantidade", "Quantitativo", "CONTAGEM", count_unit, "CAP-IND-01")
        add("População", "População", "CONTAGEM", "habitantes")
    return out


def _series(operation, rows, detail, mapping, options, breaks=None):
    """Série temporal já calculada: competências como eixo; ausências permanecem lacunas; `quebras` sem linha."""
    data, table = (detail, "detail_rows") if operation == "temporal" and detail else (rows, "rows")
    if not data or "Período" not in data[0] or "Território" not in data[0]:
        return None
    if len({row["Período"] for row in data}) < 2:
        return None  # uma competência não forma série
    value = next((key for key in ("Densidade por 1.000", "Quantidade") if key in data[0]), None)
    if not value:
        return None
    unit = DENSITY_UNIT if value.startswith("Densidade") else count_unit_label(mapping, options)
    if unit == "pessoas" and options.get("fts_scope_confirmed") is True:
        unit = "profissionais"
    return {"tabela": table, "periodo": "Período", "territorio": "Território", "categoria": "Categoria",
            "valor": value, "unidade": unit, "tipo": "CONTINUO" if value.startswith("Densidade") else "CONTAGEM",
            "quebras": list(breaks or [])}


def _unavailable(reason, pending=None, period=None):
    item = {"estado": "INDISPONIVEL", "desfecho": "BLQ-DAD", "motivo": reason, "competencia": period}
    if pending:
        item["pendencia"] = pending
    return item


def _geometry(frame, mapping, operation, options, result, nearest, criteria):
    if operation in WITHOUT_MAP:
        return {"estado": "NAO_APLICAVEL", "motivo": "Mapa não aplicável: " + WITHOUT_MAP[operation] + "."}
    members = (result.get("metadata") or {}).get("universe", {}).get("members") or []
    if not members:
        return {"estado": "NAO_APLICAVEL", "motivo": "Mapa não aplicável: o resultado não tem territórios identificados."}
    # Só municípios têm ponto: Brasil e estados (níveis agregados) nunca entram no mapa nem em "sem_geometria".
    members = [item for item in members if item.get("nivel") == "MUN" or
               (item.get("nivel") is None and str(item.get("id", "")).startswith(("code:", "name:")))]
    if not members:
        return {"estado": "NAO_APLICAVEL", "motivo": "Mapa não aplicável: Brasil e estados são agregados sem ponto; "
                                                     "marque municípios para ver o mapa."}
    if nearest is not None:
        period = nearest["structured"].get("periodo_geometria")
    elif criteria is not None:
        period = criteria["structured"].get("periodo")
    elif operation == "comparisons" and ((result.get("metadata") or {}).get("comparacao") or {}).get("competencia_valores"):
        # Comparação com janela: o mapa usa as coordenadas da competência dos valores (uma só).
        period = result["metadata"]["comparacao"]["competencia_valores"]
    else:
        periods = (result.get("metadata") or {}).get("periods") or []
        if mapping.get("period") and len(periods) != 1:
            return _unavailable("O resultado reúne " + str(len(periods)) + " competências; o mapa usa as coordenadas de uma "
                                "única competência, pois elas podem mudar entre competências. Escolha uma competência.",
                                "COMPETENCIA_UNICA")
        period = periods[0] if mapping.get("period") else None
    if not mapping.get("latitude") or not mapping.get("longitude"):
        return _unavailable("Latitude e longitude não estão associadas; o mapa exige geometria autorizada.",
                            "COORDENADAS_NAO_ASSOCIADAS", period)
    # Configuração contextual de apresentação da versão governada Brasil nas análises sem
    # distância. Não é um padrão para uploads nem uma declaração sobre o datum original,
    # ausente na fonte: desenha os pontos sem alterar opções, pré-exame ou chave de execução.
    # Nas análises de distância, o referencial já é premissa governada do perfil (opção "crs").
    profile = None if options.get("crs") else curated_profile(frame, mapping)
    automatic = bool(profile and {"latitude", "longitude"} <= set(profile["governed_roles"]) and governed_version(frame))
    governed_crs = "crs" in (options.get("governed_premises") or [])
    if automatic:
        options = {**options, "crs": "SIRGAS2000", "number_format": options.get("number_format") or "decimal_comma"}
    elif "number_format" not in options:
        # Bases importadas: o separador das coordenadas verificado nos dados vale para desenhar os pontos; um valor
        # escolhido explicitamente prevalece. Formato misto continua pedindo a escolha (SEPARADOR_DECIMAL).
        from semantic_bridge import verified_separator
        if verified_separator(frame, mapping) == "decimal_comma":
            options = {**options, "number_format": "decimal_comma"}
    crs = canonical_crs(options.get("crs"))
    if not crs:
        if options.get("crs"):
            return _unavailable("Referencial geodésico informado não suportado nesta versão (somente SIRGAS2000); nenhuma "
                                "transformação é aplicada.", "REFERENCIAL_NAO_SUPORTADO", period)
        return _unavailable("Informe o referencial geodésico das coordenadas para habilitar o mapa; nenhum referencial é "
                            "presumido.", "REFERENCIAL_GEODESICO", period)
    if not _coordinate_roles_established(frame, mapping, options):
        return _unavailable("Escolha as colunas de latitude e longitude na preparação para ver o mapa.", "PAPEIS_COORDENADAS", period)
    ids = [item["id"] for item in members]
    try:
        if nearest is not None or (criteria is not None and criteria_needs(options)["spatial"]):
            # Mesma leitura (memorizada na requisição) que a referência mais próxima usou.
            inputs = nearest_inputs(frame, mapping, options)
            coordinates = inputs["coordinates"]
            ids += inputs["references"]["membros"]
        elif operation == "spatial":
            coordinates = territory_coordinates(scoped(frame, mapping, options), mapping, options)  # recorte da análise
        else:
            coordinates = territory_coordinates(_in_period(frame, mapping, period), mapping, options)
    except ChoiceRequired as exc:
        return _unavailable(str(exc), "SEPARADOR_DECIMAL" if "separador decimal" in str(exc) else "ESCOLHA_PENDENTE", period)
    except ValueError as exc:
        return _unavailable(str(exc), None, period)
    wanted = list(dict.fromkeys(ids))
    present = coordinates.reindex(wanted)
    point_ids, lat, lon, missing, complemented = [], [], [], [], []
    for key, row in zip(wanted, present.itertuples()):
        condition = row.condicao if isinstance(row.condicao, str) else "SEM_REGISTRO"
        if condition == "VALIDA":
            point_ids.append(key)
            lat.append(float(row.lat))
            lon.append(float(row.lon))
            if row.coordenada == "complementada":
                complemented.append(key)
        else:
            missing.append({"id": key, "condicao": condition, "motivo": MOTIVES.get(condition),
                            "texto": CONDITION_TEXT.get(condition)})
    complement = coordinates.attrs.get("complemento")
    return {"estado": "DISPONIVEL", "tipo": "PONTOS", "competencia": period, "referencial": crs,
            "configuracao_apresentacao": {"origem": "configuracao_contextual_base_brasil",
                "premissa": "SIRGAS2000 somente para apresentação dos pontos; datum não declarado na fonte original",
                "formato_coordenadas": options.get("number_format")} if automatic else None,
            "premissa_referencial": "SIRGAS 2000, premissa governada da base Brasil oficial; a fonte original não declara o "
                                    "referencial" if governed_crs else None,
            "fonte": "latitude e longitude da própria base, na competência do resultado",
            "ids": point_ids, "lat": lat, "lon": lon, "complementados": complemented, "sem_geometria": missing,
            "complemento_geografico": {key: complement[key] for key in
                                       ("estado", "arquivo", "sha256", "identificador", "versao", "premissa", "proveniencia")
                                       if complement.get(key) is not None} if complement else None}
