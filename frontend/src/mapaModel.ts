// Mapa da página única (23/10/2026): modelo puro do desenho. Projeta as coordenadas autorizadas do motor só para desenhar,
// enquadra, dimensiona (área proporcional), pinta (cor contínua linear ou, só por escolha da pessoa, logarítmica), monta as
// marcas da legenda, posiciona os nomes, acha o ponto sob o ponteiro e interpola a transição entre as vistas. Nada aqui
// classifica, cria quantil, faixa, contagem, posição ou distância (SPEC, Parte 13; RQ-REP-02 e RQ-REP-09): as classes e os
// valores chegam prontos do motor, pelas funções da área. Sem importações em tempo de execução (os testes em Node transpilam
// este arquivo sozinho): só tipos.
import type { EsquemaDeCor } from "./esquemaDeCor";
import type { PinturaDoMapa, Posicoes } from "./mapaContrato";
import type { PainelItem } from "./painelApi";
import type { Pintura } from "./painelModel";

const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
const finito = (valor: unknown): valor is number => typeof valor === "number" && Number.isFinite(valor);
const entre01 = (t: number) => Math.min(1, Math.max(0, t));

// ================================================================================================ cores e medidas
/** Cores e superfícies do mapa e do mapinha (modo claro), da paleta validada pela skill de visualização (superfície #fcfcfb,
 * tintas #0b0b0b e #52514e, grade #e1e0d9, eixo #c3c2b7) e da identidade da aplicação nos controles. O componente passa estas
 * cores ao canvas e, como variáveis CSS (--mapa-*), a mapa.css: o modo escuro troca só este objeto (MAPA_CORES_ESCURO, pela
 * coresDoMapa). */
export const MAPA_CORES = {
  /** Superfície do desenho (a mesma do gráfico) e anel fino dos pontos. */
  superficie: "#fcfcfb",
  /** Seleção, mira da referência, anel do conjunto e nomes. */
  tinta: "#0b0b0b",
  /** Ligações ilustrativas e textos de apoio. */
  tinta2: "#52514e",
  /** Textos leves (marcas da legenda). */
  muda: "#898781",
  /** Anel tracejado do valor não avaliável (o COR_NAO_AVALIAVEL do gráfico). */
  naoAvaliavel: "#898781",
  /** Pontos sem camada de cor (a análise sem cores próprias e sem os quintis do motor): a cor única do gráfico (COR_BOLHA),
   * que não codifica nada. */
  neutro: "#008b9e",
  /** Demais unidades da fonte, ao fundo (o formato do Brasil). */
  fundo: "#d9d8d1",
  /** Itens fora da régua ou dos filtros: bem claros, no lugar, sem interação. */
  esmaecido: "#e1e0d9",
  esmaecidoBorda: "#d9d8d1",
  /** Pontos do mapinha. */
  miniPontos: "#c3c2b7",
  /** Contorno de foco pelo teclado (o mesmo da página). */
  foco: "#3bb5be",
  /** Linhas finas da legenda. */
  eixo: "#c3c2b7",
  borda: "#dfe7ed",
  /** Controles, cartões e dica (identidade da aplicação). */
  painel: "#ffffff",
  controleTexto: "#0e2840",
  controleBorda: "#c9d8e2",
  controleRealce: "#eef7f8",
  destaqueTexto: "#0c6b74",
  destaqueFundo: "#effafb",
  textoApoio: "#52606d",
  sombra: "rgba(9, 37, 60, 0.12)",
} as const;
export type CoresDoMapa = { [chave in keyof typeof MAPA_CORES]: string };

/** Modo escuro (23/10/2026): as mesmas chaves, para a superfície escura do gráfico (#1a1a19). Superfície e tintas da tabela
 * "Chart chrome & ink" da skill (#f0efec a 15,2:1, #c3c2b7 a 9,7:1, muda #898781 a 4,85:1, eixo #383835); o ponto neutro é a
 * série única do escuro (#1ba3b5, PASS no validador); fundo (#383835, 1,48:1), esmaecidos (#2c2c2a com borda #383835) e pontos do
 * mapinha (#45443f, 1,78:1) ficam tão recessivos quanto no claro (1,39:1, 1,29:1 e 1,75:1); controles, cartões e dica nas
 * superfícies elevadas e nas tintas da página (styles.css), com os textos acima de 4,5:1. */
export const MAPA_CORES_ESCURO: CoresDoMapa = {
  superficie: "#1a1a19",
  tinta: "#f0efec",
  tinta2: "#c3c2b7",
  muda: "#898781",
  naoAvaliavel: "#898781",
  neutro: "#1ba3b5",
  fundo: "#383835",
  esmaecido: "#2c2c2a",
  esmaecidoBorda: "#383835",
  miniPontos: "#45443f",
  foco: "#3bb5be",
  eixo: "#383835",
  borda: "#2e2e2b",
  painel: "#232321",
  controleTexto: "#e6e5df",
  controleBorda: "#45453f",
  controleRealce: "#142d2e",
  destaqueTexto: "#6fcbd2",
  destaqueFundo: "#142d2e",
  textoApoio: "#c3c2b7",
  sombra: "rgba(0, 0, 0, 0.5)",
};
/** As cores do mapa no esquema de cor em uso (useEsquemaDeCor). */
export const coresDoMapa = (esquema: EsquemaDeCor): CoresDoMapa => esquema === "escuro" ? MAPA_CORES_ESCURO : MAPA_CORES;

