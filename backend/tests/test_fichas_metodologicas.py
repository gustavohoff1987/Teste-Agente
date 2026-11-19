"""As fichas metodológicas em PDF (comando de ajustes pré-publicação, AJ-03, 18/11/2026; reescritas para quem usa o Agente no
comando de correção das fichas, AJ-06, do mesmo dia).

Os dois arquivos que saem com a interface (`frontend/public/fichas/`) são PDFs válidos — a cadeia de tabelas de referências
confere, objeto a objeto —, com título (o `<title>` da fonte), idioma pt-BR, texto selecionável (fontes embutidas com o mapa
para Unicode), marcação de acessibilidade (PDF com tags), sumário navegável e os destinos nomeados de todas as seções da fonte,
inclusive as que a página abre (`SECOES_DAS_FICHAS`, em `frontend/src/fichas.ts`). E correspondem às fontes atuais
(`Docs/fichas/`): a impressão digital SHA-256 da fonte e da folha de estilo, que `scripts/gerar_fichas.py` grava nos metadados, é
a dos arquivos de hoje, com as quebras de linha em LF (como o Git os guarda). Mudou a fonte ou o estilo: gere os PDFs de novo,
com `python scripts/gerar_fichas.py`.

Desde o AJ-06, as fichas são só metodológicas, para quem usa o Agente (gestão, área técnica, pesquisa): o texto à vista não traz
as marcas de estado ("Implementado", "Não implementado", "Hipótese ou limitação"), caminhos de arquivo, rotas e campos da API,
nomes de variáveis e funções, códigos de aviso, a SPEC e os códigos das decisões e dos comandos, hashes nem o manifesto; nem as
palavras "motor", "código" e "página", o campo `criterio` e "por convenção" (a tela e as fichas dizem "limite fixo"), "jeito" (é
"forma de projetar") e o nome antigo do sinal 10 ("Mais longe da referência"). Cada seção que o comando manda ficar existe, com
o id de antes (as exportações e as versões saíram; a "Leitura rápida" é nova). A letra é a Inter em versão estática, só das
fichas (Docs/fichas/fontes/, com a licença OFL), embutida como TrueType — nenhuma fonte Type 3 —, e os arquivos de fonte do site
(frontend/src/tipografia/) ficam idênticos. Os campos que o leitor de PDF mostra nas propriedades (assunto, palavras-chave e
aplicativo) não trazem caminhos nem SHA-256. Desde o AJ-19 (rodada final da correção das fichas, do mesmo dia), o percentual que
arredonda para zero sai sem sinal ("0%") no estudo que imprime as tabelas das faixas (scripts/calibrar_simulador.py), e a Ficha B
não traz "−0%" nem "+0%".

A leitura do PDF é feita aqui, sem dependência nova e sem o gerador: pela estrutura que o Chromium escreve (tabela de referências
clássica, sem fluxos de objetos) e pela atualização incremental do gerador. Só lê arquivos versionados; nenhum dado da base.
"""
import hashlib
import html
import importlib.util
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
# AJ-06: as seções de cada ficha, na ordem (as que ficam, com o id de antes, e a "Leitura rápida", nova) e as que saíram.
SECOES = {
    "detector": ["leitura-rapida", "o-que-e", "dados", "niveis", "regua", "sinais", "condicoes", "parametros", "ajustar-criterios",
                 "estados-e-conjuntos", "mesma-queda", "aviso-da-base", "historico", "regua-da-data", "simulador", "limites"],
    "simulador": ["leitura-rapida", "o-que-e", "modos", "formas-de-projetar", "forma-escolhida", "faixa", "avaliacao",
                  "entradas-e-saidas", "intervencoes", "meta", "referencias", "conjuntos-e-brasil", "hipotese", "horizonte", "limites"],
}
SAIRAM = ("exportacoes", "versoes")
# O que não pode aparecer no texto à vista das fichas (sem diferenciar maiúsculas): o bastidor do desenvolvimento.
PROIBIDOS = [r"implementad", r"hipótese ou limitação", r"\bmotor\b", r"\bcódigos?\b", r"\bpáginas?\b", r"por convenção",
             r"\bcriterio\b", r"\bjeitos?\b", r"longe da referência", r"\bspec\b", r"proposta v3", r"divergência aprovada",
             r"\bd-[abc]\b", r"\baj-\d", r"\bcomandos?\b", r"manifesto", r"\bsha\b", r"sha-?256", r"\bhash", r"/api/",
             r"\bbackend\b", r"\bfrontend\b", r"\bdocs/", r"\bscripts/", r"\.(?:py|tsx?|md|css|html|json|pdf|csv|xlsx)\b"]
