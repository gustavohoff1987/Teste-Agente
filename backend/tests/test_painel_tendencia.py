"""Tendência da página única (CAP-TEN-01, DA-15): a classe de cada item em POST /api/painel com `tendencia`.

Os testes documentam o diagnóstico de 23/10/2026 (Docs/PAINEL_INTEGRADO.md, "Tendência na janela"): na base versionada,
a ausência generalizada de classe em janelas longas — os 62 municípios do Amazonas sem classificação com as 22
competências de 2014 a 2024 — vem da regra DA-15 (uma velocidade positiva e uma negativa na janela bastam para a série
ficar sem classificação por mudança de direção), não de falha no cálculo. O método não muda.

Catálogo sintético próprio, instalado como versão governada (manifesto próprio), com sete competências anuais de junho
(2018 a 2024) e população constante (2.000 em todas as linhas: a densidade, por 1.000 habitantes, é a metade da
quantidade). Cada unidade realiza um desfecho:
- as séries de AT-53 (SPEC, seção 20.4) nos últimos quatro junhos, sem registro antes (10, 11, 12, 14 → aceleração do
  crescimento; 10, 12, 14, 16 → crescimento; 10, 14, 16, 17 → desaceleração do crescimento; 20, 18, 15, 11 → aceleração
  de declínio; 20, 12, 8, 6 → desaceleração de declínio (os rótulos do declínio com "de" desde 24/10/2026, divergência
  aprovada); 10, 12, 12, 15 → crescimento, intervalo com velocidade zero;
  10, 12, 15, 17 → crescimento, ritmo sem monotonicidade; 10, 12, 11, 13 → sem classificação, mudança de direção;
  5, 5, 5, 5 → sem classificação, série estável), mais o declínio (constante, e com intervalo de velocidade zero);
- três observações (série insuficiente) e o intervalo irregular de AT-53 (2018: 10, 2019: 12, 2021: 16, 2022: 18 →
  velocidades iguais, crescimento, pela normalização pelo tempo transcorrido);
- séries longas, cuja classe muda com a janela: uma queda antiga basta para a janela inteira ficar sem classificação.
Os testes com a base versionada rodam no job dados-reais (ADT_REAL_DATA_DIR), somente em leitura.
"""
import hashlib
import json
from fractions import Fraction

import pytest
from openpyxl import Workbook

import brazil_data
import main
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from test_painel_pagina import HEADER, analyze, by_id, inspection, ok, post
from test_painel_pagina import real  # noqa: F401 (fixture)

