// Modelo puro do Simulador de Cenários Territoriais (comando V22, Eixo II, etapa 4; Docs/SIMULADOR_DE_CENARIOS.md): a seleção local
// (uma cópia da seleção principal, editável só aqui), a configuração dos cenários (janela, método, horizonte e intervenções), o
// pedido a POST /api/simulador, a leitura da resposta, a exportação e a importação dos cenários (JSON) e a exportação dos
// resultados (CSV). Nada é projetado na tela: a base de cada cenário, a intervenção, a faixa e o texto fixo vêm do motor
// (backend/simulador.py). Sem importações em tempo de execução, para os testes Node lerem só este arquivo.
import type { PainelMunicipios } from "./painelApi";

export type SelecaoDasFerramentas = { base?: { municipios: PainelMunicipios }; estados_unidade?: string[];
  conjuntos?: { id: string; rotulo: string; membros: string[]; versao?: number }[] };
/** A seleção local do Simulador: listas explícitas, para acrescentar e tirar territórios sem tocar na seleção principal. O Brasil
 * (a contagem nacional de médicos únicos) só existe aqui: a seleção principal não o tem como unidade. */
export type SelecaoLocal = { municipios: string[]; estados: string[]; conjuntos: { id: string; rotulo: string; membros: string[]; versao?: number }[];
  brasil?: boolean };
export const ID_DO_BRASIL = "br";
export const SELECAO_LOCAL_VAZIA: SelecaoLocal = { municipios: [], estados: [], conjuntos: [] };
export const MAX_TERRITORIOS = 100;
export const MAX_CENARIOS = 5;

export type MetodoDoCenario = "padrao" | "M0" | "M0d" | "M0g" | "M1" | "M2" | "M3" | "manual";
/** Os nomes da base (seção A.2.6), como o motor os manda em `fonte.rotulos`: na base do Brasil, "médicos", "município", "estado". */
export type NomesDaBase = { profissional: string; profissionais: string; unidade: string; unidades: string; grupo: string; grupos: string; todo: string };
export const NOMES_DO_BRASIL: NomesDaBase = { profissional: "médico", profissionais: "médicos", unidade: "município", unidades: "municípios",
  grupo: "estado", grupos: "estados", todo: "Brasil" };
/** As formas com artigo e preposição dos nomes da base, para a concordância dos textos ("os municípios", "do Brasil"; "as comunas",
 * "da Solária"): as que o motor manda (`fonte.formas`). */
export type FormasDaBase = { oUnidade: string; osUnidades: string; oGrupo: string; osGrupos: string; dosGrupos: string; doTodo: string; noTodo: string;
  oTodo: string };
export const FORMAS_DO_BRASIL: FormasDaBase = { oUnidade: "o município", osUnidades: "os municípios", oGrupo: "o estado", osGrupos: "os estados",
  dosGrupos: "dos estados", doTodo: "do Brasil", noTodo: "no Brasil", oTodo: "o Brasil" };
/** Um texto com a primeira letra maiúscula ("médicos" → "Médicos"), para o começo de um rótulo. */
export const comMaiuscula = (t: string): string => t.charAt(0).toUpperCase() + t.slice(1);
export const METODOS_DA_TELA: { chave: MetodoDoCenario; rotulo: string; apoio: string }[] = [
  { chave: "padrao", rotulo: "Continuar como vinha (a forma escolhida pela base)", apoio: "a forma de projetar que a própria base escolheu, pela retroprojeção: o Agente refaz no passado a projeção que teria feito e confere com o que aconteceu depois" },
  { chave: "M0", rotulo: "Persistência (M0)", apoio: "o último valor se mantém" },
  { chave: "M0d", rotulo: "Último valor com o crescimento do grupo de cima (M0d)", apoio: "o último valor com o crescimento recente do grupo de cima do território, nos 3 anos anteriores" },
  { chave: "M0g", rotulo: "Último valor com o crescimento da base toda (M0g)", apoio: "o último valor com o crescimento recente da soma de todos os territórios, nos 3 anos anteriores" },
  { chave: "M1", rotulo: "Taxa composta da janela (M1)", apoio: "o percentual médio que reproduz o crescimento ocorrido na janela" },
  { chave: "M2", rotulo: "Tendência linear robusta (M2)", apoio: "a variação típica por ano, pela mediana das variações entre os registros da janela" },
  { chave: "M3", rotulo: "Tendência log-linear (M3)", apoio: "a variação proporcional ajustada a todos os registros da janela" },
  { chave: "manual", rotulo: "Taxa informada por você", apoio: "uma taxa anual sua, como hipótese; o sistema não sugere taxas" },
];
export type IntervencaoDaTela = { tipo: "acrescimo" | "retirada"; quantidade: string; em: string; periodica: boolean; ate: string; aCadaMeses: string;
  permanencia: string };
/** O planejamento inverso de um cenário (etapa 5): a meta hipotética e o calendário dos acréscimos. */
export type PlanoDaTela = { meta: "valor" | "patamar" | "referencia"; valor: string; referencia: string; em: string; periodica: boolean; ate: string;
  aCadaMeses: string; permanencia: string };
export type CenarioDaTela = { id: string; nome: string; metodo: MetodoDoCenario; taxaManual: string; janela: { inicio: string; fim: string } | null;
  intervencoes: IntervencaoDaTela[]; planejamento?: PlanoDaTela };
/** Uma referência de comparação (etapa 5): um território (o Brasil, um estado, um município ou um conjunto da seleção local), fixa
 * ou dinâmica, ou um valor informado pela pessoa. Pode ficar fora da seleção do Simulador. */
export type ReferenciaDaTela = { id: string; alvo: string; rotulo: string; tipo: "fixa" | "dinamica" | "valor"; valor: string };
export const MAX_REFERENCIAS = 5;
export type ConfigDoSimulador = { local: SelecaoLocal; janela: { inicio: string; fim: string } | null; horizonte: string; modo: "simples" | "avancado";
  cenarios: CenarioDaTela[];
  referencias?: ReferenciaDaTela[];
  /** A métrica da comparação com as referências: a quantidade de médicos (padrão) ou a taxa por 1.000 habitantes, com uma hipótese
   * de população (ver `populacao`). */
  metrica?: "quantidade" | "taxa";
  /** Na comparação por quantidade, o que a frase destaca: a diferença (padrão) ou a razão (Proposta V3, seção C.5). */
  forma?: "razao";
  /** Na comparação por taxa, a hipótese de população: igual à do último registro (padrão) ou crescendo x% ao ano depois dele, uma
   * hipótese da pessoa (`populacaoPct`, como foi digitado; pode ser negativo). */
  populacao?: "crescendo";
  populacaoPct?: string;
  /** De onde veio a configuração, quando o Simulador foi aberto pelo Detector de Sinais: o território, a data e os sinais dele. */
  doDetector?: { rotulo: string; fim: string; sinais: string[]; recuperacao: boolean; exploratorio?: boolean };
  /** A seleção local ainda é a cópia da seleção principal, sem alteração feita no Simulador: enquanto for assim, ela acompanha a
   * seleção principal. Depois da primeira alteração aqui (ou de um cenário importado), só muda por comando explícito. */
  acompanha?: boolean;
  /** Modo simples (Proposta V3, seção C.2): o território em análise, entre os da seleção local (sem ele, o primeiro). */
  territorio?: string;
  /** A faixa mostrada: onde o valor real ficou em 5, 8 (padrão) ou 9 de cada 10 retroprojeções de territórios do mesmo porte. */
  faixa?: 5 | 8 | 9;
  /** A janela com que o Detector de Sinais abriu o Simulador (quando a pessoa a escolheu lá): é a que vale no modo simples, que
   * não leva ao motor a janela geral escolhida no modo avançado. */
  janelaDoDetector?: { inicio: string; fim: string } };
/** O que testar, no modo simples: só continuar como vinha, acrescentar, retirar ou chegar a uma meta (o planejamento inverso). */
export type TesteDoCenario = "continuar" | "acrescentar" | "retirar" | "meta";
export const TESTES: { chave: TesteDoCenario; rotulo: string }[] = [{ chave: "continuar", rotulo: "Só continuar como vinha" },
  { chave: "acrescentar", rotulo: "Acrescentar" }, { chave: "retirar", rotulo: "Retirar" }, { chave: "meta", rotulo: "Chegar a uma meta" }];
/** O teste em uso num cenário do modo simples, pelo que ele tem: a meta, a primeira intervenção ou nada. */
export const testeDoCenario = (cenario: CenarioDaTela): TesteDoCenario => cenario.planejamento ? "meta"
  : !cenario.intervencoes.length ? "continuar" : cenario.intervencoes[0].tipo === "retirada" ? "retirar" : "acrescentar";
/** O cenário com outro teste: a forma de projetar volta à escolhida pela base; a quantidade, a meta e a data digitadas ficam. */
export function comOTeste(cenario: CenarioDaTela, teste: TesteDoCenario, em: string): CenarioDaTela {
  const { planejamento, ...resto } = cenario;
  const base = { ...resto, metodo: "padrao" as MetodoDoCenario, taxaManual: "", janela: null };
  const anterior = cenario.intervencoes[0];
  const data = anterior?.em || planejamento?.em || em;
  if (teste === "continuar") return { ...base, intervencoes: [] };
  if (teste === "meta") return { ...base, intervencoes: [], planejamento: planejamento ?? { ...novoPlano(data), valor: "" } };
  return { ...base, intervencoes: [{ ...(anterior ?? novaIntervencao(data)), tipo: teste === "retirar" ? "retirada" : "acrescimo", em: data, periodica: false,
    ate: data }] };
}
/** Os territórios da seleção local, na ordem do pedido, com o identificador que o motor usa: as unidades, os grupos de cima como
 * unidade ("uf:<prefixo>"), os conjuntos e o todo. */
export function territoriosDaSelecaoLocal(local: SelecaoLocal, nomes: { unidade: (id: string) => string; grupo: (prefixo: string) => string; todo: string }):
  { id: string; rotulo: string }[] {
  return [...local.municipios.map(id => ({ id, rotulo: nomes.unidade(id) })), ...local.estados.map(prefixo => ({ id: "uf:" + prefixo, rotulo: nomes.grupo(prefixo) })),
    ...local.conjuntos.map(conjunto => ({ id: conjunto.id, rotulo: comoConjunto(conjunto.rotulo) })),
    ...(local.brasil ? [{ id: ID_DO_BRASIL, rotulo: nomes.todo }] : [])];
}
/** A seleção local só com um território (o do modo simples); a mesma seleção quando ele não está nela. */
export function soOTerritorio(local: SelecaoLocal, id: string | undefined): SelecaoLocal {
  if (!id) return local;
  if (id === ID_DO_BRASIL && local.brasil) return { municipios: [], estados: [], conjuntos: [], brasil: true };
  if (local.municipios.includes(id)) return { municipios: [id], estados: [], conjuntos: [] };
  if (id.startsWith("uf:") && local.estados.includes(id.slice(3))) return { municipios: [], estados: [id.slice(3)], conjuntos: [] };
  const conjunto = local.conjuntos.find(item => item.id === id);
  return conjunto ? { municipios: [], estados: [], conjuntos: [conjunto] } : local;
}

// ------------------------------------------------------------------------------------------------ datas
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const competenciaCurta = (c: string | null | undefined): string => !c || !/^\d{6}$/.test(c) ? c ?? ""
  : c.endsWith("00") ? c.slice(0, 4) : MESES[Number(c.slice(4)) - 1] + "/" + c.slice(0, 4);
