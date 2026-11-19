import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
// Simulador de Cenários Territoriais (comando V22, etapa 4): o modelo puro da tela (simuladorModel.ts) — a seleção local (cópia da
// seleção principal, editável só no Simulador), a configuração dos cenários, o pedido a POST /api/simulador (com a persistência
// como referência), a leitura da resposta, os textos da tabela e as exportações (JSON do cenário e CSV dos resultados). Da etapa 5:
// o Brasil na seleção local, as referências de comparação e a métrica, o planejamento inverso, a hipótese derivada da simulação,
// o CSV das comparações e a configuração com que o Detector abre o Simulador. Nada é projetado na tela: os valores vêm do motor.
// Da Proposta V3 (comando V23, Parte C): o modo simples numa tela só (o território, o que testar e até quando), com um território
// só no pedido; o jeito de projetar escolhido pela base; a faixa "N em cada 10" (conferida, provisória ou indisponível, com o
// motivo); os "Entenda"; os três números; as competências de qualquer base; e os nomes da base nos textos (não só "médicos").
const S = await source('simuladorModel');
const ler = caminho => readFileSync(new URL('../src/' + caminho, import.meta.url), 'utf8');
const COMPETENCIAS = Array.from({length: 22}, (_, k) => String(2014 + Math.floor(k / 2)) + (k % 2 ? '06' : '01'));
const cenario = (extra = {}) => ({...S.novoCenario('c1', 'Cenário 1'), ...extra});
const CHEIO = {
  local: {municipios: ['code:130420', 'code:130260'], estados: ['15'], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 2}]},
  janela: {inicio: '201906', fim: '202406'}, horizonte: '202812', modo: 'avancado', cenarios: [
    cenario({nome: 'Com reforço', metodo: 'manual', taxaManual: '1,5', janela: {inicio: '202106', fim: '202406'}, intervencoes: [
      {tipo: 'acrescimo', quantidade: '2,5', em: '202501', periodica: true, ate: '202701', aCadaMeses: '6', permanencia: '90'},
      {tipo: 'retirada', quantidade: '1', em: '202601', periodica: false, ate: '202601', aCadaMeses: '12', permanencia: '100'}]}),
    {...S.novoCenario('c2', 'Só a persistência'), metodo: 'M0'}]};

test('datas: competências reais, qualquer mês como data final e a janela padrão de 3 anos', () => {
  assert.deepEqual([S.competenciaCurta('202406'), S.competenciaCurta('202501'), S.competenciaCurta(null), S.competenciaCurta('x')], ['jun/2024', 'jan/2025', '', 'x']);
  // Numa base com um registro por ano ("AAAA00", Proposta V3: qualquer base), a data curta é só o ano.
  assert.deepEqual(['202300', '199900', '202400'].map(S.competenciaCurta), ['2023', '1999', '2024']);
  assert.equal(S.dataDoMes(S.mesDe('202406')), '202406');
  assert.equal(S.mesDe('202406') - S.mesDe('202401'), 5, 'de janeiro a junho são 5 meses');
  assert.equal(S.mesDe('202501') - S.mesDe('202406'), 7, 'de junho a janeiro são 7 meses');
  assert.deepEqual([S.anosDepois('202406', 2), S.anosDepois('202401', 10), S.dataDoMes(S.mesDe('202412') + 1)], ['202606', '203401', '202501']);
  assert.deepEqual([S.paraCampoDeMes('202806'), S.paraCampoDeMes(''), S.doCampoDeMes('2028-06'), S.doCampoDeMes('2028')], ['2028-06', '', '202806', '']);
  assert.deepEqual(S.janelaPadrao(COMPETENCIAS), {inicio: '202106', fim: '202406'}, 'os 7 registros até o último');
  // A distância entre o último registro e hoje, em palavras.
  assert.deepEqual([new Date(2026, 10, 10), new Date(2025, 5, 30), new Date(2024, 6, 1), new Date(2024, 5, 15), new Date(2020, 0, 1)].map(hoje => S.tempoDesde('202406', hoje)),
    ['2 anos e 5 meses', '1 ano', '1 mês', '0 meses', '0 meses']);
  assert.equal(S.janelaPadrao(['202401']), null);
  assert.deepEqual(S.janelaPadrao(['202401', '202406']), {inicio: '202401', fim: '202406'});
});

test('a seleção local é uma cópia da principal: municípios um a um, estados como unidade e conjuntos com a versão', () => {
  const c = {todasAsUnidades: ['code:110001', 'code:120001', 'code:130260'], unidadesDoGrupo: g => g === '13' ? ['code:130260', 'code:130420'] : []};
  assert.deepEqual(S.copiarSelecao(null, c), {municipios: [], estados: [], conjuntos: []});
  assert.deepEqual(S.copiarSelecao({base: {municipios: {todos: true, estados: [], ids: []}}}, c).municipios, ['code:110001', 'code:120001', 'code:130260']);
  const principal = {base: {municipios: {todos: false, estados: ['13'], ids: ['code:150140', 'code:130260']}}, estados_unidade: ['35', '12'],
    conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 3, substitui: true}]};
  const copia = S.copiarSelecao(principal, c);
  assert.deepEqual(copia, {municipios: ['code:130260', 'code:130420', 'code:150140'], estados: ['12', '35'],
    conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 3}]});
  assert.notEqual(copia.conjuntos[0].membros, principal.conjuntos[0].membros, 'mudar a cópia não toca na seleção principal');
  assert.equal(S.totalDaSelecaoLocal(copia), 6);
  assert.deepEqual(S.selecaoLocalParaOPedido(copia), {base: {municipios: {todos: false, estados: [], ids: ['code:130260', 'code:130420', 'code:150140']}},
    estados_unidade: ['12', '35'], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 3}]});
  assert.deepEqual(S.selecaoLocalParaOPedido(S.SELECAO_LOCAL_VAZIA), {});
});

test('acrescentar e tirar territórios só no Simulador, sem somar o estado inteiro aos municípios dele', () => {
  const local = {municipios: ['code:130260'], estados: ['35'], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002']},
    {id: 'g2', rotulo: 'Sul', membros: ['uf:41', 'uf:42']}]};
  const tentar = (tipo, id, grupo) => S.acrescentarTerritorio(local, {tipo, id, grupo});
  assert.equal(tentar('municipio', 'code:130260', '13').motivo, 'Este território já está na seleção do Simulador.');
  assert.equal(tentar('municipio', 'code:355030', '35').motivo, 'O estado deste município está na seleção como unidade: tire o estado para usar o município.');
  assert.equal(tentar('municipio', 'code:410690', '41').motivo, 'O estado deste município está no conjunto Sul: tire o conjunto para usar o município.');
  assert.equal(tentar('estado', '35', '35').motivo, 'Este estado já está na seleção do Simulador.');
  assert.equal(tentar('estado', '11', '11').motivo, 'O conjunto Par tem municípios neste estado: tire o conjunto para usar o estado como unidade.');
  for (const recusado of [tentar('municipio', 'code:130260', '13'), tentar('estado', '11', '11')]) assert.equal(recusado.local, local, 'recusado: nada muda');
  const novo = tentar('municipio', 'code:130420', '13');
  assert.equal(novo.motivo, null);
  assert.deepEqual(novo.local.municipios, ['code:130260', 'code:130420']);
  assert.deepEqual(local.municipios, ['code:130260'], 'a seleção de antes não é alterada');
  // O estado como unidade tira os municípios dele da seleção local (o estado inteiro já os conta).
  const comOEstado = tentar('estado', '13', '13');
  assert.deepEqual([comOEstado.motivo, comOEstado.local.municipios, comOEstado.local.estados], [null, [], ['13', '35']]);
  assert.deepEqual(S.tirarTerritorio(local, 'code:130260').municipios, []);
  assert.deepEqual(S.tirarTerritorio(local, 'uf:35').estados, []);
  assert.deepEqual(S.tirarTerritorio(local, 'g2').conjuntos.map(item => item.id), ['g1']);
});

test('o que falta para calcular, em palavras', () => {
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  assert.deepEqual(inicial, {local: {municipios: ['code:130260'], estados: [], conjuntos: []}, janela: null, horizonte: '202606', modo: 'simples',
    cenarios: [{id: 'c1', nome: 'Cenário 1', metodo: 'padrao', taxaManual: '', janela: null, intervencoes: []}], acompanha: true},
    'a cópia acompanha a seleção principal até ser alterada no Simulador');
  assert.equal(S.pendenciaDoPedido(inicial), null);
  assert.equal(S.pendenciaDoPedido({...inicial, local: S.SELECAO_LOCAL_VAZIA}), 'Escolha pelo menos um território para o Simulador.');
  const muitos = {municipios: Array.from({length: 101}, (_, k) => 'code:' + (110000 + k)), estados: [], conjuntos: []};
  // O limite de 100 territórios vale no modo avançado, que compara todos. No modo simples (V3), o pedido leva um território só: a
  // seleção local pode ser maior, e nada fica pendente por isso.
  assert.equal(S.pendenciaDoPedido({...inicial, modo: 'avancado', local: muitos}), 'O Simulador compara até 100 territórios de cada vez; a seleção local tem 101.');
  assert.equal(S.pendenciaDoPedido({...inicial, local: muitos}), null);
  assert.deepEqual(S.pedidoDoSimulador({...inicial, local: muitos}).base, {municipios: {todos: false, estados: [], ids: ['code:110000']}});
  assert.equal(S.pendenciaDoPedido({...inicial, horizonte: ''}), 'Escolha a data final do cenário.');
  // A taxa é da pessoa: sem ela, o cenário manual não é pedido (o sistema não sugere uma).
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({metodo: 'manual'})]}), 'Informe a taxa anual do cenário “Cenário 1”.');
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({metodo: 'manual', taxaManual: '2,5'})]}), null);
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({intervencoes: [{...S.novaIntervencao('202506'), quantidade: '0'}]})]}),
    'Informe quantos entram ou saem em cada intervenção.');   // sem "médicos": o texto vale para qualquer base (V3)
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({intervencoes: [{...S.novaIntervencao(''), quantidade: '2'}]})]}), 'Informe a data de cada intervenção.');
  // O calendário é do modo avançado: lá, a data final vem depois da inicial; no modo simples, ele não vai no pedido e não impede o cálculo.
  const comCalendario = {...inicial, cenarios: [cenario({intervencoes: [{...S.novaIntervencao('202506'), periodica: true, ate: '202501'}]})]};
  assert.equal(S.pendenciaDoPedido({...comCalendario, modo: 'avancado'}), 'Numa intervenção periódica, a data final vem depois da inicial.');
  assert.equal(S.pendenciaDoPedido(comCalendario), null);
  // No modo simples, só o primeiro cenário vale.
  const dois = [cenario(), {...S.novoCenario('c2', 'B'), metodo: 'manual'}];
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: dois}), null);
  assert.equal(S.pendenciaDoPedido({...inicial, modo: 'avancado', cenarios: dois}), 'Informe a taxa anual do cenário “B”.');
  assert.deepEqual(S.novaIntervencao('202506'), {tipo: 'acrescimo', quantidade: '1', em: '202506', periodica: false, ate: '202506', aCadaMeses: '12', permanencia: '100'},
    'a permanência total (100% ao ano) é a hipótese padrão');
});

test('o pedido ao motor: a seleção local, os cenários em uso e a persistência como referência', () => {
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  assert.deepEqual(S.pedidoDoSimulador(inicial), {base: {municipios: {todos: false, estados: [], ids: ['code:130260']}}, horizonte: '202606',
    cenarios: [{id: 'c1', nome: 'Cenário 1', metodo: 'padrao'}, {id: 'm0', nome: 'Persistência (referência)', metodo: 'M0'}]});
  // Modo avançado: a janela de cada cenário, as intervenções (os números digitados com vírgula) e a permanência só quando não é
  // total; o cenário que já é a persistência sem intervenção dispensa a referência.
  assert.deepEqual(S.pedidoDoSimulador(CHEIO), {
    base: {municipios: {todos: false, estados: [], ids: ['code:130260', 'code:130420']}}, estados_unidade: ['15'],
    conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 2}],
    janela: {inicio: '201906', fim: '202406'}, horizonte: '202812',
    cenarios: [{id: 'c1', nome: 'Com reforço', metodo: 'manual', taxa_manual_pct: 1.5, janela: {inicio: '202106', fim: '202406'},
      intervencoes: [{tipo: 'acrescimo', quantidade: 2.5, em: '202501', ate: '202701', a_cada_meses: 6, permanencia_pct_ao_ano: 90},
        {tipo: 'retirada', quantidade: 1, em: '202601'}]},
    {id: 'c2', nome: 'Só a persistência', metodo: 'M0'}]});
  // Modo simples: só o primeiro cenário, sem a janela própria, com a referência.
  const simples = S.pedidoDoSimulador({...CHEIO, modo: 'simples'});
  assert.deepEqual(simples.cenarios.map(item => item.id), ['c1', 'm0']);
  assert.equal('janela' in simples.cenarios[0], false);
  // Do cenário, vai o que a tela simples mostra: a primeira intervenção, numa data, com permanência total (o calendário, a
  // permanência e a segunda intervenção são do modo avançado). O método escolhido lá continua valendo, e a tela avisa.
  assert.deepEqual(simples.cenarios[0], {id: 'c1', nome: 'Com reforço', metodo: 'manual', taxa_manual_pct: 1.5,
    intervencoes: [{tipo: 'acrescimo', quantidade: 2.5, em: '202501'}]});
  // Desde a V3, o pedido do modo simples leva só o território em análise: sem escolha, o primeiro da seleção local. A janela geral
  // (que é do modo avançado) também não vai.
  assert.deepEqual([simples.base, 'estados_unidade' in simples, 'conjuntos' in simples, 'janela' in simples],
    [{municipios: {todos: false, estados: [], ids: ['code:130420']}}, false, false, false]);
  assert.deepEqual([S.cenariosEmUso(CHEIO).length, S.cenariosEmUso({...CHEIO, modo: 'simples'}).length,
    S.cenariosEmUso({...CHEIO, cenarios: Array.from({length: 8}, (_, k) => S.novoCenario('c' + k, 'x'))}).length], [2, 1, S.MAX_CENARIOS]);
  // Nenhum campo do pedido leva uma taxa sugerida, uma média aritmética ou uma projeção feita na tela.
  assert.equal(/media|sugest|previs/i.test(JSON.stringify(S.pedidoDoSimulador(CHEIO))), false);
  assert.equal(S.METODOS_DA_TELA.some(item => /média aritmética/i.test(item.rotulo)), false);
  // Os métodos da tela (V3): o primeiro é o jeito que a própria base escolheu; entram o M0d e o M0g; os nomes valem para qualquer base.
  assert.deepEqual(S.METODOS_DA_TELA.map(item => item.chave), ['padrao', 'M0', 'M0d', 'M0g', 'M1', 'M2', 'M3', 'manual']);
  assert.deepEqual(S.METODOS_DA_TELA.slice(0, 4).map(item => item.rotulo), ['Continuar como vinha (a forma escolhida pela base)', 'Persistência (M0)',
    'Último valor com o crescimento do grupo de cima (M0d)', 'Último valor com o crescimento da base toda (M0g)']);
  assert.equal(/médic|estado|municíp/i.test(JSON.stringify(S.METODOS_DA_TELA)), false);
});

// A resposta do motor na Proposta V3 (SIMULADOR-CENARIOS/V3/1): os nomes da base e a origem na fonte; em cada cenário, o jeito
// escolhido pela base, a faixa "N em cada 10" (com a conferência e como foi montada) e os "Entenda"; na retroprojeção, a escolha
// de cada nível e as faixas (a que a base não sustenta vem sem limites).
const ROTULOS_DO_BRASIL = {profissional: 'médico', profissionais: 'médicos', unidade: 'município', unidades: 'municípios', grupo: 'estado', grupos: 'estados',
  todo: 'Brasil'};
const BRUTO = {versao: 'SIMULADOR-CENARIOS/V3/1', fonte: {base: 'Brasil', categoria: 'MEDICINA', versao: 'abc', primeira: '201401', ultima: '202406', competencias: 22,
    rotulos: ROTULOS_DO_BRASIL, origem: 'brasil', ancora: '06',
    formas: {o_unidade: 'o município', os_unidades: 'os municípios', o_grupo: 'o estado', os_grupos: 'os estados', dos_grupos: 'dos estados', do_todo: 'do Brasil',
      no_todo: 'no Brasil', o_todo: 'o Brasil'}},
  competencias: ['201401', '202406'], ultimo_registro: '202406', janela: {inicio: '202106', fim: '202406', registros: 7, anos: 3, padrao: true},
  horizonte: {data: '202606', anos_desde_o_ultimo_registro: 2}, faixa: {em_10: 8, opcoes: [5, 8, 9], padrao: 8},
  territorios: [{id: 'code:130260', tipo: 'municipio', nivel: 'municipios', rotulo: 'MANAUS (AM)', uf: 'AM', unidade: 'médicos registrados no município',
    observado: [{competencia: '202401', valor: null, estado: 'ausencia_de_dado'}, {competencia: '202406', valor: 51, estado: 'observado', marca: 'pico_que_volta'}],
    historico: {registros: 7, de: '202106', ate: '202406', anos: 3, taxas_de_junho: [{de: '202106', ate: '202206', taxa_pct: 4.44}], media_aritmetica_pct: 4.26,
      mediana_pct: 4.25, desvio_pct: 0.18, taxa_composta_pct: 4.2603, nota: 'A média aritmética é só descrição.'}, lacunas: ['202401'],
    cenarios: [{id: 'c1', nome: 'Com 4 médicos', estado: 'calculado',
      metodo: {pedido: 'padrao', usado: 'M0d', rotulo: 'persistência com o crescimento recente do estado', padrao: true, provisorio: false, voltou_ao_m0: false, soma: null,
        escolhido_pela_base: 'M0d', e_o_escolhido: true},
      parametros: {n0: 51, origem: '202406', janela: {inicio: '202106', fim: '202406', registros: 7}, deriva_pct: 3.39},
      avisos: [{codigo: 'HORIZONTE_CAUTELA', texto: 'Cautela: o horizonte passa da metade da janela do método.'}, {codigo: 'X'}],
      horizonte: {anos: 2, aviso: 'cautela'},
      faixa: {estado: 'disponivel', motivo: null, em_10: 8, porte: '50 a 99', ate_anos: 4, como: 'propria',
        rotulo: 'a margem observada no passado da base, em municípios do mesmo porte; acompanha a intervenção', conferencia: 'conferida', casos: 2523, cobertura_pct: 75.4,
        origens_de_teste: 4},
      trajetoria: [{data: '202501', anos: 0.5833, base: 52, intervencao: 4, total: 56, retroprojecao: false,
          faixa: {inferior: 48.2, superior: 66.4, anos: 1, validada: true, estado: 'conferida', como: 'propria'}},
        {data: '202606', anos: 2, base: 54.5189, intervencao: 4, total: 58.5189, retroprojecao: false,
          faixa: {inferior: 48.16, superior: 74.87, anos: 2, validada: true, estado: 'conferida', como: 'propria'}}],
      final: {data: '202606', base: 54.5189, intervencao: 4, total: 58.5189, faixa: {inferior: 48.16, superior: 74.87, anos: 2, validada: true, estado: 'conferida', como: 'propria'}},
      texto: 'Cenário hipotético, não é previsão: …; "MANAUS (AM)" teria 59 médicos em jun/2026. Base: registros até jun/2024.',
      entenda: {jeito: {texto: 'O cenário parte do último registro usado (jun/2024) e soma o crescimento recente do estado.',
          exemplo: 'De 51 médicos em jun/2024, a base do cenário vai a 52,7 um ano depois, sem contar intervenções.'},
        faixa: {texto: 'Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte.', exemplo: 'Entre 48 e 75 médicos na data final.'}}},
    {id: 'm0', nome: 'Persistência (referência)', estado: 'retirada_acima_do_estoque', motivo: 'Em jan/2025, as retiradas passam…', metodo: {pedido: 'M0', usado: 'M0'},
      parametros: {n0: 51, origem: '202406'}, avisos: []},
    {id: 'c3', nome: 'Taxa', estado: 'nao_aplicavel', motivo: 'A taxa composta exige…', metodo: {pedido: 'M1'}},
    {id: 'c4', nome: 'Log', estado: 'nao_calculavel', motivo: 'Série em zero.', metodo: {pedido: 'M3'}}]},
  {id: null, rotulo: 'sem id'},
  {id: 'g1', tipo: 'conjunto', nivel: 'municipios', rotulo: 'Par', unidade: 'soma das contagens dos componentes', membros: ['code:1', 'code:2'],
    nomes_dos_membros: ['A (AM)', 'B (AM)'], observado: [], historico: {}, lacunas: [], cenarios: []}],
  retroprojecao: {origens: ['201706', '202306'], em_10: 8,
    faixas: [{porte: '1 a 3', anos: 1, em_10: 8, inferior_pct: -9.3, superior_pct: 87.3, casos: 4039, pede: 200, origens: 7, cobertura_pct: 75.0, estado: 'conferida',
        como: 'propria', rotulo: 'conferida com o que veio depois'},
      {porte: '10.000 ou mais', anos: 1, em_10: 8, inferior_pct: null, superior_pct: null, casos: 31, pede: 200, origens: null, cobertura_pct: null, estado: 'indisponivel',
        como: 'indisponivel', rotulo: 'indisponível (sem casos bastantes)'}],
    tabela: [{metodo: 'M0d', porte: '1 a 3', anos: 4, casos: 2715, origens: 4, erro_absoluto_medio: 1.7, vies: 1.4, frente_ao_m0: 0.8998},
      {metodo: 'M0', porte: '1 a 3', anos: 4, casos: 2715, origens: 4, erro_absoluto_medio: 1.9, vies: 1.7, frente_ao_m0: null}],
    escolha: {metodo: 'M0d'},
    niveis: {municipios: {origens: ['201706', '202306'], faixas: [], tabela: [], escolha: {metodo: 'M0d', rotulo: 'persistência com o crescimento recente do estado',
        motivo: 'escolhido', origens: 7, combinacoes: 22, texto: 'Para os municípios, a base escolheu a persistência com o crescimento recente do estado: …',
        candidatos: [{metodo: 'M1', frente_ao_m0: 1.0154, menos_erro_em: 2, combinacoes: 22, casos: 122317, vale: false, rotulo: 'taxa composta da janela'},
          {metodo: 'M0d', frente_ao_m0: 0.7136, menos_erro_em: 22, combinacoes: 22, casos: 122317, vale: true, rotulo: 'persistência com o crescimento recente do estado'}],
        excecoes: []}},
      estados: {escolha: {metodo: 'M1', rotulo: 'taxa composta da janela', motivo: 'escolhido', texto: 'Para os estados como unidade, a base escolheu a taxa composta da janela: …',
        candidatos: [{metodo: 'M1', frente_ao_m0: null}, 7]}}}},
  notas: ['Cenários hipotéticos.', 7], limitacoes: ['CENARIO_HIPOTETICO', 'PADRAO_ESCOLHIDO_PELA_BASE', 'FAIXA_SO_DO_METODO_PADRAO']};

