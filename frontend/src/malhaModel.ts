// A malha municipal do IBGE (comando V23, etapa 7: o mapa do Detector de Sinais com divisas, na base do Brasil). O arquivo é
// versionado em `frontend/public/malha/`, com a fonte, a data e o SHA-256 em `fonte.json`, e só é pedido quando o mapa abre. Aqui
// fica a leitura dele (TopoJSON), pura e sem rede: as áreas de cada município, as divisas dos estados (os trechos da malha entre
// municípios de estados diferentes, e a borda do país) e o retângulo de cada estado, para aproximar o mapa nele. A malha serve só
// ao desenho: nenhuma área, distância ou valor é calculado com ela.

/** Um ponto [longitude, latitude], em graus. */
export type Ponto = [number, number];
/** O retângulo que contém uma área: [menor longitude, menor latitude, maior longitude, maior latitude]. */
export type Caixa = [number, number, number, number];
export type AreaDaMalha = { codigo: string; uf: string; aneis: Ponto[][]; caixa: Caixa };
export type Malha = {
  /** A área de cada município, pelo código de 6 dígitos da base (os 6 primeiros do `codarea` da malha). */
  areas: Map<string, AreaDaMalha>;
  /** As divisas dos estados: cada trecho, uma linha, com o retângulo dela. */
  divisasDosEstados: { linha: Ponto[]; caixa: Caixa }[];
  /** O retângulo de cada estado (pelo prefixo de 2 dígitos), a união dos municípios dele. */
  ufs: Map<string, Caixa>;
};

export const ARQUIVO_DA_MALHA = "malha/municipios-ibge-qualidade-minima.json";

const uniao = (a: Caixa | undefined, b: Caixa): Caixa => a ? [Math.min(a[0], b[0]), Math.min(a[1], b[1]), Math.max(a[2], b[2]), Math.max(a[3], b[3])] : b;

/** A malha lida de um TopoJSON do IBGE; null quando o conteúdo não é uma topologia com áreas. */
export function decodificarMalha(bruto: unknown): Malha | null {
  const topo = bruto as { type?: unknown; arcs?: unknown; transform?: { scale?: unknown; translate?: unknown }; objects?: unknown } | null;
  if (!topo || topo.type !== "Topology" || !Array.isArray(topo.arcs) || !topo.objects || typeof topo.objects !== "object") return null;
  const objeto = Object.values(topo.objects as Record<string, { geometries?: unknown }>)[0];
  if (!objeto || !Array.isArray(objeto.geometries)) return null;
  const par = (valor: unknown, padrao: Ponto): Ponto => Array.isArray(valor) && valor.length === 2 && valor.every(n => typeof n === "number") ? valor as Ponto : padrao;
  const [ex, ey] = par(topo.transform?.scale, [1, 1]), [dx, dy] = par(topo.transform?.translate, [0, 0]);
  // Cada arco da topologia: as posições vêm como diferenças acumuladas, numa grade de inteiros.
  const arcos: Ponto[][] = (topo.arcs as number[][][]).map(arco => {
    let x = 0, y = 0;
    return arco.map(([px, py]) => { x += px; y += py; return [x * ex + dx, y * ey + dy] as Ponto; });
  });
  // Um arco com índice negativo é o arco ~i percorrido ao contrário.
  const doArco = (indice: number): Ponto[] => indice >= 0 ? arcos[indice] ?? [] : [...(arcos[~indice] ?? [])].reverse();
  const anelDe = (indices: number[]): Ponto[] => {
    const anel: Ponto[] = [];
    for (const indice of indices) { const trecho = doArco(indice); anel.push(...(anel.length ? trecho.slice(1) : trecho)); }
    return anel;
  };
  const areas = new Map<string, AreaDaMalha>(), ufs = new Map<string, Caixa>();
  /** De quais estados são os municípios que usam cada arco. */
  const usos = new Map<number, string[]>();
  for (const bruta of objeto.geometries as { type?: unknown; arcs?: unknown; properties?: { codarea?: unknown } }[]) {
    const codarea = typeof bruta?.properties?.codarea === "string" ? bruta.properties.codarea : "";
    if (codarea.length < 6 || !Array.isArray(bruta.arcs) || (bruta.type !== "Polygon" && bruta.type !== "MultiPolygon")) continue;
    const indices = (bruta.type === "Polygon" ? bruta.arcs : (bruta.arcs as unknown[][]).flat()) as number[][];
    const aneis = indices.map(anelDe).filter(anel => anel.length >= 3);
    if (!aneis.length) continue;
    const uf = codarea.slice(0, 2), codigo = codarea.slice(0, 6);
    let caixa: Caixa | undefined;
    for (const anel of aneis) for (const [x, y] of anel) caixa = uniao(caixa, [x, y, x, y]);
    areas.set(codigo, { codigo, uf, aneis, caixa: caixa! });
    ufs.set(uf, uniao(ufs.get(uf), caixa!));
    for (const indice of new Set(indices.flat().map(i => i >= 0 ? i : ~i))) usos.set(indice, [...(usos.get(indice) ?? []), uf]);
  }
  if (!areas.size) return null;
  // A divisa de um estado: o arco usado por um município só (a borda do país e o litoral) ou por municípios de estados diferentes.
  const divisasDosEstados = [...usos.entries()].filter(([, usado]) => usado.length === 1 || new Set(usado).size > 1)
    .sort(([a], [b]) => a - b).map(([indice]) => {
      let caixa: Caixa | undefined;
      for (const [x, y] of arcos[indice]) caixa = uniao(caixa, [x, y, x, y]);
      return { linha: arcos[indice], caixa: caixa! };
    });
  return { areas, divisasDosEstados, ufs };
}

