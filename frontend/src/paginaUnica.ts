// Página única de análise (22/10/2026). Tipos do contrato entre a estrutura da página (App.tsx) e a área de análise
// (AreaDeAnalise.tsx), e funções puras da estrutura: resumo da fonte, rótulos das unidades territoriais, colunas de uma
// planilha enviada, Histórico e exportação da sessão. Nada é calculado aqui: os números vêm do motor, e estas funções só
// organizam o que o backend devolveu e o que a pessoa escolheu. Sem importações: os testes unitários
// (frontend/tests/paginaUnica.test.mjs) transpilam este arquivo sozinho.

/** As quatro famílias de análise da área. */
export type Familia = "distribuicao" | "espacial" | "tendencia" | "rotatividade";
export type Indicador = "densidade" | "quantidade";
/** O nível em análise: os municípios, os estados como unidades ou o Brasil inteiro como uma unidade (24/10/2026). */
export type Nivel = "estados" | "municipios" | "brasil";
/** Universo do gráfico, na forma de `options.base.municipios` do motor. */
export type MunicipiosDoGrafico = { todos: boolean; estados: string[]; ids: string[] };
/** Como se chamam as unidades territoriais e os grupos delas, no singular e no plural. */
export type Rotulo = { singular: string; plural: string };
export type Rotulos = { unidade: Rotulo; grupo: Rotulo | null };
/** A fonte que a área usa: a base do Brasil ou uma planilha enviada, com o mapeamento confirmado na tela. */
export type FonteDados = {
  tipo: "brasil" | "arquivo"; apiBase: string; datasetVersion: string; sheet: string;
  mapping: Record<string, string>; arquivo: File | null; nome: string;
  geoVersion?: string; premissas?: Record<string, string | string[]>;
  /** Nomes das unidades e dos grupos: fixos na base do Brasil (município, estado); na planilha, os que a pessoa escolheu. */
  rotulos: Rotulos;
};
/** Comando da conversa para a área (campo `painel` da resposta do intérprete). */
export type PedidoDoChat = {
  familia?: Familia | null; indicador?: Indicador | null; nivel?: Nivel | null;
  municipios?: MunicipiosDoGrafico | null; competencia?: string | null; janela?: string[] | null;
  visaoTendencia?: "mudanca" | "classes" | "series" | null; referencia?: { membros: string[]; criterio?: object } | null;
  funcao?: "comparar" | "juntar" | "condicoes" | "ordenar" | "exportar" | null; selecao?: string[] | null;
  ordenar?: object | null; condicoes?: object[] | null;
  /** Grupos por posição da distribuição (quartis, quintis, decis) ou "nenhum" para tirá-los. */
  grupos?: { tipo: string } | null;
  /** Vista do desenho pedida na conversa ("ver no mapa", "volte ao gráfico"): estado visual, não recalcula. */
  vista?: "grafico" | "mapa" | null;
  /** Explicação pedida na conversa (26/10/2026): abre "Entenda esta análise" na aba, com os termos (códigos das classes)
   * destacados. Estado visual: nada é recalculado. */
  explicar?: { aba: Familia; termos: string[] } | null;
};
/** O que está no gráfico, informado pela área a cada mudança: é o contexto da conversa. */
export type ContextoDoGrafico = {
  familia: Familia; indicador: Indicador; nivel: Nivel; municipios: MunicipiosDoGrafico; idsNaTela: string[];
  competencia: string; janela: string[]; referencia: string[]; titulo: string;
  /** Os estados escolhidos no nível estados (24/10/2026). */
  estados?: string[];
  /** Vista em exibição e a frase-resumo do motor (verificada), para a conversa responder "o que o gráfico mostra?". */
  vista?: "grafico" | "mapa" | "lado"; resumo?: string | null;
  /** Se o mapa pode ser mostrado agora e, se não, o motivo (estados sem ponto, planilha sem coordenadas, visão Séries). */
  mapaDisponivel?: boolean; motivoSemMapa?: string | null;
  /** Os itens da comparação aberta (2 ou 3 ids), para a conversa trocar a ordem, incluir, tirar e voltar a ela. */
  comparar?: string[];
};
/** Estado de uma análise, guardado pela área ao calcular: o Histórico o reabre sem recalcular. */
export type EstadoSalvo = { titulo: string; definicao: object; resposta: object | null; quando: string };

