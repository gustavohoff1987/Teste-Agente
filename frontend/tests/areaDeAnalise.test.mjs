import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';
import ts from 'typescript';
async function source(name, ajustar = code => code) {
  const code = ts.transpileModule(readFileSync(new URL('../src/' + name + '.ts', import.meta.url), 'utf8'),
    {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  return import('data:text/javascript;base64,' + Buffer.from(ajustar(code)).toString('base64'));
}
// Área de análise (23/10/2026): os ajustes dentro de cada análise, a vista do desenho (gráfico, mapa ou lado a lado), as decisões
// puras do mapa (disponibilidade com o motivo, pintura, opções da pergunta, cor contínua, tamanho e ligações), o estado salvo com
// a vista, o aspecto "mapa" dos não avaliáveis, a frase-resumo do motor e os dados do mapa no cliente (painelModel.ts e
// painelApi.ts, com a sessão substituída por um esboço: os testes não fazem pedidos).
const M = await source('painelModel');
const A = await source('painelApi', code => code.replace(/import\s*\{[^}]*\}\s*from\s*["']\.\/conversationSession["'];?/,
  'const contextRevision = () => 0; const fetch = globalThis.fetch;'));

const VAZIO = {populacao: null, quantidade: null, densidade: null};
const municipio = (id, rotulo, valores = {}) => ({id, tipo: 'municipio', rotulo, uf: rotulo.slice(-3, -1), populacao: 1000, quantidade: 10,
  densidade: 10, distancia_km: null, inicial: {...VAZIO}, variacao_percentual: {...VAZIO},
  avaliavel: {densidade: true, distancia: null, variacao: null}, motivos: [], referencia: false, ...valores});
const SEM_REGISTRO = 'Sem registro em junho de 2024 na categoria MEDICINA: valores não avaliáveis, nunca zero (SEM_REGISTRO_OBSERVADO)';
const SEM_PONTO = 'Sem coordenada válida da sede municipal na competência (SEM_INFORMACAO_ESPACIAL)';
const BR = M.ROTULOS_BRASIL;
const DISTRITOS = {unidade: {singular: 'distrito', plural: 'distritos'}, grupo: {singular: 'província', plural: 'províncias'}};
const definicao = (extra = {}) => ({...M.definicaoInicial({tipo: 'brasil', periodos: ['202306', '202406'], categoria: 'MEDICINA', temGrupos: true}), ...extra});
const resposta = (extra = {}) => ({competencia: '202406', competencia_inicial: null, categoria: 'MEDICINA', versao_base: 'v1', chave_execucao: 'k1',
  nivel: 'municipios', referencia: null, itens: [], dominios: {}, notas: ['Nota do motor.'], limitacoes: [], tendencia: null, grupos: null,
  faixas: null, faixasDistancia: null, condicoes: null, ordenacao: null, comparacao: null, contextoBrasil: null, disponibilidade: {}, sessao: null,
  rotulos: null, indicador: 'densidade', resumo: null, ...extra});

test('ajustes dentro da análise: cada aba só com os seus; o mesmo indicador em todas, menos na rotatividade; nos estados, os da distribuição', () => {
  const a = extra => M.ajustesDaAnalise({familia: 'distribuicao', nivel: 'municipios', disponivel: true, categorias: 1, ...extra});
  assert.deepEqual(a({}), ['indicador', 'competencia', 'agrupar']);
  assert.deepEqual(a({categorias: 2}), ['indicador', 'categoria', 'competencia', 'agrupar']);  // a categoria junto do indicador
  assert.deepEqual(a({familia: 'espacial'}), ['indicador', 'competencia', 'referencia']);
  assert.deepEqual(a({familia: 'tendencia', categorias: 3}), ['indicador', 'categoria', 'janela', 'visao']);
  assert.deepEqual(a({familia: 'rotatividade'}), ['periodos']);
  assert.deepEqual(a({familia: 'rotatividade', categorias: 2}), ['periodos', 'categoria']);
  // O indicador é um só (fica na definição): a escolha acompanha a pessoa em todas as abas que o têm, sempre à vista e em primeiro.
  for (const familia of ['distribuicao', 'espacial', 'tendencia']) assert.equal(a({familia})[0], 'indicador');
  // Nos estados (E1), o desenho é o dos estados, qualquer que seja a aba; com a família indisponível, o da distribuição.
  for (const familia of ['distribuicao', 'espacial', 'tendencia']) assert.deepEqual(a({familia, nivel: 'estados'}), ['indicador', 'competencia', 'agrupar']);
  assert.deepEqual(a({familia: 'rotatividade', disponivel: false}), ['indicador', 'competencia', 'agrupar']);
  // A escala não é ajuste da análise: fica junto do desenho.
  for (const familia of ['distribuicao', 'espacial', 'tendencia', 'rotatividade']) assert.ok(!a({familia}).includes('escala'));
  assert.equal(M.TEXTO_SEM_POPULACAO, 'Sem população na planilha: só a quantidade.');
});

test('vista do desenho: o mapa nos municípios; desligado nos estados (com o atalho), na planilha sem coordenadas e em Séries, com o motivo', () => {
  const d = extra => M.disponibilidadeDoMapa({fonte: 'brasil', temCoordenadas: true, nivel: 'municipios', series: false, rotatividade: false,
    rotulos: BR, ...extra});
  assert.deepEqual(d({}), {disponivel: true, motivo: null, atalho: null});
  // Os estados não têm um ponto (os ladrilhos não foram aprovados): o atalho leva aos municípios no mapa.
  assert.deepEqual(d({nivel: 'estados'}), {disponivel: false, atalho: 'Ver os municípios no mapa',
    motivo: 'Os estados não têm um ponto no mapa: cada ponto do mapa é um município.'});
  const semColunas = d({fonte: 'arquivo', temCoordenadas: false, rotulos: DISTRITOS});
  assert.equal(semColunas.disponivel, false);
  assert.equal(semColunas.atalho, null);
  assert.equal(semColunas.motivo, 'A planilha não tem as colunas de latitude e longitude: o mapa precisa das coordenadas de cada distrito. ' +
    'A tabela continua.');
  assert.ok(d({fonte: 'arquivo', temCoordenadas: false, rotatividade: true, rotulos: DISTRITOS}).motivo
    .startsWith('Sem latitude e longitude na planilha, a rotatividade fica nas barras'));
  assert.equal(d({fonte: 'arquivo', temCoordenadas: true, rotatividade: true, rotulos: DISTRITOS}).disponivel, true);
  const series = d({series: true});
  assert.equal(series.disponivel, false);
  assert.equal(series.motivo, 'Na visão Séries, cada município é uma linha no tempo: o mapa fica com Classes e Mudança.');
  // Numa planilha com grupos, os nomes da planilha.
  assert.deepEqual(d({fonte: 'arquivo', nivel: 'estados', rotulos: DISTRITOS}), {disponivel: false, atalho: 'Ver os distritos no mapa',
    motivo: 'As províncias não têm um ponto no mapa: cada ponto do mapa é um distrito.'});
  assert.equal(d({fonte: null}).disponivel, false);
  assert.equal(M.LARGURA_LADO_A_LADO, 1600);
});

test('pintura do mapa: a camada do gráfico, a cor contínua (rotatividade ou escolha da pessoa) ou a pergunta; as opções de cada análise', () => {
  const p = extra => M.pinturaDoMapa({camada: 'unica', rotatividade: false, corContinua: false, ...extra});
  assert.equal(p({}), 'pergunta');  // sem cor escolhida, o mapa pergunta (decisão de 23/10)
  assert.equal(p({corContinua: true}), 'continua');
  for (const camada of ['grupos', 'faixas', 'condicoes', 'ordem', 'classes', 'variacao']) {
    assert.equal(p({camada}), 'camada');
    assert.equal(p({camada, corContinua: true}), 'camada');  // a camada em uso no gráfico vale também no mapa
  }
  assert.equal(p({rotatividade: true}), 'continua');
  assert.deepEqual(M.opcoesDePintura('distribuicao'), ['quintis', 'faixas', 'continua']);
  assert.deepEqual(M.opcoesDePintura('espacial'), ['continua', 'condicoes']);
  assert.deepEqual(M.opcoesDePintura('tendencia'), []);
  assert.deepEqual(M.opcoesDePintura('rotatividade'), []);
  // Cor contínua: o indicador no domínio do motor, ou a permanência da coorte inicial de 0 a 100%.
  const dominios = {densidade: [0.5, 15], quantidade: [1, 105], populacao: [1000, 9000]};
  const cor = M.corContinuaDoMapa({rotatividade: false, indicador: 'densidade', dominios});
  assert.deepEqual([cor.rotulo, cor.dominio], ['Densidade (por 1.000 habitantes)', [0.5, 15]]);
  assert.equal(cor.valor(municipio('code:1', 'A (AM)', {densidade: 2.5})), 2.5);
  assert.equal(cor.valor(municipio('code:1', 'A (AM)', {densidade: null})), null);
  assert.equal(M.corContinuaDoMapa({rotatividade: false, indicador: 'quantidade', dominios}).rotulo, 'Quantidade (profissionais)');
  const permanencia = M.corContinuaDoMapa({rotatividade: true, indicador: 'densidade', dominios});
  assert.deepEqual([permanencia.rotulo, permanencia.dominio], ['Permanência da coorte inicial (%)', [0, 100]]);
  assert.equal(permanencia.valor(municipio('code:2', 'B (AM)', {rotatividade: {coorteInicial: 120, permanencia: 72.5}})), 72.5);
  // Tamanho (área proporcional): população na densidade, quantidade na quantidade, coorte inicial na rotatividade.
  const populacao = M.tamanhoDoMapa({rotatividade: false, indicador: 'densidade', dominios});
  assert.deepEqual([populacao.rotulo, populacao.maximo, populacao.valor(municipio('code:1', 'A (AM)', {populacao: 1234}))], ['População', 9000, 1234]);
  const quantidade = M.tamanhoDoMapa({rotatividade: false, indicador: 'quantidade', dominios});
  assert.deepEqual([quantidade.rotulo, quantidade.maximo, quantidade.valor(municipio('code:1', 'A (AM)', {quantidade: 7}))],
    ['Quantidade de profissionais', 105, 7]);
  const coorte = M.tamanhoDoMapa({rotatividade: true, indicador: 'densidade', dominios});
  assert.deepEqual([coorte.rotulo, coorte.maximo, coorte.valor(municipio('code:2', 'B (AM)', {rotatividade: {coorteInicial: 120}}))],
    ['Coorte inicial', null, 120]);
});

test('ligações ilustrativas do mapa: só das unidades selecionadas, até a referência mais próxima do motor (com o empate), até 30', () => {
  const manaus = {id: 'code:130260', rotulo: 'MANAUS (AM)'};
  const itens = [municipio('code:130260', 'MANAUS (AM)', {referencia: true}),
    municipio('code:130420', 'TEFE (AM)', {referencia_mais_proxima: [manaus]}),
    municipio('code:130340', 'PARINTINS (AM)', {referencia_mais_proxima: [manaus, {id: 'code:130185', rotulo: 'IRANDUBA (AM)'}]}),
    municipio('code:350010', 'FORA (SP)', {referencia_mais_proxima: null}),
    {...municipio('c1', 'Interior'), tipo: 'conjunto', referencia_mais_proxima: [manaus]}];
  assert.deepEqual(M.ligacoesDoMapa(itens, ['code:130340', 'code:130260', 'code:350010', 'c1', 'code:130420']),
    [{de: 'code:130340', para: ['code:130260', 'code:130185']}, {de: 'code:130420', para: ['code:130260']}]);
  assert.deepEqual(M.ligacoesDoMapa(itens, []), []);
  const muitos = Array.from({length: 40}, (_, i) => municipio('code:' + (100000 + i), 'M' + i + ' (AM)', {referencia_mais_proxima: [manaus]}));
  assert.equal(M.MAX_LIGACOES, 30);
  assert.equal(M.ligacoesDoMapa(muitos, muitos.map(item => item.id)).length, 30);
});

test('Histórico: a vista do desenho e a cor contínua entram no estado salvo; o estado de antes, sem os campos, continua legível', () => {
  const def = definicao({nivel: 'municipios', base: {todos: false, estados: ['13'], ids: []}});
  const corpo = resposta();
  const salvo = M.salvarEstado('Densidade de médicos', {chave: 'k', familia: 'distribuicao', opcoes: {competencia: '202406', categoria: 'MEDICINA'},
    definicao: def, visual: {escala: 'linear', corte: null, selecionados: [], vista: 'mapa', corContinua: true}}, corpo, '2026-10-23T12:00:00.000Z');
  const lido = M.lerEstadoSalvo(salvo);
  assert.deepEqual(lido.visual, {escala: 'linear', corte: null, selecionados: [], vista: 'mapa', corContinua: true});
  assert.deepEqual(lido, {...salvo.definicao, resposta: corpo});
  const lado = M.salvarEstado('T', {...salvo.definicao, visual: {...salvo.definicao.visual, vista: 'lado'}}, corpo);
  assert.equal(M.lerEstadoSalvo(lado).visual.vista, 'lado');  // numa janela estreita, a área troca pelo mapa
  // Estado de antes de 23/10, sem vista nem cor: reabre sem os campos (a área mostra o gráfico, e o mapa pergunta como pintar).
  const antigo = {titulo: 'T', quando: '', resposta: corpo, definicao: {versao: 1, chave: 'k', familia: 'distribuicao', opcoes: null, definicao: def,
    visual: {escala: 'logaritmica', corte: null, selecionados: ['code:130260']}}};
  assert.deepEqual(M.lerEstadoSalvo(antigo).visual, {escala: 'logaritmica', corte: null, selecionados: ['code:130260']});
  // Valores estranhos ficam de fora, sem derrubar o estado.
  const estranho = {...antigo, definicao: {...antigo.definicao, visual: {...antigo.definicao.visual, vista: 'tela-cheia', corContinua: 'sim'}}};
  assert.deepEqual(M.lerEstadoSalvo(estranho).visual, {escala: 'logaritmica', corte: null, selecionados: ['code:130260']});
});

test('não avaliáveis no mapa: com o mapa à vista, a unidade sem coordenada válida entra à parte, com o motivo do motor, e continua no gráfico', () => {
  const itens = [municipio('code:130420', 'TEFE (AM)'), municipio('code:130260', 'MANAUS (AM)'),
    municipio('code:130185', 'IRANDUBA (AM)', {populacao: null, quantidade: null, densidade: null, motivos: [SEM_REGISTRO],
      avaliavel: {densidade: false, distancia: null, variacao: null}})];
  const semCoordenada = new Map([['code:130420', SEM_PONTO], ['code:130260', ''], ['code:130185', SEM_PONTO]]);
  const {plotaveis, fora} = M.separarItens(itens, 'densidade', {semCoordenada});
  assert.deepEqual(plotaveis.map(item => item.id), ['code:130260', 'code:130420']);  // no gráfico, as bolhas ficam
  assert.deepEqual(fora.map(item => [item.id, item.aspecto, item.motivo]), [['code:130185', 'indicador', SEM_REGISTRO],
    ['code:130260', 'mapa', 'Sem coordenada válida para o mapa.'], ['code:130420', 'mapa', SEM_PONTO]]);
  // Sem o mapa à vista, a lista não muda.
  assert.deepEqual(M.separarItens(itens, 'densidade', {}).fora.map(item => item.aspecto), ['indicador']);
  assert.deepEqual(M.separarItens(itens, 'densidade', {semCoordenada: null}).fora.map(item => item.aspecto), ['indicador']);
  // Na rotatividade, a coorte avaliável sem coordenada também; a não avaliável fica só com o motivo da coorte.
  const coortes = [municipio('code:3', 'C (AM)', {rotatividade: {coorteInicial: 120, permaneceram: 87, sairam: 33, permanencia: 72.5, saida: 27.5,
    avaliavel: true, motivo: null}}), municipio('code:4', 'D (AM)', {rotatividade: {coorteInicial: null, permaneceram: null, sairam: null,
    permanencia: null, saida: null, avaliavel: false, motivo: 'Não avaliável: sem registro observado em um dos períodos (SEM_REGISTRO_OBSERVADO)'}})];
  const rot = M.separarItens(coortes, 'densidade', {rotatividade: true, semCoordenada: new Map([['code:3', SEM_PONTO], ['code:4', SEM_PONTO]])});
  assert.deepEqual(rot.plotaveis.map(item => item.id), ['code:3']);
  assert.deepEqual(rot.fora.map(item => [item.id, item.aspecto]), [['code:3', 'mapa'], ['code:4', 'rotatividade']]);
  // A dica do ponto na rotatividade traz a permanência e a coorte inicial do motor.
  const dica = M.montarDica(coortes[0], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR});
  assert.ok(dica.linhas.some(linha => linha.rotulo === 'Permanência da coorte inicial' && linha.valor === '72,50%'));
  assert.ok(dica.linhas.some(linha => linha.rotulo === 'Coorte inicial' && linha.valor === '120'));
  assert.ok(M.montarDica(coortes[1], {indicador: 'densidade', competencia: '202406', competenciaInicial: null, distancia: false, variacao: false,
    tendencia: false, nomes: new Map(), rotulos: BR}).notas.some(nota => nota.endsWith('(SEM_REGISTRO_OBSERVADO)')));
});

test('conversa: "ver no mapa" e "volte ao gráfico" são estado visual; o mapa vale para a análise que resulta do pedido; nos estados, o motivo', () => {
  const c = {periodos: ['202306', '202406'], nomes: new Map(), temGrupos: true,
    disponivel: f => M.disponibilidadeDaFamilia(f, {fonte: 'brasil', nivel: 'municipios', disponibilidade: null, temIdentificador: false, rotulos: BR}),
    mapa: d => M.disponibilidadeDoMapa({fonte: 'brasil', temCoordenadas: true, nivel: d.nivel, series: false, rotatividade: false, rotulos: BR})};
  const estados = definicao();
  const noMapa = M.aplicarPedido(estados, {vista: 'mapa'}, c);
  assert.equal(noMapa.vista, null);
  assert.deepEqual(noMapa.mensagens, ['Mapa: Os estados não têm um ponto no mapa: cada ponto do mapa é um município.']);
  assert.equal(noMapa.definicao.nivel, 'estados');  // a vista não muda a análise
  const amazonas = M.aplicarPedido(estados, {municipios: {todos: false, estados: ['13'], ids: []}, vista: 'mapa'}, c);
  assert.equal(amazonas.vista, 'mapa');
  assert.deepEqual(amazonas.mensagens, []);
  assert.equal(M.aplicarPedido(estados, {vista: 'grafico'}, c).vista, 'grafico');
  assert.equal(M.aplicarPedido(estados, {}, c).vista, null);
  const {mapa, ...semConferencia} = c;
  assert.equal(M.aplicarPedido(estados, {vista: 'mapa'}, semConferencia).vista, 'mapa');
});

test('frase-resumo do motor no cliente e no arquivo de método; dados do mapa normalizados (pontos num Map, sem coordenada com o motivo)', () => {
  const bruta = {competencia: '202406', categoria: 'MEDICINA', nivel: 'municipios', indicador: 'quantidade', itens: [],
    resumo: {texto: '  Nos 62 municípios do Amazonas, em junho de 2024, a quantidade de médicos vai de 1 a 4.730.  '}};
  const r = A.normalizarResposta(bruta);
  assert.deepEqual(r.resumo, {texto: 'Nos 62 municípios do Amazonas, em junho de 2024, a quantidade de médicos vai de 1 a 4.730.'});
  assert.equal(r.indicador, 'quantidade');
  const antiga = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: []});
  assert.deepEqual([antiga.resumo, antiga.indicador], [null, null]);  // a resposta de antes continua legível
  assert.deepEqual(A.resumoDe('Frase do motor.'), {texto: 'Frase do motor.'});
  assert.equal(A.resumoDe({texto: '   '}), null);
  assert.equal(A.resumoDe(null), null);
  const metodo = M.textoDoMetodo(resposta({resumo: {texto: 'Frase do motor.'}}), 'Densidade de médicos', null);
  assert.deepEqual(metodo.split('\n').slice(0, 4), ['Densidade de médicos', 'Frase do motor.', '', 'Procedência']);
  assert.ok(!M.textoDoMetodo(resposta({resumo: {texto: 'Frase do motor.'}}), 'T', null, null).includes('Frase do motor.'));  // fora da tela, fora do arquivo
  assert.deepEqual(M.textoDoMetodo(resposta(), 'T', null).split('\n').slice(0, 2), ['T', '']);
  const dados = A.normalizarMapa({competencia: '202406', referencial: 'SIRGAS2000',
    pontos: [{id: 'code:130260', lat: -3.1019, lon: -60.025}, {id: 'code:130420', lat: '-3.35', lon: -64.71}, {id: 'code:1', lat: 95, lon: 0}, {lat: 1, lon: 1}],
    sem_coordenada: [{id: 'code:130185', rotulo: 'IRANDUBA (AM)', motivo: SEM_PONTO}, {rotulo: 'sem identificador'}]});
  assert.equal(dados.competencia, '202406');
  assert.equal(dados.referencial, 'SIRGAS2000');
  assert.ok(dados.pontos instanceof Map);
  assert.deepEqual([...dados.pontos.entries()], [['code:130260', [-3.1019, -60.025]]]);
  assert.deepEqual(dados.semCoordenada, [{id: 'code:130185', rotulo: 'IRANDUBA (AM)', motivo: SEM_PONTO}]);
  assert.throws(() => A.normalizarMapa({competencia: '202406'}), erro => erro instanceof A.ErroDoMotor);
});
