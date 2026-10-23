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
// puras do mapa (disponibilidade com o motivo, pintura com os quintis do motor, cor contínua, tamanho e ligações), o estado salvo
// com a vista, o aspecto "mapa" dos não avaliáveis, a frase-resumo do motor, os dados do mapa no cliente, os nomes das abas, a
// apresentação de cada aba e as explicações da tendência (painelModel.ts e painelApi.ts, com a sessão substituída por um esboço:
// os testes não fazem pedidos).
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

test('pintura do mapa: a camada do gráfico, a cor contínua da rotatividade ou os 5 grupos iguais (quintis) do motor, sem pergunta', () => {
  const p = extra => M.pinturaDoMapa({camada: 'unica', rotatividade: false, gruposDoMapa: true, ...extra});
  assert.equal(p({}), 'quintis');  // sem cor própria da análise, os quintis que o motor devolveu em grupos_mapa
  assert.equal(p({gruposDoMapa: false}), 'camada');  // sem eles (uma análise guardada antes), a cor única do gráfico
  for (const camada of ['grupos', 'faixas', 'condicoes', 'ordem', 'classes', 'variacao']) {
    assert.equal(p({camada}), 'camada');  // a camada em uso no gráfico vale também no mapa
    assert.equal(p({camada, gruposDoMapa: false}), 'camada');
  }
  assert.equal(p({rotatividade: true}), 'continua');
  assert.equal(M.opcoesDePintura, undefined);  // a pergunta "Como pintar o mapa?" saiu (23/10/2026)
  // O pedido leva os quintis do mapa só quando a análise não tem cor própria e o mapa está disponível.
  const d = extra => definicao({base: {todos: false, estados: ['13'], ids: []}, ...extra});
  const q = (def, familia = 'distribuicao', mapa = true) => M.precisaQuintisDoMapa(def, familia, mapa);
  assert.equal(q(d()), true);
  assert.equal(q(d(), 'espacial'), true);  // a distância nunca pinta o mapa (RQ-REP-02): os quintis do indicador
  assert.equal(q(d(), 'tendencia'), false);  // as classes já pintam
  assert.equal(q(d(), 'rotatividade'), false);  // a permanência já pinta
  assert.equal(q(d(), 'distribuicao', false), false);  // sem mapa (planilha sem coordenadas, visão Séries)
  assert.equal(q(d({nivel: 'estados'})), false);
  assert.equal(q(d({agrupar: {tipo: 'quartis', faixas: []}})), false);
  assert.equal(q(d({agrupar: {tipo: 'faixas', faixas: [1, 2]}})), false);
  assert.equal(q(d({agrupar: {tipo: 'faixas', faixas: [1]}})), true);  // faixas incompletas não pintam o gráfico
  assert.equal(q(d({condicoes: [{atributo: 'densidade', operador: '>', valor: 1}]})), false);
  assert.equal(q(d({ordenar: {atributo: 'densidade', ordem: 'desc'}})), false);
  const opcoes = M.montarOpcoes(d(), 'distribuicao', undefined, {quintisDoMapa: true});
  assert.deepEqual(opcoes.grupos_mapa, {tipo: 'quintis'});
  assert.equal(opcoes.grupos, undefined);  // o gráfico continua sem grupos
  assert.equal(M.montarOpcoes(d(), 'distribuicao').grupos_mapa, undefined);
  // Com os quintis do mapa, o indicador muda a resposta: a troca do indicador pede de novo; a troca da vista, não.
  assert.equal(M.pedidoDependeDoIndicador(opcoes), true);
  assert.equal(M.pedidoDependeDoIndicador(M.montarOpcoes(d(), 'distribuicao')), false);
  assert.notEqual(M.chaveDoPedido(opcoes), M.chaveDoPedido({...opcoes, indicador: 'quantidade'}));
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
  // Estado de antes de 23/10, sem vista nem cor: reabre sem os campos (a área mostra o gráfico).
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
  const estados = definicao({nivel: 'estados'});
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

test('nomes padronizados: a Seleção de Territórios primeiro, e as quatro análises com o nome completo', () => {
  assert.deepEqual(M.ABAS, ['territorios', 'distribuicao', 'espacial', 'tendencia', 'rotatividade']);
  assert.deepEqual(M.ABAS.map(M.nomeDaAba), ['Seleção de Territórios', 'Análise de Distribuição', 'Análise Espacial',
    'Análise de Tendência', 'Análise de Rotatividade']);
  assert.equal(M.NOME_SELECAO, 'Seleção de Territórios');  // a seleção não é uma análise
  assert.equal(M.TEXTO_DA_SELECAO, 'Selecione os territórios que deseja incluir em suas análises. Você poderá acrescentar ou retirar ' +
    'territórios a qualquer momento, e as análises serão atualizadas conforme a seleção realizada.');
  // A abertura não marca territórios: nada é pedido ao motor até a escolha.
  for (const tipo of ['brasil', 'arquivo']) {
    const inicial = M.definicaoInicial({tipo, periodos: ['202406'], categoria: '', temGrupos: tipo === 'brasil'});
    assert.equal(inicial.nivel, 'municipios');
    assert.deepEqual(inicial.base, {todos: false, estados: [], ids: []});
    assert.equal(M.bloqueioDoPedido(inicial, {fonte: tipo, rotulos: BR}), M.TEXTO_SEM_SELECAO);
  }
});

test('apresentação de cada aba: o que a aba faz, com os nomes territoriais da fonte e sem códigos internos', () => {
  const brasil = aba => M.apresentacaoDaAba(aba, {rotulos: BR, brasil: true, comGrupos: true});
  const planilha = aba => M.apresentacaoDaAba(aba, {rotulos: DISTRITOS, brasil: false, comGrupos: true});
  const tudo = a => [a.titulo, ...a.paragrafos, ...(a.itens || []).flatMap(item => [item.termo, item.texto]), a.nota || ''].join(' ');
  for (const aba of M.ABAS) {
    assert.equal(brasil(aba).titulo, M.nomeDaAba(aba));
    assert.ok(brasil(aba).paragrafos.length >= 1);
    const texto = tudo(planilha(aba));
    assert.ok(!/município|estado|Brasil/i.test(texto), aba + ': ' + texto);  // a planilha fala de distritos e províncias
    // Sem códigos do motor na tela, a não ser a âncora do método na nota da tendência.
    assert.ok(!/[A-Z]{3,}_[A-Z]/.test(texto.replace('CAP-TEN-01 (DA-15)', '')), aba + ': ' + texto);
  }
  assert.equal(brasil('territorios').paragrafos[0], M.TEXTO_DA_SELECAO);
  assert.ok(brasil('territorios').paragrafos[1].includes('os municípios de um estado de uma vez'));
  assert.ok(planilha('territorios').paragrafos[1].includes('os distritos de uma província de uma vez'));
  // Antes dos dados, sem falar de planilha nem do Brasil.
  const antes = M.apresentacaoDaAba('territorios', {rotulos: M.ROTULOS_GENERICOS, brasil: false, comGrupos: false, semDados: true});
  assert.ok(antes.paragrafos[1].startsWith('Depois de escolher os dados, a lista de territórios aparece aqui.'), antes.paragrafos[1]);
  assert.ok(brasil('distribuicao').paragrafos[1].includes('5 grupos iguais (quintis)'));
  assert.ok(brasil('espacial').paragrafos[1].includes('(a sede municipal)'));
  assert.ok(!planilha('espacial').paragrafos[1].includes('sede'));
  assert.ok(brasil('rotatividade').paragrafos[1].includes('envie uma planilha com o identificador individual'));
  assert.ok(!planilha('rotatividade').paragrafos[1].includes('envie'));
  // As classes da tendência, na ordem da SPEC, com o que cada uma quer dizer, e o não avaliável.
  const tendencia = brasil('tendencia');
  assert.deepEqual(tendencia.itens.map(item => item.termo), ['Crescimento', 'Aceleração do crescimento', 'Desaceleração do crescimento',
    'Declínio', 'Aceleração do declínio', 'Desaceleração do declínio', 'Sem classificação', 'Não avaliável']);
  assert.ok(tendencia.itens.every(item => item.texto && item.texto.endsWith('.')));
  assert.ok(tendencia.paragrafos[0].includes('pelo menos quatro observações válidas'));
  assert.ok(tendencia.nota.includes('Basta um trecho na direção contrária'));
  assert.ok(tendencia.nota.endsWith('Método de classificação: CAP-TEN-01 (DA-15).'));
  assert.deepEqual(Object.keys(M.DESCRICAO_DAS_CLASSES), M.CLASSES_TENDENCIA.map(classe => classe.codigo));
});

test('tendência: o motivo de cada unidade em palavras, sem o código; a nota das sem classificação conta pelo motor e explica a regra', () => {
  const t = extra => ({classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: null, motivoCodigo: null,
    motivoTexto: null, avaliavel: true, observacoes: 22, velocidades: [], ...extra});
  assert.equal(M.explicacaoDaTendencia(t({motivoCodigo: 'MUDANCA_DE_DIRECAO', motivoTexto: 'Mudança de direção'})),
    'Sem classificação: na janela, o indicador subiu em alguns trechos e caiu em outros (mudança de direção).');
  assert.equal(M.explicacaoDaTendencia(t({motivoCodigo: 'SERIE_ESTAVEL'})),
    'Sem classificação: o indicador não variou em nenhum trecho da janela (série estável).');
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: null, motivoCodigo: 'SERIE_INSUFICIENTE',
    motivoTexto: '3 de 4 observações necessárias'})), 'Não avaliável: série insuficiente na janela (3 de 4 observações necessárias).');
  // Sem o código nem o texto do motivo (uma resposta de antes), vale o rótulo do motor, que já diz o motivo.
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: 'Não avaliável: série insuficiente'})),
    'Não avaliável: série insuficiente');
  assert.equal(M.explicacaoDaTendencia(t({avaliavel: false, classe: null, rotulo: 'Não avaliável'})), 'Não avaliável.');
  assert.equal(M.explicacaoDaTendencia(t({motivo: 'Mudança de direção (MUDANCA_DE_DIRECAO)'})), 'Sem classificação: mudança de direção.');
  assert.equal(M.explicacaoDaTendencia(t({classe: 'CRESCIMENTO_ACELERADO', familia: 'CRESCIMENTO', rotulo: 'Aceleração do crescimento'})),
    'Aceleração do crescimento: ' + M.DESCRICAO_DAS_CLASSES.CRESCIMENTO_ACELERADO);
  assert.equal(M.explicacaoDaTendencia(null), null);
  for (const caso of [t({motivoCodigo: 'MUDANCA_DE_DIRECAO'}), t({motivoCodigo: 'SERIE_ESTAVEL'})])
    assert.ok(!/MUDANCA_DE_DIRECAO|SERIE_ESTAVEL/.test(M.explicacaoDaTendencia(caso)));
  const topo = (contagens, porMotivo) => ({contagens, semClassificacaoPorMotivo: porMotivo});
  // Todas as unidades sem classe (o cenário real das 22 competências): a contagem por motivo e a explicação da regra.
  const real = M.notaSemClassificacao(topo({SEM_CLASSIFICACAO: 62}, {MUDANCA_DE_DIRECAO: 62}), {rotulos: BR, brasil: true});
  assert.ok(real.startsWith('Sem classificação: 62 municípios por mudança de direção'), real);
  assert.ok(real.includes('Nenhum município recebeu classe nesta janela'));
  assert.ok(real.includes('uma única mudança de direção basta'));
  assert.ok(real.includes('como os últimos 4 junhos'));
  assert.ok(real.endsWith('Isso é o resultado do método, não falta de dados.'));
  // Com unidades classificadas, só a contagem por motivo.
  assert.equal(M.notaSemClassificacao(topo({CRESCIMENTO: 17, SEM_CLASSIFICACAO: 38}, {MUDANCA_DE_DIRECAO: 37, SERIE_ESTAVEL: 1}),
    {rotulos: BR, brasil: true}), 'Sem classificação: 37 municípios por mudança de direção (o indicador subiu em alguns trechos e ' +
    'caiu em outros); 1 município por série estável (o indicador não variou).');
  assert.equal(M.notaSemClassificacao(topo({CRESCIMENTO: 5}, {}), {rotulos: BR, brasil: true}), null);
  assert.equal(M.notaSemClassificacao(null, {rotulos: BR, brasil: true}), null);
  const distritos = M.notaSemClassificacao(topo({SEM_CLASSIFICACAO: 3}, {MUDANCA_DE_DIRECAO: 3}), {rotulos: DISTRITOS, brasil: false});
  assert.ok(distritos.includes('Nenhum distrito recebeu classe') && !distritos.includes('junhos'), distritos);
  // A resposta do motor chega com o motivo separado do código e a contagem por motivo.
  const r = A.normalizarResposta({competencia: '202406', categoria: 'MEDICINA', itens: [{id: 'code:1', tipo: 'municipio', rotulo: 'A (AM)',
    tendencia: {classe: 'SEM_CLASSIFICACAO', familia: 'NENHUMA', rotulo: 'Sem classificação', motivo: 'MUDANCA_DE_DIRECAO',
      motivo_texto: 'Mudança de direção', avaliavel: true, observacoes: 22, velocidades: []}}],
    tendencia: {competencias: ['202306', '202406'], contagens: {SEM_CLASSIFICACAO: 1}, sem_classificacao_por_motivo: {MUDANCA_DE_DIRECAO: 1}}});
  assert.equal(r.itens[0].tendencia.motivoCodigo, 'MUDANCA_DE_DIRECAO');
  assert.equal(r.tendencia.semClassificacaoPorMotivo.MUDANCA_DE_DIRECAO, 1);
});

