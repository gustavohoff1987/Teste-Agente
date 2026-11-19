"""Gera as fichas metodológicas em PDF do Detector de Sinais e do Simulador de Cenários (comando de ajustes pré-publicação, AJ-03,
18/11/2026), a partir das fontes versionadas em Docs/fichas/ (HTML, com a folha de estilo ficha.css). Ferramenta de desenvolvimento,
fora do produto e do CI: os PDFs gerados são versionados em frontend/public/fichas/ e saem com os arquivos estáticos da interface.

Uso, da raiz do repositório (com o Playwright e o navegador dele instalados, como nos roteiros de navegador):
    python scripts/gerar_fichas.py              # gera as duas fichas
    python scripts/gerar_fichas.py --conferir   # só confere se os PDFs correspondem às fontes atuais (não gera nada)

O que o PDF tem:
- título (o <title> da fonte), idioma pt-BR, texto selecionável, marcação de acessibilidade (PDF com tags), o sumário navegável
  (os links do sumário da fonte e o sumário lateral do PDF, pelos títulos) e os destinos nomeados das seções (o id de cada seção
  na fonte), que a página usa para abrir a ficha no ponto certo ("#nameddest=…");
- a **impressão digital** (SHA-256) da fonte e da folha de estilo, gravada nos metadados do documento (/FonteSHA256 e
  /EstiloSHA256, com o arquivo da fonte em /FonteArquivo). O teste backend/tests/test_fichas_metodologicas.py confere que cada PDF
  corresponde à fonte atual: mudou a fonte, gere o PDF de novo com este script. As quebras de linha entram na conta como LF (o Git
  pode deixar a cópia local em CRLF);
- desde o AJ-06 (comando de correção das fichas, 18/11/2026), os campos que o leitor de PDF mostra nas propriedades — o assunto,
  as palavras-chave e o aplicativo — dizem o que a ficha é, para quem usa o Agente, sem caminhos e sem SHA-256; e a letra é a
  Inter estática das fichas (Docs/fichas/fontes/), embutida como TrueType (com a variável do site, o Chromium a embutia como
  Type 3).

Sem dependência nova: o Playwright é o dos roteiros de navegador; os metadados entram numa atualização incremental do PDF, escrita
aqui mesmo. Nada vai à rede, e nada da base de dados entra nas fichas além dos números que elas citam.
"""
import argparse
import hashlib
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FONTES = ROOT / "Docs" / "fichas"
ESTILO = FONTES / "ficha.css"
DESTINO = ROOT / "frontend" / "public" / "fichas"
FICHAS = {
    "detector": {"fonte": FONTES / "ficha_detector.html", "pdf": DESTINO / "ficha-detector.pdf",
                 "rodape": "Ficha metodológica A — Detector de Sinais Territoriais"},
    "simulador": {"fonte": FONTES / "ficha_simulador.html", "pdf": DESTINO / "ficha-simulador.pdf",
                  "rodape": "Ficha metodológica B — Simulador de Cenários Territoriais"},
}
AUTOR = "Agente Diagnóstico Territorial da Força de Trabalho na Saúde"
# O que o leitor de PDF mostra como aplicativo: o navegador que fez o PDF, sem caminho de arquivo (AJ-06).
APLICATIVO = "Chromium, a partir da fonte em HTML"
IDIOMA = "pt-BR"


