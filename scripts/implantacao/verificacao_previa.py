"""Verificação prévia da implantação (F2-0 do Docs/implantacao/ROTEIRO_FASE2.md): só leitura, obrigatória antes de qualquer
implantação do Agente Diagnóstico Territorial da Força de Trabalho na Saúde no Cloud Run e de cada atualização.

Usa só comandos gcloud de leitura (list, describe, get-value) com a conta já autenticada (P-1) e mostra OK, ATENÇÃO, FALHA ou
MANUAL para: a conta autenticada, o projeto e a região, a conta de faturamento, o orçamento só de alertas de R$ 11 (25, 50, 75
e 100%), a trava de R$ 11 do Cloud Run (MANUAL: conferida no Console, P-2), as APIs habilitadas, os recursos não previstos
(serviços do Cloud Run, repositórios do Artifact Registry, contas de serviço, segredos e pools de identidade) e, se o serviço
já existir, mínimo 0, máximo 1, 1 vCPU, 2 GiB, cobrança por requisição, sem aumento de CPU na partida, concorrência e timeout.
Nada é criado, alterado ou apagado; nenhum valor de segredo é lido. Desde 02/11/2026 (primeira execução do F2-0), uma
listagem que falha não passa mais por "nenhum recurso": com a API do recurso desligada (antes do F2-1), o item diz isso; com
a API ligada, a falha da listagem é FALHA.

Uso: python scripts/implantacao/verificacao_previa.py [--projeto agente-diagnostico-territorial] [--regiao us-central1]
Sai com 1 se alguma verificação falhar.
"""
import argparse
import json
import shutil
import subprocess
import sys

SERVICO = "agente-diagnostico-territorial"
REPOSITORIO = "agente-diagnostico-territorial"
CONTAS_PREVISTAS = {"adt-execucao", "adt-envio-imagem"}
SEGREDOS_PREVISTOS = {"gemini-api-key"}
APIS_NAO_PREVISTAS = {"cloudbuild.googleapis.com": "Cloud Build (a imagem é construída no GitHub Actions)",
                      "containerscanning.googleapis.com": "varredura de vulnerabilidades (cobrada à parte)"}
API_DE = {"serviços do Cloud Run": "run.googleapis.com", "repositórios do Artifact Registry": "artifactregistry.googleapis.com",
          "segredos": "secretmanager.googleapis.com"}


def gcloud(*args) -> tuple[int, str]:
    executavel = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
    feito = subprocess.run([executavel, *args], capture_output=True, text=True, timeout=120)
    return feito.returncode, (feito.stdout if feito.returncode == 0 else feito.stderr)


def em_json(rodar, *args):
    codigo, saida = rodar(*args, "--format=json")
    if codigo != 0:
        return None
    try:
        return json.loads(saida or "null")
    except ValueError:
        return None


