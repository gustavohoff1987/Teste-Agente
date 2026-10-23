// Conversa agindo no gráfico (22/10/2026): funções puras da conversa da página única. Reconhecem a escolha da fonte, os
// pedidos de apresentação (a vista do desenho, gráfico ou mapa, desde 23/10/2026) e o pedido de resumo, transformam o
// campo `painel` da resposta do intérprete num pedido para a área de análise e montam, a partir do contexto do gráfico, as
// opções que vão ao intérprete local. Nada daqui vai ao provedor de IA: o backend só lhe entrega o pedido sanitizado e
// estados enumerados. Só importações de tipos: os testes unitários (frontend/tests/conversaGrafico.test.mjs) transpilam
// este arquivo sozinho.
import type { ContextoDoGrafico, Familia, Indicador, PedidoDoChat, Rotulos } from "./paginaUnica";

export function normalizeCommand(message: string): string {
  return message.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
    .replace(/[.,!?]/g, " ").replace(/\s+/g, " ").trim();
}

/** A mensagem inteira é a escolha da fonte ("usar dados do Brasil", "enviar meus dados"): a mesma ação dos botões. */
export function comandoDeFonte(message: string): "brasil" | "arquivo" | null {
  const texto = normalizeCommand(message);
  if (/^(?:(?:quero|vou|prefiro|usar|utilizar|use|escolho|seleciono|pode usar|quero usar|comecar com) )*(?:(?:os|a|a base|a base de|a base do) )?(?:dados do brasil|base do brasil|base brasileira|brasil)$/.test(texto))
    return "brasil";
  if (/^(?:(?:quero|vou|prefiro|usar|utilizar|escolho|seleciono|quero usar) )*(?:importar|upload|enviar arquivo|enviar planilha|enviar meus dados|enviar os meus dados|meus dados|importar meus dados|importar arquivo)$/.test(texto))
    return "arquivo";
  return null;
}

/** Pedidos de apresentação que a interface reconhece sozinha, sem recalcular: a vista do desenho (o mapa voltou em
 * 23/10/2026 como segunda vista do gráfico) e a tabela, que fica nos Detalhes. */
export type ResultView = "mapa" | "graficos" | "tabela";
const VIEW_WORDS = new Map<string, ResultView>([["mapa", "mapa"], ["grafico", "graficos"], ["graficos", "graficos"], ["tabela", "tabela"]]);
// Palavras que acompanham o pedido sem mudar o sentido; qualquer outra (inclusive "não") deixa a mensagem para a
// interpretação, que também conhece esses pedidos ("mostre o Pará no mapa" muda o recorte e a vista juntos).
const VIEW_FILLER = new Set(("me mostre mostra mostrar ver veja abra abre abrir exiba exibe exibir quero queria gostaria " +
  "pode poderia de do da no na em num numa um uma o a os as isso isto esse essa resultado resultados aba agora entao " +
  "tambem por favor la ai e pra para volte volta voltar retorne retorna retornar ao pro vamos va ir passe passa passar " +
  "mude muda mudar").split(" "));
const PREVIOUS_FILLER = new Set(("volta volte voltar retorna retorne retornar reabra reabre reabrir abra abre abrir mostra " +
  "mostre mostrar ver quero queria me de do da para pra pro ao a o as os no na por favor aquele aquela e agora").split(" "));
// "Para" depois de artigo ("mostre o Para no mapa") ou escrito "Pará" é o estado, não a preposição.
const ANTES_DO_ESTADO = new Set(["o", "do", "no", "ao", "pelo"]);

/** "Ver no mapa", "volte ao gráfico", "agora a tabela": o pedido, ou null quando a mensagem diz mais do que isso. */
export function viewCommand(message: string): ResultView | null {
  if (/(?:^|[^\p{L}])pará(?!\p{L})/iu.test(message.normalize("NFC"))) return null;
  const words = normalizeCommand(message).split(" ").filter(Boolean);
  const views = words.filter(word => VIEW_WORDS.has(word));
  const filler = (word: string, index: number) =>
    VIEW_FILLER.has(word) && !(word === "para" && ANTES_DO_ESTADO.has(words[index - 1] ?? ""));
  if (views.length !== 1 || words.some((word, index) => !VIEW_WORDS.has(word) && !filler(word, index))) return null;
  return VIEW_WORDS.get(views[0]) ?? null;
}

