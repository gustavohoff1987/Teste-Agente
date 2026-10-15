# Microiteração — distribuição territorial e clareza da interface

Data: 15/10/2026. Branch existente: `feat/novos-blocos-incrementais`. Escopo: refinamento incremental de interface, distribuição e posições. Sem nova branch e sem merge na `main`.

## Decisões

- A mensagem de dados preparados na conversa ficou objetiva: “Os dados já estão preparados para a análise solicitada”.
- Distribuição mantém **uma competência por análise**; a comparação de períodos permanece em Evolução temporal. Nenhuma soma implícita entre competências.
- A escolha de agrupamento oferece **quartis (4), quintis (5) e decis (10)**, valores já admitidos pelo motor. O padrão permanece em cinco.
- A tabela de distribuição abre ordenada por posição geral crescente: grupos inferiores antes dos superiores. Busca e filtros aplicam-se imediatamente. A exportação de territórios usa a ordem exibida e exporta todo o filtro.
- O backend emite `Posição geral` e `Posição no quartil/quintil/decil` (ou `Posição na faixa` para os demais valores admitidos pela API), para cada universo período/categoria. Empates recebem a mesma menor posição (1, 1, 3); classificação existente, cortes e cálculos de indicadores não foram modificados.
- Na primeira análise de distribuição, o painel de histórico com uma única entrada não aparece; com vários resultados continua acessível. A situação técnica “válido/vigente” não fica exposta no resultado atual de distribuição; o histórico e as regras de invalidação seguem intactos.
  - **Superado no mesmo dia pelo commit `dbaa0bd`:** o painel "Histórico de resultados" e o controle de invalidação foram retirados da interface em todas as análises. O histórico interno da sessão permanece (reaproveitamento, retomada e competências calculadas). Detalhes em [`REGISTRO_DE_COMPORTAMENTO.md`](REGISTRO_DE_COMPORTAMENTO.md).
- O bloco “Método e limitações” exibe uma explicação acessível na distribuição, mantendo as notas técnicas originais em um controle expansível. A exportação JSON preserva notas e metadados originais.

## Limites e preservação

Não foram modificados os arquivos de dados brasileiros, a camada geográfica, distâncias geodésicas, o método de quantis Hyndman–Fan tipo 7, os critérios científicos de seleção nem a SPEC. As novas posições são derivados determinísticos do indicador sem arredondamento intermediário, nunca posições inventadas no frontend.

A apresentação com agrupamentos diferentes mantém o contrato de campo `Quintil` nas respostas JSON por compatibilidade com consumidores existentes; o conteúdo do campo indica corretamente “quartil”, “quintil” ou “decil”. A UI usa a denominação correta.

## Validação

Testes acrescentados em `backend/tests/test_representation.py` verificam 4, 5 e 10 grupos, integridade das contagens, colunas de posição e empate. A compilação do frontend e a regressão automatizada devem ser verificadas no CI da branch. Registrar qualquer falha encontrada; não confundir ausência de falhas no CI com equivalência integral do estudo científico.
