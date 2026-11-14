"""Perfil da base para o Detector de Sinais e o Simulador de Cenários (comando V23, seção 2; Proposta V3, seção A.3).

Antes de abrir as ferramentas, o Agente lê a base sozinho: as datas e os intervalos, a série anual (o mês âncora), os portes, o
grupo de cima, a população, as coordenadas, o que a contagem conta e os nomes. Daí sai o resumo **"com esta base, dá para… / não
dá para… (motivo)"**, com os números da régua do Detector (quantas comparações a base tem e quantas cada nível pede) e, quando o
Simulador os calcula, os da retroprojeção. Vale para a base do Brasil e para uma planilha enviada (series_da_planilha).

Tudo aqui é leitura e texto determinístico: nada é gravado, e nada vai ao provedor de IA.
"""
from __future__ import annotations

import numpy as np

import comparativos
import detector
import reguas
import series_brasil
from series_brasil import Base

VERSION = "PERFIL-DA-BASE/1"
MESES = detector.MESES
ORDINAIS = ("1º", "2º", "3º", "4º", "5º", "6º", "7º", "8º", "9º", "10º")


def _br(valor) -> str:
    return detector._br(valor)


def _lista(itens: list[str], final: str = " e ") -> str:
    return itens[0] if len(itens) == 1 else ", ".join(itens[:-1]) + final + itens[-1]


def _ano_da_base(base: Base, e: int) -> str:
    """"o 2º ano da base": em que ano da série fica a data."""
    ordem = int(base.periodos[e][:4]) - int(base.periodos[0][:4]) + 1
    return "o " + ORDINAIS[ordem - 1] + " ano da base" if ordem <= len(ORDINAIS) else "o ano " + str(ordem) + " da base"


def _dos_trechos(trechos) -> str:
    """"de 2014 a 2024", "de 2014 a 2017 e de 2018 a 2021"; sem nenhum, "em nenhum trecho desta base"."""
    partes = ["de " + str(inicio) + " a " + str(fim) for inicio, fim in trechos]
    return _lista(partes) if partes else "em nenhum trecho desta base"


def _intervalos(tipos: tuple) -> str:
    """"5 ou 7 meses", "6 meses", "de 5 a 6 ou 7 meses"."""
    partes = [_br(a) if a == b else "de " + _br(a) + " a " + _br(b) for a, b in tipos]
    return _lista(partes, " ou ") + (" mês" if tipos == ((1.0, 1.0),) else " meses")


def capacidade_da_regua(base: Base, cal: detector.Calibracao) -> dict:
    """O que a régua da queda recente (sinal 6) sustenta em cada nível: desde que data a maioria dos territórios com registro pôde
    ser comparada naquele nível e, na última data, quantos não podem e a maior quantidade de comparações que a base tem."""
    saida = {}
    t = len(base.periodos)
    for nivel, _, minimo in reguas.NIVEIS:
        n_porte, n_vizinhas, n_todas = cal.c_perda[1], cal.c_perda[3], cal.c_perda[5]
        avaliavel = (n_porte >= minimo) | (n_vizinhas >= minimo) | ((n_todas >= minimo) if nivel == "moderado" else False)
        desde = None
        for e in range(1, t):
            com_registro = cal.regular[:, e]
            if com_registro.any() and (avaliavel[:, e] & com_registro).sum() * 2 >= com_registro.sum():
                desde = e
                break
        ultimo = cal.regular[:, t - 1]
        sem = int((ultimo & ~avaliavel[:, t - 1]).sum())
        # Quantas comparações a base tem no último registro, em todas as faixas de porte (o teto do que qualquer nível pode usar).
        chega = int(n_todas[:, t - 1][ultimo].max()) if ultimo.any() else 0
        saida[nivel] = {"desde": None if desde is None else base.periodos[desde], "pede": int(minimo), "chega_a": chega,
                        "sem_comparacoes_no_ultimo": sem, "com_registro_no_ultimo": int(ultimo.sum())}
    return saida


def _frases_da_regua(base: Base, capacidade: dict, quem: str) -> tuple[list[str], list[dict]]:
    """As linhas "dá para" e "não dá para" dos três níveis, para os territórios de `quem` ("" ou "nos estados como unidade")."""
    da, nao = [], []
    nomes = {"moderado": "moderados", "elevado": "elevados", "critico": "críticos"}
    for nivel in ("moderado", "elevado", "critico"):
        c = capacidade[nivel]
        onde = (" " + quem) if quem else ""
        if c["desde"] is None:
            nao.append({"o_que": "Alertas " + nomes[nivel] + onde,
                        "motivo": "eles pedem " + _br(c["pede"]) + " comparações, e esta base chega a " + _br(c["chega_a"]) + "."})
            continue
        e = base.periodos.index(c["desde"])
        frase = "Alertas " + nomes[nivel] + onde + " desde " + detector.curta(c["desde"]) + " (" + _ano_da_base(base, e) + ")."
        if c["sem_comparacoes_no_ultimo"]:
            frase += (" No último registro, " + _br(c["sem_comparacoes_no_ultimo"]) + " de " + _br(c["com_registro_no_ultimo"]) +
                      " territórios ficam sem comparações suficientes neste nível (os de porte com pouca história).")
        da.append(frase)
    return da, nao


