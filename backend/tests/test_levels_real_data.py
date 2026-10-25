"""Níveis Brasil, estados e municípios com a base versionada (job dados-reais; somente leitura, sem pulos no CI).

ADT_REAL_DATA_DIR indica a pasta com Dados_Brasil.xlsx, Dados_Estados_Brasil.csv e Dados_Municipios_Brasil.csv. Os
valores esperados vêm de uma leitura independente dos arquivos (pandas e Fraction), nunca do módulo testado; os SHA-256
das fontes são conferidos antes e depois. As requisições pesadas ficam em fixtures por módulo, para não alongar o job.
"""
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from brazil_data import FILES
from install_brazil_data import install
from main import app

client = TestClient(app)
PARTIAL_STATES = {("11", "201501"), ("31", "201501"), ("35", "201501"), ("42", "201701"), ("43", "201506"),
                  ("43", "202001")}
NOTE_2015 = ("Em junho de 2015, a base municipal não tem registro de 1 município (CRISTAL DO SUL, RS, 430607); a "
             "população do Brasil desse ano soma os 5.569 municípios com registro.")
# Nota UF_DECLARADA_DIVERGENTE: desde a correção de 25/10/2026 (o 251365 em 2016/6), nenhuma linha governada a gera.
UF_NOTE = "trazem na coluna uf um estado diferente do indicado pelo código IBGE"
TRACE = "Coordenada complementada (camada oficial)"
STATE_TYPE = "Unidades distintas: contagem estadual (não é a soma dos municípios)"
NO_POPULATION = "Não avaliável: população estadual incompleta nesta competência (DENOMINADOR_AUSENTE)"
# Código IBGE (dois dígitos) de cada sigla: tabela pública do IBGE, como na fonte municipal.
PREFIX = {"RO": "11", "AC": "12", "AM": "13", "RR": "14", "PA": "15", "AP": "16", "TO": "17", "MA": "21", "PI": "22",
          "CE": "23", "RN": "24", "PB": "25", "PE": "26", "AL": "27", "SE": "28", "BA": "29", "MG": "31", "ES": "32",
          "RJ": "33", "SP": "35", "PR": "41", "SC": "42", "RS": "43", "MS": "50", "MT": "51", "GO": "52", "DF": "53"}


@pytest.fixture(scope="module")
def real_sources():
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    yield paths
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


@pytest.fixture(scope="module")
def real(real_sources, tmp_path_factory):
    """Catálogo instalado a partir dos originais, inspeção municipal e leitura independente das três fontes."""
    folder = tmp_path_factory.mktemp("levels-real") / "brasil"
    install(real_sources[0].parent, folder)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(folder))
        response = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"})
        assert response.status_code == 200, response.text[:1000]
        files = {path.name: path for path in real_sources}
        municipal = pd.read_csv(files[FILES["municipal"]], sep=";", encoding="utf-8-sig", dtype=str)
        municipal["period"] = municipal.periodo_ano + municipal.periodo_mes.str.zfill(2)
        municipal["q"] = municipal.quantidade.astype(int)
        municipal["p"] = municipal["população_estimada"].astype(int)
        municipal["prefix"] = municipal.cod_ibge.str[:2]
        national = pd.read_excel(files[FILES["national"]], dtype=str)
        national["period"] = national.periodo_ano.astype(str) + national.periodo_mes.astype(str).str.zfill(2)
        counts = dict(zip(national.period, national.contagem.astype(int)))
        state = pd.read_csv(files[FILES["state"]], sep=";", encoding="utf-8", dtype=str)
        state["period"] = state.periodo_ano + state.periodo_mes.str.zfill(2)
        state["q"] = state.contagem.astype(int)
        yield {"info": response.json(), "municipal": municipal, "national": counts, "state": state,
               "state_counts": {(uf, period): q for uf, period, q in zip(state.uf, state.period, state.q)}}


def analyze(real, operation, abrangencia=None, **options):
    info = real["info"]
    if abrangencia is not None:
        options["abrangencia"] = abrangencia
    response = client.post("/api/analyze", data={
        "dataset": "brazil", "scope": "auto" if abrangencia is not None else "municipal",
        "dataset_version": info["source"]["version"], "operation": operation,
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options)})
    assert response.status_code == 200, response.text[:2000]
    return response.json()


def all_states(real):
    return [item["prefixo"] for item in real["info"]["niveis"]["estados"]]


