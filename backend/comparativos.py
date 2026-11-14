"""Sinais 8 a 12 do Detector de Sinais Territoriais (comando V23, Proposta V3, tabela B.2): menos profissionais por habitante,
perda de posição, mais longe da referência, distância e sinais juntos. Referência metodológica: Docs/DETECTOR_E_SIMULADOR_V3.md
(Partes A e B); as definições operacionais da V2.2 (Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 4.1 e 4.2) continuam valendo no
que a V3 não muda.

O que este módulo calcula (os textos ficam em detector.py):

- **8, menos profissionais por habitante:** a taxa por 1.000 habitantes e a variação dela numa janela de 2 anos na série anual,
  com a decomposição (profissionais, população e taxa).
- **9, perda de posição:** o percentil do território pela taxa, (posto médio − 0,5) ÷ n, num universo fixo na janela (os
  municípios com taxa válida nas duas datas; para estados como unidade, os estados), e a variação em pontos.
- **10, mais longe da referência:** o índice 100 × taxa do território ÷ taxa da referência, com a referência no grupo de cima,
  na mesma unidade do território e sem ele, e a variação em pontos.
- **11, distância:** a distância geodésica até o território mais próximo com taxa igual ou maior que o critério (padrão: a taxa
  da base toda na data; ajustável de 10% a 500% dela), com a posição dessa distância entre os que não atendem ao critério. Só
  contexto: nunca vira alerta nem juízo assistencial.
- **12, sinais juntos:** quais sinais coincidem no território, sem soma e sem índice; os efeitos de uma mesma queda contam como
  um evento, não como evidências independentes.

**Os níveis dos sinais 8 a 10 (comparado com a base):** a variação em 2 anos é comparada com as variações anteriores de territórios
do mesmo porte (o número de profissionais no início da janela): moderado, 1 em cada 20; elevado, 1 em cada 100; crítico, 1 em
cada 1.000, com os mínimos de comparações da régua comum (reguas.py) e "sem comparações suficientes" quando a base não os tem.
Abaixo de 20 profissionais no início da janela, os sinais são descritivos.

**População comparável (seção A.3 da V3):** a variação dos sinais 8, 9 e 10 só é calculada em janelas inteiras dentro de um
trecho de população comparável. Os trechos vêm da própria base (`populacao_comparavel`), que é olhada inteira em cada passagem de
ano: quando a população se repete em boa parte dela, ou salta em boa parte dela, e isso foge do que é comum nas outras passagens,
o trecho termina ali. Uma janela que cruze esse limite fica com o estado "comparacao_nao_habilitada", com o valor da data (taxa,
percentil, índice) ainda à vista. Alguns territórios com o valor do ano anterior, ou com um salto, são normais e não desligam a
comparação. Para o sinal 10, a mesma regra é uma decisão conservadora desta implementação: o índice usa as duas populações, e a
troca de série mudaria o índice sem mudança real.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np

import nearest_reference
import reguas
from series_brasil import Base, Territorio
from territorial_levels import STATES, state_with_preposition

POR = 1000.0                                 # a taxa do Agente: médicos por 1.000 habitantes
ANOS_DA_JANELA = 2
# População comparável: a base inteira, em cada passagem de ano (de junho a junho).
PARTE_REPETIDA = 0.5                         # metade ou mais da base com a população do ano anterior: população repetida
SALTO_PCT = 5.0                              # a variação de um ano para o outro que conta como salto de um território
PARTE_COM_SALTO = 0.05                       # a parte da base com salto que termina um trecho...
VEZES_O_COMUM = 3.0                          # ...se também for 3 vezes o que é comum nas outras passagens da mesma base
MINIMO_COM_SALTO = 3                         # e houver pelo menos 3 territórios com salto
MINIMO_DE_MEDICOS = 20                       # abaixo disso, no início da janela, os indicadores 8 a 10 são descritivos
CRS = "SIRGAS2000"
EPS = 1e-9                                   # tolerância das comparações com os limites (o caso exato no limite conta)

# Sinais 8, 9 e 10 (Proposta V3, tabela B.2): a raridade da variação em 2 anos na própria base — 1 em cada 20 (moderado), 1 em
# cada 100 (elevado) e 1 em cada 1.000 (crítico) —, e o critério do sinal 11 (X% da taxa da base toda).
UM_EM = {"moderado_um_em": 20, "elevado_um_em": 100, "critico_um_em": 1000}
PADRAO = {
    "disponibilidade": dict(UM_EM),
    "posicao": dict(UM_EM),
    "defasagem": dict(UM_EM),
    "contexto": {"taxa_do_brasil_pct": 100.0},
}
COMPARADO = "comparado com a base"
_UM_EM = (2, 100000, True)
EDITAVEIS = {
    "disponibilidade": {chave: _UM_EM for chave in UM_EM},
    "posicao": {chave: _UM_EM for chave in UM_EM},
    "defasagem": {chave: _UM_EM for chave in UM_EM},
    "contexto": {"taxa_do_brasil_pct": (10.0, 500.0, False)},
}


def conferir(em_uso: dict) -> None:
    """A ordem dos limites dos sinais 8 a 10 é conferida com os demais, em detector.parametros (moderado ≤ elevado ≤ crítico)."""


# --------------------------------------------------------------------------------------------- população comparável
_COMPARAVEL: dict[str, dict] = {}
_TRAVA_DO_COMPARAVEL = threading.Lock()


def populacao_comparavel(base: Base) -> dict:
    """Os trechos de população comparável da base, lidos dela mesma (perfil da base, seção A.3 da V3). Em cada passagem de ano
    (de um junho ao seguinte), a base inteira é olhada: a parte dos territórios com a mesma população do ano anterior e a parte
    com variação acima de 5%. A passagem termina um trecho quando a população é **repetida** (metade da base ou mais repete o
    valor, e isso não é o comum nas outras passagens) ou **salta** (5% da base ou mais, pelo menos 3 territórios e 3 vezes o
    comum nas outras passagens). Uma base com a população constante em todos os anos é um trecho só: a taxa varia só com a
    contagem. Devolve os anos, as passagens medidas, as quebras (ano → motivo) e os trechos (início, fim)."""
    with _TRAVA_DO_COMPARAVEL:
        guardado = _COMPARAVEL.get(base.versao)
    if guardado is not None:
        return guardado
    junhos = {int(periodo[:4]): posicao for posicao, periodo in enumerate(base.periodos) if periodo.endswith("06")}
    anos = sorted(junhos)
    passagens = []
    for a, b in zip(anos, anos[1:]):
        antes, depois = base.populacao[:, junhos[a]], base.populacao[:, junhos[b]]
        with np.errstate(invalid="ignore"):
            validos = ~np.isnan(antes) & ~np.isnan(depois) & (antes > 0) & (depois > 0)
        n = int(validos.sum())
        if not n:
            passagens.append({"de": a, "ate": b, "territorios": 0, "repetidos": None, "saltos": None})
            continue
        variacao = np.abs(depois[validos] / antes[validos] - 1.0) * 100.0
        passagens.append({"de": a, "ate": b, "territorios": n, "repetidos": float((depois[validos] == antes[validos]).mean()),
                          "saltos": float((variacao > SALTO_PCT).mean())})
    quebras: dict[int, str] = {}
    for k, passagem in enumerate(passagens):
        if not passagem["territorios"]:
            quebras[passagem["ate"]] = "sem_populacao"
            continue
        outras = [outra for j, outra in enumerate(passagens) if j != k and outra["territorios"]]
        comum_repetido = float(np.median([outra["repetidos"] for outra in outras])) if outras else passagem["repetidos"]
        comum_salto = float(np.median([outra["saltos"] for outra in outras])) if outras else passagem["saltos"]
        if passagem["repetidos"] >= PARTE_REPETIDA and comum_repetido < PARTE_REPETIDA:
            quebras[passagem["ate"]] = "repetida"
        elif passagem["saltos"] >= max(PARTE_COM_SALTO, VEZES_O_COMUM * comum_salto) and \
                round(passagem["saltos"] * passagem["territorios"]) >= MINIMO_COM_SALTO:
            quebras[passagem["ate"]] = "salto"
    trechos: list[tuple[int, int]] = []
    for ano in anos:
        if not trechos or ano in quebras:
            trechos.append((ano, ano))
        else:
            trechos[-1] = (trechos[-1][0], ano)
    saida = {"anos": tuple(anos), "passagens": tuple(passagens), "quebras": quebras, "trechos": tuple(trechos)}
    with _TRAVA_DO_COMPARAVEL:
        if len(_COMPARAVEL) > 8:
            _COMPARAVEL.clear()
        _COMPARAVEL[base.versao] = saida
    return saida


def trechos_comparaveis(base: Base) -> list[list[int]]:
    """Os trechos em que cabe uma janela de comparação inteira (2 anos): [[2014, 2024]]."""
    return [[a, b] for a, b in populacao_comparavel(base)["trechos"] if b - a >= ANOS_DA_JANELA]


def _anos(anos: list[int]) -> str:
    textos = [str(ano) for ano in anos]
    return textos[0] if len(textos) == 1 else ", ".join(textos[:-1]) + " e " + textos[-1]


def texto_dos_trechos(base: Base) -> str:
    """"2014–2024", "2014–2017 e 2018–2021" ou, sem um trecho de 2 anos, "nenhum trecho nesta base"."""
    trechos = [str(a) + "–" + str(b) for a, b in trechos_comparaveis(base)]
    return "nenhum trecho nesta base" if not trechos else trechos[0] if len(trechos) == 1 else ", ".join(trechos[:-1]) + " e " + trechos[-1]


def motivo_da_janela(base: Base, ini: int | None, fim: int | None) -> str | None:
    """Por que a janela não tem população comparável, com os anos: "a população de 2022 e 2023 repete a do ano anterior em boa
    parte da base, e a de 2024 muda de patamar em boa parte da base"."""
    if ini is None or fim is None:
        return None
    primeiro, ultimo = int(base.periodos[ini][:4]), int(base.periodos[fim][:4])
    quebras = {ano: motivo for ano, motivo in populacao_comparavel(base)["quebras"].items() if primeiro < ano <= ultimo}
    if not quebras:
        return None
    partes = []
    for motivo, frase in (("repetida", " repete a do ano anterior em boa parte da base"), ("salto", " muda de patamar em boa parte da base"),
                          ("sem_populacao", " não tem como ser comparada com a do ano anterior")):
        anos = sorted(ano for ano, qual in quebras.items() if qual == motivo)
        if anos:
            partes.append("a população de " + _anos(anos) + frase)
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + ", e " + partes[-1]


