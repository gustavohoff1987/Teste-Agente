import { forwardRef, memo, useCallback, useEffect, useId, useImperativeHandle, useLayoutEffect, useMemo, useRef, useState,
  type CSSProperties, type KeyboardEvent } from "react";
import { Expand, Minus, Plus, Search } from "lucide-react";
import type { DadosDoMapa, MapaHandle, MapaProps, Posicoes } from "./mapaContrato";
import type { PainelIndicador } from "./painelApi";
import { artigo, compacto, formatarNumero, generoDe, maiuscula, textoDaMarca, umA, type Dica, type RotulosTerritoriais } from "./painelModel";
import MiniMapa from "./MiniMapa";
import { useNarrow } from "./useNarrow";
import { useEsquemaDeCor } from "./useEsquemaDeCor";
import {
  ALVO_MOUSE, ALVO_TOQUE, LIMITE_NOMES_TODOS, OPACIDADE_APAGADA, RAIO_FUNDO, alvoMaisProximo, areaVisivel, baseDoMapa, coresDoMapa,
  assinaturaDe, deslocar, enquadrar, escalaEfetiva, gradienteDaRampa, limitesComContexto, limitesComReferencias, limitesDe, marcasDaLegenda,
  marcasDeTamanho, montarCena, paraTela,
  posicaoDoContexto, posicionarNomes, projetar, rampaContinua, segmentosDasLigacoes, vizinhoNaDirecao, zoomEm, type Caixa, type Cena,
  type CoresDoMapa, type Direcao, type EscalaDeCor, type PedidoDeNome, type PontoDaCena, type Vista,
} from "./mapaModel";
import "./mapa.css";

// Mapa da página única (23/10/2026): segunda vista do gráfico de bolhas, com a mesma análise. Reaproveita o mapa antigo
// (TerritoryMap, até 22/10/2026): canvas sem serviço externo, projeção equirretangular só para desenhar, pontos em lotes,
// zoom, arrasto, pinça, duplo clique, teclado, alvo ampliado e nomes que não se cobrem. Cada ponto é a sede do município
// (IBGE) na base do Brasil, ou a coordenada da planilha; o mapa só desenha o que o motor devolveu (RQ-REP-09) e não mede
// distância. Tamanho com área proporcional; cor da camada do gráfico, dos 5 grupos iguais (quintis) do motor quando a análise
// não tem cor própria (23/10/2026, sem a pergunta "Como pintar o mapa?") ou, na rotatividade, contínua. O enquadramento inicial
// tem contexto em volta dos pontos (limitesComContexto). A régua e os filtros esmaecem, nunca escondem. Arrasto, zoom e o ponto sob o
// mouse redesenham sob requestAnimationFrame, sem estado React a cada movimento; a dica e o mapinha do canto são filhos com
// estado próprio. Trocar de vista, navegar e marcar são estado visual (RQ-REP-06). Modo escuro (23/10/2026): as cores vêm do
// esquema do aparelho (coresDoMapa e rampaContinua); na troca de esquema e no começo da impressão (sempre clara), o canvas é
// redesenhado na hora.

type Tamanho = { w: number; h: number; dpr: number };
type Tela = { sx: Float32Array; sy: Float32Array; r: Float32Array };
type Ativo = { id: string; origem: "mouse" | "teclado" | "toque" | "busca" } | null;
type Area = { latMin: number; latMax: number; lonMin: number; lonMax: number };

const FONTE_NOME = "600 12px \"Inter Variable\", Inter, ui-sans-serif, system-ui, sans-serif";
const PASSO_TECLADO = 60;
const ZOOM_BOTAO = 1.6, ZOOM_TECLADO = 1.5;
/** Caixa dos botões de zoom (canto superior direito): os nomes não passam por baixo deles. */
const CAIXA_CONTROLES = (w: number): Caixa => ({ x0: w - 54, y0: 0, x1: w, y1: 132 });

/** A vista deixada em cada análise (pela assinatura dos itens com ponto): cada vista volta como foi deixada, mesmo depois de o
 * mapa sair da tela. Só estado visual da sessão. */
const memoriaDeVistas = new Map<string, Vista>();
function lembrarVista(chave: string, vista: Vista) {
  memoriaDeVistas.delete(chave);
  memoriaDeVistas.set(chave, vista);
  if (memoriaDeVistas.size > 16) memoriaDeVistas.delete(memoriaDeVistas.keys().next().value as string);
}

/** As cores do mapa como variáveis CSS (--mapa-superficie, --mapa-tinta…), para mapa.css: uma só fonte, as cores do esquema em
 * uso (MAPA_CORES no claro, MAPA_CORES_ESCURO no escuro). */
const variaveisCss = (cores: CoresDoMapa) => Object.fromEntries(Object.entries(cores).map(([chave, valor]) =>
  ["--mapa-" + chave.replace(/[A-Z]/g, letra => "-" + letra.toLowerCase()), valor])) as unknown as CSSProperties;

const corDesenhada = (ponto: PontoDaCena, cores: CoresDoMapa) => ponto.esmaecido ? cores.esmaecido : ponto.vazada ? cores.naoAvaliavel : ponto.cor;
const minusculaInicial = (texto: string) => texto.length > 1 && texto.charAt(1) === texto.charAt(1).toLocaleLowerCase("pt-BR")
  ? texto.charAt(0).toLocaleLowerCase("pt-BR") + texto.slice(1) : texto;
const semAcento = (texto: string) => texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const textoDoReferencial = (referencial: string) => /sirgas/i.test(referencial) ? "SIRGAS 2000" : /wgs/i.test(referencial) ? "WGS 84" : referencial;
function circulo(ctx: CanvasRenderingContext2D, x: number, y: number, r: number) {
  ctx.moveTo(x + r, y);
  ctx.arc(x, y, r, 0, 2 * Math.PI);
}

type JanelaComMapa = Window & { __adtMapa?: unknown };

