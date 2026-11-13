// Modelo puro do Detector de Sinais Territoriais (comando V22, Eixo II; Docs/DETECTOR_DE_SINAIS.md): a leitura da resposta de
// POST /api/detector para os tipos da tela, os textos curtos da tabela, os filtros, a ordem e as exportações. Nada é calculado
// aqui: a contagem, a mudança, a comparação com territórios parecidos e a intensidade do sinal vêm do motor (backend/detector.py).
// A tela usa linguagem simples (decisão D-C de 10/11/2026): "sem classificação", com o motivo, no lugar de "não calibrado";
// "limite provisório", no lugar de "candidato"; os termos técnicos ficam nos detalhes e nas exportações. Sem importações em tempo
// de execução, para os testes Node lerem só este arquivo.
import type { PainelDominio, PainelItem, PainelMunicipios } from "./painelApi";

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
  /** Conjunto: os identificadores dos componentes (para o contorno no mapa). */
  idsDosMembros: string[];
  // Fenômenos 8 a 12 (etapa 5 do comando V22): o nível da data, a variação em 2 anos (quando a comparação é habilitada) e o sinal
  // observado, com limites provisórios e sem intensidade.
  disponibilidade: { estado: string; taxa: number | null; populacao: number | null; variacaoPct: number | null; sinal: string | null };
  posicao: { estado: string; percentil: number | null; universo: number | null; variacaoPp: number | null; sinal: string | null };
  defasagem: { estado: string; indice: number | null; variacaoPontos: number | null; sinal: string | null };
  contexto: { estado: string; distanciaKm: number | null; referencia: string | null; referenciaId: string | null; percentil: number | null };
  coexistencia: { estado: string; combinacoes: string[]; textos: string[]; repercussoes: number };
};
/** A janela de comparação dos fenômenos 8 a 10 e o critério do contexto geográfico (fenômeno 11), do motor. */
export type ComparacaoDoDetector = { de: string | null; ate: string | null; estado: string; minimoDeMedicos: number;
  contexto: { taxaMinima: number | null; taxaDoBrasil: number | null; pctDaTaxaDoBrasil: number | null; atendem: number; universo: number } };
/** As séries de um território para os gráficos dos fenômenos 8 e 10: a taxa, a taxa da referência e o índice, por competência. */
export type ComparativoDoTerritorio = { competencias: string[]; taxa: (number | null)[]; indice: (number | null)[];
  referencia: { rotulo: string; motivo: string | null; taxa: (number | null)[] } };
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
  comparacao: ComparacaoDoDetector;
  /** As coordenadas autorizadas do motor (id → [latitude, longitude]) para o mapa: os municípios da seleção e os de referência. */
  coordenadas: Record<string, [number, number]>;
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
  comparativo: ComparativoDoTerritorio | null; notas: string[]; exploratorio: boolean };

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
const numerosOuNulos = (valor: unknown): (number | null)[] => lista(valor).map(num);
function comparacaoDe(bruto: unknown): ComparacaoDoDetector {
  const c = objeto(bruto), x = objeto(c.contexto);
  return { de: texto(c.de), ate: texto(c.ate), estado: texto(c.estado) ?? "", minimoDeMedicos: num(c.minimo_de_medicos) ?? 20,
    contexto: { taxaMinima: num(x.taxa_minima), taxaDoBrasil: num(x.taxa_do_brasil), pctDaTaxaDoBrasil: num(x.pct_da_taxa_do_brasil),
      atendem: num(x.atendem) ?? 0, universo: num(x.universo) ?? 0 } };
}
function coordenadasDe(bruto: unknown): Record<string, [number, number]> {
  const saida: Record<string, [number, number]> = {};
  for (const [id, par] of Object.entries(objeto(bruto))) {
    const [lat, lon] = lista(par).map(num);
    if (lat !== null && lon !== null && lat !== undefined && lon !== undefined) saida[id] = [lat, lon];
  }
  return saida;
}
function linhaDe(bruto: unknown): LinhaDoDetector | null {
  const o = objeto(bruto);
  const id = texto(o.id), rotulo = texto(o.rotulo);
  if (!id || !rotulo) return null;
  const ultima = objeto(o.ultima), e = objeto(o.estrutural), pe = objeto(o.perda), pa = objeto(o.patamar), de = objeto(o.declinio),
    ds = objeto(o.desaceleracao), ins = objeto(o.instabilidade), reg = objeto(o.registro), dim = objeto(o.dimensoes),
    di = objeto(o.disponibilidade), po = objeto(o.posicao), df = objeto(o.defasagem), cx = objeto(o.contexto), co = objeto(o.coexistencia);
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
    registro: { estado: texto(reg.estado) ?? "normal", tipos: textos(reg.tipos) }, membros: num(o.membros),
    idsDosMembros: textos(o.ids_dos_membros),
    disponibilidade: { estado: texto(di.estado) ?? "", taxa: num(di.taxa), populacao: num(di.populacao), variacaoPct: num(di.variacao_pct),
      sinal: texto(di.sinal) },
    posicao: { estado: texto(po.estado) ?? "", percentil: num(po.percentil), universo: num(po.universo), variacaoPp: num(po.variacao_pp),
      sinal: texto(po.sinal) },
    defasagem: { estado: texto(df.estado) ?? "", indice: num(df.indice), variacaoPontos: num(df.variacao_pontos), sinal: texto(df.sinal) },
    contexto: { estado: texto(cx.estado) ?? "", distanciaKm: num(cx.distancia_km), referencia: texto(cx.referencia),
      referenciaId: texto(cx.referencia_id), percentil: num(cx.percentil) },
    coexistencia: { estado: texto(co.estado) ?? "", combinacoes: textos(co.combinacoes), textos: textos(co.textos),
      repercussoes: num(co.repercussoes) ?? 0 } };
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
    comparacao: comparacaoDe(o.comparacao), coordenadas: coordenadasDe(o.coordenadas),
    notas: textos(o.notas), limitacoes: textos(o.limitacoes) };
}