test('a resposta do motor vira os tipos da tela, sem calcular nada', () => {
  const lida = S.normalizarSimulador(BRUTO);
  assert.deepEqual(lida.territorios.map(item => item.id), ['code:130260', 'g1'], 'o território sem id fica de fora');
  assert.deepEqual([lida.versao, lida.ultimoRegistro, lida.horizonte, lida.janela], ['SIMULADOR-CENARIOS/V3/1', '202406',
    {data: '202606', anosDesdeOUltimoRegistro: 2}, {inicio: '202106', fim: '202406', registros: 7, anos: 3, padrao: true}]);
  const manaus = lida.territorios[0];
  assert.deepEqual(manaus.observado, [{competencia: '202401', valor: null, estado: 'ausencia_de_dado', marca: null},
    {competencia: '202406', valor: 51, estado: 'observado', marca: 'pico_que_volta'}], 'ausência de dado não é zero');
  assert.deepEqual([manaus.historico.taxaCompostaPct, manaus.historico.mediaAritmeticaPct, manaus.historico.taxasDeJunho, manaus.lacunas],
    [4.2603, 4.26, [{de: '202106', ate: '202206', taxaPct: 4.44}], ['202401']]);
  const [calculado, retirada, naoSeAplica, naoCalculavel] = manaus.cenarios;
  // Na V3, o método padrão é o que a própria base escolheu (e a resposta diz isso): nos municípios e nos estados, deixou de ser provisório.
  assert.deepEqual(calculado.metodo, {pedido: 'padrao', usado: 'M0d', rotulo: 'persistência com o crescimento recente do estado', padrao: true, provisorio: false,
    voltouAoM0: false, soma: null, escolhidoPelaBase: 'M0d', eOEscolhido: true});
  assert.deepEqual(calculado.avisos, [{codigo: 'HORIZONTE_CAUTELA', texto: 'Cautela: o horizonte passa da metade da janela do método.'}], 'o aviso sem texto fica de fora');
  // A faixa de cada ponto diz se foi conferida com o que veio depois ("conferida") ou não ("provisoria") e como foi montada.
  assert.deepEqual(calculado.final, {data: '202606', base: 54.5189, intervencao: 4, total: 58.5189,
    faixa: {inferior: 48.16, superior: 74.87, anos: 2, validada: true, estado: 'conferida', como: 'propria'}});
  assert.deepEqual(calculado.trajetoria[0], {data: '202501', anos: 0.5833, base: 52, intervencao: 4, total: 56, retroprojecao: false, observado: null,
    faixa: {inferior: 48.2, superior: 66.4, anos: 1, validada: true, estado: 'conferida', como: 'propria'}});
  assert.deepEqual([calculado.faixa.estado, calculado.horizonte, calculado.parametros.origem], ['disponivel', {anos: 2, aviso: 'cautela'}, '202406']);
  assert.deepEqual([retirada.estado, retirada.final, retirada.texto, retirada.trajetoria, retirada.faixa.estado],
    ['retirada_acima_do_estoque', null, null, [], 'indisponivel']);
  assert.deepEqual(lida.territorios[1].membros, ['A (AM)', 'B (AM)'], 'os nomes dos componentes do conjunto');
  // Das faixas da retroprojeção, só as que têm limites: a que a base não sustenta (sem limites) fica de fora, e a tabela diz "indisponível".
  assert.deepEqual(lida.retroprojecao.faixas, [{porte: '1 a 3', anos: 1, inferiorPct: -9.3, superiorPct: 87.3, casos: 4039, origens: 7, coberturaPct: 75,
    rotulo: 'conferida com o que veio depois'}]);
  assert.deepEqual(lida.retroprojecao.tabela.map(linha => linha.frenteAoM0), [0.8998, null]);
  assert.deepEqual(lida.notas, ['Cenários hipotéticos.']);
  assert.deepEqual(lida.limitacoes, ['CENARIO_HIPOTETICO', 'PADRAO_ESCOLHIDO_PELA_BASE', 'FAIXA_SO_DO_METODO_PADRAO']);
  // Uma resposta vazia não quebra a tela.
  assert.deepEqual(S.normalizarSimulador(null).territorios, []);
  // Os textos da tabela: o valor com a faixa, ou o estado em palavras (nunca um número inventado).
  assert.deepEqual([calculado, retirada, naoSeAplica, naoCalculavel].map(item => S.textoDoFinal(item)),
    ['58,5 (48,2 a 74,9)', 'retirada acima do estoque: rever', 'não se aplica', 'não calculável']);
  // Num conjunto, a faixa leva o rótulo "aproximação", e o método é a soma das projeções dos membros (ou a soma das contagens).
  assert.equal(S.textoDoFinal(calculado, true), '58,5 (48,2 a 74,9, aproximação)');
  assert.equal(S.textoDoFinal(retirada, true), 'retirada acima do estoque: rever');
  const somado = {...calculado, metodo: {...calculado.metodo, soma: 'soma das projeções dos membros'}};
  assert.equal(S.metodoNaTabela(calculado), 'último valor com o crescimento do estado');
  assert.equal(S.metodoNaTabela({...calculado, metodo: {...calculado.metodo, usado: 'M0', voltouAoM0: true}}), 'último valor mantido (sem o crescimento do estado)');
  assert.equal(S.metodoNaTabela(somado, true), 'soma das projeções dos membros (cada um com o crescimento do seu estado)');
  assert.equal(S.metodoNaTabela({...somado, metodo: {...somado.metodo, usado: 'M0'}}, true), 'soma das projeções dos membros (cada um no último valor)');
  assert.equal(S.metodoNaTabela({...calculado, metodo: {...calculado.metodo, usado: 'M1'}}, true), 'soma das contagens dos componentes · taxa composta da janela');
  assert.ok(S.textoDaFaixa(calculado, true).startsWith('Faixa de 8 em cada 10 (aproximação) em jun/2026: de 48,2 a 74,9 médicos.'));
  assert.deepEqual([S.formatarMedicos(51), S.formatarMedicos(58.5189), S.formatarMedicos(14771.16), S.formatarTaxa(4.2603), S.formatarTaxa(-12.642), S.formatarTaxa(0)],
    ['51', '58,5', '14.771,2', '+4,26%', '−12,64%', '0,00%']);
  // A faixa de 8 em cada 10 (V3; antes, "faixa de 80%"), em linguagem simples: o que ela é e se foi conferida com o que veio depois ou
  // é provisória; sem faixa, indisponível, com o motivo do motor. Os demais casos ficam no teste próprio da faixa, mais abaixo.
  assert.equal(S.textoDaFaixa(calculado), 'Faixa de 8 em cada 10 em jun/2026: de 48,2 a 74,9 médicos. No passado da base, em 8 de cada 10 casos de territórios do mesmo ' +
    'porte, o número observado ficou dentro dessa margem; ela acompanha a intervenção. Conferida com o que veio depois.');
  const longe = {...calculado, final: {...calculado.final, faixa: {...calculado.final.faixa, anos: 4, validada: false, estado: 'provisoria'}}};
  assert.ok(S.textoDaFaixa(longe, true).endsWith('territórios com o porte desta soma (uma aproximação para o conjunto), o número observado ficou dentro dessa ' +
    'margem; ela acompanha a intervenção. Faixa provisória: ainda não deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do esperado.'));
  assert.equal(S.textoDaFaixa({...calculado, final: {...calculado.final, faixa: null}}),
    'Faixa de 8 em cada 10: indisponível nesta data: ela vai só até 4 anos depois do último registro usado.');
  const semCasos = 'A faixa de 8 em cada 10 pede 200 casos por prazo, e esta base tem 189 em 1 ano para o porte deste território, mesmo juntando os ' +
    'portes vizinhos e os menores.';
  assert.equal(S.textoDaFaixa({...calculado, final: {...calculado.final, faixa: null},
    faixa: {estado: 'indisponivel', motivo: semCasos, rotulo: null, em10: 8, ateAnos: null, conferencia: null, como: null}}), 'Faixa de 8 em cada 10: indisponível. ' + semCasos);
  assert.deepEqual(['M0', 'M0d', 'M0g', 'M1'].map(metodo => S.NOME_CURTO_DO_METODO[metodo]),
    ['último valor mantido', 'último valor com o crescimento do estado', 'último valor com o crescimento da base toda', 'taxa composta da janela']);
  // Linguagem simples nos textos da tela (decisão D-C): os termos técnicos ficam nos detalhes, na documentação e nas exportações.
  const semComentarios = codigo => codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  const codigo = semComentarios(ler('simuladorModel.ts')) + semComentarios(ler('SimuladorDeCenarios.tsx'));
  for (const termo of ['deriva', 'não calibrado', 'limiar', 'Theil', 'Poisson', 'fora da amostra', 'média aritmética como'])
    assert.ok(!codigo.includes(termo), termo);
  // "candidatos" passou a ser um campo da resposta do motor (a escolha do jeito de projetar, V3), que o modelo lê pelo nome: a palavra
  // fica só em nomes do código. Nos textos (cadeias, modelos de texto e texto do JSX), que são o que vai à tela, nenhum dos termos aparece.
  const textosDoCodigo = [['simuladorModel.ts', ts.ScriptKind.TS], ['SimuladorDeCenarios.tsx', ts.ScriptKind.TSX]].flatMap(([nome, tipo]) => {
    const textos = [];
    const visitar = no => {
      if (ts.isStringLiteralLike(no) || ts.isTemplateHead(no) || ts.isTemplateMiddle(no) || ts.isTemplateTail(no) || ts.isJsxText(no)) textos.push(no.text);
      ts.forEachChild(no, visitar);
    };
    visitar(ts.createSourceFile(nome, ler(nome), ts.ScriptTarget.ES2022, true, tipo));
    return textos;
  });
  assert.ok(textosDoCodigo.includes('O que testar') && textosDoCodigo.includes(' (escolhida pela base)'), 'os textos da tela entram na conferência');
  for (const termo of ['deriva', 'candidato', 'não calibrado', 'limiar', 'theil', 'poisson', 'fora da amostra', 'média aritmética como'])
    assert.deepEqual(textosDoCodigo.filter(texto => texto.toLowerCase().includes(termo)), [], termo);
  // AJ-05 (18/11/2026): nos textos da tela do Simulador, "forma de projetar", nunca "jeito"; e nada de "por convenção" (os limites dos
  // sinais 1 e 2 aplicados ao cenário são os "limites fixos" do Detector). Os identificadores (data-testid) e o campo `jeito` da
  // resposta do motor, que não muda, não são textos da tela.
  assert.deepEqual(textosDoCodigo.filter(texto => /jeito|convenç/i.test(texto) && !/^[a-z0-9-]+$/.test(texto)), [], 'jeito ou convenção num texto da tela');
  // As contas da data final: a base do cenário e a intervenção, separadas.
  assert.equal(S.contasDoFinal(calculado), 'Na data final, neste território: base do cenário de 54,5 + 4 da intervenção = 58,5 médicos (o texto acima arredonda para o inteiro).');
  assert.equal(S.contasDoFinal({...calculado, final: {...calculado.final, intervencao: -3, total: 51.5189}}),
    'Na data final, neste território: base do cenário de 54,5 − 3 da intervenção = 51,5 médicos (o texto acima arredonda para o inteiro).');
  assert.equal(S.contasDoFinal({...calculado, final: {...calculado.final, intervencao: 0, total: 54.5189}}), 'Na data final: base do cenário de 54,5 médicos, sem intervenção.');
  assert.equal(S.contasDoFinal(retirada), '');
  // Os limites das faixas, em percentual inteiro: arredondados, nunca truncados.
  assert.deepEqual([-25.6, 48.1, 0.2, 104.4, -0.4].map(S.formatarPercentualInteiro), ['−26%', '+48%', '0%', '+104%', '0%']);
});

test('exportar e importar o cenário (JSON), com a versão do método e da base', () => {
  const exportado = S.exportarCenario(CHEIO, {versaoDoMetodo: 'SIMULADOR-CENARIOS/V3/1', versaoDaBase: 'abc', ultimoRegistro: '202406', quando: '2026-11-10T12:00:00.000Z'});
  const lido = JSON.parse(exportado);
  assert.deepEqual([lido.formato, lido.versao_do_metodo, lido.base, lido.exportado_em], ['ADT-CENARIO/1', 'SIMULADOR-CENARIOS/V3/1',
    {nome: 'Brasil', categoria: 'MEDICINA', versao: 'abc', ultimo_registro: '202406'}, '2026-11-10T12:00:00.000Z']);
  assert.equal(lido.aviso, 'Cenários hipotéticos e condicionais: não são previsão nem recomendação.');
  assert.deepEqual(lido.selecao_local.conjuntos, [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 2}], 'a composição e a versão do conjunto');
  const importado = S.importarCenario(exportado);
  assert.deepEqual([importado.erro, importado.versaoDaBase], [null, 'abc']);
  assert.deepEqual(importado.config, CHEIO, 'ida e volta sem perda');
  assert.equal('acompanha' in importado.config, false, 'o cenário importado não acompanha a seleção principal');
  assert.equal('acompanha' in JSON.parse(S.exportarCenario({...CHEIO, acompanha: true}, {versaoDoMetodo: '', versaoDaBase: '', ultimoRegistro: '', quando: ''})), false);
  assert.deepEqual(S.importarCenario('{nao json'), {config: null, erro: 'O arquivo não é um JSON de cenário.', versaoDaBase: null});
  assert.equal(S.importarCenario('{"formato":"X"}').erro, 'O arquivo não é um cenário do Simulador (formato ADT-CENARIO/1).');
  assert.equal(S.importarCenario(JSON.stringify({formato: S.FORMATO_DO_CENARIO, cenarios: [], horizonte: '202606'})).erro,
    'O cenário do arquivo está incompleto (faltam os cenários ou a data final).');
  // Um arquivo com partes inválidas: o método desconhecido vira o padrão, o conjunto de um só membro sai, e nada é calculado.
  const tolerante = S.importarCenario(JSON.stringify({formato: S.FORMATO_DO_CENARIO, horizonte: '202606', modo: 'x',
    selecao_local: {municipios: ['code:1', 3], conjuntos: [{id: 'g', membros: ['code:1']}, {id: 'h', membros: ['code:1', 'code:2']}]},
    cenarios: [{metodo: 'previsao', intervencoes: [{tipo: 'x', em: '202501'}]}, {id: 'k', nome: 'K', metodo: 'M0d'}, {metodo: 'M0g'}]})).config;
  assert.deepEqual([tolerante.modo, tolerante.local.municipios, tolerante.local.conjuntos.map(item => item.id), tolerante.cenarios.map(item => item.metodo)],
    ['simples', ['code:1'], ['h'], ['padrao', 'M0d', 'M0g']]);   // o M0g (o crescimento da base toda, V3) é um método válido no arquivo
  assert.deepEqual(tolerante.cenarios[0].intervencoes, [{tipo: 'acrescimo', quantidade: '1', em: '202501', periodica: false, ate: '202501', aCadaMeses: '12',
    permanencia: '100'}]);
});

test('CSV dos resultados: uma linha por território, cenário e data, com a rastreabilidade', () => {
  const lida = S.normalizarSimulador(BRUTO);
  const csv = S.csvDoSimulador(lida);
  assert.equal(csv.charCodeAt(0), 0xFEFF, 'com BOM, para o Excel');
  const linhas = csv.slice(1).split('\r\n');
  assert.equal(linhas.length, 7, 'o cabeçalho, 2 datas do cenário calculado, 3 cenários sem valor e o fim');
  assert.equal(linhas[0], 'Identificador;Território;Tipo;Unidade de contagem;Cenário;Método pedido;Método usado;Estado do cenário;Origem do cenário;' +
    'Médicos na origem;Janela: início;Janela: fim;Data;Natureza;Observado;Base do cenário;Intervenção;Total do cenário;Faixa de 80%: inferior;' +
    'Faixa de 80%: superior;Avisos;Texto do cenário;Planejamento inverso: meta;Planejamento inverso: médicos por evento;Planejamento inverso: eventos;' +
    'Hipótese do cenário: nível em poucos médicos;Versão do método;Versão da base');
  assert.equal(linhas[2], 'code:130260;MANAUS (AM);municipio;médicos registrados no município;Com 4 médicos;padrao;M0d;calculado;202406;51;202106;202406;202606;' +
    'cenário hipotético;;54,5189;4;58,5189;48,16;74,87;HORIZONTE_CAUTELA;"Cenário hipotético, não é previsão: …; ""MANAUS (AM)"" teria 59 médicos em jun/2026. ' +
    'Base: registros até jun/2024.";;;;;SIMULADOR-CENARIOS/V3/1;abc', 'a precisão integral, com vírgula decimal, e as aspas dobradas');
  assert.equal(linhas[3], 'code:130260;MANAUS (AM);municipio;médicos registrados no município;Persistência (referência);M0;M0;' +
    'retirada_acima_do_estoque: Em jan/2025, as retiradas passam…;202406;51;;;;;;;;;;;;;;;;;SIMULADOR-CENARIOS/V3/1;abc', 'sem valor inventado');
  assert.ok(linhas[4].includes(';nao_aplicavel: A taxa composta exige…;') && linhas[5].includes(';nao_calculavel: Série em zero.;'));
  assert.ok(linhas.slice(0, 6).every(linha => linha.split(';').length >= 28));
  assert.equal(linhas[6], '');
  // O cabeçalho diz a faixa da resposta: 80% com 8 em cada 10 (o padrão); 50% e 90% quando a pessoa pede 5 ou 9 em cada 10.
  assert.deepEqual([5, 9].map(em10 => S.csvDoSimulador({...lida, retroprojecao: {...lida.retroprojecao, em10}}).slice(1).split('\r\n')[0].split(';').slice(18, 20)),
    [['Faixa de 50%: inferior', 'Faixa de 50%: superior'], ['Faixa de 90%: inferior', 'Faixa de 90%: superior']]);
});

// ------------------------------------------------------------------------------------------------ etapa 5 do comando V22
test('o Brasil entra só na seleção local do Simulador, pela contagem nacional', () => {
  const local = {municipios: ['code:130260'], estados: ['35'], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 2}]};
  const comBrasil = S.comOBrasil(local, true);
  assert.deepEqual(comBrasil, {...local, brasil: true});
  assert.deepEqual([S.ID_DO_BRASIL, S.totalDaSelecaoLocal(local), S.totalDaSelecaoLocal(comBrasil)], ['br', 3, 4]);
  assert.deepEqual(S.selecaoLocalParaOPedido(comBrasil).brasil, true);
  assert.deepEqual(S.selecaoLocalParaOPedido(S.comOBrasil(S.SELECAO_LOCAL_VAZIA, true)), {brasil: true}, 'só o Brasil também é uma seleção');
  assert.equal('brasil' in S.selecaoLocalParaOPedido(local), false);
  assert.deepEqual([S.comOBrasil(comBrasil, false), S.tirarTerritorio(comBrasil, 'br')], [local, local]);
  assert.deepEqual(S.tirarTerritorio(comBrasil, 'uf:35'), {municipios: ['code:130260'], estados: [], conjuntos: local.conjuntos, brasil: true});
  assert.equal(S.pendenciaDoPedido({...S.configInicial(S.comOBrasil(S.SELECAO_LOCAL_VAZIA, true), '202406')}), null);
  // A seleção principal não tem o Brasil como unidade: a cópia dela nunca o traz.
  assert.equal('brasil' in S.copiarSelecao({base: {municipios: {todos: true, estados: [], ids: []}}}, {todasAsUnidades: ['code:1'], unidadesDoGrupo: () => []}), false);
});

const R1 = S.novaReferencia([], {alvo: 'code:420540', rotulo: 'FLORIANOPOLIS (SC)', tipo: 'dinamica'});
const R2 = S.novaReferencia([R1], {alvo: 'br', rotulo: 'Brasil', tipo: 'fixa'});
const R3 = S.novaReferencia([R1, R2], {alvo: 'valor', rotulo: 'Valor informado por você', tipo: 'valor', valor: '6.500'});
const R4 = S.novaReferencia([R1, R3], {alvo: 'g1', rotulo: 'Par (conjunto)', tipo: 'fixa'});

