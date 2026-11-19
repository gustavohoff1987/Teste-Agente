"""Os produtos prontos da imagem (PA-01, 19/11/2026; Docs/OTIMIZACAO_LATENCIA.md, U12).

O que depende só da base versionada e do código, e até então se calculava na partida (o exame da base que o aquecimento faz) ou
no primeiro uso das ferramentas (a base das séries, as calibrações do Detector, as retroprojeções do Simulador e os quadros
comparativos da data padrão), é preparado uma vez, na construção da imagem (Dockerfile, logo depois do COPY backend/), e
carregado no aquecimento nos mesmos guardados de memória que o código já usa (GUARDADOS), em vez de calculado.

- gerar(pasta): só na construção. Pelo próprio app, faz o mesmo exame da base do aquecimento e o primeiro Detector e o primeiro
  Simulador com a base do Brasil e os valores padrão; grava o conteúdo dos guardados num arquivo e a chave num JSON.
- carregar(pasta): no aquecimento. Só com a mesma chave (a versão da base verificada pelo manifesto, a camada de coordenadas, o
  código do backend e as versões do Python e das bibliotecas) e com o arquivo íntegro (tamanho e SHA-256 conferidos antes da
  leitura). Sem o arquivo, com outra chave ou com ADT_BRASIL_CACHE_MAX_MB=0, nada é carregado e tudo é calculado como antes.
  Nada é gravado em execução, e a conferência da base pelo manifesto continua no aquecimento e a cada requisição.

Formato: pickle, o mesmo da memória entre requisições (request_memo._store). Os produtos são quadros do pandas e estruturas com
matrizes do numpy; um formato que não executa código ao ser lido pediria um conversor para cada produto (ou o pyarrow, que a
imagem não tem), com o risco de mudar tipos. Por isso o arquivo é gerado na mesma construção, fica numa pasta que o usuário do
serviço (10001) não grava e só é lido com a chave certa e o SHA-256 conferido. O pickle não guarda a marca de somente leitura
das matrizes: a chave leva a marca de cada uma, reaplicada na carga.

Uso na construção: python -m produtos_prontos gerar /app/prontos
"""
from __future__ import annotations

import collections
import dataclasses
import hashlib
import importlib
import importlib.metadata
import json
import os
import pickle
import platform
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

FORMATO = 1
BACKEND = Path(__file__).resolve().parent
PASTA = BACKEND.parent / "prontos"   # /app/prontos na imagem; no repositório, ausente (o cálculo de sempre)
ARQUIVO_DA_CHAVE, ARQUIVO_DOS_PRODUTOS = "chave.json", "produtos.pickle"
# Os guardados de memória que o exame da base e o primeiro uso das ferramentas preenchem, todos por versão da base:
# (módulo, guardado, trava do guardado no módulo).
GUARDADOS = (
    ("main", "_BRAZIL_FRAMES", "_BRAZIL_FRAMES_LOCK"),                 # os quadros das fontes interpretados
    ("request_memo", "_SHARED", "_SHARED_LOCK"),                       # as derivações por versão (perfis, pré-exame, catálogo…)
    ("territorial_levels", "_CACHE", "_LOCK"),                         # o índice da fonte municipal
    ("brazil_catalog_profile", "_VERIFIED", None),                     # as conferências do perfil da fonte
    ("series_brasil", "_BASES", "_LOCK"),                              # a base das séries das ferramentas
    ("detector", "_CALIBRACOES", "_LOCK"),                             # a calibração municipal
    ("detector", "_BASES_DOS_ESTADOS", "_LOCK"),
    ("detector", "_CALIBRACOES_DOS_ESTADOS", "_LOCK"),
    ("detector", "_FALTAS", "_LOCK"),
    ("simulador", "_RETROS", "_LOCK"),                                 # as retroprojeções (municípios e estados)
    ("comparativos", "_COMPARAVEL", "_LOCK"),
    ("comparativos", "_QUADROS", "_LOCK"),
    ("comparativos", "_TAXAS", "_LOCK"),
    ("comparativos", "_REGUAS", "_LOCK"),
)
# O primeiro uso das ferramentas com a base do Brasil e os valores padrão, como a página pede: o perfil da base e a lista do
# Detector com todos os municípios; o Simulador no modo simples (um município, o cenário e a persistência, 2 anos à frente).
PRIMEIROS_USOS = (
    ("/api/detector", {"base": {"municipios": {"todos": True}}, "perfil": True}),
    ("/api/detector", {"base": {"municipios": {"todos": True}}}),
    ("/api/simulador", {"base": {"municipios": {"todos": False, "estados": [], "ids": ["code:420020"]}}, "horizonte": "202606",
                        "cenarios": [{"id": "c1", "nome": "Cenário 1", "metodo": "padrao"},
                                     {"id": "m0", "nome": "Persistência (referência)", "metodo": "M0"}]}),
)


