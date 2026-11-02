# Relatório da implantação — Fase 1 (preparação e validação)

Agente Diagnóstico Territorial da Força de Trabalho na Saúde — Google Cloud Run (serviço de análise) e GitHub Pages (interface).
Comando de implantação de 01/11/2026 (`COMANDO_IMPLANTACAO_REVISADO (1).txt`), Fase 1. Ramo `implantacao/cloud-run-pages`.

**Situação:** em andamento — preparação implementada; medições e verificações do CI pendentes da primeira execução no ramo.
**Conclusão estimada da Fase 1:** 75% (o que falta está na seção I). **Nada foi publicado**; nenhuma chamada real ao Gemini,
nenhum recurso no Google Cloud, nenhuma configuração ou etiqueta no GitHub, nenhum merge e nenhum pull request.

## A. Base escolhida, commit e evidências

**Base: `feat/desafio-adversarial-conversacional`, commit `b50272d` (29/10/2026).** Ramo `implantacao/cloud-run-pages` criado
a partir dele.

| Ramo | Último commit | CI do último commit | Situação em relação à base |
|---|---|---|---|
| `feat/desafio-adversarial-conversacional` | `b50272d` (29/10, 20:19 UTC) | execução 40948024661: os 7 jobs em sucesso (backend 1.168 aprovados e 63 pulados, os de dados reais; dados reais 1.231 aprovados e nenhum pulado; frontend, navegador, governança e resumo) | a base |
| `feat/novos-blocos-incrementais` | `849b40d` (29/10, 18:43 UTC) | execução 40933587141: os 7 jobs em sucesso | 23 commits atrás da base; os 2 exclusivos são `9cf13f8` (Gemini sem teto local, enviado por engano a este ramo) e a reversão dele, `849b40d`. O efeito líquido é só a entrada do registro sobre a reversão; a mudança em si está na base desde `dd5743f` (26/10) |
| `claude/ux-adjustments-coordinates-vm8esj` | `ff8a5fa` (25/10) | — | contido na base (ancestral) |
| `ajustes-ux-diagnostico-territorial-20261024` | `2635582` (25/10) | — | contido na base (ancestral) |
| `main` | `6284151` (09/10) | — | só a SPEC; ancestral da base; não modificado |

Fundamento: a base é a mais completa (contém todos os outros ramos, exceto o par de commits sem efeito líquido), é o ramo
principal de desenvolvimento declarado no `ci.yml` desde 26/10/2026 e tem o CI verde em todos os jobs no último commit.
Nenhuma alteração relevante fica de fora. A escolha não se apoiou na data dos commits.

Repositório: `gustavohoff1987/Teste-Agente`, público, ramo padrão `main`, sem Pages, sem ambientes, sem segredos e sem
variáveis do Actions (lidos pela API em 01/11/2026); único workflow ativo, o `ci.yml`.

## B. Arquivos, classificação das mudanças e mecanismos preservados

**Mudanças de comportamento** (classificadas antes de codar, todas previstas — escopo e compatibilidade —, registradas em
[REGISTRO_DE_COMPORTAMENTO.md](../REGISTRO_DE_COMPORTAMENTO.md), entrada de 01/11/2026):

