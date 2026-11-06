# Roteiro da Fase 2 — implantação do Agente Diagnóstico Territorial da Força de Trabalho na Saúde

Google Cloud Run (serviço de análise) e GitHub Pages (interface). **Nada aqui foi executado.** Cada operação F2-n (F2-0 a
F2-13) só acontece depois de o responsável pelo produto escrever **AUTORIZO F2-n**, que vale só para aquela operação, na ordem
abaixo (seção 13 do comando de implantação de 01/11/2026; ajustes do comando de 02/11/2026, seção 4). Antes de cada uma, o
agente apresenta de novo os comandos exatos, o efeito, o custo esperado e como desfazer. Sem teste de carga. Qualquer passo
fora desta lista, que amplie recursos ou que possa gerar custo não previsto, para e volta ao responsável. As conferências na
interface publicada (F2-9 a F2-11) são do responsável, no navegador; o agente confere só pela API (`curl`), sem instalar
navegador de teste no computador do responsável.

As providências do responsável (P-1 a P-9, V-1 a V-7) estão em [PROVIDENCIAS_DO_RESPONSAVEL.md](PROVIDENCIAS_DO_RESPONSAVEL.md);
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
IMG=$REGIAO-docker.pkg.dev/$PROJETO/$REPOSITORIO/$IMAGEM   # a imagem no Artifact Registry (etiquetas em-uso e anterior)
```

Recursos do serviço (decisões que não mudam): 1 vCPU, 2 GiB, mínimo 0 e máximo 1 instância, cobrança por requisição
(`--cpu-throttling`), um processo Uvicorn, acesso público sem login, aumento de CPU na partida **desligado**
(`--no-cpu-boost`; ligado, eleva a CPU e o consumo da trava; só com autorização). A concorrência e o timeout vêm da medição
no CI ([relatório](RELATORIO_IMPLANTACAO.md), seção C): **concorrência 40** (o máximo medido foi de 22 pedidos em andamento
com 20 usuários simulados; acima da concorrência, a plataforma segura os pedidos ou responde 429 sem CORS, que o navegador vê
como indisponibilidade) e **timeout 150 s** (a conversa vai a cerca de 95 s, mais a espera por vaga, e a tela desiste aos 100
s; a operação pesada mais longa medida, dois XLSX de 15 MB juntos, levou 71 s, mais até 20 s de fila).

## Execução no Windows (registrada na F2-2, 02/11/2026)

Os blocos abaixo estão em sintaxe bash. Neste computador, o gcloud é o `gcloud.cmd`, que fica fora do PATH das sessões
abertas antes da instalação: `%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`.
- Pelo Git Bash, o `cmd.exe` interpreta mal o caminho com espaços quando outro argumento também vem entre aspas.
- O agente executa os comandos pelo PowerShell (`& $G ...`), com `CLOUDSDK_CORE_DISABLE_PROMPTS=1`.
- Os trechos em Python vão em arquivos, porque o PowerShell perde as aspas de scripts passados em linha.
- A saída JSON do PowerShell traz BOM: ler com `utf-8-sig`, ou filtrar pelo próprio `--format` do gcloud.
- A F2-0 escreve sempre em UTF-8 (desde 06/11/2026) e não cai por causa de nenhum caractere. Redirecionada, a saída começa com a
  marca BOM: sem ela, o PowerShell 5.1 relê o texto na página do console (cp850) e troca a seta e os acentos.
- Os arquivos temporários ficam fora do repositório.

## F2-0 — Verificação prévia (só leitura)

Providências antes: **P-1** (gcloud autenticado na conta e no projeto certos) e **P-2** (trava e alertas conferidos no
Console).

```bash
python scripts/implantacao/verificacao_previa.py --projeto agente-diagnostico-territorial --regiao us-central1
```

O script só lê (gcloud `list`/`describe`) e mostra OK, ATENÇÃO, FALHA ou MANUAL para: conta autenticada, projeto e região, conta
de faturamento, orçamento só de alertas de R$ 11 com 25/50/75/100%, trava de R$ 11 do Cloud Run (MANUAL: a CLI não a expõe; P-2),
APIs habilitadas e recursos não previstos (serviços, repositórios, contas de serviço, segredos, pools de identidade) e, se o
serviço já existir, mínimo 0, máximo 1, 1 vCPU, 2 GiB, cobrança por requisição, sem aumento de CPU na partida, concorrência e
timeout. Qualquer resultado fora do previsto interrompe a implantação até o responsável decidir. **Efeito:** nenhum. **Custo:**
nenhum. **Desfazer:** nada a desfazer. É obrigatória antes de qualquer implantação (F2-6) e de cada atualização.

**Sem resposta não é aprovação (desde 05/11/2026).**
- **Sem perguntas:** o script chama o gcloud sem entrada e com a oferta de habilitar APIs desligada. Assim, o gcloud nunca para
  esperando uma resposta nem habilita nada.
- **Limite de tempo real:** 30 s na consulta de orçamentos e 120 s nas demais. Ao estourar, o script encerra também o Python
  aberto pelo `gcloud.cmd` no Windows, e a verificação continua nos itens seguintes.
- **Orçamentos:** a consulta que falha ou não responde fica MANUAL, com a conferência obrigatória no Console (P-2). Hoje é sempre
  esse o resultado, porque a API de orçamentos (`billingbudgets.googleapis.com`) está desligada no projeto; ela não deve ser
  habilitada só para isso.
- **Demais verificações obrigatórias:** a que não se conclui é FALHA, inclusive as contas de serviço e os pools de identidade.
- **Saída:** 1 se houver falha e 2 se, sem falhas, restar item MANUAL. A trava é sempre MANUAL, então a saída 0 não ocorre: toda
  F2-0 termina na conferência do responsável, e nada segue antes dela.

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

## F2-2 — Repositório do Artifact Registry

Escopo simplificado por decisão do responsável (02/11/2026): só o repositório. Os registros de auditoria `DATA_WRITE` e a
política de limpeza ficam adiados para uma etapa posterior, se efetivamente necessária (F2-13). Os registros de auditoria
padrão do Google Cloud ficam como estão.

```bash
gcloud artifacts repositories create $REPOSITORIO --project=$PROJETO --location=$REGIAO --repository-format=docker \
  --description="Imagens do serviço de análise do Agente Diagnóstico Territorial da Força de Trabalho na Saúde"
