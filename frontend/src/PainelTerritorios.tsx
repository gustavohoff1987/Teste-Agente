import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { ArrowRight, ChevronDown, Search, X } from "lucide-react";
import type { PainelConjuntoPedido, PainelMunicipios, PainelNivel } from "./painelApi";
import {
  BASE_VAZIA, alternarUnidade, artigo, baseVazia, desmarcarGrupo, grupoDaUnidade, grupoInteiro, maiuscula, marcadasNoGrupo,
  marcadasPorGrupo, marcarGrupo, nomeDaUnidade, quantos, resumoDoUniverso, textoTodasAsUnidadesDoGrupo, todosOs,
  unidadeMarcada, type GrupoInfo, type OpcaoVerPor, type RotulosTerritoriais, type UnidadeDoCatalogo,
} from "./painelModel";

// Seleção de Territórios unificada (05/11/2026, comando do responsável; no lugar dos três níveis separados de 24/10/2026, um por
// vez): um só componente hierárquico, com multisseleção. À esquerda, a busca (estados e municípios) e a árvore: o Brasil (todos os
// municípios), os estados (cada um com a caixa de três estados: inteiro, em parte ou nada, e a lista dos municípios, que se abre no
// lugar) e os municípios. Marcar o Brasil marca todos os municípios; um estado, todos os municípios dele; desmarcar um município de
// um estado ou do Brasil marcado deixa os demais marcados (a exclusão); estados inteiros e municípios avulsos de estados diferentes
// se combinam. À direita, sempre à vista, o que está na análise: o resumo da abrangência, o "Ver por" (06/11/2026, no lugar de "Cada
// ponto da análise é": o estado ou o município, só no todo e numa seleção de estados inteiros; o todo deixou de ser unidade de
// análise e é a referência fixa), os totais individualizados (quando a abrangência é um estado inteiro ou o Brasil inteiro) e o que
// está marcado, estado a estado, com o × de cada um. Nenhum nível é somado a outro (RQ-DAD-30). Numa planilha, os mesmos passos com
// a nomenclatura dela (grupos e unidades), sem o "Ver por". Cada mudança é um pedido explícito ao motor e um passo do Desfazer;
// nada é calculado aqui.

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
/** Acima disto, a lista de um grupo ganha atalhos por letra inicial (a lista inteira continua à vista em "Todas"). */
const COM_LETRAS = 120;
const LIMITE_BUSCA = 20;

type Props = {
  rotulos: RotulosTerritoriais;
  brasil: boolean;
  grupos: GrupoInfo[];
  /** A base do Brasil com os estados (a fonte estadual): o "Ver por" aparece. */
  comNiveis: boolean;
  /** As opções do "Ver por" (painelModel.opcoesVerPor): com menos de duas, o controle não aparece. */
  verPor: OpcaoVerPor[];
  unidades: UnidadeDoCatalogo[];
  total: number;
  /** O nível em uso no "Ver por" (cada ponto é um município ou um estado). */
  nivel: PainelNivel;
  base: PainelMunicipios;
  /** Os estados como unidades (só leitura: vêm da árvore, com estados inteiros). */
  estados: string[];
  conjuntos: PainelConjuntoPedido[];
  /** Grupo com a lista aberta (só mostra a lista; não muda a seleção). */
  aberto: string | null;
  /** O que a última mudança coletiva fez ("Municípios da Bahia desmarcados."), para a pessoa ver e, se quiser, usar o Desfazer. */
  aviso: string | null;
  /** Rótulo do botão que leva às análises ("Ver a análise"). */
  verAnalise: string;
  /** Os totais individualizados da abrangência (o Brasil inteiro, os estados inteiros), quando o motor já os devolveu. */
  totais?: ReactNode;
  /** Nova escolha da árvore, com o que mudou em palavras (vai para o Desfazer); `coletiva` quando muda muitos de uma vez. */
  onBase: (base: PainelMunicipios, acao: string, coletiva?: boolean) => void;
  /** O "Ver por" escolhido (a área confere se a escolha permite). */
  onUnidade: (nivel: PainelNivel) => void;
  onAbrir: (grupo: string | null) => void;
  /** Desfaz um conjunto criado no Juntar (o × dele, no que está marcado). */
  onDesfazerConjunto: (id: string) => void;
  onVerAnalise: () => void;
};