def june_population(municipal, year):
    """Leitura independente de BR-POP-JUNHO-1: soma da população de junho, cada código uma vez."""
    june = municipal[municipal.period == year + "06"].drop_duplicates("cod_ibge")
    return int(june.p.sum()), sorted(set(municipal.cod_ibge) - set(june.cod_ibge))


@pytest.fixture(scope="module")
def brazil_density(real):
    return analyze(real, "density", {"brasil": True})


@pytest.fixture(scope="module")
def states_counts(real):
    return analyze(real, "counts", {"estados": all_states(real)})


@pytest.fixture(scope="module")
def states_density(real):
    return analyze(real, "density", {"estados": all_states(real)})


def state_population(municipal, prefix, period):
    """Leitura independente de UF-POP-MUNICIPIOS-1: soma da população dos municípios do estado (prefixo do código) na
    própria competência, cada código uma vez; None quando falta algum município do estado nessa competência."""
    members = set(municipal[municipal.prefix == prefix].cod_ibge)
    rows = municipal[(municipal.prefix == prefix) & (municipal.period == period)].drop_duplicates("cod_ibge")
    return int(rows.p.sum()) if set(rows.cod_ibge) == members else None


def state_series(real, sigla, periods, density=True):
    """Série independente de um estado: (competência, valor) válidos; a densidade sem população completa fica fora."""
    out = []
    for period in periods:
        quantity = real["state_counts"][(sigla, period)]
        if not density:
            out.append((period, Fraction(quantity)))
            continue
        population = state_population(real["municipal"], PREFIX[sigla], period)
        if population is not None:
            out.append((period, Fraction(quantity * 1000, population)))
    return out


def row_of(rows, territory, period):
    found = [row for row in rows if row["Território"] == territory and row["Período"] == period]
    assert len(found) == 1, (territory, period)
    return found[0]


def test_real_brazil_density_uses_the_national_count_and_the_june_population(real, brazil_density):
    municipal, counts = real["municipal"], real["national"]
    rows = {row["Período"]: row for row in brazil_density["rows"]}
    assert len(rows) == 22 and all(row["Nível"] == "Brasil (total nacional)" for row in rows.values())
    for period, row in rows.items():
        assert row["Quantidade"] == counts[period]  # contagem nacional, nunca a soma dos municípios
        assert row["Quantidade"] < int(municipal[municipal.period == period].q.sum())
        population, _ = june_population(municipal, period[:4])
        assert row["População"] == population and row["Competência da população"] == period[:4] + "06"
        assert row["Densidade por 1.000"] == pytest.approx(float(Fraction(counts[period] * 1000, population)), rel=1e-12)
        assert rows[period[:4] + "01"]["População"] == rows[period[:4] + "06"]["População"]
    latest = rows["202406"]
    assert (latest["Quantidade"], latest["População"]) == (502495, 212583750)
    assert round(latest["Densidade por 1.000"], 4) == 2.3638
    assert rows["202401"]["Densidade por 1.000"] == pytest.approx(2.3026924682625083, rel=1e-12)
    assert rows["201601"]["Densidade por 1.000"] == pytest.approx(1.6352593477236699, rel=1e-12)
    january_2016 = int(municipal[municipal.period == "201601"].drop_duplicates("cod_ibge").p.sum())
    assert rows["201601"]["População"] == 206084130 != january_2016 == 206084128  # nunca a população de janeiro
    assert rows["201701"]["Densidade por 1.000"] == pytest.approx(1.6883321334149035, rel=1e-12)
    assert rows["202001"]["Densidade por 1.000"] == pytest.approx(1.8474653692979441, rel=1e-12)
    # 2015: a população de junho soma os 5.569 municípios com registro (430607 ausente), avaliável com limitações.
    population_2015, missing = june_population(municipal, "2015")
    assert missing == ["430607"] and population_2015 == 204450315
    for period in ("201501", "201506"):
        assert rows[period]["População"] == population_2015 and rows[period]["Densidade por 1.000"] is not None
        assert rows[period]["Condição"] == "Avaliável com limitações: população nacional parcial (POPULACAO_NACIONAL_PARCIAL)"
    entries = {item["competencia"]: item for item in brazil_density["metadata"]["populacao_nacional"]}
    assert all(entries[period]["avaliabilidade"] == "AVALIAVEL" for period in rows if not period.startswith("2015"))
    for period in ("201501", "201506"):
        assert (entries[period]["avaliabilidade"], entries[period]["motivo"], entries[period]["ausentes"],
                entries[period]["incluidos"], entries[period]["previstos"]) == (
            "AVALIAVEL_COM_LIMITACOES", "POPULACAO_NACIONAL_PARCIAL", ["430607"], 5569, 5570)
        assert entries[period]["nota"] == NOTE_2015
    assert NOTE_2015 in brazil_density["notes"]
    # A nota de procedência da série não afirma 5.570 municípios em todos os anos (2015 soma 5.569).
    assert any(note.startswith("Brasil (total nacional): contagem nacional de médicos da base Brasil, não a soma dos "
                               "municípios. População: soma das populações estimadas dos municípios com registro em junho "
                               "de cada ano") for note in brazil_density["notes"])
    assert "POPULACAO_NACIONAL_PARCIAL" in brazil_density["metadata"]["evaluability"]["limitacoes"]
    # 2016: a linha do 251365 em junho, corrigida em 25/10/2026, traz a PB e a estimativa do IBGE de 2016 (2.685, a mesma
    # de janeiro), no lugar do PA e de 331.942; nenhuma nota de UF divergente.
    santarem = municipal[(municipal.cod_ibge == "251365") & (municipal.period == "201606")]
    assert santarem.uf.tolist() == ["PB"] and santarem.p.tolist() == [2685]
    assert rows["201606"]["População"] == june_population(municipal, "2016")[0] == 206084130
    assert not any(UF_NOTE in note for note in brazil_density["notes"])