let pedida: Promise<Malha | null> | null = null;
/** A malha, pedida uma vez só (quando o mapa abre pela primeira vez); null quando o arquivo não pôde ser lido — a tela segue sem
 * as divisas e diz isso, e a próxima abertura do mapa tenta de novo. `raiz` é o endereço da interface (o `BASE_URL` dela). */
export function carregarMalha(raiz: string, pedir: (endereco: string) => Promise<unknown> = endereco => fetch(endereco).then(resposta =>
  resposta.ok ? resposta.json() : Promise.reject(new Error("malha indisponível")))): Promise<Malha | null> {
  if (!pedida) {
    const tentativa: Promise<Malha | null> = pedir(raiz.replace(/\/?$/, "/") + ARQUIVO_DA_MALHA).then(decodificarMalha).catch(() => null)
      .then(malha => { if (!malha && pedida === tentativa) pedida = null; return malha; });
    pedida = tentativa;
  }
  return pedida;
}

/** O caminho SVG de uma lista de linhas ou anéis, com a projeção do mapa; `fechar` fecha cada anel (as áreas). */
export function caminhoDaMalha(linhas: Ponto[][], xy: (ponto: Ponto) => [number, number], fechar = false): string {
  let caminho = "";
  for (const linha of linhas) {
    if (linha.length < 2) continue;
    caminho += "M" + linha.map(ponto => { const [x, y] = xy(ponto); return x.toFixed(1) + "," + y.toFixed(1); }).join("L") + (fechar ? "Z" : "");
  }
  return caminho;
}

/** As duas caixas se tocam? (para desenhar só as áreas que aparecem no mapa). */
export const caixasSeTocam = (a: Caixa, b: Caixa): boolean => a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1];

/** Um território à vista no mapa: o identificador dele na tela, o código de 6 dígitos da base e, quando ele tem nível no desenho,
 * a cor do nível e o que ela diz. */
export type NoMapa = { id: string; codigo: string; cor?: string; chave?: string };
export type DivisasDoMapa = { areas: { id: string; aneis: Ponto[][]; cor?: string; chave?: string }[]; comBordas: boolean; linhas: Ponto[][];
  moldura: Caixa | null;
  /** Os estados (prefixos) dos territórios à vista que têm área na malha, em ordem. */
  ufs: string[] };

/** As divisas a desenhar num mapa: as áreas dos municípios à vista que têm nível, com a cor dele (o que a malha tiver a mais, e
 * quem não tem nível, fica sem cor); as divisas dos estados, sempre; e as dos municípios quando o mapa é aproximado num estado
 * (`aproximado`, o prefixo dele) ou quando os territórios à vista são de um estado só. A moldura é o estado aproximado ou, sem
 * ele, o retângulo das áreas à vista. Só desenho: nada é medido. */
export function divisasDoMapa(malha: Malha, aVista: NoMapa[], aproximado = ""): DivisasDoMapa {
  const comArea = aVista.filter(item => malha.areas.has(item.codigo));
  const ufs = [...new Set(comArea.map(item => malha.areas.get(item.codigo)!.uf))].sort();
  const emFoco = aproximado && malha.ufs.has(aproximado) ? aproximado : "";
  const comBordas = !!emFoco || ufs.length === 1;
  let moldura: Caixa | null = emFoco ? malha.ufs.get(emFoco)! : null;
  if (!emFoco) for (const item of comArea) moldura = uniao(moldura ?? undefined, malha.areas.get(item.codigo)!.caixa);
  const naMoldura = (caixa: Caixa): boolean => !moldura || caixasSeTocam(caixa, moldura);
  const doCodigo = new Map(comArea.map(item => [item.codigo, item]));
  const areas: DivisasDoMapa["areas"] = [];
  for (const item of comArea) {
    const area = malha.areas.get(item.codigo)!;
    if (item.cor && naMoldura(area.caixa)) areas.push({ id: item.id, aneis: area.aneis, cor: item.cor, chave: item.chave });
  }
  if (comBordas) {
    const estados = new Set(emFoco ? [emFoco] : ufs);
    for (const area of malha.areas.values())
      if (estados.has(area.uf) && !doCodigo.get(area.codigo)?.cor) areas.push({ id: doCodigo.get(area.codigo)?.id ?? "malha:" + area.codigo, aneis: area.aneis });
  }
  return { areas, comBordas, linhas: malha.divisasDosEstados.filter(divisa => naMoldura(divisa.caixa)).map(divisa => divisa.linha), moldura, ufs };
}
