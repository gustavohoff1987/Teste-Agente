"""Mecanismos da implantação (01/11/2026; Docs/implantacao/), conferidos com respostas simuladas, sem rede e sem chave:
- a proteção dos ambientes antes dos workflows protegidos (validacao-gemini-real.yml e imagem.yml): a execução para
  quando o repositório não está público (desde 02/11/2026), o ambiente não existe, não tem revisor, aceita outras etiquetas ou
  ramos, o gatilho não é a etiqueta ou o commit não pertence ao ramo de preparação;
- a validação real pelo contêiner: sem o segredo, nenhum pedido; o teto rígido de chamadas; um 429 real encerra; as mensagens
  espaçadas; o resumo nas anotações da execução, sem textos e sem o padrão de chave (desde 02/11/2026);
- o padrão de chave do Google: achado por arquivo e contagem, nunca mostrado;
- os workflows: só os gatilhos previstos, o ci.yml com o ramo de preparação e o job do contêiner, e nenhum gatilho manual;
  desde a D-3 (07/11/2026), nenhum publica no Pages nem usa a variável VITE_API_BASE_URL do repositório ou o ambiente
  github-pages: a interface é publicada pelo repositório de destino (Docs/implantacao/destino/publicar.yml);
- a verificação prévia (F2-0): só leitura, e ausência de resposta nunca vale como aprovação (desde 05/11/2026): o gcloud roda
  sem entrada, sem perguntas e com limite de tempo real, os orçamentos sem resposta ficam MANUAL e as demais consultas, FALHA;
  a saída é sempre em UTF-8, com a marca BOM só quando redirecionada no Windows, e nenhum caractere encerra o script (desde
  06/11/2026).
"""
import codecs
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / ".github" / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"


def carregar(nome):
    especificacao = importlib.util.spec_from_file_location(nome, SCRIPTS / (nome + ".py"))
    modulo = importlib.util.module_from_spec(especificacao)
    especificacao.loader.exec_module(modulo)
    return modulo


protecao = carregar("conferir_protecao")
validacao = carregar("validar_gemini_conteiner")
chave = carregar("verificar_chave_google")
anotar = carregar("anotar_validacao")
origem = carregar("conferir_origem")

REPO, AMBIENTE, PADRAO, RAMO = "gustavohoff1987/Teste-Agente", "gemini-real", "validacao-gemini-real-*", "implantacao/cloud-run-pages"
COMMIT, REF = "a" * 40, "refs/tags/validacao-gemini-real-20261102"
REVISOR = {"type": "required_reviewers", "prevent_self_review": False,
           "reviewers": [{"type": "User", "reviewer": {"login": "responsavel"}}]}


def api_simulada(ambiente=None, politicas=None, comparacao="behind", status_do_ambiente=200, repositorio=None,
                 status_do_repositorio=200):
    """A API do GitHub simulada: a visibilidade do repositório, o ambiente, as regras de implantação dele e a comparação do
    commit com o ramo."""
    repositorio = repositorio if repositorio is not None else {"full_name": REPO, "private": False, "visibility": "public"}
    ambiente = ambiente if ambiente is not None else {
        "name": AMBIENTE, "protection_rules": [REVISOR, {"type": "branch_policy"}],
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}}
    politicas = politicas if politicas is not None else [{"name": PADRAO, "type": "tag"}]
    pedidos = []

    def api(caminho):
        pedidos.append(caminho)
        if caminho == f"/repos/{REPO}":
            return (status_do_repositorio, repositorio if status_do_repositorio == 200 else {"message": "Forbidden"})
        if caminho == f"/repos/{REPO}/environments/{AMBIENTE}":
            return (status_do_ambiente, ambiente if status_do_ambiente == 200 else {"message": "Not Found"})
        if caminho.startswith(f"/repos/{REPO}/environments/{AMBIENTE}/deployment-branch-policies"):
            return 200, {"total_count": len(politicas), "branch_policies": politicas}
        if caminho == f"/repos/{REPO}/compare/{RAMO}...{COMMIT}":
            return 200, {"status": comparacao}
        raise AssertionError("pedido inesperado: " + caminho)
    api.pedidos = pedidos
    return api


def test_protecao_confere_quando_tudo_esta_como_previsto():
    api = api_simulada()
    assert protecao.conferir(api, REPO, AMBIENTE, PADRAO, RAMO, COMMIT, REF) == []
    assert api.pedidos[0] == f"/repos/{REPO}"  # a visibilidade é a primeira conferência
    assert protecao.conferir(api_simulada(comparacao="identical"), REPO, AMBIENTE, PADRAO, RAMO, COMMIT, REF) == []


