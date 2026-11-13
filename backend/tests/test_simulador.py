"""Simulador de Cenários Territoriais (comando V22, etapa 4; backend/simulador.py; a referência é
Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2.5, 7 a 9, 11 e 8.8, e Docs/SIMULADOR_DE_CENARIOS.md).

Três grupos de testes:
- **fórmulas**, sobre séries sintéticas montadas direto em `series_brasil.Base` (o calendário real, de janeiro e junho de 2014 a
  2024): a persistência (M0) e a persistência com a deriva do estado (M0d); a taxa composta com o tempo real (M1); a tendência
  linear robusta (M2) e a log-linear (M3); a taxa informada pela pessoa; o zero e a ausência; a quebra de fonte (a volta ao M0);
  as intervenções (somadas à base, sem crescer com ela; a permanência; a retirada impossível); os conjuntos e os estados como
  unidade; a média aritmética, só descritiva; os avisos de horizonte; as faixas de 80% (só do M0d municipal, de 1 a 4 anos, pela
  retroprojeção com origens móveis) e a ausência de observações futuras nos ajustes;
- **rota** POST /api/simulador, com um catálogo sintético instalado como versão governada; da etapa 5 do comando: o Brasil como
  território (só no Simulador), as referências fixas, dinâmicas e por valor (o alcance, a sobreposição e a comparação por taxa com
  a população constante), o planejamento inverso (o menor inteiro que alcança a meta, reaplicado ao Simulador), a hipótese
  derivada da simulação e as recusas;
- **base versionada** (job dados-reais, ADT_REAL_DATA_DIR, somente leitura): as faixas e os erros da retroprojeção do anexo
  (seção 8.8), o Distrito Federal (a quebra de fonte), Rio Rufino (o pico fora do ajuste) e o limite de territórios; o Brasil,
  as referências de Manaus, o planejamento inverso e "Simular recuperação" (etapa 5).
Nenhum valor sintético representa quantitativos reais.
"""
import hashlib
import json
import os
import random
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import detector
import main
import series_brasil
import simulador
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from install_brazil_data import install

client = TestClient(main.app)
PERIODOS = tuple(str(ano) + mes for ano in range(2014, 2025) for mes in ("01", "06"))
T = len(PERIODOS)
MESES = np.array([series_brasil.mes_da_competencia(p) for p in PERIODOS])
ANOS = (MESES - MESES[-1]) / 12.0   # o tempo real de cada registro, em anos, até jun/2024 (5 e 7 meses entre os registros)
FIXO = "Cenário hipotético, não é previsão: "


def base(series: dict, estados: dict | None = None) -> series_brasil.Base:
    codigos = tuple(sorted(series))
    quantidade = np.array([[np.nan if v is None else float(v) for v in series[codigo]] for codigo in codigos])
    prefixos = tuple(codigo[:2] for codigo in codigos)
    do_estado = {}
    for linha, prefixo in enumerate(prefixos):
        do_estado.setdefault(prefixo, []).append(linha)
    vazio = np.full(quantidade.shape, np.nan)
    return series_brasil.Base(
        versao="sintetica-" + hashlib.sha256(quantidade.tobytes()).hexdigest()[:12], periodos=PERIODOS, meses=MESES, codigos=codigos,
        nomes=tuple("M" + codigo for codigo in codigos), prefixos=prefixos, quantidade=quantidade, populacao=vazio,
        latitude=vazio, longitude=vazio,
        estados={prefixo: np.array(valores, dtype=float) for prefixo, valores in (estados or {}).items()},
        brasil=np.full(T, np.nan), indice={codigo: linha for linha, codigo in enumerate(codigos)},
        do_estado={prefixo: tuple(linhas) for prefixo, linhas in do_estado.items()})


def simular(b, territorio, cenario, horizonte="202606", janela=None):
    """Um território num cenário, pelo caminho da rota (a calibração do Detector e a retroprojeção da própria base)."""
    cal = detector.calibrar(b, guardar=False)
    retro = simulador.retroprojetar(b, guardar=False)
    inicio, fim, _ = simulador._janela(b, janela)
    pedido = simulador._cenarios([cenario], b, {territorio.id})[0]
    return simulador._simular(b, cal, retro, territorio, pedido, inicio, fim, simulador._competencia_futura(horizonte, "Data final"))


def avisos(resultado):
    return [aviso["codigo"] for aviso in resultado["avisos"]]


def municipio(b, codigo):
    return series_brasil.municipio(b, codigo)


