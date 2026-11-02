"""Falha se o padrão de uma chave de API do Google aparecer nos arquivos indicados (01/11/2026; seção 6.1 do comando de
implantação): na imagem do contêiner, no build da interface (frontend/dist), nos relatórios e nos artefatos.

Mostra só o arquivo e a contagem, nunca o trecho. Os padrões: o clássico "AIza" seguido de 35 caracteres e o formato "AQ."
seguido de 40 ou mais (o da chave em uso no projeto). Só a biblioteca padrão: roda também dentro da imagem, com o Python dela.

Uso:
  python .github/scripts/verificar_chave_google.py <arquivo ou pasta> [...]
  python verificar_chave_google.py --raiz-da-imagem /      (dentro do contêiner: todo o sistema de arquivos da imagem)
"""
import argparse
import os
import re
import sys
from pathlib import Path

PADROES = {
    "AIza": re.compile(rb"(?<![0-9A-Za-z_-])AIza[0-9A-Za-z_-]{35}(?![0-9A-Za-z_-])"),
    "AQ.": re.compile(rb"(?<![0-9A-Za-z_-])AQ\.[0-9A-Za-z_-]{40,}"),
}
FORA_DA_IMAGEM = ("/proc", "/sys", "/dev", "/run", "/tmp", "/verificacao")
LIMITE_POR_ARQUIVO = 64 * 1024 * 1024


def arquivos(alvos, raiz_da_imagem: bool):
    for alvo in alvos:
        caminho = Path(alvo)
        if caminho.is_file():
            yield caminho
            continue
        if not caminho.is_dir():
            continue
        for pasta, subpastas, nomes in os.walk(caminho, followlinks=False):
            if raiz_da_imagem:
                subpastas[:] = [nome for nome in subpastas
                                if not any(os.path.join(pasta, nome).startswith(fora) for fora in FORA_DA_IMAGEM)]
            for nome in nomes:
                arquivo = Path(pasta, nome)
                if arquivo.is_file() and not arquivo.is_symlink():
                    yield arquivo


def verificar(alvos, raiz_da_imagem: bool = False) -> tuple[int, list[tuple[str, str, int]]]:
    """(arquivos examinados, [(arquivo, padrão, ocorrências)])."""
    examinados, achados = 0, []
    for arquivo in arquivos(alvos, raiz_da_imagem):
        try:
            if arquivo.stat().st_size > LIMITE_POR_ARQUIVO:
                # Arquivo grande: em blocos, com a sobreposição de 128 bytes; cada ocorrência conta uma vez (a que termina
                # dentro do bloco novo).
                contagens = dict.fromkeys(PADROES, 0)
                with arquivo.open("rb") as entrada:
                    anterior = b""
                    while bloco := entrada.read(8 * 1024 * 1024):
                        janela = anterior + bloco
                        for nome, padrao in PADROES.items():
                            contagens[nome] += sum(1 for achado in padrao.finditer(janela) if achado.end() > len(anterior))
                        anterior = janela[-128:]
                examinados += 1
                achados += [(str(arquivo), nome, n) for nome, n in contagens.items() if n]
                continue
            conteudo = arquivo.read_bytes()
        except OSError:
            continue
        examinados += 1
        for nome, padrao in PADROES.items():
            ocorrencias = len(padrao.findall(conteudo))
            if ocorrencias:
                achados.append((str(arquivo), nome, ocorrencias))
    return examinados, achados


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("alvos", nargs="*", help="arquivos ou pastas")
    parser.add_argument("--raiz-da-imagem", help="dentro do contêiner: a raiz do sistema de arquivos da imagem")
    argumentos = parser.parse_args(argv)
    alvos = list(argumentos.alvos) + ([argumentos.raiz_da_imagem] if argumentos.raiz_da_imagem else [])
    if not alvos:
        parser.error("indique ao menos um arquivo ou pasta")
    examinados, achados = verificar(alvos, raiz_da_imagem=bool(argumentos.raiz_da_imagem))
    for arquivo, nome, ocorrencias in achados:
        print(f"::error title=Padrão de chave do Google::{arquivo}: {ocorrencias} ocorrência(s) do padrão {nome}", flush=True)
    print(f"Padrão de chave do Google: {examinados} arquivo(s) examinado(s) em {', '.join(alvos)}; "
          + (f"{len(achados)} com ocorrência." if achados else "nenhuma ocorrência."), flush=True)
    return 1 if achados else 0


if __name__ == "__main__":
    sys.exit(main())
