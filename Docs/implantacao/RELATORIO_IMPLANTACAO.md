# Relatório da implantação — Fase 1 (preparação e validação) e ajustes antes da Fase 2

Agente Diagnóstico Territorial da Força de Trabalho na Saúde — Google Cloud Run (serviço de análise) e GitHub Pages (interface).
Comando de implantação de 01/11/2026 (`COMANDO_IMPLANTACAO_REVISADO (1).txt`), Fase 1, e comando de ajustes antes da Fase 2,
teste de gatilho e validação real do Gemini, de 02/11/2026 (`COMANDO_AJUSTES_PRE_FASE2.txt`). Ramo `implantacao/cloud-run-pages`.

**Situação (02/11/2026):** a Fase 1 está concluída (execução 41375485808, commit `b8ae7fb`, os 8 jobs em sucesso). O comando de
ajustes antes da Fase 2 está em execução: os ajustes das seções 2 a 5 estão feitos (seção M); faltam o CI do último commit, o
teste de gatilho e a validação real do Gemini. **Conclusão estimada do comando: 35%** (seção M). Nada foi publicado: nenhum
recurso no Google Cloud, nenhuma configuração do GitHub feita pelo agente, nenhum merge e nenhum pull request. **Parecer:
Pronto com ressalvas** (seção L).

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
variáveis do Actions (lidos pela API em 01/11/2026); único workflow ativo, o `ci.yml`. Em 02/11/2026, pela API pública sem
autenticação: público (`private: false`, `visibility: public`), sem Pages e sem ambientes.

Commits da Fase 1 no ramo: `938717d` (hospedagem: serviço, interface, contêiner e verificações), `04e22dd` (documentação da
implantação), `2863e47` (roteiros com o serviço noutro endereço), `b75fa65` (aviso de ocupado), `41b97bb` (medições),
`b8ae7fb` (teto total das sessões) e `5aad80b` (este relatório). Commits dos ajustes de 02/11/2026: seção M.

## B. Arquivos, classificação das mudanças e mecanismos preservados

**Mudanças de comportamento** (classificadas antes de codar, todas previstas — escopo e compatibilidade —, registradas em
[REGISTRO_DE_COMPORTAMENTO.md](../REGISTRO_DE_COMPORTAMENTO.md), três entradas de 01/11/2026):

| Item do comando (seção 4) | Implementação |
|---|---|
| 1. Upload de 15 MB = 15.000.000 bytes | `backend/carga.py` (`MAX_UPLOAD_BYTES`, limite do pedido) e `backend/main.py`; `frontend/src/paginaUnica.ts` (`LIMITE_DO_ARQUIVO`, `recusaDoArquivo`), `App.tsx`, `JanelaDeEnvio.tsx`; textos, recusas e testes |
| 2. Estados de conexão e mensagem institucional | `frontend/src/conexao.ts` e `AvisoDaConexao.tsx`; `App.tsx`, `SessionPrivacy.tsx`, `painelApi.ts`, `AreaDeAnalise.tsx`, `AnalysisAssistant.tsx`, `historicoConversa.ts`, `styles.css`. O aviso de ocupado só sai com a resposta de uma rota com limite (a lista de `carga.py`) ou depois de 20 s (correção da primeira execução do CI, seção I) |
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

**Divergências:** a da RQ-FLX-17 (seção F), apresentada na Fase 1, foi aprovada pelo responsável em 02/11/2026, opção (a):
registrada, sem alteração do código (registro de comportamento, entrada de 02/11/2026). Nenhuma divergência aprovada foi
contrariada; a SPEC (inclusive a TPL-09) não foi alterada. A classificação dos ajustes de 02/11/2026 está na seção M.

**Mecanismos preservados:** os contratos analíticos e metodológicos, as fórmulas, os parâmetros, os critérios estatísticos e
as regras espaciais (as análises pelo contêiner são idênticas às da referência, seção C); a governança da autoridade analítica
do modelo conversacional (a conferência de fidelidade, a triagem, nenhum dado ao provedor); a integridade da base pelo
manifesto; a sessão em memória com o prazo de 1.800 s e o catálogo de interações; a consulta da sessão a cada 30 s; a decisão
de 26/10/2026 de não ter teto local de chamadas ao Gemini.

## C. Contêiner (medições no runner do GitHub, não no Cloud Run)

A imagem foi construída e executada no job `conteiner` do `ci.yml` (sem envio a registro), com `--cpus=1 --memory=2g
--memory-swap=2g` e `/tmp` em tmpfs dentro do limite. Medições do artefato `medicoes-do-conteiner` da execução 41372746893
(commit `41b97bb`); a memória das sessões no teto atual, da execução 41375485808 (commit `b8ae7fb`, que só muda esse teto).
Runner: x86_64 com 4 CPUs, limitado a 1 pelo cgroup. **Limitações:** a CPU do runner não é a vCPU do Google; não se reproduz a
restrição de CPU entre requisições, a partida a frio real, a rede, o balanceador nem o escalonamento do Cloud Run. Nada
daqui é confirmação na nuvem; os recursos de produção serão os do Cloud Run. Valores de memória em MiB (cgroup).

