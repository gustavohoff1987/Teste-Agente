# Roteiro da Fase 2 — implantação do Agente Diagnóstico Territorial da Força de Trabalho na Saúde

Google Cloud Run (serviço de análise) e GitHub Pages (interface). **Nada aqui foi executado.** Cada operação F2-n só acontece
depois de o responsável pelo produto escrever **AUTORIZO F2-n**, que vale só para aquela operação, na ordem abaixo
(seção 13 do comando de implantação de 01/11/2026). Antes de cada uma, o agente apresenta de novo os comandos exatos, o
efeito, o custo esperado e como desfazer. Sem teste de carga. Qualquer passo fora desta lista, que amplie recursos ou que
possa gerar custo não previsto, para e volta ao responsável.

As providências do responsável (P-1 a P-8, V-1 a V-7) estão em [PROVIDENCIAS_DO_RESPONSAVEL.md](PROVIDENCIAS_DO_RESPONSAVEL.md);
o que foi medido e o parecer, em [RELATORIO_IMPLANTACAO.md](RELATORIO_IMPLANTACAO.md).

## Valores fixos

```bash
PROJETO=agente-diagnostico-territorial          # o ID não muda por causa do nome da aplicação
REGIAO=us-central1
SERVICO=agente-diagnostico-territorial          # serviço do Cloud Run
REPOSITORIO=agente-diagnostico-territorial      # repositório Docker do Artifact Registry (igual ao de imagem.yml)
IMAGEM=servico-de-analise                       # nome da imagem (igual ao de imagem.yml)
SA_EXECUCAO=adt-execucao@$PROJETO.iam.gserviceaccount.com        # identidade do serviço no Cloud Run
SA_IMAGEM=adt-envio-imagem@$PROJETO.iam.gserviceaccount.com      # identidade do GitHub Actions para enviar a imagem
ORIGEM=https://gustavohoff1987.github.io        # a origem do Pages (sem caminho), a única no CORS
NUMERO=$(gcloud projects describe $PROJETO --format='value(projectNumber)')
```

Recursos do serviço (decisões que não mudam): 1 vCPU, 2 GiB, mínimo 0 e máximo 1 instância, cobrança por requisição
(`--cpu-throttling`), um processo Uvicorn, acesso público sem login, aumento de CPU na partida **desligado**
(`--no-cpu-boost`; ligado, eleva a CPU e o consumo da trava; só com autorização). A concorrência e o timeout vêm da medição
no CI (relatório, seções C e I): os valores abaixo, **concorrência 20** e **timeout 150 s** (acima do prazo de 100 s da
conversa na tela), são os propostos até o relatório registrar a medição; se ela indicar outros, este roteiro é atualizado antes
do F2-6.

## F2-0 — Verificação prévia (só leitura)

Providências antes: **P-1** (gcloud autenticado na conta e no projeto certos) e **P-2** (trava e alertas conferidos no
Console).

```bash
python scripts/implantacao/verificacao_previa.py --projeto agente-diagnostico-territorial --regiao us-central1
```

O script só lê (gcloud `list`/`describe`) e mostra OK, ATENÇÃO ou MANUAL para: conta autenticada, projeto e região, conta de
faturamento, orçamento só de alertas de R$ 11 com 25/50/75/100%, trava de R$ 11 do Cloud Run (MANUAL: a CLI não a expõe; P-2),
APIs habilitadas e recursos não previstos (serviços, repositórios, contas de serviço, segredos, pools de identidade) e, se o
serviço já existir, mínimo 0, máximo 1, 1 vCPU, 2 GiB, cobrança por requisição, sem aumento de CPU na partida, concorrência e
timeout. Qualquer resultado fora do previsto interrompe a implantação até o responsável decidir. **Efeito:** nenhum. **Custo:**
nenhum. **Desfazer:** nada a desfazer. É obrigatória antes de qualquer implantação (F2-6) e de cada atualização.

## F2-1 — Habilitar as APIs necessárias

```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com cloudresourcemanager.googleapis.com \
  --project=$PROJETO
```

Não habilitar: Cloud Build (`cloudbuild.googleapis.com`; a imagem é construída no GitHub Actions) e Container Scanning
(`containerscanning.googleapis.com`; a varredura de vulnerabilidades do Artifact Registry é cobrada à parte).
**Efeito:** as APIs ficam disponíveis; nada roda. **Custo:** nenhum. **Desfazer:** `gcloud services disable <api> --project=$PROJETO`
(só depois de remover os recursos que a usam).

