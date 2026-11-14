"""Detector de Sinais Territoriais (comando V23, Proposta V3, Partes A e B; o motor dos sinais 1 a 7, da descontinuidade de
registro, do alerta de cada território e dos textos). Referência metodológica: Docs/DETECTOR_E_SIMULADOR_V3.md; a V2.2
(Docs/DETECTOR_E_SIMULADOR_V2_2.md) continua valendo no que a V3 não muda. A tela e os textos estão em Docs/DETECTOR_DE_SINAIS.md.

A ideia: o Detector compara cada território com o que é comum na própria base — territórios de tamanho parecido (o porte) e só o
que veio antes de cada data. Três coisas nunca se confundem:

1. **fato observado** — a contagem e a mudança entre registros (−3, −30%, com as datas reais); sempre exibido;
2. **raridade** — (mudanças anteriores iguais ou piores + 1) ÷ (total de mudanças anteriores + 1), entre as mudanças anteriores à
   data avaliada de territórios do mesmo porte e com o mesmo tempo entre registros, contando os empates (reguas.py);
3. **nível do alerta** — moderado (1 em cada 20, com pelo menos 19 comparações), elevado (1 em cada 100, com 99) ou crítico
   (1 em cada 1.000, com 999), sempre com o tipo de critério: "comparado com a base" ou "por convenção". Quando a base não tem
   comparações bastantes para um nível, a resposta diz "sem comparações suficientes", com quantas há e quantas ele pede. "Raro"
   quer dizer incomum nesta base, não comprovadamente pior: o nível não é juízo de desassistência, de suficiência do cuidado nem
   de prioridade de provimento (divergência aprovada da SPEC, CFG-NOR: D-A, com os nomes de 13/11/2026).

Os 12 sinais (tabela B.2), sempre pelo motor e sem o provedor de IA; todos os limites são padrões e podem ser trocados, como
configuração exploratória:

- **1–2, poucos profissionais e nenhum registrado (por convenção):** 1 ou zero confirmado, crítico; 2–3, elevado; 4–5, moderado.
  O nível exibido é o mais grave entre os dois últimos registros válidos (a piora aparece na hora; a melhora, depois de dois).
- **3, declínio persistente (por convenção):** quedas seguidas na série anual (o mês âncora) e perda acumulada: 2 e 10%, moderado;
  3 e 20%, elevado; 4 e 30%, crítico.
- **4, desaceleração (por convenção, exploratório):** a classe da Análise de Tendência (trend.classify_pairs, CAP-TEN-01) nos 4
  registros anuais; moderado quando a classe se repete em 2 anos seguidos. Mostra uma mudança de ritmo; não indica o que vem depois.
- **5, instabilidade (comparado com a base):** a oscilação de 7 registros dividida pela típica do porte; moderado quando o
  índice é raro (1 em cada 20).
- **6, queda recente (comparado com a base, com tamanho mínimo):** a queda entre registros consecutivos sempre aparece; é alerta
  quando é rara e tem o tamanho mínimo do nível (2 e 10%; 2 e 20%; 3 e 30% do que havia).
- **7, abaixo do que já teve (por convenção e comparado com a base):** patamar = a maior média de dois anos completos, antes dos
  4 últimos registros. Os 2 últimos registros 15% ou mais abaixo: moderado; isso e raro (1 em 100): elevado; os 4 últimos 30%
  ou mais abaixo e raro (1 em 1.000): crítico. Só com patamar de pelo menos 20.
- **8 a 12:** comparativos.py (a taxa por habitante, a posição, a referência, a distância e os sinais juntos).
- **descontinuidade de registro:** pico que volta, quebra de fonte e "verificar registro", como na V2.2. O pico não gera alerta
  na volta e sai da régua; a queda grande que persiste continua alertável.

Um nível por território: o maior entre os seus sinais, sem soma nem índice; os sinais que vêm da mesma queda contam como um
evento. Os estados como unidade têm régua própria (a base dos estados); um conjunto não tem nível, só os fatos e o motivo. Quando,
numa data, as quedas raras passam do triplo do esperado, a resposta traz o aviso da base.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, replace

import numpy as np

import nomes_anteriores
import reguas
import series_brasil
import comparativos
from series_brasil import Base, Territorio
from territorial_levels import STATES, human_period
from trend import FAMILY as FAMILIA_DA_TENDENCIA, LABELS as ROTULOS_DA_TENDENCIA, classify_pairs

VERSION = "DETECTOR-SINAIS/V3/1"   # Proposta V3 (comando V23): régua comum, níveis moderado, elevado e crítico
# Faixas de porte da régua comum (Proposta V3, seção A.2.2): pelo número de profissionais no registro anterior (ou pelo
# patamar, no sinal 7). As quatro faixas acima de 300 substituem o antigo "300 ou mais".
PORTES = reguas.PORTES
ROTULOS_DOS_PORTES = reguas.ROTULOS_DOS_PORTES
INTERVALOS = (5, 7)  # meses da base do Brasil (janeiro → junho e junho → janeiro): só para a oscilação típica do sinal 5
ORIGENS = 6          # k e n de cada origem da régua: o porte, o porte com as vizinhas e todas as faixas
SEM_DATA = 10 ** 6   # "nunca conhecido"

# Parâmetros padrão: os limites da tabela B.2 da Proposta V3. Todos podem ser trocados, como configuração exploratória.
UM_EM = {"moderado_um_em": 20, "elevado_um_em": 100, "critico_um_em": 1000}
PADRAO = {
    "estrutural": {"critico": 1, "elevado": 3, "moderado": 5},
    "declinio": {"moderado_quedas": 2, "moderado_perda": 10.0, "elevado_quedas": 3, "elevado_perda": 20.0,
                 "critico_quedas": 4, "critico_perda": 30.0},
    "desaceleracao": {"anos": 2},
    "instabilidade": {"moderado_um_em": 20},
    "perda": {**UM_EM, "moderado_minimo": 2, "moderado_fracao": 10.0, "elevado_minimo": 2, "elevado_fracao": 20.0,
              "critico_minimo": 3, "critico_fracao": 30.0},
    "patamar": {"moderado": 15.0, "critico": 30.0, "minimo": 20, "elevado_um_em": 100, "critico_um_em": 1000},
    **comparativos.PADRAO,   # sinais 8 a 10 (raridade da variação em 2 anos) e o critério do sinal 11
}
# O que a pessoa pode trocar, como configuração exploratória: (mínimo, máximo, inteiro).
_UM_EM = (2, 100000, True)
EDITAVEIS = {
    "estrutural": {"critico": (0, 50, True), "elevado": (0, 50, True), "moderado": (0, 50, True)},
    "declinio": {"moderado_quedas": (1, 10, True), "moderado_perda": (1.0, 90.0, False), "elevado_quedas": (1, 10, True),
                 "elevado_perda": (1.0, 90.0, False), "critico_quedas": (1, 10, True), "critico_perda": (1.0, 90.0, False)},
    "desaceleracao": {"anos": (1, 5, True)},
    "instabilidade": {"moderado_um_em": _UM_EM},
    "perda": {"moderado_um_em": _UM_EM, "elevado_um_em": _UM_EM, "critico_um_em": _UM_EM,
              "moderado_minimo": (1, 50, True), "moderado_fracao": (1.0, 90.0, False), "elevado_minimo": (1, 50, True),
              "elevado_fracao": (1.0, 90.0, False), "critico_minimo": (1, 50, True), "critico_fracao": (1.0, 90.0, False)},
    "patamar": {"moderado": (1.0, 90.0, False), "critico": (1.0, 90.0, False), "minimo": (1, 1000, True),
                "elevado_um_em": _UM_EM, "critico_um_em": _UM_EM},
    **comparativos.EDITAVEIS,
}
# Registro (seção 2.4): critérios provisórios, fixos (mudam o que entra na calibração).
PICO_SALTO, PICO_FATOR, PICO_RETORNO, PICO_REGISTROS = 10, 2.0, 1.25, 2
QUEDA_GRANDE, QUEDA_FRACAO = 10, 0.5
THETA, REGISTROS_DA_INSTABILIDADE, MEDIA_MINIMA_DA_INSTABILIDADE, MINIMO_DE_ESCALA = 1.35, 7, 6.0, 100
GRAVIDADE = reguas.GRAVIDADE   # None 0, moderado 1, elevado 2, critico 3
MAX_LINHAS = 6000


# --------------------------------------------------------------------------------------------- parâmetros
def parametros(bruto) -> tuple[dict, bool]:
    """Os parâmetros em uso e se há algum personalizado (a configuração exploratória, que nunca troca os padrões em silêncio)."""
    em_uso = {grupo: dict(valores) for grupo, valores in PADRAO.items()}
    if bruto in (None, {}):
        return em_uso, False
    if not isinstance(bruto, dict):
        raise ValueError("Parâmetros do Detector inválidos.")
    personalizado = False
    for grupo, valores in bruto.items():
        if grupo not in EDITAVEIS or not isinstance(valores, dict):
            raise ValueError("Parâmetro do Detector desconhecido: " + str(grupo) + ".")
        for chave, valor in valores.items():
            if chave not in EDITAVEIS[grupo]:
                raise ValueError("Parâmetro do Detector desconhecido: " + grupo + "." + str(chave) + ".")
            minimo, maximo, inteiro = EDITAVEIS[grupo][chave]
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or \
                    not minimo <= valor <= maximo or (inteiro and int(valor) != valor):
                raise ValueError("Valor fora do intervalo em " + grupo + "." + chave + ": use " +
                                 ("um inteiro " if inteiro else "um número ") + "de " + str(minimo) + " a " + str(maximo) + ".")
            valor = int(valor) if inteiro else float(valor)
            if valor != PADRAO[grupo][chave]:
                personalizado = True
            em_uso[grupo][chave] = valor
    e = em_uso["estrutural"]
    if not e["critico"] <= e["elevado"] <= e["moderado"]:
        raise ValueError("Poucos profissionais: os limites precisam crescer (crítico ≤ elevado ≤ moderado).")
    for grupo in ("perda", "disponibilidade", "posicao", "defasagem"):
        g = em_uso[grupo]
        if not g["moderado_um_em"] <= g["elevado_um_em"] <= g["critico_um_em"]:
            raise ValueError("Raridade: o nível mais grave não pode ser mais comum que o menos grave (moderado ≤ elevado ≤ crítico).")
    q, d = em_uso["perda"], em_uso["declinio"]
    if not (q["moderado_fracao"] <= q["elevado_fracao"] <= q["critico_fracao"] and
            q["moderado_minimo"] <= q["elevado_minimo"] <= q["critico_minimo"]):
        raise ValueError("Queda recente: o tamanho mínimo do nível mais grave não pode ser menor que o do menos grave.")
    if not (d["moderado_quedas"] <= d["elevado_quedas"] <= d["critico_quedas"] and
            d["moderado_perda"] <= d["elevado_perda"] <= d["critico_perda"]):
        raise ValueError("Declínio persistente: o limite do nível mais grave não pode ser menor que o do menos grave.")
    if em_uso["patamar"]["critico"] < em_uso["patamar"]["moderado"] or \
            em_uso["patamar"]["critico_um_em"] < em_uso["patamar"]["elevado_um_em"]:
        raise ValueError("Abaixo do que já teve: o limite do nível mais grave não pode ser menor que o do menos grave.")
    comparativos.conferir(em_uso)
    return em_uso, personalizado


porte_de = reguas.porte_de   # o índice da faixa de porte de uma contagem (None para zero, ausente ou abaixo de 1)
_portes = reguas.portes      # a faixa de porte de cada valor de uma matriz (−1 para zero, ausente ou abaixo de 1)


# --------------------------------------------------------------------------------------------- calibração (municipal)
@dataclass(frozen=True)
class Calibracao:
    """O que a calibração municipal guarda por versão da base: marcas de registro e a excepcionalidade de cada transição e de
    cada afastamento de patamar, sempre só com o que era conhecido na data avaliada."""
    versao: str
    pico: np.ndarray            # [município, competência]: o registro faz parte de um pico que volta
    pico_conhecido: np.ndarray  # índice da competência em que a volta foi observada (SEM_DATA: não é pico)
    marca: np.ndarray           # transição que termina na competência: 0, 1 salto, 2 meio do pico, 3 volta, 4 quebra de fonte
    marca_conhecida: np.ndarray  # índice em que a marca da transição passou a ser conhecida
    salto: np.ndarray           # transição: salto de 10 ou mais que ao menos dobra (com ou sem volta)
    queda_grande: np.ndarray    # transição: queda de 10 ou mais que leva à metade ou menos
    quebra: np.ndarray          # registro em quebra de fonte (soma municipal da UF abaixo da contagem estadual)
    c_perda: np.ndarray         # [6, município, competência]: as comparações da transição na régua comum (k e n do porte,
    #                             do porte com as vizinhas e de todas as faixas), só com as transições anteriores do mesmo tempo
    #                             entre registros e sem as descontinuidades já conhecidas na data avaliada
    patamar: np.ndarray         # patamar de cada município em cada data (NaN: sem bloco elegível)
    patamar_ano: np.ndarray     # ano inicial do bloco do patamar (−1: nenhum)
    afastamento: np.ndarray     # 1 − máx(2 últimos)/patamar (NaN quando não se aplica)
    c_patamar: np.ndarray       # [6, município, competência]: as comparações do afastamento (maior é pior), pelo porte do patamar
    instabilidade: np.ndarray   # índice de instabilidade (NaN: não calculável)
    c_instabilidade: np.ndarray  # [6, município, competência]: as comparações do índice (maior é pior), pelo porte da média da janela
    porte_da_janela: np.ndarray  # faixa de porte da média dos 7 registros da janela do sinal 5 (−1: nenhuma)
    escala: np.ndarray          # [competência, tipo de intervalo]: c do tipo, estimado só com transições anteriores
    blocos: tuple               # (ano inicial, índices dos 4 registros, índice do último registro)
    relativa: np.ndarray        # variação relativa de cada transição (NaN quando não se aplica)
    regular: np.ndarray         # transição com os dois registros, N anterior ≥ 1 e intervalo de 5 ou 7 meses
    porte: np.ndarray           # faixa de porte do N anterior de cada transição (−1: nenhuma)
    porte_do_patamar: np.ndarray
    intervalo: np.ndarray       # meses de cada transição


_CALIBRACOES: dict[str, Calibracao] = {}
_LOCK = threading.Lock()


def _blocos(base: Base) -> tuple:
    """Blocos de dois anos civis completos: janeiro e junho do ano Y e do ano Y + 1."""
    posicao = {periodo: indice for indice, periodo in enumerate(base.periodos)}
    anos = sorted({int(periodo[:4]) for periodo in base.periodos})
    blocos = []
    for ano in anos:
        chaves = [str(ano) + "01", str(ano) + "06", str(ano + 1) + "01", str(ano + 1) + "06"]
        if all(chave in posicao for chave in chaves):
            indices = tuple(posicao[chave] for chave in chaves)
            blocos.append((ano, indices, max(indices)))
    return tuple(blocos)


def calibrar(base: Base, guardar: bool = True) -> Calibracao:
    """A calibração da versão da base (montada uma vez). Tudo aqui respeita as origens móveis: o que entra na avaliação de uma
    data são só as transições e as avaliações anteriores a ela, e um pico só conta como pico depois que a volta foi observada.
    Sem `guardar` (o estudo do modelo nulo, em scripts/calibrar_detector.py), nada fica na memória."""
    with _LOCK:
        guardada = _CALIBRACOES.get(base.versao) if guardar else None
    if guardada is not None:
        return guardada
    q = base.quantidade
    n, t = q.shape
    meses = base.meses
    with np.errstate(invalid="ignore", divide="ignore"):
        delta = np.full((n, t), np.nan)
        delta[:, 1:] = q[:, 1:] - q[:, :-1]
        anterior = np.full((n, t), np.nan)
        anterior[:, 1:] = q[:, :-1]
        relativa = delta / anterior
        salto = (delta >= PICO_SALTO) & (q >= PICO_FATOR * anterior)
        queda_grande = (delta <= -QUEDA_GRANDE) & (q <= QUEDA_FRACAO * anterior)
    intervalo = np.zeros(t, dtype=int)
    intervalo[1:] = np.diff(meses)

    # Picos que voltam: do salto até a volta (em até dois registros, a até 125% do valor anterior ao salto).
    pico = np.zeros((n, t), dtype=bool)
    pico_conhecido = np.full((n, t), SEM_DATA, dtype=np.int32)
    marca = np.zeros((n, t), dtype=np.int8)
    marca_conhecida = np.full((n, t), SEM_DATA, dtype=np.int32)
    for linha, i in np.argwhere(salto):
        base_do_salto = q[linha, i - 1]
        volta = next((k for k in range(i + 1, min(i + PICO_REGISTROS, t - 1) + 1)
                      if q[linha, k] == q[linha, k] and q[linha, k] <= PICO_RETORNO * base_do_salto), None)
        if volta is None:
            continue
        pico[linha, i:volta] = True
        pico_conhecido[linha, i:volta] = volta
        marca[linha, i] = 1
        marca[linha, i + 1:volta] = 2
        marca[linha, volta] = 3
        marca_conhecida[linha, i:volta + 1] = volta

    # Quebra de fonte: a soma municipal da UF abaixo da contagem estadual de médicos únicos da própria UF.
    quebra = np.zeros((n, t), dtype=bool)
    for prefixo, estadual in base.estados.items():
        linhas = list(base.do_estado.get(prefixo, ()))
        if not linhas:
            continue
        with np.errstate(invalid="ignore"):
            # Só nas competências em que todos os municípios da UF têm registro: a soma com um ausente não é a soma da UF.
            abaixo = (base.soma_municipal_do_estado(prefixo) < estadual) & (base.ausentes_do_estado(prefixo) == 0)
        if abaixo.any():
            quebra[np.ix_(linhas, np.flatnonzero(abaixo))] = True
    em_quebra = quebra.copy()
    em_quebra[:, 1:] |= quebra[:, :-1]  # a transição que sai da quebra também é da quebra
    for linha, i in np.argwhere(em_quebra & (marca == 0)):
        if i > 0:
            marca[linha, i] = 4
            marca_conhecida[linha, i] = i

    # Perda abrupta: P(X ≤ x) na célula porte × tipo de intervalo, só com transições anteriores e sem as descontinuidades já
    # conhecidas na data avaliada.
    regular = np.zeros((n, t), dtype=bool)
    with np.errstate(invalid="ignore"):
        regular[:, 1:] = (q[:, 1:] == q[:, 1:]) & (q[:, :-1] >= 1)
    regular &= (intervalo > 0)[None, :]
    porte = _portes(anterior)
    c_perda = np.zeros((ORIGENS, n, t), dtype=np.int32)
    for j in range(1, t):
        atuais = np.flatnonzero(regular[:, j])
        colunas = [i for i in range(1, j) if intervalo[i] == intervalo[j]]   # só o mesmo tempo entre registros
        if not atuais.size or not colunas:
            continue
        usavel = regular[:, colunas] & ~(marca_conhecida[:, colunas] <= j)
        comparadas = reguas.comparar_com_o_passado(
            relativa[atuais, j], delta[atuais, j], anterior[atuais, j], porte[atuais, j], relativa[:, colunas][usavel],
            delta[:, colunas][usavel], anterior[:, colunas][usavel], porte[:, colunas][usavel])
        for origem in range(ORIGENS):
            c_perda[origem, atuais, j] = comparadas[origem]

    # Afastamento de patamar: o patamar de cada data e a cauda do afastamento por faixa de porte do patamar.
    blocos = _blocos(base)
    medias = np.full((n, len(blocos)), np.nan)
    for b, (_, indices, _) in enumerate(blocos):
        medias[:, b] = q[:, list(indices)].mean(axis=1)  # NaN quando falta um dos 4 registros
    patamar = np.full((n, t), np.nan)
    patamar_ano = np.full((n, t), -1, dtype=np.int32)
    for e in range(t):
        melhores = np.full(n, -np.inf)
        anos = np.full(n, -1, dtype=np.int32)
        for b, (ano, indices, fim) in enumerate(blocos):
            if fim > e - 4:
                continue
            indices = list(indices)
            # Fora do patamar: o bloco com um registro de pico já conhecido na data ou em quebra de fonte.
            limpo = ~((pico_conhecido[:, indices] <= e).any(axis=1) | quebra[:, indices].any(axis=1))
            media = np.where(limpo, medias[:, b], np.nan)
            with np.errstate(invalid="ignore"):
                melhor = media > melhores
            melhores[melhor], anos[melhor] = media[melhor], ano
        achou = np.isfinite(melhores)
        patamar[achou, e], patamar_ano[achou, e] = melhores[achou], anos[achou]
    afastamento = np.full((n, t), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        for e in range(1, t):
            ok = (patamar[:, e] > 0) & (q[:, e] == q[:, e]) & (q[:, e - 1] == q[:, e - 1])
            afastamento[ok, e] = 1 - np.maximum(q[ok, e], q[ok, e - 1]) / patamar[ok, e]
    porte_do_patamar = _portes(np.floor(patamar))
    c_patamar = np.zeros((ORIGENS, n, t), dtype=np.int32)
    with np.errstate(invalid="ignore"):
        falta = afastamento * patamar   # o afastamento em número de profissionais, para a comparação entre todas as faixas
    for e in range(1, t):
        atuais = np.flatnonzero(np.isfinite(afastamento[:, e]) & (porte_do_patamar[:, e] >= 0))
        if not atuais.size:
            continue
        # Só avaliações anteriores, sem as que tinham um registro de pico (conhecido até a data) nos dois últimos registros.
        usavel = np.isfinite(afastamento[:, :e]) & (porte_do_patamar[:, :e] >= 0)
        com_pico = (pico_conhecido[:, :e] <= e)
        com_pico[:, 1:] |= (pico_conhecido[:, :e - 1] <= e) if e > 1 else False
        usavel &= ~com_pico & ~quebra[:, :e]
        comparadas = reguas.comparar_com_o_passado(
            afastamento[atuais, e], falta[atuais, e], patamar[atuais, e], porte_do_patamar[atuais, e], afastamento[:, :e][usavel],
            falta[:, :e][usavel], patamar[:, :e][usavel], porte_do_patamar[:, :e][usavel], pior_e_menor=False)
        for origem in range(ORIGENS):
            c_patamar[origem, atuais, e] = comparadas[origem]

    # Instabilidade (descritiva): as variações de 7 registros pela oscilação típica do porte, por tipo de intervalo.
    instabilidade = np.full((n, t), np.nan)
    media_da_janela = np.full((n, t), np.nan)
    escala = np.full((t, len(INTERVALOS)), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        padronizada = delta / np.power(anterior, THETA / 2)
    grande = regular & (anterior >= MEDIA_MINIMA_DA_INSTABILIDADE)
    for e in range(REGISTROS_DA_INSTABILIDADE - 1, t):
        for k, meses_do_tipo in enumerate(INTERVALOS):
            colunas = [i for i in range(1, e) if intervalo[i] == meses_do_tipo]
            if not colunas:
                continue
            usavel = grande[:, colunas] & ~(marca_conhecida[:, colunas] <= e)
            valores = padronizada[:, colunas][usavel]
            if valores.size >= MINIMO_DE_ESCALA:
                mediana = np.median(valores)
                escala[e, k] = 1.4826 * np.median(np.abs(valores - mediana))
        janela = list(range(e - REGISTROS_DA_INSTABILIDADE + 1, e + 1))
        transicoes = janela[1:]
        if any(intervalo[i] not in INTERVALOS for i in transicoes):
            continue
        c = np.array([escala[e, INTERVALOS.index(int(intervalo[i]))] for i in transicoes])
        if not np.isfinite(c).all() or (c <= 0).any():
            continue
        valores = q[:, janela]
        media = valores.mean(axis=1)
        with np.errstate(invalid="ignore"):
            ok = np.isfinite(media) & (media >= MEDIA_MINIMA_DA_INSTABILIDADE) & ~(marca_conhecida[:, transicoes] <= e).any(axis=1) & \
                ~quebra[:, janela].any(axis=1)
        if not ok.any():
            continue
        z = delta[np.ix_(np.flatnonzero(ok), transicoes)] / (c[None, :] * np.power(media[ok], THETA / 2)[:, None])
        instabilidade[ok, e] = z.std(axis=1, ddof=1)
        media_da_janela[ok, e] = media[ok]

    # Instabilidade (sinal 5): o índice de cada data comparado com os índices anteriores do mesmo porte (a média da janela). O
    # índice já é a oscilação dividida pela típica do porte: entre todas as faixas, ele é comparado como está.
    porte_da_janela = _portes(np.floor(media_da_janela))
    c_instabilidade = np.zeros((ORIGENS, n, t), dtype=np.int32)
    um = np.ones((n, t))
    for e in range(1, t):
        atuais = np.flatnonzero(np.isfinite(instabilidade[:, e]) & (porte_da_janela[:, e] >= 0))
        usavel = np.isfinite(instabilidade[:, :e]) & (porte_da_janela[:, :e] >= 0)
        if not atuais.size or not usavel.any():
            continue
        comparadas = reguas.comparar_com_o_passado(
            instabilidade[atuais, e], instabilidade[atuais, e], um[atuais, e], porte_da_janela[atuais, e],
            instabilidade[:, :e][usavel], instabilidade[:, :e][usavel], um[:, :e][usavel], porte_da_janela[:, :e][usavel],
            pior_e_menor=False)
        for origem in range(ORIGENS):
            c_instabilidade[origem, atuais, e] = comparadas[origem]

    for matriz in (pico, pico_conhecido, marca, marca_conhecida, salto, queda_grande, quebra, c_perda, patamar,
                   patamar_ano, afastamento, c_patamar, instabilidade, c_instabilidade, porte_da_janela, escala, relativa, regular,
                   porte, porte_do_patamar, intervalo):
        matriz.setflags(write=False)
    calibracao = Calibracao(versao=base.versao, pico=pico, pico_conhecido=pico_conhecido, marca=marca,
                            marca_conhecida=marca_conhecida, salto=salto, queda_grande=queda_grande, quebra=quebra,
                            c_perda=c_perda, patamar=patamar, patamar_ano=patamar_ano,
                            afastamento=afastamento, c_patamar=c_patamar, instabilidade=instabilidade,
                            c_instabilidade=c_instabilidade, porte_da_janela=porte_da_janela,
                            escala=escala, blocos=blocos, relativa=relativa, regular=regular, porte=porte,
                            porte_do_patamar=porte_do_patamar, intervalo=intervalo)
    if guardar:
        with _LOCK:
            _CALIBRACOES.clear()
            _CALIBRACOES[base.versao] = calibracao
    return calibracao


# --------------------------------------------------------------------------------------------- avaliação de um território
NIVEIS = tuple(chave for chave, _, _ in reguas.NIVEIS)   # do mais grave ao menos grave: critico, elevado, moderado
POR_CONVENCAO, COMPARADO = "por convenção", "comparado com a base"


def _num(valor):
    """Número JSON: inteiro quando é inteiro, float senão; None para ausente."""
    if valor is None or valor != valor:
        return None
    valor = float(valor)
    return int(valor) if valor.is_integer() else valor


def _anterior_valido(serie: np.ndarray, e: int) -> int | None:
    for i in range(e - 1, -1, -1):
        if serie[i] == serie[i]:
            return i
    return None


def _ancora(base: Base) -> str:
    """O mês âncora da série anual da base ("06" na base do Brasil): o mês presente em todos os anos (perfil da base)."""
    return getattr(base, "ancora", None) or "06"


def _raridade(matriz: np.ndarray, linha: int, e: int, p: dict) -> dict:
    """O que a régua comum diz de uma avaliação: o nível que a raridade sustenta e, para cada nível, se pôde ser avaliado, com
    quantas comparações anteriores e quantas ele pede. `p` traz o "1 em cada N" de cada nível (`<nível>_um_em`)."""
    limites = {nivel: p[nivel + "_um_em"] for nivel in NIVEIS if nivel + "_um_em" in p}
    lida = reguas.nivel_da_raridade(*(int(valor) for valor in matriz[:, linha, e]), limites=limites)
    lida["niveis"] = {nivel: dados for nivel, dados in lida["niveis"].items() if nivel in limites}
    return lida


def _sem_comparacoes(raridade: dict) -> dict | None:
    """O nível mais grave que a base ainda não sustenta: quantas comparações há e quantas ele pede."""
    return reguas.sem_comparacoes(raridade)


def _classe_estrutural(n: int, p: dict) -> str | None:
    return "critico" if n <= p["critico"] else "elevado" if n <= p["elevado"] else "moderado" if n <= p["moderado"] else None


def _estrutural(base: Base, serie: np.ndarray, e: int, p: dict, com_nivel: bool) -> dict:
    """Sinais 1 e 2: poucos profissionais e nenhum profissional registrado, por convenção, com a duração do zero e a histerese
    (a piora aparece na hora; a melhora, depois de dois registros). Um conjunto não tem nível (`com_nivel` falso)."""
    if serie[e] != serie[e]:
        return {"estado": "ausencia_de_dado", "classe": None, "n": None}
    n = int(serie[e])
    do_valor = _classe_estrutural(n, p)
    ant = _anterior_valido(serie, e)
    da_anterior = _classe_estrutural(int(serie[ant]), p) if ant is not None else None
    exibida = do_valor if GRAVIDADE[do_valor] >= GRAVIDADE[da_anterior] else da_anterior
    zeros = 0
    inicio_do_zero = None
    for i in range(e, -1, -1):
        if serie[i] == 0:
            zeros, inicio_do_zero = zeros + 1, i
        else:
            break
    saida = {"n": n, "impacto_pct": (100.0 / n) if n > 0 else None, "zero_confirmado": n == 0,
             "classe_do_valor": do_valor if com_nivel else None,
             "classe": exibida if com_nivel else None, "mantida_pela_anterior": com_nivel and exibida != do_valor,
             "criterio": POR_CONVENCAO,
             "anterior": None if ant is None else {"competencia": base.periodos[ant], "n": int(serie[ant])},
             "zeros": None if not zeros else {"registros": zeros, "desde": base.periodos[inicio_do_zero],
                                             "meses": int(base.meses[e] - base.meses[inicio_do_zero])}}
    saida["estado"] = "nivel_sem_classificacao" if not com_nivel else "classificado" if exibida else "sem_sinal"
    return saida


def _perda(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, e: int, p: dict) -> dict:
    """Sinal 6: a queda de um registro para o seguinte. O fato sempre sai; o alerta exige que a queda seja rara na base (entre
    as mudanças anteriores de territórios do mesmo porte, com o mesmo tempo entre registros) e tenha um tamanho mínimo."""
    if serie[e] != serie[e]:
        return {"estado": "ausencia_de_dado", "classe": None}
    ant = _anterior_valido(serie, e)
    if ant is None:
        return {"estado": "janela_insuficiente", "classe": None}
    anterior, atual = int(serie[ant]), int(serie[e])
    delta = atual - anterior
    meses = int(base.meses[e] - base.meses[ant])
    fato = {"de": base.periodos[ant], "ate": base.periodos[e], "anterior": anterior, "atual": atual, "delta": delta,
            "pct": (100.0 * delta / anterior) if anterior > 0 else None, "meses": meses, "classe": None, "magnitude": None,
            "criterio": COMPARADO}
    marca = int(cal.marca[linha, e]) if cal is not None and ant == e - 1 else 0
    conhecida = marca and int(cal.marca_conhecida[linha, e]) <= e
    if delta >= 0:
        fato["estado"] = "descontinuidade_de_registro" if conhecida and marca in (1, 2, 4) else "sem_perda"
        if cal is not None and ant == e - 1 and bool(cal.salto[linha, e]) and not conhecida:
            fato["verificar_registro"] = "salto"
        if cal is not None and ant == e - 1 and anterior >= 1 and fato["estado"] == "sem_perda":
            # Sem queda, a tela ainda diz que níveis a base sustenta para o porte (o crítico, de 3.000 para cima, não); e o
            # território conta como comparado com a base quando a régua tinha comparações para ele (`avaliavel`).
            raridade = _raridade(cal.c_perda, linha, e, p)
            fato["porte"] = porte_de(anterior)
            fato["sem_comparacoes"] = _sem_comparacoes(raridade)
            fato["avaliavel"] = any(dados["avaliado"] for dados in raridade["niveis"].values())
        return fato
    queda = -delta
    minimos = {nivel: max(p[nivel + "_minimo"], math.ceil(p[nivel + "_fracao"] / 100.0 * anterior)) for nivel in NIVEIS}
    # O maior nível cujo tamanho mínimo a queda alcança (o tamanho sozinho não é alerta: falta a raridade).
    fato["magnitude"] = next((nivel for nivel in NIVEIS if queda >= minimos[nivel]), None)
    fato["minimos"] = minimos
    fato["porte"] = porte_de(anterior)
    if conhecida:
        # A volta de um pico (ou a transição de uma quebra de fonte) não é perda: o fato aparece, com a marca, sem alerta.
        fato["estado"] = "descontinuidade_de_registro"
        fato["descontinuidade"] = "quebra_de_fonte" if marca == 4 else "pico_que_volta"
        return fato
    if cal is not None and ant == e - 1 and bool(cal.queda_grande[linha, e]):
        fato["verificar_registro"] = "queda"
    if cal is None:
        fato["estado"] = "nivel_sem_classificacao"
        return fato
    if ant != e - 1 or anterior < 1:
        fato["estado"], fato["motivo"] = "sem_comparacoes", "registro_anterior_ausente" if ant != e - 1 else "anterior_em_zero"
        return fato
    raridade = _raridade(cal.c_perda, linha, e, p)
    fato["raridade"] = {**raridade, "intervalo_meses": meses}
    fato["sem_comparacoes"] = _sem_comparacoes(raridade)
    # O nível é o mais grave em que a queda é rara (com comparações bastantes) e tem o tamanho mínimo daquele nível.
    nivel = next((chave for chave in NIVEIS if raridade["niveis"].get(chave, {}).get("avaliado")
                  and raridade["niveis"][chave]["atingido"] and queda >= minimos[chave]), None)
    if nivel:
        fato["estado"], fato["classe"] = "alerta", nivel
    elif not any(dados["avaliado"] for dados in raridade["niveis"].values()):
        fato["estado"], fato["motivo"] = "sem_comparacoes", "poucas_comparacoes"
    elif fato["magnitude"] is None:
        fato["estado"], fato["motivo"] = "perda_observada", "tamanho_abaixo"
    else:
        fato["estado"], fato["motivo"] = "perda_observada", "comum_para_o_porte"
    return fato


def _patamar_da_serie(base: Base, blocos: tuple, serie: np.ndarray, e: int) -> tuple[float | None, int | None]:
    """O patamar de uma série fora da calibração (conjunto): o mesmo cálculo, na própria série."""
    melhor, ano_do_melhor = None, None
    for ano, indices, fim in blocos:
        if fim > e - 4:
            continue
        valores = serie[list(indices)]
        if np.isnan(valores).any():
            continue
        media = float(valores.mean())
        if melhor is None or media > melhor:
            melhor, ano_do_melhor = media, ano
    return melhor, ano_do_melhor


def _patamar(base: Base, cal: Calibracao | None, blocos: tuple, linha: int | None, serie: np.ndarray, e: int, p: dict) -> dict:
    """Sinal 7: abaixo do que já teve — a distância ao patamar (a maior média de dois anos completos, antes dos 4 últimos
    registros). Moderado por convenção (os 2 últimos registros abaixo do limite); elevado e crítico, com a raridade na base."""
    if serie[e] != serie[e]:
        return {"estado": "ausencia_de_dado", "classe": None}
    if cal is not None:
        patamar = float(cal.patamar[linha, e]) if math.isfinite(float(cal.patamar[linha, e])) else None
        ano = int(cal.patamar_ano[linha, e]) if patamar is not None else None
    else:
        patamar, ano = _patamar_da_serie(base, blocos, serie, e)
    if patamar is None:
        return {"estado": "janela_insuficiente", "classe": None}
    atual = float(serie[e])
    bloco = next(indices for inicio, indices, _ in blocos if inicio == ano)
    saida = {"patamar": patamar, "bloco": {"de": base.periodos[min(bloco)], "ate": base.periodos[max(bloco)]}, "atual": int(atual),
             "diferenca": atual - patamar, "diferenca_pct": (100.0 * (atual - patamar) / patamar) if patamar > 0 else None,
             "classe": None, "criterio": POR_CONVENCAO}
    if patamar <= 0:
        saida["estado"] = "nao_calculavel"
        return saida
    limite_moderado, limite_critico = (1 - p["moderado"] / 100.0) * patamar, (1 - p["critico"] / 100.0) * patamar
    ultimos = [serie[i] for i in range(max(0, e - 3), e + 1)]
    dois = ultimos[-2:]
    abaixo_2 = len(dois) == 2 and all(v == v and v <= limite_moderado for v in dois)
    abaixo_4 = len(ultimos) == 4 and all(v == v and v <= limite_critico for v in ultimos)
    # Há quantos registros seguidos o território está abaixo do limite do moderado.
    duracao = 0
    for i in range(e, -1, -1):
        if serie[i] == serie[i] and serie[i] <= limite_moderado:
            duracao += 1
        else:
            break
    fim_do_bloco = max(bloco)
    depois = [(i, serie[i]) for i in range(fim_do_bloco + 1, e + 1) if serie[i] == serie[i]]
    if depois:
        indice_do_vale, vale = min(depois, key=lambda par: (par[1], par[0]))
        saida["vale"] = {"competencia": base.periodos[indice_do_vale], "valor": int(vale)}
        if vale < atual < patamar and indice_do_vale < e:
            saida["recuperado_pct"] = 100.0 * (atual - vale) / (patamar - vale)
    saida.update({"abaixo_por_2": abaixo_2, "abaixo_por_4": abaixo_4, "registros_abaixo": duracao,
                  "afastamento_pct": None if len(dois) < 2 or any(v != v for v in dois) else 100.0 * (1 - float(max(dois)) / patamar)})
    if cal is None:
        saida["estado"] = "nivel_sem_classificacao"
        return saida
    if cal.quebra[linha, max(0, e - 3):e + 1].any() or (cal.pico_conhecido[linha, max(0, e - 1):e + 1] <= e).any():
        saida["estado"] = "descontinuidade_de_registro"
        return saida
    if patamar < p["minimo"]:
        saida["estado"] = "descritivo"
        return saida
    if not abaixo_2:
        saida["estado"] = "sem_sinal"
        return saida
    raridade = _raridade(cal.c_patamar, linha, e, p)
    saida["raridade"] = raridade
    saida["sem_comparacoes"] = _sem_comparacoes(raridade)
    atingido = {nivel: bool(dados["avaliado"] and dados["atingido"]) for nivel, dados in raridade["niveis"].items()}
    saida["estado"], saida["classe"] = "classificado", "moderado"
    if atingido.get("elevado"):
        saida["classe"], saida["criterio"] = "elevado", COMPARADO
    if abaixo_4 and atingido.get("critico"):
        saida["classe"], saida["criterio"] = "critico", COMPARADO
    return saida


def _anuais(base: Base, inicio: int, e: int) -> list[int]:
    """Os registros do mês âncora (a série anual) da janela."""
    ancora = _ancora(base)
    return [i for i in range(inicio, e + 1) if base.periodos[i].endswith(ancora)]


_junhos = _anuais   # o nome antigo, da base do Brasil


def _declinio(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, inicio: int, e: int, p: dict) -> dict:
    """Sinal 3: declínio persistente — quedas anuais seguidas, com a perda medida desde o primeiro valor da sequência. Os níveis
    são por convenção."""
    anuais = _anuais(base, inicio, e)
    if len(anuais) < 2:
        return {"estado": "janela_insuficiente", "classe": None}
    def valor(i):
        if serie[i] != serie[i] or (cal is not None and int(cal.pico_conhecido[linha, i]) <= e):
            return None  # ausente ou registro de pico: fora da sequência
        return float(serie[i])
    ultimo = anuais[-1]
    if valor(ultimo) is None:
        return {"estado": "ausencia_de_dado", "classe": None, "ate": base.periodos[ultimo]}
    reducoes, posicao = 0, len(anuais) - 1
    while posicao > 0:
        atual, antes = valor(anuais[posicao]), valor(anuais[posicao - 1])
        consecutivos = int(base.periodos[anuais[posicao]][:4]) - int(base.periodos[anuais[posicao - 1]][:4]) == 1
        if atual is None or antes is None or not consecutivos or not atual < antes:
            break
        reducoes, posicao = reducoes + 1, posicao - 1
    primeiro = anuais[posicao]
    saida = {"reducoes": reducoes, "de": base.periodos[primeiro], "ate": base.periodos[ultimo], "junhos": len(anuais),
             "inicial": _num(valor(primeiro)), "final": _num(valor(ultimo)), "classe": None, "criterio": POR_CONVENCAO}
    if not reducoes:
        saida["estado"] = "sem_sinal"
        return saida
    perda = 100.0 * (1 - valor(ultimo) / valor(primeiro))
    saida["perda_pct"] = perda
    saida["classe"] = next((nivel for nivel in NIVEIS if reducoes >= p[nivel + "_quedas"] and perda >= p[nivel + "_perda"] - 1e-9), None)
    saida["estado"] = "classificado" if saida["classe"] else "reducao_observada"
    return saida


def _classe_dos_anuais(base: Base, serie: np.ndarray, ultimo: int) -> tuple[str | None, list[int]]:
    """A classe da Análise de Tendência (CAP-TEN-01) nos 4 registros anuais que terminam em `ultimo`; None sem os 4 registros."""
    ano, mes = int(base.periodos[ultimo][:4]), base.periodos[ultimo][4:]
    indices = []
    for passo in range(3, -1, -1):
        chave = str(ano - passo) + mes
        if chave not in base.periodos:
            return None, []
        indices.append(base.periodos.index(chave))
    if any(serie[i] != serie[i] for i in indices):
        return None, indices
    # As velocidades exatas (Δy, Δt), como pares de inteiros: a mesma função da Análise de Tendência (trend.classify_pairs, o
    # caminho em massa de classify_frame), sem regra paralela.
    velocidades = [(int(serie[b]) - int(serie[a]), int(base.meses[b] - base.meses[a])) for a, b in zip(indices, indices[1:])]
    return classify_pairs(velocidades)[0], indices


_classe_dos_junhos = _classe_dos_anuais   # o nome antigo, da base do Brasil


def _desaceleracao(base: Base, serie: np.ndarray, e: int, p: dict, com_nivel: bool = True) -> dict:
    """Sinal 4: desaceleração — a classe "Crescimento desacelerado" da Análise de Tendência nos 4 registros anuais até o último.
    Moderado, por convenção e exploratório, quando a classe se repete em anos seguidos: mostra uma mudança de ritmo e não
    indica o que vem depois."""
    anuais = _anuais(base, 0, e)
    if not anuais:
        return {"estado": "janela_insuficiente", "classe": None}
    ultimo = anuais[-1]
    categoria, indices = _classe_dos_anuais(base, serie, ultimo)
    if categoria is None:
        return {"estado": "janela_insuficiente" if not indices else "ausencia_de_dado", "classe": None,
                "ate": base.periodos[ultimo]}
    saida = {"de": base.periodos[indices[0]], "ate": base.periodos[ultimo], "tendencia": categoria,
             "rotulo": ROTULOS_DA_TENDENCIA[categoria], "valores": [int(serie[i]) for i in indices], "classe": None,
             "desacelera": categoria == "CRESCIMENTO_DESACELERADO", "persistente": None, "anos": 0,
             "criterio": POR_CONVENCAO, "exploratorio": True}
    if saida["desacelera"]:
        seguidos, posicao = 1, len(anuais) - 2
        while posicao >= 0 and _classe_dos_anuais(base, serie, anuais[posicao])[0] == "CRESCIMENTO_DESACELERADO":
            seguidos, posicao = seguidos + 1, posicao - 1
        saida["anos"] = seguidos
        saida["persistente"] = seguidos >= 2
        if com_nivel and seguidos >= p["anos"]:
            saida["classe"] = "moderado"
    saida["estado"] = "classificado" if saida["classe"] else "sinal_observado" if saida["desacelera"] else "sem_sinal"
    return saida


def _instabilidade(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, e: int, p: dict) -> dict:
    """Sinal 5: instabilidade — a oscilação dos 7 últimos registros dividida pela típica do porte (1 = a típica). Moderado quando
    o índice é raro na base, entre os índices anteriores de territórios do mesmo porte."""
    if e < REGISTROS_DA_INSTABILIDADE - 1:
        return {"estado": "janela_insuficiente", "classe": None}
    janela = serie[e - REGISTROS_DA_INSTABILIDADE + 1:e + 1]
    if np.isnan(janela).any():
        return {"estado": "ausencia_de_dado", "classe": None}
    media = float(janela.mean())
    variacoes = np.diff(janela)
    saida = {"registros": REGISTROS_DA_INSTABILIDADE, "de": base.periodos[e - REGISTROS_DA_INSTABILIDADE + 1],
             "ate": base.periodos[e], "media": media, "classe": None, "criterio": COMPARADO,
             "inversoes": int(np.sum(np.sign(variacoes[1:]) * np.sign(variacoes[:-1]) < 0))}
    if media < MEDIA_MINIMA_DA_INSTABILIDADE:
        saida["estado"] = "nao_calculavel"
        return saida
    if cal is None:
        saida["estado"] = "nivel_sem_classificacao"
        return saida
    indice = float(cal.instabilidade[linha, e])
    if not math.isfinite(indice):
        marcada = (cal.marca_conhecida[linha, e - REGISTROS_DA_INSTABILIDADE + 2:e + 1] <= e).any() or \
            cal.quebra[linha, e - REGISTROS_DA_INSTABILIDADE + 1:e + 1].any()
        saida["estado"] = "descontinuidade_de_registro" if marcada else "nao_calculavel"
        return saida
    saida["indice"] = indice
    saida["porte"] = int(cal.porte_da_janela[linha, e]) if int(cal.porte_da_janela[linha, e]) >= 0 else None
    raridade = _raridade(cal.c_instabilidade, linha, e, p)
    saida["raridade"] = raridade
    saida["sem_comparacoes"] = _sem_comparacoes(raridade)
    moderado = raridade["niveis"]["moderado"]
    if not moderado["avaliado"]:
        saida["estado"] = "sem_comparacoes"
    elif moderado["atingido"]:
        saida["estado"], saida["classe"] = "classificado", "moderado"
    else:
        saida["estado"] = "sem_sinal"
    return saida


def _registro(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, inicio: int, e: int) -> dict:
    """A qualidade do registro na janela: normal, "verificar registro" ou descontinuidade de registro, com os eventos."""
    if cal is None:
        return {"estado": "normal", "eventos": []}
    eventos = []
    i = max(inicio, 1)
    while i <= e:
        marca, conhecida = int(cal.marca[linha, i]), int(cal.marca_conhecida[linha, i]) <= e
        if marca == 1 and conhecida:
            volta = int(cal.marca_conhecida[linha, i])
            eventos.append({"tipo": "pico_que_volta", "de": base.periodos[i - 1], "em": base.periodos[i],
                            "ate": base.periodos[volta], "valores": [_num(serie[k]) for k in range(i - 1, volta + 1)]})
        elif marca == 4:
            pass  # a quebra de fonte entra abaixo, pelos registros em quebra
        elif bool(cal.salto[linha, i]) and not (marca == 1 and conhecida):
            eventos.append({"tipo": "salto", "de": base.periodos[i - 1], "em": base.periodos[i],
                            "valores": [_num(serie[i - 1]), _num(serie[i])]})
        elif bool(cal.queda_grande[linha, i]) and not (marca in (2, 3) and conhecida):
            eventos.append({"tipo": "queda_grande", "de": base.periodos[i - 1], "em": base.periodos[i],
                            "valores": [_num(serie[i - 1]), _num(serie[i])]})
        i += 1
    i = inicio
    while i <= e:
        if bool(cal.quebra[linha, i]):
            fim = i
            while fim + 1 <= e and bool(cal.quebra[linha, fim + 1]):
                fim += 1
            eventos.insert(0, {"tipo": "quebra_de_fonte", "de": base.periodos[i], "ate": base.periodos[fim]})
            i = fim + 1
        else:
            i += 1
    estado = "descontinuidade_de_registro" if any(ev["tipo"] in ("pico_que_volta", "quebra_de_fonte") for ev in eventos) else \
        "verificar_registro" if eventos else "normal"
    return {"estado": estado, "eventos": eventos}


# Os 12 sinais, na ordem do catálogo, com o grupo da tela (B.3) e as quedas que vêm do mesmo evento.
SINAIS = (("estrutural", "quantos"), ("ausencia", "quantos"), ("declinio", "mudou"), ("desaceleracao", "mudou"),
          ("instabilidade", "mudou"), ("perda", "mudou"), ("patamar", "mudou"), ("disponibilidade", "comparado"),
          ("posicao", "comparado"), ("defasagem", "comparado"), ("contexto", "onde"), ("combinados", "juntos"))
DA_MESMA_QUEDA = ("perda", "declinio", "patamar", "disponibilidade", "posicao", "defasagem")


def _alerta(situacao: dict, tipo: str) -> dict:
    """O alerta do território: um nível só, o maior entre os seus sinais, sem soma nem índice. Os sinais que vêm da mesma queda
    contam como um evento. Um conjunto não tem nível: não há outros iguais para comparar."""
    if tipo == "conjunto":
        return {"estado": "sem_nivel", "nivel": None, "sinal": None, "criterio": None, "sinais": [], "outros": 0, "eventos": 0,
                "motivo": "Um conjunto não tem outros iguais para comparar: a tela mostra os fatos, sem nível."}
    com_nivel = []
    for chave in ("estrutural", "declinio", "desaceleracao", "instabilidade", "perda", "patamar", "disponibilidade", "posicao",
                  "defasagem"):
        sinal = situacao.get(chave) or {}
        if sinal.get("classe"):
            nome = "ausencia" if chave == "estrutural" and sinal.get("zero_confirmado") else chave
            com_nivel.append({"sinal": nome, "nivel": sinal["classe"], "criterio": sinal.get("criterio") or POR_CONVENCAO})
    com_nivel.sort(key=lambda item: -GRAVIDADE[item["nivel"]])
    quedas = [item for item in com_nivel if item["sinal"] in DA_MESMA_QUEDA]
    eventos = len(com_nivel) - max(len(quedas) - 1, 0)
    if com_nivel:
        principal = com_nivel[0]
        return {"estado": "alerta", "nivel": principal["nivel"], "sinal": principal["sinal"], "criterio": principal["criterio"],
                "sinais": com_nivel, "outros": len(com_nivel) - 1, "eventos": eventos,
                "mesma_queda": [item["sinal"] for item in quedas] if len(quedas) > 1 else []}
    comparados = ("perda", "instabilidade", "patamar", "disponibilidade", "posicao", "defasagem")
    faltam = [chave for chave in comparados if (situacao.get(chave) or {}).get("estado") == "sem_comparacoes"]
    # "Sem comparações suficientes" é do território quando nenhum sinal comparado com a base pôde ser avaliado; se algum pôde (e
    # não é raro), o território fica sem alerta, e os sinais sem comparações aparecem nos detalhes. Quem não caiu no último
    # registro também foi comparado, quando a régua tinha comparações para o porte dele.
    avaliados = [chave for chave in comparados if (situacao.get(chave) or {}).get("avaliavel")
                 or any(dados.get("avaliado") for dados in (((situacao.get(chave) or {}).get("raridade") or {}).get("niveis") or {}).values())]
    return {"estado": "sem_comparacoes" if faltam and not avaliados else "sem_alerta", "nivel": None, "sinal": None, "criterio": None,
            "sinais": [], "outros": 0, "eventos": 0, "sem_comparacoes": faltam, "mesma_queda": []}


def avaliar(base: Base, cal: Calibracao, territorio: Territorio, inicio: int, e: int, p: dict, inicio_da_janela: int | None = None,
            comparar: bool = True, cal_dos_estados: Calibracao | None = None) -> dict:
    """A situação de um território na data `e` (a mais recente da janela), sinal a sinal. `inicio` é o começo da janela dos
    indicadores (depois de uma quebra de fonte); `inicio_da_janela`, o da janela pedida, para a qualidade do registro. Com
    `comparar`, entram os sinais 8 a 12 (comparativos.py); o histórico de sinais avalia só os sinais 1 a 7.

    A régua é a do nível do território: a dos municípios (`cal`) ou a dos estados como unidade (`cal_dos_estados`, com a base dos
    estados). Um conjunto não tem régua: saem os fatos, sem nível."""
    municipal, estadual = territorio.tipo == "municipio", territorio.tipo == "estado"
    serie = territorio.serie
    if municipal:
        calibracao, linha = cal, territorio.linha
    elif estadual and cal_dos_estados is not None:
        calibracao, linha = cal_dos_estados, sorted(base.estados).index(territorio.uf)
    else:
        calibracao, linha = None, None
    com_nivel = territorio.tipo != "conjunto"
    ultima = next((i for i in range(e, -1, -1) if serie[i] == serie[i]), None)
    situacao = {
        "estrutural": _estrutural(base, serie, e, p["estrutural"], com_nivel),
        "perda": _perda(base, calibracao, linha, serie, e, p["perda"]),
        "patamar": _patamar(base, calibracao, cal.blocos, linha, serie, e, p["patamar"]),
        "declinio": _declinio(base, calibracao, linha, serie, inicio, e, p["declinio"]),
        "desaceleracao": _desaceleracao(base, serie, e, p["desaceleracao"], com_nivel),
        "instabilidade": _instabilidade(base, calibracao, linha, serie, e, p["instabilidade"]),
        "registro": _registro(base, calibracao, linha, serie, inicio if inicio_da_janela is None else inicio_da_janela, e),
    }
    if not com_nivel:
        situacao["declinio"]["classe"] = None   # o conjunto mostra os fatos, sem nível
    # Campos que a resposta já trazia (V22), com os valores da V3: o `sinal` do declínio repete o nível; `critica`, no sinal 7, diz
    # quando os 4 últimos registros cumprem o limite do crítico, mas a base não tem comparações para ele.
    situacao["declinio"]["sinal"] = situacao["declinio"].get("classe")
    do_critico = ((situacao["patamar"].get("raridade") or {}).get("niveis") or {}).get("critico") or {}
    situacao["patamar"]["critica"] = "sem_comparacoes" if situacao["patamar"].get("abaixo_por_4") and do_critico and \
        not do_critico.get("avaliado") else None
    sinais = []
    if situacao["estrutural"].get("classe"):
        sinais.append("estrutural")
    if situacao["estrutural"].get("zero_confirmado"):
        sinais.append("ausencia")
    if situacao["perda"].get("delta", 0) < 0 and situacao["perda"]["estado"] != "descontinuidade_de_registro":
        sinais.append("perda")
    if situacao["perda"].get("classe"):
        sinais.append("alerta_perda")
    if situacao["patamar"].get("abaixo_por_2") and situacao["patamar"]["estado"] != "descontinuidade_de_registro":
        sinais.append("patamar")
    if situacao["declinio"].get("reducoes", 0) >= p["declinio"]["moderado_quedas"]:
        sinais.append("declinio")
    if situacao["desaceleracao"].get("desacelera"):
        sinais.append("desaceleracao")
    if situacao["instabilidade"].get("classe"):
        sinais.append("instabilidade")
    if situacao["registro"]["estado"] != "normal":
        sinais.append("registro")
    if comparar:
        qd = comparativos.quadro(base, e, p)
        situacao["disponibilidade"] = comparativos.disponibilidade(base, qd, territorio, p)
        situacao["posicao"] = comparativos.posicao(base, qd, territorio, p)
        situacao["defasagem"] = comparativos.defasagem(base, qd, territorio, p)
        situacao["contexto"] = comparativos.contexto(base, qd, territorio)
        for chave in ("disponibilidade", "posicao", "defasagem"):
            situacao[chave]["sinal"] = situacao[chave].get("classe")   # o campo anterior, com o nível da V3
        sinais += [chave for chave in ("disponibilidade", "posicao", "defasagem") if situacao[chave].get("classe")]
        situacao["coexistencia"] = comparativos.coexistencia(sinais, situacao["estrutural"].get("classe"))
        if situacao["coexistencia"]["combinacoes"]:
            sinais.append("combinados")
    alerta = _alerta(situacao, territorio.tipo)
    dimensoes = {
        "estrutural": situacao["estrutural"].get("classe"),
        "trajetoria": max((situacao["perda"].get("classe"), situacao["patamar"].get("classe"), situacao["declinio"].get("classe")),
                          key=lambda c: GRAVIDADE[c]),
        "ritmo": max((situacao["desaceleracao"].get("classe"), situacao["instabilidade"].get("classe")), key=lambda c: GRAVIDADE[c]),
        "comparacao": max(((situacao.get(chave) or {}).get("classe") for chave in ("disponibilidade", "posicao", "defasagem")),
                          key=lambda c: GRAVIDADE[c]) if comparar else None,
        "contexto": None,    # 11: só contexto
    }
    return {
        "id": territorio.id, "tipo": territorio.tipo, "nivel": territorio.nivel, "rotulo": territorio.rotulo,
        "uf": STATES[territorio.uf][0] if territorio.uf else None, "unidade": territorio.unidade,
        "ultima": None if ultima is None else {"competencia": base.periodos[ultima], "valor": int(serie[ultima]),
                                               "na_data": ultima == e},
        "porte": porte_de(serie[ultima]) if ultima is not None else None,
        **situacao, "sinais": sinais, "dimensoes": dimensoes, "alerta": alerta,
        **({"membros": list(territorio.membros), "nomes_dos_membros": list(territorio.nomes_dos_membros),
            "versao": territorio.versao} if territorio.tipo == "conjunto" else {}),
    }


# --------------------------------------------------------------------------------------------- a régua de uma data
def _limite_da_raridade(ordenados: np.ndarray, um_em: float):
    """O valor a partir do qual uma mudança nova é rara: com n mudanças anteriores em ordem crescente, a raridade (k + 1) ÷
    (n + 1) fica em 1 em cada N ou menos quando no máximo ⌊(n + 1) ÷ N⌋ − 1 delas são iguais ou piores. Devolve o valor de
    corte (a mudança precisa ser pior que ele) ou None, sem comparações bastantes."""
    n = ordenados.size
    maximo = int(math.floor((n + 1) / um_em + 1e-12)) - 1
    if maximo < 0 or maximo >= n:
        return None
    return float(ordenados[maximo])


def limiares(base: Base, cal: Calibracao, e: int, p: dict) -> dict:
    """O que a régua diz na data `e`, para a tela explicar: por faixa de porte, quantas mudanças anteriores há (com o mesmo tempo
    entre registros) e a partir de que queda ela é rara em cada nível; e, no sinal 7, a partir de que afastamento."""
    perda, patamar = p["perda"], p["patamar"]
    meses = int(cal.intervalo[e]) if e > 0 else None
    celulas = []
    if e > 0 and meses:
        colunas = [i for i in range(1, e) if int(cal.intervalo[i]) == meses]
        if colunas:
            usavel = cal.regular[:, colunas] & ~(cal.marca_conhecida[:, colunas] <= e)
            valores, faixas = cal.relativa[:, colunas][usavel], cal.porte[:, colunas][usavel]
        else:
            valores, faixas = np.empty(0), np.empty(0, dtype=np.int8)
        for faixa, rotulo in enumerate(ROTULOS_DOS_PORTES):
            anteriores = np.sort(valores[faixas == faixa])
            celula = {"porte": rotulo, "comparacoes": int(anteriores.size)}
            for nivel in NIVEIS:
                um_em = perda[nivel + "_um_em"]
                corte = _limite_da_raridade(anteriores, um_em)
                celula[nivel] = {"um_em": um_em, "pede": max(int(math.ceil(um_em)) - 1, 1),
                                 "queda_pct": None if corte is None else -100.0 * corte + 0.0}
            # As chaves que a resposta já trazia: as transições anteriores e o corte dos dois níveis mais graves.
            celula.update({"transicoes": celula["comparacoes"], "queda_incomum_pct": celula["elevado"]["queda_pct"],
                           "queda_muito_incomum_pct": celula["critico"]["queda_pct"],
                           "alta": "calibrado" if celula["elevado"]["queda_pct"] is not None else "sem_calibracao",
                           "critica": "calibrado" if celula["critico"]["queda_pct"] is not None else "sem_calibracao"})
            celulas.append(celula)
    faixas_do_patamar = []
    if e > 0:
        usavel = np.isfinite(cal.afastamento[:, :e])
        com_pico = (cal.pico_conhecido[:, :e] <= e)
        if e > 1:
            com_pico[:, 1:] |= (cal.pico_conhecido[:, :e - 1] <= e)
        usavel &= ~com_pico & ~cal.quebra[:, :e]
        valores, faixas = cal.afastamento[:, :e][usavel], cal.porte_do_patamar[:, :e][usavel]
        for faixa, rotulo in enumerate(ROTULOS_DOS_PORTES):
            if PORTES[faixa][1] is not None and PORTES[faixa][1] < patamar["minimo"]:
                continue
            anteriores = np.sort(-valores[faixas == faixa])  # o maior afastamento é o pior: a cauda de baixo do oposto
            celula = {"porte": rotulo, "comparacoes": int(anteriores.size)}
            for nivel in ("critico", "elevado"):
                um_em = patamar[nivel + "_um_em"]
                corte = _limite_da_raridade(anteriores, um_em)
                celula[nivel] = {"um_em": um_em, "pede": max(int(math.ceil(um_em)) - 1, 1),
                                 "afastamento_pct": None if corte is None else -100.0 * corte + 0.0}
            celula.update({"observacoes": celula["comparacoes"], "afastamento_incomum_pct": celula["elevado"]["afastamento_pct"],
                           "alta": "calibrado" if celula["elevado"]["afastamento_pct"] is not None else "sem_calibracao",
                           "critica": "calibrado" if celula["critico"]["afastamento_pct"] is not None else "sem_calibracao"})
            faixas_do_patamar.append(celula)
    # O aviso da base (B.1): numa mesma data, muitas quedas raras juntas (mais que o triplo do esperado) podem vir de uma
    # mudança no registro da base, e não nos territórios.
    avaliadas, raras = 0, 0
    if e > 0:
        k = np.where(cal.c_perda[1, :, e] >= 19, cal.c_perda[0, :, e], cal.c_perda[2, :, e])
        n = np.where(cal.c_perda[1, :, e] >= 19, cal.c_perda[1, :, e], cal.c_perda[3, :, e])
        k = np.where(n >= 19, k, cal.c_perda[4, :, e])
        n = np.where(n >= 19, n, cal.c_perda[5, :, e])
        com_regua = cal.regular[:, e] & (n >= 19)
        avaliadas = int(com_regua.sum())
        raras = int((com_regua & (reguas.raridade(k, n) <= 1.0 / 20.0 + 1e-12)).sum())
    esperado = 100.0 / 20.0
    taxa = (100.0 * raras / avaliadas) if avaliadas else None
    return {"competencia": base.periodos[e], "intervalo_meses": meses, "perda": celulas, "patamar": faixas_do_patamar,
            "monitoramento": {"avaliadas": avaliadas, "raras": raras, "incomuns": raras, "taxa_pct": taxa, "esperado_pct": esperado,
                              "aviso_da_base": bool(taxa is not None and avaliadas >= 100 and taxa > 3 * esperado)}}


# --------------------------------------------------------------------------------------------- textos determinísticos
MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro", "novembro", "dezembro")
NOMES_DAS_CLASSES = {"moderado": "moderado", "elevado": "elevado", "critico": "crítico"}
# Os 12 sinais (Proposta V3, tabela B.2), na ordem da tela: a chave, o número, o grupo (B.3) e a dimensão que a tabela já trazia.
FENOMENOS = (
    ("estrutural", "1–2", "quantos", "Condição estrutural"),
    ("declinio", "3", "mudou", "Trajetória"),
    ("desaceleracao", "4", "mudou", "Ritmo e instabilidade"),
    ("instabilidade", "5", "mudou", "Ritmo e instabilidade"),
    ("perda", "6", "mudou", "Trajetória"),
    ("patamar", "7", "mudou", "Trajetória"),
    ("disponibilidade", "8", "comparado", "Comparação relativa"),
    ("posicao", "9", "comparado", "Comparação relativa"),
    ("defasagem", "10", "comparado", "Comparação relativa"),
    ("contexto", "11", "onde", "Contexto geográfico"),
    ("coexistencia", "12", "juntos", "Coexistência"),
)
GRUPOS_DOS_SINAIS = (("quantos", "Quantos há"), ("mudou", "Como mudou"), ("comparado", "Comparado com outros"), ("onde", "Onde fica"),
                     ("juntos", "Juntos"))
NAO_SIGNIFICA_GERAL = ("Não diz que a população está sem atendimento, que o atendimento é insuficiente nem que há prioridade de "
                       "provimento. O nível do alerta descreve este sinal na base, não uma urgência assistencial.")
SEM_NIVEL_NO_CONJUNTO = ("Sem nível: um conjunto não tem outros iguais para comparar. O Detector mostra os fatos, e os níveis ficam "
                         "com os territórios que o compõem.")
INCOMUM_NAO_E_PIOR = "\"Raro\" quer dizer incomum nesta base, não comprovadamente pior."


def curta(competencia: str) -> str:
    """"jun/2024", como na tela."""
    return MESES_CURTOS[int(competencia[4:]) - 1] + "/" + competencia[:4]


def _br(valor, casas: int = 1) -> str:
    """Número em português: milhar com ponto, decimal com vírgula; inteiro sem casas."""
    if isinstance(valor, int) or float(valor).is_integer():
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _pct(valor, casas: int = 1) -> str:
    return f"{valor:.{casas}f}".replace(".", ",") + "%"


def _com_sinal(valor) -> str:
    return ("+" if valor > 0 else "−" if valor < 0 else "") + _br(abs(valor))


def _rotulos(base: Base) -> dict:
    """Os nomes da base (seção A.2.6): na base do Brasil, "médicos", "estado", "junho" e "Brasil"; numa planilha, os dela."""
    return series_brasil.rotulos(base)


def _profissionais(base: Base, n) -> str:
    r = _rotulos(base)
    return _br(n) + " " + (r["profissional"] if n == 1 else r["profissionais"])


def _medicos(n) -> str:
    """Na base do Brasil (o nome antigo, usado pelos textos de registro)."""
    return _br(n) + (" médico" if n == 1 else " médicos")


def _mes_ancora(base: Base) -> str:
    return MESES[int(_ancora(base)) - 1]


def _quem(base: Base, av: dict) -> str:
    r = _rotulos(base)
    return {"municipio": "o " + r["unidade"], "estado": "o " + r["grupo"], "conjunto": "o conjunto", "brasil": "o " + r["todo"]}[av["tipo"]]


def _os_parecidos(base: Base, av: dict) -> str:
    r = _rotulos(base)
    return r["grupos"] if av["tipo"] == "estado" else r["unidades"]


def _limitacoes(base: Base, av: dict) -> str:
    r = _rotulos(base)
    partes = [("O valor do conjunto é a " if av["tipo"] == "conjunto" else "A contagem é de ") + av["unidade"] + "."]
    partes.append("O registro mais recente da base é " + curta(base.periodos[-1]) + " e não descreve a situação de hoje.")
    if av["tipo"] == "conjunto":
        partes.append("No conjunto, a soma só existe nos registros em que todos os componentes têm valor.")
    if av["tipo"] == "estado":
        partes.append("O " + r["grupo"] + " como unidade é comparado com a base dos " + r["grupos"] + ", que é pequena: os níveis mais "
                      "graves podem não ter comparações suficientes.")
    return " ".join(partes)


def texto_do_registro(registro: dict) -> str:
    """A qualidade do registro em palavras: normal, "verificar registro" ou descontinuidade de registro."""
    if not registro["eventos"]:
        return "Sem marcas de registro na janela."
    partes = []
    for evento in registro["eventos"]:
        valores = " → ".join(_br(v) if v is not None else "sem registro" for v in evento.get("valores") or [])
        if evento["tipo"] == "pico_que_volta":
            partes.append("Descontinuidade de registro (pico que volta): de " + curta(evento["de"]) + " a " + curta(evento["ate"]) +
                          ", os valores foram " + valores + ". O pico não gera alerta na volta e fica fora da comparação com "
                          "territórios parecidos e dos cálculos de tendência.")
        elif evento["tipo"] == "quebra_de_fonte":
            partes.append("Descontinuidade de registro (quebra de fonte): de " + curta(evento["de"]) + " a " + curta(evento["ate"]) +
                          ", a soma municipal da UF ficou abaixo da contagem estadual de médicos únicos. Esse trecho fica fora da "
                          "comparação com territórios parecidos, e a janela dos indicadores começa depois dele.")
        elif evento["tipo"] == "salto":
            partes.append("Verificar registro: em " + curta(evento["em"]) + ", salto de 10 ou mais que ao menos dobrou a "
                          "contagem (" + valores + "). Se a contagem voltar em até dois registros, o trecho passa a "
                          "descontinuidade de registro.")
        else:
            partes.append("Verificar registro: em " + curta(evento["em"]) + ", queda de 10 ou mais que levou a contagem à "
                          "metade ou menos (" + valores + "). Pode ser mudança real ou falha do registro; a queda continua "
                          "valendo para os alertas.")
    return " ".join(partes)


def _um_em(valor) -> str:
    return "1 em cada " + _br(valor)


def _porte_em_palavras(base: Base, av: dict, faixa: int | None) -> str:
    """"municípios de 20 a 49 médicos": com quem o território foi comparado."""
    r = _rotulos(base)
    return _os_parecidos(base, av) + ("" if faixa is None else " de " + ROTULOS_DOS_PORTES[faixa] + " " + r["profissionais"])


def _comparado_com(base: Base, av: dict, raridade: dict | None, faixa: int | None, o_que: str) -> str:
    """A frase de "com quem foi comparado e quantos casos havia" (seção A.2.5), com a raridade lida."""
    if not raridade or raridade.get("comparacoes") is None:
        return ""
    origem = {"porte": _porte_em_palavras(base, av, faixa),
              "vizinhas": _porte_em_palavras(base, av, faixa) + " e das duas faixas de porte vizinhas (faltavam comparações só nessa faixa)",
              "todas": _os_parecidos(base, av) + " de todos os portes, com a mudança ajustada ao tamanho (faltavam comparações de porte "
                       "parecido)"}[raridade["origem"]]
    quantas = int(round(raridade["raridade"] * (raridade["comparacoes"] + 1))) - 1
    return ("Comparado com a base: entre " + _br(raridade["comparacoes"]) + " " + o_que + " de " + origem + ", " +
            ("nenhuma foi igual ou pior" if quantas <= 0 else _br(quantas) + (" foi igual ou pior" if quantas == 1 else " foram iguais ou piores")) +
            " (raridade de " + _um_em(max(round(1 / raridade["raridade"]), 1)) + ").")


def _falta_historia(falta: dict | None, o_que: str) -> str:
    """"A base ainda não tem história para dizer se esta queda chega ao nível elevado ou crítico: são 54 comparações, e o elevado
    pede 99."""
    if not falta:
        return ""
    nomes = [NOMES_DAS_CLASSES[nivel] for nivel in falta["niveis"]]
    quais = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " ou " + nomes[-1]
    return ("A base ainda não tem história para dizer se " + o_que + " chega ao nível " + quais + ": são " + _br(falta["comparacoes"]) +
            " comparações, e o " + NOMES_DAS_CLASSES[falta["nivel"]] + " pede " + _br(falta["pede"]) + ".")


def _item(nivel, estado, criterio, frase, observado, regra, habitual, significa, nao_significa, entenda, exemplo, exploratorio=False) -> dict:
    """Um sinal na tela: o nível, uma frase, o "Entenda" (duas ou três frases e um exemplo com números) e a explicação completa
    (os sete campos que a resposta já trazia)."""
    return {"nivel": nivel, "estado_do_nivel": estado, "criterio_do_nivel": criterio, "situacao": frase,
            "entenda": {"texto": entenda, "exemplo": exemplo}, "exploratorio": exploratorio,
            "observado": observado, "criterio": regra, "habitual": habitual, "significa": significa, "nao_significa": nao_significa}


def _estado_do_nivel(s: dict) -> str:
    """alerta | sem_alerta | sem_comparacoes | sem_nivel (conjunto) | sem_dado | nao_avaliado."""
    if s.get("classe"):
        return "alerta"
    estado = s.get("estado")
    if estado == "sem_comparacoes":
        return "sem_comparacoes"
    if estado == "nivel_sem_classificacao":
        return "sem_nivel"
    if estado in ("ausencia_de_dado", "janela_insuficiente"):
        return "sem_dado"
    if estado in ("descritivo", "nao_calculavel", "descontinuidade_de_registro", "comparacao_nao_habilitada", "referencia_invalida",
                  "nao_aplicavel"):
        return "nao_avaliado"
    return "sem_alerta"


def _texto_estrutural(base: Base, av: dict, e: int, p: dict) -> dict:
    s, limites, r = av["estrutural"], p["estrutural"], _rotulos(base)
    regra = ("Por convenção, pelo número de " + r["profissionais"] + " no último registro: " + str(limites["critico"]) + " ou nenhum, "
             "crítico; até " + str(limites["elevado"]) + ", elevado; até " + str(limites["moderado"]) + ", moderado; acima disso, "
             "sem alerta por este sinal. Vale a situação mais grave entre os dois últimos registros: a piora aparece na hora, e a "
             "melhora, depois de dois registros.")
    entenda = ("Com poucos " + r["profissionais"] + ", a saída de um só muda muito o total do território. Os limites são uma "
               "convenção, iguais para todos, e não uma comparação com a base.")
    exemplo = ("Com 2 " + r["profissionais"] + ", a saída de um reduz o total em 50%; com 20, em 5%.")
    if s["estado"] == "ausencia_de_dado":
        return _item(None, "sem_dado", POR_CONVENCAO, "Sem registro em " + curta(base.periodos[e]),
                     "Não há registro deste território em " + curta(base.periodos[e]) + ": ausência de dado, que não é o mesmo que zero.",
                     regra, "Não avaliável sem o registro.", "Falta o registro desta data.",
                     "Não quer dizer que o território ficou sem " + r["profissionais"] + ".", entenda, exemplo)
    n = s["n"]
    nenhum = "Nenhum " + r["profissional"] + " registrado"
    observado = "Em " + curta(base.periodos[e]) + ", " + _quem(base, av) + " tinha " + (_profissionais(base, n) if n else nenhum.lower())
    if s["anterior"]:
        observado += "; em " + curta(s["anterior"]["competencia"]) + ", " + _br(s["anterior"]["n"])
    observado += ". Contagem: " + av["unidade"] + "."
    frase = ("Só 1 " + r["profissional"]) if n == 1 else _profissionais(base, n) if n else nenhum
    if s.get("mantida_pela_anterior") and s["anterior"]:
        # O nível vem do registro anterior (a melhora só vale depois de dois registros): a frase diz de onde ele vem.
        frase += " (" + _br(s["anterior"]["n"]) + " no registro anterior)"
    if s["zeros"]:
        registros = s["zeros"]["registros"]
        desde = " há " + str(registros) + (" registro" if registros == 1 else " registros") + ", desde " + curta(s["zeros"]["desde"])
        observado += " Zero confirmado no registro" + desde + (" (" + str(s["zeros"]["meses"]) + " meses)." if s["zeros"]["meses"] else ".")
        frase += desde
    impacto = ("Com " + _profissionais(base, n) + ", a saída de um reduziria o número registrado em " +
               (_pct(s["impacto_pct"]) if s["impacto_pct"] >= 0.05 else "menos de 0,1%") + "."
               if n else "Com zero registrado, o efeito da saída de um não é calculável.")
    if s["estado"] == "nivel_sem_classificacao":
        habitual = SEM_NIVEL_NO_CONJUNTO + " " + impacto
    else:
        habitual = "Por convenção: o limite é o mesmo para todos os territórios, e não uma comparação com a base. " + impacto
        if s.get("mantida_pela_anterior"):
            habitual += " O nível exibido vem do registro anterior: a melhora só vale depois de dois registros seguidos."
    return _item(s.get("classe"), _estado_do_nivel(s), POR_CONVENCAO, frase, observado, regra, habitual,
                 "Com poucos " + r["profissionais"] + " registrados, cada saída pesa muito no total do território.",
                 NAO_SIGNIFICA_GERAL + " Mais " + r["profissionais"] + " que o limite também não querem dizer atendimento suficiente.",
                 entenda, exemplo)


def _texto_declinio(base: Base, av: dict, p: dict) -> dict:
    s, limites, r = av["declinio"], p["declinio"], _rotulos(base)
    mes = _mes_ancora(base)
    regra = ("Por convenção, pelas quedas seguidas na série anual (de " + mes + " a " + mes + ") e pela perda acumulada desde o início da "
             "sequência: " + str(limites["moderado_quedas"]) + " quedas e perda de " + _pct(limites["moderado_perda"], 0) + " ou mais, "
             "moderado; " + str(limites["elevado_quedas"]) + " quedas e " + _pct(limites["elevado_perda"], 0) + " ou mais, elevado; " +
             str(limites["critico_quedas"]) + " quedas e " + _pct(limites["critico_perda"], 0) + " ou mais, crítico. Registros de pico "
             "que volta ficam fora da sequência.")
    entenda = ("Olha a série de " + mes + " de cada ano e conta quantos anos seguidos o número caiu. Vira alerta quando as quedas se "
               "repetem e a perda somada é grande.")
    exemplo = "De 50 para 46, depois 42 e depois 38 " + r["profissionais"] + ": três quedas seguidas e perda de 24%, nível elevado."
    significa = "O número de " + r["profissionais"] + " vem caindo ano após ano, e não só num registro."
    nao = NAO_SIGNIFICA_GERAL + " Não diz por que caiu nem que vai continuar caindo."
    if s["estado"] in ("janela_insuficiente", "ausencia_de_dado"):
        motivo = "Faltam registros de " + mes + " para comparar." if s["estado"] == "janela_insuficiente" else \
            "Não há registro em " + curta(s["ate"]) + " (ausência de dado não é zero)."
        return _item(None, "sem_dado", POR_CONVENCAO, "Sem a série anual para avaliar", motivo, regra, "Não avaliável.", significa, nao,
                     entenda, exemplo)
    if not s["reducoes"]:
        return _item(None, _estado_do_nivel(s), POR_CONVENCAO, "Sem queda no último ano",
                     "Até " + curta(s["ate"]) + ", o número não caiu no último ano da série anual (de " + mes + " a " + mes + ").", regra,
                     "Por convenção. Sem quedas seguidas.", significa, nao, entenda, exemplo)
    quedas = str(s["reducoes"]) + (" queda anual" if s["reducoes"] == 1 else " quedas anuais seguidas")
    frase = quedas + ": −" + _pct(s["perda_pct"]) + " desde " + curta(s["de"])
    observado = ("De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", o número de " + r["profissionais"] + " caiu " + str(s["reducoes"]) +
                 (" vez" if s["reducoes"] == 1 else " anos seguidos") + ": de " + _br(s["inicial"]) + " para " + _br(s["final"]) + " (−" +
                 _pct(s["perda_pct"]) + ").")
    habitual = "Por convenção: os limites são os mesmos para todos os territórios." if av["tipo"] != "conjunto" else SEM_NIVEL_NO_CONJUNTO
    return _item(s.get("classe"), "sem_nivel" if av["tipo"] == "conjunto" else _estado_do_nivel(s), POR_CONVENCAO, frase, observado, regra,
                 habitual, significa, nao, entenda, exemplo)


def _texto_desaceleracao(base: Base, av: dict, p: dict) -> dict:
    s, r = av["desaceleracao"], _rotulos(base)
    mes = _mes_ancora(base)
    regra = ("A classe \"" + ROTULOS_DA_TENDENCIA["CRESCIMENTO_DESACELERADO"] + "\" da Análise de Tendência do Agente nos 4 registros de " +
             mes + " até o último. Moderado, por convenção e exploratório, quando a classe se repete em " + str(p["desaceleracao"]["anos"]) +
             " anos seguidos.")
    entenda = ("O número ainda cresce, mas cada ano cresce menos que o anterior. Este sinal mostra uma mudança de ritmo; não indica o "
               "que vem depois.")
    exemplo = "De 40 para 50, depois 56 e depois 59 " + r["profissionais"] + ": os aumentos foram de 10, 6 e 3."
    significa = "O crescimento perdeu ritmo nos últimos anos."
    nao = "Não é queda nem previsão de queda: num estudo com esta base, a repetição da classe não antecipou o crescimento seguinte. " + \
        NAO_SIGNIFICA_GERAL
    if s["estado"] in ("janela_insuficiente", "ausencia_de_dado"):
        return _item(None, "sem_dado", POR_CONVENCAO, "Sem os 4 registros anuais para avaliar",
                     "Faltam registros de " + mes + " nos 4 últimos anos.", regra, "Não avaliável.", significa, nao, entenda, exemplo, True)
    valores = " → ".join(_br(v) for v in s["valores"])
    observado = ("De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", os valores de " + mes + " foram " + valores + ". A Análise de "
                 "Tendência classifica essa série como \"" + s["rotulo"] + "\".")
    if not s["desacelera"]:
        return _item(None, "sem_alerta", POR_CONVENCAO, "Sem desaceleração (tendência: " + s["rotulo"].lower() + ")", observado, regra,
                     "Por convenção. A classe da série não é a de crescimento desacelerado.", significa, nao, entenda, exemplo, True)
    frase = "O crescimento perde ritmo" + (" há " + str(s["anos"]) + " anos" if s["anos"] >= 2 else "")
    habitual = ("Por convenção e exploratório: a classe se repete há " + str(s["anos"]) + " anos." if s["anos"] >= 2 else
                "Por convenção e exploratório: a classe apareceu só no último ano, ainda sem repetição.")
    if av["tipo"] == "conjunto":
        habitual = SEM_NIVEL_NO_CONJUNTO
    return _item(s.get("classe"), "sem_nivel" if av["tipo"] == "conjunto" else _estado_do_nivel(s), POR_CONVENCAO, frase, observado, regra,
                 habitual, significa, nao, entenda, exemplo, True)


def _texto_instabilidade(base: Base, av: dict, p: dict) -> dict:
    s, r = av["instabilidade"], _rotulos(base)
    um_em = p["instabilidade"]["moderado_um_em"]
    regra = ("A oscilação dos " + str(REGISTROS_DA_INSTABILIDADE) + " últimos registros dividida pela oscilação típica de territórios do "
             "mesmo porte (1 = a típica). Moderado quando o índice é raro na base: só " + _um_em(um_em) + " índices anteriores de "
             "territórios do mesmo porte foi igual ou maior, com pelo menos " + _br(max(um_em - 1, 1)) + " comparações.")
    entenda = ("Mede o quanto o número sobe e desce de um registro para o outro, comparado com o sobe e desce comum em territórios do "
               "mesmo tamanho. " + INCOMUM_NAO_E_PIOR)
    exemplo = "Índice 1: oscila como o comum. Índice 2,5: oscila duas vezes e meia o comum para o porte."
    significa = "A série é mais irregular que o comum para o porte."
    nao = "Não diz se o número está subindo ou caindo, nem o motivo da oscilação. " + NAO_SIGNIFICA_GERAL
    estado = s["estado"]
    if estado in ("janela_insuficiente", "ausencia_de_dado"):
        return _item(None, "sem_dado", COMPARADO, "Sem os " + str(REGISTROS_DA_INSTABILIDADE) + " registros para avaliar",
                     "Faltam registros na janela dos " + str(REGISTROS_DA_INSTABILIDADE) + " últimos.", regra, "Não avaliável.", significa,
                     nao, entenda, exemplo)
    janela = "De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", a média foi de " + _br(s["media"]) + " " + r["profissionais"] + \
        ", com " + str(s["inversoes"]) + (" inversão" if s["inversoes"] == 1 else " inversões") + " de direção."
    if estado == "nao_calculavel":
        return _item(None, "nao_avaliado", COMPARADO, "Oscilação não calculável", janela, regra,
                     "Não calculável: com média abaixo de " + _br(MEDIA_MINIMA_DA_INSTABILIDADE) + " ou sem a oscilação típica do porte, "
                     "o índice não é estável.", significa, nao, entenda, exemplo)
    if estado == "descontinuidade_de_registro":
        return _item(None, "nao_avaliado", COMPARADO, "Descontinuidade de registro na janela", janela, regra,
                     "Não avaliado: a janela tem um registro marcado como descontinuidade.", significa, nao, entenda, exemplo)
    if estado == "nivel_sem_classificacao":
        return _item(None, "sem_nivel", COMPARADO, "Oscilação sem nível no conjunto", janela, regra, SEM_NIVEL_NO_CONJUNTO, significa, nao,
                     entenda, exemplo)
    frase = "Oscila " + _br(s["indice"], 1) + " vez" + ("" if round(s["indice"], 1) == 1 else "es") + " o comum para o porte"
    observado = janela + " O índice de instabilidade é " + _br(s["indice"], 2) + " (1 é a oscilação típica do porte)."
    habitual = _comparado_com(base, av, s.get("raridade"), s.get("porte"), "índices anteriores") or "Sem comparações anteriores."
    if estado == "sem_comparacoes":
        habitual = _falta_historia(s.get("sem_comparacoes"), "esta oscilação")
    return _item(s.get("classe"), _estado_do_nivel(s), COMPARADO, frase, observado, regra, habitual, significa, nao, entenda, exemplo)


def _texto_perda(base: Base, av: dict, p: dict) -> dict:
    s, limites, r = av["perda"], p["perda"], _rotulos(base)
    def do_nivel(nivel):
        return ("rara (" + _um_em(limites[nivel + "_um_em"]) + ") e de pelo menos " + _br(limites[nivel + "_minimo"]) + " " +
                r["profissionais"] + " e " + _pct(limites[nivel + "_fracao"], 0) + " do que havia")
    regra = ("A mudança de um registro para o seguinte, comparada com as mudanças anteriores de territórios do mesmo porte e com o "
             "mesmo tempo entre registros (aumentos, estabilidade e quedas). Moderado: queda " + do_nivel("moderado") + "; elevado: " +
             do_nivel("elevado") + "; crítico: " + do_nivel("critico") + ". Raridade = (mudanças anteriores iguais ou piores + 1) ÷ "
             "(total + 1); cada nível pede um mínimo de comparações (19, 99 e 999, nos padrões).")
    entenda = ("Compara a queda do último registro com as mudanças que já aconteceram em territórios do mesmo tamanho. É alerta quando "
               "a queda é rara e tem um tamanho mínimo. " + INCOMUM_NAO_E_PIOR)
    exemplo = ("Uma queda de 2 para 1 " + r["profissional"] + " não vira alerta de queda, porque é só 1: ela aparece como crítico em "
               "\"Poucos " + r["profissionais"] + "\".")
    significa = "O número caiu de um registro para o seguinte mais do que o comum para o porte."
    nao = "Não diz o motivo da queda nem se ela vai continuar; uma queda rara também pode ser falha do registro. " + NAO_SIGNIFICA_GERAL
    estado = s["estado"]
    if estado in ("ausencia_de_dado", "janela_insuficiente"):
        return _item(None, "sem_dado", COMPARADO, "Sem registro para comparar",
                     "Falta o registro desta data ou o anterior (ausência de dado não é zero).", regra, "Não avaliável.", significa, nao,
                     entenda, exemplo)
    passou = "De " + curta(s["de"]) + " a " + curta(s["ate"]) + " (" + str(s["meses"]) + " meses), passou de " + _br(s["anterior"]) + \
        " para " + _br(s["atual"]) + " " + r["profissionais"] + " (" + _com_sinal(s["delta"]) + \
        (", " + ("−" if s["pct"] < 0 else "+") + _pct(abs(s["pct"])) if s["pct"] is not None else "") + ")."
    if estado == "sem_perda":
        falta = _falta_historia(s.get("sem_comparacoes"), "uma queda")
        return _item(None, "sem_alerta", COMPARADO, "Sem queda no último registro", passou, regra,
                     "Não houve queda." + (" " + falta if falta else ""), significa, nao, entenda, exemplo)
    queda = "Caiu de " + _br(s["anterior"]) + " para " + _br(s["atual"]) + ((" (−" + _pct(-s["pct"]) + ")") if s.get("pct") is not None else "")
    if estado == "descontinuidade_de_registro":
        qual = "quebra de fonte" if s.get("descontinuidade") == "quebra_de_fonte" else "pico que volta"
        return _item(None, "nao_avaliado", COMPARADO, ("Mudança" if s["delta"] >= 0 else queda) + " com descontinuidade de registro", passou,
                     regra, "Não é alerta: a mudança coincide com uma descontinuidade de registro (" + qual + ").", significa, nao, entenda,
                     exemplo)
    if estado == "nivel_sem_classificacao":
        return _item(None, "sem_nivel", COMPARADO, queda, passou, regra, SEM_NIVEL_NO_CONJUNTO, significa, nao, entenda, exemplo)
    minimos = s.get("minimos") or {}
    tamanho = (" Para este porte, o tamanho mínimo é de " + _profissionais(base, minimos["moderado"]) + " (moderado), " +
               _br(minimos["elevado"]) + " (elevado) e " + _br(minimos["critico"]) + " (crítico).") if minimos else ""
    comparado = _comparado_com(base, av, s.get("raridade"), s.get("porte"), "mudanças anteriores")
    falta = _falta_historia(s.get("sem_comparacoes"), "esta queda")
    if estado == "alerta":
        habitual = comparado + tamanho + (" " + falta if falta else "")
    elif estado == "sem_comparacoes":
        habitual = (falta or "Sem comparações suficientes: falta o registro anterior ou ele está em zero.") + tamanho
    elif s.get("motivo") == "tamanho_abaixo":
        habitual = "Sem alerta: a queda é menor que o tamanho mínimo." + tamanho + (" " + comparado if comparado else "")
    else:
        habitual = "Sem alerta: quedas assim são comuns para o porte. " + comparado + (" " + falta if falta else "")
    return _item(s.get("classe"), _estado_do_nivel(s), COMPARADO, queda, passou, regra, habitual.strip(), significa, nao, entenda, exemplo)


def _texto_patamar(base: Base, av: dict, p: dict) -> dict:
    s, limites, r = av["patamar"], p["patamar"], _rotulos(base)
    regra = ("O patamar é a maior média de dois anos completos, antes dos 4 últimos registros (não é o maior registro sozinho). "
             "Moderado, por convenção: os 2 últimos registros " + _pct(limites["moderado"], 0) + " ou mais abaixo do patamar. Elevado: "
             "isso, e o afastamento raro na base (" + _um_em(limites["elevado_um_em"]) + " afastamentos anteriores de territórios com "
             "patamar do mesmo porte). Crítico: os 4 últimos registros " + _pct(limites["critico"], 0) + " ou mais abaixo, e raro (" +
             _um_em(limites["critico_um_em"]) + "). Só com patamar de pelo menos " + _br(limites["minimo"]) + " " + r["profissionais"] + ".")
    entenda = ("Compara o número de hoje com o melhor período que o território já teve: a maior média de dois anos seguidos. " +
               INCOMUM_NAO_E_PIOR)
    exemplo = "Patamar de 80 " + r["profissionais"] + " e os dois últimos registros com 66 e 64: 17,5% abaixo, nível moderado."
    significa = "O território tem hoje menos " + r["profissionais"] + " do que no melhor período que já teve."
    nao = "O patamar não é uma meta nem o número certo para o território. " + NAO_SIGNIFICA_GERAL
    estado = s["estado"]
    if estado in ("ausencia_de_dado", "janela_insuficiente"):
        return _item(None, "sem_dado", POR_CONVENCAO, "Sem dois anos completos para o patamar",
                     "Faltam registros para calcular o patamar ou o registro desta data.", regra, "Não avaliável.", significa, nao, entenda,
                     exemplo)
    if estado == "nao_calculavel":
        return _item(None, "nao_avaliado", POR_CONVENCAO, "Patamar em zero", "O patamar anterior é zero.", regra, "Não calculável.",
                     significa, nao, entenda, exemplo)
    observado = ("O patamar é de " + _br(s["patamar"]) + " " + r["profissionais"] + " (média de " + curta(s["bloco"]["de"]) + " a " +
                 curta(s["bloco"]["ate"]) + "). O último registro tem " + _br(s["atual"]) + ": " +
                 ("−" if s["diferenca"] < 0 else "+") + _pct(abs(s["diferenca_pct"])) + " ante o patamar.")
    if s.get("registros_abaixo"):
        observado += " Está " + _pct(limites["moderado"], 0) + " ou mais abaixo há " + str(s["registros_abaixo"]) + \
            (" registro." if s["registros_abaixo"] == 1 else " registros.")
    if s.get("recuperado_pct") is not None:
        observado += " Desde o menor valor (" + _br(s["vale"]["valor"]) + ", em " + curta(s["vale"]["competencia"]) + "), recuperou " + \
            _pct(s["recuperado_pct"], 0) + " da distância até o patamar."
    abaixo = s["diferenca"] < 0
    frase = (_pct(-s["diferenca_pct"], 0) + " abaixo do que já teve" if abaixo else "No patamar ou acima dele") + \
        " (patamar de " + _br(round(s["patamar"])) + ")"
    if estado == "nivel_sem_classificacao":
        return _item(None, "sem_nivel", POR_CONVENCAO, frase, observado, regra, SEM_NIVEL_NO_CONJUNTO, significa, nao, entenda, exemplo)
    if estado == "descontinuidade_de_registro":
        return _item(None, "nao_avaliado", POR_CONVENCAO, frase, observado, regra,
                     "Não avaliado: os últimos registros têm uma descontinuidade de registro.", significa, nao, entenda, exemplo)
    if estado == "descritivo":
        return _item(None, "nao_avaliado", POR_CONVENCAO, frase, observado, regra,
                     "Só descritivo: o patamar é menor que " + _br(limites["minimo"]) + " " + r["profissionais"] + ", e poucas unidades "
                     "mudam muito o percentual.", significa, nao, entenda, exemplo)
    if estado == "sem_sinal":
        return _item(None, "sem_alerta", POR_CONVENCAO, frase, observado, regra,
                     "Sem alerta: os 2 últimos registros não estão " + _pct(limites["moderado"], 0) + " ou mais abaixo do patamar.",
                     significa, nao, entenda, exemplo)
    comparado = _comparado_com(base, av, s.get("raridade"), porte_de(math.floor(s["patamar"])), "afastamentos anteriores")
    falta = _falta_historia(s.get("sem_comparacoes"), "este afastamento")
    habitual = ("Por convenção: os 2 últimos registros estão " + _pct(limites["moderado"], 0) + " ou mais abaixo do patamar. " + comparado +
                (" " + falta if falta else "")).strip()
    if s.get("abaixo_por_4") and s["classe"] != "critico":
        habitual += " Os 4 últimos registros estão " + _pct(limites["critico"], 0) + " ou mais abaixo, mas o afastamento não é raro o " \
            "bastante para o crítico (ou faltam comparações)."
    return _item(s["classe"], "alerta", s.get("criterio") or POR_CONVENCAO, frase, observado, regra, habitual, significa, nao, entenda,
                 exemplo)


# --------------------------------------------------------------------------------------------- textos dos sinais 8 a 12
def _populacao_nao_comparavel(base: Base, s: dict) -> str:
    """O motivo da comparação não habilitada, lido da própria base: os anos em que a população se repete ou salta, e os trechos
    comparáveis."""
    periodos = base.periodos
    motivo = comparativos.motivo_da_janela(base, periodos.index(s["de"]) if s.get("de") in periodos else None,
                                           periodos.index(s["ate"]) if s.get("ate") in periodos else None)
    return (motivo or "a população da base não é comparável de um ano para o outro nesta janela") + \
        "; população comparável nesta base: " + comparativos.texto_dos_trechos(base)


def _taxa(valor) -> str:
    """Uma taxa por 1.000 habitantes, sempre com duas casas ("4,00")."""
    return f"{float(valor):,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _variacao(valor, casas: int = 1) -> str:
    """Uma variação percentual com o sinal; o que arredonda para zero sai sem sinal ("0,0%")."""
    arredondado = round(abs(valor), casas)
    return ("" if arredondado == 0 else "+" if valor > 0 else "−") + _pct(arredondado, casas)


def _pontos(valor) -> str:
    arredondado = round(abs(valor), 1)
    return ("" if arredondado == 0 else "+" if valor > 0 else "−") + _br(arredondado) + (" ponto" if arredondado == 1 else " pontos")


def _regra_relativa(base: Base, limites: dict, o_que: str) -> str:
    r = _rotulos(base)
    mes = _mes_ancora(base)
    return ("A variação " + o_que + " em 2 anos (de " + mes + " a " + mes + "), comparada com as variações anteriores de territórios do "
            "mesmo porte (o número de " + r["profissionais"] + " no início da janela). Moderado: rara, " + _um_em(limites["moderado_um_em"]) +
            "; elevado: " + _um_em(limites["elevado_um_em"]) + "; crítico: " + _um_em(limites["critico_um_em"]) + ". Só em janelas com "
            "população comparável (" + comparativos.texto_dos_trechos(base) + ") e com pelo menos " + str(comparativos.MINIMO_DE_MEDICOS) +
            " " + r["profissionais"] + " no início da janela.")


def _relativo(base: Base, av: dict, chave: str, p: dict, nivel_da_data: str, variacao: str | None, observado: str, o_que: str,
              regra: str, significa: str, nao: str, entenda: str, exemplo: str) -> dict:
    """O texto comum dos sinais 8, 9 e 10: o nível da data sempre à vista; a variação, quando a janela vale; e a raridade."""
    s, r = av[chave], _rotulos(base)
    estado = s["estado"]
    if estado == "ausencia_de_dado":
        return _item(None, "sem_dado", COMPARADO, "Sem registro na data", "Não há registro do território em " + curta(s["competencia"]) +
                     " (ausência de dado não é zero).", regra, "Não avaliável.", significa, nao, entenda, exemplo)
    if estado in ("nao_calculavel", "referencia_invalida", "nao_aplicavel"):
        return _item(None, "nao_avaliado", COMPARADO, {"nao_calculavel": "Não calculável", "referencia_invalida": "Sem referência",
                                                     "nao_aplicavel": "Não se aplica"}[estado] if variacao is None else nivel_da_data,
                     (observado + " " if observado else "") + (s.get("motivo") or ""), regra, "Não avaliado.", significa, nao, entenda,
                     exemplo)
    if estado == "comparacao_nao_habilitada":
        return _item(None, "nao_avaliado", COMPARADO, nivel_da_data + " · comparação não habilitada", observado, regra,
                     "Comparação não habilitada: de " + curta(s["de"]) + " a " + curta(s["ate"]) + ", " +
                     _populacao_nao_comparavel(base, s) + ".", significa, nao, entenda, exemplo)
    if estado == "janela_insuficiente":
        return _item(None, "sem_dado", COMPARADO, nivel_da_data + " · sem o registro de dois anos antes", observado, regra,
                     "Janela insuficiente: falta o registro de " + _mes_ancora(base) + " de dois anos antes.", significa, nao, entenda,
                     exemplo)
    frase = variacao or nivel_da_data
    if estado == "descritivo":
        return _item(None, "nao_avaliado", COMPARADO, frase, observado, regra,
                     "Só descritivo: com menos de " + str(comparativos.MINIMO_DE_MEDICOS) + " " + r["profissionais"] + " no início da "
                     "janela, poucas unidades mudam muito a taxa.", significa, nao, entenda, exemplo)
    if estado == "nivel_sem_classificacao":
        return _item(None, "sem_nivel", COMPARADO, frase, observado, regra, SEM_NIVEL_NO_CONJUNTO, significa, nao, entenda, exemplo)
    faixa = s.get("porte")
    comparado = _comparado_com(base, av, s.get("raridade"), faixa, "variações anteriores")
    falta = _falta_historia(s.get("sem_comparacoes"), o_que)
    if estado == "sem_comparacoes":
        habitual = falta or "Sem comparações suficientes."
    elif s.get("classe"):
        habitual = comparado + (" " + falta if falta else "")
    else:
        habitual = "Sem alerta: variações assim são comuns para o porte. " + comparado + (" " + falta if falta else "")
    return _item(s.get("classe"), _estado_do_nivel(s), COMPARADO, frase, observado, regra, habitual.strip(), significa, nao, entenda, exemplo)


def _texto_disponibilidade(base: Base, av: dict, p: dict) -> dict:
    s, r = av["disponibilidade"], _rotulos(base)
    regra = _regra_relativa(base, p["disponibilidade"], "da taxa de " + r["profissionais"] + " por 1.000 habitantes")
    entenda = ("Divide o número de " + r["profissionais"] + " pela população e vê quanto essa taxa mudou em 2 anos. A queda pode vir de "
               "menos " + r["profissionais"] + ", de mais habitantes ou dos dois. " + INCOMUM_NAO_E_PIOR)
    exemplo = "De 2,00 para 1,60 por 1.000 habitantes em 2 anos: queda de 20% na taxa."
    significa = "Há menos " + r["profissionais"] + " por habitante do que dois anos antes."
    nao = "Não mede acesso, cobertura nem qualidade do atendimento, e a população é uma estimativa. " + NAO_SIGNIFICA_GERAL
    nivel = (_taxa(s["taxa"]) + " por 1.000 habitantes em " + curta(s["competencia"])) if s.get("taxa") is not None else "Sem taxa na data"
    variacao = observado = None
    if s.get("variacao_pct") is not None:
        variacao = _variacao(s["variacao_pct"]) + " de " + r["profissionais"] + " por habitante em 2 anos"
        m, pop = s["medicos"], s["populacao_da_janela"]
        observado = ("De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", a taxa passou de " + _taxa(s["taxa_inicial"]) + " para " +
                     _taxa(s["taxa_final"]) + " por 1.000 habitantes (" + _variacao(s["variacao_pct"]) + "). O número de " +
                     r["profissionais"] + " passou de " + _br(m["inicial"]) + " para " + _br(m["final"]) + " (" + _variacao(m["variacao_pct"]) +
                     "), e a população, de " + _br(pop["inicial"]) + " para " + _br(pop["final"]) + " (" + _variacao(pop["variacao_pct"]) + ").")
    elif s.get("taxa") is not None:
        observado = "Em " + curta(s["competencia"]) + ", a taxa é de " + _taxa(s["taxa"]) + " por 1.000 habitantes."
    return _relativo(base, av, "disponibilidade", p, nivel, variacao, observado or "", "esta queda da taxa", regra, significa, nao, entenda,
                     exemplo)


def _texto_posicao(base: Base, av: dict, p: dict) -> dict:
    s, r = av["posicao"], _rotulos(base)
    regra = _regra_relativa(base, p["posicao"], "do percentil do território pela taxa por habitante (no universo fixo da janela)")
    entenda = ("Põe os territórios em fila pela taxa de " + r["profissionais"] + " por habitante e vê quantas posições em 100 o "
               "território perdeu em 2 anos. Ele pode perder posição mesmo sem cair, se os outros cresceram mais. " + INCOMUM_NAO_E_PIOR)
    exemplo = "Do percentil 60 para o 45: tinha taxa maior que 60 em cada 100 territórios e passou a ter maior que 45."
    significa = "O território ficou para trás em relação aos outros da base."
    nao = "A posição compara territórios, não mede suficiência. " + NAO_SIGNIFICA_GERAL
    nivel = ("Percentil " + _br(round(s["percentil"])) + " em " + curta(s["competencia"])) if s.get("percentil") is not None else "Sem posição"
    variacao = observado = None
    if s.get("variacao_pp") is not None:
        variacao = _pontos(s["variacao_pp"]) + " de percentil em 2 anos"
        observado = ("De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", o percentil passou de " + _br(round(s["percentil_inicial"], 1)) +
                     " para " + _br(round(s["percentil_final"], 1)) + " (" + _pontos(s["variacao_pp"]) + "), entre " +
                     _br(s["universo_da_janela"]) + " " + _os_parecidos(base, av) + " com taxa nas duas datas.")
    elif s.get("percentil") is not None:
        observado = "Em " + curta(s["competencia"]) + ", o território está no percentil " + _br(round(s["percentil"], 1)) + ", entre " + \
            _br(s["universo"]) + " " + _os_parecidos(base, av) + " com taxa na data."
    return _relativo(base, av, "posicao", p, nivel, variacao, observado or (s.get("motivo") or ""), "esta perda de posição", regra, significa,
                     nao, entenda, exemplo)


def _texto_defasagem(base: Base, av: dict, p: dict) -> dict:
    s, r = av["defasagem"], _rotulos(base)
    rotulo = s["referencia"]["rotulo"]   # "demais municípios do Amazonas (soma municipal)": nunca dentro de outros parênteses
    regra = _regra_relativa(base, p["defasagem"], "do índice ante a referência (100 × taxa do território ÷ taxa da referência, com a "
                            "referência no grupo de cima e sem o território" + (": " + rotulo if rotulo else "") + ")")
    entenda = ("Compara a taxa do território com a do grupo de cima sem ele, e vê quanto essa relação mudou em 2 anos. " +
               INCOMUM_NAO_E_PIOR)
    exemplo = "Índice 100: taxa igual à da referência. De 90 para 75: ficou 15 pontos mais longe dela."
    significa = "A taxa do território ficou mais distante, para baixo, da taxa da referência."
    nao = "A referência é uma comparação, não uma meta nem um padrão de suficiência. " + NAO_SIGNIFICA_GERAL
    nivel = ("Índice " + _br(round(s["indice"], 1)) + " ante a referência em " + curta(s["competencia"])) if s.get("indice") is not None \
        else "Sem índice"
    na_data = ""
    if s.get("indice") is not None:
        na_data = ("Em " + curta(s["competencia"]) + ", a taxa do território é de " + _taxa(s["taxa"]) + " por 1.000 habitantes, e a " +
                   ("dos " + rotulo if rotulo else "da referência") + ", de " + _taxa(s["referencia"]["taxa"]) + ": índice " +
                   _br(round(s["indice"], 1)) + " (100 é a taxa da referência).")
    variacao = None
    observado = na_data
    if s.get("variacao_pontos") is not None:
        variacao = _pontos(s["variacao_pontos"]) + " no índice ante a referência em 2 anos"
        observado = ("De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", o índice passou de " + _br(round(s["indice_inicial"], 1)) +
                     " para " + _br(round(s["indice_final"], 1)) + " (" + _pontos(s["variacao_pontos"]) + "). " + na_data)
    return _relativo(base, av, "defasagem", p, nivel, variacao, observado, "este afastamento da referência", regra, significa, nao, entenda,
                     exemplo)


def _texto_contexto(base: Base, av: dict, p: dict) -> dict:
    s, r = av["contexto"], _rotulos(base)
    c = s["criterio"]
    limiar = "" if c["taxa_minima"] is None else _taxa(c["taxa_minima"]) + " " + r["profissionais"] + " por 1.000 habitantes em " + \
        curta(c["competencia"]) + " (" + _pct(p["contexto"]["taxa_do_brasil_pct"], 0) + " da taxa do " + r["todo"] + ", de " + \
        _taxa(c["taxa_do_brasil"]) + ")"
    regra = ("Distância em linha reta entre as coordenadas do território e as do mais próximo com taxa igual ou maior que " +
             (limiar or "o critério") + ". O critério pode ser trocado, de 10% a 500% da taxa da base toda. A posição compara essa "
             "distância com a dos " + _br(s["universo"]) + " territórios abaixo do critério. Só contexto: nunca vira alerta.")
    entenda = ("Diz a que distância, em linha reta, fica o território mais próximo com mais " + r["profissionais"] + " por habitante "
               "que o critério. É só contexto: não vira alerta.")
    exemplo = "A 120 km do mais próximo: mais longe que 90 em cada 100 territórios abaixo do critério."
    significa = "Diz a que distância, em linha reta, fica o território mais próximo acima do critério."
    nao = ("Não é distância por estrada, tempo de viagem nem acesso. Não indica falta de atendimento nem como a rede de saúde se "
           "organiza, e não tem nível.")
    if s["estado"] == "nao_aplicavel":
        return _item(None, "contexto", None, "Não se aplica ao " + r["grupo"] + " como unidade", s["motivo"], regra, "Não se aplica.",
                     significa, nao, entenda, exemplo)
    if s["estado"] == "atende_ao_criterio":
        return _item(None, "contexto", None, "Acima do critério (" + (limiar.split(" em ")[0] if limiar else "o critério") + " ou mais)",
                     "A taxa do território (ou de um dos componentes do conjunto) é igual ou maior que " + limiar + ": não há distância a "
                     "medir.", regra, "Só contexto.", significa, nao, entenda, exemplo)
    if s["estado"] != "contexto":
        return _item(None, "contexto", None, "Sem coordenada válida" if s["estado"] == "sem_coordenada" else "Não calculável",
                     s.get("motivo") or "", regra, "Não calculável.", significa, nao, entenda, exemplo)
    ref = s["referencia"]
    observado = ("O componente mais próximo do critério é " + s["membro"] + ": fica a " if s.get("membro") else "O território fica a ") + \
        _br(round(s["distancia_km"], 1)) + " km, em linha reta, de " + ref["rotulo"] + " (" + _taxa(ref["taxa"]) + " por 1.000 habitantes), o " \
        "mais próximo com taxa igual ou maior que " + limiar + "."
    habitual = "Só contexto, sem nível."
    if s["percentil_da_distancia"] is not None:
        habitual = "A distância é maior que a de " + _pct(s["percentil_da_distancia"], 0) + " dos territórios abaixo do critério. Só " \
            "contexto, sem nível."
    return _item(None, "contexto", None, "A " + _br(round(s["distancia_km"], 1)) + " km de " + ref["rotulo"] + ", em linha reta", observado,
                 regra, habitual, significa, nao, entenda, exemplo)


NOMES_CURTOS_DOS_SINAIS = {"estrutural": "poucos {profissionais}", "ausencia": "nenhum {profissional} registrado",
                           "declinio": "declínio persistente", "desaceleracao": "desaceleração", "instabilidade": "instabilidade",
                           "perda": "queda recente", "patamar": "abaixo do que já teve",
                           "disponibilidade": "menos {profissionais} por habitante", "posicao": "perda de posição",
                           "defasagem": "mais longe da referência"}


def nome_do_sinal(base: Base, chave: str, inicial_maiuscula: bool = False) -> str:
    nome = NOMES_CURTOS_DOS_SINAIS[chave].format(**_rotulos(base))
    return nome[:1].upper() + nome[1:] if inicial_maiuscula else nome


def _texto_coexistencia(base: Base, av: dict) -> dict:
    s, alerta = av["coexistencia"], av["alerta"]
    regra = ("Mostra quais sinais com nível coincidem no território. Os que vêm da mesma queda (queda recente, declínio, abaixo do "
             "que já teve e os três comparados com outros) contam como um evento só. Não soma pontos e não forma índice.")
    entenda = ("Lista os sinais que aparecem juntos no território. O alerta do território é o maior nível entre eles: os níveis não "
               "se somam.")
    exemplo = "Queda recente (elevado) e abaixo do que já teve (moderado), da mesma queda: um evento, e o alerta é elevado."
    significa = "Mais de um sinal aponta para o mesmo território na mesma data."
    nao = "Não é uma nota nem um índice geral, e sinais da mesma queda não são evidências independentes. " + NAO_SIGNIFICA_GERAL
    com_nivel = alerta.get("sinais") or []
    if alerta["estado"] == "sem_nivel":
        return _item(None, "sem_nivel", None, "Sem nível no conjunto", alerta["motivo"], regra, SEM_NIVEL_NO_CONJUNTO, significa, nao,
                     entenda, exemplo)
    if not com_nivel:
        return _item(None, "juntos", None, "Nenhum sinal com nível", "Nenhum sinal do território tem nível nesta data.", regra,
                     "Sem coincidência.", significa, nao, entenda, exemplo)
    nomes = [nome_do_sinal(base, item["sinal"]) + " (" + NOMES_DAS_CLASSES[item["nivel"]] + ")" for item in com_nivel]
    lista = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    frase = ("Um sinal com nível: " if len(nomes) == 1 else str(len(nomes)) + " sinais com nível: ") + lista
    observado = "Sinais com nível em " + curta(av["ultima"]["competencia"] if av.get("ultima") else base.periodos[-1]) + ": " + lista + "."
    habitual = "O alerta do território é o maior nível: " + NOMES_DAS_CLASSES[alerta["nivel"]] + ". Os níveis não se somam."
    if alerta.get("mesma_queda"):
        habitual += " " + str(len(alerta["mesma_queda"])) + " desses sinais vêm da mesma queda e contam como um evento."
    if s["combinacoes"]:
        observado += " Combinações: " + "; ".join(item["texto"] for item in s["combinacoes"]) + "."
    return _item(None, "juntos", None, frase, observado, regra, habitual, significa, nao, entenda, exemplo)


def fenomenos(base: Base, av: dict, e: int, p: dict) -> list[dict]:
    """Os 12 sinais do território (1 e 2 juntos), na ordem da tela: o nível, uma frase, o "Entenda" e a explicação completa."""
    r = _rotulos(base)
    nomes = {"estrutural": "Poucos " + r["profissionais"] + " ou nenhum " + r["profissional"] + " registrado",
             "declinio": "Declínio persistente", "desaceleracao": "Desaceleração", "instabilidade": "Instabilidade",
             "perda": "Queda recente", "patamar": "Abaixo do que já teve", "disponibilidade": "Menos " + r["profissionais"] + " por habitante",
             "posicao": "Perda de posição", "defasagem": "Mais longe da referência", "contexto": "Distância", "coexistencia": "Sinais juntos"}
    textos = {"estrutural": lambda: _texto_estrutural(base, av, e, p), "declinio": lambda: _texto_declinio(base, av, p),
              "desaceleracao": lambda: _texto_desaceleracao(base, av, p), "instabilidade": lambda: _texto_instabilidade(base, av, p),
              "perda": lambda: _texto_perda(base, av, p), "patamar": lambda: _texto_patamar(base, av, p),
              "disponibilidade": lambda: _texto_disponibilidade(base, av, p), "posicao": lambda: _texto_posicao(base, av, p),
              "defasagem": lambda: _texto_defasagem(base, av, p), "contexto": lambda: _texto_contexto(base, av, p),
              "coexistencia": lambda: _texto_coexistencia(base, av)}
    limitacoes, qualidade = _limitacoes(base, av), texto_do_registro(av["registro"])
    itens = [{"chave": chave, "numero": numero, "nome": nomes[chave], "grupo": grupo, "dimensao": dimensao, **textos[chave](),
              "sem_comparacoes": _sem_comparacoes_do_sinal(av.get(chave)), "limitacoes": limitacoes, "qualidade": qualidade}
             for chave, numero, grupo, dimensao in FENOMENOS if chave in av or chave == "coexistencia" and "coexistencia" in av]
    for item in itens:
        # Os campos que a resposta já trazia: o estado do sinal no motor e a classe (o nível).
        item["estado"], item["classe"] = (av.get(item["chave"]) or {}).get("estado"), item["nivel"]
    return itens


def _sem_comparacoes_do_sinal(s) -> dict | None:
    """Os níveis que a base ainda não sustenta neste sinal, para a tela dizer ao lado do nível: "Sem comparações suficientes
    para o crítico: há 203, e ele pede 999."."""
    falta = (s or {}).get("sem_comparacoes") if isinstance(s, dict) else None
    if not falta:
        return None
    nomes = ["o " + NOMES_DAS_CLASSES[nivel] for nivel in falta["niveis"]]
    quais = nomes[0] if len(nomes) == 1 else ", ".join(nomes[:-1]) + " e " + nomes[-1]
    pede = ("ele pede " if len(nomes) == 1 else "o " + NOMES_DAS_CLASSES[falta["nivel"]] + " pede ") + _br(falta["pede"])
    return {"niveis": list(falta["niveis"]), "nivel": falta["nivel"], "comparacoes": falta["comparacoes"], "pede": falta["pede"],
            "texto": "Sem comparações suficientes para " + quais + ": há " + _br(falta["comparacoes"]) + ", e " + pede + "."}