@pytest.mark.parametrize("caso,api,ref,trecho", [
    ("o repositório é privado", api_simulada(repositorio={"private": True, "visibility": "private"}), REF,
     "não está público"),
    ("o repositório é interno", api_simulada(repositorio={"private": True, "visibility": "internal"}), REF,
     "não está público"),
    ("visibilidade incoerente", api_simulada(repositorio={"private": False, "visibility": "internal"}), REF,
     "não está público"),
    ("visibilidade ausente", api_simulada(repositorio={"full_name": REPO}), REF, "não está público"),
    ("visibilidade ilegível", api_simulada(status_do_repositorio=403), REF, "visibilidade do repositório"),
    ("o ambiente não existe", api_simulada(status_do_ambiente=404), REF, "não existe"),
    ("sem revisor obrigatório", api_simulada(ambiente={"name": AMBIENTE, "protection_rules": [{"type": "branch_policy"}],
                                                        "deployment_branch_policy": {"protected_branches": False,
                                                                                     "custom_branch_policies": True}}),
     REF, "revisor obrigatório"),
    ("revisor sem ninguém", api_simulada(ambiente={"name": AMBIENTE, "protection_rules": [{**REVISOR, "reviewers": []}],
                                                    "deployment_branch_policy": {"protected_branches": False,
                                                                                 "custom_branch_policies": True}}),
     REF, "revisor obrigatório"),
    ("sem regra de implantação", api_simulada(ambiente={"name": AMBIENTE, "protection_rules": [REVISOR],
                                                         "deployment_branch_policy": None}), REF, "não restringe"),
    ("só ramos protegidos", api_simulada(ambiente={"name": AMBIENTE, "protection_rules": [REVISOR],
                                                    "deployment_branch_policy": {"protected_branches": True,
                                                                                 "custom_branch_policies": False}}),
     REF, "não restringe"),
    ("aceita outras etiquetas", api_simulada(politicas=[{"name": PADRAO, "type": "tag"}, {"name": "*", "type": "tag"}]),
     REF, "aceita outras"),
    ("aceita um ramo", api_simulada(politicas=[{"name": PADRAO, "type": "tag"}, {"name": "main", "type": "branch"}]),
     REF, "aceita outras"),
    ("padrão de etiqueta diferente", api_simulada(politicas=[{"name": "validacao-*", "type": "tag"}]), REF, "aceita outras"),
    ("o commit não pertence ao ramo", api_simulada(comparacao="diverged"), REF, "não pertence ao ramo"),
    ("o commit está à frente do ramo", api_simulada(comparacao="ahead"), REF, "não pertence ao ramo"),
    ("o gatilho é um ramo", api_simulada(), "refs/heads/implantacao/cloud-run-pages", "não é uma etiqueta"),
    ("outra etiqueta", api_simulada(), "refs/tags/imagem-1", "não é uma etiqueta"),
])
def test_protecao_para_a_execucao_sem_chamadas(caso, api, ref, trecho):
    problemas = protecao.conferir(api, REPO, AMBIENTE, PADRAO, RAMO, COMMIT, ref)
    assert problemas and any(trecho in p for p in problemas), (caso, problemas)
    assert all(not caminho.startswith("/repos/" + REPO + "/actions/secrets") for caminho in api.pedidos)


def test_protecao_sai_com_erro_e_nada_segue(monkeypatch, capsys):
    monkeypatch.setattr(protecao, "api_do_github", api_simulada(status_do_ambiente=404))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    monkeypatch.setenv("GITHUB_REF", REF)
    assert protecao.main(["--ambiente", AMBIENTE, "--etiquetas", PADRAO, "--ramo", RAMO]) == 1
    assert "nada segue" in capsys.readouterr().out


def test_repositorio_que_nao_esta_publico_encerra_a_execucao_mesmo_com_o_ambiente_em_ordem(monkeypatch, capsys):
    """O caso dos três workflows protegidos, que chamam todos o mesmo script antes do job com ambiente."""
    monkeypatch.setattr(protecao, "api_do_github", api_simulada(repositorio={"private": True, "visibility": "private"}))
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO)
    monkeypatch.setenv("GITHUB_SHA", COMMIT)
    monkeypatch.setenv("GITHUB_REF", REF)
    assert protecao.main(["--ambiente", AMBIENTE, "--etiquetas", PADRAO, "--ramo", RAMO]) == 1
    saida = capsys.readouterr().out
    assert "::error title=Proteção do ambiente gemini-real::o repositório" in saida and "não está público" in saida
    assert "1 problema(s); nada segue" in saida


# ---------------------------------------------------------------------------------------------- origem da 2ª publicação

ORIGEM_REPO, ORIGEM_RAMO, ORIGEM_SHA = "gustavohoff1987/Teste-Agente", "implantacao/cloud-run-pages", "b" * 40


def api_da_origem(comparacao="behind", execucoes=None, status_das_execucoes=200):
    """A API pública simulada: a comparação do commit com o ramo e as execuções do CI nele."""
    execucoes = execucoes if execucoes is not None else [
        {"name": "CI Portal Experimental", "status": "completed", "conclusion": "cancelled"},
        {"name": "CI Portal Experimental", "status": "completed", "conclusion": "success"}]
    pedidos = []

    def api(caminho):
        pedidos.append(caminho)
        if caminho == f"/repos/{ORIGEM_REPO}/compare/{ORIGEM_RAMO}...{ORIGEM_SHA}":
            return 200, {"status": comparacao}
        if caminho.startswith(f"/repos/{ORIGEM_REPO}/actions/runs?head_sha={ORIGEM_SHA}&event=push"):
            return status_das_execucoes, {"workflow_runs": execucoes}
        raise AssertionError("pedido inesperado: " + caminho)
    api.pedidos = pedidos
    return api


