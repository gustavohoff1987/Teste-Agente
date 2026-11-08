import { useMemo } from "react";
import { coresDoMapa } from "./mapaModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";

// O mini mapa dos conjuntos (07/11/2026, item 7 do comando de 07/11/2026): no alto de "Por critérios" e de "Agrupar territórios" e
// em "Ver os conjuntos no mapa", na Seleção de Territórios. Desenha, sem medir nada, as coordenadas autorizadas que o motor deu:
// em cinza claro, o fundo (onde procurar ou o estado aberto); em destaque, os que atendem; cada conjunto com o contorno tracejado
// em volta dos membros (a envoltória dos pontos, com folga) e o nome junto ao contorno; os membros em pontos cheios; os sem
// conjunto vazados e com o nome ao lado; a barra de escala do tamanho da distância escolhida e a legenda. O nome de cada
// território aparece ao passar o mouse ou tocar. Cada conjunto se distingue pelo contorno e pelo nome, não só pela cor. No modo
// "Agrupar territórios", tocar num ponto põe ou tira o território do conjunto (a lista continua sendo o caminho pelo teclado).

export type ConjuntoNoMapa = { id: string; nome: string; membros: string[] };

type Props = {
  /** Coordenadas autorizadas (id → [latitude, longitude]), só para desenhar. */
  coordenadas: Map<string, [number, number]>;
  /** O fundo, em cinza claro. */
  fundo: string[];
  /** Os que atendem, em destaque (sem agrupamento). */
  destaque?: string[];
  conjuntos: ConjuntoNoMapa[];
  /** Os sem conjunto: vazados, com o nome ao lado. */
  semConjunto?: string[];
  nomeDe: (id: string) => string;
  /** A distância escolhida (km): a barra de escala tem esse tamanho. */
  escalaKm?: number | null;
  /** O último resultado válido enquanto falta algo (item 7.4). */
  esmaecido?: boolean;
  /** Tocar num ponto (modo Agrupar territórios): entra ou sai do conjunto. */
  onTocar?: (id: string) => void;
  rotulo: string;
  /** O que dizer quando ainda não há o que desenhar (nada escolhido, por exemplo). */
  vazio?: string;
  largura?: number;
  altura?: number;
};

const MARGEM = 14;
const FOLGA = 7;
const KM_POR_GRAU = 111.32;
const MAX_NOMES_AVULSOS = 12;
// O piso da escala tipográfica (28/10/2026): nenhum texto abaixo de 12 px, também no SVG.
const LETRA = 12;

/** A envoltória convexa (cadeia monótona de Andrew) dos pontos já na tela. */
function envoltoria(pontos: [number, number][]): [number, number][] {
  const p = [...pontos].sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (p.length < 3) return p;
  const cruz = (o: [number, number], a: [number, number], b: [number, number]) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const baixo: [number, number][] = [], cima: [number, number][] = [];
  for (const ponto of p) {
    while (baixo.length >= 2 && cruz(baixo[baixo.length - 2], baixo[baixo.length - 1], ponto) <= 0) baixo.pop();
    baixo.push(ponto);
  }
  for (let i = p.length - 1; i >= 0; i--) {
    while (cima.length >= 2 && cruz(cima[cima.length - 2], cima[cima.length - 1], p[i]) <= 0) cima.pop();
    cima.push(p[i]);
  }
  return [...baixo.slice(0, -1), ...cima.slice(0, -1)];
}

/** O contorno com folga: a envoltória dos pontos de um círculo em volta de cada membro (cantos arredondados, mesmo com 1 ou 2). Também
 * no mapa da análise (MapaAnalise, item 7.10). */
export function contornoComFolga(pontos: [number, number][], folga = FOLGA): [number, number][] {
  const anel: [number, number][] = [];
  for (const [x, y] of pontos)
    for (let k = 0; k < 12; k++) anel.push([x + folga * Math.cos(k * Math.PI / 6), y + folga * Math.sin(k * Math.PI / 6)]);
  return envoltoria(anel);
}
/** O ponto está dentro do contorno (raio cruzando as arestas)? */
export function dentroDoContorno(forma: [number, number][], x: number, y: number): boolean {
  let dentro = false;
  for (let i = 0, j = forma.length - 1; i < forma.length; j = i++) {
    const [xi, yi] = forma[i], [xj, yj] = forma[j];
    if ((yi > y) !== (yj > y) && x < (xj - xi) * (y - yi) / (yj - yi) + xi) dentro = !dentro;
  }
  return dentro;
}

