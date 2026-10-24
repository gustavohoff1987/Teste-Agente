"""Frase-resumo da página única (resumo_painel.py; Docs/PAINEL_INTEGRADO.md, seção "Frase-resumo").

As mesmas regras da frase-resumo de /api/analyze (test_result_summary.py, decisão D7): só cópias verificadas de valores da
própria resposta (cada segmento é conferido contra o caminho), texto fixo sem LEX-DES, LEX-NORM e LEX-CAU, LEX-CMP só nas
relações do motor, LEX-TEN só com a tendência, a taxa do Brasil só como contexto (nunca "acima" ou "abaixo") e números pela
regra de apresentação (RQ-REP-05). Uma falha ao compor nunca derruba a resposta, e nada da frase vai ao provedor de IA.

Catálogo sintético e planilhas de test_painel_pagina.py: no Amazonas, em junho de 2024, MANACAPURU e NOVO AIRAO têm
8 por 1.000 (a menor densidade), MANAUS 25 (a maior); MANACAPURU não tem coordenadas.
"""
import json
import logging
import re
import unicodedata

import llm_bridge
import painel
import resumo_painel
from nearest_reference import TPL_11
from result_conversation import resolve
from territorial_levels import NOTE_STATES
from trend import TEXT_MINIMUM
from test_painel_pagina import (AM, BELEM, DISTRICT_MAPPING, LABELS, MANACAPURU, MANAUS, NOVO, PARINTINS, PERIODS, TEFE,
                                YEARS, by_id, districts, inspection, ok, page, post, upload)
from test_painel_pagina import repo  # noqa: F401 (fixture)

LEX_NORM = ["adequado", "inadequado", "suficiente", "insuficiente", "deficitario", "deficit", "prioritario", "critico",
            "problematico", "ideal", "excesso", "carencia"]
LEX_CAU = ["causa", "explica", "devido a", "em razao de", "leva a", "impacto", "efeito de", "resulta de"]
LEX_DES = ["destaca-se", "chama atencao", "notavel", "principal", "mais importante"]
LEX_TEN = ["tendencia", "aceleracao", "desaceleracao", "crescimento acelerado", "crescimento desacelerado", "declinio"]
LEX_CMP = ["maioria", "a maior parte", "dobro", "metade", "maior", "menor", "percentual", "porcentagem", "proporcao",
           "razao", "primeiro", "segundo", "terceiro"]
SETS = [{"id": "c1", "rotulo": "Manaus e Parintins", "membros": [MANAUS, PARINTINS]}]


def plain(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold()) if not unicodedata.combining(c))


def found(words, text):
    return [word for word in words if re.search(r"(?<!\w)" + re.escape(word) + r"(?!\w)", plain(text))]


def check(body):
    """Contrato comum: partes = texto, cada segmento conferido contra o caminho na resposta, léxico controlado."""
    resumo = body["resumo"]
    assert set(resumo) == {"versao", "texto", "partes", "segmentos", "contagens", "nota"}
    assert resumo["texto"] == "".join(part["texto"] for part in resumo["partes"])
    assert resumo_painel.verify(body)
    for segment in resumo["segmentos"]:
        assert resumo_painel.verify_segment(segment, body), segment
        if segment["formato"] in ("numero", "texto"):
            value = resolve(body, segment["caminho"])  # cópia literal do caminho, na regra de apresentação
            assert segment["texto"] == (value if segment["formato"] == "texto" else
                                        resumo_painel.number(value, segment.get("casas", 2)))
    forged = dict(resumo["segmentos"][0], texto=resumo["segmentos"][0]["texto"] + "0")
    assert not resumo_painel.verify_segment(forged, body)
    text = resumo["texto"]
    assert not found(LEX_NORM + LEX_CAU + LEX_DES, text), found(LEX_NORM + LEX_CAU + LEX_DES, text)
    assert not found(["acima", "abaixo"], text)
    template = " ".join(part["texto"] for part in resumo["partes"] if "segmento" not in part)
    assert not found(LEX_CMP, template), found(LEX_CMP, template)  # LEX-CMP só nas relações copiadas do motor
    if body.get("tendencia") is None:
        assert not found(LEX_TEN, text), found(LEX_TEN, text)
    # As contagens que a frase copia são as dos itens da resposta.
    units = [item for item in body["itens"] if item["tipo"] in ("municipio", "estado", "brasil")]
    assert resumo["contagens"]["unidades"] == len(units)
    assert resumo["contagens"]["sem_valor"] == sum(item[body["indicador"]] is None for item in units)
    assert resumo["contagens"]["conjuntos"] == sum(item["tipo"] == "conjunto" for item in body["itens"])
    json.dumps(resumo, allow_nan=False)
    return text


