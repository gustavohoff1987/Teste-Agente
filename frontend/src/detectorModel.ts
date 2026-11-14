// Modelo puro do Detector de Sinais (comando V23, Proposta V3, Parte B; Docs/DETECTOR_DE_SINAIS.md): a leitura da resposta de
// POST /api/detector para os tipos da tela, os textos curtos da lista, os filtros, a ordem, os critérios em frases e as exportações.
// Nada é calculado aqui: a contagem, a mudança, a comparação com territórios do mesmo porte, o nível de cada sinal e o alerta do
// território (um nível só, o maior entre os sinais) vêm do motor (backend/detector.py). Os níveis são moderado, elevado e
// crítico, sempre com o tipo de critério ("comparado com a base" ou "por convenção"); quando a base não tem comparações bastantes,
// a tela diz "sem comparações suficientes", com os números. Os nomes ("médicos", "estado") vêm da base (`fonte.rotulos`). Sem
// importações em tempo de execução, para os testes Node lerem só este arquivo.
import type { PainelDominio, PainelItem, PainelMunicipios } from "./painelApi";

export type NivelDoAlerta = "moderado" | "elevado" | "critico";
/** O nome antigo do tipo, ainda usado pela tela. */
export type ClasseDoSinal = NivelDoAlerta;
/** Do mais grave ao menos grave. */
export const NIVEIS: NivelDoAlerta[] = ["critico", "elevado", "moderado"];
export const NOMES_DOS_NIVEIS: Record<NivelDoAlerta, string> = { moderado: "Moderado", elevado: "Elevado", critico: "Crítico" };
export const GRAVIDADE: Record<string, number> = { critico: 3, elevado: 2, moderado: 1 };
/** As cores dos níveis no desenho (mapa e gráfico): amarelo, laranja e vermelho (seção B.1), nos passos de estado da skill de
 * visualização (aviso, sério e crítico), os mesmos nos dois esquemas de cor. O amarelo e o laranja ficam abaixo de 3:1 na
 * superfície clara, de propósito: o nível vem sempre escrito (legenda, dica e lista), nunca só pela cor, e o ponto leva um anel. */
export const CORES_DOS_NIVEIS: Record<NivelDoAlerta, string> = { moderado: "#fab219", elevado: "#ec835a", critico: "#d03b3b" };
/** O estado do alerta de um território: um dos três níveis, "sem alerta", "sem comparações suficientes" ou "sem nível" (conjunto). */
export type EstadoDoAlerta = NivelDoAlerta | "sem_alerta" | "sem_comparacoes" | "sem_nivel";
export const ESTADOS_DO_ALERTA: EstadoDoAlerta[] = ["critico", "elevado", "moderado", "sem_alerta", "sem_comparacoes", "sem_nivel"];
/** Os nomes da base (seção A.2.6): na base do Brasil, "médicos", "estado" e "Brasil"; numa planilha, os dela. */
export type RotulosDaBase = { profissional: string; profissionais: string; unidade: string; unidades: string; grupo: string; grupos: string; todo: string;
  /** As formas com artigo que o motor manda (`fonte.formas`), para a concordância: "o município", "a área". Sem elas, o masculino. */
  oUnidade?: string; oGrupo?: string };
export const ROTULOS_DO_BRASIL: RotulosDaBase = { profissional: "médico", profissionais: "médicos", unidade: "município", unidades: "municípios",
  grupo: "estado", grupos: "estados", todo: "Brasil" };

/** A seleção que as ferramentas recebem: o mesmo contrato do painel (os municípios, os estados como unidade e os conjuntos). */
export type SelecaoDasFerramentas = { base?: { municipios: PainelMunicipios }; estados_unidade?: string[];
  conjuntos?: { id: string; rotulo: string; membros: string[]; versao?: number }[] };
export type JanelaDoDetector = { inicio: string; fim: string; registros: number; meses: number; padrao: boolean;
  ultimoRegistroDaBase: string; eOUltimo: boolean };
export type ParametrosDoDetector = Record<string, Record<string, number>>;
/** O que o pedido das ferramentas diz de uma planilha enviada, como no pedido do painel: os nomes (painel "Colunas"), as
 * premissas confirmadas e a categoria. Na base do Brasil, nada disso vai. */
export type OpcoesDaBase = { rotulos?: unknown; premissas?: unknown; categoria?: string };
export type OpcoesDoDetector = SelecaoDasFerramentas & OpcoesDaBase & { janela?: { inicio?: string; fim?: string }; parametros?: ParametrosDoDetector;
  detalhe?: string };

export type SinalComNivel = { sinal: string; nivel: NivelDoAlerta; criterio: string };
/** O alerta do território: um nível só (o maior entre os sinais, sem soma nem índice), o tipo de critério e o porquê. */
export type AlertaDoTerritorio = { estado: "alerta" | "sem_alerta" | "sem_comparacoes" | "sem_nivel"; nivel: NivelDoAlerta | null;
  sinal: string | null; criterio: string | null; outros: number; porQue: string | null; sinais: SinalComNivel[];
  /** Os sinais que vêm da mesma queda: contam como um evento. */
  mesmaQueda: string[];
  /** Os sinais comparados com a base que ficaram sem comparações suficientes. */
  semComparacoes: string[]; motivo: string | null };
export type LinhaDoDetector = {
  id: string; tipo: "municipio" | "estado" | "conjunto" | "brasil"; nivel: string; rotulo: string; uf: string | null;
  /** Base Brasil: os nomes anteriores do município (13/11/2026), só para a busca por nome; o que aparece é o nome atual. */
  nomesAnteriores?: string[];
  ultima: { competencia: string; valor: number; naData: boolean } | null; porte: number | null; sinais: string[];
  alerta: AlertaDoTerritorio;
  estrutural: { estado: string; classe: NivelDoAlerta | null; n: number | null; impactoPct: number | null; zeros: number | null; mantida: boolean };
  perda: { estado: string; classe: NivelDoAlerta | null; delta: number | null; pct: number | null; de: string | null; ate: string | null;
    magnitude: string | null; motivo: string | null; verificar: string | null };
  patamar: { estado: string; classe: NivelDoAlerta | null; patamar: number | null; diferencaPct: number | null; abaixo: boolean };
  declinio: { estado: string; classe: NivelDoAlerta | null; reducoes: number | null; perdaPct: number | null };
  desaceleracao: { estado: string; classe: NivelDoAlerta | null; desacelera: boolean; persistente: boolean | null; anos: number | null;
    rotulo: string | null };
  instabilidade: { estado: string; classe: NivelDoAlerta | null; indice: number | null };
  registro: { estado: string; tipos: string[] };
  membros: number | null;
  /** Conjunto: os identificadores dos componentes (para o contorno no mapa). */
  idsDosMembros: string[];
  // Sinais 8 a 12: o valor da data, a variação em 2 anos (quando a população é comparável) e o nível, pela raridade na base.
  disponibilidade: { estado: string; classe: NivelDoAlerta | null; taxa: number | null; populacao: number | null; variacaoPct: number | null };
  posicao: { estado: string; classe: NivelDoAlerta | null; percentil: number | null; universo: number | null; variacaoPp: number | null };
  defasagem: { estado: string; classe: NivelDoAlerta | null; indice: number | null; variacaoPontos: number | null };
  contexto: { estado: string; distanciaKm: number | null; referencia: string | null; referenciaId: string | null; percentil: number | null };
  coexistencia: { estado: string; combinacoes: string[]; textos: string[]; repercussoes: number };
};
/** A janela de comparação dos sinais 8 a 10 e o critério da distância (sinal 11), do motor. */
export type ComparacaoDoDetector = { de: string | null; ate: string | null; estado: string; minimoDeMedicos: number;
  /** Os trechos de população comparável da base, lidos dela mesma ([[2014, 2024]]), e o motivo quando a janela não cabe num deles. */
  trechos: [number, number][]; motivo: string | null;
  contexto: { taxaMinima: number | null; taxaDoBrasil: number | null; pctDaTaxaDoBrasil: number | null; atendem: number; universo: number } };