// ---------------------------------------------------------------------------------------------------------------------
// Resumo da fonte

const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

/** "202406" vira "jun/2024"; outros formatos (um ano, por exemplo) ficam como estão. */
export function competenciaCurta(valor: string): string {
  const partes = /^(\d{4})(\d{2})$/.exec(valor);
  const mes = partes ? Number(partes[2]) : 0;
  return partes && mes >= 1 && mes <= 12 ? MESES_CURTOS[mes - 1] + "/" + partes[1] : valor;
}

export const cronologica = (valores: string[]) =>
  [...new Set(valores)].sort((a, b) => a.localeCompare(b, "pt-BR", { numeric: true }));

/** Primeiro e último período, em ordem cronológica: "jan/2014 a jun/2024". */
export function intervaloDePeriodos(periodos: string[]): string {
  const lista = cronologica(periodos.filter(Boolean));
  if (!lista.length) return "";
  return lista.length === 1 ? competenciaCurta(lista[0])
    : competenciaCurta(lista[0]) + " a " + competenciaCurta(lista[lista.length - 1]);
}

/** Categoria em caixa alta ("MEDICINA") aparece como frase ("Medicina"); as demais ficam como vieram. */
export function nomeDaCategoria(categoria: string): string {
  const texto = categoria.trim();
  if (!texto || texto !== texto.toLocaleUpperCase("pt-BR") || !/\p{L}/u.test(texto)) return texto;
  return texto.charAt(0) + texto.slice(1).toLocaleLowerCase("pt-BR");
}

/** Linha da fonte no alto da página: "Dados do Brasil · Medicina · jan/2014 a jun/2024" ou, numa planilha,
 * "dados.csv · distritos e províncias · Medicina · 2021 a 2024". */
export function resumoDaFonte({ tipo, nome, categorias, periodos, rotulos }: {
  tipo: "brasil" | "arquivo"; nome: string; categorias: string[]; periodos: string[]; rotulos?: Rotulos | null;
}): string {
  const partes = [tipo === "brasil" ? "Dados do Brasil" : nome];
  if (tipo === "arquivo" && rotulos) partes.push(rotulos.unidade.plural + (rotulos.grupo ? " e " + rotulos.grupo.plural : ""));
  const lista = [...new Set(categorias.filter(Boolean))];
  if (lista.length === 1) partes.push(nomeDaCategoria(lista[0]));
  else if (lista.length > 1) partes.push(lista.length + " categorias");
  const intervalo = intervaloDePeriodos(periodos);
  if (intervalo) partes.push(intervalo);
  return partes.join(" · ");
}

// ---------------------------------------------------------------------------------------------------------------------
// Rótulos das unidades territoriais

/** Base do Brasil: rótulos fixos. */
export const ROTULOS_DO_BRASIL: Rotulos = {
  unidade: { singular: "município", plural: "municípios" }, grupo: { singular: "estado", plural: "estados" },
};
export const UNIDADE_GENERICA: Rotulo = { singular: "unidade", plural: "unidades" };
export const GRUPO_GENERICO: Rotulo = { singular: "grupo", plural: "grupos" };

const semAcento = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();

