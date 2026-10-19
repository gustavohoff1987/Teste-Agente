"""Níveis Brasil, estados e municípios na base oficial (D3, D4 e D5), com fontes sintéticas na CI.

O catálogo tem a coluna uf (com o 251365 declarado PA só em 2024/1), quatro competências municipais e uma competência
nacional a mais (2022/6), sem população municipal: ela testa a lacuna da densidade do Brasil, que nunca vira zero.
Em junho de 2024 falta o 130420: a população do Brasil de 2024 soma os municípios com registro (avaliável com
limitações, como 2015 na base real).
"""
import hashlib
import json
from fractions import Fraction

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import llm_bridge
import main
import territorial_levels as levels
from brazil_data import FILES
from catalog_support import use_external_catalog
from install_brazil_data import install
from temporal_change import evolution
from territorial_selection import territory_catalog

client = TestClient(main.app)
PERIODS = ["202301", "202306", "202401", "202406"]
NATIONAL = {"202206": 95, "202301": 100, "202306": 110, "202401": 120, "202406": 130}
MUNICIPAL = {  # código: (nome, uf, quantidades por competência, populações por competência)
    "130260": ("MANAUS", "AM", [40, 42, 44, 46], [1000, 1010, 1020, 1020]),
    "130420": ("TEFE", "AM", [10, 11, 12, None], [2000, 2000, 2000, None]),
    "130340": ("PARINTINS", "AM", [7, 7, 8, 8], [4000] * 4),
    "150140": ("BELEM", "PA", [50, 52, 54, 56], [3000] * 4),
    "251365": ("SANTAREM", "PB", [5] * 4, [500] * 4),
}
COORDINATES = {"130260": ("-3,1", "-60,0"), "130420": ("-3,3", "-64,7"), "130340": ("-2,6", "-56,7"),
               "150140": ("-1,4", "-48,5"), "251365": ("-6,5", "-38,4")}
AM = ["code:130260", "code:130340", "code:130420"]


def municipal_csv():
    lines = ["regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
             "quantidade;população_estimada"]
    for i, period in enumerate(PERIODS):
        for code, (name, uf, counts, populations) in MUNICIPAL.items():
            if counts[i] is None:
                continue
            declared = "PA" if code == "251365" and period == "202401" else uf
            region = "NORTE" if declared in ("AM", "PA") else "NORDESTE"
            lat, lon = COORDINATES[code]
            lines.append(f"{region};{declared};{name};{code};{lat};{lon};MEDICINA;{period[:4]};{int(period[4:])};"
                         f"{counts[i]};{populations[i]}")
    return "\n".join(lines) + "\n"


@pytest.fixture
def catalog(tmp_path, monkeypatch):
    source = tmp_path / "original"
    source.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for period, count in NATIONAL.items():
        book.active.append(["Brasil", int(period[:4]), int(period[4:]), "MEDICINA", count])
    book.save(source / FILES["national"])
    (source / FILES["municipal"]).write_text(municipal_csv(), encoding="utf-8")
    hashes = {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES.values()}
    destination = tmp_path / "resident"
    install(source, destination, governed=False)
    use_external_catalog(monkeypatch, destination)
    yield destination
    assert hashes == {name: hashlib.sha256((source / name).read_bytes()).hexdigest() for name in FILES.values()}


def inspected(scope="municipal"):
    response = client.post("/api/inspect", data={"dataset": "brazil", "scope": scope})
    assert response.status_code == 200, response.text
    return response.json()


def analyze(info, operation, abrangencia=None, scope=None, headers=None, **options):
    """Com abrangência, scope=auto (a análise resolve o recorte); sem ela, o caminho atual da fonte inspecionada."""
    if abrangencia is not None:
        options["abrangencia"] = abrangencia
    scope = scope or ("auto" if abrangencia is not None else info["source"]["scope"])
    return client.post("/api/analyze", headers=headers or {}, data={
        "dataset": "brazil", "scope": scope, "dataset_version": info["source"]["version"], "operation": operation,
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options)})


def ok(response):
    assert response.status_code == 200, response.text[:2000]
    return response.json()


def refused(response, text):
    assert response.status_code == 422, response.text[:2000]
    assert text in response.json()["detail"], response.json()["detail"]


def sources():
    return main._brazil_sources()


def by(rows, territory, period=None):
    found = [row for row in rows if row["Território"] == territory and (period is None or row["Período"] == period)]
    assert len(found) == 1, (territory, period, rows)
    return found[0]