/** As séries de um território para os gráficos dos sinais 8 e 10: a taxa, a taxa da referência e o índice, por competência. */
export type ComparativoDoTerritorio = { competencias: string[]; taxa: (number | null)[]; indice: (number | null)[]; trechos: [number, number][];
  referencia: { rotulo: string; motivo: string | null; taxa: (number | null)[] } };
/** A régua de uma data, por faixa de porte: quantas comparações anteriores há e, em cada nível, o "1 em cada N", quantas ele pede
 * e a partir de que mudança ela é rara (null: sem comparações suficientes). */
export type CorteDaRegua = { umEm: number; pede: number; cortePct: number | null };
export type FaixaDaRegua = { porte: string; comparacoes: number; niveis: Partial<Record<NivelDoAlerta, CorteDaRegua>> };
export type ReguaDaData = { competencia: string; intervaloMeses: number | null; perda: FaixaDaRegua[]; patamar: FaixaDaRegua[];
  monitoramento: { avaliadas: number; raras: number; taxaPct: number | null; esperadoPct: number | null; avisoDaBase: boolean } };
export type TextoDoEntenda = { texto: string; exemplo: string };
export type RespostaDoDetector = {
  versao: string; fonte: { base: string; categoria: string; versao: string; primeira: string; ultima: string; competencias: number;
    rotulos: RotulosDaBase; unidades: Record<string, string>;
    /** De onde vem a base ("brasil" ou "planilha") e o que ela tem: sem coordenadas, não há mapa; sem população, não há gráfico. */
    origem: "brasil" | "planilha"; tem: { populacao: boolean; coordenadas: boolean; grupo: boolean; serieAnual: boolean } };
  janela: JanelaDoDetector; competencias: string[];
  parametros: { padrao: ParametrosDoDetector; emUso: ParametrosDoDetector; personalizados: boolean;
    editaveis: Record<string, Record<string, { minimo: number; maximo: number; inteiro: boolean }>> };
  exploratorio: boolean; linhas: LinhaDoDetector[];
  /** Os níveis (o "1 em cada N" e as comparações que cada um pede), os grupos dos sinais e os rótulos das faixas de porte. */
  niveis: { chave: NivelDoAlerta; nome: string; umEm: number; pede: number }[];
  grupos: { chave: string; nome: string; sinais: string[] }[]; portes: string[];
  /** Os "Entenda" da primeira tela: da ferramenta, do alerta e dos termos (porte, patamar, percentil, 1 em cada N). */
  entenda: Record<string, TextoDoEntenda>;
  resumo: { territorios: number; porTipo: Record<string, number>; niveis: Record<string, number>; comNivel: Record<string, number>;
    sinais: Record<string, number>; semRegistroNaData: number };
  calibracao: ReguaDaData;
  /** A régua própria dos estados como unidade (a base dos estados), quando a seleção tem algum. */
  calibracaoDosEstados: ReguaDaData | null;
  /** O aviso da base: numa mesma data, as quedas raras passam do triplo do esperado. */
  avisoDaBase: string | null;
  comparacao: ComparacaoDoDetector;
  /** As coordenadas autorizadas do motor (id → [latitude, longitude]) para o mapa: os municípios da seleção e os de referência. */
  coordenadas: Record<string, [number, number]>;
  /** Os sinais que esta base não sustenta (sinal → motivo): sem população, sem coordenadas, sem grupo de cima ou sem série anual. */
  indisponiveis: Record<string, string>;
  notas: string[]; limitacoes: string[];
};
/** O perfil da base (seção A.3): o que o Agente leu dela e o resumo "com esta base, dá para… / não dá para… (motivo)". */
export type PerfilDaBase = { origem: "brasil" | "planilha"; base: string; categoria: string; territorios: number; registros: number;
  primeira: string; ultima: string; itens: { chave: string; titulo: string; lido: string; falta: string | null }[];
  daPara: string[]; naoDaPara: { oQue: string; motivo: string }[]; avisos: string[] };
export type PontoDaSerie = { competencia: string; valor: number | null; estado: string; marca: string | null; membrosSemRegistro: number | null };
export type PassoDoHistorico = { competencia: string; valor: number | null; alerta: NivelDoAlerta | null; estrutural: NivelDoAlerta | null;
  perda: { delta: number; pct: number | null; estado: string; classe: NivelDoAlerta | null } | null;
  patamar: { estado: string; classe: NivelDoAlerta | null; diferencaPct: number | null }; instabilidade: NivelDoAlerta | null;
  declinio: { reducoes: number | null; classe: NivelDoAlerta | null } | null;
  desaceleracao: { desacelera: boolean; classe: NivelDoAlerta | null; rotulo: string | null } | null };
/** Um sinal no detalhe do território: o nível, uma frase, o "Entenda" e a explicação completa (os sete campos). */
export type FenomenoDoDetalhe = { chave: string; numero: string; nome: string; grupo: string; dimensao: string;
  nivel: NivelDoAlerta | null; estadoDoNivel: string; criterioDoNivel: string | null; exploratorio: boolean;
  situacao: string; entenda: TextoDoEntenda;
  /** Os níveis que a base ainda não sustenta neste sinal: "Sem comparações suficientes para o crítico: há 203, e ele pede 999." */
  semComparacoes: { niveis: string[]; comparacoes: number; pede: number; texto: string } | null;
  observado: string; criterio: string; habitual: string; significa: string; naoSignifica: string; limitacoes: string; qualidade: string };
export type DetalheDoDetector = { id: string; rotulo: string; tipo: string; unidade: string; membros: string[]; janela: JanelaDoDetector;
  inicioDoTerritorio: string; depoisDaQuebra: boolean; serie: PontoDaSerie[]; historico: PassoDoHistorico[]; fenomenos: FenomenoDoDetalhe[];
  linha: LinhaDoDetector | null; comparativo: ComparativoDoTerritorio | null; notas: string[]; exploratorio: boolean };

// ------------------------------------------------------------------------------------------------ leitura da resposta
const objeto = (valor: unknown): Record<string, unknown> => valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : {};
const lista = (valor: unknown): unknown[] => Array.isArray(valor) ? valor : [];
const texto = (valor: unknown): string | null => typeof valor === "string" && valor ? valor : null;
const num = (valor: unknown): number | null => typeof valor === "number" && Number.isFinite(valor) ? valor : null;
const nivel = (valor: unknown): NivelDoAlerta | null => valor === "moderado" || valor === "elevado" || valor === "critico" ? valor : null;
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
const trechosDe = (bruto: unknown): [number, number][] =>
  lista(bruto).map(par => lista(par).map(num)).filter((par): par is [number, number] => par.length === 2 && par.every(ano => ano !== null));
