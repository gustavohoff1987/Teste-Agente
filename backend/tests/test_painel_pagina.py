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
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import llm_bridge
import main
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
    assert states["espacial"]["disponivel"] is False and "estados não têm um ponto único" in states["espacial"]["motivo"]
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
