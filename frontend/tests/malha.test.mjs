import {createHash} from 'node:crypto';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// A malha das divisas no mapa do Detector de Sinais (comando V23, etapa 7): o modelo puro (malhaModel.ts) — a leitura do TopoJSON
// do IBGE (as áreas dos municípios, as divisas dos estados e o retângulo de cada estado), as divisas a desenhar (as áreas com a
// cor do nível, as divisas dos estados sempre e as dos municípios ao aproximar um estado ou com um estado só) e o pedido único do
// arquivo —, o arquivo versionado (`frontend/public/malha/`, com a fonte, a data e o SHA-256) e a tela.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const M = await source('malhaModel');
const ler = caminho => readFileSync(new URL('../src/' + caminho, import.meta.url), 'utf8');

// Uma malha pequena, feita à mão: quatro quadrados numa grade de 2 × 2. A (110001) e B (110002) são do estado 11; C (120001) e D
// (120005), do estado 12. Os arcos 0 (entre A e B) e 1 (entre C e D) ficam dentro de um estado; os arcos 2 (A e C) e 3 (B e D)
// separam os dois estados; os arcos 4 a 7 são a borda de fora. As posições vêm como diferenças acumuladas, com a transformação.
const TOPO = {type: 'Topology', transform: {scale: [0.5, 0.5], translate: [-50, -10]},
  arcs: [[[1, 0], [0, 1]], [[1, 1], [0, 1]], [[0, 1], [1, 0]], [[1, 1], [1, 0]], [[1, 0], [-1, 0], [0, 1]], [[1, 0], [1, 0], [0, 1]],
    [[0, 1], [0, 1], [1, 0]], [[2, 1], [0, 1], [-1, 0]]],
  objects: {BRMU: {type: 'GeometryCollection', geometries: [
    {type: 'Polygon', arcs: [[4, 2, -1]], properties: {codarea: '1100015'}},
    {type: 'Polygon', arcs: [[5, -4, -1]], properties: {codarea: '1100023'}},
    {type: 'MultiPolygon', arcs: [[[6, -2, -3]]], properties: {codarea: '1200013'}},
    {type: 'Polygon', arcs: [[7, -2, 3]], properties: {codarea: '1200054'}},
    {type: 'Point', arcs: [], properties: {codarea: '1299999'}}, {type: 'Polygon', arcs: [[4, 2, -1]], properties: {}}]}}};

test('a malha lida do TopoJSON: as áreas pelo código da base, as divisas dos estados e o retângulo de cada estado', () => {
  const malha = M.decodificarMalha(TOPO);
  assert.deepEqual([...malha.areas.keys()], ['110001', '110002', '120001', '120005'], 'os 6 primeiros dígitos do codarea; o que não é área fica de fora');
  // O anel de A: (1,0) → (0,0) → (0,1) → (1,1) → (1,0) na grade, com a escala de 0,5 e a origem em (−50, −10).
  assert.deepEqual(malha.areas.get('110001'), {codigo: '110001', uf: '11', caixa: [-50, -10, -49.5, -9.5],
    aneis: [[[-49.5, -10], [-50, -10], [-50, -9.5], [-49.5, -9.5], [-49.5, -10]]]});
  assert.deepEqual(malha.areas.get('120001').aneis, [[[-50, -9.5], [-50, -9], [-49.5, -9], [-49.5, -9.5], [-50, -9.5]]], 'o MultiPolygon, anel a anel');
  assert.deepEqual([...malha.ufs.entries()], [['11', [-50, -10, -49, -9.5]], ['12', [-50, -9.5, -49, -9]]]);
  // As divisas dos estados: os arcos entre municípios de estados diferentes (2 e 3) e os de um município só (a borda: 4 a 7). Os
  // arcos 0 e 1, entre municípios do mesmo estado, não são divisa de estado.
  assert.equal(malha.divisasDosEstados.length, 6);
  assert.deepEqual(malha.divisasDosEstados.slice(0, 2), [[[-50, -9.5], [-49.5, -9.5]], [[-49.5, -9.5], [-49, -9.5]]]);
  // O que não é uma topologia com áreas não vira malha.
  for (const ruim of [null, undefined, 7, {}, {type: 'Topology'}, {type: 'Topology', arcs: [], objects: {x: {geometries: []}}},
    {type: 'FeatureCollection', arcs: [], objects: {}}]) assert.equal(M.decodificarMalha(ruim), null);
});