# 1. Contrato e erros ---------------------------------------------------------------------------------------------
def test_contract_errors_canonical_ids_and_explicit_absorptions(catalog):
    info = inspected()
    upload = client.post("/api/analyze", files={"file": ("importada.csv", municipal_csv().encode())}, data={
        "operation": "density", "mapping": json.dumps(info["suggested_mapping"]),
        "options": json.dumps({"abrangencia": {"brasil": True}})})
    refused(upload, "A abrangência por Brasil e estados existe só na base Brasil oficial.")
    refused(analyze(info, "density", {"brasil": True}, territory_ids=["code:130260"]),
            "Use a abrangência territorial ou a lista de territórios, não as duas.")
    refused(analyze(info, "density", {"brasil": True}, scope="national"), "envie scope=auto")
    refused(analyze(info, "density", {}), "Nenhum território marcado na abrangência.")
    refused(analyze(info, "density", {"brasil": False, "estados": [], "municipios": {"todos": False}}),
            "Nenhum território marcado na abrangência.")
    for code in ("99", "3", "35"):  # "35": prefixo válido, mas sem membros nesta versão da base
        refused(analyze(info, "density", {"estados": [code]}), "Estado não reconhecido nesta base: " + code + ".")
    refused(analyze(info, "density", {"municipios": {"ids": ["code:130260", "code:130260"]}}),
            "identificadores distintos")
    refused(analyze(info, "density", {"municipios": {"ids": ["code:999999"]}}), "inexistentes")
    refused(analyze(info, "density", {"pais": True}), "Abrangência territorial inválida")

    a = levels.parse({"brasil": True, "estados": ["15", "13"], "municipios": {"estados": ["25"], "ids": ["code:150140"]}})
    assert levels.canonical_ids(a) == ["br", "uf:13", "uf:15", "mun:uf:25", "code:150140"]
    every = levels.parse({"municipios": {"todos": True, "estados": ["13"], "ids": ["code:150140"]}})
    assert every.absorvidos == ("mun:uf:13", "code:150140") and every.ids == () and every.mun_estados == ()
    group = levels.parse({"municipios": {"estados": ["13"], "ids": ["code:130260", "code:150140"]}})
    assert group.absorvidos == ("code:130260",) and group.ids == ("code:150140",)
    body = ok(analyze(info, "density", {"municipios": {"estados": ["13"], "ids": ["code:130260"]},
                                        "brasil": True}, period_filter="202306"))
    selection = body["metadata"]["selecao_territorial"]
    assert selection["absorvidos"] == ["code:130260"] and selection["ids_canonicos"] == ["br", "mun:uf:13"]
    assert selection["pedido"]["municipios"]["ids"] == ["code:130260"]
    assert body["metadata"]["options"]["abrangencia"] == {
        "brasil": True, "estados": [], "municipios": {"todos": False, "estados": ["13"], "ids": []}}


# 2. Roteamento e paridade ----------------------------------------------------------------------------------------
def test_routing_keeps_current_rows_for_municipalities_and_brazil_counts(catalog):
    info = inspected()
    old = ok(analyze(info, "density", period_filter="202306"))
    every = ok(analyze(info, "density", {"municipios": {"todos": True}}, period_filter="202306"))
    assert every["rows"] == old["rows"] and every["metadata"]["selecao_territorial"]["rota"] == "municipal"
    assert "Todos os municípios: os 5 municípios previstos nesta versão da base têm registro no recorte escolhido." in every["notes"]
    assert "territory_ids" not in every["metadata"]["options"]
    chosen = ["code:130260", "code:150140"]
    direct = ok(analyze(info, "counts", {"municipios": {"ids": chosen}}))
    assert direct["rows"] == ok(analyze(info, "counts", territory_ids=chosen))["rows"]
    national = inspected("national")
    current = ok(analyze(national, "counts", scope="national"))
    routed = ok(analyze(info, "counts", {"brasil": True}))
    assert routed["rows"] == current["rows"]
    assert routed["metadata"]["source"]["scope"] == "national" and routed["metadata"]["selecao_territorial"]["rota"] == "nacional"
    density = ok(analyze(info, "density", {"brasil": True}))
    assert density["metadata"]["source"]["scope"] == "niveis"
    assert density["metadata"]["source"]["fontes_usadas"] == ["national"]
    assert density["metadata"]["selecao_territorial"]["rota"] == "niveis"
    # scope=national continua sem densidade: a densidade do Brasil só existe pela abrangência.
    refused(analyze(national, "density", scope="national"), "")


# 3. Matriz de níveis por análise ---------------------------------------------------------------------------------
OBJECTS = {"brasil": {"brasil": True}, "estado": {"estados": ["13", "15"]},
           "municipio": {"municipios": {"ids": ["code:130260", "code:150140"]}}}
REASONS = {
    ("distribution", "brasil"): "Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só.",
    ("ranking", "brasil"): "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só.",
    ("aggregate", "brasil"): "Não se aplica: o total do Brasil vem pronto da fonte nacional e não é somado a outros territórios.",
    **{(op, "brasil"): "Não se aplica: as distâncias e os critérios usam a localização de cada município."
       for op in ("spatial", "nearest", "criteria")},
    **{(op, "estado"): "Não se aplica: estados não têm um ponto único. Para usar os municípios de um estado, marque o grupo "
                       "em Municípios." for op in ("spatial", "nearest", "criteria")},
    **{("rotation", level): "A rotatividade não está disponível nos dados do Brasil: falta um identificador da mesma pessoa "
                            "entre os períodos." for level in OBJECTS},
}


@pytest.mark.parametrize("operation", list(levels.OPERATION_LEVELS))
def test_matrix_accepts_and_refuses_levels_with_explicit_reasons(catalog, operation):
    index = levels.municipal_index(sources().frame("municipal"))
    rule = levels.OPERATION_LEVELS[operation]
    for level, raw in OBJECTS.items():
        # O Brasil vai com um município, para que o mínimo de dois objetos da comparação não decida o caso.
        a = levels.parse({**raw, **({"municipios": {"ids": ["code:130260"]}} if level == "brasil" else {})})
        if (operation, level) in REASONS:
            assert level not in rule["aceita"]
            with pytest.raises(ValueError) as error:
                levels.plan(a, operation, {}, index)
            assert str(error.value) == REASONS[(operation, level)]
        else:
            assert level in rule["aceita"]
            levels.plan(a, operation, {}, index)  # aceito: nenhuma exceção
    assert rule["texto"]


def test_minimum_and_mixture_are_checked_again_in_the_backend(catalog):
    info = inspected()
    refused(analyze(info, "ranking", {"estados": ["13"]}, period_filter="202306"),
            "Recortes e rankings precisa de pelo menos dois territórios do mesmo tipo.")
    refused(analyze(info, "distribution", {"estados": ["13", "15"], "municipios": {"ids": ["code:130260"]}},
                    period_filter="202306", distribution_indicator="density"), "Você marcou estados e municípios.")
    refused(analyze(info, "ranking", {"brasil": True, "estados": ["13", "15"]}, period_filter="202306"),
            "Não se aplica: o ranking ordena vários territórios, e o Brasil é um só.")
    refused(analyze(info, "comparisons", {"brasil": True}, period_filter="202306"), "pelo menos dois territórios")
    refused(analyze(info, "aggregate", {"municipios": {"ids": ["code:130260"]}}, period_filter="202306"),
            "A agregação precisa de pelo menos dois municípios.")


