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
3. **Varredura de segredos e proteção de push do GitHub: não conferidas em 02/11/2026.** Sem o `gh` e sem token, a API
   pública não mostra essa configuração (o bloco `security_and_analysis` só aparece para quem administra o repositório). Em
   01/11/2026 estavam desativadas. Conferir ou ativar em Settings → Code security → Secret Protection (varredura) e Push
   protection, gratuitas em repositório público; o agente não as altera.
4. **Stash local do GitHub Desktop com `backend/.env`: ainda existe.** Em 02/11/2026, `git stash list` (só a lista, sem abrir
   o conteúdo) mostra `stash@{0}: On main: !!GitHub_Desktop<main>`. Em 01/11/2026 ele guardava um `backend/.env` com
   `GEMINI_API_KEY` (o valor não foi exibido) e **nunca foi enviado** ao GitHub. Recomendação: conferir o resto do stash e
   descartá-lo (`git stash drop stash@{0}`), para que um `stash pop` seguido de commit não publique a chave.
5. **GitHub CLI (`gh`): não instalado** (02/11/2026). Sem ele, o agente consulta só a API pública do GitHub sem autenticação
   (até 60 consultas por hora; ela entrega os estados das execuções, as anotações e os ambientes, mas não o log nem os
   artefatos) e nunca extrai tokens do Git Credential Manager nem de outro armazenamento. Para regularizar (opcional):
   `winget install GitHub.cli` e `gh auth login`.
6. **Teste de gatilho: autorizado em 02/11/2026** ("AUTORIZO O TESTE DE GATILHO"). O agente envia uma etiqueta
   `teste-gatilho-AAAAMMDD` ao último commit verificado, confere a execução de `teste-gatilho.yml` (só registra o ref e o
   commit, sem ambiente, segredos ou build) e apaga a etiqueta. O resultado está no relatório, seção H.

## Validação real do Gemini (autorizada em 02/11/2026)

A chave atual é mantida: na validação, como segredo do ambiente protegido `gemini-real`; na Fase 2, no Secret Manager (P-4).
Criar, trocar, desativar ou revogar a chave não faz parte deste trabalho.

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
  20 chamadas reais somadas, com pelo menos 10 s entre o início das mensagens (o nível gratuito tem cerca de 10 por minuto),
  para num 429 real e publica só um relatório sanitizado. O resumo dele sai também nas anotações da execução, que o agente lê
  pela API pública do GitHub sem login (o log e o artefato exigem autenticação).
- **V-7.** Ao final, apagar o segredo `GEMINI_API_KEY` do ambiente `gemini-real` (Settings → Environments → `gemini-real` →
  o segredo → remover). É só a cópia no GitHub: a chave continua válida.

## Fase 2 (cada operação com AUTORIZO F2-n)

- **P-1 (antes de F2-0).** O gcloud **não está instalado** neste computador (`gcloud --version`, 02/11/2026; não houve
  autenticação). Para instalar no Windows: baixar e executar o instalador do Google Cloud CLI
  (`https://dl.google.com/dl/cloudsdk/channels/rapid/GoogleCloudSDKInstaller.exe`, da página "Install the gcloud CLI" do
  Google), com o Python embutido, que é o padrão. **O download é grande** (o pacote do Linux tem 94,4 MB; o do Windows, com o
  Python embutido, não tem tamanho publicado e tende a ser maior): faça-o, de preferência, fora dos dados móveis. Depois:
  `gcloud --version`; `gcloud auth login` com a conta Google dona do projeto; `gcloud config set project
  agente-diagnostico-territorial`; conferir com `gcloud config list`.
- **P-2 (com F2-0).** No Console (Faturamento → Orçamentos e alertas), conferir, sem alterar: a trava (spend cap) de R$ 11 por
  mês só do Cloud Run, com alertas de 50, 80 e 100%, e o orçamento só de alertas de R$ 11, com 25, 50, 75 e 100%.
- **P-3 (antes de F2-5).** Criar o ambiente `producao`: revisor obrigatório = você; "Prevent self-review" desativado; regra
  de implantação só por etiquetas `imagem-*`; variáveis do ambiente (não secretas) `GCP_PROVEDOR_DE_IDENTIDADE` e
  `GCP_CONTA_DE_ENVIO_DE_IMAGEM`, com os valores que o F2-3 imprime.
- **P-4 (antes de F2-4).** Pelo Console (Segurança → Secret Manager → Criar segredo), criar `gemini-api-key`, colando a chave
  atual copiada do AI Studio; nunca por linha de comando, chat ou terminal do Claude Code. No projeto da chave (AI Studio /
  Google Cloud do projeto da chave): restringir a chave à Generative Language API (APIs e serviços → Credenciais → a chave →
  Restrições de API) e confirmar que o projeto continua sem faturamento (Faturamento → "Este projeto não tem uma conta de
  faturamento"). Conferir no AI Studio os limites do nível gratuito do `gemini-3.5-flash-lite` (cerca de 10 por minuto e 500
  por dia).
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
