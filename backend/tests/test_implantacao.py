"""Mecanismos da implantação (01/11/2026; Docs/implantacao/), conferidos com respostas simuladas, sem rede e sem chave:
- a proteção dos ambientes antes dos workflows protegidos (validacao-gemini-real.yml, imagem.yml e pages.yml): a execução para
  quando o repositório não está público (desde 02/11/2026), o ambiente não existe, não tem revisor, aceita outras etiquetas ou
  ramos, o gatilho não é a etiqueta ou o commit não pertence ao ramo de preparação;
- a validação real pelo contêiner: sem o segredo, nenhum pedido; o teto rígido de chamadas; um 429 real encerra; as mensagens
  espaçadas; o resumo nas anotações da execução, sem textos e sem o padrão de chave (desde 02/11/2026);
- o padrão de chave do Google: achado por arquivo e contagem, nunca mostrado;
- os workflows: só os gatilhos previstos, o ci.yml com o ramo de preparação e o job do contêiner, e nenhum gatilho manual.
"""
import importlib.util
import json
import re
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
                                           ("pages.yml", "publicacao-pages-*"), ("teste-gatilho.yml", "teste-gatilho-*")])
def test_workflows_protegidos_so_rodam_por_etiqueta(nome, etiqueta):
    texto, topo = gatilhos(nome)
    assert re.search(r"on:\s*\n\s*push:\s*\n\s*tags:\s*\[\s*\"" + re.escape(etiqueta) + r"\"\s*\]", topo), topo
    for proibido in ("workflow_dispatch", "repository_dispatch", "workflow_run", "pull_request", "schedule", "branches"):
        assert proibido not in topo, (nome, proibido)
    assert "permissions:" in topo


@pytest.mark.parametrize("nome,ambiente", [("validacao-gemini-real.yml", "gemini-real"), ("imagem.yml", "producao"),
                                          ("pages.yml", "github-pages")])
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


def test_verificacao_previa_aponta_projeto_recursos_e_limites_fora_do_previsto():
    itens = previa.verificar(gcloud_simulado(projeto="outro", maximo="3", memoria="4Gi", orcamento=False,
                                             extras=("cloudbuild.googleapis.com",)), "agente-diagnostico-territorial", "us-east1")
    falhas = {nome for situacao, nome, _ in itens if situacao == "FALHA"}
    assert {"projeto ativo", "região", "orçamento de alertas de R$ 11", "serviço: máximo de instâncias", "serviço: memória"} <= falhas
    assert any(situacao == "ATENÇÃO" and "cloudbuild" in detalhe for situacao, _, detalhe in itens)
