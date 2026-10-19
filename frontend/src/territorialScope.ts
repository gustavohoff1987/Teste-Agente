// Abrangência territorial da base oficial (D3): Brasil (total nacional), estados (soma dos municípios pelo código IBGE),
// "Todos os municípios" e municípios, agrupados por estado. Funções puras: só organizam o que o usuário marcou e o que o
// backend informou (bloco "niveis" da inspeção). Nenhum valor, soma, mínimo ou classe é calculado aqui; as regras de
// cada análise (aceita, padrão, motivos e texto) vêm do backend, que confere de novo o pedido.

export type Level = "brasil" | "estado" | "municipio";
export type LevelRule = {
  aceita: Level[]; estado_como: "objeto" | "expansao" | null; minimo: number; combinacao: string;
  padrao: "brasil" | "todos_municipios" | null; disponivel: boolean; texto: string; motivos: Partial<Record<Level, string>>;
};
export type StateInfo = { prefixo: string; sigla: string; nome: string; rotulo: string; rotulo_grupo: string; municipios: number };
export type Levels = {
  brasil: { disponivel: boolean; motivo: string; periodos: string[] };
  estados: StateInfo[]; municipios: { total: number }; operacoes: Record<string, LevelRule>;
};
/** O que o usuário marcou além dos municípios (estes ficam na seleção compartilhada de identificadores). */
export type ScopeSelection = { brasil: boolean; estados: string[]; todos: boolean; grupos: string[] };
export type Abrangencia = { brasil: boolean; estados: string[]; municipios: { todos: boolean; estados: string[]; ids: string[] } };
export type Effective = { abrangencia: Abrangencia; padrao: boolean };

export const EMPTY_SCOPE: ScopeSelection = { brasil: false, estados: [], todos: false, grupos: [] };
const sorted = (values: string[]) => [...new Set(values)].sort((a, b) => a.localeCompare(b, "pt-BR", { numeric: true }));
const accepts = (rule: LevelRule, level: Level) => rule.disponivel && rule.aceita.includes(level);
/** Prefixo do estado (dois primeiros dígitos do código IBGE) de um identificador "code:"; vazio fora dele. */
export const prefixOf = (id: string) => id.startsWith("code:") ? id.slice(5, 7) : "";

/** Seleção que vale nesta análise: só os níveis que ela aceita. Sem nada aplicável, vale o padrão da análise
 * (Brasil ou todos os municípios). Análise indisponível para níveis (rotatividade): null, e o pedido segue sem abrangência. */
export function effectiveScope(scope: ScopeSelection, ids: string[], rule: LevelRule | undefined): Effective | null {
  if (!rule || !rule.disponivel) return null;
  const municipal = accepts(rule, "municipio");
  const brasil = accepts(rule, "brasil") && scope.brasil;
  const estados = accepts(rule, "estado") ? sorted(scope.estados) : [];
  const todos = municipal && scope.todos;
  const grupos = municipal && !todos ? sorted(scope.grupos) : [];
  const chosen = municipal && !todos ? [...new Set(ids)] : [];  // ordem da escolha; o backend normaliza a ordem na chave
  if (brasil || estados.length || todos || grupos.length || chosen.length)
    return { abrangencia: { brasil, estados, municipios: { todos, estados: grupos, ids: chosen } }, padrao: false };
  const national = rule.padrao === "brasil" && accepts(rule, "brasil");
  return { abrangencia: { brasil: national, estados: [], municipios: { todos: !national, estados: [], ids: [] } }, padrao: true };
}

function municipalCount(municipios: Abrangencia["municipios"], levels: Levels | undefined): number {
  const size = (prefix: string) => levels?.estados.find(item => item.prefixo === prefix)?.municipios || 0;
  return municipios.todos ? levels?.municipios.total || 0
    : municipios.estados.reduce((total, prefix) => total + size(prefix), 0) +
      municipios.ids.filter(id => !municipios.estados.includes(prefixOf(id))).length;
}

/** Seleção só de municípios (uploads e base sem o bloco de níveis): os marcados ou, sem marcação, todos. */
export function municipalOnly(ids: string[]): Effective {
  return { abrangencia: { brasil: false, estados: [], municipios: { todos: !ids.length, estados: [], ids } }, padrao: !ids.length };
}

/** Itens marcados que valem nesta análise (Brasil + estados + municípios; "Todos" e grupos contam os seus municípios).
 * Sem marcação, zero: vale o padrão da análise. */
export function countSelected(effective: Effective | null, levels: Levels | undefined): number {
  if (!effective || effective.padrao) return 0;
  const { brasil, estados, municipios } = effective.abrangencia;
  return Number(brasil) + estados.length + municipalCount(municipios, levels);
}

/** Composição curta da seleção: "Brasil · 2 estados · 3 municípios". */
export function breakdown(effective: Effective | null, levels: Levels | undefined): string {
  if (!effective) return "";
  const { brasil, estados, municipios } = effective.abrangencia;
  const parts: string[] = [];
  if (brasil) parts.push("Brasil");
  if (estados.length) parts.push(estados.length + (estados.length === 1 ? " estado" : " estados"));
  const n = municipalCount(municipios, levels);
  if (municipios.todos || n) parts.push(n.toLocaleString("pt-BR") + (n === 1 ? " município" : " municípios"));
  return parts.join(" · ");
}

const joined = (parts: string[]) => parts.length < 2 ? parts.join("") : parts.slice(0, -1).join(", ") + " e " + parts[parts.length - 1];