# Os arquivos de fonte do site, que as fichas deixaram de usar e que não mudam (SHA-256, com o texto em LF).
TIPOGRAFIA_DO_SITE = {
    "LICENCA-OFL.txt": "3b0a5fca3d17942cde889069889dedbbbd075e9b599968c82a95f4d944e9b345",
    "inter-latin-ext-opsz-normal.woff2": "5e6d4fe9d9f4bff8b2a2469d25ab19576bb85331e22c6ed51398e16f95d56a9c",
    "inter-latin-opsz-normal.woff2": "2c295d99e26dcf357d4d01bcf270fd6924b600c9a13dd8c363ef114f4c6976fa",
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


def texto_a_vista(fonte: str) -> str:
    """O texto que a pessoa lê: o corpo da fonte, sem as marcas do HTML."""
    corpo = re.search(r"<body\b[^>]*>(.*)</body>", fonte, re.S).group(1)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", corpo)))


@pytest.mark.parametrize("nome", list(FICHAS))
def test_so_o_metodo_para_quem_usa_o_agente(nome):
    """AJ-06: nada do bastidor do desenvolvimento no texto à vista; o vocabulário da tela ("limite fixo", "forma de projetar")."""
    fonte = FICHAS[nome]["fonte"].read_text(encoding="utf-8")
    texto = texto_a_vista(fonte)
    for proibido in PROIBIDOS:
        achado = re.search(proibido, texto, re.IGNORECASE)
        assert not achado, (nome, proibido, texto[max(0, achado.start() - 80):achado.end() + 80] if achado else "")
    # Nomes de variáveis, de funções e de códigos de aviso (com "_" ou em camelCase); os métodos (M0 a M3) são nomes, e ficam.
    assert not re.findall(r"\b[A-Za-z0-9]+_[A-Za-z0-9_]+\b", texto), nome
    assert not re.findall(r"\b[a-zà-ú]+[A-Z][A-Za-z]+\b", texto), nome
    corpo = re.search(r"<body\b[^>]*>(.*)</body>", fonte, re.S).group(1)
    for marca in ("<code", "<em", "<i>", "<i ", 'class="marca'):
        assert marca not in corpo, (nome, marca)
    # Só os caracteres que a letra das fichas tem: o latim (até U+00FF), a pontuação geral (aspas, travessões, reticências) e o
    # sinal de menos. Sem setas, sinais de comparação nem emoji, que viriam de outra fonte.
    fora = sorted({c for c in texto if ord(c) > 0xFF and not 0x2000 <= ord(c) <= 0x206F and c != "\u2212"})
    assert not fora, (nome, fora)
    assert "limite fixo" in texto if nome == "detector" else "forma de projetar" in texto, nome


@pytest.mark.parametrize("nome", list(FICHAS))
def test_as_secoes_que_ficam_e_a_abertura(nome):
    """AJ-06: as seções do comando, na ordem e com o id de antes (a "Leitura rápida" é nova; as exportações e as versões saíram),
    todas no sumário; a abertura com para quem é, a base e a data dos números, a versão do método e a data da ficha."""
    fonte = FICHAS[nome]["fonte"].read_text(encoding="utf-8")
    assert re.findall(r'<section id="([a-z0-9-]+)"', fonte) == SECOES[nome]
    assert not [secao for secao in SAIRAM if f'id="{secao}"' in fonte], nome
    sumario = re.search(r'<nav class="sumario".*?</nav>', fonte, re.S).group(0)
    assert re.findall(r'href="#([a-z0-9-]+)"', sumario) == SECOES[nome]
    capa = texto_a_vista(fonte.split("<nav", 1)[0] + "</body>")
    versao = {"detector": "DETECTOR-SINAIS/V3/1", "simulador": "SIMULADOR-CENARIOS/V3/1"}[nome]
    for trecho in (versao, "jun/2024", "18/11/2026", "médicos"):
        assert trecho in capa, (nome, trecho)


def test_os_textos_novos_do_detector_e_o_titulo_da_avaliacao_do_simulador():
    """AJ-09 e AJ-10 na Ficha A: o sinal 10 é "Perda em relação à referência" e a mesma queda é "vista de ângulos diferentes"; o
    critério do sinal 11, com a taxa do Brasil na data. AJ-07: a seção da Ficha B que a exportação da avaliação cita pelo título."""
    detector = texto_a_vista(FICHAS["detector"]["fonte"].read_text(encoding="utf-8"))
    for trecho in ("Perda em relação à referência", "A taxa do território piorou em relação à da referência: caiu mais, ou subiu menos, "
                   "que ela.", "são a mesma queda vista de ângulos diferentes", "2,01", "2,36", "500%"):
        assert trecho in detector, trecho
    simulador = FICHAS["simulador"]["fonte"].read_text(encoding="utf-8")
    titulo = html.unescape(re.sub(r"<[^>]+>", "", re.search(r'<h2 id="avaliacao-titulo">(.*?)</h2>', simulador, re.S).group(1))).strip()
    assert re.sub(r"^\d+\.\s*", "", titulo) == "A avaliação dos métodos no histórico da base", titulo


def test_o_percentual_que_arredonda_para_zero_sai_sem_sinal_e_a_ficha_b_sem_menos_zero():
    """AJ-19 (rodada final da correção das fichas, 18/11/2026): no estudo que imprime as tabelas das faixas
    (scripts/calibrar_simulador.py, as Tabelas 5 e 7 da Ficha B), o sinal vem do número já arredondado: o que arredonda para zero
    sai "0%", sem sinal (antes, −0,3 saía "−0%", e 0,4, "+0%"); os outros números não mudam. A Ficha B não traz "−0%" nem "+0%",
    e a explicação das faixas não fala mais deles."""
    especificacao = importlib.util.spec_from_file_location("calibrar_simulador", ROOT / "scripts" / "calibrar_simulador.py")
    calibrar = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(calibrar)
    assert [calibrar._pct(valor) for valor in (-0.3, -0.6, 0.4, 2)] == ["0%", "−1%", "0%", "+2%"]
    assert calibrar._pct(-0.04, 1) == "0,0%"
    assert [calibrar._pct(valor) for valor in (0, -9.2, 87.4)] == ["0%", "−9%", "+87%"]
    assert calibrar._pct(81.3, 1, False) == "81,3%" and calibrar._pct(-0.3, 0, False) == "0%"
    texto = texto_a_vista(FICHAS["simulador"]["fonte"].read_text(encoding="utf-8"))
    assert not re.search(r"[−+-]0(?:,0+)?%", texto), re.findall(r".{0,40}[−+-]0(?:,0+)?%", texto)
    assert "0% a +4% (p)" in texto and "0% a +2% (p)" in texto


def test_a_letra_estatica_das_fichas_e_a_do_site_intocada():
    """AJ-06: a folha das fichas carrega só os arquivos estáticos de Docs/fichas/fontes/ (com a licença OFL), nos pesos que
    existem em arquivo e sem itálico; os arquivos de fonte do site ficam idênticos."""
    # As regras, sem os comentários (o comentário do alto cita a pasta da fonte do site, para dizer que ela não muda).
    estilo = re.sub(r"/\*.*?\*/", "", ESTILO.read_text(encoding="utf-8"), flags=re.S)
    fontes = re.findall(r'url\("([^"]+)"\)', estilo)
    assert fontes and all(fonte.startswith("fontes/") and (FONTES / fonte).is_file() for fonte in fontes), fontes
    assert (FONTES / "fontes" / "LICENCA-OFL.txt").read_text(encoding="utf-8").count("SIL OPEN FONT LICENSE Version 1.1") == 1
    assert "tipografia" not in estilo and "woff2-variations" not in estilo and "italic" not in estilo
    declarados = {int(peso) for peso in re.findall(r"@font-face \{[^}]*font-weight: (\d+);", estilo)}
    usados = {int(peso) for peso in re.findall(r"font-weight:\s*(\d+)", estilo)}
    assert declarados == {400, 600, 700} and usados <= declarados, (declarados, usados)
    for nome, esperado in TIPOGRAFIA_DO_SITE.items():
        dados = (ROOT / "frontend" / "src" / "tipografia" / nome).read_bytes()
        assert hashlib.sha256(dados.replace(b"\r\n", b"\n") if nome.endswith(".txt") else dados).hexdigest() == esperado, nome


def test_nenhuma_fonte_type3_e_as_propriedades_sem_caminhos(ficha):
    """AJ-06: as fontes do PDF são TrueType embutidas (nenhuma Type 3); o assunto, as palavras-chave e o aplicativo, que o leitor
    de PDF mostra, sem caminhos de arquivo e sem SHA-256 (a impressão digital fica nas chaves da conferência)."""
    nome, pdf, _ = ficha
    assert not re.search(rb"/Subtype\s*/Type3", pdf.dados), (nome, "fonte Type 3")
    assert re.search(rb"/FontFile2\s+\d+\s+\d+\s+R", pdf.dados), (nome, "fonte TrueType embutida")
    info = pdf.objeto(pdf.referencia(pdf.trailer, "Info"))
    for chave in ("Subject", "Keywords", "Creator"):
        valor = campo(info, chave)
        assert valor and not re.search(r"[0-9a-f]{64}|SHA|[/\\]|\.(?:py|html|css)\b", valor), (nome, chave, valor)