// Nomes territoriais comuns, com acentos e plural (inclusive os termos em inglês de planilhas de outros países). Fora
// desta lista, a sugestão é a própria palavra da coluna, e a pessoa ajusta.
const TERMOS: Record<string, Rotulo> = Object.fromEntries(([
  [["municipio", "municipality", "municipalidad"], "município", "municípios"],
  [["distrito", "district", "distrito sanitario"], "distrito", "distritos"],
  [["provincia", "province"], "província", "províncias"],
  [["condado", "county"], "condado", "condados"],
  [["estado", "state", "uf"], "estado", "estados"],
  [["departamento", "department"], "departamento", "departamentos"],
  [["regiao", "region"], "região", "regiões"],
  [["comuna", "commune"], "comuna", "comunas"],
  [["cidade", "city", "ciudad"], "cidade", "cidades"],
  [["pais", "country"], "país", "países"],
  [["territorio", "territory"], "território", "territórios"],
  [["localidade", "locality"], "localidade", "localidades"],
  [["bairro", "neighborhood", "barrio"], "bairro", "bairros"],
  [["cantao", "canton"], "cantão", "cantões"],
  [["paroquia", "parish"], "paróquia", "paróquias"],
  [["freguesia"], "freguesia", "freguesias"],
  [["concelho"], "concelho", "concelhos"],
  [["prefeitura", "prefecture"], "prefeitura", "prefeituras"],
  [["zona", "zone"], "zona", "zonas"],
  [["area"], "área", "áreas"],
  [["setor", "sector"], "setor", "setores"],
  [["polo"], "polo", "polos"],
  [["dsei"], "DSEI", "DSEIs"],
  [["unidade", "unit"], "unidade", "unidades"],
] as [string[], string, string][]).flatMap(([chaves, singular, plural]) =>
  chaves.map(chave => [chave, { singular, plural }] as [string, Rotulo])));
// Partes do nome da coluna que não dizem o que é a unidade ("nome_distrito", "cod_municipio", "territorio_superior_1").
const RUIDO = new Set(["nome", "nm", "no", "cod", "codigo", "code", "id", "de", "do", "da", "dos", "das", "of", "the", "name",
  "sigla", "desc", "descricao", "ibge", "geocodigo", "geocode", "territorial", "analise", "superior", "nivel", "level", "mae"]);

/** Plural simples do português, para palavras fora da lista de termos. */
export function pluralizar(palavra: string): string {
  const texto = palavra.trim();
  if (!texto) return texto;
  if (/ão$/i.test(texto)) return texto.replace(/ão$/i, "ões");
  if (/[aeiou]l$/i.test(texto)) return texto.replace(/l$/i, "is");
  if (/m$/i.test(texto)) return texto.replace(/m$/i, "ns");
  if (/[rz]$/i.test(texto)) return texto + "es";
  if (/[sx]$/i.test(texto)) return texto;
  return texto + "s";
}

/** Sugestão de nome a partir do nome da coluna: "distrito" sugere distrito/distritos; "provincia", província/províncias. */
export function sugerirRotulo(coluna: string | undefined | null): Rotulo | null {
  if (!coluna) return null;
  const texto = semAcento(coluna);
  const palavras = texto.split(/[^a-z0-9]+/).filter(Boolean);
  const composta = palavras.join(" ");
  if (TERMOS[composta]) return { ...TERMOS[composta] };
  for (const palavra of palavras) if (TERMOS[palavra]) return { ...TERMOS[palavra] };
  const util = palavras.find(palavra => /^[a-z]{3,}$/.test(palavra) && !RUIDO.has(palavra));
  return util ? { singular: util, plural: pluralizar(util) } : null;
}

export function rotulosSugeridos(unidade: string | undefined, grupo: string | undefined): Rotulos {
  return {
    unidade: sugerirRotulo(unidade) ?? { ...UNIDADE_GENERICA },
    grupo: grupo ? sugerirRotulo(grupo) ?? { ...GRUPO_GENERICO } : null,
  };
}

// ---------------------------------------------------------------------------------------------------------------------
// Colunas de uma planilha enviada (painel "Colunas")

/** Papéis das colunas. `grupo_territorial` é a coluna-mãe que agrupa as unidades (estado, província, região). */
export type Papel = "territory" | "territory_id" | "grupo_territorial" | "period" | "category" | "count" | "population" |
  "latitude" | "longitude" | "identity";
