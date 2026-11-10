// Modelo puro do Simulador de Cenários Territoriais (comando V22, Eixo II, etapa 4; Docs/SIMULADOR_DE_CENARIOS.md): a seleção local
// (uma cópia da seleção principal, editável só aqui), a configuração dos cenários (janela, método, horizonte e intervenções), o
// pedido a POST /api/simulador, a leitura da resposta, a exportação e a importação dos cenários (JSON) e a exportação dos
// resultados (CSV). Nada é projetado na tela: a base de cada cenário, a intervenção, a faixa e o texto fixo vêm do motor
// (backend/simulador.py). Sem importações em tempo de execução, para os testes Node lerem só este arquivo.
import type { PainelMunicipios } from "./painelApi";

export type SelecaoDasFerramentas = { base?: { municipios: PainelMunicipios }; estados_unidade?: string[];
  conjuntos?: { id: string; rotulo: string; membros: string[]; versao?: number }[] };
/** A seleção local do Simulador: listas explícitas, para acrescentar e tirar territórios sem tocar na seleção principal. */
export type SelecaoLocal = { municipios: string[]; estados: string[]; conjuntos: { id: string; rotulo: string; membros: string[]; versao?: number }[] };
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
export type CenarioDaTela = { id: string; nome: string; metodo: MetodoDoCenario; taxaManual: string; janela: { inicio: string; fim: string } | null;
  intervencoes: IntervencaoDaTela[] };
export type ConfigDoSimulador = { local: SelecaoLocal; janela: { inicio: string; fim: string } | null; horizonte: string; modo: "simples" | "avancado";
  cenarios: CenarioDaTela[];
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
export const totalDaSelecaoLocal = (local: SelecaoLocal): number => local.municipios.length + local.estados.length + local.conjuntos.length;
/** A seleção local no contrato das ferramentas (o do painel). */
export function selecaoLocalParaOPedido(local: SelecaoLocal): SelecaoDasFerramentas {
  return { ...(local.municipios.length ? { base: { municipios: { todos: false, estados: [], ids: [...local.municipios].sort(comparar) } } } : {}),
    ...(local.estados.length ? { estados_unidade: [...local.estados].sort(comparar) } : {}), ...(local.conjuntos.length ? { conjuntos: local.conjuntos } : {}) };
}
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
    conjuntos: local.conjuntos.filter(item => item.id !== id) };
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
  }
  return null;
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
      ...(numero(item.permanencia) !== null && numero(item.permanencia)! < 100 ? { permanencia_pct_ao_ano: numero(item.permanencia) } : {}) })) } : {}) }));
  const temReferencia = cenarios.some(cenario => cenario.metodo === "M0" && !("intervencoes" in cenario) && !("janela" in cenario));
  return { ...selecaoLocalParaOPedido(config.local), ...(config.janela ? { janela: config.janela } : {}), horizonte: config.horizonte,
    cenarios: temReferencia ? cenarios : [...cenarios, { id: ID_DA_REFERENCIA, nome: "Persistência (referência)", metodo: "M0" }] };
}

// ------------------------------------------------------------------------------------------------ resposta
export type PontoDoCenario = { data: string; anos: number; base: number; intervencao: number; total: number; retroprojecao: boolean;
  observado: number | null; faixa: { inferior: number; superior: number; anos: number; validada: boolean } | null };
export type CenarioCalculado = { id: string; nome: string; estado: string; motivo: string | null;
  metodo: { pedido: string; usado: string | null; rotulo: string | null; padrao: boolean; provisorio: boolean; voltouAoM0: boolean; soma: string | null };
  parametros: Record<string, unknown>; avisos: { codigo: string; texto: string }[]; trajetoria: PontoDoCenario[];
  faixa: { estado: string; motivo: string | null; rotulo: string | null };
  final: { data: string; base: number; intervencao: number; total: number; faixa: PontoDoCenario["faixa"] } | null; texto: string | null;
  horizonte: { anos: number; aviso: string } | null };
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
  retroprojecao: { origens: string[]; faixas: FaixaDaRetroprojecao[]; tabela: LinhaDaRetroprojecao[] }; notas: string[]; limitacoes: string[] };

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
    texto: texto(o.texto), horizonte: num(h.anos) !== null ? { anos: num(h.anos)!, aviso: texto(h.aviso) ?? "normal" } : null };
}
/** A resposta de POST /api/simulador nos tipos da tela. */
export function normalizarSimulador(bruto: unknown): RespostaDoSimulador {
  const o = objeto(bruto), fonte = objeto(o.fonte), janela = objeto(o.janela), horizonte = objeto(o.horizonte), retro = objeto(o.retroprojecao);
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
    notas: textos(o.notas), limitacoes: textos(o.limitacoes) };
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
  return "Faixa de 80% em " + competenciaCurta(cenario.final.data) + ": de " + formatarMedicos(faixa.inferior) + " a " + formatarMedicos(faixa.superior) +
    " médicos. No passado da base, em 8 de cada 10 casos de municípios " + (conjunto ? "com o porte desta soma (uma aproximação para o conjunto)" : "do mesmo porte") +
    ", o número observado ficou dentro dessa margem; ela acompanha a intervenção." + (faixa.validada ? " Conferida com dados que não entraram no cálculo dela."
      : " Limite provisório: para 3 e 4 anos, a margem ainda não foi conferida com dados à parte.");
}
/** As contas da data final, com uma casa: a base do cenário, a intervenção e o total (o texto do cenário arredonda para o inteiro). */
export function contasDoFinal(cenario: CenarioCalculado): string {
  const f = cenario.final;
  if (!f) return "";
  if (!f.intervencao) return "Na data final: base do cenário de " + formatarMedicos(f.base) + " médicos, sem intervenção.";
  return "Na data final: base do cenário de " + formatarMedicos(f.base) + (f.intervencao > 0 ? " + " : " − ") + formatarMedicos(Math.abs(f.intervencao)) +
    " da intervenção = " + formatarMedicos(f.total) + " médicos (o texto acima arredonda para o inteiro).";
}
/** O valor final de um cenário, para a tabela: "26,4 (20,3 a 39,0)" com a faixa, ou o motivo quando não há valor. */
export function textoDoFinal(cenario: CenarioCalculado): string {
  if (cenario.estado !== "calculado" || !cenario.final) return cenario.estado === "retirada_acima_do_estoque" ? "retirada acima do estoque: rever"
    : cenario.estado === "nao_aplicavel" ? "não se aplica" : "não calculável";
  const faixa = cenario.final.faixa;
  return formatarMedicos(cenario.final.total) + (faixa ? " (" + formatarMedicos(faixa.inferior) + " a " + formatarMedicos(faixa.superior) + ")" : "");
}