def entenda_da_ferramenta(base: Base) -> dict:
    """Os "Entenda" da primeira tela (seção A.4): duas ou três frases simples e um exemplo com números, com os nomes da base. A
    explicação inteira fica em "Como foi calculado"."""
    r = _rotulos(base)
    return {
        "ferramenta": {
            "texto": "O Detector compara cada território com o que é comum na própria base: territórios de tamanho parecido e só o "
                     "que veio antes de cada data. São 12 sinais, e o alerta do território é o maior nível entre eles: moderado, "
                     "elevado ou crítico. " + INCOMUM_NAO_E_PIOR,
            "exemplo": "Uma queda de 18 para 11 " + r["profissionais"] + " é rara quando, entre as mudanças anteriores de " +
                       r["unidades"] + " de 10 a 19 " + r["profissionais"] + ", só 1 em cada 100 foi igual ou pior: alerta elevado."},
        "alerta": {
            "texto": "Um nível por território: o maior entre os seus sinais, sem soma nem índice. \"Comparado com a base\" quer dizer "
                     "raro entre territórios de tamanho parecido; \"por convenção\", um limite igual para todos. Quando faltam "
                     "comparações, a tela diz \"sem comparações suficientes\".",
            "exemplo": "Moderado: 1 em cada 20, com pelo menos 19 comparações. Elevado: 1 em cada 100, com 99. Crítico: 1 em cada "
                       "1.000, com 999."},
        "termos": {
            "texto": "Porte é o tamanho do território, pelo número de " + r["profissionais"] + "; patamar, o melhor período que ele "
                     "já teve (a maior média de dois anos seguidos). Percentil é a posição entre 100: no percentil 60, a taxa é "
                     "maior que a de 60 em cada 100 territórios. \"1 em cada 20\" quer dizer que, entre 20 mudanças anteriores de "
                     "territórios parecidos, só 1 foi igual ou pior.",
            "exemplo": "\"18% abaixo do que já teve (patamar de 130)\": o território teve, em média, 130 " + r["profissionais"] +
                       " no seu melhor período de dois anos e hoje tem 18% menos."},
    }