export default function PainelTerritorios(p: Props) {
  const [consulta, setConsulta] = useState("");
  const [letra, setLetra] = useState("");
  const buscaRef = useRef<HTMLInputElement>(null);
  const unidade = p.rotulos.unidade, grupoRotulo = p.rotulos.grupo ?? { singular: "grupo", plural: "grupos" };
  const generoF = artigo(unidade, false) === "a", generoGrupoF = artigo(grupoRotulo, false) === "a";
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
  const porId = useMemo(() => new Map(validas.map(item => [item.id, item])), [validas]);
  const todasAsUnidades = useMemo(() => validas.map(item => item.id), [validas]);
  const idsDoGrupo = (grupo: string) => (porGrupo.get(grupo) || []).map(item => item.id);
  const todosOsGrupos = p.grupos.map(item => item.id);
  const temGrupos = p.grupos.length > 0;
  const nomeDoGrupo = (id: string) => p.grupos.find(item => item.id === id)?.nome || id;
  useEffect(() => setLetra(""), [p.aberto]);

  // ------------------------------------------------------------------------------------------ o que está marcado
  const marcadas = useMemo(() => marcadasPorGrupo(p.base, { grupos: p.grupos, unidadesDoGrupo: idsDoGrupo, nomes,
    grupoDe: id => grupoDeId.get(id) ?? "", todas: todasAsUnidades }), [p.base, p.grupos, nomes, grupoDeId, todasAsUnidades, porGrupo]);
  const unidadesMarcadas = marcadas.reduce((soma, item) => soma + item.marcadas, 0);
  const vazio = p.nivel === "brasil" ? false : p.nivel === "estados" ? !p.estados.length : baseVazia(p.base) && !p.conjuntos.length;
  const nomesCompletos = useMemo(() => new Map(validas.map(item => [item.id, nomeDaUnidade(item)])), [validas]);
  const resumo = resumoDoUniverso({ nivel: p.nivel, base: p.base, estados: p.estados, conjuntos: p.conjuntos.length, grupos: p.grupos,
    rotulos: p.rotulos, total: p.total, grupoDe: id => grupoDeId.get(id) ?? "", nomes: nomesCompletos });
  const deGrupo = (g: Pick<GrupoInfo, "nome" | "rotuloGrupo">) => textoTodasAsUnidadesDoGrupo(p.rotulos, g).replace(/^Tod[oa]s [oa]s /, "");
  /** "da Bahia", "de Buenos Aires": o fim de "municípios da Bahia". */
  const doGrupo = (g: Pick<GrupoInfo, "nome" | "rotuloGrupo">) => deGrupo(g).replace(/^\S+\s/, "");
  const marcadosTexto = (marcados: boolean) => (marcados ? " marcad" : " desmarcad") + (generoF ? "as." : "os.");
  const nomeCompleto = (id: string) => nomesCompletos.get(id) || nomes.get(id) || id;
  const raiz = p.brasil ? "Brasil" : "Toda a planilha";
  const totalTexto = (generoF ? "todas as " : "todos os ") + p.total.toLocaleString("pt-BR") + " " + (p.total === 1 ? unidade.singular : unidade.plural);

  // ------------------------------------------------------------------------------------------ ações
  // O que muda um território só começa pelo verbo ("Marcar MANAUS (AM)"): o Desfazer diz "Desfazer: marcar MANAUS (AM)", e o nome
  // próprio fica como é (começando pelo nome, a primeira letra iria para a minúscula).
  const alternar = (item: UnidadeDoCatalogo) => {
    const grupo = grupoDaUnidade(item);
    const marcada = unidadeMarcada(p.base, item.id, temGrupos ? grupo : "");
    p.onBase(alternarUnidade(p.base, item.id, temGrupos ? grupo : "", temGrupos ? idsDoGrupo(grupo) : [], todosOsGrupos, todasAsUnidades),
      (marcada ? "Desmarcar " : "Marcar ") + nomeDaUnidade(item));
  };
  /** Tira uma unidade marcada (o × da lista à direita). */
  const tirarUnidade = (id: string) => {
    const item = porId.get(id);
    const grupo = item ? grupoDaUnidade(item) : grupoDeId.get(id) ?? "";
    p.onBase(alternarUnidade(p.base, id, temGrupos ? grupo : "", temGrupos ? idsDoGrupo(grupo) : [], todosOsGrupos, todasAsUnidades),
      "Tirar " + nomeCompleto(id));
  };
  const alternarGrupo = (grupo: GrupoInfo) => {
    const ids = idsDoGrupo(grupo.id);
    if (grupoInteiro(p.base, grupo.id)) p.onBase(desmarcarGrupo(p.base, grupo.id, ids, todosOsGrupos, todasAsUnidades),
      maiuscula(deGrupo(grupo)) + marcadosTexto(false), true);
    else p.onBase(marcarGrupo(p.base, grupo.id, ids), maiuscula(todosOs(unidade)) + " " + doGrupo(grupo) + marcadosTexto(true), true);
  };
  const tirarGrupo = (g: GrupoInfo) => p.onBase(desmarcarGrupo(p.base, g.id, idsDoGrupo(g.id), todosOsGrupos, todasAsUnidades),
    maiuscula(deGrupo(g)) + marcadosTexto(false), true);
  /** A raiz da árvore: o Brasil inteiro (ou a planilha inteira), marcado ou desmarcado de uma vez. */
  const alternarRaiz = () => p.base.todos
    ? p.onBase({ ...BASE_VAZIA }, (p.brasil ? "Brasil inteiro desmarcado" : maiuscula(unidade.plural) + marcadosTexto(false).replace(/\.$/, "")) + ".", true)
    : p.onBase({ todos: true, estados: [], ids: [] }, (p.brasil ? "Brasil inteiro marcado: " : "Toda a planilha marcada: ") + totalTexto + ".", true);
  const escolherUnidade = (valor: PainelNivel) => { if (valor !== p.nivel) p.onUnidade(valor); };

  // ------------------------------------------------------------------------------------------ partes
  const caixaDaUnidade = (item: UnidadeDoCatalogo, testid: string, comGrupo = false) => <li key={item.id} data-testid={testid} data-id={item.id}>
    <label className="analise-caixa">
      <input type="checkbox" checked={unidadeMarcada(p.base, item.id, temGrupos ? grupoDaUnidade(item) : "")} onChange={() => alternar(item)}/>
      <span className="min-w-0 flex-1">{comGrupo ? nomeDaUnidade(item) : item.name || item.label}</span>
      {comGrupo && temGrupos ? <span className="shrink-0 text-[12px] text-slate-500">{nomeDoGrupo(grupoDaUnidade(item))}</span>
        : item.code && <span className="shrink-0 text-[12px] text-slate-500">{item.code}</span>}
    </label>
  </li>;
  const botoesColetivos = (marcar: { rotulo: string; desligado: boolean; acao: () => void },
    desmarcar: { rotulo: string; desligado: boolean; acao: () => void }) => <div className="analise-territorios-coletivos" role="group"
    aria-label="Marcar ou desmarcar de uma vez">
    <button type="button" data-testid="analise-marcar-todos" className="analise-botao-secundario" disabled={marcar.desligado} onClick={marcar.acao}>
      {marcar.rotulo}</button>
    <button type="button" data-testid="analise-desmarcar-todos" className="analise-botao-secundario" disabled={desmarcar.desligado} onClick={desmarcar.acao}>
      {desmarcar.rotulo}</button>
  </div>;

  const listaDeUnidades = (lista: UnidadeDoCatalogo[], grupo: GrupoInfo | null) => {
    const letras = lista.length > COM_LETRAS ? [...new Set(lista.map(item => sem((item.name || item.label).charAt(0)).toUpperCase()))].sort() : [];
    const visiveis = letra && letras.length ? lista.filter(item => sem((item.name || item.label).charAt(0)).toUpperCase() === letra) : lista;
    const ids = lista.map(item => item.id);
    const n = grupo ? marcadasNoGrupo(p.base, grupo.id, ids) : lista.filter(item => unidadeMarcada(p.base, item.id, "")).length;
    const rotulo = grupo ? maiuscula(deGrupo(grupo)) : maiuscula(unidade.plural) + " da planilha";
    // Sem a lista das unidades (o catálogo da planilha não veio, por exemplo com nomes que não permitem escolher uma a uma), a
    // escolha possível é a planilha inteira: "Marcar todos" continua valendo.
    const semLista = !grupo && !lista.length;
    const todasMarcadas = grupo ? n === lista.length : p.base.todos || (lista.length > 0 && n === lista.length);
    return <div data-testid="analise-grupo-unidades" data-id={grupo?.id ?? ""} className="analise-unidades">
      <p className="text-xs text-slate-700" role="status"><strong className="text-ink">{rotulo}</strong>: {semLista
        ? (p.base.todos ? (generoF ? "todas marcadas" : "todos marcados") : (generoF ? "nenhuma marcada" : "nenhum marcado")) + ". A lista " +
          (generoF ? "das " : "dos ") + unidade.plural + " não está disponível; a análise pode usar a planilha inteira."
        : n + " de " + quantos(lista.length, unidade) + " marcad" + (generoF ? "as" : "os") + "."}</p>
      {botoesColetivos(
        { rotulo: "Marcar " + todosOs(unidade) + (grupo ? " " + doGrupo(grupo) : ""), desligado: todasMarcadas,
          acao: () => grupo ? p.onBase(marcarGrupo(p.base, grupo.id, ids), maiuscula(todosOs(unidade)) + " " + doGrupo(grupo) + marcadosTexto(true), true)
            : p.onBase({ todos: true, estados: [], ids: [] }, maiuscula(todosOs(unidade)) + marcadosTexto(true), true) },
        { rotulo: "Desmarcar " + artigo(unidade, true) + " " + (grupo ? deGrupo(grupo) : unidade.plural), desligado: n === 0 && (!!grupo || !p.base.todos),
          acao: () => grupo ? p.onBase(desmarcarGrupo(p.base, grupo.id, ids, todosOsGrupos, todasAsUnidades), maiuscula(deGrupo(grupo)) + marcadosTexto(false), true)
            : p.onBase({ ...BASE_VAZIA }, maiuscula(unidade.plural) + marcadosTexto(false), true) })}
      {letras.length > 0 && <div className="flex flex-wrap gap-1" role="group" aria-label="Atalho pela letra inicial">
        <button type="button" aria-pressed={!letra} className="analise-letra" onClick={() => setLetra("")}>Todas</button>
        {letras.map(item => <button key={item} type="button" aria-pressed={letra === item} className="analise-letra" onClick={() => setLetra(item)}>{item}</button>)}
      </div>}
      <ul className="analise-unidades-lista" aria-label={rotulo}>{visiveis.map(item => caixaDaUnidade(item, "analise-unidade"))}</ul>
    </div>;
  };

  /** Uma linha da árvore: o grupo (o estado) com a caixa de três estados (inteiro, em parte ou nada), o nome inteiro, quantas unidades
   * estão marcadas e o botão que abre a lista das unidades no lugar (um grupo aberto por vez). */
  const linhaDoGrupo = (grupo: GrupoInfo, testid: string) => {
    const ids = idsDoGrupo(grupo.id), total = grupo.unidades || ids.length;
    const inteiro = grupoInteiro(p.base, grupo.id), n = marcadasNoGrupo(p.base, grupo.id, ids), parcial = !inteiro && n > 0;
    const aberto = p.aberto === grupo.id && testid === "analise-grupo";
    const idDaLista = "analise-lista-" + grupo.id.replace(/[^A-Za-z0-9_-]/g, "_");
    const contagem = inteiro ? (generoF ? "todas as " : "todos os ") + total.toLocaleString("pt-BR") + " " + (total === 1 ? unidade.singular : unidade.plural)
      : n ? n.toLocaleString("pt-BR") + " de " + quantos(total, unidade) : quantos(total, unidade);
    const verTexto = (aberto ? "Fechar a lista " + (generoF ? "das " : "dos ") : "Ver " + (generoF ? "as " : "os ")) + quantos(total, unidade) + " " + doGrupo(grupo);
    return <li key={grupo.id} data-testid={testid} data-id={grupo.id} data-marcadas={n} data-aberto={aberto ? "true" : "false"}
      data-situacao={inteiro ? "inteiro" : parcial ? "parcial" : "nenhum"} className={"analise-grupo" + (aberto ? " analise-grupo-aberto" : "")}>
      <div className="analise-grupo-linha">
        <label className="analise-caixa analise-grupo-caixa">
          <input type="checkbox" data-testid="analise-grupo-todos" checked={inteiro}
            ref={elemento => { if (elemento) elemento.indeterminate = parcial; }}
            aria-label={textoTodasAsUnidadesDoGrupo(p.rotulos, grupo)} onChange={() => alternarGrupo(grupo)}/>
          <span className="analise-grupo-texto">
            <span className="analise-grupo-nome">{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span>
            <span data-testid="analise-grupo-contagem" className="analise-grupo-contagem">{contagem}</span>
          </span>
        </label>
        <button type="button" data-testid="analise-grupo-ver" className="analise-expandir" aria-expanded={aberto}
          aria-controls={aberto ? idDaLista : undefined} aria-label={verTexto} title={verTexto}
          onClick={() => { setConsulta(""); p.onAbrir(aberto ? null : grupo.id); }}>
          <span className="analise-expandir-texto">{aberto ? "Fechar" : maiuscula(unidade.plural)}</span>
          <ChevronDown size={16} aria-hidden="true" className="analise-expandir-seta"/>
        </button>
      </div>
      {aberto && <div id={idDaLista} className="analise-grupo-aberto-bloco">
        {listaDeUnidades(porGrupo.get(grupo.id) || [], grupo)}
        <button type="button" data-testid="analise-grupo-voltar" className="analise-botao-secundario analise-voltar-grupos" onClick={() => p.onAbrir(null)}>
          Fechar a lista {generoF ? "das " : "dos "}{unidade.plural} {doGrupo(grupo)}</button>
      </div>}
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

  const conteudo = (() => {
    if (busca) {
      const nada = !busca.grupos.length && !busca.unidades.length;
      return <div data-testid="analise-busca-resultado" className="analise-unidades">
        {nada ? <p className="text-xs text-slate-600">Nada encontrado com “{consulta.trim()}”.</p> : <>
          {busca.grupos.length > 0 && <ul className="analise-grupos"
            aria-label={maiuscula(grupoRotulo.plural) + " encontrad" + (artigo(grupoRotulo, false) === "a" ? "as" : "os")}>
            {busca.grupos.map(grupo => linhaDoGrupo(grupo, "analise-busca-grupo"))}
          </ul>}
          {busca.unidades.length > 0 && <ul className="analise-unidades-lista" aria-label="Resultado da busca">
            {busca.unidades.map(item => caixaDaUnidade(item, "analise-busca-item", true))}
          </ul>}
        </>}
      </div>;
    }
    if (!temGrupos) return listaDeUnidades([...validas].sort((a, b) => comparar(a.name || a.label, b.name || b.label)), null);
    const algo = p.base.todos || !baseVazia(p.base);
    return <div data-testid="analise-arvore" className="analise-arvore">
      <div data-testid="analise-raiz" data-marcado={p.base.todos ? "true" : algo ? "parcial" : "false"} className="analise-raiz">
        <label className="analise-caixa analise-grupo-caixa">
          <input type="checkbox" data-testid="analise-raiz-caixa" checked={p.base.todos}
            ref={elemento => { if (elemento) elemento.indeterminate = !p.base.todos && algo; }}
            aria-label={raiz + ": " + totalTexto} onChange={alternarRaiz}/>
          <span className="analise-grupo-texto">
            <span className="analise-grupo-nome analise-raiz-nome">{raiz}</span>
            <span className="analise-grupo-contagem">{totalTexto}{p.brasil ? ", em " + quantos(p.grupos.length, grupoRotulo) : ""}</span>
          </span>
        </label>
      </div>
      <ul className="analise-grupos analise-grupos-arvore" aria-label={maiuscula(grupoRotulo.plural)}>
        {p.grupos.map(grupo => linhaDoGrupo(grupo, "analise-grupo"))}
      </ul>
    </div>;
  })();

  // ------------------------------------------------------------------------------------------ o que entra na análise (à direita)
  // Estado a estado, em tempo real: o estado inteiro numa linha ("todos os 62") e, quando são algumas, cada unidade com o × dela;
  // cada estado com o × que o tira inteiro.
  const selecionadas = (() => {
    if (p.base.todos) return <div data-testid="analise-selecionado" data-grupo="todos" className="analise-selecionado-grupo">
      <div className="analise-selecionado-cabeca">
        <span className="min-w-0"><strong className="text-ink">{maiuscula(todosOs(unidade))}{p.brasil ? " do Brasil" : ""}</strong> ({p.total.toLocaleString("pt-BR")})</span>
        <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + todosOs(unidade)}
          onClick={alternarRaiz}><X size={13} aria-hidden="true"/></button>
      </div>
    </div>;
    if (!marcadas.length && !p.conjuntos.length) return <p className="analise-selecionados-vazio">Nenhum{generoF ? "a" : ""} {unidade.singular}{" "}
      marcad{generoF ? "a" : "o"} ainda: marque na lista{temGrupos ? " (" + (p.brasil ? "o Brasil, " : "") + (generoGrupoF ? "uma " : "um ") +
      grupoRotulo.singular + " inteir" + (generoGrupoF ? "a" : "o") + " ou abra a lista d" + (generoGrupoF ? "ela" : "ele") + "; ou use a busca)" : ""}.</p>;
    return <ul className="analise-selecionados-lista">
      {marcadas.map(item => {
        const g = p.grupos.find(grupo => grupo.id === item.grupo);
        return <li key={item.grupo || "unidades"} data-testid="analise-selecionado" data-grupo={item.grupo} className="analise-selecionado-grupo">
          <div className="analise-selecionado-cabeca">
            <span className="min-w-0"><strong className="text-ink">{item.nome || (temGrupos ? "Sem " + grupoRotulo.singular : maiuscula(unidade.plural))}</strong>
              {" "}<span className="text-slate-600">· {item.inteiro ? (generoF ? "todas as " : "todos os ") + item.total : item.marcadas + " de " + item.total}</span></span>
            {g && <button type="button" data-testid="analise-selecionado-tirar-grupo" className="analise-icone analise-icone-pequeno"
              aria-label={"Tirar " + deGrupo(g)} onClick={() => tirarGrupo(g)}><X size={13} aria-hidden="true"/></button>}
          </div>
          {item.ids.length > 0 && <ul className="analise-selecionado-unidades" aria-label={"Marcad" + (generoF ? "as" : "os") + (item.nome ? " " + doGrupo(g ?? { nome: item.nome, rotuloGrupo: "" }) : "")}>
            {item.ids.map(id => <li key={id} data-testid="analise-selecionado-unidade" data-id={id} className="analise-etiqueta">
              {nomes.get(id) || nomeCompleto(id)}
              <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + nomeCompleto(id)} onClick={() => tirarUnidade(id)}>
                <X size={13} aria-hidden="true"/></button>
            </li>)}
          </ul>}
        </li>;
      })}
      {p.conjuntos.length > 0 && <li data-testid="analise-selecionado" data-grupo="conjuntos" className="analise-selecionado-grupo">
        <div className="analise-selecionado-cabeca"><strong className="text-ink">{p.conjuntos.length === 1 ? "Conjunto" : "Conjuntos"}</strong></div>
        <ul className="analise-selecionado-unidades">
          {p.conjuntos.map(conjunto => <li key={conjunto.id} data-testid="analise-selecionado-conjunto" data-id={conjunto.id} className="analise-etiqueta">
            {conjunto.rotulo}
            <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Desfazer o conjunto " + conjunto.rotulo}
              onClick={() => p.onDesfazerConjunto(conjunto.id)}><X size={13} aria-hidden="true"/></button>
          </li>)}
        </ul>
      </li>}
    </ul>;
  })();

  return <section data-testid="analise-territorios" data-nivel={p.nivel} data-marcadas={unidadesMarcadas} aria-labelledby="analise-territorios-titulo"
    className="analise-territorios">
    <h3 id="analise-territorios-titulo" tabIndex={-1} className="sr-only">Territórios</h3>
    <div className="analise-territorios-colunas">
      <div data-testid="analise-territorios-lista" className="analise-territorios-lista">
        <p data-testid="analise-territorios-instrucao" className="analise-territorios-instrucao">{temGrupos
          ? "Marque " + (p.brasil ? "o Brasil, " : "") + grupoRotulo.plural + " inteir" + (generoGrupoF ? "as" : "os") + " ou " + unidade.plural + ". " +
            maiuscula(artigo(grupoRotulo, false)) + " " + grupoRotulo.singular + " marcad" + (generoGrupoF ? "a" : "o") + " traz " + todosOs(unidade) + " del" +
            (generoGrupoF ? "a" : "e") + ", e você pode desmarcar " + (generoF ? "algumas" : "alguns") + ". Abra a lista de " +
            (generoGrupoF ? "uma " : "um ") + grupoRotulo.singular + " para escolher " + unidade.plural + (generoF ? " uma a uma." : " um a um.")
          : "Marque " + unidade.plural + (generoF ? " uma a uma" : " um a um") + " ou a planilha inteira."}</p>
        <div className="analise-busca">
          <label className="sr-only" htmlFor="analise-busca">{rotuloDaBusca}</label>
          <Search size={16} aria-hidden="true" className="analise-busca-icone"/>
          <input ref={buscaRef} id="analise-busca" type="search" data-testid="analise-busca" value={consulta} autoComplete="off"
            onChange={event => setConsulta(event.target.value)} placeholder={placeholder} className="analise-campo analise-busca-campo"/>
          {consulta && <button type="button" className="analise-icone analise-busca-limpar" aria-label="Limpar a busca"
            onClick={() => { setConsulta(""); buscaRef.current?.focus(); }}><X size={14} aria-hidden="true"/></button>}
        </div>
        {conteudo}
      </div>

      <aside data-testid="analise-selecionados" className="analise-selecionados" aria-label="Na análise">
        <div className="analise-selecionados-cabeca">
          <p className="m-0 min-w-0"><span className="analise-territorios-secao">Na análise</span>{" "}
            <strong data-testid="analise-selecionados-resumo" className="text-ink">{resumo}</strong></p>
          <button type="button" data-testid="analise-ver-analise" className="analise-botao-primario" disabled={vazio} onClick={p.onVerAnalise}>
            {p.verAnalise}<ArrowRight size={15} aria-hidden="true"/></button>
        </div>
        {/* "Ver por" (06/11/2026, no lugar de "Cada ponto da análise é"): só os níveis abaixo do lugar em uso; o todo nunca é opção
            (é a referência fixa); com uma opção só, o controle não aparece. */}
        {p.comNiveis && p.verPor.length > 1 && <div className="analise-unidade-de-analise">
          <p id="analise-nivel-titulo" className="analise-territorios-secao">Ver por</p>
          <div role="radiogroup" aria-labelledby="analise-nivel-titulo" data-testid="analise-nivel" className="analise-niveis">
            {p.verPor.map(opcao => <button key={opcao.nivel} type="button" role="radio" aria-checked={p.nivel === opcao.nivel}
                data-testid={"analise-nivel-" + opcao.nivel} data-possivel="true" className="analise-nivel" onClick={() => escolherUnidade(opcao.nivel)}>
                <span className="analise-nivel-nome">{opcao.rotulo}</span><span className="analise-nivel-apoio">{opcao.apoio}</span>
              </button>)}
          </div>
        </div>}
        {p.totais}
        {p.aviso && <p role="status" data-testid="analise-selecao-aviso" className="analise-desfazer">{p.aviso} Para desfazer, use o botão Desfazer, no alto.</p>}
        <div data-testid="analise-selecionados-itens" className="analise-selecionados-itens">{selecionadas}</div>
      </aside>
    </div>
  </section>;
}
