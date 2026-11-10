import { useEffect, useMemo, useState, type ReactNode, type Dispatch, type SetStateAction } from "react";
import { ArrowRight, ChevronRight, Filter, Layers3, Pencil, Search, X } from "lucide-react";
import MapaDosConjuntos, { type ConjuntoNoMapa } from "./MapaDosConjuntos";
import type { PainelConjuntoPedido, PainelMunicipios, PainelNivel, Rotulo } from "./painelApi";
import {
  BASE_VAZIA, RESSALVA_DA_SOMA, alternarUnidade, artigo, baseVazia, conjuntoDeEstados, descricaoDoConjunto, desmarcarGrupo,
  doTodo, formatarNumero, grupoDaUnidade, grupoDoIdDoEstado, grupoInteiro, maiuscula, marcadasNoGrupo, marcadasPorGrupo,
  marcarGrupo, nomeDaUnidade, nomeDoTodo, quantos, resumoDoUniverso, textoDaAgregacao, textoTodasAsUnidadesDoGrupo,
  todoInteiro, todosOs, unidadeMarcada, type GrupoInfo, type RotulosTerritoriais, type UnidadeDoCatalogo,
} from "./painelModel";

// Seleção de Territórios (comando V22, 9/11/2026, seções 2 e 3; antes, desde 07/11/2026, os modos "Marcar na lista", "Por critérios"
// e "Agrupar territórios" no alto da coluna da esquerda). À esquerda, sempre à vista, a busca e a árvore Brasil → região → estado →
// município, em linhas compactas: o Brasil com as regiões abaixo, recolhidas de início; em cada linha, a seta que abre e fecha (abrir
// nunca marca, marcar não abre, fechar não muda a seleção) separada da caixa que marca os descendentes, com a marcação parcial. Cada
// estado tem "Só o estado", que põe o estado na seleção como uma unidade (uma bolha, com a fonte estadual): os municípios dele saem da
// seleção e ficam esmaecidos e bloqueados enquanto ele estiver assim; as regiões e o Brasil têm "Só os estados". À direita,
// "Territórios selecionados": o mapa de prévia da seleção atual (o mesmo mini mapa de "Por critérios", sem estado próprio), a lista
// (os territórios individuais, os estados como unidade e os conjuntos) e as três ações: Confirmar seleção (vai à análise aberta),
// Aplicar critérios de seleção e Agrupar territórios selecionados, que abrem no lugar da lista; a árvore continua à vista. Não há
// uma segunda seleção: tudo lê a mesma escolha da área, e cada mudança é um passo do Desfazer. Nenhum nível é somado a outro
// (RQ-DAD-30). Numa planilha, os mesmos passos com a nomenclatura dela.
export type AcaoDaSelecao = "lista" | "criterios" | "agrupar";

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
/** Acima disto, a lista de um grupo ganha atalhos por letra inicial (a lista inteira continua à vista em "Todas"). */
const COM_LETRAS = 120;
const LIMITE_BUSCA = 20;
/** A lista à direita com milhares de territórios (seção 3): a síntese por grupo e, em cada um, só as primeiras etiquetas. */
const ETIQUETAS_POR_GRUPO = 8;
const GRUPOS_A_VISTA = 12;

type Props = {
  rotulos: RotulosTerritoriais;
  brasil: boolean;
  grupos: GrupoInfo[];
  unidades: UnidadeDoCatalogo[];
  total: number;
  /** O nível da seleção (municipios, estados ou, numa planilha com dois níveis, regioes). */
  nivel: PainelNivel;
  /** As seções da árvore: as regiões (na base do Brasil) ou os grupos de cima de uma planilha, com a seção de cada grupo. */
  secoesDaArvore?: { regioes: GrupoInfo[]; regiaoDoGrupo: (grupo: string) => string } | null;
  /** Numa planilha com dois níveis de grupo, os grupos de cima podem entrar como unidade ("Só a zona"). */
  regioesComoUnidade?: boolean;
  /** As regiões abertas na árvore, guardadas pela área: continuam abertas ao voltar à Seleção (a aba desmonta este painel). */
  regioesAbertas?: string[];
  onRegioesAbertas?: Dispatch<SetStateAction<string[]>>;
  base: PainelMunicipios;
  /** Os estados como unidade (ou, no nível regioes, os grupos de cima como unidade). */
  estados: string[];
  conjuntos: PainelConjuntoPedido[];
  /** O grupo com a lista aberta (só mostra a lista; não muda a seleção). */
  aberto: string | null;
  onAbrir: (grupo: string | null) => void;
  /** Coordenadas autorizadas para o mapa de prévia (do motor), só para desenhar; null enquanto não chegam. */
  coordenadas: Map<string, [number, number]> | null;
  /** Os totais individualizados (o Brasil inteiro, os estados inteiros), quando o motor já os devolveu. */
  totais?: ReactNode;
  regra?: { texto: string; onReaplicar: () => void } | null;
  onBase: (base: PainelMunicipios, acao: string) => void;
  /** "Só o estado" e "Só os estados": os grupos entram (ou saem) como unidade. */
  onEstadosComoUnidade: (grupos: string[], ativar: boolean, acao: string) => void;
  onRegioesComoUnidade?: (regioes: string[], ativar: boolean, acao: string) => void;
  onDesfazerConjunto: (id: string) => void;
  onEditarConjunto: (id: string) => void;
  valoresDosConjuntos?: Map<string, { quantidade: number | null; densidade: number | null }>;
  profissionais: string;
  /** A ação aberta à direita: a lista ou o formulário de critérios ou de agrupamento (`painelDaAcao`). */
  acao: AcaoDaSelecao;
  painelDaAcao?: ReactNode;
  /** Confirmar seleção (decisão 4): vai à análise aberta ("Confirmar seleção · Análise de Distribuição"). */
  onConfirmar: () => void;
  analiseAberta: string;
  /** Sem o motor (fonte sem a rota dos critérios), a ação de critérios não aparece. */
  onCriterios?: () => void;
  onAgrupar: () => void;
  /** Por que não dá para agrupar agora (nada selecionado, menos de dois territórios). */
  motivoDoAgrupar?: string | null;
};

