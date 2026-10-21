# Latência do Gemini — 21/10/2026

## Resultado e mudança aplicada

O backend estava configurado com uma chave aceita pela API e com o modelo `gemini-3.5-flash-lite`.
No diagnóstico inicial, a chamada real falhou com `httpx.ReadTimeout` após 22,74 s; o cliente usava
`timeout=22.0`. Uma chamada seguinte, com espera de até 60 s apenas no diagnóstico, concluiu com
HTTP 200 em 47,27 s. Essas chamadas diretas não incluíram o bloco de exemplos: usaram `_call_gemini`
sem preencher `_EXAMPLES`. Portanto, a demora já ocorreu sem exemplos da biblioteca.

Por pedido do responsável, o cliente passa a usar **75 s** e a distinguir tempo limite de outros
erros de transporte. Ambos conservam HTTP 503. Os erros HTTP efetivamente recebidos do provedor
continuam no tratamento anterior: 429 para cota, 503 para autorização e 502 para outros status,
com o status do provedor na mensagem. Um HTTP 503 do Google não é `ReadTimeout` local.

O [HTTPX aplica o timeout por operação](https://www.python-httpx.org/advanced/timeouts/): conexão,
leitura de um trecho, escrita e espera por conexão. Não se trata de um cronômetro global de 75 s
para todo o pedido, nem do prazo da sessão. A interface usa `fetch` sem prazo adicional nesse caminho
e exibe o `detail` da API. O proxy Vite não configura um prazo próprio.

## Como foi feita a comparação

Medição manual solicitada pelo responsável, iniciada em **21/10/2026 às 12:18:26 (UTC−03:00)**,
em Windows, Python 3.12 e HTTPX 0.28.1. Não foi executada suíte de testes local.

- Frase sintética fixa: "Quero comparar a quantidade de profissionais entre dois períodos."
- Nenhuma base, arquivo, sessão, campo ou valor dos dados do Brasil foi carregado ou enviado.
- Mesmo modelo, regras de sistema, esquema de resposta, temperatura 0, máximo de 600 tokens de saída
  e timeout 75 s nas seis chamadas, sem novas tentativas automáticas.
- Três pares sequenciais, alternando a ordem: sem/com, com/sem, sem/com. Cada chamada cria seu cliente
  HTTP, como o produto. Somente a presença do bloco de exemplos varia no pedido.
- Recuperação e máscara pelo `_library_examples` real, sem base nem continuidade: biblioteca
  `fde96d0ef453`, limite padrão de cinco exemplos, ids `J-0256#2`, `A-0124#2`, `C-0129#1`, `J-0154#1`,
  `A-0113#1`; bloco de 2.119 caracteres. Os exemplos continuam habilitados no produto.
- Medidas monotônicas locais e eventos de transporte; somente durações, contagens, ids da biblioteca,
  status HTTP e motivos de término foram registrados. Chaves e corpos de respostas não foram gravados.
- As chamadas passam pelo contador local de 20 solicitações por processo, em um processo de diagnóstico
  separado. Não alteram o contador do servidor já aberto.

## Preparação local e tamanho do pedido

| Medida | Resultado |
|---|---:|
| Primeira carga do índice + seleção + máscara | 830,82 ms |
| Seleção + máscara com índice carregado, mediana de 30 execuções | 4,89 ms |
| Maior tempo dessas 30 execuções | 7,30 ms |
| Corpo UTF-8 sem exemplos / com exemplos | 4.892 / 7.268 bytes |
| Tokens de entrada informados pelo Gemini, sem / com exemplos | 708 / 1.254 |
| Acréscimo de tokens pelos cinco exemplos | 546 (+77,1%) |

A carga é única por processo e acontece antes da chamada HTTP. Mesmo a primeira carga medida não
explica a espera de dezenas de segundos observada anteriormente. O custo dos exemplos inclui tanto
a recuperação local quanto o maior pedido enviado ao modelo. A medição sem base não estima o custo
da minimização de valores de uma base carregada nem do pré-exame contextual.

## Chamadas remotas

| Par / ordem | Biblioteca | HTTP | Total da chamada | Espera pelos cabeçalhos | Tokens de entrada / saída |
|---|---|---:|---:|---:|---:|
| 1 / 1 | sem | 200 | 10,04 s | 9,22 s | 708 / 62 |
| 1 / 2 | com cinco exemplos | 503 | 1,02 s | 0,43 s | não informados |
| 2 / 1 | com cinco exemplos | 200 | 8,52 s | 7,93 s | 1.254 / 82 |
| 2 / 2 | sem | 200 | 12,93 s | 12,36 s | 708 / 62 |
| 3 / 1 | sem | 200 | 7,54 s | 6,96 s | 708 / 86 |
| 3 / 2 | com cinco exemplos | 200 | 9,16 s | 8,56 s | 1.254 / 41 |

As cinco respostas bem-sucedidas terminaram com `STOP`. TCP + TLS levou aproximadamente 0,17–0,21 s
nessas chamadas; envio do corpo, menos de 1 ms; leitura do corpo, menos de 3 ms. A espera pelos
cabeçalhos concentrou a maior parte do tempo. Ela inclui o tempo remoto e a rede e não separa fila,
processamento interno do modelo ou causas dentro da infraestrutura do provedor.

Entre os sucessos, a mediana sem exemplos foi 10,04 s (n=3) e com exemplos 8,84 s (n=2).
O HTTP 503 não entra nessa comparação como se fosse uma resposta rápida válida. Nos dois pares
completos, adicionar exemplos coincidiu com −4,41 s em um e +1,62 s no outro. A amostra pequena,
o erro remoto, a variação da saída e possíveis efeitos de ordem/cache impedem concluir que a
biblioteca acelera, atrasa de forma consistente ou não tem impacto. O aumento do volume de entrada
foi observado; sua contribuição causal para a latência não foi isolada.

O [guia oficial do Gemini](https://ai.google.dev/gemini-api/docs/troubleshooting) descreve erros
transitórios e possível aumento de latência por raciocínio. Estas respostas não informaram
`thoughtsTokenCount` nem `cachedContentTokenCount`; a ausência desses campos não comprova ausência
de raciocínio ou cache. Não há evidência nesta medição para atribuir a demora a esses mecanismos.

## Decisões e reprodução

Aplicados o timeout solicitado e a distinção das mensagens. Não há base empírica suficiente para
reduzir/desligar os exemplos, mudar o modelo ou alterar seus parâmetros. A integração continua sem
retry automático. Se a lentidão persistir, uma amostra maior, com várias mensagens e horários, deve
comparar latência e qualidade de interpretação conjuntamente antes de reduzir exemplos. Aumentar o
timeout evita interrupções prematuras, mas não torna a resposta do provedor mais rápida.

Ferramenta manual: `scripts/diagnosticar_latencia_gemini.py`. Quando houver pedido explícito de nova
medição, execute na raiz com `GEMINI_API_KEY` disponível no ambiente ou no `backend/.env`:

```powershell
$env:PYTHONUTF8 = '1'
python scripts/diagnosticar_latencia_gemini.py
```

O script faz até seis chamadas reais, pode consumir a cota do provedor, não lê a base e não é chamado
pelo CI. Interrompe se a credencial for recusada ou a cota se esgotar. A biblioteca precisa estar
habilitada; sua configuração persistente não é modificada.

Os testes automáticos usam transporte simulado e rodam somente no GitHub Actions: timeout exato de
75 s, distinção entre as quatro subclasses de timeout e outros erros, mensagem da API sem detalhes
privados, uma tentativa, restauração do contexto dos exemplos, saúde do backend e erros HTTP do
provedor. O teste que exigia até 30 s foi atualizado por incompatibilidade com o novo requisito;
nenhuma cobertura foi removida. A governança e a compilação dos Python alterados são as checagens
locais permitidas pelo `AGENTS.md`.