def perfil(base: Base, cal: detector.Calibracao | None = None) -> dict:
    """O perfil da base e o resumo "dá para / não dá para" (seção A.3)."""
    cal = cal if cal is not None else detector.calibrar(base)
    r = series_brasil.rotulos(base)
    descricao = base.descricao or {"base": "Brasil", "categoria": "MEDICINA"}
    t = len(base.periodos)
    faltas = detector.falta_na_base(base)
    tem_populacao = bool(np.isfinite(base.populacao).any())
    tem_coordenadas = bool(np.isfinite(base.latitude).any())
    tem_grupo = bool(base.do_estado)
    itens, da_para, nao_da_para = [], [], []

    # Datas e intervalos.
    irregular = len(cal.tipos) > 1 or any(a != b for a, b in cal.tipos)
    itens.append({"chave": "datas", "titulo": "Datas e intervalos",
                  "lido": _br(t) + " registros, de " + detector.curta(base.periodos[0]) + " a " + detector.curta(base.periodos[-1]) + ", com " +
                  _intervalos(cal.tipos) + " entre eles. Só se comparam mudanças com o mesmo tempo entre registros" +
                  (" (as durações parecidas ficam juntas)." if any(a != b for a, b in cal.tipos) else "."),
                  "falta": None, "irregular": irregular})

    # Série anual (o mês âncora).
    if base.ancora:
        anuais = [p for p in base.periodos if p.endswith(base.ancora)]
        quantos = " (" + _br(len(anuais)) + " anos, de " + anuais[0][:4] + " a " + anuais[-1][:4] + ")."
        itens.append({"chave": "serie_anual", "titulo": "Série anual", "falta": None,
                      "lido": "A base tem um registro por ano" + quantos if base.ancora == "00" else
                      "Usa os registros de " + MESES[int(base.ancora) - 1] + ", o mês presente em todos os anos" + quantos})
    else:
        motivo = "nenhum mês se repete em todos os anos."
        itens.append({"chave": "serie_anual", "titulo": "Série anual", "lido": "A base não tem série anual: " + motivo,
                      "falta": "Ficam indisponíveis os sinais anuais (3, 4 e 8 a 10) e a retroprojeção do Simulador."})
        nao_da_para.append({"o_que": "Sinais anuais (declínio persistente, desaceleração e os comparados em 2 anos) e a retroprojeção "
                                     "do Simulador", "motivo": motivo})
    if "patamar" in faltas:
        nao_da_para.append({"o_que": '"Abaixo do que já teve" (sinal 7)', "motivo": faltas["patamar"][:1].lower() + faltas["patamar"][1:]})

    # Portes: quantos territórios em cada faixa, no último registro de cada um.
    ultimos = np.full(len(base.codigos), np.nan)
    for coluna in range(t):
        valores = base.quantidade[:, coluna]
        ultimos = np.where(np.isnan(valores), ultimos, valores)
    faixas = reguas.portes(ultimos)
    por_porte = [{"porte": rotulo, "territorios": int((faixas == k).sum())} for k, rotulo in enumerate(reguas.ROTULOS_DOS_PORTES)]
    em_zero = int((ultimos == 0).sum())
    ocupadas = [item for item in por_porte if item["territorios"]]
    itens.append({"chave": "portes", "titulo": "Portes", "falta": None, "por_porte": por_porte, "em_zero": em_zero,
                  "lido": _br(len(base.codigos)) + " " + r["unidades"] + ", em " + _br(len(ocupadas)) + (" faixa" if len(ocupadas) == 1 else " faixas") +
                  " de porte pelo número de " + r["profissionais"] + " (" +
                  _lista([_br(item["territorios"]) + " de " + item["porte"] for item in ocupadas]) +
                  ("; " + _br(em_zero) + " em zero" if em_zero else "") + "). Quando faltam casos numa faixa, ela se junta às vizinhas."})

    # Grupo de cima.
    if tem_grupo:
        itens.append({"chave": "grupo", "titulo": "Grupo de cima", "falta": None,
                      "lido": _br(len(base.do_estado)) + " " + (r["grupo"] if len(base.do_estado) == 1 else r["grupos"]) +
                      (" (pelo prefixo do código IBGE)." if base.do_brasil else " (a coluna de grupo escolhida).")})
    else:
        itens.append({"chave": "grupo", "titulo": "Grupo de cima", "lido": "A base não tem coluna de grupo.",
                      "falta": "O Simulador usa o crescimento da base toda; o sinal 10 fica indisponível."})
        nao_da_para.append({"o_que": '"Mais longe da referência" (sinal 10) e o crescimento do grupo no Simulador',
                            "motivo": "a base não tem grupo de cima; o Simulador usa o crescimento da base toda."})

    # População: os trechos comparáveis, lidos da própria base.
    if tem_populacao:
        trechos = comparativos.trechos_comparaveis(base)
        itens.append({"chave": "populacao", "titulo": "População", "falta": None, "trechos": trechos,
                      "lido": "Com população. A variação por habitante é comparável " + _dos_trechos(trechos) + "."})
        if base.ancora and trechos:
            da_para.append("Sinais por habitante (8 a 10) e comparações por habitante no Simulador, " + _dos_trechos(trechos) + ".")
    else:
        itens.append({"chave": "populacao", "titulo": "População", "lido": "A base não tem coluna de população.",
                      "falta": "Ficam indisponíveis os sinais 8 a 11 e as comparações por habitante do Simulador."})
        nao_da_para.append({"o_que": "Sinais por habitante (8 a 11) e comparações por habitante no Simulador",
                            "motivo": "a base não tem população."})

    # Coordenadas.
    if tem_coordenadas:
        itens.append({"chave": "coordenadas", "titulo": "Coordenadas", "falta": None,
                      "lido": "Com coordenadas (" + ("SIRGAS 2000, do perfil oficial" if base.do_brasil else "o referencial informado") + ")."})
        if tem_populacao:
            da_para.append("Distância até " + r["o_unidade"] + " mais " + ("próximo" if r["o_unidade"].startswith("o ") else "próxima") +
                           " com mais " + r["profissionais"] + " por habitante (sinal 11, só contexto).")
    else:
        itens.append({"chave": "coordenadas", "titulo": "Coordenadas", "lido": "A base não tem coordenadas com o referencial informado.",
                      "falta": "O sinal 11 (distância) fica indisponível."})
        if tem_populacao:
            nao_da_para.append({"o_que": "Distância (sinal 11)", "motivo": "a base não tem coordenadas com o referencial informado."})

    # O que a contagem conta.
    aviso = next((item["texto"] for item in base.avisos if item.get("codigo") == "DUPLA_CONTAGEM"), None)
    itens.append({"chave": "contagem", "titulo": "O que a contagem conta", "lido": series_brasil.contagem_de(base, "municipio")[:1].upper() +
                  series_brasil.contagem_de(base, "municipio")[1:] + ".", "falta": aviso})
    # Nomes.
    itens.append({"chave": "nomes", "titulo": "Nomes", "falta": None,
                  "lido": "A contagem é de " + r["profissionais"] + "; os territórios são " + r["os_unidades"] +
                  ("; o grupo de cima, " + r["os_grupos"] if tem_grupo else "") + "; o todo, " + r["o_todo"] + "."})

    # O que a régua do Detector sustenta (municípios ou unidades) e, na base do Brasil, a régua própria dos estados.
    capacidade = capacidade_da_regua(base, cal)
    da, nao = _frases_da_regua(base, capacidade, "")
    da_para = da + da_para
    nao_da_para = nao + nao_da_para
    dos_estados = None
    if base.estados:
        cal_dos_estados = detector.calibrar_estados(base)
        dos_estados = capacidade_da_regua(detector.base_dos_estados(base), cal_dos_estados)
        da, nao = _frases_da_regua(base, dos_estados, "n" + r["os_grupos"] + " como unidade")
        da_para += da
        nao_da_para += nao
    if base.ancora:
        da_para.append("Sinais anuais (declínio persistente e desaceleração), pela série de " +
                       ("cada ano" if base.ancora == "00" else MESES[int(base.ancora) - 1]) + ".")

    return {"versao": VERSION, "origem": base.origem, "base": descricao["base"], "categoria": descricao["categoria"],
            "versao_da_base": base.versao, "territorios": len(base.codigos), "registros": t, "primeira": base.periodos[0],
            "ultima": base.periodos[-1], "ancora": base.ancora, "nomes": series_brasil.rotulos_publicos(base), "itens": itens,
            "regua": capacidade, **({"regua_dos_estados": dos_estados} if dos_estados else {}),
            "da_para": da_para, "nao_da_para": nao_da_para, "avisos": [item["texto"] for item in base.avisos],
            "tem": {"populacao": tem_populacao, "coordenadas": tem_coordenadas, "grupo": tem_grupo, "serie_anual": bool(base.ancora)}}
