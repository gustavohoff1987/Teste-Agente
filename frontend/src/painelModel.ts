// Painel integrado de bolhas (21/10/2026): modelo puro de desenho. Só posiciona, filtra (estado visual) e formata o que o
// motor entregou em /api/painel. Valores, variações percentuais, distâncias, domínios, posições dos candidatos e tipos de
// contagem vêm da resposta: nada aqui soma, conta, calcula média, classifica ou cria posição. A ordem padrão é a do código
// territorial (RQ-REP-03); reordenar a tabela é estado visual pedido pelo usuário, sem posições. Sem importações de outros
// módulos em tempo de execução (testes em Node): só tipos do cliente da API.
import type {
  PainelConjuntoPedido, PainelDominio, PainelIndicador, PainelItem, PainelMunicipios, PainelOpcoes, PainelOrdem,
  PainelAtributo, PainelReferenciaPedido, PainelResposta, ReferenciaCandidato,
} from "./painelApi";

const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
const limpo = (valor: number) => Number(valor.toPrecision(12));  // sem resíduo binário (0,30000000000000004)
const ehNumero = (valor: number | null): valor is number => valor !== null;
export const numero = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;

// ------------------------------------------------------------------------------------------------ números e textos
const casas = (digitos: number) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digitos, maximumFractionDigits: digitos });
const ate = (digitos: number) => new Intl.NumberFormat("pt-BR", { maximumFractionDigits: digitos });
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });

/** Arredondamento decimal convencional sobre o valor absoluto (RQ-REP-05), com a correção binária de representation.ts. */
export function arredondar(valor: number, digitos: number): number {
  const fator = 10 ** digitos;
  return Math.round(valor * fator + Number.EPSILON * fator * Math.max(1, valor)) / fator;
}
const mostrado = (valor: number, digitos: number) => Math.sign(valor) * arredondar(Math.abs(valor), digitos);

/** Duas casas; mais casas quando o arredondamento mostraria um valor não nulo como zero ou um valor igual a um limiar
 * diferente dele (relação com limiar, RQ-REP-05). */
function digitosPara(valor: number, limiares: number[] = []): number {
  let digitos = 2;
  while (digitos < 8 && ((valor !== 0 && mostrado(valor, digitos) === 0) ||
    limiares.some(limiar => limiar !== valor && mostrado(limiar, digitos) === mostrado(valor, digitos)))) digitos += 1;
  return digitos;
}

/** Medida contínua com duas casas (sinal preservado, com o sinal de menos tipográfico); contagem inteira. */
export function formatarNumero(valor: number, contagem = false, limiares: number[] = []): string {
  if (contagem) return inteiro.format(valor);
  const digitos = digitosPara(valor, limiares);
  return (valor < 0 ? "−" : "") + casas(digitos).format(arredondar(Math.abs(valor), digitos));
}

/** Variação percentual do motor (CAP-TMP-01) em pt-BR: "+12,40%", "−3,00%", "0,00%". Duas casas como toda medida contínua
 * (RQ-REP-05); um valor não nulo nunca aparece como zero. Sem valor: "Não avaliável". */
export function formatarVariacao(valor: number | null | undefined): string {
  if (valor === null || valor === undefined || !Number.isFinite(valor)) return "Não avaliável";
  const digitos = digitosPara(valor);
  return (valor > 0 ? "+" : valor < 0 ? "−" : "") + casas(digitos).format(arredondar(Math.abs(valor), digitos)) + "%";
}

/** Rótulo curto de escala (legenda de tamanho e marcas grandes): "2 mi", "500 mil", "1,5 mil", "200". */
export function compacto(valor: number): string {
  const absoluto = Math.abs(valor);
  if (absoluto >= 1e6) return ate(1).format(valor / 1e6) + " mi";
  if (absoluto >= 1e3) return ate(1).format(valor / 1e3) + " mil";
  return inteiro.format(valor);
}

/** Competência AAAAMM como mês/ano ("06/2024"). */
export function exibirCompetencia(valor: string | null | undefined): string {
  if (!valor) return "";
  if (/^\d{6}$/.test(valor)) {
    const mes = Number(valor.slice(4));
    if (mes >= 1 && mes <= 12) return valor.slice(4) + "/" + valor.slice(0, 4);
  }
  return valor;
}

// ------------------------------------------------------------------------------------------------ indicadores
export const INDICADORES: Record<PainelIndicador, { rotulo: string; eixo: string; unidade: string; contagem: boolean }> = {
  densidade: { rotulo: "Densidade", eixo: "Densidade (profissionais por 1.000 habitantes)", unidade: "por 1.000 habitantes", contagem: false },
  quantidade: { rotulo: "Quantidade", eixo: "Quantidade de profissionais", unidade: "profissionais", contagem: true },
};
export const ATRIBUTOS: Record<PainelAtributo, string> = { densidade: "densidade", quantidade: "quantidade", populacao: "população" };
export const ORDENS: Record<PainelOrdem, string> = { desc: "da maior para a menor", asc: "da menor para a maior" };

export const valorDe = (item: PainelItem, indicador: PainelIndicador): number | null => numero(item[indicador]);
export const inicialDe = (item: PainelItem, campo: PainelIndicador | "populacao"): number | null => numero(item.inicial?.[campo]);
/** Variação do motor; null quando não avaliável (v1 = 0, valor ausente ou suporte incompatível), sempre com o motivo. */
export const variacaoDe = (item: PainelItem, campo: PainelIndicador | "populacao"): number | null =>
  numero(item.variacao_percentual?.[campo]);

export function formatarIndicador(valor: number | null, indicador: PainelIndicador, limiares: number[] = []): string {
  if (valor === null) return "Não avaliável";
  const spec = INDICADORES[indicador];
  return formatarNumero(valor, spec.contagem, limiares) + " " + spec.unidade;
}

