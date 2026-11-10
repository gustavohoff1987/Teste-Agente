// Modelo puro do Detector de Sinais Territoriais (comando V22, Eixo II; Docs/DETECTOR_DE_SINAIS.md): a leitura da resposta de
// POST /api/detector para os tipos da tela, os textos curtos da tabela, os filtros, a ordem e as exportações. Nada é calculado
// aqui: a contagem, a mudança, a comparação com territórios parecidos e a intensidade do sinal vêm do motor (backend/detector.py).
// A tela usa linguagem simples (decisão D-C de 10/11/2026): "sem classificação", com o motivo, no lugar de "não calibrado";
// "limite provisório", no lugar de "candidato"; os termos técnicos ficam nos detalhes e nas exportações. Sem importações em tempo
// de execução, para os testes Node lerem só este arquivo.
import type { PainelMunicipios } from "./painelApi";

export type ClasseDoSinal = "atencao" | "alta" | "critica";
export const NOMES_DAS_CLASSES: Record<ClasseDoSinal, string> = { atencao: "Atenção", alta: "Alta", critica: "Crítica" };
export const GRAVIDADE: Record<string, number> = { critica: 3, alta: 2, atencao: 1 };
export const ROTULOS_DOS_PORTES = ["1 a 3", "4 a 9", "10 a 19", "20 a 49", "50 a 99", "100 a 299", "300 ou mais"];
export const TEXTO_LIMITES_PROVISORIOS = "Intensidade do sinal com limites provisórios: descreve o indicador, não a urgência do atendimento.";

/** A seleção que as ferramentas recebem: o mesmo contrato do painel (os municípios, os estados como unidade e os conjuntos). */
export type SelecaoDasFerramentas = { base?: { municipios: PainelMunicipios }; estados_unidade?: string[];
  conjuntos?: { id: string; rotulo: string; membros: string[]; versao?: number }[] };
export type JanelaDoDetector = { inicio: string; fim: string; registros: number; meses: number; padrao: boolean;
  ultimoRegistroDaBase: string; eOUltimo: boolean };
export type ParametrosDoDetector = Record<string, Record<string, number>>;
export type OpcoesDoDetector = SelecaoDasFerramentas & { janela?: { inicio?: string; fim?: string }; parametros?: ParametrosDoDetector;
  detalhe?: string };

export type LinhaDoDetector = {
  id: string; tipo: "municipio" | "estado" | "conjunto" | "brasil"; nivel: string; rotulo: string; uf: string | null;
  ultima: { competencia: string; valor: number; naData: boolean } | null; porte: number | null; sinais: string[];
  dimensoes: { estrutural: ClasseDoSinal | null; trajetoria: ClasseDoSinal | null; ritmo: ClasseDoSinal | null };
  estrutural: { estado: string; classe: ClasseDoSinal | null; n: number | null; impactoPct: number | null; zeros: number | null; mantida: boolean };
  perda: { estado: string; classe: ClasseDoSinal | null; delta: number | null; pct: number | null; de: string | null; ate: string | null;
    magnitude: string | null; motivo: string | null; verificar: string | null };
  patamar: { estado: string; classe: ClasseDoSinal | null; patamar: number | null; diferencaPct: number | null; abaixo: boolean; critica: string | null };
  declinio: { estado: string; reducoes: number | null; perdaPct: number | null; sinal: string | null };
  desaceleracao: { estado: string; desacelera: boolean; persistente: boolean | null; rotulo: string | null };
  instabilidade: { estado: string; indice: number | null };
  registro: { estado: string; tipos: string[] };
  membros: number | null;
};
export type CelulaDaPerda = { porte: string; transicoes: number; quedaIncomumPct: number | null; quedaMuitoIncomumPct: number | null;
  alta: string; critica: string };