## F2-2 — Repositório do Artifact Registry com política de limpeza

```bash
gcloud artifacts repositories create $REPOSITORIO --project=$PROJETO --location=$REGIAO --repository-format=docker \
  --description="Imagens do serviço de análise do Agente Diagnóstico Territorial da Força de Trabalho na Saúde"
cat > politica-de-limpeza.json <<'JSON'
[
  {"name": "manter-as-2-mais-recentes", "action": {"type": "Keep"}, "mostRecentVersions": {"keepCount": 2}},
  {"name": "apagar-as-demais-depois-de-1-dia", "action": {"type": "Delete"}, "condition": {"tagState": "any", "olderThan": "86400s"}}
]
JSON
gcloud artifacts repositories set-cleanup-policies $REPOSITORIO --project=$PROJETO --location=$REGIAO \
  --policy=politica-de-limpeza.json --no-dry-run
```

**Efeito:** um repositório privado de imagens; ficam as 2 versões mais recentes (a em uso e a anterior, para o rollback).
**Custo:** a franquia é de 0,5 GB por mês; cada imagem deve ter cerca de 0,2 GB comprimida (estimativa; o tamanho medido no
CI fica no relatório, seção C), então 2 versões ficam dentro dela. Acima, cerca de US$ 0,10 por GB por mês, **fora da trava do Cloud Run**. **Desfazer:**
`gcloud artifacts repositories delete $REPOSITORIO --project=$PROJETO --location=$REGIAO` (apaga as imagens).

## F2-3 — Contas de serviço e federação de identidade restrita ao ambiente `producao`

```bash
gcloud iam service-accounts create adt-execucao --project=$PROJETO \
  --display-name="Agente Diagnóstico Territorial da Força de Trabalho na Saúde - execução no Cloud Run"
gcloud iam service-accounts create adt-envio-imagem --project=$PROJETO \
  --display-name="Agente Diagnóstico Territorial da Força de Trabalho na Saúde - envio da imagem pelo GitHub Actions"
# Envio da imagem: só escrever neste repositório.
gcloud artifacts repositories add-iam-policy-binding $REPOSITORIO --project=$PROJETO --location=$REGIAO \
  --member="serviceAccount:$SA_IMAGEM" --role="roles/artifactregistry.writer"
# Federação: só tokens do repositório gustavohoff1987/Teste-Agente emitidos para o ambiente producao.
gcloud iam workload-identity-pools create github --project=$PROJETO --location=global --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc teste-agente --project=$PROJETO --location=global \
  --workload-identity-pool=github --display-name="Teste-Agente, ambiente producao" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.environment=assertion.environment" \
  --attribute-condition="assertion.repository == 'gustavohoff1987/Teste-Agente' && assertion.environment == 'producao' && assertion.sub == 'repo:gustavohoff1987/Teste-Agente:environment:producao'"
gcloud iam service-accounts add-iam-policy-binding $SA_IMAGEM --project=$PROJETO --role="roles/iam.workloadIdentityUser" \
  --member="principal://iam.googleapis.com/projects/$NUMERO/locations/global/workloadIdentityPools/github/subject/repo:gustavohoff1987/Teste-Agente:environment:producao"
echo "GCP_PROVEDOR_DE_IDENTIDADE=projects/$NUMERO/locations/global/workloadIdentityPools/github/providers/teste-agente"
echo "GCP_CONTA_DE_ENVIO_DE_IMAGEM=$SA_IMAGEM"
```

A conta de execução não recebe nenhum papel além da leitura do segredo (F2-4). Nenhuma chave de conta de serviço é criada.
Os dois valores impressos (não secretos) entram como variáveis do ambiente `producao` (P-3). **Efeito:** identidades sem
acesso a nada além do previsto. **Custo:** nenhum. **Desfazer:** `gcloud iam workload-identity-pools delete github --location=global
--project=$PROJETO` e `gcloud iam service-accounts delete <conta> --project=$PROJETO`.

## F2-4 — Leitura do segredo `gemini-api-key` pela conta de execução

Providência antes: **P-4** (o responsável cria o segredo `gemini-api-key` pelo Console, colando a chave do AI Studio).