// ------------------------------------------------------------------------------------------------ conjuntos (RQ-REP-14)
export const SOMA = "SOMA_DOS_COMPONENTES";
/** Tipo de contagem do agregado como texto: a soma nunca é rotulada como pessoas únicas ou profissionais distintos. */
export function textoDaContagem(contagem: string | null | undefined): string {
  if (!contagem || contagem === SOMA) return "soma das contagens dos componentes, com possível dupla contagem";
  if (contagem === "UNIDADES_DISTINTAS") return "unidades distintas, conforme premissa do usuário";
  return contagem.toLowerCase().replace(/_/g, " ");
}
export const NOTA_SOMA = "Soma das contagens dos componentes, com possível dupla contagem: quem atua em mais de um município " +
  "do conjunto pode ser contado mais de uma vez. A população também é a soma dos membros.";

/** Novo conjunto do usuário (CAP-AGR-01 no motor): identificador c1, c2…; os membros são municípios, sem repetição. */
export function novoConjunto(existentes: PainelConjuntoPedido[], membros: string[], rotulo: string): PainelConjuntoPedido {
  const usados = existentes.map(conjunto => /^c(\d+)$/.exec(conjunto.id)).map(achado => achado ? Number(achado[1]) : 0);
  const proximo = Math.max(0, ...usados) + 1;
  return { id: "c" + proximo, rotulo: rotulo.trim() || "Conjunto " + proximo, membros: [...new Set(membros)] };
}

// ------------------------------------------------------------------------------------------------ ordem e motivos
/** Ordem neutra (RQ-REP-03): municípios pelo código territorial; depois os conjuntos, na ordem de criação. */
export function ordemNeutra(a: { id: string; tipo?: string }, b: { id: string; tipo?: string }): number {
  const grupoA = a.tipo === "conjunto" ? 1 : 0, grupoB = b.tipo === "conjunto" ? 1 : 0;
  return grupoA - grupoB || comparar(a.id, b.id);
}

const sem = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();

export type Aspecto = "indicador" | "distancia" | "variacao";
/** Aspecto de um motivo do motor, pelo começo do texto (nunca pela posição na lista): "Distância não avaliável …" só vale
 * para a distância; "Variação não avaliável …" e "Variação percentual … não avaliável …" só para a variação; os demais
 * ("Sem registro em …", "Nenhum membro do conjunto …", "Agregado parcial …") valem para todos. */
export function aspectoDoMotivo(texto: string): "distancia" | "variacao" | "geral" {
  const inicio = sem(texto);
  if (inicio.startsWith("distancia nao avaliavel")) return "distancia";
  if (inicio.startsWith("variacao nao avaliavel") || inicio.startsWith("variacao percentual")) return "variacao";
  return "geral";
}
/** Agregado parcial: aviso (o valor existe, sobre os membros com registro), não motivo de valor não avaliável. */
export const ehAviso = (texto: string) => sem(texto).startsWith("agregado parcial");
const textosDe = (item: PainelItem) => [...new Set((item.motivos || []).filter((texto): texto is string =>
  typeof texto === "string" && !!texto.trim()).map(texto => texto.trim()))];
/** Motivos do motor para um aspecto: primeiro os do próprio aspecto, depois os gerais (sem o aviso de agregado parcial).
 * Sem aspecto, todos os textos. */
export function motivosDe(item: PainelItem, aspecto?: Aspecto): string[] {
  const textos = textosDe(item);
  if (!aspecto) return textos;
  return [...textos.filter(texto => aspectoDoMotivo(texto) === aspecto),
    ...textos.filter(texto => aspectoDoMotivo(texto) === "geral" && !ehAviso(texto))];
}
export const avisosDe = (item: PainelItem) => textosDe(item).filter(ehAviso);

const LIMITACOES: Record<string, string> = {
  SOMA_COM_POSSIVEL_DUPLA_CONTAGEM: "Conjuntos: soma das contagens dos componentes, com possível dupla contagem.",
  AGREGADO_PARCIAL: "Agregado parcial: algum conjunto tem membro sem registro na competência, e o valor dele vale para os membros " +
    "com registro, não para o conjunto completo.",
  DISTANCIA_GEODESICA_DIRETA: "Distância geodésica direta entre os municípios, não o trajeto de deslocamento.",
  UNIDADES_NAO_AVALIAVEIS: "Há itens com valor não avaliável, listados à parte com o motivo.",
};
/** Código de limitação do motor em texto; código desconhecido aparece como está. */
export const textoDaLimitacao = (codigo: string) => LIMITACOES[codigo] || "Limitação registrada pelo motor: " + codigo + ".";
export type NaoAvaliavel = { id: string; rotulo: string; tipo: PainelItem["tipo"]; aspecto: Aspecto; motivo: string };
const MOTIVO_PADRAO: Record<Aspecto, (indicador: PainelIndicador) => string> = {
  indicador: indicador => "Sem " + INDICADORES[indicador].rotulo.toLowerCase() + " avaliável na competência.",
  distancia: () => "Sem coordenada válida para medir a distância até a referência.",
  variacao: () => "Variação não avaliável (valor inicial zero ou ausente).",
};

/** Itens desenháveis no estado do painel e não avaliáveis à parte (RQ-REP-04), na ordem neutra. Sem o indicador, o item
 * não vira bolha; com a distância à vista, também sem coordenada. Variação não avaliável: a bolha fica, vazada, e o item
 * entra na lista com o motivo. */