**Partida e imagem**

| Medida | Valor no runner |
|---|---|
| Limites lidos no cgroup | `cpu.max` 100000 100000 (1 CPU), `memory.max` 2147483648 (2 GiB), swap 0, `/tmp` em tmpfs, usuário 10001 |
| Imagem | 350,9 MiB descompactada; cerca de 126 MiB comprimida (`docker save` com `gzip -1`, estimativa do que o Artifact Registry guarda) |
| Porta aberta e saúde respondendo | 10,1 s e 10,2 s; o aquecimento (8,5 s: base 7,7 s, biblioteca conversacional 0,8 s) termina antes da porta |
| Memória em repouso, depois da partida | 343,8 MiB (pico 347,6 MiB) |
| Reinício (do `docker start` à saúde) | 9,6 s |
| Encerramento com SIGTERM | 0,6 s, código 0, encerramento no log |
| Gravações fora de `/tmp` | nenhuma (`docker diff`) |

**Análises** — as 21 consultas medidas deram respostas **idênticas** às da referência em processo (o mesmo código e as
mesmas versões fixadas dos testes com dados reais, sem os campos voláteis): o exame da base; 12 análises em `/api/analyze`
(densidade, quantitativos também com todas as competências, relatório, distribuição, comparações, evolução e tendência,
agregação, ranking, espacial, referência mais próxima e critérios combinados) e a rotatividade com planilha; 5 gráficos da
página única, o mapa e as contagens da escolha dos territórios. Tempos de 0,09 a 7,4 s (evolução e tendência); os gráficos
da página única, de 0,14 a 0,27 s. Maior resposta: evolução e tendência, 20,3 MiB (3,8 MiB transferidos com gzip), abaixo
do limite de 32 MiB do HTTP/1. Memória máxima nas análises: 563,9 MiB (pico 630 MiB).

**Planilhas** (geradas no CI, sem dados reais; o gráfico é o de densidade de todos os territórios, com o código territorial
escolhido como no painel Colunas)

| Caso | Desfecho | Exame: s; MiB máx. | Gráfico: s; MiB máx.; itens |
|---|---|---|---|
| CSV pequeno (100 KB) | aceito | 0,15; 438,6 | 0,31; 437,6; 1.072 |
| XLSX pequeno (100 KB) | aceito | 0,38; 437,5 | 0,43; 437,5; 1.198 |
| CSV médio (3 MB) | aceito | 1,26; 440,7 | 1,86; 449,6; 5.570 |
| XLSX médio (3 MB) | aceito | 5,82; 446,0 | 6,22; 448,0; 5.570 |
| CSV de 14,9 MB | aceito | 5,09; 687,8 | 5,03; 683,8; 5.570 |
| XLSX de 14,9 MB | aceito | 33,6; 730,8 | 33,2; 694,4; 5.570 |
| CSV de 15.000.000 bytes (160.936 linhas) | aceito | 4,85; 707,5 | 5,32; 711,1; 5.570 |
| XLSX de 15.000.000 bytes (281.998 linhas) | aceito | 33,9; 721,7 | 33,5; 737,9; 5.570 |
| CSV e XLSX de 15.000.001 bytes, 20 MB e CSV de 40 MB | recusados pelo tamanho (413, "Arquivo acima do limite de 15 MB; nenhum dado foi analisado."), em até 0,1 s | — |
| XLSX malformado e truncado | inválidos (422, "Não foi possível interpretar este arquivo Excel…") | — |
| XLSX com expansão desproporcional (400 MB descompactados) | recusado antes da leitura (422, com a TPL-13), em 0,003 s | — |
| Dois envios simultâneos de 14,9 MB (CSV e XLSX) | aceitos, em 7,8 s e 38,7 s; 855,9 MiB máx. | — |

O XLSX custa de 6 a 7 vezes o CSV do mesmo tamanho, a cada análise: o arquivo é reenviado e lido de novo em cada pedido.

**Memória das sessões** (gráficos de todos os municípios, 8 por sessão, até o teto recusar o primeiro de uma sessão nova; com
as sessões cheias, os envios de planilha)

| Teto total (JSON) | Guardado | Memória real das sessões | Base + sessões | + CSV de 14,9 MB | + XLSX de 15 MB | + dois XLSX de 15 MB juntos (pico) |
|---|---|---|---|---|---|---|
| 256 MiB (antes; execução 41372746893) | 104 gráficos em 13 sessões | 812,9 MiB (3,18 × o JSON) | 1.156,0 MiB | 1.402,6 MiB | 1.463,8 MiB | 1.834,8 MiB (**89,6%** dos 2 GiB) |
| **128 MiB** (agora; execução 41375485808) | 56 gráficos em 7 sessões | 459,5 MiB (3,59 × o JSON) | 802,9 MiB | 1.063,2 MiB | 1.099,3 MiB | 1.488,5 MiB (**72,7%** dos 2 GiB) |