def test_real_national_reference_is_the_same_in_the_old_and_new_routes(real):
    old = analyze(real, "density", period_filter="202406")
    every = analyze(real, "density", {"municipios": {"todos": True}}, period_filter="202406")
    assert len(old["rows"]) == 5570 and every["rows"] == old["rows"]
    for body in (old, every):
        reference = body["metadata"]["referencia_nacional"]
        [value] = reference["valores"]
        assert (value["numerador"], value["denominador"], value["competencia"], value["competencia_populacao"]) == (
            502495, 212583750, "202406", "202406")
        assert round(value["valor"], 4) == 2.3638 and value["avaliabilidade"] == "AVALIAVEL"
        assert body["metadata"]["representacao"]["referencias"][0]["valores"][0]["valor"] == value["valor"]
        assert body["metadata"]["metodos"]["populacao_nacional"] == "BR-POP-JUNHO-1"
    assert every["metadata"]["selecao_territorial"]["rota"] == "municipal"
    assert "Todos os municípios: os 5.570 municípios previstos nesta versão da base têm registro no recorte escolhido." in \
        every["notes"]


def test_real_states_use_the_state_source_and_the_population_of_their_municipalities(real, states_counts,
                                                                                    states_density, brazil_density):
    municipal, counts = real["municipal"], real["state_counts"]
    # As 594 contagens (27 UFs × 22 competências) vêm da fonte estadual como estão, nunca da soma dos municípios.
    rows = states_counts["rows"]
    assert len(rows) == len(counts) == 594
    assert {(row["Território"][-3:-1], row["Período"]): row["Quantidade"] for row in rows} == counts
    assert all(row["Nível"] == "Estado" and row["Tipo de contagem"] == STATE_TYPE and row["Condição"] == "Avaliável"
               for row in rows)
    # Por competência: Brasil ≤ Σ estados (quem atua em mais de um estado conta em cada um) ≤ Σ municípios (quem atua em
    # mais de um município do estado conta uma vez no estado).
    national = {row["Período"]: row["Quantidade"] for row in brazil_density["rows"]}
    by_period = {}
    for row in rows:
        by_period[row["Período"]] = by_period.get(row["Período"], 0) + row["Quantidade"]
    assert len(by_period) == 22
    for period, total in by_period.items():
        assert national[period] <= total <= int(municipal[municipal.period == period].q.sum()), period
    assert (national["202406"], by_period["202406"]) == (502495, 539090)
    # Densidade: população da própria competência, soma dos municípios do estado (código IBGE), só com todos presentes.
    members = municipal.groupby("prefix").cod_ibge.nunique()
    present = municipal.drop_duplicates(["cod_ibge", "period"]).groupby(["prefix", "period"]).agg(
        n=("cod_ibge", "size"), p=("p", "sum"), q=("q", "sum"))
    populations = {key: int(item["p"]) if item["n"] == members[key[0]] else None for key, item in present.iterrows()}
    density = states_density["rows"]
    assert len(density) == 594
    gaps = set()
    for row in density:
        sigla, period = row["Território"][-3:-1], row["Período"]
        population = populations[(PREFIX[sigla], period)]
        assert row["Quantidade"] == counts[(sigla, period)]
        if population is None:
            gaps.add((PREFIX[sigla], period))
            assert (row["População"], row["Densidade por 1.000"], row["Condição"]) == (None, None, NO_POPULATION)
        else:
            assert (row["População"], row["Condição"], row["Competência da população"]) == (population, "Avaliável", period)
            assert row["Densidade por 1.000"] == pytest.approx(float(Fraction(counts[(sigla, period)] * 1000, population)),
                                                               rel=1e-12)
    assert gaps == PARTIAL_STATES
    assert {(item["estado"], item["competencia"]) for item in states_density["metadata"]["populacao_estadual"]
            if item["populacao"] is None} == PARTIAL_STATES
    latest = [row for row in density if row["Período"] == "202406"]
    assert len(latest) == 27 and sum(row["População"] for row in latest) == 212583750
    sp = row_of(density, "São Paulo (SP)", "202406")
    assert (sp["Quantidade"], sp["População"]) == (148909, 45973194)
    assert sp["Densidade por 1.000"] == pytest.approx(3.2390396890849047, rel=1e-12)
    sp_2015 = row_of(density, "São Paulo (SP)", "201501")
    assert sp_2015["Cobertura"] == "População: 644 de 645 municípios; sem registro: 353286"
    assert ("São Paulo (SP) em janeiro de 2015: população estadual incompleta, 644 de 645 municípios com registro na fonte "
            "municipal (sem registro: 353286); a população não é estimada e a densidade do estado não é avaliada."
            ) in states_density["notes"]
    # PB em 2016/6: os 223 municípios pelo prefixo do código IBGE, com o 251365 corrigido (2.685), a mesma de janeiro.
    pb = {period: row_of(density, "Paraíba (PB)", period)["População"] for period in ("201601", "201606")}
    assert pb == {"201601": 3999415, "201606": 3999415}
    assert not any(UF_NOTE in note for note in states_density["notes"])
    # Contagem estadual acima da soma completa dos seus municípios (DF de 2014 a 2017): nota, e os valores entram como estão.
    above = sorted((sigla, period) for (sigla, period), quantity in counts.items()
                   if populations[(PREFIX[sigla], period)] is not None and
                   quantity > int(present.loc[(PREFIX[sigla], period), "q"]))
    assert [sigla for sigla, _ in above] == ["DF"] * 8
    divergence = [note for note in states_density["notes"] if "supera a soma das contagens dos seus municípios" in note]
    assert len(divergence) == len(above) and all(note.startswith("Distrito Federal (DF) em ") for note in divergence)
    assert ("Distrito Federal (DF) em janeiro de 2014: a contagem estadual de médicos únicos (7.832) supera a soma das "
            "contagens dos seus municípios na fonte municipal (4.640); as duas fontes divergem nesta competência e entram "
            "como estão.") in states_density["notes"]


