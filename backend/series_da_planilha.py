"""Séries de uma planilha enviada para o Detector de Sinais e o Simulador de Cenários (comando V23, seção 2; Proposta V3, seção
A.3: "qualquer base").

A planilha é lida com o **mesmo mapeamento de colunas, as mesmas premissas e o mesmo catálogo das análises** (`painel._upload_context`,
o portão de `/api/painel`): a coluna territorial e o código, o período, a categoria, a contagem, a população, o grupo de cima e as
coordenadas são os que a pessoa escolheu no painel "Colunas". Daqui sai uma `series_brasil.Base`, a mesma estrutura da base do
Brasil, com o que antes era fixo dito pela própria planilha:

- **datas:** as competências viram "AAAAMM" (de "AAAAMM", de "AAAA-MM" ou de "AAAA-MM-DD"); uma planilha só com anos fica com
  "AAAA00" (um registro por ano). Números que não são anos não são datas: as ferramentas dizem isso e param. A posição de cada
  registro é o mês real, como na base do Brasil.
- **mês âncora, tipos de intervalo e meses de registro:** lidos das datas (`series_brasil.mes_ancora` e os demais ajudantes).
- **grupo de cima:** a coluna do papel `grupo_territorial`; sem ela, a base não tem grupo (o sinal 10 e o crescimento do grupo no
  Simulador ficam indisponíveis). Não há "grupo como unidade": a planilha não tem uma contagem própria do grupo.
- **o todo:** a soma das unidades com registro em cada data ("a base toda"), para o critério da distância e para o crescimento da
  base toda no Simulador.
- **população e coordenadas:** só quando as colunas foram escolhidas (as coordenadas, com o referencial informado); sem elas, os
  sinais 8 a 11 e as comparações por habitante ficam indisponíveis, com o motivo.
- **nomes:** os do painel "Colunas" (`rotulos`: a unidade, o grupo e o todo); o que a contagem conta vem da unidade de contagem
  informada (pessoas, vínculos, postos ou outra).

Só lê: nada é gravado, e nada daqui vai ao provedor de IA. A base montada fica guardada por conteúdo (o resumo das linhas, o
mapeamento e as opções), como as matrizes da base do Brasil.
"""
from __future__ import annotations

import hashlib
import json
import re
import threading

import numpy as np
import pandas as pd

import series_brasil
from series_brasil import Base

VERSION = "SERIES-PLANILHA/1"
OPCOES_DA_BASE = ("rotulos", "premissas", "categoria")   # o que o pedido das ferramentas traz sobre a planilha (como no painel)
MAX_BASES = 3
_BASES: dict[str, Base] = {}
_LOCK = threading.Lock()

SEM_DATAS = ("As ferramentas precisam de datas (mês e ano, ou só o ano) para medir o tempo entre os registros. A coluna de período "
             "desta planilha não traz datas que o Agente reconheça: use AAAAMM, AAAA-MM, AAAA-MM-DD ou o ano.")


def _competencias(rotulos: list[str]) -> list[str]:
    """As competências da planilha no formato das ferramentas ("AAAAMM"; "AAAA00" numa planilha só com anos), na ordem dos rótulos."""
    from data_contract import resolve_convention
    convencao = resolve_convention(rotulos, "auto")
    try:
        if convencao == "yyyymm":
            datas = pd.to_datetime(rotulos, format="%Y%m", errors="raise")
            saida = [f"{d.year:04d}{d.month:02d}" for d in datas]
        elif convencao == "date":
            datas = pd.to_datetime(rotulos, format="ISO8601", errors="raise")
            saida = [f"{d.year:04d}{d.month:02d}" for d in datas]
        else:
            if not all(re.fullmatch(r"(1[89]|2[01])\d\d(\.0+)?", rotulo) for rotulo in rotulos):
                raise ValueError(SEM_DATAS)
            saida = [rotulo[:4] + "00" for rotulo in rotulos]
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(str(exc) if str(exc) == SEM_DATAS else SEM_DATAS) from None
    if len(set(saida)) != len(saida):
        raise ValueError("A planilha tem mais de um registro no mesmo mês. As ferramentas usam um registro por mês: escolha uma "
                         "data por mês ou junte os registros.")
    return saida


def _nomes(labels, contagem: str) -> dict:
    """Os nomes da base para os textos (seção A.2.6), com as formas de artigo e preposição que a concordância pede."""
    unidade, grupo, todo = labels.unidade, labels.grupo, labels.todo
    profissional, profissionais = {"vinculos": ("vínculo", "vínculos"), "postos": ("posto", "postos")}.get(contagem, ("profissional", "profissionais"))
    return {"profissional": profissional, "profissionais": profissionais, "unidade": unidade.singular, "unidades": unidade.plural,
            "grupo": grupo.singular, "grupos": grupo.plural, "todo": todo.nome if todo else "a base toda",
            "o_unidade": unidade.g("o", "a") + " " + unidade.singular, "os_unidades": unidade.g("os", "as") + " " + unidade.plural,
            "o_grupo": grupo.g("o", "a") + " " + grupo.singular, "os_grupos": grupo.g("os", "as") + " " + grupo.plural,
            "dos_grupos": "d" + grupo.g("os", "as") + " " + grupo.plural, "do_todo": labels.de_todo(), "no_todo": labels.em_todo(),
            "o_todo": ((todo.artigo + " ") if todo and todo.artigo else "") + todo.nome if todo else "a base toda"}