/** Rampa sequencial de um tom (azul, claro → escuro; passos 250, 350, 450, 550 e 650 da paleta), conferida pelo validador da
 * skill (`--ordinal`, modo claro: L monótono, passos ≥ 0,06, ponta clara a 2,06:1 da superfície, um só matiz). Com pontos
 * pequenos sobre a superfície, a ponta clara não pode sumir. É a mesma família dos grupos e faixas do gráfico. */
export const RAMPA_CONTINUA = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"] as const;
/** No escuro, a âncora vira: do escuro (menor valor) ao claro (maior), passos 600, 500, 400, 300 e 200, sem ir além do 600 na
 * ponta junto da superfície. Validador (`--ordinal --mode dark --surface "#1a1a19"`): L monótono, passos ≥ 0,06, ponta escura a
 * 2,15:1 da superfície e um só matiz (3°): PASS. É a rampa dos grupos e faixas do escuro, com 5 tons. */
export const RAMPA_CONTINUA_ESCURA = ["#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"] as const;
/** A rampa contínua no esquema de cor em uso. */
export const rampaContinua = (esquema: EsquemaDeCor): readonly string[] => esquema === "escuro" ? RAMPA_CONTINUA_ESCURA : RAMPA_CONTINUA;

/** Raio máximo (área proporcional) na vista inicial: menor que o do gráfico, para os pontos não cobrirem o território. */
export const RAIO_MAXIMO_MAPA = 16;
/** Raio mínimo visível: valores muito pequenos (ou sem valor de tamanho) ficam nele. */
export const RAIO_MINIMO_MAPA = 2.5;
/** Meio lado do quadradinho das unidades de fundo. */
export const RAIO_FUNDO = 1.25;
/** Opacidade das pinturas apagadas (não atende, fora dos primeiros): mais claras, como no gráfico. */
export const OPACIDADE_APAGADA = 0.5;
/** Alvo do clique, maior que o ponto (px): mouse e toque. */
export const ALVO_MOUSE = 12;
export const ALVO_TOQUE = 18;
/** Ligações ilustrativas: só dos selecionados, no máximo 30. */
export const MAX_LIGACOES = 30;
/** Com até este número de pontos à vista no resultado, todos ganham o nome. */
export const LIMITE_NOMES_TODOS = 12;
/** Folga do enquadramento (px), maior que o raio máximo. */
export const FOLGA_ENQUADRAMENTO = 32;
/** Vão mínimo do enquadramento (graus): um ponto só, ou pontos muito próximos, não viram um zoom extremo. */
export const VAO_MINIMO = 1.5;
/** Acima deste número de pontos em uma das vistas, a troca entre o gráfico e o mapa é direta, sem animação. */
export const LIMITE_TRANSICAO = 1500;

// ================================================================================================ projeção (só para desenhar)
export type Projecao = {
  ids: string[];
  /** Longitude × cosseno da latitude média (graus) e −latitude: equirretangular, só para o desenho. */
  x: Float64Array;
  y: Float64Array;
  k: number;
  indice: Map<string, number>;
};
export const coordenadaValida = (lat: unknown, lon: unknown) =>
  finito(lat) && finito(lon) && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;

/** Projeção equirretangular (longitude × cos da latitude média; y = −latitude). Serve só para posicionar no desenho: nenhuma
 * distância é medida no mapa (as distâncias vêm do motor, geodésicas). Coordenadas inválidas ficam de fora. */
export function projetar(pontos: Map<string, [number, number]>): Projecao {
  const validos: [string, number, number][] = [];
  let menor = Infinity, maior = -Infinity;
  for (const [id, coordenada] of pontos) {
    const [lat, lon] = coordenada || [];
    if (!coordenadaValida(lat, lon)) continue;
    validos.push([id, lat, lon]);
    menor = Math.min(menor, lat); maior = Math.max(maior, lat);
  }
  const k = validos.length ? Math.max(0.05, Math.cos(((menor + maior) / 2) * Math.PI / 180)) : 1;
  const x = new Float64Array(validos.length), y = new Float64Array(validos.length);
  const ids: string[] = [], indice = new Map<string, number>();
  validos.forEach(([id, lat, lon], i) => { ids.push(id); x[i] = lon * k; y[i] = -lat; indice.set(id, i); });
  return { ids, x, y, k, indice };
}

export type Limites = { minX: number; maxX: number; minY: number; maxY: number };
/** Retângulo que contém os pontos indicados (índices da projeção); null sem pontos. */
export function limitesDe(projecao: Pick<Projecao, "x" | "y">, indices: Iterable<number>): Limites | null {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const i of indices) {
    const x = projecao.x[i], y = projecao.y[i];
    if (!finito(x) || !finito(y)) continue;
    if (x < minX) minX = x; if (x > maxX) maxX = x;
    if (y < minY) minY = y; if (y > maxY) maxY = y;
  }
  return Number.isFinite(minX) ? { minX, maxX, minY, maxY } : null;
}