JUNES = ["201806", "201906", "202006", "202106", "202206", "202306", "202406"]
LAST4 = JUNES[-4:]
POPULATION = 2000
# código: (nome, quantidades de junho de 2018 a 2024; None = sem registro na competência)
SERIES = {
    "130010": ("CRESCE ACELERADO", [None, None, None, 10, 11, 12, 14]),
    "130020": ("CRESCE CONSTANTE", [None, None, None, 10, 12, 14, 16]),
    "130030": ("CRESCE DESACELERADO", [None, None, None, 10, 14, 16, 17]),
    "130040": ("DECLINA ACELERADO", [None, None, None, 20, 18, 15, 11]),
    "130050": ("DECLINA DESACELERADO", [None, None, None, 20, 12, 8, 6]),
    "130060": ("CRESCE COM PAUSA", [None, None, None, 10, 12, 12, 15]),
    "130070": ("CRESCE SEM RITMO", [None, None, None, 10, 12, 15, 17]),
    "130080": ("SOBE E DESCE", [None, None, None, 10, 12, 11, 13]),
    "130090": ("ESTAVEL", [None, None, None, 5, 5, 5, 5]),
    "130100": ("DECLINA CONSTANTE", [None, None, None, 20, 18, 16, 14]),
    "130110": ("DECLINA COM PAUSA", [None, None, None, 20, 18, 18, 15]),
    "130120": ("TRES OBSERVACOES", [None, None, None, None, 10, 11, 12]),
    "130130": ("INTERVALO IRREGULAR", [10, 12, None, 16, 18, None, None]),
    "130140": ("LONGA COM QUEDA ANTIGA", [30, 20, 15, 10, 11, 12, 14]),
    "130150": ("LONGA ESTAVEL NO FIM", [5, 6, 7, 8, 8, 8, 8]),
    "130160": ("LONGA EM DECLINIO", [40, 30, 20, 20, 12, 8, 6]),
    "130170": ("LONGA ACELERADA", [7, 8, 9, 10, 11, 12, 14]),
}
CODES = ["code:" + code for code in SERIES]
# Classe e motivo esperados em cada janela, pela regra de DA-15 (classe None: não avaliável).
EXPECTED_LAST4 = {
    "130010": ("CRESCIMENTO_ACELERADO", None),
    "130020": ("CRESCIMENTO", None),
    "130030": ("CRESCIMENTO_DESACELERADO", None),
    "130040": ("DECLINIO_ACELERADO", None),
    "130050": ("DECLINIO_DESACELERADO", None),
    "130060": ("CRESCIMENTO", None),
    "130070": ("CRESCIMENTO", None),
    "130080": ("SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO"),
    "130090": ("SEM_CLASSIFICACAO", "SERIE_ESTAVEL"),
    "130100": ("DECLINIO", None),
    "130110": ("DECLINIO", None),
    "130120": (None, "SERIE_INSUFICIENTE"),
    "130130": (None, "SERIE_INSUFICIENTE"),  # só 2021 e 2022 na janela
    "130140": ("CRESCIMENTO_ACELERADO", None),  # 10, 11, 12, 14
    "130150": ("SEM_CLASSIFICACAO", "SERIE_ESTAVEL"),  # 8, 8, 8, 8
    "130160": ("DECLINIO_DESACELERADO", None),  # 20, 12, 8, 6
    "130170": ("CRESCIMENTO_ACELERADO", None),
}
EXPECTED_ALL = {**EXPECTED_LAST4,
                "130130": ("CRESCIMENTO", None),  # 2018, 2019, 2021 e 2022: velocidades iguais (AT-53)
                "130140": ("SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO"),  # 30, 20, 15, 10, 11, 12, 14
                "130150": ("CRESCIMENTO", None),  # 5, 6, 7, 8, 8, 8, 8: intervalos de velocidade zero
                "130160": ("DECLINIO", None)}  # 40, 30, 20, 20, 12, 8, 6: intervalo de velocidade zero
LABELS = {"CRESCIMENTO": "Crescimento", "CRESCIMENTO_ACELERADO": "Aceleração do crescimento",
          "CRESCIMENTO_DESACELERADO": "Desaceleração do crescimento", "DECLINIO": "Declínio",
          "DECLINIO_ACELERADO": "Aceleração de declínio", "DECLINIO_DESACELERADO": "Desaceleração de declínio",
          "SEM_CLASSIFICACAO": "Sem classificação"}
FAMILY = {"CRESCIMENTO": "CRESCIMENTO", "CRESCIMENTO_ACELERADO": "CRESCIMENTO",
          "CRESCIMENTO_DESACELERADO": "CRESCIMENTO", "DECLINIO": "DECLINIO", "DECLINIO_ACELERADO": "DECLINIO",
          "DECLINIO_DESACELERADO": "DECLINIO", "SEM_CLASSIFICACAO": "NENHUMA"}
MOTIVE_TEXT = {"MUDANCA_DE_DIRECAO": "Mudança de direção", "SERIE_ESTAVEL": "Série estável"}
ZERO = dict.fromkeys(LABELS, 0)


def municipal_text():
    lines = [HEADER]
    for i, period in enumerate(JUNES):
        for index, (code, (name, counts)) in enumerate(SERIES.items(), start=11):
            if counts[i] is None:
                continue
            lines.append(";".join(["NORTE", "AM", name, code, "-3," + str(index), "-60," + str(index), "MEDICINA",
                                   period[:4], str(int(period[4:])), str(counts[i]), str(POPULATION)]))
    return "\n".join(lines) + "\n"


@pytest.fixture
def series(tmp_path, monkeypatch):
    """Repositório temporário com o catálogo das séries como versão governada (manifesto próprio), como a fixture repo de
    test_painel_pagina.py."""
    root = tmp_path / "repositorio"
    root.mkdir()
    book = Workbook()
    book.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for period in JUNES:
        book.active.append(["Brasil", int(period[:4]), int(period[4:]), "MEDICINA", 1000])
    book.save(root / FILES["national"])
    (root / FILES["municipal"]).write_text(municipal_text(), encoding="utf-8")
    write_state_source(root, {("AM", period): 50 for period in JUNES})
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


def trend(info, window, indicador="densidade", base=None):
    return ok(post(info, nivel="municipios", indicador=indicador, competencia="202406",
                   base=base or {"municipios": {"estados": ["13"]}}, tendencia={"competencias": window}))