def _resumo_do_codigo() -> str:
    """SHA-256 do código do backend (os .py, fora dos testes): outro código, outros produtos."""
    resumo = hashlib.sha256()
    for arquivo in sorted(p for p in BACKEND.rglob("*.py") if "tests" not in p.relative_to(BACKEND).parts and
                          "__pycache__" not in p.parts):
        resumo.update(arquivo.relative_to(BACKEND).as_posix().encode("utf-8") + b"\0" + arquivo.read_bytes() + b"\0")
    return resumo.hexdigest()


def _resumo_das_bibliotecas() -> str:
    """SHA-256 da versão do Python, da arquitetura e das versões de todas as bibliotecas instaladas."""
    instaladas = sorted({f"{(d.metadata['Name'] or '').lower()}=={d.version}" for d in importlib.metadata.distributions()})
    texto = "\n".join([sys.version, platform.machine(), *instaladas])
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def chave(integridade: dict) -> dict:
    """A chave dos produtos: a versão da base verificada pelo manifesto, a camada de coordenadas, o código e as bibliotecas."""
    import series_brasil
    return {"formato": FORMATO, "base": integridade.get("versao"), "integridade": integridade.get("integridade"),
            "camada_de_coordenadas": series_brasil._camada_de_coordenadas(), "codigo": _resumo_do_codigo(),
            "bibliotecas": _resumo_das_bibliotecas()}


def _modulo(nome: str):
    return sys.modules.get(nome) or importlib.import_module(nome)


def _trava(modulo, nome_da_trava):
    if nome_da_trava is None:
        return _SemTrava()
    return getattr(modulo, nome_da_trava)


class _SemTrava:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _matrizes(valor, vistos: set):
    """As matrizes do numpy dos produtos, sempre na mesma ordem (dicionários na ordem de inserção, que o pickle mantém; campos
    das dataclasses na ordem da definição). Os quadros do pandas, os textos e os bytes ficam de fora."""
    if isinstance(valor, (str, bytes, bytearray, int, float, complex, bool, type(None), pd.DataFrame, pd.Series, pd.Index,
                          np.generic)):
        return
    if id(valor) in vistos:
        return
    vistos.add(id(valor))
    if isinstance(valor, np.ndarray):
        yield valor
    elif isinstance(valor, dict):
        for chave_do_item, item in valor.items():
            yield from _matrizes(chave_do_item, vistos)
            yield from _matrizes(item, vistos)
    elif isinstance(valor, (list, tuple)):
        for item in valor:
            yield from _matrizes(item, vistos)
    elif dataclasses.is_dataclass(valor) and not isinstance(valor, type):
        for campo in dataclasses.fields(valor):
            yield from _matrizes(getattr(valor, campo.name), vistos)
    elif hasattr(valor, "__dict__") and not isinstance(valor, type):
        for item in vars(valor).values():
            yield from _matrizes(item, vistos)


