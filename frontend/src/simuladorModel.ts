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

export type MetodoDoCenario = "padrao" | "M0" | "M0d" | "M1" | "M2" | "M3" | "manual";
export const METODOS_DA_TELA: { chave: MetodoDoCenario; rotulo: string; apoio: string }[] = [
  { chave: "padrao", rotulo: "Padrão provisório", apoio: "municípios: o último valor com o crescimento recente do estado (M0d); estados: a taxa composta de 3 anos (M1)" },
  { chave: "M0", rotulo: "Persistência (M0)", apoio: "o último valor se mantém" },
  { chave: "M1", rotulo: "Taxa composta da janela (M1)", apoio: "o percentual médio que reproduz o crescimento ocorrido na janela" },
  { chave: "M2", rotulo: "Tendência linear robusta (M2)", apoio: "a variação típica em médicos por ano, pela mediana das variações entre os registros da janela" },
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
  /** A métrica da comparação com as referências: a quantidade de médicos (padrão) ou a taxa por 1.000 habitantes, com a hipótese de
   * população constante (a do último registro). */
  metrica?: "quantidade" | "taxa";
  /** De onde veio a configuração, quando o Simulador foi aberto pelo Detector de Sinais: o território, a data e os sinais dele. */
  doDetector?: { rotulo: string; fim: string; sinais: string[]; recuperacao: boolean; exploratorio?: boolean };
  /** A seleção local ainda é a cópia da seleção principal, sem alteração feita no Simulador: enquanto for assim, ela acompanha a
   * seleção principal. Depois da primeira alteração aqui (ou de um cenário importado), só muda por comando explícito. */
  acompanha?: boolean };

// ------------------------------------------------------------------------------------------------ datas
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
export const competenciaCurta = (c: string | null | undefined): string => c && /^\d{6}$/.test(c) ? MESES[Number(c.slice(4)) - 1] + "/" + c.slice(0, 4) : c ?? "";
export const mesDe = (c: string): number => Number(c.slice(0, 4)) * 12 + Number(c.slice(4)) - 1;
export const dataDoMes = (mes: number): string => String(Math.floor(mes / 12)) + String(mes % 12 + 1).padStart(2, "0");
/** A data AAAAMM tantos anos depois de outra (os atalhos de horizonte: só atalhos, nunca limites). */
export const anosDepois = (c: string, anos: number): string => dataDoMes(mesDe(c) + 12 * anos);
/** "2028-06" (o campo de mês do navegador) ↔ "202806". */
export const paraCampoDeMes = (c: string): string => /^\d{6}$/.test(c) ? c.slice(0, 4) + "-" + c.slice(4) : "";
export const doCampoDeMes = (valor: string): string => /^\d{4}-\d{2}$/.test(valor) ? valor.slice(0, 4) + valor.slice(5) : "";
/** Há quanto tempo é uma competência, em palavras ("2 anos e 5 meses"), contado até a data de hoje do aparelho: a distância entre
 * o último registro e hoje fica à vista (o que vem depois do registro é simulado, não é a situação atual). */