def months(start, end):
    return (int(end[:4]) - int(start[:4])) * 12 + int(end[4:]) - int(start[4:])


def expected_trend(code, window, indicador, expected):
    """O que DA-15 dá para a série na janela, calculado aqui, sem o motor: as observações sem imputação (competência sem
    registro fica fora), as velocidades v = (y2 − y1) ÷ (t2 − t1) em meses (passo 3; a densidade é quantidade × 1.000 ÷
    população) e a classe esperada, com o rótulo, a família e o motivo."""
    scale = Fraction(1000, POPULATION) if indicador == "densidade" else Fraction(1)
    points = [(period, Fraction(count) * scale) for period, count in zip(JUNES, SERIES[code][1])
              if count is not None and period in window]
    classe, motive = expected[code]
    if classe is None:
        return {"classe": None, "familia": None, "rotulo": "Não avaliável: série insuficiente", "motivo": motive,
                "motivo_texto": str(len(points)) + " de 4 observações necessárias", "avaliavel": False,
                "observacoes": [{"competencia": period, "valor": float(value)} for period, value in points],
                "velocidades": []}
    speeds = [(b - a) / months(start, end) for (start, a), (end, b) in zip(points, points[1:])]
    return {"classe": classe, "familia": FAMILY[classe], "rotulo": LABELS[classe], "motivo": motive,
            "motivo_texto": MOTIVE_TEXT[motive] if motive else None, "avaliavel": True,
            "observacoes": [{"competencia": period, "valor": float(value)} for period, value in points],
            "velocidades": [float(speed) for speed in speeds]}


def coherent(item_trend):
    """A classe concorda com o sinal das velocidades (DA-15, passos 4 a 6): família do crescimento, nenhuma negativa e
    alguma positiva; família do declínio, nenhuma positiva e alguma negativa; mudança de direção, as duas; série
    estável, todas zero; não avaliável, sem velocidades."""
    speeds = item_trend["velocidades"]
    up, down = any(v > 0 for v in speeds), any(v < 0 for v in speeds)
    if item_trend["familia"] == "CRESCIMENTO":
        return up and not down
    if item_trend["familia"] == "DECLINIO":
        return down and not up
    if item_trend["motivo"] == "MUDANCA_DE_DIRECAO":
        return up and down
    if item_trend["motivo"] == "SERIE_ESTAVEL":
        return bool(speeds) and not up and not down
    return not item_trend["avaliavel"] and speeds == []


# --------------------------------------------------------------------------------------------- catálogo sintético
@pytest.mark.parametrize("indicador", ["densidade", "quantidade"])
def test_each_series_gets_the_class_of_da_15_in_the_last_four_junes(series, indicador):
    body = trend(inspection(), LAST4, indicador)
    items = by_id(body)
    assert list(items) == CODES
    for code in SERIES:
        item_trend = items["code:" + code]["tendencia"]
        assert item_trend == expected_trend(code, LAST4, indicador, EXPECTED_LAST4), code
        assert coherent(item_trend), code
    top = body["tendencia"]
    assert top["contagens"] == {**ZERO, "CRESCIMENTO": 3, "CRESCIMENTO_ACELERADO": 3, "CRESCIMENTO_DESACELERADO": 1,
                                "DECLINIO": 2, "DECLINIO_ACELERADO": 1, "DECLINIO_DESACELERADO": 2, "SEM_CLASSIFICACAO": 3}
    assert top["sem_classificacao_por_motivo"] == {"MUDANCA_DE_DIRECAO": 1, "SERIE_ESTAVEL": 2}
    assert top["nao_avaliaveis_por_motivo"] == {"SERIE_INSUFICIENTE": 2, "INCOMPARABILIDADE": 0}
    assert top["familias"] == {"CRESCIMENTO": 7, "DECLINIO": 5, "NENHUMA": 3}
    assert (top["avaliaveis"], top["nao_avaliaveis"], top["unidades_total"], top["universo"]) == (15, 2, 17, 17)
    # Classes e não avaliáveis juntos: resultado com limitação (RQ-CAP-08).
    assert (top["desfecho"], top["bloqueio"]) == ("RES-LIM", None)
    assert (top["indicador"], top["unidade_tempo"]) == (indicador, "mês")
    assert (top["janela"]["periodos"], top["janela"]["inicio"], top["janela"]["fim"]) == (LAST4, "202106", "202406")
    # As contagens do motor são as dos itens.
    tally = dict(ZERO)
    for item in body["itens"]:
        if item["tendencia"]["classe"]:
            tally[item["tendencia"]["classe"]] += 1
    assert tally == top["contagens"]