def _o_que_conta(contagem: str, personalizada: str, unidade: str, um: str = "um") -> tuple[str, str | None]:
    """O que a contagem conta, como nas análises (a unidade de contagem informada no painel "Colunas"), e o aviso de dupla contagem
    quando ela não foi informada como pessoas."""
    if contagem == "pessoas":
        return "pessoas registradas em cada " + unidade + " (quem aparece em mais de " + um + " conta em cada " + um + ")", None
    if contagem in ("vinculos", "postos"):
        nome = "vínculos" if contagem == "vinculos" else "postos"
        return (nome + " registrados em cada " + unidade,
                "A contagem é de " + nome + ", não de pessoas: uma pessoa com mais de um conta mais de uma vez.")
    if contagem == "outro" and personalizada:
        return personalizada + " em cada " + unidade, "A contagem é de " + personalizada + ": pode haver dupla contagem de pessoas."
    return ("contagem da planilha em cada " + unidade + " (a unidade de contagem não foi informada)",
            "A planilha não diz o que a contagem conta: pode haver dupla contagem de pessoas.")


def _chave(frame, mapping: dict, opcoes: dict) -> str:
    resumo = hashlib.sha256(pd.util.hash_pandas_object(frame, index=True).values.tobytes())
    resumo.update(json.dumps([list(map(str, frame.columns)), mapping, opcoes], sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    return "planilha:" + resumo.hexdigest()


def opcoes_da_base(opcoes: dict) -> dict:
    """Do pedido das ferramentas, o que descreve a planilha (os nomes, as premissas e a categoria), como no painel."""
    return {chave: opcoes[chave] for chave in OPCOES_DA_BASE if opcoes.get(chave) not in (None, "", {}, [])}


def base_da_planilha(frame, mapping: dict, opcoes: dict) -> Base:
    """A base das ferramentas para a planilha enviada (montada uma vez por conteúdo, mapeamento e opções)."""
    if frame is None or not isinstance(mapping, dict):
        raise ValueError('Envie a planilha e o mapeamento de colunas escolhido no painel "Colunas".')
    da_base = opcoes_da_base(opcoes if isinstance(opcoes, dict) else {})
    chave = _chave(frame, mapping, da_base)
    with _LOCK:
        guardada = _BASES.get(chave)
    if guardada is not None:
        return guardada
    montada = _montar(frame, mapping, da_base, chave)
    with _LOCK:
        _BASES[chave] = montada
        while len(_BASES) > MAX_BASES:
            _BASES.pop(next(iter(_BASES)))
    return montada


def _montar(frame, mapping: dict, opcoes: dict, versao: str) -> Base:
    import painel  # importação tardia: o painel importa meio motor
    from data_contract import text_values

    coluna_de_periodo = (mapping or {}).get("period")
    brutos = list(dict.fromkeys(text_values(frame[coluna_de_periodo]).dropna().tolist())) \
        if coluna_de_periodo and coluna_de_periodo in getattr(frame, "columns", ()) else []
    # O mesmo portão das análises: papéis reconhecidos ou escolhidos, competência e categoria existentes, premissas e nomes.
    ctx = painel._upload_context(frame, dict(mapping), {**opcoes, "competencia": brutos[-1] if brutos else None}, True)
    if ctx.periods_error or not ctx.positions:
        raise ValueError(SEM_DATAS)
    ordenados = list(ctx.periods)                                   # os rótulos da planilha, na ordem do tempo
    competencias = _competencias(ordenados)
    ordem = sorted(range(len(competencias)), key=lambda k: series_brasil.mes_da_competencia(competencias[k]))
    ordenados, competencias = [ordenados[k] for k in ordem], [competencias[k] for k in ordem]
    if len(competencias) < 2:
        raise ValueError("A planilha tem um registro só no tempo: as ferramentas comparam registros de datas diferentes.")

    unidade = ctx.labels.unidade
    chaves = sorted(ctx.catalog, key=lambda item: (ctx.catalog[item]["code"], item))
    if not chaves:
        raise ValueError("A planilha não tem " + unidade.plural + " para as ferramentas.")
    prefixo = "code:" if ctx.mapping.get("territory_id") else "name:"
    codigos = tuple(chave[len(prefixo):] for chave in chaves)
    nomes_simples = [ctx.catalog[chave]["name"] for chave in chaves]
    repetidos = {nome for nome in nomes_simples if nomes_simples.count(nome) > 1} if len(set(nomes_simples)) != len(nomes_simples) else set()
    nomes = tuple(ctx.catalog[chave]["label"] if ctx.catalog[chave]["name"] in repetidos else ctx.catalog[chave]["name"] for chave in chaves)
    linha_de = {chave: posicao for posicao, chave in enumerate(chaves)}
    forma = (len(chaves), len(competencias))
    quantidade, populacao = np.full(forma, np.nan), np.full(forma, np.nan)
    for coluna, periodo in enumerate(ordenados):
        for chave, registro in painel._measures(ctx, periodo).records.items():
            linha = linha_de.get(chave)
            if linha is None:
                continue
            valores = registro["valores"]
            if valores.get("quantidade") is not None:
                quantidade[linha, coluna] = float(valores["quantidade"])
            if ctx.density and valores.get("populacao") is not None:
                populacao[linha, coluna] = float(valores["populacao"])
    presentes = quantidade[~np.isnan(quantidade)]
    if not presentes.size:
        raise ValueError("A planilha não tem contagens para as ferramentas.")
    if (presentes < 0).any() or (np.abs(presentes - np.round(presentes)) > 1e-9).any():
        raise ValueError("As ferramentas contam em números inteiros (0, 1, 2…): a coluna de contagem desta planilha tem valores "
                         "negativos ou com casas decimais.")
    quantidade = np.where(np.isnan(quantidade), np.nan, np.round(quantidade))

    avisos = []
    # Coordenadas: só com as colunas e o referencial escolhidos (como na Análise Espacial); sem eles, a distância fica indisponível.
    latitude, longitude = np.full(forma, np.nan), np.full(forma, np.nan)
    tem_coordenadas = False
    if ctx.mapping.get("latitude") and ctx.mapping.get("longitude"):
        try:
            espaciais = painel._upload_spatial_settings(ctx)
            for coluna, periodo in enumerate(ordenados):
                pontos = painel._coordinates(ctx.frame, ctx.mapping, espaciais, periodo)
                validos = pontos[pontos["condicao"] == "VALIDA"]
                for chave, lat, lon in zip(validos.index.tolist(), validos["lat"].tolist(), validos["lon"].tolist()):
                    linha = linha_de.get(chave)
                    if linha is not None:
                        latitude[linha, coluna], longitude[linha, coluna] = float(lat), float(lon)
            tem_coordenadas = bool(np.isfinite(latitude).any())
        except Exception as exc:  # noqa: BLE001 — a falta de coordenadas não impede os outros sinais: vira motivo no perfil
            avisos.append({"codigo": "COORDENADAS", "texto": "As coordenadas não puderam ser usadas: " + str(exc)})

    # O grupo de cima (a coluna do papel grupo_territorial): o valor de cada unidade; sem ele (ou com mais de um), sem grupo.
    grupos_das_unidades = [ctx.groups.get(chave) or "" for chave in chaves] if ctx.group_column else [""] * len(chaves)
    do_grupo: dict[str, list[int]] = {}
    for posicao, grupo in enumerate(grupos_das_unidades):
        if grupo:
            do_grupo.setdefault(grupo, []).append(posicao)
    # O todo: a soma das unidades com registro em cada data (NaN quando nenhuma tem).
    com_registro = (~np.isnan(quantidade)).sum(axis=0)
    todo = np.where(com_registro > 0, np.nansum(quantidade, axis=0), np.nan)

    contagem = str(ctx.premissas.get("count_unit") or "")
    o_que_conta, aviso_da_contagem = _o_que_conta(contagem, str(ctx.premissas.get("custom_count_unit") or "").strip(), unidade.singular,
                                                  unidade.g("um", "uma"))
    if aviso_da_contagem:
        avisos.append({"codigo": "DUPLA_CONTAGEM", "texto": aviso_da_contagem})
    for matriz in (quantidade, populacao, latitude, longitude, todo):
        matriz.setflags(write=False)
    return Base(
        versao=versao, periodos=tuple(competencias), meses=np.array([series_brasil.mes_da_competencia(p) for p in competencias]),
        codigos=codigos, nomes=nomes, prefixos=tuple(grupos_das_unidades), quantidade=quantidade, populacao=populacao,
        latitude=latitude, longitude=longitude, estados={}, brasil=todo,
        indice={codigo: posicao for posicao, codigo in enumerate(codigos)},
        do_estado={grupo: tuple(linhas) for grupo, linhas in do_grupo.items()},
        origem="planilha", ancora=series_brasil.mes_ancora(tuple(competencias)), rotulos=_nomes(ctx.labels, contagem),
        grupos={grupo: (grupo, grupo) for grupo in do_grupo}, prefixo_do_id=prefixo,
        contagens={"municipio": o_que_conta, "conjunto": "soma das contagens dos componentes (não é o número de pessoas diferentes do conjunto)",
                   "brasil": "soma das contagens de " + unidade.g("todos os", "todas as") + " " + unidade.plural + " com registro na data"},
        descricao={"base": "planilha enviada", "categoria": str(ctx.premissas.get("object_declaration") or ctx.category),
                   "tem_populacao": bool(ctx.density),
                   "tem_coordenadas": tem_coordenadas, "tem_grupo": bool(do_grupo), "periodos_da_planilha": dict(zip(competencias, ordenados))},
        avisos=tuple(avisos))