# --------------------------------------------------------------------------------------------- janela de comparação
def janela(base: Base, e: int) -> tuple[int | None, int | None, str | None]:
    """Os dois junhos da janela de comparação (2 anos, de junho a junho) que termina no último junho até a data avaliada, e o
    motivo quando a variação não pode ser calculada: "janela_insuficiente" (falta um dos junhos) ou "comparacao_nao_habilitada"
    (a janela não cabe inteira num trecho de população comparável da base)."""
    junhos = [i for i in range(e + 1) if base.periodos[i].endswith("06")]
    if not junhos:
        return None, None, "janela_insuficiente"
    fim = junhos[-1]
    ano = int(base.periodos[fim][:4])
    alvo = str(ano - ANOS_DA_JANELA) + "06"
    if alvo not in base.periodos:
        return None, fim, "janela_insuficiente"
    ini = base.periodos.index(alvo)
    if any(ano - ANOS_DA_JANELA < quebra <= ano for quebra in populacao_comparavel(base)["quebras"]):
        return ini, fim, "comparacao_nao_habilitada"
    return ini, fim, None


def percentis(valores: np.ndarray) -> tuple[np.ndarray, int]:
    """O percentil de cada valor no universo dos valores válidos: (posto médio − 0,5) ÷ n × 100, com os empates no posto médio
    (seção 4.2). NaN fora do universo."""
    saida = np.full(valores.shape, np.nan)
    validos = ~np.isnan(valores)
    v = valores[validos]
    n = int(v.size)
    if not n:
        return saida, 0
    ordem = np.argsort(v, kind="mergesort")
    ordenados = v[ordem]
    inicio = np.r_[True, ordenados[1:] != ordenados[:-1]]
    primeiro = np.flatnonzero(inicio)
    ultimo = np.r_[primeiro[1:], n] - 1
    medio = (primeiro + ultimo) / 2.0 + 1.0
    postos = np.empty(n)
    postos[ordem] = medio[np.cumsum(inicio) - 1]
    saida[validos] = 100.0 * (postos - 0.5) / n
    return saida, n