const MapaAnalise = forwardRef<MapaHandle, MapaProps>(function MapaAnalise(p, ref) {
  const estreito = useNarrow();
  const quadroRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dicaRef = useRef<DicaHandle>(null);
  const cantoRef = useRef<CantoHandle>(null);
  const atual = useRef(p);
  atual.current = p;
  // Esquema de cor do aparelho (a impressão é sempre clara): as cores do canvas, das legendas e das variáveis de mapa.css.
  const esquema = useEsquemaDeCor();
  const cores = coresDoMapa(esquema), rampa = rampaContinua(esquema);
  const variaveis = useMemo(() => variaveisCss(cores), [cores]);
  const coresRef = useRef(cores), esquemaRef = useRef(esquema);
  coresRef.current = cores; esquemaRef.current = esquema;

  // ------------------------------------------------------------------------------------------ o que desenhar
  const projecao = useMemo(() => projetar(p.dados.pontos), [p.dados.pontos]);
  const limitesTodos = useMemo(() => limitesDe(projecao, projecao.ids.map((_, i) => i)), [projecao]);
  const base = useMemo(() => baseDoMapa(p.itens, projecao), [p.itens, projecao]);
  // O enquadramento inicial cobre também os territórios de referência desenhados (25/10/2026); a vista guardada é a deste conjunto.
  const limitesDoQuadro = useMemo(() => limitesComReferencias(projecao, base, p.referencias), [projecao, base, p.referencias]);
  const assinatura = useMemo(() => base.assinatura + (p.referencias.length ? "|" + assinaturaDe(p.referencias) : ""),
    [base.assinatura, p.referencias]);
  const cena = useMemo(() => montarCena(base, { dentro: p.dentro, pintura: p.pintura, pintar: p.pintar, valorContinuo: p.valorContinuo,
    dominio: p.dominio, escala: p.escala, tamanho: p.tamanho.valor, maximoTamanho: p.tamanho.maximo, cores, rampa }),
  [base, p.dentro, p.pintura, p.pintar, p.valorContinuo, p.dominio, p.escala, p.tamanho.valor, p.tamanho.maximo, cores, rampa]);
  const selecionados = useMemo(() => new Set(p.selecionados), [p.selecionados]);
  const segmentos = useMemo(() => segmentosDasLigacoes(p.ligacoes, id => projecao.indice.has(id)), [p.ligacoes, projecao]);

  const projRef = useRef(projecao), limitesTodosRef = useRef(limitesTodos), baseRef = useRef(base), cenaRef = useRef(cena);
  const selRef = useRef(selecionados), segRef = useRef(segmentos), quadroLimitesRef = useRef(limitesDoQuadro), assinaturaRef = useRef(assinatura);
  projRef.current = projecao; limitesTodosRef.current = limitesTodos; baseRef.current = base; cenaRef.current = cena;
  selRef.current = selecionados; segRef.current = segmentos; quadroLimitesRef.current = limitesDoQuadro; assinaturaRef.current = assinatura;

  // ------------------------------------------------------------------------------------------ estado visual (refs)
  const vista = useRef<Vista | null>(null);
  const interagiu = useRef(false);
  const tamanho = useRef<Tamanho>({ w: 0, h: 0, dpr: 1 });
  const tela = useRef<Tela | null>(null);
  const ativo = useRef<Ativo>(null);
  const avisado = useRef<string | null>(null);
  const quadro = useRef(0);
  const ponteiro = useRef<{ x: number; y: number } | null>(null);
  const arrastando = useRef(false);
  const focoTeclado = useRef(false);
  const larguras = useRef(new Map<string, number>());
  const desenhos = useRef(0);
  const ultimaDica = useRef("");
  const ultimaArea = useRef("");
  const dicaGuardada = useRef<{ id: string; cena: Cena; fonte: MapaProps["dicaDe"]; versao: number; dica: Dica; notas: string[] } | null>(null);
  const estreitoRef = useRef(estreito);
  estreitoRef.current = estreito;
  // Um só quadro por vez: o ponto sob o mouse é procurado uma vez por quadro, antes do desenho (ver passoDoQuadro). O mapa só é
  // redesenhado quando algo mudou (`sujo`): mover o mouse sem trocar de ponto não redesenha.
  const passoDoQuadro = useRef<FrameRequestCallback>(() => {});
  const sujo = useRef(false);
  const pedirQuadro = useCallback(() => {
    if (!quadro.current) quadro.current = requestAnimationFrame(tempo => passoDoQuadro.current(tempo));
  }, []);
  const agendar = useCallback(() => { sujo.current = true; pedirQuadro(); }, [pedirQuadro]);

  const vistaInicial = useCallback((): Vista => {
    const { w, h } = tamanho.current;
    return enquadrar(limitesComContexto(quadroLimitesRef.current, limitesTodosRef.current), w, h);
  }, []);
  // A Inter embutida (28/10/2026) pode chegar depois do primeiro desenho (font-display: swap): as larguras dos nomes medidas com a
  // fonte de reserva saem da memória, e o mapa redesenha os nomes com a Inter, sem esconder nem sobrepor nomes por medida errada.
  useEffect(() => {
    let vivo = true;
    void document.fonts?.ready.then(() => { if (vivo) { larguras.current.clear(); agendar(); } });
    return () => { vivo = false; };
  }, [agendar]);
  const limitesDeZoom = useCallback(() => {
    const { w, h } = tamanho.current;
    const inicial = vistaInicial().escala, todos = enquadrar(limitesTodosRef.current, w, h).escala;
    return { min: Math.min(inicial, todos) * 0.6, max: Math.max(inicial, todos) * 64 };
  }, [vistaInicial]);

  // ------------------------------------------------------------------------------------------ desenho
  const desenhar = useCallback(() => {
    sujo.current = false;
    const canvas = canvasRef.current, v = vista.current;
    const { w, h, dpr } = tamanho.current;
    if (!canvas || !v || w < 2 || h < 2) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const inicio = performance.now();
    const props = atual.current, c = cenaRef.current, pr = projRef.current, b = baseRef.current, sel = selRef.current;
    const paleta = coresRef.current;
    const e = v.escala, ox = w / 2 - v.cx * e, oy = h / 2 - v.cy * e;
    const zoom = v.escala / vistaInicial().escala;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.globalAlpha = 1;
    ctx.setLineDash([]);
    ctx.fillStyle = paleta.superficie;
    ctx.fillRect(0, 0, w, h);

    // 1. Fundo: as demais unidades da fonte, em quadradinhos cinza bem claros (o formato do Brasil), sem interação.
    ctx.fillStyle = paleta.fundo;
    ctx.beginPath();
    for (const i of b.fundo) {
      const x = pr.x[i] * e + ox, y = pr.y[i] * e + oy;
      if (x < -2 || y < -2 || x > w + 2 || y > h + 2) continue;
      ctx.rect(x - RAIO_FUNDO, y - RAIO_FUNDO, 2 * RAIO_FUNDO, 2 * RAIO_FUNDO);
    }
    ctx.fill();

    const n = c.pontos.length, sx = new Float32Array(n), sy = new Float32Array(n), rs = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const ponto = c.pontos[i];
      sx[i] = pr.x[ponto.indice] * e + ox; sy[i] = pr.y[ponto.indice] * e + oy; rs[i] = ponto.r;
    }
    tela.current = { sx, sy, r: rs };
    const naTela = (i: number) => sx[i] > -rs[i] - 8 && sy[i] > -rs[i] - 8 && sx[i] < w + rs[i] + 8 && sy[i] < h + rs[i] + 8;

    // 2. Fora da régua ou dos filtros: no lugar e no tamanho, bem claros, sem interação (nunca somem).
    ctx.fillStyle = paleta.esmaecido;
    ctx.strokeStyle = paleta.esmaecidoBorda;
    ctx.lineWidth = 0.75;
    ctx.beginPath();
    for (let i = 0; i < n; i++) if (c.pontos[i].esmaecido && naTela(i)) circulo(ctx, sx[i], sy[i], rs[i]);
    ctx.fill();
    ctx.stroke();

    // 3. Pontos do resultado: por faixa de raio, os maiores atrás e os menores na frente; em cada faixa, lotes pela pintura,
    //    com o anel fino da superfície separando os sobrepostos. Vazado (não avaliável): anel tracejado cinza, nunca zero.
    for (let i = 0; i < n;) {
      const faixa = Math.floor(rs[i]);
      const lotes = new Map<string, number[]>();
      let j = i;
      for (; j < n && Math.floor(rs[j]) === faixa; j++) {
        const ponto = c.pontos[j];
        if (ponto.esmaecido || !naTela(j)) continue;
        const chave = ponto.vazada ? "v" : (ponto.apagada ? "a" : "c") + ponto.cor;
        const lote = lotes.get(chave);
        if (lote) lote.push(j); else lotes.set(chave, [j]);
      }
      for (const [chave, membros] of lotes) {
        ctx.beginPath();
        for (const k of membros) circulo(ctx, sx[k], sy[k], rs[k]);
        if (chave === "v") {
          ctx.fillStyle = paleta.superficie;
          ctx.fill();
          ctx.setLineDash([3, 2]);
          ctx.lineWidth = 1.25;
          ctx.strokeStyle = paleta.naoAvaliavel;
          ctx.stroke();
          ctx.setLineDash([]);
        } else {
          ctx.globalAlpha = chave[0] === "a" ? OPACIDADE_APAGADA : 1;
          ctx.fillStyle = chave.slice(1);
          ctx.fill();
          ctx.globalAlpha = 1;
          ctx.lineWidth = 0.8;
          ctx.strokeStyle = paleta.superficie;
          ctx.stroke();
        }
      }
      i = j;
    }

    const posicaoDe = (id: string): [number, number, number] | null => {
      const k = c.porId.get(id);
      if (k !== undefined) return [sx[k], sy[k], rs[k]];
      const i = pr.indice.get(id);
      return i === undefined ? null : [pr.x[i] * e + ox, pr.y[i] * e + oy, RAIO_FUNDO * 1.6];
    };

    // 4. Ligações ilustrativas (não são trajeto): dos selecionados até a referência mais próxima indicada pelo motor.
    if (segRef.current.length) {
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = paleta.tinta2;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      for (const segmento of segRef.current) {
        const a = posicaoDe(segmento.de), z = posicaoDe(segmento.para);
        if (!a || !z) continue;
        ctx.moveTo(a[0], a[1]);
        ctx.lineTo(z[0], z[1]);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // 5. Membros de conjuntos: anel escuro (o conjunto não tem ponto).
    if (b.aneis.length) {
      ctx.globalAlpha = 0.7;
      ctx.strokeStyle = paleta.tinta;
      ctx.lineWidth = 1.25;
      ctx.beginPath();
      for (const anel of b.aneis) {
        const pos = posicaoDe(anel.membro);
        if (pos) circulo(ctx, pos[0], pos[1], pos[2] + 4);
      }
      ctx.stroke();
      ctx.globalAlpha = 1;
    }

    // 6. Referência: a mesma mira do gráfico.
    if (props.referencias.length) {
      ctx.strokeStyle = paleta.tinta;
      ctx.lineWidth = 1.5;
      ctx.lineCap = "round";
      ctx.beginPath();
      for (const id of props.referencias) {
        const pos = posicaoDe(id);
        if (!pos) continue;
        const [x, y, r] = pos;
        ctx.moveTo(x - r - 9, y); ctx.lineTo(x - r - 3, y); ctx.moveTo(x + r + 3, y); ctx.lineTo(x + r + 9, y);
        ctx.moveTo(x, y - r - 9); ctx.lineTo(x, y - r - 3); ctx.moveTo(x, y + r + 3); ctx.lineTo(x, y + r + 9);
      }
      ctx.stroke();
      ctx.lineCap = "butt";
    }

    // 7. Selecionados: anel escuro, como a bolha marcada.
    ctx.strokeStyle = paleta.tinta;
    ctx.lineWidth = 2;
    ctx.beginPath();
    for (const id of sel) {
      const k = c.porId.get(id);
      if (k !== undefined && naTela(k)) circulo(ctx, sx[k], sy[k], rs[k] + 2);
    }
    ctx.stroke();

    // 8. Ativo (mouse, teclado, toque ou busca) e o ativo do gráfico ao lado: anel externo; foco do teclado: contorno de foco.
    const ativos = new Set([ativo.current?.id, props.ativoExterno].filter((id): id is string => !!id));
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    for (const id of ativos) {
      const k = c.porId.get(id);
      if (k !== undefined && naTela(k)) circulo(ctx, sx[k], sy[k], rs[k] + 4.5);
    }
    ctx.stroke();
    const focado = ativo.current?.origem === "teclado" && focoTeclado.current ? c.porId.get(ativo.current.id) : undefined;
    if (focado !== undefined && naTela(focado)) {
      ctx.strokeStyle = paleta.foco;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      circulo(ctx, sx[focado], sy[focado], rs[focado] + 8);
      ctx.stroke();
    }

    // 9. Nomes: dos selecionados, dos que têm texto extra ("1º") e, com poucos pontos, de todos; com zoom, de mais pontos, sem
    //    cobrir uns aos outros (os maiores primeiro). Halo da superfície; texto em tinta, nunca na cor da série.
    const ativosNoResultado = n - c.esmaecidos;
    const todos = ativosNoResultado <= LIMITE_NOMES_TODOS;
    const pedidos: PedidoDeNome[] = [];
    ctx.font = FONTE_NOME;
    const larguraDe = (texto: string) => {
      let largura = larguras.current.get(texto);
      if (largura === undefined) { largura = Math.ceil(ctx.measureText(texto).width); larguras.current.set(texto, largura); }
      return largura;
    };
    const textos = new Map<string, string>();
    let extras = 0;
    for (let i = 0; i < n; i++) {
      if (!naTela(i)) continue;
      const ponto = c.pontos[i];
      const extra = !ponto.esmaecido ? props.extraDoRotulo?.(ponto.item) ?? null : null;
      const obrigatorio = sel.has(ponto.id) || !!extra || (todos && !ponto.esmaecido);
      const opcional = !obrigatorio && !ponto.esmaecido && zoom > 1.25 && extras < 60;
      if (!obrigatorio && !opcional) continue;
      if (opcional) extras += 1;
      const texto = (extra ? extra + " " : "") + ponto.item.rotulo;
      textos.set(ponto.id, texto);
      pedidos.push({ id: ponto.id, x: sx[i], y: sy[i], r: rs[i], largura: larguraDe(texto), obrigatorio });
    }
    // A referência fora do resultado, quando uma ligação chega até ela (os territórios da base e os marcados), ganha o
    // nome (25/10/2026), com "· referência".
    for (const id of new Set(segRef.current.map(segmento => segmento.para))) {
      const nome = props.nomesDasReferencias?.get(id), pos = c.porId.has(id) ? null : posicaoDe(id);
      if (!nome || !pos || pos[0] < 0 || pos[1] < 0 || pos[0] > w || pos[1] > h) continue;
      const texto = nome + " · referência";
      textos.set(id, texto);
      pedidos.push({ id, x: pos[0], y: pos[1], r: pos[2], largura: larguraDe(texto), obrigatorio: true });
    }
    const comMiniMapa = zoom > 1.1;
    const tamanhoMini = estreitoRef.current ? 88 : 120;
    const obstaculos = [CAIXA_CONTROLES(w), ...(comMiniMapa ? [{ x0: 0, y0: h - tamanhoMini - 16, x1: tamanhoMini + 16, y1: h }] : [])];
    const escritos = new Set<string>();
    if (pedidos.length) {
      ctx.lineJoin = "round";
      ctx.lineWidth = 3;
      ctx.strokeStyle = paleta.superficie;
      ctx.fillStyle = paleta.tinta;
      for (const nome of posicionarNomes(pedidos, w, h, obstaculos)) {
        const texto = textos.get(nome.id)!;
        ctx.strokeText(texto, nome.x, nome.y);
        ctx.fillText(texto, nome.x, nome.y);
        escritos.add(nome.id);
      }
    }

    // 10. Gancho de teste (como o __adtMapModel do mapa antigo), a dica e o mapinha do canto.
    const escalaDoGancho = props.pintura === "continua" ? escalaEfetiva(props.escala, props.dominio) : "nenhuma";
    const pontosDoGancho = c.pontos;
    desenhos.current += 1;
    (window as JanelaComMapa).__adtMapa = {
      pintura: props.pintura, escala: escalaDoGancho, dominio: props.pintura === "continua" ? props.dominio : null,
      contexto: b.fundo.length, esmaecidos: c.esmaecidos, brasil: props.contextoBrasil?.valor ?? null,
      vista: { cx: v.cx, cy: v.cy, escala: v.escala, zoom }, largura: w, altura: h, desenhos: desenhos.current,
      ms: performance.now() - inicio,
      /** Esquema de cor do desenho ("claro" ou "escuro") e a superfície pintada no canvas. */
      esquema: esquemaRef.current, superficie: paleta.superficie,
      /** x e y em pixels CSS, relativos ao canvas (`mapa-canvas`). */
      get pontos() {
        return pontosDoGancho.map((ponto, i) => ({ id: ponto.id, x: sx[i], y: sy[i], r: ponto.r, cor: corDesenhada(ponto, paleta),
          esmaecido: ponto.esmaecido, selecionado: sel.has(ponto.id), vazada: ponto.vazada, apagada: ponto.apagada, naTela: naTela(i) }));
      },
      /** Os territórios de referência desenhados (a mira), em pixels CSS, e o nome escrito junto, quando há (25/10/2026). */
      get referencias() {
        return props.referencias.map(id => {
          const pos = posicaoDe(id);
          return { id, x: pos ? pos[0] : null, y: pos ? pos[1] : null, naTela: !!pos && pos[0] >= 0 && pos[1] >= 0 && pos[0] <= w && pos[1] <= h,
            nome: escritos.has(id) ? textos.get(id) ?? null : null };
        });
      },
    };

    const a = ativo.current, k = a ? c.porId.get(a.id) : undefined;
    if (!a || k === undefined || arrastando.current || c.pontos[k].esmaecido || !naTela(k)) {
      if (ultimaDica.current) { ultimaDica.current = ""; dicaRef.current?.mostrar(null); }
    } else {
      // O conteúdo da dica só é refeito quando muda o ponto, a cena ou a função da dica (indicador, limiares).
      const guardadaAntes = dicaGuardada.current;
      if (guardadaAntes?.id !== a.id || guardadaAntes.cena !== c || guardadaAntes.fonte !== props.dicaDe) {
        const conjuntos = b.aneis.filter(anel => anel.membro === a.id).map(anel => anel.rotulo);
        dicaGuardada.current = { id: a.id, cena: c, fonte: props.dicaDe, versao: (guardadaAntes?.versao ?? 0) + 1,
          dica: props.dicaDe(c.pontos[k].item),
          notas: conjuntos.length ? ["Membro do conjunto " + conjuntos.join(", ") + " (o conjunto não tem ponto no mapa)."] : [] };
      }
      const chave = a.id + "|" + dicaGuardada.current!.versao + "|" + Math.round(sx[k]) + "|" + Math.round(sy[k]) + "|" + w + "|" + h +
        "|" + a.origem;
      if (chave !== ultimaDica.current) {
        ultimaDica.current = chave;
        const guardada = dicaGuardada.current!;
        dicaRef.current?.mostrar({ id: a.id, dica: guardada.dica, notas: guardada.notas, x: sx[k], y: sy[k], r: rs[k], largura: w, altura: h,
          anunciar: a.origem === "teclado" });
      }
    }
    const area = comMiniMapa ? areaVisivel(v, w, h, pr.k) : null;
    const chaveArea = area ? [area.latMin, area.latMax, area.lonMin, area.lonMax].map(valor => valor.toFixed(3)).join(",") : "";
    if (chaveArea !== ultimaArea.current) { ultimaArea.current = chaveArea; cantoRef.current?.definir(area); }
  }, [vistaInicial]);

  /** As posições do último desenho, só se ainda correspondem à cena atual (os índices mudam com a cena). */
  const telaAlinhada = useCallback(() => {
    const t = tela.current;
    return t && t.sx.length === cenaRef.current.pontos.length ? t : null;
  }, []);
  /** O ponto interativo sob o ponteiro, pelas posições do último desenho (alvo ampliado). */
  const pegar = useCallback((x: number, y: number, alvo: number) => {
    const t = telaAlinhada(), c = cenaRef.current;
    if (!t) return -1;
    return alvoMaisProximo(x, y, t.sx, t.sy, t.r, i => !c.pontos[i].esmaecido, alvo);
  }, [telaAlinhada]);
  /** Troca o ponto ativo (anel, dica) e avisa a área (`onAtivo`) só quando o id muda. */
  const definirAtivo = useCallback((novo: Ativo) => {
    ativo.current = novo;
    const id = novo?.id ?? null;
    if (id !== avisado.current) { avisado.current = id; atual.current.onAtivo?.(id); }
    agendar();
  }, [agendar]);
  passoDoQuadro.current = () => {
    quadro.current = 0;
    const pendente = ponteiro.current;
    ponteiro.current = null;
    if (pendente && !arrastando.current) {
      const i = pegar(pendente.x, pendente.y, ALVO_MOUSE);
      const id = i >= 0 ? cenaRef.current.pontos[i].id : null;
      const canvas = canvasRef.current;
      if (canvas) canvas.style.cursor = id ? "pointer" : "grab";
      if (id && id !== ativo.current?.id) {
        ativo.current = { id, origem: "mouse" };
        sujo.current = true;
        if (id !== avisado.current) { avisado.current = id; atual.current.onAtivo?.(id); }
      } else if (!id && ativo.current?.origem === "mouse") {
        ativo.current = null;
        sujo.current = true;
        if (avisado.current !== null) { avisado.current = null; atual.current.onAtivo?.(null); }
      }
    }
    if (sujo.current) desenhar();
  };

  const marcarInteracao = useCallback(() => {
    interagiu.current = true;
    if (vista.current) lembrarVista(assinaturaRef.current, vista.current);
  }, []);
  const zoom = useCallback((fator: number, px?: number, py?: number) => {
    const v = vista.current;
    if (!v) return;
    const { w, h } = tamanho.current;
    vista.current = zoomEm(v, fator, px ?? w / 2, py ?? h / 2, w, h, limitesDeZoom());
    marcarInteracao();
    agendar();
  }, [agendar, limitesDeZoom, marcarInteracao]);
  const verTudo = useCallback(() => {
    interagiu.current = false;
    memoriaDeVistas.delete(assinaturaRef.current);
    if (tamanho.current.w) vista.current = vistaInicial();
    agendar();
  }, [agendar, vistaInicial]);
  /** Mede a área e cria a vista quando ainda não há (por exemplo, `posicoes()` logo depois de montar, para a transição). */
  const garantirVista = useCallback(() => {
    const elemento = quadroRef.current, canvas = canvasRef.current;
    if (elemento && canvas && !tamanho.current.w) {
      const w = elemento.clientWidth, h = elemento.clientHeight;
      if (w >= 2 && h >= 2) {
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        tamanho.current = { w, h, dpr };
        canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      }
    }
    if (!vista.current && tamanho.current.w) vista.current = memoriaDeVistas.get(assinaturaRef.current) ?? vistaInicial();
  }, [vistaInicial]);
  /** Centra num ponto (busca por nome), com zoom suficiente para vê-lo entre os vizinhos. */
  const centrar = useCallback((id: string) => {
    garantirVista();
    const v = vista.current, i = projRef.current.indice.get(id);
    if (!v || i === undefined) return;
    const escala = Math.min(limitesDeZoom().max, Math.max(v.escala, vistaInicial().escala * 4));
    vista.current = { cx: projRef.current.x[i], cy: projRef.current.y[i], escala };
    marcarInteracao();
    const ponto = cenaRef.current.pontos[cenaRef.current.porId.get(id) ?? -1];
    if (ponto && !ponto.esmaecido) definirAtivo({ id, origem: "busca" }); else agendar();
  }, [agendar, definirAtivo, garantirVista, limitesDeZoom, marcarInteracao, vistaInicial]);

  // A análise mudou de itens (ou de territórios de referência): volta a vista guardada para eles, ou o enquadramento inicial. (Antes
  // do efeito do tamanho.)
  useEffect(() => {
    const guardada = memoriaDeVistas.get(assinatura);
    interagiu.current = !!guardada;
    vista.current = guardada ?? (tamanho.current.w ? vistaInicial() : null);
    agendar();
  }, [assinatura, agendar, vistaInicial]);

  // Tamanho do canvas (densidade de pixels) e novo enquadramento enquanto a pessoa não navegou. Oculto (largura zero), espera.
  useEffect(() => {
    const elemento = quadroRef.current;
    if (!elemento) return;
    const medir = () => {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const w = elemento.clientWidth, h = elemento.clientHeight, dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (w < 2 || h < 2) return;
      const mudou = w !== tamanho.current.w || h !== tamanho.current.h || dpr !== tamanho.current.dpr;
      if (mudou) {
        tamanho.current = { w, h, dpr };
        canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr);
      }
      if (!vista.current || (mudou && !interagiu.current)) vista.current = vistaInicial();
      desenhar();
    };
    medir();
    if (typeof ResizeObserver === "undefined") return;
    const observador = new ResizeObserver(medir);
    observador.observe(elemento);
    return () => observador.disconnect();
  }, [desenhar, vistaInicial]);

  // Redesenho quando muda o que se vê (pintura, régua, seleção, referência, ligações, destaque do gráfico ao lado).
  useEffect(() => {
    const a = ativo.current;
    if (a) {
      const k = cena.porId.get(a.id);
      if (k === undefined || cena.pontos[k].esmaecido) definirAtivo(null);
    }
    agendar();
  }, [cena, selecionados, segmentos, p.referencias, p.ativoExterno, p.extraDoRotulo, p.contextoBrasil, p.dicaDe, agendar, definirAtivo]);

  // Troca do esquema de cor: o canvas é redesenhado já no commit, sem esperar o próximo quadro. No começo da impressão, a troca
  // para o claro chega síncrona (flushSync, em useEsquemaDeCor), e o mapa vai claro para a página impressa.
  useLayoutEffect(() => { desenhar(); }, [esquema, desenhar]);

  // Ao sair: cancela o quadro pendente, avisa que nada está ativo e retira o gancho de teste.
  useEffect(() => () => {
    if (quadro.current) cancelAnimationFrame(quadro.current);
    quadro.current = 0;
    if (avisado.current !== null) { avisado.current = null; atual.current.onAtivo?.(null); }
    delete (window as JanelaComMapa).__adtMapa;
  }, []);

  // Arrasto, pinça, clique e toque (Pointer Events); zoom pela roda só com Ctrl/⌘ ou com o mapa em foco; duplo clique amplia.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ponteiros = new Map<number, { x: number; y: number }>();
    let movido = 0, pinca = 0;
    const local = (evento: { clientX: number; clientY: number }): [number, number] => {
      const caixa = canvas.getBoundingClientRect();
      return [evento.clientX - caixa.left, evento.clientY - caixa.top];
    };
    const baixo = (evento: PointerEvent) => {
      if (evento.pointerType === "mouse" && evento.button !== 0) return;
      canvas.setPointerCapture?.(evento.pointerId);
      const [x, y] = local(evento);
      ponteiros.set(evento.pointerId, { x, y });
      movido = 0;
      if (ponteiros.size === 2) {
        const [a, b] = [...ponteiros.values()];
        pinca = Math.hypot(a.x - b.x, a.y - b.y);
      }
    };
    const mover = (evento: PointerEvent) => {
      const [x, y] = local(evento);
      const anterior = ponteiros.get(evento.pointerId);
      if (!anterior) {
        if (evento.pointerType === "mouse") { ponteiro.current = { x, y }; pedirQuadro(); }
        return;
      }
      ponteiros.set(evento.pointerId, { x, y });
      const v = vista.current;
      if (!v) return;
      if (ponteiros.size === 2) {
        const [a, b] = [...ponteiros.values()];
        const distancia = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinca > 0) zoom(distancia / pinca, (a.x + b.x) / 2, (a.y + b.y) / 2);
        pinca = distancia; movido += 10;
        return;
      }
      const dx = x - anterior.x, dy = y - anterior.y;
      movido += Math.abs(dx) + Math.abs(dy);
      if (movido > 3) {
        // Ao começar a arrastar, a dica do ponto sob o mouse ou tocado sai (o ponto se move junto com o mapa).
        if (!arrastando.current && (ativo.current?.origem === "toque" || ativo.current?.origem === "mouse")) definirAtivo(null);
        arrastando.current = true;
        canvas.style.cursor = "grabbing";
        vista.current = deslocar(v, dx, dy);
        marcarInteracao();
        agendar();
      }
    };
    const soltar = (evento: PointerEvent) => {
      const [x, y] = local(evento);
      const clique = evento.type === "pointerup" && ponteiros.size === 1 && ponteiros.has(evento.pointerId) && movido <= 3;
      ponteiros.delete(evento.pointerId);
      if (ponteiros.size < 2) pinca = 0;
      if (!ponteiros.size && arrastando.current) { arrastando.current = false; canvas.style.cursor = "grab"; agendar(); }
      if (!clique) return;
      const toque = evento.pointerType !== "mouse";
      const i = pegar(x, y, toque ? ALVO_TOQUE : ALVO_MOUSE);
      if (i < 0) { if (toque || ativo.current?.origem === "busca") definirAtivo(null); return; }
      const id = cenaRef.current.pontos[i].id;
      definirAtivo({ id, origem: toque ? "toque" : "mouse" });
      atual.current.onAlternar(id);
    };
    const sair = (evento: PointerEvent) => {
      if (evento.pointerType !== "mouse" || ponteiros.size) return;
      ponteiro.current = null;
      canvas.style.cursor = "grab";
      if (ativo.current?.origem === "mouse") definirAtivo(null);
    };
    const roda = (evento: WheelEvent) => {
      if (!(evento.ctrlKey || evento.metaKey || document.activeElement === canvas)) return;
      evento.preventDefault();
      const [x, y] = local(evento);
      zoom(Math.exp(-evento.deltaY * 0.0015), x, y);
    };
    const duplo = (evento: MouseEvent) => { const [x, y] = local(evento); zoom(2, x, y); };
    canvas.addEventListener("pointerdown", baixo);
    canvas.addEventListener("pointermove", mover);
    canvas.addEventListener("pointerup", soltar);
    canvas.addEventListener("pointercancel", soltar);
    canvas.addEventListener("pointerleave", sair);
    canvas.addEventListener("wheel", roda, { passive: false });
    canvas.addEventListener("dblclick", duplo);
    return () => {
      canvas.removeEventListener("pointerdown", baixo);
      canvas.removeEventListener("pointermove", mover);
      canvas.removeEventListener("pointerup", soltar);
      canvas.removeEventListener("pointercancel", soltar);
      canvas.removeEventListener("pointerleave", sair);
      canvas.removeEventListener("wheel", roda);
      canvas.removeEventListener("dblclick", duplo);
    };
  }, [agendar, definirAtivo, marcarInteracao, pedirQuadro, pegar, zoom]);

  // Teclado no mapa em foco: setas movem a vista; Shift + setas vão ao ponto vizinho; + e − ampliam e reduzem; 0 ou Home
  // voltam ao enquadramento inicial; Enter ou espaço marcam o ponto em foco; Esc fecha a dica.
  const pontoCentral = useCallback(() => {
    const t = telaAlinhada(), c = cenaRef.current;
    if (!t) return -1;
    const { w, h } = tamanho.current;
    let melhor = -1, menor = Infinity;
    for (let i = 0; i < c.pontos.length; i++) {
      if (c.pontos[i].esmaecido) continue;
      const d = (t.sx[i] - w / 2) ** 2 + (t.sy[i] - h / 2) ** 2;
      if (d < menor) { menor = d; melhor = i; }
    }
    return melhor;
  }, [telaAlinhada]);
  const focarPonto = useCallback((indice: number) => {
    const t = telaAlinhada(), c = cenaRef.current, v = vista.current;
    if (!t || !v || indice < 0 || indice >= c.pontos.length) return;
    const { w, h } = tamanho.current;
    const x = t.sx[indice], y = t.sy[indice];
    if (x < 48 || y < 48 || x > w - 60 || y > h - 48) { vista.current = deslocar(v, w / 2 - x, h / 2 - y); marcarInteracao(); }
    definirAtivo({ id: c.pontos[indice].id, origem: "teclado" });
  }, [definirAtivo, marcarInteracao, telaAlinhada]);
  function teclado(evento: KeyboardEvent<HTMLCanvasElement>) {
    const v = vista.current;
    if (!v) return;
    const setas: Record<string, Direcao> = { ArrowLeft: "esquerda", ArrowRight: "direita", ArrowUp: "cima", ArrowDown: "baixo" };
    const direcao = setas[evento.key];
    const c = cenaRef.current, t = telaAlinhada();
    if (direcao && evento.shiftKey) {
      const atualIndice = ativo.current ? c.porId.get(ativo.current.id) ?? -1 : -1;
      if (atualIndice < 0 || c.pontos[atualIndice].esmaecido) focarPonto(pontoCentral());
      else if (t) {
        const proximo = vizinhoNaDirecao(atualIndice, direcao, t.sx, t.sy, i => !c.pontos[i].esmaecido);
        focarPonto(proximo >= 0 ? proximo : atualIndice);
      }
    } else if (direcao) {
      const passo: Record<Direcao, [number, number]> = { esquerda: [PASSO_TECLADO, 0], direita: [-PASSO_TECLADO, 0],
        cima: [0, PASSO_TECLADO], baixo: [0, -PASSO_TECLADO] };
      vista.current = deslocar(v, ...passo[direcao]);
      marcarInteracao();
      agendar();
    } else if (evento.key === "+" || evento.key === "=") zoom(ZOOM_TECLADO);
    else if (evento.key === "-" || evento.key === "_") zoom(1 / ZOOM_TECLADO);
    else if (evento.key === "0" || evento.key === "Home") verTudo();
    else if (evento.key === "Enter" || evento.key === " ") {
      const a = ativo.current, k = a ? c.porId.get(a.id) : undefined;
      if (a && k !== undefined && !c.pontos[k].esmaecido) atual.current.onAlternar(a.id);
      else focarPonto(pontoCentral());
    } else if (evento.key === "Escape") definirAtivo(null);
    else return;
    evento.preventDefault();
  }
  function aoFocar(evento: { currentTarget: HTMLCanvasElement }) {
    let visivel = true;
    try { visivel = evento.currentTarget.matches(":focus-visible"); } catch { visivel = true; }
    focoTeclado.current = visivel;
    if (visivel && !ativo.current) focarPonto(pontoCentral());
    else agendar();
  }
  function aoSair() {
    focoTeclado.current = false;
    if (ativo.current?.origem === "teclado") definirAtivo(null); else agendar();
  }

  useImperativeHandle(ref, () => ({
    posicoes: (): Posicoes => {
      garantirVista();
      const saida: Posicoes = new Map();
      const canvas = canvasRef.current, v = vista.current;
      if (!canvas || !v) return saida;
      const caixa = canvas.getBoundingClientRect();
      const { w, h } = tamanho.current, pr = projRef.current;
      for (const ponto of cenaRef.current.pontos) {
        const [x, y] = paraTela(pr.x[ponto.indice], pr.y[ponto.indice], v, w, h);
        saida.set(ponto.id, { x: caixa.left + x, y: caixa.top + y, r: ponto.r, cor: corDesenhada(ponto, coresRef.current) });
      }
      return saida;
    },
    verTudo,
  }), [garantirVista, verTudo]);

  // ------------------------------------------------------------------------------------------ textos e legendas
  const rotulos = p.rotulos, unidade = rotulos.unidade;
  const feminino = generoDe(unidade) === "f";
  const escalaCor = escalaEfetiva(p.escala, p.dominio);
  const temReferencia = p.referencias.some(id => projecao.indice.has(id));
  const semPontoNoResultado = useMemo(() => {
    const sem = new Set(p.dados.semCoordenada.map(item => item.id));
    return base.semPonto.length > 0 || p.itens.some(item => sem.has(item.id));
  }, [base.semPonto, p.dados.semCoordenada, p.itens]);
  const simbolos = [
    cena.vazadas > 0 ? "anel tracejado cinza: valor não avaliável nesta camada, nunca zero (veja Não avaliáveis)" : "",
    cena.esmaecidos > 0 ? "pontos bem claros: fora da régua ou dos filtros (ficam no lugar, sem interação)" : "",
    base.fundo.length > 0 ? "cinza miúdo ao fundo: " + artigo(unidade, true) + " demais " + unidade.plural + " da fonte, só para situar" : "",
    base.aneis.length > 0 ? "anel escuro: membro de conjunto; o conjunto não tem ponto, e o valor dele é a soma das contagens dos " +
      "componentes, com possível dupla contagem" : "",
    temReferencia ? (p.referenciaPorItem ? "mira: referência mais próxima" : "mira: membro da referência (distância 0)") : "",
  ].filter(Boolean).join("; ");
  const rotuloDoCanvas = "Mapa de pontos d" + artigo(unidade, true) + " " + unidade.plural + " do resultado. Com o mapa em foco: as setas " +
    "movem a vista; Shift e as setas vão ao ponto vizinho; Enter marca ou desmarca; + e − ampliam ou reduzem; 0 volta ao enquadramento " +
    "inicial. Os mesmos valores estão na tabela dos Detalhes.";
  // A lista da busca depende só dos itens com ponto (não da régua nem da pintura): não é refeita a cada passo da régua.
  const pontosDaBusca = useMemo(() => base.pontos.map(ponto => ({ id: ponto.item.id, rotulo: ponto.item.rotulo }))
    .sort((a, b) => a.rotulo.localeCompare(b.rotulo, "pt-BR")), [base.pontos]);

  return <div data-testid="mapa-analise" className={"mapa" + (p.carregando ? " mapa-carregando" : "")} style={variaveis}
    data-pintura={p.pintura} data-pontos={cena.pontos.length} data-contexto={base.fundo.length} data-esmaecidos={cena.esmaecidos}
    data-escala={p.pintura === "continua" ? escalaCor : "nenhuma"} data-esquema={esquema} aria-busy={p.carregando || undefined}>
    <div className="mapa-barra mapa-nao-imprimir">
      <BuscaNoMapa pontos={pontosDaBusca} rotulos={rotulos} onAchar={centrar}/>
    </div>
    <div ref={quadroRef} className="mapa-quadro">
      <canvas ref={canvasRef} data-testid="mapa-canvas" className="mapa-canvas" tabIndex={0} role="img" aria-label={rotuloDoCanvas}
        onKeyDown={teclado} onFocus={aoFocar} onBlur={aoSair}/>
      <div className="mapa-controles mapa-nao-imprimir">
        <button type="button" data-testid="mapa-ampliar" className="mapa-controle" aria-label="Ampliar o mapa" title="Ampliar"
          onClick={() => zoom(ZOOM_BOTAO)}><Plus size={16} aria-hidden="true"/></button>
        <button type="button" data-testid="mapa-reduzir" className="mapa-controle" aria-label="Reduzir o mapa" title="Reduzir"
          onClick={() => zoom(1 / ZOOM_BOTAO)}><Minus size={16} aria-hidden="true"/></button>
        <button type="button" data-testid="mapa-ver-tudo" className="mapa-controle" aria-label="Ver tudo: volta ao enquadramento inicial"
          title="Ver tudo" onClick={verTudo}><Expand size={15} aria-hidden="true"/></button>
      </div>
      <CantoMiniMapa ref={cantoRef} pontos={p.dados.pontos} tamanho={estreito ? 88 : 120}/>
      <DicaDoMapa ref={dicaRef}/>
      {!cena.pontos.length && <p role="status" data-testid="mapa-vazio" className="mapa-vazio">
        Nenhum ponto para desenhar: sem coordenada válida, {artigo(unidade, true)} {unidade.plural} ficam fora do mapa e aparecem em Não
        avaliáveis (Detalhes).</p>}
    </div>
    <div className="mapa-legendas">
      <LegendaDeTamanho maximo={cena.maximoTamanho} rotulo={p.tamanho.rotulo} cores={cores}/>
      {p.pintura === "continua"
        ? <LegendaContinua rotulo={p.rotuloContinuo} dominio={p.dominio} escala={p.escala} indicador={p.indicador} contexto={p.contextoBrasil}
          cores={cores} rampa={rampa}/>
        : <div data-testid="mapa-legenda" data-tipo={p.pintura} className="mapa-legenda" role="group" aria-label="Legenda da cor">
          {p.pintura === "quintis" && <p data-testid="mapa-legenda-quintis" className="mapa-legenda-linha">Cores do mapa: 5 grupos
            iguais (quintis) {INDICADORES_DO_MAPA[p.indicador]}, calculados com {artigo(unidade, true)} {unidade.plural} da
            análise.</p>}
          {p.legendaCor ?? <p>Cor única: nenhuma camada de cor em uso.</p>}</div>}
      <div className="mapa-notas">
        <p data-testid="mapa-nota">{p.brasil === false ? "Cada ponto é a coordenada " + (feminino ? "da " : "do ") + unidade.singular +
          " informada na planilha." : "Cada ponto é a sede do município (IBGE) na base do Brasil."} A posição é só
          para o desenho: o mapa não mede distância.{p.dados.referencial ? " Referencial das coordenadas: " +
          textoDoReferencial(p.dados.referencial) + "." : ""}{semPontoNoResultado ? " Sem coordenada válida, " + umaUnidade(rotulos) +
          " fica fora do mapa e aparece em Não avaliáveis." : ""}</p>
        {simbolos && <p data-testid="mapa-simbolos">{maiuscula(simbolos)}.</p>}
        {segmentos.length > 0 && <p data-testid="mapa-ligacoes">Linhas tracejadas: ligação ilustrativa, não é trajeto. Cada uma liga {p.comTerritoriosBase
          ? "um território da base ou " : ""}{feminino ? "uma " : "um "}{unidade.singular} marcad{feminino ? "a" : "o"} (até 30) {p.referenciaPorItem ? "à referência mais próxima del" +
          (feminino ? "a" : "e") : "ao membro mais próximo da referência"}; a distância é medida em linha reta.</p>}
      </div>
    </div>
  </div>;
});