/** "Volte para o resultado anterior", "volta pra análise de antes": reabrir a análise anterior, sem recalcular. */
export function previousResultCommand(message: string): boolean {
  const words = normalizeCommand(message).split(" ").filter(Boolean);
  const target = words.filter(word => ["resultado", "analise", "selecao", "recorte"].includes(word));
  const marker: string[] = words.filter(word => word === "anterior" || word === "antes");
  return target.length === 1 && marker.length === 1 &&
    words.every(word => target.includes(word) || marker.includes(word) || PREVIOUS_FILLER.has(word));
}

/** Resposta a um pedido de apresentação e, quando a vista muda, o pedido para a área (`{ vista }`, pelo mesmo caminho dos
 * demais comandos do gráfico). Trocar de vista é estado visual: nada é recalculado (RQ-REP-06). */
export type RespostaDaVista = { texto: string; pedido: PedidoDoChat | null };
const NADA_MUDOU = "Nada mudou no gráfico.";
const comPonto = (texto: string) => /[.!?…]$/.test(texto) ? texto : texto + ".";

/** "Ver no mapa" troca o gráfico pelo mapa quando a área diz que ele está disponível; senão, a resposta é o motivo da área
 * (por exemplo, nos estados, que não têm um ponto), e nada muda. "Volte ao gráfico" desfaz. "Agora a tabela" aponta os
 * Detalhes. */
export function respostaDaVista(vista: ResultView, contexto: ContextoDoGrafico | null): RespostaDaVista {
  if (vista === "tabela")
    return { texto: "A tabela fica em Detalhes, logo abaixo do " + (contexto?.vista === "mapa" ? "mapa" : "gráfico") +
      ", com os mesmos valores do motor.", pedido: null };
  if (vista === "mapa") {
    if (!contexto) return { texto: "Ainda não há uma análise na tela para mostrar no mapa.", pedido: null };
    if (contexto.mapaDisponivel === false)
      return { texto: comPonto(contexto.motivoSemMapa?.trim() || "O mapa não está disponível nesta análise") + " " + NADA_MUDOU,
        pedido: null };
    if (contexto.vista === "mapa") return { texto: "O mapa já está na tela. Para voltar, peça “volte ao gráfico”.", pedido: null };
    return { texto: "Mostrei o mapa no lugar do gráfico. Para voltar, peça “volte ao gráfico”.", pedido: { vista: "mapa" } };
  }
  const jaNoGrafico = "O gráfico já está na tela. Peça uma mudança, por exemplo outra competência ou outro recorte, e eu a aplico.";
  if (!contexto || contexto.vista === "grafico") return { texto: jaNoGrafico, pedido: null };
  // No mapa ou lado a lado, volta ao gráfico; sem a vista no contexto, o pedido vai assim mesmo (a área o aplica sem mudar nada).
  return { texto: contexto.vista ? "Voltei ao gráfico. Para ver de novo no mapa, peça “ver no mapa”." : jaNoGrafico,
    pedido: { vista: "grafico" } };
}

// Pedido de resumo do que está na tela ("o que esse gráfico mostra?", "resuma o gráfico", "explique o resultado", "o que
// estou vendo?"), com palavras que não mudam o pedido antes e depois. Qualquer outra palavra (um período, um nome, "de
// forma simples") deixa a mensagem para a interpretação.
const RESUMO_ALVO = "(?:(?:esse|este|essa|esta|esses|estes|o|a|os|as|nesse|neste|nessa|nesta|no|na|do|da|desse|deste|dessa|desta) )?" +
  "(?:grafico|mapa|resultado|resultados|desenho|analise|tela)";
const RESUMO_VERBO = "(?:mostra|mostram|esta mostrando|estao mostrando|significa|significam|quer dizer|querem dizer|diz|dizem|" +
  "representa|representam)";
