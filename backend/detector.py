"""Detector de Sinais Territoriais (comando V22, Eixo II, etapa 3: o núcleo — fenômenos 1 a 7, a descontinuidade de registro e
os estados de calibração). Referência metodológica: Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2.4, 4, 4.2 e 5, com as
decisões de 10/11/2026 (D-A a D-C). A tela e os textos estão em Docs/DETECTOR_DE_SINAIS.md.

Três camadas, que nunca se confundem:

1. **fato observado** — a contagem e a mudança entre registros (−3 médicos, −30%, com as datas reais); sempre exibido;
2. **excepcionalidade** — se a mudança é incomum para territórios do mesmo porte e o mesmo tipo de intervalo (5 ou 7 meses),
   medida só com as transições anteriores à data avaliada (origens móveis, sem dados futuros);
3. **sinal analítico** — a intensidade do sinal (atenção, alta, crítica), por fenômeno, com limites provisórios. Não é juízo
   de desassistência, de suficiência do cuidado nem de prioridade de provimento (divergência aprovada da SPEC, CFG-NOR: D-A).

O que é calculado, sempre pelo motor e sem o provedor de IA:

- **1–2, escala estrutural:** N = 0 (zero confirmado) e N = 1, crítica; 2–3, alta; 4–5, atenção; N ≥ 6, sem sinal estrutural
  (não é "atendimento suficiente"). Impacto numérico 100/N da perda hipotética de um registro (N = 0: não calculável). A
  classe exibida é a mais grave entre as duas últimas observações válidas (a piora aparece na hora; a melhora, depois de duas).
- **3, declínio persistente:** série de junho, reduções consecutivas, perda medida desde o primeiro valor da sequência; duas
  reduções e ≥ 10% (forte) ou três e ≥ 20% (muito forte). Sinal observado, sem intensidade, até a calibração.
- **4, desaceleração do crescimento:** a classe da Análise de Tendência (trend.classify_pairs, CAP-TEN-01) nos 4 junhos até o junho
  avaliado; a persistência (a mesma classe um ano antes) é exploratória.
- **5, instabilidade:** descritiva — o desvio-padrão das variações entre 7 registros, dividido pela oscilação típica do porte
  (c·N̄^(θ/2), θ = 1,35, c por tipo de intervalo); "não calculável" com N̄ < 6.
- **6, perda abrupta:** a perda entre registros consecutivos sempre aparece. Alerta só com magnitude (alta: ≥ máx(2; ⌈0,2·N⌉);
  crítica: ≥ máx(3; ⌈0,3·N⌉)) **e** excepcionalidade (P(X ≤ x) ≤ 1% ou 0,1% na célula porte × intervalo, contando empates, com
  o mínimo de 100 ou 1.000 transições anteriores; abaixo dele, sem classificação).
- **7, afastamento de patamar:** patamar = maior média dos 4 registros de dois anos civis completos, em blocos que terminam
  antes dos 4 últimos registros. Os 2 últimos registros ≤ 85% do patamar: atenção. Alta: atenção e cauda de 1% do afastamento
  na faixa de porte. Crítica (4 últimos ≤ 70% e cauda de 0,1%): não calibrável na base atual. Patamar < 20 médicos: descritivo.
- **descontinuidade de registro:** pico que volta (salto de 10 ou mais médicos que ao menos dobra a contagem e volta, em até
  dois registros, a até 125% do valor anterior) e quebra de fonte (soma municipal da UF abaixo da contagem estadual). O pico não
  gera alerta na volta e sai da calibração; a queda grande que persiste continua alertável, com "verificar registro".

A calibração é municipal: estados como unidade e conjuntos recebem os fatos e os indicadores descritivos, sem intensidade.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass

import numpy as np

import nomes_anteriores
import series_brasil
import comparativos
from series_brasil import Base, Territorio
from territorial_levels import STATES, human_period
from trend import FAMILY as FAMILIA_DA_TENDENCIA, LABELS as ROTULOS_DA_TENDENCIA, classify_pairs

VERSION = "DETECTOR-SINAIS/V2.2/2"   # /2: os fenômenos 8 a 12 (etapa 5 do comando V22)
# Faixas de porte da calibração (seção 4.2): pelo número de médicos antes da transição (ou pelo patamar, no indicador 7).
PORTES = ((1, 3), (4, 9), (10, 19), (20, 49), (50, 99), (100, 299), (300, None))
ROTULOS_DOS_PORTES = ("1 a 3", "4 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 ou mais")
INTERVALOS = (5, 7)  # meses: janeiro → junho e junho → janeiro
SEM_DATA = 10 ** 6   # "nunca conhecido"

# Parâmetros padrão: limites provisórios (candidatos da V2.2), sujeitos à calibração.
PADRAO = {
    "estrutural": {"critica": 1, "alta": 3, "atencao": 5},
    "declinio": {"forte_reducoes": 2, "forte_perda": 10.0, "muito_forte_reducoes": 3, "muito_forte_perda": 20.0},
    "perda": {"alta_minimo": 2, "alta_fracao": 20.0, "critica_minimo": 3, "critica_fracao": 30.0,
              "alta_alfa": 1.0, "critica_alfa": 0.1, "alta_transicoes": 100, "critica_transicoes": 1000},
    "patamar": {"atencao": 15.0, "critica": 30.0, "minimo": 20, "alta_alfa": 1.0, "alta_observacoes": 100},
    **comparativos.PADRAO,   # fenômenos 8 a 11: limites provisórios e o critério do contexto geográfico
}
# O que a pessoa pode trocar, como configuração exploratória: (mínimo, máximo, inteiro).
EDITAVEIS = {
    "estrutural": {"critica": (0, 50, True), "alta": (0, 50, True), "atencao": (0, 50, True)},
    "declinio": {"forte_perda": (1.0, 90.0, False), "muito_forte_perda": (1.0, 90.0, False)},
    "perda": {"alta_minimo": (1, 50, True), "alta_fracao": (1.0, 90.0, False), "critica_minimo": (1, 50, True),
              "critica_fracao": (1.0, 90.0, False), "alta_alfa": (0.01, 20.0, False), "critica_alfa": (0.01, 20.0, False)},
    "patamar": {"atencao": (1.0, 90.0, False), "critica": (1.0, 90.0, False), "minimo": (1, 1000, True),
                "alta_alfa": (0.01, 20.0, False)},
    **comparativos.EDITAVEIS,
}
# Registro (seção 2.4): critérios provisórios, fixos (mudam o que entra na calibração).
PICO_SALTO, PICO_FATOR, PICO_RETORNO, PICO_REGISTROS = 10, 2.0, 1.25, 2
QUEDA_GRANDE, QUEDA_FRACAO = 10, 0.5
THETA, REGISTROS_DA_INSTABILIDADE, MEDIA_MINIMA_DA_INSTABILIDADE, MINIMO_DE_ESCALA = 1.35, 7, 6.0, 100
GRAVIDADE = {None: 0, "atencao": 1, "alta": 2, "critica": 3}
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
    if not e["critica"] <= e["alta"] <= e["atencao"]:
        raise ValueError("Escala estrutural: os limites precisam crescer (crítica ≤ alta ≤ atenção).")
    if em_uso["perda"]["critica_fracao"] < em_uso["perda"]["alta_fracao"] or \
            em_uso["perda"]["critica_minimo"] < em_uso["perda"]["alta_minimo"] or \
            em_uso["perda"]["critica_alfa"] > em_uso["perda"]["alta_alfa"]:
        raise ValueError("Perda abrupta: o critério da intensidade crítica não pode ser mais frouxo que o da alta.")
    if em_uso["patamar"]["critica"] < em_uso["patamar"]["atencao"] or \
            em_uso["declinio"]["muito_forte_perda"] < em_uso["declinio"]["forte_perda"]:
        raise ValueError("O limite mais grave não pode ser menor que o menos grave.")
    comparativos.conferir(em_uso)
    return em_uso, personalizado


def porte_de(valor) -> int | None:
    """Índice da faixa de porte (PORTES) de uma contagem; None para zero, ausente ou negativo."""
    if valor is None or valor != valor or valor < 1:
        return None
    for indice, (minimo, maximo) in enumerate(PORTES):
        if valor >= minimo and (maximo is None or valor <= maximo):
            return indice
    return None


def _portes(valores: np.ndarray) -> np.ndarray:
    """Faixa de porte de cada valor (−1 para zero, ausente ou abaixo de 1)."""
    saida = np.full(valores.shape, -1, dtype=np.int8)
    with np.errstate(invalid="ignore"):
        for indice, (minimo, maximo) in enumerate(PORTES):
            dentro = (valores >= minimo) & ((valores <= maximo) if maximo is not None else True)
            saida[dentro] = indice
    return saida


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
    p_perda: np.ndarray         # P(X ≤ x) da variação relativa na célula, só com transições anteriores (NaN: não se aplica)
    n_perda: np.ndarray         # transições anteriores na célula
    patamar: np.ndarray         # patamar de cada município em cada data (NaN: sem bloco elegível)
    patamar_ano: np.ndarray     # ano inicial do bloco do patamar (−1: nenhum)
    afastamento: np.ndarray     # 1 − máx(2 últimos)/patamar (NaN quando não se aplica)
    p_patamar: np.ndarray       # P(A ≥ a) do afastamento na faixa de porte do patamar, só com avaliações anteriores
    n_patamar: np.ndarray
    instabilidade: np.ndarray   # índice de instabilidade (NaN: não calculável)
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
    regular &= np.isin(intervalo, INTERVALOS)[None, :]
    porte = _portes(anterior)
    p_perda = np.full((n, t), np.nan)
    n_perda = np.zeros((n, t), dtype=np.int32)
    for j in range(1, t):
        if intervalo[j] not in INTERVALOS:
            continue
        colunas = [i for i in range(1, j) if intervalo[i] == intervalo[j]]
        if colunas:
            usavel = regular[:, colunas] & ~(marca_conhecida[:, colunas] <= j)
            valores, faixas = relativa[:, colunas][usavel], porte[:, colunas][usavel]
        else:
            valores, faixas = np.empty(0), np.empty(0, dtype=np.int8)
        for faixa in range(len(PORTES)):
            atuais = np.flatnonzero(regular[:, j] & (porte[:, j] == faixa))
            if not atuais.size:
                continue
            anteriores = np.sort(valores[faixas == faixa])
            n_perda[atuais, j] = anteriores.size
            if anteriores.size:
                p_perda[atuais, j] = np.searchsorted(anteriores, relativa[atuais, j], side="right") / anteriores.size

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
    p_patamar = np.full((n, t), np.nan)
    n_patamar = np.zeros((n, t), dtype=np.int32)
    for e in range(1, t):
        if not np.isfinite(afastamento[:, e]).any():
            continue
        # Só avaliações anteriores, sem as que tinham um registro de pico (conhecido até a data) nos dois últimos registros.
        usavel = np.isfinite(afastamento[:, :e])
        com_pico = (pico_conhecido[:, :e] <= e)
        com_pico[:, 1:] |= (pico_conhecido[:, :e - 1] <= e) if e > 1 else False
        usavel &= ~com_pico & ~quebra[:, :e]
        valores, faixas = afastamento[:, :e][usavel], porte_do_patamar[:, :e][usavel]
        for faixa in range(len(PORTES)):
            atuais = np.flatnonzero(np.isfinite(afastamento[:, e]) & (porte_do_patamar[:, e] == faixa))
            if not atuais.size:
                continue
            anteriores = np.sort(valores[faixas == faixa])
            n_patamar[atuais, e] = anteriores.size
            if anteriores.size:
                p_patamar[atuais, e] = 1 - np.searchsorted(anteriores, afastamento[atuais, e], side="left") / anteriores.size

    # Instabilidade (descritiva): as variações de 7 registros pela oscilação típica do porte, por tipo de intervalo.
    instabilidade = np.full((n, t), np.nan)
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

    for matriz in (pico, pico_conhecido, marca, marca_conhecida, salto, queda_grande, quebra, p_perda, n_perda, patamar,
                   patamar_ano, afastamento, p_patamar, n_patamar, instabilidade, escala, relativa, regular, porte,
                   porte_do_patamar, intervalo):
        matriz.setflags(write=False)
    calibracao = Calibracao(versao=base.versao, pico=pico, pico_conhecido=pico_conhecido, marca=marca,
                            marca_conhecida=marca_conhecida, salto=salto, queda_grande=queda_grande, quebra=quebra,
                            p_perda=p_perda, n_perda=n_perda, patamar=patamar, patamar_ano=patamar_ano,
                            afastamento=afastamento, p_patamar=p_patamar, n_patamar=n_patamar, instabilidade=instabilidade,
                            escala=escala, blocos=blocos, relativa=relativa, regular=regular, porte=porte,
                            porte_do_patamar=porte_do_patamar, intervalo=intervalo)
    if guardar:
        with _LOCK:
            _CALIBRACOES.clear()
            _CALIBRACOES[base.versao] = calibracao
    return calibracao


# --------------------------------------------------------------------------------------------- avaliação de um território
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


def _classe_estrutural(n: int, p: dict) -> str | None:
    return "critica" if n <= p["critica"] else "alta" if n <= p["alta"] else "atencao" if n <= p["atencao"] else None


def _estrutural(base: Base, serie: np.ndarray, e: int, p: dict, calibravel: bool) -> dict:
    """Fenômenos 1 e 2: a escala estrutural, com a duração do zero e a histerese (a mais grave das duas últimas observações)."""
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
             "classe_do_valor": do_valor if calibravel else None,
             "classe": exibida if calibravel else None, "mantida_pela_anterior": calibravel and exibida != do_valor,
             "anterior": None if ant is None else {"competencia": base.periodos[ant], "n": int(serie[ant])},
             "zeros": None if not zeros else {"registros": zeros, "desde": base.periodos[inicio_do_zero],
                                             "meses": int(base.meses[e] - base.meses[inicio_do_zero])}}
    saida["estado"] = "nivel_sem_classificacao" if not calibravel else "classificado" if exibida else "sem_sinal"
    return saida


def _perda(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, e: int, p: dict) -> dict:
    """Fenômeno 6: a transição mais recente. O fato sempre sai; o alerta exige magnitude e excepcionalidade calibrada."""
    if serie[e] != serie[e]:
        return {"estado": "ausencia_de_dado", "classe": None}
    ant = _anterior_valido(serie, e)
    if ant is None:
        return {"estado": "janela_insuficiente", "classe": None}
    anterior, atual = int(serie[ant]), int(serie[e])
    delta = atual - anterior
    meses = int(base.meses[e] - base.meses[ant])
    fato = {"de": base.periodos[ant], "ate": base.periodos[e], "anterior": anterior, "atual": atual, "delta": delta,
            "pct": (100.0 * delta / anterior) if anterior > 0 else None, "meses": meses, "classe": None, "magnitude": None}
    marca = int(cal.marca[linha, e]) if cal is not None and ant == e - 1 else 0
    conhecida = marca and int(cal.marca_conhecida[linha, e]) <= e
    if delta >= 0:
        fato["estado"] = "descontinuidade_de_registro" if conhecida and marca in (1, 2, 4) else "sem_perda"
        if cal is not None and ant == e - 1 and bool(cal.salto[linha, e]) and not conhecida:
            fato["verificar_registro"] = "salto"
        return fato
    queda = -delta
    minimo_alta = max(p["alta_minimo"], math.ceil(p["alta_fracao"] / 100.0 * anterior))
    minimo_critica = max(p["critica_minimo"], math.ceil(p["critica_fracao"] / 100.0 * anterior))
    fato["magnitude"] = "critica" if queda >= minimo_critica else "alta" if queda >= minimo_alta else None
    fato["minimos"] = {"alta": minimo_alta, "critica": minimo_critica}
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
    if ant != e - 1 or meses not in INTERVALOS or not math.isfinite(float(cal.p_perda[linha, e])):
        fato["estado"] = "nao_calibrado"
        fato["motivo"] = "intervalo_irregular"
        return fato
    prob, anteriores = float(cal.p_perda[linha, e]), int(cal.n_perda[linha, e])
    fato["excepcionalidade"] = {"p": prob, "transicoes": anteriores, "intervalo_meses": meses}
    incomum = anteriores >= p["alta_transicoes"] and prob <= p["alta_alfa"] / 100.0
    muito_incomum = anteriores >= p["critica_transicoes"] and prob <= p["critica_alfa"] / 100.0
    fato["excepcionalidade"]["nivel"] = "muito_incomum" if muito_incomum else "incomum" if incomum else \
        "nao_calibrada" if anteriores < p["alta_transicoes"] else "comum"
    if fato["magnitude"] is None:
        fato["estado"], fato["motivo"] = "perda_observada", "magnitude_abaixo"
    elif anteriores < p["alta_transicoes"]:
        fato["estado"], fato["motivo"] = "nao_calibrado", "poucas_transicoes"
    elif fato["magnitude"] == "critica" and muito_incomum:
        fato["estado"], fato["classe"] = "alerta", "critica"
    elif incomum:
        fato["estado"], fato["classe"] = "alerta", "alta"
        if fato["magnitude"] == "critica" and anteriores < p["critica_transicoes"]:
            fato["critica_sem_calibracao"] = True
    else:
        fato["estado"], fato["motivo"] = "perda_observada", "comum_para_o_porte"
    return fato


def _patamar_da_serie(base: Base, blocos: tuple, serie: np.ndarray, e: int) -> tuple[float | None, int | None]:
    """O patamar de uma série fora da calibração municipal (estado como unidade, conjunto): o mesmo cálculo, na própria série."""
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
    """Fenômeno 7: o afastamento do patamar anterior (a maior média de dois anos civis completos, antes dos 4 últimos registros)."""
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
    saida = {"patamar": patamar, "bloco": {"de": str(ano) + "01", "ate": str(ano + 1) + "06"}, "atual": int(atual),
             "diferenca": atual - patamar, "diferenca_pct": (100.0 * (atual - patamar) / patamar) if patamar > 0 else None,
             "classe": None}
    if patamar <= 0:
        saida["estado"] = "nao_calculavel"
        return saida
    limite_atencao, limite_critica = (1 - p["atencao"] / 100.0) * patamar, (1 - p["critica"] / 100.0) * patamar
    ultimos = [serie[i] for i in range(max(0, e - 3), e + 1)]
    dois = ultimos[-2:]
    abaixo_2 = len(dois) == 2 and all(v == v and v <= limite_atencao for v in dois)
    abaixo_4 = len(ultimos) == 4 and all(v == v and v <= limite_critica for v in ultimos)
    # Há quantos registros seguidos o território está abaixo do limite de atenção.
    duracao = 0
    for i in range(e, -1, -1):
        if serie[i] == serie[i] and serie[i] <= limite_atencao:
            duracao += 1
        else:
            break
    fim_do_bloco = base.periodos.index(saida["bloco"]["ate"])
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
    prob, anteriores = float(cal.p_patamar[linha, e]), int(cal.n_patamar[linha, e])
    incomum = math.isfinite(prob) and anteriores >= p["alta_observacoes"] and prob <= p["alta_alfa"] / 100.0
    saida["excepcionalidade"] = {"p": prob if math.isfinite(prob) else None, "observacoes": anteriores,
                                 "porte": porte_de(math.floor(patamar)),
                                 "nivel": "incomum" if incomum else "nao_calibrada" if anteriores < p["alta_observacoes"] else "comum"}
    saida["estado"], saida["classe"] = "classificado", "alta" if incomum else "atencao"
    # A crítica exige os 4 últimos registros ≤ 70% do patamar e a cauda de 0,1%, que a base atual não permite estimar.
    saida["critica"] = "nao_calibravel" if abaixo_4 else None
    return saida


def _junhos(base: Base, inicio: int, e: int) -> list[int]:
    return [i for i in range(inicio, e + 1) if base.periodos[i].endswith("06")]


def _declinio(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, inicio: int, e: int, p: dict) -> dict:
    """Fenômeno 3: reduções consecutivas na série de junho, com a perda medida desde o primeiro valor da sequência."""
    junhos = _junhos(base, inicio, e)
    if len(junhos) < 2:
        return {"estado": "janela_insuficiente", "classe": None}
    def valor(i):
        if serie[i] != serie[i] or (cal is not None and int(cal.pico_conhecido[linha, i]) <= e):
            return None  # ausente ou registro de pico: fora da sequência
        return float(serie[i])
    ultimo = junhos[-1]
    if valor(ultimo) is None:
        return {"estado": "ausencia_de_dado", "classe": None, "ate": base.periodos[ultimo]}
    reducoes, posicao = 0, len(junhos) - 1
    while posicao > 0:
        atual, antes = valor(junhos[posicao]), valor(junhos[posicao - 1])
        consecutivos = int(base.periodos[junhos[posicao]][:4]) - int(base.periodos[junhos[posicao - 1]][:4]) == 1
        if atual is None or antes is None or not consecutivos or not atual < antes:
            break
        reducoes, posicao = reducoes + 1, posicao - 1
    primeiro = junhos[posicao]
    saida = {"reducoes": reducoes, "de": base.periodos[primeiro], "ate": base.periodos[ultimo], "junhos": len(junhos),
             "inicial": _num(valor(primeiro)), "final": _num(valor(ultimo)), "classe": None, "sinal": None}
    if not reducoes:
        saida["estado"] = "sem_sinal"
        return saida
    perda = 100.0 * (1 - valor(ultimo) / valor(primeiro))
    saida["perda_pct"] = perda
    if reducoes >= p["muito_forte_reducoes"] and perda >= p["muito_forte_perda"]:
        saida["sinal"] = "muito_forte"
    elif reducoes >= p["forte_reducoes"] and perda >= p["forte_perda"]:
        saida["sinal"] = "forte"
    # Sinal observado: sem intensidade até a calibração (seção 4.2).
    saida["estado"] = "sinal_observado" if saida["sinal"] else "reducao_observada"
    return saida


def _classe_dos_junhos(base: Base, serie: np.ndarray, ultimo: int) -> tuple[str | None, list[int]]:
    """A classe da Análise de Tendência (CAP-TEN-01) nos 4 junhos que terminam em `ultimo`; None sem os 4 registros."""
    ano = int(base.periodos[ultimo][:4])
    indices = []
    for passo in range(3, -1, -1):
        chave = str(ano - passo) + "06"
        if chave not in base.periodos:
            return None, []
        indices.append(base.periodos.index(chave))
    if any(serie[i] != serie[i] for i in indices):
        return None, indices
    # As velocidades exatas (Δy, Δt), como pares de inteiros: a mesma função da Análise de Tendência (trend.classify_pairs, o
    # caminho em massa de classify_frame), sem regra paralela.
    velocidades = [(int(serie[b]) - int(serie[a]), int(base.meses[b] - base.meses[a])) for a, b in zip(indices, indices[1:])]
    return classify_pairs(velocidades)[0], indices


def _desaceleracao(base: Base, serie: np.ndarray, e: int) -> dict:
    """Fenômeno 4: a classe "Desaceleração do crescimento" do Agente nos 4 junhos até o junho avaliado; atualizada só em junho."""
    junhos = _junhos(base, 0, e)
    if not junhos:
        return {"estado": "janela_insuficiente", "classe": None}
    ultimo = junhos[-1]
    categoria, indices = _classe_dos_junhos(base, serie, ultimo)
    if categoria is None:
        return {"estado": "janela_insuficiente" if not indices else "ausencia_de_dado", "classe": None,
                "ate": base.periodos[ultimo]}
    saida = {"de": base.periodos[indices[0]], "ate": base.periodos[ultimo], "tendencia": categoria,
             "rotulo": ROTULOS_DA_TENDENCIA[categoria], "valores": [int(serie[i]) for i in indices], "classe": None,
             "desacelera": categoria == "CRESCIMENTO_DESACELERADO", "persistente": None}
    if saida["desacelera"] and len(junhos) >= 2:
        anterior, _ = _classe_dos_junhos(base, serie, junhos[-2])
        saida["persistente"] = anterior == "CRESCIMENTO_DESACELERADO"  # exploratória: não gera intensidade
    saida["estado"] = "sinal_observado" if saida["desacelera"] else "sem_sinal"
    return saida


def _instabilidade(base: Base, cal: Calibracao | None, linha: int | None, serie: np.ndarray, e: int) -> dict:
    """Fenômeno 5: descritivo, sem intensidade. 1 = a oscilação típica do porte."""
    if e < REGISTROS_DA_INSTABILIDADE - 1:
        return {"estado": "janela_insuficiente", "classe": None}
    janela = serie[e - REGISTROS_DA_INSTABILIDADE + 1:e + 1]
    if np.isnan(janela).any():
        return {"estado": "ausencia_de_dado", "classe": None}
    media = float(janela.mean())
    variacoes = np.diff(janela)
    saida = {"registros": REGISTROS_DA_INSTABILIDADE, "de": base.periodos[e - REGISTROS_DA_INSTABILIDADE + 1],
             "ate": base.periodos[e], "media": media, "classe": None,
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
    saida["indice"], saida["estado"] = indice, "descritivo"
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


def avaliar(base: Base, cal: Calibracao, territorio: Territorio, inicio: int, e: int, p: dict, inicio_da_janela: int | None = None,
            comparar: bool = True) -> dict:
    """A situação de um território na data `e` (a mais recente da janela), fenômeno a fenômeno. `inicio` é o começo da janela dos
    indicadores (depois de uma quebra de fonte); `inicio_da_janela`, o da janela pedida, para a qualidade do registro. Com
    `comparar`, entram os fenômenos 8 a 12 (comparativos.py); o histórico de sinais avalia só o núcleo (1 a 7)."""
    municipal = territorio.tipo == "municipio"
    calibracao, linha, serie = (cal if municipal else None), territorio.linha, territorio.serie
    ultima = next((i for i in range(e, -1, -1) if serie[i] == serie[i]), None)
    situacao = {
        "estrutural": _estrutural(base, serie, e, p["estrutural"], municipal),
        "perda": _perda(base, calibracao, linha, serie, e, p["perda"]),
        "patamar": _patamar(base, calibracao, cal.blocos, linha, serie, e, p["patamar"]),
        "declinio": _declinio(base, calibracao, linha, serie, inicio, e, p["declinio"]),
        "desaceleracao": _desaceleracao(base, serie, e),
        "instabilidade": _instabilidade(base, calibracao, linha, serie, e),
        "registro": _registro(base, calibracao, linha, serie, inicio if inicio_da_janela is None else inicio_da_janela, e),
    }
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
    if situacao["declinio"].get("reducoes", 0) >= p["declinio"]["forte_reducoes"]:
        sinais.append("declinio")
    if situacao["desaceleracao"].get("desacelera"):
        sinais.append("desaceleracao")
    if situacao["registro"]["estado"] != "normal":
        sinais.append("registro")
    if comparar:
        qd = comparativos.quadro(base, e, p)
        situacao["disponibilidade"] = comparativos.disponibilidade(base, qd, territorio, p)
        situacao["posicao"] = comparativos.posicao(base, qd, territorio, p)
        situacao["defasagem"] = comparativos.defasagem(base, qd, territorio, p)
        situacao["contexto"] = comparativos.contexto(base, qd, territorio)
        sinais += [chave for chave in ("disponibilidade", "posicao", "defasagem") if situacao[chave].get("sinal")]
        situacao["coexistencia"] = comparativos.coexistencia(sinais, situacao["estrutural"].get("classe"))
        if situacao["coexistencia"]["combinacoes"]:
            sinais.append("combinados")
    dimensoes = {
        "estrutural": situacao["estrutural"].get("classe"),
        "trajetoria": max((situacao["perda"].get("classe"), situacao["patamar"].get("classe")), key=lambda c: GRAVIDADE[c]),
        "ritmo": None,  # desaceleração e instabilidade: sinais descritivos, sem intensidade
        "comparacao": None,  # 8 a 10: sinais observados com limites provisórios, sem intensidade (decisão D-A)
        "contexto": None,    # 11: só contexto
    }
    return {
        "id": territorio.id, "tipo": territorio.tipo, "nivel": territorio.nivel, "rotulo": territorio.rotulo,
        "uf": STATES[territorio.uf][0] if territorio.uf else None, "unidade": territorio.unidade,
        "ultima": None if ultima is None else {"competencia": base.periodos[ultima], "valor": int(serie[ultima]),
                                               "na_data": ultima == e},
        "porte": porte_de(serie[ultima]) if ultima is not None else None,
        **situacao, "sinais": sinais, "dimensoes": dimensoes,
        **({"membros": list(territorio.membros), "nomes_dos_membros": list(territorio.nomes_dos_membros),
            "versao": territorio.versao} if territorio.tipo == "conjunto" else {}),
    }


# --------------------------------------------------------------------------------------------- limiares de uma data
def _limiar_inferior(ordenados: np.ndarray, alfa: float):
    """O maior valor x da amostra com P(X ≤ x) ≤ alfa, contando empates; None quando nenhum valor cabe na cauda."""
    n = ordenados.size
    k = int(math.floor(alfa * n + 1e-12))
    while k > 0:
        valor = ordenados[k - 1]
        if np.searchsorted(ordenados, valor, side="right") <= int(math.floor(alfa * n + 1e-12)):
            return float(valor)
        k = int(np.searchsorted(ordenados, valor, side="left"))
    return None


def limiares(base: Base, cal: Calibracao, e: int, p: dict) -> dict:
    """O que a calibração diz na data `e`, para a tela explicar: por faixa de porte, quantas transições anteriores há e a partir
    de que queda a variação é incomum; e, no afastamento de patamar, a partir de que afastamento."""
    perda, patamar = p["perda"], p["patamar"]
    meses = int(cal.intervalo[e]) if e > 0 else None
    celulas = []
    if e > 0 and meses in INTERVALOS:
        colunas = [i for i in range(1, e) if int(cal.intervalo[i]) == meses]
        if colunas:
            usavel = cal.regular[:, colunas] & ~(cal.marca_conhecida[:, colunas] <= e)
            valores, faixas = cal.relativa[:, colunas][usavel], cal.porte[:, colunas][usavel]
        else:
            valores, faixas = np.empty(0), np.empty(0, dtype=np.int8)
        for faixa, rotulo in enumerate(ROTULOS_DOS_PORTES):
            anteriores = np.sort(valores[faixas == faixa])
            alta = _limiar_inferior(anteriores, perda["alta_alfa"] / 100.0) if anteriores.size >= perda["alta_transicoes"] else None
            critica = _limiar_inferior(anteriores, perda["critica_alfa"] / 100.0) \
                if anteriores.size >= perda["critica_transicoes"] else None
            celulas.append({"porte": rotulo, "transicoes": int(anteriores.size),
                            "queda_incomum_pct": None if alta is None else -100.0 * alta,
                            "queda_muito_incomum_pct": None if critica is None else -100.0 * critica,
                            "alta": "calibrado" if anteriores.size >= perda["alta_transicoes"] else "sem_calibracao",
                            "critica": "calibrado" if anteriores.size >= perda["critica_transicoes"] else "sem_calibracao"})
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
            anteriores = np.sort(-valores[faixas == faixa])  # cauda de cima: a de baixo do oposto
            limite = _limiar_inferior(anteriores, patamar["alta_alfa"] / 100.0) if anteriores.size >= patamar["alta_observacoes"] else None
            faixas_do_patamar.append({"porte": rotulo, "observacoes": int(anteriores.size),
                                      "afastamento_incomum_pct": None if limite is None else -100.0 * limite,
                                      "alta": "calibrado" if anteriores.size >= patamar["alta_observacoes"] else "sem_calibracao",
                                      "critica": "nao_calibravel"})
    avaliadas = np.isfinite(cal.p_perda[:, e]) if e > 0 else np.zeros(0, dtype=bool)
    incomuns = int((avaliadas & (cal.p_perda[:, e] <= perda["alta_alfa"] / 100.0) &
                    (cal.n_perda[:, e] >= perda["alta_transicoes"])).sum()) if e > 0 else 0
    return {"competencia": base.periodos[e], "intervalo_meses": meses, "perda": celulas, "patamar": faixas_do_patamar,
            # Só monitoramento (seção 4.2): a taxa de variações incomuns por registro, em todos os municípios da base.
            "monitoramento": {"avaliadas": int(avaliadas.sum()), "incomuns": incomuns,
                              "taxa_pct": (100.0 * incomuns / int(avaliadas.sum())) if int(avaliadas.sum()) else None}}


# --------------------------------------------------------------------------------------------- textos determinísticos
MESES_CURTOS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")
NOMES_DAS_CLASSES = {"atencao": "atenção", "alta": "alta", "critica": "crítica"}
FENOMENOS = (
    ("estrutural", "1–2", "Dependência de poucos médicos e ausência de médicos registrados", "Condição estrutural"),
    ("declinio", "3", "Declínio persistente", "Trajetória"),
    ("perda", "6", "Perda abrupta de médicos", "Trajetória"),
    ("patamar", "7", "Afastamento de patamar anterior", "Trajetória"),
    ("desaceleracao", "4", "Desaceleração do crescimento", "Ritmo e instabilidade"),
    ("instabilidade", "5", "Instabilidade temporal", "Ritmo e instabilidade"),
    ("disponibilidade", "8", "Deterioração da disponibilidade relativa", "Comparação relativa"),
    ("posicao", "9", "Deterioração da posição relativa", "Comparação relativa"),
    ("defasagem", "10", "Ampliação da defasagem ante referência", "Comparação relativa"),
    ("contexto", "11", "Distância geográfica a territórios com maior disponibilidade de médicos", "Contexto geográfico"),
    ("coexistencia", "12", "Coexistência de sinais", "Coexistência"),
)
NAO_SIGNIFICA_GERAL = ("Não diz que a população está sem atendimento, que o atendimento é insuficiente nem que há prioridade de "
                       "provimento. A intensidade do sinal descreve este indicador, não uma urgência assistencial.")
SEM_CALIBRACAO_DO_NIVEL = ("Sem classificação: a comparação com territórios parecidos existe só para municípios. Para estados como "
                           "unidade e para conjuntos, o Detector mostra os fatos e os indicadores descritivos.")
LIMITES_PROVISORIOS = "Limites provisórios, sujeitos à calibração."


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


def _pct_curto(valor) -> str:
    """Percentual de um limite, sem zeros à direita: 1 → "1%"; 0,1 → "0,1%"; 0,25 → "0,25%"."""
    return (f"{valor:.2f}".rstrip("0").rstrip(".")).replace(".", ",") + "%"


def _parte(p: float) -> str:
    """Uma fração como percentual de duas casas; o que arredondaria para zero sai como "menos de 0,01%"."""
    return "menos de 0,01%" if 0 < p < 0.00005 else _pct(100 * p, 2)


def _com_sinal(valor) -> str:
    return ("+" if valor > 0 else "−" if valor < 0 else "") + _br(abs(valor))


def _medicos(n) -> str:
    return _br(n) + (" médico" if n == 1 else " médicos")


def _quem(av: dict) -> str:
    return {"municipio": "o município", "estado": "o estado", "conjunto": "o conjunto", "brasil": "o Brasil"}[av["tipo"]]


def _unidade_curta(av: dict) -> str:
    return {"municipio": "médicos registrados", "estado": "médicos únicos (fonte estadual)", "brasil": "médicos únicos (fonte nacional)",
            "conjunto": "médicos na soma das contagens dos componentes"}[av["tipo"]]


def _limitacoes(base: Base, av: dict) -> str:
    partes = [("O valor do conjunto é a " if av["tipo"] == "conjunto" else "A contagem é de ") + av["unidade"] + "."]
    partes.append("A base só tem médicos, com registros de janeiro e junho; o mais recente é " + curta(base.periodos[-1]) +
                  " e não descreve a situação de hoje.")
    if av["tipo"] == "conjunto":
        partes.append("No conjunto, a soma só existe nas competências em que todos os componentes têm registro.")
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
            partes.append("Verificar registro: em " + curta(evento["em"]) + ", salto de 10 ou mais médicos que ao menos dobrou a "
                          "contagem (" + valores + "). Se a contagem voltar em até dois registros, o trecho passa a "
                          "descontinuidade de registro.")
        else:
            partes.append("Verificar registro: em " + curta(evento["em"]) + ", queda de 10 ou mais médicos que levou a contagem à "
                          "metade ou menos (" + valores + "). Pode ser mudança real ou falha do registro; a queda continua "
                          "valendo para os alertas.")
    return " ".join(partes)


def _texto_estrutural(base: Base, av: dict, e: int, p: dict) -> dict:
    s, limites = av["estrutural"], p["estrutural"]
    criterio = ("Escala pelo número de médicos: até " + str(limites["critica"]) + " (inclusive nenhum), intensidade crítica; até " +
                str(limites["alta"]) + ", alta; até " + str(limites["atencao"]) + ", atenção; acima disso, sem sinal por esta "
                "escala. Vale a situação mais grave entre os dois últimos registros: a piora aparece na hora, e a melhora, depois "
                "de dois registros. " + LIMITES_PROVISORIOS)
    if s["estado"] == "ausencia_de_dado":
        return {"situacao": "Sem registro em " + curta(base.periodos[e]) + ".", "observado": "Não há registro deste território em " +
                curta(base.periodos[e]) + ": ausência de dado, que não é o mesmo que zero.", "criterio": criterio,
                "habitual": "Não avaliável sem o registro.", "significa": "Falta o registro da competência.",
                "nao_significa": "Não quer dizer que o território ficou sem médicos."}
    n = s["n"]
    observado = "Em " + curta(base.periodos[e]) + ", " + _quem(av) + " tinha " + (_medicos(n) if n else "nenhum médico") + \
        " (" + _unidade_curta(av) + ")"
    if s["anterior"]:
        observado += "; em " + curta(s["anterior"]["competencia"]) + ", " + _br(s["anterior"]["n"])
    observado += "."
    if s["zeros"]:
        observado += " Zero confirmado no registro há " + str(s["zeros"]["registros"]) + \
            (" registro" if s["zeros"]["registros"] == 1 else " registros seguidos") + ", desde " + curta(s["zeros"]["desde"]) + \
            (" (" + str(s["zeros"]["meses"]) + " meses)." if s["zeros"]["meses"] else ".")
    impacto = ("Com " + _medicos(n) + ", a saída de um reduziria o número registrado em " + _pct(s["impacto_pct"]) + "."
               if n else "Com zero médicos registrados, o impacto da saída de um não é calculável.")
    if s["estado"] == "nivel_sem_classificacao":
        situacao, habitual = _medicos(n) + " · sem classificação neste nível", SEM_CALIBRACAO_DO_NIVEL + " " + impacto
    elif s["classe"]:
        situacao = (_medicos(n) if n else "Nenhum médico registrado") + " · intensidade " + NOMES_DAS_CLASSES[s["classe"]]
        habitual = "A escala estrutural é uma convenção sobre o número de médicos, não uma comparação com a oscilação habitual. " + impacto
        if s["mantida_pela_anterior"]:
            habitual += " A intensidade exibida vem do registro anterior: a melhora só vale depois de dois registros seguidos."
    else:
        situacao = _medicos(n) + " · sem sinal por esta escala"
        habitual = "A escala estrutural é uma convenção sobre o número de médicos, não uma comparação com a oscilação habitual. " + impacto
    return {"situacao": situacao, "observado": observado, "criterio": criterio, "habitual": habitual,
            "significa": "Com poucos médicos registrados, cada saída pesa muito no total do território.",
            "nao_significa": NAO_SIGNIFICA_GERAL + " Seis ou mais médicos também não querem dizer atendimento suficiente."}


def _texto_declinio(base: Base, av: dict, p: dict) -> dict:
    s, limites = av["declinio"], p["declinio"]
    criterio = ("Série de junho, com reduções em anos seguidos; a perda é medida desde o primeiro valor da sequência. " +
                str(limites["forte_reducoes"]) + " reduções e perda de " + _pct(limites["forte_perda"], 0) + " ou mais: sinal forte; " +
                str(limites["muito_forte_reducoes"]) + " reduções e " + _pct(limites["muito_forte_perda"], 0) +
                " ou mais: muito forte. " + LIMITES_PROVISORIOS)
    comum = {"criterio": criterio, "significa": "O número de médicos diminuiu de forma repetida, e não só de um registro para o outro.",
             "nao_significa": "Não identifica a causa da queda nem diz que ela vai continuar. " + NAO_SIGNIFICA_GERAL}
    if s["estado"] in ("janela_insuficiente", "ausencia_de_dado"):
        motivo = "A janela tem menos de dois junhos." if s["estado"] == "janela_insuficiente" else \
            "Não há registro em " + curta(s["ate"]) + " (ou ele é um registro de pico)."
        return {"situacao": "Não avaliável nesta janela.", "observado": motivo, "habitual": "Não avaliável.", **comum}
    if not s["reducoes"]:
        return {"situacao": "Sem queda no último junho.", "observado": "Em " + curta(s["ate"]) + ", o número de médicos (" +
                _br(s["final"]) + ") não é menor que o do junho anterior.", "habitual": "Sem sinal.", **comum}
    observado = "De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", o número de médicos caiu em " + str(s["reducoes"]) + \
        (" junho seguido" if s["reducoes"] == 1 else " junhos seguidos") + ": de " + _br(s["inicial"]) + " para " + _br(s["final"]) + \
        " (−" + _pct(s["perda_pct"]) + ")."
    nome = {"forte": "sinal observado forte", "muito_forte": "sinal observado muito forte"}.get(s["sinal"], "queda observada")
    return {"situacao": "−" + _pct(s["perda_pct"]) + " em " + str(s["reducoes"]) + (" junho" if s["reducoes"] == 1 else " junhos seguidos") +
            " · " + nome, "observado": observado,
            "habitual": "Sem classificação de intensidade: ainda não há comparação com territórios parecidos para dizer se uma "
                        "sequência de quedas como esta é incomum. O fato fica como sinal observado.", **comum}


def _texto_perda(base: Base, av: dict, p: dict) -> dict:
    s, limites = av["perda"], p["perda"]
    criterio = ("Alerta só quando a queda é grande para o porte e também incomum. Grande: pelo menos " + str(limites["alta_minimo"]) +
                " médicos e " + _pct(limites["alta_fracao"], 0) + " do número anterior (intensidade alta) ou pelo menos " +
                str(limites["critica_minimo"]) + " médicos e " + _pct(limites["critica_fracao"], 0) + " (crítica), arredondando para "
                "cima. Incomum: entre as transições anteriores de municípios do mesmo porte, no mesmo tipo de intervalo (5 ou 7 "
                "meses), no máximo " + _pct_curto(limites["alta_alfa"]) + " (alta) ou " +
                _pct_curto(limites["critica_alfa"]) + " (crítica) tiveram variação igual ou pior, contando os empates; é "
                "preciso haver ao menos " + _br(limites["alta_transicoes"]) + " (alta) ou " + _br(limites["critica_transicoes"]) +
                " (crítica) transições anteriores. " + LIMITES_PROVISORIOS)
    comum = {"criterio": criterio,
             "significa": "Uma redução de um registro para o seguinte, descrita como aconteceu. A perda aparece mesmo quando não é incomum.",
             "nao_significa": "Não informa, sozinha, mudança na qualidade ou no acesso à assistência, nem a causa da redução. " +
                              NAO_SIGNIFICA_GERAL}
    if s["estado"] in ("ausencia_de_dado", "janela_insuficiente"):
        return {"situacao": "Sem registro para comparar.", "observado": "Falta o registro desta competência ou o anterior: ausência de "
                "dado, que não é o mesmo que zero.", "habitual": "Não avaliável.", **comum}
    intervalo = "Entre " + curta(s["de"]) + " e " + curta(s["ate"]) + " (" + str(s["meses"]) + " meses), o número de médicos "
    if s["delta"] >= 0:
        observado = intervalo + ("continuou em " + _br(s["atual"]) if s["delta"] == 0 else "passou de " + _br(s["anterior"]) + " para " +
                                 _br(s["atual"]) + " (" + _com_sinal(s["delta"]) + ")") + "."
        habitual = "Sem perda no último registro."
        if s.get("verificar_registro") == "salto":
            habitual += " O salto leva a nota “verificar registro”."
        if s["estado"] == "descontinuidade_de_registro":
            habitual = "A transição faz parte de uma descontinuidade de registro; não é comparada com a oscilação habitual."
        return {"situacao": "Sem perda no último registro.", "observado": observado, "habitual": habitual, **comum}
    observado = intervalo + "passou de " + _br(s["anterior"]) + " para " + _br(s["atual"]) + " (" + _com_sinal(s["delta"]) + \
        ("; −" + _pct(-s["pct"]) if s["pct"] is not None else "") + ")."
    fato = _com_sinal(s["delta"]) + (" (−" + _pct(-s["pct"]) + ")" if s["pct"] is not None else "")
    if s["estado"] == "descontinuidade_de_registro":
        return {"situacao": fato + " · descontinuidade de registro, sem alerta", "observado": observado,
                "habitual": "A queda é a volta de um pico de registro (ou está numa quebra de fonte): não gera alerta e fica fora da "
                            "comparação com territórios parecidos.", **comum}
    minimos = " Para este porte, a queda é grande a partir de " + _medicos(s["minimos"]["alta"]) + " (alta) ou " + \
        _medicos(s["minimos"]["critica"]) + " (crítica)."
    if s["estado"] == "nivel_sem_classificacao":
        return {"situacao": fato + " · sem classificação neste nível", "observado": observado, "habitual": SEM_CALIBRACAO_DO_NIVEL, **comum}
    if s["estado"] == "nao_calibrado" and s.get("motivo") == "intervalo_irregular":
        return {"situacao": fato + " · sem classificação", "observado": observado,
                "habitual": "Sem classificação: o registro anterior é de " + str(s["meses"]) + " meses antes, e a comparação com "
                            "territórios parecidos só existe para os intervalos de 5 e de 7 meses (e a partir do terceiro registro "
                            "da base).", **comum}
    ex = s["excepcionalidade"]
    quantas = "Entre " + _br(ex["transicoes"]) + " transições anteriores de municípios com " + ROTULOS_DOS_PORTES[s["porte"]] + \
        " médicos, no mesmo tipo de intervalo (" + str(ex["intervalo_meses"]) + " meses), " + \
        ("nenhuma teve" if ex["p"] == 0 else _parte(ex["p"]) + " tiveram") + " variação igual ou pior que esta"
    if s["estado"] == "nao_calibrado":
        return {"situacao": fato + " · sem classificação", "observado": observado,
                "habitual": "Sem classificação: há poucos municípios parecidos na base, antes desta data, para dizer se esta queda é "
                            "incomum (" + _br(ex["transicoes"]) + " transições anteriores; o mínimo é " +
                            _br(limites["alta_transicoes"]) + ")." + minimos, **comum}
    if s["classe"]:
        nome = "muito incomum" if s["classe"] == "critica" else "incomum"
        habitual = quantas + ": é " + nome + " (limite de " +             _pct_curto(limites["critica_alfa" if s["classe"] == "critica" else "alta_alfa"]) + ")." + minimos
        if s.get("critica_sem_calibracao"):
            habitual += " A queda chega ao mínimo da intensidade crítica, mas há poucas transições anteriores para dizer se é muito incomum."
        return {"situacao": fato + " · alerta de intensidade " + NOMES_DAS_CLASSES[s["classe"]], "observado": observado,
                "habitual": habitual, **comum}
    if s.get("motivo") == "magnitude_abaixo":
        return {"situacao": fato + " · perda observada, sem alerta", "observado": observado,
                "habitual": "A queda não chega ao mínimo para um alerta." + minimos + " " + quantas + ".", **comum}
    return {"situacao": fato + " · perda observada, sem alerta", "observado": observado,
            "habitual": quantas + ": é uma oscilação comum para o porte." + minimos, **comum}


def _texto_patamar(base: Base, av: dict, p: dict) -> dict:
    s, limites = av["patamar"], p["patamar"]
    criterio = ("Patamar: a maior média dos 4 registros de dois anos seguidos, em blocos que terminam antes dos 4 últimos registros "
                "(não é o maior registro sozinho). Atenção: os 2 últimos registros " + _pct(limites["atencao"], 0) + " ou mais abaixo do "
                "patamar. Alta: além disso, um afastamento incomum para o porte (no máximo " + _pct_curto(limites["alta_alfa"]) +
                " das avaliações anteriores). Crítica: os 4 últimos registros " + _pct(limites["critica"], 0) + " ou mais abaixo e "
                "muito incomum; a base atual não permite estimar esse limite. Com patamar abaixo de " + str(limites["minimo"]) +
                " médicos, o indicador é só descritivo. " + LIMITES_PROVISORIOS)
    comum = {"criterio": criterio, "significa": "O número de médicos está abaixo de um nível que o território já sustentou por dois anos.",
             "nao_significa": "Não pressupõe que o território devesse voltar ao patamar. " + NAO_SIGNIFICA_GERAL}
    if s["estado"] in ("ausencia_de_dado", "janela_insuficiente", "nao_calculavel"):
        motivo = {"ausencia_de_dado": "Não há registro nesta competência.",
                  "janela_insuficiente": "Ainda não há dois anos civis completos antes dos 4 últimos registros para formar o patamar.",
                  "nao_calculavel": "O patamar anterior é zero: o afastamento não é calculável."}[s["estado"]]
        return {"situacao": "Não avaliável nesta data.", "observado": motivo, "habitual": "Não avaliável.", **comum}
    observado = "O patamar anterior é de " + _br(s["patamar"], 1) + " médicos (a média de " + curta(s["bloco"]["de"]) + " a " + \
        curta(s["bloco"]["ate"]) + "). Em " + curta(av["ultima"]["competencia"]) + ", " + _quem(av) + " tinha " + _br(s["atual"]) + ": " + \
        (_pct(abs(s["diferenca_pct"])) + (" abaixo" if s["diferenca"] < 0 else " acima") + " do patamar" if s["diferenca"] else "igual ao patamar") + "."
    if s.get("registros_abaixo"):
        observado += " Está " + _pct(limites["atencao"], 0) + " ou mais abaixo há " + str(s["registros_abaixo"]) + \
            (" registro." if s["registros_abaixo"] == 1 else " registros seguidos.")
    if s.get("recuperado_pct") is not None:
        observado += " Desde o menor valor depois do patamar (" + _br(s["vale"]["valor"]) + ", em " + curta(s["vale"]["competencia"]) + \
            "), recuperou " + _pct(s["recuperado_pct"]) + " da diferença."
    fato = (_pct(abs(s["diferenca_pct"])) + (" abaixo" if s["diferenca"] < 0 else " acima") + " do patamar") if s["diferenca"] else "No patamar"
    if s["estado"] == "nivel_sem_classificacao":
        return {"situacao": fato + " · sem classificação neste nível", "observado": observado, "habitual": SEM_CALIBRACAO_DO_NIVEL, **comum}
    if s["estado"] == "descontinuidade_de_registro":
        return {"situacao": fato + " · descontinuidade de registro", "observado": observado,
                "habitual": "Os últimos registros têm uma descontinuidade de registro: o afastamento não é classificado.", **comum}
    if s["estado"] == "descritivo":
        return {"situacao": fato + " · descritivo", "observado": observado,
                "habitual": "Sem classificação: com patamar abaixo de " + str(limites["minimo"]) + " médicos, perder o patamar é fácil "
                            "(de 4 para 3 já são 25%), e a comparação não distingue oscilação de mudança. A escala estrutural "
                            "continua informativa.", **comum}
    if s["estado"] == "sem_sinal":
        return {"situacao": fato + " · sem sinal", "observado": observado,
                "habitual": "Os 2 últimos registros não estão " + _pct(limites["atencao"], 0) + " ou mais abaixo do patamar.", **comum}
    ex = s["excepcionalidade"]
    if ex["nivel"] == "nao_calibrada":
        habitual = "Sem comparação: há poucas avaliações anteriores de municípios com patamar parecido (" + _br(ex["observacoes"]) + \
            "; o mínimo é " + _br(limites["alta_observacoes"]) + ") para dizer se este afastamento é incomum."
    else:
        habitual = "Entre " + _br(ex["observacoes"]) + " avaliações anteriores de municípios com patamar de " + \
            ROTULOS_DOS_PORTES[ex["porte"]] + " médicos, " + \
            ("nenhuma estava tão ou mais afastada" if ex["p"] == 0 else _parte(ex["p"]) + " estavam tão ou mais afastadas") + " do patamar: " + \
            ("é incomum (limite de " + _pct_curto(limites["alta_alfa"]) + ")." if ex["nivel"] == "incomum"
             else "não é incomum.")
    if s.get("critica") == "nao_calibravel":
        habitual += " Os 4 últimos registros estão " + _pct(limites["critica"], 0) + " ou mais abaixo do patamar, mas a base não tem " \
            "casos suficientes para dizer se isso é muito incomum: sem classificação crítica."
    return {"situacao": fato + " · intensidade " + NOMES_DAS_CLASSES[s["classe"]], "observado": observado, "habitual": habitual, **comum}


def _texto_desaceleracao(base: Base, av: dict) -> dict:
    s = av["desaceleracao"]
    comum = {"criterio": "A mesma classe da Análise de Tendência (CAP-TEN-01), calculada com o número de médicos nos 4 junhos até o "
                         "junho avaliado e atualizada só em junho: crescimento em todos os períodos, com velocidade cada vez menor.",
             "significa": "O território continua crescendo, mas mais devagar a cada ano.",
             "nao_significa": "Não é queda no número de médicos nem diz que o crescimento vai parar. " + NAO_SIGNIFICA_GERAL}
    if s["estado"] in ("janela_insuficiente", "ausencia_de_dado"):
        return {"situacao": "Não avaliável nesta data.", "observado": "Faltam os 4 junhos seguidos (ou o registro de um deles) até a data "
                "avaliada.", "habitual": "Não avaliável.", **comum}
    valores = ", ".join(_br(v) for v in s["valores"][:-1]) + " e " + _br(s["valores"][-1])
    observado = "Nos 4 junhos de " + curta(s["de"]) + " a " + curta(s["ate"]) + ", os valores foram " + valores + \
        ". A Análise de Tendência classifica essa série como “" + s["rotulo"] + "”."
    if s["desacelera"]:
        habitual = "Sinal descritivo, sem intensidade."
        if s["persistente"]:
            observado += " A mesma classe apareceu na janela encerrada um ano antes."
            habitual += " A repetição da classe em dois anos seguidos é uma leitura exploratória: na base, ocorre menos do que o " \
                "acaso produziria e não antecipa o crescimento seguinte."
        return {"situacao": "Desaceleração do crescimento" + (" · repetida (exploratória)" if s["persistente"] else ""),
                "observado": observado, "habitual": habitual, **comum}
    # Sem a classe: o fenômeno descreve séries em crescimento. Em declínio ou sem classificação de tendência, não se aplica.
    familia = FAMILIA_DA_TENDENCIA[s["tendencia"]]
    if familia == "DECLINIO":
        return {"situacao": "Não se aplica: a série está em declínio.", "observado": observado,
                "habitual": "Não se aplica: o fenômeno descreve séries em crescimento.", **comum}
    if familia == "NENHUMA":
        return {"situacao": "Não se aplica: a série não tem classificação de tendência.", "observado": observado,
                "habitual": "Não se aplica: o fenômeno descreve séries em crescimento.", **comum}
    return {"situacao": "Sem desaceleração: " + ("o crescimento está acelerando." if s["tendencia"] == "CRESCIMENTO_ACELERADO"
                                                  else "a série está em crescimento."), "observado": observado,
            "habitual": "Sem sinal.", **comum}


def _texto_instabilidade(base: Base, av: dict) -> dict:
    s = av["instabilidade"]
    comum = {"criterio": "Desvio-padrão das variações entre 7 registros, dividido pela oscilação típica do porte (c·N̄^(θ/2), com θ = "
                         "1,35 e c estimado por tipo de intervalo, de 5 ou 7 meses, só com transições anteriores). Com média abaixo "
                         "de 6 médicos, não é calculado. Sem intensidade: indicador descritivo.",
             "significa": "Diz se a série deste território oscila mais ou menos que o comum para o porte; projeções para uma série "
                          "que oscila muito tendem a ser menos estáveis.",
             "nao_significa": "Não mede rotatividade de pessoas: a base conta médicos por território, sem acompanhar cada "
                              "profissional. " + NAO_SIGNIFICA_GERAL}
    if s["estado"] in ("janela_insuficiente", "ausencia_de_dado"):
        return {"situacao": "Não calculável nesta data.", "observado": "O indicador usa 7 registros seguidos até a data avaliada, e "
                "falta algum deles.", "habitual": "Não calculável.", **comum}
    periodo = "Nos 7 registros de " + curta(s["de"]) + " a " + curta(s["ate"]) + ", a média foi de " + _br(s["media"], 1) + " médicos"
    if s["estado"] == "nao_calculavel":
        return {"situacao": "Não calculável (menos de 6 médicos, em média).", "observado": periodo + ".",
                "habitual": "Não calculável: com menos de 6 médicos em média (ou sem base de comparação nesta data), a oscilação "
                            "típica não é estimada.", **comum}
    if s["estado"] == "nivel_sem_classificacao":
        return {"situacao": "Sem comparação neste nível.", "observado": periodo + ", com " + str(s["inversoes"]) +
                (" inversão" if s["inversoes"] == 1 else " inversões") + " de direção.", "habitual": SEM_CALIBRACAO_DO_NIVEL, **comum}
    if s["estado"] == "descontinuidade_de_registro":
        return {"situacao": "Não calculado: descontinuidade de registro no período.", "observado": periodo + ".",
                "habitual": "Os 7 registros incluem uma descontinuidade de registro: o indicador não é calculado.", **comum}
    vezes = " vez" if s["indice"] < 2 else " vezes"
    return {"situacao": "Oscilação de " + _br(s["indice"], 1) + vezes + " a típica do porte.",
            "observado": periodo + ", e a oscilação entre os registros foi " + _br(s["indice"], 2) + vezes +
            " a oscilação típica de municípios do mesmo porte, com " + str(s["inversoes"]) +
            (" inversão" if s["inversoes"] == 1 else " inversões") + " de direção.",
            "habitual": "1 corresponde à oscilação típica; valores maiores indicam uma série mais irregular. Indicador descritivo, "
                        "sem intensidade.", **comum}


# --------------------------------------------------------------------------------------------- textos dos fenômenos 8 a 12
SEM_VALIDACAO = ("Sem classificação de intensidade: os limites deste indicador são provisórios e ainda não foram conferidos com a "
                 "base. O fato fica como sinal observado.")


def _populacao_nao_comparavel(base: Base, s: dict) -> str:
    """O motivo da comparação não habilitada, lido da própria base: os anos em que a população se repete ou salta, e os trechos
    comparáveis."""
    periodos = base.periodos
    motivo = comparativos.motivo_da_janela(base, periodos.index(s["de"]) if s.get("de") in periodos else None,
                                           periodos.index(s["ate"]) if s.get("ate") in periodos else None)
    return (motivo or "a população da base não é comparável de um ano para o outro nesta janela") + \
        "; população comparável nesta base: " + comparativos.texto_dos_trechos(base)
NOMES_DOS_SINAIS = {"forte": "sinal observado forte", "muito_forte": "sinal observado muito forte", "queda": "queda de posição observada"}


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


def _sem_variacao(base: Base, s: dict, nivel: str) -> dict | None:
    """Os estados em que a variação não existe: o nível da data continua à vista, com o motivo."""
    if s["estado"] == "comparacao_nao_habilitada":
        return {"situacao": nivel + " · comparação não habilitada",
                "habitual": "Comparação não habilitada: de " + curta(s["de"]) + " a " + curta(s["ate"]) + ", " + _populacao_nao_comparavel(base, s) + "."}
    if s["estado"] == "janela_insuficiente":
        return {"situacao": nivel + " · janela insuficiente", "habitual": "Janela insuficiente: falta o registro de junho de dois anos antes."}
    return None


def _texto_disponibilidade(base: Base, av: dict, p: dict) -> dict:
    s, limites = av["disponibilidade"], p["disponibilidade"]
    comum = {"criterio": "Taxa de médicos por 1.000 habitantes (a contagem do território ÷ a população estimada da mesma competência; "
                         "num conjunto, a soma das contagens ÷ a soma das populações), comparada de junho a junho em 2 anos. Queda de " +
                         _pct(limites["forte"], 0) + " ou mais: sinal forte; de " + _pct(limites["muito_forte"], 0) + " ou mais: muito "
                         "forte. " + LIMITES_PROVISORIOS + " A variação só é calculada em trechos com população comparável (" +
                         comparativos.texto_dos_trechos(base) + "); com menos de " + str(comparativos.MINIMO_DE_MEDICOS) +
                         " médicos no início da janela, o indicador é "
                         "descritivo.",
             "significa": "Há menos médicos registrados por habitante do que dois anos antes, pela combinação da mudança no número "
                          "de médicos e na população.",
             "nao_significa": "Não mede acesso, cobertura nem qualidade do atendimento, e a população é uma estimativa. " + NAO_SIGNIFICA_GERAL}
    if s["estado"] == "ausencia_de_dado":
        return {"situacao": "Sem registro na data.", "observado": "Falta o registro do território em " + curta(s["competencia"]) +
                " ou numa das datas da janela (ausência de dado não é zero).", "habitual": "Não avaliável.", **comum}
    if s["estado"] == "nao_calculavel":
        return {"situacao": "Não calculável.", "observado": s["motivo"], "habitual": "Não calculável.", **comum}
    nivel = _taxa(s["taxa"]) + " por 1.000 habitantes em " + curta(s["competencia"])
    na_data = "Em " + curta(s["competencia"]) + ", a taxa é de " + _taxa(s["taxa"]) + " por 1.000 habitantes (" + \
        _br(s["populacao"]) + " habitantes)."
    sem = _sem_variacao(base, s, nivel)
    if sem:
        return {**sem, "observado": na_data + " A variação em 2 anos não é calculada nesta janela.", **comum}
    m, pop = s["medicos"], s["populacao_da_janela"]
    observado = "De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", a taxa passou de " + _taxa(s["taxa_inicial"]) + " para " + \
        _taxa(s["taxa_final"]) + " por 1.000 habitantes (" + _variacao(s["variacao_pct"]) + "). O número de médicos passou de " + \
        _br(m["inicial"]) + " para " + _br(m["final"]) + " (" + _variacao(m["variacao_pct"]) + "), e a população, de " + \
        _br(pop["inicial"]) + " para " + _br(pop["final"]) + " (" + _variacao(pop["variacao_pct"]) + ")."
    situacao = _variacao(s["variacao_pct"]) + " na taxa por habitante em 2 anos"
    if s["estado"] == "descritivo":
        return {"situacao": situacao + " · descritivo", "observado": observado,
                "habitual": "Descritivo: com menos de " + str(comparativos.MINIMO_DE_MEDICOS) + " médicos no início da janela, poucas "
                            "unidades mudam muito o percentual.", **comum}
    if s["estado"] == "sem_sinal":
        return {"situacao": situacao + " · sem sinal", "observado": observado,
                "habitual": "A taxa não caiu " + _pct(limites["forte"], 0) + " ou mais em 2 anos.", **comum}
    return {"situacao": situacao + " · " + NOMES_DOS_SINAIS[s["sinal"]], "observado": observado, "habitual": SEM_VALIDACAO, **comum}


def _texto_posicao(base: Base, av: dict, p: dict) -> dict:
    s, limites = av["posicao"], p["posicao"]
    comum = {"criterio": "Percentil do território pela taxa de médicos por 1.000 habitantes, no universo dos territórios do mesmo "
                         "tipo com taxa válida ((posto médio − 0,5) ÷ n, com os empates no posto médio), fixo na janela de junho a "
                         "junho em 2 anos. Queda de " + _br(limites["queda"]) + " pontos ou mais: queda de posição; de " +
                         _br(limites["forte"]) + " ou mais, terminando até o percentil " + _br(limites["forte_final"]) + ": forte; de " +
                         _br(limites["muito_forte"]) + " ou mais, terminando até o percentil " + _br(limites["muito_forte_final"]) +
                         " e repetida em duas avaliações anuais: muito forte. " + LIMITES_PROVISORIOS + " Só em trechos com população "
                         "comparável; com menos de " + str(comparativos.MINIMO_DE_MEDICOS) + " médicos no início da janela, descritivo.",
             "significa": "O território perdeu posição entre os territórios comparados: outros passaram à frente dele na taxa por "
                          "habitante.",
             "nao_significa": "Perder posição não é o mesmo que perder médicos: o território pode ter crescido menos que os outros. " +
                              NAO_SIGNIFICA_GERAL}
    if s["estado"] == "nao_aplicavel":
        return {"situacao": "Não se aplica a conjuntos.", "observado": s["motivo"], "habitual": "Não se aplica.", **comum}
    if s["estado"] == "ausencia_de_dado":
        return {"situacao": "Sem registro na data.", "observado": "Não há registro do território em " + curta(s["competencia"]) +
                " (ausência de dado não é zero).", "habitual": "Não avaliável.", **comum}
    if s["estado"] == "nao_calculavel" and s["percentil"] is None:
        return {"situacao": "Não calculável.", "observado": s["motivo"], "habitual": "Não calculável.", **comum}
    nivel = "Percentil " + _br(round(s["percentil"])) + " entre " + _br(s["universo"]) + " " + s["nome_do_universo"].split(" com ")[0] + \
        " em " + curta(s["competencia"])
    na_data = "Em " + curta(s["competencia"]) + ", o território está no percentil " + _br(round(s["percentil"], 1)) + " da taxa por " \
        "habitante, entre " + _br(s["universo"]) + " " + s["nome_do_universo"] + " (0 é a menor taxa; 100, a maior)."
    if s["estado"] == "nao_calculavel":
        return {"situacao": nivel + " · variação não calculável", "observado": na_data + " " + s["motivo"], "habitual": "Não calculável.", **comum}
    sem = _sem_variacao(base, s, nivel)
    if sem:
        return {**sem, "observado": na_data + " A variação em 2 anos não é calculada nesta janela.", **comum}
    observado = "De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", o território passou do percentil " + _br(round(s["percentil_inicial"], 1)) + \
        " para o " + _br(round(s["percentil_final"], 1)) + " (" + _pontos(s["variacao_pp"]) + "), entre " + _br(s["universo_da_janela"]) + \
        " territórios com taxa válida nas duas datas."
    situacao = _pontos(s["variacao_pp"]) + " de percentil em 2 anos"
    if s["estado"] == "descritivo":
        return {"situacao": situacao + " · descritivo", "observado": observado,
                "habitual": "Descritivo: com menos de " + str(comparativos.MINIMO_DE_MEDICOS) + " médicos no início da janela, poucas "
                            "unidades mudam muito a taxa e a posição.", **comum}
    if s["estado"] == "sem_sinal":
        return {"situacao": situacao + " · sem sinal", "observado": observado,
                "habitual": "O território não perdeu " + _br(limites["queda"]) + " pontos ou mais de percentil em 2 anos.", **comum}
    habitual = SEM_VALIDACAO
    if s.get("confirmada") is False:
        habitual += " A queda chega ao limite do sinal muito forte, mas não se repetiu em duas avaliações anuais."
    return {"situacao": situacao + " · " + NOMES_DOS_SINAIS[s["sinal"]], "observado": observado, "habitual": habitual, **comum}


def _texto_defasagem(base: Base, av: dict, p: dict) -> dict:
    s, limites = av["defasagem"], p["defasagem"]
    rotulo = s["referencia"]["rotulo"]   # "demais municípios do Amazonas (soma municipal)": nunca dentro de outros parênteses
    comum = {"criterio": "Índice = 100 × taxa do território ÷ taxa da referência, com a referência na mesma unidade do território e "
                         "sem ele" + (": " + rotulo if rotulo else "") + ". A variação vai de junho a junho, em 2 anos. Queda de " +
                         _br(limites["forte"]) + " pontos ou "
                         "mais, com o índice final abaixo de " + _br(limites["forte_final"]) + ": sinal forte; de " +
                         _br(limites["muito_forte"]) + " ou mais, com o final abaixo de " + _br(limites["muito_forte_final"]) +
                         ": muito forte. " + LIMITES_PROVISORIOS + " Só em trechos com população comparável; com menos de " +
                         str(comparativos.MINIMO_DE_MEDICOS) + " médicos no início da janela, descritivo.",
             "significa": "A taxa do território ficou mais distante, para baixo, da taxa da referência.",
             "nao_significa": "A referência é uma comparação, não uma meta nem um padrão de suficiência. " + NAO_SIGNIFICA_GERAL}
    if s["estado"] == "referencia_invalida":
        return {"situacao": "Referência inválida.", "observado": s["motivo"], "habitual": "Não avaliável.", **comum}
    if s["estado"] == "ausencia_de_dado":
        return {"situacao": "Sem registro na data.", "observado": "Não há registro do território em " + curta(s["competencia"]) +
                " (ausência de dado não é zero).", "habitual": "Não avaliável.", **comum}
    if s["estado"] == "nao_calculavel" and s["indice"] is None:
        return {"situacao": "Não calculável.", "observado": s["motivo"], "habitual": "Não calculável.", **comum}
    nivel = "Índice " + _br(round(s["indice"], 1)) + " ante a referência em " + curta(s["competencia"])
    na_data = "Em " + curta(s["competencia"]) + ", a taxa do território é de " + _taxa(s["taxa"]) + " por 1.000 habitantes, e a " + \
        ("dos " + rotulo if rotulo else "da referência") + ", de " + _taxa(s["referencia"]["taxa"]) + ": índice " + _br(round(s["indice"], 1)) + \
        " (100 é a taxa da referência)."
    if s["estado"] == "nao_calculavel":
        return {"situacao": nivel + " · variação não calculável", "observado": na_data + " " + s["motivo"], "habitual": "Não calculável.", **comum}
    sem = _sem_variacao(base, s, nivel)
    if sem:
        return {**sem, "observado": na_data + " A variação em 2 anos não é calculada nesta janela.", **comum}
    observado = "De " + curta(s["de"]) + " a " + curta(s["ate"]) + ", o índice passou de " + _br(round(s["indice_inicial"], 1)) + " para " + \
        _br(round(s["indice_final"], 1)) + " (" + _pontos(s["variacao_pontos"]) + "). " + na_data
    situacao = _pontos(s["variacao_pontos"]) + " no índice ante a referência em 2 anos"
    if s["estado"] == "descritivo":
        return {"situacao": situacao + " · descritivo", "observado": observado,
                "habitual": "Descritivo: com menos de " + str(comparativos.MINIMO_DE_MEDICOS) + " médicos no início da janela, poucas "
                            "unidades mudam muito a taxa e o índice.", **comum}
    if s["estado"] == "sem_sinal":
        return {"situacao": situacao + " · sem sinal", "observado": observado,
                "habitual": "O índice não caiu " + _br(limites["forte"]) + " pontos ou mais com o final abaixo de " +
                            _br(limites["forte_final"]) + ".", **comum}
    return {"situacao": situacao + " · " + NOMES_DOS_SINAIS[s["sinal"]], "observado": observado, "habitual": SEM_VALIDACAO, **comum}


def _texto_contexto(base: Base, av: dict, p: dict) -> dict:
    s = av["contexto"]
    c = s["criterio"]
    limiar = "" if c["taxa_minima"] is None else _taxa(c["taxa_minima"]) + " por 1.000 habitantes em " + curta(c["competencia"]) + \
        " (" + _pct(p["contexto"]["taxa_do_brasil_pct"], 0) + " da taxa do Brasil, de " + _taxa(c["taxa_do_brasil"]) + ")"
    comum = {"criterio": "Distância em linha reta (geodésica, SIRGAS 2000) entre as coordenadas do território e as do município mais "
                         "próximo com taxa igual ou maior que " + (limiar or "o critério") + ". O percentil compara essa distância "
                         "com a dos " + _br(s["universo"]) + " municípios que não atendem ao critério. Só contexto, sem intensidade.",
             "significa": "Diz a que distância, em linha reta, fica o município mais próximo com mais médicos por habitante que o "
                          "critério.",
             "nao_significa": "Não é distância por estrada, tempo de viagem nem acesso. Não indica isolamento, falta de atendimento "
                              "nem como a rede de saúde se organiza, e não tem intensidade."}
    if s["estado"] == "nao_aplicavel":
        return {"situacao": "Não se aplica a estados como unidade.", "observado": s["motivo"], "habitual": "Não se aplica.", **comum}
    if s["estado"] == "atende_ao_criterio":
        return {"situacao": "O território atende ao critério.", "observado": "A taxa do território (ou de um dos componentes do "
                "conjunto) é igual ou maior que " + limiar + ": não há distância a medir.", "habitual": "Só contexto.", **comum}
    if s["estado"] != "contexto":
        return {"situacao": "Sem coordenada válida." if s["estado"] == "sem_coordenada" else "Não calculável.",
                "observado": s["motivo"], "habitual": "Não calculável.", **comum}
    r = s["referencia"]
    observado = ("O componente mais próximo do critério é " + s["membro"] + ": fica a " if s.get("membro") else "O território fica a ") + \
        _br(round(s["distancia_km"], 1)) + " km, em linha reta, de " + r["rotulo"] + " (" + _taxa(r["taxa"]) + " por 1.000 habitantes), o " \
        "município mais próximo com taxa igual ou maior que " + limiar + "."
    habitual = "Só contexto, sem classificação."
    if s["percentil_da_distancia"] is not None:
        habitual = "A distância é maior que a de " + _pct(s["percentil_da_distancia"], 0) + " dos municípios que não atendem ao " \
            "critério. Só contexto, sem classificação."
    return {"situacao": "A " + _br(round(s["distancia_km"], 1)) + " km de " + r["rotulo"] + ", em linha reta", "observado": observado,
            "habitual": habitual, **comum}


def _texto_coexistencia(base: Base, av: dict) -> dict:
    s = av["coexistencia"]
    comum = {"criterio": "Combinações pré-definidas de sinais do mesmo território: " +
                         "; ".join(texto[0].lower() + texto[1:] for _, texto in comparativos.COMBINACOES) + ". Não há soma de pontos "
                         "nem índice geral.",
             "significa": "Mais de um sinal aparece no mesmo território, o que ajuda a ler o conjunto.",
             "nao_significa": "Sinais que vêm da mesma queda no número de médicos não são evidências independentes: contam como um "
                              "evento com várias repercussões. As combinações não têm intensidade nem dizem o que fazer. " +
                              NAO_SIGNIFICA_GERAL}
    partes = []
    if s["combinacoes"]:
        partes.append("Combinações presentes: " + "; ".join(c["texto"][0].lower() + c["texto"][1:] for c in s["combinacoes"]) + ".")
    else:
        partes.append("Nenhuma das combinações pré-definidas aparece.")
    if len(s["repercussoes"]) > 1:
        partes.append("Os sinais " + ", ".join(s["repercussoes"]) + " vêm de quedas no número de médicos e podem ser repercussões do "
                      "mesmo evento: contam como uma frente de sinal.")
    if s["frentes"]:
        partes.append("Frentes de sinal: " + ", ".join(s["frentes"]) + ".")
    n = len(s["combinacoes"])
    return {"situacao": "Sem combinação de sinais." if not n else str(n) + (" combinação de sinais" if n == 1 else " combinações de sinais"),
            "observado": " ".join(partes),
            "habitual": "Sem classificação: as combinações ainda não foram testadas com a base e não formam um índice.", **comum}


def fenomenos(base: Base, av: dict, e: int, p: dict) -> list[dict]:
    """Os detalhes de cada fenômeno, em textos fixos: o que foi observado, o critério, quanto difere do habitual, o que significa,
    o que não significa, as limitações do dado e a qualidade do registro."""
    textos = {"estrutural": _texto_estrutural(base, av, e, p), "declinio": _texto_declinio(base, av, p),
              "perda": _texto_perda(base, av, p), "patamar": _texto_patamar(base, av, p),
              "desaceleracao": _texto_desaceleracao(base, av), "instabilidade": _texto_instabilidade(base, av),
              "disponibilidade": _texto_disponibilidade(base, av, p), "posicao": _texto_posicao(base, av, p),
              "defasagem": _texto_defasagem(base, av, p), "contexto": _texto_contexto(base, av, p),
              "coexistencia": _texto_coexistencia(base, av)}
    limitacoes, qualidade = _limitacoes(base, av), texto_do_registro(av["registro"])
    return [{"chave": chave, "numero": numero, "nome": nome, "dimensao": dimensao, "estado": av[chave]["estado"],
             "classe": av[chave].get("classe"), **textos[chave], "limitacoes": limitacoes, "qualidade": qualidade}
            for chave, numero, nome, dimensao in FENOMENOS]


# --------------------------------------------------------------------------------------------- resposta
def _linha(av: dict) -> dict:
    """A linha da tabela: só o que a tabela e os filtros usam (os detalhes vêm no pedido de um território)."""
    e, pe, pa, de, ds, ins = (av[chave] for chave in ("estrutural", "perda", "patamar", "declinio", "desaceleracao", "instabilidade"))
    di, po, df, co, cx = (av[chave] for chave in ("disponibilidade", "posicao", "defasagem", "contexto", "coexistencia"))
    anteriores = nomes_anteriores.do_rotulo(av["id"], av["rotulo"]) if av["tipo"] == "municipio" else []
    return {
        "id": av["id"], "tipo": av["tipo"], "nivel": av["nivel"], "rotulo": av["rotulo"], "uf": av["uf"],
        **({"nomes_anteriores": anteriores} if anteriores else {}),   # só para a busca por nome ("Parati" acha PARATY)
        "ultima": av["ultima"], "porte": av["porte"], "sinais": av["sinais"], "dimensoes": av["dimensoes"],
        "estrutural": {"estado": e["estado"], "classe": e.get("classe"), "n": e.get("n"), "impacto_pct": e.get("impacto_pct"),
                       "zeros": (e.get("zeros") or {}).get("registros"), "mantida": bool(e.get("mantida_pela_anterior"))},
        "perda": {"estado": pe["estado"], "classe": pe.get("classe"), "delta": pe.get("delta"), "pct": pe.get("pct"),
                  "de": pe.get("de"), "ate": pe.get("ate"), "magnitude": pe.get("magnitude"), "motivo": pe.get("motivo"),
                  "verificar": pe.get("verificar_registro")},
        "patamar": {"estado": pa["estado"], "classe": pa.get("classe"), "patamar": pa.get("patamar"),
                    "diferenca_pct": pa.get("diferenca_pct"), "abaixo": bool(pa.get("abaixo_por_2")), "critica": pa.get("critica")},
        "declinio": {"estado": de["estado"], "reducoes": de.get("reducoes"), "perda_pct": de.get("perda_pct"), "sinal": de.get("sinal")},
        "desaceleracao": {"estado": ds["estado"], "desacelera": bool(ds.get("desacelera")), "persistente": ds.get("persistente"),
                          "rotulo": ds.get("rotulo")},
        "instabilidade": {"estado": ins["estado"], "indice": ins.get("indice")},
        "registro": {"estado": av["registro"]["estado"], "tipos": sorted({evento["tipo"] for evento in av["registro"]["eventos"]})},
        # Fenômenos 8 a 12: o nível da data, a variação (quando a comparação é habilitada) e o sinal observado.
        "disponibilidade": {"estado": di["estado"], "taxa": di.get("taxa"), "populacao": di.get("populacao"),
                            "variacao_pct": di.get("variacao_pct"), "sinal": di.get("sinal")},
        "posicao": {"estado": po["estado"], "percentil": po.get("percentil"), "universo": po.get("universo"),
                    "variacao_pp": po.get("variacao_pp"), "sinal": po.get("sinal")},
        "defasagem": {"estado": df["estado"], "indice": df.get("indice"), "variacao_pontos": df.get("variacao_pontos"),
                      "sinal": df.get("sinal")},
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


def _fonte(base: Base) -> dict:
    return {"base": "Brasil", "categoria": "MEDICINA", "versao": base.versao, "primeira": base.periodos[0],
            "ultima": base.periodos[-1], "competencias": len(base.periodos),
            "unidades": {"municipio": series_brasil.UNIDADE_MUNICIPIO, "estado": series_brasil.UNIDADE_ESTADO,
                         "conjunto": series_brasil.UNIDADE_CONJUNTO}}


def _notas(base: Base, personalizado: bool, niveis: set) -> list[str]:
    notas = ["Base: só médicos, com registros de janeiro e junho de " + base.periodos[0][:4] + " a " + base.periodos[-1][:4] +
             " (5 e 7 meses entre um e outro). O registro mais recente é " + curta(base.periodos[-1]) + ": os sinais descrevem a "
             "situação até essa data, não a de hoje.",
             "Fato observado, raridade e sinal são coisas diferentes: a mudança entre registros sempre aparece; a intensidade do "
             "sinal (atenção, alta, crítica) só existe quando há critério e comparação com territórios parecidos.",
             "Intensidade do sinal: caracteriza o indicador, com limites provisórios. Não é juízo de desassistência, de "
             "suficiência do atendimento nem de prioridade de provimento.",
             "Zero é registro observado (zero confirmado); a competência sem registro é ausência de dado, nunca zero.",
             "Comparação relativa (taxa por habitante, posição e defasagem ante a referência): a variação só é calculada em janelas "
             "de junho a junho, em 2 anos, dentro de um trecho de população comparável, lido da própria base; fora disso, \"comparação não "
             "habilitada\", com o nível da data à vista. Os limites são provisórios e não geram intensidade.",
             "Contexto geográfico: distância em linha reta até o município mais próximo que atende ao critério. Não é acesso, tempo "
             "de viagem nem isolamento, e não tem intensidade. Sinais combinados: sem índice geral; repercussões da mesma queda "
             "contam como um evento."]
    if niveis - {"municipios"}:
        notas.append("A comparação com territórios parecidos existe só para municípios: estados como unidade e conjuntos têm os "
                     "fatos e os indicadores descritivos, sem intensidade. O conjunto é a soma das contagens dos componentes, não o "
                     "número de médicos diferentes.")
    if personalizado:
        notas.append("Configuração personalizada — exploratória: os limites em uso são diferentes dos padrões, e os resultados não "
                     "substituem os da configuração padrão.")
    return notas


def _resumo(linhas: list[dict]) -> dict:
    def contar(chave, valores):
        return {valor or "nenhuma": sum(1 for linha in linhas if linha["dimensoes"][chave] == valor) for valor in valores}
    return {"territorios": len(linhas),
            "por_tipo": {tipo: sum(1 for linha in linhas if linha["tipo"] == tipo) for tipo in ("municipio", "estado", "conjunto")},
            "estrutural": contar("estrutural", ("critica", "alta", "atencao", None)),
            "trajetoria": contar("trajetoria", ("critica", "alta", "atencao", None)),
            "sinais": {sinal: sum(1 for linha in linhas if sinal in linha["sinais"])
                       for sinal in ("estrutural", "ausencia", "perda", "alerta_perda", "patamar", "declinio", "desaceleracao", "registro",
                                     "disponibilidade", "posicao", "defasagem", "combinados")},
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


def _historico(base: Base, cal: Calibracao, territorio: Territorio, inicio: int, e: int, p: dict) -> list[dict]:
    """O histórico de sinais na janela: a situação de cada data, avaliada só com o que era conhecido nela."""
    saida = []
    for i in range(inicio, e + 1):
        av = avaliar(base, cal, territorio, inicio, i, p, comparar=False)
        junho = base.periodos[i].endswith("06")
        saida.append({
            "competencia": base.periodos[i], "valor": av["ultima"]["valor"] if av["ultima"] and av["ultima"]["na_data"] else None,
            "estrutural": av["estrutural"].get("classe"),
            "perda": None if av["perda"].get("delta", 0) >= 0 or av["perda"]["estado"] in ("ausencia_de_dado", "janela_insuficiente")
            else {"delta": av["perda"]["delta"], "pct": av["perda"]["pct"], "estado": av["perda"]["estado"],
                  "classe": av["perda"].get("classe")},
            "patamar": {"estado": av["patamar"]["estado"], "classe": av["patamar"].get("classe"),
                        "diferenca_pct": av["patamar"].get("diferenca_pct")},
            "declinio": {"reducoes": av["declinio"].get("reducoes"), "sinal": av["declinio"].get("sinal")} if junho else None,
            "desaceleracao": {"desacelera": bool(av["desaceleracao"].get("desacelera")),
                              "rotulo": av["desaceleracao"].get("rotulo")} if junho else None,
        })
    return saida


def _comparativo(base: Base, territorio: Territorio, e: int) -> dict:
    """As séries do território para os gráficos dos fenômenos 8 e 10: a taxa por 1.000 habitantes, a taxa da referência (na mesma
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


def compute(sources, opcoes: dict) -> dict:
    """POST /api/detector. Sem `detalhe`: a tabela da situação mais recente da janela, de todos os territórios da seleção, com o
    resumo, os limiares da data e os parâmetros em uso. Com `detalhe` (o id de um território da seleção): a série, o histórico de
    sinais e os textos de cada fenômeno. Nada é registrado na sessão, e nada vai ao provedor de IA."""
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
             "exploratorio": personalizado}
    detalhe = opcoes.get("detalhe")
    if detalhe is not None:
        alvo = next((territorio for territorio in territorios if territorio.id == detalhe), None)
        if alvo is None:
            raise ValueError("Território fora da seleção do Detector: " + str(detalhe) + ".")
        comeco = _inicio_do_territorio(cal, alvo, inicio, e)
        av = avaliar(base, cal, alvo, comeco, e, p, inicio)
        return {**comum, "territorio": av, "janela_do_territorio": {"inicio": base.periodos[comeco], "depois_da_quebra": comeco != inicio},
                "serie": _serie(base, cal, alvo, e), "historico": _historico(base, cal, alvo, comeco, e, p),
                "comparativo": _comparativo(base, alvo, e), "coordenadas": _coordenadas(base, qd, [alvo], [_linha(av)]),
                "fenomenos": fenomenos(base, av, e, p), "notas": _notas(base, personalizado, {alvo.nivel})}
    linhas = [_linha(avaliar(base, cal, territorio, _inicio_do_territorio(cal, territorio, inicio, e), e, p, inicio))
              for territorio in territorios]
    return {**comum, "linhas": linhas, "resumo": _resumo(linhas), "calibracao": limiares(base, cal, e, p),
            "coordenadas": _coordenadas(base, qd, territorios, linhas),
            "notas": _notas(base, personalizado, {territorio.nivel for territorio in territorios}),
            "limitacoes": ["LIMITES_PROVISORIOS", "CALIBRACAO_SO_MUNICIPAL", "COMPARACAO_SO_COM_POPULACAO_COMPARAVEL"] +
                          (["CONFIGURACAO_EXPLORATORIA"] if personalizado else [])}