# --------------------------------------------------------------------------------------------- M0 e M0d
def test_persistencia_e_persistencia_com_a_deriva_do_estado():
    # A soma municipal da UF cresce 10% ao ano (composto); o município fica em 10.
    b = base({"110001": [10] * T, "110002": [100 * 1.1 ** a - 10 for a in ANOS]})
    alvo = municipio(b, "110001")
    padrao = simular(b, alvo, {"metodo": "padrao"})
    assert padrao["estado"] == "calculado"
    assert padrao["metodo"] == {"pedido": "padrao", "usado": "M0d", "rotulo": "persistência com o crescimento recente do estado", "padrao": True,
                                "provisorio": True, "voltou_ao_m0": False, "soma": None}
    assert padrao["parametros"]["n0"] == 10 and padrao["parametros"]["origem"] == "202406"
    assert padrao["parametros"]["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7}  # os 3 anos até o último registro
    assert padrao["parametros"]["deriva_pct"] == pytest.approx(10.0) and padrao["parametros"]["estado_da_deriva"] == "Rondônia"
    assert padrao["final"]["base"] == pytest.approx(10 * 1.1 ** 2) and padrao["final"]["intervencao"] == 0
    assert padrao["final"]["total"] == pytest.approx(12.1) and padrao["final"]["data"] == "202606"
    # O texto é o do modelo fixo: o método, as premissas, o valor (inteiro) e a data, com "Base: registros até…".
    assert padrao["texto"] == (FIXO + "com o método persistência com o crescimento recente do estado e as premissas janela de jun/2021 a "
                               "jun/2024; crescimento de Rondônia de +10,00% ao ano; sem intervenção, M110001 teria 12 médicos em "
                               "jun/2026. Base: registros até jun/2024.")
    # Data final em qualquer mês: 4,5 anos depois, com o tempo real.
    assert simular(b, alvo, {"metodo": "M0d"}, "202812")["final"]["base"] == pytest.approx(10 * 1.1 ** 4.5)
    persistencia = simular(b, alvo, {"metodo": "M0"})
    assert persistencia["metodo"]["usado"] == "M0" and persistencia["metodo"]["provisorio"] is False
    assert [ponto["base"] for ponto in persistencia["trajetoria"]] == [10.0] * 4  # jan e jun de 2025 e de 2026
    assert [ponto["data"] for ponto in persistencia["trajetoria"]] == ["202501", "202506", "202601", "202606"]
    assert persistencia["texto"].startswith(FIXO + "com o método persistência (o último valor se mantém)")
    assert persistencia["faixa"]["estado"] == "indisponivel" and "só existe para o método padrão dos municípios" in persistencia["faixa"]["motivo"]


def test_zero_continua_zero_e_ausencia_nao_e_zero():
    b = base({"110001": [3] * 10 + [0] * 12, "110002": [50 * 1.05 ** a for a in ANOS], "110003": [7] * 21 + [None],
              "110004": [None] * T})
    zero = simular(b, municipio(b, "110001"), {"metodo": "padrao"})
    assert zero["final"]["total"] == 0 and "ZERO_CONTINUA_ZERO" in avisos(zero)
    assert zero["faixa"] == {"estado": "indisponivel", "motivo": "Com zero médicos na origem, não há faixa.", "rotulo": None}
    # Com uma intervenção, o território em zero passa a ter os médicos acrescentados (a base continua em zero).
    com = simular(b, municipio(b, "110001"), {"metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 3, "em": "202506"}]})
    assert (com["final"]["base"], com["final"]["intervencao"], com["final"]["total"]) == (0, 3, 3)
    assert "M110001 teria 3 médicos em jun/2026" in com["texto"]
    # O último registro ausente não é zero: a origem é o último registro usável, e o trecho até jun/2024 é retroprojeção.
    falta = simular(b, municipio(b, "110003"), {"metodo": "M0"})
    assert falta["parametros"]["origem"] == "202401" and falta["parametros"]["n0"] == 7 and "RETROPROJECAO" in avisos(falta)
    primeiro = falta["trajetoria"][0]
    assert (primeiro["data"], primeiro["retroprojecao"], primeiro["observado"]) == ("202406", True, None)
    assert all(not ponto["retroprojecao"] and "observado" not in ponto for ponto in falta["trajetoria"][1:])
    assert falta["texto"].endswith("Base: registros até jan/2024.")
    nada = simular(b, municipio(b, "110004"), {"metodo": "M0"})
    assert nada["estado"] == "nao_calculavel" and "ausência de dado não é zero" in nada["motivo"]


def test_quebra_de_fonte_na_janela_da_deriva_volta_a_persistencia():
    """A soma municipal da UF abaixo da contagem estadual até jun/2022 (como o Distrito Federal até jun/2017): a janela começa
    depois da quebra, e o método padrão volta ao M0, com os avisos."""
    b = base({"530010": [100] * 18 + [300] * 4, "110001": [12] * T}, estados={"53": [250] * T, "11": [1] * T})
    df = simular(b, municipio(b, "530010"), {"metodo": "padrao"})
    assert df["metodo"]["usado"] == "M0" and df["metodo"]["voltou_ao_m0"] is True and df["metodo"]["provisorio"] is True
    assert avisos(df) == ["JANELA_DEPOIS_DA_QUEBRA", "VOLTA_AO_M0", "HORIZONTE_CAUTELA"]
    assert df["parametros"]["janela"] == {"inicio": "202301", "fim": "202406", "registros": 4}
    assert df["final"]["total"] == 300 and "persistência (o último valor se mantém)" in df["texto"]
    assert next(a["texto"] for a in df["avisos"] if a["codigo"] == "VOLTA_AO_M0") == (
        "Sem o crescimento recente do estado (há quebra de fonte nos 3 anos usados para medir o crescimento do estado): o cenário usa a "
        "persistência (o último valor se mantém).")
    # Os outros métodos ajustam só nos registros depois da quebra (o salto de 100 para 300 não vira taxa).
    m1 = simular(b, municipio(b, "530010"), {"metodo": "M1"})
    assert m1["parametros"]["taxa_pct"] == 0 and m1["parametros"]["anos"] == pytest.approx(17 / 12) and m1["final"]["total"] == 300
    # O município de outra UF, sem quebra, tem a deriva.
    assert simular(b, municipio(b, "110001"), {"metodo": "padrao"})["metodo"]["usado"] == "M0d"


# --------------------------------------------------------------------------------------------- M1, M2, M3 e a taxa da pessoa
def test_taxa_composta_usa_o_tempo_real_e_recusa_o_inicio_em_zero():
    b = base({"110001": [100 * 1.1 ** a for a in ANOS], "110002": [0] * 10 + [5] * 12, "110003": [50] * T})
    alvo = municipio(b, "110001")
    m1 = simular(b, alvo, {"metodo": "M1"})
    assert m1["parametros"]["taxa_pct"] == pytest.approx(10.0) and m1["parametros"]["acumulado_pct"] == pytest.approx(33.1)
    assert m1["parametros"]["anos"] == 3.0 and m1["final"]["total"] == pytest.approx(121.0)
    assert "taxa de +10,00% ao ano; sem intervenção, M110001 teria 121 médicos em jun/2026" in m1["texto"]
    # De jan/2021 a jun/2024 são 41 meses (3 anos e 5 meses), não 3,5 anos: T é o tempo real.
    longa = simular(b, alvo, {"metodo": "M1"}, janela={"inicio": "202101", "fim": "202406"})
    assert longa["parametros"]["anos"] == pytest.approx(41 / 12) and longa["parametros"]["janela"]["registros"] == 8
    assert longa["parametros"]["taxa_pct"] == pytest.approx(10.0) and longa["parametros"]["acumulado_pct"] == pytest.approx(100 * (1.1 ** (41 / 12) - 1))
    # Com início em zero, a taxa não é definida: nem infinito, nem um ajuste que finge precisão.
    zero = simular(b, municipio(b, "110002"), {"metodo": "M1"}, janela={"inicio": "201806", "fim": "202406"})
    assert zero["estado"] == "nao_aplicavel" and "com início em zero, a taxa não é definida" in zero["motivo"]
    assert "texto" not in zero and "final" not in zero
    # Abaixo de 100 médicos, o aviso da retroprojeção.
    assert "M1_ABAIXO_DE_100" in avisos(simular(b, municipio(b, "110003"), {"metodo": "M1"}))
    assert "M1_ABAIXO_DE_100" not in avisos(m1)


def test_tendencia_linear_robusta_e_log_linear():
    reta = [50 + 4 * a for a in ANOS]
    com_um_valor_estranho = list(reta)
    com_um_valor_estranho[T - 6] = 1.0   # um registro muito abaixo: a mediana das inclinações não muda
    b = base({"110001": reta, "110002": com_um_valor_estranho, "110003": [6 - 4 * a for a in ANOS],
              "110004": [100 * 1.1 ** a for a in ANOS], "110005": [0] * T, "110006": [None] * 20 + [4, 5]})
    for codigo in ("110001", "110002"):
        m2 = simular(b, municipio(b, codigo), {"metodo": "M2"})
        assert m2["parametros"]["inclinacao_por_ano"] == pytest.approx(4.0) and m2["parametros"]["valor_na_origem"] == pytest.approx(50.0)
        assert m2["final"]["total"] == pytest.approx(58.0)
        assert "variação de +4 médicos por ano" in m2["texto"] and "com o método tendência linear robusta e as premissas" in m2["texto"]
        # A diferença entre a tendência ajustada e o último registro fica sempre à vista.
        assert next(a["texto"] for a in m2["avisos"] if a["codigo"] == "DIFERENCA_PARA_O_ULTIMO_REGISTRO") == (
            "A tendência ajustada dá 50 em jun/2024, e o registro é 50 (a mesma contagem): o cenário segue a tendência ajustada.")
    # A reta que desce passa de zero: a base para em zero, com o aviso (um número negativo não é estoque válido).
    desce = simular(b, municipio(b, "110003"), {"metodo": "M2"})
    assert desce["parametros"]["inclinacao_por_ano"] == pytest.approx(-4.0) and desce["final"]["total"] == 0
    assert "BASE_TRUNCADA_EM_ZERO" in avisos(desce) and "variação de −4 médicos por ano" in desce["texto"]
    assert [round(ponto["base"], 6) for ponto in desce["trajetoria"]] == [round(6 - 4 * 7 / 12, 6), 2.0, 0.0, 0.0]
    # A série exponencial exata: o ajuste de Poisson devolve a taxa dela; a dispersão é só diagnóstico.
    m3 = simular(b, municipio(b, "110004"), {"metodo": "M3"})
    assert m3["parametros"]["taxa_pct"] == pytest.approx(10.0) and m3["parametros"]["valor_na_origem"] == pytest.approx(100.0)
    assert m3["final"]["total"] == pytest.approx(121.0) and m3["parametros"]["dispersao"] == pytest.approx(0.0, abs=1e-9)
    # Série toda em zero: a log-linear não é calculável; a linear dá zero.
    assert simular(b, municipio(b, "110005"), {"metodo": "M3"})["estado"] == "nao_calculavel"
    assert simular(b, municipio(b, "110005"), {"metodo": "M2"})["final"]["total"] == 0
    # Dois registros na janela: M2 e M3 não se aplicam; a taxa composta, sim.
    for metodo in ("M2", "M3"):
        curto = simular(b, municipio(b, "110006"), {"metodo": metodo})
        assert curto["estado"] == "nao_aplicavel" and "pelo menos três registros" in curto["motivo"]
    assert simular(b, municipio(b, "110006"), {"metodo": "M1"})["parametros"]["anos"] == pytest.approx(5 / 12)


def test_ajustes_em_lote_theil_sen_e_poisson():
    t = np.array([-3.0, -2.0, -1.0, 0.0])
    a, b = simulador.theil_sen(t, np.array([[1.0, 3.0, 5.0, 7.0], [10.0, 10.0, 40.0, 10.0]]))
    assert a.tolist() == [7.0, 10.0] and b.tolist() == [2.0, 0.0]   # intercepto = mediana(y) − b · mediana(t)
    alfa, beta, dispersao, ok = simulador.poisson(t, np.array([[8.0, 4.0, 2.0, 1.0], [0.0, 0.0, 0.0, 0.0]]))
    assert ok.tolist() == [True, False] and np.exp(alfa[0]) == pytest.approx(1.0) and np.exp(beta[0]) == pytest.approx(0.5)
    assert dispersao[0] == pytest.approx(0.0, abs=1e-9) and np.isnan(dispersao[1])


def test_taxa_informada_pela_pessoa_e_hipotese_dela():
    b = base({"110001": [10] * T, "110002": [90] * T})
    manual = simular(b, municipio(b, "110001"), {"metodo": "manual", "taxa_manual_pct": -20})
    assert manual["metodo"]["usado"] == "manual" and manual["metodo"]["provisorio"] is False
    assert manual["final"]["total"] == pytest.approx(10 * 0.8 ** 2) and "TAXA_DA_PESSOA" in avisos(manual)
    assert "taxa de −20,00% ao ano informada pela pessoa" in manual["texto"]
    with pytest.raises(ValueError, match="O sistema não sugere uma taxa"):
        simulador._cenarios([{"metodo": "manual"}], b, set())
    with pytest.raises(ValueError, match="só vale com o método manual"):
        simulador._cenarios([{"metodo": "M1", "taxa_manual_pct": 3}], b, set())


# --------------------------------------------------------------------------------------------- intervenções
def test_intervencoes_somam_a_base_e_nao_crescem_com_ela():
    b = base({"110001": [10] * T, "110002": [90] * T})
    alvo = municipio(b, "110001")

    def com(intervencoes, horizonte="202606", **cenario):
        return simular(b, alvo, {"metodo": "M0", **cenario, "intervencoes": intervencoes}, horizonte)
    pontual = com([{"tipo": "acrescimo", "quantidade": 5, "em": "202501"}])
    assert (pontual["final"]["base"], pontual["final"]["intervencao"], pontual["final"]["total"]) == (10, 5, 15)
    assert "acréscimo de 5 médicos em jan/2025, com permanência total (hipótese), M110001 teria 15 médicos em jun/2026" in pontual["texto"]
    # A base cresce 10% ao ano (a taxa da pessoa); os 5 acrescentados, não: 10 × 1,1² + 5, e não (10 + 5) × 1,1².
    cresce = com([{"tipo": "acrescimo", "quantidade": 5, "em": "202501"}], metodo="manual", taxa_manual_pct=10)
    assert cresce["final"]["base"] == pytest.approx(12.1) and cresce["final"]["total"] == pytest.approx(17.1)
    # Um acréscimo anual acontece uma vez por ano: 2 médicos em jun/2025, jun/2026 e jun/2027.
    anual = com([{"tipo": "acrescimo", "quantidade": 2, "em": "202506", "ate": "202706", "a_cada_meses": 12}], "202806")
    assert [(ponto["data"], ponto["intervencao"]) for ponto in anual["trajetoria"]] == [
        ("202501", 0), ("202506", 2), ("202601", 2), ("202606", 4), ("202701", 4), ("202706", 6), ("202801", 6), ("202806", 6)]
    assert anual["final"]["total"] == 16
    assert "acréscimo de 2 médicos a cada 12 meses, de jun/2025 a jun/2027, com permanência total (hipótese)" in anual["texto"]
    # A permanência é uma hipótese: com 50% ao ano, dos 8 médicos de jun/2025 ficam 2 em jun/2027.
    meia = com([{"tipo": "acrescimo", "quantidade": 8, "em": "202506", "permanencia_pct_ao_ano": 50}], "202706")
    assert meia["final"]["intervencao"] == pytest.approx(2.0) and "com permanência de 50% ao ano (hipótese)" in meia["texto"]
    retirada = com([{"tipo": "retirada", "quantidade": 3, "em": "202501"}])
    assert retirada["final"]["total"] == 7 and "retirada de 3 médicos em jan/2025" in retirada["texto"]
    # A data da intervenção entra na trajetória, mesmo fora de janeiro e junho.
    marco = com([{"tipo": "acrescimo", "quantidade": 1, "em": "202503"}])
    assert [ponto["data"] for ponto in marco["trajetoria"]] == ["202501", "202503", "202506", "202601", "202606"]
    # Retirada acima do estoque: o cenário volta para revisão; o zero não esconde a intervenção impossível.
    demais = com([{"tipo": "retirada", "quantidade": 12, "em": "202501"}])
    assert demais["estado"] == "retirada_acima_do_estoque" and "final" not in demais and "texto" not in demais
    assert demais["motivo"] == ("Em jan/2025, as retiradas passam do número de médicos do cenário em 2: reveja a quantidade ou a data. "
                                "Nenhum estoque negativo é aceito.")
    # A intervenção até a origem já está nos registros.
    antes = com([{"tipo": "acrescimo", "quantidade": 1, "em": "202406"}])
    assert antes["estado"] == "nao_calculavel" and "ela já está nos registros" in antes["motivo"]


def test_intervencao_so_nos_territorios_indicados_e_validacoes():
    b = base({"110001": [10] * T, "110002": [90] * T})
    cal = detector.calibrar(b, guardar=False)
    retro = simulador.retroprojetar(b, guardar=False)
    ids = {"code:110001", "code:110002"}
    cenario = simulador._cenarios([{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501",
                                                                    "territorios": ["code:110002"]}]}], b, ids)[0]
    finais = [simulador._simular(b, cal, retro, municipio(b, codigo), cenario, 15, 21, series_brasil.mes_da_competencia("202606"))
              for codigo in ("110001", "110002")]
    assert [final["final"]["total"] for final in finais] == [10, 94]
    assert "sem intervenção" in finais[0]["texto"] and "acréscimo de 4 médicos em jan/2025" in finais[1]["texto"]
    # Com mais de um território no pedido, o texto diz para quem a intervenção vale: cada território recebe a quantidade inteira.
    geral = simulador._cenarios([{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]}], b, ids)[0]
    varios = [simulador._simular(b, cal, retro, municipio(b, codigo), geral, 15, 21, series_brasil.mes_da_competencia("202606"), True)
              for codigo in ("110001", "110002")]
    assert [final["final"]["total"] for final in varios] == [14, 94]
    assert all("acréscimo de 4 médicos em cada território do cenário, em jan/2025, com permanência total (hipótese)" in final["texto"]
               for final in varios)
    so_um = simulador._simular(b, cal, retro, municipio(b, "110002"), cenario, 15, 21, series_brasil.mes_da_competencia("202606"), True)
    assert "acréscimo de 4 médicos só nos territórios indicados, em jan/2025" in so_um["texto"]
    for intervencao, trecho in (
            ({"tipo": "doacao", "quantidade": 1, "em": "202501"}, "o tipo é acrescimo ou retirada"),
            ({"tipo": "acrescimo", "quantidade": 0, "em": "202501"}, "número acima de zero"),
            ({"tipo": "acrescimo", "quantidade": True, "em": "202501"}, "número acima de zero"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "2025"}, "use ano e mês"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202513"}, "use ano e mês"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "202401"}, "a data final vem antes da inicial"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "202701", "a_cada_meses": 0}, "de 1 a 120"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "permanencia_pct_ao_ano": 120}, "de 0 a 100"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "territorios": ["code:999999"]}, "precisam estar na seleção"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "209912", "a_cada_meses": 1}, "eventos demais")):
        with pytest.raises(ValueError, match=trecho):
            simulador._cenarios([{"metodo": "M0", "intervencoes": [intervencao]}], b, ids)
    with pytest.raises(ValueError, match="Método desconhecido"):
        simulador._cenarios([{"metodo": "media_aritmetica"}], b, ids)
    with pytest.raises(ValueError, match="até 6 cenários"):
        simulador._cenarios([{"id": "c" + str(k), "metodo": "M0"} for k in range(7)], b, ids)
    with pytest.raises(ValueError, match="mesmo id"):
        simulador._cenarios([{"id": "a", "metodo": "M0"}, {"id": "a", "metodo": "M1"}], b, ids)


# --------------------------------------------------------------------------------------------- conjuntos e estados
def test_conjuntos_somam_as_projecoes_dos_membros_e_estados_usam_a_serie_do_nivel():
    series = {"110001": [10] * T, "110002": [100 * 1.1 ** a - 10 for a in ANOS], "120001": [20] * T,
              "120002": [200 * 1.05 ** a - 20 for a in ANOS]}
    estados = {"11": [90 * 1.1 ** a for a in ANOS], "12": [100] * T}
    b = base(series, estados)
    assert not detector.calibrar(b, guardar=False).quebra.any()
    estado, par = series_brasil.selecao(b, {"estados_unidade": ["11"], "conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:110001", "code:120001"], "versao": 2}]})
    # M0d num conjunto de municípios: a soma das projeções dos membros, cada um com a deriva da sua UF (10% e 5% ao ano).
    soma = simular(b, par, {"metodo": "padrao"})
    assert soma["metodo"]["usado"] == "M0d" and soma["metodo"]["soma"] == "soma das projeções dos membros"
    assert soma["parametros"]["soma_das_projecoes"] is True and soma["parametros"]["derivas_pct"] == [5.0, 10.0]
    assert soma["final"]["total"] == pytest.approx(10 * 1.1 ** 2 + 20 * 1.05 ** 2)
    assert "o crescimento recente do estado de cada membro; sem intervenção, Par (soma das projeções dos membros) teria 34 médicos" in soma["texto"]
    # Nos outros métodos, o ajuste é na série da soma das contagens.
    m1 = simular(b, par, {"metodo": "M1"})
    assert m1["parametros"]["serie_da_soma"] is True and m1["parametros"]["n0"] == 30 and m1["final"]["total"] == pytest.approx(30)
    assert "Par (soma das contagens dos componentes) teria 30 médicos" in m1["texto"]
    # Estado como unidade: o padrão provisório é a taxa composta de 3 anos na série do próprio nível, com aviso; sem M0d e sem faixa.
    uf = simular(b, estado, {"metodo": "padrao"})
    assert uf["metodo"]["usado"] == "M1" and uf["metodo"]["provisorio"] is True and "PADRAO_PROVISORIO_DO_NIVEL" in avisos(uf)
    assert uf["parametros"]["n0"] == pytest.approx(90) and uf["final"]["total"] == pytest.approx(90 * 1.21)
    assert "Rondônia (RO) teria 109 médicos em jun/2026" in uf["texto"]
    assert uf["faixa"]["estado"] == "indisponivel"
    recusado = simular(b, estado, {"metodo": "M0d"})
    assert recusado["estado"] == "nao_aplicavel" and "vale para municípios e conjuntos de municípios" in recusado["motivo"]
    # Sem a deriva de uma UF (quebra de fonte nela), o membro dela fica na persistência, com o aviso.
    quebrada = base(series, {"11": [90 * 1.1 ** a for a in ANOS], "12": [300] * T})
    sem = simular(quebrada, series_brasil.selecao(quebrada, {"conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:110001", "code:120001"]}]})[0], {"metodo": "padrao"})
    assert "DERIVA_INDISPONIVEL" in avisos(sem) and sem["final"]["total"] == pytest.approx(10 * 1.1 ** 2 + 20)