/** A resposta de um território (com `detalhe`) nos tipos da tela. */
export function normalizarDetalhe(bruto: unknown): DetalheDoDetector {
  const o = objeto(bruto), t = objeto(o.territorio), jt = objeto(o.janela_do_territorio), cp = objeto(o.comparativo), cr = objeto(cp.referencia);
  return { id: texto(t.id) ?? "", rotulo: texto(t.rotulo) ?? "", tipo: texto(t.tipo) ?? "municipio", unidade: texto(t.unidade) ?? "",
    comparativo: textos(cp.competencias).length ? { competencias: textos(cp.competencias), taxa: numerosOuNulos(cp.taxa),
      indice: numerosOuNulos(cp.indice), referencia: { rotulo: texto(cr.rotulo) ?? "", motivo: texto(cr.motivo), taxa: numerosOuNulos(cr.taxa) } } : null,
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
      : pa.critica === "nao_calibravel" ? "crítica: sem base para avaliar" : null });
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

const duasCasas = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const formatarTaxa = (valor: number) => duasCasas.format(valor);
const variacaoComSinal = (valor: number, sufixo: string) => {
  const arredondado = Math.round(Math.abs(valor) * 10) / 10;
  return (arredondado === 0 ? "" : valor > 0 ? "+" : "−") + umaCasa.format(arredondado) + sufixo;
};
// Na tabela, o nome curto do sinal; que ele é um sinal observado, com limite provisório e sem intensidade, está na legenda da
// tabela (TEXTO_SINAIS_RELATIVOS) e nos detalhes de cada fenômeno.
const SINAIS_RELATIVOS: Record<string, string> = { queda: "queda de posição", forte: "sinal forte", muito_forte: "sinal muito forte" };
export const TEXTO_SINAIS_RELATIVOS = "Na comparação relativa, “sinal forte”, “sinal muito forte” e “queda de posição” são sinais observados em 2 anos, " +
  "com limites provisórios e sem intensidade.";
const ESTADOS_RELATIVOS: Record<string, string> = { comparacao_nao_habilitada: "variação em 2 anos: comparação não habilitada",
  janela_insuficiente: "variação em 2 anos: janela insuficiente", descritivo: "descritivo: menos de 20 médicos no início da janela",
  nao_calculavel: "variação não calculável", referencia_invalida: "sem referência na mesma unidade" };
