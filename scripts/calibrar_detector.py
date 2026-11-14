"""Estudo de calibração do Detector de Sinais Territoriais com a base versionada (somente leitura), fora do produto e do CI.

Uso, da raiz do repositório:
    python scripts/calibrar_detector.py [--so-regua] [--so-contexto]

O que faz (Docs/DETECTOR_E_SIMULADOR_V3.md, Partes A, B e F; os resultados ficam em Docs/DETECTOR_DE_SINAIS.md):

1. lê a base Brasil pela mesma leitura verificada do serviço (integridade pelo manifesto) e monta a régua do Detector, dos
   municípios e dos estados como unidade;
2. **a régua da queda recente (sinal 6), só pela raridade** (sem o tamanho mínimo): por nível e por faixa de porte, quantas
   mudanças puderam ser avaliadas e quantas ficaram no nível — a taxa de alertas, que deve ficar perto de 1 em 20, 1 em 100 e
   1 em 1.000. As descontinuidades de registro já conhecidas em cada data ficam fora do passado dela, como no produto;
3. **os alertas de cada sinal, em todas as datas** (com os critérios padrão completos): os sinais 1 a 10, por nível; e, em
   cada data, a **proporção de territórios com algum alerta** (a Parte F do anexo pede rever o padrão se passar de cerca de 20%);
4. **os limites que a raridade dá ao sinal 8** no último registro, por faixa de porte: a partir de que queda da taxa por
   habitante cada nível é raro;
5. **o contexto geográfico (sinal 11)** em cada registro anual: o critério e as distâncias.

`--so-regua` imprime só a parte 2 (segundos); `--so-contexto`, só a parte 5.

Nada é gravado: o estudo só imprime as tabelas (Markdown). Nenhum dado é alterado, e nada vai ao provedor de IA.
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import comparativos  # noqa: E402
import detector  # noqa: E402
import reguas  # noqa: E402
import series_brasil  # noqa: E402

SINAIS = ("estrutural", "declinio", "desaceleracao", "instabilidade", "perda", "patamar", "disponibilidade", "posicao", "defasagem")
NOMES = {"estrutural": "1–2 Poucos médicos ou nenhum", "declinio": "3 Declínio persistente", "desaceleracao": "4 Desaceleração",
         "instabilidade": "5 Instabilidade", "perda": "6 Queda recente", "patamar": "7 Abaixo do que já teve",
         "disponibilidade": "8 Menos médicos por habitante", "posicao": "9 Perda de posição", "defasagem": "10 Mais longe da referência"}
FORA_DA_AVALIACAO = ("ausencia_de_dado", "janela_insuficiente", "nao_calculavel", "descritivo", "sem_comparacoes",
                     "descontinuidade_de_registro", "comparacao_nao_habilitada", "referencia_invalida")


class _Fontes:
    """As fontes da base, como o serviço as entrega (main.BrazilSources), sem subir o serviço."""

    def __init__(self):
        import main  # só para a leitura dos quadros; nenhuma rota é chamada
        self._fontes = main._brazil_sources("")
        self.version = self._fontes.version

    def frame(self, escopo):
        return self._fontes.frame(escopo)


def _linha(celulas):
    return "| " + " | ".join(str(celula) for celula in celulas) + " |"


def _pct(parte, total, casas=2):
    return "–" if not total else f"{100 * parte / total:.{casas}f}%".replace(".", ",")


def _numero(valor):
    return f"{int(valor):,}".replace(",", ".")


def _regua_da_queda(nome, cal):
    """A taxa de alertas da régua, só pela raridade: por nível e por faixa de porte. Devolve a primeira data avaliada de cada
    nível (o índice da competência, ou None)."""
    c = reguas.Comparacoes(*(cal.c_perda[origem][cal.regular].astype(np.int64) for origem in range(6)), theta=np.empty(0))
    niveis, porte = reguas.niveis_em_vetor(c), cal.porte[cal.regular]
    tempo = np.nonzero(cal.regular)[1]
    print(f"\n## Régua da queda recente, só pela raridade: {nome} ({_numero(cal.regular.sum())} mudanças de um registro para o seguinte)\n")
    print(_linha(["Porte", "Moderado: avaliadas", "Moderado: taxa (meta 5%)", "Elevado: avaliadas", "Elevado: taxa (meta 1%)",
                  "Crítico: avaliadas", "Crítico: taxa (meta 0,1%)"]))
    print(_linha(["---"] * 7))

    def conta(nivel, minimo, faixa=None):
        n = np.where(c.n_porte >= minimo, c.n_porte, c.n_vizinhas)
        if nivel == 1:
            n = np.where(n >= minimo, n, c.n_todas)
        avaliadas = (n >= minimo) & (True if faixa is None else porte == faixa)
        return int(avaliadas.sum()), int((avaliadas & (niveis >= nivel)).sum()), avaliadas

    def celulas_de(faixa):
        celulas = []
        for nivel, minimo in ((1, 19), (2, 99), (3, 999)):
            avaliadas, atingidas, _ = conta(nivel, minimo, faixa)
            celulas += [_numero(avaliadas), _pct(atingidas, avaliadas) if avaliadas else "sem comparações suficientes"]
        return celulas
    for faixa, rotulo in enumerate(reguas.ROTULOS_DOS_PORTES):
        if (porte == faixa).any():
            print(_linha([rotulo] + celulas_de(faixa)))
    print(_linha(["**Todos**"] + celulas_de(None)))
    desde = []
    for nivel, minimo in ((1, 19), (2, 99), (3, 999)):
        datas = sorted(set(tempo[conta(nivel, minimo)[2]].tolist()))
        desde.append(None if not datas else datas[0])
    return desde


def _primeiras_datas(base, desde):
    return " · ".join(nome + " " + ("nunca" if data is None else "desde " + detector.curta(base.periodos[data]))
                      for nome, data in zip(("moderado", "elevado", "crítico"), desde))


def _alertas_por_sinal(base, cal, cal_dos_estados, p):
    """Em todas as datas, os níveis de cada sinal e o alerta de cada município; e os dos estados como unidade."""
    municipios = [series_brasil.municipio(base, codigo) for codigo in base.codigos]
    t = len(base.periodos)
    por_sinal = {chave: Counter() for chave in SINAIS}
    avaliados = {chave: 0 for chave in SINAIS}
    por_data = []
    for e in range(1, t):
        do_dia = Counter()
        comparados = 0
        for territorio in municipios:
            av = detector.avaliar(base, cal, territorio, 0, e, p)
            do_dia[av["alerta"]["nivel"] or av["alerta"]["estado"]] += 1
            comparados += any(item["criterio"] == detector.COMPARADO for item in av["alerta"]["sinais"])
            for chave in SINAIS:
                sinal = av[chave]
                if sinal["estado"] in FORA_DA_AVALIACAO:
                    continue
                avaliados[chave] += 1
                por_sinal[chave][sinal.get("classe")] += 1
        por_data.append((base.periodos[e], do_dia, comparados))
        print(f"  … {detector.curta(base.periodos[e])} avaliado", file=sys.stderr)
    print("\n## Alertas de cada sinal, em todas as datas (municípios; critérios padrão)\n")
    print(_linha(["Sinal", "Avaliações", "Moderado", "Elevado", "Crítico", "Algum nível"]))
    print(_linha(["---"] * 6))
    for chave in SINAIS:
        c, total = por_sinal[chave], avaliados[chave]
        algum = c["moderado"] + c["elevado"] + c["critico"]
        print(_linha([NOMES[chave], _numero(total), _pct(c["moderado"], total), _pct(c["elevado"], total), _pct(c["critico"], total),
                      _pct(algum, total)]))
    print("\nAvaliações: as que tinham o registro, a janela e as comparações que o sinal pede. Ficam fora a ausência de dado, a "
          "janela insuficiente, o que é só descritivo e o que não tem comparações suficientes.")
    print("\n## Proporção de municípios com algum alerta, por data\n")
    print(_linha(["Data", "Crítico", "Elevado", "Moderado", "Algum alerta", "Algum alerta comparado com a base", "Sem alerta",
                  "Sem comparações suficientes"]))
    print(_linha(["---"] * 8))
    for periodo, do_dia, comparados in por_data:
        total = sum(do_dia.values())
        algum = do_dia["critico"] + do_dia["elevado"] + do_dia["moderado"]
        print(_linha([detector.curta(periodo), _pct(do_dia["critico"], total, 1), _pct(do_dia["elevado"], total, 1),
                      _pct(do_dia["moderado"], total, 1), _pct(algum, total, 1), _pct(comparados, total, 1),
                      _pct(do_dia["sem_alerta"], total, 1), _pct(do_dia["sem_comparacoes"], total, 1)]))
    if cal_dos_estados is None:
        return
    estados = [series_brasil.estado(base, uf) for uf in sorted(base.estados)]
    print("\n## Estados como unidade: alertas por data (régua própria, com a base dos estados)\n")
    print(_linha(["Data", "Crítico", "Elevado", "Moderado", "Sem alerta", "Sem comparações suficientes"]))
    print(_linha(["---"] * 6))
    for e in range(1, t):
        do_dia = Counter()
        for territorio in estados:
            av = detector.avaliar(base, cal, territorio, 0, e, p, cal_dos_estados=cal_dos_estados)
            do_dia[av["alerta"]["nivel"] or av["alerta"]["estado"]] += 1
        print(_linha([detector.curta(base.periodos[e]), do_dia["critico"], do_dia["elevado"], do_dia["moderado"], do_dia["sem_alerta"],
                      do_dia["sem_comparacoes"]]))


def _limites_do_sinal_8(base):
    """A partir de que queda da taxa por habitante, em 2 anos, cada nível é raro: no último registro anual, por faixa de porte."""
    regua = comparativos.regua_relativa(base, "municipios")
    medida, porte = regua.valor["disponibilidade"], regua.porte
    janelas = [k for k in range(len(base.periodos)) if np.isfinite(medida[:, k]).any()]
    if len(janelas) < 2:
        print("\n## Sinal 8: sem janelas anteriores para comparar\n")
        return
    fim, antes = janelas[-1], janelas[:-1]
    usavel = np.isfinite(medida[:, antes]) & (porte[:, antes] >= 0)
    print(f"\n## Sinal 8: os limites que a raridade dá em {detector.curta(base.periodos[fim])} (variação da taxa por habitante em 2 anos)\n")
    print(_linha(["Porte no início da janela", "Variações anteriores", "Moderado: queda maior que", "Elevado: queda maior que",
                  "Crítico: queda maior que"]))
    print(_linha(["---"] * 5))

    def linha(rotulo, valores):
        ordenados = np.sort(valores)
        celulas = [rotulo, _numero(ordenados.size)]
        for um_em in (20, 100, 1000):
            corte = detector._limite_da_raridade(ordenados, um_em)
            celulas.append("sem comparações suficientes" if corte is None else f"{-corte:.1f}%".replace(".", ","))
        print(_linha(celulas))
    for faixa, rotulo in enumerate(reguas.ROTULOS_DOS_PORTES):
        valores = medida[:, antes][usavel & (porte[:, antes] == faixa)]
        if valores.size:
            linha(rotulo, valores)
    linha("**Todas as janelas e portes juntos**", medida[:, antes][usavel])
    print("\nPopulação comparável nesta base: " + comparativos.texto_dos_trechos(base) + ".")


def _contexto(base):
    p = detector.parametros(None)[0]
    print("\n## Sinal 11: contexto geográfico em cada registro anual (critério: a taxa da base toda na data)\n")
    print(_linha(["Data", "Taxa do Brasil (por 1.000)", "Municípios acima do critério", "Municípios com distância", "Distância mediana (km)",
                  "Distância no percentil 90 (km)", "Maior distância (km)"]))
    print(_linha(["---"] * 7))
    for e, periodo in enumerate(base.periodos):
        if not periodo.endswith(detector._ancora(base)):
            continue
        qd = comparativos.quadro(base, e, p, guardar=False)
        distancias = qd.distancia_km[np.isfinite(qd.distancia_km)]
        if qd.taxa_do_brasil is None or not distancias.size:
            continue
        print(_linha([detector.curta(periodo), f"{qd.taxa_do_brasil:.2f}".replace(".", ","), _numero(qd.atende.sum()), _numero(distancias.size),
                      f"{np.median(distancias):.1f}".replace(".", ","), f"{np.percentile(distancias, 90):.1f}".replace(".", ","),
                      f"{distancias.max():.1f}".replace(".", ",")]))


def main():
    argumentos = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    argumentos.add_argument("--so-regua", action="store_true", help="imprime só a régua da queda recente (municípios e estados)")
    argumentos.add_argument("--so-contexto", action="store_true", help="imprime só o contexto geográfico (sinal 11)")
    opcoes = argumentos.parse_args()

    fontes = _Fontes()
    base = series_brasil.base_de(fontes)
    print(f"Base Brasil, versão {base.versao[:12]} · {len(base.codigos)} municípios · {len(base.periodos)} competências, de "
          f"{base.periodos[0]} a {base.periodos[-1]}")
    print("Método: " + detector.VERSION + " · régua comum: 10 faixas de porte, raridade (k + 1) ÷ (n + 1), mínimos de 19, 99 e 999 "
          "comparações")
    if opcoes.so_contexto:
        _contexto(base)
        return
    cal = detector.calibrar(base, guardar=False)
    cal_dos_estados = detector.calibrar_estados(base)
    desde = _regua_da_queda("municípios", cal)
    print("\nPrimeira data avaliada: " + _primeiras_datas(base, desde) + ".")
    if cal_dos_estados is not None:
        desde = _regua_da_queda("estados como unidade", cal_dos_estados)
        print("\nPrimeira data avaliada nos estados: " + _primeiras_datas(base, desde) + ". Em " + detector.curta(base.periodos[-1]) +
              ", os estados têm " + _numero(cal_dos_estados.c_perda[5][:, -1].max()) + " comparações; o crítico pede 999.")
    if opcoes.so_regua:
        return
    _alertas_por_sinal(base, cal, cal_dos_estados, detector.parametros(None)[0])
    _limites_do_sinal_8(base)
    _contexto(base)


if __name__ == "__main__":
    main()