# 4. BR-POP-JUNHO-1 -----------------------------------------------------------------------------------------------
def test_national_population_is_the_june_sum_of_municipalities_without_estimation(catalog):
    index = levels.municipal_index(sources().frame("municipal"))
    june_2023 = levels.population_for(index, "202301")
    assert june_2023["populacao"] == 1010 + 2000 + 4000 + 3000 + 500 == 10510  # janeiro seria 10500
    assert june_2023["competencia_populacao"] == "202306" and june_2023["avaliabilidade"] == "AVALIAVEL"
    assert levels.population_for(index, "202306") == june_2023
    partial = levels.population_for(index, "202401")
    assert partial == levels.population_for(index, "202406")
    assert (partial["populacao"], partial["incluidos"], partial["previstos"]) == (1020 + 4000 + 3000 + 500, 4, 5)
    assert (partial["avaliabilidade"], partial["motivo"], partial["ausentes"]) == (
        "AVALIAVEL_COM_LIMITACOES", "POPULACAO_NACIONAL_PARCIAL", ["130420"])
    assert partial["nota"] == ("Em junho de 2024, a base municipal não tem registro de 1 município (TEFE, AM, 130420); "
                               "a população do Brasil desse ano soma os 4 municípios com registro.")
    gap = levels.population_for(index, "202206")
    assert (gap["populacao"], gap["avaliabilidade"], gap["motivo"]) == (None, "NAO_AVALIAVEL", "SEM_COMPETENCIA_DE_JUNHO")
    frame = pd.DataFrame([
        {"municipio": "A", "cod_ibge": "130001", "Período (ano e mês)": "202306", "categoria_profissional": "MEDICINA",
         "quantidade": "1", "população_estimada": "100"},
        {"municipio": "A", "cod_ibge": "130001", "Período (ano e mês)": "202306", "categoria_profissional": "OUTRA",
         "quantidade": "1", "população_estimada": "120"}])
    conflicting = levels._build_index(frame)
    with pytest.raises(ValueError, match="Populações conflitantes no mesmo município em junho de 2023"):
        levels.population_for(conflicting, "202301")


