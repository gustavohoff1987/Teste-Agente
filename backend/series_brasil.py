"""Séries observadas da base Brasil para o Detector de Sinais Territoriais e o Simulador de Cenários Territoriais (comando
V22, seção 11: contratos compartilhados; Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2 e 13).

Um só lugar lê as três fontes governadas e as entrega como séries por território e competência, com as regras que as duas
ferramentas compartilham:

- **datas reais:** as competências são as da base (janeiro e junho de 2014 a 2024), na ordem da data; a posição de cada uma é
  o mês real (ano × 12 + mês − 1), de modo que janeiro → junho são 5 meses e junho → janeiro, 7. Nenhuma data é inventada.
- **zero e ausente:** contagem zero é registro observado ("zero confirmado"); o par município × competência sem linha fica
  ausente (NaN), nunca zero.
- **fontes e unidade de contagem:** o município vem da fonte municipal (médicos registrados no município: quem atua em mais
  de um conta em cada um); o estado como unidade, da fonte estadual (médicos únicos na UF); o Brasil, da fonte nacional. Uma
  soma de municípios (um conjunto) é sempre "soma das contagens dos componentes", nunca "médicos únicos".
- **seleção:** o mesmo contrato do painel — `base.municipios` ({todos, estados, ids}), `estados_unidade` e `conjuntos`
  ({id, rotulo, membros}), com os ids "code:<IBGE>" e "uf:<prefixo>". Conjuntos reúnem territórios do mesmo nível.

Só lê: nenhum arquivo é alterado, e nada daqui vai ao provedor de IA. As matrizes ficam guardadas por versão da base (são
pequenas: 5.570 × 22), e cada pedido recebe o mesmo objeto, que ninguém altera.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from brazil_catalog_profile import FIELDS, TRUSTED_CATEGORY
from territorial_levels import SIGLAS, STATES, human_period

VERSION = "SERIES-BRASIL/1"
# O Detector de Sinais vale para qualquer base desde o comando V23 (a do Brasil ou uma planilha enviada); o Simulador de Cenários
# continua só com a base do Brasil até ganhar a mesma estrutura (Parte C da Proposta V3).
OFFICIAL_ONLY = ("O Simulador de Cenários Territoriais usa a base do Brasil (médicos, registros de janeiro e junho de 2014 a 2024); "
                 "com uma planilha enviada, ainda não está disponível.")
SEM_BASE = "Escolha a base do Brasil ou envie uma planilha: a ferramenta lê a base que estiver em uso."
UNIDADE_MUNICIPIO = "médicos registrados no município (fonte municipal; quem atua em mais de um município conta em cada um)"
UNIDADE_ESTADO = "médicos únicos no estado (fonte estadual)"
UNIDADE_BRASIL = "médicos únicos no Brasil (fonte nacional)"
UNIDADE_CONJUNTO = "soma das contagens dos componentes (não é o número de médicos diferentes do conjunto)"
# Os nomes da base (Proposta V3, seção A.2.6): na base do Brasil, os textos dizem "médicos", "estado", "junho" e "Brasil"; numa
# planilha enviada, os nomes vêm dela (perfil da base).
ROTULOS_DO_BRASIL = {"profissional": "médico", "profissionais": "médicos", "unidade": "município", "unidades": "municípios",
                     "grupo": "estado", "grupos": "estados", "todo": "Brasil"}
# As formas com artigo e preposição, para a concordância ("o município", "a unidade"; "do Brasil", "da Solária", "de toda a
# base"). Ficam fora de `fonte.rotulos` da resposta, que traz só os sete nomes.
FORMAS_DO_BRASIL = {"o_unidade": "o município", "os_unidades": "os municípios", "o_grupo": "o estado", "os_grupos": "os estados",
                    "dos_grupos": "dos estados", "do_todo": "do Brasil", "no_todo": "no Brasil", "o_todo": "o Brasil"}
NOMES_PUBLICOS = ("profissional", "profissionais", "unidade", "unidades", "grupo", "grupos", "todo")


def rotulos(base) -> dict:
    """Os nomes que os textos usam para esta base: os sete nomes e as formas com artigo e preposição."""
    return {**ROTULOS_DO_BRASIL, **FORMAS_DO_BRASIL, **(getattr(base, "rotulos", None) or {})}


def rotulos_publicos(base) -> dict:
    """Os sete nomes da base, como a resposta das rotas os traz (`fonte.rotulos`)."""
    r = rotulos(base)
    return {chave: r[chave] for chave in NOMES_PUBLICOS}


def nome_do_grupo(base, chave: str) -> tuple[str, str]:
    """(nome curto, nome) de um grupo de cima: na base do Brasil, a sigla e o nome do estado; numa planilha, o valor da coluna."""
    proprios = getattr(base, "grupos", None) or {}
    if chave in proprios:
        return proprios[chave]
    return (STATES[chave][0], STATES[chave][1]) if chave in STATES else (str(chave), str(chave))


# --------------------------------------------------------------------------------------------- calendário de qualquer base
def mes_ancora(periodos) -> str | None:
    """O mês âncora da série anual (seção A.3): o mês presente em todos os anos da base. Vale o mês do último registro, quando ele
    aparece em todos os anos desde a primeira vez (sem falha) e cobre a base inteira ou falta só um ano numa das pontas; senão,
    entre os meses que cumprem isso, o mais próximo do último registro. Sem nenhum, None: a base não tem série anual. Na base do
    Brasil (janeiro e junho de 2014 a 2024), é junho ("06")."""
    if not periodos:
        return None
    anos_da_base = sorted({int(periodo[:4]) for periodo in periodos})
    por_mes: dict[str, set[int]] = {}
    for periodo in periodos:
        por_mes.setdefault(periodo[4:], set()).add(int(periodo[:4]))

    def serve(mes: str) -> bool:
        anos = sorted(por_mes[mes])
        sem_falha = anos == list(range(anos[0], anos[-1] + 1))
        return sem_falha and len(anos) >= 2 and len(anos) >= len(anos_da_base) - 1
    ultimo = periodos[-1][4:]
    if serve(ultimo):
        return ultimo
    candidatos = [mes for mes in por_mes if serve(mes)]
    if not candidatos:
        return None
    distancia = lambda mes: (int(ultimo) - int(mes)) % 12   # noqa: E731 — o mês mais recente antes do último registro
    return min(candidatos, key=lambda mes: (distancia(mes), mes))


def meses_de_registro(periodos) -> tuple[str, ...]:
    """Os meses do ano em que a base tem registro em todos os anos completos (na base do Brasil, "01" e "06"): os que formam os
    "dois anos completos" do patamar. Vazio quando nenhum mês se repete em todos os anos do meio da base."""
    anos = sorted({int(periodo[:4]) for periodo in periodos})
    if len(anos) < 2:
        return ()
    por_ano: dict[int, set[str]] = {}
    for periodo in periodos:
        por_ano.setdefault(int(periodo[:4]), set()).add(periodo[4:])
    # Os anos das pontas podem estar incompletos (a base começa ou termina no meio do ano): valem os meses dos anos do meio,
    # ou, com dois anos só, os comuns aos dois.
    meio = anos[1:-1] or anos
    comuns = set.intersection(*(por_ano[ano] for ano in meio))
    return tuple(sorted(comuns))


def tipos_de_intervalo(meses) -> tuple[np.ndarray, tuple]:
    """O tipo do intervalo de cada transição (seção A.3: "compara só intervalos iguais; com intervalos irregulares, agrupa os de
    duração parecida"). Devolve, para cada registro, o tipo da transição que termina nele (−1 no primeiro) e os tipos, cada um
    com o menor e o maior intervalo, em meses. Durações com até 1 mês de diferença da menor do grupo ficam juntas: na base do
    Brasil, 5 e 7 meses são dois tipos."""
    intervalos = np.diff(np.asarray(meses, dtype=float))
    distintos = sorted({float(valor) for valor in intervalos if valor > 0})
    grupos: list[list[float]] = []
    for valor in distintos:
        if grupos and valor - grupos[-1][0] <= 1.0 + 1e-9:
            grupos[-1].append(valor)
        else:
            grupos.append([valor])
    tipo = np.full(len(meses), -1, dtype=int)
    for posicao, valor in enumerate(intervalos, start=1):
        tipo[posicao] = next((k for k, grupo in enumerate(grupos) if grupo[0] - 1e-9 <= valor <= grupo[-1] + 1e-9), -1)
    return tipo, tuple((grupo[0], grupo[-1]) for grupo in grupos)


MAX_CONJUNTOS = 60
MAX_MEMBROS = 6000


def _inteiros(serie: pd.Series, nome: str) -> np.ndarray:
    valores = pd.to_numeric(serie.astype(str).str.strip().str.replace(".", "", regex=False), errors="coerce")
    if valores.isna().any():
        raise ValueError("A base Brasil tem " + nome + " não numérica: a leitura das séries foi interrompida.")
    return valores.to_numpy(dtype=float)


def _decimais(serie: pd.Series) -> np.ndarray:
    """Coordenadas com vírgula decimal; o que não é número fica ausente (NaN), com o motivo dado por quem usa."""
    return pd.to_numeric(serie.astype(str).str.strip().str.replace(",", ".", regex=False), errors="coerce").to_numpy(dtype=float)


def mes_da_competencia(competencia: str) -> int:
    """Posição em meses de uma competência AAAAMM (ano × 12 + mês − 1), a mesma da Análise de Tendência."""
    return int(competencia[:4]) * 12 + int(competencia[4:]) - 1


@dataclass(frozen=True)
class Base:
    """As séries da base Brasil de uma versão. Matrizes [território, competência] com NaN no registro ausente."""
    versao: str
    periodos: tuple[str, ...]
    meses: np.ndarray                      # posição de cada competência, em meses
    codigos: tuple[str, ...]               # código IBGE de 6 dígitos, em ordem
    nomes: tuple[str, ...]                 # "MANAUS (AM)"
    prefixos: tuple[str, ...]              # prefixo da UF de cada município ("13")
    quantidade: np.ndarray                 # [município, competência]
    populacao: np.ndarray
    latitude: np.ndarray
    longitude: np.ndarray
    estados: dict                          # prefixo → contagem estadual por competência (NaN ausente)
    brasil: np.ndarray                     # contagem nacional por competência (NaN ausente)
    indice: dict = field(repr=False, default_factory=dict)      # código → linha
    do_estado: dict = field(repr=False, default_factory=dict)   # prefixo → linhas dos municípios
    # Proposta V3 (qualquer base, seção A.3): o que era fixo da base do Brasil passa a ser dito pela base.
    origem: str = "brasil"                                      # "brasil" | "planilha"
    ancora: str | None = "06"                                   # o mês âncora da série anual; None: sem série anual
    rotulos: dict | None = None                                 # os nomes da base (None: os do Brasil)
    grupos: dict = field(repr=False, default_factory=dict)      # grupo de cima → (nome curto, nome); vazio: os estados do Brasil
    prefixo_do_id: str = "code:"                                # o prefixo dos identificadores das unidades ("code:" ou "name:")
    contagens: dict | None = None                               # o que a contagem conta, por tipo de território (None: Brasil)
    descricao: dict | None = None                               # {"base", "categoria"}: como a fonte se apresenta
    avisos: tuple = ()                                          # o que a leitura da base teve a dizer (perfil da base)

    @property
    def do_brasil(self) -> bool:
        return self.origem == "brasil"

    @property
    def anos(self) -> np.ndarray:
        """Tempo de cada competência em anos (mês real ÷ 12)."""
        return self.meses / 12.0

    def posicao(self, competencia: str) -> int:
        try:
            return self.periodos.index(str(competencia))
        except ValueError:
            # Numa planilha com um registro por ano ("202400"), a data é o ano.
            extenso = lambda periodo: periodo[:4] if periodo.endswith("00") else human_period(periodo)   # noqa: E731
            raise ValueError("Competência fora da base: " + str(competencia) + ". Escolha uma das competências com registro, de " +
                             extenso(self.periodos[0]) + " a " + extenso(self.periodos[-1]) + ".") from None

    def soma_municipal_do_estado(self, prefixo: str) -> np.ndarray:
        """Soma das contagens municipais da UF por competência (a mesma unidade da série municipal). Com município ausente na
        competência, a soma é a dos que têm registro (o número de ausentes sai em `ausentes_do_estado`)."""
        linhas = self.do_estado.get(prefixo, ())
        if not len(linhas):
            return np.full(len(self.periodos), np.nan)
        return np.nansum(self.quantidade[list(linhas)], axis=0)

    def ausentes_do_estado(self, prefixo: str) -> np.ndarray:
        linhas = self.do_estado.get(prefixo, ())
        return np.isnan(self.quantidade[list(linhas)]).sum(axis=0) if len(linhas) else np.zeros(len(self.periodos), dtype=int)


_BASES: dict[str, Base] = {}
_LOCK = threading.Lock()


def _montar(sources) -> Base:
    municipal = sources.frame("municipal")
    if municipal is None:
        raise ValueError(SEM_BASE)
    campos = FIELDS["municipal"]
    quadro = municipal[municipal[campos["category"]].astype(str).str.strip().str.upper() == TRUSTED_CATEGORY]
    if quadro.empty:
        raise ValueError("A base Brasil não tem registros de " + TRUSTED_CATEGORY + ".")
    codigos_linha = quadro[campos["territory_id"]].astype(str).str.strip()
    periodos_linha = quadro[campos["period"]].astype(str).str.strip()
    periodos = tuple(sorted(set(periodos_linha), key=mes_da_competencia))
    codigos = tuple(sorted(set(codigos_linha)))
    linha = pd.Index(codigos).get_indexer(codigos_linha)
    coluna = pd.Index(periodos).get_indexer(periodos_linha)
    if len(set(zip(linha.tolist(), coluna.tolist()))) != len(quadro):
        raise ValueError("A base Brasil tem mais de um registro para o mesmo município e competência.")
    forma = (len(codigos), len(periodos))

    def matriz(valores: np.ndarray) -> np.ndarray:
        saida = np.full(forma, np.nan)
        saida[linha, coluna] = valores
        return saida
    quantidade = matriz(_inteiros(quadro[campos["count"]], "contagem"))
    populacao = matriz(_inteiros(quadro[campos["population"]], "população"))
    latitude, longitude = matriz(_decimais(quadro[campos["latitude"]])), matriz(_decimais(quadro[campos["longitude"]]))
    # O nome do registro mais recente de cada município, com a UF do prefixo do código IBGE (como no painel).
    ordem = np.argsort(coluna, kind="stable")
    nome_de = dict(zip(codigos_linha.to_numpy()[ordem], quadro[campos["territory"]].astype(str).str.strip().to_numpy()[ordem]))
    prefixos = tuple(codigo[:2] for codigo in codigos)
    desconhecidos = sorted({prefixo for prefixo in prefixos if prefixo not in STATES})
    if desconhecidos:
        raise ValueError("Código IBGE com UF desconhecida na base Brasil: " + ", ".join(desconhecidos[:5]) + ".")
    nomes = tuple(nome_de[codigo] + " (" + STATES[prefixo][0] + ")" for codigo, prefixo in zip(codigos, prefixos))
    do_estado: dict[str, list[int]] = {}
    for posicao, prefixo in enumerate(prefixos):
        do_estado.setdefault(prefixo, []).append(posicao)

    estados: dict[str, np.ndarray] = {}
    estadual = sources.frame("state")
    if estadual is not None:
        campos_uf = FIELDS["state"]
        quadro_uf = estadual[estadual[campos_uf["category"]].astype(str).str.strip().str.upper() == TRUSTED_CATEGORY]
        contagens = _inteiros(quadro_uf[campos_uf["count"]], "contagem estadual")
        for sigla, periodo, valor in zip(quadro_uf[campos_uf["territory"]].astype(str).str.strip().str.upper(),
                                         quadro_uf[campos_uf["period"]].astype(str).str.strip(), contagens):
            prefixo = SIGLAS.get(sigla)
            if prefixo is None or periodo not in periodos:
                continue
            estados.setdefault(prefixo, np.full(len(periodos), np.nan))[periodos.index(periodo)] = valor
    brasil = np.full(len(periodos), np.nan)
    nacional = sources.frame("national")
    if nacional is not None:
        campos_br = FIELDS["national"]
        quadro_br = nacional[nacional[campos_br["category"]].astype(str).str.strip().str.upper() == TRUSTED_CATEGORY]
        for periodo, valor in zip(quadro_br[campos_br["period"]].astype(str).str.strip(),
                                  _inteiros(quadro_br[campos_br["count"]], "contagem nacional")):
            if periodo in periodos:
                brasil[periodos.index(periodo)] = valor
    for matriz_ in (quantidade, populacao, latitude, longitude, brasil, *estados.values()):
        matriz_.setflags(write=False)
    return Base(versao=sources.version, periodos=periodos, meses=np.array([mes_da_competencia(p) for p in periodos]),
                codigos=codigos, nomes=nomes, prefixos=prefixos, quantidade=quantidade, populacao=populacao,
                latitude=latitude, longitude=longitude, estados=estados, brasil=brasil,
                indice={codigo: posicao for posicao, codigo in enumerate(codigos)},
                do_estado={prefixo: tuple(linhas) for prefixo, linhas in do_estado.items()},
                ancora=mes_ancora(periodos))   # lido da própria base: junho, na base do Brasil


def base_de(sources) -> Base:
    """As séries da versão da base em uso (montadas uma vez por versão)."""
    if sources is None:
        raise ValueError(SEM_BASE)
    with _LOCK:
        guardada = _BASES.get(sources.version)
    if guardada is not None:
        return guardada
    montada = _montar(sources)
    with _LOCK:
        _BASES.clear()  # uma versão por vez
        _BASES[sources.version] = montada
    return montada


# --------------------------------------------------------------------------------------------- seleção compartilhada
@dataclass(frozen=True)
class Territorio:
    """Um território da seleção, com a série observada dele e o que ela conta."""
    id: str
    tipo: str                 # "municipio" | "estado" | "conjunto" | "brasil"
    nivel: str                # "municipios" | "estados" | "brasil"
    rotulo: str
    uf: str | None            # prefixo da UF (município e estado)
    serie: np.ndarray         # contagem por competência (NaN ausente)
    unidade: str              # o que a contagem conta
    membros: tuple = ()       # conjunto: ids dos membros
    nomes_dos_membros: tuple = ()
    linha: int | None = None  # município: a linha nas matrizes da base
    versao: int | None = None  # conjunto: a versão da composição
    ausentes: np.ndarray | None = None  # conjunto: membros sem registro em cada competência


def id_do_municipio(codigo: str, base: Base | None = None) -> str:
    """O identificador de uma unidade: "code:<código>" (na base do Brasil, o código IBGE) ou, numa planilha sem a coluna de
    código, "name:<nome>"."""
    return (base.prefixo_do_id if base is not None else "code:") + codigo


def contagem_de(base: Base, tipo: str) -> str:
    """O que a contagem conta num território do tipo pedido (município, estado, conjunto ou o todo)."""
    proprias = base.contagens or {}
    padrao = {"municipio": UNIDADE_MUNICIPIO, "estado": UNIDADE_ESTADO, "conjunto": UNIDADE_CONJUNTO, "brasil": UNIDADE_BRASIL}
    return proprias.get(tipo) or padrao[tipo]


def _codigo(base: Base, valor) -> str:
    prefixo = base.prefixo_do_id
    if not isinstance(valor, str) or not valor.startswith(prefixo) or valor[len(prefixo):] not in base.indice:
        raise ValueError(("Território fora da base Brasil: " if base.do_brasil else "Território fora da base: ") + str(valor) + ".")
    return valor[len(prefixo):]


def _prefixo(base: Base, valor) -> str:
    """A chave de um grupo de cima no pedido: na base do Brasil, o prefixo da UF ("13" ou "uf:13"); numa planilha, o valor da
    coluna de grupo."""
    if not base.do_brasil:
        if str(valor) not in base.do_estado:
            raise ValueError(rotulos(base)["grupo"].capitalize() + " sem registro na base: " + str(valor) + ".")
        return str(valor)
    texto = str(valor)[3:] if isinstance(valor, str) and valor.startswith("uf:") else str(valor)
    if texto not in STATES:
        raise ValueError("Estado sem registro: " + str(valor) + ".")
    return texto


def municipio(base: Base, codigo: str) -> Territorio:
    linha = base.indice[codigo]
    return Territorio(id=id_do_municipio(codigo, base), tipo="municipio", nivel="municipios", rotulo=base.nomes[linha],
                      uf=base.prefixos[linha] or None, serie=base.quantidade[linha], unidade=contagem_de(base, "municipio"), linha=linha)


def estado(base: Base, prefixo: str) -> Territorio:
    serie = base.estados.get(prefixo)
    if serie is None:
        if not base.do_brasil:
            raise ValueError("Esta base não tem uma contagem própria d" + rotulos(base)["o_grupo"] + ": " + rotulos(base)["o_grupo"] +
                             " não entra como unidade. Use um conjunto com " + rotulos(base)["os_unidades"] + " desse grupo.")
        raise ValueError("Estado sem registro na fonte estadual: " + STATES[prefixo][1] + ".")
    return Territorio(id="uf:" + prefixo, tipo="estado", nivel="estados", rotulo=STATES[prefixo][1] + " (" + STATES[prefixo][0] + ")",
                      uf=prefixo, serie=serie, unidade=contagem_de(base, "estado"))


def brasil(base: Base) -> Territorio:
    """O todo da base: na base do Brasil, o país, pela contagem nacional; numa planilha, a soma das unidades ("a base toda")."""
    nome = "Brasil" if base.do_brasil else rotulos(base)["todo"][:1].upper() + rotulos(base)["todo"][1:]
    return Territorio(id="br", tipo="brasil", nivel="brasil", rotulo=nome, uf=None, serie=base.brasil, unidade=contagem_de(base, "brasil"))


def _conjunto(base: Base, bruto) -> Territorio:
    if not isinstance(bruto, dict) or not isinstance(bruto.get("id"), str) or not isinstance(bruto.get("membros"), list):
        raise ValueError("Conjunto inválido: envie id, rotulo e membros.")
    membros = list(dict.fromkeys(bruto["membros"]))
    if len(membros) < 2 or len(membros) > MAX_MEMBROS:
        raise ValueError("O conjunto " + bruto["id"] + " precisa de dois ou mais territórios.")
    de_estados = [base.do_brasil and isinstance(m, str) and m.startswith("uf:") for m in membros]
    if any(de_estados) and not all(de_estados):
        raise ValueError("O conjunto " + bruto["id"] + " mistura estados e municípios: um conjunto reúne territórios do mesmo nível.")
    rotulo = str(bruto.get("rotulo") or bruto["id"]).strip() or bruto["id"]
    versao = bruto.get("versao") if isinstance(bruto.get("versao"), int) and not isinstance(bruto.get("versao"), bool) else None
    if all(de_estados) and base.do_brasil:
        partes = [estado(base, _prefixo(base, m)) for m in membros]
        unidade = "soma das contagens estaduais dos componentes (quem atua em mais de um estado conta em cada um)"
        nivel = "estados"
    else:
        partes = [municipio(base, _codigo(base, m)) for m in membros]
        unidade, nivel = contagem_de(base, "conjunto"), "municipios"
    matriz = np.vstack([parte.serie for parte in partes])
    ausentes = np.isnan(matriz).sum(axis=0)
    # A soma só existe quando todos os membros têm registro na competência: um conjunto parcial não é o conjunto.
    serie = np.where(ausentes == 0, np.nansum(matriz, axis=0), np.nan)
    return Territorio(id=bruto["id"], tipo="conjunto", nivel=nivel, rotulo=rotulo, uf=None, serie=serie, unidade=unidade,
                      membros=tuple(parte.id for parte in partes), nomes_dos_membros=tuple(parte.rotulo for parte in partes),
                      versao=versao, ausentes=ausentes)


def selecao(base: Base, opcoes: dict, com_brasil: bool = False) -> list[Territorio]:
    """Os territórios de um pedido, na ordem: municípios (pelo código), estados como unidade e conjuntos. O mesmo contrato do
    painel (`base.municipios`, `estados_unidade` e `conjuntos`); um estado como unidade (ou num conjunto de estados) e os
    municípios dele não entram juntos (RQ-DAD-30), como no painel. Com `com_brasil` (o Simulador de Cenários), `brasil: true`
    acrescenta o Brasil no fim, pela contagem nacional de médicos únicos: cada território é simulado à parte, e o Brasil nunca é
    somado aos demais."""
    bruto = ((opcoes.get("base") or {}).get("municipios") or {}) if isinstance(opcoes.get("base"), dict) else {}
    if not isinstance(bruto, dict):
        raise ValueError("Seleção inválida: envie base.municipios com todos, estados e ids.")
    linhas: set[int] = set()
    if bruto.get("todos") is True:
        linhas.update(range(len(base.codigos)))
    for prefixo in bruto.get("estados") or []:
        linhas.update(base.do_estado.get(_prefixo(base, prefixo), ()))
    for valor in bruto.get("ids") or []:
        linhas.add(base.indice[_codigo(base, valor)])
    unidades = [_prefixo(base, valor) for valor in dict.fromkeys(opcoes.get("estados_unidade") or [])]
    conjuntos_brutos = opcoes.get("conjuntos") or []
    if not isinstance(conjuntos_brutos, list) or len(conjuntos_brutos) > MAX_CONJUNTOS:
        raise ValueError("Conjuntos inválidos: envie uma lista de até " + str(MAX_CONJUNTOS) + " conjuntos.")
    conjuntos = [_conjunto(base, item) for item in conjuntos_brutos]
    if len({conjunto.id for conjunto in conjuntos}) != len(conjuntos):
        raise ValueError("Conjuntos com o mesmo id no pedido.")
    inteiros = set(unidades) | {membro[3:] for conjunto in conjuntos if conjunto.nivel == "estados" for membro in conjunto.membros}
    sobrepostos = sorted({base.prefixos[linha] for linha in linhas} & inteiros)
    if sobrepostos:
        raise ValueError("Municípios de " + ", ".join(nome_do_grupo(base, p)[1] for p in sobrepostos[:5]) + " estão na seleção junto com o "
                         "estado inteiro (como unidade ou num conjunto de estados): o estado já está na análise e não é somado "
                         "a eles (RQ-DAD-30).")
    territorios = [municipio(base, base.codigos[linha]) for linha in sorted(linhas)]
    territorios += [estado(base, prefixo) for prefixo in sorted(unidades)]
    territorios += conjuntos
    if com_brasil and opcoes.get("brasil") is True:
        territorios.append(brasil(base))
    if not territorios:
        raise ValueError("Nenhum território na seleção: escolha os territórios na Seleção de Territórios.")
    return territorios