export type Mapeamento = Partial<Record<Papel, string>>;
export const PAPEIS: { papel: Papel; rotulo: string; ajuda: string; obrigatorio: boolean; vazio: string }[] = [
  { papel: "territory", rotulo: "Unidade territorial", ajuda: "A unidade de cada linha: município, distrito, condado…",
    obrigatorio: true, vazio: "Escolher coluna" },
  { papel: "territory_id", rotulo: "Código da unidade", ajuda: "Distingue unidades com o mesmo nome", obrigatorio: false,
    vazio: "Sem código" },
  { papel: "grupo_territorial", rotulo: "Grupo territorial", ajuda: "A coluna-mãe que agrupa as unidades: estado, província…",
    obrigatorio: false, vazio: "Sem grupo" },
  { papel: "period", rotulo: "Período", ajuda: "Ano ou competência (AAAAMM)", obrigatorio: true, vazio: "Escolher coluna" },
  { papel: "category", rotulo: "Categoria", ajuda: "Profissão ou categoria", obrigatorio: false, vazio: "Sem categoria" },
  { papel: "count", rotulo: "Quantidade", ajuda: "A contagem de profissionais", obrigatorio: true, vazio: "Escolher coluna" },
  { papel: "population", rotulo: "População", ajuda: "Para a densidade por 1.000 habitantes", obrigatorio: false,
    vazio: "Sem população" },
  { papel: "latitude", rotulo: "Latitude", ajuda: "Para a análise espacial", obrigatorio: false, vazio: "Sem latitude" },
  { papel: "longitude", rotulo: "Longitude", ajuda: "Para a análise espacial", obrigatorio: false, vazio: "Sem longitude" },
  { papel: "identity", rotulo: "Identificador individual", ajuda: "Para a rotatividade", obrigatorio: false,
    vazio: "Sem identificador" },
];
/** Papéis que o pré-exame do backend conhece (semantic_bridge.ROLES); o grupo territorial vai em `hierarchy_columns`. */
const PAPEIS_DO_PREEXAME: Papel[] = ["territory", "territory_id", "period", "category", "count", "population", "latitude",
  "longitude", "identity"];
export const UNIDADES_DE_CONTAGEM: [string, string][] = [["pessoas", "Pessoas"], ["vinculos", "Vínculos de trabalho"],
  ["postos", "Postos de trabalho"], ["outro", "Outra unidade"]];
/** Referenciais das coordenadas admitidos: SIRGAS 2000 (SPEC) e WGS 84 (aprovado pelo responsável pelo produto em
 * 22/10/2026). A pessoa informa o referencial em que as coordenadas foram coletadas, e o sistema não converte um no outro.
 * "Outro referencial" e "Não sei" deixam a análise espacial indisponível: nada é presumido. */
export const REFERENCIAIS_ACEITOS: readonly string[] = ["SIRGAS2000", "WGS84"];
export const REFERENCIAIS: [string, string][] = [["SIRGAS2000", "SIRGAS 2000"], ["WGS84", "WGS 84"],
  ["outro", "Outro referencial"], ["desconhecido", "Não sei"]];
export const SEPARADORES: [string, string][] = [["decimal_comma", "Vírgula"], ["decimal_point", "Ponto"]];

export type EscolhasDaPlanilha = {
  mapeamento: Mapeamento;
  /** Papéis cuja coluna a pessoa escolheu no seletor (os demais vêm do reconhecimento por regra do backend). */
  escolhidos: Papel[];
  unidadeDeContagem: string; textoDaUnidade: string; referencial: string; separador: string;
  /** Sem coluna de categoria: quem são os trabalhadores contados (o objeto da análise), escrito pela pessoa. */
  objeto: string;
  rotulos: Rotulos;
  /** Nomes editados pela pessoa: deixam de acompanhar a sugestão quando a coluna muda. */
  rotulosEditados: { unidade: boolean; grupo: boolean };
};

/** Escolhas iniciais: só os papéis reconhecidos por regra conclusiva (o mapeamento sugerido pelo /api/inspect). As
 * sugestões ficam no topo de cada seletor e nunca são escolhidas em silêncio. */
export function escolhasIniciais(sugerido: Record<string, string> | undefined): EscolhasDaPlanilha {
  const mapeamento: Mapeamento = {};
  for (const { papel } of PAPEIS) if (sugerido?.[papel]) mapeamento[papel] = sugerido[papel];
  return { mapeamento, escolhidos: [], unidadeDeContagem: "", textoDaUnidade: "", referencial: "", separador: "", objeto: "",
    rotulos: rotulosSugeridos(mapeamento.territory, mapeamento.grupo_territorial),
    rotulosEditados: { unidade: false, grupo: false } };
}