# 5. Densidade do Brasil ------------------------------------------------------------------------------------------
def test_brazil_density_uses_the_national_count_and_the_june_population(catalog):
    info = inspected()
    body = ok(analyze(info, "density", {"brasil": True}, period_filters=["202301"]))
    [row] = body["rows"]
    assert row["Nível"] == "Brasil (total nacional)" and row["Território"] == "Brasil"
    assert row["Quantidade"] == 100 != 40 + 10 + 7 + 50 + 5  # contagem nacional, nunca a soma dos municípios
    assert row["População"] == 10510 and row["Competência da população"] == "202306"
    assert row["Densidade por 1.000"] == pytest.approx(float(Fraction(100 * 1000, 10510)), rel=1e-12)
    assert row["Densidade por 1.000"] != pytest.approx(100 / 10500 * 1000)
    assert any(note.startswith("Brasil (total nacional): contagem nacional de médicos da base Brasil, não a soma dos "
                               "municípios. População: soma das populações estimadas dos 5 municípios em junho de 2023, "
                               "usada também em janeiro de 2023 (regra BR-POP-JUNHO-1).") for note in body["notes"])
    assert body["metadata"]["metodos"] == {"niveis": "NIVEIS-BR-UF-MUN-1", "populacao_nacional": "BR-POP-JUNHO-1"}
    assert "DENOMINADOR_ALTERNATIVO" in body["metadata"]["evaluability"]["limitacoes"]
    partial = ok(analyze(info, "density", {"brasil": True}, period_filters=["202406"]))
    [row] = partial["rows"]
    assert row["População"] == 8520 and row["Densidade por 1.000"] == pytest.approx(130 * 1000 / 8520, rel=1e-12)
    assert row["Condição"].startswith("Avaliável com limitações") and "POPULACAO_NACIONAL_PARCIAL" in row["Condição"]
    assert partial["metadata"]["populacao_nacional"][0]["ausentes"] == ["130420"]
    assert partial["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"
    assert "POPULACAO_NACIONAL_PARCIAL" in partial["metadata"]["evaluability"]["limitacoes"]
    assert levels.population_for(levels.municipal_index(sources().frame("municipal")), "202406")["nota"] in partial["notes"]
    # Série com um ano parcial (5 municípios em 2023, 4 em 2024): a nota de procedência não afirma um total único.
    series = ok(analyze(info, "density", {"brasil": True}, period_filters=PERIODS))
    assert any(note.startswith("Brasil (total nacional): contagem nacional de médicos da base Brasil, não a soma dos "
                               "municípios. População: soma das populações estimadas dos municípios com registro em junho "
                               "de cada ano, usada também em janeiro do mesmo ano (regra BR-POP-JUNHO-1).")
               for note in series["notes"])
    gap = ok(analyze(info, "density", {"brasil": True}, period_filters=["202206"]))
    [row] = gap["rows"]
    assert row["Quantidade"] == 95 and row["Densidade por 1.000"] is None and row["População"] is None
    assert "SEM_COMPETENCIA_DE_JUNHO" in row["Condição"]


# 6 e 7. Estados e blocos ------------------------------------------------------------------------------------------
def test_states_are_sums_of_their_municipalities_by_the_ibge_prefix(catalog):
    info = inspected()
    body = ok(analyze(info, "density", {"estados": ["13", "25"]}, period_filters=["202301", "202401", "202406"]))
    rows = body["rows"]
    complete = by(rows, "Amazonas (AM)", "202301")
    assert (complete["Quantidade"], complete["População"]) == (40 + 10 + 7, 1000 + 2000 + 4000)
    assert complete["Densidade por 1.000"] == pytest.approx(57 / 7000 * 1000)
    assert complete["Cobertura"] == "3 de 3 municípios" and complete["Condição"] == "Avaliável"
    partial = by(rows, "Amazonas (AM)", "202406")
    assert (partial["Quantidade"], partial["População"]) == (46 + 8, 1020 + 4000)
    assert partial["Cobertura"] == "2 de 3 municípios; sem registro: 130420"
    assert "AGREGADO_PARCIAL" in partial["Condição"]
    assert ("Amazonas (AM) em junho de 2024: soma parcial, 2 de 3 municípios; sem registro: 130420. O valor não representa "
            "o estado inteiro.") in body["notes"]
    for row in rows:
        assert row["Nível"] == "Estado (soma dos municípios)"
        assert row["Tipo de contagem"] == "Soma dos componentes (possível dupla contagem)"
        assert "pessoas únicas" not in json.dumps(row, ensure_ascii=False) and "Unidades distintas" not in row["Tipo de contagem"]
    # 251365: PB pelo prefixo do código, embora a coluna uf traga PA em 2024/1; nota de qualidade da fonte.
    assert by(rows, "Paraíba (PB)", "202401")["Quantidade"] == 5
    assert ("Em janeiro de 2024, 1 registro(s) da fonte municipal trazem na coluna uf um estado diferente do indicado pelo "
            "código IBGE (251365); o estado segue o código, e os valores entram como estão na fonte.") in body["notes"]
    support = {(item["estado"], item["competencia"]): item for item in body["metadata"]["suporte_agregado"]}
    assert support[("13", "202406")]["ausentes"] == ["130420"] and support[("13", "202406")]["previstos"] == 3
    assert support[("13", "202406")]["tipo"] == "SOMA_DOS_COMPONENTES" and support[("13", "202406")]["fundamento"] == "CAP-AGR-01"
    assert levels.NOTE_STATES in body["notes"]
    assert body["metadata"]["metodos"]["estado"] == "brasil-cod-uf-prefix-1"
    assert body["metadata"]["evaluability"]["status"] == "AVALIAVEL_COM_LIMITACOES"


def test_levels_appear_in_blocks_and_are_never_summed(catalog):
    info = inspected()
    body = ok(analyze(info, "counts", {"municipios": {"ids": ["code:130260"]}, "estados": ["13"], "brasil": True},
                      period_filter="202306"))
    assert [row["Nível"] for row in body["rows"]] == ["Brasil (total nacional)", "Estado (soma dos municípios)", "Município"]
    assert [row["Quantidade"] for row in body["rows"]] == [110, 42 + 11 + 7, 42]
    assert not any("Total" in str(value) for row in body["rows"] for value in row.values())
    assert levels.NOTE_LEVELS in body["notes"]
    assert "NIVEIS_TERRITORIAIS_DIFERENTES" in body["metadata"]["evaluability"]["limitacoes"]
    members = body["metadata"]["universe"]["members"]
    assert [(item["id"], item["nivel"]) for item in members] == [("br", "BR"), ("uf:13", "UF"), ("code:130260", "MUN")]
    assert body["metadata"]["universe"]["classification_scope"] == "universos separados por nível"
    assert body["metadata"]["representacao"]["niveis"]["ordem"] == [
        "Brasil (total nacional)", "Estado (soma dos municípios)", "Município"]
    # Janeiro com o Brasil e outro nível: a nota da competência da população.
    january = ok(analyze(info, "density", {"brasil": True, "municipios": {"ids": ["code:130260"]}}, period_filter="202301"))
    assert levels.NOTE_JANUARY in january["notes"]
    # Competência só da fonte nacional: o município fica não avaliável nela (sem erro e sem zero).
    gap = ok(analyze(info, "counts", {"brasil": True, "municipios": {"ids": ["code:130260"]}}, period_filters=["202206"]))
    assert [(row["Nível"], row["Quantidade"]) for row in gap["rows"]] == [("Brasil (total nacional)", 95), ("Município", None)]
    assert gap["rows"][1]["Condição"] == "Não avaliável: sem registro nesta competência na fonte municipal"


# 8. Ranking e distribuição ---------------------------------------------------------------------------------------
def test_state_ranking_and_distribution_are_universes_of_their_own(catalog):
    info = inspected()
    ranking = ok(analyze(info, "ranking", {"estados": ["13", "15", "25"]}, period_filter="202406"))
    rows = ranking["rows"]
    assert [(row["Posição"], row["Território"]) for row in rows[:2]] == [(1, "Pará (PA)"), (2, "Paraíba (PB)")]
    excluded = by(rows, "Amazonas (AM)")
    assert excluded["Posição"] is None and excluded["Densidade por 1.000"] is None
    assert excluded["Condição"] == "Não avaliável: agregado parcial (2 de 3 municípios; sem registro: 130420)"
    assert ranking["metadata"]["universe"]["classification_scope"] == "estados selecionados (soma dos municípios)"
    assert levels.NOTE_STATES_ORDER in ranking["notes"]
    refused(analyze(info, "ranking", {"estados": ["13", "15"]}, period_filter="202406"),
            "Menos de dois estados avaliáveis em junho de 2024: Amazonas (AM).")
    distribution = ok(analyze(info, "distribution", {"estados": ["13", "15", "25"]}, period_filter="202306",
                              distribution_indicator="density"))
    assert sorted(row["Território"] for row in distribution["detail_rows"]) == ["Amazonas (AM)", "Paraíba (PB)", "Pará (PA)"]
    assert {row["Nível"] for row in distribution["detail_rows"]} == {"Estado (soma dos municípios)"}
    assert sum(row["Unidades"] for row in distribution["rows"]) == 3
    assert distribution["metadata"]["representacao"]["geometria"]["estado"] == "NAO_APLICAVEL"


# 9. Comparações ---------------------------------------------------------------------------------------------------
def test_comparisons_relate_only_objects_of_the_same_level(catalog):
    info = inspected()
    body = ok(analyze(info, "comparisons", {"brasil": True, "estados": ["13", "15"], "municipios": {"ids": ["code:130260"]}},
                      period_filter="202306"))
    rows = body["rows"]
    assert [row["Nível"] for row in rows] == ["Brasil (total nacional)", "Estado (soma dos municípios)", "Município"]
    assert rows[0]["Condição"] == levels.SIDE_BY_SIDE["BR"] and rows[0]["Relação A/B"] is None
    assert (rows[1]["Objeto A"], rows[1]["Objeto B"], rows[1]["Relação A/B"]) == ("Amazonas (AM)", "Pará (PA)", "MENOR")
    assert rows[1]["Diferença A − B"] == pytest.approx(60 / 7010 * 1000 - 52 / 3000 * 1000)
    assert rows[2]["Condição"] == levels.SIDE_BY_SIDE["MUN"] and rows[2]["Diferença A − B"] is None
    pair = ok(analyze(info, "comparisons", {"brasil": True, "municipios": {"ids": ["code:130260", "code:150140"]}},
                      period_filter="202306", comparison_indicator="quantity"))
    assert pair["rows"][0]["Quantidade"] == 110 and pair["rows"][0]["Condição"] == levels.SIDE_BY_SIDE["BR"]
    assert (pair["rows"][1]["Objeto A"], pair["rows"][1]["Objeto B"]) == ("BELEM [150140]", "MANAUS [130260]")
    single = ok(analyze(info, "comparisons", {"estados": ["13"], "municipios": {"ids": ["code:150140"]}},
                        period_filter="202306"))
    assert single["rows"][0]["Condição"] == levels.SIDE_BY_SIDE["UF"]
    three = ok(analyze(info, "comparisons", {"estados": ["13", "15", "25"]}, period_filter="202306"))
    assert len(three["rows"]) == 3 and all(row.get("Diferença A − B") is None for row in three["rows"])  # AT-84


# 10. Evolução temporal --------------------------------------------------------------------------------------------
def test_temporal_state_with_changing_members_is_incomparable_and_brazil_gaps_stay_empty(catalog):
    info = inspected()
    body = ok(analyze(info, "temporal", {"brasil": True, "estados": ["13", "15"]}, period_filters=PERIODS,
                      temporal_indicator="density"))
    amazonas = by(body["rows"], "Amazonas (AM)")
    assert amazonas["Tendência"] == "Não avaliável: série não comparável"
    assert amazonas["Motivo da tendência"] == "Membros efetivos diferentes entre competências (202406: 130420 ausente)"
    assert amazonas["Direção da mudança"] is None and amazonas["Variação absoluta"] is None
    assert "INCOMPARABILIDADE" in amazonas["Condição da mudança"]
    assert by(body["rows"], "Pará (PA)")["Direção da mudança"] == "Aumento"
    tendencia = body["metadata"]["tendencia"]
    unit = next(item for item in tendencia["unidades"] if item["territorio"] == "Amazonas (AM)")
    assert unit["velocidades"] == [] and tendencia["nao_avaliaveis_por_motivo"]["INCOMPARABILIDADE"] == 1
    assert body["metadata"]["mudanca"]["nao_avaliaveis"]["INCOMPARABILIDADE"] == 1
    assert sum(body["metadata"]["mudanca"]["direcoes"].values()) == 2  # Brasil e Pará
    serie = body["metadata"]["representacao"]["serie"]
    assert serie["quebras"] == [{"territorio": "Amazonas (AM)", "categoria": "MEDICINA", "nivel": "UF", "periodos": ["202406"]}]
    assert [panel["id"] for panel in serie["paineis"]] == ["U", "S"]
    assert ("A mudança e a tendência de Amazonas (AM) não foram avaliadas: o número de municípios incluídos muda em junho "
            "de 2024. Escolha um intervalo sem essas competências para avaliá-las.") in body["notes"]
    brazil = by(body["rows"], "Brasil")
    assert brazil["Observações da tendência"] == 4 and brazil["Inicial"] == pytest.approx(100 / 10510 * 1000)
    # Competência nacional sem população de junho: lacuna (None), nunca zero, e fora das observações.
    full = ok(analyze(info, "temporal", {"brasil": True}, temporal_indicator="density"))
    gap = [row for row in full["detail_rows"] if row["Período"] == "202206"]
    assert gap == [{"Nível": "Brasil (total nacional)", "Território": "Brasil", "Período": "202206", "Categoria": "MEDICINA",
                    "Densidade por 1.000": None}]
    assert full["metadata"]["tendencia"]["unidades"][0]["ausentes"] == ["202206"]


def test_evolution_receives_change_incomparability_through_its_input():
    data = pd.DataFrame({"territory": ["S"] * 4 + ["T"] * 4, "period": ["1", "2", "3", "4"] * 2, "category": "C",
                         "quantity": [1.0, 2.0, 3.0, 4.0, 4.0, 3.0, 2.0, 1.0], "population": float("nan")})
    data["density"] = float("nan")
    positions = {"1": 1.0, "2": 2.0, "3": 3.0, "4": 4.0}
    rows, _, meta, moved, breaks = evolution(data, "quantity", positions, convention="numeric",
                                             incomparable={("S", "C"): "membros"}, change_incomparable={("S", "C"): "x"})
    assert rows[0]["Direção da mudança"] is None and rows[0]["Condição da mudança"] == "Não avaliável: x (INCOMPARABILIDADE)"
    assert rows[1]["Direção da mudança"] == "Redução"
    assert moved["direcoes"] == {"AUMENTO": 0, "REDUCAO": 1, "SEM_MUDANCA": 0}
    assert moved["nao_avaliaveis"] == {"SEM_REGISTRO_OBSERVADO": 0, "INCOMPARABILIDADE": 1}
    assert breaks == [{"territorio": "S", "categoria": "C"}]
    _, _, _, plain, _ = evolution(data, "quantity", positions, convention="numeric")
    assert plain["nao_avaliaveis"] == {"SEM_REGISTRO_OBSERVADO": 0}  # sem o parâmetro, o contrato de C2 não muda


# 11. Agregação ----------------------------------------------------------------------------------------------------
def test_aggregation_expands_states_into_their_municipalities(catalog):
    info = inspected()
    state = ok(analyze(info, "aggregate", {"estados": ["13"]}, period_filter="202301"))
    assert state["rows"] == ok(analyze(info, "aggregate", territory_ids=AM, period_filter="202301"))["rows"]
    assert state["rows"][0]["Quantidade"] == 57 and state["metadata"]["selecao_territorial"]["rota"] == "municipal"
    assert state["metadata"]["options"]["territory_ids"] == AM
    partial = ok(analyze(info, "aggregate", {"estados": ["13"]}, period_filter="202406"))
    assert (partial["rows"][0]["Quantidade"], partial["rows"][0]["População"]) == (54, 5020)
    assert ("Amazonas (AM) em junho de 2024: soma parcial, 2 de 3 municípios; sem registro: 130420. O valor não representa "
            "o estado inteiro.") in partial["notes"]
    assert "AGREGADO_PARCIAL" in partial["metadata"]["evaluability"]["limitacoes"]
    overlap = ok(analyze(info, "aggregate", {"estados": ["13"], "municipios": {"ids": ["code:130260"]}}, period_filter="202301"))
    assert overlap["rows"] == state["rows"] and "code:130260" in overlap["metadata"]["selecao_territorial"]["absorvidos"]
    every = ok(analyze(info, "aggregate", {"municipios": {"todos": True}}, period_filter="202301"))
    assert ("Soma dos 5 municípios (possível dupla contagem); não é o total do Brasil, que vem da contagem nacional."
            in every["notes"])
    refused(analyze(info, "aggregate", {"brasil": True, "estados": ["13"]}, period_filter="202301"),
            "Não se aplica: o total do Brasil vem pronto da fonte nacional")


# 12. Espacial, referência mais próxima e critérios ----------------------------------------------------------------
def test_distance_analyses_use_state_groups_as_municipalities_and_refuse_states(catalog):
    info = inspected()
    options = {"period_filter": "202301", "crs": "SIRGAS2000", "reference_territory": "MANAUS [130260]"}
    grouped = ok(analyze(info, "spatial", {"municipios": {"estados": ["13"]}}, **options))
    explicit = ok(analyze(info, "spatial", territory_ids=AM, **options))
    assert grouped["rows"] == explicit["rows"] and len(grouped["rows"]) == 3
    refused(analyze(info, "spatial", {"estados": ["13"]}, **options), "estados não têm um ponto único")
    refused(analyze(info, "criteria", {"estados": ["13"]}, period_filter="202301",
                    criteria={"attribute": "densidade", "operator": "<", "value": "4"}), "estados não têm um ponto único")
    refused(analyze(info, "nearest", {"brasil": True}, period_filter="202301"),
            "as distâncias e os critérios usam a localização de cada município")


# 13. Taxa nacional de referência (D5) -----------------------------------------------------------------------------
def test_national_reference_is_context_in_density_results_also_without_abrangencia(catalog, monkeypatch):
    info = inspected()
    old = ok(analyze(info, "density", period_filter="202306"))
    reference = old["metadata"]["referencia_nacional"]
    assert reference["papel"] == "REFERENCIA_DE_CONTEXTO" and reference["regra_populacao"] == "BR-POP-JUNHO-1"
    assert reference["nota"] == ("Taxa nacional como referência de contexto: não classifica nem colore os municípios e não "
                                 "entra em rankings, distribuições ou agregações.")
    [value] = reference["valores"]
    assert (value["competencia"], value["numerador"], value["denominador"], value["competencia_populacao"]) == (
        "202306", 110, 10510, "202306")
    assert value["valor"] == pytest.approx(float(Fraction(110000, 10510)), rel=1e-12) and value["avaliabilidade"] == "AVALIAVEL"
    assert old["metadata"]["representacao"]["referencias"][0]["valores"][0]["valor"] == value["valor"]
    assert old["metadata"]["metodos"] == {"populacao_nacional": "BR-POP-JUNHO-1"}
    assert old["metadata"]["evaluability"]["status"] == "AVALIAVEL"  # a referência não altera o resultado municipal
    levels_body = ok(analyze(info, "density", {"brasil": True, "municipios": {"todos": True}}, period_filter="202306"))
    brazil = by(levels_body["rows"], "Brasil")
    assert brazil["Densidade por 1.000"] == value["valor"] and brazil["Quantidade"] == value["numerador"]
    assert levels_body["metadata"]["referencia_nacional"]["valores"] == reference["valores"]
    municipal = [{key: row[key] for key in ("Território", "Período", "Categoria", "Quantidade", "População",
                                             "Densidade por 1.000")} for row in levels_body["rows"] if row["Nível"] == "Município"]
    assert municipal == old["rows"]  # as linhas municipais não mudam
    partial = ok(analyze(info, "report", period_filter="202406", report_indicator="density"))["metadata"]["referencia_nacional"]
    assert (partial["valores"][0]["avaliabilidade"], partial["valores"][0]["motivo"], partial["valores"][0]["ausentes"]) == (
        "AVALIAVEL_COM_LIMITACOES", "POPULACAO_NACIONAL_PARCIAL", ["130420"])
    for operation, extra in (("report", {"report_indicator": "quantity"}), ("counts", {}),
                             ("ranking", {}), ("aggregate", {})):
        body = ok(analyze(info, operation, period_filter="202306", **extra))
        assert "referencia_nacional" not in body["metadata"] and "metodos" not in body["metadata"], operation
    upload = client.post("/api/analyze", files={"file": ("importada.csv", municipal_csv().encode())}, data={
        "operation": "density", "mapping": json.dumps({**info["suggested_mapping"], "period": "periodo_ano"}),
        "options": json.dumps({"confirmed_roles": ["territory_id"], "period_filter": "2023"})})
    assert "referencia_nacional" not in upload.json().get("metadata", {})

    def broken(*_args, **_kwargs):
        raise ValueError("falha simulada")
    monkeypatch.setattr(levels, "population_for", broken)
    failed = ok(analyze(info, "density", period_filter="202306"))
    assert failed["rows"] == old["rows"]
    assert failed["metadata"]["referencia_nacional"] == {"estado": "INDISPONIVEL", "motivo": "falha simulada"}
    assert "metodos" not in failed["metadata"] and failed["metadata"]["representacao"]["referencias"] == []


# 14. Chave de execução -------------------------------------------------------------------------------------------
def test_execution_keys_are_reproducible_order_free_and_route_specific(catalog):
    info = inspected()
    key = lambda body: body["metadata"]["execution_key"]
    first = ok(analyze(info, "density", {"estados": ["15", "13"], "brasil": True}, period_filter="202306"))
    again = ok(analyze(info, "density", {"brasil": True, "estados": ["13", "15"]}, period_filter="202306"))
    assert key(first) == key(again)
    every = ok(analyze(info, "density", {"municipios": {"todos": True}}, period_filter="202306"))
    old = ok(analyze(info, "density", period_filter="202306"))
    assert len({key(first), key(every), key(old)}) == 3
    counts = ok(analyze(info, "counts", period_filter="202306"))
    assert "metodos" not in counts["metadata"] and "abrangencia" not in counts["metadata"]["options"]
    assert key(counts) == key(ok(analyze(info, "counts", period_filter="202306")))


# 15. Inspeção e pré-exame ----------------------------------------------------------------------------------------
def test_inspect_lists_levels_and_preflight_reports_each_level(catalog):
    info = inspected()
    block = info["niveis"]
    assert block["regra_estado"] == "brasil-cod-uf-prefix-1" and block["regra_populacao_nacional"] == "BR-POP-JUNHO-1"
    assert [(item["prefixo"], item["sigla"], item["rotulo_grupo"], item["municipios"]) for item in block["estados"]] == [
        ("13", "AM", "Municípios do Amazonas", 3), ("15", "PA", "Municípios do Pará", 1),
        ("25", "PB", "Municípios da Paraíba", 1)]
    assert block["municipios"] == {"total": 5}
    assert block["brasil"]["periodos"] == sorted(NATIONAL)
    assert [(item["competencia"], item["motivo"]) for item in block["brasil"]["densidade_nao_avaliavel"]] == [
        ("202206", "SEM_COMPETENCIA_DE_JUNHO")]
    assert [(item["competencia"], item["ausentes"]) for item in block["brasil"]["densidade_com_limitacoes"]] == [
        ("202401", ["130420"]), ("202406", ["130420"])]
    assert block["operacoes"]["density"]["aceita"] == ["brasil", "estado", "municipio"]
    assert block["operacoes"]["ranking"]["motivos"]["brasil"] == REASONS[("ranking", "brasil")]
    assert block["operacoes"]["comparisons"]["texto"].startswith("Compare dois ou mais territórios.")
    assert "niveis" not in inspected("national")
    upload = client.post("/api/inspect", files={"file": ("importada.csv", municipal_csv().encode())}).json()
    assert "niveis" not in upload
    response = client.post("/api/preflight", data={
        "dataset": "brazil", "scope": "auto", "dataset_version": info["source"]["version"], "operation": "density",
        "mapping": json.dumps(info["suggested_mapping"]),
        "options": json.dumps({"abrangencia": {"brasil": True, "estados": ["13"]}, "period_filter": "202306"})})
    assert response.status_code == 200, response.text
    body = response.json()
    density = body["capabilities"]["density"]
    assert density["status"] == "available" and set(density["niveis"]) == {"brasil", "estados"}
    ranking = body["capabilities"]["ranking"]
    assert ranking["status"] == "unavailable" and ranking["reasons"] == ["Brasil: " + REASONS[("ranking", "brasil")]]
    assert len(body["territory_choices"]) == 5  # a lista da tela vem sempre da fonte municipal inteira


def test_preflight_reports_a_pending_scope_choice_instead_of_refusing(catalog):
    """Mistura de níveis ou territórios de menos: o pré-exame devolve a escolha pendente (a tela mostra o motivo e mantém
    o cálculo bloqueado); o cálculo continua recusado com o mesmo texto."""
    info = inspected()

    def check(operation, abrangencia):
        response = client.post("/api/preflight", data={
            "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"], "operation": operation,
            "mapping": json.dumps(info["suggested_mapping"]),
            "options": json.dumps({"abrangencia": abrangencia, "period_filter": "202306", "distribution_indicator": "density"})})
        body = ok(response)
        capability = body["capabilities"][operation]
        assert capability["status"] == "needs_confirmation"
        assert capability["reasons"] == [body["abrangencia_pendente"]]
        assert capability["niveis"] == {"selecao": {"status": "needs_confirmation", "reasons": [body["abrangencia_pendente"]]}}
        assert len(body["territory_choices"]) == 5  # esquema da fonte municipal inteira
        refused(analyze(info, operation, abrangencia, period_filter="202306", distribution_indicator="density"),
                body["abrangencia_pendente"])
        return body["abrangencia_pendente"]

    assert check("distribution", {"estados": ["13"], "municipios": {"ids": ["code:130260"]}}) == (
        "Você marcou estados e municípios. Distribuição usa territórios do mesmo tipo: escolha qual manter.")
    assert check("ranking", {"municipios": {"ids": ["code:130260"]}}).endswith(
        "precisa de pelo menos dois territórios do mesmo tipo. Marque mais um.")
    assert check("aggregate", {"municipios": {"ids": ["code:130260"]}}) == "A agregação precisa de pelo menos dois municípios."