def test_origem_confere_com_o_commit_no_ramo_e_o_ci_em_sucesso():
    assert origem.conferir(api_da_origem(), ORIGEM_REPO, ORIGEM_RAMO, ORIGEM_SHA, "CI Portal Experimental") == []
    assert origem.conferir(api_da_origem(comparacao="identical"), ORIGEM_REPO, ORIGEM_RAMO, ORIGEM_SHA,
                           "CI Portal Experimental") == []


@pytest.mark.parametrize("caso,api,commit,trecho", [
    ("SHA curto", api_da_origem(), "b" * 7, "não é um SHA completo"),
    ("SHA vazio", api_da_origem(), "", "não é um SHA completo"),
    ("fora do ramo", api_da_origem(comparacao="diverged"), ORIGEM_SHA, "não pertence ao ramo"),
    ("à frente do ramo", api_da_origem(comparacao="ahead"), ORIGEM_SHA, "não pertence ao ramo"),
    ("CI reprovado", api_da_origem(execucoes=[{"name": "CI Portal Experimental", "status": "completed",
                                               "conclusion": "failure"}]), ORIGEM_SHA, "não terminou em sucesso"),
    ("CI em andamento", api_da_origem(execucoes=[{"name": "CI Portal Experimental", "status": "in_progress",
                                                  "conclusion": None}]), ORIGEM_SHA, "não terminou em sucesso"),
    ("só outro workflow", api_da_origem(execucoes=[{"name": "Teste de gatilho por etiqueta", "status": "completed",
                                                    "conclusion": "success"}]), ORIGEM_SHA, "nenhuma execução"),
    ("execuções ilegíveis", api_da_origem(status_das_execucoes=403), ORIGEM_SHA, "não foi possível ler"),
])
def test_origem_para_antes_do_build(caso, api, commit, trecho):
    problemas = origem.conferir(api, ORIGEM_REPO, ORIGEM_RAMO, commit, "CI Portal Experimental")
    assert problemas and any(trecho in p for p in problemas), (caso, problemas)


def test_modelo_do_workflow_do_destino_so_publica_por_etiqueta_depois_das_conferencias():
    texto = (ROOT / "Docs" / "implantacao" / "destino" / "publicar.yml").read_text(encoding="utf-8")
    topo = texto.split("\njobs:", 1)[0]
    assert re.search(r"on:\s*\n\s*push:\s*\n\s*tags:\s*\[\s*\"publicacao-pages-\*\"\s*\]", topo), topo
    for proibido in ("workflow_dispatch", "repository_dispatch", "workflow_run", "pull_request", "schedule", "branches"):
        assert proibido not in topo, proibido
    assert "secrets." not in texto
    # As conferências usam as cópias revisadas do próprio destino, nunca as do commit conferido (origem/).
    assert "python3 .github/scripts/conferir_protecao.py --ambiente github-pages" in texto
    assert "python3 .github/scripts/conferir_origem.py --repositorio gustavohoff1987/Teste-Agente" in texto
    assert "origem/.github/scripts" not in texto
    build = texto.split("\n  build:\n", 1)[1].split("\n  publicar:\n", 1)[0]
    assert "needs: conferir" in build and "ADT_BASE_DA_PAGINA: /\n" in build and "verificar_chave_google.py" in build
    publicar = texto.split("\n  publicar:\n", 1)[1]
    assert "needs: build" in publicar and "name: github-pages" in publicar and "pages: write" in publicar
    assert "pages: write" not in texto.split("\n  publicar:\n", 1)[0]


def test_origem_sai_com_erro_e_nada_segue(monkeypatch, capsys):
    monkeypatch.setattr(origem, "api_do_github", api_da_origem(comparacao="diverged"))
    assert origem.main(["--repositorio", ORIGEM_REPO, "--ramo", ORIGEM_RAMO, "--commit", ORIGEM_SHA]) == 1
    saida = capsys.readouterr().out
    assert "::error title=Origem da publicação::" in saida and "nada segue" in saida


# ---------------------------------------------------------------------------------------------- validação real

def test_sem_o_segredo_nenhum_pedido_sai(monkeypatch, capsys, tmp_path):
    import httpx

    class Proibido:
        def __init__(self, *args, **kwargs):
            raise AssertionError("nenhum pedido sem o segredo")
    monkeypatch.setattr(httpx, "Client", Proibido)
    for vazio in ("", "   "):
        monkeypatch.setenv("GEMINI_API_KEY", vazio)
        assert validacao.chave_configurada() is False
        assert validacao.main(["--url", "http://127.0.0.1:1", "--url-chave-invalida", "http://127.0.0.1:2",
                               "--saida", str(tmp_path / "relatorio")]) == 1
    assert "nada foi enviado" in capsys.readouterr().out
    monkeypatch.setenv("GEMINI_API_KEY", "qualquer")
    assert validacao.chave_configurada() is True


def test_o_teto_e_rigido_e_cada_mensagem_reserva_o_maximo_dela():
    orcamento = validacao.Orcamento(20)
    assert orcamento.cabe() and orcamento.saldo() == 20
    orcamento.registrar(18)
    assert not orcamento.cabe() and orcamento.cabe(2) and not orcamento.cabe(3)
    assert validacao.MAXIMO_POR_MENSAGEM == 3


class Resposta:
    def __init__(self, status, corpo):
        self.status_code, self._corpo = status, corpo

    def json(self):
        return self._corpo


