"""Detector de Sinais Territoriais (comando V22, etapas 3 e 5; backend/detector.py, backend/comparativos.py e
backend/series_brasil.py; a referência é Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2.4, 4.1, 4.2 e 14).

Três grupos de testes:
- **regras**, sobre séries sintéticas montadas direto em `series_brasil.Base` (o calendário real, de janeiro e junho de 2014 a
  2024): a escala estrutural e a histerese; o zero e a ausência; a perda abrupta (a magnitude arredondada para cima, os empates
  contados, só as transições anteriores, o mínimo de transições); o pico que volta, a quebra de fonte e a queda grande que
  persiste; o patamar; o declínio; a desaceleração igual à classe da Análise de Tendência; a instabilidade; os níveis sem
  calibração; e os parâmetros exploratórios; da etapa 5, os fenômenos 8 a 12, com população e coordenadas sintéticas: a janela de
  comparação só em trechos com população comparável, o percentil pelo posto médio, a taxa por habitante e a decomposição (com os
  limites exatos), a posição no universo fixo (com a confirmação em duas avaliações), a defasagem ante a referência na mesma
  unidade, a distância ao município mais próximo que atende ao critério e a coexistência de sinais, sem índice geral;
- **rota** POST /api/detector, com um catálogo sintético instalado como versão governada;
- **base versionada** (job dados-reais, ADT_REAL_DATA_DIR, somente leitura): os casos do anexo — Rio Rufino (SC), o Distrito
  Federal antes de 2018, uma queda grande que persiste, a desaceleração igual à da Análise de Tendência e os números do perfil;
  e os fenômenos 8 a 12 ("comparação não habilitada" em jun/2024; os sinais observados em jun/2021).
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
import comparativos
import detector
import main
import series_brasil
import trend
from brazil_data import FILES, GOVERNED_MANIFEST, manifest_from_repository
from catalog_support import write_state_source
from install_brazil_data import install

client = TestClient(main.app)
PERIODOS = tuple(str(ano) + mes for ano in range(2014, 2025) for mes in ("01", "06"))
T = len(PERIODOS)
P = detector.parametros(None)[0]


def serie(*trechos):
    """Série de 22 registros: cada trecho é (valor, quantos); o último vale até o fim. None é registro ausente."""
    valores = []
    for valor, quantos in trechos[:-1]:
        valores += [valor] * quantos
    valores += [trechos[-1][0]] * (T - len(valores))
    assert len(valores) == T, len(valores)
    return valores


def base(series: dict, estados: dict | None = None) -> series_brasil.Base:
    codigos = tuple(sorted(series))
    quantidade = np.array([[np.nan if v is None else float(v) for v in series[codigo]] for codigo in codigos])
    prefixos = tuple(codigo[:2] for codigo in codigos)
    do_estado = {}
    for linha, prefixo in enumerate(prefixos):
        do_estado.setdefault(prefixo, []).append(linha)
    vazio = np.full(quantidade.shape, np.nan)
    return series_brasil.Base(
        versao="sintetica-" + hashlib.sha256(quantidade.tobytes()).hexdigest()[:12], periodos=PERIODOS,
        meses=np.array([series_brasil.mes_da_competencia(p) for p in PERIODOS]), codigos=codigos,
        nomes=tuple("M" + codigo for codigo in codigos), prefixos=prefixos, quantidade=quantidade, populacao=vazio,
        latitude=vazio, longitude=vazio,
        estados={prefixo: np.array(valores, dtype=float) for prefixo, valores in (estados or {}).items()},
        brasil=np.full(T, np.nan), indice={codigo: linha for linha, codigo in enumerate(codigos)},
        do_estado={prefixo: tuple(linhas) for prefixo, linhas in do_estado.items()})


def avaliar(b, codigo, e, inicio=0, p=P):
    cal = detector.calibrar(b, guardar=False)
    return detector.avaliar(b, cal, series_brasil.municipio(b, codigo), inicio, e, p)


def fundo(quantos, valor=12, prefixo="11"):
    return {prefixo + str(1000 + i): serie((valor, T)) for i in range(quantos)}


def i(competencia):
    return PERIODOS.index(competencia)


# --------------------------------------------------------------------------------------------- escala estrutural (1–2)
def test_escala_estrutural_zero_confirmado_ausencia_e_histerese():
    b = base({"110001": serie((6, 2), (3, 1), (6, 3), (1, 1), (0, 3), (4, 1), (None, 1), (7, 10)), **fundo(3)})
    def estrutural(e):
        return avaliar(b, "110001", e)["estrutural"]
    assert (estrutural(1)["classe"], estrutural(1)["estado"]) == (None, "sem_sinal")
    # A piora aparece na hora; a melhora, só depois de duas observações (a mais grave das duas últimas).
    tres = estrutural(2)
    assert (tres["n"], tres["classe"], tres["impacto_pct"], tres["mantida_pela_anterior"]) == (3, "alta", pytest.approx(100 / 3), False)
    volta = estrutural(3)
    assert (volta["n"], volta["classe_do_valor"], volta["classe"], volta["mantida_pela_anterior"]) == (6, None, "alta", True)
    assert estrutural(4)["classe"] is None
    assert (estrutural(6)["n"], estrutural(6)["classe"], estrutural(6)["impacto_pct"]) == (1, "critica", 100.0)
    # Zero é registro observado: crítica, com a duração do zero (registros e meses reais) e o impacto não calculável.
    zero = estrutural(9)
    assert (zero["n"], zero["classe"], zero["zero_confirmado"], zero["impacto_pct"]) == (0, "critica", True, None)
    assert zero["zeros"] == {"registros": 3, "desde": PERIODOS[7], "meses": 12}  # 201706 → 201806: 7 + 5 meses
    quatro = estrutural(10)
    assert (quatro["n"], quatro["classe_do_valor"], quatro["classe"]) == (4, "atencao", "critica")  # a anterior era zero
    # Ausência de dado não é zero: sem classe e sem número.
    ausente = estrutural(11)
    assert ausente == {"estado": "ausencia_de_dado", "classe": None, "n": None}
    depois = avaliar(b, "110001", 12)
    assert depois["estrutural"]["anterior"] == {"competencia": PERIODOS[10], "n": 4}  # a observação válida anterior
    assert depois["perda"]["meses"] == 12 and depois["perda"]["delta"] == 3


# --------------------------------------------------------------------------------------------- perda abrupta (6)
def _cenario_dos_empates(terceiro_empate=False, futuro=False):
    """98 municípios constantes em 12; A cai de 12 para 8 em jun/2015 e B em jun/2014 (as duas transições de 5 meses antes de
    jun/2016); o alvo cai de 12 para 8 em jun/2016. Na célula (10 a 19 médicos, 5 meses), antes de jun/2016: 201 transições, duas
    delas iguais à do alvo."""
    series = fundo(98)
    series["110101"] = serie((12, 3), (8, 1))
    series["110102"] = serie((12, 1), (8, 1))
    series["110200"] = serie((12, 5), (8, 1))
    if terceiro_empate:
        series["110103"] = serie((12, 3), (8, 1))
    if futuro:  # quedas enormes depois da data avaliada: não podem mudar a avaliação de jun/2016
        for k in range(50):
            series["11" + str(1000 + k)] = serie((12, 7), (2, 1))
    return base(series)


def test_perda_abrupta_conta_os_empates_e_so_as_transicoes_anteriores():
    perda = avaliar(_cenario_dos_empates(), "110200", i("201606"))["perda"]
    assert (perda["anterior"], perda["atual"], perda["delta"], perda["meses"]) == (12, 8, -4, 5)
    assert perda["pct"] == pytest.approx(-100 / 3)
    # Magnitude, com o arredondamento para cima: alta a partir de máx(2; ⌈2,4⌉) = 3; crítica a partir de máx(3; ⌈3,6⌉) = 4.
    assert perda["minimos"] == {"alta": 3, "critica": 4} and perda["magnitude"] == "critica"
    # Excepcionalidade: P(X ≤ x) com os empates: 2 de 201 (0,995% ≤ 1%). A crítica exige 1.000 transições anteriores.
    assert perda["excepcionalidade"] == {"p": pytest.approx(2 / 201), "transicoes": 201, "intervalo_meses": 5, "nivel": "incomum"}
    assert (perda["estado"], perda["classe"], perda.get("critica_sem_calibracao")) == ("alerta", "alta", True)
    # Com um terceiro empate, 3 de 203 (1,48% > 1%): a queda é comum para o porte; o fato continua à vista, sem alerta.
    comum = avaliar(_cenario_dos_empates(terceiro_empate=True), "110200", i("201606"))["perda"]
    assert comum["excepcionalidade"]["p"] == pytest.approx(3 / 203) and comum["excepcionalidade"]["nivel"] == "comum"
    assert (comum["estado"], comum["classe"], comum["motivo"], comum["delta"]) == ("perda_observada", None, "comum_para_o_porte", -4)
    # Origens móveis: o que acontece depois da data avaliada não entra na comparação.
    com_futuro = avaliar(_cenario_dos_empates(futuro=True), "110200", i("201606"))["perda"]
    assert com_futuro["excepcionalidade"] == perda["excepcionalidade"] and com_futuro["classe"] == "alta"


def test_perda_abrupta_magnitude_minima_e_minimo_de_transicoes():
    def perda(valor_final, quantos=120):
        b = base({**fundo(quantos, 11), "110200": serie((11, 5), (valor_final, 1))})
        return avaliar(b, "110200", i("201606"))["perda"]
    # 11 médicos: 2 a menos não chegam a ⌈0,2 × 11⌉ = 3; 3 chegam à alta; 4, à crítica (⌈0,3 × 11⌉ = 4).
    assert (perda(9)["magnitude"], perda(9)["estado"], perda(9)["motivo"]) == (None, "perda_observada", "magnitude_abaixo")
    assert perda(9)["minimos"] == {"alta": 3, "critica": 4}
    assert (perda(8)["magnitude"], perda(8)["classe"]) == ("alta", "alta")
    assert (perda(7)["magnitude"], perda(7)["classe"]) == ("critica", "alta")  # crítica só com 1.000 transições anteriores
    # Abaixo de 100 transições anteriores na célula, sem classificação (a perda continua à vista).
    def em_jun_2015(quantos):
        b = base({**fundo(quantos, 12), "110200": serie((12, 3), (8, 1))})
        return avaliar(b, "110200", i("201506"))["perda"]
    pouco = em_jun_2015(98)  # 98 + a do próprio alvo, em jun/2014 = 99
    assert (pouco["excepcionalidade"]["transicoes"], pouco["estado"], pouco["motivo"], pouco["classe"]) == (
        99, "nao_calibrado", "poucas_transicoes", None)
    assert pouco["delta"] == -4 and pouco["excepcionalidade"]["nivel"] == "nao_calibrada"
    bastante = em_jun_2015(99)
    assert (bastante["excepcionalidade"]["transicoes"], bastante["estado"], bastante["classe"]) == (100, "alerta", "alta")
    # Sem perda, nada a classificar; o aumento também é fato observado.
    assert perda(14)["estado"] == "sem_perda" and perda(14)["delta"] == 3
    # A primeira transição da base não tem com o que comparar.
    primeira = avaliar(base({**fundo(120), "110200": serie((12, 1), (8, 1))}), "110200", 1)["perda"]
    assert (primeira["estado"], primeira["motivo"]) == ("nao_calibrado", "intervalo_irregular")


def test_perda_no_territorio_em_zero_e_no_registro_ausente():
    b = base({"110001": serie((5, 1), (0, 2), (None, 1), (3, 1)), **fundo(3)})
    assert avaliar(b, "110001", 1)["perda"]["delta"] == -5 and avaliar(b, "110001", 1)["perda"]["pct"] == -100.0
    zero = avaliar(b, "110001", 2)["perda"]
    assert (zero["anterior"], zero["delta"], zero["pct"], zero["estado"]) == (0, 0, None, "sem_perda")
    assert avaliar(b, "110001", 3)["perda"] == {"estado": "ausencia_de_dado", "classe": None}


# --------------------------------------------------------------------------------------------- descontinuidade de registro
def test_pico_que_volta_nao_gera_alerta_e_sai_da_calibracao():
    pico = serie((4, 19), (87, 1), (5, 1))  # como Rio Rufino (SC): 4 → 87 → 5, em jan/2023, jun/2023 e jan/2024
    b = base({"420001": pico, **fundo(120, 60)})
    no_salto = avaliar(b, "420001", 19)
    assert no_salto["perda"]["estado"] == "sem_perda" and no_salto["perda"]["verificar_registro"] == "salto"
    assert no_salto["registro"]["estado"] == "verificar_registro"  # a volta ainda não foi observada
    na_volta = avaliar(b, "420001", 20)
    assert (na_volta["perda"]["delta"], na_volta["perda"]["estado"], na_volta["perda"]["classe"]) == (
        -82, "descontinuidade_de_registro", None)
    assert na_volta["perda"]["descontinuidade"] == "pico_que_volta"
    assert na_volta["registro"] == {"estado": "descontinuidade_de_registro", "eventos": [
        {"tipo": "pico_que_volta", "de": "202301", "em": "202306", "ate": "202401", "valores": [4, 87, 5]}]}
    assert "perda" not in na_volta["sinais"] and "registro" in na_volta["sinais"]
    # O patamar não usa o bloco com o registro do pico; a instabilidade não é calculada com ele.
    assert avaliar(b, "420001", 21)["patamar"]["patamar"] == 4.0
    # Até dois registros: 4 → 87 → 80 → 5 é pico; com três registros no alto, não (só "verificar registro").
    dois = base({"420001": serie((4, 6), (87, 1), (80, 1), (5, 1)), **fundo(3)})
    cal = detector.calibrar(dois, guardar=False)
    assert cal.marca[dois.indice["420001"], 6:9].tolist() == [1, 2, 3] and cal.pico[dois.indice["420001"], 6:8].all()
    tres = base({"420001": serie((4, 6), (87, 1), (80, 1), (70, 1), (5, 1)), **fundo(3)})
    assert not detector.calibrar(tres, guardar=False).marca[tres.indice["420001"]].any()
    assert avaliar(tres, "420001", 9)["registro"]["estado"] == "verificar_registro"
    # A volta precisa chegar a até 125% do valor anterior ao salto: 4 → 87 → 6 não é pico.
    seis = base({"420001": serie((4, 6), (87, 1), (6, 1)), **fundo(3)})
    assert not detector.calibrar(seis, guardar=False).marca[seis.indice["420001"]].any()


def test_pico_conhecido_fica_fora_da_comparacao_das_datas_seguintes():
    """O alvo (60 médicos) cai em jan/2018 (7 meses). Antes dele, a volta de um pico (87 → 5, em jan/2017, 7 meses) estaria na
    mesma célula (50 a 99 médicos): conhecida na data avaliada, ela não conta."""
    def alvo(com_pico):
        series = {**fundo(150, 60), "110200": serie((60, 8), (40, 1))}
        series["420001"] = serie((4, 5), (87, 1), (5, 1)) if com_pico else serie((4, T))
        return avaliar(base(series), "110200", i("201801"))["perda"]["excepcionalidade"]
    assert alvo(True) == alvo(False)
    assert alvo(True)["intervalo_meses"] == 7 and alvo(True)["transicoes"] == 151 * 3  # jan/2015, jan/2016 e jan/2017


def test_quebra_de_fonte_e_janela_depois_dela():
    """A soma municipal da UF abaixo da contagem estadual (como o Distrito Federal até jun/2017): o trecho fica fora da
    calibração, a transição que sai dele não é perda nem ganho a classificar, e a janela começa depois."""
    b = base({"530010": serie((100, 8), (300, 1)), **fundo(3)}, estados={"53": [250] * T, "11": [1] * T})
    cal = detector.calibrar(b, guardar=False)
    linha = b.indice["530010"]
    assert cal.quebra[linha].tolist() == [True] * 8 + [False] * (T - 8)
    assert cal.marca[linha, 1:9].tolist() == [4] * 8 and not cal.marca[linha, 9:].any()
    assert not cal.quebra[b.indice["111000"]].any()
    territorio = series_brasil.municipio(b, "530010")
    assert detector._inicio_do_territorio(cal, territorio, 0, T - 1) == 8
    saida = detector.avaliar(b, cal, territorio, 8, 8, P, 0)
    assert saida["perda"]["estado"] == "descontinuidade_de_registro" and saida["perda"]["delta"] == 200
    assert saida["registro"] == {"estado": "descontinuidade_de_registro",
                                 "eventos": [{"tipo": "quebra_de_fonte", "de": "201401", "ate": "201706"}]}
    assert "quebra de fonte" in detector.texto_do_registro(saida["registro"])
    # Na série, o registro que sai da quebra (100 → 300: um salto que dobra a contagem) não leva "verificar registro": o salto é
    # a própria quebra de fonte, como no registro do território (CI 42895759046, com Brasília em jan/2018).
    assert bool(cal.salto[linha, 8]) and int(cal.marca[linha, 8]) == 4
    assert [ponto.get("marca") for ponto in detector._serie(b, cal, territorio, T - 1)[:10]] == ["quebra_de_fonte"] * 8 + [None, None]
    # Um salto fora da quebra continua com "verificar registro".
    outro = base({"530010": serie((100, 8), (300, 4), (700, 1)), **fundo(3)}, estados={"53": [250] * T, "11": [1] * T})
    marcas = [ponto.get("marca") for ponto in detector._serie(outro, detector.calibrar(outro, guardar=False),
                                                              series_brasil.municipio(outro, "530010"), T - 1)]
    assert marcas[8] is None and marcas[12] == "verificar_registro", marcas


def test_queda_grande_que_persiste_continua_alertavel_com_verificar_registro():
    b = base({**fundo(120, 40), "110200": serie((40, 5), (15, 1))})
    av = avaliar(b, "110200", i("201606"))
    assert av["perda"]["verificar_registro"] == "queda" and av["perda"]["delta"] == -25
    assert (av["perda"]["estado"], av["perda"]["classe"], av["perda"]["magnitude"]) == ("alerta", "alta", "critica")
    assert av["registro"]["estado"] == "verificar_registro" and av["registro"]["eventos"][0]["tipo"] == "queda_grande"
    # Dois registros depois, a queda persiste: continua "verificar registro", nunca descontinuidade.
    assert avaliar(b, "110200", i("201706"))["registro"]["estado"] == "verificar_registro"
    assert "Verificar registro" in detector.texto_do_registro(av["registro"])


# --------------------------------------------------------------------------------------------- afastamento de patamar (7)
def test_patamar_e_a_maior_media_de_dois_anos_antes_dos_quatro_ultimos_registros():
    b = base({"110001": serie((50, 4), (60, 4), (40, 1)), "110002": serie((10, 4), (5, 1)), **fundo(3)})
    # Em jan/2019, o bloco 2016–2017 termina em jun/2017 (dentro dos 4 últimos registros): vale o de 2015–2016, com média 55.
    antes = avaliar(b, "110001", i("201901"))["patamar"]
    assert (antes["patamar"], antes["bloco"]) == (55.0, {"de": "201501", "ate": "201606"})
    em_junho = avaliar(b, "110001", i("201906"))["patamar"]
    assert (em_junho["patamar"], em_junho["bloco"]) == (60.0, {"de": "201601", "ate": "201706"})
    assert em_junho["afastamento_pct"] == pytest.approx(100 / 3) and em_junho["diferenca_pct"] == pytest.approx(-100 / 3)
    # Os 2 últimos registros ≤ 85% do patamar: atenção. Sem avaliações anteriores bastantes, não há como dizer se é incomum.
    assert (em_junho["abaixo_por_2"], em_junho["estado"], em_junho["classe"]) == (True, "classificado", "atencao")
    assert em_junho["excepcionalidade"]["nivel"] == "nao_calibrada"
    # Os 4 últimos ≤ 70%: a condição da crítica, que a base não permite calibrar.
    assert em_junho["abaixo_por_4"] is True and em_junho["critica"] == "nao_calibravel"
    assert em_junho["registros_abaixo"] == 4 and em_junho["vale"] == {"competencia": "201801", "valor": 40}
    # Patamar abaixo de 20 médicos: descritivo (o fato aparece, sem intensidade).
    pequeno = avaliar(b, "110002", i("201806"))["patamar"]
    assert (pequeno["patamar"], pequeno["abaixo_por_2"], pequeno["estado"], pequeno["classe"]) == (10.0, True, "descritivo", None)
    # Antes de haver um bloco completo fora dos 4 últimos registros, janela insuficiente.
    assert avaliar(b, "110001", i("201701"))["patamar"] == {"estado": "janela_insuficiente", "classe": None}
    # Com avaliações anteriores bastantes na faixa do patamar e um afastamento na cauda de 1%, intensidade alta.
    muitos = {"12" + str(1000 + k): serie((60, T)) for k in range(60)}
    c = base({**muitos, "110001": serie((60, 8), (40, 1))})
    alta = avaliar(c, "110001", i("201906"))["patamar"]
    assert alta["excepcionalidade"]["observacoes"] >= 100 and alta["excepcionalidade"]["nivel"] == "incomum"
    assert (alta["classe"], alta["critica"]) == ("alta", "nao_calibravel")


# --------------------------------------------------------------------------------------------- declínio (3)
def test_declinio_persistente_na_serie_de_junho():
    # Janeiro repete o junho anterior: nenhuma variação entre junho e janeiro, para a série de junho contar a história.
    junhos = {**{ano: 100 for ano in range(2014, 2020)}, 2020: 95, 2021: 88, 2022: 79, 2023: 85, 2024: 80}
    valores = []
    for ano in range(2014, 2025):
        valores += [junhos.get(ano - 1, 100), junhos[ano]]
    b = base({"110001": valores, **fundo(3)})
    def declinio(competencia, inicio=0):
        return avaliar(b, "110001", i(competencia), inicio)["declinio"]
    um = declinio("202006")  # 2018 → 2019 fica em 100; 2019 → 2020 cai uma vez
    assert (um["reducoes"], um["perda_pct"], um["sinal"], um["estado"]) == (1, pytest.approx(5.0), None, "reducao_observada")
    dois = declinio("202106")  # duas reduções e 12% desde 100: forte
    assert (dois["reducoes"], dois["de"], dois["inicial"], dois["final"], dois["sinal"]) == (2, "201906", 100, 88, "forte")
    assert dois["perda_pct"] == pytest.approx(12.0) and dois["estado"] == "sinal_observado" and dois["classe"] is None
    tres = declinio("202206")  # três reduções e 21%: muito forte
    assert (tres["reducoes"], tres["sinal"], tres["perda_pct"]) == (3, "muito_forte", pytest.approx(21.0))
    # Em janeiro, vale o último junho; a sequência se quebra com o aumento de 2023.
    assert declinio("202301")["reducoes"] == 3 and declinio("202306")["reducoes"] == 0
    assert declinio("202406")["reducoes"] == 1
    # A perda é medida desde o primeiro valor da sequência dentro da janela.
    na_janela = declinio("202206", inicio=i("202006"))
    assert (na_janela["reducoes"], na_janela["inicial"]) == (2, 95) and na_janela["perda_pct"] == pytest.approx(100 * 16 / 95)
    assert declinio("201401") == {"estado": "janela_insuficiente", "classe": None}


# --------------------------------------------------------------------------------------------- desaceleração (4)
def test_desaceleracao_e_a_classe_da_analise_de_tendencia_nos_quatro_junhos():
    sorteio = random.Random(20261110)
    vistas = set()
    for _ in range(400):
        junhos = [sorteio.randint(0, 40) for _ in range(4)]
        if sorteio.random() < 0.5:  # metade das séries com crescimento, para a classe aparecer
            junhos = sorted(junhos)
        valores = [7] * T
        for ano, valor in zip((2021, 2022, 2023, 2024), junhos):
            valores[i(str(ano) + "06")] = valor
        b = base({"110001": valores})
        saida = detector._desaceleracao(b, b.quantidade[0], T - 1)
        esperada = trend.classify((str(ano) + "06", series_brasil.mes_da_competencia(str(ano) + "06"), valor)
                                  for ano, valor in zip((2021, 2022, 2023, 2024), junhos))
        assert (saida["tendencia"], saida["rotulo"]) == (esperada.category, esperada.label), junhos
        assert saida["desacelera"] == (esperada.category == "CRESCIMENTO_DESACELERADO")
        # A situação em palavras: fora do crescimento, o fenômeno não se aplica (em vez de "sem desaceleração (declínio)").
        situacao = detector._texto_desaceleracao(b, {"desaceleracao": saida})["situacao"]
        if esperada.category == "CRESCIMENTO_DESACELERADO":  # com a repetição, "· repetida (exploratória)"
            assert situacao.startswith("Desaceleração do crescimento"), (junhos, situacao)
        else:
            assert situacao == {"CRESCIMENTO": "Sem desaceleração: a série está em crescimento.",
                                "CRESCIMENTO_ACELERADO": "Sem desaceleração: o crescimento está acelerando.",
                                "SEM_CLASSIFICACAO": "Não se aplica: a série não tem classificação de tendência."}.get(
                esperada.category, "Não se aplica: a série está em declínio."), (junhos, situacao)
        vistas.add(esperada.category)
    assert vistas == set(trend.CLASSES), "as 400 séries passam por todas as classes da Análise de Tendência"
    # 10, 16, 20, 22 desacelera; atualizada só em junho (em janeiro, vale o último junho); a persistência é exploratória.
    valores = [7] * T
    for competencia, valor in (("202006", 2), ("202106", 10), ("202206", 16), ("202306", 20), ("202406", 22)):
        valores[i(competencia)] = valor
    b = base({"110001": valores})
    agora = detector._desaceleracao(b, b.quantidade[0], T - 1)
    assert (agora["desacelera"], agora["persistente"], agora["de"], agora["ate"], agora["classe"]) == (
        True, True, "202106", "202406", None)
    assert detector._desaceleracao(b, b.quantidade[0], i("202401"))["ate"] == "202306"
    assert detector._desaceleracao(b, b.quantidade[0], i("201606"))["estado"] == "janela_insuficiente"


# --------------------------------------------------------------------------------------------- instabilidade (5)
def test_instabilidade_descritiva_e_nao_calculavel_abaixo_de_seis():
    sorteio = np.random.default_rng(7)
    series = {"11" + str(1000 + k): [int(v) for v in np.maximum(6, 50 + sorteio.normal(0, 4, T).round())] for k in range(80)}
    series["110001"] = serie((3, 3), (4, 1))        # média abaixo de 6
    series["110002"] = [50, 80] * (T // 2)          # oscila muito mais que o fundo
    b = base(series)
    e = T - 1
    pequeno = avaliar(b, "110001", e)["instabilidade"]
    assert (pequeno["estado"], pequeno["classe"]) == ("nao_calculavel", None) and "indice" not in pequeno
    comum = avaliar(b, "111000", e)["instabilidade"]
    irregular = avaliar(b, "110002", e)["instabilidade"]
    assert comum["estado"] == irregular["estado"] == "descritivo" and comum["classe"] is irregular["classe"] is None
    assert irregular["indice"] > 3 * comum["indice"] > 0 and irregular["inversoes"] == 5  # 6 variações que alternam
    assert avaliar(b, "110002", 3)["instabilidade"] == {"estado": "janela_insuficiente", "classe": None}


# --------------------------------------------------------------------------------------------- níveis e parâmetros
def test_estados_e_conjuntos_tem_os_fatos_sem_intensidade():
    b = base({"110001": serie((3, 5), (1, 1)), "110002": serie((2, 5), (1, 1)), "110003": serie((2, 4), (None, 1), (2, 1))},
             estados={"11": [9] * 5 + [4] * (T - 5)})
    cal = detector.calibrar(b, guardar=False)
    territorios = series_brasil.selecao(b, {"estados_unidade": ["11"], "conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:110001", "code:110002"], "versao": 3},
        {"id": "c2", "rotulo": "Com falta", "membros": ["code:110001", "code:110003"]}]})
    estado, par, falta = (detector.avaliar(b, cal, territorio, 0, 5, P) for territorio in territorios)
    for av in (estado, par):
        assert av["estrutural"]["estado"] == "nivel_sem_classificacao" and av["estrutural"]["classe"] is None
        assert av["perda"]["estado"] == "nivel_sem_classificacao" and av["perda"]["classe"] is None and av["perda"]["delta"] < 0
        assert av["dimensoes"] == {"estrutural": None, "trajetoria": None, "ritmo": None, "comparacao": None, "contexto": None}
    assert (estado["estrutural"]["n"], estado["unidade"]) == (4, series_brasil.UNIDADE_ESTADO)
    assert (par["estrutural"]["n"], par["perda"]["delta"], par["versao"], par["membros"]) == (
        2, -3, 3, ["code:110001", "code:110002"])
    assert par["unidade"] == series_brasil.UNIDADE_CONJUNTO and par["nomes_dos_membros"] == ["M110001", "M110002"]
    # O conjunto só existe na competência em que todos os componentes têm registro.
    assert detector.avaliar(b, cal, territorios[2], 0, 4, P)["estrutural"]["estado"] == "ausencia_de_dado"
    assert falta["estrutural"]["n"] == 3
    # Um conjunto reúne territórios do mesmo nível; o estado inteiro e os municípios dele não entram juntos.
    with pytest.raises(ValueError, match="mistura estados e municípios"):
        series_brasil.selecao(b, {"conjuntos": [{"id": "c", "rotulo": "x", "membros": ["code:110001", "uf:11"]}]})
    with pytest.raises(ValueError, match="junto com o estado inteiro"):
        series_brasil.selecao(b, {"base": {"municipios": {"ids": ["code:110001"]}}, "estados_unidade": ["11"]})
    with pytest.raises(ValueError, match="Nenhum território na seleção"):
        series_brasil.selecao(b, {})


def test_parametros_exploratorios_nunca_trocam_os_padroes_em_silencio():
    padrao = json.dumps(detector.PADRAO, sort_keys=True)
    em_uso, personalizado = detector.parametros(None)
    assert em_uso == detector.PADRAO and personalizado is False and em_uso is not detector.PADRAO
    em_uso, personalizado = detector.parametros({"perda": {"alta_alfa": 5, "alta_minimo": 2}, "estrutural": {"atencao": 9}})
    assert personalizado is True and em_uso["perda"]["alta_alfa"] == 5.0 and em_uso["estrutural"]["atencao"] == 9
    assert detector.parametros({"perda": {"alta_minimo": 2}})[1] is False  # igual ao padrão: não é personalizado
    assert json.dumps(detector.PADRAO, sort_keys=True) == padrao
    for invalido, texto in (({"perda": {"alta_alfa": 500}}, "fora do intervalo"), ({"perda": {"outra": 1}}, "desconhecido"),
                            ({"registro": {"salto": 1}}, "desconhecido"), ({"estrutural": {"critica": 9}}, "precisam crescer"),
                            ({"perda": {"critica_fracao": 5}}, "não pode ser mais frouxo"), ({"perda": {"alta_minimo": 2.5}}, "inteiro")):
        with pytest.raises(ValueError, match=texto):
            detector.parametros(invalido)
    # Com um limite personalizado, o mesmo fato ganha outra leitura — marcada como exploratória pela rota.
    b = base({**fundo(120, 11), "110200": serie((11, 5), (9, 1))})
    frouxo = detector.parametros({"perda": {"alta_fracao": 10}})[0]
    assert avaliar(b, "110200", i("201606"))["perda"]["magnitude"] is None
    assert avaliar(b, "110200", i("201606"), p=frouxo)["perda"]["magnitude"] == "alta"


def test_textos_dos_detalhes_sao_fixos_e_em_linguagem_simples():
    b = _cenario_dos_empates()
    cal = detector.calibrar(b, guardar=False)
    av = detector.avaliar(b, cal, series_brasil.municipio(b, "110200"), 0, i("201606"), P)
    itens = detector.fenomenos(b, av, i("201606"), P)
    assert [item["chave"] for item in itens] == ["estrutural", "declinio", "perda", "patamar", "desaceleracao", "instabilidade",
                                                 "disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"]
    assert [item["numero"] for item in itens] == ["1–2", "3", "6", "7", "4", "5", "8", "9", "10", "11", "12"]   # os 12 fenômenos
    campos = ("situacao", "observado", "criterio", "habitual", "significa", "nao_significa", "limitacoes", "qualidade")
    assert all(isinstance(item[campo], str) and item[campo] for item in itens for campo in campos)
    perda = next(item for item in itens if item["chave"] == "perda")
    assert perda["observado"] == ("Entre jan/2016 e jun/2016 (5 meses), o número de médicos passou de 12 para 8 (−4; −33,3%).")
    assert perda["situacao"] == "−4 (−33,3%) · alerta de intensidade alta"
    assert perda["habitual"].startswith("Entre 201 transições anteriores de municípios com 10 a 19 médicos, no mesmo tipo de "
                                        "intervalo (5 meses), 1,00% tiveram variação igual ou pior que esta: é incomum (limite de 1%).")
    assert "Limites provisórios" in perda["criterio"] and "arredondando para cima" in perda["criterio"]
    # Linguagem simples e controlada: sem juízo de assistência, de causa ou de prioridade.
    tudo = " ".join(item[campo] for item in itens for campo in campos).lower()
    for proibido in ("desassistid", "isolad", "sem cobertura", "não calibrad", "candidato", "recomenda", "deveria", "criticidade"):
        assert proibido not in tudo, proibido
    assert "não diz que a população está sem atendimento" in tudo
    # Sem classificação, a tela recebe o motivo em palavras.
    pouco = base({**fundo(98, 12), "110200": serie((12, 3), (8, 1))})
    cal = detector.calibrar(pouco, guardar=False)
    av = detector.avaliar(pouco, cal, series_brasil.municipio(pouco, "110200"), 0, i("201506"), P)
    texto = next(item for item in detector.fenomenos(pouco, av, i("201506"), P) if item["chave"] == "perda")
    assert texto["habitual"].startswith("Sem classificação: há poucos municípios parecidos na base, antes desta data, para dizer se "
                                        "esta queda é incomum (99 transições anteriores; o mínimo é 100).")


# --------------------------------------------------------------------------------------------- fenômenos 8 a 12 (etapa 5)
def base_comparavel(series: dict, populacoes=10000, coordenadas: dict | None = None, estados: dict | None = None,
                    brasil=None) -> series_brasil.Base:
    """Como `base`, com a população (um número para todos, ou por código: um número ou os 22 valores), as coordenadas (por código:
    latitude e longitude, iguais em todas as competências) e a contagem nacional. A versão sai de tudo isso: os quadros dos
    fenômenos 8 a 11 são guardados por versão da base."""
    codigos = tuple(sorted(series))
    quantidade = np.array([[np.nan if v is None else float(v) for v in series[codigo]] for codigo in codigos])
    prefixos = tuple(codigo[:2] for codigo in codigos)
    do_estado = {}
    for linha, prefixo in enumerate(prefixos):
        do_estado.setdefault(prefixo, []).append(linha)

    def da_populacao(codigo):
        valor = populacoes.get(codigo, 10000) if isinstance(populacoes, dict) else populacoes
        return [np.nan if v is None else float(v) for v in valor] if isinstance(valor, (list, tuple)) else [float(valor)] * T
    populacao = np.array([da_populacao(codigo) for codigo in codigos])
    latitude, longitude = np.full(quantidade.shape, np.nan), np.full(quantidade.shape, np.nan)
    for codigo, (lat, lon) in (coordenadas or {}).items():
        latitude[codigos.index(codigo)], longitude[codigos.index(codigo)] = lat, lon
    nacional = np.full(T, np.nan) if brasil is None else np.array(brasil, dtype=float)
    das_ufs = {prefixo: np.array(valores, dtype=float) for prefixo, valores in (estados or {}).items()}
    marca = hashlib.sha256(b"".join(m.tobytes() for m in (quantidade, populacao, latitude, longitude, nacional, *das_ufs.values())))
    return series_brasil.Base(
        versao="sintetica-" + marca.hexdigest()[:12], periodos=PERIODOS,
        meses=np.array([series_brasil.mes_da_competencia(p) for p in PERIODOS]), codigos=codigos,
        nomes=tuple("M" + codigo for codigo in codigos), prefixos=prefixos, quantidade=quantidade, populacao=populacao,
        latitude=latitude, longitude=longitude, estados=das_ufs, brasil=nacional,
        indice={codigo: linha for linha, codigo in enumerate(codigos)},
        do_estado={prefixo: tuple(linhas) for prefixo, linhas in do_estado.items()})


def texto_do(b, av, e, chave, p=P):
    return next(item for item in detector.fenomenos(b, av, e, p) if item["chave"] == chave)


def test_janela_de_comparacao_so_em_trechos_com_populacao_comparavel():
    b = base_comparavel({"110001": serie((10, T))})
    janelas = {c: comparativos.janela(b, i(c)) for c in PERIODOS}
    def datas(c):
        ini, fim, motivo = janelas[c]
        return (None if ini is None else PERIODOS[ini], None if fim is None else PERIODOS[fim], motivo)
    # Sem um junho, ou sem o junho de dois anos antes: janela insuficiente.
    assert datas("201401") == (None, None, "janela_insuficiente")
    assert datas("201406") == datas("201501") == (None, "201406", "janela_insuficiente")
    assert datas("201506") == (None, "201506", "janela_insuficiente")
    # De junho a junho em 2 anos, atualizada só em junho; habilitada só dentro de 2014–2017 e de 2018–2021.
    assert datas("201606") == datas("201701") == ("201406", "201606", None)
    assert datas("201706") == datas("201801") == ("201506", "201706", None)
    assert datas("202006") == datas("202101") == ("201806", "202006", None)
    assert datas("202106") == datas("202201") == ("201906", "202106", None)
    # As janelas que cruzam 2017→2018 e as que passam de 2021 (a população se repete até 2023 e muda de base em 2024).
    for fim, ini in (("201806", "201606"), ("201906", "201706"), ("202206", "202006"), ("202306", "202106"), ("202406", "202206")):
        assert datas(fim) == (ini, fim, "comparacao_nao_habilitada"), fim
    assert comparativos.TRECHOS_COMPARAVEIS == ((2014, 2017), (2018, 2021)) and comparativos.MINIMO_DE_MEDICOS == 20


def test_percentil_e_o_posto_medio_menos_meio_sobre_n():
    percentis, n = comparativos.percentis(np.array([1.0, 2.0, 2.0, 3.0, np.nan]))
    assert n == 4 and percentis[:4].tolist() == [12.5, 50.0, 50.0, 87.5] and np.isnan(percentis[4])   # os empates no posto médio
    assert comparativos.percentis(np.array([np.nan]))[1] == 0


def _cenario_da_disponibilidade():
    """Sete municípios de 50.000 habitantes; a mudança ocorre em jun/2021 (a janela é de jun/2019 a jun/2021)."""
    antes = i("202106")
    return base_comparavel(
        {"110001": serie((100, antes), (80, 1)), "110002": serie((100, T)), "110003": serie((100, antes), (95, 1)),
         "110004": serie((10, antes), (5, 1)), "110005": serie((100, T)), "110006": serie((100, antes), (None, 1)),
         "110007": serie((100, antes), (90, 1))},
        populacoes={"110001": 50000, "110002": [50000] * antes + [56000] * (T - antes), "110003": 50000, "110004": 50000,
                    "110005": [50000] * antes + [None] * (T - antes), "110006": 50000, "110007": 50000})


def test_disponibilidade_relativa_a_taxa_e_a_decomposicao_com_os_limites_exatos():
    b = _cenario_da_disponibilidade()
    e = i("202106")
    resultado = {codigo: avaliar(b, codigo, e)["disponibilidade"] for codigo in b.codigos}
    # Queda de exatamente 20% (100 → 80 médicos, população igual): o limite exato conta como muito forte.
    vinte = resultado["110001"]
    assert (vinte["estado"], vinte["sinal"], vinte["de"], vinte["ate"]) == ("sinal_observado", "muito_forte", "201906", "202106")
    assert (vinte["taxa_inicial"], vinte["taxa_final"], vinte["taxa"], vinte["populacao"]) == (2.0, 1.6, 1.6, 50000.0)
    assert vinte["variacao_pct"] == pytest.approx(-20.0) and vinte["medicos"] == {"inicial": 100.0, "final": 80.0, "variacao_pct": pytest.approx(-20.0)}
    assert vinte["populacao_da_janela"] == {"inicial": 50000.0, "final": 50000.0, "variacao_pct": 0.0}
    # Exatamente 10% (100 → 90): forte. Só a população cresceu 12% (a taxa cai 10,7%): forte, com a decomposição à vista.
    assert (resultado["110007"]["sinal"], resultado["110007"]["variacao_pct"]) == ("forte", pytest.approx(-10.0))
    so_a_populacao = resultado["110002"]
    assert (so_a_populacao["sinal"], so_a_populacao["medicos"]["variacao_pct"]) == ("forte", 0.0)
    assert so_a_populacao["variacao_pct"] == pytest.approx(100 * (50 / 56 - 1)) and so_a_populacao["populacao_da_janela"]["variacao_pct"] == pytest.approx(12.0)
    # Abaixo do limite, sem sinal; com menos de 20 médicos no início da janela, descritivo (sem sinal, com a variação à vista).
    assert (resultado["110003"]["estado"], resultado["110003"]["sinal"], resultado["110003"]["variacao_pct"]) == ("sem_sinal", None, pytest.approx(-5.0))
    assert (resultado["110004"]["estado"], resultado["110004"]["sinal"], resultado["110004"]["variacao_pct"]) == ("descritivo", None, -50.0)
    # Sem população, o denominador não é estimado; sem registro, ausência de dado (não é zero).
    assert resultado["110005"]["estado"] == "nao_calculavel" and resultado["110005"]["motivo"] == "Sem população válida na data (o denominador não é estimado)."
    assert resultado["110006"]["estado"] == "ausencia_de_dado" and resultado["110006"]["taxa"] is None
    # Nenhuma intensidade nestes indicadores: só o sinal observado, com limite provisório (decisão D-A).
    av = avaliar(b, "110001", e)
    assert av["dimensoes"]["comparacao"] is None and "classe" not in av["disponibilidade"] and "disponibilidade" in av["sinais"]
    texto = texto_do(b, av, e, "disponibilidade")
    assert texto["numero"] == "8" and texto["situacao"] == "−20,0% na taxa por habitante em 2 anos · sinal observado muito forte"
    assert texto["observado"] == ("De jun/2019 a jun/2021, a taxa passou de 2,00 para 1,60 por 1.000 habitantes (−20,0%). O número de médicos "
                                  "passou de 100 para 80 (−20,0%), e a população, de 50.000 para 50.000 (0,0%).")
    assert texto["habitual"] == detector.SEM_VALIDACAO and "Queda de 10% ou mais: sinal forte; de 20% ou mais: muito forte." in texto["criterio"]
    assert "Limites provisórios" in texto["criterio"] and "Não mede acesso, cobertura nem qualidade do atendimento" in texto["nao_significa"]
    # Em jun/2024, a janela (jun/2022 a jun/2024) cruza a troca de base da população: o nível da data fica à vista, sem a variação.
    em_2024 = avaliar(b, "110001", i("202406"))
    assert em_2024["disponibilidade"] == {"taxa": 1.6, "populacao": 50000.0, "competencia": "202406", "sinal": None, "de": "202206",
                                          "ate": "202406", "estado": "comparacao_nao_habilitada"}
    assert em_2024["posicao"]["estado"] == em_2024["defasagem"]["estado"] == "comparacao_nao_habilitada"
    assert em_2024["posicao"]["percentil"] is not None and em_2024["defasagem"]["indice"] is not None
    texto = texto_do(b, em_2024, i("202406"), "disponibilidade")
    assert texto["situacao"] == "1,60 por 1.000 habitantes em jun/2024 · comparação não habilitada"
    assert texto["habitual"] == ("Comparação não habilitada: de jun/2022 a jun/2024, a população de 2021 a 2023 é repetida e a de 2024 é de "
                                 "outra base; só há população comparável dentro de 2014–2017 e de 2018–2021.")
    # Antes de haver dois anos de junhos, janela insuficiente nos três indicadores.
    cedo = avaliar(b, "110001", i("201506"))
    assert [cedo[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem")] == ["janela_insuficiente"] * 3
    # Num conjunto, a taxa é a soma das contagens ÷ a soma das populações (nunca a média das taxas): 180 ÷ 106.000.
    cal = detector.calibrar(b, guardar=False)
    [par] = series_brasil.selecao(b, {"conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:110001", "code:110002"]}]})
    do_par = detector.avaliar(b, cal, par, 0, e, P)["disponibilidade"]
    assert (do_par["taxa"], do_par["populacao"], do_par["sinal"]) == (pytest.approx(1000 * 180 / 106000), 106000.0, "forte")
    assert do_par["taxa"] != pytest.approx((1.6 + 1000 * 100 / 56000) / 2) and do_par["variacao_pct"] == pytest.approx(100 * (180 / 106000 / (200 / 100000) - 1))


def test_posicao_relativa_no_universo_fixo_da_janela_e_a_confirmacao_em_duas_avaliacoes():
    # 20 municípios de fundo (100 a 290 médicos, 10.000 habitantes cada) e cinco alvos; com os 25, os percentis são redondos.
    fundo_fixo = {"11" + str(1000 + k): serie((100 + 10 * k, T)) for k in range(20)}
    alvos = {"112001": serie((215, i("202106")), (135, 1)),    # de 54 para 30: forte (−24 pontos, termina até o percentil 50)
             "112002": serie((285, i("202106")), (255, 1)),    # de 94 para 82: queda de posição (−12 pontos)
             "112003": serie((275, i("202001")), (105, 1)),    # caiu em jan/2020: muito forte nas duas avaliações anuais
             "112004": serie((265, i("202101")), (115, 1)),    # caiu em jan/2021: chega ao limite, mas só numa avaliação
             "112005": serie((15, i("202106")), (8, 1))}       # menos de 20 médicos no início da janela: descritivo
    b = base_comparavel({**fundo_fixo, **alvos})
    e = i("202106")
    posicao = {codigo: avaliar(b, codigo, e)["posicao"] for codigo in alvos}
    def resumo(codigo):
        p = posicao[codigo]
        return (p["estado"], p["sinal"], round(p["percentil_inicial"], 6), round(p["percentil_final"], 6), round(p["variacao_pp"], 6), p.get("confirmada"))
    assert resumo("112001") == ("sinal_observado", "forte", 54.0, 30.0, -24.0, None)
    assert resumo("112002") == ("sinal_observado", "queda", 94.0, 82.0, -12.0, None)
    assert resumo("112003") == ("sinal_observado", "muito_forte", 86.0, 10.0, -76.0, True)
    assert resumo("112004") == ("sinal_observado", "forte", 78.0, 18.0, -60.0, False)
    assert resumo("112005") == ("descritivo", None, 2.0, 2.0, 0.0, None)
    assert all(p["universo"] == p["universo_da_janela"] == 25 and p["nome_do_universo"] == "municípios do Brasil com taxa válida" for p in posicao.values())
    av = avaliar(b, "112004", e)
    texto = texto_do(b, av, e, "posicao")
    assert texto["numero"] == "9" and texto["situacao"] == "−60 pontos de percentil em 2 anos · sinal observado forte"
    assert texto["observado"] == ("De jun/2019 a jun/2021, o território passou do percentil 78 para o 18 (−60 pontos), entre 25 territórios com "
                                  "taxa válida nas duas datas.")
    assert texto["habitual"] == detector.SEM_VALIDACAO + " A queda chega ao limite do sinal muito forte, mas não se repetiu em duas avaliações anuais."
    assert "(posto médio − 0,5) ÷ n" in texto["criterio"] and "Perder posição não é o mesmo que perder médicos" in texto["nao_significa"]
    # Conjuntos não entram em universos de percentis.
    cal = detector.calibrar(b, guardar=False)
    [par] = series_brasil.selecao(b, {"conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:112001", "code:112002"]}]})
    do_par = detector.avaliar(b, cal, par, 0, e, P)
    assert (do_par["posicao"]["estado"], do_par["posicao"]["percentil"]) == ("nao_aplicavel", None)
    assert texto_do(b, do_par, e, "posicao")["situacao"] == "Não se aplica a conjuntos."


def _cenario_da_defasagem():
    """Em cada UF, um alvo (100 médicos até jan/2021 e outro valor depois) e dois municípios fixos (100 e 300 médicos), todos com
    1 médico por 100 habitantes no início: a referência de cada alvo (os demais municípios da UF) fica em 10 por 1.000."""
    def da_uf(prefixo, final):
        return {prefixo + "0001": serie((100, i("202106")), (final, 1)), prefixo + "0002": serie((100, T)), prefixo + "0003": serie((300, T))}
    series = {**da_uf("12", 60), **da_uf("13", 59), **da_uf("14", 84), **da_uf("15", 79), "530010": serie((100, i("202106")), (50, 1))}
    return base_comparavel(series, populacoes={codigo: 30000 if codigo.endswith("0003") else 10000 for codigo in series},
                           estados={"12": [500] * T, "13": [400] * i("202106") + [300] * (T - i("202106")), "14": [450] * T})


def test_defasagem_ante_a_referencia_na_mesma_unidade_e_sem_o_territorio():
    b = _cenario_da_defasagem()
    e = i("202106")
    defasagem = {codigo: avaliar(b, codigo, e)["defasagem"] for codigo in ("120001", "130001", "140001", "150001", "530010")}
    def resumo(codigo):
        d = defasagem[codigo]
        return (d["estado"], d["sinal"], round(d["indice_inicial"], 6), round(d["indice_final"], 6), round(d["variacao_pontos"], 6))
    # O índice final abaixo de 60 é estrito: 60 é forte; 59, muito forte. Abaixo de 80 também: 84 não dá sinal; 79 dá.
    assert resumo("120001") == ("sinal_observado", "forte", 100.0, 60.0, -40.0)
    assert resumo("130001") == ("sinal_observado", "muito_forte", 100.0, 59.0, -41.0)
    assert resumo("140001") == ("sem_sinal", None, 100.0, 84.0, -16.0)
    assert resumo("150001") == ("sinal_observado", "forte", 100.0, 79.0, -21.0)
    assert defasagem["120001"]["referencia"] == {"rotulo": "demais municípios do Acre (soma municipal)", "taxa": 10.0}
    # Um município sozinho na UF (como o Distrito Federal) não tem referência na mesma unidade.
    assert (defasagem["530010"]["estado"], defasagem["530010"]["indice"]) == ("referencia_invalida", None)
    assert defasagem["530010"]["motivo"] == "A UF deste município não tem outros municípios: não há referência na mesma unidade."
    av = avaliar(b, "120001", e)
    texto = texto_do(b, av, e, "defasagem")
    assert texto["numero"] == "10" and texto["situacao"] == "−40 pontos no índice ante a referência em 2 anos · sinal observado forte"
    assert texto["observado"] == ("De jun/2019 a jun/2021, o índice passou de 100 para 60 (−40 pontos). Em jun/2021, a taxa do território é de "
                                  "6,00 por 1.000 habitantes, e a dos demais municípios do Acre (soma municipal), de "
                                  "10,00: índice 60 (100 é a taxa da referência).")
    assert "A referência é uma comparação, não uma meta nem um padrão de suficiência." in texto["nao_significa"]
    # O estado como unidade: a contagem estadual ÷ a soma das populações municipais, diante dos demais estados; no universo dos
    # estados para a posição. O conjunto de municípios: diante dos demais municípios das mesmas UFs, sem os membros.
    cal = detector.calibrar(b, guardar=False)
    estado, par, das_ufs = series_brasil.selecao(b, {"estados_unidade": ["13"], "conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:120001", "code:130001"]}, {"id": "c2", "rotulo": "UFs", "membros": ["uf:12", "uf:14"]}]})
    do_estado = detector.avaliar(b, cal, estado, 0, e, P)
    assert (do_estado["disponibilidade"]["taxa"], do_estado["disponibilidade"]["populacao"], do_estado["disponibilidade"]["sinal"]) == (6.0, 50000.0, "muito_forte")
    assert do_estado["defasagem"]["referencia"] == {"rotulo": "demais estados (soma das contagens estaduais)", "taxa": 9.5}
    assert (do_estado["defasagem"]["sinal"], do_estado["defasagem"]["indice_final"]) == ("forte", pytest.approx(100 * 6 / 9.5))
    assert (do_estado["posicao"]["universo"], do_estado["posicao"]["nome_do_universo"], do_estado["posicao"]["estado"]) == (3, "estados com taxa válida", "sem_sinal")
    assert do_estado["posicao"]["percentil"] == pytest.approx(100 * 0.5 / 3)   # a menor taxa entre os três estados
    do_par = detector.avaliar(b, cal, par, 0, e, P)["defasagem"]
    assert do_par["referencia"]["rotulo"] == "demais municípios do Acre e do Amazonas (soma municipal)"
    assert (do_par["sinal"], round(do_par["indice_final"], 6), round(do_par["variacao_pontos"], 6)) == ("muito_forte", 59.5, -40.5)
    dos_estados = detector.avaliar(b, cal, das_ufs, 0, e, P)
    assert dos_estados["defasagem"]["referencia"] == {"rotulo": "demais estados (soma das contagens estaduais)", "taxa": 6.0}
    assert dos_estados["disponibilidade"]["taxa"] == 9.5 and dos_estados["posicao"]["estado"] == "nao_aplicavel"


def _cenario_do_contexto(**extra):
    """Cinco municípios de 100.000 habitantes na linha do Equador (1 grau de longitude = 111,32 km); a taxa do Brasil é de 2 por
    1.000 (1.000 médicos, 500.000 habitantes). O primeiro e o último atendem ao critério; o quarto não tem coordenada."""
    series = {"210001": serie((300, T)), "210002": serie((100, T)), "210003": serie((150, T)), "210004": serie((100, T)), "210005": serie((500, T))}
    return base_comparavel(series, populacoes=100000, estados={"21": [900] * T}, **{"brasil": [1000] * T, "coordenadas": {
        "210001": (0.0, -50.0), "210002": (0.0, -49.0), "210003": (0.0, -47.0), "210005": (0.0, -40.0)}, **extra})


def test_contexto_geografico_e_a_distancia_ao_municipio_mais_proximo_que_atende_ao_criterio():
    b = _cenario_do_contexto()
    e = i("202406")
    contexto = {codigo: avaliar(b, codigo, e)["contexto"] for codigo in b.codigos}
    criterio = {"taxa_minima": 2.0, "taxa_do_brasil": 2.0, "competencia": "202406"}
    assert all(c["criterio"] == criterio and c["universo"] == 2 for c in contexto.values())
    assert contexto["210001"]["estado"] == contexto["210005"]["estado"] == "atende_ao_criterio" and contexto["210001"]["distancia_km"] is None
    perto, longe = contexto["210002"], contexto["210003"]
    assert (perto["estado"], perto["referencia"], perto["percentil_da_distancia"]) == ("contexto", {"id": "code:210001", "rotulo": "M210001", "taxa": 3.0}, 25.0)
    assert perto["distancia_km"] == pytest.approx(111.3195, abs=1e-3)           # 1 grau de longitude no Equador (SIRGAS 2000)
    assert (longe["referencia"]["id"], longe["percentil_da_distancia"]) == ("code:210001", 75.0)   # a 3 graus do primeiro e a 7 do último
    assert longe["distancia_km"] == pytest.approx(333.9585, abs=1e-3)
    assert (contexto["210004"]["estado"], contexto["210004"]["motivo"]) == ("sem_coordenada", "Sem coordenada válida na data.")
    # Só contexto: sem intensidade, sem sinal e sem juízo sobre o atendimento.
    av = avaliar(b, "210003", e)
    assert av["dimensoes"]["contexto"] is None and "contexto" not in av["sinais"] and "classe" not in av["contexto"]
    texto = texto_do(b, av, e, "contexto")
    assert texto["numero"] == "11" and texto["situacao"] == "A 334 km de M210001, em linha reta"
    assert texto["observado"] == ("O território fica a 334 km, em linha reta, de M210001 (3,00 por 1.000 habitantes), o município mais próximo "
                                  "com taxa igual ou maior que 2,00 por 1.000 habitantes em jun/2024 (100% da taxa do Brasil, de 2,00).")
    assert texto["habitual"] == "A distância é maior que a de 75% dos municípios que não atendem ao critério. Só contexto, sem classificação."
    assert texto["nao_significa"].startswith("Não é distância por estrada, tempo de viagem nem acesso.") and "sem intensidade" in texto["criterio"]
    # O estado como unidade não tem um ponto único; o conjunto vale pelo componente mais próximo, e atende se um deles atende.
    cal = detector.calibrar(b, guardar=False)
    estado, baixos, misto = series_brasil.selecao(b, {"estados_unidade": ["21"]}) + series_brasil.selecao(b, {"conjuntos": [
        {"id": "c1", "rotulo": "Baixos", "membros": ["code:210002", "code:210003"]},
        {"id": "c2", "rotulo": "Com quem atende", "membros": ["code:210001", "code:210002"]}]})
    assert detector.avaliar(b, cal, estado, 0, e, P)["contexto"]["estado"] == "nao_aplicavel"
    dos_baixos = detector.avaliar(b, cal, baixos, 0, e, P)["contexto"]
    assert (dos_baixos["estado"], dos_baixos["membro"], dos_baixos["percentil_da_distancia"]) == ("contexto", "M210002", None)
    assert dos_baixos["distancia_km"] == pytest.approx(111.3195, abs=1e-3)
    assert detector.avaliar(b, cal, misto, 0, e, P)["contexto"]["estado"] == "atende_ao_criterio"
    # O critério é um parâmetro exploratório: com 70% da taxa do Brasil (1,4 por 1.000), o terceiro município passa a atender.
    com_70, personalizado = detector.parametros({"contexto": {"taxa_do_brasil_pct": 70}})
    assert personalizado is True
    assert avaliar(b, "210003", e, p=com_70)["contexto"]["estado"] == "atende_ao_criterio"
    de_perto = avaliar(b, "210002", e, p=com_70)["contexto"]
    assert (de_perto["criterio"]["taxa_minima"], de_perto["referencia"]["id"], de_perto["universo"]) == (pytest.approx(1.4), "code:210001", 1)
    # Sem a contagem nacional, o critério não pode ser aplicado.
    sem_brasil = _cenario_do_contexto(brasil=None)
    assert avaliar(sem_brasil, "210002", e)["contexto"] == {
        "distancia_km": None, "referencia": None, "percentil_da_distancia": None, "universo": 0, "estado": "nao_calculavel",
        "criterio": {"taxa_minima": None, "taxa_do_brasil": None, "competencia": "202406"},
        "motivo": "Sem a taxa do Brasil na data: o critério não pode ser aplicado."}


def test_coexistencia_de_sinais_sem_indice_geral_e_com_as_repercussoes_da_mesma_queda():
    def chaves(sinais, classe):
        saida = comparativos.coexistencia(sinais, classe)
        return saida["estado"], [c["chave"] for c in saida["combinacoes"]], saida["repercussoes"], saida["frentes"]
    # As quatro combinações pré-definidas (seção 4.1, item 12).
    assert chaves(["estrutural", "perda"], "alta") == ("sinais_combinados", ["estrutural_e_perda"], ["perda no último registro"],
                                                      ["condição estrutural", "queda no número de médicos"])
    assert chaves(["estrutural", "perda"], "atencao")[:2] == ("sem_combinacao", [])     # pede intensidade alta ou crítica
    assert chaves(["patamar"], "atencao")[:2] == ("sinais_combinados", ["patamar_e_estrutural"])
    assert chaves(["declinio", "posicao"], None)[:2] == ("sinais_combinados", ["declinio_e_relativa"])
    assert chaves(["estrutural", "declinio", "perda", "patamar"], "critica")[1] == ["estrutural_e_perda", "estrutural_e_declinio", "patamar_e_estrutural"]
    # Os efeitos da mesma queda (a perda, o patamar e os três indicadores relativos) não são evidências independentes: cinco
    # repercussões, uma frente de sinal, e nenhuma combinação.
    efeitos = chaves(["perda", "patamar", "disponibilidade", "posicao", "defasagem"], None)
    assert efeitos[0] == "sem_combinacao" and len(efeitos[2]) == 5 and efeitos[3] == ["queda no número de médicos"]
    assert chaves([], None) == ("sem_combinacao", [], [], []) and chaves(["desaceleracao", "ausencia"], None)[3] == ["condição estrutural", "ritmo"]
    # Sem índice geral: só o perfil por dimensão e as combinações, com "combinados" entre os sinais do território.
    b = base({"110001": serie((3, 5), (1, 1)), "110002": serie((2, T))})
    av = avaliar(b, "110001", 5)
    assert av["coexistencia"]["estado"] == "sinais_combinados" and av["sinais"] == ["estrutural", "perda", "combinados"]
    assert av["dimensoes"] == {"estrutural": "critica", "trajetoria": None, "ritmo": None, "comparacao": None, "contexto": None}
    assert not {"indice_geral", "escore", "pontuacao", "nota"} & set(av) and "classe" not in av["coexistencia"]
    texto = texto_do(b, av, 5, "coexistencia")
    assert texto["numero"] == "12" and texto["situacao"] == "1 combinação de sinais"
    assert texto["observado"].startswith("Combinações presentes: poucos médicos e perda no último registro.")
    assert texto["criterio"].endswith("Não há soma de pontos nem índice geral.")
    assert "não são evidências independentes" in texto["nao_significa"] and "nem dizem o que fazer" in texto["nao_significa"]
    # Sem população na base, os indicadores 8 a 11 dizem por que não são calculados; o núcleo (1 a 7) não muda.
    assert [av[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem", "contexto")] == ["nao_calculavel"] * 4
    so_o_nucleo = detector.avaliar(b, detector.calibrar(b, guardar=False), series_brasil.municipio(b, "110001"), 0, 5, P, comparar=False)
    assert not {"disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"} & set(so_o_nucleo)
    assert so_o_nucleo["sinais"] == ["estrutural", "perda"] and so_o_nucleo["estrutural"] == av["estrutural"]


def test_parametros_dos_fenomenos_8_a_11_sao_exploratorios_e_ordenados():
    assert {chave: detector.PADRAO[chave] for chave in ("disponibilidade", "posicao", "defasagem", "contexto")} == {
        "disponibilidade": {"forte": 10.0, "muito_forte": 20.0},
        "posicao": {"queda": 10.0, "forte": 15.0, "forte_final": 50.0, "muito_forte": 25.0, "muito_forte_final": 25.0},
        "defasagem": {"forte": 15.0, "forte_final": 80.0, "muito_forte": 25.0, "muito_forte_final": 60.0},
        "contexto": {"taxa_do_brasil_pct": 100.0}}
    for invalido, trecho in (({"disponibilidade": {"forte": 30}}, "mais grave não pode ser menor"), ({"posicao": {"queda": 20}}, "mais grave não pode ser menor"),
                             ({"contexto": {"taxa_do_brasil_pct": 5}}, "fora do intervalo"), ({"posicao": {"forte_final": 10}}, "desconhecido")):
        with pytest.raises(ValueError, match=trecho):
            detector.parametros(invalido)
    # Com o limite da queda forte em 25%, a queda de 20% deixa de ser muito forte: a leitura muda, e é exploratória.
    b = _cenario_da_disponibilidade()
    frouxo, personalizado = detector.parametros({"disponibilidade": {"muito_forte": 25}})
    assert personalizado is True and avaliar(b, "110001", i("202106"), p=frouxo)["disponibilidade"]["sinal"] == "forte"
    assert avaliar(b, "110001", i("202106"))["disponibilidade"]["sinal"] == "muito_forte"


# --------------------------------------------------------------------------------------------- rota
UNIDADES = {"130260": ("MANAUS", "AM", [30 + k for k in range(T)]), "130420": ("TEFE", "AM", [3] * 10 + [0] * 12),
            "130340": ("PARINTINS", "AM", [20] * 12 + [12] * 10), "150140": ("BELEM", "PA", [50] * T)}
COORDENADAS = {"130260": ("-3", "-60"), "130420": ("-3", "-65"), "130340": ("-3", "-57"), "150140": ("-1", "-48")}


@pytest.fixture
def catalogo(tmp_path, monkeypatch):
    """Catálogo sintético (4 municípios de 1.000 habitantes, 22 competências) instalado como versão governada. A contagem
    nacional é de 100 médicos: a taxa do Brasil fica em 25 por 1.000, e Manaus e Belém atendem ao critério do contexto geográfico."""
    raiz = tmp_path / "repositorio"
    raiz.mkdir()
    livro = Workbook()
    livro.active.append(["pais", "periodo_ano", "periodo_mes", "categoria_profissional", "contagem"])
    for periodo in PERIODOS:
        livro.active.append(["Brasil", int(periodo[:4]), int(periodo[4:]), "MEDICINA", 100])
    livro.save(raiz / FILES["national"])
    linhas = ["regiao_geografica;uf;municipio;cod_ibge;latitude;longitude;categoria_profissional;periodo_ano;periodo_mes;"
              "quantidade;população_estimada"]
    for k, periodo in enumerate(PERIODOS):
        for codigo, (nome, uf, valores) in UNIDADES.items():
            if codigo == "130340" and periodo == "201501":
                continue  # um registro ausente
            linhas.append(";".join(["NORTE", uf, nome, codigo, *COORDENADAS[codigo], "MEDICINA", periodo[:4], str(int(periodo[4:])),
                                    str(valores[k]), "1000"]))
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
    return client.post("/api/detector", data={"dataset": "brazil", "scope": "municipal", "options": json.dumps(opcoes), **dados})


def corpo(resposta):
    assert resposta.status_code == 200, resposta.text[:2000]
    body = resposta.json()
    json.dumps(body, allow_nan=False)
    return body


def recusa(resposta, trecho):
    assert resposta.status_code == 422, resposta.text[:500]
    assert trecho in resposta.json()["detail"], resposta.json()["detail"]


def test_rota_do_detector_tabela_detalhe_e_recusas(catalogo, monkeypatch):
    monkeypatch.setattr(main, "llm_interpret", lambda *a, **k: (_ for _ in ()).throw(AssertionError("o Detector não usa o provedor de IA")))
    body = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "estados_unidade": ["15"],
                        "conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:130260", "code:130420"], "versao": 2}]}))
    assert body["versao"] == detector.VERSION and body["fonte"]["categoria"] == "MEDICINA" and body["exploratorio"] is False
    assert (body["fonte"]["primeira"], body["fonte"]["ultima"], body["fonte"]["competencias"]) == ("201401", "202406", 22)
    assert body["janela"] == {"inicio": "201401", "fim": "202406", "registros": 22, "meses": 125, "padrao": True,
                              "ultimo_registro_da_base": "202406", "e_o_ultimo": True}
    assert body["competencias"] == list(PERIODOS) and body["parametros"]["padrao"] == detector.PADRAO
    linhas = {linha["id"]: linha for linha in body["linhas"]}
    assert list(linhas) == ["code:130260", "code:130340", "code:130420", "uf:15", "c1"]
    assert body["resumo"]["por_tipo"] == {"municipio": 3, "estado": 1, "conjunto": 1}
    tefe = linhas["code:130420"]  # zero confirmado há 12 registros: crítica, com o fenômeno "ausência"
    assert (tefe["rotulo"], tefe["estrutural"]["classe"], tefe["estrutural"]["n"], tefe["estrutural"]["zeros"]) == ("TEFE (AM)", "critica", 0, 12)
    assert {"estrutural", "ausencia"} <= set(tefe["sinais"]) and tefe["dimensoes"]["estrutural"] == "critica"
    assert (linhas["uf:15"]["tipo"], linhas["uf:15"]["rotulo"], linhas["uf:15"]["estrutural"]["estado"]) == (
        "estado", "Pará (PA)", "nivel_sem_classificacao")
    assert (linhas["c1"]["tipo"], linhas["c1"]["membros"], linhas["c1"]["ultima"]["valor"]) == ("conjunto", 2, 51)
    assert {nota[:5] for nota in body["notas"]} >= {"Base:", "Fato ", "Inten", "Zero "}
    assert body["limitacoes"] == ["LIMITES_PROVISORIOS", "CALIBRACAO_SO_MUNICIPAL", "COMPARACAO_SO_COM_POPULACAO_COMPARAVEL"]
    # Fenômenos 8 a 12 (etapa 5). Em jun/2024, a comparação de 2 anos não é habilitada: o nível da data fica à vista.
    assert body["comparacao"] == {"de": "202206", "ate": "202406", "estado": "comparacao_nao_habilitada", "trechos": [[2014, 2017], [2018, 2021]],
                                  "minimo_de_medicos": 20, "contexto": {"taxa_minima": 25.0, "taxa_do_brasil": 25.0, "pct_da_taxa_do_brasil": 100.0,
                                                                        "atendem": 2, "universo": 2}}
    manaus = linhas["code:130260"]
    assert manaus["disponibilidade"] == {"estado": "comparacao_nao_habilitada", "taxa": 51.0, "populacao": 1000.0, "variacao_pct": None, "sinal": None}
    assert manaus["posicao"] == {"estado": "comparacao_nao_habilitada", "percentil": 87.5, "universo": 4, "variacao_pp": None, "sinal": None}
    assert manaus["defasagem"]["indice"] == pytest.approx(100 * 51 / 6) and manaus["defasagem"]["estado"] == "comparacao_nao_habilitada"
    assert manaus["contexto"] == {"estado": "atende_ao_criterio", "distancia_km": None, "referencia": None, "referencia_id": None, "percentil": None}
    # Parintins e Tefé não atendem: a distância em linha reta até Manaus, o município mais próximo que atende (Belém fica mais longe).
    parintins, tefe_c = linhas["code:130340"]["contexto"], tefe["contexto"]
    assert (parintins["estado"], parintins["referencia"], parintins["referencia_id"], parintins["percentil"]) == ("contexto", "MANAUS (AM)", "code:130260", 25.0)
    assert parintins["distancia_km"] == pytest.approx(333.504, abs=1e-3) and tefe_c["distancia_km"] == pytest.approx(555.839, abs=1e-3)
    assert (tefe_c["referencia_id"], tefe_c["percentil"]) == ("code:130260", 75.0)
    assert linhas["uf:15"]["contexto"]["estado"] == "nao_aplicavel" and linhas["c1"]["contexto"]["estado"] == "atende_ao_criterio"
    assert linhas["c1"]["posicao"]["estado"] == "nao_aplicavel" and linhas["c1"]["ids_dos_membros"] == ["code:130260", "code:130420"]
    assert linhas["c1"]["disponibilidade"]["taxa"] == pytest.approx(1000 * 51 / 2000)   # a soma das contagens ÷ a soma das populações
    assert linhas["uf:15"]["disponibilidade"]["taxa"] == pytest.approx(45.0)            # a contagem estadual ÷ a população dos municípios
    # Tefé (em zero) reúne a condição estrutural e o afastamento de patamar: sinais combinados, sem índice geral.
    assert tefe["coexistencia"]["combinacoes"] == ["patamar_e_estrutural"] and "combinados" in tefe["sinais"]
    assert tefe["coexistencia"]["textos"] == ["Abaixo do patamar anterior e poucos médicos"]
    assert all(linha["dimensoes"]["comparacao"] is None and linha["dimensoes"]["contexto"] is None for linha in body["linhas"])
    assert set(body["resumo"]["sinais"]) >= {"disponibilidade", "posicao", "defasagem", "combinados"}
    # As coordenadas autorizadas para o mapa: os municípios da seleção (e os membros do conjunto), na competência avaliada.
    assert body["coordenadas"] == {"code:130260": [-3.0, -60.0], "code:130340": [-3.0, -57.0], "code:130420": [-3.0, -65.0]}
    # Em jun/2021, a janela (jun/2019 a jun/2021) é habilitada: Parintins caiu de 20 para 12 médicos (−40% na taxa): muito forte.
    em_2021 = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "janela": {"fim": "202106"}}))
    assert (em_2021["comparacao"]["estado"], em_2021["comparacao"]["de"], em_2021["comparacao"]["ate"]) == ("comparavel", "201906", "202106")
    queda = {linha["id"]: linha for linha in em_2021["linhas"]}["code:130340"]
    assert queda["disponibilidade"] == {"estado": "sinal_observado", "taxa": 12.0, "populacao": 1000.0, "variacao_pct": pytest.approx(-40.0),
                                        "sinal": "muito_forte"}
    assert "disponibilidade" in queda["sinais"] and em_2021["resumo"]["sinais"]["disponibilidade"] == 1
    # A janela escolhida entre as competências reais: a situação é a do fim dela; o registro ausente não é zero.
    janela = corpo(pedir({"base": {"municipios": {"ids": ["code:130340"]}}, "janela": {"inicio": "201406", "fim": "201501"}}))
    assert janela["janela"]["padrao"] is False and (janela["janela"]["registros"], janela["janela"]["meses"]) == (2, 7)
    parintins = janela["linhas"][0]
    assert parintins["estrutural"]["estado"] == "ausencia_de_dado" and parintins["ultima"] == {
        "competencia": "201406", "valor": 20, "na_data": False}
    assert janela["resumo"]["sem_registro_na_data"] == 1
    # Os detalhes de um território: a série, o histórico e os sete campos de cada fenômeno.
    detalhe = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "detalhe": "code:130340"}))
    assert detalhe["territorio"]["id"] == "code:130340" and len(detalhe["serie"]) == 22 and len(detalhe["historico"]) == 22
    assert detalhe["serie"][2] == {"competencia": "201501", "valor": None, "estado": "ausencia_de_dado"}
    assert [fenomeno["numero"] for fenomeno in detalhe["fenomenos"]] == ["1–2", "3", "6", "7", "4", "5", "8", "9", "10", "11", "12"]
    # As séries dos gráficos dos fenômenos 8 e 10: a taxa do território, a da referência (os demais municípios da UF) e o índice.
    comparativo = detalhe["comparativo"]
    assert comparativo["competencias"] == list(PERIODOS) and comparativo["trechos"] == [[2014, 2017], [2018, 2021]]
    assert (comparativo["taxa"][0], comparativo["taxa"][2], comparativo["taxa"][-1]) == (20.0, None, 12.0)   # o registro ausente não é zero
    assert comparativo["referencia"]["rotulo"] == "demais municípios do Amazonas (soma municipal)"
    assert comparativo["referencia"]["motivo"] is None and comparativo["referencia"]["taxa"][-1] == pytest.approx(1000 * 51 / 2000)
    assert comparativo["indice"][-1] == pytest.approx(100 * 12 / 25.5)
    assert set(detalhe["coordenadas"]) == {"code:130340", "code:130260"}   # o território e o município de referência do contexto
    assert all(fenomeno[campo] for fenomeno in detalhe["fenomenos"]
               for campo in ("observado", "criterio", "habitual", "significa", "nao_significa", "limitacoes", "qualidade"))
    queda = next(passo for passo in detalhe["historico"] if passo["competencia"] == "202001")
    assert queda["perda"]["delta"] == -8 and queda["valor"] == 12
    # Parâmetros personalizados: exploratório, com os padrões à vista.
    exploratorio = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "parametros": {"estrutural": {"atencao": 40}}}))
    assert exploratorio["exploratorio"] is True and exploratorio["parametros"]["personalizados"] is True
    assert exploratorio["parametros"]["padrao"] == detector.PADRAO and exploratorio["parametros"]["em_uso"]["estrutural"]["atencao"] == 40
    assert exploratorio["limitacoes"][-1] == "CONFIGURACAO_EXPLORATORIA" and any("exploratória" in nota for nota in exploratorio["notas"])
    assert {linha["id"]: linha["estrutural"]["classe"] for linha in exploratorio["linhas"]}["code:130340"] == "atencao"
    # Recusas, em português.
    recusa(pedir({}), "Nenhum território na seleção")
    recusa(pedir({"base": {"municipios": {"ids": ["code:999999"]}}}), "Território fora da base Brasil")
    recusa(pedir({"base": {"municipios": {"todos": True}}, "janela": {"inicio": "202406", "fim": "201401"}}), "o início vem depois do fim")
    recusa(pedir({"base": {"municipios": {"todos": True}}, "janela": {"fim": "202407"}}), "Competência fora da base")
    recusa(pedir({"base": {"municipios": {"todos": True}}, "outra": 1}), "Opção desconhecida")
    recusa(pedir({"base": {"municipios": {"todos": True}}, "detalhe": "code:150140x"}), "fora da seleção")
    recusa(client.post("/api/detector", data={"dataset": "", "options": "{}"}), "usam a base do Brasil")
    recusa(client.post("/api/detector", data={"options": "{}"}, files={"file": ("p.csv", b"a;b\n1;2\n", "text/csv")}),
           "usam a base do Brasil")


# --------------------------------------------------------------------------------------------- base versionada
@pytest.fixture(scope="module")
def real(tmp_path_factory):
    """Base versionada instalada numa pasta temporária (job dados-reais), somente em leitura."""
    pasta = os.getenv("ADT_REAL_DATA_DIR")
    if not pasta:
        pytest.skip("Defina ADT_REAL_DATA_DIR para testar as bases locais somente em leitura")
    arquivos = [p for p in Path(pasta).iterdir() if p.suffix.lower() in (".csv", ".xlsx")]
    antes = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}
    destino = tmp_path_factory.mktemp("detector-real") / "brasil"
    install(Path(pasta), destino)
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("ADT_BRASIL_DATA_DIR", str(destino))
        patch.delenv("ADT_BRASIL_DATA_VERSION", raising=False)
        main._BRAZIL_FRAMES.clear()
        yield series_brasil.base_de(main._brazil_sources(""))
        main._BRAZIL_FRAMES.clear()
    assert antes == {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in arquivos}


def test_real_perfil_da_base_e_tabela_inteira(real):
    assert len(real.codigos) == 5570 and real.periodos == PERIODOS and np.diff(real.meses).tolist() == [5, 7] * 10 + [5]
    cal = detector.calibrar(real)
    # Os 10 municípios com pico que volta e a quebra de fonte só no Distrito Federal, de jan/2014 a jun/2017 (o perfil da base).
    assert len({linha for linha, _ in np.argwhere(cal.marca == 1)}) == 10
    assert {real.prefixos[linha] for linha, _ in np.argwhere(cal.quebra)} == {"53"}
    assert sorted({real.periodos[k] for _, k in np.argwhere(cal.quebra)}) == list(PERIODOS[:8])
    body = corpo(pedir({"base": {"municipios": {"todos": True}}}))
    assert body["resumo"]["territorios"] == 5570 and body["fonte"]["categoria"] == "MEDICINA"
    assert body["resumo"]["sinais"]["desaceleracao"] == 182  # o número do anexo (seção 1.2, ajuste c)
    assert sum(1 for linha in body["linhas"] if linha["desaceleracao"]["persistente"]) == 16  # seção 4.2
    assert body["resumo"]["sinais"]["ausencia"] == 0  # nenhum município em zero em jun/2024
    # Em jun/2024, todas as células (porte × intervalo) têm o mínimo de transições anteriores para os dois limites.
    assert [celula["porte"] for celula in body["calibracao"]["perda"]] == list(detector.ROTULOS_DOS_PORTES)
    assert all(celula["alta"] == celula["critica"] == "calibrado" and celula["transicoes"] >= 1000 for celula in body["calibracao"]["perda"])
    assert all(faixa["critica"] == "nao_calibravel" for faixa in body["calibracao"]["patamar"])
    assert 0 < body["calibracao"]["monitoramento"]["taxa_pct"] < 2  # só monitoramento: perto de 1% por construção
    # Nas primeiras datas, a comparação ainda não existe: sem classificação, com a perda à vista.
    cedo = corpo(pedir({"base": {"municipios": {"todos": True}}, "janela": {"fim": "201406"}}))
    assert cedo["calibracao"]["perda"] == [] or all(c["alta"] == "sem_calibracao" for c in cedo["calibracao"]["perda"])
    assert not any(linha["perda"]["classe"] for linha in cedo["linhas"])
    assert any(linha["perda"]["estado"] == "nao_calibrado" and linha["perda"]["delta"] < 0 for linha in cedo["linhas"])


def test_real_rio_rufino_pico_que_volta(real):
    def detalhe(fim):
        return corpo(pedir({"base": {"municipios": {"ids": ["code:421505"]}}, "detalhe": "code:421505", "janela": {"fim": fim}}))
    no_pico = detalhe("202306")["territorio"]
    assert no_pico["rotulo"] == "RIO RUFINO (SC)" and no_pico["ultima"]["valor"] == 87
    assert no_pico["perda"]["verificar_registro"] == "salto" and no_pico["registro"]["estado"] == "verificar_registro"
    volta = detalhe("202401")
    assert volta["territorio"]["perda"]["delta"] == -82 and volta["territorio"]["perda"]["classe"] is None
    assert volta["territorio"]["perda"]["estado"] == "descontinuidade_de_registro"
    assert volta["territorio"]["registro"]["eventos"] == [
        {"tipo": "pico_que_volta", "de": "202301", "em": "202306", "ate": "202401", "valores": [4, 87, 5]}]
    assert next(ponto for ponto in volta["serie"] if ponto["competencia"] == "202306")["marca"] == "pico_que_volta"
    assert "pico que volta" in volta["fenomenos"][0]["qualidade"]


def test_real_distrito_federal_quebra_de_fonte(real):
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:530010"]}}, "detalhe": "code:530010"}))
    assert body["territorio"]["registro"] == {"estado": "descontinuidade_de_registro",
                                              "eventos": [{"tipo": "quebra_de_fonte", "de": "201401", "ate": "201706"}]}
    assert body["janela_do_territorio"] == {"inicio": "201801", "depois_da_quebra": True}
    assert [ponto.get("marca") for ponto in body["serie"][:9]] == ["quebra_de_fonte"] * 8 + [None]
    assert body["historico"][0]["competencia"] == "201801"


def test_real_queda_grande_que_persiste_continua_alertavel(real):
    cal = detector.calibrar(real)
    q, p = real.quantidade, detector.PADRAO["perda"]
    candidatos = []
    for linha, j in np.argwhere(cal.queda_grande & (cal.marca == 0)):
        if j + 2 < len(PERIODOS) and q[linha, j + 2] <= 0.6 * q[linha, j - 1] and cal.n_perda[linha, j] >= p["alta_transicoes"] \
                and cal.p_perda[linha, j] <= p["alta_alfa"] / 100:
            candidatos.append((linha, j))
    assert candidatos, "a base tem quedas grandes que persistem e são incomuns para o porte"
    linha, j = candidatos[0]
    codigo = "code:" + real.codigos[linha]
    body = corpo(pedir({"base": {"municipios": {"ids": [codigo]}}, "detalhe": codigo, "janela": {"fim": PERIODOS[j]}}))
    perda = body["territorio"]["perda"]
    assert perda["verificar_registro"] == "queda" and perda["estado"] == "alerta" and perda["classe"] in ("alta", "critica")
    assert {"tipo": "queda_grande", "de": PERIODOS[j - 1], "em": PERIODOS[j],
            "valores": [int(q[linha, j - 1]), int(q[linha, j])]} in body["territorio"]["registro"]["eventos"]
    assert body["territorio"]["registro"]["estado"] in ("verificar_registro", "descontinuidade_de_registro")


def test_real_desaceleracao_e_a_classe_da_analise_de_tendencia(real):
    """Na última competência, o rótulo do indicador 4 é o da Análise de Tendência na série anual (os 4 junhos), com a quantidade."""
    inspecao = client.post("/api/inspect", data={"dataset": "brazil", "scope": "municipal"}).json()
    opcoes = {"nivel": "municipios", "indicador": "quantidade", "competencia": "202406", "base": {"municipios": {"estados": ["13", "42"]}},
              "competencia_inicial": "202106", "tendencia": {"competencias": ["202106", "202206", "202306", "202406"]}}
    painel = client.post("/api/painel", data={"dataset": "brazil", "scope": "municipal", "dataset_version": inspecao["source"]["version"],
                                              "mapping": json.dumps(inspecao["suggested_mapping"]), "options": json.dumps(opcoes)})
    assert painel.status_code == 200, painel.text[:2000]
    da_tendencia = {item["id"]: item["tendencia"] for item in painel.json()["itens"] if item["tipo"] == "municipio"}
    linhas = {linha["id"]: linha for linha in corpo(pedir({"base": {"municipios": {"estados": ["13", "42"]}}}))["linhas"]}
    assert len(da_tendencia) == len(linhas) > 300
    conferidos = 0
    for codigo, tendencia in da_tendencia.items():
        if not tendencia["avaliavel"]:
            continue
        conferidos += 1
        assert linhas[codigo]["desaceleracao"]["rotulo"] == tendencia["rotulo"], codigo
        assert linhas[codigo]["desaceleracao"]["desacelera"] == (tendencia["classe"] == "CRESCIMENTO_DESACELERADO"), codigo
    assert conferidos > 300



def test_real_fenomenos_8_a_12_comparacao_so_com_populacao_comparavel(real):
    # No último registro (jun/2024), a janela de jun/2022 a jun/2024 cruza a troca de base da população: os indicadores 8, 9 e 10
    # ficam com "comparação não habilitada", com o nível da data à vista (critério de aceitação do comando, seção 14).
    hoje = corpo(pedir({"base": {"municipios": {"todos": True}}}))
    assert hoje["comparacao"]["estado"] == "comparacao_nao_habilitada" and (hoje["comparacao"]["de"], hoje["comparacao"]["ate"]) == ("202206", "202406")
    assert hoje["comparacao"]["trechos"] == [[2014, 2017], [2018, 2021]] and hoje["comparacao"]["minimo_de_medicos"] == 20
    assert all(linha["disponibilidade"]["estado"] == linha["posicao"]["estado"] == "comparacao_nao_habilitada" for linha in hoje["linhas"])
    assert all(linha["disponibilidade"]["taxa"] is not None and linha["posicao"]["percentil"] is not None for linha in hoje["linhas"])
    por_estado = {}
    for linha in hoje["linhas"]:
        por_estado[linha["defasagem"]["estado"]] = por_estado.get(linha["defasagem"]["estado"], 0) + 1
    assert por_estado == {"comparacao_nao_habilitada": 5569, "referencia_invalida": 1}   # Brasília é o único município da UF
    assert [hoje["resumo"]["sinais"][chave] for chave in ("disponibilidade", "posicao", "defasagem", "combinados")] == [0, 0, 0, 262]
    assert hoje["limitacoes"] == ["LIMITES_PROVISORIOS", "CALIBRACAO_SO_MUNICIPAL", "COMPARACAO_SO_COM_POPULACAO_COMPARAVEL"]
    # O contexto geográfico vale em qualquer data: o critério é a taxa do Brasil (2,36 por 1.000 em jun/2024).
    contexto = hoje["comparacao"]["contexto"]
    assert contexto["taxa_minima"] == contexto["taxa_do_brasil"] == pytest.approx(2.36375, abs=1e-5) and contexto["pct_da_taxa_do_brasil"] == 100.0
    assert (contexto["atendem"], contexto["universo"]) == (2002, 3566)
    estados = {}
    for linha in hoje["linhas"]:
        estados[linha["contexto"]["estado"]] = estados.get(linha["contexto"]["estado"], 0) + 1
    assert estados == {"contexto": 3566, "atende_ao_criterio": 2002, "sem_coordenada": 2}
    assert len(hoje["coordenadas"]) == 5564 and all(len(par) == 2 for par in hoje["coordenadas"].values())
    # Em jun/2021, a janela (jun/2019 a jun/2021) cabe em 2018–2021: os sinais observados, com limites provisórios e sem intensidade.
    antes = corpo(pedir({"base": {"municipios": {"todos": True}}, "janela": {"fim": "202106"}}))
    assert (antes["comparacao"]["estado"], antes["comparacao"]["de"], antes["comparacao"]["ate"]) == ("comparavel", "201906", "202106")
    assert antes["comparacao"]["contexto"]["taxa_do_brasil"] == pytest.approx(1.98342, abs=1e-5)
    assert (antes["comparacao"]["contexto"]["atendem"], antes["comparacao"]["contexto"]["universo"]) == (1720, 3846)
    assert [antes["resumo"]["sinais"][chave] for chave in ("disponibilidade", "posicao", "defasagem", "combinados")] == [191, 225, 108, 568]
    def contar(chave):
        saida = {}
        for linha in antes["linhas"]:
            rotulo = linha[chave]["sinal"] or linha[chave]["estado"]
            saida[rotulo] = saida.get(rotulo, 0) + 1
        return saida
    assert contar("disponibilidade") == {"sem_sinal": 1822, "descritivo": 3554, "forte": 114, "muito_forte": 77, "nao_calculavel": 3}
    assert contar("posicao") == {"sem_sinal": 1788, "descritivo": 3557, "queda": 163, "forte": 61, "muito_forte": 1}
    assert contar("defasagem") == {"sem_sinal": 1904, "descritivo": 3557, "forte": 84, "muito_forte": 24, "referencia_invalida": 1}
    assert all(linha["dimensoes"]["comparacao"] is None and linha["dimensoes"]["contexto"] is None for linha in antes["linhas"])
    linhas = {linha["id"]: linha for linha in antes["linhas"]}
    # Barra Bonita (SP): a mesma queda aparece na perda, na taxa, na posição e no índice — quatro repercussões, nenhuma combinação.
    barra = linhas["code:350530"]
    assert barra["rotulo"] == "BARRA BONITA (SP)" and barra["sinais"] == ["perda", "alerta_perda", "registro", "disponibilidade", "posicao", "defasagem"]
    assert (barra["disponibilidade"]["sinal"], barra["posicao"]["sinal"], barra["defasagem"]["sinal"]) == ("muito_forte", "queda", "forte")
    assert barra["disponibilidade"]["variacao_pct"] == pytest.approx(-36.205, abs=1e-3) and barra["posicao"]["variacao_pp"] == pytest.approx(-11.526, abs=1e-3)
    assert barra["defasagem"]["indice"] == pytest.approx(72.887, abs=1e-3) and barra["posicao"]["universo"] == 5570
    assert barra["coexistencia"] == {"estado": "sem_combinacao", "combinacoes": [], "textos": [], "repercussoes": 4}
    assert barra["contexto"]["estado"] == "atende_ao_criterio"
    # Manaus, abaixo da taxa do Brasil em jun/2021: o município mais próximo que atende ao critério fica a 424 km, em linha reta.
    manaus = linhas["code:130260"]["contexto"]
    assert (manaus["estado"], manaus["referencia"], manaus["referencia_id"]) == ("contexto", "JACAREACANGA (PA)", "code:150375")
    assert manaus["distancia_km"] == pytest.approx(423.514, abs=1e-3) and manaus["percentil"] == pytest.approx(98.271, abs=1e-3)
    assert "code:150375" in antes["coordenadas"] and "code:130260" in antes["coordenadas"]
    # Os detalhes de um território trazem os 11 itens (os 12 fenômenos; 1 e 2 juntos) e as séries dos gráficos dos fenômenos 8 e 10.
    detalhe = corpo(pedir({"base": {"municipios": {"ids": ["code:350530"]}}, "detalhe": "code:350530", "janela": {"fim": "202106"}}))
    assert [fenomeno["numero"] for fenomeno in detalhe["fenomenos"]] == ["1–2", "3", "6", "7", "4", "5", "8", "9", "10", "11", "12"]
    oito = next(fenomeno for fenomeno in detalhe["fenomenos"] if fenomeno["chave"] == "disponibilidade")
    assert oito["situacao"] == "−36,2% na taxa por habitante em 2 anos · sinal observado muito forte" and oito["habitual"] == detector.SEM_VALIDACAO
    comparativo = detalhe["comparativo"]
    assert comparativo["competencias"] == list(PERIODOS[:16]) and len(comparativo["taxa"]) == len(comparativo["indice"]) == 16
    assert comparativo["referencia"]["rotulo"] == "demais municípios de São Paulo (soma municipal)"
    assert comparativo["taxa"][-1] == pytest.approx(3.0727, abs=1e-4) and comparativo["indice"][-1] == pytest.approx(72.887, abs=1e-3)
    tudo = " ".join(fenomeno[campo] for fenomeno in detalhe["fenomenos"] for campo in ("situacao", "observado", "criterio", "habitual",
                                                                                        "significa", "nao_significa")).lower()
    for proibido in ("desassistid", "isolad", "sem cobertura", "recomenda", "deveria", "criticidade", "vazio assistencial"):
        assert proibido not in tudo, proibido