export function separarItens(itens: PainelItem[], indicador: PainelIndicador, distancia: boolean, crescimento: boolean):
  { plotaveis: PainelItem[]; fora: NaoAvaliavel[] } {
  const plotaveis: PainelItem[] = [], fora: NaoAvaliavel[] = [];
  const registrar = (item: PainelItem, aspecto: Aspecto) => fora.push({ id: item.id, rotulo: item.rotulo, tipo: item.tipo, aspecto,
    motivo: motivosDe(item, aspecto)[0] || MOTIVO_PADRAO[aspecto](indicador) });
  for (const item of [...itens].sort(ordemNeutra)) {
    if (valorDe(item, indicador) === null) { registrar(item, "indicador"); continue; }
    if (distancia && numero(item.distancia_km) === null) { registrar(item, "distancia"); continue; }
    plotaveis.push(item);
    if (crescimento && variacaoDe(item, indicador) === null) registrar(item, "variacao");
  }
  return { plotaveis, fora };
}

// ------------------------------------------------------------------------------------------------ escalas
export type Escala = "linear" | "logaritmica";

/** Maior potência de 10 que não passa do valor (corrige o log10 inexato perto das potências exatas). */
function potencia(valor: number): number {
  let resultado = 10 ** Math.floor(Math.log10(valor));
  if (resultado * 10 <= valor * (1 + 1e-9)) resultado *= 10;
  if (resultado > valor * (1 + 1e-9)) resultado /= 10;
  return limpo(resultado);
}

function passoBonito(bruto: number, fatores = [1, 2, 2.5, 5, 10]): number {
  if (!(bruto > 0) || !Number.isFinite(bruto)) return 1;
  const base = potencia(bruto);
  return fatores.map(fator => limpo(fator * base)).find(candidato => candidato >= bruto * (1 - 1e-9)) ?? limpo(10 * base);
}

/** Escala do eixo do indicador: logarítmica só com todos os valores positivos (como a escala de cor do mapa). */
export function escalaPossivel(valores: number[], escolhida: Escala): Escala {
  return escolhida === "logaritmica" && valores.length > 0 && valores.every(valor => valor > 0) ? "logaritmica" : "linear";
}

/** Domínio de desenho em números redondos ao redor dos valores (só enquadra; linear a partir do zero). */
export function enquadrar(valores: number[], escala: Escala): PainelDominio {
  const validos = valores.filter(valor => Number.isFinite(valor));
  if (!validos.length) return [0, 1];
  let menor = Math.min(...validos), maior = Math.max(...validos);
  if (escala === "logaritmica" && menor > 0) {
    const baixo = limpo(([5, 2, 1].find(fator => fator * potencia(menor) <= menor * (1 + 1e-9)) ?? 1) * potencia(menor));
    const alto = limpo(([1, 2, 5, 10].find(fator => fator * potencia(maior) >= maior * (1 - 1e-9)) ?? 10) * potencia(maior));
    return alto > baixo ? [baixo, alto] : [baixo, limpo(baixo * 10)];
  }
  if (menor > 0) menor = 0;
  if (maior <= menor) maior = menor + (Math.abs(menor) * 0.1 || 1);
  const passo = passoBonito((maior - menor) / 5);
  const inicio = limpo(Math.floor(limpo(menor / passo)) * passo), fim = limpo(Math.ceil(limpo(maior / passo)) * passo);
  return [menor >= 0 && inicio < 0 ? 0 : inicio, fim > inicio ? fim : limpo(inicio + passo)];
}

/** Marcas do eixo: passos 1, 2, 2,5 ou 5 × 10ⁿ; na logarítmica, 1, 2 e 5 de cada década (só as potências de 10 se forem muitas). */
export function marcas(dominio: PainelDominio, escala: Escala, alvo = 5): number[] {
  const [a, b] = dominio;
  if (!(b > a)) return [a];
  if (escala === "logaritmica" && a > 0) {
    const lista: number[] = [];
    for (let k = Math.floor(Math.log10(a)); k <= Math.ceil(Math.log10(b)); k++)
      for (const fator of [1, 2, 5]) {
        const valor = limpo(fator * 10 ** k);
        if (valor >= a * (1 - 1e-9) && valor <= b * (1 + 1e-9)) lista.push(valor);
      }
    return lista.length > 7 ? lista.filter(valor => Number.isInteger(limpo(Math.log10(valor)))) : lista;
  }
  const passo = passoBonito((b - a) / Math.max(1, alvo - 1));
  const lista: number[] = [];
  for (let valor = limpo(Math.ceil(limpo(a / passo)) * passo); valor <= b + passo * 1e-9; valor = limpo(valor + passo)) lista.push(valor);
  return lista;
}

export function textoDaMarca(valor: number): string {
  return Math.abs(valor) >= 10000 ? compacto(valor) : ate(3).format(valor);
}

/** Posição (0 a 1) de um valor no domínio; fora dele, presa às pontas. */
export function fracao(valor: number, dominio: PainelDominio, escala: Escala): number {
  const [a, b] = dominio;
  let posicao: number;
  if (escala === "logaritmica" && a > 0 && b > a) posicao = valor > 0 ? Math.log(valor / a) / Math.log(b / a) : 0;
  else posicao = b > a ? (valor - a) / (b - a) : 0.5;
  return Math.min(1, Math.max(0, posicao));
}

export function valorNaFracao(posicao: number, dominio: PainelDominio, escala: Escala): number {
  const [a, b] = dominio, t = Math.min(1, Math.max(0, posicao));
  if (escala === "logaritmica" && a > 0 && b > a) return a * (b / a) ** t;
  return a + (b - a) * t;
}

// ------------------------------------------------------------------------------------------------ tamanho (população)
export const RAIO_MINIMO = 4;
/** Maior raio conforme a largura do gráfico (celular a tela larga). */
export function raioMaximo(largura: number): number {
  return Math.round(Math.min(34, Math.max(12, largura / 34)));
}

/** Área proporcional à população (raio pela raiz quadrada); populações muito pequenas ficam no tamanho mínimo visível. */
export function raioDaPopulacao(populacao: number | null | undefined, maxima: number | null | undefined, raioMax: number): number {
  const valor = numero(populacao), topo = numero(maxima);
  if (valor === null || valor <= 0 || topo === null || topo <= 0) return RAIO_MINIMO;
  return Math.max(RAIO_MINIMO, raioMax * Math.sqrt(Math.min(valor, topo) / topo));
}

