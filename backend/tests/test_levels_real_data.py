"""Níveis Brasil, estados e municípios com a base versionada (job dados-reais; somente leitura, sem pulos no CI).

ADT_REAL_DATA_DIR indica a pasta com Dados_Brasil.xlsx e Dados_Municipios_Brasil.csv. Os valores esperados vêm de
uma leitura independente dos arquivos (pandas e Fraction), nunca do módulo testado; os SHA-256 das fontes são
conferidos antes e depois. As requisições pesadas ficam em fixtures por módulo, para não alongar o job.
"""
import hashlib
import json
import os
from fractions import Fraction
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from install_brazil_data import install
from main import app

client = TestClient(app)
PARTIAL_STATES = {("11", "201501"), ("31", "201501"), ("35", "201501"), ("42", "201701"), ("43", "201506"),
                  ("43", "202001")}
NOTE_2015 = ("Em junho de 2015, a base municipal não tem registro de 1 município (CRISTAL DO SUL, RS, 430607); a "
             "população do Brasil desse ano soma os 5.569 municípios com registro.")
NOTE_2016 = ("Em junho de 2016, 1 registro(s) da fonte municipal trazem na coluna uf um estado diferente do indicado pelo "
             "código IBGE (251365); o estado segue o código, e os valores entram como estão na fonte.")
TRACE = "Coordenada complementada (camada oficial)"


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
    """Catálogo instalado a partir dos originais, inspeção municipal e leitura independente das duas fontes."""
    folder = tmp_path_factory.mktemp("levels-real") / "brasil"
    install(real_sources[0].parent, folder)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(folder))
        response = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"})
        assert response.status_code == 200, response.text[:1000]
        csv = next(p for p in real_sources if p.suffix.lower() == ".csv")
        xlsx = next(p for p in real_sources if p.suffix.lower() == ".xlsx")
        municipal = pd.read_csv(csv, sep=";", encoding="utf-8-sig", dtype=str)
        municipal["period"] = municipal.periodo_ano + municipal.periodo_mes.str.zfill(2)
        municipal["q"] = municipal.quantidade.astype(int)
        municipal["p"] = municipal["população_estimada"].astype(int)
        national = pd.read_excel(xlsx, dtype=str)
        national["period"] = national.periodo_ano.astype(str) + national.periodo_mes.astype(str).str.zfill(2)
        counts = dict(zip(national.period, national.contagem.astype(int)))
        yield {"info": response.json(), "municipal": municipal, "national": counts}


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
    return analyze(real, "density", {"estados": all_states(real)}, period_filters=["201501", "201606", "202406"])


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
    assert rows["201601"]["Densidade por 1.000"] == pytest.approx(1.6326508900316625, rel=1e-12)
    assert rows["201601"]["Densidade por 1.000"] != pytest.approx(1.6352593636, rel=1e-6)  # nunca a população de janeiro
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
    # 2016: a população de junho inclui a linha do 251365 declarada PA na coluna uf (331.942), com nota.
    santarem = municipal[(municipal.cod_ibge == "251365") & (municipal.period == "201606")]
    assert santarem.uf.tolist() == ["PA"] and santarem.p.tolist() == [331942]
    assert rows["201606"]["População"] == june_population(municipal, "2016")[0] == 206413387
    assert NOTE_2016 in brazil_density["notes"]


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


def test_real_states_are_sums_of_municipalities_with_partial_support(real, states_counts, states_density, brazil_density):
    municipal = real["municipal"]
    rows = states_density["rows"]
    latest = [row for row in rows if row["Período"] == "202406"]
    assert len(latest) == 27 and all(row["Condição"] == "Avaliável" for row in latest)
    assert sum(row["Quantidade"] for row in latest) == 817419
    assert sum(row["População"] for row in latest) == 212583750
    sp = row_of(rows, "São Paulo (SP)", "202406")
    assert (sp["Quantidade"], sp["População"]) == (239208, 45973194)
    assert sp["Densidade por 1.000"] == pytest.approx(5.203206024797842, rel=1e-12)
    sp_2015 = row_of(rows, "São Paulo (SP)", "201501")
    assert (sp_2015["Quantidade"], sp_2015["População"]) == (138983, 44395267)
    assert sp_2015["Cobertura"] == "644 de 645 municípios; sem registro: 353286"
    assert sp_2015["Condição"] == "Avaliável com limitações: soma parcial (AGREGADO_PARCIAL)"
    assert ("São Paulo (SP) em janeiro de 2015: soma parcial, 644 de 645 municípios; sem registro: 353286. O valor não "
            "representa o estado inteiro.") in states_density["notes"]
    # PB em 2016/6 inclui o 251365 (declarado PA na fonte), pelo prefixo do código IBGE.
    assert row_of(rows, "Paraíba (PB)", "201606")["População"] == 4328672
    assert NOTE_2016 in states_density["notes"]
    support = states_counts["metadata"]["suporte_agregado"]
    assert {(item["estado"], item["competencia"]) for item in support if item["ausentes"]} == PARTIAL_STATES
    national = {row["Período"]: row["Quantidade"] for row in brazil_density["rows"]}
    by_period = {}
    for row in states_counts["rows"]:
        by_period[row["Período"]] = by_period.get(row["Período"], 0) + row["Quantidade"]
    assert len(by_period) == 22
    for period, total in by_period.items():
        assert total == int(municipal[municipal.period == period].q.sum())  # Σ UF = Σ MUN
        assert national[period] < total  # o Brasil nunca é a soma municipal
    assert all(row["Tipo de contagem"] == "Soma dos componentes (possível dupla contagem)" for row in states_counts["rows"])