export const mesDe = (c: string): number => Number(c.slice(0, 4)) * 12 + Number(c.slice(4)) - 1;
export const dataDoMes = (mes: number): string => String(Math.floor(mes / 12)) + String(mes % 12 + 1).padStart(2, "0");
/** A data AAAAMM tantos anos depois de outra (os atalhos de horizonte: só atalhos, nunca limites). */
export const anosDepois = (c: string, anos: number): string => ehAnual(c) ? String(Number(c.slice(0, 4)) + anos) + "00" : dataDoMes(mesDe(c) + 12 * anos);
/** Uma data de uma base com um registro por ano: "AAAA00" (só o ano). */
export const ehAnual = (c: string): boolean => /^\d{4}00$/.test(c);
/** "2028-06" (o campo de mês do navegador) ↔ "202806". */
export const paraCampoDeMes = (c: string): string => /^\d{6}$/.test(c) ? c.slice(0, 4) + "-" + c.slice(4) : "";
export const doCampoDeMes = (valor: string): string => /^\d{4}-\d{2}$/.test(valor) ? valor.slice(0, 4) + valor.slice(5) : "";
/** Há quanto tempo é uma competência, em palavras ("2 anos e 5 meses"), contado até a data de hoje do aparelho: a distância entre
 * o último registro e hoje fica à vista (o que vem depois do registro é simulado, não é a situação atual). */
export function tempoDesde(competencia: string, hoje: Date): string {
  if (ehAnual(competencia)) {
    // Numa base com um registro por ano, a distância é contada em anos inteiros.
    const anos = Math.max(0, hoje.getFullYear() - Number(competencia.slice(0, 4)));
    return anos ? anos + (anos === 1 ? " ano" : " anos") : "menos de 1 ano";
  }
  const meses = Math.max(0, hoje.getFullYear() * 12 + hoje.getMonth() - mesDe(competencia));
  const anos = Math.floor(meses / 12), resto = meses % 12;
  return [...(anos ? [anos + (anos === 1 ? " ano" : " anos")] : []), ...(resto || !anos ? [resto + (resto === 1 ? " mês" : " meses")] : [])].join(" e ");
}
/** A janela padrão: os 3 anos até o último registro, pelo tempo e não pela contagem de registros (na base do Brasil, 7
 * registros; numa base com um registro por ano, 4). Uma base mais curta começa no primeiro registro. */
export function janelaPadrao(competencias: string[]): { inicio: string; fim: string } | null {
  return janelaDeAnos(competencias, 3, true);
}
/** A janela dos últimos `anos` anos até o último registro: começa no primeiro registro a até esse tempo do último. Quando a base
 * não chega a esse tempo, null — ou, com `curta`, a base inteira. */
export function janelaDeAnos(competencias: string[], anos: number, curta = false): { inicio: string; fim: string } | null {
  if (competencias.length < 2) return null;
  const fim = competencias[competencias.length - 1], desde = mesDe(fim) - 12 * anos;
  if (!curta && mesDe(competencias[0]) > desde) return null;
  // Numa base com registros espaçados, nenhum outro registro cai nesse tempo: a janela começa no registro anterior ao último.
  const inicio = competencias.find(c => mesDe(c) >= desde) ?? competencias[0];
  return { inicio: inicio === fim ? competencias[competencias.length - 2] : inicio, fim };
}

// ------------------------------------------------------------------------------------------------ seleção local
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
/** A cópia local da seleção principal: os municípios um a um (os estados inteiros e "todos" viram a lista deles), os estados como
 * unidade e os conjuntos, com a composição e a versão. `unidadesDoGrupo` dá os ids dos municípios de um estado. */
export function copiarSelecao(principal: SelecaoDasFerramentas | null, c: { todasAsUnidades: string[]; unidadesDoGrupo: (grupo: string) => string[] }): SelecaoLocal {
  if (!principal) return { ...SELECAO_LOCAL_VAZIA };
  const m = principal.base?.municipios;
  const municipios = !m ? [] : m.todos ? c.todasAsUnidades : [...new Set([...m.estados.flatMap(c.unidadesDoGrupo), ...m.ids])];
  return { municipios: [...municipios].sort(comparar), estados: [...(principal.estados_unidade ?? [])].sort(comparar),
    conjuntos: (principal.conjuntos ?? []).map(({ id, rotulo, membros, versao }) => ({ id, rotulo, membros: [...membros], ...(versao ? { versao } : {}) })) };
}
export const totalDaSelecaoLocal = (local: SelecaoLocal): number => local.municipios.length + local.estados.length + local.conjuntos.length +
  (local.brasil ? 1 : 0);
/** A seleção local no contrato das ferramentas (o do painel). */
export function selecaoLocalParaOPedido(local: SelecaoLocal): SelecaoDasFerramentas {
  return { ...(local.municipios.length ? { base: { municipios: { todos: false, estados: [], ids: [...local.municipios].sort(comparar) } } } : {}),
    ...(local.estados.length ? { estados_unidade: [...local.estados].sort(comparar) } : {}), ...(local.conjuntos.length ? { conjuntos: local.conjuntos } : {}),
    ...(local.brasil ? { brasil: true } : {}) };
}
/** O Brasil na seleção local: entra e sai só no Simulador (a contagem nacional de médicos únicos; nunca é somado aos demais). */
export const comOBrasil = (local: SelecaoLocal, incluir: boolean): SelecaoLocal => {
  const { brasil: _brasil, ...resto } = local;
  return incluir ? { ...resto, brasil: true } : resto;
};
/** Acrescenta um município (se o estado dele não estiver como unidade nem num conjunto de estados) ou um estado como unidade (os
 * municípios dele saem: o estado inteiro e os municípios dele não entram juntos; um conjunto de municípios com membros no estado
 * impede, como na Seleção de Territórios). Devolve a seleção e, quando nada mudou, o motivo. */
export function acrescentarTerritorio(local: SelecaoLocal, alvo: { tipo: "municipio" | "estado"; id: string; grupo: string },
  /** Numa planilha enviada: o grupo de cima de cada unidade (na base do Brasil, ele vem do código IBGE) e os nomes da base, para
   * os motivos dizerem "a zona desta área", e não "o estado deste município". */
  daPlanilha?: { grupoDe: (id: string) => string; r: NomesDaBase; formas: FormasDaBase }): { local: SelecaoLocal; motivo: string | null } {
  const noGrupo = (id: string): boolean => daPlanilha ? daPlanilha.grupoDe(id) === alvo.id : id.startsWith("code:" + alvo.id);
  // Os nomes com a concordância da base: "o estado deste município", "a zona desta área".
  const f = daPlanilha?.formas ?? FORMAS_DO_BRASIL, r = daPlanilha?.r ?? NOMES_DO_BRASIL;
  const este = (comArtigo: string, nome: string): string => (comArtigo.startsWith("o ") ? "este " : "esta ") + nome;
  if (alvo.tipo === "municipio") {
    if (local.municipios.includes(alvo.id)) return { local, motivo: "Este território já está na seleção do Simulador." };
    if (local.estados.includes(alvo.grupo)) return { local, motivo: comMaiuscula(f.oGrupo) + " d" + este(f.oUnidade, r.unidade) +
      " está na seleção como unidade: tire " + f.oGrupo + " para usar " + f.oUnidade + "." };
    const comOEstado = local.conjuntos.find(conjunto => conjunto.membros.includes("uf:" + alvo.grupo));
    if (comOEstado) return { local, motivo: "O estado deste município está no conjunto " + comOEstado.rotulo + ": tire o conjunto para usar o município." };
    return { local: { ...local, municipios: [...local.municipios, alvo.id].sort(comparar) }, motivo: null };
  }
  if (local.estados.includes(alvo.id)) return { local, motivo: comMaiuscula(este(f.oGrupo, r.grupo)) + " já está na seleção do Simulador." };
  const comMembros = local.conjuntos.find(conjunto => conjunto.membros.some(noGrupo));
  if (comMembros) return { local, motivo: "O conjunto " + comMembros.rotulo + " tem " + r.unidades + " n" + este(f.oGrupo, r.grupo) +
    ": tire o conjunto para usar " + f.oGrupo + " como unidade." };
  return { local: { ...local, estados: [...local.estados, alvo.id].sort(comparar), municipios: local.municipios.filter(id => !noGrupo(id)) }, motivo: null };
}
export function tirarTerritorio(local: SelecaoLocal, id: string): SelecaoLocal {
  return { municipios: local.municipios.filter(item => item !== id), estados: local.estados.filter(item => "uf:" + item !== id),
    conjuntos: local.conjuntos.filter(item => item.id !== id), ...(local.brasil && id !== ID_DO_BRASIL ? { brasil: true } : {}) };
}

// ------------------------------------------------------------------------------------------------ cenários e pedido
export const novaIntervencao = (em: string): IntervencaoDaTela => ({ tipo: "acrescimo", quantidade: "1", em, periodica: false, ate: em, aCadaMeses: "12",
  permanencia: "100" });
export const novoCenario = (id: string, nome: string): CenarioDaTela => ({ id, nome, metodo: "padrao", taxaManual: "", janela: null, intervencoes: [] });
/** A configuração inicial: a seleção local (cópia da principal, que ela acompanha até ser alterada no Simulador), a janela padrão
 * do motor, 2 anos de horizonte e um cenário sem intervenção. */
export function configInicial(local: SelecaoLocal, ultimoRegistro: string): ConfigDoSimulador {
  return { local, janela: null, horizonte: anosDepois(ultimoRegistro, 2), modo: "simples", cenarios: [novoCenario("c1", "Cenário 1")], acompanha: true };
}
const numero = (texto: string): number | null => {
  const valor = Number(texto.trim().replace(/\./g, "").replace(",", "."));
  return texto.trim() && Number.isFinite(valor) ? valor : null;
};
/** O que falta para calcular, em palavras; null quando o pedido pode ser feito. */
export function pendenciaDoPedido(config: ConfigDoSimulador): string | null {
  const total = totalDaSelecaoLocal(config.local);
  if (!total) return "Escolha pelo menos um território para o Simulador.";
  if (config.modo !== "simples" && total > MAX_TERRITORIOS) return "O Simulador compara até " + MAX_TERRITORIOS + " territórios de cada vez; a seleção local tem " + total + ".";
  if (!/^\d{6}$/.test(config.horizonte)) return "Escolha a data final do cenário.";
  // No modo simples, só conta o que vai no pedido: o que testar com uma data (ver `doModoSimples`).
  const simples = config.modo === "simples";
  for (const doConfig of cenariosEmUso(config)) {
    const cenario = simples ? doModoSimples(doConfig) : doConfig;
    if (cenario.metodo === "manual" && numero(cenario.taxaManual) === null) return "Informe a taxa anual do cenário “" + cenario.nome + "”.";
    for (const item of cenario.intervencoes) {
      const quantidade = numero(item.quantidade);
      if (quantidade === null || quantidade <= 0) return "Informe quantos entram ou saem em cada intervenção.";
      if (!/^\d{6}$/.test(item.em) || (item.periodica && !/^\d{6}$/.test(item.ate))) return "Informe a data de cada intervenção.";
      if (item.periodica && item.ate < item.em) return "Numa intervenção periódica, a data final vem depois da inicial.";
    }
    const plano = cenario.planejamento;
    if (plano) {
      const meta = numero(plano.valor);
      if (plano.meta === "valor" && (meta === null || meta <= 0)) return "Informe a meta: um número acima de zero.";
      if (plano.meta === "patamar" && plano.valor.trim() && (meta === null || meta <= 0)) return "Informe a meta: um número acima de zero.";
      if (plano.meta === "referencia" && config.modo === "simples") return "No modo simples, a meta é um número: informe a meta em “O que testar”.";
      if (plano.meta === "referencia" && !(config.referencias ?? []).some(ref => ref.id === plano.referencia))
        return "Escolha a referência que serve de meta no planejamento inverso.";
      if (!/^\d{6}$/.test(plano.em) || (plano.periodica && !/^\d{6}$/.test(plano.ate))) return "Informe a data dos acréscimos do planejamento inverso.";
      if (plano.periodica && plano.ate < plano.em) return "No planejamento inverso, a data final dos acréscimos vem depois da inicial.";
    }
  }
  // As referências são do modo avançado: no modo simples elas não vão no pedido, e uma referência incompleta não impede o cálculo.
  for (const ref of simples ? [] : config.referencias ?? []) {
    const valor = numero(ref.valor);
    if (ref.tipo === "valor" && (valor === null || valor < 0)) return "Informe o valor da referência “" + ref.rotulo + "”.";
  }
  // A hipótese de população só vai no pedido com referências, por taxa, no modo avançado.
  if (!simples && (config.referencias ?? []).length && config.metrica === "taxa" && config.populacao === "crescendo") {
    const crescimento = numero(config.populacaoPct ?? "");
    if (crescimento === null || Math.abs(crescimento) > MAX_CRESCIMENTO_DA_POPULACAO)
      return "Informe o crescimento da população: um número entre −" + MAX_CRESCIMENTO_DA_POPULACAO + " e " + MAX_CRESCIMENTO_DA_POPULACAO + " (% ao ano).";
  }
  return null;
}
/** O limite do crescimento da população (% ao ano, para cima ou para baixo), o mesmo do motor. */
export const MAX_CRESCIMENTO_DA_POPULACAO = 20;
/** "Comparar … por": a diferença, a razão ou a taxa por 1.000 habitantes (Proposta V3, seção C.5). */
export type ModoDaComparacao = "diferenca" | "razao" | "taxa";
export const modoDaComparacao = (config: Pick<ConfigDoSimulador, "metrica" | "forma">): ModoDaComparacao =>
  config.metrica === "taxa" ? "taxa" : config.forma === "razao" ? "razao" : "diferenca";