def test_the_classes_change_with_the_window_as_the_series_do(series):
    info = inspection()
    recent, whole = trend(info, LAST4), trend(info, JUNES)
    before, after = by_id(recent), by_id(whole)
    for code in SERIES:
        item_trend = after["code:" + code]["tendencia"]
        assert item_trend == expected_trend(code, JUNES, "densidade", EXPECTED_ALL), code
        assert coherent(item_trend), code
    changed = {code for code in SERIES
               if before["code:" + code]["tendencia"]["classe"] != after["code:" + code]["tendencia"]["classe"]}
    # Só mudam as séries com registros fora dos últimos quatro junhos; sem eles, as observações são as mesmas (nada é
    # imputado nas competências sem registro).
    assert changed == {"130130", "130140", "130150", "130160"}
    # Uma queda antiga basta: 10, 11, 12, 14 acelera nos últimos junhos, mas a série inteira muda de direção.
    longa = after["code:130140"]["tendencia"]
    assert (longa["classe"], longa["motivo"], longa["motivo_texto"]) == ("SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO",
                                                                        "Mudança de direção")
    assert sum(v < 0 for v in longa["velocidades"]) == 3 and sum(v > 0 for v in longa["velocidades"]) == 3
    # Intervalo irregular de AT-53: 2 por ano em cada intervalo (2019 → 2021 são 24 meses), a mesma velocidade.
    irregular = after["code:130130"]["tendencia"]
    assert [point["competencia"] for point in irregular["observacoes"]] == ["201806", "201906", "202106", "202206"]
    assert irregular["velocidades"] == [float(Fraction(2, 12) / 2)] * 3  # densidade: metade da quantidade, por mês
    quantity = ok(post(info, nivel="municipios", indicador="quantidade", competencia="202406",
                       base={"municipios": {"ids": ["code:130130"]}}, tendencia={"competencias": JUNES}))
    assert quantity["itens"][0]["tendencia"]["velocidades"] == [float(Fraction(2, 12))] * 3
    top = whole["tendencia"]
    assert top["contagens"] == {**ZERO, "CRESCIMENTO": 5, "CRESCIMENTO_ACELERADO": 2, "CRESCIMENTO_DESACELERADO": 1,
                                "DECLINIO": 3, "DECLINIO_ACELERADO": 1, "DECLINIO_DESACELERADO": 1, "SEM_CLASSIFICACAO": 3}
    assert top["sem_classificacao_por_motivo"] == {"MUDANCA_DE_DIRECAO": 2, "SERIE_ESTAVEL": 1}
    assert top["nao_avaliaveis_por_motivo"] == {"SERIE_INSUFICIENTE": 1, "INCOMPARABILIDADE": 0}
    assert (top["avaliaveis"], top["nao_avaliaveis"], top["desfecho"]) == (16, 1, "RES-LIM")
    assert top["janela"]["periodos"] == JUNES


def test_the_outcome_of_the_stage_follows_rq_cap_08(series):
    info = inspection()

    def outcome(codes, window=LAST4):
        return trend(info, window, base={"municipios": {"ids": ["code:" + code for code in codes]}})["tendencia"]

    # Só classes: RES-VAL. Só sem classificação (resultado do método, não falta de dados): RES-SCL.
    assert outcome(["130010", "130020", "130040", "130100"])["desfecho"] == "RES-VAL"
    stable = outcome(["130080", "130090"])
    assert (stable["desfecho"], stable["sem_classificacao_por_motivo"]) == ("RES-SCL", {"MUDANCA_DE_DIRECAO": 1,
                                                                                        "SERIE_ESTAVEL": 1})
    # Nenhuma unidade avaliável: a causa normativa (BLQ-MET), sem bloqueio da etapa.
    missing = outcome(["130120", "130130"])
    assert (missing["desfecho"], missing["bloqueio"], missing["avaliaveis"]) == ("BLQ-MET", None, 0)
    # Menos de quatro competências na janela: o bloqueio da etapa (série insuficiente).
    short = outcome(["130010", "130020"], LAST4[1:])
    assert (short["desfecho"], short["bloqueio"]["motivo"], short["bloqueio"]["periodos_distintos"]) == (
        "BLQ-MET", "SERIE_INSUFICIENTE", 3)


