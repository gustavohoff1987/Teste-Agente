"""Simulador de Cenários Territoriais (comando V22, Eixo II, etapa 4: o núcleo — seleção local, métodos de base, intervenções,
retroprojeções, faixas e textos de cenário). Referência metodológica: Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2.5, 7 a 9, 11 e
8.8 (que prevalece). A tela e a rota estão em Docs/SIMULADOR_DE_CENARIOS.md.

O Simulador é a **exceção aprovada** à exclusão de projeção da SPEC (FAM-08, Caso 4; AT-04), restrita a esta ferramenta
determinística (decisão 2 do comando V22). Tudo o que ele entrega é **cenário hipotético condicional**: nunca previsão, observação
atual, conclusão assistencial nem recomendação de provimento. Os textos de cenário vêm só do modelo fixo da seção 2.5, montados
aqui, sem o provedor de IA.

Tendência-base e intervenção ficam separadas (seção 9):

    N(t) = max(0, B(t) + I(t))        I(t) = Σ a_j · S(t − t_j),   S(u) = 0 para u < 0

com t em anos reais desde a origem (o último registro usável da janela) e a permanência total (S = 1) como padrão, rotulada como
hipótese. O crescimento histórico nunca é aplicado aos médicos acrescentados.

Métodos de base (seção 8.8):

- **M0, persistência:** B(t) = N0. Sempre calculado: é a referência de comparação.
- **M0d, persistência com deriva do estado** (padrão provisório dos municípios): B(t) = N0 × (1 + g_UF)^t, com g_UF = o
  crescimento anual composto da soma municipal da UF nos 3 anos anteriores à origem. Volta ao M0, com aviso, sem os 3 anos ou com
  quebra de fonte na janela da deriva. Zero continua zero.
- **M1, taxa composta:** r = (Nf/Ni)^(1/T) − 1, com T real em anos e extremos acima de zero; B(t) = N0 × (1 + r)^t. É o padrão
  provisório dos estados como unidade (na janela de 3 anos da série do próprio nível), com aviso.
- **M2, tendência linear robusta (Theil–Sen):** inclinação = mediana das inclinações entre pares de registros; intercepto =
  mediana(y) − b · mediana(t); a projeção negativa não aparece como estoque válido.
- **M3, tendência log-linear:** Poisson com ligação log (IRLS); a dispersão quase-Poisson é só diagnóstico; série toda em zero,
  não calculável.
- **taxa manual:** a taxa anual digitada pela pessoa, como hipótese dela; o sistema nunca sugere uma.
- **conjuntos:** no M0 e no M0d, a soma das projeções dos membros (cada um com a deriva da sua UF); nos demais, o método na série
  da soma das contagens. Sempre rotulado.

A **média aritmética das taxas** (de junho a junho) é só estatística descritiva, ao lado da mediana, da dispersão e da taxa
composta: nunca alimenta uma projeção. Comparar janelas e métodos é sensibilidade a método e janela, não faixa de confiança.

**Faixas de 80%** (seção 8.8): só para o M0d municipal (e, como aproximação, para conjuntos de municípios), de 1 a 4 anos, pela
retroprojeção com origens móveis na própria base (P10 a P90 da razão observado ÷ projetado − 1, por porte na origem e horizonte);
a data intermediária usa a faixa do ano inteiro seguinte; a faixa é da base e se desloca com a intervenção. Fora disso,
"indisponível", sem extrapolar.
"""
from __future__ import annotations

import math
import threading
from contextvars import ContextVar
from dataclasses import dataclass

import numpy as np

import comparativos
import detector
import reguas
import series_brasil
from series_brasil import Base, Territorio, mes_da_competencia

# Numa base com um registro por ano ("AAAA00"), as datas do pedido e da resposta são anos. Vale para o pedido em curso.
_ANUAL: ContextVar[bool] = ContextVar("simulador_base_anual", default=False)

VERSION = "SIMULADOR-CENARIOS/V3/1"   # Proposta V3 (comando V23): o jeito de projetar escolhido pela base e as faixas conferidas no tempo
# Os nomes dos métodos nos textos (decisão D-C: linguagem simples). No anexo, a "deriva do estado" do M0d é o crescimento anual
# composto da soma municipal da UF; na tela e nos textos de cenário, "o crescimento recente do estado".
METODOS = ("padrao", "M0", "M0d", "M0g", "M1", "M2", "M3", "manual")
NOMES_DOS_METODOS = {
    "M0": "persistência (o último valor se mantém)",
    "M0d": "persistência com o crescimento recente do estado",
    "M0g": "persistência com o crescimento recente da base toda",
    "M1": "taxa composta da janela",
    "M2": "tendência linear robusta",
    "M3": "tendência log-linear",
    "manual": "taxa informada pela pessoa",
}
ANOS_DA_DERIVA = 3
ANOS_DA_JANELA_PADRAO = 3
HORIZONTES_DA_FAIXA = (1, 2, 3, 4)
# As faixas de porte são as dez da régua comum (Proposta V3, seção A.2.2), pelo número de profissionais na origem (N0 ≥ 1).
ROTULOS_DOS_PORTES_DA_FAIXA = reguas.ROTULOS_DOS_PORTES
# A escolha do jeito de projetar (seção C.3): os candidatos na ordem de proximidade do território (o próprio, o grupo de cima, a
# base toda), comparados com manter o último valor (M0).
PROXIMIDADE = ("M1", "M0d", "M0g")
MINIMO_DE_ORIGENS = 3                  # com menos origens de retroprojeção (ou de teste), não há escolha (nem conferência)
MINIMO_POR_PORTE_NA_ESCOLHA = 30       # os portes com menos casos juntam-se aos vizinhos
TOLERANCIA_DA_ESCOLHA = 0.05           # entre os que valem, fica o mais próximo a até 5% do melhor
# As faixas (seção C.4): os percentis do erro relativo, os casos mínimos (20 fora de cada lado) e a meta de cobertura, em %.
FAIXAS_EM_10 = {5: (25.0, 75.0, 80, 50), 8: (10.0, 90.0, 200, 80), 9: (5.0, 95.0, 400, 90)}
FAIXA_PADRAO = 8
MINIMO_DE_CASOS_DE_TESTE = 50          # com menos casos de teste, a faixa não pôde ser conferida no tempo: fica provisória
MINIMO_DE_CASOS_DA_FAIXA = FAIXAS_EM_10[FAIXA_PADRAO][2]
MAX_TERRITORIOS, MAX_CENARIOS, MAX_INTERVENCOES, MAX_EVENTOS = 100, 6, 12, 240
MAX_REFERENCIAS = 5
METRICAS = ("quantidade", "taxa")
# A comparação com uma referência (Proposta V3, seção C.5): pela diferença ou pela razão; por taxa, com a população igual à do
# último registro ou crescendo x% ao ano, uma hipótese da pessoa (a mesma taxa no território e na referência).
FORMAS_DA_COMPARACAO = ("diferenca", "razao")
MAX_CRESCIMENTO_DA_POPULACAO = 20.0   # % ao ano, para cima ou para baixo
ANO_LIMITE = 2100
PREVISAO_NAO = "Cenário hipotético, não é previsão"