class ContainerSimulado:
    """O contêiner simulado: cada mensagem à conversa conta uma chamada; `respostas` dá o corpo de cada uma."""

    def __init__(self, respostas):
        self.respostas, self.usadas, self.pedidos = list(respostas), 0, []

    def get(self, caminho):
        assert caminho == "/api/llm/status"
        return Resposta(200, {"configured": True, "model": "gemini-3.5-flash-lite", "disponivel": True,
                              "requests_used_today": self.usadas})

    def post(self, caminho, **kwargs):
        self.pedidos.append(caminho)
        if caminho == "/api/session":
            return Resposta(200, {"token": "t"})
        if caminho == "/api/inspect":
            return Resposta(200, {"source": {"version": "v"}, "suggested_mapping": {}})
        if caminho == "/api/analyze":
            return Resposta(200, {"result_id": "r"})
        self.usadas += 1
        return Resposta(200, self.respostas.pop(0) if self.respostas else {"reply": "ok"})


def test_um_429_real_encerra_a_validacao_sem_novas_chamadas():
    simulado = ContainerSimulado([{"reply": "ok"}, {"indisponibilidade": {"tipo": "cota"}}])
    etapas = []
    with pytest.raises(validacao.Interrompida, match="429"):
        validacao.validar(simulado, validacao.Orcamento(20), etapas)
    assert simulado.usadas == 2
    assert [p for p in simulado.pedidos if "llm" in p] == ["/api/llm/interpret", "/api/llm/interpret-context"]


def test_sem_saldo_nenhuma_mensagem_comeca():
    simulado = ContainerSimulado([])
    with pytest.raises(validacao.Interrompida, match="teto"):
        validacao.validar(simulado, validacao.Orcamento(2), [])
    assert simulado.usadas == 0


def test_o_relatorio_da_validacao_nao_leva_textos(tmp_path):
    simulado = ContainerSimulado([{"reply": "texto do Gemini sobre o resultado", "redacao": {"origem": "GEMINI_VALIDADO",
                                                                                           "tentativas": 1}}])
    etapas = []
    validacao.validar(simulado, validacao.Orcamento(20), etapas)
    assert "texto do Gemini" not in json.dumps(etapas, ensure_ascii=False)
    assert any(e.get("origem") == "GEMINI_VALIDADO" for e in etapas)


def test_o_ritmo_espaca_o_inicio_das_mensagens():
    agora, esperas = [100.0], []

    def dormir(segundos):
        esperas.append(segundos)
        agora[0] += segundos
    ritmo = validacao.Ritmo(10, relogio=lambda: agora[0], dormir=dormir)
    ritmo.esperar()  # a primeira não espera
    agora[0] += 3
    ritmo.esperar()  # 3 s depois da anterior: espera os 7 que faltam
    agora[0] += 12
    ritmo.esperar()  # 12 s depois: segue
    assert esperas == [7.0]


def test_cada_mensagem_da_validacao_passa_pelo_ritmo():
    class Contador:
        intervalo = 10

        def __init__(self):
            self.inicios = 0

        def esperar(self):
            self.inicios += 1

        def marcar(self):
            pass
    contador = Contador()
    validacao.validar(ContainerSimulado([]), validacao.Orcamento(20), [], contador)
    assert contador.inicios == 4  # a interpretação, a pergunta, a explicação mais simples e a pergunta conceitual


RELATORIO_SANITIZADO = {
    "teto": 20, "chamadas_usadas": 17, "interrompida": None, "data": "2026-11-02 12:00:00", "etapas": [
        {"etapa": "estado do provedor", "configurado": True, "modelo": "gemini-3.5-flash-lite", "disponivel": True},
        {"etapa": "autenticação e modelo (interpretação)", "status": 200, "tempo_s": 2.1, "chamadas": 1,
         "origem": "GEMINI_VALIDADO", "tentativas": 1, "indisponibilidade": None},
        {"etapa": "roteiro validar_gemini_real.py", "codigo": 0, "chamadas": 12, "turnos": [
            {"cenario": "B continuidade", "status": 200, "tempo_s": 3.4, "canal": "conversa", "origem": "GEMINI_VALIDADO",
             "tentativas": 1, "indisponibilidade": None}]},
        {"etapa": "chave inválida", "status": 200, "tempo_s": 0.4, "indisponibilidade": "configuracao",
         "causa": "configuracao", "escopo": "global", "mensagem_de_configuracao": True}]}


def test_o_resumo_da_validacao_vai_as_anotacoes_em_ate_quatro(tmp_path, capsys):
    arquivo = tmp_path / "validacao-gemini-real.json"
    arquivo.write_text(json.dumps(RELATORIO_SANITIZADO, ensure_ascii=False), encoding="utf-8")
    assert anotar.main([str(arquivo)]) == 0
    linhas = capsys.readouterr().out.splitlines()
    assert len(linhas) == 4 and all(linha.startswith("::notice title=Validação real%3A ") for linha in linhas)
    assert "chamadas reais usadas 17; sem interrupção" in linhas[0]
    assert "autenticação e modelo (interpretação): status 200, tempo_s 2.1, chamadas 1" in linhas[1]
    assert "%0A- B continuidade: status 200, tempo_s 3.4, canal conversa" in linhas[2]
    assert "mensagem_de_configuracao True" in linhas[3]