/** A configuração com outro jeito de comparar: a taxa troca a métrica; a diferença e a razão são formas da comparação por quantidade. */
export const comAComparacao = (modo: ModoDaComparacao): Partial<ConfigDoSimulador> =>
  modo === "taxa" ? { metrica: "taxa", forma: undefined } : { metrica: undefined, forma: modo === "razao" ? "razao" : undefined };
/** O que o pedido leva da comparação: nada no padrão (a diferença, por quantidade); a forma, pela razão; por taxa, a métrica e,
 * com a população crescendo, a taxa de crescimento (zero é a população constante). */
export function comparacaoDoPedido(config: ConfigDoSimulador): Record<string, unknown> | null {
  if (config.metrica === "taxa") {
    const crescimento = config.populacao === "crescendo" ? numero(config.populacaoPct ?? "") : null;
    return { metrica: "taxa", ...(crescimento ? { populacao_pct_ao_ano: crescimento } : {}) };
  }
  return config.forma === "razao" ? { forma: "razao" } : null;
}
/** As premissas do Simulador estão todas no padrão (Proposta V3, seções A.4 e C.5)? A forma de projetar e a janela que a base
 * escolheu, a faixa de 8 em cada 10, a permanência total e a comparação pela diferença. O território, o que testar (as quantidades,
 * as datas e a meta), a data final e as referências não são premissas: são o cenário. */
export function premissasNoPadrao(config: ConfigDoSimulador): boolean {
  const total = (texto: string): boolean => { const valor = numero(texto); return valor === null || valor >= 100; };
  return !config.janela && !config.janelaDoDetector && (config.faixa ?? 8) === 8 && config.metrica !== "taxa" && config.forma !== "razao" &&
    config.cenarios.every(cenario => cenario.metodo === "padrao" && !cenario.janela && cenario.intervencoes.every(item => total(item.permanencia)) &&
      (!cenario.planejamento || total(cenario.planejamento.permanencia)));
}
/** "Voltar ao padrão": todas as premissas de volta ao padrão, de uma vez; o cenário (o que testar, as datas e as referências) fica. */
export function comAsPremissasPadrao(config: ConfigDoSimulador): Partial<ConfigDoSimulador> {
  return { janela: null, janelaDoDetector: undefined, faixa: undefined, metrica: undefined, forma: undefined, populacao: undefined, populacaoPct: undefined,
    cenarios: config.cenarios.map(cenario => ({ ...cenario, metodo: "padrao" as MetodoDoCenario, taxaManual: "", janela: null,
      intervencoes: cenario.intervencoes.map(item => ({ ...item, permanencia: "100" })),
      ...(cenario.planejamento ? { planejamento: { ...cenario.planejamento, permanencia: "100" } } : {}) })) };
}
/** A janela escolhida na tela; a que é igual à janela padrão da base vale como "sem janela escolhida" (o padrão), para a faixa e
 * o "Voltar ao padrão" a reconhecerem. */
export function janelaOuPadrao(janela: { inicio: string; fim: string }, competencias: string[]): { inicio: string; fim: string } | null {
  const padrao = janelaPadrao(competencias);
  return padrao && padrao.inicio === janela.inicio && padrao.fim === janela.fim ? null : janela;
}
/** O tempo entre duas datas da base, em palavras: "3 anos", "1 ano", "2 anos e 5 meses", "7 meses". */
export function tempoEntre(inicio: string, fim: string): string {
  const meses = Math.max(0, mesDe(fim) - mesDe(inicio)), anos = Math.floor(meses / 12), resto = meses % 12;
  return [anos ? anos + (anos === 1 ? " ano" : " anos") : "", resto || !anos ? resto + (resto === 1 ? " mês" : " meses") : ""].filter(Boolean).join(" e ");
}
/** O "(Entenda)" geral do Simulador, no título (Proposta V3, seções A.4 e C.7): três frases simples e um exemplo, com o nome que
 * a base dá à contagem. Os números do exemplo são ilustrativos. */
export function entendaDoSimulador(r: NomesDaBase = NOMES_DO_BRASIL): { texto: string; exemplo: string } {
  return { texto: "Mostra para onde o território iria se continuasse como vinha, e o efeito das mudanças que você quer testar. O “como vinha” e a " +
    "margem de erro vêm da própria base: o Agente refaz no passado a projeção que teria feito e confere com o que aconteceu depois. Todo " +
    "resultado é um cenário hipotético, nunca uma previsão.",
    exemplo: "Com 22 " + r.profissionais + " no último registro, “continuar como vinha” pode levar a 25 dois anos depois; com 5 acrescentados, a 30. " +
      "Os números deste exemplo são ilustrativos." };
}
/** O cenário como o modo simples o mostra e pede: o que testar com uma data — a meta com um acréscimo numa data, ou um acréscimo ou
 * uma retirada numa data, com permanência total. O calendário, a permanência e as outras intervenções escolhidos no modo
 * avançado ficam guardados na configuração e não vão no pedido do modo simples. */
export function doModoSimples(cenario: CenarioDaTela): CenarioDaTela {
  const { planejamento, ...resto } = cenario;
  const umaData = <T extends { em: string; periodica: boolean; ate: string; permanencia: string }>(item: T): T => ({ ...item, periodica: false, ate: item.em,
    permanencia: "100" });
  return planejamento ? { ...resto, janela: null, intervencoes: [], planejamento: umaData(planejamento) }
    : { ...resto, janela: null, intervencoes: cenario.intervencoes.slice(0, 1).map(umaData) };
}
/** O plano inicial: a meta num valor (a informar), com um acréscimo um ano depois do último registro. */
export const novoPlano = (em: string): PlanoDaTela => ({ meta: "valor", valor: "", referencia: "", em, periodica: false, ate: em, aCadaMeses: "12",
  permanencia: "100" });
/** Uma referência nova, com o identificador livre seguinte ("r1", "r2"…); null no limite de referências. */
/** O nome de um conjunto com a palavra "Conjunto" uma vez só: "Conjunto A" continua "Conjunto A"; um nome próprio ("Sul do Pará")
 * ganha a palavra na frente. */
export const comoConjunto = (rotulo: string): string => /^conjunto(\s|$)/i.test(rotulo.trim()) ? rotulo.trim() : "Conjunto " + rotulo.trim();

export function novaReferencia(atuais: ReferenciaDaTela[], parte: Pick<ReferenciaDaTela, "alvo" | "rotulo" | "tipo"> & { valor?: string }): ReferenciaDaTela | null {
  if (atuais.length >= MAX_REFERENCIAS) return null;
  const n = atuais.reduce((maior, ref) => Math.max(maior, Number(/^r(\d+)$/.exec(ref.id)?.[1] ?? 0)), 0) + 1;
  return { id: "r" + n, alvo: parte.alvo, rotulo: parte.rotulo, tipo: parte.tipo, valor: parte.valor ?? "" };
}
/** A configuração com que o Detector abre o Simulador: só o território dele na seleção local (que deixa de acompanhar a principal),
 * a janela em uso quando a pessoa a escolheu e, em "Simular recuperação", o planejamento inverso com a meta hipotética de voltar ao
 * patamar anterior (decisão D-B: a meta é uma hipótese editável, nunca uma recomendação). */
export function configDoDetector(alvo: { local: SelecaoLocal; rotulo: string; sinais: string[]; fim: string; exploratorio?: boolean }, ultimoRegistro: string,
  janela: { inicio: string; fim: string } | null, patamar: number | null): ConfigDoSimulador {
  const inicial = configInicial(alvo.local, ultimoRegistro);
  const cenario = inicial.cenarios[0];
  return { ...inicial, acompanha: false, janela, ...(janela ? { janelaDoDetector: janela } : {}),
    doDetector: { rotulo: alvo.rotulo, fim: alvo.fim, sinais: alvo.sinais, recuperacao: patamar !== null,
    ...(alvo.exploratorio ? { exploratorio: true } : {}) },
    cenarios: [patamar === null ? cenario : { ...cenario, nome: "Recuperação do patamar",
      // O patamar vai com a precisão do Detector (a média de 4 registros: múltiplos de 0,25), para a conta usar o mesmo valor.
      planejamento: { ...novoPlano(anosDepois(ultimoRegistro, 1)), meta: "patamar", valor: String(patamar).replace(".", ",") } }] };
}
/** O nome do que a contagem conta, concordando com o número digitado: "1 profissional", "2 profissionais" (em branco ou sem
 * número, o plural). */
export const nomeNoNumero = (quantidade: string | number, r: NomesDaBase = NOMES_DO_BRASIL): string =>
  (typeof quantidade === "number" ? quantidade : numero(quantidade)) === 1 ? r.profissional : r.profissionais;
/** O que o campo da meta mostra no modo simples. A meta que veio do Detector é o patamar, uma média que pode ter decimal (78,25): o
 * campo mostra a meta em uso, o inteiro arredondado para cima (79), como o motor a calcula. O plano guarda o patamar sem arredondar,
 * para a tela e o motor dizerem de onde a meta veio. */
export function metaNoCampo(plano: PlanoDaTela): string {
  const valor = numero(plano.valor);
  return plano.meta === "patamar" && valor !== null && valor > 0 ? String(Math.ceil(valor - 1e-9)) : plano.valor;
}
/** A frase sobre a meta que veio do Detector, no modo simples: "A meta veio do Detector de Sinais: o patamar anterior, de 78,25
 * médicos (a maior média de dois anos seguidos), arredondado para cima." Sem valor, o motor usa o patamar do território. */
export function textoDaMetaDoPatamar(plano: PlanoDaTela, r: NomesDaBase = NOMES_DO_BRASIL): string {
  const valor = numero(plano.valor);
  if (valor === null || valor <= 0) return "A meta é o patamar anterior do território (a maior média de dois anos seguidos), arredondado para cima: uma hipótese que você pode trocar. ";
  const inteira = Math.ceil(valor - 1e-9);
  return "A meta veio do Detector de Sinais: o patamar anterior, de " + ateDuasCasas.format(valor) + " " + (valor === 1 ? r.profissional : r.profissionais) +
    " (a maior média de dois anos seguidos)" + (inteira - valor > 1e-9 ? ", arredondado para cima" : "") + ". É uma hipótese que você pode trocar. ";
}
/** Ao trocar o território do modo simples, a meta sai: ela era do território de antes (o patamar dele, ou um número pensado para
 * ele). O campo fica em branco, à espera da meta do novo território; o resto do que a tela simples mostra continua. */
export function aoTrocarDeTerritorio(config: ConfigDoSimulador, territorio: string): Partial<ConfigDoSimulador> {
  if (territorio === config.territorio || !config.cenarios[0]?.planejamento) return { territorio };
  return { territorio, cenarios: config.cenarios.map((cenario, indice) => indice === 0 && cenario.planejamento
    ? { ...cenario, planejamento: { ...cenario.planejamento, meta: "valor" as const, valor: "", referencia: "" } } : cenario) };
}
/** A seleção local com que o Detector abre o Simulador: só o território dele (um município, um estado como unidade ou um conjunto,
 * com a composição e a versão que ele tem na seleção principal); null quando o conjunto não está mais na seleção principal. */