export default MapaAnalise;

const umaUnidade = (rotulos: RotulosTerritoriais) => (generoDe(rotulos.unidade) === "f" ? "a " : "o ") + rotulos.unidade.singular;

// ================================================================================================ dica
type InfoDaDica = { id: string; dica: Dica; notas: string[]; x: number; y: number; r: number; largura: number; altura: number;
  anunciar: boolean };
type DicaHandle = { mostrar: (info: InfoDaDica | null) => void };

/** A mesma dica do gráfico (montarDica), contida na área do mapa. Estado próprio: o mapa não renderiza a cada movimento. Pelo
 * teclado, a descrição do ponto em foco também vai para a região lida pelos leitores de tela. */
const DicaDoMapa = forwardRef<DicaHandle, object>(function DicaDoMapa(_, ref) {
  const [info, setInfo] = useState<InfoDaDica | null>(null);
  const [posicao, setPosicao] = useState<{ left: number; top: number } | null>(null);
  const caixa = useRef<HTMLDivElement>(null);
  useImperativeHandle(ref, () => ({ mostrar: setInfo }), []);
  useLayoutEffect(() => {
    const elemento = caixa.current;
    if (!info || !elemento) { setPosicao(null); return; }
    const largura = elemento.offsetWidth, altura = elemento.offsetHeight;
    let left = info.x + info.r + 12;
    if (left + largura > info.largura - 4) left = info.x - info.r - 12 - largura;
    left = Math.max(4, Math.min(left, info.largura - largura - 4));
    const top = Math.max(4, Math.min(info.y - 16, info.altura - altura - 4));
    setPosicao({ left, top });
  }, [info]);
  const anuncio = info?.anunciar ? [info.dica.titulo, info.dica.subtitulo, ...info.dica.linhas.map(linha => linha.rotulo + ": " + linha.valor)]
    .filter(Boolean).join(". ") + "." : "";
  return <>
    <p className="sr-only" aria-live="polite" data-testid="mapa-foco">{anuncio}</p>
    {info && <div ref={caixa} role="tooltip" id="mapa-dica" data-testid="mapa-dica" data-id={info.id} className="mapa-dica"
      style={{ left: posicao?.left ?? 0, top: posicao?.top ?? 0, visibility: posicao ? "visible" : "hidden" }}>
      <strong className="mapa-dica-titulo">{info.dica.titulo}</strong>
      {info.dica.subtitulo && <span className="mapa-dica-subtitulo">{info.dica.subtitulo}</span>}
      <dl className="mapa-dica-linhas">
        {info.dica.linhas.map(linha => <div key={linha.rotulo}>
          <dt className="sr-only">{linha.rotulo}</dt>
          <dd><span className="mapa-dica-valor">{linha.valor}</span> <span className="mapa-dica-rotulo">· {linha.rotulo}</span></dd>
        </div>)}
      </dl>
      {[...info.dica.notas, ...info.notas].map(nota => <p key={nota} className="mapa-dica-nota">{nota}</p>)}
    </div>}
  </>;
});