Com o teto antigo, o pior caso ficava a 0,4 ponto do alerta de 90% da medição; com uma instância só, a falta de memória
reinicia o serviço e perde todas as sessões. Pelo item 7 da seção 4, o teto total foi reduzido para 128 MiB (registro de
01/11/2026), e o pior caso medido caiu para 72,7%. No teto, o gráfico é calculado e mostrado, sem a referência para a
conversa, e nenhuma sessão é encerrada.

**Concorrência** (cada usuário simulado repete abertura em paralelo, exame da base, gráficos leves e pesados, mapa, escolha
dos territórios, planilha de 3 MB e conversa com o Gemini simulado de 2 a 20 s, com pausas de 0,2 a 1 s — bem mais intenso que
uma pessoa —, e a consulta da sessão a cada 30 s; 45 s por rodada)

| Vagas | Usuários | Pedidos | Simultâneos (máx.) | Ocupados (503) | Erros | `/api/health` p50/p95/máx. (ms) | Memória máx. (MiB) | Gráfico de todos os municípios p95 (s) | Conversa p95 (s) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 1 | 27 | 4 | 0 | 0 | 2/12/263 | 444,8 | 0,31 | 12,0 |
| 2 | 5 | 141 | 11 | 0 | 0 | 2/117/511 | 768,6 | 0,83 | 15,1 |
| 2 | 10 | 210 | 13 | 0 | 0 | 25/305/876 | 953,4 | 2,77 | 16,6 |
| 2 | 20 | 368 | 22 | 76 | 0 | 17/386/725 | 1.079,6 | 6,64 | 19,3 |
| 1 | 10 | 205 | 15 | 1 | 0 | 8/171/345 | 703,9 | 3,46 | 16,1 |
| 1 | 20 | 397 | 21 | 92 | 0 | 10/246/542 | 898,9 | 4,29 | 19,1 |

Nenhum 429 (não há plataforma no runner); todo 503 foi a resposta legível de ocupado; nenhum erro sem resposta legível; nenhuma
falta de memória. A saúde respondeu abaixo de 1 s durante as operações pesadas: elas não bloqueiam o laço de eventos.

**Definidos pela medição** (aplicados no [roteiro da Fase 2](ROTEIRO_FASE2.md), F2-6):

- **Concorrência do Cloud Run: 40.** O máximo medido foi de 22 pedidos em andamento com 20 usuários simulados. Com 40, a
  abertura de páginas (3 a 4 pedidos paralelos) e a conversa longa não esbarram no limite da plataforma, que seguraria os
  pedidos ou responderia 429 sem CORS (no navegador, falha de rede e o aviso de indisponibilidade) antes do limite legível do
  próprio serviço (ocupado). As operações pesadas já são limitadas pelo serviço; as leves pesam pouco na memória.
- **Timeout: 150 s.** Na conversa, nenhuma chamada nova ao Gemini começa depois de 20 s e cada uma vai até 75 s (cerca de 95 s),
  mais até 20 s de espera por vaga para ler a base; a tela desiste aos 100 s. Nas pesadas, até 20 s de fila e 33,9 s do XLSX
  de 15 MB (71 s com dois juntos).
- **Semáforo das operações pesadas: 2 vagas, fila de 8, espera de 20 s (mantidos).** Com 1 vCPU, 1 ou 2 vagas dão vazão
  parecida (20 usuários: 368 e 397 pedidos; 76 e 92 ocupados), mas com 1 vaga um XLSX de 15 MB (cerca de 34 s) seguraria todas
  as outras operações pesadas, que receberiam "ocupado" depois de 20 s de fila. O custo de memória da segunda vaga está na
  medição do pior caso (sessões no teto e dois XLSX juntos).

## D. Interface

- **Build:** `npm run build` (TypeScript, testes do Node e Vite) no job `frontend`; no job `conteiner`, também o build do
  Pages (`ADT_BASE_DA_PAGINA=/Teste-Agente/`, serviço noutro endereço), os dois sem nenhuma ocorrência do padrão de chave. O
  `base` padrão continua `/`. `VITE_API_BASE_URL` é variável do repositório (não secreta), criada só no F2-9.
- **Pages:** `pages.yml` (build sem ambiente; publicação no ambiente `github-pages`, Node 22.23.4 fixado, `npm ci`,
  verificações, padrão de chave no build). A origem do CORS é `https://gustavohoff1987.github.io` (sem caminho).
- **Comunicação com o backend e recursos visuais:** `ui_hospedagem.py` passou (recursos sob `/Teste-Agente/`, fonte embutida,
  nome oficial no título, serviço noutro endereço com CORS para a base, o gráfico com a sessão, o CSV e o modelo XLSX,
  documentação da API desligada, CORS só da origem da página), e os roteiros da página única, da área de análise e do mapa
  passaram com a base versionada na mesma topologia (seleção, gráficos, mapa, envio de planilha, Histórico, Nova sessão). A
  página não tem rotas internas (só a âncora `#topo`).
