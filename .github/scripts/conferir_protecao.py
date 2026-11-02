"""Confere, pela API do GitHub e só em leitura, a proteção de um ambiente antes de um workflow protegido seguir (01/11/2026;
seções 1.2 e 6.3 do comando de implantação): validacao-gemini-real.yml (ambiente gemini-real, etiquetas
validacao-gemini-real-*), imagem.yml (producao, imagem-*) e pages.yml (github-pages, publicacao-pages-*).

Exige, nesta ordem:
1. o repositório está público (desde 02/11/2026; no plano gratuito do GitHub, o Pages e as proteções dos ambientes dependem
   disso);
2. o gatilho é uma etiqueta com o padrão do ambiente;
3. o ambiente existe (o job deste script não usa ambiente: se ele não existir, nada o cria);
4. o ambiente tem revisor obrigatório;
5. as implantações no ambiente só são aceitas por etiquetas com exatamente esse padrão (nenhum ramo, nenhuma outra etiqueta);
6. o commit da etiqueta pertence ao ramo de preparação (a restrição de ramo destes workflows, que só rodam por etiqueta).
Qualquer falha encerra a execução (código 1) antes do job protegido: nenhuma chamada ao provedor, nenhuma imagem enviada,
nenhuma publicação. Mostra só nomes, contagens e estados; nenhum segredo é lido.

Uso (no workflow): python .github/scripts/conferir_protecao.py --ambiente gemini-real --etiquetas "validacao-gemini-real-*"
  --ramo implantacao/cloud-run-pages   (repositório, commit e ref vêm de GITHUB_REPOSITORY, GITHUB_SHA e GITHUB_REF)
"""
import argparse
import fnmatch
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.github.com"


def api_do_github(caminho: str) -> tuple[int, dict]:
    """GET na API do GitHub com o GITHUB_TOKEN do workflow; (status, corpo JSON ou {})."""
    pedido = urllib.request.Request(API + caminho, headers={"Accept": "application/vnd.github+json",
                                                            "X-GitHub-Api-Version": "2022-11-28",
                                                            "Authorization": "Bearer " + os.environ.get("GITHUB_TOKEN", "")})
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            return resposta.status, json.load(resposta)
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.load(exc)
        except ValueError:
            return exc.code, {}


def conferir(api, repositorio: str, ambiente: str, padrao: str, ramo: str, commit: str, ref: str) -> list[str]:
    """Os problemas da proteção (lista vazia quando tudo confere). `api(caminho)` devolve (status, corpo)."""
    problemas = []
    status, dados = api(f"/repos/{repositorio}")
    if status != 200:
        problemas.append(f"não foi possível ler a visibilidade do repositório {repositorio} (HTTP {status})")
    elif dados.get("private") is not False or dados.get("visibility") != "public":
        problemas.append(f"o repositório {repositorio} não está público (visibilidade: {dados.get('visibility') or 'desconhecida'})")
    etiqueta = ref[len("refs/tags/"):] if ref.startswith("refs/tags/") else ""
    if not etiqueta or not fnmatch.fnmatchcase(etiqueta, padrao):
        problemas.append(f"o gatilho ({ref or 'vazio'}) não é uma etiqueta {padrao}")
    status, dados = api(f"/repos/{repositorio}/environments/{urllib.parse.quote(ambiente)}")
    if status == 404:
        return problemas + [f"o ambiente {ambiente} não existe"]
    if status != 200:
        return problemas + [f"não foi possível ler o ambiente {ambiente} (HTTP {status})"]
    regras = dados.get("protection_rules") or []
    if not any(regra.get("type") == "required_reviewers" and regra.get("reviewers") for regra in regras):
        problemas.append(f"o ambiente {ambiente} não tem revisor obrigatório")
    politica = dados.get("deployment_branch_policy") or {}
    if not politica.get("custom_branch_policies") or politica.get("protected_branches"):
        problemas.append(f"o ambiente {ambiente} não restringe as implantações às etiquetas {padrao}")
    else:
        status, lista = api(f"/repos/{repositorio}/environments/{urllib.parse.quote(ambiente)}/deployment-branch-policies"
                            "?per_page=100")
        if status != 200:
            problemas.append(f"não foi possível ler as regras de implantação do ambiente {ambiente} (HTTP {status})")
        else:
            obtidas = sorted((item.get("type", "branch"), item.get("name", "")) for item in lista.get("branch_policies") or [])
            if obtidas != [("tag", padrao)]:
                problemas.append(f"o ambiente {ambiente} aceita outras implantações além das etiquetas {padrao}: "
                                 + ", ".join(f"{tipo} {nome}" for tipo, nome in obtidas))
    status, comparacao = api(f"/repos/{repositorio}/compare/{urllib.parse.quote(ramo, safe='/')}...{commit}")
    if status != 200 or comparacao.get("status") not in ("identical", "behind"):
        problemas.append(f"o commit {commit[:7]} não pertence ao ramo {ramo}")
    return problemas


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--ambiente", required=True)
    parser.add_argument("--etiquetas", required=True)
    parser.add_argument("--ramo", required=True)
    argumentos = parser.parse_args(argv)
    problemas = conferir(api_do_github, os.environ.get("GITHUB_REPOSITORY", ""), argumentos.ambiente, argumentos.etiquetas,
                         argumentos.ramo, os.environ.get("GITHUB_SHA", ""), os.environ.get("GITHUB_REF", ""))
    for problema in problemas:
        print(f"::error title=Proteção do ambiente {argumentos.ambiente}::{problema}", flush=True)
    print(f"Proteção do ambiente {argumentos.ambiente}: " + ("confere; o job protegido pode seguir."
                                                              if not problemas else f"{len(problemas)} problema(s); nada segue."),
          flush=True)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())
