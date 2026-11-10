"""Estudo de retroprojeção do Simulador de Cenários Territoriais com a base versionada (somente leitura), fora do produto e do CI.

Uso, da raiz do repositório:
    python scripts/calibrar_simulador.py

O que faz (Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 8.8 e 11; os resultados ficam em Docs/SIMULADOR_DE_CENARIOS.md):

1. lê a base Brasil pela mesma leitura verificada do serviço e roda a retroprojeção com origens móveis do Simulador
   (simulador.retroprojetar): em cada junho com 3 anos de história, cada método é ajustado só com os registros até a origem e
   confrontado com o observado 1, 2, 3 e 4 anos depois;
2. imprime as faixas de 80% do método padrão dos municípios (M0d), por porte na origem e horizonte, com o número de casos e de
   origens e a cobertura fora da amostra (a faixa calculada sem uma origem, conferida nela);
3. imprime o erro absoluto médio de cada método frente ao M0 (a persistência), por porte e horizonte, e o viés;
4. confere o padrão provisório dos estados como unidade e do Brasil (M1 de 3 anos na série do próprio nível) contra o M0.

Nada é gravado: o estudo só imprime as tabelas (Markdown). Nenhum dado é alterado, e nada vai ao provedor de IA.
"""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import series_brasil  # noqa: E402
import simulador  # noqa: E402


def _linha(celulas):
    return "| " + " | ".join(str(c) for c in celulas) + " |"


def _pct(valor, casas=0, sinal=True):
    return (("+" if valor > 0 else "−" if valor < 0 else "") if sinal else "") + f"{abs(valor):.{casas}f}%".replace(".", ",")


def main():
    import main as servico  # só para a leitura dos quadros; nenhuma rota é chamada
    base = series_brasil.base_de(servico._brazil_sources(""))
    retro = simulador.retroprojetar(base, guardar=False)
    portes = simulador.ROTULOS_DOS_PORTES_DA_FAIXA
    print("Base Brasil, versão", base.versao[:12], "· método", simulador.VERSION)
    print("Origens (junho, com 3 anos de história):", ", ".join(retro.origens))

    print("\n## Faixas de 80% do M0d (P10 a P90 de observado ÷ projetado − 1)\n")
    print(_linha(["Médicos na origem"] + [str(anos) + (" ano" if anos == 1 else " anos") for anos in simulador.HORIZONTES_DA_FAIXA]))
    print(_linha(["---"] * 5))
    for porte, rotulo in enumerate(portes):
        celulas = [rotulo]
        for anos in simulador.HORIZONTES_DA_FAIXA:
            f = retro.faixas.get((porte, anos))
            celulas.append("indisponível" if not f else _pct(100 * f["inferior"]) + " a " + _pct(100 * f["superior"]) + " (" +
                           str(f["origens"]) + " origens, " + str(f["casos"]) + " casos, cobertura " +
                           ("—" if f["cobertura"] is None else _pct(100 * f["cobertura"], 1, False)) + ")")
        print(_linha(celulas))

    tabela = {(linha["metodo"], linha["porte"], linha["anos"]): linha for linha in retro.tabela}
    print("\n## Erro absoluto médio frente ao M0 (1,00 = igual à persistência; abaixo, erra menos)\n")
    print(_linha(["Método", "Médicos na origem", "1 ano", "2 anos", "3 anos", "4 anos"]))
    print(_linha(["---"] * 6))
    for metodo in ("M0d", "M1", "M2", "M3"):
        for porte, rotulo in enumerate(portes):
            print(_linha([metodo, rotulo] + [f"{tabela[(metodo, porte, anos)]['frente_ao_m0']:.2f}".replace(".", ",")
                                             if (metodo, porte, anos) in tabela else "—" for anos in simulador.HORIZONTES_DA_FAIXA]))
    print("\n## Viés médio em 4 anos (observado − projetado, em médicos)\n")
    print(_linha(["Médicos na origem", "M0", "M0d"]))
    print(_linha(["---"] * 3))
    for porte, rotulo in enumerate(portes):
        print(_linha([rotulo] + [f"{tabela[(metodo, porte, 4)]['vies']:+.1f}".replace(".", ",") for metodo in ("M0", "M0d")]))

    # Estados como unidade e Brasil: M1 de 3 anos na série do próprio nível contra o M0 (erro relativo absoluto mediano).
    print("\n## Estados como unidade e Brasil: padrão provisório (M1 de 3 anos) contra o M0\n")
    print(_linha(["Nível", "Horizonte", "Casos", "Erro mediano do M1 de 3 anos", "Erro mediano do M0"]))
    print(_linha(["---"] * 5))
    for nome, series in (("Estados", list(base.estados.values())), ("Brasil", [base.brasil])):
        for anos in (1, 2, 4):
            erros_m1, erros_m0 = [], []
            for serie in series:
                for origem in range(6, len(base.periodos) - 2 * anos):
                    if not base.periodos[origem].endswith("06"):
                        continue
                    inicio, alvo = origem - 6, origem + 2 * anos
                    if any(serie[k] != serie[k] or serie[k] <= 0 for k in (inicio, origem, alvo)):
                        continue
                    taxa = (serie[origem] / serie[inicio]) ** (1 / 3.0) - 1
                    erros_m1.append(abs(serie[origem] * (1 + taxa) ** anos / serie[alvo] - 1))
                    erros_m0.append(abs(serie[origem] / serie[alvo] - 1))
            print(_linha([nome, str(anos) + (" ano" if anos == 1 else " anos"), len(erros_m1),
                          _pct(100 * float(np.median(erros_m1)), 1, False), _pct(100 * float(np.median(erros_m0)), 1, False)]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