export function selecaoDoDetector(alvo: { id: string; tipo: string }, principal: SelecaoDasFerramentas | null): SelecaoLocal | null {
  if (alvo.tipo === "estado") return { municipios: [], estados: [alvo.id.replace(/^uf:/, "")], conjuntos: [] };
  if (alvo.tipo === "conjunto") {
    const conjunto = (principal?.conjuntos ?? []).find(item => item.id === alvo.id);
    return conjunto ? { municipios: [], estados: [], conjuntos: [{ id: conjunto.id, rotulo: conjunto.rotulo, membros: [...conjunto.membros],
      ...(conjunto.versao ? { versao: conjunto.versao } : {}) }] } : null;
  }
  return alvo.tipo === "municipio" ? { municipios: [alvo.id], estados: [], conjuntos: [] } : null;
}
/** As referências que continuam valendo com uma seleção local: a que aponta para um conjunto que saiu dela é retirada (um município,
 * um estado, o Brasil e um valor informado não dependem da seleção local). */
export function referenciasValidas(referencias: ReferenciaDaTela[] | undefined, local: SelecaoLocal): ReferenciaDaTela[] {
  const conjuntos = new Set(local.conjuntos.map(conjunto => conjunto.id));
  return (referencias ?? []).filter(ref => ref.tipo === "valor" || ref.alvo === ID_DO_BRASIL || ref.alvo.startsWith("code:") || ref.alvo.startsWith("name:") ||
    ref.alvo.startsWith("uf:") ||
    conjuntos.has(ref.alvo));
}
export const MAX_INTERVENCOES = 8;
/** O resultado do planejamento inverso como uma intervenção do cenário (por comando da pessoa): o acréscimo calculado entra na lista
 * de intervenções, e o planejamento sai. Recalculado, o cenário alcança a meta. Sem resultado ou no limite de intervenções, nada muda. */
export function comOPlanoComoIntervencao(cenario: CenarioDaTela, plano: PlanejamentoDoCenario | null): CenarioDaTela {
  const i = plano?.intervencao;
  if (!i || plano?.estado !== "calculado" || cenario.intervencoes.length >= MAX_INTERVENCOES) return cenario;
  const { planejamento: _planejamento, ...semOPlano } = cenario;
  return { ...semOPlano, intervencoes: [...cenario.intervencoes, { tipo: "acrescimo", quantidade: String(i.quantidade), em: i.em, periodica: !!i.ate,
    ate: i.ate ?? i.em, aCadaMeses: String(i.aCadaMeses ?? 12), permanencia: String(i.permanencia).replace(".", ",") }] };
}
/** Os cenários que valem: no modo simples, só o primeiro. */
export const cenariosEmUso = (config: ConfigDoSimulador): CenarioDaTela[] => config.modo === "simples" ? config.cenarios.slice(0, 1) : config.cenarios.slice(0, MAX_CENARIOS);
export const ID_DA_REFERENCIA = "m0";
/** O pedido de POST /api/simulador: a seleção local, a janela, a data final e os cenários, mais a persistência (M0) sem intervenção
 * como referência de comparação, sempre à vista. */
export function pedidoDoSimulador(config: ConfigDoSimulador, daBase?: { rotulos?: unknown; premissas?: unknown; categoria?: string }): Record<string, unknown> {
  // No modo simples, o pedido leva só o que a tela simples mostra (ver `doModoSimples`): o que só o modo avançado escolhe — a
  // janela geral, as referências de comparação, o calendário e a permanência — fica guardado, e volta a valer no modo avançado.
  const simples = config.modo === "simples";
  const cenarios = cenariosEmUso(config).map(doConfig => simples ? doModoSimples(doConfig) : doConfig).map(cenario => ({ id: cenario.id, nome: cenario.nome, metodo: cenario.metodo,
    ...(cenario.metodo === "manual" ? { taxa_manual_pct: numero(cenario.taxaManual) } : {}),
    ...(config.modo === "avancado" && cenario.janela ? { janela: cenario.janela } : {}),
    ...(cenario.intervencoes.length ? { intervencoes: cenario.intervencoes.map(item => ({ tipo: item.tipo, quantidade: numero(item.quantidade),
      em: item.em, ...(item.periodica ? { ate: item.ate, a_cada_meses: Math.max(1, Math.round(numero(item.aCadaMeses) ?? 12)) } : {}),
      ...(numero(item.permanencia) !== null && numero(item.permanencia)! < 100 ? { permanencia_pct_ao_ano: numero(item.permanencia) } : {}) })) } : {}),
    ...(cenario.planejamento ? { planejamento: planoDoPedido(cenario.planejamento) } : {}) }));
  const temReferencia = cenarios.some(cenario => cenario.metodo === "M0" && !("intervencoes" in cenario) && !("janela" in cenario) &&
    !("planejamento" in cenario));
  // Da janela, vai só aquela com que o Detector de Sinais abriu o Simulador, quando houve.
  const janela = simples ? config.janelaDoDetector ?? null : config.janela;
  const referencias = simples ? [] : (config.referencias ?? []).map(ref => ref.tipo === "valor"
    ? { id: ref.id, tipo: "valor", valor: numero(ref.valor), rotulo: ref.rotulo } : { id: ref.id, tipo: ref.tipo, territorio: ref.alvo });
  // No modo simples, o pedido leva só o território em análise (o primeiro da seleção local, quando nenhum foi escolhido).
  const local = simples ? soOTerritorio(config.local, config.territorio ?? primeiroDaSelecao(config.local)) : config.local;
  return { ...(daBase ?? {}), ...selecaoLocalParaOPedido(local), ...(janela ? { janela } : {}), horizonte: config.horizonte,
    ...(config.faixa && config.faixa !== 8 ? { faixa: config.faixa } : {}),
    cenarios: temReferencia ? cenarios : [...cenarios, { id: ID_DA_REFERENCIA, nome: "Persistência (referência)", metodo: "M0" }],
    ...(referencias.length ? { referencias, ...(comparacaoDoPedido(config) ? { comparacao: comparacaoDoPedido(config) } : {}) } : {}) };
}
function formasDe(bruto: unknown): FormasDaBase {
  const f = objeto(bruto), b = FORMAS_DO_BRASIL;
  return { oUnidade: texto(f.o_unidade) ?? b.oUnidade, osUnidades: texto(f.os_unidades) ?? b.osUnidades, oGrupo: texto(f.o_grupo) ?? b.oGrupo,
    osGrupos: texto(f.os_grupos) ?? b.osGrupos, dosGrupos: texto(f.dos_grupos) ?? b.dosGrupos, doTodo: texto(f.do_todo) ?? b.doTodo,
    noTodo: texto(f.no_todo) ?? b.noTodo, oTodo: texto(f.o_todo) ?? b.oTodo };
}
/** As formas com artigo de uma planilha enviada antes da primeira resposta do motor, pelos nomes do painel "Colunas" (o gênero da
 * unidade e do grupo e o artigo do todo), como o motor as monta: "a comuna", "os condados", "da Solária"; sem o nome do todo, "a
 * base toda". Sem planilha (a base do Brasil), null. */
export function formasDaPlanilha(daBase: { rotulos?: unknown } | undefined): FormasDaBase | null {
  if (!daBase) return null;
  const item = (valor: unknown): Record<string, unknown> => valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : {};
  const nome = (valor: unknown): string | null => typeof valor === "string" && valor.trim() ? valor.trim() : null;
  const r = item(daBase.rotulos), unidade = item(r.unidade), grupo = item(r.grupo), todo = item(r.todo);
  // Sem os nomes, valem os do motor: "a unidade" (feminino) e "o grupo".
  const feminina = nome(unidade.singular) ? unidade.genero === "f" : true, doGrupo = grupo.genero === "f";
  const singular = nome(unidade.singular) ?? "unidade", plural = nome(unidade.plural) ?? "unidades";
  const grupoSingular = nome(grupo.singular) ?? "grupo", grupoPlural = nome(grupo.plural) ?? "grupos";
  const doTodo = nome(todo.nome), artigo = nome(todo.artigo) ?? "";
  return { oUnidade: (feminina ? "a " : "o ") + singular, osUnidades: (feminina ? "as " : "os ") + plural,
    oGrupo: (doGrupo ? "a " : "o ") + grupoSingular, osGrupos: (doGrupo ? "as " : "os ") + grupoPlural, dosGrupos: (doGrupo ? "das " : "dos ") + grupoPlural,
    doTodo: !doTodo ? "de toda a base" : artigo ? "d" + artigo + " " + doTodo : "de " + doTodo,
    noTodo: !doTodo ? "em toda a base" : artigo ? "n" + artigo + " " + doTodo : "em " + doTodo,
    oTodo: !doTodo ? "a base toda" : (artigo ? artigo + " " : "") + doTodo };
}
const PREPOSICOES = ["de", "da", "do", "das", "dos", "em", "na", "no", "nas", "nos", "para", "com", "por", "sem", "a", "à"];
const DOS_DOIS_GENEROS = ["ista", "iatra", "euta"];
const PLURAIS: [string, string][] = [["ões", "ão"], ["ães", "ão"], ["ãos", "ão"], ["ais", "al"], ["éis", "el"], ["eis", "el"], ["óis", "ol"], ["ns", "m"]];
const palavraNoSingular = (palavra: string): string | null => {
  for (const [plural, singular] of PLURAIS) if (palavra.endsWith(plural) && palavra.length > plural.length + 1) return palavra.slice(0, -plural.length) + singular;
  if (/[aeiou][rz]es$/.test(palavra)) return palavra.slice(0, -2);
  return palavra.endsWith("s") && !palavra.endsWith("ss") ? palavra.slice(0, -1) : null;
};
/** [singular, plural] do nome dos trabalhadores informado no envio ("Enfermeiros" → ["enfermeiro", "enfermeiros"]), a mesma regra
 * do motor (`series_da_planilha.nome_dos_trabalhadores`): só as palavras antes da primeira preposição vão para o singular; null
 * quando o nome não é um plural que os textos possam usar com segurança (mais de um nome, sigla, nome feminino ou palavra que não
 * está no plural). */