def test_real_state_ranking_and_aggregations(real):
    counts, municipal = real["state_counts"], real["municipal"]
    ranking = analyze(real, "ranking", {"estados": all_states(real)}, period_filter="202406")
    densities = {sigla: Fraction(counts[(sigla, "202406")] * 1000, state_population(municipal, prefix, "202406"))
                 for sigla, prefix in PREFIX.items()}
    expected = sorted(densities, key=lambda sigla: (-densities[sigla], sigla))
    assert [row["Território"][-3:-1] for row in ranking["rows"]] == expected
    assert expected[:3] == ["DF", "SP", "RS"] and expected[-3:] == ["AM", "PA", "MA"]
    assert [row["Posição"] for row in ranking["rows"]] == list(range(1, 28))
    # Agregação de estados: soma das contagens estaduais e das populações (possível dupla contagem entre estados).
    north = [prefix for prefix in all_states(real) if prefix[0] == "1"]
    [row] = analyze(real, "aggregate", {"estados": north}, period_filter="202406")["rows"]
    siglas = [sigla for sigla, prefix in PREFIX.items() if prefix in north]
    quantity = sum(counts[(sigla, "202406")] for sigla in siglas)
    population = sum(state_population(municipal, PREFIX[sigla], "202406") for sigla in siglas)
    assert (row["Quantidade"], row["População"]) == (quantity, population) == (27384, 18669345)
    assert row["Tipo"] == "Soma dos componentes (possível dupla contagem)"
    assert row["Densidade por 1.000"] == pytest.approx(quantity / population * 1000)
    every_state = analyze(real, "aggregate", {"estados": all_states(real)}, period_filter="202406")
    [row] = every_state["rows"]
    # A soma dos 27 estados não é o total do Brasil: quem atua em mais de um estado conta em cada um.
    assert (row["Quantidade"], row["População"]) == (539090, 212583750) and row["Quantidade"] > real["national"]["202406"]
    assert any(note.startswith("Agregação de estados: soma das contagens estaduais") for note in every_state["notes"])
    aggregate = analyze(real, "aggregate", {"municipios": {"todos": True}}, period_filter="202406")
    [row] = aggregate["rows"]
    assert row["Quantidade"] == 817419 and row["População"] == 212583750 and "possível dupla contagem" in row["Tipo"]
    assert ("Soma dos 5.570 municípios (possível dupla contagem); não é o total do Brasil, que vem da contagem nacional."
            in aggregate["notes"])
    assert "referencia_nacional" not in aggregate["metadata"]


