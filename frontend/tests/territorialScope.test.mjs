import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const {EMPTY_SCOPE, breakdown, countSelected, describeScope, effectiveScope, fromMembers, groupState, municipalOnly,
  periodsForScope, toggle} = await source('territorialScope');

// Regras como o backend as devolve no bloco "niveis" da inspeção (territorial_levels.OPERATION_LEVELS).
const rule = (aceita, padrao, extra = {}) => ({aceita, estado_como: 'objeto', minimo: 1, combinacao: 'blocos', padrao,
  disponivel: true, texto: '', motivos: {}, ...extra});
const DENSITY = rule(['brasil', 'estado', 'municipio'], 'todos_municipios');
const COUNTS = rule(['brasil', 'estado', 'municipio'], 'brasil');
const DISTRIBUTION = rule(['estado', 'municipio'], 'todos_municipios', {combinacao: 'mesmo_nivel', minimo: 2,
  motivos: {brasil: 'Não se aplica: a distribuição agrupa vários territórios, e o Brasil é um só.'}});
const SPATIAL = rule(['municipio'], 'todos_municipios', {estado_como: null, combinacao: 'municipal'});
const AGGREGATE = rule(['estado', 'municipio'], 'todos_municipios', {estado_como: 'expansao', combinacao: 'uniao', minimo: 2});
const ROTATION = rule([], null, {disponivel: false});
const LEVELS = {brasil: {disponivel: true, motivo: '', periodos: ['202306', '202406']},
  estados: [{prefixo: '13', sigla: 'AM', nome: 'Amazonas', rotulo: 'Amazonas (AM)', rotulo_grupo: 'Municípios do Amazonas', municipios: 62},
            {prefixo: '15', sigla: 'PA', nome: 'Pará', rotulo: 'Pará (PA)', rotulo_grupo: 'Municípios do Pará', municipios: 144},
            {prefixo: '35', sigla: 'SP', nome: 'São Paulo', rotulo: 'São Paulo (SP)', rotulo_grupo: 'Municípios de São Paulo', municipios: 645}],
  municipios: {total: 5570}, operacoes: {}};
const NAMES = {'code:130260': 'MANAUS (AM)', 'code:130420': 'TEFE (AM)', 'code:130340': 'PARINTINS (AM)', 'code:350010': 'FORA (SP)'};
const nameOf = id => NAMES[id] || id;
const describe = (scope, ids, r = DENSITY) => describeScope(effectiveScope(scope, ids, r), LEVELS, nameOf);

test('caixa da abrangência territorial: os resumos de antes continuam (só municípios)', () => {
  assert.equal(describeScope(municipalOnly([]), LEVELS, nameOf), 'Todos os municípios');
  assert.equal(describeScope(municipalOnly(['code:130260']), LEVELS, nameOf), 'MANAUS (AM)');
  assert.equal(describeScope(municipalOnly(['code:130260', 'code:130420']), LEVELS, nameOf), 'MANAUS (AM) e TEFE (AM)');
  assert.equal(describeScope(municipalOnly(['code:130260', 'code:130420', 'code:130340', 'code:350010']), LEVELS, nameOf),
    '4 municípios: MANAUS (AM), TEFE (AM) e mais 2');
  // Padrão de cada análise, sem nada marcado: Brasil (Quantitativos) ou todos os municípios (Densidade).
  assert.equal(describe(EMPTY_SCOPE, [], COUNTS), 'Brasil (total nacional)');
  assert.equal(describe(EMPTY_SCOPE, [], DENSITY), 'Todos os municípios');
});

test('caixa da abrangência territorial: Brasil, estados, grupos e municípios na ordem dos níveis', () => {
  assert.equal(describe({...EMPTY_SCOPE, estados: ['13']}, []), 'Amazonas (estado)');
  assert.equal(describe({...EMPTY_SCOPE, estados: ['15', '13']}, []), 'Amazonas e Pará (estados)');
  assert.equal(describe({...EMPTY_SCOPE, estados: ['13', '15', '35']}, []), '3 estados');
  assert.equal(describe({...EMPTY_SCOPE, grupos: ['13']}, []), 'Municípios do Amazonas (62)');
  assert.equal(describe({...EMPTY_SCOPE, brasil: true, estados: ['13']}, ['code:130260']),
    'Brasil (total nacional), Amazonas (estado) e MANAUS (AM)');
  assert.equal(describe({...EMPTY_SCOPE, brasil: true}, ['code:130260', 'code:130420']), 'Brasil (total nacional) e 2 municípios');
  assert.equal(describe({...EMPTY_SCOPE, brasil: true, todos: true}, []), 'Brasil (total nacional) e Todos os municípios');
});