# --------------------------------------------------------------------------------------------- estatísticas descritivas
def test_media_aritmetica_e_so_descritiva_e_nunca_alimenta_a_projecao():
    # Junho a junho: 100 → 150 → 100 → 150 → 100. As taxas são +50% e −33,3%; a média aritmética delas é +8,3%, e o crescimento
    # ocorrido em 4 anos é zero (a taxa composta).
    oscila = [100 if (k // 2) % 2 == 0 else 150 for k in range(T)]
    b = base({"110001": oscila, "110002": [10] * T})
    alvo = municipio(b, "110001")
    cal = detector.calibrar(b, guardar=False)
    inicio, fim, _ = simulador._janela(b, {"inicio": "202006", "fim": "202406"})
    indices, _ = simulador._usaveis(b, cal, alvo, inicio, fim)
    historico = simulador._estatisticas(b, alvo.serie, indices)
    assert [round(taxa["taxa_pct"], 2) for taxa in historico["taxas_de_junho"]] == [50.0, -33.33, 50.0, -33.33]
    assert historico["media_aritmetica_pct"] == pytest.approx(25 / 3) and historico["mediana_pct"] == pytest.approx(25 / 3)
    assert historico["taxa_composta_pct"] == pytest.approx(0.0, abs=1e-9) and historico["desvio_pct"] == pytest.approx(48.1125, abs=1e-3)
    assert historico["registros"] == 9 and historico["anos"] == 4.0 and "não é usada para projetar" in historico["nota"]
    # Nenhum método projeta com a média aritmética: em 2 anos, ela daria 100 × 1,0833² ≈ 117,4.
    com_a_media = 100 * (1 + 25 / 300) ** 2
    for metodo in ("padrao", "M0", "M0d", "M1", "M2", "M3"):
        resultado = simular(b, alvo, {"metodo": metodo}, janela={"inicio": "202006", "fim": "202406"})
        assert resultado["estado"] == "calculado" and abs(resultado["final"]["total"] - com_a_media) > 5, metodo
        assert "media_aritmetica_pct" not in resultado["parametros"]
    assert simular(b, alvo, {"metodo": "M1"}, janela={"inicio": "202006", "fim": "202406"})["final"]["total"] == pytest.approx(100.0)
    assert "media" not in simulador.METODOS and "media_aritmetica" not in simulador.NOMES_DOS_METODOS


def test_avisos_de_horizonte_frente_a_janela_do_metodo():
    b = base({"110001": [10] * T, "110002": [90] * T})
    alvo = municipio(b, "110001")
    esperado = {"202506": ("normal", None), "202606": ("cautela", "HORIZONTE_CAUTELA"), "202806": ("extrapolacao", "HORIZONTE_EXTRAPOLACAO"),
                "203106": ("extrapolacao_extrema", "HORIZONTE_EXTRAPOLACAO_EXTREMA")}
    for data, (nivel, codigo) in esperado.items():
        resultado = simular(b, alvo, {"metodo": "M0"}, data)
        assert resultado["horizonte"]["aviso"] == nivel and avisos(resultado) == ([codigo] if codigo else []), data
    # O aviso diz os dois tempos, em palavras simples.
    assert simular(b, alvo, {"metodo": "M0"}, "202806")["avisos"][0]["texto"] == (
        "Extrapolação além da janela: a data final fica mais longe do que o tempo de história usado no cálculo (4 anos à frente, com "
        "3 anos de história usados no cálculo).")
    assert simulador._tempo(1.0) == "1 ano" and simulador._tempo(29 / 12) == "2,4 anos"
    # A janela do próprio método conta: com 1 ano de janela, 2 anos de horizonte já são extrapolação.
    curta = simular(b, alvo, {"metodo": "M1"}, janela={"inicio": "202306", "fim": "202406"})
    assert curta["horizonte"] == {"anos": 2.0, "aviso": "extrapolacao"}
    # A data final até a origem não é cenário.
    with pytest.raises(ValueError, match="use ano e mês"):
        simulador._competencia_futura("2026-06", "Data final")
    assert simular(b, alvo, {"metodo": "M0"}, "202406")["estado"] == "nao_calculavel"


# --------------------------------------------------------------------------------------------- retroprojeção e faixas
def _base_das_faixas(depois=None):
    """60 municípios de uma UF, em 30 pares que somam 29 (a soma da UF fica constante: a deriva é zero, e o M0d é o último
    valor), com 10 a 19 médicos. `depois` troca os valores posteriores a uma competência (para a prova de que o ajuste não vê o
    futuro)."""
    sorteio = random.Random(20261110)
    series = {}
    for par in range(30):
        valor, caminho = sorteio.randint(12, 17), []
        for _ in range(T):
            valor = min(19, max(10, valor + sorteio.choice((-1, 0, 0, 1))))
            caminho.append(valor)
        series["11" + str(1000 + 2 * par)] = caminho
        series["11" + str(1001 + 2 * par)] = [29 - v for v in caminho]
    if depois:
        corte = PERIODOS.index(depois) + 1
        series = {codigo: valores[:corte] + [valores[k] + (3 if k % 2 else 0) for k in range(corte, T)] for codigo, valores in series.items()}
    return base(series)


def test_retroprojecao_com_origens_moveis_e_faixas_de_80():
    b = _base_das_faixas()
    retro = simulador.retroprojetar(b, guardar=False)
    assert retro.origens == ("201706", "201806", "201906", "202006", "202106", "202206", "202306")  # junhos com 3 anos de história
    q = b.quantidade
    for anos in (1, 2, 3, 4):
        origens = [k for k in range(T) if PERIODOS[k].endswith("06") and k >= 6 and k + 2 * anos <= T - 1]
        razoes = np.concatenate([q[:, k + 2 * anos] / q[:, k] - 1 for k in origens])  # a deriva é zero: o projetado é o último valor
        faixa = retro.faixas[(1, anos)]
        assert (faixa["casos"], faixa["origens"]) == (60 * len(origens), len(origens)) == (60 * (8 - anos), 8 - anos)
        assert (faixa["inferior"], faixa["superior"]) == pytest.approx(tuple(np.percentile(razoes, [10, 90])))
        assert faixa["inferior"] < 0 < faixa["superior"] and 0.6 < faixa["cobertura"] <= 1
    assert set(retro.faixas) == {(1, anos) for anos in (1, 2, 3, 4)}  # só o porte "10 a 19" tem casos
    linhas = {(linha["metodo"], linha["anos"]): linha for linha in retro.tabela if linha["porte"] == 1}
    assert {metodo for metodo, _ in linhas} == {"M0", "M0d", "M1", "M2", "M3"}
    for anos in (1, 2, 3, 4):
        assert linhas[("M0", anos)]["frente_ao_m0"] == pytest.approx(1.0) and linhas[("M0d", anos)]["frente_ao_m0"] == pytest.approx(1.0)
        assert linhas[("M0", anos)]["casos"] == 60 * (8 - anos) and linhas[("M0", anos)]["vies"] == pytest.approx(
            float(np.mean(np.concatenate([q[:, k + 2 * anos] - q[:, k] for k in range(T) if PERIODOS[k].endswith("06") and 6 <= k <= T - 1 - 2 * anos]))))
    # A faixa do cenário: a da base, deslocada pela intervenção; a data intermediária usa a do ano inteiro seguinte; depois de 4
    # anos, indisponível.
    alvo = municipio(b, "111000")
    n0 = float(q[b.indice["111000"], -1])
    cenario = simular(b, alvo, {"metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 5, "em": "202506"}]}, "202906")
    assert cenario["faixa"] == {"estado": "disponivel", "motivo": None, "porte": "10 a 19",
                                "rotulo": "a margem observada no passado da base, em municípios do mesmo porte; acompanha a intervenção"}
    pontos = {ponto["data"]: ponto for ponto in cenario["trajetoria"]}
    for data, anos, efeito in (("202501", 1, 0), ("202506", 1, 5), ("202601", 2, 5), ("202606", 2, 5), ("202706", 3, 5), ("202806", 4, 5)):
        limites = retro.faixas[(1, anos)]
        assert pontos[data]["faixa"] == {"inferior": pytest.approx(n0 * (1 + limites["inferior"]) + efeito),
                                         "superior": pytest.approx(n0 * (1 + limites["superior"]) + efeito), "anos": anos,
                                         "validada": anos <= 2}, data
    assert pontos["202901"]["faixa"] is None and cenario["final"]["faixa"] is None and "FAIXA_ATE_4_ANOS" in avisos(cenario)
    # Só o M0d municipal tem faixa: os outros métodos, não.
    for metodo in ("M0", "M1", "M2", "M3"):
        outro = simular(b, alvo, {"metodo": metodo})
        assert outro["faixa"]["estado"] == "indisponivel" and all(ponto["faixa"] is None for ponto in outro["trajetoria"]), metodo
    # Num conjunto de municípios, a faixa é uma aproximação, rotulada (o porte é o da soma: 29, de 20 a 49, sem casos nesta base).
    par = series_brasil.selecao(b, {"conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:111000", "code:111001"]}]})[0]
    assert simular(b, par, {"metodo": "padrao"})["faixa"]["motivo"] == "A base não tem retroprojeções bastantes para a faixa deste porte."


def test_o_ajuste_nao_usa_observacoes_posteriores_a_janela():
    """A mesma janela (até jun/2019) em duas bases que só diferem depois dela: os parâmetros e a base do cenário são os mesmos."""
    a, depois = _base_das_faixas(), _base_das_faixas(depois="201906")
    assert (a.quantidade[:, :12] == depois.quantidade[:, :12]).all() and (a.quantidade[:, 12:] != depois.quantidade[:, 12:]).any()
    janela = {"inicio": "201606", "fim": "201906"}
    for metodo in ("M0", "M0d", "M1", "M2", "M3"):
        um = simular(a, municipio(a, "111000"), {"metodo": metodo}, "202106", janela)
        outro = simular(depois, municipio(depois, "111000"), {"metodo": metodo}, "202106", janela)
        assert um["estado"] == outro["estado"] == "calculado" and um["parametros"] == outro["parametros"], metodo
        assert [ponto["base"] for ponto in um["trajetoria"]] == [ponto["base"] for ponto in outro["trajetoria"]], metodo
        # Com a origem antes do último registro, o trecho com registros é retroprojeção, ao lado do observado (que difere).
        assert um["trajetoria"][0]["retroprojecao"] is True and "RETROPROJECAO" in avisos(um)
        assert [ponto["data"] for ponto in um["trajetoria"]] == ["202001", "202006", "202101", "202106"]
    assert um["trajetoria"][0]["observado"] == float(a.quantidade[a.indice["111000"], 12])


# --------------------------------------------------------------------------------------------- rota
UNIDADES = {"130260": ("MANAUS", "AM", [30 + k for k in range(T)]), "130420": ("TEFE", "AM", [3] * 10 + [0] * 12),
            "130340": ("PARINTINS", "AM", [20] * 12 + [12] * 10), "150140": ("BELEM", "PA", [50] * T)}
POPULACOES = {"130260": 2000, "130420": 1000, "130340": 1000, "150140": 4000}


@pytest.fixture
def catalogo(tmp_path, monkeypatch):
    """Catálogo sintético (4 municípios, 22 competências) instalado como versão governada. A contagem nacional cresce 10 médicos
    por registro (de 900 a 1.110), e as populações são diferentes (POPULACOES), para a comparação por taxa."""
    raiz = tmp_path / "repositorio"
    raiz.mkdir()
    livro = Workbook()
    livro.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for k, periodo in enumerate(PERIODOS):
        livro.active.append(["Brasil", int(periodo[:4]), int(periodo[4:]), "MEDICINA", 900 + 10 * k])
    livro.save(raiz / FILES["national"])
    linhas = ["regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
              "quantidade;população_estimada"]
    for k, periodo in enumerate(PERIODOS):
        for codigo, (nome, uf, valores) in UNIDADES.items():
            if codigo == "130340" and periodo == "201501":
                continue  # um registro ausente
            linhas.append(";".join(["NORTE", uf, nome, codigo, "-3", "-60", "MEDICINA", periodo[:4], str(int(periodo[4:])),
                                    str(valores[k]), str(POPULACOES[codigo])]))
    (raiz / FILES["municipal"]).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    write_state_source(raiz, {(uf, periodo): contagem for periodo in PERIODOS for uf, contagem in (("AM", 40), ("PA", 45))})
    (raiz / GOVERNED_MANIFEST).parent.mkdir(parents=True, exist_ok=True)
    (raiz / GOVERNED_MANIFEST).write_text(json.dumps(manifest_from_repository(raiz)), encoding="utf-8")
    monkeypatch.setattr(brazil_data, "REPO_ROOT", raiz)
    monkeypatch.delenv("ADT_BRASIL_DATA_DIR", raising=False)
    monkeypatch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
    main._BRAZIL_FRAMES.clear()
    antes = {nome: hashlib.sha256((raiz / nome).read_bytes()).hexdigest() for nome in FILES.values()}
    yield raiz
    assert antes == {nome: hashlib.sha256((raiz / nome).read_bytes()).hexdigest() for nome in FILES.values()}
    main._BRAZIL_FRAMES.clear()


def pedir(opcoes, **dados):
    return client.post("/api/simulador", data={"dataset": "brazil", "scope": "municipal", "options": json.dumps(opcoes), **dados})


def corpo(resposta):
    assert resposta.status_code == 200, resposta.text[:2000]
    body = resposta.json()
    json.dumps(body, allow_nan=False)
    return body


def recusa(resposta, trecho):
    assert resposta.status_code == 422, resposta.text[:500]
    assert trecho in resposta.json()["detail"], resposta.json()["detail"]


def test_rota_do_simulador_cenarios_estatisticas_e_recusas(catalogo, monkeypatch):
    monkeypatch.setattr(main, "llm_interpret", lambda *a, **k: (_ for _ in ()).throw(AssertionError("o Simulador não usa o provedor de IA")))
    selecao = {"base": {"municipios": {"ids": ["code:130260", "code:130420"]}}, "estados_unidade": ["15"],
               "conjuntos": [{"id": "g1", "rotulo": "Par", "membros": ["code:130260", "code:130340"], "versao": 2}]}
    body = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [
        {"id": "c1", "nome": "Com 4 médicos", "metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]},
        {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}]}))
    assert body["versao"] == simulador.VERSION and body["fonte"]["categoria"] == "MEDICINA"
    assert (body["fonte"]["primeira"], body["fonte"]["ultima"], body["ultimo_registro"]) == ("201401", "202406", "202406")
    assert body["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7, "anos": 3.0, "padrao": True}
    assert body["horizonte"] == {"data": "202606", "anos_desde_o_ultimo_registro": 2.0}
    assert body["competencias"] == list(PERIODOS) and body["limitacoes"] == ["CENARIO_HIPOTETICO", "PADRAO_PROVISORIO", "FAIXA_SO_DO_METODO_PADRAO"]
    territorios = {item["id"]: item for item in body["territorios"]}
    assert list(territorios) == ["code:130260", "code:130420", "uf:15", "g1"]
    manaus = territorios["code:130260"]
    assert (manaus["rotulo"], manaus["tipo"], manaus["uf"], len(manaus["observado"])) == ("MANAUS (AM)", "municipio", "AM", 22)
    assert manaus["observado"][-1] == {"competencia": "202406", "valor": 51.0, "estado": "observado"}
    # A deriva do Amazonas: a soma municipal passa de 57 (jun/2021) para 63 (jun/2024).
    deriva = (63 / 57) ** (1 / 3) - 1
    com, referencia = manaus["cenarios"]
    assert (com["id"], com["nome"], com["estado"], com["metodo"]["usado"], com["metodo"]["provisorio"]) == ("c1", "Com 4 médicos", "calculado", "M0d", True)
    assert com["parametros"]["deriva_pct"] == pytest.approx(100 * deriva) and com["parametros"]["estado_da_deriva"] == "Amazonas"
    assert com["final"] == {"data": "202606", "base": pytest.approx(51 * (1 + deriva) ** 2), "intervencao": 4.0,
                            "total": pytest.approx(51 * (1 + deriva) ** 2 + 4), "faixa": None}
    assert com["texto"].startswith(FIXO) and com["texto"].endswith("MANAUS (AM) teria 59 médicos em jun/2026. Base: registros até jun/2024.")
    assert "acréscimo de 4 médicos em cada território do cenário, em jan/2025, com permanência total (hipótese)" in com["texto"]
    assert any("Cada intervenção vale para cada território do cenário" in nota for nota in body["notas"])
    assert com["faixa"]["estado"] == "indisponivel"   # o catálogo de teste não tem retroprojeções bastantes
    assert (referencia["id"], referencia["metodo"]["usado"], referencia["final"]["total"]) == ("m0", "M0", 51.0)
    assert manaus["historico"]["taxa_composta_pct"] == pytest.approx(100 * ((51 / 45) ** (1 / 3) - 1))
    assert [taxa["ate"] for taxa in manaus["historico"]["taxas_de_junho"]] == ["202206", "202306", "202406"]
    assert manaus["historico"]["media_aritmetica_pct"] == pytest.approx(100 * np.mean([47 / 45 - 1, 49 / 47 - 1, 51 / 49 - 1]))
    # Tefé está em zero: continua em zero sem intervenção; com os 4 médicos do cenário, tem 4.
    tefe = territorios["code:130420"]
    assert tefe["observado"][-1]["estado"] == "zero_confirmado"
    assert [cenario["final"]["total"] for cenario in tefe["cenarios"]] == [4.0, 0.0]
    # O estado como unidade (contagem estadual de médicos únicos) e o conjunto (soma dos componentes), rotulados.
    para = territorios["uf:15"]
    assert (para["rotulo"], para["tipo"], para["unidade"]) == ("Pará (PA)", "estado", series_brasil.UNIDADE_ESTADO)
    assert para["cenarios"][0]["metodo"]["usado"] == "M1" and para["cenarios"][0]["final"]["total"] == pytest.approx(49.0)
    par = territorios["g1"]
    assert (par["tipo"], par["membros"], par["nomes_dos_membros"], par["versao"]) == (
        "conjunto", ["code:130260", "code:130340"], ["MANAUS (AM)", "PARINTINS (AM)"], 2)
    assert par["cenarios"][0]["final"]["total"] == pytest.approx((51 + 12) * (1 + deriva) ** 2 + 4)
    assert "Par (soma das projeções dos membros) teria" in par["cenarios"][0]["texto"]
    assert any("soma dos componentes" in nota for nota in body["notas"]) and any("não são previsão" in nota for nota in body["notas"])
    assert body["retroprojecao"]["origens"] == ["201706", "201806", "201906", "202006", "202106", "202206", "202306"]
    # Sem cenários no pedido: um cenário sem intervenção, no método padrão, 2 anos depois do último registro.
    simples = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}}))
    assert simples["horizonte"]["data"] == "202606" and [c["nome"] for c in simples["territorios"][0]["cenarios"]] == ["Sem intervenção"]
    # A janela escolhida entre as competências reais; o registro ausente é lacuna, não zero.
    janela = corpo(pedir({"base": {"municipios": {"ids": ["code:130340"]}}, "janela": {"inicio": "201406", "fim": "201606"},
                          "horizonte": "201806", "cenarios": [{"metodo": "M1"}]}))
    parintins = janela["territorios"][0]
    assert janela["janela"] == {"inicio": "201406", "fim": "201606", "registros": 5, "anos": 2.0, "padrao": False}
    assert parintins["lacunas"] == ["201501"] and parintins["historico"]["registros"] == 4
    cenario = parintins["cenarios"][0]
    assert cenario["final"]["total"] == 20.0 and "RETROPROJECAO" in [aviso["codigo"] for aviso in cenario["avisos"]]
    assert [(ponto["data"], ponto["retroprojecao"], ponto["observado"]) for ponto in cenario["trajetoria"]] == [
        ("201701", True, 20.0), ("201706", True, 20.0), ("201801", True, 20.0), ("201806", True, 20.0)]
    # Recusas, em português.
    recusa(pedir({}), "Nenhum território na seleção")
    recusa(pedir({"base": {"municipios": {"ids": ["code:999999"]}}}), "Território fora da base Brasil")
    recusa(pedir({**selecao, "outra": 1}), "Opção desconhecida")
    recusa(pedir({**selecao, "horizonte": "202406"}), "A data final precisa ser depois do fim da janela")
    recusa(pedir({**selecao, "horizonte": "2026"}), "Data final inválida")
    recusa(pedir({**selecao, "janela": {"inicio": "202406", "fim": "201401"}}), "com o início antes do fim")
    recusa(pedir({**selecao, "janela": {"fim": "202407"}}), "Competência fora da base")
    recusa(pedir({**selecao, "cenarios": [{"metodo": "previsao"}]}), "Método desconhecido")
    recusa(pedir({**selecao, "cenarios": [{"metodo": "manual"}]}), "O sistema não sugere uma taxa")
    recusa(pedir({**selecao, "cenarios": [{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": -1, "em": "202501"}]}]}),
           "número acima de zero")
    recusa(pedir({**selecao, "cenarios": [{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 1, "em": "202501",
                                                                             "territorios": ["code:150140"]}]}]}), "precisam estar na seleção")
    recusa(pedir({"base": {"municipios": {"ids": ["code:150140"]}}, "estados_unidade": ["15"]}), "junto com o estado inteiro")
    recusa(client.post("/api/simulador", data={"dataset": "", "options": "{}"}), "usam a base do Brasil")
    recusa(client.post("/api/simulador", data={"options": "{}"}, files={"file": ("p.csv", b"a;b\n1;2\n", "text/csv")}),
           "usam a base do Brasil")


# --------------------------------------------------------------------------------------------- etapa 5: Brasil, referências e planejamento inverso
def _comparacao(body, territorio, referencia, cenario=0):
    item = next(item for item in body["territorios"] if item["id"] == territorio)
    return next(c for c in item["cenarios"][cenario]["comparacoes"] if c["id"] == referencia)


def test_rota_o_brasil_e_territorio_so_do_simulador_com_o_padrao_provisorio(catalogo):
    body = corpo(pedir({"brasil": True, "horizonte": "202606"}))
    [brasil] = body["territorios"]
    assert (brasil["id"], brasil["tipo"], brasil["nivel"], brasil["rotulo"], brasil["uf"], brasil["unidade"]) == (
        "br", "brasil", "brasil", "Brasil", None, series_brasil.UNIDADE_BRASIL)
    cenario = brasil["cenarios"][0]
    taxa = (1110 / 1050) ** (1 / 3) - 1   # a contagem nacional vai de 1.050 (jun/2021) a 1.110 (jun/2024)
    assert cenario["metodo"] == {"pedido": "padrao", "usado": "M1", "rotulo": "taxa composta da janela", "padrao": True, "provisorio": True,
                                 "voltou_ao_m0": False, "soma": None}
    assert cenario["parametros"]["n0"] == 1110 and cenario["parametros"]["taxa_pct"] == pytest.approx(100 * taxa)
    assert cenario["final"]["total"] == pytest.approx(1110 * (1 + taxa) ** 2) and cenario["final"]["faixa"] is None
    assert cenario["faixa"]["estado"] == "indisponivel"
    provisorio = next(aviso["texto"] for aviso in cenario["avisos"] if aviso["codigo"] == "PADRAO_PROVISORIO_DO_NIVEL")
    assert provisorio.startswith("Para o Brasil, o método padrão é provisório") and "na contagem nacional" in provisorio
    assert cenario["texto"].startswith(FIXO) and "sem intervenção, Brasil teria 1.152 médicos em jun/2026." in cenario["texto"]
    assert "hipotetico" not in cenario   # a escala estrutural é só dos municípios
    assert any("o Brasil, a contagem nacional" in nota for nota in body["notas"])
    # O Brasil entra por último, ao lado dos demais territórios: cada um é simulado à parte, e ele nunca é somado a eles.
    juntos = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "estados_unidade": ["15"], "brasil": True}))
    assert [item["id"] for item in juntos["territorios"]] == ["code:130260", "uf:15", "br"]
    # Sem "brasil": true, nada muda; e o Detector de Sinais não tem o Brasil como unidade.
    assert [item["id"] for item in corpo(pedir({"estados_unidade": ["15"], "brasil": False}))["territorios"]] == ["uf:15"]
    with pytest.raises(ValueError, match="Opção desconhecida no pedido do Detector: brasil"):
        detector.compute(main._brazil_sources(""), {"brasil": True})