/** Vista: centro no mundo projetado e escala em pixels por unidade do mundo (≈ por grau). */
export type Vista = { cx: number; cy: number; escala: number };
/** Enquadramento: os pontos cabem na área com a folga; vão mínimo para um ponto só. Sem pontos, uma vista neutra. */
export function enquadrar(limites: Limites | null, largura: number, altura: number, folga = FOLGA_ENQUADRAMENTO, vaoMinimo = VAO_MINIMO): Vista {
  if (!limites) return { cx: 0, cy: 0, escala: 1 };
  const vaoX = Math.max(limites.maxX - limites.minX, vaoMinimo), vaoY = Math.max(limites.maxY - limites.minY, vaoMinimo);
  const utilX = Math.max(largura - 2 * folga, 40), utilY = Math.max(altura - 2 * folga, 40);
  return { cx: (limites.minX + limites.maxX) / 2, cy: (limites.minY + limites.maxY) / 2, escala: Math.max(1e-6, Math.min(utilX / vaoX, utilY / vaoY)) };
}

/** Enquadramento inicial com contexto (23/10/2026): o retângulo dos itens ganha uma margem em volta e não fica menor que uma fração
 * da extensão de todos os pontos da fonte (o desenho do país, ou da planilha, ao fundo), para o mapa abrir com a geografia
 * reconhecível em volta dos pontos, e não só com bolhas ampliadas; nunca passa da extensão de todos os pontos (com todos os
 * pontos escolhidos, a vista é a de sempre: a fonte inteira). Vale para qualquer fonte com coordenadas: nenhuma escala fixa do
 * Brasil. Depois de aberto, o zoom é livre. */
export const MARGEM_DE_CONTEXTO = 0.25;
export const CONTEXTO_MINIMO = 0.25;
export function limitesComContexto(itens: Limites | null, todos: Limites | null, margem = MARGEM_DE_CONTEXTO,
  minimo = CONTEXTO_MINIMO): Limites | null {
  if (!itens) return todos;
  if (!todos) return itens;
  const totalX = todos.maxX - todos.minX, totalY = todos.maxY - todos.minY;
  const limite = (vao: number, total: number) => Math.min(Math.max(vao * (1 + 2 * margem), total * minimo), Math.max(total, vao));
  const meiaX = limite(itens.maxX - itens.minX, totalX) / 2, meiaY = limite(itens.maxY - itens.minY, totalY) / 2;
  const cx = (itens.minX + itens.maxX) / 2, cy = (itens.minY + itens.maxY) / 2;
  return { minX: cx - meiaX, maxX: cx + meiaX, minY: cy - meiaY, maxY: cy + meiaY };
}

/** Do mundo projetado para a tela (px, a partir do canto superior esquerdo da área do mapa). */
export function paraTela(x: number, y: number, vista: Vista, largura: number, altura: number): [number, number] {
  return [(x - vista.cx) * vista.escala + largura / 2, (y - vista.cy) * vista.escala + altura / 2];
}
/** Da tela para o mundo projetado. */
export function paraMundo(px: number, py: number, vista: Vista, largura: number, altura: number): [number, number] {
  return [vista.cx + (px - largura / 2) / vista.escala, vista.cy + (py - altura / 2) / vista.escala];
}
/** Zoom em torno de um ponto da tela (o ponto sob o cursor fica no lugar), com a escala presa aos limites. */
export function zoomEm(vista: Vista, fator: number, px: number, py: number, largura: number, altura: number,
  limites: { min: number; max: number }): Vista {
  const escala = Math.min(limites.max, Math.max(limites.min, vista.escala * fator));
  const [wx, wy] = paraMundo(px, py, vista, largura, altura);
  return { cx: wx - (px - largura / 2) / escala, cy: wy - (py - altura / 2) / escala, escala };
}
/** Deslocamento da vista em pixels da tela (arrastar, setas). */
export const deslocar = (vista: Vista, dx: number, dy: number): Vista => ({ ...vista, cx: vista.cx - dx / vista.escala, cy: vista.cy - dy / vista.escala });

/** Área à vista em graus (para o retângulo do mapinha). */
export function areaVisivel(vista: Vista, largura: number, altura: number, k: number):
  { latMin: number; latMax: number; lonMin: number; lonMax: number } {
  const [x0, y0] = paraMundo(0, 0, vista, largura, altura), [x1, y1] = paraMundo(largura, altura, vista, largura, altura);
  return { lonMin: x0 / k, lonMax: x1 / k, latMax: -y0, latMin: -y1 };
}

// ================================================================================================ tamanho (área proporcional)
/** Raio com a área proporcional ao valor (raio pela raiz quadrada); sem valor, zero ou negativo, o mínimo visível. Acima do
 * máximo da escala, preso no raio máximo. */
export function raioDeArea(valor: number | null | undefined, maximo: number | null | undefined, raioMax = RAIO_MAXIMO_MAPA,
  raioMin = RAIO_MINIMO_MAPA): number {
  if (!finito(valor) || valor <= 0 || !finito(maximo) || maximo <= 0) return raioMin;
  return Math.max(raioMin, raioMax * Math.sqrt(Math.min(valor, maximo) / maximo));
}