def test_real_251365_belongs_to_pb_and_state_groups_expand_to_municipalities(real):
    block = real["info"]["niveis"]
    members = {item["sigla"]: item["municipios"] for item in block["estados"]}
    assert len(members) == 27 and (members["PB"], members["SP"], members["MG"], members["DF"]) == (223, 645, 853, 1)
    assert all(item["objeto"] for item in block["estados"])  # as 27 UFs estão na fonte estadual
    assert block["fonte_estadual"]["disponivel"] and block["fonte_estadual"]["periodos"] == sorted(set(real["state"].period))
    assert block["regra_estado"] == "UF-CONTAGEM-ESTADUAL-1" and block["regra_populacao_estadual"] == "UF-POP-MUNICIPIOS-1"
    assert block["municipios"]["total"] == 5570
    assert [(item["competencia"], item["ausentes"]) for item in block["brasil"]["densidade_com_limitacoes"]] == [
        ("201501", ["430607"]), ("201506", ["430607"])]
    assert block["brasil"]["densidade_nao_avaliavel"] == []
    item = next(choice for choice in real["info"]["preflight"]["territory_choices"] if choice["code"] == "251365")
    assert (item["selection_reason"], item["state"], item["state_code"]) == ("", "PB", "25")
    # Desde a correção de 25/10/2026, a coluna uf do 251365 traz PB em todas as competências: nenhum município tem a nota.
    assert not any("hierarchy_note" in choice for choice in real["info"]["preflight"]["territory_choices"])
    group = analyze(real, "aggregate", {"municipios": {"estados": ["25"]}}, period_filter="202406")
    assert len(group["metadata"]["options"]["territory_ids"]) == 223
    assert "code:251365" in group["metadata"]["options"]["territory_ids"]


def test_real_spatial_analysis_with_all_municipalities_in_one_competencia(real):
    body = analyze(real, "spatial", {"municipios": {"todos": True}}, period_filter="202406",
                   reference_territory="MANAUS [130260]")
    assert len(body["rows"]) == 5570 and all(row["Distância (km)"] is not None for row in body["rows"])
    assert sum(row[TRACE] != "Não" for row in body["rows"]) == 6  # os seis pontos da camada complementar


def test_real_trend_anchors_for_brazil_and_states(real):
    periods = sorted(set(real["state"].period))
    full = analyze(real, "temporal", {"brasil": True, "estados": ["35", "43"]}, temporal_indicator="density")
    rows = {row["Território"]: row for row in full["rows"]}
    assert (rows["Brasil"]["Tendência"], rows["Brasil"]["Observações da tendência"]) == ("Crescimento", 22)
    # Estados: competência sem a população completa do estado é lacuna, fora das observações (SP em 2015/1; RS em 2015/6
    # e 2020/1); a série segue com as demais, e a mudança usa os extremos, que têm valor.
    for name, sigla, observed in (("São Paulo (SP)", "SP", 21), ("Rio Grande do Sul (RS)", "RS", 20)):
        series = state_series(real, sigla, periods)
        assert rows[name]["Observações da tendência"] == len(series) == observed, name
        assert rows[name]["Tendência"] == _classify(series), name
        assert rows[name]["Direção da mudança"] == "Aumento" and rows[name]["Tipo de contagem"] == STATE_TYPE, name
    assert full["metadata"]["representacao"]["serie"]["quebras"] == []
    june = [period for period in periods if period.endswith("06")]
    annual = analyze(real, "temporal", {"brasil": True, "estados": ["35", "43"]}, temporal_indicator="density",
                     period_filters=june)
    rows = {row["Território"]: row for row in annual["rows"]}
    assert (rows["Brasil"]["Tendência"], rows["Brasil"]["Observações da tendência"]) == ("Crescimento", 11)
    assert rows["São Paulo (SP)"]["Tendência"] == _classify(state_series(real, "SP", june)) == "Crescimento"
    rs = state_series(real, "RS", june)  # sem 2015/6
    assert (rows["Rio Grande do Sul (RS)"]["Tendência"], rows["Rio Grande do Sul (RS)"]["Observações da tendência"]) == (
        _classify(rs), 10)
    assert annual["metadata"]["tendencia"]["janela"]["serie_anual"] == "06"


