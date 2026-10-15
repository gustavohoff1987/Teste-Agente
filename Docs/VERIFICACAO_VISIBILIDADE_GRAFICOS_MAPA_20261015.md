# Verificação dirigida da visibilidade de gráficos e mapas — 15/10/2026

Escopo: auditoria funcional em `feat/novos-blocos-incrementais`, sem alteração de algoritmo, arquivos de dados ou componentes de produção. Não confundir código implementado com acessibilidade imediata no fluxo padrão.

## Achados de inspeção estática (pré-teste)

1. O componente `ResultWorkspace.tsx` implementa abas Mapa, Gráficos e Tabela, com apenas uma visualização principal de cada vez.
2. O gráfico de barras por território é ocultado quando o resultado tem mais de 40 territórios e o usuário não selecionou nenhum. Surge após seleção explícita, até 40 barras.
3. O gráfico de contagem por quintil pertence a `DistributionResults.tsx`, abaixo do painel principal e **fora** da aba Gráficos. `countBars()` do painel principal não agrega a distribuição.
4. O mapa de pontos foi implementado e é exercitado por `ui_map_smoke.py`, com testes de seleção, zoom, cores, indicadores e PNG.
5. O mapa exige coordenadas, competência única, papéis de latitude/longitude reconhecidos e CRS explicitamente informado. No modo Brasil, o CRS é iniciado vazio; a preparação de Densidade/Distribuição não solicita CRS. O usuário precisa abrir Mapa, declarar CRS e separador decimal e executar novamente.
6. `CI #212` passou em backend, frontend, ui-conversational e ui-block1, incluindo `ui_map_smoke.py`. Isso confirma a implementação no cenário de teste já existente, mas não a experiência inicial com muitos municípios.

## Verificação E2E dirigida

Arquivo `backend/tests/ui_visibility_diagnostic.py`, acoplado ao job `ui-block1` da CI: dados sintéticos com 60 territórios e duas competências. Ele verifica:
- Densidade com 60 territórios: aba Gráficos aberta, nenhuma barra territorial inicial; barra após seleção na tabela.
- Mapa inicialmente indisponível por falta de CRS; disponível após declaração explícita e nova execução.
- Distribuição em cinco classes: gráfico de frequências existente fora da aba Gráficos, enquanto barras territoriais não aparecem sem seleção.
- Integridade dos valores de retorno e erros de página.

Capturas e relatório local em `.local/ui-validation/diagnostico_visibilidade*`. O relatório do teste é diagnóstico; **não corrige** os pontos levantados. Status final deverá ser confrontado com a execução do GitHub Actions para o commit da verificação.

## Recomendações para decisão futura (sem execução)

- Dar visibilidade explícita ao acesso a Mapa/Gráficos/Tabela e oferecer mensagens claras quando os requisitos de geometria não estiverem preenchidos.
- Para densidade com muitos territórios, considerar gráfico agregado pertinente ou seleção guiada, **sem seleção territorial arbitrária ou inferência estatística não autorizada**.
- Integrar o gráfico de frequências de quartis/quintis/decis na aba Gráficos ou fornecer navegação direta inequívoca; preservar os resultados já calculados pelo motor.
- Oferecer confirmação simples de CRS no preparo de densidade/distribuição quando haja coordenadas, sem presumir origem geodésica de uploads externos.
- Cobrir também o caso com base brasileira real de 5.570 municípios em teste local autorizado; a fixture sintética de CI reproduz a condição `>40`, mas não certifica desempenho e experiência específicos da base integral.