const limpo = (valor: number) => Number(valor.toPrecision(12));
function potencia(valor: number): number {
  let resultado = 10 ** Math.floor(Math.log10(valor));
  if (resultado * 10 <= valor * (1 + 1e-9)) resultado *= 10;
  if (resultado > valor * (1 + 1e-9)) resultado /= 10;
  return limpo(resultado);
}
const redondoAbaixo = (valor: number) => limpo(([5, 2, 1].find(fator => fator * potencia(valor) <= valor * (1 + 1e-9)) ?? 1) * potencia(valor));
const redondoAcima = (valor: number) => limpo(([1, 2, 5, 10].find(fator => fator * potencia(valor) >= valor * (1 - 1e-9)) ?? 10) * potencia(valor));

/** Três tamanhos de referência para a legenda (1, 2 ou 5 × 10ⁿ abaixo do máximo da escala), com o mesmo raio do desenho:
 * marcas da legenda, não dados. Todas na proporção exata (25/10/2026): uma referência abaixo do raio mínimo visível seria
 * desenhada maior do que a área dela; no lugar, entra o menor número redondo que já alcança o mínimo, ou nada, se ele não ficar
 * abaixo da referência anterior. A mesma regra da legenda do gráfico (valoresDaLegendaDeTamanho, em painelModel.ts). */
export function marcasDeTamanho(maximo: number | null | undefined, raioMax = RAIO_MAXIMO_MAPA, raioMin = RAIO_MINIMO_MAPA):
  { valor: number; raio: number }[] {
  if (!finito(maximo) || maximo <= 0) return [];
  const minimo = maximo * (raioMin / raioMax) ** 2, maior = redondoAbaixo(maximo);
  const valores: number[] = [];
  for (const candidato of [maior, redondoAbaixo(maior / 4), redondoAbaixo(maior / 25)]) {
    const valor = candidato >= minimo * (1 - 1e-9) ? candidato : redondoAcima(minimo);
    if (valor > 0 && valor <= maximo && (!valores.length || valor < valores[valores.length - 1])) valores.push(valor);
  }
  return valores.map(valor => ({ valor, raio: raioDeArea(valor, maximo, raioMax, raioMin) }));
}

// ================================================================================================ cor contínua
export type EscalaDeCor = "linear" | "logaritmica";
/** A escala que vale: linear por padrão; logarítmica SÓ quando a pessoa a escolheu e o domínio é todo positivo. Nunca muda
 * sozinha conforme a magnitude (Parte 13: mudança automática de escala é proibida). */
export function escalaEfetiva(escolhida: EscalaDeCor | null | undefined, dominio: [number, number] | null | undefined): EscalaDeCor {
  return escolhida === "logaritmica" && !!dominio && finito(dominio[0]) && finito(dominio[1]) && dominio[0] > 0 && dominio[1] > 0
    ? "logaritmica" : "linear";
}
/** Posição (0 a 1) do valor no domínio; fora dele, presa às pontas; domínio de um só valor, o meio da rampa. */
export function fracaoDeCor(valor: number, dominio: [number, number], escala: EscalaDeCor): number {
  const [a, b] = dominio;
  if (!(b > a)) return 0.5;
  if (escala === "logaritmica" && a > 0) return entre01(valor > 0 ? Math.log(valor / a) / Math.log(b / a) : 0);
  return entre01((valor - a) / (b - a));
}

function rgb(hex: string): [number, number, number] | null {
  const texto = /^#([0-9a-f]{6})$/i.exec(hex.trim())?.[1];
  if (!texto) return null;
  const valor = parseInt(texto, 16);
  return [(valor >> 16) & 255, (valor >> 8) & 255, valor & 255];
}
const hex = (canais: number[]) => "#" + canais.map(canal => Math.round(Math.min(255, Math.max(0, canal))).toString(16).padStart(2, "0")).join("");

/** Mistura de duas cores hexadecimais (#rrggbb); outra notação troca no meio do caminho. */
export function misturarCores(de: string, para: string, t: number): string {
  const [a, b] = [rgb(de), rgb(para)];
  if (!a || !b) return t < 0.5 ? de : para;
  return hex(a.map((canal, i) => canal + (b[i] - canal) * entre01(t)));
}
/** Cor na posição t (0 a 1) da rampa, interpolada entre os passos vizinhos. */
export function corNaRampa(t: number, rampa: readonly string[] = RAMPA_CONTINUA): string {
  const posicao = entre01(Number.isFinite(t) ? t : 0) * (rampa.length - 1);
  const indice = Math.min(rampa.length - 2, Math.floor(posicao));
  return rampa.length < 2 ? rampa[0] : misturarCores(rampa[indice], rampa[indice + 1], posicao - indice);
}
/** Cor contínua de um valor existente (mapeamento visual contínuo: transformação admitida, não é classe). Sem valor ou sem
 * domínio: null (o ponto fica vazado, nunca zero). */
export function corContinua(valor: number | null | undefined, dominio: [number, number] | null | undefined,
  escala: EscalaDeCor | null | undefined, rampa: readonly string[] = RAMPA_CONTINUA): string | null {
  if (!finito(valor) || !dominio || !finito(dominio[0]) || !finito(dominio[1])) return null;
  return corNaRampa(fracaoDeCor(valor, dominio, escalaEfetiva(escala, dominio)), rampa);
}
/** Gradiente CSS da rampa (barra da legenda): a mesma interpolação do desenho. */
export const gradienteDaRampa = (rampa: readonly string[] = RAMPA_CONTINUA) =>
  "linear-gradient(to right, " + rampa.map((cor, i) => cor + " " + Math.round(i / (rampa.length - 1) * 100) + "%").join(", ") + ")";