def test_rota_referencias_fixas_dinamicas_e_valor_com_alcance_e_sobreposicao(catalogo):
    selecao = {"base": {"municipios": {"ids": ["code:130260", "code:130340"]}}, "estados_unidade": ["15"],
               "conjuntos": [{"id": "g1", "rotulo": "Par", "membros": ["code:130260", "code:130340"], "versao": 2}]}
    com_reforco = {"id": "c1", "metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 5, "em": "202501", "ate": "202601",
                                                                 "a_cada_meses": 12}]}
    body = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [com_reforco], "referencias": [
        {"id": "fixa", "territorio": "code:150140"}, {"id": "din", "territorio": "code:130260", "tipo": "dinamica"},
        {"id": "val", "tipo": "valor", "valor": 20, "rotulo": "Meta local"}, {"id": "uf", "territorio": "uf:13"},
        {"id": "br", "territorio": "br", "tipo": "dinamica"}]}))
    assert body["comparacao"] == {"metrica": "quantidade", "hipotese_de_populacao": None}
    assert [(ref["id"], ref["rotulo"], ref["tipo"], ref["territorio"], ref["estado"], ref["descricao"]) for ref in body["referencias"]] == [
        ("fixa", "BELEM (PA)", "fixa", "code:150140", "calculada", "fixa: o valor de jun/2024 mantido"),
        ("din", "MANAUS (AM)", "dinamica", "code:130260", "calculada",
         "dinâmica: persistência com o crescimento recente do estado, com registros até jun/2024"),
        ("val", "Meta local", "valor", None, "calculada", "valor informado por você, mantido"),
        ("uf", "Amazonas (AM)", "fixa", "uf:13", "calculada", "fixa: o valor de jun/2024 mantido"),
        ("br", "Brasil", "dinamica", "br", "calculada", "dinâmica: taxa composta da janela, com registros até jun/2024")]
    assert body["referencias"][3]["unidade"] == series_brasil.UNIDADE_ESTADO and body["referencias"][2]["unidade"] is None
    # Parintins (12, com +5 em jan/2025 e +5 em jan/2026) diante do valor informado (20): alcança na primeira data avaliada em
    # que o cenário fica no nível da referência.
    alcanca = _comparacao(body, "code:130340", "val")
    assert alcanca["alcance"] == {"estado": "alcanca", "data": "202601"}
    assert [(p["data"], p["territorio"], p["referencia"], p["diferenca"]) for p in alcanca["pontos"]] == [
        ("202406", 12.0, 20.0, 8.0), ("202501", 17.0, 20.0, 3.0), ("202506", 17.0, 20.0, 3.0), ("202601", 22.0, 20.0, -2.0),
        ("202606", 22.0, 20.0, -2.0)]
    assert alcanca["final"]["razao"] == pytest.approx(1.1) and alcanca["final"]["indice"] == pytest.approx(110.0)
    assert alcanca["texto"] == ("Em jun/2026, PARINTINS (AM) teria 22 médicos, e a referência Meta local (valor informado por você, mantido), "
                                "20: 2 acima da referência (índice 110; 100 é a referência). No cenário, alcança a referência em jan/2026, a "
                                "primeira data avaliada em que isso ocorre.")
    # Diante de Belém fixa (50): sem cruzamento no horizonte, nenhuma data é inventada.
    nao = _comparacao(body, "code:130340", "fixa")
    assert nao["alcance"] == {"estado": "nao_alcanca", "data": None} and nao["metodo"] == "M0" and nao["avisos"] == []
    assert nao["texto"].endswith("50: 28 abaixo da referência (índice 44; 100 é a referência). Não alcança no horizonte simulado (até jun/2026).")
    # A referência dinâmica segue o método dela (a persistência com o crescimento recente do estado), sem intervenções; na origem,
    # vale o registro.
    deriva = (63 / 57) ** (1 / 3) - 1
    dinamica = _comparacao(body, "code:130340", "din")
    assert dinamica["metodo"] == "M0d" and dinamica["pontos"][0]["referencia"] == 51.0
    assert dinamica["final"]["referencia"] == pytest.approx(51 * (1 + deriva) ** 2)
    assert "MANAUS (AM) (dinâmica: persistência com o crescimento recente do estado, com registros até jun/2024), 54,5: 32,5 abaixo" in dinamica["texto"]
    # Na origem, o território já está no nível da referência ou acima dele.
    acima = _comparacao(body, "code:130260", "fixa")
    assert acima["alcance"] == {"estado": "ja_acima", "data": None} and acima["inicial"]["diferenca"] == -1.0
    assert acima["texto"].endswith("Na origem, o território já está no nível da referência ou acima dele.")
    # Sobreposição e unidades: nunca se declara uma independência que não há.
    assert _comparacao(body, "code:130260", "din")["avisos"] == ["A referência é o próprio território."]
    contem, unidades = _comparacao(body, "code:130260", "uf")["avisos"]
    assert contem == "A referência contém o território (o estado inclui o município): a comparação não é independente."
    assert unidades == ("As contagens têm unidades diferentes: no território, " + series_brasil.UNIDADE_MUNICIPIO + "; na referência, " +
                        series_brasil.UNIDADE_ESTADO + ". A comparação é entre esses quantitativos.")
    do_brasil = _comparacao(body, "code:130260", "br")["avisos"]
    assert do_brasil[0] == "A referência (Brasil) contém o território: a comparação não é independente."
    assert do_brasil[-1].startswith("Para o Brasil, o método padrão é provisório")   # o aviso do método da referência dinâmica
    assert _comparacao(body, "uf:15", "fixa")["avisos"][0] == "O território contém a referência: a comparação não é independente."
    assert _comparacao(body, "g1", "din")["avisos"][0] == "O território e a referência têm 1 município em comum: a comparação não é independente."
    assert any(nota.startswith("Referências: a comparação mostra a diferença, a razão e o índice") and "nenhuma data é inventada" in nota
               and "não é comparar a suficiência do atendimento" in nota for nota in body["notas"])
    # Um conjunto da seleção local também serve de referência; diante de si mesmo, o valor é o mesmo.
    conjunto = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [{"id": "c1", "metodo": "M0"}],
                            "referencias": [{"id": "g", "territorio": "g1"}]}))
    assert _comparacao(conjunto, "code:130260", "g")["avisos"][0] == (
        "O território e a referência têm 1 município em comum: a comparação não é independente.")
    assert _comparacao(conjunto, "code:130260", "g")["final"]["referencia"] == 63.0
    proprio = _comparacao(conjunto, "g1", "g")
    assert proprio["avisos"] == ["A referência é o próprio território."] and ": o mesmo valor (índice 100; 100 é a referência)." in proprio["texto"]
    # Sem referências no pedido, os cenários não têm comparações.
    sem = corpo(pedir({**selecao, "horizonte": "202606"}))
    assert sem["referencias"] == [] and "comparacoes" not in sem["territorios"][0]["cenarios"][0]
    assert not any(nota.startswith("Referências:") for nota in sem["notas"])