- **Estados de conexão (A a G):** `conexao.test.mjs` (relógio simulado) e `ui_conexao.py`, com o serviço de verdade parado e
  restabelecido no contêiner, passaram: A e B (o serviço parado na abertura: o aviso de partida e, depois da tentativa curta, a
  indisponibilidade com o texto institucional, sem detalhes técnicos), G (o botão, a pausa com a aba oculta e o
  restabelecimento automático com "Conexão restabelecida."), F (arquivo malformado e acima de 15 MB), D (a conversa sem o
  Gemini), C (o ocupado com o aviso e a nova tentativa sozinha do gráfico) e E (o reinício do contêiner com a sessão aberta:
  o aviso de sessão expirada ou indisponível, distinto da indisponibilidade).

## E. Gemini

- **Testes simulados:** pytest (`test_hospedagem.py`, provedor simulado por HTTP no formato real) e, no contêiner, os 13
  cenários da medição, todos corretos e sem detalhe técnico na tela: sucesso; demora de 5 s; saída fora do contrato com as 2
  regenerações (3 chamadas) e a reserva; tempo esgotado aos 75 s, 503 e 500 (espera por indisponibilidade); 429 por minuto
  (RetryInfo de 3 s) e o retorno depois da espera; chave inválida (400 `API_KEY_INVALID`) e recusada (403), como configuração;
  429 por dia (QuotaFailure), com espera até a virada do dia no horário do Pacífico; e o motor funcionando sem o Gemini.
- **Validação real (preparada, não executada):** `validacao-gemini-real.yml` com o job `conferir-protecao` (sem ambiente e
  sem segredos) e o job `validacao` (ambiente `gemini-real`), teto de 20 chamadas somadas, 429 real encerra, chave inválida
  noutro contêiner e relatório sanitizado conferido contra o padrão de chave. O mecanismo é demonstrado por testes com
  respostas simuladas da API (`test_implantacao.py`): para sem chamadas quando o repositório não está público (desde
  02/11/2026), o ambiente não existe, não tem revisor, aceita outras etiquetas ou ramos, o gatilho não é a etiqueta ou o
  commit não pertence ao ramo; sem o segredo, nenhum pedido sai. Desde 02/11/2026, as mensagens começam com pelo menos 10 s
  entre si (o nível gratuito tem cerca de 10 chamadas por minuto, e um 429 real encerra a validação), o roteiro registra o
  tempo de cada mensagem e o resumo sanitizado sai também nas anotações da execução (`anotar_validacao.py`), legíveis pela API
  pública do GitHub sem login.
  **A validação real depende de "AUTORIZO A VALIDAÇÃO REAL DO GEMINI"** (providências V-1 a V-7).
- **Chamadas por mensagem (medidas):** 1 por mensagem numa conversa típica, 0 nas respondidas localmente ("Obrigado!") e até 3
  com as regenerações.
- **Capacidade frente ao nível gratuito:** cerca de 10 requisições por minuto e 500 por dia por projeto (a conferir no AI
  Studio, P-4): cerca de 10 mensagens por minuto e 500 por dia, somando todos os usuários. Sem teto local (decisão de
  26/10/2026): a proteção é a espera após o 429 e a resposta determinística de reserva.
- **Segurança da chave:** o histórico público (5 ramos e 8 pull requests) não tem nenhuma ocorrência dos padrões de chave do
  Google; o padrão do comando (`AIza` + 35) não cobre o formato da chave em uso (`AQ.`), e a verificação confere os dois. Uma
  ocorrência existe só num stash local, nunca enviado (providência 4). A imagem, os builds da interface e os artefatos foram
  conferidos em cada execução do job `conteiner`, sem nenhuma ocorrência; o `.dockerignore` exclui `.env`.
- **Secret Manager:** preparado no roteiro (F2-4): segredo `gemini-api-key` cadastrado pelo responsável no Console (P-4), lido
  só pela conta de execução, na versão fixada.

## F. Sessão de 30 minutos (TPL-09, RQ-FLX-17)

1. **Comportamento efetivo:** a consulta periódica, a reconexão e as atividades automáticas não renovam o prazo; só as
   interações do catálogo renovam; a expiração ocorre aos 1.800 s sem interação; o encerramento é imediato. Conferido pelo
   código (`conversation_session.py`, `conversationSession.ts`), pelos testes existentes, por `ui_sessao.py` (prazo reduzido
   só no servidor de teste: consulta sem renovação, interação com renovação, expiração com o aviso, encerramento imediato e aba
   congelada) e pela API do contêiner (1.800,0 s ao criar; 1.797,0 s depois de 3 s com a consulta; 1.800,0 s depois da
   interação; 410 depois do encerramento e depois do reinício).
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
4. **Impacto financeiro (medido):** cada consulta leva cerca de 1 ms no contêiner (p95 de 1,2 ms) e cada pré-verificação do
   CORS, menos de 1 ms (válida por 2 h); com o arredondamento de 100 ms, cada consulta isolada conta 0,1 s. São 12 s faturáveis
   por hora de aba aberta com sessão ativa e 6 s até a expiração de 30 minutos: cerca de 0,02% da trava por hora de aba.