export type FaixaDoPatamar = { porte: string; observacoes: number; afastamentoIncomumPct: number | null; alta: string; critica: string };
export type RespostaDoDetector = {
  versao: string; fonte: { base: string; categoria: string; versao: string; primeira: string; ultima: string; competencias: number;
    unidades: Record<string, string> };
  janela: JanelaDoDetector; competencias: string[];
  parametros: { padrao: ParametrosDoDetector; emUso: ParametrosDoDetector; personalizados: boolean;
    editaveis: Record<string, Record<string, { minimo: number; maximo: number; inteiro: boolean }>> };
  exploratorio: boolean; linhas: LinhaDoDetector[];
  resumo: { territorios: number; porTipo: Record<string, number>; estrutural: Record<string, number>; trajetoria: Record<string, number>;
    sinais: Record<string, number>; semRegistroNaData: number };
  calibracao: { competencia: string; intervaloMeses: number | null; perda: CelulaDaPerda[]; patamar: FaixaDoPatamar[];
    monitoramento: { avaliadas: number; incomuns: number; taxaPct: number | null } };
  notas: string[]; limitacoes: string[];
};
export type PontoDaSerie = { competencia: string; valor: number | null; estado: string; marca: string | null; membrosSemRegistro: number | null };
export type PassoDoHistorico = { competencia: string; valor: number | null; estrutural: ClasseDoSinal | null;
  perda: { delta: number; pct: number | null; estado: string; classe: ClasseDoSinal | null } | null;
  patamar: { estado: string; classe: ClasseDoSinal | null; diferencaPct: number | null };
  declinio: { reducoes: number | null; sinal: string | null } | null; desaceleracao: { desacelera: boolean; rotulo: string | null } | null };
export type FenomenoDoDetalhe = { chave: string; numero: string; nome: string; dimensao: string; estado: string; classe: ClasseDoSinal | null;
  situacao: string; observado: string; criterio: string; habitual: string; significa: string; naoSignifica: string; limitacoes: string;
  qualidade: string };
export type DetalheDoDetector = { id: string; rotulo: string; tipo: string; unidade: string; membros: string[]; janela: JanelaDoDetector;
  inicioDoTerritorio: string; depoisDaQuebra: boolean; serie: PontoDaSerie[]; historico: PassoDoHistorico[]; fenomenos: FenomenoDoDetalhe[];
  notas: string[]; exploratorio: boolean };

// ------------------------------------------------------------------------------------------------ leitura da resposta
const objeto = (valor: unknown): Record<string, unknown> => valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : {};
const lista = (valor: unknown): unknown[] => Array.isArray(valor) ? valor : [];
const texto = (valor: unknown): string | null => typeof valor === "string" && valor ? valor : null;
const num = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;
const classe = (valor: unknown): ClasseDoSinal | null => valor === "atencao" || valor === "alta" || valor === "critica" ? valor : null;
const textos = (valor: unknown): string[] => lista(valor).filter((item): item is string => typeof item === "string");
const numeros = (valor: unknown): Record<string, number> => Object.fromEntries(Object.entries(objeto(valor))
  .filter((par): par is [string, number] => typeof par[1] === "number"));

