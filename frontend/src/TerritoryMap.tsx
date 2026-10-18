import { forwardRef, useCallback, useEffect, useImperativeHandle, useMemo, useRef, type KeyboardEvent } from "react";
import { Expand, Minus, Plus } from "lucide-react";
import { INK } from "./representation";

// Mapa de pontos em Canvas 2D, sem serviço externo nem chave de API: os pontos são as coordenadas
// autorizadas pelo backend. A projeção equirretangular (longitude × cos da latitude média) serve só
// para desenhar; nenhuma distância é medida no mapa. Milhares de pontos são desenhados por cor em
// lotes; arrasto, zoom e destaque redesenham sob requestAnimationFrame, sem novo estado do React.

export type MapHandle = { snapshot: () => HTMLCanvasElement | null; center: (id: string) => void; reset: () => void };
export type MapProps = {
  ids: string[]; lat: number[]; lon: number[];
  fills: (string | null)[];        // cor por ponto; null = não avaliável (anel vazado)
  passes: boolean[];               // filtro visual: falso = contexto esmaecido
  references: Set<string>;         // losangos
  selected: Set<string>;
  focusId: string | null;
  connections: { from: string; to: string[] }[];
  labelOf: (id: string) => string;
  detailOf: (id: string) => string;
  onSelect: (id: string, additive: boolean) => void;
  ariaLabel: string;
};
type View = { cx: number; cy: number; scale: number };

const RING = INK.surface;

