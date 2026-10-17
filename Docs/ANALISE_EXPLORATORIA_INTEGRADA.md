# Investigação territorial progressiva

A investigação reúne as análises concluídas **somente na memória da aba e da sessão atual**.
“Ver investigação” abre uma sequência de etapas, com seis cartões por página. Cada etapa identifica
operação, período, categoria, recorte e situação informada pelo motor. “Ver contexto” expande os
detalhes; “Abrir etapa” consulta o resultado existente. O histórico anterior continua disponível.

O resultado selecionado conserva tabelas, mapas, gráficos, distribuições, séries, métricas,
notas e exportações já existentes. “Recolher análise” reduz sua apresentação sem eliminar o conteúdo.
A identidade da execução mostra fonte, indicadores e unidades, recorte, períodos, categoria,
versão, método, momento e parâmetros. Condições completas continuam no JSON e nas notas do motor.
Resultados limitados mantêm seus qualificadores; resultado sem linhas recebe mensagem específica.

## Seleção, filtro e execução

- Selecionar linhas, barras ou pontos destaca territórios dentro do resultado.
- Filtros da tabela, filtros visuais, seleção, indicador, aba, ordenação e páginas são lembrados
  por resultado ao navegar. A distribuição também conserva grupo e busca. O enquadramento manual
  do mapa volta à extensão inicial quando a representação é remontada.
- “Destacar seleção nesta análise” copia **somente identificadores territoriais**, por ação
  explícita. Exige mesma fonte e versão, hash dos dados, método, associação de campos, períodos,
  categorias, universo integral e condições de unidade/tratamento/agregação. Não usa semelhança
  de nomes; não faz interseções nem harmonização. Agregados, coortes e séries de várias competências
  permanecem independentes. Camadas geográficas declaradas diferentes bloqueiam o destaque.
- Dimensões diferentes podem receber o mesmo destaque quando essa identidade é comprovada.
  A tela informa diferenças de operação, indicador/unidade e parâmetros. **Destaque compatível
  não certifica comparabilidade de valores**, não transfere quintis, não produz relações e não
  soma resultados. Relações analíticas continuam exclusivamente nas operações existentes.
- “Usar seleção na próxima análise” leva identificadores à preparação. Comparações e agregações
  continuam exigindo suas confirmações e uma execução explícita. Alterar parâmetros não recalcula
  nem modifica resultados anteriores. Abrir uma etapa não restaura parâmetros silenciosamente.

## Conversa, disponibilidade e privacidade

A conversa recebe o identificador do resultado em exibição pelo contrato já existente. O servidor
resolve a referência na sessão de origem e verifica integridade e contexto. Valores, nomes de
campos, registros e visualizações não são enviados ao Gemini como fonte de verdade. A seleção
visual permanece distinta da seleção analítica; só a ação explícita de reutilização muda a preparação.

O limite existente do servidor continua em 64 referências ou 32 MiB por sessão, com teto global
de 256 MiB e 128 sessões. Quando o cálculo não cabe nesse registro, permanece consultável e
exportável na aba e a tela informa que sua referência conversacional está indisponível.
Não há banco novo, login, salvamento permanente, descarte automático de análises anteriores
para abrir espaço nem alteração do prazo de 1.800 segundos sem interação efetiva.

Recarregar a página descarta a investigação local. Encerrar, expirar ou perder a sessão no servidor
descarta o conteúdo conforme o mecanismo já existente. Exporte o que precisa conservar.

## Arquitetura e validação

`InvestigationOverview` compõe cartões leves e identidade; `investigation.ts` decide somente a
possibilidade de destaque; `InvestigationViewState` guarda controles, sem copiar linhas analíticas.
`App` mantém o histórico e uma única representação detalhada montada. `ResultWorkspace`,
`ResultTable`, `DistributionResults`, `CriteriaResults` e `TerritoryMap` continuam responsáveis
pelas visualizações. Não há dependência nova nem mudança de motor ou API.

Testes: `npm test` em `frontend/` valida a política real de compatibilidade; `ui_investigation.py`
é registrado no executor para catálogo sintético e base versionada. As jornadas anteriores e
os testes de backend continuam cobrindo métodos, limites, privacidade, sessão e exportações.