// ------------------------------------------------------------------------------------------------ exportar e importar
export const FORMATO_DO_CENARIO = "ADT-CENARIO/1";
/** A configuração dos cenários num JSON legível: a seleção local (com a composição e a versão dos conjuntos), a janela, a data final
 * e os cenários, com a versão do método e da base em que foram montados. */
export function exportarCenario(config: ConfigDoSimulador, c: { versaoDoMetodo: string; versaoDaBase: string; ultimoRegistro: string; quando: string }): string {
  return JSON.stringify({ formato: FORMATO_DO_CENARIO, ferramenta: "Simulador de Cenários Territoriais", versao_do_metodo: c.versaoDoMetodo,
    base: { nome: "Brasil", categoria: "MEDICINA", versao: c.versaoDaBase, ultimo_registro: c.ultimoRegistro }, exportado_em: c.quando,
    aviso: "Cenários hipotéticos e condicionais: não são previsão nem recomendação.",
    selecao_local: config.local, janela: config.janela, horizonte: config.horizonte, modo: config.modo, cenarios: config.cenarios }, null, 2);
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
      }) };
  }).slice(0, MAX_CENARIOS);
  if (!cenarios.length || !texto(o.horizonte)) return { config: null, erro: "O cenário do arquivo está incompleto (faltam os cenários ou a data final).", versaoDaBase: null };
  return { erro: null, versaoDaBase: texto(objeto(o.base).versao),
    config: { local: { municipios: textos(local.municipios), estados: textos(local.estados), conjuntos },
      janela: texto(janela.inicio) && texto(janela.fim) ? { inicio: texto(janela.inicio)!, fim: texto(janela.fim)! } : null,
      horizonte: texto(o.horizonte)!, modo: o.modo === "avancado" ? "avancado" : "simples", cenarios } };
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
    "Total do cenário", "Faixa de 80%: inferior", "Faixa de 80%: superior", "Avisos", "Texto do cenário", "Versão do método", "Versão da base"];
  const linhas = [cabecalho.map(celula).join(";")];
  for (const territorio of resposta.territorios) for (const cenario of territorio.cenarios) {
    const p = cenario.parametros, janela = objeto(p.janela);
    const fixas = [territorio.id, territorio.rotulo, territorio.tipo, territorio.unidade, cenario.nome, cenario.metodo.pedido, cenario.metodo.usado ?? "",
      cenario.estado + (cenario.motivo ? ": " + cenario.motivo : ""), texto(p.origem) ?? "", num(p.n0), texto(janela.inicio) ?? "", texto(janela.fim) ?? ""];
    const fim = [cenario.avisos.map(aviso => aviso.codigo).join(" | "), cenario.texto ?? "", resposta.versao, resposta.fonte.versao];
    if (!cenario.trajetoria.length) { linhas.push([...fixas, "", "", "", "", "", "", "", "", ...fim].map(celula).join(";")); continue; }
    for (const ponto of cenario.trajetoria) linhas.push([...fixas, ponto.data, ponto.retroprojecao ? "retroprojeção (data com registro)" : "cenário hipotético",
      ponto.observado, ponto.base, ponto.intervencao, ponto.total, ponto.faixa?.inferior ?? null, ponto.faixa?.superior ?? null, ...fim].map(celula).join(";"));
  }
  return "\uFEFF" + linhas.join("\r\n") + "\r\n";
}
