"""Estudo de calibração do Detector de Sinais Territoriais com a base versionada (somente leitura), fora do produto e do CI.

Uso, da raiz do repositório:
    python scripts/calibrar_detector.py [--repeticoes 5] [--semente 20261110]

O que faz (Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 4.2 e 6; os resultados ficam em Docs/DETECTOR_DE_SINAIS.md):

1. lê a base Brasil pela mesma leitura verificada do serviço (integridade pelo manifesto) e monta a calibração do Detector;
2. mostra, por data, quantas transições municipais foram avaliadas, quantas ficaram na cauda de 1% e quantos alertas de perda
   abrupta (magnitude e excepcionalidade) saíram: é só monitoramento, porque em dado real a taxa fica perto da meta por
   construção;
3. mostra as células da última data (porte × intervalo), com o número de transições anteriores e a queda a partir da qual a
   variação é incomum;
4. mede o falso alerta e a perda não detectada no **modelo nulo sintético** da seção 4.2: séries N(t+1) = N(t)·(1 + g) + ε, com
   Var(ε) = φ·N^θ, arredondadas para inteiros não negativos, sem nenhuma queda real; depois, com quedas de 20%, 30% e 50%
   injetadas no último registro. g e φ vêm da própria base (por tipo de intervalo, 5 ou 7 meses); θ = 1,35.

5. mostra a **fotografia dos fenômenos 8 a 11** (etapa 5 do comando V22; seção 4.1 do anexo, itens 8 a 11): nas datas em que a
   janela de comparação de 2 anos cabe num trecho com população comparável (junho de 2016, 2017, 2020 e 2021), quantos municípios
   têm cada sinal observado (a queda da taxa por habitante, a queda de posição e a ampliação da defasagem ante a referência),
   quantos ficam só descritivos (menos de 20 médicos no início da janela) e, em cada junho, o critério e as distâncias do
   contexto geográfico. Os limites desses indicadores são provisórios e não têm validação: a fotografia mostra a sensibilidade
   deles, não uma taxa de acerto. `--so-comparativos` imprime só esta parte.

Nada é gravado: o estudo só imprime as tabelas (Markdown). Nenhum dado é alterado, e nada vai ao provedor de IA.
"""
import argparse
import dataclasses
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import comparativos  # noqa: E402
import detector  # noqa: E402
import series_brasil  # noqa: E402
from brazil_data import load_brazil_sources  # noqa: E402


class _Fontes:
    """As fontes da base, como o serviço as entrega (main.BrazilSources), sem subir o serviço."""

    def __init__(self):
        import main  # só para a leitura dos quadros; nenhuma rota é chamada
        self._fontes = main._brazil_sources("")
        self.version = self._fontes.version

    def frame(self, escopo):
        return self._fontes.frame(escopo)


def _alertas(base, cal, p):
    """As matrizes [município, data] dos alertas de perda abrupta, pela mesma regra de detector._perda (magnitude e
    excepcionalidade, sem as descontinuidades conhecidas na data)."""
    q = base.quantidade
    n, t = q.shape
    alta = np.zeros((n, t), dtype=bool)
    critica = np.zeros((n, t), dtype=bool)
    with np.errstate(invalid="ignore"):
        for j in range(1, t):
            anterior, queda = q[:, j - 1], q[:, j - 1] - q[:, j]
            conhecida = cal.marca_conhecida[:, j] <= j
            avaliada = np.isfinite(cal.p_perda[:, j]) & ~conhecida
            grande = queda >= np.maximum(p["alta_minimo"], np.ceil(p["alta_fracao"] / 100.0 * anterior))
            muito = queda >= np.maximum(p["critica_minimo"], np.ceil(p["critica_fracao"] / 100.0 * anterior))
            incomum = (cal.n_perda[:, j] >= p["alta_transicoes"]) & (cal.p_perda[:, j] <= p["alta_alfa"] / 100.0)
            muito_incomum = (cal.n_perda[:, j] >= p["critica_transicoes"]) & (cal.p_perda[:, j] <= p["critica_alfa"] / 100.0)
            critica[:, j] = avaliada & muito & muito_incomum
            alta[:, j] = avaliada & grande & incomum & ~critica[:, j]
    return alta, critica


