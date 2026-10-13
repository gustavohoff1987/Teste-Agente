// Árvore de critérios no formato aceito pelo motor (CAP-SUB-01). Só estrutura o que o usuário
// escolheu: nenhum operador, valor, unidade ou referência é sugerido aqui.
export type Attribute = "densidade" | "quantidade" | "populacao" | "distancia" | "territorio" | "uf";
export type NumericAttribute = "densidade" | "quantidade" | "populacao" | "distancia";
export type Leaf = { id: string; attribute: Attribute; operator: string; value: string | string[]; unit?: string; category?: string };
export type Composite = { id?: string; logic: "and" | "or" | "not"; operands: CriteriaNode[] };
export type CriteriaNode = Leaf | Composite;
export type RankingSpec = { attribute: NumericAttribute; direction: "asc" | "desc" | ""; top_n?: number; exact_n?: boolean; set?: "atende" | "universo" };
export type BandsSpec = { attribute: NumericAttribute; limits: string[] };

export const ATTRIBUTE_LABELS: Record<Attribute, string> = {
  densidade: "Densidade", quantidade: "Quantidade", populacao: "População",
  distancia: "Distância à referência mais próxima", territorio: "Território", uf: "UF",
};
export const NUMERIC_OPERATORS: [string, string][] = [["<", "<"], ["<=", "≤"], [">", ">"], [">=", "≥"], ["=", "="], ["!=", "≠"]];
export const UNITS: Partial<Record<Attribute, [string, string][]>> = {
  densidade: [["por_1000_habitantes", "por 1.000 habitantes"], ["por_10000_habitantes", "por 10.000 habitantes"],
    ["por_100000_habitantes", "por 100.000 habitantes"]],
  distancia: [["km", "km"], ["m", "m"]],
};
const SYMBOL: Record<string, string> = { "<": "<", "<=": "≤", ">": ">", ">=": "≥", "=": "=", "!=": "≠", in: "pertence a", not_in: "não pertence a" };

export const isLeaf = (node: CriteriaNode): node is Leaf => "attribute" in node;

export function leaves(node: CriteriaNode | null): Leaf[] {
  if (!node) return [];
  return isLeaf(node) ? [node] : node.operands.flatMap(leaves);
}

export function nextId(node: CriteriaNode | null): string {
  const used = leaves(node).map(leaf => Number(/^c(\d+)$/.exec(leaf.id)?.[1] || 0));
  return "c" + (Math.max(0, ...used) + 1);
}

// Critérios sucessivos: E com o que já existe (CAP-SUB-01); OU só por escolha explícita.
export function addCondition(node: CriteriaNode | null, leaf: Leaf, logic: "and" | "or"): CriteriaNode {
  if (!node) return leaf;
  if (!isLeaf(node) && node.logic === logic) return {...node, operands: [...node.operands, leaf]};
  return {logic, operands: [node, leaf]};
}

export function updateLeaf(node: CriteriaNode, id: string, patch: Partial<Leaf>): CriteriaNode {
  if (isLeaf(node)) return node.id === id ? {...node, ...patch} : node;
  return {...node, operands: node.operands.map(child => updateLeaf(child, id, patch))};
}

export function removeLeaf(node: CriteriaNode | null, id: string): CriteriaNode | null {
  if (!node) return null;
  if (isLeaf(node)) return node.id === id ? null : node;
  const operands = node.operands.map(child => removeLeaf(child, id)).filter((child): child is CriteriaNode => !!child);
  if (node.logic === "not") return operands.length ? {...node, operands} : null;
  return operands.length === 0 ? null : operands.length === 1 ? operands[0] : {...node, operands};
}

export function isNegated(node: CriteriaNode | null, id: string): boolean {
  if (!node || isLeaf(node)) return false;
  if (node.logic === "not" && isLeaf(node.operands[0]) && node.operands[0].id === id) return true;
  return node.operands.some(child => isNegated(child, id));
}

export function toggleNegation(node: CriteriaNode, id: string): CriteriaNode {
  if (isLeaf(node)) return node.id === id ? {logic: "not", operands: [node]} : node;
  if (node.logic === "not" && isLeaf(node.operands[0]) && node.operands[0].id === id) return node.operands[0];
  return {...node, operands: node.operands.map(child => toggleNegation(child, id))};
}

export function unitText(leaf: Leaf, countUnit = ""): string {
  const chosen = UNITS[leaf.attribute]?.find(([value]) => value === leaf.unit)?.[1];
  if (chosen) return chosen;
  return {densidade: "por 1.000 habitantes", distancia: "km", populacao: "habitantes", quantidade: countUnit || "unidade de contagem",
    territorio: "", uf: ""}[leaf.attribute];
}

export function describeLeaf(leaf: Leaf, countUnit = ""): string {
  const value = Array.isArray(leaf.value) ? (leaf.attribute === "uf" ? leaf.value.join(", ") : leaf.value.length + " território(s)")
    : String(leaf.value || "?").replace(".", ",");
  const unit = unitText(leaf, countUnit);
  return [ATTRIBUTE_LABELS[leaf.attribute].toLowerCase(), SYMBOL[leaf.operator] || "?", value, unit].filter(Boolean).join(" ") +
    (leaf.category ? " (" + leaf.category + ")" : "");
}

export function describe(node: CriteriaNode | null, countUnit = ""): string {
  if (!node) return "";
  if (isLeaf(node)) return describeLeaf(node, countUnit);
  if (node.logic === "not") return "NÃO (" + describe(node.operands[0], countUnit) + ")";
  return "(" + node.operands.map(child => describe(child, countUnit)).join(node.logic === "and" ? " E " : " OU ") + ")";
}

export function uses(node: CriteriaNode | null, attribute: Attribute, ranking?: RankingSpec | null, bands?: BandsSpec | null): boolean {
  return leaves(node).some(leaf => leaf.attribute === attribute) || ranking?.attribute === attribute || bands?.attribute === attribute;
}

// Condição completa o bastante para o motor validar: operador escolhido e valor informado.
export function complete(node: CriteriaNode | null): boolean {
  return leaves(node).every(leaf => !!leaf.operator && (Array.isArray(leaf.value) ? leaf.value.length > 0 : !!String(leaf.value).trim()));
}