export type TamanhoLegenda = { valor: number; raio: number; texto: string };
/** Três tamanhos de referência em números redondos (1, 2 ou 5 × 10ⁿ) abaixo da maior população: legenda de escala, não dado. */
export function legendaDeTamanhos(maxima: number | null | undefined, raioMax: number): TamanhoLegenda[] {
  const topo = numero(maxima);
  if (topo === null || topo <= 0) return [];
  const abaixo = (valor: number) => limpo(([5, 2, 1].find(fator => fator * potencia(valor) <= valor * (1 + 1e-9)) ?? 1) * potencia(valor));
  const maior = abaixo(topo);
  const valores = [maior, abaixo(maior / 4), abaixo(maior / 25)].filter((valor, indice, todos) => valor > 0 && todos.indexOf(valor) === indice);
  return valores.map(valor => ({ valor, raio: raioDaPopulacao(valor, topo, raioMax), texto: compacto(valor) + " hab." }));
}

// ------------------------------------------------------------------------------------------------ cor
/** Bolha sem crescimento (série única): azul-petróleo da identidade, com croma e contraste validados. */
export const COR_BOLHA = "#008b9e";
export const COR_NEUTRA = "#c9c7bf";
export const COR_NAO_AVALIAVEL = "#898781";
// Divergente das cores de tendência (crescimento em azul, declínio em laranja; sem verde = bom nem vermelho = ruim). Cada
// braço começa num tom claro já com matiz, para que o sinal de uma variação pequena continue visível (RQ-REP-05); só o zero
// é cinza. Mapeamento visual contínuo dentro de cada braço: não cria classes.
export const RAMPA_CRESCIMENTO = ["#9cc2ee", "#2a78d6", "#184f95"];
export const RAMPA_QUEDA = ["#f2ad8c", "#eb6834", "#a8431b"];

function rgb(hex: string): [number, number, number] {
  const valor = parseInt(hex.slice(1), 16);
  return [(valor >> 16) & 255, (valor >> 8) & 255, valor & 255];
}
function misturar(de: string, para: string, t: number): string {
  const [a, b] = [rgb(de), rgb(para)];
  return "#" + a.map((canal, i) => Math.round(canal + (b[i] - canal) * t).toString(16).padStart(2, "0")).join("");
}

/** Cor da variação: azul para crescimento, laranja para queda, intensidade contínua por |variação| ÷ limite. */
export function corDaVariacao(valor: number, limite: number): string {
  if (valor === 0 || !Number.isFinite(valor)) return COR_NEUTRA;
  const t = limite > 0 ? Math.min(1, Math.abs(valor) / limite) : 1;
  const rampa = valor > 0 ? RAMPA_CRESCIMENTO : RAMPA_QUEDA;
  const posicao = t * (rampa.length - 1), indice = Math.min(rampa.length - 2, Math.floor(posicao));
  return misturar(rampa[indice], rampa[indice + 1], posicao - indice);
}

/** Limite simétrico da escala de cor: o maior |valor| do domínio de variação do motor (ou dos valores, só para enquadrar). */
export function limiteDaVariacao(resposta: Pick<PainelResposta, "dominios">, indicador: PainelIndicador, itens: PainelItem[]): number {
  const dominio = resposta.dominios["variacao_" + indicador];
  const valores = dominio ? [dominio[0], dominio[1]] : itens.map(item => variacaoDe(item, indicador)).filter(ehNumero);
  return Math.max(0, ...valores.filter(valor => Number.isFinite(valor)).map(Math.abs));
}

// ------------------------------------------------------------------------------------------------ régua (estado visual)
export type Corte = { minimo: number; maximo: number };
/** A régua filtra os municípios base; conjuntos e membros da referência ficam sempre à vista. */
export const sujeitoARegua = (item: PainelItem) => item.tipo === "municipio" && !item.referencia;

/** Dentro do corte, com os limites incluídos ("acima de" e "abaixo de" os cursores). Sem corte, tudo aparece. */
export function noCorte(item: PainelItem, indicador: PainelIndicador, corte: Corte | null): boolean {
  if (!corte || !sujeitoARegua(item)) return true;
  const valor = valorDe(item, indicador);
  return valor !== null && valor >= corte.minimo && valor <= corte.maximo;
}

export function corteAtivo(corte: Corte | null, dominio: PainelDominio | null): boolean {
  return !!corte && !!dominio && (corte.minimo > dominio[0] || corte.maximo < dominio[1]);
}

/** Passo da régua: 1, 2 ou 5 × 10ⁿ perto de 1% do domínio; inteiro na contagem e de pelo menos 0,01 nas medidas contínuas,
 * para que o limite exibido com duas casas seja o limite exato. */
export function passoDaRegua(dominio: PainelDominio, contagem: boolean): number {
  const passo = passoBonito((dominio[1] - dominio[0]) / 100, [1, 2, 5, 10]);
  return contagem ? Math.max(1, Math.round(passo)) : Math.max(0.01, passo);
}

/** Valor de um cursor em número redondo: múltiplo do passo na linear; inteiro (contagem) ou duas casas na logarítmica. As
 * pontas do domínio ficam exatas (todos à vista). */
export function ajustarValor(valor: number, dominio: PainelDominio, escala: Escala, contagem: boolean): number {
  const [a, b] = dominio;
  if (!(valor > a)) return a;
  if (!(valor < b)) return b;
  const passo = escala === "logaritmica" ? (contagem ? 1 : 0.01) : passoDaRegua(dominio, contagem);
  return Math.min(b, Math.max(a, limpo(Math.round(valor / passo) * passo)));
}