def test_anotacao_com_o_padrao_de_chave_nao_sai(tmp_path, capsys):
    classica = "AIza" + "Sy" + "D" * 33  # montada aqui, como nos testes do padrão
    arquivo = tmp_path / "validacao-gemini-real.json"
    arquivo.write_text(json.dumps({**RELATORIO_SANITIZADO, "interrompida": "erro " + classica}), encoding="utf-8")
    assert anotar.main([str(arquivo)]) == 1
    saida = capsys.readouterr().out
    assert classica not in saida and "1 anotação(ões) omitida(s)" in saida
    assert saida.count("::notice") == 3


def test_sem_relatorio_a_anotacao_avisa(tmp_path, capsys):
    assert anotar.main([str(tmp_path / "ausente.json")]) == 1
    assert "sem relatório" in capsys.readouterr().out


# ---------------------------------------------------------------------------------------------- padrão de chave

def test_padrao_de_chave_achado_por_arquivo_e_contagem_sem_mostrar_o_trecho(tmp_path, capsys):
    classica = "AIza" + "Sy" + "B" * 33  # 35 caracteres depois de AIza, montada aqui (nada parecido fica versionado)
    nova = "AQ." + "Ab3_" * 13
    (tmp_path / "limpo.js").write_text("const a = 'AIza curto'; const b = 'AQ.curto';", encoding="utf-8")
    (tmp_path / "relatorio.json").write_text(json.dumps({"x": classica, "y": [classica]}), encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "log.txt").write_bytes(b"\x00\x01" + nova.encode() + b"\n")
    examinados, achados = chave.verificar([str(tmp_path)])
    assert examinados == 3
    assert sorted((Path(a).name, p, n) for a, p, n in achados) == [("log.txt", "AQ.", 1), ("relatorio.json", "AIza", 2)]
    assert chave.main([str(tmp_path)]) == 1
    saida = capsys.readouterr().out
    assert classica not in saida and nova not in saida and "relatorio.json" in saida
    assert chave.main([str(tmp_path / "limpo.js")]) == 0


def test_padrao_de_chave_em_arquivo_grande_conta_cada_ocorrencia_uma_vez(tmp_path, monkeypatch):
    monkeypatch.setattr(chave, "LIMITE_POR_ARQUIVO", 1000)
    classica = "AIza" + "Q" * 35
    (tmp_path / "grande.bin").write_bytes(b"x" * 5000 + b" " + classica.encode() + b" " + b"y" * 5000)
    assert chave.verificar([str(tmp_path)])[1] == [(str(tmp_path / "grande.bin"), "AIza", 1)]


# ---------------------------------------------------------------------------------------------- workflows

def gatilhos(nome):
    texto = (WORKFLOWS / nome).read_text(encoding="utf-8")
    return texto, texto.split("\njobs:", 1)[0]


@pytest.mark.parametrize("nome,etiqueta", [("validacao-gemini-real.yml", "validacao-gemini-real-*"), ("imagem.yml", "imagem-*"),
                                           ("teste-gatilho.yml", "teste-gatilho-*")])
def test_workflows_protegidos_so_rodam_por_etiqueta(nome, etiqueta):
    texto, topo = gatilhos(nome)
    assert re.search(r"on:\s*\n\s*push:\s*\n\s*tags:\s*\[\s*\"" + re.escape(etiqueta) + r"\"\s*\]", topo), topo
    for proibido in ("workflow_dispatch", "repository_dispatch", "workflow_run", "pull_request", "schedule", "branches"):
        assert proibido not in topo, (nome, proibido)
    assert "permissions:" in topo


@pytest.mark.parametrize("nome,ambiente", [("validacao-gemini-real.yml", "gemini-real"), ("imagem.yml", "producao")])
def test_o_job_protegido_so_vem_depois_da_conferencia_da_protecao(nome, ambiente):
    texto, _ = gatilhos(nome)
    assert "conferir_protecao.py --ambiente " + ambiente in texto
    assert f"environment: {ambiente}" in texto or f"name: {ambiente}" in texto
    bloco = texto.split("environment:", 1)[0]
    assert "conferir-protecao" in bloco or "conferir-protecao" in texto.split("needs:", 1)[1][:200]


def test_a_validacao_real_espaca_as_mensagens_e_anota_o_resumo_depois_do_padrao_de_chave():
    texto, _ = gatilhos("validacao-gemini-real.yml")
    assert "--teto 20 --intervalo 10" in texto
    posicao = texto.index("anotar_validacao.py")
    assert texto.index("verificar_chave_google.py") < posicao
    passo = texto[texto.rindex("- name:", 0, posicao):posicao]
    assert "steps.chave.outcome == 'success'" in passo


def test_teste_de_gatilho_sem_ambiente_sem_segredos_e_sem_build():
    texto, _ = gatilhos("teste-gatilho.yml")
    for proibido in ("environment:", "secrets.", "docker build", "npm ", "pip install"):
        assert proibido not in texto, proibido


def test_ci_tem_o_ramo_de_preparacao_e_o_job_do_conteiner_no_resumo():
    texto = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    ramos = re.search(r"branches:\s*\[([^\]]*)\]", texto).group(1)
    assert "implantacao/cloud-run-pages" in ramos and "feat/desafio-adversarial-conversacional" in ramos
    assert "\n  conteiner:\n" in texto
    resumo = texto.split("\n  resumo:\n", 1)[1]
    assert re.search(r"needs:\s*\[[^\]]*\bconteiner\b", resumo)
    assert '"conteiner":' in resumo
    for proibido in ("workflow_dispatch", "repository_dispatch", "workflow_run", "continue-on-error"):
        assert proibido not in texto, proibido