test('as divisas a desenhar: as áreas com a cor do nível, as divisas dos estados sempre e as dos municípios ao aproximar ou com um estado só', () => {
  const malha = M.decodificarMalha(TOPO);
  const A = {id: 'code:110001', codigo: '110001', cor: '#b00020', chave: 'critico'}, C = {id: 'code:120001', codigo: '120001'};
  const semArea = {id: 'code:999999', codigo: '999999', cor: '#b00020', chave: 'critico'};
  // Dois estados à vista, sem aproximar: só a área com nível é desenhada (com a cor dele); as divisas dos municípios não aparecem;
  // a moldura é o retângulo das áreas à vista; quem não tem área na malha fica de fora do desenho das áreas.
  const geral = M.divisasDoMapa(malha, [A, C, semArea]);
  assert.deepEqual([geral.ufs, geral.comBordas, geral.moldura], [['11', '12'], false, [-50, -10, -49.5, -9]]);
  assert.deepEqual(geral.areas, [{id: 'code:110001', aneis: malha.areas.get('110001').aneis, cor: '#b00020', chave: 'critico'}]);
  assert.equal(geral.linhas.length, 6, 'todas as divisas dos estados: o desenho deixa de fora o que não cabe nele');
  // Aproximado no estado 12: a moldura é o estado inteiro, as divisas dos municípios dele aparecem (as áreas sem cor: C, que
  // está à vista sem nível, e D, que nem está à vista), e a área colorida do outro estado continua com a cor.
  const perto = M.divisasDoMapa(malha, [A, C, semArea], '12');
  assert.deepEqual([perto.comBordas, perto.moldura], [true, [-50, -9.5, -49, -9]]);
  assert.deepEqual(perto.areas.map(area => [area.id, area.cor ?? null]), [['code:110001', '#b00020'], ['code:120001', null], ['malha:120005', null]]);
  // Um estado só à vista: as divisas dos municípios aparecem sem aproximar.
  const so = M.divisasDoMapa(malha, [C]);
  assert.deepEqual([so.ufs, so.comBordas, so.moldura, so.areas.map(area => area.id)], [['12'], true, [-50, -9.5, -49.5, -9], ['code:120001', 'malha:120005']]);
  // Um estado que a malha não tem não aproxima nada; sem ninguém à vista, não há moldura.
  assert.deepEqual([M.divisasDoMapa(malha, [A, C], '99').comBordas, M.divisasDoMapa(malha, []).moldura, M.divisasDoMapa(malha, []).areas], [false, null, []]);
  // O caminho do desenho, com a projeção de quem chama; as áreas fecham o anel.
  const vezesDez = ([x, y]) => [x * 10, y * 10];
  assert.equal(M.caminhoDaMalha([[[0, 0], [1, 0], [1, 1]], [[5, 5]], [[2, 2], [3, 2]]], vezesDez), 'M0.0,0.0L10.0,0.0L10.0,10.0M20.0,20.0L30.0,20.0');
  assert.equal(M.caminhoDaMalha([[[0, 0], [1, 0], [1, 1]]], vezesDez, true), 'M0.0,0.0L10.0,0.0L10.0,10.0Z');
});

