"""A régua comum do Detector de Sinais e do Simulador de Cenários (Proposta V3, Parte A; Docs/DETECTOR_E_SIMULADOR_V3.md).

As duas ferramentas aprendem com a própria base, olhando para territórios de tamanho parecido e só para o que veio antes de cada
data. Este módulo guarda o que elas têm em comum e não sabe nada da base do Brasil:

- **portes** (A.2.2): dez faixas pelo número de profissionais — 1–3, 4–9, 10–19, 20–49, 50–99, 100–299, 300–999, 1.000–2.999,
  3.000–9.999 e 10.000 ou mais;
- **raridade** (B.1): (mudanças anteriores iguais ou piores + 1) ÷ (total de mudanças anteriores + 1), só com as mudanças
  anteriores à data avaliada, do mesmo porte e do mesmo tipo de comparação (o tempo entre registros), contando os empates;
- **níveis** (B.1): moderado (1 em cada 20, com pelo menos 19 comparações), elevado (1 em cada 100, com 99) e crítico (1 em cada
  1.000, com 999);
- **retaguarda** (A.2.4): quando faltam comparações, a faixa de porte junta-se às vizinhas, uma de cada lado; se ainda faltar, só
  o moderado junta todas as faixas, com a mudança padronizada pelo tamanho (mudança ÷ tamanho^(θ/2), com θ estimado só com o
  passado). Se nada bastar, o nível fica "sem comparações suficientes", com quantas há e quantas ele pede.

Nada aqui lê arquivos nem vai ao provedor de IA: são contas sobre vetores.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

PORTES = ((1, 3), (4, 9), (10, 19), (20, 49), (50, 99), (100, 299), (300, 999), (1000, 2999), (3000, 9999), (10000, None))
ROTULOS_DOS_PORTES = ("1 a 3", "4 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 a 999", "1.000 a 2.999", "3.000 a 9.999",
                      "10.000 ou mais")
# Os níveis de alerta, do mais grave ao menos grave: (chave, 1 em cada N, comparações anteriores necessárias).
NIVEIS = (("critico", 1000, 999), ("elevado", 100, 99), ("moderado", 20, 19))
GRAVIDADE = {None: 0, "moderado": 1, "elevado": 2, "critico": 3}
NOMES_DOS_NIVEIS = {"moderado": "Moderado", "elevado": "Elevado", "critico": "Crítico"}
ORIGENS = ("porte", "vizinhas", "todas")          # de onde vieram as comparações de um nível
MINIMO_PARA_THETA = 30                            # mudanças anteriores numa faixa para ela entrar na estimativa de θ
THETA_PADRAO = 1.0                                # sem passado bastante: a variância cresce com o tamanho (contagem)
EPS = 1e-12


def porte_de(valor) -> int | None:
    """O índice da faixa de porte (PORTES) de uma contagem; None para zero, ausente ou abaixo de 1."""
    if valor is None or valor != valor or valor < 1:
        return None
    for indice, (minimo, maximo) in enumerate(PORTES):
        if valor >= minimo and (maximo is None or valor <= maximo):
            return indice
    return None


def portes(valores: np.ndarray) -> np.ndarray:
    """A faixa de porte de cada valor (−1 para zero, ausente ou abaixo de 1)."""
    saida = np.full(np.shape(valores), -1, dtype=np.int8)
    with np.errstate(invalid="ignore"):
        for indice, (minimo, maximo) in enumerate(PORTES):
            dentro = (valores >= minimo) & ((valores <= maximo) if maximo is not None else True)
            saida[dentro] = indice
    return saida


def raridade(iguais_ou_piores, total):
    """(k + 1) ÷ (n + 1): a própria mudança entra na conta, o que evita dizer "nunca aconteceu" com uma história curta."""
    return (np.asarray(iguais_ou_piores, dtype=float) + 1.0) / (np.asarray(total, dtype=float) + 1.0)


@dataclass(frozen=True)
class Comparacoes:
    """Para cada avaliação, quantas mudanças anteriores havia (n) e quantas eram iguais ou piores (k), em cada origem: a própria
    faixa de porte, a faixa com as vizinhas e todas as faixas com a mudança padronizada pelo tamanho. −1 em n: não se aplica."""
    k_porte: np.ndarray
    n_porte: np.ndarray
    k_vizinhas: np.ndarray
    n_vizinhas: np.ndarray
    k_todas: np.ndarray
    n_todas: np.ndarray
    theta: np.ndarray        # o θ usado na padronização, por data (NaN sem avaliação)


def theta_do_passado(delta: np.ndarray, tamanho: np.ndarray, porte: np.ndarray) -> float:
    """θ da relação entre o tamanho e a dispersão robusta da mudança (MAD), com as mudanças dadas (as do passado): a dispersão
    cresce com tamanho^(θ/2). Regressão de log(MAD) em log(tamanho mediano), nas faixas com pelo menos 30 mudanças. Sem duas
    faixas assim, θ = 1."""
    xs, ys = [], []
    for faixa in range(len(PORTES)):
        dentro = porte == faixa
        if int(dentro.sum()) < MINIMO_PARA_THETA:
            continue
        valores = delta[dentro]
        mad = float(np.median(np.abs(valores - np.median(valores))))
        if mad <= 0:
            continue
        xs.append(np.log(float(np.median(tamanho[dentro]))))
        ys.append(np.log(mad))
    if len(xs) < 2 or max(xs) - min(xs) < EPS:
        return THETA_PADRAO
    inclinacao = float(np.polyfit(np.array(xs), np.array(ys), 1)[0])
    return float(min(max(2.0 * inclinacao, 0.0), 2.0))


def comparar_com_o_passado(valor, delta, tamanho, porte, valor_passado, delta_passado, tamanho_passado, porte_passado,
                           pior_e_menor: bool = True) -> tuple:
    """As comparações de um grupo de avaliações da mesma data com o passado dado (já filtrado por quem chama: o mesmo tipo de
    comparação, só datas anteriores e sem o que não deve entrar). Devolve (k_porte, n_porte, k_vizinhas, n_vizinhas, k_todas,
    n_todas, θ): em cada origem, quantas mudanças anteriores havia (n) e quantas eram iguais ou piores (k).

    - `valor`: a medida comparada dentro da faixa de porte e com as vizinhas (por exemplo, a variação relativa);
    - `delta` e `tamanho`: a mudança absoluta e o tamanho, para a comparação entre todas as faixas (delta ÷ tamanho^(θ/2), com θ
      estimado só com o passado dado);
    - `pior_e_menor`: a queda é o lado ruim (o padrão); falso quando o maior valor é o pior (afastamento, oscilação)."""
    sinal = 1.0 if pior_e_menor else -1.0
    v, vp = sinal * np.asarray(valor, dtype=float), sinal * np.asarray(valor_passado, dtype=float)
    d, dp = sinal * np.asarray(delta, dtype=float), sinal * np.asarray(delta_passado, dtype=float)
    s, sp = np.asarray(tamanho, dtype=float), np.asarray(tamanho_passado, dtype=float)
    f, fp = np.asarray(porte, dtype=np.int64), np.asarray(porte_passado, dtype=np.int64)
    k_porte, n_porte = np.zeros(v.shape, dtype=np.int64), np.zeros(v.shape, dtype=np.int64)
    k_viz, n_viz = np.zeros(v.shape, dtype=np.int64), np.zeros(v.shape, dtype=np.int64)
    k_todas, n_todas = np.zeros(v.shape, dtype=np.int64), np.zeros(v.shape, dtype=np.int64)
    if not vp.size:
        return k_porte, n_porte, k_viz, n_viz, k_todas, n_todas, float("nan")
    for faixa in np.unique(f):
        atuais = f == faixa
        da_faixa = np.sort(vp[fp == faixa])
        k_porte[atuais], n_porte[atuais] = np.searchsorted(da_faixa, v[atuais] + EPS, side="right"), da_faixa.size
        com_vizinhas = np.sort(vp[(fp >= faixa - 1) & (fp <= faixa + 1)])
        k_viz[atuais], n_viz[atuais] = np.searchsorted(com_vizinhas, v[atuais] + EPS, side="right"), com_vizinhas.size
    theta = theta_do_passado(dp, sp, fp)
    ordenados = np.sort(dp / np.power(np.maximum(sp, 1.0), theta / 2.0))
    k_todas[:] = np.searchsorted(ordenados, d / np.power(np.maximum(s, 1.0), theta / 2.0) + EPS, side="right")
    n_todas[:] = ordenados.size
    return k_porte, n_porte, k_viz, n_viz, k_todas, n_todas, theta


def comparar(valor: np.ndarray, delta: np.ndarray, tamanho: np.ndarray, porte: np.ndarray, tempo: np.ndarray, tipo: np.ndarray,
             pior_e_menor: bool = True, usavel=None) -> Comparacoes:
    """As comparações de cada avaliação (vetores de mesmo tamanho, só com avaliações válidas: porte ≥ 0), cada uma só com as
    avaliações de datas anteriores e do mesmo tipo de comparação (o tempo entre registros), nunca misturados.

    `tempo` é o índice da data avaliada. `usavel(data)`, quando dado, devolve a máscara das avaliações que podem entrar no
    passado daquela data (o Detector tira as descontinuidades de registro já conhecidas nela)."""
    valor, delta, tamanho = np.asarray(valor, dtype=float), np.asarray(delta, dtype=float), np.asarray(tamanho, dtype=float)
    porte, tempo, tipo = np.asarray(porte, dtype=np.int64), np.asarray(tempo, dtype=np.int64), np.asarray(tipo, dtype=np.int64)
    campos = [np.zeros(valor.shape, dtype=np.int64) for _ in range(6)]
    datas = np.unique(tempo)
    thetas = np.full(int(datas.max()) + 1 if datas.size else 0, np.nan)
    for data in datas:
        pode = (tempo < data) if usavel is None else ((tempo < data) & usavel(int(data)))
        for qual in np.unique(tipo[tempo == data]):
            agora, antes = (tempo == data) & (tipo == qual), pode & (tipo == qual)
            saida = comparar_com_o_passado(valor[agora], delta[agora], tamanho[agora], porte[agora], valor[antes], delta[antes],
                                           tamanho[antes], porte[antes], pior_e_menor)
            for campo, resultado in zip(campos, saida[:6]):
                campo[agora] = resultado
            if saida[6] == saida[6]:
                thetas[int(data)] = saida[6]
    return Comparacoes(k_porte=campos[0], n_porte=campos[1], k_vizinhas=campos[2], n_vizinhas=campos[3], k_todas=campos[4],
                       n_todas=campos[5], theta=thetas)


def nivel_da_raridade(k_porte: int, n_porte: int, k_vizinhas: int, n_vizinhas: int, k_todas: int, n_todas: int,
                      limites: dict | None = None) -> dict:
    """O nível que a raridade sustenta numa avaliação, do mais grave ao menos grave. Para cada nível, vale a primeira origem com
    comparações bastantes: a faixa de porte, depois a faixa com as vizinhas e, só no moderado, todas as faixas. Devolve o nível
    (ou None), a raridade e a origem usadas, e, para cada nível, se foi avaliado ou quantas comparações faltaram.

    `limites` troca o "1 em cada N" de cada nível ({"moderado": 20, ...}); os mínimos de comparações acompanham (N − 1)."""
    saida = {"nivel": None, "raridade": None, "origem": None, "comparacoes": None, "niveis": {}}
    for chave, um_em, minimo in NIVEIS:
        if limites and chave in limites:
            um_em = float(limites[chave])
            minimo = max(int(np.ceil(um_em)) - 1, 1)
        origens = [("porte", k_porte, n_porte), ("vizinhas", k_vizinhas, n_vizinhas)]
        if chave == "moderado":
            origens.append(("todas", k_todas, n_todas))
        usada = next(((nome, k, n) for nome, k, n in origens if n >= minimo), None)
        if usada is None:
            maior = max(n for _, _, n in origens)
            saida["niveis"][chave] = {"avaliado": False, "comparacoes": int(maior), "pede": int(minimo), "um_em": um_em}
            continue
        nome, k, n = usada
        valor = float(raridade(k, n))
        atingido = valor <= 1.0 / um_em + EPS
        saida["niveis"][chave] = {"avaliado": True, "comparacoes": int(n), "pede": int(minimo), "um_em": um_em, "origem": nome,
                                  "raridade": valor, "atingido": bool(atingido)}
        if atingido and saida["nivel"] is None:
            saida.update(nivel=chave, raridade=valor, origem=nome, comparacoes=int(n))
    if saida["nivel"] is None:
        # Sem nível: a raridade e as comparações do nível menos grave que pôde ser avaliado, para a tela dizer com quem comparou.
        for chave, _, _ in reversed(NIVEIS):
            dados = saida["niveis"][chave]
            if dados["avaliado"]:
                saida.update(raridade=dados["raridade"], origem=dados["origem"], comparacoes=dados["comparacoes"])
                break
    return saida


def sem_comparacoes(lida: dict) -> dict | None:
    """De uma leitura de `nivel_da_raridade`: os níveis que a base ainda não sustenta, com quantas comparações há e quantas o
    menos grave deles pede ("são 54 comparações, e o elevado pede 99"). None quando todos os níveis puderam ser avaliados."""
    faltam = [(nivel, dados) for nivel, dados in lida["niveis"].items() if not dados["avaliado"]]
    if not faltam:
        return None
    faltam.sort(key=lambda par: GRAVIDADE[par[0]])
    return {"niveis": [nivel for nivel, _ in faltam], "nivel": faltam[0][0], "comparacoes": faltam[0][1]["comparacoes"],
            "pede": faltam[0][1]["pede"]}


def niveis_em_vetor(c: Comparacoes, limites: dict | None = None) -> np.ndarray:
    """O nível de cada avaliação (0 sem nível, 1 moderado, 2 elevado, 3 crítico) e, em −1, as avaliações em que nem o moderado
    pôde ser avaliado. Versão vetorial de `nivel_da_raridade`, para a calibração."""
    saida = np.zeros(c.n_porte.shape, dtype=np.int8)
    algum = np.zeros(c.n_porte.shape, dtype=bool)
    for chave, um_em, minimo in reversed(NIVEIS):       # do moderado ao crítico: o mais grave fica por último
        if limites and chave in limites:
            um_em = float(limites[chave])
            minimo = max(int(np.ceil(um_em)) - 1, 1)
        k = np.where(c.n_porte >= minimo, c.k_porte, c.k_vizinhas)
        n = np.where(c.n_porte >= minimo, c.n_porte, c.n_vizinhas)
        if chave == "moderado":
            k = np.where(n >= minimo, k, c.k_todas)
            n = np.where(n >= minimo, n, c.n_todas)
        avaliado = n >= minimo
        algum |= avaliado
        atingido = avaliado & (raridade(k, n) <= 1.0 / um_em + EPS)
        saida[atingido] = GRAVIDADE[chave]
    saida[~algum] = -1
    return saida