gcloud artifacts repositories describe $REPOSITORIO --project=$PROJETO --location=$REGIAO   # conferência, só leitura
```

- **Sem política de limpeza, nada é apagado automaticamente.** A imagem em produção e a anterior, a da reversão, ficam
  preservadas e marcadas com as etiquetas `em-uso` e `anterior` a cada implantação e reversão (F2-6).
- **Imagens antigas:** saem só à mão, por decisão do responsável, com `gcloud artifacts docker images delete "$IMG@<digest>"`.
  Nunca a marcada com `em-uso` ou `anterior`.

**Efeito:** um repositório de imagens no Artifact Registry, sem acesso público. **Custo:** a franquia do Artifact Registry é
de 0,5 GB por mês, e cada imagem tem cerca de 126 MiB comprimida (350,9 MiB descompactada; medida no CI, relatório, seção C).
Sem limpeza automática, as versões se acumulam a cada envio. A franquia comporta umas 3 a 4 imagens; acima dela, o custo é de
cerca de US$ 0,10 por GB por mês, **fora da trava do Cloud Run**. **Desfazer:**
`gcloud artifacts repositories delete $REPOSITORIO --project=$PROJETO --location=$REGIAO` (apaga as imagens).

**Execução de 02/11/2026:** a primeira autorização da F2-2 foi executada com o escopo anterior, antes da decisão de
simplificar. Ela incluiu os registros `DATA_WRITE` do Artifact Registry e a política de limpeza em simulação. A retirada dos
dois, mantido o repositório, foi apresentada ao responsável como a F2-2 de escopo simplificado (relatório, seção N):

```bash
# Registros DATA_WRITE: a política do projeto é lida, perde só a entrada do Artifact Registry em auditConfigs (bindings e
# etag intactos) e é gravada de volta; o arquivo temporário fica fora do repositório e é apagado em seguida.
gcloud projects get-iam-policy $PROJETO --format=json > politica-do-projeto.json
#   (retirar de auditConfigs a entrada com service artifactregistry.googleapis.com)
gcloud projects set-iam-policy $PROJETO politica-do-projeto.json --format="value(etag)" && rm -f politica-do-projeto.json
# Política de limpeza: as três regras saem, e o repositório fica sem política.
gcloud artifacts repositories delete-cleanup-policies $REPOSITORIO --project=$PROJETO --location=$REGIAO \
  --policynames=manter-em-uso-e-anterior,manter-a-mais-recente,apagar-as-demais-depois-de-1-dia
