"""Grupos do mapa da página única: `grupos_mapa` em POST /api/painel (Docs/PAINEL_INTEGRADO.md, "Grupos do mapa").

O mapa pinta, por padrão, os 5 grupos iguais (quintis) de CAP-DIS-02. Para a troca de vista entre o gráfico e o mapa não
pedir cálculo (RQ-REP-06), a tela pede os grupos do mapa junto com a análise, numa chave própria. O cálculo é o de
`grupos` (a mesma função e a mesma memória da versão), sem método novo; com ele, só se somam `grupos_mapa` no topo e
`grupo_mapa` nos itens, e a chave de execução muda: a frase-resumo, as notas e o resto da resposta continuam os mesmos.

Catálogo sintético e planilha de distritos de test_painel_pagina.py: no Amazonas, em junho de 2024, a densidade é 8 em
MANACAPURU e em NOVO AIRAO, 10 em TEFE, 12 em PARINTINS e 25 em MANAUS (por 1.000). O caso com a base versionada roda no
job dados-reais (ADT_REAL_DATA_DIR), somente em leitura.
"""
import numpy as np

import main
import painel
from test_painel_pagina import (BELEM, MANACAPURU, MANAUS, NOVO, PARINTINS, PERIODS, TEFE, by_id, districts, inspection,
                                ok, page, post, refused)
from test_painel_pagina import real, repo  # noqa: F401 (fixtures)

QUINTIS = {"tipo": "quintis"}
INVALID = 'Grupos por posição inválidos (grupos_mapa): use {"tipo": "quartis", "quintis" ou "decis"}.'


def without_map(body):
    """A resposta sem o que os grupos do mapa acrescentam: `grupos_mapa`, `grupo_mapa` e a chave de execução."""
    out = {key: value for key, value in body.items() if key not in ("grupos_mapa", "chave_execucao")}
    out["itens"] = [{key: value for key, value in item.items() if key != "grupo_mapa"} for item in body["itens"]]
    return out


# --------------------------------------------------------------------------------------------- mesmo cálculo de grupos
def test_map_groups_are_the_groups_by_position_of_the_same_request(repo):
    info = inspection()
    for tipo in ("quartis", "quintis", "decis"):
        body = ok(page(info, grupos={"tipo": tipo}, grupos_mapa={"tipo": tipo}))
        # Rótulos, cortes, contagens, universo e o grupo de cada item: os mesmos de `grupos`.
        assert body["grupos_mapa"] == body["grupos"] and body["grupos_mapa"]["tipo"] == tipo
        assert [item["grupo_mapa"] for item in body["itens"]] == [item["grupo"] for item in body["itens"]]
    # Quintis (Hyndman–Fan tipo 7) sobre 8, 25, 12, 8 e 10: valores iguais no mesmo grupo, grupos vazios mantidos.
    body = ok(page(info, grupos_mapa=QUINTIS))
    groups = body["grupos_mapa"]
    values = [8, 25, 12, 8, 10]
    assert groups["cortes"] == [float(np.quantile(values, j / 5, method="linear")) for j in range(1, 5)]
    assert groups["rotulos"] == ["1º quintil", "2º quintil", "3º quintil", "4º quintil", "5º quintil"]
    assert groups["contagens"] == [2, 0, 1, 1, 1]
    assert (groups["k"], groups["atributo"], groups["universo"], groups["classificados"], groups["nao_avaliaveis"]) == (
        5, "densidade", 5, 5, 0)
    items = by_id(body)
    assert {key: items[key]["grupo_mapa"]["indice"] for key in items} == {MANACAPURU: 1, NOVO: 1, TEFE: 3, PARINTINS: 4,
                                                                         MANAUS: 5}
    assert items[TEFE]["grupo_mapa"] == {"indice": 3, "rotulo": "3º quintil"}