| Item do comando (seção 4) | Implementação |
|---|---|
| 1. Upload de 15 MB = 15.000.000 bytes | `backend/carga.py` (`MAX_UPLOAD_BYTES`, limite do pedido) e `backend/main.py`; `frontend/src/paginaUnica.ts` (`LIMITE_DO_ARQUIVO`, `recusaDoArquivo`), `App.tsx`, `JanelaDeEnvio.tsx`; textos, recusas e testes |
| 2. Estados de conexão e mensagem institucional | `frontend/src/conexao.ts` e `AvisoDaConexao.tsx`; `App.tsx`, `SessionPrivacy.tsx`, `painelApi.ts`, `AreaDeAnalise.tsx`, `AnalysisAssistant.tsx`, `historicoConversa.ts`, `styles.css` |
| 3. Nova tentativa moderada | `conexao.ts`: tentativa curta de 2 s; depois 5, 10, 20, 40, 60 e 120 s; pausa com a aba oculta; botão |
| 4. Nome oficial completo | `index.html`, `App.tsx` (título e rodapé), mensagem institucional |
| 5. CORS restrito | `main.py`: `ADT_ALLOWED_ORIGINS` (produção: só `https://gustavohoff1987.github.io`; desenvolvimento: o Vite local), só `Content-Type` e `X-ADT-Session`, pré-verificação de 2 h |
| 6. `/docs`, `/redoc` e `/openapi.json` fora em produção | `ADT_DOCUMENTACAO_DA_API=0`, já no `Dockerfile` |
| 7. Limites de memória, por sessão e fila de operações pesadas | `carga.py`: vagas (2), fila (8), espera (20 s), 6 pedidos por sessão, 503 com `ocupado`; as rotas pesadas fora do laço de eventos. `conversation_session.py`: o teto total dos resultados guardados passou de 256 para 128 MiB pela medição (seção C); os 32 MiB por sessão ficam |
| 8. Recusa de planilhas malformadas ou desproporcionais | `carga.conferir_xlsx` (100 vezes com piso de 10 MB, ou 150 MB) e `conferir_csv` (6 milhões de células), com a TPL-13 |
| 9. Aquecimento antes da porta | `main._lifespan` (a porta do Uvicorn só abre depois), com a duração no log |
| Seção 6.3 (mensagem de configuração) | `llm_bridge`: a chave inválida (400 `API_KEY_INVALID`) é problema de configuração, como 401/403 |
| Seção 6.2 (provedor simulado) | `llm_bridge._endereco`: `ADT_GEMINI_ENDERECO_DE_TESTE`, só na própria máquina |

**Sem mudança de comportamento do produto** (novos arquivos de implantação e testes): `Dockerfile`, `.dockerignore`,
`backend/requirements-conteiner.txt`; `.github/workflows/` (`ci.yml` com as três alterações permitidas;
`validacao-gemini-real.yml`, `imagem.yml`, `pages.yml`, `teste-gatilho.yml`); `.github/scripts/` (`medir_conteiner.py`,
`planilhas_de_teste.py`, `verificar_chave_google.py`, `conferir_protecao.py`, `validar_gemini_conteiner.py`);
`backend/tests/` (`test_hospedagem.py`, `test_implantacao.py`, `serve_gemini_http.py`, `serve_ui_conteiner.py`,
`ui_conexao.py`, `ui_hospedagem.py`, `ui_sessao.py`; `run_ui_checks.py`, `ui_support.py`, `ui_pagina_unica.py`,
`serve_ui_offline.py`, `test_brazil_cache.py` ajustados); `scripts/implantacao/verificacao_previa.py`;
`scripts/validar_gemini_real.py` (teto rígido); `Docs/implantacao/`.

**Divergências apresentadas:** a da RQ-FLX-17 (seção F), não implementada, aguarda decisão. Nenhuma divergência aprovada
foi contrariada; a SPEC (inclusive a TPL-09) não foi alterada.

**Mecanismos preservados:** os contratos analíticos e metodológicos, as fórmulas, os parâmetros, os critérios estatísticos e
as regras espaciais; a governança da autoridade analítica do modelo conversacional (a conferência de fidelidade, a triagem,
nenhum dado ao provedor); a integridade da base pelo manifesto; a sessão em memória com o prazo de 1.800 s e o catálogo de
interações; a consulta da sessão a cada 30 s; a decisão de 26/10/2026 de não ter teto local de chamadas ao Gemini.

## C. Contêiner (medições no runner do GitHub, não no Cloud Run)

*Pendente da primeira execução do job `conteiner` no ramo.* O job constrói a imagem (sem envio a registro) e roda cada
contêiner com `--cpus=1 --memory=2g --memory-swap=2g` e `/tmp` em tmpfs; mede a partida (porta e saúde), o aquecimento, a
memória em repouso, sob carga e o pico, as análises de cada família contra a referência em processo, as planilhas (até
15.000.000 bytes aceitas, 15.000.001 recusadas, malformadas e desproporcionais), dois envios simultâneos de 14,9 MB, a
memória das sessões até os tetos, a concorrência (1, 5, 10 e 20 usuários, com 2 e com 1 vaga), as gravações fora de `/tmp`
e o encerramento por SIGTERM. Os números entram aqui e no artefato `medicoes-do-conteiner`. A CPU do runner não é a vCPU do
Google; nada medido aqui é confirmação na nuvem.