def test_rota_comparacao_por_taxa_declara_a_populacao_constante(catalogo):
    # Populações do catálogo: Manaus 2.000, Parintins 1.000, Belém 4.000 (o Pará soma 4.000; o Brasil, 8.000).
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:130260", "code:130340"]}}, "estados_unidade": ["15"], "horizonte": "202606",
                        "cenarios": [{"id": "c1", "metodo": "M0"}], "comparacao": {"metrica": "taxa"},
                        "referencias": [{"id": "fixa", "territorio": "code:150140"}, {"id": "val", "tipo": "valor", "valor": 20},
                                        {"id": "br", "territorio": "br"}]}))
    assert body["comparacao"] == {"metrica": "taxa", "hipotese_de_populacao": "constante: a população de jun/2024 em todas as datas simuladas"}
    manaus = _comparacao(body, "code:130260", "fixa")
    assert (manaus["metrica"], manaus["final"]["territorio"], manaus["final"]["referencia"]) == ("taxa", 25.5, 12.5)
    assert manaus["texto"] == ("Em jun/2026, MANAUS (AM) teria 25,50 médicos por 1.000 habitantes, e a referência BELEM (PA) (fixa: o valor de "
                               "jun/2024 mantido), 12,50: 13 acima da referência (índice 204; 100 é a referência). Na origem, o território já "
                               "está no nível da referência ou acima dele. Hipótese: população constante, a de jun/2024.")
    # O valor informado já está na métrica escolhida (uma taxa); o estado e o Brasil usam a soma das populações municipais.
    assert _comparacao(body, "code:130340", "val")["final"] == {"data": "202606", "territorio": 12.0, "referencia": 20.0, "diferenca": 8.0,
                                                                 "razao": pytest.approx(0.6), "indice": pytest.approx(60.0)}
    assert _comparacao(body, "uf:15", "fixa")["final"]["territorio"] == pytest.approx(45 / 4000 * 1000)
    assert _comparacao(body, "code:130260", "br")["final"]["referencia"] == pytest.approx(1110 / 8000 * 1000)
    assert any("por taxa, vale a hipótese de população constante" in nota for nota in body["notas"])