test('referências de comparação: fixas, dinâmicas ou um valor, até cinco, com a métrica declarada', () => {
  assert.deepEqual([R1, R2, R3, R4], [{id: 'r1', alvo: 'code:420540', rotulo: 'FLORIANOPOLIS (SC)', tipo: 'dinamica', valor: ''},
    {id: 'r2', alvo: 'br', rotulo: 'Brasil', tipo: 'fixa', valor: ''}, {id: 'r3', alvo: 'valor', rotulo: 'Valor informado por você', tipo: 'valor', valor: '6.500'},
    {id: 'r4', alvo: 'g1', rotulo: 'Par (conjunto)', tipo: 'fixa', valor: ''}], 'o identificador livre seguinte');
  // O nome do conjunto leva a palavra "Conjunto" uma vez só (revisão da etapa 5, 13/11/2026): "+ Conjunto A", nunca "+ Conjunto Conjunto A".
  assert.deepEqual(['Conjunto A', ' conjunto b ', 'Par', 'Conjuntura'].map(S.comoConjunto), ['Conjunto A', 'conjunto b', 'Conjunto Par', 'Conjunto Conjuntura']);
  assert.deepEqual([S.MAX_REFERENCIAS, S.novaReferencia([R1, R2, R3, R4, R1], {alvo: 'uf:35', rotulo: 'x', tipo: 'fixa'})], [5, null]);
  // A referência a um conjunto vale enquanto ele está na seleção local; as demais não dependem dela.
  const local = {municipios: [], estados: [], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:1', 'code:2']}]};
  assert.deepEqual(S.referenciasValidas([R1, R2, R3, R4], local).map(ref => ref.id), ['r1', 'r2', 'r3', 'r4']);
  assert.deepEqual(S.referenciasValidas([R1, R2, R3, R4], S.SELECAO_LOCAL_VAZIA).map(ref => ref.id), ['r1', 'r2', 'r3']);
  assert.deepEqual([S.referenciasValidas(undefined, local), S.referenciasValidas([{...R4, alvo: 'uf:35'}], S.SELECAO_LOCAL_VAZIA).length], [[], 1]);
  // Numa planilha sem a coluna de código, a unidade é identificada pelo nome ("name:…"): a referência a ela também não depende da seleção local.
  assert.deepEqual(S.referenciasValidas([{...R4, id: 'r5', alvo: 'name:Distrito 02'}, {...R4, id: 'r6', alvo: 'outro'}], S.SELECAO_LOCAL_VAZIA).map(ref => ref.id), ['r5']);
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  // O pedido: o território de cada referência, ou o valor da pessoa (com vírgula e ponto de milhar); a métrica só vai quando é a taxa.
  // (No modo avançado, que leva a seleção local inteira; no modo simples da V3, só o território em análise vai no pedido.)
  const comBrasil = {...inicial, local: S.comOBrasil(inicial.local, true), referencias: [R1, R2, R3], metrica: 'taxa'};
  const pedido = S.pedidoDoSimulador({...comBrasil, modo: 'avancado'});
  assert.deepEqual(pedido.referencias, [{id: 'r1', tipo: 'dinamica', territorio: 'code:420540'}, {id: 'r2', tipo: 'fixa', territorio: 'br'},
    {id: 'r3', tipo: 'valor', valor: 6500, rotulo: 'Valor informado por você'}]);
  assert.deepEqual([pedido.comparacao, pedido.brasil], [{metrica: 'taxa'}, true]);
  // No modo simples, o pedido não leva as referências nem a métrica (elas ficam guardadas e voltam a valer no modo avançado), e o
  // Brasil só vai quando é o território em análise.
  const doSimples = S.pedidoDoSimulador(comBrasil);
  assert.deepEqual(['referencias' in doSimples, 'comparacao' in doSimples, 'brasil' in doSimples], [false, false, false]);
  assert.deepEqual([S.pedidoDoSimulador({...comBrasil, territorio: 'br'}).brasil, 'base' in S.pedidoDoSimulador({...comBrasil, territorio: 'br'})], [true, false]);
  const avancado = {...inicial, modo: 'avancado'};
  assert.deepEqual(['comparacao' in S.pedidoDoSimulador({...avancado, referencias: [R1]}), S.pedidoDoSimulador({...avancado, referencias: [R1]}).referencias.length], [false, 1],
    'por quantidade, a métrica padrão do motor');
  assert.equal('comparacao' in S.pedidoDoSimulador({...avancado, metrica: 'taxa'}), false, 'sem referências, não há comparação a pedir');
  assert.deepEqual([S.pendenciaDoPedido({...avancado, referencias: [{...R3, valor: ''}]}), S.pendenciaDoPedido({...avancado, referencias: [{...R3, valor: '-1'}]}),
    S.pendenciaDoPedido({...avancado, referencias: [R3]})], ['Informe o valor da referência “Valor informado por você”.',
    'Informe o valor da referência “Valor informado por você”.', null]);
});

test('planejamento inverso: a meta é uma hipótese da pessoa, e o pedido leva só a meta e o calendário', () => {
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  assert.deepEqual(S.novoPlano('202506'), {meta: 'valor', valor: '', referencia: '', em: '202506', periodica: false, ate: '202506', aCadaMeses: '12', permanencia: '100'});
  // (No modo avançado: o calendário dos acréscimos e a meta por referência são dele; o modo simples vem logo abaixo.)
  const comPlano = (plano, modo = 'avancado') => ({...inicial, modo, referencias: [R1, R2, R3],
    cenarios: [{...inicial.cenarios[0], planejamento: {...S.novoPlano('202506'), ...plano}}]});
  assert.deepEqual([comPlano({}), comPlano({valor: '20'}), comPlano({meta: 'patamar'}), comPlano({meta: 'patamar', valor: 'x'}), comPlano({meta: 'referencia'}),
    comPlano({meta: 'referencia', referencia: 'r1'}), comPlano({valor: '20', em: ''}), comPlano({valor: '20', periodica: true, ate: '202501'})].map(S.pendenciaDoPedido), [
    'Informe a meta: um número acima de zero.', null, null, 'Informe a meta: um número acima de zero.',   // sem "médicos": vale para qualquer base (V3)
    'Escolha a referência que serve de meta no planejamento inverso.', null, 'Informe a data dos acréscimos do planejamento inverso.',
    'No planejamento inverso, a data final dos acréscimos vem depois da inicial.']);
  // No modo simples, a meta é um número (ou o patamar trazido pelo Detector): as referências não vão no pedido, e a meta por
  // referência, que só o modo avançado monta, fica pendente, com a indicação de onde informar a meta.
  assert.deepEqual([comPlano({meta: 'referencia'}, 'simples'), comPlano({meta: 'referencia', referencia: 'r1'}, 'simples'), comPlano({valor: '20'}, 'simples'),
    comPlano({meta: 'patamar'}, 'simples'), comPlano({}, 'simples')].map(S.pendenciaDoPedido), ['No modo simples, a meta é um número: informe a meta em “O que testar”.',
    'No modo simples, a meta é um número: informe a meta em “O que testar”.', null, null, 'Informe a meta: um número acima de zero.']);
  const [cenario, persistencia] = S.pedidoDoSimulador(comPlano({meta: 'referencia', referencia: 'r1', periodica: true, ate: '202806', permanencia: '95'})).cenarios;
  assert.deepEqual(cenario.planejamento, {meta: {tipo: 'referencia', referencia: 'r1'}, em: '202506', ate: '202806', a_cada_meses: 12, permanencia_pct_ao_ano: 95});
  assert.deepEqual(persistencia, {id: 'm0', nome: 'Persistência (referência)', metodo: 'M0'}, 'a persistência de comparação continua no pedido');
  // O patamar anterior: em branco, o motor usa o de cada território; com valor, o que a pessoa informou.
  assert.deepEqual(S.pedidoDoSimulador(comPlano({meta: 'patamar'})).cenarios[0].planejamento, {meta: {tipo: 'patamar'}, em: '202506'});
  assert.deepEqual(S.pedidoDoSimulador(comPlano({meta: 'patamar', valor: '1,8'})).cenarios[0].planejamento, {meta: {tipo: 'patamar', valor: 1.8}, em: '202506'});
  // O cenário que é a persistência, mas com planejamento, não dispensa a persistência de comparação.
  assert.deepEqual(S.pedidoDoSimulador({...inicial, cenarios: [{...inicial.cenarios[0], metodo: 'M0', planejamento: {...S.novoPlano('202506'), valor: '20'}}]})
    .cenarios.map(item => item.id), ['c1', 'm0']);
  // Nenhuma quantidade vai no pedido: quem calcula o número de médicos é o motor.
  assert.equal(/quantidade|por_evento/.test(JSON.stringify(S.pedidoDoSimulador(comPlano({valor: '20'})).cenarios[0].planejamento)), false);
});

test('"Abrir no Simulador" e "Simular recuperação": o Detector leva o território e o contexto, e a meta é hipotética e editável', () => {
  const principal = {base: {municipios: {todos: false, estados: ['13'], ids: []}}, estados_unidade: ['15'],
    conjuntos: [{id: 'c1', rotulo: 'Par', membros: ['code:1', 'code:2'], versao: 3}]};
  assert.deepEqual([{id: 'code:130260', tipo: 'municipio'}, {id: 'uf:15', tipo: 'estado'}, {id: 'c1', tipo: 'conjunto'}, {id: 'c9', tipo: 'conjunto'},
    {id: 'br', tipo: 'brasil'}].map(alvo => S.selecaoDoDetector(alvo, principal)), [{municipios: ['code:130260'], estados: [], conjuntos: []},
    {municipios: [], estados: ['15'], conjuntos: []}, {municipios: [], estados: [], conjuntos: [{id: 'c1', rotulo: 'Par', membros: ['code:1', 'code:2'], versao: 3}]},
    null, null], 'o conjunto vai com a composição e a versão; o que não está mais na seleção principal não vai');
  assert.equal(S.selecaoDoDetector({id: 'c1', tipo: 'conjunto'}, null), null);
  const recuperacao = S.configDoDetector({local: {municipios: ['code:170025'], estados: [], conjuntos: []}, rotulo: 'ABREULANDIA (TO)',
    sinais: ['Poucos médicos (escala estrutural)'], fim: '202406', exploratorio: true}, '202406', null, 1.75);
  assert.deepEqual(recuperacao, {local: {municipios: ['code:170025'], estados: [], conjuntos: []}, janela: null, horizonte: '202606', modo: 'simples', acompanha: false,
    doDetector: {rotulo: 'ABREULANDIA (TO)', fim: '202406', sinais: ['Poucos médicos (escala estrutural)'], recuperacao: true, exploratorio: true},
    cenarios: [{id: 'c1', nome: 'Recuperação do patamar', metodo: 'padrao', taxaManual: '', janela: null, intervencoes: [],
      planejamento: {meta: 'patamar', valor: '1,75', referencia: '', em: '202506', periodica: false, ate: '202506', aCadaMeses: '12', permanencia: '100'}}]},
    'a meta leva o patamar com a precisão do Detector');
  assert.equal(S.pendenciaDoPedido(recuperacao), null);
  assert.deepEqual(S.pedidoDoSimulador(recuperacao).cenarios[0].planejamento, {meta: {tipo: 'patamar', valor: 1.75}, em: '202506'});
  // Na V3, o Simulador abre no modo simples com "Chegar a uma meta" marcado e o patamar como meta. A pessoa pode trocá-la (ou apagá-la:
  // em branco, o motor usa o patamar do território), e marcar "Chegar a uma meta" de novo não apaga o que veio do Detector.
  assert.deepEqual([recuperacao.modo, S.testeDoCenario(recuperacao.cenarios[0]),
    S.comOTeste(recuperacao.cenarios[0], 'meta', '202506').planejamento === recuperacao.cenarios[0].planejamento], ['simples', 'meta', true]);
  const comAMeta = valor => ({...recuperacao, cenarios: [{...recuperacao.cenarios[0], planejamento: {...recuperacao.cenarios[0].planejamento, valor}}]});
  assert.deepEqual([S.pedidoDoSimulador(comAMeta('3')).cenarios[0].planejamento, S.pedidoDoSimulador(comAMeta('')).cenarios[0].planejamento, S.pendenciaDoPedido(comAMeta('')),
    S.pendenciaDoPedido(comAMeta('x'))], [{meta: {tipo: 'patamar', valor: 3}, em: '202506'}, {meta: {tipo: 'patamar'}, em: '202506'}, null,
    'Informe a meta: um número acima de zero.']);
  // "Abrir no Simulador": sem planejamento, com a janela que a pessoa escolheu no Detector; a seleção não acompanha a principal.
  const aberto = S.configDoDetector({local: {municipios: [], estados: ['15'], conjuntos: []}, rotulo: 'Pará (PA)', sinais: [], fim: '202106'}, '202406',
    {inicio: '201801', fim: '202106'}, null);
  assert.deepEqual([aberto.janela, aberto.acompanha, aberto.doDetector, 'planejamento' in aberto.cenarios[0], aberto.cenarios[0].nome],
    [{inicio: '201801', fim: '202106'}, false, {rotulo: 'Pará (PA)', fim: '202106', sinais: [], recuperacao: false}, false, 'Cenário 1']);
  assert.deepEqual([aberto.modo, S.testeDoCenario(aberto.cenarios[0]), S.primeiroDaSelecao(aberto.local)], ['simples', 'continuar', 'uf:15']);
  // A janela escolhida no Detector fica guardada à parte: é a que o modo simples leva ao motor, mesmo que a janela geral mude no
  // modo avançado (onde vale a janela geral). Sem janela escolhida lá, nada é guardado.
  assert.deepEqual([aberto.janelaDoDetector, 'janelaDoDetector' in recuperacao], [{inicio: '201801', fim: '202106'}, false]);
  assert.deepEqual(S.pedidoDoSimulador(aberto), {estados_unidade: ['15'], janela: {inicio: '201801', fim: '202106'}, horizonte: '202606',
    cenarios: [{id: 'c1', nome: 'Cenário 1', metodo: 'padrao'}, {id: 'm0', nome: 'Persistência (referência)', metodo: 'M0'}]});
  const comOutraJanela = {...aberto, janela: {inicio: '202006', fim: '202406'}};
  assert.deepEqual([S.pedidoDoSimulador(comOutraJanela).janela, S.pedidoDoSimulador({...comOutraJanela, modo: 'avancado'}).janela],
    [{inicio: '201801', fim: '202106'}, {inicio: '202006', fim: '202406'}]);
  // O contexto do Detector não vai ao motor nem ao cenário exportado: é só o aviso da tela.
  assert.equal(JSON.stringify(S.pedidoDoSimulador(recuperacao)).includes('ABREULANDIA'), false);
  assert.equal('doDetector' in JSON.parse(S.exportarCenario(recuperacao, {versaoDoMetodo: '', versaoDaBase: '', ultimoRegistro: '', quando: ''})), false);
});

const BRUTO_5 = {versao: 'SIMULADOR-CENARIOS/V3/1', fonte: {base: 'Brasil', categoria: 'MEDICINA', versao: 'abc', primeira: '201401', ultima: '202406'},
  competencias: ['202406'], ultimo_registro: '202406', janela: {inicio: '202106', fim: '202406', registros: 7, anos: 3, padrao: true},
  horizonte: {data: '202606', anos_desde_o_ultimo_registro: 2},
  territorios: [{id: 'code:130340', tipo: 'municipio', nivel: 'municipios', rotulo: 'PARINTINS (AM)', unidade: 'médicos registrados no município', observado: [],
    historico: {}, lacunas: [], cenarios: [
      {id: 'c1', nome: 'Cenário 1', estado: 'calculado', metodo: {pedido: 'M0', usado: 'M0'}, parametros: {n0: 12, origem: '202406', janela: {inicio: '202106', fim: '202406'}},
        avisos: [], trajetoria: [{data: '202606', anos: 2, base: 12, intervencao: 0, total: 12, retroprojecao: false}],
        final: {data: '202606', base: 12, intervencao: 0, total: 12}, texto: 'Cenário hipotético, não é previsão: …',
        comparacoes: [{id: 'r1', rotulo: 'BELEM (PA)', tipo: 'fixa', metrica: 'quantidade', avisos: ['A referência contém o território.', 3], estado: 'calculada',
          descricao: 'fixa: o valor de jun/2024 mantido', metodo: 'M0',
          pontos: [{data: '202406', territorio: 12, referencia: 50, diferenca: 38, razao: 0.24, indice: 24}, {data: 'x'},
            {data: '202606', territorio: 12, referencia: 50, diferenca: 38, razao: 0.24, indice: 24}],
          final: {data: '202606', territorio: 12, referencia: 50, diferenca: 38, razao: 0.24, indice: 24}, alcance: {estado: 'nao_alcanca', data: null}, texto: 'Em jun/2026, …'},
        {id: 'r2', rotulo: 'Meta', tipo: 'valor', metrica: 'quantidade', avisos: [], estado: 'nao_calculavel', motivo: 'A referência não tem valor nas datas do cenário.'}],
        planejamento: {meta: {tipo: 'valor', valor: 21, rotulo: 'Meta hipotética: 21 médicos em jun/2026'}, base_na_data_final: 12, outras_intervencoes: 0, sem_o_plano: 12,
          eventos: 2, datas: ['202501', '202601'], permanencia_pct_ao_ano: 100, estado: 'calculado', falta: 9, por_evento: 5, total: 10, teorico_por_evento: 4.5, resultado: 22,
          intervencao: {tipo: 'acrescimo', quantidade: 5, em: '202501', ate: '202601', a_cada_meses: 12, permanencia_pct_ao_ano: 97.5},
          trajetoria: [{data: '202501', total: 17, intervencao: 5}, {data: 'x'}, {total: 20}, {data: '202606', total: 22, intervencao: 10}],
          texto: 'Meta hipotética: 21 médicos em jun/2026. …'},
        hipotetico: {rotulo: 'hipótese do cenário', data: '202606', valor: 12, inteiro: 12, classe: null, impacto_pct: 8.333333333333334}},
      {id: 'm0', nome: 'Persistência (referência)', estado: 'calculado', metodo: {pedido: 'M0', usado: 'M0'}, parametros: {n0: 12, origem: '202406'}, avisos: [], trajetoria: [],
        final: {data: '202606', base: 12, intervencao: 0, total: 12},
        planejamento: {estado: 'nao_alcancavel', motivo: 'Com permanência zero…', meta: {tipo: 'valor', valor: 20, rotulo: 'Meta hipotética: 20 médicos em jun/2026'},
          eventos: 1, datas: ['202506']}}]}],
  retroprojecao: {}, notas: [], limitacoes: [],
  referencias: [{id: 'r1', rotulo: 'BELEM (PA)', tipo: 'fixa', territorio: 'code:150140', unidade: 'médicos registrados no município', estado: 'calculada',
    descricao: 'fixa: o valor de jun/2024 mantido', motivo: null}],
  comparacao: {metrica: 'quantidade', hipotese_de_populacao: null}};

test('as comparações, o planejamento inverso e a hipótese derivada da simulação vêm do motor', () => {
  const lida = S.normalizarSimulador(BRUTO_5);
  const [c1, m0] = lida.territorios[0].cenarios;
  const ponto = {territorio: 12, referencia: 50, diferenca: 38, razao: 0.24, indice: 24};
  // `forma` (a diferença ou a razão) é de 15/11/2026: a resposta de antes não a traz, e vale a diferença.
  assert.deepEqual(c1.comparacoes[0], {id: 'r1', rotulo: 'BELEM (PA)', tipo: 'fixa', metrica: 'quantidade', forma: 'diferenca', estado: 'calculada', motivo: null,
    avisos: ['A referência contém o território.'], descricao: 'fixa: o valor de jun/2024 mantido', pontos: [{data: '202406', ...ponto}, {data: '202606', ...ponto}],
    final: {data: '202606', ...ponto}, alcance: {estado: 'nao_alcanca', data: null}, texto: 'Em jun/2026, …'}, 'o ponto sem valor fica de fora; nenhuma data de alcance é inventada');
  assert.deepEqual(c1.comparacoes[1], {id: 'r2', rotulo: 'Meta', tipo: 'valor', metrica: 'quantidade', forma: 'diferenca', estado: 'nao_calculavel',
    motivo: 'A referência não tem valor nas datas do cenário.', avisos: [], descricao: null, pontos: [], final: null, alcance: null, texto: null});
  // O caminho do cenário com o acréscimo (para o gráfico) vem do motor: o ponto sem data ou sem total fica de fora. A meta que
  // não é o patamar não traz a origem.
  assert.deepEqual(c1.planejamento, {estado: 'calculado', motivo: null,
    meta: {tipo: 'valor', valor: 21, rotulo: 'Meta hipotética: 21 médicos em jun/2026', patamar: null, registros: null}, semOPlano: 12,
    eventos: 2, datas: ['202501', '202601'], porEvento: 5, total: 10, teoricoPorEvento: 4.5, resultado: 22, texto: 'Meta hipotética: 21 médicos em jun/2026. …',
    trajetoria: [{data: '202501', total: 17, intervencao: 5}, {data: '202606', total: 22, intervencao: 10}],
    intervencao: {tipo: 'acrescimo', quantidade: 5, em: '202501', ate: '202601', aCadaMeses: 12, permanencia: 97.5}});
  assert.deepEqual(m0.planejamento.trajetoria, [], 'sem resultado, não há caminho a desenhar');
  // A meta que é o patamar diz de onde veio: o patamar sem arredondar e de quantos registros ele é a média.
  const doPatamar = S.normalizarSimulador({...BRUTO_5, territorios: [{...BRUTO_5.territorios[0], cenarios: [{...BRUTO_5.territorios[0].cenarios[0],
    planejamento: {...BRUTO_5.territorios[0].cenarios[0].planejamento, meta: {tipo: 'patamar', valor: 79, patamar: 78.25, registros: 4, arredondado: true,
      rotulo: 'Meta hipotética: voltar ao patamar de 79 médicos em jun/2026 (patamar de 78,25, média de 4 registros, arredondado para cima)'}}}]}]});
  assert.deepEqual(doPatamar.territorios[0].cenarios[0].planejamento.meta, {tipo: 'patamar', valor: 79, patamar: 78.25, registros: 4,
    rotulo: 'Meta hipotética: voltar ao patamar de 79 médicos em jun/2026 (patamar de 78,25, média de 4 registros, arredondado para cima)'});
  assert.deepEqual([m0.comparacoes, m0.planejamento.estado, m0.planejamento.porEvento, m0.planejamento.intervencao, m0.planejamento.texto, m0.hipotetico],
    [[], 'nao_alcancavel', null, null, null, null], 'sem resultado, nenhum número de médicos aparece');
  assert.deepEqual(c1.hipotetico, {rotulo: 'hipótese do cenário', data: '202606', valor: 12, inteiro: 12, classe: null, impactoPct: 8.333333333333334, naFaixa: null});
  assert.deepEqual([lida.referencias, lida.comparacao], [[{id: 'r1', rotulo: 'BELEM (PA)', tipo: 'fixa', territorio: 'code:150140',
    unidade: 'médicos registrados no município', estado: 'calculada', descricao: 'fixa: o valor de jun/2024 mantido', motivo: null}],
    {metrica: 'quantidade', forma: 'diferenca', populacaoPctAoAno: null, hipoteseDePopulacao: null}]);
  const antiga = S.normalizarSimulador(BRUTO).territorios[0].cenarios[0];   // uma resposta sem os campos da etapa 5
  assert.deepEqual([antiga.comparacoes, antiga.planejamento, antiga.hipotetico, S.normalizarSimulador(null).referencias, S.normalizarSimulador(null).comparacao],
    [[], null, null, [], {metrica: 'quantidade', forma: 'diferenca', populacaoPctAoAno: null, hipoteseDePopulacao: null}]);
  // "Usar como intervenção deste cenário": por comando da pessoa, o acréscimo calculado entra nas intervenções, e o planejamento sai.
  const daTela = {...S.novoCenario('c1', 'Cenário 1'), planejamento: S.novoPlano('202501')};
  assert.deepEqual(S.comOPlanoComoIntervencao(daTela, c1.planejamento), {id: 'c1', nome: 'Cenário 1', metodo: 'padrao', taxaManual: '', janela: null,
    intervencoes: [{tipo: 'acrescimo', quantidade: '5', em: '202501', periodica: true, ate: '202601', aCadaMeses: '12', permanencia: '97,5'}]});
  assert.equal(S.comOPlanoComoIntervencao(daTela, m0.planejamento), daTela, 'sem resultado calculado, nada muda');
  assert.equal(S.comOPlanoComoIntervencao(daTela, null), daTela);
  const cheio = {...daTela, intervencoes: Array.from({length: S.MAX_INTERVENCOES}, () => S.novaIntervencao('202501'))};
  assert.equal(S.comOPlanoComoIntervencao(cheio, c1.planejamento), cheio, 'no limite de intervenções, nada muda');
});

test('os níveis no cenário: só "Poucos médicos", como hipótese do cenário rotulada pelo motor, e só quando é pertinente', () => {
  const h = extra => ({rotulo: 'hipótese do cenário', data: '202606', valor: 1.19, inteiro: 1, classe: 'critico', impactoPct: 100,
    naFaixa: {inferior: 'critico', superior: 'elevado'}, ...extra});
  // Proposta V3, seção C.6: "seria Crítico em 'Poucos médicos'"; quando a faixa cruza um limite, "pode ficar entre…", sem escolher um só.
  assert.equal(S.textoDaHipotese(h()), 'Hipótese do cenário (não é um sinal observado): com 1 médico em jun/2026, o território seria Crítico em “Poucos médicos” ' +
    '(a saída de 1 tiraria 100,0%). Pela faixa do cenário, pode ficar entre elevado e crítico. Os limites são os limites fixos do Detector; os sinais comparados ' +
    'com a base valem só para registros reais.');
  assert.equal(S.textoDaHipotese(h({inteiro: 12, valor: 12, classe: null, impactoPct: 8.3333, naFaixa: null})), 'Hipótese do cenário (não é um sinal observado): ' +
    'com 12 médicos em jun/2026, o território não teria alerta em “Poucos médicos” (a saída de 1 tiraria 8,3%). Os limites são os limites fixos do Detector; os ' +
    'sinais comparados com a base valem só para registros reais.');
  assert.ok(S.textoDaHipotese(h({inteiro: 6018, valor: 6017.98, classe: null, impactoPct: 0.0166, naFaixa: {inferior: null, superior: null}}))
    .startsWith('Hipótese do cenário (não é um sinal observado): com 6.018 médicos em jun/2026, o território não teria alerta em “Poucos médicos”. O'));
  assert.ok(S.textoDaHipotese(h({inteiro: 4, valor: 4, classe: 'moderado', impactoPct: 25, naFaixa: {inferior: 'elevado', superior: null}}))
    .includes('seria Moderado em “Poucos médicos” (a saída de 1 tiraria 25,0%). Pela faixa do cenário, pode ficar entre sem alerta e elevado.'));
  assert.deepEqual(['moderado', 'elevado', 'critico', null].map(S.nivelNoCenario), ['moderado', 'elevado', 'crítico', 'sem alerta']);
  // O painel fica fora da tela quando o sinal não tem o que dizer (um território grande, sem nível nem nos limites da faixa).
  assert.deepEqual([null, h(), h({inteiro: 12, classe: null, naFaixa: null}), h({inteiro: 6018, classe: null, naFaixa: {inferior: null, superior: null}}),
    h({inteiro: 30, classe: null, naFaixa: {inferior: 'moderado', superior: null}}), h({inteiro: 21, classe: null, naFaixa: null})].map(S.hipotesePertinente),
    [false, true, true, false, true, false]);
});

test('CSV das comparações e o cenário exportado levam as referências, a métrica e o planejamento', () => {
  const lida = S.normalizarSimulador({...BRUTO_5, comparacao: {metrica: 'taxa', hipotese_de_populacao: 'constante: a população de jun/2024 em todas as datas simuladas'}});
  const csv = S.csvDasComparacoes(lida);
  assert.equal(csv.charCodeAt(0), 0xFEFF);
  const linhas = csv.slice(1).split('\r\n');
  assert.equal(linhas.length, 5, 'o cabeçalho, as 2 datas da referência calculada, a referência sem valor e o fim');
  assert.equal(linhas[0], 'Identificador;Território;Cenário;Referência;Tipo da referência;O que é a referência;Métrica;Data;Valor do território;Valor da referência;' +
    'Diferença (referência − território);Razão (território ÷ referência);Índice (100 = referência);Alcance no horizonte simulado;Data do alcance;Avisos;' +
    'Hipótese de população;Versão do método;Versão da base');
  assert.equal(linhas[2], 'code:130340;PARINTINS (AM);Cenário 1;BELEM (PA);fixa;fixa: o valor de jun/2024 mantido;quantidade;202606;12;50;38;0,24;24;' +
    'não alcança no horizonte simulado;;A referência contém o território.;constante: a população de jun/2024 em todas as datas simuladas;SIMULADOR-CENARIOS/V3/1;abc');
  assert.equal(linhas[3], 'code:130340;PARINTINS (AM);Cenário 1;Meta;valor;A referência não tem valor nas datas do cenário.;quantidade;;;;;;;;;;' +
    'constante: a população de jun/2024 em todas as datas simuladas;SIMULADOR-CENARIOS/V3/1;abc', 'sem valor inventado');
  // O CSV dos resultados diz a meta, o número de médicos por evento (ou por que não há) e o nível da hipótese do cenário.
  const resultados = S.csvDoSimulador(lida).slice(1).split('\r\n');
  assert.ok(resultados[1].endsWith(';Meta hipotética: 21 médicos em jun/2026;5;2;sem alerta;SIMULADOR-CENARIOS/V3/1;abc'));
  assert.ok(resultados[2].endsWith(';Meta hipotética: 20 médicos em jun/2026;nao_alcancavel;1;;SIMULADOR-CENARIOS/V3/1;abc'));
  // Exportar e importar: o Brasil, as referências (a que aponta para um conjunto que não veio fica de fora), a métrica e o planejamento.
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:1', 'code:2']}]}, '202406');
  const cheio = {...inicial, local: S.comOBrasil(inicial.local, true), acompanha: false, metrica: 'taxa', referencias: [R1, R2, R3, R4, {...R4, id: 'r9', alvo: 'g9'}],
    doDetector: {rotulo: 'x', fim: '202406', sinais: [], recuperacao: true},
    cenarios: [{...inicial.cenarios[0], planejamento: {...S.novoPlano('202506'), meta: 'referencia', referencia: 'r1'}}]};
  const exportado = S.exportarCenario(cheio, {versaoDoMetodo: 'v', versaoDaBase: 'abc', ultimoRegistro: '202406', quando: 'q'});
  assert.deepEqual([JSON.parse(exportado).metrica, JSON.parse(exportado).referencias.length, JSON.parse(exportado).selecao_local.brasil], ['taxa', 5, true]);
  const {config} = S.importarCenario(exportado);
  assert.deepEqual(config, {local: cheio.local, janela: null, horizonte: '202606', modo: 'simples', cenarios: cheio.cenarios, referencias: [R1, R2, R3, R4], metrica: 'taxa'});
  assert.deepEqual(S.pedidoDoSimulador(config), S.pedidoDoSimulador({...cheio, referencias: [R1, R2, R3, R4]}), 'o cenário importado pede o mesmo cálculo');
  // No modo avançado, o pedido do cenário importado leva as referências e a métrica (o modo simples não as leva): o mesmo cálculo de antes de exportar.
  const noAvancado = S.pedidoDoSimulador({...config, modo: 'avancado'});
  assert.deepEqual(noAvancado, S.pedidoDoSimulador({...cheio, modo: 'avancado', referencias: [R1, R2, R3, R4]}));
  assert.deepEqual([noAvancado.referencias.map(ref => ref.id), noAvancado.comparacao, noAvancado.brasil, 'referencias' in S.pedidoDoSimulador(config)],
    [['r1', 'r2', 'r3', 'r4'], {metrica: 'taxa'}, true, false]);
  // Um arquivo com partes inválidas: a referência sem alvo sai, o tipo desconhecido vira fixa, e a meta desconhecida vira um valor a informar.
  const tolerante = S.importarCenario(JSON.stringify({formato: S.FORMATO_DO_CENARIO, horizonte: '202606', selecao_local: {municipios: ['code:1'], brasil: 'sim'},
    referencias: [{tipo: 'valor'}, {alvo: 'uf:35', tipo: 'x', rotulo: 'SP'}, {tipo: 'fixa'}, 7], metrica: 'outra',
    cenarios: [{planejamento: {meta: 'x', em: '202506'}}, {planejamento: 'nao'}]})).config;
  assert.deepEqual([tolerante.local, tolerante.referencias, 'metrica' in tolerante, tolerante.cenarios.map(item => item.planejamento)], [
    {municipios: ['code:1'], estados: [], conjuntos: []},
    [{id: 'r1', alvo: 'valor', rotulo: 'Referência', tipo: 'valor', valor: ''}, {id: 'r2', alvo: 'uf:35', rotulo: 'SP', tipo: 'fixa', valor: ''}], false,
    [{meta: 'valor', valor: '', referencia: '', em: '202506', periodica: false, ate: '202506', aCadaMeses: '12', permanencia: '100'}, undefined]]);
  assert.equal(S.pendenciaDoPedido(tolerante), 'Informe a meta: um número acima de zero.', 'nada é calculado com a meta em branco');
});

// ------------------------------------------------------------------------------------------------ Proposta V3 (comando V23, Parte C)
test('modo simples: o que testar — só continuar, acrescentar, retirar ou chegar a uma meta; o que foi digitado fica ao trocar', () => {
  assert.deepEqual(S.TESTES, [{chave: 'continuar', rotulo: 'Só continuar como vinha'}, {chave: 'acrescentar', rotulo: 'Acrescentar'}, {chave: 'retirar', rotulo: 'Retirar'},
    {chave: 'meta', rotulo: 'Chegar a uma meta'}]);
  assert.equal(/médic|estado|municíp/i.test(JSON.stringify(S.TESTES)), false, 'os nomes valem para qualquer base');
  const c1 = S.novoCenario('c1', 'Cenário 1');
  // Acrescentar: uma intervenção só, numa data, na data proposta (um ano depois do último registro). O jeito de projetar volta ao
  // escolhido pela base, sem taxa nem janela próprias (o que tiver vindo do modo avançado).
  const acrescentar = S.comOTeste({...c1, metodo: 'M1', taxaManual: '2', janela: {inicio: '201906', fim: '202406'}}, 'acrescentar', '202506');
  assert.deepEqual(acrescentar, {id: 'c1', nome: 'Cenário 1', metodo: 'padrao', taxaManual: '', janela: null,
    intervencoes: [{tipo: 'acrescimo', quantidade: '1', em: '202506', periodica: false, ate: '202506', aCadaMeses: '12', permanencia: '100'}]});
  // Retirar, depois de digitar a quantidade e a data: as duas ficam (a permanência também), e a repetição sai (uma data só).
  const digitado = {...acrescentar, intervencoes: [{...acrescentar.intervencoes[0], quantidade: '7', em: '202601', periodica: true, ate: '202801', aCadaMeses: '6', permanencia: '90'}]};
  const retirar = S.comOTeste(digitado, 'retirar', '202506');
  assert.deepEqual(retirar.intervencoes, [{tipo: 'retirada', quantidade: '7', em: '202601', periodica: false, ate: '202601', aCadaMeses: '6', permanencia: '90'}]);
  assert.deepEqual(S.comOTeste(retirar, 'acrescentar', '202506').intervencoes, [{...retirar.intervencoes[0], tipo: 'acrescimo'}], 'e de volta');
  // Chegar a uma meta: a meta em branco (a informar), com o acréscimo na data que já estava digitada.
  const meta = S.comOTeste(retirar, 'meta', '202506');
  assert.deepEqual(meta, {id: 'c1', nome: 'Cenário 1', metodo: 'padrao', taxaManual: '', janela: null, intervencoes: [],
    planejamento: {meta: 'valor', valor: '', referencia: '', em: '202601', periodica: false, ate: '202601', aCadaMeses: '12', permanencia: '100'}});
  assert.deepEqual(S.comOTeste(c1, 'meta', '202506').planejamento, S.novoPlano('202506'), 'sem nada digitado, a data proposta');
  // A meta digitada fica quando a pessoa marca "Chegar a uma meta" de novo; ao passar para "Acrescentar", a data dela fica.
  const comMeta = {...meta, planejamento: {...meta.planejamento, valor: '40'}};
  assert.equal(S.comOTeste(comMeta, 'meta', '202506').planejamento, comMeta.planejamento);
  assert.deepEqual(S.comOTeste(comMeta, 'acrescentar', '202506').intervencoes, [S.novaIntervencao('202601')]);
  assert.equal('planejamento' in S.comOTeste(comMeta, 'acrescentar', '202506'), false, 'um teste de cada vez');
  // Só continuar como vinha: sem intervenção e sem meta.
  assert.deepEqual(S.comOTeste(comMeta, 'continuar', '202506'), c1);
  assert.deepEqual(S.comOTeste(digitado, 'continuar', '202506'), c1);
  // O teste em uso, pelo que o cenário tem: a meta, a primeira intervenção ou nada.
  assert.deepEqual([c1, acrescentar, retirar, meta, comMeta].map(S.testeDoCenario), ['continuar', 'acrescentar', 'retirar', 'meta', 'meta']);
  // O pedido de cada teste: os números digitados, numa data, com permanência total (a repetição e a permanência são do modo
  // avançado e não vão no pedido do modo simples); a meta, com a data do acréscimo. Em branco, falta a meta.
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  const doPedido = cenario => S.pedidoDoSimulador({...inicial, cenarios: [cenario]}).cenarios[0];
  assert.deepEqual([acrescentar, retirar, comMeta, c1].map(doPedido), [
    {id: 'c1', nome: 'Cenário 1', metodo: 'padrao', intervencoes: [{tipo: 'acrescimo', quantidade: 1, em: '202506'}]},
    {id: 'c1', nome: 'Cenário 1', metodo: 'padrao', intervencoes: [{tipo: 'retirada', quantidade: 7, em: '202601'}]},
    {id: 'c1', nome: 'Cenário 1', metodo: 'padrao', planejamento: {meta: {tipo: 'valor', valor: 40}, em: '202601'}},
    {id: 'c1', nome: 'Cenário 1', metodo: 'padrao'}]);
  assert.deepEqual([meta, comMeta, acrescentar, {...acrescentar, intervencoes: [{...acrescentar.intervencoes[0], quantidade: ''}]}]
    .map(cenario => S.pendenciaDoPedido({...inicial, cenarios: [cenario]})),
    ['Informe a meta: um número acima de zero.', null, null, 'Informe quantos entram ou saem em cada intervenção.']);
});

test('modo simples: os territórios da seleção local, o território em análise e o pedido com um território só', () => {
  const local = {municipios: ['code:130260', 'code:130420'], estados: ['15', '41'], conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 2},
    {id: 'g2', rotulo: 'Conjunto Sul', membros: ['uf:41', 'uf:42']}], brasil: true};
  const nomes = {unidade: id => 'M ' + id.slice(5), grupo: prefixo => 'E ' + prefixo, todo: 'Tudo'};
  // Na ordem do pedido, com o identificador que o motor usa: as unidades, os grupos de cima como unidade, os conjuntos e o todo.
  assert.deepEqual(S.territoriosDaSelecaoLocal(local, nomes), [{id: 'code:130260', rotulo: 'M 130260'}, {id: 'code:130420', rotulo: 'M 130420'}, {id: 'uf:15', rotulo: 'E 15'},
    {id: 'uf:41', rotulo: 'E 41'}, {id: 'g1', rotulo: 'Conjunto Par'}, {id: 'g2', rotulo: 'Conjunto Sul'}, {id: 'br', rotulo: 'Tudo'}]);
  assert.deepEqual(S.territoriosDaSelecaoLocal(S.SELECAO_LOCAL_VAZIA, nomes), []);
  // A seleção só com um território; o que não está nela (ou nenhum) deixa a seleção como está.
  assert.deepEqual(['code:130420', 'uf:41', 'g2', 'br'].map(id => S.soOTerritorio(local, id)), [{municipios: ['code:130420'], estados: [], conjuntos: []},
    {municipios: [], estados: ['41'], conjuntos: []}, {municipios: [], estados: [], conjuntos: [{id: 'g2', rotulo: 'Conjunto Sul', membros: ['uf:41', 'uf:42']}]},
    {municipios: [], estados: [], conjuntos: [], brasil: true}]);
  for (const id of [undefined, '', 'code:999', 'uf:99', 'g9']) assert.equal(S.soOTerritorio(local, id), local, String(id));
  const semBrasil = S.comOBrasil(local, false);
  assert.equal(S.soOTerritorio(semBrasil, 'br'), semBrasil, 'o Brasil só vale quando está na seleção local');
  // O primeiro da seleção, na ordem do pedido: uma unidade; sem unidades, um grupo como unidade; depois, um conjunto; por fim, o todo.
  assert.deepEqual([local, {...local, municipios: []}, {...local, municipios: [], estados: []}, {municipios: [], estados: [], conjuntos: [], brasil: true},
    S.SELECAO_LOCAL_VAZIA].map(S.primeiroDaSelecao), ['code:130260', 'uf:15', 'g1', 'br', undefined]);
  // O pedido do modo simples leva só o território em análise (sem escolha, o primeiro), nunca a seleção local inteira.
  const config = {...S.configInicial(local, '202406')};
  const cenarios = [{id: 'c1', nome: 'Cenário 1', metodo: 'padrao'}, {id: 'm0', nome: 'Persistência (referência)', metodo: 'M0'}];
  assert.deepEqual(S.pedidoDoSimulador(config), {base: {municipios: {todos: false, estados: [], ids: ['code:130260']}}, horizonte: '202606', cenarios});
  assert.deepEqual(['code:130420', 'uf:41', 'g1', 'br'].map(territorio => S.pedidoDoSimulador({...config, territorio})), [
    {base: {municipios: {todos: false, estados: [], ids: ['code:130420']}}, horizonte: '202606', cenarios}, {estados_unidade: ['41'], horizonte: '202606', cenarios},
    {conjuntos: [{id: 'g1', rotulo: 'Par', membros: ['code:110001', 'code:110002'], versao: 2}], horizonte: '202606', cenarios},
    {brasil: true, horizonte: '202606', cenarios}]);
  // No modo avançado, a seleção local inteira, como antes: o território do modo simples não muda o pedido.
  assert.deepEqual(S.pedidoDoSimulador({...config, modo: 'avancado', territorio: 'uf:41'}), {base: {municipios: {todos: false, estados: [], ids: ['code:130260', 'code:130420']}},
    estados_unidade: ['15', '41'], conjuntos: local.conjuntos, brasil: true, horizonte: '202606', cenarios});
  // A configuração inicial não fixa o território nem a faixa: valem o primeiro da seleção local e 8 em cada 10.
  assert.deepEqual(['territorio' in config, 'faixa' in config], [false, false]);
});