def _retrato() -> dict:
    """O conteúdo atual dos guardados, para gravar (os próprios objetos: um pickle só mantém as referências compartilhadas)."""
    retrato = {}
    for nome_do_modulo, nome, nome_da_trava in GUARDADOS:
        modulo = _modulo(nome_do_modulo)
        with _trava(modulo, nome_da_trava):
            guardado = getattr(modulo, nome)
            retrato[nome_do_modulo + "." + nome] = guardado.copy()
    return retrato


def limpar():
    """Esvazia todos os guardados (antes de gerar e nos testes): o processo volta ao estado da partida sem aquecimento."""
    for nome_do_modulo, nome, nome_da_trava in GUARDADOS:
        modulo = _modulo(nome_do_modulo)
        with _trava(modulo, nome_da_trava):
            getattr(modulo, nome).clear()
    import request_memo
    request_memo.clear_shared()


def _restaurar(produtos: dict, limite_dos_quadros: int):
    """Os produtos nos guardados, com os mesmos limites do cálculo: só os quadros que caberiam no guardado (ADT_BRASIL_CACHE_MAX_MB)
    e as derivações dentro do teto da memória entre requisições."""
    import request_memo
    quadros = produtos["main._BRAZIL_FRAMES"]
    for chave_do_quadro in [c for c, quadro in quadros.items() if quadro.memory_usage(deep=True).sum() > limite_dos_quadros]:
        del quadros[chave_do_quadro]
    if sum(tamanho for _, tamanho in produtos["request_memo._SHARED"].values()) > request_memo.SHARED_LIMIT_BYTES:
        produtos["request_memo._SHARED"] = collections.OrderedDict()
    for nome_do_modulo, nome, nome_da_trava in GUARDADOS:
        modulo = _modulo(nome_do_modulo)
        with _trava(modulo, nome_da_trava):
            guardado = getattr(modulo, nome)
            guardado.clear()
            guardado.update(produtos[nome_do_modulo + "." + nome])
            if nome_do_modulo == "request_memo":
                modulo._shared_bytes = sum(tamanho for _, tamanho in guardado.values())


def _desfecho(estado: str, inicio: float, **detalhes) -> dict:
    return {"estado": estado, "segundos": round(time.monotonic() - inicio, 3), **detalhes}


def carregar(pasta: Path | str | None = None, limite_dos_quadros: int | None = None) -> dict:
    """Carrega os produtos prontos nos guardados, se valerem para esta base, este código e estas bibliotecas. Nunca levanta: um
    problema qualquer equivale a não ter os produtos (o cálculo de sempre). Devolve o desfecho: carregados, ausentes,
    chave_diferente, arquivo_diferente, desligados ou erro, com a duração."""
    inicio = time.monotonic()
    pasta = Path(pasta) if pasta is not None else PASTA
    if limite_dos_quadros is None:
        import main
        limite_dos_quadros = main._brazil_cache_limit_bytes()
    if limite_dos_quadros <= 0:
        return _desfecho("desligados", inicio, motivo="ADT_BRASIL_CACHE_MAX_MB=0: nada é reaproveitado")
    restaurou = False
    try:
        arquivo_da_chave = pasta / ARQUIVO_DA_CHAVE
        if not arquivo_da_chave.is_file():
            return _desfecho("ausentes", inicio)
        gravada = json.loads(arquivo_da_chave.read_text(encoding="utf-8"))
        from brazil_data import load_brazil_sources
        _, integridade = load_brazil_sources()   # a mesma conferência pelo manifesto do exame da base
        if integridade.get("integridade") != "verificada":
            return _desfecho("chave_diferente", inicio, diferencas=["integridade"])
        atual, anterior = chave(integridade), gravada.get("chave") or {}
        diferencas = sorted(nome for nome in set(atual) | set(anterior) if atual.get(nome) != anterior.get(nome))
        if diferencas:
            return _desfecho("chave_diferente", inicio, diferencas=diferencas)
        conteudo = (pasta / ARQUIVO_DOS_PRODUTOS).read_bytes()
        if len(conteudo) != gravada.get("bytes") or hashlib.sha256(conteudo).hexdigest() != gravada.get("sha256"):
            return _desfecho("arquivo_diferente", inicio)
        produtos = pickle.loads(conteudo)
        nomes = {nome_do_modulo + "." + nome for nome_do_modulo, nome, _ in GUARDADOS}
        if not isinstance(produtos, dict) or set(produtos) != nomes:
            return _desfecho("arquivo_diferente", inicio)
        matrizes, marcas = list(_matrizes(produtos, set())), gravada.get("matrizes", "")
        if len(matrizes) != len(marcas):
            return _desfecho("arquivo_diferente", inicio)
        for matriz, marca in zip(matrizes, marcas):
            if marca == "0":
                matriz.setflags(write=False)
        restaurou = True
        _restaurar(produtos, limite_dos_quadros)
        return _desfecho("carregados", inicio, guardados={nome: len(valor) for nome, valor in produtos.items()},
                         bytes=len(conteudo))
    except Exception as exc:  # noqa: BLE001 - sem os produtos, o cálculo de sempre
        if restaurou:
            limpar()
        return _desfecho("erro", inicio, motivo=type(exc).__name__)