def test_nenhum_segredo_de_repositorio_nos_workflows():
    for arquivo in WORKFLOWS.glob("*.yml"):
        texto = arquivo.read_text(encoding="utf-8")
        segredos = set(re.findall(r"secrets\.([A-Z_]+)", texto))
        if arquivo.name == "validacao-gemini-real.yml":
            assert segredos == {"GEMINI_API_KEY"}, segredos
            assert texto.count("secrets.GEMINI_API_KEY") == 1 and "environment: gemini-real" in texto
        else:
            assert segredos <= {"GITHUB_TOKEN"}, (arquivo.name, segredos)


def test_a_publicacao_antiga_no_pages_saiu_do_teste_agente():
    """D-3 (07/11/2026): o pages.yml saiu, e nenhum workflow daqui publica no Pages nem usa a variável VITE_API_BASE_URL do
    repositório ou o ambiente github-pages (retirados na D3-b). A publicação é a do destino, cujo modelo continua conferido."""
    assert not (WORKFLOWS / "pages.yml").exists()
    for arquivo in WORKFLOWS.glob("*.yml"):
        texto = arquivo.read_text(encoding="utf-8")
        for proibido in ("actions/deploy-pages", "actions/upload-pages-artifact", "pages: write", "github-pages",
                         "vars.VITE_API_BASE_URL"):
            assert proibido not in texto, (arquivo.name, proibido)
    destino = (ROOT / "Docs" / "implantacao" / "destino" / "publicar.yml").read_text(encoding="utf-8")
    assert "actions/deploy-pages" in destino and "name: github-pages" in destino and "vars.VITE_API_BASE_URL" in destino


# ---------------------------------------------------------------------------------------------- verificação prévia (F2-0)

_PREVIA = importlib.util.spec_from_file_location("verificacao_previa", ROOT / "scripts" / "implantacao" / "verificacao_previa.py")
previa = importlib.util.module_from_spec(_PREVIA)
_PREVIA.loader.exec_module(previa)


def gcloud_simulado(projeto="agente-diagnostico-territorial", maximo="1", memoria="2Gi", orcamento=True, extras=()):
    """As respostas de leitura do gcloud, como a CLI as dá; nenhuma escrita é aceita."""
    servico = {"metadata": {"name": "agente-diagnostico-territorial"}, "spec": {"template": {
        "metadata": {"annotations": {"autoscaling.knative.dev/maxScale": maximo, "run.googleapis.com/cpu-throttling": "true",
                                     "run.googleapis.com/startup-cpu-boost": "false"}},
        "spec": {"containerConcurrency": 20, "timeoutSeconds": 150,
                 "containers": [{"resources": {"limits": {"cpu": "1", "memory": memoria}}}]}}}}
    orcamentos = [{"amount": {"specifiedAmount": {"currencyCode": "BRL", "units": "11"}},
                   "thresholdRules": [{"thresholdPercent": p} for p in (0.25, 0.5, 0.75, 1.0)]}] if orcamento else []
    respostas = {
        ("auth", "list"): "responsavel@exemplo.invalid\n", ("config", "get-value"): projeto + "\n",
        ("billing", "projects"): json.dumps({"billingEnabled": True, "billingAccountName": "billingAccounts/0000-1111"}),
        ("billing", "budgets"): json.dumps(orcamentos), ("services", "list"): "run.googleapis.com\n" + "\n".join(extras),
        ("run", "services"): json.dumps([servico]), ("artifacts", "repositories"): json.dumps(
            [{"name": "projects/p/locations/us-central1/repositories/agente-diagnostico-territorial"}]),
        ("iam", "service-accounts"): "adt-execucao@p.iam.gserviceaccount.com\nadt-envio-imagem@p.iam.gserviceaccount.com\n",
        ("secrets", "list"): "projects/1/secrets/gemini-api-key\n", ("iam", "workload-identity-pools"): "projects/1/locations/global/workloadIdentityPools/github\n",
    }

    def rodar(*args):
        assert not ({"create", "delete", "update", "deploy", "add-iam-policy-binding", "enable", "disable"} & set(args)), args
        return 0, respostas[args[:2]]
    return rodar


def test_verificacao_previa_tudo_previsto_so_com_as_conferencias_manuais():
    itens = previa.verificar(gcloud_simulado(), "agente-diagnostico-territorial", "us-central1")
    assert not [i for i in itens if i[0] in ("FALHA", "ATENÇÃO")], itens
    assert any(i[0] == "MANUAL" and "trava de R$ 11" in i[1] for i in itens)


