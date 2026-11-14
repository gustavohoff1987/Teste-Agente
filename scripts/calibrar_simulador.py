"""Estudo de retroprojeção do Simulador de Cenários Territoriais com a base versionada (somente leitura), fora do produto e do CI.

Uso, da raiz do repositório:
    python scripts/calibrar_simulador.py

O que faz (Docs/DETECTOR_E_SIMULADOR_V3.md, Parte C, seções C.3 e C.4; os resultados ficam em Docs/SIMULADOR_DE_CENARIOS.md):

1. lê a base Brasil pela mesma leitura verificada do serviço e roda a retroprojeção com origens móveis do Simulador
   (simulador.retroprojetar), nos municípios e nos estados como unidade: em cada registro do mês âncora com 3 anos de história,
   cada jeito de projetar é ajustado só com os registros até a origem e confrontado com o observado 1, 2, 3 e 4 anos depois;
2. imprime a escolha do jeito de projetar de cada nível (regra C.3): o erro de cada candidato frente a manter o último valor, em
   quantas combinações de origem e prazo ele errou menos, quem vale, o escolhido e as exceções por porte;
3. imprime as faixas de 5, 8 e 9 em cada 10 do jeito escolhido, por porte na origem e prazo, com o estado de cada uma (conferida,
   provisória ou indisponível), como foi montada (o próprio porte, com os vizinhos ou com portes menores), os casos e a cobertura
   da conferência no tempo (a faixa remontada só com o que já era conhecido em cada origem de teste);
4. imprime o erro absoluto médio de cada método frente ao M0 (a persistência), por porte e prazo, e o viés em 4 anos;
5. confere o todo (na base do Brasil, a contagem nacional), que é uma série só e não tem retroprojeção própria: a taxa composta
   de 3 anos contra manter o último valor.

Nada é gravado: o estudo só imprime as tabelas (Markdown). Nenhum dado é alterado, e nada vai ao provedor de IA.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import detector  # noqa: E402
import series_brasil  # noqa: E402
import simulador  # noqa: E402

NOMES_DO_ESTADO = {"conferida": "conferida", "provisoria": "provisória", "indisponivel": "indisponível"}
COMO = {"propria": "o próprio porte", "vizinhas": "com os vizinhos", "portes_menores": "com portes menores", "indisponivel": "—"}
MOTIVOS = {"sem_conferencia": "sem conferência bastante", "cobertura_abaixo": "cobertura um pouco abaixo", "cobertura_baixa": "cobertura baixa",
           "poucos_casos": "poucos casos", None: ""}


def _linha(celulas):
    return "| " + " | ".join(str(c) for c in celulas) + " |"


def _pct(valor, casas=0, sinal=True):
    return (("+" if valor > 0 else "−" if valor < 0 else "") if sinal else "") + f"{abs(valor):.{casas}f}%".replace(".", ",")


def _br(valor):
    return f"{valor:,}".replace(",", ".")


def _razao(valor):
    return "—" if valor is None else f"{valor:.3f}".replace(".", ",")


def _prazos():
    return [str(anos) + (" ano" if anos == 1 else " anos") for anos in simulador.HORIZONTES_DA_FAIXA]


def _escolha(base, nivel, retro):
    r = series_brasil.rotulos(base)
    quem = r["unidades"] if nivel == "municipios" else r["grupos"] + " como unidade"
    escolha = retro.escolha
    print("\n## A escolha do jeito de projetar: " + quem + "\n")
    print("Origens:", ", ".join(detector.curta(origem) for origem in retro.origens) or "nenhuma", "·", _br(len(retro.casos)), "casos ·",
          escolha["combinacoes"], "combinações de origem e prazo.\n")
    print(_linha(["Jeito", "Erro frente a manter o último valor", "Errou menos em", "Casos", "Vale"]))
    print(_linha(["---"] * 5))
    for item in escolha["candidatos"]:
        print(_linha([simulador._nome_do_metodo(base, item["metodo"]) + " (" + item["metodo"] + ")", _razao(item["frente_ao_m0"]),
                      str(item["menos_erro_em"]) + " de " + str(item["combinacoes"]), _br(item["casos"]), "sim" if item["vale"] else "não"]))
    print("\nEscolhido:", simulador._nome_do_metodo(base, escolha["metodo"]), "(" + escolha["metodo"] + "; " + escolha["motivo"] + ").",
          "Exceções por porte:", ", ".join(simulador.ROTULOS_DOS_PORTES_DA_FAIXA[porte] for porte in escolha["excecoes"]) or "nenhuma" + ".")
    if escolha["por_porte"]:
        print("\nO escolhido frente a manter o último valor, por porte e prazo (com pelo menos " +
              str(simulador.MINIMO_POR_PORTE_NA_ESCOLHA) + " casos):\n")
        print(_linha([r["profissionais"].capitalize() + " na origem", "Razões, do menor prazo ao maior"]))
        print(_linha(["---"] * 2))
        for item in escolha["por_porte"]:
            print(_linha([simulador.ROTULOS_DOS_PORTES_DA_FAIXA[item["porte"]],
                          " · ".join(f"{razao:.2f}".replace(".", ",") for razao in item["frente_ao_m0"]) or "—"]))


def _faixas(base, nivel, retro):
    r = series_brasil.rotulos(base)
    quem = r["unidades"] if nivel == "municipios" else r["grupos"] + " como unidade"
    portes = sorted({porte for (_, porte, _) in retro.faixas})
    if not portes:
        print("\n## Faixas: " + quem + "\n\nSem faixas: a base não tem retroprojeção bastante neste nível.")
        return
    for em_10, (inferior, superior, minimo, meta) in simulador.FAIXAS_EM_10.items():
        print("\n## Faixa de " + str(em_10) + " em cada 10 do jeito escolhido: " + quem + "\n")
        print("Do " + f"{inferior:g}" + "º ao " + f"{superior:g}" + "º percentil de observado ÷ cenário − 1; pede " + str(minimo) +
              " casos por prazo; meta de cobertura de " + str(meta) + "%. \"(p)\" é provisória.\n")
        print(_linha([r["profissionais"].capitalize() + " na origem"] + _prazos()))
        print(_linha(["---"] * 5))
        for porte in portes:
            celulas = [simulador.ROTULOS_DOS_PORTES_DA_FAIXA[porte]]
            for anos in simulador.HORIZONTES_DA_FAIXA:
                f = retro.faixas.get((em_10, porte, anos))
                if f is None:
                    celulas.append("—")
                elif "inferior" not in f:
                    celulas.append("indisponível (" + _br(f["casos"]) + " casos)")
                else:
                    celulas.append(_pct(100 * f["inferior"]) + " a " + _pct(100 * f["superior"]) +
                                   {"conferida": "", "provisoria": " (p)", "indisponivel": " (indisponível)"}[f["estado"]])
            print(_linha(celulas))
        if em_10 != simulador.FAIXA_PADRAO:
            continue
        print("\nComo cada faixa de " + str(em_10) + " em cada 10 foi montada e conferida no tempo:\n")
        print(_linha([r["profissionais"].capitalize() + " na origem", "Prazo", "Estado", "Montada", "Casos", "Origens",
                      "Cobertura na conferência", "Origens de teste", "Casos de teste"]))
        print(_linha(["---"] * 9))
        for porte in portes:
            for anos, prazo in zip(simulador.HORIZONTES_DA_FAIXA, _prazos()):
                f = retro.faixas.get((em_10, porte, anos))
                if f is None:
                    continue
                estado = NOMES_DO_ESTADO[f["estado"]] + (" (" + MOTIVOS[f["motivo"]] + ")" if f.get("motivo") else "")
                print(_linha([simulador.ROTULOS_DOS_PORTES_DA_FAIXA[porte], prazo, estado, COMO[f["como"]], _br(f["casos"]),
                              f.get("origens", "—"), "—" if f.get("cobertura") is None else _pct(f["cobertura"], 1, False),
                              f.get("origens_de_teste", "—"), "—" if "casos_de_teste" not in f else _br(f["casos_de_teste"])]))


def _erros(base, nivel, retro):
    r = series_brasil.rotulos(base)
    quem = r["unidades"] if nivel == "municipios" else r["grupos"] + " como unidade"
    tabela = {(linha["metodo"], linha["porte"], linha["anos"]): linha for linha in retro.tabela}
    portes = sorted({porte for (_, porte, _) in tabela})
    metodos = [metodo for metodo in ("M0d", "M0g", "M1", "M2", "M3") if any(chave[0] == metodo for chave in tabela)]
    if not portes:
        return
    print("\n## Erro absoluto médio frente ao M0: " + quem + " (1,00 = igual à persistência; abaixo, erra menos)\n")
    print(_linha(["Método", r["profissionais"].capitalize() + " na origem"] + _prazos()))
    print(_linha(["---"] * 6))
    for metodo in metodos:
        for porte in portes:
            print(_linha([metodo, simulador.ROTULOS_DOS_PORTES_DA_FAIXA[porte]] + [
                "—" if (metodo, porte, anos) not in tabela or tabela[(metodo, porte, anos)]["frente_ao_m0"] is None
                else f"{tabela[(metodo, porte, anos)]['frente_ao_m0']:.2f}".replace(".", ",") for anos in simulador.HORIZONTES_DA_FAIXA]))
    escolhido = retro.escolha["metodo"]
    print("\n## Viés médio em 4 anos: " + quem + " (observado − projetado, em " + r["profissionais"] + ")\n")
    print(_linha([r["profissionais"].capitalize() + " na origem", "M0"] + ([escolhido] if escolhido != "M0" else [])))
    print(_linha(["---"] * (3 if escolhido != "M0" else 2)))
    for porte in portes:
        print(_linha([simulador.ROTULOS_DOS_PORTES_DA_FAIXA[porte]] + [
            "—" if (metodo, porte, 4) not in tabela else f"{tabela[(metodo, porte, 4)]['vies']:+.1f}".replace(".", ",").replace("-", "−")
            for metodo in (("M0", escolhido) if escolhido != "M0" else ("M0",))]))


def _o_todo(base):
    """O todo (na base do Brasil, a contagem nacional) é uma série só: a taxa composta de 3 anos contra manter o último valor, nas
    mesmas origens (o erro relativo absoluto mediano)."""
    r = series_brasil.rotulos(base)
    if not base.ancora:
        return
    serie = base.brasil
    do_ano = {int(periodo[:4]): i for i, periodo in enumerate(base.periodos) if periodo.endswith(base.ancora)}
    print("\n## " + r["o_todo"][0].upper() + r["o_todo"][1:] + ": a taxa composta de 3 anos contra manter o último valor\n")
    print(_linha(["Prazo", "Casos", "Erro mediano da taxa composta de 3 anos", "Erro mediano de manter o último valor"]))
    print(_linha(["---"] * 4))
    for anos, prazo in zip(simulador.HORIZONTES_DA_FAIXA, _prazos()):
        do_m1, do_m0 = [], []
        for ano, origem in do_ano.items():
            if ano - 3 not in do_ano or ano + anos not in do_ano:
                continue
            inicio, alvo = do_ano[ano - 3], do_ano[ano + anos]
            if any(serie[k] != serie[k] or serie[k] <= 0 for k in (inicio, origem, alvo)):
                continue
            taxa = (serie[origem] / serie[inicio]) ** (1 / 3.0) - 1
            do_m1.append(abs(serie[origem] * (1 + taxa) ** anos / serie[alvo] - 1))
            do_m0.append(abs(serie[origem] / serie[alvo] - 1))
        if do_m1:
            print(_linha([prazo, len(do_m1), _pct(100 * float(np.median(do_m1)), 1, False), _pct(100 * float(np.median(do_m0)), 1, False)]))


def main():
    import main as servico  # só para a leitura dos quadros; nenhuma rota é chamada
    base = series_brasil.base_de(servico._brazil_sources(""))
    print("Base Brasil, versão", base.versao[:12], "· método", simulador.VERSION)
    for nivel in ("municipios", "estados") if base.estados else ("municipios",):
        retro = simulador.retroprojetar(base, nivel, guardar=False)
        _escolha(base, nivel, retro)
        _faixas(base, nivel, retro)
        _erros(base, nivel, retro)
    _o_todo(base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
