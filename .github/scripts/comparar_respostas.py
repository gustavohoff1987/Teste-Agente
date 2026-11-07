"""Comparação das respostas das análises no job "conteiner" do CI (medir_conteiner.py), desde 07/11/2026. Não tem efeitos ao
ser importado: os testes usam este módulo sem Docker e sem a base.

Cada análise feita pelo HTTP do contêiner é comparada com duas referências em processo (TestClient do backend):
- na própria imagem, a comparação é exata (bit a bit). O código e os dados do commit, montados só para leitura em /src, rodam
  com o Python, as bibliotecas e a libm da imagem (comando_da_referencia_na_imagem e referencia_na_imagem.py). Isso confere o
  empacotamento (o código e os dados que a imagem leva em /app são os do commit) sem depender do sistema do runner.
- no runner, a mesma referência de antes (o ambiente dos testes com dados reais) precisa ser equivalente: é exata em chaves,
  textos, inteiros, booleanos, nulos, ordem e tamanhos; nos números decimais, aceita diferença relativa de até
  TOLERANCIA_RELATIVA (1e-9, 1 mm em 1.000 km). Assim, o ambiente dos testes e o da produção têm de tomar as mesmas decisões.

Motivo (Docs/implantacao/RELATORIO_IMPLANTACAO.md, 07/11/2026). No Ubuntu 26.04 do runner, a glibc é a da variante amd64v3,
compilada com FMA; na imagem (Debian trixie), é a compilação genérica. A hypot da glibc escolhe o algoritmo na compilação
(__FP_FAST_FMA em sysdeps/ieee754/dbl-64/e_hypot.c), e as duas versões diferem no último bit em cerca de 13% das entradas. A
geodésica do PROJ normaliza senos e cossenos com a hypot, e as distâncias passam a diferir em até 2,3e-12 km. Os valores
exibidos e as decisões (a referência mais próxima, os empates, os limiares) não mudam.
"""
import base64
import math
import os
import platform
import sys
from pathlib import PurePosixPath

VOLATEIS = {"result_id", "created_at"}
TOLERANCIA_RELATIVA = 1e-9
RAIZ_NA_IMAGEM = "/src"
SCRIPT_DA_REFERENCIA = RAIZ_NA_IMAGEM + "/.github/scripts/referencia_na_imagem.py"
EXEMPLOS = 5


def normalizar(valor):
    """A resposta sem os campos voláteis (identificador do resultado e hora de criação), em qualquer nível."""
    if isinstance(valor, dict):
        return {chave: normalizar(item) for chave, item in valor.items() if chave not in VOLATEIS}
    if isinstance(valor, list):
        return [normalizar(item) for item in valor]
    return valor


def identicas(a, b) -> bool:
    """Igualdade exata das respostas normalizadas: uma diferença no último bit de um número já as distingue."""
    return normalizar(a) == normalizar(b)