def test_map_groups_in_the_distribution_the_spatial_analysis_the_change_and_the_quantity(repo):
    info = inspection()
    reference = {"membros": [PARINTINS, BELEM]}
    for options in ({}, {"referencia": reference}, {"competencia_inicial": "202006"}, {"indicador": "quantidade"},
                    {"tendencia": {"competencias": PERIODS}}):
        alone = ok(page(info, grupos_mapa=QUINTIS, **options))
        groups = ok(page(info, grupos=QUINTIS, **options))
        assert alone["grupos_mapa"] == groups["grupos"]
        assert [item["grupo_mapa"] for item in alone["itens"]] == [item["grupo"] for item in groups["itens"]]
    # Na análise espacial, a referência de outro estado é item, mas não é do universo: sem grupo do mapa.
    spatial = by_id(ok(page(info, grupos_mapa=QUINTIS, referencia=reference)))
    assert spatial[BELEM]["grupo_mapa"] is None
    assert spatial[PARINTINS]["grupo_mapa"] == {"indice": 4, "rotulo": "4º quintil"}
    # Conjuntos ficam fora do universo, como em `grupos`.
    sets = by_id(ok(page(info, grupos_mapa=QUINTIS, conjuntos=[{"id": "c1", "rotulo": "Manaus e Tefé",
                                                                "membros": [MANAUS, TEFE]}])))
    assert sets["c1"]["grupo_mapa"] is None


def test_map_groups_in_the_states_level_and_in_the_uploaded_spreadsheet(repo):
    info = inspection()
    states = ok(post(info, nivel="estados", indicador="densidade", competencia="202406", grupos={"tipo": "quartis"},
                     grupos_mapa={"tipo": "quartis"}))
    assert states["grupos_mapa"] == states["grupos"] and states["grupos_mapa"]["classificados"] == 2
    assert [item["grupo_mapa"] for item in states["itens"]] == [item["grupo"] for item in states["itens"]]
    upload = ok(districts(grupos={"tipo": "quartis"}, grupos_mapa={"tipo": "quartis"}))
    assert upload["grupos_mapa"] == upload["grupos"] and upload["grupos_mapa"]["universo"] == 4
    assert [item["grupo_mapa"] for item in upload["itens"]] == [item["grupo"] for item in upload["itens"]]


def test_with_the_same_inputs_the_map_groups_read_the_memory_of_the_groups(repo, monkeypatch):
    info = inspection()
    calls = []
    original = main._compute

    def counting(df, mapping, operation, options, prepared=None):
        if operation == "distribution":
            calls.append(options["quantile_count"])
        return original(df, mapping, operation, options, prepared=prepared)

    monkeypatch.setattr(main, "_compute", counting)
    body = ok(page(info, grupos=QUINTIS, grupos_mapa=QUINTIS))
    assert calls == [5] and body["grupos_mapa"] == body["grupos"]  # um cálculo: o do mapa vem da memória da versão
    ok(page(info, grupos=QUINTIS, grupos_mapa={"tipo": "quartis"}))
    assert calls == [5, 4]  # quintis já guardados; os quartis do mapa, calculados à parte


# --------------------------------------------------------------------------------------------- o resto não muda
def test_the_summary_the_notes_and_the_rest_of_the_answer_do_not_change_with_the_map_groups(repo):
    info = inspection()
    for options in ({}, {"grupos": {"tipo": "quartis"}}, {"referencia": {"membros": [MANAUS]}, "faixas": [0, 10, 20]},
                    {"tendencia": {"competencias": PERIODS}, "competencia_inicial": "202006",
                     "comparar": [MANAUS, TEFE]}):
        plain = ok(page(info, **options))
        with_map = ok(page(info, grupos_mapa=QUINTIS, **options))
        # Sem a opção, nada dela na resposta; com ela, só os grupos do mapa a mais.
        assert "grupos_mapa" not in plain and not any("grupo_mapa" in item for item in plain["itens"])
        assert without_map(with_map) == without_map(plain)
        assert with_map["resumo"] == plain["resumo"]  # a frase-resumo não descreve os grupos do mapa
        assert painel.summary_facts(with_map) == painel.summary_facts(plain)
        assert (with_map["notas"], with_map["limitacoes"]) == (plain["notas"], plain["limitacoes"])
        # A chave de execução muda com a opção e com o tipo, e se repete com o mesmo pedido.
        assert with_map["chave_execucao"] != plain["chave_execucao"]
        assert ok(page(info, grupos_mapa=QUINTIS, **options))["chave_execucao"] == with_map["chave_execucao"]
        assert ok(page(info, grupos_mapa={"tipo": "quartis"}, **options))["chave_execucao"] != with_map["chave_execucao"]