## D. Interface

- **Build:** `npm run build` (TypeScript, testes e Vite); para o Pages, `ADT_BASE_DA_PAGINA=/Teste-Agente/` e
  `VITE_API_BASE_URL` (variável do repositório, não secreta, criada só no F2-9). O `base` padrão continua `/`.
- **Pages:** `pages.yml` (build sem ambiente; publicação no ambiente `github-pages`, Node 22.23.4 fixado, `npm ci`,
  verificações, padrão de chave no build). A origem do CORS é `https://gustavohoff1987.github.io` (sem caminho).
- **Comunicação com o backend e recursos visuais:** conferidos no job `conteiner` pelo roteiro `ui_hospedagem.py` (recursos sob
  `/Teste-Agente/`, fonte embutida, serviço noutro endereço com CORS e pré-verificação, CSV, modelo XLSX baixado do serviço,
  documentação desligada) e pelos roteiros da página única com a base versionada na mesma topologia (seleção, gráficos, mapa,
  envio de planilha, Histórico, Nova sessão). A página não tem rotas internas (só a âncora `#topo`). *Resultado pendente do CI.*
- **Estados de conexão (A a G):** `conexao.ts` (testado com relógio simulado em `conexao.test.mjs`) e `ui_conexao.py`, com o
  serviço de verdade parado e restabelecido no contêiner. *Resultado pendente do CI.*

## E. Gemini

- **Testes simulados:** pytest (`test_hospedagem.py`, provedor simulado por HTTP no formato real: sucesso, 429 por minuto e
  por dia com QuotaFailure e RetryInfo, chave inválida 400 e recusada 403, 503, saída fora do contrato com as 2 regenerações) e
  as medições do contêiner (os mesmos e mais a demora de 5 s, o tempo esgotado de 75 s, o 500, o retorno depois da espera do
  429 e o motor funcionando com o Gemini em espera). *Resultado do contêiner pendente do CI.*
- **Validação real (preparada, não executada):** `validacao-gemini-real.yml` com o job `conferir-protecao` (sem ambiente e
  sem segredos) e o job `validacao` (ambiente `gemini-real`), teto de 20 chamadas somadas, 429 real encerra, chave inválida
  noutro contêiner e relatório sanitizado conferido contra o padrão de chave. O mecanismo é demonstrado por testes com
  respostas simuladas da API (`test_implantacao.py`): para sem chamadas quando o ambiente não existe, não tem revisor, aceita
  outras etiquetas ou ramos, o gatilho não é a etiqueta ou o commit não pertence ao ramo; sem o segredo, nenhum pedido sai.
  **A validação real depende de "AUTORIZO A VALIDAÇÃO REAL DO GEMINI"** (providências V-1 a V-7).
- **Capacidade frente ao nível gratuito:** cerca de 10 requisições por minuto e 500 por dia por projeto (a conferir no AI
  Studio). Com, em geral, 1 chamada por mensagem (até 3 com regenerações), são cerca de 10 mensagens por minuto e 500 por dia,
  somando todos os usuários. Sem teto local (decisão de 26/10/2026): a proteção é a espera após o 429 e a resposta
  determinística de reserva. *As chamadas por mensagem medidas entram aqui.*
- **Segurança da chave:** o histórico público (5 ramos e 8 pull requests) não tem nenhuma ocorrência dos padrões de chave do
  Google; o padrão do comando (`AIza` + 35) não cobre o formato da chave em uso (`AQ.`), e a verificação confere os dois. Uma
  ocorrência existe só num stash local, nunca enviado (providência 4). A imagem, os builds da interface e os artefatos são
  conferidos no CI; o `.dockerignore` exclui `.env`.