def impressao_digital(caminho: Path) -> str:
    """O SHA-256 de uma fonte, com as quebras de linha em LF (como o Git guarda o arquivo)."""
    return hashlib.sha256(caminho.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _texto_pdf(valor: str) -> bytes:
    """Uma cadeia de texto do PDF em UTF-16BE com a marca de ordem, em hexadecimal: vale para qualquer letra."""
    return b"<FEFF" + valor.encode("utf-16-be").hex().upper().encode("ascii") + b">"


def _ultimo_trailer(pdf: bytes) -> tuple[dict, int]:
    """O dicionário do último trailer (tabela de referências clássica, como o Chromium escreve) e a posição da tabela dele."""
    inicio = int(re.findall(rb"startxref\s+(\d+)\s+%%EOF", pdf)[-1])
    if not pdf[inicio:inicio + 4] == b"xref":
        raise SystemExit("O PDF não tem a tabela de referências clássica que este script sabe atualizar.")
    trailer = pdf[pdf.index(b"trailer", inicio):]
    corpo = trailer[trailer.index(b"<<"):trailer.index(b"startxref")]
    campos = {"Size": int(re.search(rb"/Size\s+(\d+)", corpo).group(1)),
              "Root": re.search(rb"/Root\s+(\d+\s+\d+\s+R)", corpo).group(1),
              "Info": (re.search(rb"/Info\s+(\d+\s+\d+\s+R)", corpo) or [None, None])[1],
              "ID": (re.search(rb"/ID\s*(\[[^\]]*\])", corpo) or [None, None])[1]}
    return campos, inicio


def _objeto(pdf: bytes, referencia: bytes) -> bytes:
    """O corpo da última definição de um objeto ("12 0 R"), entre "obj" e "endobj"."""
    numero, geracao = referencia.split()[:2]
    achados = list(re.finditer(rb"(?<![0-9])" + numero + rb"\s+" + geracao + rb"\s+obj\b(.*?)endobj", pdf, re.S))
    if not achados:
        raise SystemExit("Objeto não encontrado no PDF: " + referencia.decode())
    return achados[-1].group(1).strip()


def gravar_metadados(pdf: bytes, titulo: str, assunto: str, palavras: str, fonte: str, impressao_da_fonte: str,
                     impressao_do_estilo: str) -> bytes:
    """Acrescenta ao PDF uma atualização incremental com os metadados do documento (título, autor, assunto, palavras-chave, o
    aplicativo e as impressões digitais da fonte e do estilo) e, quando falta, o idioma no catálogo. O conteúdo das páginas não
    muda."""
    trailer, tabela_anterior = _ultimo_trailer(pdf)
    proximo = trailer["Size"]
    novos = []   # (número, corpo)
    info = {"Title": titulo, "Author": AUTOR, "Subject": assunto, "Keywords": palavras, "Creator": APLICATIVO, "FonteArquivo": fonte}
    corpo_info = b"<< " + b" ".join(b"/" + chave.encode("ascii") + b" " + _texto_pdf(valor) for chave, valor in info.items())
    corpo_info += b" /FonteSHA256 (" + impressao_da_fonte.encode("ascii") + b") /EstiloSHA256 (" + impressao_do_estilo.encode("ascii") + b")"
    if trailer["Info"]:
        anterior = _objeto(pdf, trailer["Info"])
        for chave in (b"Producer", b"CreationDate", b"ModDate"):
            achado = re.search(rb"/" + chave + rb"\s*(\([^)]*\)|<[^>]*>)", anterior)
            if achado:
                corpo_info += b" /" + chave + b" " + achado.group(1)
        numero_info = int(trailer["Info"].split()[0])
    else:
        numero_info, proximo = proximo, proximo + 1
    novos.append((numero_info, corpo_info + b" >>"))
    catalogo = _objeto(pdf, trailer["Root"])
    if b"/Lang" not in catalogo:
        fim = catalogo.rindex(b">>")
        novos.append((int(trailer["Root"].split()[0]), catalogo[:fim] + b" /Lang " + _texto_pdf(IDIOMA) + b" " + catalogo[fim:]))
    saida = bytearray(pdf if pdf.endswith(b"\n") else pdf + b"\n")
    posicoes = {}
    for numero, corpo in novos:
        posicoes[numero] = len(saida)
        saida += str(numero).encode() + b" 0 obj\n" + corpo + b"\nendobj\n"
    tabela = len(saida)
    saida += b"xref\n"
    for numero in sorted(posicoes):
        saida += str(numero).encode() + b" 1\n" + ("%010d 00000 n \n" % posicoes[numero]).encode()
    saida += (b"trailer\n<< /Size " + str(max(proximo, max(posicoes) + 1)).encode() + b" /Root " + trailer["Root"] + b" /Info " +
              str(numero_info).encode() + b" 0 R" + (b" /ID " + trailer["ID"] if trailer["ID"] else b"") + b" /Prev " +
              str(tabela_anterior).encode() + b" >>\nstartxref\n" + str(tabela).encode() + b"\n%%EOF\n")
    return bytes(saida)


def metadados(pdf: bytes) -> dict:
    """Os metadados que este script grava, lidos da última definição do dicionário de informações (para a conferência)."""
    trailer, _ = _ultimo_trailer(pdf)
    info = _objeto(pdf, trailer["Info"])
    saida = {}
    for chave in ("FonteSHA256", "EstiloSHA256"):
        achado = re.search(rb"/" + chave.encode() + rb"\s*\(([0-9a-f]{64})\)", info)
        saida[chave] = achado.group(1).decode() if achado else None
    titulo = re.search(rb"/Title\s*<FEFF([0-9A-Fa-f]*)>", info)
    saida["Title"] = bytes.fromhex(titulo.group(1).decode()).decode("utf-16-be") if titulo else None
    return saida


def conferir() -> list[str]:
    """Os PDFs que não correspondem à fonte ou ao estilo atuais (vazio: todos em dia)."""
    problemas = []
    estilo = impressao_digital(ESTILO)
    for nome, ficha in FICHAS.items():
        if not ficha["pdf"].exists():
            problemas.append(nome + ": o PDF não existe")
            continue
        lidos = metadados(ficha["pdf"].read_bytes())
        if lidos["FonteSHA256"] != impressao_digital(ficha["fonte"]) or lidos["EstiloSHA256"] != estilo:
            problemas.append(nome + ": o PDF não corresponde à fonte atual")
    return problemas


def gerar(nomes: list[str]) -> None:
    from playwright.sync_api import sync_playwright   # só aqui: a conferência não precisa do navegador

    DESTINO.mkdir(parents=True, exist_ok=True)
    estilo = impressao_digital(ESTILO)
    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True, channel=os.getenv("ADT_BROWSER_CHANNEL") or None)
        pagina = navegador.new_page()
        for nome in nomes:
            ficha = FICHAS[nome]
            fonte = ficha["fonte"]
            pagina.goto(fonte.resolve().as_uri())
            pagina.evaluate("document.fonts.ready")
            titulo = pagina.title()
            rodape = ('<div style="width:100%;padding:0 16mm;display:flex;justify-content:space-between;font-family:Arial,sans-serif;'
                      'font-size:7.5pt;color:#52606d;"><span>' + ficha["rodape"] + '</span><span>página <span class="pageNumber"></span> '
                      'de <span class="totalPages"></span></span></div>')
            with tempfile.TemporaryDirectory(prefix="adt-fichas-") as pasta:
                provisorio = Path(pasta) / "ficha.pdf"
                pagina.pdf(path=str(provisorio), format="A4", print_background=True, prefer_css_page_size=True, tagged=True, outline=True,
                           display_header_footer=True, header_template="<span></span>", footer_template=rodape)
                bruto = provisorio.read_bytes()
            relativa = fonte.relative_to(ROOT).as_posix()
            impressao = impressao_digital(fonte)
            ferramenta = titulo.split(" — ")[-1]
            assunto = (titulo + ". Para quem usa o Agente: o que a ferramenta mede, como mede, com que critérios e limites, como "
                       "ler o resultado e o que ele não diz.")
            palavras = "ficha metodológica; " + ferramenta + "; método; Agente Diagnóstico Territorial"
            ficha["pdf"].write_bytes(gravar_metadados(bruto, titulo, assunto, palavras, relativa, impressao, estilo))
            print(f"{ficha['pdf'].relative_to(ROOT).as_posix()}: {ficha['pdf'].stat().st_size:,} bytes · fonte {impressao[:12]}…")
        navegador.close()


def main():
    argumentos = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    argumentos.add_argument("--conferir", action="store_true", help="só confere se os PDFs correspondem às fontes atuais")
    argumentos.add_argument("ficha", nargs="*", choices=[[], *FICHAS], help="detector, simulador ou as duas (padrão)")
    opcoes = argumentos.parse_args()
    if opcoes.conferir:
        problemas = conferir()
        print("\n".join(problemas) if problemas else "As fichas correspondem às fontes atuais.")
        sys.exit(1 if problemas else 0)
    gerar(opcoes.ficha or list(FICHAS))


if __name__ == "__main__":
    main()