def test_without_two_units_with_value_the_map_groups_are_null_and_the_request_is_not_refused(repo):
    info = inspection()
    single = ok(page(info, base={"municipios": {"ids": [MANAUS]}}, grupos_mapa=QUINTIS))
    assert single["grupos_mapa"] is None and [item["grupo_mapa"] for item in single["itens"]] == [None]
    assert without_map(single) == without_map(ok(page(info, base={"municipios": {"ids": [MANAUS]}})))
    # Dois municípios, um sem registro em 2020 (NOVO AIRAO): um só com valor.
    early = ok(page(info, competencia="202006", base={"municipios": {"ids": [MANAUS, NOVO]}}, grupos_mapa=QUINTIS))
    assert early["grupos_mapa"] is None and all(item["grupo_mapa"] is None for item in early["itens"])
    # Estados em 2020: o Amazonas sem população completa, só o Pará com densidade.
    states = ok(post(info, nivel="estados", indicador="densidade", competencia="202006", grupos_mapa={"tipo": "quartis"}))
    assert states["grupos_mapa"] is None
    # `grupos`, pedido pela pessoa, continua recusado com o motivo.
    refused(page(info, base={"municipios": {"ids": [MANAUS]}}, grupos=QUINTIS), "pelo menos dois municípios")
    refused(post(info, nivel="estados", indicador="densidade", competencia="202006", grupos={"tipo": "quartis"}),
            "pelo menos dois estados com densidade em junho de 2020")


def test_an_invalid_type_of_map_groups_is_refused_with_the_message(repo):
    info = inspection()
    for invalid in ({"tipo": "tercis"}, {"tipo": "quintis", "extra": 1}, {}, "quintis", ["quintis"]):
        refused(page(info, grupos_mapa=invalid), INVALID)
    # `grupos` mantém a mensagem de sempre; sem `nivel` (contrato de 21/10), a chave é da página única.
    refused(page(info, grupos={"tipo": "tercis"}), 'Grupos por posição inválidos: use {"tipo": "quartis", "quintis" ou')
    legacy = refused(post(info, competencia="202406", base={"municipios": {"ids": [MANAUS]}}, grupos_mapa=QUINTIS),
                     "Parâmetro não reconhecido no painel: grupos_mapa.")
    assert "nivel" in legacy["detail"]


# --------------------------------------------------------------------------------------------- base versionada
def test_real_map_quintiles_of_amazonas_are_the_quintile_groups(real):
    amazonas = {"nivel": "municipios", "indicador": "densidade", "competencia": "202406",
                "base": {"municipios": {"estados": ["13"]}}}
    both = ok(post(real, **amazonas, grupos=QUINTIS, grupos_mapa=QUINTIS))
    assert both["grupos_mapa"] == both["grupos"]
    assert both["grupos_mapa"]["classificados"] == sum(both["grupos_mapa"]["contagens"]) == 62
    assert [item["grupo_mapa"] for item in both["itens"]] == [item["grupo"] for item in both["itens"]]
    alone = ok(post(real, **amazonas, grupos_mapa=QUINTIS))
    assert alone["grupos_mapa"] == both["grupos"]
    assert [item["grupo_mapa"] for item in alone["itens"]] == [item["grupo"] for item in both["itens"]]
    plain = ok(post(real, **amazonas))
    assert without_map(alone) == without_map(plain) and alone["resumo"] == plain["resumo"]
