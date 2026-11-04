# Relatório da implantação — Fase 1 (preparação e validação) e ajustes antes da Fase 2

Agente Diagnóstico Territorial da Força de Trabalho na Saúde — Google Cloud Run (serviço de análise) e GitHub Pages (interface).
Comando de implantação de 01/11/2026 (`COMANDO_IMPLANTACAO_REVISADO (1).txt`), Fase 1, e comando de ajustes antes da Fase 2,
teste de gatilho e validação real do Gemini, de 02/11/2026 (`COMANDO_AJUSTES_PRE_FASE2.txt`). Ramo `implantacao/cloud-run-pages`.

**Situação (02/11/2026):** a Fase 1 está concluída (execução 41375485808, commit `b8ae7fb`, os 8 jobs em sucesso). O comando de
ajustes antes da Fase 2 também:
- os ajustes das seções 2 a 5 estão feitos e verificados (execução 41492208661, commit `381523a`, os 8 jobs em sucesso);
- o teste de gatilho passou (seção H);
- a validação real do Gemini foi feita com sucesso (execução 41506330654: 15 chamadas reais de 20, sem 429; seção M).

**Conclusão: 100% das etapas do comando.** O responsável apagou o segredo do ambiente `gemini-real` (V-7) e ativou a
varredura de segredos e a proteção de push (providência 3), ambas conferidas com o `gh` em 02/11/2026. O último CI do ramo
está em sucesso (seção I).

Nada foi publicado: nenhum recurso no Google Cloud, nenhuma configuração do GitHub feita pelo agente (o ambiente, o segredo e
as proteções foram configurados pelo responsável), nenhum merge e nenhum pull request. As únicas chamadas reais ao Gemini
foram as 15 da validação autorizada. **Parecer: Pronto para implantação** (seção L). A Fase 2 pode começar, operação por
operação, com "AUTORIZO F2-n"; o gcloud está instalado e autenticado (P-1, conferida em 02/11/2026). Próxima operação: F2-0
(verificação prévia, só leitura), com P-2 (a trava e os alertas conferidos no Console pelo responsável).

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
- **Validação real (02/11/2026): feita, com sucesso.** Execução 41506330654: 15 chamadas reais de 20, sem interrupção e
  sem nenhum 429; as 10 respostas redigidas pelo Gemini passaram na conferência de fidelidade (8 na primeira tentativa, 2
  depois de uma regeneração), em 1,03 a 3,93 s (mediana de 1,5 s); a chave inválida apareceu como problema de configuração.
  Detalhes na seção M.
- **Validação real (preparada na Fase 1, executada em 02/11/2026):** `validacao-gemini-real.yml` com o job `conferir-protecao` (sem ambiente e
  sem segredos) e o job `validacao` (ambiente `gemini-real`), teto de 20 chamadas somadas, 429 real encerra, chave inválida
  noutro contêiner e relatório sanitizado conferido contra o padrão de chave. O mecanismo é demonstrado por testes com
  respostas simuladas da API (`test_implantacao.py`): para sem chamadas quando o repositório não está público (desde
  02/11/2026), o ambiente não existe, não tem revisor, aceita outras etiquetas ou ramos, o gatilho não é a etiqueta ou o
  commit não pertence ao ramo; sem o segredo, nenhum pedido sai. Desde 02/11/2026, as mensagens começam com pelo menos 10 s
  entre si (precaução desta validação, não um limite da aplicação: o nível gratuito admite 15 chamadas por minuto, e um
  429 real encerra a validação), o roteiro registra o
  tempo de cada mensagem e o resumo sanitizado sai também nas anotações da execução (`anotar_validacao.py`), legíveis pela API
  pública do GitHub sem login.
  A validação real dependia de "AUTORIZO A VALIDAÇÃO REAL DO GEMINI" (providências V-1 a V-7), concedida em 02/11/2026.
- **Chamadas por mensagem (medidas):** 1 por mensagem numa conversa típica, 0 nas respondidas localmente ("Obrigado!") e até 3
  com as regenerações. Na validação real: 1 nas redigidas pelo Gemini na primeira tentativa, 2 nas duas com regeneração, 0
  nas respondidas pelo canal sistêmico ou localmente.
