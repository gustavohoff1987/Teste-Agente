import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';

// Modo escuro (23/10/2026): a página segue o esquema de cor do aparelho, sem botão, e a impressão é sempre clara. Confere a loja
// do esquema (esquemaDeCor.ts, com uma janela de mentira), as paletas do gráfico e do mapa por esquema (painelModel.ts e
// mapaModel.ts) e o contraste das cores do escuro com as contas do validador da skill de visualização (WCAG e luminosidade
// OKLCH), as variáveis de styles.css (o claro em :root, o escuro só na tela) contra as paletas em JavaScript e contra as classes
// do Tailwind, e que nenhuma cor fixa ficou fora das variáveis nas folhas de estilo.
async function source(name) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(code).toString('base64'));
}
const E = await source('esquemaDeCor');
const M = await source('painelModel');
const MP = await source('mapaModel');
const ler = arquivo => readFileSync(new URL('../' + arquivo, import.meta.url), 'utf8');
const semComentarios = texto => texto.replace(/\/\*[\s\S]*?\*\//g, '');
const TAILWIND = (await import(new URL('../tailwind.config.js', import.meta.url).href)).default;

// ------------------------------------------------------------------------------------------------ contas de cor
const HEX = /^#[0-9a-f]{6}$/;
const canais = hex => { const v = parseInt(hex.slice(1), 16); return [(v >> 16) & 255, (v >> 8) & 255, v & 255]; };
const linear = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const luminancia = hex => { const [r, g, b] = canais(hex).map(linear); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
/** Contraste WCAG 2 (o mesmo contrast() do validador da skill). */
const contraste = (a, b) => { const [x, y] = [luminancia(a), luminancia(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
function oklab(hex) {
  const [r, g, b] = canais(hex).map(linear);
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s, 1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}
const L = hex => oklab(hex)[0];
const matiz = hex => { const [, a, b] = oklab(hex); return ((Math.atan2(b, a) * 180 / Math.PI) % 360 + 360) % 360; };
/** As regras --ordinal do validador: L monótono no sentido pedido, passos ≥ 0,06, a ponta junto da superfície a 2:1 ou mais e
 * um só matiz (até 40°). `sobe`: do escuro ao claro (rampa do modo escuro); sem ele, do claro ao escuro (modo claro). Nos dois
 * casos, o primeiro passo é o mais perto da superfície. */
function rampaOrdinal(rampa, superficie, sobe, rotulo) {
  const ls = rampa.map(L);
  ls.slice(1).forEach((l, i) => {
    assert.ok(sobe ? l > ls[i] : l < ls[i], rotulo + ': luminosidade monótona');
    assert.ok(Math.abs(l - ls[i]) >= 0.06, rotulo + ': passos visíveis (ΔL ≥ 0,06)');
  });
  assert.ok(contraste(rampa[0], superficie) >= 2, rotulo + ': a ponta junto da superfície fica a 2:1 ou mais (' + rampa[0] + ')');
  const matizes = rampa.map(matiz);
  let abertura = Math.max(...matizes) - Math.min(...matizes);
  if (abertura > 180) abertura = 360 - abertura;
  assert.ok(abertura <= 40, rotulo + ': um só matiz');
}

// ------------------------------------------------------------------------------------------------ variáveis de styles.css
const CSS = semComentarios(ler('src/styles.css'));
const SELETOR_ESCURO = '@media screen and (prefers-color-scheme: dark)';
const inicioClaro = CSS.indexOf(':root {'), inicioEscuro = CSS.indexOf(SELETOR_ESCURO);
const fimEscuro = CSS.indexOf('}', CSS.indexOf(':root {', inicioEscuro)) + 1;
const declaracoes = bloco => Object.fromEntries([...bloco.matchAll(/(--[\w-]+)\s*:\s*([^;]+);/g)].map(m => [m[1], m[2].trim()]));
const CLARO = declaracoes(CSS.slice(inicioClaro, inicioEscuro));
const ESCURO = declaracoes(CSS.slice(inicioEscuro, fimEscuro));
const curto = hex => hex.length === 4 ? '#' + [...hex.slice(1)].map(c => c + c).join('') : hex;
/** O valor de uma variável como #rrggbb no esquema: hex direto, ou rgb(var(--tom-x)) com os canais do tom. */
function hexDe(nome, esquema) {
  const valor = (esquema === 'escuro' && nome in ESCURO ? ESCURO : CLARO)[nome];
  assert.ok(valor, 'variável ' + nome + ' definida');
  const tom = /^rgb\(var\((--tom-[\w-]+)\)\)$/.exec(valor);
  if (tom) return hexDosCanais(tom[1], esquema);
  assert.match(curto(valor.toLowerCase()), HEX, nome);
  return curto(valor.toLowerCase());
}
function hexDosCanais(nome, esquema) {
  const valor = (esquema === 'escuro' ? ESCURO : CLARO)[nome];
  assert.ok(valor, 'tom ' + nome + ' definido no ' + esquema);
  return '#' + valor.split(/\s+/).map(Number).map(c => c.toString(16).padStart(2, '0')).join('');
}

test('loja do esquema: o escuro só na tela e fora da impressão; avisa a troca do aparelho e a impressão, que passa pelo síncrono', () => {
  assert.equal(E.CONSULTA_ESCURO, 'screen and (prefers-color-scheme: dark)', 'a mesma condição do bloco escuro de styles.css');
  assert.equal(E.esquemaDe(true, false), 'escuro');
  assert.equal(E.esquemaDe(true, true), 'claro', 'na impressão, sempre claro');
  assert.equal(E.esquemaDe(false, false), 'claro');
  const midia = {matches: true, ouvintes: new Set(), addEventListener(tipo, f) { assert.equal(tipo, 'change'); this.ouvintes.add(f); },
    removeEventListener(tipo, f) { this.ouvintes.delete(f); }};
  const ouvintes = {beforeprint: new Set(), afterprint: new Set()};
  const consultas = [];
  const janela = {matchMedia(consulta) { consultas.push(consulta); return midia; },
    addEventListener(tipo, f) { ouvintes[tipo].add(f); }, removeEventListener(tipo, f) { ouvintes[tipo].delete(f); }};
  let sincronos = 0;
  const loja = E.criarLojaDoEsquema(janela, acao => { sincronos += 1; acao(); });
  assert.equal(loja.atual(), 'escuro');
  assert.deepEqual([...new Set(consultas)], [E.CONSULTA_ESCURO]);
  const vistos = [];
  const sair = loja.assinar(() => vistos.push(loja.atual()));
  const outro = loja.assinar(() => {});
  assert.equal(midia.ouvintes.size, 1, 'um ouvinte só para todos os que assinam');
  midia.matches = false; midia.ouvintes.forEach(f => f());
  midia.matches = true; midia.ouvintes.forEach(f => f());
  assert.deepEqual(vistos, ['claro', 'escuro']);
  ouvintes.beforeprint.forEach(f => f());
  assert.equal(loja.atual(), 'claro', 'durante a impressão, claro');
  assert.equal(sincronos, 1, 'o começo da impressão avisa pelo síncrono (flushSync no React)');
  ouvintes.afterprint.forEach(f => f());
  assert.deepEqual(vistos, ['claro', 'escuro', 'claro', 'escuro']);
  sair();
  assert.equal(ouvintes.beforeprint.size, 1, 'enquanto houver quem assine, os ouvintes ficam');
  outro();
  assert.equal(ouvintes.beforeprint.size + ouvintes.afterprint.size + midia.ouvintes.size, 0, 'sem assinantes, sem ouvintes');
  const semJanela = E.criarLojaDoEsquema(null);
  assert.equal(semJanela.atual(), 'claro');
  assert.doesNotThrow(() => semJanela.assinar(() => {})());
});

test('paleta do gráfico por esquema: o claro continua o de antes; o escuro tem as mesmas chaves, passos validados e contraste', () => {
  const claro = M.paletaDoGrafico('claro'), escuro = M.paletaDoGrafico('escuro');
  assert.equal(claro, M.PALETA_CLARA);
  assert.equal(escuro, M.PALETA_ESCURA);
  assert.equal(claro.bolha, M.COR_BOLHA);
  assert.equal(claro.neutra, M.COR_NEUTRA);
  assert.equal(claro.zero, M.COR_NEUTRA, 'no claro, o zero da variação é o neutro, como antes');
  assert.equal(claro.naoAvaliavel, M.COR_NAO_AVALIAVEL);
  assert.equal(claro.tendencia, M.CORES_TENDENCIA);
  assert.equal(claro.ordinais, M.RAMPAS_ORDINAIS);
  assert.equal(claro.aumento, M.RAMPA_AUMENTO);
  assert.equal(claro.reducao, M.RAMPA_REDUCAO);
  assert.deepEqual(Object.keys(escuro).sort(), Object.keys(claro).sort());
  assert.deepEqual(Object.keys(escuro.ordinais), Object.keys(claro.ordinais));
  const planas = paleta => [paleta.superficie, paleta.tinta, paleta.tinta2, paleta.muda, paleta.grade, paleta.eixo, paleta.bolha, paleta.neutra,
    paleta.zero, paleta.naoAvaliavel, paleta.vazia, paleta.dica, ...Object.values(paleta.tendencia), ...Object.values(paleta.ordinais).flat(),
    ...paleta.aumento, ...paleta.reducao];
  for (const cor of [...planas(claro), ...planas(escuro)]) assert.match(cor, HEX);
  // Os valores validados das notas do modo escuro (validate_palette.js --mode dark --surface "#1a1a19").
  assert.equal(escuro.superficie, '#1a1a19');
  assert.equal(escuro.bolha, '#1ba3b5');
  assert.deepEqual(escuro.tendencia, {CRESCIMENTO: '#3987e5', DECLINIO: '#d95926', NENHUMA: '#199e70'});
  // AJ-12 (18/11/2026; muda de propósito): as de 4 e de 5 tons começam no #1c5cab, um passo mais longe da superfície.
  assert.deepEqual(escuro.ordinais[5], ['#1c5cab', '#2a78d6', '#5598e7', '#86b6ef', '#b7d3f6']);
  assert.deepEqual(escuro.ordinais[4], ['#1c5cab', '#2a78d6', '#5598e7', '#9ec5f4']);
  assert.deepEqual(escuro.ordinais[3], ['#1c5cab', '#3987e5', '#9ec5f4']);
  assert.deepEqual(escuro.ordinais[2], ['#1c5cab', '#86b6ef']);
  // Marcas: as categóricas a 3:1 ou mais da superfície escura; as tintas de texto a 4,5:1 ou mais.
  for (const cor of [escuro.bolha, ...Object.values(escuro.tendencia)]) assert.ok(contraste(cor, escuro.superficie) >= 3, cor);
  for (const cor of [escuro.tinta, escuro.tinta2, escuro.muda]) assert.ok(contraste(cor, escuro.superficie) >= 4.5, cor);
  for (const paleta of [claro, escuro]) assert.ok(contraste(paleta.naoAvaliavel, paleta.superficie) >= 3, 'anel do não avaliável visível');
  assert.equal(escuro.vazia, escuro.superficie, 'a bolha vazada mostra a superfície, nunca um preenchimento');
  // Grupos e faixas: no claro, do claro (menor) ao escuro (maior); no escuro, a âncora vira: do escuro ao claro.
  for (const total of [2, 3, 4, 5]) {
    rampaOrdinal(claro.ordinais[total], claro.superficie, false, 'claro ' + total);
    rampaOrdinal(escuro.ordinais[total], escuro.superficie, true, 'escuro ' + total);
  }
  // Divergente: cada braço, do perto de zero ao limite, clareia no escuro; o zero fica mais escuro que os dois começos.
  rampaOrdinal(escuro.aumento, escuro.superficie, true, 'aumento');
  rampaOrdinal(escuro.reducao, escuro.superficie, true, 'redução');
  for (const comeco of [escuro.aumento[0], escuro.reducao[0]]) assert.ok(L(comeco) - L(escuro.zero) >= 0.06, 'zero abaixo de ' + comeco);
  assert.ok(contraste(escuro.zero, escuro.superficie) >= 1.6, 'o zero aparece, recessivo como no claro');
  assert.ok(contraste(escuro.neutra, escuro.superficie) > contraste(escuro.zero, escuro.superficie), 'o neutro aparece mais que o zero');
});

test('pintura no escuro: cada camada usa a paleta do esquema; sem paleta, o claro de antes', () => {
  const P = M.PALETA_ESCURA;
  const item = (extra = {}) => ({id: 'code:1', tipo: 'municipio', rotulo: 'X (AM)', uf: 'AM', populacao: 10, quantidade: 1, densidade: 1,
    distancia_km: null, inicial: {populacao: 10, quantidade: 1, densidade: 1}, variacao_percentual: {populacao: 0, quantidade: 0, densidade: 0},
    avaliavel: {densidade: true, distancia: null, variacao: true}, motivos: [], referencia: false, ...extra});
  const p = (camada, extra = {}) => ({camada, indicador: 'densidade', limiteVariacao: 40, totalGrupos: 5, totalFaixas: 3, primeiros: 2, paleta: P, ...extra});
  assert.deepEqual(M.pintar(item(), p('unica')), {cor: '#1ba3b5', vazada: false, apagada: false});
  assert.equal(M.pintar(item(), {...p('unica'), paleta: undefined}).cor, M.COR_BOLHA, 'sem paleta, o claro');
  assert.equal(M.pintar(item({grupo: {indice: 1, rotulo: '1º quintil'}}), p('grupos')).cor, '#1c5cab');
  assert.equal(M.pintar(item({grupo: {indice: 5, rotulo: '5º quintil'}}), p('grupos')).cor, '#b7d3f6');
  assert.equal(M.pintar(item({grupo: {indice: 7, rotulo: '7º decil'}}), p('grupos', {totalGrupos: 10})).cor, P.bolha, 'decis: só as linhas de corte');
  assert.equal(M.pintar(item({faixa: 'fora'}), p('faixas')).cor, P.neutra);
  assert.deepEqual(M.pintar(item({condicoes: {situacao: 'ATENDE', porCondicao: [], motivo: null}}), p('condicoes')), {cor: P.bolha, vazada: false, apagada: false});
  assert.deepEqual(M.pintar(item({condicoes: {situacao: 'NAO_ATENDE', porCondicao: [], motivo: null}}), p('condicoes')), {cor: P.neutra, vazada: false, apagada: true});
  assert.deepEqual(M.pintar(item({condicoes: {situacao: 'NAO_AVALIAVEL', porCondicao: [], motivo: 'x'}}), p('condicoes')), {cor: P.vazia, vazada: true, apagada: false});
  assert.deepEqual(M.pintar(item({ordem: {posicao: 3}}), p('ordem')), {cor: P.neutra, vazada: false, apagada: true});
  assert.equal(M.pintar(item({tendencia: {avaliavel: true, familia: 'DECLINIO', classe: 'DECLINIO'}}), p('classes')).cor, '#d95926');
  assert.equal(M.pintar(item({variacao_percentual: {populacao: 0, quantidade: 10, densidade: 10}}), p('variacao')).cor, '#3987e5');
  assert.equal(M.corDaVariacao(0, 40, P), P.zero);
  assert.equal(M.corDaVariacao(10, 40, P), P.aumento[1]);
  assert.equal(M.corDaVariacao(-10, 40, P), P.reducao[1]);
  assert.equal(M.corDaVariacao(40, 40, P), '#9ec5f4', 'no escuro, o maior aumento é o mais claro');
  assert.equal(M.corDaVariacao(-80, 40, P), '#f2ad8c');
  assert.equal(M.corOrdinal(1, 5, P), '#1c5cab');
  assert.equal(M.corOrdinal(5, 5, P), '#b7d3f6');
  assert.equal(M.corOrdinal(1, 10, P), null);
  // A legenda da variação: no claro, a mesma de antes; no escuro, com o zero escuro no meio.
  assert.equal(M.gradienteDaVariacao(), 'linear-gradient(to right, #a8431b, #eb6834, #f2ad8c 48%, #c9c7bf 48% 52%, #9cc2ee 52%, #2a78d6, #184f95)');
  assert.equal(M.gradienteDaVariacao(P), 'linear-gradient(to right, #f2ad8c, #d95926, #a8431b 48%, #45443f 48% 52%, #1c5cab 52%, #3987e5, #9ec5f4)');
  // Séries: a cor da linha é a da família no esquema.
  const serie = {...item(), tendencia: {avaliavel: true, familia: 'CRESCIMENTO', classe: 'CRESCIMENTO', observacoes: [{competencia: '202306', valor: 1}]}};
  const {series} = M.montarSeries({itens: [serie], janela: ['202306'], dominio: [0, 2], x0: 0, x1: 100, y0: 0, y1: 100, paleta: P});
  assert.equal(series[0].cor, '#3987e5');
  const semFamilia = M.montarSeries({itens: [{...item(), tendencia: null}], janela: ['202306'], dominio: [0, 2], x0: 0, x1: 100, y0: 0, y1: 100, paleta: P});
  assert.equal(semFamilia.series[0].cor, P.naoAvaliavel);
});

test('cores do mapa por esquema: as mesmas chaves, a rampa contínua do escuro do escuro ao claro e os textos a 4,5:1', () => {
  assert.equal(MP.coresDoMapa('claro'), MP.MAPA_CORES);
  assert.equal(MP.coresDoMapa('escuro'), MP.MAPA_CORES_ESCURO);
  assert.deepEqual(Object.keys(MP.MAPA_CORES_ESCURO).sort(), Object.keys(MP.MAPA_CORES).sort());
  for (const [chave, valor] of Object.entries(MP.MAPA_CORES_ESCURO))
    assert.match(valor, /^(#[0-9a-f]{6}|rgba\(\d+, \d+, \d+, 0?\.\d+\))$/, chave);
  const C = MP.MAPA_CORES_ESCURO, P = M.PALETA_ESCURA;
  // A mesma superfície, as mesmas tintas e o mesmo neutro do gráfico no escuro.
  assert.equal(C.superficie, P.superficie);
  assert.equal(C.tinta, P.tinta);
  assert.equal(C.tinta2, P.tinta2);
  assert.equal(C.muda, P.muda);
  assert.equal(C.eixo, P.eixo);
  assert.equal(C.neutro, P.bolha);
  assert.equal(C.naoAvaliavel, P.naoAvaliavel);
  assert.equal(MP.MAPA_CORES.neutro, M.PALETA_CLARA.bolha);
  for (const [texto, fundo] of [[C.tinta, C.superficie], [C.tinta2, C.superficie], [C.muda, C.superficie], [C.textoApoio, C.painel],
    [C.textoApoio, C.superficie], [C.controleTexto, C.painel], [C.controleTexto, C.controleRealce], [C.destaqueTexto, C.destaqueFundo],
    [C.painel, C.destaqueTexto]])
    assert.ok(contraste(texto, fundo) >= 4.5, texto + ' sobre ' + fundo + ': ' + contraste(texto, fundo).toFixed(2));
  // Fundo, esmaecidos e mapinha: recessivos, mas à vista, como no claro.
  for (const cor of [C.fundo, C.esmaecido, C.esmaecidoBorda, C.miniPontos]) {
    assert.ok(contraste(cor, C.superficie) > 1.15 && contraste(cor, C.superficie) < 2, cor);
    assert.ok(L(cor) > L(C.superficie), cor + ' acima da superfície');
  }
  assert.ok(contraste(C.foco, C.superficie) >= 3);
  // Rampa contínua: no claro, como antes; no escuro, do escuro (menor) ao claro (maior).
  assert.equal(MP.rampaContinua('claro'), MP.RAMPA_CONTINUA);
  assert.deepEqual([...MP.rampaContinua('escuro')], ['#184f95', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4']);
  rampaOrdinal([...MP.RAMPA_CONTINUA], MP.MAPA_CORES.superficie, false, 'contínua clara');
  rampaOrdinal([...MP.RAMPA_CONTINUA_ESCURA], C.superficie, true, 'contínua escura');
  const escura = MP.rampaContinua('escuro');
  assert.equal(MP.corContinua(0, [0, 100], 'linear', escura), '#184f95');
  assert.equal(MP.corContinua(100, [0, 100], 'linear', escura), '#9ec5f4');
  assert.equal(MP.corContinua(50, [0, 100], 'linear', escura), '#3987e5');
  assert.equal(MP.gradienteDaRampa(escura), 'linear-gradient(to right, #184f95 0%, #256abf 25%, #3987e5 50%, #6da7ec 75%, #9ec5f4 100%)');
  // Cena no escuro: a vazada mostra a superfície escura; os quintis pintam com a cor que a área entrega (a do grupo).
  const ponto = (id, densidade) => ({item: {id, tipo: 'municipio', rotulo: id, uf: 'AM', populacao: 10, quantidade: 1, densidade, distancia_km: null,
    motivos: [], referencia: false}, indice: 0});
  const base = {pontos: [ponto('a', 1), ponto('b', null)]};
  const entrada = {dentro: new Set(['a', 'b']), pintar: () => ({cor: '#000000', vazada: false, apagada: false}), valorContinuo: item => item.densidade,
    dominio: [0, 2], escala: 'linear', tamanho: () => null, maximoTamanho: null, cores: C, rampa: escura};
  const continua = MP.montarCena(base, {...entrada, pintura: 'continua'});
  assert.equal(continua.pontos.find(p => p.id === 'b').cor, C.superficie);
  assert.equal(continua.pontos.find(p => p.id === 'a').cor, '#3987e5');
  const quintis = MP.montarCena(base, {...entrada, pintar: () => ({cor: C.neutro, vazada: false, apagada: false}), pintura: 'quintis'});
  assert.ok(quintis.pontos.every(p => p.cor === C.neutro));
});

test('styles.css: o claro em :root e o escuro só na tela; as variáveis do desenho são as paletas do gráfico e do mapa', () => {
  assert.ok(inicioClaro >= 0 && inicioEscuro > inicioClaro, 'o claro antes do escuro');
  const blocosDeEsquema = [...CSS.matchAll(/@media[^{]*prefers-color-scheme[^{]*\{/g)].map(m => m[0].replace(/\s*\{$/, '').trim());
  assert.deepEqual(blocosDeEsquema, [SELETOR_ESCURO], 'um bloco escuro só, e só na tela: a impressão fica clara');
  assert.match(CSS.slice(inicioClaro, inicioEscuro), /color-scheme:\s*light/, 'controles nativos claros no claro e na impressão');
  assert.match(CSS.slice(inicioEscuro, fimEscuro), /color-scheme:\s*dark/, 'controles nativos escuros no escuro');
  for (const nome of Object.keys(ESCURO)) assert.ok(nome in CLARO, nome + ' tem o valor do claro');
  for (const nome of Object.keys(CLARO).filter(nome => nome.startsWith('--tom-'))) assert.ok(nome in ESCURO, nome + ' tem o valor do escuro');
  for (const [esquema, paleta, mapa] of [['claro', M.PALETA_CLARA, MP.MAPA_CORES], ['escuro', M.PALETA_ESCURA, MP.MAPA_CORES_ESCURO]]) {
    assert.equal(hexDe('--grafico-superficie', esquema), paleta.superficie, esquema);
    assert.equal(hexDe('--grafico-tinta', esquema), paleta.tinta, esquema);
    assert.equal(hexDe('--grafico-tinta-2', esquema), paleta.tinta2, esquema);
    assert.equal(hexDe('--grafico-muda', esquema), paleta.muda, esquema);
    assert.equal(hexDe('--grafico-serie', esquema), paleta.bolha, esquema);
    assert.equal(hexDe('--cor-superficie-elevada', esquema), mapa.painel, esquema + ': cartões e dica do mapa na superfície elevada');
    assert.equal(hexDe('--cor-foco', esquema), mapa.foco, esquema);
    assert.equal(hexDe('--cor-tinta', esquema), mapa.controleTexto, esquema);
  }
});

test('contraste no escuro: textos, avisos, links e botões a 4,5:1 ou mais nas superfícies em que aparecem; o foco a 3:1', () => {
  const v = nome => nome.startsWith('--tom-') ? hexDosCanais(nome, 'escuro') : hexDe(nome, 'escuro');
  const pares = [
    ['--cor-texto', '--cor-pagina'], ['--cor-texto', '--cor-superficie'], ['--cor-texto', '--cor-superficie-elevada'],
    ['--cor-tinta', '--cor-superficie'], ['--cor-tinta', '--cor-superficie-elevada'], ['--cor-tinta', '--cor-superficie-suave'],
    ['--cor-tinta', '--cor-realce'], ['--cor-tinta', '--cor-realce-destaque'], ['--cor-tinta', '--tom-blue-50'],
    ['--cor-texto-forte', '--cor-superficie-suave'], ['--cor-texto-2', '--cor-superficie'], ['--cor-texto-2', '--cor-superficie-suave'],
    ['--cor-texto-2', '--cor-superficie-elevada'], ['--cor-texto-2', '--grafico-superficie'], ['--cor-texto-apoio', '--cor-pagina'],
    ['--cor-texto-apoio', '--cor-superficie'], ['--cor-texto-3', '--cor-superficie'], ['--cor-texto-desligado', '--tom-slate-50'],
    ['--tom-slate-700', '--tom-slate-100'], ['--tom-slate-700', '--cor-superficie-elevada'], ['--tom-slate-600', '--cor-superficie'],
    ['--tom-slate-600', '--cor-superficie-elevada'], ['--tom-slate-500', '--cor-superficie'], ['--tom-slate-500', '--cor-superficie-elevada'],
    ['--tom-slate-400', '--cor-pagina'],
    // Destaque (identidade), links e ações
    ['--cor-destaque', '--cor-pagina'], ['--cor-destaque', '--cor-superficie'], ['--cor-destaque', '--cor-superficie-elevada'],
    ['--cor-destaque', '--grafico-superficie'], ['--cor-destaque', '--tom-cyan-50'], ['--cor-destaque', '--tom-cyan-100'],
    ['--cor-destaque', '--tom-blue-50'], ['--cor-destaque-texto', '--cor-superficie'], ['--cor-destaque-texto', '--cor-superficie-suave'],
    ['--cor-destaque-texto', '--cor-realce-destaque'], ['--cor-destaque-texto', '--cor-superficie-elevada'],
    // Botões: o preenchimento claro com o texto escuro (a tinta e o destaque viram no escuro)
    ['--cor-sobre-tinta', '--cor-tinta'], ['--cor-sobre-tinta', '--cor-destaque'], ['--cor-sobre-tinta', '--cor-destaque-realce'],
    ['--tom-white', '--tom-blue-600'], ['--tom-white', '--tom-blue-700'], ['--tom-white', '--tom-ink-realce'], ['--tom-white', '--cor-enviar'],
    ['--tom-white', '--cor-enviar-realce'],
    // Avisos e erros
    ['--tom-amber-900', '--tom-amber-50'], ['--tom-amber-900', '--cor-superficie'], ['--tom-amber-900', '--cor-superficie-elevada'],
    ['--tom-amber-800', '--tom-amber-50'], ['--tom-rose-800', '--tom-rose-50'], ['--tom-rose-800', '--cor-superficie'],
    ['--tom-rose-800', '--cor-superficie-elevada'],
    // Níveis do alerta do Detector (comando V23): o moderado usa o âmbar acima; o elevado, o laranja; o crítico, o rosa com o texto claro.
    ['--tom-orange-900', '--tom-orange-50'], ['--tom-orange-900', '--cor-superficie'], ['--tom-white', '--tom-rose-800'],
    // Desenho
    ['--grafico-tinta', '--grafico-superficie'], ['--grafico-tinta-2', '--grafico-superficie'], ['--grafico-tinta-2', '--cor-superficie-elevada'],
    ['--grafico-muda', '--grafico-superficie'],
  ];
  for (const [texto, fundo] of pares) {
    const razao = contraste(v(texto), v(fundo));
    assert.ok(razao >= 4.5, texto + ' sobre ' + fundo + ': ' + razao.toFixed(2) + ':1');
  }
  for (const fundo of ['--cor-pagina', '--cor-superficie', '--cor-superficie-elevada', '--cor-superficie-suave', '--grafico-superficie'])
    assert.ok(contraste(v('--cor-foco'), v(fundo)) >= 3, 'foco visível sobre ' + fundo);
  for (const [borda, fundo] of [['--cor-borda-nav', '--cor-superficie'], ['--cor-borda-painel', '--cor-superficie-elevada'],
    ['--tom-rose-600', '--cor-superficie'], ['--cor-enviar-borda', '--cor-superficie-elevada']])
    assert.ok(contraste(v(borda), v(fundo)) >= 3, borda + ' sobre ' + fundo);
  // Elevação no escuro: página < cartão < gráfico < elevado (mais claro é mais alto).
  const ordem = ['--cor-pagina', '--cor-superficie', '--grafico-superficie', '--cor-superficie-elevada'].map(nome => luminancia(v(nome)));
  ordem.slice(1).forEach((valor, i) => assert.ok(valor > ordem[i], 'superfícies em ordem de elevação'));
});

test('AJ-01: o botão de abrir e fechar da árvore fica a 3:1 ou mais do fundo da linha, e a seta, do botão, no claro e no escuro', () => {
  // As cores vêm das regras de analise.css (o botão e o botão sob o mouse) e das variáveis de styles.css dos dois esquemas
  // (WCAG 2.2, critério 1.4.11: componentes e objetos gráficos a 3:1). As linhas da árvore ficam sobre a superfície do painel, a
  // superfície suave (a linha do Brasil), o realce de destaque (o estado como unidade) ou a página.
  const ANALISE = semComentarios(ler('src/analise.css'));
  const regra = seletor => {
    const achada = new RegExp(seletor.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '\\s*\\{([^}]*)\\}').exec(ANALISE);
    assert.ok(achada, 'a regra ' + seletor + ' em analise.css');
    return achada[1];
  };
  const variavel = (bloco, propriedade) => {
    const achada = new RegExp('(?:^|[;{\\s])' + propriedade + '\\s*:\\s*var\\((--[\\w-]+)\\)').exec(bloco);
    assert.ok(achada, propriedade + ' por variável');
    return achada[1];
  };
  const botao = regra('.analise-no-seta'), sobOMouse = regra('.analise-no-seta:hover');
  const fundo = variavel(botao, 'background'), seta = variavel(botao, 'color'), realce = variavel(sobOMouse, 'background');
  assert.deepEqual([fundo, seta, realce], ['--cor-destaque', '--cor-sobre-tinta', '--cor-destaque-realce']);
  assert.match(botao, /border-radius:\s*\d+px/, 'cantos arredondados');
  const lado = Number(/width:\s*(\d+)px/.exec(botao)?.[1]);
  assert.ok(lado >= 32 && Number(/height:\s*(\d+)px/.exec(botao)?.[1]) === lado, 'a área de toque de antes (32 px) ou maior');
  assert.match(ANALISE, /@media \(max-width: 699px\), \(pointer: coarse\) \{[^@]*\.analise-no-seta \{ width: 40px; height: 40px; \}/,
    'no celular e no toque, 40 px, como antes');
  for (const esquema of ['claro', 'escuro']) {
    const v = nome => nome.startsWith('--tom-') ? hexDosCanais(nome, esquema) : hexDe(nome, esquema);
    for (const cor of [fundo, realce]) {
      for (const linha of ['--cor-superficie', '--cor-superficie-suave', '--cor-realce-destaque', '--cor-pagina', '--cor-superficie-elevada']) {
        const razao = contraste(v(cor), v(linha));
        assert.ok(razao >= 3, esquema + ': ' + cor + ' sobre ' + linha + ' a ' + razao.toFixed(2) + ':1');
      }
      const daSeta = contraste(v(seta), v(cor));
      assert.ok(daSeta >= 3, esquema + ': a seta (' + seta + ') sobre ' + cor + ' a ' + daSeta.toFixed(2) + ':1');
    }
  }
  // Na tela: a seta para baixo com o nível fechado e para cima com ele aberto, nos três níveis, com os mesmos identificadores.
  const tela = ler('src/PainelTerritorios.tsx');
  assert.match(tela, /data-seta=\{aberta \? "cima" : "baixo"\}/);
  assert.match(tela, /\{aberta \? <ChevronUp [^>]*\/>\s*: <ChevronDown [^>]*\/>\}/);
  for (const testid of ['"analise-raiz-ver"', '"analise-regiao-ver"', '"analise-grupo-ver"', '"analise-busca-grupo-ver"']) assert.ok(tela.includes(testid), testid);
  assert.ok(!/rotate\(90deg\)/.test(ANALISE), 'a seta não gira mais: ela troca de sentido');
});

test('AJ-12 e AJ-13: a ponta dos grupos e faixas como desenhada (a 88%) a 2:1 ou mais da superfície; o contorno dos rótulos', () => {
  // As bolhas do gráfico são desenhadas a 88% de opacidade (a opacidade não muda): a cor que se vê é a mistura com a superfície.
  const grafico = ler('src/PainelChart.tsx');
  assert.ok(grafico.includes('<circle className="analise-marca" r={bolha.r} fill={bolha.cor} fillOpacity={bolha.vazada ? 1 : 0.88}'), 'as bolhas a 88%');
  const desenhada = (cor, superficie) => '#' + canais(cor).map((c, i) => Math.round(c * 0.88 + canais(superficie)[i] * 0.12)
    .toString(16).padStart(2, '0')).join('');
  for (const paleta of [M.PALETA_CLARA, M.PALETA_ESCURA]) {
    for (const total of [1, 2, 3, 4, 5]) {
      const ponta = paleta.ordinais[total][0], razao = contraste(desenhada(ponta, paleta.superficie), paleta.superficie);
      assert.ok(razao >= 2, paleta.superficie + ', ' + total + ' tons: ' + ponta + ' desenhado a 88% fica a ' + razao.toFixed(2) + ':1');
    }
  }
  // Os valores do comando: no claro, a rampa começa no #6da7ec (2,17:1 desenhado); no escuro, no #1c5cab (2,30:1 desenhado).
  assert.deepEqual(M.RAMPAS_ORDINAIS, {1: ['#2a78d6'], 2: ['#6da7ec', '#1c5cab'], 3: ['#6da7ec', '#2a78d6', '#104281'],
    4: ['#6da7ec', '#3987e5', '#256abf', '#104281'], 5: ['#6da7ec', '#3987e5', '#256abf', '#184f95', '#0d366b']});
  assert.equal(contraste(desenhada('#6da7ec', '#fcfcfb'), '#fcfcfb').toFixed(2), '2.17');
  assert.equal(contraste(desenhada('#1c5cab', '#1a1a19'), '#1a1a19').toFixed(2), '2.30');
  // Fica: a rampa contínua do mapa (os pontos sem transparência), as rampas de aumento e de redução e as cores da tendência.
  assert.deepEqual([...MP.RAMPA_CONTINUA], ['#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281']);
  assert.deepEqual([...MP.RAMPA_CONTINUA_ESCURA], ['#184f95', '#256abf', '#3987e5', '#6da7ec', '#9ec5f4']);
  assert.deepEqual([M.RAMPA_AUMENTO, M.RAMPA_REDUCAO, M.PALETA_ESCURA.aumento, M.PALETA_ESCURA.reducao],
    [['#9cc2ee', '#2a78d6', '#184f95'], ['#f2ad8c', '#eb6834', '#a8431b'], ['#1c5cab', '#3987e5', '#9ec5f4'], ['#a8431b', '#d95926', '#f2ad8c']]);
  // AJ-13: o contorno dos rótulos das bolhas, de 3 px, opaco e na cor da superfície do gráfico, nos dois modos (como os outros
  // rótulos do desenho); a posição dos rótulos e a regra que evita a sobreposição não mudam.
  const ANALISE = semComentarios(ler('src/analise.css'));
  const rotulo = /\.analise-rotulo \{([^}]*)\}/.exec(ANALISE)[1];
  assert.match(rotulo, /paint-order: stroke; stroke: var\(--grafico-superficie\); stroke-width: 3px;/);
  assert.ok(!/stroke-opacity/.test(rotulo), 'o contorno opaco');
  assert.match(ANALISE, /\.analise-linha-texto \{[^}]*stroke: var\(--grafico-superficie\); stroke-width: 3px;/);
  assert.match(semComentarios(ler('src/styles.css')), /\.painel-rotulo \{[^}]*stroke:var\(--grafico-superficie\); stroke-width:3px;/);
});

test('AJ-16 e AJ-22: no modo leve, 88% só quando a cor da bolha é um tom da rampa em uso (grupos ou faixas de 1 a 5 tons); o resto a 62%', () => {
  const [claro, escuro] = [M.PALETA_CLARA, M.PALETA_ESCURA];
  const item = (extra = {}) => ({id: 'code:1', tipo: 'municipio', rotulo: 'X (AM)', uf: 'AM', populacao: 10, quantidade: 1, densidade: 1,
    distancia_km: null, inicial: {populacao: 10, quantidade: 1, densidade: 1}, variacao_percentual: {populacao: 0, quantidade: 0, densidade: 0},
    avaliavel: {densidade: true, distancia: null, variacao: true}, motivos: [], referencia: false, ...extra});
  for (const paleta of [claro, escuro]) {
    // Os tons em uso: os da rampa dos grupos ou das faixas de 1 a 5 tons, a mesma lista da paleta (a camada leve é memorizada e
    // compara as propriedades por referência). Com mais de 5 (os decis, as faixas com mais de 5 rótulos) ou outra camada, nenhum, e
    // sempre a mesma lista vazia.
    for (const total of [1, 2, 3, 4, 5]) {
      assert.equal(M.tonsDaRampa('grupos', total, 0, paleta), paleta.ordinais[total]);
      assert.equal(M.tonsDaRampa('faixas', 0, total, paleta), paleta.ordinais[total]);
    }
    const nenhum = M.tonsDaRampa('unica', 5, 5, paleta);
    assert.deepEqual(nenhum, []);
    for (const [camada, grupos, faixas] of [['grupos', 10, 0], ['grupos', 0, 5], ['faixas', 0, 6], ['faixas', 5, 0], ['variacao', 5, 5],
      ['classes', 5, 5], ['condicoes', 5, 5], ['ordem', 5, 5]])
      assert.equal(M.tonsDaRampa(camada, grupos, faixas, paleta), nenhum, camada + ' ' + grupos + ' ' + faixas);
    // Bolha a bolha, pela pintura (pintar, no mesmo formato): os quintis, os quartis e as faixas de até 5 tons a 88%; os decis e as
    // faixas com mais de 5 rótulos (a cor única, com as linhas de corte), o cinza de fora das faixas, a cor única e as outras
    // camadas a 62%, como antes do AJ-16; a apagada (35%) e a vazada (inteira) não mudam.
    const noLeve = (camada, extra = {}, totais = {}) => {
      const p = {camada, indicador: 'densidade', limiteVariacao: 40, totalGrupos: 0, totalFaixas: 0, primeiros: null, paleta, ...totais};
      return M.opacidadeNoLeve(M.pintar(item(extra), p), M.tonsDaRampa(camada, p.totalGrupos, p.totalFaixas, paleta));
    };
    const grupo = (indice, total) => noLeve('grupos', {grupo: {indice, rotulo: indice + 'º'}}, {totalGrupos: total});
    const faixa = (indice, total) => noLeve('faixas', {faixa: indice === 'fora' ? 'fora' : {indice, rotulo: 'faixa ' + indice}}, {totalFaixas: total});
    assert.deepEqual([1, 2, 3, 4, 5].map(i => grupo(i, 5)), [0.88, 0.88, 0.88, 0.88, 0.88], 'quintis');
    assert.deepEqual([1, 4].map(i => grupo(i, 4)), [0.88, 0.88], 'quartis');
    assert.deepEqual([1, 7, 10].map(i => grupo(i, 10)), [0.62, 0.62, 0.62], 'decis');
    assert.deepEqual([1, 2, 3, 'fora'].map(i => faixa(i, 3)), [0.88, 0.88, 0.88, 0.62], 'faixas digitadas e o cinza de fora');
    assert.deepEqual([1, 6, 'fora'].map(i => faixa(i, 6)), [0.62, 0.62, 0.62], 'mais de 5 faixas');
    assert.equal(noLeve('unica'), 0.62, 'cor única');
    assert.equal(noLeve('condicoes', {condicoes: {situacao: 'ATENDE', porCondicao: [], motivo: null}}), 0.62);
    assert.equal(noLeve('condicoes', {condicoes: {situacao: 'NAO_ATENDE', porCondicao: [], motivo: null}}), 0.35, 'apagada');
    assert.equal(noLeve('grupos', {}, {totalGrupos: 5}), 1, 'sem grupo: vazada');
    assert.equal(M.opacidadeNoLeve({cor: paleta.ordinais[5][0], vazada: false, apagada: true}, paleta.ordinais[5]), 0.35, 'a apagada vem antes do tom');
  }
  // Por quê: a 62%, a ponta das rampas fica abaixo de 2:1 da superfície (1,70:1 no claro e 1,74:1 no escuro); a 88%, os números do
  // AJ-12 (a conta dos 2:1 de cada rampa está no teste do AJ-12). Na cor única (e nos decis), a transparência passa (2,28:1 e 2,99:1)
  // e continua mostrando onde há muitas bolhas.
  const desenhada = (cor, superficie, alfa) => '#' + canais(cor).map((c, i) => Math.round(c * alfa + canais(superficie)[i] * (1 - alfa))
    .toString(16).padStart(2, '0')).join('');
  const razao = (cor, superficie, alfa) => contraste(desenhada(cor, superficie, alfa), superficie).toFixed(2);
  assert.deepEqual([0.62, 0.88].map(alfa => [razao(claro.ordinais[5][0], claro.superficie, alfa), razao(escuro.ordinais[5][0], escuro.superficie, alfa)]),
    [['1.70', '1.74'], ['2.17', '2.30']]);
  assert.deepEqual([razao(claro.bolha, claro.superficie, 0.62), razao(escuro.bolha, escuro.superficie, 0.62)], ['2.28', '2.99']);
  // No gráfico: a camada leve usa essa opacidade, com os tons da rampa em uso que a área leva ao gráfico (a camada em uso, os totais
  // de grupos e de faixas e a paleta do esquema; a pintura não muda de formato). Ficam o esmaecer da camada inteira com o destaque da
  // análise (30%) e as bolhas do modo normal (88%); o gráfico do Detector de Sinais, que pinta pelo nível, não leva os tons e continua
  // a 62% no modo leve. A regra do AJ-16, pela camada em uso, saiu.
  const grafico = ler('src/PainelChart.tsx'), area = ler('src/AreaDeAnalise.tsx');
  assert.ok(grafico.includes('fill={bolha.cor} fillOpacity={opacidadeNoLeve(bolha, tons)}'), 'a camada leve');
  assert.ok(grafico.includes('esmaecida={!!destaque} tons={p.tonsDaRampa}'), 'os tons chegam à camada leve');
  assert.ok(grafico.includes('<g data-testid="analise-camada-leve" className="analise-camada-leve" opacity={esmaecida ? 0.3 : undefined}'), 'o esmaecer');
  assert.equal(grafico.split('fillOpacity={bolha.vazada ? 1 : 0.88}').length - 1, 1, 'o modo normal a 88%');
  assert.ok(area.includes(' tonsDaRampa={tonsDaRampa(camadaFinal, totalGrupos, totalFaixas, paleta)} '), 'os tons em uso, da área de análise');
  assert.ok(!ler('src/DetectorGraficos.tsx').includes('tonsDaRampa'), 'o gráfico do Detector, sem os tons');
  assert.ok(!('pelaRampaOrdinal' in M) && !grafico.includes('gruposOuFaixas') && !area.includes('gruposOuFaixas'), 'sem a regra do AJ-16 pela camada');
});

test('AJ-11 e AJ-15: o item selecionado no escuro — fundo verde-azulado escuro, texto claro e borda verde-água, também no traço dos painéis; no claro, o de antes', () => {
  // As variáveis novas nos dois blocos. No claro, os mesmos valores da tinta e nenhum contorno: o estilo calculado não muda.
  const novas = ['--cor-selecionado', '--cor-sobre-selecionado', '--cor-borda-selecionado', '--contorno-selecionado'];
  assert.deepEqual(novas.map(nome => CLARO[nome]), [CLARO['--cor-tinta'], CLARO['--cor-sobre-tinta'], CLARO['--cor-tinta'], 'none']);
  assert.deepEqual(novas.map(nome => ESCURO[nome]),
    ['rgb(var(--tom-cyan-100))', 'rgb(var(--tom-ink))', 'rgb(var(--tom-teal))', 'inset 0 0 0 1px rgb(var(--tom-teal))']);
  // No escuro: o texto a 4,5:1 ou mais sobre o fundo novo (também o texto de apoio das abas, desenhado a 78%); a borda a 3:1 ou
  // mais com o fundo novo e com o painel; o fundo escuro e o texto claro.
  const v = nome => nome.startsWith('--tom-') ? hexDosCanais(nome, 'escuro') : hexDe(nome, 'escuro');
  const fundo = v('--cor-selecionado'), texto = v('--cor-sobre-selecionado'), borda = v('--cor-borda-selecionado');
  assert.deepEqual([fundo, texto, borda], ['#1a3d3c', '#e6e5df', '#4fbdc6']);
  const mistura = (frente, atras, alfa) => '#' + canais(frente).map((c, i) => Math.round(c * alfa + canais(atras)[i] * (1 - alfa))
    .toString(16).padStart(2, '0')).join('');
  assert.match(semComentarios(ler('src/analise.css')), /\.analise-familia-apoio \{[^}]*opacity: \.78;/, 'o apoio das abas a 78%');
  for (const [nome, cor, minimo] of [['texto', texto, 4.5], ['apoio das abas', mistura(texto, fundo, 0.78), 4.5], ['texto secundário', v('--cor-texto-2'), 4.5]]) {
    const razao = contraste(cor, fundo);
    assert.ok(razao >= minimo, nome + ' sobre o selecionado: ' + razao.toFixed(2) + ':1');
  }
  for (const superficie of ['--cor-selecionado', '--cor-superficie', '--cor-superficie-suave', '--cor-pagina']) {
    const razao = contraste(borda, v(superficie));
    assert.ok(razao >= 3, 'borda do selecionado sobre ' + superficie + ': ' + razao.toFixed(2) + ':1');
  }
  assert.ok(luminancia(fundo) < 0.05 && luminancia(texto) > 0.5, 'fundo escuro e texto claro');
  assert.ok(contraste(texto, v('--cor-pagina')) > contraste(fundo, v('--cor-pagina')), 'o selecionado deixa de ser o elemento mais claro');
  // As regras de analise.css que passam a usar as variáveis novas (com a borda ou, onde o item não tem borda, o contorno por dentro).
  const ANALISE = semComentarios(ler('src/analise.css'));
  const SEL = '{ border-color: var(--cor-borda-selecionado); background: var(--cor-selecionado); color: var(--cor-sobre-selecionado); }';
  for (const seletor of ['.analise-familia[aria-selected="true"]', '.territorios-aba[aria-selected="true"]', '.territorios-botoes > button[aria-pressed="true"]',
    '.analise-funcao[aria-expanded="true"]', '.analise-botao-secundario[aria-pressed="true"]', '.analise-letra[aria-pressed="true"]',
    '.analise-so-estado[aria-pressed="true"]', '.analise-ferramenta-nova[aria-pressed="true"]', '.ferramenta-resumo-nivel[aria-pressed="true"]',
    '.ferramenta-modos .analise-botao-secundario[aria-pressed="true"], .ferramenta-atalhos .analise-botao-secundario[aria-pressed="true"]'])
    assert.ok(ANALISE.replace(/\{\s+/g, '{ ').includes(seletor + ' ' + SEL), seletor);
  assert.ok(ANALISE.includes('.analise-segmentos > button[aria-checked="true"], .analise-segmentos > button[aria-pressed="true"] { background: var(--cor-selecionado);\n' +
    '  color: var(--cor-sobre-selecionado); box-shadow: var(--contorno-selecionado); }'), 'os segmentos, com o contorno por dentro');
  assert.ok(ANALISE.includes('.analise-ferramentas-botao[aria-expanded="true"] { background: var(--cor-selecionado); color: var(--cor-sobre-selecionado);\n' +
    '  box-shadow: var(--contorno-selecionado); }'), 'o botão das ferramentas, com o contorno por dentro (a borda dele é a do campo)');
  assert.match(ANALISE, /\.territorios-marcado \{[^}]*border: 1px solid var\(--cor-borda-selecionado\);[^}]*background: var\(--cor-selecionado\); color: var\(--cor-sobre-selecionado\);/);
  assert.match(ANALISE, /\.analise-aba-painel \{[^}]*border-top: 3px solid var\(--cor-borda-selecionado\);/, 'o traço de cima do painel da aba');
  // AJ-15 (18/11/2026): o traço de cima do painel das ferramentas (o mesmo no Detector e no Simulador) passa a ser o do painel da
  // aba; antes, a tinta, que no escuro é um traço creme logo abaixo do botão verde-azulado da ferramenta. No escuro, o verde-água
  // fica a 8:1 do painel (a borda sobre --cor-superficie, acima); no claro, a variável é a própria tinta, e nada muda.
  assert.match(ANALISE, /\.analise-ferramenta-painel \{[^}]*border-top: 3px solid var\(--cor-borda-selecionado\);/, 'o traço de cima do painel das ferramentas');
  assert.ok(!ANALISE.includes('border-top: 3px solid var(--cor-tinta)'), 'nenhum traço de painel na tinta');
  // Ficam como estão: o número das etapas do Simulador (o único fundo da tinta que sobra) e o uso da tinta como cor de texto e de
  // borda — o passar do mouse dos controles do alto, as etiquetas, os cursores da régua e os marcados das fichas e dos contadores,
  // que ficam junto das cores dos dados: ali, o verde-água se confundiria com a cor única das bolhas no escuro (#1ba3b5), e o
  // contorno neutro é o certo. "Começar a análise" é uma classe do Tailwind (bg-ink), fora de analise.css.
  assert.deepEqual(ANALISE.match(/background: var\(--cor-tinta\)/g), ['background: var(--cor-tinta)']);
  assert.match(ANALISE, /\.ferramenta-etapa-numero \{[^}]*background: var\(--cor-tinta\); color: var\(--cor-sobre-tinta\);/);
  const regraDe = (css, seletor) => {
    const inicio = css.indexOf(seletor + ' {');
    assert.ok(inicio >= 0, seletor);
    return css.slice(inicio, css.indexOf('}', inicio));
  };
  for (const [seletor, declaracao] of [['.analise-controle-global:hover:not(:disabled)', 'border-color: var(--cor-tinta);'],
    ['.analise-chip[aria-pressed="true"]', 'border-color: var(--cor-tinta);'], ['.analise-etiqueta', 'border: 1px solid var(--cor-tinta);'],
    ['.analise-contagem[aria-pressed="true"]', 'border-color: var(--cor-tinta); box-shadow: inset 0 0 0 1px var(--cor-tinta);'],
    ['.analise-cursor::after', 'border: 2px solid var(--cor-tinta);']])
    assert.ok(regraDe(ANALISE, seletor).includes(declaracao), seletor + ': ' + declaracao);
  assert.ok(regraDe(semComentarios(ler('src/styles.css')), '.painel-cursor::after').includes('border:2px solid var(--cor-tinta);'), 'o cursor da régua do painel');
});

test('Tailwind: cada tom das classes lê uma variável com os dois esquemas; as classes mudam sozinhas no escuro', () => {
  const cores = TAILWIND.theme.extend.colors;
  const valores = [];
  const visitar = valor => typeof valor === 'string' ? valores.push(valor) : Object.values(valor).forEach(visitar);
  visitar(cores);
  visitar(TAILWIND.theme.extend.borderColor);
  assert.ok(valores.length >= 25);
  for (const valor of valores) {
    const nome = /var\((--tom-[\w-]+)\)/.exec(valor)?.[1];
    assert.ok(nome, 'cor das classes por variável: ' + valor);
    assert.match(CLARO[nome] ?? '', /^\d{1,3} \d{1,3} \d{1,3}$/, nome + ' no claro');
    assert.match(ESCURO[nome] ?? '', /^\d{1,3} \d{1,3} \d{1,3}$/, nome + ' no escuro');
  }
  for (const familia of ['white', 'ink', 'teal', 'canvas', 'line', 'slate', 'amber', 'rose', 'blue', 'cyan']) assert.ok(familia in cores, familia);
  // O claro continua o de antes: os tons do Tailwind e da identidade.
  assert.equal(hexDosCanais('--tom-white', 'claro'), '#ffffff');
  assert.equal(hexDosCanais('--tom-ink', 'claro'), '#0e2840');
  assert.equal(hexDosCanais('--tom-teal', 'claro'), '#0c8792');
  assert.equal(hexDosCanais('--tom-canvas', 'claro'), '#f5f8fb');
  assert.equal(hexDosCanais('--tom-line', 'claro'), '#dfebf0');
  assert.equal(hexDosCanais('--tom-slate-600', 'claro'), '#475569');
  assert.equal(hexDosCanais('--tom-amber-900', 'claro'), '#78350f');
  assert.equal(hexDosCanais('--tom-rose-800', 'claro'), '#9f1239');
  assert.equal(hexDosCanais('--tom-blue-600', 'claro'), '#2563eb');
  assert.equal(hexDosCanais('--tom-cyan-50', 'claro'), '#ecfeff');
  assert.equal(hexDosCanais('--tom-borda-padrao', 'claro'), '#e5e7eb', 'a borda padrão do preflight, o gray-200');
});

test('nenhuma cor fixa fora das variáveis nas folhas de estilo da página, da área de análise e do mapa', () => {
  const corFixa = /#[0-9a-fA-F]{3,8}\b|rgba?\(\s*\d/;
  const foraDosBlocos = CSS.slice(0, inicioClaro) + CSS.slice(fimEscuro + 1);
  for (const [nome, texto] of [['styles.css', foraDosBlocos], ['analise.css', semComentarios(ler('src/analise.css'))],
    ['mapa.css', semComentarios(ler('src/mapa.css'))]]) {
    const linhas = texto.split('\n').filter(linha => corFixa.test(linha));
    assert.deepEqual(linhas, [], nome + ': cores fixas fora das variáveis');
  }
  // O fecho do bloco escuro é o do @media (o :root escuro fica dentro dele).
  assert.equal(CSS.slice(fimEscuro).trimStart()[0], '}');
});