/** Escolher a coluna de um papel. Uma coluna representa um papel só: escolhida aqui, sai do papel anterior. Os nomes das
 * unidades e dos grupos acompanham a coluna enquanto a pessoa não os editar. */
export function escolherColuna(escolhas: EscolhasDaPlanilha, papel: Papel, coluna: string): EscolhasDaPlanilha {
  const mapeamento: Mapeamento = {};
  for (const [chave, valor] of Object.entries(escolhas.mapeamento) as [Papel, string][])
    if (valor && valor !== coluna && chave !== papel) mapeamento[chave] = valor;
  if (coluna) mapeamento[papel] = coluna;
  const escolhidos = [...new Set([...escolhas.escolhidos.filter(item => item !== papel && mapeamento[item]),
    ...(coluna ? [papel] : [])])];
  const contagemMudou = papel === "count" && coluna !== escolhas.mapeamento.count;
  const rotulos: Rotulos = {
    unidade: !escolhas.rotulosEditados.unidade && papel === "territory" ? sugerirRotulo(coluna) ?? { ...UNIDADE_GENERICA }
      : !escolhas.rotulosEditados.unidade && !mapeamento.territory ? { ...UNIDADE_GENERICA } : escolhas.rotulos.unidade,
    grupo: !mapeamento.grupo_territorial ? null
      : papel === "grupo_territorial" && (!escolhas.rotulosEditados.grupo || !escolhas.rotulos.grupo)
        ? sugerirRotulo(coluna) ?? { ...GRUPO_GENERICO } : escolhas.rotulos.grupo ?? sugerirRotulo(mapeamento.grupo_territorial)
        ?? { ...GRUPO_GENERICO },
  };
  return { ...escolhas, mapeamento, escolhidos, rotulos,
    ...(contagemMudou ? { unidadeDeContagem: "", textoDaUnidade: "" } : {}),
    rotulosEditados: { unidade: escolhas.rotulosEditados.unidade, grupo: mapeamento.grupo_territorial ? escolhas.rotulosEditados.grupo : false } };
}

/** A pessoa escreve o nome das unidades ou dos grupos (singular ou plural). */
export function editarRotulo(escolhas: EscolhasDaPlanilha, qual: "unidade" | "grupo", forma: keyof Rotulo,
  valor: string): EscolhasDaPlanilha {
  const atual = qual === "unidade" ? escolhas.rotulos.unidade : escolhas.rotulos.grupo ?? { ...GRUPO_GENERICO };
  const novo = { ...atual, [forma]: valor };
  return { ...escolhas, rotulos: qual === "unidade" ? { ...escolhas.rotulos, unidade: novo } : { ...escolhas.rotulos, grupo: novo },
    rotulosEditados: { ...escolhas.rotulosEditados, [qual]: true } };
}

/** O que ainda falta para começar a análise da planilha, na ordem dos campos. */
export function pendenciasDasColunas(escolhas: EscolhasDaPlanilha): string[] {
  const { mapeamento, rotulos } = escolhas;
  const faltam: string[] = [];
  if (!mapeamento.territory) faltam.push("Escolha a coluna da unidade territorial.");
  if (!mapeamento.period) faltam.push("Escolha a coluna do período.");
  if (!mapeamento.count) faltam.push("Escolha a coluna da quantidade.");
  else if (!escolhas.unidadeDeContagem) faltam.push("Diga o que a quantidade conta: pessoas, vínculos, postos ou outra unidade.");
  else if (escolhas.unidadeDeContagem === "outro" && !escolhas.textoDaUnidade.trim()) faltam.push("Descreva a unidade de contagem.");
  if (!mapeamento.category && !escolhas.objeto.trim())
    faltam.push("Diga quem são os trabalhadores contados, por exemplo, médicos ou enfermeiros.");
  if (!rotulos.unidade.singular.trim() || !rotulos.unidade.plural.trim())
    faltam.push("Diga como se chamam as unidades, no singular e no plural.");
  if (mapeamento.grupo_territorial && (!rotulos.grupo?.singular.trim() || !rotulos.grupo?.plural.trim()))
    faltam.push("Diga como se chamam os grupos, no singular e no plural.");
  return faltam;
}

