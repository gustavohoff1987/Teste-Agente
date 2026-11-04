"""Confere, pela API do GitHub e só em leitura, o commit de origem de uma publicação construída noutro repositório (04/11/2026;
segunda publicação da interface em https://diagnostico-territorial.github.io/, Docs/implantacao/ROTEIRO_FASE2.md, M-0 a M-5).

O repositório de destino guarda uma cópia revisada deste script e o roda antes de construir: assim, a verificação não depende
do código que ela confere. Exige, nesta ordem:
1. o commit é um SHA completo (40 caracteres hexadecimais), fixado no destino (origem.txt);
2. o commit pertence ao ramo de preparação do repositório de origem (o ramo contém o commit);
3. o CI do repositório de origem terminou em sucesso nesse commit (uma execução do workflow, num push).
Qualquer falha encerra a execução (código 1) antes do build: nada é construído nem publicado. Nenhum segredo é lido; num
repositório público, a API responde até sem o token.

Uso (no workflow do destino): python .github/scripts/conferir_origem.py --repositorio gustavohoff1987/Teste-Agente
  --ramo implantacao/cloud-run-pages --commit <sha> [--workflow "CI Portal Experimental"]
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


def api_do_github(caminho: str) -> tuple[int, dict]:
    """GET na API do GitHub (com o GITHUB_TOKEN do workflow, se houver); (status, corpo JSON ou {})."""
    cabecalhos = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if os.environ.get("GITHUB_TOKEN"):
        cabecalhos["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    try:
        with urllib.request.urlopen(urllib.request.Request(API + caminho, headers=cabecalhos), timeout=30) as resposta:
            return resposta.status, json.load(resposta)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.load(exc)
        except ValueError:
            return exc.code, {}


def conferir(api, repositorio: str, ramo: str, commit: str, workflow: str) -> list[str]:
    """Os problemas da origem (lista vazia quando tudo confere). `api(caminho)` devolve (status, corpo)."""
    if not re.fullmatch(r"[0-9a-f]{40}", commit or ""):
        return [f"o commit de origem ({commit or 'vazio'}) não é um SHA completo"]
    problemas = []
    status, comparacao = api(f"/repos/{repositorio}/compare/{urllib.parse.quote(ramo, safe='/')}...{commit}")
    if status != 200 or comparacao.get("status") not in ("identical", "behind"):
        problemas.append(f"o commit {commit[:7]} não pertence ao ramo {ramo} de {repositorio}")
    status, lista = api(f"/repos/{repositorio}/actions/runs?head_sha={commit}&event=push&per_page=100")
    if status != 200:
        return problemas + [f"não foi possível ler as execuções do CI de {repositorio} (HTTP {status})"]
    execucoes = [e for e in lista.get("workflow_runs") or [] if e.get("name") == workflow]
    if not any(e.get("status") == "completed" and e.get("conclusion") == "success" for e in execucoes):
        estados = ", ".join(f"{e.get('status')}/{e.get('conclusion')}" for e in execucoes) or "nenhuma execução"
        problemas.append(f"o CI \"{workflow}\" não terminou em sucesso no commit {commit[:7]} ({estados})")
    return problemas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--repositorio", required=True)
    parser.add_argument("--ramo", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--workflow", default="CI Portal Experimental")
    argumentos = parser.parse_args(argv)
    problemas = conferir(api_do_github, argumentos.repositorio, argumentos.ramo, argumentos.commit.strip(),
                         argumentos.workflow)
    for problema in problemas:
        print(f"::error title=Origem da publicação::{problema}", flush=True)
    print(f"Origem {argumentos.repositorio}@{argumentos.commit.strip()[:7]}: " +
          ("confere; o build pode seguir." if not problemas else f"{len(problemas)} problema(s); nada segue."), flush=True)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