# --------------------------------------------------------------------------------------------- distribuição
def test_distribution_summary_copies_the_items_and_the_brazil_rate_as_context(repo):
    info = inspection()
    body = ok(page(info))
    assert by_id(body)[NOVO]["densidade"] == by_id(body)[MANACAPURU]["densidade"] == 8 and AM[0] == MANACAPURU
    text = check(body)
    rate = resumo_painel.number(body["contexto"]["brasil"]["densidade"])
    # Desde 24/10/2026: sem "Entre os municípios" e sem as contagens que são zero ("0 municípios sem valor").
    assert text == ("Em junho de 2024, o gráfico tem 5 municípios. A densidade vai de 8 a 25 por 1.000 habitantes. "
                    "Referência de contexto: a taxa do Brasil (total nacional) é de " + rate + " por 1.000 habitantes.")
    # Os extremos são cópias dos itens (o primeiro na ordem dos itens, no empate de 8 por 1.000).
    paths = [segment["caminho"] for segment in body["resumo"]["segmentos"]]
    items = body["itens"]
    assert ["itens", [item["id"] for item in items].index(MANACAPURU), "densidade"] in paths
    assert ["itens", [item["id"] for item in items].index(MANAUS), "densidade"] in paths
    # Quantidade, sem a escala da densidade; grupos e faixas com as contagens do motor.
    counts = ok(page(info, indicador="quantidade", grupos={"tipo": "quartis"}, faixas=[0, 10, 100]))
    text = check(counts)
    assert "A quantidade vai de 4 a 50." in text and "sem valor" not in text
    assert "por 1.000 habitantes" not in text  # sem a taxa (só com a densidade) e sem a escala
    assert "Grupos por posição (quartis): 1º quartil, " in text
    assert "Faixas de quantidade: 0 a <10, 3; 10 a 100, 2." in text  # fora das faixas e sem valor: zero, fora da frase
    assert counts["faixas"]["contagens"] == [3, 2]


def test_change_summary_copies_the_extremes_of_the_engine_variation(repo):
    body = ok(page(inspection(), competencia_inicial="202006"))
    text = check(body)
    assert "Variação da densidade entre junho de 2020 e junho de 2024: de " in text
    assert ". 2 municípios sem variação avaliável." in text  # TEFE (base zero) e NOVO AIRAO (sem registro em 2020)
    values = [item["variacao_percentual"]["densidade"] for item in body["itens"]
              if item["variacao_percentual"]["densidade"] is not None]
    assert resumo_painel.number(min(values)) + "% a " + resumo_painel.number(max(values)) + "%" in text