def por_que(base: Base, av: dict, e: int, p: dict) -> str | None:
    """A coluna "Por quê" da lista: a frase do sinal principal do alerta, com quantos outros sinais têm nível."""
    alerta = av["alerta"]
    if alerta["estado"] != "alerta":
        return None
    chave = "estrutural" if alerta["sinal"] == "ausencia" else alerta["sinal"]
    texto = {"estrutural": lambda: _texto_estrutural(base, av, e, p), "declinio": lambda: _texto_declinio(base, av, p),
             "desaceleracao": lambda: _texto_desaceleracao(base, av, p), "instabilidade": lambda: _texto_instabilidade(base, av, p),
             "perda": lambda: _texto_perda(base, av, p), "patamar": lambda: _texto_patamar(base, av, p),
             "disponibilidade": lambda: _texto_disponibilidade(base, av, p), "posicao": lambda: _texto_posicao(base, av, p),
             "defasagem": lambda: _texto_defasagem(base, av, p)}[chave]()["situacao"]
    outros = alerta["outros"]
    return texto + (" (+" + str(outros) + (" sinal)" if outros == 1 else " sinais)") if outros else "")


# --------------------------------------------------------------------------------------------- resposta
def _linha(base: Base, av: dict, e: int, p: dict) -> dict:
    """A linha da lista: o alerta do território (um nível só, com o tipo de critério e o porquê) e o que os filtros, o mapa e o
    gráfico usam. Os detalhes vêm no pedido de um território."""
    es, pe, pa, de, ds, ins = (av[chave] for chave in ("estrutural", "perda", "patamar", "declinio", "desaceleracao", "instabilidade"))
    di, po, df, co, cx = (av[chave] for chave in ("disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"))
    anteriores = nomes_anteriores.do_rotulo(av["id"], av["rotulo"]) if av["tipo"] == "municipio" else []
    alerta = av["alerta"]
    return {
        "id": av["id"], "tipo": av["tipo"], "nivel": av["nivel"], "rotulo": av["rotulo"], "uf": av["uf"],
        **({"nomes_anteriores": anteriores} if anteriores else {}),   # só para a busca por nome ("Parati" acha PARATY)
        "ultima": av["ultima"], "porte": av["porte"], "sinais": av["sinais"], "dimensoes": av["dimensoes"],
        # O alerta do território: o maior nível entre os sinais, sem soma nem índice, com o tipo de critério e o porquê.
        "alerta": {"estado": alerta["estado"], "nivel": alerta["nivel"], "sinal": alerta["sinal"], "criterio": alerta["criterio"],
                   "outros": alerta["outros"], "por_que": por_que(base, av, e, p),
                   "sinais": [{"sinal": item["sinal"], "nivel": item["nivel"], "criterio": item["criterio"]} for item in alerta["sinais"]],
                   "mesma_queda": alerta.get("mesma_queda") or [], "sem_comparacoes": alerta.get("sem_comparacoes") or [],
                   "motivo": alerta.get("motivo")},
        "estrutural": {"estado": es["estado"], "classe": es.get("classe"), "n": es.get("n"), "impacto_pct": es.get("impacto_pct"),
                       "zeros": (es.get("zeros") or {}).get("registros"), "mantida": bool(es.get("mantida_pela_anterior"))},
        "perda": {"estado": pe["estado"], "classe": pe.get("classe"), "delta": pe.get("delta"), "pct": pe.get("pct"),
                  "de": pe.get("de"), "ate": pe.get("ate"), "magnitude": pe.get("magnitude"), "motivo": pe.get("motivo"),
                  "verificar": pe.get("verificar_registro")},
        "patamar": {"estado": pa["estado"], "classe": pa.get("classe"), "patamar": pa.get("patamar"),
                    "diferenca_pct": pa.get("diferenca_pct"), "abaixo": bool(pa.get("abaixo_por_2")), "critica": pa.get("critica")},
        "declinio": {"estado": de["estado"], "classe": de.get("classe"), "reducoes": de.get("reducoes"), "perda_pct": de.get("perda_pct"),
                     "sinal": de.get("sinal")},
        "desaceleracao": {"estado": ds["estado"], "classe": ds.get("classe"), "desacelera": bool(ds.get("desacelera")),
                          "persistente": ds.get("persistente"), "anos": ds.get("anos"), "rotulo": ds.get("rotulo")},
        "instabilidade": {"estado": ins["estado"], "classe": ins.get("classe"), "indice": ins.get("indice")},
        "registro": {"estado": av["registro"]["estado"], "tipos": sorted({evento["tipo"] for evento in av["registro"]["eventos"]})},
        # Sinais 8 a 12: o nível da data, a variação (quando a comparação é habilitada) e o nível do alerta.
        "disponibilidade": {"estado": di["estado"], "classe": di.get("classe"), "taxa": di.get("taxa"), "populacao": di.get("populacao"),
                            "variacao_pct": di.get("variacao_pct"), "sinal": di.get("sinal")},
        "posicao": {"estado": po["estado"], "classe": po.get("classe"), "percentil": po.get("percentil"), "universo": po.get("universo"),
                    "variacao_pp": po.get("variacao_pp"), "sinal": po.get("sinal")},
        "defasagem": {"estado": df["estado"], "classe": df.get("classe"), "indice": df.get("indice"),
                      "variacao_pontos": df.get("variacao_pontos"), "sinal": df.get("sinal")},
        "contexto": {"estado": co["estado"], "distancia_km": co.get("distancia_km"),
                     "referencia": (co.get("referencia") or {}).get("rotulo"), "referencia_id": (co.get("referencia") or {}).get("id"),
                     "percentil": co.get("percentil_da_distancia")},
        "coexistencia": {"estado": cx["estado"], "combinacoes": [c["chave"] for c in cx["combinacoes"]],
                         "textos": [c["texto"] for c in cx["combinacoes"]], "repercussoes": len(cx["repercussoes"])},
        **({"membros": len(av["membros"]), "ids_dos_membros": list(av["membros"])} if av["tipo"] == "conjunto" else {}),
    }