def _june_density(municipal, codes, period):
    rows = municipal[(municipal.period == period) & municipal.cod_ibge.isin(codes)]
    return Fraction(int(rows.q.sum()) * 1000, int(rows.p.sum())), set(rows.cod_ibge)


def _months(period):
    return int(period[:4]) * 12 + int(period[4:])


def _classify(points):
    """Leitura independente da DA-15 sobre (competência, valor) válidos: velocidade = variação ÷ meses entre
    observações consecutivas, com Fraction."""
    speeds = [(b - a) / (_months(q) - _months(p)) for (p, a), (q, b) in zip(points, points[1:])]
    if all(v == 0 for v in speeds):
        return "Sem classificação"
    if any(v > 0 for v in speeds) and any(v < 0 for v in speeds):
        return "Sem classificação"
    base = "Crescimento" if all(v >= 0 for v in speeds) else "Declínio"
    if any(v == 0 for v in speeds):
        return base
    size = [abs(v) for v in speeds]
    steps = list(zip(size, size[1:]))
    if all(b >= a for a, b in steps) and any(b > a for a, b in steps):
        return {"Crescimento": "Aceleração do crescimento", "Declínio": "Aceleração de declínio"}[base]
    if all(b <= a for a, b in steps) and any(b < a for a, b in steps):
        return {"Crescimento": "Desaceleração do crescimento", "Declínio": "Desaceleração de declínio"}[base]
    return base


@pytest.fixture(scope="module")
def june_comparison(real):
    """Ten §5: densidade, série anual de junho, valores em 06/2024; Brasil, AM, SP, RS e três municípios do AM."""
    june = sorted(period for period in real["info"]["periods"] if period.endswith("06"))
    request = {"brasil": True, "estados": ["13", "35", "43"],
               "municipios": {"ids": ["code:130260", "code:130420", "code:130340"]}}
    return june, analyze(real, "comparisons", request, period_filters=june, comparison_values_period="202406",
                         comparison_indicator="density")