def _numero(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _anotar(resumo: dict, lista: str, texto: str):
    resumo[lista + "_total"] += 1
    if len(resumo[lista]) < EXEMPLOS:
        resumo[lista].append(texto[:300])


def _comparar(a, b, caminho: str, tolerancia: float, resumo: dict):
    if isinstance(a, dict) and isinstance(b, dict):
        if a.keys() != b.keys():
            _anotar(resumo, "outras_diferencas", f"{caminho}: chaves só de um lado {sorted(set(a) ^ set(b))[:EXEMPLOS]}")
        for chave in sorted(a.keys() & b.keys()):
            _comparar(a[chave], b[chave], f"{caminho}.{chave}", tolerancia, resumo)
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            _anotar(resumo, "outras_diferencas", f"{caminho}: {len(a)} itens × {len(b)}")
        for indice, (x, y) in enumerate(zip(a, b)):
            _comparar(x, y, f"{caminho}[{indice}]", tolerancia, resumo)
    elif _numero(a) and _numero(b) and (isinstance(a, float) or isinstance(b, float)):
        if a == b:
            return
        if not (math.isfinite(a) and math.isfinite(b)):
            _anotar(resumo, "outras_diferencas", f"{caminho}: {a!r} × {b!r}")
            return
        relativa = abs(a - b) / max(abs(a), abs(b))
        resumo["numeros_diferentes"] += 1
        resumo["maior_diferenca_relativa"] = max(resumo["maior_diferenca_relativa"], relativa)
        if relativa > tolerancia:
            _anotar(resumo, "fora_da_tolerancia", f"{caminho}: {a!r} × {b!r} (relativa {relativa:.1e})")
    elif type(a) is not type(b) or a != b:
        _anotar(resumo, "outras_diferencas", f"{caminho}: {a!r} × {b!r}")


def comparar_com_tolerancia(a, b, tolerancia: float = TOLERANCIA_RELATIVA) -> dict:
    """Equivalência entre as respostas de dois ambientes. É exata em tudo, menos nos números decimais, que podem diferir até
    a tolerância relativa. Devolve se são equivalentes, quantos números diferem, a maior diferença relativa e até
    EXEMPLOS caminhos de cada tipo de diferença."""
    resumo = {"equivalente": True, "numeros_diferentes": 0, "maior_diferenca_relativa": 0.0,
              "fora_da_tolerancia": [], "fora_da_tolerancia_total": 0, "outras_diferencas": [], "outras_diferencas_total": 0}
    _comparar(normalizar(a), normalizar(b), "$", tolerancia, resumo)
    resumo["equivalente"] = not resumo["fora_da_tolerancia_total"] and not resumo["outras_diferencas_total"]
    return resumo


def pedidos_para_json(pedidos) -> list[dict]:
    """Os pedidos (família, rota, formulário, arquivos, usada pela página) no formato que a referência na imagem recebe
    pela entrada padrão; o conteúdo dos arquivos vai em base64."""
    return [{"familia": familia, "rota": rota, "formulario": formulario,
             "arquivos": None if not arquivos else {campo: [nome, base64.b64encode(conteudo).decode("ascii")]
                                                     for campo, (nome, conteudo) in arquivos.items()}}
            for familia, rota, formulario, arquivos, _pagina in pedidos]


def arquivos_de_json(arquivos):
    """O inverso de pedidos_para_json para os arquivos: {campo: (nome, bytes)}, ou None."""
    return None if not arquivos else {campo: (nome, base64.b64decode(conteudo)) for campo, (nome, conteudo) in arquivos.items()}


def comando_da_referencia_na_imagem(imagem: str, raiz) -> list[str]:
    """O docker run da referência na imagem: a mesma imagem do contêiner, o commit montado só para leitura em /src, sem rede
    e sem a chave do Gemini. O código e os dados vêm de /src, e não de /app."""
    return ["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "python",
            "-e", "GEMINI_API_KEY=", "-e", "ADT_AQUECIMENTO=0", "-e", "PYTHONDONTWRITEBYTECODE=1",
            "-v", f"{raiz}:{RAIZ_NA_IMAGEM}:ro", imagem, SCRIPT_DA_REFERENCIA]


def codigo_do_commit(arquivo_main: str) -> bool:
    """O main.py importado pela referência na imagem é o do commit (/src/backend), e não o da imagem (/app/backend)."""
    return PurePosixPath(arquivo_main).parent == PurePosixPath(RAIZ_NA_IMAGEM, "backend")


def ambiente(arquivo_main: str | None = None) -> dict:
    """O ambiente de uma referência: o sistema, a glibc, o Python, a libm carregada e o main.py usado."""
    libm = []
    try:
        with open("/proc/self/maps", encoding="utf-8") as mapas:
            libm = sorted({linha.split()[-1] for linha in mapas if "libm.so" in linha})
    except OSError:
        pass
    glibc = os.confstr("CS_GNU_LIBC_VERSION") if hasattr(os, "confstr") and "CS_GNU_LIBC_VERSION" in os.confstr_names else ""
    return {"sistema": platform.platform(), "glibc": glibc, "python": sys.version.split()[0], "libm": libm,
            "main": arquivo_main}