test('a malha é pedida uma vez só; se o arquivo não puder ser lido, a tela segue sem as divisas e a próxima abertura tenta de novo', async () => {
  const pedidos = [];
  const falha = endereco => { pedidos.push(endereco); return Promise.reject(new Error('sem rede')); };
  const certo = endereco => { pedidos.push(endereco); return Promise.resolve(TOPO); };
  assert.equal(await M.carregarMalha('/base', falha), null);
  const lida = await M.carregarMalha('/base/', certo);
  assert.equal(lida.areas.size, 4);
  assert.equal(await M.carregarMalha('/', falha), lida, 'depois de lida, a malha não é pedida de novo');
  assert.deepEqual(pedidos, ['/base/' + M.ARQUIVO_DA_MALHA, '/base/' + M.ARQUIVO_DA_MALHA]);
  assert.equal(M.ARQUIVO_DA_MALHA, 'malha/municipios-ibge-qualidade-minima.json');
});

test('o arquivo versionado da malha: a fonte, a data e o SHA-256 conferem, e ela tem os 5.570 municípios em 27 estados', () => {
  const pasta = new URL('../public/malha/', import.meta.url);
  const fonte = JSON.parse(readFileSync(new URL('fonte.json', pasta), 'utf8'));
  const bytes = readFileSync(new URL(fonte.arquivo, pasta));
  assert.equal(fonte.arquivo, 'municipios-ibge-qualidade-minima.json');
  assert.deepEqual([bytes.length, createHash('sha256').update(bytes).digest('hex')], [fonte.bytes, fonte.sha256], 'o arquivo é o que a fonte registra, byte a byte');
  assert.deepEqual([fonte.bytes, fonte.sha256, fonte.consultado_em, fonte.geometrias], [1428796, 'b509836495fa76a9adf620a2a5c57b462b745bbb0613e9d98cc1123d494edc21',
    '2026-11-15', 5570]);
  assert.equal(fonte.fonte, 'https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/json&qualidade=minima&intrarregiao=municipio');
  const malha = M.decodificarMalha(JSON.parse(bytes.toString('utf8')));
  assert.deepEqual([malha.areas.size, malha.ufs.size, malha.divisasDosEstados.length], [5570, 27, 1669]);
  assert.ok([...malha.areas.values()].every(area => /^\d{6}$/.test(area.codigo) && area.uf === area.codigo.slice(0, 2) && area.aneis.length >= 1 &&
    area.aneis.every(anel => anel.length >= 4 && anel.every(([lon, lat]) => lon > -75 && lon < -28 && lat > -34.5 && lat < 6))), 'toda área fica no Brasil');
  // O mapa aproximado em Santa Catarina, com um município de Roraima à vista em crítico: a moldura é Santa Catarina, e nada é
  // cortado por ela — o desenho mostra um pouco além da moldura (ela não tem a proporção do mapa), e um ponto que aparece ao
  // lado do estado tem a área dele. Vão ao desenho as duas áreas com nível, as 294 outras de Santa Catarina (sem cor; Florianópolis,
  // que está à vista sem nível, pelo identificador da tela) e todas as divisas dos estados.
  const boaVista = {id: 'code:140010', codigo: '140010', cor: '#b00020', chave: 'critico'}, lages = {id: 'code:420930', codigo: '420930', cor: '#e07a1f', chave: 'elevado'};
  const perto = M.divisasDoMapa(malha, [boaVista, {id: 'code:420540', codigo: '420540'}, lages], '42');
  assert.deepEqual([perto.comBordas, perto.ufs, perto.moldura.map(n => +n.toFixed(2))], [true, ['14', '42'], [-53.84, -29.35, -48.37, -25.98]]);
  assert.deepEqual([perto.areas.filter(area => area.cor).map(area => area.id), perto.areas.filter(area => !area.cor).length, perto.linhas.length],
    [['code:140010', 'code:420930'], 294, 1669]);
  assert.ok(perto.areas.some(area => area.id === 'code:420540' && !area.cor));
  assert.equal(perto.areas.filter(area => area.id.startsWith('malha:')).length, 293);
  // Sem aproximar, com dois estados à vista: só as áreas com nível, todas as divisas dos estados, e a moldura das áreas à vista.
  const geral = M.divisasDoMapa(malha, [boaVista, {id: 'code:420540', codigo: '420540'}, lages]);
  assert.deepEqual([geral.areas.length, geral.linhas.length, geral.comBordas, geral.moldura.map(n => +n.toFixed(2))], [2, 1669, false, [-61, -28.43, -48.37, 3.58]]);
});