def test_verificacao_previa_nao_toma_listagem_que_falhou_por_nenhum_recurso():
    """Primeira execução real do F2-0 (02/11/2026): com as APIs desligadas, as listagens falham; antes, isso passava calado."""
    simulado = gcloud_simulado()

    def rodar(*args):
        if args[:2] in {("run", "services"), ("artifacts", "repositories")}:
            return 1, "ERROR: permission denied"
        if args[:2] == ("services", "list"):
            return 0, "run.googleapis.com\nartifactregistry.googleapis.com\n"
        return simulado(*args)
    itens = previa.verificar(rodar, "agente-diagnostico-territorial", "us-central1")
    falhas = {nome for situacao, nome, _ in itens if situacao == "FALHA"}
    assert {"serviços do Cloud Run", "repositórios do Artifact Registry"} <= falhas
    assert ("OK", "segredos") in {(s, n) for s, n, _ in itens}  # Secret Manager desligado: nenhum segredo possível
    assert any(n == "segredos" and "desligada" in d for _, n, d in itens)

    def apis_ilegiveis(*args):
        return (1, "ERROR: forbidden") if args[:2] == ("services", "list") else simulado(*args)
    itens = previa.verificar(apis_ilegiveis, "agente-diagnostico-territorial", "us-central1")
    assert ("FALHA", "APIs habilitadas") in {(s, n) for s, n, _ in itens}


def test_verificacao_previa_aceita_a_conta_padrao_do_compute_criada_pelo_google():
    simulado = gcloud_simulado()

    def rodar(*args):
        if args[:2] == ("iam", "service-accounts"):
            return 0, "338451103854-compute@developer.gserviceaccount.com\nadt-execucao@p.iam.gserviceaccount.com\n"
        return simulado(*args)
    itens = previa.verificar(rodar, "agente-diagnostico-territorial", "us-central1")
    assert not [i for i in itens if i[0] in ("FALHA", "ATENÇÃO")], itens
    assert any(n == "conta padrão do Compute" for _, n, _ in itens)


def test_verificacao_previa_aponta_projeto_recursos_e_limites_fora_do_previsto():
    itens = previa.verificar(gcloud_simulado(projeto="outro", maximo="3", memoria="4Gi", orcamento=False,
                                             extras=("cloudbuild.googleapis.com",)), "agente-diagnostico-territorial", "us-east1")
    falhas = {nome for situacao, nome, _ in itens if situacao == "FALHA"}
    assert {"projeto ativo", "região", "orçamento de alertas de R$ 11", "serviço: máximo de instâncias", "serviço: memória"} <= falhas
    assert any(situacao == "ATENÇÃO" and "cloudbuild" in detalhe for situacao, _, detalhe in itens)


# Cada consulta obrigatória e o item que ela reprova quando não se conclui. Em 05/11/2026, a F2-0 parou num TimeoutExpired, e as
# listagens de contas de serviço e de pools de identidade passavam caladas quando falhavam.
OBRIGATORIAS = {("auth", "list"): "conta autenticada", ("config", "get-value"): "projeto ativo",
                ("billing", "projects"): "conta de faturamento", ("services", "list"): "APIs habilitadas",
                ("run", "services"): "serviços do Cloud Run", ("artifacts", "repositories"): "repositórios do Artifact Registry",
                ("iam", "service-accounts"): "contas de serviço", ("secrets", "list"): "segredos",
                ("iam", "workload-identity-pools"): "pools de identidade"}


@pytest.mark.parametrize("resposta", [(previa.SEM_RESPOSTA, "sem resposta em 120 s"), (1, "ERROR: permission denied")])
@pytest.mark.parametrize("consulta", OBRIGATORIAS)
def test_verificacao_previa_consulta_obrigatoria_nao_concluida_e_falha(consulta, resposta):
    simulado = gcloud_simulado(extras=("artifactregistry.googleapis.com", "secretmanager.googleapis.com"))

    def rodar(*args):
        return resposta if args[:2] == consulta else simulado(*args)
    itens = previa.verificar(rodar, "agente-diagnostico-territorial", "us-central1")
    linhas = [(situacao, detalhe) for situacao, nome, detalhe in itens if nome == OBRIGATORIAS[consulta]]
    assert len(linhas) == 1 and linhas[0][0] == "FALHA" and resposta[1] in linhas[0][1], itens


@pytest.mark.parametrize("resposta", [(previa.SEM_RESPOSTA, "sem resposta em 30 s"), (1, "ERROR: API desligada")])
def test_verificacao_previa_orcamentos_sem_resposta_ficam_manuais_e_nao_aprovam(resposta, monkeypatch, capsys):
    simulado = gcloud_simulado()

    def rodar(*args):
        return resposta if args[:2] == ("billing", "budgets") else simulado(*args)
    itens = previa.verificar(rodar, "agente-diagnostico-territorial", "us-central1")
    assert not [i for i in itens if i[0] == "FALHA"], itens
    situacao, detalhe = next((s, d) for s, n, d in itens if n == "orçamento de alertas de R$ 11")
    assert situacao == "MANUAL" and resposta[1] in detalhe and "Console" in detalhe
    monkeypatch.setattr(previa, "gcloud", rodar)
    assert previa.main([]) == 2  # conferência manual pendente não é sucesso
    assert "Sem aprovação: nada segue" in capsys.readouterr().out


def test_verificacao_previa_falha_sai_com_1(monkeypatch, capsys):
    monkeypatch.setattr(previa, "gcloud", gcloud_simulado(projeto="outro"))
    assert previa.main([]) == 1
    assert "Nada segue até corrigir" in capsys.readouterr().out