def test_real_comparison_window_relates_in_june_2024_and_trends_each_object(real, june_comparison):
    june, body = june_comparison
    municipal, counts = real["municipal"], real["national"]
    assert len(june) == 11 and {row["Período"] for row in body["rows"]} == {"202406"}
    assert not any("%" in key or "Razão" in key for row in body["rows"] + body["detail_rows"] for key in row)
    detail = {row["Território"]: row for row in body["detail_rows"]}
    assert list(detail) == ["Brasil", "Amazonas (AM)", "São Paulo (SP)", "Rio Grande do Sul (RS)", "MANAUS [130260]",
                            "PARINTINS [130340]", "TEFE [130420]"]  # municípios na ordem do código (RQ-REP-03)
    # Brasil: contagem nacional ÷ população de junho (BR-POP-JUNHO-1), lado a lado e sem relação com outros níveis.
    brazil = detail["Brasil"]
    assert (brazil["Quantidade"], brazil["População"]) == (502495, 212583750) and round(brazil["Densidade por 1.000"], 4) == 2.3638
    populations = [june_population(municipal, period[:4])[0] for period in june]
    expected = [(period, Fraction(counts[period] * 1000, population)) for period, population in zip(june, populations)]
    assert (brazil["Tendência"], brazil["Observações da tendência"]) == (_classify(expected), 11) == ("Crescimento", 11)
    assert body["rows"][0]["Condição"].startswith("Lado a lado: o Brasil é outro nível")
    # Estados: contagem estadual ÷ população dos seus municípios em cada junho; RS sem 2015/6 (população incompleta).
    sp_series = state_series(real, "SP", june)
    sp = detail["São Paulo (SP)"]
    assert (sp["Quantidade"], sp["População"], sp["Tipo de contagem"]) == (148909, 45973194, STATE_TYPE)
    assert round(sp["Densidade por 1.000"], 4) == 3.239 == round(float(sp_series[-1][1]), 4)
    assert sp["Tendência"] == _classify(sp_series) == "Crescimento"
    rs_series = state_series(real, "RS", june)
    rs = detail["Rio Grande do Sul (RS)"]
    assert (rs["Tendência"], rs["Observações da tendência"]) == (_classify(rs_series), 10)
    am_series = state_series(real, "AM", june)
    am = detail["Amazonas (AM)"]
    assert round(am["Densidade por 1.000"], 4) == 1.3991 == round(float(am_series[-1][1]), 4)
    assert am["Tendência"] == _classify(am_series)
    for name in ("MANAUS [130260]", "TEFE [130420]", "PARINTINS [130340]"):
        assert detail[name]["Tendência"] == "Sem classificação", name
        assert detail[name]["Motivo da tendência"] == "Mudança de direção", name
    for name, code, value in (("MANAUS [130260]", "130260", 2.0748), ("TEFE [130420]", "130420", 0.8704),
                              ("PARINTINS [130340]", "130340", 1.1574)):
        own = [(period, _june_density(municipal, {code}, period)[0]) for period in june]
        assert round(detail[name]["Densidade por 1.000"], 4) == value == round(float(own[-1][1]), 4)
        assert _classify(own) == "Sem classificação"
    # Relações só dentro do mesmo nível: estados entre si e municípios entre si (três de cada: sem diferenças de par).
    levels = [row["Nível"] for row in body["rows"]]
    assert levels == ["Brasil (total nacional)"] + ["Estado"] * 3 + ["Município"] * 3
    assert all(row.get("Diferença A − B") is None for row in body["rows"])
    groups = {group["nivel"]: group for group in body["metadata"]["comparacao"]["grupos"]}
    assert (groups["BR"]["relacoes"], groups["UF"]["relacoes"], groups["MUN"]["relacoes"]) == (False, True, True)
    tendencia = body["metadata"]["tendencia"]
    assert tendencia["desfecho"] == "RES-VAL"
    assert tendencia["nao_avaliaveis_por_motivo"] == {"SERIE_INSUFICIENTE": 0, "INCOMPARABILIDADE": 0}
    assert tendencia["janela"]["serie_anual"] == "06"
    resumo = body["metadata"]["representacao"]["resumo"]
    assert resumo["texto"].startswith("Na competência dos valores 202406: ")
    assert "Brasil (total nacional) lado a lado, sem relação: 2,36 por 1.000 habitantes." in resumo["texto"]
    assert body["metadata"]["representacao"]["geometria"]["estado"] == "DISPONIVEL"
    assert sorted(body["metadata"]["representacao"]["geometria"]["ids"]) == ["code:130260", "code:130340", "code:130420"]


def test_real_density_summary_and_national_series_for_the_card(real):
    body = analyze(real, "density", period_filter="202406")
    resumo = body["metadata"]["representacao"]["resumo"]
    assert resumo["texto"] == ("Na competência 202406, densidade por 1.000 habitantes: 5570 registros avaliáveis e 0 não "
                               "avaliáveis. Referência de contexto: taxa nacional de 2,36 por 1.000 habitantes (Brasil, "
                               "total nacional); não classifica nem colore os territórios.")
    serie = {item["competencia"]: item for item in body["metadata"]["referencia_nacional"]["serie"]}
    assert len(serie) == 22 and round(serie["202406"]["valor"], 4) == 2.3638
    assert serie["201506"]["avaliabilidade"] == "AVALIAVEL_COM_LIMITACOES"  # 2015: população de 5.569 municípios
    population, _ = june_population(real["municipal"], "2016")
    assert serie["201601"]["valor"] == pytest.approx(float(Fraction(real["national"]["201601"] * 1000, population)), rel=1e-12)
    assert resumo["indicadores"][-1]["papel"] == "REFERENCIA_DE_CONTEXTO"


def test_real_regions_follow_the_first_digit_of_the_ibge_code(real):
    """As Grandes Regiões da conversa ("estados da Região Norte") vêm do primeiro dígito do código IBGE e conferem com a
    coluna regiao_geografica da fonte municipal em todas as linhas, e a coluna uf, com o prefixo do código (até a correção de
    25/10/2026, a linha do 251365 em 2016/6 trazia o Norte e o PA)."""
    from territorial_selection import REGIONS
    municipal = real["municipal"]
    differs = municipal[municipal.cod_ibge.str[0].map(REGIONS) != municipal.regiao_geografica]
    assert differs.empty, list(zip(differs.cod_ibge, differs.period, differs.uf))
    assert (municipal.uf.map(PREFIX) == municipal.prefix).all()
    assert set(REGIONS.values()) == set(municipal.regiao_geografica)


