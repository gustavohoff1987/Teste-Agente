"""Simulador de Cenários Territoriais (comandos V22 e V23; backend/simulador.py; a referência é a Parte C de
Docs/DETECTOR_E_SIMULADOR_V3.md — a seção C.3, o jeito de projetar que a própria base escolhe, e a C.4, as faixas — e
Docs/SIMULADOR_DE_CENARIOS.md).

Três grupos de testes:
- **fórmulas**, sobre séries sintéticas montadas direto em `series_brasil.Base` (o calendário real, de janeiro e junho de 2014 a
  2024): a persistência (M0), com o crescimento recente do estado (M0d) e com o da base toda (M0g); a taxa composta com o tempo
  real (M1); a tendência linear robusta (M2) e a log-linear (M3); a taxa informada pela pessoa; o zero e a ausência; a quebra de
  fonte (a volta ao M0); as intervenções (somadas à base, sem crescer com ela; a permanência; a retirada impossível); os conjuntos
  e os estados como unidade; a média aritmética, só descritiva; os avisos de horizonte; a retroprojeção com origens móveis (os
  casos que entram e a ausência de observações futuras nos ajustes); o **método padrão**, que é o jeito de projetar que a própria
  base escolhe para cada nível de território (o próprio território, o grupo de cima ou a base toda, cada um comparado com manter
  o último valor; a exceção por porte; o último valor quando nenhum vale ou quando falta história); e as **faixas** de 5, 8 e 9 em
  cada 10, só do jeito escolhido (os percentis, os casos mínimos, a retaguarda com os portes vizinhos e os menores, e a
  conferência no tempo: conferida, provisória ou indisponível). A escolha e as faixas são conferidas com uma referência refeita
  aqui, em laços simples, sobre os mesmos dados sintéticos;
- **rota** POST /api/simulador, com um catálogo sintético instalado como versão governada: a resposta (a fonte, a opção `faixa`, a
  retroprojeção por nível com a escolha e a frase dela), o Brasil como território (só no Simulador, com o jeito escolhido para os
  estados, como provisório), as referências fixas, dinâmicas e por valor (o alcance, a sobreposição e a comparação por taxa com a
  população constante), o planejamento inverso (o menor inteiro que alcança a meta, reaplicado ao Simulador), a hipótese derivada
  da simulação e as recusas. A planilha enviada inteira está em test_ferramentas_qualquer_base.py;
- **base versionada** (job dados-reais, ADT_REAL_DATA_DIR, somente leitura): a escolha (M0d nos municípios, M1 nos estados), as
  faixas e os erros da retroprojeção da Proposta V3, o Distrito Federal (a quebra de fonte), Rio Rufino (o pico fora do ajuste)
  e o limite de territórios; o Brasil, as referências de Manaus, o planejamento inverso e "Simular recuperação".
Nenhum valor sintético representa quantitativos reais.
"""
import contextvars
import hashlib
import json
import math
import os
import random
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

import brazil_data
import detector
import main
import reguas
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
JUNHOS = ("201706", "201806", "201906", "202006", "202106", "202206", "202306")   # as origens da retroprojeção neste calendário
FIXO = "Cenário hipotético, não é previsão: "
# As faixas (Proposta V3, seção C.4), em cada 10: os percentis do erro relativo, os casos mínimos e a meta de cobertura, em %.
FAIXAS = {5: (25, 75, 80, 50), 8: (10, 90, 200, 80), 9: (5, 95, 400, 90)}
ROTULOS = {"M0": "persistência (o último valor se mantém)", "M0d": "persistência com o crescimento recente do estado",
           "M0g": "persistência com o crescimento recente da base toda", "M1": "taxa composta da janela"}
# Os textos fixos dos cenários que se repetem nos testes.
SO_DO_ESCOLHIDO = ("A faixa de 8 em cada 10 só existe para o jeito de projetar e a janela que a própria base escolheu ({}, com os 3 anos até a "
                   "origem). Com outro jeito ou outra janela, não há faixa.")
SEM_FAIXA = "Sem a faixa, o cenário mostra só a linha: ela não diz quanto o valor real costuma se afastar."
REFEITA = ("Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte. Em {} de cada 10 vezes, o valor real ficou "
           "dentro desta faixa. Não é garantia: o passado testado (2017–2024) pode não se repetir.")
AINDA_PROVISORIA = (" Faixa provisória: ainda não deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do "
                    "esperado.")
SEM_CONFERENCIA = "Faixa provisória: ainda não deu para conferi-la com dados que vieram depois (poucas origens ou poucos casos de teste)."
MARGEM_DO_PORTE = "a margem observada no passado da base, em municípios do mesmo porte; acompanha a intervenção"
ERROU_MENOS = "Usamos este jeito porque, nesta base, ele errou menos que simplesmente manter o último valor, quando refeito no passado."
NAO_PODE_SER_USADO = "Neste caso, o jeito escolhido pela base não pôde ser usado, e o cenário mantém o último valor."
NENHUM_VALE = ("Nesta base, nenhum jeito de projetar errou menos que manter o último valor, quando conferido com o passado: o cenário mantém o "
               "último valor.")
SEM_RETROPROJECAO_BASTANTE = "A faixa de 8 em cada 10 vem da retroprojeção, e esta base não tem retroprojeção bastante: "
# Quando o padrão cai no último valor neste território (o porte em que o escolhido errou mais, ou a falta do crescimento que ele
# pede), a faixa da base é a do jeito escolhido, e o cenário fica sem ela.
SO_O_ULTIMO_VALOR = ("A faixa de 8 em cada 10 é a do jeito de projetar que a base escolheu ({}). Neste território, o cenário mantém o último "
                     "valor, e não há faixa.")
SEM_A_TAXA_COMPOSTA = ("Sem a taxa composta do território (ela exige dois registros nos 3 anos até a origem, com o primeiro e o último acima de "
                       "zero): o cenário usa a persistência (o último valor se mantém).")


def base(series: dict, estados: dict | None = None, periodos: tuple = PERIODOS, com_grupo: bool = True) -> series_brasil.Base:
    """Uma base sintética: as séries por código (os dois primeiros dígitos são o grupo de cima, a UF; `com_grupo=False`: base sem
    grupo de cima) e, em `estados`, a contagem própria de cada UF. A versão cobre as séries, o calendário, os grupos e as contagens
    dos grupos: a retroprojeção dos grupos como unidade é guardada por versão."""
    codigos = tuple(sorted(series))
    quantidade = np.array([[np.nan if v is None else float(v) for v in series[codigo]] for codigo in codigos])
    prefixos = tuple(codigo[:2] if com_grupo else "" for codigo in codigos)
    do_estado = {}
    for linha, prefixo in enumerate(prefixos):
        if prefixo:
            do_estado.setdefault(prefixo, []).append(linha)
    vazio = np.full(quantidade.shape, np.nan)
    dos_grupos = {prefixo: np.array(valores, dtype=float) for prefixo, valores in (estados or {}).items()}
    marca = hashlib.sha256(quantidade.tobytes() + repr((periodos, prefixos, sorted((p, v.tolist()) for p, v in dos_grupos.items()))).encode())
    return series_brasil.Base(
        versao="sintetica-" + marca.hexdigest()[:12], periodos=periodos, meses=np.array([series_brasil.mes_da_competencia(p) for p in periodos]),
        codigos=codigos, nomes=tuple("M" + codigo for codigo in codigos), prefixos=prefixos, quantidade=quantidade, populacao=vazio,
        latitude=vazio, longitude=vazio, estados=dos_grupos,
        brasil=np.full(len(periodos), np.nan), indice={codigo: linha for linha, codigo in enumerate(codigos)},
        do_estado={prefixo: tuple(linhas) for prefixo, linhas in do_estado.items()},
        ancora=series_brasil.mes_ancora(periodos))   # lido do calendário, como nas bases reais: junho, de 2014 a 2024


def retroprojecoes(b) -> dict:
    """As retroprojeções de uma base, como `compute` as monta: a das unidades e, quando a base tem a contagem própria dos grupos
    de cima, a dos grupos como unidade."""
    return {"municipios": simulador.retroprojetar(b, "municipios", guardar=False),
            "estados": simulador.retroprojetar(b, "estados", guardar=False) if b.estados else None}


def simular(b, territorio, cenario, horizonte="202606", janela=None, em_10=8, retros=None):
    """Um território num cenário, pelo caminho da rota (a calibração do Detector e as retroprojeções da própria base)."""
    cal = detector.calibrar(b, guardar=False)
    inicio, fim, _ = simulador._janela(b, janela)
    pedido = simulador._cenarios([cenario], b, {territorio.id})[0]
    return simulador._simular(b, cal, retros or retroprojecoes(b), territorio, pedido, inicio, fim,
                              simulador._competencia_futura(horizonte, "Data final"), em_10=em_10)


def avisos(resultado):
    return [aviso["codigo"] for aviso in resultado["avisos"]]


def aviso(resultado, codigo):
    """O texto de um aviso do cenário, pelo código."""
    return next(item["texto"] for item in resultado["avisos"] if item["codigo"] == codigo)


def municipio(b, codigo):
    return series_brasil.municipio(b, codigo)


def jeito(pedido, usado, escolhido, **outros):
    """O bloco `metodo` de um cenário calculado: o que foi pedido, o que foi usado e o que a base escolheu para o nível."""
    return {"pedido": pedido, "usado": usado, "rotulo": ROTULOS[usado], "padrao": pedido == "padrao", "provisorio": False,
            "voltou_ao_m0": False, "soma": None, "escolhido_pela_base": escolhido, "e_o_escolhido": usado == escolhido, **outros}


def _inteiro(valor):
    """O inteiro mais próximo, com o meio para cima (como os textos dos cenários mostram os números)."""
    return int(math.floor(valor + 0.5))


def _br(valor, casas=0):
    """Um número como os textos o mostram: o ponto nos milhares e a vírgula nas casas decimais."""
    return ("{:,.%df}" % casas).format(valor).replace(",", "_").replace(".", ",").replace("_", ".")


def poucos_casos(casos, em_10=8, prazo="1 ano"):
    """O motivo de um cenário sem faixa por falta de casos: quantos a faixa pede e quantos a base tem, no prazo da primeira."""
    return ("A faixa de %d em cada 10 pede %d casos por prazo, e esta base tem %d em %s para o porte deste território, mesmo juntando os "
            "portes vizinhos e os menores.") % (em_10, FAIXAS[em_10][2], casos, prazo)


def faixa_ate(prazo, em_10=8):
    """O aviso de que a faixa do cenário acaba antes da data final: vai até o maior prazo seguido que a base sustenta."""
    return ("A faixa de %d em cada 10 vai só até %s depois da origem (o maior prazo que a retroprojeção desta base sustenta); além disso, é "
            "indisponível (sem extrapolar)." % (em_10, prazo))


@pytest.fixture(autouse=True)
def datas_com_ano_e_mes():
    """As datas destes testes têm ano e mês, e os cenários são montados direto (fora de `compute`). A marca de base com datas só
    de ano (`simulador._ANUAL`) vale só durante um `compute` — que a devolve ao que era, como o teste da marca confere —, mas
    cada teste deste arquivo começa com ela desligada e a devolve como estava, para não depender de quem rodou antes."""
    antes = simulador._ANUAL.get()
    simulador._ANUAL.set(False)
    yield
    simulador._ANUAL.set(antes)


# --------------------------------------------------------------------------------------------- referência (laços simples)
def _casos_de_referencia(b):
    """As retroprojeções de uma base sem picos nem quebras de fonte, refeitas em laços simples (Proposta V3, seção C.3): em cada
    junho com o junho de 3 anos antes e ao menos 1 ano depois, cada território com a janela de 3 anos inteira e 1 ou mais na
    origem e 3 anos antes é projetado 1 a 4 anos à frente — pelo último valor (M0), pelo crescimento do grupo de cima (M0d), pelo
    da base toda (M0g) e pelo do próprio território (M1) nesses 3 anos — e confrontado com o observado, quando há."""
    junho = {int(p[:4]): k for k, p in enumerate(b.periodos) if p.endswith("06")}
    q, casos = b.quantidade, []
    for ano in sorted(junho):
        if ano - 3 not in junho or ano + 1 not in junho:
            continue
        o, antes = junho[ano], junho[ano - 3]
        da_base = np.nansum(q[:, o]) / np.nansum(q[:, antes])
        for linha in range(len(b.codigos)):
            n0, n_antes = q[linha, o], q[linha, antes]
            if np.isnan(q[linha, antes:o + 1]).any() or n0 < 1 or n_antes < 1:
                continue
            do_grupo = list(b.do_estado.get(b.prefixos[linha], ()))
            for prazo in (1, 2, 3, 4):
                if ano + prazo not in junho or np.isnan(q[linha, junho[ano + prazo]]):
                    continue
                caso = {"ano": ano, "prazo": prazo, "porte": reguas.porte_de(n0), "linha": linha, "observado": float(q[linha, junho[ano + prazo]]),
                        "M0": float(n0), "M0g": float(n0 * da_base ** (prazo / 3)), "M1": float(n0 * (n0 / n_antes) ** (prazo / 3))}
                if do_grupo:
                    caso["M0d"] = float(n0 * (np.nansum(q[do_grupo, o]) / np.nansum(q[do_grupo, antes])) ** (prazo / 3))
                casos.append(caso)
    return casos


def _erro(casos, metodo):
    return sum(abs(caso["observado"] - caso[metodo]) for caso in casos)


def _frente_ao_ultimo_valor(casos, metodo, juntos=False):
    """O erro absoluto médio de um jeito ÷ o de manter o último valor, com cada porte pesando o mesmo (regra C.3). Só para bases
    em que nenhum porte precisa juntar-se a um vizinho: um porte só, ou 30 casos ou mais em cada um. `juntos`: a base pequena,
    em que nenhum porte chega a 30 casos e todos acabam num grupo só."""
    portes = sorted({caso["porte"] for caso in casos})
    grupos = [casos] if juntos or len(portes) == 1 else [[caso for caso in casos if caso["porte"] == porte] for porte in portes]
    assert len(grupos) == 1 or all(len(grupo) >= 30 for grupo in grupos), "a referência não junta portes"
    razoes = [_erro(grupo, metodo) / _erro(grupo, "M0") for grupo in grupos if _erro(grupo, "M0") > 0]
    return sum(razoes) / len(razoes) if razoes else None


def _escolha_de_referencia(casos, juntos=False):
    """A regra de escolha (seção C.3) sobre os casos de referência: os candidatos na ordem de proximidade do território (o
    próprio, o grupo de cima, a base toda), com o erro frente ao último valor, em quantas combinações de origem e prazo cada um
    errou menos e se vale (errou menos no total e em pelo menos metade das combinações); e o escolhido — entre os que valem, o
    mais próximo a até 5% do melhor; se nenhum vale, o último valor."""
    combinacoes = sorted({(caso["ano"], caso["prazo"]) for caso in casos})
    candidatos = []
    for metodo in ("M1", "M0d", "M0g"):
        com_o_metodo = [caso for caso in casos if metodo in caso]
        if not com_o_metodo:
            continue
        total = _frente_ao_ultimo_valor(com_o_metodo, metodo, juntos)
        menos = 0
        for combinacao in combinacoes:
            razao = _frente_ao_ultimo_valor([caso for caso in com_o_metodo if (caso["ano"], caso["prazo"]) == combinacao], metodo, juntos)
            menos += int(razao is not None and razao < 1)
        candidatos.append({"metodo": metodo, "frente_ao_m0": total, "menos_erro_em": menos, "combinacoes": len(combinacoes),
                           "casos": len(com_o_metodo), "vale": total is not None and total < 1 and 2 * menos >= len(combinacoes)})
    valem = [candidato for candidato in candidatos if candidato["vale"]]
    melhor = min((candidato["frente_ao_m0"] for candidato in valem), default=None)
    return next((candidato["metodo"] for candidato in valem if candidato["frente_ao_m0"] <= 1.05 * melhor), "M0"), candidatos


def _aproximado(valor):
    return None if valor is None else pytest.approx(valor)


def _confere_candidatos(escolha, casos, juntos=False):
    """A escolha do motor diante da referência: o escolhido e, de cada candidato, o erro frente ao último valor, as combinações
    em que errou menos, os casos e se vale. Devolve {método: vale}."""
    escolhido, candidatos = _escolha_de_referencia(casos, juntos)
    assert escolha["metodo"] == escolhido and escolha["combinacoes"] == len({(caso["ano"], caso["prazo"]) for caso in casos})
    assert escolha["candidatos"] == [{**candidato, "frente_ao_m0": _aproximado(candidato["frente_ao_m0"])} for candidato in candidatos]
    return {candidato["metodo"]: candidato["vale"] for candidato in candidatos}


def _razoes(casos, metodo):
    """O erro relativo de cada caso: observado ÷ cenário − 1."""
    return np.array([caso["observado"] / caso[metodo] - 1 for caso in casos])


def _conferencia_de_referencia(casos, metodo, em_10):
    """A conferência no tempo de uma faixa do próprio porte, sem retaguarda (seção C.4), sobre os casos de um porte e de um
    prazo: em cada origem, os limites vêm só dos casos cujo resultado já era conhecido (origem + prazo ≤ origem de teste); com
    casos bastantes, os casos dessa origem são testados. Devolve as origens de teste, os casos de teste e quantos ficaram dentro."""
    inferior, superior, minimo, _ = FAIXAS[em_10]
    origens = testados = dentro = 0
    for ano in sorted({caso["ano"] for caso in casos}):
        conhecidos = [caso for caso in casos if caso["ano"] + caso["prazo"] <= ano]
        if len(conhecidos) < minimo:
            continue
        a, b = np.percentile(_razoes(conhecidos, metodo), [inferior, superior])
        de_teste = _razoes([caso for caso in casos if caso["ano"] == ano], metodo)
        origens, testados, dentro = origens + 1, testados + len(de_teste), dentro + int(((de_teste >= a) & (de_teste <= b)).sum())
    return origens, testados, dentro


def _estado_da_conferencia(origens, testados, dentro, meta):
    """O estado de uma faixa pela conferência (seção C.4): com menos de 3 origens de teste ou menos de 50 casos de teste, não deu
    para conferir (provisória); senão, pela cobertura em pontos inteiros — até 5 abaixo da meta, conferida; de 5 a 10 abaixo,
    provisória; mais que isso, indisponível."""
    if origens < 3 or testados < 50:
        return "provisoria", "sem_conferencia"
    cobertura = _inteiro(100 * dentro / testados)
    return ("conferida", None) if cobertura >= meta - 5 else ("provisoria", "cobertura_abaixo") if cobertura >= meta - 10 else \
        ("indisponivel", "cobertura_baixa")


def _confere_faixa(faixa, casos, metodo, em_10):
    """Uma faixa do motor, montada com os casos do próprio porte, diante da referência: os limites pelos percentis do erro
    relativo, os casos, as origens e a conferência no tempo."""
    inferior, superior, minimo, meta = FAIXAS[em_10]
    assert (faixa["casos"], faixa["origens"], faixa["pede"], faixa["como"], faixa["meta"]) == (
        len(casos), len({caso["ano"] for caso in casos}), minimo, "propria", meta)
    assert (faixa["inferior"], faixa["superior"]) == pytest.approx(tuple(np.percentile(_razoes(casos, metodo), [inferior, superior])))
    origens, testados, dentro = _conferencia_de_referencia(casos, metodo, em_10)
    assert (faixa["origens_de_teste"], faixa["casos_de_teste"]) == (origens, testados)
    assert faixa["cobertura"] == (pytest.approx(100 * dentro / testados) if testados else None)
    assert (faixa["estado"], faixa["motivo"]) == _estado_da_conferencia(origens, testados, dentro, meta)


def _casos_a_mao(linhas, metodo="M0"):
    """Casos de retroprojeção montados à mão, na matriz do motor: cada linha é (ano da origem, prazo, porte, observado, projeção
    do método, último valor)."""
    casos = np.full((len(linhas), simulador.COLUNAS), np.nan)
    for k, (ano, prazo, porte, observado, projecao, n0) in enumerate(linhas):
        casos[k, [simulador.ANO, simulador.PRAZO, simulador.PORTE, simulador.LINHA, simulador.N0, simulador.OBSERVADO]] = ano, prazo, porte, k, n0, observado
        casos[k, simulador.COLUNA["M0"]] = n0
        casos[k, simulador.COLUNA[metodo]] = projecao
    return casos


def _casos_com_erro(linhas):
    """Casos do último valor montados à mão: cada linha é (ano da origem, prazo, porte, erro relativo). O cenário é 100, e o
    observado, 100 × (1 + erro)."""
    return _casos_a_mao([(ano, prazo, porte, 100.0 * (1 + erro), 100.0, 100.0) for ano, prazo, porte, erro in linhas])


# --------------------------------------------------------------------------------------------- bases sintéticas com resultado conhecido
def _series_do_grupo(sorteio, prefixo, primeiro, quantos, crescimento, ruido, partida, periodos=PERIODOS):
    """`quantos` territórios de um grupo: cada um parte de um valor sorteado em `partida` (no primeiro registro), segue o
    crescimento anual do grupo e leva, em cada registro, um ruído sorteado de até ±`ruido` (em fração do valor). As contagens são
    inteiras, de 1 para cima. Os sorteios usam só `random()`, que o Python garante igual de uma versão para outra."""
    meses = np.array([series_brasil.mes_da_competencia(p) for p in periodos])
    anos = (meses - meses[0]) / 12.0
    series = {}
    for k in range(quantos):
        inicial = partida[0] + (partida[1] - partida[0]) * sorteio.random()
        series[prefixo + str(primeiro + k)] = [max(1, round(inicial * (1 + crescimento) ** a * (1 + ruido * (2 * sorteio.random() - 1)))) for a in anos]
    return series


def _series_de_grupos(grupos, por_grupo=30, ruido=0.08, partida=(110, 130), periodos=PERIODOS):
    """Territórios de 100 a 299 médicos (um porte só) em grupos: `grupos` diz o crescimento anual de cada grupo (o prefixo é só
    o rótulo do grupo)."""
    sorteio = random.Random(20261114)
    series = {}
    for prefixo, crescimento in grupos.items():
        series.update(_series_do_grupo(sorteio, prefixo, 1000, por_grupo, crescimento, ruido, partida, periodos))
    return series


def _base_do_grupo_de_cima():
    """A base em que o grupo de cima erra menos: 30 municípios de Rondônia, que cresce 6% ao ano, e 30 do Acre, parado, todos de
    100 a 299 médicos e com ruído de ±8%. Mais dois municípios que não geram retroprojeções: um sem médicos, em Rondônia, e um
    do Distrito Federal com quebra de fonte até jun/2022 (a soma municipal abaixo da contagem estadual)."""
    series = _series_de_grupos({"11": 0.06, "12": 0.0})
    series["119999"] = [0] * T
    series["530010"] = [1000] * 18 + [3000] * 4
    return base(series, estados={"53": [2500] * T})


def _base_da_excecao():
    """Três portes: em Rondônia, que cresce 6% ao ano, 30 municípios de 100 a 299 e 30 de 300 a 999 médicos, que crescem com o
    estado, e 30 de 10 a 19, parados e com ruído de ±20%; no Acre, 30 de 100 a 299, parados."""
    sorteio = random.Random(20261114)
    series = {}
    series.update(_series_do_grupo(sorteio, "11", 1000, 30, 0.06, 0.08, (110, 130)))
    series.update(_series_do_grupo(sorteio, "12", 1000, 30, 0.0, 0.08, (110, 130)))
    series.update(_series_do_grupo(sorteio, "11", 2000, 30, 0.0, 0.2, (14, 15)))
    series.update(_series_do_grupo(sorteio, "11", 3000, 30, 0.06, 0.08, (350, 450)))
    return base(series)


def _base_das_faixas(depois=None):
    """60 municípios de uma UF, em 30 pares que somam 29 (a soma da UF fica constante: o crescimento do estado e o da base toda
    são zero, e o M0d e o M0g são o último valor), com 10 a 19 médicos. `depois` troca os valores posteriores a uma competência
    (para a prova de que o ajuste não vê o futuro)."""
    sorteio = random.Random(20261110)
    series = {}
    for par in range(30):
        valor, caminho = 12 + int(6 * sorteio.random()), []
        for _ in range(T):
            valor = min(19, max(10, valor + (-1, 0, 0, 1)[int(4 * sorteio.random())]))
            caminho.append(valor)
        series["11" + str(1000 + 2 * par)] = caminho
        series["11" + str(1001 + 2 * par)] = [29 - v for v in caminho]
    if depois:
        corte = PERIODOS.index(depois) + 1
        series = {codigo: valores[:corte] + [valores[k] + (3 if k % 2 else 0) for k in range(corte, T)] for codigo, valores in series.items()}
    return base(series)


