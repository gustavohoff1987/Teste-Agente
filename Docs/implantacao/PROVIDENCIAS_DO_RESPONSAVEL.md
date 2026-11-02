# Providências que dependem do responsável pelo produto

Agente Diagnóstico Territorial da Força de Trabalho na Saúde — implantação no Google Cloud Run e no GitHub Pages
(comando de 01/11/2026, seção 12.2; atualizadas pelo comando de ajustes antes da Fase 2, de 02/11/2026). O agente não executa
nenhuma destas providências: ele as pede, espera a confirmação e confere só em leitura. O responsável é o único revisor e
aprovador. Em todos os ambientes do GitHub, a opção "Prevent self-review" fica **desativada**, para que o responsável possa
aprovar o que ele mesmo iniciou; isso não autoriza publicação automática: cada job protegido espera a aprovação dele na
interface do GitHub. O agente nunca aprova execuções pendentes, nem pela API.

## Decisões e conferências antes da Fase 2

1. **Divergência da RQ-FLX-17 (sessão de 30 minutos): resolvida em 02/11/2026.** Opção (a): a divergência fica registrada,
   sem alteração do código ([registro de comportamento](../REGISTRO_DE_COMPORTAMENTO.md), entrada de 02/11/2026; relatório,
   seção F). Com as sessões em memória e mínimo 0 instâncias, uma sessão pode se perder antes do prazo, e a interface avisa.