def test_rota_planejamento_inverso_e_o_menor_inteiro_que_alcanca_a_meta(catalogo):
    parintins = {"base": {"municipios": {"ids": ["code:130340"]}}, "horizonte": "202606"}   # 12 médicos, mantidos (M0)

    def plano(planejamento, extra=None, selecao=parintins, referencias=None):
        body = corpo(pedir({**selecao, "cenarios": [{"id": "c1", "metodo": "M0", **(extra or {}), "planejamento": planejamento}],
                            **({"referencias": referencias} if referencias else {})}))
        return body, {item["id"]: item["cenarios"][0] for item in body["territorios"]}

    body, cenarios = plano({"meta": {"tipo": "valor", "valor": 20}, "em": "202506"})
    cenario = cenarios["code:130340"]
    um = cenario["planejamento"]
    assert (um["estado"], um["eventos"], um["datas"], um["por_evento"], um["total"], um["teorico_por_evento"], um["resultado"]) == (
        "calculado", 1, ["202506"], 8, 8, 8.0, 20.0)
    assert um["meta"] == {"tipo": "valor", "valor": 20.0, "rotulo": "Meta hipotética: 20 médicos em jun/2026"}
    assert (um["base_na_data_final"], um["outras_intervencoes"], um["sem_o_plano"], um["falta"]) == (12.0, 0.0, 12.0, 8.0)
    assert um["intervencao"] == {"tipo": "acrescimo", "quantidade": 8, "em": "202506", "permanencia_pct_ao_ano": 100.0}
    assert um["texto"] == (
        "Meta hipotética: 20 médicos em jun/2026. Menor acréscimo inteiro que alcança a meta, nas hipóteses deste cenário: 8 médicos em "
        "jun/2025. Pela conta sem arredondar, seriam 8 por evento. " + FIXO + "com o método persistência (o último valor se mantém) e as "
        "premissas janela de jun/2021 a jun/2024; acréscimo de 8 médicos neste território, pelo planejamento inverso, em jun/2025, com "
        "permanência total (hipótese), PARINTINS (AM) teria 20 médicos em jun/2026. Base: registros até jun/2024. É uma conta condicional "
        "às hipóteses do cenário, não um plano.")
    for proibida in ("recomenda", "é preciso", "deveria", "necessário prover"):   # decisão D-B: nenhuma palavra de recomendação
        assert proibida not in um["texto"].lower()
    # O cenário continua sendo o do pedido: o acréscimo planejado só entra nele por comando da pessoa.
    assert cenario["final"]["total"] == 12.0 and "sem intervenção, PARINTINS (AM) teria 12 médicos" in cenario["texto"]
    assert any(nota.startswith("Planejamento inverso: o menor número inteiro de médicos por evento") for nota in body["notas"])
    # A base entra sem arredondar: para 20,5, a conta dá 8,5, e o inteiro que alcança é 9.
    meio = plano({"meta": {"tipo": "valor", "valor": 20.5}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert (meio["teorico_por_evento"], meio["por_evento"], meio["resultado"]) == (8.5, 9, 21.0)
    assert "9 médicos em jun/2025. Pela conta sem arredondar, seriam 8,50 por evento." in meio["texto"]
    # Eventos iguais num calendário: x = ⌈(meta − N(T)) ÷ k⌉. Com 2 eventos e meta de 21, 4,5 vira 5 por evento (10 no total).
    dois = plano({"meta": {"tipo": "valor", "valor": 21}, "em": "202501", "ate": "202601", "a_cada_meses": 12})[1]["code:130340"]["planejamento"]
    assert (dois["eventos"], dois["datas"], dois["teorico_por_evento"], dois["por_evento"], dois["total"], dois["resultado"]) == (
        2, ["202501", "202601"], 4.5, 5, 10, 22.0)
    assert dois["intervencao"] == {"tipo": "acrescimo", "quantidade": 5, "em": "202501", "ate": "202601", "a_cada_meses": 12,
                                   "permanencia_pct_ao_ano": 100.0}
    assert "5 médicos em cada um dos 2 eventos, de jan/2025 a jan/2026 (10 no total)" in dois["texto"]
    # Reaplicado ao Simulador como intervenção, o inteiro alcança a meta; com um a menos, não (seção 14.1 do anexo).
    reaplicado = corpo(pedir({**parintins, "cenarios": [{"id": "a", "metodo": "M0", "intervencoes": [dois["intervencao"]]},
                                                        {"id": "b", "metodo": "M0", "intervencoes": [{**dois["intervencao"], "quantidade": 4}]}]}))
    com, sem = (c["final"]["total"] for c in reaplicado["territorios"][0]["cenarios"])
    assert com == dois["resultado"] == 22.0 and com >= 21 > sem == 20.0
    # Com permanência menor, cada médico acrescentado vale menos na data final: 50% ao ano, um ano antes, dobra a conta.
    metade = plano({"meta": {"tipo": "valor", "valor": 20}, "em": "202506", "permanencia_pct_ao_ano": 50})[1]["code:130340"]["planejamento"]
    assert (metade["por_evento"], metade["teorico_por_evento"], metade["resultado"]) == (16, pytest.approx(16.0), pytest.approx(20.0))
    zero = plano({"meta": {"tipo": "valor", "valor": 20}, "em": "202506", "permanencia_pct_ao_ano": 0})[1]["code:130340"]["planejamento"]
    assert zero["estado"] == "nao_alcancavel" and zero["motivo"].startswith("Com permanência zero") and "por_evento" not in zero
    # As outras intervenções do cenário contam antes: com +3 em jan/2025, faltam 5.
    outras = plano({"meta": {"tipo": "valor", "valor": 20}, "em": "202506"},
                   extra={"intervencoes": [{"tipo": "acrescimo", "quantidade": 3, "em": "202501"}]})[1]["code:130340"]["planejamento"]
    assert (outras["outras_intervencoes"], outras["sem_o_plano"], outras["por_evento"], outras["resultado"]) == (3.0, 15.0, 5, 20.0)
    # Meta já alcançada, e calendário sem evento até a data final.
    ja = plano({"meta": {"tipo": "valor", "valor": 10}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert (ja["estado"], ja["por_evento"], ja["total"], ja["intervencao"]) == ("ja_alcancada", 0, 0, None)
    assert ja["texto"] == ("Meta hipotética: 10 médicos em jun/2026. No cenário, o território já teria 12 médicos em jun/2026: a meta é "
                           "alcançada sem acréscimo.")
    tarde = plano({"meta": {"tipo": "valor", "valor": 20}, "em": "202701"})[1]["code:130340"]["planejamento"]
    assert (tarde["estado"], tarde["eventos"], tarde["motivo"]) == (
        "nao_calculavel", 0, "Nenhum evento do calendário cai depois da origem do cenário e até a data final.")
    # "Simular recuperação" (decisão D-B): a meta hipotética de voltar ao patamar anterior. Sem valor, o patamar é o do
    # território (Parintins teve 20 médicos); com valor, o que a pessoa informou.
    patamar = plano({"meta": {"tipo": "patamar"}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert patamar["meta"] == {"tipo": "patamar", "valor": 20.0, "rotulo": "Meta hipotética: voltar ao patamar de 20 médicos em jun/2026"}
    assert patamar["por_evento"] == 8 and patamar["texto"].startswith("Meta hipotética: voltar ao patamar de 20 médicos em jun/2026. ")
    informado = plano({"meta": {"tipo": "patamar", "valor": 18}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert (informado["meta"]["valor"], informado["por_evento"]) == (18.0, 6)
    # Com vários territórios, a conta é de cada um: Manaus já está acima do patamar dela; Tefé (em zero) voltaria a 3.
    varios = plano({"meta": {"tipo": "patamar"}, "em": "202506"},
                   selecao={"base": {"municipios": {"ids": ["code:130260", "code:130420"]}}, "estados_unidade": ["15"], "horizonte": "202606"})[1]
    assert [(chave, c["planejamento"]["estado"], c["planejamento"]["meta"]["valor"], c["planejamento"]["por_evento"]) for chave, c in varios.items()] == [
        ("code:130260", "ja_alcancada", 45.5, 0), ("code:130420", "calculado", 3.0, 3), ("uf:15", "ja_alcancada", 45.0, 0)]
    assert "acréscimo de 3 médicos neste território, pelo planejamento inverso," in varios["code:130420"]["planejamento"]["texto"]
    # A meta numa referência: o valor dela na data final.
    da_referencia = plano({"meta": {"tipo": "referencia", "referencia": "fixa"}, "em": "202506"},
                          referencias=[{"id": "fixa", "territorio": "code:150140"}])[1]["code:130340"]["planejamento"]
    assert da_referencia["meta"] == {"tipo": "referencia", "valor": 50.0,
                                     "rotulo": "Meta hipotética: alcançar a referência BELEM (PA) (50 médicos em jun/2026)"}
    assert (da_referencia["por_evento"], da_referencia["resultado"]) == (38, 50.0)
    ausente = plano({"meta": {"tipo": "referencia", "referencia": "x"}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert ausente == {"estado": "nao_calculavel", "motivo": "A referência da meta não está no pedido."}


def test_rota_hipotese_derivada_da_simulacao_so_a_dependencia_de_poucos_medicos(catalogo):
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:130420", "code:130260"]}}, "estados_unidade": ["15"], "brasil": True,
                        "conjuntos": [{"id": "g1", "rotulo": "Par", "membros": ["code:130340", "code:150140"]}], "horizonte": "202606",
                        "cenarios": [{"id": "c1", "metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]}]}))
    cenarios = {item["id"]: item["cenarios"][0] for item in body["territorios"]}
    # Tefé, em zero, teria 4 médicos no cenário: a única leitura do Detector que vale para um valor simulado é a escala estrutural.
    assert cenarios["code:130420"]["hipotetico"] == {"rotulo": "hipótese derivada da simulação", "data": "202606", "valor": 4.0, "inteiro": 4,
                                                     "classe": "atencao", "impacto_pct": 25.0}
    assert cenarios["code:130260"]["hipotetico"]["classe"] is None and cenarios["code:130260"]["hipotetico"]["inteiro"] == 55
    # Só para municípios, como a escala estrutural do Detector; e nenhum teste de evento observado (perda, patamar, declínio).
    assert all("hipotetico" not in cenarios[chave] for chave in ("uf:15", "g1", "br"))
    assert set(cenarios["code:130420"]["hipotetico"]) == {"rotulo", "data", "valor", "inteiro", "classe", "impacto_pct"}


def test_rota_recusas_das_referencias_da_metrica_e_do_planejamento(catalogo):
    so = {"base": {"municipios": {"ids": ["code:130340"]}}, "horizonte": "202606"}
    recusa(pedir({**so, "referencias": [{"id": "r" + str(k), "tipo": "valor", "valor": 1} for k in range(6)]}), "Referências inválidas: envie uma lista de até 5.")
    recusa(pedir({**so, "referencias": [{"territorio": "xx"}]}), "indique um município (code:…), um estado (uf:…), o Brasil (br) ou um conjunto")
    recusa(pedir({**so, "referencias": [{"territorio": "g9"}]}), "um conjunto da seleção do Simulador")
    recusa(pedir({**so, "referencias": [{"id": "a", "tipo": "valor", "valor": 1}, {"id": "a", "tipo": "valor", "valor": 2}]}), "Referências com o mesmo id")
    recusa(pedir({**so, "referencias": [{"territorio": "br", "tipo": "movel"}]}), "o tipo é fixa, dinamica ou valor")
    recusa(pedir({**so, "referencias": [{"tipo": "valor", "valor": -1}]}), "um número igual ou maior que zero")
    recusa(pedir({**so, "referencias": [{"territorio": "br", "tipo": "dinamica", "metodo": "x"}]}), "Método desconhecido na referência: x.")
    recusa(pedir({**so, "referencias": [{"territorio": "br", "tipo": "dinamica", "metodo": "manual"}]}), "O sistema não sugere uma taxa.")
    recusa(pedir({**so, "referencias": [{"territorio": "code:999999"}]}), "Território fora da base Brasil")
    recusa(pedir({**so, "comparacao": {"metrica": "indice"}}), "Comparação inválida: a métrica é quantidade ou taxa.")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"em": "202506"}}]}), "envie a meta e o calendário dos acréscimos")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"meta": {"tipo": "x"}, "em": "202506"}}]}),
           "a meta é um valor, o patamar anterior ou uma referência")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"meta": {"tipo": "valor", "valor": 0}, "em": "202506"}}]}),
           "a meta é um número de médicos acima de zero")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"meta": {"tipo": "referencia"}, "em": "202506"}}]}), "indique a referência da meta")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"meta": {"tipo": "valor", "valor": 5}}}]}), "Data da intervenção inválida")


