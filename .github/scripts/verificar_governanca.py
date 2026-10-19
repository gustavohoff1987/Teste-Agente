"""Verificações de governança do repositório: rodam no CI e devem rodar antes de cada push.

1. Registro de comportamento. Todo commit posterior à vigência da regra que altere o produto
   (frontend/, backend/ fora de backend/tests/, dados/ ou os arquivos de dados da raiz) precisa,
   no mesmo commit, fazer uma destas coisas:
     a) atualizar Docs/REGISTRO_DE_COMPORTAMENTO.md; ou
     b) declarar na mensagem uma linha "Comportamento: sem alteração — <motivo>".
   Para regularizar um commit já publicado sem nenhuma das duas, acrescente ao registro uma
   entrada que cite o hash curto dele (7 caracteres ou mais). Não é preciso reescrever o histórico.
2. Jornadas de navegador. Todo backend/tests/ui_*.py ativo precisa estar registrado no executor
   (backend/tests/run_ui_checks.py), e o workflow do CI precisa chamar todas as suítes do executor.
   Assim, nenhum roteiro de navegador existe sem rodar.

Uso, na raiz do repositório:  python .github/scripts/verificar_governanca.py
Requer o histórico completo do Git (no CI, checkout com fetch-depth: 0).
"""
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parents[2]
REGISTRO = "Docs/REGISTRO_DE_COMPORTAMENTO.md"
# Vigência: a regra vale para commits posteriores ao último commit de 15/10/2026 sem ela.
BASE = "dbaa0bda3781ce5aeeab01bd4ca787f318bea33c"
VIGENCIA = "2026-10-15T21:08:09Z"  # usada só quando BASE não é ancestral do commit verificado
PRODUTO = ("frontend/", "backend/", "dados/")
DADOS_RAIZ = ("Dados_Brasil.xlsx", "Dados_Municipios_Brasil.csv", "Dados_Estados_Brasil.csv")
FORA_DO_PRODUTO = ("backend/tests/",)
DECLARACAO = re.compile(r"^\s*Comportamento:\s*sem\s+altera[cç][aã]o\b", re.IGNORECASE | re.MULTILINE)
HASH = re.compile(r"(?<![0-9a-f])[0-9a-f]{7,40}(?![0-9a-f])")
GITHUB = os.environ.get("GITHUB_ACTIONS") == "true"


class Violacao(NamedTuple):
    sha: str
    assunto: str
    arquivos: list


def git(*args, cwd=ROOT):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


def afeta_comportamento(caminho):
    """Arquivos cuja alteração pode mudar o que o usuário ou a API observam."""
    if caminho.startswith(FORA_DO_PRODUTO):
        return False
    return caminho.startswith(PRODUTO) or caminho in DADOS_RAIZ


def declara_sem_alteracao(mensagem):
    return bool(DECLARACAO.search(mensagem))


def registro_cita(sha, texto):
    """O registro cita o commit por um prefixo de 7 a 40 caracteres, isolado (não dentro de um SHA-256)."""
    return any(sha.startswith(token) for token in HASH.findall(texto.lower()))


def commits_sujeitos(cwd=ROOT, base=BASE):
    """Commits (sem merges, do mais antigo ao mais novo) aos quais a regra se aplica."""
    if git("rev-parse", "--is-shallow-repository", cwd=cwd).strip() == "true":
        raise RuntimeError("histórico incompleto (clone raso); no CI use actions/checkout com fetch-depth: 0")
    ancestral = subprocess.run(["git", "merge-base", "--is-ancestor", base, "HEAD"], cwd=cwd,
                               capture_output=True).returncode == 0
    if ancestral:
        saida = git("rev-list", "--reverse", "--no-merges", "--ancestry-path", base + "..HEAD", cwd=cwd)
    else:  # ex.: ramo que recebeu as mudanças por squash; vale a data de vigência
        saida = git("rev-list", "--reverse", "--no-merges", "--since=" + VIGENCIA, "HEAD", cwd=cwd)
    return saida.split()