export function nomeDosTrabalhadores(declarado: unknown): [string, string] | null {
  const nome = (typeof declarado === "string" ? declarado : "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
  if (!nome || nome.length > 60 || /[^a-zà-öø-ÿ \-]/.test(nome) || /(^| )(e|ou)( |$)/.test(nome)) return null;
  const palavras = nome.split(" "), singulares: string[] = [];
  for (let posicao = 0; posicao < palavras.length; posicao++) {
    const palavra = palavras[posicao];
    if (PREPOSICOES.includes(palavra)) { singulares.push(...palavras.slice(posicao)); break; }
    const partes = palavra.split("-").map(palavraNoSingular);
    if (partes.some(parte => parte === null) || (posicao === 0 && palavra.length < 5)) {
      if (posicao === 0) return null;
      singulares.push(palavra);
      continue;
    }
    singulares.push(partes.join("-"));
  }
  const primeira = singulares[0].split("-")[0];
  if (primeira.endsWith("a") && !DOS_DOIS_GENEROS.some(fim => primeira.endsWith(fim))) return null;
  return [singulares.join(" "), nome];
}
/** Os nomes de uma planilha enviada antes da primeira resposta do motor, pelo que o pedido diz dela (os nomes do painel "Colunas" e
 * a unidade de contagem), como o motor os monta: o nome dos trabalhadores informado no envio, "profissionais", "vínculos" ou
 * "postos"; a unidade, o grupo de cima e o todo. Sem planilha (a base do Brasil), null. */
export function nomesDaPlanilha(daBase: { rotulos?: unknown; premissas?: unknown } | undefined): NomesDaBase | null {
  if (!daBase) return null;
  const item = (valor: unknown): Record<string, unknown> => valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : {};
  const nome = (valor: unknown): string | null => typeof valor === "string" && valor.trim() ? valor.trim() : null;
  const r = item(daBase.rotulos), unidade = item(r.unidade), grupo = item(r.grupo), todo = item(r.todo);
  const premissas = item(daBase.premissas), contagem = nome(premissas.count_unit);
  // O que a contagem conta: vínculos ou postos, quando a unidade de contagem diz isso; senão, o nome dos trabalhadores informado no
  // envio, quando ele serve aos textos; senão, "profissionais" (como o motor).
  const [profissional, profissionais] = contagem === "vinculos" ? ["vínculo", "vínculos"] : contagem === "postos" ? ["posto", "postos"]
    : nomeDosTrabalhadores(premissas.object_declaration || premissas.category_constant) ?? ["profissional", "profissionais"];
  return { profissional, profissionais, unidade: nome(unidade.singular) ?? "unidade", unidades: nome(unidade.plural) ?? "unidades",
    grupo: nome(grupo.singular) ?? "grupo", grupos: nome(grupo.plural) ?? "grupos", todo: nome(todo.nome) ?? "a base toda" };
}
/** As competências de uma base no formato das ferramentas, em ordem: "AAAAMM" (de "AAAAMM", "AAAA-MM" ou "AAAA-MM-DD") ou
 * "AAAA00" (uma planilha só com anos). O que não é data fica de fora. */
export function competenciasDasFerramentas(periodos: string[]): string[] {
  const saida = new Set<string>();
  for (const bruto of periodos) {
    const p = String(bruto).trim();
    const mes = /^(\d{4})(\d{2})$/.exec(p) ?? /^(\d{4})-(\d{2})(?:-\d{2})?$/.exec(p);
    if (mes && Number(mes[2]) >= 1 && Number(mes[2]) <= 12) saida.add(mes[1] + mes[2]);
    else if (/^(1[89]|2[01])\d\d(\.0+)?$/.test(p)) saida.add(p.slice(0, 4) + "00");
  }
  return [...saida].sort();
}
/** O identificador do primeiro território da seleção local, na ordem do pedido. */
export const primeiroDaSelecao = (local: SelecaoLocal): string | undefined => local.municipios[0] ?? (local.estados[0] !== undefined ? "uf:" + local.estados[0]
  : local.conjuntos[0]?.id ?? (local.brasil ? ID_DO_BRASIL : undefined));
/** O planejamento inverso no contrato do motor: a meta e o calendário dos acréscimos. */
function planoDoPedido(plano: PlanoDaTela): Record<string, unknown> {
  const valor = numero(plano.valor);
  return { meta: plano.meta === "referencia" ? { tipo: "referencia", referencia: plano.referencia }
    : plano.meta === "patamar" ? { tipo: "patamar", ...(valor !== null ? { valor } : {}) } : { tipo: "valor", valor },
    em: plano.em, ...(plano.periodica ? { ate: plano.ate, a_cada_meses: Math.max(1, Math.round(numero(plano.aCadaMeses) ?? 12)) } : {}),
    ...(numero(plano.permanencia) !== null && numero(plano.permanencia)! < 100 ? { permanencia_pct_ao_ano: numero(plano.permanencia) } : {}) };
}

// ------------------------------------------------------------------------------------------------ resposta
export type PontoDoCenario = { data: string; anos: number; base: number; intervencao: number; total: number; retroprojecao: boolean;
  observado: number | null;
  /** A faixa do ponto: os limites, o prazo e se foi conferida com o que veio depois ("conferida") ou não ("provisoria"). */
  faixa: { inferior: number; superior: number; anos: number; validada: boolean; estado: string; como: string | null } | null };
export type TextoDoEntenda = { texto: string; exemplo: string };
export type CenarioCalculado = { id: string; nome: string; estado: string; motivo: string | null;
  metodo: { pedido: string; usado: string | null; rotulo: string | null; padrao: boolean; provisorio: boolean; voltouAoM0: boolean; soma: string | null;
    /** A forma de projetar que a própria base escolheu para o nível do território, e se é a que está em uso. */
    escolhidoPelaBase: string | null; eOEscolhido: boolean };
  parametros: Record<string, unknown>; avisos: { codigo: string; texto: string }[]; trajetoria: PontoDoCenario[];
  /** A faixa do cenário: N em cada 10, até quantos anos vai e, quando falta, o motivo. */
  faixa: { estado: string; motivo: string | null; rotulo: string | null; em10: number; ateAnos: number | null; conferencia: string | null; como: string | null };
  /** Os "Entenda" do resultado (do motor): a forma de projetar (no campo `jeito`) e a faixa, em duas ou três frases e um exemplo. */
  entenda: { jeito: TextoDoEntenda; faixa: TextoDoEntenda } | null;
  final: { data: string; base: number; intervencao: number; total: number; faixa: PontoDoCenario["faixa"] } | null; texto: string | null;
  horizonte: { anos: number; aviso: string } | null;
  /** Etapa 5: o cenário diante de cada referência, o planejamento inverso e a hipótese derivada da simulação. */
  comparacoes: ComparacaoDoCenario[]; planejamento: PlanejamentoDoCenario | null; hipotetico: HipoteseDerivada | null };
export type PontoDaComparacao = { data: string; territorio: number; referencia: number; diferenca: number; razao: number | null; indice: number | null };
export type ComparacaoDoCenario = { id: string; rotulo: string; tipo: string; metrica: string;
  /** O que a frase destaca: a diferença ou a razão (a resposta de antes de 15/11/2026 não traz a forma: é a diferença). */
  forma: string; estado: string; motivo: string | null; avisos: string[];
  descricao: string | null; pontos: PontoDaComparacao[]; final: PontoDaComparacao | null;
  alcance: { estado: string; data: string | null } | null; texto: string | null };
/** A meta do planejamento: o valor em uso (um inteiro, quando ela é o patamar: o patamar arredondado para cima) e, no patamar, de
 * onde ela veio — o patamar sem arredondar e de quantos registros ele é a média. `trajetoria`: o caminho do cenário com o
 * acréscimo calculado (o total e o acréscimo acumulado em cada data), para o gráfico. */
export type PlanejamentoDoCenario = { estado: string; motivo: string | null;
  meta: { tipo: string; valor: number; rotulo: string; patamar: number | null; registros: number | null } | null;
  semOPlano: number | null; eventos: number; datas: string[]; porEvento: number | null; total: number | null; teoricoPorEvento: number | null;
  resultado: number | null; texto: string | null; trajetoria: { data: string; total: number; intervencao: number }[];
  intervencao: { tipo: string; quantidade: number; em: string; ate: string | null; aCadaMeses: number | null; permanencia: number } | null };
export type HipoteseDerivada = { rotulo: string; data: string; valor: number; inteiro: number; classe: string | null; impactoPct: number | null;
  naFaixa: { inferior: string | null; superior: string | null } | null };
export type ReferenciaDaResposta = { id: string; rotulo: string; tipo: string; territorio: string | null; unidade: string | null; estado: string;
  descricao: string | null; motivo: string | null };
export type TerritorioSimulado = { id: string; tipo: string; nivel: string; rotulo: string; unidade: string; membros: string[];
  observado: { competencia: string; valor: number | null; estado: string; marca: string | null }[];
  historico: { registros: number; de: string | null; ate: string | null; anos: number; taxasDeJunho: { de: string; ate: string; taxaPct: number }[];
    mediaAritmeticaPct: number | null; medianaPct: number | null; desvioPct: number | null; taxaCompostaPct: number | null; nota: string };
  lacunas: string[]; cenarios: CenarioCalculado[] };
export type FaixaDaRetroprojecao = { porte: string; anos: number; inferiorPct: number; superiorPct: number; casos: number; origens: number;
  coberturaPct: number | null; rotulo: string };
export type LinhaDaRetroprojecao = { metodo: string; porte: string; anos: number; casos: number; origens: number; erroAbsolutoMedio: number; vies: number;
  frenteAoM0: number | null };
/** A forma de projetar que a base escolheu para um nível de território, com a frase que o motor escreveu (regra C.3). */
export type EscolhaDaBase = { metodo: string; rotulo: string; motivo: string; texto: string;
  candidatos: { metodo: string; rotulo: string; frenteAoM0: number | null; menosErroEm: number; combinacoes: number; vale: boolean }[] };
export type RespostaDoSimulador = { versao: string; fonte: { base: string; categoria: string; versao: string; primeira: string; ultima: string;
    rotulos: NomesDaBase; origem: "brasil" | "planilha";
    /** As formas com artigo dos nomes da base e o mês da série anual ("06" na base do Brasil; "00" numa base só com anos; null sem série anual). */
    formas: FormasDaBase; ancora: string | null };
  competencias: string[]; ultimoRegistro: string; janela: { inicio: string; fim: string; registros: number; anos: number; padrao: boolean };
  horizonte: { data: string; anosDesdeOUltimoRegistro: number }; territorios: TerritorioSimulado[];
  retroprojecao: { origens: string[]; faixas: FaixaDaRetroprojecao[]; tabela: LinhaDaRetroprojecao[]; em10: number;
    /** A escolha por nível: "municipios" (as unidades da base) e, quando há, "estados" (os grupos de cima como unidade). */
    escolhas: Record<string, EscolhaDaBase>;
    /** A retroprojeção tal como o motor a mandou (os campos e os números dele), para "Exportar a avaliação dos métodos" (AJ-03). */
    bruta: Record<string, unknown> };
  notas: string[]; limitacoes: string[];
  referencias: ReferenciaDaResposta[];
  /** A comparação deste cálculo: a métrica, a forma (diferença ou razão) e, por taxa, a hipótese de população — o texto dela e,
   * quando a população cresce, a taxa por ano (null na população constante). */
  comparacao: { metrica: string; forma: string; populacaoPctAoAno: number | null; hipoteseDePopulacao: string | null } };

const objeto = (valor: unknown): Record<string, unknown> => valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : {};
const lista = (valor: unknown): unknown[] => Array.isArray(valor) ? valor : [];
const texto = (valor: unknown): string | null => typeof valor === "string" && valor ? valor : null;
const num = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;
const textos = (valor: unknown): string[] => lista(valor).filter((item): item is string => typeof item === "string");
function faixaDe(bruto: unknown): PontoDoCenario["faixa"] {
  const f = objeto(bruto);
  return num(f.inferior) !== null && num(f.superior) !== null ? { inferior: num(f.inferior)!, superior: num(f.superior)!, anos: num(f.anos) ?? 0,
    validada: f.validada === true, estado: texto(f.estado) ?? (f.validada === true ? "conferida" : "provisoria"), como: texto(f.como) } : null;
}
function pontoDaComparacao(bruto: unknown): PontoDaComparacao | null {
  const p = objeto(bruto);
  return texto(p.data) && num(p.territorio) !== null && num(p.referencia) !== null ? { data: texto(p.data)!, territorio: num(p.territorio)!,
    referencia: num(p.referencia)!, diferenca: num(p.diferenca) ?? 0, razao: num(p.razao), indice: num(p.indice) } : null;
}
function comparacaoDe(bruto: unknown): ComparacaoDoCenario {
  const c = objeto(bruto), a = objeto(c.alcance);
  return { id: texto(c.id) ?? "", rotulo: texto(c.rotulo) ?? "", tipo: texto(c.tipo) ?? "", metrica: texto(c.metrica) ?? "quantidade",
    forma: texto(c.forma) ?? "diferenca", estado: texto(c.estado) ?? "", motivo: texto(c.motivo), avisos: textos(c.avisos), descricao: texto(c.descricao),
    pontos: lista(c.pontos).map(pontoDaComparacao).filter((ponto): ponto is PontoDaComparacao => !!ponto), final: pontoDaComparacao(c.final),
    alcance: texto(a.estado) ? { estado: texto(a.estado)!, data: texto(a.data) } : null, texto: texto(c.texto) };
}
function planejamentoDe(bruto: unknown): PlanejamentoDoCenario | null {
  if (!bruto || typeof bruto !== "object") return null;
  const p = objeto(bruto), meta = objeto(p.meta), i = objeto(p.intervencao);
  return { estado: texto(p.estado) ?? "", motivo: texto(p.motivo),
    meta: num(meta.valor) !== null ? { tipo: texto(meta.tipo) ?? "", valor: num(meta.valor)!, rotulo: texto(meta.rotulo) ?? "",
      patamar: num(meta.patamar), registros: num(meta.registros) } : null,
    semOPlano: num(p.sem_o_plano), eventos: num(p.eventos) ?? 0, datas: textos(p.datas), porEvento: num(p.por_evento), total: num(p.total),
    teoricoPorEvento: num(p.teorico_por_evento), resultado: num(p.resultado), texto: texto(p.texto),
    trajetoria: lista(p.trajetoria).map(item => { const t = objeto(item); return { data: texto(t.data) ?? "", total: num(t.total), intervencao: num(t.intervencao) ?? 0 }; })
      .filter((ponto): ponto is { data: string; total: number; intervencao: number } => !!ponto.data && ponto.total !== null),
    intervencao: num(i.quantidade) !== null && texto(i.em) ? { tipo: texto(i.tipo) ?? "acrescimo", quantidade: num(i.quantidade)!, em: texto(i.em)!,
      ate: texto(i.ate), aCadaMeses: num(i.a_cada_meses), permanencia: num(i.permanencia_pct_ao_ano) ?? 100 } : null };
}
function hipoteticoDe(bruto: unknown): HipoteseDerivada | null {
  if (!bruto || typeof bruto !== "object") return null;
  const h = objeto(bruto), f = h.na_faixa ? objeto(h.na_faixa) : null;
  return num(h.valor) === null ? null : { rotulo: texto(h.rotulo) ?? "", data: texto(h.data) ?? "", valor: num(h.valor)!, inteiro: num(h.inteiro) ?? 0,
    classe: texto(h.classe), impactoPct: num(h.impacto_pct), naFaixa: f ? { inferior: texto(f.inferior), superior: texto(f.superior) } : null };
}
const entendaDe = (bruto: unknown): TextoDoEntenda => { const e = objeto(bruto); return { texto: texto(e.texto) ?? "", exemplo: texto(e.exemplo) ?? "" }; };
function nomesDe(bruto: unknown): NomesDaBase {
  const r = objeto(bruto);
  return Object.fromEntries(Object.entries(NOMES_DO_BRASIL).map(([chave, padrao]) => [chave, texto(r[chave]) ?? padrao])) as NomesDaBase;
}
function escolhaDe(bruto: unknown): EscolhaDaBase {
  const e = objeto(bruto);
  return { metodo: texto(e.metodo) ?? "M0", rotulo: texto(e.rotulo) ?? "", motivo: texto(e.motivo) ?? "", texto: texto(e.texto) ?? "",
    candidatos: lista(e.candidatos).map(item => { const c = objeto(item); return { metodo: texto(c.metodo) ?? "", rotulo: texto(c.rotulo) ?? "",
      frenteAoM0: num(c.frente_ao_m0), menosErroEm: num(c.menos_erro_em) ?? 0, combinacoes: num(c.combinacoes) ?? 0, vale: c.vale === true }; }) };
}
function cenarioDe(bruto: unknown): CenarioCalculado {
  const o = objeto(bruto), m = objeto(o.metodo), f = objeto(o.faixa), fim = objeto(o.final), h = objeto(o.horizonte);
  return { id: texto(o.id) ?? "", nome: texto(o.nome) ?? "", estado: texto(o.estado) ?? "", motivo: texto(o.motivo),
    metodo: { pedido: texto(m.pedido) ?? "", usado: texto(m.usado), rotulo: texto(m.rotulo), padrao: m.padrao === true, provisorio: m.provisorio === true,
      voltouAoM0: m.voltou_ao_m0 === true, soma: texto(m.soma), escolhidoPelaBase: texto(m.escolhido_pela_base), eOEscolhido: m.e_o_escolhido === true },
    parametros: objeto(o.parametros),
    avisos: lista(o.avisos).map(item => ({ codigo: texto(objeto(item).codigo) ?? "", texto: texto(objeto(item).texto) ?? "" })).filter(item => item.texto),
    trajetoria: lista(o.trajetoria).map(item => {
      const p = objeto(item);
      return { data: texto(p.data) ?? "", anos: num(p.anos) ?? 0, base: num(p.base) ?? 0, intervencao: num(p.intervencao) ?? 0, total: num(p.total) ?? 0,
        retroprojecao: p.retroprojecao === true, observado: num(p.observado), faixa: faixaDe(p.faixa) };
    }),
    faixa: { estado: texto(f.estado) ?? "indisponivel", motivo: texto(f.motivo), rotulo: texto(f.rotulo), em10: num(f.em_10) ?? 8, ateAnos: num(f.ate_anos),
      conferencia: texto(f.conferencia), como: texto(f.como) },
    entenda: o.entenda ? { jeito: entendaDe(objeto(o.entenda).jeito), faixa: entendaDe(objeto(o.entenda).faixa) } : null,
    final: texto(fim.data) ? { data: texto(fim.data)!, base: num(fim.base) ?? 0, intervencao: num(fim.intervencao) ?? 0, total: num(fim.total) ?? 0,
      faixa: faixaDe(fim.faixa) } : null,
    texto: texto(o.texto), horizonte: num(h.anos) !== null ? { anos: num(h.anos)!, aviso: texto(h.aviso) ?? "normal" } : null,
    comparacoes: lista(o.comparacoes).map(comparacaoDe), planejamento: planejamentoDe(o.planejamento), hipotetico: hipoteticoDe(o.hipotetico) };
}
/** A resposta de POST /api/simulador nos tipos da tela. */
export function normalizarSimulador(bruto: unknown): RespostaDoSimulador {
  const o = objeto(bruto), fonte = objeto(o.fonte), janela = objeto(o.janela), horizonte = objeto(o.horizonte), retro = objeto(o.retroprojecao),
    comparacao = objeto(o.comparacao);
  return { versao: texto(o.versao) ?? "",
    fonte: { base: texto(fonte.base) ?? "", categoria: texto(fonte.categoria) ?? "", versao: texto(fonte.versao) ?? "", primeira: texto(fonte.primeira) ?? "",
      ultima: texto(fonte.ultima) ?? "", rotulos: nomesDe(fonte.rotulos), origem: fonte.origem === "planilha" ? "planilha" : "brasil",
      formas: formasDe(fonte.formas), ancora: texto(fonte.ancora) ?? (fonte.origem === "planilha" ? null : "06") },
    competencias: textos(o.competencias), ultimoRegistro: texto(o.ultimo_registro) ?? "",
    janela: { inicio: texto(janela.inicio) ?? "", fim: texto(janela.fim) ?? "", registros: num(janela.registros) ?? 0, anos: num(janela.anos) ?? 0,
      padrao: janela.padrao === true },
    horizonte: { data: texto(horizonte.data) ?? "", anosDesdeOUltimoRegistro: num(horizonte.anos_desde_o_ultimo_registro) ?? 0 },
    territorios: lista(o.territorios).map(item => {
      const t = objeto(item), h = objeto(t.historico);
      return { id: texto(t.id) ?? "", tipo: texto(t.tipo) ?? "municipio", nivel: texto(t.nivel) ?? "municipios", rotulo: texto(t.rotulo) ?? "",
        unidade: texto(t.unidade) ?? "", membros: textos(t.nomes_dos_membros),
        observado: lista(t.observado).map(ponto => {
          const p = objeto(ponto);
          return { competencia: texto(p.competencia) ?? "", valor: num(p.valor), estado: texto(p.estado) ?? "", marca: texto(p.marca) };
        }),
        historico: { registros: num(h.registros) ?? 0, de: texto(h.de), ate: texto(h.ate), anos: num(h.anos) ?? 0,
          taxasDeJunho: lista(h.taxas_de_junho).map(taxa => ({ de: texto(objeto(taxa).de) ?? "", ate: texto(objeto(taxa).ate) ?? "",
            taxaPct: num(objeto(taxa).taxa_pct) ?? 0 })),
          mediaAritmeticaPct: num(h.media_aritmetica_pct), medianaPct: num(h.mediana_pct), desvioPct: num(h.desvio_pct),
          taxaCompostaPct: num(h.taxa_composta_pct), nota: texto(h.nota) ?? "" },
        lacunas: textos(t.lacunas), cenarios: lista(t.cenarios).map(cenarioDe) };
    }).filter(item => item.id),
    retroprojecao: { origens: textos(retro.origens), em10: num(retro.em_10) ?? 8, bruta: retro,
      escolhas: Object.fromEntries(Object.entries(objeto(retro.niveis)).map(([nivel, dados]) => [nivel, escolhaDe(objeto(dados).escolha)])),
      // Só as faixas com limites: a que a base não sustenta fica de fora, e a tabela diz "indisponível".
      faixas: lista(retro.faixas).map(objeto).filter(f => num(f.inferior_pct) !== null && num(f.superior_pct) !== null).map(f => (
        { porte: texto(f.porte) ?? "", anos: num(f.anos) ?? 0, inferiorPct: num(f.inferior_pct) ?? 0, superiorPct: num(f.superior_pct) ?? 0,
          casos: num(f.casos) ?? 0, origens: num(f.origens) ?? 0, coberturaPct: num(f.cobertura_pct), rotulo: texto(f.rotulo) ?? "" })),
      tabela: lista(retro.tabela).map(item => {
        const l = objeto(item);
        return { metodo: texto(l.metodo) ?? "", porte: texto(l.porte) ?? "", anos: num(l.anos) ?? 0, casos: num(l.casos) ?? 0, origens: num(l.origens) ?? 0,
          erroAbsolutoMedio: num(l.erro_absoluto_medio) ?? 0, vies: num(l.vies) ?? 0, frenteAoM0: num(l.frente_ao_m0) };
      }) },
    notas: textos(o.notas), limitacoes: textos(o.limitacoes),
    referencias: lista(o.referencias).map(item => {
      const r = objeto(item);
      return { id: texto(r.id) ?? "", rotulo: texto(r.rotulo) ?? "", tipo: texto(r.tipo) ?? "", territorio: texto(r.territorio), unidade: texto(r.unidade),
        estado: texto(r.estado) ?? "", descricao: texto(r.descricao), motivo: texto(r.motivo) };
    }),
    comparacao: { metrica: texto(comparacao.metrica) ?? "quantidade", forma: texto(comparacao.forma) ?? "diferenca",
      populacaoPctAoAno: typeof comparacao.populacao_pct_ao_ano === "number" && Number.isFinite(comparacao.populacao_pct_ao_ano)
        ? comparacao.populacao_pct_ao_ano : null,
      hipoteseDePopulacao: texto(comparacao.hipotese_de_populacao) } };
}

// ------------------------------------------------------------------------------------------------ apresentação
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const umaCasa = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const duasCasas = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const ateDuasCasas = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });   // o patamar: "78,25", "58,5", "20"
/** Um número de médicos de cenário: o inteiro quando é inteiro; senão, uma casa (a precisão integral fica nas exportações). */
export const formatarMedicos = (valor: number): string => Number.isInteger(valor) ? inteiro.format(valor) : umaCasa.format(valor);
export const formatarTaxa = (valor: number): string => (valor > 0 ? "+" : valor < 0 ? "−" : "") + duasCasas.format(Math.abs(valor)) + "%";
/** Um percentual inteiro, arredondado, com o sinal ("−26%", "+48%"): os limites das faixas da retroprojeção. */
export function formatarPercentualInteiro(valor: number): string {
  const n = Math.round(Math.abs(valor));
  return (n === 0 ? "" : valor > 0 ? "+" : "−") + inteiro.format(n) + "%";
}
/** O nome curto de cada método, em palavras, para a tabela (o código fica na dica e nas exportações). */
export const NOME_CURTO_DO_METODO: Record<string, string> = { M0: "último valor mantido", M0d: "último valor com o crescimento do estado",
  M0g: "último valor com o crescimento da base toda", M1: "taxa composta da janela", M2: "tendência linear", M3: "tendência log-linear",
  manual: "taxa informada por você" };