```

## F2-3 — Contas de serviço e federação de identidade restrita ao ambiente `producao`

```bash
gcloud iam service-accounts create adt-execucao --project=$PROJETO \
  --display-name="Agente Diagnóstico Territorial da Força de Trabalho na Saúde - execução no Cloud Run"
gcloud iam service-accounts create adt-envio-imagem --project=$PROJETO \
  --display-name="Agente Diagnóstico Territorial da Força de Trabalho na Saúde - envio da imagem (GitHub Actions)"   # até 100 caracteres
# Envio da imagem: só escrever neste repositório.
gcloud artifacts repositories add-iam-policy-binding $REPOSITORIO --project=$PROJETO --location=$REGIAO \
  --member="serviceAccount:$SA_IMAGEM" --role="roles/artifactregistry.writer"
# Federação: só tokens do repositório gustavohoff1987/Teste-Agente emitidos para o ambiente producao.
# O repositório usa o sub com identificadores imutáveis (gh api repos/gustavohoff1987/Teste-Agente/actions/oidc/
# customization/sub: use_immutable_subject true): repositório 1411794822, dono 322563090 (corrigido na F2-5, 03/11/2026).
gcloud iam workload-identity-pools create github --project=$PROJETO --location=global --display-name="GitHub Actions"
gcloud iam workload-identity-pools providers create-oidc teste-agente --project=$PROJETO --location=global \
  --workload-identity-pool=github --display-name="Teste-Agente, ambiente producao" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.environment=assertion.environment" \
  --attribute-condition="assertion.repository_id == '1411794822' && assertion.repository_owner_id == '322563090' && assertion.environment == 'producao' && assertion.sub == 'repo:gustavohoff1987@322563090/Teste-Agente@1411794822:environment:producao'"
gcloud iam service-accounts add-iam-policy-binding $SA_IMAGEM --project=$PROJETO --role="roles/iam.workloadIdentityUser" \
  --member="principal://iam.googleapis.com/projects/$NUMERO/locations/global/workloadIdentityPools/github/subject/repo:gustavohoff1987@322563090/Teste-Agente@1411794822:environment:producao"
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

O workflow `imagem.yml` confere o repositório público, a proteção do ambiente e o commit no ramo, constrói a imagem do commit,
repete o teste rápido do contêiner (saúde, exame da base, documentação desligada, padrão de chave) e a envia ao Artifact
Registry pela federação. O **digest** sai no resumo da execução, para o F2-6. Sem política de limpeza, nada é apagado
automaticamente (F2-2). **Custo:** armazenamento (F2-2). **Desfazer:** apagar a versão no Artifact
Registry (`gcloud artifacts docker images delete "$IMG@<digest>"`), nunca a marcada com `em-uso` ou `anterior`.

## F2-6 — Implantar no Cloud Run, ainda sem acesso público

Antes: F2-0 de novo. Todos os parâmetros explícitos:

```bash
gcloud run deploy $SERVICO --project=$PROJETO --region=$REGIAO \
  --image="$REGIAO-docker.pkg.dev/$PROJETO/$REPOSITORIO/$IMAGEM@sha256:<digest do F2-5>" \
  --execution-environment=gen2 --cpu=1 --memory=2Gi --min-instances=0 --max-instances=1 \
  --concurrency=40 --timeout=150 --cpu-throttling --no-cpu-boost --port=8080 \
  --startup-probe=tcpSocket.port=8080,initialDelaySeconds=0,timeoutSeconds=10,periodSeconds=10,failureThreshold=24 \
  --service-account=$SA_EXECUCAO --set-secrets=GEMINI_API_KEY=gemini-api-key:1 \
  --set-env-vars=ADT_ALLOWED_ORIGINS=$ORIGEM,ADT_DOCUMENTACAO_DA_API=0 \
  --ingress=all --no-allow-unauthenticated --labels=aplicacao=agente-diagnostico-territorial
# Teste pelo proxy autenticado (o token fica com o gcloud; nada é exibido). Exige o componente extra do gcloud para o
# proxy; sem ele (F2-6 de 03/11/2026), a partida é conferida pelo Cloud Logging, e a saúde por HTTP, na F2-8:
gcloud run services proxy $SERVICO --project=$PROJETO --region=$REGIAO --port=18080 &
curl -fsS http://127.0.0.1:18080/api/health
```

