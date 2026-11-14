"""A régua comum do Detector de Sinais e do Simulador de Cenários (comando V23; backend/reguas.py; Proposta V3, Parte A e seção
B.1): os dez portes, a raridade com o "+1", os mínimos de comparações de cada nível (19, 99 e 999) e a retaguarda — a faixa de
porte, depois a faixa com as vizinhas e, só no moderado, todas as faixas com a mudança padronizada pelo tamanho. Só vetores
sintéticos: nenhum valor representa quantitativos reais.
"""
import numpy as np
import pytest

import reguas


def test_dez_faixas_de_porte_com_as_quatro_acima_de_300():
    assert len(reguas.PORTES) == len(reguas.ROTULOS_DOS_PORTES) == 10
    assert reguas.ROTULOS_DOS_PORTES[6:] == ("300 a 999", "1.000 a 2.999", "3.000 a 9.999", "10.000 ou mais")
    casos = {1: 0, 3: 0, 4: 1, 9: 1, 10: 2, 19: 2, 20: 3, 49: 3, 50: 4, 99: 4, 100: 5, 299: 5, 300: 6, 999: 6, 1000: 7, 2999: 7,
             3000: 8, 9999: 8, 10000: 9, 250000: 9}
    assert {valor: reguas.porte_de(valor) for valor in casos} == casos
    assert [reguas.porte_de(valor) for valor in (0, 0.5, -3, None, float("nan"))] == [None] * 5
    matriz = np.array([[1.0, 300.0, np.nan], [0.0, 2999.0, 10000.0]])
    assert reguas.portes(matriz).tolist() == [[0, 6, -1], [-1, 7, 9]]


def test_raridade_conta_a_propria_mudanca_e_fixa_os_minimos_dos_niveis():
    # (mudanças anteriores iguais ou piores + 1) ÷ (total de mudanças anteriores + 1).
    assert reguas.raridade(0, 19) == pytest.approx(1 / 20) and reguas.raridade(0, 99) == pytest.approx(1 / 100)
    assert reguas.raridade(0, 999) == pytest.approx(1 / 1000) and reguas.raridade(2, 201) == pytest.approx(3 / 202)
    # Com menos comparações que o mínimo, nem a mudança mais rara chega ao nível: é o "+1" que fixa 19, 99 e 999.
    assert reguas.raridade(0, 18) > 1 / 20 and reguas.raridade(0, 98) > 1 / 100 and reguas.raridade(0, 998) > 1 / 1000
    assert reguas.NIVEIS == (("critico", 1000, 999), ("elevado", 100, 99), ("moderado", 20, 19))
    assert reguas.GRAVIDADE == {None: 0, "moderado": 1, "elevado": 2, "critico": 3}


