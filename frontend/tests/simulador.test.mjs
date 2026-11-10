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
// como referência), a leitura da resposta, os textos da tabela e as exportações (JSON do cenário e CSV dos resultados). Nada é
// projetado na tela: os valores vêm do motor.
const S = await source('simuladorModel');
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
  assert.equal(S.pendenciaDoPedido({...inicial, local: muitos}), 'O Simulador compara até 100 territórios de cada vez; a seleção local tem 101.');
  assert.equal(S.pendenciaDoPedido({...inicial, horizonte: ''}), 'Escolha a data final do cenário.');
  // A taxa é da pessoa: sem ela, o cenário manual não é pedido (o sistema não sugere uma).
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({metodo: 'manual'})]}), 'Informe a taxa anual do cenário “Cenário 1”.');
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({metodo: 'manual', taxaManual: '2,5'})]}), null);
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({intervencoes: [{...S.novaIntervencao('202506'), quantidade: '0'}]})]}),
    'Informe quantos médicos entram ou saem em cada intervenção.');
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({intervencoes: [{...S.novaIntervencao(''), quantidade: '2'}]})]}), 'Informe a data de cada intervenção.');
  assert.equal(S.pendenciaDoPedido({...inicial, cenarios: [cenario({intervencoes: [{...S.novaIntervencao('202506'), periodica: true, ate: '202501'}]})]}),
    'Numa intervenção periódica, a data final vem depois da inicial.');
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
  assert.deepEqual([S.cenariosEmUso(CHEIO).length, S.cenariosEmUso({...CHEIO, modo: 'simples'}).length,
    S.cenariosEmUso({...CHEIO, cenarios: Array.from({length: 8}, (_, k) => S.novoCenario('c' + k, 'x'))}).length], [2, 1, S.MAX_CENARIOS]);
  // Nenhum campo do pedido leva uma taxa sugerida, uma média aritmética ou uma projeção feita na tela.
  assert.equal(/media|sugest|previs/i.test(JSON.stringify(S.pedidoDoSimulador(CHEIO))), false);
  assert.equal(S.METODOS_DA_TELA.some(item => /média aritmética/i.test(item.rotulo)), false);
});