```bash
gcloud secrets versions list gemini-api-key --project=$PROJETO --format="table(name,state,createTime)"   # nomes, nunca o valor
gcloud secrets add-iam-policy-binding gemini-api-key --project=$PROJETO \
  --member="serviceAccount:$SA_EXECUCAO" --role="roles/secretmanager.secretAccessor"
```

**Efeito:** só a conta de execução lê o segredo, e só ele. **Custo:** dentro da franquia (6 versões ativas e 10 mil acessos
por mês; o Cloud Run lê o segredo na partida de cada instância). **Desfazer:** `gcloud secrets remove-iam-policy-binding` com os
mesmos parâmetros.

## F2-5 — Enviar a imagem (etiqueta `imagem-*`)

Providências: **P-3** (ambiente `producao` com revisor, etiquetas `imagem-*` e as variáveis da federação) e **P-5** (aprovar
o job). O commit é o último do ramo `implantacao/cloud-run-pages` com o CI em PASS.

```bash
git tag imagem-$(date +%Y%m%d)-1 <commit verificado> && git push origin imagem-$(date +%Y%m%d)-1
```

O workflow `imagem.yml` confere a proteção do ambiente e o commit no ramo, constrói a imagem do commit, repete o teste rápido
do contêiner (saúde, exame da base, documentação desligada, padrão de chave) e a envia ao Artifact Registry pela federação. O
**digest** sai no resumo da execução, para o F2-6. **Custo:** armazenamento (F2-2). **Desfazer:** apagar a versão no Artifact
Registry (`gcloud artifacts docker images delete <imagem>@<digest>`).

## F2-6 — Implantar no Cloud Run, ainda sem acesso público

Antes: F2-0 de novo. Todos os parâmetros explícitos:

```bash
gcloud run deploy $SERVICO --project=$PROJETO --region=$REGIAO \
  --image="$REGIAO-docker.pkg.dev/$PROJETO/$REPOSITORIO/$IMAGEM@sha256:<digest do F2-5>" \
  --execution-environment=gen2 --cpu=1 --memory=2Gi --min-instances=0 --max-instances=1 \
  --concurrency=20 --timeout=150 --cpu-throttling --no-cpu-boost --port=8080 \
  --startup-probe=tcpSocket.port=8080,initialDelaySeconds=0,timeoutSeconds=10,periodSeconds=10,failureThreshold=24 \
  --service-account=$SA_EXECUCAO --set-secrets=GEMINI_API_KEY=gemini-api-key:1 \
  --set-env-vars=ADT_ALLOWED_ORIGINS=$ORIGEM,ADT_DOCUMENTACAO_DA_API=0 \
  --ingress=all --no-allow-unauthenticated --labels=aplicacao=agente-diagnostico-territorial
# Teste pelo proxy autenticado (o token fica com o gcloud; nada é exibido):
gcloud run services proxy $SERVICO --project=$PROJETO --region=$REGIAO --port=18080 &
curl -fsS http://127.0.0.1:18080/api/health
```

- `--set-secrets=…:1`: a versão fixada do segredo (não `latest`).
- A sonda de partida espera a porta até 240 s (24 × 10 s), o limite do Cloud Run; o aquecimento termina antes de a porta
  abrir (relatório, seção C). Sem sonda de vida: o serviço não reinicia por demora de uma operação pesada.
- `gen2`: o mesmo controle de memória (cgroup v2) medido no CI.
**Efeito:** o serviço existe, só para quem tem permissão. **Custo:** entra na trava (tempo de instância ativa). **Desfazer:**
`gcloud run services delete $SERVICO --project=$PROJETO --region=$REGIAO`. **Rollback** de uma revisão nova:
`gcloud run revisions list --service=$SERVICO --project=$PROJETO --region=$REGIAO` e
`gcloud run services update-traffic $SERVICO --project=$PROJETO --region=$REGIAO --to-revisions=<revisão anterior>=100`.

## F2-7 — Liberar o acesso público

```bash
gcloud run services add-iam-policy-binding $SERVICO --project=$PROJETO --region=$REGIAO \
  --member=allUsers --role=roles/run.invoker
```