test('o pedido leva a faixa só quando não é a de 8 em cada 10 e, numa planilha, o que descreve a base', () => {
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  assert.deepEqual([5, 8, 9, undefined].map(faixa => S.pedidoDoSimulador({...inicial, faixa}).faixa), [5, undefined, 9, undefined]);
  assert.deepEqual([5, 8, 9, undefined].map(faixa => 'faixa' in S.pedidoDoSimulador({...inicial, faixa})), [true, false, true, false]);
  assert.deepEqual(S.pedidoDoSimulador({...inicial, modo: 'avancado', faixa: 9}).faixa, 9, 'nos dois modos');
  // Numa planilha enviada, o pedido leva os nomes, as premissas e a categoria dela, como no pedido do painel; o que é do Simulador prevalece.
  const daBase = {rotulos: {profissional: 'enfermeiro'}, premissas: {x: 1}, categoria: 'ENFERMAGEM'};
  assert.deepEqual(S.pedidoDoSimulador(inicial, daBase), {rotulos: {profissional: 'enfermeiro'}, premissas: {x: 1}, categoria: 'ENFERMAGEM',
    base: {municipios: {todos: false, estados: [], ids: ['code:130260']}}, horizonte: '202606',
    cenarios: [{id: 'c1', nome: 'Cenário 1', metodo: 'padrao'}, {id: 'm0', nome: 'Persistência (referência)', metodo: 'M0'}]});
  assert.deepEqual(S.pedidoDoSimulador(inicial, {horizonte: 'x', categoria: 'C'}).horizonte, '202606');
  assert.deepEqual(S.pedidoDoSimulador(inicial, undefined), S.pedidoDoSimulador(inicial), 'na base do Brasil, nada a mais');
});

test('as competências de qualquer base no formato das ferramentas: AAAAMM, ou AAAA00 numa planilha só com anos', () => {
  assert.deepEqual(S.competenciasDasFerramentas(['202406', '2024-06', '2024-06-30']), ['202406'], 'as três formas da mesma data, uma vez só');
  assert.deepEqual(S.competenciasDasFerramentas(['2024']), ['202400']);
  assert.deepEqual(S.competenciasDasFerramentas(['2024', '2022', '2023', '2022']), ['202200', '202300', '202400'], 'em ordem, sem repetir');
  // O ano que a planilha traz como número com casas ("2023.0") também é um ano; "2024.5" e "2020." não são datas.
  assert.deepEqual(S.competenciasDasFerramentas(['2023.0', '2022', '2021.00', '2024.5', '2020.']), ['202100', '202200', '202300']);
  // O que não é data fica de fora: texto, mês que não existe, ano fora do alcance e formas incompletas.
  assert.deepEqual(S.competenciasDasFerramentas(['2024-06-30', 'x', '', '2023-13', '202313', '2023-01', ' 2022-12 ', '1799', '2200', '20240', '2024-6', '202401', '202406']),
    ['202212', '202301', '202401', '202406']);
  assert.deepEqual(S.competenciasDasFerramentas([]), []);
});

test('a resposta V3: o jeito escolhido pela base, a faixa "N em cada 10", os "Entenda", os nomes da base e a escolha de cada nível', () => {
  const lida = S.normalizarSimulador(BRUTO);
  const [calculado, retirada] = lida.territorios[0].cenarios;
  // A fonte: os nomes da base (como o motor os manda) e de onde ela vem.
  assert.deepEqual(lida.fonte, {base: 'Brasil', categoria: 'MEDICINA', versao: 'abc', primeira: '201401', ultima: '202406', rotulos: ROTULOS_DO_BRASIL, origem: 'brasil',
    formas: S.FORMAS_DO_BRASIL, ancora: '06'});   // as formas com artigo e o mês da série anual têm teste próprio, mais abaixo
  assert.deepEqual(S.NOMES_DO_BRASIL, ROTULOS_DO_BRASIL);
  // A faixa do cenário: N em cada 10, até quantos anos vai, a conferência da data final e como foi montada; sem faixa, o padrão de leitura.
  assert.deepEqual(calculado.faixa, {estado: 'disponivel', motivo: null, rotulo: 'a margem observada no passado da base, em municípios do mesmo porte; acompanha a intervenção',
    em10: 8, ateAnos: 4, conferencia: 'conferida', como: 'propria'});
  assert.deepEqual(retirada.faixa, {estado: 'indisponivel', motivo: null, rotulo: null, em10: 8, ateAnos: null, conferencia: null, como: null});
  // Os "Entenda" do resultado: os textos e os exemplos são os do motor; sem cenário calculado, não há.
  assert.deepEqual(calculado.entenda, {jeito: {texto: 'O cenário parte do último registro usado (jun/2024) e soma o crescimento recente do estado.',
      exemplo: 'De 51 médicos em jun/2024, a base do cenário vai a 52,7 um ano depois, sem contar intervenções.'},
    faixa: {texto: 'Refizemos este tipo de projeção em datas passadas, para territórios do mesmo porte.', exemplo: 'Entre 48 e 75 médicos na data final.'}});
  assert.deepEqual([retirada.entenda, retirada.metodo.escolhidoPelaBase, retirada.metodo.eOEscolhido], [null, null, false]);
  // A retroprojeção: a faixa pedida e, por nível, o jeito que a base escolheu, com a frase do motor e os que foram comparados.
  assert.equal(lida.retroprojecao.em10, 8);
  assert.deepEqual(Object.keys(lida.retroprojecao.escolhas), ['municipios', 'estados']);
  assert.deepEqual(lida.retroprojecao.escolhas.municipios, {metodo: 'M0d', rotulo: 'persistência com o crescimento recente do estado', motivo: 'escolhido',
    texto: 'Para os municípios, a base escolheu a persistência com o crescimento recente do estado: …',
    candidatos: [{metodo: 'M1', rotulo: 'taxa composta da janela', frenteAoM0: 1.0154, menosErroEm: 2, combinacoes: 22, vale: false},
      {metodo: 'M0d', rotulo: 'persistência com o crescimento recente do estado', frenteAoM0: 0.7136, menosErroEm: 22, combinacoes: 22, vale: true}]});
  assert.deepEqual([lida.retroprojecao.escolhas.estados.metodo, lida.retroprojecao.escolhas.estados.candidatos[0]],
    ['M1', {metodo: 'M1', rotulo: '', frenteAoM0: null, menosErroEm: 0, combinacoes: 0, vale: false}], 'sem número, nenhum é inventado');
  // Outra base: os nomes dela (o que faltar ou vier errado fica com o nome padrão) e a origem "planilha".
  const OUTRA = {profissional: 'enfermeiro', profissionais: 'enfermeiros', unidade: 'distrito', unidades: 'distritos', grupo: 'província', grupos: 'províncias', todo: 'Angola'};
  const daPlanilha = S.normalizarSimulador({...BRUTO, fonte: {...BRUTO.fonte, base: 'Planilha enviada', categoria: 'ENFERMAGEM', rotulos: OUTRA, origem: 'planilha'}}).fonte;
  assert.deepEqual([daPlanilha.rotulos, daPlanilha.origem, daPlanilha.base], [OUTRA, 'planilha', 'Planilha enviada']);
  assert.deepEqual(S.normalizarSimulador({...BRUTO, fonte: {...BRUTO.fonte, rotulos: {profissionais: 'enfermeiros', grupo: 7}, origem: 'x'}}).fonte.rotulos,
    {...ROTULOS_DO_BRASIL, profissionais: 'enfermeiros'});
  // Uma resposta sem os campos da V3 (ou vazia) não quebra a tela: os nomes do Brasil, 8 em cada 10, nenhuma escolha, e a faixa de
  // cada ponto é "conferida" ou "provisória" pelo campo de antes (`validada`).
  const vazia = S.normalizarSimulador(null);
  assert.deepEqual([vazia.fonte.rotulos, vazia.fonte.origem, vazia.retroprojecao], [ROTULOS_DO_BRASIL, 'brasil', {origens: [], em10: 8, escolhas: {}, faixas: [], tabela: [], bruta: {}}]);
  const deAntes = S.normalizarSimulador({territorios: [{id: 'code:1', cenarios: [{id: 'c1', estado: 'calculado', metodo: {pedido: 'padrao', usado: 'M0d', provisorio: true},
    parametros: {n0: 5, origem: '202406'}, faixa: {estado: 'disponivel', motivo: null, rotulo: 'x'},
    trajetoria: [{data: '202606', anos: 2, base: 6, intervencao: 0, total: 6, faixa: {inferior: 4, superior: 9, anos: 2, validada: true}},
      {data: '202806', anos: 4, base: 7, intervencao: 0, total: 7, faixa: {inferior: 4, superior: 12, anos: 4, validada: false}}],
    final: {data: '202806', base: 7, intervencao: 0, total: 7, faixa: {inferior: 4, superior: 12, anos: 4, validada: false}}}]}]}).territorios[0].cenarios[0];
  assert.deepEqual([deAntes.metodo.provisorio, deAntes.metodo.escolhidoPelaBase, deAntes.metodo.eOEscolhido, deAntes.entenda, deAntes.faixa.em10, deAntes.faixa.ateAnos],
    [true, null, false, null, 8, null]);
  assert.deepEqual(deAntes.trajetoria.map(ponto => [ponto.faixa.estado, ponto.faixa.como]), [['conferida', null], ['provisoria', null]]);
  assert.ok(S.textoDaFaixa(deAntes).startsWith('Faixa de 8 em cada 10 em jun/2028: de 4 a 12 médicos.') && S.textoDaFaixa(deAntes).includes(' Faixa provisória: '));
});

