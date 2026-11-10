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
from dataclasses import dataclass

import numpy as np

import detector
import series_brasil
from series_brasil import Base, Territorio, mes_da_competencia
from territorial_levels import STATES

VERSION = "SIMULADOR-CENARIOS/V2.2/1"
# Os nomes dos métodos nos textos (decisão D-C: linguagem simples). No anexo, a "deriva do estado" do M0d é o crescimento anual
# composto da soma municipal da UF; na tela e nos textos de cenário, "o crescimento recente do estado".
METODOS = ("padrao", "M0", "M0d", "M1", "M2", "M3", "manual")
NOMES_DOS_METODOS = {
    "M0": "persistência (o último valor se mantém)",
    "M0d": "persistência com o crescimento recente do estado",
    "M1": "taxa composta da janela",
    "M2": "tendência linear robusta",
    "M3": "tendência log-linear",
    "manual": "taxa informada pela pessoa",
}
ANOS_DA_DERIVA = 3
ANOS_DA_JANELA_PADRAO = 3
HORIZONTES_DA_FAIXA = (1, 2, 3, 4)
# Faixas de porte das faixas de 80% (seção 11.2): pelo número de médicos na origem (N0 ≥ 1).
PORTES_DA_FAIXA = ((1, 9), (10, 19), (20, 49), (50, 99), (100, 299), (300, None))
ROTULOS_DOS_PORTES_DA_FAIXA = ("1 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 ou mais")
MINIMO_DE_CASOS_DA_FAIXA = 100
MAX_TERRITORIOS, MAX_CENARIOS, MAX_INTERVENCOES, MAX_EVENTOS = 100, 6, 12, 240
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
@dataclass(frozen=True)
class Retroprojecao:
    """A retroprojeção da versão da base: as faixas de 80% do M0d por porte e horizonte e o erro de cada método frente ao M0."""
    versao: str
    origens: tuple
    faixas: dict      # (porte, anos) → {"inferior", "superior", "casos", "origens", "cobertura"}
    tabela: tuple     # linhas {"metodo", "porte", "anos", "casos", "origens", "erro_absoluto_medio", "vies", "frente_ao_m0"}


_RETROS: dict[str, Retroprojecao] = {}
_LOCK = threading.Lock()


def _porte_da_faixa(valor) -> int | None:
    if valor is None or valor != valor or valor < 1:
        return None
    for indice, (minimo, maximo) in enumerate(PORTES_DA_FAIXA):
        if valor >= minimo and (maximo is None or valor <= maximo):
            return indice
    return None


def _somas_das_ufs(base: Base) -> dict:
    return {prefixo: base.soma_municipal_do_estado(prefixo) for prefixo in base.do_estado}


def _deriva_das_linhas(base: Base, cal: detector.Calibracao, somas: dict, origem: int) -> np.ndarray:
    """A deriva anual de cada município numa origem: o crescimento composto da soma municipal da UF nos 3 anos anteriores, no
    mesmo mês. NaN sem os 3 anos, com soma zero ou com quebra de fonte na janela da deriva (aí o método volta ao M0)."""
    saida = np.full(len(base.codigos), np.nan)
    antes = origem - 2 * ANOS_DA_DERIVA
    if antes < 0 or base.meses[origem] - base.meses[antes] != 12 * ANOS_DA_DERIVA:
        return saida
    for prefixo, linhas in base.do_estado.items():
        soma = somas[prefixo]
        if soma[antes] > 0 and soma[origem] > 0 and not cal.quebra[list(linhas), antes:origem + 1].any():
            saida[list(linhas)] = (soma[origem] / soma[antes]) ** (1.0 / ANOS_DA_DERIVA) - 1
    return saida