# --------------------------------------------------------------------------------------------- quadro de uma data
@dataclass(frozen=True)
class Quadro:
    """O que os fenômenos 8 a 11 usam, calculado uma vez por versão da base, data avaliada e critério do contexto."""
    e: int
    ini: int | None
    fim: int | None
    motivo: str | None
    anterior: tuple | None            # (ini, fim) da janela encerrada um ano antes, quando também é comparável
    taxa: np.ndarray                  # [município, competência], por 1.000 habitantes (NaN sem contagem ou sem população)
    taxa_da_referencia: np.ndarray    # [município, competência]: os demais municípios da UF (NaN sem outros municípios)
    percentil_na_data: np.ndarray
    universo_na_data: int
    percentil_ini: np.ndarray | None
    percentil_fim: np.ndarray | None
    universo: int
    percentil_ini_anterior: np.ndarray | None
    percentil_fim_anterior: np.ndarray | None
    taxa_do_brasil: float | None
    limiar: float | None
    atende: np.ndarray                # [município]: a taxa na data é igual ou maior que o critério
    com_coordenada: np.ndarray
    distancia_km: np.ndarray          # [município]: até o município mais próximo que atende (NaN para quem atende ou não tem ponto)
    referencia: np.ndarray            # [município]: a linha do município mais próximo que atende (−1 sem)
    percentil_da_distancia: np.ndarray
    universo_da_distancia: int


_QUADROS: dict[tuple, Quadro] = {}
_TAXAS: dict[str, tuple] = {}
_LOCK = threading.Lock()
_MAX_QUADROS = 12