test('os três números do modo simples: no último registro, na data final e a diferença — ou, na meta, quanto acrescentar', () => {
  const [calculado, retirada, naoSeAplica] = S.normalizarSimulador(BRUTO).territorios[0].cenarios;
  const inicio = [{rotulo: 'No último registro (jun/2024)', valor: '51'}, {rotulo: 'Em jun/2026', valor: '59'}];
  // 1. Sem meta: a diferença entre os dois números inteiros da tela, com o sinal e a palavra no singular ou no plural.
  assert.deepEqual(S.tresNumeros(calculado), [...inicio, {rotulo: 'Diferença', valor: '+8 médicos'}]);
  const com = total => S.tresNumeros({...calculado, final: {...calculado.final, total}}).slice(1);
  assert.deepEqual([52.4, 49.6, 51.2].map(com), [[{rotulo: 'Em jun/2026', valor: '52'}, {rotulo: 'Diferença', valor: '+1 médico'}],
    [{rotulo: 'Em jun/2026', valor: '50'}, {rotulo: 'Diferença', valor: '−1 médico'}], [{rotulo: 'Em jun/2026', valor: '51'}, {rotulo: 'Diferença', valor: '0 médicos'}]]);
  assert.deepEqual(S.tresNumeros({...calculado, parametros: {n0: 4730, origem: '202406'}, final: {...calculado.final, total: 5335.27}}),
    [{rotulo: 'No último registro (jun/2024)', valor: '4.730'}, {rotulo: 'Em jun/2026', valor: '5.335'}, {rotulo: 'Diferença', valor: '+605 médicos'}]);
  // 2. Com a meta calculada: quanto seria preciso acrescentar (o número do motor: por evento vezes os eventos), no lugar da diferença.
  const plano = {estado: 'calculado', motivo: null, meta: {tipo: 'valor', valor: 70, rotulo: 'Meta hipotética: 70 médicos em jun/2026'}, semOPlano: 58.5189, eventos: 1,
    datas: ['202501'], porEvento: 12, total: 12, teoricoPorEvento: 11.48, resultado: 70.5189, texto: 'Meta…', intervencao: null};
  assert.deepEqual(S.tresNumeros({...calculado, planejamento: plano}), [...inicio, {rotulo: 'Para chegar à meta', valor: 'precisaria acrescentar 12'}]);
  assert.deepEqual(S.tresNumeros({...calculado, planejamento: {...plano, eventos: 4, porEvento: 387}})[2], {rotulo: 'Para chegar à meta', valor: 'precisaria acrescentar 1.548'});
  // 3. Com a meta já alcançada no cenário: nada a acrescentar. Sem resultado (meta não alcançável), fica a diferença: nenhum número é inventado.
  assert.deepEqual(S.tresNumeros({...calculado, planejamento: {...plano, estado: 'ja_alcancada', porEvento: 0, total: 0}}),
    [...inicio, {rotulo: 'Para chegar à meta', valor: 'nada a acrescentar'}]);
  assert.deepEqual(S.tresNumeros({...calculado, planejamento: {...plano, estado: 'nao_alcancavel', porEvento: null, total: null}})[2], {rotulo: 'Diferença', valor: '+8 médicos'});
  // Sem cenário calculado, não há números. Numa base com um registro por ano, as datas são anos.
  assert.deepEqual([S.tresNumeros(retirada), S.tresNumeros(naoSeAplica)], [[], []]);
  assert.deepEqual(S.tresNumeros({...calculado, parametros: {n0: 51, origem: '202400'}, final: {...calculado.final, data: '202600'}}).map(item => item.rotulo),
    ['No último registro (2024)', 'Em 2026', 'Diferença']);
});

test('a faixa em palavras: conferida, provisória, indisponível com o motivo e além do último prazo', () => {
  const [calculado, retirada] = S.normalizarSimulador(BRUTO).territorios[0].cenarios;
  const meio = ', o número observado ficou dentro dessa margem; ela acompanha a intervenção.';
  const provisoria = ' Faixa provisória: ainda não deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do esperado.';
  const comAFaixa = parte => ({...calculado, final: {...calculado.final, faixa: {...calculado.final.faixa, ...parte}}});
  // 1. Conferida: a faixa cobriu o esperado nos dados que vieram depois.
  assert.equal(S.textoDaFaixa(calculado), 'Faixa de 8 em cada 10 em jun/2026: de 48,2 a 74,9 médicos. No passado da base, em 8 de cada 10 casos de territórios do mesmo porte' +
    meio + ' Conferida com o que veio depois.');
  // 2. Provisória: ainda não deu para conferir (ou a conferência ficou um pouco abaixo do esperado).
  assert.equal(S.textoDaFaixa(comAFaixa({anos: 4, validada: false, estado: 'provisoria'})), 'Faixa de 8 em cada 10 em jun/2026: de 48,2 a 74,9 médicos. No passado da ' +
    'base, em 8 de cada 10 casos de territórios do mesmo porte' + meio + provisoria);
  // De quem é a margem: do mesmo porte, com os portes vizinhos, com portes menores ou, num conjunto, do porte da soma (aproximação).
  assert.ok(S.textoDaFaixa(comAFaixa({como: 'vizinhas'})).includes('casos de territórios do mesmo porte e dos portes vizinhos' + meio + ' Conferida com o que veio depois.'));
  assert.ok(S.textoDaFaixa(comAFaixa({como: 'portes_menores', estado: 'provisoria', validada: false})).endsWith('casos de territórios do mesmo porte e de portes menores' +
    meio + provisoria));
  assert.equal(S.textoDaFaixa(calculado, true), 'Faixa de 8 em cada 10 (aproximação) em jun/2026: de 48,2 a 74,9 médicos. No passado da base, em 8 de cada 10 casos de ' +
    'territórios com o porte desta soma (uma aproximação para o conjunto)' + meio + ' Conferida com o que veio depois.');
  // 3. Indisponível, com o motivo do motor (sem motivo, só "indisponível"): nada é extrapolado.
  const semCasos = 'A faixa de 8 em cada 10 pede 200 casos por prazo, e esta base tem 189 em 1 ano para o porte deste território, mesmo juntando os ' +
    'portes vizinhos e os menores.';
  const semFaixa = {estado: 'indisponivel', motivo: semCasos, rotulo: null, em10: 8, ateAnos: null, conferencia: null, como: null};
  const semFinal = {...calculado, final: {...calculado.final, faixa: null}};
  assert.equal(S.textoDaFaixa({...semFinal, faixa: semFaixa}), 'Faixa de 8 em cada 10: indisponível. ' + semCasos);
  assert.equal(S.textoDaFaixa({...semFinal, faixa: {...semFaixa, motivo: null}}), 'Faixa de 8 em cada 10: indisponível.');
  assert.equal(S.textoDaFaixa(retirada), 'Faixa de 8 em cada 10: indisponível.', 'sem cenário calculado');
  // 4. Além do último prazo com casos suficientes: a faixa existe, mas não nesta data.
  assert.equal(S.textoDaFaixa(semFinal), 'Faixa de 8 em cada 10: indisponível nesta data: ela vai só até 4 anos depois do último registro usado.');
  assert.equal(S.textoDaFaixa({...semFinal, faixa: {...calculado.faixa, ateAnos: 2}}),
    'Faixa de 8 em cada 10: indisponível nesta data: ela vai só até 2 anos depois do último registro usado.');
  // A faixa pedida: 5 ou 9 em cada 10, no nome e na frase.
  assert.ok(S.textoDaFaixa({...calculado, faixa: {...calculado.faixa, em10: 5}}).startsWith('Faixa de 5 em cada 10 em jun/2026: de 48,2 a 74,9 médicos. No passado da base, ' +
    'em 5 de cada 10 casos de territórios do mesmo porte'));
  assert.equal(S.textoDaFaixa({...semFinal, faixa: {...semFaixa, em10: 9, motivo: 'Sem casos.'}}), 'Faixa de 9 em cada 10: indisponível. Sem casos.');
});

test('a faixa que vai só até 1 ano diz "1 ano", no singular', () => {
  // Numa base com poucas origens de retroprojeção (uma planilha curta), a faixa pode ir só até 1 ano. O aviso do motor já diz
  // "1 ano"; a frase da tela precisa dizer o mesmo, e não "1 anos".
  const [calculado] = S.normalizarSimulador(BRUTO).territorios[0].cenarios;
  assert.equal(S.textoDaFaixa({...calculado, faixa: {...calculado.faixa, ateAnos: 1}, final: {...calculado.final, faixa: null}}),
    'Faixa de 8 em cada 10: indisponível nesta data: ela vai só até 1 ano depois do último registro usado.');
});

test('os textos com os nomes de outra base: nada de "médicos", "município" ou "estado"', () => {
  const OUTRA = {profissional: 'enfermeiro', profissionais: 'enfermeiros', unidade: 'distrito', unidades: 'distritos', grupo: 'província', grupos: 'províncias', todo: 'Angola'};
  const [calculado] = S.normalizarSimulador(BRUTO).territorios[0].cenarios;
  const somado = {...calculado, metodo: {...calculado.metodo, soma: 'soma das projeções dos membros'}};
  const hipotese = {rotulo: 'hipótese do cenário', data: '202606', valor: 1.19, inteiro: 1, classe: 'critico', impactoPct: 100, naFaixa: {inferior: 'critico', superior: 'elevado'}};
  // O nome curto do método: "o crescimento do estado" é da base do Brasil; noutra base, "do grupo de cima", com o nome dele.
  assert.deepEqual(['M0', 'M0d', 'M0g', 'M1', 'M2', 'M3', 'manual', 'X'].map(metodo => S.nomeCurtoDoMetodo(metodo)), ['último valor mantido',
    'último valor com o crescimento do estado', 'último valor com o crescimento da base toda', 'taxa composta da janela', 'tendência linear', 'tendência log-linear',
    'taxa informada por você', 'X']);
  assert.deepEqual(['M0', 'M0d', 'M0g'].map(metodo => S.nomeCurtoDoMetodo(metodo, OUTRA)), ['último valor mantido',
    'último valor com o crescimento do grupo de cima (província)', 'último valor com o crescimento da base toda']);
  assert.deepEqual([S.metodoNaTabela(calculado, false, OUTRA), S.metodoNaTabela({...calculado, metodo: {...calculado.metodo, usado: 'M0', voltouAoM0: true}}, false, OUTRA),
    S.metodoNaTabela(somado, true, OUTRA)], ['último valor com o crescimento do grupo de cima (província)', 'último valor mantido (sem o crescimento do grupo de cima)',
    'soma das projeções dos membros (cada um com o crescimento do seu grupo de cima)']);
  // Os três números, a faixa, as contas da data final e a hipótese do cenário.
  assert.deepEqual([S.tresNumeros(calculado, OUTRA)[2], S.tresNumeros({...calculado, final: {...calculado.final, total: 52.4}}, OUTRA)[2]],
    [{rotulo: 'Diferença', valor: '+8 enfermeiros'}, {rotulo: 'Diferença', valor: '+1 enfermeiro'}]);
  assert.ok(S.textoDaFaixa(calculado, false, OUTRA).startsWith('Faixa de 8 em cada 10 em jun/2026: de 48,2 a 74,9 enfermeiros. No passado da base, em 8 de cada 10 casos de ' +
    'territórios do mesmo porte,'));
  assert.deepEqual([S.contasDoFinal(calculado, OUTRA), S.contasDoFinal({...calculado, final: {...calculado.final, intervencao: 0}}, OUTRA)],
    ['Na data final, neste território: base do cenário de 54,5 + 4 da intervenção = 58,5 enfermeiros (o texto acima arredonda para o inteiro).',
      'Na data final: base do cenário de 54,5 enfermeiros, sem intervenção.']);
  assert.equal(S.textoDaHipotese(hipotese, OUTRA), 'Hipótese do cenário (não é um sinal observado): com 1 enfermeiro em jun/2026, o território seria Crítico em “Poucos ' +
    'enfermeiros” (a saída de 1 tiraria 100,0%). Pela faixa do cenário, pode ficar entre elevado e crítico. Os limites são os limites fixos do Detector; os sinais ' +
    'comparados com a base valem só para registros reais.');
  assert.ok(S.textoDaHipotese({...hipotese, inteiro: 12, valor: 12, classe: null, impactoPct: 8.3333, naFaixa: null}, OUTRA)
    .startsWith('Hipótese do cenário (não é um sinal observado): com 12 enfermeiros em jun/2026, o território não teria alerta em “Poucos enfermeiros” (a saída'));
  // Nenhum desses textos traz os nomes da base do Brasil.
  const textos = [S.tresNumeros(calculado, OUTRA), S.textoDaFaixa(calculado, false, OUTRA), S.textoDaFaixa(calculado, true, OUTRA), S.contasDoFinal(calculado, OUTRA),
    S.metodoNaTabela(calculado, false, OUTRA), S.metodoNaTabela(somado, true, OUTRA), S.textoDaHipotese(hipotese, OUTRA), ['M0', 'M0d', 'M0g'].map(m => S.nomeCurtoDoMetodo(m, OUTRA))];
  assert.equal(/médic|municíp|estado/i.test(JSON.stringify(textos)), false, JSON.stringify(textos));
  // O cabeçalho do CSV dos resultados também diz a contagem da base (na base do Brasil, "Médicos na origem", como antes).
  const cabecalho = S.csvDoSimulador(S.normalizarSimulador({fonte: {rotulos: OUTRA}})).slice(1).split('\r\n')[0].split(';');
  assert.deepEqual([cabecalho[9], cabecalho[23], cabecalho[25], cabecalho.length],
    ['Enfermeiros na origem', 'Planejamento inverso: enfermeiros por evento', 'Hipótese do cenário: nível em poucos enfermeiros', 28]);
  assert.equal(/médic/i.test(cabecalho.join(';')), false);
});