const unidadeDaContagem = (escolhas: EscolhasDaPlanilha): Record<string, string> => ({
  ...(escolhas.mapeamento.count && escolhas.unidadeDeContagem ? { count_unit: escolhas.unidadeDeContagem } : {}),
  ...(escolhas.unidadeDeContagem === "outro" && escolhas.textoDaUnidade.trim()
    ? { custom_count_unit: escolhas.textoDaUnidade.trim() } : {}),
});
/** Sem coluna de categoria, o objeto da análise escrito pela pessoa vira a premissa `category_constant` (como na preparação
 * de antes): o motor exige saber quem são os trabalhadores contados. */
const objetoDaPlanilha = (escolhas: EscolhasDaPlanilha): Record<string, string> =>
  !escolhas.mapeamento.category && escolhas.objeto.trim() ? { category_constant: escolhas.objeto.trim() } : {};
const comCoordenadas = (escolhas: EscolhasDaPlanilha) => !!escolhas.mapeamento.latitude && !!escolhas.mapeamento.longitude;
/** O referencial informado vira a premissa `crs` só com latitude e longitude e só se for um dos admitidos. */
const referencialDaPlanilha = (escolhas: EscolhasDaPlanilha): Record<string, string> =>
  comCoordenadas(escolhas) && REFERENCIAIS_ACEITOS.includes(escolhas.referencial) ? { crs: escolhas.referencial } : {};

/** Mapeamento e opções da planilha para o pré-exame e para a conversa (rotas atuais do backend): o grupo territorial segue
 * em `hierarchy_columns` (nível superior 1), porque o pré-exame só aceita os papéis de semantic_bridge.ROLES. */
/** Papéis escolhidos pela pessoa no seletor (a escolha substitui a confirmação, D1), só os do pré-exame e com coluna. */
const papeisEscolhidos = (escolhas: EscolhasDaPlanilha) =>
  escolhas.escolhidos.filter(papel => PAPEIS_DO_PREEXAME.includes(papel) && escolhas.mapeamento[papel]);

export function contextoDaPlanilha(escolhas: EscolhasDaPlanilha): { mapping: Record<string, string>; options: Record<string, unknown> } {
  const mapping: Record<string, string> = {};
  for (const papel of PAPEIS_DO_PREEXAME) if (escolhas.mapeamento[papel]) mapping[papel] = escolhas.mapeamento[papel]!;
  const options: Record<string, unknown> = {
    confirmed_roles: papeisEscolhidos(escolhas),
    ...unidadeDaContagem(escolhas),
    ...objetoDaPlanilha(escolhas),
    ...referencialDaPlanilha(escolhas),
    ...(comCoordenadas(escolhas) && escolhas.separador ? { number_format: escolhas.separador } : {}),
    ...(escolhas.mapeamento.grupo_territorial
      ? { hierarchy_columns: { territorio_superior_1: escolhas.mapeamento.grupo_territorial } } : {}),
  };
  return { mapping, options };
}

/** Mapeamento da planilha para a conversa (28/10/2026): o do pré-exame com o papel `grupo_territorial`, que o backend da conversa
 * tira antes do pré-exame e usa para reconhecer os grupos pelo nome ("mostre o condado …"). Sem ele, nenhum grupo da planilha era
 * reconhecido na conversa. */
export function mapeamentoDaConversa(escolhas: EscolhasDaPlanilha): Record<string, string> {
  const { mapping } = contextoDaPlanilha(escolhas);
  return escolhas.mapeamento.grupo_territorial ? { ...mapping, grupo_territorial: escolhas.mapeamento.grupo_territorial } : mapping;
}

