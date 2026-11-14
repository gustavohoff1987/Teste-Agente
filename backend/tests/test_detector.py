"""Detector de Sinais Territoriais (comando V23; backend/detector.py, backend/comparativos.py, backend/reguas.py e
backend/series_brasil.py; a referência é Docs/DETECTOR_E_SIMULADOR_V3.md, Partes A e B, e, no que ela não muda, a V2.2).

Três grupos de testes:
- **regras**, sobre séries sintéticas montadas direto em `series_brasil.Base` (o calendário real, de janeiro e junho de 2014 a
  2024): os sinais 1 e 2 por convenção, com a histerese; a queda recente pela raridade na base (os empates contados, só as
  mudanças anteriores, o tamanho mínimo, as comparações mínimas e a retaguarda pelas faixas vizinhas e por todas as faixas); o
  pico que volta, a quebra de fonte e a queda grande que persiste; o patamar; o declínio; a desaceleração igual à classe da
  Análise de Tendência; a instabilidade; a régua própria dos estados; os conjuntos sem nível; um nível por território, com os
  efeitos da mesma queda como um evento; os critérios ajustáveis; os textos (uma frase, o "Entenda" e a explicação completa);
  e os sinais 8 a 12, com população e coordenadas sintéticas;
- **rota** POST /api/detector, com um catálogo sintético instalado como versão governada;
- **base versionada** (job dados-reais, ADT_REAL_DATA_DIR, somente leitura): os critérios de aceitação do comando V23 — as taxas
  de alerta da régua, o crítico sem comparações de 3.000 médicos para cima, a régua dos estados — e os casos do anexo (Rio
  Rufino, o Distrito Federal antes de 2018, uma queda grande que persiste e a desaceleração igual à da Análise de Tendência) e
  os sinais 8 a 12 com a população comparável da base (a janela de dois anos, os níveis, o contexto geográfico e "Juntos").
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
import reguas
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


# --------------------------------------------------------------------------------------------- sinais 1 e 2 (por convenção)
def test_poucos_medicos_zero_confirmado_ausencia_e_histerese():
    b = base({"110001": serie((6, 2), (3, 1), (6, 3), (1, 1), (0, 3), (4, 1), (None, 1), (7, 10)), **fundo(3)})
    def estrutural(e):
        return avaliar(b, "110001", e)["estrutural"]
    assert (estrutural(1)["classe"], estrutural(1)["estado"], estrutural(1)["criterio"]) == (None, "sem_sinal", "por convenção")
    # A piora aparece na hora; a melhora, só depois de dois registros (o mais grave dos dois últimos).
    tres = estrutural(2)
    assert (tres["n"], tres["classe"], tres["impacto_pct"], tres["mantida_pela_anterior"]) == (3, "elevado", pytest.approx(100 / 3), False)
    volta = estrutural(3)
    assert (volta["n"], volta["classe_do_valor"], volta["classe"], volta["mantida_pela_anterior"]) == (6, None, "elevado", True)
    # A frase da lista diz de onde vem o nível mantido: "6 médicos (3 no registro anterior)".
    def frase(e):
        return texto_do(b, avaliar(b, "110001", e), e, "estrutural")
    assert [frase(e)["situacao"] for e in (2, 3, 4, 6, 9, 10)] == [
        "3 médicos", "6 médicos (3 no registro anterior)", "6 médicos", "Só 1 médico", "Nenhum médico registrado há 3 registros, desde jun/2017",
        "4 médicos (0 no registro anterior)"]
    assert frase(3)["habitual"].endswith("O nível exibido vem do registro anterior: a melhora só vale depois de dois registros seguidos.")
    # Num território grande, o efeito da saída de um não é "0,0%".
    grande = base({**fundo(3), "110900": serie((67575, T))})
    assert texto_do(grande, avaliar(grande, "110900", 5), 5, "estrutural")["habitual"].endswith(
        "Com 67.575 médicos, a saída de um reduziria o número registrado em menos de 0,1%.")
    assert estrutural(4)["classe"] is None
    assert (estrutural(6)["n"], estrutural(6)["classe"], estrutural(6)["impacto_pct"]) == (1, "critico", 100.0)
    # Zero é registro observado: crítico, com a duração do zero (registros e meses reais) e o impacto não calculável.
    zero = estrutural(9)
    assert (zero["n"], zero["classe"], zero["zero_confirmado"], zero["impacto_pct"]) == (0, "critico", True, None)
    assert zero["zeros"] == {"registros": 3, "desde": PERIODOS[7], "meses": 12}  # 201706 → 201806: 7 + 5 meses
    quatro = estrutural(10)
    assert (quatro["n"], quatro["classe_do_valor"], quatro["classe"]) == (4, "moderado", "critico")  # o anterior era zero
    # Ausência de dado não é zero: sem nível e sem número.
    assert estrutural(11) == {"estado": "ausencia_de_dado", "classe": None, "n": None}
    depois = avaliar(b, "110001", 12)
    assert depois["estrutural"]["anterior"] == {"competencia": PERIODOS[10], "n": 4}  # o registro válido anterior
    assert depois["perda"]["meses"] == 12 and depois["perda"]["delta"] == 3
    # O alerta do território em zero é do sinal 2, por convenção.
    alerta = avaliar(b, "110001", 9)["alerta"]
    assert (alerta["estado"], alerta["nivel"], alerta["sinal"], alerta["criterio"]) == ("alerta", "critico", "ausencia", "por convenção")


# --------------------------------------------------------------------------------------------- sinal 6: queda recente
def _cenario_dos_empates(empates=2, futuro=False):
    """98 municípios constantes em 12; o alvo cai de 12 para 8 em jun/2016. Antes dele, com o mesmo tempo entre registros (5
    meses), `empates` municípios tiveram a mesma queda. Na faixa de 10 a 19 médicos, antes de jun/2016: cerca de 200 mudanças."""
    series = fundo(98)
    series["110200"] = serie((12, 5), (8, 1))
    for k in range(empates):
        series["1101" + str(10 + k)] = serie((12, 1), (8, 1)) if k % 2 else serie((12, 3), (8, 1))
    if futuro:  # quedas enormes depois da data avaliada: não podem mudar a avaliação de jun/2016
        for k in range(50):
            series["11" + str(1000 + k)] = serie((12, 7), (2, 1))
    return base(series)


def test_queda_recente_e_rara_na_base_com_o_mais_um_os_empates_e_so_o_passado():
    perda = avaliar(_cenario_dos_empates(), "110200", i("201606"))["perda"]
    assert (perda["anterior"], perda["atual"], perda["delta"], perda["meses"], perda["porte"]) == (12, 8, -4, 5, 2)
    assert perda["pct"] == pytest.approx(-100 / 3) and perda["criterio"] == "comparado com a base"
    # O tamanho mínimo de cada nível, com o arredondamento para cima: máx(2; ⌈1,2⌉), máx(2; ⌈2,4⌉) e máx(3; ⌈3,6⌉).
    assert perda["minimos"] == {"critico": 4, "elevado": 3, "moderado": 2} and perda["magnitude"] == "critico"
    # Raridade = (iguais ou piores + 1) ÷ (total + 1), com os empates: (2 + 1) ÷ (201 + 1) = 1,49%. É moderado (até 1 em 20), não
    # elevado (1 em 100); o crítico pede 999 comparações, e a base tem 202 (com as faixas vizinhas).
    raridade = perda["raridade"]
    assert (raridade["nivel"], raridade["origem"], raridade["comparacoes"], raridade["intervalo_meses"]) == ("moderado", "porte", 201, 5)
    assert raridade["raridade"] == pytest.approx(3 / 202)
    assert raridade["niveis"]["elevado"] == {"avaliado": True, "comparacoes": 201, "pede": 99, "um_em": 100.0, "origem": "porte",
                                             "raridade": pytest.approx(3 / 202), "atingido": False}
    assert raridade["niveis"]["critico"] == {"avaliado": False, "comparacoes": 202, "pede": 999, "um_em": 1000.0}
    assert (perda["estado"], perda["classe"]) == ("alerta", "moderado")
    assert perda["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 202, "pede": 999}
    # Quem não caiu também sabe que níveis a base sustenta para o seu porte: sem alerta, com o crítico "sem comparações suficientes".
    cenario = _cenario_dos_empates()
    parado = avaliar(cenario, "110110", i("201606"))
    assert (parado["perda"]["estado"], parado["perda"]["delta"], parado["perda"]["classe"]) == ("sem_perda", 0, None)
    assert parado["perda"]["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 202, "pede": 999}
    do_parado = texto_do(cenario, parado, i("201606"), "perda")
    assert (do_parado["situacao"], do_parado["estado_do_nivel"]) == ("Sem queda no último registro", "sem_alerta")
    assert do_parado["habitual"] == ("Não houve queda. A base ainda não tem história para dizer se uma queda chega ao nível crítico: são 202 "
                                     "comparações, e o crítico pede 999.")
    assert do_parado["sem_comparacoes"]["texto"] == "Sem comparações suficientes para o crítico: há 202, e ele pede 999."
    # Sem empates, a queda é a maior da história: 1 ÷ (198 + 1) = 0,5%, elevado. O crítico continua sem comparações.
    unica = avaliar(_cenario_dos_empates(empates=0), "110200", i("201606"))["perda"]
    assert (unica["estado"], unica["classe"], unica["raridade"]["raridade"]) == ("alerta", "elevado", pytest.approx(1 / 199))
    # Com 12 empates, (12 + 1) ÷ (216 + 1) = 6,0%: comum para o porte. O fato continua à vista, sem alerta.
    comum = avaliar(_cenario_dos_empates(empates=12), "110200", i("201606"))["perda"]
    assert comum["raridade"]["raridade"] == pytest.approx(13 / 217) and comum["raridade"]["nivel"] is None
    assert (comum["estado"], comum["classe"], comum["motivo"], comum["delta"]) == ("perda_observada", None, "comum_para_o_porte", -4)
    # Só o passado: o que acontece depois da data avaliada não entra na comparação.
    com_futuro = avaliar(_cenario_dos_empates(futuro=True), "110200", i("201606"))["perda"]
    assert com_futuro["raridade"] == perda["raridade"] and com_futuro["classe"] == "moderado"


def test_queda_recente_pede_tamanho_minimo_e_comparacoes_minimas():
    # De 2 para 1 médico: é só 1 médico, abaixo do tamanho mínimo. Não vira alerta de queda; aparece como crítico no sinal 1.
    b = base({**fundo(120, valor=2), "110200": serie((2, 5), (1, 1))})
    av = avaliar(b, "110200", i("201606"))
    assert (av["perda"]["estado"], av["perda"]["classe"], av["perda"]["motivo"], av["perda"]["magnitude"]) == (
        "perda_observada", None, "tamanho_abaixo", None)
    assert av["perda"]["minimos"] == {"critico": 3, "elevado": 2, "moderado": 2}
    assert (av["alerta"]["nivel"], av["alerta"]["sinal"], av["alerta"]["criterio"]) == ("critico", "estrutural", "por convenção")
    # Com 11 comparações, nem o moderado é avaliado: "sem comparações suficientes", com quantas há e quantas ele pede.
    b = base({**fundo(10), "110200": serie((12, 3), (8, 2), (5, 1))})
    cedo = avaliar(b, "110200", i("201506"))["perda"]
    assert (cedo["estado"], cedo["classe"], cedo["motivo"], cedo["delta"]) == ("sem_comparacoes", None, "poucas_comparacoes", -4)
    assert cedo["sem_comparacoes"] == {"niveis": ["moderado", "elevado", "critico"], "nivel": "moderado", "comparacoes": 11, "pede": 19}
    assert not any(dados["avaliado"] for dados in cedo["raridade"]["niveis"].values())
    # O território fica "sem comparações suficientes" quando tinha o que comparar (uma queda) e nenhum sinal pôde ser comparado.
    # Quem não caiu não tem o que alertar: fica sem alerta, com ou sem comparações na régua.
    do_alvo, do_vizinho = avaliar(b, "110200", i("201506")), avaliar(b, "111000", i("201506"))
    assert (do_alvo["alerta"]["estado"], do_alvo["alerta"]["nivel"], do_alvo["alerta"]["sem_comparacoes"]) == ("sem_comparacoes", None, ["perda"])
    assert (do_vizinho["perda"]["estado"], do_vizinho["perda"]["avaliavel"], do_vizinho["alerta"]["estado"]) == ("sem_perda", False, "sem_alerta")
    assert avaliar(b, "111000", i("201606"))["perda"]["avaliavel"] is True
    # Um ano depois, com 22: o moderado pode ser avaliado (a queda mais rara de 22: 1 ÷ 23); o elevado ainda pede 99.
    depois = avaliar(b, "110200", i("201606"))["perda"]
    assert (depois["estado"], depois["classe"], depois["delta"]) == ("alerta", "moderado", -3)
    assert depois["raridade"]["niveis"]["moderado"]["raridade"] == pytest.approx(1 / 23)
    assert depois["sem_comparacoes"] == {"niveis": ["elevado", "critico"], "nivel": "elevado", "comparacoes": 22, "pede": 99}


def test_retaguarda_da_queda_recente_as_faixas_vizinhas_e_so_no_moderado_todas_as_faixas():
    # O alvo (30 médicos, faixa de 20 a 49) é o único do seu porte: as comparações vêm da faixa vizinha (10 a 19).
    series = fundo(150)
    series["110200"] = serie((30, 5), (20, 1))
    vizinhas = avaliar(base(series), "110200", i("201606"))["perda"]
    assert (vizinhas["estado"], vizinhas["classe"], vizinhas["porte"]) == ("alerta", "elevado", 3)
    assert [vizinhas["raridade"]["niveis"][nivel].get("origem") for nivel in ("moderado", "elevado", "critico")] == ["vizinhas", "vizinhas", None]
    assert vizinhas["raridade"]["niveis"]["elevado"]["comparacoes"] == 302
    # O alvo (2.000 médicos) não tem vizinhos de porte: só o moderado junta todas as faixas, com a mudança padronizada pelo
    # tamanho. O elevado e o crítico ficam sem comparações suficientes.
    series["110200"] = serie((2000, 5), (1500, 1))
    todas = avaliar(base(series), "110200", i("201606"))["perda"]
    assert (todas["estado"], todas["classe"], todas["porte"]) == ("alerta", "moderado", 7)
    assert todas["raridade"]["niveis"]["moderado"]["origem"] == "todas" and todas["raridade"]["niveis"]["moderado"]["comparacoes"] == 302
    assert todas["sem_comparacoes"] == {"niveis": ["elevado", "critico"], "nivel": "elevado", "comparacoes": 2, "pede": 99}


def test_queda_no_territorio_em_zero_e_no_registro_ausente():
    b = base({"110001": serie((5, 1), (0, 2), (None, 1), (3, 1)), **fundo(3)})
    assert avaliar(b, "110001", 1)["perda"]["delta"] == -5 and avaliar(b, "110001", 1)["perda"]["pct"] == -100.0
    zero = avaliar(b, "110001", 2)["perda"]
    assert (zero["anterior"], zero["delta"], zero["pct"], zero["estado"]) == (0, 0, None, "sem_perda")
    assert avaliar(b, "110001", 3)["perda"] == {"estado": "ausencia_de_dado", "classe": None}


# --------------------------------------------------------------------------------------------- descontinuidade de registro
def test_pico_que_volta_nao_gera_alerta_e_sai_da_regua():
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
    # O patamar não usa o bloco com o registro do pico.
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
    mesma faixa (50 a 99 médicos): conhecida na data avaliada, ela não conta."""
    def alvo(com_pico):
        series = {**fundo(150, 60), "110200": serie((60, 8), (40, 1))}
        series["420001"] = serie((4, 5), (87, 1), (5, 1)) if com_pico else serie((4, T))
        return avaliar(base(series), "110200", i("201801"))["perda"]["raridade"]
    assert alvo(True) == alvo(False)
    assert alvo(True)["intervalo_meses"] == 7 and alvo(True)["comparacoes"] == 151 * 3  # jan/2015, jan/2016 e jan/2017