function comparacaoDe(bruto: unknown): ComparacaoDoDetector {
  const c = objeto(bruto), x = objeto(c.contexto);
  return { de: texto(c.de), ate: texto(c.ate), estado: texto(c.estado) ?? "", minimoDeMedicos: num(c.minimo_de_medicos) ?? 20,
    trechos: trechosDe(c.trechos), motivo: texto(c.motivo),
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
function rotulosDe(bruto: unknown, formas?: unknown): RotulosDaBase {
  const r = objeto(bruto), f = objeto(formas);
  return { ...Object.fromEntries(Object.entries(ROTULOS_DO_BRASIL).map(([chave, padrao]) => [chave, texto(r[chave]) ?? padrao])) as RotulosDaBase,
    ...(texto(f.o_unidade) ? { oUnidade: texto(f.o_unidade)! } : {}), ...(texto(f.o_grupo) ? { oGrupo: texto(f.o_grupo)! } : {}) };
}
function alertaDe(bruto: unknown): AlertaDoTerritorio {
  const a = objeto(bruto);
  const estado = a.estado === "alerta" || a.estado === "sem_comparacoes" || a.estado === "sem_nivel" ? a.estado : "sem_alerta";
  return { estado, nivel: nivel(a.nivel), sinal: texto(a.sinal), criterio: texto(a.criterio), outros: num(a.outros) ?? 0, porQue: texto(a.por_que),
    sinais: lista(a.sinais).map(item => { const s = objeto(item); return { sinal: texto(s.sinal) ?? "", nivel: nivel(s.nivel), criterio: texto(s.criterio) ?? "" }; })
      .filter((item): item is SinalComNivel => !!item.sinal && item.nivel !== null),
    mesmaQueda: textos(a.mesma_queda), semComparacoes: textos(a.sem_comparacoes), motivo: texto(a.motivo) };
}
function linhaDe(bruto: unknown): LinhaDoDetector | null {
  const o = objeto(bruto);
  const id = texto(o.id), rotulo = texto(o.rotulo);
  if (!id || !rotulo) return null;
  const ultima = objeto(o.ultima), e = objeto(o.estrutural), pe = objeto(o.perda), pa = objeto(o.patamar), de = objeto(o.declinio),
    ds = objeto(o.desaceleracao), ins = objeto(o.instabilidade), reg = objeto(o.registro),
    di = objeto(o.disponibilidade), po = objeto(o.posicao), df = objeto(o.defasagem), cx = objeto(o.contexto), co = objeto(o.coexistencia);
  const tipo = o.tipo === "estado" || o.tipo === "conjunto" || o.tipo === "brasil" ? o.tipo : "municipio";
  return { id, rotulo, tipo, nivel: texto(o.nivel) ?? "municipios", uf: texto(o.uf),
    ...(textos(o.nomes_anteriores).length ? { nomesAnteriores: textos(o.nomes_anteriores) } : {}),
    ultima: texto(ultima.competencia) && num(ultima.valor) !== null
      ? { competencia: texto(ultima.competencia)!, valor: num(ultima.valor)!, naData: ultima.na_data === true } : null,
    porte: num(o.porte), sinais: textos(o.sinais), alerta: alertaDe(o.alerta),
    estrutural: { estado: texto(e.estado) ?? "", classe: nivel(e.classe), n: num(e.n), impactoPct: num(e.impacto_pct), zeros: num(e.zeros),
      mantida: e.mantida === true },
    perda: { estado: texto(pe.estado) ?? "", classe: nivel(pe.classe), delta: num(pe.delta), pct: num(pe.pct), de: texto(pe.de),
      ate: texto(pe.ate), magnitude: texto(pe.magnitude), motivo: texto(pe.motivo), verificar: texto(pe.verificar) },
    patamar: { estado: texto(pa.estado) ?? "", classe: nivel(pa.classe), patamar: num(pa.patamar), diferencaPct: num(pa.diferenca_pct),
      abaixo: pa.abaixo === true },
    declinio: { estado: texto(de.estado) ?? "", classe: nivel(de.classe), reducoes: num(de.reducoes), perdaPct: num(de.perda_pct) },
    desaceleracao: { estado: texto(ds.estado) ?? "", classe: nivel(ds.classe), desacelera: ds.desacelera === true,
      persistente: typeof ds.persistente === "boolean" ? ds.persistente : null, anos: num(ds.anos), rotulo: texto(ds.rotulo) },
    instabilidade: { estado: texto(ins.estado) ?? "", classe: nivel(ins.classe), indice: num(ins.indice) },
    registro: { estado: texto(reg.estado) ?? "normal", tipos: textos(reg.tipos) }, membros: num(o.membros),
    idsDosMembros: textos(o.ids_dos_membros),
    disponibilidade: { estado: texto(di.estado) ?? "", classe: nivel(di.classe), taxa: num(di.taxa), populacao: num(di.populacao),
      variacaoPct: num(di.variacao_pct) },
    posicao: { estado: texto(po.estado) ?? "", classe: nivel(po.classe), percentil: num(po.percentil), universo: num(po.universo),
      variacaoPp: num(po.variacao_pp) },
    defasagem: { estado: texto(df.estado) ?? "", classe: nivel(df.classe), indice: num(df.indice), variacaoPontos: num(df.variacao_pontos) },
    contexto: { estado: texto(cx.estado) ?? "", distanciaKm: num(cx.distancia_km), referencia: texto(cx.referencia),
      referenciaId: texto(cx.referencia_id), percentil: num(cx.percentil) },
    coexistencia: { estado: texto(co.estado) ?? "", combinacoes: textos(co.combinacoes), textos: textos(co.textos),
      repercussoes: num(co.repercussoes) ?? 0 } };
}
function reguaDe(bruto: unknown): ReguaDaData {
  const cal = objeto(bruto), mon = objeto(cal.monitoramento);
  const faixas = (itens: unknown, campo: string): FaixaDaRegua[] => lista(itens).map(item => {
    const c = objeto(item);
    const niveis: FaixaDaRegua["niveis"] = {};
    for (const chave of NIVEIS) if (c[chave]) {
      const n = objeto(c[chave]);
      niveis[chave] = { umEm: num(n.um_em) ?? 0, pede: num(n.pede) ?? 0, cortePct: num(n[campo]) };
    }
    return { porte: texto(c.porte) ?? "", comparacoes: num(c.comparacoes) ?? 0, niveis };
  });
  return { competencia: texto(cal.competencia) ?? "", intervaloMeses: num(cal.intervalo_meses), perda: faixas(cal.perda, "queda_pct"),
    patamar: faixas(cal.patamar, "afastamento_pct"),
    monitoramento: { avaliadas: num(mon.avaliadas) ?? 0, raras: num(mon.raras) ?? 0, taxaPct: num(mon.taxa_pct), esperadoPct: num(mon.esperado_pct),
      avisoDaBase: mon.aviso_da_base === true } };
}
const entendaDe = (bruto: unknown): TextoDoEntenda => { const e = objeto(bruto); return { texto: texto(e.texto) ?? "", exemplo: texto(e.exemplo) ?? "" }; };

/** A resposta da lista de POST /api/detector nos tipos da tela. */
export function normalizarDetector(bruto: unknown): RespostaDoDetector {
  const o = objeto(bruto), fonte = objeto(o.fonte), p = objeto(o.parametros), resumo = objeto(o.resumo), tem = objeto(fonte.tem);
  const editaveis = Object.fromEntries(Object.entries(objeto(p.editaveis)).map(([grupo, chaves]) => [grupo,
    Object.fromEntries(Object.entries(objeto(chaves)).map(([chave, faixa]) => {
      const f = objeto(faixa);
      return [chave, { minimo: num(f.minimo) ?? 0, maximo: num(f.maximo) ?? 0, inteiro: f.inteiro === true }];
    }))]));
  return { versao: texto(o.versao) ?? "",
    fonte: { base: texto(fonte.base) ?? "", categoria: texto(fonte.categoria) ?? "", versao: texto(fonte.versao) ?? "",
      primeira: texto(fonte.primeira) ?? "", ultima: texto(fonte.ultima) ?? "", competencias: num(fonte.competencias) ?? 0,
      rotulos: rotulosDe(fonte.rotulos, fonte.formas),
      unidades: Object.fromEntries(Object.entries(objeto(fonte.unidades)).filter((par): par is [string, string] => typeof par[1] === "string")),
      // Uma resposta sem `tem` (a de antes do comando V23) é a da base do Brasil, que tem tudo.
      origem: fonte.origem === "planilha" ? "planilha" : "brasil",
      tem: { populacao: tem.populacao !== false, coordenadas: tem.coordenadas !== false, grupo: tem.grupo !== false, serieAnual: tem.serie_anual !== false } },
    janela: janelaDe(o.janela), competencias: textos(o.competencias),
    parametros: { padrao: parametrosDe(p.padrao), emUso: parametrosDe(p.em_uso), personalizados: p.personalizados === true, editaveis },
    exploratorio: o.exploratorio === true,
    linhas: lista(o.linhas).map(linhaDe).filter((linha): linha is LinhaDoDetector => !!linha),
    niveis: lista(o.niveis).map(item => { const n = objeto(item); return { chave: nivel(n.chave), nome: texto(n.nome) ?? "", umEm: num(n.um_em) ?? 0,
      pede: num(n.pede) ?? 0 }; }).filter((item): item is RespostaDoDetector["niveis"][number] => item.chave !== null),
    grupos: lista(o.grupos).map(item => { const g = objeto(item); return { chave: texto(g.chave) ?? "", nome: texto(g.nome) ?? "", sinais: textos(g.sinais) }; }),
    portes: textos(o.portes),
    entenda: Object.fromEntries(Object.entries(objeto(o.entenda)).map(([chave, valor]) => [chave, entendaDe(valor)])),
    resumo: { territorios: num(resumo.territorios) ?? 0, porTipo: numeros(resumo.por_tipo), niveis: numeros(resumo.niveis),
      comNivel: numeros(resumo.com_nivel), sinais: numeros(resumo.sinais), semRegistroNaData: num(resumo.sem_registro_na_data) ?? 0 },
    calibracao: reguaDe(o.calibracao), calibracaoDosEstados: o.calibracao_dos_estados ? reguaDe(o.calibracao_dos_estados) : null,
    avisoDaBase: texto(o.aviso_da_base),
    comparacao: comparacaoDe(o.comparacao), coordenadas: coordenadasDe(o.coordenadas),
    indisponiveis: Object.fromEntries(Object.entries(objeto(o.indisponiveis)).filter((par): par is [string, string] => typeof par[1] === "string")),
    notas: textos(o.notas), limitacoes: textos(o.limitacoes) };
}

/** O perfil da base, da resposta de POST /api/detector com `{"perfil": true}`; null quando a resposta não o traz. */
export function normalizarPerfil(bruto: unknown): PerfilDaBase | null {
  const perfil = objeto(objeto(bruto).perfil);
  if (!lista(perfil.itens).length) return null;
  return { origem: perfil.origem === "planilha" ? "planilha" : "brasil", base: texto(perfil.base) ?? "", categoria: texto(perfil.categoria) ?? "",
    territorios: num(perfil.territorios) ?? 0, registros: num(perfil.registros) ?? 0, primeira: texto(perfil.primeira) ?? "",
    ultima: texto(perfil.ultima) ?? "",
    itens: lista(perfil.itens).map(item => { const i = objeto(item); return { chave: texto(i.chave) ?? "", titulo: texto(i.titulo) ?? "",
      lido: texto(i.lido) ?? "", falta: texto(i.falta) }; }).filter(item => item.titulo && item.lido),
    daPara: textos(perfil.da_para),
    naoDaPara: lista(perfil.nao_da_para).map(item => { const n = objeto(item); return { oQue: texto(n.o_que) ?? "", motivo: texto(n.motivo) ?? "" }; })
      .filter(item => item.oQue),
    avisos: textos(perfil.avisos) };
}

/** A resposta de um território (com `detalhe`) nos tipos da tela. */
export function normalizarDetalhe(bruto: unknown): DetalheDoDetector {
  const o = objeto(bruto), t = objeto(o.territorio), jt = objeto(o.janela_do_territorio), cp = objeto(o.comparativo), cr = objeto(cp.referencia);
  return { id: texto(t.id) ?? "", rotulo: texto(t.rotulo) ?? "", tipo: texto(t.tipo) ?? "municipio", unidade: texto(t.unidade) ?? "",
    comparativo: textos(cp.competencias).length ? { competencias: textos(cp.competencias), taxa: numerosOuNulos(cp.taxa),
      indice: numerosOuNulos(cp.indice), trechos: trechosDe(cp.trechos), referencia: { rotulo: texto(cr.rotulo) ?? "", motivo: texto(cr.motivo), taxa: numerosOuNulos(cr.taxa) } } : null,
    membros: textos(t.nomes_dos_membros), janela: janelaDe(o.janela), inicioDoTerritorio: texto(jt.inicio) ?? "",
    depoisDaQuebra: jt.depois_da_quebra === true, exploratorio: o.exploratorio === true, notas: textos(o.notas), linha: linhaDe(o.linha),
    serie: lista(o.serie).map(item => {
      const s = objeto(item);
      return { competencia: texto(s.competencia) ?? "", valor: num(s.valor), estado: texto(s.estado) ?? "", marca: texto(s.marca),
        membrosSemRegistro: num(s.membros_sem_registro) };
    }),
    historico: lista(o.historico).map(item => {
      const h = objeto(item), perda = h.perda ? objeto(h.perda) : null, pat = objeto(h.patamar), dec = h.declinio ? objeto(h.declinio) : null,
        des = h.desaceleracao ? objeto(h.desaceleracao) : null;
      return { competencia: texto(h.competencia) ?? "", valor: num(h.valor), alerta: nivel(h.alerta), estrutural: nivel(h.estrutural),
        perda: perda && num(perda.delta) !== null ? { delta: num(perda.delta)!, pct: num(perda.pct), estado: texto(perda.estado) ?? "",
          classe: nivel(perda.classe) } : null,
        patamar: { estado: texto(pat.estado) ?? "", classe: nivel(pat.classe), diferencaPct: num(pat.diferenca_pct) },
        instabilidade: nivel(h.instabilidade),
        declinio: dec ? { reducoes: num(dec.reducoes), classe: nivel(dec.classe) } : null,
        desaceleracao: des ? { desacelera: des.desacelera === true, classe: nivel(des.classe), rotulo: texto(des.rotulo) } : null };
    }),
    fenomenos: lista(o.fenomenos).map(item => {
      const f = objeto(item), falta = f.sem_comparacoes ? objeto(f.sem_comparacoes) : null;
      return { chave: texto(f.chave) ?? "", numero: texto(f.numero) ?? "", nome: texto(f.nome) ?? "", grupo: texto(f.grupo) ?? "",
        dimensao: texto(f.dimensao) ?? "", nivel: nivel(f.nivel), estadoDoNivel: texto(f.estado_do_nivel) ?? "",
        criterioDoNivel: texto(f.criterio_do_nivel), exploratorio: f.exploratorio === true, situacao: texto(f.situacao) ?? "",
        entenda: entendaDe(f.entenda),
        semComparacoes: falta && texto(falta.texto) ? { niveis: textos(falta.niveis), comparacoes: num(falta.comparacoes) ?? 0, pede: num(falta.pede) ?? 0,
          texto: texto(falta.texto)! } : null,
        observado: texto(f.observado) ?? "", criterio: texto(f.criterio) ?? "", habitual: texto(f.habitual) ?? "", significa: texto(f.significa) ?? "",
        naoSignifica: texto(f.nao_significa) ?? "", limitacoes: texto(f.limitacoes) ?? "", qualidade: texto(f.qualidade) ?? "" };
    }) };
}

// ------------------------------------------------------------------------------------------------ apresentação
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
/** "jun/2024"; numa planilha com um registro por ano ("202400"), "2024". */
export const competenciaCurta = (c: string | null | undefined): string => !c || !/^\d{6}$/.test(c) ? c ?? ""
  : c.endsWith("00") ? c.slice(0, 4) : MESES[Number(c.slice(4)) - 1] + "/" + c.slice(0, 4);
const inteiro = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 0 });
const umaCasa = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
export const formatarInteiro = (n: number) => inteiro.format(n);
export const formatarPct = (valor: number) => umaCasa.format(Math.abs(valor)) + "%";
/** "5 médicos", "1 médico": com os nomes da base (sem eles, os da base do Brasil). */
export const profissionais = (n: number, r: RotulosDaBase = ROTULOS_DO_BRASIL) => inteiro.format(n) + " " + (n === 1 ? r.profissional : r.profissionais);
export const medicos = (n: number) => profissionais(n);
const duasCasas = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
export const formatarTaxa = (valor: number) => duasCasas.format(valor);
const maiuscula = (valor: string) => valor.charAt(0).toUpperCase() + valor.slice(1);