/** Mapeamento da planilha para o motor do gráfico (`FonteDados.mapping`): todos os papéis escolhidos, com o grupo. */
export function mapeamentoDaPlanilha(mapeamento: Mapeamento): Record<string, string> {
  const resultado: Record<string, string> = {};
  for (const { papel } of PAPEIS) if (mapeamento[papel]) resultado[papel] = mapeamento[papel]!;
  return resultado;
}

/** Premissas da planilha para o motor do gráfico (`FonteDados.premissas`). Só SIRGAS 2000 e WGS 84 valem como referencial:
 * com outro, ou sem saber qual é, nada é presumido, e a análise espacial fica indisponível, com o motivo. */
export function premissasDaPlanilha(escolhas: EscolhasDaPlanilha): Record<string, string | string[]> {
  const escolhidos = papeisEscolhidos(escolhas);
  return {
    // As colunas escolhidas pela pessoa valem como papéis estabelecidos no motor do gráfico, como no pré-exame (D1).
    ...(escolhidos.length ? { confirmed_roles: escolhidos } : {}),
    ...unidadeDaContagem(escolhas),
    ...objetoDaPlanilha(escolhas),
    ...referencialDaPlanilha(escolhas),
    ...(comCoordenadas(escolhas) && escolhas.separador ? { number_format: escolhas.separador } : {}),
  };
}

export type Disponibilidade = { familia: Familia; rotulo: string; disponivel: boolean; motivo: string };
type Capacidade = { status: string; reasons?: string[] };

/** O que a planilha permite, pelas capacidades do pré-exame do backend: a análise sem os dados necessários fica
 * indisponível, com o motivo. Os rótulos são os nomes padronizados das análises (os mesmos de NOMES_FAMILIAS, em
 * painelModel.ts, repetidos aqui porque este arquivo não importa outros módulos). A escolha pendente (por exemplo, a referência da análise espacial, feita no gráfico) não
 * torna a análise indisponível. Sem o pré-exame, a lista fica vazia. */
export function disponibilidadeDaPlanilha(capacidades: Record<string, Capacidade> | undefined, escolhas: EscolhasDaPlanilha,
  separadorMisto: boolean): Disponibilidade[] {
  if (!capacidades) return [];
  const livre = (operacao: string) => !!capacidades[operacao] && capacidades[operacao].status !== "unavailable";
  const motivo = (operacao: string) => capacidades[operacao]?.reasons?.[0] || "Os dados da planilha não permitem esta análise.";
  const item = (familia: Familia, rotulo: string, falta: string): Disponibilidade =>
    ({ familia, rotulo, disponivel: !falta, motivo: falta });
  const { mapeamento } = escolhas;
  const espacial = !mapeamento.latitude || !mapeamento.longitude ? "Faltam as colunas de latitude e longitude."
    : !REFERENCIAIS_ACEITOS.includes(escolhas.referencial)
      ? (escolhas.referencial
        ? "Só os referenciais SIRGAS 2000 e WGS 84 são admitidos; com outro, ou sem saber qual é, nada é presumido."
        : "Escolha o referencial das coordenadas.")
      : separadorMisto && !escolhas.separador ? "Escolha o separador decimal das coordenadas."
        : livre("spatial") ? "" : motivo("spatial");
  return [
    item("distribuicao", "Análise de Distribuição", livre("counts") || livre("density") ? "" : motivo("counts")),
    item("espacial", "Análise Espacial", espacial),
    item("tendencia", "Análise de Tendência", livre("temporal") ? "" : motivo("temporal")),
    item("rotatividade", "Análise de Rotatividade", !mapeamento.identity ? "Falta a coluna do identificador individual."
      : livre("rotation") ? "" : motivo("rotation")),
  ];
}

// ---------------------------------------------------------------------------------------------------------------------
// Histórico e exportação da sessão

/** Uma análise da sessão: o último estado guardado pela área, com a fonte em que foi calculada. */
export type AnaliseGuardada = { id: number; fonteChave: string; fonteNome: string; estado: EstadoSalvo };

/** Guarda o estado da análise em exibição: a mesma análise é atualizada; uma nova entra no fim da lista. */
export function registrarEstado(lista: AnaliseGuardada[], entrada: AnaliseGuardada): AnaliseGuardada[] {
  const indice = lista.findIndex(item => item.id === entrada.id);
  if (indice < 0) return [...lista, entrada];
  const proxima = [...lista];
  proxima[indice] = entrada;
  return proxima;
}

