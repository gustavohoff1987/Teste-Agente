/** Navegação no fluxo único, respeitando movimento reduzido. */
export function scrollAnalysisTo(id: string): boolean {
  const target = document.getElementById(id);
  if (!target) return false;
  if (target.closest(".preparation-context")) window.dispatchEvent(new Event("adt:prepare"));
  requestAnimationFrame(() => target.scrollIntoView({block: "start", behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth"}));
  return true;
}