def _janela(base: Base, bruto) -> tuple[int, int, bool]:
    """A janela pedida: início e fim entre as competências reais; sem pedido, a série inteira."""
    if bruto in (None, {}):
        return 0, len(base.periodos) - 1, True
    if not isinstance(bruto, dict):
        raise ValueError("Janela inválida: envie inicio e fim, com competências da base.")
    inicio = base.posicao(bruto["inicio"]) if bruto.get("inicio") else 0
    fim = base.posicao(bruto["fim"]) if bruto.get("fim") else len(base.periodos) - 1
    if inicio > fim:
        raise ValueError("Janela inválida: o início vem depois do fim.")
    return inicio, fim, inicio == 0 and fim == len(base.periodos) - 1


def _inicio_do_territorio(cal: Calibracao, territorio: Territorio, inicio: int, e: int) -> int:
    """A janela de um município começa depois de uma quebra de fonte (seção 2.4)."""
    if territorio.tipo != "municipio" or not cal.quebra[territorio.linha].any():
        return inicio
    quebrados = np.flatnonzero(cal.quebra[territorio.linha, inicio:e + 1])
    return inicio if not quebrados.size else min(e, inicio + int(quebrados[-1]) + 1)


_BASES_DOS_ESTADOS: dict[str, Base] = {}


