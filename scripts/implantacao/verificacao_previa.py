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

Desde 05/11/2026, ausência de resposta nunca vale como aprovação. O gcloud roda sem entrada e sem perguntas (nunca oferece
habilitar uma API) e com limite de tempo real: 30 s na consulta de orçamentos, 120 s nas demais. A consulta de orçamentos que
falha ou não responde fica MANUAL, com a conferência obrigatória no Console; qualquer outra verificação obrigatória que não se
conclua é FALHA, inclusive as contas de serviço e os pools de identidade, que antes passavam calados.

Desde 06/11/2026, a saída é sempre em UTF-8, no console ou redirecionada, e nenhum caractere encerra o script. Redirecionada no
Windows, ela começa com a marca BOM, para o PowerShell 5.1 manter a seta e os acentos.

Uso: python scripts/implantacao/verificacao_previa.py [--projeto agente-diagnostico-territorial] [--regiao us-central1]
Sai com 1 se alguma verificação falhar e com 2 se, sem falhas, restar conferência manual: nos dois casos, nada segue.
"""
import argparse
import json
import os
import shutil
import signal
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
LIMITE_PADRAO = 120  # segundos por consulta
LIMITES = {("billing", "budgets"): 30}  # orçamentos: sem resposta, o item fica MANUAL em vez de segurar a verificação
SEM_RESPOSTA = -1  # o código de uma consulta que não terminou ou nem começou
# Com uma API desligada, o gcloud pergunta se deve habilitá-la, o que seria uma alteração, e fica parado esperando a resposta.
# O padrão dessa pergunta é "sim" em alguns comandos: por isso a oferta é desligada, além das perguntas em geral.
SEM_PERGUNTAS = {"CLOUDSDK_CORE_DISABLE_PROMPTS": "1", "CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API": "false"}


def encerrar(processo: subprocess.Popen) -> None:
    """Encerra o comando e os processos que ele abriu. No Windows, o gcloud.cmd abre um Python que sobrevive ao kill do cmd.exe
    e segura os canais de saída; `subprocess.run(timeout=...)` só voltaria quando esse Python terminasse, ou nunca."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(processo.pid)], stdin=subprocess.DEVNULL, capture_output=True,
                           timeout=10)
        else:
            os.killpg(processo.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    processo.kill()
    try:
        processo.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        pass


def executar(comando: list[str], limite: int) -> tuple[int, str]:
    """(código, saída) do comando. Sem resposta no limite, ou sem conseguir iniciá-lo: (SEM_RESPOSTA, motivo), nunca exceção."""
    try:
        processo = subprocess.Popen(comando, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, encoding="utf-8", errors="replace", env={**os.environ, **SEM_PERGUNTAS},
                                    start_new_session=os.name != "nt")
    except OSError as erro:
        return SEM_RESPOSTA, f"o gcloud não pôde ser executado: {erro}"
    try:
        saida, erros = processo.communicate(timeout=limite)
    except subprocess.TimeoutExpired:
        encerrar(processo)
        return SEM_RESPOSTA, f"sem resposta em {limite} s"
    return processo.returncode, (saida if processo.returncode == 0 else erros)


def gcloud(*args) -> tuple[int, str]:
    executavel = shutil.which("gcloud") or shutil.which("gcloud.cmd") or "gcloud"
    return executar([executavel, *args], LIMITES.get(args[:2], LIMITE_PADRAO))


def nao_concluida(saida: str) -> str:
    return "consulta não concluída: " + (" ".join(saida.split())[:280] or "sem detalhe")


def em_json(rodar, *args):
    """(dados, "") ou (None, motivo): o que falhou, não respondeu ou veio vazio ou ilegível nunca passa por resposta."""
    codigo, saida = rodar(*args, "--format=json")
    if codigo != 0:
        return None, nao_concluida(saida)
    try:
        dados = json.loads(saida or "null")
    except ValueError:
        return None, nao_concluida("resposta ilegível")
    return (dados, "") if dados is not None else (None, nao_concluida("resposta vazia"))


def em_linhas(rodar, *args):
    """A mesma regra de em_json, para as listagens em `--format=value(...)`."""
    codigo, saida = rodar(*args)
    return (saida.split(), "") if codigo == 0 else (None, nao_concluida(saida))


def verificar(rodar, projeto: str, regiao: str) -> list[tuple[str, str, str]]:
    """[(situação, item, detalhe)]; situação: OK, ATENÇÃO, FALHA ou MANUAL. `rodar(*args)` devolve (código, saída)."""
    itens = []

    def item(situacao, nome, detalhe=""):
        itens.append((situacao, nome, detalhe))

    codigo, saida = rodar("auth", "list", "--filter=status:ACTIVE", "--format=value(account)")
    conta = saida.strip() if codigo == 0 else ""
    item("OK" if conta else "FALHA", "conta autenticada",
         conta or ("nenhuma conta ativa: gcloud auth login (P-1)" if codigo == 0 else nao_concluida(saida)))
    codigo, saida = rodar("config", "get-value", "project")
    ativo = saida.strip() if codigo == 0 else ""
    item("OK" if ativo == projeto else "FALHA", "projeto ativo",
         f"{ativo or 'nenhum'} (esperado {projeto})" if codigo == 0 else nao_concluida(saida))
    if regiao != "us-central1":
        item("FALHA", "região", f"{regiao} (esperado us-central1)")
    else:
        item("OK", "região", regiao)
    faturamento, motivo = em_json(rodar, "billing", "projects", "describe", projeto)
    conta_de_faturamento = ((faturamento or {}).get("billingAccountName") or "").split("/")[-1]
    item("OK" if conta_de_faturamento and faturamento.get("billingEnabled") else "FALHA", "conta de faturamento",
         motivo or conta_de_faturamento or "sem faturamento vinculado")
    if not conta_de_faturamento:
        item("MANUAL", "orçamento de alertas de R$ 11", "não consultado sem a conta de faturamento; conferir no Console (P-2)")
    else:
        orcamentos, motivo = em_json(rodar, "billing", "budgets", "list", "--billing-account=" + conta_de_faturamento)
        if orcamentos is None:
            item("MANUAL", "orçamento de alertas de R$ 11", motivo + "; conferir no Console (P-2)")
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
    habilitadas = set(apis.split()) if codigo == 0 else set()
    apis_lidas = bool(habilitadas)  # uma lista vazia não diz que as APIs estão desligadas
    item("OK" if apis_lidas else "FALHA", "APIs habilitadas",
         f"listagem concluída ({len(habilitadas)})" if apis_lidas else nao_concluida(apis or "lista vazia"))
    for api, motivo in APIS_NAO_PREVISTAS.items():
        if api in habilitadas:
            item("ATENÇÃO", "API não prevista habilitada", f"{api}: {motivo}")

    def listar(rotulo, *args, ler=em_json):
        """A listagem de um tipo de recurso: None (sem consulta) com a API desligada; [] e FALHA se ela não se concluir. Sem
        entrada em API_DE, a falha é sempre FALHA: contas de serviço e pools existem mesmo com a API do IAM desligada."""
        if apis_lidas and rotulo in API_DE and API_DE[rotulo] not in habilitadas:
            item("OK", rotulo, f"API {API_DE[rotulo]} desligada: nenhum recurso possível (antes do F2-1)")
            return None
        dados, motivo = ler(rodar, *args)
        if dados is None:
            item("FALHA", rotulo, motivo + "; nada pode ser dado como inexistente")
            return []
        item("OK", rotulo, f"listagem concluída ({len(dados)})")
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
    contas = listar("contas de serviço", "iam", "service-accounts", "list", "--project=" + projeto, "--format=value(email)",
                    ler=em_linhas)
    for email in contas:
        if email.endswith("-compute@developer.gserviceaccount.com"):
            # Criada pelo Google ao habilitar o Cloud Run (F2-1, 02/11/2026); o serviço usa a adt-execucao, não esta.
            item("OK", "conta padrão do Compute", email + " (criada pelo Google; não usada pelo serviço)")
            continue
        if email.split("@")[0] not in CONTAS_PREVISTAS:
            item("ATENÇÃO", "conta de serviço não prevista", email)
    segredos = listar("segredos", "secrets", "list", "--project=" + projeto) or []
    for nome in (s.get("name", "") for s in segredos):
        if nome.split("/")[-1] not in SEGREDOS_PREVISTOS:
            item("ATENÇÃO", "segredo não previsto", nome.split("/")[-1])
    pools = listar("pools de identidade", "iam", "workload-identity-pools", "list", "--location=global", "--project=" + projeto,
                   "--format=value(name)", ler=em_linhas)
    for nome in pools:
        if nome.split("/")[-1] != "github":
            item("ATENÇÃO", "pool de identidade não previsto", nome.split("/")[-1])
    return itens


def preparar_saida() -> None:
    """Redirecionada no Windows, a saída usaria o cp1252, que não tem a seta do item da trava: o script cairia no print, no meio da
    tabela. Só nesse caso ela leva a marca BOM: sem a marca, o PowerShell 5.1 relê o texto no cp850 e troca a seta e os acentos."""
    com_marca = os.name == "nt" and not sys.stdout.isatty()
    sys.stdout.reconfigure(encoding="utf-8-sig" if com_marca else "utf-8", errors="replace")


def main(argv=None) -> int:
    preparar_saida()
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
          + ("Nada segue até corrigir." if falhas else "Sem aprovação: nada segue até o responsável conferir os itens MANUAL."))
    return 1 if falhas else 2 if manuais else 0


if __name__ == "__main__":
    sys.exit(main())