# --------------------------------------------------------------------------------------------- base versionada
@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    pasta = os.getenv("ADT_REAL_DATA_DIR")
    if not pasta:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    arquivos = [p for p in Path(pasta).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
    destino = tmp_path_factory.mktemp("simulador-real") / "brasil"
    install(Path(pasta), destino)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(destino))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        main._BRAZIL_FRAMES.clear()
        yield series_brasil.base_de(main._brazil_sources(""))
        main._BRAZIL_FRAMES.clear()
    assert antes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}


def _inteiros(faixa):
    return round(100 * faixa["inferior"]), round(100 * faixa["superior"])


def test_real_faixas_e_erros_da_retroprojecao_do_anexo(real):
    retro = simulador.retroprojetar(real)
    assert retro.origens == ("201706", "201806", "201906", "202006", "202106", "202206", "202306")
    # As faixas de 80% do M0d (Docs/DETECTOR_E_SIMULADOR_V2_2.md, seção 8.8): P10 a P90, por porte na origem e horizonte.
    assert [[_inteiros(retro.faixas[(porte, anos)]) for anos in (1, 2, 3, 4)] for porte in range(6)] == [
        [(-26, 48), (-31, 72), (-32, 85), (-31, 104)],
        [(-23, 29), (-28, 40), (-29, 53), (-30, 62)],
        [(-19, 24), (-23, 34), (-24, 44), (-25, 55)],
        [(-15, 20), (-19, 30), (-20, 42), (-19, 55)],
        [(-12, 17), (-16, 26), (-16, 34), (-17, 42)],
        [(-7, 10), (-10, 18), (-12, 25), (-11, 34)]]
    assert [retro.faixas[(0, anos)]["casos"] for anos in (1, 2, 3, 4)] == [15101, 13362, 11480, 9395]
    assert [retro.faixas[(0, anos)]["origens"] for anos in (1, 2, 3, 4)] == [7, 6, 5, 4]
    # A cobertura fora da amostra (a faixa calculada sem uma origem, conferida nela) fica perto de 80% em todas as células.
    assert all(0.79 <= faixa["cobertura"] <= 0.81 for faixa in retro.faixas.values()) and len(retro.faixas) == 24
    tabela = {(linha["metodo"], linha["porte"], linha["anos"]): linha for linha in retro.tabela}
    # Em 4 anos, a persistência com a deriva erra menos que a persistência em todos os portes; a taxa composta do próprio
    # município erra mais abaixo de 100 médicos.
    assert [round(tabela[("M0d", porte, 4)]["frente_ao_m0"], 2) for porte in range(6)] == [0.87, 0.83, 0.78, 0.72, 0.64, 0.47]
    assert [round(tabela[("M1", porte, 4)]["frente_ao_m0"], 2) for porte in range(6)] == [1.37, 1.44, 1.27, 1.18, 0.97, 0.76]
    assert all(tabela[("M0", porte, anos)]["frente_ao_m0"] == pytest.approx(1.0) for porte in range(6) for anos in (1, 2, 3, 4))
    assert all(tabela[("M0d", porte, 4)]["vies"] < tabela[("M0", porte, 4)]["vies"] for porte in range(6))  # o viés cai com a deriva