# --------------------------------------------------------------------------------------------- M0, M0d e M0g
def test_persistencia_e_persistencia_com_a_deriva_do_estado():
    # A soma municipal da UF cresce 10% ao ano (composto); o município fica em 10. Nesta base de dois municípios, o jeito que a
    # base escolhe é a taxa do próprio território: o M0d é pedido pelo nome (o método padrão tem os seus testes, mais abaixo).
    b = base({"110001": [10] * T, "110002": [100 * 1.1 ** a - 10 for a in ANOS]})
    alvo = municipio(b, "110001")
    deriva = simular(b, alvo, {"metodo": "M0d"})
    assert deriva["estado"] == "calculado" and deriva["metodo"] == jeito("M0d", "M0d", "M1")
    assert deriva["parametros"]["n0"] == 10 and deriva["parametros"]["origem"] == "202406"
    assert deriva["parametros"]["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7}  # os 3 anos até o último registro
    assert deriva["parametros"]["deriva_pct"] == pytest.approx(10.0) and deriva["parametros"]["estado_da_deriva"] == "Rondônia"
    assert deriva["final"]["base"] == pytest.approx(10 * 1.1 ** 2) and deriva["final"]["intervencao"] == 0
    assert deriva["final"]["total"] == pytest.approx(12.1) and deriva["final"]["data"] == "202606"
    # O texto é o do modelo fixo: o método, as premissas, o valor (inteiro) e a data, com "Base: registros até…".
    assert deriva["texto"] == (FIXO + "com o método persistência com o crescimento recente do estado e as premissas janela de jun/2021 a "
                               "jun/2024; crescimento de Rondônia de +10,00% ao ano; sem intervenção, M110001 teria 12 médicos em "
                               "jun/2026. Base: registros até jun/2024.")
    # O "Entenda" do jeito de projetar: o que o cenário faz, com os números dele, e de quem foi a escolha.
    assert deriva["entenda"]["jeito"] == {
        "texto": "O cenário parte do último registro usado (jun/2024) e soma o crescimento recente do estado: +10,00% ao ano nos 3 anos "
                 "anteriores. Este jeito foi escolhido por você: o que a base escolheu é a taxa composta da janela.",
        "exemplo": "De 10 médicos em jun/2024, a base do cenário vai a 11 um ano depois, sem contar intervenções."}
    # Data final em qualquer mês: 4,5 anos depois, com o tempo real.
    assert simular(b, alvo, {"metodo": "M0d"}, "202812")["final"]["base"] == pytest.approx(10 * 1.1 ** 4.5)
    # M0g: o último valor com o crescimento recente da base toda (a soma de todos os municípios, que aqui também cresce 10%).
    da_base = simular(b, alvo, {"metodo": "M0g"})
    assert da_base["metodo"] == jeito("M0g", "M0g", "M1")
    assert da_base["parametros"]["crescimento_da_base_pct"] == pytest.approx(10.0) and da_base["final"]["total"] == pytest.approx(12.1)
    assert da_base["texto"] == (FIXO + "com o método persistência com o crescimento recente da base toda e as premissas janela de jun/2021 a "
                                "jun/2024; crescimento da base toda de +10,00% ao ano; sem intervenção, M110001 teria 12 médicos em "
                                "jun/2026. Base: registros até jun/2024.")
    persistencia = simular(b, alvo, {"metodo": "M0"})
    assert persistencia["metodo"]["usado"] == "M0" and persistencia["metodo"]["provisorio"] is False
    assert [ponto["base"] for ponto in persistencia["trajetoria"]] == [10.0] * 4  # jan e jun de 2025 e de 2026
    assert [ponto["data"] for ponto in persistencia["trajetoria"]] == ["202501", "202506", "202601", "202606"]
    assert persistencia["texto"].startswith(FIXO + "com o método persistência (o último valor se mantém)")
    # A faixa só existe para o jeito que a base escolheu: com outro, fica indisponível, com o motivo.
    assert persistencia["faixa"] == {"estado": "indisponivel", "motivo": SO_DO_ESCOLHIDO.format("taxa composta da janela"), "rotulo": None, "em_10": 8}
    assert persistencia["entenda"]["faixa"] == {"texto": SO_DO_ESCOLHIDO.format("taxa composta da janela"), "exemplo": SEM_FAIXA}


def test_zero_continua_zero_e_ausencia_nao_e_zero():
    b = base({"110001": [3] * 10 + [0] * 12, "110002": [50 * 1.05 ** a for a in ANOS], "110003": [7] * 21 + [None],
              "110004": [None] * T})
    # O crescimento do estado, ou o da base toda, multiplica o último valor: zero continua zero. (A faixa de um território em
    # zero, "Com zero médicos na origem, não há faixa.", está no teste do padrão com a faixa: só o jeito escolhido tem faixa.)
    for metodo, multiplica in (("M0d", "o crescimento do estado"), ("M0g", "o crescimento da base toda")):
        zero = simular(b, municipio(b, "110001"), {"metodo": metodo})
        assert zero["metodo"]["usado"] == metodo and zero["final"]["total"] == 0 and "ZERO_CONTINUA_ZERO" in avisos(zero), metodo
        assert aviso(zero, "ZERO_CONTINUA_ZERO") == ("O território está em zero: sem uma intervenção, continua em zero (" + multiplica +
                                                      " multiplica o último valor).")
    # Com uma intervenção, o território em zero passa a ter os médicos acrescentados (a base continua em zero).
    com = simular(b, municipio(b, "110001"), {"metodo": "M0d", "intervencoes": [{"tipo": "acrescimo", "quantidade": 3, "em": "202506"}]})
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
    depois da quebra, e o M0d volta ao M0, com os avisos. (O mesmo caminho pelo método padrão, numa base que escolhe o M0d, está
    no teste do padrão com a faixa.)"""
    b = base({"530010": [100] * 18 + [300] * 4, "110001": [12] * T}, estados={"53": [250] * T, "11": [1] * T})
    df = simular(b, municipio(b, "530010"), {"metodo": "M0d"})
    assert df["metodo"]["usado"] == "M0" and df["metodo"]["voltou_ao_m0"] is True and df["metodo"]["provisorio"] is False
    assert avisos(df) == ["JANELA_DEPOIS_DA_QUEBRA", "VOLTA_AO_M0", "HORIZONTE_CAUTELA"]
    assert df["parametros"]["janela"] == {"inicio": "202301", "fim": "202406", "registros": 4}
    assert df["final"]["total"] == 300 and "persistência (o último valor se mantém)" in df["texto"]
    assert aviso(df, "VOLTA_AO_M0") == (
        "Sem o crescimento recente do estado (há quebra de fonte nos 3 anos usados para medir o crescimento do estado): o cenário usa a "
        "persistência (o último valor se mantém).")
    # Os outros métodos ajustam só nos registros depois da quebra (o salto de 100 para 300 não vira taxa).
    m1 = simular(b, municipio(b, "530010"), {"metodo": "M1"})
    assert m1["parametros"]["taxa_pct"] == 0 and m1["parametros"]["anos"] == pytest.approx(17 / 12) and m1["final"]["total"] == 300
    # O município de outra UF, sem quebra, tem a deriva.
    assert simular(b, municipio(b, "110001"), {"metodo": "M0d"})["metodo"]["usado"] == "M0d"
    # Sem médicos no estado 3 anos antes, também não há crescimento a medir: o M0d, e o M0g numa base só com ele, voltam ao M0.
    vazios = base({"110001": [0] * 16 + [5] * 6, "120001": [10] * T})
    sem_soma = simular(vazios, municipio(vazios, "110001"), {"metodo": "M0d"})
    assert sem_soma["metodo"]["voltou_ao_m0"] is True and sem_soma["final"]["total"] == 5
    assert aviso(sem_soma, "VOLTA_AO_M0") == ("Sem o crescimento recente do estado (a soma dos municípios do estado é zero nesses 3 anos): o "
                                              "cenário usa a persistência (o último valor se mantém).")
    um_so = base({"110001": [0] * 16 + [5] * 6})
    sem_base = simular(um_so, municipio(um_so, "110001"), {"metodo": "M0g"})
    assert sem_base["metodo"]["voltou_ao_m0"] is True and sem_base["final"]["total"] == 5
    assert aviso(sem_base, "VOLTA_AO_M0") == ("Sem o crescimento recente da base toda (a soma da base toda é zero nesses 3 anos): o cenário usa "
                                              "a persistência (o último valor se mantém).")


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
    # Nesta base, a taxa do próprio território é o jeito escolhido. A faixa é do jeito e da janela escolhidos (os 3 anos até a
    # origem): com outra janela, não há faixa; com a janela dos 3 anos, falta só a base ter casos (aqui não tem).
    assert m1["metodo"]["e_o_escolhido"] is True and longa["metodo"]["e_o_escolhido"] is True
    assert longa["faixa"]["motivo"] == SO_DO_ESCOLHIDO.format("taxa composta da janela")
    assert m1["faixa"]["motivo"] == "A base não tem retroprojeções de territórios de 100 a 299 médicos."
    assert simular(b, municipio(b, "110003"), {"metodo": "M1"})["faixa"]["motivo"] == poucos_casos(16)
    # Com início em zero, a taxa não é definida: nem infinito, nem um ajuste que finge precisão.
    zero = simular(b, municipio(b, "110002"), {"metodo": "M1"}, janela={"inicio": "201806", "fim": "202406"})
    assert zero["estado"] == "nao_aplicavel" and "com início em zero, a taxa não é definida" in zero["motivo"]
    assert "texto" not in zero and "final" not in zero
    # O aviso de que a taxa composta errou mais que o último valor já não tem um corte fixo (100 médicos): vem da retroprojeção
    # da própria base, por porte, e está no teste da exceção por porte. Aqui, com poucos casos por porte, não há aviso.
    assert "M1_ABAIXO_DE_100" not in avisos(m1) and "M1_ABAIXO_DE_100" not in avisos(simular(b, municipio(b, "110003"), {"metodo": "M1"}))


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
        assert aviso(m2, "DIFERENCA_PARA_O_ULTIMO_REGISTRO") == (
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
    retros = retroprojecoes(b)
    ids = {"code:110001", "code:110002"}
    cenario = simulador._cenarios([{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501",
                                                                    "territorios": ["code:110002"]}]}], b, ids)[0]
    finais = [simulador._simular(b, cal, retros, municipio(b, codigo), cenario, 15, 21, series_brasil.mes_da_competencia("202606"))
              for codigo in ("110001", "110002")]
    assert [final["final"]["total"] for final in finais] == [10, 94]
    assert "sem intervenção" in finais[0]["texto"] and "acréscimo de 4 médicos em jan/2025" in finais[1]["texto"]
    # Com mais de um território no pedido, o texto diz para quem a intervenção vale: cada território recebe a quantidade inteira.
    geral = simulador._cenarios([{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]}], b, ids)[0]
    varios = [simulador._simular(b, cal, retros, municipio(b, codigo), geral, 15, 21, series_brasil.mes_da_competencia("202606"), True)
              for codigo in ("110001", "110002")]
    assert [final["final"]["total"] for final in varios] == [14, 94]
    assert all("acréscimo de 4 médicos em cada território do cenário, em jan/2025, com permanência total (hipótese)" in final["texto"]
               for final in varios)
    so_um = simulador._simular(b, cal, retros, municipio(b, "110002"), cenario, 15, 21, series_brasil.mes_da_competencia("202606"), True)
    assert "acréscimo de 4 médicos só nos territórios indicados, em jan/2025" in so_um["texto"]
    for intervencao, trecho in (
            ({"tipo": "doacao", "quantidade": 1, "em": "202501"}, "o tipo é acrescimo ou retirada"),
            ({"tipo": "acrescimo", "quantidade": 0, "em": "202501"}, "a quantidade é um número acima de zero"),
            ({"tipo": "acrescimo", "quantidade": True, "em": "202501"}, "a quantidade é um número acima de zero"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "2025"}, "use ano e mês"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202513"}, "use ano e mês"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "202401"}, "a data final vem antes da inicial"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "202701", "a_cada_meses": 0}, "de 1 a 120"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "permanencia_pct_ao_ano": 120}, "de 0 a 100"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "territorios": ["code:999999"]}, "precisam estar na seleção"),
            ({"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "209912", "a_cada_meses": 1}, "eventos demais")):
        with pytest.raises(ValueError, match=trecho):
            simulador._cenarios([{"metodo": "M0", "intervencoes": [intervencao]}], b, ids)
    with pytest.raises(ValueError, match="Método desconhecido: media_aritmetica. Use padrao, M0, M0d, M0g, M1, M2, M3 ou manual."):
        simulador._cenarios([{"metodo": "media_aritmetica"}], b, ids)
    with pytest.raises(ValueError, match="até 6 cenários"):
        simulador._cenarios([{"id": "c" + str(k), "metodo": "M0"} for k in range(7)], b, ids)
    with pytest.raises(ValueError, match="mesmo id"):
        simulador._cenarios([{"id": "a", "metodo": "M0"}, {"id": "a", "metodo": "M1"}], b, ids)
    assert simulador.METODOS == ("padrao", "M0", "M0d", "M0g", "M1", "M2", "M3", "manual")
    # Numa base com um registro por ano, as datas são anos ("AAAA00"), e os eventos se repetem de 12 em 12 meses (ou num múltiplo
    # de 12): outro intervalo é recusado, na intervenção e no calendário do planejamento inverso. Nas outras bases, nada muda.
    def numa_base_anual(pedido):
        contexto = contextvars.copy_context()   # o indicador da base anual vale só neste contexto: não passa para os outros testes
        contexto.run(simulador._ANUAL.set, True)
        return contexto.run(simulador._cenarios, [{"metodo": "M0", **pedido}], b, ids)[0]
    de_2025_a_2027 = {"tipo": "acrescimo", "quantidade": 1, "em": "202500", "ate": "202700"}
    so_de_12_em_12 = "numa base com um registro por ano, o intervalo entre os eventos é de 12 meses ou um múltiplo de 12"
    for pedido in ({"intervencoes": [{**de_2025_a_2027, "a_cada_meses": 6}]}, {"intervencoes": [{**de_2025_a_2027, "a_cada_meses": 18}]},
                   {"planejamento": {"meta": {"tipo": "valor", "valor": 5}, "em": "202500", "ate": "202700", "a_cada_meses": 18}}):
        with pytest.raises(ValueError, match=so_de_12_em_12):
            numa_base_anual(pedido)
    anos = [series_brasil.mes_da_competencia(ano) for ano in ("202500", "202600", "202700")]
    assert numa_base_anual({"intervencoes": [de_2025_a_2027]})["intervencoes"][0]["datas"] == anos   # sem intervalo no pedido: 12 meses
    assert numa_base_anual({"intervencoes": [{**de_2025_a_2027, "a_cada_meses": 24}]})["intervencoes"][0]["datas"] == anos[::2]
    assert simulador._ANUAL.get() is False
    semestral = simulador._cenarios([{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 1, "em": "202501", "ate": "202601",
                                                                      "a_cada_meses": 6}]}], b, ids)[0]
    assert len(semestral["intervencoes"][0]["datas"]) == 3


# --------------------------------------------------------------------------------------------- conjuntos e estados
def test_conjuntos_somam_as_projecoes_dos_membros_e_estados_usam_a_serie_do_nivel():
    series = {"110001": [10] * T, "110002": [100 * 1.1 ** a - 10 for a in ANOS], "120001": [20] * T,
              "120002": [200 * 1.05 ** a - 20 for a in ANOS]}
    estados = {"11": [90 * 1.1 ** a for a in ANOS], "12": [100] * T}
    b = base(series, estados)
    assert not detector.calibrar(b, guardar=False).quebra.any()
    retros = retroprojecoes(b)
    estado, par = series_brasil.selecao(b, {"estados_unidade": ["11"], "conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:110001", "code:120001"], "versao": 2}]})
    # M0d num conjunto de municípios: a soma das projeções dos membros, cada um com a deriva da sua UF (10% e 5% ao ano).
    soma = simular(b, par, {"metodo": "M0d"}, retros=retros)
    assert soma["metodo"]["usado"] == "M0d" and soma["metodo"]["soma"] == "soma das projeções dos membros"
    assert soma["parametros"]["soma_das_projecoes"] is True and soma["parametros"]["derivas_pct"] == [5.0, 10.0]
    assert soma["final"]["total"] == pytest.approx(10 * 1.1 ** 2 + 20 * 1.05 ** 2)
    assert "o crescimento recente do estado de cada membro; sem intervenção, Par (soma das projeções dos membros) teria 34 médicos" in soma["texto"]
    # Nos outros métodos, o ajuste é na série da soma das contagens.
    m1 = simular(b, par, {"metodo": "M1"}, retros=retros)
    assert m1["parametros"]["serie_da_soma"] is True and m1["parametros"]["n0"] == 30 and m1["final"]["total"] == pytest.approx(30)
    assert "Par (soma das contagens dos componentes) teria 30 médicos" in m1["texto"]
    # O M0g no conjunto: a série da soma com o crescimento da base toda — a soma de todos os municípios, de jun/2021 a jun/2024.
    dos_municipios = ((100 + 200) / (100 * 1.1 ** -3 + 200 * 1.05 ** -3)) ** (1 / 3) - 1
    m0g = simular(b, par, {"metodo": "M0g"}, retros=retros)
    assert m0g["parametros"]["serie_da_soma"] is True and m0g["parametros"]["crescimento_da_base_pct"] == pytest.approx(100 * dos_municipios)
    assert m0g["final"]["total"] == pytest.approx(30 * (1 + dos_municipios) ** 2)
    # O padrão do conjunto é o jeito escolhido para os municípios (nesta base, a taxa composta), na série da soma.
    assert retros["municipios"].escolha["metodo"] == "M1"
    do_par = simular(b, par, {"metodo": "padrao"}, retros=retros)
    assert do_par["metodo"] == jeito("padrao", "M1", "M1") and do_par["parametros"]["serie_da_soma"] is True
    # Estado como unidade: o padrão é o jeito que a retroprojeção dos próprios estados escolhe, com a série do nível. Os
    # candidatos são o próprio estado e a base toda (a soma das contagens estaduais): o grupo de cima dos estados é a base toda.
    dos_estados = retros["estados"]
    assert dos_estados.nivel == "estados" and dos_estados.origens == JUNHOS and retros["municipios"].nivel == "municipios"
    valem = _confere_candidatos(dos_estados.escolha, _casos_de_referencia(detector.base_dos_estados(b)), juntos=True)
    assert dos_estados.escolha["metodo"] == "M1" and valem == {"M1": True, "M0g": False}
    uf = simular(b, estado, {"metodo": "padrao"}, retros=retros)
    assert uf["metodo"] == jeito("padrao", "M1", "M1") and avisos(uf) == ["HORIZONTE_CAUTELA"]   # já não é provisório, nem tem aviso do nível
    assert uf["parametros"]["n0"] == pytest.approx(90) and uf["final"]["total"] == pytest.approx(90 * 1.21)
    assert "Rondônia (RO) teria 109 médicos em jun/2026" in uf["texto"]
    assert uf["faixa"] == {"estado": "indisponivel", "motivo": poucos_casos(14), "rotulo": None, "em_10": 8}
    recusado = simular(b, estado, {"metodo": "M0d"}, retros=retros)
    assert recusado["estado"] == "nao_aplicavel" and recusado["motivo"] == (
        "A persistência com o crescimento recente do estado vale para os municípios e conjuntos de municípios, numa base com grupo de cima; "
        "nos outros casos, use o crescimento da base toda (M0g) ou a taxa composta do próprio território (M1).")
    # O M0g do estado usa o crescimento da soma das contagens estaduais (não o da soma municipal).
    das_ufs = ((90 + 100) / (90 * 1.1 ** -3 + 100)) ** (1 / 3) - 1
    com_a_base = simular(b, estado, {"metodo": "M0g"}, retros=retros)
    assert com_a_base["parametros"]["crescimento_da_base_pct"] == pytest.approx(100 * das_ufs)
    assert com_a_base["final"]["total"] == pytest.approx(90 * (1 + das_ufs) ** 2) and "serie_da_soma" not in com_a_base["parametros"]
    # Sem a deriva de uma UF (quebra de fonte nela), o membro dela fica na persistência, com o aviso.
    quebrada = base(series, {"11": [90 * 1.1 ** a for a in ANOS], "12": [300] * T})
    sem = simular(quebrada, series_brasil.selecao(quebrada, {"conjuntos": [
        {"id": "c1", "rotulo": "Par", "membros": ["code:110001", "code:120001"]}]})[0], {"metodo": "M0d"})
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
    retros = retroprojecoes(b)
    for metodo in ("padrao", "M0", "M0d", "M0g", "M1", "M2", "M3"):
        resultado = simular(b, alvo, {"metodo": metodo}, janela={"inicio": "202006", "fim": "202406"}, retros=retros)
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
    # Manter o último valor não usa a história. Muda de propósito na revisão final do V23 (15/11/2026): a frase é simples e não
    # fala em referência nem em história (antes, "… a mais da metade do tempo de referência (2 anos à frente; a referência são 3
    # anos, porque manter o último valor não usa a história)", o que confundia). Os níveis e os códigos são os mesmos.
    assert simular(b, alvo, {"metodo": "M0"}, "202806")["avisos"][0]["texto"] == (
        "Extrapolação: a data final fica longe do último registro, e o cenário é muito incerto (aqui, 4 anos à frente).")
    assert simular(b, alvo, {"metodo": "M0"}, "202606")["avisos"][0]["texto"] == (
        "Cautela: quanto mais longe a data final, mais incerto o cenário (aqui, 2 anos à frente).")
    assert simular(b, alvo, {"metodo": "M0"}, "203106")["avisos"][0]["texto"] == (
        "Extrapolação extrema: a data final fica muito longe do último registro, e o cenário é incerto demais para ser lido como um "
        "número (aqui, 7 anos à frente).")
    assert simular(b, alvo, {"metodo": "M1"}, janela={"inicio": "202306", "fim": "202406"})["avisos"][0]["texto"] == (
        "Extrapolação além da janela: a data final fica mais longe do que o tempo de história usado no cálculo (2 anos à frente, com "
        "1 ano de história usados no cálculo).")
    assert simulador._tempo(1.0) == "1 ano" and simulador._tempo(29 / 12) == "2,4 anos"
    # A janela do próprio método conta: com 1 ano de janela, 2 anos de horizonte já são extrapolação.
    curta = simular(b, alvo, {"metodo": "M1"}, janela={"inicio": "202306", "fim": "202406"})
    assert curta["horizonte"] == {"anos": 2.0, "aviso": "extrapolacao"}
    # A data final até a origem não é cenário.
    with pytest.raises(ValueError, match="use ano e mês"):
        simulador._competencia_futura("2026-06", "Data final")
    assert simular(b, alvo, {"metodo": "M0"}, "202406")["estado"] == "nao_calculavel"


# --------------------------------------------------------------------------------------------- retroprojeção: os casos
def test_casos_da_retroprojecao_so_com_a_janela_inteira_e_o_alvo_observado():
    """Os casos da retroprojeção (seção C.3): as origens são os junhos com o junho de 3 anos antes e ao menos 1 ano depois; um
    território só entra numa origem com a janela de 3 anos inteira (sem ausência, sem pico já conhecido na origem, sem quebra de
    fonte), com 1 ou mais na origem e 3 anos antes, e só nos prazos em que o alvo foi observado, fora de pico e de quebra."""
    def com(trocas):
        valores = [10] * T
        for periodo, valor in trocas.items():
            valores[PERIODOS.index(periodo)] = valor
        return valores
    b = base({"110001": [10] * T,                      # inteira: todas as origens e todos os prazos
              "110002": com({"201901": None}),         # ausência em jan/2019: fora das origens cuja janela passa por ela (2019 a 2021)
              "110003": com({"202206": None}),         # ausência em jun/2022: fora como origem, como janela (2023) e como alvo
              "110004": [0] * 10 + [5] * 12,           # zero até jun/2018: só entra com 1 ou mais na origem e 3 anos antes (2022 e 2023)
              "110005": com({"201906": 40}),           # pico que volta (10 → 40 → 10), conhecido em jan/2020
              "530010": [100] * 8 + [300] * 14},       # quebra de fonte até jun/2017 (a soma municipal abaixo da contagem estadual)
             estados={"53": [250] * T})
    retro = simulador.retroprojetar(b, guardar=False)
    assert retro.origens == JUNHOS and retro.casos.shape == (68, simulador.COLUNAS)
    casos = {}
    for caso in retro.casos:
        casos.setdefault(b.codigos[int(caso[simulador.LINHA])], {}).setdefault(int(caso[simulador.ANO]), []).append(int(caso[simulador.PRAZO]))
    assert casos == {
        "110001": {2017: [1, 2, 3, 4], 2018: [1, 2, 3, 4], 2019: [1, 2, 3, 4], 2020: [1, 2, 3, 4], 2021: [1, 2, 3], 2022: [1, 2], 2023: [1]},
        "110002": {2017: [1, 2, 3, 4], 2018: [1, 2, 3, 4], 2022: [1, 2], 2023: [1]},
        "110003": {2017: [1, 2, 3, 4], 2018: [1, 2, 3], 2019: [1, 2, 4], 2020: [1, 3, 4], 2021: [2, 3]},
        "110004": {2022: [1, 2], 2023: [1]},
        # O pico de jun/2019 não é alvo (2017 em 2 anos, 2018 em 1 ano) nem fica na janela depois de conhecido (2020 a 2022);
        # em jun/2019, a volta ainda não tinha sido observada: a origem entra, com os 40 do registro (sem observações futuras).
        "110005": {2017: [1, 3, 4], 2018: [2, 3, 4], 2019: [1, 2, 3, 4], 2023: [1]},
        "530010": {2021: [1, 2, 3], 2022: [1, 2], 2023: [1]}}
    do_pico = retro.casos[(retro.casos[:, simulador.LINHA] == b.indice["110005"]) & (retro.casos[:, simulador.ANO] == 2019)]
    assert do_pico[:, simulador.N0].tolist() == [40.0] * 4 and do_pico[:, simulador.OBSERVADO].tolist() == [10.0] * 4
    assert do_pico[:, simulador.PORTE].tolist() == [3.0] * 4   # o porte é o da origem: 40, de 20 a 49
    # Cada caso guarda a projeção de cada método, feita só com os registros até a origem.
    assert tuple(simulador.COLUNA) == ("M0", "M0d", "M0g", "M1", "M2", "M3")
    da_quebra = retro.casos[(retro.casos[:, simulador.LINHA] == b.indice["530010"]) & (retro.casos[:, simulador.ANO] == 2021)]
    assert all(da_quebra[:, simulador.COLUNA[metodo]].tolist() == pytest.approx([300.0] * 3) for metodo in ("M0", "M0d", "M1", "M2", "M3"))


def test_o_ajuste_nao_usa_observacoes_posteriores_a_janela():
    """A mesma janela (até jun/2019) em duas bases que só diferem depois dela: os parâmetros e a base do cenário são os mesmos."""
    a, depois = _base_das_faixas(), _base_das_faixas(depois="201906")
    assert (a.quantidade[:, :12] == depois.quantidade[:, :12]).all() and (a.quantidade[:, 12:] != depois.quantidade[:, 12:]).any()
    janela = {"inicio": "201606", "fim": "201906"}
    retros_de_a, retros_de_depois = retroprojecoes(a), retroprojecoes(depois)
    for metodo in ("M0", "M0d", "M0g", "M1", "M2", "M3"):
        um = simular(a, municipio(a, "111000"), {"metodo": metodo}, "202106", janela, retros=retros_de_a)
        outro = simular(depois, municipio(depois, "111000"), {"metodo": metodo}, "202106", janela, retros=retros_de_depois)
        assert um["estado"] == outro["estado"] == "calculado" and um["parametros"] == outro["parametros"], metodo
        assert [ponto["base"] for ponto in um["trajetoria"]] == [ponto["base"] for ponto in outro["trajetoria"]], metodo
        # Com a origem antes do último registro, o trecho com registros é retroprojeção, ao lado do observado (que difere).
        assert um["trajetoria"][0]["retroprojecao"] is True and "RETROPROJECAO" in avisos(um)
        assert [ponto["data"] for ponto in um["trajetoria"]] == ["202001", "202006", "202101", "202106"]
    assert um["trajetoria"][0]["observado"] == float(a.quantidade[a.indice["111000"], 12])
    # A retroprojeção da base também não vê o futuro: nas origens até jun/2019, o último valor e as projeções de todos os métodos
    # são os mesmos nas duas bases; só muda o observado depois de jun/2019 (e, com ele, o que as origens seguintes projetam).
    casos_de_a, casos_de_depois = retros_de_a["municipios"].casos, retros_de_depois["municipios"].casos
    chaves, projecoes = [simulador.ANO, simulador.PRAZO, simulador.LINHA], [simulador.N0, *simulador.COLUNA.values()]
    assert casos_de_a.shape == casos_de_depois.shape == (60 * 22, simulador.COLUNAS) and (casos_de_a[:, chaves] == casos_de_depois[:, chaves]).all()
    ate_2019 = casos_de_a[:, simulador.ANO] <= 2019
    assert np.array_equal(casos_de_a[ate_2019][:, projecoes], casos_de_depois[ate_2019][:, projecoes], equal_nan=True)
    assert (casos_de_a[~ate_2019][:, simulador.N0] != casos_de_depois[~ate_2019][:, simulador.N0]).all()
    ja_conhecido = casos_de_a[:, simulador.ANO] + casos_de_a[:, simulador.PRAZO] <= 2019
    assert (casos_de_a[ja_conhecido][:, simulador.OBSERVADO] == casos_de_depois[ja_conhecido][:, simulador.OBSERVADO]).all()
    assert (casos_de_a[~ja_conhecido][:, simulador.OBSERVADO] != casos_de_depois[~ja_conhecido][:, simulador.OBSERVADO]).all()


# --------------------------------------------------------------------------------------------- o padrão: o jeito que a base escolhe
def test_erro_frente_ao_ultimo_valor_cada_porte_pesa_o_mesmo_e_os_de_poucos_casos_juntam_se():
    # Os portes com menos de 30 casos juntam-se a um vizinho: ao porte menor ao lado; o primeiro, ao seguinte.
    for portes, esperado in (({0: 40, 1: 10, 2: 40}, [[0, 1], [2]]), ({0: 10, 1: 40}, [[0, 1]]), ({0: 10, 1: 10, 2: 10}, [[0, 1, 2]]),
                             ({3: 30, 5: 30}, [[3], [5]]), ({3: 29, 5: 30}, [[3, 5]]), ({2: 5}, [[2]]),
                             ({0: 40, 1: 10, 2: 10, 3: 40}, [[0, 1, 2], [3]]), ({1: 30, 2: 20, 3: 20, 4: 30}, [[1], [2, 3], [4]])):
        dos_casos = np.array([porte for porte, quantos in portes.items() for _ in range(quantos)], dtype=float)
        assert simulador._grupos_de_porte(dos_casos) == esperado, portes
    # Dois portes de 30 casos: num, o jeito erra 1 e o último valor erra 2 (razão 0,5); no outro, erram 300 e 200 (razão 1,5).
    # Com o mesmo peso para cada porte, o erro frente ao último valor é 1,0; somando os erros, seria 1,49 (o porte maior mandaria).
    m1 = simulador.COLUNA["M1"]
    casos = _casos_a_mao([(2020, 1, 1, 12.0, 11.0, 10.0)] * 30 + [(2020, 1, 6, 700.0, 400.0, 500.0)] * 30, "M1")
    assert simulador._frente_ao_m0(casos, m1, np.ones(60, dtype=bool)) == pytest.approx(1.0)
    # Com 29 casos no porte menor, os dois portes juntam-se, e os erros somam-se.
    casos = _casos_a_mao([(2020, 1, 1, 12.0, 11.0, 10.0)] * 29 + [(2020, 1, 6, 700.0, 400.0, 500.0)] * 30, "M1")
    assert simulador._frente_ao_m0(casos, m1, np.ones(59, dtype=bool)) == pytest.approx((29 * 1 + 30 * 300) / (29 * 2 + 30 * 200))
    # Sem casos, ou quando o último valor não errou, não há razão a calcular.
    assert simulador._frente_ao_m0(casos, m1, np.zeros(59, dtype=bool)) is None
    parado = _casos_a_mao([(2020, 1, 1, 10.0, 11.0, 10.0)] * 30, "M1")
    assert simulador._frente_ao_m0(parado, m1, np.ones(30, dtype=bool)) is None
    # Sem série anual ou com menos de 3 origens, não há escolha: o padrão é o último valor, com o motivo.
    sem_escolha = {"metodo": "M0", "origens": 7, "combinacoes": 0, "candidatos": [], "excecoes": [], "por_porte": []}
    assert simulador._escolher(casos, 7, False) == {**sem_escolha, "motivo": "sem_serie_anual"}
    assert simulador._escolher(casos, 2, True) == {**sem_escolha, "motivo": "poucas_origens", "origens": 2}
    assert simulador._escolher(np.empty((0, simulador.COLUNAS)), 7, True) == {**sem_escolha, "motivo": "poucas_origens"}
    assert (simulador.MINIMO_DE_ORIGENS, simulador.MINIMO_POR_PORTE_NA_ESCOLHA, simulador.TOLERANCIA_DA_ESCOLHA, simulador.PROXIMIDADE) == (
        3, 30, 0.05, ("M1", "M0d", "M0g"))


@pytest.mark.parametrize("grupos, por_grupo, ruido, partida, com_grupo, escolhido, valem, erra_menos", [
    # Rondônia cresce 6% ao ano e o Acre fica parado: o crescimento do grupo de cima erra bem menos; o do próprio território e o
    # da base toda também valem, mas erram mais de 5% acima dele.
    ({"11": 0.06, "12": 0.0}, 30, 0.08, (110, 130), True, "M0d", {"M1": True, "M0d": True, "M0g": True}, "M0d"),
    # Tendência pequena diante do ruído (+3% e −1% ao ano): a taxa do próprio território erra mais que o último valor e não vale.
    ({"11": 0.03, "12": -0.01}, 30, 0.08, (140, 180), True, "M0d", {"M1": False, "M0d": True, "M0g": True}, "M0d"),
    # Os dois grupos crescem igual: a base toda erra um pouco menos, mas fica o grupo de cima, o mais próximo a até 5% do melhor.
    ({"11": 0.05, "12": 0.05}, 30, 0.08, (110, 130), True, "M0d", {"M1": True, "M0d": True, "M0g": True}, "M0g"),
    # Vinte grupos de 3 territórios: o crescimento de um grupo tão pequeno vale, mas erra mais de 5% acima do da base toda.
    ({str(10 + grupo): 0.05 for grupo in range(20)}, 3, 0.08, (110, 130), True, "M0g", {"M1": True, "M0d": True, "M0g": True}, "M0g"),
    # Sem grupo de cima, os candidatos são o próprio território e a base toda: com todos crescendo igual, a base toda.
    ({"11": 0.05, "12": 0.05}, 30, 0.08, (110, 130), False, "M0g", {"M1": True, "M0g": True}, "M0g"),
    # Sem grupo de cima e cada território com o seu crescimento (+6% ou −2% ao ano, quase sem ruído): o próprio território.
    ({"11": 0.06, "12": -0.02}, 30, 0.01, (130, 150), False, "M1", {"M1": True, "M0g": True}, "M1"),
    # Sem tendência, só ruído: nenhum jeito erra menos que manter o último valor, e o padrão é o último valor.
    ({"11": 0.0, "12": 0.0}, 30, 0.08, (150, 250), True, "M0", {"M1": False, "M0d": False, "M0g": False}, None),
], ids=["o-grupo-de-cima-erra-menos", "o-proprio-territorio-nao-vale", "o-mais-proximo-a-ate-5-por-cento-do-melhor", "grupos-pequenos-a-base-toda",
        "sem-grupo-a-base-toda", "sem-grupo-o-proprio-territorio", "nenhum-vale"])
def test_o_padrao_e_o_jeito_de_projetar_que_a_propria_base_escolhe(grupos, por_grupo, ruido, partida, com_grupo, escolhido, valem, erra_menos):
    """A regra de escolha (seção C.3) em bases sintéticas de um porte só (100 a 299 médicos), com 60 territórios e 7 origens. Os
    candidatos do motor são conferidos com a referência refeita aqui; o que cada base deve dar está escrito por extenso."""
    b = base(_series_de_grupos(grupos, por_grupo, ruido, partida), com_grupo=com_grupo)
    retro = simulador.retroprojetar(b, guardar=False)
    casos = _casos_de_referencia(b)
    assert retro.origens == JUNHOS and len(retro.casos) == len(casos) == 60 * 22 and {caso["porte"] for caso in casos} == {5}
    assert _confere_candidatos(retro.escolha, casos) == valem
    escolha = retro.escolha
    assert (escolha["metodo"], escolha["motivo"], escolha["origens"], escolha["combinacoes"], escolha["excecoes"]) == (
        escolhido, "escolhido" if any(valem.values()) else "nenhum_vale", 7, 22, [])
    erros = {candidato["metodo"]: candidato["frente_ao_m0"] for candidato in escolha["candidatos"] if candidato["vale"]}
    assert min(erros, key=erros.get, default=None) == erra_menos
    if erros:
        # Fica o mais próximo do território a até 5% do melhor: os mais próximos que ele, quando valem, erram mais de 5% acima.
        mais_proximos = ("M1", "M0d", "M0g")[:("M1", "M0d", "M0g").index(escolhido)]
        assert erros[escolhido] <= 1.05 * erros[erra_menos] and all(erros[metodo] > 1.05 * erros[erra_menos] for metodo in mais_proximos if metodo in erros)
    # O cenário do método padrão usa o jeito escolhido; quando nenhum vale, mantém o último valor e diz por quê.
    cenario = simular(b, municipio(b, b.codigos[0]), {"metodo": "padrao"}, retros={"municipios": retro, "estados": None})
    assert cenario["metodo"] == jeito("padrao", escolhido, escolhido)
    assert avisos(cenario)[0] == ("PADRAO_E_O_ULTIMO_VALOR" if escolhido == "M0" else "HORIZONTE_CAUTELA")
    if escolhido == "M0":
        assert aviso(cenario, "PADRAO_E_O_ULTIMO_VALOR") == NENHUM_VALE
        assert cenario["entenda"]["jeito"]["texto"] == ("O cenário parte do último registro usado (jun/2024) e mantém o valor dele. Nesta base, "
                                                        "nenhum outro jeito errou menos que manter o último valor, quando refeito no passado.")
    else:
        assert cenario["entenda"]["jeito"]["texto"].endswith(ERROU_MENOS)
    # As faixas são as do jeito escolhido (as do último valor, quando nenhum vale): no porte dos casos, há faixa de 8 em 10.
    assert retro.faixas[(8, 5, 1)]["como"] == "propria" and retro.faixas[(8, 5, 1)]["casos"] == 60 * 7


def test_sem_retroprojecao_bastante_o_padrao_e_o_ultimo_valor():
    grupos = {"11": 0.06, "12": 0.0}
    # Registros de 2019 a 2024: só duas origens (jun/2022 e jun/2023) têm 3 anos antes e 1 ano depois. Sem 3 origens, não há
    # escolha nem faixa: o padrão é manter o último valor, com o aviso.
    curtos = tuple(str(ano) + mes for ano in range(2019, 2025) for mes in ("01", "06"))
    b = base(_series_de_grupos(grupos, periodos=curtos), periodos=curtos)
    retro = simulador.retroprojetar(b, guardar=False)
    assert retro.origens == ("202206", "202306") and retro.faixas == {} and len(retro.casos) == 60 * 3
    assert retro.escolha == {"metodo": "M0", "motivo": "poucas_origens", "origens": 2, "combinacoes": 0, "candidatos": [], "excecoes": [],
                             "por_porte": []}
    cenario = simular(b, municipio(b, "111000"), {"metodo": "padrao"})
    assert cenario["metodo"] == jeito("padrao", "M0", "M0") and avisos(cenario) == ["SEM_RETROPROJECAO", "HORIZONTE_CAUTELA"]
    assert aviso(cenario, "SEM_RETROPROJECAO") == ("A base não tem história bastante para a retroprojeção (são menos de 3 origens com 3 anos "
                                                   "antes e 1 ano depois): o cenário mantém o último valor.")
    sem_origens = SEM_RETROPROJECAO_BASTANTE + "são menos de 3 origens com 3 anos antes e 1 ano depois."
    assert cenario["faixa"] == {"estado": "indisponivel", "motivo": sem_origens, "rotulo": None, "em_10": 8}
    n0 = str(int(b.quantidade[b.indice["111000"], -1]))
    assert cenario["entenda"] == {"jeito": {"texto": "O cenário parte do último registro usado (jun/2024) e mantém o valor dele. Sem retroprojeção "
                                                     "bastante nesta base, o padrão é manter o último valor.",
                                            "exemplo": "De " + n0 + " médicos em jun/2024, a base do cenário vai a " + n0 + " um ano depois, sem "
                                                       "contar intervenções."},
                                  "faixa": {"texto": sem_origens, "exemplo": SEM_FAIXA}}
    # Com um ano a mais de registros (2018 a 2024), são três origens: a escolha já existe (aqui, o grupo de cima), em 6
    # combinações de origem e prazo. A faixa de 8 em 10 ainda não: pede 200 casos por prazo, e são 180 em 1 ano.
    medios = tuple(str(ano) + mes for ano in range(2018, 2025) for mes in ("01", "06"))
    b = base(_series_de_grupos(grupos, periodos=medios), periodos=medios)
    retro = simulador.retroprojetar(b, guardar=False)
    assert retro.origens == ("202106", "202206", "202306")
    assert _confere_candidatos(retro.escolha, _casos_de_referencia(b)) == {"M1": True, "M0d": True, "M0g": True}
    assert (retro.escolha["metodo"], retro.escolha["motivo"], retro.escolha["origens"], retro.escolha["combinacoes"]) == ("M0d", "escolhido", 3, 6)
    assert [retro.faixas[(8, 5, anos)] for anos in (1, 2, 3)] == [
        {"estado": "indisponivel", "motivo": "poucos_casos", "casos": casos, "pede": 200, "como": "indisponivel"} for casos in (180, 120, 60)]
    assert (8, 5, 4) not in retro.faixas   # nenhuma origem tem o alvo de 4 anos
    retros = {"municipios": retro, "estados": None}
    cenario = simular(b, municipio(b, "111000"), {"metodo": "padrao"}, retros=retros)
    assert cenario["metodo"] == jeito("padrao", "M0d", "M0d") and avisos(cenario) == ["HORIZONTE_CAUTELA"]
    assert cenario["faixa"] == {"estado": "indisponivel", "motivo": poucos_casos(180), "rotulo": None, "em_10": 8}
    # A de 5 em 10 pede 80 casos: existe até 2 anos (120 casos), ainda sem conferência (provisória); em 3 anos, 60 casos não bastam.
    em_5 = simular(b, municipio(b, "111000"), {"metodo": "padrao"}, "202706", em_10=5, retros=retros)
    assert (em_5["faixa"]["estado"], em_5["faixa"]["ate_anos"], em_5["final"]["faixa"]) == ("disponivel", 2, None)
    assert [None if ponto["faixa"] is None else (ponto["faixa"]["anos"], ponto["faixa"]["estado"]) for ponto in em_5["trajetoria"]] == [
        (1, "provisoria"), (1, "provisoria"), (2, "provisoria"), (2, "provisoria"), None, None]
    assert aviso(em_5, "FAIXA_ATE_4_ANOS") == faixa_ate("2 anos", 5)
    # Sem série anual (nenhum mês se repete em todos os anos): não há retroprojeção, e o padrão é o último valor. A janela
    # padrão são os 3 anos até o último registro, pelo tempo: aqui, os 4 registros desde jul/2021.
    irregulares = ("201402", "201505", "201608", "201711", "201901", "202004", "202107", "202210", "202312", "202403")
    b = base(_series_de_grupos(grupos, periodos=irregulares), periodos=irregulares)
    assert b.ancora is None
    retro = simulador.retroprojetar(b, guardar=False)
    assert (retro.origens, retro.casos.shape, retro.faixas, retro.tabela) == ((), (0, simulador.COLUNAS), {}, ())
    assert retro.escolha == {"metodo": "M0", "motivo": "sem_serie_anual", "origens": 0, "combinacoes": 0, "candidatos": [], "excecoes": [],
                             "por_porte": []}
    retros = {"municipios": retro, "estados": None}
    cenario = simular(b, municipio(b, "111000"), {"metodo": "padrao"}, "202603", retros=retros)
    assert cenario["metodo"] == jeito("padrao", "M0", "M0") and avisos(cenario) == ["SEM_RETROPROJECAO", "HORIZONTE_CAUTELA"]
    assert aviso(cenario, "SEM_RETROPROJECAO") == ("A base não tem série anual (nenhum mês se repete em todos os anos): sem retroprojeção, o "
                                                   "cenário mantém o último valor.")
    assert cenario["parametros"]["janela"] == {"inicio": "202107", "fim": "202403", "registros": 4}
    assert cenario["faixa"] == {"estado": "indisponivel", "motivo": SEM_RETROPROJECAO_BASTANTE + "nenhum mês se repete em todos os anos.",
                                "rotulo": None, "em_10": 8}
    assert [ponto["data"] for ponto in cenario["trajetoria"]] == ["202503", "202603"]
    # Sem o registro de 3 anos antes (o mesmo mês), o crescimento do estado e o da base toda não podem ser medidos.
    for metodo, sem in (("M0d", "Sem o crescimento recente do estado (não há registros do estado 3 anos antes do último registro usado)"),
                        ("M0g", "Sem o crescimento recente da base toda (não há registros 3 anos antes do último registro usado)")):
        pedido = simular(b, municipio(b, "111000"), {"metodo": metodo}, "202603", retros=retros)
        assert pedido["metodo"]["usado"] == "M0" and pedido["metodo"]["voltou_ao_m0"] is True, metodo
        assert aviso(pedido, "VOLTA_AO_M0") == sem + ": o cenário usa a persistência (o último valor se mantém)."
    # Numa base de registros espaçados (aqui, um a cada 4 anos), nenhum outro registro cai nos 3 anos até o último: a janela padrão
    # começa no registro anterior, para ter dois registros. A taxa composta, pedida pelo nome, é a desses 4 anos.
    espacados = ("201006", "201406", "201806", "202206")
    b = base({"110001": [10, 12, 15, 20], "110002": [90] * 4}, periodos=espacados)
    assert b.ancora is None and simulador._janela(b, None) == (2, 3, True) and simulador._janela(b, {"fim": "201806"}) == (1, 2, False)
    with pytest.raises(ValueError, match="Janela inválida: ela precisa de pelo menos dois registros, com o início antes do fim."):
        simulador._janela(b, {"fim": "201006"})   # o primeiro registro da base não tem registro anterior
    body = simulador.compute(None, {"base": {"municipios": {"ids": ["code:110001"]}}, "cenarios": [{"metodo": "padrao"}, {"metodo": "M1"}]}, base=b)
    assert body["janela"] == {"inicio": "201806", "fim": "202206", "registros": 2, "anos": 4.0, "padrao": True}
    padrao, composta = body["territorios"][0]["cenarios"]
    assert padrao["metodo"] == jeito("padrao", "M0", "M0") and padrao["parametros"]["janela"] == {"inicio": "201806", "fim": "202206", "registros": 2}
    assert (composta["parametros"]["anos"], composta["parametros"]["taxa_pct"], composta["final"]["data"], composta["final"]["total"]) == (
        4.0, pytest.approx(100 * ((20 / 15) ** 0.25 - 1)), "202406", pytest.approx(20 * (20 / 15) ** 0.5))
    # Com um buraco de 4 anos só antes do último registro, a janela padrão é a do registro anterior; a que termina antes do buraco
    # continua com os 3 anos, pelo tempo (7 registros), como em toda base com outro registro nesses 3 anos.
    com_buraco = PERIODOS[:14] + ("202406",)
    b = base({"110001": [10 + k for k in range(15)], "110002": [90] * 15}, periodos=com_buraco)
    assert simulador._janela(b, None) == (13, 14, True) and simulador._janela(b, {"fim": "202006"}) == (7, 13, False)


def test_padrao_sem_a_taxa_composta_do_territorio_volta_ao_ultimo_valor():
    """Numa base que escolhe a taxa composta do próprio território, ela não se aplica a quem tem menos de dois registros nos 3 anos
    até a origem, ou zero no primeiro ou no último deles. O padrão desses territórios volta ao último valor, com o aviso (como nos
    outros jeitos escolhidos, quando falta o crescimento que eles pedem) e sem faixa; pedida pelo nome, a taxa composta continua
    "não aplicável"."""
    b = base({"110001": [100 * 1.1 ** a for a in ANOS], "110002": [50] * T,
              "110003": [0] * 16 + [5] * 6,     # zero em jun/2021, 3 anos antes da origem
              "110004": [None] * 21 + [7],      # um registro só
              "110005": [3] * 10 + [0] * 12,    # zero na origem
              "110006": [1] * T})
    retros = retroprojecoes(b)
    assert retros["municipios"].escolha["metodo"] == "M1"
    sem_faixa = {"estado": "indisponivel", "motivo": SO_O_ULTIMO_VALOR.format(ROTULOS["M1"]), "rotulo": None, "em_10": 8}
    for codigo, n0, registros in (("110003", 5, 7), ("110004", 7, 1), ("110005", 0, 7)):
        alvo = municipio(b, codigo)
        padrao = simular(b, alvo, {"metodo": "padrao"}, retros=retros)
        assert padrao["metodo"] == jeito("padrao", "M0", "M1", voltou_ao_m0=True), codigo
        assert avisos(padrao) == ["VOLTA_AO_M0", "HORIZONTE_CAUTELA"] and aviso(padrao, "VOLTA_AO_M0") == SEM_A_TAXA_COMPOSTA, codigo
        assert (padrao["parametros"]["n0"], padrao["parametros"]["janela"]["registros"], padrao["final"]["total"]) == (n0, registros, n0), codigo
        assert padrao["faixa"] == sem_faixa and padrao["entenda"]["faixa"] == {"texto": sem_faixa["motivo"], "exemplo": SEM_FAIXA}, codigo
        assert padrao["entenda"]["jeito"]["texto"] == "O cenário parte do último registro usado (jun/2024) e mantém o valor dele. " + NAO_PODE_SER_USADO
        # A janela com um registro só é dita assim no texto do cenário, e não "de jun/2024 a jun/2024".
        assert ("as premissas janela com um registro só (jun/2024); sem intervenção" if registros == 1 else
                "as premissas janela de jun/2021 a jun/2024; sem intervenção") in padrao["texto"], padrao["texto"]
        pelo_nome = simular(b, alvo, {"metodo": "M1"}, retros=retros)
        assert pelo_nome["estado"] == "nao_aplicavel" and "com início em zero, a taxa não é definida" in pelo_nome["motivo"], codigo
    # Com uma intervenção, o território em zero passa a ter os médicos acrescentados: o padrão já não fica "não aplicável".
    com = simular(b, municipio(b, "110005"), {"metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]},
                  retros=retros)
    assert (com["final"]["base"], com["final"]["intervencao"], com["final"]["total"]) == (0, 4, 4) and "M110005 teria 4 médicos em jun/2026" in com["texto"]
    # Onde a taxa composta se aplica, o padrão é ela. Com 1 médico, os textos usam o singular.
    assert simular(b, municipio(b, "110002"), {"metodo": "padrao"}, retros=retros)["metodo"] == jeito("padrao", "M1", "M1")
    com_um = simular(b, municipio(b, "110006"), {"metodo": "padrao"}, retros=retros)
    assert com_um["metodo"] == jeito("padrao", "M1", "M1") and com_um["texto"].endswith("M110006 teria 1 médico em jun/2026. Base: registros até jun/2024.")
    assert com_um["entenda"]["jeito"]["exemplo"] == "De 1 médico em jun/2024, a base do cenário vai a 1 um ano depois, sem contar intervenções."


def test_padrao_sem_o_registro_de_3_anos_antes_da_origem_nao_usa_a_taxa_composta_de_outra_janela():
    """A taxa composta que a base escolhe é a dos 3 anos até a origem, como na retroprojeção — e a faixa foi medida para ela.
    Quando a base não tem o registro de 3 anos antes da origem (registros espaçados, ou origem perto do começo), o padrão não usa
    a taxa de outra janela com essa faixa: volta ao último valor, com o aviso e sem faixa. Pedida pelo nome, a taxa composta
    continua a ser a da janela do cenário, sem faixa."""
    # Dois registros por ano de 2010 a 2020 e, depois, só jun/2024. São 40 territórios, cada um com o seu crescimento (de −3% a
    # +9% ao ano): a retroprojeção (origens de jan/2013 a jan/2019) escolhe a taxa composta do próprio território.
    com_buraco = tuple(str(ano) + mes for ano in range(2010, 2021) for mes in ("01", "06")) + ("202406",)
    anos = [(series_brasil.mes_da_competencia(periodo) - series_brasil.mes_da_competencia("201001")) / 12 for periodo in com_buraco]
    b = base({"11%04d" % k: [_inteiro((100 + k) * (0.97 + 0.003 * k) ** a) for a in anos] for k in range(40)}, periodos=com_buraco)
    retros = retroprojecoes(b)
    retro, alvo = retros["municipios"], municipio(b, "110020")
    assert b.ancora == "01" and retro.origens == tuple(str(ano) + "01" for ano in range(2013, 2020)) and retro.escolha["metodo"] == "M1"
    serie = [float(valor) for valor in alvo.serie]
    sem_faixa = {"estado": "indisponivel", "motivo": SO_O_ULTIMO_VALOR.format(ROTULOS["M1"]), "rotulo": None, "em_10": 8}

    def volta_ao_ultimo_valor(cenario, n0, outros_avisos):
        assert cenario["metodo"] == jeito("padrao", "M0", "M1", voltou_ao_m0=True)
        assert avisos(cenario) == ["VOLTA_AO_M0", "HORIZONTE_CAUTELA", *outros_avisos] and aviso(cenario, "VOLTA_AO_M0") == SEM_A_TAXA_COMPOSTA
        assert (cenario["parametros"]["n0"], cenario["final"]["total"]) == (n0, n0)
        assert cenario["faixa"] == sem_faixa and all(ponto["faixa"] is None for ponto in cenario["trajetoria"])
        assert cenario["entenda"]["jeito"]["texto"].endswith(NAO_PODE_SER_USADO)

    # No último registro (jun/2024), o registro anterior é o de jun/2020, 4 anos antes: a base não tem o de jun/2021.
    assert simulador._janela(b, None) == (21, 22, True) and simulador._antes(b, 22) is None
    volta_ao_ultimo_valor(simular(b, alvo, {"metodo": "padrao"}, retros=retros), serie[22], [])
    # Pedida pelo nome, a taxa composta é a da janela do cenário (os 4 anos entre os dois registros), sem faixa: não é a janela
    # que a base escolheu.
    pelo_nome = simular(b, alvo, {"metodo": "M1"}, retros=retros)
    assert pelo_nome["metodo"] == jeito("M1", "M1", "M1") and pelo_nome["parametros"]["janela"] == {"inicio": "202006", "fim": "202406", "registros": 2}
    assert (pelo_nome["parametros"]["anos"], pelo_nome["parametros"]["taxa_pct"]) == (4.0, pytest.approx(100 * ((serie[22] / serie[21]) ** 0.25 - 1)))
    assert pelo_nome["faixa"] == {"estado": "indisponivel", "motivo": SO_DO_ESCOLHIDO.format(ROTULOS["M1"]), "rotulo": None, "em_10": 8}
    # Com a origem perto do começo da base (jun/2012: não há registro de jun/2009), o mesmo.
    volta_ao_ultimo_valor(simular(b, alvo, {"metodo": "padrao"}, "201406", {"fim": "201206"}, retros=retros), serie[5], ["RETROPROJECAO"])
    # Onde a base tem o registro de 3 anos antes — a origem em jun/2020, antes do buraco, e em jan/2013, a primeira com ele —, o
    # padrão é a taxa composta desses 3 anos (7 registros), com a faixa.
    for fim, final, primeiro, origem in (("202006", "202206", 15, 21), ("201301", "201501", 0, 6)):
        cenario = simular(b, alvo, {"metodo": "padrao"}, final, {"fim": fim}, retros=retros)
        assert cenario["metodo"] == jeito("padrao", "M1", "M1"), fim
        assert cenario["parametros"]["janela"] == {"inicio": com_buraco[primeiro], "fim": fim, "registros": 7} and cenario["parametros"]["anos"] == 3.0, fim
        assert cenario["parametros"]["taxa_pct"] == pytest.approx(100 * ((serie[origem] / serie[primeiro]) ** (1 / 3) - 1)), fim
        assert cenario["faixa"]["estado"] == "disponivel" and cenario["final"]["faixa"]["anos"] == 2, fim


def test_num_porte_em_que_o_escolhido_erra_mais_vale_o_ultimo_valor_e_o_aviso_da_taxa_composta_vem_da_tabela():
    """A exceção por porte (seção C.3, item 4): os municípios de 10 a 19 médicos ficam parados num estado que cresce; para eles, o
    crescimento do estado erra mais que manter o último valor em todos os prazos. O jeito escolhido para a base continua sendo o
    grupo de cima (erra menos nos outros dois portes, e cada porte pesa o mesmo), mas nesse porte o padrão é o último valor."""
    b = _base_da_excecao()
    retros = retroprojecoes(b)
    retro, casos = retros["municipios"], _casos_de_referencia(b)
    assert sorted({caso["porte"] for caso in casos}) == [2, 5, 6]
    assert _confere_candidatos(retro.escolha, casos) == {"M1": False, "M0d": True, "M0g": True} and retro.escolha["metodo"] == "M0d"

    def celula(metodo, porte, prazo):
        """O erro de um método ÷ o do último valor, num porte e num prazo (as células com 30 casos ou mais)."""
        da_celula = [caso for caso in casos if (caso["porte"], caso["prazo"]) == (porte, prazo)]
        assert len(da_celula) >= 30
        return _erro(da_celula, metodo) / _erro(da_celula, "M0")
    prazos = (1, 2, 3, 4)
    assert retro.escolha["por_porte"] == [{"porte": porte, "frente_ao_m0": pytest.approx([celula("M0d", porte, prazo) for prazo in prazos])}
                                          for porte in (2, 5, 6)]
    assert all(celula("M0d", 2, prazo) > 1 for prazo in prazos) and all(celula("M0d", porte, prazo) < 1 for porte in (5, 6) for prazo in prazos)
    assert retro.escolha["excecoes"] == [2]
    # "Como os métodos se saíram no passado": a tabela traz o mesmo erro, por método, porte e prazo.
    tabela = {(linha["metodo"], linha["porte"], linha["anos"]): linha for linha in retro.tabela}
    for metodo in ("M0d", "M0g", "M1"):
        for porte in (2, 5, 6):
            assert [tabela[(metodo, porte, prazo)]["frente_ao_m0"] for prazo in prazos] == pytest.approx([celula(metodo, porte, prazo) for prazo in prazos])
    assert [tabela[("M0", porte, 1)]["casos"] for porte in (2, 5, 6)] == [210, 420, 210]
    # O padrão de um município de 10 a 19 médicos é o último valor, com o aviso; nos outros portes, o jeito escolhido.
    pequeno, medio, grande = municipio(b, "112000"), municipio(b, "111000"), municipio(b, "113000")
    assert [reguas.porte_de(alvo.serie[-1]) for alvo in (pequeno, medio, grande)] == [2, 5, 6]
    do_pequeno = simular(b, pequeno, {"metodo": "padrao"}, retros=retros)
    assert do_pequeno["metodo"] == jeito("padrao", "M0", "M0d") and avisos(do_pequeno) == ["PORTE_USA_O_ULTIMO_VALOR", "HORIZONTE_CAUTELA"]
    assert aviso(do_pequeno, "PORTE_USA_O_ULTIMO_VALOR") == (
        "Em territórios de 10 a 19 médicos, o jeito de projetar escolhido pela base errou mais que manter o último valor, em todos os prazos "
        "conferidos: o cenário mantém o último valor.")
    assert do_pequeno["final"]["total"] == pequeno.serie[-1] and do_pequeno["entenda"]["jeito"]["texto"] == (
        "O cenário parte do último registro usado (jun/2024) e mantém o valor dele. Neste porte, o jeito escolhido pela base errou mais que "
        "manter o último valor, quando refeito no passado: o cenário mantém o último valor.")
    # A faixa da base é a do jeito escolhido: neste porte, o padrão fica sem ela, e o motivo diz por quê. Pedido pelo nome, o
    # último valor é "outro jeito" (o motivo de sempre); o crescimento do estado, pedido pelo nome, tem a faixa dele.
    assert do_pequeno["faixa"] == {"estado": "indisponivel", "motivo": SO_O_ULTIMO_VALOR.format(ROTULOS["M0d"]), "rotulo": None, "em_10": 8}
    assert simular(b, pequeno, {"metodo": "M0"}, retros=retros)["faixa"]["motivo"] == SO_DO_ESCOLHIDO.format(ROTULOS["M0d"])
    assert simular(b, pequeno, {"metodo": "M0d"}, retros=retros)["faixa"]["estado"] == "disponivel"
    for alvo in (medio, grande):
        do_porte = simular(b, alvo, {"metodo": "padrao"}, retros=retros)
        assert do_porte["metodo"] == jeito("padrao", "M0d", "M0d") and "PORTE_USA_O_ULTIMO_VALOR" not in avisos(do_porte)
    # O aviso da taxa composta (M1) também vem da tabela da própria base, por porte (antes, valia um corte fixo de 100 médicos):
    # aparece onde ela errou mais que o último valor em todos os prazos — aqui, só de 10 a 19 médicos.
    assert all(celula("M1", 2, prazo) > 1 for prazo in prazos)
    assert celula("M1", 5, 1) > 1 > celula("M1", 5, 4) and celula("M1", 6, 4) < 1
    da_taxa = simular(b, pequeno, {"metodo": "M1"}, retros=retros)
    assert da_taxa["metodo"]["usado"] == "M1" and aviso(da_taxa, "M1_ABAIXO_DE_100") == (
        "Em territórios de 10 a 19 médicos, este método errou mais do que simplesmente manter o último valor, quando conferido com o passado da base.")
    assert all("M1_ABAIXO_DE_100" not in avisos(simular(b, alvo, {"metodo": "M1"}, retros=retros)) for alvo in (medio, grande))


def _base_sem_a_contagem_dos_grupos(com_grupo):
    """A base de Rondônia (6% ao ano) e do Acre (parado), sem a contagem própria dos grupos, com o todo como a soma das unidades
    (como numa planilha enviada); `com_grupo=False`: sem grupo de cima."""
    b = base(_series_de_grupos({"11": 0.06, "12": 0.0}), com_grupo=com_grupo)
    return replace(b, brasil=np.nansum(b.quantidade, axis=0))


@pytest.mark.parametrize("com_grupo, escolhido", [(True, "M0d"), (False, "M0g")])
def test_o_todo_numa_base_sem_a_contagem_dos_grupos_usa_a_taxa_composta_da_serie_dele(com_grupo, escolhido):
    """Numa base sem a contagem própria dos grupos de cima, o todo não tem retroprojeção própria (é uma série só) nem a dos
    grupos: vale a das unidades. Quando o jeito escolhido para elas é o crescimento do grupo de cima ou o da base toda, o todo —
    que é a própria base toda — usa a taxa composta da série dele nos 3 anos até a origem, como provisório."""
    b = _base_sem_a_contagem_dos_grupos(com_grupo)
    retros = retroprojecoes(b)
    assert retros["estados"] is None and retros["municipios"].escolha["metodo"] == escolhido
    todo = series_brasil.brasil(b)
    cenario = simular(b, todo, {"metodo": "padrao"}, retros=retros)
    taxa = (b.brasil[-1] / b.brasil[PERIODOS.index("202106")]) ** (1 / 3) - 1
    assert cenario["metodo"] == jeito("padrao", "M1", escolhido, provisorio=True)
    assert cenario["parametros"]["taxa_pct"] == pytest.approx(100 * taxa) and cenario["final"]["total"] == pytest.approx(b.brasil[-1] * (1 + taxa) ** 2)
    assert cenario["parametros"]["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7}
    assert avisos(cenario) == ["PADRAO_PROVISORIO_DO_NIVEL", "HORIZONTE_CAUTELA"]
    provisorio = "Para o Brasil, o método padrão é provisório: uma série só não tem retroprojeção própria, e vale o jeito escolhido para os municípios."
    assert aviso(cenario, "PADRAO_PROVISORIO_DO_NIVEL") == provisorio + " Ele só foi conferido num período de crescimento."
    # O todo não tem faixa: uma série só não tem retroprojeção própria. O motivo é esse com o padrão e com um método pedido pelo nome.
    sem_faixa = {"estado": "indisponivel", "motivo": "Não há faixa para o Brasil: uma série só não tem retroprojeção própria.", "rotulo": None, "em_10": 8}
    assert cenario["faixa"] == sem_faixa and cenario["final"]["faixa"] is None
    assert [simular(b, todo, {"metodo": metodo}, retros=retros)["faixa"] for metodo in ("M1", "M0")] == [sem_faixa] * 2
    # A frase sobre o período de crescimento é só da base do Brasil: numa planilha, o aviso para na primeira.
    da_planilha = replace(b, origem="planilha")
    assert aviso(simular(da_planilha, series_brasil.brasil(da_planilha), {"metodo": "padrao"}, retros=retros), "PADRAO_PROVISORIO_DO_NIVEL") == provisorio
    # Pedidos pelo nome, o crescimento do grupo de cima e o da base toda não se aplicam ao todo.
    assert [simular(b, todo, {"metodo": metodo}, retros=retros)["estado"] for metodo in ("M0d", "M0g")] == ["nao_aplicavel"] * 2


def test_o_entenda_do_todo_com_a_taxa_composta_nao_diz_que_o_cenario_mantem_o_ultimo_valor():
    """O "Entenda" do jeito de projetar, quando o padrão do todo troca o crescimento do grupo de cima (ou o da base toda) pela taxa
    composta da série dele: o cenário não mantém o último valor (segue a taxa composta), e o texto diz por que essa é a taxa que
    vale. (A primeira versão dizia "…o jeito escolhido pela base não pôde ser usado, e o cenário mantém o último valor"; o defeito
    foi achado ao escrever estes testes e corrigido no motor.)"""
    b = _base_sem_a_contagem_dos_grupos(True)
    cenario = simular(b, series_brasil.brasil(b), {"metodo": "padrao"})
    assert cenario["metodo"]["usado"] == "M1" and cenario["final"]["total"] > cenario["parametros"]["n0"]
    taxa, n0 = (b.brasil[-1] / b.brasil[PERIODOS.index("202106")]) ** (1 / 3) - 1, b.brasil[-1]
    assert cenario["entenda"]["jeito"] == {
        "texto": "O cenário parte do último registro usado (jun/2024) e segue o crescimento do próprio território: +" + _br(100 * taxa, 2) +
                 "% ao ano na janela usada. Para o Brasil, o crescimento da base toda é o da própria série: vale a taxa composta dos 3 anos "
                 "até a origem, como padrão provisório.",
        "exemplo": "De " + _br(n0) + " médicos em jun/2024, a base do cenário vai a " + _br(n0 * (1 + taxa), 1) + " um ano depois, sem contar "
                   "intervenções."}
    assert "mantém o último valor" not in cenario["entenda"]["jeito"]["texto"]


# --------------------------------------------------------------------------------------------- as faixas
def test_faixas_de_5_8_e_9_em_cada_10_percentis_e_casos_minimos():
    """As três faixas (seção C.4): os percentis do erro relativo (25 a 75, 10 a 90, 5 a 95) e os casos mínimos (80, 200 e 400: 20
    fora de cada lado). Casos de um porte e de uma origem só, com o erro espalhado por igual de −30% a +50%."""
    assert simulador.FAIXAS_EM_10 == FAIXAS and simulador.FAIXA_PADRAO == 8 and simulador.HORIZONTES_DA_FAIXA == (1, 2, 3, 4)
    assert simulador.ROTULOS_DOS_PORTES_DA_FAIXA == reguas.ROTULOS_DOS_PORTES and len(reguas.ROTULOS_DOS_PORTES) == 10
    for quantos, disponiveis in ((79, ()), (80, (5,)), (199, (5,)), (200, (5, 8)), (399, (5, 8)), (400, (5, 8, 9))):
        erros = np.linspace(-0.3, 0.5, quantos)
        faixas = simulador._faixas(_casos_com_erro([(2020, 1, 4, erro) for erro in erros]), "M0")
        for em_10, (inferior, superior, minimo, meta) in FAIXAS.items():
            if em_10 not in disponiveis:
                assert faixas[(em_10, 4, 1)] == {"estado": "indisponivel", "motivo": "poucos_casos", "casos": quantos, "pede": minimo,
                                                 "como": "indisponivel"}, (quantos, em_10)
                continue
            # Com uma origem só, não dá para conferir a faixa no tempo: fica provisória.
            assert faixas[(em_10, 4, 1)] == {
                "estado": "provisoria", "motivo": "sem_conferencia", "inferior": pytest.approx(np.percentile(erros, inferior)),
                "superior": pytest.approx(np.percentile(erros, superior)), "casos": quantos, "pede": minimo, "como": "propria", "origens": 1,
                "cobertura": None, "origens_de_teste": 0, "casos_de_teste": 0, "meta": meta}, (quantos, em_10)
    assert [(faixas[(em_10, 4, 1)]["inferior"], faixas[(em_10, 4, 1)]["superior"]) for em_10 in (5, 8, 9)] == [
        pytest.approx((-0.1, 0.3)), pytest.approx((-0.22, 0.42)), pytest.approx((-0.26, 0.46))]
    assert simulador._faixas(np.empty((0, simulador.COLUNAS)), "M0") == {}


def test_faixas_retaguarda_com_os_portes_vizinhos_e_com_portes_menores():
    """A retaguarda (seção C.4 e regra A.2.4): faltando casos do próprio porte, a faixa junta os portes vizinhos, um de cada lado;
    ainda faltando, portes menores, um a um; se nada bastar, fica indisponível, com quantos casos há e quantos a faixa pede.
    Casos de 1 ano: 10 no porte de 1 a 3, nenhum no de 4 a 9, 250 no de 10 a 19, 100 no de 20 a 49, 30 no de 50 a 99 e 20 no de
    100 a 299, cada porte com o seu espalhamento de erros (para os limites dizerem que casos entraram)."""
    quantos = {0: 10, 2: 250, 3: 100, 4: 30, 5: 20}
    erros = {porte: np.linspace(-0.05 * (porte + 1), 0.1 * (porte + 1), n) for porte, n in quantos.items()}
    faixas = simulador._faixas(_casos_com_erro([(2020, 1, porte, erro) for porte in quantos for erro in erros[porte]]), "M0")
    esperado = {   # porte: (como a faixa foi montada, os portes que entram nela)
        1: ("vizinhas", (0, 2)), 2: ("propria", (2,)), 3: ("vizinhas", (2, 3, 4)), 4: ("portes_menores", (2, 3, 4, 5)),
        5: ("portes_menores", (2, 3, 4, 5)), 6: ("portes_menores", (2, 3, 4, 5)), 9: ("portes_menores", (2, 3, 4, 5))}
    for porte, (como, usados) in esperado.items():
        faixa, juntos = faixas[(8, porte, 1)], np.concatenate([erros[usado] for usado in usados])
        assert (faixa["como"], faixa["casos"], faixa["pede"]) == (como, len(juntos), 200), porte
        assert (faixa["inferior"], faixa["superior"]) == pytest.approx(tuple(np.percentile(juntos, [10, 90]))), porte
    # Com 1 a 3, não há portes menores a juntar, e o vizinho de cima não tem casos: indisponível, com os 10 casos que há.
    assert faixas[(8, 0, 1)] == {"estado": "indisponivel", "motivo": "poucos_casos", "casos": 10, "pede": 200, "como": "indisponivel"}
    assert {porte for em_10, porte, _ in faixas if em_10 == 8} == set(range(10))
    # Com o mínimo de 80 casos (5 em 10), menos portes precisam da retaguarda; com o de 400 (9 em 10), mais — e os portes de 10 a
    # 49 ficam indisponíveis, com os casos que a retaguarda alcança (o porte de 4 a 9, sem casos próprios, nem aparece).
    assert {porte: (faixas[(5, porte, 1)]["como"], faixas[(5, porte, 1)]["casos"]) for porte in range(10)} == {
        0: ("indisponivel", 10), 1: ("vizinhas", 260), 2: ("propria", 250), 3: ("propria", 100), 4: ("vizinhas", 150),
        **{porte: ("portes_menores", 150) for porte in range(5, 10)}}
    assert {porte: (faixas[(9, porte, 1)]["como"], faixas[(9, porte, 1)]["casos"]) for em_10, porte, _ in faixas if em_10 == 9} == {
        0: ("indisponivel", 10), 2: ("indisponivel", 360), 3: ("indisponivel", 390), **{porte: ("portes_menores", 400) for porte in range(4, 10)}}


@pytest.mark.parametrize("em_10", [5, 8, 9])
def test_faixas_conferencia_no_tempo_conferida_provisoria_e_indisponivel(em_10):
    """A conferência no tempo (seção C.4): em cada origem de teste, a faixa é remontada só com os casos cujo resultado já era
    conhecido e testada nos casos dessa origem. Quatro origens antigas (2017 a 2020) formam o passado, com o erro espalhado de
    −10% a +10% (três delas não bastam para o mínimo; as quatro, sim); as origens de teste (2021 a 2023) têm 200 casos, uns com
    erro zero (dentro da faixa) e os outros com ±50% (fora). A cobertura é comparada em pontos inteiros: 74,5% é 75%."""
    _, _, minimo, meta = FAIXAS[em_10]
    do_passado = int(0.3 * minimo)

    def faixa(dentro, de_teste=200, origens=(2021, 2022, 2023)):
        linhas = [(ano, 1, 4, erro) for ano in (2017, 2018, 2019, 2020) for erro in np.linspace(-0.1, 0.1, do_passado)]
        for ano, parte in zip(origens, np.array_split(np.arange(de_teste), len(origens))):
            linhas += [(ano, 1, 4, 0.0 if k < dentro else 0.5 if k % 2 else -0.5) for k in parte]
        return simulador._faixas(_casos_com_erro(linhas), "M0")[(em_10, 4, 1)]
    for dentro, estado, motivo in ((2 * (meta - 5) - 1, "conferida", None),                 # meio ponto abaixo de (meta − 5): arredonda para ela
                                   (2 * (meta - 5) - 2, "provisoria", "cobertura_abaixo"),   # um ponto abaixo
                                   (2 * (meta - 10) - 1, "provisoria", "cobertura_abaixo"),  # meio ponto abaixo de (meta − 10)
                                   (2 * (meta - 10) - 2, "indisponivel", "cobertura_baixa")):
        lida = faixa(dentro)
        assert (lida["estado"], lida["motivo"], lida["cobertura"], lida["origens_de_teste"], lida["casos_de_teste"], lida["meta"]) == (
            estado, motivo, dentro / 2, 3, 200, meta), dentro
        assert -0.1 < lida["inferior"] < 0 < lida["superior"] < 0.1 and (lida["casos"], lida["origens"], lida["como"]) == (4 * do_passado + 200, 7, "propria")
    # Não deu para conferir: menos de 3 origens de teste, ou menos de 50 casos de teste — mesmo com todos dentro da faixa.
    assert [(lida["estado"], lida["motivo"], lida["cobertura"], lida["origens_de_teste"], lida["casos_de_teste"])
            for lida in (faixa(200, origens=(2021, 2022)), faixa(48, 48), faixa(50, 50))] == [
        ("provisoria", "sem_conferencia", 100.0, 2, 200), ("provisoria", "sem_conferencia", 100.0, 3, 48), ("conferida", None, 100.0, 3, 50)]
    assert (simulador.MINIMO_DE_ORIGENS, simulador.MINIMO_DE_CASOS_DE_TESTE) == (3, 50)


def test_retroprojecao_com_origens_moveis_e_faixas_do_jeito_escolhido():
    b = _base_das_faixas()
    retros = retroprojecoes(b)
    retro, casos = retros["municipios"], _casos_de_referencia(b)
    assert retro.nivel == "municipios" and retro.origens == JUNHOS  # junhos com 3 anos de história e ao menos 1 ano à frente
    # A soma da UF não muda: o crescimento do estado e o da base toda são zero (o M0d e o M0g são o próprio último valor, e
    # erram o mesmo que ele), e a taxa de cada município só acrescenta ruído. Nenhum jeito vale: o escolhido é o último valor,
    # e as faixas são as dele.
    assert _confere_candidatos(retro.escolha, casos) == {"M1": False, "M0d": False, "M0g": False}
    assert (retro.escolha["metodo"], retro.escolha["motivo"]) == ("M0", "nenhum_vale")
    assert [candidato["frente_ao_m0"] for candidato in retro.escolha["candidatos"][1:]] == [1.0, 1.0]
    q = b.quantidade
    for anos in (1, 2, 3, 4):
        origens = [k for k in range(T) if PERIODOS[k].endswith("06") and k >= 6 and k + 2 * anos <= T - 1]
        razoes = np.concatenate([q[:, k + 2 * anos] / q[:, k] - 1 for k in origens])  # o projetado é o último valor
        faixa = retro.faixas[(8, 2, anos)]   # o porte de 10 a 19 médicos
        assert (faixa["casos"], faixa["origens"]) == (60 * len(origens), len(origens)) == (60 * (8 - anos), 8 - anos)
        assert (faixa["inferior"], faixa["superior"]) == pytest.approx(tuple(np.percentile(razoes, [10, 90])))
        assert faixa["inferior"] < 0 < faixa["superior"]
    # As três faixas do porte, com a conferência no tempo, diante da referência. Em 1 ano, a de 8 em 10 tem 3 origens de teste
    # (2021 a 2023, quando o passado já soma 200 casos) e fica conferida; nos outros prazos, ainda não deu para conferir. A de
    # 9 em 10 pede 400 casos: só existe em 1 ano (420 casos), sem conferência.
    estados = {5: ["conferida", "conferida", "provisoria", "provisoria"], 8: ["conferida", "provisoria", "provisoria", "provisoria"],
               9: ["provisoria", "indisponivel", "indisponivel", "indisponivel"]}
    for em_10, por_prazo in estados.items():
        for anos, estado in zip((1, 2, 3, 4), por_prazo):
            faixa, do_prazo = retro.faixas[(em_10, 2, anos)], [caso for caso in casos if caso["prazo"] == anos]
            assert faixa["estado"] == estado, (em_10, anos)
            if estado == "indisponivel":
                assert faixa == {"estado": "indisponivel", "motivo": "poucos_casos", "casos": len(do_prazo), "pede": 400, "como": "indisponivel"}
            else:
                _confere_faixa(faixa, do_prazo, "M0", em_10)
    assert (retro.faixas[(8, 2, 1)]["origens_de_teste"], retro.faixas[(8, 2, 1)]["casos_de_teste"]) == (3, 180)
    assert 75 <= retro.faixas[(8, 2, 1)]["cobertura"] <= 100
    # Só o porte de 10 a 19 tem casos; os outros portes só têm faixa pela retaguarda (o de 1 a 3, nem assim).
    assert {chave for chave in retro.faixas if chave[1] == 2} == {(em_10, 2, anos) for em_10 in (5, 8, 9) for anos in (1, 2, 3, 4)}
    assert all(faixa["como"] in ("vizinhas", "portes_menores") for chave, faixa in retro.faixas.items() if chave[1] != 2)
    assert [(retro.faixas[(8, porte, 1)]["como"], retro.faixas[(8, porte, 1)]["casos"]) for porte in (1, 3, 4)] == [
        ("vizinhas", 420), ("vizinhas", 420), ("portes_menores", 420)]
    assert not any(chave[1] == 0 for chave in retro.faixas)
    linhas = {(linha["metodo"], linha["anos"]): linha for linha in retro.tabela if linha["porte"] == 2}
    assert {metodo for metodo, _ in linhas} == {"M0", "M0d", "M0g", "M1", "M2", "M3"} and {linha["porte"] for linha in retro.tabela} == {2}
    for anos in (1, 2, 3, 4):
        assert [linhas[(metodo, anos)]["frente_ao_m0"] for metodo in ("M0", "M0d", "M0g")] == pytest.approx([1.0, 1.0, 1.0])
        assert linhas[("M0", anos)]["casos"] == 60 * (8 - anos) and linhas[("M0", anos)]["vies"] == pytest.approx(
            float(np.mean(np.concatenate([q[:, k + 2 * anos] - q[:, k] for k in range(T) if PERIODOS[k].endswith("06") and 6 <= k <= T - 1 - 2 * anos]))))
    # A faixa do cenário: a da base, deslocada pela intervenção; a data intermediária usa a do ano inteiro seguinte; depois de 4
    # anos, indisponível. O ponto só é "validado" com a faixa conferida (aqui, a de 1 ano).
    alvo = municipio(b, "111000")
    n0 = float(q[b.indice["111000"], -1])
    cenario = simular(b, alvo, {"metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 5, "em": "202506"}]}, "202906",
                      retros=retros)
    assert cenario["metodo"] == jeito("padrao", "M0", "M0") and aviso(cenario, "PADRAO_E_O_ULTIMO_VALOR") == NENHUM_VALE
    assert cenario["faixa"] == {"estado": "disponivel", "motivo": None, "em_10": 8, "porte": "10 a 19", "ate_anos": 4, "como": "propria",
                                "rotulo": MARGEM_DO_PORTE}
    pontos = {ponto["data"]: ponto for ponto in cenario["trajetoria"]}
    for data, anos, efeito in (("202501", 1, 0), ("202506", 1, 5), ("202601", 2, 5), ("202606", 2, 5), ("202706", 3, 5), ("202806", 4, 5)):
        limites = retro.faixas[(8, 2, anos)]
        assert pontos[data]["faixa"] == {"inferior": pytest.approx(n0 * (1 + limites["inferior"]) + efeito),
                                         "superior": pytest.approx(n0 * (1 + limites["superior"]) + efeito), "anos": anos,
                                         "validada": anos == 1, "estado": "conferida" if anos == 1 else "provisoria", "como": "propria"}, data
    assert pontos["202901"]["faixa"] is None and cenario["final"]["faixa"] is None
    assert avisos(cenario) == ["PADRAO_E_O_ULTIMO_VALOR", "HORIZONTE_EXTRAPOLACAO", "FAIXA_ATE_4_ANOS"]
    assert aviso(cenario, "FAIXA_ATE_4_ANOS") == faixa_ate("4 anos")
    # Só o jeito escolhido pela base tem faixa — aqui, o último valor, pedido como padrão ou pelo nome; os outros métodos, não.
    assert simular(b, alvo, {"metodo": "M0"}, retros=retros)["faixa"]["estado"] == "disponivel"
    for metodo in ("M0d", "M0g", "M1", "M2", "M3"):
        outro = simular(b, alvo, {"metodo": metodo}, retros=retros)
        assert outro["faixa"] == {"estado": "indisponivel", "motivo": SO_DO_ESCOLHIDO.format(ROTULOS["M0"]), "rotulo": None, "em_10": 8}, metodo
        assert all(ponto["faixa"] is None for ponto in outro["trajetoria"]), metodo
    # Num conjunto de municípios, a faixa é uma aproximação, rotulada, com o porte da soma: 29, de 20 a 49 médicos. Esse porte
    # não tem casos próprios nesta base: a faixa vem dos portes vizinhos (os de 10 a 19), ainda sem conferência.
    par = series_brasil.selecao(b, {"conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:111000", "code:111001"]}]})[0]
    do_par = simular(b, par, {"metodo": "padrao"}, retros=retros)
    assert do_par["metodo"] == jeito("padrao", "M0", "M0", soma="soma das projeções dos membros")
    assert do_par["faixa"] == {"estado": "disponivel", "motivo": None, "em_10": 8, "porte": "20 a 49", "ate_anos": 4, "como": "vizinhas",
                               "rotulo": "aproximação: a margem dos municípios com o porte da soma; acompanha a intervenção",
                               "conferencia": "provisoria", "casos": 360, "cobertura_pct": None, "origens_de_teste": 0}
    assert do_par["final"]["faixa"]["inferior"] == pytest.approx(29 * (1 + retro.faixas[(8, 3, 2)]["inferior"]))


def test_o_padrao_no_cenario_com_a_faixa_do_jeito_escolhido_nas_tres_medidas():
    """O cenário do método padrão numa base que escolhe o crescimento do grupo de cima: o jeito, os números dele, o "Entenda" e a
    faixa de 5, 8 ou 9 em cada 10, com a conferência do prazo da data final."""
    b = _base_do_grupo_de_cima()
    retros = retroprojecoes(b)
    retro = retros["municipios"]
    casos = [caso for caso in _casos_de_referencia(b) if caso["porte"] == 5]   # os 60 municípios de 100 a 299 médicos
    assert (retro.escolha["metodo"], retro.escolha["motivo"], len(retro.casos), len(casos)) == ("M0d", "escolhido", 60 * 22, 60 * 22)
    # As faixas do porte, nas três medidas, diante da referência (os limites, os casos e a conferência no tempo).
    estados = {5: ["conferida", "conferida", "provisoria", "provisoria"], 8: ["conferida", "provisoria", "provisoria", "provisoria"],
               9: ["provisoria", "indisponivel", "indisponivel", "indisponivel"]}
    for em_10, por_prazo in estados.items():
        for anos, estado in zip((1, 2, 3, 4), por_prazo):
            faixa, do_prazo = retro.faixas[(em_10, 5, anos)], [caso for caso in casos if caso["prazo"] == anos]
            assert faixa["estado"] == estado, (em_10, anos)
            if estado == "indisponivel":
                assert faixa == {"estado": "indisponivel", "motivo": "poucos_casos", "casos": len(do_prazo), "pede": 400, "como": "indisponivel"}
            else:
                _confere_faixa(faixa, do_prazo, "M0d", em_10)
    # O cenário de um município de Rondônia: o último valor com o crescimento da soma municipal do estado de jun/2021 a jun/2024.
    alvo = municipio(b, "111000")
    n0 = float(b.quantidade[b.indice["111000"], -1])
    do_estado = b.quantidade[list(b.do_estado["11"])].sum(axis=0)
    deriva = (do_estado[-1] / do_estado[PERIODOS.index("202106")]) ** (1 / 3) - 1
    em_pct = ("%+.2f" % (100 * deriva)).replace(".", ",") + "%"
    mais_5 = {"metodo": "padrao", "intervencoes": [{"tipo": "acrescimo", "quantidade": 5, "em": "202506"}]}
    cenario = simular(b, alvo, mais_5, "202906", retros=retros)
    assert cenario["metodo"] == jeito("padrao", "M0d", "M0d")
    assert cenario["parametros"]["deriva_pct"] == pytest.approx(100 * deriva) and cenario["parametros"]["estado_da_deriva"] == "Rondônia"
    assert cenario["entenda"]["jeito"] == {
        "texto": "O cenário parte do último registro usado (jun/2024) e soma o crescimento recente do estado: " + em_pct + " ao ano nos 3 anos "
                 "anteriores. " + ERROU_MENOS,
        "exemplo": "De " + str(int(n0)) + " médicos em jun/2024, a base do cenário vai a " + ("%.1f" % (n0 * (1 + deriva))).replace(".", ",") +
                   " um ano depois, sem contar intervenções."}
    # A faixa de 8 em 10: a da base, em torno da base do cenário e deslocada pela intervenção; a data intermediária usa a do ano
    # inteiro seguinte; cada ponto diz o prazo, a conferência e como a faixa foi montada; depois de 4 anos, não há faixa.
    assert cenario["faixa"] == {"estado": "disponivel", "motivo": None, "em_10": 8, "porte": "100 a 299", "ate_anos": 4, "como": "propria",
                                "rotulo": MARGEM_DO_PORTE}
    pontos = {ponto["data"]: ponto for ponto in cenario["trajetoria"]}
    for data, anos, efeito in (("202501", 1, 0), ("202506", 1, 5), ("202601", 2, 5), ("202606", 2, 5), ("202706", 3, 5), ("202806", 4, 5)):
        limites, tempo = retro.faixas[(8, 5, anos)], (series_brasil.mes_da_competencia(data) - MESES[-1]) / 12
        assert pontos[data]["base"] == pytest.approx(n0 * (1 + deriva) ** tempo) and pontos[data]["intervencao"] == efeito
        assert pontos[data]["faixa"] == {"inferior": pytest.approx(pontos[data]["base"] * (1 + limites["inferior"]) + efeito),
                                         "superior": pytest.approx(pontos[data]["base"] * (1 + limites["superior"]) + efeito), "anos": anos,
                                         "validada": anos == 1, "estado": "conferida" if anos == 1 else "provisoria", "como": "propria"}, data
    assert pontos["202901"]["faixa"] is None and cenario["final"]["faixa"] is None
    assert avisos(cenario) == ["HORIZONTE_EXTRAPOLACAO", "FAIXA_ATE_4_ANOS"] and aviso(cenario, "FAIXA_ATE_4_ANOS") == faixa_ate("4 anos")
    assert cenario["entenda"]["faixa"] == {"texto": REFEITA.format(8), "exemplo": "A faixa vai só até 4 anos depois da origem."}
    # Até 2 anos (o horizonte padrão), a data final tem a faixa de 2 anos: provisória, porque só uma origem pôde ser testada.
    curto = simular(b, alvo, mais_5, retros=retros)
    de_2_anos = retro.faixas[(8, 5, 2)]
    assert curto["faixa"] == {**cenario["faixa"], "conferencia": "provisoria", "casos": 360, "cobertura_pct": de_2_anos["cobertura"], "origens_de_teste": 1}
    assert curto["final"]["faixa"] == pontos["202606"]["faixa"] and curto["final"]["faixa"]["validada"] is False
    assert avisos(curto) == ["HORIZONTE_CAUTELA", "FAIXA_PROVISORIA"] and aviso(curto, "FAIXA_PROVISORIA") == SEM_CONFERENCIA
    assert curto["entenda"]["faixa"] == {
        "texto": REFEITA.format(8) + AINDA_PROVISORIA,
        "exemplo": "Entre %d e %d médicos na data final." % (_inteiro(curto["final"]["faixa"]["inferior"]), _inteiro(curto["final"]["faixa"]["superior"]))}
    # Até 1 ano, a faixa é a conferida: sem aviso de faixa (nem de horizonte), e o ponto é "validado".
    de_1_ano = simular(b, alvo, mais_5, "202506", retros=retros)
    assert avisos(de_1_ano) == [] and de_1_ano["final"]["faixa"]["validada"] is True
    assert (de_1_ano["faixa"]["conferencia"], de_1_ano["faixa"]["casos"], de_1_ano["faixa"]["origens_de_teste"]) == ("conferida", 420, 3)
    assert de_1_ano["faixa"]["cobertura_pct"] == retro.faixas[(8, 5, 1)]["cobertura"] and de_1_ano["entenda"]["faixa"]["texto"] == REFEITA.format(8)
    # A de 5 em 10 é mais estreita e, em 2 anos, já está conferida (pede menos casos, e mais origens puderam ser testadas).
    em_5 = simular(b, alvo, mais_5, em_10=5, retros=retros)
    assert (em_5["faixa"]["em_10"], em_5["faixa"]["conferencia"], em_5["faixa"]["origens_de_teste"]) == (5, "conferida", 3)
    assert avisos(em_5) == ["HORIZONTE_CAUTELA"] and em_5["final"]["faixa"]["validada"] is True
    de_8, de_5 = curto["final"]["faixa"], em_5["final"]["faixa"]
    assert de_8["inferior"] < de_5["inferior"] < em_5["final"]["total"] < de_5["superior"] < de_8["superior"]
    assert em_5["final"]["faixa"]["inferior"] == pytest.approx(em_5["final"]["base"] * (1 + retro.faixas[(5, 5, 2)]["inferior"]) + 5)
    assert em_5["entenda"]["faixa"]["texto"] == REFEITA.format(5)
    # A de 9 em 10 pede 400 casos: nesta base, só vai até 1 ano, e o cenário diz isso.
    em_9 = simular(b, alvo, mais_5, em_10=9, retros=retros)
    assert em_9["faixa"] == {"estado": "disponivel", "motivo": None, "em_10": 9, "porte": "100 a 299", "ate_anos": 1, "como": "propria",
                             "rotulo": MARGEM_DO_PORTE}
    assert [None if ponto["faixa"] is None else (ponto["faixa"]["anos"], ponto["faixa"]["estado"]) for ponto in em_9["trajetoria"]] == [
        (1, "provisoria"), (1, "provisoria"), None, None]
    assert avisos(em_9) == ["HORIZONTE_CAUTELA", "FAIXA_ATE_4_ANOS"] and em_9["final"]["faixa"] is None
    assert aviso(em_9, "FAIXA_ATE_4_ANOS") == faixa_ate("1 ano", 9)
    assert em_9["entenda"]["faixa"] == {"texto": REFEITA.format(9), "exemplo": "A faixa vai só até 1 ano depois da origem."}


def test_o_padrao_no_cenario_so_o_jeito_escolhido_tem_faixa_e_os_casos_sem_ela():
    b = _base_do_grupo_de_cima()
    retros = retroprojecoes(b)
    retro, alvo = retros["municipios"], municipio(b, "111000")
    so_do_m0d = {"estado": "indisponivel", "motivo": SO_DO_ESCOLHIDO.format(ROTULOS["M0d"]), "rotulo": None, "em_10": 8}
    # Só o jeito escolhido pela base tem faixa: pedido pelo nome, o M0d tem a mesma faixa do padrão; os outros métodos, não.
    padrao, pelo_nome = simular(b, alvo, {"metodo": "padrao"}, retros=retros), simular(b, alvo, {"metodo": "M0d"}, retros=retros)
    assert pelo_nome["metodo"] == jeito("M0d", "M0d", "M0d") and pelo_nome["faixa"] == padrao["faixa"] and pelo_nome["final"] == padrao["final"]
    for metodo in ("M0", "M0g", "M1", "M2", "M3"):
        outro = simular(b, alvo, {"metodo": metodo}, retros=retros)
        assert outro["metodo"]["escolhido_pela_base"] == "M0d" and outro["metodo"]["e_o_escolhido"] is False, metodo
        assert outro["faixa"] == so_do_m0d and all(ponto["faixa"] is None for ponto in outro["trajetoria"]), metodo
        assert outro["entenda"]["faixa"] == {"texto": so_do_m0d["motivo"], "exemplo": SEM_FAIXA}, metodo
    assert simular(b, alvo, {"metodo": "M0"}, retros=retros)["entenda"]["jeito"]["texto"] == (
        "O cenário parte do último registro usado (jun/2024) e mantém o valor dele. Este jeito foi escolhido por você: o que a base "
        "escolheu é a persistência com o crescimento recente do estado.")
    # Um município sem médicos: o padrão (o crescimento do estado) mantém o zero, e não há faixa para zero na origem.
    zero = simular(b, municipio(b, "119999"), {"metodo": "padrao"}, retros=retros)
    assert zero["metodo"] == jeito("padrao", "M0d", "M0d") and zero["final"]["total"] == 0 and avisos(zero) == ["ZERO_CONTINUA_ZERO", "HORIZONTE_CAUTELA"]
    assert zero["faixa"] == {"estado": "indisponivel", "motivo": "Com zero médicos na origem, não há faixa.", "rotulo": None, "em_10": 8}
    # O município com quebra de fonte nos 3 anos do crescimento do estado: o padrão volta ao último valor, com os avisos, e fica
    # sem faixa — a faixa da base é a do jeito escolhido, que aqui não pôde ser usado, e o motivo diz isso.
    df = simular(b, municipio(b, "530010"), {"metodo": "padrao"}, retros=retros)
    assert df["metodo"] == jeito("padrao", "M0", "M0d", voltou_ao_m0=True)
    assert avisos(df) == ["JANELA_DEPOIS_DA_QUEBRA", "VOLTA_AO_M0", "HORIZONTE_CAUTELA"] and df["final"]["total"] == 3000
    assert df["faixa"] == {"estado": "indisponivel", "motivo": SO_O_ULTIMO_VALOR.format(ROTULOS["M0d"]), "rotulo": None, "em_10": 8}
    assert df["entenda"] == {"jeito": {"texto": "O cenário parte do último registro usado (jun/2024) e mantém o valor dele. " + NAO_PODE_SER_USADO,
                                       "exemplo": "De 3.000 médicos em jun/2024, a base do cenário vai a 3.000 um ano depois, sem contar intervenções."},
                             "faixa": {"texto": SO_O_ULTIMO_VALOR.format(ROTULOS["M0d"]), "exemplo": SEM_FAIXA}}
    # Num conjunto de municípios, o padrão é a soma das projeções dos membros, e a faixa é uma aproximação, rotulada, com o porte
    # da soma (dois municípios do Acre, que somam de 100 a 299 médicos).
    par = series_brasil.selecao(b, {"conjuntos": [{"id": "c1", "rotulo": "Par", "membros": ["code:121000", "code:121001"]}]})[0]
    assert reguas.porte_de(par.serie[-1]) == 5
    do_par = simular(b, par, {"metodo": "padrao"}, retros=retros)
    assert do_par["metodo"] == jeito("padrao", "M0d", "M0d", soma="soma das projeções dos membros")
    assert do_par["faixa"]["rotulo"] == "aproximação: a margem dos municípios com o porte da soma; acompanha a intervenção"
    assert (do_par["faixa"]["porte"], do_par["faixa"]["como"], do_par["faixa"]["conferencia"]) == ("100 a 299", "propria", "provisoria")
    assert do_par["final"]["faixa"]["inferior"] == pytest.approx(do_par["final"]["total"] * (1 + retro.faixas[(8, 5, 2)]["inferior"]))
    assert do_par["final"]["faixa"]["superior"] == pytest.approx(do_par["final"]["total"] * (1 + retro.faixas[(8, 5, 2)]["superior"]))
    # O estado como unidade segue a retroprojeção dos estados: aqui, uma contagem estadual só, que não muda — nenhum jeito vale, e
    # o padrão é o último valor; a faixa diz quantos casos a base tem.
    assert (retros["estados"].escolha["metodo"], retros["estados"].escolha["motivo"], len(retros["estados"].casos)) == ("M0", "nenhum_vale", 22)
    uf = simular(b, series_brasil.selecao(b, {"estados_unidade": ["53"]})[0], {"metodo": "padrao"}, retros=retros)
    assert uf["metodo"] == jeito("padrao", "M0", "M0") and avisos(uf) == ["PADRAO_E_O_ULTIMO_VALOR", "HORIZONTE_CAUTELA"]
    assert uf["faixa"] == {"estado": "indisponivel", "motivo": poucos_casos(7), "rotulo": None, "em_10": 8}


def _faixa_feita(estado, motivo=None, como="propria", cobertura=None, origens_de_teste=0):
    """Uma faixa como a retroprojeção a guarda, com limites de −10% e +20%."""
    return {"estado": estado, "motivo": motivo, "inferior": -0.1, "superior": 0.2, "casos": 300, "pede": 200, "como": como, "origens": 5,
            "cobertura": cobertura, "origens_de_teste": origens_de_teste, "casos_de_teste": 180 if origens_de_teste else 0, "meta": 80}


def test_faixa_do_cenario_a_conferencia_o_prazo_a_retaguarda_e_os_motivos():
    """O que o cenário diz da faixa, com as faixas da retroprojeção trocadas à mão (limites de −10% e +20% no porte do município):
    a conferência do prazo da data final, os avisos, o maior prazo com faixa e, sem faixa, o motivo."""
    b = _base_do_grupo_de_cima()
    cal, retros, alvo = detector.calibrar(b, guardar=False), retroprojecoes(b), municipio(b, "111000")
    inicio, fim, _ = simulador._janela(b, None)
    pedido = simulador._cenarios([{"metodo": "padrao"}], b, {alvo.id})[0]

    def com(faixas, horizonte="202606"):
        trocada = replace(retros["municipios"], faixas={(8, 5, anos): faixa for anos, faixa in faixas.items()})
        return simulador._simular(b, cal, {"municipios": trocada, "estados": None}, alvo, pedido, inicio, fim,
                                  simulador._competencia_futura(horizonte, "Data final"))
    conferida = _faixa_feita("conferida", cobertura=78.0, origens_de_teste=3)
    sem_casos = {"estado": "indisponivel", "motivo": "poucos_casos", "casos": 150, "pede": 200, "como": "indisponivel"}
    # Conferida nos dois prazos: sem aviso de faixa, e o ponto é "validado".
    cenario = com({1: conferida, 2: _faixa_feita("conferida", cobertura=76.2, origens_de_teste=3)})
    total = cenario["final"]["total"]
    assert cenario["final"]["faixa"] == {"inferior": pytest.approx(0.9 * total), "superior": pytest.approx(1.2 * total), "anos": 2, "validada": True,
                                         "estado": "conferida", "como": "propria"}
    assert cenario["faixa"] == {"estado": "disponivel", "motivo": None, "em_10": 8, "porte": "100 a 299", "ate_anos": 2, "como": "propria",
                                "rotulo": MARGEM_DO_PORTE, "conferencia": "conferida", "casos": 300, "cobertura_pct": 76.2, "origens_de_teste": 3}
    assert avisos(cenario) == ["HORIZONTE_CAUTELA"]
    assert cenario["entenda"]["faixa"] == {"texto": REFEITA.format(8),
                                           "exemplo": "Entre %d e %d médicos na data final." % (_inteiro(0.9 * total), _inteiro(1.2 * total))}
    # Provisória porque a conferência ficou um pouco abaixo do esperado: o aviso diz a cobertura e a meta.
    abaixo = com({1: conferida, 2: _faixa_feita("provisoria", "cobertura_abaixo", cobertura=72.4, origens_de_teste=4)})
    assert [ponto["faixa"]["validada"] for ponto in abaixo["trajetoria"]] == [True, True, False, False]   # 2025 (1 ano) e 2026 (2 anos)
    assert (abaixo["faixa"]["conferencia"], abaixo["final"]["faixa"]["estado"]) == ("provisoria", "provisoria")
    assert avisos(abaixo) == ["HORIZONTE_CAUTELA", "FAIXA_PROVISORIA"] and aviso(abaixo, "FAIXA_PROVISORIA") == (
        "Faixa provisória: a conferência com o que veio depois ficou um pouco abaixo do esperado (72%, para uma meta de 80%).")
    assert abaixo["entenda"]["faixa"]["texto"] == REFEITA.format(8) + AINDA_PROVISORIA
    # Provisória porque ainda não deu para conferir.
    sem_conferencia = com({1: conferida, 2: _faixa_feita("provisoria", "sem_conferencia")})
    assert aviso(sem_conferencia, "FAIXA_PROVISORIA") == SEM_CONFERENCIA
    assert (sem_conferencia["faixa"]["cobertura_pct"], sem_conferencia["faixa"]["origens_de_teste"]) == (None, 0)
    # A retaguarda: a faixa montada com os portes vizinhos, ou com portes menores (mais larga, com o aviso), diz com quem. O resumo
    # da faixa (como ela foi montada e o rótulo) descreve o prazo da data final, quando ela tem faixa: aqui, em 2 anos, a de portes
    # menores; em 1 ano, a dos vizinhos. Com a data final além da faixa, descreve o primeiro prazo.
    com_vizinhas = _faixa_feita("conferida", como="vizinhas", cobertura=78.0, origens_de_teste=3)
    com_menores = _faixa_feita("provisoria", "sem_conferencia", como="portes_menores")
    dos_vizinhos = "a margem observada no passado da base, em municípios do mesmo porte e dos portes vizinhos; acompanha a intervenção"
    dos_menores = ("a margem observada no passado da base, em municípios do mesmo porte e de portes menores (a faixa fica mais larga, e por isso "
                   "mais cautelosa); acompanha a intervenção")
    em_2_anos = com({1: com_vizinhas, 2: com_menores})
    assert [ponto["faixa"]["como"] for ponto in em_2_anos["trajetoria"]] == ["vizinhas", "vizinhas", "portes_menores", "portes_menores"]
    assert (em_2_anos["faixa"]["como"], em_2_anos["faixa"]["rotulo"], em_2_anos["faixa"]["conferencia"]) == ("portes_menores", dos_menores, "provisoria")
    assert avisos(em_2_anos) == ["HORIZONTE_CAUTELA", "FAIXA_PROVISORIA", "FAIXA_COM_PORTES_MENORES"]
    assert aviso(em_2_anos, "FAIXA_COM_PORTES_MENORES") == ("Faltaram casos do mesmo porte: a faixa junta portes menores, que variam mais. Ela "
                                                           "fica mais larga, e por isso mais cautelosa.")
    em_1_ano = com({1: com_vizinhas, 2: com_menores}, "202506")
    assert (em_1_ano["faixa"]["como"], em_1_ano["faixa"]["rotulo"], em_1_ano["faixa"]["conferencia"]) == ("vizinhas", dos_vizinhos, "conferida")
    assert avisos(em_1_ano) == []
    alem = com({1: com_vizinhas, 2: com_menores}, "202706")
    assert (alem["faixa"]["como"], alem["faixa"]["rotulo"], alem["final"]["faixa"]) == ("vizinhas", dos_vizinhos, None) and "conferencia" not in alem["faixa"]
    assert avisos(alem) == ["HORIZONTE_CAUTELA", "FAIXA_ATE_4_ANOS"] and aviso(alem, "FAIXA_ATE_4_ANOS") == faixa_ate("2 anos")
    # O prazo: a faixa do cenário vai do 1.º ano até o maior prazo seguido que a base sustenta (aqui, 3 anos); depois dele, o ponto
    # fica sem faixa, e o aviso diz até onde ela vai.
    provisoria = _faixa_feita("provisoria", "sem_conferencia")
    baixa = _faixa_feita("indisponivel", "cobertura_baixa", cobertura=61.6, origens_de_teste=3)
    ate_3 = com({1: conferida, 2: conferida, 3: provisoria, 4: sem_casos}, "202806")
    assert ate_3["faixa"]["ate_anos"] == 3 and ate_3["final"]["faixa"] is None and "conferencia" not in ate_3["faixa"]
    assert [None if ponto["faixa"] is None else ponto["faixa"]["anos"] for ponto in ate_3["trajetoria"]] == [1, 1, 2, 2, 3, 3, None, None]
    assert avisos(ate_3) == ["HORIZONTE_EXTRAPOLACAO", "FAIXA_ATE_4_ANOS"] and aviso(ate_3, "FAIXA_ATE_4_ANOS") == faixa_ate("3 anos")
    assert ate_3["entenda"]["faixa"] == {"texto": REFEITA.format(8), "exemplo": "A faixa vai só até 3 anos depois da origem."}
    # A faixa é seguida, sem "buracos": um prazo sem faixa (por falta de casos ou pela conferência) encerra-a ali, mesmo que um
    # prazo maior a tenha. Com faixa em 1 e 2 anos, sem ela em 3 e com ela em 4, a do cenário vai só até 2 anos.
    for do_3_ano in (sem_casos, baixa):
        ate_2 = com({1: conferida, 2: conferida, 3: do_3_ano, 4: provisoria}, "202806")
        assert ate_2["faixa"]["ate_anos"] == 2 and ate_2["final"]["faixa"] is None and "conferencia" not in ate_2["faixa"]
        assert [None if ponto["faixa"] is None else ponto["faixa"]["anos"] for ponto in ate_2["trajetoria"]] == [1, 1, 2, 2, None, None, None, None]
        assert avisos(ate_2) == ["HORIZONTE_EXTRAPOLACAO", "FAIXA_ATE_4_ANOS"] and aviso(ate_2, "FAIXA_ATE_4_ANOS") == faixa_ate("2 anos")
        assert ate_2["entenda"]["faixa"] == {"texto": REFEITA.format(8), "exemplo": "A faixa vai só até 2 anos depois da origem."}
        dentro = com({1: conferida, 2: conferida, 3: do_3_ano, 4: provisoria})   # até 2 anos, a data final tem a faixa, sem aviso de prazo
        assert (dentro["final"]["faixa"]["anos"], dentro["faixa"]["conferencia"], avisos(dentro)) == (2, "conferida", ["HORIZONTE_CAUTELA"])
    # Sem faixa no 1.º ano, o cenário não tem faixa, mesmo que os prazos seguintes a tenham, e diz por quê, com o motivo do 1.º
    # ano: a conferência não a sustentou (com a cobertura e o prazo) ou faltam casos (com quantos há). Sem o 1.º ano na
    # retroprojeção, vale o motivo do primeiro prazo que há; sem nenhum, a base não tem retroprojeções deste porte.
    nao_sustenta = "Conferida com o que veio depois, a faixa de 8 em cada 10 cobriu 62% dos casos em 1 ano, para uma meta de 80%: a base não a sustenta."
    for faixas, motivo in (
            ({1: baixa, 2: conferida, 3: provisoria, 4: provisoria}, nao_sustenta),
            ({1: sem_casos, 2: conferida, 3: provisoria, 4: provisoria}, poucos_casos(150)),
            ({1: baixa, 2: _faixa_feita("indisponivel", "cobertura_baixa", cobertura=55.0, origens_de_teste=3)}, nao_sustenta),
            ({1: sem_casos, 2: {**sem_casos, "casos": 120}}, poucos_casos(150)),
            ({2: {**sem_casos, "casos": 120}}, poucos_casos(120, prazo="2 anos")),
            ({}, "A base não tem retroprojeções de territórios de 100 a 299 médicos.")):
        for horizonte, do_horizonte in (("202606", "HORIZONTE_CAUTELA"), ("202806", "HORIZONTE_EXTRAPOLACAO")):
            sem_faixa = com(faixas, horizonte)
            assert sem_faixa["faixa"] == {"estado": "indisponivel", "motivo": motivo, "rotulo": None, "em_10": 8}
            assert sem_faixa["final"]["faixa"] is None and all(ponto["faixa"] is None for ponto in sem_faixa["trajetoria"])
            assert avisos(sem_faixa) == [do_horizonte] and sem_faixa["entenda"]["faixa"] == {"texto": motivo, "exemplo": SEM_FAIXA}


# --------------------------------------------------------------------------------------------- compute: a resposta
def test_compute_a_opcao_faixa_e_a_retroprojecao_por_nivel():
    """A resposta de `compute` numa base dada (o caminho da planilha enviada): a opção `faixa` (5, 8 ou 9 em cada 10; sem ela, 8),
    as faixas da retroprojeção em %, com a conferência, e a escolha de cada nível, com os candidatos e a frase."""
    b = _base_do_grupo_de_cima()
    opcoes = {"base": {"municipios": {"ids": ["code:111000", "code:119999"]}}, "estados_unidade": ["53"], "horizonte": "202606"}
    casos = [caso for caso in _casos_de_referencia(b) if caso["porte"] == 5]
    nomes = {"conferida": "conferida com o que veio depois", "provisoria": "provisória"}
    for em_10 in (8, 5, 9):
        inferior, superior, minimo, meta = FAIXAS[em_10]
        body = simulador.compute(None, {**opcoes, **({} if em_10 == 8 else {"faixa": em_10})}, base=b)
        json.dumps(body, allow_nan=False)
        assert body["versao"] == simulador.VERSION and body["fonte"]["versao"] == b.versao
        assert body["faixa"] == {"em_10": em_10, "opcoes": [5, 8, 9], "padrao": 8}
        assert body["limitacoes"] == ["CENARIO_HIPOTETICO", "PADRAO_ESCOLHIDO_PELA_BASE", "FAIXA_SO_DO_METODO_PADRAO"]
        retro = body["retroprojecao"]
        assert set(retro) == {"origens", "faixas", "tabela", "em_10", "escolha", "niveis"} and retro["em_10"] == em_10
        assert list(retro["niveis"]) == ["municipios", "estados"] and retro["origens"] == list(JUNHOS)
        dos_municipios, dos_estados = retro["niveis"]["municipios"], retro["niveis"]["estados"]
        assert (retro["escolha"], retro["faixas"], retro["tabela"]) == (dos_municipios["escolha"], dos_municipios["faixas"], dos_municipios["tabela"])
        # As faixas do porte dos municípios desta base, na medida pedida: os limites em %, os casos e a conferência no tempo.
        assert all(faixa["em_10"] == em_10 and faixa["pede"] == minimo for faixa in retro["faixas"] + dos_estados["faixas"])
        do_porte = [faixa for faixa in retro["faixas"] if faixa["porte"] == "100 a 299"]
        assert [faixa["anos"] for faixa in do_porte] == [1, 2, 3, 4]
        for faixa in do_porte:
            do_prazo = [caso for caso in casos if caso["prazo"] == faixa["anos"]]
            comum = {"porte": "100 a 299", "anos": faixa["anos"], "em_10": em_10, "casos": len(do_prazo), "pede": minimo}
            if len(do_prazo) < minimo:   # só na de 9 em 10, de 2 a 4 anos
                assert faixa == {**comum, "inferior_pct": None, "superior_pct": None, "origens": None, "cobertura_pct": None, "estado": "indisponivel",
                                 "como": "indisponivel", "origens_de_teste": None, "casos_de_teste": None, "rotulo": "indisponível (sem casos bastantes)"}
                continue
            limites = np.percentile(_razoes(do_prazo, "M0d"), [inferior, superior])
            origens, testados, dentro = _conferencia_de_referencia(do_prazo, "M0d", em_10)
            estado = _estado_da_conferencia(origens, testados, dentro, meta)[0]
            assert faixa == {**comum, "inferior_pct": pytest.approx(100 * limites[0]), "superior_pct": pytest.approx(100 * limites[1]),
                             "origens": 8 - faixa["anos"], "cobertura_pct": pytest.approx(100 * dentro / testados) if testados else None,
                             "estado": estado, "como": "propria", "origens_de_teste": origens, "casos_de_teste": testados, "rotulo": nomes[estado]}
        if em_10 == 8:   # os portes sem casos próprios só têm faixa pela retaguarda, e o rótulo diz como
            assert {(faixa["porte"], faixa["rotulo"]) for faixa in retro["faixas"] if faixa["porte"] != "100 a 299"} == {
                ("50 a 99", "provisória (com os portes vizinhos)"), ("300 a 999", "provisória (com os portes vizinhos)"),
                ("1.000 a 2.999", "provisória (com portes menores)"), ("3.000 a 9.999", "provisória (com portes menores)"),
                ("10.000 ou mais", "provisória (com portes menores)")}
        # A escolha de cada nível: o jeito, o motivo, os candidatos (com o nome de cada um) e a frase.
        escolha = retro["escolha"]
        assert (escolha["metodo"], escolha["rotulo"], escolha["motivo"], escolha["origens"], escolha["combinacoes"], escolha["excecoes"]) == (
            "M0d", ROTULOS["M0d"], "escolhido", 7, 22, [])
        assert [(candidato["metodo"], candidato["rotulo"], candidato["vale"]) for candidato in escolha["candidatos"]] == [
            ("M1", ROTULOS["M1"], True), ("M0d", ROTULOS["M0d"], True), ("M0g", ROTULOS["M0g"], True)]
        do_m0d = _frente_ao_ultimo_valor(casos, "M0d")
        assert escolha["candidatos"][1]["frente_ao_m0"] == pytest.approx(do_m0d) and escolha["candidatos"][1]["menos_erro_em"] == 22
        assert round(100 * (1 - do_m0d)) == 45 and escolha["texto"] == (
            "Para os municípios, a base escolheu a persistência com o crescimento recente do estado: na retroprojeção, ela errou 45% menos que "
            "manter o último valor, e menos em 22 de 22 combinações de origem e prazo.")
        assert (dos_estados["escolha"]["metodo"], dos_estados["escolha"]["motivo"], dos_estados["escolha"]["rotulo"]) == ("M0", "nenhum_vale", ROTULOS["M0"])
        assert dos_estados["escolha"]["texto"] == ("Para os estados como unidade: nesta base, nenhum jeito de projetar errou menos que manter o "
                                                   "último valor, quando conferido com o passado: o cenário mantém o último valor.")
        assert [(faixa["porte"], faixa["anos"], faixa["estado"], faixa["casos"], faixa["inferior_pct"]) for faixa in dos_estados["faixas"]] == [
            ("1.000 a 2.999", anos, "indisponivel", 8 - anos, None) for anos in (1, 2, 3, 4)]
        assert {linha["metodo"] for linha in retro["tabela"]} == {"M0", "M0d", "M0g", "M1", "M2", "M3"}
        assert {linha["porte"] for linha in retro["tabela"]} == {"100 a 299"}
        assert {linha["metodo"] for linha in dos_estados["tabela"]} == {"M0", "M0g", "M1", "M2", "M3"}   # sem o M0d: o grupo de cima deles é a base toda
        # Os cenários e as notas seguem a medida pedida.
        do_municipio, em_zero, do_estado = (item["cenarios"][0] for item in body["territorios"])
        assert do_municipio["faixa"]["em_10"] == em_zero["faixa"]["em_10"] == do_estado["faixa"]["em_10"] == em_10
        assert do_municipio["metodo"] == jeito("padrao", "M0d", "M0d") and do_municipio["faixa"]["estado"] == "disponivel"
        assert (do_municipio["final"]["faixa"] or {}).get("estado") == {8: "provisoria", 5: "conferida", 9: None}[em_10]
        assert do_estado["faixa"]["motivo"] == poucos_casos(7, em_10)
        assert sum(nota.startswith("A faixa de %d em cada 10 só existe para o jeito e a janela escolhidos" % em_10) for nota in body["notas"]) == 1
    for invalida in (7, 0, "8", True, 8.5, None):
        with pytest.raises(ValueError, match="Faixa inválida: escolha 5, 8 ou 9 em cada 10."):
            simulador.compute(None, {**opcoes, "faixa": invalida}, base=b)
    # A medida é um número inteiro: 8.0 (como pode chegar de um JSON) vira 8, na resposta e nos textos ("8 em cada 10").
    com_decimal = simulador.compute(None, {**opcoes, "faixa": 8.0}, base=b)
    assert com_decimal["faixa"] == {"em_10": 8, "opcoes": [5, 8, 9], "padrao": 8} and type(com_decimal["faixa"]["em_10"]) is int
    assert type(com_decimal["retroprojecao"]["em_10"]) is int and type(com_decimal["territorios"][0]["cenarios"][0]["faixa"]["em_10"]) is int
    assert sum(nota.startswith("A faixa de 8 em cada 10 só existe para o jeito e a janela escolhidos") for nota in com_decimal["notas"]) == 1


def test_compute_devolve_a_marca_de_base_anual_ao_que_era():
    """A marca de base com datas só de ano (`simulador._ANUAL`) vale só durante o cálculo de `compute`: no fim — com resposta
    ou com recusa —, volta ao que era. Antes, um `compute` chamado direto com uma base anual deixava-a ligada, e os cenários de
    datas com mês montados depois, no mesmo processo, eram recusados ("use o ano"). Ela vale para toda base em que as datas só
    têm o ano, com ou sem anos faltando."""
    anos = tuple(str(ano) + "00" for ano in range(2014, 2024))
    anual = base({"110001": [10 + k for k in range(10)], "110002": [90] * 10}, periodos=anos)
    semestral = base({"110001": [10] * T, "110002": [90] * T})
    assert anual.ancora == "00" and simulador._ANUAL.get() is False
    pedido = {"base": {"municipios": {"ids": ["code:110001"]}}, "horizonte": "202500"}
    # Durante o cálculo, as datas são anos: a janela padrão são os 3 anos até o último registro (4 registros), e o cenário vai de
    # ano em ano. Depois dele, a marca está desligada.
    body = simulador.compute(None, pedido, base=anual)
    cenario = body["territorios"][0]["cenarios"][0]
    assert body["janela"] == {"inicio": "202000", "fim": "202300", "registros": 4, "anos": 3.0, "padrao": True}
    assert [ponto["data"] for ponto in cenario["trajetoria"]] == ["202400", "202500"] and cenario["texto"].endswith("em 2025. Base: registros até 2023.")
    assert simulador._ANUAL.get() is False
    # Também quando o pedido é recusado no meio do cálculo: a data com mês e o intervalo que não é de 12 em 12 meses.
    de_6_em_6 = [{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 1, "em": "202400", "ate": "202500", "a_cada_meses": 6}]}]
    for recusado, motivo in (({**pedido, "horizonte": "202506"}, "Data final inválida: use o ano"),
                             ({**pedido, "cenarios": de_6_em_6}, "o intervalo entre os eventos é de 12 meses ou um múltiplo de 12")):
        with pytest.raises(ValueError, match=motivo):
            simulador.compute(None, recusado, base=anual)
        assert simulador._ANUAL.get() is False
    # Um cenário de datas com mês, montado direto logo depois, funciona.
    depois = simular(semestral, municipio(semestral, "110001"), {"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 2, "em": "202501"}]})
    assert (depois["estado"], depois["final"]["data"], depois["final"]["total"]) == ("calculado", "202606", 12.0)
    # A marca vem das datas da base (todas só com o ano, "AAAA00"), e não da série anual: uma base de anos com anos faltando (um
    # registro a cada 5 anos, sem série anual) também pede e mostra as datas em anos.
    de_5_em_5 = ("200400", "200900", "201400", "201900", "202400")
    espacada = base({"110001": [10, 12, 15, 20, 30], "110002": [90] * 5}, periodos=de_5_em_5)
    em_anos = {"base": {"municipios": {"ids": ["code:110001"]}}, "horizonte": "202600", "cenarios": [{"metodo": "M1"}]}
    body = simulador.compute(None, em_anos, base=espacada)
    cenario = body["territorios"][0]["cenarios"][0]
    assert espacada.ancora is None and body["janela"] == {"inicio": "201900", "fim": "202400", "registros": 2, "anos": 5.0, "padrao": True}
    assert [ponto["data"] for ponto in cenario["trajetoria"]] == ["202500", "202600"] and cenario["final"]["total"] == pytest.approx(30 * 1.5 ** 0.4)
    assert cenario["texto"].endswith("janela de 2019 a 2024; taxa de +8,45% ao ano; sem intervenção, M110001 teria 35 médicos em 2026. Base: registros até 2024.")
    with pytest.raises(ValueError, match="Data final inválida: use o ano"):
        simulador.compute(None, {**em_anos, "horizonte": "202606"}, base=espacada)
    assert simulador._ANUAL.get() is False
    # `compute` devolve a marca ao que era antes dele — também quando ela já estava ligada (e a base do pedido não é anual).
    simulador._ANUAL.set(True)
    assert simulador.compute(None, {"base": {"municipios": {"ids": ["code:110001"]}}}, base=semestral)["horizonte"]["data"] == "202606"
    assert simulador._ANUAL.get() is True


# --------------------------------------------------------------------------------------------- rota
UNIDADES = {"130260": ("MANAUS", "AM", [30 + k for k in range(T)]), "130420": ("TEFE", "AM", [3] * 10 + [0] * 12),
            "130340": ("PARINTINS", "AM", [20] * 12 + [12] * 10), "150140": ("BELEM", "PA", [50] * T)}
POPULACOES = {"130260": 2000, "130420": 1000, "130340": 1000, "150140": 4000}
ESTADOS_PARADOS = {"AM": [40] * T, "PA": [45] * T}
# O Amazonas com um médico a mais por registro (sempre abaixo da soma municipal: sem quebra de fonte) e o Pará parado.
ESTADOS_QUE_CRESCEM = {"AM": [30 + k for k in range(T)], "PA": [45] * T}


@pytest.fixture
def catalogo(tmp_path, monkeypatch, request):
    """Catálogo sintético (4 municípios, 22 competências) instalado como versão governada. A contagem nacional cresce 10 médicos
    por registro (de 900 a 1.110), e as populações são diferentes (POPULACOES), para a comparação por taxa. As contagens estaduais
    não mudam (ESTADOS_PARADOS), salvo quando o teste pede outras (`indirect`)."""
    estados = getattr(request, "param", ESTADOS_PARADOS)
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
    write_state_source(raiz, {(uf, periodo): contagens[k] for k, periodo in enumerate(PERIODOS) for uf, contagens in estados.items()})
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
    mais_4 = [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]
    body = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [
        {"id": "c1", "nome": "Com 4 médicos", "metodo": "padrao", "intervencoes": mais_4},
        {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"},
        {"id": "d", "nome": "Com o crescimento do estado", "metodo": "M0d", "intervencoes": mais_4}]}))
    assert body["versao"] == simulador.VERSION == "SIMULADOR-CENARIOS/V3/1"
    # A fonte, como no Detector: os nomes da base, de onde ela vem e o que ela tem.
    fonte = body["fonte"]
    assert set(fonte) == {"base", "categoria", "versao", "primeira", "ultima", "competencias", "rotulos", "origem", "ancora", "formas", "tem", "unidades"}
    assert (fonte["base"], fonte["categoria"], fonte["origem"], fonte["ancora"], fonte["competencias"]) == ("Brasil", "MEDICINA", "brasil", "06", 22)
    assert (fonte["primeira"], fonte["ultima"], body["ultimo_registro"]) == ("201401", "202406", "202406")
    assert fonte["rotulos"]["profissionais"] == "médicos" and fonte["tem"] == {"populacao": True, "coordenadas": True, "grupo": True, "serie_anual": True}
    assert body["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7, "anos": 3.0, "padrao": True}
    assert body["horizonte"] == {"data": "202606", "anos_desde_o_ultimo_registro": 2.0}
    assert body["competencias"] == list(PERIODOS) and body["limitacoes"] == ["CENARIO_HIPOTETICO", "PADRAO_ESCOLHIDO_PELA_BASE", "FAIXA_SO_DO_METODO_PADRAO"]
    assert body["faixa"] == {"em_10": 8, "opcoes": [5, 8, 9], "padrao": 8}
    assert [metodo["chave"] for metodo in body["metodos"]] == ["M0", "M0d", "M0g", "M1", "M2", "M3", "manual"]
    assert body["metodos"][2] == {"chave": "M0g", "rotulo": ROTULOS["M0g"]}
    # A retroprojeção do catálogo, por nível, com a escolha de cada um. Nos municípios, a referência refeita aqui (são poucos
    # casos: todos os portes ficam juntos) dá a taxa composta do próprio município; o crescimento do estado e o da base toda
    # erram mais que o último valor.
    retro = body["retroprojecao"]
    assert set(retro) == {"origens", "faixas", "tabela", "em_10", "escolha", "niveis"} and set(retro["niveis"]) == {"municipios", "estados"}
    assert retro["em_10"] == 8 and retro["origens"] == list(JUNHOS)
    dos_municipios = retro["niveis"]["municipios"]
    assert (retro["escolha"], retro["faixas"], retro["tabela"], retro["origens"]) == (
        dos_municipios["escolha"], dos_municipios["faixas"], dos_municipios["tabela"], dos_municipios["origens"])
    escolhido, candidatos = _escolha_de_referencia(_casos_de_referencia(series_brasil.base_de(main._brazil_sources(""))), juntos=True)
    escolha = retro["escolha"]
    assert escolhido == "M1" and (escolha["metodo"], escolha["rotulo"], escolha["motivo"], escolha["origens"], escolha["combinacoes"], escolha["excecoes"]) == (
        "M1", ROTULOS["M1"], "escolhido", 7, 22, [])
    assert escolha["candidatos"] == [{**candidato, "frente_ao_m0": pytest.approx(candidato["frente_ao_m0"]), "rotulo": ROTULOS[candidato["metodo"]]}
                                     for candidato in candidatos]
    assert [(candidato["metodo"], candidato["casos"], candidato["vale"]) for candidato in candidatos] == [
        ("M1", 70, True), ("M0d", 70, False), ("M0g", 70, False)]
    assert escolha["texto"] == ("Para os municípios, a base escolheu a taxa composta da janela: na retroprojeção, ela errou 29% menos que manter o "
                                "último valor, e menos em 19 de 22 combinações de origem e prazo.")
    # Nos estados, as contagens do catálogo não mudam: o último valor não erra, nenhum jeito vale, e o padrão é o último valor.
    dos_estados = retro["niveis"]["estados"]
    assert (dos_estados["escolha"]["metodo"], dos_estados["escolha"]["motivo"]) == ("M0", "nenhum_vale")
    assert [(candidato["metodo"], candidato["frente_ao_m0"], candidato["vale"]) for candidato in dos_estados["escolha"]["candidatos"]] == [
        ("M1", None, False), ("M0g", None, False)]
    assert dos_estados["escolha"]["texto"] == "Para os estados como unidade: n" + NENHUM_VALE[1:]
    # As faixas da resposta: neste catálogo, sem casos bastantes em nenhum porte — com quantos casos há e quantos a faixa pede.
    assert all(faixa["estado"] == "indisponivel" and faixa["inferior_pct"] is None and faixa["superior_pct"] is None and faixa["pede"] == 200
               and faixa["em_10"] == 8 and faixa["rotulo"] == "indisponível (sem casos bastantes)" for faixa in retro["faixas"] + dos_estados["faixas"])
    assert [(faixa["porte"], faixa["anos"], faixa["casos"]) for faixa in dos_estados["faixas"]] == [
        ("20 a 49", 1, 14), ("20 a 49", 2, 12), ("20 a 49", 3, 10), ("20 a 49", 4, 8)]
    assert {linha["metodo"] for linha in retro["tabela"]} == {"M0", "M0d", "M0g", "M1", "M2", "M3"}
    assert {linha["metodo"] for linha in dos_estados["tabela"]} == {"M0", "M0g", "M1", "M2", "M3"}
    territorios = {item["id"]: item for item in body["territorios"]}
    assert list(territorios) == ["code:130260", "code:130420", "uf:15", "g1"]
    manaus = territorios["code:130260"]
    assert (manaus["rotulo"], manaus["tipo"], manaus["uf"], len(manaus["observado"])) == ("MANAUS (AM)", "municipio", "AM", 22)
    assert manaus["observado"][-1] == {"competencia": "202406", "valor": 51.0, "estado": "observado"}
    # O padrão é o jeito escolhido para os municípios: a taxa composta de Manaus, que passa de 45 (jun/2021) a 51 (jun/2024).
    taxa = (51 / 45) ** (1 / 3) - 1
    com, referencia, do_estado = manaus["cenarios"]
    assert (com["id"], com["nome"], com["estado"]) == ("c1", "Com 4 médicos", "calculado") and com["metodo"] == jeito("padrao", "M1", "M1")
    assert com["parametros"]["taxa_pct"] == pytest.approx(100 * taxa) and com["parametros"]["janela"] == {"inicio": "202106", "fim": "202406", "registros": 7}
    assert com["final"] == {"data": "202606", "base": pytest.approx(51 * (1 + taxa) ** 2), "intervencao": 4.0,
                            "total": pytest.approx(51 * (1 + taxa) ** 2 + 4), "faixa": None}
    assert com["texto"].startswith(FIXO) and com["texto"].endswith("MANAUS (AM) teria 59 médicos em jun/2026. Base: registros até jun/2024.")
    assert "acréscimo de 4 médicos em cada território do cenário, em jan/2025, com permanência total (hipótese)" in com["texto"]
    assert any("Cada intervenção vale para cada território do cenário" in nota for nota in body["notas"])
    # O catálogo de teste não tem retroprojeções bastantes para a faixa: o cenário diz quantos casos há.
    assert com["faixa"] == {"estado": "indisponivel", "motivo": poucos_casos(22), "rotulo": None, "em_10": 8}
    assert com["entenda"]["faixa"] == {"texto": poucos_casos(22), "exemplo": SEM_FAIXA} and com["entenda"]["jeito"]["texto"].endswith(ERROU_MENOS)
    assert (referencia["id"], referencia["metodo"]["usado"], referencia["final"]["total"]) == ("m0", "M0", 51.0)
    # O M0d, pedido pelo nome, usa a deriva do Amazonas: a soma municipal passa de 57 (jun/2021) para 63 (jun/2024).
    deriva = (63 / 57) ** (1 / 3) - 1
    assert do_estado["metodo"] == jeito("M0d", "M0d", "M1")
    assert do_estado["parametros"]["deriva_pct"] == pytest.approx(100 * deriva) and do_estado["parametros"]["estado_da_deriva"] == "Amazonas"
    assert do_estado["final"]["total"] == pytest.approx(51 * (1 + deriva) ** 2 + 4) and "crescimento do Amazonas de +3,39% ao ano" in do_estado["texto"]
    assert manaus["historico"]["taxa_composta_pct"] == pytest.approx(100 * ((51 / 45) ** (1 / 3) - 1))
    assert [taxa_de_junho["ate"] for taxa_de_junho in manaus["historico"]["taxas_de_junho"]] == ["202206", "202306", "202406"]
    assert manaus["historico"]["media_aritmetica_pct"] == pytest.approx(100 * np.mean([47 / 45 - 1, 49 / 47 - 1, 51 / 49 - 1]))
    # Tefé está em zero: continua em zero sem intervenção; com os 4 médicos do cenário, tem 4. A taxa composta (o padrão deste
    # catálogo) não se aplica a quem está em zero: o padrão de Tefé volta ao último valor, com o aviso, e fica sem faixa.
    tefe = territorios["code:130420"]
    assert tefe["observado"][-1]["estado"] == "zero_confirmado"
    assert [cenario["final"]["total"] for cenario in tefe["cenarios"]] == [4.0, 0.0, 4.0]
    sem_a_taxa = tefe["cenarios"][0]
    assert sem_a_taxa["metodo"] == jeito("padrao", "M0", "M1", voltou_ao_m0=True)
    assert [item["codigo"] for item in sem_a_taxa["avisos"]] == ["VOLTA_AO_M0", "HORIZONTE_CAUTELA"] and sem_a_taxa["avisos"][0]["texto"] == SEM_A_TAXA_COMPOSTA
    assert sem_a_taxa["faixa"] == {"estado": "indisponivel", "motivo": SO_O_ULTIMO_VALOR.format(ROTULOS["M1"]), "rotulo": None, "em_10": 8}
    assert sem_a_taxa["texto"].endswith("TEFE (AM) teria 4 médicos em jun/2026. Base: registros até jun/2024.")
    assert sem_a_taxa["entenda"]["jeito"]["texto"].endswith(NAO_PODE_SER_USADO)
    # O estado como unidade (contagem estadual de médicos únicos) segue a escolha do nível dele: o último valor, com o aviso, mais
    # os 4 da intervenção. O M0d não se aplica a ele.
    para = territorios["uf:15"]
    assert (para["rotulo"], para["tipo"], para["unidade"]) == ("Pará (PA)", "estado", series_brasil.UNIDADE_ESTADO)
    assert para["cenarios"][0]["metodo"] == jeito("padrao", "M0", "M0") and para["cenarios"][0]["final"]["total"] == pytest.approx(49.0)
    assert [item["codigo"] for item in para["cenarios"][0]["avisos"]] == ["PADRAO_E_O_ULTIMO_VALOR", "HORIZONTE_CAUTELA"]
    assert para["cenarios"][2]["estado"] == "nao_aplicavel"
    # O conjunto (soma dos componentes), rotulado. O padrão (a taxa composta) é ajustado na série da soma, de 57 a 63; o M0d é a
    # soma das projeções dos membros. Aqui os dois dão o mesmo número: os membros são do Amazonas, e a soma deles é a do estado.
    par = territorios["g1"]
    assert (par["tipo"], par["membros"], par["nomes_dos_membros"], par["versao"]) == (
        "conjunto", ["code:130260", "code:130340"], ["MANAUS (AM)", "PARINTINS (AM)"], 2)
    assert par["cenarios"][0]["metodo"] == jeito("padrao", "M1", "M1") and par["cenarios"][0]["parametros"]["serie_da_soma"] is True
    assert par["cenarios"][0]["final"]["total"] == pytest.approx((51 + 12) * (1 + deriva) ** 2 + 4)
    assert "Par (soma das contagens dos componentes) teria" in par["cenarios"][0]["texto"]
    assert par["cenarios"][2]["final"]["total"] == pytest.approx((51 + 12) * (1 + deriva) ** 2 + 4)
    assert "Par (soma das projeções dos membros) teria" in par["cenarios"][2]["texto"]
    assert any("soma dos componentes" in nota for nota in body["notas"]) and any("não são previsão" in nota for nota in body["notas"])
    assert any(nota.startswith("\"Continuar como vinha\" usa o jeito de projetar que a própria base escolheu, pela retroprojeção") for nota in body["notas"])
    assert any(nota.startswith("A faixa de 8 em cada 10 só existe para o jeito e a janela escolhidos pela base") for nota in body["notas"])
    assert any(nota.endswith("A base só tem médicos, com registros de janeiro e junho (5 e 7 meses entre um e outro).") for nota in body["notas"])
    # Sem cenários no pedido: um cenário sem intervenção, no método padrão, 2 anos depois do último registro.
    simples = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}}))
    assert simples["horizonte"]["data"] == "202606" and [c["nome"] for c in simples["territorios"][0]["cenarios"]] == ["Sem intervenção"]
    assert simples["territorios"][0]["cenarios"][0]["metodo"] == jeito("padrao", "M1", "M1")
    # A janela escolhida entre as competências reais; o registro ausente é lacuna, não zero.
    janela = corpo(pedir({"base": {"municipios": {"ids": ["code:130340"]}}, "janela": {"inicio": "201406", "fim": "201606"},
                          "horizonte": "201806", "cenarios": [{"metodo": "M1"}]}))
    parintins = janela["territorios"][0]
    assert janela["janela"] == {"inicio": "201406", "fim": "201606", "registros": 5, "anos": 2.0, "padrao": False}
    assert parintins["lacunas"] == ["201501"] and parintins["historico"]["registros"] == 4
    cenario = parintins["cenarios"][0]
    assert cenario["final"]["total"] == 20.0 and "RETROPROJECAO" in [item["codigo"] for item in cenario["avisos"]]
    assert [(ponto["data"], ponto["retroprojecao"], ponto["observado"]) for ponto in cenario["trajetoria"]] == [
        ("201701", True, 20.0), ("201706", True, 20.0), ("201801", True, 20.0), ("201806", True, 20.0)]
    # A opção `faixa`: 5, 8 ou 9 em cada 10; a resposta, as faixas da retroprojeção e a nota seguem a medida pedida.
    for em_10 in (5, 9):
        outra = corpo(pedir({**selecao, "faixa": em_10}))
        assert outra["faixa"] == {"em_10": em_10, "opcoes": [5, 8, 9], "padrao": 8} and outra["retroprojecao"]["em_10"] == em_10
        assert all(faixa["em_10"] == em_10 and faixa["pede"] == FAIXAS[em_10][2] for faixa in outra["retroprojecao"]["faixas"])
        assert outra["territorios"][0]["cenarios"][0]["faixa"]["em_10"] == em_10
        assert any(nota.startswith("A faixa de %d em cada 10 só existe" % em_10) for nota in outra["notas"])
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
           "Intervenção inválida: a quantidade é um número acima de zero.")
    recusa(pedir({**selecao, "cenarios": [{"metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 1, "em": "202501",
                                                                             "territorios": ["code:150140"]}]}]}), "precisam estar na seleção")
    recusa(pedir({"base": {"municipios": {"ids": ["code:150140"]}}, "estados_unidade": ["15"]}), "junto com o estado inteiro")
    for invalida in (7, "8", True, 8.5, None):
        recusa(pedir({**selecao, "faixa": invalida}), "Faixa inválida: escolha 5, 8 ou 9 em cada 10.")
    assert any(nota.startswith("A faixa de 8 em cada 10 só existe") for nota in corpo(pedir({**selecao, "faixa": 8.0}))["notas"])   # 8.0 é 8
    # Sem base nenhuma, a rota diz o que fazer. Uma planilha enviada é aceita desde o comando V23 (como no Detector) e passa pelo
    # mesmo portão das análises, que pede as colunas; a planilha inteira está em test_ferramentas_qualquer_base.py.
    recusa(client.post("/api/simulador", data={"dataset": "", "options": "{}"}), "Escolha a base do Brasil ou envie uma planilha")
    recusa(client.post("/api/simulador", data={"options": "{}"}, files={"file": ("p.csv", b"a;b\n1;2\n", "text/csv")}),
           "Escolha a coluna territorial")


# --------------------------------------------------------------------------------------------- etapa 5: Brasil, referências e planejamento inverso
def _comparacao(body, territorio, referencia, cenario=0):
    item = next(item for item in body["territorios"] if item["id"] == territorio)
    return next(c for c in item["cenarios"][cenario]["comparacoes"] if c["id"] == referencia)


PROVISORIO_DO_BRASIL = ("Para o Brasil, o método padrão é provisório: uma série só não tem retroprojeção própria, e vale o jeito escolhido para os "
                        "estados. Ele só foi conferido num período de crescimento.")
SEM_FAIXA_DO_BRASIL = {"estado": "indisponivel", "motivo": "Não há faixa para o Brasil: uma série só não tem retroprojeção própria.", "rotulo": None,
                       "em_10": 8}


def test_rota_o_brasil_e_territorio_so_do_simulador_com_o_padrao_provisorio(catalogo):
    body = corpo(pedir({"brasil": True, "horizonte": "202606", "cenarios": [{"id": "p", "metodo": "padrao"}, {"id": "m1", "metodo": "M1"},
                                                                            {"id": "g", "metodo": "M0g"}]}))
    [brasil] = body["territorios"]
    assert (brasil["id"], brasil["tipo"], brasil["nivel"], brasil["rotulo"], brasil["uf"], brasil["unidade"]) == (
        "br", "brasil", "brasil", "Brasil", None, series_brasil.UNIDADE_BRASIL)
    padrao, composta, da_base = brasil["cenarios"]
    # O Brasil não tem retroprojeção própria (é uma série só): vale o jeito escolhido para os estados, como provisório, com o
    # aviso. Neste catálogo, as contagens estaduais não mudam: nenhum jeito erra menos que o último valor, e o padrão é ele.
    assert padrao["metodo"] == jeito("padrao", "M0", "M0", provisorio=True)
    assert [item["codigo"] for item in padrao["avisos"]] == ["PADRAO_E_O_ULTIMO_VALOR", "PADRAO_PROVISORIO_DO_NIVEL", "HORIZONTE_CAUTELA"]
    assert next(item["texto"] for item in padrao["avisos"] if item["codigo"] == "PADRAO_PROVISORIO_DO_NIVEL") == PROVISORIO_DO_BRASIL
    assert padrao["parametros"]["n0"] == 1110 and padrao["final"]["total"] == 1110 and padrao["final"]["faixa"] is None
    assert padrao["faixa"] == SEM_FAIXA_DO_BRASIL
    assert padrao["texto"].startswith(FIXO) and "sem intervenção, Brasil teria 1.110 médicos em jun/2026." in padrao["texto"]
    assert "hipotetico" not in padrao   # a escala estrutural é só dos municípios
    # A taxa composta, pedida pelo nome: a contagem nacional vai de 1.050 (jun/2021) a 1.110 (jun/2024).
    taxa = (1110 / 1050) ** (1 / 3) - 1
    assert composta["metodo"] == jeito("M1", "M1", "M0")
    assert composta["parametros"]["n0"] == 1110 and composta["parametros"]["taxa_pct"] == pytest.approx(100 * taxa)
    assert composta["final"]["total"] == pytest.approx(1110 * (1 + taxa) ** 2) and composta["final"]["faixa"] is None
    assert composta["faixa"] == SEM_FAIXA_DO_BRASIL   # o motivo do Brasil vem primeiro, também com um método pedido pelo nome
    assert composta["texto"].startswith(FIXO) and "sem intervenção, Brasil teria 1.152 médicos em jun/2026." in composta["texto"]
    # O crescimento da base toda não vale para o todo: a série dele é a própria base toda.
    assert da_base["estado"] == "nao_aplicavel" and da_base["motivo"] == (
        "O crescimento da base toda não vale para o Brasil: a série é a própria base toda. Use a taxa composta (M1).")
    assert any("e o Brasil, a contagem do todo, com um padrão provisório (o jeito escolhido para o nível de baixo)" in nota for nota in body["notas"])
    # O Brasil entra por último, ao lado dos demais territórios: cada um é simulado à parte, e ele nunca é somado a eles.
    juntos = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "estados_unidade": ["15"], "brasil": True}))
    assert [item["id"] for item in juntos["territorios"]] == ["code:130260", "uf:15", "br"]
    # Sem "brasil": true, nada muda; e o Detector de Sinais não tem o Brasil como unidade.
    assert [item["id"] for item in corpo(pedir({"estados_unidade": ["15"], "brasil": False}))["territorios"]] == ["uf:15"]
    with pytest.raises(ValueError, match="Opção desconhecida no pedido do Detector: brasil"):
        detector.compute(main._brazil_sources(""), {"brasil": True})


@pytest.mark.parametrize("catalogo", [ESTADOS_QUE_CRESCEM], indirect=True)
def test_rota_o_padrao_do_brasil_segue_o_jeito_escolhido_para_os_estados(catalogo):
    """Com contagens estaduais que crescem (o Amazonas, um médico a mais por registro; o Pará, parado), a retroprojeção dos
    estados escolhe a taxa composta do próprio estado; o padrão do Brasil passa a ser ela, na contagem nacional, ainda provisório."""
    body = corpo(pedir({"brasil": True, "estados_unidade": ["13"], "horizonte": "202606"}))
    dos_estados = body["retroprojecao"]["niveis"]["estados"]["escolha"]
    do_catalogo = detector.base_dos_estados(series_brasil.base_de(main._brazil_sources("")))
    escolhido, candidatos = _escolha_de_referencia(_casos_de_referencia(do_catalogo))
    assert escolhido == dos_estados["metodo"] == "M1" and dos_estados["motivo"] == "escolhido"
    assert dos_estados["candidatos"] == [{**candidato, "frente_ao_m0": pytest.approx(candidato["frente_ao_m0"]), "rotulo": ROTULOS[candidato["metodo"]]}
                                         for candidato in candidatos]
    assert [(candidato["metodo"], candidato["casos"], candidato["vale"]) for candidato in candidatos] == [("M1", 44, True), ("M0g", 44, False)]
    assert dos_estados["texto"] == ("Para os estados como unidade, a base escolheu a taxa composta da janela: na retroprojeção, ela errou 83% menos "
                                    "que manter o último valor, e menos em 22 de 22 combinações de origem e prazo.")
    amazonas, brasil = body["territorios"]
    # O estado como unidade: a taxa composta da contagem estadual, de 45 (jun/2021) a 51 (jun/2024). Não é provisório.
    do_estado = amazonas["cenarios"][0]
    assert do_estado["metodo"] == jeito("padrao", "M1", "M1") and [item["codigo"] for item in do_estado["avisos"]] == ["HORIZONTE_CAUTELA"]
    assert do_estado["final"]["total"] == pytest.approx(51 * (51 / 45) ** (2 / 3))
    # O Brasil: a mesma taxa composta, na contagem nacional (de 1.050 a 1.110), como provisório e sem faixa.
    cenario = brasil["cenarios"][0]
    taxa = (1110 / 1050) ** (1 / 3) - 1
    assert cenario["metodo"] == jeito("padrao", "M1", "M1", provisorio=True)
    assert cenario["parametros"]["n0"] == 1110 and cenario["parametros"]["taxa_pct"] == pytest.approx(100 * taxa)
    assert cenario["final"]["total"] == pytest.approx(1110 * (1 + taxa) ** 2) and cenario["final"]["faixa"] is None
    assert cenario["faixa"] == SEM_FAIXA_DO_BRASIL
    assert [item["codigo"] for item in cenario["avisos"]] == ["PADRAO_PROVISORIO_DO_NIVEL", "HORIZONTE_CAUTELA"]
    assert cenario["avisos"][0]["texto"] == PROVISORIO_DO_BRASIL
    assert cenario["texto"].startswith(FIXO) and "sem intervenção, Brasil teria 1.152 médicos em jun/2026." in cenario["texto"]
    assert cenario["entenda"]["jeito"]["texto"].endswith(ERROU_MENOS) and cenario["entenda"]["faixa"]["texto"] == SEM_FAIXA_DO_BRASIL["motivo"]
    assert "hipotetico" not in cenario


def test_rota_referencias_fixas_dinamicas_e_valor_com_alcance_e_sobreposicao(catalogo):
    selecao = {"base": {"municipios": {"ids": ["code:130260", "code:130340"]}}, "estados_unidade": ["15"],
               "conjuntos": [{"id": "g1", "rotulo": "Par", "membros": ["code:130260", "code:130340"], "versao": 2}]}
    com_reforco = {"id": "c1", "metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 5, "em": "202501", "ate": "202601",
                                                                 "a_cada_meses": 12}]}
    body = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [com_reforco], "referencias": [
        {"id": "fixa", "territorio": "code:150140"}, {"id": "din", "territorio": "code:130260", "tipo": "dinamica", "metodo": "M0d"},
        {"id": "val", "tipo": "valor", "valor": 20, "rotulo": "Meta local"}, {"id": "uf", "territorio": "uf:13"},
        {"id": "br", "territorio": "br", "tipo": "dinamica"}]}))
    # Sem `forma` e sem a hipótese de população no pedido, vale o de antes: a diferença (os campos são novos, de 15/11/2026).
    assert body["comparacao"] == {"metrica": "quantidade", "forma": "diferenca", "populacao_pct_ao_ano": None, "hipotese_de_populacao": None}
    assert [(ref["id"], ref["rotulo"], ref["tipo"], ref["territorio"], ref["estado"], ref["descricao"]) for ref in body["referencias"]] == [
        ("fixa", "BELEM (PA)", "fixa", "code:150140", "calculada", "fixa: o valor de jun/2024 mantido"),
        ("din", "MANAUS (AM)", "dinamica", "code:130260", "calculada",
         "dinâmica: persistência com o crescimento recente do estado, com registros até jun/2024"),
        ("val", "Meta local", "valor", None, "calculada", "valor informado por você, mantido"),
        ("uf", "Amazonas (AM)", "fixa", "uf:13", "calculada", "fixa: o valor de jun/2024 mantido"),
        # Sem método no pedido, a referência dinâmica segue o padrão do nível dela: no Brasil deste catálogo, o último valor.
        ("br", "Brasil", "dinamica", "br", "calculada", "dinâmica: persistência (o último valor se mantém), com registros até jun/2024")]
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
    # A referência dinâmica segue o método dela (aqui, a persistência com o crescimento recente do estado, pedida pelo nome), sem
    # intervenções; na origem, vale o registro.
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
    assert do_brasil[-2:] == [NENHUM_VALE, PROVISORIO_DO_BRASIL]   # os avisos do método da referência dinâmica (o padrão do Brasil)
    assert _comparacao(body, "uf:15", "fixa")["avisos"][0] == "O território contém a referência: a comparação não é independente."
    assert _comparacao(body, "g1", "din")["avisos"][0] == "O território e a referência têm 1 município em comum: a comparação não é independente."
    assert any(nota.startswith("Referências: a comparação mostra a diferença, a razão e o índice") and "nenhuma data é inventada" in nota
               and "não é comparar a suficiência do atendimento" in nota for nota in body["notas"])
    # Sem método no pedido, a referência dinâmica segue o jeito que a base escolheu para o nível dela: a taxa composta, num
    # município; o último valor, num estado deste catálogo. O crescimento da base toda (M0g) também serve de referência.
    do_padrao = corpo(pedir({"base": {"municipios": {"ids": ["code:130340"]}}, "horizonte": "202606", "cenarios": [{"id": "c1", "metodo": "M0"}],
                             "referencias": [{"id": "m", "territorio": "code:130260", "tipo": "dinamica"},
                                             {"id": "e", "territorio": "uf:13", "tipo": "dinamica"},
                                             {"id": "g", "territorio": "code:130260", "tipo": "dinamica", "metodo": "M0g"}]}))
    assert [(ref["id"], ref["descricao"]) for ref in do_padrao["referencias"]] == [
        ("m", "dinâmica: taxa composta da janela, com registros até jun/2024"),
        ("e", "dinâmica: persistência (o último valor se mantém), com registros até jun/2024"),
        ("g", "dinâmica: persistência com o crescimento recente da base toda, com registros até jun/2024")]
    do_municipio = _comparacao(do_padrao, "code:130340", "m")
    assert do_municipio["metodo"] == "M1" and do_municipio["final"]["referencia"] == pytest.approx(51 * (51 / 45) ** (2 / 3)) and do_municipio["avisos"] == []
    assert _comparacao(do_padrao, "code:130340", "e")["metodo"] == "M0" and _comparacao(do_padrao, "code:130340", "e")["avisos"][-1] == NENHUM_VALE
    assert _comparacao(do_padrao, "code:130340", "g")["metodo"] == "M0g"
    # Um conjunto da seleção local também serve de referência; diante de si mesmo, o valor é o mesmo.
    conjunto = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [{"id": "c1", "metodo": "M0"}],
                            "referencias": [{"id": "g", "territorio": "g1"}]}))
    assert _comparacao(conjunto, "code:130260", "g")["avisos"][0] == (
        "O território e a referência têm 1 município em comum: a comparação não é independente.")
    assert _comparacao(conjunto, "code:130260", "g")["final"]["referencia"] == 63.0
    proprio = _comparacao(conjunto, "g1", "g")
    assert proprio["avisos"] == ["A referência é o próprio território."] and ": o mesmo valor (índice 100; 100 é a referência)." in proprio["texto"]
    # Sem referências no pedido, os cenários não têm comparações.
    # A comparação pela razão (Proposta V3, seção C.5): a frase diz quantas vezes o valor da referência o território teria; os
    # números de cada data (a diferença, a razão e o índice) são os mesmos das duas formas.
    pela_razao = corpo(pedir({**selecao, "horizonte": "202606", "cenarios": [com_reforco], "comparacao": {"forma": "razao"}, "referencias": [
        {"id": "fixa", "territorio": "code:150140"}, {"id": "val", "tipo": "valor", "valor": 20, "rotulo": "Meta local"},
        {"id": "zero", "tipo": "valor", "valor": 0, "rotulo": "Zero"}]}))
    assert pela_razao["comparacao"] == {"metrica": "quantidade", "forma": "razao", "populacao_pct_ao_ano": None, "hipotese_de_populacao": None}
    assert (_comparacao(pela_razao, "code:130340", "val")["forma"], alcanca["forma"]) == ("razao", "diferenca")
    assert _comparacao(pela_razao, "code:130340", "val")["texto"] == (
        "Em jun/2026, PARINTINS (AM) teria 22 médicos, e a referência Meta local (valor informado por você, mantido), 20: 1,10 vezes o valor "
        "da referência (índice 110; 100 é a referência). No cenário, alcança a referência em jan/2026, a primeira data avaliada em que isso "
        "ocorre.")
    assert _comparacao(pela_razao, "code:130340", "fixa")["texto"].endswith(
        "50: 0,44 vezes o valor da referência (índice 44; 100 é a referência). Não alcança no horizonte simulado (até jun/2026).")
    for territorio, referencia in (("code:130340", "val"), ("code:130340", "fixa"), ("code:130260", "fixa"), ("uf:15", "fixa")):
        assert _comparacao(pela_razao, territorio, referencia)["pontos"] == _comparacao(body, territorio, referencia)["pontos"]
    # Diante de uma referência em zero, a razão não existe, e a frase diz isso (nenhum número é inventado).
    do_zero = _comparacao(pela_razao, "code:130340", "zero")
    assert (do_zero["final"]["razao"], do_zero["final"]["indice"], do_zero["final"]["diferenca"]) == (None, None, -22.0)
    assert do_zero["texto"] == ("Em jun/2026, PARINTINS (AM) teria 22 médicos, e a referência Zero (valor informado por você, mantido), 0: a "
                                "razão não pode ser calculada, porque a referência é zero. Na origem, o território já está no nível da "
                                "referência ou acima dele.")
    sem = corpo(pedir({**selecao, "horizonte": "202606"}))
    assert sem["referencias"] == [] and "comparacoes" not in sem["territorios"][0]["cenarios"][0]
    assert not any(nota.startswith("Referências:") for nota in sem["notas"])


def test_rota_comparacao_por_taxa_declara_a_populacao_constante(catalogo):
    # Populações do catálogo: Manaus 2.000, Parintins 1.000, Belém 4.000 (o Pará soma 4.000; o Brasil, 8.000).
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:130260", "code:130340"]}}, "estados_unidade": ["15"], "horizonte": "202606",
                        "cenarios": [{"id": "c1", "metodo": "M0"}], "comparacao": {"metrica": "taxa"},
                        "referencias": [{"id": "fixa", "territorio": "code:150140"}, {"id": "val", "tipo": "valor", "valor": 20},
                                        {"id": "br", "territorio": "br"}]}))
    assert body["comparacao"] == {"metrica": "taxa", "forma": "diferenca", "populacao_pct_ao_ano": None,
                                  "hipotese_de_populacao": "constante: a população de jun/2024 em todas as datas simuladas"}
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
    assert any("por taxa, vale a hipótese de população constante." in nota for nota in body["notas"])


def test_rota_comparacao_por_taxa_com_a_populacao_crescendo_e_uma_hipotese_da_pessoa(catalogo):
    """Proposta V3, seção C.5: na comparação por taxa, a população pode ser a do último registro (o padrão) ou crescer x% ao ano
    depois dele, uma hipótese da pessoa — a mesma taxa no território e na referência. A base não traz população futura: nada é
    estimado pelo sistema, e a frase, a resposta e a nota dizem a hipótese."""
    pedido = {"base": {"municipios": {"ids": ["code:130260", "code:130340"]}}, "horizonte": "202606", "cenarios": [{"id": "c1", "metodo": "M0"}],
              "referencias": [{"id": "fixa", "territorio": "code:150140"}, {"id": "val", "tipo": "valor", "valor": 20}]}
    constante = corpo(pedir({**pedido, "comparacao": {"metrica": "taxa"}}))
    body = corpo(pedir({**pedido, "comparacao": {"metrica": "taxa", "populacao_pct_ao_ano": 2}}))
    assert body["comparacao"] == {
        "metrica": "taxa", "forma": "diferenca", "populacao_pct_ao_ano": 2.0,
        "hipotese_de_populacao": "crescendo 2% ao ano depois de jun/2024 (hipótese sua), a mesma taxa em todos os territórios; até essa "
                                 "data, a população de jun/2024"}
    # Manaus (51 médicos, 2.000 habitantes) e Belém (50 e 4.000), 2 anos depois do último registro: as duas populações crescem
    # 2% ao ano (× 1,02²), e as taxas caem na mesma proporção; a razão e o índice não mudam.
    manaus, antes = _comparacao(body, "code:130260", "fixa"), _comparacao(constante, "code:130260", "fixa")
    assert (antes["final"]["territorio"], antes["final"]["referencia"]) == (25.5, 12.5)
    assert manaus["final"] == {"data": "202606", "territorio": pytest.approx(25.5 / 1.02 ** 2), "referencia": pytest.approx(12.5 / 1.02 ** 2),
                               "diferenca": pytest.approx(-13 / 1.02 ** 2), "razao": pytest.approx(2.04), "indice": pytest.approx(204.0)}
    # No último registro (a origem), vale a população dele; entre as datas, o crescimento é proporcional ao tempo (7 meses).
    assert [ponto["data"] for ponto in manaus["pontos"]] == ["202406", "202501", "202506", "202601", "202606"]
    assert manaus["inicial"] == antes["inicial"] and manaus["pontos"][1]["territorio"] == pytest.approx(25.5 / 1.02 ** (7 / 12))
    assert manaus["texto"] == ("Em jun/2026, MANAUS (AM) teria 24,51 médicos por 1.000 habitantes, e a referência BELEM (PA) (fixa: o valor de "
                               "jun/2024 mantido), 12,01: 12,50 acima da referência (índice 204; 100 é a referência). Na origem, o território "
                               "já está no nível da referência ou acima dele. Hipótese sua: população crescendo 2% ao ano depois de jun/2024, "
                               "a mesma taxa no território e na referência.")
    # O valor informado já é uma taxa e não muda: só a taxa do território cai.
    parintins = _comparacao(body, "code:130340", "val")
    assert parintins["final"] == {"data": "202606", "territorio": pytest.approx(12 / 1.02 ** 2), "referencia": 20.0,
                                  "diferenca": pytest.approx(20 - 12 / 1.02 ** 2), "razao": pytest.approx(0.6 / 1.02 ** 2),
                                  "indice": pytest.approx(60 / 1.02 ** 2)}
    assert parintins["texto"].endswith("20: 8,47 abaixo da referência (índice 57,7; 100 é a referência). Não alcança no horizonte simulado (até "
                                       "jun/2026). Hipótese sua: população crescendo 2% ao ano depois de jun/2024; o valor informado não muda.")
    assert any(nota.endswith("por taxa, vale a hipótese de população crescendo 2% ao ano depois de jun/2024, a mesma taxa no território e na "
                             "referência (a base não traz população futura: a taxa de crescimento é uma hipótese sua).") for nota in body["notas"])
    # A população diminuindo, com a comparação pela razão: as duas escolhas valem juntas.
    caindo = corpo(pedir({**pedido, "comparacao": {"metrica": "taxa", "forma": "razao", "populacao_pct_ao_ano": -1.5}}))
    assert caindo["comparacao"]["hipotese_de_populacao"].startswith("diminuindo 1,5% ao ano depois de jun/2024 (hipótese sua)")
    assert _comparacao(caindo, "code:130260", "fixa")["final"]["territorio"] == pytest.approx(25.5 / 0.985 ** 2)
    assert _comparacao(caindo, "code:130260", "fixa")["texto"].endswith(
        "12,88: 2,04 vezes o valor da referência (índice 204; 100 é a referência). Na origem, o território já está no nível da referência ou "
        "acima dele. Hipótese sua: população diminuindo 1,5% ao ano depois de jun/2024, a mesma taxa no território e na referência.")
    # Zero é a população constante: a resposta e os textos são os de antes.
    assert corpo(pedir({**pedido, "comparacao": {"metrica": "taxa", "populacao_pct_ao_ano": 0}})) == constante


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
    # A meta diz de onde veio (o patamar é a média de 4 registros) e é sempre um número inteiro de médicos (revisão das capturas,
    # 14/11/2026).
    patamar = plano({"meta": {"tipo": "patamar"}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert patamar["meta"] == {"tipo": "patamar", "valor": 20.0, "patamar": 20.0, "registros": 4, "arredondado": False,
                               "rotulo": "Meta hipotética: voltar ao patamar de 20 médicos em jun/2026 (média de 4 registros)"}
    assert patamar["por_evento"] == 8 and patamar["texto"].startswith(
        "Meta hipotética: voltar ao patamar de 20 médicos em jun/2026 (média de 4 registros). ")
    # O valor que vem no pedido e é o patamar do território (o que o Detector leva) tem o mesmo rótulo; outro valor é dito como
    # informado, sem a média que ele não é.
    do_detector = plano({"meta": {"tipo": "patamar", "valor": 20}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert do_detector["meta"] == patamar["meta"]
    informado = plano({"meta": {"tipo": "patamar", "valor": 18}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert (informado["meta"]["valor"], informado["por_evento"]) == (18.0, 6)
    assert (informado["meta"]["registros"], informado["meta"]["rotulo"]) == (
        None, "Meta hipotética: voltar ao patamar de 18 médicos em jun/2026 (patamar informado)")
    # O patamar com decimal (como os 78,25 que o Detector leva): a meta é o inteiro acima dele, para o resultado do cenário não
    # parecer abaixo da meta, e o rótulo diz o patamar sem arredondar. De 12 para 18,25 faltariam 6,25: 7 médicos, e não 6,
    # chegam aos 19 da meta.
    com_decimal = plano({"meta": {"tipo": "patamar", "valor": 18.25}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert com_decimal["meta"] == {
        "tipo": "patamar", "valor": 19.0, "patamar": 18.25, "registros": None, "arredondado": True,
        "rotulo": "Meta hipotética: voltar ao patamar de 19 médicos em jun/2026 (patamar informado: 18,25, arredondado para cima)"}
    assert (com_decimal["por_evento"], com_decimal["teorico_por_evento"], com_decimal["resultado"]) == (7, 7.0, 19.0)
    assert "PARINTINS (AM) teria 19 médicos em jun/2026." in com_decimal["texto"]
    # Com vários territórios, a conta é de cada um: Manaus já está acima do patamar dela (45,5: a meta é 46); Tefé (em zero)
    # voltaria a 3.
    varios = plano({"meta": {"tipo": "patamar"}, "em": "202506"},
                   selecao={"base": {"municipios": {"ids": ["code:130260", "code:130420"]}}, "estados_unidade": ["15"], "horizonte": "202606"})[1]
    assert [(chave, c["planejamento"]["estado"], c["planejamento"]["meta"]["valor"], c["planejamento"]["por_evento"]) for chave, c in varios.items()] == [
        ("code:130260", "ja_alcancada", 46.0, 0), ("code:130420", "calculado", 3.0, 3), ("uf:15", "ja_alcancada", 45.0, 0)]
    assert varios["code:130260"]["planejamento"]["meta"]["patamar"] == 45.5
    assert "acréscimo de 3 médicos neste território, pelo planejamento inverso," in varios["code:130420"]["planejamento"]["texto"]
    # A meta numa referência: o valor dela na data final.
    da_referencia = plano({"meta": {"tipo": "referencia", "referencia": "fixa"}, "em": "202506"},
                          referencias=[{"id": "fixa", "territorio": "code:150140"}])[1]["code:130340"]["planejamento"]
    assert da_referencia["meta"] == {"tipo": "referencia", "valor": 50.0,
                                     "rotulo": "Meta hipotética: alcançar a referência BELEM (PA) (50 médicos em jun/2026)"}
    assert (da_referencia["por_evento"], da_referencia["resultado"]) == (38, 50.0)
    ausente = plano({"meta": {"tipo": "referencia", "referencia": "x"}, "em": "202506"})[1]["code:130340"]["planejamento"]
    assert ausente == {"estado": "nao_calculavel", "motivo": "A referência da meta não está no pedido."}
    # Com o método padrão, a conta parte da base do jeito que a base escolheu (em Manaus, a taxa composta: 55,4 em jun/2026).
    do_padrao = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "horizonte": "202606", "cenarios": [
        {"id": "c1", "metodo": "padrao", "planejamento": {"meta": {"tipo": "valor", "valor": 60}, "em": "202506"}}]}))["territorios"][0]["cenarios"][0]
    na_data_final = 51 * (51 / 45) ** (2 / 3)
    assert do_padrao["planejamento"]["base_na_data_final"] == pytest.approx(na_data_final)
    assert (do_padrao["planejamento"]["por_evento"], do_padrao["planejamento"]["teorico_por_evento"]) == (5, pytest.approx(60 - na_data_final))
    assert "com o método taxa composta da janela e as premissas" in do_padrao["planejamento"]["texto"]


def test_rota_hipotese_derivada_da_simulacao_so_a_dependencia_de_poucos_medicos(catalogo):
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:130420", "code:130260"]}}, "estados_unidade": ["15"], "brasil": True,
                        "conjuntos": [{"id": "g1", "rotulo": "Par", "membros": ["code:130340", "code:150140"]}], "horizonte": "202606",
                        "cenarios": [{"id": "c1", "metodo": "M0", "intervencoes": [{"tipo": "acrescimo", "quantidade": 4, "em": "202501"}]}]}))
    cenarios = {item["id"]: item["cenarios"][0] for item in body["territorios"]}
    # Tefé, em zero, teria 4 médicos no cenário: a única leitura do Detector que vale para um valor simulado é a escala estrutural.
    assert cenarios["code:130420"]["hipotetico"] == {"rotulo": "hipótese do cenário", "data": "202606", "valor": 4.0, "inteiro": 4,
                                                     "classe": "moderado", "impacto_pct": 25.0}
    assert cenarios["code:130260"]["hipotetico"]["classe"] is None and cenarios["code:130260"]["hipotetico"]["inteiro"] == 55
    # Só para municípios, como a escala estrutural do Detector; e nenhum teste de evento observado (perda, patamar, declínio).
    assert all("hipotetico" not in cenarios[chave] for chave in ("uf:15", "g1", "br"))
    assert set(cenarios["code:130420"]["hipotetico"]) == {"rotulo", "data", "valor", "inteiro", "classe", "impacto_pct"}


def test_rota_recusas_das_referencias_da_metrica_e_do_planejamento(catalogo):
    so = {"base": {"municipios": {"ids": ["code:130340"]}}, "horizonte": "202606"}
    recusa(pedir({**so, "referencias": [{"id": "r" + str(k), "tipo": "valor", "valor": 1} for k in range(6)]}), "Referências inválidas: envie uma lista de até 5.")
    recusa(pedir({**so, "referencias": [{"territorio": "xx"}]}),
           "indique um território da base (na base do Brasil, um município, code:…, ou um estado, uf:…), o todo (br) ou um conjunto")
    recusa(pedir({**so, "referencias": [{"territorio": "g9"}]}), "um conjunto da seleção do Simulador")
    recusa(pedir({**so, "referencias": [{"id": "a", "tipo": "valor", "valor": 1}, {"id": "a", "tipo": "valor", "valor": 2}]}), "Referências com o mesmo id")
    recusa(pedir({**so, "referencias": [{"territorio": "br", "tipo": "movel"}]}), "o tipo é fixa, dinamica ou valor")
    recusa(pedir({**so, "referencias": [{"tipo": "valor", "valor": -1}]}), "um número igual ou maior que zero")
    recusa(pedir({**so, "referencias": [{"territorio": "br", "tipo": "dinamica", "metodo": "x"}]}), "Método desconhecido na referência: x.")
    recusa(pedir({**so, "referencias": [{"territorio": "br", "tipo": "dinamica", "metodo": "manual"}]}), "O sistema não sugere uma taxa.")
    recusa(pedir({**so, "referencias": [{"territorio": "code:999999"}]}), "Território fora da base Brasil")
    recusa(pedir({**so, "comparacao": {"metrica": "indice"}}), "Comparação inválida: a métrica é quantidade ou taxa.")
    recusa(pedir({**so, "comparacao": {"forma": "soma"}}), "Comparação inválida: a forma é diferenca ou razao.")
    for crescimento in (25, -20.5, "2", True, None):
        recusa(pedir({**so, "comparacao": {"metrica": "taxa", "populacao_pct_ao_ano": crescimento}}),
               "Comparação inválida: o crescimento da população é um número entre −20% e +20% ao ano.")
    recusa(pedir({**so, "comparacao": {"populacao_pct_ao_ano": 2}}),
           "Comparação inválida: o crescimento da população vale só na comparação por taxa (a métrica taxa).")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"em": "202506"}}]}), "envie a meta e o calendário dos acréscimos")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"meta": {"tipo": "x"}, "em": "202506"}}]}),
           "a meta é um valor, o patamar anterior ou uma referência")
    recusa(pedir({**so, "cenarios": [{"metodo": "M0", "planejamento": {"meta": {"tipo": "valor", "valor": 0}, "em": "202506"}}]}),
           "Planejamento inverso inválido: a meta é um número acima de zero.")
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


def _resumo(candidato):
    return candidato["metodo"], round(candidato["frente_ao_m0"], 3), candidato["menos_erro_em"], candidato["combinacoes"], candidato["vale"]


def test_real_a_escolha_as_faixas_e_os_erros_da_retroprojecao_da_proposta(real):
    """Os critérios de aceitação do comando V23 (Docs/DETECTOR_E_SIMULADOR_V3.md, seções C.3 e C.4): na base do Brasil, a regra
    dá o M0d nos municípios e o M1 nos estados; as faixas de 8 em 10 dos municípios são as da tabela; as de 3 e 4 anos são
    provisórias; nos estados, a faixa de 8 em 10 fica indisponível."""
    municipios, estados = simulador.retroprojetar(real), simulador.retroprojetar(real, "estados")
    assert municipios.origens == estados.origens == JUNHOS
    assert (municipios.nivel, estados.nivel, len(municipios.casos), len(estados.casos)) == ("municipios", "estados", 122317, 594)
    # A escolha: nos municípios, o crescimento do estado (o da base toda erra um pouco menos, mas o do estado fica a até 5% dele,
    # e é o mais próximo; a taxa do próprio município erra mais que o último valor); nos estados, a taxa do próprio estado.
    assert (municipios.escolha["metodo"], municipios.escolha["motivo"], municipios.escolha["excecoes"]) == ("M0d", "escolhido", [])
    assert [_resumo(candidato) for candidato in municipios.escolha["candidatos"]] == [
        ("M1", 1.015, 2, 22, False), ("M0d", 0.714, 22, 22, True), ("M0g", 0.7, 22, 22, True)]
    assert (estados.escolha["metodo"], estados.escolha["motivo"], estados.escolha["excecoes"]) == ("M1", "escolhido", [])
    assert [_resumo(candidato) for candidato in estados.escolha["candidatos"]] == [("M1", 0.398, 22, 22, True), ("M0g", 0.41, 22, 22, True)]
    # As faixas de 8 em 10 do M0d municipal: P10 a P90 do erro relativo, por porte na origem (os dez da régua comum) e prazo.
    faixas = municipios.faixas
    assert [[_inteiros(faixas[(8, porte, anos)]) for anos in (1, 2, 3, 4)] for porte in range(10)] == [
        [(-9, 87), (-18, 105), (-21, 140), (-21, 153)],
        [(-26, 40), (-31, 56), (-33, 69), (-34, 82)],
        [(-23, 29), (-28, 40), (-29, 53), (-30, 62)],
        [(-19, 24), (-23, 34), (-24, 44), (-25, 55)],
        [(-15, 20), (-19, 30), (-20, 42), (-19, 55)],
        [(-12, 17), (-16, 26), (-16, 34), (-17, 42)],
        [(-9, 12), (-12, 20), (-14, 28), (-12, 37)],
        [(-6, 8), (-8, 16), (-10, 21), (-10, 28)],
        [(-6, 7), (-8, 14), (-10, 19), (-9, 23)],
        [(-5, 5), (-8, 14), (-10, 19), (-9, 23)]]
    assert [faixas[(8, 0, anos)]["casos"] for anos in (1, 2, 3, 4)] == [4039, 3649, 3216, 2715]
    assert [faixas[(8, 0, anos)]["origens"] for anos in (1, 2, 3, 4)] == [7, 6, 5, 4]
    # A retaguarda: de 3.000 a 9.999 médicos, com os portes vizinhos; com 10.000 ou mais (8 municípios), com os vizinhos em 1 ano
    # e com portes menores de 2 a 4 anos.
    assert [[faixas[(8, porte, anos)]["como"] for anos in (1, 2, 3, 4)] for porte in range(10)] == [["propria"] * 4] * 8 + [
        ["vizinhas"] * 4, ["vizinhas", "portes_menores", "portes_menores", "portes_menores"]]
    assert [faixas[(8, 8, anos)]["casos"] for anos in (1, 2, 3, 4)] == [679, 560, 446, 338]
    assert [faixas[(8, 9, anos)]["casos"] for anos in (1, 2, 3, 4)] == [203, 560, 446, 338]
    # A conferência no tempo: em 1 e 2 anos (6 e 4 origens de teste), as faixas cobriram 75% ou mais e estão conferidas — menos
    # a do porte de 10.000 ou mais, com poucos casos de teste; em 3 anos só há 2 origens de teste, e em 4, nenhuma: provisórias.
    assert [[faixas[(8, porte, anos)]["estado"] for anos in (1, 2, 3, 4)] for porte in range(10)] == [
        ["conferida", "conferida", "provisoria", "provisoria"]] * 9 + [["provisoria"] * 4]
    assert all([faixas[(8, porte, anos)]["origens_de_teste"] for anos in (1, 2, 3, 4)] == [6, 4, 2, 0] for porte in range(10))
    assert all(75 <= _inteiro(faixa["cobertura"]) <= 90 for (em_10, _, _), faixa in faixas.items() if em_10 == 8 and faixa["estado"] == "conferida")
    assert {faixa["motivo"] for (em_10, _, _), faixa in faixas.items() if em_10 == 8 and faixa["estado"] == "provisoria"} == {"sem_conferencia"}
    assert len(faixas) == 3 * 10 * 4   # as três medidas (5, 8 e 9 em 10), os dez portes e os quatro prazos
    # Nos estados, a faixa de 8 em 10 pede 200 casos por prazo, e a base tem 189 em 1 ano: indisponível em todos os portes.
    de_8 = {chave: faixa for chave, faixa in estados.faixas.items() if chave[0] == 8}
    assert len(de_8) == 16 and all(faixa["estado"] == "indisponivel" and faixa["motivo"] == "poucos_casos" and faixa["pede"] == 200 for faixa in de_8.values())
    assert [de_8[(8, 9, anos)]["casos"] for anos in (1, 2, 3, 4)] == [189, 162, 135, 108]
    assert any(faixa["estado"] == "provisoria" for chave, faixa in estados.faixas.items() if chave[0] == 5)   # a de 5 em 10 já existe
    tabela = {(linha["metodo"], linha["porte"], linha["anos"]): linha for linha in municipios.tabela}
    # Em 4 anos, a persistência com o crescimento do estado erra menos que a persistência em todos os portes; a taxa composta do
    # próprio município erra mais abaixo de 100 médicos. De 1 a 9 médicos, o M0d erra um pouco mais em 1 ano (1,04 e 1,02), mas
    # menos de 2 a 4 anos: não entra na exceção por porte.
    assert [round(tabela[("M0d", porte, 4)]["frente_ao_m0"], 2) for porte in range(10)] == [0.9, 0.87, 0.83, 0.78, 0.72, 0.64, 0.57, 0.53, 0.29, 0.41]
    assert [round(tabela[("M1", porte, 4)]["frente_ao_m0"], 2) for porte in range(10)] == [1.29, 1.39, 1.44, 1.27, 1.18, 0.97, 0.74, 0.61, 1.21, 0.42]
    assert [round(tabela[("M0d", porte, 1)]["frente_ao_m0"], 2) for porte in (0, 1, 2)] == [1.04, 1.02, 0.98]
    assert all(tabela[("M0", porte, anos)]["frente_ao_m0"] == pytest.approx(1.0) for porte in range(10) for anos in (1, 2, 3, 4))
    assert all(tabela[("M0d", porte, 4)]["vies"] < tabela[("M0", porte, 4)]["vies"] for porte in range(10))  # o viés cai com a deriva
    assert {linha["metodo"] for linha in estados.tabela} == {"M0", "M0g", "M1", "M2", "M3"} and {linha["porte"] for linha in estados.tabela} == {6, 7, 8, 9}


def test_real_cenarios_do_distrito_federal_rio_rufino_e_limites(real):
    # Distrito Federal: com a janela até jun/2019, a deriva (jun/2016 a jun/2019) pega a quebra de fonte, e o padrão (o M0d,
    # escolhido pela base) volta ao M0; com a janela padrão (até jun/2024), a deriva existe.
    antiga = corpo(pedir({"base": {"municipios": {"ids": ["code:530010"]}}, "janela": {"inicio": "201606", "fim": "201906"},
                          "horizonte": "202106"}))["territorios"][0]
    assert antiga["rotulo"] == "BRASILIA (DF)"
    cenario = antiga["cenarios"][0]
    assert cenario["metodo"] == jeito("padrao", "M0", "M0d", voltou_ao_m0=True)
    assert {"JANELA_DEPOIS_DA_QUEBRA", "VOLTA_AO_M0", "RETROPROJECAO"} <= {item["codigo"] for item in cenario["avisos"]}
    assert cenario["parametros"]["janela"]["inicio"] == "201801"
    assert cenario["faixa"] == {"estado": "indisponivel", "motivo": SO_O_ULTIMO_VALOR.format(ROTULOS["M0d"]), "rotulo": None, "em_10": 8}
    assert cenario["entenda"]["jeito"]["texto"].endswith(NAO_PODE_SER_USADO)
    assert [ponto.get("marca") for ponto in antiga["observado"][:9]] == ["quebra_de_fonte"] * 8 + [None]
    atual = corpo(pedir({"base": {"municipios": {"ids": ["code:530010"]}}}))["territorios"][0]["cenarios"][0]
    assert atual["metodo"] == jeito("padrao", "M0d", "M0d")
    # Brasília tem mais de 10.000 médicos, o porte dos 8 maiores municípios: a faixa junta os portes vizinhos (1 ano) e portes
    # menores (2 anos, a data final), e não tem casos de teste bastantes para a conferência: é provisória, com os avisos.
    assert (atual["faixa"]["estado"], atual["faixa"]["porte"], atual["faixa"]["ate_anos"], atual["faixa"]["conferencia"]) == (
        "disponivel", "10.000 ou mais", 4, "provisoria")
    assert (atual["faixa"]["casos"], atual["faixa"]["origens_de_teste"]) == (560, 4)
    assert atual["final"]["faixa"]["anos"] == 2 and atual["final"]["faixa"]["validada"] is False
    assert (atual["final"]["faixa"]["estado"], atual["final"]["faixa"]["como"]) == ("provisoria", "portes_menores")
    # O resumo da faixa descreve o prazo da data final (2 anos: com portes menores), não o do primeiro ano (com os vizinhos).
    assert (atual["faixa"]["como"], atual["faixa"]["rotulo"]) == (
        "portes_menores", "a margem observada no passado da base, em municípios do mesmo porte e de portes menores (a faixa fica mais larga, e por "
                          "isso mais cautelosa); acompanha a intervenção")
    assert [item["codigo"] for item in atual["avisos"]] == ["HORIZONTE_CAUTELA", "FAIXA_PROVISORIA", "FAIXA_COM_PORTES_MENORES"]
    assert atual["final"]["faixa"]["inferior"] < atual["final"]["total"] < atual["final"]["faixa"]["superior"]
    assert atual["texto"].startswith(FIXO) and "Base: registros até jun/2024." in atual["texto"]
    # Rio Rufino (SC): o registro de jun/2023 (4 → 87 → 5) é um pico que volta e fica fora da base do cenário.
    rio = corpo(pedir({"base": {"municipios": {"ids": ["code:421505"]}}, "cenarios": [{"id": "a", "metodo": "M2"}, {"id": "b", "metodo": "padrao"}]}))
    rufino = rio["territorios"][0]
    assert next(ponto for ponto in rufino["observado"] if ponto["competencia"] == "202306")["marca"] == "pico_que_volta"
    m2, padrao = rufino["cenarios"]
    assert "PICO_FORA_DO_AJUSTE" in [item["codigo"] for item in m2["avisos"]] and m2["parametros"]["janela"]["registros"] == 6
    assert next(a["texto"] for a in m2["avisos"] if a["codigo"] == "DIFERENCA_PARA_O_ULTIMO_REGISTRO").startswith(
        "A tendência ajustada dá 5,7 em jun/2024, e o registro é 5 (+0,7)")
    assert m2["final"]["total"] < 20 and padrao["metodo"]["usado"] == "M0d" and padrao["parametros"]["n0"] == real.quantidade[real.indice["421505"], -1]
    assert m2["faixa"]["estado"] == "indisponivel" and m2["metodo"]["e_o_escolhido"] is False   # a faixa é só do jeito escolhido
    # Com 5 médicos (de 4 a 9), a faixa do padrão em 2 anos está conferida com o que veio depois: o ponto é "validado".
    assert (padrao["faixa"]["porte"], padrao["faixa"]["como"], padrao["faixa"]["conferencia"], padrao["final"]["faixa"]["validada"]) == (
        "4 a 9", "propria", "conferida", True)
    assert rufino["historico"]["registros"] == 6
    # Estado como unidade: o padrão é o jeito escolhido pela retroprojeção dos estados (a taxa composta), sem aviso do nível; a
    # faixa de 8 em 10 fica indisponível, com os casos que a base tem. E o limite de territórios.
    estado = corpo(pedir({"estados_unidade": ["35"], "horizonte": "202806"}))["territorios"][0]
    assert estado["rotulo"] == "São Paulo (SP)" and estado["cenarios"][0]["metodo"] == jeito("padrao", "M1", "M1")
    assert [item["codigo"] for item in estado["cenarios"][0]["avisos"]] == ["HORIZONTE_EXTRAPOLACAO"]
    assert estado["cenarios"][0]["faixa"] == {"estado": "indisponivel", "motivo": poucos_casos(189), "rotulo": None, "em_10": 8}
    assert estado["cenarios"][0]["horizonte"]["aviso"] == "extrapolacao"
    recusa(pedir({"base": {"municipios": {"todos": True}}}), "O Simulador compara até 100 territórios de cada vez (a seleção tem 5570)")


def test_real_brasil_referencias_e_planejamento_inverso(real):
    # O Brasil como território: a contagem nacional (502.495 médicos em jun/2024), com o jeito escolhido para os estados (a taxa
    # composta), como provisório, e sem faixa.
    resposta = corpo(pedir({"brasil": True}))
    brasil = resposta["territorios"][0]
    cenario = brasil["cenarios"][0]
    assert (brasil["id"], brasil["unidade"], cenario["parametros"]["n0"]) == ("br", series_brasil.UNIDADE_BRASIL, 502495.0)
    assert cenario["metodo"] == jeito("padrao", "M1", "M1", provisorio=True)
    assert cenario["parametros"]["taxa_pct"] == pytest.approx(5.9001, abs=1e-4) and cenario["final"]["total"] == pytest.approx(563539.32, abs=0.01)
    assert cenario["faixa"] == SEM_FAIXA_DO_BRASIL and cenario["final"]["faixa"] is None
    assert [item["codigo"] for item in cenario["avisos"]] == ["PADRAO_PROVISORIO_DO_NIVEL", "HORIZONTE_CAUTELA"]
    assert cenario["avisos"][0]["texto"] == PROVISORIO_DO_BRASIL
    assert "sem intervenção, Brasil teria 563.539 médicos em jun/2026." in cenario["texto"]
    # A resposta traz a escolha de cada nível, com a frase, e as faixas: 40 nos municípios (dez portes, quatro prazos) e, nos
    # estados, só as indisponíveis dos portes que têm casos.
    retro = resposta["retroprojecao"]
    assert retro["escolha"]["texto"] == ("Para os municípios, a base escolheu a persistência com o crescimento recente do estado: na retroprojeção, "
                                         "ela errou 29% menos que manter o último valor, e menos em 22 de 22 combinações de origem e prazo.")
    assert retro["niveis"]["estados"]["escolha"]["texto"] == (
        "Para os estados como unidade, a base escolheu a taxa composta da janela: na retroprojeção, ela errou 60% menos que manter o último "
        "valor, e menos em 22 de 22 combinações de origem e prazo.")
    assert len(retro["faixas"]) == 40 and {faixa["estado"] for faixa in retro["faixas"]} == {"conferida", "provisoria"}
    assert {faixa["rotulo"] for faixa in retro["faixas"]} == {
        "conferida com o que veio depois", "conferida com o que veio depois (com os portes vizinhos)", "provisória",
        "provisória (com os portes vizinhos)", "provisória (com portes menores)"}
    assert len(retro["niveis"]["estados"]["faixas"]) == 16 and all(
        faixa["estado"] == "indisponivel" and faixa["inferior_pct"] is None for faixa in retro["niveis"]["estados"]["faixas"])
    # Manaus diante de Florianópolis (dinâmica), do Brasil e de São Paulo (fixas) e de um valor informado, até jun/2028, com o
    # planejamento inverso: a meta hipotética de alcançar Florianópolis, com um acréscimo por ano.
    body = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "horizonte": "202806", "cenarios": [
        {"id": "c1", "metodo": "padrao", "planejamento": {"meta": {"tipo": "referencia", "referencia": "floripa"}, "em": "202506",
                                                        "ate": "202806", "a_cada_meses": 12}}],
        "referencias": [{"id": "floripa", "territorio": "code:420540", "tipo": "dinamica"}, {"id": "br", "territorio": "br"},
                        {"id": "sp", "territorio": "uf:35"}, {"id": "v", "tipo": "valor", "valor": 6500}]}))
    manaus = body["territorios"][0]["cenarios"][0]
    assert manaus["metodo"] == jeito("padrao", "M0d", "M0d")
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
    # Com 6.018 médicos no cenário, a escala estrutural não dá sinal, nem nos limites da faixa de 8 em 10 — a de 4 anos, do porte
    # de 3.000 a 9.999 médicos (com os portes vizinhos), provisória: em 4 anos, ainda não dá para conferir nesta base.
    assert manaus["hipotetico"]["classe"] is None and manaus["hipotetico"]["na_faixa"] == {"inferior": None, "superior": None}
    assert manaus["final"]["faixa"]["anos"] == 4 and manaus["final"]["faixa"]["validada"] is False
    assert (manaus["faixa"]["porte"], manaus["final"]["faixa"]["estado"], manaus["final"]["faixa"]["como"]) == ("3.000 a 9.999", "provisoria", "vizinhas")
    assert [item["codigo"] for item in manaus["avisos"]] == ["HORIZONTE_EXTRAPOLACAO", "FAIXA_PROVISORIA"]
    # Por taxa, com a população de jun/2024 em todas as datas simuladas: Manaus (2,34 por 1.000) diante do Brasil (2,36).
    taxa = corpo(pedir({"base": {"municipios": {"ids": ["code:130260"]}}, "horizonte": "202606", "comparacao": {"metrica": "taxa"},
                        "referencias": [{"id": "br", "territorio": "br"}]}))
    do_brasil = taxa["territorios"][0]["cenarios"][0]["comparacoes"][0]
    assert do_brasil["final"]["territorio"] == pytest.approx(2.3404, abs=1e-4) and do_brasil["final"]["referencia"] == pytest.approx(2.3638, abs=1e-4)
    assert do_brasil["texto"].startswith("Em jun/2026, MANAUS (AM) teria 2,34 médicos por 1.000 habitantes, e a referência Brasil (fixa: o valor de "
                                         "jun/2024 mantido), 2,36: 0,02 abaixo da referência (índice 99; 100 é a referência).")
    assert do_brasil["texto"].endswith("Hipótese: população constante, a de jun/2024.")
    # "Simular recuperação": Abreulândia (TO), abaixo do patamar anterior (1,75 médico), teria 1 médico no cenário; a meta é o
    # patamar arredondado para cima (2 médicos, com a origem no rótulo); a conta condicional dá 1 médico em jun/2025, e a hipótese
    # derivada da simulação mostra a dependência de poucos médicos.
    abreulandia = corpo(pedir({"base": {"municipios": {"ids": ["code:170025"]}}, "cenarios": [
        {"id": "c1", "metodo": "padrao", "planejamento": {"meta": {"tipo": "patamar"}, "em": "202506"}}]}))["territorios"][0]["cenarios"][0]
    recuperacao = abreulandia["planejamento"]
    assert recuperacao["meta"] == {
        "tipo": "patamar", "valor": 2.0, "patamar": 1.75, "registros": 4, "arredondado": True,
        "rotulo": "Meta hipotética: voltar ao patamar de 2 médicos em jun/2026 (patamar de 1,75, média de 4 registros, arredondado para cima)"}
    assert (recuperacao["por_evento"], recuperacao["eventos"]) == (1, 1) and recuperacao["teorico_por_evento"] == pytest.approx(0.8138, abs=1e-4)
    assert "ABREULANDIA (TO) teria 2 médicos em jun/2026." in recuperacao["texto"]
    # O caminho do cenário com o acréscimo, para o gráfico: o total e o acréscimo acumulado em cada data; a última é a da meta.
    assert [(ponto["data"], ponto["intervencao"]) for ponto in recuperacao["trajetoria"]] == [
        ("202501", 0.0), ("202506", 1.0), ("202601", 1.0), ("202606", 1.0)]
    assert recuperacao["trajetoria"][-1]["total"] == pytest.approx(recuperacao["resultado"]) == pytest.approx(2.1862, abs=1e-4)
    assert recuperacao["trajetoria"][-1]["total"] >= recuperacao["meta"]["valor"]
    assert abreulandia["hipotetico"] == {"rotulo": "hipótese do cenário", "data": "202606", "valor": pytest.approx(1.1862, abs=1e-4),
                                         "inteiro": 1, "classe": "critico", "impacto_pct": 100.0, "na_faixa": {"inferior": "critico", "superior": "elevado"}}
    # Com 1 médico (de 1 a 3), a faixa de 8 em 10 de 2 anos está conferida com o que veio depois; e o texto usa o singular.
    assert (abreulandia["faixa"]["porte"], abreulandia["faixa"]["conferencia"], abreulandia["final"]["faixa"]["validada"]) == ("1 a 3", "conferida", True)
    assert abreulandia["entenda"]["jeito"]["exemplo"] == "De 1 médico em jun/2024, a base do cenário vai a 1,1 um ano depois, sem contar intervenções."
    # A de 5 em 10, nesse porte, não passou na conferência de 1 ano (cobriu 29%, para uma meta de 50%): sem o 1.º ano, o cenário
    # não tem faixa, mesmo havendo a de 3 e a de 4 anos na retroprojeção (a faixa não aparece com "buracos"); o motivo é o do 1.º ano.
    estreita = corpo(pedir({"base": {"municipios": {"ids": ["code:170025"]}}, "faixa": 5, "horizonte": "202806"}))["territorios"][0]["cenarios"][0]
    assert [simulador.retroprojetar(real).faixas[(5, 0, anos)]["estado"] for anos in (1, 2, 3, 4)] == ["indisponivel", "indisponivel", "provisoria", "provisoria"]
    assert estreita["faixa"] == {"estado": "indisponivel", "rotulo": None, "em_10": 5, "motivo":
                                 "Conferida com o que veio depois, a faixa de 5 em cada 10 cobriu 29% dos casos em 1 ano, para uma meta de 50%: a base não a sustenta."}
    assert all(ponto["faixa"] is None for ponto in estreita["trajetoria"]) and "na_faixa" not in estreita["hipotetico"]
    assert [item["codigo"] for item in estreita["avisos"]] == ["HORIZONTE_EXTRAPOLACAO"]