/** O nome curto de cada sinal, com os nomes da base: "Poucos médicos", "Queda recente", "Menos médicos por habitante". */
export function nomeDoSinal(chave: string, r: RotulosDaBase = ROTULOS_DO_BRASIL): string {
  const nomes: Record<string, string> = { estrutural: "Poucos " + r.profissionais, ausencia: "Nenhum " + r.profissional + " registrado",
    declinio: "Declínio persistente", desaceleracao: "Desaceleração", instabilidade: "Instabilidade", perda: "Queda recente",
    patamar: "Abaixo do que já teve", disponibilidade: "Menos " + r.profissionais + " por habitante", posicao: "Perda de posição",
    defasagem: "Mais longe da referência", contexto: "Distância", coexistencia: "Sinais juntos", registro: "Registro a verificar" };
  return nomes[chave] ?? chave;
}

/** O estado do alerta de uma linha: o nível, "sem_alerta", "sem_comparacoes" ou "sem_nivel". */
export const estadoDoAlerta = (linha: LinhaDoDetector): EstadoDoAlerta => linha.alerta.nivel ?? (linha.alerta.estado === "alerta" ? "sem_alerta" : linha.alerta.estado);
const NOMES_DOS_ESTADOS: Record<EstadoDoAlerta, [string, string]> = { critico: ["crítico", "críticos"], elevado: ["elevado", "elevados"],
  moderado: ["moderado", "moderados"], sem_alerta: ["sem alerta", "sem alerta"],
  sem_comparacoes: ["sem comparações suficientes", "sem comparações suficientes"], sem_nivel: ["sem nível (conjunto)", "sem nível (conjuntos)"] };