def base_dos_estados(base: Base) -> Base | None:
    """A base dos estados como unidade, para a régua própria deles (Proposta V3, seção B.1): as contagens estaduais como linhas, sem
    população, coordenadas nem grupo de cima. None quando a base não tem a fonte estadual."""
    if not base.estados:
        return None
    with _LOCK:
        guardada = _BASES_DOS_ESTADOS.get(base.versao)
    if guardada is not None:
        return guardada
    ufs = tuple(sorted(base.estados))
    vazio = np.full((len(ufs), len(base.periodos)), np.nan)
    quantidade = np.vstack([base.estados[uf] for uf in ufs])
    quantidade.setflags(write=False)
    vazio.setflags(write=False)
    montada = replace(base, versao=base.versao + ":estados", codigos=ufs, nomes=tuple(STATES[uf][1] for uf in ufs), prefixos=ufs,
                      quantidade=quantidade, populacao=vazio, latitude=vazio, longitude=vazio, estados={},
                      indice={uf: linha for linha, uf in enumerate(ufs)}, do_estado={})
    with _LOCK:
        _BASES_DOS_ESTADOS.clear()
        _BASES_DOS_ESTADOS[base.versao] = montada
    return montada


_CALIBRACOES_DOS_ESTADOS: dict[str, Calibracao] = {}