function janelaDe(bruto: unknown): JanelaDoDetector {
  const j = objeto(bruto);
  return { inicio: texto(j.inicio) ?? "", fim: texto(j.fim) ?? "", registros: num(j.registros) ?? 0, meses: num(j.meses) ?? 0,
    padrao: j.padrao === true, ultimoRegistroDaBase: texto(j.ultimo_registro_da_base) ?? "", eOUltimo: j.e_o_ultimo === true };
}
function parametrosDe(bruto: unknown): ParametrosDoDetector {
  return Object.fromEntries(Object.entries(objeto(bruto)).map(([grupo, valores]) => [grupo, numeros(valores)]));
}
function linhaDe(bruto: unknown): LinhaDoDetector | null {
  const o = objeto(bruto);
  const id = texto(o.id), rotulo = texto(o.rotulo);
  if (!id || !rotulo) return null;
  const ultima = objeto(o.ultima), e = objeto(o.estrutural), pe = objeto(o.perda), pa = objeto(o.patamar), de = objeto(o.declinio),
    ds = objeto(o.desaceleracao), ins = objeto(o.instabilidade), reg = objeto(o.registro), dim = objeto(o.dimensoes);
  const tipo = o.tipo === "estado" || o.tipo === "conjunto" || o.tipo === "brasil" ? o.tipo : "municipio";
  return { id, rotulo, tipo, nivel: texto(o.nivel) ?? "municipios", uf: texto(o.uf),
    ultima: texto(ultima.competencia) && num(ultima.valor) !== null
      ? { competencia: texto(ultima.competencia)!, valor: num(ultima.valor)!, naData: ultima.na_data === true } : null,
    porte: num(o.porte), sinais: textos(o.sinais),
    dimensoes: { estrutural: classe(dim.estrutural), trajetoria: classe(dim.trajetoria), ritmo: classe(dim.ritmo) },
    estrutural: { estado: texto(e.estado) ?? "", classe: classe(e.classe), n: num(e.n), impactoPct: num(e.impacto_pct), zeros: num(e.zeros),
      mantida: e.mantida === true },
    perda: { estado: texto(pe.estado) ?? "", classe: classe(pe.classe), delta: num(pe.delta), pct: num(pe.pct), de: texto(pe.de),
      ate: texto(pe.ate), magnitude: texto(pe.magnitude), motivo: texto(pe.motivo), verificar: texto(pe.verificar) },
    patamar: { estado: texto(pa.estado) ?? "", classe: classe(pa.classe), patamar: num(pa.patamar), diferencaPct: num(pa.diferenca_pct),
      abaixo: pa.abaixo === true, critica: texto(pa.critica) },
    declinio: { estado: texto(de.estado) ?? "", reducoes: num(de.reducoes), perdaPct: num(de.perda_pct), sinal: texto(de.sinal) },
    desaceleracao: { estado: texto(ds.estado) ?? "", desacelera: ds.desacelera === true,
      persistente: typeof ds.persistente === "boolean" ? ds.persistente : null, rotulo: texto(ds.rotulo) },
    instabilidade: { estado: texto(ins.estado) ?? "", indice: num(ins.indice) },
    registro: { estado: texto(reg.estado) ?? "normal", tipos: textos(reg.tipos) }, membros: num(o.membros) };
}

/** A resposta da tabela de POST /api/detector nos tipos da tela. */
export function normalizarDetector(bruto: unknown): RespostaDoDetector {
  const o = objeto(bruto), fonte = objeto(o.fonte), p = objeto(o.parametros), resumo = objeto(o.resumo), cal = objeto(o.calibracao),
    mon = objeto(cal.monitoramento);
  const editaveis = Object.fromEntries(Object.entries(objeto(p.editaveis)).map(([grupo, chaves]) => [grupo,
    Object.fromEntries(Object.entries(objeto(chaves)).map(([chave, faixa]) => {
      const f = objeto(faixa);
      return [chave, { minimo: num(f.minimo) ?? 0, maximo: num(f.maximo) ?? 0, inteiro: f.inteiro === true }];
    }))]));
  return { versao: texto(o.versao) ?? "",
    fonte: { base: texto(fonte.base) ?? "", categoria: texto(fonte.categoria) ?? "", versao: texto(fonte.versao) ?? "",
      primeira: texto(fonte.primeira) ?? "", ultima: texto(fonte.ultima) ?? "", competencias: num(fonte.competencias) ?? 0,
      unidades: Object.fromEntries(Object.entries(objeto(fonte.unidades)).filter((par): par is [string, string] => typeof par[1] === "string")) },
    janela: janelaDe(o.janela), competencias: textos(o.competencias),
    parametros: { padrao: parametrosDe(p.padrao), emUso: parametrosDe(p.em_uso), personalizados: p.personalizados === true, editaveis },
    exploratorio: o.exploratorio === true,
    linhas: lista(o.linhas).map(linhaDe).filter((linha): linha is LinhaDoDetector => !!linha),
    resumo: { territorios: num(resumo.territorios) ?? 0, porTipo: numeros(resumo.por_tipo), estrutural: numeros(resumo.estrutural),
      trajetoria: numeros(resumo.trajetoria), sinais: numeros(resumo.sinais), semRegistroNaData: num(resumo.sem_registro_na_data) ?? 0 },
    calibracao: { competencia: texto(cal.competencia) ?? "", intervaloMeses: num(cal.intervalo_meses),
      perda: lista(cal.perda).map(item => {
        const c = objeto(item);
        return { porte: texto(c.porte) ?? "", transicoes: num(c.transicoes) ?? 0, quedaIncomumPct: num(c.queda_incomum_pct),
          quedaMuitoIncomumPct: num(c.queda_muito_incomum_pct), alta: texto(c.alta) ?? "", critica: texto(c.critica) ?? "" };
      }),
      patamar: lista(cal.patamar).map(item => {
        const c = objeto(item);
        return { porte: texto(c.porte) ?? "", observacoes: num(c.observacoes) ?? 0, afastamentoIncomumPct: num(c.afastamento_incomum_pct),
          alta: texto(c.alta) ?? "", critica: texto(c.critica) ?? "" };
      }),
      monitoramento: { avaliadas: num(mon.avaliadas) ?? 0, incomuns: num(mon.incomuns) ?? 0, taxaPct: num(mon.taxa_pct) } },
    notas: textos(o.notas), limitacoes: textos(o.limitacoes) };
}