def _taxas(base: Base, guardar: bool = True) -> tuple:
    """As taxas municipais e a taxa da referência de cada município (os demais municípios da UF), em todas as competências."""
    with _LOCK:
        guardadas = _TAXAS.get(base.versao) if guardar else None
    if guardadas is not None:
        return guardadas
    q, pop = base.quantidade, base.populacao
    valido = ~np.isnan(q) & ~np.isnan(pop) & (pop > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        taxa = np.where(valido, POR * q / pop, np.nan)
    referencia = np.full(q.shape, np.nan)
    for linhas in base.do_estado.values():
        linhas = list(linhas)
        qv, pv = np.where(valido[linhas], q[linhas], 0.0), np.where(valido[linhas], pop[linhas], 0.0)
        outros_q, outros_pop = qv.sum(axis=0)[None, :] - qv, pv.sum(axis=0)[None, :] - pv
        with np.errstate(invalid="ignore", divide="ignore"):
            referencia[linhas] = np.where(valido[linhas] & (outros_pop > 0), POR * outros_q / outros_pop, np.nan)
    for matriz in (taxa, referencia):
        matriz.setflags(write=False)
    if guardar:
        with _LOCK:
            _TAXAS.clear()
            _TAXAS[base.versao] = (taxa, referencia)
    return taxa, referencia


def taxa_do_brasil(base: Base, i: int) -> float | None:
    """A taxa do Brasil numa competência: a contagem nacional (médicos únicos) ÷ a soma das populações municipais com registro."""
    pop = float(np.nansum(base.populacao[:, i]))
    nacional = base.brasil[i]
    return float(POR * nacional / pop) if nacional == nacional and pop > 0 else None


def quadro(base: Base, e: int, p: dict, guardar: bool = True) -> Quadro:
    pct = float(p["contexto"]["taxa_do_brasil_pct"])
    chave = (base.versao, e, pct)
    with _LOCK:
        guardado = _QUADROS.get(chave) if guardar else None
    if guardado is not None:
        return guardado
    taxa, taxa_da_referencia = _taxas(base, guardar)
    ini, fim, motivo = janela(base, e)
    percentil_na_data, universo_na_data = percentis(taxa[:, e])

    def do_par(a: int, b: int):
        juntos = ~np.isnan(taxa[:, a]) & ~np.isnan(taxa[:, b])   # o universo fixo na janela
        pa, n = percentis(np.where(juntos, taxa[:, a], np.nan))
        pb, _ = percentis(np.where(juntos, taxa[:, b], np.nan))
        return pa, pb, n
    percentil_ini = percentil_fim = percentil_ini_anterior = percentil_fim_anterior = None
    universo, anterior = 0, None
    if motivo is None:
        percentil_ini, percentil_fim, universo = do_par(ini, fim)
        # A janela encerrada um ano antes, para a confirmação em duas avaliações anuais (só quando também é comparável).
        junhos = [i for i in range(fim) if base.periodos[i].endswith("06")]
        if junhos:
            ia, fa, motivo_anterior = janela(base, junhos[-1])
            if motivo_anterior is None:
                anterior = (ia, fa)
                percentil_ini_anterior, percentil_fim_anterior, _ = do_par(ia, fa)
    # Contexto geográfico: os municípios com taxa igual ou maior que o critério, na data, e a distância de cada um dos demais.
    do_brasil = taxa_do_brasil(base, e)
    limiar = None if do_brasil is None else do_brasil * pct / 100.0
    lat, lon = base.latitude[:, e], base.longitude[:, e]
    with np.errstate(invalid="ignore"):
        com_coordenada = np.isfinite(lat) & np.isfinite(lon) & (np.abs(lat) <= 90) & (np.abs(lon) <= 180)
        atende = np.zeros(len(base.codigos), dtype=bool) if limiar is None else (taxa[:, e] >= limiar - EPS)
    distancia = np.full(len(base.codigos), np.nan)
    referencia = np.full(len(base.codigos), -1, dtype=int)
    alvos = np.flatnonzero(com_coordenada & ~atende & ~np.isnan(taxa[:, e]))
    fontes = np.flatnonzero(com_coordenada & atende)
    if len(alvos) and len(fontes):
        metros, empates, _ = nearest_reference.nearest_exact(lat[alvos], lon[alvos], lat[fontes], lon[fontes], crs=CRS)
        distancia[alvos] = metros / 1000.0
        # Com empate exato, a referência de menor código (a ordem das linhas da base).
        referencia[alvos] = [int(fontes[min(candidatos)]) if candidatos else -1 for candidatos in empates]
    percentil_da_distancia, universo_da_distancia = percentis(distancia)
    for matriz in (percentil_na_data, percentil_da_distancia, distancia, referencia, atende, com_coordenada):
        matriz.setflags(write=False)
    saida = Quadro(e=e, ini=ini, fim=fim, motivo=motivo, anterior=anterior, taxa=taxa, taxa_da_referencia=taxa_da_referencia,
                   percentil_na_data=percentil_na_data, universo_na_data=universo_na_data, percentil_ini=percentil_ini,
                   percentil_fim=percentil_fim, universo=universo, percentil_ini_anterior=percentil_ini_anterior,
                   percentil_fim_anterior=percentil_fim_anterior, taxa_do_brasil=do_brasil, limiar=limiar, atende=atende,
                   com_coordenada=com_coordenada, distancia_km=distancia, referencia=referencia,
                   percentil_da_distancia=percentil_da_distancia, universo_da_distancia=universo_da_distancia)
    if guardar:
        with _LOCK:
            if len(_QUADROS) >= _MAX_QUADROS:
                _QUADROS.pop(next(iter(_QUADROS)))
            _QUADROS[chave] = saida
    return saida


# --------------------------------------------------------------------------------------------- séries de um território
def _num(valor) -> float | None:
    return None if valor is None or valor != valor else float(valor)


def _linhas_dos_membros(base: Base, territorio: Territorio) -> list[int]:
    return [base.indice[membro[5:]] for membro in territorio.membros]


linhas_dos_membros = _linhas_dos_membros


def populacao_do_territorio(base: Base, territorio: Territorio) -> np.ndarray:
    """A população do território em cada competência: a do município; a soma das populações municipais do estado, do conjunto
    ou do Brasil (NaN quando falta a de algum componente: o denominador nunca é estimado)."""
    pop = base.populacao
    if territorio.tipo == "municipio":
        return pop[territorio.linha]
    if territorio.tipo == "estado":
        linhas = list(base.do_estado.get(territorio.uf, ()))
    elif territorio.tipo == "brasil":
        return np.nansum(pop, axis=0)   # como a taxa do Brasil do Agente: os municípios com registro (2015: 5.569 de 5.570)
    elif territorio.nivel == "estados":
        linhas = [linha for membro in territorio.membros for linha in base.do_estado.get(membro[3:], ())]
    else:
        linhas = _linhas_dos_membros(base, territorio)
    if not linhas:
        return np.full(len(base.periodos), np.nan)
    parte = pop[linhas]
    return np.where(np.isnan(parte).any(axis=0), np.nan, np.nansum(parte, axis=0))


def taxa_do_territorio(base: Base, territorio: Territorio) -> np.ndarray:
    """A taxa do território por 1.000 habitantes em cada competência. Num conjunto, a soma das contagens ÷ a soma das populações
    (nunca a média das taxas dos componentes)."""
    if territorio.tipo == "municipio":
        return _taxas(base)[0][territorio.linha]
    pop = populacao_do_territorio(base, territorio)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(~np.isnan(territorio.serie) & ~np.isnan(pop) & (pop > 0), POR * territorio.serie / pop, np.nan)


def _e(nomes: list[str]) -> str:
    """"do Acre", "do Acre e do Amazonas", "do Acre, do Amazonas e do Pará"."""
    return nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]