const apoioRelativo = (estado: string, sinal: string | null): string | null => sinal ? SINAIS_RELATIVOS[sinal] ?? null : ESTADOS_RELATIVOS[estado] ?? null;

/** A comparação relativa da linha (fenômenos 8, 9 e 10): a taxa por habitante, a posição e o índice ante a referência, com a
 * variação em 2 anos quando a comparação é habilitada. Sem intensidade: os limites são provisórios. */
export function trechosDaComparacao(linha: LinhaDoDetector): Trecho[] {
  const saida: (Trecho & { estado: string })[] = [];
  const d = linha.disponibilidade, p = linha.posicao, f = linha.defasagem;
  if (d.taxa !== null) saida.push({ chave: "disponibilidade", estado: d.estado, classe: null, apoio: apoioRelativo(d.estado, d.sinal),
    texto: formatarTaxa(d.taxa) + " por 1.000 hab." + (d.variacaoPct !== null ? " (" + variacaoComSinal(d.variacaoPct, "%") + " em 2 anos)" : "") });
  if (p.percentil !== null) saida.push({ chave: "posicao", estado: p.estado, classe: null, apoio: apoioRelativo(p.estado, p.sinal),
    texto: "Percentil " + Math.round(p.percentil) + (p.variacaoPp !== null ? " (" + variacaoComSinal(p.variacaoPp, " pontos") + ")" : "") });
  if (f.indice !== null) saida.push({ chave: "defasagem", estado: f.estado, classe: null, apoio: apoioRelativo(f.estado, f.sinal),
    texto: "Índice " + umaCasa.format(f.indice) + " ante a referência" + (f.variacaoPontos !== null ? " (" + variacaoComSinal(f.variacaoPontos, " pontos") + ")" : "") });
  // Quando nenhuma variação pôde ser calculada pelo mesmo motivo, o motivo aparece uma vez só, no fim.
  const motivos = new Set(saida.map(trecho => trecho.estado));
  if (saida.length > 1 && motivos.size === 1 && ["comparacao_nao_habilitada", "janela_insuficiente", "descritivo"].includes(saida[0].estado))
    saida.forEach((trecho, indice) => { if (indice < saida.length - 1) trecho.apoio = null; });
  return saida.map(({ estado: _estado, ...trecho }) => trecho);
}

/** O critério do contexto geográfico, para o cabeçalho da coluna: "município mais próximo com 2,36 médicos por 1.000 habitantes
 * ou mais". Sem a taxa do critério na data, não há o que dizer. */
export const criterioDoContexto = (taxaMinima: number | null): string | null =>
  taxaMinima === null ? null : "município mais próximo com " + formatarTaxa(taxaMinima) + " médicos por 1.000 habitantes ou mais";

/** O contexto geográfico da linha (fenômeno 11): a distância até o município mais próximo que atende ao critério. Só contexto.
 * Com a taxa do critério (`taxaMinima`), a célula diz o critério por extenso: "mais longe que 99% dos municípios abaixo de 2,36
 * médicos por 1.000 habitantes". */
export function trechoDoContexto(linha: LinhaDoDetector, taxaMinima: number | null = null): Trecho {
  const c = linha.contexto;
  const criterio = taxaMinima === null ? null : formatarTaxa(taxaMinima) + " médicos por 1.000 habitantes";
  if (c.estado === "contexto" && c.distanciaKm !== null) return { chave: "contexto", classe: null,
    texto: "A " + umaCasa.format(c.distanciaKm) + " km de " + (c.referencia ?? "um município que atende ao critério"),
    apoio: c.percentil !== null
      ? "mais longe que " + Math.round(c.percentil) + "% dos municípios " + (criterio ? "abaixo de " + criterio : "que não atendem ao critério")
      : linha.tipo === "conjunto" ? "pelo componente mais próximo" : null };
  if (c.estado === "atende_ao_criterio") return { chave: "contexto", texto: "Atende ao critério", classe: null,
    apoio: criterio ? "taxa de " + criterio + " ou mais" : "taxa igual ou maior que a do critério" };
  if (c.estado === "nao_aplicavel") return { chave: "contexto", texto: "Não se aplica", classe: null, apoio: "o estado como unidade não tem um ponto único" };
  if (c.estado === "sem_coordenada") return { chave: "contexto", texto: "Sem coordenada válida", classe: null, apoio: null };
  return { chave: "contexto", texto: "Não calculável", classe: null, apoio: null };
}