export default function PainelTerritorios(p: Props) {
  const [consulta, setConsulta] = useState("");
  const [letra, setLetra] = useState("");
  const [raizAberta, setRaizAberta] = useState(true);
  const [regioesLocais, setRegioesLocais] = useState<string[]>([]);
  const regioesAbertas = p.regioesAbertas ?? regioesLocais;
  const setRegioesAbertas = p.onRegioesAbertas ?? setRegioesLocais;
  const [gruposExpandidos, setGruposExpandidos] = useState<string[]>([]);
  const [todosOsGruposAVista, setTodosOsGruposAVista] = useState(false);
  const unidade = p.rotulos.unidade, grupoRotulo = p.rotulos.grupo ?? { singular: "grupo", plural: "grupos" };
  const superior: Rotulo = p.rotulos.grupo_superior ?? { singular: "região", plural: "regiões", genero: "f" };
  const generoF = artigo(unidade, false) === "a", generoGrupoF = artigo(grupoRotulo, false) === "a";
  const superiorF = artigo(superior, false) === "a";
  const validas = useMemo(() => p.unidades.filter(item => !item.selection_reason), [p.unidades]);
  const porGrupo = useMemo(() => {
    const mapa = new Map<string, UnidadeDoCatalogo[]>();
    for (const item of validas) {
      const grupo = grupoDaUnidade(item);
      if (!mapa.has(grupo)) mapa.set(grupo, []);
      mapa.get(grupo)!.push(item);
    }
    for (const lista of mapa.values()) lista.sort((a, b) => comparar(a.name || a.label, b.name || b.label));
    return mapa;
  }, [validas]);
  const grupoDeId = useMemo(() => new Map(validas.map(item => [item.id, grupoDaUnidade(item)])), [validas]);
  const nomes = useMemo(() => new Map(validas.map(item => [item.id, item.name || item.label])), [validas]);
  const nomesCompletos = useMemo(() => new Map(validas.map(item => [item.id, nomeDaUnidade(item)])), [validas]);
  const porId = useMemo(() => new Map(validas.map(item => [item.id, item])), [validas]);
  const todasAsUnidades = useMemo(() => validas.map(item => item.id), [validas]);
  const idsDoGrupo = (grupo: string) => (porGrupo.get(grupo) || []).map(item => item.id);
  const todosOsGrupos = p.grupos.map(item => item.id);
  const temGrupos = p.grupos.length > 0;
  const nomeDoGrupo = (id: string) => p.grupos.find(item => item.id === id)?.nome || id;
  const nomeCompleto = (id: string) => nomesCompletos.get(id) || nomes.get(id) || id;
  const raiz = nomeDoTodo(p.brasil, p.rotulos);
  const secoes = p.secoesDaArvore ?? null;
  const regioesDaArvore = secoes?.regioes ?? [];
  const gruposDaSecao = (regiao: string) => p.grupos.filter(grupo => secoes?.regiaoDoGrupo(grupo.id) === regiao);
  // A lista de um estado aberta (pela árvore, pela bolha ou pela trilha) abre a região dele, que fica aberta depois que a lista fecha.
  useEffect(() => {
    const regiao = p.aberto && secoes ? secoes.regiaoDoGrupo(p.aberto) : "";
    if (regiao) setRegioesAbertas(atual => atual.includes(regiao) ? atual : [...atual, regiao]);
  }, [p.aberto]);
  // Os estados como unidade e, numa planilha com dois níveis, os grupos de cima como unidade (que valem sozinhos).
  const noNivelDeCima = p.nivel === "regioes";
  const comoUnidade = useMemo(() => new Set(noNivelDeCima ? [] : p.estados), [p.estados, noNivelDeCima]);
  const regioesUnidade = useMemo(() => new Set(noNivelDeCima ? p.estados : []), [p.estados, noNivelDeCima]);
  /** O grupo está como unidade (ele mesmo ou o grupo de cima dele): os municípios dele ficam bloqueados. */
  // Os estados membros de um conjunto de estados (comando V22) também ficam inteiros na análise: os municípios deles não entram.
  const emConjuntoDeEstados = useMemo(() => new Set(p.conjuntos.filter(conjuntoDeEstados).flatMap(conjunto => conjunto.membros.map(grupoDoIdDoEstado))),
    [p.conjuntos]);
  const bloqueado = (grupo: string) => comoUnidade.has(grupo) || emConjuntoDeEstados.has(grupo) ||
    (!!secoes && regioesUnidade.has(secoes.regiaoDoGrupo(grupo)));
  /** Por que os municípios de um estado ficam de fora: o estado como unidade ou num conjunto de estados. */
  const ondeEsta = (grupo: string) => {
    const nos = p.conjuntos.filter(conjunto => conjuntoDeEstados(conjunto) && conjunto.membros.includes("uf:" + grupo)).map(conjunto => conjunto.rotulo);
    return comoUnidade.has(grupo) || !nos.length ? "está na seleção como unidade" : "está no conjunto " + nos.join(", ");
  };
  // Os municípios que estão na seleção dentro de um conjunto (10/11/2026, conferência das capturas): a árvore diz quantos de cada
  // estado estão em conjuntos e marca cada um como "em conjunto", para eles não parecerem fora da seleção.
  const conjuntosDaUnidade = useMemo(() => {
    const mapa = new Map<string, string[]>();
    for (const conjunto of p.conjuntos) if (!conjuntoDeEstados(conjunto))
      for (const id of conjunto.membros) mapa.set(id, [...(mapa.get(id) ?? []), conjunto.rotulo]);
    return mapa;
  }, [p.conjuntos]);
  const emConjuntos = (ids: string[]) => ids.reduce((soma, id) => soma + (conjuntosDaUnidade.has(id) ? 1 : 0), 0);
  const textoEmConjuntos = (n: number) => n ? " · " + n.toLocaleString("pt-BR") + (n === 1 ? " em conjunto" : " em conjuntos") : "";
  const estado = grupoRotulo.singular;
  const soO = (rotulo: Rotulo) => "Só " + artigo(rotulo, false) + " " + rotulo.singular;
  const soOs = (rotulo: Rotulo) => "Só " + artigo(rotulo, true) + " " + rotulo.plural;
  const daRegiao = (regiao: GrupoInfo) => (p.brasil ? "da Região " : "de ") + regiao.nome;
  const deGrupo = (g: Pick<GrupoInfo, "nome" | "rotuloGrupo">) => textoTodasAsUnidadesDoGrupo(p.rotulos, g).replace(/^Tod[oa]s [oa]s /, "");
  const doGrupo = (g: Pick<GrupoInfo, "nome" | "rotuloGrupo">) => deGrupo(g).replace(/^\S+\s/, "");

  // ------------------------------------------------------------------------------------------ a caixa de um nível (raiz, região)
  /** A caixa de um nível marca os municípios dos grupos dele que não estão como unidade. Marcada: todos esses grupos inteiros;
   * em parte: algo marcado (ou um grupo como unidade); desligada: todos os grupos do nível como unidade. */
  const situacaoDe = (grupos: string[]) => {
    const livres = grupos.filter(grupo => !bloqueado(grupo));
    const inteiros = livres.filter(grupo => grupoInteiro(p.base, grupo)).length;
    const algum = livres.some(grupo => marcadasNoGrupo(p.base, grupo, idsDoGrupo(grupo)) > 0) || grupos.some(bloqueado);
    const marcado = livres.length > 0 && inteiros === livres.length;
    return { livres, marcado, parcial: !marcado && algum, desligado: !livres.length };
  };
  const alternarNivel = (grupos: string[], nome: string) => {
    const { livres, marcado } = situacaoDe(grupos);
    let base = p.base;
    if (!marcado && livres.length === p.grupos.length && !comoUnidade.size && !regioesUnidade.size) base = { todos: true, estados: [], ids: [] };
    else for (const grupo of livres) base = marcado ? desmarcarGrupo(base, grupo, idsDoGrupo(grupo), todosOsGrupos, todasAsUnidades)
      : marcarGrupo(base, grupo, idsDoGrupo(grupo));
    p.onBase(base, (marcado ? "Desmarcar " : "Marcar ") + nome);
  };
  const alternarUnidadeDaLista = (item: UnidadeDoCatalogo) => {
    const grupo = grupoDaUnidade(item);
    const marcada = unidadeMarcada(p.base, item.id, temGrupos ? grupo : "");
    p.onBase(alternarUnidade(p.base, item.id, temGrupos ? grupo : "", temGrupos ? idsDoGrupo(grupo) : [], todosOsGrupos, todasAsUnidades),
      (marcada ? "Desmarcar " : "Marcar ") + nomeDaUnidade(item));
  };
  const tirarUnidade = (id: string) => {
    const item = porId.get(id);
    const grupo = item ? grupoDaUnidade(item) : grupoDeId.get(id) ?? "";
    p.onBase(alternarUnidade(p.base, id, temGrupos ? grupo : "", temGrupos ? idsDoGrupo(grupo) : [], todosOsGrupos, todasAsUnidades),
      "Tirar " + nomeCompleto(id));
  };
  const alternarGrupo = (grupo: GrupoInfo) => {
    const ids = idsDoGrupo(grupo.id);
    if (grupoInteiro(p.base, grupo.id)) p.onBase(desmarcarGrupo(p.base, grupo.id, ids, todosOsGrupos, todasAsUnidades), "Desmarcar " + deGrupo(grupo));
    else p.onBase(marcarGrupo(p.base, grupo.id, ids), "Marcar " + todosOs(unidade) + " " + doGrupo(grupo));
  };
  const tirarGrupo = (g: GrupoInfo) => p.onBase(desmarcarGrupo(p.base, g.id, idsDoGrupo(g.id), todosOsGrupos, todasAsUnidades), "Tirar " + deGrupo(g));
  /** "Só o estado" de um grupo: liga ou desliga. */
  const alternarComoUnidade = (grupo: GrupoInfo) => {
    const ativo = comoUnidade.has(grupo.id);
    p.onEstadosComoUnidade([grupo.id], !ativo, (ativo ? "Tirar " : "Só ") + (ativo ? grupo.nome + " (" + estado + ")" : artigo(grupoRotulo, false) + " " + estado + ": " + grupo.nome));
  };
  /** "Só os estados" de um nível: todos os grupos dele como unidade (ou, se já estão, nenhum). */
  const alternarTodosComoUnidade = (grupos: string[], nome: string) => {
    const todos = grupos.length > 0 && grupos.every(grupo => comoUnidade.has(grupo));
    p.onEstadosComoUnidade(grupos, !todos, (todos ? "Tirar " + artigo(grupoRotulo, true) + " " + grupoRotulo.plural + " como unidade " : soOs(grupoRotulo) + " ") + nome);
  };

  // ------------------------------------------------------------------------------------------ partes da árvore
  const seta = (aberta: boolean, rotulo: string, testid: string, alternar: () => void, controla?: string) =>
    <button type="button" data-testid={testid} className="analise-no-seta" aria-expanded={aberta} aria-controls={aberta ? controla : undefined}
      aria-label={rotulo} title={rotulo} onClick={alternar}><ChevronRight size={16} aria-hidden="true" className="analise-no-seta-icone"/></button>;
  const botaoComoUnidade = (ativo: boolean, rotulo: string, testid: string, acao: () => void, descricao: string) =>
    <button type="button" data-testid={testid} aria-pressed={ativo} className="analise-so-estado" title={descricao} onClick={acao}>{rotulo}</button>;

  const caixaDaUnidade = (item: UnidadeDoCatalogo, testid: string, comGrupo = false) => {
    const grupo = grupoDaUnidade(item);
    const preso = temGrupos && bloqueado(grupo);
    const nosConjuntos = conjuntosDaUnidade.get(item.id);
    return <li key={item.id} data-testid={testid} data-id={item.id} data-bloqueada={preso ? "true" : undefined}
      data-conjunto={nosConjuntos ? nosConjuntos.join(", ") : undefined}>
      <label className={"analise-caixa" + (preso ? " analise-caixa-bloqueada" : "")}
        title={preso ? nomeDoGrupo(grupo) + " " + ondeEsta(grupo) + "; " + artigo(unidade, true) + " " + unidade.plural + " del" +
          (generoGrupoF ? "a" : "e") + " ficam de fora enquanto isso." : undefined}>
        <input type="checkbox" checked={!preso && unidadeMarcada(p.base, item.id, temGrupos ? grupo : "")} disabled={preso}
          onChange={() => alternarUnidadeDaLista(item)}/>
        <span className="min-w-0 flex-1">{comGrupo ? nomeDaUnidade(item) : item.name || item.label}</span>
        {nosConjuntos && <span data-testid="analise-unidade-em-conjunto" className="analise-marca-grupo shrink-0"
          title={"Na seleção, dentro d" + (nosConjuntos.length === 1 ? "o conjunto " : "os conjuntos ") + nosConjuntos.join(", ")}>em conjunto</span>}
        {comGrupo && temGrupos ? <span className="shrink-0 text-[12px] text-slate-500">{nomeDoGrupo(grupo)}</span>
          : item.code && <span className="shrink-0 text-[12px] text-slate-500">{item.code}</span>}
      </label>
    </li>;
  };

  const listaDeUnidades = (lista: UnidadeDoCatalogo[], grupo: GrupoInfo | null) => {
    const letras = lista.length > COM_LETRAS ? [...new Set(lista.map(item => sem((item.name || item.label).charAt(0)).toUpperCase()))].sort() : [];
    const visiveis = letra && letras.length ? lista.filter(item => sem((item.name || item.label).charAt(0)).toUpperCase() === letra) : lista;
    const ids = lista.map(item => item.id);
    const preso = !!grupo && bloqueado(grupo.id);
    const n = preso ? 0 : grupo ? marcadasNoGrupo(p.base, grupo.id, ids) : lista.filter(item => unidadeMarcada(p.base, item.id, "")).length;
    const rotulo = grupo ? maiuscula(deGrupo(grupo)) : maiuscula(unidade.plural) + " " + doTodo(p.brasil, p.rotulos);
    const semLista = !grupo && !lista.length;
    const todasMarcadas = grupo ? n === lista.length : p.base.todos || (lista.length > 0 && n === lista.length);
    return <div data-testid="analise-grupo-unidades" data-id={grupo?.id ?? ""} className="analise-unidades">
      <p className="text-xs text-slate-700" role="status"><strong className="text-ink">{rotulo}</strong>: {preso
        ? (generoGrupoF ? "a " : "o ") + grupoRotulo.singular + " " + ondeEsta(grupo!.id) + "; " + artigo(unidade, true) + " " + unidade.plural +
          " del" + (generoGrupoF ? "a" : "e") + " ficam de fora enquanto isso."
        : semLista ? (p.base.todos ? (generoF ? "todas marcadas" : "todos marcados") : (generoF ? "nenhuma marcada" : "nenhum marcado")) +
          ". A lista " + (generoF ? "das " : "dos ") + unidade.plural + " não está disponível; a análise pode usar " +
          (p.rotulos.todo?.nome?.trim() ? todoInteiro(false, p.rotulos) : "toda a base") + "."
          : n + " de " + quantos(lista.length, unidade) + " marcad" + (generoF ? "as" : "os") +
            (emConjuntos(ids) ? "; " + emConjuntos(ids).toLocaleString("pt-BR") + (emConjuntos(ids) === 1 ? " em conjunto" : " em conjuntos") : "") + "."}</p>
      {!preso && <div className="analise-territorios-coletivos" role="group" aria-label="Marcar ou desmarcar de uma vez">
        <button type="button" data-testid="analise-marcar-todos" className="analise-botao-secundario" disabled={todasMarcadas}
          onClick={() => grupo ? p.onBase(marcarGrupo(p.base, grupo.id, ids), "Marcar " + todosOs(unidade) + " " + doGrupo(grupo))
            : p.onBase({ todos: true, estados: [], ids: [] }, "Marcar " + todosOs(unidade))}>
          {"Marcar " + todosOs(unidade) + (grupo ? " " + doGrupo(grupo) : "")}</button>
        <button type="button" data-testid="analise-desmarcar-todos" className="analise-botao-secundario" disabled={n === 0 && (!!grupo || !p.base.todos)}
          onClick={() => grupo ? p.onBase(desmarcarGrupo(p.base, grupo.id, ids, todosOsGrupos, todasAsUnidades), "Desmarcar " + deGrupo(grupo))
            : p.onBase({ ...BASE_VAZIA }, "Desmarcar " + artigo(unidade, true) + " " + unidade.plural)}>
          {"Desmarcar " + artigo(unidade, true) + " " + (grupo ? deGrupo(grupo) : unidade.plural)}</button>
      </div>}
      {letras.length > 0 && <div className="flex flex-wrap gap-1" role="group" aria-label="Atalho pela letra inicial">
        <button type="button" aria-pressed={!letra} className="analise-letra" onClick={() => setLetra("")}>Todas</button>
        {letras.map(item => <button key={item} type="button" aria-pressed={letra === item} className="analise-letra" onClick={() => setLetra(item)}>{item}</button>)}
      </div>}
      <ul className="analise-unidades-lista analise-no-unidades" aria-label={rotulo}>{visiveis.map(item => caixaDaUnidade(item, "analise-unidade"))}</ul>
    </div>;
  };

  /** Uma linha de estado: a seta, a caixa (inteiro, em parte ou nada; desligada com o estado como unidade), o nome e a contagem, e
   * "Só o estado". A lista dos municípios abre abaixo, numa caixa com rolagem própria, para a próxima linha continuar perto. */
  const linhaDoGrupo = (grupo: GrupoInfo, testid: string) => {
    const ids = idsDoGrupo(grupo.id), total = grupo.unidades || ids.length;
    const unidadeAtiva = comoUnidade.has(grupo.id), preso = bloqueado(grupo.id);
    const inteiro = !preso && grupoInteiro(p.base, grupo.id), n = preso ? 0 : marcadasNoGrupo(p.base, grupo.id, ids), parcial = !inteiro && n > 0;
    const aberto = p.aberto === grupo.id && testid === "analise-grupo";
    const idDaLista = "analise-lista-" + grupo.id.replace(/[^A-Za-z0-9_-]/g, "_");
    const contagem = unidadeAtiva ? "como unidade" + (p.brasil ? " · fonte estadual" : "")
      : emConjuntoDeEstados.has(grupo.id) ? ondeEsta(grupo.id).replace(/^está /, "")
      : preso ? "como unidade, pel" + (superiorF ? "a " : "o ") + superior.singular
        : inteiro ? (generoF ? "todas as " : "todos os ") + total.toLocaleString("pt-BR") + " " + (total === 1 ? unidade.singular : unidade.plural)
          : n ? n.toLocaleString("pt-BR") + " de " + quantos(total, unidade) : quantos(total, unidade);
    const nosConjuntos = preso ? 0 : emConjuntos(ids);
    const verTexto = (aberto ? "Fechar a lista " + (generoF ? "das " : "dos ") : "Ver " + (generoF ? "as " : "os ")) + quantos(total, unidade) + " " + doGrupo(grupo);
    return <li key={grupo.id} data-testid={testid} data-id={grupo.id} data-marcadas={n} data-em-conjuntos={nosConjuntos}
      data-aberto={aberto ? "true" : "false"}
      data-unidade={unidadeAtiva ? "true" : "false"} data-situacao={unidadeAtiva ? "unidade" : inteiro ? "inteiro" : parcial ? "parcial" : "nenhum"}
      className={"analise-no analise-no-grupo" + (aberto ? " analise-no-aberto" : "")}>
      <div className="analise-no-linha">
        {seta(aberto, verTexto, testid === "analise-grupo" ? "analise-grupo-ver" : "analise-busca-grupo-ver",
          () => { setConsulta(""); p.onAbrir(aberto ? null : grupo.id); }, idDaLista)}
        <label className="analise-caixa analise-no-caixa">
          <input type="checkbox" data-testid="analise-grupo-todos" checked={inteiro} disabled={preso}
            ref={elemento => { if (elemento) elemento.indeterminate = parcial; }}
            aria-label={textoTodasAsUnidadesDoGrupo(p.rotulos, grupo)} onChange={() => alternarGrupo(grupo)}/>
          <span className="analise-no-texto">
            <span className="analise-no-nome">{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span>
            <span data-testid="analise-grupo-contagem" className="analise-no-contagem">{contagem}{textoEmConjuntos(nosConjuntos)}</span>
          </span>
        </label>
        {botaoComoUnidade(unidadeAtiva, soO(grupoRotulo), "analise-grupo-so-estado",
          () => alternarComoUnidade(grupo), unidadeAtiva ? "Tirar " + grupo.nome + " da seleção como unidade; " + artigo(unidade, true) + " " +
            unidade.plural + " del" + (generoGrupoF ? "a" : "e") + " ficam livres, sem nenhum marcado."
            : grupo.nome + " entra na seleção como uma unidade" + (p.brasil ? ", com a fonte estadual" : "") + "; " + artigo(unidade, true) + " " +
              unidade.plural + " del" + (generoGrupoF ? "a" : "e") + " saem da seleção.")}
      </div>
      {aberto && <div id={idDaLista} className="analise-no-filhos">
        {listaDeUnidades(porGrupo.get(grupo.id) || [], grupo)}
        <button type="button" data-testid="analise-grupo-voltar" className="analise-botao-secundario analise-voltar-grupos" onClick={() => p.onAbrir(null)}>
          Fechar a lista {generoF ? "das " : "dos "}{unidade.plural} {doGrupo(grupo)}</button>
      </div>}
    </li>;
  };

  /** Uma região (ou o grupo de cima de uma planilha): a seta, a caixa e "Só os estados"; numa planilha, também "Só a zona". */
  const linhaDaRegiao = (regiao: GrupoInfo) => {
    const grupos = gruposDaSecao(regiao.id), ids = grupos.map(grupo => grupo.id);
    const aberta = regioesAbertas.includes(regiao.id) || (!!p.aberto && ids.includes(p.aberto));
    const s = situacaoDe(ids);
    const total = grupos.reduce((soma, grupo) => soma + (grupo.unidades || idsDoGrupo(grupo.id).length), 0);
    const todosUnidade = ids.length > 0 && ids.every(id => comoUnidade.has(id));
    const regiaoUnidade = regioesUnidade.has(regiao.id);
    const idDaSecao = "analise-regiao-" + regiao.id.replace(/[^A-Za-z0-9_-]/g, "_");
    return <li key={regiao.id} data-testid="analise-regiao" data-id={regiao.id} data-aberta={aberta ? "true" : "false"}
      data-situacao={regiaoUnidade ? "unidade" : s.marcado ? "inteiro" : s.parcial ? "parcial" : "nenhum"} className="analise-no analise-no-regiao">
      <div className="analise-no-linha">
        {seta(aberta, (aberta ? "Fechar " : "Abrir ") + regiao.nome, "analise-regiao-ver",
          () => {
            // Recolher a região fecha também a lista aberta de um estado dela (senão a região continuaria aberta por ela).
            if (aberta && p.aberto && ids.includes(p.aberto)) p.onAbrir(null);
            setRegioesAbertas(atual => aberta ? atual.filter(id => id !== regiao.id) : [...atual, regiao.id]);
          }, idDaSecao)}
        <label className="analise-caixa analise-no-caixa">
          <input type="checkbox" data-testid="analise-regiao-todos" checked={s.marcado} disabled={s.desligado}
            ref={elemento => { if (elemento) elemento.indeterminate = s.parcial; }}
            aria-label={maiuscula(todosOs(unidade)) + " " + daRegiao(regiao)} onChange={() => alternarNivel(ids, todosOs(unidade) + " " + daRegiao(regiao))}/>
          <span className="analise-no-texto">
            <span className="analise-no-nome">{regiao.nome}</span>
            <span data-testid="analise-regiao-contagem" className="analise-no-contagem">{regiaoUnidade ? "como unidade" :
              (p.brasil ? ids.length + (ids.length === 1 ? " UF" : " UFs") : quantos(ids.length, grupoRotulo)) + " · " + quantos(total, unidade)}</span>
          </span>
        </label>
        <span className="analise-no-acoes">
          {p.regioesComoUnidade && p.onRegioesComoUnidade && botaoComoUnidade(regiaoUnidade, soO(superior), "analise-regiao-so-regiao",
            () => p.onRegioesComoUnidade!([regiao.id], !regiaoUnidade, (regiaoUnidade ? "Tirar " : "Só ") + regiao.nome),
            regiao.nome + " como uma unidade: não se mistura com outros níveis.")}
          {botaoComoUnidade(todosUnidade, soOs(grupoRotulo), "analise-regiao-so-estados", () => alternarTodosComoUnidade(ids, daRegiao(regiao)),
            maiuscula(artigo(grupoRotulo, true)) + " " + grupoRotulo.plural + " " + daRegiao(regiao) + " como unidade, cada " +
              (generoGrupoF ? "uma" : "um") + " numa bolha" + (p.brasil ? ", com a fonte estadual" : "") + ".")}
        </span>
      </div>
      {aberta && <ul id={idDaSecao} className="analise-no-filhos analise-no-lista" aria-label={maiuscula(grupoRotulo.plural) + " " + daRegiao(regiao)}>
        {grupos.map(grupo => linhaDoGrupo(grupo, "analise-grupo"))}
      </ul>}
    </li>;
  };

  // ------------------------------------------------------------------------------------------ busca
  const termo = sem(consulta.trim());
  const busca = useMemo(() => {
    if (!termo) return null;
    const grupos = temGrupos ? p.grupos.filter(g => sem(g.nome + " " + g.sigla).includes(termo)).slice(0, 8) : [];
    const unidades = validas.filter(item => sem(item.name + " " + item.code + " " + item.label).includes(termo)).slice(0, LIMITE_BUSCA);
    return { grupos, unidades };
  }, [termo, temGrupos, p.grupos, validas]);
  const placeholder = temGrupos ? "Buscar " + unidade.singular + " ou " + grupoRotulo.singular : "Buscar " + unidade.singular;
  const rotuloDaBusca = "Buscar pelo nome: " + (temGrupos ? unidade.plural + " ou " + grupoRotulo.plural : unidade.plural);

  // O resumo do universo carregado (seção 2): "5.570 municípios | 27 UFs", do que a base tem, nunca fixo.
  const universo = p.total.toLocaleString("pt-BR") + " " + (p.total === 1 ? unidade.singular : unidade.plural) +
    (temGrupos ? " | " + p.grupos.length.toLocaleString("pt-BR") + " " + (p.brasil ? (p.grupos.length === 1 ? "UF" : "UFs") : (p.grupos.length === 1 ? grupoRotulo.singular : grupoRotulo.plural)) : "");
  const arvore = (() => {
    if (busca) {
      const nada = !busca.grupos.length && !busca.unidades.length;
      return <div data-testid="analise-busca-resultado" className="analise-unidades">
        {nada ? <p className="text-xs text-slate-600">Nada encontrado com “{consulta.trim()}”.</p> : <>
          {busca.grupos.length > 0 && <ul className="analise-no-lista"
            aria-label={maiuscula(grupoRotulo.plural) + " encontrad" + (generoGrupoF ? "as" : "os")}>
            {busca.grupos.map(grupo => linhaDoGrupo(grupo, "analise-busca-grupo"))}
          </ul>}
          {busca.unidades.length > 0 && <ul className="analise-unidades-lista" aria-label="Resultado da busca">
            {busca.unidades.map(item => caixaDaUnidade(item, "analise-busca-item", true))}
          </ul>}
        </>}
      </div>;
    }
    if (!temGrupos) return listaDeUnidades([...validas].sort((a, b) => comparar(a.name || a.label, b.name || b.label)), null);
    const s = situacaoDe(todosOsGrupos);
    const todosUnidade = todosOsGrupos.length > 0 && todosOsGrupos.every(id => comoUnidade.has(id));
    return <div data-testid="analise-arvore" className="analise-arvore">
      <div data-testid="analise-raiz" data-marcado={s.marcado ? "true" : s.parcial ? "parcial" : "false"} className="analise-no analise-no-raiz">
        <div className="analise-no-linha">
          {seta(raizAberta, (raizAberta ? "Fechar " : "Abrir ") + raiz, "analise-raiz-ver", () => setRaizAberta(atual => !atual), "analise-arvore-secoes")}
          <label className="analise-caixa analise-no-caixa">
            <input type="checkbox" data-testid="analise-raiz-caixa" checked={s.marcado} disabled={s.desligado}
              ref={elemento => { if (elemento) elemento.indeterminate = s.parcial; }}
              aria-label={raiz + ": " + todosOs(unidade)} onChange={() => alternarNivel(todosOsGrupos, todosOs(unidade) + " " + doTodo(p.brasil, p.rotulos))}/>
            <span className="analise-no-texto">
              <span className="analise-no-nome analise-raiz-nome">{raiz}</span>
              <span data-testid="analise-raiz-universo" className="analise-no-contagem">{universo}</span>
            </span>
          </label>
          <span className="analise-no-acoes">
            {botaoComoUnidade(todosUnidade, soOs(grupoRotulo), "analise-raiz-so-estados", () => alternarTodosComoUnidade(todosOsGrupos, doTodo(p.brasil, p.rotulos)),
              maiuscula(todosOs(grupoRotulo)) + " como unidade, cada " + (generoGrupoF ? "uma" : "um") + " numa bolha" + (p.brasil ? ", com a fonte estadual" : "") + ".")}
          </span>
        </div>
        {raizAberta && <div id="analise-arvore-secoes" className="analise-no-filhos">
          {regioesDaArvore.length ? <ul data-testid="analise-regioes" className="analise-no-lista" aria-label={maiuscula(superior.plural)}>
            {regioesDaArvore.map(linhaDaRegiao)}
          </ul> : <ul className="analise-no-lista" aria-label={maiuscula(grupoRotulo.plural)}>
            {p.grupos.map(grupo => linhaDoGrupo(grupo, "analise-grupo"))}
          </ul>}
        </div>}
      </div>
    </div>;
  })();

  // ------------------------------------------------------------------------------------------ territórios selecionados (à direita)
  const marcadas = useMemo(() => marcadasPorGrupo(p.base, { grupos: p.grupos, unidadesDoGrupo: idsDoGrupo, nomes,
    grupoDe: id => grupoDeId.get(id) ?? "", todas: todasAsUnidades }), [p.base, p.grupos, nomes, grupoDeId, todasAsUnidades, porGrupo]);
  const resumo = resumoDoUniverso({ nivel: p.nivel, base: p.base, estados: p.estados, conjuntos: p.conjuntos.length, grupos: p.grupos,
    regioes: regioesDaArvore, rotulos: p.rotulos, total: p.total, grupoDe: id => grupoDeId.get(id) ?? "", nomes: nomesCompletos });
  const vazio = baseVazia(p.base) && !p.estados.length && !p.conjuntos.length;
  const nomeDoEstado = (id: string) => nomeDoGrupo(grupoDoIdDoEstado(id) || id);
  const membrosParaDesenhar = (conjunto: PainelConjuntoPedido) => conjuntoDeEstados(conjunto)
    ? conjunto.membros.flatMap(id => idsDoGrupo(grupoDoIdDoEstado(id))) : conjunto.membros;
  const nomeDoMembro = (id: string) => id.startsWith("uf:") ? nomeDoEstado(id) : nomeCompleto(id);
  // O mapa de prévia (seção 3): a seleção atual, sem estado próprio — os territórios individuais em destaque, os estados como unidade
  // e os conjuntos com o contorno e o nome (a dica do contorno lista todos os integrantes), e, de fundo, os estados tocados.
  const mapaDaSelecao = useMemo(() => {
    if (!p.coordenadas) return null;
    const individuais = p.base.todos ? todasAsUnidades : validas.filter(item => unidadeMarcada(p.base, item.id, grupoDaUnidade(item))).map(item => item.id);
    const estadosNoMapa: ConjuntoNoMapa[] = (noNivelDeCima ? [] : p.estados).map(grupo => ({ id: "uf:" + grupo,
      nome: nomeDoGrupo(grupo) + " (" + estado + ")", membros: idsDoGrupo(grupo),
      descricao: nomeDoGrupo(grupo) + " (" + estado + ")" + (p.brasil ? " · fonte estadual (médicos únicos no estado)" : "") }));
    const regioesNoMapa: ConjuntoNoMapa[] = (noNivelDeCima ? p.estados : []).map(regiao => ({ id: "rg:" + regiao,
      nome: (regioesDaArvore.find(item => item.id === regiao)?.nome ?? regiao) + " (" + superior.singular + ")",
      membros: gruposDaSecao(regiao).flatMap(grupo => idsDoGrupo(grupo.id)) }));
    const conjuntos: ConjuntoNoMapa[] = p.conjuntos.map(conjunto => ({ id: conjunto.id, nome: conjunto.rotulo, membros: membrosParaDesenhar(conjunto),
      descricao: descricaoDoConjunto(conjunto.rotulo, conjunto.membros, nomeDoMembro) + " · " + textoDaAgregacao(conjuntoDeEstados(conjunto)) }));
    const tocados = new Set([...individuais.map(id => grupoDeId.get(id) ?? ""), ...(noNivelDeCima ? [] : p.estados),
      ...conjuntos.flatMap(conjunto => conjunto.membros.map(id => grupoDeId.get(id) ?? ""))]);
    const fundo = temGrupos ? validas.filter(item => tocados.has(grupoDaUnidade(item))).map(item => item.id) : todasAsUnidades;
    return { individuais, conjuntos: [...estadosNoMapa, ...regioesNoMapa, ...conjuntos], fundo };
  }, [p.coordenadas, p.base, p.estados, p.conjuntos, validas, noNivelDeCima, porGrupo]);

  const linhasDosGrupos = marcadas.filter(item => !(item.grupo && bloqueado(item.grupo)));
  const gruposAVista = todosOsGruposAVista ? linhasDosGrupos : linhasDosGrupos.slice(0, GRUPOS_A_VISTA);
  const lista = (() => {
    if (vazio) return <p className="analise-selecionados-vazio">Nenhum território selecionado ainda: marque na lista ({p.brasil ? "o Brasil, uma região, " : ""}
      {generoGrupoF ? "uma " : "um "}{grupoRotulo.singular} inteir{generoGrupoF ? "a" : "o"}, {unidade.plural} ou “{soO(grupoRotulo)}”) ou use a busca.</p>;
    return <ul className="analise-selecionados-lista">
      {p.base.todos && !comoUnidade.size && <li data-testid="analise-selecionado" data-grupo="todos" className="analise-selecionado-grupo">
        <div className="analise-selecionado-cabeca">
          <span className="min-w-0"><strong className="text-ink">{maiuscula(todosOs(unidade))}{p.brasil ? " do Brasil" : ""}</strong> ({p.total.toLocaleString("pt-BR")})</span>
          <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + todosOs(unidade)}
            onClick={() => p.onBase({ ...BASE_VAZIA }, "Tirar " + todosOs(unidade))}><X size={13} aria-hidden="true"/></button>
        </div>
      </li>}
      {!p.base.todos && gruposAVista.map(item => {
        const g = p.grupos.find(grupo => grupo.id === item.grupo);
        return <GrupoNaLista key={item.grupo || "unidades"} grupo={item} info={g} rotulo={item.nome || (temGrupos ? "Sem " + grupoRotulo.singular : maiuscula(unidade.plural))}
          unidade={unidade} generoF={generoF} nomeDe={id => nomes.get(id) || nomeCompleto(id)} nomeCompleto={nomeCompleto}
          emConjuntos={textoEmConjuntos(item.grupo ? emConjuntos(idsDoGrupo(item.grupo)) : emConjuntos(todasAsUnidades))}
          onTirarGrupo={g ? () => tirarGrupo(g) : undefined} rotuloTirarGrupo={g ? "Tirar " + deGrupo(g) : ""} onTirar={tirarUnidade}/>;
      })}
      {!p.base.todos && linhasDosGrupos.length > GRUPOS_A_VISTA && <li><button type="button" data-testid="analise-selecionados-mais" className="analise-link"
        aria-expanded={todosOsGruposAVista} onClick={() => setTodosOsGruposAVista(atual => !atual)}>{todosOsGruposAVista ? "Mostrar menos"
          : "Ver mais " + quantos(linhasDosGrupos.length - GRUPOS_A_VISTA, grupoRotulo)}</button></li>}
      {(noNivelDeCima ? [] : p.estados).map(grupo => <li key={"uf:" + grupo} data-testid="analise-selecionado-estado" data-id={grupo}
        className="analise-selecionado-grupo analise-selecionado-estado">
        <div className="analise-selecionado-cabeca">
          <span className="min-w-0"><strong className="text-ink">{nomeDoGrupo(grupo)} ({estado})</strong>{" "}
            <span className="text-slate-600">· {p.brasil ? "uma bolha, com a fonte estadual" : "uma bolha, pel" + artigo(unidade, true) + " " + unidade.plural + " del" + (generoGrupoF ? "a" : "e")}</span></span>
          <button type="button" data-testid="analise-selecionado-tirar-estado" className="analise-icone analise-icone-pequeno"
            aria-label={"Tirar " + nomeDoGrupo(grupo) + " (" + estado + ")"} onClick={() => p.onEstadosComoUnidade([grupo], false, "Tirar " + nomeDoGrupo(grupo) + " (" + estado + ")")}>
            <X size={13} aria-hidden="true"/></button>
        </div>
      </li>)}
      {noNivelDeCima && p.estados.map(regiao => <li key={"rg:" + regiao} data-testid="analise-selecionado-regiao" data-id={regiao}
        className="analise-selecionado-grupo analise-selecionado-estado">
        <div className="analise-selecionado-cabeca">
          <span className="min-w-0"><strong className="text-ink">{regioesDaArvore.find(item => item.id === regiao)?.nome ?? regiao} ({superior.singular})</strong></span>
          {p.onRegioesComoUnidade && <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + regiao}
            onClick={() => p.onRegioesComoUnidade!([regiao], false, "Tirar " + regiao)}><X size={13} aria-hidden="true"/></button>}
        </div>
      </li>)}
      {p.conjuntos.length > 0 && <li data-testid="analise-selecionado" data-grupo="conjuntos" className="analise-selecionado-grupo">
        <ul className="analise-grupos-agregados" aria-label={p.conjuntos.length === 1 ? "Conjunto" : "Conjuntos"}>
          {p.conjuntos.map(conjunto => {
            const valores = p.valoresDosConjuntos?.get(conjunto.id);
            const deEstados = conjuntoDeEstados(conjunto);
            return <li key={conjunto.id} data-testid="analise-selecionado-conjunto" data-id={conjunto.id} data-nivel={deEstados ? "estados" : "municipios"}
              className="analise-grupo-agregado">
              <div className="min-w-0">
                <span data-testid="analise-selecionado-conjunto-texto">
                  <strong className="text-ink">{conjunto.rotulo}</strong> · <span className="analise-marca-grupo">conjunto</span> ·{" "}
                  {quantos(conjunto.membros.length, deEstados ? grupoRotulo : unidade)}
                  {typeof valores?.quantidade === "number" && " · " + valores.quantidade.toLocaleString("pt-BR") + " " + p.profissionais}
                  {typeof valores?.densidade === "number" && " · " + formatarNumero(valores.densidade) + " por mil"}</span>
                <details className="analise-conjunto-membros"><summary>Ver {deEstados ? (generoGrupoF ? "as " : "os ") + grupoRotulo.plural : (generoF ? "as " : "os ") + unidade.plural}</summary>
                  <span data-testid="analise-selecionado-conjunto-membros">{descricaoDoConjunto(conjunto.rotulo, conjunto.membros, nomeDoMembro)}. {maiuscula(textoDaAgregacao(deEstados))}.</span>
                </details>
              </div>
              <span className="analise-grupo-agregado-acoes">
                {!deEstados && <button type="button" data-testid="analise-selecionado-conjunto-editar" className="analise-icone analise-icone-pequeno"
                  aria-label={"Editar o conjunto " + conjunto.rotulo} onClick={() => p.onEditarConjunto(conjunto.id)}><Pencil size={13} aria-hidden="true"/></button>}
                <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Desfazer o conjunto " + conjunto.rotulo}
                  onClick={() => p.onDesfazerConjunto(conjunto.id)}><X size={13} aria-hidden="true"/></button>
              </span>
            </li>;
          })}
        </ul>
        <p data-testid="analise-selecionado-ressalva" className="analise-ressalva">{RESSALVA_DA_SOMA}</p>
      </li>}
    </ul>;
  })();

  return <section data-testid="analise-territorios" data-nivel={p.nivel} data-acao={p.acao} aria-labelledby="analise-territorios-titulo"
    className="analise-territorios">
    <h3 id="analise-territorios-titulo" tabIndex={-1} className="sr-only">Territórios</h3>
    <div className="analise-territorios-colunas">
      <div data-testid="analise-territorios-lista" className="analise-territorios-lista">
        <p data-testid="analise-territorios-instrucao" className="analise-territorios-instrucao">{temGrupos
          ? "A seta abre a lista; a caixa marca " + artigo(unidade, true) + " " + unidade.plural + ". “" + soO(grupoRotulo) +
            "” põe " + artigo(grupoRotulo, false) + " " + grupoRotulo.singular + " na seleção como uma unidade" + (p.brasil ? ", com a fonte estadual" : "") + "."
          : "Marque " + unidade.plural + (generoF ? " uma a uma" : " um a um") + " ou " + (p.rotulos.todo?.nome?.trim() ? todoInteiro(false, p.rotulos) : "toda a base") + "."}</p>
        <div className="analise-busca">
          <label className="sr-only" htmlFor="analise-busca">{rotuloDaBusca}</label>
          <Search size={16} aria-hidden="true" className="analise-busca-icone"/>
          <input id="analise-busca" type="search" data-testid="analise-busca" value={consulta} autoComplete="off"
            onChange={event => setConsulta(event.target.value)} placeholder={placeholder} className="analise-campo analise-busca-campo"/>
          {consulta && <button type="button" className="analise-icone analise-busca-limpar" aria-label="Limpar a busca"
            onClick={() => setConsulta("")}><X size={14} aria-hidden="true"/></button>}
        </div>
        {arvore}
      </div>

      <aside data-testid="analise-selecionados" className="analise-selecionados" aria-label="Territórios selecionados">
        {p.acao !== "lista" && p.painelDaAcao ? p.painelDaAcao : <>
          <div className="analise-selecionados-cabeca">
            <p className="m-0 min-w-0"><span className="analise-territorios-secao">Territórios selecionados</span>{" "}
              <strong data-testid="analise-selecionados-resumo" className="text-ink">{resumo}</strong></p>
          </div>
          <div data-testid="analise-mapa-selecao" className="analise-mapa-selecao">
            {mapaDaSelecao ? <MapaDosConjuntos largura={420} altura={210} coordenadas={p.coordenadas!} fundo={mapaDaSelecao.fundo} destaque={mapaDaSelecao.individuais}
              conjuntos={mapaDaSelecao.conjuntos} nomeDe={nomeCompleto} rotulo={"Mapa da seleção atual: " + resumo}
              vazio="O mapa aparece com o primeiro território selecionado." legenda="pontos cheios: selecionados · tracejado: estado como unidade ou conjunto"/>
              : <p className="analise-agregar-apoio">{vazio ? "O mapa aparece com o primeiro território selecionado." : "Carregando os pontos do mapa…"}</p>}
          </div>
          {p.regra && <p data-testid="analise-selecao-regra" className="analise-selecao-regra"><span>Seleção por critérios: {p.regra.texto}</span>{" "}
            <button type="button" data-testid="analise-criterios-reaplicar" className="analise-link" onClick={p.regra.onReaplicar}>
              Reaplicar em outra competência</button></p>}
          <div data-testid="analise-selecionados-itens" className="analise-selecionados-itens">{lista}</div>
          {p.totais}
          <div data-testid="analise-selecao-acoes" className="analise-selecao-acoes" role="group" aria-label="Ações da seleção">
            <button type="button" data-testid="analise-confirmar-selecao" className="analise-botao-primario" disabled={vazio} onClick={p.onConfirmar}
              title={"Vai à " + p.analiseAberta + " com esta seleção"}>Confirmar seleção<ArrowRight size={15} aria-hidden="true"/></button>
            {p.onCriterios && <button type="button" data-testid="analise-aplicar-criterios" className="analise-botao-secundario" onClick={p.onCriterios}>
              <Filter size={14} aria-hidden="true"/>Aplicar critérios de seleção</button>}
            <button type="button" data-testid="analise-agrupar-selecionados" className="analise-botao-secundario" disabled={!!p.motivoDoAgrupar}
              title={p.motivoDoAgrupar ?? undefined} onClick={p.onAgrupar}><Layers3 size={14} aria-hidden="true"/>Agrupar territórios selecionados</button>
          </div>
        </>}
      </aside>
    </div>
  </section>;
}