/** Valor da caixa "Abrangência territorial", na ordem Brasil → estados → municípios. `nameOf` dá o nome do município
 * com a UF ("MANAUS (AM)"); os rótulos dos estados e dos grupos vêm do backend. */
export function describeScope(effective: Effective | null, levels: Levels | undefined, nameOf: (id: string) => string): string {
  if (!effective) return "Todos os municípios";
  const { brasil, estados, municipios } = effective.abrangencia;
  const state = (prefix: string) => levels?.estados.find(item => item.prefixo === prefix);
  const parts: string[] = [];
  if (brasil) parts.push("Brasil (total nacional)");
  const names = estados.map(prefix => state(prefix)?.nome || prefix);
  if (names.length === 1) parts.push(names[0] + " (estado)");
  else if (names.length === 2) parts.push(names[0] + " e " + names[1] + " (estados)");
  else if (names.length) parts.push(names.length + " estados");
  if (municipios.todos) parts.push("Todos os municípios");
  for (const prefix of municipios.estados) {
    const item = state(prefix);
    parts.push(item ? item.rotulo_grupo + " (" + item.municipios.toLocaleString("pt-BR") + ")" : "Municípios " + prefix);
  }
  const loose = municipios.ids.map(nameOf);
  if (loose.length && !parts.length) {
    parts.push(loose.length <= 2 ? loose.join(" e ") : loose.length + " municípios: " + loose.slice(0, 2).join(", ") +
      " e mais " + (loose.length - 2));
    return parts[0];
  }
  if (loose.length) parts.push(loose.length === 1 ? loose[0] : loose.length + " municípios");
  return parts.length ? joined(parts) : "Nenhum território";
}

export type Toggle = { kind: "brasil" } | { kind: "estado"; prefix: string } | { kind: "todos_estados"; prefixes: string[] } |
  { kind: "todos" } | { kind: "grupo"; prefix: string; members: string[] } | { kind: "municipio"; id: string; members?: string[] };

/** Marcar ou desmarcar um item. A primeira marcação substitui o padrão da análise (o padrão nunca é copiado). Um grupo
 * marcado absorve os municípios dele; desmarcar um município de um grupo marcado deixa os demais marcados. */
export function toggle(scope: ScopeSelection, ids: string[], item: Toggle): { scope: ScopeSelection; ids: string[] } {
  const without = (list: string[], value: string) => list.filter(entry => entry !== value);
  switch (item.kind) {
    case "brasil": return { scope: { ...scope, brasil: !scope.brasil }, ids };
    case "estado": return { scope: { ...scope, estados: scope.estados.includes(item.prefix) ? without(scope.estados, item.prefix)
      : sorted([...scope.estados, item.prefix]) }, ids };
    case "todos_estados": {
      const all = item.prefixes.every(prefix => scope.estados.includes(prefix));
      return { scope: { ...scope, estados: all ? [] : sorted(item.prefixes) }, ids };
    }
    case "todos": return scope.todos ? { scope: { ...scope, todos: false }, ids }
      : { scope: { ...scope, todos: true, grupos: [] }, ids: [] };
    case "grupo": {
      if (scope.grupos.includes(item.prefix)) return { scope: { ...scope, grupos: without(scope.grupos, item.prefix) }, ids };
      const members = new Set(item.members);
      const full = item.members.length > 0 && item.members.every(id => ids.includes(id));
      if (full) return { scope, ids: ids.filter(id => !members.has(id)) };
      return { scope: { ...scope, grupos: sorted([...scope.grupos, item.prefix]) }, ids: ids.filter(id => !members.has(id)) };
    }
    case "municipio": {
      const prefix = prefixOf(item.id);
      if (scope.todos) return { scope, ids };
      if (prefix && scope.grupos.includes(prefix))
        return { scope: { ...scope, grupos: without(scope.grupos, prefix) },
          ids: [...ids, ...(item.members || []).filter(id => id !== item.id && !ids.includes(id))] };
      return { scope, ids: ids.includes(item.id) ? without(ids, item.id) : [...ids, item.id] };
    }
  }
}

/** Estado da caixa de um grupo de municípios: marcada, parcial (tri-estado) ou desmarcada. */
export function groupState(prefix: string, scope: ScopeSelection, ids: string[], members: string[]): "checked" | "mixed" | "unchecked" {
  if (scope.todos || scope.grupos.includes(prefix)) return "checked";
  const marked = members.filter(id => ids.includes(id)).length;
  return marked && marked === members.length ? "checked" : marked ? "mixed" : "unchecked";
}

/** Itens de um resultado (ids "br", "uf:NN" e "code:…") levados de volta à seleção: Brasil, estados e municípios. */
export function fromMembers(members: string[]): { scope: ScopeSelection; ids: string[] } {
  return { scope: { ...EMPTY_SCOPE, brasil: members.includes("br"),
    estados: sorted(members.filter(id => id.startsWith("uf:")).map(id => id.slice(3))) },
    ids: members.filter(id => id.startsWith("code:") || id.startsWith("name:")) };
}

/** Competências oferecidas na caixa Período: com o Brasil e outro nível, a união das duas fontes (cada nível mostra a
 * própria ausência no resultado); só com o Brasil, as da fonte nacional; nos demais casos, as da fonte municipal. */
export function periodsForScope(effective: Effective | null, national: string[], municipal: string[]): string[] {
  if (!effective || !effective.abrangencia.brasil) return municipal;
  const { estados, municipios } = effective.abrangencia;
  const others = estados.length > 0 || municipios.todos || municipios.estados.length > 0 || municipios.ids.length > 0;
  return others ? sorted([...national, ...municipal]) : national;
}