def _linha(celulas):
    return "| " + " | ".join(str(c) for c in celulas) + " |"


def _pct(parte, total, casas=2):
    return "—" if not total else f"{100.0 * parte / total:.{casas}f}%".replace(".", ",")


def _fotografia_dos_comparativos(base, cal):
    """Os sinais observados dos fenômenos 8 a 10 em cada junho com comparação habilitada, e o contexto geográfico (11) em cada
    junho da base. Usa as mesmas funções do serviço (detector.avaliar, com os parâmetros padrão), município a município."""
    p = detector.PADRAO
    territorios = [series_brasil.municipio(base, codigo) for codigo in base.codigos]
    junhos = [i for i, periodo in enumerate(base.periodos) if periodo.endswith("06")]
    print("\n## Fenômenos 8 a 10: sinais observados nas datas com comparação habilitada (limites provisórios, sem validação)\n")
    print(_linha(["Data", "Janela", "Avaliados (20 médicos ou mais no início)", "Só descritivos (menos de 20)",
                  "8: queda da taxa forte", "8: muito forte", "9: queda de posição", "9: forte", "9: muito forte (confirmada)",
                  "10: defasagem forte", "10: muito forte", "Com sinais combinados (12)"]))
    print(_linha(["---"] * 12))
    for e in junhos:
        ini, fim, motivo = comparativos.janela(base, e)
        if motivo:
            continue
        contagem = {chave: {} for chave in ("disponibilidade", "posicao", "defasagem")}
        combinados = 0
        for territorio in territorios:
            av = detector.avaliar(base, cal, territorio, 0, e, p)
            for chave in contagem:
                rotulo = av[chave].get("sinal") or av[chave]["estado"]
                contagem[chave][rotulo] = contagem[chave].get(rotulo, 0) + 1
            combinados += "combinados" in av["sinais"]
        d, po, df = contagem["disponibilidade"], contagem["posicao"], contagem["defasagem"]
        avaliados = d.get("sem_sinal", 0) + d.get("forte", 0) + d.get("muito_forte", 0)
        print(_linha([base.periodos[e], base.periodos[ini] + " a " + base.periodos[fim], avaliados, d.get("descritivo", 0),
                      d.get("forte", 0), d.get("muito_forte", 0), po.get("queda", 0), po.get("forte", 0), po.get("muito_forte", 0),
                      df.get("forte", 0), df.get("muito_forte", 0), combinados]))
    print("\nPopulação comparável nesta base: " + comparativos.texto_dos_trechos(base) + ". Nos junhos em que a janela não cabe num "
          "trecho, \"comparação não habilitada\", com o nível da data à vista.")
    print("\n## Fenômeno 11: contexto geográfico em cada junho (critério: a taxa do Brasil na data)\n")
    print(_linha(["Data", "Taxa do Brasil (por 1.000)", "Municípios que atendem", "Municípios com distância", "Distância mediana (km)",
                  "Distância no percentil 90 (km)", "Maior distância (km)"]))
    print(_linha(["---"] * 7))
    for e in junhos:
        qd = comparativos.quadro(base, e, p, guardar=False)
        distancias = qd.distancia_km[~np.isnan(qd.distancia_km)]
        if qd.taxa_do_brasil is None or not distancias.size:
            print(_linha([base.periodos[e], "—", "—", "—", "—", "—", "—"]))
            continue
        print(_linha([base.periodos[e], f"{qd.taxa_do_brasil:.2f}".replace(".", ","), int(qd.atende.sum()), int(distancias.size),
                      f"{np.median(distancias):.1f}".replace(".", ","), f"{np.percentile(distancias, 90):.1f}".replace(".", ","),
                      f"{distancias.max():.1f}".replace(".", ",")]))