- `--set-secrets=…:1`: a versão fixada do segredo (não `latest`).
- A sonda de partida espera a porta até 240 s (24 × 10 s), o limite do Cloud Run; o aquecimento termina antes de a porta
  abrir (relatório, seção C). Sem sonda de vida: o serviço não reinicia por demora de uma operação pesada.
- `gen2`: o mesmo controle de memória (cgroup v2) medido no CI.

**Marcação das imagens, a cada implantação** (depois de a revisão nova responder; as etiquetas identificam a imagem em
produção e a da reversão, que nunca saem na remoção manual de imagens antigas e que uma política de limpeza futura, se
adotada, terá de preservar):

```bash
EM_USO=$(gcloud artifacts docker images describe "$IMG:em-uso" --format='value(image_summary.digest)' 2>/dev/null)
[ -n "$EM_USO" ] && gcloud artifacts docker tags add "$IMG@$EM_USO" "$IMG:anterior"   # na primeira implantação, não há
gcloud artifacts docker tags add "$IMG@sha256:<digest do F2-5>" "$IMG:em-uso"            # o gcloud cria ou atualiza a etiqueta
gcloud artifacts docker tags list "$IMG"                                                  # em-uso e anterior nos digests certos
```

**Reversão** (voltar à imagem `anterior`) e a marcação correspondente:

```bash
EM_USO=$(gcloud artifacts docker images describe "$IMG:em-uso" --format='value(image_summary.digest)')
ANTERIOR=$(gcloud artifacts docker images describe "$IMG:anterior" --format='value(image_summary.digest)')
gcloud run revisions list --service=$SERVICO --project=$PROJETO --region=$REGIAO   # a revisão com a imagem $ANTERIOR
gcloud run services update-traffic $SERVICO --project=$PROJETO --region=$REGIAO --to-revisions=<revisão anterior>=100
gcloud artifacts docker tags add "$IMG@$ANTERIOR" "$IMG:em-uso"
gcloud artifacts docker tags add "$IMG@$EM_USO" "$IMG:anterior"
gcloud artifacts docker tags list "$IMG"
```

As duas etiquetas ficam sempre nas duas imagens usadas por último: a reversão troca uma pela outra, e a imagem retirada fica
preservada como `anterior` até a implantação seguinte. Enquanto não houver limpeza automática, as imagens mais antigas também
ficam, até a remoção manual.

**Efeito:** o serviço existe, só para quem tem permissão. **Custo:** entra na trava (tempo de instância ativa). **Desfazer:**
`gcloud run services delete $SERVICO --project=$PROJETO --region=$REGIAO`.

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
curl -sS -o /dev/null -w '%{http_code}\n' "$URL/docs"                    # 404 (sem -f, que esconderia o código)
curl -fsS -X POST -d "dataset=brazil&scope=municipal" "$URL/api/inspect" -o /dev/null -w '%{http_code}\n'   # 200
# CORS, pelos cabeçalhos da resposta:
curl -sS -o /dev/null -D - -H "Origin: https://exemplo.invalid" "$URL/api/health" | grep -i '^access-control-allow-origin' \
  || echo "sem Access-Control-Allow-Origin para a origem estranha (o esperado)"