def test_real_state_ranking_and_aggregation_of_all_municipalities(real):
    ranking = analyze(real, "ranking", {"estados": all_states(real)}, period_filter="202406")
    ordered = [row["Território"] for row in ranking["rows"]]
    assert ordered[:3] == ["São Paulo (SP)", "Rio Grande do Sul (RS)", "Santa Catarina (SC)"]
    assert ordered[-2:] == ["Maranhão (MA)", "Amazonas (AM)"]
    assert [row["Posição"] for row in ranking["rows"]] == list(range(1, 28))
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
    assert block["municipios"]["total"] == 5570
    assert [(item["competencia"], item["ausentes"]) for item in block["brasil"]["densidade_com_limitacoes"]] == [
        ("201501", ["430607"]), ("201506", ["430607"])]
    assert block["brasil"]["densidade_nao_avaliavel"] == []
    item = next(choice for choice in real["info"]["preflight"]["territory_choices"] if choice["code"] == "251365")
    assert (item["selection_reason"], item["state"], item["state_code"]) == ("", "PB", "25")
    assert "PA" in item["hierarchy_note"] and "(PB)" in item["hierarchy_note"]
    group = analyze(real, "aggregate", {"municipios": {"estados": ["25"]}}, period_filter="202406")
    assert len(group["metadata"]["options"]["territory_ids"]) == 223
    assert "code:251365" in group["metadata"]["options"]["territory_ids"]


def test_real_spatial_analysis_with_all_municipalities_in_one_competencia(real):
    body = analyze(real, "spatial", {"municipios": {"todos": True}}, period_filter="202406",
                   reference_territory="MANAUS [130260]")
    assert len(body["rows"]) == 5570 and all(row["Distância (km)"] is not None for row in body["rows"])
    assert sum(row[TRACE] != "Não" for row in body["rows"]) == 6  # os seis pontos da camada complementar


def test_real_trend_anchors_for_brazil_and_states(real):
    full = analyze(real, "temporal", {"brasil": True, "estados": ["35", "43"]}, temporal_indicator="density")
    rows = {row["Território"]: row for row in full["rows"]}
    assert (rows["Brasil"]["Tendência"], rows["Brasil"]["Observações da tendência"]) == ("Crescimento", 22)
    assert rows["São Paulo (SP)"]["Tendência"] == "Não avaliável: série não comparável"
    assert "201501: 353286 ausente" in rows["São Paulo (SP)"]["Motivo da tendência"]
    assert rows["São Paulo (SP)"]["Direção da mudança"] == "Aumento"  # mesmos membros em 2014/1 e 2024/6
    assert rows["Rio Grande do Sul (RS)"]["Tendência"] == "Não avaliável: série não comparável"
    breaks = full["metadata"]["representacao"]["serie"]["quebras"]
    assert {item["territorio"] for item in breaks} == {"São Paulo (SP)", "Rio Grande do Sul (RS)"}
    june = sorted(period for period in real["info"]["periods"] if period.endswith("06"))
    annual = analyze(real, "temporal", {"brasil": True, "estados": ["35", "43"]}, temporal_indicator="density",
                     period_filters=june)
    rows = {row["Território"]: row for row in annual["rows"]}
    assert (rows["Brasil"]["Tendência"], rows["Brasil"]["Observações da tendência"]) == ("Crescimento", 11)
    assert rows["São Paulo (SP)"]["Tendência"] == "Crescimento"
    assert rows["Rio Grande do Sul (RS)"]["Tendência"] == "Não avaliável: série não comparável"
    assert rows["Rio Grande do Sul (RS)"]["Motivo da tendência"] == (
        "Membros efetivos diferentes entre competências (201506: 430607 ausente)")
    assert annual["metadata"]["tendencia"]["janela"]["serie_anual"] == "06"