- **Capacidade frente ao nível gratuito:** 15 requisições por minuto (RPM), 250 mil tokens por minuto (TPM) e 500
  requisições por dia (RPD) para o `gemini-3.5-flash-lite`, conferidos pelo responsável no AI Studio em 02/11/2026, no projeto
  da chave em uso (o provedor pode mudá-los): cerca de 15 mensagens por minuto e 500 por dia, somando todos os usuários. Sem teto local (decisão de
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
- **Teste de gatilho (02/11/2026): comprovado.** A etiqueta `teste-gatilho-20261102`, enviada às 18:02:12 UTC ao último
  commit verificado (`381523a`, execução 41492208661 em PASS), acionou em 1 s a execução 41496728825 do `teste-gatilho.yml`,
  que não está no ramo padrão. O job `registrar` terminou em sucesso em 31 s e registrou `ref: refs/tags/teste-gatilho-20261102`,
  `commit: 381523ae7403…` e `evento: push`. A etiqueta foi apagada em seguida no GitHub e na cópia local, e o apagamento não
  iniciou nenhuma execução. Os workflows protegidos usam o mesmo mecanismo (`push` de etiqueta com o padrão de cada um).
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
| 41492208661 | `381523a` (ajustes de 02/11/2026) | os 8 jobs em sucesso: `backend` 1.237 aprovados e 63 pulados (os de dados reais); `dados-reais` 1.300 aprovados e nenhum pulado; `frontend`, 160 testes do Node e nenhuma falha; navegador, contêiner e governança em ordem. Os 12 testes novos são a conferência do repositório público, o ritmo das mensagens, as anotações e o passo do workflow |
| 41510828308 | `da65a1c` (relatório de 02/11/2026) | os 8 jobs em sucesso |
| 41516575786 | `4d32bb4` (parecer revisto) | os 8 jobs em sucesso |
| 41529991952 | `c762c2e` (limites do Gemini, P-1 e segurança) | os 8 jobs em sucesso |

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
| 3 | Ativar a varredura de segredos e a proteção de push | feita em 02/11/2026; as duas ativadas, conferidas com o `gh`, nenhum alerta aberto | barram o envio acidental de uma chave ao repositório público |
| 4 | Descartar o `stash@{0}`, depois de extrair os três scripts soltos de `.local/`, e proteger o `main` localmente | feita em 02/11/2026, com a autorização do responsável (seção M) | o stash guardava o `backend/.env` com a chave, que um `stash pop` seguido de commit publicaria; o `main` não tem `.gitignore` |
| 5 | Instalar o `gh` | feita em 02/11/2026 | com ele, o agente lê o log e os artefatos das execuções |
| 6 | Teste de gatilho | feito: comprovado (seção H) | comprova que uma etiqueta aciona um workflow que não está no ramo padrão, antes de a validação real e a Fase 2 dependerem disso |
| V-1 a V-6 | Validação real do Gemini | feita, com sucesso (seção M) | sem ela, o parecer não podia ser "Pronto para implantação" |
| V-7 | Apagar o segredo `GEMINI_API_KEY` do ambiente `gemini-real` | feita em 02/11/2026: o ambiente está sem segredos (conferido com o `gh`) | a validação acabou; era só a cópia no GitHub, e a chave continua válida |
| P-1 | Instalar o gcloud e autenticá-lo | feita em 02/11/2026: versão 591.0.0, conta `mister.hoff87@gmail.com`, projeto `agente-diagnostico-territorial`, configuração `default` (conferido só em leitura) | toda a Fase 2 usa o gcloud |
| P-2 | Conferir a trava e os alertas no Console | feita em 02/11/2026: limite de R$ 11 do Cloud Run (Configurado; 50, 80 e 100%) e orçamento de alertas de R$ 11 (25, 50, 75 e 100%), sem alteração | a Fase 2 só começa com o controle de gastos confirmado |
| P-3 a P-9 | Os ambientes `producao` e `github-pages`, o segredo no Secret Manager e a restrição da chave, o Pages, as aprovações, as autorizações F2-n e as conferências no navegador | pendentes | cada operação da Fase 2 depende delas (seção K) |

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
  preserve as duas imagens. **Revisto em 02/11/2026 pelo responsável:** a F2-2 fica só com o repositório, e a política de
  limpeza, a simulação e os registros `DATA_WRITE` ficam adiados (F2-13, só se necessária). Sem limpeza automática, nada é
  apagado; as etiquetas `em-uso` e `anterior` da F2-6 continuam;
- o 404 de `/docs` sem `curl -f` e o CORS pelos cabeçalhos, sem `Access-Control-Allow-Origin` para uma origem estranha e com
  ele para `https://gustavohoff1987.github.io` (F2-8);
- as conferências na interface ficam com o responsável, no navegador, e as do agente, só pela API (F2-9 a F2-11; P-9);
- o gcloud: não instalado em 02/11/2026 de manhã; instalado e autenticado depois pelo responsável (P-1).

## L. Parecer (revisto em 02/11/2026)

**Pronto para implantação.** Revisto depois de o responsável ativar as proteções do repositório; antes, era "Pronto com
ressalvas", com uma única ressalva, a varredura de segredos e a proteção de push desativadas.
- **O que a Fase 1 pede** está implementado e verificado no CI com o Gemini simulado:
  - a imagem roda com 1 CPU e 2 GiB e parte em cerca de 10 s, com o aquecimento antes da porta;
  - dá as mesmas respostas da referência em todas as famílias;
  - recusa o que deve recusar antes de ler e mantém a saúde respondendo sob carga;
  - cabe na memória no pior caso medido: 72,7% dos 2 GiB, depois do ajuste do teto das sessões;
  - a interface aberta pelo Pages trata os estados A a G.
- **A validação real do Gemini**, que faltava, foi feita com sucesso em 02/11/2026 (seção M):
  - 15 chamadas reais de 20, sem 429;
  - todas as respostas redigidas pelo Gemini passaram na conferência de fidelidade;
  - a chave inválida foi tratada como problema de configuração.
- **O gatilho por etiqueta** está comprovado (seção H).

- **As proteções do repositório**, conferidas com o `gh` em 02/11/2026, estão ativas: a varredura de segredos
  (`secret_scanning`) e a proteção de push (`secret_scanning_push_protection`), sem nenhum alerta aberto. Com o repositório
  público e a chave passando por segredos do GitHub e do Secret Manager, elas barram o envio acidental de uma chave. Seguem
  desativados, como opcionais, os padrões genéricos, a verificação de validade e as atualizações de segurança do Dependabot.

Nenhuma ressalva impede a implantação. A Fase 2 continua dependendo, operação por operação, de "AUTORIZO F2-n".

Riscos que só se confirmam na Fase 2 e não impedem o início dela:
- **Medições:** são do runner do GitHub. A partida a frio, a CPU entre requisições, a rede, o balanceador e o consumo real da
  trava só se confirmam no Cloud Run (F2-8 e F2-12).
- **Planilha XLSX de 15 MB:** leva cerca de 34 s por análise no runner, porque é reenviada e lida de novo a cada pedido. É o
  principal risco de espera para quem a usa e de consumo da trava; o CSV do mesmo tamanho leva cerca de 5 s.
- **Nível gratuito do Gemini:** admite 15 chamadas por minuto e 500 por dia para todos os usuários juntos (conferido em
  02/11/2026; o provedor pode mudar). Acima disso, a conversa
  espera e usa a resposta determinística de reserva (decisão de 26/10/2026, sem teto local).

Pré-requisito da Fase 2: o gcloud instalado e autenticado (P-1) — feito em 02/11/2026.

Resolvidas em 02/11/2026:
- a validação real do Gemini, com o segredo do ambiente `gemini-real` apagado depois (V-7);
- o gatilho por etiqueta;
- a divergência da RQ-FLX-17 (opção a);
- a política dos dados com o repositório público;
- o stash local com a chave (descartado, com o `main` protegido localmente);
- a varredura de segredos e a proteção de push (ativadas pelo responsável).

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
| 5 e 7 | Validação real: pelo menos 10 s entre o início das mensagens (precaução desta validação; o nível gratuito admite 15 chamadas por minuto, e um 429 real a encerraria), o tempo de cada mensagem, a falha técnica com o relatório gravado e o resumo sanitizado em até quatro anotações da execução (`anotar_validacao.py`), com os testes | `19f2fa5` |
| 1, 2 e 5 | A divergência aprovada da RQ-FLX-17 no registro, no README e na seção F; as providências atualizadas (1 e 2 resolvidas; 3 a 6 pelas conferências abaixo) | `381523a` |
| 4 | O roteiro (F2-2, F2-5, F2-6, F2-8 a F2-11, o F2-13 novo e os custos), a P-1 com a instalação do gcloud e a P-9 nova | `381523a` |
| 5 a 7 | As orientações complementares (o `gh`, a segurança do repositório e o stash), os resultados do teste de gatilho e da validação real, o parecer revisto, as providências e, no F2-2, a remoção do arquivo temporário com a política do projeto | o commit deste relatório |

**Conferências da seção 5 (só leitura)**

| Conferência | Resultado em 02/11/2026 |
|---|---|
| GitHub CLI (`gh`) | não instalado (nem no PATH, nem nas pastas de instalação, nem no `winget`) |
| Acesso à API do GitHub | até a instalação do `gh`, só a API pública sem autenticação, até 60 consultas por hora; nenhum token extraído de armazenamento de credenciais. Ela entrega o repositório, as execuções, os jobs, as anotações e os ambientes, mas não o log dos jobs (403) nem os artefatos (401). Depois, o `gh` autenticado (abaixo) |
| Varredura de segredos e proteção de push | sem autenticação, não conferíveis (o bloco `security_and_analysis` não vem na resposta pública); com o `gh`, desativadas; depois, **ativadas** pelo responsável e conferidas de novo, sem nenhum alerta aberto (abaixo) |
| Stash com `backend/.env` | não descartado: `git stash list` mostra `stash@{0}: On main: !!GitHub_Desktop<main>`; o exame só pelos metadados está abaixo |
| gcloud (P-1) | de manhã, não instalado; depois, instalado pelo responsável e conferido só em leitura: Google Cloud SDK 591.0.0, conta `mister.hoff87@gmail.com` ativa, projeto `agente-diagnostico-territorial`, configuração `default` ativa (usado pelo caminho completo, fora do PATH da sessão) |
| Repositório | público (`private: false`, `visibility: public`) |

**Orientações complementares do responsável (02/11/2026): GitHub CLI e stash local**

- **`gh` disponível e autenticado.** O responsável instalou e autenticou o GitHub CLI num PowerShell separado. Nesta sessão, o
  executável não está no PATH (herdado de antes da instalação) e é usado pelo caminho completo,
  `C:\Program Files\GitHub CLI\gh.exe`, versão 2.103.3, sem reiniciar o Claude Code. `gh auth status`, com as linhas do token
  filtradas: conta `gustavohoff1987`, credencial no cofre do sistema (keyring), escopos `gist`, `read:org`, `repo` e
  `workflow`, protocolo HTTPS. Nenhum token foi exibido, copiado ou extraído. Passa a ser a forma preferida de consultar as
  execuções, os logs e os artefatos.
- **Segurança do repositório, com o `gh` (permissão de administrador):** a varredura de segredos (`secret_scanning`), a
  proteção de push (`secret_scanning_push_protection`), os padrões genéricos (`secret_scanning_non_provider_patterns`), a
  verificação de validade (`secret_scanning_validity_checks`) e as atualizações de segurança do Dependabot estão
  **desativadas**. O agente não as altera: ativar a varredura e a proteção de push continua sendo a providência 3. Depois da
  validação real, o responsável ativou as duas: com o `gh`, `secret_scanning` e `secret_scanning_push_protection` aparecem
  ativados e não há nenhum alerta aberto. Os padrões genéricos, a verificação de validade e as atualizações de segurança do
  Dependabot seguem desativados, como opcionais.
- **Stash `stash@{0}`, só pelos metadados e nomes**, sem abrir conteúdo nem calcular nada sobre os arquivos `.env`. Criado
  pelo GitHub Desktop em 17/10/2026, 19:25 (−03), no `main` (`6284151`, que só tem a SPEC e nenhum `.gitignore`); commits
  `73427d3` (cópia de trabalho) e `17d88e5` (índice, idêntico à cópia de trabalho), nenhum enviado ao GitHub. Guarda 11.114
  arquivos, todos como adicionados em relação ao `main`:

  | Categoria | Arquivos |
  |---|---|
  | `frontend/node_modules` (dependências instaladas; o `npm ci` as recria) | 10.001 |
  | `.local/`: caches do npm (382), logs de execuções do Actions baixados em 17/10 (257), temporários do pytest (252), saídas de roteiros de interface, de execuções e de investigações (`ui*`, `run*`, `remediation*` e outras, com cópias da base do Brasil; 117) e três scripts soltos (`integrity_exploration.py`, `test_investigation_ui.py`, `update_view_controls.py`) | 1.011 (sem os `.env`) |
  | caches do Python (`__pycache__`) | 69 |
  | `frontend/dist` e `frontend/.vite` (build e cache) | 8 |
  | arquivos `.env`: `backend/.env` e 24 nos temporários do pytest em `.local/` | 25 |
  | código, testes ou documentação do produto | **nenhum** |

  Nove arquivos guardados (as cópias de `Dados_Brasil.xlsx`, uma linha de base de integridade e uma imagem do build) têm a
  mesma versão em algum ramo; os demais só existem no stash, e todos são artefatos locais que o `.gitignore` deste ramo ignora
  (`.local/`, `node_modules/`, `__pycache__/`, `frontend/dist/`).
- **Proteção do `backend/.env` contra commit:** neste ramo, o `.gitignore` o ignora (`git check-ignore`: linha 10, `.env`;
  também `.env.*`, com exceção de `.env.example`), e ele não está no índice. Não há proteção no `main`, que não tem
  `.gitignore`: foi assim que, em 17/10, o GitHub Desktop pôs o `.env` e os artefatos no stash ao trocar de ramo. Um
  `git stash pop` ou `apply` neste ramo devolveria o `backend/.env` já adicionado ao índice, e o `.gitignore` não impede o
  commit de arquivo já adicionado.
- **Recomendação:** havia evidência suficiente para descartar o stash. Ele não guardava código, testes nem documentação do
  produto, só artefatos locais que se recriam ou que só têm valor de histórico, e o `.env`, cuja chave continua no AI Studio.
  O que podia merecer preservação: os três scripts soltos de `.local/`.
- **Feito com a autorização expressa do responsável (02/11/2026):**
  1. os três scripts foram extraídos para `.local/`, pelos identificadores dos objetos, sem exibir o conteúdo:
     `integrity_exploration.py` (1.707 bytes), `test_investigation_ui.py` (516) e `update_view_controls.py` (2.192). Nenhum
     existia lá antes, e o `git hash-object` dos gravados confere com os do stash. Padrão de chave: 3 arquivos examinados,
     nenhuma ocorrência;
  2. o `stash@{0}` (`73427d3e2b`, conferido logo antes) foi descartado, e a lista de stashes está vazia. Os objetos dele ficam
     no banco local do git, sem nenhuma referência, até a coleta de lixo do próprio git; nunca foram enviados ao GitHub;
  3. `.env`, `.env.*` e `.local/` estão no `.git/info/exclude`, local e não versionado, que vale para todos os ramos. Num
     repositório sem `.gitignore`, como o `main`, elas ignoram o `backend/.env`, os `.env.*` e o `.local/`; neste ramo, o
     `.gitignore` tem precedência e continua deixando o `.env.example` versionável. Nenhum arquivo rastreado foi afetado.
- **Anotações da validação real (decisão técnica):** ficam como estão (`19f2fa5`, já verificado pelos testes). Retirá-las
  seria mais uma alteração no workflow e mais uma execução do CI, contra a orientação de evitar alterações desnecessárias.
  Elas só repetem o relatório sanitizado, já conferido contra o padrão de chave. Com o `gh`, a fonte principal do resultado
  passa a ser o artefato e o log da execução, e as anotações servem de conferência rápida. O espaçamento de 10 s entre as
  mensagens não depende do acesso. Ele evita o 429 real do nível gratuito e continua necessário.

**Andamento**

| Etapa | Situação | Peso |
|---|---|---|
| Ajustes das seções 2 a 5 | feitos | 35% |
| CI do último commit | PASS: execução 41492208661, `381523a`, os 8 jobs | 15% |
| Teste de gatilho | comprovado: execução 41496728825; etiqueta apagada | 10% |
| Validação real (V-2 a V-6) | feita, com sucesso: execução 41506330654 | 30% |
| Relatório final e parecer revisto | este relatório (seção L) | 10% |
| **Conclusão** | **100% das etapas do comando**; o V-7 e a providência 3 também feitos pelo responsável | |

**Teste de gatilho:** comprovado em 02/11/2026 (seção H). A etiqueta `teste-gatilho-20261102` no `381523a` acionou a execução
41496728825 em 1 s, que terminou com sucesso em 31 s; a etiqueta foi apagada.

**Validação real do Gemini (02/11/2026), passo a passo:**
- **V-2 e V-3:** o responsável criou o ambiente `gemini-real`. A conferência, só em leitura pelo `gh`, encontrou:
  - o revisor obrigatório `gustavohoff1987`, com "Prevent self-review" e o bypass de administradores desativados
    (`can_admins_bypass: false`);
  - implantações só por regras próprias (`custom_branch_policies: true`, `protected_branches: false`), com uma única regra, a
    etiqueta `validacao-gemini-real-*`, e nenhuma de ramo;
  - nenhum segredo nem variável no ambiente ou no repositório, e nenhum outro ambiente.

  A função `conferir()` do `conferir_protecao.py`, a mesma do job `conferir-protecao`, foi rodada localmente com a API real
  pelo `gh`, sem enviar etiqueta, para a etiqueta `validacao-gemini-real-20261102` no `381523a`. Ela conferiu as cinco
  condições: o repositório público, o ambiente, o revisor, a regra da etiqueta e o commit no ramo.
- **V-4:** o responsável cadastrou a chave atual como segredo `GEMINI_API_KEY` do ambiente. O `gh` conferiu só o nome e a
  data (19:00:04 UTC), e não há segredo no repositório.
- **V-5:** a etiqueta `validacao-gemini-real-20261102` foi enviada às 19:03:17 UTC ao `381523a` e acionou a execução
  41506330654. O job `conferir-protecao` passou em 8 s, e o job `validacao` esperou a aprovação, sem nenhuma chamada antes
  dela.
- **V-6:** o responsável aprovou às 19:23 UTC. O job `validacao` levou 4 min (19:23:22 a 19:27:21 UTC), assim:
  - dependências fixadas, 15 s;
  - a imagem do mesmo commit, 22 s, sem envio a registro;
  - os dois contêineres de 1 CPU e 2 GiB prontos, 10 s;
  - a validação, 3 min 1 s.
  
  Todos os passos terminaram em sucesso. O resultado vem de três fontes, que coincidem:
  - o artefato `validacao-gemini-real`, baixado com o `gh` para uma pasta nova e conferido de novo: nenhuma ocorrência do
    padrão de chave;
  - o log, em que a chave só aparece mascarada (`***`);
  - as quatro anotações.
- **V-7, feito pelo responsável:** o segredo `GEMINI_API_KEY` saiu do ambiente `gemini-real`, que está sem segredos
  (conferido com o `gh`, só pelos nomes). Era só a cópia no GitHub; a chave continua válida.

**Resultado da validação real**

| Medida | Resultado |
|---|---|
| Chamadas reais | **15 de 20**: 3 pelo caminho HTTP do contêiner, 11 no roteiro e 1 com a chave inválida. Sem interrupção e sem nenhum 429 |
| Ritmo | 18 mensagens em 3 min 1 s, com pelo menos 10 s entre o início de duas, abaixo do limite de 15 chamadas por minuto do nível gratuito; o intervalo foi precaução do teste, não limite da aplicação |
| Provedor | configurado, modelo `gemini-3.5-flash-lite`, disponível |
| Autenticação e modelo | a interpretação pelo Gemini em 1,12 s, com 1 chamada |
| Caminho HTTP: a pergunta sobre o resultado e a explicação mais simples | respondidas pelo canal sistêmico, sem chamada (0,42 s e 0,53 s), todas com status 200 |
| Caminho HTTP: a pergunta conceitual | redigida pelo Gemini e aprovada na conferência de fidelidade na segunda tentativa (1 regeneração): 3,93 s, 2 chamadas |
| Roteiro `validar_gemini_real.py` | 13 mensagens, todas com status 200, código 0. 9 redigidas pelo Gemini e aprovadas na conferência (`GEMINI_VALIDADO`): continuidade, explicação do resultado, explicação progressiva (3), outra formulação, paráfrase metodológica (2) e governança. 8 passaram na primeira tentativa e 1 na segunda, em 1,03 a 2,50 s. 3 foram respondidas localmente, sem chamada (0,01 a 3,52 s; entre elas, o pedido de recomendar uma política, do cenário de governança). A pergunta de cobertura veio pelo canal contextual, sem texto redigido pelo Gemini (3,15 s); pela contagem, ela usou a 11ª chamada do roteiro |
| Reserva determinística | nenhuma: todo texto do Gemini apresentado passou na conferência |
| Chave propositalmente inválida (outro contêiner) | a recusa do provedor apareceu como problema de configuração (`causa: configuracao`, escopo `acesso`), sem detalhe técnico, em 0,14 s |
| Tempos das respostas redigidas pelo Gemini | de 1,03 a 3,93 s, com mediana de 1,5 s (10 respostas); a mais longa foi a que precisou de regeneração |
| Sigilo | relatório, anotações e log sem nenhuma ocorrência do padrão de chave; nenhum texto de mensagem ou de resposta no relatório publicado |

Observação de manutenção: a execução avisou que a ação `actions/upload-artifact` fixada (v4.6.2) é de Node.js 20 e roda
forçada no Node.js 24 do GitHub. Não afetou o resultado; a troca por uma versão para Node.js 24 fica para quando ela estiver
fixada no repositório.

## N. Comando consolidado: atualizações finais e continuidade da Fase 2 (02/11/2026)

**Atualizações documentais e conferências (seções 1 a 4 do comando), só em leitura:**
- **Limites do Gemini:** conferidos pelo responsável no AI Studio em 02/11/2026, no projeto da chave em uso, para o
  `gemini-3.5-flash-lite` no nível gratuito: 15 requisições por minuto (RPM), 250 mil tokens por minuto (TPM) e 500
  requisições por dia (RPD). O provedor pode mudá-los. As referências a "cerca de 10 por minuto" foram trocadas nos documentos
  e nos comentários das ferramentas de validação. Os 10 s entre as mensagens da validação real foram precaução daquele teste,
  não limite da aplicação. Nenhum código da integração, tratamento de 429, governança conversacional ou configuração de
  infraestrutura mudou, e a validação real não foi repetida.
- **P-1 concluída:** Google Cloud SDK 591.0.0, conta `mister.hoff87@gmail.com` ativa, projeto `agente-diagnostico-territorial`,
  configuração `default` ativa (`gcloud --version`, `auth list`, `config list` e `config configurations list`). O executável
  está fora do PATH desta sessão e é usado pelo caminho completo. Nenhum recurso do Google Cloud foi criado, alterado ou
  consultado além disso.
- **Segurança do GitHub (com o `gh`):** repositório público; varredura de segredos e proteção de push ativadas; nenhum alerta
  aberto; o ambiente `gemini-real` continua configurado e sem segredos (V-7); nenhum segredo de repositório; nenhum stash
  local; os três scripts preservados em `.local/`; o `gh` autenticado na conta `gustavohoff1987`. A chave no AI Studio foi
  mantida, segundo o responsável.
- **CI:** o último commit antes deste comando, `4d32bb4`, passou nos 8 jobs (execução 41516575786). O commit destas
  atualizações (`c762c2e`), só de documentação e comentários, passou nos 8 jobs (execução 41529991952).

**Fase 2: registro das operações** (cada uma só depois de "AUTORIZO F2-n"; o roteiro está em
[ROTEIRO_FASE2.md](ROTEIRO_FASE2.md))

| Operação | Situação |
|---|---|
| F2-0 — verificação prévia (só leitura) | **feita** com "AUTORIZO F2-0": 0 falhas; os 2 itens MANUAL confirmados pela P-2 |
| F2-1 — habilitar as APIs | **feita** com "AUTORIZO F2-1" (abaixo) |
| F2-2 — repositório do Artifact Registry | **concluída** com o escopo simplificado: repositório mantido, política de limpeza retirada, `DATA_WRITE` desligado pelo responsável no Console (abaixo) |
| F2-3 — contas de serviço e federação restrita ao ambiente `producao` | **feita** com "AUTORIZO F2-3" (abaixo) |
| F2-4 — leitura do segredo pela conta de execução | **feita** com "AUTORIZO F2-4" (abaixo) |
| F2-3 — correção da federação | **feita** com "AUTORIZO F2-3" (abaixo) |
| F2-5 — enviar a imagem | **feita**: a primeira tentativa falhou na federação; depois da correção, a imagem foi enviada (abaixo) |
| F2-6 — implantar no Cloud Run, sem acesso público | **feita** com "AUTORIZO F2-6" (abaixo) |
| F2-7 — liberar o acesso público | **feita** com "AUTORIZO F2-7" (abaixo) |
| F2-8 — testes de produção sem o Gemini | **feita** com "AUTORIZO F2-8" (abaixo) |
| F2-9 — publicar a interface | **feita** com "AUTORIZO F2-9" e conferida pelo responsável no navegador (abaixo) |
| F2-10 — teste de produção com o Gemini real | **feita** com "AUTORIZO F2-10" (abaixo) |
| F2-11 a F2-13 | não iniciadas (a F2-13, adiada) |

**F2-0 (02/11/2026).** `scripts/implantacao/verificacao_previa.py`, com o gcloud pelo caminho completo e
`CLOUDSDK_CORE_DISABLE_PROMPTS=1` (o gcloud não oferece habilitar APIs). Resultado:
- **OK:** conta `mister.hoff87@gmail.com`, projeto `agente-diagnostico-territorial`, região `us-central1`, conta de
  faturamento vinculada (`018DD6-38822B-764E9C`).
- **Nenhum recurso da implantação ainda:** as APIs do Cloud Run, do Artifact Registry e do Secret Manager estão desligadas
  (então não há serviço, repositório nem segredo); nenhuma conta de serviço criada e nenhum pool de identidade.
- **APIs:** o Cloud Build e o Container Scanning (não previstos) estão desligados. Ligadas, as que o Google habilita por padrão
  num projeto novo (BigQuery e afins, Cloud Logging, Monitoring, Trace, Storage, Datastore, Dataform, Dataplex e as de
  gerenciamento): sem custo sem uso, e nenhuma é usada pela implantação além do Logging e do Monitoring do Cloud Run.
- **MANUAL (P-2):** o orçamento de alertas de R$ 11 (a listagem pelo gcloud exige a API de orçamentos, que não está
  habilitada no projeto, e nada foi habilitado para isso) e a trava de R$ 11 do Cloud Run: conferência do responsável no
  Console.

**Problema encontrado e corrigido na primeira execução:** o script tomava uma listagem que falhava por "nenhum recurso" (as
listagens do Cloud Run, do Artifact Registry e do Secret Manager falham com as APIs desligadas, e uma falha de permissão
passaria do mesmo jeito). Agora, com a API desligada, o item diz isso; com a API ligada, a falha da listagem é FALHA; a falha
da própria lista de APIs também. Teste novo em `test_implantacao.py`. A F2-0 foi repetida com o script corrigido, com o
mesmo resultado e os três itens explícitos. (Na conferência manual das listagens, o `gcloud` sem extensão no Git Bash falha
por montar mal o caminho do SDK; o certo é o `gcloud.cmd`, que é o que o script encontra.)

**P-2 (02/11/2026), concluída pelo responsável no Console:** o limite de gastos mensal de R$ 11 do projeto, com status
Configurado, só do Cloud Run, com alertas de 50, 80 e 100%; e o orçamento geral de alertas de R$ 11 por mês, com 25, 50, 75
e 100%. As configurações financeiras não foram alteradas.

**F2-1 (02/11/2026).** `gcloud services enable` das sete APIs no projeto de hospedagem `agente-diagnostico-territorial`
(operação `acf.p2-338451103854-4c947d6e-…`, concluída com sucesso). Conferência só em leitura: `run`, `artifactregistry`,
`secretmanager`, `iam`, `iamcredentials`, `sts` e `cloudresourcemanager` ligadas; `cloudbuild` e `containerscanning`
desligadas. O Google ligou junto, como dependências, `containerregistry.googleapis.com` e `pubsub.googleapis.com`, sem custo
sem uso e não usadas pelo roteiro. Nenhum recurso criado; o projeto da chave do Gemini não foi tocado.

**F2-2 (02/11/2026).**
- **Repositório:** `agente-diagnostico-territorial`, Docker, `us-central1`, modo padrão, chave gerenciada pelo Google, 0 MB.
  Antes da criação, a listagem confirmou que não havia repositório.
- **Auditoria:** a política IAM do projeto foi lida para um arquivo temporário fora do repositório. Ela não tinha
  `auditConfigs` e tinha 6 bindings. Recebeu só `artifactregistry.googleapis.com` com `DATA_WRITE` e foi gravada de volta
  com o etag (novo etag `BwZfU5kPhJo=`). O arquivo temporário foi apagado. Na conferência, a entrada de auditoria está
  presente e os 6 bindings continuam lá. Nenhum membro foi exibido.
- **Limpeza:** as três regras (`manter-em-uso-e-anterior`, `manter-a-mais-recente` e `apagar-as-demais-depois-de-1-dia`)
  estão aplicadas com `cleanupPolicyDryRun: true`. Nada é apagado até a F2-13.
- **Problemas de execução no Windows**, sem efeito em nenhum recurso:
  - Pelo Git Bash, o `gcloud.cmd`, cujo caminho tem espaços, recebeu mal um argumento entre aspas, e o `cmd.exe` não chegou a
    rodar a criação.
  - Pelo PowerShell, o script Python em linha perdeu as aspas, e a saída JSON veio com BOM.
  - Contorno: executar os comandos pelo PowerShell e usar scripts em arquivo. O roteiro registra isso em "Execução no
    Windows".

**F2-2, escopo simplificado (02/11/2026).** Depois da execução, o responsável decidiu manter só o repositório. Adiou os
registros de auditoria `DATA_WRITE` e a política de limpeza (em simulação ou com exclusões) e preservou os registros de
auditoria padrão. A mensagem chegou quando a operação já tinha terminado. O roteiro foi atualizado (F2-2 e F2-13), e a
retirada dos dois itens já aplicados foi apresentada para autorização. O repositório fica.

**F2-2, escopo simplificado, execução (02/11/2026, "AUTORIZO F2-2"):**
- **Política de limpeza:** as três regras foram retiradas com `delete-cleanup-policies`. O repositório continua vazio e sem
  nenhuma regra. O indicador `cleanupPolicyDryRun: true` ficou, inerte sem regras; uma política futura começaria em
  simulação.
- **Registros `DATA_WRITE`:** não saem pelo gcloud. Gravar a política sem `auditConfigs` deixa a configuração como está, porque
  o gcloud só atualiza os campos presentes (etag `BwZfVAt0dwk=`; o resto da política, igual). Gravar a entrada sem nenhum tipo
  de registro é recusado pelo Google (`INVALID_ARGUMENT`), e nada muda. A outra via, a API com um token impresso pelo gcloud,
  contraria a regra de não extrair tokens e não foi usada. O agente pediu ao responsável que desmarque o "Data Write" do
  Artifact Registry no Console (IAM e administrador → Registros de auditoria). Os 6 bindings estão preservados em todas as
  leituras, e os arquivos temporários foram apagados.

**F2-2 concluída (02/11/2026).** O responsável desmarcou o "Data Write" do Artifact Registry no Console. A conferência só em
leitura mostrou:
- a política do projeto sem nenhuma configuração de auditoria (`auditConfigs` vazio), como no início; os registros padrão
  do Google seguem;
- os 6 bindings intactos;
- o repositório `agente-diagnostico-territorial` vazio e sem política de limpeza.

**F2-3 (02/11/2026).** Pelo PowerShell, com o gcloud chamado pelo Python embutido do SDK (`platform\bundledpython\python.exe
lib\gcloud.py`), sem o `cmd.exe`, que interpretaria o `&&` e as aspas da condição.
- **Contas de serviço:** `adt-execucao@agente-diagnostico-territorial.iam.gserviceaccount.com` e
  `adt-envio-imagem@agente-diagnostico-territorial.iam.gserviceaccount.com`, ativas e sem nenhuma chave criada.
- **Permissões:**
  - `roles/artifactregistry.writer` só no repositório, para a conta de envio;
  - `roles/iam.workloadIdentityUser` sobre a conta de envio, só para
    `principal://…/workloadIdentityPools/github/subject/repo:gustavohoff1987/Teste-Agente:environment:producao`;
  - nenhuma permissão sobre a conta de execução, e nenhum papel das contas novas no projeto.
- **Federação:** o pool `github` e o provedor OIDC `teste-agente`, `ACTIVE`, com o emissor
  `https://token.actions.githubusercontent.com` e a condição restrita ao repositório, ao ambiente `producao` e ao subject.
- **Valores para a P-3** (não secretos, variáveis do ambiente `producao`):
  - `GCP_PROVEDOR_DE_IDENTIDADE` = `projects/338451103854/locations/global/workloadIdentityPools/github/providers/teste-agente`;
  - `GCP_CONTA_DE_ENVIO_DE_IMAGEM` = `adt-envio-imagem@agente-diagnostico-territorial.iam.gserviceaccount.com`.
- **Problemas encontrados e corrigidos:**
  - o nome de exibição da conta de envio passava de 100 caracteres e foi recusado, sem criar nada; o nome foi encurtado, e o
    roteiro também;
  - a conta padrão do Compute (`338451103854-compute@developer.gserviceaccount.com`), criada pelo Google ao habilitar o Cloud
    Run, seria apontada como "não prevista" pela verificação prévia e travaria a F2-0 antes da F2-6. O script passou a
    reconhecê-la (OK, não usada pelo serviço), com teste. A conta não foi alterada.

**P-4 e P-3 (03/11/2026), feitas pelo responsável e conferidas só em leitura:**
- **P-4:** o segredo `gemini-api-key` existe no projeto de hospedagem, com replicação automática e a versão 1 `enabled`
  (criada em 03/11/2026, 00:43 UTC), com a chave atual, segundo o responsável. O valor não foi lido. Ainda não há permissões
  sobre ele, nem outros segredos. A restrição da chave à Generative Language API e o projeto da chave sem faturamento ficam
  como informados pelo responsável: o agente não lê o projeto da chave.
- **P-3** (chamada de P-5 na mensagem do responsável): o ambiente `producao` tem o revisor obrigatório `gustavohoff1987`,
  "Prevent self-review" e o bypass de administradores desativados, e só a regra de etiqueta `imagem-*`, sem regras de ramo.
  Tem as variáveis `GCP_PROVEDOR_DE_IDENTIDADE` e `GCP_CONTA_DE_ENVIO_DE_IMAGEM`, com os valores da F2-3, e nenhum segredo.
- **CI:** o último commit (`0818488`) passou nos 8 jobs (execução 41553222496).

**F2-4 (03/11/2026).** O papel `roles/secretmanager.secretAccessor` foi dado no segredo `gemini-api-key` só para
`adt-execucao` (novo etag `BwZfVPpit6g=`). Conferência:
- a política do segredo tem esse único vínculo;
- nenhuma conta nova tem papel no projeto;
- a versão 1 continua `enabled`;
- o valor do segredo não foi lido.

**F2-5, primeira tentativa (03/11/2026, "AUTORIZO F2-5").**
- **Etiqueta:** `imagem-20261103-1`, no `e2e64f4` (CI em PASS, execução 41558414040), acionou a execução 41561015736. O job
  `conferir-protecao` passou. O responsável aprovou o job `imagem` (P-5), que construiu a imagem e passou no teste rápido do
  contêiner.
- **Falha no passo da federação:** `unauthorized_client: The given credential is rejected by the attribute condition`. Nada
  foi enviado ao Artifact Registry.
- **Causa, conferida só em leitura:** o repositório usa o `sub` com identificadores imutáveis (`use_immutable_subject: true`,
  prefixo `repo:gustavohoff1987@322563090/Teste-Agente@1411794822`). O token chega com
  `repo:gustavohoff1987@322563090/Teste-Agente@1411794822:environment:producao`, e a condição e o vínculo da F2-3 esperavam
  `repo:gustavohoff1987/Teste-Agente:environment:producao`.
- **Correção proposta** (altera os recursos da F2-3): a condição passa a conferir os identificadores imutáveis do repositório
  e do dono, o ambiente e o `sub` novo; o vínculo `workloadIdentityUser` da conta de envio passa para o `sub` novo; o vínculo
  antigo sai. Depois, uma nova execução do job, com nova aprovação (P-5).

**Correção da federação (03/11/2026, "AUTORIZO F2-3").**
- **Provedor `teste-agente`:** ativo. A condição confere `assertion.repository_id == '1411794822'`,
  `assertion.repository_owner_id == '322563090'`, o ambiente `producao` e o `sub` `repo:gustavohoff1987@322563090/Teste-Agente@1411794822:environment:producao`. O mapeamento ganhou
  `attribute.repository_id`.
- **Conta `adt-envio-imagem`:** tem só o vínculo `workloadIdentityUser` com o `sub` novo; o antigo foi retirado. Nenhuma
  conta nova tem papel no projeto.
- **Roteiro:** a F2-3 foi atualizada com esse formato.

**F2-5 concluída (03/11/2026).**
- **Execução:** a mesma 41561015736 foi reexecutada (`gh run rerun --failed`) e aprovada pelo responsável (P-5). Todos os
  passos passaram: a construção, o teste rápido do contêiner, a federação e o envio.
- **Imagem:** `us-central1-docker.pkg.dev/agente-diagnostico-territorial/agente-diagnostico-territorial/servico-de-analise`,
  com o digest **`sha256:6988e2e9496c71b3caec50704d8710abe65d2aeb99f50fefb670d4a400b1a86e`** e a etiqueta
  `e2e64f4b78446e8116e60c52c992c7678a40717e`. O repositório tem 118,7 MB, dentro da franquia.
- **Commit `dfd2bf7`:** a mensagem dele anunciava esta conclusão, mas, por uma falha do agente na hora de gravar, ele só
  levou o registro da primeira tentativa. O conteúdo completo veio no commit seguinte.

**F2-6 (03/11/2026, "AUTORIZO F2-6").**
- **F2-0 de novo:** 0 falhas. Com as APIs ligadas, nenhum serviço, repositório, segredo, conta ou pool fora do previsto; a
  conta padrão do Compute aparece como OK; os itens MANUAL foram confirmados pela P-2.
- **Implantação:** revisão `agente-diagnostico-territorial-00001-48n`, com 100% do tráfego e as condições `Ready`,
  `ConfigurationsReady` e `RoutesReady` verdadeiras. Endereço: `https://agente-diagnostico-territorial-338451103854.us-central1.run.app`
  (também `https://agente-diagnostico-territorial-woz4embaja-uc.a.run.app`).
- **Configuração efetiva, conferida só em leitura:**
  - a imagem pelo digest `sha256:6988e2e9…1a86e`;
  - 1 vCPU e 2 GiB; mínimo 0 e máximo 1 instância; concorrência 40 e timeout de 150 s;
  - cobrança por requisição, sem aumento de CPU na partida, ambiente `gen2`;
  - a conta `adt-execucao`;
  - `ADT_ALLOWED_ORIGINS=https://gustavohoff1987.github.io`, `ADT_DOCUMENTACAO_DA_API=0` e `GEMINI_API_KEY` do segredo
    `gemini-api-key`, versão 1;
  - a sonda TCP na porta 8080 (24 × 10 s) e `ingress: all`.
- **Acesso:** a política de invocação não tem nenhum membro. Sem login, o serviço responde **403**.
- **Partida na nuvem** (Cloud Logging):
  - a instância começou às 23:03:07 UTC;
  - o aquecimento terminou em 13,6 s (base do Brasil 12,5 s, biblioteca conversacional 1,1 s), contra 8,5 s no runner;
  - a porta abriu às 23:03:27, cerca de 20 s depois do início, e a sonda passou na 2ª tentativa.
- **Teste pelo proxy autenticado: não feito.** O `gcloud run services proxy` precisa de um componente extra do gcloud, cuja
  instalação foi recusada no modo não interativo. O agente não instalou nada nem usou um token impresso pelo gcloud. A
  saúde por HTTP fica para a F2-8, depois do acesso liberado; a partida e a sonda estão comprovadas pelos registros.
- **Marcação:** a etiqueta `em-uso` está no digest implantado. Na primeira implantação não há `anterior`.

**F2-7 (03/11/2026, "AUTORIZO F2-7").**
- **Acesso:** a política de invocação tem só `roles/run.invoker` para `allUsers` (etag `BwZfZ8p30ew=`).
- **Saúde sem login:** HTTP 200 em 25,2 s, uma partida a frio, porque a instância tinha encerrado por ociosidade. A resposta
  foi `{"status":"ok","llm":false,"version":"0.1.0"}`. O campo `llm` é fixo no código (`main.health`) e não indica
  o estado do Gemini.
- **Gemini:** `/api/llm/status` mostra `configured: true`, `gemini-3.5-flash-lite`, `disponivel: true` e 0 chamadas no dia;
  a chave chegou pelo segredo. Nenhuma chamada ao provedor foi feita.

**F2-8 (03/11/2026, "AUTORIZO F2-8").** Só requisições à API pública, com a instância já ativa:
- **Saúde:** 200 em 0,25 s.
- **Documentação:** `/docs` e `/openapi.json` respondem 404, sem `curl -f`.
- **CORS:** sem `Access-Control-Allow-Origin` para uma origem estranha; com ele para `https://gustavohoff1987.github.io`.
  A pré-verificação responde 200, com os métodos GET e POST, os cabeçalhos com `Content-Type` e `X-ADT-Session` e a
  validade de 7.200 s.
- **Base do Brasil:** o exame responde 200 em 1,09 s, na versão `c4d82eeee4e4`, a governada pelo manifesto. O gráfico dos
  estados (densidade, 202406) responde 200 em 0,78 s, com 27 itens.
- **Envio pequeno:** um CSV sintético de 100.000 bytes, do gerador do CI e sem dados reais. O exame responde 200 em
  0,81 s; o gráfico de todos os territórios, 200 em 1,39 s, com 1.072 itens, o mesmo do CI.
- **Gemini:** 0 chamadas antes e depois.
- **Fora do teste:** o envio acima de 15 MB, coberto pelo CI, para não gastar dados móveis.

**P-6 (03/11/2026), feita pelo responsável e conferida só em leitura com o `gh`:**
- **Pages:** origem GitHub Actions (`build_type: workflow`), endereço `https://gustavohoff1987.github.io/Teste-Agente/`,
  HTTPS obrigatório. Nenhum workflow de modelo do Pages foi criado.
- **Ambiente `github-pages`:** revisor obrigatório `gustavohoff1987`, com "Prevent self-review" e o bypass de
  administradores desativados, e só a regra de etiqueta `publicacao-pages-*`, sem regras de ramo. Sem segredos nem
  variáveis.
- **Variável do repositório:** `VITE_API_BASE_URL=https://agente-diagnostico-territorial-338451103854.us-central1.run.app`,
  que passa na validação do `pages.yml`.
- **Conferência de proteção:** a função `conferir()` do `pages.yml`, rodada localmente com a API real e sem enviar
  etiqueta, confere para `publicacao-pages-20261103-1` no `4b701ed`. O CI desse commit está em PASS (execução
  41744759859).

**F2-9 (03/11/2026, "AUTORIZO F2-9").**
- **Etiqueta:** `publicacao-pages-20261103-1`, no `4b701ed`, acionou a execução 41751939348. Os jobs `conferir-protecao` e
  `build` passaram: `npm ci`, os testes, o build com `ADT_BASE_DA_PAGINA=/Teste-Agente/` e a conferência do padrão de chave.
  O responsável aprovou o job `publicar` (P-7) às 01:15 UTC, e ele terminou em sucesso.
- **Conferência só pela API:** `https://gustavohoff1987.github.io/Teste-Agente/` responde 200, com o título oficial; o
  script `assets/index-DOALu701.js` responde 200 e traz o endereço do serviço; a saúde do serviço responde 200.
- **Conferência no navegador (P-9):** do responsável.

**P-9 da F2-9 (03/11/2026), conferência do responsável no navegador:** a interface carregou pelo endereço público, a
seleção do Distrito Federal, os indicadores e o mapa de Brasília funcionaram. A conversa não foi usada nessa conferência.

**Conferência do agente nos registros do Cloud Run** (só leitura, as últimas 3 horas):
- todas as requisições da página responderam 200: o exame da base, 4 gráficos (`/api/painel`), a escolha de territórios,
  o mapa, a abertura, a renovação e o encerramento da sessão e as pré-verificações de CORS;
- 60 consultas da sessão, a cada 30 s, da aba aberta;
- nenhum erro 5xx. O único 403 e os dois 404 da janela são os testes esperados da F2-6 e da F2-8.
- Gemini: 0 chamadas no dia.

**F2-10 (03/11/2026, "AUTORIZO F2-10").**
- **Antes (01:59 UTC):** `/api/llm/status` com o Gemini configurado e disponível, e 0 chamadas no dia.
- **Na página publicada, o responsável** mandou as três mensagens: a pergunta sobre o resultado, a explicação mais simples e
  a pergunta conceitual. Ele informou que as respostas vieram normalmente.
- **Depois:** **5 chamadas** no dia, dentro do teto de 5, sem espera de cota.
- **Registros do Cloud Run** (só status e tempos, sem conteúdo): 6 `POST /api/llm/interpret-context`, entre 02:05:30 e
  02:08:22 UTC, todas com 200, de 1,07 a 2,75 s.
- **Última hora:** 212 respostas 200 e uma 410. A 410 foi às 01:48:38 UTC, antes do teste: a consulta de uma sessão
  aberta às 01:18:14 e parada havia 30 minutos. É a expiração prevista (a consulta periódica não renova o prazo), e a
  página abriu outra sessão. Nenhum 5xx.

Ponto de retomada: "AUTORIZO F2-11" (suspender o acesso, conferir a mensagem institucional e restaurar).