def calibrar_estados(base: Base) -> Calibracao | None:
    """A régua dos estados como unidade: a mesma calibração, com a base dos estados. É uma base pequena: os níveis mais graves
    podem ficar sem comparações suficientes, e a tela diz isso."""
    dos_estados = base_dos_estados(base)
    if dos_estados is None:
        return None
    with _LOCK:
        guardada = _CALIBRACOES_DOS_ESTADOS.get(base.versao)
    if guardada is None:
        guardada = calibrar(dos_estados, guardar=False)
        with _LOCK:
            _CALIBRACOES_DOS_ESTADOS.clear()
            _CALIBRACOES_DOS_ESTADOS[base.versao] = guardada
    return guardada


def _fonte(base: Base) -> dict:
    return {"base": "Brasil", "categoria": "MEDICINA", "versao": base.versao, "primeira": base.periodos[0],
            "ultima": base.periodos[-1], "competencias": len(base.periodos), "rotulos": dict(_rotulos(base)),
            "unidades": {"municipio": series_brasil.UNIDADE_MUNICIPIO, "estado": series_brasil.UNIDADE_ESTADO,
                         "conjunto": series_brasil.UNIDADE_CONJUNTO}}


def _notas(base: Base, personalizado: bool, niveis: set) -> list[str]:
    r = _rotulos(base)
    notas = ["O registro mais recente da base é " + curta(base.periodos[-1]) + ": os sinais descrevem a situação até essa data, não a "
             "de hoje.",
             "O Detector compara cada território com o que é comum na própria base: territórios de tamanho parecido e só o que veio "
             "antes de cada data. Os níveis são moderado, elevado e crítico; cada alerta diz o tipo de critério: \"comparado com a "
             "base\" ou \"por convenção\".",
             "\"Raro\" quer dizer incomum nesta base, não comprovadamente pior: por construção, cerca de 1 em cada 20 territórios "
             "recebe moderado em cada sinal comparado com a base. O nível não é juízo de desassistência, de suficiência do "
             "atendimento nem de prioridade de provimento.",
             "Um nível por território: o maior entre os seus sinais, sem soma nem índice. Sinais que vêm da mesma queda contam como "
             "um evento.",
             "Quando a base não tem comparações bastantes para um nível, a tela diz \"sem comparações suficientes\", com quantas há "
             "e quantas o nível pede.",
             "Zero é registro observado (zero confirmado); a data sem registro é ausência de dado, nunca zero.",
             "A distância (sinal 11) é só contexto: em linha reta, não é acesso nem tempo de viagem, e nunca vira alerta."]
    if "estados" in niveis:
        notas.append("O " + r["grupo"] + " como unidade tem régua própria, com a base dos " + r["grupos"] + ": é uma base pequena, e os "
                     "níveis mais graves podem ficar sem comparações suficientes.")
    if "conjunto" in niveis:
        notas.append("Um conjunto não tem nível: não há outros iguais para comparar. A tela mostra os fatos; o conjunto é a soma das "
                     "contagens dos componentes, não o número de " + r["profissionais"] + " diferentes.")
    if personalizado:
        notas.append("Configuração exploratória: os critérios em uso são diferentes dos padrões, e os resultados não substituem os da "
                     "configuração padrão.")
    return notas