- **Secret Manager:** preparado no roteiro (F2-4): segredo `gemini-api-key` cadastrado pelo responsável no Console (P-4), lido
  só pela conta de execução, na versão fixada.

## F. Sessão de 30 minutos (TPL-09, RQ-FLX-17)

1. **Comportamento efetivo:** a consulta periódica, a reconexão e as atividades automáticas não renovam o prazo; só as
   interações do catálogo renovam; a expiração ocorre aos 1.800 s sem interação; o encerramento é imediato. Conferido pelo
   código (`conversation_session.py`, `conversationSession.ts`), pelos testes existentes e por `ui_sessao.py` (prazo reduzido
   só no servidor de teste) e pela API do contêiner. *Resultado pendente do CI.*
2. **Permanência da instância:** enquanto uma aba com sessão ativa consulta a sessão a cada 30 s, a instância recebe uma
   requisição a cada 30 s e não fica ociosa. Sem requisições, o Cloud Run pode manter a instância ociosa por até 15 minutos e
   depois encerrá-la. Abas em segundo plano (o Chrome espaça os temporizadores; com o tempo, a uma vez por minuto), aparelhos em
   repouso e navegadores móveis (que suspendem a página) espaçam ou suspendem as consultas: sem consultas por mais de 15
   minutos, a instância pode ser encerrada, e a sessão se perde antes dos 30 minutos. Reproduzido em `ui_sessao.py` com a aba
   congelada (nenhuma consulta sai; a sessão expira no servidor; ao voltar, a tela avisa).
3. **Limites das consultas:** elas não protegem contra a troca de instância pelo Cloud Run (que ocorre em operação normal),
   nova revisão, falta de memória, reinício ou suspensão pela trava. Em todos esses casos, as sessões em memória se perdem; a
   interface mostra "A sessão anterior expirou ou ficou indisponível no servidor." e começa outra (reproduzido em
   `ui_conexao.py` com o reinício do contêiner).
4. **Impacto financeiro:** cada consulta isolada conta pelo menos 100 ms faturáveis; com a pré-verificação do CORS válida por
   2 h, são 120 consultas e no máximo 1 pré-verificação por hora de aba aberta, cerca de 12 s faturáveis por hora, 6 s até a
   expiração de 30 minutos, cerca de 0,02% da trava por hora de aba. *O tempo medido de cada consulta entra aqui.*
5. **Testes:** `ui_sessao.py` (consulta sem renovação, interação com renovação, expiração, encerramento explícito e aba
   congelada) e `ui_conexao.py` (reinício do contêiner com a sessão aberta). *Resultado pendente do CI.*

**Divergência confirmada (aguarda decisão):** a RQ-FLX-17 garante que "a reconexão tecnicamente possível antes da expiração
mantém a mesma sessão"; com sessões em memória e mínimo 0 instâncias, a perda antes do prazo é possível nos casos dos itens
2 e 3. Riscos: perder análises não exportadas e a conversa; a interface avisa e começa outra sessão, sem confundir com a
indisponibilidade do serviço. Alternativas: (a) registrar a divergência sem alterar o código — **recomendada**, a menos
complexa, coerente com as decisões de não ter banco nem instância mínima; (b) complementar o aviso, o que exige alterar a
TPL-09 (fora do autorizado); (c) instância mínima, cerca de US$ 20 por mês, acima da trava de R$ 11; (d) persistência das
sessões, contrária à decisão de não usar banco.

## G. Custos

- **Na trava (Cloud Run, custo bruto, sem a franquia):** 1 vCPU + 2 GiB a cerca de US$ 0,000029 por segundo de instância
  ativa; R$ 11 (cerca de US$ 2) cobrem cerca de 19 h de instância ativa por mês (a franquia gratuita cobriria cerca de 50 h,
  mas a trava não a desconta). Com cobrança por requisição, a instância só conta durante as requisições, a partida e o
  encerramento. Atingida a trava, o serviço responde com erro até o dia 1º do mês seguinte ou até o responsável suspendê-la; a
  interface mostra "Serviço temporariamente indisponível". *Horas e interações por mês com os segundos faturáveis medidos
  entram aqui.*