export type MarcaDaLegenda = { valor: number; posicao: number; extremo: boolean };
/** Marcas da legenda contínua: os extremos (o menor e o maior valor do domínio) e marcas de leitura entre eles (1, 2 e 5 × 10ⁿ
 * na logarítmica; passos redondos na linear), longe das pontas. São marcas do eixo da legenda, não limites de classe. */
export function marcasDaLegenda(dominio: [number, number] | null | undefined, escala: EscalaDeCor | null | undefined, alvo = 4): MarcaDaLegenda[] {
  if (!dominio || !finito(dominio[0]) || !finito(dominio[1])) return [];
  const [a, b] = dominio;
  const efetiva = escalaEfetiva(escala, dominio);
  if (!(b > a)) return [{ valor: a, posicao: 0.5, extremo: true }];
  const extremos: MarcaDaLegenda[] = [{ valor: a, posicao: 0, extremo: true }, { valor: b, posicao: 1, extremo: true }];
  const candidatos: number[] = [];
  if (efetiva === "logaritmica") {
    for (let k = Math.floor(Math.log10(a)); k <= Math.ceil(Math.log10(b)); k++)
      for (const fator of [1, 2, 5]) candidatos.push(limpo(fator * 10 ** k));
  } else {
    const bruto = (b - a) / Math.max(1, alvo);
    const base = potencia(bruto);
    const passo = [1, 2, 2.5, 5, 10].map(fator => limpo(fator * base)).find(candidato => candidato >= bruto * (1 - 1e-9)) ?? limpo(10 * base);
    for (let valor = limpo(Math.ceil(limpo(a / passo)) * passo); valor <= b + passo * 1e-9; valor = limpo(valor + passo)) candidatos.push(valor);
  }
  const leitura = candidatos.filter(valor => valor > a && valor < b)
    .map(valor => ({ valor, posicao: fracaoDeCor(valor, dominio, efetiva), extremo: false }))
    .filter(marca => marca.posicao >= 0.12 && marca.posicao <= 0.88);
  // Muitas marcas na logarítmica: só as potências de 10.
  const enxutas = leitura.length > 5 ? leitura.filter(marca => Number.isInteger(limpo(Math.log10(marca.valor)))) : leitura;
  return [extremos[0], ...enxutas, extremos[1]];
}
/** Posição da marca de contexto (o valor do Brasil) na rampa: só uma marca na legenda, nunca classifica ponto nenhum. Fora do
 * domínio, presa na ponta, com `fora`. */
export function posicaoDoContexto(valor: number | null | undefined, dominio: [number, number] | null | undefined,
  escala: EscalaDeCor | null | undefined): { posicao: number; fora: boolean } | null {
  if (!finito(valor) || !dominio || !finito(dominio[0]) || !finito(dominio[1])) return null;
  const fora = valor < dominio[0] || valor > dominio[1];
  return { posicao: fracaoDeCor(valor, dominio, escalaEfetiva(escala, dominio)), fora };
}

// ================================================================================================ cena (o que desenhar)
export type PontoComItem = { item: PainelItem; indice: number };
export type AnelDeConjunto = { conjunto: string; rotulo: string; membro: string; indice: number };
export type BaseDoMapa = {
  /** Itens desenháveis com coordenada (unidades; estados e conjuntos não têm ponto), na ordem recebida. */
  pontos: PontoComItem[];
  /** Itens desenháveis sem coordenada válida: ficam fora do mapa (a área os lista em Não avaliáveis, com o motivo do motor). */
  semPonto: string[];
  /** Índices da projeção que não são itens: o fundo (o formato do Brasil, ou da planilha). */
  fundo: number[];
  /** Membros de conjuntos com coordenada: ganham o anel escuro (o conjunto não tem ponto). */
  aneis: AnelDeConjunto[];
  /** Identidade do conjunto de itens com ponto (o enquadramento inicial muda só quando ela muda). */
  assinatura: string;
  limites: Limites | null;
};

/** Assinatura curta de uma lista de identificadores (FNV-1a de 32 bits), para guardar a vista de cada análise. */
export function assinaturaDe(ids: string[]): string {
  let h = 0x811c9dc5;
  for (const id of ids) {
    for (let i = 0; i < id.length; i++) { h ^= id.charCodeAt(i); h = Math.imul(h, 0x01000193) >>> 0; }
    h ^= 0x1f; h = Math.imul(h, 0x01000193) >>> 0;
  }
  return ids.length + ":" + h.toString(36);
}

/** Separa o que tem ponto: unidades com coordenada (os itens), as demais unidades da fonte (o fundo) e os membros dos
 * conjuntos (anéis). Estados e conjuntos não viram ponto. */
export function baseDoMapa(itens: PainelItem[], projecao: Projecao): BaseDoMapa {
  const pontos: PontoComItem[] = [], semPonto: string[] = [], usados = new Set<number>(), aneis: AnelDeConjunto[] = [];
  for (const item of itens) {
    if (item.tipo === "estado") continue;
    if (item.tipo === "conjunto") {
      for (const membro of item.membros || []) {
        const indice = projecao.indice.get(membro);
        if (indice !== undefined) aneis.push({ conjunto: item.id, rotulo: item.rotulo, membro, indice });
      }
      continue;
    }
    const indice = projecao.indice.get(item.id);
    if (indice === undefined) { semPonto.push(item.id); continue; }
    if (usados.has(indice)) continue;
    usados.add(indice);
    pontos.push({ item, indice });
  }
  const fundo: number[] = [];
  for (let i = 0; i < projecao.ids.length; i++) if (!usados.has(i)) fundo.push(i);
  return { pontos, semPonto, fundo, aneis, assinatura: assinaturaDe(pontos.map(ponto => ponto.item.id)),
    limites: limitesDe(projecao, pontos.map(ponto => ponto.indice)) };
}