@pytest.mark.parametrize("sistema, terminal, marca", [("nt", False, True), ("nt", True, False), ("posix", False, False)])
def test_verificacao_previa_chega_ao_fim_em_utf8_com_a_marca_so_redirecionada_no_windows(sistema, terminal, marca, monkeypatch):
    """Redirecionada no Windows, a saída usava o cp1252. Medido em 06/11/2026: `UnicodeEncodeError` na seta do item da trava, 5
    linhas da tabela, sem o resumo e com a saída 1. O erro do gcloud também pode trazer caracteres fora do cp1252. Sem a marca,
    o PowerShell 5.1 relia o texto no cp850; no console ela apareceria como um caractere a mais."""
    simulado = gcloud_simulado()

    def rodar(*args):
        return (1, "ERROR: ✗ sem permissão") if args[:2] == ("billing", "budgets") else simulado(*args)

    class Saida(io.TextIOWrapper):
        def isatty(self):
            return terminal
    bruto = io.BytesIO()
    saida = Saida(bruto, encoding="cp1252", errors="strict")
    monkeypatch.setattr(sys, "stdout", saida)
    monkeypatch.setattr(previa, "os", types.SimpleNamespace(name=sistema))
    monkeypatch.setattr(previa, "gcloud", rodar)
    assert previa.main([]) == 2
    saida.flush()
    assert bruto.getvalue().startswith(codecs.BOM_UTF8) is marca
    texto = bruto.getvalue().decode("utf-8-sig")
    assert "Faturamento → Orçamentos e alertas" in texto and "✗ sem permissão" in texto
    assert texto.rstrip().endswith("conferir os itens MANUAL.")


def test_verificacao_previa_processo_inteiro_com_a_saida_em_cp1252_nao_cai(tmp_path):
    """O script como no redirecionamento do Windows, sem gcloud no caminho: a saída 1 vem das falhas, não de uma exceção."""
    resultado = subprocess.run([sys.executable, previa.__file__], stdin=subprocess.DEVNULL, capture_output=True, timeout=60,
                               env={**os.environ, "PATH": str(tmp_path), "PYTHONIOENCODING": "cp1252"})
    assert b"Traceback" not in resultado.stderr, resultado.stderr
    texto = resultado.stdout.decode("utf-8-sig")
    assert "Faturamento → Orçamentos e alertas" in texto and "Nada segue até corrigir" in texto
    assert resultado.returncode == 1


def test_verificacao_previa_faturamento_sem_resposta_nao_afirma_que_nao_ha_vinculo():
    simulado = gcloud_simulado()

    def rodar(*args):
        return (previa.SEM_RESPOSTA, "sem resposta em 120 s") if args[:2] == ("billing", "projects") else simulado(*args)
    itens = previa.verificar(rodar, "agente-diagnostico-territorial", "us-central1")
    assert not any("sem faturamento vinculado" in detalhe for _, _, detalhe in itens), itens
    assert ("MANUAL", "orçamento de alertas de R$ 11") in {(s, n) for s, n, _ in itens}  # o item não some do resultado


def test_verificacao_previa_lista_de_apis_vazia_nao_passa_por_apis_desligadas():
    simulado = gcloud_simulado()

    def rodar(*args):
        return (0, "") if args[:2] == ("services", "list") else simulado(*args)
    itens = previa.verificar(rodar, "agente-diagnostico-territorial", "us-central1")
    assert ("FALHA", "APIs habilitadas") in {(s, n) for s, n, _ in itens}
    assert not any("desligada" in detalhe for _, _, detalhe in itens), itens


def test_verificacao_previa_o_limite_de_tempo_vale_com_um_processo_neto():
    """Como o gcloud.cmd no Windows: o neto herda os canais de saída e sobrevive ao kill do filho. Medido em 05/11/2026, com
    `subprocess.run(timeout=2)` a exceção só veio aos 12 s, quando o neto terminou."""
    neto = "import time; time.sleep(60)"
    filho = f"import subprocess, sys; subprocess.run([sys.executable, '-c', {neto!r}])"
    inicio = time.monotonic()
    assert previa.executar([sys.executable, "-c", filho], 1) == (previa.SEM_RESPOSTA, "sem resposta em 1 s")
    assert time.monotonic() - inicio < 30


def test_verificacao_previa_gcloud_sem_entrada_sem_perguntas_e_com_o_limite_de_cada_consulta(monkeypatch):
    """Com a API de orçamentos desligada, o gcloud pergunta se deve habilitá-la: nem a pergunta nem a resposta podem existir."""
    leitura = ("import os, sys; print(os.environ['CLOUDSDK_CORE_DISABLE_PROMPTS'], "
               "os.environ['CLOUDSDK_CORE_SHOULD_PROMPT_TO_ENABLE_API'], repr(sys.stdin.read()))")
    assert previa.executar([sys.executable, "-c", leitura], 30) == (0, "1 false ''\n")
    limites = {}

    def executar(comando, limite):
        limites[tuple(comando[1:3])] = limite
        return 0, ""
    monkeypatch.setattr(previa, "executar", executar)
    previa.gcloud("billing", "budgets", "list")
    previa.gcloud("billing", "projects", "describe", "p")
    assert limites == {("billing", "budgets"): 30, ("billing", "projects"): 120}


def test_verificacao_previa_gcloud_ausente_nao_derruba_o_script():
    codigo, motivo = previa.executar([str(ROOT / "nao-existe" / "gcloud")], 1)
    assert codigo == previa.SEM_RESPOSTA and "não pôde ser executado" in motivo