def test_one_territory_gets_its_own_sentence_without_ranges_or_zero_counts(repo):
    """Um território só (24/10/2026): a frase diz o nome, a competência e o valor dele, a variação com a direção (aumento,
    redução ou sem mudança, CAP-TMP-01) e a classe da tendência, sem frases coletivas ("entre os municípios"), sem "de X a
    X" e sem contagens zero. Base zero e série insuficiente em palavras, sem códigos. O mesmo vale para um estado e para o
    Brasil; com dois itens de mesmo valor, o valor sai uma vez."""
    info = inspection()
    window = PERIODS[2:]
    one = ok(page(info, base={"municipios": {"ids": [MANAUS]}}, competencia_inicial="202106",
                  tendencia={"competencias": window}))
    text = check(one)
    rate = resumo_painel.number(one["contexto"]["brasil"]["densidade"])
    assert one["itens"][0]["tendencia"]["rotulo"] == "Desaceleração do crescimento"
    assert text == ("MANAUS (AM), em junho de 2024: densidade de 25 por 1.000 habitantes. Entre junho de 2021 e junho de "
                    "2024, a variação da densidade foi de 25% (aumento). Tendência de junho de 2021 a junho de 2024: "
                    "Desaceleração do crescimento. Referência de contexto: a taxa do Brasil (total nacional) é de " + rate +
                    " por 1.000 habitantes.")
    assert ["itens", 0, "tendencia", "rotulo"] in [segment["caminho"] for segment in one["resumo"]["segmentos"]]
    tefe = check(ok(page(info, base={"municipios": {"ids": [TEFE]}}, competencia_inicial="202006",
                         tendencia={"competencias": PERIODS})))
    assert "a variação da densidade não é avaliável: o valor inicial é zero." in tefe and "BASE_ZERO" not in tefe
    novo = check(ok(page(info, base={"municipios": {"ids": [NOVO]}}, competencia_inicial="202006",
                         tendencia={"competencias": PERIODS})))
    assert "a variação da densidade não é avaliável: falta o valor numa das duas competências." in novo
    assert "Tendência de junho de 2019 a junho de 2024: não avaliável. " + TEXT_MINIMUM in novo
    para = check(ok(post(info, nivel="estados", indicador="densidade", competencia="202406", estados=["15"],
                         competencia_inicial="202106", tendencia={"competencias": window})))
    assert para.startswith("Pará (PA), em junho de 2024: densidade de 20 por 1.000 habitantes. Entre junho de 2021 e "
                           "junho de 2024, a variação da densidade foi de 0% (sem mudança). Tendência de junho de 2021 a "
                           "junho de 2024: Sem classificação, porque o valor não mudou entre os períodos.")
    brasil = ok(post(info, nivel="brasil", indicador="densidade", competencia="202406", competencia_inicial="202106",
                     tendencia={"competencias": window}))
    text = check(brasil)
    item = brasil["itens"][0]
    assert text == ("Brasil, em junho de 2024: densidade de " + resumo_painel.number(item["densidade"]) + " por 1.000 "
                    "habitantes. Entre junho de 2021 e junho de 2024, a variação da densidade foi de " +
                    resumo_painel.number(item["variacao_percentual"]["densidade"]) + "% (redução). Tendência de junho de "
                    "2021 a junho de 2024: " + item["tendencia"]["rotulo"] + ".")
    assert "Referência de contexto" not in text  # o próprio item é o total nacional
    pair = check(ok(page(info, base={"municipios": {"ids": [MANACAPURU, NOVO]}})))
    assert "A densidade é de 8 por 1.000 habitantes em todos." in pair and "de 8 a 8" not in pair


# --------------------------------------------------------------------------------------------- análise espacial
def test_spatial_summary_has_the_reference_the_distances_and_the_straight_line_note(repo):
    body = ok(page(inspection(), referencia={"membros": [PARINTINS, BELEM]}, faixas_distancia=[0, 100, 1000]))
    text = check(body)
    assert "Distância em linha reta até o membro mais próximo da referência (PARINTINS (AM) e BELEM (PA)): de " in text
    assert ". 1 município sem distância." in text  # MANACAPURU, sem coordenadas (os membros da referência ficam fora)
    assert "Faixas de distância (km): 0 a <100, " in text
    assert text.count(TPL_11) == 1 and ["notas", body["notas"].index(TPL_11)] in [
        segment["caminho"] for segment in body["resumo"]["segmentos"]]
    single = check(ok(page(inspection(), referencia={"membros": [MANAUS]})))
    assert "Distância em linha reta até a referência MANAUS (AM): de " in single


# --------------------------------------------------------------------------------------------- tendência
def test_trend_summary_uses_the_engine_family_counts_only_with_cap_ten_01(repo):
    body = ok(page(inspection(), tendencia={"competencias": PERIODS}))
    text = check(body)
    families = body["tendencia"]["familias"]
    assert (families["CRESCIMENTO"], families["DECLINIO"], families["NENHUMA"], body["tendencia"]["nao_avaliaveis"]) == (
        2, 1, 1, 1)
    assert ("Tendência de junho de 2019 a junho de 2024: 2 na família do crescimento, 1 na família do declínio e 1 sem "
            "classificação; 1 não avaliável.") in text
    short = ok(page(inspection(), tendencia={"competencias": PERIODS[-3:]}))
    assert ("Tendência de junho de 2022 a junho de 2024: " + short["tendencia"]["bloqueio"]["texto"]) in check(short)