// ================================================================================================ mapinha do canto
type CantoHandle = { definir: (area: Area | null) => void };
/** Com zoom além do inicial, o mapinha mostra onde está a área à vista. Estado próprio, atualizado pelo desenho. */
const CantoMiniMapa = forwardRef<CantoHandle, { pontos: DadosDoMapa["pontos"]; tamanho: number }>(function CantoMiniMapa({ pontos, tamanho }, ref) {
  const [area, setArea] = useState<Area | null>(null);
  useImperativeHandle(ref, () => ({ definir: setArea }), []);
  if (!area) return null;
  return <div className="mapa-mini mapa-nao-imprimir"><MiniMapa pontos={pontos} destaque={null} enquadramento={area} tamanho={tamanho}/></div>;
});

// ================================================================================================ busca por nome
/** "Achar no mapa": escolher um nome centra o mapa no ponto e mostra a dica dele (não marca nada). */
const BuscaNoMapa = memo(function BuscaNoMapa({ pontos, rotulos, onAchar }: { pontos: { id: string; rotulo: string }[];
  rotulos: RotulosTerritoriais; onAchar: (id: string) => void }) {
  const lista = useId();
  const [texto, setTexto] = useState("");
  const [aviso, setAviso] = useState("");
  const indice = useMemo(() => pontos.map(ponto => ({ ...ponto, chave: semAcento(ponto.rotulo) })), [pontos]);
  function achar(valor: string, exato: boolean) {
    const chave = semAcento(valor);
    if (!chave) { setAviso(""); return; }
    const achado = indice.find(ponto => ponto.chave === chave) ?? (exato ? undefined : indice.find(ponto => ponto.chave.includes(chave)));
    if (achado) { onAchar(achado.id); setAviso(""); }
    else if (!exato) setAviso("Nenhum ponto com esse nome no mapa.");
  }
  if (!pontos.length) return null;
  return <div className="mapa-busca-area">
    <label className="mapa-busca">
      <Search size={14} aria-hidden="true"/>
      <span className="sr-only">Achar no mapa pelo nome</span>
      <input type="search" data-testid="mapa-busca" list={lista} value={texto} autoComplete="off"
        placeholder={"Achar " + umA(rotulos.unidade) + " no mapa"}
        onChange={evento => { setTexto(evento.target.value); achar(evento.target.value, true); }}
        onKeyDown={evento => { if (evento.key === "Enter") { evento.preventDefault(); achar(texto, false); } }}/>
    </label>
    <OpcoesDaBusca id={lista} pontos={pontos}/>
    {aviso && <span role="status" className="mapa-busca-aviso">{aviso}</span>}
  </div>;
});
const OpcoesDaBusca = memo(function OpcoesDaBusca({ id, pontos }: { id: string; pontos: { id: string; rotulo: string }[] }) {
  return <datalist id={id}>{pontos.map(ponto => <option key={ponto.id} value={ponto.rotulo}/>)}</datalist>;
});