ESTADOS_DO_ALERTA = ("critico", "elevado", "moderado", "sem_alerta", "sem_comparacoes", "sem_nivel")


def _resumo(linhas: list[dict]) -> dict:
    def contar(chave, valores):
        return {valor or "nenhuma": sum(1 for linha in linhas if linha["dimensoes"][chave] == valor) for valor in valores}
    def do_alerta(linha):
        return linha["alerta"]["nivel"] or linha["alerta"]["estado"]
    return {"territorios": len(linhas),
            "por_tipo": {tipo: sum(1 for linha in linhas if linha["tipo"] == tipo) for tipo in ("municipio", "estado", "conjunto")},
            # O resumo dos níveis, que a tela mostra no alto e usa como filtro: um nível por território.
            "niveis": {estado: sum(1 for linha in linhas if do_alerta(linha) == estado) for estado in ESTADOS_DO_ALERTA},
            "estrutural": contar("estrutural", ("critico", "elevado", "moderado", None)),
            "trajetoria": contar("trajetoria", ("critico", "elevado", "moderado", None)),
            "sinais": {sinal: sum(1 for linha in linhas if sinal in linha["sinais"])
                       for sinal in ("estrutural", "ausencia", "perda", "alerta_perda", "patamar", "declinio", "desaceleracao",
                                     "instabilidade", "registro", "disponibilidade", "posicao", "defasagem", "combinados")},
            # Quantos territórios têm nível em cada sinal (o filtro "Sinal" da tela).
            "com_nivel": {sinal: sum(1 for linha in linhas if any(item["sinal"] == sinal for item in linha["alerta"]["sinais"]))
                          for sinal in ("estrutural", "ausencia", "declinio", "desaceleracao", "instabilidade", "perda", "patamar",
                                        "disponibilidade", "posicao", "defasagem")},
            "sem_registro_na_data": sum(1 for linha in linhas if not (linha["ultima"] or {}).get("na_data"))}