/** Os sinais combinados da linha (fenômeno 12): as combinações pré-definidas, sem índice geral. */
export function trechosCombinados(linha: LinhaDoDetector): Trecho[] {
  const textosDasCombinacoes = linha.coexistencia.textos;
  return textosDasCombinacoes.map((item, indice) => ({ chave: "coexistencia", texto: item, classe: null,
    apoio: indice === textosDasCombinacoes.length - 1 && linha.coexistencia.repercussoes > 1
      ? linha.coexistencia.repercussoes + " sinais vêm de quedas no número de médicos: contam como um evento" : null }));
}

// ------------------------------------------------------------------------------------------------ gráficos e mapa (etapa 5)
const SEM_VALORES = { populacao: null, quantidade: null, densidade: null };
/** As linhas com distância (fenômeno 11) como itens do gráfico de bolhas do Agente: X = a distância até o município mais próximo
 * que atende ao critério; Y = a taxa por 1.000 habitantes; tamanho = a população. Só os valores do motor. */
export function itensDoContexto(linhas: LinhaDoDetector[]): PainelItem[] {
  return linhas.filter(linha => linha.contexto.estado === "contexto" && linha.contexto.distanciaKm !== null && linha.disponibilidade.taxa !== null)
    .map(linha => ({ id: linha.id, tipo: linha.tipo, rotulo: linha.rotulo, uf: linha.uf, populacao: linha.disponibilidade.populacao,
      quantidade: linha.ultima?.valor ?? null, densidade: linha.disponibilidade.taxa, distancia_km: linha.contexto.distanciaKm,
      ...(linha.tipo === "conjunto" ? { membros: linha.idsDosMembros, contagem: "SOMA_DOS_COMPONENTES" } : {}),
      inicial: SEM_VALORES, variacao_percentual: SEM_VALORES, avaliavel: { densidade: true, distancia: true, variacao: null }, motivos: [],
      referencia: false, tendencia: null, grupo: null, grupoMapa: null, faixa: null, faixa_distancia: null,
      referenciaDoItem: linha.contexto.referenciaId ? [{ id: linha.contexto.referenciaId, rotulo: linha.contexto.referencia ?? "" }] : null,
      membroDaReferencia: null, condicoes: null, ordem: null, rotatividade: null, serie: null }));
}
/** Os domínios [mínimo, máximo] dos itens do gráfico de bolhas, como o motor os manda no painel. */
export function dominiosDoContexto(itens: PainelItem[]): Partial<Record<string, PainelDominio | null>> {
  const dominio = (valores: (number | null)[]): PainelDominio | null => {
    const validos = valores.filter((valor): valor is number => valor !== null && Number.isFinite(valor));
    return validos.length ? [Math.min(...validos), Math.max(...validos)] : null;
  };
  return { densidade: dominio(itens.map(item => item.densidade)), distancia_km: dominio(itens.map(item => item.distancia_km)),
    populacao: dominio(itens.map(item => item.populacao)), quantidade: dominio(itens.map(item => item.quantidade)) };
}
/** O que o mapa do Detector desenha: no fundo, os municípios da seleção com ponto; em destaque, os que têm o fenômeno do filtro (ou,
 * sem filtro, algum sinal combinado); os conjuntos, pelo contorno dos componentes; vazados, os municípios de referência do contexto
 * geográfico (o mais próximo que atende ao critério) dos territórios em destaque. */