/** O nome curto de um método com os nomes da base ("o crescimento do estado", "da província"). */
export const nomeCurtoDoMetodo = (metodo: string, r: NomesDaBase = NOMES_DO_BRASIL): string => metodo === "M0d"
  ? "último valor com o crescimento d" + (r.grupo === "estado" ? "o estado" : "o grupo de cima (" + r.grupo + ")") : NOME_CURTO_DO_METODO[metodo] ?? metodo;
/** Os três números do modo simples (seção C.2): no último registro, na data final e a diferença — ou, na meta, quantos seria
 * preciso acrescentar. Tudo vem do motor; aqui só se escreve. */
export function tresNumeros(cenario: CenarioCalculado, r: NomesDaBase = NOMES_DO_BRASIL): { rotulo: string; valor: string }[] {
  if (cenario.estado !== "calculado" || !cenario.final) return [];
  const n0 = Number(cenario.parametros.n0), origem = String(cenario.parametros.origem ?? "");
  const saida = [{ rotulo: "No último registro (" + competenciaCurta(origem) + ")", valor: formatarMedicos(n0) },
    { rotulo: "Em " + competenciaCurta(cenario.final.data), valor: formatarMedicos(Math.round(cenario.final.total)) }];
  const plano = cenario.planejamento;
  if (plano && plano.estado === "calculado" && plano.porEvento !== null)
    return [...saida, { rotulo: "Para chegar à meta", valor: "precisaria acrescentar " + formatarMedicos(plano.porEvento * Math.max(1, plano.eventos)) }];
  if (plano && plano.estado === "ja_alcancada") return [...saida, { rotulo: "Para chegar à meta", valor: "nada a acrescentar" }];
  const diferenca = Math.round(cenario.final.total) - Math.round(n0);
  return [...saida, { rotulo: "Diferença", valor: (diferenca > 0 ? "+" : diferenca < 0 ? "−" : "") + formatarMedicos(Math.abs(diferenca)) + " " +
    (Math.abs(diferenca) === 1 ? r.profissional : r.profissionais) }];
}
/** A faixa de 80% da data final, em linguagem simples (decisão D-C): o que ela é, de onde vem e, de 3 a 4 anos, que é um limite
 * provisório. Sem faixa, "indisponível" e o motivo: nada é extrapolado. */