def test_real_conversation_prepares_the_state_questions_and_the_levels_route_answers_them(real):
    """As quatro perguntas do pedido de 19/10/2026 pela gramática local: estados marcados na abrangência, competências da
    base e nenhuma escolha silenciosa (São Paulo é estado e município); o cálculo, pela mesma rota de níveis."""
    info = real["info"]
    form = {"dataset": "brazil", "dataset_version": info["source"]["version"], "mapping": json.dumps(info["suggested_mapping"])}

    def interpret(message, **options):
        response = client.post("/api/exploration/interpret", data={**form, "message": message,
                                                                   "options": json.dumps(options)})
        assert response.status_code == 200, response.text[:1000]
        body = response.json()
        assert body["handled"] is True and body.get("executed", False) is False
        return body

    counts, municipal = real["state_counts"], real["municipal"]
    periods = sorted(set(real["state"].period))
    minas = interpret("Quantos médicos havia em Minas Gerais em junho de 2024?")
    assert (minas["operation"], minas["estados"], minas["territory_ids"]) == ("counts", ["31"], [])
    assert minas["options_patch"] == {"period_filter": "202406", "period_filters": []}
    [row] = analyze(real, "counts", {"estados": ["31"]}, period_filter="202406")["rows"]
    assert (row["Território"], row["Quantidade"]) == ("Minas Gerais (MG)", counts[("MG", "202406")]) == ("Minas Gerais (MG)",
                                                                                                        61032)
    ambiguous = interpret("Qual era a densidade médica de São Paulo em 2024?")
    assert ambiguous["clarification"] == ("“São Paulo” identifica um estado e também um município. Diga “estado de São "
                                          "Paulo” ou “município de São Paulo”.")
    assert ambiguous["pending_operation"] == "density" and "estados" not in ambiguous and "territory_ids" not in ambiguous
    answer = interpret("estado de São Paulo", conversation_pending_operation="density")
    assert (answer["operation"], answer["estados"], answer["territory_ids"]) == ("density", ["35"], [])
    state = interpret("Qual era a densidade médica do estado de São Paulo em 2024?")
    assert state["estados"] == ["35"] and "Esta análise usa uma competência" in state["clarification"]
    [row] = analyze(real, "density", {"estados": ["35"]}, period_filter="202406")["rows"]
    assert (row["Quantidade"], row["População"]) == (148909, 45973194)
    assert row["Densidade por 1.000"] == pytest.approx(float(Fraction(148909 * 1000, 45973194)), rel=1e-12)
    city = interpret("Qual era a densidade médica do município de São Paulo em junho de 2024?")
    assert city["territory_ids"] == ["code:355030"] and "estados" not in city
    north = interpret("Compare a densidade médica dos estados da Região Norte.")
    assert (north["operation"], north["estados"], north["territory_ids"]) == (
        "comparisons", ["11", "12", "13", "14", "15", "16", "17"], [])
    assert north["options_patch"] == {"comparison_indicator": "density"}
    body = analyze(real, "comparisons", {"estados": north["estados"]}, period_filter="202406", comparison_indicator="density")
    values = {row["Território"][-3:-1]: row["Densidade por 1.000"] for row in body["rows"]}
    assert sorted(values) == sorted(sigla for sigla, prefix in PREFIX.items() if prefix[0] == "1")
    for sigla, value in values.items():
        population = state_population(municipal, PREFIX[sigla], "202406")
        assert value == pytest.approx(float(Fraction(counts[(sigla, "202406")] * 1000, population)), rel=1e-12), sigla
    assert all(row["Nível"] == "Estado" and row["Condição"] == "Comparável" for row in body["rows"])
    south = interpret("Mostre a evolução do número de médicos no Rio Grande do Sul entre 2014 e 2024.")
    assert (south["operation"], south["estados"], south["territory_ids"]) == ("temporal", ["43"], [])
    assert south["options_patch"] == {"period_filter": "", "period_filters": periods, "temporal_indicator": "quantity"}
    [row] = analyze(real, "temporal", {"estados": ["43"]}, period_filters=periods, temporal_indicator="quantity")["rows"]
    series = state_series(real, "RS", periods, density=False)
    assert (row["Território"], row["Inicial"], row["Final"]) == ("Rio Grande do Sul (RS)", 21680, 33985)
    assert (row["Tendência"], row["Observações da tendência"]) == (_classify(series), 22) == ("Crescimento", 22)
    assert row["Direção da mudança"] == "Aumento" and row["Tipo de contagem"] == STATE_TYPE