def test_real_cenarios_do_distrito_federal_rio_rufino_e_limites(real):
    # Distrito Federal: com a janela até jun/2019, a deriva (jun/2016 a jun/2019) pega a quebra de fonte, e o padrão volta ao M0;
    # com a janela padrão (até jun/2024), a deriva existe.
    antiga = corpo(pedir({"base": {"municipios": {"ids": ["code:530010"]}}, "janela": {"inicio": "201606", "fim": "201906"},
                          "horizonte": "202106"}))["territorios"][0]
    assert antiga["rotulo"] == "BRASILIA (DF)"
    cenario = antiga["cenarios"][0]
    assert cenario["metodo"]["usado"] == "M0" and cenario["metodo"]["voltou_ao_m0"] is True
    assert {"JANELA_DEPOIS_DA_QUEBRA", "VOLTA_AO_M0", "RETROPROJECAO"} <= {aviso["codigo"] for aviso in cenario["avisos"]}
    assert cenario["parametros"]["janela"]["inicio"] == "201801"
    assert [ponto.get("marca") for ponto in antiga["observado"][:9]] == ["quebra_de_fonte"] * 8 + [None]
    atual = corpo(pedir({"base": {"municipios": {"ids": ["code:530010"]}}}))["territorios"][0]["cenarios"][0]
    assert atual["metodo"]["usado"] == "M0d" and atual["faixa"]["estado"] == "disponivel" and atual["faixa"]["porte"] == "300 ou mais"
    assert atual["final"]["faixa"]["anos"] == 2 and atual["final"]["faixa"]["validada"] is True
    assert atual["final"]["faixa"]["inferior"] < atual["final"]["total"] < atual["final"]["faixa"]["superior"]
    assert atual["texto"].startswith(FIXO) and "Base: registros até jun/2024." in atual["texto"]
    # Rio Rufino (SC): o registro de jun/2023 (4 → 87 → 5) é um pico que volta e fica fora da base do cenário.
    rio = corpo(pedir({"base": {"municipios": {"ids": ["code:421505"]}}, "cenarios": [{"id": "a", "metodo": "M2"}, {"id": "b", "metodo": "padrao"}]}))
    rufino = rio["territorios"][0]
    assert next(ponto for ponto in rufino["observado"] if ponto["competencia"] == "202306")["marca"] == "pico_que_volta"
    m2, padrao = rufino["cenarios"]
    assert "PICO_FORA_DO_AJUSTE" in [aviso["codigo"] for aviso in m2["avisos"]] and m2["parametros"]["janela"]["registros"] == 6
    assert next(a["texto"] for a in m2["avisos"] if a["codigo"] == "DIFERENCA_PARA_O_ULTIMO_REGISTRO").startswith(
        "A tendência ajustada dá 5,7 em jun/2024, e o registro é 5 (+0,7)")
    assert m2["final"]["total"] < 20 and padrao["metodo"]["usado"] == "M0d" and padrao["parametros"]["n0"] == real.quantidade[real.indice["421505"], -1]
    assert rufino["historico"]["registros"] == 6
    # Estado como unidade e Brasil inteiro: o limite de territórios e o padrão provisório do nível.
    estado = corpo(pedir({"estados_unidade": ["35"], "horizonte": "202806"}))["territorios"][0]
    assert estado["rotulo"] == "São Paulo (SP)" and estado["cenarios"][0]["metodo"]["usado"] == "M1"
    assert estado["cenarios"][0]["faixa"]["estado"] == "indisponivel" and estado["cenarios"][0]["horizonte"]["aviso"] == "extrapolacao"
    recusa(pedir({"base": {"municipios": {"todos": True}}}), "O Simulador compara até 100 territórios de cada vez (a seleção tem 5570)")



def test_real_brasil_referencias_e_planejamento_inverso(real):
    # O Brasil como território: a contagem nacional (502.495 médicos em jun/2024), com o padrão provisório do nível e sem faixa.
    brasil = corpo(pedir({"brasil": True}))["territorios"][0]
    cenario = brasil["cenarios"][0]
    assert (brasil["id"], brasil["unidade"], cenario["metodo"]["usado"], cenario["parametros"]["n0"]) == ("br", series_brasil.UNIDADE_BRASIL, "M1", 502495.0)
    assert cenario["parametros"]["taxa_pct"] == pytest.approx(5.9001, abs=1e-4) and cenario["final"]["total"] == pytest.approx(563539.32, abs=0.01)
    assert cenario["faixa"]["estado"] == "indisponivel" and cenario["final"]["faixa"] is None
    assert "PADRAO_PROVISORIO_DO_NIVEL" in [aviso["codigo"] for aviso in cenario["avisos"]]
    assert "sem intervenção, Brasil teria 563.539 médicos em jun/2026." in cenario["texto"]
    # Manaus diante de Florianópolis (dinâmica), do Brasil e de São Paulo (fixas) e de um valor informado, até jun/2028, com o
    # planejamento inverso: a meta hipotética de alcançar Florianópolis, com um acréscimo por ano.
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "horizonte": "202806", "cenarios": [
        {"id": "c1", "metodo": "padrao", "planejamento": {"meta": {"tipo": "referencia", "referencia": "floripa"}, "em": "202506",
                                                        "ate": "202806", "a_cada_meses": 12}}],
        "referencias": [{"id": "floripa", "territorio": "code:420540", "tipo": "dinamica"}, {"id": "br", "territorio": "br"},
                        {"id": "sp", "territorio": "uf:35"}, {"id": "v", "tipo": "valor", "valor": 6500}]}))
    manaus = body["territorios"][0]["cenarios"][0]
    comparacoes = {c["id"]: c for c in manaus["comparacoes"]}
    assert all(c["alcance"] == {"estado": "nao_alcanca", "data": None} for c in comparacoes.values())
    floripa = comparacoes["floripa"]
    assert (floripa["metodo"], floripa["inicial"]["territorio"], floripa["inicial"]["referencia"], floripa["avisos"]) == ("M0d", 4730.0, 5172.0, [])
    assert floripa["final"]["referencia"] == pytest.approx(7565.57, abs=0.01) and floripa["final"]["indice"] == pytest.approx(79.54, abs=0.01)
    assert floripa["texto"].endswith("7.565,6: 1.547,6 abaixo da referência (índice 79,5; 100 é a referência). Não alcança no horizonte simulado (até jun/2028).")
    assert comparacoes["br"]["avisos"][0] == "A referência (Brasil) contém o território: a comparação não é independente."
    assert comparacoes["sp"]["final"]["referencia"] == 148909.0 and len(comparacoes["sp"]["avisos"]) == 1   # só as unidades diferentes
    assert comparacoes["v"]["final"]["diferenca"] == pytest.approx(482.02, abs=0.01)
    plano = manaus["planejamento"]
    assert (plano["estado"], plano["eventos"], plano["datas"], plano["por_evento"], plano["total"]) == (
        "calculado", 4, ["202506", "202606", "202706", "202806"], 387, 1548)
    assert plano["teorico_por_evento"] == pytest.approx(386.896, abs=1e-3) and plano["resultado"] == pytest.approx(7565.98, abs=0.01)
    assert plano["meta"]["rotulo"] == "Meta hipotética: alcançar a referência FLORIANOPOLIS (SC) (7.565,6 médicos em jun/2028)"
    assert "387 médicos em cada um dos 4 eventos, de jun/2025 a jun/2028 (1.548 no total). Pela conta sem arredondar, seriam 386,90 por evento." in plano["texto"]
    assert plano["texto"].endswith("MANAUS (AM) teria 7.566 médicos em jun/2028. Base: registros até jun/2024. É uma conta condicional às "
                                   "hipóteses do cenário, não um plano.")
    # Reaplicado como intervenção, o inteiro alcança a meta; com um médico a menos por evento, não.
    def reaplicar(quantidade):
        return corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "horizonte": "202806", "cenarios": [
            {"id": "c1", "metodo": "padrao", "intervencoes": [{**plano["intervencao"], "quantidade": quantidade}]}]}))["territorios"][0]["cenarios"][0]["final"]["total"]
    assert reaplicar(387) == pytest.approx(plano["resultado"]) and reaplicar(387) >= plano["meta"]["valor"] > reaplicar(386)
    # Com 6.018 médicos no cenário, a escala estrutural não dá sinal, nem nos limites da faixa de 80% (calibrada, de 4 anos).
    assert manaus["hipotetico"]["classe"] is None and manaus["hipotetico"]["na_faixa"] == {"inferior": None, "superior": None}
    assert manaus["final"]["faixa"]["anos"] == 4 and manaus["final"]["faixa"]["validada"] is False
    # Por taxa, com a população de jun/2024 em todas as datas simuladas: Manaus (2,34 por 1.000) diante do Brasil (2,36).
    taxa = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "horizonte": "202606", "comparacao": {"metrica": "taxa"},
                        "referencias": [{"id": "br", "territorio": "br"}]}))
    do_brasil = taxa["territorios"][0]["cenarios"][0]["comparacoes"][0]
    assert do_brasil["final"]["territorio"] == pytest.approx(2.3404, abs=1e-4) and do_brasil["final"]["referencia"] == pytest.approx(2.3638, abs=1e-4)
    assert do_brasil["texto"].startswith("Em jun/2026, MANAUS (AM) teria 2,34 médicos por 1.000 habitantes, e a referência Brasil (fixa: o valor de "
                                         "jun/2024 mantido), 2,36: 0,02 abaixo da referência (índice 99; 100 é a referência).")
    assert do_brasil["texto"].endswith("Hipótese: população constante, a de jun/2024.")
    # "Simular recuperação": Abreulândia (TO), abaixo do patamar anterior (1,75 médico), teria 1 médico no cenário; a conta
    # condicional dá 1 médico em jun/2025, e a hipótese derivada da simulação mostra a dependência de poucos médicos.
    abreulandia = corpo(pedir({"base": {"municipios": {"ids": ["code:170025"]}}, "cenarios": [
        {"id": "c1", "metodo": "padrao", "planejamento": {"meta": {"tipo": "patamar"}, "em": "202506"}}]}))["territorios"][0]["cenarios"][0]
    recuperacao = abreulandia["planejamento"]
    assert recuperacao["meta"] == {"tipo": "patamar", "valor": 1.75, "rotulo": "Meta hipotética: voltar ao patamar de 1,8 médicos em jun/2026"}
    assert (recuperacao["por_evento"], recuperacao["eventos"]) == (1, 1) and recuperacao["teorico_por_evento"] == pytest.approx(0.5638, abs=1e-4)
    assert "ABREULANDIA (TO) teria 2 médicos em jun/2026." in recuperacao["texto"]
    assert abreulandia["hipotetico"] == {"rotulo": "hipótese derivada da simulação", "data": "202606", "valor": pytest.approx(1.1862, abs=1e-4),
                                         "inteiro": 1, "classe": "critica", "impacto_pct": 100.0, "na_faixa": {"inferior": "critica", "superior": "alta"}}