/** Um passo do cursor pelo teclado (setas: 1; Page Up/Down: 10), sempre saindo do valor atual quando há para onde ir. */
export function moverCursor(atual: number, sentido: 1 | -1, grande: boolean, dominio: PainelDominio, escala: Escala, contagem: boolean): number {
  const [a, b] = dominio, passos = grande ? 10 : 1;
  const minimo = escala === "logaritmica" ? (contagem ? 1 : 0.01) : passoDaRegua(dominio, contagem);
  const proximo = escala === "logaritmica" && a > 0
    ? (sentido > 0 ? Math.max(atual * 10 ** (passos / 50), atual + minimo) : Math.min(atual / 10 ** (passos / 50), atual - minimo))
    : atual + sentido * passos * minimo;
  const ajustado = ajustarValor(proximo, dominio, escala, contagem);
  if (ajustado !== atual || atual <= a || atual >= b) return ajustado;
  return ajustarValor(atual + sentido * minimo * 1.5, dominio, escala, contagem);
}

// ------------------------------------------------------------------------------------------------ arranjo do eixo único
export type Capsula = { id: string; x0: number; x1: number; r: number };

/** Arranjo do eixo único: desloca cada bolha (ou cometa, do valor inicial ao atual) na vertical, o mínimo possível a partir
 * da linha central, sem sobreposição. A altura não carrega valor. Determinístico: ordem pela posição, pelo raio e pelo id. */
export function arranjar(capsulas: Capsula[], folga = 1.5): Map<string, number> {
  const ordem = capsulas.map(capsula => ({ id: capsula.id, r: capsula.r, a: Math.min(capsula.x0, capsula.x1), b: Math.max(capsula.x0, capsula.x1) }))
    .sort((p, q) => p.a - q.a || q.r - p.r || comparar(p.id, q.id));
  const colocadas: { a: number; b: number; r: number; y: number }[] = [];
  const saida = new Map<string, number>();
  ordem.forEach((atual, indice) => {
    const lacuna = (outra: { a: number; b: number }) => Math.max(0, outra.a - atual.b, atual.a - outra.b);
    const vizinhas = colocadas.filter(outra => lacuna(outra) < atual.r + outra.r + folga);
    const candidatos = [0];
    for (const outra of vizinhas) {
      const alcance = atual.r + outra.r + folga, g = lacuna(outra), dy = Math.sqrt(alcance * alcance - g * g);
      candidatos.push(outra.y + dy, outra.y - dy);
    }
    const acimaPrimeiro = indice % 2 === 0;  // alterna o lado nos empates, para o enxame ficar equilibrado
    candidatos.sort((u, v) => Math.abs(u) - Math.abs(v) || (acimaPrimeiro ? u - v : v - u));
    const livre = candidatos.find(y => vizinhas.every(outra => {
      const alcance = atual.r + outra.r + folga, g = lacuna(outra);
      return Math.abs(y - outra.y) >= Math.sqrt(Math.max(0, alcance * alcance - g * g)) - 1e-6;
    }));
    const y = livre ?? 0;
    colocadas.push({ a: atual.a, b: atual.b, r: atual.r, y });
    saida.set(atual.id, y);
  });
  return saida;
}

// ------------------------------------------------------------------------------------------------ gráfico
export type Vista = "final" | "inicial";
export type MarcaEixo = { valor: number; pos: number; texto: string };
export type EixoDesenho = { tipo: PainelIndicador | "distancia"; rotulo: string; dominio: PainelDominio; escala: Escala;
  de: number; ate: number; marcas: MarcaEixo[] };
export type BolhaDesenho = {
  id: string; tipo: PainelItem["tipo"]; item: PainelItem; x: number; y: number; r: number;
  /** Na vista da competência inicial, itens sem variação avaliável não têm posição observada e ficam ocultos. */
  visivel: boolean;
  valor: number; inicial: number | null; variacao: number | null; referencia: boolean;
  /** Início do rastro (valor na competência inicial), relativo ao centro da bolha. */
  rastro: { dx: number; dy: number } | null;
  /** Conjunto com a distância à vista: do membro mais próximo (centro) ao mais distante, relativo ao centro. */
  faixa: { dx: number } | null;
  cor: string; vazada: boolean;
};
export type Grafico = { largura: number; altura: number; topo: number; base: number; esquerda: number; direita: number;
  eixoX: EixoDesenho; eixoY: EixoDesenho | null; bolhas: BolhaDesenho[]; raioMax: number; populacaoMaxima: number; escala: Escala };
export type ParametrosGrafico = {
  itens: PainelItem[]; dominios: PainelResposta["dominios"]; indicador: PainelIndicador; escala: Escala;
  distancia: boolean; crescimento: boolean; vista: Vista; largura: number; limiteVariacao: number; rotuloDistancia: string;
};

/** Desenho do painel no estado escolhido. Sem distância: eixo único horizontal do indicador, com as bolhas arrumadas sem
 * sobreposição. Com distância: X = distância até a referência, Y = indicador. Tamanho = população (área proporcional).
 * Com crescimento, o rastro liga só os dois valores observados da mesma unidade (inicial e atual), quando o motor devolve a
 * variação: sem reta de ajuste, sem projeção. */
