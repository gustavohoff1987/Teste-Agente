import { useEffect, useMemo, useRef, useState } from "react";
import { ChevronDown, ChevronRight, Map as MapaIcone, Search } from "lucide-react";
import type { PainelMunicipios, PainelNivel } from "./painelApi";
import {
  alternarUnidade, artigo, desmarcarGrupo, generoDe, grupoDaUnidade, grupoInteiro, marcadasNoGrupo, marcarGrupo, maiuscula, nomeDaUnidade, quantos,
  textoTodasAsUnidades, textoTodasAsUnidadesDoGrupo, textoTodosOsGrupos, textoVerUnidades, todosOs, unidadeMarcada,
  type GrupoInfo, type RotulosTerritoriais, type UnidadeDoCatalogo,
} from "./painelModel";

// Escolha dos territórios em lista (pedido do responsável, 22/10/2026), na aba Seleção de Territórios desde 23/10/2026: a mesma
// seleção vale para todas as análises, e a pessoa volta a ela quando quiser. Não depende de digitação nem de adivinhar onde clicar. Brasil: "Todos os estados" (os estados em bolhas) ou "Todos os municípios do Brasil" (modo leve).
// Estados: a lista inteira, cada um com "Ver os N municípios" (abre a lista dele e põe o estado no gráfico) e a caixa "Todos os
// municípios de <estado>". Municípios do estado aberto: caixas de marcar, sem rolagem escondida, com "Marcar todos" e
// "Desmarcar todos". A busca é só um complemento. Numa planilha, os mesmos passos com a nomenclatura dela (grupos e unidades).
// Cada mudança aqui é um pedido explícito ao motor; nada é calculado na tela.

const sem = (texto: string) => texto.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const comparar = (a: string, b: string) => a.localeCompare(b, "pt-BR", { numeric: true });
/** Acima disto, a lista de um grupo ganha atalhos por letra inicial (a lista inteira continua à vista em "Todas"). */
const COM_LETRAS = 120;

type Props = {
  rotulos: RotulosTerritoriais;
  brasil: boolean;
  grupos: GrupoInfo[];
  /** A fonte tem bolhas de grupo (os estados na base do Brasil). */
  comBolhasDeGrupo: boolean;
  unidades: UnidadeDoCatalogo[];
  total: number;
  nivel: PainelNivel;
  base: PainelMunicipios;
  aberto: string | null;
  desabilitado: boolean;
  onGrupos: () => void;
  onTodas: () => void;
  onVer: (grupo: string) => void;
  onFechar: () => void;
  onBase: (base: PainelMunicipios) => void;
};