/** Limites do enquadramento inicial (25/10/2026): os itens com ponto e os territórios de referência desenhados (a mira), para a
 * referência fora do resultado não ficar cortada na borda nem fora da vista. */
export function limitesComReferencias(projecao: Projecao, base: Pick<BaseDoMapa, "pontos">, referencias: string[]): Limites | null {
  const indices = base.pontos.map(ponto => ponto.indice);
  for (const id of referencias) {
    const indice = projecao.indice.get(id);
    if (indice !== undefined) indices.push(indice);
  }
  return limitesDe(projecao, indices);
}

export type PontoDaCena = {
  id: string; item: PainelItem; indice: number; r: number;
  /** Preenchimento (a cor da camada, a contínua ou a neutra); na vazada, a superfície. */
  cor: string; vazada: boolean; apagada: boolean;
  /** Fora da régua ou dos filtros: bem claro, no lugar, sem interação. */
  esmaecido: boolean;
};
export type Cena = {
  /** Na ordem de desenho: os maiores atrás, os menores na frente. */
  pontos: PontoDaCena[];
  porId: Map<string, number>;
  esmaecidos: number;
  vazadas: number;
  /** Máximo da escala de tamanho em uso (o do motor; sem ele, o maior valor dos itens, só para a escala). */
  maximoTamanho: number | null;
};
export type EntradaDaCena = {
  dentro: Set<string>;
  pintura: PinturaDoMapa;
  pintar: (item: PainelItem) => Pintura;
  valorContinuo: (item: PainelItem) => number | null;
  dominio: [number, number] | null;
  escala: EscalaDeCor;
  tamanho: (item: PainelItem) => number | null;
  maximoTamanho: number | null;
  raioMax?: number;
  raioMin?: number;
  cores?: Pick<CoresDoMapa, "neutro" | "superficie">;
  rampa?: readonly string[];
};

/** Pintura, tamanho e estado de cada ponto. Só traduz o que a área entregou: a pintura da camada (do motor), o valor contínuo
 * (do motor) e o valor de tamanho. */
export function montarCena(base: Pick<BaseDoMapa, "pontos">, e: EntradaDaCena): Cena {
  const cores = e.cores ?? MAPA_CORES;
  const valoresTamanho = base.pontos.map(ponto => e.tamanho(ponto.item));
  const maximoTamanho = finito(e.maximoTamanho) && e.maximoTamanho > 0 ? e.maximoTamanho
    : valoresTamanho.reduce<number | null>((maior, valor) => finito(valor) && valor > 0 && (maior === null || valor > maior) ? valor : maior, null);
  let esmaecidos = 0, vazadas = 0;
  const pontos: PontoDaCena[] = base.pontos.map((ponto, i) => {
    let cor: string = cores.neutro, vazada = false, apagada = false;
    if (e.pintura === "camada" || e.pintura === "quintis") {
      const pintura = e.pintar(ponto.item);
      cor = pintura.cor; vazada = !!pintura.vazada; apagada = !!pintura.apagada;
    } else if (e.pintura === "continua") {
      const continua = corContinua(e.valorContinuo(ponto.item), e.dominio, e.escala, e.rampa ?? RAMPA_CONTINUA);
      if (continua === null) vazada = true; else cor = continua;
    }
    if (vazada) { cor = cores.superficie; apagada = false; vazadas += 1; }
    const esmaecido = !e.dentro.has(ponto.item.id);
    if (esmaecido) esmaecidos += 1;
    return { id: ponto.item.id, item: ponto.item, indice: ponto.indice, r: raioDeArea(valoresTamanho[i], maximoTamanho, e.raioMax, e.raioMin),
      cor, vazada, apagada, esmaecido };
  });
  pontos.sort((a, b) => b.r - a.r || comparar(a.id, b.id));
  return { pontos, porId: new Map(pontos.map((ponto, i) => [ponto.id, i])), esmaecidos, vazadas, maximoTamanho };
}

// ================================================================================================ interação
/** O ponto sob o ponteiro: o centro mais próximo entre os interativos cujo alvo (o maior entre o alvo mínimo e o raio) contém
 * o ponteiro. Nos empates, o desenhado por último (o menor, na frente). -1 quando não há. */
export function alvoMaisProximo(px: number, py: number, xs: ArrayLike<number>, ys: ArrayLike<number>, raios: ArrayLike<number>,
  interativo: (i: number) => boolean, alvo: number): number {
  let melhor = -1, menor = Infinity;
  for (let i = 0; i < xs.length; i++) {
    if (!interativo(i)) continue;
    const dx = xs[i] - px, dy = ys[i] - py, d = dx * dx + dy * dy, limite = Math.max(alvo, raios[i]);
    if (d <= limite * limite && d <= menor) { melhor = i; menor = d; }
  }
  return melhor;
}

