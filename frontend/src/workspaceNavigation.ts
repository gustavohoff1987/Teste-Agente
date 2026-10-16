/** Move somente a área rolável da análise, preservando a conversa e o histórico. */
export function scrollAnalysisTo(id: string): boolean {
  const target = document.getElementById(id);
  const panel = target?.closest<HTMLElement>(".analysis-scroll");
  if (!target || !panel) return false;
  const top = panel.scrollTop + target.getBoundingClientRect().top - panel.getBoundingClientRect().top - 12;
  panel.scrollTo({top: Math.max(0, top), behavior: "smooth"});
  return true;
}