const TerritoryMap = forwardRef<MapHandle, MapProps>(function TerritoryMap(props, handle) {
  const wrap = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  const tooltip = useRef<HTMLDivElement>(null);
  const view = useRef<View | null>(null);
  const size = useRef({ w: 0, h: 0, dpr: 1 });
  const interacted = useRef(false);
  const frame = useRef(0);
  const latest = useRef(props);
  latest.current = props;
  const hover = useRef<number>(-1);

  // Projeção (estado só visual): memória contínua, recalculada apenas quando a geometria muda.
  const world = useMemo(() => {
    const n = props.ids.length;
    const midLat = n ? (Math.min(...props.lat) + Math.max(...props.lat)) / 2 : 0;
    const k = Math.cos(midLat * Math.PI / 180);
    const x = new Float64Array(n), y = new Float64Array(n);
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (let i = 0; i < n; i++) {
      x[i] = props.lon[i] * k; y[i] = -props.lat[i];
      minX = Math.min(minX, x[i]); maxX = Math.max(maxX, x[i]); minY = Math.min(minY, y[i]); maxY = Math.max(maxY, y[i]);
    }
    const index = new Map(props.ids.map((id, i) => [id, i]));
    return { x, y, k, index, bounds: { minX, maxX, minY, maxY } };
  }, [props.ids, props.lat, props.lon]);

  const fit = useCallback((): View => {
    const { w, h } = size.current;
    const { minX, maxX, minY, maxY } = world.bounds;
    if (!Number.isFinite(minX)) return { cx: 0, cy: 0, scale: 1 };
    const pad = 28;
    const spanX = Math.max(maxX - minX, 0.05), spanY = Math.max(maxY - minY, 0.05);
    const scale = Math.min((w - 2 * pad) / spanX, (h - 2 * pad) / spanY, 4000);
    return { cx: (minX + maxX) / 2, cy: (minY + maxY) / 2, scale: Math.max(scale, 0.0001) };
  }, [world]);

  const project = (i: number, v: View) => {
    const { w, h } = size.current;
    return [(world.x[i] - v.cx) * v.scale + w / 2, (world.y[i] - v.cy) * v.scale + h / 2];
  };

  const draw = useCallback(() => {
    frame.current = 0;
    const element = canvas.current;
    const v = view.current;
    if (!element || !v) return;
    const started = performance.now();
    const { w, h, dpr } = size.current;
    const ctx = element.getContext("2d")!;
    const p = latest.current;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = INK.surface; ctx.fillRect(0, 0, w, h);
    drawGraticule(ctx, v, w, h, world.k);
    const fitScale = fit().scale;
    const zoom = v.scale / fitScale;
    const r = Math.min(7, 2.4 * Math.pow(Math.max(zoom, 1), 0.33));
    const n = p.ids.length;
    const sx = new Float32Array(n), sy = new Float32Array(n);
    for (let i = 0; i < n; i++) { const [a, b] = project(i, v); sx[i] = a; sy[i] = b; }
    const inside = (i: number) => sx[i] > -10 && sx[i] < w + 10 && sy[i] > -10 && sy[i] < h + 10;
    // 1. Contexto fora do filtro: pontos pequenos esmaecidos.
    ctx.fillStyle = INK.faint; ctx.beginPath();
    for (let i = 0; i < n; i++) if (!p.passes[i] && inside(i)) { ctx.moveTo(sx[i] + r * 0.7, sy[i]); ctx.arc(sx[i], sy[i], r * 0.7, 0, 2 * Math.PI); }
    ctx.fill();
    // 2. Valores (lotes por cor, anel de superfície separando pontos sobrepostos).
    const groups = new Map<string, number[]>();
    const hollow: number[] = [];
    for (let i = 0; i < n; i++) {
      if (!p.passes[i] || !inside(i) || p.references.has(p.ids[i])) continue;
      const fill = p.fills[i];
      if (fill === null) hollow.push(i); else (groups.get(fill) || groups.set(fill, []).get(fill)!).push(i);
    }
    ctx.lineWidth = 0.8; ctx.strokeStyle = RING;
    for (const [fill, members] of groups) {
      ctx.fillStyle = fill; ctx.beginPath();
      for (const i of members) { ctx.moveTo(sx[i] + r, sy[i]); ctx.arc(sx[i], sy[i], r, 0, 2 * Math.PI); }
      ctx.fill(); ctx.stroke();
    }
    // 3. Não avaliáveis: anel vazado cinza, distinto de qualquer valor (RQ-REP-04).
    ctx.fillStyle = INK.surface; ctx.strokeStyle = INK.muted; ctx.lineWidth = 1.4; ctx.beginPath();
    for (const i of hollow) { ctx.moveTo(sx[i] + r, sy[i]); ctx.arc(sx[i], sy[i], r, 0, 2 * Math.PI); }
    ctx.fill(); ctx.stroke();
    // 4. Conexões ilustrativas (tracejadas) entre alvo selecionado e referência mais próxima.
    ctx.setLineDash([5, 4]); ctx.strokeStyle = INK.secondary; ctx.lineWidth = 1.4; ctx.beginPath();
    for (const link of p.connections) {
      const a = world.index.get(link.from);
      if (a === undefined) continue;
      for (const to of link.to) {
        const b = world.index.get(to);
        if (b === undefined || b === a) continue;
        ctx.moveTo(sx[a], sy[a]); ctx.lineTo(sx[b], sy[b]);
      }
    }
    ctx.stroke(); ctx.setLineDash([]);
    // 5. Referências: losangos por cima dos valores; fora do filtro, esmaecidos (contexto), salvo as
    //    ligadas a um alvo selecionado.
    const linked = new Set(p.connections.flatMap(link => link.to));
    const diamond = (i: number, d: number) => {
      ctx.beginPath(); ctx.moveTo(sx[i], sy[i] - d); ctx.lineTo(sx[i] + d, sy[i]); ctx.lineTo(sx[i], sy[i] + d); ctx.lineTo(sx[i] - d, sy[i]); ctx.closePath();
    };
    ctx.lineWidth = 0.8; ctx.strokeStyle = "#c3c2b7"; ctx.fillStyle = INK.faint;
    for (let i = 0; i < n; i++) {
      if (!p.references.has(p.ids[i]) || !inside(i) || p.passes[i] || linked.has(p.ids[i])) continue;
      diamond(i, r + 0.6); ctx.fill(); ctx.stroke();
    }
    ctx.lineWidth = 1.3; ctx.strokeStyle = INK.primary;
    for (let i = 0; i < n; i++) {
      if (!p.references.has(p.ids[i]) || !inside(i) || !(p.passes[i] || linked.has(p.ids[i]))) continue;
      diamond(i, r + 1.6); ctx.fillStyle = p.fills[i] ?? INK.surface; ctx.fill(); ctx.stroke();
    }
    // 6. Seleção e foco: anéis escuros (estado visual; não altera a classe).
    ctx.strokeStyle = INK.primary;
    for (const id of p.selected) {
      const i = world.index.get(id);
      if (i === undefined) continue;
      ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(sx[i], sy[i], r + 3.5, 0, 2 * Math.PI); ctx.stroke();
    }
    const focus = p.focusId !== null ? world.index.get(p.focusId) : undefined;
    if (focus !== undefined) { ctx.lineWidth = 1.5; ctx.beginPath(); ctx.arc(sx[focus], sy[focus], r + 7, 0, 2 * Math.PI); ctx.stroke(); }
    if (hover.current >= 0 && hover.current < n) {
      const i = hover.current;
      ctx.lineWidth = 1.5; ctx.strokeStyle = INK.secondary; ctx.beginPath(); ctx.arc(sx[i], sy[i], r + 2.5, 0, 2 * Math.PI); ctx.stroke();
    }
    // 7. Poucos territórios: nome (e, até três, o valor) junto ao ponto, com halo da superfície; um ponto
    //    isolado sem nome não diz onde nem o quê.
    if (n <= 12) {
      ctx.lineJoin = "round";
      for (let i = 0; i < n; i++) {
        if (!p.passes[i] || !inside(i)) continue;
        const lines = [[p.labelOf(p.ids[i]), "600 12px system-ui, sans-serif", INK.primary],
          ...(n <= 3 ? [[p.detailOf(p.ids[i]), "11px system-ui, sans-serif", INK.secondary]] : [])];
        lines.forEach(([text, font, color], line) => {
          ctx.font = font; ctx.lineWidth = 3; ctx.strokeStyle = INK.surface;
          const x = Math.min(sx[i] + r + 6, w - ctx.measureText(text).width - 4), y = sy[i] + 4 + line * 15;
          ctx.strokeText(text, x, y); ctx.fillStyle = color; ctx.fillText(text, x, y);
        });
      }
    }
    // Gancho de teste e medição (só com window.__ADT_TEST__): tempo de desenho, zoom e posição de cada ponto.
    const scope = window as unknown as { __ADT_TEST__?: boolean; __adtMapStats?: unknown[]; __adtMapLocate?: (id: string) => number[] | null };
    if (scope.__ADT_TEST__) {
      scope.__adtMapStats = [...(scope.__adtMapStats || []).slice(-199),
        { drawMs: performance.now() - started, points: n, at: performance.now(), zoom, cx: v.cx, cy: v.cy, w, h }];
      scope.__adtMapLocate = (id: string) => { const i = world.index.get(id); return i === undefined || !view.current ? null : project(i, view.current); };
    }
  }, [world, fit]);

  const schedule = useCallback(() => { if (!frame.current) frame.current = requestAnimationFrame(draw); }, [draw]);

  // Tamanho do canvas (densidade de pixels do dispositivo) e novo enquadramento se o usuário não navegou.
  useEffect(() => {
    const element = wrap.current;
    if (!element) return;
    const observer = new ResizeObserver(() => {
      const target = canvas.current;
      if (!target) return;  // notificação entregue depois de o mapa sair da tela (troca de aba)
      const w = Math.max(element.clientWidth, 1), h = Math.max(element.clientHeight, 1), dpr = Math.min(window.devicePixelRatio || 1, 2);
      size.current = { w, h, dpr };
      target.width = Math.round(w * dpr); target.height = Math.round(h * dpr);
      if (!view.current || !interacted.current) view.current = fit();
      draw();
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
      if (frame.current) cancelAnimationFrame(frame.current);
      frame.current = 0;
    };
  }, [fit, draw]);

  useEffect(() => { if (!interacted.current && size.current.w) view.current = fit(); schedule(); }, [world, fit, schedule]);
  useEffect(() => { schedule(); }, [props.fills, props.passes, props.references, props.selected, props.focusId, props.connections, schedule]);

  const zoomAt = useCallback((factor: number, px?: number, py?: number) => {
    const v = view.current;
    if (!v) return;
    const { w, h } = size.current;
    const fx = px ?? w / 2, fy = py ?? h / 2;
    const base = fit().scale;
    const scale = Math.min(Math.max(v.scale * factor, base * 0.6), base * 600);
    const wx = v.cx + (fx - w / 2) / v.scale, wy = v.cy + (fy - h / 2) / v.scale;
    view.current = { cx: wx - (fx - w / 2) / scale, cy: wy - (fy - h / 2) / scale, scale };
    interacted.current = true;
    schedule();
  }, [fit, schedule]);

  const pick = useCallback((px: number, py: number, radius = 12): number => {
    const v = view.current;
    if (!v) return -1;
    const p = latest.current;
    let best = -1, bestDistance = radius * radius, bestPasses = false;
    for (let i = 0; i < p.ids.length; i++) {
      const [x, y] = project(i, v);
      const d = (x - px) ** 2 + (y - py) ** 2;
      // Pontos no filtro têm prioridade sobre o contexto esmaecido.
      if ((d < bestDistance && (p.passes[i] || !bestPasses)) || (p.passes[i] && !bestPasses && d < radius * radius)) {
        best = i; bestDistance = d; bestPasses = p.passes[i];
      }
    }
    return best;
  }, [world]);

  useImperativeHandle(handle, () => ({
    snapshot: () => canvas.current,
    center: (id: string) => {
      const i = world.index.get(id);
      if (i === undefined || !view.current) return;
      const scale = Math.max(view.current.scale, fit().scale * 6);
      view.current = { cx: world.x[i], cy: world.y[i], scale };
      interacted.current = true; schedule();
    },
    reset: () => { interacted.current = false; view.current = fit(); schedule(); },
  }), [world, fit, schedule]);

  // Arrasto, pinça e clique (Pointer Events); zoom pela roda só com Ctrl/⌘ ou com o mapa em foco.
  useEffect(() => {
    const element = canvas.current;
    if (!element) return;
    const pointers = new Map<number, { x: number; y: number }>();
    let moved = 0, pinch = 0;
    const local = (event: PointerEvent | WheelEvent | MouseEvent) => {
      const box = element.getBoundingClientRect();
      return [event.clientX - box.left, event.clientY - box.top];
    };
    const showTooltip = (index: number, x: number, y: number) => {
      const tip = tooltip.current;
      if (!tip) return;
      if (index < 0) { tip.hidden = true; return; }
      const p = latest.current;
      tip.hidden = false;
      tip.querySelector("strong")!.textContent = p.labelOf(p.ids[index]);
      tip.querySelector("span")!.textContent = p.detailOf(p.ids[index]);
      const { w, h } = size.current;
      const width = tip.offsetWidth, height = tip.offsetHeight;
      tip.style.left = Math.min(Math.max(x + 12, 4), w - width - 4) + "px";
      tip.style.top = (y + 14 + height > h ? Math.max(y - height - 12, 4) : y + 14) + "px";
    };
    const down = (event: PointerEvent) => {
      element.setPointerCapture(event.pointerId);
      const [x, y] = local(event);
      pointers.set(event.pointerId, { x, y });
      moved = 0;
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        pinch = Math.hypot(a.x - b.x, a.y - b.y);
      }
    };
    const move = (event: PointerEvent) => {
      const [x, y] = local(event);
      const previous = pointers.get(event.pointerId);
      if (!previous) {
        if (event.pointerType === "mouse") {
          const index = pick(x, y);
          if (index !== hover.current) { hover.current = index; schedule(); }
          showTooltip(index, x, y);
          element.style.cursor = index >= 0 ? "pointer" : "grab";
        }
        return;
      }
      pointers.set(event.pointerId, { x, y });
      const v = view.current;
      if (!v) return;
      if (pointers.size === 2) {
        const [a, b] = [...pointers.values()];
        const distance = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinch > 0) zoomAt(distance / pinch, (a.x + b.x) / 2, (a.y + b.y) / 2);
        pinch = distance; moved += 10;
        return;
      }
      const dx = x - previous.x, dy = y - previous.y;
      moved += Math.abs(dx) + Math.abs(dy);
      if (moved > 3) {
        view.current = { ...v, cx: v.cx - dx / v.scale, cy: v.cy - dy / v.scale };
        interacted.current = true; showTooltip(-1, 0, 0); schedule();
      }
    };
    const up = (event: PointerEvent) => {
      const [x, y] = local(event);
      const wasClick = pointers.size === 1 && moved <= 3;
      pointers.delete(event.pointerId);
      if (pointers.size < 2) pinch = 0;
      if (wasClick) {
        const index = pick(x, y, event.pointerType === "mouse" ? 12 : 18);
        if (index >= 0) latest.current.onSelect(latest.current.ids[index], event.shiftKey || event.ctrlKey || event.metaKey);
      }
    };
    const leave = () => { hover.current = -1; showTooltip(-1, 0, 0); schedule(); };
    const wheel = (event: WheelEvent) => {
      if (!(event.ctrlKey || event.metaKey || document.activeElement === element)) return;
      event.preventDefault();
      const [x, y] = local(event);
      zoomAt(Math.exp(-event.deltaY * 0.0015), x, y);
    };
    const dbl = (event: MouseEvent) => { const [x, y] = local(event); zoomAt(2, x, y); };
    element.addEventListener("pointerdown", down);
    element.addEventListener("pointermove", move);
    element.addEventListener("pointerup", up);
    element.addEventListener("pointercancel", up);
    element.addEventListener("pointerleave", leave);
    element.addEventListener("wheel", wheel, { passive: false });
    element.addEventListener("dblclick", dbl);
    return () => {
      element.removeEventListener("pointerdown", down);
      element.removeEventListener("pointermove", move);
      element.removeEventListener("pointerup", up);
      element.removeEventListener("pointercancel", up);
      element.removeEventListener("pointerleave", leave);
      element.removeEventListener("wheel", wheel);
      element.removeEventListener("dblclick", dbl);
    };
  }, [pick, zoomAt, schedule]);

  const keyboard = (event: KeyboardEvent) => {
    const v = view.current;
    if (!v) return;
    const step = 60 / v.scale;
    const moves: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (moves[event.key]) {
      view.current = { ...v, cx: v.cx + moves[event.key][0], cy: v.cy + moves[event.key][1] };
      interacted.current = true; schedule(); event.preventDefault();
    } else if (event.key === "+" || event.key === "=") { zoomAt(1.5); event.preventDefault(); }
    else if (event.key === "-" || event.key === "_") { zoomAt(1 / 1.5); event.preventDefault(); }
    else if (event.key === "0" || event.key === "Home") { interacted.current = false; view.current = fit(); schedule(); event.preventDefault(); }
  };

  const button = "flex h-9 w-9 items-center justify-center rounded-lg border border-line bg-white text-slate-700 shadow-sm hover:bg-slate-50";
  return <div ref={wrap} className="relative h-[440px] w-full overflow-hidden rounded-xl border border-line bg-[#fcfcfb] max-sm:h-[360px]">
    <canvas ref={canvas} tabIndex={0} role="img" aria-label={props.ariaLabel} onKeyDown={keyboard} data-testid="territory-map"
      className="absolute inset-0 h-full w-full touch-none outline-none focus-visible:ring-2 focus-visible:ring-teal" style={{ cursor: "grab" }}/>
    <div ref={tooltip} hidden role="tooltip" className="pointer-events-none absolute z-10 max-w-[240px] rounded-lg border border-line bg-white px-2.5 py-1.5 text-xs shadow-card">
      <strong className="block text-ink"/><span className="block text-slate-600"/>
    </div>
    <div className="no-print absolute right-2 top-2 flex flex-col gap-1.5">
      <button type="button" aria-label="Ampliar o mapa" title="Ampliar" className={button} onClick={() => zoomAt(1.6)}><Plus size={16}/></button>
      <button type="button" aria-label="Reduzir o mapa" title="Reduzir" className={button} onClick={() => zoomAt(1 / 1.6)}><Minus size={16}/></button>
      <button type="button" aria-label="Ver a extensão completa" title="Extensão completa" className={button}
        onClick={() => { interacted.current = false; view.current = fit(); schedule(); }}><Expand size={15}/></button>
    </div>
  </div>;
});

