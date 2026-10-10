# Base lógica Brasil — integração e validação em 10/10/2026

Implementação na branch `feat/portal-uma-pagina-v1`, exclusivamente no Teste-Agente.
As fontes são lidas sem alteração. Os dados residentes e as evidências de navegador
ficam em `.local/`, ignorada pelo Git; não houve publicação dos arquivos.

## Alterações dos campos e consumidores

| Estrutura anterior nos testes | Estrutura atual | Ajuste |
| --- | --- | --- |
| `Período` / `Competência` | `periodo_ano` + `periodo_mes` | Composição determinística AAAAMM em memória, com confirmação e linhagem |
| `ibge` | `cod_ibge` | Novo alias de código territorial; confirmação mantida |
| `categoria_profisional` | `categoria_profissional` | Alias correto já era suportado; testes atualizados, alias antigo preservado |
| `Contagem` / `Total de médicos únicos` | `quantidade` / `contagem` | Aliases existentes; unidade continua declarada pelo usuário |
| Nacional sem geografia/categoria explícitas | `pais`, `categoria_profissional` | Reconhecimento de país e uso da categoria da própria base |
| Coordenadas com vírgula | `latitude`, `longitude` | Formato já suportado mediante declaração; validação de intervalos mantida |

O leitor comum atende inspeção, pré-exame, cálculo e contexto conversacional.
`dataset_normalization.py` mantém os campos originais; `semantic_bridge.py` oferece
o campo derivado como proposta, não como confirmação. O motor mantém seus cálculos.
Filtros, multiplicidade e séries usam o mesmo período composto. Os metadados de
exportação registram a regra, os campos de origem, o recorte e a versão lógica.

## Uma base lógica, sem misturar granularidades

O catálogo `brazil_data.py` administra duas fontes privadas. A interface mostra
somente Dados do Brasil e a abrangência analítica. O padrão é nacional para contagens,
evolução temporal e relatórios; municipal para as outras operações. O usuário pode
escolher a abrangência explicitamente. Trocar de recorte exige novas confirmações.

Não há união, preenchimento ou soma entre fontes. Quantitativos nacionais são lidos
da fonte nacional; não são obtidos pela soma das contagens municipais. A agregação
municipal conserva as exigências de aditividade e o rótulo de possível dupla contagem.
Selecionar um recorte sem os requisitos necessários mantém a análise bloqueada.

O catálogo compartilha as rotas existentes com uploads. A requisição usa `dataset=brazil`,
`scope=national|municipal|auto` e a versão retornada por `/api/inspect`. Nenhum caminho
de arquivo é aceito do navegador. Fonte residente e upload são mutuamente exclusivos.
Ambos os hashes são verificados; uma fonte ausente ou alterada impede usar o catálogo.
A conversa recebe somente os estados técnicos já previstos, nunca linhas ou arquivos.

## Qualidade dos dados e aplicabilidade

Foram encontrados 22 períodos (janeiro e junho de 2014 a 2024), 22 linhas nacionais e
122.534 municipais. Os códigos distinguem 5.570 municípios; nomes isolados geram
11.528 registros em 5.324 grupos com mais de uma linha. Confirmar o código elimina
essa ambiguidade sem somar municípios homônimos.

| Capacidade | Validação nas fontes atuais |
| --- | --- |
| Quantitativos | Nacional e municipal, preservando as contagens de cada fonte |
| Densidade | Municipal, quantidade / população × 1.000 |
| Distribuição | Quantidade e densidade, período único, quintis e empates conferidos |
| Comparações e rankings | Densidades e posições conferidas por período/categoria |
| Evolução temporal | Quantidade nacional; quantidade e densidade municipais; extremos ausentes e zeros respeitados |
| Agregação | Apenas soma explicitamente autorizada; resultado não identificado como total nacional de pessoas únicas |
| Espacial | Base completa bloqueada por coordenadas inválidas; cálculo confrontado com Haversine em subconjunto de teste válido |
| Rotatividade | Bloqueada corretamente: ausência de identificadores individuais longitudinais |
| Relatórios | Dados e densidades municipais, quantitativos nacionais e exportação CSV |