const RESUMO = new RegExp("^(?:(?:e|entao|agora|afinal|me|pode|poderia|voce pode|voce poderia|por favor) )*(?:" + [
  "o que " + RESUMO_ALVO + " " + RESUMO_VERBO,
  "o que " + RESUMO_VERBO + " " + RESUMO_ALVO,
  "o que (?:eu )?(?:estou|to|tou|estamos) vendo",
  "(?:resuma|resume|resumir|resumo|sintetize|sintetiza)(?: " + RESUMO_ALVO + ")?",
  "(?:faca|faz|de|da) (?:um |uma )?(?:resumo|sintese)(?: " + RESUMO_ALVO + ")?",
  "(?:explique|explica|explicar|descreva|descreve|descrever) " + RESUMO_ALVO,
].join("|") + ")(?: (?:aqui|ai|agora|na tela|por favor|pra mim|para mim))*$");

/** "O que esse gráfico mostra?": o pedido de resumo, respondido na tela com a frase do motor, sem o intérprete. */
export function pedidoDeResumo(message: string): boolean {
  return RESUMO.test(normalizeCommand(message));
}

/** A frase-resumo verificada do motor, como veio (sem paráfrase), ou o aviso de que ainda não há o que resumir. */
export function respostaDoResumo(contexto: ContextoDoGrafico | null): string {
  const resumo = typeof contexto?.resumo === "string" ? contexto.resumo.trim() : "";
  return resumo || "Ainda não há um gráfico calculado para resumir.";
}

const FAMILIAS: Familia[] = ["distribuicao", "espacial", "tendencia", "rotatividade"];
const FUNCOES = ["comparar", "juntar", "condicoes", "ordenar", "exportar"] as const;
const VISOES = ["mudanca", "classes", "series"] as const;
const textos = (valor: unknown): string[] =>
  Array.isArray(valor) ? [...new Set(valor.filter((item): item is string => typeof item === "string" && !!item))] : [];
const objeto = (valor: unknown): Record<string, unknown> | null =>
  valor && typeof valor === "object" && !Array.isArray(valor) ? valor as Record<string, unknown> : null;

/** Campo `painel` da resposta da conversa → pedido para a área. Só os campos válidos entram; `null` (não citado) fica de
 * fora. Sem nenhum campo, não há pedido. */
export function pedidoDoPainel(painel: unknown): PedidoDoChat | null {
  const p = objeto(painel);
  if (!p) return null;
  const pedido: PedidoDoChat = {};
  if (FAMILIAS.includes(p.familia as Familia)) pedido.familia = p.familia as Familia;
  if (p.indicador === "densidade" || p.indicador === "quantidade") pedido.indicador = p.indicador;
  if (p.nivel === "estados" || p.nivel === "municipios") pedido.nivel = p.nivel;
  const municipios = objeto(p.municipios);
  if (municipios) {
    const todos = municipios.todos === true, estados = textos(municipios.estados), ids = textos(municipios.ids);
    if (todos || estados.length || ids.length) pedido.municipios = { todos, estados, ids };
  }
  if (typeof p.competencia === "string" && p.competencia) pedido.competencia = p.competencia;
  const janela = textos(p.janela);
  if (janela.length) pedido.janela = janela;
  const visao = p.visao_tendencia ?? p.visaoTendencia;
  if (VISOES.includes(visao as typeof VISOES[number])) pedido.visaoTendencia = visao as typeof VISOES[number];
  const referencia = objeto(p.referencia);
  if (referencia) {
    const membros = textos(referencia.membros), criterio = objeto(referencia.criterio);
    if (membros.length || criterio) pedido.referencia = { membros, ...(criterio ? { criterio } : {}) };
  }
  if (FUNCOES.includes(p.funcao as typeof FUNCOES[number])) pedido.funcao = p.funcao as typeof FUNCOES[number];
  const selecao = textos(p.selecao);
  if (selecao.length) pedido.selecao = selecao;
  const ordenar = objeto(p.ordenar);
  if (ordenar) pedido.ordenar = ordenar;
  if (Array.isArray(p.condicoes)) {
    const condicoes = p.condicoes.filter((item): item is object => !!objeto(item));
    if (condicoes.length) pedido.condicoes = condicoes;
  }
  const grupos = objeto(p.grupos);
  if (grupos && ["quartis", "quintis", "decis", "nenhum"].includes(grupos.tipo as string)) pedido.grupos = { tipo: grupos.tipo as string };
  // Vista do desenho pedida junto com o comando ("mostre o Pará no mapa"): estado visual, que a área aplica sem recalcular.
  if (p.vista === "grafico" || p.vista === "mapa") pedido.vista = p.vista;
  return Object.keys(pedido).length ? pedido : null;
}

