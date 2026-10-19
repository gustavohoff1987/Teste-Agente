"""A verificação de governança do CI também precisa ser testada: uma guarda quebrada aprovaria tudo em silêncio."""
import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_SPEC = importlib.util.spec_from_file_location("verificar_governanca", ROOT / ".github" / "scripts" / "verificar_governanca.py")
gov = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(gov)


def test_classifica_arquivos_que_podem_mudar_comportamento():
    for caminho in ("frontend/src/App.tsx", "frontend/package.json", "backend/main.py", "backend/requirements.txt",
                    "dados/brasil/manifesto.json", "Dados_Brasil.xlsx", "Dados_Municipios_Brasil.csv",
                    "Dados_Estados_Brasil.csv"):
        assert gov.afeta_comportamento(caminho), caminho
    for caminho in ("backend/tests/ui_block1_smoke.py", "backend/tests/test_engine.py", "Docs/BLOCO1.md",
                    "README.md", ".github/workflows/ci.yml", "AGENTS.md"):
        assert not gov.afeta_comportamento(caminho), caminho


@pytest.mark.parametrize("mensagem", [
    "test: identificador estável\n\nComportamento: sem alteração — só um atributo para testes",
    "x\n\ncomportamento: sem alteracao",
    "x\n\n  Comportamento:  Sem Alteração.",
])
def test_declaracao_explicita_de_ausencia_de_mudanca(mensagem):
    assert gov.declara_sem_alteracao(mensagem)


@pytest.mark.parametrize("mensagem", [
    "feat: muda a tela",
    "fix: x\n\nComportamento: alterado na tela de resultados",
    "refactor: sem alteração de comportamento",  # precisa ser a linha explícita, não uma frase solta
])
def test_sem_declaracao_explicita(mensagem):
    assert not gov.declara_sem_alteracao(mensagem)


def test_registro_cita_commit_pelo_hash_curto_isolado():
    sha = "abcdef1234567890abcdef1234567890abcdef12"
    assert gov.registro_cita(sha, "- 15/10/2026 · `abcdef1` · painel retirado")
    assert gov.registro_cita(sha, "commit ABCDEF1234567")
    assert not gov.registro_cita(sha, "versão " + "0" * 10 + "abcdef1" + "0" * 47)  # dentro de um SHA-256
    assert not gov.registro_cita(sha, "abcdef")  # menos de 7 caracteres
    assert not gov.registro_cita(sha, "abcdef2")  # outro commit


@pytest.fixture
def repo(tmp_path):
    def git(*args):
        return subprocess.run(["git", "-c", "user.name=Teste", "-c", "user.email=teste@example.com", *args],
                              cwd=tmp_path, check=True, capture_output=True, text=True).stdout.strip()

    def commit(arquivos, mensagem):
        for caminho, conteudo in arquivos.items():
            alvo = tmp_path / caminho
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_text(conteudo, encoding="utf-8")
        git("add", "-A")
        git("commit", "-q", "-m", mensagem)
        return git("rev-parse", "HEAD")

    git("init", "-q")
    return tmp_path, commit


def test_commit_de_produto_sem_registro_e_apontado_e_pode_ser_regularizado(repo):
    raiz, commit = repo
    base = commit({gov.REGISTRO: "# Registro\n"}, "base")
    sem_registro = commit({"frontend/src/App.tsx": "a"}, "feat: muda a tela")
    commit({"backend/main.py": "b"}, "refactor: extrai função\n\nComportamento: sem alteração — refatoração pura")
    commit({"backend/main.py": "c", gov.REGISTRO: "# Registro\n- novo cálculo\n"}, "feat: novo cálculo registrado")
    commit({"backend/tests/test_x.py": "t", "Docs/OUTRO.md": "d"}, "test: só testes e documentação")
    violacoes, verificados = gov.verificar_registro(raiz, base)
    assert verificados == 4
    assert [(v.sha, v.arquivos) for v in violacoes] == [(sem_registro, ["frontend/src/App.tsx"])]
    # Regularização sem reescrever o histórico: o registro passa a citar o commit.
    commit({gov.REGISTRO: "# Registro\n- novo cálculo\n- `" + sem_registro[:7] + "` tela alterada\n"}, "docs: registra")
    assert gov.verificar_registro(raiz, base)[0] == []


def test_mudanca_nos_dados_versionados_tambem_exige_registro(repo):
    raiz, commit = repo
    base = commit({gov.REGISTRO: "# Registro\n"}, "base")
    alterado = commit({"Dados_Municipios_Brasil.csv": "municipio;quantidade\n"}, "Add files via upload")
    assert [v.sha for v in gov.verificar_registro(raiz, base)[0]] == [alterado]


def test_clone_raso_nao_e_aprovado_em_silencio(tmp_path, repo):
    raiz, commit = repo
    base = commit({gov.REGISTRO: "# Registro\n"}, "base")
    commit({"backend/main.py": "x"}, "feat: x")
    raso = tmp_path.parent / (tmp_path.name + "-raso")
    subprocess.run(["git", "clone", "-q", "--depth", "1", raiz.as_uri(), str(raso)], check=True, capture_output=True)
    with pytest.raises(RuntimeError, match="histórico incompleto"):
        gov.verificar_registro(raso, base)


def test_roteiro_de_navegador_fora_do_ci_e_apontado(tmp_path):
    testes = tmp_path / "backend" / "tests"
    testes.mkdir(parents=True)
    for nome in ("ui_support.py", "ui_registrado_smoke.py", "ui_esquecido_smoke.py"):
        (testes / nome).write_text("", encoding="utf-8")
    (testes / "run_ui_checks.py").write_text(
        'SUITES = {"a": {"roteiros": [("ui_registrado_smoke.py", {})]},\n'
        '          "b": {"roteiros": [("ui_removido_smoke.py", {})]}}\n'
        "def registered_scripts():\n"
        '    return sorted({n for s in SUITES.values() for n, _ in s["roteiros"]})\n', encoding="utf-8")
    fluxo = tmp_path / ".github" / "workflows"
    fluxo.mkdir(parents=True)
    (fluxo / "ci.yml").write_text("      - run: python backend/tests/run_ui_checks.py --suite a\n", encoding="utf-8")
    problemas = "\n".join(gov.verificar_roteiros(tmp_path))
    assert "ui_esquecido_smoke.py não roda no CI" in problemas
    assert "ui_removido_smoke.py, que não existe" in problemas
    assert "a suíte 'b'" in problemas
    assert "ui_registrado_smoke.py" not in problemas and "ui_support.py" not in problemas


def test_repositorio_atual_nao_tem_jornada_de_navegador_fora_do_ci():
    assert gov.verificar_roteiros(ROOT) == []