export function tempoDesde(competencia: string, hoje: Date): string {
  const meses = Math.max(0, hoje.getFullYear() * 12 + hoje.getMonth() - mesDe(competencia));
  const anos = Math.floor(meses / 12), resto = meses % 12;
  return [...(anos ? [anos + (anos === 1 ? " ano" : " anos")] : []), ...(resto || !anos ? [resto + (resto === 1 ? " mês" : " meses")] : [])].join(" e ");
}
/** A janela padrão: os 3 anos até o último registro (7 registros). */
export function janelaPadrao(competencias: string[]): { inicio: string; fim: string } | null {
  if (competencias.length < 2) return null;
  return { inicio: competencias[Math.max(0, competencias.length - 7)], fim: competencias[competencias.length - 1] };
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
export function acrescentarTerritorio(local: SelecaoLocal, alvo: { tipo: "municipio" | "estado"; id: string; grupo: string }): { local: SelecaoLocal; motivo: string | null } {
  if (alvo.tipo === "municipio") {
    if (local.municipios.includes(alvo.id)) return { local, motivo: "Este território já está na seleção do Simulador." };
    if (local.estados.includes(alvo.grupo)) return { local, motivo: "O estado deste município está na seleção como unidade: tire o estado para usar o município." };
    const comOEstado = local.conjuntos.find(conjunto => conjunto.membros.includes("uf:" + alvo.grupo));
    if (comOEstado) return { local, motivo: "O estado deste município está no conjunto " + comOEstado.rotulo + ": tire o conjunto para usar o município." };
    return { local: { ...local, municipios: [...local.municipios, alvo.id].sort(comparar) }, motivo: null };
  }
  if (local.estados.includes(alvo.id)) return { local, motivo: "Este estado já está na seleção do Simulador." };
  const comMembros = local.conjuntos.find(conjunto => conjunto.membros.some(id => id.startsWith("code:" + alvo.id)));
  if (comMembros) return { local, motivo: "O conjunto " + comMembros.rotulo + " tem municípios neste estado: tire o conjunto para usar o estado como unidade." };
  const prefixo = "code:" + alvo.id;
  return { local: { ...local, estados: [...local.estados, alvo.id].sort(comparar), municipios: local.municipios.filter(id => !id.startsWith(prefixo)) }, motivo: null };
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
  if (total > MAX_TERRITORIOS) return "O Simulador compara até " + MAX_TERRITORIOS + " territórios de cada vez; a seleção local tem " + total + ".";
  if (!/^\d{6}$/.test(config.horizonte)) return "Escolha a data final do cenário.";
  for (const cenario of cenariosEmUso(config)) {
    if (cenario.metodo === "manual" && numero(cenario.taxaManual) === null) return "Informe a taxa anual do cenário “" + cenario.nome + "”.";
    for (const item of cenario.intervencoes) {
      const quantidade = numero(item.quantidade);
      if (quantidade === null || quantidade <= 0) return "Informe quantos médicos entram ou saem em cada intervenção.";
      if (!/^\d{6}$/.test(item.em) || (item.periodica && !/^\d{6}$/.test(item.ate))) return "Informe a data de cada intervenção.";
      if (item.periodica && item.ate < item.em) return "Numa intervenção periódica, a data final vem depois da inicial.";
    }
    const plano = cenario.planejamento;
    if (plano) {
      const meta = numero(plano.valor);
      if (plano.meta === "valor" && (meta === null || meta <= 0)) return "Informe a meta do planejamento inverso, em médicos.";
      if (plano.meta === "patamar" && plano.valor.trim() && (meta === null || meta <= 0)) return "Informe a meta do planejamento inverso, em médicos.";
      if (plano.meta === "referencia" && !(config.referencias ?? []).some(ref => ref.id === plano.referencia))
        return "Escolha a referência que serve de meta no planejamento inverso.";
      if (!/^\d{6}$/.test(plano.em) || (plano.periodica && !/^\d{6}$/.test(plano.ate))) return "Informe a data dos acréscimos do planejamento inverso.";
      if (plano.periodica && plano.ate < plano.em) return "No planejamento inverso, a data final dos acréscimos vem depois da inicial.";
    }
  }
  for (const ref of config.referencias ?? []) {
    const valor = numero(ref.valor);
    if (ref.tipo === "valor" && (valor === null || valor < 0)) return "Informe o valor da referência “" + ref.rotulo + "”.";
  }
  return null;
}
/** O plano inicial: a meta num valor (a informar), com um acréscimo um ano depois do último registro. */
export const novoPlano = (em: string): PlanoDaTela => ({ meta: "valor", valor: "", referencia: "", em, periodica: false, ate: em, aCadaMeses: "12",
  permanencia: "100" });
/** Uma referência nova, com o identificador livre seguinte ("r1", "r2"…); null no limite de referências. */
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
  return { ...inicial, acompanha: false, janela, doDetector: { rotulo: alvo.rotulo, fim: alvo.fim, sinais: alvo.sinais, recuperacao: patamar !== null,
    ...(alvo.exploratorio ? { exploratorio: true } : {}) },
    cenarios: [patamar === null ? cenario : { ...cenario, nome: "Recuperação do patamar",
      // O patamar vai com a precisão do Detector (a média de 4 registros: múltiplos de 0,25), para a conta usar o mesmo valor.
      planejamento: { ...novoPlano(anosDepois(ultimoRegistro, 1)), meta: "patamar", valor: String(patamar).replace(".", ",") } }] };
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
  return (referencias ?? []).filter(ref => ref.tipo === "valor" || ref.alvo === ID_DO_BRASIL || ref.alvo.startsWith("code:") || ref.alvo.startsWith("uf:") ||
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
export function pedidoDoSimulador(config: ConfigDoSimulador): Record<string, unknown> {
  const cenarios = cenariosEmUso(config).map(cenario => ({ id: cenario.id, nome: cenario.nome, metodo: cenario.metodo,
    ...(cenario.metodo === "manual" ? { taxa_manual_pct: numero(cenario.taxaManual) } : {}),
    ...(config.modo === "avancado" && cenario.janela ? { janela: cenario.janela } : {}),
    ...(cenario.intervencoes.length ? { intervencoes: cenario.intervencoes.map(item => ({ tipo: item.tipo, quantidade: numero(item.quantidade),
      em: item.em, ...(item.periodica ? { ate: item.ate, a_cada_meses: Math.max(1, Math.round(numero(item.aCadaMeses) ?? 12)) } : {}),
      ...(numero(item.permanencia) !== null && numero(item.permanencia)! < 100 ? { permanencia_pct_ao_ano: numero(item.permanencia) } : {}) })) } : {}),
    ...(cenario.planejamento ? { planejamento: planoDoPedido(cenario.planejamento) } : {}) }));
  const temReferencia = cenarios.some(cenario => cenario.metodo === "M0" && !("intervencoes" in cenario) && !("janela" in cenario) &&
    !("planejamento" in cenario));
  const referencias = (config.referencias ?? []).map(ref => ref.tipo === "valor"
    ? { id: ref.id, tipo: "valor", valor: numero(ref.valor), rotulo: ref.rotulo } : { id: ref.id, tipo: ref.tipo, territorio: ref.alvo });
  return { ...selecaoLocalParaOPedido(config.local), ...(config.janela ? { janela: config.janela } : {}), horizonte: config.horizonte,
    cenarios: temReferencia ? cenarios : [...cenarios, { id: ID_DA_REFERENCIA, nome: "Persistência (referência)", metodo: "M0" }],
    ...(referencias.length ? { referencias, ...(config.metrica === "taxa" ? { comparacao: { metrica: "taxa" } } : {}) } : {}) };
}
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
  observado: number | null; faixa: { inferior: number; superior: number; anos: number; validada: boolean } | null };
export type CenarioCalculado = { id: string; nome: string; estado: string; motivo: string | null;
  metodo: { pedido: string; usado: string | null; rotulo: string | null; padrao: boolean; provisorio: boolean; voltouAoM0: boolean; soma: string | null };
  parametros: Record<string, unknown>; avisos: { codigo: string; texto: string }[]; trajetoria: PontoDoCenario[];
  faixa: { estado: string; motivo: string | null; rotulo: string | null };
  final: { data: string; base: number; intervencao: number; total: number; faixa: PontoDoCenario["faixa"] } | null; texto: string | null;
  horizonte: { anos: number; aviso: string } | null;
  /** Etapa 5: o cenário diante de cada referência, o planejamento inverso e a hipótese derivada da simulação. */
  comparacoes: ComparacaoDoCenario[]; planejamento: PlanejamentoDoCenario | null; hipotetico: HipoteseDerivada | null };
export type PontoDaComparacao = { data: string; territorio: number; referencia: number; diferenca: number; razao: number | null; indice: number | null };
export type ComparacaoDoCenario = { id: string; rotulo: string; tipo: string; metrica: string; estado: string; motivo: string | null; avisos: string[];
  descricao: string | null; pontos: PontoDaComparacao[]; final: PontoDaComparacao | null;
  alcance: { estado: string; data: string | null } | null; texto: string | null };
export type PlanejamentoDoCenario = { estado: string; motivo: string | null; meta: { tipo: string; valor: number; rotulo: string } | null;
  semOPlano: number | null; eventos: number; datas: string[]; porEvento: number | null; total: number | null; teoricoPorEvento: number | null;
  resultado: number | null; texto: string | null;
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
export type RespostaDoSimulador = { versao: string; fonte: { base: string; categoria: string; versao: string; primeira: string; ultima: string };
  competencias: string[]; ultimoRegistro: string; janela: { inicio: string; fim: string; registros: number; anos: number; padrao: boolean };
  horizonte: { data: string; anosDesdeOUltimoRegistro: number }; territorios: TerritorioSimulado[];
  retroprojecao: { origens: string[]; faixas: FaixaDaRetroprojecao[]; tabela: LinhaDaRetroprojecao[] }; notas: string[]; limitacoes: string[];
  referencias: ReferenciaDaResposta[]; comparacao: { metrica: string; hipoteseDePopulacao: string | null } };

const objeto = (valor: unknown): Record<string, unknown> => valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : {};
const lista = (valor: unknown): unknown[] => Array.isArray(valor) ? valor : [];
const texto = (valor: unknown): string | null => typeof valor === "string" && valor ? valor : null;
const num = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;
const textos = (valor: unknown): string[] => lista(valor).filter((item): item is string => typeof item === "string");
function faixaDe(bruto: unknown): PontoDoCenario["faixa"] {
  const f = objeto(bruto);
  return num(f.inferior) !== null && num(f.superior) !== null ? { inferior: num(f.inferior)!, superior: num(f.superior)!, anos: num(f.anos) ?? 0,
    validada: f.validada === true } : null;
}
function pontoDaComparacao(bruto: unknown): PontoDaComparacao | null {
  const p = objeto(bruto);
  return texto(p.data) && num(p.territorio) !== null && num(p.referencia) !== null ? { data: texto(p.data)!, territorio: num(p.territorio)!,
    referencia: num(p.referencia)!, diferenca: num(p.diferenca) ?? 0, razao: num(p.razao), indice: num(p.indice) } : null;
}
function comparacaoDe(bruto: unknown): ComparacaoDoCenario {
  const c = objeto(bruto), a = objeto(c.alcance);
  return { id: texto(c.id) ?? "", rotulo: texto(c.rotulo) ?? "", tipo: texto(c.tipo) ?? "", metrica: texto(c.metrica) ?? "quantidade",
    estado: texto(c.estado) ?? "", motivo: texto(c.motivo), avisos: textos(c.avisos), descricao: texto(c.descricao),
    pontos: lista(c.pontos).map(pontoDaComparacao).filter((ponto): ponto is PontoDaComparacao => !!ponto), final: pontoDaComparacao(c.final),
    alcance: texto(a.estado) ? { estado: texto(a.estado)!, data: texto(a.data) } : null, texto: texto(c.texto) };
}
function planejamentoDe(bruto: unknown): PlanejamentoDoCenario | null {
  if (!bruto || typeof bruto !== "object") return null;
  const p = objeto(bruto), meta = objeto(p.meta), i = objeto(p.intervencao);
  return { estado: texto(p.estado) ?? "", motivo: texto(p.motivo),
    meta: num(meta.valor) !== null ? { tipo: texto(meta.tipo) ?? "", valor: num(meta.valor)!, rotulo: texto(meta.rotulo) ?? "" } : null,
    semOPlano: num(p.sem_o_plano), eventos: num(p.eventos) ?? 0, datas: textos(p.datas), porEvento: num(p.por_evento), total: num(p.total),
    teoricoPorEvento: num(p.teorico_por_evento), resultado: num(p.resultado), texto: texto(p.texto),
    intervencao: num(i.quantidade) !== null && texto(i.em) ? { tipo: texto(i.tipo) ?? "acrescimo", quantidade: num(i.quantidade)!, em: texto(i.em)!,
      ate: texto(i.ate), aCadaMeses: num(i.a_cada_meses), permanencia: num(i.permanencia_pct_ao_ano) ?? 100 } : null };
}
function hipoteticoDe(bruto: unknown): HipoteseDerivada | null {
  if (!bruto || typeof bruto !== "object") return null;
  const h = objeto(bruto), f = h.na_faixa ? objeto(h.na_faixa) : null;
  return num(h.valor) === null ? null : { rotulo: texto(h.rotulo) ?? "", data: texto(h.data) ?? "", valor: num(h.valor)!, inteiro: num(h.inteiro) ?? 0,
    classe: texto(h.classe), impactoPct: num(h.impacto_pct), naFaixa: f ? { inferior: texto(f.inferior), superior: texto(f.superior) } : null };
}
function cenarioDe(bruto: unknown): CenarioCalculado {
  const o = objeto(bruto), m = objeto(o.metodo), f = objeto(o.faixa), fim = objeto(o.final), h = objeto(o.horizonte);
  return { id: texto(o.id) ?? "", nome: texto(o.nome) ?? "", estado: texto(o.estado) ?? "", motivo: texto(o.motivo),
    metodo: { pedido: texto(m.pedido) ?? "", usado: texto(m.usado), rotulo: texto(m.rotulo), padrao: m.padrao === true, provisorio: m.provisorio === true,
      voltouAoM0: m.voltou_ao_m0 === true, soma: texto(m.soma) },
    parametros: objeto(o.parametros),
    avisos: lista(o.avisos).map(item => ({ codigo: texto(objeto(item).codigo) ?? "", texto: texto(objeto(item).texto) ?? "" })).filter(item => item.texto),
    trajetoria: lista(o.trajetoria).map(item => {
      const p = objeto(item);
      return { data: texto(p.data) ?? "", anos: num(p.anos) ?? 0, base: num(p.base) ?? 0, intervencao: num(p.intervencao) ?? 0, total: num(p.total) ?? 0,
        retroprojecao: p.retroprojecao === true, observado: num(p.observado), faixa: faixaDe(p.faixa) };
    }),
    faixa: { estado: texto(f.estado) ?? "indisponivel", motivo: texto(f.motivo), rotulo: texto(f.rotulo) },
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
      ultima: texto(fonte.ultima) ?? "" },
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
    retroprojecao: { origens: textos(retro.origens),
      faixas: lista(retro.faixas).map(item => {
        const f = objeto(item);
        return { porte: texto(f.porte) ?? "", anos: num(f.anos) ?? 0, inferiorPct: num(f.inferior_pct) ?? 0, superiorPct: num(f.superior_pct) ?? 0,
          casos: num(f.casos) ?? 0, origens: num(f.origens) ?? 0, coberturaPct: num(f.cobertura_pct), rotulo: texto(f.rotulo) ?? "" };
      }),
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
    comparacao: { metrica: texto(comparacao.metrica) ?? "quantidade", hipoteseDePopulacao: texto(comparacao.hipotese_de_populacao) } };
}

// ------------------------------------------------------------------------------------------------ apresentação
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const umaCasa = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
const duasCasas = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
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
  M1: "taxa composta da janela", M2: "tendência linear", M3: "tendência log-linear", manual: "taxa informada por você" };
/** A faixa de 80% da data final, em linguagem simples (decisão D-C): o que ela é, de onde vem e, de 3 a 4 anos, que é um limite
 * provisório. Sem faixa, "indisponível" e o motivo: nada é extrapolado. */
export function textoDaFaixa(cenario: CenarioCalculado, conjunto = false): string {
  const faixa = cenario.final?.faixa;
  if (!cenario.final || !faixa) return "Faixa de 80%: indisponível" + (cenario.faixa.motivo ? ". " + cenario.faixa.motivo
    : cenario.faixa.estado === "disponivel" ? " nesta data: ela vai só até 4 anos depois do último registro usado." : ".");
  return "Faixa de 80% " + (conjunto ? "(aproximação) " : "") + "em " + competenciaCurta(cenario.final.data) + ": de " + formatarMedicos(faixa.inferior) +
    " a " + formatarMedicos(faixa.superior) +
    " médicos. No passado da base, em 8 de cada 10 casos de municípios " + (conjunto ? "com o porte desta soma (uma aproximação para o conjunto)" : "do mesmo porte") +
    ", o número observado ficou dentro dessa margem; ela acompanha a intervenção." + (faixa.validada ? " Conferida com dados que não entraram no cálculo dela."
      : " Limite provisório: para 3 e 4 anos, a margem ainda não foi conferida com dados à parte.");
}
/** As contas da data final, com uma casa: a base do cenário, a intervenção e o total (o texto do cenário arredonda para o inteiro). */
export function contasDoFinal(cenario: CenarioCalculado): string {
  const f = cenario.final;
  if (!f) return "";
  if (!f.intervencao) return "Na data final: base do cenário de " + formatarMedicos(f.base) + " médicos, sem intervenção.";
  return "Na data final, neste território: base do cenário de " + formatarMedicos(f.base) + (f.intervencao > 0 ? " + " : " − ") +
    formatarMedicos(Math.abs(f.intervencao)) + " da intervenção = " + formatarMedicos(f.total) + " médicos (o texto acima arredonda para o inteiro).";
}
/** O método de um cenário na tabela, em palavras. Num conjunto, a soma vem primeiro: a soma das projeções dos membros (a
 * persistência, com ou sem o crescimento do estado de cada um) ou a soma das contagens dos componentes (os demais métodos). */
export function metodoNaTabela(cenario: CenarioCalculado, conjunto = false): string {
  const usado = cenario.metodo.usado ?? "", nome = NOME_CURTO_DO_METODO[usado] ?? usado;
  if (!conjunto) return nome + (cenario.metodo.voltouAoM0 ? " (sem o crescimento do estado)" : "");
  if (cenario.metodo.soma) return cenario.metodo.soma + (usado === "M0d" ? " (cada um com o crescimento do seu estado)" : " (cada um no último valor)");
  return "soma das contagens dos componentes · " + nome;
}
const NOMES_DAS_INTENSIDADES: Record<string, string> = { atencao: "atenção", alta: "alta", critica: "crítica" };
const intensidadeEstrutural = (classe: string | null) => classe ? "intensidade " + (NOMES_DAS_INTENSIDADES[classe] ?? classe) : "sem sinal";
/** A única leitura do Detector que vale para uma trajetória simulada (seção 3.3 do anexo): a dependência de poucos médicos do valor
 * do cenário, rotulada como hipótese derivada da simulação. Não é um sinal observado. */
export function textoDaHipotese(h: HipoteseDerivada): string {
  const quantos = formatarMedicos(h.inteiro) + (h.inteiro === 1 ? " médico" : " médicos");
  const rotulo = h.rotulo || "hipótese da simulação";   // o rótulo é o do motor
  return rotulo.charAt(0).toUpperCase() + rotulo.slice(1) + " (não é um sinal observado): com " + quantos + " em " + competenciaCurta(h.data) + ", " +
    (h.classe ? "a dependência de poucos médicos teria " + intensidadeEstrutural(h.classe) : "não haveria sinal de dependência de poucos médicos por esta escala") +
    (h.impactoPct !== null && h.inteiro <= 20 ? " (a saída de 1 tiraria " + umaCasa.format(h.impactoPct) + "%)" : "") + "." +
    (h.naFaixa && (h.naFaixa.inferior !== h.classe || h.naFaixa.superior !== h.classe)
      ? " Nos limites da faixa de 80%: " + intensidadeEstrutural(h.naFaixa.inferior) + " no inferior e " + intensidadeEstrutural(h.naFaixa.superior) + " no superior." : "") +
    " A intensidade usa os limites provisórios do Detector; os sinais de perda, de patamar e de declínio valem só para registros reais.";
}
/** A hipótese entra na tela só quando é pertinente: há intensidade no valor do cenário ou num dos limites da faixa, ou o território
 * teria até 20 médicos (a escala trata de poucos médicos; num território grande, o painel seria só ruído). */
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

// ------------------------------------------------------------------------------------------------ exportar e importar
export const FORMATO_DO_CENARIO = "ADT-CENARIO/1";
/** A configuração dos cenários num JSON legível: a seleção local (com a composição e a versão dos conjuntos), a janela, a data final
 * e os cenários, com a versão do método e da base em que foram montados. */
export function exportarCenario(config: ConfigDoSimulador, c: { versaoDoMetodo: string; versaoDaBase: string; ultimoRegistro: string; quando: string }): string {
  return JSON.stringify({ formato: FORMATO_DO_CENARIO, ferramenta: "Simulador de Cenários Territoriais", versao_do_metodo: c.versaoDoMetodo,
    base: { nome: "Brasil", categoria: "MEDICINA", versao: c.versaoDaBase, ultimo_registro: c.ultimoRegistro }, exportado_em: c.quando,
    aviso: "Cenários hipotéticos e condicionais: não são previsão nem recomendação.",
    selecao_local: config.local, janela: config.janela, horizonte: config.horizonte, modo: config.modo, cenarios: config.cenarios,
    ...(config.referencias?.length ? { referencias: config.referencias } : {}), ...(config.metrica === "taxa" ? { metrica: "taxa" } : {}) }, null, 2);
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
      ...(validas.length ? { referencias: validas } : {}), ...(o.metrica === "taxa" ? { metrica: "taxa" as const } : {}) } };
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
  const cabecalho = ["Identificador", "Território", "Tipo", "Unidade de contagem", "Cenário", "Método pedido", "Método usado", "Estado do cenário",
    "Origem do cenário", "Médicos na origem", "Janela: início", "Janela: fim", "Data", "Natureza", "Observado", "Base do cenário", "Intervenção",
    "Total do cenário", "Faixa de 80%: inferior", "Faixa de 80%: superior", "Avisos", "Texto do cenário",
    "Planejamento inverso: meta", "Planejamento inverso: médicos por evento", "Planejamento inverso: eventos",
    "Hipótese da simulação: intensidade estrutural", "Versão do método", "Versão da base"];
  const linhas = [cabecalho.map(celula).join(";")];
  for (const territorio of resposta.territorios) for (const cenario of territorio.cenarios) {
    const p = cenario.parametros, janela = objeto(p.janela);
    const fixas = [territorio.id, territorio.rotulo, territorio.tipo, territorio.unidade, cenario.nome, cenario.metodo.pedido, cenario.metodo.usado ?? "",
      cenario.estado + (cenario.motivo ? ": " + cenario.motivo : ""), texto(p.origem) ?? "", num(p.n0), texto(janela.inicio) ?? "", texto(janela.fim) ?? ""];
    const plano = cenario.planejamento;
    const fim = [cenario.avisos.map(aviso => aviso.codigo).join(" | "), cenario.texto ?? "", plano?.meta?.rotulo ?? "",
      plano?.estado === "calculado" || plano?.estado === "ja_alcancada" ? plano.porEvento : plano ? plano.estado : null, plano ? plano.eventos : null,
      cenario.hipotetico ? cenario.hipotetico.classe ?? "sem sinal por esta escala" : "", resposta.versao, resposta.fonte.versao];
    if (!cenario.trajetoria.length) { linhas.push([...fixas, "", "", "", "", "", "", "", "", ...fim].map(celula).join(";")); continue; }
    for (const ponto of cenario.trajetoria) linhas.push([...fixas, ponto.data, ponto.retroprojecao ? "retroprojeção (data com registro)" : "cenário hipotético",
      ponto.observado, ponto.base, ponto.intervencao, ponto.total, ponto.faixa?.inferior ?? null, ponto.faixa?.superior ?? null, ...fim].map(celula).join(";"));
  }
  return "\uFEFF" + linhas.join("\r\n") + "\r\n";
}