# --------------------------------------------------------------------------------------------- ajustes (em lote)
def theil_sen(t: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Theil–Sen em lote: `t` (k,) em anos e `y` (n, k) sem ausentes. Inclinação = mediana das inclinações entre os pares de
    registros; intercepto = mediana(y) − b · mediana(t) (seção 8.8)."""
    i, j = np.triu_indices(len(t), 1)
    inclinacoes = (y[:, j] - y[:, i]) / (t[j] - t[i])[None, :]
    b = np.median(inclinacoes, axis=1)
    return np.median(y, axis=1) - b * np.median(t), b


def poisson(t: np.ndarray, y: np.ndarray, iteracoes: int = 60) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Regressão de Poisson com ligação log, por IRLS, em lote: log μ = α + β·t. Devolve α, β, a dispersão quase-Poisson (χ² de
    Pearson ÷ (k − 2); só diagnóstico) e quais séries convergiram. Série toda em zero não tem ajuste."""
    n, k = y.shape
    mu = y + 0.5
    eta = np.log(mu)
    alfa = np.zeros(n)
    beta = np.zeros(n)
    ok = y.sum(axis=1) > 0
    for _ in range(iteracoes):
        z = eta + (y - mu) / mu
        w = mu
        sw, swt, swtt = w.sum(axis=1), (w * t).sum(axis=1), (w * t * t).sum(axis=1)
        swz, swtz = (w * z).sum(axis=1), (w * t * z).sum(axis=1)
        det = sw * swtt - swt * swt
        with np.errstate(invalid="ignore", divide="ignore"):
            nova_beta = (sw * swtz - swt * swz) / det
            nova_alfa = (swz - nova_beta * swt) / sw
        ok &= np.isfinite(nova_alfa) & np.isfinite(nova_beta)
        nova_eta = np.clip(np.where(ok[:, None], nova_alfa[:, None] + nova_beta[:, None] * t[None, :], 0.0), -30, 30)
        mudou = np.abs(nova_eta - eta).max() if n else 0.0
        alfa, beta, eta = np.where(ok, nova_alfa, 0.0), np.where(ok, nova_beta, 0.0), nova_eta
        mu = np.exp(eta)
        if mudou < 1e-10:
            break
    with np.errstate(invalid="ignore", divide="ignore"):
        dispersao = ((y - mu) ** 2 / mu).sum(axis=1) / max(1, k - 2)
    return alfa, beta, np.where(ok, dispersao, np.nan), ok


# --------------------------------------------------------------------------------------------- retroprojeção (origens móveis)
# Uma linha por caso (território, origem, prazo): o ano da origem, o prazo em anos, a faixa de porte na origem, o valor na origem,
# o observado no alvo, a linha do território e a projeção de cada método.
ANO, PRAZO, PORTE, N0, OBSERVADO, LINHA = 0, 1, 2, 3, 4, 5
COLUNA = {"M0": 6, "M0d": 7, "M0g": 8, "M1": 9, "M2": 10, "M3": 11}
COLUNAS = 12


@dataclass(frozen=True)
class Retroprojecao:
    """A retroprojeção de um nível de território numa versão da base (Proposta V3, seções C.3 e C.4): os casos, o jeito de projetar
    que a própria base escolhe, as faixas por porte e prazo (com a conferência no tempo) e o erro de cada método frente ao M0."""
    versao: str
    nivel: str        # "municipios" (as unidades da base) ou "estados" (os grupos de cima como unidade, com a contagem própria)
    origens: tuple    # as competências das origens
    casos: np.ndarray
    escolha: dict     # {"metodo", "motivo", "origens", "combinacoes", "candidatos", "excecoes", "por_porte"}
    faixas: dict      # (em_10, porte, anos) → {"estado", "inferior", "superior", "casos", "como", "cobertura", …}
    tabela: tuple     # linhas {"metodo", "porte", "anos", "casos", "origens", "erro_absoluto_medio", "vies", "frente_ao_m0"}


_RETROS: dict[tuple, Retroprojecao] = {}
_LOCK = threading.Lock()


def _porte_da_faixa(valor) -> int | None:
    """A faixa de porte de um valor na origem (as dez da régua comum); None com zero, ausente ou abaixo de 1."""
    return reguas.porte_de(valor)


def _casos(b: Base, cal: detector.Calibracao) -> tuple[np.ndarray, list[int]]:
    """Os casos da retroprojeção de uma base, sem observações futuras: em cada registro do mês âncora com 3 anos de história e
    ao menos 1 ano à frente, cada método é ajustado só com os registros até a origem e confrontado com o observado 1, 2, 3 e 4
    anos depois. Entram os territórios com a janela de 3 anos inteira (sem ausência, sem pico conhecido até a origem e sem quebra
    de fonte), com pelo menos 1 na origem e 3 anos antes, e com o alvo observado, fora de pico e de quebra."""
    vazio = np.empty((0, COLUNAS))
    if not b.ancora:
        return vazio, []
    q = b.quantidade
    do_ano = {int(periodo[:4]): i for i, periodo in enumerate(b.periodos) if periodo.endswith(b.ancora)}
    anos = [ano for ano in sorted(do_ano) if ano - ANOS_DA_JANELA_PADRAO in do_ano and ano + 1 in do_ano
            and b.meses[do_ano[ano]] - b.meses[do_ano[ano - ANOS_DA_JANELA_PADRAO]] == 12 * ANOS_DA_JANELA_PADRAO]
    if not anos:
        return vazio, []
    toda = np.nansum(q, axis=0)
    somas = {grupo: np.nansum(q[list(linhas)], axis=0) for grupo, linhas in b.do_estado.items()}
    partes = []
    for ano in anos:
        o, antes = do_ano[ano], do_ano[ano - ANOS_DA_JANELA_PADRAO]
        janela = list(range(antes, o + 1))
        y, n0, n_antes = q[:, janela], q[:, o], q[:, antes]
        inteira = ~np.isnan(y).any(axis=1) & ~(cal.pico_conhecido[:, janela] <= o).any(axis=1) & ~cal.quebra[:, janela].any(axis=1)
        do_grupo = np.full(q.shape[0], np.nan)
        for grupo, linhas in b.do_estado.items():
            soma, linhas = somas[grupo], list(linhas)
            if soma[antes] > 0 and soma[o] > 0 and not cal.quebra[linhas, antes:o + 1].any():
                do_grupo[linhas] = (soma[o] / soma[antes]) ** (1.0 / ANOS_DA_JANELA_PADRAO) - 1
        da_base = (toda[o] / toda[antes]) ** (1.0 / ANOS_DA_JANELA_PADRAO) - 1 if toda[antes] > 0 and toda[o] > 0 else np.nan
        with np.errstate(invalid="ignore", divide="ignore"):
            proprio = np.where((n0 > 0) & (n_antes > 0), (n0 / n_antes) ** (1.0 / ANOS_DA_JANELA_PADRAO) - 1, np.nan)
        t = (b.meses[janela] - b.meses[o]) / 12.0
        y_limpo = np.where(inteira[:, None], y, 1.0)
        a2, b2 = theil_sen(t, y_limpo)
        a3, b3, _, ok3 = poisson(t, y_limpo)
        porte = reguas.portes(n0)
        for prazo in HORIZONTES_DA_FAIXA:
            if ano + prazo not in do_ano or b.meses[do_ano[ano + prazo]] - b.meses[o] != 12 * prazo:
                continue
            alvo = do_ano[ano + prazo]
            observado = q[:, alvo]
            with np.errstate(invalid="ignore"):
                valido = inteira & (n0 >= 1) & (n_antes >= 1) & ~np.isnan(observado) & ~cal.pico[:, alvo] & ~cal.quebra[:, alvo]
            linhas = np.nonzero(valido)[0]
            if not linhas.size:
                continue
            bloco = np.full((linhas.size, COLUNAS), np.nan)
            bloco[:, ANO], bloco[:, PRAZO], bloco[:, PORTE], bloco[:, LINHA] = ano, prazo, porte[linhas], linhas
            bloco[:, N0], bloco[:, OBSERVADO] = n0[linhas], observado[linhas]
            with np.errstate(invalid="ignore", over="ignore"):
                bloco[:, COLUNA["M0"]] = n0[linhas]
                bloco[:, COLUNA["M0d"]] = n0[linhas] * (1 + do_grupo[linhas]) ** prazo
                bloco[:, COLUNA["M0g"]] = n0[linhas] * (1 + da_base) ** prazo
                bloco[:, COLUNA["M1"]] = n0[linhas] * (1 + proprio[linhas]) ** prazo
                bloco[:, COLUNA["M2"]] = np.maximum(0.0, a2[linhas] + b2[linhas] * prazo)
                bloco[:, COLUNA["M3"]] = np.where(ok3[linhas], np.exp(np.clip(a3[linhas] + b3[linhas] * prazo, -30, 30)), np.nan)
            partes.append(bloco)
    return (np.vstack(partes) if partes else vazio), [do_ano[ano] for ano in anos]


def _grupos_de_porte(portes: np.ndarray, minimo: int = MINIMO_POR_PORTE_NA_ESCOLHA) -> list[list[int]]:
    """Os portes presentes, com os de menos de `minimo` casos juntados a um vizinho (regra C.3: cada porte tem o mesmo peso, e os
    portes com poucos casos juntam-se aos vizinhos)."""
    blocos = [[int(porte)] for porte in sorted(set(portes.astype(int).tolist()))]
    conta = lambda bloco: int(np.isin(portes, bloco).sum())   # noqa: E731
    while len(blocos) > 1:
        pequenos = [k for k, bloco in enumerate(blocos) if conta(bloco) < minimo]
        if not pequenos:
            break
        k = pequenos[-1]
        vizinho = k - 1 if k > 0 else k + 1
        a, b = sorted((k, vizinho))
        blocos[a:b + 1] = [blocos[a] + blocos[b]]
    return blocos


def _frente_ao_m0(casos: np.ndarray, coluna: int, mascara: np.ndarray) -> float | None:
    """O erro absoluto médio de um método frente ao de manter o último valor (1 = igual; abaixo de 1, erra menos), com cada grupo
    de porte pesando o mesmo."""
    if not mascara.any():
        return None
    erro = np.abs(casos[:, OBSERVADO] - casos[:, coluna])
    do_m0 = np.abs(casos[:, OBSERVADO] - casos[:, COLUNA["M0"]])
    partes = []
    for bloco in _grupos_de_porte(casos[mascara, PORTE]):
        do_bloco = mascara & np.isin(casos[:, PORTE], bloco)
        if do_m0[do_bloco].mean() > 0:
            partes.append(float(erro[do_bloco].mean() / do_m0[do_bloco].mean()))
    return float(np.mean(partes)) if partes else None


def _escolher(casos: np.ndarray, origens: int, tem_serie_anual: bool) -> dict:
    """O jeito de projetar que a própria base escolhe (regra C.3). Cada candidato é comparado com manter o último valor: só vale o
    que errou menos no total e em pelo menos metade das combinações de origem e prazo; entre os que valem, fica o mais próximo do
    território (o próprio, o grupo de cima, a base toda) cujo erro esteja a até 5% do melhor. Num porte em que o escolhido erra
    mais que manter o último valor em todos os prazos, vale o último valor. Com menos de 3 origens, o padrão é o último valor."""
    saida = {"metodo": "M0", "motivo": "escolhido", "origens": origens, "combinacoes": 0, "candidatos": [], "excecoes": [], "por_porte": []}
    if not tem_serie_anual:
        return {**saida, "motivo": "sem_serie_anual"}
    if origens < MINIMO_DE_ORIGENS or not casos.size:
        return {**saida, "motivo": "poucas_origens"}
    combinacoes = sorted({(int(ano), int(prazo)) for ano, prazo in zip(casos[:, ANO], casos[:, PRAZO])})
    saida["combinacoes"] = len(combinacoes)
    for metodo in PROXIMIDADE:
        coluna = COLUNA[metodo]
        com_projecao = np.isfinite(casos[:, coluna])
        if not com_projecao.any():
            continue
        total = _frente_ao_m0(casos, coluna, com_projecao)
        menos = 0
        for ano, prazo in combinacoes:
            da_combinacao = com_projecao & (casos[:, ANO] == ano) & (casos[:, PRAZO] == prazo)
            razao = _frente_ao_m0(casos, coluna, da_combinacao)
            menos += razao is not None and razao < 1
        saida["candidatos"].append({"metodo": metodo, "frente_ao_m0": total, "menos_erro_em": int(menos), "combinacoes": len(combinacoes),
                                    "casos": int(com_projecao.sum()),
                                    "vale": bool(total is not None and total < 1 and 2 * menos >= len(combinacoes))})
    valem = [item for item in saida["candidatos"] if item["vale"]]
    if not valem:
        return {**saida, "motivo": "nenhum_vale"}
    melhor = min(item["frente_ao_m0"] for item in valem)
    proximos = {item["metodo"] for item in valem if item["frente_ao_m0"] <= melhor * (1 + TOLERANCIA_DA_ESCOLHA) + 1e-12}
    saida["metodo"] = next(metodo for metodo in PROXIMIDADE if metodo in proximos)
    # A exceção por porte: onde o escolhido erra mais que manter o último valor em todos os prazos, vale o último valor.
    coluna = COLUNA[saida["metodo"]]
    erro = np.abs(casos[:, OBSERVADO] - casos[:, coluna])
    do_m0 = np.abs(casos[:, OBSERVADO] - casos[:, COLUNA["M0"]])
    for porte in sorted(set(casos[:, PORTE].astype(int).tolist())):
        razoes = []
        for prazo in HORIZONTES_DA_FAIXA:
            celula = np.isfinite(casos[:, coluna]) & (casos[:, PORTE] == porte) & (casos[:, PRAZO] == prazo)
            if celula.sum() >= MINIMO_POR_PORTE_NA_ESCOLHA and do_m0[celula].mean() > 0:
                razoes.append(float(erro[celula].mean() / do_m0[celula].mean()))
        saida["por_porte"].append({"porte": porte, "frente_ao_m0": razoes})
        if razoes and all(razao > 1 for razao in razoes):
            saida["excecoes"].append(porte)
    return saida


def _conjunto_da_faixa(casos: np.ndarray, com_projecao: np.ndarray, porte: int, prazo: int, minimo: int) -> tuple[np.ndarray | None, str]:
    """Os casos que formam a faixa de um porte num prazo (seção C.4 e a retaguarda da regra A.2.4): os do próprio porte; faltando
    casos, com as faixas vizinhas, uma de cada lado; ainda faltando, com portes menores, um a um (a faixa fica mais larga, e por
    isso mais cautelosa); se nada bastar, nenhuma."""
    do_prazo = com_projecao & (casos[:, PRAZO] == prazo)
    proprio = do_prazo & (casos[:, PORTE] == porte)
    if proprio.sum() >= minimo:
        return proprio, "propria"
    usados = do_prazo & (np.abs(casos[:, PORTE] - porte) <= 1)
    if usados.sum() >= minimo:
        return usados, "vizinhas"
    menor = porte - 1
    while usados.sum() < minimo and menor - 1 >= 0:
        menor -= 1
        usados = do_prazo & (casos[:, PORTE] >= menor) & (casos[:, PORTE] <= porte + 1)
    return (usados, "portes_menores") if usados.sum() >= minimo else (None, "indisponivel")


def _faixas(casos: np.ndarray, metodo: str) -> dict:
    """As faixas do jeito escolhido, por porte e prazo, para 5, 8 e 9 em cada 10 (seção C.4): os percentis do erro relativo
    (observado ÷ cenário − 1), com pelo menos 20 casos fora de cada lado, a retaguarda e a conferência no tempo — a faixa é
    remontada só com as retroprojeções cujo resultado já era conhecido em cada origem de teste e conferida nos casos dela."""
    saida = {}
    if not casos.size:
        return saida
    coluna = COLUNA[metodo]
    com_projecao = np.isfinite(casos[:, coluna]) & (casos[:, coluna] > 0)
    with np.errstate(invalid="ignore", divide="ignore"):
        razao = casos[:, OBSERVADO] / casos[:, coluna] - 1
    origens = sorted(set(casos[:, ANO].astype(int).tolist()))
    for em_10, (inferior, superior, minimo, meta) in FAIXAS_EM_10.items():
        for porte in range(len(reguas.PORTES)):
            for prazo in HORIZONTES_DA_FAIXA:
                do_porte = com_projecao & (casos[:, PORTE] == porte) & (casos[:, PRAZO] == prazo)
                usados, como = _conjunto_da_faixa(casos, com_projecao, porte, prazo, minimo)
                if usados is None:
                    # Quantos casos a base tem para este prazo, juntando tudo o que a retaguarda permite.
                    alcance = int((com_projecao & (casos[:, PRAZO] == prazo) & (casos[:, PORTE] <= porte + 1)).sum())
                    if do_porte.any():   # só os portes que a base tem neste prazo
                        saida[(em_10, porte, prazo)] = {"estado": "indisponivel", "motivo": "poucos_casos", "casos": alcance, "pede": minimo,
                                                        "como": como}
                    continue
                limites = np.percentile(razao[usados], [inferior, superior])
                dentro = testados = origens_de_teste = 0
                for origem in origens:
                    de_teste = do_porte & (casos[:, ANO] == origem)
                    if not de_teste.any():
                        continue
                    conhecidos, _ = _conjunto_da_faixa(casos, com_projecao & (casos[:, ANO] + prazo <= origem), porte, prazo, minimo)
                    if conhecidos is None:
                        continue
                    a, b = np.percentile(razao[conhecidos], [inferior, superior])
                    dentro += int(((razao[de_teste] >= a) & (razao[de_teste] <= b)).sum())
                    testados += int(de_teste.sum())
                    origens_de_teste += 1
                cobertura = (100.0 * dentro / testados) if testados else None
                if origens_de_teste < MINIMO_DE_ORIGENS or testados < MINIMO_DE_CASOS_DE_TESTE:
                    estado, motivo = "provisoria", "sem_conferencia"
                else:
                    # A cobertura é comparada em pontos percentuais inteiros, como aparece na tela (74,95% é 75%).
                    arredondada = math.floor(cobertura + 0.5)
                    estado, motivo = ("conferida", None) if arredondada >= meta - 5 else ("provisoria", "cobertura_abaixo") \
                        if arredondada >= meta - 10 else ("indisponivel", "cobertura_baixa")
                saida[(em_10, porte, prazo)] = {
                    "estado": estado, "motivo": motivo, "inferior": float(limites[0]), "superior": float(limites[1]),
                    "casos": int(usados.sum()), "pede": minimo, "como": como, "origens": len(set(casos[usados, ANO].astype(int).tolist())),
                    "cobertura": cobertura, "origens_de_teste": origens_de_teste, "casos_de_teste": testados, "meta": meta}
    return saida


def _tabela(casos: np.ndarray) -> tuple:
    """O erro de cada método por porte e prazo, frente a manter o último valor ("Como os métodos se saíram no passado")."""
    linhas = []
    if not casos.size:
        return ()
    do_m0 = np.abs(casos[:, OBSERVADO] - casos[:, COLUNA["M0"]])
    for metodo, coluna in COLUNA.items():
        for porte in sorted(set(casos[:, PORTE].astype(int).tolist())):
            for prazo in HORIZONTES_DA_FAIXA:
                celula = np.isfinite(casos[:, coluna]) & (casos[:, PORTE] == porte) & (casos[:, PRAZO] == prazo)
                if not celula.any():
                    continue
                erro = casos[celula, OBSERVADO] - casos[celula, coluna]
                soma_do_m0 = float(do_m0[celula].sum())
                linhas.append({"metodo": metodo, "porte": porte, "anos": prazo, "casos": int(celula.sum()),
                               "origens": len(set(casos[celula, ANO].astype(int).tolist())),
                               "erro_absoluto_medio": float(np.abs(erro).mean()), "vies": float(erro.mean()),
                               "frente_ao_m0": (float(np.abs(erro).sum()) / soma_do_m0) if soma_do_m0 > 0 else None})
    return tuple(linhas)


def retroprojetar(base: Base, nivel: str = "municipios", guardar: bool = True) -> Retroprojecao:
    """A retroprojeção de um nível de território (as unidades da base, ou os grupos de cima como unidade, quando a base tem a
    contagem própria deles), montada uma vez por versão da base: os casos, a escolha do jeito de projetar e as faixas."""
    chave = (base.versao, nivel)
    with _LOCK:
        guardada = _RETROS.get(chave) if guardar else None
    if guardada is not None:
        return guardada
    if nivel == "municipios":
        b, cal = base, detector.calibrar(base, guardar=guardar)
    else:
        b, cal = detector.base_dos_estados(base), detector.calibrar_estados(base)
    casos, origens = _casos(b, cal) if b is not None else (np.empty((0, COLUNAS)), [])
    escolha = _escolher(casos, len(origens), bool(b is not None and b.ancora))
    retro = Retroprojecao(versao=base.versao, nivel=nivel, origens=tuple(b.periodos[i] for i in origens) if b is not None else (),
                          casos=casos, escolha=escolha, tabela=_tabela(casos),
                          # Sem retroprojeção bastante, não há faixa. Quando nenhum candidato errou menos que manter o último
                          # valor, o jeito escolhido é o último valor, e a faixa é a dele.
                          faixas=_faixas(casos, escolha["metodo"]) if escolha["motivo"] in ("escolhido", "nenhum_vale") else {})
    if guardar:
        with _LOCK:
            for antiga in [k for k in _RETROS if k[0] != base.versao]:
                del _RETROS[antiga]
            _RETROS[chave] = retro
    return retro


# --------------------------------------------------------------------------------------------- pedido
def _competencia_futura(texto, nome: str) -> int:
    """Uma data AAAAMM (qualquer mês) como posição em meses; recusa o que não é data. Numa base com um registro por ano, a data é
    o ano ("AAAA00")."""
    anual = _ANUAL.get()
    if not isinstance(texto, str) or len(texto) != 6 or not texto.isdigit() or int(texto[:4]) > ANO_LIMITE or \
            not (int(texto[4:]) == 0 if anual else 1 <= int(texto[4:]) <= 12):
        raise ValueError(nome + " inválida: use " + ("o ano (AAAA00)" if anual else "ano e mês (AAAAMM)") + ", até " + str(ANO_LIMITE) + ".")
    return mes_da_competencia(texto)


def _data(mes: int) -> str:
    if _ANUAL.get() and (mes + 1) % 12 == 0:
        return str((mes + 1) // 12) + "00"
    return str(mes // 12) + str(mes % 12 + 1).zfill(2)


def _inicio_padrao(base: Base, fim: int) -> int:
    """O primeiro registro dos 3 anos até `fim`, pelo tempo e não pela contagem de registros (na base do Brasil, com dois
    registros por ano, são 7 registros; numa base com um registro por ano, 4)."""
    inicio = int(np.searchsorted(base.meses, base.meses[fim] - 12 * ANOS_DA_JANELA_PADRAO))
    # Numa base com registros espaçados, nenhum outro registro cai nesses 3 anos: a janela começa no registro anterior.
    return max(0, fim - 1) if inicio >= fim else inicio


def _janela(base: Base, bruto, padrao_ate: int | None = None) -> tuple[int, int, bool]:
    """A janela histórica: início e fim entre as competências reais. Sem pedido, os 3 anos até o último registro."""
    fim_padrao = len(base.periodos) - 1 if padrao_ate is None else padrao_ate
    if bruto in (None, {}):
        return _inicio_padrao(base, fim_padrao), fim_padrao, True
    if not isinstance(bruto, dict):
        raise ValueError("Janela inválida: envie inicio e fim, com competências da base.")
    fim = base.posicao(bruto["fim"]) if bruto.get("fim") else fim_padrao
    inicio = base.posicao(bruto["inicio"]) if bruto.get("inicio") else _inicio_padrao(base, fim)
    if inicio >= fim:
        raise ValueError("Janela inválida: ela precisa de pelo menos dois registros, com o início antes do fim.")
    return inicio, fim, False


def _intervencoes(brutas, ids: set) -> list[dict]:
    """As intervenções de um cenário, validadas: acréscimo ou retirada de X médicos numa data (pontual) ou num calendário (de…
    até…, a cada tantos meses), com a hipótese de permanência (100% ao ano, a total, é o padrão)."""
    if brutas in (None, []):
        return []
    if not isinstance(brutas, list) or len(brutas) > MAX_INTERVENCOES:
        raise ValueError("Intervenções inválidas: envie uma lista de até " + str(MAX_INTERVENCOES) + ".")
    saida = []
    for bruta in brutas:
        if not isinstance(bruta, dict) or bruta.get("tipo") not in ("acrescimo", "retirada"):
            raise ValueError("Intervenção inválida: o tipo é acrescimo ou retirada.")
        quantidade = bruta.get("quantidade")
        if isinstance(quantidade, bool) or not isinstance(quantidade, (int, float)) or not math.isfinite(quantidade) or quantidade <= 0 \
                or quantidade > 1_000_000:
            raise ValueError("Intervenção inválida: a quantidade é um número acima de zero.")
        em = _competencia_futura(bruta.get("em"), "Data da intervenção")
        ate = _competencia_futura(bruta["ate"], "Data final da intervenção") if bruta.get("ate") else em
        passo = bruta.get("a_cada_meses", 12)
        if isinstance(passo, bool) or not isinstance(passo, int) or not 1 <= passo <= 120:
            raise ValueError("Intervenção inválida: o intervalo entre os eventos é um número inteiro de meses, de 1 a 120.")
        if _ANUAL.get() and passo % 12:
            # Numa base com um registro por ano, as datas são anos: os eventos se repetem de ano em ano (ou a cada tantos anos).
            raise ValueError("Intervenção inválida: numa base com um registro por ano, o intervalo entre os eventos é de 12 meses ou "
                             "um múltiplo de 12.")
        if ate < em:
            raise ValueError("Intervenção inválida: a data final vem antes da inicial.")
        permanencia = bruta.get("permanencia_pct_ao_ano", 100)
        if isinstance(permanencia, bool) or not isinstance(permanencia, (int, float)) or not 0 <= permanencia <= 100:
            raise ValueError("Intervenção inválida: a permanência é um percentual ao ano, de 0 a 100.")
        alvos = bruta.get("territorios")
        if alvos is not None and (not isinstance(alvos, list) or not alvos or any(alvo not in ids for alvo in alvos)):
            raise ValueError("Intervenção inválida: os territórios dela precisam estar na seleção do Simulador.")
        datas = list(range(em, ate + 1, passo))
        if len(datas) > MAX_EVENTOS:
            raise ValueError("Intervenção inválida: são eventos demais; aumente o intervalo ou encurte o período.")
        saida.append({"tipo": bruta["tipo"], "quantidade": float(quantidade), "em": em, "ate": ate, "a_cada_meses": passo,
                      "periodica": ate > em, "permanencia": float(permanencia), "territorios": None if alvos is None else set(alvos),
                      "datas": datas})
    return saida


def _cenarios(brutos, base: Base, ids: set) -> list[dict]:
    if brutos in (None, []):
        brutos = [{"id": "c1", "nome": "Sem intervenção", "metodo": "padrao"}]
    if not isinstance(brutos, list) or len(brutos) > MAX_CENARIOS:
        raise ValueError("Cenários inválidos: envie uma lista de até " + str(MAX_CENARIOS) + " cenários.")
    saida, vistos = [], set()
    for posicao, bruto in enumerate(brutos):
        if not isinstance(bruto, dict):
            raise ValueError("Cenário inválido.")
        chave = str(bruto.get("id") or "c" + str(posicao + 1))
        if chave in vistos:
            raise ValueError("Cenários com o mesmo id no pedido.")
        vistos.add(chave)
        metodo = bruto.get("metodo", "padrao")
        if metodo not in METODOS:
            raise ValueError("Método desconhecido: " + str(metodo) + ". Use padrao, M0, M0d, M0g, M1, M2, M3 ou manual.")
        taxa = bruto.get("taxa_manual_pct")
        if metodo == "manual":
            if isinstance(taxa, bool) or not isinstance(taxa, (int, float)) or not -99 <= taxa <= 500:
                raise ValueError("Taxa manual inválida: informe a taxa anual, em %, de −99 a 500. O sistema não sugere uma taxa.")
        elif taxa is not None:
            raise ValueError("A taxa manual só vale com o método manual.")
        saida.append({"id": chave, "nome": str(bruto.get("nome") or "Cenário " + str(posicao + 1))[:80], "metodo": metodo,
                      "taxa": None if taxa is None else float(taxa), "janela": bruto.get("janela"),
                      "intervencoes": _intervencoes(bruto.get("intervencoes"), ids), "planejamento": _plano(bruto.get("planejamento"))})
    return saida


# --------------------------------------------------------------------------------------------- um território, um cenário
def _inteiro_da_tela(valor: float) -> int:
    """O número de médicos de um texto de cenário: o inteiro mais próximo (meio para cima). A precisão integral fica na resposta."""
    return int(math.floor(valor + 0.5))


def _br(valor, casas: int = 1) -> str:
    if float(valor).is_integer():
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _curto(valor: float) -> str:
    """Um número com até duas casas, sem zeros à direita: 1, 1,5 ou 1,25."""
    return ("%.2f" % valor).rstrip("0").rstrip(".").replace(".", ",")


def _pct(valor, casas: int = 1) -> str:
    return ("+" if valor > 0 else "−" if valor < 0 else "") + f"{abs(valor):.{casas}f}".replace(".", ",") + "%"


def _tempo(anos: float) -> str:
    """Um tempo em anos, em palavras: "2 anos", "1 ano", "2,4 anos"."""
    return _br(round(anos, 1)) + (" ano" if round(anos, 1) == 1 else " anos")


def _diferenca_do_ajuste(valor: float, n0: float, quando: str) -> dict:
    """A diferença entre a tendência ajustada e o último registro usado, sempre exibida no M2 e no M3 (seção 8.8)."""
    diferenca = valor - n0
    return {"codigo": "DIFERENCA_PARA_O_ULTIMO_REGISTRO",
            "texto": "A tendência ajustada dá " + _br(round(valor, 1)) + " em " + quando + ", e o registro é " + _br(n0) + " (" +
                     ("a mesma contagem" if abs(diferenca) < 0.05 else ("+" if diferenca > 0 else "−") + _br(round(abs(diferenca), 1))) +
                     "): o cenário segue a tendência ajustada."}


def _usaveis(base: Base, cal: detector.Calibracao, territorio: Territorio, inicio: int, fim: int) -> tuple[list[int], list[str]]:
    """Os registros da janela que entram nos ajustes: os que existem, fora os registros de pico (conhecidos até o fim da janela) e
    os que estão numa quebra de fonte (a janela começa depois dela)."""
    serie, avisos = territorio.serie, []
    indices = [i for i in range(inicio, fim + 1) if serie[i] == serie[i]]
    if territorio.tipo == "municipio":
        linha = territorio.linha
        picos = [i for i in indices if int(cal.pico_conhecido[linha, i]) <= fim]
        quebrados = [i for i in indices if bool(cal.quebra[linha, i])]
        if picos:
            avisos.append({"codigo": "PICO_FORA_DO_AJUSTE", "texto": "O registro de " + ", ".join(detector.curta(base.periodos[i]) for i in picos) +
                           " é um pico que volta (descontinuidade de registro) e fica fora da base do cenário."})
        if quebrados:
            avisos.append({"codigo": "JANELA_DEPOIS_DA_QUEBRA", "texto": "A janela começa depois da quebra de fonte (os registros até " +
                           detector.curta(base.periodos[quebrados[-1]]) + " ficam fora da base do cenário)."})
        fora = set(picos) | set(quebrados)
        indices = [i for i in indices if i not in fora]
    return indices, avisos


def _estatisticas(base: Base, serie: np.ndarray, indices: list[int]) -> dict:
    """As estatísticas históricas da janela, só descritivas: as taxas de junho a junho, a média aritmética, a mediana e a dispersão
    delas, ao lado da taxa composta. A média aritmética nunca alimenta uma projeção (seção 8.6)."""
    junhos = [i for i in indices if base.ancora and base.periodos[i].endswith(base.ancora)]   # os registros da série anual
    taxas = []
    for a, b in zip(junhos, junhos[1:]):
        if int(base.periodos[b][:4]) - int(base.periodos[a][:4]) == 1 and serie[a] > 0:
            taxas.append({"de": base.periodos[a], "ate": base.periodos[b], "taxa_pct": float(100.0 * (serie[b] / serie[a] - 1))})
    valores = [taxa["taxa_pct"] for taxa in taxas]
    composta = None
    if len(indices) >= 2 and serie[indices[0]] > 0 and serie[indices[-1]] > 0:
        anos = (base.meses[indices[-1]] - base.meses[indices[0]]) / 12.0
        composta = float(100.0 * ((serie[indices[-1]] / serie[indices[0]]) ** (1.0 / anos) - 1))
    return {"registros": len(indices), "de": base.periodos[indices[0]] if indices else None,
            "ate": base.periodos[indices[-1]] if indices else None,
            "anos": float((base.meses[indices[-1]] - base.meses[indices[0]]) / 12.0) if len(indices) >= 2 else 0.0,
            "taxas_de_junho": taxas,
            "media_aritmetica_pct": float(np.mean(valores)) if valores else None,
            "mediana_pct": float(np.median(valores)) if valores else None,
            "desvio_pct": float(np.std(valores, ddof=1)) if len(valores) >= 2 else None,
            "taxa_composta_pct": composta,
            "nota": "A média aritmética das taxas é só descrição do passado: com taxas que oscilam, ela superestima o crescimento "
                    "que de fato ocorreu no mesmo período (a taxa composta); por isso não é usada para projetar."}


def _antes(base: Base, origem: int) -> int | None:
    """O registro de 3 anos antes de uma origem (o mesmo mês do ano); None quando a base não o tem."""
    achados = np.nonzero(base.meses == int(base.meses[origem]) - 12 * ANOS_DA_DERIVA)[0]
    return int(achados[0]) if achados.size else None


def _retro_do(retros: dict, territorio: Territorio, base: Base | None = None) -> Retroprojecao | None:
    """A retroprojeção do nível do território: a das unidades da base, ou a dos grupos de cima como unidade (que vale também
    para o todo, que não tem retroprojeção própria; numa base sem a contagem própria dos grupos — uma planilha, em que o grupo é a
    soma das unidades dele —, o todo usa a das unidades)."""
    if territorio.tipo == "brasil" and base is not None and base.grupos_por_soma:
        return retros.get("municipios")
    do_nivel = retros.get("municipios" if territorio.nivel == "municipios" else "estados")
    return retros.get("municipios") if do_nivel is None and territorio.tipo == "brasil" else do_nivel


def _deriva(base: Base, cal: detector.Calibracao, prefixo: str | None, origem: int) -> tuple[float | None, str | None]:
    """O crescimento anual recente do grupo de cima numa origem (a "deriva" do M0d: na base do Brasil, a do estado) e, quando não
    há, o motivo."""
    r = series_brasil.rotulos(base)
    linhas = list(base.do_estado.get(prefixo, ())) if prefixo else []
    if not linhas:
        return None, "a base não tem grupo de cima"
    antes = _antes(base, origem)
    if antes is None:
        return None, "não há registros d" + r["o_grupo"] + " 3 anos antes do último registro usado"
    if cal.quebra[linhas, antes:origem + 1].any():
        return None, "há quebra de fonte nos 3 anos usados para medir o crescimento d" + r["o_grupo"]
    soma = base.soma_municipal_do_estado(prefixo)
    if not soma[antes] > 0 or not soma[origem] > 0:
        return None, "a soma d" + r["os_unidades"] + " d" + r["o_grupo"] + " é zero nesses 3 anos"
    return float((soma[origem] / soma[antes]) ** (1.0 / ANOS_DA_DERIVA) - 1), None


def _crescimento_da_base(base: Base, origem: int, nivel: str = "municipios") -> tuple[float | None, str | None]:
    """O crescimento anual recente da base toda numa origem (o M0g): a soma de todos os territórios do nível (as unidades da
    base, ou os grupos de cima com contagem própria) nos 3 anos anteriores. Sem ele, o motivo."""
    antes = _antes(base, origem)
    if antes is None:
        return None, "não há registros 3 anos antes do último registro usado"
    # A base toda do nível: as unidades; ou os grupos de cima — na base do Brasil, também para o todo (a contagem própria deles);
    # numa planilha, o todo é a soma das unidades e continua com elas.
    das_unidades = nivel == "municipios" or not base.estados or (nivel == "brasil" and base.grupos_por_soma)
    toda = np.nansum(base.quantidade, axis=0) if das_unidades else np.nansum(np.vstack(list(base.estados.values())), axis=0)
    if not toda[antes] > 0 or not toda[origem] > 0:
        return None, "a soma da base toda é zero nesses 3 anos"
    return float((toda[origem] / toda[antes]) ** (1.0 / ANOS_DA_DERIVA) - 1), None


def _errou_mais(retro: Retroprojecao | None, metodo: str, porte: int | None) -> bool:
    """Na retroprojeção da base, o método errou mais que manter o último valor em todos os prazos conferidos deste porte."""
    if retro is None or porte is None:
        return False
    razoes = [linha["frente_ao_m0"] for linha in retro.tabela if linha["metodo"] == metodo and linha["porte"] == porte
              and linha["casos"] >= MINIMO_POR_PORTE_NA_ESCOLHA and linha["frente_ao_m0"] is not None]
    return bool(razoes) and all(razao > 1 for razao in razoes)


MOTIVOS_SEM_ESCOLHA = {
    "sem_serie_anual": "A base não tem série anual (nenhum mês se repete em todos os anos): sem retroprojeção, o cenário mantém o "
                       "último valor.",
    "poucas_origens": "A base não tem história bastante para a retroprojeção (são menos de 3 origens com 3 anos antes e 1 ano "
                      "depois): o cenário mantém o último valor.",
    "nenhum_vale": "Nesta base, nenhuma forma de projetar errou menos que manter o último valor, quando conferida com o passado: o "
                   "cenário mantém o último valor.",
}


def _base_do_cenario(base: Base, cal: detector.Calibracao, retro: Retroprojecao | None, territorio: Territorio, metodo: str, taxa_manual,
                     inicio: int, fim: int):
    """A trajetória-base B(t) de um território num método: devolve o método usado, os parâmetros, os avisos e a função B(anos
    desde a origem), ou o motivo de não haver. `metodo` "padrao" vale o jeito de projetar que a própria base escolheu para o
    nível do território (regra C.3 da Proposta V3), com a exceção por porte."""
    indices, avisos = _usaveis(base, cal, territorio, inicio, fim)
    if not indices:
        return {"estado": "nao_calculavel", "motivo": "Não há registro usável na janela escolhida (ausência de dado não é zero)."}
    r = series_brasil.rotulos(base)
    origem = indices[-1]
    serie = territorio.serie
    n0 = float(serie[origem])
    t = (base.meses[indices] - base.meses[origem]) / 12.0
    y = np.array([float(serie[i]) for i in indices])
    pedido = metodo
    provisorio = False
    escolha = retro.escolha if retro is not None else {"metodo": "M0", "motivo": "poucas_origens", "excecoes": []}
    if metodo == "padrao":
        metodo = escolha["metodo"]
        if escolha["motivo"] != "escolhido":
            avisos.append({"codigo": "PADRAO_E_O_ULTIMO_VALOR" if escolha["motivo"] == "nenhum_vale" else "SEM_RETROPROJECAO",
                           "texto": MOTIVOS_SEM_ESCOLHA[escolha["motivo"]]})
        elif _porte_da_faixa(n0) in escolha["excecoes"]:
            # A exceção por porte: neste porte, o jeito escolhido errou mais que manter o último valor em todos os prazos.
            metodo = "M0"
            avisos.append({"codigo": "PORTE_USA_O_ULTIMO_VALOR", "texto": "Em territórios de " + ROTULOS_DOS_PORTES_DA_FAIXA[_porte_da_faixa(n0)] +
                           " " + r["profissionais"] + ", a forma de projetar escolhida pela base errou mais que manter o último valor, "
                           "em todos os prazos conferidos: o cenário mantém o último valor."})
        if territorio.tipo == "brasil" and metodo in ("M0d", "M0g"):
            # O todo é a própria base toda: o crescimento recente dela é a taxa composta da série dele nos 3 anos até a origem.
            metodo = "M1"
        if metodo == "M1":
            # O crescimento do próprio território nos 3 anos até o último registro usado, como na retroprojeção. Sem o registro
            # de 3 anos antes na base (registros espaçados, ou origem perto do começo), a taxa escolhida não pode ser medida como
            # lá: fica só a origem, e o padrão volta ao último valor, com o aviso (abaixo).
            inicio = _antes(base, origem)
            indices = [i for i in indices if i >= inicio] if inicio is not None else indices[-1:]
            t = (base.meses[indices] - base.meses[origem]) / 12.0
            y = np.array([float(serie[i]) for i in indices])
        if territorio.tipo == "brasil":
            # O todo não tem retroprojeção própria (é uma série só): usa o jeito escolhido para o nível de baixo, como provisório.
            provisorio = True
            avisos.append({"codigo": "PADRAO_PROVISORIO_DO_NIVEL", "texto":
                           "Para " + r["o_todo"] + ", o método padrão é provisório: uma série só não tem retroprojeção própria, e vale o "
                           "forma escolhida para " + (r["os_grupos"] if base.estados and not base.grupos_por_soma else r["os_unidades"]) + "." +
                           (" Ele só foi conferido num período de crescimento." if base.do_brasil else "")})
    parametros = {"n0": n0, "origem": base.periodos[origem], "janela": {"inicio": base.periodos[indices[0]], "fim": base.periodos[origem],
                                                                          "registros": len(indices)}}
    janela_do_metodo = float((base.meses[origem] - base.meses[indices[0]]) / 12.0)
    if metodo == "M0d" and (territorio.nivel != "municipios" or not base.do_estado):
        return {"estado": "nao_aplicavel", "motivo": "A persistência com o crescimento recente d" + r["o_grupo"] + " vale para " +
                r["os_unidades"] + " e conjuntos de " + r["unidades"] + ", numa base com grupo de cima; nos outros casos, use o "
                "crescimento da base toda (M0g) ou a taxa composta do próprio território (M1)."}
    if metodo == "M0g" and territorio.tipo == "brasil":
        return {"estado": "nao_aplicavel", "motivo": "O crescimento da base toda não vale para " + r["o_todo"] + ": a série é a própria base "
                "toda. Use a taxa composta (M1)."}

    def conjunto_de_municipios():
        return territorio.tipo == "conjunto" and territorio.nivel == "municipios"

    if metodo in ("M0", "M0d") and conjunto_de_municipios():
        # A soma das projeções dos membros, cada um com o crescimento recente do grupo de cima dele.
        partes, sem_deriva = [], []
        for membro in territorio.membros:
            codigo = membro[len(base.prefixo_do_id):]
            linha = base.indice[codigo]
            valor = float(base.quantidade[linha, origem])
            deriva, motivo = (_deriva(base, cal, base.prefixos[linha], origem) if metodo == "M0d" else (0.0, None))
            if deriva is None:
                sem_deriva.append(base.nomes[linha])
                deriva = 0.0
            partes.append((valor, deriva))
        if sem_deriva:
            avisos.append({"codigo": "DERIVA_INDISPONIVEL", "texto": "Sem o crescimento recente d" + r["o_grupo"] + " para " +
                           ", ".join(sem_deriva[:5]) + ": nesses membros, vale a persistência (o último valor)."})
        parametros["soma_das_projecoes"] = True
        if metodo == "M0d":
            parametros["derivas_pct"] = sorted({round(100.0 * deriva, 4) for _, deriva in partes})
        funcao = lambda anos: float(sum(valor * (1 + deriva) ** anos for valor, deriva in partes))  # noqa: E731
        return {"estado": "calculado", "pedido": pedido, "usado": metodo, "provisorio": provisorio, "parametros": parametros,
                "avisos": avisos, "funcao": funcao, "origem": origem, "indices": indices, "janela_do_metodo": float(ANOS_DA_DERIVA),
                "rotulo_da_soma": "soma das projeções dos membros"}
    if metodo == "M0":
        return {"estado": "calculado", "pedido": pedido, "usado": "M0", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: n0, "origem": origem, "indices": indices, "janela_do_metodo": float(ANOS_DA_DERIVA)}
    if metodo == "M0d":
        deriva, motivo = _deriva(base, cal, territorio.uf, origem)
        if deriva is None:
            avisos.append({"codigo": "VOLTA_AO_M0", "texto": "Sem o crescimento recente d" + r["o_grupo"] + " (" + motivo +
                           "): o cenário usa a persistência (o último valor se mantém)."})
            return {"estado": "calculado", "pedido": pedido, "usado": "M0", "provisorio": provisorio, "parametros": parametros,
                    "avisos": avisos, "funcao": lambda anos: n0, "origem": origem, "indices": indices,
                    "janela_do_metodo": float(ANOS_DA_DERIVA), "voltou_ao_m0": True}
        parametros["deriva_pct"] = 100.0 * deriva
        parametros["estado_da_deriva"] = series_brasil.nome_do_grupo(base, territorio.uf)[1]
        if n0 == 0:
            avisos.append({"codigo": "ZERO_CONTINUA_ZERO", "texto": "O território está em zero: sem uma intervenção, continua em zero "
                           "(o crescimento d" + r["o_grupo"] + " multiplica o último valor)."})
        return {"estado": "calculado", "pedido": pedido, "usado": "M0d", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: n0 * (1 + deriva) ** anos, "origem": origem, "indices": indices,
                "janela_do_metodo": float(ANOS_DA_DERIVA)}
    if metodo == "M0g":
        # O último valor com o crescimento recente da base toda (Proposta V3, seção C.3): o candidato das bases sem grupo de cima.
        crescimento, motivo = _crescimento_da_base(base, origem, territorio.nivel)
        if crescimento is None:
            avisos.append({"codigo": "VOLTA_AO_M0", "texto": "Sem o crescimento recente da base toda (" + motivo +
                           "): o cenário usa a persistência (o último valor se mantém)."})
            return {"estado": "calculado", "pedido": pedido, "usado": "M0", "provisorio": provisorio, "parametros": parametros,
                    "avisos": avisos, "funcao": lambda anos: n0, "origem": origem, "indices": indices,
                    "janela_do_metodo": float(ANOS_DA_DERIVA), "voltou_ao_m0": True}
        parametros["crescimento_da_base_pct"] = 100.0 * crescimento
        if territorio.tipo == "conjunto":
            parametros["serie_da_soma"] = True
        if n0 == 0:
            avisos.append({"codigo": "ZERO_CONTINUA_ZERO", "texto": "O território está em zero: sem uma intervenção, continua em zero "
                           "(o crescimento da base toda multiplica o último valor)."})
        return {"estado": "calculado", "pedido": pedido, "usado": "M0g", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: n0 * (1 + crescimento) ** anos, "origem": origem, "indices": indices,
                "janela_do_metodo": float(ANOS_DA_DERIVA)}
    if metodo == "manual":
        parametros["taxa_pct"] = taxa_manual
        avisos.append({"codigo": "TAXA_DA_PESSOA", "texto": "A taxa de " + _pct(taxa_manual, 2) + " ao ano foi informada pela pessoa, como "
                       "hipótese dela; o sistema não sugere taxas."})
        return {"estado": "calculado", "pedido": pedido, "usado": "manual", "provisorio": False, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: n0 * (1 + taxa_manual / 100.0) ** anos, "origem": origem, "indices": indices,
                "janela_do_metodo": max(janela_do_metodo, 1e-9)}
    if conjunto_de_municipios() or (territorio.tipo == "conjunto"):
        parametros["serie_da_soma"] = True
    if metodo == "M1":
        if len(indices) < 2 or not y[0] > 0 or not y[-1] > 0:
            if pedido == "padrao":
                # O jeito escolhido pela base é a taxa composta, mas ela não se aplica a este território: como nos outros jeitos
                # escolhidos, o padrão volta ao último valor, com o aviso.
                avisos.append({"codigo": "VOLTA_AO_M0", "texto": "Sem a taxa composta do território (ela exige dois registros nos 3 anos "
                               "até a origem, com o primeiro e o último acima de zero): o cenário usa a persistência (o último valor se "
                               "mantém)."})
                return {"estado": "calculado", "pedido": pedido, "usado": "M0", "provisorio": provisorio, "parametros": parametros,
                        "avisos": avisos, "funcao": lambda anos: n0, "origem": origem, "indices": indices,
                        "janela_do_metodo": float(ANOS_DA_DERIVA), "voltou_ao_m0": True}
            return {"estado": "nao_aplicavel", "motivo": "A taxa composta exige dois registros na janela, com o primeiro e o último acima "
                    "de zero (com início em zero, a taxa não é definida)."}
        taxa = float((y[-1] / y[0]) ** (1.0 / janela_do_metodo) - 1)
        parametros.update({"taxa_pct": 100.0 * taxa, "acumulado_pct": float(100.0 * (y[-1] / y[0] - 1)), "anos": janela_do_metodo})
        if territorio.tipo == "municipio" and _errou_mais(retro, "M1", _porte_da_faixa(n0)):
            # O nome do aviso é o de antes (a V2.2 fixava 100); o corte vem agora da retroprojeção da própria base, por porte.
            avisos.append({"codigo": "M1_ABAIXO_DE_100", "texto": "Em territórios de " + ROTULOS_DOS_PORTES_DA_FAIXA[_porte_da_faixa(n0)] + " " +
                           r["profissionais"] + ", este método errou mais do que simplesmente manter o último valor, quando conferido com "
                           "o passado da base."})
        return {"estado": "calculado", "pedido": pedido, "usado": "M1", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: n0 * (1 + taxa) ** anos, "origem": origem, "indices": indices, "janela_do_metodo": janela_do_metodo}
    if len(indices) < 3:
        return {"estado": "nao_aplicavel", "motivo": "Este método precisa de pelo menos três registros na janela."}
    if metodo == "M2":
        a, b = theil_sen(t, y[None, :])
        a, b = float(a[0]), float(b[0])
        parametros.update({"inclinacao_por_ano": b, "valor_na_origem": a, "diferenca_para_n0": a - n0})
        avisos.append(_diferenca_do_ajuste(a, n0, detector.curta(base.periodos[origem])))
        return {"estado": "calculado", "pedido": pedido, "usado": "M2", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: a + b * anos, "origem": origem, "indices": indices, "janela_do_metodo": janela_do_metodo,
                "pode_ficar_negativo": True}
    if not y.sum() > 0:
        return {"estado": "nao_calculavel", "motivo": "Com a série toda em zero na janela, a tendência log-linear não é calculável."}
    alfa, beta, dispersao, ok = poisson(t, y[None, :])
    if not bool(ok[0]):
        return {"estado": "nao_calculavel", "motivo": "O ajuste log-linear não convergiu com os registros desta janela."}
    alfa, beta = float(alfa[0]), float(beta[0])
    parametros.update({"taxa_pct": 100.0 * (math.exp(beta) - 1), "valor_na_origem": math.exp(alfa), "diferenca_para_n0": math.exp(alfa) - n0,
                       "dispersao": float(dispersao[0]) if math.isfinite(float(dispersao[0])) else None})
    avisos.append(_diferenca_do_ajuste(math.exp(alfa), n0, detector.curta(base.periodos[origem])))
    return {"estado": "calculado", "pedido": pedido, "usado": "M3", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
            "funcao": lambda anos: math.exp(min(30.0, alfa + beta * anos)), "origem": origem, "indices": indices,
            "janela_do_metodo": janela_do_metodo}


def _aviso_do_horizonte(anos: float, janela: float, sem_historia: bool = False) -> dict:
    """Os avisos H/W (seção 7.3): informativos, sem garantia estatística. `sem_historia`: o cenário mantém o último valor (M0), que
    não usa a história. Os níveis continuam os mesmos (medidos com os 3 anos de referência), mas a frase é simples e não fala em
    referência nem em história (revisão final do V23, 15/11/2026: "a referência são 3 anos, porque manter o último valor não usa a
    história" confundia, e uma base pode nem ter 3 anos): "Cautela: quanto mais longe a data final, mais incerto o cenário (aqui,
    2 anos à frente)."."""
    razao = anos / janela if janela > 0 else math.inf
    if sem_historia:
        aqui = " (aqui, " + _tempo(anos) + " à frente)."
        if razao <= 0.5:
            return {"nivel": "normal", "texto": "Quanto mais longe a data final, mais incerto o cenário" + aqui}
        if razao <= 1:
            return {"nivel": "cautela", "texto": "Cautela: quanto mais longe a data final, mais incerto o cenário" + aqui}
        if razao <= 2:
            return {"nivel": "extrapolacao", "texto": "Extrapolação: a data final fica longe do último registro, e o cenário é muito "
                    "incerto" + aqui}
        return {"nivel": "extrapolacao_extrema", "texto": "Extrapolação extrema: a data final fica muito longe do último registro, e o "
                "cenário é incerto demais para ser lido como um número" + aqui}
    tempo = "tempo de história usado no cálculo"
    tempos = " (" + _tempo(anos) + " à frente, com " + _tempo(janela) + " de história usados no cálculo)."
    if razao <= 0.5:
        return {"nivel": "normal", "texto": "A data final fica a até metade do " + tempo + tempos}
    if razao <= 1:
        return {"nivel": "cautela", "texto": "Cautela: a data final fica a mais da metade do " + tempo + tempos}
    if razao <= 2:
        return {"nivel": "extrapolacao", "texto": "Extrapolação além da janela: a data final fica mais longe do que o " + tempo + tempos}
    return {"nivel": "extrapolacao_extrema", "texto": "Extrapolação extrema: a data final fica a mais do dobro do " + tempo + tempos}


def _efeito(intervencoes: list[dict], territorio: Territorio, mes: int) -> float:
    """I(t): a soma dos eventos até a data, cada um com a permanência dele (S(u) = (p/100)^u; p = 100: permanência total)."""
    total = 0.0
    for item in intervencoes:
        if item["territorios"] is not None and territorio.id not in item["territorios"]:
            continue
        sinal = 1.0 if item["tipo"] == "acrescimo" else -1.0
        for data in item["datas"]:
            if data <= mes:
                anos = (mes - data) / 12.0
                total += sinal * item["quantidade"] * ((item["permanencia"] / 100.0) ** anos if item["permanencia"] < 100 else 1.0)
    return total


def _premissas(base: Base, resultado: dict, cenario: dict, territorio: Territorio, varios: bool = False) -> str:
    """As premissas do texto de cenário: a janela, o parâmetro do método e as intervenções, por extenso. Com mais de um território
    no pedido (`varios`), o texto diz que a intervenção vale para cada território do cenário (cada um recebe a quantidade
    inteira), ou só para os indicados."""
    p, r = resultado["parametros"], series_brasil.rotulos(base)
    # Uma janela com um registro só (uma base com registros espaçados) é dita assim, e não "de jun/2024 a jun/2024".
    partes = ["janela com um registro só (" + detector.curta(p["janela"]["fim"]) + ")" if p["janela"]["inicio"] == p["janela"]["fim"] else
              "janela de " + detector.curta(p["janela"]["inicio"]) + " a " + detector.curta(p["janela"]["fim"])]
    if resultado["usado"] == "M0d":
        partes.append(("crescimento " + comparativos._do_grupo(base, territorio.uf) + " de " + _pct(p["deriva_pct"], 2) + " ao ano")
                      if "deriva_pct" in p else "o crescimento recente d" + r["o_grupo"] + " de cada membro")
    elif resultado["usado"] == "M0g":
        partes.append("crescimento da base toda de " + _pct(p["crescimento_da_base_pct"], 2) + " ao ano")
    elif resultado["usado"] in ("M1", "M3", "manual"):
        partes.append("taxa de " + _pct(p["taxa_pct"], 2) + " ao ano" + (" informada pela pessoa" if resultado["usado"] == "manual" else ""))
    elif resultado["usado"] == "M2":
        partes.append("variação de " + ("+" if p["inclinacao_por_ano"] >= 0 else "−") + _br(abs(p["inclinacao_por_ano"]), 2) + " " + r["profissionais"] + " por ano")
    aplicaveis = [item for item in cenario["intervencoes"] if item["territorios"] is None or territorio.id in item["territorios"]]
    if not aplicaveis:
        partes.append("sem intervenção")
    for item in aplicaveis:
        verbo = "acréscimo" if item["tipo"] == "acrescimo" else "retirada"
        quando = ("em " + detector.curta(_data(item["em"]))) if not item["periodica"] else \
            ("a cada " + str(item["a_cada_meses"]) + " meses, de " + detector.curta(_data(item["em"])) + " a " + detector.curta(_data(item["ate"])))
        permanencia = "com permanência total" if item["permanencia"] >= 100 else "com permanência de " + _br(item["permanencia"], 1) + "% ao ano"
        onde = " neste território, pelo planejamento inverso," if item.get("planejada") else \
            "" if not varios else " em cada território do cenário," if item["territorios"] is None else " só nos territórios indicados,"
        partes.append(verbo + " de " + _br(item["quantidade"], 1) + " " + (r["profissional"] if item["quantidade"] == 1 else r["profissionais"]) +
                      onde + " " + quando +
                      ", " + permanencia + " (hipótese)")
    return "; ".join(partes)


def _nome_do_metodo(base: Base, metodo: str) -> str:
    """O nome de um método nos textos, com os nomes da base ("o crescimento recente do estado", "da província")."""
    if metodo == "M0d":
        return "persistência com o crescimento recente d" + series_brasil.rotulos(base)["o_grupo"]
    return NOMES_DOS_METODOS[metodo]


def _meses_de_exibicao(base: Base, de: int, ate: int) -> set:
    """As datas de exibição entre dois meses: os meses do ano em que a base tem registro (na base do Brasil, janeiro e junho)."""
    do_ano = {mes_da_competencia("2000" + mes) % 12 for mes in series_brasil.meses_de_registro(base.periodos)} or \
        {int(base.meses[-1]) % 12}
    return {mes for mes in range(de + 1, ate + 1) if mes % 12 in do_ano}


def _rotulo_da_faixa(base: Base, territorio: Territorio, como: str) -> str:
    """De onde vem a margem da faixa, em palavras: os territórios do mesmo porte, com os portes vizinhos ou com portes menores."""
    r = series_brasil.rotulos(base)
    quem = r["unidades"] if territorio.nivel == "municipios" else r["grupos"]
    com_quem = {"propria": quem + " do mesmo porte", "vizinhas": quem + " do mesmo porte e dos portes vizinhos",
                "portes_menores": quem + " do mesmo porte e de portes menores (a faixa fica mais larga, e por isso mais cautelosa)"}
    return ("aproximação: a margem d" + r["os_unidades"] + " com o porte da soma" if territorio.tipo == "conjunto"
            else "a margem observada no passado da base, em " + com_quem[como]) + "; acompanha a intervenção"


def _faixa_do_cenario(base: Base, retro: Retroprojecao | None, territorio: Territorio, resultado: dict, em_10: int) -> tuple[dict, dict]:
    """A faixa de um cenário (seção C.4) e os limites por prazo. Só existe para o jeito e a janela escolhidos pela base, com pelo
    menos 1 na origem e casos bastantes na retroprojeção; fora disso, "indisponível", com o motivo."""
    r = series_brasil.rotulos(base)
    faixa = {"estado": "indisponivel", "motivo": None, "rotulo": None, "em_10": em_10}
    n0 = resultado["parametros"]["n0"]
    porte = _porte_da_faixa(n0)
    escolha = retro.escolha if retro is not None else None
    de_cada = "A faixa de " + str(em_10) + " em cada 10"
    if escolha is None or escolha["motivo"] not in ("escolhido", "nenhum_vale"):
        faixa["motivo"] = de_cada + " vem da retroprojeção, e esta base não tem retroprojeção bastante" + (
            "." if escolha is None else ": " + {"sem_serie_anual": "nenhum mês se repete em todos os anos.",
                                                "poucas_origens": "são menos de 3 origens com 3 anos antes e 1 ano depois."}[escolha["motivo"]])
        return faixa, {}
    if territorio.tipo == "brasil":
        faixa["motivo"] = "Não há faixa para " + r["o_todo"] + ": uma série só não tem retroprojeção própria."
        return faixa, {}
    # O jeito e a janela escolhidos pela base: o mesmo método, com os 3 anos até a origem.
    antes = _antes(base, resultado["origem"])
    da_base = resultado["usado"] == escolha["metodo"] and not resultado.get("voltou_ao_m0") and (
        resultado["usado"] != "M1" or resultado["pedido"] == "padrao" or (antes is not None and resultado["indices"][0] == antes))
    if not da_base and resultado["pedido"] == "padrao":
        # O padrão caiu no último valor neste território (o porte em que o escolhido errou mais, ou a falta do crescimento que
        # ele pede): a faixa da base é a do jeito escolhido, e não a do último valor.
        faixa["motivo"] = (de_cada + " é a da forma de projetar que a base escolheu (" + _nome_do_metodo(base, escolha["metodo"]) +
                           "). Neste território, o cenário mantém o último valor, e não há faixa.")
        return faixa, {}
    if not da_base:
        faixa["motivo"] = (de_cada + " só existe para a forma de projetar e a janela que a própria base escolheu (" +
                           _nome_do_metodo(base, escolha["metodo"]) + ", com os 3 anos até a origem). Com outra forma ou outra janela, "
                           "não há faixa.")
        return faixa, {}
    if porte is None:
        faixa["motivo"] = "Com zero " + r["profissionais"] + " na origem, não há faixa."
        return faixa, {}
    limites = {prazo: retro.faixas.get((em_10, porte, prazo)) for prazo in HORIZONTES_DA_FAIXA}
    limites = {prazo: item for prazo, item in limites.items() if item is not None}
    # A faixa do cenário vai do primeiro ano até o maior prazo seguido que a base sustenta: um prazo sem faixa (poucos casos ou
    # cobertura baixa na conferência) encerra a faixa ali, para ela não aparecer com "buracos" entre a origem e a data final.
    disponiveis = {}
    for prazo in HORIZONTES_DA_FAIXA:
        if prazo not in limites or limites[prazo]["estado"] == "indisponivel":
            break
        disponiveis[prazo] = limites[prazo]
    if not disponiveis:
        prazo = 1 if 1 in limites else next(iter(limites), None)
        primeiro = limites.get(prazo)
        if primeiro is None:
            faixa["motivo"] = "A base não tem retroprojeções de territórios de " + ROTULOS_DOS_PORTES_DA_FAIXA[porte] + " " + r["profissionais"] + "."
        elif primeiro["motivo"] == "poucos_casos":
            # Os casos contados são os do porte do território (com os vizinhos e os menores), e não os da base inteira, que o
            # perfil da base mostra: a frase diz isso, para um número não parecer contradizer o outro.
            faixa["motivo"] = (de_cada + " pede " + _br(primeiro["pede"]) + " casos por prazo, e esta base tem " + _br(primeiro["casos"]) +
                               " em " + _tempo(prazo) + " para o porte deste território, mesmo juntando os portes vizinhos e os menores.")
        else:
            faixa["motivo"] = ("Conferida com o que veio depois, " + de_cada[0].lower() + de_cada[1:] + " cobriu " +
                               _br(math.floor(primeiro["cobertura"] + 0.5)) + "% dos casos em " + _tempo(prazo) + ", para uma meta de " +
                               _br(primeiro["meta"]) + "%: a base não a sustenta.")
        return faixa, {}
    primeira = disponiveis[min(disponiveis)]
    # O resumo descreve o primeiro prazo; quando a data final tem faixa, `_simular` troca pelo da data final.
    faixa = {"estado": "disponivel", "motivo": None, "em_10": em_10, "porte": ROTULOS_DOS_PORTES_DA_FAIXA[porte], "ate_anos": max(disponiveis),
             "como": primeira["como"], "rotulo": _rotulo_da_faixa(base, territorio, primeira["como"])}
    return faixa, disponiveis


def _entenda_do_cenario(base: Base, retro: Retroprojecao | None, territorio: Territorio, resultado: dict, faixa: dict,
                        final_da_faixa: dict | None, em_10: int) -> dict:
    """Os "Entenda" do resultado (Proposta V3, seções C.2 e C.5): duas ou três frases simples sobre o jeito de projetar e sobre a
    faixa, com os números deste cenário e da retroprojeção da própria base."""
    r, p, usado = series_brasil.rotulos(base), resultado["parametros"], resultado["usado"]
    escolha = retro.escolha if retro is not None else None
    partida = "O cenário parte do último registro usado (" + detector.curta(p["origem"]) + ")"
    if usado == "M0":
        jeito = partida + " e mantém o valor dele."
    elif usado == "M0d":
        jeito = partida + (" e soma o crescimento recente d" + r["o_grupo"] + ": " + _pct(p["deriva_pct"], 2) + " ao ano nos 3 anos anteriores."
                           if "deriva_pct" in p else " de cada membro e soma o crescimento recente d" + r["o_grupo"] + " de cada um.")
    elif usado == "M0g":
        jeito = partida + " e soma o crescimento recente da base toda: " + _pct(p["crescimento_da_base_pct"], 2) + " ao ano nos 3 anos anteriores."
    elif usado in ("M1", "M3"):
        jeito = partida + " e segue o crescimento do próprio território: " + _pct(p["taxa_pct"], 2) + " ao ano na janela usada."
    elif usado == "M2":
        jeito = partida + " e segue a tendência linear da janela usada."
    else:
        jeito = partida + " e aplica a taxa de " + _pct(p["taxa_pct"], 2) + " ao ano, informada por você."
    if escolha is None or escolha["motivo"] in ("sem_serie_anual", "poucas_origens"):
        porque = "Sem retroprojeção bastante nesta base, o padrão é manter o último valor."
    elif usado == escolha["metodo"] and escolha["motivo"] == "escolhido":
        porque = "Usamos esta forma porque, nesta base, ela errou menos que simplesmente manter o último valor, quando refeita no passado."
    elif usado == escolha["metodo"]:
        porque = "Nesta base, nenhuma outra forma errou menos que manter o último valor, quando refeita no passado."
    elif resultado["pedido"] == "padrao" and usado == "M0":
        porque = ("Neste porte, a forma escolhida pela base errou mais que manter o último valor, quando refeita no passado: o cenário "
                  "mantém o último valor." if any(aviso["codigo"] == "PORTE_USA_O_ULTIMO_VALOR" for aviso in resultado["avisos"]) else
                  "Neste caso, a forma escolhida pela base não pôde ser usada, e o cenário mantém o último valor.")
    elif resultado["pedido"] == "padrao":
        # O todo: o crescimento do grupo de cima ou da base toda, para ele, é o da própria série.
        porque = ("Para " + r["o_todo"] + ", o crescimento da base toda é o da própria série: vale a taxa composta dos 3 anos até a "
                  "origem, como padrão provisório.")
    else:
        porque = "Esta forma foi escolhida por você: a que a base escolheu é a " + _nome_do_metodo(base, escolha["metodo"]) + "."
    exemplo_do_jeito = ("De " + _br(round(p["n0"], 1)) + " " + (r["profissional"] if round(p["n0"], 1) == 1 else r["profissionais"]) +
                        " em " + detector.curta(p["origem"]) +
                        ", a base do cenário vai a " + _br(round(float(resultado["funcao"](1.0)), 1)) + " um ano depois, sem contar intervenções.")
    testado = ""
    if retro is not None and retro.origens:
        testado = " (" + retro.origens[0][:4] + "–" + base.periodos[-1][:4] + ")"
    if faixa["estado"] != "disponivel":
        da_faixa = {"texto": faixa["motivo"] or "Sem faixa neste cenário.",
                    "exemplo": "Sem a faixa, o cenário mostra só a linha: ela não diz quanto o valor real costuma se afastar."}
    else:
        quantos = str(em_10) + " de cada 10"
        texto = ("Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte. Em " + quantos +
                 " vezes, o valor real ficou dentro desta faixa. Não é garantia: o passado testado" + testado + " pode não se repetir.")
        if final_da_faixa is not None and final_da_faixa["estado"] == "provisoria":
            texto += " Faixa provisória: ainda não deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do esperado."
        exemplo = "A faixa vai só até " + _tempo(faixa["ate_anos"]) + " depois da origem." if final_da_faixa is None else (
            "Entre " + _br(_inteiro_da_tela(final_da_faixa["inferior"])) + " e " + _br(_inteiro_da_tela(final_da_faixa["superior"])) + " " +
            r["profissionais"] + " na data final.")
        da_faixa = {"texto": texto, "exemplo": exemplo}
    return {"jeito": {"texto": jeito + " " + porque, "exemplo": exemplo_do_jeito}, "faixa": da_faixa}


def _simular(base: Base, cal: detector.Calibracao, retros: dict, territorio: Territorio, cenario: dict, inicio: int, fim: int,
             horizonte: int, varios: bool = False, em_10: int = FAIXA_PADRAO) -> dict:
    """Um território num cenário: a base B(t), as intervenções I(t), o total, a faixa (quando sustentada), os avisos e o texto."""
    if cenario["janela"] not in (None, {}):
        inicio, fim, _ = _janela(base, cenario["janela"])
    retro = _retro_do(retros, territorio, base)
    r = series_brasil.rotulos(base)
    resultado = _base_do_cenario(base, cal, retro, territorio, cenario["metodo"], cenario["taxa"], inicio, fim)
    cabecalho = {"id": cenario["id"], "nome": cenario["nome"], "metodo": {"pedido": cenario["metodo"]}}
    if resultado["estado"] != "calculado":
        return {**cabecalho, "estado": resultado["estado"], "motivo": resultado["motivo"]}
    origem = resultado["origem"]
    mes_da_origem = int(base.meses[origem])
    if horizonte <= mes_da_origem:
        return {**cabecalho, "estado": "nao_calculavel", "motivo": "A data final precisa ser depois da origem do cenário (" +
                detector.curta(base.periodos[origem]) + ")."}
    for item in cenario["intervencoes"]:
        if item["em"] <= mes_da_origem:
            return {**cabecalho, "estado": "nao_calculavel", "motivo": "A intervenção de " + detector.curta(_data(item["em"])) +
                    " é anterior ou igual à origem do cenário (" + detector.curta(base.periodos[origem]) + "): ela já está nos registros."}
    funcao = resultado["funcao"]
    usado = resultado["usado"]
    escolhido = retro.escolha["metodo"] if retro is not None else "M0"
    metodo = {"pedido": resultado["pedido"], "usado": usado, "rotulo": _nome_do_metodo(base, usado),
              "padrao": resultado["pedido"] == "padrao", "provisorio": bool(resultado["provisorio"]),
              "voltou_ao_m0": bool(resultado.get("voltou_ao_m0")), "soma": resultado.get("rotulo_da_soma"),
              # O jeito que a própria base escolheu para o nível deste território (regra C.3) e se é o que está em uso.
              "escolhido_pela_base": escolhido, "e_o_escolhido": usado == escolhido}
    avisos = list(resultado["avisos"])
    # As datas de exibição: os registros reais entre a origem e o último registro (retroprojeção rotulada), os meses de registro
    # da base até o horizonte (na base do Brasil, janeiro e junho), as datas das intervenções e a data final.
    ultimo = int(base.meses[-1])
    marcas = {int(base.meses[i]) for i in range(origem + 1, len(base.periodos))}
    marcas.update(_meses_de_exibicao(base, mes_da_origem, horizonte))
    for item in cenario["intervencoes"]:
        if item["territorios"] is None or territorio.id in item["territorios"]:
            marcas.update(data for data in item["datas"] if mes_da_origem < data <= horizonte)
    marcas.add(horizonte)
    marcas = sorted(m for m in marcas if m <= horizonte)
    # A faixa (seção C.4): só para o jeito e a janela escolhidos pela base, com N0 ≥ 1, até o maior prazo com casos suficientes.
    faixa, limites = _faixa_do_cenario(base, retro, territorio, resultado, em_10)
    trajetoria, negativo, truncado = [], None, False
    posicao = {int(mes): i for i, mes in enumerate(base.meses)}
    for mes in marcas:
        anos = (mes - mes_da_origem) / 12.0
        b = float(funcao(anos))
        if b < 0:
            truncado, b = True, 0.0
        efeito = _efeito(cenario["intervencoes"], territorio, mes)
        total = b + efeito
        if total < -1e-9 and negativo is None:
            negativo = (mes, total)
        ponto = {"data": _data(mes), "anos": anos, "base": b, "intervencao": efeito, "total": max(0.0, total),
                 "retroprojecao": mes <= ultimo, "faixa": None}
        if mes <= ultimo and mes in posicao:
            observado = territorio.serie[posicao[mes]]
            ponto["observado"] = None if observado != observado else float(observado)
        if faixa["estado"] == "disponivel":
            inteiro = max(1, math.ceil(anos - 1e-9))  # a data intermediária usa a faixa do ano inteiro seguinte
            do_prazo = limites.get(inteiro)
            if do_prazo is not None:
                ponto["faixa"] = {"inferior": max(0.0, b * (1 + do_prazo["inferior"]) + efeito),
                                  "superior": max(0.0, b * (1 + do_prazo["superior"]) + efeito), "anos": inteiro,
                                  "validada": do_prazo["estado"] == "conferida", "estado": do_prazo["estado"], "como": do_prazo["como"]}
        trajetoria.append(ponto)
    if negativo is not None:
        # Retirada acima do estoque: o cenário é devolvido para revisão; o zero matemático não esconde a intervenção impossível.
        return {**cabecalho, "metodo": metodo, "estado": "retirada_acima_do_estoque",
                "motivo": "Em " + detector.curta(_data(negativo[0])) + ", as retiradas passam do número de " + r["profissionais"] +
                          " do cenário em " + _br(-negativo[1], 1) + ": reveja a quantidade ou a data. Nenhum estoque negativo é aceito.",
                "parametros": resultado["parametros"], "avisos": avisos}
    if truncado:
        avisos.append({"codigo": "BASE_TRUNCADA_EM_ZERO", "texto": "A tendência da janela levaria a um número negativo: a base do cenário "
                       "para em zero (um número negativo de " + r["profissionais"] + " não é um estoque válido)."})
    anos_do_horizonte = (horizonte - mes_da_origem) / 12.0
    hw = _aviso_do_horizonte(anos_do_horizonte, resultado["janela_do_metodo"], sem_historia=usado == "M0")
    if hw["nivel"] != "normal":
        avisos.append({"codigo": "HORIZONTE_" + hw["nivel"].upper(), "texto": hw["texto"]})
    if faixa["estado"] == "disponivel" and anos_do_horizonte > faixa["ate_anos"] + 1e-9:
        # O nome do aviso é o de antes; o prazo é o maior seguido que a retroprojeção desta base sustenta.
        avisos.append({"codigo": "FAIXA_ATE_4_ANOS", "texto": "A faixa de " + str(em_10) + " em cada 10 vai só até " + _tempo(faixa["ate_anos"]) +
                       " depois da origem (o maior prazo que a retroprojeção desta base sustenta); além disso, é indisponível (sem "
                       "extrapolar)."})
    final_da_faixa = trajetoria[-1]["faixa"]
    if final_da_faixa is not None:
        # O resumo da faixa descreve a data final: a conferência, os casos e como ela foi montada nesse prazo.
        faixa["conferencia"] = final_da_faixa["estado"]
        faixa["como"], faixa["rotulo"] = final_da_faixa["como"], _rotulo_da_faixa(base, territorio, final_da_faixa["como"])
        do_prazo = limites[final_da_faixa["anos"]]
        faixa["casos"], faixa["cobertura_pct"], faixa["origens_de_teste"] = do_prazo["casos"], do_prazo["cobertura"], do_prazo["origens_de_teste"]
        if final_da_faixa["estado"] == "provisoria":
            avisos.append({"codigo": "FAIXA_PROVISORIA", "texto": "Faixa provisória: " + (
                "ainda não deu para conferi-la com dados que vieram depois (poucas origens ou poucos casos de teste)."
                if do_prazo["motivo"] == "sem_conferencia" else "a conferência com o que veio depois ficou um pouco abaixo do esperado (" +
                _br(math.floor(do_prazo["cobertura"] + 0.5)) + "%, para uma meta de " + _br(do_prazo["meta"]) + "%).")})
        if final_da_faixa["como"] == "portes_menores":
            avisos.append({"codigo": "FAIXA_COM_PORTES_MENORES", "texto": "Faltaram casos do mesmo porte: a faixa junta portes menores, que "
                           "variam mais. Ela fica mais larga, e por isso mais cautelosa."})
    if mes_da_origem < ultimo:
        avisos.append({"codigo": "RETROPROJECAO", "texto": "A origem (" + detector.curta(base.periodos[origem]) + ") é anterior ao último "
                       "registro (" + detector.curta(base.periodos[-1]) + "): até lá, o cenário é calculado sobre datas que já têm registro e "
                       "aparece ao lado do observado."})
    final = trajetoria[-1]
    quem = territorio.rotulo + (" (soma das projeções dos membros)" if metodo["soma"] else
                                " (soma das contagens dos componentes)" if territorio.tipo == "conjunto" else "")
    texto = (PREVISAO_NAO + ": com o método " + _nome_do_metodo(base, usado) + " e as premissas " +
             _premissas(base, resultado, cenario, territorio, varios) + ", " + quem + " teria " + _br(_inteiro_da_tela(final["total"])) +
             " " + (r["profissional"] if _inteiro_da_tela(final["total"]) == 1 else r["profissionais"]) + " em " +
             detector.curta(final["data"]) + ". Base: registros até " + detector.curta(base.periodos[origem]) + ".")
    return {**cabecalho, "metodo": metodo, "estado": "calculado", "parametros": resultado["parametros"], "avisos": avisos,
            "horizonte": {"anos": anos_do_horizonte, "aviso": hw["nivel"]}, "faixa": faixa, "trajetoria": trajetoria,
            "final": {"data": final["data"], "base": final["base"], "intervencao": final["intervencao"], "total": final["total"],
                      "faixa": final["faixa"]},
            "texto": texto, "entenda": _entenda_do_cenario(base, retro, territorio, resultado, faixa, final["faixa"], em_10)}


# --------------------------------------------------------------------------------------------- resposta
def _observado(base: Base, cal: detector.Calibracao, territorio: Territorio) -> list[dict]:
    saida = []
    for i, periodo in enumerate(base.periodos):
        valor = territorio.serie[i]
        ponto = {"competencia": periodo, "valor": None if valor != valor else float(valor),
                 "estado": "ausencia_de_dado" if valor != valor else "zero_confirmado" if valor == 0 else "observado"}
        if territorio.tipo == "municipio":
            if int(cal.pico_conhecido[territorio.linha, i]) < detector.SEM_DATA:
                ponto["marca"] = "pico_que_volta"
            elif bool(cal.quebra[territorio.linha, i]):
                ponto["marca"] = "quebra_de_fonte"
        saida.append(ponto)
    return saida


NOMES_DA_CONFERENCIA = {"conferida": "conferida com o que veio depois", "provisoria": "provisória", "indisponivel": "indisponível"}
COMO_A_FAIXA_FOI_MONTADA = {"propria": "com os casos do próprio porte", "vizinhas": "com os portes vizinhos",
                            "portes_menores": "com portes menores", "indisponivel": "sem casos bastantes"}


def _texto_da_escolha(base: Base, nivel: str, escolha: dict) -> str:
    """A escolha do jeito de projetar de um nível, numa frase (seção C.3), com os números da retroprojeção da própria base."""
    r = series_brasil.rotulos(base)
    quem = r["os_unidades"] if nivel == "municipios" else r["os_grupos"] + " como unidade"
    if escolha["motivo"] != "escolhido":
        return "Para " + quem + ": " + MOTIVOS_SEM_ESCOLHA[escolha["motivo"]][:1].lower() + MOTIVOS_SEM_ESCOLHA[escolha["motivo"]][1:]
    do_escolhido = next(item for item in escolha["candidatos"] if item["metodo"] == escolha["metodo"])
    return ("Para " + quem + ", a base escolheu a " + _nome_do_metodo(base, escolha["metodo"]) + ": na retroprojeção, ela errou " +
            _br(round(100.0 * (1 - do_escolhido["frente_ao_m0"]))) + "% menos que manter o último valor, e menos em " +
            _br(do_escolhido["menos_erro_em"]) + " de " + _br(do_escolhido["combinacoes"]) + " combinações de origem e prazo.")


def _retro_da_resposta(base: Base, retros: dict, em_10: int = FAIXA_PADRAO) -> dict:
    """A retroprojeção na resposta: as origens, as faixas e a tabela das unidades da base (os campos de antes) e, por nível, o
    jeito de projetar que a base escolheu, com os candidatos ("Como os métodos se saíram no passado")."""
    retro = retros["municipios"]

    def faixas_de(do_nivel: Retroprojecao) -> list:
        saida = []
        for (da_faixa, porte, anos), f in sorted(do_nivel.faixas.items()):
            if da_faixa != em_10:
                continue
            com_limites = "inferior" in f
            saida.append({"porte": ROTULOS_DOS_PORTES_DA_FAIXA[porte], "anos": anos, "em_10": em_10,
                          "inferior_pct": 100.0 * f["inferior"] if com_limites else None,
                          "superior_pct": 100.0 * f["superior"] if com_limites else None, "casos": f["casos"], "pede": f["pede"],
                          "origens": f.get("origens"), "cobertura_pct": f.get("cobertura"), "estado": f["estado"], "como": f["como"],
                          "origens_de_teste": f.get("origens_de_teste"), "casos_de_teste": f.get("casos_de_teste"),
                          "rotulo": NOMES_DA_CONFERENCIA[f["estado"]] + (" (" + COMO_A_FAIXA_FOI_MONTADA[f["como"]] + ")"
                                                                           if f["como"] != "propria" else "")})
        return saida

    def escolha_de(nivel: str, do_nivel: Retroprojecao) -> dict:
        e = do_nivel.escolha
        return {"metodo": e["metodo"], "rotulo": _nome_do_metodo(base, e["metodo"]), "motivo": e["motivo"], "origens": e["origens"],
                "combinacoes": e["combinacoes"], "texto": _texto_da_escolha(base, nivel, e),
                "candidatos": [{**item, "rotulo": _nome_do_metodo(base, item["metodo"])} for item in e["candidatos"]],
                "excecoes": [ROTULOS_DOS_PORTES_DA_FAIXA[porte] for porte in e["excecoes"]]}
    niveis = {nivel: {"origens": list(do_nivel.origens), "escolha": escolha_de(nivel, do_nivel), "faixas": faixas_de(do_nivel),
                      "tabela": [{**linha, "porte": ROTULOS_DOS_PORTES_DA_FAIXA[linha["porte"]]} for linha in do_nivel.tabela]}
              for nivel, do_nivel in retros.items() if do_nivel is not None}
    return {"origens": list(retro.origens), "faixas": niveis["municipios"]["faixas"], "tabela": niveis["municipios"]["tabela"],
            "em_10": em_10, "escolha": niveis["municipios"]["escolha"], "niveis": niveis}


def _notas(base: Base, niveis: set, com_referencias: bool = False, com_planejamento: bool = False, em_10: int = FAIXA_PADRAO,
           crescimento_pct: float = 0.0) -> list[str]:
    r = series_brasil.rotulos(base)
    meses = series_brasil.meses_de_registro(base.periodos)
    # Uma base só com anos ("AAAA00"): um registro por ano ou, quando faltam anos entre os registros, registros anuais espaçados.
    anual = all(periodo.endswith("00") for periodo in base.periodos)
    registros = ("um registro por ano" if base.ancora == "00" else "registros anuais, com anos sem registro" if anual else
                 "registros de " + " e ".join(detector.MESES[int(mes) - 1] for mes in meses) if 0 < len(meses) <= 3 else "registros em datas variadas")
    intervalos = sorted({int(round(float(valor))) for valor in np.diff(base.meses) if valor > 0})
    notas = ["Cenários hipotéticos e condicionais: não são previsão, observação atual, conclusão sobre o atendimento nem recomendação "
             "de provimento.",
             "O registro mais recente da base é " + detector.curta(base.periodos[-1]) + ": o que vem depois dele no gráfico é simulado, "
             "nunca observado. A base só tem " + r["profissionais"] + ", com " + registros +
             (" (" + " e ".join(str(valor) for valor in intervalos) + " meses entre um e outro)" if 0 < len(intervalos) <= 2 and not anual
              else "") + ".",
             "A base do cenário e a intervenção ficam separadas: N(t) = máx(0, B(t) + I(t)). O crescimento histórico não é aplicado aos " +
             r["profissionais"] + " acrescentados; a permanência total dos acréscimos é uma hipótese.",
             "Cada intervenção vale para cada território do cenário: cada " + r["unidade"] +
             (", " + r["grupo"] + " como unidade" if base.estados else "") + " e conjunto recebe o acréscimo "
             "ou a retirada inteiros, não uma parte de um total.",
             "\"Continuar como vinha\" usa a forma de projetar que a própria base escolheu, pela retroprojeção: o Agente refaz no "
             "passado a projeção que teria feito e confere com o que aconteceu depois. Comparar métodos e janelas mostra a "
             "sensibilidade ao método e à janela, não uma faixa de confiança.",
             "A faixa de " + str(em_10) + " em cada 10 só existe para a forma e a janela escolhidas pela base, quando há casos bastantes "
             "na retroprojeção; é \"conferida\" quando cobriu o esperado nos dados que vieram depois e \"provisória\" quando ainda não "
             "deu para conferir. Fora disso, é indisponível, com o motivo. O passado testado não garante o futuro.",
             "A média aritmética das taxas é só descrição do passado; o percentual médio que reproduz o crescimento ocorrido é a taxa "
             "composta (M1)."]
    if niveis - {"municipios"}:
        # Com a contagem própria dos grupos (a base do Brasil), eles entram como unidade, e o todo é a contagem dele; sem ela (uma
        # planilha), o todo é a soma das unidades com registro.
        # Numa planilha com a coluna de grupo, o grupo como unidade é a soma das unidades dele (nas datas em que todas têm registro).
        do_todo = (r["o_todo"][:1].upper() + r["o_todo"][1:] + " é a soma d" + r["os_unidades"] + " com registro em cada data e entra com "
                   "um padrão provisório (a forma escolhida para " + r["os_unidades"] + ").")
        notas.append((r["grupos"][:1].upper() + r["grupos"][1:] + " como unidade usam a contagem própria de cada um, e " + r["o_todo"] +
                      ", a contagem do todo, com um padrão provisório (a forma escolhida para o nível de baixo)."
                      if base.estados and not base.grupos_por_soma else
                      r["grupos"][:1].upper() + r["grupos"][1:] + " como unidade são a soma d" + r["os_unidades"] + " de cada " +
                      ("um" if r["o_grupo"].startswith("o ") else "uma") + ", nas datas em "
                      "que tod" + r["os_unidades"][:2] + " têm registro. " + do_todo if base.estados else do_todo) +
                     " Num conjunto, o valor é a soma dos componentes, não o número de " + r["profissionais"] + " diferentes.")
    if com_referencias:
        hipotese = ("população constante" if not crescimento_pct else _hipotese_de_populacao(base, crescimento_pct) +
                    " (a base não traz população futura: a taxa de crescimento é uma hipótese sua)")
        notas.append("Referências: a comparação mostra a diferença, a razão e o índice (100 é a referência), sem chamar a variação de "
                     "convergência. Sem cruzamento, \"não alcança no horizonte simulado\": nenhuma data é inventada. Comparar "
                     "quantitativos de territórios de portes diferentes não é comparar a suficiência do atendimento; por taxa, vale a "
                     "hipótese de " + hipotese + ".")
    if com_planejamento:
        notas.append("Planejamento inverso: o menor número inteiro de " + r["profissionais"] + " por evento com que o cenário alcança a "
                     "meta na data final, com a base do cenário sem arredondar. É uma conta condicional às hipóteses, não um plano.")
    return notas


# --------------------------------------------------------------------------------------------- referências (seção 10.5)
def _referencias(brutas, base: Base, territorios: list) -> list[dict]:
    """As referências do pedido: um município, um estado como unidade, o Brasil ou um conjunto da seleção, **fixa** (o valor do
    último registro usável se mantém) ou **dinâmica** (segue um método próprio, sem intervenções); ou um **valor** informado pela
    pessoa. Podem ficar fora da seleção do Simulador."""
    if brutas in (None, []):
        return []
    if not isinstance(brutas, list) or len(brutas) > MAX_REFERENCIAS:
        raise ValueError("Referências inválidas: envie uma lista de até " + str(MAX_REFERENCIAS) + ".")
    conjuntos = {territorio.id: territorio for territorio in territorios if territorio.tipo == "conjunto"}
    saida, vistos = [], set()
    for posicao, bruta in enumerate(brutas):
        if not isinstance(bruta, dict):
            raise ValueError("Referência inválida.")
        chave = str(bruta.get("id") or "r" + str(posicao + 1))
        if chave in vistos:
            raise ValueError("Referências com o mesmo id no pedido.")
        vistos.add(chave)
        tipo = bruta.get("tipo", "fixa")
        if tipo not in ("fixa", "dinamica", "valor"):
            raise ValueError("Referência inválida: o tipo é fixa, dinamica ou valor.")
        if tipo == "valor":
            valor = bruta.get("valor")
            if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor < 0:
                raise ValueError("Referência inválida: o valor informado é um número igual ou maior que zero.")
            saida.append({"id": chave, "tipo": "valor", "valor": float(valor), "territorio": None, "metodo": None, "taxa": None,
                          "rotulo": str(bruta.get("rotulo") or "Valor informado por você")[:80]})
            continue
        alvo = bruta.get("territorio")
        if alvo == "br":
            territorio = series_brasil.brasil(base)
        elif isinstance(alvo, str) and alvo.startswith("uf:"):
            territorio = series_brasil.estado(base, series_brasil._prefixo(base, alvo))
        elif isinstance(alvo, str) and alvo.startswith(base.prefixo_do_id):
            territorio = series_brasil.municipio(base, series_brasil._codigo(base, alvo))
        elif alvo in conjuntos:
            territorio = conjuntos[alvo]
        else:
            raise ValueError("Referência inválida: indique um território da base (na base do Brasil, um município, code:…, ou um "
                             "estado, uf:…), o todo (br) ou um conjunto da seleção do Simulador.")
        metodo, taxa = bruta.get("metodo", "padrao"), bruta.get("taxa_manual_pct")
        if tipo == "fixa":
            metodo, taxa = "M0", None
        elif metodo not in METODOS:
            raise ValueError("Método desconhecido na referência: " + str(metodo) + ".")
        elif metodo == "manual" and (isinstance(taxa, bool) or not isinstance(taxa, (int, float)) or not -99 <= taxa <= 500):
            raise ValueError("Taxa manual inválida na referência: informe a taxa anual, em %, de −99 a 500. O sistema não sugere uma taxa.")
        saida.append({"id": chave, "tipo": tipo, "valor": None, "territorio": territorio, "metodo": metodo,
                      "taxa": float(taxa) if metodo == "manual" else None, "rotulo": territorio.rotulo})
    return saida


def _curva_da_referencia(base: Base, cal: detector.Calibracao, retros: dict, ref: dict, inicio: int, fim: int) -> dict:
    """A referência ao longo do tempo: uma função do mês (None quando não há valor) e o que a descreve."""
    if ref["tipo"] == "valor":
        return {"estado": "calculada", "funcao": lambda mes: ref["valor"], "descricao": "valor informado por você, mantido",
                "usado": None, "avisos": [], "origem": None}
    resultado = _base_do_cenario(base, cal, _retro_do(retros, ref["territorio"], base), ref["territorio"], ref["metodo"], ref["taxa"], inicio, fim)
    if resultado["estado"] != "calculado":
        return {"estado": "nao_calculavel", "motivo": resultado["motivo"]}
    origem, funcao, serie = resultado["origem"], resultado["funcao"], ref["territorio"].serie
    mes_da_origem = int(base.meses[origem])
    por_mes = {int(base.meses[i]): float(serie[i]) for i in range(len(base.periodos)) if serie[i] == serie[i]}

    def no_mes(mes: int):
        if mes <= mes_da_origem:   # antes da origem da referência, vale o registro, se houver
            return por_mes.get(mes)
        return max(0.0, float(funcao((mes - mes_da_origem) / 12.0)))
    descricao = ("fixa: o valor de " + detector.curta(base.periodos[origem]) + " mantido") if ref["tipo"] == "fixa" else \
        ("dinâmica: " + NOMES_DOS_METODOS[resultado["usado"]] + ", com registros até " + detector.curta(base.periodos[origem]))
    return {"estado": "calculada", "funcao": no_mes, "descricao": descricao, "usado": resultado["usado"],
            "avisos": resultado["avisos"] if ref["tipo"] == "dinamica" else [], "origem": base.periodos[origem]}


def _sobreposicao(base: Base, territorio: Territorio, ref: dict) -> list[str]:
    """Os avisos de sobreposição e de unidade entre um território e uma referência: nunca se declara independência que não há."""
    outro = ref["territorio"]
    if outro is None:
        return []
    avisos = []

    def municipios_de(t: Territorio) -> set | None:
        if t.tipo == "municipio":
            return {t.id}
        if t.tipo == "conjunto" and t.nivel == "municipios":
            return set(t.membros)
        return None

    def ufs_de(t: Territorio) -> set:
        if t.tipo == "estado":
            return {t.uf}
        if t.tipo == "conjunto" and t.nivel == "estados":
            return {membro[3:] for membro in t.membros}
        return set()
    if outro.id == territorio.id:
        avisos.append("A referência é o próprio território.")
    elif outro.tipo == "brasil":
        avisos.append("A referência (" + outro.rotulo + ") contém o território: a comparação não é independente.")
    elif territorio.tipo == "brasil":
        avisos.append("O território (" + territorio.rotulo + ") contém a referência: a comparação não é independente.")
    else:
        meus, dele = municipios_de(territorio), municipios_de(outro)
        if meus is not None and dele is not None:
            comuns = meus & dele
            if comuns:
                r = series_brasil.rotulos(base)
                avisos.append("O território e a referência têm " + str(len(comuns)) + " " + (r["unidade"] if len(comuns) == 1 else r["unidades"]) +
                              " em comum: a comparação não é independente.")
        elif meus is not None and {"code:" + codigo for uf in ufs_de(outro) for codigo in
                                   (base.codigos[linha] for linha in base.do_estado.get(uf, ()))} & meus:
            avisos.append("A referência contém o território (" + series_brasil.rotulos(base)["o_grupo"] + " inclui " +
                          series_brasil.rotulos(base)["o_unidade"] + "): a comparação não é independente.")
        elif dele is not None and {"code:" + codigo for uf in ufs_de(territorio) for codigo in
                                   (base.codigos[linha] for linha in base.do_estado.get(uf, ()))} & dele:
            avisos.append("O território contém a referência: a comparação não é independente.")
        elif ufs_de(territorio) & ufs_de(outro):
            avisos.append("O território e a referência têm " + series_brasil.rotulos(base)["grupos"] + " em comum: a comparação não é independente.")
    if outro.unidade != territorio.unidade:
        avisos.append("As contagens têm unidades diferentes: no território, " + territorio.unidade + "; na referência, " + outro.unidade +
                      ". A comparação é entre esses quantitativos.")
    return avisos


def _hipotese_de_populacao(base: Base, crescimento_pct: float, com_valor_informado: bool = False) -> str:
    """A hipótese de população da comparação por taxa, em palavras: constante (a do último registro) ou crescendo (ou diminuindo)
    x% ao ano depois dele, uma hipótese da pessoa. A mesma taxa vale para o território e para a referência; quando a referência é
    um valor informado, ele já é uma taxa e não muda."""
    ultimo = detector.curta(base.periodos[-1])
    if not crescimento_pct:
        return "população constante, a de " + ultimo
    return ("população " + ("crescendo " if crescimento_pct > 0 else "diminuindo ") + _curto(abs(crescimento_pct)) + "% ao ano depois de " +
            ultimo + ("; o valor informado não muda" if com_valor_informado else ", a mesma taxa no território e na referência"))


def _comparar(base: Base, territorio: Territorio, resultado: dict, ref: dict, curva: dict, metrica: str, populacoes: dict,
              forma: str = "diferenca", crescimento_pct: float = 0.0) -> dict:
    """Um cenário de um território diante de uma referência: a diferença, a razão e o índice em cada data, e o alcance. Sem
    cruzamento no horizonte, "não alcança no horizonte simulado": nenhuma data é inventada. `forma` diz o que a frase destaca (a
    diferença ou a razão); os três números continuam em cada data. Por taxa, a população é a do último registro ou, com
    `crescimento_pct`, cresce essa taxa ao ano depois dele (nas datas até o último registro, vale a dele)."""
    cabecalho = {"id": ref["id"], "rotulo": ref["rotulo"], "tipo": ref["tipo"], "metrica": metrica, "forma": forma,
                 "avisos": _sobreposicao(base, territorio, ref)}
    if resultado["estado"] != "calculado":
        return {**cabecalho, "estado": "nao_calculavel", "motivo": "O cenário deste território não foi calculado."}
    if curva["estado"] != "calculada":
        return {**cabecalho, "estado": "nao_calculavel", "motivo": "A referência não pôde ser calculada: " + curva["motivo"]}
    fator_a = fator_b = 1.0
    if metrica == "taxa":
        pop_a = populacoes.get(territorio.id)
        pop_b = None if ref["territorio"] is None else populacoes.get(ref["territorio"].id)
        if not pop_a or (ref["territorio"] is not None and not pop_b):
            return {**cabecalho, "estado": "nao_calculavel", "motivo": "Sem população válida no último registro para a hipótese de "
                    "população " + ("constante." if not crescimento_pct else "da comparação.")}
        fator_a = 1000.0 / pop_a
        fator_b = 1.0 if ref["territorio"] is None else 1000.0 / pop_b   # o valor informado já está na métrica escolhida
    origem = base.periodos.index(resultado["parametros"]["origem"])
    datas = [(int(base.meses[origem]), base.periodos[origem], float(resultado["parametros"]["n0"]))] + \
        [(mes_da_competencia(ponto["data"]), ponto["data"], float(ponto["total"])) for ponto in resultado["trajetoria"]]
    ultimo = int(base.meses[-1])
    pontos = []
    for mes, data, a in datas:
        b = curva["funcao"](mes)
        if b is None:
            continue
        # A população cresce só depois do último registro: até ele, vale a população dele.
        da_populacao = (1.0 + crescimento_pct / 100.0) ** (max(0, mes - ultimo) / 12.0) if metrica == "taxa" else 1.0
        a, b = a * fator_a / da_populacao, b * (fator_b / da_populacao if ref["territorio"] is not None else fator_b)
        pontos.append({"data": data, "territorio": a, "referencia": b, "diferenca": b - a,
                       "razao": (a / b) if b > 0 else None, "indice": (100.0 * a / b) if b > 0 else None})
    if not pontos:
        return {**cabecalho, "estado": "nao_calculavel", "motivo": "A referência não tem valor nas datas do cenário."}
    inicial, final = pontos[0], pontos[-1]
    if inicial["territorio"] >= inicial["referencia"]:
        alcance = {"estado": "ja_acima", "data": None}
    else:
        primeiro = next((ponto for ponto in pontos[1:] if ponto["territorio"] >= ponto["referencia"]), None)
        alcance = {"estado": "alcanca", "data": primeiro["data"]} if primeiro else {"estado": "nao_alcanca", "data": None}
    unidade = series_brasil.rotulos(base)["profissionais"] + ("" if metrica == "quantidade" else " por 1.000 habitantes")
    casas = 1 if metrica == "quantidade" else 2
    diferenca = final["diferenca"]
    if abs(diferenca) < 0.5 * 10 ** -casas:
        destaque = "o mesmo valor"
    elif forma == "razao":
        # Pela razão: quantas vezes o valor da referência o território teria (o índice é a mesma conta, vezes 100).
        destaque = ("a razão não pode ser calculada, porque a referência é zero" if final["razao"] is None else
                    _br(round(final["razao"], 2), 2) + " vezes o valor da referência")
    else:
        destaque = _br(round(abs(diferenca), casas), casas) + (" abaixo da referência" if diferenca > 0 else " acima da referência")
    texto = ("Em " + detector.curta(final["data"]) + ", " + territorio.rotulo + " teria " + _br(round(final["territorio"], casas), casas) +
             " " + unidade + ", e a referência " + ref["rotulo"] + " (" + curva["descricao"] + "), " +
             _br(round(final["referencia"], casas), casas) + ": " + destaque +
             ("" if final["indice"] is None else " (índice " + _br(round(final["indice"], 1)) + "; 100 é a referência)") + ". " +
             {"ja_acima": "Na origem, o território já está no nível da referência ou acima dele.",
              "nao_alcanca": "Não alcança no horizonte simulado (até " + detector.curta(final["data"]) + ").",
              "alcanca": "No cenário, alcança a referência em " + detector.curta(alcance["data"] or final["data"]) +
                         ", a primeira data avaliada em que isso ocorre."}[alcance["estado"]] +
             ((" Hipótese: " if not crescimento_pct else " Hipótese sua: ") +
              _hipotese_de_populacao(base, crescimento_pct, ref["territorio"] is None) + "." if metrica == "taxa" else ""))
    return {**cabecalho, "estado": "calculada", "descricao": curva["descricao"], "metodo": curva["usado"],
            "avisos": cabecalho["avisos"] + [aviso["texto"] for aviso in curva["avisos"]],
            "pontos": pontos, "inicial": inicial, "final": final, "alcance": alcance, "texto": texto}


# --------------------------------------------------------------------------------------------- planejamento inverso (seção 10.3)
def _plano(bruto) -> dict | None:
    """O pedido de planejamento inverso de um cenário: a meta (um valor, o patamar anterior ou uma referência) e o calendário dos
    acréscimos (uma data ou eventos periódicos, com a permanência)."""
    if bruto in (None, {}):
        return None
    if not isinstance(bruto, dict) or not isinstance(bruto.get("meta"), dict):
        raise ValueError("Planejamento inverso inválido: envie a meta e o calendário dos acréscimos.")
    meta = bruto["meta"]
    tipo = meta.get("tipo")
    if tipo not in ("valor", "patamar", "referencia"):
        raise ValueError("Planejamento inverso inválido: a meta é um valor, o patamar anterior ou uma referência.")
    valor = meta.get("valor")
    if tipo == "valor" or (tipo == "patamar" and valor is not None):
        if isinstance(valor, bool) or not isinstance(valor, (int, float)) or not math.isfinite(valor) or valor <= 0 or valor > 10_000_000:
            raise ValueError("Planejamento inverso inválido: a meta é um número acima de zero.")
        valor = float(valor)
    if tipo == "referencia" and not isinstance(meta.get("referencia"), str):
        raise ValueError("Planejamento inverso inválido: indique a referência da meta.")
    [calendario] = _intervencoes([{"tipo": "acrescimo", "quantidade": 1, "em": bruto.get("em"), "ate": bruto.get("ate"),
                                   "a_cada_meses": bruto.get("a_cada_meses", 12),
                                   "permanencia_pct_ao_ano": bruto.get("permanencia_pct_ao_ano", 100)}], set())
    return {"meta": {"tipo": tipo, "valor": valor, "referencia": meta.get("referencia")}, "calendario": calendario}


def _planejar(base: Base, cal: detector.Calibracao, retro: Retroprojecao, territorio: Territorio, cenario: dict, resultado: dict,
              inicio: int, fim: int, horizonte: int, varios: bool, curvas: dict, em_10: int = FAIXA_PADRAO) -> dict | None:
    """O planejamento inverso de um território num cenário: o menor número inteiro de médicos por evento com que N(T) alcança a
    meta na data final T, com a base B(T) sem arredondar (seção 8.8). É uma conta condicional às hipóteses, nunca um plano."""
    plano = cenario.get("planejamento")
    if not plano:
        return None
    if resultado["estado"] != "calculado":
        return {"estado": "nao_calculavel", "motivo": "O cenário deste território não foi calculado."}
    origem = base.periodos.index(resultado["parametros"]["origem"])
    mes_da_origem = int(base.meses[origem])
    data_final = detector.curta(_data(horizonte))
    meta = plano["meta"]
    da_meta = {}   # de onde a meta veio, quando ela é o patamar: o patamar sem arredondar e de quantos registros é a média
    if meta["tipo"] == "referencia":
        curva = curvas.get(meta["referencia"])
        if curva is None:
            return {"estado": "nao_calculavel", "motivo": "A referência da meta não está no pedido."}
        if curva["estado"] != "calculada" or curva["funcao"](horizonte) is None:
            return {"estado": "nao_calculavel", "motivo": "A referência da meta não pôde ser calculada."}
        alvo = float(curva["funcao"](horizonte))
        rotulo = "Meta hipotética: alcançar a referência " + curva["rotulo"] + " (" + _br(round(alvo, 1)) + " " + series_brasil.rotulos(base)["profissionais"] + " em " + data_final + ")"
    elif meta["tipo"] == "patamar":
        do_territorio = detector._patamar(base, cal if territorio.tipo == "municipio" else None, cal.blocos, territorio.linha,
                                          territorio.serie, origem, detector.PADRAO["patamar"]).get("patamar")
        alvo = meta["valor"] if meta["valor"] is not None else do_territorio
        if alvo is None:
            return {"estado": "nao_calculavel", "motivo": "Não há patamar anterior calculável para este território (faltam dois anos "
                    "completos de registros antes dos mais recentes)."}
        # O patamar é uma média e pode ter decimal (78,25); a meta é um número inteiro de profissionais, o patamar arredondado para
        # cima (79), para o resultado do cenário não parecer abaixo dela. O rótulo diz de onde ela veio: o patamar do território
        # (a média dos registros de dois anos completos) ou um valor informado no pedido que não é o patamar dele.
        patamar = float(alvo)
        alvo = float(math.ceil(patamar - 1e-9))
        arredondado = alvo - patamar > 1e-9
        e_o_do_territorio = do_territorio is not None and abs(patamar - float(do_territorio)) < 1e-6
        registros = detector._registros_de_dois_anos(base) if e_o_do_territorio else None
        da_meta = {"patamar": patamar, "registros": registros, "arredondado": arredondado}
        sem_arredondar = detector._do_patamar(patamar, sempre_com_decimal=True)
        if e_o_do_territorio:
            de_onde = ("patamar de " + sem_arredondar + ", " if arredondado else "") + "média de " + str(registros) + " registros"
        else:
            de_onde = "patamar informado" + (": " + sem_arredondar if arredondado else "")
        rotulo = ("Meta hipotética: voltar ao patamar de " + _br(alvo) + " " + series_brasil.rotulos(base)["profissionais"] + " em " + data_final +
                  " (" + de_onde + (", arredondado para cima" if arredondado else "") + ")")
    else:
        alvo = float(meta["valor"])
        rotulo = "Meta hipotética: " + _br(round(alvo, 1)) + " " + series_brasil.rotulos(base)["profissionais"] + " em " + data_final
    calendario = plano["calendario"]
    eventos = [data for data in calendario["datas"] if mes_da_origem < data <= horizonte]
    comum = {"meta": {"tipo": meta["tipo"], "valor": alvo, "rotulo": rotulo, **da_meta}, "base_na_data_final": resultado["final"]["base"],
             "outras_intervencoes": resultado["final"]["intervencao"], "sem_o_plano": resultado["final"]["total"],
             "eventos": len(eventos), "datas": [_data(data) for data in eventos], "permanencia_pct_ao_ano": calendario["permanencia"]}
    if not eventos:
        return {**comum, "estado": "nao_calculavel", "motivo": "Nenhum evento do calendário cai depois da origem do cenário e até a "
                "data final."}
    # A conta usa a base sem arredondar e sem o piso em zero do total exibido.
    atual = resultado["final"]["base"] + resultado["final"]["intervencao"]
    permanencia = calendario["permanencia"]
    peso = sum((permanencia / 100.0) ** ((horizonte - data) / 12.0) if permanencia < 100 else 1.0 for data in eventos)
    falta = alvo - atual
    if falta <= 1e-9:
        return {**comum, "estado": "ja_alcancada", "falta": 0.0, "por_evento": 0, "total": 0, "teorico_por_evento": 0.0,
                "resultado": resultado["final"]["total"], "intervencao": None,
                "texto": rotulo + ". No cenário, o território já teria " + _br(round(atual, 1)) + " " + series_brasil.rotulos(base)["profissionais"] +
                         " em " + data_final +
                         ": a meta é alcançada sem acréscimo."}
    if peso <= 0:
        return {**comum, "estado": "nao_alcancavel", "falta": falta,
                "motivo": "Com permanência zero, nenhum " + series_brasil.rotulos(base)["profissional"] + " acrescentado está no território na data final: a meta não é alcançada "
                          "com este calendário."}
    teorico = falta / peso
    por_evento = max(1, math.ceil(teorico - 1e-9))
    while atual + por_evento * peso < alvo - 1e-9:      # busca entre inteiros, contra o erro de ponto flutuante
        por_evento += 1
    while por_evento > 1 and atual + (por_evento - 1) * peso >= alvo - 1e-9:
        por_evento -= 1
    planejada = {"tipo": "acrescimo", "quantidade": float(por_evento), "em": eventos[0], "ate": eventos[-1],
                 "a_cada_meses": calendario["a_cada_meses"], "periodica": len(eventos) > 1, "permanencia": permanencia,
                 "territorios": {territorio.id}, "datas": eventos, "planejada": True}
    aplicado = _simular(base, cal, retro, territorio, {**cenario, "intervencoes": cenario["intervencoes"] + [planejada]},
                        inicio, fim, horizonte, varios, em_10)
    quando = ("em " + detector.curta(_data(eventos[0]))) if len(eventos) == 1 else \
        ("em cada um dos " + str(len(eventos)) + " eventos, de " + detector.curta(_data(eventos[0])) + " a " + detector.curta(_data(eventos[-1])))
    texto = (rotulo + ". Menor acréscimo inteiro que alcança a meta, nas hipóteses deste cenário: " + _br(por_evento) +
             " " + (series_brasil.rotulos(base)["profissional"] if por_evento == 1 else series_brasil.rotulos(base)["profissionais"]) + " " + quando +
             ("" if len(eventos) == 1 else " (" + _br(por_evento * len(eventos)) + " no total)") +
             ". Pela conta sem arredondar, seriam " + _br(round(teorico, 2), 2) + " por evento. " + (aplicado.get("texto") or "") +
             " É uma conta condicional às hipóteses do cenário, não um plano.")
    return {**comum, "estado": "calculado", "falta": falta, "por_evento": por_evento, "total": por_evento * len(eventos),
            "teorico_por_evento": teorico, "resultado": aplicado["final"]["total"] if aplicado["estado"] == "calculado" else None,
            # O caminho do cenário com o acréscimo calculado, para o gráfico: o total e o acréscimo acumulado em cada data.
            "trajetoria": [{"data": ponto["data"], "total": ponto["total"], "intervencao": ponto["intervencao"]}
                           for ponto in aplicado["trajetoria"]] if aplicado["estado"] == "calculado" else [],
            "intervencao": {"tipo": "acrescimo", "quantidade": por_evento, "em": _data(eventos[0]),
                            **({"ate": _data(eventos[-1]), "a_cada_meses": calendario["a_cada_meses"]} if len(eventos) > 1 else {}),
                            "permanencia_pct_ao_ano": permanencia},
            "texto": texto}


def _hipotetico(territorio: Territorio, resultado: dict) -> dict | None:
    """Os níveis no cenário (Proposta V3, seção C.6): só os sinais 1 e 2 do Detector (poucos profissionais e nenhum, por
    convenção) podem ser aplicados a um valor simulado, rotulados como hipótese do cenário. Os sinais comparados com a base
    (5 a 10) e os de evento observado (queda, patamar, declínio) nunca se aplicam a curvas simuladas. Só para municípios."""
    if territorio.tipo != "municipio" or resultado["estado"] != "calculado":
        return None
    limites = detector.PADRAO["estrutural"]

    def classe(valor: float):
        return detector._classe_estrutural(_inteiro_da_tela(valor), limites)
    final = resultado["final"]
    inteiro = _inteiro_da_tela(final["total"])
    saida = {"rotulo": "hipótese do cenário", "data": final["data"], "valor": final["total"], "inteiro": inteiro,
             "classe": classe(final["total"]), "impacto_pct": (100.0 / inteiro) if inteiro > 0 else None}
    if final["faixa"]:
        saida["na_faixa"] = {"inferior": classe(final["faixa"]["inferior"]), "superior": classe(final["faixa"]["superior"])}
    return saida


def compute(sources, opcoes: dict, base: Base | None = None) -> dict:
    """POST /api/simulador: os cenários de cada território da seleção local, na base do Brasil (pelas fontes verificadas) ou na de
    uma planilha enviada (`base`, de series_da_planilha). Só calcula: nada é registrado na sessão, e nada vai ao provedor de IA."""
    # A marca de base com um registro por ano vale só durante este cálculo: no fim, volta ao que era.
    marca = _ANUAL.set(False)
    try:
        return _calcular(sources, opcoes, base)
    finally:
        _ANUAL.reset(marca)


def _calcular(sources, opcoes: dict, base: Base | None = None) -> dict:
    """O cálculo de `compute`, com a marca de base anual já sob a guarda dele."""
    if not isinstance(opcoes, dict):
        raise ValueError("Pedido do Simulador inválido.")
    desconhecidas = set(opcoes) - {"base", "estados_unidade", "conjuntos", "brasil", "janela", "horizonte", "cenarios", "referencias",
                                   "comparacao", "faixa"}
    if desconhecidas:
        raise ValueError("Opção desconhecida no pedido do Simulador: " + ", ".join(sorted(desconhecidas)) + ".")
    em_10 = opcoes.get("faixa", FAIXA_PADRAO)
    if isinstance(em_10, bool) or em_10 not in FAIXAS_EM_10:
        raise ValueError("Faixa inválida: escolha 5, 8 ou 9 em cada 10.")
    em_10 = int(em_10)   # 8.0 é 8: os textos dizem "8 em cada 10"
    base = base if base is not None else series_brasil.base_de(sources)
    # Uma base com um registro por ano tem todas as datas no formato "AAAA00", mesmo quando faltam anos entre os registros.
    _ANUAL.set(all(periodo.endswith("00") for periodo in base.periodos))
    cal = detector.calibrar(base)
    # A retroprojeção de cada nível, montada uma vez por versão da base: as unidades e, quando a base tem a contagem própria dos
    # grupos de cima, os grupos como unidade.
    retro = {"municipios": retroprojetar(base, "municipios"), "estados": retroprojetar(base, "estados") if base.estados else None}
    territorios = series_brasil.selecao(base, opcoes, com_brasil=True)
    if len(territorios) > MAX_TERRITORIOS:
        raise ValueError("O Simulador compara até " + str(MAX_TERRITORIOS) + " territórios de cada vez (a seleção tem " +
                         str(len(territorios)) + "): reduza a seleção local do Simulador.")
    inicio, fim, padrao = _janela(base, opcoes.get("janela"))
    ultimo = int(base.meses[-1])
    horizonte = _competencia_futura(opcoes["horizonte"], "Data final") if opcoes.get("horizonte") else ultimo + 24
    if horizonte <= int(base.meses[fim]):
        raise ValueError("A data final precisa ser depois do fim da janela (" + detector.curta(base.periodos[fim]) + ").")
    cenarios = _cenarios(opcoes.get("cenarios"), base, {territorio.id for territorio in territorios})
    referencias = _referencias(opcoes.get("referencias"), base, territorios)
    comparacao = opcoes.get("comparacao") or {}
    metrica = comparacao.get("metrica", "quantidade") if isinstance(comparacao, dict) else None
    if metrica not in METRICAS:
        raise ValueError("Comparação inválida: a métrica é quantidade ou taxa.")
    # A forma da comparação e a hipótese de população (seção C.5): campos novos e opcionais; sem eles, vale o de antes (a
    # diferença e a população constante).
    forma = comparacao.get("forma", "diferenca")
    if forma not in FORMAS_DA_COMPARACAO:
        raise ValueError("Comparação inválida: a forma é diferenca ou razao.")
    crescimento_pct = comparacao.get("populacao_pct_ao_ano", 0)
    if isinstance(crescimento_pct, bool) or not isinstance(crescimento_pct, (int, float)) or not math.isfinite(crescimento_pct) or \
            abs(crescimento_pct) > MAX_CRESCIMENTO_DA_POPULACAO:
        raise ValueError("Comparação inválida: o crescimento da população é um número entre −" + _br(MAX_CRESCIMENTO_DA_POPULACAO) + "% e +" +
                         _br(MAX_CRESCIMENTO_DA_POPULACAO) + "% ao ano.")
    crescimento_pct = float(crescimento_pct)
    if crescimento_pct and metrica != "taxa":
        raise ValueError("Comparação inválida: o crescimento da população vale só na comparação por taxa (a métrica taxa).")
    curvas = {ref["id"]: {**_curva_da_referencia(base, cal, retro, ref, inicio, fim), "rotulo": ref["rotulo"]} for ref in referencias}
    populacoes = {}
    if metrica == "taxa":   # hipótese explícita: a população do último registro vale em todas as datas simuladas
        for alvo in territorios + [ref["territorio"] for ref in referencias if ref["territorio"] is not None]:
            valor = comparativos.populacao_do_territorio(base, alvo)[-1]
            populacoes[alvo.id] = float(valor) if valor == valor and valor > 0 else None
    varios = len(territorios) > 1

    def do_cenario(territorio: Territorio, cenario: dict) -> dict:
        resultado = _simular(base, cal, retro, territorio, cenario, inicio, fim, horizonte, varios, em_10)
        if referencias:
            resultado["comparacoes"] = [_comparar(base, territorio, resultado, ref, curvas[ref["id"]], metrica, populacoes, forma,
                                                  crescimento_pct) for ref in referencias]
        planejado = _planejar(base, cal, retro, territorio, cenario, resultado, inicio, fim, horizonte, varios, curvas, em_10)
        if planejado is not None:
            resultado["planejamento"] = planejado
        hipotetico = _hipotetico(territorio, resultado)
        if hipotetico is not None:
            resultado["hipotetico"] = hipotetico
        return resultado
    saida = []
    for territorio in territorios:
        indices, _ = _usaveis(base, cal, territorio, inicio, fim)
        saida.append({
            "id": territorio.id, "tipo": territorio.tipo, "nivel": territorio.nivel, "rotulo": territorio.rotulo,
            "uf": series_brasil.nome_do_grupo(base, territorio.uf)[0] if territorio.uf else None, "unidade": territorio.unidade,
            **({"membros": list(territorio.membros), "nomes_dos_membros": list(territorio.nomes_dos_membros), "versao": territorio.versao}
               if territorio.tipo == "conjunto" else {}),
            "observado": _observado(base, cal, territorio),
            "historico": _estatisticas(base, territorio.serie, indices),
            "lacunas": [base.periodos[i] for i in range(inicio, fim + 1) if territorio.serie[i] != territorio.serie[i]],
            "cenarios": [do_cenario(territorio, cenario) for cenario in cenarios],
        })
    return {"versao": VERSION,
            # A fonte, como no Detector: os nomes da base, de onde ela vem e o que ela tem (perfil da base, seção A.3).
            "fonte": detector._fonte(base),
            "competencias": list(base.periodos), "ultimo_registro": base.periodos[-1],
            "janela": {"inicio": base.periodos[inicio], "fim": base.periodos[fim], "registros": fim - inicio + 1,
                       "anos": float((base.meses[fim] - base.meses[inicio]) / 12.0), "padrao": padrao},
            "horizonte": {"data": _data(horizonte), "anos_desde_o_ultimo_registro": (horizonte - ultimo) / 12.0},
            "metodos": [{"chave": chave, "rotulo": _nome_do_metodo(base, chave)} for chave in NOMES_DOS_METODOS],
            "faixa": {"em_10": em_10, "opcoes": sorted(FAIXAS_EM_10), "padrao": FAIXA_PADRAO},
            "territorios": saida, "retroprojecao": _retro_da_resposta(base, retro, em_10),
            "referencias": [{"id": ref["id"], "rotulo": ref["rotulo"], "tipo": ref["tipo"],
                             "territorio": None if ref["territorio"] is None else ref["territorio"].id,
                             "unidade": None if ref["territorio"] is None else ref["territorio"].unidade,
                             "estado": curvas[ref["id"]]["estado"], "descricao": curvas[ref["id"]].get("descricao"),
                             "motivo": curvas[ref["id"]].get("motivo")} for ref in referencias],
            "comparacao": {"metrica": metrica, "forma": forma,
                           "populacao_pct_ao_ano": (crescimento_pct or None) if metrica == "taxa" else None,
                           "hipotese_de_populacao": None if metrica != "taxa" else
                           ("constante: a população de " + detector.curta(base.periodos[-1]) + " em todas as datas simuladas")
                           if not crescimento_pct else
                           (("crescendo " if crescimento_pct > 0 else "diminuindo ") + _curto(abs(crescimento_pct)) + "% ao ano depois de " +
                            detector.curta(base.periodos[-1]) + " (hipótese sua), a mesma taxa em todos os territórios; até essa data, a "
                            "população de " + detector.curta(base.periodos[-1]))},
            "notas": _notas(base, {territorio.nivel for territorio in territorios}, bool(referencias),
                            any(cenario["planejamento"] for cenario in cenarios), em_10, crescimento_pct if metrica == "taxa" else 0.0),
            "limitacoes": ["CENARIO_HIPOTETICO", "PADRAO_ESCOLHIDO_PELA_BASE", "FAIXA_SO_DO_METODO_PADRAO"]}