/** Só para a escolha explícita entre alternativas (um botão de esclarecimento) quando o intérprete não devolve o campo
 * `painel`: a operação escolhida vira a família ou a função equivalente, com a mesma correspondência do motor da conversa. */
export function pedidoDaOperacao(operacao: string | null | undefined, indicador?: string | null): PedidoDoChat | null {
  const medida: Indicador | null = indicador === "quantity" ? "quantidade" : indicador === "density" ? "densidade" : null;
  const com = (pedido: PedidoDoChat): PedidoDoChat => medida && !pedido.indicador ? { ...pedido, indicador: medida } : pedido;
  switch (operacao) {
    case "density": return { familia: "distribuicao", indicador: "densidade" };
    case "counts": return { familia: "distribuicao", indicador: "quantidade" };
    case "distribution": return com({ familia: "distribuicao" });
    case "temporal": return com({ familia: "tendencia" });
    case "spatial": case "nearest": return { familia: "espacial" };
    case "rotation": return { familia: "rotatividade" };
    case "comparisons": return com({ funcao: "comparar" });
    case "aggregate": return { funcao: "juntar" };
    case "ranking": return { funcao: "ordenar" };
    case "criteria": return { funcao: "condicoes" };
    case "report": return { funcao: "exportar" };
    default: return null;
  }
}

const NOMES_DAS_FAMILIAS: Record<Familia, string> = { distribuicao: "distribuição", espacial: "análise espacial",
  tendencia: "tendência", rotatividade: "rotatividade" };
const NOMES_DAS_FUNCOES: Record<typeof FUNCOES[number], string> = { comparar: "comparação", juntar: "junção de unidades",
  condicoes: "seleção por condições", ordenar: "ordenação", exportar: "exportação" };

/** O pedido em palavras: "distribuição da densidade", "comparação". */
export function rotuloDoPedido(pedido: PedidoDoChat | null): string {
  if (!pedido) return "";
  const partes: string[] = [];
  if (pedido.familia) partes.push(NOMES_DAS_FAMILIAS[pedido.familia] + (pedido.indicador ? " da " + pedido.indicador : ""));
  else if (pedido.indicador) partes.push(pedido.indicador);
  if (pedido.funcao) partes.push(NOMES_DAS_FUNCOES[pedido.funcao]);
  return partes.join(", com ");
}

// A família na operação que o intérprete local já conhece (exploration_operation); a família vai também em painel_familia.
const OPERACAO_DA_FAMILIA: Record<Familia, string> = { distribuicao: "density", espacial: "spatial", tendencia: "temporal",
  rotatividade: "rotation" };
const ID_TERRITORIAL = /^(?:code|name):/;

/** Opções da conversa a partir do contexto do gráfico: as unidades na tela (só as do catálogo territorial; com "Todos",
 * nenhuma, porque o universo é a base inteira), a família, o indicador e a competência ou a janela. As chaves `painel_*`
 * levam o estado do gráfico como ele está (nível, indicador, escolha das unidades, competência, janela, referência, vista do
 * desenho, se o mapa está disponível e a frase-resumo do motor), para a conversa completar o pedido sem perder o que já está
 * na tela. O backend as tira das opções antes do pré-exame, do intérprete e do provedor de IA (conversa_grafico.CONTEXTO). */