test('planilha com a coluna-mãe: os grupos da Seleção vêm do catálogo do pré-exame (a província de cada distrito)', () => {
  const unidade = (id, nome, provincia) => ({id, name: nome, code: '', label: nome, state: '', state_name: '', state_code: '',
    parents: provincia ? [provincia] : []});
  const catalogo = [unidade('name:Alfa', 'Alfa', 'Norte'), unidade('name:Beta', 'Beta', 'Norte'), unidade('name:Gama', 'Gama', 'Sul'),
    unidade('name:Delta', 'Delta', 'Sul')];
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo).map(grupo => [grupo.id, grupo.nome, grupo.unidades]), [['Norte', 'Norte', 2],
    ['Sul', 'Sul', 2]]);
  assert.equal(M.grupoDaUnidade(catalogo[2]), 'Sul');
  // Sem a coluna-mãe, a lista fica sem grupos; na base do Brasil, o estado pelo código IBGE continua valendo.
  assert.deepEqual(M.gruposDaFonte(undefined, catalogo.map(item => ({...item, parents: []}))), []);
  assert.equal(M.grupoDaUnidade({...catalogo[0], state: 'AM', state_code: '13', parents: ['Amazonas']}), '13');
  // A província marcada inteira vai ao motor pelo valor dela, e os distritos dela saem da lista solta.
  assert.deepEqual(M.normalizarBase({todos: false, estados: ['Sul'], ids: ['name:Gama', 'name:Alfa']}, id =>
    M.grupoDaUnidade(catalogo.find(item => item.id === id))), {todos: false, estados: ['Sul'], ids: ['name:Alfa']});
});