/** O resumo dos níveis no alto: "41 críticos", "1 elevado", "4.118 sem alerta", "1 sem nível (conjunto)". */
export const textoDaContagem = (estado: EstadoDoAlerta, n: number): string => inteiro.format(n) + " " + NOMES_DOS_ESTADOS[estado][n === 1 ? 0 : 1];
/** O nome do estado do alerta para o filtro "Nível" e a coluna "Alerta": "Crítico", "Sem alerta", "Sem comparações suficientes". */
export const nomeDoEstado = (estado: EstadoDoAlerta): string => estado === "sem_nivel" ? "Sem nível (conjunto)" : maiuscula(NOMES_DOS_ESTADOS[estado][0]);

/** A coluna "Alerta": o nível (sempre escrito) e o tipo de critério; sem nível, o que a base diz no lugar. */
export function textoDoAlerta(linha: LinhaDoDetector): { estado: EstadoDoAlerta; nivel: NivelDoAlerta | null; texto: string; criterio: string | null } {
  const estado = estadoDoAlerta(linha);
  return { estado, nivel: linha.alerta.nivel, texto: nomeDoEstado(estado), criterio: linha.alerta.nivel ? linha.alerta.criterio : null };
}
const listar = (itens: string[]) => itens.length <= 1 ? itens.join("") : itens.slice(0, -1).join(", ") + " e " + itens[itens.length - 1];
/** A coluna "Por quê": a frase do sinal principal (do motor), com quantos outros sinais têm nível; sem alerta, o que a base diz. */
export function textoDoPorQue(linha: LinhaDoDetector, r: RotulosDaBase = ROTULOS_DO_BRASIL): string {
  const a = linha.alerta;
  if (a.estado === "alerta") return a.porQue ?? nomeDoSinal(a.sinal ?? "", r);
  if (a.estado === "sem_nivel") return a.motivo ?? "Um conjunto não tem outros iguais para comparar.";
  const faltam = listar(a.semComparacoes.map(sinal => nomeDoSinal(sinal, r).toLowerCase()));
  if (a.estado === "sem_comparacoes") return "A base ainda não tem história para comparar" + (faltam ? ": " + faltam : "") + ".";
  if (!linha.ultima) return "Sem registro na janela.";
  return "Nenhum sinal com nível" + (faltam ? " (sem comparações suficientes em " + faltam + ")" : "") + ".";
}
/** Os sinais da mesma queda, por extenso: "Queda recente e abaixo do que já teve vêm da mesma queda: contam como um evento." */
export function textoDaMesmaQueda(linha: LinhaDoDetector, r: RotulosDaBase = ROTULOS_DO_BRASIL): string | null {
  const nomes = linha.alerta.mesmaQueda.map(sinal => nomeDoSinal(sinal, r).toLowerCase());
  return nomes.length > 1 ? maiuscula(listar(nomes)) + " vêm da mesma queda: contam como um evento." : null;
}

/** Os trechos de população comparável, por extenso: "de 2014 a 2024", "de 2014 a 2017 e de 2018 a 2021"; sem nenhum, "em nenhum
 * trecho desta base". */
export function textoDosTrechos(trechos: [number, number][]): string {
  const partes = trechos.map(([inicio, fim]) => "de " + inicio + " a " + fim);
  return !partes.length ? "em nenhum trecho desta base" : partes.length === 1 ? partes[0] : partes.slice(0, -1).join(", ") + " e " + partes[partes.length - 1];
}

/** O critério da distância (sinal 11), para a legenda do gráfico: "município mais próximo com 2,36 médicos por 1.000 habitantes ou
 * mais". Sem a taxa do critério na data, não há o que dizer. */
export const criterioDoContexto = (taxaMinima: number | null, r: RotulosDaBase = ROTULOS_DO_BRASIL): string | null =>
  taxaMinima === null ? null : maisProximo(r) + " com " + formatarTaxa(taxaMinima) + " " + r.profissionais + " por 1.000 habitantes ou mais";
/** O artigo da unidade da base ("o" município, "a" área), pelas formas que o motor manda; sem elas, o masculino. */
export const artigoDaUnidade = (r: RotulosDaBase = ROTULOS_DO_BRASIL): "o" | "a" => r.oUnidade?.startsWith("a ") ? "a" : "o";
/** "município mais próximo", "área mais próxima". */
export const maisProximo = (r: RotulosDaBase = ROTULOS_DO_BRASIL): string => r.unidade + (artigoDaUnidade(r) === "a" ? " mais próxima" : " mais próximo");