# --------------------------------------------------------------------------------------------- condições e comparação
def test_conditions_summary_copies_the_three_state_counts(repo):
    body = ok(page(inspection(), referencia={"membros": [PARINTINS, BELEM]},
                   condicoes=[{"atributo": "densidade", "operador": "<", "valor": "15"},
                              {"atributo": "distancia_km", "operador": ">", "valor": 100}]))
    counts = body["condicoes"]["contagens"]
    assert (" Condições " + body["condicoes"]["descricao"] + ": atendem, " + str(counts["ATENDE"]) + "; não atendem, " +
            str(counts["NAO_ATENDE"]) + ("; sem dado, " + str(counts["NAO_AVALIAVEL"]) if counts["NAO_AVALIAVEL"] else "") +
            ".") in check(body)


def test_comparison_summary_is_the_relation_returned_by_the_engine(repo):
    info = inspection()
    pair = ok(page(info, comparar=[TEFE, MANAUS]))
    text = check(pair)
    assert ("Comparação de densidade: MANAUS (AM), 25; TEFE (AM), 10 por 1.000 habitantes. O valor de MANAUS (AM) é maior "
            "que o de TEFE (AM). Diferença A − B: 15 por 1.000 habitantes.") in text
    assert any(segment["tipo"] == "RELACAO" for segment in pair["resumo"]["segmentos"])
    three = ok(page(info, comparar=[MANAUS, TEFE, PARINTINS]))
    assert ("Comparação de densidade: MANAUS (AM), 25; TEFE (AM), 10; PARINTINS (AM), 12 por 1.000 habitantes; maior "
            "valor: MANAUS (AM); menor valor: TEFE (AM); sem diferenças automáticas entre pares.") in check(three)
    # A relação vem do motor: forjar o texto, ou mudar a relação no resultado, faz o segmento não conferir.
    relation = next(segment for segment in pair["resumo"]["segmentos"] if segment["tipo"] == "RELACAO")
    assert not resumo_painel.verify_segment(dict(relation, texto="O valor de TEFE (AM) é maior que o de MANAUS (AM)."),
                                            pair)
    changed = json.loads(json.dumps(pair))
    changed["comparacao"]["diferencas"][0]["relacao"] = "MENOR"
    assert not resumo_painel.verify(changed)


# --------------------------------------------------------------------------------------------- conjuntos e estados
def test_sets_and_states_keep_the_caveats_of_the_engine(repo):
    info = inspection()
    sets = ok(page(info, conjuntos=SETS))
    text = check(sets)
    assert text.startswith("Em junho de 2024, o gráfico tem 5 municípios e 1 conjunto. A densidade vai de ")
    assert "Conjuntos: soma das contagens dos componentes, com possível dupla contagem." in text
    states = ok(post(info, nivel="estados", indicador="densidade", competencia="202406"))
    text = check(states)
    assert text.startswith("Em junho de 2024, o gráfico tem 2 estados. A densidade vai de ")
    assert NOTE_STATES in text and "Referência de contexto: a taxa do Brasil (total nacional) é de" in text