/** O indicador dos quintis do mapa, na legenda. */
const INDICADORES_DO_MAPA: Record<string, string> = { densidade: "da densidade", quantidade: "da quantidade" };

// ================================================================================================ legendas
/** Legenda de tamanho: três valores de referência com o mesmo raio do desenho (área proporcional). */
function LegendaDeTamanho({ maximo, rotulo, cores }: { maximo: number | null; rotulo: string; cores: CoresDoMapa }) {
  const marcas = marcasDeTamanho(maximo);
  const nome = minusculaInicial(rotulo);
  if (!marcas.length) return <div data-testid="mapa-legenda-tamanho" className="mapa-legenda-tamanho">
    <span>Tamanho: {nome}; sem valores, todos os pontos ficam no tamanho mínimo.</span></div>;
  const maior = Math.max(...marcas.map(marca => marca.raio));
  const baseY = Math.ceil(2 * maior + 6), larguraTexto = 60;
  let anterior = -Infinity;
  const posicoes = marcas.map(marca => {
    const cy = baseY - 2 - marca.raio, topo = cy - marca.raio, y = Math.max(topo + 4, anterior + 12);
    anterior = y;
    return { marca, cy, topo, y };
  });
  const altura = Math.max(baseY, Math.ceil(anterior + 4));
  return <div data-testid="mapa-legenda-tamanho" className="mapa-legenda-tamanho" role="group"
    aria-label={"Tamanho: " + nome + ". Referências: " + marcas.map(marca => compacto(marca.valor)).join(", ")}>
    <svg width={2 * maior + 10 + larguraTexto} height={altura} aria-hidden="true" className="overflow-visible">
      {posicoes.map(({ marca, cy, topo, y }) => <g key={marca.valor} data-testid="mapa-legenda-tamanho-item" data-valor={marca.valor}
        data-raio={marca.raio.toFixed(2)}>
        <circle cx={maior + 2} cy={cy} r={marca.raio} fill="none" stroke={cores.tinta2} strokeWidth={1}/>
        <line x1={maior + 2} x2={2 * maior + 8} y1={topo} y2={y - 4} stroke={cores.eixo} strokeWidth={1}/>
        <text x={2 * maior + 11} y={y} className="mapa-legenda-texto">{compacto(marca.valor)}</text>
      </g>)}
    </svg>
    <span className="mapa-legenda-tamanho-texto">Tamanho: {nome}. Área proporcional; os muito pequenos ficam no tamanho mínimo visível.</span>
  </div>;
}