export type Direcao = "esquerda" | "direita" | "cima" | "baixo";
/** Teclado: o ponto vizinho na direção pedida (até 60° do eixo), o mais próximo com peso no desvio lateral. -1 quando não há. */
export function vizinhoNaDirecao(atual: number, direcao: Direcao, xs: ArrayLike<number>, ys: ArrayLike<number>,
  interativo: (i: number) => boolean): number {
  if (atual < 0 || atual >= xs.length) return -1;
  let melhor = -1, menor = Infinity;
  for (let i = 0; i < xs.length; i++) {
    if (i === atual || !interativo(i)) continue;
    const dx = xs[i] - xs[atual], dy = ys[i] - ys[atual];
    const ao = direcao === "direita" ? dx : direcao === "esquerda" ? -dx : direcao === "baixo" ? dy : -dy;
    const lado = Math.abs(direcao === "direita" || direcao === "esquerda" ? dy : dx);
    if (ao <= 0.5 || lado > ao * 1.75) continue;
    const nota = ao + 2 * lado;
    if (nota < menor) { melhor = i; menor = nota; }
  }
  return melhor;
}

// ================================================================================================ nomes
export type Caixa = { x0: number; y0: number; x1: number; y1: number };
export type PedidoDeNome = { id: string; x: number; y: number; r: number; largura: number;
  /** Selecionados, os de `extraDoRotulo` e, com poucos pontos, todos: o nome aparece mesmo sem lugar livre. */
  obrigatorio: boolean };
/** x: início do texto; y: linha de base. */
export type NomeNoMapa = { id: string; x: number; y: number; caixa: Caixa };
const cruza = (a: Caixa, b: Caixa) => a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;

/** Nomes junto aos pontos sem cobrir uns aos outros, os pontos nomeados nem os obstáculos (controles e mapinha): à direita, à
 * esquerda, um pouco acima ou abaixo, ou centrado embaixo ou em cima. Só o texto se move, nunca o ponto. Um nome não
 * obrigatório sem lugar livre não aparece; o obrigatório fica à direita, dentro da área. */
export function posicionarNomes(pedidos: PedidoDeNome[], largura: number, altura: number, obstaculos: Caixa[] = [], linha = 14): NomeNoMapa[] {
  const ocupadas: Caixa[] = [...obstaculos];
  const caixasDosPontos = new Map(pedidos.map(p => [p.id, { x0: p.x - p.r - 2, y0: p.y - p.r - 2, x1: p.x + p.r + 2, y1: p.y + p.r + 2 }]));
  ocupadas.push(...caixasDosPontos.values());
  const dentro = (c: Caixa) => c.x0 >= 2 && c.x1 <= largura - 2 && c.y0 >= 2 && c.y1 <= altura - 2;
  const saida: NomeNoMapa[] = [];
  const ordem = [...pedidos].sort((a, b) => Number(b.obrigatorio) - Number(a.obrigatorio));
  for (const p of ordem) {
    const propria = caixasDosPontos.get(p.id)!;
    const caixaDe = (x: number, y: number): Caixa => ({ x0: x - 2, y0: y - linha + 3, x1: x + p.largura + 2, y1: y + 4 });
    const direita = p.x + p.r + 5, esquerda = p.x - p.r - 5 - p.largura, centro = p.x - p.largura / 2;
    const candidatos: [number, number][] = [[direita, p.y + 4], [esquerda, p.y + 4], [direita, p.y + 4 + linha], [direita, p.y + 4 - linha],
      [esquerda, p.y + 4 + linha], [esquerda, p.y + 4 - linha], [centro, p.y + p.r + linha], [centro, p.y - p.r - 6]];
    let lugar = candidatos.find(([x, y]) => {
      const caixa = caixaDe(x, y);
      return dentro(caixa) && !ocupadas.some(outra => outra !== propria && cruza(caixa, outra));
    }) ?? null;
    if (!lugar && p.obrigatorio)
      lugar = [Math.max(4, Math.min(direita, largura - p.largura - 6)), Math.max(linha, Math.min(p.y + 4, altura - 6))];
    if (!lugar) continue;
    const caixa = caixaDe(lugar[0], lugar[1]);
    ocupadas.push(caixa);
    saida.push({ id: p.id, x: lugar[0], y: lugar[1], caixa });
  }
  return saida;
}

// ================================================================================================ ligações
/** Ligações ilustrativas (não são trajeto) dos selecionados até a referência mais próxima, como o motor indicou: no máximo
 * 30 origens; sem coordenada de um dos lados, ou ligando o ponto a ele mesmo, a linha não aparece. */
export function segmentosDasLigacoes(ligacoes: { de: string; para: string[] }[], temPonto: (id: string) => boolean,
  maximo = MAX_LIGACOES): { de: string; para: string }[] {
  const saida: { de: string; para: string }[] = [];
  const vistos = new Set<string>();
  for (const ligacao of ligacoes) {
    if (vistos.size >= maximo) break;
    if (vistos.has(ligacao.de)) continue;
    vistos.add(ligacao.de);
    if (!temPonto(ligacao.de)) continue;
    for (const para of new Set(ligacao.para)) if (para !== ligacao.de && temPonto(para)) saida.push({ de: ligacao.de, para });
  }
  return saida;
}