// ------------------------------------------------------------------------------------------------ gráfico e mapa
const SEM_VALORES = { populacao: null, quantidade: null, densidade: null };
/** As linhas com distância (sinal 11) como itens do gráfico de bolhas do Agente: X = a distância até o território mais próximo que
 * atende ao critério; Y = a taxa por 1.000 habitantes; tamanho = a população. Só os valores do motor. */
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
/** O nível que o mapa e o gráfico pintam num território: sem filtro de sinal, o do alerta (o maior entre os sinais); com o filtro,
 * o nível daquele sinal no território. */
export function nivelNoDesenho(linha: LinhaDoDetector, sinal: string): NivelDoAlerta | null {
  if (sinal === "todos" || sinal === "juntos" || sinal === "registro") return linha.alerta.nivel;
  return linha.alerta.sinais.find(item => item.sinal === sinal)?.nivel ?? null;
}
/** O que o mapa do Detector desenha: os municípios à vista com ponto, pintados pelo nível (os sem nível, no fundo); os conjuntos,
 * pelo contorno dos componentes; e o nome de cada grupo de cima (o estado, na base do Brasil) junto aos pontos dele. */
export function camadasDoMapa(resposta: RespostaDoDetector, linhas: LinhaDoDetector[], sinal: string): { fundo: string[];
  porNivel: Record<NivelDoAlerta, string[]>; conjuntos: { id: string; nome: string; membros: string[] }[];
  grupos: { id: string; nome: string; membros: string[] }[] } {
  const comPonto = (id: string) => id in resposta.coordenadas;
  const municipios = linhas.filter(linha => linha.tipo === "municipio" && comPonto(linha.id));
  const porNivel: Record<NivelDoAlerta, string[]> = { critico: [], elevado: [], moderado: [] };
  const fundo: string[] = [];
  const grupos = new Map<string, string[]>();
  for (const linha of municipios) {
    const nivel = nivelNoDesenho(linha, sinal);
    (nivel ? porNivel[nivel] : fundo).push(linha.id);
    if (linha.uf) grupos.set(linha.uf, [...(grupos.get(linha.uf) ?? []), linha.id]);
  }
  return { fundo, porNivel,
    conjuntos: linhas.filter(linha => linha.tipo === "conjunto" && linha.idsDosMembros.some(comPonto))
      .map(linha => ({ id: linha.id, nome: linha.rotulo, membros: linha.idsDosMembros.filter(comPonto) })),
    grupos: [...grupos.entries()].map(([uf, membros]) => ({ id: "grupo:" + uf, nome: uf, membros })) };
}
/** A série da taxa de um território e a da referência dele, para a Série temporal do Agente (sinais 8 e 10). */
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

/** A coluna "Último registro": "jun/2024 · 5 médicos"; sem registro na data, diz de quando é o último. */
export function textoDaUltima(linha: LinhaDoDetector, fim: string, r: RotulosDaBase = ROTULOS_DO_BRASIL): string {
  if (!linha.ultima) return "Sem registro na janela";
  const valor = competenciaCurta(linha.ultima.competencia) + " · " + profissionais(linha.ultima.valor, r);
  return linha.ultima.naData ? valor : valor + " (sem registro em " + competenciaCurta(fim) + ")";
}

/** O tipo do território, ao lado do nome: "estado como unidade · régua própria", "conjunto · soma de 3 territórios". */
export function tipoDoTerritorio(linha: LinhaDoDetector, r: RotulosDaBase = ROTULOS_DO_BRASIL): string | null {
  return linha.tipo === "estado" ? r.grupo + " como unidade · régua própria" : linha.tipo === "conjunto"
    ? "conjunto · soma de " + (linha.membros ?? 0) + " territórios" : null;
}

// ------------------------------------------------------------------------------------------------ filtros e ordem
/** O filtro "Sinal": os sinais que podem ter nível (a linha passa quando o sinal tem nível nela), mais os territórios com mais de
 * um sinal com nível e os com registro a verificar ou com descontinuidade. */
export const SINAIS_DO_FILTRO = ["estrutural", "ausencia", "declinio", "desaceleracao", "instabilidade", "perda", "patamar", "disponibilidade",
  "posicao", "defasagem"];
export function filtrosDeSinal(r: RotulosDaBase = ROTULOS_DO_BRASIL): { chave: string; rotulo: string }[] {
  return [{ chave: "todos", rotulo: "Todos" }, ...SINAIS_DO_FILTRO.map(chave => ({ chave, rotulo: nomeDoSinal(chave, r) })),
    { chave: "juntos", rotulo: "Mais de um sinal com nível" }, { chave: "registro", rotulo: "Registro a verificar ou com descontinuidade" }];
}
/** O que o Detector leva ao Simulador de Cenários (o contexto analítico preservado): o território, a data avaliada, a janela em uso
 * (quando a pessoa a escolheu; a janela padrão do Detector, a série inteira, não é levada), os sinais com nível, pelos nomes da
 * tela ("Queda recente (elevado)"), e se os critérios eram personalizados (exploratórios). */
export type AlvoDoSimulador = { id: string; tipo: LinhaDoDetector["tipo"]; rotulo: string; sinais: string[]; fim: string;
  janela: { inicio: string; fim: string } | null; exploratorio: boolean };
export function alvoDoSimulador(linha: LinhaDoDetector, resposta: Pick<RespostaDoDetector, "janela" | "exploratorio"> & { fonte?: { rotulos: RotulosDaBase } }): AlvoDoSimulador {
  const r = resposta.fonte?.rotulos ?? ROTULOS_DO_BRASIL;
  return { id: linha.id, tipo: linha.tipo, rotulo: linha.rotulo,
    sinais: linha.alerta.sinais.map(item => nomeDoSinal(item.sinal, r) + " (" + NOMES_DOS_NIVEIS[item.nivel].toLowerCase() + ")"), fim: resposta.janela.fim,
    janela: resposta.janela.padrao ? null : { inicio: resposta.janela.inicio, fim: resposta.janela.fim }, exploratorio: resposta.exploratorio };
}
/** O patamar que "Simular recuperação" leva ao Simulador como meta hipotética: só quando o território está abaixo dele (acima do
 * patamar, não há o que recuperar). */
export const patamarARecuperar = (linha: LinhaDoDetector): number | null =>
  linha.patamar.patamar !== null && linha.patamar.diferencaPct !== null && linha.patamar.diferencaPct < 0 ? linha.patamar.patamar : null;
export type FiltrosDoDetector = { nivel: string; sinal: string; busca: string };
export const SEM_FILTROS: FiltrosDoDetector = { nivel: "todos", sinal: "todos", busca: "" };
const semAcento = (valor: string) => valor.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

/** As linhas que passam nos filtros: o nível (o do alerta do território), o sinal (com nível na linha) e o nome. */
export function filtrarLinhas(linhas: LinhaDoDetector[], filtros: FiltrosDoDetector): LinhaDoDetector[] {
  const termo = semAcento(filtros.busca.trim());
  const comOSinal = (linha: LinhaDoDetector) => filtros.sinal === "todos" ? true : filtros.sinal === "juntos" ? linha.alerta.sinais.length > 1
    : filtros.sinal === "registro" ? linha.sinais.includes("registro") : linha.alerta.sinais.some(item => item.sinal === filtros.sinal);
  return linhas.filter(linha => (filtros.nivel === "todos" || estadoDoAlerta(linha) === filtros.nivel) && comOSinal(linha) &&
    (!termo || semAcento([linha.rotulo, ...(linha.nomesAnteriores ?? [])].join(" ")).includes(termo)));
}