- **Fora da trava:** Artifact Registry acima de 0,5 GB; Secret Manager acima da franquia; Cloud Logging acima de 50 GiB;
  tráfego de saída que não entre na trava (detalhe no [roteiro](ROTEIRO_FASE2.md#custos-fora-da-trava-estimativas-conferir-no-console)).
  Sem Cloud Build e sem varredura de vulnerabilidades.
- **Riscos de cobrança excedente:** a trava tem atraso e não cobre outros serviços; a partida a frio é cobrada; uma operação
  pesada longa (um XLSX de 15 MB) consome segundos de CPU a cada análise (o arquivo é reenviado e lido de novo).
- **Medidas preventivas:** máximo de 1 instância, cobrança por requisição, sem aumento de CPU na partida, vagas e fila para
  operações pesadas, limite de 15 MB, o pedido abandonado na fila sai sem calcular, o log de acesso do Uvicorn desligado (o
  Cloud Run já registra as requisições), a política de limpeza do Artifact Registry e a verificação prévia (F2-0).

## H. Gatilhos

- **`ci.yml` no ramo de preparação:** comprovado no primeiro envio do ramo. *Pendente do envio.*
- **Gatilhos por etiqueta** (`validacao-gemini-real-*`, `imagem-*`, `publicacao-pages-*`): não podem ser comprovados na Fase 1
  (enviar etiquetas não está autorizado). A sintaxe dos workflows é conferida pelo actionlint no job `conteiner`, e os testes
  de `test_implantacao.py` conferem que só há os gatilhos previstos, sem `workflow_dispatch`, `repository_dispatch` ou
  `workflow_run`. O `teste-gatilho.yml` está pronto e só roda depois de "AUTORIZO O TESTE DE GATILHO".
- **Se um gatilho não funcionar:** parar e apresentar as alternativas — ramo dedicado de acionamento com regra de ramo no
  ambiente; os arquivos de workflow no `main` (exige autorização para modificar o `main`); ou a validação real executada pelo
  responsável num terminal separado, com `scripts/validar_gemini_real.py`.

## I. Testes

*Pendente da primeira execução do CI no ramo* (os 8 jobs). Antes do envio, só as checagens de segundos do AGENTS.md:
`py_compile` dos arquivos Python, `tsc --noEmit` da interface, pyflakes nos arquivos novos e a governança depois do commit.

**Problemas encontrados e corrigidos na Fase 1:** a chave inválida do Gemini (resposta real 400 `API_KEY_INVALID`) caía como
falha interna, sem a espera de configuração; as rotas pesadas bloqueavam o laço de eventos (a saúde e a consulta da sessão
esperavam o cálculo); o arquivo enviado era lido inteiro antes da conferência do tamanho; as mensagens de erro mostravam o
código HTTP, e a falha de rede no gráfico mostrava o texto técnico do navegador; a verificação de saúde da interface era única,
sem nova tentativa; o padrão de chave do comando não cobria o formato da chave em uso.

**Só se confirma no Cloud Run:** a partida a frio real (com a CPU do Google), a restrição de CPU entre requisições, a latência
da rede, o balanceador (que devolve 429 acima da concorrência com uma instância), o encerramento por ociosidade e a troca de
instâncias, o consumo efetivo da trava e o tráfego de saída.

## J. Providências que dependem do responsável

Em ordem, com o porquê, em [PROVIDENCIAS_DO_RESPONSAVEL.md](PROVIDENCIAS_DO_RESPONSAVEL.md): as decisões da Fase 1 (a
divergência da RQ-FLX-17, a política dos dados com o repositório público, a varredura de segredos e a proteção de push, o
stash local, o `gh` e o teste de gatilho), a validação real (V-1 a V-7) e a Fase 2 (P-1 a P-8).

## K. Roteiro da Fase 2

[ROTEIRO_FASE2.md](ROTEIRO_FASE2.md): F2-0 a F2-12, com os comandos revisados e não executados, o efeito, o custo esperado e
como desfazer cada operação, e os custos fora da trava.

## L. Parecer

*Pendente das verificações do CI.* Sem a validação real do Gemini, o parecer não pode ser "Pronto para implantação".