def test_nivel_da_raridade_usa_a_primeira_origem_com_comparacoes_bastantes():
    # A própria faixa basta para os três níveis: a mudança mais rara de 1.000 é crítica.
    tudo = reguas.nivel_da_raridade(0, 1000, 0, 3000, 0, 9000)
    assert (tudo["nivel"], tudo["origem"], tudo["comparacoes"], tudo["raridade"]) == ("critico", "porte", 1000, pytest.approx(1 / 1001))
    assert all(dados["avaliado"] and dados["origem"] == "porte" for dados in tudo["niveis"].values())
    # 54 comparações na faixa e 120 com as vizinhas: o moderado sai da faixa; o elevado, das vizinhas; o crítico não tem base.
    lida = reguas.nivel_da_raridade(0, 54, 0, 120, 0, 5000)
    assert (lida["nivel"], lida["origem"], lida["comparacoes"]) == ("elevado", "vizinhas", 120)
    assert lida["niveis"]["moderado"]["origem"] == "porte" and lida["niveis"]["elevado"]["origem"] == "vizinhas"
    assert lida["niveis"]["critico"] == {"avaliado": False, "comparacoes": 120, "pede": 999, "um_em": 1000}
    assert reguas.sem_comparacoes(lida) == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 120, "pede": 999}
    # Só o moderado junta todas as faixas: com 10 na faixa, 15 com as vizinhas e 400 em todas, o elevado continua sem base.
    pequena = reguas.nivel_da_raridade(0, 10, 0, 15, 3, 400)
    assert (pequena["nivel"], pequena["origem"], pequena["raridade"]) == ("moderado", "todas", pytest.approx(4 / 401))
    assert pequena["niveis"]["elevado"] == {"avaliado": False, "comparacoes": 15, "pede": 99, "um_em": 100}
    assert reguas.sem_comparacoes(pequena) == {"niveis": ["elevado", "critico"], "nivel": "elevado", "comparacoes": 15, "pede": 99}
    # Sem comparações bastantes em nenhuma origem: nenhum nível avaliado, com quantas há e quantas o moderado pede.
    nada = reguas.nivel_da_raridade(0, 5, 0, 9, 0, 12)
    assert nada["nivel"] is None and nada["raridade"] is None and not any(dados["avaliado"] for dados in nada["niveis"].values())
    assert reguas.sem_comparacoes(nada) == {"niveis": ["moderado", "elevado", "critico"], "nivel": "moderado", "comparacoes": 12, "pede": 19}
    # Mudança comum: avaliada, sem nível, com a raridade do moderado para a tela dizer com quem comparou.
    comum = reguas.nivel_da_raridade(30, 100, 80, 300, 900, 3000)
    assert (comum["nivel"], comum["origem"], comum["comparacoes"], comum["raridade"]) == (None, "porte", 100, pytest.approx(31 / 101))
    assert reguas.sem_comparacoes(comum) == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 300, "pede": 999}
    # Os limites podem ser trocados (configuração exploratória): 1 em cada 50 pede 49 comparações.
    trocado = reguas.nivel_da_raridade(0, 30, 0, 60, 0, 60, limites={"moderado": 50})
    assert trocado["niveis"]["moderado"] == {"avaliado": True, "comparacoes": 60, "pede": 49, "um_em": 50.0, "origem": "vizinhas",
                                           "raridade": pytest.approx(1 / 61), "atingido": True}


def test_comparar_com_o_passado_conta_os_empates_na_faixa_nas_vizinhas_e_em_todas():
    # Passado: 4 mudanças na faixa 2 (10 a 19), 2 na faixa 3 (20 a 49) e 1 na faixa 7 (1.000 a 2.999).
    valor_passado = np.array([-0.5, -0.2, 0.0, 0.1, -0.4, 0.3, -0.01])
    porte_passado = np.array([2, 2, 2, 2, 3, 3, 7])
    tamanho_passado = np.array([10.0, 10.0, 10.0, 10.0, 20.0, 20.0, 1000.0])
    delta_passado = valor_passado * tamanho_passado
    # Atual: uma queda de 20% com 10 (faixa 2) — empata com uma do passado — e uma de 1% com 2.000 (faixa 7).
    saida = reguas.comparar_com_o_passado(np.array([-0.2, -0.01]), np.array([-2.0, -20.0]), np.array([10.0, 2000.0]), np.array([2, 7]),
                                          valor_passado, delta_passado, tamanho_passado, porte_passado)
    k_porte, n_porte, k_viz, n_viz, k_todas, n_todas, theta = saida
    assert (k_porte.tolist(), n_porte.tolist()) == ([2, 1], [4, 1])        # −0,5 e −0,2 (o empate conta); −0,01 empata
    assert (k_viz.tolist(), n_viz.tolist()) == ([3, 1], [6, 1])            # com a faixa 3: mais a queda de 40%
    assert theta == reguas.THETA_PADRAO and n_todas.tolist() == [7, 7]     # sem 30 mudanças por faixa, θ = 1
    # Todas as faixas, com a mudança ÷ √tamanho. No passado: −1,58, −0,63, 0, 0,32, −1,79, 1,34 e −0,32. A queda de 20% com 10
    # vale −2/√10 = −0,63 (três iguais ou piores, com o empate); a de 1% com 2.000, −20/√2000 = −0,45 (as mesmas três).
    assert k_todas.tolist() == [3, 3]
    # Quando o maior é o pior (afastamento, oscilação), a contagem é a dos iguais ou maiores.
    maior = reguas.comparar_com_o_passado(np.array([0.3]), np.array([0.3]), np.array([1.0]), np.array([2]), np.array([0.1, 0.3, 0.5, 0.2]),
                                          np.array([0.1, 0.3, 0.5, 0.2]), np.ones(4), np.array([2, 2, 2, 2]), pior_e_menor=False)
    assert (maior[0].tolist(), maior[1].tolist()) == ([2], [4])
    # Sem passado, nada a comparar.
    vazio = reguas.comparar_com_o_passado(np.array([-0.2]), np.array([-2.0]), np.array([10.0]), np.array([2]), np.empty(0), np.empty(0),
                                          np.empty(0), np.empty(0, dtype=int))
    assert [campo.tolist() for campo in vazio[:6]] == [[0]] * 6 and vazio[6] != vazio[6]