Há seis municípios com coordenadas fora dos intervalos válidos em cada período,
totalizando 132 linhas: ANANAS (170100), PESCARIA BRAVA (421265), BALNEARIO RINCAO
(422000), JARAGUARI (500490), CAMPESTRE DA SERRA (430367) e AGUAS DE LINDOIA (350050).
Exemplo: latitude `-63741`. Não é possível determinar a correção apenas pelo valor.
Também há coordenadas que variam ao longo do tempo. Não se corrigiram ou excluíram
linhas no aplicativo. O subconjunto válido existe somente no teste de distância.

## Reproduzir a validação

### Resultados executados

| Verificação | Resultado |
| --- | --- |
| Suíte geral do backend | 105 passaram; 20 testes reais omitidos nessa execução por serem opt-in |
| Suíte com as duas fontes reais | 20 passaram, com comparações independentes e preservação dos hashes |
| Build do frontend (TypeScript + Vite) | Passou |
| Navegador: sessão e upload sintético | Passou; privacidade, teclado, densidade, CSV, conversa simulada e recuperação |
| Navegador: carrossel | Passou; dez análises, teclado, roda, gestos, seleção sem execução e responsividade |
| Navegador: catálogo Brasil | Passou; 22 linhas nacionais exportadas, 5.570 municípios no filtro, troca de recorte e retorno ao upload internacional |
| Navegador: upload municipal real | Passou; 122.534 linhas exportadas conferidas com Decimal, filtros, metadados, falha simulada de pré-exame e tela de 390 px |
| Integridade e Git | Originais e cópias com hashes idênticos; dados privados ignorados, nenhum CSV/XLS/XLSX rastreado pelo Git |

Os quatro fluxos de navegador terminaram sem erros JavaScript. No upload municipal,
o maior desvio absoluto na densidade exportada foi `5,91025063785 × 10⁻¹⁵`.
As evidências completas e capturas ficam somente em `.local/ui-validation/`.

O teste de atualização dos filtros identificou um botão habilitado durante o
pré-exame: o motor já recusava executar nesse intervalo. O botão de atualizar
resultados agora também fica desabilitado até a revalidação terminar; o teste
foi repetido e passou. Os cálculos analíticos não foram alterados.

Avisos não impeditivos: depreciação de httpx no cliente de testes Starlette, restrição
de escrita do cache pytest no sandbox e bundle Vite acima de 500 kB. A compilação e
os testes concluíram com sucesso. As chamadas ao provedor de IA foram simuladas;
esta validação não comprova disponibilidade ou quota do serviço externo.

### Comandos

```powershell
py -m pytest -q
$env:ADT_REAL_DATA_DIR = 'C:\Users\User\Desktop\Dados_Brasil'
py -m pytest -q backend/tests/test_real_data.py
cd frontend
npm.cmd run build
```

Com backend e Vite ativos, na raiz:

```powershell
python backend/tests/ui_session_smoke.py
python backend/tests/ui_carousel_smoke.py
python backend/tests/ui_brazil_smoke.py
python backend/tests/ui_smoke.py
```

Os testes gerais usam fontes sintéticas e não precisam do catálogo real. Os testes
reais são opt-in e comparam os hashes dos originais antes e depois. O teste de upload
municipal confere o CSV exportado com Decimal, linha por linha. O teste do catálogo
confere exportação nacional, densidade municipal, troca de recorte, descarte de
confirmações, conversa simulada e retorno ao upload internacional. Não há chamadas
reais ao provedor de IA nos testes.

Para a futura operação online, será necessário disponibilizar as fontes autorizadas
ao backend e configurar o diretório ou adaptar o carregador isolado, preservando
versões, integridade e granularidades. Não existe caminho fixo para a Área de Trabalho
no carregador. Esta etapa não escolhe nem implementa hospedagem, Docker, armazenamento
em nuvem ou publicação; essas decisões não são necessárias à implementação local.