export function textoDaFaixa(cenario: CenarioCalculado, conjunto = false, r: NomesDaBase = NOMES_DO_BRASIL): string {
  const faixa = cenario.final?.faixa, nome = "Faixa de " + cenario.faixa.em10 + " em cada 10";
  if (!cenario.final || !faixa) return nome + ": indisponível" + (cenario.faixa.motivo ? ". " + cenario.faixa.motivo
    : cenario.faixa.estado === "disponivel" ? " nesta data: ela vai só até " + ((cenario.faixa.ateAnos ?? 4) === 1 ? "1 ano" : (cenario.faixa.ateAnos ?? 4) + " anos") +
      " depois do último registro usado." : ".");
  const deQuem = conjunto ? "com o porte desta soma (uma aproximação para o conjunto)" : faixa.como === "vizinhas" ? "do mesmo porte e dos portes vizinhos"
    : faixa.como === "portes_menores" ? "do mesmo porte e de portes menores" : "do mesmo porte";
  return nome + " " + (conjunto ? "(aproximação) " : "") + "em " + competenciaCurta(cenario.final.data) + ": de " + formatarMedicos(faixa.inferior) +
    " a " + formatarMedicos(faixa.superior) + " " + r.profissionais + ". No passado da base, em " + cenario.faixa.em10 + " de cada 10 casos de territórios " + deQuem +
    ", o número observado ficou dentro dessa margem; ela acompanha a intervenção." + (faixa.estado === "conferida" ? " Conferida com o que veio depois."
      : " Faixa provisória: ainda não deu para conferi-la com dados que vieram depois, ou a conferência ficou um pouco abaixo do esperado.") +
    faixaSemALinha(cenario);
}
/** A faixa pode ficar inteira de um lado da linha do cenário (por exemplo, a de 5 em cada 10 de um estado, em 4 anos): não é erro
 * da conta, e a frase diz o que isso quer dizer. Com a linha dentro da faixa, nada. */
export function faixaSemALinha(cenario: CenarioCalculado): string {
  const faixa = cenario.final?.faixa, total = cenario.final?.total;
  if (!faixa || total === undefined || (faixa.inferior <= total + 1e-9 && faixa.superior >= total - 1e-9)) return "";
  const lado = faixa.inferior > total ? "acima" : "abaixo";
  return " A faixa fica inteira " + lado + " da linha do cenário: no passado da base, neste porte e neste prazo, o número observado ficou, na maior parte " +
    "dos casos, " + lado + " do que esta forma de projetar dava.";
}
/** As contas da data final, com uma casa: a base do cenário, a intervenção e o total (o texto do cenário arredonda para o inteiro). */
export function contasDoFinal(cenario: CenarioCalculado, r: NomesDaBase = NOMES_DO_BRASIL): string {
  const f = cenario.final;
  if (!f) return "";
  if (!f.intervencao) return "Na data final: base do cenário de " + formatarMedicos(f.base) + " " + r.profissionais + ", sem intervenção.";
  return "Na data final, neste território: base do cenário de " + formatarMedicos(f.base) + (f.intervencao > 0 ? " + " : " − ") +
    formatarMedicos(Math.abs(f.intervencao)) + " da intervenção = " + formatarMedicos(f.total) + " " + r.profissionais + " (o texto acima arredonda para o inteiro).";
}
/** O método de um cenário na tabela, em palavras. Num conjunto, a soma vem primeiro: a soma das projeções dos membros (a
 * persistência, com ou sem o crescimento do estado de cada um) ou a soma das contagens dos componentes (os demais métodos). */
export function metodoNaTabela(cenario: CenarioCalculado, conjunto = false, r: NomesDaBase = NOMES_DO_BRASIL): string {
  const usado = cenario.metodo.usado ?? "", nome = nomeCurtoDoMetodo(usado, r);
  if (!conjunto) return nome + (cenario.metodo.voltouAoM0 ? " (sem o crescimento d" + (r.grupo === "estado" ? "o estado" : "o grupo de cima") + ")" : "");
  if (cenario.metodo.soma) return cenario.metodo.soma + (usado === "M0d" ? " (cada um com o crescimento do seu " + (r.grupo === "estado" ? "estado" : "grupo de cima") + ")"
    : " (cada um no último valor)");
  return "soma das contagens dos componentes · " + nome;
}
const NOMES_DOS_NIVEIS: Record<string, string> = { moderado: "moderado", elevado: "elevado", critico: "crítico" };
/** O nível de "Poucos médicos" num valor do cenário: "moderado", "elevado", "crítico" ou "sem alerta". */
export const nivelNoCenario = (classe: string | null) => classe ? NOMES_DOS_NIVEIS[classe] ?? classe : "sem alerta";
/** Os níveis no cenário (Proposta V3, seção C.6): só os sinais 1 e 2 do Detector, de limite fixo, valem para um valor simulado,
 * rotulados como hipótese do cenário (o rótulo vem do motor). Quando a faixa cruza um limite, a tela diz "pode ficar entre
 * moderado e elevado", sem escolher um só. Os sinais comparados com a base nunca se aplicam a valores simulados. */
export function textoDaHipotese(h: HipoteseDerivada, r: NomesDaBase = NOMES_DO_BRASIL): string {
  const quantos = formatarMedicos(h.inteiro) + " " + (h.inteiro === 1 ? r.profissional : r.profissionais);
  const rotulo = h.rotulo || "hipótese do cenário";   // o rótulo é o do motor
  const nome = nivelNoCenario(h.classe);
  return rotulo.charAt(0).toUpperCase() + rotulo.slice(1) + " (não é um sinal observado): com " + quantos + " em " + competenciaCurta(h.data) + ", " +
    (h.classe ? "o território seria " + nome.charAt(0).toUpperCase() + nome.slice(1) + " em “Poucos " + r.profissionais + "”"
      : "o território não teria alerta em “Poucos " + r.profissionais + "”") +
    (h.impactoPct !== null && h.inteiro <= 20 ? " (a saída de 1 tiraria " + umaCasa.format(h.impactoPct) + "%)" : "") + "." +
    (h.naFaixa && (h.naFaixa.inferior !== h.classe || h.naFaixa.superior !== h.classe)
      ? " Pela faixa do cenário, pode ficar entre " + nivelNoCenario(h.naFaixa.superior) + " e " + nivelNoCenario(h.naFaixa.inferior) + "." : "") +
    " Os limites são os limites fixos do Detector; os sinais comparados com a base valem só para registros reais.";
}
/** A hipótese entra na tela só quando é pertinente: há nível no valor do cenário ou num dos limites da faixa, ou o território
 * teria até 20 médicos (o sinal trata de poucos médicos; num território grande, o painel seria só ruído). */
export const hipotesePertinente = (h: HipoteseDerivada | null): h is HipoteseDerivada =>
  !!h && (!!h.classe || !!h.naFaixa?.inferior || !!h.naFaixa?.superior || h.inteiro <= 20);
/** O valor final de um cenário, para a tabela: "26,4 (20,3 a 39,0)" com a faixa, ou o motivo quando não há valor. Num conjunto,
 * a faixa é a do porte da soma e leva o rótulo "aproximação". */
export function textoDoFinal(cenario: CenarioCalculado, conjunto = false): string {
  if (cenario.estado !== "calculado" || !cenario.final) return cenario.estado === "retirada_acima_do_estoque" ? "retirada acima do estoque: rever"
    : cenario.estado === "nao_aplicavel" ? "não se aplica" : "não calculável";
  const faixa = cenario.final.faixa;
  return formatarMedicos(cenario.final.total) + (faixa ? " (" + formatarMedicos(faixa.inferior) + " a " + formatarMedicos(faixa.superior) +
    (conjunto ? ", aproximação" : "") + ")" : "");
}

// ------------------------------------------------------------------------------------------------ a avaliação dos métodos (AJ-03)
/** "Exportar a avaliação dos métodos (JSON)" (AJ-03, 18/11/2026): os números que estavam em "Como os métodos se saíram no passado"
 * — a forma de projetar escolhida em cada nível, o erro de cada candidata frente a manter o último valor e as faixas de N em cada 10
 * por porte e prazo, com as origens e os casos — tal como o motor os mandou na resposta (`retroprojecao`), com as versões do
 * método e da base, a janela, as notas e as limitações. É a avaliação dos métodos no histórico da base em uso, e não uma análise
 * do território escolhido; o método está na Ficha B, a ficha metodológica do Simulador. Nada é calculado aqui. */
export function avaliacaoDosMetodos(resposta: RespostaDoSimulador, quando: string): string {
  return JSON.stringify({ ferramenta: "Simulador de Cenários Territoriais",
    conteudo: "avaliação das formas de projetar no passado da base (retroprojeção): a forma escolhida em cada nível, o erro de cada " +
      "candidata frente a manter o último valor e as faixas por porte e prazo; não é uma análise do território escolhido",
    versao_do_metodo: resposta.versao, fonte: resposta.fonte, ultimo_registro: resposta.ultimoRegistro, janela: resposta.janela,
    retroprojecao: resposta.retroprojecao.bruta, notas: resposta.notas, limitacoes: resposta.limitacoes, exportado_em: quando,
    referencia: "Ficha metodológica B — Simulador de Cenários Territoriais (fichas/ficha-simulador.pdf), seção “A avaliação dos métodos no histórico da base”" }, null, 2);
}
/** A janela do cálculo, no modo avançado (antes, na linha das versões, que saiu da tela no AJ-03): "Janela deste cálculo: de
 * jun/2021 a jun/2024 (a janela padrão). Cada cenário parte do último registro usável do território nessa janela." */
export function textoDaJanelaDoCalculo(resposta: Pick<RespostaDoSimulador, "janela">): string {
  const j = resposta.janela;
  return "Janela deste cálculo: de " + competenciaCurta(j.inicio) + " a " + competenciaCurta(j.fim) + (j.padrao ? " (a janela padrão)" : "") +
    ". Cada cenário parte do último registro usável do território nessa janela.";
}

// ------------------------------------------------------------------------------------------------ exportar e importar
export const FORMATO_DO_CENARIO = "ADT-CENARIO/1";
/** A configuração dos cenários num JSON legível: a seleção local (com a composição e a versão dos conjuntos), a janela, a data final
 * e os cenários, com a versão do método e da base em que foram montados. */