// ================================================================================================ mapinha
export type GeometriaDoMiniMapa = {
  largura: number; altura: number;
  /** Caminho SVG com um quadradinho por pixel ocupado (os pontos repetidos no mesmo pixel viram um só). */
  caminho: string;
  ocupados: number;
  k: number; minX: number; minY: number; escala: number; ox: number; oy: number;
};
/** Desenho do mapinha: todos os pontos da fonte, em quadradinhos de 1 px, enquadrados num quadrado de `tamanho` px. */
export function geometriaDoMiniMapa(pontos: Map<string, [number, number]>, tamanho = 120, folga = 4): GeometriaDoMiniMapa {
  const projecao = projetar(pontos);
  const limites = limitesDe(projecao, projecao.ids.map((_, i) => i));
  const lado = Math.max(24, Math.round(tamanho));
  if (!limites) return { largura: lado, altura: lado, caminho: "", ocupados: 0, k: projecao.k, minX: 0, minY: 0, escala: 1, ox: 0, oy: 0 };
  const vaoX = Math.max(limites.maxX - limites.minX, 0.5), vaoY = Math.max(limites.maxY - limites.minY, 0.5);
  const escala = Math.min((lado - 2 * folga) / vaoX, (lado - 2 * folga) / vaoY);
  // Os pontos ficam centrados no quadrado (com um vão mínimo, um ponto só não vira um zoom extremo).
  const ox = (lado - (limites.maxX - limites.minX) * escala) / 2, oy = (lado - (limites.maxY - limites.minY) * escala) / 2;
  const ocupadas = new Set<number>();
  const partes: string[] = [];
  for (let i = 0; i < projecao.ids.length; i++) {
    const px = Math.floor((projecao.x[i] - limites.minX) * escala + ox), py = Math.floor((projecao.y[i] - limites.minY) * escala + oy);
    const chave = py * 4096 + px;
    if (ocupadas.has(chave)) continue;
    ocupadas.add(chave);
    partes.push("M" + px + " " + py + "h1v1h-1z");
  }
  return { largura: lado, altura: lado, caminho: partes.join(""), ocupados: ocupadas.size, k: projecao.k, minX: limites.minX,
    minY: limites.minY, escala, ox, oy };
}
/** Posição de uma coordenada no mapinha (px). */
export function noMiniMapa(geo: GeometriaDoMiniMapa, lat: number, lon: number): [number, number] {
  return [(lon * geo.k - geo.minX) * geo.escala + geo.ox, (-lat - geo.minY) * geo.escala + geo.oy];
}
/** Retângulo da área à vista no mapinha, preso às bordas e com um tamanho mínimo visível. */
export function retanguloNoMiniMapa(geo: GeometriaDoMiniMapa, area: { latMin: number; latMax: number; lonMin: number; lonMax: number }):
  { x: number; y: number; largura: number; altura: number } {
  const [ax, ay] = noMiniMapa(geo, area.latMax, area.lonMin), [bx, by] = noMiniMapa(geo, area.latMin, area.lonMax);
  let x0 = Math.max(0.5, Math.min(ax, bx)), y0 = Math.max(0.5, Math.min(ay, by));
  let x1 = Math.min(geo.largura - 0.5, Math.max(ax, bx)), y1 = Math.min(geo.altura - 0.5, Math.max(ay, by));
  if (x1 - x0 < 4) { const meio = (x0 + x1) / 2; x0 = Math.max(0.5, meio - 2); x1 = Math.min(geo.largura - 0.5, x0 + 4); }
  if (y1 - y0 < 4) { const meio = (y0 + y1) / 2; y0 = Math.max(0.5, meio - 2); y1 = Math.min(geo.altura - 0.5, y0 + 4); }
  return { x: x0, y: y0, largura: Math.max(0, x1 - x0), altura: Math.max(0, y1 - y0) };
}

// ================================================================================================ transição entre as vistas
/** Suavização da transição (cúbica, entra e sai devagar). */
export const suavizar = (t: number) => { const u = entre01(t); return u < 0.5 ? 4 * u * u * u : 1 - (-2 * u + 2) ** 3 / 2; };
export type QuadroPonto = { id: string; x: number; y: number; r: number; cor: string; alfa: number };
/** Um quadro da transição: cada id presente nos dois lados vai da posição, do raio e da cor de origem aos de destino; o que só
 * existe na origem some aos poucos, e o que só existe no destino aparece aos poucos. `t` já suavizado (0 a 1). */
export function quadroDaTransicao(origem: Posicoes, destino: Posicoes, t: number): QuadroPonto[] {
  const u = entre01(t);
  const saida: QuadroPonto[] = [];
  for (const [id, a] of origem) {
    const b = destino.get(id);
    if (b) saida.push({ id, x: a.x + (b.x - a.x) * u, y: a.y + (b.y - a.y) * u, r: Math.max(0.5, a.r + (b.r - a.r) * u),
      cor: misturarCores(a.cor, b.cor, u), alfa: 1 });
    else saida.push({ id, x: a.x, y: a.y, r: a.r, cor: a.cor, alfa: 1 - u });
  }
  for (const [id, b] of destino) if (!origem.has(id)) saida.push({ id, x: b.x, y: b.y, r: b.r, cor: b.cor, alfa: u });
  // Os maiores atrás, como nas duas vistas.
  return saida.sort((p, q) => q.r - p.r);
}
