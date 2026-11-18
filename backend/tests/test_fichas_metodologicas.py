"""As fichas metodológicas em PDF (comando de ajustes pré-publicação, AJ-03, 18/11/2026).

Os dois arquivos que saem com a interface (`frontend/public/fichas/`) são PDFs válidos — a cadeia de tabelas de referências
confere, objeto a objeto —, com título (o `<title>` da fonte), idioma pt-BR, texto selecionável (fontes embutidas com o mapa
para Unicode), marcação de acessibilidade (PDF com tags), sumário navegável e os destinos nomeados de todas as seções da fonte,
inclusive as que a página abre (`SECOES_DAS_FICHAS`, em `frontend/src/fichas.ts`). E correspondem às fontes atuais
(`Docs/fichas/`): a impressão digital SHA-256 da fonte e da folha de estilo, que `scripts/gerar_fichas.py` grava nos metadados, é
a dos arquivos de hoje, com as quebras de linha em LF (como o Git os guarda). Mudou a fonte ou o estilo: gere os PDFs de novo,
com `python scripts/gerar_fichas.py`.

As fontes seguem o vocabulário da tela (AJ-05): "forma de projetar", nunca "jeito"; "limite fixo", e "por convenção" só onde a
ficha explica o valor do campo `criterio` das exportações e da API.

A leitura do PDF é feita aqui, sem dependência nova e sem o gerador: pela estrutura que o Chromium escreve (tabela de referências
clássica, sem fluxos de objetos) e pela atualização incremental do gerador. Só lê arquivos versionados; nenhum dado da base.
"""
import hashlib
import html
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FONTES = ROOT / "Docs" / "fichas"
ESTILO = FONTES / "ficha.css"
PUBLICAS = ROOT / "frontend" / "public"
FICHAS = {
    "detector": {"fonte": FONTES / "ficha_detector.html", "titulo": "Ficha metodológica A — Detector de Sinais Territoriais"},
    "simulador": {"fonte": FONTES / "ficha_simulador.html", "titulo": "Ficha metodológica B — Simulador de Cenários Territoriais"},
}


