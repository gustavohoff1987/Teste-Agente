import { memo, useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent as EventoMouse,
  type PointerEvent as EventoPonteiro, type ReactNode, type RefObject } from "react";
import type { GraficoComMapaProps } from "./mapaContrato";
import MiniMapa from "./MiniMapa";
import type { PainelIndicador, PainelItem, PainelResposta } from "./painelApi";
import {
  INDICADORES, LIMITE_LEVE, caudaDoCometa, exibirCompetencia, formatarNumero, formatarVariacao, larguraDoTexto, legendaDeTamanhos,
  montarDica, montarGrafico, paletaDoGrafico, posicaoNoEixo, posicionarRotulos, type BolhaDesenho, type Corte, type Escala,
  type PaletaDoGrafico, type Pintura, type RotulosTerritoriais, type Vista,
} from "./painelModel";
import { useEsquemaDeCor } from "./useEsquemaDeCor";

// Gráfico de bolhas da área de análise. O eixo Y é sempre o indicador (decisão do responsável, 22/10/2026). Sem a análise
// espacial, as bolhas se espalham na horizontal só como arranjo; com ela, X é a distância até a referência. Só desenha o que o
// modelo posicionou a partir da resposta do motor. Marcas finas com anel de 2 px na cor da superfície, alvo de pelo menos
// 24 px, dica ao passar o mouse e ao focar, rótulos diretos seletivos (texto em tinta, nunca na cor da série) e navegação pelas
// setas. Com muitas bolhas (modo leve, acima de LIMITE_LEVE), as posições valem para todos os itens, numa faixa limitada; a
// régua só esconde. Uma camada de círculos simples desenha a massa; só as bolhas em destaque ganham o desenho completo.
// Com o mapa (23/10/2026): com `pontosDoMapa`, a dica da unidade com ponto mostra o mapinha ("onde fica?"); `ativoExterno` dá o
// anel à bolha do item sob o mouse no mapa (lado a lado), e `onAtivo` avisa a área quando a bolha ativa muda. Modo escuro
// (23/10/2026): superfície, tintas, grade e eixo vêm da paleta do esquema de cor do aparelho (paletaDoGrafico); a impressão é
// sempre clara.

