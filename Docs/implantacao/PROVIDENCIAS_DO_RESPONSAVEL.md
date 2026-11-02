# Providências que dependem do responsável pelo produto

Agente Diagnóstico Territorial da Força de Trabalho na Saúde — implantação no Google Cloud Run e no GitHub Pages
(comando de 01/11/2026, seção 12.2). **Nenhuma destas providências foi executada pelo agente.** O responsável é o único
revisor e aprovador. Em todos os ambientes do GitHub, a opção "Prevent self-review" fica **desativada**, para que o
responsável possa aprovar o que ele mesmo iniciou; isso não autoriza publicação automática: cada job protegido espera a
aprovação dele na interface do GitHub. O agente nunca aprova execuções pendentes, nem pela API.

## Decisões pedidas na Fase 1 (antes da Fase 2)

1. **Divergência da RQ-FLX-17 (sessão de 30 minutos).** Com as sessões em memória e mínimo 0 instâncias, uma sessão pode se
   perder antes do prazo (relatório, seção F). Alternativas, da menos complexa para a mais: (a) registrar a divergência sem
   alterar o código (a interface já informa a perda); (b) complementar o aviso, o que exigiria alterar a TPL-09; (c) mínimo de
   1 instância, cerca de US$ 20 por mês, acima da trava; (d) persistência das sessões, contrária à decisão de não usar banco.
   Recomendação do agente: (a). **Nada foi implementado; aguarda a decisão.**
2. **Política dos dados do Brasil e repositório público.** O README ("Política dos dados do Brasil", itens 1 e 8, e
   "Licença e autorização de redistribuição: pendentes") diz que o repositório "deve permanecer privado" e pede não
   redistribuir os arquivos fora dele; o repositório `gustavohoff1987/Teste-Agente` é público (conferido pela API em
   01/11/2026), e o comando pede que continue público. O agente não alterou a visibilidade nem a política. Decidir: atualizar a
   política (registrando a autorização de redistribuição) ou outra providência. A imagem do contêiner leva os mesmos arquivos e
   fica no Artifact Registry, privado.
3. **Varredura de segredos e proteção de push do GitHub: desativadas** (lidas pela API em 01/11/2026). Ativar em Settings →
   Code security → Secret Protection (varredura) e Push protection. Gratuitas em repositório público.
4. **Stash local do GitHub Desktop com `backend/.env`.** No seu computador, `stash@{0}` ("On main: !!GitHub_Desktop<main>",
   17/10/2026) guarda um `backend/.env` com `GEMINI_API_KEY` no formato `AQ.` (53 caracteres; o valor não foi exibido). Ele
   **nunca foi enviado** ao GitHub (a API não encontra os commits `17d88e5` e `73427d3`), e o histórico público não tem nenhuma
   ocorrência dos padrões de chave; pelo critério do comando, a chave não precisa ser substituída. Recomendação: conferir o
   resto do stash e descartá-lo (`git stash drop stash@{0}`), para que um `stash pop` seguido de commit não publique a chave.
5. **Ferramenta local:** o GitHub CLI (`gh`) não está instalado; o agente acompanhou o CI pela API REST, com o token do Git
   Credential Manager, só em leitura. Para regularizar (opcional): `winget install GitHub.cli` e `gh auth login`.
6. **Teste de gatilho (opcional, antes da Fase 2):** escrever **AUTORIZO O TESTE DE GATILHO** para o agente enviar uma
   etiqueta `teste-gatilho-AAAAMMDD` ao commit verificado, conferir a execução de `teste-gatilho.yml` (só registra o ref e o
   commit, sem ambiente, segredos ou build) e apagar a etiqueta depois.

## Validação real do Gemini (só se o responsável decidir fazê-la)

- **V-1.** Escrever **AUTORIZO A VALIDAÇÃO REAL DO GEMINI** (vale para uma execução; repetir exige nova autorização).
- **V-2.** Criar o ambiente `gemini-real`: Settings → Environments → New environment → `gemini-real`; "Required reviewers" =
  você; "Prevent self-review" desativado; "Deployment branches and tags" → "Selected branches and tags" → "Add deployment
  branch or tag rule" → tipo **Tag**, padrão `validacao-gemini-real-*`; nenhuma regra de ramo.
- **V-3.** O agente confere a configuração, só em leitura (o ambiente, o revisor e a regra de etiqueta), e mostra o resultado.
- **V-4.** Só então: no ambiente `gemini-real`, "Add environment secret" → `GEMINI_API_KEY`, colando a chave direto do AI
  Studio (nunca no chat, no terminal do Claude Code ou num arquivo). Nunca como segredo do repositório nem de outro ambiente.
- **V-5.** O agente envia uma etiqueta `validacao-gemini-real-AAAAMMDD` ao commit verificado e acompanha. O primeiro job
  (`conferir-protecao`, sem ambiente) encerra a execução sem nenhuma chamada se o ambiente não existir, não tiver revisor,
  aceitar outras etiquetas ou ramos, ou se o commit não pertencer ao ramo `implantacao/cloud-run-pages`.
- **V-6.** Aprovar o job `validacao` na interface do GitHub (Actions → a execução → "Review deployments"). O job faz no máximo
  20 chamadas reais somadas, para num 429 real e publica só um relatório sanitizado.
- **V-7.** Ao final, apagar o segredo `GEMINI_API_KEY` do ambiente `gemini-real`.

## Fase 2 (cada operação com AUTORIZO F2-n)

- **P-1 (antes de F2-0).** Autenticar o gcloud na conta e no projeto certos: `gcloud auth login` com a conta Google dona do
  projeto; `gcloud config set project agente-diagnostico-territorial`; conferir com `gcloud config list`.
- **P-2 (com F2-0).** No Console (Faturamento → Orçamentos e alertas), conferir, sem alterar: a trava (spend cap) de R$ 11 por
  mês só do Cloud Run, com alertas de 50, 80 e 100%, e o orçamento só de alertas de R$ 11, com 25, 50, 75 e 100%.
- **P-3 (antes de F2-5).** Criar o ambiente `producao`: revisor obrigatório = você; "Prevent self-review" desativado; regra
  de implantação só por etiquetas `imagem-*`; variáveis do ambiente (não secretas) `GCP_PROVEDOR_DE_IDENTIDADE` e
  `GCP_CONTA_DE_ENVIO_DE_IMAGEM`, com os valores que o F2-3 imprime.
- **P-4 (antes de F2-4).** Pelo Console (Segurança → Secret Manager → Criar segredo), criar `gemini-api-key`, colando a chave
  copiada do AI Studio; nunca por linha de comando, chat ou terminal do Claude Code. No projeto da chave (AI Studio / Google
  Cloud do projeto da chave): restringir a chave à Generative Language API (APIs e serviços → Credenciais → a chave →
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
  público) e F2-9 (publicar a interface).