test('a tela: o modo simples numa tela só, e as quatro etapas só no modo avançado', () => {
  const tela = ler('SimuladorDeCenarios.tsx'), area = ler('AreaDeAnalise.tsx');
  // O modo simples e os passos do modo avançado são blocos separados, cada um atrás do seu modo; a raiz diz o modo em uso.
  const inicioDoSimples = tela.indexOf('{config.modo === "simples" && <div data-testid="simulador-simples" data-teste={teste}');
  const inicioDoAvancado = tela.indexOf('{config.modo === "avancado" && <ol className="ferramenta-etapas analise-nao-imprimir" aria-label="Etapas do Simulador">');
  assert.ok(inicioDoSimples > 0 && inicioDoAvancado > inicioDoSimples, 'o modo simples vem antes dos passos');
  const simples = tela.slice(inicioDoSimples, inicioDoAvancado), avancado = tela.slice(inicioDoAvancado);
  assert.match(tela, /<section data-testid="simulador" data-estado=\{[^}]*\}\s+data-etapa=\{etapa\} data-modo=\{config\.modo\}/);
  // Numa tela só: o território, até quando (com os atalhos), o que testar, "Calcular" e o resultado, com os dois "Entenda".
  for (const id of ['simulador-territorio', 'simulador-sem-territorio', 'simulador-aviso-local', 'simulador-metodo-do-avancado', 'simulador-o-que-testar',
    'simulador-teste-quantidade', 'simulador-teste-meta-valor', 'simulador-teste-meta-origem',
    'simulador-calcular', 'simulador-pendencia', 'simulador-erro', 'simulador-resultado', 'simulador-desatualizado', 'simulador-texto', 'simulador-tres-numeros',
    'simulador-faixa-estado', 'simulador-faixa-texto', 'simulador-planejamento', 'simulador-planejamento-texto', 'simulador-planejamento-motivo', 'simulador-hipotetico',
    'simulador-avisos', 'simulador-motivo', 'simulador-avancado'])
    assert.equal(simples.split('data-testid="' + id + '"').length - 1, 1, id);
  // AJ-03 (18/11/2026): "Como os métodos se saíram no passado" e a linha de versões saíram da tela, nos dois modos.
  for (const fora of ['simulador-validacao-botao', 'simulador-validacao', 'simulador-escolhas', 'simulador-versoes', 'simulador-faixas', 'simulador-erros'])
    assert.ok(!tela.includes('"' + fora + '"'), fora);
  // As datas (até quando, e a do acréscimo, da retirada ou do acréscimo da meta, uma de cada vez) são campos de data: o identificador
  // vai em `testid`, e o campo é de mês ou, numa base só com anos, de ano (o teste do campo de data fica mais abaixo).
  assert.equal(simples.split('<CampoDeData testid="simulador-horizonte"').length - 1, 1);
  assert.equal(simples.split('<CampoDeData testid="simulador-teste-em"').length - 1, 2);
  for (const trecho of ['data-testid={"simulador-atalho-" + anos}', 'data-testid={"simulador-teste-" + item.chave}', 'testid="simulador-entenda-jeito"',
    'testid="simulador-entenda-faixa"', '<GraficoDoCenario ']) assert.equal(simples.split(trecho).length - 1, 1, trecho);
  assert.match(simples, /\{\[1, 2, 4\]\.map\(anos => <button key=\{anos\} type="button" data-testid=\{"simulador-atalho-" \+ anos\}/, 'os atalhos de 1, 2 e 4 anos');
  // O que é do modo avançado (os passos, a seleção local, a tabela, os métodos, a faixa pedida e as exportações) não aparece no modo simples.
  for (const id of ['simulador-etapa-', 'simulador-territorios', 'simulador-base', 'simulador-intervencoes-etapa', 'simulador-resultados', 'simulador-calcular-direto',
    'simulador-locais', 'simulador-foco', 'simulador-tabela', 'simulador-cenario-resultado', 'simulador-faixa-em-10', 'simulador-busca', 'simulador-exportar-csv']) {
    assert.ok(!simples.includes('"' + id), id + ' fora do modo simples');
    assert.ok(avancado.includes('"' + id), id + ' no modo avançado');
  }
  assert.match(tela, /const etapaVisivel = config\.modo === "avancado" \? etapa : 0;/);
  for (const [numero, id] of [[1, 'simulador-territorios'], [2, 'simulador-base'], [3, 'simulador-intervencoes-etapa']])
    assert.ok(tela.includes('{etapaVisivel === ' + numero + ' && <div data-testid="' + id + '"'), id);
  assert.ok(tela.includes('{etapaVisivel === 4 && resposta && <div data-testid="simulador-resultados"'));
  assert.ok(!/\{etapa === \d/.test(tela), 'nenhum passo aparece só pelo número dele, sem o modo avançado');
  assert.match(tela, /\{config\.modo === "avancado" && etapa !== 3 && etapa !== 4 && <div[^>]*>\s*<button type="button" data-testid="simulador-calcular-direto"/);
  // Os dois caminhos entre os modos. O modo avançado vale para qualquer base: nada o desliga com uma planilha enviada.
  assert.match(tela, /data-testid="simulador-modo-simples" className="analise-botao-secundario" aria-pressed=\{config\.modo === "simples"\}\s+onClick=\{\(\) => mudar\(\{ modo: "simples" \}\)\}>Modo simples<\/button>/);
  assert.match(tela, /data-testid="simulador-modo-avancado" className="analise-botao-secundario" aria-pressed=\{config\.modo === "avancado"\}\s+onClick=\{\(\) => mudar\(\{ modo: "avancado" \}\)\}>Avançado<\/button>/);
  assert.match(simples, /<button type="button" data-testid="simulador-avancado" className="analise-link"\s+onClick=\{\(\) => mudar\(\{ modo: "avancado" \}\)\}>Avançado</);
  assert.ok(!tela.includes('semAvancado') && !area.includes('semAvancado'), 'o motivo de não haver o modo avançado saiu da tela e da área');
  // O território é um dos da seleção local, e o que testar vem do modelo (TESTES e comOTeste): nada é calculado na tela.
  assert.ok(tela.includes('const doSimples = territoriosDaSelecaoLocal(config.local, { unidade: nomeDe, grupo: estadoComoUnidade, todo: r.todo });'));
  assert.ok(tela.includes('const territorioDoSimples = doSimples.some(item => item.id === config.territorio) ? config.territorio! : primeiroDaSelecao(config.local) ?? "";'));
  // Trocar o território tira a meta, que era do território de antes (revisão das capturas, 14/11/2026), e o resultado anterior, que
  // também era dele (15/11/2026): o aviso "As escolhas mudaram depois deste cálculo" fica para as mudanças no mesmo território.
  assert.match(simples, /<select data-testid="simulador-territorio" className="analise-campo" value=\{territorioDoSimples\} disabled=\{!doSimples\.length\}\s+onChange=\{event => trocarDeTerritorio\(event\.target\.value\)\}>/);
  assert.match(tela, /function trocarDeTerritorio\(id: string\) \{\s+if \(id === territorioDoSimples\) return;\s+controle\.current\?\.abort\(\);\s+mudar\(aoTrocarDeTerritorio\(config!, id\)\);\s+setResposta\(null\); setCalculado\(""\); setErro\(null\); setCarregando\(false\); setFoco\(null\);\s+\}/);
  assert.equal(tela.split('aoTrocarDeTerritorio(').length - 1, 1, 'a troca de território passa sempre por trocarDeTerritorio');
  assert.match(simples, /\{TESTES\.map\(item => <label key=\{item\.chave\}[^>]*><input type="radio" name="simulador-teste"\s+data-testid=\{"simulador-teste-" \+ item\.chave\} checked=\{teste === item\.chave\}\s+onChange=\{\(\) => trocarCenario\(0, comOTeste\(cenarioDoSimples, item\.chave, anosDepois\(ultimoRegistro, 1\)\)\)\}\/>\{item\.rotulo\}<\/label>\)\}/);
  assert.ok(tela.includes('const teste = testeDoCenario(cenarioDoSimples);'));
  assert.match(simples, /<button type="button" data-testid="simulador-calcular" className="analise-botao-primario" disabled=\{!!pendencia \|\| carregando\} onClick=\{calcular\}>\s+\{carregando \? "Calculando…" : "Calcular"\}<\/button>/);
  // O pedido leva o que descreve a base (numa planilha), na chave do cálculo e no pedido ao motor: nunca o pedido sem ela.
  assert.equal(tela.split('pedidoDoSimulador(config, p.daBase)').length - 1, 2);
  assert.ok(!tela.includes('pedidoDoSimulador(config)'));
  assert.ok(tela.includes('pedirAoMotor(p.fonte, "/api/simulador", pedidoDoSimulador(config, p.daBase), novo.signal)'));
  // O resultado: a frase fixa, os três números, o jeito de projetar (com "escolhido pela base"), a faixa e os avisos são os do motor.
  assert.match(simples, /<div data-testid="simulador-resultado" data-estado=\{resultadoDoSimples\.estado\}\s+data-metodo=\{resultadoDoSimples\.metodo\.usado \?\? ""\} data-faixa=\{resultadoDoSimples\.faixa\.estado\} data-conferencia=\{resultadoDoSimples\.final\?\.faixa\?\.estado \?\? ""\}/);
  assert.ok(simples.includes('<p data-testid="simulador-texto" className="ferramenta-texto-do-cenario">{resultadoDoSimples.texto}</p>'));
  assert.ok(simples.includes('{tresNumeros(resultadoDoSimples, r).map(item => <div key={item.rotulo}><dt>{item.rotulo}</dt><dd>{item.valor}</dd></div>)}'));
  assert.ok(simples.includes('<span>Forma de projetar: {resultadoDoSimples.metodo.rotulo}{resultadoDoSimples.metodo.eOEscolhido ? " (escolhida pela base)" : ""}</span>'));
  assert.match(simples, /<Entenda sobre="A forma de projetar" texto=\{resultadoDoSimples\.entenda\.jeito\.texto\} exemplo=\{resultadoDoSimples\.entenda\.jeito\.exemplo\}\s+testid="simulador-entenda-jeito" completaHref=\{linkDaFicha\(BASE, "simulador", SECOES_DAS_FICHAS\.simulador\.forma\)\}\/>/);
  assert.match(simples, /<Entenda sobre=\{"A faixa de " \+ resultadoDoSimples\.faixa\.em10 \+ " em cada 10"\} texto=\{resultadoDoSimples\.entenda\.faixa\.texto\}\s+exemplo=\{resultadoDoSimples\.entenda\.faixa\.exemplo\} testid="simulador-entenda-faixa"\s+completaHref=\{linkDaFicha\(BASE, "simulador", SECOES_DAS_FICHAS\.simulador\.faixa\)\}\/>/);
  assert.match(simples, /<span data-testid="simulador-faixa-estado">Faixa de \{resultadoDoSimples\.faixa\.em10\} em cada 10: \{!resultadoDoSimples\.final\?\.faixa \? "indisponível"\s+: resultadoDoSimples\.final\.faixa\.estado === "conferida" \? "conferida" : "provisória"\}<\/span>/);
  assert.ok(simples.includes('<p data-testid="simulador-faixa-texto" className="ferramenta-apoio">{textoDaFaixa(resultadoDoSimples, territorioEmFoco.tipo === "conjunto", r)}</p>'));
  assert.ok(simples.includes('<p data-testid="simulador-planejamento-texto" className="ferramenta-texto-do-cenario">{resultadoDoSimples.planejamento.texto}</p>'));
  assert.ok(simples.includes('{resultadoDoSimples.avisos.map(aviso => <li key={aviso.codigo} data-codigo={aviso.codigo}>{aviso.texto}</li>)}'));
  assert.ok(!tela.includes('resposta.retroprojecao.escolhas') && !tela.includes('resposta.notas'), 'a escolha e as notas vão na exportação, não na tela');
  // "Simular recuperação" (Detector de Sinais): no modo simples, a meta está em "O que testar", e a tela diz de onde ela veio.
  assert.ok(tela.includes('a volta ao patamar anterior (" + (config.modo === "simples" ? "em “O que testar”" : "etapa 3") + ")."'));
  // O campo mostra a meta em uso (o patamar arredondado para cima); digitar outra troca a meta por um número da pessoa.
  assert.match(simples, /<input data-testid="simulador-teste-meta-valor" inputMode="decimal"[^>]*aria-label="Meta hipotética"\s+value=\{metaNoCampo\(cenarioDoSimples\.planejamento\)\}/);
  assert.ok(simples.includes('onChange={event => mudarPlano(0, { valor: event.target.value, meta: "valor" })}/>'));
  // O identificador de cada opção de "O que testar" ("simulador-teste-" + a chave) é só dela: o campo do valor da meta tem outro nome.
  for (const {chave} of S.TESTES) assert.ok(!tela.includes('data-testid="simulador-teste-' + chave + '"'), 'simulador-teste-' + chave + ' é só o da opção');
  assert.match(simples, /<span data-testid="simulador-teste-meta-origem">\{cenarioDoSimples\.planejamento\.meta === "patamar" \? textoDaMetaDoPatamar\(cenarioDoSimples\.planejamento, r\)\s+: "A meta é uma hipótese sua\. "\}<\/span>O Agente calcula quantos faltariam, com o menor número inteiro\./);
  // Os nomes vêm da base (os da resposta do motor; antes dela, os que o pedido diz da planilha ou, sem planilha, os do Brasil), e
  // a faixa do gráfico e das legendas é a pedida.
  assert.ok(tela.includes('const nomesDaBase: NomesDaBase = resposta?.fonte.rotulos ?? nomesDaPlanilha(props.daBase) ?? NOMES_DO_BRASIL;'));
  assert.ok(tela.includes('"; banda: faixa de " + em10 + " em cada 10" + (territorio.tipo === "conjunto" ? " (aproximação)" : "")'));
  assert.equal(tela.split('em10={resposta.retroprojecao.em10}').length - 1, 2, 'nos dois modos');
  assert.ok(tela.includes('<span data-testid="simulador-grafico-fonte">{fonte.origem === "planilha" ? "Fonte: " + fonte.base + " (" + fonte.categoria.toLowerCase() + "), registros até "'));
  assert.match(avancado, /<select data-testid="simulador-faixa-em-10"[^>]*value=\{config\.faixa \?\? 8\}\s+onChange=\{event => mudar\(\{ faixa: Number\(event\.target\.value\) as 5 \| 8 \| 9 \}\)\}>\s+\{\[5, 8, 9\]\.map\(quantos => <option key=\{quantos\} value=\{quantos\}>\{quantos\}<\/option>\)\}/);
  assert.ok(!/80%/.test(tela.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '')), 'a tela diz "N em cada 10", não "80%"');
  // A área entrega ao Simulador as competências no formato das ferramentas e o que descreve a base. Com uma planilha, a ferramenta
  // só fica desligada quando nenhuma data dela é reconhecida (as planilhas só com o ano entram).
  assert.match(area, /<SimuladorDeCenarios fonte=\{fonteMotor\} principal=\{selecaoParaFerramentas\} resumoDaPrincipal=\{resumoDaSelecao\} unidades=\{municipios\} grupos=\{grupos\}\s+competencias=\{periodosDasFerramentas\} config=\{configDoSimulador\} onConfig=\{setConfigDoSimulador\} onAplicarSelecao=\{aplicarSelecaoDoSimulador\}\s+daBase=\{baseDasFerramentas\} grupoDe=\{tipo === "arquivo" \? grupoDe : undefined\}\/>/);
  assert.ok(area.includes('const periodosDasFerramentas = useMemo(() => tipo === "arquivo" ? competenciasDasFerramentas(periodos) : periodos, [tipo, periodos]);'));
  assert.match(area, /const motivoDoSimulador = tipo !== "arquivo" \|\| periodosDasFerramentas\.length \? null\s+: "O Simulador de Cenários precisa de datas na planilha que o Agente reconheça \(AAAAMM, AAAA-MM, AAAA-MM-DD ou só o ano\)\.";/);
});

test('a tela: toda data do cenário é um campo de data — de mês ou, numa base só com anos, de ano', () => {
  const tela = ler('SimuladorDeCenarios.tsx');
  // O campo de data: um campo de mês (com o mínimo no último registro, quando pedido) ou, quando o último registro é "AAAA00", uma
  // lista de anos que começa no ano seguinte a ele; a data sai sempre no formato do modelo ("AAAAMM" ou "AAAA00").
  const inicio = tela.indexOf('function CampoDeData({ testid, valor, ultimo, comMinimo = false, className = "analise-campo", rotulo, onMudar }');
  assert.ok(inicio > 0);
  const campo = tela.slice(inicio, tela.indexOf('\n}\n', inicio));
  for (const trecho of ['if (!ehAnual(ultimo)) return <input type="month" data-testid={testid} className={className} aria-label={rotulo} value={paraCampoDeMes(valor)}',
    'min={comMinimo ? paraCampoDeMes(ultimo) : undefined} onChange={event => onMudar(doCampoDeMes(event.target.value))}/>;',
    'const primeiro = Number(ultimo.slice(0, 4)) + 1;', '<select data-testid={testid} data-anual="true" className={className} aria-label={rotulo} value={atual ?? ""}',
    'onChange={event => onMudar(event.target.value ? event.target.value + "00" : "")}>']) assert.ok(campo.includes(trecho), trecho);
  // Nenhum campo de mês fora dele: uma base só com anos nunca recebe um campo de mês.
  assert.equal(tela.split('type="month"').length - 1, 1);
  assert.equal(campo.split('type="month"').length - 1, 1);
  // As seis datas do Simulador passam por ele (a data final e a data do modo simples, duas vezes cada uma: uma por modo ou por
  // frase), e nenhuma aparece como um campo escrito à mão.
  for (const [id, vezes] of [['simulador-horizonte', 2], ['simulador-teste-em', 2], ['simulador-plano-em', 1], ['simulador-plano-ate', 1], ['simulador-intervencao-em', 1],
    ['simulador-intervencao-ate', 1]]) {
    assert.equal(tela.split('<CampoDeData testid="' + id + '"').length - 1, vezes, id);
    assert.ok(!tela.includes('data-testid="' + id + '"'), id + ' só pelo campo de data');
  }
  assert.equal(tela.split('<CampoDeData ').length - 1, 8);
  for (const trecho of ['<CampoDeData testid="simulador-horizonte" valor={config.horizonte} ultimo={ultimoRegistro} comMinimo onMudar={data => mudar({ horizonte: data })}/>',
    '<CampoDeData testid="simulador-teste-em" className="ferramenta-campo-da-frase" rotulo="Data da mudança" valor={cenarioDoSimples.intervencoes[0].em}',
    '<CampoDeData testid="simulador-teste-em" className="ferramenta-campo-da-frase" rotulo="Data do acréscimo" valor={cenarioDoSimples.planejamento.em}',
    '<CampoDeData testid="simulador-plano-em" valor={plano.em} ultimo={ultimoRegistro} comMinimo onMudar={data => mudarPlano(indice, { em: data })}/>',
    '<CampoDeData testid="simulador-plano-ate" valor={plano.ate} ultimo={ultimoRegistro} onMudar={data => mudarPlano(indice, { ate: data })}/>',
    '<CampoDeData testid="simulador-intervencao-em" valor={item.em} ultimo={ultimoRegistro} comMinimo onMudar={data => mudarIntervencao(indice, k, { em: data })}/>',
    '<CampoDeData testid="simulador-intervencao-ate" valor={item.ate} ultimo={ultimoRegistro} onMudar={data => mudarIntervencao(indice, k, { ate: data })}/>'])
    assert.ok(tela.includes(trecho), trecho);
  // Numa base só com anos, o intervalo dos eventos é dito em anos (nas intervenções e no planejamento inverso).
  assert.ok(tela.includes('const daPlanilha = !!props.daBase, anual = ehAnual(ultimoRegistro);'));
  assert.equal(tela.split('{anual ? "a cada (anos)" : "a cada (meses)"}').length - 1, 2);
  // Os textos do modo avançado usam os nomes da base: as formas com artigo e o título da hipótese ("Poucos …", igual nos dois modos).
  // A tabela de erros dos métodos saiu com "Como os métodos se saíram no passado" (AJ-03): os números vão na exportação.
  assert.ok(tela.includes('const formas: FormasDaBase = resposta?.fonte.formas ?? formasDaPlanilha(props.daBase) ?? FORMAS_DO_BRASIL;'));
  assert.equal(tela.split('<p className="ferramenta-cartao-titulo">Poucos {r.profissionais}, no cenário<span className="analise-marca-grupo">').length - 1, 2);
  assert.ok(!tela.includes('Dependência de poucos'));
  assert.ok(!tela.includes('metodosDaTabela'));
  // "Copiar de novo a seleção principal" também desfaz a janela com que o Detector abriu o Simulador.
  assert.ok(tela.includes('mudar({ local: copia, acompanha: true, doDetector: undefined, janelaDoDetector: undefined, referencias: referenciasValidas(config.referencias, copia) });'));
});

test('modo simples: o pedido não leva a janela geral nem as referências do modo avançado, só a janela com que o Detector abriu o Simulador', () => {
  const inicial = S.configInicial({municipios: ['code:130260', 'code:130420'], estados: [], conjuntos: []}, '202406');
  const cenarios = [{id: 'c1', nome: 'Cenário 1', metodo: 'padrao'}, {id: 'm0', nome: 'Persistência (referência)', metodo: 'M0'}];
  const comTudo = {...inicial, janela: {inicio: '201906', fim: '202406'}, referencias: [R1, R3], metrica: 'taxa'};
  // No modo simples: o território em análise, a data final e o cenário. A janela geral, as referências e a métrica ficam na configuração.
  assert.deepEqual(S.pedidoDoSimulador(comTudo), {base: {municipios: {todos: false, estados: [], ids: ['code:130260']}}, horizonte: '202606', cenarios});
  assert.deepEqual(S.pedidoDoSimulador({...comTudo, janela: null, referencias: [], metrica: 'quantidade'}), S.pedidoDoSimulador(comTudo),
    'mudar o que é do modo avançado não muda o pedido do modo simples');
  // No modo avançado, a mesma configuração leva tudo de novo: nada se perdeu ao passar pelo modo simples.
  assert.deepEqual(S.pedidoDoSimulador({...comTudo, modo: 'avancado'}), {base: {municipios: {todos: false, estados: [], ids: ['code:130260', 'code:130420']}},
    janela: {inicio: '201906', fim: '202406'}, horizonte: '202606', cenarios,
    referencias: [{id: 'r1', tipo: 'dinamica', territorio: 'code:420540'}, {id: 'r3', tipo: 'valor', valor: 6500, rotulo: 'Valor informado por você'}],
    comparacao: {metrica: 'taxa'}});
  // A janela escolhida no Detector de Sinais é a única que o modo simples leva; no modo avançado, vale a janela geral.
  const doDetector = {...comTudo, janelaDoDetector: {inicio: '201801', fim: '202106'}};
  assert.deepEqual(S.pedidoDoSimulador(doDetector), {base: {municipios: {todos: false, estados: [], ids: ['code:130260']}}, janela: {inicio: '201801', fim: '202106'},
    horizonte: '202606', cenarios});
  assert.deepEqual(S.pedidoDoSimulador({...doDetector, modo: 'avancado'}), S.pedidoDoSimulador({...comTudo, modo: 'avancado'}));
  // O cenário exportado continua levando o que é do modo avançado, mesmo exportado no modo simples.
  const exportado = JSON.parse(S.exportarCenario(comTudo, {versaoDoMetodo: 'v', versaoDaBase: 'abc', ultimoRegistro: '202406', quando: 'q'}));
  assert.deepEqual([exportado.modo, exportado.janela, exportado.referencias.map(ref => ref.id), exportado.metrica], ['simples', {inicio: '201906', fim: '202406'}, ['r1', 'r3'], 'taxa']);
});

test('bases só com o ano ("AAAA00"): as datas do cenário, a distância até hoje e a janela contam anos', () => {
  assert.deepEqual(['202300', '202306', '2023', '20230', 'x', ''].map(S.ehAnual), [true, false, false, false, false, false]);
  // Tantos anos depois: numa base só com anos, outro ano (sem mês); numa base com mês, como antes.
  assert.deepEqual([S.anosDepois('202300', 2), S.anosDepois('202300', 0), S.anosDepois('202406', 2), S.anosDepois('202401', 10)], ['202500', '202300', '202606', '203401']);
  assert.deepEqual([S.configInicial({municipios: ['name:A'], estados: [], conjuntos: []}, '202300').horizonte, S.novoPlano(S.anosDepois('202300', 1)).em, S.competenciaCurta('202500')],
    ['202500', '202400', '2025'], 'a data final proposta, a data do acréscimo e a data curta são anos');
  // A distância entre o último registro e hoje, em anos inteiros (o registro é do ano, sem mês).
  assert.deepEqual([new Date(2026, 10, 10), new Date(2024, 0, 1), new Date(2023, 11, 31), new Date(2023, 0, 1), new Date(2020, 0, 1)].map(hoje => S.tempoDesde('202300', hoje)),
    ['3 anos', '1 ano', 'menos de 1 ano', 'menos de 1 ano', 'menos de 1 ano']);
  // A janela padrão são os 3 anos até o último registro, pelo tempo: 7 registros na base do Brasil, 4 numa base só com anos; uma
  // base mais curta começa no primeiro registro; com um registro só, não há janela.
  const ANOS = Array.from({length: 10}, (_, k) => String(2014 + k) + '00');
  assert.deepEqual([S.janelaPadrao(COMPETENCIAS), S.janelaPadrao(ANOS), S.janelaPadrao(['202200', '202300']), S.janelaPadrao(['202300']), S.janelaPadrao([])],
    [{inicio: '202106', fim: '202406'}, {inicio: '202000', fim: '202300'}, {inicio: '202200', fim: '202300'}, null, null]);
  // A janela dos últimos N anos ("Últimos 5 anos"): do primeiro registro a até N anos do último; quando a base não chega a esse
  // tempo, não há (o atalho fica desligado) — ou, a pedido (`curta`), a base inteira.
  assert.deepEqual([S.janelaDeAnos(COMPETENCIAS, 5), S.janelaDeAnos(COMPETENCIAS, 3), S.janelaDeAnos(ANOS, 5), S.janelaDeAnos(ANOS, 9)],
    [{inicio: '201906', fim: '202406'}, {inicio: '202106', fim: '202406'}, {inicio: '201800', fim: '202300'}, {inicio: '201400', fim: '202300'}]);
  assert.deepEqual([S.janelaDeAnos(ANOS, 10), S.janelaDeAnos(COMPETENCIAS, 10.5), S.janelaDeAnos(['202401', '202406'], 5), S.janelaDeAnos(['202406'], 5, true)],
    [null, null, null, null]);
  assert.deepEqual([S.janelaDeAnos(ANOS, 10, true), S.janelaDeAnos(COMPETENCIAS, 10.5, true), S.janelaDeAnos(['202401', '202406'], 5, true)],
    [{inicio: '201400', fim: '202300'}, {inicio: '201401', fim: '202406'}, {inicio: '202401', fim: '202406'}]);
});

test('as formas com artigo dos nomes da base: as do motor na resposta e, antes dela, as que o pedido diz da planilha', () => {
  assert.deepEqual(S.FORMAS_DO_BRASIL, {oUnidade: 'o município', osUnidades: 'os municípios', oGrupo: 'o estado', osGrupos: 'os estados', dosGrupos: 'dos estados',
    doTodo: 'do Brasil', noTodo: 'no Brasil', oTodo: 'o Brasil'});
  assert.equal(S.formasDaPlanilha(undefined), null, 'a base do Brasil não tem "o que o pedido diz dela"');
  // O gênero da unidade e do grupo de cima e o artigo do todo, como no painel "Colunas".
  const daSolaria = {oUnidade: 'a comuna', osUnidades: 'as comunas', oGrupo: 'o condado', osGrupos: 'os condados', dosGrupos: 'dos condados', doTodo: 'da Solária',
    noTodo: 'na Solária', oTodo: 'a Solária'};
  assert.deepEqual(S.formasDaPlanilha({rotulos: {unidade: {singular: 'comuna', plural: 'comunas', genero: 'f'}, grupo: {singular: 'condado', plural: 'condados'},
    todo: {nome: 'Solária', artigo: 'a'}}}), daSolaria);
  assert.deepEqual(S.formasDaPlanilha({rotulos: {unidade: {singular: 'distrito', plural: 'distritos', genero: 'm'}, grupo: {singular: 'província', plural: 'províncias', genero: 'f'},
    todo: {nome: 'Angola'}}}), {oUnidade: 'o distrito', osUnidades: 'os distritos', oGrupo: 'a província', osGrupos: 'as províncias', dosGrupos: 'das províncias',
    doTodo: 'de Angola', noTodo: 'em Angola', oTodo: 'Angola'}, 'sem artigo: "de Angola", "em Angola"');
  // Sem os nomes (ou com nomes que não são texto), valem os do motor: "a unidade", "o grupo" e "a base toda".
  const padrao = {oUnidade: 'a unidade', osUnidades: 'as unidades', oGrupo: 'o grupo', osGrupos: 'os grupos', dosGrupos: 'dos grupos', doTodo: 'de toda a base',
    noTodo: 'em toda a base', oTodo: 'a base toda'};
  assert.deepEqual([S.formasDaPlanilha({}), S.formasDaPlanilha({rotulos: {unidade: 7, grupo: [], todo: 'x'}})], [padrao, padrao]);
  assert.deepEqual(S.formasDaPlanilha({rotulos: {unidade: {singular: 'concelho', plural: 'concelhos'}, todo: {nome: 'Brasil', artigo: 'o'}}}),
    {...padrao, oUnidade: 'o concelho', osUnidades: 'os concelhos', doTodo: 'do Brasil', noTodo: 'no Brasil', oTodo: 'o Brasil'}, 'a unidade com nome e sem gênero é masculina');
  assert.deepEqual(['médicos', 'a base toda', 'Brasil', ''].map(S.comMaiuscula), ['Médicos', 'A base toda', 'Brasil', '']);
  // Na resposta do motor, as formas e o mês da série anual vêm na fonte: "06" na base do Brasil, "00" numa base só com anos e
  // nenhum numa planilha sem série anual. O que faltar numa resposta fica com o da base do Brasil.
  const fonte = bruto => S.normalizarSimulador({fonte: bruto}).fonte;
  const daPlanilha = fonte({base: 'planilha enviada', categoria: 'Enfermeiros', versao: 'p', origem: 'planilha', ancora: '00', formas: {o_unidade: 'a comuna',
    os_unidades: 'as comunas', o_grupo: 'o condado', os_grupos: 'os condados', dos_grupos: 'dos condados', do_todo: 'da Solária', no_todo: 'na Solária', o_todo: 'a Solária'}});
  assert.deepEqual([daPlanilha.formas, daPlanilha.ancora, daPlanilha.origem], [daSolaria, '00', 'planilha']);
  assert.deepEqual([fonte({origem: 'planilha'}).ancora, fonte({origem: 'planilha', ancora: '03'}).ancora, fonte({}).ancora, S.normalizarSimulador(null).fonte.ancora],
    [null, '03', '06', '06']);
  assert.deepEqual([S.normalizarSimulador(BRUTO).fonte.formas, S.normalizarSimulador(null).fonte.formas, fonte({formas: {o_unidade: 'a comuna', o_todo: 7}}).formas],
    [S.FORMAS_DO_BRASIL, S.FORMAS_DO_BRASIL, {...S.FORMAS_DO_BRASIL, oUnidade: 'a comuna'}]);
});

test('qualquer base: os nomes da planilha antes da primeira resposta, e o cenário exportado com a base, o território e a faixa', () => {
  // Antes da primeira resposta do motor, os nomes de uma planilha vêm do que o pedido diz dela, como o motor os monta: a frase
  // "Acrescentar … profissionais" não diz "médicos" com uma planilha.
  assert.equal(S.nomesDaPlanilha(undefined), null, 'a base do Brasil não tem "o que o pedido diz dela"');
  assert.deepEqual(S.nomesDaPlanilha({rotulos: {unidade: {singular: 'comuna', plural: 'comunas', genero: 'f'}, grupo: {singular: 'condado', plural: 'condados'},
    todo: {nome: 'Solária', artigo: 'a'}}, premissas: {count_unit: 'pessoas'}}),
    {profissional: 'profissional', profissionais: 'profissionais', unidade: 'comuna', unidades: 'comunas', grupo: 'condado', grupos: 'condados', todo: 'Solária'});
  assert.deepEqual(S.nomesDaPlanilha({premissas: {count_unit: 'vinculos'}}),
    {profissional: 'vínculo', profissionais: 'vínculos', unidade: 'unidade', unidades: 'unidades', grupo: 'grupo', grupos: 'grupos', todo: 'a base toda'});
  assert.deepEqual([S.nomesDaPlanilha({premissas: {count_unit: 'postos'}}).profissionais, S.nomesDaPlanilha({}).profissionais], ['postos', 'profissionais']);
  // O nome dos trabalhadores informado no envio ("Quem são os trabalhadores contados?") vale para os textos quando é um plural que
  // eles podem usar, pela mesma regra do motor (series_da_planilha.nome_dos_trabalhadores): só as palavras antes da primeira
  // preposição vão para o singular. Nome feminino, dois nomes, sigla ou palavra que não está no plural: "profissionais".
  assert.deepEqual(['Enfermeiros', 'médicos', 'PROFISSIONAIS', 'Técnicos de enfermagem', 'Agentes comunitários de saúde', 'Cirurgiões-dentistas',
    'Auxiliares de enfermagem', 'Dentistas', 'Fisioterapeutas', 'Pediatras', 'Cuidadores', 'Homens'].map(S.nomeDosTrabalhadores), [
    ['enfermeiro', 'enfermeiros'], ['médico', 'médicos'], ['profissional', 'profissionais'], ['técnico de enfermagem', 'técnicos de enfermagem'],
    ['agente comunitário de saúde', 'agentes comunitários de saúde'], ['cirurgião-dentista', 'cirurgiões-dentistas'],
    ['auxiliar de enfermagem', 'auxiliares de enfermagem'], ['dentista', 'dentistas'], ['fisioterapeuta', 'fisioterapeutas'], ['pediatra', 'pediatras'],
    ['cuidador', 'cuidadores'], ['homem', 'homens']]);
  assert.deepEqual(['Enfermeiras', 'Médicos e enfermeiros', 'ACS', 'Enfermagem', 'Agentes 2', 'Pessoas', '', null, undefined, 7].map(S.nomeDosTrabalhadores),
    Array(10).fill(null));
  const nomesCom = premissas => { const nomes = S.nomesDaPlanilha({premissas}); return [nomes.profissional, nomes.profissionais]; };
  assert.deepEqual([nomesCom({count_unit: 'pessoas', object_declaration: 'Enfermeiros'}), nomesCom({count_unit: 'pessoas', category_constant: 'Técnicos de enfermagem'}),
    nomesCom({object_declaration: '', category_constant: 'Dentistas'}), nomesCom({count_unit: 'pessoas', object_declaration: 'Enfermagem'}),
    nomesCom({count_unit: 'vinculos', object_declaration: 'Enfermeiros'})],
    [['enfermeiro', 'enfermeiros'], ['técnico de enfermagem', 'técnicos de enfermagem'], ['dentista', 'dentistas'], ['profissional', 'profissionais'],
      ['vínculo', 'vínculos']]);
  const tela = ler('SimuladorDeCenarios.tsx');
  assert.ok(tela.includes('const nomesDaBase: NomesDaBase = resposta?.fonte.rotulos ?? nomesDaPlanilha(props.daBase) ?? NOMES_DO_BRASIL;'));
  // O cenário exportado diz a base em uso (sem a opção, a do Brasil) e leva o território em análise e a faixa pedida; a importação os repõe.
  const config = {...S.configInicial({municipios: ['name:Distrito 13', 'name:Distrito 02'], estados: [], conjuntos: []}, '202307'), territorio: 'name:Distrito 02', faixa: 5};
  const exportado = JSON.parse(S.exportarCenario(config, {versaoDoMetodo: 'v', versaoDaBase: 'planilha:abc', ultimoRegistro: '202307', quando: 'q',
    base: {nome: 'planilha enviada', categoria: 'Enfermeiros'}}));
  assert.deepEqual(exportado.base, {nome: 'planilha enviada', categoria: 'Enfermeiros', versao: 'planilha:abc', ultimo_registro: '202307'});
  assert.deepEqual([exportado.territorio, exportado.faixa], ['name:Distrito 02', 5]);
  const lido = S.importarCenario(JSON.stringify(exportado)).config;
  assert.deepEqual([lido.territorio, lido.faixa, lido.modo, lido.local.municipios], ['name:Distrito 02', 5, 'simples', ['name:Distrito 13', 'name:Distrito 02']]);
  // Sem o território e com a faixa padrão, o arquivo não leva essas chaves; uma faixa que não existe não é lida.
  const padrao = JSON.parse(S.exportarCenario({...config, territorio: undefined, faixa: 8}, {versaoDoMetodo: '', versaoDaBase: '', ultimoRegistro: '', quando: ''}));
  assert.deepEqual(['territorio' in padrao, 'faixa' in padrao, padrao.base.nome], [false, false, 'Brasil']);
  assert.equal('faixa' in S.importarCenario(JSON.stringify({...exportado, faixa: 7})).config, false);
  // Na tela: a exportação diz a planilha, e o modo simples avisa quando o cenário usa um jeito de projetar escolhido no modo
  // avançado. Desde 15/11/2026, a volta ao que a base escolheu é pelo "Voltar ao padrão" único, no alto (o aviso só o indica).
  assert.ok(tela.includes('...(p.daBase ? { base: { nome: resposta?.fonte.base || "planilha enviada", categoria: resposta?.fonte.categoria || p.daBase.categoria || "" } } : {})'));
  assert.ok(tela.includes('{cenarioDoSimples.metodo !== "padrao" && <p data-testid="simulador-metodo-do-avancado"'));
  assert.ok(tela.includes('“Voltar ao padrão”, no alto, desfaz essa escolha.</p>}') && !tela.includes('Voltar ao jeito escolhido pela base') && !tela.includes('Voltar à forma escolhida pela base'));
});

test('modo simples: o pedido leva só o que a tela simples mostra — sem o calendário, a permanência e as outras intervenções do modo avançado', () => {
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  const periodica = {tipo: 'acrescimo', quantidade: '2,5', em: '202501', periodica: true, ate: '202701', aCadaMeses: '6', permanencia: '90'};
  const outra = {tipo: 'retirada', quantidade: '1', em: '202601', periodica: false, ate: '202601', aCadaMeses: '12', permanencia: '100'};
  // O que a tela simples mostra é uma quantidade e uma data: o pedido leva a primeira intervenção, numa data, com permanência total.
  const doAvancado = {...inicial, cenarios: [cenario({intervencoes: [periodica, outra]})]};
  assert.deepEqual(S.doModoSimples(doAvancado.cenarios[0]).intervencoes, [{...periodica, periodica: false, ate: '202501', permanencia: '100'}]);
  assert.deepEqual(S.pedidoDoSimulador(doAvancado).cenarios[0], {id: 'c1', nome: 'Cenário 1', metodo: 'padrao',
    intervencoes: [{tipo: 'acrescimo', quantidade: 2.5, em: '202501'}]});
  // No modo avançado, a mesma configuração leva tudo de novo: nada se perdeu.
  assert.deepEqual(S.pedidoDoSimulador({...doAvancado, modo: 'avancado'}).cenarios[0].intervencoes, [
    {tipo: 'acrescimo', quantidade: 2.5, em: '202501', ate: '202701', a_cada_meses: 6, permanencia_pct_ao_ano: 90}, {tipo: 'retirada', quantidade: 1, em: '202601'}]);
  // Com a meta, vai só ela, com um acréscimo numa data: sem o calendário, a permanência e as intervenções do modo avançado.
  const comMeta = {...inicial, cenarios: [cenario({intervencoes: [outra],
    planejamento: {...S.novoPlano('202506'), valor: '30', periodica: true, ate: '202706', aCadaMeses: '6', permanencia: '80'}})]};
  assert.deepEqual(S.pedidoDoSimulador(comMeta).cenarios[0], {id: 'c1', nome: 'Cenário 1', metodo: 'padrao',
    planejamento: {meta: {tipo: 'valor', valor: 30}, em: '202506'}});
  assert.deepEqual(S.pedidoDoSimulador({...comMeta, modo: 'avancado'}).cenarios[0].planejamento,
    {meta: {tipo: 'valor', valor: 30}, em: '202506', ate: '202706', a_cada_meses: 6, permanencia_pct_ao_ano: 80});
  // O que falta para calcular olha só para o que vai no pedido: o calendário incompleto, a segunda intervenção sem quantidade e uma
  // referência sem valor são do modo avançado e não impedem o cálculo no modo simples.
  const incompleto = {...inicial, cenarios: [cenario({intervencoes: [{...periodica, ate: '202401'}, {...outra, quantidade: ''}]})],
    referencias: [{id: 'r1', alvo: 'valor', rotulo: 'Valor informado por você', tipo: 'valor', valor: ''}]};
  assert.equal(S.pendenciaDoPedido(incompleto), null);
  assert.equal(S.pendenciaDoPedido({...incompleto, modo: 'avancado'}), 'Numa intervenção periódica, a data final vem depois da inicial.');
  assert.equal(S.pendenciaDoPedido({...incompleto, modo: 'avancado', cenarios: [cenario()]}), 'Informe o valor da referência “Valor informado por você”.');
  // A janela com que o Detector de Sinais abriu o Simulador vai no cenário exportado, e a importação a repõe (o aviso de origem, não).
  const doDetector = S.configDoDetector({local: {municipios: ['code:130260'], estados: [], conjuntos: []}, rotulo: 'MANAUS (AM)', sinais: [], fim: '202106'},
    '202406', {inicio: '201801', fim: '202106'}, null);
  const exportado = JSON.parse(S.exportarCenario(doDetector, {versaoDoMetodo: 'v', versaoDaBase: 'abc', ultimoRegistro: '202406', quando: 'q'}));
  assert.deepEqual([exportado.janela_do_detector, 'doDetector' in exportado], [{inicio: '201801', fim: '202106'}, false]);
  const importado = S.importarCenario(JSON.stringify(exportado)).config;
  assert.deepEqual(importado.janelaDoDetector, {inicio: '201801', fim: '202106'});
  assert.deepEqual(S.pedidoDoSimulador(importado), S.pedidoDoSimulador(doDetector), 'o pedido do modo simples é o mesmo depois de exportar e importar');
  assert.equal('janela_do_detector' in JSON.parse(S.exportarCenario(inicial, {versaoDoMetodo: '', versaoDaBase: '', ultimoRegistro: '', quando: ''})), false);
  // A janela padrão tem pelo menos dois registros: numa base com registros espaçados, começa no registro anterior ao último.
  assert.deepEqual([S.janelaPadrao(['201400', '201900', '202400']), S.janelaPadrao(['201401', '202406'])],
    [{inicio: '201900', fim: '202400'}, {inicio: '201401', fim: '202406'}]);
  // Na tela, o todo já na seleção diz o nome com o artigo, e a referência dinâmica segue o jeito escolhido pela base.
  const tela = ler('SimuladorDeCenarios.tsx');
  assert.ok(tela.includes('setAvisoLocal(comMaiuscula(formas.oTodo) + " já está na seleção do Simulador.");'));
  assert.ok(tela.includes('<option value="dinamica">Dinâmica: segue a forma escolhida pela base</option>'));
});

test('revisão das capturas: a meta sai ao trocar de território, a meta do patamar é inteira e diz de onde veio, e o gráfico mostra o caminho com o acréscimo', () => {
  const recuperacao = S.configDoDetector({local: {municipios: ['code:420010', 'code:420005'], estados: ['15'], conjuntos: []}, rotulo: 'ABELARDO LUZ (SC)',
    sinais: ['Abaixo do que já teve (moderado)'], fim: '202406'}, '202406', null, 78.25);
  const plano = recuperacao.cenarios[0].planejamento;
  // O plano guarda o patamar com a precisão do Detector, e é ele que vai ao motor (que arredonda para cima e diz a origem).
  assert.deepEqual([plano.meta, plano.valor, S.pedidoDoSimulador(recuperacao).cenarios[0].planejamento.meta], ['patamar', '78,25', {tipo: 'patamar', valor: 78.25}]);
  // O campo mostra a meta em uso: o inteiro acima do patamar. O que não é o patamar aparece como foi digitado.
  assert.deepEqual([plano, {...plano, valor: '20'}, {...plano, valor: '1,75'}, {...plano, valor: ''}, {...plano, valor: 'x'}, {...plano, meta: 'valor', valor: '78,25'}]
    .map(S.metaNoCampo), ['79', '20', '2', '', 'x', '78,25']);
  assert.equal(S.textoDaMetaDoPatamar(plano), 'A meta veio do Detector de Sinais: o patamar anterior, de 78,25 médicos (a maior média de dois anos seguidos), ' +
    'arredondado para cima. É uma hipótese que você pode trocar. ');
  assert.equal(S.textoDaMetaDoPatamar({...plano, valor: '20'}), 'A meta veio do Detector de Sinais: o patamar anterior, de 20 médicos (a maior média de dois anos ' +
    'seguidos). É uma hipótese que você pode trocar. ');
  assert.equal(S.textoDaMetaDoPatamar({...plano, valor: '1'}, {...S.NOMES_DO_BRASIL, profissional: 'enfermeiro', profissionais: 'enfermeiros'}),
    'A meta veio do Detector de Sinais: o patamar anterior, de 1 enfermeiro (a maior média de dois anos seguidos). É uma hipótese que você pode trocar. ');
  assert.equal(S.textoDaMetaDoPatamar({...plano, valor: ''}), 'A meta é o patamar anterior do território (a maior média de dois anos seguidos), arredondado para cima: ' +
    'uma hipótese que você pode trocar. ');
  // Trocar o território tira a meta, que era do território de antes (o Pará não fica com a meta de Abelardo Luz): o campo fica
  // em branco, à espera de outra, e a data do acréscimo continua. Escolher o mesmo território não muda nada.
  const comTerritorio = {...recuperacao, territorio: 'code:420010'};
  const trocado = S.aoTrocarDeTerritorio(comTerritorio, 'uf:15');
  assert.deepEqual([trocado.territorio, trocado.cenarios[0].planejamento], ['uf:15', {...plano, meta: 'valor', valor: '', referencia: ''}]);
  assert.equal(S.pendenciaDoPedido({...comTerritorio, ...trocado}), 'Informe a meta: um número acima de zero.');
  assert.deepEqual(S.aoTrocarDeTerritorio(comTerritorio, 'code:420010'), {territorio: 'code:420010'});
  const digitada = {...comTerritorio, cenarios: [{...recuperacao.cenarios[0], planejamento: {...plano, meta: 'valor', valor: '30'}}]};
  assert.equal(S.aoTrocarDeTerritorio(digitada, 'uf:15').cenarios[0].planejamento.valor, '', 'a meta digitada para um território também sai');
  // Sem meta (acrescentar, retirar ou só continuar), a troca de território só troca o território.
  const semMeta = {...comTerritorio, cenarios: [S.comOTeste(recuperacao.cenarios[0], 'acrescentar', '202506')]};
  assert.deepEqual(S.aoTrocarDeTerritorio(semMeta, 'uf:15'), {territorio: 'uf:15'});
  // Na tela: o gráfico desenha a meta (uma linha na altura dela), o caminho do cenário com o acréscimo e a marca em cada data
  // em que o acréscimo entra; a legenda diz o que é cada um.
  const tela = ler('SimuladorDeCenarios.tsx');
  const grafico = tela.slice(tela.indexOf('function GraficoDoCenario('), tela.indexOf('export default function SimuladorDeCenarios('));
  for (const id of ['simulador-plano-no-grafico', 'simulador-meta-linha', 'simulador-plano-curva', 'simulador-plano-evento', 'simulador-meta-legenda'])
    assert.equal(grafico.split('data-testid="' + id + '"').length - 1, 1, id);
  assert.ok(grafico.includes('const planos = calculados.filter(cenario => cenario.planejamento?.meta && (cenario.planejamento.estado === "calculado" || ' +
    'cenario.planejamento.estado === "ja_alcancada"))'));
  assert.ok(grafico.includes('...planos.flatMap(item => [item.meta, ...item.plano.trajetoria.map(ponto => ponto.total)])'), 'a meta e o caminho entram na escala');
  assert.ok(grafico.includes('{plano.trajetoria.length > 0 && <path data-testid="simulador-plano-curva" d={caminho([origem, ...plano.trajetoria.map(ponto =>'));
  assert.ok(grafico.includes('"; linha contínua: o cenário com o acréscimo que alcança a meta (▼ na data do acréscimo)"'));
  assert.ok(grafico.includes('plano.estado === "ja_alcancada" ? "; o cenário já chega a ela, sem acréscimo" : ""'));
});

test('revisão das capturas de 15/11/2026: o singular com 1, a faixa inteira de um lado da linha, o aviso único da seleção e os gráficos na largura da tela', () => {
  // "Acrescentar 1 profissional", "2 profissionais": o nome concorda com o número digitado (em branco ou sem número, o plural).
  const OUTRA = {...S.NOMES_DO_BRASIL, profissional: 'enfermeiro', profissionais: 'enfermeiros'};
  assert.deepEqual(['1', '1,0', '2', '', 'x', '0', '1,5', 1, 3].map(quantidade => S.nomeNoNumero(quantidade)),
    ['médico', 'médico', 'médicos', 'médicos', 'médicos', 'médicos', 'médicos', 'médico', 'médicos']);
  assert.deepEqual(['1', '2', ''].map(quantidade => S.nomeNoNumero(quantidade, OUTRA)), ['enfermeiro', 'enfermeiros', 'enfermeiros']);
  const tela = ler('SimuladorDeCenarios.tsx');
  assert.ok(tela.includes('{nomeNoNumero(cenarioDoSimples.intervencoes[0].quantidade, r)} em{" "}'));
  assert.ok(tela.includes('{nomeNoNumero(metaNoCampo(cenarioDoSimples.planejamento), r)} na data final, com um acréscimo em{" "}'));
  // A faixa pode ficar inteira de um lado da linha do cenário (a de 5 em cada 10 de um estado, em 4 anos): a frase diz o que isso
  // quer dizer. Com a linha dentro da faixa (ou na borda dela), sem faixa ou sem cenário calculado, nada.
  const [calculado, retirada] = S.normalizarSimulador(BRUTO).territorios[0].cenarios;
  const com = (total, inferior, superior) => ({...calculado, final: {...calculado.final, total, faixa: {...calculado.final.faixa, inferior, superior}}});
  const fora = lado => ' A faixa fica inteira ' + lado + ' da linha do cenário: no passado da base, neste porte e neste prazo, o número observado ficou, na maior ' +
    'parte dos casos, ' + lado + ' do que esta forma de projetar dava.';
  assert.deepEqual([com(60, 48.2, 74.9), com(60, 61, 74.9), com(60, 40, 59.5), com(60, 60, 70), com(60, 50, 60), {...calculado, final: {...calculado.final, faixa: null}},
    retirada].map(S.faixaSemALinha), ['', fora('acima'), fora('abaixo'), '', '', '', '']);
  assert.ok(S.textoDaFaixa(com(60, 61, 74.9)).endsWith(' Conferida com o que veio depois.' + fora('acima')));
  assert.ok(S.textoDaFaixa(com(60, 48.2, 74.9)).endsWith(' Conferida com o que veio depois.'));
  // No modo avançado, de onde vem a seleção é dito numa mensagem só: quando ela não acompanha a seleção principal, a própria frase
  // vira o aviso (antes, um aviso amarelo repetia a frase de cima).
  assert.equal(tela.split('data-testid="simulador-origem-da-selecao"').length - 1, 1);
  assert.equal(tela.split('data-testid="simulador-nao-acompanha"').length - 1, 1);
  assert.match(tela, /<p data-testid="simulador-origem-da-selecao" data-acompanha=\{config\.acompanha \? "true" : "false"\} role=\{config\.acompanha \? undefined : "status"\}\s+className=\{config\.acompanha \? "ferramenta-apoio" : "ferramenta-exploratorio"\}>/);
  assert.ok(tela.includes('<span data-testid="simulador-nao-acompanha">{config.doDetector ? <><strong>não acompanha</strong> a seleção principal ({p.resumoDaPrincipal}).</>'));
  assert.ok(!tela.includes('<p data-testid="simulador-nao-acompanha"'), 'o aviso separado saiu');
  // Os gráficos das ferramentas são desenhados na largura que têm na tela: o texto mantém 12 px também no celular, onde o gráfico
  // fica mais alto e mostra menos datas no eixo.
  const grafico = tela.slice(tela.indexOf('function GraficoDoCenario('), tela.indexOf('export default function SimuladorDeCenarios('));
  assert.ok(grafico.includes('const [refDoGrafico, medida] = useLargura(760, semDesenho);'), 'a medida recomeça quando o desenho aparece');
  assert.ok(grafico.includes('const { largura, altura, estreito } = tamanhoDoGrafico(medida, 860, 300, 340);'));
  assert.ok(grafico.includes('const passoDosAnos = Math.max(1, Math.ceil(anos.length / (estreito ? 5 : 10)));'));
  assert.ok(grafico.includes('const espacoDoSimulado = largura - xDoUltimo - 4;'));
  assert.ok(grafico.includes('const nomeDoSimulado = espacoDoSimulado >= 118 ? "simulado (hipótese)" : espacoDoSimulado >= 52 ? "simulado" : "";'));
  assert.ok(grafico.includes('{nomeDoSimulado && <text x={xDoUltimo + 4} y={topo + 11} className="ferramenta-serie-texto">{nomeDoSimulado}</text>}'));
  assert.ok(grafico.includes('<figure ref={refDoGrafico as RefObject<HTMLElement>} data-testid="simulador-grafico" data-largura={largura}'));
  assert.ok(!/const largura = \d/.test(grafico), 'nenhuma largura fixa no gráfico do cenário');
  const painelChart = ler('PainelChart.tsx');
  assert.ok(painelChart.includes('export function useLargura(inicial = 900, chave: unknown = null): [RefObject<HTMLElement>, number] {') &&
    painelChart.includes('  }, [chave]);'));
  for (const trecho of ['export function tamanhoDoGrafico(medida: number, larguraMaxima: number, altura: number, alturaNoEstreito: number): { largura: number;',
    'const largura = Math.max(280, Math.min(larguraMaxima, Math.round(medida)));', 'const estreito = largura < 560;',
    'return { largura, altura: estreito ? alturaNoEstreito : altura, estreito };']) assert.ok(painelChart.includes(trecho), trecho);
});

test('etapa 7: a comparação pela diferença, pela razão ou pela taxa, com a população igual ou crescendo x% ao ano, e as premissas padrão', () => {
  const inicial = S.configInicial({municipios: ['code:130260'], estados: [], conjuntos: []}, '202406');
  const avancado = {...inicial, modo: 'avancado', referencias: [R2]};
  // "Comparar … por": a diferença (o padrão), a razão ou a taxa por 1.000 habitantes (Proposta V3, seção C.5).
  assert.deepEqual([{}, {metrica: 'quantidade'}, {forma: 'razao'}, {metrica: 'taxa'}, {metrica: 'taxa', forma: 'razao'}].map(S.modoDaComparacao),
    ['diferenca', 'diferenca', 'razao', 'taxa', 'taxa']);
  assert.deepEqual(['diferenca', 'razao', 'taxa'].map(S.comAComparacao),
    [{metrica: undefined, forma: undefined}, {metrica: undefined, forma: 'razao'}, {metrica: 'taxa', forma: undefined}]);
  // O pedido: nada no padrão; a forma, pela razão; por taxa, a métrica e, com a população crescendo, a taxa de crescimento (zero é
  // a população constante). Sem a hipótese "crescendo" escolhida, um número guardado não vai; sem referências ou no modo simples,
  // não há comparação a pedir.
  const pede = parte => S.pedidoDoSimulador({...avancado, ...parte}).comparacao ?? null;
  assert.deepEqual([pede({}), pede({forma: 'razao'}), pede({metrica: 'taxa'}), pede({metrica: 'taxa', forma: 'razao'}),
    pede({metrica: 'taxa', populacao: 'crescendo', populacaoPct: '1,5'}), pede({metrica: 'taxa', populacao: 'crescendo', populacaoPct: '-2'}),
    pede({metrica: 'taxa', populacao: 'crescendo', populacaoPct: '0'}), pede({metrica: 'taxa', populacaoPct: '3'}), pede({populacao: 'crescendo', populacaoPct: '3'})],
    [null, {forma: 'razao'}, {metrica: 'taxa'}, {metrica: 'taxa'}, {metrica: 'taxa', populacao_pct_ao_ano: 1.5}, {metrica: 'taxa', populacao_pct_ao_ano: -2},
      {metrica: 'taxa'}, {metrica: 'taxa'}, null]);
  assert.deepEqual(['comparacao' in S.pedidoDoSimulador({...avancado, referencias: [], forma: 'razao'}),
    'comparacao' in S.pedidoDoSimulador({...avancado, modo: 'simples', forma: 'razao'})], [false, false]);
  // O que falta para calcular: com a população crescendo, a taxa é um número entre −20 e 20 — só quando ela vai no pedido.
  const cresce = pct => ({...avancado, metrica: 'taxa', populacao: 'crescendo', populacaoPct: pct});
  const falta = 'Informe o crescimento da população: um número entre −20 e 20 (% ao ano).';
  assert.deepEqual(['', 'x', '21', '-20,5', '20', '-20', '1,5', '0'].map(pct => S.pendenciaDoPedido(cresce(pct))), [falta, falta, falta, falta, null, null, null, null]);
  assert.deepEqual([{modo: 'simples'}, {referencias: []}, {metrica: 'quantidade'}, {populacao: undefined}].map(parte => S.pendenciaDoPedido({...cresce(''), ...parte})),
    [null, null, null, null]);
  assert.equal(S.MAX_CRESCIMENTO_DA_POPULACAO, 20);
  // A resposta: a forma de cada comparação e, no cálculo, a forma e a hipótese de população (a taxa por ano, quando ela cresce).
  const base = {versao: 'v', territorios: [{id: 'a', cenarios: [{id: 'c1', estado: 'calculado', comparacoes: [{id: 'r1', forma: 'razao', metrica: 'taxa'}, {id: 'r2'}]}]}]};
  const lida = S.normalizarSimulador({...base, comparacao: {metrica: 'taxa', forma: 'razao', populacao_pct_ao_ano: 2, hipotese_de_populacao: 'crescendo 2% ao ano'}});
  assert.deepEqual(lida.comparacao, {metrica: 'taxa', forma: 'razao', populacaoPctAoAno: 2, hipoteseDePopulacao: 'crescendo 2% ao ano'});
  assert.deepEqual(lida.territorios[0].cenarios[0].comparacoes.map(comparacao => comparacao.forma), ['razao', 'diferenca']);
  assert.deepEqual(S.normalizarSimulador({...base, comparacao: {metrica: 'taxa', populacao_pct_ao_ano: 'x'}}).comparacao,
    {metrica: 'taxa', forma: 'diferenca', populacaoPctAoAno: null, hipoteseDePopulacao: null});
  // As premissas no padrão: o jeito de projetar e a janela que a base escolheu, a faixa de 8 em cada 10, a permanência total e a
  // comparação pela diferença. O que testar, as datas e as referências não são premissas.
  const cen = (extra = {}) => ({...S.novoCenario('c1', 'Cenário 1'), ...extra});
  const acrescimo = {tipo: 'acrescimo', quantidade: '5', em: '202501', periodica: false, ate: '202501', aCadaMeses: '12', permanencia: '90'};
  assert.deepEqual([inicial, avancado, {...inicial, faixa: 8}, {...inicial, metrica: 'quantidade'}, {...inicial, populacao: 'crescendo', populacaoPct: '2'},
    {...inicial, cenarios: [cen({intervencoes: [{...acrescimo, permanencia: '100'}]})]}, {...inicial, cenarios: [cen({intervencoes: [{...acrescimo, permanencia: ''}]})]}]
    .map(S.premissasNoPadrao), [true, true, true, true, true, true, true]);
  assert.deepEqual([{janela: {inicio: '201906', fim: '202406'}}, {janelaDoDetector: {inicio: '201801', fim: '202106'}}, {faixa: 5}, {metrica: 'taxa'}, {forma: 'razao'},
    {cenarios: [cen({metodo: 'M1'})]}, {cenarios: [cen({janela: {inicio: '202106', fim: '202406'}})]}, {cenarios: [cen({intervencoes: [acrescimo]})]},
    {cenarios: [cen({planejamento: {...S.novoPlano('202506'), valor: '30', permanencia: '80'}})]}].map(parte => S.premissasNoPadrao({...inicial, ...parte})),
    Array(9).fill(false));
  // "Voltar ao padrão": todas as premissas de volta, de uma vez; o cenário (a quantidade, a data, a meta, as referências, o
  // território e a data final) fica como estava.
  const cheio = {...inicial, modo: 'avancado', janela: {inicio: '201906', fim: '202406'}, janelaDoDetector: {inicio: '201801', fim: '202106'}, faixa: 5, metrica: 'taxa',
    forma: 'razao', populacao: 'crescendo', populacaoPct: '2', referencias: [R2], territorio: 'code:130260', horizonte: '202806',
    cenarios: [cen({metodo: 'manual', taxaManual: '1,5', janela: {inicio: '202106', fim: '202406'}, intervencoes: [acrescimo],
      planejamento: {...S.novoPlano('202506'), valor: '30', permanencia: '80'}})]};
  const volta = S.comAsPremissasPadrao(cheio), depois = {...cheio, ...volta};
  assert.deepEqual(Object.keys(volta).sort(), ['cenarios', 'faixa', 'forma', 'janela', 'janelaDoDetector', 'metrica', 'populacao', 'populacaoPct']);
  assert.deepEqual([volta.janela, volta.janelaDoDetector, volta.faixa, volta.metrica, volta.forma, volta.populacao, volta.populacaoPct],
    [null, undefined, undefined, undefined, undefined, undefined, undefined]);
  assert.deepEqual(volta.cenarios, [cen({intervencoes: [{...acrescimo, permanencia: '100'}], planejamento: {...S.novoPlano('202506'), valor: '30', permanencia: '100'}})]);
  assert.equal(S.premissasNoPadrao(depois), true);
  assert.deepEqual([depois.referencias, depois.territorio, depois.horizonte, depois.modo, depois.local], [[R2], 'code:130260', '202806', 'avancado', cheio.local]);
  assert.deepEqual(S.pedidoDoSimulador(depois).cenarios[0], {id: 'c1', nome: 'Cenário 1', metodo: 'padrao',
    intervencoes: [{tipo: 'acrescimo', quantidade: 5, em: '202501'}], planejamento: {meta: {tipo: 'valor', valor: 30}, em: '202506'}});
  assert.deepEqual(['janela' in S.pedidoDoSimulador(depois), 'faixa' in S.pedidoDoSimulador(depois), 'comparacao' in S.pedidoDoSimulador(depois)], [false, false, false]);
  // A janela igual à que a base escolheu vale como o padrão (sem janela escolhida); outra janela fica como foi escolhida.
  assert.deepEqual(S.janelaPadrao(COMPETENCIAS), {inicio: '202106', fim: '202406'});
  assert.deepEqual([{inicio: '202106', fim: '202406'}, {inicio: '201906', fim: '202406'}, {inicio: '202106', fim: '202401'}].map(janela => S.janelaOuPadrao(janela, COMPETENCIAS)),
    [null, {inicio: '201906', fim: '202406'}, {inicio: '202106', fim: '202401'}]);
  // O tempo da janela, em palavras (as opções da frase da janela), também numa base só com anos.
  assert.deepEqual([['202106', '202406'], ['202306', '202406'], ['202401', '202406'], ['201401', '202406'], ['202301', '202401'], ['202305', '202406'],
    ['202000', '202300'], ['202200', '202300']].map(([de, ate]) => S.tempoEntre(de, ate)),
    ['3 anos', '1 ano', '5 meses', '10 anos e 5 meses', '1 ano', '1 ano e 1 mês', '3 anos', '1 ano']);
  // O cenário exportado leva a forma e a hipótese de população (só quando não são o padrão), e a importação as repõe.
  const exportado = JSON.parse(S.exportarCenario(cheio, {versaoDoMetodo: 'v', versaoDaBase: 'abc', ultimoRegistro: '202406', quando: 'q'}));
  assert.deepEqual([exportado.metrica, exportado.forma, exportado.populacao, exportado.populacao_pct], ['taxa', 'razao', 'crescendo', '2']);
  const importado = S.importarCenario(JSON.stringify(exportado)).config;
  assert.deepEqual([importado.metrica, importado.forma, importado.populacao, importado.populacaoPct], ['taxa', 'razao', 'crescendo', '2']);
  const semNada = JSON.parse(S.exportarCenario(inicial, {versaoDoMetodo: '', versaoDaBase: '', ultimoRegistro: '', quando: ''}));
  assert.deepEqual(['forma' in semNada, 'populacao' in semNada, 'populacao_pct' in semNada], [false, false, false]);
  const estranho = S.importarCenario(JSON.stringify({...exportado, populacao: 'outra', forma: 'x'})).config;
  assert.deepEqual(['forma' in estranho, 'populacao' in estranho, 'populacaoPct' in estranho], [false, false, false]);
});

test('etapa 7: o "(Entenda)" geral no título, um "Voltar ao padrão" único e as premissas em frases com campos', () => {
  // O "(Entenda)" geral: três frases simples e um exemplo, com o nome que a base dá à contagem.
  const entenda = S.entendaDoSimulador();
  assert.equal(entenda.texto, 'Mostra para onde o território iria se continuasse como vinha, e o efeito das mudanças que você quer testar. O “como vinha” e a ' +
    'margem de erro vêm da própria base: o Agente refaz no passado a projeção que teria feito e confere com o que aconteceu depois. Todo resultado é um ' +
    'cenário hipotético, nunca uma previsão.');
  assert.equal(entenda.exemplo, 'Com 22 médicos no último registro, “continuar como vinha” pode levar a 25 dois anos depois; com 5 acrescentados, a 30. Os ' +
    'números deste exemplo são ilustrativos.');
  assert.equal(entenda.texto.split('. ').length, 3, 'duas ou três frases');
  assert.ok(S.entendaDoSimulador({...S.NOMES_DO_BRASIL, profissional: 'enfermeiro', profissionais: 'enfermeiros'}).exemplo.startsWith('Com 22 enfermeiros no último registro'));
  const tela = ler('SimuladorDeCenarios.tsx');
  assert.ok(tela.includes('const doSimulador = entendaDoSimulador(nomesDaBase);'));
  assert.match(tela, /<div className="ferramenta-titulo-linha">\s+<h2 id="simulador-titulo" data-testid="simulador-titulo" tabIndex=\{-1\} className="analise-titulo">Simulador de Cenários Territoriais<\/h2>\s+<Entenda sobre="Simulador de Cenários" texto=\{doSimulador\.texto\} exemplo=\{doSimulador\.exemplo\} testid="simulador-entenda-ferramenta"\s+completaHref=\{linkDaFicha\(BASE, "simulador", SECOES_DAS_FICHAS\.simulador\.ferramenta\)\}\/>/);
  // Um "Voltar ao padrão" só, sempre à vista (fora das etapas), desligado enquanto as premissas são as do padrão. Os atalhos de
  // volta de antes — "Janela padrão (3 anos)" e "Voltar ao jeito escolhido pela base" — saíram.
  assert.ok(tela.includes('const noPadrao = premissasNoPadrao(config);'));
  assert.match(tela, /<button type="button" data-testid="simulador-voltar-ao-padrao" className="analise-botao-secundario" disabled=\{noPadrao\}[\s\S]{0,400}?onClick=\{\(\) => mudar\(comAsPremissasPadrao\(config\)\)\}><RotateCcw size=\{14\} aria-hidden="true"\/>Voltar ao padrão<\/button>/);
  assert.equal(tela.split('Voltar ao padrão</button>').length - 1, 1, 'um botão só');
  assert.ok(tela.indexOf('data-testid="simulador-voltar-ao-padrao"') < tela.indexOf('{config.modo === "simples" && <div data-testid="simulador-simples"'), 'antes dos dois modos');
  for (const fora of ['simulador-janela-padrao', 'Janela padrão (3 anos)', 'Voltar ao jeito escolhido pela base']) assert.ok(!tela.includes(fora), fora);
  // As premissas em frases, com os campos dentro delas (seção C.5): a janela, o jeito de projetar, a permanência (na intervenção e
  // no planejamento inverso) e a comparação. A faixa já era uma frase. Os campos mantêm os identificadores de antes.
  for (const id of ['simulador-frase-da-janela', 'simulador-frase-do-jeito', 'simulador-frase-da-permanencia', 'simulador-frase-da-permanencia-do-plano',
    'simulador-frase-da-comparacao', 'simulador-janela-inicio', 'simulador-janela-fim', 'simulador-metodo', 'simulador-taxa-manual', 'simulador-cenario-janela-inicio',
    'simulador-cenario-janela-fim', 'simulador-intervencao-permanencia', 'simulador-plano-permanencia', 'simulador-metrica', 'simulador-populacao',
    'simulador-populacao-pct', 'simulador-faixa-em-10']) assert.equal(tela.split('data-testid="' + id + '"').length - 1, 1, id);
  for (const id of ['simulador-janela-inicio', 'simulador-janela-fim', 'simulador-metodo', 'simulador-taxa-manual', 'simulador-cenario-janela-inicio',
    'simulador-cenario-janela-fim', 'simulador-intervencao-permanencia', 'simulador-plano-permanencia', 'simulador-metrica', 'simulador-populacao',
    'simulador-populacao-pct', 'simulador-faixa-em-10'])
    assert.match(tela, new RegExp('<(select|input) data-testid="' + id + '"( inputMode="(decimal|numeric)")? className="ferramenta-campo-da-frase"'), id);
  assert.ok(!/<label className="analise-rotulo-campo">(Método da base do cenário|Janela própria: de|Janela histórica: de|Permanência \(% ao ano\))/.test(tela),
    'nenhuma dessas premissas fica num campo com rótulo solto');
  assert.ok(tela.includes('<p data-testid="simulador-frase-da-janela" data-padrao={config.janela ? "false" : "true"} className="ferramenta-frase">Janela histórica: o crescimento é'));
  assert.ok(tela.includes('{tempoEntre(c, janela?.fim ?? ultimoRegistro) + " (desde " + competenciaCurta(c) + ")"}</option>)}'));
  assert.equal(tela.split('janelaOuPadrao(').length - 1, 4, 'os dois campos e os dois atalhos da janela');
  // Sem janela escolhida, a frase mostra a janela padrão — a do último cálculo só quando ele foi feito com a janela padrão: depois
  // de "Voltar ao padrão", a janela de um cálculo anterior feito com outra janela não aparece como se fosse a que vale.
  assert.ok(tela.includes('const janela = config.janela ?? (resposta?.janela.padrao ? resposta.janela : null) ?? janelaPadrao(p.competencias);'));
  assert.ok(!tela.includes('config.janela ?? resposta?.janela ??'));
  assert.ok(tela.includes('<p data-testid="simulador-frase-do-jeito" className="ferramenta-frase">Forma de projetar:{" "}'));
  assert.ok(tela.includes('<option value="">a janela geral</option>') && tela.includes('<option key={c} value={c}>uma janela própria, desde {competenciaCurta(c)}</option>)}'));
  assert.ok(tela.includes('? "Do efeito da retirada, a cada ano permanecem" : "Dos " + r.profissionais + " acrescentados, a cada ano permanecem"}{" "}'));
  assert.ok(tela.includes('Dos {r.profissionais} acrescentados, a\n            cada ano permanecem{" "}'));
  assert.ok(tela.includes('Comparar cada cenário com {referencias.length === 1 ? "a referência" : "as referências"} por{" "}'));
  assert.match(tela, /<select data-testid="simulador-metrica" className="ferramenta-campo-da-frase" aria-label="Comparar por" value=\{modoDaComparacao\(config\)\}\s+onChange=\{event => mudar\(comAComparacao\(event\.target\.value as ModoDaComparacao\)\)\}>\s+<option value="diferenca">diferença \(em \{r\.profissionais\}\)<\/option>\s+<option value="razao">razão \(quantas vezes o valor da referência\)<\/option>\s+<option value="taxa">taxa por 1\.000 habitantes<\/option>/);
  assert.match(tela, /\{config\.metrica === "taxa" && <>, com a população\{" "\}\s+<select data-testid="simulador-populacao" className="ferramenta-campo-da-frase" aria-label="Hipótese de população" value=\{config\.populacao \?\? "constante"\}\s+onChange=\{event => mudar\(\{ populacao: event\.target\.value === "crescendo" \? "crescendo" : undefined \}\)\}>\s+<option value="constante">igual à do último registro \(\{competenciaCurta\(ultimoRegistro\)\}\)<\/option>\s+<option value="crescendo">crescendo<\/option>/);
  assert.ok(tela.includes('value={config.populacaoPct ?? ""} placeholder="0,0" onChange={event => mudar({ populacaoPct: event.target.value })}/>% ao ano depois dele (uma'));
  // As listas dentro das frases têm largura para o texto da opção, e a frase da permanência ocupa a linha inteira do bloco.
  const css = ler('analise.css');
  assert.ok(css.includes('select.ferramenta-campo-da-frase { max-width: min(100%, 30em); text-align: left; }'));
  assert.ok(css.includes('.ferramenta-frase-inteira { grid-column: 1 / -1; }'));
});

test('etapa 7: numa planilha, o grupo de cima entra como unidade — a seleção das ferramentas, a busca do Simulador e os motivos com os nomes da base', () => {
  // A regra de acrescentar um território com uma planilha: o grupo de cada unidade vem da base (e não do código IBGE), e os
  // motivos usam os nomes dela, com a concordância ("a zona desta área").
  const zonas = {'code:A00': 'Norte', 'code:A01': 'Norte', 'code:A10': 'Sul', 'code:A11': 'Sul'};
  const daPlanilha = {grupoDe: id => zonas[id] ?? '',
    r: {...S.NOMES_DO_BRASIL, profissional: 'posto', profissionais: 'postos', unidade: 'área', unidades: 'áreas', grupo: 'zona', grupos: 'zonas', todo: 'a base toda'},
    formas: {...S.FORMAS_DO_BRASIL, oUnidade: 'a área', osUnidades: 'as áreas', oGrupo: 'a zona', osGrupos: 'as zonas', dosGrupos: 'das zonas'}};
  const local = {municipios: ['code:A00', 'code:A10'], estados: [], conjuntos: [{id: 'c1', rotulo: 'Par do Sul', membros: ['code:A10', 'code:A11']}]};
  const tentar = (de, tipo, id, grupo) => S.acrescentarTerritorio(de, {tipo, id, grupo}, daPlanilha);
  // A zona como unidade tira da seleção local as áreas dela (a zona inteira já as conta); as das outras zonas ficam.
  const comNorte = tentar(local, 'estado', 'Norte', 'Norte');
  assert.deepEqual(comNorte, {local: {...local, municipios: ['code:A10'], estados: ['Norte']}, motivo: null});
  assert.equal(tentar(local, 'estado', 'Sul', 'Sul').motivo, 'O conjunto Par do Sul tem áreas nesta zona: tire o conjunto para usar a zona como unidade.');
  assert.equal(tentar(comNorte.local, 'estado', 'Norte', 'Norte').motivo, 'Esta zona já está na seleção do Simulador.');
  assert.equal(tentar(comNorte.local, 'municipio', 'code:A01', 'Norte').motivo, 'A zona desta área está na seleção como unidade: tire a zona para usar a área.');
  assert.deepEqual(tentar(comNorte.local, 'municipio', 'code:A11', 'Sul').local.municipios, ['code:A10', 'code:A11']);
  // O pedido leva a zona em `estados_unidade`, como o estado na base do Brasil, e o território dela é "uf:<zona>".
  assert.deepEqual(S.selecaoLocalParaOPedido(comNorte.local), {base: {municipios: {todos: false, estados: [], ids: ['code:A10']}}, estados_unidade: ['Norte'],
    conjuntos: [{id: 'c1', rotulo: 'Par do Sul', membros: ['code:A10', 'code:A11']}]});
  assert.deepEqual(S.territoriosDaSelecaoLocal(comNorte.local, {unidade: id => id, grupo: grupo => grupo + ' (zona)', todo: 'a base toda'}).map(item => item.id),
    ['code:A10', 'uf:Norte', 'c1']);
  // Sem a planilha, a regra e os motivos são os de antes (o estado pelo código IBGE).
  const doBrasil = {municipios: ['code:410690', 'code:130260'], estados: [], conjuntos: []};
  assert.deepEqual(S.acrescentarTerritorio(doBrasil, {tipo: 'estado', id: '41', grupo: '41'}), {local: {municipios: ['code:130260'], estados: ['41'], conjuntos: []}, motivo: null});
  // Na tela: a busca do Simulador oferece o grupo de cima em qualquer base (nos territórios e nas referências), com o nome que a
  // base dá a ele; a seleção das ferramentas não tira mais o grupo de cima da planilha — só o nível acima dele fica fora.
  const tela = ler('SimuladorDeCenarios.tsx'), area = ler('AreaDeAnalise.tsx');
  assert.ok(tela.includes('estados: p.grupos.filter(g => sem(g.nome + " " + g.sigla).includes(pedido)).slice(0, 4),') && !tela.includes('estados: daPlanilha ? []'));
  assert.ok(tela.includes('acrescentarTerritorio(config!.local, alvo, daPlanilha && p.grupoDe ? { grupoDe: p.grupoDe, r: nomesDaBase, formas } : undefined);'));
  assert.ok(tela.includes('{g.nome} como {r.grupo} (unidade)</button></li>)}') && tela.includes('{g.nome} ({r.grupo})</button></li>)}'));
  assert.ok(tela.includes('? r.unidade + (p.grupos.length ? ", " + r.grupo : "") + " ou " + formas.oTodo : "município, estado ou o Brasil"}), só no Simulador'));
  assert.ok(tela.includes('? r.unidade + (p.grupos.length ? " ou " + r.grupo : "") : "município ou estado"})'));
  assert.ok(tela.includes('? r.unidades + (p.grupos.length ? ", " + r.grupos + " como unidade" : "") + " e conjuntos" : "municípios, estados como unidade e conjuntos"}).</>'));
  assert.ok(!/como estado \(unidade\)|\(estado\)<\/button>/.test(tela), 'nenhum "estado" escrito na busca');
  assert.match(area, /if \(tipo === "brasil"\) return completa;\s+if \(def\.nivel === "regioes"\) return null;\s+return Object\.keys\(completa\)\.length \? completa : null;/);
  assert.ok(!area.includes('estados_unidade: _semContagemPropria') && !area.includes('não tem contagem própria'));
  assert.ok(area.includes('const nivelForaDasFerramentas = tipo === "arquivo" && !semSelecao(def) && def.nivel === "regioes";'));
  assert.ok(area.includes('const avisoDasFerramentas = nivelForaDasFerramentas ? "Numa planilha, as ferramentas avaliam " + rotulos.unidade.plural + ", " +'));
});

test('AJ-03: a avaliação dos métodos sai numa exportação, com os números do motor; a ficha metodológica (PDF) e a janela do cálculo na tela', () => {
  // A exportação leva a retroprojeção tal como o motor a mandou (a escolha por nível, os candidatos, as faixas por porte e prazo e a
  // tabela dos erros), com as versões do método e da base, a janela, as notas e as limitações.
  const lida = S.normalizarSimulador(BRUTO);
  assert.deepEqual(lida.retroprojecao.bruta, BRUTO.retroprojecao, 'os campos e os números do motor, sem leitura');
  const avaliacao = JSON.parse(S.avaliacaoDosMetodos(lida, '2026-11-18T12:00:00.000Z'));
  assert.equal(avaliacao.ferramenta, 'Simulador de Cenários Territoriais');
  assert.deepEqual(avaliacao.retroprojecao, BRUTO.retroprojecao);
  assert.deepEqual([avaliacao.versao_do_metodo, avaliacao.fonte.versao, avaliacao.ultimo_registro, avaliacao.janela, avaliacao.notas, avaliacao.limitacoes,
    avaliacao.exportado_em], [BRUTO.versao, BRUTO.fonte.versao, BRUTO.ultimo_registro, lida.janela, lida.notas, lida.limitacoes, '2026-11-18T12:00:00.000Z']);
  assert.ok(avaliacao.conteudo.includes('não é uma análise do território escolhido'));
  assert.ok(!/jeito|convenç/i.test(JSON.stringify({conteudo: avaliacao.conteudo, referencia: avaliacao.referencia})));
  // AJ-07 (18/11/2026): a referência cita a seção da Ficha B pelo título, que não depende da numeração (antes, "seção 6"); o
  // título é o da seção da fonte da ficha.
  assert.equal(avaliacao.referencia, 'Ficha metodológica B — Simulador de Cenários Territoriais (fichas/ficha-simulador.pdf), seção “A avaliação dos métodos no histórico da base”');
  const ficha = readFileSync(new URL('../../Docs/fichas/ficha_simulador.html', import.meta.url), 'utf8');
  const titulo = /<h2 id="avaliacao-titulo">([^<]*)<\/h2>/.exec(ficha)?.[1].replace(/^\d+\.\s*/, '');
  assert.equal(titulo, 'A avaliação dos métodos no histórico da base');
  // A janela do cálculo, no modo avançado (antes, na linha das versões): a do motor, com "(a janela padrão)" quando é ela.
  assert.equal(S.textoDaJanelaDoCalculo({janela: {inicio: '202106', fim: '202406', registros: 7, anos: 3, padrao: true}}),
    'Janela deste cálculo: de jun/2021 a jun/2024 (a janela padrão). Cada cenário parte do último registro usável do território nessa janela.');
  assert.equal(S.textoDaJanelaDoCalculo({janela: {inicio: '201906', fim: '202406', registros: 11, anos: 5, padrao: false}}),
    'Janela deste cálculo: de jun/2019 a jun/2024. Cada cenário parte do último registro usável do território nessa janela.');
  // Na tela: a exportação nova e o link da ficha, no alto, nos dois modos; a exportação fica desligada até haver um cálculo.
  const tela = ler('SimuladorDeCenarios.tsx');
  const acoes = tela.slice(tela.indexOf('<div className="ferramenta-acoes analise-nao-imprimir">'), tela.indexOf('{config.modo === "simples" && <div data-testid="simulador-simples"'));
  assert.ok(acoes.includes('<button type="button" data-testid="simulador-exportar-avaliacao" className="analise-botao-secundario" disabled={!resposta}'));
  assert.ok(acoes.includes('avaliacaoDosMetodos(resposta, new Date().toISOString()), "application/json")}>'));
  assert.ok(acoes.includes('<a data-testid="simulador-ficha" className="analise-botao-secundario" href={linkDaFicha(BASE, "simulador")} target="_blank" rel="noopener">'));
  assert.ok(tela.includes('const BASE = import.meta.env.BASE_URL || "/";'));
  assert.ok(tela.includes('<p data-testid="simulador-janela-do-calculo" className="ferramenta-apoio">{textoDaJanelaDoCalculo(resposta)}</p>'));
  assert.ok(!/Método \{resposta\.versao\}/.test(tela), 'a linha de versões saiu');
});