/** A resposta de um território (com `detalhe`) nos tipos da tela. */
export function normalizarDetalhe(bruto: unknown): DetalheDoDetector {
  const o = objeto(bruto), t = objeto(o.territorio), jt = objeto(o.janela_do_territorio);
  return { id: texto(t.id) ?? "", rotulo: texto(t.rotulo) ?? "", tipo: texto(t.tipo) ?? "municipio", unidade: texto(t.unidade) ?? "",
    membros: textos(t.nomes_dos_membros), janela: janelaDe(o.janela), inicioDoTerritorio: texto(jt.inicio) ?? "",
    depoisDaQuebra: jt.depois_da_quebra === true, exploratorio: o.exploratorio === true, notas: textos(o.notas),
    serie: lista(o.serie).map(item => {
      const s = objeto(item);
      return { competencia: texto(s.competencia) ?? "", valor: num(s.valor), estado: texto(s.estado) ?? "", marca: texto(s.marca),
        membrosSemRegistro: num(s.membros_sem_registro) };
    }),
    historico: lista(o.historico).map(item => {
      const h = objeto(item), perda = h.perda ? objeto(h.perda) : null, pat = objeto(h.patamar), dec = h.declinio ? objeto(h.declinio) : null,
        des = h.desaceleracao ? objeto(h.desaceleracao) : null;
      return { competencia: texto(h.competencia) ?? "", valor: num(h.valor), estrutural: classe(h.estrutural),
        perda: perda && num(perda.delta) !== null ? { delta: num(perda.delta)!, pct: num(perda.pct), estado: texto(perda.estado) ?? "",
          classe: classe(perda.classe) } : null,
        patamar: { estado: texto(pat.estado) ?? "", classe: classe(pat.classe), diferencaPct: num(pat.diferenca_pct) },
        declinio: dec ? { reducoes: num(dec.reducoes), sinal: texto(dec.sinal) } : null,
        desaceleracao: des ? { desacelera: des.desacelera === true, rotulo: texto(des.rotulo) } : null };
    }),
    fenomenos: lista(o.fenomenos).map(item => {
      const f = objeto(item);
      return { chave: texto(f.chave) ?? "", numero: texto(f.numero) ?? "", nome: texto(f.nome) ?? "", dimensao: texto(f.dimensao) ?? "",
        estado: texto(f.estado) ?? "", classe: classe(f.classe), situacao: texto(f.situacao) ?? "", observado: texto(f.observado) ?? "",
        criterio: texto(f.criterio) ?? "", habitual: texto(f.habitual) ?? "", significa: texto(f.significa) ?? "",
        naoSignifica: texto(f.nao_significa) ?? "", limitacoes: texto(f.limitacoes) ?? "", qualidade: texto(f.qualidade) ?? "" };
    }) };
}

