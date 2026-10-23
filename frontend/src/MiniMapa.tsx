import { memo } from "react";
import type { MiniMapaProps } from "./mapaContrato";
import { coordenadaValida, coresDoMapa, geometriaDoMiniMapa, noMiniMapa, retanguloNoMiniMapa, type GeometriaDoMiniMapa } from "./mapaModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";

// Mapinha (23/10/2026): o Brasil (ou a planilha) em pontos cinza e um destaque. Aparece na dica do gráfico ("onde fica?") e no
// canto do mapa com zoom, com o retângulo da área à vista. SVG pequeno: os pontos viram um só caminho, com um quadradinho por
// pixel ocupado, calculado uma vez por fonte e tamanho. Só desenha coordenadas autorizadas do motor; não mede nada. As cores são
// as do mapa no esquema de cor do aparelho (coresDoMapa).

const memoria = new WeakMap<Map<string, [number, number]>, Map<number, GeometriaDoMiniMapa>>();
function geometria(pontos: Map<string, [number, number]>, tamanho: number): GeometriaDoMiniMapa {
  let porTamanho = memoria.get(pontos);
  if (!porTamanho) { porTamanho = new Map(); memoria.set(pontos, porTamanho); }
  let geo = porTamanho.get(tamanho);
  if (!geo) { geo = geometriaDoMiniMapa(pontos, tamanho); porTamanho.set(tamanho, geo); }
  return geo;
}

/** A camada dos pontos não depende do destaque nem do retângulo: não é refeita a cada movimento. */
const Pontos = memo(function Pontos({ caminho, cor }: { caminho: string; cor: string }) {
  return <path d={caminho} fill={cor} shapeRendering="crispEdges"/>;
});

export default function MiniMapa({ pontos, destaque, enquadramento = null, tamanho = 120 }: MiniMapaProps) {
  const cores = coresDoMapa(useEsquemaDeCor());
  const geo = geometria(pontos, Math.round(tamanho));
  const coordenada = destaque ? pontos.get(destaque) : undefined;
  const alvo = coordenada && coordenadaValida(coordenada[0], coordenada[1]) ? noMiniMapa(geo, coordenada[0], coordenada[1]) : null;
  const moldura = enquadramento ? retanguloNoMiniMapa(geo, enquadramento) : null;
  const rotulo = enquadramento ? "Mapinha: o retângulo mostra a área à vista no mapa" : alvo ? "Mapinha: onde fica o ponto destacado" : "Mapinha";
  return <svg data-testid="minimapa" data-destaque={alvo ? destaque ?? "" : ""} data-enquadramento={moldura ? "true" : undefined}
    width={geo.largura} height={geo.altura} viewBox={`0 0 ${geo.largura} ${geo.altura}`} role="img" aria-label={rotulo}
    style={{ display: "block", flexShrink: 0 }}>
    <rect x={0.5} y={0.5} width={geo.largura - 1} height={geo.altura - 1} rx={6} fill={cores.superficie} stroke={cores.borda}/>
    <Pontos caminho={geo.caminho} cor={cores.miniPontos}/>
    {moldura && <rect data-testid="minimapa-moldura" x={moldura.x} y={moldura.y} width={moldura.largura} height={moldura.altura}
      fill={cores.tinta} fillOpacity={0.06} stroke={cores.tinta} strokeWidth={1.25}/>}
    {alvo && <circle data-testid="minimapa-destaque" cx={alvo[0]} cy={alvo[1]} r={3.5} fill={cores.tinta}
      stroke={cores.superficie} strokeWidth={1.5}/>}
  </svg>;
}