def verificar(rodar, projeto: str, regiao: str) -> list[tuple[str, str, str]]:
    """[(situação, item, detalhe)]; situação: OK, ATENÇÃO, FALHA ou MANUAL. `rodar(*args)` devolve (código, saída)."""
    itens = []

    def item(situacao, nome, detalhe=""):
        itens.append((situacao, nome, detalhe))

    codigo, conta = rodar("auth", "list", "--filter=status:ACTIVE", "--format=value(account)")
    conta = conta.strip() if codigo == 0 else ""
    item("OK" if conta else "FALHA", "conta autenticada", conta or "nenhuma conta ativa: gcloud auth login (P-1)")
    codigo, ativo = rodar("config", "get-value", "project")
    ativo = ativo.strip() if codigo == 0 else ""
    item("OK" if ativo == projeto else "FALHA", "projeto ativo", f"{ativo or 'nenhum'} (esperado {projeto})")
    if regiao != "us-central1":
        item("FALHA", "região", f"{regiao} (esperado us-central1)")
    else:
        item("OK", "região", regiao)
    faturamento = em_json(rodar, "billing", "projects", "describe", projeto) or {}
    conta_de_faturamento = (faturamento.get("billingAccountName") or "").split("/")[-1]
    item("OK" if faturamento.get("billingEnabled") and conta_de_faturamento else "FALHA", "conta de faturamento",
         conta_de_faturamento or "sem faturamento vinculado")
    if conta_de_faturamento:
        orcamentos = em_json(rodar, "billing", "budgets", "list", "--billing-account=" + conta_de_faturamento)
        if orcamentos is None:
            item("MANUAL", "orçamento de alertas de R$ 11", "a listagem não respondeu; conferir no Console (P-2)")
        else:
            alertas = []
            for orcamento in orcamentos:
                valor = ((orcamento.get("amount") or {}).get("specifiedAmount") or {})
                limites = sorted(round(float(t.get("thresholdPercent", 0)) * 100) for t in orcamento.get("thresholdRules") or [])
                if valor.get("currencyCode") == "BRL" and str(valor.get("units")) == "11":
                    alertas.append(limites)
            if [25, 50, 75, 100] in alertas:
                item("OK", "orçamento de alertas de R$ 11", "alertas de 25, 50, 75 e 100%")
            else:
                item("FALHA", "orçamento de alertas de R$ 11", "não encontrado com 25, 50, 75 e 100%: " + json.dumps(alertas))
    item("MANUAL", "trava de R$ 11 do Cloud Run (alertas de 50, 80 e 100%)",
         "conferir no Console, Faturamento → Orçamentos e alertas, sem alterar (P-2)")
    codigo, apis = rodar("services", "list", "--enabled", "--project=" + projeto, "--format=value(config.name)")
    apis_lidas = codigo == 0
    habilitadas = set(apis.split()) if apis_lidas else set()
    if not apis_lidas:
        item("FALHA", "APIs habilitadas", "a listagem falhou: " + apis.strip()[:200])
    for api, motivo in APIS_NAO_PREVISTAS.items():
        if api in habilitadas:
            item("ATENÇÃO", "API não prevista habilitada", f"{api}: {motivo}")

    def listar(rotulo, *args):
        """A listagem de um tipo de recurso: None (sem consulta) com a API desligada; [] e FALHA se a listagem falhar."""
        if apis_lidas and API_DE[rotulo] not in habilitadas:
            item("OK", rotulo, f"API {API_DE[rotulo]} desligada: nenhum recurso possível (antes do F2-1)")
            return None
        dados = em_json(rodar, *args)
        if dados is None:
            item("FALHA", rotulo, "a listagem falhou (permissão ou API); nada pode ser dado como inexistente")
            return []
        return dados

    servicos = listar("serviços do Cloud Run", "run", "services", "list", "--project=" + projeto, "--region=" + regiao) or []
    for servico in servicos:
        nome = (servico.get("metadata") or {}).get("name", "")
        if nome != SERVICO:
            item("ATENÇÃO", "serviço do Cloud Run não previsto", nome)
            continue
        modelo = (servico.get("spec") or {}).get("template") or {}
        anotacoes = (modelo.get("metadata") or {}).get("annotations") or {}
        especificacao = modelo.get("spec") or {}
        container = (especificacao.get("containers") or [{}])[0]
        limites = (container.get("resources") or {}).get("limits") or {}
        esperado = {"mínimo de instâncias": (anotacoes.get("autoscaling.knative.dev/minScale", "0"), "0"),
                    "máximo de instâncias": (anotacoes.get("autoscaling.knative.dev/maxScale"), "1"),
                    "vCPU": (limites.get("cpu"), "1"), "memória": (limites.get("memory"), "2Gi"),
                    "cobrança por requisição": (anotacoes.get("run.googleapis.com/cpu-throttling", "true"), "true"),
                    "aumento de CPU na partida": (anotacoes.get("run.googleapis.com/startup-cpu-boost", "false"), "false")}
        for rotulo, (obtido, previsto) in esperado.items():
            item("OK" if str(obtido) == previsto else "FALHA", "serviço: " + rotulo, f"{obtido} (esperado {previsto})")
        item("OK", "serviço: concorrência e timeout",
             f"{especificacao.get('containerConcurrency')} e {especificacao.get('timeoutSeconds')} s (ver o roteiro)")
    repositorios = listar("repositórios do Artifact Registry", "artifacts", "repositories", "list", "--project=" + projeto,
                          "--location=" + regiao) or []
    for repositorio in repositorios:
        nome = (repositorio.get("name") or "").split("/")[-1]
        if nome != REPOSITORIO:
            item("ATENÇÃO", "repositório do Artifact Registry não previsto", nome)
    codigo, contas = rodar("iam", "service-accounts", "list", "--project=" + projeto, "--format=value(email)")
    for email in (contas.split() if codigo == 0 else []):
        if email.split("@")[0] not in CONTAS_PREVISTAS:
            item("ATENÇÃO", "conta de serviço não prevista", email)
    segredos = listar("segredos", "secrets", "list", "--project=" + projeto) or []
    for nome in (s.get("name", "") for s in segredos):
        if nome.split("/")[-1] not in SEGREDOS_PREVISTOS:
            item("ATENÇÃO", "segredo não previsto", nome.split("/")[-1])
    codigo, pools = rodar("iam", "workload-identity-pools", "list", "--location=global", "--project=" + projeto,
                          "--format=value(name)")
    for nome in (pools.split() if codigo == 0 else []):
        if nome.split("/")[-1] != "github":
            item("ATENÇÃO", "pool de identidade não previsto", nome.split("/")[-1])
    return itens


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--projeto", default="agente-diagnostico-territorial")
    parser.add_argument("--regiao", default="us-central1")
    argumentos = parser.parse_args(argv)
    itens = verificar(gcloud, argumentos.projeto, argumentos.regiao)
    largura = max(len(nome) for _, nome, _ in itens)
    for situacao, nome, detalhe in itens:
        print(f"{situacao:8} {nome.ljust(largura)}  {detalhe}")
    falhas = sum(1 for situacao, _, _ in itens if situacao == "FALHA")
    manuais = sum(1 for situacao, _, _ in itens if situacao == "MANUAL")
    print(f"\n{falhas} falha(s); {manuais} conferência(s) manual(is) no Console. "
          + ("Nada segue até corrigir." if falhas else "Confira os itens MANUAL antes de seguir."))
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