5. **Testes:** `ui_sessao.py` e `ui_conexao.py` passaram (seção I).

**Divergência aprovada em 02/11/2026:** a RQ-FLX-17 garante que "a reconexão tecnicamente possível antes da expiração
mantém a mesma sessão"; com sessões em memória e mínimo 0 instâncias, a perda antes do prazo é possível nos casos dos itens
2 e 3. Riscos: perder análises não exportadas e a conversa; a interface avisa e começa outra sessão, sem confundir com a
indisponibilidade do serviço. Alternativas apresentadas: (a) registrar a divergência sem alterar o código, a recomendada, a
menos complexa, coerente com as decisões de não ter banco nem instância mínima; (b) complementar o aviso, o que exige alterar
a TPL-09; (c) instância mínima, cerca de US$ 20 por mês, acima da trava de R$ 11; (d) persistência das sessões, contrária à
decisão de não usar banco. **O responsável adotou a opção (a)**: a divergência está no registro de comportamento (entrada de
02/11/2026) e no README ("Sessões"), sem mudança no código, na TPL-09 ou na SPEC.

## G. Custos

**Na trava (Cloud Run, custo bruto, sem a franquia):** 1 vCPU + 2 GiB a cerca de US$ 0,000029 por segundo de instância ativa
(US$ 0,000024 da vCPU e US$ 0,0000025 por GiB, cobrança por requisição; a conferir na tabela do Google). R$ 11 (cerca de US$ 2)
cobrem cerca de 69 mil segundos, **cerca de 19 h de instância ativa por mês** (a franquia gratuita cobriria cerca de 50 h, mas a
trava não a desconta). Com cobrança por requisição, a instância só conta enquanto há requisição em andamento (pedidos
simultâneos contam uma vez), na partida e no encerramento, arredondado a 100 ms.

Segundos faturáveis por interação, **estimados com os tempos do runner** (a vCPU do Google pode ser mais lenta ou mais rápida):

| Interação | Segundos faturáveis |
|---|---|
| Partida a frio (depois de 15 min sem uso) e encerramento | cerca de 11 s |
| Abrir a página (saúde, sessão e estado do Gemini, em paralelo) | 0,1 s |
| Usar os dados do Brasil (exame da base) | 0,3 s |
| Cada mudança no gráfico (gráfico, mapa e contagens) | 0,2 a 0,5 s |
| Análise completa pelo motor (`/api/analyze`, pela API; a página única usa o gráfico) | 0,7 a 7,4 s |
| Mensagem na conversa (a requisição dura o tempo do Gemini, que só a validação real mede) | cerca de 2 a 5 s (estimativa) |
| Planilha CSV de 3 MB: exame e cada gráfico | 1,3 s e 1,9 s |
| Planilha CSV de 15 MB: exame e cada gráfico | 4,9 s e 5,3 s |
| Planilha XLSX de 15 MB: exame e cada gráfico (reenviada e lida de novo) | 33,9 s e 33,5 s |
| Aba aberta com sessão ativa (consultas) | 12 s por hora |

**Horas e interações por mês até a trava (estimativas):** uma sessão típica com a base do Brasil (abrir, 20 mudanças no
gráfico, 5 mensagens e a aba aberta por 30 minutos) consome cerca de 30 s: **cerca de 2.300 sessões por mês** (cerca de 75 por
dia), ou cerca de 1.700 se cada uma começar com partida a frio. Com uma planilha CSV de 3 MB e 10 gráficos, cerca de 40 s
(1.700 por mês); com um XLSX de 15 MB e 10 gráficos, cerca de 390 s (**cerca de 175 por mês**). Só a aba aberta, sem
interações: cerca de 5.700 horas de aba por mês.