curl -sS -o /dev/null -D - -H "Origin: $ORIGEM" "$URL/api/health" | grep -i '^access-control-allow-origin'
#   esperado: access-control-allow-origin: https://gustavohoff1987.github.io
curl -sS -o /dev/null -D - -X OPTIONS -H "Origin: $ORIGEM" -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type,x-adt-session" "$URL/api/inspect" | grep -i '^access-control-allow'
#   a pré-verificação do navegador: a origem do Pages, os métodos e os dois cabeçalhos da interface
```

Uma análise (o gráfico dos estados) e um envio pequeno (CSV de 100 KB) pelo mesmo caminho, pela API. **Custo:** segundos de
instância (trava).

## F2-9 — Publicar a interface

Providências: **P-6** (Pages ativado com origem GitHub Actions e o ambiente `github-pages` com revisor e etiquetas
`publicacao-pages-*`) e **P-7** (aprovar o job). A variável do repositório `VITE_API_BASE_URL` recebe o endereço do serviço (o
`$URL` do F2-8, sem `/` no fim; não é segredo).

```bash
git tag publicacao-pages-$(date +%Y%m%d)-1 <commit verificado> && git push origin publicacao-pages-$(date +%Y%m%d)-1
```

O workflow `pages.yml` confere o repositório público e a proteção, faz `npm ci`, os testes, o TypeScript e o build com
`ADT_BASE_DA_PAGINA=/Teste-Agente/` e a variável, confere o padrão de chave no build e publica em
`https://gustavohoff1987.github.io/Teste-Agente/`.

- **Conferência na interface (responsável, P-9):** no navegador, a página abre com o nome oficial, o diálogo de abertura, um
  gráfico e o mapa respondem, e a conversa responde.
- **Conferência do agente, só pela API:** `curl -sS -o /dev/null -w '%{http_code}\n' https://gustavohoff1987.github.io/Teste-Agente/`
  (200) e `curl -fsS "$URL/api/health"`.

**Custo:** nenhum (o Pages não cobra). **Desfazer:** Settings → Pages → desativar (a interface sai do ar; o serviço continua).

## F2-10 — Teste de produção com o Gemini real (até 5 chamadas)

- **Na interface (responsável, P-9):** pela página publicada, no navegador, uma pergunta sobre um resultado, uma explicação
  mais simples e uma pergunta conceitual.
- **Conferência do agente, só pela API:** `curl -fsS "$URL/api/llm/status"` antes e depois (`requests_used_today`, sem a chave):
  no máximo 5 chamadas a mais.

**Custo:** nível gratuito do `gemini-3.5-flash-lite`, sem faturamento no projeto da chave.

## F2-11 — Suspender temporariamente o acesso, conferir a mensagem institucional e restaurar

- **Agente:** remove o `allUsers` (o desfazer do F2-7) e confere pela API que o serviço recusa o acesso:
  `curl -sS -o /dev/null -w '%{http_code}\n' "$URL/api/health"` (403).
- **Responsável (P-9):** no navegador, a interface mostra "Serviço temporariamente indisponível", com o texto institucional.
- **Agente:** adiciona de novo o `allUsers` (o comando do F2-7) e confere o 200 em `/api/health`.

**Custo:** nenhum.

## F2-12 — Conferência final (só leitura)

No Console: Faturamento → Orçamentos e alertas (a trava de R$ 11 do Cloud Run e os dois conjuntos de alertas, sem alterar) e
Faturamento → Relatórios, filtrado pelo Cloud Run. Tempo faturável das consultas de sessão: Cloud Run → serviço → Métricas →
"Billable container instance time" e "Request count" por rota (`/api/session`). Comparar com a estimativa do relatório
(seção F e G).

## F2-13 — Política de limpeza do Artifact Registry (adiada; só se necessária, com AUTORIZO F2-13)

Adiada por decisão do responsável (02/11/2026). Se o armazenamento crescer a ponto de justificá-la, a operação será
apresentada de novo, com a política, os custos e a reversão. Ela terá de preservar a imagem em produção e a anterior
(etiquetas `em-uso` e `anterior`, F2-6), e a validação dela será definida nessa apresentação. Até lá, nenhuma política de
limpeza, nenhuma simulação e nenhum registro de auditoria `DATA_WRITE`; as imagens antigas saem só à mão (F2-2).

## Custos fora da trava (estimativas; conferir no Console)