def test_comparar_usa_so_as_datas_anteriores_e_o_mesmo_tipo_de_comparacao():
    # Três datas (1, 2 e 3), dois tipos de intervalo (5 e 7 meses), tudo na faixa 2. Em cada data, uma mudança por tipo.
    valor = np.array([-0.1, -0.3, -0.2, -0.4, -0.25, -0.5])
    tempo = np.array([1, 1, 2, 2, 3, 3])
    tipo = np.array([5, 7, 5, 7, 5, 7])
    porte = np.full(6, 2)
    tamanho = np.full(6, 10.0)
    c = reguas.comparar(valor, valor * tamanho, tamanho, porte, tempo, tipo)
    # Na data 1 não há passado; na 2, só a mudança da data 1 do mesmo tipo; na 3, as das datas 1 e 2 do mesmo tipo.
    assert c.n_porte.tolist() == [0, 0, 1, 1, 2, 2]
    assert c.k_porte.tolist() == [0, 0, 0, 0, 0, 0]      # cada queda é a maior do seu tipo até a data
    # O que não pode entrar no passado de uma data fica de fora (o Detector tira as descontinuidades já conhecidas nela).
    sem_a_primeira = reguas.comparar(valor, valor * tamanho, tamanho, porte, tempo, tipo,
                                     usavel=lambda data: np.array([False, True, True, True, True, True]))
    assert sem_a_primeira.n_porte.tolist() == [0, 0, 0, 1, 1, 2]
    niveis = reguas.niveis_em_vetor(c)
    assert niveis.tolist() == [-1] * 6      # com uma ou duas comparações, nem o moderado é avaliado


def test_theta_do_passado_vem_da_dispersao_por_porte():
    gerador = np.random.default_rng(20261113)
    partes = []
    for faixa, tamanho in ((2, 15.0), (4, 70.0), (6, 600.0)):
        # A dispersão cresce com a raiz do tamanho (θ = 1): 400 mudanças por faixa.
        partes.append((gerador.normal(0.0, np.sqrt(tamanho), 400), np.full(400, tamanho), np.full(400, faixa)))
    delta = np.concatenate([parte[0] for parte in partes])
    tamanho = np.concatenate([parte[1] for parte in partes])
    porte = np.concatenate([parte[2] for parte in partes])
    assert reguas.theta_do_passado(delta, tamanho, porte) == pytest.approx(1.0, abs=0.15)
    # Com uma faixa só (ou menos de 30 mudanças por faixa), não há como estimar: θ = 1.
    assert reguas.theta_do_passado(delta[:400], tamanho[:400], porte[:400]) == reguas.THETA_PADRAO
    assert reguas.theta_do_passado(delta[:20], tamanho[:20], porte[:20]) == reguas.THETA_PADRAO
