"""Página única de análise (contrato de 22/10/2026; Docs/PAINEL_INTEGRADO.md): POST /api/painel com `nivel`.

Cada extensão é conferida contra a análise existente da mesma capacidade, pelas rotas (/api/analyze), como em
test_painel.py: estados (abrangência por estados), tendência (evolução temporal), grupos por posição (distribuição),
faixas, condições e ordenação (critérios combinados), comparação, referência mais próxima (com empates), rotatividade
e a linha de contexto do Brasil (taxa nacional). O formato de 21/10 (sem `nivel`) continua em test_painel.py.

Catálogo sintético instalado como versão governada (como em test_painel.py), com valores fictícios em seis competências
de junho:
- MANAUS fica exatamente entre PARINTINS e BELEM (mesma latitude, longitudes simétricas): empate na referência;
- MANACAPURU e NOVO AIRAO empatam na densidade de 2024 (8 por 1.000); MANACAPURU não tem coordenadas;
- NOVO AIRAO só tem registro a partir de 2022 (série insuficiente e população estadual incompleta antes disso);
- TEFE tem quantidade zero em 2019 e 2020 (base zero).
As planilhas enviadas são de "distritos" e "províncias", sem código IBGE. Os testes com a base versionada, no fim,
rodam no job dados-reais (ADT_REAL_DATA_DIR), somente em leitura.
"""
import hashlib
import json
import os
import re
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import llm_bridge
import main
import painel
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from conversation_session import PANEL_KEEP, sessions
from install_brazil_data import install
from nearest_reference import GEOD
from territorial_levels import ROTATION

client = TestClient(main.app)
PERIODS = ["201906", "202006", "202106", "202206", "202306", "202406"]
HEADER = ("regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
          "quantidade;população_estimada")
# código: (nome, UF, latitude e longitude com vírgula decimal, quantidades e populações por competência)
UNITS = {
    "130260": ("MANAUS", "AM", ("-3", "-60"), [30, 35, 40, 44, 47, 50], [2000] * 6),
    "130420": ("TEFE", "AM", ("-3,5", "-64,7"), [0, 0, 5, 6, 6, 6], [600] * 6),
    "130340": ("PARINTINS", "AM", ("-3", "-61"), [20, 16, 14, 13, 12, 12], [1000] * 6),
    "130250": ("MANACAPURU", "AM", ("", ""), [8] * 6, [1000] * 6),
    "130390": ("NOVO AIRAO", "AM", ("-2,6", "-60,9"), [None, None, None, 3, 3, 4], [None, None, None, 500, 500, 500]),
    "150140": ("BELEM", "PA", ("-3", "-59"), [50, 51, 52, 54, 55, 56], [3000] * 6),
}
MANAUS, TEFE, PARINTINS, MANACAPURU, NOVO, BELEM = ("code:" + code for code in UNITS)
AM = [MANACAPURU, MANAUS, PARINTINS, NOVO, TEFE]  # ordem do código IBGE
STATE_COUNTS = {"AM": 100, "PA": 60}
TOP = {"competencia", "competencia_inicial", "categoria", "versao_base", "chave_execucao", "referencia", "itens",
       "dominios", "notas", "limitacoes", "nivel", "indicador", "rotulos", "disponibilidade", "contexto", "sessao",
       "resumo"}  # resumo: a frase-resumo do motor (23/10/2026; test_painel_resumo.py)
BRAZIL_LABELS = {"unidade": {"singular": "município", "plural": "municípios", "genero": "m"},
                 "grupo": {"singular": "estado", "plural": "estados", "genero": "m"}}