def main():
    argumentos = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    argumentos.add_argument("--repeticoes", type=int, default=5)
    argumentos.add_argument("--semente", type=int, default=20261110)
    argumentos.add_argument("--so-comparativos", action="store_true", help="imprime só a fotografia dos fenômenos 8 a 11")
    opcoes = argumentos.parse_args()

    fontes = _Fontes()
    base = series_brasil.base_de(fontes)
    cal = detector.calibrar(base, guardar=False)
    p = detector.PADRAO["perda"]
    q = base.quantidade
    n, t = q.shape
    print("Base Brasil, versão", base.versao[:12], "·", n, "municípios ·", t, "competências, de", base.periodos[0], "a", base.periodos[-1])
    print("Método:", detector.VERSION)
    if opcoes.so_comparativos:
        _fotografia_dos_comparativos(base, cal)
        return 0

    print("\n## Monitoramento por data (dado real)\n")
    print(_linha(["Data", "Intervalo (meses)", "Transições avaliadas", "Na cauda de 1%", "Taxa", "Alertas de intensidade alta",
                  "Alertas de intensidade crítica"]))
    print(_linha(["---"] * 7))
    alta, critica = _alertas(base, cal, p)
    for j in range(1, t):
        avaliadas = np.isfinite(cal.p_perda[:, j])
        cauda = avaliadas & (cal.p_perda[:, j] <= p["alta_alfa"] / 100.0) & (cal.n_perda[:, j] >= p["alta_transicoes"])
        print(_linha([base.periodos[j], int(cal.intervalo[j]), int(avaliadas.sum()), int(cauda.sum()),
                      _pct(cauda.sum(), avaliadas.sum()), int(alta[:, j].sum()), int(critica[:, j].sum())]))

    print("\n## Células da última data (" + base.periodos[-1] + ")\n")
    limiares = detector.limiares(base, cal, t - 1, detector.PADRAO)
    print(_linha(["Porte (médicos antes)", "Transições anteriores", "Queda incomum (1%) a partir de", "Queda muito incomum (0,1%) a partir de"]))
    print(_linha(["---"] * 4))
    for celula in limiares["perda"]:
        print(_linha([celula["porte"], celula["transicoes"],
                      "—" if celula["queda_incomum_pct"] is None else f"{celula['queda_incomum_pct']:.1f}%".replace(".", ","),
                      "—" if celula["queda_muito_incomum_pct"] is None else f"{celula['queda_muito_incomum_pct']:.1f}%".replace(".", ",")]))
    print("\nAfastamento de patamar (indicador 7), cauda de 1% por faixa de porte do patamar:\n")
    print(_linha(["Patamar (médicos)", "Avaliações anteriores", "Afastamento incomum a partir de"]))
    print(_linha(["---"] * 3))
    for faixa in limiares["patamar"]:
        print(_linha([faixa["porte"], faixa["observacoes"],
                      "—" if faixa["afastamento_incomum_pct"] is None else f"{faixa['afastamento_incomum_pct']:.1f}%".replace(".", ",")]))

    _fotografia_dos_comparativos(base, cal)

    # ------------------------------------------------------------------ modelo nulo sintético (seção 4.2)
    intervalo = cal.intervalo
    crescimento, phi = {}, {}
    soma = np.nansum(q, axis=0)
    for k, meses in enumerate(detector.INTERVALOS):
        taxas = [soma[j] / soma[j - 1] - 1 for j in range(1, t) if intervalo[j] == meses]
        crescimento[meses] = float(np.median(taxas))
        phi[meses] = float(cal.escala[t - 1, k]) ** 2
    print("\n## Modelo nulo sintético\n")
    print("Parâmetros estimados na base: crescimento por transição g =",
          ", ".join(f"{100 * crescimento[m]:.2f}% ({m} meses)".replace(".", ",") for m in detector.INTERVALOS) + "; φ =",
          ", ".join(f"{phi[m]:.4f} ({m} meses)".replace(".", ",") for m in detector.INTERVALOS) + "; θ =",
          str(detector.THETA).replace(".", ",") + ".", opcoes.repeticoes, "repetições, semente", opcoes.semente, "\n")
    inicial = np.array([next((v for v in linha if v == v), 0.0) for linha in q])
    portes = detector.ROTULOS_DOS_PORTES
    falsos = {"avaliadas": np.zeros(len(portes)), "alta": np.zeros(len(portes)), "critica": np.zeros(len(portes))}
    deteccao = {queda: {"total": np.zeros(len(portes)), "alta": np.zeros(len(portes)), "critica": np.zeros(len(portes))}
                for queda in (0.2, 0.3, 0.5)}
    for repeticao in range(opcoes.repeticoes):
        sorteio = np.random.default_rng(opcoes.semente + repeticao)
        sintetica = np.zeros((n, t))
        sintetica[:, 0] = inicial
        for j in range(1, t):
            meses = int(intervalo[j])
            anterior = sintetica[:, j - 1]
            ruido = sorteio.normal(0.0, 1.0, n) * np.sqrt(phi[meses] * np.power(anterior, detector.THETA))
            sintetica[:, j] = np.maximum(0, np.rint(anterior * (1 + crescimento[meses]) + ruido))
        nula = dataclasses.replace(base, versao="modelo-nulo-" + str(repeticao), quantidade=sintetica, estados={})
        cal_nula = detector.calibrar(nula, guardar=False)
        alta_nula, critica_nula = _alertas(nula, cal_nula, p)
        avaliadas = np.isfinite(cal_nula.p_perda) & (cal_nula.n_perda >= p["alta_transicoes"])
        for faixa in range(len(portes)):
            da_faixa = cal_nula.porte == faixa
            falsos["avaliadas"][faixa] += (avaliadas & da_faixa).sum()
            falsos["alta"][faixa] += (alta_nula & da_faixa).sum()
            falsos["critica"][faixa] += (critica_nula & da_faixa).sum()
        for queda in deteccao:
            injetada = sintetica.copy()
            injetada[:, t - 1] = np.rint(sintetica[:, t - 1] * (1 - queda))
            com_queda = dataclasses.replace(nula, versao="modelo-nulo-queda", quantidade=injetada)
            cal_queda = detector.calibrar(com_queda, guardar=False)
            alta_q, critica_q = _alertas(com_queda, cal_queda, p)
            for faixa in range(len(portes)):
                da_faixa = (cal_queda.porte[:, t - 1] == faixa) & np.isfinite(cal_queda.p_perda[:, t - 1])
                deteccao[queda]["total"][faixa] += da_faixa.sum()
                deteccao[queda]["alta"][faixa] += (alta_q[:, t - 1] & da_faixa).sum()
                deteccao[queda]["critica"][faixa] += (critica_q[:, t - 1] & da_faixa).sum()

    print("Falso alerta de perda abrupta (séries sem nenhuma queda real), por avaliação:\n")
    print(_linha(["Porte (médicos antes)", "Avaliações", "Alerta de intensidade alta", "Alerta de intensidade crítica", "Algum alerta"]))
    print(_linha(["---"] * 5))
    for faixa, rotulo in enumerate(portes):
        total = falsos["avaliadas"][faixa]
        print(_linha([rotulo, int(total), _pct(falsos["alta"][faixa], total), _pct(falsos["critica"][faixa], total, 3),
                      _pct(falsos["alta"][faixa] + falsos["critica"][faixa], total)]))
    total = falsos["avaliadas"].sum()
    print(_linha(["Todos", int(total), _pct(falsos["alta"].sum(), total), _pct(falsos["critica"].sum(), total, 3),
                  _pct(falsos["alta"].sum() + falsos["critica"].sum(), total)]))

    for queda in deteccao:
        print("\nQueda de " + str(int(queda * 100)) + "% injetada no último registro: detectada (algum alerta), crítica e não detectada:\n")
        print(_linha(["Porte (médicos antes)", "Séries", "Com alerta", "Com alerta de intensidade crítica", "Perda não detectada"]))
        print(_linha(["---"] * 5))
        for faixa, rotulo in enumerate(portes):
            total = deteccao[queda]["total"][faixa]
            com = deteccao[queda]["alta"][faixa] + deteccao[queda]["critica"][faixa]
            print(_linha([rotulo, int(total), _pct(com, total, 1), _pct(deteccao[queda]["critica"][faixa], total, 1),
                          _pct(total - com, total, 1)]))
        total = deteccao[queda]["total"].sum()
        com = deteccao[queda]["alta"].sum() + deteccao[queda]["critica"].sum()
        print(_linha(["Todos", int(total), _pct(com, total, 1), _pct(deteccao[queda]["critica"].sum(), total, 1),
                      _pct(total - com, total, 1)]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