export function montarGrafico(p: ParametrosGrafico): Grafico {
  const largura = Math.max(280, Math.round(p.largura));
  const raioMax = raioMaximo(largura);
  const dominioDo = (chave: string): PainelDominio | null => {
    const dominio = p.dominios[chave];
    return dominio && Number.isFinite(dominio[0]) && Number.isFinite(dominio[1]) ? dominio : null;
  };
  const comRastro = (item: PainelItem) => p.crescimento && variacaoDe(item, p.indicador) !== null && inicialDe(item, p.indicador) !== null;
  const valores = [...(dominioDo(p.indicador) || p.itens.map(item => valorDe(item, p.indicador)).filter(ehNumero)),
    ...p.itens.filter(comRastro).map(item => inicialDe(item, p.indicador)).filter(ehNumero)];
  const escala = escalaPossivel(valores, p.escala);
  const dominioIndicador = enquadrar(valores, escala);
  const populacoes = [...(dominioDo("populacao") ? [dominioDo("populacao")![1]] : p.itens.map(item => numero(item.populacao)).filter(ehNumero)),
    ...(p.crescimento ? p.itens.map(item => inicialDe(item, "populacao")).filter(ehNumero) : [])];
  const populacaoMaxima = populacoes.length ? Math.max(...populacoes) : 0;
  const esquerda = p.distancia ? 66 : 20, direita = 24, topo = 16, rodape = 50;
  const folga = Math.max(8, Math.round(raioMax * 0.6));
  const de = esquerda + folga, ateX = largura - direita - folga;
  const entre = (t: number, inicio: number, fim: number) => inicio + (fim - inicio) * t;
  const especie = INDICADORES[p.indicador];
  const naVistaInicial = p.crescimento && p.vista === "inicial";

  const base = p.itens.map(item => {
    const valor = valorDe(item, p.indicador) as number;
    const rastro = comRastro(item);
    const inicial = rastro ? inicialDe(item, p.indicador) : null;
    const variacao = p.crescimento ? variacaoDe(item, p.indicador) : null;
    const rFinal = raioDaPopulacao(item.populacao, populacaoMaxima, raioMax);
    const rInicial = rastro ? raioDaPopulacao(inicialDe(item, "populacao") ?? item.populacao, populacaoMaxima, raioMax) : rFinal;
    const cor = p.crescimento ? (variacao === null ? "#ffffff" : corDaVariacao(variacao, p.limiteVariacao)) : COR_BOLHA;
    return { item, valor, inicial, variacao, rFinal, rInicial, cor, vazada: p.crescimento && variacao === null,
      visivel: !naVistaInicial || rastro };
  });

  const eixoIndicador = (inicio: number, fim: number): EixoDesenho => ({ tipo: p.indicador, rotulo: especie.eixo, dominio: dominioIndicador,
    escala, de: inicio, ate: fim, marcas: marcas(dominioIndicador, escala).map(valor => ({ valor,
      pos: entre(fracao(valor, dominioIndicador, escala), inicio, fim), texto: textoDaMarca(valor) })) });

  if (!p.distancia) {
    const x = (valor: number) => entre(fracao(valor, dominioIndicador, escala), de, ateX);
    const arranjo = arranjar(base.map(d => ({ id: d.item.id, x0: d.inicial !== null ? x(d.inicial) : x(d.valor), x1: x(d.valor),
      r: Math.max(d.rFinal, d.rInicial) })));
    let acima = 0, abaixo = 0;
    for (const d of base) {
      const y = arranjo.get(d.item.id) ?? 0, r = Math.max(d.rFinal, d.rInicial);
      acima = Math.min(acima, y - r); abaixo = Math.max(abaixo, y + r);
    }
    const alturaPlot = Math.max(180, Math.ceil(abaixo - acima) + 24);
    const centro = topo + alturaPlot / 2 - (acima + abaixo) / 2;
    const bolhas = base.map(d => {
      const y = centro + (arranjo.get(d.item.id) ?? 0);
      const xFinal = x(d.valor), xInicial = d.inicial !== null ? x(d.inicial) : null;
      const naInicial = naVistaInicial && xInicial !== null;
      return { id: d.item.id, tipo: d.item.tipo, item: d.item, x: naInicial ? xInicial! : xFinal, y, r: naInicial ? d.rInicial : d.rFinal,
        visivel: d.visivel, valor: d.valor, inicial: d.inicial, variacao: d.variacao, referencia: !!d.item.referencia,
        rastro: !naVistaInicial && xInicial !== null && Math.abs(xInicial - xFinal) >= 1 ? { dx: xInicial - xFinal, dy: 0 } : null,
        faixa: null, cor: d.cor, vazada: d.vazada };
    });
    return { largura, altura: topo + alturaPlot + rodape, topo, base: topo + alturaPlot, esquerda, direita,
      eixoX: eixoIndicador(de, ateX), eixoY: null, bolhas, raioMax, populacaoMaxima, escala };
  }

  const distancias = [0, ...(dominioDo("distancia_km") || []), ...p.itens.map(item => numero(item.distancia_km)).filter(ehNumero),
    ...p.itens.map(item => numero(item.distancia_km_max)).filter(ehNumero)];
  const dominioDistancia = enquadrar(distancias, "linear");
  const alturaPlot = Math.round(Math.min(540, Math.max(280, largura * 0.5)));
  const baixoY = topo + alturaPlot - folga, altoY = topo + folga;
  const x = (valor: number) => entre(fracao(valor, dominioDistancia, "linear"), de, ateX);
  const y = (valor: number) => entre(fracao(valor, dominioIndicador, escala), baixoY, altoY);
  const bolhas = base.map(d => {
    const distancia = numero(d.item.distancia_km) ?? 0, maxima = numero(d.item.distancia_km_max);
    const bx = x(distancia), yFinal = y(d.valor), yInicial = d.inicial !== null ? y(d.inicial) : null;
    const naInicial = naVistaInicial && yInicial !== null;
    return { id: d.item.id, tipo: d.item.tipo, item: d.item, x: bx, y: naInicial ? yInicial! : yFinal, r: naInicial ? d.rInicial : d.rFinal,
      visivel: d.visivel, valor: d.valor, inicial: d.inicial, variacao: d.variacao, referencia: !!d.item.referencia,
      rastro: !naVistaInicial && yInicial !== null && Math.abs(yInicial - yFinal) >= 1 ? { dx: 0, dy: yInicial - yFinal } : null,
      faixa: d.item.tipo === "conjunto" && maxima !== null && maxima > distancia ? { dx: x(maxima) - bx } : null,
      cor: d.cor, vazada: d.vazada };
  });
  const eixoX: EixoDesenho = { tipo: "distancia", rotulo: p.rotuloDistancia, dominio: dominioDistancia, escala: "linear", de, ate: ateX,
    marcas: marcas(dominioDistancia, "linear").map(valor => ({ valor, pos: x(valor), texto: textoDaMarca(valor) })) };
  return { largura, altura: topo + alturaPlot + rodape, topo, base: topo + alturaPlot, esquerda, direita, eixoX,
    eixoY: eixoIndicador(baixoY, altoY), bolhas, raioMax, populacaoMaxima, escala };
}