**Efeito:** qualquer pessoa chama o serviço (o CORS restringe só os navegadores, não é autenticação). **Custo:** entra na trava.
**Desfazer (suspensão manual reversível, sem excluir o serviço):** `gcloud run services remove-iam-policy-binding $SERVICO
--project=$PROJETO --region=$REGIAO --member=allUsers --role=roles/run.invoker`; a interface mostra então "Serviço
temporariamente indisponível".

## F2-8 — Testes de produção sem o Gemini

```bash
URL=$(gcloud run services describe $SERVICO --project=$PROJETO --region=$REGIAO --format='value(status.url)')
curl -fsS "$URL/api/health"
curl -fsS -o /dev/null -w '%{http_code}\n' "$URL/docs"                                   # 404
curl -fsS -X POST -d "dataset=brazil&scope=municipal" "$URL/api/inspect" -o /dev/null -w '%{http_code}\n'   # 200
curl -s -o /dev/null -w '%{http_code}\n' -H "Origin: https://exemplo.invalid" "$URL/api/health"   # 200, sem CORS
```

Uma análise (o gráfico dos estados) e um envio pequeno (CSV de 100 KB) pelo mesmo caminho. **Custo:** segundos de instância
(trava).

## F2-9 — Publicar a interface

Providências: **P-6** (Pages ativado com origem GitHub Actions e o ambiente `github-pages` com revisor e etiquetas
`publicacao-pages-*`) e **P-7** (aprovar o job). A variável do repositório `VITE_API_BASE_URL` recebe o endereço do serviço (o
`$URL` do F2-8, sem `/` no fim; não é segredo).

```bash
git tag publicacao-pages-$(date +%Y%m%d)-1 <commit verificado> && git push origin publicacao-pages-$(date +%Y%m%d)-1
```

O workflow `pages.yml` confere a proteção, faz `npm ci`, os testes, o TypeScript e o build com `ADT_BASE_DA_PAGINA=/Teste-Agente/`
e a variável, confere o padrão de chave no build e publica em `https://gustavohoff1987.github.io/Teste-Agente/`. **Custo:**
nenhum (o Pages não cobra). **Desfazer:** Settings → Pages → desativar (a interface sai do ar; o serviço continua).

## F2-10 — Teste de produção com o Gemini real (até 5 chamadas)

Pela interface publicada: uma pergunta sobre um resultado, uma explicação mais simples e uma pergunta conceitual, conferindo
em `"$URL/api/llm/status"` (`requests_used_today`, sem a chave) que não passaram de 5 chamadas. **Custo:** nível gratuito do
`gemini-3.5-flash-lite`, sem faturamento no projeto da chave.

## F2-11 — Suspender temporariamente o acesso, conferir a mensagem institucional e restaurar

O mesmo par de comandos do F2-7 (remover e, depois de conferir a mensagem na interface, adicionar de novo o `allUsers`).
**Custo:** nenhum.

## F2-12 — Conferência final (só leitura)

No Console: Faturamento → Orçamentos e alertas (a trava de R$ 11 do Cloud Run e os dois conjuntos de alertas, sem alterar) e
Faturamento → Relatórios, filtrado pelo Cloud Run. Tempo faturável das consultas de sessão: Cloud Run → serviço → Métricas →
"Billable container instance time" e "Request count" por rota (`/api/session`). Comparar com a estimativa do relatório
(seção F e G).

## Custos fora da trava (estimativas; conferir no Console)

| Item | Franquia | Uso esperado | Acima da franquia |
|---|---|---|---|
| Artifact Registry (armazenamento) | 0,5 GB/mês | 2 versões de cerca de 0,2 GB | cerca de US$ 0,10 por GB/mês |
| Secret Manager | 6 versões ativas e 10 mil acessos/mês | 1 versão; 1 acesso por partida de instância | US$ 0,06 por versão/mês; US$ 0,03 por 10 mil acessos |
| Cloud Logging | 50 GiB/mês | registros de requisição do Cloud Run e o log do Uvicorn (sem o log de acesso) | cerca de US$ 0,50 por GiB |
| Tráfego de saída | conferir se entra na trava | o gráfico de todos os municípios tem cerca de 2 MB comprimido; uma sessão típica, de 5 a 20 MB | conforme a tabela de rede do Google |
| Cloud Build | não usado | — | — |
| Varredura de vulnerabilidades | não habilitada | — | cobrada por imagem |