const BRUTO = {versao: 'SIMULADOR-CENARIOS/V2.2/1', fonte: {base: 'Brasil', categoria: 'MEDICINA', versao: 'abc', primeira: '201401', ultima: '202406', competencias: 22},
  competencias: ['201401', '202406'], ultimo_registro: '202406', janela: {inicio: '202106', fim: '202406', registros: 7, anos: 3, padrao: true},
  horizonte: {data: '202606', anos_desde_o_ultimo_registro: 2},
  territorios: [{id: 'code:130260', tipo: 'municipio', nivel: 'municipios', rotulo: 'MANAUS (AM)', uf: 'AM', unidade: 'médicos registrados no município',
    observado: [{competencia: '202401', valor: null, estado: 'ausencia_de_dado'}, {competencia: '202406', valor: 51, estado: 'observado', marca: 'pico_que_volta'}],
    historico: {registros: 7, de: '202106', ate: '202406', anos: 3, taxas_de_junho: [{de: '202106', ate: '202206', taxa_pct: 4.44}], media_aritmetica_pct: 4.26,
      mediana_pct: 4.25, desvio_pct: 0.18, taxa_composta_pct: 4.2603, nota: 'A média aritmética é só descrição.'}, lacunas: ['202401'],
    cenarios: [{id: 'c1', nome: 'Com 4 médicos', estado: 'calculado',
      metodo: {pedido: 'padrao', usado: 'M0d', rotulo: 'persistência com a deriva do estado', padrao: true, provisorio: true, voltou_ao_m0: false, soma: null},
      parametros: {n0: 51, origem: '202406', janela: {inicio: '202106', fim: '202406', registros: 7}, deriva_pct: 3.39},
      avisos: [{codigo: 'HORIZONTE_CAUTELA', texto: 'Cautela: o horizonte passa da metade da janela do método.'}, {codigo: 'X'}],
      horizonte: {anos: 2, aviso: 'cautela'}, faixa: {estado: 'disponivel', motivo: null, porte: '50 a 99', rotulo: 'faixa de 80% da retroprojeção; desloca-se com a intervenção'},
      trajetoria: [{data: '202501', anos: 0.5833, base: 52, intervencao: 4, total: 56, retroprojecao: false, faixa: {inferior: 48.2, superior: 66.4, anos: 1, validada: true}},
        {data: '202606', anos: 2, base: 54.5189, intervencao: 4, total: 58.5189, retroprojecao: false, faixa: {inferior: 48.16, superior: 74.87, anos: 2, validada: true}}],
      final: {data: '202606', base: 54.5189, intervencao: 4, total: 58.5189, faixa: {inferior: 48.16, superior: 74.87, anos: 2, validada: true}},
      texto: 'Cenário hipotético, não é previsão: …; "MANAUS (AM)" teria 59 médicos em jun/2026. Base: registros até jun/2024.'},
    {id: 'm0', nome: 'Persistência (referência)', estado: 'retirada_acima_do_estoque', motivo: 'Em jan/2025, as retiradas passam…', metodo: {pedido: 'M0', usado: 'M0'},
      parametros: {n0: 51, origem: '202406'}, avisos: []},
    {id: 'c3', nome: 'Taxa', estado: 'nao_aplicavel', motivo: 'A taxa composta exige…', metodo: {pedido: 'M1'}},
    {id: 'c4', nome: 'Log', estado: 'nao_calculavel', motivo: 'Série em zero.', metodo: {pedido: 'M3'}}]},
  {id: null, rotulo: 'sem id'},
  {id: 'g1', tipo: 'conjunto', nivel: 'municipios', rotulo: 'Par', unidade: 'soma das contagens dos componentes', membros: ['code:1', 'code:2'],
    nomes_dos_membros: ['A (AM)', 'B (AM)'], observado: [], historico: {}, lacunas: [], cenarios: []}],
  retroprojecao: {origens: ['201706', '202306'],
    faixas: [{porte: '1 a 9', anos: 1, inferior_pct: -26.2, superior_pct: 48.1, casos: 15101, origens: 7, cobertura_pct: 80.0, rotulo: 'validada fora da amostra'}],
    tabela: [{metodo: 'M0d', porte: '1 a 9', anos: 4, casos: 9395, origens: 4, erro_absoluto_medio: 2.1, vies: 1.4, frente_ao_m0: 0.8728},
      {metodo: 'M0', porte: '1 a 9', anos: 4, casos: 9395, origens: 4, erro_absoluto_medio: 2.4, vies: 2.6, frente_ao_m0: null}]},
  notas: ['Cenários hipotéticos.', 7], limitacoes: ['CENARIO_HIPOTETICO']};