function drawGraticule(ctx: CanvasRenderingContext2D, v: View, w: number, h: number, k: number) {
  const pxPerDegree = v.scale;
  const step = [20, 10, 5, 2, 1, 0.5, 0.25, 0.1, 0.05, 0.02, 0.01].find(candidate => candidate * pxPerDegree * Math.max(k, 0.3) <= 160 && candidate * pxPerDegree * Math.max(k, 0.3) >= 50) ?? 10;
  const left = v.cx - w / 2 / v.scale, right = v.cx + w / 2 / v.scale, top = v.cy - h / 2 / v.scale, bottom = v.cy + h / 2 / v.scale;
  ctx.strokeStyle = INK.grid; ctx.lineWidth = 1; ctx.fillStyle = INK.muted; ctx.font = "10px system-ui, sans-serif";
  ctx.beginPath();
  for (let lon = Math.ceil(left / k / step) * step; lon * k <= right; lon += step) {
    const x = (lon * k - v.cx) * v.scale + w / 2;
    ctx.moveTo(x, 0); ctx.lineTo(x, h);
  }
  for (let lat = Math.ceil(-bottom / step) * step; -lat >= top; lat += step) {
    const y = (-lat - v.cy) * v.scale + h / 2;
    ctx.moveTo(0, y); ctx.lineTo(w, y);
  }
  ctx.stroke();
  for (let lon = Math.ceil(left / k / step) * step; lon * k <= right; lon += step)
    ctx.fillText(Math.abs(lon).toFixed(step < 1 ? 2 : 0).replace(".", ",") + "°" + (lon < 0 ? "O" : lon > 0 ? "L" : ""), (lon * k - v.cx) * v.scale + w / 2 + 3, h - 4);
  for (let lat = Math.ceil(-bottom / step) * step; -lat >= top; lat += step)
    ctx.fillText(Math.abs(lat).toFixed(step < 1 ? 2 : 0).replace(".", ",") + "°" + (lat < 0 ? "S" : lat > 0 ? "N" : ""), 4, (-lat - v.cy) * v.scale + h / 2 - 3);
}

export default TerritoryMap;