/** Largura do contêiner em pixels (ignora larguras nulas de uma área oculta). */
export function useLargura(inicial = 900): [RefObject<HTMLElement>, number] {
  const ref = useRef<HTMLElement>(null);
  const [largura, setLargura] = useState(inicial);
  useEffect(() => {
    const elemento = ref.current;
    if (!elemento) return;
    const medir = () => { if (elemento.clientWidth > 0) setLargura(elemento.clientWidth); };
    medir();
    if (typeof ResizeObserver === "undefined") return;
    const observador = new ResizeObserver(medir);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, []);
  return [ref, largura];
}

export type FaseAnimacao = "parado" | "preparar" | "tocar";
export type LinhaDeReferencia = { valor: number; rotulo: string };
type Props = {
  resposta: PainelResposta;
  /** Itens desenháveis e dentro da régua e dos filtros, na ordem neutra. */
  itens: PainelItem[];
  /** Todos os itens desenháveis, antes da régua: no modo leve, as posições valem para todos e a régua só esconde. */
  todos: PainelItem[];
  indicador: PainelIndicador;
  escala: Escala;
  distancia: boolean;
  cometa: boolean;
  vista: Vista;
  fase: FaseAnimacao;
  pintura: (item: PainelItem) => Pintura;
  selecionados: string[];
  limiares: number[];
  nomes: Map<string, string>;
  carregando: boolean;
  rotuloDistancia: string;
  rotulos: RotulosTerritoriais;
  /** Linha de contexto do Brasil (densidade), que não classifica nada. */
  contextoBrasil: LinhaDeReferencia | null;
  /** Cortes dos grupos (do motor) ou limites das faixas (digitados), no eixo do indicador. */
  cortes: LinhaDeReferencia[];
  corte: Corte | null;
  faixasDistancia: LinhaDeReferencia[];
  /** Texto extra do rótulo direto (por exemplo, a posição "1º" na ordenação). */
  extraDoRotulo?: (item: PainelItem) => string | null;
  /** Bolhas com rótulo direto sempre (as siglas dos estados, os N primeiros). */
  rotuloSempre?: (item: PainelItem) => boolean;
  unidadesDoGrupo: (id: string) => number | null;
  legendaCor: ReactNode;
  notas: string[];
  onAlternar: (id: string) => void;
  onAbrirGrupo: (id: string) => void;
} & GraficoComMapaProps;

const siglaDe = (item: PainelItem) => item.uf || (/\(([^()]+)\)\s*$/.exec(item.rotulo) || [])[1] || item.rotulo;

export default function PainelChart(p: Props) {
  const [ref, largura] = useLargura();
  const paleta = paletaDoGrafico(useEsquemaDeCor());
  const [ativo, setAtivo] = useState<string | null>(null);
  const [foco, setFoco] = useState<string | null>(null);
  // A bolha ativa (mouse ou foco) é avisada à área só quando muda; ao sair da tela, o aviso de que nada está ativo.
  const aoAtivar = useRef(p.onAtivo);
  aoAtivar.current = p.onAtivo;
  const avisado = useRef<string | null>(null);
  useEffect(() => {
    if (ativo === avisado.current) return;
    avisado.current = ativo;
    aoAtivar.current?.(ativo);
  }, [ativo]);
  useEffect(() => () => { if (avisado.current !== null) aoAtivar.current?.(null); }, []);
  const externo = p.ativoExterno ?? null;
  const elementos = useRef(new Map<string, SVGGElement>());
  const focarDepois = useRef<string | null>(null);
  const leve = p.todos.length > LIMITE_LEVE;
  const desenhaveis = leve ? p.todos : p.itens;
  const extras = useMemo(() => p.contextoBrasil ? [p.contextoBrasil.valor] : [], [p.contextoBrasil]);
  const grafico = useMemo(() => montarGrafico({ itens: desenhaveis, dominios: p.resposta.dominios, indicador: p.indicador, escala: p.escala,
    distancia: p.distancia, cometa: p.cometa, vista: p.vista, largura, rotuloDistancia: p.rotuloDistancia, pintura: p.pintura, extras,
    denso: leve }),
  [desenhaveis, p.resposta.dominios, p.indicador, p.escala, p.distancia, p.cometa, p.vista, largura, p.rotuloDistancia, p.pintura, extras, leve]);
  // Modo leve: a régua só esconde (as posições não mudam); no modo normal, o gráfico já recebe só os itens do corte.
  const dentro = useMemo(() => leve ? new Set(p.itens.map(item => item.id)) : null, [leve, p.itens]);
  const desenhada = useCallback((bolha: BolhaDesenho) => bolha.visivel && (!dentro || dentro.has(bolha.id)), [dentro]);
  const selecionados = useMemo(() => new Set(p.selecionados), [p.selecionados]);
  const destaque = p.selecionados.length > 0;
  const competenciaInicial = p.resposta.competencia_inicial || null;
  const especie = INDICADORES[p.indicador];

  // Uma parada de tabulação no gráfico; as setas percorrem as bolhas (de cima para baixo no eixo único; da esquerda para a
  // direita com a distância).
  const navegaveis = useMemo(() => grafico.bolhas.filter(desenhada).sort((a, b) => p.distancia
    ? a.x - b.x || a.y - b.y || a.id.localeCompare(b.id, "pt-BR", { numeric: true })
    : a.y - b.y || a.x - b.x || a.id.localeCompare(b.id, "pt-BR", { numeric: true })), [grafico, desenhada, p.distancia]);
  const focoEfetivo = navegaveis.some(bolha => bolha.id === foco) ? foco : navegaveis[0]?.id ?? null;
  useEffect(() => {
    if (!focarDepois.current) return;
    elementos.current.get(focarDepois.current)?.focus();
    focarDepois.current = null;
  });
  const ativarLeve = useCallback((id: string | null) => setAtivo(atual => atual === id ? atual : id), []);

  const textoDoRotulo = (bolha: BolhaDesenho) => {
    if (bolha.tipo === "estado") return siglaDe(bolha.item);
    const nome = bolha.item.rotulo + (bolha.tipo === "conjunto" ? " (soma)" : "");
    const extra = p.extraDoRotulo?.(bolha.item);
    if (extra) return extra + " " + nome;
    if (p.vista === "inicial" && p.cometa) return nome + " · " + exibirCompetencia(competenciaInicial);
    if (p.cometa && bolha.variacao !== null) return nome + " · " + formatarVariacao(bolha.variacao);
    if (bolha.referencia) return nome + " · referência";
    return nome + " · " + formatarNumero(bolha.valor, especie.contagem, p.limiares);
  };
  const rotulados = grafico.bolhas.filter(bolha => desenhada(bolha) && (selecionados.has(bolha.id) || bolha.tipo === "conjunto" ||
    bolha.referencia || bolha.id === ativo || !!p.rotuloSempre?.(bolha.item)));
  const rotulos = posicionarRotulos(rotulados.map(bolha => ({ id: bolha.id, x: bolha.x, y: bolha.y, r: bolha.r,
    largura: larguraDoTexto(textoDoRotulo(bolha)) })), grafico.largura - 4);
  // Ordem de desenho estável: as mais populosas atrás. Não depende do mouse, do foco nem do destaque.
  const ordem = useMemo(() => [...grafico.bolhas].sort((a, b) => (b.item.populacao ?? -1) - (a.item.populacao ?? -1) ||
    a.id.localeCompare(b.id, "pt-BR", { numeric: true })), [grafico]);
  const opacidadeDe = (bolha: BolhaDesenho) => !bolha.visivel ? 0
    : destaque && !selecionados.has(bolha.id) && bolha.id !== ativo && bolha.id !== externo ? 0.22 : bolha.apagada ? 0.45 : 1;
  const bolhaAtiva = ativo ? grafico.bolhas.find(bolha => bolha.id === ativo && desenhada(bolha)) : undefined;
  const especiais = leve ? ordem.filter(bolha => desenhada(bolha) && (selecionados.has(bolha.id) || bolha.tipo === "conjunto" ||
    bolha.referencia || bolha.id === ativo || bolha.id === externo || bolha.id === focoEfetivo)) : [];
  const dica = bolhaAtiva ? montarDica(bolhaAtiva.item, { indicador: p.indicador, competencia: p.resposta.competencia,
    competenciaInicial, distancia: p.distancia, variacao: p.cometa && !!competenciaInicial, tendencia: !!bolhaAtiva.item.tendencia,
    nomes: p.nomes, limiares: p.limiares, rotulos: p.rotulos, unidadesDoGrupo: p.unidadesDoGrupo }) : null;

  function acionar(bolha: BolhaDesenho) {
    if (bolha.tipo === "estado") p.onAbrirGrupo(bolha.id);
    else p.onAlternar(bolha.id);
  }
  function teclado(event: KeyboardEvent<SVGGElement>, bolha: BolhaDesenho) {
    const indice = navegaveis.findIndex(item => item.id === bolha.id);
    let alvo: string | null = null;
    if (event.key === "ArrowRight" || event.key === "ArrowDown") alvo = navegaveis[Math.min(navegaveis.length - 1, indice + 1)]?.id ?? null;
    else if (event.key === "ArrowLeft" || event.key === "ArrowUp") alvo = navegaveis[Math.max(0, indice - 1)]?.id ?? null;
    else if (event.key === "Home") alvo = navegaveis[0]?.id ?? null;
    else if (event.key === "End") alvo = navegaveis[navegaveis.length - 1]?.id ?? null;
    else if (event.key === "Enter" || event.key === " ") { event.preventDefault(); acionar(bolha); return; }
    else if (event.key === "Escape") { setAtivo(null); return; }
    if (!alvo) return;
    event.preventDefault();
    setFoco(alvo);
    focarDepois.current = alvo;
    elementos.current.get(alvo)?.focus();
  }

  const descricao = (bolha: BolhaDesenho) => {
    const partes = [bolha.item.rotulo, especie.rotulo + " " + formatarNumero(bolha.valor, especie.contagem, p.limiares) + " " + especie.unidade];
    if (bolha.item.populacao !== null) partes.push("população " + formatarNumero(bolha.item.populacao, true));
    if (p.distancia && bolha.item.distancia_km !== null) partes.push("distância " + formatarNumero(bolha.item.distancia_km) + " km");
    if (p.cometa && competenciaInicial) partes.push("variação " + formatarVariacao(bolha.variacao));
    if (bolha.item.tendencia) partes.push("tendência: " + bolha.item.tendencia.rotulo);
    if (bolha.tipo === "conjunto") partes.push("soma das contagens dos componentes");
    if (bolha.tipo === "estado") {
      const n = p.unidadesDoGrupo(bolha.id);
      partes.push("Enter para ver " + (n !== null ? n + " " : "") + p.rotulos.unidade.plural);
    }
    return partes.join("; ");
  };
  const larguraDica = Math.min(270, grafico.largura - 16);
  // Mapinha na dica: só da unidade com ponto no mapa (estados e conjuntos não têm ponto).
  const miniNaDica = !!bolhaAtiva && bolhaAtiva.tipo === "municipio" && !!p.pontosDoMapa?.has(bolhaAtiva.id);
  const posicaoDica = bolhaAtiva ? {
    left: Math.max(4, bolhaAtiva.x + bolhaAtiva.r + 12 + larguraDica > grafico.largura ? bolhaAtiva.x - bolhaAtiva.r - 12 - larguraDica : bolhaAtiva.x + bolhaAtiva.r + 12),
    top: Math.max(4, Math.min(grafico.altura - (miniNaDica ? 244 : 140), bolhaAtiva.y - 16)),
  } : null;
  const classe = "analise-svg" + (leve ? " analise-leve-svg" : (p.fase === "preparar" ? " analise-sem-transicao" : "") +
    (p.fase === "tocar" ? " analise-reproduzindo" : ""));
  const eixoX = grafico.eixoX, eixoY = grafico.eixoY;
  const esquerdaPlot = grafico.esquerda, direitaPlot = grafico.largura - grafico.direita;
  const temConjunto = grafico.bolhas.some(bolha => bolha.tipo === "conjunto"), temReferencia = grafico.bolhas.some(bolha => bolha.referencia);
  const temVazada = grafico.bolhas.some(bolha => bolha.vazada && bolha.visivel);
  const simbolos = [temConjunto ? "anel escuro: conjunto (soma das contagens dos componentes, com possível dupla contagem)" : "",
    temReferencia ? "mira: membro da referência (distância 0)" : "",
    temConjunto && p.distancia ? "traço horizontal: do membro mais próximo ao mais distante do conjunto" : "",
    p.cometa ? "rastro: do valor na competência inicial (círculo vazado) até a atual" : "",
    temVazada ? "bolha vazada tracejada: valor não avaliável nesta camada (veja Não avaliáveis)" : ""]
    .filter(Boolean).join("; ").replace(/^./, letra => letra.toUpperCase());
  const linhaH = (valor: number) => posicaoNoEixo(eixoY, valor);
  const dentroDoEixo = (valor: number) => valor >= eixoY.dominio[0] && valor <= eixoY.dominio[1];

  const desenharBolha = (bolha: BolhaDesenho, testid: string, interativa: boolean) => {
    const selecionado = selecionados.has(bolha.id);
    const gradiente = "analise-cometa-" + bolha.id.replace(/[^a-zA-Z0-9_-]/g, "_");
    return <g key={bolha.id} ref={elemento => { if (elemento) elementos.current.set(bolha.id, elemento); else elementos.current.delete(bolha.id); }}
      className={"analise-bolha" + (bolha.tipo === "estado" ? " analise-bolha-grupo" : "")} data-testid={testid} data-id={bolha.id}
      data-tipo={bolha.tipo} data-valor={String(bolha.valor)} data-populacao={bolha.item.populacao ?? ""}
      data-distancia={p.distancia ? String(bolha.item.distancia_km ?? "") : undefined}
      data-variacao={p.cometa && bolha.variacao !== null ? String(bolha.variacao) : undefined}
      data-classe={bolha.item.tendencia ? bolha.item.tendencia.classe ?? "NAO_AVALIAVEL" : undefined}
      data-grupo={bolha.item.grupo ? String(bolha.item.grupo.indice) : undefined}
      data-faixa={bolha.item.faixa ? (bolha.item.faixa === "fora" ? "fora" : String(bolha.item.faixa.indice)) : undefined}
      data-condicao={bolha.item.condicoes?.situacao} data-posicao={bolha.item.ordem?.posicao ?? undefined}
      data-referencia={bolha.referencia ? "true" : undefined} data-selecionado={selecionado ? "true" : undefined}
      data-visivel={bolha.visivel ? "true" : "false"}
      style={{ transform: `translate(${bolha.x}px, ${bolha.y}px)`, opacity: opacidadeDe(bolha), pointerEvents: bolha.visivel && interativa ? undefined : "none" }}
      role="button" tabIndex={bolha.visivel && focoEfetivo === bolha.id ? 0 : -1} aria-pressed={bolha.tipo === "estado" ? undefined : selecionado}
      aria-label={descricao(bolha)} aria-hidden={bolha.visivel ? undefined : true} aria-describedby={ativo === bolha.id ? "analise-dica" : undefined}
      onPointerEnter={() => setAtivo(bolha.id)} onPointerLeave={() => setAtivo(atual => atual === bolha.id ? null : atual)}
      onFocus={() => { setFoco(bolha.id); setAtivo(bolha.id); }} onBlur={() => setAtivo(atual => atual === bolha.id ? null : atual)}
      onClick={() => acionar(bolha)} onKeyDown={event => teclado(event, bolha)}>
      {bolha.rastro && <g key={bolha.rastro.dx.toFixed(1) + ":" + bolha.rastro.dy.toFixed(1)} className="analise-rastro" data-testid="analise-rastro" aria-hidden="true">
        <defs>
          <linearGradient id={gradiente} gradientUnits="userSpaceOnUse" x1={bolha.rastro.dx} y1={bolha.rastro.dy} x2={0} y2={0}>
            <stop offset="0" stopColor={bolha.vazada ? paleta.naoAvaliavel : bolha.cor} stopOpacity={0}/>
            <stop offset="1" stopColor={bolha.vazada ? paleta.naoAvaliavel : bolha.cor} stopOpacity={0.6}/>
          </linearGradient>
        </defs>
        <polygon points={caudaDoCometa(bolha.rastro.dx, bolha.rastro.dy, bolha.r)} fill={`url(#${gradiente})`}/>
        <circle cx={bolha.rastro.dx} cy={bolha.rastro.dy} r={3.5} fill={paleta.superficie} stroke={bolha.vazada ? paleta.naoAvaliavel : bolha.cor} strokeWidth={1.5}/>
      </g>}
      {bolha.faixa && <g aria-hidden="true">
        <line x1={0} x2={bolha.faixa.dx} y1={0} y2={0} stroke={paleta.tinta2} strokeWidth={1.5} strokeLinecap="round"/>
        <line x1={bolha.faixa.dx} x2={bolha.faixa.dx} y1={-5} y2={5} stroke={paleta.tinta2} strokeWidth={1.5} strokeLinecap="round"/>
      </g>}
      <circle className="analise-marca" r={bolha.r} fill={bolha.cor} fillOpacity={bolha.vazada ? 1 : 0.88}
        stroke={bolha.vazada ? paleta.naoAvaliavel : paleta.superficie} strokeWidth={bolha.vazada ? 1.5 : 2} strokeDasharray={bolha.vazada ? "3 2" : undefined}/>
      {bolha.tipo === "conjunto" && <circle r={bolha.r + 4} fill="none" stroke={paleta.tinta} strokeOpacity={0.7} strokeWidth={1.25}/>}
      {bolha.referencia && <path d={`M${-(bolha.r + 9)} 0H${-(bolha.r + 3)}M${bolha.r + 3} 0H${bolha.r + 9}M0 ${-(bolha.r + 9)}V${-(bolha.r + 3)}M0 ${bolha.r + 3}V${bolha.r + 9}`}
        stroke={paleta.tinta} strokeWidth={1.5} strokeLinecap="round"/>}
      {(selecionado || ativo === bolha.id || externo === bolha.id) && <circle r={bolha.r + 2} fill="none" stroke={paleta.tinta} strokeWidth={2}/>}
      <circle className="analise-alvo" r={Math.max(bolha.r + 2, 12)} fill="transparent"/>
    </g>;
  };

  const notaArranjo = !p.distancia ? (grafico.arranjo === "exato"
    ? "Eixo vertical: " + especie.rotulo.toLowerCase() + ". A posição horizontal é só arranjo, para as bolhas não se sobreporem; ela não carrega valor."
    : "Eixo vertical: " + especie.rotulo.toLowerCase() + ". A posição horizontal é só arranjo, numa faixa limitada: com muitas bolhas, elas " +
      "ficam semitransparentes e podem se sobrepor. Passe o mouse ou use as setas para ver cada uma.") : null;

  return <figure ref={ref} data-testid="analise-grafico" data-modo={leve ? "leve" : "completo"} data-arranjo={grafico.arranjo}
    data-desenhadas={navegaveis.length} className={"analise-grafico" + (p.carregando ? " analise-grafico-carregando" : "")} aria-busy={p.carregando || undefined}>
    <svg viewBox={`0 0 ${grafico.largura} ${grafico.altura}`} width="100%" height={grafico.altura} role="group" className={classe}
      aria-label={"Bolhas do gráfico: " + (eixoX ? "distância até a referência no eixo horizontal e " + especie.rotulo.toLowerCase() + " no vertical"
        : especie.rotulo.toLowerCase() + " no eixo vertical; a posição horizontal é só arranjo") + ". Tamanho: população. Use as setas para percorrer as bolhas e Enter para " +
        (grafico.bolhas.some(bolha => bolha.tipo === "estado") ? "ver " + p.rotulos.unidade.plural + "." : "destacar.")}>
      {/* Grade recessiva: linhas finas, sólidas, um tom acima da superfície. */}
      {eixoY.marcas.map(marca => <line key={"gy" + marca.valor} x1={esquerdaPlot} x2={direitaPlot} y1={marca.pos} y2={marca.pos} stroke={paleta.grade} strokeWidth={1}/>)}
      {eixoX?.marcas.map(marca => <line key={"gx" + marca.valor} x1={marca.pos} x2={marca.pos} y1={grafico.topo} y2={grafico.base} stroke={paleta.grade} strokeWidth={1}/>)}
      <g data-testid="analise-eixo-y" data-eixo={eixoY.tipo} data-escala={eixoY.escala} data-dominio={eixoY.dominio.join(",")} aria-hidden="true">
        <line x1={esquerdaPlot} x2={esquerdaPlot} y1={grafico.topo} y2={grafico.base} stroke={paleta.eixo} strokeWidth={1}/>
        {eixoY.marcas.map(marca => <text key={marca.valor} x={esquerdaPlot - 6} y={marca.pos + 4} textAnchor="end" className="analise-marca-texto">{marca.texto}</text>)}
        <text transform={`translate(14 ${(grafico.topo + grafico.base) / 2}) rotate(-90)`} textAnchor="middle" className="analise-eixo-titulo">
          {eixoY.rotulo}{eixoY.escala === "logaritmica" ? " · escala logarítmica" : ""}</text>
      </g>
      {eixoX && <g data-testid="analise-eixo-x" data-eixo={eixoX.tipo} data-escala={eixoX.escala} data-dominio={eixoX.dominio.join(",")} aria-hidden="true">
        <line x1={esquerdaPlot} x2={direitaPlot} y1={grafico.base} y2={grafico.base} stroke={paleta.eixo} strokeWidth={1}/>
        {eixoX.marcas.map(marca => <text key={marca.valor} x={marca.pos} y={grafico.base + 16} textAnchor="middle" className="analise-marca-texto">{marca.texto}</text>)}
        <text x={(esquerdaPlot + direitaPlot) / 2} y={grafico.base + 38} textAnchor="middle" className="analise-eixo-titulo">{eixoX.rotulo}</text>
      </g>}
      {/* Linhas de referência: o contexto do Brasil (não classifica), os cortes dos grupos ou os limites das faixas, a régua e
          as faixas de distância. Todas finas e sólidas, com o texto em tinta. */}
      {p.contextoBrasil && dentroDoEixo(p.contextoBrasil.valor) && <g data-testid="analise-contexto-brasil" data-valor={p.contextoBrasil.valor} aria-hidden="true">
        <line x1={esquerdaPlot} x2={direitaPlot} y1={linhaH(p.contextoBrasil.valor)} y2={linhaH(p.contextoBrasil.valor)} stroke={paleta.tinta2} strokeWidth={1}/>
        <text x={direitaPlot - 2} y={linhaH(p.contextoBrasil.valor) - 5} textAnchor="end" className="analise-linha-texto">{p.contextoBrasil.rotulo}</text>
      </g>}
      {p.cortes.filter(item => dentroDoEixo(item.valor)).map((item, indice) => <g key={"c" + indice} data-testid="analise-corte" data-valor={item.valor} aria-hidden="true">
        <line x1={esquerdaPlot} x2={direitaPlot} y1={linhaH(item.valor)} y2={linhaH(item.valor)} stroke={paleta.eixo} strokeWidth={1}/>
        <text x={esquerdaPlot + 4} y={linhaH(item.valor) - 4} className="analise-linha-texto analise-linha-texto-leve">{item.rotulo}</text>
      </g>)}
      {p.corte && [p.corte.minimo, p.corte.maximo].filter(dentroDoEixo).map((valor, indice) => <line key={"r" + indice} data-testid="analise-corte-regua"
        x1={esquerdaPlot} x2={direitaPlot} y1={linhaH(valor)} y2={linhaH(valor)} stroke={paleta.tinta} strokeOpacity={0.55} strokeWidth={1} aria-hidden="true"/>)}
      {eixoX && p.faixasDistancia.filter(item => item.valor >= eixoX.dominio[0] && item.valor <= eixoX.dominio[1]).map((item, indice) =>
        <g key={"fd" + indice} data-testid="analise-faixa-distancia" aria-hidden="true">
          <line x1={posicaoNoEixo(eixoX, item.valor)} x2={posicaoNoEixo(eixoX, item.valor)} y1={grafico.topo} y2={grafico.base} stroke={paleta.eixo} strokeWidth={1}/>
          <text x={posicaoNoEixo(eixoX, item.valor) + 4} y={grafico.topo + 12} className="analise-linha-texto analise-linha-texto-leve">{item.rotulo}</text>
        </g>)}
      {leve ? <>
        <CamadaLeve bolhas={ordem} dentro={dentro!} cometa={p.cometa} distancia={p.distancia} esmaecida={destaque} paleta={paleta}
          onAtivar={ativarLeve} onAcionar={id => { const bolha = grafico.bolhas.find(item => item.id === id); if (bolha) acionar(bolha); }}/>
        {especiais.map(bolha => desenharBolha(bolha, "analise-bolha-destaque",
          selecionados.has(bolha.id) || bolha.tipo === "conjunto" || bolha.referencia || bolha.id === focoEfetivo))}
      </> : ordem.map(bolha => desenharBolha(bolha, "analise-bolha", true))}
      <g className="analise-rotulos" aria-hidden="true" pointerEvents="none">
        {ordem.filter(bolha => rotulos.has(bolha.id)).map(bolha => {
          const rotulo = rotulos.get(bolha.id)!;
          return <g key={bolha.id} className="analise-rotulo-grupo" data-id={bolha.id}
            style={{ transform: `translate(${bolha.x}px, ${bolha.y}px)`, opacity: opacidadeDe(bolha) }}>
            <text x={rotulo.dx} y={rotulo.dy + 4} textAnchor={rotulo.ancora} className="analise-rotulo">{textoDoRotulo(bolha)}</text>
          </g>;
        })}
      </g>
    </svg>
    {(leve ? !navegaveis.length : !grafico.bolhas.length) && <p role="status" className="analise-grafico-vazio">
      Nenhuma bolha para desenhar: os itens ficaram fora da régua ou dos filtros, ou não têm valor avaliável (veja Não avaliáveis, em Detalhes).</p>}
    {dica && posicaoDica && <div role="tooltip" id="analise-dica" data-testid="analise-dica" className="analise-dica"
      style={{ left: posicaoDica.left, top: posicaoDica.top, width: larguraDica }}>
      <strong className="block text-sm text-ink">{dica.titulo}</strong>
      <span className="block text-[11px] text-slate-600">{dica.subtitulo}</span>
      {dica.acao && <span data-testid="analise-dica-acao" className="analise-dica-acao">{dica.acao} ›
        <span className="block font-normal text-slate-600">Clique na bolha ou tecle Enter.</span></span>}
      <dl className="mt-1.5 space-y-0.5">
        {dica.linhas.map(linha => <div key={linha.rotulo} className="flex flex-col">
          <dt className="sr-only">{linha.rotulo}</dt>
          <dd className="text-xs"><span className="font-semibold text-ink">{linha.valor}</span> <span className="text-slate-500">· {linha.rotulo}</span></dd>
        </div>)}
      </dl>
      {dica.notas.map(nota => <p key={nota} className="mt-1 text-[11px] leading-4 text-slate-600">{nota}</p>)}
      {miniNaDica && <div className="mt-1.5"><MiniMapa pontos={p.pontosDoMapa!} destaque={bolhaAtiva!.id} tamanho={96}/></div>}
    </div>}
    <figcaption className="analise-legenda">
      <LegendaDeTamanho maxima={grafico.populacaoMaxima} raioMax={grafico.raioMax} paleta={paleta}/>
      {p.legendaCor}
      <div className="min-w-0 max-w-xl space-y-1">
        {notaArranjo && <p data-testid="analise-arranjo-nota">{notaArranjo}</p>}
        {eixoY && eixoX && <p>Horizontal: distância até a referência, do motor; vertical: {especie.rotulo.toLowerCase()}. Sem reta de tendência nem
          correlação: cada bolha é só um par de valores.{leve ? " Com muitas bolhas, elas ficam semitransparentes e podem se sobrepor." : ""}</p>}
        {simbolos && <p data-testid="analise-simbolos">{simbolos}.</p>}
        {p.notas.map(nota => <p key={nota}>{nota}</p>)}
      </div>
    </figcaption>
  </figure>;
}

/** Legenda de tamanho: três populações de referência com o mesmo raio do gráfico (área proporcional à população). */
function LegendaDeTamanho({ maxima, raioMax, paleta }: { maxima: number; raioMax: number; paleta: PaletaDoGrafico }) {
  const tamanhos = legendaDeTamanhos(maxima, raioMax);
  if (!tamanhos.length) return null;
  const maior = Math.max(...tamanhos.map(item => item.raio));
  const base = Math.ceil(2 * maior + 6), larguraTexto = 78;
  let anterior = -Infinity;
  const posicoes = tamanhos.map(item => {
    const cy = base - 2 - item.raio, topo = cy - item.raio, y = Math.max(topo + 4, anterior + 12);
    anterior = y;
    return { item, cy, topo, y };
  });
  const altura = Math.max(base, Math.ceil(anterior + 4));
  return <div data-testid="analise-legenda-tamanho" aria-label={"Tamanho: população. Referências: " + tamanhos.map(item => item.texto).join(", ")}
    className="flex items-end gap-2">
    <svg width={2 * maior + 10 + larguraTexto} height={altura} aria-hidden="true" className="overflow-visible">
      {posicoes.map(({ item, cy, topo, y }) => <g key={item.valor} data-testid="analise-legenda-tamanho-item" data-valor={item.valor} data-raio={item.raio.toFixed(2)}>
        <circle cx={maior + 2} cy={cy} r={item.raio} fill="none" stroke={paleta.tinta2} strokeWidth={1}/>
        <line x1={maior + 2} x2={2 * maior + 8} y1={topo} y2={y - 4} stroke={paleta.eixo} strokeWidth={1}/>
        <text x={2 * maior + 11} y={y} className="analise-marca-texto">{item.texto}</text>
      </g>)}
    </svg>
    <span className="max-w-[9rem] leading-4">Área proporcional à população; as muito pequenas ficam no tamanho mínimo visível.</span>
  </div>;
}

type CamadaProps = {
  bolhas: BolhaDesenho[]; dentro: Set<string>; cometa: boolean; distancia: boolean; esmaecida: boolean; paleta: PaletaDoGrafico;
  onAtivar: (id: string | null) => void; onAcionar: (id: string) => void;
};

/** Modo leve: um círculo simples por bolha (e uma linha fina por rastro), com os mesmos atributos de dados e um único conjunto de
 * eventos no grupo. Não depende do mouse, do foco nem da seleção: passar o mouse não redesenha os milhares de círculos. Fora da
 * régua, o círculo só fica oculto. */
const CamadaLeve = memo(function CamadaLeve({ bolhas, dentro, cometa, distancia, esmaecida, paleta, onAtivar, onAcionar }: CamadaProps) {
  const alvo = (event: EventoPonteiro<SVGGElement> | EventoMouse<SVGGElement>) =>
    (event.target as Element).closest?.("[data-id]")?.getAttribute("data-id") ?? null;
  return <g data-testid="analise-camada-leve" className="analise-camada-leve" style={{ opacity: esmaecida ? 0.3 : 1 }}
    onPointerMove={event => onAtivar(alvo(event))} onPointerLeave={() => onAtivar(null)}
    onClick={event => { const id = alvo(event); if (id) onAcionar(id); }}>
    {cometa && bolhas.map(bolha => bolha.rastro && <line key={"r" + bolha.id} x1={bolha.x + bolha.rastro.dx} y1={bolha.y + bolha.rastro.dy}
      x2={bolha.x} y2={bolha.y} stroke={bolha.vazada ? paleta.naoAvaliavel : bolha.cor} strokeOpacity={0.5} strokeWidth={1.5} strokeLinecap="round" aria-hidden="true"
      display={bolha.visivel && dentro.has(bolha.id) ? undefined : "none"}/>)}
    {bolhas.map(bolha => {
      const visivel = bolha.visivel && dentro.has(bolha.id);
      return <circle key={bolha.id} data-testid="analise-bolha" data-id={bolha.id} data-tipo={bolha.tipo} data-valor={String(bolha.valor)}
        data-populacao={bolha.item.populacao ?? ""} data-distancia={distancia ? String(bolha.item.distancia_km ?? "") : undefined}
        data-variacao={cometa && bolha.variacao !== null ? String(bolha.variacao) : undefined}
        data-classe={bolha.item.tendencia ? bolha.item.tendencia.classe ?? "NAO_AVALIAVEL" : undefined}
        data-grupo={bolha.item.grupo ? String(bolha.item.grupo.indice) : undefined}
        data-condicao={bolha.item.condicoes?.situacao} data-visivel={visivel ? "true" : "false"}
        cx={bolha.x} cy={bolha.y} r={bolha.r} fill={bolha.cor} fillOpacity={bolha.vazada ? 1 : bolha.apagada ? 0.35 : 0.62}
        stroke={bolha.vazada ? paleta.naoAvaliavel : paleta.superficie} strokeWidth={bolha.vazada ? 1 : 0.75} strokeDasharray={bolha.vazada ? "2 1.5" : undefined}
        display={visivel ? undefined : "none"} aria-hidden="true"/>;
    })}
  </g>;
});