def referencia_do_territorio(base: Base, territorio: Territorio) -> tuple[np.ndarray, str, str | None]:
    """A taxa da referência do território em cada competência, o rótulo dela e, quando não há referência, o motivo. A referência
    fica na mesma unidade do território e não o contém (seção 4.2, indicador 10). O rótulo traz o estado com a preposição certa
    ("demais municípios do Amazonas") e um só par de parênteses, para caber em frases sem parênteses dentro de parênteses."""
    vazio = np.full(len(base.periodos), np.nan)
    q, pop = base.quantidade, base.populacao
    if territorio.tipo == "municipio":
        outros = [linha for linha in base.do_estado.get(territorio.uf, ()) if linha != territorio.linha]
        if not outros:
            return vazio, "", "A UF deste município não tem outros municípios: não há referência na mesma unidade."
        return _taxas(base)[1][territorio.linha], "demais municípios " + state_with_preposition(territorio.uf) + " (soma municipal)", None
    if territorio.tipo == "conjunto" and territorio.nivel == "municipios":
        dentro = set(_linhas_dos_membros(base, territorio))
        ufs = sorted({base.prefixos[linha] for linha in dentro})
        outros = [linha for uf in ufs for linha in base.do_estado.get(uf, ()) if linha not in dentro]
        if not outros:
            return vazio, "", "As UFs do conjunto não têm outros municípios: não há referência na mesma unidade."
        valido = ~np.isnan(q[outros]) & ~np.isnan(pop[outros]) & (pop[outros] > 0)
        soma_q, soma_pop = np.where(valido, q[outros], 0.0).sum(axis=0), np.where(valido, pop[outros], 0.0).sum(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            taxa = np.where(soma_pop > 0, POR * soma_q / soma_pop, np.nan)
        return taxa, "demais municípios " + _e([state_with_preposition(uf) for uf in ufs]) + " (soma municipal)", None
    if territorio.nivel == "estados":
        dentro = {territorio.uf} if territorio.tipo == "estado" else {membro[3:] for membro in territorio.membros}
        outros = [uf for uf in base.estados if uf not in dentro]
        if not outros:
            return vazio, "", "Não há outros estados com registro: não há referência na mesma unidade."
        contagens = np.vstack([base.estados[uf] for uf in outros])
        populacoes = np.vstack([np.where(np.isnan(base.populacao[list(base.do_estado.get(uf, ()))]).any(axis=0), np.nan,
                                         np.nansum(base.populacao[list(base.do_estado.get(uf, ()))], axis=0)) for uf in outros])
        completo = ~np.isnan(contagens).any(axis=0) & ~np.isnan(populacoes).any(axis=0)
        with np.errstate(invalid="ignore", divide="ignore"):
            taxa = np.where(completo, POR * np.nansum(contagens, axis=0) / np.nansum(populacoes, axis=0), np.nan)
        return taxa, "demais estados (soma das contagens estaduais)", None
    return vazio, "", "Não há referência na mesma unidade para este território."


# --------------------------------------------------------------------------------------------- fenômenos 8 a 11
# --------------------------------------------------------------------------------------------- a régua dos sinais 8 a 10
@dataclass(frozen=True)
class ReguaRelativa:
    """A régua dos sinais 8, 9 e 10 de um nível (municípios ou estados como unidade), por versão da base: a variação em 2 anos de
    cada unidade em cada janela com população comparável e as comparações dela na régua comum, só com as janelas anteriores."""
    unidades: tuple    # municípios: os códigos, na ordem da base; estados: os prefixos, em ordem
    valor: dict        # chave → [unidade, competência]: a variação na janela que termina na competência (NaN: não se aplica)
    porte: np.ndarray  # [unidade, competência]: a faixa de porte pelo número no início da janela (−1: abaixo de 20 ou sem registro)
    c: dict            # chave → [6, unidade, competência]: k e n do porte, do porte com as vizinhas e de todas as faixas


_REGUAS: dict[tuple, ReguaRelativa] = {}
CHAVES_RELATIVAS = ("disponibilidade", "posicao", "defasagem")


def regua_relativa(base: Base, nivel: str = "municipios", guardar: bool = True) -> ReguaRelativa:
    """A régua dos sinais 8 a 10 (montada uma vez por versão da base e nível). Em cada registro anual com a janela de 2 anos
    habilitada, a variação da taxa (8), do percentil no universo fixo da janela (9) e do índice ante a referência (10) de cada
    unidade com pelo menos 20 profissionais no início da janela; cada uma é comparada só com as das janelas anteriores, de
    unidades do mesmo porte (o número no início da janela)."""
    chave = (base.versao, nivel)
    with _LOCK:
        guardada = _REGUAS.get(chave) if guardar else None
    if guardada is not None:
        return guardada
    t = len(base.periodos)
    if nivel == "municipios":
        unidades = tuple(base.codigos)
        taxa, referencia = _taxas(base, guardar)
        contagem = base.quantidade
    else:
        unidades = tuple(sorted(base.estados))
        estados = [_estado(base, uf) for uf in unidades]
        taxa = np.vstack([taxa_do_territorio(base, estado) for estado in estados]) if estados else np.empty((0, t))
        referencia = np.vstack([referencia_do_territorio(base, estado)[0] for estado in estados]) if estados else np.empty((0, t))
        contagem = np.vstack([estado.serie for estado in estados]) if estados else np.empty((0, t))
    n = len(unidades)
    valor = {nome: np.full((n, t), np.nan) for nome in CHAVES_RELATIVAS}
    porte = np.full((n, t), -1, dtype=np.int8)
    janelas = []
    for fim in range(t):
        ini, ultimo, motivo = janela(base, fim)
        if motivo is not None or ultimo != fim or not n:
            continue
        janelas.append(fim)
        with np.errstate(invalid="ignore", divide="ignore"):
            no_inicio = contagem[:, ini]
            validos = ~np.isnan(no_inicio) & ~np.isnan(contagem[:, fim]) & (no_inicio >= MINIMO_DE_MEDICOS)
            porte[:, fim] = np.where(validos, reguas.portes(no_inicio), -1)
            valor["disponibilidade"][:, fim] = np.where(taxa[:, ini] > 0, 100.0 * (taxa[:, fim] / taxa[:, ini] - 1.0), np.nan)
            juntos = ~np.isnan(taxa[:, ini]) & ~np.isnan(taxa[:, fim])   # o universo fixo na janela
            pa, _ = percentis(np.where(juntos, taxa[:, ini], np.nan))
            pb, _ = percentis(np.where(juntos, taxa[:, fim], np.nan))
            valor["posicao"][:, fim] = pb - pa
            indice_ini = np.where(referencia[:, ini] > 0, 100.0 * taxa[:, ini] / referencia[:, ini], np.nan)
            indice_fim = np.where(referencia[:, fim] > 0, 100.0 * taxa[:, fim] / referencia[:, fim], np.nan)
            valor["defasagem"][:, fim] = indice_fim - indice_ini
    c = {nome: np.zeros((6, n, t), dtype=np.int32) for nome in CHAVES_RELATIVAS}
    um = np.ones((n, t))
    for nome in CHAVES_RELATIVAS:
        medida = valor[nome]
        usavel = np.isfinite(medida) & (porte >= 0)
        for posicao_da_janela, fim in enumerate(janelas):
            atuais = np.flatnonzero(usavel[:, fim])
            antes = janelas[:posicao_da_janela]
            if not atuais.size or not antes:
                continue
            passado = usavel[:, antes]
            if not passado.any():
                continue
            # A medida já é relativa (variação percentual, pontos de percentil ou de índice): entre todas as faixas, é comparada
            # como está.
            comparadas = reguas.comparar_com_o_passado(
                medida[atuais, fim], medida[atuais, fim], um[atuais, fim], porte[atuais, fim], medida[:, antes][passado],
                medida[:, antes][passado], um[:, antes][passado], porte[:, antes][passado])
            for origem in range(6):
                c[nome][origem, atuais, fim] = comparadas[origem]
    for matriz in (porte, *valor.values(), *c.values()):
        matriz.setflags(write=False)
    saida = ReguaRelativa(unidades=unidades, valor=valor, porte=porte, c=c)
    if guardar:
        with _LOCK:
            if len(_REGUAS) > 4:
                _REGUAS.clear()
            _REGUAS[chave] = saida
    return saida


def _nivel_relativo(base: Base, qd: Quadro, territorio: Territorio, nome: str, p: dict) -> dict:
    """O nível de um dos sinais 8 a 10 pela raridade da variação na base: o estado, a classe, a raridade lida e os níveis que a
    base ainda não sustenta. Municípios pela régua dos municípios; estados como unidade, pela dos estados; um conjunto não tem
    régua (não há outros iguais para comparar)."""
    if territorio.tipo == "conjunto":
        return {"estado": "nivel_sem_classificacao", "classe": None, "criterio": COMPARADO}
    if territorio.tipo == "municipio":
        regua, linha = regua_relativa(base, "municipios"), territorio.linha
    else:
        regua = regua_relativa(base, "estados")
        linha = regua.unidades.index(territorio.uf)
    limites = {nivel: p[nome][nivel + "_um_em"] for nivel, _, _ in reguas.NIVEIS}
    lida = reguas.nivel_da_raridade(*(int(x) for x in regua.c[nome][:, linha, qd.fim]), limites=limites)
    faixa = int(regua.porte[linha, qd.fim])
    saida = {"classe": lida["nivel"], "criterio": COMPARADO, "raridade": lida, "sem_comparacoes": reguas.sem_comparacoes(lida),
             "porte": faixa if faixa >= 0 else None}
    saida["estado"] = "classificado" if lida["nivel"] else "sem_comparacoes" if not any(
        dados["avaliado"] for dados in lida["niveis"].values()) else "sem_sinal"
    return saida


def _comum(base: Base, qd: Quadro) -> dict:
    return {"de": None if qd.ini is None else base.periodos[qd.ini], "ate": None if qd.fim is None else base.periodos[qd.fim]}


def disponibilidade(base: Base, qd: Quadro, territorio: Territorio, p: dict) -> dict:
    """Fenômeno 8: a taxa na data e a variação dela na janela de comparação, com a decomposição."""
    taxa, pop, serie = taxa_do_territorio(base, territorio), populacao_do_territorio(base, territorio), territorio.serie
    saida = {"taxa": _num(taxa[qd.e]), "populacao": _num(pop[qd.e]), "competencia": base.periodos[qd.e], "classe": None, **_comum(base, qd)}
    if serie[qd.e] != serie[qd.e]:
        return {**saida, "estado": "ausencia_de_dado"}
    if saida["taxa"] is None:
        return {**saida, "estado": "nao_calculavel", "motivo": "Sem população válida na data (o denominador não é estimado)."}
    if qd.motivo:
        return {**saida, "estado": qd.motivo}
    a, b = qd.ini, qd.fim
    if serie[a] != serie[a] or serie[b] != serie[b]:
        return {**saida, "estado": "ausencia_de_dado"}
    if taxa[a] != taxa[a] or taxa[b] != taxa[b] or not taxa[a] > 0:
        return {**saida, "estado": "nao_calculavel", "motivo": "Sem taxa válida e acima de zero no início ou no fim da janela."}
    variacao = 100.0 * (taxa[b] / taxa[a] - 1)
    saida.update({"taxa_inicial": float(taxa[a]), "taxa_final": float(taxa[b]), "variacao_pct": float(variacao),
                  "medicos": {"inicial": float(serie[a]), "final": float(serie[b]), "variacao_pct": float(100.0 * (serie[b] / serie[a] - 1))},
                  "populacao_da_janela": {"inicial": float(pop[a]), "final": float(pop[b]), "variacao_pct": float(100.0 * (pop[b] / pop[a] - 1))}})
    if serie[a] < MINIMO_DE_MEDICOS:
        return {**saida, "estado": "descritivo"}
    return {**saida, **_nivel_relativo(base, qd, territorio, "disponibilidade", p)}


def posicao(base: Base, qd: Quadro, territorio: Territorio, p: dict) -> dict:
    """Fenômeno 9: o percentil do território pela taxa e a variação dele num universo fixo na janela. Municípios no universo
    dos municípios do Brasil; estados como unidade, no dos estados; conjuntos não entram em universos de percentis."""
    saida = {"percentil": None, "universo": None, "competencia": base.periodos[qd.e], "classe": None, **_comum(base, qd)}
    if territorio.tipo == "conjunto":
        return {**saida, "estado": "nao_aplicavel", "motivo": "Conjuntos não entram no universo de percentis: a posição relativa "
                "compara territórios do mesmo tipo, um a um."}
    if territorio.serie[qd.e] != territorio.serie[qd.e]:
        return {**saida, "estado": "ausencia_de_dado"}
    if territorio.tipo == "municipio":
        linha = territorio.linha
        saida.update({"percentil": _num(qd.percentil_na_data[linha]), "universo": qd.universo_na_data,
                      "nome_do_universo": "municípios do Brasil com taxa válida"})
        if saida["percentil"] is None:
            return {**saida, "estado": "nao_calculavel", "motivo": "Sem taxa válida na data."}
        if qd.motivo:
            return {**saida, "estado": qd.motivo}
        pa, pb = qd.percentil_ini[linha], qd.percentil_fim[linha]
        if pa != pa or pb != pb:
            return {**saida, "estado": "nao_calculavel", "motivo": "O território não está no universo fixo da janela (falta a taxa "
                    "numa das datas)."}
        inicial = base.quantidade[linha, qd.ini]
        universo = qd.universo
    else:   # estado como unidade: o universo dos estados com taxa válida
        estados = {uf: taxa_do_territorio(base, _estado(base, uf)) for uf in base.estados}
        ufs = sorted(estados)
        na_data, n = percentis(np.array([estados[uf][qd.e] for uf in ufs]))
        saida.update({"percentil": _num(na_data[ufs.index(territorio.uf)]), "universo": n,
                      "nome_do_universo": "estados com taxa válida"})
        if saida["percentil"] is None:
            return {**saida, "estado": "nao_calculavel", "motivo": "Sem taxa válida na data."}
        if qd.motivo:
            return {**saida, "estado": qd.motivo}

        def do_par(a, b):
            juntos = np.array([estados[uf][a] == estados[uf][a] and estados[uf][b] == estados[uf][b] for uf in ufs])
            xa, n_par = percentis(np.where(juntos, np.array([estados[uf][a] for uf in ufs]), np.nan))
            xb, _ = percentis(np.where(juntos, np.array([estados[uf][b] for uf in ufs]), np.nan))
            return xa[ufs.index(territorio.uf)], xb[ufs.index(territorio.uf)], n_par
        pa, pb, universo = do_par(qd.ini, qd.fim)
        if pa != pa or pb != pb:
            return {**saida, "estado": "nao_calculavel", "motivo": "O território não está no universo fixo da janela."}
        inicial = territorio.serie[qd.ini]
    variacao = float(pb - pa)
    saida.update({"percentil_inicial": float(pa), "percentil_final": float(pb), "variacao_pp": variacao, "universo_da_janela": universo})
    if inicial < MINIMO_DE_MEDICOS:
        return {**saida, "estado": "descritivo"}
    return {**saida, **_nivel_relativo(base, qd, territorio, "posicao", p)}


def _estado(base: Base, uf: str) -> Territorio:
    return Territorio(id="uf:" + uf, tipo="estado", nivel="estados", rotulo=STATES[uf][1], uf=uf, serie=base.estados[uf], unidade="")


def defasagem(base: Base, qd: Quadro, territorio: Territorio, p: dict) -> dict:
    """Fenômeno 10: o índice 100 × taxa do território ÷ taxa da referência (na mesma unidade, sem o território) e a variação."""
    taxa = taxa_do_territorio(base, territorio)
    da_referencia, rotulo, sem_referencia = referencia_do_territorio(base, territorio)
    saida = {"indice": None, "referencia": {"rotulo": rotulo, "taxa": _num(da_referencia[qd.e])}, "taxa": _num(taxa[qd.e]),
             "competencia": base.periodos[qd.e], "classe": None, **_comum(base, qd)}
    if sem_referencia:
        return {**saida, "estado": "referencia_invalida", "motivo": sem_referencia}
    if territorio.serie[qd.e] != territorio.serie[qd.e]:
        return {**saida, "estado": "ausencia_de_dado"}

    def indice(i):
        return float(100.0 * taxa[i] / da_referencia[i]) if taxa[i] == taxa[i] and da_referencia[i] == da_referencia[i] and \
            da_referencia[i] > 0 else None
    saida["indice"] = indice(qd.e)
    if saida["indice"] is None:
        return {**saida, "estado": "nao_calculavel", "motivo": "Sem taxa válida do território ou da referência na data."}
    if qd.motivo:
        return {**saida, "estado": qd.motivo}
    inicial, final = indice(qd.ini), indice(qd.fim)
    if inicial is None or final is None:
        return {**saida, "estado": "nao_calculavel", "motivo": "Sem taxa válida do território ou da referência no início ou no fim "
                "da janela."}
    variacao = final - inicial
    saida.update({"indice_inicial": inicial, "indice_final": final, "variacao_pontos": variacao})
    if territorio.serie[qd.ini] < MINIMO_DE_MEDICOS:
        return {**saida, "estado": "descritivo"}
    return {**saida, **_nivel_relativo(base, qd, territorio, "defasagem", p)}


def contexto(base: Base, qd: Quadro, territorio: Territorio) -> dict:
    """Fenômeno 11: a distância geodésica até o município mais próximo com taxa igual ou maior que o critério. Só contexto."""
    criterio = {"taxa_minima": qd.limiar, "taxa_do_brasil": qd.taxa_do_brasil, "competencia": base.periodos[qd.e]}
    saida = {"distancia_km": None, "referencia": None, "percentil_da_distancia": None, "criterio": criterio,
             "universo": qd.universo_da_distancia}
    if qd.limiar is None:
        return {**saida, "estado": "nao_calculavel", "motivo": "Sem a taxa do Brasil na data: o critério não pode ser aplicado."}
    if territorio.nivel != "municipios":
        return {**saida, "estado": "nao_aplicavel", "motivo": "O estado como unidade não tem um ponto único: a distância é medida "
                "de cada município."}
    linhas = [territorio.linha] if territorio.tipo == "municipio" else _linhas_dos_membros(base, territorio)
    if any(bool(qd.atende[linha]) for linha in linhas):
        return {**saida, "estado": "atende_ao_criterio"}
    com_distancia = [linha for linha in linhas if qd.distancia_km[linha] == qd.distancia_km[linha]]
    if not com_distancia:
        sem_ponto = not any(bool(qd.com_coordenada[linha]) for linha in linhas)
        return {**saida, "estado": "sem_coordenada" if sem_ponto else "nao_calculavel",
                "motivo": "Sem coordenada válida na data." if sem_ponto else "Sem taxa válida na data ou sem município que atenda ao "
                "critério."}
    perto = min(com_distancia, key=lambda linha: (qd.distancia_km[linha], linha))   # num conjunto, o membro mais próximo
    alvo = int(qd.referencia[perto])
    return {**saida, "estado": "contexto", "distancia_km": float(qd.distancia_km[perto]),
            "percentil_da_distancia": _num(qd.percentil_da_distancia[perto]) if territorio.tipo == "municipio" else None,
            "referencia": {"id": "code:" + base.codigos[alvo], "rotulo": base.nomes[alvo], "taxa": _num(qd.taxa[alvo, qd.e])},
            **({"membro": base.nomes[perto]} if territorio.tipo == "conjunto" else {})}


# --------------------------------------------------------------------------------------------- fenômeno 12
COMBINACOES = (
    ("estrutural_e_perda", "Poucos médicos e perda no último registro"),
    ("estrutural_e_declinio", "Poucos médicos e declínio persistente"),
    ("declinio_e_relativa", "Declínio persistente e queda da disponibilidade ou da posição relativa"),
    ("patamar_e_estrutural", "Abaixo do patamar anterior e poucos médicos"),
)
REPERCUSSOES = (("perda", "perda no último registro"), ("declinio", "declínio persistente"), ("patamar", "afastamento de patamar"),
                ("disponibilidade", "queda da taxa por habitante"), ("posicao", "queda da posição relativa"),
                ("defasagem", "ampliação da defasagem ante a referência"))


def coexistencia(sinais: list[str], classe_estrutural: str | None) -> dict:
    """Fenômeno 12: o perfil e as combinações pré-definidas, sem índice geral. As repercussões de quedas no número de médicos
    (perda, declínio, patamar e os três indicadores relativos) são efeitos que se sobrepõem: contam como uma frente de sinal, não
    como evidências independentes."""
    tem = set(sinais)
    presentes = {
        "estrutural_e_perda": classe_estrutural in ("elevado", "critico") and "perda" in tem,
        "estrutural_e_declinio": classe_estrutural in ("elevado", "critico") and "declinio" in tem,
        "declinio_e_relativa": "declinio" in tem and bool(tem & {"disponibilidade", "posicao"}),
        "patamar_e_estrutural": "patamar" in tem and classe_estrutural is not None,
    }
    combinacoes = [{"chave": chave, "texto": texto} for chave, texto in COMBINACOES if presentes[chave]]
    repercussoes = [texto for chave, texto in REPERCUSSOES if chave in tem]
    frentes = [nome for nome, vale in (("condição estrutural", classe_estrutural is not None or "ausencia" in tem),
                                       ("queda no número de médicos", bool(repercussoes)),
                                       ("ritmo", "desaceleracao" in tem)) if vale]
    return {"estado": "sinais_combinados" if combinacoes else "sem_combinacao", "combinacoes": combinacoes,
            "repercussoes": repercussoes, "frentes": frentes}