# --------------------------------------------------------------------------------------------- planilhas
def test_uploaded_summary_uses_the_received_labels_and_the_rotation_percent(repo):
    body = ok(districts(premissas={"count_unit": "pessoas", "crs": "SIRGAS2000"}, referencia={"membros": [
        "name:Alto Rio"]}, tendencia={"competencias": YEARS}))
    text = check(body)
    assert text.startswith("Em 2024, o gráfico tem 4 distritos. A densidade vai de 10 a 16 por 1.000 habitantes. ")
    assert "1 distrito sem distância." in text and "Tendência de 2021 a 2024: " in text
    assert "Referência de contexto" not in text  # o contexto do Brasil não se aplica às planilhas
    people = {"2023": {"Alto Rio": ["p1", "p2", "p3", "p4"], "Campina": ["p5", "p6"]},
              "2024": {"Alto Rio": ["p1", "p2", "p9"], "Campina": ["p5", "p6", "p7"], "Serra": ["p8"]}}
    lines = ["distrito;provincia;ano;categoria;id_pessoa;populacao"]
    for year, units in people.items():
        for name, ids in units.items():
            lines += [";".join([name, "Província Norte", year, "Enfermeiros", person, "1000"]) for person in ids]
    mapping = {"territory": "distrito", "period": "ano", "category": "categoria", "identity": "id_pessoa",
               "population": "populacao", "grupo_territorial": "provincia"}
    rotation = ok(upload({"nivel": "municipios", "indicador": "quantidade", "competencia": "2024", "rotulos": LABELS,
                          "base": {"municipios": {"todos": True}}, "rotatividade": {"inicial": "2023", "final": "2024"}},
                         mapping=mapping, contents=("\n".join(lines) + "\n").encode(), name="pessoas.csv"))
    text = check(rotation)
    assert ("Permanência da coorte inicial entre 2023 e 2024: de 50% a 100%. 1 distrito sem permanência avaliável."
            in text)


# --------------------------------------------------------------------------------------------- regras e falhas
def test_numbers_follow_the_presentation_rule():
    assert resumo_painel.number(5570) == "5.570" and resumo_painel.number(0) == "0"
    assert resumo_painel.number(2.074847150002237) == "2,07" and resumo_painel.number(1474.7512) == "1.474,75"
    assert resumo_painel.number(0.004) == "0,004"  # mais casas só quando o valor arredondaria para zero
    assert resumo_painel.number(-75.1) == "-75,10"
    # Mais casas só para preservar a relação entre valores comparados na mesma frase.
    assert resumo_painel.places_for([0.123, 0.124]) == 3 and resumo_painel.places_for([0.12, 2.5]) == 2
    assert resumo_painel.places_for([8.001, 8.004]) == 3 and resumo_painel.places_for([3, 3]) == 2
    assert resumo_painel.places_for([8, 8.004]) == 2  # o inteiro sai sem casas: "8" e "8,00" já se distinguem


def test_a_failing_summary_never_breaks_the_chart(repo, monkeypatch, caplog):
    info = inspection()
    first = ok(page(info))
    assert "resumo" in first

    def broken(*_args):
        raise RuntimeError("falha simulada")

    # Cada remendo vale só no seu bloco: monkeypatch.undo() desfaria também os da fixture repo (a base temporária).
    with monkeypatch.context() as patch:
        patch.setattr(resumo_painel, "summary", broken)
        with caplog.at_level(logging.ERROR):
            failed = ok(page(info))
    assert "resumo" not in failed
    assert failed["itens"] == first["itens"] and failed["chave_execucao"] == first["chave_execucao"]
    assert "Falha ao compor a frase-resumo do gráfico" in caplog.text
    # Um segmento que não confere tira a frase da resposta (nunca uma frase com número não conferido).
    with monkeypatch.context() as patch:
        patch.setattr(resumo_painel, "verify", lambda body: False)
        assert "resumo" not in ok(page(info))


def test_the_summary_never_reaches_the_provider(repo, monkeypatch):
    calls = []

    async def forbidden(*args):
        calls.append(args)
        raise AssertionError("A frase-resumo não chama o provedor de IA.")

    monkeypatch.setattr(llm_bridge, "_call_gemini", forbidden)
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-not-real")
    body = ok(page(inspection(), tendencia={"competencias": PERIODS}, comparar=[MANAUS, TEFE]))
    assert body["resumo"]["texto"] and calls == []
    assert painel.summary_facts(body)["contagens"] == body["resumo"]["contagens"]
    upload_body = ok(upload({"nivel": "municipios", "indicador": "densidade", "competencia": "2024", "rotulos": LABELS,
                             "premissas": {"count_unit": "pessoas"}, "base": {"municipios": {"todos": True}}},
                            mapping=DISTRICT_MAPPING))
    assert upload_body["resumo"]["texto"] and calls == []