def municipal_text():
    lines = [HEADER]
    for i, period in enumerate(PERIODS):
        for code, (name, uf, (lat, lon), counts, populations) in UNITS.items():
            if counts[i] is None:
                continue
            lines.append(";".join(["NORTE", uf, name, code, lat, lon, "MEDICINA", period[:4], str(int(period[4:])),
                                   str(counts[i]), str(populations[i])]))
    return "\n".join(lines) + "\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """Repositório temporário com o catálogo sintético como versão governada (manifesto próprio)."""
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for period in PERIODS:
        book.active.append(["Brasil", int(period[:4]), int(period[4:]), "MEDICINA", 1000])
    book.save(root / FILES["national"])
    (root / FILES["municipal"]).write_text(municipal_text(), encoding="utf-8")
    write_state_source(root, {(uf, period): count for period in PERIODS for uf, count in STATE_COUNTS.items()})
    (root / GOVERNED_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (root / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(root)), encoding="utf-8")
    monkeypatch.setattr(brazil_data, "REPO_ROOT", root)
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    main._BRAZIL_FRAMES.clear()
    originals = {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES.values()}
    yield root
    assert originals == {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES.values()}
    main._BRAZIL_FRAMES.clear()


def inspection():
    response = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"})
    assert response.status_code == 200, response.text[:2000]
    return response.json()


def post(info, path="/api/painel", headers=None, revision=0, **options):
    return client.post(path, headers=headers or {}, data={
        "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
        "context_revision": str(revision), "mapping": json.dumps(info["suggested_mapping"]),
        "options": json.dumps(options)})


def page(info, headers=None, revision=0, **options):
    """Pedido da página única: nível municípios, densidade, junho de 2024 e os municípios do Amazonas."""
    return post(info, headers=headers, revision=revision,
                **{"nivel": "municipios", "indicador": "densidade", "competencia": "202406",
                   "base": {"municipios": {"estados": ["13"]}}, **options})


def analyze(info, operation, abrangencia=None, **options):
    if abrangencia is not None:
        options["abrangencia"] = abrangencia
    return client.post("/api/analyze", data={
        "dataset": "brazil", "scope": "auto" if abrangencia is not None else "municipal",
        "dataset_version": info["source"]["version"], "operation": operation,
        "mapping": json.dumps(info["suggested_mapping"]), "options": json.dumps(options)})


def ok(response):
    assert response.status_code == 200, response.text[:3000]
    return response.json()


def refused(response, text):
    assert response.status_code == 422, response.text[:2000]
    assert text in response.json()["detail"], response.json()["detail"]
    return response.json()


def by_id(body):
    return {item["id"]: item for item in body["itens"]}


def code_of(territory):
    """Id do item a partir do rótulo do motor ("MANAUS [130260]")."""
    return "code:" + territory.rsplit(" [", 1)[1].rstrip("]")


def km(a, b):
    (lat_a, lon_a), (lat_b, lon_b) = (tuple(float(v.replace(",", ".")) for v in UNITS[key[5:]][2]) for key in (a, b))
    return GEOD.inv(lon_a, lat_a, lon_b, lat_b)[2] / 1000


def criteria(info, ids, **options):
    """Critérios combinados (/api/analyze, operação criteria) nos municípios pedidos, em junho de 2024."""
    body = ok(analyze(info, "criteria", {"municipios": {"ids": ids}}, period_filter="202406", category_filter="MEDICINA",
                      crs="SIRGAS2000", number_format="decimal_comma", **options))
    return body["metadata"]["criterios"]


# --------------------------------------------------------------------------------------------- contrato
def test_page_contract_has_the_fixed_top_fields_and_strict_keys(repo):
    info = inspection()
    body = ok(page(info))
    assert set(body) == TOP
    assert (body["nivel"], body["indicador"], body["rotulos"]) == ("municipios", "densidade", BRAZIL_LABELS)
    assert [item["id"] for item in body["itens"]] == AM
    assert all(item["grupo_territorial"] == "13" for item in body["itens"])
    assert body["sessao"] == {"registrado": False, "result_id": None,
                              "motivo": "Sem sessão: o pedido não trouxe o cabeçalho X-ADT-Session."}
    # Campos por item só quando pedidos: nenhum dos campos das análises opcionais aparece sem o pedido.
    optional = {"tendencia", "grupo", "faixa", "faixa_distancia", "condicoes", "ordem", "rotatividade",
                "referencia_mais_proxima"}
    assert not optional & set(body["itens"][0])
    json.dumps(body, allow_nan=False)
    assert ok(page(info))["chave_execucao"] == body["chave_execucao"]
    assert ok(page(info, indicador="quantidade"))["chave_execucao"] != body["chave_execucao"]
    # Chaves estritas, mensagens em português.
    refused(page(info, desconhecida=1), "não reconhecido")
    refused(page(info, nivel="regioes"), "Nível do gráfico inválido")
    refused(post(info, nivel="municipios", competencia="202406", base={"municipios": {"todos": True}}),
            "Escolha o indicador do gráfico")
    refused(page(info, premissas={"crs": "SIRGAS2000"}), "as premissas vêm do perfil oficial")
    refused(page(info, rotulos={"unidade": {"singular": "distrito", "plural": "distritos"}}), "rótulos são fixos")
    # Sem `nivel`, a página única não vale: as chaves novas são desconhecidas (contrato de 21/10).
    legacy = refused(post(info, competencia="202406", base={"municipios": {"ids": [MANAUS]}},
                          tendencia={"competencias": PERIODS}), "não reconhecido")
    assert "nivel" in legacy["detail"]
    # Escolha pendente nos dois formatos: o texto em `detail` e a pendência estruturada, aqui sem chave de premissa que a
    # tela resolva (a ordem do critério é escolha do usuário).
    pending = {"competencia": "202406", "base": {"municipios": {"ids": [MANAUS]}},
               "referencia": {"membros": [MANAUS], "criterio": {"atributo": "densidade", "ordem": "maior"}}}
    for options in (pending, {**pending, "nivel": "municipios", "indicador": "densidade"}):
        choice = refused(post(info, **options), "Escolha a ordem do critério")
        assert choice["pendencia"] == {"chave": None, "opcoes": [], "texto": choice["detail"]}


def test_the_brazil_context_line_is_the_national_reference_of_the_density_analysis(repo):
    info = inspection()
    line = ok(page(info))["contexto"]["brasil"]
    assert set(line) == {"rotulo", "competencia", "densidade", "quantidade", "populacao", "competencia_populacao",
                         "avaliabilidade", "motivo", "nota", "regra_populacao"}
    analysis = ok(analyze(info, "density", {"municipios": {"ids": [MANAUS]}}, period_filter="202406"))
    [value] = analysis["metadata"]["referencia_nacional"]["valores"]
    assert line["densidade"] == value["valor"] == float(Fraction(1000 * 1000, 8100))
    assert (line["quantidade"], line["populacao"], line["competencia"]) == (1000, 8100, "202406")
    assert line["avaliabilidade"] == "AVALIAVEL" and line["regra_populacao"] == "BR-POP-JUNHO-1"
    assert "não classifica nem colore" in line["nota"]


def test_availability_explains_what_the_brazil_base_allows(repo):
    info = inspection()
    available = ok(page(info))["disponibilidade"]
    assert set(available) == {"distribuicao", "densidade", "espacial", "tendencia", "rotatividade", "estados", "grupos"}
    assert all(set(entry) == {"disponivel", "motivo", "pendencia"} for entry in available.values())
    assert {key for key, entry in available.items() if not entry["disponivel"]} == {"rotatividade"}
    assert available["rotatividade"]["motivo"] == ROTATION
    states = ok(post(info, nivel="estados", indicador="densidade", competencia="202406"))["disponibilidade"]
    # O motivo segue a estrutura reconhecida (rótulos da fonte, 23/10/2026): na base do Brasil, estados e municípios.
    assert states["espacial"] == {"disponivel": False, "pendencia": None, "motivo": (
        "No nível dos estados, a distância não se aplica: os estados não têm um ponto único. Abra os municípios de um "
        "estado para usar a análise espacial.")}
    refused(page(info, rotatividade={"inicial": "202306", "final": "202406"}), ROTATION)


# --------------------------------------------------------------------------------------------- estados
def test_states_level_uses_the_state_source_and_the_state_population(repo):
    info = inspection()
    body = ok(post(info, nivel="estados", indicador="densidade", competencia="202406", competencia_inicial="202006"))
    assert set(body) == TOP
    items = by_id(body)
    assert list(items) == ["uf:13", "uf:15"]
    assert all(item["tipo"] == "estado" and item["grupo_territorial"] is None for item in items.values())
    analysis = ok(analyze(info, "density", {"estados": ["13", "15"]}, period_filter="202406"))
    rows = {row["Território"]: row for row in analysis["rows"] if row["Nível"] == "Estado"}
    for item in items.values():
        row = rows[item["rotulo"]]
        assert (item["quantidade"], item["populacao"], item["densidade"]) == (
            row["Quantidade"], row["População"], row["Densidade por 1.000"])
    assert (items["uf:13"]["quantidade"], items["uf:13"]["populacao"]) == (100, 5100)
    assert items["uf:13"]["densidade"] == float(Fraction(100 * 1000, 5100)) and items["uf:15"]["densidade"] == 20
    # Em 2020, NOVO AIRAO não tem registro: a população do Amazonas não é estimada (DENOMINADOR_AUSENTE) e a variação
    # da densidade não é avaliável; a contagem estadual continua avaliável.
    amazonas = items["uf:13"]
    assert amazonas["inicial"] == {"populacao": None, "quantidade": 100, "densidade": None}
    assert amazonas["variacao_percentual"] == {"populacao": None, "quantidade": 0, "densidade": None}
    assert any("DADO_AUSENTE" in text for text in amazonas["motivos"])
    early = by_id(ok(post(info, nivel="estados", indicador="densidade", competencia="202006")))["uf:13"]
    assert early["densidade"] is None and early["quantidade"] == 100
    assert any("população estadual incompleta, 4 de 5 municípios" in text and "(DENOMINADOR_AUSENTE)" in text
               for text in early["motivos"])
    assert any(note.startswith("Estados: contagem de médicos únicos da fonte estadual") for note in body["notas"])
    # Estados não têm ponto único nem conjuntos no gráfico; a base vale só para municípios.
    states = {"nivel": "estados", "indicador": "densidade", "competencia": "202406"}
    refused(post(info, **states, base={"municipios": {"todos": True}}), "base vale só para municípios")
    refused(post(info, **states, referencia={"membros": [MANAUS]}), "estados não têm um ponto único")
    refused(post(info, **states, conjuntos=[{"id": "c", "rotulo": "x", "membros": [MANAUS, TEFE]}]), "Conjuntos de estados")
    refused(post(info, **states, faixas_distancia=[0, 100]), "não têm um ponto único")
    refused(post(info, **states, condicoes=[{"atributo": "distancia_km", "operador": ">", "valor": 1}]), "ponto único")


def test_states_level_with_the_chosen_states(repo):
    """Seleção de Territórios (24/10/2026): no nível estados, `estados` traz os estados escolhidos (prefixos IBGE ou ids
    uf:), com os mesmos valores do pedido com todos; sem a lista, todos, como antes."""
    info = inspection()
    states = {"nivel": "estados", "indicador": "densidade", "competencia": "202406"}
    todos = ok(post(info, **states))
    para = ok(post(info, **states, estados=["15"]))
    assert [item["id"] for item in para["itens"]] == ["uf:15"]
    assert para["itens"][0] == by_id(todos)["uf:15"]
    assert [item["id"] for item in ok(post(info, **states, estados=["uf:15", "13"]))["itens"]] == ["uf:13", "uf:15"]
    assert para["chave_execucao"] != todos["chave_execucao"]
    # A tendência e os grupos valem sobre os estados escolhidos.
    trend = ok(post(info, **states, estados=["15"], tendencia={"competencias": PERIODS}))
    assert trend["tendencia"]["universo"] == 1 and trend["itens"][0]["tendencia"]["motivo"] == "SERIE_ESTAVEL"
    refused(post(info, **states, estados=[]), "Estados inválidos")
    refused(post(info, **states, estados=["15", "15"]), "Estados inválidos")
    refused(post(info, **states, estados=["99"]), "Estado sem registro na fonte estadual: 99")
    refused(page(info, estados=["13"]), "A lista estados vale só no nível estados")


# --------------------------------------------------------------------------------------------- Brasil
def test_brazil_level_is_the_national_total_as_one_unit(repo):
    """O Brasil como unidade agregada (24/10/2026; decisões D3 e D4): um item só, com a contagem da fonte nacional e a
    população BR-POP-JUNHO-1, os mesmos valores da linha de contexto; a tendência é a da evolução temporal do Brasil;
    o que agrupa, ordena, filtra ou compara vários territórios não se aplica (matriz da D3)."""
    info = inspection()
    brazil = {"nivel": "brasil", "indicador": "densidade", "competencia": "202406"}
    body = ok(post(info, **brazil, competencia_inicial="202106"))
    assert set(body) == TOP
    [item] = body["itens"]
    assert (item["id"], item["tipo"], item["rotulo"], item["uf"], item["grupo_territorial"]) == (
        "br", "brasil", "Brasil", None, None)
    line = ok(page(info))["contexto"]["brasil"]
    assert (item["quantidade"], item["populacao"], item["densidade"]) == (line["quantidade"], line["populacao"],
                                                                          line["densidade"])
    before = ok(page(info, competencia="202106"))["contexto"]["brasil"]
    assert item["inicial"] == {"populacao": before["populacao"], "quantidade": before["quantidade"],
                               "densidade": before["densidade"]}
    assert item["variacao_percentual"]["quantidade"] == 0  # 1.000 nas duas competências
    if before["densidade"] is not None:
        exact = (Fraction(1000 * 1000, line["populacao"]) - Fraction(1000 * 1000, before["populacao"])) / \
            Fraction(1000 * 1000, before["populacao"]) * 100
        assert item["variacao_percentual"]["densidade"] == float(exact)
    # O próprio item é o total nacional: sem a linha de contexto; a nota diz a regra e que o Brasil não soma níveis.
    assert body["contexto"] == {"brasil": None}
    assert painel.NOTE_BRAZIL in body["notas"] and painel.NOTE_CONTEXT not in body["notas"]
    assert body["disponibilidade"]["espacial"] == {"disponivel": False, "motivo": painel.BRAZIL_NO_POINT, "pendencia": None}
    # Tendência: a mesma classe da evolução temporal do Brasil (abrangência nacional de /api/analyze), na mesma janela.
    window = PERIODS[2:]
    trend = ok(post(info, **brazil, tendencia={"competencias": window}))
    analysis = ok(analyze(info, "temporal", {"brasil": True}, temporal_indicator="density", period_filters=window))
    [row] = [row for row in analysis["rows"] if row["Território"].startswith("Brasil")]
    assert trend["itens"][0]["tendencia"]["rotulo"] == row["Tendência"]
    assert trend["tendencia"]["universo"] == 1
    # Funções de vários territórios e a distância não se aplicam; nas planilhas, não há nível Brasil.
    refused(post(info, **brazil, grupos={"tipo": "quartis"}), "a distribuição agrupa vários territórios, e o Brasil é um só")
    refused(post(info, **brazil, ordenar={"atributo": "densidade", "ordem": "desc"}), "e o Brasil é um só")
    refused(post(info, **brazil, comparar=["br", "uf:13"]), "e o Brasil é um só")
    refused(post(info, **brazil, referencia={"membros": [MANAUS]}), "o Brasil não tem um ponto único")
    refused(post(info, **brazil, base={"municipios": {"todos": True}}), "a unidade é o país inteiro")
    refused(post(info, **brazil, estados=["13"]), "A lista estados vale só no nível estados")
    refused(post(info, **brazil, rotatividade={"inicial": "202306", "final": "202406"}), ROTATION)
    refused(districts(nivel="brasil"), "O nível Brasil existe só na base do Brasil")


# --------------------------------------------------------------------------------------------- tendência
def test_trend_per_item_is_the_temporal_evolution_of_the_same_window(repo):
    info = inspection()
    window = PERIODS
    body = ok(page(info, tendencia={"competencias": window},
                   conjuntos=[{"id": "c1", "rotulo": "Manaus e Novo Airão", "membros": [MANAUS, NOVO]},
                              {"id": "c2", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]}]))
    items = by_id(body)
    analysis = ok(analyze(info, "temporal", {"municipios": {"ids": AM}}, temporal_indicator="density",
                          period_filters=window))
    rows = {code_of(row["Território"]): row for row in analysis["rows"]}
    speeds = {code_of(unit["territorio"]): unit["velocidades"] for unit in analysis["metadata"]["tendencia"]["unidades"]}
    details = {}
    for row in analysis["detail_rows"]:
        details.setdefault(code_of(row["Território"]), {})[row["Período"]] = row["Densidade por 1.000"]
    for key in AM:
        trend, row = items[key]["tendencia"], rows[key]
        assert set(trend) == {"classe", "familia", "rotulo", "motivo", "motivo_texto", "avaliavel", "observacoes",
                              "velocidades"}
        assert (trend["rotulo"], trend["motivo_texto"], len(trend["observacoes"])) == (
            row["Tendência"], row["Motivo da tendência"], row["Observações da tendência"])
        assert trend["velocidades"] == speeds[key]
        assert {point["competencia"]: point["valor"] for point in trend["observacoes"]} == {
            period: value for period, value in details[key].items() if value is not None}
    # As contagens do motor por classe (trend.summarize) são as da evolução temporal no mesmo universo.
    summary = analysis["metadata"]["tendencia"]
    assert body["tendencia"]["contagens"] == summary["contagens"]
    assert body["tendencia"]["nao_avaliaveis_por_motivo"] == summary["nao_avaliaveis_por_motivo"]
    assert body["tendencia"]["janela"]["periodos"] == window and body["tendencia"]["universo"] == 5
    assert items[MANACAPURU]["tendencia"]["classe"] == "SEM_CLASSIFICACAO"
    assert (items[MANACAPURU]["tendencia"]["familia"], items[MANACAPURU]["tendencia"]["motivo"]) == ("NENHUMA",
                                                                                                    "SERIE_ESTAVEL")
    assert items[NOVO]["tendencia"]["motivo"] == "SERIE_INSUFICIENTE" and items[NOVO]["tendencia"]["avaliavel"] is False
    assert items[MANAUS]["tendencia"]["familia"] == "CRESCIMENTO" and items[PARINTINS]["tendencia"]["familia"] == "DECLINIO"
    # Conjunto com membros diferentes na janela: INCOMPARABILIDADE pela entrada (CAP-AGR-01, F-05b), sem velocidades.
    assert items["c1"]["tendencia"]["motivo"] == "INCOMPARABILIDADE" and items["c1"]["tendencia"]["velocidades"] == []
    c2 = items["c2"]["tendencia"]
    # Cada competência pela agregação municipal (soma das quantidades / soma das populações × 1.000, como em _compute).
    assert c2["avaliavel"] is True and [point["valor"] for point in c2["observacoes"]] == [
        (a + b) / 3000 * 1000 for a, b in zip(UNITS["130260"][3], UNITS["130340"][3])]
    assert body["dominios"]["tendencia"] == [0, 25]
    assert any(note.startswith("Tendência (CAP-TEN-01, DA-15") for note in body["notas"])
    # Quantidade como indicador; janela de três competências: bloqueio do método (BLQ-MET), série insuficiente.
    counts = ok(page(info, indicador="quantidade", tendencia={"competencias": window}))
    analysis = ok(analyze(info, "temporal", {"municipios": {"ids": AM}}, temporal_indicator="quantity",
                          period_filters=window))
    assert counts["tendencia"]["contagens"] == analysis["metadata"]["tendencia"]["contagens"]
    short = ok(page(info, tendencia={"competencias": PERIODS[-3:]}))
    assert short["tendencia"]["desfecho"] == "BLQ-MET" and short["tendencia"]["bloqueio"]["motivo"] == "SERIE_INSUFICIENTE"
    assert all(item["tendencia"]["motivo"] == "SERIE_INSUFICIENTE" for item in short["itens"])
    refused(page(info, tendencia={"competencias": ["202406"]}), "Janela da tendência inválida")
    refused(page(info, tendencia={"competencias": ["202406", "209912"]}), "Competência inexistente")
    refused(page(info, tendencia=PERIODS), "Tendência inválida")


def test_states_trend_uses_the_state_values_in_the_window(repo):
    info = inspection()
    body = ok(post(info, nivel="estados", indicador="densidade", competencia="202406", tendencia={"competencias": PERIODS}))
    items = by_id(body)
    # Amazonas sem população completa até 2021 (NOVO AIRAO): três observações, série insuficiente; Pará estável.
    assert items["uf:13"]["tendencia"]["motivo"] == "SERIE_INSUFICIENTE"
    assert [point["competencia"] for point in items["uf:13"]["tendencia"]["observacoes"]] == PERIODS[3:]
    assert (items["uf:15"]["tendencia"]["classe"], items["uf:15"]["tendencia"]["motivo"]) == ("SEM_CLASSIFICACAO",
                                                                                            "SERIE_ESTAVEL")
    analysis = ok(analyze(info, "temporal", {"estados": ["13", "15"]}, temporal_indicator="density",
                          period_filters=PERIODS))
    labels = {row["Território"]: row["Tendência"] for row in analysis["rows"]}
    assert {item["rotulo"]: item["tendencia"]["rotulo"] for item in body["itens"]} == labels


# --------------------------------------------------------------------------------------------- grupos e faixas
def test_groups_by_position_are_the_distribution_of_the_same_units(repo):
    info = inspection()
    body = ok(page(info, grupos={"tipo": "quartis"}))
    analysis = ok(analyze(info, "distribution", {"municipios": {"ids": AM}}, distribution_indicator="density",
                          quantile_count=4, period_filter="202406"))
    expected = {code_of(row["Território"]): row["Quintil"] for row in analysis["detail_rows"]}
    items = by_id(body)
    assert {key: items[key]["grupo"]["rotulo"] for key in AM} == expected
    assert {key: items[key]["grupo"]["indice"] for key in AM} == {MANACAPURU: 1, NOVO: 1, TEFE: 2, PARINTINS: 3, MANAUS: 4}
    groups = body["grupos"]
    assert groups["contagens"] == [row["Unidades"] for row in analysis["rows"]] == [2, 1, 1, 1]
    values = [8, 25, 12, 8, 10]
    assert groups["cortes"] == [float(np.quantile(values, j / 4, method="linear")) for j in range(1, 4)] == [8, 10, 12]
    assert (groups["tipo"], groups["k"], groups["atributo"], groups["universo"]) == ("quartis", 4, "densidade", 5)
    quantity = ok(page(info, indicador="quantidade", grupos={"tipo": "quintis"}))
    analysis = ok(analyze(info, "distribution", {"municipios": {"ids": AM}}, distribution_indicator="quantity",
                          quantile_count=5, period_filter="202406"))
    expected = {code_of(row["Território"]): row["Quintil"] for row in analysis["detail_rows"]}
    assert {key: by_id(quantity)[key]["grupo"]["rotulo"] for key in AM} == expected
    refused(page(info, grupos={"tipo": "tercis"}), "Grupos por posição inválidos")
    refused(page(info, base={"municipios": {"ids": [MANAUS]}}, grupos={"tipo": "quartis"}), "pelo menos dois municípios")


def test_user_bands_and_distance_bands_are_the_combined_criteria_bands(repo):
    info = inspection()
    reference = {"membros": [PARINTINS, BELEM]}
    body = ok(page(info, faixas=[0, 10, 20, 30], faixas_distancia=["0", "100,5", "1000"], referencia=reference))
    items = by_id(body)
    expected = criteria(info, AM, bands={"attribute": "densidade", "limits": [0, 10, 20, 30]})["faixas"]
    assert {key: items[key]["faixa"]["rotulo"] for key in AM} == expected["pertenca"]
    assert {key: items[key]["faixa"]["indice"] for key in AM} == {MANACAPURU: 1, NOVO: 1, TEFE: 2, PARINTINS: 2, MANAUS: 3}
    assert body["faixas"]["rotulos"] == [entry["faixa"] for entry in expected["faixas"]] == ["0 a <10", "10 a <20", "20 a 30"]
    assert body["faixas"]["contagens"] == [entry["n"] for entry in expected["faixas"]] == [2, 2, 1]
    distance = criteria(info, AM, bands={"attribute": "distancia", "limits": ["0", "100,5", "1000"]},
                        reference_mode="list", reference_ids=reference["membros"])["faixas"]
    assert {key: items[key]["faixa_distancia"]["rotulo"] for key in AM if key != MANACAPURU} == distance["pertenca"]
    assert items[MANACAPURU]["faixa_distancia"] is None and body["faixas_distancia"]["nao_avaliaveis"] == 1
    assert body["faixas_distancia"]["capacidade"] == "CAP-ESP-03" and body["faixas"]["capacidade"] == "CAP-DIS-03"
    # Fora de todas as faixas e itens fora do universo (a referência de outro estado e os conjuntos).
    out = by_id(ok(page(info, faixas=[9, 11], referencia=reference)))
    assert out[MANAUS]["faixa"] == "fora" and out[TEFE]["faixa"] == {"indice": 1, "rotulo": "9 a 11"}
    assert out[BELEM]["faixa"] is None
    refused(page(info, faixas=[2, 1]), "crescentes e distintos")
    refused(page(info, faixas_distancia=[0, 100]), "exigem a referência")


# --------------------------------------------------------------------------------------------- condições e ordem
def test_conditions_are_the_combined_criteria_with_three_states(repo):
    info = inspection()
    conditions = [{"atributo": "densidade", "operador": "<", "valor": "15"},
                  {"atributo": "distancia_km", "operador": ">", "valor": 100}]
    reference = {"membros": [PARINTINS, BELEM]}
    body = ok(page(info, condicoes=conditions, referencia=reference))
    tree = {"logic": "and", "operands": [{"attribute": "densidade", "operator": "<", "value": "15"},
                                         {"attribute": "distancia", "operator": ">", "value": 100}]}
    structured = criteria(info, AM, criteria=tree, reference_mode="list", reference_ids=reference["membros"])
    expected = {item["elemento"]: item["estado"] for item in structured["avaliacoes"]}
    items = by_id(body)
    assert {key: items[key]["condicoes"]["situacao"] for key in AM} == expected
    assert expected == {MANACAPURU: "NAO_AVALIAVEL", MANAUS: "NAO_ATENDE", PARINTINS: "NAO_ATENDE", NOVO: "NAO_ATENDE",
                        TEFE: "ATENDE"}
    assert body["condicoes"]["contagens"] == {key: structured["contagens"][key]
                                              for key in ("ATENDE", "NAO_ATENDE", "NAO_AVALIAVEL")}
    gap = items[MANACAPURU]["condicoes"]["por_condicao"]
    assert [entry["estado"] for entry in gap] == ["ATENDE", "NAO_AVALIAVEL"]
    assert gap[1]["motivos"] == ["SEM_INFORMACAO_ESPACIAL"] and gap[0]["valor"] == 8
    assert items[TEFE]["condicoes"]["por_condicao"][1]["valor"] == km(TEFE, PARINTINS)
    assert [entry["texto"] for entry in body["condicoes"]["definicao"]] == [
        "densidade < 15 por 1.000 habitantes", "distância à referência mais próxima > 100 km"]
    assert items[BELEM]["condicoes"] is None  # a referência de outro estado não é do universo
    assert any("não constituem critério legal" in note for note in body["notas"])
    refused(page(info, condicoes=[{"atributo": "renda", "operador": "<", "valor": 1}]), "Atributo da condição")
    refused(page(info, condicoes=[{"atributo": "densidade", "operador": "~", "valor": 1}]), "Operador não autorizado")
    refused(page(info, condicoes=[{"atributo": "distancia_km", "operador": ">", "valor": 1}]), "exige a referência")


def test_ordering_shares_tied_positions_and_keeps_the_ties_at_the_cut(repo):
    info = inspection()
    body = ok(page(info, ordenar={"atributo": "densidade", "ordem": "asc", "primeiros": 1}))
    structured = criteria(info, AM, ranking={"attribute": "densidade", "direction": "asc", "top_n": 1})
    items = by_id(body)
    assert {key: items[key]["ordem"]["posicao"] for key in AM} == {
        entry["id"]: entry["posicao"] for entry in structured["ordenacao"]["posicoes"]}
    assert {key: items[key]["ordem"]["posicao"] for key in AM} == {MANACAPURU: 1, NOVO: 1, TEFE: 3, PARINTINS: 4,
                                                                  MANAUS: 5}
    chosen = {entry["id"] for entry in structured["selecao"]["membros"]}
    assert {key for key in AM if items[key]["ordem"]["selecionado"]} == chosen == {MANACAPURU, NOVO}
    ordering = body["ordenacao"]
    assert (ordering["selecionados"], ordering["empates_no_corte"]) == (2, True) and "EMPATE_NO_CORTE" in body["limitacoes"]
    # Variação percentual do indicador (CAP-TMP-01): base zero fica fora da ordenação, sem posição.
    change = by_id(ok(page(info, competencia_inicial="202006", ordenar={"atributo": "variacao", "ordem": "desc"})))
    assert change[TEFE]["ordem"]["posicao"] is None and change[NOVO]["ordem"]["posicao"] is None
    assert change[MANAUS]["ordem"]["posicao"] == 1  # 15 → 25 por 1.000
    refused(page(info, ordenar={"atributo": "variacao", "ordem": "desc"}), "exige a competência inicial")
    refused(page(info, ordenar={"atributo": "densidade", "ordem": "alfabetica"}), "Ordem inválida")


# --------------------------------------------------------------------------------------------- comparação e referência
def test_comparison_of_two_and_three_items_comes_from_the_engine(repo):
    info = inspection()
    body = ok(page(info, comparar=[TEFE, MANAUS]))
    [row] = ok(analyze(info, "comparisons", {"municipios": {"ids": [MANAUS, TEFE]}}, comparison_indicator="density",
                       period_filter="202406"))["rows"]
    comparison = body["comparacao"]
    assert [entry["id"] for entry in comparison["itens"]] == [TEFE, MANAUS]
    assert comparison["diferencas"] == [{"a": code_of(row["Objeto A"]), "b": code_of(row["Objeto B"]),
                                         "relacao": row["Relação A/B"], "diferenca": row["Diferença A − B"]}]
    assert comparison["diferencas"][0] == {"a": MANAUS, "b": TEFE, "relacao": "MAIOR", "diferenca": 15}
    assert (comparison["maior"], comparison["menor"]) == ([MANAUS], [TEFE])
    three = ok(page(info, comparar=[MANAUS, TEFE, PARINTINS]))["comparacao"]
    assert (three["maior"], three["menor"], three["diferencas"]) == ([MANAUS], [TEFE], [])
    assert {entry["id"]: entry["proximo_valor_maior"] for entry in three["relacoes"]} == {TEFE: 12, PARINTINS: 25,
                                                                                         MANAUS: None}
    assert any("sem diferenças automáticas entre pares" in note for note in three["notas"])
    # Um conjunto e um item de fora dele; itens relacionados (membros em comum) não são comparados.
    sets = [{"id": "c2", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]}]
    body = ok(page(info, conjuntos=sets, comparar=["c2", TEFE]))
    mixed = body["comparacao"]
    assert mixed["maior"] == ["c2"] and mixed["diferencas"][0]["diferenca"] == by_id(body)["c2"]["densidade"] - 10
    refused(page(info, conjuntos=sets, comparar=["c2", MANAUS]), "Itens relacionados não são comparados")
    refused(page(info, comparar=[MANAUS]), "Comparação inválida")
    refused(page(info, comparar=[MANAUS, BELEM]), "fora do gráfico")
    states = ok(post(info, nivel="estados", indicador="densidade", competencia="202406", comparar=["uf:15", "uf:13"]))
    assert states["comparacao"]["maior"] == ["uf:15"]


def test_nearest_reference_member_keeps_the_exact_ties(repo):
    info = inspection()
    reference = {"membros": [PARINTINS, BELEM]}
    items = by_id(ok(page(info, referencia=reference)))
    nearest = ok(analyze(info, "nearest", period_filter="202406", reference_mode="list", reference_ids=reference["membros"],
                         crs="SIRGAS2000", number_format="decimal_comma", category_filter="MEDICINA"))
    records = {record["unidade"]: record for record in nearest["metadata"]["nearest_reference"]["cobertura_referencias"]}
    assert km(MANAUS, PARINTINS) == km(MANAUS, BELEM)  # MANAUS fica exatamente no meio
    manaus = items[MANAUS]["referencia_mais_proxima"]
    assert manaus == {"id": PARINTINS, "rotulo": "PARINTINS (AM)",
                      "empate": [{"id": PARINTINS, "rotulo": "PARINTINS (AM)"}, {"id": BELEM, "rotulo": "BELEM (PA)"}]}
    assert [entry["id"] for entry in manaus["empate"]] == records[MANAUS]["minimo_completo"]["referencias"]
    assert items[TEFE]["referencia_mais_proxima"] == {"id": PARINTINS, "rotulo": "PARINTINS (AM)", "empate": []}
    assert items[TEFE]["distancia_km"] == records[TEFE]["minimo_completo"]["distancia_km"] == km(TEFE, PARINTINS)
    assert items[MANACAPURU]["referencia_mais_proxima"] is None
    assert items[BELEM]["referencia_mais_proxima"]["id"] == BELEM  # o próprio membro, a distância zero


# --------------------------------------------------------------------------------------------- escolha dos territórios
# Comando Seleção de Territórios (27/10/2026; no lugar do território de referência por elegibilidade de 24/10/2026): base e
# referência escolhidas do mesmo jeito (partir de, filtros com E e escolha), num objeto de consulta; a distância de cada município
# da base vai sempre até a referência mais próxima, sem ele mesmo. Densidades de junho de 2024: MANAUS 25, BELEM 18,67,
# PARINTINS 12, TEFE 10, MANACAPURU e NOVO AIRAO 8 (MANACAPURU sem coordenada); todos do Norte (1º dígito do código).
TODOS = [MANACAPURU, MANAUS, PARINTINS, NOVO, TEFE, BELEM]  # ordem do código IBGE
GEODESICA = {"medida": "geodesica", "ate": "referencia_mais_proxima"}


def lado(tipo="pais", regioes=(), ufs=(), filtros=(), modo="todos", municipios=()):
    return {"partir_de": {"tipo": tipo, "regioes": list(regioes), "ufs": list(ufs)}, "filtros": list(filtros),
            "escolha": {"modo": modo, "municipios": list(municipios)}}


def filtro(indicador, operador, valor):
    return {"indicador": indicador, "operador": operador, "valor": valor}


def consulta(base=None, referencia=None):
    """A consulta da janela: sem base, a seleção prévia (os municípios do Amazonas do pedido); sem referência, o país."""
    return {"base": base or lado("selecao_previa"), "referencia": referencia or lado(), "distancia": dict(GEODESICA)}


def reference_of(item):
    """As referências mais próximas de um item: a primeira e as empatadas."""
    found = item["referencia_do_item"]
    return [] if found is None else [entry["id"] for entry in found["empate"]] or [found["id"]]


def territorios(info, **options):
    """As contagens da janela (POST /api/painel/territorios), com a seleção prévia do Amazonas."""
    return post(info, path="/api/painel/territorios", **{"competencia": "202406", "base": {"municipios": {"estados": ["13"]}},
                                                          **options})


def test_consulta_selects_the_base_and_measures_the_nearest_reference_without_the_territory_itself(repo):
    """A base parte da seleção prévia (os municípios do Amazonas), e a referência, do país com densidade > 10 (CAP-SUB-01,
    valores exatos: TEFE, com 10, fica de fora). Para cada município da base, a referência mais próxima (CAP-ESP-02, mínimo do
    conjunto completo, com os empates), nunca ele mesmo; as referências não entram como itens."""
    info = inspection()
    body = ok(page(info, consulta=consulta(referencia=lado(filtros=[filtro("densidade", ">", 10)]))))
    items = by_id(body)
    assert list(items) == AM
    reference = body["referencia"]
    assert {key: value for key, value in reference.items() if key != "membros"} == {
        "tipo": "consulta",
        "consulta": {"base": lado("selecao_previa"), "referencia": lado(filtros=[filtro("densidade", ">", 10)]),
                     "distancia": GEODESICA},
        "base_texto": "da seleção prévia", "texto": "de todo o país com densidade > 10 por 1.000 habitantes",
        "contagens": {"base": {"partir_de": 5, "filtros": 5, "final": 5, "nao_avaliaveis": 0, "sem_referencia": 0},
                      "referencia": {"partir_de": 6, "filtros": 3, "final": 3, "nao_avaliaveis": 0}},
        "sem_referencia": [],
        "origem": ("Para cada município da base, o município mais próximo entre os municípios de todo o país com densidade > 10 "
                   "por 1.000 habitantes (3 municípios em junho de 2024); o próprio município não é a sua referência. Os "
                   "filtros são escolha do usuário e não têm caráter normativo")}
    assert [(member["id"], member["rotulo"], member["uf"]) for member in reference["membros"]] == [
        (MANAUS, "MANAUS (AM)", "AM"), (PARINTINS, "PARINTINS (AM)", "AM"), (BELEM, "BELEM (PA)", "PA")]
    for member in reference["membros"]:
        _, _, _, counts, populations = UNITS[member["id"].removeprefix("code:")]
        assert (member["populacao"], member["quantidade"]) == (populations[-1], counts[-1])
        assert member["densidade"] == pytest.approx(counts[-1] * 1000 / populations[-1], rel=1e-12)
    # MANAUS é referência, mas não é a sua: fica entre PARINTINS e BELEM, no empate exato.
    assert items[MANAUS]["referencia_do_item"] == {"id": PARINTINS, "rotulo": "PARINTINS (AM)", "empate": [
        {"id": PARINTINS, "rotulo": "PARINTINS (AM)"}, {"id": BELEM, "rotulo": "BELEM (PA)"}]}
    assert items[MANAUS]["distancia_km"] == km(MANAUS, PARINTINS) == km(MANAUS, BELEM)
    assert reference_of(items[PARINTINS]) == [MANAUS] and items[PARINTINS]["distancia_km"] == km(PARINTINS, MANAUS)
    for key in (TEFE, NOVO):
        assert reference_of(items[key]) == [PARINTINS] and items[key]["distancia_km"] == km(key, PARINTINS)
    assert items[MANACAPURU]["distancia_km"] is None and items[MANACAPURU]["referencia_do_item"] is None
    assert any("(SEM_INFORMACAO_ESPACIAL)" in text for text in items[MANACAPURU]["motivos"])
    assert all(item["referencia_mais_proxima"] is None and not item["referencia"] for item in items.values())
    assert any(note.startswith("Escolha dos territórios. Base: os municípios da seleção prévia (5 municípios). Referência: "
                               "Para cada município da base") for note in body["notas"])
    assert "DISTANCIA_GEODESICA_DIRETA" in body["limitacoes"]
    assert ("Distância em linha reta até a referência mais próxima de cada município (o mais próximo entre os municípios de "
            "todo o país com densidade > 10 por 1.000 habitantes): ") in body["resumo"]["texto"]
    # As referências são as do critério de densidade da análise existente (CAP-REF-01), e os municípios fora dele têm a mesma
    # distância da referência mais próxima dela.
    nearest = ok(analyze(info, "nearest", period_filter="202406", reference_mode="criterion",
                         reference_criterion={"operator": ">", "value": "10"}, crs="SIRGAS2000",
                         number_format="decimal_comma", category_filter="MEDICINA"))["metadata"]["nearest_reference"]
    assert sorted(member["id"] for member in nearest["conjunto_referencias"]["membros"]) == sorted([MANAUS, PARINTINS, BELEM])
    records = {record["unidade"]: record for record in nearest["cobertura_referencias"]}
    for key in (TEFE, NOVO):
        assert items[key]["distancia_km"] == records[key]["minimo_completo"]["distancia_km"]
        assert reference_of(items[key]) == records[key]["minimo_completo"]["referencias"]
    # Ida e volta sem perda: a consulta devolvida, enviada de novo, é o mesmo pedido (a mesma chave de execução).
    again = ok(page(info, consulta=reference["consulta"]))
    assert again["chave_execucao"] == body["chave_execucao"] and again["referencia"]["consulta"] == reference["consulta"]


def test_consulta_steps_start_from_filters_and_choice_as_in_the_command(repo):
    """Partir de, filtros e escolha (critérios de aceite 1, 2, 5, 6, 7 e 8, na base sintética): município selecionado = está em
    partir de E atende a todos os filtros E, no modo marcados, está entre os marcados."""
    info = inspection()
    ref = lado(filtros=[filtro("densidade", ">", 10)])

    def base(**options):
        body = ok(page(info, consulta=consulta(lado(**options), ref)))
        return [item["id"] for item in body["itens"]], body["referencia"]["contagens"]["base"]
    # Todo o país, sem filtro, todos: entram todos os municípios.
    assert base() == (TODOS, {"partir_de": 6, "filtros": 6, "final": 6, "nao_avaliaveis": 0, "sem_referencia": 0})
    # Uma região com filtro de densidade: só os do Norte abaixo de 15, e as contagens das etapas.
    assert base(tipo="regioes", regioes=["Norte"], filtros=[filtro("densidade", "<", 15)]) == (
        [MANACAPURU, PARINTINS, NOVO, TEFE], {"partir_de": 6, "filtros": 4, "final": 4, "nao_avaliaveis": 0, "sem_referencia": 0})
    assert base(tipo="regioes", regioes=["Nordeste"])[0] == []
    assert base(tipo="ufs", ufs=["15"])[0] == [BELEM]
    # Combinada: a região, a população e a densidade valem juntas.
    assert base(tipo="regioes", regioes=["Norte"], filtros=[filtro("populacao", ">", 900), filtro("densidade", "<", 15)])[0] == [
        MANACAPURU, PARINTINS]
    # Faixa: o mesmo indicador duas vezes (a partir de 8 e abaixo de 12).
    assert base(filtros=[filtro("densidade", ">=", 8), filtro("densidade", "<", 12)])[0] == [MANACAPURU, NOVO, TEFE]
    # Escolha direta: da seleção prévia, só os marcados; marcado que não passa pelos filtros não entra.
    assert base(tipo="selecao_previa", modo="marcados", municipios=[TEFE, MANAUS]) == (
        [MANAUS, TEFE], {"partir_de": 5, "filtros": 5, "final": 2, "nao_avaliaveis": 0, "sem_referencia": 0})
    assert base(tipo="selecao_previa", filtros=[filtro("densidade", ">", 10)], modo="marcados", municipios=[TEFE, MANAUS]) == (
        [MANAUS], {"partir_de": 5, "filtros": 2, "final": 1, "nao_avaliaveis": 0, "sem_referencia": 0})
    # Filtro não avaliável (NOVO AIRAO sem registro em 2019): fica de fora, contado, e nunca como "não atende".
    early = ok(page(info, competencia="201906", consulta=consulta(lado(filtros=[filtro("densidade", "<", 100)]), lado())))
    assert NOVO not in by_id(early) and early["referencia"]["contagens"]["base"]["nao_avaliaveis"] == 1
    # Sem seleção prévia, a base que parte do país continua (a seleção é só uma das opções).
    alone = ok(post(info, nivel="municipios", indicador="densidade", competencia="202406", consulta=consulta(lado(), ref)))
    assert [item["id"] for item in alone["itens"]] == TODOS
    empty = ok(post(info, nivel="municipios", indicador="densidade", competencia="202406", consulta=consulta(referencia=ref)))
    assert empty["itens"] == [] and empty["referencia"]["contagens"]["base"]["final"] == 0
    # Conjuntos continuam como itens, sem distância própria: cada membro tem a sua referência.
    sets = ok(page(info, consulta=consulta(referencia=ref), conjuntos=[{"id": "c1", "rotulo": "Capital e vizinho",
                                                                           "membros": [MANAUS, PARINTINS]}]))
    [group] = [item for item in sets["itens"] if item["tipo"] == "conjunto"]
    assert group["distancia_km"] is None and group["referencia_do_item"] is None
    assert any(text.startswith("Distância não se aplica ao conjunto") for text in group["motivos"])


def test_consulta_reference_follows_the_base_and_the_distance_filter_never_hides_a_municipality(repo):
    """A referência conforme a base (o mesmo estado ou a mesma região de cada município da base) restringe, para cada um, quais
    referências contam, sem reduzir a lista; quem fica sem referência no próprio recorte aparece com o motivo, nunca some em
    silêncio nem ganha distância zero (CAP-ESP-02). No filtro de distância, a decisão de 27/10/2026 segue a SPEC (CAP-SUB-01,
    AT-68): sem referência no recorte, a distância não é avaliável, e o município fica fora da base, listado com o motivo."""
    info = inspection()
    uf = lado("mesma_uf_da_base", filtros=[filtro("densidade", ">", 10)])
    body = ok(page(info, consulta=consulta(lado(), uf)))
    items = by_id(body)
    assert {key: reference_of(item) for key, item in items.items()} == {
        MANACAPURU: [], MANAUS: [PARINTINS], PARINTINS: [MANAUS], NOVO: [PARINTINS], TEFE: [PARINTINS], BELEM: []}
    missing = ("Sem referência no recorte: nenhum outro município da referência no mesmo estado (Pará) em junho de 2024 "
               "(DEPENDENCIA_NAO_AVALIAVEL, CONJUNTO_REFERENCIAS_VAZIO)")
    assert items[BELEM]["distancia_km"] is None and missing in items[BELEM]["motivos"]
    assert body["referencia"]["contagens"]["referencia"] == {"partir_de": 6, "filtros": 3, "final": 3, "nao_avaliaveis": 0}
    assert body["referencia"]["texto"] == "do mesmo estado de cada município da base com densidade > 10 por 1.000 habitantes"
    assert "(3 municípios em todo o país em junho de 2024)" in body["referencia"]["origem"]
    # A mesma região de cada município: todos são do Norte, como a referência do país inteiro.
    region = ok(page(info, consulta=consulta(lado(), lado("mesma_regiao_da_base", filtros=[filtro("densidade", ">", 10)]))))
    country = ok(page(info, consulta=consulta(lado(), lado(filtros=[filtro("densidade", ">", 10)]))))
    assert [(item["id"], item["distancia_km"], reference_of(item)) for item in region["itens"]] == [
        (item["id"], item["distancia_km"], reference_of(item)) for item in country["itens"]]
    # Com o filtro de distância: só quem atende entra; sem referência no recorte e sem coordenada, fora da base, com o motivo.
    assert km(NOVO, PARINTINS) < 100 < km(MANAUS, PARINTINS) < km(TEFE, PARINTINS)
    far = ok(page(info, consulta=consulta(lado(filtros=[filtro("distancia", ">", 100)]), uf)))
    assert [item["id"] for item in far["itens"]] == [MANAUS, PARINTINS, TEFE]
    assert all(item["distancia_km"] > 100 for item in far["itens"])
    assert far["referencia"]["contagens"]["base"] == {"partir_de": 6, "filtros": 3, "final": 3, "nao_avaliaveis": 2,
                                                      "sem_referencia": 2}
    assert far["referencia"]["sem_referencia"] == [
        {"id": MANACAPURU, "rotulo": "MANACAPURU (AM)", "uf": "AM",
         "motivo": "Distância não avaliável em junho de 2024: coordenadas ausentes (SEM_INFORMACAO_ESPACIAL)"},
        {"id": BELEM, "rotulo": "BELEM (PA)", "uf": "PA", "motivo": missing}]
    assert ("2 municípios ficaram fora da base porque o filtro de distância não é avaliável para eles (sem referência no recorte "
            "ou sem coordenada válida): MANACAPURU (AM) e BELEM (PA).") in far["notas"]
    assert far["referencia"]["base_texto"] == "de todo o país com distância à referência mais próxima > 100 km"
    near = ok(page(info, consulta=consulta(lado(filtros=[filtro("distancia", "<=", 100)]), uf)))
    assert [item["id"] for item in near["itens"]] == [NOVO]  # "até" também nunca inclui o não avaliável
    assert near["referencia"]["contagens"]["base"]["sem_referencia"] == 2
    # Sem o filtro de distância, todos entram, e o resultado mostra a distância de cada um (ou o motivo).
    assert [item["id"] for item in body["itens"]] == TODOS and body["referencia"]["sem_referencia"] == []
    # Referência vazia: nenhuma distância (nunca zero), com o motivo; com o filtro, a base fica vazia, e todos são listados.
    none = ok(page(info, consulta=consulta(lado(), lado("regioes", regioes=["Nordeste"]))))
    assert none["referencia"]["membros"] == [] and none["referencia"]["contagens"]["referencia"]["final"] == 0
    assert all(item["distancia_km"] is None and item["referencia_do_item"] is None for item in none["itens"])
    assert ("Sem referência no recorte: nenhum outro município da referência em junho de 2024 (DEPENDENCIA_NAO_AVALIAVEL, "
            "CONJUNTO_REFERENCIAS_VAZIO)") in by_id(none)[TEFE]["motivos"]
    nobody = ok(page(info, consulta=consulta(lado(filtros=[filtro("distancia", ">", 0)]), lado("regioes", regioes=["Nordeste"]))))
    assert nobody["itens"] == [] and [entry["id"] for entry in nobody["referencia"]["sem_referencia"]] == TODOS
    # Uma referência sem coordenada válida no recorte (MANACAPURU, densidade 8, entra em "≥ 8"): a distância fica não
    # avaliável, sem trocar pela mais próxima entre as demais (mínimo do conjunto completo, CAP-ESP-02).
    gap = by_id(ok(page(info, consulta=consulta(referencia=lado(filtros=[filtro("densidade", ">=", 8)])))))
    reason = ("Distância não avaliável em junho de 2024: sem coordenada válida na referência MANACAPURU (AM) "
              "(SEM_INFORMACAO_ESPACIAL); a mais próxima não é escolhida entre as demais (DEPENDENCIA_NAO_AVALIAVEL)")
    for key in (MANAUS, PARINTINS, NOVO, TEFE):
        assert gap[key]["distancia_km"] is None and reason in gap[key]["motivos"]
    # Referência pelos marcados (a conversa: "use Belém como referência"): a distância até eles, sem os marcados como itens.
    marked = by_id(ok(page(info, consulta=consulta(referencia=lado(modo="marcados", municipios=[BELEM])))))
    assert list(marked) == AM and all(reference_of(marked[key]) == [BELEM] for key in (MANAUS, PARINTINS, NOVO, TEFE))
    assert marked[MANAUS]["distancia_km"] == km(MANAUS, BELEM)


def test_consulta_is_validated_and_incomplete_parts_block_the_calculation(repo):
    info = inspection()
    ok_ref = lado(filtros=[filtro("densidade", ">", 10)])
    # O que falta completar desativa o cálculo, com os textos do comando.
    for spec, text in (
            (consulta(lado("regioes"), ok_ref), "Base incompleta: escolha ao menos uma região."),
            (consulta(lado(), lado("ufs")), "Referência incompleta: escolha ao menos um estado."),
            (consulta(lado(filtros=[filtro("populacao", ">", None)]), ok_ref), "Base incompleta: preencha o valor do filtro."),
            (consulta(lado(), lado(modo="marcados")), "Referência incompleta: marque ao menos um município."),
            (consulta(lado(filtros=[filtro("distancia", ">", 300)]), lado("regioes")),
             "Base incompleta: complete a referência para usar o filtro de distância.")):
        refused(page(info, consulta=spec), text)
    # Forma fora do contrato: recusada com o motivo.
    for spec, text in (
            (consulta(lado("mesma_uf_da_base"), ok_ref), "A base não tem as opções relativas"),
            (consulta(lado(), lado(filtros=[filtro("distancia", ">", 1)])), "A referência não tem o filtro de distância"),
            (consulta(lado(filtros=[filtro("distancia", "<", 1)]), ok_ref), "Operador do filtro de distância não reconhecido"),
            (consulta(lado(filtros=[filtro("densidade", "=", 1)]), ok_ref), "Operador do filtro não reconhecido"),
            (consulta(lado(filtros=[filtro("distancia_km", ">", 1)]), ok_ref), "Indicador do filtro não reconhecido"),
            (consulta(lado(filtros=[filtro("densidade", ">", -1)]), ok_ref),
             "O valor do filtro de densidade deve ser um número não negativo."),
            (consulta(lado(filtros=[filtro("densidade", ">", 1)] * 13), ok_ref), "envie até 12 filtros"),
            (consulta(lado("regioes", regioes=["Amazônia"]), ok_ref), "Regiões inexistentes na consulta: Amazônia."),
            (consulta(lado("ufs", ufs=["99"]), ok_ref), "Estados inexistentes na consulta: 99."),
            (consulta(lado("pais", regioes=["Norte"]), ok_ref), "Base da consulta: regioes vale só com o tipo regioes."),
            (consulta(lado(municipios=[MANAUS]), ok_ref), "a lista de marcados vale só no modo marcados"),
            (consulta(lado(modo="marcados", municipios=["code:999999"]), ok_ref), "inexistentes ou incompatíveis com a base"),
            ({**consulta(), "distancia": {"medida": "estrada", "ate": "referencia_mais_proxima"}},
             "Distância da consulta não suportada"),
            ({"base": lado()}, "Consulta inválida")):
        refused(page(info, consulta=spec), text)
    refused(page(info, consulta=consulta(), referencia={"membros": [MANAUS]}), "não envie referencia junto com consulta")
    # O território de referência por elegibilidade (e o "mais distante") saiu: o pedido antigo diz onde a referência foi parar.
    for relation in ("mais_proxima", "mais_distante"):
        refused(page(info, referencia={"relacao": relation, "delimitacao": {"tipo": "todos"},
                                       "condicao": {"atributo": "densidade", "operador": ">", "valor": 10}}),
                "O território de referência por elegibilidade foi substituído pela Escolha dos territórios")
    # Só na página única e só com municípios.
    refused(post(info, competencia="202406", base={"municipios": {"estados": ["13"]}}, consulta=consulta()),
            "Parâmetro não reconhecido no painel: consulta.")
    refused(post(info, nivel="estados", indicador="densidade", competencia="202406", consulta=consulta()),
            "a Escolha dos territórios mede a distância de cada município")
    refused(post(info, nivel="brasil", indicador="densidade", competencia="202406", consulta=consulta()),
            "o Brasil não tem um ponto único")


def test_territories_route_counts_each_step_for_the_window_without_starting_the_analysis(repo):
    """POST /api/painel/territorios (27/10/2026): o que a janela mostra enquanto a consulta é montada, tudo do motor."""
    info = inspection()
    ref = lado("ufs", ufs=["15"], filtros=[filtro("densidade", ">", 10)])
    base = lado("regioes", regioes=["Norte"], filtros=[filtro("densidade", "<", 15), filtro("distancia", ">", 100)])
    body = ok(territorios(info, consulta=consulta(base, ref)))
    assert body["selecao_previa"] == {"total": 5, "nomes": ["MANACAPURU (AM)", "MANAUS (AM)", "PARINTINS (AM)", "NOVO AIRAO (AM)",
                                                            "TEFE (AM)"]}
    assert body["base"] == {"contagens": {"partir_de": 6, "filtros": 3, "final": 3, "nao_avaliaveis": 1, "sem_referencia": 1},
                            "pendencias": [], "previa": {"total": 3, "nomes": ["PARINTINS (AM)", "NOVO AIRAO (AM)", "TEFE (AM)"]},
                            "marcados": []}
    assert body["referencia"] == {"contagens": {"partir_de": 1, "filtros": 1, "final": 1, "nao_avaliaveis": 0}, "pendencias": [],
                                  "previa": {"total": 1, "nomes": ["BELEM (PA)"]}, "marcados": []}
    assert "lista" not in body and "sessao" not in body
    # As contagens batem com o cálculo da análise.
    panel = ok(page(info, consulta=consulta(base, ref)))
    assert panel["referencia"]["contagens"] == {"base": body["base"]["contagens"], "referencia": body["referencia"]["contagens"]}
    assert len(panel["itens"]) == body["base"]["contagens"]["final"]
    # Incompleto: a etapa pendente fica sem contagem; o filtro sem valor não corta; o filtro de distância espera a referência.
    pending = ok(territorios(info, consulta=consulta(lado("regioes"), lado(modo="marcados"))))
    assert pending["base"]["contagens"] == {"partir_de": None, "filtros": None, "final": None, "nao_avaliaveis": None,
                                            "sem_referencia": 0}
    assert pending["base"]["pendencias"] == ["escolha ao menos uma região"] and pending["base"]["previa"] is None
    assert pending["referencia"]["pendencias"] == ["marque ao menos um município"]
    assert pending["referencia"]["contagens"]["final"] is None
    unvalued = ok(territorios(info, consulta=consulta(lado(filtros=[filtro("densidade", "<", None)]), ref)))
    assert unvalued["base"]["contagens"]["filtros"] == 6 and unvalued["base"]["pendencias"] == ["preencha o valor do filtro"]
    waiting = ok(territorios(info, consulta=consulta(lado(filtros=[filtro("densidade", "<", 15), filtro("distancia", ">", 100)]),
                                                     lado("ufs"))))
    assert waiting["base"]["pendencias"] == ["complete a referência para usar o filtro de distância"]
    assert waiting["base"]["contagens"]["filtros"] == 4  # a distância não corta enquanto a referência está incompleta
    # Os marcados, com quem passa pelas etapas 1 e 2.
    marked = ok(territorios(info, consulta=consulta(lado("selecao_previa", filtros=[filtro("densidade", ">", 10)], modo="marcados",
                                                         municipios=[TEFE, MANAUS]), ref)))
    assert [(entry["id"], entry["uf"], entry["passa"]) for entry in marked["base"]["marcados"]] == [
        (MANAUS, "AM", True), (TEFE, "AM", False)]
    assert marked["base"]["marcados"][0]["densidade"] == 25 and marked["base"]["contagens"]["final"] == 1
    # A lista para marcar: só quem passou pelas etapas 1 e 2, pela busca no nome (sem acento nem caixa), em ordem alfabética.
    listed = ok(territorios(info, consulta=consulta(lado(filtros=[filtro("densidade", "<", 15)]), ref),
                            lista={"lado": "base", "busca": "", "limite": 100}))["lista"]
    assert listed["total"] == 4 and [entry["rotulo"] for entry in listed["itens"]] == [
        "MANACAPURU (AM)", "NOVO AIRAO (AM)", "PARINTINS (AM)", "TEFE (AM)"]
    assert listed["itens"][3] == {"id": TEFE, "rotulo": "TEFE (AM)", "uf": "AM", "densidade": 10}
    found = ok(territorios(info, consulta=consulta(lado(filtros=[filtro("densidade", "<", 15)]), ref),
                           lista={"lado": "base", "busca": "Airão", "limite": 100}))["lista"]
    assert [entry["id"] for entry in found["itens"]] == [NOVO] and found["busca"] == "Airão"
    short = ok(territorios(info, consulta=consulta(lado(), ref), lista={"lado": "referencia", "busca": "", "limite": 1}))["lista"]
    assert (short["lado"], short["total"], [entry["id"] for entry in short["itens"]]) == ("referencia", 1, [BELEM])
    refused(territorios(info, consulta=consulta(), lista={"lado": "outro"}), "Lista inválida")
    refused(territorios(info, consulta=consulta(), lista={"lado": "base", "limite": 0}), "Limite da lista inválido")
    refused(territorios(info), "Envie a consulta da Escolha dos territórios.")
    refused(territorios(info, consulta={"base": lado()}), "Consulta inválida")


# --------------------------------------------------------------------------------------------- série temporal
def observed(points):
    return {point["competencia"]: point["valor"] for point in points if point["valor"] is not None}


def test_time_series_is_the_observed_value_in_each_period_without_classes(repo):
    """Série temporal (24/10/2026): o valor observado do indicador em cada competência do intervalo, pela mesma
    preparação da tendência (os mesmos valores das observações dela), sem classificar, sem linha ajustada e sem preencher
    lacunas (sem registro, null; o zero observado é valor)."""
    info = inspection()
    sets = [{"id": "c1", "rotulo": "Manaus e Novo Airão", "membros": [MANAUS, NOVO]},
            {"id": "c2", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]}]
    body = ok(page(info, serie={"competencias": list(reversed(PERIODS))}, conjuntos=sets))
    assert body["serie"] == {"janela": {"inicio": "201906", "fim": "202406", "competencias": PERIODS}, "competencias": 6,
                             "indicador": "densidade", "unidade_valor": "por 1.000 habitantes", "itens_com_valor": 7,
                             "itens": 7, "rotulo_itens": "municípios"}
    items = by_id(body)
    trend = by_id(ok(page(info, competencia_inicial="201906", tendencia={"competencias": PERIODS}, conjuntos=sets)))
    for key, item in items.items():
        assert [point["competencia"] for point in item["serie"]["observacoes"]] == PERIODS
        assert observed(item["serie"]["observacoes"]) == observed(trend[key]["tendencia"]["observacoes"])
        assert item.get("tendencia") is None  # sem classificação
    assert [point["valor"] for point in items[NOVO]["serie"]["observacoes"]][:3] == [None, None, None]
    assert items[TEFE]["serie"]["observacoes"][0]["valor"] == 0
    # Conjunto com membros diferentes no intervalo: os valores valem isoladamente, sem linha (RQ-REP-15).
    assert items["c1"]["serie"]["comparavel"] is False and items["c1"]["serie"]["motivo"].startswith("Série não comparável: ")
    assert items["c2"]["serie"] == {"observacoes": trend["c2"]["tendencia"]["observacoes"], "comparavel": True, "motivo": None}
    assert body["dominios"]["serie"] == [0, 25]
    assert any(note.startswith("Série temporal de junho de 2019 a junho de 2024 (6 competências)") for note in body["notas"])
    assert " Série temporal de junho de 2019 a junho de 2024: 6 competências." in body["resumo"]["texto"]
    # Os estados e o Brasil, pelas mesmas séries da tendência deles.
    states = ok(post(info, nivel="estados", indicador="densidade", competencia="202406", serie={"competencias": PERIODS}))
    state_trend = by_id(ok(post(info, nivel="estados", indicador="densidade", competencia="202406",
                                tendencia={"competencias": PERIODS})))
    assert states["serie"]["rotulo_itens"] == "estados" and states["serie"]["itens"] == 2
    for key, item in by_id(states).items():
        assert observed(item["serie"]["observacoes"]) == observed(state_trend[key]["tendencia"]["observacoes"])
    assert [point["valor"] for point in by_id(states)["uf:13"]["serie"]["observacoes"]][:3] == [None, None, None]
    brazil = ok(post(info, nivel="brasil", indicador="quantidade", competencia="202406", serie={"competencias": PERIODS}))
    [item] = brazil["itens"]
    assert brazil["serie"]["rotulo_itens"] == "Brasil" and brazil["serie"]["unidade_valor"] != "por 1.000 habitantes"
    assert [point["valor"] for point in item["serie"]["observacoes"]] == [1000] * 6
    # Validação do intervalo.
    refused(page(info, serie={"competencias": ["202406"]}), "Intervalo da série temporal inválido")
    refused(page(info, serie={"competencias": ["202406", "202406"]}), "Intervalo da série temporal inválido")
    refused(page(info, serie={"competencias": ["202406", "209912"]}), "Competência inexistente na série temporal: 209912.")
    refused(page(info, serie=PERIODS), "Série temporal inválida")


# --------------------------------------------------------------------------------------------- sessão e privacidade
def test_the_chart_result_is_recorded_without_replacing_the_conversation_context(repo, monkeypatch):
    forbidden = []

    async def provider(*args):
        forbidden.append(args)
        raise AssertionError("O gráfico não chama o provedor de IA.")

    monkeypatch.setattr(llm_bridge, "_call_gemini", provider)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    info = inspection()
    token = client.post("/api/session").json()["token"]
    headers = {"X-ADT-Session": token}
    try:
        body = ok(page(info, headers=headers, tendencia={"competencias": PERIODS}, grupos={"tipo": "quartis"}))
        assert body["sessao"]["registrado"] is True and body["sessao"]["motivo"] is None
        stored = client.get("/api/session/result/" + body["sessao"]["result_id"], headers=headers)
        assert stored.status_code == 200, stored.text
        record = stored.json()
        assert record["result"]["itens"] == body["itens"] and record["result"]["sessao"] == body["sessao"]
        assert record["result"]["metadata"]["operation"] == "painel"
        assert record["result"]["metadata"]["execution_key"] == body["chave_execucao"]
        assert record["context"]["origem"] == "painel" and record["context"]["painel"]["nivel"] == "municipios"
        assert sessions.sessions[token].context == {}  # o contexto da conversa não é substituído
        # A conversa lê o resultado do gráfico da mesma base sem calcular nem chamar o provedor.
        reply = client.post("/api/llm/interpret-context", headers=headers, data={
            "dataset": "brazil", "scope": "municipal", "dataset_version": info["source"]["version"],
            "mapping": json.dumps(info["suggested_mapping"]), "options": "{}", "context_revision": "0",
            "message": "O que esse resultado significa?", "displayed_result_id": body["sessao"]["result_id"]})
        assert reply.status_code == 200, reply.text
        answer = reply.json()
        assert answer["result_reference"]["result_id"] == body["sessao"]["result_id"]
        assert answer["result_status"] == "LEITURA_CONVERSACIONAL_NAO_IMPLEMENTADA"
        # Revisão antiga: o cálculo volta inteiro e o resultado não é gravado.
        client.post("/api/session/revision", headers=headers, json={"revision": 3})
        stale = ok(page(info, headers=headers, revision=1))
        assert stale["sessao"]["registrado"] is False and "contexto mudou" in stale["sessao"]["motivo"]
        assert stale["itens"] == ok(page(info))["itens"]
        # Só os resultados mais recentes do gráfico ficam na sessão; os mais antigos saem primeiro.
        first = body["sessao"]["result_id"]
        for _ in range(PANEL_KEEP):
            assert ok(page(info, headers=headers, revision=3))["sessao"]["registrado"] is True
        panels = [record for record in sessions.sessions[token].results.values() if record.get("painel")]
        assert len(panels) == PANEL_KEEP
        assert client.get("/api/session/result/" + first, headers=headers).status_code == 404
    finally:
        client.post("/api/session/close", headers=headers)
    assert forbidden == []


# --------------------------------------------------------------------------------------------- planilhas enviadas
YEARS = ["2021", "2022", "2023", "2024"]
# distrito: (província, latitude e longitude com ponto decimal, quantidades e populações por ano)
DISTRICTS = {
    "Alto Rio": ("Província Norte", "-3.1", "-60.0", [10, 12, 14, 16], [1000] * 4),
    "Baixo Rio": ("Província Norte", "-3.5", "-61.0", [5, 5, 5, 5], [500] * 4),
    "Campina": ("Província Sul", "-8.0", "-55.0", [30, 27, 25, 20], [2000] * 4),
    "Serra": ("Província Sul", "", "", [0, 2, 3, 4], [400] * 4),
}
DISTRICT_MAPPING = {"territory": "distrito", "period": "ano", "category": "categoria", "count": "quantidade",
                    "population": "populacao", "latitude": "latitude", "longitude": "longitude",
                    "grupo_territorial": "provincia"}
LABELS = {"unidade": {"singular": "distrito", "plural": "distritos"},
          "grupo": {"singular": "província", "plural": "províncias"}}
ALTO, BAIXO, CAMPINA, SERRA = ("name:" + name for name in DISTRICTS)


def districts_csv(districts=DISTRICTS, code=False):
    """Planilha de distritos e províncias (CSV com ponto e vírgula); com `code`, uma coluna codigo_identificador."""
    lines = ["distrito;provincia;" + ("codigo_identificador;" if code else "") +
             "ano;categoria;quantidade;populacao;latitude;longitude"]
    for i, year in enumerate(YEARS):
        for number, (name, (province, lat, lon, counts, populations)) in enumerate(districts.items(), start=1):
            lines.append(";".join([name, province, *(["D" + str(number)] if code else []), year, "Enfermeiros",
                                   str(counts[i]), str(populations[i]), lat, lon]))
    return ("\n".join(lines) + "\n").encode()


def upload(options, mapping=DISTRICT_MAPPING, contents=None, path="/api/painel", name="distritos.csv"):
    return client.post(path, files={"file": (name, contents or districts_csv())},
                       data={"mapping": json.dumps(mapping), "options": json.dumps(options)})


def districts(**options):
    """Pedido da página única sobre a planilha de distritos, com os rótulos e a unidade de contagem escolhidos."""
    return upload({"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "rotulos": LABELS,
                   "premissas": {"count_unit": "pessoas"}, "base": {"municipios": {"todos": True}}, **options})


def analyze_upload(operation, mapping=DISTRICT_MAPPING, contents=None, **options):
    fields = {key: value for key, value in mapping.items() if key != "grupo_territorial"}
    return client.post("/api/analyze", files={"file": ("distritos.csv", contents or districts_csv())},
                       data={"operation": operation, "mapping": json.dumps(fields), "options": json.dumps(
                           {"count_unit": "pessoas", "category_filter": "Enfermeiros", **options})})


def test_uploaded_districts_follow_the_received_labels_and_the_province_column(repo):
    body = ok(districts(base={"municipios": {"estados": ["Província Norte"]}}))
    assert set(body) == TOP and body["rotulos"] == {
        "unidade": {"singular": "distrito", "plural": "distritos", "genero": "m"},
        "grupo": {"singular": "província", "plural": "províncias", "genero": "f"}}
    items = by_id(body)
    assert list(items) == [ALTO, BAIXO]
    assert all(item["tipo"] == "municipio" and item["uf"] is None for item in items.values())
    assert {key: item["grupo_territorial"] for key, item in items.items()} == {ALTO: "Província Norte",
                                                                               BAIXO: "Província Norte"}
    assert body["contexto"] == {"brasil": None} and body["versao_base"] == hashlib.sha256(districts_csv()).hexdigest()
    assert any(note.startswith("Distritos base (2024): 2 de 2 com registro") for note in body["notas"])
    assert not any("município" in note or "Município" in note for note in body["notas"])
    available = body["disponibilidade"]
    assert available["estados"]["disponivel"] is False and available["grupos"]["disponivel"] is False
    assert "não há bolha de província" in available["grupos"]["motivo"]
    assert "somar os distritos seria uma agregação (CAP-AGR-01)" in available["grupos"]["motivo"]
    # Os valores são os da análise de densidade do mesmo arquivo.
    rows = {row["Território"]: row for row in ok(analyze_upload("density", period_filter="2024"))["rows"]}
    for name in ("Alto Rio", "Baixo Rio"):
        item = items["name:" + name]
        assert (item["populacao"], item["quantidade"], item["densidade"]) == (
            rows[name]["População"], rows[name]["Quantidade"], rows[name]["Densidade por 1.000"])
    # Mensagens com os rótulos recebidos; sem rótulos, "unidade" e "grupo".
    refused(districts(base={"municipios": {"estados": ["Província Leste"]}}), "Províncias inexistentes na planilha")
    refused(districts(base={"municipios": {"ids": ["name:Vila"]}}), "Distritos inexistentes")
    refused(districts(nivel="estados"), "O nível estados existe só na base do Brasil")
    refused(districts(base={}), "Escolha os distritos base ou um conjunto")
    plain = upload({"nivel": "municipios", "indicador": "densidade", "competencia": "2024",
                    "premissas": {"count_unit": "pessoas"}, "base": {}})
    refused(plain, "Escolha as unidades base ou um conjunto")
    no_group = upload({"nivel": "municipios", "indicador": "densidade", "competencia": "2024",
                       "premissas": {"count_unit": "pessoas"}, "base": {"municipios": {"estados": ["Província Sul"]}}},
                      mapping={key: value for key, value in DISTRICT_MAPPING.items() if key != "grupo_territorial"})
    refused(no_group, "não tem a coluna de grupo escolhida (papel grupo_territorial)")


def test_territorial_messages_follow_the_structure_of_the_spreadsheet(repo):
    """Textos territoriais pela estrutura reconhecida (23/10/2026): numa planilha de distritos e províncias, as mensagens,
    as notas, os motivos e a disponibilidade usam os nomes da planilha, com o gênero de cada um, e nenhum cita município,
    UF, IBGE ou a base do Brasil, salvo o motivo do nível estados, que existe só nela (com a fonte estadual)."""
    # O nível de cima não tem ponto único: na base do Brasil, os estados; nas planilhas, o grupo com o nome recebido.
    assert painel._sem_ponto_unico(painel._labels(LABELS, brazil=False)) == (
        "No nível das províncias, a distância não se aplica: as províncias não têm um ponto único. Abra os distritos de "
        "uma província para usar a análise espacial.")
    communes = {"unidade": {"singular": "comuna", "plural": "comunas"}, "grupo": {"singular": "região", "plural": "regiões"}}
    assert painel._sem_ponto_unico(painel._labels(communes, brazil=False)) == (
        "No nível das regiões, a distância não se aplica: as regiões não têm um ponto único. Abra as comunas de uma região "
        "para usar a análise espacial.")
    assert painel._sem_ponto_unico(painel.BRASIL) == (
        "No nível dos estados, a distância não se aplica: os estados não têm um ponto único. Abra os municípios de um "
        "estado para usar a análise espacial.")
    # A coluna do grupo igual à das unidades: o nome da planilha, com a concordância (antes, "A coluna do província").
    options = {"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "rotulos": LABELS,
               "premissas": {"count_unit": "pessoas"}, "base": {"municipios": {"todos": True}}}
    refused(upload(options, mapping={**DISTRICT_MAPPING, "grupo_territorial": "distrito"}),
            "A coluna da província (grupo_territorial) precisa ser diferente da coluna de distritos e do código.")
    # Uma resposta com distância, conjunto, mudança, tendência e grupos: todos os textos com os nomes da planilha.
    body = ok(districts(premissas={"count_unit": "pessoas", "crs": "SIRGAS2000"}, referencia={"membros": [ALTO]},
                        conjuntos=[{"id": "norte", "rotulo": "Norte", "membros": [ALTO, BAIXO]}],
                        competencia_inicial="2021", tendencia={"competencias": YEARS}, grupos={"tipo": "quartis"}))
    notes = body["notas"]
    assert "Distritos base (2024): 4 de 4 com registro." in notes
    assert "Distritos base na competência inicial (2021): 4 de 4 com registro." in notes
    assert any(note.startswith("Conjuntos (CAP-AGR-01)") and "quem atua em mais de um distrito é contado em cada um" in note
               and "cada população de distrito uma vez" in note for note in notes)
    assert any("Grupos por posição (CAP-DIS-02) entre os 4 distritos do universo" in note for note in notes)
    available = body["disponibilidade"]
    assert available["grupos"]["motivo"] == (
        "Sem um valor próprio de cada província na planilha, não há bolha de província: somar os distritos seria uma "
        "agregação (CAP-AGR-01), com possível dupla contagem. A província serve para navegar e escolher os distritos.")
    # O nível estados é o da base do Brasil, com a fonte estadual: o motivo o cita pelo nome, sem trocá-lo pela província.
    assert available["estados"]["motivo"] == ("O nível estados existe só na base do Brasil, com a fonte estadual de médicos "
                                              "únicos.")
    texts = notes + [text for item in body["itens"] for text in item["motivos"]] + [
        entry["motivo"] for key, entry in available.items() if key != "estados"]
    brazilian = re.compile(r"munic[íi]pi|\bIBGE\b|\bUF\b|\bBrasil\b|\bestad(?:o|os|ual|uais)\b", re.IGNORECASE)
    assert not [text for text in texts if brazilian.search(text)]


def test_uploaded_choices_return_structured_pendencies(repo):
    pending = upload({"nivel": "municipios", "indicador": "densidade", "competencia": "2024",
                      "base": {"municipios": {"todos": True}}})
    body = refused(pending, "Escolha a unidade de contagem")
    assert body["pendencia"] == {"chave": "count_unit", "opcoes": ["pessoas", "vinculos", "postos", "outro"],
                                 "texto": body["detail"]}
    # Coluna de código só sugerida (sem regra conclusiva): a pessoa precisa escolhê-la, como em /api/analyze (D1).
    coded = {"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "premissas": {"count_unit": "pessoas"},
             "base": {"municipios": {"todos": True}}}
    with_code = upload(coded, mapping={**DISTRICT_MAPPING, "territory_id": "codigo_identificador"},
                       contents=districts_csv(code=True))
    body = refused(with_code, "Escolha a coluna de Código identificador territorial")
    assert (body["pendencia"]["chave"], body["pendencia"]["opcoes"]) == ("confirmed_roles", ["territory_id"])
    coded["premissas"] = {"count_unit": "pessoas", "confirmed_roles": ["territory_id"]}
    chosen = ok(upload(coded, mapping={**DISTRICT_MAPPING, "territory_id": "codigo_identificador"},
                       contents=districts_csv(code=True)))
    assert [item["id"] for item in chosen["itens"]] == ["code:D1", "code:D2", "code:D3", "code:D4"]
    assert chosen["itens"][0]["rotulo"] == "Alto Rio [D1]"
    refused(districts(premissas={"count_unit": "pessoas", "crs": "SIRGAS2000", "extra": 1}), "Premissa não reconhecida")


def test_uploaded_distance_needs_a_confirmed_supported_reference(repo):
    reference = {"membros": [ALTO]}
    missing = refused(districts(referencia=reference), "Confirme o referencial geodésico")
    assert missing["pendencia"]["chave"] == "crs" and missing["pendencia"]["opcoes"] == ["SIRGAS2000", "WGS84"]
    assert ok(districts())["disponibilidade"]["espacial"]["pendencia"]["chave"] == "crs"
    # Referencial fora dos aceitos (SAD69): indisponível com o motivo, sem presumir nem transformar.
    other = ok(districts(premissas={"count_unit": "pessoas", "crs": "SAD69"}))["disponibilidade"]["espacial"]
    assert other["disponivel"] is False and other["pendencia"] is None
    assert "Referencial geodésico informado não suportado" in other["motivo"]
    refused(districts(premissas={"count_unit": "pessoas", "crs": "SAD69"}, referencia=reference),
            "Referencial geodésico informado não suportado")
    body = ok(districts(premissas={"count_unit": "pessoas", "crs": "SIRGAS 2000"}, referencia=reference))
    items = by_id(body)
    nearest = ok(analyze_upload("nearest", period_filter="2024", reference_mode="list", reference_ids=[ALTO],
                                crs="SIRGAS2000"))
    records = {record["unidade"]: record for record in nearest["metadata"]["nearest_reference"]["cobertura_referencias"]}
    for key in (BAIXO, CAMPINA):
        assert items[key]["distancia_km"] == records[key]["minimo_completo"]["distancia_km"]
    assert items[ALTO]["distancia_km"] == 0 and items[SERRA]["distancia_km"] is None
    assert any("(SEM_INFORMACAO_ESPACIAL)" in text for text in items[SERRA]["motivos"])
    assert body["disponibilidade"]["espacial"] == {"disponivel": True, "motivo": "", "pendencia": None}
    # WGS 84 (Adendo REF-20261022): mesma distância de /api/analyze no elipsoide WGS 84, sem converter coordenadas.
    wgs84 = by_id(ok(districts(premissas={"count_unit": "pessoas", "crs": "WGS 84"}, referencia=reference)))
    nearest_wgs84 = ok(analyze_upload("nearest", period_filter="2024", reference_mode="list", reference_ids=[ALTO],
                                      crs="WGS84"))
    records = {record["unidade"]: record
               for record in nearest_wgs84["metadata"]["nearest_reference"]["cobertura_referencias"]}
    for key in (BAIXO, CAMPINA):
        assert wgs84[key]["distancia_km"] == records[key]["minimo_completo"]["distancia_km"]
    # Coordenadas com vírgula e ponto misturados: o separador fica com a pessoa (sem presumir).
    mixed = {**DISTRICTS, "Baixo Rio": ("Província Norte", "-3,5", "-61,0", [5] * 4, [500] * 4)}
    contents = districts_csv(mixed)
    roles = {"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "referencia": reference,
             "base": {"municipios": {"todos": True}},
             "premissas": {"count_unit": "pessoas", "crs": "SIRGAS2000", "confirmed_roles": ["latitude", "longitude"]}}
    assert refused(upload(roles, contents=contents), "separador decimal")["pendencia"]["chave"] == "number_format"
    roles["premissas"]["number_format"] = "decimal_point"
    refused(upload(roles, contents=contents), "incompatíveis com o ponto decimal")


def test_uploaded_consulta_uses_the_spreadsheet_levels(repo):
    """Escolha dos territórios numa planilha (27/10/2026): partir da planilha inteira, das províncias da coluna-mãe ou da
    seleção prévia (as regiões existem só na base do Brasil), com os nomes da planilha. Densidades de 2024: Alto Rio 16, Baixo
    Rio, Campina e Serra 10; Serra não tem coordenada."""
    premises = {"count_unit": "pessoas", "crs": "SIRGAS2000"}
    same = lado("mesma_uf_da_base", filtros=[filtro("densidade", ">=", 10)])
    missing = refused(districts(consulta=consulta(lado(), same)), "Confirme o referencial geodésico")
    assert missing["pendencia"]["chave"] == "crs"
    # Na janela, o que impede medir a distância vira pendência do filtro de distância, e as contagens continuam.
    counting = ok(upload({"competencia": "2024", "rotulos": LABELS, "premissas": {"count_unit": "pessoas"},
                          "consulta": consulta(lado(filtros=[filtro("distancia", ">", 10)]), same)}, path="/api/painel/territorios"))
    assert counting["base"]["contagens"]["filtros"] == 4
    assert any(text.startswith("Confirme o referencial geodésico") for text in counting["base"]["pendencias"])
    body = ok(districts(premissas=premises, consulta=consulta(lado(), same)))
    items = by_id(body)
    assert body["referencia"]["texto"] == "da mesma província de cada distrito da base com densidade ≥ 10 por 1.000 habitantes"
    assert body["referencia"]["origem"] == (
        "Para cada distrito da base, o distrito mais próximo entre os distritos da mesma província de cada distrito da base com "
        "densidade ≥ 10 por 1.000 habitantes (4 distritos em toda a planilha em 2024); o próprio distrito não é a sua "
        "referência. Os filtros são escolha do usuário e não têm caráter normativo")
    # Província Norte: cada um vai até o outro. Província Sul: Serra é referência, mas sem coordenada, e Campina fica sem distância.
    assert reference_of(items[ALTO]) == [BAIXO] and reference_of(items[BAIXO]) == [ALTO]
    assert items[CAMPINA]["distancia_km"] is None and items[SERRA]["distancia_km"] is None
    assert any("na referência Serra (SEM_INFORMACAO_ESPACIAL)" in text for text in items[CAMPINA]["motivos"])
    brazilian = re.compile(r"munic[íi]pi|\bIBGE\b|\bUF\b|\bBrasil\b|\bpa[íi]s\b|\bestad(?:o|os|ual|uais)\b", re.IGNORECASE)
    texts = [body["referencia"]["origem"], body["referencia"]["texto"]] + [text for item in body["itens"] for text in item["motivos"]]
    assert not [text for text in texts if brazilian.search(text)]
    # A planilha inteira: só Alto Rio passa de 10; ele mesmo fica sem referência no recorte.
    whole = by_id(ok(districts(premissas=premises, consulta=consulta(lado(), lado(filtros=[filtro("densidade", ">", 10)])))))
    assert reference_of(whole[BAIXO]) == [ALTO] and reference_of(whole[CAMPINA]) == [ALTO]
    assert ("Sem referência no recorte: nenhum outro distrito da referência em 2024 (DEPENDENCIA_NAO_AVALIAVEL, "
            "CONJUNTO_REFERENCIAS_VAZIO)") in whole[ALTO]["motivos"]
    chosen = by_id(ok(districts(premissas=premises, consulta=consulta(lado(), lado("ufs", ufs=["Província Norte"],
                                                                                   filtros=[filtro("densidade", ">=", 10)])))))
    assert reference_of(chosen[CAMPINA]) == [ALTO]  # Baixo Rio (10) fica mais longe de Campina que Alto Rio
    north = ok(districts(premissas=premises, consulta=consulta(lado("ufs", ufs=["Província Norte"]), lado())))
    assert [item["id"] for item in north["itens"]] == [ALTO, BAIXO]
    assert north["referencia"]["base_texto"] == "da província escolhida (Província Norte)"
    refused(districts(premissas=premises, consulta=consulta(lado("regioes", regioes=["Norte"]), lado())),
            "As regiões (Norte, Nordeste, Sudeste, Sul e Centro-Oeste) existem só na base do Brasil.")
    refused(districts(premissas=premises, consulta=consulta(lado(), lado("mesma_regiao_da_base"))),
            "As regiões (Norte, Nordeste, Sudeste, Sul e Centro-Oeste) existem só na base do Brasil.")
    refused(districts(premissas=premises, consulta=consulta(lado("ufs", ufs=["Província Leste"]), lado())),
            "Províncias inexistentes na consulta: Província Leste.")
    pending = refused(districts(premissas=premises, consulta=consulta(lado("ufs"), lado())), "Base incompleta: escolha ao menos uma "
                                                                                             "província.")
    assert pending["detail"].startswith("Base incompleta")
    # Sem a coluna de província, partir de uma província (ou do mesmo grupo de cada base) não existe.
    options = {"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "rotulos": LABELS,
               "premissas": premises, "consulta": consulta(lado(), same)}
    plain = {key: value for key, value in DISTRICT_MAPPING.items() if key != "grupo_territorial"}
    refused(upload(options, mapping=plain), "A planilha não tem a coluna de província (papel grupo_territorial): parta da "
                                            "planilha inteira ou da seleção prévia.")


def test_uploaded_rotation_with_the_individual_identifier_is_cap_rot_01(repo):
    people = {"2023": {"Alto Rio": ["p1", "p2", "p3", "p4"], "Campina": ["p5", "p6"]},
              "2024": {"Alto Rio": ["p1", "p2", "p9"], "Campina": ["p5", "p6", "p7"], "Serra": ["p8"]}}
    lines = ["distrito;provincia;ano;categoria;id_pessoa;populacao"]
    for year, units in people.items():
        for name, ids in units.items():
            lines += [";".join([name, DISTRICTS[name][0], year, "Enfermeiros", person, "1000"]) for person in ids]
    contents = ("\n".join(lines) + "\n").encode()
    mapping = {"territory": "distrito", "period": "ano", "category": "categoria", "identity": "id_pessoa",
               "population": "populacao", "grupo_territorial": "provincia"}
    body = ok(upload({"nivel": "municipios", "indicador": "quantidade", "competencia": "2024", "rotulos": LABELS,
                      "base": {"municipios": {"todos": True}}, "rotatividade": {"inicial": "2023", "final": "2024"}},
                     mapping=mapping, contents=contents, name="pessoas.csv"))
    items = by_id(body)
    analysis = client.post("/api/analyze", files={"file": ("pessoas.csv", contents)}, data={
        "operation": "rotation", "mapping": json.dumps({k: v for k, v in mapping.items() if k != "grupo_territorial"}),
        "options": json.dumps({"initial_period": "2023", "final_period": "2024", "category_filter": "Enfermeiros"})})
    rows = {"name:" + row["Território"]: row for row in ok(analysis)["rows"]}
    for key, row in rows.items():
        rotation = items[key]["rotatividade"]
        assert (rotation["coorte_inicial"], rotation["permanencia"], rotation["saida"], rotation["permanencia_percentual"],
                rotation["saida_percentual"]) == (row["Coorte inicial"], row["Permanecem"], row["Saíram"],
                                                  row["Permanência (%)"], row["Rotatividade (%)"])
    assert items[ALTO]["rotatividade"]["saida_percentual"] == 50 and items[SERRA]["rotatividade"]["avaliavel"] is False
    assert body["rotatividade"] == {"inicial": "2023", "final": "2024", "universo": 3, "avaliaveis": 2, "nao_avaliaveis": 1}
    assert body["disponibilidade"]["rotatividade"]["disponivel"] is True
    assert "p1" not in json.dumps(body)  # identificadores individuais nunca são devolvidos
    # Sem identificador individual, a rotatividade fica indisponível, com o motivo.
    without = ok(districts())["disponibilidade"]["rotatividade"]
    assert without["disponivel"] is False and "identificador individual" in without["motivo"]
    refused(districts(rotatividade={"inicial": "2023", "final": "2024"}), "identificador individual")


def test_uploaded_trend_conditions_and_reference_candidates(repo):
    body = ok(districts(tendencia={"competencias": YEARS}, condicoes=[{"atributo": "densidade", "operador": ">=", "valor": 10}],
                        ordenar={"atributo": "densidade", "ordem": "desc", "primeiros": 1}))
    items = by_id(body)
    analysis = ok(analyze_upload("temporal", temporal_indicator="density", period_filters=YEARS))
    labels = {"name:" + row["Território"]: row["Tendência"] for row in analysis["rows"]}
    assert {key: item["tendencia"]["rotulo"] for key, item in items.items()} == labels
    assert items[ALTO]["tendencia"]["classe"] == "CRESCIMENTO" and items[CAMPINA]["tendencia"]["familia"] == "DECLINIO"
    assert {key: item["condicoes"]["situacao"] for key, item in items.items()} == {
        ALTO: "ATENDE", BAIXO: "ATENDE", CAMPINA: "ATENDE", SERRA: "ATENDE"}
    assert [key for key, item in items.items() if item["ordem"]["selecionado"]] == [ALTO]
    candidates = ok(upload({"competencia": "2024", "premissas": {"count_unit": "pessoas"}, "rotulos": LABELS,
                            "universo": {"municipios": {"estados": ["Província Sul"]}},
                            "criterio": {"atributo": "densidade", "ordem": "desc"}}, path="/api/painel/referencias"))
    # Empate na densidade (10 por 1.000): mesma posição; dentro do empate, ordem alfabética só para exibir.
    assert [(item["id"], item["posicao"]) for item in candidates["candidatos"]] == [(CAMPINA, 1), (SERRA, 1)]
    assert all(item["uf"] is None for item in candidates["candidatos"])


def test_upload_without_population_offers_the_quantity_only(repo):
    mapping = {key: value for key, value in DISTRICT_MAPPING.items() if key != "population"}
    options = {"nivel": "municipios", "competencia": "2024", "premissas": {"count_unit": "pessoas"},
               "base": {"municipios": {"todos": True}}}
    refused(upload({**options, "indicador": "densidade"}, mapping=mapping), "não tem coluna de população")
    body = ok(upload({**options, "indicador": "quantidade", "grupos": {"tipo": "quartis"}}, mapping=mapping))
    assert body["disponibilidade"]["densidade"]["disponivel"] is False
    assert all(item["densidade"] is None and item["populacao"] is None for item in body["itens"])
    assert [by_id(body)[key]["quantidade"] for key in (ALTO, BAIXO, CAMPINA, SERRA)] == [16, 5, 20, 4]
    refused(upload({**options, "indicador": "quantidade", "condicoes": [
        {"atributo": "densidade", "operador": ">", "valor": 1}]}, mapping=mapping), "não tem coluna de população")
    # Sem `nivel`, a planilha continua recusada, como no contrato de 21/10.
    refused(upload({"competencia": "2024"}), "base Brasil oficial")


def test_uploads_never_reach_the_ai_provider(repo, monkeypatch):
    calls = []

    async def forbidden(*args):
        calls.append(args)
        raise AssertionError("O gráfico não chama o provedor de IA.")

    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    before = client.get("/api/llm/status").json()["requests_used_today"]
    ok(districts(premissas={"count_unit": "pessoas", "crs": "SIRGAS2000"}, referencia={"membros": [ALTO]},
                 tendencia={"competencias": YEARS}, grupos={"tipo": "quartis"}, comparar=[ALTO, CAMPINA]))
    info = inspection()
    ok(post(info, nivel="estados", indicador="densidade", competencia="202406", tendencia={"competencias": PERIODS}))
    assert calls == [] and client.get("/api/llm/status").json()["requests_used_today"] == before


# --------------------------------------------------------------------------------------------- base versionada
AM3 = ["code:130260", "code:130420", "code:130340"]
JUNE = [str(year) + "06" for year in range(2014, 2025)]


@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    folder = os.getenv("ADT_REAL_DATA_DIR")
    if not folder:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    paths = [p for p in Path(folder).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    catalog = tmp_path_factory.mktemp("painel-pagina-real") / "brasil"
    install(Path(folder), catalog)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(catalog))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        main._BRAZIL_FRAMES.clear()
        yield inspection()
        main._BRAZIL_FRAMES.clear()
    assert before == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def test_real_states_match_the_state_level_of_the_density_analysis(real):
    body = ok(post(real, nivel="estados", indicador="densidade", competencia="202406"))
    items = by_id(body)
    assert len(items) == 27 and list(items) == sorted(items)
    analysis = ok(analyze(real, "density", {"estados": [key[3:] for key in items]}, period_filter="202406"))
    rows = {row["Território"]: row for row in analysis["rows"] if row["Nível"] == "Estado"}
    for item in items.values():
        row = rows[item["rotulo"]]
        assert (item["quantidade"], item["populacao"], item["densidade"]) == (
            row["Quantidade"], row["População"], row["Densidade por 1.000"])
    line = body["contexto"]["brasil"]
    assert line["densidade"] is not None and line["competencia"] == "202406"
    # Os estados escolhidos (24/10/2026): os mesmos valores do pedido com todos.
    chosen = ok(post(real, nivel="estados", indicador="densidade", competencia="202406", estados=["29", "42"]))
    assert [item["id"] for item in chosen["itens"]] == ["uf:29", "uf:42"]
    assert all(item == items[item["id"]] for item in chosen["itens"])


def test_real_brazil_level_is_the_national_reference_and_the_national_trend(real):
    """O Brasil como unidade agregada, com a base versionada: os valores da linha de contexto (BR-POP-JUNHO-1) e a classe
    da evolução temporal do Brasil nos últimos 4 junhos e nos últimos 4 semestres."""
    line = ok(post(real, nivel="estados", indicador="densidade", competencia="202406"))["contexto"]["brasil"]
    for window in (["202106", "202206", "202306", "202406"], ["202301", "202306", "202401", "202406"]):
        body = ok(post(real, nivel="brasil", indicador="densidade", competencia="202406", competencia_inicial=window[0],
                       tendencia={"competencias": window}))
        [item] = body["itens"]
        assert (item["quantidade"], item["populacao"], item["densidade"]) == (line["quantidade"], line["populacao"],
                                                                              line["densidade"])
        analysis = ok(analyze(real, "temporal", {"brasil": True}, temporal_indicator="density", period_filters=window))
        [row] = [row for row in analysis["rows"] if row["Território"].startswith("Brasil")]
        assert item["tendencia"]["rotulo"] == row["Tendência"]
        assert body["resumo"]["texto"].startswith("Brasil, em junho de 2024: densidade de ")


def test_real_trend_groups_and_conditions_for_amazonas(real):
    body = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406",
                   base={"municipios": {"estados": ["13"]}}, referencia={"membros": [AM3[0]]},
                   tendencia={"competencias": JUNE}, grupos={"tipo": "quintis"},
                   condicoes=[{"atributo": "densidade", "operador": "<", "valor": 1},
                              {"atributo": "distancia_km", "operador": ">", "valor": 150}]))
    items = by_id(body)
    units = [item["id"] for item in body["itens"]]
    assert len(units) == 62
    analysis = ok(analyze(real, "temporal", {"municipios": {"estados": ["13"]}}, temporal_indicator="density",
                          period_filters=JUNE))
    labels = {code_of(row["Território"]): row["Tendência"] for row in analysis["rows"]}
    assert {key: items[key]["tendencia"]["rotulo"] for key in labels} == labels
    assert body["tendencia"]["contagens"] == analysis["metadata"]["tendencia"]["contagens"]
    distribution = ok(analyze(real, "distribution", {"municipios": {"estados": ["13"]}}, distribution_indicator="density",
                              quantile_count=5, period_filter="202406"))
    expected = {code_of(row["Território"]): row["Quintil"] for row in distribution["detail_rows"]}
    assert {key: items[key]["grupo"]["rotulo"] for key in expected} == expected
    assert body["grupos"]["classificados"] == len(expected)
    structured = ok(analyze(real, "criteria", {"municipios": {"estados": ["13"]}}, period_filter="202406",
                            category_filter="MEDICINA", crs="SIRGAS2000", number_format="decimal_comma",
                            reference_mode="list", reference_ids=[AM3[0]],
                            criteria={"logic": "and", "operands": [
                                {"attribute": "densidade", "operator": "<", "value": 1},
                                {"attribute": "distancia", "operator": ">", "value": 150}]}))["metadata"]["criterios"]
    assert {key: items[key]["condicoes"]["situacao"] for key in units} == {
        item["elemento"]: item["estado"] for item in structured["avaliacoes"]}


def test_real_all_municipalities_with_trend_and_conditions(real):
    body = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406",
                   base={"municipios": {"todos": True}}, referencia={"membros": [AM3[0]]},
                   tendencia={"competencias": JUNE},
                   condicoes=[{"atributo": "densidade", "operador": "<", "valor": 1},
                              {"atributo": "distancia_km", "operador": ">", "valor": 150}]))
    units = [item for item in body["itens"] if item["tipo"] == "municipio"]
    assert len(units) == body["tendencia"]["universo"] == body["condicoes"]["universo"]
    assert sum(body["tendencia"]["contagens"].values()) + body["tendencia"]["nao_avaliaveis"] == len(units)
    assert sum(body["condicoes"]["contagens"].values()) == len(units)
    assert all(len(item["tendencia"]["observacoes"]) <= len(JUNE) for item in units)
    json.dumps(body, allow_nan=False)


def test_real_consulta_matches_every_geodesic_and_the_series_matches_the_trend(real):
    """Base versionada (27/10/2026): a base dos 62 municípios do Amazonas (seleção prévia) com a referência no mesmo estado de
    cada município, acima de 50 mil habitantes, conferida com todas as distâncias de cada referência (a referência mais próxima
    da análise existente, uma referência por vez): a mais próxima, sem o próprio município, com os empates. E a série temporal
    dos junhos, com os mesmos valores das observações da tendência."""
    am = {"municipios": {"estados": ["13"]}}
    base = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406", base=am))
    eligibles = [item["id"] for item in base["itens"] if item["populacao"] is not None and item["populacao"] > 50000]
    assert 2 <= len(eligibles) < 62
    distance = {}
    for key in eligibles:
        nearest = ok(analyze(real, "nearest", am, period_filter="202406", reference_mode="list", reference_ids=[key],
                             crs="SIRGAS2000", number_format="decimal_comma", category_filter="MEDICINA"))
        for record in nearest["metadata"]["nearest_reference"]["cobertura_referencias"]:
            found = record["minimo_completo"]
            distance[record["unidade"], key] = found["distancia_km"] if found["avaliabilidade"] == "AVALIAVEL" else None
    body = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406", base=am, consulta=consulta(
        referencia=lado("mesma_uf_da_base", filtros=[filtro("populacao", ">", 50000)]))))
    assert body["referencia"]["contagens"]["referencia"]["partir_de"] == 5570
    units = [item for item in body["itens"] if item["tipo"] == "municipio"]
    assert len(units) == 62
    for item in units:
        others = {key: distance[item["id"], key] for key in eligibles if key != item["id"]}
        if None in others.values() or not others:
            assert item["distancia_km"] is None and item["referencia_do_item"] is None
            continue
        best = min(others.values())
        assert item["distancia_km"] == best
        assert sorted(reference_of(item)) == sorted(key for key, value in others.items() if value == best)
    json.dumps(body, allow_nan=False)
    series = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406", base=am,
                     serie={"competencias": JUNE}))
    trend = by_id(ok(post(real, nivel="municipios", indicador="densidade", competencia="202406", base=am,
                          tendencia={"competencias": JUNE})))
    assert series["serie"]["competencias"] == len(JUNE) and series["serie"]["itens"] == 62
    for item in series["itens"]:
        assert observed(item["serie"]["observacoes"]) == observed(trend[item["id"]]["tendencia"]["observacoes"])


def test_real_consulta_of_the_command_north_far_from_acre(real):
    """O exemplo do comando (27/10/2026) na base versionada: municípios do Norte com densidade abaixo de 0,5, a mais de 300 km
    de um município do Acre com densidade acima de 2. As contagens das etapas batem entre a janela e o cálculo, e cada número
    vem do motor: a densidade, a distância e a referência de cada item."""
    spec = consulta(lado("regioes", regioes=["Norte"], filtros=[filtro("densidade", "<", 0.5), filtro("distancia", ">", 300)]),
                    lado("ufs", ufs=["12"], filtros=[filtro("densidade", ">", 2)]))
    counts = ok(post(real, path="/api/painel/territorios", competencia="202406", consulta=spec))
    body = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406", consulta=spec))
    assert body["referencia"]["contagens"] == {"base": counts["base"]["contagens"], "referencia": counts["referencia"]["contagens"]}
    assert counts["base"]["contagens"]["partir_de"] == 450 and counts["referencia"]["contagens"]["partir_de"] == 22
    assert 0 < len(body["itens"]) == counts["base"]["contagens"]["final"] < counts["base"]["contagens"]["partir_de"]
    acre = {member["id"] for member in body["referencia"]["membros"]}
    assert acre and all(member["rotulo"].endswith("(AC)") and member["densidade"] > 2 for member in body["referencia"]["membros"])
    for item in body["itens"]:
        assert item["id"][5] == "1" and item["densidade"] < 0.5 and item["distancia_km"] > 300
        assert set(reference_of(item)) <= acre
    # Sem o filtro de distância, entram todos os do Norte abaixo de 0,5, e o resultado mostra a distância de cada um.
    open_spec = consulta(lado("regioes", regioes=["Norte"], filtros=[filtro("densidade", "<", 0.5)]), spec["referencia"])
    wider = ok(post(real, nivel="municipios", indicador="densidade", competencia="202406", consulta=open_spec))
    near = [item for item in wider["itens"] if item["distancia_km"] is not None and item["distancia_km"] <= 300]
    unknown = [item for item in wider["itens"] if item["distancia_km"] is None]
    assert len(wider["itens"]) == counts["base"]["contagens"]["final"] + len(near) + len(unknown)
    assert len(unknown) <= counts["base"]["contagens"]["sem_referencia"]
    # Todo o país, sem filtro, todos: entram todos os municípios.
    country = ok(post(real, path="/api/painel/territorios", competencia="202406", consulta=consulta(lado(), lado())))
    assert country["base"]["contagens"] == {"partir_de": 5570, "filtros": 5570, "final": 5570, "nao_avaliaveis": 0,
                                            "sem_referencia": 0}