def _serie(base: Base, cal: Calibracao, territorio: Territorio, e: int) -> list[dict]:
    """A série observada do território, com o estado de cada registro (observado, zero confirmado ou ausência de dado) e as marcas."""
    saida = []
    for i, periodo in enumerate(base.periodos[:e + 1]):
        valor = territorio.serie[i]
        ponto = {"competencia": periodo, "valor": _num(valor),
                 "estado": "ausencia_de_dado" if valor != valor else "zero_confirmado" if valor == 0 else "observado"}
        if territorio.tipo == "municipio":
            linha = territorio.linha
            if int(cal.pico_conhecido[linha, i]) <= e:
                ponto["marca"] = "pico_que_volta"
            elif bool(cal.quebra[linha, i]):
                ponto["marca"] = "quebra_de_fonte"
            elif i > 0 and int(cal.marca[linha, i]) != 4 and (bool(cal.salto[linha, i]) or bool(cal.queda_grande[linha, i])) and \
                    not (int(cal.marca[linha, i]) in (2, 3) and int(cal.marca_conhecida[linha, i]) <= e):
                # O registro que sai de uma quebra de fonte (marca 4) não entra aqui: o salto dele é a própria quebra, como em
                # _registro (CI 42895759046: Brasília, 4.070 → 8.851 em jan/2018).
                ponto["marca"] = "verificar_registro"
        elif territorio.tipo == "conjunto" and territorio.ausentes is not None and territorio.ausentes[i]:
            ponto["membros_sem_registro"] = int(territorio.ausentes[i])
        saida.append(ponto)
    return saida


def _historico(base: Base, cal: Calibracao, territorio: Territorio, inicio: int, e: int, p: dict,
               cal_dos_estados: Calibracao | None = None) -> list[dict]:
    """O histórico de sinais na janela: a situação de cada data, avaliada só com o que era conhecido nela (sinais 1 a 7)."""
    saida = []
    ancora = _ancora(base)
    for i in range(inicio, e + 1):
        av = avaliar(base, cal, territorio, inicio, i, p, comparar=False, cal_dos_estados=cal_dos_estados)
        anual = base.periodos[i].endswith(ancora)
        saida.append({
            "competencia": base.periodos[i], "valor": av["ultima"]["valor"] if av["ultima"] and av["ultima"]["na_data"] else None,
            "alerta": av["alerta"]["nivel"],
            "estrutural": av["estrutural"].get("classe"),
            "perda": None if av["perda"].get("delta", 0) >= 0 or av["perda"]["estado"] in ("ausencia_de_dado", "janela_insuficiente")
            else {"delta": av["perda"]["delta"], "pct": av["perda"]["pct"], "estado": av["perda"]["estado"],
                  "classe": av["perda"].get("classe")},
            "patamar": {"estado": av["patamar"]["estado"], "classe": av["patamar"].get("classe"),
                        "diferenca_pct": av["patamar"].get("diferenca_pct")},
            "instabilidade": av["instabilidade"].get("classe"),
            "declinio": {"reducoes": av["declinio"].get("reducoes"), "classe": av["declinio"].get("classe"),
                         "sinal": av["declinio"].get("sinal")} if anual else None,
            "desaceleracao": {"desacelera": bool(av["desaceleracao"].get("desacelera")), "classe": av["desaceleracao"].get("classe"),
                              "rotulo": av["desaceleracao"].get("rotulo")} if anual else None,
        })
    return saida


def _comparativo(base: Base, territorio: Territorio, e: int) -> dict:
    """As séries do território para os gráficos dos sinais 8 e 10: a taxa por 1.000 habitantes, a taxa da referência (na mesma
    unidade, sem o território) e o índice, em cada competência até a data avaliada. O nível de cada data é válido nela; a
    variação entre datas só é lida nos trechos com população comparável."""
    taxa = comparativos.taxa_do_territorio(base, territorio)
    referencia, rotulo, motivo = comparativos.referencia_do_territorio(base, territorio)
    with np.errstate(invalid="ignore", divide="ignore"):
        indice = np.where(referencia > 0, 100.0 * taxa / referencia, np.nan)
    return {"competencias": list(base.periodos[:e + 1]), "taxa": [_num(v) for v in taxa[:e + 1]],
            "referencia": {"rotulo": rotulo, "motivo": motivo, "taxa": [_num(v) for v in referencia[:e + 1]]},
            "indice": [_num(v) for v in indice[:e + 1]],
            "trechos": comparativos.trechos_comparaveis(base)}


def _coordenadas(base: Base, qd: comparativos.Quadro, territorios: list, linhas: list[dict]) -> dict:
    """As coordenadas autorizadas para o mapa do Detector: os municípios da seleção (e os componentes dos conjuntos de municípios)
    e o município mais próximo que atende ao critério de cada um, na competência avaliada. Sem coordenada válida, sem ponto."""
    marcados = set()
    for territorio in territorios:
        if territorio.tipo == "municipio":
            marcados.add(territorio.linha)
        elif territorio.tipo == "conjunto" and territorio.nivel == "municipios":
            marcados.update(comparativos.linhas_dos_membros(base, territorio))
    for linha in linhas:
        referencia = linha["contexto"].get("referencia_id")
        if referencia:
            marcados.add(base.indice[referencia[5:]])
    return {"code:" + base.codigos[i]: [float(base.latitude[i, qd.e]), float(base.longitude[i, qd.e])]
            for i in sorted(marcados) if bool(qd.com_coordenada[i])}


def _aviso_da_base(base: Base, regua: dict) -> str | None:
    """O aviso da base (B.1): quando, numa mesma data, as quedas raras passam do triplo do esperado."""
    m = regua["monitoramento"]
    if not m.get("aviso_da_base"):
        return None
    return ("Em " + curta(regua["competencia"]) + ", " + _pct(m["taxa_pct"]) + " dos territórios tiveram uma queda rara ao mesmo tempo "
            "(o esperado é cerca de " + _pct(m["esperado_pct"], 0) + "). Quando muitos caem juntos, pode ter havido mudança no registro da "
            "base, e não nos territórios.")


def compute(sources, opcoes: dict) -> dict:
    """POST /api/detector. Sem `detalhe`: a lista da situação mais recente da janela, de todos os territórios da seleção, com o
    alerta de cada um, o resumo dos níveis, a régua da data e os critérios em uso. Com `detalhe` (o id de um território da
    seleção): a série, o histórico de sinais e os textos de cada sinal. Nada é registrado na sessão, e nada vai ao provedor de IA."""
    if not isinstance(opcoes, dict):
        raise ValueError("Pedido do Detector inválido.")
    desconhecidas = set(opcoes) - {"base", "estados_unidade", "conjuntos", "janela", "parametros", "detalhe"}
    if desconhecidas:
        raise ValueError("Opção desconhecida no pedido do Detector: " + ", ".join(sorted(desconhecidas)) + ".")
    base = series_brasil.base_de(sources)
    cal = calibrar(base)
    p, personalizado = parametros(opcoes.get("parametros"))
    inicio, e, padrao = _janela(base, opcoes.get("janela"))
    territorios = series_brasil.selecao(base, opcoes)
    if len(territorios) > MAX_LINHAS:
        raise ValueError("Seleção grande demais para o Detector.")
    cal_dos_estados = calibrar_estados(base) if any(territorio.tipo == "estado" for territorio in territorios) else None
    janela = {"inicio": base.periodos[inicio], "fim": base.periodos[e], "registros": e - inicio + 1,
              "meses": int(base.meses[e] - base.meses[inicio]), "padrao": padrao,
              "ultimo_registro_da_base": base.periodos[-1], "e_o_ultimo": e == len(base.periodos) - 1}
    qd = comparativos.quadro(base, e, p)
    comparacao = {"de": None if qd.ini is None else base.periodos[qd.ini], "ate": None if qd.fim is None else base.periodos[qd.fim],
                  "estado": qd.motivo or "comparavel", "trechos": comparativos.trechos_comparaveis(base),
                  "motivo": comparativos.motivo_da_janela(base, qd.ini, qd.fim) if qd.motivo == "comparacao_nao_habilitada" else None,
                  "minimo_de_medicos": comparativos.MINIMO_DE_MEDICOS,
                  "contexto": {"taxa_minima": qd.limiar, "taxa_do_brasil": qd.taxa_do_brasil,
                               "pct_da_taxa_do_brasil": p["contexto"]["taxa_do_brasil_pct"], "atendem": int(qd.atende.sum()),
                               "universo": qd.universo_da_distancia}}
    comum = {"versao": VERSION, "fonte": _fonte(base), "janela": janela, "competencias": list(base.periodos), "comparacao": comparacao,
             "parametros": {"padrao": PADRAO, "em_uso": p, "personalizados": personalizado,
                            "editaveis": {grupo: {chave: {"minimo": faixa[0], "maximo": faixa[1], "inteiro": faixa[2]}
                                                  for chave, faixa in chaves.items()} for grupo, chaves in EDITAVEIS.items()}},
             # Os níveis e os grupos dos sinais, para a tela não repetir a regra: 1 em cada N e as comparações que cada nível pede.
             "niveis": [{"chave": chave, "nome": reguas.NOMES_DOS_NIVEIS[chave], "um_em": um_em, "pede": minimo}
                        for chave, um_em, minimo in reversed(reguas.NIVEIS)],
             "grupos": [{"chave": chave, "nome": nome, "sinais": [sinal for sinal, _, grupo, _ in FENOMENOS if grupo == chave]}
                        for chave, nome in GRUPOS_DOS_SINAIS],
             "portes": list(ROTULOS_DOS_PORTES),
             "entenda": entenda_da_ferramenta(base),
             "exploratorio": personalizado}
    detalhe = opcoes.get("detalhe")
    if detalhe is not None:
        alvo = next((territorio for territorio in territorios if territorio.id == detalhe), None)
        if alvo is None:
            raise ValueError("Território fora da seleção do Detector: " + str(detalhe) + ".")
        comeco = _inicio_do_territorio(cal, alvo, inicio, e)
        av = avaliar(base, cal, alvo, comeco, e, p, inicio, cal_dos_estados=cal_dos_estados)
        return {**comum, "territorio": av, "janela_do_territorio": {"inicio": base.periodos[comeco], "depois_da_quebra": comeco != inicio},
                "serie": _serie(base, cal, alvo, e), "historico": _historico(base, cal, alvo, comeco, e, p, cal_dos_estados),
                "comparativo": _comparativo(base, alvo, e), "coordenadas": _coordenadas(base, qd, [alvo], [_linha(base, av, e, p)]),
                "fenomenos": fenomenos(base, av, e, p), "linha": _linha(base, av, e, p),
                "notas": _notas(base, personalizado, {alvo.nivel, alvo.tipo})}
    linhas = [_linha(base, avaliar(base, cal, territorio, _inicio_do_territorio(cal, territorio, inicio, e), e, p, inicio,
                                   cal_dos_estados=cal_dos_estados), e, p) for territorio in territorios]
    regua = limiares(base, cal, e, p)
    return {**comum, "linhas": linhas, "resumo": _resumo(linhas), "calibracao": regua,
            **({"calibracao_dos_estados": limiares(base_dos_estados(base), cal_dos_estados, e, p)} if cal_dos_estados is not None else {}),
            "aviso_da_base": _aviso_da_base(base, regua),
            "coordenadas": _coordenadas(base, qd, territorios, linhas),
            "notas": _notas(base, personalizado, {territorio.nivel for territorio in territorios} | {territorio.tipo for territorio in territorios}),
            "limitacoes": ["RARO_E_INCOMUM_NA_BASE", "CONJUNTO_SEM_NIVEL", "COMPARACAO_SO_COM_POPULACAO_COMPARAVEL"] +
                          (["CONFIGURACAO_EXPLORATORIA"] if personalizado else [])}