export function camadasDoMapa(resposta: RespostaDoDetector, linhas: LinhaDoDetector[], fenomeno: string): { fundo: string[]; destaque: string[];
  conjuntos: { id: string; nome: string; membros: string[] }[]; referencias: string[]; sinal: string } {
  const comPonto = (id: string) => id in resposta.coordenadas;
  const sinal = fenomeno === "todos" ? "combinados" : fenomeno;
  const marcadas = linhas.filter(linha => linha.sinais.includes(sinal));
  const municipios = (lista: LinhaDoDetector[]) => lista.filter(linha => linha.tipo === "municipio" && comPonto(linha.id)).map(linha => linha.id);
  const destaque = municipios(marcadas);
  const noDestaque = new Set(destaque);
  return { fundo: municipios(linhas).filter(id => !noDestaque.has(id)), destaque, sinal,
    conjuntos: linhas.filter(linha => linha.tipo === "conjunto" && linha.idsDosMembros.some(comPonto))
      .map(linha => ({ id: linha.id, nome: linha.rotulo, membros: linha.idsDosMembros.filter(comPonto) })),
    referencias: [...new Set(marcadas.map(linha => linha.contexto.referenciaId).filter((id): id is string => !!id && comPonto(id) && !noDestaque.has(id)))] };
}
/** A série da taxa de um território e a da referência dele, para a Série temporal do Agente (fenômenos 8 e 10). */
export function seriesDoComparativo(detalhe: DetalheDoDetector): { item: PainelItem; referencias: { id: string; rotulo: string;
  observacoes: { competencia: string; valor: number | null }[] }[] } | null {
  const c = detalhe.comparativo;
  if (!c || !c.taxa.some(valor => valor !== null)) return null;
  const observacoes = (valores: (number | null)[]) => c.competencias.map((competencia, indice) => ({ competencia, valor: valores[indice] ?? null }));
  const ultima = [...c.taxa].reverse().find(valor => valor !== null) ?? null;
  const item = { id: detalhe.id, tipo: detalhe.tipo, rotulo: detalhe.rotulo, uf: null, populacao: null, quantidade: null, densidade: ultima,
    distancia_km: null, inicial: SEM_VALORES, variacao_percentual: SEM_VALORES, avaliavel: { densidade: true, distancia: null, variacao: null },
    motivos: [], referencia: false, tendencia: null, grupo: null, grupoMapa: null, faixa: null, faixa_distancia: null, referenciaDoItem: null,
    membroDaReferencia: null, condicoes: null, ordem: null, rotatividade: null,
    serie: { observacoes: observacoes(c.taxa), comparavel: true, motivo: null } } as PainelItem;
  // No desenho, o rótulo curto da referência ("demais municípios do Amazonas"); o completo fica na legenda do gráfico.
  return { item, referencias: c.referencia.taxa.some(valor => valor !== null)
    ? [{ id: "referencia", rotulo: "Referência: " + c.referencia.rotulo.replace(/\s*\(.*$/, ""), observacoes: observacoes(c.referencia.taxa) }] : [] };
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
  { chave: "disponibilidade", rotulo: "Queda da taxa por habitante (2 anos)" },
  { chave: "posicao", rotulo: "Queda da posição relativa (2 anos)" },
  { chave: "defasagem", rotulo: "Defasagem ante a referência (2 anos)" },
  { chave: "combinados", rotulo: "Sinais combinados" },
];
/** O que o Detector leva ao Simulador de Cenários (o contexto analítico preservado): o território, a data avaliada, a janela em uso
 * (quando a pessoa a escolheu; a janela padrão do Detector, a série inteira, não é levada), os sinais à vista, pelos nomes dos
 * filtros, e se os parâmetros eram personalizados (exploratórios). */
export type AlvoDoSimulador = { id: string; tipo: LinhaDoDetector["tipo"]; rotulo: string; sinais: string[]; fim: string;
  janela: { inicio: string; fim: string } | null; exploratorio: boolean };
export function alvoDoSimulador(linha: LinhaDoDetector, resposta: Pick<RespostaDoDetector, "janela" | "exploratorio">): AlvoDoSimulador {
  const rotulos = new Map(FILTROS_DE_FENOMENO.map(item => [item.chave, item.rotulo]));
  return { id: linha.id, tipo: linha.tipo, rotulo: linha.rotulo, sinais: linha.sinais.map(sinal => rotulos.get(sinal) ?? sinal), fim: resposta.janela.fim,
    janela: resposta.janela.padrao ? null : { inicio: resposta.janela.inicio, fim: resposta.janela.fim }, exploratorio: resposta.exploratorio };
}
/** O patamar anterior que "Simular recuperação" leva ao Simulador como meta hipotética: só quando o território está abaixo dele
 * (acima do patamar, não há o que recuperar). */
export const patamarARecuperar = (linha: LinhaDoDetector): number | null =>
  linha.patamar.patamar !== null && linha.patamar.diferencaPct !== null && linha.patamar.diferencaPct < 0 ? linha.patamar.patamar : null;
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
  disponibilidade: { grupo: "Taxa por habitante (em 2 anos)", campos: { forte: "Sinal forte: queda mínima da taxa (%)",
    muito_forte: "Sinal muito forte: queda mínima da taxa (%)" } },
  posicao: { grupo: "Posição relativa (em 2 anos)", campos: { queda: "Queda de posição: mínimo (pontos de percentil)",
    forte: "Sinal forte: queda mínima (pontos de percentil)", muito_forte: "Sinal muito forte: queda mínima (pontos de percentil)" } },
  defasagem: { grupo: "Defasagem ante a referência (em 2 anos)", campos: { forte: "Sinal forte: queda mínima do índice (pontos)",
    muito_forte: "Sinal muito forte: queda mínima do índice (pontos)" } },
  contexto: { grupo: "Contexto geográfico", campos: { taxa_do_brasil_pct: "Critério: taxa mínima do município mais próximo (% da taxa do Brasil)" } },
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
    ["Janela de comparação: de", () => resposta.comparacao.de], ["Janela de comparação: até", () => resposta.comparacao.ate],
    ["Janela de comparação: estado", () => resposta.comparacao.estado],
    ["Taxa por 1.000 habitantes", l => l.disponibilidade.taxa], ["População", l => l.disponibilidade.populacao],
    ["Variação da taxa em 2 anos (%)", l => l.disponibilidade.variacaoPct], ["Taxa: estado", l => l.disponibilidade.estado],
    ["Taxa: sinal observado", l => l.disponibilidade.sinal],
    ["Percentil da taxa", l => l.posicao.percentil], ["Universo do percentil", l => l.posicao.universo],
    ["Variação do percentil em 2 anos (pontos)", l => l.posicao.variacaoPp], ["Posição: estado", l => l.posicao.estado],
    ["Posição: sinal observado", l => l.posicao.sinal],
    ["Índice ante a referência", l => l.defasagem.indice], ["Variação do índice em 2 anos (pontos)", l => l.defasagem.variacaoPontos],
    ["Defasagem: estado", l => l.defasagem.estado], ["Defasagem: sinal observado", l => l.defasagem.sinal],
    ["Distância ao município mais próximo que atende ao critério (km)", l => l.contexto.distanciaKm],
    ["Município mais próximo que atende ao critério", l => l.contexto.referencia], ["Percentil da distância", l => l.contexto.percentil],
    ["Contexto geográfico: estado", l => l.contexto.estado], ["Critério do contexto: taxa mínima", () => resposta.comparacao.contexto.taxaMinima],
    ["Sinais combinados", l => l.coexistencia.textos.join(" | ")],
    ["Configuração", () => resposta.exploratorio ? "personalizada (exploratória)" : "padrão (limites provisórios)"],
    ["Versão do método", () => resposta.versao], ["Versão da base", () => resposta.fonte.versao],
  ];
  const corpo = [colunas.map(([nome]) => celula(nome)).join(";"), ...linhas.map(linha => colunas.map(([, valor]) => celula(valor(linha))).join(";"))];
  return "﻿" + corpo.join("\r\n") + "\r\n";
}

/** O método em JSON: a fonte, a janela, os parâmetros (padrão e em uso), o que a comparação diz na data e as notas. */
export function metodoDoDetector(resposta: RespostaDoDetector): string {
  return JSON.stringify({ ferramenta: "Detector de Sinais Territoriais", versao_do_metodo: resposta.versao, fonte: resposta.fonte,
    janela: resposta.janela, parametros: resposta.parametros, comparacao_na_data: resposta.calibracao,
    comparacao_relativa: resposta.comparacao, notas: resposta.notas,
    limitacoes: resposta.limitacoes, referencia: "Docs/DETECTOR_E_SIMULADOR_V2_2.md, seções 2.4, 4, 4.1, 4.2 e 5" }, null, 2);
}
