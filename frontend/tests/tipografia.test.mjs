import {existsSync, readFileSync, readdirSync} from 'node:fs';
import {test} from 'node:test';
import assert from 'node:assert/strict';

// Tipografia (28/10/2026, pedido do responsável: a marca e as letras pequenas, em todas as camadas, sem latência nova). Confere a
// Inter embutida no próprio app (nenhuma requisição externa), a escala com o piso de tamanho nas folhas de estilo e nas classes do
// Tailwind, a marca ("da Força de Trabalho na Saúde" maior que antes e menor que o nome do agente) e os textos de apoio da conversa.
const ler = arquivo => readFileSync(new URL('../' + arquivo, import.meta.url), 'utf8');
const semComentarios = texto => texto.replace(/\/\*[\s\S]*?\*\//g, '');
const FOLHAS = ['src/styles.css', 'src/analise.css', 'src/mapa.css'];
const CSS = Object.fromEntries(FOLHAS.map(folha => [folha, semComentarios(ler(folha))]));
const TAILWIND = (await import(new URL('../tailwind.config.js', import.meta.url).href)).default;

/** As regras de uma folha como [seletor, corpo], fora dos @media (o corpo de cada regra aninhada vem com o seletor dela). */
function regras(css) {
  const saida = [];
  for (const [, seletor, corpo] of css.matchAll(/([^{}]+)\{([^{}]*)\}/g)) saida.push([seletor.trim(), corpo]);
  return saida;
}
const tamanho = corpo => { const achado = /font-size:\s*([0-9.]+)px/.exec(corpo); return achado ? Number(achado[1]) : null; };
const regra = (folha, seletor) => regras(CSS[folha]).find(([s]) => s === seletor)?.[1] ?? '';

test('a Inter vem embutida no app: @font-face local, sem requisição externa, com a licença OFL', () => {
  const faces = [...CSS['src/styles.css'].matchAll(/@font-face\s*\{([^}]*)\}/g)].map(([, corpo]) => corpo);
  assert.equal(faces.length, 2, 'os subconjuntos latino e latino estendido');
  for (const corpo of faces) {
    assert.match(corpo, /font-family:\s*"Inter Variable"/);
    assert.match(corpo, /font-display:\s*swap/, 'o texto aparece na hora, sem esperar a fonte');
    assert.match(corpo, /font-weight:\s*100 900/, 'a fonte variável cobre os pesos usados (650, 750)');
    const arquivo = /url\("\.\/(tipografia\/[^"]+\.woff2)"\)/.exec(corpo)?.[1];
    assert.ok(arquivo, 'a fonte vem de um arquivo do próprio app');
    const bytes = readFileSync(new URL('../src/' + arquivo, import.meta.url));
    assert.equal(bytes.subarray(0, 4).toString('latin1'), 'wOF2', arquivo + ' é um WOFF2');
    assert.ok(bytes.length < 150_000, arquivo + ': subconjunto leve');
  }
  assert.ok(existsSync(new URL('../src/tipografia/LICENCA-OFL.txt', import.meta.url)), 'a licença OFL acompanha a fonte');
  assert.match(ler('src/tipografia/LICENCA-OFL.txt'), /SIL Open Font License, Version 1\.1/);
  // Nenhuma folha nem a página pedem algo fora do app (fontes, CDNs): os testes de navegador bloqueiam a rede externa.
  for (const arquivo of [...FOLHAS, 'index.html']) assert.doesNotMatch(ler(arquivo), /url\(\s*["']?https?:|<link[^>]+https?:|@import\s+url\(/i, arquivo);
  assert.deepEqual(readdirSync(new URL('../src/tipografia/', import.meta.url)).filter(nome => nome.endsWith('.woff2')).sort(),
    ['inter-latin-ext-opsz-normal.woff2', 'inter-latin-opsz-normal.woff2']);
  // A família da página e a do Tailwind começam pela Inter embutida, com a do sistema como reserva.
  const raiz = regras(CSS['src/styles.css']).find(([seletor, corpo]) => seletor === ':root' && /font-family/.test(corpo))?.[1] ?? '';
  assert.match(raiz.replace(/\s+/g, ' '), /font-family: "Inter Variable", Inter, ui-sans-serif, system-ui/);
  assert.deepEqual(TAILWIND.theme.extend.fontFamily.sans.slice(0, 2), ['Inter Variable', 'Inter']);
});

test('escala com piso: nenhuma letra abaixo de 11 px; abaixo de 12 px, só rótulos em caixa alta e números de eixo', () => {
  const abaixo = [];
  for (const [folha, css] of Object.entries(CSS)) {
    for (const [seletor, corpo] of regras(css)) {
      for (const [, valor] of corpo.matchAll(/font-size:\s*([0-9.]+)px/g)) {
        const px = Number(valor);
        assert.ok(px >= 11, folha + ': ' + seletor + ' com ' + px + ' px');
        if (px < 12) abaixo.push([seletor.replace(/\s+/g, ' '), /text-transform:\s*uppercase|font-variant-numeric:\s*tabular-nums/.test(corpo)]);
      }
    }
  }
  // A versão do celular do sobretítulo do banner herda a caixa alta da regra principal.
  assert.deepEqual(abaixo.filter(([seletor, micro]) => !micro && seletor !== '.hero-eyebrow'), []);
  // A escala usa só inteiros (12, 13, 14, 15…), salvo os rótulos do desenho (12,5 px, com a largura estimada) e os micro (11,5 px).
  const meios = Object.entries(CSS).flatMap(([folha, css]) => regras(css).flatMap(([seletor, corpo]) =>
    [...corpo.matchAll(/font-size:\s*([0-9.]+)px/g)].map(([, px]) => Number(px)).filter(px => !Number.isInteger(px) && px !== 11.5)
      .map(px => folha + ' ' + seletor.replace(/\s+/g, ' ') + ' ' + px)));
  assert.deepEqual(meios.filter(item => !/\.(analise|painel)-(rotulo|eixo-titulo)\b/.test(item)), []);
  // O que era miúdo subiu (antes: 10 a 11,5 px).
  assert.equal(tamanho(regra('src/styles.css', '.hero-eyebrow')), 11.5);
  assert.equal(tamanho(regra('src/styles.css', '.fonte-diagnostico')), 12);
  assert.equal(tamanho(regra('src/styles.css', '.colunas-campo small')), 12);
  assert.equal(tamanho(regra('src/analise.css', '.territorios-apoio')), 12);
  assert.equal(tamanho(regra('src/analise.css', '.analise-nota')), 12);
  assert.equal(tamanho(regra('src/analise.css', '.analise-legenda')), 12);
  assert.equal(tamanho(regra('src/analise.css', '.analise-rotulo-campo')), 13, 'os rótulos dos campos (antes, 11,5 px)');
  assert.match(regra('src/analise.css', '.analise-rotulo-campo'), /font-weight:\s*600/, 'a hierarquia vem do peso');
  assert.equal(tamanho(regra('src/analise.css', '.analise-frase-resumo')), 15, 'a frase-resumo do motor, texto de leitura');
  // Com a letra maior, os campos dos ajustes na altura do seletor segmentado (40 px) e, na gaveta Condições, o Indicador na linha
  // toda e a Condição e o Valor na seguinte: nenhum campo corta o texto.
  assert.match(regra('src/analise.css', '.analise-ajustes .analise-campo'), /min-height:\s*40px/);
  const gavetas = ler('src/PainelGavetas.tsx');
  assert.match(gavetas, /<label className="analise-rotulo-campo basis-full">Indicador/);
  assert.match(gavetas, /<label className="analise-rotulo-campo min-w-\[7rem\] flex-1">Condição/);
  assert.match(gavetas, /<label className="analise-rotulo-campo min-w-\[7rem\] flex-1">Valor/);
  // Os números dos eixos e da rampa do mapa não crescem além de 11,5 px: a margem do eixo e o afastamento dos rótulos são fixos.
  assert.equal(tamanho(regra('src/mapa.css', '.mapa-rampa-textos')), 11.5);
  assert.match(regra('src/mapa.css', '.mapa-rampa-textos'), /height:\s*16px/, 'a caixa da rampa cabe a letra');
  // Tailwind: o text-xs dos textos de apoio é 13 px, e nenhuma classe de tamanho arbitrário fica abaixo de 12 px.
  assert.deepEqual(TAILWIND.theme.extend.fontSize.xs, ['13px', {lineHeight: '18px'}]);
  for (const arquivo of readdirSync(new URL('../src/', import.meta.url)).filter(nome => nome.endsWith('.tsx'))) {
    const pequenos = [...ler('src/' + arquivo).matchAll(/text-\[([0-9.]+)px\]/g)].map(([, px]) => Number(px)).filter(px => px < 12);
    assert.deepEqual(pequenos, [], arquivo + ': classes de tamanho abaixo de 12 px');
  }
});

test('a marca: "da Força de Trabalho na Saúde" maior que antes e menor que o nome do agente, no turquesa da identidade', () => {
  const nome = regra('src/styles.css', '.pagina-marca strong'), subtitulo = regra('src/styles.css', '.pagina-marca small');
  assert.equal(tamanho(nome), 20);
  assert.equal(tamanho(subtitulo), 14, 'antes, 12 px');
  assert.ok(tamanho(subtitulo) < tamanho(nome));
  assert.match(subtitulo, /color:\s*var\(--cor-destaque-texto\)/, 'o turquesa de texto, a 4,5:1 ou mais nos dois esquemas');
  assert.match(subtitulo, /font-weight:\s*600/);
  assert.match(regra('src/styles.css', '.pagina-marca-de'), /font-weight:\s*450/, 'o "da" mais leve');
  assert.match(ler('src/App.tsx'), /<small><span className="pagina-marca-de">da<\/span> Força de Trabalho na Saúde<\/small>/);
  // No celular, a mesma relação, menor.
  const celular = CSS['src/styles.css'].slice(CSS['src/styles.css'].indexOf('@media (max-width: 639px)'));
  assert.match(celular, /\.pagina-marca strong \{ font-size: 17px; \}\s*\.pagina-marca small \{ font-size: 13px; \}/);
});

test('a conversa: a letra das mensagens continua (15 px; 14 no celular) e os textos de apoio sobem', () => {
  const estilos = CSS['src/styles.css'];
  assert.match(estilos, /\.chat-mensagem \{[^}]*font-size:15px/);
  assert.match(estilos, /@media \(max-width:639px\) \{(?:\s*[^{}]+\{[^{}]*\})*?\s*\.chat-mensagem \{ font-size:14px; \}/);
  assert.equal(tamanho(regra('src/styles.css', '.chat-estado-servico')), 13, 'o aviso do serviço (antes, 11 px)');
  assert.equal(tamanho(regra('src/styles.css', '.conversation-composer details')), 12, '"Privacidade da conversa" (antes, 10 px)');
  assert.equal(tamanho(regra('src/styles.css', '.chat-ir-ao-fim')), 12);
  assert.match(estilos, /\[data-hora\]::after \{[^}]*font-size:12px[^}]*font-variant-numeric:tabular-nums/, 'a hora no balão (antes, 11 px)');
  // O balão do agente mostra a resposta inteira, na letra das mensagens: as regras da antiga "última resposta" (corte em 140 px,
  // rolagem dentro do balão, letra menor que a da pessoa) não valem nele.
  assert.match(regra('src/styles.css', '.chat-balao-agente.latest-reply'), /display:block;\s*font-size:inherit;\s*line-height:inherit/);
  assert.match(regra('src/styles.css', '.chat-balao-agente.latest-reply > div'), /max-height:none;\s*overflow:visible/);
  assert.match(estilos, /\.chat-estado-servico \{ font-size:12px; \}/, 'o aviso no celular');
  assert.match(estilos, /\.conversation-composer textarea \{ font-size: 16px; \}/, 'no celular, 16 px: sem zoom ao focar o campo');
  const caixa = ler('src/ChatFloatingBox.tsx'), assistente = ler('src/AnalysisAssistant.tsx');
  assert.match(caixa, /text-\[15px\] font-bold[^"]*">Agente Diagnóstico Territorial/, 'o nome do agente no cabeçalho da caixa (antes, 14 px)');
  assert.match(caixa, /text-\[12px\] text-slate-600">\{ocupado/, 'a linha de apoio do cabeçalho (antes, 11 px, em slate-500)');
  assert.match(assistente, /text-\[12px\] text-slate-500">Enter para enviar/);
  assert.match(assistente, /text-\[15px\] leading-6 text-ink focus:outline-none/, 'o campo de mensagem na letra das mensagens');
});

test('rótulos do desenho: o tamanho da folha e a largura estimada para afastar os rótulos andam juntos', async () => {
  const ts = (await import('typescript')).default;
  const codigo = ts.transpileModule(ler('src/painelModel.ts'), {compilerOptions: {module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022}}).outputText;
  const M = await import('data:text/javascript;base64,' + Buffer.from(codigo).toString('base64'));
  const rotulo = tamanho(regra('src/analise.css', '.analise-rotulo'));
  assert.equal(rotulo, 12.5);
  assert.equal(M.larguraDoTexto('Manaus'), Math.ceil(6 * rotulo * 0.56) + 4, 'a estimativa usa o tamanho do rótulo');
  assert.equal(tamanho(regra('src/analise.css', '.analise-marca-texto')), 11.5);
  assert.match(ler('src/PainelSeries.tsx'), /larguraDoTexto\(serie\.rotulo, 12\)/, 'os rótulos das séries usam o tamanho das marcas');
  assert.match(ler('src/MapaAnalise.tsx'), /const FONTE_NOME = "600 12px \\"Inter Variable\\", Inter/, 'os nomes no mapa, na Inter embutida, sem crescer');
  assert.match(ler('src/MapaAnalise.tsx'), /document\.fonts\?\.ready\.then\(\(\) => \{ if \(vivo\) \{ larguras\.current\.clear\(\); agendar\(\); \} \}\)/,
    'com a fonte carregada, as larguras dos nomes são medidas de novo');
});

test('contraste no claro dos textos pequenos: o turquesa e o cinza de texto a 4,5:1 ou mais', () => {
  const css = CSS['src/styles.css'];
  const claro = css.slice(css.indexOf(':root {'), css.indexOf('@media screen and (prefers-color-scheme: dark)'));
  const escuro = css.slice(css.indexOf('@media screen and (prefers-color-scheme: dark)'));
  const valor = (bloco, nome) => new RegExp(nome + ':\\s*([^;]+);').exec(bloco)?.[1].trim();
  const hex = canaisOuHex => canaisOuHex.startsWith('#') ? canaisOuHex
    : '#' + canaisOuHex.split(/\s+/).map(c => Number(c).toString(16).padStart(2, '0')).join('');
  const linear = c => { c /= 255; return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
  const luz = cor => { const v = parseInt(cor.slice(1), 16); const [r, g, b] = [(v >> 16) & 255, (v >> 8) & 255, v & 255].map(linear);
    return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const contraste = (a, b) => { const [x, y] = [luz(a), luz(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const pagina = hex(valor(claro, '--tom-canvas')), branco = hex(valor(claro, '--tom-white'));
  for (const nome of ['--cor-texto-3', '--cor-destaque-texto', '--cor-texto-apoio'])
    for (const fundo of [pagina, branco]) assert.ok(contraste(hex(valor(claro, nome)), fundo) >= 4.5, nome + ' sobre ' + fundo);
  assert.equal(valor(claro, '--cor-texto-3'), '#587080', 'antes, #6b8494 (3,9:1 no branco)');
  // O turquesa de texto do Tailwind é o mesmo das folhas, nos dois esquemas; o da identidade (teal) continua nas bordas e fundos.
  assert.equal(hex(valor(claro, '--tom-teal-texto')), valor(claro, '--cor-destaque-texto'));
  assert.equal(hex(valor(escuro, '--tom-teal-texto')), valor(escuro, '--cor-destaque-texto'));
  assert.equal(TAILWIND.theme.extend.colors.teal.texto, 'rgb(var(--tom-teal-texto) / <alpha-value>)');
  for (const arquivo of readdirSync(new URL('../src/', import.meta.url)).filter(nome => nome.endsWith('.tsx')))
    assert.doesNotMatch(ler('src/' + arquivo), /\btext-teal(?!-)/, arquivo + ': texto turquesa no tom de texto');
  for (const [folha, seletor] of [['src/styles.css', '.pagina-aviso'], ['src/analise.css', '.analise-status']])
    assert.match(regra(folha, seletor), /color:\s*var\(--cor-destaque-texto\)/, seletor);
  assert.match(regra('src/styles.css', '.pagina-rodape'), /color:\s*var\(--cor-texto-apoio\)/, 'o rodapé (antes, slate-400 a 2,4:1)');
  assert.match(regra('src/styles.css', '::placeholder'), /color:\s*var\(--cor-texto-3\);\s*opacity:\s*1/, 'o texto de exemplo dos campos');
  // Sem a suavização que afina o texto escuro pequeno no Mac.
  assert.doesNotMatch(css, /font-smoothing/);
});