/** Cauda do cometa: triângulo do ponto da competência inicial (fino) até a bolha, em coordenadas relativas ao centro. */
export function caudaDoCometa(dx: number, dy: number, r: number): string {
  const comprimento = Math.hypot(dx, dy);
  if (comprimento < 1) return "";
  const meia = Math.min(r * 0.7, 6);
  const px = -dy / comprimento * meia, py = dx / comprimento * meia;
  const f = (valor: number) => String(Math.round(valor * 100) / 100);
  return f(dx) + "," + f(dy) + " " + f(px) + "," + f(py) + " " + f(-px) + "," + f(-py);
}

export type Rotulo = { dx: number; dy: number; ancora: "start" | "end" };
/** Rótulos diretos seletivos: à direita da bolha (à esquerda perto da borda), deslocados na vertical quando colidem. */
export function posicionarRotulos(itens: { id: string; x: number; y: number; r: number; largura: number }[], limite: number,
  altura = 15): Map<string, Rotulo> {
  const ocupados: { x0: number; x1: number; y0: number; y1: number }[] = [];
  const saida = new Map<string, Rotulo>();
  for (const item of [...itens].sort((a, b) => a.y - b.y || a.x - b.x || comparar(a.id, b.id))) {
    const direita = item.x + item.r + 6 + item.largura <= limite;
    const x0 = direita ? item.x + item.r + 6 : item.x - item.r - 6 - item.largura, x1 = x0 + item.largura;
    const deslocamentos = [0, altura, -altura, 2 * altura, -2 * altura, 3 * altura, -3 * altura];
    const dy = deslocamentos.find(desvio => !ocupados.some(caixa => x0 < caixa.x1 && x1 > caixa.x0 &&
      item.y + desvio - altura / 2 < caixa.y1 && item.y + desvio + altura / 2 > caixa.y0)) ?? 0;
    ocupados.push({ x0, x1, y0: item.y + dy - altura / 2, y1: item.y + dy + altura / 2 });
    saida.set(item.id, { dx: direita ? item.r + 6 : -(item.r + 6), dy, ancora: direita ? "start" : "end" });
  }
  return saida;
}

/** Largura aproximada de um texto de 12 px (Inter), só para afastar rótulos. */
export const larguraDoTexto = (texto: string, tamanho = 12) => Math.ceil(texto.length * tamanho * 0.56) + 4;

// ------------------------------------------------------------------------------------------------ dica e tabela
export type LinhaDica = { rotulo: string; valor: string };
export type Dica = { titulo: string; subtitulo: string; linhas: LinhaDica[]; notas: string[] };
export type ContextoDica = { indicador: PainelIndicador; competencia: string; competenciaInicial: string | null; distancia: boolean;
  crescimento: boolean; nomes: Map<string, string>; limiares?: number[] };

/** Conteúdo da dica (ao passar o mouse e ao focar): nome, UF, população, profissionais, densidade, distância e variação, só
 * com valores do motor; o valor vem primeiro, o rótulo depois. */
export function montarDica(item: PainelItem, contexto: ContextoDica): Dica {
  const conjunto = item.tipo === "conjunto";
  const limiares = (indicador: PainelIndicador) => contexto.indicador === indicador ? contexto.limiares || [] : [];
  const populacao = numero(item.populacao), quantidade = numero(item.quantidade);
  const linhas: LinhaDica[] = [
    { rotulo: conjunto ? "População (soma dos membros)" : "População", valor: populacao === null ? "Não avaliável" : formatarNumero(populacao, true) + " habitantes" },
    { rotulo: conjunto ? "Profissionais (soma das contagens dos componentes)" : "Profissionais",
      valor: quantidade === null ? "Não avaliável" : formatarNumero(quantidade, true, limiares("quantidade")) },
    { rotulo: "Densidade", valor: formatarIndicador(valorDe(item, "densidade"), "densidade", limiares("densidade")) },
  ];
  const notas: string[] = [];
  if (contexto.distancia) {
    const distancia = numero(item.distancia_km), maxima = numero(item.distancia_km_max);
    linhas.push({ rotulo: item.referencia ? "Distância (membro da referência)" : conjunto ? "Distância (membro mais próximo)" : "Distância até a referência",
      valor: distancia === null ? "Não avaliável" : formatarNumero(distancia) + " km" });
    if (conjunto && maxima !== null) linhas.push({ rotulo: "Distância (membro mais distante)", valor: formatarNumero(maxima) + " km" });
    if (distancia === null) notas.push(...motivosDe(item, "distancia").slice(0, 1));
  }
  if (contexto.crescimento) {
    const desde = exibirCompetencia(contexto.competenciaInicial);
    const especie = INDICADORES[contexto.indicador];
    const variacao = variacaoDe(item, contexto.indicador), inicial = inicialDe(item, contexto.indicador);
    linhas.push({ rotulo: "Variação da " + especie.rotulo.toLowerCase() + (desde ? " desde " + desde : ""), valor: formatarVariacao(variacao) });
    if (inicial !== null) linhas.push({ rotulo: especie.rotulo + (desde ? " em " + desde : " na competência inicial"),
      valor: formatarIndicador(inicial, contexto.indicador) });
    const populacaoVariacao = variacaoDe(item, "populacao");
    if (populacaoVariacao !== null) linhas.push({ rotulo: "Variação da população", valor: formatarVariacao(populacaoVariacao) });
    if (variacao === null) notas.push(motivosDe(item, "variacao")[0] || MOTIVO_PADRAO.variacao(contexto.indicador));
  }
  notas.push(...avisosDe(item));
  if (conjunto) {
    notas.push(NOTA_SOMA);
    const membros = (item.membros || []).map(id => contexto.nomes.get(id) || id);
    if (membros.length) notas.push("Membros: " + membros.join(", ") + ".");
  }
  if (item.referencia) notas.push("Membro da referência da distância.");
  return { titulo: item.rotulo, subtitulo: conjunto ? "Conjunto de municípios · " + textoDaContagem(item.contagem) : ["Município", item.uf || ""].filter(Boolean).join(" · "),
    linhas, notas: [...new Set(notas)] };
}