# 16. Conversa e provedor ------------------------------------------------------------------------------------------
def test_conversation_keeps_municipal_ids_and_the_provider_never_sees_levels(catalog, monkeypatch):
    info = inspected()
    form = {"dataset": "brazil", "dataset_version": info["source"]["version"], "mapping": json.dumps(info["suggested_mapping"])}
    parsed = client.post("/api/exploration/interpret", data={**form, "message": "Compare Manaus e Belém",
                                                             "options": "{}"}).json()
    assert set(parsed["territory_ids"]) == {"code:130260", "code:150140"}
    state = client.post("/api/exploration/interpret", data={**form, "message": "Compare os municípios da Paraíba",
                                                            "options": "{}"}).json()
    assert state["territory_ids"] == ["code:251365"]  # PB pelo prefixo do código IBGE
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    monkeypatch.setattr(llm_bridge, "_counter", 0)
    monkeypatch.setattr(llm_bridge, "_counter_day", "")
    headers = {"X-ADT-Session": client.post("/api/session").json()["token"]}
    abrangencia = {"brasil": True, "estados": ["13"], "municipios": {"ids": ["code:130260"]}}
    result = ok(analyze(info, "density", abrangencia, headers=headers, period_filter="202406"))
    assert result["conversation_reference"]["available"] is True
    sent = []

    async def provider(payload, *_args):
        sent.extend(payload)
        return {"intent": "ANALITICO", "topic": "none", "operation": "density", "indicator": "density",
                "period": "", "category": "", "territory": ""}

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    response = client.post("/api/llm/interpret-context", headers=headers, data={
        **form, "scope": "municipal", "options": json.dumps({"abrangencia": abrangencia}),
        "message": "Quero ver a densidade de outro jeito", "history": "[]", "displayed_result_id": result["result_id"]})
    assert response.status_code == 200, response.text
    assert sent, "o pedido analítico deveria chegar ao provedor minimizado"
    content = " ".join(sent)
    for forbidden in ("abrangencia", "referencia", "tendencia", "BR-POP", "Amazonas", "MANAUS", "130260", "Brasil (total",
                      "soma dos municípios", "suporte_agregado", "niveis", "130420", "TEFE", result["result_id"]):
        assert forbidden not in content, forbidden