test('a resposta do motor vira os tipos da tela, sem calcular nada', () => {
  const lida = S.normalizarSimulador(BRUTO);
  assert.deepEqual(lida.territorios.map(item => item.id), ['code:130260', 'g1'], 'o território sem id fica de fora');
  assert.deepEqual([lida.versao, lida.ultimoRegistro, lida.horizonte, lida.janela], ['SIMULADOR-CENARIOS/V2.2/1', '202406',
    {data: '202606', anosDesdeOUltimoRegistro: 2}, {inicio: '202106', fim: '202406', registros: 7, anos: 3, padrao: true}]);
  const manaus = lida.territorios[0];
  assert.deepEqual(manaus.observado, [{competencia: '202401', valor: null, estado: 'ausencia_de_dado', marca: null},
    {competencia: '202406', valor: 51, estado: 'observado', marca: 'pico_que_volta'}], 'ausência de dado não é zero');
  assert.deepEqual([manaus.historico.taxaCompostaPct, manaus.historico.mediaAritmeticaPct, manaus.historico.taxasDeJunho, manaus.lacunas],
    [4.2603, 4.26, [{de: '202106', ate: '202206', taxaPct: 4.44}], ['202401']]);
  const [calculado, retirada, naoSeAplica, naoCalculavel] = manaus.cenarios;
  assert.deepEqual(calculado.metodo, {pedido: 'padrao', usado: 'M0d', rotulo: 'persistência com a deriva do estado', padrao: true, provisorio: true,
    voltouAoM0: false, soma: null});
  assert.deepEqual(calculado.avisos, [{codigo: 'HORIZONTE_CAUTELA', texto: 'Cautela: o horizonte passa da metade da janela do método.'}], 'o aviso sem texto fica de fora');
  assert.deepEqual(calculado.final, {data: '202606', base: 54.5189, intervencao: 4, total: 58.5189, faixa: {inferior: 48.16, superior: 74.87, anos: 2, validada: true}});
  assert.deepEqual(calculado.trajetoria[0], {data: '202501', anos: 0.5833, base: 52, intervencao: 4, total: 56, retroprojecao: false, observado: null,
    faixa: {inferior: 48.2, superior: 66.4, anos: 1, validada: true}});
  assert.deepEqual([calculado.faixa.estado, calculado.horizonte, calculado.parametros.origem], ['disponivel', {anos: 2, aviso: 'cautela'}, '202406']);
  assert.deepEqual([retirada.estado, retirada.final, retirada.texto, retirada.trajetoria, retirada.faixa.estado],
    ['retirada_acima_do_estoque', null, null, [], 'indisponivel']);
  assert.deepEqual(lida.territorios[1].membros, ['A (AM)', 'B (AM)'], 'os nomes dos componentes do conjunto');
  assert.deepEqual(lida.retroprojecao.faixas[0], {porte: '1 a 9', anos: 1, inferiorPct: -26.2, superiorPct: 48.1, casos: 15101, origens: 7, coberturaPct: 80,
    rotulo: 'validada fora da amostra'});
  assert.deepEqual(lida.retroprojecao.tabela.map(linha => linha.frenteAoM0), [0.8728, null]);
  assert.deepEqual(lida.notas, ['Cenários hipotéticos.']);
  // Uma resposta vazia não quebra a tela.
  assert.deepEqual(S.normalizarSimulador(null).territorios, []);
  // Os textos da tabela: o valor com a faixa, ou o estado em palavras (nunca um número inventado).
  assert.deepEqual([calculado, retirada, naoSeAplica, naoCalculavel].map(S.textoDoFinal),
    ['58,5 (48,2 a 74,9)', 'retirada acima do estoque: rever', 'não se aplica', 'não calculável']);
  assert.deepEqual([S.formatarMedicos(51), S.formatarMedicos(58.5189), S.formatarMedicos(14771.16), S.formatarTaxa(4.2603), S.formatarTaxa(-12.642), S.formatarTaxa(0)],
    ['51', '58,5', '14.771,2', '+4,26%', '−12,64%', '0,00%']);
  // A faixa de 80%, em linguagem simples: o que ela é e, de 3 a 4 anos, que é um limite provisório; sem faixa, indisponível.
  assert.equal(S.textoDaFaixa(calculado), 'Faixa de 80% em jun/2026: de 48,2 a 74,9 médicos. No passado da base, em 8 de cada 10 casos de municípios do mesmo ' +
    'porte, o número observado ficou dentro dessa margem; ela acompanha a intervenção. Conferida com dados que não entraram no cálculo dela.');
  const longe = {...calculado, final: {...calculado.final, faixa: {...calculado.final.faixa, anos: 4, validada: false}}};
  assert.ok(S.textoDaFaixa(longe, true).endsWith('municípios com o porte desta soma (uma aproximação para o conjunto), o número observado ficou dentro dessa ' +
    'margem; ela acompanha a intervenção. Limite provisório: para 3 e 4 anos, a margem ainda não foi conferida com dados à parte.'));
  assert.equal(S.textoDaFaixa({...calculado, final: {...calculado.final, faixa: null}}),
    'Faixa de 80%: indisponível nesta data: ela vai só até 4 anos depois do último registro usado.');
  assert.equal(S.textoDaFaixa({...calculado, final: {...calculado.final, faixa: null}, faixa: {estado: 'indisponivel', motivo: 'Não há faixa para estados como unidade.', rotulo: null}}),
    'Faixa de 80%: indisponível. Não há faixa para estados como unidade.');
  assert.deepEqual(['M0', 'M0d', 'M1'].map(metodo => S.NOME_CURTO_DO_METODO[metodo]),
    ['último valor mantido', 'último valor com o crescimento do estado', 'taxa composta da janela']);
  // Linguagem simples nos textos da tela (decisão D-C): os termos técnicos ficam nos detalhes, na documentação e nas exportações.
  const semComentarios = codigo => codigo.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/.*$/gm, '');
  const codigo = semComentarios(readFileSync(new URL('../src/simuladorModel.ts', import.meta.url), 'utf8')) +
    semComentarios(readFileSync(new URL('../src/SimuladorDeCenarios.tsx', import.meta.url), 'utf8'));
  for (const termo of ['deriva', 'candidato', 'não calibrado', 'limiar', 'Theil', 'Poisson', 'fora da amostra', 'média aritmética como'])
    assert.ok(!codigo.includes(termo), termo);
  // As contas da data final: a base do cenário e a intervenção, separadas.
  assert.equal(S.contasDoFinal(calculado), 'Na data final: base do cenário de 54,5 médicos + 4 da intervenção = 58,5 médicos (o texto acima arredonda para o inteiro).');
  assert.equal(S.contasDoFinal({...calculado, final: {...calculado.final, intervencao: -3, total: 51.5189}}),
    'Na data final: base do cenário de 54,5 médicos − 3 da intervenção = 51,5 médicos (o texto acima arredonda para o inteiro).');
  assert.equal(S.contasDoFinal({...calculado, final: {...calculado.final, intervencao: 0, total: 54.5189}}), 'Na data final: base do cenário de 54,5 médicos, sem intervenção.');
  assert.equal(S.contasDoFinal(retirada), '');
  // Os limites das faixas, em percentual inteiro: arredondados, nunca truncados.
  assert.deepEqual([-25.6, 48.1, 0.2, 104.4, -0.4].map(S.formatarPercentualInteiro), ['−26%', '+48%', '0%', '+104%', '0%']);
});

