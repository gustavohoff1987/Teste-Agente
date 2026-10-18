type Mapping = Partial<Record<string, string>>;
type Defaults = {mapping: Mapping; category: string; count_unit: string;
  fts_scope_confirmed: boolean; object_confirmed: boolean; population_denominator_confirmed: boolean};

/** Evidência do perfil oficial só vale enquanto os significados reconhecidos forem preservados. */
export function matchesCuratedPreparation(defaults: Defaults | null | undefined, current: {
  official: boolean; mapping: Mapping; category: string; countUnit: string;
  fts: boolean; object: boolean; population: boolean;
}): boolean {
  if (!current.official || !defaults || current.category !== defaults.category || current.countUnit !== defaults.count_unit ||
    current.fts !== defaults.fts_scope_confirmed || current.object !== defaults.object_confirmed ||
    current.population !== defaults.population_denominator_confirmed) return false;
  return [...new Set([...Object.keys(defaults.mapping), ...Object.keys(current.mapping)])]
    .every(role => (defaults.mapping[role] || "") === (current.mapping[role] || ""));
}