2. **Política dos dados do Brasil: resolvida em 02/11/2026.** A caracterização das bases (agregados de natureza pública, sem
   dados pessoais ou sensíveis), a procedência (dados oficiais do Ministério da Saúde, com extração autorizada), a natureza
   (agregados por território e competência, redistribuição permitida) e o repositório público estão no README ("Política dos
   dados do Brasil"). Os workflows protegidos param se o repositório não estiver público.
3. **Varredura de segredos e proteção de push do GitHub: ativadas pelo responsável em 02/11/2026.** Conferidas com o `gh`, só
   em leitura: `secret_scanning` e `secret_scanning_push_protection` ativados, nenhum alerta aberto. Seguem desativados, como
   opcionais, os padrões genéricos, a verificação de validade e as atualizações de segurança do Dependabot (Settings → Code
   security); o agente não os altera.
4. **Stash local do GitHub Desktop (`stash@{0}`, 17/10/2026): resolvido em 02/11/2026, com a sua autorização expressa.**
   O exame só dos metadados e dos nomes (relatório, seção M) mostrou que ele não guardava código, testes nem documentação do
   produto: eram 11.114 arquivos locais, como `frontend/node_modules`, `.local/`, caches e build, e 25 arquivos `.env`, entre
   eles o `backend/.env` com a chave, nunca enviados ao GitHub. Os três scripts soltos foram extraídos para `.local/`, sem
   nenhuma ocorrência do padrão de chave, e o stash foi descartado. `.env`, `.env.*` e `.local/` entraram no
   `.git/info/exclude`, que protege também o `main`, que não tem `.gitignore`.
5. **GitHub CLI (`gh`): instalado e autenticado pelo responsável em 02/11/2026** (conta `gustavohoff1987`). Nesta sessão do
   Claude Code, ele é usado pelo caminho completo (`C:\Program Files\GitHub CLI\gh.exe`), sem exibir o token. Antes dele, o
   agente usou só a API pública sem autenticação e nunca extraiu tokens do Git Credential Manager nem de outro armazenamento.
6. **Teste de gatilho: feito em 02/11/2026** ("AUTORIZO O TESTE DE GATILHO"). A etiqueta `teste-gatilho-20261102` no último
   commit verificado (`381523a`) acionou o `teste-gatilho.yml` (execução 41496728825, sucesso; só registra o ref e o commit,
   sem ambiente, segredos ou build), e a etiqueta foi apagada. Detalhes no relatório, seção H.

## Validação real do Gemini (feita em 02/11/2026)

A chave atual é mantida: na validação, como segredo do ambiente protegido `gemini-real`; na Fase 2, no Secret Manager (P-4).
Criar, trocar, desativar ou revogar a chave não faz parte deste trabalho.

**Situação:** V-1 a V-7 feitos em 02/11/2026. A execução 41506330654 terminou em sucesso, com 15 chamadas reais de 20 e
nenhum 429 (relatório, seção M). Depois, o segredo saiu do ambiente `gemini-real` (V-7, conferido com o `gh`).

- **V-1.** "AUTORIZO A VALIDAÇÃO REAL DO GEMINI": concedida em 02/11/2026, para uma execução com chamadas reais, logo depois
  do sucesso do teste de gatilho. Uma execução que termine antes da primeira chamada real (por exemplo, na conferência da
  proteção) não consome a autorização: o agente identifica a causa, corrige ou pede o ajuste do ambiente, e repete.
- **V-2.** Criar o ambiente `gemini-real`: Settings → Environments → New environment → `gemini-real`; "Required reviewers" =
  você; "Prevent self-review" desativado; "Deployment branches and tags" → "Selected branches and tags" → "Add deployment
  branch or tag rule" → tipo **Tag**, padrão `validacao-gemini-real-*`; nenhuma regra de ramo.
- **V-3.** O agente confere a configuração, só em leitura (o ambiente, o revisor e a regra de etiqueta), e mostra o resultado.
- **V-4.** Só então: no ambiente `gemini-real`, "Add environment secret" → `GEMINI_API_KEY`, colando a chave atual direto do
  AI Studio (nunca no chat, no terminal do Claude Code ou num arquivo). Nunca como segredo do repositório nem de outro ambiente.
- **V-5.** O agente envia uma etiqueta `validacao-gemini-real-AAAAMMDD` ao commit verificado e acompanha. O primeiro job
  (`conferir-protecao`, sem ambiente) encerra a execução sem nenhuma chamada se o repositório não estiver público, se o
  ambiente não existir, não tiver revisor, aceitar outras etiquetas ou ramos, ou se o commit não pertencer ao ramo
  `implantacao/cloud-run-pages`.
- **V-6.** Aprovar o job `validacao` na interface do GitHub (Actions → a execução → "Review deployments"). O job faz no máximo
  20 chamadas reais somadas, com pelo menos 10 s entre o início das mensagens (precaução da validação; o nível gratuito admite 15 por minuto),
  para num 429 real e publica só um relatório sanitizado. O resumo dele sai também nas anotações da execução, que o agente lê
  pela API pública do GitHub sem login (o log e o artefato exigem autenticação).
- **V-7 (feito).** Ao final, apagar o segredo `GEMINI_API_KEY` do ambiente `gemini-real` (Settings → Environments →
  `gemini-real` → o segredo → remover). É só a cópia no GitHub: a chave continua válida.

## Fase 2 (cada operação com AUTORIZO F2-n)

- **P-1 (antes de F2-0): concluída em 02/11/2026.** O responsável instalou o Google Cloud CLI no Windows e concluiu o
  `gcloud init`. O agente conferiu só em leitura (`gcloud --version`, `gcloud auth list`, `gcloud config list` e
  `gcloud config configurations list`): versão 591.0.0, conta `mister.hoff87@gmail.com` ativa, projeto
  `agente-diagnostico-territorial`, configuração `default` ativa. O executável não está no PATH das sessões do Claude Code
  abertas antes da instalação: o agente usa o caminho completo
  (`%LOCALAPPDATA%\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd`). A região `us-central1` vai explícita em cada comando
  do roteiro.
- **P-2 (com F2-0).** No Console (Faturamento → Orçamentos e alertas), conferir, sem alterar: a trava (spend cap) de R$ 11 por
  mês só do Cloud Run, com alertas de 50, 80 e 100%, e o orçamento só de alertas de R$ 11, com 25, 50, 75 e 100%.
  **Concluída em 02/11/2026:** o responsável conferiu no Console o limite de gastos mensal de R$ 11 do projeto, com status
  Configurado, só do Cloud Run e com alertas de 50, 80 e 100%, e o orçamento geral de alertas de R$ 11 por mês, com 25, 50,
  75 e 100%. Nada foi alterado.
- **P-3 (antes de F2-5).** Criar o ambiente `producao`: revisor obrigatório = você; "Prevent self-review" desativado; regra
  de implantação só por etiquetas `imagem-*`; variáveis do ambiente (não secretas) `GCP_PROVEDOR_DE_IDENTIDADE` e
  `GCP_CONTA_DE_ENVIO_DE_IMAGEM`, com os valores que o F2-3 imprime.
- **P-4 (antes de F2-4).** Pelo Console (Segurança → Secret Manager → Criar segredo), criar `gemini-api-key`, colando a chave
  atual copiada do AI Studio; nunca por linha de comando, chat ou terminal do Claude Code. No projeto da chave (AI Studio /
  Google Cloud do projeto da chave): restringir a chave à Generative Language API (APIs e serviços → Credenciais → a chave →
  Restrições de API) e confirmar que o projeto continua sem faturamento (Faturamento → "Este projeto não tem uma conta de
  faturamento"). Limites do nível gratuito do `gemini-3.5-flash-lite`, conferidos pelo responsável no AI Studio em 02/11/2026, no
  projeto da chave em uso: 15 requisições por minuto, 250 mil tokens por minuto e 500 requisições por dia (o provedor pode
  mudá-los).
- **P-5 (em F2-5).** Aprovar, no ambiente `producao`, o job de envio da imagem.
- **P-6 (antes de F2-9).** Settings → Pages → Build and deployment → Source: **GitHub Actions**, sem usar os modelos de
  workflow sugeridos pela página (gravariam no `main`). No ambiente `github-pages` (criado pelo Pages): revisor obrigatório =
  você, "Prevent self-review" desativado, e trocar a regra padrão de ramo pela regra de etiquetas `publicacao-pages-*`. Depois
  do F2-8, criar a variável do repositório `VITE_API_BASE_URL` com o endereço do serviço (`https://….run.app`, sem `/` no fim).
- **P-7 (em F2-9).** Aprovar, no ambiente `github-pages`, o job de publicação.
- **P-8 (em cada operação).** Autorizar com **AUTORIZO F2-n**, em especial F2-6 (implantar o backend), F2-7 (liberar o acesso
  público), F2-9 (publicar a interface) e F2-13 (habilitar as exclusões da limpeza do Artifact Registry, depois da simulação).
- **P-9 (em F2-9, F2-10 e F2-11).** As conferências na interface publicada, no navegador: a página, o diálogo de abertura, um
  gráfico, o mapa e a conversa (F2-9); as três mensagens com o Gemini real (F2-10); a mensagem institucional com o acesso
  suspenso (F2-11). O agente confere só pela API, sem instalar navegador de teste no seu computador.