def test_quebra_de_fonte_e_janela_depois_dela():
    """A soma municipal da UF abaixo da contagem estadual (como o Distrito Federal até jun/2017): o trecho fica fora da régua,
    a transição que sai dele não é queda nem ganho a classificar, e a janela começa depois."""
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
    assert (av["perda"]["estado"], av["perda"]["classe"], av["perda"]["magnitude"]) == ("alerta", "elevado", "critico")
    assert av["registro"]["estado"] == "verificar_registro" and av["registro"]["eventos"][0]["tipo"] == "queda_grande"
    # Dois registros depois, a queda persiste: continua "verificar registro", nunca descontinuidade.
    assert avaliar(b, "110200", i("201706"))["registro"]["estado"] == "verificar_registro"
    assert "Verificar registro" in detector.texto_do_registro(av["registro"])


# --------------------------------------------------------------------------------------------- sinal 7: abaixo do que já teve
def test_patamar_moderado_por_convencao_e_os_niveis_seguintes_pela_raridade():
    series = fundo(30, valor=40)
    series.update({"110200": serie((40, 8), (30, 1)), "110201": serie((40, 8), (26, 1)), "110202": serie((15, 8), (10, 1)),
                   "110203": serie((40, 8), (36, 1))})
    b = base(series)
    # O patamar é a maior média de dois anos completos, antes dos 4 últimos registros: 40 (2014 e 2015).
    vinte_e_cinco = avaliar(b, "110200", T - 1)["patamar"]
    assert (vinte_e_cinco["patamar"], vinte_e_cinco["bloco"], vinte_e_cinco["atual"]) == (40.0, {"de": "201401", "ate": "201506"}, 30)
    assert (vinte_e_cinco["diferenca_pct"], vinte_e_cinco["afastamento_pct"], vinte_e_cinco["registros_abaixo"]) == (-25.0, 25.0, 14)
    # Os 2 últimos registros 15% ou mais abaixo: moderado, por convenção. O elevado pede, além disso, que o afastamento seja
    # raro na base (1 em 100): aqui, 25 ÷ 463 = 5,4%, não é.
    assert (vinte_e_cinco["estado"], vinte_e_cinco["classe"], vinte_e_cinco["criterio"]) == ("classificado", "moderado", "por convenção")
    assert (vinte_e_cinco["abaixo_por_2"], vinte_e_cinco["abaixo_por_4"]) == (True, False)
    elevado = vinte_e_cinco["raridade"]["niveis"]["elevado"]
    assert (elevado["avaliado"], elevado["comparacoes"], elevado["atingido"], elevado["raridade"]) == (True, 462, False, pytest.approx(25 / 463))
    assert vinte_e_cinco["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 476, "pede": 999}
    # Os 4 últimos registros 30% ou mais abaixo: o crítico pediria também a raridade de 1 em 1.000, que a base não sustenta.
    trinta_e_cinco = avaliar(b, "110201", T - 1)["patamar"]
    assert (trinta_e_cinco["abaixo_por_4"], trinta_e_cinco["classe"], trinta_e_cinco["criterio"]) == (True, "moderado", "por convenção")
    # Patamar abaixo de 20: só descritivo. Menos de 15% abaixo: sem alerta.
    assert (avaliar(b, "110202", T - 1)["patamar"]["estado"], avaliar(b, "110202", T - 1)["patamar"]["classe"]) == ("descritivo", None)
    assert (avaliar(b, "110203", T - 1)["patamar"]["estado"], avaliar(b, "110203", T - 1)["patamar"]["abaixo_por_2"]) == ("sem_sinal", False)
    # Com muitos territórios parecidos sem afastamento, um afastamento de 40% é raro: elevado, comparado com a base.
    series = fundo(150, valor=40)
    series["110200"] = serie((40, 18), (24, 1))
    raro = avaliar(base(series), "110200", T - 1)
    assert (raro["patamar"]["classe"], raro["patamar"]["criterio"]) == ("elevado", "comparado com a base")
    assert (raro["alerta"]["nivel"], raro["alerta"]["sinal"], raro["alerta"]["criterio"]) == ("elevado", "patamar", "comparado com a base")
    assert detector.por_que(base(series), raro, T - 1, P) == "40% abaixo do que já teve (patamar de 40)"


# --------------------------------------------------------------------------------------------- sinal 3: declínio persistente
def test_declinio_persistente_por_convencao_nos_tres_niveis():
    def declinio(junhos):   # os valores de junho de 2020 a 2024
        b = base({"110200": [50] * 12 + [valor for junho in junhos for valor in (junho, junho)], **fundo(3)})
        return avaliar(b, "110200", T - 1)["declinio"]
    critico = declinio([50, 45, 40, 34, 30])     # 4 quedas anuais seguidas e perda de 40%
    assert (critico["estado"], critico["classe"], critico["reducoes"], critico["perda_pct"]) == ("classificado", "critico", 4, pytest.approx(40.0))
    assert (critico["de"], critico["ate"], critico["inicial"], critico["final"], critico["criterio"]) == ("202006", "202406", 50, 30, "por convenção")
    elevado = declinio([50, 50, 46, 42, 38])     # 3 quedas e 24%
    assert (elevado["classe"], elevado["reducoes"], elevado["perda_pct"]) == ("elevado", 3, pytest.approx(24.0))
    moderado = declinio([50, 50, 50, 47, 44])    # 2 quedas e 12%
    assert (moderado["classe"], moderado["reducoes"], moderado["perda_pct"]) == ("moderado", 2, pytest.approx(12.0))
    # Duas quedas com perda de 4%, ou uma queda só (mesmo de 20%): o fato aparece, sem nível.
    assert (declinio([50, 50, 50, 49, 48])["estado"], declinio([50, 50, 50, 49, 48])["classe"]) == ("reducao_observada", None)
    uma = declinio([50, 50, 50, 50, 40])
    assert (uma["estado"], uma["classe"], uma["reducoes"], uma["perda_pct"]) == ("reducao_observada", None, 1, pytest.approx(20.0))


# --------------------------------------------------------------------------------------------- sinal 4: desaceleração
def test_desaceleracao_e_a_classe_da_analise_de_tendencia_moderado_quando_se_repete():
    def junhos(valores):   # os 11 valores de junho, de 2014 a 2024 (janeiro igual a junho)
        return [valor for junho in valores for valor in (junho, junho)]
    b = base({"110201": junhos([10] * 7 + [22, 32, 40, 46]),          # aumentos de 12, 10, 8 e 6: duas janelas seguidas
              "110202": junhos([10] * 7 + [10, 20, 28, 34]),          # só a última janela (10, 8 e 6)
              "110203": junhos([10] * 7 + [10, 20, 30, 40]), **fundo(3)})
    repetida = avaliar(b, "110201", T - 1)["desaceleracao"]
    assert (repetida["tendencia"], repetida["desacelera"], repetida["persistente"], repetida["anos"]) == ("CRESCIMENTO_DESACELERADO", True, True, 2)
    assert (repetida["estado"], repetida["classe"], repetida["criterio"], repetida["exploratorio"]) == ("classificado", "moderado", "por convenção", True)
    assert (repetida["valores"], repetida["de"], repetida["ate"]) == ([22, 32, 40, 46], "202106", "202406")
    # A classe é a da Análise de Tendência, pela mesma função, sem regra paralela.
    velocidades = [(10, 12), (8, 12), (6, 12)]
    assert trend.classify_pairs(velocidades)[0] == "CRESCIMENTO_DESACELERADO" and repetida["rotulo"] == trend.LABELS["CRESCIMENTO_DESACELERADO"]
    # Só no último ano: o sinal é observado, sem nível (o moderado pede a classe em 2 anos seguidos).
    uma_vez = avaliar(b, "110202", T - 1)["desaceleracao"]
    assert (uma_vez["estado"], uma_vez["classe"], uma_vez["desacelera"], uma_vez["persistente"], uma_vez["anos"]) == (
        "sinal_observado", None, True, False, 1)
    assert "desaceleracao" in avaliar(b, "110202", T - 1)["sinais"]
    constante = avaliar(b, "110203", T - 1)["desaceleracao"]
    assert (constante["estado"], constante["desacelera"], constante["tendencia"]) == ("sem_sinal", False, "CRESCIMENTO")


# --------------------------------------------------------------------------------------------- sinal 5: instabilidade
def test_instabilidade_moderado_quando_o_indice_e_raro_para_o_porte():
    # 60 municípios oscilam pouco (30 e 31); o alvo oscila muito (30 e 42).
    series = {"11" + str(1000 + k): [30 + (j + k) % 2 for j in range(T)] for k in range(60)}
    series["110200"] = [30 + 12 * (j % 2) for j in range(T)]
    b = base(series)
    alvo = avaliar(b, "110200", T - 1)["instabilidade"]
    assert (alvo["estado"], alvo["classe"], alvo["criterio"], alvo["porte"], alvo["inversoes"]) == ("classificado", "moderado", "comparado com a base", 3, 5)
    assert alvo["indice"] == pytest.approx(3.9008, abs=1e-3) and alvo["media"] == pytest.approx(36.857, abs=1e-3)
    moderado = alvo["raridade"]["niveis"]["moderado"]
    assert (moderado["avaliado"], moderado["comparacoes"], moderado["origem"], moderado["atingido"]) == (True, 915, "porte", True)
    assert set(alvo["raridade"]["niveis"]) == {"moderado"}      # o sinal 5 só tem o moderado
    comum = avaliar(b, "111000", T - 1)["instabilidade"]
    assert (comum["estado"], comum["classe"]) == ("sem_sinal", None) and comum["indice"] == pytest.approx(0.3688, abs=1e-3)
    assert "instabilidade" in avaliar(b, "110200", T - 1)["sinais"] and avaliar(b, "110200", T - 1)["dimensoes"]["ritmo"] == "moderado"
    # Abaixo de 6 médicos em média, ou sem a oscilação típica do porte (uma base em que ninguém oscila), não é calculável.
    parado = base({**fundo(120), "110200": serie((12, T))})
    assert avaliar(parado, "110200", T - 1)["instabilidade"]["estado"] == "nao_calculavel"
    assert avaliar(base({**fundo(3), "110200": serie((3, T))}), "110200", T - 1)["instabilidade"]["estado"] == "nao_calculavel"
    assert avaliar(b, "110200", 3)["instabilidade"] == {"estado": "janela_insuficiente", "classe": None}


# --------------------------------------------------------------------------------------------- estados e conjuntos
def test_estados_tem_regua_propria_e_conjuntos_ficam_sem_nivel():
    ufs = sorted(series_brasil.STATES)
    estados = {uf: serie((5000, T)) for uf in ufs}
    estados["13"] = serie((5000, 11), (4000, 1))      # cai 20% em jun/2019
    estados["35"] = serie((5000, 3), (4500, 1))       # cai 10% em jun/2015
    b = base({**fundo(4, prefixo="13"), "130260": serie((12, 11), (2, 1))}, estados=estados)
    cal = detector.calibrar(b, guardar=False)
    dos_estados = detector.calibrar(detector.base_dos_estados(b), guardar=False)
    amazonas, sao_paulo, parana, par = series_brasil.selecao(b, {"estados_unidade": ["13", "35", "41"], "conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:130260", "code:131000"]}]})
    def situacao(territorio, competencia):
        return detector.avaliar(b, cal, territorio, 0, i(competencia), P, cal_dos_estados=dos_estados)
    # A régua do estado é a base dos estados: em jun/2015, 27 comparações (o moderado pede 19; o elevado, 99).
    cedo = situacao(sao_paulo, "201506")
    assert (cedo["perda"]["estado"], cedo["perda"]["classe"], cedo["perda"]["delta"]) == ("alerta", "moderado", -500)
    assert cedo["perda"]["raridade"]["niveis"]["moderado"]["comparacoes"] == 27
    assert cedo["perda"]["sem_comparacoes"] == {"niveis": ["elevado", "critico"], "nivel": "elevado", "comparacoes": 27, "pede": 99}
    assert (cedo["alerta"]["nivel"], cedo["alerta"]["sinal"], cedo["alerta"]["criterio"]) == ("moderado", "perda", "comparado com a base")
    # Em jun/2019, 135 comparações: a queda do Amazonas é elevada; o crítico nunca tem comparações bastantes numa base de 27.
    depois = situacao(amazonas, "201906")
    assert (depois["perda"]["classe"], depois["perda"]["raridade"]["niveis"]["elevado"]["comparacoes"]) == ("elevado", 135)
    assert depois["perda"]["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 135, "pede": 999}
    assert situacao(parana, "201906")["alerta"]["estado"] == "sem_alerta"
    # Sem a régua dos estados (o histórico pede a dos municípios), o estado fica sem nível, com os fatos.
    sem_regua = detector.avaliar(b, cal, amazonas, 0, i("201906"), P)
    assert sem_regua["perda"]["estado"] == "nivel_sem_classificacao" and sem_regua["perda"]["delta"] == -1000
    # Um conjunto não tem outros iguais para comparar: os fatos, sem nível, com o motivo.
    do_par = situacao(par, "201906")
    assert (do_par["perda"]["estado"], do_par["perda"]["delta"], do_par["estrutural"]["estado"]) == ("nivel_sem_classificacao", -10, "nivel_sem_classificacao")
    assert do_par["alerta"] == {"estado": "sem_nivel", "nivel": None, "sinal": None, "criterio": None, "sinais": [], "outros": 0, "eventos": 0,
                                "motivo": "Um conjunto não tem outros iguais para comparar: a tela mostra os fatos, sem nível."}
    assert do_par["membros"] == ("code:130260", "code:131000") or do_par["membros"] == ["code:130260", "code:131000"]


# --------------------------------------------------------------------------------------------- critérios ajustáveis
def test_criterios_ajustaveis_nunca_trocam_os_padroes_em_silencio():
    padrao, personalizado = detector.parametros(None)
    assert personalizado is False and padrao == detector.PADRAO and padrao is not detector.PADRAO
    # Os padrões da tabela B.2 da Proposta V3.
    assert padrao["estrutural"] == {"critico": 1, "elevado": 3, "moderado": 5}
    assert padrao["declinio"] == {"moderado_quedas": 2, "moderado_perda": 10.0, "elevado_quedas": 3, "elevado_perda": 20.0,
                                  "critico_quedas": 4, "critico_perda": 30.0}
    assert padrao["desaceleracao"] == {"anos": 2} and padrao["instabilidade"] == {"moderado_um_em": 20}
    assert padrao["perda"] == {"moderado_um_em": 20, "elevado_um_em": 100, "critico_um_em": 1000, "moderado_minimo": 2, "moderado_fracao": 10.0,
                               "elevado_minimo": 2, "elevado_fracao": 20.0, "critico_minimo": 3, "critico_fracao": 30.0}
    assert padrao["patamar"] == {"moderado": 15.0, "critico": 30.0, "minimo": 20, "elevado_um_em": 100, "critico_um_em": 1000}
    um_em = {"moderado_um_em": 20, "elevado_um_em": 100, "critico_um_em": 1000}
    assert padrao["disponibilidade"] == padrao["posicao"] == padrao["defasagem"] == um_em and padrao["contexto"] == {"taxa_do_brasil_pct": 100.0}
    assert set(detector.EDITAVEIS) == set(detector.PADRAO) and all(set(detector.EDITAVEIS[g]) == set(detector.PADRAO[g]) for g in detector.PADRAO)
    # Trocar um valor torna a configuração exploratória; o que não foi trocado continua no padrão.
    em_uso, personalizado = detector.parametros({"perda": {"moderado_um_em": 50}, "contexto": {"taxa_do_brasil_pct": 70}})
    assert personalizado is True and em_uso["perda"]["moderado_um_em"] == 50 and em_uso["perda"]["elevado_um_em"] == 100
    assert detector.PADRAO["perda"]["moderado_um_em"] == 20
    assert detector.parametros({"perda": {"moderado_um_em": 20}})[1] is False      # o mesmo valor do padrão não é troca
    # 1 em cada 50 pede 49 comparações: com 22, o moderado deixa de ser avaliado.
    b = base({**fundo(10), "110200": serie((12, 3), (8, 2), (5, 1))})
    trocado = avaliar(b, "110200", i("201606"), p=em_uso)["perda"]
    assert (trocado["estado"], trocado["sem_comparacoes"]["nivel"], trocado["sem_comparacoes"]["pede"]) == ("sem_comparacoes", "moderado", 49)
    # Os limites dos sinais por convenção também são ajustáveis.
    ate_30, _ = detector.parametros({"estrutural": {"moderado": 30}})
    assert avaliar(b, "110200", i("201606"), p=ate_30)["estrutural"]["classe"] == "moderado"
    for ruim, trecho in (({"estrutural": {"critico": 9}}, "os limites precisam crescer"), ({"perda": {"alta_alfa": 1}}, "desconhecido"),
                         ({"perda": {"moderado_um_em": 500}}, "não pode ser mais comum"), ({"posicao": {"critico_um_em": 10}}, "não pode ser mais comum"),
                         ({"declinio": {"critico_perda": 5}}, "não pode ser menor"), ({"patamar": {"critico": 5}}, "não pode ser menor"),
                         ({"perda": {"moderado_minimo": 1.5}}, "inteiro"), ({"contexto": {"taxa_do_brasil_pct": 5}}, "de 10.0 a 500.0"),
                         ({"outro": {}}, "desconhecido"), ("texto", "inválidos")):
        with pytest.raises(ValueError, match=trecho):
            detector.parametros(ruim)


# --------------------------------------------------------------------------------------------- sinais 8 a 12
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


def _populacao_por_ano(inicial, saltos=(), parados=()):
    """Os 22 valores de uma população que cresce 1% ao ano, salta 10% nos anos de `saltos` e repete o valor nos de `parados`
    (janeiro e junho de cada ano com o mesmo valor, como na base)."""
    valores, atual = [], float(inicial)
    for ano in range(2014, 2025):
        if ano in saltos:
            atual = float(round(atual * 1.10))
        elif ano != 2014 and ano not in parados:
            atual = float(round(atual * 1.01))
        valores += [atual, atual]
    return valores


def test_janela_de_comparacao_so_em_trechos_com_populacao_comparavel():
    """Comando V23 (Parte D e seção A.3 do anexo): os trechos de população comparável vêm da própria base, olhada inteira em cada
    passagem de ano, e não de anos fixos."""
    def datas(janelas, c):
        ini, fim, motivo = janelas[c]
        return (None if ini is None else PERIODOS[ini], None if fim is None else PERIODOS[fim], motivo)
    # Uma base com a população constante é um trecho só (a taxa varia só com a contagem): toda janela com os dois junhos vale.
    b = base_comparavel({"110001": serie((10, T))})
    janelas = {c: comparativos.janela(b, i(c)) for c in PERIODOS}
    # Sem um junho, ou sem o junho de dois anos antes: janela insuficiente.
    assert datas(janelas, "201401") == (None, None, "janela_insuficiente")
    assert datas(janelas, "201406") == datas(janelas, "201501") == (None, "201406", "janela_insuficiente")
    assert datas(janelas, "201506") == (None, "201506", "janela_insuficiente")
    # De junho a junho em 2 anos, atualizada só em junho.
    assert datas(janelas, "201606") == datas(janelas, "201701") == ("201406", "201606", None)
    assert datas(janelas, "201806") == ("201606", "201806", None) and datas(janelas, "202406") == ("202206", "202406", None)
    assert comparativos.populacao_comparavel(b)["quebras"] == {} and comparativos.populacao_comparavel(b)["trechos"] == ((2014, 2024),)
    assert comparativos.trechos_comparaveis(b) == [[2014, 2024]] and comparativos.texto_dos_trechos(b) == "2014–2024"
    assert comparativos.MINIMO_DE_MEDICOS == 20
    # Quatro municípios crescem 1% ao ano; em 2018 e em 2024, todos saltam 10%; em 2022 e 2023, todos repetem o valor de 2021
    # (o desenho da população anterior à troca de 13/11/2026). O salto e a repetição na base inteira terminam o trecho.
    codigos = ("110001", "110002", "110003", "110004")
    quebrada = base_comparavel({codigo: serie((30, T)) for codigo in codigos},
                               populacoes={codigo: _populacao_por_ano(10000 * (k + 1), saltos=(2018, 2024), parados=(2022, 2023))
                                           for k, codigo in enumerate(codigos)})
    lido = comparativos.populacao_comparavel(quebrada)
    assert lido["quebras"] == {2018: "salto", 2022: "repetida", 2023: "repetida", 2024: "salto"}
    assert lido["trechos"] == ((2014, 2017), (2018, 2021), (2022, 2022), (2023, 2023), (2024, 2024))
    assert comparativos.trechos_comparaveis(quebrada) == [[2014, 2017], [2018, 2021]]
    assert comparativos.texto_dos_trechos(quebrada) == "2014–2017 e 2018–2021"
    das_quebras = {c: comparativos.janela(quebrada, i(c)) for c in PERIODOS}
    assert datas(das_quebras, "201706") == datas(das_quebras, "201801") == ("201506", "201706", None)
    assert datas(das_quebras, "202006") == ("201806", "202006", None) and datas(das_quebras, "202106") == ("201906", "202106", None)
    for fim, ini in (("201806", "201606"), ("201906", "201706"), ("202206", "202006"), ("202306", "202106"), ("202406", "202206")):
        assert datas(das_quebras, fim) == (ini, fim, "comparacao_nao_habilitada"), fim
    assert comparativos.motivo_da_janela(quebrada, i("201706"), i("201906")) == "a população de 2018 muda de patamar em boa parte da base"
    assert comparativos.motivo_da_janela(quebrada, i("202206"), i("202406")) == (
        "a população de 2023 repete a do ano anterior em boa parte da base, e a população de 2024 muda de patamar em boa parte da base")
    assert comparativos.motivo_da_janela(quebrada, i("201906"), i("202106")) is None
    # Um território parado e outro com um salto são normais e não desligam a comparação (decisão do responsável de 13/11/2026).
    normais = base_comparavel({codigo: serie((30, T)) for codigo in codigos},
                              populacoes={"110001": _populacao_por_ano(10000), "110002": 20000, "110003": _populacao_por_ano(30000, saltos=(2020,)),
                                          "110004": _populacao_por_ano(40000)})
    assert comparativos.populacao_comparavel(normais)["quebras"] == {} and comparativos.trechos_comparaveis(normais) == [[2014, 2024]]
    assert all(comparativos.janela(normais, i(c))[2] is None for c in ("201606", "202006", "202406"))


def test_percentil_e_o_posto_medio_menos_meio_sobre_n():
    percentis, n = comparativos.percentis(np.array([1.0, 2.0, 2.0, 3.0, np.nan]))
    assert n == 4 and percentis[:4].tolist() == [12.5, 50.0, 50.0, 87.5] and np.isnan(percentis[4])   # os empates no posto médio
    assert comparativos.percentis(np.array([np.nan]))[1] == 0


def _cenario_dos_relativos():
    """30 municípios de fundo com 100 médicos e 50.000 habitantes; o alvo cai de 100 para 80 em jun/2021 (a janela é de jun/2019 a
    jun/2021); um município pequeno (10 médicos) cai para 5."""
    series = {"11" + str(1000 + k): serie((100, T)) for k in range(30)}
    series["110200"] = serie((100, 15), (80, 1))
    series["110300"] = serie((10, 15), (5, 1))
    return base_comparavel(series, populacoes=50000)


def test_sinais_8_a_10_pela_raridade_da_variacao_em_dois_anos():
    b = _cenario_dos_relativos()
    e = i("202106")
    alvo = avaliar(b, "110200", e)
    taxa, posicao, referencia = alvo["disponibilidade"], alvo["posicao"], alvo["defasagem"]
    # Sinal 8: a taxa por 1.000 habitantes caiu 20% em 2 anos, com a decomposição à vista.
    assert (taxa["taxa_inicial"], taxa["taxa_final"], taxa["taxa"], taxa["populacao"]) == (2.0, 1.6, 1.6, 50000.0)
    assert taxa["variacao_pct"] == pytest.approx(-20.0) and taxa["medicos"] == {"inicial": 100.0, "final": 80.0, "variacao_pct": pytest.approx(-20.0)}
    assert taxa["populacao_da_janela"] == {"inicial": 50000.0, "final": 50000.0, "variacao_pct": 0.0}
    # Sinal 9: o percentil no universo fixo da janela; sinal 10: o índice ante os demais municípios da UF, sem o território.
    assert posicao["variacao_pp"] == pytest.approx(-46.875) and posicao["percentil"] == pytest.approx(4.6875)
    assert referencia["variacao_pontos"] == pytest.approx(-20.4609, abs=1e-3) and referencia["indice"] == pytest.approx(82.5291, abs=1e-3)
    assert referencia["referencia"]["rotulo"] == "demais municípios de Rondônia (soma municipal)"
    # A régua: as variações das janelas anteriores (de jun/2016 a jun/2020: 5 janelas × 31 municípios com 20 médicos ou mais),
    # do mesmo porte (100 a 299 médicos no início da janela). Nenhuma foi igual ou pior: 1 ÷ 156, elevado; o crítico pede 999.
    for sinal in (taxa, posicao, referencia):
        assert (sinal["estado"], sinal["classe"], sinal["criterio"], sinal["porte"]) == ("classificado", "elevado", "comparado com a base", 5)
        assert sinal["raridade"]["niveis"]["elevado"] == {"avaliado": True, "comparacoes": 155, "pede": 99, "um_em": 100.0, "origem": "porte",
                                                          "raridade": pytest.approx(1 / 156), "atingido": True}
        assert sinal["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 155, "pede": 999}
    # Um nível por território: o maior entre os sinais, sem soma. Os quatro vêm da mesma queda e contam como um evento.
    assert alvo["alerta"] == {"estado": "alerta", "nivel": "elevado", "sinal": "perda", "criterio": "comparado com a base", "outros": 3,
                              "sinais": [{"sinal": chave, "nivel": "elevado", "criterio": "comparado com a base"}
                                         for chave in ("perda", "disponibilidade", "posicao", "defasagem")],
                              "eventos": 1, "mesma_queda": ["perda", "disponibilidade", "posicao", "defasagem"]}
    assert alvo["dimensoes"] == {"estrutural": None, "trajetoria": "elevado", "ritmo": None, "comparacao": "elevado", "contexto": None}
    assert detector.por_que(b, alvo, e, P) == "Caiu de 100 para 80 (−20,0%) (+3 sinais)"
    assert not {"indice_geral", "escore", "pontuacao", "nota"} & set(alvo)
    # Quem não mudou: avaliado, sem alerta. Com menos de 20 médicos no início da janela: só descritivo.
    parado = avaliar(b, "111000", e)
    assert [parado[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem")] == ["sem_sinal"] * 3
    assert parado["alerta"]["estado"] == "sem_alerta" and parado["disponibilidade"]["raridade"]["niveis"]["moderado"]["raridade"] == 1.0
    pequeno = avaliar(b, "110300", e)
    assert [pequeno[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem")] == ["descritivo"] * 3
    assert pequeno["disponibilidade"]["variacao_pct"] == pytest.approx(-50.0) and pequeno["disponibilidade"]["classe"] is None
    # Na primeira janela da base não há variações anteriores: "sem comparações suficientes", com o nível da data à vista.
    primeira = avaliar(b, "110200", i("201606"))
    assert [primeira[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem")] == ["sem_comparacoes"] * 3
    assert primeira["disponibilidade"]["sem_comparacoes"] == {"niveis": ["moderado", "elevado", "critico"], "nivel": "moderado",
                                                             "comparacoes": 0, "pede": 19}
    # O território, que não caiu no último registro e foi comparado com a base nesse sinal, fica sem alerta; os sinais sem
    # comparações aparecem na linha dele.
    assert primeira["disponibilidade"]["taxa"] == 2.0 and (primeira["perda"]["estado"], primeira["perda"]["avaliavel"]) == ("sem_perda", True)
    assert (primeira["alerta"]["estado"], primeira["alerta"]["sem_comparacoes"]) == ("sem_alerta", ["disponibilidade", "posicao", "defasagem"])
    # Antes de haver dois anos de registros anuais, janela insuficiente nos três.
    cedo = avaliar(b, "110200", i("201506"))
    assert [cedo[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem")] == ["janela_insuficiente"] * 3
    # A régua guarda, por versão da base, a variação de cada janela e as comparações dela.
    regua = comparativos.regua_relativa(b, "municipios", guardar=False)
    assert len(regua.unidades) == 32 and sorted(set(regua.porte[:, e].tolist())) == [-1, 5]
    assert [PERIODOS[k] for k in range(T) if np.isfinite(regua.valor["disponibilidade"][:, k]).any()] == [
        str(ano) + "06" for ano in range(2016, 2025)]


def test_textos_de_um_sinal_uma_frase_o_entenda_e_a_explicacao_completa():
    b = _cenario_dos_relativos()
    e = i("202106")
    av = avaliar(b, "110200", e)
    itens = detector.fenomenos(b, av, e, P)
    # Os 12 sinais (1 e 2 juntos), na ordem da tela, nos quatro grupos mais "Juntos".
    assert [(item["numero"], item["chave"], item["grupo"]) for item in itens] == [
        ("1–2", "estrutural", "quantos"), ("3", "declinio", "mudou"), ("4", "desaceleracao", "mudou"), ("5", "instabilidade", "mudou"),
        ("6", "perda", "mudou"), ("7", "patamar", "mudou"), ("8", "disponibilidade", "comparado"), ("9", "posicao", "comparado"),
        ("10", "defasagem", "comparado"), ("11", "contexto", "onde"), ("12", "coexistencia", "juntos")]
    assert [item["nome"] for item in itens] == [
        "Poucos médicos ou nenhum médico registrado", "Declínio persistente", "Desaceleração", "Instabilidade", "Queda recente",
        "Abaixo do que já teve", "Menos médicos por habitante", "Perda de posição", "Mais longe da referência", "Distância", "Sinais juntos"]
    campos = {"chave", "numero", "nome", "grupo", "dimensao", "nivel", "estado_do_nivel", "criterio_do_nivel", "situacao", "entenda",
              "exploratorio", "sem_comparacoes", "observado", "criterio", "habitual", "significa", "nao_significa", "limitacoes", "qualidade",
              "estado", "classe"}   # `estado` e `classe`: os campos que a resposta já trazia (a classe é o nível)
    assert all(set(item) == campos and all(item[campo] for campo in ("situacao", "observado", "criterio", "habitual", "significa",
                                                                      "nao_significa", "limitacoes", "qualidade")) for item in itens)
    assert all(item["entenda"]["texto"] and item["entenda"]["exemplo"] for item in itens)
    queda = texto_do(b, av, e, "perda")
    assert (queda["nivel"], queda["estado_do_nivel"], queda["criterio_do_nivel"]) == ("elevado", "alerta", "comparado com a base")
    assert queda["situacao"] == "Caiu de 100 para 80 (−20,0%)"
    assert queda["observado"] == "De jan/2021 a jun/2021 (5 meses), passou de 100 para 80 médicos (−20, −20,0%)."
    # Com quem foi comparado e quantos casos havia; e o nível que a base ainda não sustenta, com os números.
    assert queda["habitual"] == (
        "Comparado com a base: entre 217 mudanças anteriores de municípios de 100 a 299 médicos, nenhuma foi igual ou pior (raridade de 1 em "
        "cada 218). Para este porte, o tamanho mínimo é de 10 médicos (moderado), 20 (elevado) e 30 (crítico). A base ainda não tem história "
        "para dizer se esta queda chega ao nível crítico: são 217 comparações, e o crítico pede 999.")
    # Ao lado do nível, a tela diz o que a base ainda não sustenta em cada sinal comparado com ela.
    assert queda["sem_comparacoes"] == {"niveis": ["critico"], "nivel": "critico", "comparacoes": 217, "pede": 999,
                                        "texto": "Sem comparações suficientes para o crítico: há 217, e ele pede 999."}
    assert [(item["chave"], item["sem_comparacoes"]["comparacoes"]) for item in itens if item["sem_comparacoes"]] == [
        ("perda", 217), ("disponibilidade", 155), ("posicao", 155), ("defasagem", 155)]
    assert queda["entenda"] == {
        "texto": "Compara a queda do último registro com as mudanças que já aconteceram em territórios do mesmo tamanho. É alerta quando a "
                 "queda é rara e tem um tamanho mínimo. \"Raro\" quer dizer incomum nesta base, não comprovadamente pior.",
        "exemplo": "Uma queda de 2 para 1 médico não vira alerta de queda, porque é só 1: ela aparece como crítico em \"Poucos médicos\"."}
    assert "Raridade = (mudanças anteriores iguais ou piores + 1) ÷ (total + 1)" in queda["criterio"]
    assert "Moderado: queda rara (1 em cada 20) e de pelo menos 2 médicos e 10% do que havia" in queda["criterio"]
    taxa = texto_do(b, av, e, "disponibilidade")
    assert taxa["situacao"] == "−20,0% de médicos por habitante em 2 anos" and taxa["nivel"] == "elevado"
    assert taxa["observado"] == ("De jun/2019 a jun/2021, a taxa passou de 2,00 para 1,60 por 1.000 habitantes (−20,0%). O número de médicos "
                                 "passou de 100 para 80 (−20,0%), e a população, de 50.000 para 50.000 (0,0%).")
    assert taxa["habitual"].startswith("Comparado com a base: entre 155 variações anteriores de municípios de 100 a 299 médicos, nenhuma foi "
                                       "igual ou pior (raridade de 1 em cada 156).")
    assert texto_do(b, av, e, "posicao")["situacao"] == "−46,9 pontos de percentil em 2 anos"
    assert texto_do(b, av, e, "defasagem")["situacao"] == "−20,5 pontos no índice ante a referência em 2 anos"
    juntos = texto_do(b, av, e, "coexistencia")
    assert (juntos["nivel"], juntos["estado_do_nivel"], juntos["numero"]) == (None, "juntos", "12")
    assert juntos["situacao"] == ("4 sinais com nível: queda recente (elevado), menos médicos por habitante (elevado), perda de posição "
                                  "(elevado) e mais longe da referência (elevado)")
    assert juntos["habitual"] == ("O alerta do território é o maior nível: elevado. Os níveis não se somam. 4 desses sinais vêm da mesma "
                                  "queda e contam como um evento.")
    # O sinal 4 é exploratório e diz que não indica o que vem depois; o 11 nunca usa "isolamento" nem "desassistência".
    ritmo = texto_do(b, av, e, "desaceleracao")
    assert ritmo["exploratorio"] is True and "não indica o que vem depois" in ritmo["entenda"]["texto"]
    assert ritmo["situacao"] == "Sem desaceleração (tendência: declínio)"
    # Sem parênteses dentro de parênteses: a contagem vem numa frase própria.
    assert texto_do(b, av, e, "estrutural")["observado"] == (
        "Em jun/2021, o município tinha 80 médicos; em jan/2021, 100. Contagem: médicos registrados no município (fonte municipal; quem "
        "atua em mais de um município conta em cada um).")
    assert texto_do(b, av, e, "declinio")["situacao"] == "1 queda anual: −20,0% desde jun/2020"
    tudo = " ".join(str(item[campo]) for item in itens for campo in ("situacao", "observado", "criterio", "habitual", "significa",
                                                                      "nao_significa", "entenda")).lower()
    for proibido in ("desassist", "isolad", "isolamento", "sem cobertura", "recomenda", "deveria", "criticidade", "vazio assistencial",
                     "atenção,", "intensidade"):
        assert proibido not in tudo, proibido
    # Sem alerta e sem comparações: o estado do nível diz qual é o caso.
    sem = texto_do(b, avaliar(b, "110200", i("201606")), i("201606"), "disponibilidade")
    assert (sem["nivel"], sem["estado_do_nivel"]) == (None, "sem_comparacoes")
    assert sem["habitual"] == ("A base ainda não tem história para dizer se esta queda da taxa chega ao nível moderado, elevado ou crítico: "
                               "são 0 comparações, e o moderado pede 19.")
    assert sem["sem_comparacoes"]["texto"] == "Sem comparações suficientes para o moderado, o elevado e o crítico: há 0, e o moderado pede 19."
    # Os "Entenda" da primeira tela (seção A.4): duas ou três frases e um exemplo com números, com os nomes da base.
    da_tela = detector.entenda_da_ferramenta(b)
    assert sorted(da_tela) == ["alerta", "ferramenta", "termos"] and all(item["texto"] and item["exemplo"] for item in da_tela.values())
    assert da_tela["ferramenta"]["exemplo"] == ("Uma queda de 18 para 11 médicos é rara quando, entre as mudanças anteriores de municípios de 10 a "
                                                "19 médicos, só 1 em cada 100 foi igual ou pior: alerta elevado.")
    assert da_tela["alerta"]["exemplo"] == ("Moderado: 1 em cada 20, com pelo menos 19 comparações. Elevado: 1 em cada 100, com 99. Crítico: 1 em "
                                            "cada 1.000, com 999.")
    assert da_tela["termos"]["texto"].startswith("Porte é o tamanho do território, pelo número de médicos; patamar, o melhor período")
    # Duas ou três frases simples em cada "Entenda", na primeira tela e em cada sinal.
    assert all(2 <= texto.count(". ") + 1 <= 3 for texto in [item["texto"] for item in da_tela.values()] + [item["entenda"]["texto"] for item in itens])


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
    # Só contexto: nunca vira alerta, e não é juízo sobre o atendimento.
    av = avaliar(b, "210003", e)
    assert av["dimensoes"]["contexto"] is None and "contexto" not in av["sinais"] and "classe" not in av["contexto"]
    texto = texto_do(b, av, e, "contexto")
    assert texto["numero"] == "11" and texto["situacao"] == "A 334 km de M210001, em linha reta"
    assert texto["observado"] == ("O território fica a 334 km, em linha reta, de M210001 (3,00 por 1.000 habitantes), o mais próximo com taxa "
                                  "igual ou maior que 2,00 médicos por 1.000 habitantes em jun/2024 (100% da taxa do Brasil, de 2,00).")
    assert texto["habitual"] == "A distância é maior que a de 75% dos territórios abaixo do critério. Só contexto, sem nível."
    assert (texto["nivel"], texto["estado_do_nivel"], texto["criterio_do_nivel"]) == (None, "contexto", None)
    assert texto["nao_significa"].startswith("Não é distância por estrada, tempo de viagem nem acesso.") and "nunca vira alerta" in texto["criterio"]
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


def test_sinais_juntos_sem_soma_e_sem_indice_geral():
    def chaves(sinais, classe):
        saida = comparativos.coexistencia(sinais, classe)
        return saida["estado"], [c["chave"] for c in saida["combinacoes"]], saida["repercussoes"], saida["frentes"]
    assert chaves(["estrutural", "perda"], "elevado") == ("sinais_combinados", ["estrutural_e_perda"], ["perda no último registro"],
                                                         ["condição estrutural", "queda no número de médicos"])
    assert chaves(["estrutural", "perda"], "moderado")[:2] == ("sem_combinacao", [])     # pede o nível elevado ou crítico
    assert chaves(["patamar"], "moderado")[:2] == ("sinais_combinados", ["patamar_e_estrutural"])
    assert chaves(["declinio", "posicao"], None)[:2] == ("sinais_combinados", ["declinio_e_relativa"])
    assert chaves(["estrutural", "declinio", "perda", "patamar"], "critico")[1] == ["estrutural_e_perda", "estrutural_e_declinio", "patamar_e_estrutural"]
    # Os efeitos da mesma queda não são evidências independentes: cinco repercussões, uma frente de sinal, nenhuma combinação.
    efeitos = chaves(["perda", "patamar", "disponibilidade", "posicao", "defasagem"], None)
    assert efeitos[0] == "sem_combinacao" and len(efeitos[2]) == 5 and efeitos[3] == ["queda no número de médicos"]
    assert chaves([], None) == ("sem_combinacao", [], [], [])
    # Sem população na base, os sinais 8 a 11 dizem por que não são calculados; os sinais 1 a 7 não mudam.
    b = base({"110001": serie((3, 5), (1, 1)), "110002": serie((2, T))})
    av = avaliar(b, "110001", 5)
    assert av["coexistencia"]["estado"] == "sinais_combinados" and av["sinais"] == ["estrutural", "perda", "combinados"]
    assert av["dimensoes"] == {"estrutural": "critico", "trajetoria": None, "ritmo": None, "comparacao": None, "contexto": None}
    assert [av[chave]["estado"] for chave in ("disponibilidade", "posicao", "defasagem", "contexto")] == ["nao_calculavel"] * 4
    so_ate_o_7 = detector.avaliar(b, detector.calibrar(b, guardar=False), series_brasil.municipio(b, "110001"), 0, 5, P, comparar=False)
    assert not {"disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"} & set(so_ate_o_7)
    assert so_ate_o_7["sinais"] == ["estrutural", "perda"] and so_ate_o_7["estrutural"] == av["estrutural"]


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


def test_rota_do_detector_lista_detalhe_e_recusas(catalogo, monkeypatch):
    monkeypatch.setattr(main, "llm_interpret", lambda *a, **k: (_ for _ in ()).throw(AssertionError("o Detector não usa o provedor de IA")))
    body = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "estados_unidade": ["15"],
                        "conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:130260", "code:130420"], "versao": 2}]}))
    assert body["versao"] == detector.VERSION == "DETECTOR-SINAIS/V3/1" and body["fonte"]["categoria"] == "MEDICINA" and body["exploratorio"] is False
    assert (body["fonte"]["primeira"], body["fonte"]["ultima"], body["fonte"]["competencias"]) == ("201401", "202406", 22)
    assert body["fonte"]["rotulos"] == {"profissional": "médico", "profissionais": "médicos", "unidade": "município", "unidades": "municípios",
                                        "grupo": "estado", "grupos": "estados", "todo": "Brasil"}
    assert body["janela"] == {"inicio": "201401", "fim": "202406", "registros": 22, "meses": 125, "padrao": True,
                              "ultimo_registro_da_base": "202406", "e_o_ultimo": True}
    assert body["competencias"] == list(PERIODOS) and body["parametros"]["padrao"] == detector.PADRAO
    # Os níveis, os grupos dos sinais e os portes vêm do motor: a tela não repete a regra.
    assert body["niveis"] == [{"chave": "moderado", "nome": "Moderado", "um_em": 20, "pede": 19},
                              {"chave": "elevado", "nome": "Elevado", "um_em": 100, "pede": 99},
                              {"chave": "critico", "nome": "Crítico", "um_em": 1000, "pede": 999}]
    assert [(grupo["chave"], grupo["nome"], grupo["sinais"]) for grupo in body["grupos"]] == [
        ("quantos", "Quantos há", ["estrutural"]), ("mudou", "Como mudou", ["declinio", "desaceleracao", "instabilidade", "perda", "patamar"]),
        ("comparado", "Comparado com outros", ["disponibilidade", "posicao", "defasagem"]), ("onde", "Onde fica", ["contexto"]),
        ("juntos", "Juntos", ["coexistencia"])]
    assert body["portes"] == list(detector.ROTULOS_DOS_PORTES) and len(body["portes"]) == 10
    assert sorted(body["entenda"]) == ["alerta", "ferramenta", "termos"] and "própria base" in body["entenda"]["ferramenta"]["texto"]
    linhas = {linha["id"]: linha for linha in body["linhas"]}
    assert list(linhas) == ["code:130260", "code:130340", "code:130420", "uf:15", "c1"]
    # Um alerta por território: o nível, o sinal principal, o tipo de critério e o porquê.
    tefe = linhas["code:130420"]  # zero confirmado há 12 registros: crítico, pelo sinal 2
    assert (tefe["rotulo"], tefe["estrutural"]["classe"], tefe["estrutural"]["n"], tefe["estrutural"]["zeros"]) == ("TEFE (AM)", "critico", 0, 12)
    assert tefe["alerta"] == {"estado": "alerta", "nivel": "critico", "sinal": "ausencia", "criterio": "por convenção", "outros": 0,
                              "por_que": "Nenhum médico registrado há 12 registros, desde jan/2019",
                              "sinais": [{"sinal": "ausencia", "nivel": "critico", "criterio": "por convenção"}], "mesma_queda": [],
                              "sem_comparacoes": [], "motivo": None}
    assert {"estrutural", "ausencia"} <= set(tefe["sinais"]) and tefe["dimensoes"]["estrutural"] == "critico"
    parintins = linhas["code:130340"]   # 20 médicos até jun/2019 e 12 depois: 40% abaixo do patamar, moderado por convenção
    # `critica` e `sinal` são campos que a resposta já trazia (V22), com os valores da V3: os 4 últimos registros cumprem o limite
    # do crítico, e a base não tem comparações para ele; o `sinal` repete o nível.
    assert parintins["patamar"] == {"estado": "classificado", "classe": "moderado", "patamar": 20.0, "diferenca_pct": -40.0, "abaixo": True,
                                    "critica": "sem_comparacoes"}
    assert parintins["declinio"] == {"estado": "sem_sinal", "classe": None, "reducoes": 0, "perda_pct": None, "sinal": None}
    assert (parintins["alerta"]["nivel"], parintins["alerta"]["sinal"], parintins["alerta"]["criterio"], parintins["alerta"]["por_que"]) == (
        "moderado", "patamar", "por convenção", "40% abaixo do que já teve (patamar de 20)")
    # Manaus cresce: avaliado nos sinais 8 e 9, sem alerta; o que ficou sem comparações aparece na linha.
    manaus = linhas["code:130260"]
    assert manaus["disponibilidade"] == {"estado": "sem_sinal", "classe": None, "taxa": 51.0, "populacao": 1000.0,
                                         "variacao_pct": pytest.approx(100 * (51 / 47 - 1)), "sinal": None}
    assert manaus["posicao"] == {"estado": "sem_sinal", "classe": None, "percentil": 87.5, "universo": 4, "variacao_pp": pytest.approx(25.0),
                                 "sinal": None}
    # A régua da data continua trazendo as chaves anteriores, ao lado das novas.
    da_faixa, do_patamar = body["calibracao"]["perda"][1], body["calibracao"]["patamar"][0]
    assert (da_faixa["porte"], da_faixa["transicoes"], da_faixa["comparacoes"], da_faixa["queda_incomum_pct"], da_faixa["alta"], da_faixa["critica"]) == (
        "4 a 9", 0, 0, None, "sem_calibracao", "sem_calibracao")
    assert (do_patamar["porte"], do_patamar["observacoes"], do_patamar["comparacoes"], do_patamar["afastamento_incomum_pct"], do_patamar["alta"]) == (
        "20 a 49", 24, 24, None, "sem_calibracao")
    assert body["calibracao"]["monitoramento"] == {"avaliadas": 3, "raras": 0, "incomuns": 0, "taxa_pct": 0.0, "esperado_pct": 5.0,
                                                   "aviso_da_base": False}
    assert manaus["defasagem"]["indice"] == pytest.approx(100 * 51 / 6) and manaus["defasagem"]["estado"] == "sem_comparacoes"
    assert (manaus["alerta"]["estado"], manaus["alerta"]["nivel"], manaus["alerta"]["sem_comparacoes"]) == ("sem_alerta", None, ["defasagem"])
    # O estado como unidade usa a régua dos estados: com dois estados na base, os sinais 8 a 10 não têm comparações (aparecem na
    # linha); o último registro, sem queda, foi comparado com as 20 mudanças anteriores da faixa: sem alerta.
    para = linhas["uf:15"]
    assert (para["tipo"], para["rotulo"], para["estrutural"]["estado"]) == ("estado", "Pará (PA)", "sem_sinal")
    assert (para["alerta"]["estado"], para["alerta"]["sem_comparacoes"]) == ("sem_alerta", ["disponibilidade", "posicao", "defasagem"])
    assert body["calibracao_dos_estados"]["perda"][3]["comparacoes"] == 20      # a faixa de 20 a 49: os dois estados, em 10 datas
    # O conjunto não tem nível: os fatos e o motivo.
    par = linhas["c1"]
    assert (par["tipo"], par["membros"], par["ultima"]["valor"], par["ids_dos_membros"]) == ("conjunto", 2, 51, ["code:130260", "code:130420"])
    assert (par["alerta"]["estado"], par["alerta"]["nivel"]) == ("sem_nivel", None) and par["alerta"]["motivo"].startswith("Um conjunto não tem outros iguais")
    assert par["disponibilidade"]["taxa"] == pytest.approx(1000 * 51 / 2000) and par["posicao"]["estado"] == "nao_aplicavel"
    # O resumo dos níveis, que a tela mostra no alto e usa como filtro: um nível por território.
    assert body["resumo"]["por_tipo"] == {"municipio": 3, "estado": 1, "conjunto": 1}
    assert body["resumo"]["niveis"] == {"critico": 1, "elevado": 0, "moderado": 1, "sem_alerta": 2, "sem_comparacoes": 0, "sem_nivel": 1}
    assert body["resumo"]["com_nivel"]["ausencia"] == body["resumo"]["com_nivel"]["patamar"] == 1 and body["resumo"]["com_nivel"]["perda"] == 0
    assert body["aviso_da_base"] is None and body["calibracao"]["monitoramento"]["aviso_da_base"] is False
    assert body["limitacoes"] == ["RARO_E_INCOMUM_NA_BASE", "CONJUNTO_SEM_NIVEL", "COMPARACAO_SO_COM_POPULACAO_COMPARAVEL"]
    assert any("Um nível por território" in nota for nota in body["notas"]) and any("régua própria" in nota for nota in body["notas"])
    # Os sinais 8 a 12: a população do catálogo é constante (um trecho só, lido da própria base).
    assert body["comparacao"] == {"de": "202206", "ate": "202406", "estado": "comparavel", "trechos": [[2014, 2024]], "motivo": None,
                                  "minimo_de_medicos": 20, "contexto": {"taxa_minima": 25.0, "taxa_do_brasil": 25.0, "pct_da_taxa_do_brasil": 100.0,
                                                                        "atendem": 2, "universo": 2}}
    assert manaus["contexto"] == {"estado": "atende_ao_criterio", "distancia_km": None, "referencia": None, "referencia_id": None, "percentil": None}
    assert (parintins["contexto"]["estado"], parintins["contexto"]["referencia"], parintins["contexto"]["percentil"]) == ("contexto", "MANAUS (AM)", 25.0)
    assert parintins["contexto"]["distancia_km"] == pytest.approx(333.504, abs=1e-3)
    assert body["coordenadas"] == {"code:130260": [-3.0, -60.0], "code:130340": [-3.0, -57.0], "code:130420": [-3.0, -65.0]}
    # A janela escolhida entre as competências reais: a situação é a do fim dela; o registro ausente não é zero.
    janela = corpo(pedir({"base": {"municipios": {"ids": ["code:130340"]}}, "janela": {"inicio": "201406", "fim": "201501"}}))
    assert janela["janela"]["padrao"] is False and (janela["janela"]["registros"], janela["janela"]["meses"]) == (2, 7)
    assert janela["linhas"][0]["estrutural"]["estado"] == "ausencia_de_dado" and janela["linhas"][0]["ultima"] == {
        "competencia": "201406", "valor": 20, "na_data": False}
    assert janela["resumo"]["sem_registro_na_data"] == 1
    # Os detalhes de um território: a série, o histórico e, em cada sinal, o nível, uma frase, o "Entenda" e a explicação.
    detalhe = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "detalhe": "code:130340"}))
    assert detalhe["territorio"]["id"] == "code:130340" and len(detalhe["serie"]) == 22 and len(detalhe["historico"]) == 22
    assert detalhe["serie"][2] == {"competencia": "201501", "valor": None, "estado": "ausencia_de_dado"}
    assert detalhe["linha"]["alerta"] == parintins["alerta"]
    assert [(item["numero"], item["nivel"], item["estado_do_nivel"]) for item in detalhe["fenomenos"]][:6] == [
        ("1–2", None, "sem_alerta"), ("3", None, "sem_alerta"), ("4", None, "sem_alerta"), ("5", None, "nao_avaliado"), ("6", None, "sem_alerta"),
        ("7", "moderado", "alerta")]
    do_patamar = next(item for item in detalhe["fenomenos"] if item["chave"] == "patamar")
    assert do_patamar["situacao"] == "40% abaixo do que já teve (patamar de 20)" and do_patamar["criterio_do_nivel"] == "por convenção"
    assert "A base ainda não tem história para dizer se este afastamento chega ao nível elevado ou crítico: são 38 comparações, e o elevado pede 99." in do_patamar["habitual"]
    assert detalhe["historico"][-1] == {"competencia": "202406", "valor": 12, "alerta": "moderado", "estrutural": None, "perda": None,
                                        "patamar": {"estado": "classificado", "classe": "moderado", "diferenca_pct": -40.0},
                                        "instabilidade": None, "declinio": {"reducoes": 0, "classe": None, "sinal": None},
                                        "desaceleracao": {"desacelera": False, "classe": None, "rotulo": "Sem classificação"}}
    comparativo = detalhe["comparativo"]
    assert comparativo["competencias"] == list(PERIODOS) and comparativo["trechos"] == [[2014, 2024]]
    assert (comparativo["taxa"][0], comparativo["taxa"][2], comparativo["taxa"][-1]) == (20.0, None, 12.0)   # o registro ausente não é zero
    assert comparativo["referencia"]["rotulo"] == "demais municípios do Amazonas (soma municipal)"
    assert set(detalhe["coordenadas"]) == {"code:130340", "code:130260"}   # o território e o município de referência do contexto
    # Trocar um critério torna a configuração exploratória, com a limitação e a nota; os padrões continuam na resposta.
    exploratorio = corpo(pedir({"base": {"municipios": {"estados": ["13"]}}, "parametros": {"estrutural": {"moderado": 30}}}))
    assert exploratorio["exploratorio"] is True and exploratorio["limitacoes"][-1] == "CONFIGURACAO_EXPLORATORIA"
    assert exploratorio["parametros"]["personalizados"] is True and exploratorio["parametros"]["padrao"] == detector.PADRAO
    assert [(linha["id"], linha["alerta"]["nivel"], linha["alerta"]["sinal"]) for linha in exploratorio["linhas"]] == [
        ("code:130260", None, None), ("code:130340", "moderado", "estrutural"), ("code:130420", "critico", "ausencia")]
    assert any(nota.startswith("Configuração exploratória") for nota in exploratorio["notas"])
    # Recusas: critérios fora de ordem, chaves antigas, território fora da seleção e opção desconhecida.
    recusa(pedir({"base": {"municipios": {"estados": ["13"]}}, "parametros": {"estrutural": {"critico": 9}}}), "os limites precisam crescer")
    recusa(pedir({"base": {"municipios": {"estados": ["13"]}}, "parametros": {"perda": {"alta_alfa": 1}}}), "Parâmetro do Detector desconhecido")
    recusa(pedir({"base": {"municipios": {"estados": ["13"]}}, "detalhe": "code:150140"}), "fora da seleção")
    recusa(pedir({"base": {"municipios": {"estados": ["13"]}}, "outra": 1}), "Opção desconhecida")
    # As recusas que a rota já dava: seleção vazia, território ou competência fora da base e janela invertida.
    recusa(pedir({}), "Nenhum território na seleção")
    recusa(pedir({"base": {"municipios": {"ids": ["code:999999"]}}}), "Território fora da base Brasil")
    recusa(pedir({"base": {"municipios": {"todos": True}}, "janela": {"inicio": "202406", "fim": "201401"}}), "o início vem depois do fim")
    recusa(pedir({"base": {"municipios": {"todos": True}}, "janela": {"fim": "202407"}}), "Competência fora da base")
    # Só a base do Brasil: sem ela, ou com uma planilha enviada, a rota recusa (a recusa que a resposta já dava).
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


def test_real_regua_da_queda_recente_taxas_de_alerta_por_nivel_e_por_porte(real):
    """Critérios de aceitação do comando V23 (seção 7): na base do Brasil, moderado em cerca de 4,5% das avaliações; nas faixas
    acima de 300, 5,1%, 4,4%, 4,9% e 3,2%; e o crítico "sem comparações suficientes" de 3.000 médicos para cima. É a régua em
    uso (só a raridade, sem o tamanho mínimo), com as descontinuidades de registro fora do passado de cada data."""
    assert len(real.codigos) == 5570 and real.periodos == PERIODOS and np.diff(real.meses).tolist() == [5, 7] * 10 + [5]
    cal = detector.calibrar(real)
    assert len({linha for linha, _ in np.argwhere(cal.marca == 1)}) == 10                    # os 10 municípios com pico que volta
    assert {real.prefixos[linha] for linha, _ in np.argwhere(cal.quebra)} == {"53"}          # a quebra de fonte só no Distrito Federal
    c = reguas.Comparacoes(*(cal.c_perda[origem][cal.regular].astype(np.int64) for origem in range(6)), theta=np.empty(0))
    niveis, porte = reguas.niveis_em_vetor(c), cal.porte[cal.regular]

    def taxa(nivel, minimo, faixa=None):
        n = np.where(c.n_porte >= minimo, c.n_porte, c.n_vizinhas)
        if nivel == 1:
            n = np.where(n >= minimo, n, c.n_todas)
        avaliadas = (n >= minimo) & (True if faixa is None else porte == faixa)
        return int(avaliadas.sum()), 100.0 * int((avaliadas & (niveis >= nivel)).sum()) / max(int(avaliadas.sum()), 1)
    assert taxa(1, 19) == (105786, pytest.approx(4.50, abs=0.05))
    assert taxa(2, 99) == (105725, pytest.approx(0.88, abs=0.05)) and taxa(3, 999) == (103836, pytest.approx(0.08, abs=0.03))
    assert [taxa(1, 19, faixa)[1] for faixa in range(10)] == pytest.approx([2.53, 4.14, 4.67, 4.97, 5.95, 5.45, 5.13, 4.40, 4.88, 3.19], abs=0.01)
    assert taxa(1, 19, 9)[0] == 94
    # De 3.000 médicos para cima, a base não tem 999 comparações de tamanho parecido (nem com as faixas vizinhas): o crítico
    # nunca é avaliado.
    assert [taxa(3, 999, faixa)[0] for faixa in (7, 8, 9)] == [796, 0, 0]
    grandes = cal.porte >= 8
    assert int(cal.c_perda[1][grandes].max()) == 203 and int(cal.c_perda[3][grandes].max()) == 864 < 999


def test_real_regua_dos_estados_moderado_desde_2015_elevado_desde_2019_critico_nunca(real):
    cal = detector.calibrar_estados(real)
    assert int(cal.regular.sum()) == 567 and len(detector.base_dos_estados(real).codigos) == 27
    c = reguas.Comparacoes(*(cal.c_perda[origem][cal.regular].astype(np.int64) for origem in range(6)), theta=np.empty(0))
    niveis, tempo = reguas.niveis_em_vetor(c), np.nonzero(cal.regular)[1]

    def desde(minimo, com_todas):
        n = np.where(c.n_porte >= minimo, c.n_porte, c.n_vizinhas)
        if com_todas:
            n = np.where(n >= minimo, n, c.n_todas)
        datas = sorted(set(tempo[n >= minimo].tolist()))
        return (PERIODOS[datas[0]] if datas else None), int((n >= minimo).sum())
    assert desde(19, True) == ("201506", 513) and desde(99, False) == ("201906", 275) and desde(999, False) == (None, 0)
    assert int((niveis >= 1).sum()) == 37 and int((niveis >= 2).sum()) == 0          # 7,2% de moderados; nenhum elevado
    assert int(cal.c_perda[5][:, -1].max()) == 270                                   # as comparações dos estados em jun/2024
    # Na rota: os 27 estados como unidade em jun/2024, com a régua própria.
    body = corpo(pedir({"estados_unidade": sorted(real.estados)}))
    assert body["resumo"]["niveis"] == {"critico": 0, "elevado": 0, "moderado": 3, "sem_alerta": 24, "sem_comparacoes": 0, "sem_nivel": 0}
    assert "calibracao_dos_estados" in body and all(linha["tipo"] == "estado" for linha in body["linhas"])


def test_real_lista_inteira_um_nivel_por_territorio(real):
    body = corpo(pedir({"base": {"municipios": {"todos": True}}}))
    assert body["resumo"]["territorios"] == 5570 and body["fonte"]["categoria"] == "MEDICINA"
    assert body["resumo"]["niveis"] == {"critico": 41, "elevado": 434, "moderado": 977, "sem_alerta": 4118, "sem_comparacoes": 0, "sem_nivel": 0}
    assert body["resumo"]["com_nivel"] == {"estrutural": 801, "ausencia": 0, "declinio": 155, "desaceleracao": 16, "instabilidade": 260,
                                           "perda": 155, "patamar": 136, "disponibilidade": 107, "posicao": 178, "defasagem": 134}
    assert body["resumo"]["sinais"]["desaceleracao"] == 182 and body["resumo"]["sinais"]["ausencia"] == 0
    assert sum(1 for linha in body["linhas"] if linha["desaceleracao"]["persistente"]) == 16
    assert all(linha["alerta"]["criterio"] in ("por convenção", "comparado com a base") and linha["alerta"]["por_que"]
               for linha in body["linhas"] if linha["alerta"]["nivel"])
    # A régua da data, por porte: as dez faixas, com as comparações e a queda a partir da qual cada nível é raro.
    regua = body["calibracao"]["perda"]
    assert [celula["porte"] for celula in regua] == list(detector.ROTULOS_DOS_PORTES)
    assert [celula["comparacoes"] for celula in regua] == [6572, 16650, 12035, 9958, 3969, 3708, 1901, 616, 203, 45]
    assert all(celula["moderado"]["queda_pct"] is not None for celula in regua)
    assert [celula["critico"]["queda_pct"] is None for celula in regua] == [False] * 7 + [True] * 3
    assert regua[9]["elevado"]["queda_pct"] is None and regua[6]["moderado"]["queda_pct"] == pytest.approx(5.9, abs=0.1)
    assert body["calibracao"]["monitoramento"]["taxa_pct"] == pytest.approx(2.89, abs=0.01) and body["aviso_da_base"] is None
    # Na primeira data com transição (jun/2014), a base ainda não tem mudanças anteriores: a queda fica "sem comparações
    # suficientes", com o fato à vista; os sinais por convenção continuam valendo.
    cedo = corpo(pedir({"base": {"municipios": {"todos": True}}, "janela": {"fim": "201406"}}))
    assert not any(linha["perda"]["classe"] for linha in cedo["linhas"])
    assert sum(1 for linha in cedo["linhas"] if linha["perda"]["estado"] == "sem_comparacoes") == 1013
    assert cedo["resumo"]["niveis"]["sem_comparacoes"] == 800 and cedo["resumo"]["com_nivel"]["perda"] == 0


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
    q = real.quantidade
    niveis = np.full(cal.regular.shape, -1, dtype=np.int8)
    niveis[cal.regular] = reguas.niveis_em_vetor(reguas.Comparacoes(
        *(cal.c_perda[origem][cal.regular].astype(np.int64) for origem in range(6)), theta=np.empty(0)))
    candidatos = [(int(linha), int(j)) for linha, j in np.argwhere(cal.queda_grande & (cal.marca == 0))
                  if j + 2 < len(PERIODOS) and q[linha, j + 2] <= 0.6 * q[linha, j - 1] and niveis[linha, j] >= 1]
    assert len(candidatos) == 34, "a base tem quedas grandes que persistem e são raras para o porte"
    linha, j = candidatos[0]
    codigo = "code:" + real.codigos[linha]
    body = corpo(pedir({"base": {"municipios": {"ids": [codigo]}}, "detalhe": codigo, "janela": {"fim": PERIODOS[j]}}))
    perda = body["territorio"]["perda"]
    assert (real.nomes[linha], PERIODOS[j]) == ("COLORADO DO OESTE (RO)", "201806")
    assert (perda["verificar_registro"], perda["estado"], perda["classe"], perda["delta"], perda["anterior"]) == ("queda", "alerta", "elevado", -15, 29)
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
    """Os sinais 8 a 12 na base versionada. Com a população do Ministério da Saúde (troca de 13/11/2026, comando V23), a base
    inteira é um trecho só de população comparável, lido dela mesma: nenhum ano de 2014 a 2024 fica com "comparação não
    habilitada". Os sinais 8 a 10 têm nível pela raridade da variação em dois anos; o 11 é só contexto; o 12 não soma nem cria
    nível."""
    def contar(resposta, chave, campo="estado"):
        saida = {}
        for linha in resposta["linhas"]:
            saida[linha[chave][campo]] = saida.get(linha[chave][campo], 0) + 1
        return saida
    # No último registro (jun/2024), a janela de jun/2022 a jun/2024 vale.
    hoje = corpo(pedir({"base": {"municipios": {"todos": True}}}))
    assert hoje["comparacao"]["estado"] == "comparavel" and (hoje["comparacao"]["de"], hoje["comparacao"]["ate"]) == ("202206", "202406")
    assert hoje["comparacao"]["trechos"] == [[2014, 2024]] and hoje["comparacao"]["motivo"] is None and hoje["comparacao"]["minimo_de_medicos"] == 20
    assert all(linha["disponibilidade"]["taxa"] is not None and linha["posicao"]["percentil"] is not None for linha in hoje["linhas"])
    # Abaixo de 20 médicos, os sinais 8 a 10 são só descritivos; acima, o nível é o da raridade da variação. `sinal` repete o nível.
    assert contar(hoje, "disponibilidade") == {"sem_sinal": 2301, "descritivo": 3162, "classificado": 107}
    assert contar(hoje, "disponibilidade", "classe") == {None: 5463, "moderado": 74, "elevado": 29, "critico": 4}
    assert contar(hoje, "posicao") == {"sem_sinal": 2230, "descritivo": 3162, "classificado": 178}
    assert contar(hoje, "posicao", "classe") == {None: 5392, "moderado": 131, "elevado": 42, "critico": 5}
    assert contar(hoje, "defasagem") == {"sem_sinal": 2273, "descritivo": 3162, "classificado": 134,
                                        "referencia_invalida": 1}   # Brasília é o único município da UF
    assert contar(hoje, "defasagem", "classe") == {None: 5436, "moderado": 99, "elevado": 31, "critico": 4}
    assert all(linha[chave]["sinal"] == linha[chave]["classe"] and (linha[chave]["estado"] == "classificado") == bool(linha[chave]["classe"])
               for linha in hoje["linhas"] for chave in ("disponibilidade", "posicao", "defasagem"))
    assert [hoje["resumo"]["sinais"][chave] for chave in ("disponibilidade", "posicao", "defasagem", "combinados")] == [107, 178, 134, 328]
    assert [hoje["resumo"]["com_nivel"][chave] for chave in ("disponibilidade", "posicao", "defasagem")] == [107, 178, 134]
    # O grupo "Comparado com outros" leva o maior nível entre os sinais 8 a 10; o contexto geográfico nunca tem nível.
    assert contar(hoje, "dimensoes", "comparacao") == {None: 5328, "moderado": 172, "elevado": 60, "critico": 10}
    assert contar(hoje, "dimensoes", "contexto") == {None: 5570}
    assert not any(linha["alerta"]["sinal"] in ("contexto", "coexistencia") for linha in hoje["linhas"])
    # Os dois municípios de Sergipe cuja população de 2024 mudou na troca (a tabela corrigida do IBGE de 30/12/2024).
    de_hoje = {linha["id"]: linha for linha in hoje["linhas"]}
    assert (de_hoje["code:280120"]["rotulo"], de_hoje["code:280120"]["disponibilidade"]["populacao"]) == ("CANINDE DE SAO FRANCISCO (SE)", 33491.0)
    assert (de_hoje["code:280540"]["rotulo"], de_hoje["code:280540"]["disponibilidade"]["populacao"]) == ("POCO REDONDO (SE)", 29117.0)
    assert de_hoje["code:280120"]["disponibilidade"]["taxa"] == pytest.approx(1000 * 47 / 33491)
    assert de_hoje["code:280540"]["disponibilidade"]["taxa"] == pytest.approx(1000 * 19 / 29117)
    assert (de_hoje["code:530010"]["rotulo"], de_hoje["code:530010"]["defasagem"]["estado"], de_hoje["code:530010"]["defasagem"]["indice"]) == (
        "BRASILIA (DF)", "referencia_invalida", None)
    assert hoje["limitacoes"] == ["RARO_E_INCOMUM_NA_BASE", "CONJUNTO_SEM_NIVEL", "COMPARACAO_SO_COM_POPULACAO_COMPARAVEL"]
    # O contexto geográfico vale em qualquer data: o critério é a taxa do Brasil (2,36 por 1.000 em jun/2024).
    contexto = hoje["comparacao"]["contexto"]
    assert contexto["taxa_minima"] == contexto["taxa_do_brasil"] == pytest.approx(2.36375, abs=1e-5) and contexto["pct_da_taxa_do_brasil"] == 100.0
    assert (contexto["atendem"], contexto["universo"]) == (2002, 3566)
    assert contar(hoje, "contexto") == {"contexto": 3566, "atende_ao_criterio": 2002, "sem_coordenada": 2}
    assert len(hoje["coordenadas"]) == 5564 and all(len(par) == 2 for par in hoje["coordenadas"].values())
    # Em jun/2021, a janela é a de jun/2019 a jun/2021, com a população nova (a taxa do Brasil na data é de 2,01 por 1.000).
    antes = corpo(pedir({"base": {"municipios": {"todos": True}}, "janela": {"fim": "202106"}}))
    assert (antes["comparacao"]["estado"], antes["comparacao"]["de"], antes["comparacao"]["ate"]) == ("comparavel", "201906", "202106")
    assert antes["comparacao"]["contexto"]["taxa_do_brasil"] == pytest.approx(2.01377, abs=1e-5)
    assert (antes["comparacao"]["contexto"]["atendem"], antes["comparacao"]["contexto"]["universo"]) == (1670, 3895)
    assert [antes["resumo"]["sinais"][chave] for chave in ("disponibilidade", "posicao", "defasagem", "combinados")] == [46, 107, 78, 535]
    assert contar(antes, "disponibilidade") == {"sem_sinal": 1967, "descritivo": 3554, "classificado": 46, "nao_calculavel": 3}
    assert contar(antes, "disponibilidade", "classe") == {None: 5524, "moderado": 33, "elevado": 11, "critico": 2}
    assert contar(antes, "posicao") == {"sem_sinal": 1906, "descritivo": 3557, "classificado": 107}
    assert contar(antes, "posicao", "classe") == {None: 5463, "moderado": 82, "elevado": 24, "critico": 1}
    assert contar(antes, "defasagem") == {"sem_sinal": 1934, "descritivo": 3557, "classificado": 78, "referencia_invalida": 1}
    assert contar(antes, "defasagem", "classe") == {None: 5492, "moderado": 65, "elevado": 13}
    assert contar(antes, "dimensoes", "comparacao") == {None: 5421, "moderado": 113, "elevado": 34, "critico": 2}
    assert contar(antes, "dimensoes", "contexto") == {None: 5570}
    linhas = {linha["id"]: linha for linha in antes["linhas"]}
    # Barra Bonita (SP): a mesma queda aparece na queda recente, na taxa, na posição e no índice. São quatro repercussões de um
    # evento só: o alerta é o maior nível (crítico, pela queda recente), sem soma e sem combinação.
    barra = linhas["code:350530"]
    assert barra["rotulo"] == "BARRA BONITA (SP)" and barra["sinais"] == ["perda", "alerta_perda", "instabilidade", "registro", "disponibilidade",
                                                                           "posicao", "defasagem"]
    assert (barra["disponibilidade"]["classe"], barra["posicao"]["classe"], barra["defasagem"]["classe"]) == ("elevado", "moderado", "moderado")
    assert barra["disponibilidade"]["variacao_pct"] == pytest.approx(-35.748, abs=1e-3) and barra["posicao"]["variacao_pp"] == pytest.approx(-11.311, abs=1e-3)
    assert barra["defasagem"]["indice"] == pytest.approx(72.098, abs=1e-3) and barra["posicao"]["universo"] == 5570
    assert barra["defasagem"]["variacao_pontos"] == pytest.approx(-54.745, abs=1e-3)
    assert barra["coexistencia"] == {"estado": "sem_combinacao", "combinacoes": [], "textos": [], "repercussoes": 4}
    assert barra["contexto"]["estado"] == "atende_ao_criterio"
    assert (barra["alerta"]["nivel"], barra["alerta"]["sinal"], barra["alerta"]["criterio"], barra["alerta"]["outros"]) == (
        "critico", "perda", "comparado com a base", 4)
    assert barra["alerta"]["por_que"] == "Caiu de 233 para 111 (−52,4%) (+4 sinais)"
    assert [(item["sinal"], item["nivel"]) for item in barra["alerta"]["sinais"]] == [
        ("perda", "critico"), ("disponibilidade", "elevado"), ("instabilidade", "moderado"), ("posicao", "moderado"), ("defasagem", "moderado")]
    assert barra["alerta"]["mesma_queda"] == ["perda", "disponibilidade", "posicao", "defasagem"]
    assert barra["dimensoes"] == {"estrutural": None, "trajetoria": "critico", "ritmo": "moderado", "comparacao": "elevado", "contexto": None}
    # Manaus, abaixo da taxa do Brasil em jun/2021: o município mais próximo que atende ao critério fica a 752 km, em linha reta
    # (com a população nova, é Porto Velho; com a anterior, era Jacareacanga, a 424 km). O contexto não gera alerta.
    manaus = linhas["code:130260"]["contexto"]
    assert (manaus["estado"], manaus["referencia"], manaus["referencia_id"]) == ("contexto", "PORTO VELHO (RO)", "code:110020")
    assert manaus["distancia_km"] == pytest.approx(752.233, abs=1e-3) and manaus["percentil"] == pytest.approx(99.012, abs=1e-3)
    assert (linhas["code:130260"]["alerta"]["estado"], linhas["code:130260"]["alerta"]["nivel"]) == ("sem_alerta", None)
    assert "code:110020" in antes["coordenadas"] and "code:130260" in antes["coordenadas"]
    # Os detalhes de um território trazem os 11 itens (os 12 sinais; 1 e 2 juntos) e as séries dos gráficos dos sinais 8 e 10.
    detalhe = corpo(pedir({"base": {"municipios": {"ids": ["code:350530"]}}, "detalhe": "code:350530", "janela": {"fim": "202106"}}))
    assert [item["numero"] for item in detalhe["fenomenos"]] == ["1–2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    do_sinal = {item["chave"]: item for item in detalhe["fenomenos"]}
    assert [(chave, do_sinal[chave]["nivel"], do_sinal[chave]["estado_do_nivel"], do_sinal[chave]["criterio_do_nivel"], do_sinal[chave]["situacao"])
            for chave in ("disponibilidade", "posicao", "defasagem", "contexto")] == [
        ("disponibilidade", "elevado", "alerta", "comparado com a base", "−35,7% de médicos por habitante em 2 anos"),
        ("posicao", "moderado", "alerta", "comparado com a base", "−11,3 pontos de percentil em 2 anos"),
        ("defasagem", "moderado", "alerta", "comparado com a base", "−54,7 pontos no índice ante a referência em 2 anos"),
        ("contexto", None, "contexto", None, "Acima do critério (2,01 médicos por 1.000 habitantes ou mais)")]
    assert do_sinal["disponibilidade"]["habitual"] == ("Comparado com a base: entre 1.731 variações anteriores de municípios de 100 a 299 médicos, "
                                                       "12 foram iguais ou piores (raridade de 1 em cada 133).")
    juntos = do_sinal["coexistencia"]
    assert (juntos["nivel"], juntos["estado_do_nivel"]) == (None, "juntos") and juntos["situacao"].startswith("5 sinais com nível: queda recente (crítico)")
    assert juntos["habitual"] == ("O alerta do território é o maior nível: crítico. Os níveis não se somam. 4 desses sinais vêm da mesma "
                                  "queda e contam como um evento.")
    assert detalhe["linha"]["alerta"] == barra["alerta"]
    comparativo = detalhe["comparativo"]
    assert comparativo["competencias"] == list(PERIODOS[:16]) and len(comparativo["taxa"]) == len(comparativo["indice"]) == 16
    assert comparativo["referencia"]["rotulo"] == "demais municípios de São Paulo (soma municipal)"
    assert comparativo["taxa"][-1] == pytest.approx(3.1059, abs=1e-4) and comparativo["indice"][-1] == pytest.approx(72.098, abs=1e-3)
    assert comparativo["trechos"] == [[2014, 2024]]
    tudo = " ".join(str(item[campo]) for item in detalhe["fenomenos"] for campo in ("situacao", "observado", "criterio", "habitual", "significa",
                                                                                    "nao_significa", "entenda")).lower()
    for proibido in ("desassist", "isolad", "isolamento", "sem cobertura", "recomenda", "deveria", "criticidade", "vazio assistencial",
                     "atenção,", "intensidade"):
        assert proibido not in tudo, proibido