/** Um grupo na lista dos selecionados: o grupo inteiro numa linha ou, com algumas unidades, as etiquetas com o × (as primeiras e
 * "Ver todos os N", para listas grandes). */
function GrupoNaLista(p: { grupo: { grupo: string; nome: string; marcadas: number; total: number; inteiro: boolean; ids: string[] };
  info?: GrupoInfo; rotulo: string; unidade: Rotulo; generoF: boolean; nomeDe: (id: string) => string;
  nomeCompleto: (id: string) => string; onTirarGrupo?: () => void; rotuloTirarGrupo: string; onTirar: (id: string) => void;
  /** " · 27 em conjuntos" (10/11/2026): os do grupo que estão na seleção dentro de um conjunto. */
  emConjuntos?: string }) {
  const [todas, setTodas] = useState(false);
  const item = p.grupo;
  const ids = todas ? item.ids : item.ids.slice(0, ETIQUETAS_POR_GRUPO);
  return <li data-testid="analise-selecionado" data-grupo={item.grupo} className="analise-selecionado-grupo">
    <div className="analise-selecionado-cabeca">
      <span className="min-w-0"><strong className="text-ink">{p.rotulo}</strong>{" "}<span className="text-slate-600">· {item.inteiro
        ? (p.generoF ? "todas as " : "todos os ") + item.total : item.marcadas + " de " + quantos(item.total, p.unidade)}{p.emConjuntos ?? ""}</span></span>
      {p.onTirarGrupo && <button type="button" data-testid="analise-selecionado-tirar-grupo" className="analise-icone analise-icone-pequeno"
        aria-label={p.rotuloTirarGrupo} onClick={p.onTirarGrupo}><X size={13} aria-hidden="true"/></button>}
    </div>
    {item.ids.length > 0 && <ul className="analise-selecionado-unidades" aria-label={"Marcad" + (p.generoF ? "as" : "os") + (item.nome ? " de " + item.nome : "")}>
      {ids.map(id => <li key={id} data-testid="analise-selecionado-unidade" data-id={id} className="analise-etiqueta">
        {p.nomeDe(id)}
        <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + p.nomeCompleto(id)} onClick={() => p.onTirar(id)}>
          <X size={13} aria-hidden="true"/></button>
      </li>)}
      {item.ids.length > ETIQUETAS_POR_GRUPO && <li><button type="button" data-testid="analise-selecionado-ver-todas" className="analise-link"
        aria-expanded={todas} onClick={() => setTodas(atual => !atual)}>{todas ? "Mostrar menos" : "Ver todos os " + item.ids.length.toLocaleString("pt-BR")}</button></li>}
    </ul>}
  </li>;
}