def gerar(pasta: Path | str, primeiros_usos: tuple = PRIMEIROS_USOS) -> dict:
    """Só na construção da imagem: os produtos da base em uso, pelo próprio app (o exame do aquecimento e os primeiros usos das
    ferramentas, PRIMEIROS_USOS; os testes passam os de uma base sintética), gravados em `pasta` com a chave. Começa de
    guardados vazios e confere cada resposta."""
    os.environ["GEMINI_API_KEY"] = ""   # nada vai ao provedor de IA
    import main
    from brazil_data import load_brazil_sources
    from fastapi.testclient import TestClient
    pasta = Path(pasta)
    limpar()
    tempos = {}
    inicio = time.monotonic()
    status = main._examinar_a_base()
    tempos["exame_da_base_s"] = round(time.monotonic() - inicio, 3)
    if status != 200 or not main._BRAZIL_FRAMES:
        raise RuntimeError(f"o exame da base respondeu {status} sem guardar os quadros (ADT_BRASIL_CACHE_MAX_MB?)")
    cliente = TestClient(main.app)
    for rota, opcoes in primeiros_usos:
        inicio = time.monotonic()
        resposta = cliente.post(rota, data={"dataset": "brazil", "scope": "municipal", "dataset_version": "", "context_revision": "0",
                                            "sheet": "", "mapping": "{}", "options": json.dumps(opcoes)})
        if resposta.status_code != 200:
            raise RuntimeError(f"{rota} respondeu {resposta.status_code}: {resposta.text[:300]}")
        tempos.setdefault(rota, []).append(round(time.monotonic() - inicio, 3))
    produtos = _retrato()
    conteudo = pickle.dumps(produtos, protocol=pickle.HIGHEST_PROTOCOL)
    marcas = "".join("1" if matriz.flags.writeable else "0" for matriz in _matrizes(produtos, set()))
    _, integridade = load_brazil_sources()
    registro = {"formato": FORMATO, "chave": chave(integridade), "bytes": len(conteudo),
                "sha256": hashlib.sha256(conteudo).hexdigest(), "matrizes": marcas,
                "guardados": {nome: len(valor) for nome, valor in produtos.items()}}
    pasta.mkdir(parents=True, exist_ok=True)
    (pasta / ARQUIVO_DOS_PRODUTOS).write_bytes(conteudo)
    (pasta / ARQUIVO_DA_CHAVE).write_text(json.dumps(registro, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return {**registro, "tempos": tempos}


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "gerar":
        print(__doc__)
        sys.exit(2)
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8", errors="replace")
    feito = gerar(sys.argv[2])
    print("Produtos prontos gerados:", json.dumps({chave_: valor for chave_, valor in feito.items() if chave_ != "matrizes"},
                                                   ensure_ascii=False))