export type OrdemDoDetector = "nivel" | "nome" | "numero";
// Na lista, primeiro os níveis (do crítico ao moderado), depois quem a base não pôde comparar, os conjuntos e os sem alerta.
const ORDEM_DOS_ESTADOS: EstadoDoAlerta[] = ["critico", "elevado", "moderado", "sem_comparacoes", "sem_nivel", "sem_alerta"];
/** A ordem da lista. "Nível": o maior nível primeiro (um nível por território; não é um índice: só ordena a lista), depois o nome. */
export function ordenarLinhas(linhas: LinhaDoDetector[], ordem: OrdemDoDetector): LinhaDoDetector[] {
  const nome = (a: LinhaDoDetector, b: LinhaDoDetector) => a.rotulo.localeCompare(b.rotulo, "pt-BR", { numeric: true });
  const copia = [...linhas];
  if (ordem === "nome") return copia.sort(nome);
  if (ordem === "numero") return copia.sort((a, b) => (a.ultima?.valor ?? Infinity) - (b.ultima?.valor ?? Infinity) || nome(a, b));
  return copia.sort((a, b) => ORDEM_DOS_ESTADOS.indexOf(estadoDoAlerta(a)) - ORDEM_DOS_ESTADOS.indexOf(estadoDoAlerta(b)) || nome(a, b));
}

// ------------------------------------------------------------------------------------------------ ajustar critérios (em frases)
/** Um pedaço de frase: texto ou um campo (`grupo.campo` dos parâmetros do motor). */
export type ParteDaFrase = string | { grupo: string; campo: string };
export type CriterioEmFrases = { sinal: string; numero: string; titulo: string; tipo: string; frases: ParteDaFrase[][] };
const partesDe = (frase: string): ParteDaFrase[] => frase.split(/(\{\w+\.\w+\})/).filter(Boolean).map(pedaco => {
  const campo = /^\{(\w+)\.(\w+)\}$/.exec(pedaco);
  return campo ? { grupo: campo[1], campo: campo[2] } : pedaco;
});
/** Os critérios dos 12 sinais em frases, com os campos dentro delas (seção A.4 e tabela B.2): cada `{grupo.campo}` é um valor que
 * a pessoa pode trocar, e trocar um valor torna a configuração exploratória. Os nomes vêm da base. */