// ------------------------------------------------------------------------------------------------ apresentação
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
/** "jun/2024". */
export const competenciaCurta = (c: string | null | undefined): string => c && /^\d{6}$/.test(c) ? MESES[Number(c.slice(4)) - 1] + "/" + c.slice(0, 4) : c ?? "";
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const umaCasa = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const formatarInteiro = (n: number) => inteiro.format(n);
export const formatarPct = (valor: number) => umaCasa.format(Math.abs(valor)) + "%";
export const medicos = (n: number) => inteiro.format(n) + (n === 1 ? " médico" : " médicos");
const comSinal = (n: number) => (n > 0 ? "+" : n < 0 ? "−" : "") + inteiro.format(Math.abs(n));

export type Trecho = { chave: string; texto: string; classe: ClasseDoSinal | null;
  /** O que fica ao lado da intensidade (ou no lugar dela): "sem alerta", "sem classificação: …", "descritivo". */
  apoio: string | null };

/** A condição estrutural da linha: quantos médicos, o peso de uma saída e a intensidade (quando há). */
export function trechoEstrutural(linha: LinhaDoDetector): Trecho {
  const e = linha.estrutural;
  if (e.estado === "ausencia_de_dado" || e.n === null) return { chave: "estrutural", texto: "Sem registro nesta data", classe: null, apoio: "ausência de dado, não é zero" };
  const quantos = e.n === 0 ? "Nenhum médico registrado" + (e.zeros && e.zeros > 1 ? " há " + e.zeros + " registros" : "") : medicos(e.n);
  const impacto = e.impactoPct !== null && e.n > 0 && e.n <= 20 ? " · a saída de 1 tira " + formatarPct(e.impactoPct) : "";
  if (e.estado === "nivel_sem_classificacao") return { chave: "estrutural", texto: quantos, classe: null, apoio: "sem classificação neste nível" };
  if (e.classe) return { chave: "estrutural", texto: quantos + impacto, classe: e.classe, apoio: e.mantida ? "mantida pelo registro anterior" : null };
  return { chave: "estrutural", texto: quantos, classe: null, apoio: "sem sinal por esta escala" };
}

const MOTIVOS_DA_PERDA: Record<string, string> = {
  magnitude_abaixo: "queda pequena para o porte, sem alerta",
  comum_para_o_porte: "queda comum para o porte, sem alerta",
  poucas_transicoes: "sem classificação: poucos municípios parecidos na base para dizer se esta queda é incomum",
  intervalo_irregular: "sem classificação: faltou um registro entre os dois, e não há com o que comparar",
};
/** A trajetória da linha: a perda no último registro, o afastamento do patamar e o declínio persistente (só o que há a dizer). */
export function trechosDaTrajetoria(linha: LinhaDoDetector): Trecho[] {
  const saida: Trecho[] = [];
  const p = linha.perda;
  if (p.delta !== null && p.delta < 0) {
    const fato = comSinal(p.delta) + (p.pct !== null ? " (−" + formatarPct(p.pct) + ")" : "") + " no último registro";
    const apoio = p.estado === "alerta" ? "alerta: queda grande e incomum para o porte" : p.estado === "descontinuidade_de_registro" ? "volta de um pico de registro, sem alerta"
      : p.estado === "nivel_sem_classificacao" ? "sem classificação neste nível" : MOTIVOS_DA_PERDA[p.motivo ?? ""] ?? "sem alerta";
    saida.push({ chave: "perda", texto: fato, classe: p.classe, apoio: apoio + (p.verificar === "queda" ? " · verificar registro" : "") });
  }
  const pa = linha.patamar;
  if (pa.abaixo && pa.diferencaPct !== null && pa.estado !== "descontinuidade_de_registro") saida.push({ chave: "patamar",
    texto: formatarPct(pa.diferencaPct) + " abaixo do patamar anterior", classe: pa.classe,
    apoio: pa.estado === "descritivo" ? "descritivo: patamar com poucos médicos" : pa.estado === "nivel_sem_classificacao" ? "sem classificação neste nível"
      : pa.critica === "nao_calibravel" ? "sem base para dizer se é muito incomum" : null });
  const d = linha.declinio;
  if ((d.reducoes ?? 0) >= 2 && d.perdaPct !== null) saida.push({ chave: "declinio",
    texto: "Queda em " + d.reducoes + " junhos seguidos (−" + formatarPct(d.perdaPct) + ")", classe: null,
    apoio: d.sinal === "muito_forte" ? "sinal observado muito forte" : d.sinal === "forte" ? "sinal observado forte" : "queda observada" });
  return saida;
}