# 17. Representação ------------------------------------------------------------------------------------------------
def test_representation_draws_only_municipalities_and_declares_levels(catalog, monkeypatch):
    info = inspected()
    body = ok(analyze(info, "density", {"brasil": True, "estados": ["13"], "municipios": {"ids": ["code:130260"]}},
                      period_filter="202306", crs="SIRGAS2000"))
    geometry = body["metadata"]["representacao"]["geometria"]
    assert geometry["estado"] == "DISPONIVEL" and geometry["ids"] == ["code:130260"] and geometry["sem_geometria"] == []
    assert body["metadata"]["representacao"]["referencias"][0]["valores"][0]["competencia"] == "202306"
    aggregated = ok(analyze(info, "density", {"brasil": True, "estados": ["13"]}, period_filter="202306"))
    assert aggregated["metadata"]["representacao"]["geometria"] == {
        "estado": "NAO_APLICAVEL", "motivo": "Mapa não aplicável: Brasil e estados são agregados sem ponto; marque "
                                             "municípios para ver o mapa."}
    assert "referencia_nacional" not in aggregated["metadata"]  # sem municípios, o Brasil já é linha própria
    series = ok(analyze(info, "density", {"brasil": True, "municipios": {"ids": ["code:130260"]}},
                        period_filters=["202301", "202306"]))["metadata"]["representacao"]["serie"]
    assert series["paineis"] == [{"id": "U", "rotulo": "Densidade · Municípios e Brasil (total nacional)",
                                  "niveis": ["MUN", "BR"], "tipo_contagem": "UNIDADES_DISTINTAS",
                                  "territorios": ["MANAUS [130260]", "Brasil"], "referencia": "Brasil"}]
    import representation

    def broken(*_args, **_kwargs):
        raise RuntimeError("falha simulada")
    request = {"brasil": True, "municipios": {"ids": ["code:130260"]}}
    first = ok(analyze(info, "counts", request, period_filter="202306"))
    monkeypatch.setattr(representation, "payload", broken)
    failed = ok(analyze(info, "counts", request, period_filter="202306"))
    assert failed["rows"] == first["rows"] and failed["metadata"]["execution_key"] == first["metadata"]["execution_key"]
    assert failed["metadata"]["representacao"]["geometria"]["estado"] == "INDISPONIVEL"


# 18. Catálogo oficial: 251365 ----------------------------------------------------------------------------------------
def test_251365_is_selectable_as_pb_only_in_the_official_profile(catalog):
    info = inspected()
    item = next(choice for choice in info["preflight"]["territory_choices"] if choice["code"] == "251365")
    assert (item["selection_reason"], item["state"], item["state_code"]) == ("", "PB", "25")
    assert item["hierarchy_note"] == ("Na fonte, a coluna uf deste município traz PA e PB em competências diferentes; o "
                                      "estado segue o código IBGE (PB).")
    assert ok(analyze(info, "counts", territory_ids=["code:251365"], period_filter="202401"))["rows"][0]["Quantidade"] == 5
    upload, _ = main.read_dataset(municipal_csv().encode(), "importada.csv")
    mapping = {"territory": "municipio", "territory_id": "cod_ibge", "period": "Período (ano e mês)"}
    choices = territory_catalog(upload, mapping, {"confirmed_roles": ["territory_id"]})
    blocked = next(choice for choice in choices if choice["code"] == "251365")
    assert blocked["selection_reason"] and blocked["state"] == "" and "hierarchy_note" not in blocked