/** A análise anterior à atual, da mesma fonte ("volte ao resultado anterior"), ou null. */
export function analiseAnterior(lista: AnaliseGuardada[], atual: number, fonteChave: string): AnaliseGuardada | null {
  return lista.filter(item => item.fonteChave === fonteChave && item.id < atual)
    .reduce<AnaliseGuardada | null>((melhor, item) => !melhor || item.id > melhor.id ? item : melhor, null);
}

/** Hora em que a análise foi guardada ("14:05"); um texto que não é data fica como está. */
export function horaDe(quando: string): string {
  const data = new Date(quando);
  if (!quando || Number.isNaN(data.getTime())) return quando;
  return String(data.getHours()).padStart(2, "0") + ":" + String(data.getMinutes()).padStart(2, "0");
}

/** Identificador da sessão do resultado em exibição (`resposta.sessao`), para a conversa explicar o que está na tela. A resposta
 * guardada é a normalizada por painelApi (`resultId`); a do motor, como veio, traz `result_id`. Até 26/10/2026 só a segunda forma
 * era lida, e a conversa nunca recebia o resultado em exibição. */
export function resultadoDaSessao(estado: EstadoSalvo | null | undefined): string {
  const sessao = (estado?.resposta as { sessao?: { registrado?: unknown; resultId?: unknown; result_id?: unknown } } | null | undefined)?.sessao;
  if (sessao?.registrado !== true) return "";
  const id = typeof sessao.resultId === "string" ? sessao.resultId : sessao.result_id;
  return typeof id === "string" ? id : "";
}

function achatar(valor: unknown, prefixo: string, saida: Record<string, unknown>): Record<string, unknown> {
  if (valor && typeof valor === "object" && !Array.isArray(valor)) {
    for (const [chave, item] of Object.entries(valor)) achatar(item, prefixo ? prefixo + "." + chave : chave, saida);
  } else if (Array.isArray(valor)) {
    saida[prefixo] = valor.every(item => item === null || typeof item !== "object") ? valor.join(" | ") : JSON.stringify(valor);
  } else saida[prefixo] = valor;
  return saida;
}

/** CSV da análise em exibição (diálogo de Nova sessão): uma linha por item da resposta do motor, com todos os campos em
 * precisão integral (objetos viram colunas "campo.subcampo"). Texto que começaria uma fórmula leva um apóstrofo. */
export function csvDaResposta(resposta: unknown): string {
  const itens = (resposta as { itens?: unknown } | null)?.itens;
  if (!Array.isArray(itens) || !itens.length) return "";
  // Os grupos do mapa (quintis, só para pintar o mapa, 23/10/2026) não são valores da análise: ficam fora do CSV.
  const linhas = itens.map(item => {
    const { grupoMapa: _mapa, grupo_mapa: _mapaDoMotor, ...campos } = (item && typeof item === "object" ? item : {}) as Record<string, unknown>;
    return achatar(item && typeof item === "object" ? campos : item, "", {});
  });
  const colunas = [...new Set(linhas.flatMap(linha => Object.keys(linha)))];
  const celula = (valor: unknown) => {
    let texto = valor === null || valor === undefined ? "" : String(valor);
    if (typeof valor === "string" && /^[\s]*[=+@\-]/.test(texto)) texto = "'" + texto;
    return '"' + texto.replaceAll('"', '""') + '"';
  };
  return "﻿" + [colunas.map(celula).join(";"), ...linhas.map(linha => colunas.map(coluna => celula(linha[coluna])).join(";"))]
    .join("\r\n");
}

/** Data local do navegador (AAAA-MM-DD): o "hoje" da pessoa, com o fuso dela ("últimos N anos", AT-34). */
export function dataLocal(agora = new Date()): string {
  return agora.getFullYear() + "-" + String(agora.getMonth() + 1).padStart(2, "0") + "-" + String(agora.getDate()).padStart(2, "0");
}
