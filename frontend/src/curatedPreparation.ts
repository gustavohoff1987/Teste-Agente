type Mapping = Partial<Record<string, string>>;
type Defaults = {mapping: Mapping};

/** Perfil da base oficial, campo a campo (D1): papéis cuja coluna ainda é a canônica do perfil. Mudar uma coluna tira
 * só aquele papel do perfil; os demais continuam reconhecidos (antes, qualquer mudança desligava o perfil inteiro). */
export function governedRoles(defaults: Defaults | null | undefined, mapping: Mapping): string[] {
  if (!defaults) return [];
  return Object.entries(defaults.mapping).filter(([role, column]) => !!column && mapping[role] === column).map(([role]) => role);
}