/** O ritmo e a instabilidade da linha: sinais descritivos, sem intensidade. */
export function trechosDoRitmo(linha: LinhaDoDetector): Trecho[] {
  const saida: Trecho[] = [];
  if (linha.desaceleracao.desacelera) saida.push({ chave: "desaceleracao", texto: "Desaceleração do crescimento", classe: null,
    apoio: linha.desaceleracao.persistente ? "repetida (leitura exploratória)" : null });
  if (linha.instabilidade.indice !== null) saida.push({ chave: "instabilidade",
    texto: "Oscilação " + umaCasa.format(linha.instabilidade.indice) + "× a típica do porte", classe: null, apoio: null });
  return saida;
}

const NOMES_DO_REGISTRO: Record<string, string> = { pico_que_volta: "pico que volta", quebra_de_fonte: "quebra de fonte", salto: "salto",
  queda_grande: "queda grande" };
/** A qualidade do registro: normal, "verificar registro" ou descontinuidade de registro. */
export function textoDoRegistro(linha: LinhaDoDetector): { texto: string; marca: "normal" | "verificar" | "descontinuidade" } {
  const tipos = linha.registro.tipos.map(tipo => NOMES_DO_REGISTRO[tipo] ?? tipo).join(", ");
  if (linha.registro.estado === "descontinuidade_de_registro") return { texto: "Descontinuidade de registro" + (tipos ? " (" + tipos + ")" : ""), marca: "descontinuidade" };
  if (linha.registro.estado === "verificar_registro") return { texto: "Verificar registro" + (tipos ? " (" + tipos + ")" : ""), marca: "verificar" };
  return { texto: "Normal", marca: "normal" };
}

/** A última observação: "jun/2024 · 5 médicos"; sem registro na data, diz de quando é o último. */
export function textoDaUltima(linha: LinhaDoDetector, fim: string): string {
  if (!linha.ultima) return "Sem registro na janela";
  const valor = competenciaCurta(linha.ultima.competencia) + " · " + medicos(linha.ultima.valor);
  return linha.ultima.naData ? valor : valor + " (sem registro em " + competenciaCurta(fim) + ")";
}

/** O tipo do território, ao lado do nome: "(estado)", "conjunto · 3 territórios". */
export function tipoDoTerritorio(linha: LinhaDoDetector): string | null {
  return linha.tipo === "estado" ? "estado como unidade · fonte estadual" : linha.tipo === "conjunto"
    ? "conjunto · soma de " + (linha.membros ?? 0) + " territórios" : null;
}

// ------------------------------------------------------------------------------------------------ filtros e ordem
export const FILTROS_DE_FENOMENO: { chave: string; rotulo: string }[] = [
  { chave: "todos", rotulo: "Todos os fenômenos" },
  { chave: "estrutural", rotulo: "Poucos médicos (escala estrutural)" },
  { chave: "ausencia", rotulo: "Nenhum médico registrado" },
  { chave: "perda", rotulo: "Perda no último registro" },
  { chave: "alerta_perda", rotulo: "Perda com alerta" },
  { chave: "patamar", rotulo: "Abaixo do patamar anterior" },
  { chave: "declinio", rotulo: "Declínio em junhos seguidos" },
  { chave: "desaceleracao", rotulo: "Desaceleração do crescimento" },
  { chave: "registro", rotulo: "Registro a verificar ou com descontinuidade" },
];
export type FiltrosDoDetector = { fenomeno: string; porte: string; busca: string };
export const SEM_FILTROS: FiltrosDoDetector = { fenomeno: "todos", porte: "todos", busca: "" };
const semAcento = (valor: string) => valor.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** As linhas que passam nos filtros: o fenômeno (pelos sinais do motor), o porte (pela última contagem) e o nome. */
export function filtrarLinhas(linhas: LinhaDoDetector[], filtros: FiltrosDoDetector): LinhaDoDetector[] {
  const termo = semAcento(filtros.busca.trim());
  return linhas.filter(linha => (filtros.fenomeno === "todos" || linha.sinais.includes(filtros.fenomeno)) &&
    (filtros.porte === "todos" || (filtros.porte === "zero" ? linha.ultima?.valor === 0 : String(linha.porte) === filtros.porte)) &&
    (!termo || semAcento(linha.rotulo).includes(termo)));
}