def impressao_digital(caminho: Path) -> str:
    return hashlib.sha256(caminho.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def da_pagina() -> dict:
    """Os arquivos e as seções das fichas que a página usa (frontend/src/fichas.ts)."""
    texto = (ROOT / "frontend" / "src" / "fichas.ts").read_text(encoding="utf-8")
    arquivos = dict(re.findall(r'(detector|simulador): "(fichas/[a-z-]+\.pdf)"', texto))
    secoes_ts = re.search(r"SECOES_DAS_FICHAS = \{(.*?)\} as const", texto, re.S).group(1)
    secoes = {ferramenta: set(re.findall(r'"([a-z][a-z-]*)"', corpo)) for ferramenta, corpo in re.findall(r"(detector|simulador): \{([^}]*)\}", secoes_ts)}
    return {nome: {"pdf": PUBLICAS / arquivos[nome], "secoes": secoes[nome]} for nome in FICHAS}


DA_PAGINA = da_pagina()


class Pdf:
    """O que o teste lê de um PDF: as tabelas de referências (da última à primeira, pela cadeia /Prev) e os objetos."""

    def __init__(self, dados: bytes):
        self.dados = dados
        self.tabelas = []
        posicao = int(re.findall(rb"startxref\s+(\d+)\s+%%EOF", dados)[-1])
        while posicao is not None:
            assert dados[posicao:posicao + 4] == b"xref", "a tabela de referências não está onde o PDF diz"
            fim = dados.index(b"trailer", posicao)
            partes, i, entradas = dados[posicao + 4:fim].split(), 0, {}
            while i < len(partes):
                primeiro, quantos = int(partes[i]), int(partes[i + 1])
                i += 2
                for k in range(quantos):
                    if partes[i + 2] == b"n":
                        entradas[primeiro + k] = int(partes[i])
                    i += 3
            trailer = dados[fim:dados.index(b"startxref", fim)]
            self.tabelas.append((entradas, trailer))
            anterior = re.search(rb"/Prev\s+(\d+)", trailer)
            posicao = int(anterior.group(1)) if anterior else None
        self.posicoes = {}
        for entradas, _ in reversed(self.tabelas):   # a atualização mais recente vale
            self.posicoes.update(entradas)
        self.trailer = self.tabelas[0][1]

    def objeto(self, numero: int) -> bytes:
        inicio = self.posicoes[numero]
        cabeca = re.match(rb"\s*" + str(numero).encode() + rb"\s+\d+\s+obj\b", self.dados[inicio:inicio + 40])
        assert cabeca, f"o objeto {numero} não está onde a tabela diz"
        corpo = self.dados[inicio + cabeca.end():]
        return corpo[:corpo.index(b"endobj")]

    def referencia(self, dicionario: bytes, chave: str) -> int | None:
        achado = re.search(rb"/" + chave.encode() + rb"\s+(\d+)\s+\d+\s+R", dicionario)
        return int(achado.group(1)) if achado else None


def texto_do_pdf(valor: bytes) -> str:
    """Uma cadeia de texto do PDF: em hexadecimal UTF-16BE com a marca de ordem, ou literal."""
    if valor.startswith(b"<"):
        bruto = bytes.fromhex(valor[1:-1].decode("ascii"))
        return bruto[2:].decode("utf-16-be") if bruto.startswith(b"\xfe\xff") else bruto.decode("latin-1")
    return valor[1:-1].decode("latin-1")


def campo(dicionario: bytes, chave: str) -> str | None:
    achado = re.search(rb"/" + chave.encode() + rb"\s*(<[0-9A-Fa-f]*>|\((?:\\.|[^\\)])*\))", dicionario)
    return texto_do_pdf(achado.group(1)) if achado else None


@pytest.fixture(scope="module", params=list(FICHAS))
def ficha(request):
    nome = request.param
    pdf = DA_PAGINA[nome]["pdf"]
    assert pdf.exists(), f"{pdf.relative_to(ROOT)} não existe: gere com python scripts/gerar_fichas.py"
    return nome, Pdf(pdf.read_bytes()), FICHAS[nome]["fonte"].read_text(encoding="utf-8")


def test_a_pagina_usa_os_dois_arquivos_e_secoes_que_existem_nas_fontes():
    assert {nome: dados["pdf"].name for nome, dados in DA_PAGINA.items()} == {"detector": "ficha-detector.pdf", "simulador": "ficha-simulador.pdf"}
    for nome, dados in DA_PAGINA.items():
        fonte = FICHAS[nome]["fonte"].read_text(encoding="utf-8")
        assert "o-que-e" in dados["secoes"], nome
        assert dados["secoes"] <= set(re.findall(r'<section id="([a-z0-9-]+)"', fonte)), (nome, dados["secoes"])


def test_pdf_valido_com_a_cadeia_de_referencias_inteira(ficha):
    nome, pdf, _ = ficha
    assert pdf.dados.startswith(b"%PDF-1.") and pdf.dados.rstrip().endswith(b"%%EOF"), nome
    assert len(pdf.tabelas) >= 2, "a atualização incremental com os metadados, sobre o PDF do navegador"
    for numero in pdf.posicoes:
        pdf.objeto(numero)   # cada objeto está onde a tabela diz
    assert re.search(rb"/Type\s*/Catalog", pdf.objeto(pdf.referencia(pdf.trailer, "Root")))


def test_titulo_idioma_tags_sumario_e_texto_selecionavel(ficha):
    nome, pdf, fonte = ficha
    catalogo = pdf.objeto(pdf.referencia(pdf.trailer, "Root"))
    info = pdf.objeto(pdf.referencia(pdf.trailer, "Info"))
    titulo = html.unescape(re.search(r"<title>(.*?)</title>", fonte, re.S).group(1)).strip()
    assert titulo == FICHAS[nome]["titulo"] and campo(info, "Title") == titulo, campo(info, "Title")
    assert '<html lang="pt-BR">' in fonte and campo(catalogo, "Lang") == "pt-BR", campo(catalogo, "Lang")
    assert re.search(rb"/MarkInfo\s*<<[^>]*/Marked\s+true", catalogo), "PDF com tags"
    assert pdf.referencia(catalogo, "StructTreeRoot"), "a árvore de estrutura (PDF com tags)"
    sumario = pdf.objeto(pdf.referencia(catalogo, "Outlines"))
    assert pdf.referencia(sumario, "First") and int(re.search(rb"/Count\s+(-?\d+)", sumario).group(1)) != 0, "o sumário lateral, pelos títulos"
    paginas = pdf.objeto(pdf.referencia(catalogo, "Pages"))
    assert int(re.search(rb"/Count\s+(\d+)", paginas).group(1)) >= 2, nome
    assert re.search(rb"/FontFile[23]?\s+\d+\s+\d+\s+R", pdf.dados) and b"/ToUnicode" in pdf.dados, "texto selecionável, com as fontes embutidas"
    assert '<nav class="sumario"' in fonte and all(f'href="#{secao}"' in fonte for secao in re.findall(r'<section id="([a-z0-9-]+)"', fonte)), \
        "o sumário da fonte leva a todas as seções"


def test_destinos_nomeados_de_todas_as_secoes(ficha):
    """A página abre a ficha na seção certa pelo destino nomeado ("#nameddest=<id>"): o id de cada seção da fonte."""
    nome, pdf, fonte = ficha
    catalogo = pdf.objeto(pdf.referencia(pdf.trailer, "Root"))
    destinos = set(re.findall(rb"/([A-Za-z0-9_.-]+)\s*\[\s*\d+\s+\d+\s+R", pdf.objeto(pdf.referencia(catalogo, "Dests"))))
    secoes = set(re.findall(r'<section id="([a-z0-9-]+)"', fonte))
    assert len(secoes) >= 10, (nome, secoes)
    assert {secao.encode() for secao in secoes | DA_PAGINA[nome]["secoes"]} <= destinos, sorted(destinos)


def test_o_pdf_corresponde_a_fonte_atual(ficha):
    nome, pdf, _ = ficha
    info = pdf.objeto(pdf.referencia(pdf.trailer, "Info"))
    lida = {chave: re.search(rb"/" + chave.encode() + rb"\s*\(([0-9a-f]{64})\)", info) for chave in ("FonteSHA256", "EstiloSHA256")}
    assert lida["FonteSHA256"] and lida["EstiloSHA256"], "a impressão digital nos metadados"
    assert lida["FonteSHA256"].group(1).decode() == impressao_digital(FICHAS[nome]["fonte"]), \
        f"a fonte mudou depois do PDF: gere de novo com python scripts/gerar_fichas.py {nome}"
    assert lida["EstiloSHA256"].group(1).decode() == impressao_digital(ESTILO), \
        "a folha de estilo mudou depois do PDF: gere de novo com python scripts/gerar_fichas.py"
    assert campo(info, "FonteArquivo") == FICHAS[nome]["fonte"].relative_to(ROOT).as_posix()


@pytest.mark.parametrize("nome", list(FICHAS))
def test_o_vocabulario_da_tela_nas_fontes(nome):
    """AJ-05: "forma de projetar", nunca "jeito"; "limite fixo", e "por convenção" só onde a ficha explica o campo `criterio`."""
    fonte = FICHAS[nome]["fonte"].read_text(encoding="utf-8")
    assert not re.search(r"\bjeitos?\b", fonte, re.IGNORECASE), nome
    for paragrafo in re.findall(r"<p\b[^>]*>(.*?)</p>", fonte, re.S):
        if "por convenção" in paragrafo.lower():
            assert "<code>criterio</code>" in paragrafo, paragrafo[:200]
    if nome == "detector":
        assert "limite fixo" in fonte