- **Fora da trava:** Artifact Registry acima de 0,5 GB (2 versões de cerca de 126 MiB cabem); Secret Manager acima da
  franquia; Cloud Logging acima de 50 GiB; tráfego de saída que não entre na trava (detalhe no
  [roteiro](ROTEIRO_FASE2.md#custos-fora-da-trava-estimativas-conferir-no-console)). Sem Cloud Build e sem varredura de
  vulnerabilidades.
- **Riscos de cobrança excedente:** a trava tem atraso e não cobre outros serviços; a partida a frio é cobrada; a conversa é
  cobrada durante a espera pelo Gemini; um XLSX de 15 MB consome cerca de 34 s de CPU a cada análise.
- **Medidas preventivas:** máximo de 1 instância, cobrança por requisição, sem aumento de CPU na partida, vagas e fila para
  operações pesadas, limite de 15 MB, o pedido abandonado na fila sai sem calcular, o log de acesso do Uvicorn desligado (o
  Cloud Run já registra as requisições), a política de limpeza do Artifact Registry e a verificação prévia (F2-0).

## H. Gatilhos

- **`ci.yml` no ramo de preparação: comprovado.** Cada envio do ramo disparou o CI: execuções 41369463989 (`2863e47`),
  41372746893 (`41b97bb`) e 41375485808 (`b8ae7fb`).
- **Gatilhos por etiqueta** (`validacao-gemini-real-*`, `imagem-*`, `publicacao-pages-*`): não podem ser comprovados na Fase 1
  (enviar etiquetas não está autorizado). A sintaxe dos workflows passou no actionlint (job `conteiner`), e os testes de
  `test_implantacao.py` conferem que só há os gatilhos previstos, sem `workflow_dispatch`, `repository_dispatch` ou
  `workflow_run`. O `teste-gatilho.yml` está pronto e só roda depois de "AUTORIZO O TESTE DE GATILHO", concedida em
  02/11/2026.
- **Teste de gatilho (02/11/2026): pendente.** Etiqueta `teste-gatilho-20261102` no último commit verificado, a execução de
  `teste-gatilho.yml` conferida pela API pública e a etiqueta apagada em seguida (seção M).
- **Se um gatilho não funcionar:** parar e apresentar as alternativas — ramo dedicado de acionamento com regra de ramo no
  ambiente; os arquivos de workflow no `main` (exige autorização para modificar o `main`); ou a validação real executada pelo
  responsável num terminal separado, com `scripts/validar_gemini_real.py`.

## I. Testes

Antes de cada envio, só as checagens de segundos do AGENTS.md (`py_compile`, `tsc --noEmit`, a governança depois do commit e
o padrão de chave nos arquivos alterados); os testes completos rodaram só no GitHub Actions.

| Execução | Commit | Resultado |
|---|---|---|
| 41369463989 | `2863e47` | 6 de 8 jobs em sucesso; o `conteiner` falhou em três pontos (abaixo) e, com ele, o `resumo` |
| 41372746893 | `41b97bb` | os 8 jobs em sucesso; os 6 roteiros de navegador do contêiner e da sessão passaram |
| 41375485808 | `b8ae7fb` | os 8 jobs em sucesso; a medição sem nenhum problema, com o pior caso de memória a 72,7% dos 2 GiB |

Na execução 41375485808: `backend`, 1.225 testes aprovados e 63 pulados (os de dados reais, que rodam no job seguinte);
`dados-reais`, 1.288 aprovados e nenhum pulado; `frontend`, os 160 testes do Node e o build; navegador, os 8 roteiros do
`ui-block1`, o do `ui-conversational` e os 6 do `conteiner` (hospedagem, conexão, página única, área de análise e mapa com a
base versionada, e a sessão); `governanca` em ordem.

**Problemas encontrados e corrigidos na Fase 1:**
- antes do primeiro envio: a chave inválida do Gemini (resposta real 400 `API_KEY_INVALID`) caía como falha interna, sem a
  espera de configuração; as rotas pesadas bloqueavam o laço de eventos (a saúde e a consulta da sessão esperavam o cálculo);
  o arquivo enviado era lido inteiro antes da conferência do tamanho; as mensagens de erro mostravam o código HTTP, e a falha
  de rede no gráfico mostrava o texto técnico do navegador; a verificação de saúde da interface era única, sem nova tentativa;
  o padrão de chave do comando não cobria o formato da chave em uso;
- na execução 41369463989: **o aviso de ocupado sumia no instante em que aparecia** (defeito do produto: a resposta da
  interação da sessão, que não espera vaga, o tirava; `b75fa65`); e dois defeitos da própria medição (as planilhas iam ao
  gráfico sem a escolha do código territorial, que o nome da coluna nunca estabelece; a conferência do prazo esperava 1.800
  exatos, e o serviço devolve o tempo restante com fração; `41b97bb`);
- na mesma revisão, a medição da memória das sessões não chegava ao teto pedido pelo comando (139 MiB de 256): passou a encher
  as sessões até o teto e a medir os envios com elas cheias, e a concorrência passou a registrar os pedidos simultâneos
  (`41b97bb`);
- na execução 41372746893: **o pior caso de memória chegou a 89,6% dos 2 GiB** (sessões no teto de 256 MiB e dois XLSX de
  15 MB juntos): o teto total foi reduzido para 128 MiB (`b8ae7fb`).

**Só se confirma no Cloud Run:** a partida a frio real (com a CPU do Google e sem o aumento na partida), a restrição de CPU
entre requisições, a latência da rede, o balanceador (que devolve 429 acima da concorrência com uma instância), o encerramento
por ociosidade e a troca de instâncias, o consumo efetivo da trava e o tráfego de saída.

## J. Providências que dependem do responsável

Em ordem, com o porquê. O passo a passo está em [PROVIDENCIAS_DO_RESPONSAVEL.md](PROVIDENCIAS_DO_RESPONSAVEL.md).

| Ordem | Providência | Situação em 02/11/2026 | Por quê |
|---|---|---|---|
| 1 | Decidir a divergência da RQ-FLX-17 | resolvida: opção (a) | a sessão pode se perder antes dos 30 minutos com mínimo 0 instâncias (seção F) |
| 2 | Decidir a política dos dados com o repositório público | resolvida: a caracterização e o repositório público no README | o README dizia que o repositório devia ser privado; o Pages e as proteções dos ambientes dependem de ele ser público no plano gratuito |
| 3 | Conferir ou ativar a varredura de segredos e a proteção de push | pendente; não conferível sem autenticação | barram o envio acidental de uma chave ao repositório público |
| 4 | Conferir e descartar o `stash@{0}` | pendente; o stash ainda existe | guarda um `backend/.env` com a chave; um `stash pop` seguido de commit a publicaria |
| 5 | Instalar o `gh` (opcional) | pendente; não instalado | sem ele, o agente só lê a API pública, sem o log e os artefatos das execuções |
| 6 | Teste de gatilho | autorizado; o resultado na seção H | comprova que uma etiqueta aciona um workflow que não está no ramo padrão, antes de a validação real e a Fase 2 dependerem disso |
| V-1 a V-7 | Validação real do Gemini | autorizada; o andamento na seção M | sem ela, o parecer não pode ser "Pronto para implantação"; V-2, V-4, V-6 e V-7 são do responsável |
| P-1 | Instalar o gcloud (de preferência fora dos dados móveis) e autenticá-lo | pendente; não instalado | toda a Fase 2 usa o gcloud |
| P-2 a P-9 | A trava e os alertas, os ambientes `producao` e `github-pages`, o segredo no Secret Manager e a restrição da chave, o Pages, as aprovações, as autorizações F2-n e as conferências no navegador | pendentes | cada operação da Fase 2 depende delas (seção K) |

## K. Roteiro da Fase 2

[ROTEIRO_FASE2.md](ROTEIRO_FASE2.md): F2-0 a F2-13, com os comandos revisados e não executados, o efeito, o custo esperado e
como desfazer cada operação, e os custos fora da trava. A concorrência (40) e o timeout (150 s) do F2-6 vêm da medição
(seção C). Ajustes de 02/11/2026 (seção 4 do comando):
- a política de limpeza do Artifact Registry protege por etiqueta (regra Keep) a imagem em uso e a anterior, a da reversão, e
  começa em simulação (F2-2), com os registros de auditoria de gravação de dados do Artifact Registry ligados no próprio F2-2:
  pela documentação do Google, o resultado da simulação só aparece neles, e o processo periódico do Google faz efeito em cerca
  de um dia;
- a marcação `em-uso` e `anterior` a cada implantação e reversão (F2-6);
- as exclusões só no F2-13, operação nova com autorização própria, depois de uma simulação com pelo menos três versões que
  preserve as duas imagens;
- o 404 de `/docs` sem `curl -f` e o CORS pelos cabeçalhos, sem `Access-Control-Allow-Origin` para uma origem estranha e com
  ele para `https://gustavohoff1987.github.io` (F2-8);
- as conferências na interface ficam com o responsável, no navegador, e as do agente, só pela API (F2-9 a F2-11; P-9);
- o gcloud não está instalado (P-1).

## L. Parecer

**Pronto com ressalvas.** Tudo o que a Fase 1 pede está implementado e verificado no CI com o Gemini simulado: a imagem
roda com 1 CPU e 2 GiB, parte em cerca de 10 s com o aquecimento antes da porta, dá as mesmas respostas da referência em
todas as famílias, recusa o que deve recusar antes de ler, mantém a saúde respondendo sob carga e cabe na memória no pior caso
medido (72,7% dos 2 GiB depois do ajuste do teto das sessões); a interface aberta pelo Pages trata os estados A a G.

Ressalvas, que impedem o "Pronto para implantação":
1. a validação real do Gemini está em andamento (autorizada em 02/11/2026; seção M); pelo comando de 01/11/2026, sem ela o
   parecer não pode ser "Pronto para implantação";
2. os gatilhos por etiqueta ainda não foram comprovados (o teste de gatilho, autorizado, roda depois do CI do último commit);
3. a varredura de segredos e a proteção de push não puderam ser conferidas sem autenticação (em 01/11/2026, desativadas), e o
   stash local com a chave ainda existe (providências 3 e 4);
4. as medições são do runner do GitHub: a partida a frio, a CPU entre requisições, a rede, o balanceador e o consumo real da
   trava só se confirmam no Cloud Run (F2-8 e F2-12);
5. um XLSX de 15 MB leva cerca de 34 s por análise no runner, porque é reenviado e lido de novo a cada pedido: é o principal
   risco de espera para quem o usa e de consumo da trava (o CSV do mesmo tamanho leva cerca de 5 s).

Resolvidas em 02/11/2026: a divergência da RQ-FLX-17 (opção a) e a política dos dados com o repositório público.

## M. Ajustes antes da Fase 2, teste de gatilho e validação real (02/11/2026)

**Decisões do responsável (seção 1 do comando):** a caracterização das bases ("informações agregadas, de natureza pública, que
não expõem dados pessoais ou sensíveis de cidadãos"), a procedência (dados oficiais do Ministério da Saúde, com extração
autorizada), a natureza (agregados por território e competência, sem registros individuais nem identificadores;
redistribuição permitida), o repositório público, a opção (a) para a RQ-FLX-17 e a chave atual mantida.

**Classificação (regra 1 do AGENTS.md), pela leitura, antes de codar:**
- a política dos dados no README e nos documentos: documentação, sem mudança de comportamento (o sistema, os dados versionados
  e a interface continuam iguais); a SPEC não trata de licença, privacidade do repositório nem data de extração, e nada nela é
  contrariado;
- as duas anotações internas da biblioteca conversacional (B-0190 e B-0299): arquivo do produto, sem mudança de
  comportamento (não são exibidas nem enviadas ao provedor);
- a conferência do repositório público, o ritmo, os tempos e as anotações da validação real: workflows e scripts de
  implantação, fora do produto;
- a opção (a) da RQ-FLX-17: divergência aprovada, no registro de comportamento;
- o roteiro e as providências: documentação.

**Ajustes feitos**

| Seção do comando | Ajuste | Commit |
|---|---|---|
| 2 | README, "Política dos dados do Brasil": a caracterização com o texto exato; item 8, o repositório público (o Pages e as proteções dos ambientes dependem disso no plano gratuito); item 9, a procedência e a natureza, sem a pendência da procedência; sem a pendência da licença e da redistribuição; "Origem da base Brasil" e a operação online sem tratar o repositório como privado. Ficam o manifesto, os originais preservados, os arquivos fora do frontend, nenhum registro ao Gemini e a governança metodológica; as salvaguardas das planilhas enviadas não mudam | `4e30a97` |
| 2 | `DADOS_BRASIL_VALIDACAO.md`, `BLOCO2_ETAPA1_REFERENCIAS_PROXIMIDADE.md` e `OTIMIZACAO_LATENCIA.md` (nota de atualização na análise de 12/10/2026), no mesmo sentido; nenhum documento menciona a data de extração; as duas anotações da biblioteca conversacional | `4e30a97` |
| 3 | `conferir_protecao.py`: o job `conferir-protecao` dos três workflows protegidos encerra a execução, sem chamadas nem envio, se o repositório não estiver público (a primeira conferência); os testes cobrem o repositório privado, interno, com visibilidade incoerente, ausente ou ilegível | `4e30a97` |
| 5 e 7 | Validação real: pelo menos 10 s entre o início das mensagens (o nível gratuito tem cerca de 10 chamadas por minuto, e um 429 real a encerraria), o tempo de cada mensagem, a falha técnica com o relatório gravado e o resumo sanitizado em até quatro anotações da execução (`anotar_validacao.py`), com os testes | `19f2fa5` |
| 1, 2 e 5 | A divergência aprovada da RQ-FLX-17 no registro, no README e na seção F; as providências atualizadas (1 e 2 resolvidas; 3 a 6 pelas conferências abaixo) | o commit deste relatório |
| 4 | O roteiro (F2-2, F2-5, F2-6, F2-8 a F2-11, o F2-13 novo e os custos), a P-1 com a instalação do gcloud e a P-9 nova | o commit deste relatório |

**Conferências da seção 5 (só leitura)**

| Conferência | Resultado em 02/11/2026 |
|---|---|
| GitHub CLI (`gh`) | não instalado (nem no PATH, nem nas pastas de instalação, nem no `winget`) |
| Acesso à API do GitHub | só a API pública sem autenticação, até 60 consultas por hora; nenhum token extraído de armazenamento de credenciais. Ela entrega o repositório, as execuções, os jobs, as anotações e os ambientes, mas não o log dos jobs (403) nem os artefatos (401) |
| Varredura de segredos e proteção de push | não conferíveis sem autenticação: o bloco `security_and_analysis` não vem na resposta pública. Em 01/11/2026, desativadas |
| Stash com `backend/.env` | não descartado: `git stash list` mostra `stash@{0}: On main: !!GitHub_Desktop<main>` (só a lista, sem abrir o conteúdo) |
| gcloud (P-1) | não instalado (`gcloud --version`: comando não encontrado); nenhuma autenticação |
| Repositório | público (`private: false`, `visibility: public`) |

**Andamento**

| Etapa | Situação | Peso |
|---|---|---|
| Ajustes das seções 2 a 5 | feitos | 35% |
| CI do último commit | em andamento | 15% |
| Teste de gatilho | pendente | 10% |
| Validação real (V-2 a V-7) | pendente | 30% |
| Relatório final e parecer revisto | pendente | 10% |
| **Conclusão estimada** | **35%** | |

**Teste de gatilho:** pendente (seção H).

**Validação real do Gemini:** pendente; as chamadas usadas, os desfechos e os tempos entram aqui.