export function exportarCenario(config: ConfigDoSimulador, c: { versaoDoMetodo: string; versaoDaBase: string; ultimoRegistro: string; quando: string;
  /** A base em uso, quando não é a do Brasil (uma planilha enviada): o nome e a categoria dela. */
  base?: { nome: string; categoria: string } }): string {
  return JSON.stringify({ formato: FORMATO_DO_CENARIO, ferramenta: "Simulador de Cenários Territoriais", versao_do_metodo: c.versaoDoMetodo,
    base: { nome: c.base?.nome ?? "Brasil", categoria: c.base?.categoria ?? "MEDICINA", versao: c.versaoDaBase, ultimo_registro: c.ultimoRegistro },
    exportado_em: c.quando,
    aviso: "Cenários hipotéticos e condicionais: não são previsão nem recomendação.",
    selecao_local: config.local, janela: config.janela, horizonte: config.horizonte, modo: config.modo, cenarios: config.cenarios,
    // O território em análise do modo simples e a faixa pedida (só quando não é a de 8 em cada 10) vão junto, para a importação repô-los.
    ...(config.territorio ? { territorio: config.territorio } : {}), ...(config.faixa && config.faixa !== 8 ? { faixa: config.faixa } : {}),
    // A janela com que o Detector de Sinais abriu o Simulador (a que vale no modo simples) vai junto; o aviso de origem, não.
    ...(config.janelaDoDetector ? { janela_do_detector: config.janelaDoDetector } : {}),
    ...(config.referencias?.length ? { referencias: config.referencias } : {}), ...(config.metrica === "taxa" ? { metrica: "taxa" } : {}),
    // A forma da comparação e a hipótese de população (Proposta V3, seção C.5), só quando não são o padrão.
    ...(config.forma === "razao" ? { forma: "razao" } : {}),
    ...(config.populacao === "crescendo" ? { populacao: "crescendo", populacao_pct: config.populacaoPct ?? "" } : {}) }, null, 2);
}
const METODOS_VALIDOS = new Set(METODOS_DA_TELA.map(item => item.chave).concat(["M0d"]));
/** Lê um cenário exportado. Devolve a configuração ou o motivo de não poder usá-lo; nada é calculado aqui. */
export function importarCenario(conteudo: string): { config: ConfigDoSimulador | null; erro: string | null; versaoDaBase: string | null } {
  let bruto: unknown;
  try { bruto = JSON.parse(conteudo); } catch { return { config: null, erro: "O arquivo não é um JSON de cenário.", versaoDaBase: null }; }
  const o = objeto(bruto);
  if (o.formato !== FORMATO_DO_CENARIO) return { config: null, erro: "O arquivo não é um cenário do Simulador (formato " + FORMATO_DO_CENARIO + ").", versaoDaBase: null };
  const local = objeto(o.selecao_local), janela = objeto(o.janela);
  const conjuntos = lista(local.conjuntos).map(item => {
    const c = objeto(item);
    return texto(c.id) && textos(c.membros).length >= 2 ? { id: texto(c.id)!, rotulo: texto(c.rotulo) ?? texto(c.id)!, membros: textos(c.membros),
      ...(num(c.versao) ? { versao: num(c.versao)! } : {}) } : null;
  }).filter((item): item is NonNullable<typeof item> => !!item);
  const cenarios = lista(o.cenarios).map((item, indice) => {
    const c = objeto(item), j = objeto(c.janela);
    const metodo = METODOS_VALIDOS.has(c.metodo as MetodoDoCenario) ? c.metodo as MetodoDoCenario : "padrao";
    return { id: texto(c.id) ?? "c" + (indice + 1), nome: texto(c.nome) ?? "Cenário " + (indice + 1), metodo, taxaManual: texto(c.taxaManual) ?? "",
      janela: texto(j.inicio) && texto(j.fim) ? { inicio: texto(j.inicio)!, fim: texto(j.fim)! } : null,
      intervencoes: lista(c.intervencoes).map(bruta => {
        const i = objeto(bruta);
        return { tipo: i.tipo === "retirada" ? "retirada" as const : "acrescimo" as const, quantidade: texto(i.quantidade) ?? "1", em: texto(i.em) ?? "",
          periodica: i.periodica === true, ate: texto(i.ate) ?? texto(i.em) ?? "", aCadaMeses: texto(i.aCadaMeses) ?? "12", permanencia: texto(i.permanencia) ?? "100" };
      }),
      ...(c.planejamento && typeof c.planejamento === "object" ? { planejamento: planoImportado(objeto(c.planejamento)) } : {}) };
  }).slice(0, MAX_CENARIOS);
  const referencias = lista(o.referencias).map((item, indice) => {
    const r = objeto(item);
    const tipo = r.tipo === "dinamica" ? "dinamica" as const : r.tipo === "valor" ? "valor" as const : "fixa" as const;
    return texto(r.alvo) || tipo === "valor" ? { id: texto(r.id) ?? "r" + (indice + 1), alvo: texto(r.alvo) ?? "valor", rotulo: texto(r.rotulo) ?? "Referência",
      tipo, valor: texto(r.valor) ?? "" } : null;
  }).filter((item): item is ReferenciaDaTela => !!item).slice(0, MAX_REFERENCIAS);
  if (!cenarios.length || !texto(o.horizonte)) return { config: null, erro: "O cenário do arquivo está incompleto (faltam os cenários ou a data final).", versaoDaBase: null };
  const importada: SelecaoLocal = { municipios: textos(local.municipios), estados: textos(local.estados), conjuntos, ...(local.brasil === true ? { brasil: true } : {}) };
  const validas = referenciasValidas(referencias, importada);
  return { erro: null, versaoDaBase: texto(objeto(o.base).versao),
    config: { local: importada,
      janela: texto(janela.inicio) && texto(janela.fim) ? { inicio: texto(janela.inicio)!, fim: texto(janela.fim)! } : null,
      horizonte: texto(o.horizonte)!, modo: o.modo === "avancado" ? "avancado" : "simples", cenarios,
      ...(texto(o.territorio) ? { territorio: texto(o.territorio)! } : {}), ...(o.faixa === 5 || o.faixa === 9 ? { faixa: o.faixa } : {}),
      ...(texto(objeto(o.janela_do_detector).inicio) && texto(objeto(o.janela_do_detector).fim)
        ? { janelaDoDetector: { inicio: texto(objeto(o.janela_do_detector).inicio)!, fim: texto(objeto(o.janela_do_detector).fim)! } } : {}),
      ...(validas.length ? { referencias: validas } : {}), ...(o.metrica === "taxa" ? { metrica: "taxa" as const } : {}),
      ...(o.forma === "razao" ? { forma: "razao" as const } : {}),
      ...(o.populacao === "crescendo" ? { populacao: "crescendo" as const, populacaoPct: texto(o.populacao_pct) ?? "" } : {}) } };
}
function planoImportado(p: Record<string, unknown>): PlanoDaTela {
  return { meta: p.meta === "patamar" ? "patamar" : p.meta === "referencia" ? "referencia" : "valor", valor: texto(p.valor) ?? "",
    referencia: texto(p.referencia) ?? "", em: texto(p.em) ?? "", periodica: p.periodica === true, ate: texto(p.ate) ?? texto(p.em) ?? "",
    aCadaMeses: texto(p.aCadaMeses) ?? "12", permanencia: texto(p.permanencia) ?? "100" };
}
/** CSV das comparações com as referências (separador ";" e BOM): uma linha por território, cenário, referência e data, com o valor
 * do território, o da referência, a diferença, a razão e o índice, e o alcance no horizonte simulado. */
export function csvDasComparacoes(resposta: RespostaDoSimulador): string {
  const cabecalho = ["Identificador", "Território", "Cenário", "Referência", "Tipo da referência", "O que é a referência", "Métrica", "Data",
    "Valor do território", "Valor da referência", "Diferença (referência − território)", "Razão (território ÷ referência)",
    "Índice (100 = referência)", "Alcance no horizonte simulado", "Data do alcance", "Avisos", "Hipótese de população", "Versão do método",
    "Versão da base"];
  const alcances: Record<string, string> = { alcanca: "alcança a referência", nao_alcanca: "não alcança no horizonte simulado",
    ja_acima: "já está no nível da referência ou acima na origem" };
  const linhas = [cabecalho.map(celula).join(";")];
  for (const territorio of resposta.territorios) for (const cenario of territorio.cenarios) for (const comparacao of cenario.comparacoes) {
    const fixas = [territorio.id, territorio.rotulo, cenario.nome, comparacao.rotulo, comparacao.tipo, comparacao.descricao ?? comparacao.motivo ?? "",
      comparacao.metrica];
    const fim = [alcances[comparacao.alcance?.estado ?? ""] ?? "", comparacao.alcance?.data ?? "", comparacao.avisos.join(" | "),
      resposta.comparacao.hipoteseDePopulacao ?? "", resposta.versao, resposta.fonte.versao];
    if (!comparacao.pontos.length) { linhas.push([...fixas, "", "", "", "", "", "", ...fim].map(celula).join(";")); continue; }
    for (const ponto of comparacao.pontos) linhas.push([...fixas, ponto.data, ponto.territorio, ponto.referencia, ponto.diferenca, ponto.razao,
      ponto.indice, ...fim].map(celula).join(";"));
  }
  return "\uFEFF" + linhas.join("\r\n") + "\r\n";
}

const celula = (valor: unknown): string => {
  if (valor === null || valor === undefined) return "";
  const t = typeof valor === "number" ? String(valor).replace(".", ",") : String(valor);
  return /[";\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
};
/** CSV dos resultados (separador ";" e BOM): uma linha por território, cenário e data, com o observado, a base, a intervenção, o
 * total e a faixa em precisão integral, e a rastreabilidade em cada linha (método, origem, janela, versões). */
export function csvDoSimulador(resposta: RespostaDoSimulador): string {
  const r = resposta.fonte.rotulos;
  const cabecalho = ["Identificador", "Território", "Tipo", "Unidade de contagem", "Cenário", "Método pedido", "Método usado", "Estado do cenário",
    "Origem do cenário", comMaiuscula(r.profissionais) + " na origem", "Janela: início", "Janela: fim", "Data", "Natureza", "Observado", "Base do cenário", "Intervenção",
    "Total do cenário", "Faixa de " + resposta.retroprojecao.em10 * 10 + "%: inferior", "Faixa de " + resposta.retroprojecao.em10 * 10 + "%: superior", "Avisos",
    "Texto do cenário",
    "Planejamento inverso: meta", "Planejamento inverso: " + r.profissionais + " por evento", "Planejamento inverso: eventos",
    "Hipótese do cenário: nível em poucos " + r.profissionais, "Versão do método", "Versão da base"];
  const linhas = [cabecalho.map(celula).join(";")];
  for (const territorio of resposta.territorios) for (const cenario of territorio.cenarios) {
    const p = cenario.parametros, janela = objeto(p.janela);
    const fixas = [territorio.id, territorio.rotulo, territorio.tipo, territorio.unidade, cenario.nome, cenario.metodo.pedido, cenario.metodo.usado ?? "",
      cenario.estado + (cenario.motivo ? ": " + cenario.motivo : ""), texto(p.origem) ?? "", num(p.n0), texto(janela.inicio) ?? "", texto(janela.fim) ?? ""];
    const plano = cenario.planejamento;
    const fim = [cenario.avisos.map(aviso => aviso.codigo).join(" | "), cenario.texto ?? "", plano?.meta?.rotulo ?? "",
      plano?.estado === "calculado" || plano?.estado === "ja_alcancada" ? plano.porEvento : plano ? plano.estado : null, plano ? plano.eventos : null,
      cenario.hipotetico ? nivelNoCenario(cenario.hipotetico.classe) : "", resposta.versao, resposta.fonte.versao];
    if (!cenario.trajetoria.length) { linhas.push([...fixas, "", "", "", "", "", "", "", "", ...fim].map(celula).join(";")); continue; }
    for (const ponto of cenario.trajetoria) linhas.push([...fixas, ponto.data, ponto.retroprojecao ? "retroprojeção (data com registro)" : "cenário hipotético",
      ponto.observado, ponto.base, ponto.intervencao, ponto.total, ponto.faixa?.inferior ?? null, ponto.faixa?.superior ?? null, ...fim].map(celula).join(";"));
  }
  return "\uFEFF" + linhas.join("\r\n") + "\r\n";
}