export type OrdemDoDetector = "intensidade" | "nome" | "medicos";
const maiorGravidade = (linha: LinhaDoDetector) => Math.max(GRAVIDADE[linha.dimensoes.estrutural ?? ""] ?? 0, GRAVIDADE[linha.dimensoes.trajetoria ?? ""] ?? 0);
const somaDaGravidade = (linha: LinhaDoDetector) => (GRAVIDADE[linha.dimensoes.estrutural ?? ""] ?? 0) + (GRAVIDADE[linha.dimensoes.trajetoria ?? ""] ?? 0);
/** A ordem da tabela. "Intensidade": a maior intensidade primeiro (não é um índice geral: só ordena a lista), depois o nome. */
export function ordenarLinhas(linhas: LinhaDoDetector[], ordem: OrdemDoDetector): LinhaDoDetector[] {
  const nome = (a: LinhaDoDetector, b: LinhaDoDetector) => a.rotulo.localeCompare(b.rotulo, "pt-BR", { numeric: true });
  const copia = [...linhas];
  if (ordem === "nome") return copia.sort(nome);
  if (ordem === "medicos") return copia.sort((a, b) => (a.ultima?.valor ?? Infinity) - (b.ultima?.valor ?? Infinity) || nome(a, b));
  return copia.sort((a, b) => maiorGravidade(b) - maiorGravidade(a) || somaDaGravidade(b) - somaDaGravidade(a) || nome(a, b));
}

// ------------------------------------------------------------------------------------------------ parâmetros exploratórios
export const NOMES_DOS_PARAMETROS: Record<string, { grupo: string; campos: Record<string, string> }> = {
  estrutural: { grupo: "Poucos médicos (escala estrutural)", campos: { critica: "Crítica até (médicos)", alta: "Alta até (médicos)", atencao: "Atenção até (médicos)" } },
  perda: { grupo: "Perda entre dois registros", campos: { alta_minimo: "Alta: queda mínima (médicos)", alta_fracao: "Alta: queda mínima (% do número anterior)",
    critica_minimo: "Crítica: queda mínima (médicos)", critica_fracao: "Crítica: queda mínima (%)", alta_alfa: "Alta: incomum até (% das transições)",
    critica_alfa: "Crítica: muito incomum até (%)" } },
  patamar: { grupo: "Afastamento do patamar anterior", campos: { atencao: "Atenção: abaixo do patamar (%)", critica: "Crítica: abaixo do patamar (%)",
    minimo: "Patamar mínimo para classificar (médicos)", alta_alfa: "Alta: incomum até (% das avaliações)" } },
  declinio: { grupo: "Declínio em junhos seguidos", campos: { forte_perda: "Sinal forte: perda mínima (%)", muito_forte_perda: "Sinal muito forte: perda mínima (%)" } },
};
/** Só o que difere do padrão vai no pedido (a configuração exploratória). */
export function parametrosPersonalizados(padrao: ParametrosDoDetector, emEdicao: ParametrosDoDetector): ParametrosDoDetector | null {
  const saida: ParametrosDoDetector = {};
  for (const [grupo, campos] of Object.entries(emEdicao)) for (const [chave, valor] of Object.entries(campos))
    if (padrao[grupo]?.[chave] !== undefined && padrao[grupo][chave] !== valor) (saida[grupo] ??= {})[chave] = valor;
  return Object.keys(saida).length ? saida : null;
}