test('exportar e importar o cenário (JSON), com a versão do método e da base', () => {
  const exportado = S.exportarCenario(CHEIO, {versaoDoMetodo: 'SIMULADOR-CENARIOS/V2.2/1', versaoDaBase: 'abc', ultimoRegistro: '202406', quando: '2026-11-10T12:00:00.000Z'});
  const lido = JSON.parse(exportado);
  assert.deepEqual([lido.formato, lido.versao_do_metodo, lido.base, lido.exportado_em], ['ADT-CENARIO/1', 'SIMULADOR-CENARIOS/V2.2/1',
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
    cenarios: [{metodo: 'previsao', intervencoes: [{tipo: 'x', em: '202501'}]}, {id: 'k', nome: 'K', metodo: 'M0d'}]})).config;
  assert.deepEqual([tolerante.modo, tolerante.local.municipios, tolerante.local.conjuntos.map(item => item.id), tolerante.cenarios.map(item => item.metodo)],
    ['simples', ['code:1'], ['h'], ['padrao', 'M0d']]);
  assert.deepEqual(tolerante.cenarios[0].intervencoes, [{tipo: 'acrescimo', quantidade: '1', em: '202501', periodica: false, ate: '202501', aCadaMeses: '12',
    permanencia: '100'}]);
});

test('CSV dos resultados: uma linha por território, cenário e data, com a rastreabilidade', () => {
  const csv = S.csvDoSimulador(S.normalizarSimulador(BRUTO));
  assert.equal(csv.charCodeAt(0), 0xFEFF, 'com BOM, para o Excel');
  const linhas = csv.slice(1).split('\r\n');
  assert.equal(linhas.length, 7, 'o cabeçalho, 2 datas do cenário calculado, 3 cenários sem valor e o fim');
  assert.equal(linhas[0], 'Identificador;Território;Tipo;Unidade de contagem;Cenário;Método pedido;Método usado;Estado do cenário;Origem do cenário;' +
    'Médicos na origem;Janela: início;Janela: fim;Data;Natureza;Observado;Base do cenário;Intervenção;Total do cenário;Faixa de 80%: inferior;' +
    'Faixa de 80%: superior;Avisos;Texto do cenário;Versão do método;Versão da base');
  assert.equal(linhas[2], 'code:130260;MANAUS (AM);municipio;médicos registrados no município;Com 4 médicos;padrao;M0d;calculado;202406;51;202106;202406;202606;' +
    'cenário hipotético;;54,5189;4;58,5189;48,16;74,87;HORIZONTE_CAUTELA;"Cenário hipotético, não é previsão: …; ""MANAUS (AM)"" teria 59 médicos em jun/2026. ' +
    'Base: registros até jun/2024.";SIMULADOR-CENARIOS/V2.2/1;abc', 'a precisão integral, com vírgula decimal, e as aspas dobradas');
  assert.equal(linhas[3], 'code:130260;MANAUS (AM);municipio;médicos registrados no município;Persistência (referência);M0;M0;' +
    'retirada_acima_do_estoque: Em jan/2025, as retiradas passam…;202406;51;;;;;;;;;;;;;SIMULADOR-CENARIOS/V2.2/1;abc', 'sem valor inventado');
  assert.ok(linhas[4].includes(';nao_aplicavel: A taxa composta exige…;') && linhas[5].includes(';nao_calculavel: Série em zero.;'));
  assert.ok(linhas.slice(0, 6).every(linha => linha.split(';').length >= 24));
  assert.equal(linhas[6], '');
});