| Item | Franquia | Uso esperado | Acima da franquia |
|---|---|---|---|
| Artifact Registry (armazenamento) | 0,5 GB/mês | cerca de 126 MiB por imagem; sem limpeza automática, as versões se acumulam até a remoção manual (a franquia comporta umas 3 a 4) | cerca de US$ 0,10 por GB/mês |
| Secret Manager | 6 versões ativas e 10 mil acessos/mês | 1 versão; 1 acesso por partida de instância | US$ 0,06 por versão/mês; US$ 0,03 por 10 mil acessos |
| Cloud Logging | 50 GiB/mês | registros de requisição do Cloud Run, o log do Uvicorn (sem o log de acesso) | cerca de US$ 0,50 por GiB |
| Tráfego de saída | conferir se entra na trava | o gráfico de todos os municípios transfere cerca de 0,2 MiB com gzip (2,3 MiB sem compressão) e a análise mais pesada (evolução e tendência), 3,8 MiB; uma sessão típica, de 1 a 5 MiB | conforme a tabela de rede do Google |
| Cloud Build | não usado | — | — |
| Varredura de vulnerabilidades | não habilitada | — | cobrada por imagem |


## Segunda publicação da interface: https://diagnostico-territorial.github.io/ (M-0 a M-5)

Plano de 04/11/2026: a mesma interface, publicada na raiz pelo repositório
`diagnostico-territorial/diagnostico-territorial.github.io`, ao lado da publicação atual (`/Teste-Agente/`), que não muda.
Cada operação M-n só acontece depois de "AUTORIZO M-n".

**Desenho:** sem credencial entre repositórios.
- O destino tem o próprio workflow (modelo em [destino/publicar.yml](destino/publicar.yml)) e as próprias cópias revisadas de
  `conferir_protecao.py`, `conferir_origem.py` e `verificar_chave_google.py`.
- Ele lê o Teste-Agente, que é público, no commit fixado em `origem.txt`, e o constrói com `ADT_BASE_DA_PAGINA=/`.
- Ele publica no próprio Pages, no ambiente `github-pages`, com a aprovação do responsável.
- Antes do build, confere a origem: o commit pertence a `implantacao/cloud-run-pages`, e o CI dele terminou em sucesso.
- O serviço no Cloud Run, o Gemini, a trava e os orçamentos são os mesmos; o CORS passa a ter as duas origens (M-3).

| Operação | O que faz | Reversão |
|---|---|---|
| M-0 | Só leitura: as Actions e o ambiente do destino, o último CI, a F2-0 e o CORS de hoje | — |
| M-1 | No Teste-Agente: o CI constrói e testa a interface também na raiz (suíte `conteiner-raiz`); `conferir_origem.py` com testes; o teste do CORS com duas origens; o modelo do workflow do destino; documentação | um commit de reversão |
| P-M1 | Responsável, no destino: a varredura de segredos e a proteção de push; o ambiente `github-pages` com revisor, sem bypass e só a etiqueta `publicacao-pages-*`; a variável `VITE_API_BASE_URL`; o Pages pela origem GitHub Actions | — |
| M-2 | No `main` do destino: `.github/workflows/publicar.yml`, as cópias dos três scripts, `origem.txt` (o SHA verificado do Teste-Agente) e o README | um commit de reversão no destino |
| M-3 | A F2-0 e depois `gcloud run services update ... --update-env-vars="^##^ADT_ALLOWED_ORIGINS=https://gustavohoff1987.github.io,https://diagnostico-territorial.github.io"`, com uma revisão nova e o **mesmo digest**; a conferência dos cabeçalhos para as duas origens e para uma estranha; o registro de comportamento | o mesmo comando, só com a origem atual |
| M-4 | A etiqueta `publicacao-pages-AAAAMMDD-1` no destino; a aprovação do responsável (P-M2); a conferência pela API (200 em `/`, os recursos sob `/`, o endereço do serviço no build) | Settings → Pages do destino → desativar |
| M-5 | A conferência final: os dois sites no navegador (responsável), os registros e o uso do serviço, o relatório | — |

**Ordem:** a M-3 vem antes da M-4, para que a primeira visita ao site novo já passe no CORS.

**Custo:**
- o Pages e as Actions não custam nada em repositório público;
- as visitas ao site novo contam na trava de R$ 11 do Cloud Run e no limite de 15 chamadas por minuto do Gemini, somando
  todos os usuários;
- a M-3 cria uma revisão nova, que descarta as sessões em memória e pode causar uma partida a frio.