def retroprojetar(base: Base, guardar: bool = True) -> Retroprojecao:
    """Retroprojeções com origens móveis, sem observações futuras: em cada junho com 3 anos de história, cada método é ajustado só
    com os registros até a origem e confrontado com o que foi observado 1, 2, 3 e 4 anos depois. O M0 é sempre a referência."""
    with _LOCK:
        guardada = _RETROS.get(base.versao) if guardar else None
    if guardada is not None:
        return guardada
    cal = detector.calibrar(base, guardar=guardar)
    q = base.quantidade
    n, total = q.shape
    somas = _somas_das_ufs(base)
    porte = np.full(q.shape, -1, dtype=np.int8)
    with np.errstate(invalid="ignore"):
        for indice, (minimo, maximo) in enumerate(PORTES_DA_FAIXA):
            porte[(q >= minimo) & ((q <= maximo) if maximo is not None else True)] = indice
    origens = [i for i in range(total) if base.periodos[i].endswith("06") and i - 2 * ANOS_DA_DERIVA >= 0
               and base.meses[i] - base.meses[i - 2 * ANOS_DA_DERIVA] == 12 * ANOS_DA_DERIVA and i + 2 <= total - 1]
    razoes: dict = {}   # (porte, anos) → [(origem, array das razões observado ÷ projetado − 1 do M0d)]
    erros: dict = {}    # (metodo, porte, anos) → [soma |erro|, soma erro, casos, soma |erro do M0| nos mesmos casos, origens]
    for origem in origens:
        janela = list(range(origem - 2 * ANOS_DA_DERIVA, origem + 1))
        t = (base.meses[janela] - base.meses[origem]) / 12.0
        y = q[:, janela]
        n0 = q[:, origem]
        inteira = ~np.isnan(y).any(axis=1) & ~(cal.pico_conhecido[:, janela] <= origem).any(axis=1) & ~cal.quebra[:, janela].any(axis=1)
        deriva = _deriva_das_linhas(base, cal, somas, origem)
        y_limpo = np.where(inteira[:, None], y, 1.0)
        with np.errstate(invalid="ignore", divide="ignore"):
            taxa = np.where(inteira & (y[:, 0] > 0) & (n0 > 0), (n0 / y[:, 0]) ** (1.0 / ANOS_DA_DERIVA) - 1, np.nan)
        a2, b2 = theil_sen(t, y_limpo)
        a3, b3, _, ok3 = poisson(t, y_limpo)
        for anos in HORIZONTES_DA_FAIXA:
            alvo = origem + 2 * anos
            if alvo > total - 1 or base.meses[alvo] - base.meses[origem] != 12 * anos:
                continue
            observado = q[:, alvo]
            valido = inteira & (n0 >= 1) & ~np.isnan(observado) & ~cal.pico[:, alvo] & ~cal.quebra[:, alvo]
            with np.errstate(invalid="ignore", over="ignore"):
                projecoes = {
                    "M0": np.where(valido, n0, np.nan),
                    "M0d": np.where(valido & np.isfinite(deriva), n0 * (1 + deriva) ** anos, np.nan),
                    "M1": np.where(valido & np.isfinite(taxa), n0 * (1 + taxa) ** anos, np.nan),
                    "M2": np.where(valido, np.maximum(0.0, a2 + b2 * anos), np.nan),
                    "M3": np.where(valido & ok3, np.exp(np.clip(a3 + b3 * anos, -30, 30)), np.nan),
                }
            for faixa in range(len(PORTES_DA_FAIXA)):
                da_faixa = porte[:, origem] == faixa
                com_m0d = da_faixa & np.isfinite(projecoes["M0d"]) & (projecoes["M0d"] > 0)
                if com_m0d.any():
                    razoes.setdefault((faixa, anos), []).append((origem, observado[com_m0d] / projecoes["M0d"][com_m0d] - 1))
                for metodo, projecao in projecoes.items():
                    casos = da_faixa & np.isfinite(projecao)
                    if not casos.any():
                        continue
                    erro = observado[casos] - projecao[casos]
                    soma = erros.setdefault((metodo, faixa, anos), [0.0, 0.0, 0, 0.0, 0])
                    soma[0] += float(np.abs(erro).sum())
                    soma[1] += float(erro.sum())
                    soma[2] += int(casos.sum())
                    soma[3] += float(np.abs(observado[casos] - n0[casos]).sum())
                    soma[4] += 1
    faixas = {}
    for (faixa, anos), partes in razoes.items():
        todas = np.concatenate([valores for _, valores in partes])
        if todas.size < MINIMO_DE_CASOS_DA_FAIXA:
            continue
        # Cobertura fora da amostra: a faixa calculada sem uma origem, conferida nela.
        dentro, conferidos = 0, 0
        if len(partes) >= 2:
            for k, (_, valores) in enumerate(partes):
                outras = np.concatenate([v for m, (_, v) in enumerate(partes) if m != k])
                inferior, superior = np.percentile(outras, [10, 90])
                dentro += int(((valores >= inferior) & (valores <= superior)).sum())
                conferidos += valores.size
        inferior, superior = np.percentile(todas, [10, 90])
        faixas[(faixa, anos)] = {"inferior": float(inferior), "superior": float(superior), "casos": int(todas.size),
                                 "origens": len(partes), "cobertura": (dentro / conferidos) if conferidos else None}
    tabela = tuple({"metodo": metodo, "porte": faixa, "anos": anos, "casos": soma[2], "origens": soma[4],
                    "erro_absoluto_medio": soma[0] / soma[2], "vies": soma[1] / soma[2],
                    "frente_ao_m0": (soma[0] / soma[3]) if soma[3] > 0 else None}
                   for (metodo, faixa, anos), soma in sorted(erros.items()) if soma[2])
    retro = Retroprojecao(versao=base.versao, origens=tuple(base.periodos[i] for i in origens), faixas=faixas, tabela=tabela)
    if guardar:
        with _LOCK:
            _RETROS.clear()
            _RETROS[base.versao] = retro
    return retro