test('o que vale em cada análise: só os níveis aceitos; sem nada aplicável, o padrão da análise', () => {
  const marked = {...EMPTY_SCOPE, brasil: true, estados: ['13'], grupos: ['15']};
  assert.deepEqual(effectiveScope(marked, ['code:350010'], DENSITY), {padrao: false, abrangencia: {brasil: true, estados: ['13'],
    municipios: {todos: false, estados: ['15'], ids: ['code:350010']}}});
  // Distribuição não aceita o Brasil: ele continua guardado, mas não vai no pedido.
  assert.deepEqual(effectiveScope(marked, [], DISTRIBUTION).abrangencia, {brasil: false, estados: ['13'],
    municipios: {todos: false, estados: ['15'], ids: []}});
  // Só o Brasil marcado numa análise que não o aceita: vale o padrão (todos os municípios).
  assert.deepEqual(effectiveScope({...EMPTY_SCOPE, brasil: true}, [], DISTRIBUTION), {padrao: true, abrangencia: {brasil: false,
    estados: [], municipios: {todos: true, estados: [], ids: []}}});
  // Análise espacial: estados como objeto não valem; o grupo de municípios do estado vale.
  assert.deepEqual(effectiveScope(marked, ['code:130260'], SPATIAL).abrangencia, {brasil: false, estados: [],
    municipios: {todos: false, estados: ['15'], ids: ['code:130260']}});
  // Agregação: o estado segue como estado; o backend o expande nos municípios (estado_como "expansao").
  assert.deepEqual(effectiveScope({...EMPTY_SCOPE, estados: ['13']}, [], AGGREGATE).abrangencia.estados, ['13']);
  // Quantitativos sem nada marcado: o Brasil; com municípios marcados, só eles.
  assert.deepEqual(effectiveScope(EMPTY_SCOPE, [], COUNTS), {padrao: true, abrangencia: {brasil: true, estados: [],
    municipios: {todos: false, estados: [], ids: []}}});
  assert.equal(effectiveScope(EMPTY_SCOPE, ['code:130260'], COUNTS).abrangencia.brasil, false);
  // Rotatividade não tem níveis na base Brasil: nenhuma abrangência é enviada.
  assert.equal(effectiveScope(marked, ['code:130260'], ROTATION), null);
  assert.equal(effectiveScope(marked, [], undefined), null);
});