export default function MapaDosConjuntos(p: Props) {
  const cores = coresDoMapa(useEsquemaDeCor());
  const largura = p.largura ?? 340, altura = p.altura ?? 220;
  const desenho = useMemo(() => {
    const ids = [...new Set([...p.fundo, ...(p.destaque ?? []), ...p.conjuntos.flatMap(c => c.membros), ...(p.semConjunto ?? [])])]
      .filter(id => p.coordenadas.has(id));
    if (!ids.length) return null;
    const lats = ids.map(id => p.coordenadas.get(id)![0]), lons = ids.map(id => p.coordenadas.get(id)![1]);
    const [minLat, maxLat, minLon, maxLon] = [Math.min(...lats), Math.max(...lats), Math.min(...lons), Math.max(...lons)];
    // Projeção simples, só para desenhar: a longitude encolhida pelo cosseno da latitude média.
    const fator = Math.cos(((minLat + maxLat) / 2) * Math.PI / 180) || 1;
    const larguraGraus = Math.max((maxLon - minLon) * fator, 0.05), alturaGraus = Math.max(maxLat - minLat, 0.05);
    const escala = Math.min((largura - 2 * MARGEM) / larguraGraus, (altura - 2 * MARGEM - 16) / alturaGraus);
    const deslocX = (largura - larguraGraus * escala) / 2, deslocY = (altura - 16 - alturaGraus * escala) / 2;
    const xy = (id: string): [number, number] => {
      const [lat, lon] = p.coordenadas.get(id)!;
      return [deslocX + (lon - minLon) * fator * escala, deslocY + (maxLat - lat) * escala];
    };
    const posicao = new Map(ids.map(id => [id, xy(id)]));
    const contornos = p.conjuntos.map(conjunto => {
      const membros = conjunto.membros.filter(id => posicao.has(id)).map(id => posicao.get(id)!);
      const forma = membros.length ? contornoComFolga(membros) : [];
      const topo = forma.reduce<[number, number] | null>((melhor, ponto) => !melhor || ponto[1] < melhor[1] ? ponto : melhor, null);
      return { ...conjunto, caminho: forma.length ? "M" + forma.map(([x, y]) => x.toFixed(1) + "," + y.toFixed(1)).join("L") + "Z" : "", topo };
    });
    const barra = p.escalaKm && p.escalaKm > 0 ? Math.min(largura - 2 * MARGEM, p.escalaKm / KM_POR_GRAU * escala) : null;
    return { posicao, contornos, barra };
  }, [p.coordenadas, p.fundo, p.destaque, p.conjuntos, p.semConjunto, p.escalaKm, largura, altura]);

  if (!desenho) return <p data-testid="analise-mapa-conjuntos-vazio" className="analise-agregar-apoio">{p.vazio ?? "Sem coordenadas para desenhar."}</p>;
  const membros = new Set(p.conjuntos.flatMap(conjunto => conjunto.membros));
  const sem = new Set(p.semConjunto ?? []);
  const destaque = new Set((p.destaque ?? []).filter(id => !membros.has(id) && !sem.has(id)));
  const papel = (id: string) => membros.has(id) ? "membro" : sem.has(id) ? "sem" : destaque.has(id) ? "atende" : "fundo";
  const ordem = [...desenho.posicao.keys()].sort((a, b) => ["fundo", "atende", "sem", "membro"].indexOf(papel(a)) -
    ["fundo", "atende", "sem", "membro"].indexOf(papel(b)));
  const nomesAvulsos = [...sem].filter(id => desenho.posicao.has(id)).slice(0, MAX_NOMES_AVULSOS);
  return <figure data-testid="analise-mapa-conjuntos" data-esmaecido={p.esmaecido ? "true" : "false"}
    className={"analise-mapa-conjuntos" + (p.esmaecido ? " analise-mapa-conjuntos-esmaecido" : "")}>
    <svg viewBox={"0 0 " + largura + " " + altura} width={largura} height={altura} role="img" aria-label={p.rotulo}
      style={{ display: "block", maxWidth: "100%", height: "auto" }}>
      <rect x={0.5} y={0.5} width={largura - 1} height={altura - 1} rx={6} fill={cores.superficie} stroke={cores.borda}/>
      {desenho.contornos.map(conjunto => conjunto.caminho && <g key={conjunto.id}>
        <path data-testid="analise-mapa-contorno" data-id={conjunto.id} data-nome={conjunto.nome} d={conjunto.caminho} fill={cores.tinta}
          fillOpacity={0.04} stroke={cores.tinta} strokeWidth={1.2} strokeDasharray="4 3"><title>{conjunto.nome}</title></path>
        {conjunto.topo && <text data-testid="analise-mapa-nome-conjunto" x={conjunto.topo[0]} y={Math.max(LETRA, conjunto.topo[1] - 3)}
          textAnchor="middle" fontSize={LETRA} fontWeight={600} fill={cores.tinta}>{conjunto.nome}</text>}
      </g>)}
      {ordem.map(id => {
        const [x, y] = desenho.posicao.get(id)!;
        const tipo = papel(id);
        const raio = tipo === "fundo" ? 1.8 : 3;
        const cheio = tipo === "membro" || tipo === "atende";
        return <circle key={id} data-testid="analise-mapa-ponto" data-id={id} data-papel={tipo} cx={x} cy={y} r={raio}
          fill={tipo === "fundo" ? cores.miniPontos : cheio ? cores.tinta : cores.superficie}
          stroke={tipo === "fundo" ? "none" : cores.tinta} strokeWidth={tipo === "sem" ? 1.3 : 0.6}
          style={p.onTocar ? { cursor: "pointer" } : undefined} onClick={p.onTocar ? () => p.onTocar!(id) : undefined}>
          <title>{p.nomeDe(id)}</title></circle>;
      })}
      {nomesAvulsos.map(id => {
        const [x, y] = desenho.posicao.get(id)!;
        return <text key={"n" + id} x={x + 5} y={y + 4} fontSize={LETRA} fill={cores.tinta}>{p.nomeDe(id).replace(/\s*\([^()]*\)\s*$/, "")}</text>;
      })}
      {desenho.barra && <g data-testid="analise-mapa-escala">
        <line x1={MARGEM} x2={MARGEM + desenho.barra} y1={altura - 9} y2={altura - 9} stroke={cores.tinta} strokeWidth={1.5}/>
        <text x={MARGEM} y={altura - 13} fontSize={LETRA} fill={cores.tinta}>{(p.escalaKm ?? 0).toLocaleString("pt-BR")} km</text>
      </g>}
    </svg>
    <figcaption className="analise-mapa-conjuntos-legenda">tracejado: conjunto · vazados: sem conjunto</figcaption>
  </figure>;
}