# --------------------------------------------------------------------------------------------- pedido
def _competencia_futura(texto, nome: str) -> int:
    """Uma data AAAAMM (qualquer mês) como posição em meses; recusa o que não é data."""
    if not isinstance(texto, str) or len(texto) != 6 or not texto.isdigit() or not 1 <= int(texto[4:]) <= 12 or int(texto[:4]) > ANO_LIMITE:
        raise ValueError(nome + " inválida: use ano e mês (AAAAMM), até " + str(ANO_LIMITE) + ".")
    return mes_da_competencia(texto)


def _data(mes: int) -> str:
    return str(mes // 12) + str(mes % 12 + 1).zfill(2)


def _janela(base: Base, bruto, padrao_ate: int | None = None) -> tuple[int, int, bool]:
    """A janela histórica: início e fim entre as competências reais. Sem pedido, os 3 anos até o último registro (7 registros)."""
    fim_padrao = len(base.periodos) - 1 if padrao_ate is None else padrao_ate
    if bruto in (None, {}):
        return max(0, fim_padrao - 2 * ANOS_DA_JANELA_PADRAO), fim_padrao, True
    if not isinstance(bruto, dict):
        raise ValueError("Janela inválida: envie inicio e fim, com competências da base.")
    fim = base.posicao(bruto["fim"]) if bruto.get("fim") else fim_padrao
    inicio = base.posicao(bruto["inicio"]) if bruto.get("inicio") else max(0, fim - 2 * ANOS_DA_JANELA_PADRAO)
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
            raise ValueError("Intervenção inválida: a quantidade de médicos é um número acima de zero.")
        em = _competencia_futura(bruta.get("em"), "Data da intervenção")
        ate = _competencia_futura(bruta["ate"], "Data final da intervenção") if bruta.get("ate") else em
        passo = bruta.get("a_cada_meses", 12)
        if isinstance(passo, bool) or not isinstance(passo, int) or not 1 <= passo <= 120:
            raise ValueError("Intervenção inválida: o intervalo entre os eventos é um número inteiro de meses, de 1 a 120.")
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
            raise ValueError("Método desconhecido: " + str(metodo) + ". Use padrao, M0, M0d, M1, M2, M3 ou manual.")
        taxa = bruto.get("taxa_manual_pct")
        if metodo == "manual":
            if isinstance(taxa, bool) or not isinstance(taxa, (int, float)) or not -99 <= taxa <= 500:
                raise ValueError("Taxa manual inválida: informe a taxa anual, em %, de −99 a 500. O sistema não sugere uma taxa.")
        elif taxa is not None:
            raise ValueError("A taxa manual só vale com o método manual.")
        saida.append({"id": chave, "nome": str(bruto.get("nome") or "Cenário " + str(posicao + 1))[:80], "metodo": metodo,
                      "taxa": None if taxa is None else float(taxa), "janela": bruto.get("janela"),
                      "intervencoes": _intervencoes(bruto.get("intervencoes"), ids)})
    return saida


# --------------------------------------------------------------------------------------------- um território, um cenário
def _inteiro_da_tela(valor: float) -> int:
    """O número de médicos de um texto de cenário: o inteiro mais próximo (meio para cima). A precisão integral fica na resposta."""
    return int(math.floor(valor + 0.5))


def _br(valor, casas: int = 1) -> str:
    if float(valor).is_integer():
        return f"{int(valor):,}".replace(",", ".")
    return f"{valor:,.{casas}f}".replace(",", "_").replace(".", ",").replace("_", ".")


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
    junhos = [i for i in indices if base.periodos[i].endswith("06")]
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


def _deriva(base: Base, cal: detector.Calibracao, prefixo: str, origem: int) -> tuple[float | None, str | None]:
    """A deriva do estado numa origem e, quando não há, o motivo."""
    antes = origem - 2 * ANOS_DA_DERIVA
    if antes < 0 or base.meses[origem] - base.meses[antes] != 12 * ANOS_DA_DERIVA:
        return None, "não há registros do estado 3 anos antes do último registro usado"
    linhas = list(base.do_estado.get(prefixo, ()))
    if cal.quebra[linhas, antes:origem + 1].any():
        return None, "há quebra de fonte nos 3 anos usados para medir o crescimento do estado"
    soma = base.soma_municipal_do_estado(prefixo)
    if not soma[antes] > 0 or not soma[origem] > 0:
        return None, "a soma municipal do estado é zero nesses 3 anos"
    return float((soma[origem] / soma[antes]) ** (1.0 / ANOS_DA_DERIVA) - 1), None


def _base_do_cenario(base: Base, cal: detector.Calibracao, territorio: Territorio, metodo: str, taxa_manual, inicio: int, fim: int):
    """A trajetória-base B(t) de um território num método: devolve o método usado, os parâmetros, os avisos e a função B(anos
    desde a origem), ou o motivo de não haver. `metodo` "padrao" vale o padrão do nível."""
    indices, avisos = _usaveis(base, cal, territorio, inicio, fim)
    if not indices:
        return {"estado": "nao_calculavel", "motivo": "Não há registro usável na janela escolhida (ausência de dado não é zero)."}
    origem = indices[-1]
    serie = territorio.serie
    n0 = float(serie[origem])
    t = (base.meses[indices] - base.meses[origem]) / 12.0
    y = np.array([float(serie[i]) for i in indices])
    pedido = metodo
    provisorio = False
    if metodo == "padrao":
        provisorio = True
        metodo = "M0d" if territorio.nivel == "municipios" else "M1"
        if territorio.nivel != "municipios":
            # Estados como unidade (e conjuntos de estados): M1 de 3 anos na série do próprio nível, com aviso (seção 8.8).
            inicio = max(0, origem - 2 * ANOS_DA_JANELA_PADRAO)
            indices = [i for i in indices if i >= inicio]
            t = (base.meses[indices] - base.meses[origem]) / 12.0
            y = np.array([float(serie[i]) for i in indices])
            avisos.append({"codigo": "PADRAO_PROVISORIO_DO_NIVEL", "texto": "Para estados como unidade, o método padrão é provisório: "
                           "o crescimento médio dos 3 anos até o último registro usado, na contagem do próprio estado. Ele só foi "
                           "conferido num período de crescimento forte."})
    parametros = {"n0": n0, "origem": base.periodos[origem], "janela": {"inicio": base.periodos[indices[0]], "fim": base.periodos[origem],
                                                                          "registros": len(indices)}}
    janela_do_metodo = float((base.meses[origem] - base.meses[indices[0]]) / 12.0)
    if metodo == "M0d" and territorio.nivel != "municipios":
        return {"estado": "nao_aplicavel", "motivo": "A persistência com o crescimento recente do estado vale para municípios e conjuntos de municípios; "
                "para estados como unidade, o padrão provisório é a taxa composta de 3 anos (M1)."}

    def conjunto_de_municipios():
        return territorio.tipo == "conjunto" and territorio.nivel == "municipios"

    if metodo in ("M0", "M0d") and conjunto_de_municipios():
        # A soma das projeções dos membros, cada um com a deriva da sua UF.
        partes, sem_deriva = [], []
        for membro in territorio.membros:
            codigo = membro[5:]
            linha = base.indice[codigo]
            valor = float(base.quantidade[linha, origem])
            deriva, motivo = (_deriva(base, cal, base.prefixos[linha], origem) if metodo == "M0d" else (0.0, None))
            if deriva is None:
                sem_deriva.append(base.nomes[linha])
                deriva = 0.0
            partes.append((valor, deriva))
        if sem_deriva:
            avisos.append({"codigo": "DERIVA_INDISPONIVEL", "texto": "Sem o crescimento recente do estado para " + ", ".join(sem_deriva[:5]) +
                           ": nesses membros, vale a persistência (o último valor)."})
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
            avisos.append({"codigo": "VOLTA_AO_M0", "texto": "Sem o crescimento recente do estado (" + motivo + "): o cenário usa a persistência (o "
                           "último valor se mantém)."})
            return {"estado": "calculado", "pedido": pedido, "usado": "M0", "provisorio": provisorio, "parametros": parametros,
                    "avisos": avisos, "funcao": lambda anos: n0, "origem": origem, "indices": indices,
                    "janela_do_metodo": float(ANOS_DA_DERIVA), "voltou_ao_m0": True}
        parametros["deriva_pct"] = 100.0 * deriva
        parametros["estado_da_deriva"] = STATES[territorio.uf][1]
        if n0 == 0:
            avisos.append({"codigo": "ZERO_CONTINUA_ZERO", "texto": "O território está em zero: sem uma intervenção, continua em zero "
                           "(o crescimento do estado multiplica o último valor)."})
        return {"estado": "calculado", "pedido": pedido, "usado": "M0d", "provisorio": provisorio, "parametros": parametros, "avisos": avisos,
                "funcao": lambda anos: n0 * (1 + deriva) ** anos, "origem": origem, "indices": indices,
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
            return {"estado": "nao_aplicavel", "motivo": "A taxa composta exige dois registros na janela, com o primeiro e o último acima "
                    "de zero (com início em zero, a taxa não é definida)."}
        taxa = float((y[-1] / y[0]) ** (1.0 / janela_do_metodo) - 1)
        parametros.update({"taxa_pct": 100.0 * taxa, "acumulado_pct": float(100.0 * (y[-1] / y[0] - 1)), "anos": janela_do_metodo})
        if n0 < 100 and territorio.tipo == "municipio":
            avisos.append({"codigo": "M1_ABAIXO_DE_100", "texto": "Abaixo de 100 médicos, este método errou mais do que simplesmente "
                           "manter o último valor, quando conferido com o passado da base."})
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


def _aviso_do_horizonte(anos: float, janela: float) -> dict:
    """Os avisos H/W (seção 7.3): informativos, sem garantia estatística."""
    razao = anos / janela if janela > 0 else math.inf
    tempos = " (" + _tempo(anos) + " à frente, com " + _tempo(janela) + " de história usados no cálculo)."
    if razao <= 0.5:
        return {"nivel": "normal", "texto": "A data final fica a até metade do tempo de história usado no cálculo" + tempos}
    if razao <= 1:
        return {"nivel": "cautela", "texto": "Cautela: a data final fica a mais da metade do tempo de história usado no cálculo" + tempos}
    if razao <= 2:
        return {"nivel": "extrapolacao", "texto": "Extrapolação além da janela: a data final fica mais longe do que o tempo de história "
                "usado no cálculo" + tempos}
    return {"nivel": "extrapolacao_extrema", "texto": "Extrapolação extrema: a data final fica a mais do dobro do tempo de história usado "
            "no cálculo" + tempos}


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


def _premissas(resultado: dict, cenario: dict, territorio: Territorio) -> str:
    """As premissas do texto de cenário: a janela, o parâmetro do método e as intervenções, por extenso."""
    p = resultado["parametros"]
    partes = ["janela de " + detector.curta(p["janela"]["inicio"]) + " a " + detector.curta(p["janela"]["fim"])]
    if resultado["usado"] == "M0d":
        partes.append(("crescimento do estado de " + _pct(p["deriva_pct"], 2) + " ao ano (" + p["estado_da_deriva"] + ")") if "deriva_pct" in p
                      else "o crescimento recente do estado de cada membro")
    elif resultado["usado"] in ("M1", "M3", "manual"):
        partes.append("taxa de " + _pct(p["taxa_pct"], 2) + " ao ano" + (" informada pela pessoa" if resultado["usado"] == "manual" else ""))
    elif resultado["usado"] == "M2":
        partes.append("variação de " + ("+" if p["inclinacao_por_ano"] >= 0 else "−") + _br(abs(p["inclinacao_por_ano"]), 2) + " médicos por ano")
    aplicaveis = [item for item in cenario["intervencoes"] if item["territorios"] is None or territorio.id in item["territorios"]]
    if not aplicaveis:
        partes.append("sem intervenção")
    for item in aplicaveis:
        verbo = "acréscimo" if item["tipo"] == "acrescimo" else "retirada"
        quando = ("em " + detector.curta(_data(item["em"]))) if not item["periodica"] else \
            ("a cada " + str(item["a_cada_meses"]) + " meses, de " + detector.curta(_data(item["em"])) + " a " + detector.curta(_data(item["ate"])))
        permanencia = "com permanência total" if item["permanencia"] >= 100 else "com permanência de " + _br(item["permanencia"], 1) + "% ao ano"
        partes.append(verbo + " de " + _br(item["quantidade"], 1) + (" médico " if item["quantidade"] == 1 else " médicos ") + quando + ", " +
                      permanencia + " (hipótese)")
    return "; ".join(partes)


def _simular(base: Base, cal: detector.Calibracao, retro: Retroprojecao, territorio: Territorio, cenario: dict, inicio: int, fim: int,
             horizonte: int) -> dict:
    """Um território num cenário: a base B(t), as intervenções I(t), o total, a faixa (quando sustentada), os avisos e o texto."""
    if cenario["janela"] not in (None, {}):
        inicio, fim, _ = _janela(base, cenario["janela"])
    resultado = _base_do_cenario(base, cal, territorio, cenario["metodo"], cenario["taxa"], inicio, fim)
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
    metodo = {"pedido": resultado["pedido"], "usado": usado, "rotulo": NOMES_DOS_METODOS[usado],
              "padrao": resultado["pedido"] == "padrao", "provisorio": bool(resultado["provisorio"]),
              "voltou_ao_m0": bool(resultado.get("voltou_ao_m0")), "soma": resultado.get("rotulo_da_soma")}
    avisos = list(resultado["avisos"])
    # As datas de exibição: os registros reais entre a origem e o último registro (retroprojeção rotulada), janeiro e junho até o
    # horizonte, as datas das intervenções e a data final.
    ultimo = int(base.meses[-1])
    marcas = {int(base.meses[i]) for i in range(origem + 1, len(base.periodos))}
    ano = mes_da_origem // 12
    while ano * 12 <= horizonte:
        marcas.update(m for m in (ano * 12, ano * 12 + 5) if mes_da_origem < m <= horizonte)
        ano += 1
    for item in cenario["intervencoes"]:
        if item["territorios"] is None or territorio.id in item["territorios"]:
            marcas.update(data for data in item["datas"] if mes_da_origem < data <= horizonte)
    marcas.add(horizonte)
    marcas = sorted(m for m in marcas if m <= horizonte)
    # A faixa de 80%: só o M0d municipal (e, como aproximação, o conjunto de municípios), com N0 ≥ 1, de 1 a 4 anos.
    n0 = resultado["parametros"]["n0"]
    porte = _porte_da_faixa(n0)
    faixa = {"estado": "indisponivel", "motivo": None, "rotulo": None}
    if usado != "M0d":
        faixa["motivo"] = "A faixa de 80% só existe para o método padrão dos municípios (a persistência com o crescimento recente do estado)."
    elif territorio.nivel != "municipios":
        faixa["motivo"] = "Não há faixa para estados como unidade."
    elif porte is None:
        faixa["motivo"] = "Com zero médicos na origem, não há faixa."
    elif not any((porte, anos) in retro.faixas for anos in HORIZONTES_DA_FAIXA):
        faixa["motivo"] = "A base não tem retroprojeções bastantes para a faixa deste porte."
    else:
        faixa = {"estado": "disponivel", "motivo": None, "porte": ROTULOS_DOS_PORTES_DA_FAIXA[porte],
                 "rotulo": ("aproximação: a margem dos municípios com o porte da soma" if territorio.tipo == "conjunto"
                            else "a margem observada no passado da base, em municípios do mesmo porte") + "; acompanha a intervenção"}
    trajetoria, negativo, truncado = [], None, False
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
        if mes <= ultimo:
            observado = territorio.serie[base.periodos.index(_data(mes))]
            ponto["observado"] = None if observado != observado else float(observado)
        if faixa["estado"] == "disponivel":
            inteiro = max(1, math.ceil(anos - 1e-9))  # a data intermediária usa a faixa do ano inteiro seguinte
            limites = retro.faixas.get((porte, inteiro))
            if inteiro <= max(HORIZONTES_DA_FAIXA) and limites:
                ponto["faixa"] = {"inferior": max(0.0, b * (1 + limites["inferior"]) + efeito),
                                  "superior": max(0.0, b * (1 + limites["superior"]) + efeito), "anos": inteiro,
                                  "validada": inteiro <= 2}
        trajetoria.append(ponto)
    if negativo is not None:
        # Retirada acima do estoque: o cenário é devolvido para revisão; o zero matemático não esconde a intervenção impossível.
        return {**cabecalho, "metodo": metodo, "estado": "retirada_acima_do_estoque",
                "motivo": "Em " + detector.curta(_data(negativo[0])) + ", as retiradas passam do número de médicos do cenário em " +
                          _br(-negativo[1], 1) + ": reveja a quantidade ou a data. Nenhum estoque negativo é aceito.",
                "parametros": resultado["parametros"], "avisos": avisos}
    if truncado:
        avisos.append({"codigo": "BASE_TRUNCADA_EM_ZERO", "texto": "A tendência da janela levaria a um número negativo: a base do cenário "
                       "para em zero (um número negativo de médicos não é um estoque válido)."})
    anos_do_horizonte = (horizonte - mes_da_origem) / 12.0
    hw = _aviso_do_horizonte(anos_do_horizonte, resultado["janela_do_metodo"])
    if hw["nivel"] != "normal":
        avisos.append({"codigo": "HORIZONTE_" + hw["nivel"].upper(), "texto": hw["texto"]})
    if faixa["estado"] == "disponivel" and anos_do_horizonte > max(HORIZONTES_DA_FAIXA) + 1e-9:
        avisos.append({"codigo": "FAIXA_ATE_4_ANOS", "texto": "A faixa de 80% vai só até 4 anos depois da origem; além disso, é "
                       "indisponível (sem extrapolar)."})
    if mes_da_origem < ultimo:
        avisos.append({"codigo": "RETROPROJECAO", "texto": "A origem (" + detector.curta(base.periodos[origem]) + ") é anterior ao último "
                       "registro (" + detector.curta(base.periodos[-1]) + "): até lá, o cenário é calculado sobre datas que já têm registro e "
                       "aparece ao lado do observado."})
    final = trajetoria[-1]
    quem = territorio.rotulo + (" (soma das projeções dos membros)" if metodo["soma"] else
                                " (soma das contagens dos componentes)" if territorio.tipo == "conjunto" else "")
    texto = (PREVISAO_NAO + ": com o método " + NOMES_DOS_METODOS[usado] + " e as premissas " +
             _premissas(resultado, cenario, territorio) + ", " + quem + " teria " + _br(_inteiro_da_tela(final["total"])) +
             (" médico em " if _inteiro_da_tela(final["total"]) == 1 else " médicos em ") + detector.curta(final["data"]) +
             ". Base: registros até " + detector.curta(base.periodos[origem]) + ".")
    return {**cabecalho, "metodo": metodo, "estado": "calculado", "parametros": resultado["parametros"], "avisos": avisos,
            "horizonte": {"anos": anos_do_horizonte, "aviso": hw["nivel"]}, "faixa": faixa, "trajetoria": trajetoria,
            "final": {"data": final["data"], "base": final["base"], "intervencao": final["intervencao"], "total": final["total"],
                      "faixa": final["faixa"]},
            "texto": texto}


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


def _retro_da_resposta(retro: Retroprojecao) -> dict:
    return {"origens": list(retro.origens),
            "faixas": [{"porte": ROTULOS_DOS_PORTES_DA_FAIXA[porte], "anos": anos, "inferior_pct": 100.0 * f["inferior"],
                        "superior_pct": 100.0 * f["superior"], "casos": f["casos"], "origens": f["origens"],
                        "cobertura_pct": None if f["cobertura"] is None else 100.0 * f["cobertura"],
                        "rotulo": "conferida com dados à parte" if anos <= 2 else "limite provisório, sem conferência à parte"}
                       for (porte, anos), f in sorted(retro.faixas.items())],
            "tabela": [{**linha, "porte": ROTULOS_DOS_PORTES_DA_FAIXA[linha["porte"]]} for linha in retro.tabela]}


def _notas(base: Base, niveis: set) -> list[str]:
    notas = ["Cenários hipotéticos e condicionais: não são previsão, observação atual, conclusão sobre o atendimento nem recomendação "
             "de provimento.",
             "O registro mais recente da base é " + detector.curta(base.periodos[-1]) + ": o que vem depois dele no gráfico é simulado, "
             "nunca observado. A base só tem médicos, com registros de janeiro e junho (5 e 7 meses entre um e outro).",
             "A base do cenário e a intervenção ficam separadas: N(t) = máx(0, B(t) + I(t)). O crescimento histórico não é aplicado aos "
             "médicos acrescentados; a permanência total dos acréscimos é uma hipótese.",
             "Comparar métodos e janelas mostra a sensibilidade ao método e à janela, não uma faixa de confiança. A faixa de 80% só "
             "existe para o método padrão dos municípios, de 1 a 4 anos; fora disso, é indisponível.",
             "A média aritmética das taxas é só descrição do passado; o percentual médio que reproduz o crescimento ocorrido é a taxa "
             "composta (M1)."]
    if niveis - {"municipios"}:
        notas.append("Estados como unidade usam a contagem estadual de médicos únicos, com um padrão provisório (a taxa composta de 3 "
                     "anos). Num conjunto, o valor é a soma dos componentes, não o número de médicos diferentes.")
    return notas


def compute(sources, opcoes: dict) -> dict:
    """POST /api/simulador: os cenários de cada território da seleção local. Só calcula: nada é registrado na sessão, e nada vai ao
    provedor de IA."""
    if not isinstance(opcoes, dict):
        raise ValueError("Pedido do Simulador inválido.")
    desconhecidas = set(opcoes) - {"base", "estados_unidade", "conjuntos", "janela", "horizonte", "cenarios"}
    if desconhecidas:
        raise ValueError("Opção desconhecida no pedido do Simulador: " + ", ".join(sorted(desconhecidas)) + ".")
    base = series_brasil.base_de(sources)
    cal = detector.calibrar(base)
    retro = retroprojetar(base)
    territorios = series_brasil.selecao(base, opcoes)
    if len(territorios) > MAX_TERRITORIOS:
        raise ValueError("O Simulador compara até " + str(MAX_TERRITORIOS) + " territórios de cada vez (a seleção tem " +
                         str(len(territorios)) + "): reduza a seleção local do Simulador.")
    inicio, fim, padrao = _janela(base, opcoes.get("janela"))
    ultimo = int(base.meses[-1])
    horizonte = _competencia_futura(opcoes["horizonte"], "Data final") if opcoes.get("horizonte") else ultimo + 24
    if horizonte <= int(base.meses[fim]):
        raise ValueError("A data final precisa ser depois do fim da janela (" + detector.curta(base.periodos[fim]) + ").")
    cenarios = _cenarios(opcoes.get("cenarios"), base, {territorio.id for territorio in territorios})
    saida = []
    for territorio in territorios:
        indices, _ = _usaveis(base, cal, territorio, inicio, fim)
        saida.append({
            "id": territorio.id, "tipo": territorio.tipo, "nivel": territorio.nivel, "rotulo": territorio.rotulo,
            "uf": STATES[territorio.uf][0] if territorio.uf else None, "unidade": territorio.unidade,
            **({"membros": list(territorio.membros), "nomes_dos_membros": list(territorio.nomes_dos_membros), "versao": territorio.versao}
               if territorio.tipo == "conjunto" else {}),
            "observado": _observado(base, cal, territorio),
            "historico": _estatisticas(base, territorio.serie, indices),
            "lacunas": [base.periodos[i] for i in range(inicio, fim + 1) if territorio.serie[i] != territorio.serie[i]],
            "cenarios": [_simular(base, cal, retro, territorio, cenario, inicio, fim, horizonte) for cenario in cenarios],
        })
    return {"versao": VERSION,
            "fonte": {"base": "Brasil", "categoria": "MEDICINA", "versao": base.versao, "primeira": base.periodos[0],
                      "ultima": base.periodos[-1], "competencias": len(base.periodos)},
            "competencias": list(base.periodos), "ultimo_registro": base.periodos[-1],
            "janela": {"inicio": base.periodos[inicio], "fim": base.periodos[fim], "registros": fim - inicio + 1,
                       "anos": float((base.meses[fim] - base.meses[inicio]) / 12.0), "padrao": padrao},
            "horizonte": {"data": _data(horizonte), "anos_desde_o_ultimo_registro": (horizonte - ultimo) / 12.0},
            "metodos": [{"chave": chave, "rotulo": rotulo} for chave, rotulo in NOMES_DOS_METODOS.items()],
            "territorios": saida, "retroprojecao": _retro_da_resposta(retro),
            "notas": _notas(base, {territorio.nivel for territorio in territorios}),
            "limitacoes": ["CENARIO_HIPOTETICO", "PADRAO_PROVISORIO", "FAIXA_SO_DO_METODO_PADRAO"]}