test('marcar e desmarcar: a primeira marcação substitui o padrão; "Todos" e grupos absorvem os municípios', () => {
  let state = {scope: EMPTY_SCOPE, ids: []};
  assert.equal(effectiveScope(state.scope, state.ids, COUNTS).padrao, true);
  state = toggle(state.scope, state.ids, {kind: 'municipio', id: 'code:130260'});
  assert.deepEqual(state, {scope: EMPTY_SCOPE, ids: ['code:130260']});
  assert.equal(effectiveScope(state.scope, state.ids, COUNTS).padrao, false);  // o Brasil (padrão) não foi copiado
  state = toggle(state.scope, state.ids, {kind: 'municipio', id: 'code:130260'});
  assert.equal(effectiveScope(state.scope, state.ids, COUNTS).padrao, true);   // tudo desmarcado: volta o padrão
  state = toggle(state.scope, ['code:130260', 'code:350010'], {kind: 'todos'});
  assert.deepEqual(state, {scope: {...EMPTY_SCOPE, todos: true}, ids: []});
  assert.deepEqual(toggle(state.scope, state.ids, {kind: 'municipio', id: 'code:130260'}), state);  // incluído em "Todos"
  const members = ['code:130260', 'code:130340', 'code:130420'];
  state = toggle(EMPTY_SCOPE, ['code:130260', 'code:350010'], {kind: 'grupo', prefix: '13', members});
  assert.deepEqual(state, {scope: {...EMPTY_SCOPE, grupos: ['13']}, ids: ['code:350010']});
  assert.equal(groupState('13', state.scope, state.ids, members), 'checked');
  // Desmarcar um município de um grupo marcado: o grupo sai e os demais municípios continuam marcados.
  state = toggle(state.scope, state.ids, {kind: 'municipio', id: 'code:130340', members});
  assert.deepEqual(state, {scope: EMPTY_SCOPE, ids: ['code:350010', 'code:130260', 'code:130420']});
  assert.equal(groupState('13', state.scope, state.ids, members), 'mixed');
  assert.equal(groupState('13', EMPTY_SCOPE, members, members), 'checked');
  // Grupo cheio pelos municípios marcados: a caixa do grupo desmarca todos eles.
  assert.deepEqual(toggle(EMPTY_SCOPE, [...members, 'code:350010'], {kind: 'grupo', prefix: '13', members}),
    {scope: EMPTY_SCOPE, ids: ['code:350010']});
  assert.deepEqual(toggle(EMPTY_SCOPE, [], {kind: 'todos_estados', prefixes: ['13', '15']}).scope.estados, ['13', '15']);
  assert.deepEqual(toggle({...EMPTY_SCOPE, estados: ['13', '15']}, [], {kind: 'todos_estados', prefixes: ['13', '15']}).scope.estados, []);
  assert.deepEqual(toggle({...EMPTY_SCOPE, estados: ['15']}, [], {kind: 'estado', prefix: '13'}).scope.estados, ['13', '15']);
  assert.equal(toggle(EMPTY_SCOPE, [], {kind: 'brasil'}).scope.brasil, true);
});

test('contagem e composição da seleção que vale na análise', () => {
  const effective = effectiveScope({...EMPTY_SCOPE, brasil: true, estados: ['13', '15'], grupos: ['35']},
    ['code:130260', 'code:350010'], DENSITY);
  // Brasil + 2 estados + 645 municípios de SP + MANAUS (FORA já está no grupo de SP).
  assert.equal(countSelected(effective, LEVELS), 1 + 2 + 645 + 1);
  assert.equal(breakdown(effective, LEVELS), 'Brasil · 2 estados · 646 municípios');
  assert.equal(countSelected(effectiveScope({...EMPTY_SCOPE, todos: true}, [], DENSITY), LEVELS), 5570);
  assert.equal(breakdown(effectiveScope({...EMPTY_SCOPE, todos: true}, [], DENSITY), LEVELS), '5.570 municípios');
  assert.equal(countSelected(effectiveScope(EMPTY_SCOPE, [], DENSITY), LEVELS), 0);  // padrão: nada marcado
  assert.equal(countSelected(effectiveScope(EMPTY_SCOPE, ['code:130260', 'code:130420', 'code:130340'], DENSITY), LEVELS), 3);
});

test('transferência de um resultado com níveis e competências oferecidas', () => {
  assert.deepEqual(fromMembers(['br', 'uf:35', 'uf:13', 'code:130260']), {scope: {...EMPTY_SCOPE, brasil: true, estados: ['13', '35']},
    ids: ['code:130260']});
  assert.deepEqual(fromMembers(['code:130260', 'code:130420']), {scope: EMPTY_SCOPE, ids: ['code:130260', 'code:130420']});
  const national = ['202306', '202406'], municipal = ['202406'];
  assert.deepEqual(periodsForScope(effectiveScope(EMPTY_SCOPE, [], COUNTS), national, municipal), national);
  assert.deepEqual(periodsForScope(effectiveScope({...EMPTY_SCOPE, brasil: true}, ['code:002'], COUNTS), national, ['202401', '202406']),
    ['202306', '202401', '202406']);
  assert.deepEqual(periodsForScope(effectiveScope(EMPTY_SCOPE, [], DENSITY), national, municipal), municipal);
  assert.deepEqual(periodsForScope(null, national, municipal), municipal);
});