export default function PainelTerritorios(p: Props) {
  const [consulta, setConsulta] = useState("");
  const [letra, setLetra] = useState("");
  const abertoRef = useRef<HTMLLIElement>(null);
  const unidade = p.rotulos.unidade, grupoRotulo = p.rotulos.grupo;
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
  const todasAsUnidades = useMemo(() => validas.map(item => item.id), [validas]);
  const idsDoGrupo = (grupo: string) => (porGrupo.get(grupo) || []).map(item => item.id);
  const todosOsGrupos = p.grupos.map(item => item.id);
  const temGrupos = p.grupos.length > 0;
  const naVisaoDeGrupos = p.nivel === "estados";
  useEffect(() => setLetra(""), [p.aberto]);
  useEffect(() => {
    if (p.aberto) abertoRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [p.aberto]);

  const alternar = (item: UnidadeDoCatalogo) => {
    const grupo = grupoDaUnidade(item);
    p.onBase(alternarUnidade(p.base, item.id, temGrupos ? grupo : "", temGrupos ? idsDoGrupo(grupo) : [], todosOsGrupos, todasAsUnidades));
  };
  const achados = useMemo(() => {
    const termo = sem(consulta.trim());
    if (!termo) return [];
    return validas.filter(item => sem(item.name + " " + item.code + " " + item.label).includes(termo)).slice(0, 20);
  }, [validas, consulta]);
  const nomeDoGrupo = (id: string) => p.grupos.find(item => item.id === id)?.nome || id;

  const listaDeUnidades = (lista: UnidadeDoCatalogo[], rotulo: string, grupo: string) => {
    const letras = lista.length > COM_LETRAS ? [...new Set(lista.map(item => sem((item.name || item.label).charAt(0)).toUpperCase()))].sort() : [];
    const visiveis = letra && letras.length ? lista.filter(item => sem((item.name || item.label).charAt(0)).toUpperCase() === letra) : lista;
    const marcadas = grupo ? marcadasNoGrupo(p.base, grupo, lista.map(item => item.id)) : lista.filter(item => unidadeMarcada(p.base, item.id, "")).length;
    return <div data-testid="analise-grupo-unidades" data-id={grupo} className="analise-unidades">
      <p className="text-xs text-slate-700" role="status"><strong className="text-ink">{rotulo}</strong>: {marcadas} de {quantos(lista.length, unidade)} no gráfico.</p>
      <div className="flex flex-wrap gap-1.5">
        <button type="button" data-testid="analise-unidades-marcar-todos" disabled={p.desabilitado || marcadas === lista.length}
          className="analise-botao-secundario" onClick={() => p.onBase(grupo ? marcarGrupo(p.base, grupo, lista.map(item => item.id))
            : { todos: true, estados: [], ids: [] })}>Marcar todos</button>
        <button type="button" data-testid="analise-unidades-desmarcar-todos" disabled={p.desabilitado || marcadas === 0}
          className="analise-botao-secundario" onClick={() => p.onBase(grupo ? desmarcarGrupo(p.base, grupo, lista.map(item => item.id), todosOsGrupos, todasAsUnidades)
            : { todos: false, estados: [], ids: [] })}>Desmarcar todos</button>
      </div>
      {letras.length > 0 && <div className="flex flex-wrap gap-1" role="group" aria-label="Atalho pela letra inicial">
        <button type="button" aria-pressed={!letra} className="analise-letra" onClick={() => setLetra("")}>Todas</button>
        {letras.map(item => <button key={item} type="button" aria-pressed={letra === item} className="analise-letra" onClick={() => setLetra(item)}>{item}</button>)}
      </div>}
      <ul className="analise-unidades-lista" aria-label={rotulo}>
        {visiveis.map(item => <li key={item.id} data-testid="analise-unidade" data-id={item.id}>
          <label className="analise-caixa">
            <input type="checkbox" checked={unidadeMarcada(p.base, item.id, temGrupos ? grupoDaUnidade(item) : "")} disabled={p.desabilitado}
              onChange={() => alternar(item)}/>
            <span className="min-w-0 flex-1">{item.name || item.label}</span>
            {item.code && <span className="shrink-0 text-[11px] text-slate-500">{item.code}</span>}
          </label>
        </li>)}
      </ul>
    </div>;
  };

  return <section data-testid="analise-territorios" aria-labelledby="analise-territorios-titulo" className="analise-territorios">
    <div>
      <h3 id="analise-territorios-titulo" tabIndex={-1} className="flex items-center gap-1.5 text-sm font-bold text-ink outline-none">
        <MapaIcone size={15} aria-hidden="true"/>Territórios disponíveis</h3>
      <p className="mt-1 text-xs leading-5 text-slate-600">Tudo aparece nesta lista; procurar pelo nome é opcional.</p>
    </div>

    <div className="space-y-1.5" role="group" aria-label={p.brasil ? "Brasil" : "Planilha"}>
      <p className="analise-territorios-secao">{p.brasil ? "Brasil" : "Planilha"}</p>
      {p.comBolhasDeGrupo && grupoRotulo && <button type="button" data-testid="analise-territorios-estados" aria-pressed={naVisaoDeGrupos}
        disabled={p.desabilitado} className="analise-opcao-territorio" onClick={p.onGrupos}>
        <span className="font-semibold">{textoTodosOsGrupos(p.rotulos, p.grupos.length)}</span>
        <span className="block text-[11px] font-normal text-slate-600">{maiuscula(grupoRotulo.plural)} em bolhas, com a linha do Brasil.</span>
      </button>}
      <button type="button" data-testid="analise-territorios-todos" aria-pressed={!naVisaoDeGrupos && p.base.todos} disabled={p.desabilitado}
        className="analise-opcao-territorio" onClick={p.onTodas}>
        <span className="font-semibold">{textoTodasAsUnidades(p.rotulos, p.total, p.brasil)}</span>
        {p.total > 400 && <span className="block text-[11px] font-normal text-slate-600">Mais lento: o gráfico usa o modo leve.</span>}
      </button>
    </div>

    {temGrupos ? <div className="space-y-1.5">
      <p className="analise-territorios-secao">{maiuscula(grupoRotulo?.plural || "grupos")}</p>
      <p className="text-[11px] leading-4 text-slate-600">"{textoVerUnidades(p.rotulos, 2).replace(/\d+\s/, "N ")}" abre a lista e põe{" "}
        {artigo(grupoRotulo ?? unidade, false)} {grupoRotulo?.singular ?? "grupo"} no gráfico. A caixa marca {todosOs(unidade)}{" "}
        {generoDe(grupoRotulo ?? unidade) === "f" ? "dela" : "dele"} de uma vez, junto com o que já está marcado.</p>
      <ul className="analise-grupos" aria-label={maiuscula(grupoRotulo?.plural || "grupos")}>
        {p.grupos.map(grupo => {
          const lista = porGrupo.get(grupo.id) || [];
          const ids = lista.map(item => item.id);
          const aberto = p.aberto === grupo.id;
          const inteiro = grupoInteiro(p.base, grupo.id);
          const parcial = !inteiro && marcadasNoGrupo(p.base, grupo.id, ids) > 0;
          return <li key={grupo.id} ref={aberto ? abertoRef : undefined} data-testid="analise-grupo" data-id={grupo.id}
            data-aberto={aberto ? "true" : "false"} className={"analise-grupo" + (aberto ? " analise-grupo-aberto" : "")}>
            <div className="analise-grupo-linha">
              <label className="analise-caixa min-w-0 flex-1" title={textoTodasAsUnidadesDoGrupo(p.rotulos, grupo)}>
                <input type="checkbox" data-testid="analise-grupo-todos" checked={inteiro} disabled={p.desabilitado}
                  ref={elemento => { if (elemento) elemento.indeterminate = parcial; }}
                  aria-label={textoTodasAsUnidadesDoGrupo(p.rotulos, grupo)}
                  onChange={() => p.onBase(inteiro ? desmarcarGrupo(p.base, grupo.id, ids, todosOsGrupos, todasAsUnidades)
                    : marcarGrupo(p.base, grupo.id, ids))}/>
                <span className="min-w-0">
                  <span className="block font-semibold text-ink">{grupo.nome}{grupo.sigla ? " (" + grupo.sigla + ")" : ""}</span>
                  <span className="block text-[11px] text-slate-600">{textoTodasAsUnidadesDoGrupo(p.rotulos, grupo)}</span>
                </span>
              </label>
              <button type="button" data-testid="analise-grupo-ver" aria-expanded={aberto} disabled={p.desabilitado}
                className="analise-ver" onClick={() => aberto ? p.onFechar() : p.onVer(grupo.id)}>
                {aberto ? <ChevronDown size={14} aria-hidden="true"/> : <ChevronRight size={14} aria-hidden="true"/>}
                {aberto ? "Fechar a lista" : textoVerUnidades(p.rotulos, grupo.unidades || lista.length)}</button>
            </div>
            {aberto && listaDeUnidades(lista, maiuscula(unidade.plural) + " de " + grupo.nome, grupo.id)}
          </li>;
        })}
      </ul>
    </div> : listaDeUnidades([...validas].sort((a, b) => comparar(a.name || a.label, b.name || b.label)),
      maiuscula(unidade.plural) + " da " + (p.brasil ? "base" : "planilha"), "")}

    <div className="space-y-1.5 border-t border-line pt-3">
      <label className="block text-xs font-semibold text-ink" htmlFor="analise-busca">Procurar pelo nome ou código (opcional)</label>
      <div className="relative">
        <Search size={14} aria-hidden="true" className="pointer-events-none absolute left-2 top-1/2 -translate-y-1/2 text-slate-500"/>
        <input id="analise-busca" type="search" data-testid="analise-busca" value={consulta} disabled={p.desabilitado}
          onChange={event => setConsulta(event.target.value)} placeholder={"Ex.: nome " + (generoDe(unidade) === "f" ? "da " : "do ") + unidade.singular}
          className="analise-campo pl-7"/>
      </div>
      {consulta.trim() && (achados.length ? <ul className="space-y-0.5" aria-label="Resultado da busca">
        {achados.map(item => <li key={item.id} data-testid="analise-busca-item" data-id={item.id}>
          <label className="analise-caixa">
            <input type="checkbox" checked={unidadeMarcada(p.base, item.id, temGrupos ? grupoDaUnidade(item) : "")}
              disabled={p.desabilitado} onChange={() => alternar(item)}/>
            <span className="min-w-0 flex-1">{nomeDaUnidade(item)}</span>
            {temGrupos && <span className="shrink-0 text-[11px] text-slate-500">{nomeDoGrupo(grupoDaUnidade(item))}</span>}
          </label>
        </li>)}
      </ul> : <p className="text-[11px] text-slate-600">Nada encontrado. A lista acima continua com todas as opções.</p>)}
    </div>
  </section>;
}
