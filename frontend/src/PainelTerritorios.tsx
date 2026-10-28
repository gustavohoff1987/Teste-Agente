import { useEffect, useMemo, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, ChevronRight, Search, X } from "lucide-react";
import type { PainelConjuntoPedido, PainelMunicipios, PainelNivel } from "./painelApi";
import {
  BASE_VAZIA, alternarUnidade, artigo, desmarcarGrupo, grupoDaUnidade, grupoInteiro, maiuscula, marcadasNoGrupo, marcadasPorGrupo,
  marcarGrupo, nomeDaUnidade, normalizarEstados, quantos, resumoDoUniverso, textoTodasAsUnidadesDoGrupo, textoVerUnidades, todosOs,
  unidadeMarcada, type GrupoInfo, type RotulosTerritoriais, type UnidadeDoCatalogo,
} from "./painelModel";

// Seleção de Territórios (reformulada em 24/10/2026, pedido do responsável): só encontrar, navegar entre os níveis, marcar e
// desmarcar, ver o que está marcado e corrigir; os resultados ficam nas análises. Na base do Brasil, três níveis, um em análise
// por vez (RQ-DAD-30: nenhum nível é somado a outro): o Brasil (o país como uma unidade, com o total nacional, que não é a soma
// dos municípios), os estados (um, vários ou todos) e os municípios, navegados por estado e cumulativos: abrir outro estado só
// mostra a lista dele e não muda o que já está marcado. Cada nível guarda a sua escolha. Desde 24/10/2026 (segunda rodada), a
// tela tem duas áreas lado a lado: à esquerda, a busca e a lista para marcar; à direita, sempre à vista, o que já está marcado,
// estado a estado, com o × de cada unidade e de cada estado. Desfazer e Limpar seleção ficam no alto da área (controles globais),
// e toda mudança daqui pode ser desfeita pelo Desfazer. Numa planilha, os mesmos passos com a nomenclatura dela (grupos e unidades),
// sem os níveis. Cada mudança é um pedido explícito ao motor; nada é calculado aqui.

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
/** Acima disto, a lista de um grupo ganha atalhos por letra inicial (a lista inteira continua à vista em "Todas"). */
const COM_LETRAS = 120;
const LIMITE_BUSCA = 20;