# --------------------------------------------------------------------------------------------- base versionada
ALL22 = [str(year) + month for year in range(2014, 2025) for month in ("01", "06")]
JUNE4 = ["202106", "202206", "202306", "202406"]
AMAZONAS = {"nivel": "municipios", "indicador": "densidade", "competencia": "202406",
            "base": {"municipios": {"estados": ["13"]}}}


def test_real_amazonas_has_no_class_in_the_long_window_by_the_change_of_direction(real):
    """Diagnóstico de 23/10/2026: com as 22 competências, os 62 municípios do Amazonas ficam sem classificação por
    mudança de direção (cada série tem velocidades positivas e negativas); não é falha do cálculo."""
    body = ok(post(real, **AMAZONAS, tendencia={"competencias": ALL22}))
    assert len(body["itens"]) == 62
    for item in body["itens"]:
        item_trend = item["tendencia"]
        assert (item_trend["classe"], item_trend["motivo"]) == ("SEM_CLASSIFICACAO", "MUDANCA_DE_DIRECAO"), item["id"]
        assert any(v > 0 for v in item_trend["velocidades"]) and any(v < 0 for v in item_trend["velocidades"])
    top = body["tendencia"]
    assert top["contagens"] == {**ZERO, "SEM_CLASSIFICACAO": 62}
    assert top["sem_classificacao_por_motivo"] == {"MUDANCA_DE_DIRECAO": 62, "SERIE_ESTAVEL": 0}
    assert (top["desfecho"], top["nao_avaliaveis"]) == ("RES-SCL", 0)
    # As contagens do motor são as da evolução temporal da mesma janela (/api/analyze).
    analysis = ok(analyze(real, "temporal", {"municipios": {"estados": ["13"]}}, temporal_indicator="density",
                          period_filters=ALL22))
    assert top["contagens"] == analysis["metadata"]["tendencia"]["contagens"]
    manaus = by_id(body)["code:130260"]["tendencia"]["velocidades"]
    assert (sum(v > 0 for v in manaus), sum(v < 0 for v in manaus)) == (17, 4)
    # Os estados, com as 22: 6 em crescimento e 21 sem classificação, todos por mudança de direção. Até a correção de
    # 25/10/2026 da linha do 251365 em 2016/6 (com a população de Santarém do Pará), a densidade da PB caía em junho de
    # 2016 e a série dela ficava sem classificação (eram 5 e 22).
    states_body = ok(post(real, nivel="estados", indicador="densidade", competencia="202406",
                          tendencia={"competencias": ALL22}))
    states = states_body["tendencia"]
    assert states["contagens"] == {**ZERO, "CRESCIMENTO": 6, "SEM_CLASSIFICACAO": 21}
    assert states["sem_classificacao_por_motivo"] == {"MUDANCA_DE_DIRECAO": 21, "SERIE_ESTAVEL": 0}
    assert by_id(states_body)["uf:25"]["tendencia"]["classe"] == "CRESCIMENTO"


def test_real_amazonas_has_classes_in_the_last_four_junes_coherent_with_the_speeds(real):
    recent = ok(post(real, **AMAZONAS, tendencia={"competencias": JUNE4}))
    top = recent["tendencia"]
    assert top["contagens"] == {**ZERO, "CRESCIMENTO": 17, "CRESCIMENTO_ACELERADO": 4, "CRESCIMENTO_DESACELERADO": 1,
                                "DECLINIO_ACELERADO": 2, "SEM_CLASSIFICACAO": 38}
    assert (top["sem_classificacao_por_motivo"]["MUDANCA_DE_DIRECAO"], top["desfecho"]) == (38, "RES-VAL")
    assert any(item["tendencia"]["familia"] in ("CRESCIMENTO", "DECLINIO") for item in recent["itens"])
    for item in recent["itens"]:
        assert coherent(item["tendencia"]), item["id"]
    # O resultado muda com a janela: os 24 classificados nos últimos junhos ficam sem classe com as 22 competências.
    whole = by_id(ok(post(real, **AMAZONAS, tendencia={"competencias": ALL22})))
    changed = [item["id"] for item in recent["itens"]
               if item["tendencia"]["classe"] != whole[item["id"]]["tendencia"]["classe"]]
    assert len(changed) == 62 - 38