def verificar_registro(cwd=ROOT, base=BASE):
    """Devolve (violações, quantidade de commits verificados)."""
    commits = commits_sujeitos(cwd, base)
    try:
        registro = git("show", "HEAD:" + REGISTRO, cwd=cwd)
    except subprocess.CalledProcessError:
        registro = ""
    violacoes = []
    for sha in commits:
        arquivos = [p for p in git("diff-tree", "--root", "--no-commit-id", "--name-only", "-r", "-z", sha,
                                   cwd=cwd).split("\0") if p]
        produto = [p for p in arquivos if afeta_comportamento(p)]
        if not produto or REGISTRO in arquivos:
            continue
        mensagem = git("log", "-1", "--format=%B", sha, cwd=cwd)
        if declara_sem_alteracao(mensagem) or registro_cita(sha, registro):
            continue
        violacoes.append(Violacao(sha, mensagem.strip().splitlines()[0] if mensagem.strip() else "", produto))
    return violacoes, len(commits)


def carregar_executor(root):
    caminho = root / "backend" / "tests" / "run_ui_checks.py"
    spec = importlib.util.spec_from_file_location("run_ui_checks_governanca", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def verificar_roteiros(root=ROOT):
    """Problemas de cobertura das jornadas de navegador (lista vazia quando tudo roda no CI)."""
    root = Path(root)
    pasta = root / "backend" / "tests"
    ativos = {p.name for p in pasta.glob("ui_*.py") if p.name != "ui_support.py"}
    executor = carregar_executor(root)
    registrados = set(executor.registered_scripts())
    problemas = []
    for nome in sorted(ativos - registrados):
        problemas.append(f"backend/tests/{nome} não roda no CI: registre-o em SUITES (backend/tests/run_ui_checks.py) "
                         "ou mova-o para backend/tests/legado/ com a justificativa no README de lá.")
    for nome in sorted(registrados - ativos):
        problemas.append(f"run_ui_checks.py registra {nome}, que não existe em backend/tests/.")
    chamadas = [linha for linha in (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8").splitlines()
                if "run_ui_checks.py" in linha and not linha.lstrip().startswith("#")]
    cobertas = set()
    for linha in chamadas:
        suites = re.findall(r"--suite[ =]([\w-]+)", linha)
        cobertas.update(suites if suites else executor.SUITES)
    for suite in sorted(set(executor.SUITES) - cobertas):
        problemas.append(f"a suíte '{suite}' do run_ui_checks.py não é chamada por .github/workflows/ci.yml.")
    return problemas


def anotar(titulo, texto):
    print(f"::error title={titulo}::{texto}" if GITHUB else f"ERRO · {titulo}: {texto}", flush=True)


def main():
    falhas = 0
    linhas_resumo = []
    try:
        violacoes, verificados = verificar_registro()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        anotar("Registro de comportamento", "não foi possível verificar: " + str(exc))
        violacoes, verificados, falhas = [], 0, 1
        linhas_resumo.append("| Registro de comportamento | ❌ não verificado: " + str(exc) + " |")
    else:
        for item in violacoes:
            anotar("Mudança de comportamento sem registro",
                   f"{item.sha[:7]} \"{item.assunto}\" altera {', '.join(item.arquivos[:5])}"
                   + (" …" if len(item.arquivos) > 5 else "") +
                   f" sem atualizar {REGISTRO} e sem a linha 'Comportamento: sem alteração — <motivo>'. "
                   f"Para regularizar, registre a mudança citando {item.sha[:7]}.")
        falhas += len(violacoes)
        linhas_resumo.append(f"| Registro de comportamento ({verificados} commits desde a vigência) | " +
                             ("✅ todos registrados ou declarados" if not violacoes else
                              f"❌ {len(violacoes)} sem registro: " + ", ".join(v.sha[:7] for v in violacoes)) + " |")
    problemas = verificar_roteiros()
    for texto in problemas:
        anotar("Jornada de navegador fora do CI", texto)
    falhas += len(problemas)
    linhas_resumo.append("| Jornadas de navegador registradas no CI | " +
                         ("✅ todas" if not problemas else f"❌ {len(problemas)} problema(s)") + " |")
    tabela = "| Verificação | Resultado |\n|---|---|\n" + "\n".join(linhas_resumo)
    print("\nGovernança do repositório\n" + tabela, flush=True)
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as fh:
            fh.write("### Governança\n\n" + tabela + "\n")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