type Props = {
  rotulos: RotulosTerritoriais;
  brasil: boolean;
  grupos: GrupoInfo[];
  /** A base do Brasil com os níveis Brasil e estados (a fonte estadual e a nacional). */
  comNiveis: boolean;
  unidades: UnidadeDoCatalogo[];
  total: number;
  nivel: PainelNivel;
  base: PainelMunicipios;
  estados: string[];
  conjuntos: PainelConjuntoPedido[];
  /** Grupo com a lista aberta (só mostra a lista; não muda a seleção). */
  aberto: string | null;
  /** O que a última mudança coletiva fez ("Municípios da Bahia desmarcados."), para a pessoa ver e, se quiser, usar o Desfazer. */
  aviso: string | null;
  /** Rótulo do botão que leva às análises ("Ver a análise"). */
  verAnalise: string;
  onNivel: (nivel: PainelNivel) => void;
  /** Nova escolha dos municípios, com o que mudou em palavras (vai para o Desfazer); `coletiva` quando muda muitos de uma vez. */
  onBase: (base: PainelMunicipios, acao: string, coletiva?: boolean) => void;
  onEstados: (estados: string[], acao: string, coletiva?: boolean) => void;
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
  const nivel: PainelNivel = p.comNiveis ? p.nivel : "municipios";
  const nomeDoGrupo = (id: string) => p.grupos.find(item => item.id === id)?.nome || id;
  const grupoAberto = p.aberto ? p.grupos.find(item => item.id === p.aberto) ?? null : null;
  useEffect(() => setLetra(""), [p.aberto]);
  useEffect(() => setConsulta(""), [nivel]);

  // ------------------------------------------------------------------------------------------ o que está marcado
  const marcadas = useMemo(() => marcadasPorGrupo(p.base, { grupos: p.grupos, unidadesDoGrupo: idsDoGrupo, nomes,
    grupoDe: id => grupoDeId.get(id) ?? "", todas: todasAsUnidades }), [p.base, p.grupos, nomes, grupoDeId, todasAsUnidades, porGrupo]);
  const unidadesMarcadas = marcadas.reduce((soma, item) => soma + item.marcadas, 0);
  const vazio = nivel === "brasil" ? false : nivel === "estados" ? !p.estados.length : !p.base.todos && !unidadesMarcadas && !p.conjuntos.length;
  const nomesCompletos = useMemo(() => new Map(validas.map(item => [item.id, nomeDaUnidade(item)])), [validas]);
  const resumo = resumoDoUniverso({ nivel, base: p.base, estados: p.estados, conjuntos: p.conjuntos.length, grupos: p.grupos,
    rotulos: p.rotulos, total: p.total, grupoDe: id => grupoDeId.get(id) ?? "", nomes: nomesCompletos });
  const deGrupo = (g: Pick<GrupoInfo, "nome" | "rotuloGrupo">) => textoTodasAsUnidadesDoGrupo(p.rotulos, g).replace(/^Tod[oa]s [oa]s /, "");
  /** "da Bahia", "de Buenos Aires": o fim de "municípios da Bahia". */
  const doGrupo = (g: Pick<GrupoInfo, "nome" | "rotuloGrupo">) => deGrupo(g).replace(/^\S+\s/, "");
  const marcadosTexto = (marcados: boolean) => (marcados ? " marcad" : " desmarcad") + (generoF ? "as." : "os.");
  const nomeCompleto = (id: string) => nomesCompletos.get(id) || nomes.get(id) || id;

  // ------------------------------------------------------------------------------------------ ações
  // O que muda um território só começa pelo verbo ("Marcar MANAUS (AM)"): o Desfazer diz "Desfazer: marcar MANAUS (AM)", e o nome
  // próprio fica como é (começando pelo nome, a primeira letra iria para a minúscula).
  const alternarEstado = (id: string) => {
    const marcado = p.estados.includes(id);
    p.onEstados(normalizarEstados(marcado ? p.estados.filter(item => item !== id) : [...p.estados, id], todosOsGrupos),
      (marcado ? "Desmarcar " : "Marcar ") + nomeDoGrupo(id));
  };
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

  // ------------------------------------------------------------------------------------------ partes
  const caixaDaUnidade = (item: UnidadeDoCatalogo, testid: string, comGrupo = false) => <li key={item.id} data-testid={testid} data-id={item.id}>
    <label className="analise-caixa">
      <input type="checkbox" checked={unidadeMarcada(p.base, item.id, temGrupos ? grupoDaUnidade(item) : "")} onChange={() => alternar(item)}/>
      <span className="min-w-0 flex-1">{comGrupo ? nomeDaUnidade(item) : item.name || item.label}</span>
      {comGrupo && temGrupos ? <span className="shrink-0 text-[12px] text-slate-500">{nomeDoGrupo(grupoDaUnidade(item))}</span>
        : item.code && <span className="shrink-0 text-[12px] text-slate-500">{item.code}</span>}
    </label>
  </li>;
  const caixaDoEstado = (grupo: GrupoInfo, testid: string) => <li key={grupo.id} data-testid={testid} data-id={grupo.id}>
    <label className="analise-caixa">
      <input type="checkbox" checked={p.estados.includes(grupo.id)} onChange={() => alternarEstado(grupo.id)}/>
      <span className="min-w-0 flex-1">{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span>
    </label>
  </li>;
  const linhaDoGrupo = (grupo: GrupoInfo, testid: string) => {
    const ids = idsDoGrupo(grupo.id), total = grupo.unidades || ids.length;
    const inteiro = grupoInteiro(p.base, grupo.id), n = marcadasNoGrupo(p.base, grupo.id, ids), parcial = !inteiro && n > 0;
    return <li key={grupo.id} data-testid={testid} data-id={grupo.id} data-marcadas={n} className="analise-grupo">
      <div className="analise-grupo-linha">
        <label className="analise-caixa min-w-0 flex-1">
          <input type="checkbox" data-testid="analise-grupo-todos" checked={inteiro}
            ref={elemento => { if (elemento) elemento.indeterminate = parcial; }}
            aria-label={textoTodasAsUnidadesDoGrupo(p.rotulos, grupo)} onChange={() => alternarGrupo(grupo)}/>
          <span className="min-w-0">
            <span className="block font-semibold text-ink">{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span>
            {n > 0 && <span className="block text-[12px] text-slate-600">{(inteiro ? (generoF ? "Todas as " : "Todos os ") + total : n + " de " + total) +
              (generoF ? " marcadas" : " marcados")}</span>}
          </span>
        </label>
        <button type="button" data-testid="analise-grupo-ver" className="analise-ver" onClick={() => { setConsulta(""); p.onAbrir(grupo.id); }}>
          {textoVerUnidades(p.rotulos, total)}<ChevronRight size={14} aria-hidden="true"/></button>
      </div>
    </li>;
  };
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

  // ------------------------------------------------------------------------------------------ busca
  const termo = sem(consulta.trim());
  const busca = useMemo(() => {
    if (!termo) return null;
    const grupos = temGrupos && nivel !== "brasil" ? p.grupos.filter(g => sem(g.nome + " " + g.sigla).includes(termo)).slice(0, 8) : [];
    const unidades = nivel === "municipios" ? validas.filter(item => sem(item.name + " " + item.code + " " + item.label).includes(termo))
      .slice(0, LIMITE_BUSCA) : [];
    return { grupos, unidades };
  }, [termo, temGrupos, nivel, p.grupos, validas]);
  const placeholder = nivel === "estados" ? "Buscar " + grupoRotulo.singular
    : temGrupos ? "Buscar " + unidade.singular + " ou " + grupoRotulo.singular : "Buscar " + unidade.singular;
  const rotuloDaBusca = "Buscar pelo nome: " + (nivel === "estados" ? grupoRotulo.plural : temGrupos ? unidade.plural + " ou " + grupoRotulo.plural
    : unidade.plural);

  const conteudo = (() => {
    if (nivel === "brasil") return <div data-testid="analise-territorios-brasil" className="analise-territorios-brasil">
      <p className="font-semibold text-ink">O Brasil inteiro, como uma unidade</p>
      <p>A análise usa o total nacional de profissionais e a população do país. Não é a soma dos estados nem a seleção de todos os{" "}
        {unidade.plural}.</p>
    </div>;
    if (busca) {
      const nada = !busca.grupos.length && !busca.unidades.length;
      return <div data-testid="analise-busca-resultado" className="analise-unidades">
        {nada ? <p className="text-xs text-slate-600">Nada encontrado com “{consulta.trim()}”.</p> : <>
          {busca.grupos.length > 0 && <ul className={nivel === "estados" ? "analise-unidades-lista" : "analise-grupos"}
            aria-label={maiuscula(grupoRotulo.plural) + " encontrad" + (artigo(grupoRotulo, false) === "a" ? "as" : "os")}>
            {busca.grupos.map(grupo => nivel === "estados" ? caixaDoEstado(grupo, "analise-busca-item") : linhaDoGrupo(grupo, "analise-busca-grupo"))}
          </ul>}
          {busca.unidades.length > 0 && <ul className="analise-unidades-lista" aria-label="Resultado da busca">
            {busca.unidades.map(item => caixaDaUnidade(item, "analise-busca-item", true))}
          </ul>}
        </>}
      </div>;
    }
    if (nivel === "estados") return <div className="analise-unidades">
      {botoesColetivos(
        { rotulo: "Marcar " + todosOs(grupoRotulo) + " (" + p.grupos.length + ")", desligado: p.estados.length === p.grupos.length,
          acao: () => p.onEstados([...todosOsGrupos].sort(comparar), maiuscula(todosOs(grupoRotulo)) + (generoGrupoF ? " marcadas." : " marcados."), true) },
        { rotulo: "Desmarcar " + todosOs(grupoRotulo), desligado: !p.estados.length,
          acao: () => p.onEstados([], maiuscula(grupoRotulo.plural) + (generoGrupoF ? " desmarcadas." : " desmarcados."), true) })}
      <ul data-testid="analise-estados" className="analise-unidades-lista analise-lista-estados" aria-label={maiuscula(grupoRotulo.plural)}>
        {p.grupos.map(grupo => caixaDoEstado(grupo, "analise-estado"))}
      </ul>
    </div>;
    if (temGrupos && grupoAberto) return <div data-testid="analise-grupo" data-id={grupoAberto.id} data-aberto="true" className="analise-grupo-aberto-bloco">
      {/* "Voltar aos estados" (24/10/2026): maior e preenchido, como os botões de destaque; só fecha a lista (o Desfazer do alto desfaz passos). */}
      <button type="button" data-testid="analise-grupo-voltar" className="analise-botao-primario analise-voltar-grupos" onClick={() => p.onAbrir(null)}>
        <ArrowLeft size={17} aria-hidden="true"/>Voltar {generoGrupoF ? "às " : "aos "}{grupoRotulo.plural}</button>
      {listaDeUnidades(porGrupo.get(grupoAberto.id) || [], grupoAberto)}
    </div>;
    if (temGrupos) return <div className="analise-unidades">
      {botoesColetivos(
        { rotulo: "Marcar " + todosOs(unidade) + (p.brasil ? " do Brasil" : "") + " (" + p.total.toLocaleString("pt-BR") + ")",
          desligado: p.base.todos, acao: () => p.onBase({ todos: true, estados: [], ids: [] },
            maiuscula(todosOs(unidade)) + (p.brasil ? " do Brasil" : "") + marcadosTexto(true), true) },
        { rotulo: "Desmarcar " + todosOs(unidade), desligado: !unidadesMarcadas,
          acao: () => p.onBase({ ...BASE_VAZIA }, maiuscula(unidade.plural) + marcadosTexto(false), true) })}
      <ul className="analise-grupos" aria-label={maiuscula(grupoRotulo.plural)}>{p.grupos.map(grupo => linhaDoGrupo(grupo, "analise-grupo"))}</ul>
    </div>;
    return listaDeUnidades([...validas].sort((a, b) => comparar(a.name || a.label, b.name || b.label)), null);
  })();

  // ------------------------------------------------------------------------------------------ o que entra na análise (à direita)
  // Estado a estado, em tempo real: o estado inteiro numa linha ("todos os 62") e, quando são algumas, cada unidade com o × dela;
  // cada estado com o × que o tira inteiro. No nível dos estados, as etiquetas deles; no Brasil, ele mesmo.
  const selecionadas = (() => {
    if (nivel === "brasil") return <p className="analise-selecionados-vazio">Brasil (total nacional), como uma unidade.</p>;
    if (nivel === "estados") return p.estados.length ? <ul className="analise-selecionados-estados">
      {p.estados.map(id => <li key={id} data-testid="analise-selecionado" data-id={id} className="analise-etiqueta">
        {nomeDoGrupo(id)}
        <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + nomeDoGrupo(id)} onClick={() => alternarEstado(id)}>
          <X size={13} aria-hidden="true"/></button>
      </li>)}
    </ul> : <p className="analise-selecionados-vazio">Nenhum{generoGrupoF ? "a" : ""} {grupoRotulo.singular} marcad{generoGrupoF ? "a" : "o"} ainda: marque na
      lista ao lado.</p>;
    if (p.base.todos) return <div data-testid="analise-selecionado" data-grupo="todos" className="analise-selecionado-grupo">
      <div className="analise-selecionado-cabeca">
        <span className="min-w-0"><strong className="text-ink">{maiuscula(todosOs(unidade))}{p.brasil ? " do Brasil" : ""}</strong> ({p.total.toLocaleString("pt-BR")})</span>
        <button type="button" className="analise-icone analise-icone-pequeno" aria-label={"Tirar " + todosOs(unidade)}
          onClick={() => p.onBase({ ...BASE_VAZIA }, maiuscula(unidade.plural) + marcadosTexto(false), true)}><X size={13} aria-hidden="true"/></button>
      </div>
    </div>;
    if (!marcadas.length && !p.conjuntos.length) return <p className="analise-selecionados-vazio">Nenhum{generoF ? "a" : ""} {unidade.singular}{" "}
      marcad{generoF ? "a" : "o"} ainda: marque na lista ao lado{temGrupos ? " (abra " + (generoGrupoF ? "uma " : "um ") + grupoRotulo.singular + " ou use a busca)" : ""}.</p>;
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

  return <section data-testid="analise-territorios" data-nivel={nivel} aria-labelledby="analise-territorios-titulo" className="analise-territorios">
    <h3 id="analise-territorios-titulo" tabIndex={-1} className="sr-only">Territórios</h3>
    {p.comNiveis && <div role="radiogroup" aria-label="Nível dos territórios" data-testid="analise-nivel" className="analise-niveis">
      {([["brasil", "Brasil", "o país inteiro, como uma unidade"],
        ["estados", maiuscula(grupoRotulo.plural), p.estados.length ? p.estados.length + " de " + p.grupos.length + " marcados" : "um, vários ou todos"],
        ["municipios", maiuscula(unidade.plural), unidadesMarcadas ? quantos(unidadesMarcadas, unidade) + " marcad" + (generoF ? "a" : "o") +
          (unidadesMarcadas === 1 ? "" : "s") : "escolha por " + grupoRotulo.singular]] as [PainelNivel, string, string][]).map(([valor, rotulo, apoio]) =>
        <button key={valor} type="button" role="radio" aria-checked={nivel === valor} data-testid={"analise-nivel-" + valor}
          className="analise-nivel" onClick={() => nivel !== valor && p.onNivel(valor)}>
          <span className="analise-nivel-nome">{rotulo}</span><span className="analise-nivel-apoio">{apoio}</span>
        </button>)}
    </div>}
    <div className="analise-territorios-colunas">
      <div data-testid="analise-territorios-lista" className="analise-territorios-lista">
        {nivel !== "brasil" && <div className="analise-busca">
          <label className="sr-only" htmlFor="analise-busca">{rotuloDaBusca}</label>
          <Search size={16} aria-hidden="true" className="analise-busca-icone"/>
          <input ref={buscaRef} id="analise-busca" type="search" data-testid="analise-busca" value={consulta} autoComplete="off"
            onChange={event => setConsulta(event.target.value)} placeholder={placeholder} className="analise-campo analise-busca-campo"/>
          {consulta && <button type="button" className="analise-icone analise-busca-limpar" aria-label="Limpar a busca"
            onClick={() => { setConsulta(""); buscaRef.current?.focus(); }}><X size={14} aria-hidden="true"/></button>}
        </div>}
        {conteudo}
      </div>

      <aside data-testid="analise-selecionados" className="analise-selecionados" aria-label="Na análise">
        <div className="analise-selecionados-cabeca">
          <p className="m-0 min-w-0"><span className="analise-territorios-secao">Na análise</span>{" "}
            <strong data-testid="analise-selecionados-resumo" className="text-ink">{resumo}</strong></p>
          <button type="button" data-testid="analise-ver-analise" className="analise-botao-primario" disabled={vazio} onClick={p.onVerAnalise}>
            {p.verAnalise}<ArrowRight size={15} aria-hidden="true"/></button>
        </div>
        {p.aviso && <p role="status" data-testid="analise-selecao-aviso" className="analise-desfazer">{p.aviso} Para desfazer, use o botão Desfazer, no alto.</p>}
        <div data-testid="analise-selecionados-itens" className="analise-selecionados-itens">{selecionadas}</div>
      </aside>
    </div>
  </section>;
}