/** Legenda da cor contínua: a rampa com o mínimo e o máximo do domínio (do motor), marcas de leitura, a marca do Brasil (só
 * contexto) e o aviso de que a cor não é classe nem limiar. */
function LegendaContinua({ rotulo, dominio, escala, indicador, contexto, cores, rampa }: { rotulo: string; dominio: [number, number] | null;
  escala: EscalaDeCor; indicador: PainelIndicador; contexto: { valor: number; rotulo: string } | null; cores: CoresDoMapa;
  rampa: readonly string[] }) {
  if (!dominio || !Number.isFinite(dominio[0]) || !Number.isFinite(dominio[1]))
    return <div data-testid="mapa-legenda" data-tipo="continua" className="mapa-legenda mapa-legenda-continua">
      <p className="mapa-legenda-titulo">{rotulo}</p>
      <p>Sem valores para a cor contínua: os pontos ficam vazados (não avaliáveis), nunca como zero.</p></div>;
  const efetiva = escalaEfetiva(escala, dominio);
  const marcas = marcasDaLegenda(dominio, efetiva);
  const leitura = marcas.filter(marca => !marca.extremo);
  const unico = !(dominio[1] > dominio[0]);
  const brasil = contexto ? posicaoDoContexto(contexto.valor, dominio, efetiva) : null;
  const contagem = indicador === "quantidade" && Number.isInteger(dominio[0]) && Number.isInteger(dominio[1]);
  const minimo = formatarNumero(dominio[0], contagem, [dominio[1]]), maximo = formatarNumero(dominio[1], contagem, [dominio[0]]);
  const aviso = (unico ? "Um só valor: a cor fica no meio da rampa."
    : efetiva === "logaritmica" ? "Escala contínua logarítmica, escolhida por você, entre o menor e o maior valor: a cor avança em passos " +
      "iguais a cada multiplicação do valor, e os valores baixos ficam mais distintos."
    : "Escala contínua linear entre o menor e o maior valor.") +
    (escala === "logaritmica" && efetiva === "linear" ? " A logarítmica só vale com todos os valores positivos." : "") +
    " A cor não é classe nem limiar.";
  return <div data-testid="mapa-legenda" data-tipo="continua" data-escala={efetiva} data-dominio={dominio.join(",")}
    className="mapa-legenda mapa-legenda-continua" role="group" aria-label={"Legenda da cor: " + rotulo}>
    <p className="mapa-legenda-titulo">{rotulo}</p>
    <div className="mapa-rampa-area">
      <div className="mapa-rampa" style={{ background: gradienteDaRampa(rampa) }} aria-hidden="true"/>
      <span className="mapa-rampa-extremo" style={{ left: 0 }} aria-hidden="true"/>
      <span className="mapa-rampa-extremo" style={{ left: "calc(100% - 2px)" }} aria-hidden="true"/>
      {leitura.map(marca => <span key={marca.valor} data-testid="mapa-legenda-marca" data-valor={marca.valor} className="mapa-rampa-marca"
        style={{ left: marca.posicao * 100 + "%" }} aria-hidden="true"/>)}
      {brasil && <span data-testid="mapa-legenda-brasil-marca" data-fora={brasil.fora ? "true" : undefined} className="mapa-rampa-brasil"
        style={{ left: "calc(" + brasil.posicao * 100 + "% - 1px)" }} aria-hidden="true"/>}
    </div>
    {leitura.length > 0 && <div className="mapa-rampa-textos" aria-hidden="true">
      {leitura.map(marca => <span key={marca.valor} style={{ left: marca.posicao * 100 + "%" }}>{textoDaMarca(marca.valor)}</span>)}
    </div>}
    <div className="mapa-extremos">
      <span data-testid="mapa-legenda-min">mín. {minimo}</span>
      {!unico && <span data-testid="mapa-legenda-max">máx. {maximo}</span>}
    </div>
    {contexto && brasil && <p data-testid="mapa-legenda-brasil" className="mapa-legenda-brasil">
      <svg aria-hidden="true" width="12" height="14" className="mapa-legenda-brasil-icone"><line x1="6" y1="1" x2="6" y2="13"
        stroke={cores.tinta} strokeWidth="2" strokeDasharray="3 2"/></svg>
      <span>{contexto.rotulo}{brasil.fora ? " (fora da escala)" : ""} · referência de contexto; não classifica.</span></p>}
    <p data-testid="mapa-legenda-aviso" className="mapa-legenda-aviso">{aviso}</p>
  </div>;
}