export type ColunaTabela = "territorio" | "populacao" | "quantidade" | "densidade" | "distancia" | "variacao";
export type Ordenacao = { coluna: ColunaTabela; sentido: "asc" | "desc" } | null;

/** Linhas da tabela: na ordem neutra ou, quando o usuário clica num cabeçalho, pela coluna escolhida (estado visual, sem
 * posições; sem valor, no fim). */
export function ordenarTabela(itens: PainelItem[], ordenacao: Ordenacao, indicador: PainelIndicador): PainelItem[] {
  const neutra = [...itens].sort(ordemNeutra);
  if (!ordenacao) return neutra;
  const { coluna, sentido } = ordenacao;
  const chave = (item: PainelItem): number | string | null =>
    coluna === "territorio" ? item.rotulo : coluna === "populacao" ? numero(item.populacao)
      : coluna === "quantidade" ? numero(item.quantidade) : coluna === "densidade" ? numero(item.densidade)
      : coluna === "distancia" ? numero(item.distancia_km) : variacaoDe(item, indicador);
  return neutra.sort((a, b) => {
    const va = chave(a), vb = chave(b);
    if (va === null || vb === null) return va === vb ? 0 : va === null ? 1 : -1;
    const diferenca = typeof va === "number" && typeof vb === "number" ? va - vb : comparar(String(va), String(vb));
    return sentido === "asc" ? diferenca : -diferenca;
  });
}

// ------------------------------------------------------------------------------------------------ referência e competências
/** "Usar o primeiro" (CAP-SUB-03): os candidatos na 1ª posição do motor. Mais de um é empate, e a tela pede a escolha. */
export const primeirosColocados = (candidatos: ReferenciaCandidato[]) => candidatos.filter(candidato => candidato.posicao === 1);

export const cronologica = (valores: string[]) => [...new Set(valores)].sort(comparar);
export const maisRecente = (periodos: string[]) => cronologica(periodos).at(-1) ?? "";
export const anteriores = (periodos: string[], competencia: string) => cronologica(periodos).filter(periodo => comparar(periodo, competencia) < 0);
/** Competência inicial sugerida para o crescimento: o mesmo mês do ano anterior, se existir; senão, a mais antiga. */
export function inicialSugerida(periodos: string[], competencia: string): string {
  const lista = anteriores(periodos, competencia);
  if (/^\d{6}$/.test(competencia)) {
    const alvo = String(Number(competencia.slice(0, 4)) - 1) + competencia.slice(4);
    if (lista.includes(alvo)) return alvo;
  }
  return lista[0] ?? "";
}

// ------------------------------------------------------------------------------------------------ municípios base e pedido
export const prefixoDe = (id: string) => id.startsWith("code:") ? id.slice(5, 7) : "";

/** Universo enviado ao motor: "todos" absorve o resto; um estado inteiro absorve os seus municípios avulsos. */
export function normalizarBase(base: PainelMunicipios): PainelMunicipios {
  if (base.todos) return { todos: true, estados: [], ids: [] };
  const estados = [...new Set(base.estados)].sort(comparar);
  return { todos: false, estados, ids: [...new Set(base.ids)].filter(id => !estados.includes(prefixoDe(id))) };
}
export const baseVazia = (base: PainelMunicipios) => !base.todos && !base.estados.length && !base.ids.length;
/** O motor aceita base vazia quando há conjunto; sem os dois, não há o que pedir. */
export const semPedido = (base: PainelMunicipios, conjuntos: PainelConjuntoPedido[]) => baseVazia(base) && !conjuntos.length;
export const MAX_CONJUNTOS = 50;

/** Universo inicial: o da abrangência clássica (todos, estados inteiros e municípios marcados); sem escolha, todos os
 * municípios quando a base é pequena (até `limite`), senão nenhum, à espera da escolha. */
export function baseInicial(escopo: { todos: boolean; grupos: string[] }, ids: string[], total: number, limite = 300): PainelMunicipios {
  if (escopo.todos) return { todos: true, estados: [], ids: [] };
  if (escopo.grupos.length || ids.length) return normalizarBase({ todos: false, estados: escopo.grupos, ids });
  return { todos: total > 0 && total <= limite, estados: [], ids: [] };
}

export type DefinicaoPainel = { competencia: string; competenciaInicial: string; categoria: string; base: PainelMunicipios;
  conjuntos: PainelConjuntoPedido[]; referencia: PainelReferenciaPedido | null };

/** Opções de /api/painel, com os nomes do contrato. */
export function montarOpcoes(definicao: DefinicaoPainel): PainelOpcoes {
  const opcoes: PainelOpcoes = { competencia: definicao.competencia, categoria: definicao.categoria,
    base: { municipios: normalizarBase(definicao.base) } };
  if (definicao.competenciaInicial) opcoes.competencia_inicial = definicao.competenciaInicial;
  if (definicao.conjuntos.length) opcoes.conjuntos = definicao.conjuntos;
  if (definicao.referencia) opcoes.referencia = definicao.referencia;
  return opcoes;
}