export function opcoesDaConversa(contexto: ContextoDoGrafico | null, hoje: string): Record<string, unknown> {
  const opcoes: Record<string, unknown> = { conversation_today: hoje };
  // Sem gráfico ainda (a base acabou de ficar pronta), a página única segue reconhecida: painel_familia vai nulo, e a
  // conversa responde no formato do gráfico, nunca com as orientações das telas que saíram.
  if (!contexto) return { ...opcoes, painel_familia: null };
  const indicador = contexto.indicador === "quantidade" ? "quantity" : "density";
  const operacao = contexto.familia === "distribuicao" && contexto.indicador === "quantidade" ? "counts"
    : OPERACAO_DA_FAMILIA[contexto.familia] ?? "density";
  const ids = contexto.nivel === "municipios" && !contexto.municipios.todos
    ? [...new Set(contexto.idsNaTela.filter(id => ID_TERRITORIAL.test(id)))] : [];
  const periodo = contexto.familia === "tendencia" && contexto.janela.length
    ? { period_filter: "", period_filters: [...contexto.janela] }
    : contexto.competencia ? { period_filter: contexto.competencia, period_filters: [] } : {};
  return { ...opcoes, ...(ids.length ? { territory_ids: ids } : {}), exploration_operation: operacao,
    exploration_indicator: indicador, comparison_indicator: indicador, temporal_indicator: indicador, ...periodo,
    painel_familia: contexto.familia, painel_indicador: contexto.indicador, painel_nivel: contexto.nivel,
    painel_municipios: contexto.municipios, ...(contexto.competencia ? { painel_competencia: contexto.competencia } : {}),
    ...(contexto.janela.length ? { painel_janela: [...contexto.janela] } : {}),
    ...(contexto.referencia.length ? { painel_referencia: [...contexto.referencia] } : {}),
    ...(contexto.vista ? { painel_vista: contexto.vista } : {}),
    ...(typeof contexto.mapaDisponivel === "boolean" ? { painel_mapa_disponivel: contexto.mapaDisponivel } : {}),
    ...(typeof contexto.resumo === "string" && contexto.resumo ? { painel_resumo: contexto.resumo } : {}) };
}

export type EtapaDaFonte = { tipo: "brasil" | "arquivo" | null; pronta: boolean; colunasPendentes: boolean };

/** Orientação curta da caixa da conversa em cada etapa. Na planilha, os nomes vêm dos rótulos escolhidos (nunca
 * "município" fixo), sempre no plural, sem artigos de gênero. */
export function guiaDaConversa(fonte: EtapaDaFonte, contexto: ContextoDoGrafico | null, rotulos: Rotulos | null): string {
  if (!fonte.tipo) return "O que você quer analisar? Prefere começar com os dados do Brasil, enviar os seus ou baixar o modelo de " +
    "planilha?";
  if (!fonte.pronta) {
    if (fonte.tipo === "brasil") return "Estou preparando os dados do Brasil. Em seguida, escolha os territórios que quer analisar.";
    return fonte.colunasPendentes ? "Confira as colunas da planilha no painel Colunas, no alto da página, e escolha “Começar a análise”."
      : "Estou lendo a sua planilha.";
  }
  const unidades = rotulos?.unidade.plural || "unidades", grupos = rotulos?.grupo?.plural || "";
  // A base carregada abre sem seleção (23/10/2026): a conversa orienta a escolher os territórios.
  if (contexto && contexto.nivel === "municipios" && !contexto.municipios.todos && !contexto.municipios.estados.length &&
    !contexto.municipios.ids.length)
    return "Os dados estão prontos. Escolha os territórios na Seleção de Territórios ou me diga quais quer ver" +
      (fonte.tipo === "brasil" ? ", por exemplo “mostre o Pará” ou “todos os estados”." : ".");
  if (!contexto || contexto.nivel === "estados")
    return grupos ? "Escolha no gráfico quais " + grupos + " abrir, ou me diga quais " + unidades + " quer ver."
      : "Escolha " + unidades + " no gráfico ou me diga quais quer ver.";
  return fonte.tipo === "brasil"
    ? "Peça mudanças no gráfico, por exemplo: “mostre o Pará”, “use Belém como referência” ou “compare Manaus e Tefé”."
    : "Peça mudanças no gráfico citando " + unidades + " pelo nome: comparar, juntar, usar como referência" +
      (grupos ? " ou voltar ao nível de " + grupos : "") + ".";
}