export function criteriosEmFrases(r: RotulosDaBase = ROTULOS_DO_BRASIL): CriterioEmFrases[] {
  const raro = (grupo: string, nivel: string, o_que: string, como: string) => "em territórios do mesmo porte, só 1 em cada {" + grupo + "." + nivel +
    "_um_em} " + o_que + " anteriores foi " + como;
  const queda = (nivel: string, nome: string) => "Alerta " + nome + " quando a queda for de pelo menos {perda." + nivel + "_minimo} " + r.profissionais +
    " e {perda." + nivel + "_fracao}% do que havia, e for rara: " + raro("perda", nivel, "mudanças", "uma queda igual ou maior") + ".";
  const emDoisAnos = (grupo: string, o_que: string) => ["Moderado quando " + o_que + " em 2 anos for rara: " + raro(grupo, "moderado", "variações", "igual ou pior") +
    ".", "Elevado: só 1 em cada {" + grupo + ".elevado_um_em}. Crítico: só 1 em cada {" + grupo + ".critico_um_em}."];
  const criterios: [string, string, string, string[]][] = [
    ["estrutural", "1–2", "por convenção", ["Pelo número de " + r.profissionais + " no último registro: crítico até {estrutural.critico} (zero é sempre crítico); " +
      "elevado até {estrutural.elevado}; moderado até {estrutural.moderado}."]],
    ["declinio", "3", "por convenção", ["Moderado com {declinio.moderado_quedas} quedas anuais seguidas e perda de {declinio.moderado_perda}% ou mais.",
      "Elevado com {declinio.elevado_quedas} quedas e {declinio.elevado_perda}% ou mais.",
      "Crítico com {declinio.critico_quedas} quedas e {declinio.critico_perda}% ou mais."]],
    ["desaceleracao", "4", "por convenção (exploratório)", ["Moderado quando o crescimento perde ritmo em {desaceleracao.anos} anos seguidos."]],
    ["instabilidade", "5", "comparado com a base", ["Moderado quando a oscilação for rara: " + raro("instabilidade", "moderado", "oscilações", "igual ou maior") + "."]],
    ["perda", "6", "comparado com a base, com tamanho mínimo", [queda("moderado", "moderado"), queda("elevado", "elevado"), queda("critico", "crítico")]],
    ["patamar", "7", "por convenção e comparado com a base", [
      "Moderado quando os 2 últimos registros estiverem {patamar.moderado}% ou mais abaixo do patamar (o melhor período que o território já teve).",
      "Elevado quando, além disso, o afastamento for raro: " + raro("patamar", "elevado", "afastamentos", "igual ou maior") + ".",
      "Crítico quando os 4 últimos registros estiverem {patamar.critico}% ou mais abaixo e o afastamento for raro: só 1 em cada {patamar.critico_um_em}.",
      "Só vale para patamar de pelo menos {patamar.minimo} " + r.profissionais + "."]],
    ["disponibilidade", "8", "comparado com a base", emDoisAnos("disponibilidade", "a queda da taxa por habitante")],
    ["posicao", "9", "comparado com a base", emDoisAnos("posicao", "a perda de posição")],
    ["defasagem", "10", "comparado com a base", emDoisAnos("defasagem", "a queda do índice ante a referência")],
    ["contexto", "11", "só contexto", ["Medir a distância até o território mais próximo com taxa de pelo menos {contexto.taxa_do_brasil_pct}% da taxa da base toda."]],
  ];
  return criterios.map(([sinal, numero, tipo, frases]) => ({ sinal, numero, tipo,
    titulo: sinal === "estrutural" ? "Poucos " + r.profissionais + " ou nenhum" : nomeDoSinal(sinal, r), frases: frases.map(partesDe) }));
}
/** O nome de um campo para o leitor de tela: o título do sinal e o texto que vem antes do campo na frase. */
export function rotuloDoCampo(criterio: CriterioEmFrases, frase: ParteDaFrase[], indice: number): string {
  const antes = frase.slice(0, indice).reverse().find((parte): parte is string => typeof parte === "string") ?? "";
  return criterio.titulo + ": " + antes.trim().replace(/[,:;(]+$/, "").trim();
}
/** Só o que difere do padrão vai no pedido (a configuração exploratória). */
export function parametrosPersonalizados(padrao: ParametrosDoDetector, emEdicao: ParametrosDoDetector): ParametrosDoDetector | null {
  const saida: ParametrosDoDetector = {};
  for (const [grupo, campos] of Object.entries(emEdicao)) for (const [chave, valor] of Object.entries(campos))
    if (padrao[grupo]?.[chave] !== undefined && padrao[grupo][chave] !== valor) (saida[grupo] ??= {})[chave] = valor;
  return Object.keys(saida).length ? saida : null;
}

// ------------------------------------------------------------------------------------------------ a régua da data
/** O que a régua diz de um nível numa faixa de porte: "queda maior que 17,1%", "qualquer queda" ou "sem comparações suficientes
 * (203 de 999)". `o_que`: "queda" (sinal 6) ou "afastamento" (sinal 7). */
export function textoDoCorte(faixa: FaixaDaRegua, nivel: NivelDoAlerta, o_que = "queda"): string {
  const corte = faixa.niveis[nivel];
  if (!corte) return "—";
  if (corte.cortePct === null) return "sem comparações suficientes (" + inteiro.format(faixa.comparacoes) + " de " + inteiro.format(corte.pede) + ")";
  return corte.cortePct <= 0 ? "qualquer " + o_que : o_que + " maior que " + formatarPct(corte.cortePct);
}

// ------------------------------------------------------------------------------------------------ exportações
const celula = (valor: unknown): string => {
  if (valor === null || valor === undefined) return "";
  const t = typeof valor === "number" ? String(valor).replace(".", ",") : String(valor);
  return /[";\n]/.test(t) ? '"' + t.replace(/"/g, '""') + '"' : t;
};
/** CSV da lista (separador ";" e BOM, como as outras exportações): uma linha por território, com o alerta, o porquê, o nível de cada
 * sinal, os valores do motor e a rastreabilidade em cada linha (a janela, a versão da base e do método e se a configuração é
 * exploratória). */
export function csvDoDetector(resposta: RespostaDoDetector, linhas: LinhaDoDetector[]): string {
  const r = resposta.fonte.rotulos;
  const tipos: Record<string, string> = { municipio: r.unidade, estado: r.grupo + " como unidade", conjunto: "conjunto", brasil: r.todo };
  const doSinal = (l: LinhaDoDetector, chave: string) => { const s = l.alerta.sinais.find(item => item.sinal === chave); return s ? NOMES_DOS_NIVEIS[s.nivel] : ""; };
  const colunas: [string, (linha: LinhaDoDetector) => unknown][] = [
    ["Identificador", l => l.id], ["Território", l => l.rotulo], ["Tipo", l => tipos[l.tipo] ?? l.tipo], ["Grupo", l => l.uf],
    ["Janela: início", () => resposta.janela.inicio], ["Janela: fim", () => resposta.janela.fim],
    ["Alerta", l => nomeDoEstado(estadoDoAlerta(l))], ["Tipo de critério", l => l.alerta.criterio],
    ["Por quê", l => textoDoPorQue(l, r)], ["Sinais com nível", l => l.alerta.sinais.map(s => nomeDoSinal(s.sinal, r) + ": " + NOMES_DOS_NIVEIS[s.nivel]).join(" | ")],
    ["Sinais da mesma queda (um evento)", l => l.alerta.mesmaQueda.map(s => nomeDoSinal(s, r)).join(" | ")],
    ["Sinais sem comparações suficientes", l => l.alerta.semComparacoes.map(s => nomeDoSinal(s, r)).join(" | ")],
    ["Última competência com registro", l => l.ultima?.competencia], [maiuscula(r.profissionais), l => l.ultima?.valor],
    ["Faixa de porte", l => l.porte === null ? "" : resposta.portes[l.porte] ?? ""],
    [nomeDoSinal("estrutural", r) + ": nível", l => doSinal(l, "estrutural") || doSinal(l, "ausencia")],
    ["Efeito da saída de um (%)", l => l.estrutural.impactoPct], ["Registros seguidos em zero", l => l.estrutural.zeros],
    ["Declínio persistente: nível", l => doSinal(l, "declinio")], ["Declínio: quedas anuais seguidas", l => l.declinio.reducoes],
    ["Declínio: perda (%)", l => l.declinio.perdaPct],
    ["Desaceleração: nível (exploratório)", l => doSinal(l, "desaceleracao")], ["Classe da tendência nos 4 registros anuais", l => l.desaceleracao.rotulo],
    ["Desaceleração: anos seguidos", l => l.desaceleracao.anos],
    ["Instabilidade: nível", l => doSinal(l, "instabilidade")], ["Índice de instabilidade", l => l.instabilidade.indice],
    ["Queda recente: nível", l => doSinal(l, "perda")], ["Queda recente: de", l => l.perda.de], ["Queda recente: até", l => l.perda.ate],
    ["Variação no último registro", l => l.perda.delta], ["Variação no último registro (%)", l => l.perda.pct],
    ["Queda recente: estado", l => l.perda.estado], ["Queda recente: motivo sem alerta", l => l.perda.motivo],
    ["Abaixo do que já teve: nível", l => doSinal(l, "patamar")], ["Patamar", l => l.patamar.patamar],
    ["Diferença para o patamar (%)", l => l.patamar.diferencaPct], ["Patamar: estado", l => l.patamar.estado],
    ["Qualidade do registro", l => l.registro.estado], ["Marcas de registro", l => l.registro.tipos.join(" | ")],
    ["Janela de comparação: de", () => resposta.comparacao.de], ["Janela de comparação: até", () => resposta.comparacao.ate],
    ["Janela de comparação: estado", () => resposta.comparacao.estado],
    [nomeDoSinal("disponibilidade", r) + ": nível", l => doSinal(l, "disponibilidade")], ["Taxa por 1.000 habitantes", l => l.disponibilidade.taxa],
    ["População", l => l.disponibilidade.populacao], ["Variação da taxa em 2 anos (%)", l => l.disponibilidade.variacaoPct],
    ["Taxa: estado", l => l.disponibilidade.estado],
    ["Perda de posição: nível", l => doSinal(l, "posicao")], ["Percentil da taxa", l => l.posicao.percentil], ["Universo do percentil", l => l.posicao.universo],
    ["Variação do percentil em 2 anos (pontos)", l => l.posicao.variacaoPp], ["Posição: estado", l => l.posicao.estado],
    ["Mais longe da referência: nível", l => doSinal(l, "defasagem")], ["Índice ante a referência", l => l.defasagem.indice],
    ["Variação do índice em 2 anos (pontos)", l => l.defasagem.variacaoPontos], ["Referência: estado", l => l.defasagem.estado],
    ["Distância ao mais próximo que atende ao critério (km)", l => l.contexto.distanciaKm],
    ["Mais próximo que atende ao critério", l => l.contexto.referencia], ["Percentil da distância", l => l.contexto.percentil],
    ["Distância: estado", l => l.contexto.estado], ["Critério da distância: taxa mínima", () => resposta.comparacao.contexto.taxaMinima],
    ["Configuração", () => resposta.exploratorio ? "exploratória (critérios diferentes do padrão)" : "padrão"],
    ["Versão do método", () => resposta.versao], ["Versão da base", () => resposta.fonte.versao],
  ];
  const corpo = [colunas.map(([nome]) => celula(nome)).join(";"), ...linhas.map(linha => colunas.map(([, valor]) => celula(valor(linha))).join(";"))];
  return "﻿" + corpo.join("\r\n") + "\r\n";
}

/** O método em JSON: a fonte, a janela, os critérios (padrão e em uso), os níveis, a régua da data (a dos estados, quando há) e as notas. */
export function metodoDoDetector(resposta: RespostaDoDetector): string {
  return JSON.stringify({ ferramenta: "Detector de Sinais Territoriais", versao_do_metodo: resposta.versao, fonte: resposta.fonte,
    janela: resposta.janela, configuracao: resposta.exploratorio ? "exploratória (critérios diferentes do padrão)" : "padrão",
    parametros: resposta.parametros, niveis: resposta.niveis, regua_na_data: resposta.calibracao,
    ...(resposta.calibracaoDosEstados ? { regua_dos_estados_na_data: resposta.calibracaoDosEstados } : {}),
    aviso_da_base: resposta.avisoDaBase, comparacao_em_2_anos: resposta.comparacao, notas: resposta.notas,
    limitacoes: resposta.limitacoes, referencia: "Docs/DETECTOR_E_SIMULADOR_V3.md, Partes A e B" }, null, 2);
}
