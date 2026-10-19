"""Verificação completa local, na ordem, com o resultado de cada passo.

O CI é o único ambiente de verificação (AGENTS.md, seção 4). Este script fica fora do fluxo normal:
rode-o só por pedido explícito do responsável pelo produto, para reproduzir o CI localmente.

Uso, de qualquer pasta do repositório:
    python scripts/verificar_tudo.py [--dados-reais auto|sim|nao] [--npm-ci] [--canal chrome|chromium]
                                     [--parar-na-falha]

Passos:
  1. backend: pytest (os testes com dados reais ficam para o passo 5);
  2. frontend: npm ci, quando package.json ou package-lock.json mudaram desde o último npm ci
     bem-sucedido registrado por este script (ou com --npm-ci), e npm run build;
  3. navegador: todas as jornadas de backend/tests/run_ui_checks.py;
  4. governança: .github/scripts/verificar_governanca.py, que confere os commits; mudanças ainda sem
     commit recebem um aviso, e a governança deve rodar de novo depois do commit;
  5. dados reais: pytest com ADT_REAL_DATA_DIR, obrigatório só quando a mudança toca o motor, a API ou
     os dados (com "auto", o script decide pelos arquivos alterados em relação ao ramo remoto);
  6. integridade: a base versionada continua igual ao manifesto.

Cada passo grava o log em .local/verificacao/<data-hora>/, e o resumo final diz o que passou, falhou
ou ficou de fora, e por quê. O script define PYTHONUTF8=1 e uma pasta temporária gravável para o
pytest (--basetemp), necessárias no Windows. Nenhum passo altera os dados, chama o provedor de IA
real, faz commit ou faz push. Saída: 0 se tudo passou; 1 se algo falhou; 2 se um passo obrigatório
ficou de fora por opção.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND, FRONTEND = ROOT / "backend", ROOT / "frontend"
# Registro do último npm ci bem-sucedido; fica dentro de node_modules, que o próprio npm ci recria.
CARIMBO = FRONTEND / "node_modules" / ".adt-npm-ci.json"
DEPENDENCIAS = ("package.json", "package-lock.json")
DADOS_RAIZ = ("Dados_Brasil.xlsx", "Dados_Municipios_Brasil.csv", "Dados_Estados_Brasil.csv")
PRODUTO = ("frontend/", "backend/", "dados/")


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    return result.stdout.strip() if result.returncode == 0 else None


def alterados():
    """Arquivos alterados em relação ao ramo remoto (ou à main), com as mudanças sem commit e os novos."""
    base = None
    for referencia in (git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"), "origin/main"):
        base = git("merge-base", "HEAD", referencia) if referencia else None
        if base:
            break
    if not base:
        return None
    nomes = set((git("diff", "--name-only", base) or "").splitlines())
    return sorted(nomes | set((git("ls-files", "--others", "--exclude-standard") or "").splitlines()))


def toca_motor_api_ou_dados(caminho):
    if caminho in DADOS_RAIZ or caminho.startswith("dados/"):
        return True
    if caminho.startswith("backend/tests/"):
        return "real" in Path(caminho).name  # um teste com dados reais alterado precisa rodar
    return caminho.startswith("backend/")


def sha256(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def ultima(texto, padrao):
    achados = re.findall(padrao, texto, re.MULTILINE)
    return achados[-1] if achados else ""


class Verificacao:
    def __init__(self, args):
        self.args = args
        self.pasta = ROOT / ".local" / "verificacao" / datetime.now().strftime("%Y%m%d-%H%M%S")
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.temporaria = Path(tempfile.mkdtemp(prefix="adt-pytest-"))  # gravável também no Windows
        self.env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
        self.resultados = []  # (passo, situação, detalhe, segundos)

    def rodar(self, nome, comando, cwd, env=None):
        """Roda um comando com a saída no log do passo; devolve (código, texto do log, segundos)."""
        log = self.pasta / f"{len(self.resultados) + 1}-{nome}.log"
        inicio = time.time()
        with open(log, "ab") as saida:
            saida.write(("$ " + " ".join(str(parte) for parte in comando) + "\n\n").encode("utf-8"))
            saida.flush()
            codigo = subprocess.run([str(parte) for parte in comando], cwd=cwd, env=env or self.env,
                                    stdout=saida, stderr=subprocess.STDOUT).returncode
        return codigo, log.read_text(encoding="utf-8", errors="replace"), time.time() - inicio

    def registrar(self, passo, situacao, detalhe, segundos=0.0):
        self.resultados.append((passo, situacao, detalhe, segundos))
        print(f"   {situacao}: {detalhe} ({segundos:.0f} s)", flush=True)
        if situacao == "FALHOU" and self.args.parar_na_falha:
            raise KeyboardInterrupt

    def pytest(self, passo, nome, extra_env=None, reais=False):
        print(f"\n== {passo}", flush=True)
        comando = [sys.executable, "-m", "pytest", "-q", f"--basetemp={self.temporaria / nome}"] + (["-rs"] if reais else [])
        codigo, texto, segundos = self.rodar(nome, comando, BACKEND, {**self.env, **(extra_env or {})})
        resumo = ultima(texto, r"^=*\s*(\d+ (?:passed|failed|error).*?)\s*=*$") or "sem resumo do pytest"
        pulados = re.search(r"(\d+) skipped", resumo)
        if reais and codigo == 0 and pulados:
            self.registrar(passo, "FALHOU", resumo + " — com a base versionada, nenhum teste pode ficar pulado", segundos)
        else:
            self.registrar(passo, "PASSOU" if codigo == 0 else "FALHOU", resumo, segundos)

    def frontend(self):
        passo = "frontend (npm ci e build)"
        print(f"\n== {passo}", flush=True)
        npm = shutil.which("npm")
        if not npm:
            return self.registrar(passo, "FALHOU", "npm não encontrado no PATH")
        hashes = {nome: sha256(FRONTEND / nome) for nome in DEPENDENCIAS}
        try:
            carimbo = json.loads(CARIMBO.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            carimbo = {}
        segundos, notas = 0.0, []
        if not self.args.npm_ci and carimbo.get("hashes") == hashes:
            notas.append("npm ci dispensado (package.json e package-lock.json iguais aos do último npm ci "
                         "bem-sucedido, em " + carimbo.get("quando", "?") + ")")
        else:
            codigo, texto, segundos = self.rodar("npm-ci", [npm, "ci"], FRONTEND)
            if codigo != 0:
                dica = (" — arquivo travado: um servidor Vite aberto pode estar usando node_modules; mova os arquivos "
                        "travados para fora (esbuild.exe, rollup*.node) e rode de novo") if "EPERM" in texto else ""
                return self.registrar(passo, "FALHOU", "npm ci falhou" + dica, segundos)
            CARIMBO.write_text(json.dumps({"hashes": hashes, "quando": datetime.now().isoformat(timespec="seconds")}),
                               encoding="utf-8")
            notas.append("npm ci executado")
        codigo, texto, tempo = self.rodar("build", [npm, "run", "build"], FRONTEND)
        aprovados, falhas = ultima(texto, r"pass (\d+)"), ultima(texto, r"fail (\d+)")
        notas.append(f"testes do frontend: {aprovados or '?'} aprovados, {falhas or '?'} falhas")
        if "built in" in texto:
            notas.append("build concluído")
        self.registrar(passo, "PASSOU" if codigo == 0 else "FALHOU", "; ".join(notas), segundos + tempo)

    def navegador(self):
        passo = "jornadas de navegador"
        print(f"\n== {passo} (pode levar mais de 10 minutos)", flush=True)
        canal = self.args.canal or os.environ.get("ADT_BROWSER_CHANNEL") or "chrome"
        codigo, texto, segundos = self.rodar("navegador", [sys.executable, "backend/tests/run_ui_checks.py"], ROOT,
                                             {**self.env, "ADT_BROWSER_CHANNEL": canal})
        resumo = ultima(texto, r"^\*\*(.+?)\*\*\s*$") or "sem resumo do executor"
        self.registrar(passo, "PASSOU" if codigo == 0 else "FALHOU", resumo + f" (canal {canal})", segundos)

    def governanca(self):
        passo = "governança"
        print(f"\n== {passo}", flush=True)
        codigo, texto, segundos = self.rodar("governanca", [sys.executable, ".github/scripts/verificar_governanca.py"], ROOT)
        linhas = [re.sub(r"[|*]", " ", linha).strip() for linha in texto.splitlines()
                  if linha.startswith("| Registro") or linha.startswith("| Jornadas")]
        detalhe = "; ".join(re.sub(r"\s{2,}", ": ", linha) for linha in linhas) or "ver o log"
        pendentes = [nome for nome in (git("status", "--porcelain") or "").splitlines()
                     if nome[3:].startswith(PRODUTO) and not nome[3:].startswith("backend/tests/") or nome[3:] in DADOS_RAIZ]
        if pendentes:
            com_registro = "Docs/REGISTRO_DE_COMPORTAMENTO.md" in (git("status", "--porcelain") or "")
            detalhe += (f"; aviso: {len(pendentes)} arquivo(s) do produto sem commit; "
                        + ("o registro de comportamento também mudou" if com_registro else
                           "sem mudança no registro, o commit precisa da linha \"Comportamento: sem alteração — <motivo>\"")
                        + "; rode a governança de novo depois do commit")
        self.registrar(passo, "PASSOU" if codigo == 0 else "FALHOU", detalhe, segundos)

    def dados_reais(self):
        passo = "dados reais"
        motivo_lista = alterados()
        relevantes = None if motivo_lista is None else [nome for nome in motivo_lista if toca_motor_api_ou_dados(nome)]
        obrigatorio = relevantes is None or bool(relevantes)
        if relevantes is None:
            por_que = "sem referência do ramo remoto para comparar; por segurança, os dados reais são obrigatórios"
        elif relevantes:
            por_que = "a mudança toca o motor, a API ou os dados: " + ", ".join(relevantes[:4]) + \
                      (f" e mais {len(relevantes) - 4}" if len(relevantes) > 4 else "")
        else:
            por_que = "a mudança não toca o motor, a API nem os dados"
        escolha = self.args.dados_reais
        if escolha == "nao" or (escolha == "auto" and not obrigatorio):
            situacao = "FORA (OBRIGATÓRIO)" if obrigatorio else "FORA"
            print(f"\n== {passo}", flush=True)
            return self.registrar(passo, situacao, ("pulado por --dados-reais nao, mas " if escolha == "nao" else "pulado: ")
                                  + por_que)
        self.pytest(passo + " (" + por_que + ")", "reais", {"ADT_REAL_DATA_DIR": str(ROOT)}, reais=True)

    def integridade(self):
        passo = "integridade da base versionada"
        print(f"\n== {passo}", flush=True)
        codigo, texto, segundos = self.rodar("integridade", [sys.executable, "backend/brazil_data.py", "diagnostico"], ROOT)
        estado = ultima(texto, r'"integridade":\s*"([a-z_]+)"') or "desconhecida"
        self.registrar(passo, "PASSOU" if codigo == 0 and estado == "verificada" else "FALHOU",
                       f'"integridade": "{estado}"', segundos)

    def resumo(self):
        print("\n## Resumo da verificação completa\n")
        print("| Passo | Resultado | Detalhe | Tempo |\n|---|---|---|---|")
        for passo, situacao, detalhe, segundos in self.resultados:
            print(f"| {passo} | {situacao} | {detalhe} | {segundos:.0f} s |")
        falhas = [r for r in self.resultados if r[1] == "FALHOU"]
        fora = [r for r in self.resultados if r[1] == "FORA (OBRIGATÓRIO)"]
        if falhas:
            print(f"\n**{len(falhas)} passo(s) falharam: não envie.** Logs em {self.pasta}")
            return 1
        if fora:
            print(f"\n**Verificação incompleta: um passo obrigatório ficou de fora. Não envie.** Logs em {self.pasta}")
            return 2
        print(f"\n**Todos os passos passaram.** Logs em {self.pasta}")
        return 0


def main():
    parser = argparse.ArgumentParser(description="Verificação completa local, fora do fluxo normal (AGENTS.md, seção 4).")
    parser.add_argument("--dados-reais", choices=("auto", "sim", "nao"), default="auto",
                        help="auto (padrão): só quando a mudança toca o motor, a API ou os dados")
    parser.add_argument("--npm-ci", action="store_true", help="roda o npm ci mesmo sem mudança nas dependências")
    parser.add_argument("--canal", choices=("chrome", "chromium"), help="navegador das jornadas (padrão: chrome)")
    parser.add_argument("--parar-na-falha", action="store_true", help="interrompe no primeiro passo que falhar")
    args = parser.parse_args()
    for fluxo in (sys.stdout, sys.stderr):
        fluxo.reconfigure(encoding="utf-8", errors="replace")  # saída redirecionada no Windows usaria cp1252
    verificacao = Verificacao(args)
    print(f"Verificação completa em {ROOT}\nLogs: {verificacao.pasta}", flush=True)
    try:
        verificacao.pytest("backend (pytest)", "backend")
        verificacao.frontend()
        verificacao.navegador()
        verificacao.governanca()
        verificacao.dados_reais()
        verificacao.integridade()
    except KeyboardInterrupt:
        print("\nInterrompida.", flush=True)
    finally:
        shutil.rmtree(verificacao.temporaria, ignore_errors=True)
    sys.exit(verificacao.resumo())


if __name__ == "__main__":
    main()