test('na tela: a malha só é pedida quando o mapa do Detector abre, só na base do Brasil; a planilha segue sem divisas e diz isso', () => {
  const graficos = ler('DetectorGraficos.tsx'), mapa = ler('MapaDosConjuntos.tsx'), detector = ler('DetectorDeSinais.tsx');
  // Só o mapa do Detector pede a malha, dentro do efeito de montagem dele; e ele só é montado na vista "Mapa".
  const src = new URL('../src/', import.meta.url);
  for (const arquivo of ['DetectorDeSinais.tsx', 'SimuladorDeCenarios.tsx', 'AreaDeAnalise.tsx', 'MapaDosConjuntos.tsx', 'App.tsx'])
    assert.ok(!readFileSync(new URL(arquivo, src), 'utf8').includes('carregarMalha'), arquivo);
  assert.match(graficos, /useEffect\(\(\) => \{\s+if \(!doBrasil\) \{ setMalha\(null\); return; \}\s+let vivo = true;\s+setMalha\(undefined\);\s+carregarMalha\(import\.meta\.env\.BASE_URL \|\| "\/"\)\.then\(lida => \{ if \(vivo\) setMalha\(lida\); \}\);/);
  assert.ok(detector.includes('{vistaEmUso === "mapa" && <MapaDosNiveis resposta={resposta} linhas={filtradas} sinal={filtros.sinal} onAbrir={abrirDoDesenho}/>}'));
  assert.ok(graficos.includes('const estadoDasDivisas = !doBrasil ? "sem" : malha === undefined ? "carregando" : malha ? "carregadas" : "indisponiveis";'));
  assert.ok(graficos.includes('data-divisas={estadoDasDivisas} data-aproximado={emFoco} data-largura={largura}'));
  // "Aproximar o mapa em": um dos estados dos territórios à vista; o desenho é feito na largura da tela (mais alto no celular).
  assert.match(graficos, /\{malha && estados\.length > 1 && <label[^>]*>Aproximar o mapa em\s+<select data-testid="detector-mapa-aproximar" className="analise-campo" value=\{emFoco\} onChange=\{event => setAproximado\(event\.target\.value\)\}>\s+<option value="">todos os territórios à vista<\/option>/);
  assert.ok(graficos.includes('const [refDoMapa, medida] = useLargura(760);') && graficos.includes('const { largura, altura } = tamanhoDoGrafico(medida, 760, 440, 380);'));
  assert.ok(graficos.includes('nomeDe={id => nomes.get(id) ?? id} largura={largura} altura={altura} divisas={divisas}'));
  // A legenda diz o que as divisas são; numa planilha, que a base não as tem.
  for (const trecho of ['"As divisas são as da malha municipal do IBGE: as dos estados ficam sempre à vista; as dos municípios aparecem quando o mapa é aproximado "',
    '"As divisas estão sendo carregadas."', '"As divisas não puderam ser carregadas: o mapa mostra só os pontos, e a sigla situa os pontos de cada "',
    ': "A base não tem as divisas" + (comGrupo ? ": o nome situa os pontos de cada " + r.grupo : "") + "."}</span>']) assert.ok(graficos.includes(trecho), trecho);
  // No desenho: as áreas com cor uma a uma, as sem cor num caminho só e as divisas dos estados, por baixo dos pontos.
  for (const id of ['analise-mapa-divisas', 'analise-mapa-areas-sem-cor', 'analise-mapa-area', 'analise-mapa-divisas-dos-estados'])
    assert.equal(mapa.split('data-testid="' + id + '"').length - 1, 1, id);
  assert.ok(mapa.indexOf('data-testid="analise-mapa-divisas"') < mapa.indexOf('data-testid="analise-mapa-ponto"'), 'as divisas ficam por baixo dos pontos');
  assert.ok(mapa.includes('const [minLat, maxLat, minLon, maxLon] = moldura ? [moldura[1], moldura[3], moldura[0], moldura[2]]'));
});