// ------------------------------------------------------------------------------------------------ exportações
const celula = (valor: unknown): string => {
  if (valor === null || valor === undefined) return "";
  const t = typeof valor === "number" ? String(valor).replace(".", ",") : String(valor);
  return /[";\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
};
const NOMES_DOS_TIPOS: Record<string, string> = { municipio: "município", estado: "estado como unidade", conjunto: "conjunto", brasil: "país" };
/** CSV da tabela (separador ";" e BOM, como as outras exportações): uma linha por território, com os valores do motor e a
 * rastreabilidade em cada linha (a janela, a versão da base e do método e se a configuração é exploratória). */
export function csvDoDetector(resposta: RespostaDoDetector, linhas: LinhaDoDetector[]): string {
  const colunas: [string, (linha: LinhaDoDetector) => unknown][] = [
    ["Identificador", l => l.id], ["Território", l => l.rotulo], ["Tipo", l => NOMES_DOS_TIPOS[l.tipo] ?? l.tipo], ["UF", l => l.uf],
    ["Janela: início", () => resposta.janela.inicio], ["Janela: fim", () => resposta.janela.fim],
    ["Última competência com registro", l => l.ultima?.competencia], ["Médicos", l => l.ultima?.valor],
    ["Faixa de porte", l => l.porte === null ? "" : ROTULOS_DOS_PORTES[l.porte]],
    ["Escala estrutural: intensidade", l => l.estrutural.classe ? NOMES_DAS_CLASSES[l.estrutural.classe] : ""],
    ["Escala estrutural: estado", l => l.estrutural.estado], ["Impacto da saída de um médico (%)", l => l.estrutural.impactoPct],
    ["Registros seguidos em zero", l => l.estrutural.zeros],
    ["Perda: de", l => l.perda.de], ["Perda: até", l => l.perda.ate], ["Variação no último registro (médicos)", l => l.perda.delta],
    ["Variação no último registro (%)", l => l.perda.pct], ["Perda: estado", l => l.perda.estado],
    ["Perda: intensidade", l => l.perda.classe ? NOMES_DAS_CLASSES[l.perda.classe] : ""], ["Perda: motivo sem alerta", l => l.perda.motivo],
    ["Patamar anterior (médicos)", l => l.patamar.patamar], ["Diferença para o patamar (%)", l => l.patamar.diferencaPct],
    ["Patamar: estado", l => l.patamar.estado], ["Patamar: intensidade", l => l.patamar.classe ? NOMES_DAS_CLASSES[l.patamar.classe] : ""],
    ["Declínio: reduções em junhos seguidos", l => l.declinio.reducoes], ["Declínio: perda (%)", l => l.declinio.perdaPct],
    ["Declínio: sinal observado", l => l.declinio.sinal], ["Classe da tendência nos 4 junhos", l => l.desaceleracao.rotulo],
    ["Desaceleração repetida (exploratória)", l => l.desaceleracao.persistente === null ? "" : l.desaceleracao.persistente ? "sim" : "não"],
    ["Índice de instabilidade", l => l.instabilidade.indice], ["Qualidade do registro", l => l.registro.estado],
    ["Marcas de registro", l => l.registro.tipos.join(" | ")],
    ["Configuração", () => resposta.exploratorio ? "personalizada (exploratória)" : "padrão (limites provisórios)"],
    ["Versão do método", () => resposta.versao], ["Versão da base", () => resposta.fonte.versao],
  ];
  const corpo = [colunas.map(([nome]) => celula(nome)).join(";"), ...linhas.map(linha => colunas.map(([, valor]) => celula(valor(linha))).join(";"))];
  return "﻿" + corpo.join("\r\n") + "\r\n";
}

/** O método em JSON: a fonte, a janela, os parâmetros (padrão e em uso), o que a comparação diz na data e as notas. */
export function metodoDoDetector(resposta: RespostaDoDetector): string {
  return JSON.stringify({ ferramenta: "Detector de Sinais Territoriais", versao_do_metodo: resposta.versao, fonte: resposta.fonte,
    janela: resposta.janela, parametros: resposta.parametros, comparacao_na_data: resposta.calibracao, notas: resposta.notas,
    limitacoes: resposta.limitacoes, referencia: "Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2.4, 4, 4.2 e 5" }, null, 2);
}
